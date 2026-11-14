# ai-generated: 100% - Codex implemented CI-SPEC P-14..P-23 and checked it on the course's practice data.
"""Measure SARIF detectors on a labelled set; input files are read only."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
from urllib.parse import unquote


CLASSES = {
    "secret": (259, 260, 321, 798),
    "injection": (74, 77, 78, 79, 80, 88, 89, 90, 91, 94, 95, 96, 611, 776, 917, 943, 1336),
    "deserialization": (502,),
    "weak-crypto": (261, 326, 327, 328, 330, 331, 338, 759, 760, 916),
    "insecure-transport": (295, 297, 319, 322, 757),
    "path-traversal": (22, 23, 35, 36, 73),
    "ssrf": (918,),
    "vulnerable-dependency": (937, 1035, 1104, 1395),
    "misconfiguration": (16, 215, 250, 489, 668, 732, 1188),
    "access-control": (284, 285, 639, 862, 863),
}
CWE_CLASSES = {str(number): category for category, numbers in CLASSES.items() for number in numbers}
CWE = re.compile(r"(?<![A-Za-z0-9])CWE-([0-9]+)", re.ASCII | re.IGNORECASE)
PACKAGE_TOKEN = re.compile(r"[A-Za-z0-9._-]+")
PACKAGE_SEPARATOR = re.compile(r"[-_.]+")
SEMGREP = {"semgrep", "semgrep oss", "semgrep ce", "semgrep community edition", "semgrep pro"}
TRIVY_TAGS = {
    "vulnerability": "vulnerable-dependency",
    "secret": "secret",
    "misconfiguration": "misconfiguration",
}


def obj(value):
    return value if isinstance(value, dict) else {}


def array(value):
    return value if isinstance(value, list) else []


def tool_id(name):
    if not isinstance(name, str):
        return "unknown"
    name = name.strip().lower()
    if name in SEMGREP:
        return "semgrep"
    return re.sub(r"[^a-z0-9]+", "-", name).strip("-") or "unknown"


def normalized_path(uri):
    path = unquote(uri)
    if path[:7].lower() == "file://":
        path = path[7:]
    return path.removeprefix("./")


def set_path(uri, root):
    parts = normalized_path(uri).split("/")
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] == root:
            return "/".join(parts[index:])
    return None


def line_range(region):
    region = obj(region)
    start, end = region.get("startLine"), region.get("endLine")
    if type(start) is not int or start < 1:  # bool is not a JSON integer
        return None, None
    return start, max(start, end) if type(end) is int else start


def tags(element):
    return [tag for tag in array(obj(element.get("properties")).get("tags")) if isinstance(tag, str)]


def classes(tool, result, rule):
    explicit = obj(result.get("properties")).get("class")
    if isinstance(explicit, str) and explicit in CLASSES:
        return {explicit}
    if tool == "gitleaks":
        return {"secret"}
    if tool in {"grype", "osv-scanner"}:
        return {"vulnerable-dependency"}
    rule_tags = tags(rule)
    if tool == "trivy":
        from_trivy = {TRIVY_TAGS[tag.lower()] for tag in rule_tags if tag.lower() in TRIVY_TAGS}
        if from_trivy:
            return from_trivy
    from_cwe = {
        CWE_CLASSES[number]
        for tag in tags(result) + rule_tags
        for match in CWE.finditer(tag)
        if (number := match[1].lstrip("0")) in CWE_CLASSES
    }
    return from_cwe or {"other"}


def package_name(name):
    return PACKAGE_SEPARATOR.sub("-", name.lower())


def mentioned_packages(result):
    message = obj(result.get("message")).get("text")
    if not isinstance(message, str):
        return set()
    return {package_name(token.strip("._-")) for token in PACKAGE_TOKEN.findall(message)}


def findings(run, driver):
    """Yield only usable first physical locations, and the first rule with each string ID."""
    rules = {}
    for raw_rule in array(driver.get("rules")):
        rule = obj(raw_rule)
        if isinstance(rule.get("id"), str):
            rules.setdefault(rule["id"], rule)
    for result in array(run.get("results")):
        if not isinstance(result, dict) or result.get("kind") not in (None, "fail") or result.get("suppressions"):
            continue
        locations = array(result.get("locations"))
        first = obj(locations[0]) if locations else {}
        location = obj(first.get("physicalLocation"))
        uri = obj(location.get("artifactLocation")).get("uri")
        if not isinstance(uri, str) or not uri:
            continue
        raw_id = result.get("ruleId")
        rule_id = raw_id if isinstance(raw_id, str) else None
        yield result, rules.get(rule_id, {}), rule_id, uri, line_range(location.get("region"))


def score(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def evaluate(labels, documents):
    root = labels["set"]
    defects = labels["defects"]
    by_file_class = defaultdict(list)
    for defect in defects:
        by_file_class[defect["file"], defect["class"]].append(defect)

    tools = {}
    for document in documents:
        for run in array(obj(document).get("runs")):
            if not isinstance(run, dict):
                continue
            driver = obj(obj(run.get("tool")).get("driver"))
            tool = tool_id(driver.get("name"))
            detected, unmatched = tools.setdefault(tool, (set(), set()))
            for result, rule, rule_id, uri, (start, end) in findings(run, driver):
                file = set_path(uri, root)
                if file is None:
                    continue
                hits = set()
                for category in classes(tool, result, rule):
                    candidates = by_file_class.get((file, category), ())
                    if category == "vulnerable-dependency" and candidates:
                        packages = mentioned_packages(result)
                        hits.update(d["id"] for d in candidates if package_name(d["package"]) in packages)
                    elif start is not None:
                        hits.update(d["id"] for d in candidates
                                    if start <= d["end_line"] and d["start_line"] <= end)
                if hits:
                    detected.update(hits)
                else:
                    # Deduplicate only after matching; an FP can share a key with a different TP.
                    unmatched.add((rule_id, file, start, end))

    output = {}
    for tool, (detected, unmatched) in sorted(tools.items()):
        tp, fp, fn = len(detected), len(unmatched), len(defects) - len(detected)
        output[tool] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": score(tp, tp + fp), "recall": score(tp, tp + fn),
            "f1": score(2 * tp, 2 * tp + fp + fn),
        }
    return {"set": root, "defects": len(defects), "tools": output}


def read_json(path):
    with path.open(encoding="utf-8-sig") as source:
        return json.load(source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("sarif", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(read_json(args.labels), map(read_json, args.sarif)), indent=2))


if __name__ == "__main__":
    main()

# ai-generated: 100% - Codex wrote synthetic regression tests for the published SARIF matching rules.
import unittest

import bakeoff


def result(uri, rule="rule", start=1, end=None, **fields):
    return {
        "ruleId": rule,
        "locations": [{"physicalLocation": {
            "artifactLocation": {"uri": uri, "uriBaseId": "UNRESOLVED"},
            "region": {"startLine": start, "endLine": end},
        }}],
        **fields,
    }


def run(name, results=None, rules=None):
    return {"tool": {"driver": {"name": name, "rules": rules}}, "results": results}


def line_defect(id_, category, start, end=None, file="custom/File.py"):
    return {"id": id_, "file": file, "class": category, "start_line": start,
            "end_line": start if end is None else end}


def evaluate(defects, *runs):
    return bakeoff.evaluate({"set": "custom", "defects": defects}, [{"runs": list(runs)}])["tools"]


class BakeoffTests(unittest.TestCase):
    def test_encoded_paths_last_root_and_overlap(self):
        defects = [line_defect("a", "injection", 6, 7), line_defect("b", "injection", 8, 10)]
        match = result("FiLe:///custom/not-the-root%2Fcustom/File.py", start=7, end=8,
                       properties={"tags": ["external/cwe/CwE-00089"]})
        wrong = [
            result("custom\\File.py"),
            result("other/Custom/File.py"),
            result("custom-ish/File.py"),
        ]
        self.assertEqual(evaluate(defects, run(" Semgrep OSS ", [match, *wrong]))["semgrep"],
                         {"tp": 2, "fp": 0, "fn": 0, "precision": 1, "recall": 1, "f1": 1})

    def test_line_normalization_and_fp_dedup_after_matching(self):
        uri = "custom/File.py"
        malformed = [result(uri, start=x, end=10) for x in (True, "7", 7.0, None, 0)]
        equivalent = [result(uri, start=7, end=x) for x in (None, 7, 6, "8", True)]
        match = result(uri, start=7, properties={"class": "injection"})
        tools = evaluate([line_defect("a", "injection", 7)],
                         run("Semgrep CE", [match, *malformed, *equivalent]),
                         run("Semgrep Pro", [result(uri, start=7, rule=""),
                                              result(uri, start=7, rule=None),
                                              result(uri, start=7, rule=100)]))
        self.assertEqual(tools["semgrep"], {"tp": 1, "fp": 4, "fn": 0,
                                           "precision": 0.2, "recall": 1, "f1": 0.3333})

    def test_package_boundaries_pep503_and_no_line_requirement(self):
        path = "custom/requirements.txt"
        defects = [{"id": "pkg", "file": path, "class": "vulnerable-dependency", "package": "Foo.bar__Baz"}]
        match = result(path, start=None, rule="A", message={"text": "Affected: (Foo-BAR.baz...)"})
        no_match = [
            result(path, start=None, rule="B", message={"text": "foo-bar-baz-extra"}),
            result(path, rule="C", message={"markdown": "foo-bar-baz"}),
            result(path, rule="D", message={"text": 123}),
        ]
        self.assertEqual(evaluate(defects, run("OSV-Scanner", [match, *no_match]))["osv-scanner"],
                         {"tp": 1, "fp": 3, "fn": 0, "precision": 0.25, "recall": 1, "f1": 0.4})

    def test_class_precedence_and_first_rule_only(self):
        uri = "custom/File.py"
        defects = [line_defect("inject", "injection", 1), line_defect("secret", "secret", 2),
                   line_defect("transport", "insecure-transport", 3)]
        rules = [
            {"id": "a", "properties": {"tags": [" Misconfiguration", "SeCReT", "CWE-89"]}},
            {"id": "a", "properties": {"tags": ["CWE-295"]}},
            {"id": "b", "properties": {"tags": ["XCWE-295", "CWE-2950"]}},
        ]
        results = [
            result(uri, rule="a", properties={"class": "injection"}),
            result(uri, rule="a", start=2),
            result(uri, rule="a", start=3, ruleIndex=1),
            result(uri, rule="b", start=3, properties={"tags": [None, "cwe-00295"]}),
            result(uri, rule="b", start=3, end=4),
        ]
        self.assertEqual(evaluate(defects, run("Trivy", results, rules))["trivy"],
                         {"tp": 3, "fp": 2, "fn": 0, "precision": 0.6, "recall": 1, "f1": 0.75})

    def test_result_scope_and_malformed_records(self):
        uri = "custom/File.py"
        filtered = [
            42, None, [],
            result(uri, rule="uppercase", kind="FAIL"),
            result(uri, rule="pass", kind="pass"),
            result(uri, rule="suppression", suppressions=[None]),
            result(uri, rule="flags", suppressions={"status": "rejected"}),
            result(uri, locations={"physicalLocation": {}}),
            result(uri, locations=[None, result(uri)["locations"][0]]),
            result(""), result(1),
        ]
        kept = [result(uri, rule=str(i), kind=None, suppressions=x)
                for i, x in enumerate((None, [], {}, False, 0, ""))]
        tools = evaluate([], run("Open.Grep CE", [*filtered, *kept]), [],
                         {"tool": {"driver": {"name": {"bad": "shape"}}}, "results": {}},
                         {"tool": None}, run(" ! "))
        self.assertEqual(set(tools), {"open-grep-ce", "unknown"})
        self.assertEqual(tools["open-grep-ce"],
                         {"tp": 0, "fp": 6, "fn": 0, "precision": 0, "recall": None, "f1": 0})
        self.assertEqual(tools["unknown"],
                         {"tp": 0, "fp": 0, "fn": 0, "precision": None, "recall": None, "f1": None})

    def test_merge_tool_runs_across_files_keep_empty_tool(self):
        labels = {"set": "custom", "defects": [line_defect("a", "secret", 10)]}
        detection = result("custom/File.py", start=10)
        duplicate = result("custom/other.py", start=7)
        output = bakeoff.evaluate(labels, [
            {"runs": [run("Gitleaks", [detection, duplicate])]},
            {"runs": [run("GITLEAKS", [duplicate]), run("Grype", None)]},
        ])["tools"]
        self.assertEqual(output["gitleaks"],
                         {"tp": 1, "fp": 1, "fn": 0, "precision": 0.5, "recall": 1, "f1": 0.6667})
        self.assertEqual(output["grype"],
                         {"tp": 0, "fp": 0, "fn": 1, "precision": None, "recall": 0, "f1": 0})

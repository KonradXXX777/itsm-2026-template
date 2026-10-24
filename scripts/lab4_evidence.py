# ai-generated: 100% - Codex made the recorded-incident analysis reproducible with read-only, explicitly timed PromQL.
"""Run against the served, unmodified lab4-rec-1 snapshot; never queries the sealed fault.

python3 scripts/lab4_evidence.py --output incident/evidence.json
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
TIMES = {"baseline": "2026-10-12T04:56:00Z", "fault": "2026-10-12T05:06:00Z",
         "after": "2026-10-12T05:14:00Z"}
SERVER = 'span_kind="SPAN_KIND_SERVER"'
CALLS = "traces_span_metrics_calls_total"
BUCKETS = "traces_span_metrics_duration_milliseconds_bucket"


def quantile(service, kind="SPAN_KIND_SERVER", span=None, p=0.99):
    labels = f'service_name="{service}",span_kind="{kind}"'
    if span:
        labels += f',span_name="{span}"'
    return f'histogram_quantile({p},sum by(le)(rate({BUCKETS}{{{labels}}}[5m])))'


QUERIES = {
    "server_rps": f"sum by(service_name)(rate({CALLS}{{{SERVER}}}[5m]))",
    "server_error_rps": f'sum by(service_name)(rate({CALLS}{{{SERVER},status_code="STATUS_CODE_ERROR"}}[5m]))',
    "server_error_ratio": f'sum by(service_name)(rate({CALLS}{{{SERVER},status_code="STATUS_CODE_ERROR"}}[5m])) / sum by(service_name)(rate({CALLS}{{{SERVER}}}[5m]))',
    "server_p99_ms": f"histogram_quantile(0.99,sum by(service_name,le)(rate({BUCKETS}{{{SERVER}}}[5m])))",
    "checkout_prepare_p99_ms": quantile("checkout", "SPAN_KIND_INTERNAL", "prepareOrderItemsAndShippingQuoteFromCart"),
    "checkout_shipping_client_p99_ms": quantile("checkout", "SPAN_KIND_CLIENT", "POST"),
    "checkout_catalog_client_p99_ms": quantile("checkout", "SPAN_KIND_CLIENT", "oteldemo.ProductCatalogService/GetProduct"),
    "checkout_payment_client_p99_ms": quantile("checkout", "SPAN_KIND_CLIENT", "oteldemo.PaymentService/Charge"),
    "shipping_spans_p99_ms": f'histogram_quantile(0.99,sum by(span_name,le)(rate({BUCKETS}{{service_name="shipping",{SERVER}}}[5m])))',
    "memory_bytes": 'container_memory_usage_total_bytes{container_name=~"email|recommendation"}',
    "memory_limit_bytes": 'container_memory_usage_limit_bytes{container_name=~"email|recommendation"}',
    "uptime_seconds": 'container_uptime_seconds{container_name=~"email|recommendation"}',
    "alerts": 'ALERTS{alertstate="firing"}',
    "email_memory_peak_5m": 'max_over_time(container_memory_usage_total_bytes{container_name="email"}[5m])',
}


def api(base, path, params):
    request = Request(base.rstrip("/") + path, data=urlencode(params).encode(), method="POST")
    with urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if payload.get("status") != "success":
        raise RuntimeError(payload)
    # Prometheus does not guarantee vector ordering; normalize labels without changing samples.
    return sorted(payload["data"]["result"],
                  key=lambda row: json.dumps(row.get("metric", {}), sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:19090")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {"recording": "lab4-rec-1", "snapshot_sha256": hashlib.sha256(
        (ROOT / "incident/tsdb-snapshot.tar.gz").read_bytes()).hexdigest(), "times": TIMES,
        "queries": QUERIES, "samples": {}, "impact": {}, "ledger_checks": {}, "alert_rule_checks": {}}
    for label, time in TIMES.items():
        result["samples"][label] = {name: api(args.url, "/api/v1/query", {"query": expr, "time": time})
                                    for name, expr in QUERIES.items()}
    # Increase is extrapolated from minute-spaced counters: these are estimates of spans, not exact users/orders.
    for service in ("checkout", "ad", "shipping", "email", "frontend"):
        for suffix, extra in (("calls", ""), ("errors", ',status_code="STATUS_CODE_ERROR"')):
            expr = f'sum(increase({CALLS}{{service_name="{service}",{SERVER}{extra}}}[439s]))'
            result["impact"][service + "_" + suffix] = {"query": expr, "time": "2026-10-12T05:08:19Z",
                "result": api(args.url, "/api/v1/query", {"query": expr, "time": "2026-10-12T05:08:19Z"})}
    for name in ("ai-rca-eval.json", "ai-rca-eval-2.json"):
        path = ROOT / name
        if not path.exists():
            continue
        ledger = json.loads(path.read_text())
        checks = []
        for entry in ledger["hypotheses"]:
            if not entry.get("predicts"):
                continue
            actual = api(args.url, "/api/v1/query", {"query": entry["predicts"], "time": entry["at"]})
            healthy = api(args.url, "/api/v1/query", {"query": entry["predicts"], "time": TIMES["baseline"]})
            checks.append({"id": entry["id"], "actual": actual, "baseline": healthy,
                           "declared_result": entry["result"], "matches": bool(actual) == entry["result"]})
            if bool(actual) != entry["result"]:
                raise AssertionError(f"{name}/{entry['id']}: result does not match the snapshot")
            if entry["verdict"] in ("correct", "partially_correct") and healthy:
                raise AssertionError(f"{name}/{entry['id']}: prediction also true on healthy baseline")
        result["ledger_checks"][name] = checks
    # The submitted rules are proposals, not a claim that they ran in this historical snapshot.
    # Read YAML only when PyYAML is available (the course-agent venv includes it).
    try:
        import yaml
    except ImportError:
        pass
    else:
        rules = yaml.safe_load((ROOT / "prometheus/demo-alerts.yml").read_text())
        for group in rules["groups"]:
            for rule in group["rules"]:
                result["alert_rule_checks"][rule["alert"]] = {
                    label: api(args.url, "/api/v1/query", {"query": rule["expr"], "time": time})
                    for label, time in TIMES.items()}
        if any(v["baseline"] for v in result["alert_rule_checks"].values()):
            raise AssertionError("A proposed shop alert expression is true on the healthy baseline")
    # Only the public binary active marker and ALERTS are used to explain the formal clocks,
    # never any sealed key, ciphertext or hidden flag value.
    result["clock_samples"] = {
        "public_active_marker": api(args.url, "/api/v1/query", {
            "query": "seeded_fault_active[30m]", "time": "2026-10-12T05:16:00Z"}),
        "recorded_firing_alerts": api(args.url, "/api/v1/query", {
            "query": 'ALERTS{alertstate="firing"}[30m]', "time": "2026-10-12T05:16:00Z"})}
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()

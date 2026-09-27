# ai-generated: 100% - OpenAI Codex implemented HTTP, ticket lifecycle and DORA endpoint tests.

"""Containerized own tests for the Stretch S3 contract."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = os.getenv("SVCDESK_URL", "http://svcdesk:8080").rstrip("/")
T1 = "2026-10-14T10:00:00Z"


def request(method: str, path: str, clock: str = T1, body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json", "X-Test-Clock": clock}
    if data is not None:
        headers["Content-Type"] = "application/json"
    call = urllib.request.Request(BASE_URL + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(call, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        payload = json.loads(error.read())
        return error.code, payload


def create(**overrides) -> tuple[int, dict]:
    payload = {
        "title": "own test ticket",
        "description": "containerized verification",
        "reporter": {"name": "own tests", "vip": False},
        "impact": 1,
        "urgency": 1,
    }
    payload.update(overrides)
    return request("POST", "/tickets", body=payload)


def main() -> None:
    passed = 0
    failed = 0

    def check(name: str, condition: bool) -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
        else:
            failed += 1
            print(f"FAIL: {name}")

    for _ in range(20):
        try:
            status, payload = request("GET", "/health")
            if status == 200:
                break
        except OSError:
            time.sleep(0.5)
    else:
        print("FAIL: service did not become healthy")
        print("ITSMLAB-TESTS: passed=0 failed=1")
        raise SystemExit(1)

    check("health", status == 200 and payload == {"status": "ok"})
    status, ticket = create()
    check("create status", status == 201)
    check("create state", ticket.get("state") == "new")
    check("matrix priority", ticket.get("priority") == "P1")
    check("test clock", ticket.get("created_at") == T1)
    ticket_id = ticket["id"]
    status, fetched = request("GET", f"/tickets/{ticket_id}")
    check("get ticket", status == 200 and fetched.get("id") == ticket_id)
    query = urllib.parse.urlencode({"priority": "P1"})
    status, listed = request("GET", f"/tickets?{query}")
    check("priority filter", status == 200 and ticket_id in {item["id"] for item in listed})
    status, acknowledged = request("POST", f"/tickets/{ticket_id}/ack", "2026-10-14T10:05:00Z")
    check("ack", status == 200 and acknowledged.get("state") == "acknowledged")
    status, started = request("POST", f"/tickets/{ticket_id}/start", "2026-10-14T10:10:00Z")
    check("start", status == 200 and started.get("state") == "in_progress")
    status, resolved = request("POST", f"/tickets/{ticket_id}/resolve", "2026-10-14T11:00:00Z")
    check("resolve", status == 200 and resolved.get("state") == "resolved")
    status, closed = request("POST", f"/tickets/{ticket_id}/close", "2026-10-14T12:00:00Z")
    check("close", status == 200 and closed.get("state") == "closed")
    status, timeline = request("GET", "/dora/ticket-events")
    phases = [item["phase"] for item in timeline if item["ticket_id"] == ticket_id]
    check("ticket lifecycle stream", status == 200 and phases == ["created", "acknowledged", "resolved", "closed"])
    ordered_keys = [(item["at"], item["ticket_id"]) for item in timeline]
    check("ticket stream ordering", ordered_keys == sorted(ordered_keys))
    status, one_ticket_timeline = request("GET", f"/dora/tickets/{ticket_id}/events")
    expected_ticket_timeline = [item for item in timeline if item["ticket_id"] == ticket_id]
    check(
        "single-ticket lifecycle lookup",
        status == 200 and one_ticket_timeline == expected_ticket_timeline,
    )
    status, missing_ticket_timeline = request("GET", "/dora/tickets/not-a-ticket/events")
    check(
        "single-ticket lookup not found",
        status == 404 and "error" in missing_ticket_timeline,
    )
    status, reopened = request("POST", f"/tickets/{ticket_id}/reopen", "2026-10-15T12:00:00Z")
    check("closed reopen", status == 200 and reopened.get("state") == "in_progress")

    metrics_window = {"from": "2026-09-01T00:00:00Z", "to": "2026-09-22T00:00:00Z"}
    metrics_events = [
        {
            "event_id": "test-commit",
            "type": "commit",
            "at": "2026-09-01T00:00:00Z",
            "sha": "test-sha",
            "branch": "feature/test",
            "change_id": "test-change",
            "reverts": None,
        },
        {
            "event_id": "test-deployment",
            "type": "deployment",
            "at": "2026-09-01T00:00:10Z",
            "deployment_id": "test-deploy",
            "environment": "production",
            "outcome": "success",
            "commits": ["test-sha"],
            "unplanned": False,
            "caused_by": None,
        },
    ]
    metrics_request = {"window": metrics_window, "events": metrics_events}
    status, metrics = request("POST", "/dora/metrics", body=metrics_request)
    check(
        "DORA metric response",
        status == 200
        and metrics.get("spec_version") == "1.0.0"
        and metrics.get("counts", {}).get("deployments") == 1
        and metrics.get("change_lead_time_seconds_p50") == 10,
    )
    status, repeated_metrics = request("POST", "/dora/metrics", body=metrics_request)
    check("DORA request purity", status == 200 and repeated_metrics == metrics)
    reversed_request = {"window": metrics_window, "events": list(reversed(metrics_events))}
    status, reversed_metrics = request("POST", "/dora/metrics", body=reversed_request)
    check("DORA order independence", status == 200 and reversed_metrics == metrics)
    duplicate_request = {"window": metrics_window, "events": metrics_events * 2}
    status, duplicate_metrics = request("POST", "/dora/metrics", body=duplicate_request)
    check("DORA duplicate events", status == 200 and duplicate_metrics == metrics)
    status, empty_metrics = request("POST", "/dora/metrics", body={"window": metrics_window, "events": []})
    check(
        "DORA empty log",
        status == 200
        and empty_metrics.get("deployment_frequency_per_day") == 0.0
        and empty_metrics.get("change_lead_time_seconds_p50") is None
        and empty_metrics.get("change_fail_rate") is None
        and empty_metrics.get("counts", {}).get("deployments") == 0,
    )
    status, missing_window = request("POST", "/dora/metrics", body={"events": []})
    check("DORA rejects missing window", status == 422 and "error" in missing_window)
    status, invalid_window = request(
        "POST",
        "/dora/metrics",
        body={"window": {"from": "2026-09-02T00:00:00Z", "to": "2026-09-01T00:00:00Z"}, "events": []},
    )
    check("DORA rejects invalid window", status == 422 and "error" in invalid_window)
    bad_reference = [dict(metrics_events[0], reverts="unknown-sha")]
    status, invalid_log = request("POST", "/dora/metrics", body={"window": metrics_window, "events": bad_reference})
    check("DORA rejects malformed log", status == 422 and "error" in invalid_log)

    status, error = request("POST", "/tickets", body={"impact": 1, "urgency": 1, "reporter": {"name": "x"}})
    check("validation envelope", status == 422 and "error" in error)
    status, vip = create(reporter={"name": "VIP", "vip": True}, impact=3, urgency=3, priority="P1")
    check("VIP elevation", status == 201 and vip.get("priority") == "P2")
    status, conflict_ticket = create(title="conflict")
    status, conflict = request("POST", f"/tickets/{conflict_ticket['id']}/start")
    check("invalid transition", status == 409 and "error" in conflict)
    status, malformed = request("POST", "/tickets", "yesterday", {
        "title": "bad clock", "reporter": {"name": "x"}, "impact": 1, "urgency": 1,
    })
    check("malformed clock", status == 400 and "error" in malformed)

    print(f"ITSMLAB-TESTS: passed={passed} failed={failed}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

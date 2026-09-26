# ai-generated: 100% - OpenAI Codex implemented a dependency-free HTTP smoke and lifecycle test suite.

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
    status, reopened = request("POST", f"/tickets/{ticket_id}/reopen", "2026-10-15T12:00:00Z")
    check("closed reopen", status == 200 and reopened.get("state") == "in_progress")
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

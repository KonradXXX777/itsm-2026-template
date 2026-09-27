# ai-generated: 100% - OpenAI Codex implemented the published Lab 2 metric rules and validation.

"""Validation and deterministic calculation for the Lab 2 delivery metrics."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


SPEC_VERSION = "1.0.0"
_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
_MICROSECONDS = Decimal("1000000")
_SIX_PLACES = Decimal("0.000001")


class MetricsInputError(ValueError):
    """Raised when a request or event log violates METRIC-SPEC.md."""


def _instant(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not _RFC3339.fullmatch(value):
        raise MetricsInputError(f"{label} must be an RFC 3339 instant with an offset")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        result = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MetricsInputError(f"{label} is not a valid instant") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise MetricsInputError(f"{label} must include an offset")
    return result.astimezone(timezone.utc)


def _text(event: dict[str, Any], key: str, *, nullable: bool = False) -> str | None:
    value = event.get(key)
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not value:
        raise MetricsInputError(f"{event.get('event_id', 'event')}.{key} must be a non-empty string")
    return value


def _string_list(event: dict[str, Any], key: str) -> list[str]:
    value = event.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise MetricsInputError(f"{event.get('event_id', 'event')}.{key} must be an array of non-empty strings")
    return value


def _duration_seconds(later: datetime, earlier: datetime) -> Decimal:
    delta = later - earlier
    micros = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    return Decimal(micros) / _MICROSECONDS


def _rounded_seconds(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _median(values: list[Decimal]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        value = ordered[middle]
    else:
        value = (ordered[middle - 1] + ordered[middle]) / Decimal(2)
    return _rounded_seconds(value)


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    value = (Decimal(numerator) / Decimal(denominator)).quantize(_SIX_PLACES, rounding=ROUND_HALF_UP)
    return float(value)


def _deduplicate_and_validate(events: Any) -> list[dict[str, Any]]:
    if not isinstance(events, list):
        raise MetricsInputError("events must be an array")

    unique: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise MetricsInputError(f"events[{index}] must be an object")
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 64:
            raise MetricsInputError(f"events[{index}].event_id must contain 1 to 64 characters")
        if event_id in seen_event_ids:
            continue
        seen_event_ids.add(event_id)
        event = dict(event)
        kind = event.get("type")
        if not isinstance(kind, str) or kind not in {"commit", "deployment", "incident"}:
            raise MetricsInputError(f"{event_id}.type must be commit, deployment or incident")
        _instant(event.get("at"), f"{event_id}.at")
        unique.append(event)

    commits: dict[str, dict[str, Any]] = {}
    deployments: dict[str, dict[str, Any]] = {}
    incidents: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for event in unique:
        kind = event["type"]
        event_id = event["event_id"]
        if kind == "commit":
            if "change_id" not in event or "reverts" not in event:
                raise MetricsInputError(f"{event_id} must include change_id and reverts")
            sha = _text(event, "sha")
            branch = _text(event, "branch")
            change_id = _text(event, "change_id", nullable=True)
            reverts = _text(event, "reverts", nullable=True)
            if sha in commits:
                raise MetricsInputError(f"commit sha {sha} must be unique")
            if (reverts is None) != (change_id is not None):
                raise MetricsInputError(f"{event_id} must have change_id exactly when reverts is null")
            event["_at"] = _instant(event["at"], f"{event_id}.at")
            event["_sha"] = sha
            event["_branch"] = branch
            event["_change_id"] = change_id
            event["_reverts"] = reverts
            commits[sha] = event
        elif kind == "deployment":
            if "caused_by" not in event:
                raise MetricsInputError(f"{event_id} must include caused_by")
            deployment_id = _text(event, "deployment_id")
            environment = _text(event, "environment")
            outcome = _text(event, "outcome")
            unplanned = event.get("unplanned")
            caused_by = _text(event, "caused_by", nullable=True)
            shas = _string_list(event, "commits")
            if deployment_id in deployments:
                raise MetricsInputError(f"deployment_id {deployment_id} must be unique")
            if outcome not in {"success", "failure"}:
                raise MetricsInputError(f"{event_id}.outcome must be success or failure")
            if not isinstance(unplanned, bool):
                raise MetricsInputError(f"{event_id}.unplanned must be a boolean")
            event["_at"] = _instant(event["at"], f"{event_id}.at")
            event["_deployment_id"] = deployment_id
            event["_environment"] = environment
            event["_outcome"] = outcome
            event["_unplanned"] = unplanned
            event["_caused_by"] = caused_by
            event["_commits"] = shas
            deployments[deployment_id] = event
        else:
            incident_id = _text(event, "incident_id")
            phase = _text(event, "phase")
            shas = _string_list(event, "deployments")
            if phase not in {"opened", "resolved"}:
                raise MetricsInputError(f"{event_id}.phase must be opened or resolved")
            if phase in incidents[incident_id]:
                raise MetricsInputError(f"incident {incident_id} has more than one {phase} event")
            event["_at"] = _instant(event["at"], f"{event_id}.at")
            event["_incident_id"] = incident_id
            event["_phase"] = phase
            event["_deployments"] = shas
            incidents[incident_id][phase] = event

    for event in commits.values():
        parent = event["_reverts"]
        if parent is not None and parent not in commits:
            raise MetricsInputError(f"reverts references unknown sha {parent}")
    for event in deployments.values():
        for sha in event["_commits"]:
            if sha not in commits:
                raise MetricsInputError(f"deployment references unknown sha {sha}")
    for event in deployments.values():
        incident_id = event["_caused_by"]
        if incident_id is not None and incident_id not in incidents:
            raise MetricsInputError(f"caused_by references unknown incident {incident_id}")
    for incident_id, phases in incidents.items():
        opened = phases.get("opened")
        resolved = phases.get("resolved")
        if resolved is not None and opened is None:
            raise MetricsInputError(f"incident {incident_id} resolved without an opened event")
        if resolved is not None and resolved["_at"] < opened["_at"]:
            raise MetricsInputError(f"incident {incident_id} resolves before it opens")
        for event in phases.values():
            for deployment_id in event["_deployments"]:
                if deployment_id not in deployments:
                    raise MetricsInputError(f"incident references unknown deployment {deployment_id}")

    return unique


def calculate_metrics(payload: Any) -> dict[str, Any]:
    """Return the complete spec 1.0.0 object or raise MetricsInputError."""
    if not isinstance(payload, dict):
        raise MetricsInputError("request body must be an object")
    window = payload.get("window")
    if not isinstance(window, dict):
        raise MetricsInputError("window must be an object")
    start = _instant(window.get("from"), "window.from")
    end = _instant(window.get("to"), "window.to")
    if end <= start:
        raise MetricsInputError("window.to must be after window.from")

    events = _deduplicate_and_validate(payload.get("events"))
    commits = {event["_sha"]: event for event in events if event["type"] == "commit"}
    deployment_events = [event for event in events if event["type"] == "deployment"]
    incident_events = [event for event in events if event["type"] == "incident"]

    resolved_changes: dict[str, str] = {}

    def change_for(sha: str, trail: set[str] | None = None) -> str:
        if sha in resolved_changes:
            return resolved_changes[sha]
        trail = set() if trail is None else trail
        if sha in trail:
            raise MetricsInputError("revert references contain a cycle")
        trail.add(sha)
        commit = commits[sha]
        parent = commit["_reverts"]
        result = commit["_change_id"] if parent is None else change_for(parent, trail)
        resolved_changes[sha] = result
        return result

    for sha in commits:
        change_for(sha)

    all_changes = set(resolved_changes.values())
    first_commit_by_change: dict[str, datetime] = {}
    for sha, change_id in resolved_changes.items():
        at = commits[sha]["_at"]
        first_commit_by_change[change_id] = min(at, first_commit_by_change.get(change_id, at))

    in_window = [
        event for event in deployment_events
        if event["_environment"] == "production" and start <= event["_at"] < end
    ]
    deployment_count = len(in_window)
    successes = [event for event in in_window if event["_outcome"] == "success"]
    failures = [event for event in in_window if event["_outcome"] == "failure"]
    rework_count = sum(1 for event in in_window if event["_unplanned"] and event["_caused_by"] is not None)
    no_commit_count = sum(1 for event in in_window if not event["_commits"])

    commits_never_on_main = {
        sha
        for deployment in in_window
        for sha in deployment["_commits"]
        if commits[sha]["_branch"] != "main"
    }

    first_successful_deployment_by_sha: dict[str, datetime] = {}
    first_successful_deployment_by_change: dict[str, datetime] = {}
    for deployment in successes:
        for sha in set(deployment["_commits"]):
            first_successful_deployment_by_sha[sha] = min(
                deployment["_at"], first_successful_deployment_by_sha.get(sha, deployment["_at"])
            )
            change_id = resolved_changes[sha]
            first_successful_deployment_by_change[change_id] = min(
                deployment["_at"],
                first_successful_deployment_by_change.get(change_id, deployment["_at"]),
            )

    lead_values: list[Decimal] = []
    negative_lead_pairs = 0
    for sha, deployed_at in first_successful_deployment_by_sha.items():
        duration = _duration_seconds(deployed_at, commits[sha]["_at"])
        if duration < 0:
            negative_lead_pairs += 1
            duration = Decimal(0)
        lead_values.append(duration)

    delivered_values: list[Decimal] = []
    for change_id, delivered_at in first_successful_deployment_by_change.items():
        duration = _duration_seconds(delivered_at, first_commit_by_change[change_id])
        delivered_values.append(max(duration, Decimal(0)))

    incidents: dict[str, dict[str, Any]] = defaultdict(dict)
    incident_coverages: dict[str, set[str]] = defaultdict(set)
    for event in incident_events:
        incident_id = event["_incident_id"]
        incidents[incident_id][event["_phase"]] = event
        incident_coverages[incident_id].update(event["_deployments"])

    covering_incident: dict[str, list[tuple[datetime, bytes, str]]] = defaultdict(list)
    for incident_id, phases in incidents.items():
        opened = phases.get("opened")
        if opened is None:
            continue
        for deployment_id in incident_coverages[incident_id]:
            covering_incident[deployment_id].append(
                (opened["_at"], incident_id.encode("utf-8"), incident_id)
            )

    recovery_values: list[Decimal] = []
    open_failures = 0
    for deployment in failures:
        options = covering_incident.get(deployment["_deployment_id"], [])
        if not options:
            open_failures += 1
            continue
        incident_id = min(options)[2]
        resolved = incidents[incident_id].get("resolved")
        if resolved is None:
            open_failures += 1
            continue
        duration = _duration_seconds(resolved["_at"], deployment["_at"])
        recovery_values.append(max(duration, Decimal(0)))

    incident_intervals: list[tuple[datetime, datetime]] = []
    for phases in incidents.values():
        opened = phases.get("opened")
        if opened is None:
            continue
        resolved = phases.get("resolved")
        interval_end = resolved["_at"] if resolved is not None else end
        incident_intervals.append((opened["_at"], interval_end))
    overlapping_pairs = 0
    for index, (left_start, left_end) in enumerate(incident_intervals):
        for right_start, right_end in incident_intervals[index + 1 :]:
            if left_start < right_end and right_start < left_end:
                overlapping_pairs += 1

    window_days = _duration_seconds(end, start) / Decimal(86400)
    frequency = (Decimal(deployment_count) / window_days).quantize(_SIX_PLACES, rounding=ROUND_HALF_UP)
    return {
        "spec_version": SPEC_VERSION,
        "window": {"from": window["from"], "to": window["to"]},
        "deployment_frequency_per_day": float(frequency),
        "change_lead_time_seconds_p50": _median(lead_values),
        "failed_deployment_recovery_time_seconds_p50": _median(recovery_values),
        "change_fail_rate": _rate(len(failures), deployment_count),
        "deployment_rework_rate": _rate(rework_count, deployment_count),
        "counts": {
            "deployments": deployment_count,
            "successful_deployments": len(successes),
            "failed_deployments": len(failures),
            "recovered_failures": len(recovery_values),
            "open_failures": open_failures,
            "rework_deployments": rework_count,
            "lead_time_pairs": len(lead_values),
            "changes": len(all_changes),
        },
        "anomalies": {
            "negative_lead_time_pairs": negative_lead_pairs,
            "deployments_without_commits": no_commit_count,
            "commits_never_on_main": len(commits_never_on_main),
            "revert_chains_collapsed": sum(1 for event in commits.values() if event["_reverts"] is not None),
            "overlapping_incident_pairs": overlapping_pairs,
        },
        "ground_truth": {
            "changes_delivered": len(first_successful_deployment_by_change),
            "true_change_lead_time_seconds_p50": _median(delivered_values),
        },
    }

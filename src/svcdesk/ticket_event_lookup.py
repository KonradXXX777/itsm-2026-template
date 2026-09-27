# ai-generated: 100% - OpenAI Codex implemented the single-ticket lifecycle event lookup.

"""Build a lifecycle stream for one stored service desk ticket."""

from __future__ import annotations

from .clock import format_instant, parse_instant
from .storage import connect


PHASES = (
    ("created", "created_at", "new"),
    ("acknowledged", "acknowledged_at", "acknowledged"),
    ("resolved", "resolved_at", "resolved"),
    ("closed", "closed_at", "closed"),
)


def events_for_ticket(ticket_id: str) -> list[dict] | None:
    """Return a ticket's occurred lifecycle events, or None when it does not exist."""
    with connect() as connection:
        row = connection.execute(
            "SELECT id, priority, created_at, acknowledged_at, resolved_at, closed_at "
            "FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
    if row is None:
        return None

    events: list[dict] = []
    for phase, column, state in PHASES:
        value = row[column]
        if value is None:
            continue
        events.append(
            {
                "ticket_id": row["id"],
                "at": format_instant(parse_instant(value)),
                "phase": phase,
                "priority": row["priority"],
                "state": state,
            }
        )
    events.sort(key=lambda event: (parse_instant(event["at"]), event["ticket_id"]))
    return events

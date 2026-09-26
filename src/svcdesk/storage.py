# ai-generated: 100% - OpenAI Codex implemented the SQLite persistence layer and ticket serialization.

"""SQLite persistence for svcdesk tickets."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    reporter_name TEXT NOT NULL,
    reporter_vip INTEGER NOT NULL,
    impact INTEGER NOT NULL,
    urgency INTEGER NOT NULL,
    priority TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    ack_due_at TEXT NOT NULL,
    resolve_due_at TEXT NOT NULL,
    acknowledged_at TEXT,
    resolved_at TEXT,
    closed_at TEXT
)
"""


def database_path() -> Path:
    return Path(os.getenv("SVCDESK_DB", "/data/svcdesk.db"))


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize() -> None:
    with connect() as connection:
        connection.execute(SCHEMA)


def row_to_ticket(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "reporter": {"name": row["reporter_name"], "vip": bool(row["reporter_vip"])},
        "impact": row["impact"],
        "urgency": row["urgency"],
        "priority": row["priority"],
        "state": row["state"],
        "created_at": row["created_at"],
        "acknowledged_at": row["acknowledged_at"],
        "resolved_at": row["resolved_at"],
        "closed_at": row["closed_at"],
        "sla": {
            "ack_due_at": row["ack_due_at"],
            "resolve_due_at": row["resolve_due_at"],
        },
    }


def fetch(ticket_id: str) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()

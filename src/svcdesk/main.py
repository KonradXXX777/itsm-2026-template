# ai-generated: 100% - OpenAI Codex implemented the FastAPI contract, validation and ticket state machine.

"""FastAPI application for the Lab 1 service desk."""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

from .clock import due_instants, format_instant, is_business_time, parse_instant
from .storage import connect, fetch, initialize, row_to_ticket


MATRIX = {
    (1, 1): "P1", (1, 2): "P2", (1, 3): "P3",
    (2, 1): "P2", (2, 2): "P3", (2, 3): "P4",
    (3, 1): "P3", (3, 2): "P4", (3, 3): "P4",
}


class Reporter(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1)
    vip: StrictBool = False


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    reporter: Reporter
    impact: StrictInt = Field(ge=1, le=3)
    urgency: StrictInt = Field(ge=1, le=3)


def request_time(x_test_clock: Annotated[str | None, Header(alias="X-Test-Clock")] = None) -> datetime:
    if x_test_clock is None:
        return datetime.now(timezone.utc)
    if os.getenv("SVCDESK_TEST_CLOCK") != "1":
        return datetime.now(timezone.utc)
    try:
        return parse_instant(x_test_clock)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="invalid X-Test-Clock") from exc


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize()
    yield


app = FastAPI(title="svcdesk", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "details": jsonable_encoder(exc.errors())},
    )


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


def require_ticket(ticket_id: str):
    row = fetch(ticket_id)
    if row is None:
        raise HTTPException(status_code=404, detail="ticket not found")
    return row


def computed_priority(impact: int, urgency: int, vip: bool) -> str:
    priority = MATRIX[(impact, urgency)]
    if vip and priority in {"P3", "P4"}:
        return "P2"
    return priority


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/tickets", status_code=201)
def create_ticket(payload: TicketCreate, now: datetime = Depends(request_time)) -> dict:
    ticket_id = str(uuid.uuid4())
    priority = computed_priority(payload.impact, payload.urgency, payload.reporter.vip)
    ack_due, resolve_due = due_instants(now, priority)
    values = (
        ticket_id,
        payload.title,
        payload.description,
        payload.reporter.name,
        int(payload.reporter.vip),
        payload.impact,
        payload.urgency,
        priority,
        "new",
        format_instant(now),
        format_instant(ack_due),
        format_instant(resolve_due),
    )
    with connect() as connection:
        connection.execute(
            """INSERT INTO tickets (
                id, title, description, reporter_name, reporter_vip, impact, urgency,
                priority, state, created_at, ack_due_at, resolve_due_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            values,
        )
    return row_to_ticket(require_ticket(ticket_id))


@app.get("/tickets")
def list_tickets(
    state: Annotated[str | None, Query()] = None,
    priority: Annotated[str | None, Query()] = None,
) -> list[dict]:
    clauses: list[str] = []
    parameters: list[str] = []
    if state is not None:
        clauses.append("state = ?")
        parameters.append(state)
    if priority is not None:
        clauses.append("priority = ?")
        parameters.append(priority)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connect() as connection:
        rows = connection.execute("SELECT * FROM tickets" + where + " ORDER BY rowid", parameters).fetchall()
    return [row_to_ticket(row) for row in rows]


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict:
    return row_to_ticket(require_ticket(ticket_id))


def transition(ticket_id: str, source: set[str], target: str, now: datetime, timestamp_column: str | None = None) -> dict:
    row = require_ticket(ticket_id)
    if row["state"] not in source:
        raise HTTPException(status_code=409, detail=f"cannot transition from {row['state']} to {target}")
    assignments = ["state = ?"]
    parameters: list[str] = [target]
    if timestamp_column is not None:
        assignments.append(f"{timestamp_column} = ?")
        parameters.append(format_instant(now))
    parameters.append(ticket_id)
    with connect() as connection:
        connection.execute(f"UPDATE tickets SET {', '.join(assignments)} WHERE id = ?", parameters)
    return row_to_ticket(require_ticket(ticket_id))


@app.post("/tickets/{ticket_id}/ack")
def acknowledge(ticket_id: str, now: datetime = Depends(request_time)) -> dict:
    return transition(ticket_id, {"new"}, "acknowledged", now, "acknowledged_at")


@app.post("/tickets/{ticket_id}/start")
def start(ticket_id: str, now: datetime = Depends(request_time)) -> dict:
    return transition(ticket_id, {"acknowledged"}, "in_progress", now)


@app.post("/tickets/{ticket_id}/resolve")
def resolve(ticket_id: str, now: datetime = Depends(request_time)) -> dict:
    return transition(ticket_id, {"in_progress"}, "resolved", now, "resolved_at")


@app.post("/tickets/{ticket_id}/close")
def close(ticket_id: str, now: datetime = Depends(request_time)) -> dict:
    return transition(ticket_id, {"resolved"}, "closed", now, "closed_at")


@app.post("/tickets/{ticket_id}/reopen")
def reopen(ticket_id: str, now: datetime = Depends(request_time)) -> dict:
    row = require_ticket(ticket_id)
    if row["state"] not in {"resolved", "closed"}:
        raise HTTPException(status_code=409, detail="only resolved or closed tickets can be reopened")
    resolved_at = parse_instant(row["resolved_at"])
    if now > resolved_at + timedelta(days=7):
        raise HTTPException(status_code=409, detail="the seven-day reopen window has expired")
    return transition(ticket_id, {"resolved", "closed"}, "in_progress", now)


@app.get("/tickets/{ticket_id}/sla")
def sla_status(ticket_id: str, now: datetime = Depends(request_time)) -> dict:
    row = require_ticket(ticket_id)
    ack_due = parse_instant(row["ack_due_at"])
    resolve_due = parse_instant(row["resolve_due_at"])
    acknowledged = parse_instant(row["acknowledged_at"]) if row["acknowledged_at"] else None
    resolved = parse_instant(row["resolved_at"]) if row["resolved_at"] else None
    ack_breached = (acknowledged > ack_due) if acknowledged else (now > ack_due)
    resolve_breached = (resolved > resolve_due) if resolved else (now > resolve_due)
    paused = row["priority"] != "P1" and not is_business_time(now)
    return {
        "ack_due_at": row["ack_due_at"],
        "resolve_due_at": row["resolve_due_at"],
        "ack_breached": ack_breached,
        "resolve_breached": resolve_breached,
        "paused": paused,
    }

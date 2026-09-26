# ai-generated: 100% - OpenAI Codex implemented the published Warsaw business-time and SLA rules.

"""Clock parsing and SLA arithmetic for the svcdesk API."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


UTC = timezone.utc
WARSAW = ZoneInfo("Europe/Warsaw")
OPENING = time(8, 0)
CLOSING = time(16, 0)

TARGETS: dict[str, tuple[timedelta, timedelta]] = {
    "P1": (timedelta(minutes=15), timedelta(hours=4)),
    "P2": (timedelta(hours=1), timedelta(hours=8)),
    "P3": (timedelta(hours=4), timedelta(hours=24)),
    "P4": (timedelta(hours=8), timedelta(hours=72)),
}


def parse_instant(value: str) -> datetime:
    """Parse an RFC 3339 timestamp and normalize it to UTC."""
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    instant = datetime.fromisoformat(normalized)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return instant.astimezone(UTC)


def format_instant(value: datetime) -> str:
    """Serialize an aware instant as canonical UTC RFC 3339."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def is_business_day(day: date) -> bool:
    return day.weekday() < 5


def _at(day: date, value: time) -> datetime:
    return datetime.combine(day, value, tzinfo=WARSAW)


def _next_business_day(day: date) -> date:
    while not is_business_day(day):
        day += timedelta(days=1)
    return day


def is_business_time(instant: datetime) -> bool:
    local = instant.astimezone(WARSAW)
    return is_business_day(local.date()) and OPENING <= local.time() < CLOSING


def _align_to_business(local: datetime) -> datetime:
    day = local.date()
    if not is_business_day(day) or local.time() >= CLOSING:
        return _at(_next_business_day(day + timedelta(days=1)), OPENING)
    if local.time() < OPENING:
        return _at(day, OPENING)
    return local


def business_due(created_at: datetime, target: timedelta) -> datetime:
    cursor = _align_to_business(created_at.astimezone(WARSAW))
    remaining = target
    while True:
        closing = _at(cursor.date(), CLOSING)
        available = closing - cursor
        if remaining <= available:
            return (cursor + remaining).astimezone(UTC)
        remaining -= available
        cursor = _at(_next_business_day(cursor.date() + timedelta(days=1)), OPENING)


def due_instants(created_at: datetime, priority: str) -> tuple[datetime, datetime]:
    """Return due instants for C1=wallclock: P1 continuous, P2-P4 business."""
    ack_target, resolve_target = TARGETS[priority]
    if priority == "P1":
        return created_at + ack_target, created_at + resolve_target
    return business_due(created_at, ack_target), business_due(created_at, resolve_target)

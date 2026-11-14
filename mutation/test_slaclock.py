# ai-generated: 100% - Codex translated the course docstrings into black-box boundary and reference-model tests.
from datetime import datetime, timedelta
from itertools import product

import pytest
import slaclock as sla


def instant(value):
    return datetime.fromisoformat(value)


@pytest.mark.parametrize("vip", [False, True])
def test_priority_matrix(vip):
    matrix = [["P1", "P2", "P3"], ["P2", "P3", "P4"], ["P3", "P4", "P4"]]
    for impact, urgency in product(range(1, 4), repeat=2):
        expected = matrix[impact - 1][urgency - 1]
        if vip and expected in {"P3", "P4"}:
            expected = "P2"
        assert sla.priority_of(impact, urgency, vip) == expected
    assert sla.priority_of(3, 3) == "P4"


@pytest.mark.parametrize("bad", [-1, 0, 4, 2.0, True, False, "1", None, []])
def test_priority_rejects_each_invalid_coordinate(bad):
    with pytest.raises(ValueError):
        sla.priority_of(bad, 1)
    with pytest.raises(ValueError):
        sla.priority_of(1, bad)


@pytest.mark.parametrize(("priority", "minutes"), [
    ("P1", (15, 240)), ("P2", (60, 480)), ("P3", (240, 1440)), ("P4", (480, 4320)),
])
def test_targets(priority, minutes):
    assert sla.targets(priority) == minutes


@pytest.mark.parametrize("unknown", ["p1", " P1", "P1 ", "P5", "P0", ""])
def test_targets_exact_lookup(unknown):
    with pytest.raises(ValueError):
        sla.targets(unknown)


@pytest.mark.parametrize(("elapsed", "target", "state"), [
    (0, 1, "ok"), (1, 1, "warning"), (2, 1, "breached"),
    (74, 100, "ok"), (75, 100, "warning"), (76, 100, "warning"),
    (11, 15, "ok"), (12, 15, "warning"), (14, 15, "warning"),
    (15, 15, "warning"), (16, 15, "breached"),
    (59, 80, "ok"), (60, 80, "warning"),
    (449, 600, "ok"), (450, 600, "warning"),
])
def test_sla_state_boundaries(elapsed, target, state):
    assert sla.sla_state(elapsed, target) == state


@pytest.mark.parametrize(("elapsed", "target"), [(-1, 1), (0, 0), (1, -1), (-1, 0)])
def test_sla_state_invalid(elapsed, target):
    with pytest.raises(ValueError):
        sla.sla_state(elapsed, target)


def test_opening_closing_weekdays_and_truncation():
    monday = instant("2026-01-05T00:00")
    for day, minute in product(range(7), [0, 479, 480, 481, 659, 959, 960, 961, 1439]):
        now = monday + timedelta(days=day, minutes=minute, seconds=59, microseconds=999999)
        assert sla.is_business_time(now) is (day < 5 and 480 <= minute < 960)


@pytest.mark.parametrize(("start", "minutes", "due"), [
    ("2026-01-05T07:59:59", 0, "2026-01-05T08:00"),
    ("2026-01-05T08:00:35.116", 0, "2026-01-05T08:00"),
    ("2026-01-05T12:13:59.999999", 0, "2026-01-05T12:13"),
    ("2026-01-05T06:00", 1, "2026-01-05T08:01"),
    ("2026-01-05T08:00", 480, "2026-01-05T16:00"),
    ("2026-01-05T08:00", 481, "2026-01-06T08:01"),
    ("2026-01-05T16:00", 0, "2026-01-06T08:00"),
    ("2026-01-09T15:59:59.6", 1, "2026-01-09T16:00"),
    ("2026-01-09T15:59", 2, "2026-01-12T08:01"),
    ("2026-01-09T16:00", 0, "2026-01-12T08:00"),
    ("2026-01-09T23:59", 481, "2026-01-13T08:01"),
    ("2026-01-10T02:00", 0, "2026-01-12T08:00"),
    ("2026-01-11T10:00", 960, "2026-01-13T16:00"),
    ("2026-12-31T15:56", 7, "2027-01-01T08:03"),
])
def test_add_and_inverse(start, minutes, due):
    start, due = instant(start), instant(due)
    assert sla.add_business_minutes(start, minutes) == due
    assert sla.business_minutes_between(start, due) == minutes


@pytest.mark.parametrize(("start", "end", "minutes"), [
    ("2026-01-05T07:00", "2026-01-05T08:00", 0),
    ("2026-01-05T16:00", "2026-01-05T18:00", 0),
    ("2026-01-05T08:00:56.5", "2026-01-05T08:01:01.2", 1),
    ("2026-01-05T08:00:56.5", "2026-01-05T08:00:00.2", 0),
    ("2026-01-05T08:00", "2026-01-05T08:00", 0),
    ("2026-01-05T05:01", "2026-01-05T16:55", 480),
    ("2026-01-09T15:30", "2026-01-12T08:30", 60),
    ("2026-01-09T10:00", "2026-01-13T11:15", 1035),
    ("2026-01-10T08:00", "2026-01-11T15:00", 0),
])
def test_between_windows(start, end, minutes):
    assert sla.business_minutes_between(instant(start), instant(end)) == minutes


def test_invalid_and_maximum_calendar_span():
    monday = instant("2026-01-05T08:00")
    with pytest.raises(ValueError):
        sla.add_business_minutes(monday, -1)
    with pytest.raises(ValueError):
        sla.business_minutes_between(monday, monday - timedelta(minutes=1))
    # 52 complete weeks and Monday–Wednesday, all weekdays included.
    last_day = monday + timedelta(days=366)
    final_close = last_day.replace(hour=16)
    window_total = (52 * 5 + 3) * 480
    assert sla.add_business_minutes(monday, window_total) == final_close
    assert sla.business_minutes_between(monday, final_close) == window_total
    with pytest.raises(ValueError):
        sla.add_business_minutes(monday, window_total + 1)
    with pytest.raises(ValueError):
        sla.business_minutes_between(monday, last_day + timedelta(days=1))


def test_two_week_calendar_against_minute_model():
    start = instant("2026-02-26T15:57")
    step = timedelta(minutes=1)
    # Enumerate open instants instead of duplicating the implementation's windows.
    open_minutes = [start + i * step for i in range(14 * 24 * 60)
                    if (start + i * step).weekday() in range(5)
                    and 8 <= (start + i * step).hour < 16]
    for minutes in [1, 2, 3, 4, 62, 482, 483, 484, 962, 966, 1500, 4000]:
        due = open_minutes[minutes - 1] + step
        assert sla.add_business_minutes(start, minutes) == due
        assert sla.business_minutes_between(start, due) == minutes


def test_escalation_matrix_and_caps():
    no_breach = {"P1": 1, "P2": 1, "P3": 0, "P4": 0}
    breach = {"P1": 3, "P2": 2, "P3": 1, "P4": 1}
    for priority, breached, reopens in product(no_breach, [False, True], [0, 1, 2, 3, 100]):
        base = (breach if breached else no_breach)[priority]
        expected = min(base + (reopens >= 2), 3)
        assert sla.escalation_tier(priority, breached, reopens) == expected
    with pytest.raises(ValueError):
        sla.escalation_tier("P1", False, -1)
    with pytest.raises(ValueError):
        sla.escalation_tier("p1", True, 0)


@pytest.mark.parametrize(("literal", "minutes"), [
    ("1m", 1), ("90m", 90), ("4h", 240), ("2d", 2880), ("1d4h", 1680),
    ("1h30m", 90), ("1h59m", 119), ("1h0m", 60), ("1d0h5m", 1445),
    ("1d25h59m", 2999), ("00d0h60m", 60), ("0h60m", 60), ("60m", 60),
    ("1d59m", 1499), (" \t01h02m\n ", 62), ("0d0h0001m", 1),
])
def test_duration_valid(literal, minutes):
    assert sla.parse_duration(literal) == minutes


@pytest.mark.parametrize("literal", [
    "", " ", "0m", "0h", "0d0h0m", "1.5h", "30m1h", "-5m", "+5m", "1 h",
    "1h 30m", "1H", "1M", "2D", "1", "m", "h1", "1h2h", "1m2m", "1d2d",
    "1h1d", "1h60m", "1d60m", "1d0h60m", "01h00060m", "junk1m", "1m!",
])
def test_duration_invalid(literal):
    with pytest.raises(ValueError):
        sla.parse_duration(literal)

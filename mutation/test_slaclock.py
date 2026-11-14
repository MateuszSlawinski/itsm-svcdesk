# ai-generated: 100% - wrote behavioral boundary tests for the course SLA module and mutation criteria P-29
from datetime import datetime, timedelta

import pytest

from slaclock import (
    add_business_minutes,
    business_minutes_between,
    escalation_tier,
    is_business_time,
    parse_duration,
    priority_of,
    sla_state,
    targets,
)


@pytest.mark.parametrize(
    ("impact", "urgency", "expected"),
    [
        (1, 1, "P1"),
        (1, 2, "P2"),
        (1, 3, "P3"),
        (2, 1, "P2"),
        (2, 2, "P3"),
        (2, 3, "P4"),
        (3, 1, "P3"),
        (3, 2, "P4"),
        (3, 3, "P4"),
    ],
)
def test_priority_matrix(impact, urgency, expected):
    assert priority_of(impact, urgency) == expected


def test_vip_only_raises_priorities_below_p2():
    assert [priority_of(1, 1, True), priority_of(1, 2, True)] == ["P1", "P2"]
    assert [priority_of(1, 3, True), priority_of(3, 3, True)] == ["P2", "P2"]


@pytest.mark.parametrize("value", [0, 4, True, 1.0, "1"])
def test_priority_rejects_non_integer_or_out_of_range_values(value):
    with pytest.raises(ValueError):
        priority_of(value, 1)
    with pytest.raises(ValueError):
        priority_of(1, value)


def test_targets_are_exact_and_return_response_then_resolution():
    assert [targets(priority) for priority in ("P1", "P2", "P3", "P4")] == [
        (15, 240),
        (60, 480),
        (240, 1440),
        (480, 4320),
    ]
    for priority in ("p1", " P1", "P5"):
        with pytest.raises(ValueError):
            targets(priority)


def test_sla_state_boundaries_and_validation():
    assert [sla_state(value, 15) for value in (0, 11, 11.25, 15, 16)] == [
        "ok",
        "ok",
        "warning",
        "warning",
        "breached",
    ]
    assert sla_state(75, 100) == "warning"
    assert sla_state(74, 100) == "ok"
    for elapsed, target in ((-1, 10), (0, 0), (0, -1)):
        with pytest.raises(ValueError):
            sla_state(elapsed, target)


def test_business_time_is_weekday_and_half_open():
    monday = datetime(2026, 3, 2)
    friday = datetime(2026, 3, 6)
    saturday = datetime(2026, 3, 7)
    assert not is_business_time(monday.replace(hour=7, minute=59))
    assert is_business_time(monday.replace(hour=8))
    assert is_business_time(friday.replace(hour=15, minute=59, second=59))
    assert not is_business_time(friday.replace(hour=16))
    assert not is_business_time(saturday.replace(hour=10))


def test_add_business_minutes_handles_opening_closing_and_weekends():
    monday = datetime(2026, 3, 2)
    friday = datetime(2026, 3, 6)
    sunday = datetime(2026, 3, 8)
    assert add_business_minutes(monday.replace(hour=9), 0) == monday.replace(hour=9)
    assert add_business_minutes(monday.replace(hour=7, minute=30), 0) == monday.replace(hour=8)
    assert add_business_minutes(monday.replace(hour=16), 0) == datetime(2026, 3, 3, 8)
    assert add_business_minutes(monday.replace(hour=15, minute=30), 30) == monday.replace(hour=16)
    assert add_business_minutes(friday.replace(hour=15, minute=30), 60) == datetime(
        2026, 3, 9, 8, 30
    )
    assert add_business_minutes(sunday, 60) == datetime(2026, 3, 9, 9)


def test_add_business_minutes_rejects_negative_and_excessive_span():
    with pytest.raises(ValueError):
        add_business_minutes(datetime(2026, 3, 2, 9), -1)
    start = datetime(2026, 1, 5, 8)
    max_span_due = datetime(2027, 1, 6, 16)
    assert add_business_minutes(start, 263 * 8 * 60) == max_span_due
    with pytest.raises(ValueError):
        add_business_minutes(start, 263 * 8 * 60 + 1)


def test_business_minutes_between_uses_half_open_business_windows():
    friday = datetime(2026, 3, 6)
    monday = datetime(2026, 3, 9)
    assert business_minutes_between(friday.replace(hour=15, minute=30), monday.replace(hour=8, minute=30)) == 60
    assert business_minutes_between(monday.replace(hour=8), monday.replace(hour=16)) == 480
    assert business_minutes_between(monday.replace(hour=16), monday.replace(hour=16)) == 0
    assert business_minutes_between(monday.replace(hour=8), monday.replace(hour=8)) == 0


def test_business_minutes_between_rejects_reverse_and_excessive_span():
    start = datetime(2026, 3, 2, 9)
    with pytest.raises(ValueError):
        business_minutes_between(start, start - timedelta(minutes=1))
    boundary_start = datetime(2026, 1, 5, 8)
    boundary_end = datetime(2027, 1, 6, 16)
    assert business_minutes_between(boundary_start, boundary_end) == 263 * 8 * 60
    with pytest.raises(ValueError):
        business_minutes_between(start, start + timedelta(days=367))


def test_datetime_seconds_and_microseconds_are_ignored():
    monday = datetime(2026, 3, 2, 9)
    precise = monday.replace(minute=17, second=45, microsecond=123456)
    assert add_business_minutes(precise, 1) == monday.replace(minute=18)
    assert business_minutes_between(precise, precise + timedelta(minutes=1)) == 1


def test_business_time_operations_are_inverse_at_clock_boundaries():
    start = datetime(2026, 3, 6, 15, 30)
    due = add_business_minutes(start, 490)
    assert business_minutes_between(start, due) == 490


def test_escalation_tiers_cover_priority_breach_reopen_and_cap():
    assert [escalation_tier(priority, False, 0) for priority in ("P1", "P2", "P3", "P4")] == [
        1,
        1,
        0,
        0,
    ]
    assert escalation_tier("P1", True, 0) == 3
    assert escalation_tier("P2", True, 0) == 2
    assert escalation_tier("P3", True, 0) == 1
    assert escalation_tier("P4", False, 1) == 0
    assert escalation_tier("P4", False, 2) == 1
    assert escalation_tier("P3", True, 2) == 2
    assert escalation_tier("P1", True, 2) == 3
    for priority, reopens in (("P5", 0), ("P1", -1)):
        with pytest.raises(ValueError):
            escalation_tier(priority, False, reopens)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("90m", 90),
        ("4h", 240),
        ("1h30m", 90),
        ("2d", 2880),
        ("1d4h", 1680),
        ("1d0h5m", 1445),
        ("60m", 60),
        (" 1h59m ", 119),
        ("0h60m", 60),
    ],
)
def test_parse_duration_accepts_documented_forms(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize(
    "text",
    ["", "0m", "1.5h", "30m1h", "-5m", "1 h", "1h60m", "1d60m", "1h1h", "1H"],
)
def test_parse_duration_rejects_invalid_forms(text):
    with pytest.raises(ValueError):
        parse_duration(text)

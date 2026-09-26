# ai-generated: 90% - HTTP tests cover the Lab 2 API and published practice set
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


BASE_URL = os.environ.get("SVCDESK_URL", "http://127.0.0.1:8080")
WINDOW = {"from": "2026-09-01T00:00:00Z", "to": "2026-09-22T00:00:00Z"}
FIXTURE_PATH = Path("/app/fixtures/events-practice.jsonl")
EXPECTED_PATH = Path("/app/fixtures/metrics-practice.json")


def request_json(path, body=None, method=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    request = Request(
        BASE_URL + path,
        data=data,
        method=method or ("POST" if data is not None else "GET"),
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


@pytest.fixture(scope="module")
def practice_events():
    return [json.loads(line) for line in FIXTURE_PATH.read_text().splitlines() if line.strip()]


def score(events, window=None):
    return request_json("/dora/metrics", {"window": window or WINDOW, "events": events})


def test_health():
    status, result = request_json("/health")
    assert status == 200
    assert result == {"status": "ok", "service": "svcdesk"}


def test_practice_fixture_matches_published_values(practice_events):
    status, result = score(practice_events)
    expected = json.loads(EXPECTED_PATH.read_text())
    assert status == 200
    assert result == expected


def test_metrics_are_deterministic(practice_events):
    assert score(practice_events) == score(practice_events)


def test_metrics_ignore_event_order(practice_events):
    assert score(practice_events) == score(list(reversed(practice_events)))


def test_duplicate_event_ids_are_counted_once(practice_events):
    duplicated = practice_events + practice_events
    assert score(duplicated) == score(practice_events)


def test_empty_log_returns_empty_metrics():
    status, result = score([])
    assert status == 200
    assert result["deployment_frequency_per_day"] == 0.0
    assert result["change_lead_time_seconds_p50"] is None
    assert result["failed_deployment_recovery_time_seconds_p50"] is None
    assert result["change_fail_rate"] is None
    assert result["deployment_rework_rate"] is None
    assert all(value == 0 for group in (result["counts"], result["anomalies"]) for value in group.values())


def test_non_increasing_window_is_rejected():
    status, result = score([], {"from": WINDOW["to"], "to": WINDOW["from"]})
    assert status in (400, 422)
    assert "error" in result


def test_missing_window_is_rejected():
    status, result = request_json("/dora/metrics", {"events": []})
    assert status in (400, 422)
    assert "error" in result


def test_missing_events_is_rejected():
    status, result = request_json("/dora/metrics", {"window": WINDOW})
    assert status in (400, 422)
    assert "error" in result


def test_non_array_events_are_rejected():
    status, result = request_json("/dora/metrics", {"window": WINDOW, "events": {}})
    assert status in (400, 422)
    assert "error" in result


def test_unknown_revert_sha_is_rejected():
    events = [{
        "event_id": "c-revert",
        "type": "commit",
        "at": "2026-09-01T00:00:00Z",
        "sha": "sha-revert",
        "branch": "main",
        "change_id": None,
        "reverts": "missing",
    }]
    status, result = score(events)
    assert status in (400, 422)
    assert "error" in result


def test_ticket_event_stream_contains_lifecycle_events():
    clock = "2026-10-14T10:00:00Z"
    status, ticket = request_json(
        "/tickets",
        {
            "title": "Lab 2 event export test",
            "reporter": {"name": "Test Runner"},
            "impact": 2,
            "urgency": 2,
        },
        headers={"X-Test-Clock": clock},
    )
    assert status == 201
    ticket_id = ticket["id"]
    for action, at in (
        ("ack", "2026-10-14T10:01:00Z"),
        ("start", "2026-10-14T10:02:00Z"),
        ("resolve", "2026-10-14T10:03:00Z"),
    ):
        status, _ = request_json(
            f"/tickets/{ticket_id}/{action}",
            {},
            headers={"X-Test-Clock": at},
        )
        assert status == 200

    status, events = request_json("/dora/ticket-events")
    assert status == 200
    own_events = [event for event in events if event["ticket_id"] == ticket_id]
    assert [event["phase"] for event in own_events] == ["created", "acknowledged", "resolved"]
    assert [event["state"] for event in own_events] == ["new", "acknowledged", "resolved"]


def test_ticket_event_stream_is_sorted():
    status, events = request_json("/dora/ticket-events")
    assert status == 200
    keys = [(event["at"], event["ticket_id"]) for event in events]
    assert keys == sorted(keys)

"""Item 4: first-session funnel + D1/D7 retention (cohort by user×day)."""
from datetime import datetime, timedelta, timezone

from services.rebirth_funnel import build_report, funnel_summary, retention_cohorts


def _ev(user, etype, created_at, **payload):
    return {"user_id": user, "event_type": etype, "created_at": created_at, "payload": payload}


def test_funnel_completion_abandon_and_winrate():
    ts = "2026-06-01T10:00:00+00:00"
    events = [
        _ev("u1", "match_started", ts, match_id="m1"),
        _ev("u1", "card_played", ts, match_id="m1"),
        _ev("u1", "attack", ts, match_id="m1", is_finished=True, winner="player", match_duration_ms=120000),
        _ev("u2", "match_started", ts, match_id="m2"),
        _ev("u2", "match_abandoned", ts, match_id="m2", abandon_turn=3),
    ]
    summary = funnel_summary(events)
    assert summary["matches_started"] == 2
    assert summary["matches_finished"] == 1
    assert summary["match_completion_rate"] == 0.5
    assert summary["first_match_completion_rate"] == 0.5
    assert summary["abandon_by_turn"] == {3: 1}
    assert summary["wins_player"] == 1 and summary["wins_bot"] == 0
    assert summary["median_duration_ms"] == 120000


def test_retention_d1_d7_by_cohort():
    base = datetime(2026, 6, 1, tzinfo=timezone.utc)

    def iso(days):
        return (base + timedelta(days=days)).isoformat()

    events = [
        _ev("u1", "x", iso(0)), _ev("u1", "x", iso(1)), _ev("u1", "x", iso(7)),  # d1 + d7
        _ev("u2", "x", iso(0)),  # neither
        {"user_id": None, "event_type": "x", "created_at": iso(0), "payload": {}},  # guest ignored
    ]
    retention = retention_cohorts(events)
    assert retention["tracked_users"] == 2
    assert retention["d1_retention"] == 0.5
    assert retention["d7_retention"] == 0.5
    assert retention["cohorts"]["2026-06-01"] == {"users": 2, "d1": 1, "d7": 1}


def test_build_report_shape():
    report = build_report([])
    assert report["events_analyzed"] == 0
    assert "funnel" in report and "retention" in report
    assert report["funnel"]["match_completion_rate"] == 0.0

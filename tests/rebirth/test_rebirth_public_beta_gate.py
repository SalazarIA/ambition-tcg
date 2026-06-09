from datetime import datetime, timedelta, timezone

from services.rebirth_public_beta_gate import public_beta_gate_report


def _event(event_id, event_type, *, user_id=1, created_at=None, payload=None):
    return {
        "id": event_id,
        "user_id": user_id,
        "event_type": event_type,
        "created_at": (created_at or datetime(2026, 6, 9, 12, tzinfo=timezone.utc)).isoformat(timespec="seconds"),
        "payload": payload or {},
    }


def _passing_live_balance():
    return {
        "human_match_gate": {
            "observed_finished_matches": 500,
            "required_finished_matches": 500,
        },
        "flags": [],
    }


def test_public_beta_gate_blocks_without_real_samples():
    report = public_beta_gate_report([], live_balance={"human_match_gate": {"observed_finished_matches": 0, "required_finished_matches": 500}})

    assert report["ready"] is False
    assert "telemetry_active" in report["blockers"]
    assert "human_telemetry_sample" in report["blockers"]
    assert {check["key"]: check["state"] for check in report["checks"]}["crash_rate"] == "pending"


def test_public_beta_gate_passes_only_when_all_kpis_are_met():
    now = datetime(2026, 6, 9, 12, tzinfo=timezone.utc)
    events = []
    next_id = 1

    for user_id in range(1, 21):
        first_seen = now - timedelta(days=8)
        events.append(_event(next_id, "first_session_action", user_id=user_id, created_at=first_seen))
        next_id += 1
        if user_id <= 8:
            events.append(_event(next_id, "first_session_action", user_id=user_id, created_at=now - timedelta(days=6)))
            next_id += 1
        if user_id <= 4:
            events.append(_event(next_id, "first_session_action", user_id=user_id, created_at=now))
            next_id += 1

    for user_id in range(1, 11):
        match_id = f"first-{user_id}"
        events.append(_event(next_id, "tutorial_step_viewed", user_id=user_id, payload={"step": 1, "match_id": match_id}))
        next_id += 1
        events.append(_event(next_id, "match_started", user_id=user_id, payload={"match_id": match_id, "first_duel": True}))
        next_id += 1
        if user_id <= 8:
            events.append(_event(next_id, "tutorial_step_completed", user_id=user_id, payload={"step": 4}))
            next_id += 1
            events.append(
                _event(
                    next_id,
                    "match_finished",
                    user_id=user_id,
                    payload={"match_id": match_id, "first_duel": True, "is_finished": True, "winner": "player"},
                )
            )
            next_id += 1

    for index in range(120):
        user_id = (index % 20) + 1
        match_id = f"sample-{index}"
        events.append(_event(next_id, "match_started", user_id=user_id, payload={"match_id": match_id, "first_duel": False}))
        next_id += 1
        events.append(
            _event(
                next_id,
                "match_finished",
                user_id=user_id,
                payload={"match_id": match_id, "is_finished": True, "winner": "player" if index % 2 else "bot"},
            )
        )
        next_id += 1

    events.extend(
        [
            _event(next_id + 1, "match_abandoned", payload={"match_id": "abandoned"}),
            _event(next_id + 2, "match_won", payload={"match_id": "won"}),
            _event(next_id + 3, "match_lost", payload={"match_id": "lost"}),
            _event(next_id + 4, "card_played", payload={"match_id": "won", "card_id": "card_001"}),
            _event(next_id + 5, "card_evolved", payload={"match_id": "won", "card_id": "card_001"}),
            _event(next_id + 6, "field_pair_fused", payload={"match_id": "won"}),
        ]
    )

    report = public_beta_gate_report(events, live_balance=_passing_live_balance(), now=now)
    states = {check["key"]: check["state"] for check in report["checks"]}

    assert report["ready"] is True
    assert report["blockers"] == []
    assert states["tutorial_completion"] == "passed"
    assert states["first_match_completion"] == "passed"
    assert states["d1_retention"] == "passed"
    assert states["d7_retention"] == "passed"
    assert states["crash_rate"] == "passed"
    assert states["healthy_balance"] == "passed"

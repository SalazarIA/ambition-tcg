from datetime import datetime, timedelta, timezone

from services.rebirth_public_beta_gate import public_beta_gate_payload, public_beta_gate_report


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
    assert "cohort_window" in report["blockers"]
    assert "telemetry_active" in report["blockers"]
    assert "human_telemetry_sample" in report["blockers"]
    assert {check["key"]: check["state"] for check in report["checks"]}["crash_rate"] == "pending"


def test_public_beta_gate_payload_passes_since_to_repository():
    class Repo:
        def __init__(self):
            self.calls = []

        def query_telemetry_events(self, *, limit=None, since=None):
            self.calls.append({"limit": limit, "since": since})
            return []

    repo = Repo()
    report = public_beta_gate_payload(repo, limit=250, since="2026-06-01T00:00:00+00:00", release_version="v-test")

    assert repo.calls == [{"limit": 250, "since": "2026-06-01T00:00:00+00:00"}]
    assert report["release_version"] == "v-test"
    assert report["since"] == "2026-06-01T00:00:00+00:00"
    assert report["ready"] is False


def test_public_beta_gate_blocks_when_cohort_window_is_missing():
    report = public_beta_gate_report(
        [
            _event(1, "match_started", payload={"match_id": "m1"}),
            _event(2, "match_finished", payload={"match_id": "m1", "is_finished": True, "winner": "player"}),
            _event(3, "match_abandoned", payload={"match_id": "m2"}),
            _event(4, "match_won", payload={"match_id": "m1"}),
            _event(5, "match_lost", payload={"match_id": "m3"}),
            _event(6, "card_played", payload={"match_id": "m1", "card_id": "card_001"}),
            _event(7, "card_evolved", payload={"match_id": "m1", "card_id": "card_001"}),
            _event(8, "field_pair_fused", payload={"match_id": "m1"}),
        ],
        live_balance=_passing_live_balance(),
    )

    assert report["ready"] is False
    assert {check["key"]: check["state"] for check in report["checks"]}["cohort_window"] == "blocked"
    assert "cohort_window" in report["blockers"]


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

    report = public_beta_gate_report(
        events,
        live_balance=_passing_live_balance(),
        now=now,
        since="2026-06-01T00:00:00+00:00",
    )
    states = {check["key"]: check["state"] for check in report["checks"]}

    assert report["ready"] is True
    assert report["blockers"] == []
    assert states["cohort_window"] == "passed"
    assert states["tutorial_completion"] == "passed"
    assert states["first_match_completion"] == "passed"
    assert states["d1_retention"] == "passed"
    assert states["d7_retention"] == "passed"
    assert states["crash_rate"] == "passed"
    assert states["healthy_balance"] == "passed"

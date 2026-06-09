from datetime import datetime, timedelta, timezone

from services.rebirth_async_competition import async_competition_payload
from services.rebirth_beta_ops import beta_dashboard_payload
from services.rebirth_content_pipeline import content_pipeline_report
from services.rebirth_engine import RebirthError, declare_attack, next_turn, play_card, start_match
from services.rebirth_first_session import first_session_plan
from services.rebirth_live_balance import live_balance_payload, live_balance_report
from services.rebirth_persistence import RebirthRepository


def _register(client, username="aaa_user", email="aaa@example.com"):
    response = client.post(
        "/api/rebirth/auth/register",
        json={"username": username, "email": email, "password": "password123"},
    )
    assert response.status_code == 200
    return response.get_json()["account"]["user"]


def _finish_engine_match(seed="aaa-async-match"):
    match = start_match(seed=seed, bot_profile_id="novice")
    for _ in range(90):
        if match.get("is_finished"):
            return match
        if match.get("phase") == "result":
            next_turn(match)
            continue
        acted = False
        field = match["player"].get("battlefield") or []
        energy = int(match["player"].get("energy", 0) or 0)
        for card in list(match["player"].get("hand") or []):
            if card.get("card_type", card.get("type")) != "MONSTER":
                continue
            if int(card.get("cost", 0) or 0) > energy or len(field) >= 3:
                continue
            try:
                play_card(match, card_instance_id=card["instance_id"])
                acted = True
                break
            except RebirthError:
                continue
        if acted:
            continue
        for attacker in list(match["player"].get("battlefield") or []):
            if attacker.get("exhausted") or attacker.get("has_attacked") or attacker.get("has_acted"):
                continue
            target = (match["bot"].get("battlefield") or [None])[0]
            try:
                declare_attack(
                    match,
                    attacker_instance_id=attacker["instance_id"],
                    target_instance_id=(target or {}).get("instance_id"),
                )
                acted = True
                break
            except RebirthError:
                continue
        if not acted:
            next_turn(match)
    raise AssertionError("expected deterministic helper to finish match")


def _telemetry_event(event_id, event_type, *, user_id=1, created_at=None, payload=None):
    return {
        "id": event_id,
        "user_id": user_id,
        "event_type": event_type,
        "created_at": (created_at or datetime(2026, 6, 9, 12, tzinfo=timezone.utc)).isoformat(timespec="seconds"),
        "payload": payload or {},
    }


def test_first_session_plan_is_python_owned():
    plan = first_session_plan(
        account={"authenticated": True},
        progression={"clashes": 0, "tutorial_complete": False, "boosters_opened": 0},
        release_version="test-release",
    )

    assert plan["version"] == "first-session-v1"
    assert plan["should_guide_match"] is True
    assert plan["estimated_minutes"] == 10
    assert plan["arena_tutorial_steps"][0]["target"] == ".rb-hand .rb-mini-card"
    assert len(plan["arena_tutorial_steps"]) == 8
    assert "Funda no campo" in [step["title"] for step in plan["arena_tutorial_steps"]]
    assert [action["key"] for action in plan["actions"]][-1] == "tune_deck"


def test_content_pipeline_validates_catalog_and_starter_deck():
    report = content_pipeline_report()

    assert report["version"] == "content-pipeline-v1"
    assert report["ok"] is True
    assert report["card_count"] >= 100
    assert report["starter_deck_ok"] is True
    assert report["art"]["coverage"] == 1.0


def test_live_balance_report_requires_real_human_sample_before_balance_claims():
    events = [
        {
            "id": 1,
            "event_type": "match_finished",
            "payload": {
                "match_id": "m1",
                "is_finished": True,
                "winner": "player",
                "turn": 12,
                "bot_profile_id": "defensive",
                "rebirth_release_version": "v-test",
                "match_duration_ms": 42000,
                "player_deck_signature": "deck-alpha",
            },
        },
        {
            "id": 2,
            "event_type": "card_played",
            "payload": {"match_id": "m1", "card_id": "card_001", "cohort": "account"},
        },
        {
            "id": 3,
            "event_type": "card_evolved",
            "payload": {"match_id": "m1", "card_id": "card_001", "cohort": "account"},
        },
        {
            "id": 4,
            "event_type": "field_pair_fused",
            "payload": {"match_id": "m1", "cohort": "account"},
        },
        {
            "id": 5,
            "event_type": "match_won",
            "payload": {"match_id": "m1", "winner": "player", "cohort": "account"},
        },
    ]
    report = live_balance_report(events, release_version="v-test")

    assert report["version"] == "live-balance-v1"
    assert report["human_match_gate"]["state"] == "insufficient_sample"
    assert "needs_human_telemetry" in report["flags"]
    assert report["card_usage"][0]["card_id"] == "card_001"
    assert report["deck_usage"][0]["deck_signature"] == "deck-alpha"
    assert report["evolution_usage"][0]["card_id"] == "card_001"
    assert report["fusion_count"] == 1
    assert report["terminal_events"]["wins"] == 1
    assert report["overall"]["average_match_duration_ms"] == 42000
    assert report["release_versions"]["v-test"] == 1


def test_release_dashboard_and_live_balance_payload_scope_to_since():
    class Repo:
        def __init__(self):
            self.calls = []

        def query_telemetry_events(self, *, limit=None, since=None):
            self.calls.append({"limit": limit, "since": since})
            return []

    repo = Repo()
    dashboard = beta_dashboard_payload(repo, limit=125, since="2026-06-01T00:00:00+00:00")
    balance = live_balance_payload(repo, limit=250, since="2026-06-01T00:00:00+00:00", release_version="v-test")

    assert repo.calls == [
        {"limit": 125, "since": "2026-06-01T00:00:00+00:00"},
        {"limit": 250, "since": "2026-06-01T00:00:00+00:00"},
    ]
    assert dashboard["since"] == "2026-06-01T00:00:00+00:00"
    assert balance["since"] == "2026-06-01T00:00:00+00:00"


def test_beta_dashboard_uses_matured_cohort_retention_cards():
    now = datetime(2026, 6, 9, 12, tzinfo=timezone.utc)
    first_seen = now - timedelta(days=8)
    events = [
        _telemetry_event(1, "first_session_action", user_id=1, created_at=first_seen),
        _telemetry_event(2, "first_session_action", user_id=1, created_at=first_seen + timedelta(days=1)),
        _telemetry_event(3, "first_session_action", user_id=1, created_at=first_seen + timedelta(days=7)),
        _telemetry_event(4, "first_session_action", user_id=2, created_at=first_seen),
        _telemetry_event(5, "first_session_action", user_id=3, created_at=now),
    ]

    class Repo:
        def query_telemetry_events(self, *, limit=None, since=None):
            return events

    dashboard = beta_dashboard_payload(Repo(), since="2026-06-01T00:00:00+00:00")
    cards = {card["label"]: card for card in dashboard["cards"]}

    assert "D1 ativos" not in cards
    assert cards["D1 retenção"]["value"] == "50%"
    assert cards["D1 retenção"]["state"] == "passed"
    assert cards["D1 retenção"]["target"] == ">=35%"
    assert cards["D7 retenção"]["value"] == "50%"
    assert cards["D7 retenção"]["state"] == "passed"
    assert cards["D7 retenção"]["target"] == ">=20%"
    assert dashboard["public_beta_gate"]["checks"][4]["key"] == "d1_retention"


def test_guest_can_resume_active_match_from_session(client):
    started = client.post("/api/rebirth/start", json={"seed": "guest-resume-contract"})
    state = started.get_json()["state"]

    resumed = client.post("/api/rebirth/resume", json={"match_id": state["match_id"]})
    payload = resumed.get_json()

    assert resumed.status_code == 200
    assert payload["resumed"] is True
    assert payload["reconnect"]["scope"] == "guest_session_memory"
    assert payload["state"]["match_id"] == state["match_id"]


def test_rebirth_studio_foundation_endpoints(client):
    endpoints = {
        "/api/rebirth/first-session": "first_session",
        "/api/rebirth/content/validate": "content_pipeline",
        "/api/rebirth/balance/telemetry": "live_balance",
    }

    for path, key in endpoints.items():
        response = client.get(path)
        payload = response.get_json()
        assert response.status_code == 200
        assert payload["ok"] is True
        assert key in payload


def test_async_competition_share_is_verified_and_privacy_safe(client, flask_app):
    user = _register(client, username="async_user", email="async@example.com")
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    match = _finish_engine_match()
    match["owner_user_id"] = user["id"]
    repo.upsert_match_history(user["id"], match)

    service_payload = async_competition_payload(match)
    response = client.get(f"/api/rebirth/async/share/{match['match_id']}")
    payload = response.get_json()["async_competition"]

    assert service_payload["share"]["verified"] is True
    assert response.status_code == 200
    assert payload["share"]["verified"] is True
    assert payload["share"]["privacy"]["contains_email"] is False
    assert payload["ghost"]["mode"] == "ghost_challenge"

import json

import pytest

import app as ambition_app
from services.rebirth_persistence import RebirthPersistenceError, RebirthRepository


def test_home_rebirth_and_health_routes_return_200(client):
    home = client.get("/")
    rebirth = client.get("/rebirth")
    health = client.get("/health")

    assert home.status_code == 200
    assert "Duelos, coleção e mercado em uma mesa viva." in home.get_data(as_text=True)
    assert rebirth.status_code == 200
    assert "data-rebirth-app" in rebirth.get_data(as_text=True)
    assert health.status_code == 200
    assert health.get_json()["product"] == "Ambitionz Rebirth"


def test_rebirth_visual_contract_text_assets_and_ids(client):
    response = client.get("/rebirth")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "css/rebirth.css" in body
    assert "js/rebirth.js" in body

    for text in (
        "Invocar",
        "Encerrar turno",
        "Selecione um monstro",
        "Duplicata encontrada",
        "Evoluir",
        "Nova partida",
        "Combine duplicatas para evoluir",
        "rb-hero-portrait",
        "rb-mana-coins",
    ):
        assert text in body

    for element_id in (
        "player-hp",
        "turn-number",
        "bot-hp",
        "bot-card",
        "bot-battlefield",
        "player-battlefield",
        "focus-card",
        "evolution-panel",
        "evolution-name",
        "evolve-button",
        "player-hand",
        "hand-count",
        "player-hero-name",
        "player-mana-coins",
        "bot-hero-name",
        "bot-mana-coins",
        "play-button",
        "next-turn-button",
        "result-panel",
        "result-label",
        "result-title",
        "result-copy",
        "ability-events",
        "reward-panel",
        "bot-profile-label",
        "phase-label",
        "turn-log",
    ):
        assert f'id="{element_id}"' in body


def test_start_api_returns_clear_json_state(client):
    response = client.post("/api/rebirth/start", json={"seed": "routes-start"})
    payload = response.get_json()

    assert response.status_code == 200
    assert response.is_json
    assert payload["ok"] is True
    assert "result" in payload
    assert payload["state"]["match_id"].startswith("rebirth-")
    assert payload["state"]["player"]["hp"] == 30
    assert payload["state"]["player"]["max_hp"] == 30
    assert len(payload["state"]["player"]["hand"]) == 5
    assert payload["state"]["bot"]["hand_count"] == 5
    assert payload["state"]["bot_profile"]["id"] in {"defensive", "aggressive", "opportunist"}


def test_guest_wallet_api_returns_zero_balance_without_console_error(client):
    response = client.get("/api/rebirth/wallet")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["wallet"]["GOLD"] == 0
    assert payload["wallet"]["COINZ"] == 0
    assert payload["wallet"]["guest"] is True


def test_authenticated_match_state_uses_single_repository(client):
    register = client.post(
        "/api/rebirth/auth/register",
        json={
            "username": "RoutePilot",
            "email": "route-pilot@example.com",
            "password": "correct-horse-battery",
        },
    )
    assert register.status_code == 200

    started = client.post("/api/rebirth/start", json={"seed": "routes-single-source"})
    state = started.get_json()["state"]
    persisted = client.get(f"/api/rebirth/match-state/{state['match_id']}")

    assert started.status_code == 200
    assert persisted.status_code == 200
    assert persisted.get_json()["state"]["match_id"] == state["match_id"]

    ambition_app.MATCH_STORE.clear()
    explicit_resume = client.post("/api/rebirth/resume", json={"match_id": state["match_id"]})
    assert explicit_resume.status_code == 200
    assert explicit_resume.get_json()["resumed"] is True
    assert explicit_resume.get_json()["state"]["match_id"] == state["match_id"]

    ambition_app.MATCH_STORE.clear()
    resumed = client.post("/api/rebirth/next-turn", json={"match_id": state["match_id"]})
    resumed_state = resumed.get_json()["state"]

    assert resumed.status_code == 200
    assert resumed_state["match_id"] == state["match_id"]
    assert resumed_state["turn"] == 2


def test_shop_survives_market_read_failure(client, monkeypatch):
    def broken_market_read(*_args, **_kwargs):
        raise RebirthPersistenceError("market failed", "database_read_failed", status=500)

    monkeypatch.setattr("services.rebirth_persistence.RebirthRepository.market_offers", broken_market_read)

    page = client.get("/rebirth/shop")
    api = client.get("/api/rebirth/shop")
    payload = api.get_json()

    assert page.status_code == 200
    assert "Loja &amp; Mercado" in page.get_data(as_text=True)
    assert api.status_code == 200
    assert payload["ok"] is True
    assert payload["shop"]["market"]["offers"] == []
    assert payload["shop"]["warnings"][0]["surface"] == "market"


def test_shop_route_is_server_rendered_with_native_nav(client):
    response = client.get("/rebirth/shop")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert 'href="/rebirth/shop"' in body
    assert 'data-rebirth-market-offers' in body
    assert 'js/rebirth_product.js' in body


def test_play_card_api_blocks_first_turn_direct_damage_until_bot_responds(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-play"})
    state = start.get_json()["state"]
    card = next(card for card in state["player"]["hand"] if card["id"] == "card_001")

    response = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": card["instance_id"]},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["state"]["phase"] == "choose"
    assert payload["state"]["result"]["outcome"] == "Summon"
    assert payload["state"]["player"]["battlefield"][0]["id"] == "card_001"
    assert payload["state"]["last_clash"] is None
    assert payload["match_reward"] is None

    # O bot ainda não respondeu no turno inicial; dano direto não pode furar
    # essa janela sem defesa.
    assert payload["state"]["bot"]["battlefield"] == []
    attack = client.post(
        "/api/rebirth/attack",
        json={
            "match_id": payload["state"]["match_id"],
            "attacker_instance_id": payload["state"]["player"]["battlefield"][0]["instance_id"],
        },
    )
    attack_payload = attack.get_json()

    assert attack.status_code == 409
    assert attack_payload["ok"] is False
    assert attack_payload["error"]["code"] == "first_turn_direct_attack_blocked"

    bot_turn = client.post("/api/rebirth/next-turn", json={"match_id": payload["state"]["match_id"]})
    after_bot = bot_turn.get_json()["state"]
    assert bot_turn.status_code == 200
    assert after_bot["bot"]["hp"] == 30
    assert after_bot["bot"]["battlefield"]

    clash = client.post(
        "/api/rebirth/attack",
        json={
            "match_id": after_bot["match_id"],
            "attacker_instance_id": after_bot["player"]["battlefield"][0]["instance_id"],
            "target_instance_id": after_bot["bot"]["battlefield"][0]["instance_id"],
        },
    )
    clash_payload = clash.get_json()
    assert clash.status_code == 200
    assert clash_payload["ok"] is True
    assert clash_payload["state"]["last_clash"]["player_card"]["id"] == "card_001"
    assert clash_payload["state"]["result"]["outcome"] in {"Victory", "Defeat", "Clash"}
    if not clash_payload["state"]["is_finished"]:
        assert clash_payload["match_reward"] is None


def test_guest_match_actions_record_product_telemetry_without_false_reward(client, flask_app):
    state = client.post("/api/rebirth/start", json={"seed": "telemetry-guest"}).get_json()["state"]
    card = next(card for card in state["player"]["hand"] if int(card.get("cost", 0)) <= state["player"]["energy"])
    played = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": card["instance_id"]},
    ).get_json()
    abandoned = client.post(
        "/api/rebirth/telemetry",
        json={"match_id": state["match_id"], "event_type": "match_abandoned", "reason": "qa"},
    )

    assert played["match_reward"] is None
    assert abandoned.status_code == 200
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    with repo.connect() as db:
        rows = db.execute(
            "SELECT event_type, event_json FROM telemetry_events ORDER BY id"
        ).fetchall()
    event_types = [row["event_type"] for row in rows]
    assert event_types == ["match_started", "card_played", "match_abandoned"]
    telemetry = json.loads(rows[-1]["event_json"])
    assert telemetry["match_id"] == state["match_id"]
    assert "decision_elapsed_ms" in telemetry


def test_play_card_api_accepts_explicit_monster_slot(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-play-slot"})
    state = start.get_json()["state"]
    card = next(card for card in state["player"]["hand"] if card["id"] == "card_001")

    response = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": card["instance_id"], "field_slot": 1},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    # field_slot=1 → card lands in slot 1, slots 0 and 2 stay empty.
    assert payload["state"]["player_field"][0] is None
    assert payload["state"]["player_field"][1]["instance_id"] == card["instance_id"]
    assert payload["state"]["player_field"][2] is None
    assert payload["state"]["player"]["battlefield"][0]["field_slot"] == 1


@pytest.mark.parametrize("path", ["/api/rebirth/play-card", "/api/rebirth/attack"])
@pytest.mark.parametrize("field", ["exhausted", "has_attacked", "has_acted"])
def test_combat_routes_reject_client_authored_status_fields(client, path, field):
    state = client.post("/api/rebirth/start", json={"seed": f"status-{field}"}).get_json()["state"]

    response = client.post(path, json={"match_id": state["match_id"], field: False})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "authoritative_state_violation"


def test_evolve_api_combines_duplicate(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-evolve"})
    state = start.get_json()["state"]

    response = client.post(
        "/api/rebirth/evolve",
        json={"match_id": state["match_id"], "card_id": "card_001"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["evolved"]["id"] == "card_011"
    assert payload["state"]["player"]["hand"][0]["id"] == "card_011"


def test_next_turn_api_advances_after_result(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-next"})
    state = start.get_json()["state"]
    card = state["player"]["hand"][0]
    played = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": card["instance_id"]},
    )
    after_play = played.get_json()["state"]

    response = client.post("/api/rebirth/next-turn", json={"match_id": after_play["match_id"]})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["state"]["turn"] == 2
    assert payload["state"]["phase"] == "choose"
    assert payload["state"]["player"]["max_energy"] == 2
    assert payload["state"]["player"]["battlefield"]


def test_invalid_api_returns_json_error(client):
    response = client.post(
        "/api/rebirth/play-card",
        json={"match_id": "missing", "card_id": "card_001"},
    )
    payload = response.get_json()

    assert response.status_code == 404
    assert payload["ok"] is False
    assert payload["error"]["code"] == "missing_match"


def test_expected_action_errors_do_not_return_500(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-errors"})
    state = start.get_json()["state"]

    missing_match = client.post(
        "/api/rebirth/play-card",
        json={"match_id": "missing", "card_id": "card_001"},
    )
    malformed = client.post(
        "/api/rebirth/play-card",
        data="[",
        content_type="application/json",
    )
    invalid_card = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": "not-in-hand"},
    )
    duplicate = client.post(
        "/api/rebirth/evolve",
        json={"match_id": state["match_id"], "card_id": "card_002"},
    )
    invalid_attack = client.post(
        "/api/rebirth/attack",
        json={"match_id": state["match_id"]},
    )

    expected = [
        (missing_match, 404, "missing_match"),
        (malformed, 400, "malformed_request"),
        (invalid_card, 400, "invalid_card"),
        (duplicate, 400, "duplicate_not_available"),
        (invalid_attack, 400, "missing_attacker"),
    ]
    for response, status, code in expected:
        payload = response.get_json()
        assert response.status_code == status
        assert response.status_code != 500
        assert payload["ok"] is False
        assert payload["error"]["code"] == code


def test_legacy_routes_redirect_or_report_retired(client):
    arena = client.get("/arena")
    legacy_api = client.post("/api/ascension/start", json={})

    assert arena.status_code == 302
    assert arena.headers["Location"] == "/rebirth"
    assert legacy_api.status_code == 410
    assert legacy_api.get_json()["error"]["code"] == "legacy_disabled"

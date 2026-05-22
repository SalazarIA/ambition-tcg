import app as ambition_app
from services.rebirth_persistence import RebirthPersistenceError


def test_home_rebirth_and_health_routes_return_200(client):
    home = client.get("/")
    rebirth = client.get("/rebirth")
    health = client.get("/health")

    assert home.status_code == 200
    assert "Duelos, colecao e mercado em uma mesa viva." in home.get_data(as_text=True)
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
        "Build field",
        "Pick target",
        "Break guard",
        "Combine duplicates",
        "Evolve monsters",
        "Win the duel",
        "Play Rebirth",
        "New Match",
        "Summon",
        "Battle Zone",
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


def test_start_api_survives_async_live_state_write_failure(client, monkeypatch):
    async def broken_save_match_state(*_args, **_kwargs):
        raise RebirthPersistenceError("write failed", "database_write_failed", status=500)

    register = client.post(
        "/api/rebirth/auth/register",
        json={
            "username": "RoutePilot",
            "email": "route-pilot@example.com",
            "password": "correct-horse-battery",
        },
    )
    assert register.status_code == 200

    monkeypatch.setattr(ambition_app, "async_database_url", lambda: "postgresql+asyncpg://render/rebirth")
    monkeypatch.setattr(ambition_app, "save_match_state", broken_save_match_state)

    response = client.post("/api/rebirth/start", json={"seed": "routes-persist-degrade"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["state"]["match_id"].startswith("rebirth-")


def test_shop_survives_async_market_read_failure(client, monkeypatch):
    async def broken_market_read(*_args, **_kwargs):
        raise RebirthPersistenceError("market failed", "database_read_failed", status=500)

    monkeypatch.setattr(ambition_app, "async_database_url", lambda: "postgresql+asyncpg://render/rebirth")
    monkeypatch.setattr(ambition_app, "async_active_market_offers", broken_market_read)

    page = client.get("/rebirth/shop")
    api = client.get("/api/rebirth/shop")
    payload = api.get_json()

    assert page.status_code == 200
    assert "Loja &amp; Mercado" in page.get_data(as_text=True)
    assert api.status_code == 200
    assert payload["ok"] is True
    assert payload["shop"]["market"]["offers"] == []
    assert payload["shop"]["warnings"][0]["surface"] == "market"


def test_play_card_api_summons_then_attack_resolves_combat(client):
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
    assert payload["match_reward"]["persisted"] is False

    target = payload["state"]["bot"]["battlefield"][0]
    attack = client.post(
        "/api/rebirth/attack",
        json={
            "match_id": payload["state"]["match_id"],
            "attacker_instance_id": payload["state"]["player"]["battlefield"][0]["instance_id"],
            "target_instance_id": target["instance_id"],
        },
    )
    attack_payload = attack.get_json()

    assert attack.status_code == 200
    assert attack_payload["ok"] is True
    assert attack_payload["state"]["phase"] == "result"
    assert attack_payload["state"]["last_clash"]["player_card"]["id"] == "card_001"
    assert attack_payload["state"]["result"]["outcome"] in {"Victory", "Defeat", "Clash"}


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
    assert payload["state"]["player_field"][0] is None
    assert payload["state"]["player_field"][1]["instance_id"] == card["instance_id"]
    assert payload["state"]["player_field"][2] is None
    assert payload["state"]["player"]["battlefield"][0]["field_slot"] == 1


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

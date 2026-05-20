def test_home_rebirth_and_health_routes_return_200(client):
    home = client.get("/")
    rebirth = client.get("/rebirth")
    health = client.get("/health")

    assert home.status_code == 200
    assert "One card. One decision. One clash." in home.get_data(as_text=True)
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
        "One card",
        "One decision",
        "One clash",
        "Combine duplicates",
        "Evolve monsters",
        "Win the duel",
        "Play Rebirth Prototype",
        "New Match",
        "Combine",
        "Clash",
    ):
        assert text in body

    for element_id in (
        "player-hp",
        "turn-number",
        "bot-hp",
        "bot-card",
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


def test_play_card_api_resolves_turn(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-play"})
    state = start.get_json()["state"]
    card = next(card for card in state["player"]["hand"] if card["id"] == "dreadclaw")

    response = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": card["instance_id"]},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["state"]["phase"] == "result"
    assert payload["state"]["last_clash"]["player_card"]["id"] == "dreadclaw"
    assert payload["state"]["result"]["outcome"] in {"Victory", "Defeat", "Clash"}
    assert payload["match_reward"]["persisted"] is False


def test_evolve_api_combines_duplicate(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-evolve"})
    state = start.get_json()["state"]

    response = client.post(
        "/api/rebirth/evolve",
        json={"match_id": state["match_id"], "card_id": "dreadclaw"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["evolved"]["id"] == "dreadmaw"
    assert payload["state"]["player"]["hand"][0]["id"] == "dreadmaw"


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


def test_invalid_api_returns_json_error(client):
    response = client.post(
        "/api/rebirth/play-card",
        json={"match_id": "missing", "card_id": "dreadclaw"},
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
        json={"match_id": "missing", "card_id": "dreadclaw"},
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
        json={"match_id": state["match_id"], "card_id": "voidstalker"},
    )
    invalid_phase = client.post(
        "/api/rebirth/next-turn",
        json={"match_id": state["match_id"]},
    )

    expected = [
        (missing_match, 404, "missing_match"),
        (malformed, 400, "malformed_request"),
        (invalid_card, 400, "invalid_card"),
        (duplicate, 400, "duplicate_not_available"),
        (invalid_phase, 409, "invalid_phase"),
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

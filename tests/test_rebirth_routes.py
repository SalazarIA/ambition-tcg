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


def test_start_api_returns_clear_json_state(client):
    response = client.post("/api/rebirth/start", json={"seed": "routes-start"})
    payload = response.get_json()

    assert response.status_code == 200
    assert response.is_json
    assert payload["ok"] is True
    assert payload["state"]["match_id"].startswith("rebirth-")
    assert payload["state"]["player"]["hp"] == 3
    assert len(payload["state"]["player"]["hand"]) == 5
    assert payload["state"]["bot"]["hand_count"] == 5


def test_play_card_api_resolves_turn(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-play"})
    state = start.get_json()["state"]
    card = next(card for card in state["player"]["hand"] if card["id"] == "iron_beetle")

    response = client.post(
        "/api/rebirth/play-card",
        json={"match_id": state["match_id"], "card_instance_id": card["instance_id"]},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["state"]["phase"] == "result"
    assert payload["state"]["last_clash"]["player_card"]["id"] == "iron_beetle"
    assert payload["state"]["result"]["outcome"] in {"Victory", "Defeat", "Clash"}


def test_evolve_api_combines_duplicate(client):
    start = client.post("/api/rebirth/start", json={"seed": "routes-evolve"})
    state = start.get_json()["state"]

    response = client.post(
        "/api/rebirth/evolve",
        json={"match_id": state["match_id"], "card_id": "ember_cub"},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["evolved"]["id"] == "ember_fang"
    assert payload["state"]["player"]["hand"][0]["id"] == "ember_fang"


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
        json={"match_id": "missing", "card_id": "ember_cub"},
    )
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["ok"] is False
    assert payload["error"]["code"] == "match_not_found"


def test_legacy_routes_redirect_or_report_retired(client):
    arena = client.get("/arena")
    legacy_api = client.post("/api/ascension/start", json={})

    assert arena.status_code == 302
    assert arena.headers["Location"] == "/rebirth"
    assert legacy_api.status_code == 410
    assert legacy_api.get_json()["error"]["code"] == "legacy_disabled"

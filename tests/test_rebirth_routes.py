from pathlib import Path


def test_rebirth_route_renders(client):
    response = client.get("/rebirth")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Ambitionz Rebirth" in body
    assert "rb-shell" in body
    assert "rebirth.js" in body
    assert "rebirth_3d_adapter.js" in body


def test_rebirth_new_api_returns_json(client):
    response = client.get("/api/rebirth/new?seed=routes-a")
    payload = response.get_json()

    assert response.status_code == 200
    assert response.is_json
    assert payload["ok"] is True
    assert payload["state"]["match_id"].startswith("rebirth-")
    assert payload["state"]["player"]["hp"] == 30


def test_rebirth_intent_play_and_resolve_flow(client):
    start = client.get("/api/rebirth/new?seed=routes-flow")
    state = start.get_json()["state"]
    card_id = state["hand"][0]["id"]
    match_id = state["match_id"]

    intent = client.post("/api/rebirth/intent", json={"match_id": match_id, "intent": "STRIKE"})
    assert intent.status_code == 200
    assert intent.get_json()["state"]["selected_intent"] == "STRIKE"

    play = client.post("/api/rebirth/play-card", json={"match_id": match_id, "card_id": card_id})
    assert play.status_code == 200
    assert play.get_json()["state"]["player"]["active_card"]["id"] == card_id

    resolved = client.post("/api/rebirth/resolve", json={"match_id": match_id})
    body = resolved.get_json()
    assert resolved.status_code == 200
    assert body["state"]["combat_log"]
    assert "hp" in body["state"]["player"]
    assert "hp" in body["state"]["opponent"]


def test_rebirth_invalid_match_returns_400(client):
    response = client.post("/api/rebirth/intent", json={"match_id": "missing", "intent": "STRIKE"})
    payload = response.get_json()

    assert response.status_code == 400
    assert payload["ok"] is False
    assert payload["error"]["code"] == "match_not_found"


def test_rebirth_invalid_intent_returns_400(client):
    start = client.get("/api/rebirth/new?seed=routes-invalid")
    match_id = start.get_json()["state"]["match_id"]
    response = client.post("/api/rebirth/intent", json={"match_id": match_id, "intent": "LANE"})

    assert response.status_code == 400


def test_rebirth_assets_are_cached():
    service_worker = Path(__file__).resolve().parents[1] / "static" / "js" / "service-worker.js"
    body = service_worker.read_text()

    assert 'CACHE_NAME = "ambitionz-web-app-v195"' in body
    assert '"/rebirth"' in body
    assert '"/static/css/rebirth.css"' in body
    assert '"/static/js/rebirth.js"' in body
    assert '"/static/js/rebirth_3d_adapter.js"' in body
    assert '"/static/assets/rebirth3d/manifest.json"' in body

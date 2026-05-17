def test_training_renders_new_ascension_template(client):
    response = client.get("/training")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Ascension Duel" in body
    assert "ax-duel-altar" in body
    assert "ax-ambition-core" in body
    assert "ambitionz_ascension.js" in body
    assert "arena_clean_v48.js" not in body


def test_training_legacy_still_renders_old_arena(client):
    response = client.get("/training-legacy")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="az48-training-panel"' in body
    assert "arena_clean_v48.js" in body


def test_ascension_apis_return_json_and_progress_state(client):
    start = client.post("/api/ascension/start", json={"seed": "route-seed", "bot_profile": "Aggressor"})
    payload = start.get_json()

    assert start.status_code == 200
    assert payload["ok"] is True
    assert payload["match"]["version"] == "ascension_duel_v1"
    assert payload["match"]["bot_profile"]["label"] == "Aggressor"

    champion = next(card for card in payload["match"]["player"]["hand"] if card["type"] == "champion")
    play = client.post("/api/ascension/play", json={"card_id": champion["id"], "mode": "summon"})
    play_payload = play.get_json()

    assert play.status_code == 200
    assert play_payload["ok"] is True
    assert play_payload["match"]["player"]["active_champion"]["id"] == champion["id"]

    intent = client.post("/api/ascension/intent", json={"intent": "Strike"})
    assert intent.status_code == 200
    assert intent.get_json()["match"]["player"]["intent"] == "Strike"

    commit = client.post("/api/ascension/commit", json={})
    assert commit.status_code == 200
    assert commit.is_json
    assert commit.get_json()["match"]["round"] >= 2


def test_ascension_dominate_unavailable_is_safe_json(client):
    client.post("/api/ascension/start", json={"seed": "route-dominate"})
    response = client.post("/api/ascension/dominate", json={})
    payload = response.get_json()

    assert response.status_code == 200
    assert response.is_json
    assert payload["ok"] is False
    assert payload["domination"]["code"] == "dominate_unavailable"


def test_ascension_finished_match_returns_reward_payload(client):
    start = client.post("/api/ascension/start", json={"seed": "route-reward"})
    payload = start.get_json()
    champion = next(card for card in payload["match"]["player"]["hand"] if card["type"] == "champion")
    client.post("/api/ascension/play", json={"card_id": champion["id"], "mode": "summon"})

    with client.session_transaction() as sess:
        match_id = sess["ascension_match_id"]

    import app as ambition_app

    match = ambition_app.ascension_training_matches[match_id]
    match["player"]["ambition"] = 20
    match["opponent"]["hp"] = 10
    response = client.post("/api/ascension/dominate", json={})
    body = response.get_json()

    assert response.status_code == 200
    assert body["reward"]["xp"] > 0
    assert body["reward"]["gold"] > 0

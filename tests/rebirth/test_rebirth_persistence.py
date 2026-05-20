from services.rebirth_persistence import RebirthRepository


def register(client, username="persist_user", email="persist@example.com"):
    return client.post(
        "/api/rebirth/auth/register",
        json={"username": username, "email": email, "password": "password123"},
    )


def test_register_login_logout_and_session_are_persisted(client, flask_app):
    created = register(client)
    payload = created.get_json()

    assert created.status_code == 200
    assert payload["account"]["authenticated"] is True
    assert payload["account"]["user"]["username"] == "persist_user"

    db_user = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"]).get_user(payload["account"]["user"]["id"])
    assert db_user["email"] == "persist@example.com"

    session_response = client.get("/api/rebirth/session")
    assert session_response.get_json()["account"]["authenticated"] is True

    logout = client.post("/api/rebirth/auth/logout", json={})
    assert logout.status_code == 200
    assert logout.get_json()["account"]["authenticated"] is False

    login = client.post("/api/rebirth/auth/login", json={"email": "persist@example.com", "password": "password123"})
    assert login.status_code == 200
    assert login.get_json()["account"]["user"]["username"] == "persist_user"


def test_duplicate_account_and_bad_login_return_stable_errors(client):
    register(client, username="dupe_user", email="dupe@example.com")
    duplicate = register(client, username="dupe_user", email="dupe@example.com")
    bad_login = client.post("/api/rebirth/auth/login", json={"email": "dupe@example.com", "password": "wrong"})

    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "auth_conflict"
    assert bad_login.status_code == 401
    assert bad_login.get_json()["error"]["code"] == "invalid_credentials"


def test_loadout_persists_and_start_match_uses_account_loadout(client):
    register(client, username="deck_user", email="deck@example.com")
    card_ids = [
        "dreadclaw",
        "dreadclaw",
        "dreadclaw",
        "stoneshell",
        "stoneshell",
        "skywarden",
        "ironbastion",
        "embermaw",
    ]

    saved = client.post("/api/rebirth/loadout", json={"card_ids": card_ids})
    assert saved.status_code == 200
    assert saved.get_json()["loadout"]["summary"]["size"] == 8

    start = client.post("/api/rebirth/start", json={"seed": "account-loadout"})
    state = start.get_json()["state"]
    visible_ids = [card["id"] for card in state["player"]["hand"]]

    assert state["player"]["name"] == "deck_user"
    assert visible_ids == card_ids[:5]


def test_booster_mutates_collection_and_progression(client):
    register(client, username="owner_user", email="owner@example.com")
    before = client.get("/api/rebirth/collection").get_json()["collection"]["summary"]["owned_cards"]

    opened = client.post("/api/rebirth/booster/open", json={"seed": "ownership"})
    payload = opened.get_json()
    after = client.get("/api/rebirth/collection").get_json()["collection"]["summary"]["owned_cards"]
    progress = client.get("/api/rebirth/progression").get_json()["progression"]["profile"]

    assert opened.status_code == 200
    assert payload["booster"]["summary"]["count"] == 4
    assert after == before + 4
    assert progress["boosters_opened"] == 1
    assert progress["xp"] >= 40


def test_match_progression_daily_reward_and_tutorial_are_persisted(client):
    register(client, username="reward_user", email="reward@example.com")
    start = client.post("/api/rebirth/start", json={"seed": "reward-match"}).get_json()["state"]
    card = start["player"]["hand"][0]
    played = client.post(
        "/api/rebirth/play-card",
        json={"match_id": start["match_id"], "card_instance_id": card["instance_id"]},
    )

    assert played.status_code == 200
    assert played.get_json()["progression"]["clashes"] == 1
    reward = played.get_json()["match_reward"]
    assert reward["persisted"] is True
    assert reward["xp"] >= 25
    assert reward["daily"]["ready"] is True
    assert {"key": "first_clash", "name": "First Clash"} in reward["achievements"]

    daily = client.post("/api/rebirth/progression/claim-daily", json={})
    tutorial = client.post("/api/rebirth/onboarding/complete", json={"step": 4})
    profile = client.get("/api/rebirth/progression").get_json()["progression"]["profile"]

    assert daily.status_code == 200
    assert daily.get_json()["claim"]["xp"] == 25
    assert tutorial.status_code == 200
    assert tutorial.get_json()["tutorial"]["progression"]["tutorial_complete"] is True
    assert profile["tutorial_complete"] is True
    assert profile["clashes"] == 1


def test_profile_achievements_follow_rebirth_actions(client):
    register(client, username="badge_user", email="badge@example.com")
    profile = client.get("/api/rebirth/profile").get_json()["profile"]["profile"]
    achievements = {item["key"]: item for item in profile["achievements"]}

    assert achievements["founder"]["unlocked"] is True
    assert profile["unlocked_achievements"] == 1

    opened = client.post("/api/rebirth/booster/open", json={"seed": "badge-booster"})
    start = client.post("/api/rebirth/start", json={"seed": "badge-match"}).get_json()["state"]
    card = start["player"]["hand"][0]
    played = client.post(
        "/api/rebirth/play-card",
        json={"match_id": start["match_id"], "card_instance_id": card["instance_id"]},
    )
    daily = client.post("/api/rebirth/progression/claim-daily", json={})
    tutorial = client.post("/api/rebirth/onboarding/complete", json={"step": 4})

    assert opened.status_code == 200
    assert played.status_code == 200
    assert daily.status_code == 200
    assert tutorial.status_code == 200

    profile = client.get("/api/rebirth/profile").get_json()["profile"]["profile"]
    achievements = {item["key"]: item for item in profile["achievements"]}

    assert achievements["first_booster"]["unlocked"] is True
    assert achievements["first_clash"]["unlocked"] is True
    assert achievements["daily_claimed"]["unlocked"] is True
    assert achievements["tutorial_complete"]["unlocked"] is True
    assert profile["unlocked_achievements"] >= 5


def test_balance_simulation_is_capped_and_deterministic(client):
    response = client.get("/api/rebirth/balance/simulate?matches=500")
    payload = response.get_json()["balance"]

    assert response.status_code == 200
    assert payload["matches"] == 200
    assert payload["summary"]["average_turns"] > 0
    assert payload["bot_tuning"]["policy"].startswith("rotate defensive")
    assert {item["profile_id"] for item in payload["profile_results"]} == {"defensive", "aggressive", "opportunist"}
    assert payload["card_stats"][0]["ability_key"]
    assert payload["ability_stats"][0]["plays"] > 0

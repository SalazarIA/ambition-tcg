def register(client, username="season_user", email="season@example.com"):
    return client.post(
        "/api/rebirth/auth/register",
        json={"username": username, "email": email, "password": "password123"},
    )


def test_match_command_event_history_and_ledger_are_persisted(client):
    register(client)

    start = client.post("/api/rebirth/start", json={"seed": "season-history"}).get_json()["state"]
    assert start["version"] >= 1
    assert start["state_hash"]
    assert start["events"][0]["type"] == "MATCH_STARTED"
    evolution = start["available_evolutions"][0]

    evolved = client.post(
        "/api/rebirth/evolve",
        json={"match_id": start["match_id"], "card_id": evolution["card_id"]},
    ).get_json()["state"]
    turn_two = client.post("/api/rebirth/next-turn", json={"match_id": evolved["match_id"]}).get_json()["state"]
    played_card = next(card for card in turn_two["player"]["hand"] if card["id"] == evolution["evolution_id"])
    summoned = client.post(
        "/api/rebirth/play-card",
        json={"match_id": turn_two["match_id"], "card_instance_id": played_card["instance_id"]},
    ).get_json()
    attack_json = {
        "match_id": summoned["state"]["match_id"],
        "attacker_instance_id": summoned["state"]["player"]["battlefield"][-1]["instance_id"],
    }
    if summoned["state"]["bot"]["battlefield"]:
        attack_json["target_instance_id"] = summoned["state"]["bot"]["battlefield"][0]["instance_id"]
    played = client.post(
        "/api/rebirth/attack",
        json=attack_json,
    ).get_json()

    assert played["state"]["version"] > start["version"]
    assert {event["type"] for event in played["state"]["events"]} >= {"CARD_PLAYED", "CLASH_RESOLVED"}

    history = client.get("/api/rebirth/match-history").get_json()["history"]
    assert history[0]["match_id"] == start["match_id"]
    assert history[0]["command_count"] >= 2
    assert history[0]["event_count"] >= 4
    assert history[0]["state_hash"]

    events = client.get(f"/api/rebirth/match-history/{start['match_id']}/events").get_json()["events"]
    assert events[0]["type"] == "MATCH_STARTED"
    assert any(event["type"] == "CLASH_RESOLVED" for event in events)

    ledger = client.get("/api/rebirth/economy-ledger").get_json()["ledger"]
    assert any(entry["resource"] == "xp" and entry["reason"] == "match_clash" for entry in ledger)
    assert any(entry["resource"].startswith("card:") for entry in ledger)


def test_history_and_support_pages_render(client):
    register(client, username="pages_user", email="pages@example.com")
    for path, label in {
        "/rebirth/history": "Match History + Economy Ledger",
        "/rebirth/support": "Support + Admin Safety",
    }.items():
        response = client.get(path)
        body = response.get_data(as_text=True)
        assert response.status_code == 200
        assert label in body
        assert "Ambitionz Rebirth" in body


def test_support_export_reset_and_admin_grant(client, flask_app):
    flask_app.config["REBIRTH_ADMIN_TOKEN"] = "test-admin-token"
    created = register(client, username="support_user", email="support@example.com").get_json()
    user_id = created["account"]["user"]["id"]

    client.post("/api/rebirth/booster/open", json={"seed": "support-booster"})
    exported = client.get("/api/rebirth/support/export")
    assert exported.status_code == 200
    assert exported.get_json()["export"]["user"]["id"] == user_id
    assert exported.get_json()["export"]["ledger"]

    grant = client.post(
        "/api/rebirth/admin/grant",
        json={"user_id": user_id, "resource": "xp", "amount": 125, "reason": "qa_grant"},
        headers={"X-Rebirth-Admin-Token": "test-admin-token"},
    )
    assert grant.status_code == 200
    assert any(entry["reason"] == "qa_grant" for entry in grant.get_json()["export"]["ledger"])

    rejected = client.post("/api/rebirth/support/reset", json={"confirm": "wrong"})
    assert rejected.status_code == 409
    assert rejected.get_json()["error"]["code"] == "reset_confirmation_required"

    reset = client.post("/api/rebirth/support/reset", json={"confirm": "RESET REBIRTH"})
    assert reset.status_code == 200
    export = reset.get_json()["export"]
    assert export["progression"]["xp"] == 0
    assert export["matches"] == []
    assert export["ledger"]

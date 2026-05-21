def test_rebirth_deploy_smoke_flow(client):
    home = client.get("/")
    rebirth = client.get("/rebirth")
    health = client.get("/health")

    assert home.status_code == 200
    assert "Ambitionz Rebirth" in home.get_data(as_text=True)
    assert rebirth.status_code == 200
    assert "data-rebirth-app" in rebirth.get_data(as_text=True)
    assert health.status_code == 200
    assert health.get_json() == {
        "ok": True,
        "status": "healthy",
        "product": "Ambitionz Rebirth",
        "architecture": "Ambitionz Rebirth",
    }

    client.post(
        "/api/rebirth/auth/register",
        json={"username": "deploy_user", "email": "deploy@example.com", "password": "password123"},
    )
    collection = client.get("/rebirth/collection")
    booster = client.post("/api/rebirth/booster/open", json={"seed": "deploy-smoke-booster"})
    assert collection.status_code == 200
    assert "Minha Colecao" in collection.get_data(as_text=True)
    assert booster.status_code == 200
    assert booster.get_json()["booster"]["summary"]["count"] == 5

    start = client.post("/api/rebirth/start", json={"seed": "deploy-smoke"})
    start_payload = start.get_json()
    assert start.status_code == 200
    assert start_payload["ok"] is True
    assert start_payload["state"]["phase"] == "choose"
    assert start_payload["state"]["match_id"].startswith("rebirth-")
    evolution = start_payload["state"]["available_evolutions"][0]

    evolve = client.post(
        "/api/rebirth/evolve",
        json={
            "match_id": start_payload["state"]["match_id"],
            "card_id": evolution["card_id"],
        },
    )
    evolve_payload = evolve.get_json()
    assert evolve.status_code == 200
    assert evolve_payload["ok"] is True
    assert evolve_payload["evolved"]["id"] == evolution["evolution_id"]

    turn_two = client.post("/api/rebirth/next-turn", json={"match_id": evolve_payload["state"]["match_id"]})
    turn_two_payload = turn_two.get_json()
    assert turn_two.status_code == 200
    assert turn_two_payload["state"]["player"]["max_energy"] == 2

    played_card = next(card for card in turn_two_payload["state"]["player"]["hand"] if card["id"] == evolution["evolution_id"])
    summon = client.post(
        "/api/rebirth/play-card",
        json={
            "match_id": turn_two_payload["state"]["match_id"],
            "card_instance_id": played_card["instance_id"],
        },
    )
    summon_payload = summon.get_json()
    assert summon.status_code == 200
    assert summon_payload["ok"] is True
    assert summon_payload["state"]["phase"] == "choose"
    assert summon_payload["state"]["player"]["battlefield"][-1]["id"] == evolution["evolution_id"]

    attack_json = {
        "match_id": summon_payload["state"]["match_id"],
        "attacker_instance_id": summon_payload["state"]["player"]["battlefield"][-1]["instance_id"],
    }
    if summon_payload["state"]["bot"]["battlefield"]:
        attack_json["target_instance_id"] = summon_payload["state"]["bot"]["battlefield"][0]["instance_id"]
    clash = client.post("/api/rebirth/attack", json=attack_json)
    clash_payload = clash.get_json()
    assert clash.status_code == 200
    assert clash_payload["ok"] is True
    assert clash_payload["state"]["phase"] in {"result", "finished"}
    assert clash_payload["state"]["last_clash"]["player_card"]["id"] == evolution["evolution_id"]

    legacy_browser = client.get("/training")
    legacy_api = client.post("/api/beta/telemetry", json={"event": "retired"})
    assert legacy_browser.status_code == 302
    assert legacy_browser.headers["Location"] == "/rebirth"
    assert legacy_api.status_code == 410
    assert legacy_api.get_json()["error"]["code"] == "legacy_disabled"

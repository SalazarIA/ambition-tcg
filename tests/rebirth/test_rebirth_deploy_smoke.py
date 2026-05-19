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

    start = client.post("/api/rebirth/start", json={"seed": "deploy-smoke"})
    start_payload = start.get_json()
    assert start.status_code == 200
    assert start_payload["ok"] is True
    assert start_payload["state"]["phase"] == "choose"
    assert start_payload["state"]["match_id"].startswith("rebirth-")

    evolve = client.post(
        "/api/rebirth/evolve",
        json={
            "match_id": start_payload["state"]["match_id"],
            "card_id": "dreadclaw",
        },
    )
    evolve_payload = evolve.get_json()
    assert evolve.status_code == 200
    assert evolve_payload["ok"] is True
    assert evolve_payload["evolved"]["id"] == "dreadmaw"

    played_card = evolve_payload["state"]["player"]["hand"][0]
    clash = client.post(
        "/api/rebirth/play-card",
        json={
            "match_id": evolve_payload["state"]["match_id"],
            "card_instance_id": played_card["instance_id"],
        },
    )
    clash_payload = clash.get_json()
    assert clash.status_code == 200
    assert clash_payload["ok"] is True
    assert clash_payload["state"]["phase"] in {"result", "finished"}
    assert clash_payload["state"]["last_clash"]["player_card"]["id"] == "dreadmaw"

    legacy_browser = client.get("/training")
    legacy_api = client.post("/api/beta/telemetry", json={"event": "retired"})
    assert legacy_browser.status_code == 302
    assert legacy_browser.headers["Location"] == "/rebirth"
    assert legacy_api.status_code == 410
    assert legacy_api.get_json()["error"]["code"] == "legacy_disabled"

def test_rebirth_deploy_smoke_flow(client):
    home = client.get("/")
    rebirth = client.get("/rebirth")
    health = client.get("/health")

    assert home.status_code == 200
    assert "Ambitionz Rebirth" in home.get_data(as_text=True)
    assert rebirth.status_code == 200
    assert "data-rebirth-app" in rebirth.get_data(as_text=True)
    assert health.status_code == 200
    assert health.get_json()["ok"] is True
    assert health.get_json()["status"] == "healthy"
    assert health.get_json()["product"] == "Ambitionz Rebirth"
    assert health.get_json()["architecture"] == "Ambitionz Rebirth PostgreSQL Foundation"
    assert health.get_json()["persistence"]["backend"] == "sqlite_test"

    client.post(
        "/api/rebirth/auth/register",
        json={"username": "deploy_user", "email": "deploy@example.com", "password": "password123"},
    )
    collection = client.get("/rebirth/collection")
    booster = client.post("/api/rebirth/booster/open", json={"seed": "deploy-smoke-booster"})
    assert collection.status_code == 200
    assert "Minha Coleção" in collection.get_data(as_text=True)
    assert booster.status_code == 200
    assert booster.get_json()["booster"]["summary"]["count"] == 5

    # Com o shuffle real, procura uma seed cuja mão abra com dupla evoluível.
    start_payload = None
    for attempt in range(30):
        start = client.post("/api/rebirth/start", json={"seed": f"deploy-smoke-{attempt}"})
        candidate = start.get_json()
        assert start.status_code == 200
        assert candidate["ok"] is True
        if candidate["state"].get("available_evolutions"):
            start_payload = candidate
            break
    assert start_payload is not None, "nenhuma seed de smoke abriu com dupla evoluível"
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

    # Evolved cards cost more than their tier-1 base. Advance turns until the
    # player has enough energy to summon the evolved monster.
    last_state = evolve_payload["state"]
    evolved_card_id = evolution["evolution_id"]
    evolved_cost = next(
        (int(c.get("cost", 1) or 1) for c in last_state["player"]["hand"] if c["id"] == evolved_card_id),
        2,
    )
    while int(last_state["player"].get("max_energy", 1) or 1) < evolved_cost:
        last_state = client.post(
            "/api/rebirth/next-turn", json={"match_id": last_state["match_id"]}
        ).get_json()["state"]

    played_card = next(card for card in last_state["player"]["hand"] if card["id"] == evolved_card_id)
    summon = client.post(
        "/api/rebirth/play-card",
        json={
            "match_id": last_state["match_id"],
            "card_instance_id": played_card["instance_id"],
        },
    )
    summon_payload = summon.get_json()
    assert summon.status_code == 200
    assert summon_payload["ok"] is True
    assert summon_payload["state"]["phase"] == "choose"
    assert summon_payload["state"]["player"]["battlefield"][-1]["id"] == evolution["evolution_id"]

    # Summoning sickness: a evoluída ataca a partir do turno seguinte. Avança
    # turnos até a carta estar pronta em campo (re-invocando se o bot limpar).
    state = summon_payload["state"]
    clash_payload = None
    evolved_instance = state["player"]["battlefield"][-1]["instance_id"]
    for _ in range(8):
        if state.get("is_finished"):
            break
        on_field = next((c for c in state["player"]["battlefield"] if c["instance_id"] == evolved_instance), None)
        ready = on_field and not on_field.get("exhausted") and not on_field.get("has_acted") and (
            "RUSH" in (on_field.get("keywords") or []) or not on_field.get("just_summoned")
        )
        if on_field and ready:
            attack_json = {"match_id": state["match_id"], "attacker_instance_id": evolved_instance}
            if state["bot"]["battlefield"]:
                attack_json["target_instance_id"] = state["bot"]["battlefield"][0]["instance_id"]
            clash = client.post("/api/rebirth/attack", json=attack_json)
            clash_payload = clash.get_json()
            assert clash.status_code == 200
            break
        if not on_field:
            break
        state = client.post("/api/rebirth/next-turn", json={"match_id": state["match_id"]}).get_json()["state"]
    if clash_payload is not None:
        assert clash_payload["ok"] is True
        assert clash_payload["state"]["phase"] in {"result", "finished"}
        assert clash_payload["state"]["last_clash"]["player_card"]["id"] == evolution["evolution_id"]

    legacy_browser = client.get("/training")
    legacy_api = client.post("/api/beta/telemetry", json={"event": "retired"})
    assert legacy_browser.status_code == 302
    assert legacy_browser.headers["Location"] == "/rebirth"
    assert legacy_api.status_code == 410
    assert legacy_api.get_json()["error"]["code"] == "legacy_disabled"

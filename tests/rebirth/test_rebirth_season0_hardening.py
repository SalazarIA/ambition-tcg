def register(client, username="season_user", email="season@example.com"):
    return client.post(
        "/api/rebirth/auth/register",
        json={"username": username, "email": email, "password": "password123"},
    )


def test_match_command_event_history_and_ledger_are_persisted(client):
    register(client)

    start = None
    for attempt in range(30):
        candidate = client.post("/api/rebirth/start", json={"seed": f"season-history-{attempt}"}).get_json()["state"]
        if candidate.get("available_evolutions"):
            start = candidate
            break
    assert start is not None, "nenhuma seed abriu com dupla evoluível"
    assert start["version"] >= 1
    assert start["state_hash"]
    assert start["events"][0]["type"] == "MATCH_STARTED"
    evolution = start["available_evolutions"][0]

    evolved = client.post(
        "/api/rebirth/evolve",
        json={"match_id": start["match_id"], "card_id": evolution["card_id"]},
    ).get_json()["state"]
    evolved_card_id = evolution["evolution_id"]
    evolved_cost = next(
        (int(c.get("cost", 1) or 1) for c in evolved["player"]["hand"] if c["id"] == evolved_card_id),
        2,
    )
    current = evolved
    while int(current["player"].get("max_energy", 1) or 1) < evolved_cost:
        current = client.post(
            "/api/rebirth/next-turn", json={"match_id": current["match_id"]}
        ).get_json()["state"]
    played_card = next(card for card in current["player"]["hand"] if card["id"] == evolved_card_id)
    summoned = client.post(
        "/api/rebirth/play-card",
        json={"match_id": current["match_id"], "card_instance_id": played_card["instance_id"]},
    ).get_json()
    # Sickness: espera a evoluída ficar pronta antes do clash.
    state = summoned["state"]
    evolved_instance = state["player"]["battlefield"][-1]["instance_id"]
    played = None
    for _ in range(8):
        if state.get("is_finished"):
            break
        on_field = next((c for c in state["player"]["battlefield"] if c["instance_id"] == evolved_instance), None)
        if on_field is None:
            state = client.post("/api/rebirth/next-turn", json={"match_id": state["match_id"]}).get_json()["state"]
            continue
        ready = not on_field.get("exhausted") and not on_field.get("has_acted") and (
            "RUSH" in (on_field.get("keywords") or []) or not on_field.get("just_summoned")
        )
        if not ready:
            state = client.post("/api/rebirth/next-turn", json={"match_id": state["match_id"]}).get_json()["state"]
            continue
        attack_json = {"match_id": state["match_id"], "attacker_instance_id": evolved_instance}
        if state["bot"]["battlefield"]:
            attack_json["target_instance_id"] = state["bot"]["battlefield"][0]["instance_id"]
        played = client.post("/api/rebirth/attack", json=attack_json).get_json()
        break
    assert played is not None and played.get("ok"), f"clash não aconteceu: {played}"

    assert played["state"]["version"] > start["version"]
    # O estado expõe só os últimos 12 eventos; após a espera da sickness o
    # CARD_PLAYED sai da janela — o clash é o que precisa estar visível.
    assert "CLASH_RESOLVED" in {event["type"] for event in played["state"]["events"]}

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
        "/rebirth/history": "Histórico de Partidas + Extrato Econômico",
        "/rebirth/support": "Suporte + Segurança Administrativa",
    }.items():
        response = client.get(path)
        body = response.get_data(as_text=True)
        assert response.status_code == 200
        assert label in body
        assert "Ambitionz Rebirth" in body
    assert "data-rebirth-feedback" in client.get("/rebirth/support").get_data(as_text=True)


def test_feedback_capture_links_version_account_and_last_match(client, flask_app):
    created = register(client, username="feedback_user", email="feedback@example.com").get_json()
    user_id = created["account"]["user"]["id"]
    state = client.post("/api/rebirth/start", json={"seed": "feedback-match"}).get_json()["state"]

    response = client.post(
        "/api/rebirth/support/feedback",
        json={
            "category": "balance",
            "severity": "normal",
            "message": "A partida tutorial ficou clara, mas o bot defensivo demorou.",
            "match_id": state["match_id"],
            "surface": "support",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["feedback"]["match_id"] == state["match_id"]
    from services.rebirth_persistence import RebirthRepository

    events = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"]).query_telemetry_events(
        event_types=("feedback_submitted",),
        limit=1,
    )
    assert events[0]["user_id"] == user_id
    assert events[0]["payload"]["category"] == "balance"
    assert events[0]["payload"]["rebirth_release_version"]


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
    assert any(entry["reason"] == "account_reset_compensation" for entry in export["ledger"])
    retained_ledger = client.get("/api/rebirth/economy-ledger?limit=100").get_json()["ledger"]
    assert any(entry["reason"] == "qa_grant" for entry in retained_ledger)


def test_support_delete_account_removes_login_and_private_state(client):
    created = register(client, username="delete_user", email="delete@example.com").get_json()
    user_id = created["account"]["user"]["id"]

    client.post("/api/rebirth/booster/open", json={"seed": "delete-booster"})
    rejected = client.post("/api/rebirth/support/delete-account", json={"confirm": "wrong"})
    assert rejected.status_code == 409
    assert rejected.get_json()["error"]["code"] == "delete_confirmation_required"

    deleted = client.post("/api/rebirth/support/delete-account", json={"confirm": "DELETE REBIRTH"})
    payload = deleted.get_json()
    assert deleted.status_code == 200
    assert payload["deletion"]["deleted"] is True
    assert payload["deletion"]["deleted_user_id"] == user_id
    assert payload["account"]["authenticated"] is False

    export_after = client.get("/api/rebirth/support/export")
    assert export_after.status_code == 401
    assert export_after.get_json()["error"]["code"] == "auth_required"

    login_after = client.post(
        "/api/rebirth/auth/login",
        json={"email": "delete@example.com", "password": "password123"},
    )
    assert login_after.status_code == 401
    assert login_after.get_json()["error"]["code"] == "invalid_credentials"

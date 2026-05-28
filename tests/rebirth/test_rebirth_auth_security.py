def register_payload(username="secure_user", email="secure@example.com", password="password123"):
    return {"username": username, "email": email, "password": password}


def test_rebirth_csrf_protects_mutating_api_when_enabled(client, flask_app):
    flask_app.config["REBIRTH_REQUIRE_CSRF"] = True

    rejected = client.post("/api/rebirth/auth/register", json=register_payload())
    assert rejected.status_code == 403
    assert rejected.get_json()["error"]["code"] == "csrf_required"

    token = client.get("/api/rebirth/csrf").get_json()["csrf"]
    accepted = client.post(
        "/api/rebirth/auth/register",
        json=register_payload(),
        headers={"X-Rebirth-CSRF": token},
    )

    assert accepted.status_code == 200
    assert accepted.get_json()["account"]["authenticated"] is True
    assert accepted.get_json()["csrf"]


def test_rebirth_csrf_covers_labs_fusion_route(client, flask_app):
    # Studio master audit P1.1: /api/labs/fusion estava fora do filtro CSRF.
    # Esse gate trava qualquer regressão silenciosa do escopo de proteção.
    flask_app.config["REBIRTH_REQUIRE_CSRF"] = True

    rejected = client.post("/api/labs/fusion", json={"card_id": "card_001"})
    assert rejected.status_code == 403
    assert rejected.get_json()["error"]["code"] == "csrf_required"


def test_rebirth_beacon_endpoint_accepts_csrf_in_body(client, flask_app):
    # Studio master audit P1.2: pagehide telemetry agora usa
    # navigator.sendBeacon, que não pode setar headers. O endpoint
    # /api/rebirth/telemetry/beacon valida CSRF lendo do corpo.
    flask_app.config["REBIRTH_REQUIRE_CSRF"] = True

    no_token = client.post(
        "/api/rebirth/telemetry/beacon",
        json={"event_type": "match_abandoned", "match_id": "x"},
    )
    assert no_token.status_code == 403
    assert no_token.get_json()["error"]["code"] == "csrf_required"

    token = client.get("/api/rebirth/csrf").get_json()["csrf"]
    wrong_token = client.post(
        "/api/rebirth/telemetry/beacon",
        json={"event_type": "match_abandoned", "match_id": "x", "csrf": "wrong"},
    )
    assert wrong_token.status_code == 403
    assert wrong_token.get_json()["error"]["code"] == "csrf_required"

    # Header path NÃO é aceito — endpoint só verifica body.
    header_only = client.post(
        "/api/rebirth/telemetry/beacon",
        json={"event_type": "match_abandoned", "match_id": "x"},
        headers={"X-Rebirth-CSRF": token},
    )
    assert header_only.status_code == 403


def test_rebirth_beacon_endpoint_rejects_other_event_types(client, flask_app):
    flask_app.config["REBIRTH_REQUIRE_CSRF"] = True
    token = client.get("/api/rebirth/csrf").get_json()["csrf"]

    rejected = client.post(
        "/api/rebirth/telemetry/beacon",
        json={"event_type": "match_started", "match_id": "x", "csrf": token},
    )
    assert rejected.status_code == 400
    assert rejected.get_json()["error"]["code"] == "invalid_telemetry_event"


def test_combat_endpoints_reject_unexpected_fields(client, flask_app):
    # audit #15: defesa anti-injeção virou allowlist. Campos fora do conjunto
    # esperado são rejeitados cedo (o engine já era autoritativo, mas isto
    # fecha a porta antes do dispatch).
    flask_app.config["REBIRTH_REQUIRE_CSRF"] = False
    start = client.post("/api/rebirth/start", json={"seed": "allowlist-probe"}).get_json()["state"]
    match_id = start["match_id"]

    injected = client.post(
        "/api/rebirth/play-card",
        json={"match_id": match_id, "card_id": "card_001", "damage": 9999, "winner": "player"},
    )
    assert injected.status_code == 400
    assert injected.get_json()["error"]["code"] == "unexpected_combat_fields"

    attack_injected = client.post(
        "/api/rebirth/attack",
        json={"match_id": match_id, "attacker_instance_id": "x", "winner": "player"},
    )
    assert attack_injected.status_code == 400
    assert attack_injected.get_json()["error"]["code"] == "unexpected_combat_fields"


def test_rebirth_auth_rate_limit_returns_stable_error(client, flask_app):
    flask_app.config["REBIRTH_AUTH_RATE_LIMIT"] = 1

    first = client.post("/api/rebirth/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    second = client.post("/api/rebirth/auth/login", json={"email": "nobody@example.com", "password": "password123"})

    assert first.status_code == 401
    assert first.get_json()["error"]["code"] == "invalid_credentials"
    assert second.status_code == 429
    assert second.get_json()["error"]["code"] == "rate_limited"


def test_rebirth_auth_rate_limit_cannot_be_bypassed_by_rotating_identity(client, flask_app):
    flask_app.config["REBIRTH_AUTH_RATE_LIMIT"] = 1

    first = client.post("/api/rebirth/auth/login", json={"email": "first@example.com", "password": "password123"})
    rotated = client.post("/api/rebirth/auth/login", json={"email": "second@example.com", "password": "password123"})

    assert first.status_code == 401
    assert rotated.status_code == 429
    assert rotated.get_json()["error"]["code"] == "rate_limited"


def test_rebirth_password_change_updates_credentials(client):
    created = client.post("/api/rebirth/auth/register", json=register_payload())
    assert created.status_code == 200

    changed = client.post(
        "/api/rebirth/auth/change-password",
        json={"current_password": "password123", "new_password": "new-password-123"},
    )
    assert changed.status_code == 200
    assert changed.get_json()["message"] == "Senha atualizada."

    client.post("/api/rebirth/auth/logout", json={})
    old_login = client.post("/api/rebirth/auth/login", json={"email": "secure@example.com", "password": "password123"})
    new_login = client.post(
        "/api/rebirth/auth/login",
        json={"email": "secure@example.com", "password": "new-password-123"},
    )

    assert old_login.status_code == 401
    assert old_login.get_json()["error"]["code"] == "invalid_credentials"
    assert new_login.status_code == 200
    assert new_login.get_json()["account"]["user"]["username"] == "secure_user"

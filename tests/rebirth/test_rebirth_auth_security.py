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


def test_rebirth_auth_rate_limit_returns_stable_error(client, flask_app):
    flask_app.config["REBIRTH_AUTH_RATE_LIMIT"] = 1

    first = client.post("/api/rebirth/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    second = client.post("/api/rebirth/auth/login", json={"email": "nobody@example.com", "password": "password123"})

    assert first.status_code == 401
    assert first.get_json()["error"]["code"] == "invalid_credentials"
    assert second.status_code == 429
    assert second.get_json()["error"]["code"] == "rate_limited"


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

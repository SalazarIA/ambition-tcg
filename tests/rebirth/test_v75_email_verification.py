"""Email verification flow (schema v9).

New accounts start unverified with a one-shot verification token. The link
(or /api/rebirth/auth/verify-email) consumes the token once; resend issues a
fresh one. The token must never leak into public account payloads. Email
sending is best-effort and falls back to logging when SMTP is unconfigured,
so the whole flow works in tests without a provider.
"""

from services.rebirth_persistence import RebirthRepository


def _repo(flask_app):
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    repo.ensure_schema()
    return repo


def _token_for(repo, email):
    with repo.connect() as db:
        row = db.execute("SELECT verification_token FROM users WHERE email = ?", (email,)).fetchone()
    return row["verification_token"] if row else None


def test_new_account_starts_unverified_with_token(flask_app):
    repo = _repo(flask_app)
    user = repo.create_user("verifier", "verifier@example.com", "password123")
    assert user["email_verified"] is False
    assert user["verification_token"]  # transient, returned only on creation
    # get_user must NOT expose the raw token.
    reread = repo.get_user(user["id"])
    assert "verification_token" not in reread
    assert reread["email_verified"] is False


def test_verify_token_is_one_shot(flask_app):
    repo = _repo(flask_app)
    user = repo.create_user("once", "once@example.com", "password123")
    token = user["verification_token"]

    verified = repo.verify_email_token(token)
    assert verified["email_verified"] is True

    # Replaying the consumed token must fail (idempotent, no re-verify).
    assert repo.verify_email_token(token) is None
    assert repo.verify_email_token("bogus") is None


def test_resend_only_for_unverified(flask_app):
    repo = _repo(flask_app)
    user = repo.create_user("resender", "resender@example.com", "password123")
    first_token = user["verification_token"]

    fresh = repo.regenerate_verification_token(user["id"])
    assert fresh and fresh != first_token
    # Old token is now invalid; the fresh one verifies.
    assert repo.verify_email_token(first_token) is None
    assert repo.verify_email_token(fresh)["email_verified"] is True

    # Once verified, resend returns None (nothing to send).
    assert repo.regenerate_verification_token(user["id"]) is None


def test_account_payload_never_leaks_token(flask_app):
    from services.rebirth_product import account_payload
    repo = _repo(flask_app)
    user = repo.create_user("leaky", "leaky@example.com", "password123")
    payload = account_payload(user)
    assert "verification_token" not in payload["user"]
    assert payload["user"]["email_verified"] is False


def test_register_endpoint_creates_unverified_and_hides_token(client, flask_app):
    flask_app.config["REBIRTH_REQUIRE_CSRF"] = False
    response = client.post(
        "/api/rebirth/auth/register",
        json={"username": "apiverify", "email": "apiverify@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    account = response.get_json()["account"]
    assert account["authenticated"] is True
    assert account["user"]["email_verified"] is False
    assert "verification_token" not in account["user"]


def test_verify_email_endpoint_round_trip(client, flask_app):
    flask_app.config["REBIRTH_REQUIRE_CSRF"] = False
    client.post(
        "/api/rebirth/auth/register",
        json={"username": "rounder", "email": "rounder@example.com", "password": "password123"},
    )
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    token = _token_for(repo, "rounder@example.com")

    ok = client.post("/api/rebirth/auth/verify-email", json={"token": token})
    assert ok.status_code == 200
    assert ok.get_json()["verified"] is True
    assert ok.get_json()["account"]["user"]["email_verified"] is True

    # Consumed token → 410.
    replay = client.post("/api/rebirth/auth/verify-email", json={"token": token})
    assert replay.status_code == 410
    assert replay.get_json()["error"]["code"] == "verification_failed"


def test_verify_link_redirects_with_status(client, flask_app):
    flask_app.config["REBIRTH_REQUIRE_CSRF"] = False
    client.post(
        "/api/rebirth/auth/register",
        json={"username": "linker", "email": "linker@example.com", "password": "password123"},
    )
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    token = _token_for(repo, "linker@example.com")

    good = client.get(f"/rebirth/verify?token={token}")
    assert good.status_code == 302
    assert "verified=1" in good.headers["Location"]

    bad = client.get("/rebirth/verify?token=nope")
    assert bad.status_code == 302
    assert "verified=0" in bad.headers["Location"]


def test_resend_verification_endpoint(client, flask_app):
    flask_app.config["REBIRTH_REQUIRE_CSRF"] = False
    client.post(
        "/api/rebirth/auth/register",
        json={"username": "resendapi", "email": "resendapi@example.com", "password": "password123"},
    )
    resent = client.post("/api/rebirth/auth/resend-verification", json={})
    assert resent.status_code == 200
    assert resent.get_json()["resent"] is True

    # After verifying, resend reports already_verified.
    repo = RebirthRepository(flask_app.config["REBIRTH_DB_PATH"])
    token = _token_for(repo, "resendapi@example.com")
    client.post("/api/rebirth/auth/verify-email", json={"token": token})
    again = client.post("/api/rebirth/auth/resend-verification", json={})
    assert again.status_code == 200
    assert again.get_json()["already_verified"] is True

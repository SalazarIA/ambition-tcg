from models import SystemLog, User, db

from app import active_matches, issue_password_reset_token
from conftest import create_user, csrf_token_from_response, login_session


def test_homepage_adds_security_headers(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_csrf_rejects_post_without_token(client):
    response = client.post(
        "/login",
        data={"email": "nobody@example.com", "password": "WrongPass1"},
    )

    assert response.status_code == 400
    assert b"Invalid CSRF token" in response.data


def test_register_rejects_weak_password(client):
    token = csrf_token_from_response(client.get("/register"))

    response = client.post(
        "/register",
        data={
            "_csrf_token": token,
            "username": "weak",
            "email": "weak@example.com",
            "password": "short",
        },
        follow_redirects=True,
    )

    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Password must have at least 10 characters." in body
    assert User.query.filter_by(email="weak@example.com").first() is None


def test_login_rate_limit_blocks_repeated_invalid_attempts(client):
    token = csrf_token_from_response(client.get("/login"))
    form = {
        "_csrf_token": token,
        "email": "missing@example.com",
        "password": "WrongPass1",
    }

    for _ in range(8):
        response = client.post("/login", data=form, follow_redirects=True)
        assert response.status_code == 200

    response = client.post("/login", data=form, follow_redirects=True)
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Too many login attempts. Try again later." in body
    assert SystemLog.query.filter_by(category="auth").count() == 8


def test_debug_routes_requires_admin_even_when_dev_tools_enabled(client, flask_app):
    flask_app.config["DEV_TOOLS_ENABLED"] = True

    response = client.get("/debug/routes")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_core_game_routes_require_login(client):
    for path in ["/shop", "/deck-builder", "/missions", "/arena"]:
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


def test_admin_cannot_remove_own_or_last_admin(client):
    admin = create_user(
        username="admin",
        email="admin@example.com",
        password="StrongPass1",
        is_admin=True,
    )
    csrf_token = login_session(client, admin)

    response = client.post(
        f"/admin/users/{admin.id}/toggle-admin",
        data={"_csrf_token": csrf_token},
        follow_redirects=True,
    )

    db.session.refresh(admin)
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert admin.is_admin is True
    assert "You cannot remove your own admin access." in body


def test_password_reset_uses_stored_single_use_token(client):
    user = create_user(
        username="resetuser",
        email="reset@example.com",
        password="OldStrong1",
    )
    token = issue_password_reset_token(user)
    db.session.commit()

    csrf_token = csrf_token_from_response(client.get(f"/reset-password/{token}"))
    response = client.post(
        f"/reset-password/{token}",
        data={"_csrf_token": csrf_token, "password": "NewStrong1"},
        follow_redirects=True,
    )

    db.session.refresh(user)
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Password updated. You can login now." in body
    assert user.reset_token is None
    assert user.reset_token_expires_at is None
    assert user.check_password("NewStrong1")

    reused_response = client.get(f"/reset-password/{token}")
    assert reused_response.status_code == 200
    assert b"Password reset link expired." in reused_response.data


def test_socket_training_smoke_starts_match(client, flask_app, socketio_server):
    user = create_user(
        username="socketuser",
        email="socket@example.com",
        password="StrongPass1",
    )
    login_session(client, user)

    socket_client = socketio_server.test_client(flask_app, flask_test_client=client)

    assert socket_client.is_connected()

    socket_client.emit("join_training", {"difficulty": "normal"})
    received = socket_client.get_received()
    event_names = {packet["name"] for packet in received}

    assert "match_found" in event_names
    assert "game_state_update" in event_names
    assert active_matches

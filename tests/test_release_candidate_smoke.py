from models import MatchHistory, MatchTelemetry, SystemLog, User, db

from app import active_matches, issue_password_reset_token, socket_state
from conftest import create_user, csrf_token_from_response, login_session
from game.balance import STARTING_HP
from game.bot_ai import DIFFICULTY_PROFILES, choose_intent
from game.state import VALID_INTENTS


def test_homepage_adds_security_headers(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_support_page_renders_publicly(client):
    response = client.get("/support")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Support Ambitionz" in body
    assert "support.css" in body
    assert "Pix support key" in body


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


def test_register_grants_instant_access_even_if_auto_verify_is_disabled(client, flask_app):
    flask_app.config["BETA_AUTO_VERIFY"] = False
    token = csrf_token_from_response(client.get("/register"))

    response = client.post(
        "/register",
        data={
            "_csrf_token": token,
            "username": "instant",
            "email": "instant@example.com",
            "password": "StrongPass1",
        },
        follow_redirects=True,
    )

    user = User.query.filter_by(email="instant@example.com").first()
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Registered successfully. You can login and play now." in body
    assert user is not None
    assert user.is_verified is True
    assert user.account_status == "active"
    assert user.verified_at is not None


def test_login_normalizes_legacy_unverified_user(client):
    user = create_user(username="legacy", email="legacy@example.com", password="StrongPass1")
    user.is_verified = False
    user.account_status = "unverified"
    user.verified_at = None
    db.session.commit()

    token = csrf_token_from_response(client.get("/login"))
    response = client.post(
        "/login",
        data={
            "_csrf_token": token,
            "email": "legacy@example.com",
            "password": "StrongPass1",
        },
        follow_redirects=False,
    )

    db.session.refresh(user)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/welcome")
    assert user.is_verified is True
    assert user.account_status == "active"
    assert user.verified_at is not None


def test_resend_verification_route_normalizes_legacy_account(client):
    user = create_user(username="pending", email="pending@example.com", password="StrongPass1")
    user.is_verified = False
    user.account_status = "pending_verification"
    user.verified_at = None
    db.session.commit()

    token = csrf_token_from_response(client.get("/login"))
    response = client.post(
        "/resend-verification",
        data={"_csrf_token": token, "email": "pending@example.com"},
        follow_redirects=False,
    )

    db.session.refresh(user)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert user.is_verified is True
    assert user.account_status == "active"
    assert user.verified_at is not None


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


def test_admin_whoami_requires_admin(client):
    response = client.get("/admin/whoami")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    user = create_user(username="plainuser", email="plain@example.com", password="StrongPass1")
    login_session(client, user)
    response = client.get("/admin/whoami")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    admin = create_user(username="whoadmin", email="whoadmin@example.com", password="StrongPass1", is_admin=True)
    login_session(client, admin)
    response = client.get("/admin/whoami")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["is_admin"] is True
    assert payload["email"] == "whoadmin@example.com"


def test_hardened_routes_are_registered_from_security_ops(flask_app):
    for endpoint in ["admin_whoami", "forgot_password", "reset_password", "beta_event"]:
        assert flask_app.view_functions[endpoint].__module__ == "routes.security_ops"


def test_admin_system_shows_liveops_observability(client):
    admin = create_user(username="opsadmin", email="opsadmin@example.com", password="StrongPass1", is_admin=True)
    login_session(client, admin)
    db.session.add(SystemLog(level="warning", category="match", message="Matchmaking fallback bot match started"))
    db.session.add(SystemLog(level="warning", category="match", message="Player disconnected from active match"))
    db.session.add(SystemLog(level="error", category="match", message="Synthetic arena error"))
    db.session.commit()

    response = client.get("/admin/system")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Live Arena Ops" in body
    assert "Recent Bot Fallbacks" in body
    assert "Recent Disconnects" in body
    assert "Synthetic arena error" in body


def test_beta_event_filters_unknown_events_and_rate_limits(client, flask_app):
    flask_app.config["BETA_EVENT_RATE_LIMIT"] = 2
    flask_app.config["BETA_EVENT_RATE_WINDOW_SECONDS"] = 60

    for _ in range(3):
        response = client.post(
            "/api/beta-event",
            json={"event": "page_view", "path": "/arena", "source": "test"},
        )
        assert response.status_code == 204

    unknown_response = client.post(
        "/api/beta-event",
        json={"event": "script_probe", "path": "/admin", "source": "test"},
    )

    logs = SystemLog.query.filter_by(category="beta_event").all()
    assert unknown_response.status_code == 204
    assert len(logs) == 2
    assert all("page_view" in log.message for log in logs)


def test_forgot_password_rate_limit_blocks_extra_token_generation(client, flask_app):
    flask_app.config["PASSWORD_RESET_RATE_LIMIT"] = 2
    flask_app.config["PASSWORD_RESET_RATE_WINDOW_MINUTES"] = 60
    user = create_user(username="resetlimited", email="resetlimited@example.com", password="StrongPass1")

    for _ in range(2):
        csrf_token = csrf_token_from_response(client.get("/forgot-password"))
        response = client.post(
            "/forgot-password",
            data={"_csrf_token": csrf_token, "email": "resetlimited@example.com"},
            follow_redirects=True,
        )
        assert response.status_code == 200

    db.session.refresh(user)
    allowed_token_hash = user.reset_token
    csrf_token = csrf_token_from_response(client.get("/forgot-password"))
    response = client.post(
        "/forgot-password",
        data={"_csrf_token": csrf_token, "email": "resetlimited@example.com"},
        follow_redirects=True,
    )

    db.session.refresh(user)
    assert response.status_code == 200
    assert user.reset_token == allowed_token_hash
    assert SystemLog.query.filter_by(category="security", message="Password reset rate limit reached").count() == 1


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
    state_packet = next(packet for packet in received if packet["name"] == "game_state_update")
    state = state_packet["args"][0]

    assert "match_found" in event_names
    assert "game_state_update" in event_names
    assert state["me"]["energy"] == 2
    assert state["me"]["max_energy"] == 2
    assert state["me"]["ambition"] == 0
    assert state["enemy"]["intent"] == "Hidden"
    assert active_matches


def test_socket_public_queue_matches_two_players_before_bot_fallback(flask_app, socketio_server):
    flask_app.config["MATCHMAKING_BOT_FALLBACK_SECONDS"] = 0.25
    player_one = create_user(username="queueone", email="queueone@example.com")
    player_two = create_user(username="queuetwo", email="queuetwo@example.com")

    with flask_app.test_client() as client_one, flask_app.test_client() as client_two:
        login_session(client_one, player_one)
        login_session(client_two, player_two)
        socket_one = socketio_server.test_client(flask_app, flask_test_client=client_one)
        socket_two = socketio_server.test_client(flask_app, flask_test_client=client_two)
        socket_one.get_received()
        socket_two.get_received()

        socket_one.emit("join_queue")
        first_events = socket_one.get_received()

        assert "match_found" not in {event["name"] for event in first_events}
        assert socket_state["waiting_player"]["name"] == player_one.username

        socket_two.emit("join_queue")
        socketio_server.sleep(0.05)
        event_names_one = {event["name"] for event in socket_one.get_received()}
        event_names_two = {event["name"] for event in socket_two.get_received()}

        assert "match_found" in event_names_one
        assert "match_found" in event_names_two
        assert socket_state["waiting_player"] is None
        assert len(active_matches) == 1

        match = next(iter(active_matches.values()))
        assert match["p1"]["name"] == player_one.username
        assert match["p2"]["name"] == player_two.username
        assert not match.get("is_bot_match")

        socket_one.disconnect()
        socket_two.disconnect()


def test_socket_public_queue_falls_back_to_bot_after_timeout(flask_app, socketio_server):
    flask_app.config["MATCHMAKING_BOT_FALLBACK_SECONDS"] = 0.05
    player = create_user(username="fallback", email="fallback@example.com")

    with flask_app.test_client() as client:
        login_session(client, player)
        socket_client = socketio_server.test_client(flask_app, flask_test_client=client)
        socket_client.get_received()

        socket_client.emit("join_queue")
        socketio_server.sleep(0.12)
        received = socket_client.get_received()
        event_names = {event["name"] for event in received}

        assert "match_found" in event_names
        assert socket_state["waiting_player"] is None
        assert len(active_matches) == 1

        match = next(iter(active_matches.values()))
        assert match.get("is_bot_match") is True
        assert match.get("matchmaking_fallback") is True
        assert match["p2"]["name"] == "Ambitionz Bot"

        socket_client.disconnect()


def test_socket_public_queue_can_be_cancelled(flask_app, socketio_server):
    flask_app.config["MATCHMAKING_BOT_FALLBACK_SECONDS"] = 0.2
    player = create_user(username="cancelqueue", email="cancelqueue@example.com")

    with flask_app.test_client() as client:
        login_session(client, player)
        socket_client = socketio_server.test_client(flask_app, flask_test_client=client)
        socket_client.get_received()

        socket_client.emit("join_queue")
        assert socket_state["waiting_player"]["name"] == player.username

        socket_client.emit("cancel_queue")
        socketio_server.sleep(0.25)
        received = socket_client.get_received()
        statuses = [
            event["args"][0].get("status")
            for event in received
            if event["name"] == "matchmaking_status"
        ]

        assert "cancelled" in statuses
        assert socket_state["waiting_player"] is None
        assert not active_matches

        socket_client.disconnect()


def test_socket_disconnect_records_disconnect_telemetry(flask_app, socketio_server):
    flask_app.config["MATCHMAKING_BOT_FALLBACK_SECONDS"] = 1
    player_one = create_user(username="leaver", email="leaver@example.com")
    player_two = create_user(username="stayer", email="stayer@example.com")

    with flask_app.test_client() as client_one, flask_app.test_client() as client_two:
        login_session(client_one, player_one)
        login_session(client_two, player_two)
        socket_one = socketio_server.test_client(flask_app, flask_test_client=client_one)
        socket_two = socketio_server.test_client(flask_app, flask_test_client=client_two)
        socket_one.get_received()
        socket_two.get_received()

        socket_one.emit("join_queue")
        socket_two.emit("join_queue")
        socketio_server.sleep(0.05)
        assert active_matches

        socket_one.disconnect()
        socketio_server.sleep(0.05)

        history = MatchHistory.query.order_by(MatchHistory.id.desc()).first()
        telemetry = MatchTelemetry.query.order_by(MatchTelemetry.id.desc()).first()

        assert not active_matches
        assert history is not None
        assert history.result == "DISCONNECT"
        assert history.winner_name == player_two.username
        assert telemetry is not None
        assert telemetry.ending_reason == "disconnect"
        assert telemetry.mode == "pvp"

        socket_two.disconnect()


def test_bot_ai_keeps_unleash_out_of_intent_selection():
    for profile in DIFFICULTY_PROFILES.values():
        assert "Overreach" not in profile["intent_weights"]

    bot = {
        "hp": STARTING_HP,
        "energy": 6,
        "intent": "Strike",
        "hand": [
            {
                "type": "Monster",
                "cost": 1,
                "power": 1400,
                "sigil": "Fury",
                "role": "Aggressor",
            }
        ],
    }
    opponent = {"hp": 2000}

    for difficulty in DIFFICULTY_PROFILES:
        assert choose_intent(bot, opponent, difficulty) in VALID_INTENTS

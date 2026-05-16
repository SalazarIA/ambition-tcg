import re
from datetime import datetime, timedelta, timezone

from models import BoosterHistory, EconomyLedger, FeedbackReport, InventoryOwnership, MatchHistory, MatchTelemetry, RetentionEvent, SystemLog, User, UserMission, db

from app import active_matches, emit_arena_state_v8, end_match, issue_password_reset_token, player_rooms, socket_state, socketio
from conftest import create_user, csrf_token_from_response, login_session
from game.balance import STARTING_HP
from game.bot_ai import DIFFICULTY_PROFILES, choose_intent
from game.cards import CARD_CATALOG
from game.progression import today_key
from game.state import VALID_INTENTS


def test_homepage_adds_security_headers(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_service_worker_is_served_from_root_scope(client):
    response = client.get("/service-worker.js")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert response.headers["Service-Worker-Allowed"] == "/"
    assert "text/javascript" in response.content_type
    assert "ambitionz-web-app-v190" in body


def test_tutorial_renders_narrative_onboarding(client):
    response = client.get("/tutorial")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "First Oath" in body
    assert "Strike" in body
    assert "Guard" in body
    assert "Focus" in body
    assert "Ready and Resolve" in body
    assert 'href="/training"' in body
    assert 'href="/collection"' in body
    assert 'href="/deck-builder"' in body


def test_public_home_renders_product_entry_and_real_routes(client):
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Ambitionz" in body
    assert "Jogar Agora" in body
    assert "ambitionzgame.com" in body
    assert 'href="/training"' in body
    assert 'href="/arena"' in body
    assert 'href="/collection"' in body
    assert 'href="/deck-builder"' in body
    assert 'href="/leaderboard"' in body
    assert 'href="/roadmap"' in body
    assert 'href="/feedback"' in body
    assert "Ambitionz is a tactical card battler in public beta." in body
    assert "Beta Onboarding" in body
    assert "First Session Questline" in body
    assert "ambitionz_first_session_questline_dismissed_v1" in body
    assert 'href="/login"' in body
    assert 'href="/register"' in body


def test_public_beta_roadmap_and_feedback_routes(client):
    roadmap_response = client.get("/roadmap")
    roadmap_body = roadmap_response.get_data(as_text=True)

    assert roadmap_response.status_code == 200
    assert "Roadmap & Patch Notes" in roadmap_body
    assert "Public Beta RC V5" in roadmap_body
    assert "Arena BE2 polish" in roadmap_body
    assert "Public Beta RC Checklist" in roadmap_body
    assert "Economy beta" in roadmap_body
    assert 'href="/feedback"' in roadmap_body

    feedback_response = client.get("/feedback")
    feedback_body = feedback_response.get_data(as_text=True)

    assert feedback_response.status_code == 200
    assert "Beta Feedback" in feedback_body
    assert 'name="category"' in feedback_body
    assert 'name="message"' in feedback_body
    assert 'name="contact"' in feedback_body


def test_public_beta_feedback_post_accepts_guest_report(client):
    token = csrf_token_from_response(client.get("/feedback"))
    response = client.post(
        "/feedback",
        data={
            "_csrf_token": token,
            "category": "balance",
            "severity": "normal",
            "message": "Fire pressure felt too strong after a hard Training run.",
            "page_url": "/training",
            "contact": "tester@example.com",
        },
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Feedback sent" in body
    report = FeedbackReport.query.order_by(FeedbackReport.id.desc()).first()
    assert report is not None
    assert report.user_id is None
    assert report.username == "Guest Beta Tester"
    assert report.category == "balance"
    assert "tester@example.com" in report.message


def test_public_beta_telemetry_and_feedback_api_contract(client):
    telemetry_response = client.post(
        "/api/beta/telemetry",
        json={
            "event": "visit_home",
            "page": "/",
            "metadata": {"source": "smoke", "detail": "rc_v5"},
        },
    )
    telemetry_payload = telemetry_response.get_json()

    assert telemetry_response.status_code == 200
    assert telemetry_payload["ok"] is True
    assert telemetry_payload["event"] == "visit_home"
    assert RetentionEvent.query.filter_by(event_key="visit_home").count() == 1

    invalid_response = client.post(
        "/api/beta/telemetry",
        json={"event": "script_probe", "page": "/admin"},
    )
    invalid_payload = invalid_response.get_json()

    assert invalid_response.status_code == 400
    assert invalid_payload["ok"] is False
    assert invalid_payload["error"] == "invalid_event"

    feedback_response = client.post(
        "/api/beta/feedback",
        json={
            "type": "bug",
            "message": "The beta feedback widget submitted from Roadmap during smoke testing.",
            "page": "/roadmap",
        },
    )
    feedback_payload = feedback_response.get_json()
    report = FeedbackReport.query.order_by(FeedbackReport.id.desc()).first()

    assert feedback_response.status_code == 200
    assert feedback_payload["ok"] is True
    assert feedback_payload["stored"] in {"feedback_reports", "jsonl"}
    assert report is not None
    assert report.category == "bug"
    assert "Page: /roadmap" in report.message

    short_feedback = client.post(
        "/api/beta/feedback",
        json={"type": "suggestion", "message": "short", "page": "/roadmap"},
    )
    assert short_feedback.status_code == 400


def test_training_3d_renderer_flag_loads_three_bundle(client):
    user = create_user(username="renderer3d", email="renderer3d@example.com")
    login_session(client, user)

    response = client.get("/training?renderer=3d")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'data-arena-renderer="3d"' in body
    assert "css/arena3d.css" in body
    assert "dist/arena3d/arena3d.js" in body


def test_training_renders_bot_polish_and_result_contract(client):
    user = create_user(username="trainingpolish", email="trainingpolish@example.com")
    login_session(client, user)

    response = client.get("/training")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="az48-training-panel"' in body
    assert "Training Mode" in body
    assert "Practice intent, card, lane, Ready." in body
    assert "Easy" in body
    assert "Normal" in body
    assert "Hard" in body
    assert 'id="az48-training-result"' in body
    assert "Jogar novamente" in body
    assert 'href="/collection"' in body
    assert 'href="/deck-builder"' in body
    assert 'href="/"' in body


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


def test_profile_and_progression_render_basic_retention_summary(client):
    user = create_user(username="profilehero", email="profilehero@example.com")
    user.wins = 2
    user.losses = 1
    user.xp = 45
    user.level = 2
    user.first_training_completed = True
    history = MatchHistory(
        player1_id=user.id,
        player2_id=None,
        winner_id=user.id,
        player1_name=user.username,
        player2_name="Ambitionz Bot",
        winner_name=user.username,
        result="FINISHED",
        player1_final_hp=12,
        player2_final_hp=0,
        total_rounds=4,
        battle_log_json='["Round started", "Training complete"]',
    )
    db.session.add(
        history
    )
    db.session.commit()
    login_session(client, user)

    profile_response = client.get("/profile")
    profile_body = profile_response.get_data(as_text=True)
    assert profile_response.status_code == 200
    assert 'id="az-profile-summary"' in profile_body
    assert "profilehero" in profile_body
    assert "Most Played" in profile_body
    assert "Training" in profile_body
    assert "Latest Result" in profile_body
    assert "Win" in profile_body
    assert 'id="az-profile-first-session-questline-v1"' in profile_body
    assert 'id="az-profile-deck-readiness-coach-v1"' in profile_body

    progression_response = client.get("/progression")
    progression_body = progression_response.get_data(as_text=True)
    assert progression_response.status_code == 200
    assert 'id="az-progression-summary"' in progression_body
    assert "45/200 XP" in progression_body
    assert "3 matches played" in progression_body
    assert 'id="az-progression-first-session-questline-v1"' in progression_body
    assert 'id="az-progression-deck-readiness-coach-v1"' in progression_body

    history_response = client.get(f"/match-history/{history.id}")
    history_body = history_response.get_data(as_text=True)
    assert history_response.status_code == 200
    assert "Match Details" in history_body
    assert "Ambitionz Bot" in history_body
    assert "Round started" in history_body


def test_collection_and_deck_builder_v2_render_and_save(client):
    user = create_user(username="deckv2", email="deckv2@example.com")
    csrf_token = login_session(client, user)

    collection_response = client.get("/collection")
    collection_body = collection_response.get_data(as_text=True)
    assert collection_response.status_code == 200
    assert 'id="az-collection-summary"' in collection_body
    assert 'id="az-collection-desire-loop"' in collection_body
    assert "Total Owned" in collection_body
    assert "Unique Cards" in collection_body
    assert "Collection Progress" in collection_body

    deck_response = client.get("/deck-builder")
    deck_body = deck_response.get_data(as_text=True)
    assert deck_response.status_code == 200
    assert 'id="az-deck-validation-summary"' in deck_body
    assert "30 cards" in deck_body
    assert "Duplicate Cards" in deck_body
    assert "Save Active Deck" in deck_body
    assert 'id="az-deck-readiness-coach-v1"' in deck_body
    assert "Deck Readiness Coach" in deck_body

    selected_cards = re.findall(r'name="deck_cards" value="([^"]+)"', deck_body)
    assert len(selected_cards) == 30

    save_response = client.post(
        "/deck-builder",
        data={"_csrf_token": csrf_token, "deck_cards": selected_cards},
        follow_redirects=True,
    )
    save_body = save_response.get_data(as_text=True)
    assert save_response.status_code == 200
    assert "Deck saved successfully." in save_body


def test_main_product_routes_smoke(client):
    user = create_user(username="routesmoke", email="routesmoke@example.com")
    login_session(client, user)

    route_expectations = {
        "/": "Ambitionz",
        "/health": "Ambitionz",
        "/training": "Training Mode",
        "/collection": "Collection Progress",
        "/deck-builder": "Active Deck Status",
        "/profile": "Player Snapshot",
        "/campaign": "Beta Campaign",
        "/daily": "Daily Check-In",
        "/missions": "Beta Journey Missions",
        "/progression": "Beta Journey",
        "/match-history": "No matches yet",
        "/roadmap": "Roadmap & Patch Notes",
        "/feedback": "Beta Feedback",
        "/leaderboard": "Beta Leaderboard",
        "/ranking": "Ranking Beta",
    }

    for path, expected_text in route_expectations.items():
        response = client.get(path)
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert expected_text in body


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


def test_retention_event_filters_unknown_events_and_rate_limits(client, flask_app):
    flask_app.config["RETENTION_EVENT_RATE_LIMIT"] = 2
    flask_app.config["RETENTION_EVENT_RATE_WINDOW_SECONDS"] = 60

    for _ in range(3):
        response = client.post(
            "/api/retention/event",
            json={"event_key": "page_view", "page": "/arena", "metadata": {"source": "test"}},
        )
        assert response.status_code == 200

    unknown_response = client.post(
        "/api/retention/event",
        json={"event_key": "script_probe", "page": "/admin", "metadata": {"probe": True}},
    )

    logs = RetentionEvent.query.all()
    assert unknown_response.status_code == 200
    assert len(logs) == 2
    assert all(log.event_key == "page_view" for log in logs)


def test_beta_retention_product_events_are_accepted(client):
    for event_key in [
        "home_cta_play",
        "tutorial_start",
        "training_start_click",
        "training_result_view",
        "collection_view",
        "deck_builder_view",
        "deck_save_attempt",
        "feedback_submit",
        "campaign_view",
        "mission_cta_click",
        "daily_view",
        "feedback_view",
        "onboarding_view",
        "roadmap_view",
    ]:
        response = client.post(
            "/api/retention/event",
            json={"event_key": event_key, "page": "/beta", "metadata": {"source": "test"}},
        )
        assert response.status_code == 200

    logs = RetentionEvent.query.order_by(RetentionEvent.id.asc()).all()
    assert [log.event_key for log in logs] == [
        "home_cta_play",
        "tutorial_start",
        "training_start_click",
        "training_result_view",
        "collection_view",
        "deck_builder_view",
        "deck_save_attempt",
        "feedback_submit",
        "campaign_view",
        "mission_cta_click",
        "daily_view",
        "feedback_view",
        "onboarding_view",
        "roadmap_view",
    ]


def test_beta_loop_v1_events_are_accepted(client):
    for event_key in [
        "campaign_start",
        "campaign_result",
        "mission_progress",
        "mission_complete",
        "daily_claim",
        "daily_claimed",
        "match_recorded",
        "mission_reward_claimed",
        "shop_purchase",
        "booster_opened",
        "currency_credit",
        "currency_debit",
        "xp_awarded",
        "post_match_summary_view",
    ]:
        response = client.post(
            "/api/retention/event",
            json={"event_key": event_key, "page": "/beta-loop", "metadata": {"source": "test"}},
        )
        assert response.status_code == 200

    logs = RetentionEvent.query.order_by(RetentionEvent.id.asc()).all()
    assert [log.event_key for log in logs] == [
        "campaign_start",
        "campaign_result",
        "mission_progress",
        "mission_complete",
        "daily_claim",
        "daily_claimed",
        "match_recorded",
        "mission_reward_claimed",
        "shop_purchase",
        "booster_opened",
        "currency_credit",
        "currency_debit",
        "xp_awarded",
        "post_match_summary_view",
    ]


def test_campaign_start_sets_training_context(client):
    user = create_user(username="campaignv1", email="campaignv1@example.com")
    login_session(client, user)

    campaign_response = client.get("/campaign")
    campaign_body = campaign_response.get_data(as_text=True)
    assert campaign_response.status_code == 200
    assert 'data-chapter-id="first_signal"' in campaign_body
    assert "/campaign/start/first_signal" in campaign_body

    start_response = client.get("/campaign/start/first_signal", follow_redirects=False)
    assert start_response.status_code == 302
    assert "campaign_chapter_id=first_signal" in start_response.headers["Location"]

    training_response = client.get(start_response.headers["Location"])
    training_body = training_response.get_data(as_text=True)
    assert training_response.status_code == 200
    assert 'data-page-kind="campaign"' in training_body
    assert '"chapter_id": "first_signal"' in training_body
    assert "First Signal" in training_body

    event_keys = [event.event_key for event in RetentionEvent.query.order_by(RetentionEvent.id.asc()).all()]
    assert "campaign_view" in event_keys
    assert "campaign_start" in event_keys


def test_daily_claim_is_persistent_and_once_per_day(client):
    user = create_user(username="dailyv1", email="dailyv1@example.com")
    csrf_token = login_session(client, user)

    first_response = client.post(
        "/daily/claim",
        data={"_csrf_token": csrf_token},
        follow_redirects=True,
    )

    db.session.refresh(user)
    first_total_xp = int(user.total_xp or 0)
    first_gold = int(user.coins or 0)
    assert first_response.status_code == 200
    assert user.daily_last_checkin_date == today_key()
    assert user.daily_streak == 1
    assert user.daily_best_streak == 1
    assert first_total_xp == 35
    assert first_gold == 1075

    mission = UserMission.query.filter_by(user_id=user.id, mission_key="return_daily", mission_date="beta").first()
    assert mission is not None
    assert mission.progress == 1
    assert mission.is_complete is True

    second_response = client.post(
        "/daily/claim",
        data={"_csrf_token": csrf_token},
        follow_redirects=True,
    )
    db.session.refresh(user)
    assert second_response.status_code == 200
    assert int(user.total_xp or 0) == first_total_xp
    assert int(user.coins or 0) == first_gold
    assert user.daily_streak == 1

    event_keys = [event.event_key for event in RetentionEvent.query.order_by(RetentionEvent.id.asc()).all()]
    assert "daily_claim" in event_keys
    assert "daily_claimed" in event_keys
    assert "currency_credit" in event_keys
    assert "xp_awarded" in event_keys


def test_daily_return_loop_scales_second_day_reward(client):
    user = create_user(username="dailyv2", email="dailyv2@example.com")
    csrf_token = login_session(client, user)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    user.daily_last_checkin_date = yesterday
    user.daily_streak = 1
    user.daily_best_streak = 1
    user.coins = 1000
    db.session.commit()

    response = client.post(
        "/daily/claim",
        data={"_csrf_token": csrf_token},
        follow_redirects=True,
    )

    db.session.refresh(user)
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert user.daily_streak == 2
    assert user.daily_best_streak == 2
    assert int(user.total_xp or 0) == 40
    assert int(user.coins or 0) == 1090
    assert "40 XP" in body
    assert "90 Gold" in body


def test_wallet_gold_api_contract_for_guest_and_logged_user(client):
    guest_response = client.get("/api/wallet")
    guest_payload = guest_response.get_json()

    assert guest_response.status_code == 200
    assert guest_payload["ok"] is True
    assert guest_payload["currency"] == "Gold"
    assert guest_payload["is_guest"] is True
    assert guest_payload["balance"] == 300

    user = create_user(username="walletv1", email="walletv1@example.com")
    user.coins = 125
    db.session.commit()
    csrf_token = login_session(client, user)

    balance_response = client.get("/api/wallet")
    balance_payload = balance_response.get_json()
    assert balance_payload["balance"] == 125
    assert balance_payload["currency"] == "Gold"

    credit_response = client.post(
        "/api/wallet/credit",
        json={"amount": 25},
        headers={"X-CSRFToken": csrf_token},
    )
    assert credit_response.status_code == 200
    assert credit_response.get_json()["balance"] == 150

    debit_response = client.post(
        "/api/wallet/debit",
        json={"amount": 70},
        headers={"X-CSRFToken": csrf_token},
    )
    assert debit_response.status_code == 200
    assert debit_response.get_json()["balance"] == 80

    invalid_response = client.post(
        "/api/wallet/debit",
        json={"amount": 999},
        headers={"X-CSRFToken": csrf_token},
    )
    invalid_payload = invalid_response.get_json()
    db.session.refresh(user)

    assert invalid_response.status_code == 400
    assert invalid_payload["error"] == "insufficient_gold"
    assert invalid_payload["balance"] == 80
    assert int(user.coins or 0) == 80
    assert EconomyLedger.query.filter_by(user_id=user.id).count() >= 2


def test_shop_purchase_spends_gold_and_opens_booster_once(client):
    user = create_user(username="shopv2", email="shopv2@example.com")
    user.coins = 1000
    db.session.commit()
    csrf_token = login_session(client, user)

    shop_response = client.get("/shop")
    shop_body = shop_response.get_data(as_text=True)
    token_match = re.search(r'name="purchase_token" value="([^"]+)"', shop_body)
    assert shop_response.status_code == 200
    assert token_match
    assert "Basic Booster Pack" in shop_body
    assert "Daily Deal" in shop_body
    assert "Founder / Supporter Pack" in shop_body
    assert "No real-money checkout is active" in shop_body

    response = client.post(
        "/shop/purchase",
        data={
            "_csrf_token": csrf_token,
            "purchase_token": token_match.group(1),
            "offer_key": "basic_booster",
        },
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)
    db.session.refresh(user)

    assert response.status_code == 200
    assert "Cards Pulled" in body
    assert "Gold" in body
    assert int(user.coins or 0) == 700
    assert BoosterHistory.query.filter_by(user_id=user.id).count() == 1
    assert InventoryOwnership.query.filter_by(user_id=user.id).count() >= 1

    duplicate_response = client.post(
        "/shop/purchase",
        data={
            "_csrf_token": csrf_token,
            "purchase_token": token_match.group(1),
            "offer_key": "basic_booster",
        },
        follow_redirects=True,
    )
    db.session.refresh(user)

    assert duplicate_response.status_code == 200
    assert BoosterHistory.query.filter_by(user_id=user.id).count() == 1
    assert int(user.coins or 0) == 700

    event_keys = [event.event_key for event in RetentionEvent.query.order_by(RetentionEvent.id.asc()).all()]
    assert "shop_purchase" in event_keys
    assert "booster_opened" in event_keys
    assert "currency_debit" in event_keys


def test_booster_open_api_returns_cards_and_prevents_negative_gold(client):
    user = create_user(username="boosterv1", email="boosterv1@example.com")
    user.coins = 300
    db.session.commit()
    csrf_token = login_session(client, user)

    response = client.post(
        "/api/booster/open",
        json={"offer_key": "basic_booster", "seed": 81088},
        headers={"X-CSRFToken": csrf_token},
    )
    payload = response.get_json()
    db.session.refresh(user)

    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["balance"] == 0
    assert len(payload["cards"]) == 5
    assert all(card.get("id") for card in payload["cards"])
    assert BoosterHistory.query.filter_by(user_id=user.id).count() == 1
    assert int(user.coins or 0) == 0

    second_response = client.post(
        "/api/booster/open",
        json={"offer_key": "basic_booster", "seed": 81088},
        headers={"X-CSRFToken": csrf_token},
    )
    second_payload = second_response.get_json()
    db.session.refresh(user)

    assert second_response.status_code == 402
    assert second_payload["error"] == "insufficient_gold"
    assert second_payload["balance"] == 0
    assert int(user.coins or 0) == 0


def test_beta_missions_progress_from_real_routes(client):
    user = create_user(username="missionv1", email="missionv1@example.com")
    csrf_token = login_session(client, user)

    assert client.get("/collection").status_code == 200
    assert client.get("/deck-builder").status_code == 200
    assert client.post(
        "/complete-onboarding",
        data={"_csrf_token": csrf_token},
        follow_redirects=False,
    ).status_code == 302

    missions = {
        mission.mission_key: mission
        for mission in UserMission.query.filter_by(user_id=user.id, mission_date="beta").all()
    }

    assert missions["view_collection"].progress == 1
    assert missions["view_collection"].is_complete is True
    assert missions["save_or_validate_deck"].progress == 1
    assert missions["save_or_validate_deck"].is_complete is True
    assert missions["complete_tutorial"].progress == 1
    assert missions["complete_tutorial"].is_complete is True

    claim_response = client.post(
        f"/missions/claim/{missions['view_collection'].id}",
        data={"_csrf_token": csrf_token},
        follow_redirects=True,
    )
    db.session.refresh(user)
    db.session.refresh(missions["view_collection"])
    assert claim_response.status_code == 200
    assert missions["view_collection"].is_claimed is True
    assert user.total_xp == 20
    assert user.coins == 1020
    assert EconomyLedger.query.filter_by(user_id=user.id, source="mission_claim").count() == 1


def test_match_end_tracks_mission_v2_combat_progress(client, monkeypatch):
    user = create_user(username="missionv2", email="missionv2@example.com")
    emitted = []
    fire_card = next(card for card in CARD_CATALOG if card["element"] == "Fire")

    def fake_emit(event, payload=None, **kwargs):
        emitted.append((event, payload, kwargs))

    monkeypatch.setattr(socketio, "emit", fake_emit)

    room_id = "training_test_mission_v2"
    active_matches[room_id] = {
        "p1": {
            "sid": "sid-mission-v2",
            "user_id": user.id,
            "name": user.username,
            "hp": 18,
            "deck": [],
            "hand": [],
            "graveyard": [],
        },
        "p2": {
            "sid": "bot-mission-v2",
            "name": "Ambitionz Bot",
            "is_bot": True,
            "hp": 0,
            "deck": [],
            "hand": [],
            "graveyard": [],
        },
        "round": 2,
        "training": True,
        "is_bot_match": True,
        "bot_difficulty": "normal",
        "logs": [],
        "combat_log": [
            {"type": "intent_selected", "side": "player", "intent": "Strike"},
            {"type": "card_played", "side": "player", "card_id": fire_card["id"], "card_name": fire_card["name"]},
            {"type": "hero_damage", "attacker_side": "player", "target_side": "opponent", "damage": 12},
            {"type": "ambition_gain", "side": "player", "amount": 3},
        ],
    }
    player_rooms["sid-mission-v2"] = room_id

    end_match(room_id, "p1")

    missions = {
        mission.mission_key: mission
        for mission in UserMission.query.filter_by(user_id=user.id, mission_date="beta").all()
    }

    assert missions["win_training_match"].progress == 1
    assert missions["deal_damage_total"].progress == 12
    assert missions["play_cards_total"].progress == 1
    assert missions["play_fire_card"].progress == 1
    assert missions["gain_ambition_total"].progress == 3
    assert missions["use_strike_intent"].progress == 1

    summary = next(payload for event, payload, _kwargs in emitted if event == "post_match_summary")
    mission_names = {mission["mission_key"] for mission in summary["mission_progress"]}
    assert {"deal_damage_total", "play_cards_total", "play_fire_card"}.issubset(mission_names)
    assert summary["next_best_action"]["kind"] in {"shop", "missions", "progression", "training", "deck"}
    assert summary["next_best_action"]["label"]
    assert summary["next_actions"]["shop"].endswith("/shop")
    assert summary["next_actions"]["primary"] == summary["next_best_action"]["url"]


def test_campaign_match_end_records_history_xp_missions_and_summary(client, monkeypatch):
    user = create_user(username="matchv1", email="matchv1@example.com")
    emitted = []

    def fake_emit(event, payload=None, **kwargs):
        emitted.append((event, payload, kwargs))

    monkeypatch.setattr(socketio, "emit", fake_emit)

    room_id = "training_test_campaign"
    active_matches[room_id] = {
        "p1": {
            "sid": "sid-campaign",
            "user_id": user.id,
            "name": user.username,
            "hp": 18,
            "deck": [],
            "hand": [],
            "graveyard": [],
        },
        "p2": {
            "sid": "bot-campaign",
            "name": "Ambitionz Bot",
            "is_bot": True,
            "hp": 0,
            "deck": [],
            "hand": [],
            "graveyard": [],
        },
        "round": 3,
        "training": True,
        "is_bot_match": True,
        "bot_difficulty": "normal",
        "campaign_chapter_id": "first_signal",
        "campaign": {
            "chapter_id": "first_signal",
            "title": "First Signal",
            "difficulty": "easy",
            "reward": "35 XP beta + campaign mission progress.",
        },
        "logs": [{"type": "log", "message": "Campaign finished"}],
    }
    player_rooms["sid-campaign"] = room_id

    end_match(room_id, "p1")
    db.session.refresh(user)

    history = MatchHistory.query.order_by(MatchHistory.id.desc()).first()
    assert history is not None
    assert history.mode == "campaign"
    assert history.campaign_chapter_id == "first_signal"
    assert history.xp_gained > 0
    assert user.total_xp >= history.xp_gained
    assert room_id not in active_matches

    training_mission = UserMission.query.filter_by(user_id=user.id, mission_key="play_training_match", mission_date="beta").first()
    campaign_mission = UserMission.query.filter_by(user_id=user.id, mission_key="play_campaign_chapter", mission_date="beta").first()
    assert training_mission is not None and training_mission.progress == 1
    assert campaign_mission is not None and campaign_mission.progress == 1

    summaries = [payload for event, payload, _kwargs in emitted if event == "post_match_summary"]
    assert summaries
    assert summaries[0]["history_id"] == history.id
    assert summaries[0]["campaign_chapter_id"] == "first_signal"
    assert summaries[0]["xp_gained"] == history.xp_gained

    event_keys = {event.event_key for event in RetentionEvent.query.all()}
    assert {"campaign_result", "match_recorded", "xp_awarded", "mission_progress"}.issubset(event_keys)


def test_test_grant_routes_require_admin_dev_tools(client, flask_app):
    user = create_user(username="grantuser", email="grantuser@example.com", password="StrongPass1")
    admin = create_user(username="grantadmin", email="grantadmin@example.com", password="StrongPass1", is_admin=True)

    user_csrf = login_session(client, user)
    response = client.post("/inventory/test-card-grant", data={"_csrf_token": user_csrf}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    admin_csrf = login_session(client, admin)
    response = client.post("/economy/test-premium-grant", data={"_csrf_token": admin_csrf}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin")

    flask_app.config["DEV_TOOLS_ENABLED"] = True
    response = client.post("/economy/test-premium-grant", data={"_csrf_token": admin_csrf}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/economy/premium-ledger")


def test_arena_state_v8_emit_does_not_recurse(monkeypatch):
    emitted = []

    def fake_emit(event, payload=None, **kwargs):
        emitted.append((event, payload, kwargs))

    monkeypatch.setattr(socketio, "emit", fake_emit)

    match = {
        "p1": {
            "sid": "sid-one",
            "name": "One",
            "hp": 3600,
            "energy": 2,
            "hand": [],
            "deck": [],
        },
        "p2": {
            "sid": "sid-two",
            "name": "Two",
            "hp": 3600,
            "energy": 2,
            "hand": [],
            "deck": [],
        },
        "round": 1,
        "phase": "Set Phase",
    }

    emit_arena_state_v8(match, phase="sync")

    event_names = [event for event, _payload, _kwargs in emitted]
    assert event_names.count("arena_state_update") == 2
    assert event_names.count("game_state_update") == 2
    assert len(emitted) == 4


def test_legacy_socket_handlers_remain_bound_after_az48_aliases(flask_app):
    handlers = socketio.server.handlers["/"]

    assert handlers["set_intent"].__name__ == "set_intent"
    assert handlers["declare_ready"].__name__ == "declare_ready"
    assert handlers["arena_command_v1"].__name__ == "arena_command_v1"
    assert handlers["az48_set_intent"].__name__ == "az48_set_intent"
    assert handlers["az48_declare_ready"].__name__ == "az48_declare_ready"


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
        assert match.get("be2") is True
        assert match["player"]["name"] == player_one.username
        assert match["opponent"]["name"] == player_two.username
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
        assert match.get("be2") is True
        assert match.get("is_bot_match") is True
        assert match.get("matchmaking_fallback") is True
        assert match["opponent"]["name"] == "Ambitionz Bot"
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

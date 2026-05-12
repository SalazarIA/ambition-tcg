from services.arena_clean_state import build_arena_clean_state, build_arena_clean_payloads
from services.economy.inventory_migration import migrate_legacy_collection_to_inventory, ensure_user_has_playable_inventory, repair_user_inventory_and_deck
from services.economy.deck_inventory import owned_card_ids_for_user, validate_deck_against_inventory, build_auto_deck_from_inventory
from services.economy.inventory_cards import build_collection_from_inventory, user_inventory_counts
from services.economy.inventory_ownership import grant_card, remove_card, get_quantity
from services.economy.premium_currency import credit_gems, debit_gems
import json
import hmac
import hashlib
import os
import secrets
from collections import Counter
from datetime import datetime, timezone, timedelta

import itsdangerous
from flask import make_response, Flask, abort, flash, redirect, render_template, request, session, url_for, jsonify
from flask_socketio import SocketIO
from flask_migrate import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import text as sql_text
from sqlalchemy import inspect as sql_inspect

from config import Config
from game.battle import resolve_battle
from game.cards import CARD_CATALOG, card_sort_key
from game.deck import (
    build_playable_deck,
    collection_summary,
    deck_summary,
    draw_starting_hand,
    load_card_ids,
    validate_deck,
    full_deck_analysis,
    deck_analysis_v115,
    create_starter_deck_from_collection,
)
from models import ensure_liveops_schema, BetaInvite, SystemLog, BoosterHistory, FeedbackReport, MatchHistory, User, UserMission, db, ensure_database_schema, RetentionEvent, EconomyLedger, UserCosmetic, RewardLedger, ensure_reward_ledger_schema, PremiumCurrencyLedger, ensure_premium_currency_schema, InventoryOwnership, InventoryOwnershipLedger, ensure_inventory_ownership_schema
from game.progression import award_xp, claim_mission, ensure_daily_missions, increment_mission
from services.admin.cleanup_service import clear_gameplay_data, delete_non_admin_users
from services.battle_summary import build_match_summary_lines
from services.card_stats import update_card_stats_after_match
from services.arena_payload import build_arena_payloads_for_match, build_arena_state_payload
from services.arena_command_v1 import arena_command_error_payload
from services.match_engine_facade import MatchEngineFacade
from services.match_payloads import (
    build_game_state_payloads,
    build_post_match_payload,
    find_player_key,
    history_result_for_ending,
    perspective_battle_events,
)
from services.reward_tuning import reward_line
from services.match_telemetry import record_match_telemetry
from services.email_service import send_password_reset_email, send_smtp_test_email, is_smtp_configured
from services.security.headers import apply_security_headers
from services.security.password_policy import password_policy_errors
from services.security.rate_limit import SlidingWindowRateLimiter, request_rate_limit_key
from routes.security_ops import register_security_ops_routes
from game.rules import can_pay_cost, pay_card_cost, reset_player_energy
from game.engine import register_card_played_for_ambition, request_unleash, cancel_unleash
from game.state import create_player_state, set_player_intent
from game.matchmaking import generate_private_room_code, is_valid_room_code, normalize_room_code
from game.bot_ai import bot_choose_play
from game.rewards import apply_match_rewards
from services.economy_service import cosmetic_catalog_for_user, grant_cosmetic, spend_currency, add_currency, PREMIUM_CURRENCY_KEY
from game.match_utils import safe_user_id, player_display_name, get_match_result_label
from game.card_view import enrich_cards_for_view
from game.state import create_player_state, normalize_intent


app = Flask(__name__)

app.config["SMTP_HOST"] = os.environ.get("SMTP_HOST")
app.config["SMTP_PORT"] = int(os.environ.get("SMTP_PORT", "587"))
app.config["SMTP_USERNAME"] = os.environ.get("SMTP_USERNAME")
app.config["SMTP_PASSWORD"] = os.environ.get("SMTP_PASSWORD")
app.config["SMTP_USE_TLS"] = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes", "on")
app.config["MAIL_FROM"] = os.environ.get("MAIL_FROM")
app.config.from_object(Config)

app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
    x_port=1,
    x_prefix=1,
)

db.init_app(app)
migrate = Migrate(app, db)

socketio_allowed_origins = Config.socketio_cors_allowed_origins()
app.config["SOCKETIO_CORS_EFFECTIVE_ORIGINS"] = socketio_allowed_origins

socketio = SocketIO(
    app,
    async_mode="threading",
    cors_allowed_origins=socketio_allowed_origins,
    manage_session=False,
)

serializer = itsdangerous.URLSafeTimedSerializer(app.config["SECRET_KEY"])

active_matches = {}
player_rooms = {}
socket_state = {
    "waiting_player": None,
    "waiting_since": None,
    "waiting_deck_json": None,
    "queue_generation": 0,
    "online_players": {},
}
socket_event_hits = {}
private_waiting_rooms = {}
login_attempts = {}
retention_event_limiter = SlidingWindowRateLimiter()

CSRF_EXEMPT_ENDPOINTS = {"beta_event", "api_retention_event"}
CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
ALLOWED_RETENTION_EVENTS = {
    "page_view",
    "ui_click",
}


def create_database_tables():
    with app.app_context():
        db.create_all()
        try:
            ensure_reward_ledger_schema()
            ensure_premium_currency_schema()
            ensure_inventory_ownership_schema()
        except Exception as error:
            print("REWARD LEDGER INIT ERROR:", type(error).__name__, error)


create_database_tables()


def ensure_economy_schema():
    with app.app_context():
        try:
            inspector = sql_inspect(db.engine)
            user_columns = {col["name"] for col in inspector.get_columns("users")}

            with db.engine.begin() as connection:
                if "gems" not in user_columns:
                    connection.execute(sql_text("ALTER TABLE users ADD COLUMN gems INTEGER DEFAULT 0"))
                    print("ECONOMY SCHEMA: added users.gems")

            db.create_all()
        except Exception as error:
            print("ECONOMY SCHEMA ERROR:", type(error).__name__, error)

ensure_economy_schema()


def log_system_event(level="info", category="system", message="", details=None, user_id=None):
    try:
        payload = None

        if details is not None:
            payload = json.dumps(details, ensure_ascii=False)

        log = SystemLog(
            level=level,
            category=category,
            message=str(message)[:255],
            details_json=payload,
            user_id=user_id,
        )

        db.session.add(log)
        db.session.commit()
    except Exception as error:
        print("SYSTEM LOG ERROR:", error)


def log_rc_event(category, message, details=None, user_id=None, level="info"):
    try:
        log_system_event(
            level=level,
            category=category,
            message=message,
            details=details,
            user_id=user_id,
        )
    except Exception as error:
        print("RC EVENT LOG ERROR:", type(error).__name__, error)


def csrf_enabled():
    return bool(app.config.get("WTF_CSRF_ENABLED", True))


def generate_csrf_token():
    token = session.get("_csrf_token")

    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token

    return token


@app.context_processor
def inject_security_helpers():
    return {
        "csrf_token": generate_csrf_token,
    }


@app.before_request
def validate_csrf_token():
    if not csrf_enabled() or request.method in CSRF_SAFE_METHODS:
        return None

    if request.endpoint in CSRF_EXEMPT_ENDPOINTS or request.path.startswith("/socket.io/"):
        return None

    expected_token = session.get("_csrf_token")
    submitted_token = (
        request.form.get("_csrf_token")
        or request.headers.get("X-CSRFToken")
        or request.headers.get("X-CSRF-Token")
    )

    if expected_token and submitted_token and hmac.compare_digest(str(expected_token), str(submitted_token)):
        return None

    log_system_event(
        "warning",
        "security",
        "CSRF validation failed",
        details={"path": request.path, "endpoint": request.endpoint},
        user_id=session.get("user_id"),
    )
    abort(400, description="Invalid CSRF token.")


@app.after_request
def attach_security_headers(response):
    return apply_security_headers(response, app)


def generate_invite_code():
    return secrets.token_hex(4).upper()


def account_can_login(user):
    if not user:
        return False, "Invalid account."

    if getattr(user, "account_status", "active") in ["banned", "disabled"]:
        return False, "Account is not allowed to login."

    return True, ""


def normalize_email_verification_state(user):
    if not user:
        return

    if not bool(getattr(user, "is_verified", False)):
        user.is_verified = True

    if getattr(user, "account_status", "active") in ["unverified", "pending_verification"]:
        user.account_status = "active"

    if not getattr(user, "verified_at", None):
        user.verified_at = datetime.now(timezone.utc)


def password_errors(password):
    return password_policy_errors(
        password,
        min_length=int(app.config.get("PASSWORD_MIN_LENGTH", 10) or 10),
        require_complexity=bool(app.config.get("PASSWORD_REQUIRE_COMPLEXITY", True)),
    )


def login_attempt_fingerprint(email):
    raw = f"{request.remote_addr or 'unknown'}:{str(email or '').strip().lower()}"
    secret = str(app.config.get("SECRET_KEY", ""))
    return hmac.new(secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()


def recent_failed_login_count(fingerprint):
    cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=int(app.config.get("LOGIN_ATTEMPT_WINDOW_MINUTES", 15) or 15)
    )

    try:
        return (
            SystemLog.query
            .filter_by(category="auth", message=f"Invalid login attempt:{fingerprint}")
            .filter(SystemLog.created_at >= cutoff)
            .count()
        )
    except Exception as error:
        print("LOGIN RATE QUERY ERROR:", type(error).__name__, error)
        return login_attempts.get(fingerprint, 0)


def record_failed_login(fingerprint):
    try:
        log_system_event(
            "warning",
            "auth",
            f"Invalid login attempt:{fingerprint}",
            details={"fingerprint": fingerprint},
        )
    except Exception as error:
        print("LOGIN RATE LOG ERROR:", type(error).__name__, error)
        login_attempts[fingerprint] = login_attempts.get(fingerprint, 0) + 1


def reset_login_attempts(fingerprint):
    login_attempts.pop(fingerprint, None)


def hash_url_token(token):
    secret = str(app.config.get("SECRET_KEY", ""))
    return hmac.new(secret.encode("utf-8"), str(token).encode("utf-8"), hashlib.sha256).hexdigest()


def issue_password_reset_token(user):
    token = secrets.token_urlsafe(32)
    user.reset_token = hash_url_token(token)
    user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    return token


def reset_token_is_expired(expires_at):
    if not expires_at:
        return True

    now = datetime.now(timezone.utc)

    if getattr(expires_at, "tzinfo", None) is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    return expires_at < now


def mark_user_verified(user):
    user.is_verified = True
    user.account_status = "active"
    user.verified_at = datetime.now(timezone.utc)


def get_public_base_url():
    return app.config.get("PUBLIC_BASE_URL", request.url_root.rstrip("/"))


def log_sensitive_link_for_local_dev(label, url):
    if not app.config.get("EMAIL_LOG_BODY_ENABLED", False):
        print(f"{label} omitted. Set EMAIL_LOG_BODY_ENABLED=true only in local development if needed.")
        return

    print(f"\n--- {label} ---")
    print(url)
    print("-" * (len(label) + 8) + "\n")




def current_user():
    if "user_id" not in session:
        return None

    return db.session.get(User, session["user_id"])



def login_required_redirect():
    if "user_id" not in session:
        return redirect("/login")

    user = current_user()

    if not user:
        session.clear()
        return redirect("/login")

    return None




def dev_tools_enabled():
    config_value = app.config.get("DEV_TOOLS_ENABLED", False)
    env_value = os.environ.get("DEV_TOOLS_ENABLED", "")

    if isinstance(config_value, bool) and config_value:
        return True

    if str(config_value).strip().lower() in {"1", "true", "yes", "on"}:
        return True

    if str(env_value).strip().lower() in {"1", "true", "yes", "on"}:
        return True

    return False


def dev_tools_required_redirect():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    if not dev_tools_enabled():
        flash("Dev Tools are disabled in this environment.")
        return redirect("/admin")

    return None


def danger_confirmation_matches():
    expected = app.config.get("ADMIN_DANGER_CONFIRMATION", "RESET AMBITIONZ")
    received = request.form.get("confirmation", "").strip()

    return received == expected


def require_danger_confirmation_or_redirect():
    if danger_confirmation_matches():
        return None

    flash("Danger confirmation failed. Type the exact confirmation phrase.")
    return redirect("/admin/dev-tools")


def build_liveops_observability():
    recent_match_logs = []
    recent_errors = []

    try:
        recent_match_logs = (
            SystemLog.query
            .filter_by(category="match")
            .order_by(SystemLog.created_at.desc())
            .limit(500)
            .all()
        )
    except Exception as error:
        print("LIVEOPS MATCH LOG QUERY ERROR:", type(error).__name__, error)

    try:
        recent_errors = (
            SystemLog.query
            .filter(SystemLog.level.in_(["error", "critical"]))
            .order_by(SystemLog.created_at.desc())
            .limit(8)
            .all()
        )
    except Exception as error:
        print("LIVEOPS ERROR LOG QUERY ERROR:", type(error).__name__, error)

    def has_message(log, *needles):
        message = str(getattr(log, "message", "") or "").lower()
        return any(str(needle).lower() in message for needle in needles)

    return {
        "online_players": len(socket_state.get("online_players", {}) or {}),
        "queued_players": 1 if socket_state.get("waiting_player") else 0,
        "private_waiting_rooms": len(private_waiting_rooms),
        "active_matches": len(active_matches),
        "active_pvp_matches": sum(1 for match in active_matches.values() if not match.get("is_bot_match")),
        "active_bot_matches": sum(1 for match in active_matches.values() if match.get("is_bot_match")),
        "recent_match_starts": sum(
            1 for log in recent_match_logs
            if has_message(log, "match started", "duel started", "fallback bot match started")
        ),
        "recent_bot_fallbacks": sum(1 for log in recent_match_logs if has_message(log, "fallback bot match started")),
        "recent_disconnects": sum(1 for log in recent_match_logs if has_message(log, "disconnected")),
        "recent_errors_count": len(recent_errors),
        "recent_errors": recent_errors,
    }


def admin_audit(message, level="warning", category="admin"):
    try:
        user = current_user()
        log_system_event(
            level,
            category,
            message,
            user_id=getattr(user, "id", None),
        )
    except Exception as error:
        print("ADMIN AUDIT LOG FAILED:", type(error).__name__, error)



def _card_cost_value(card):
    try:
        return int(card.get("cost", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _is_playable_with_energy(card, energy):
    return _card_cost_value(card) <= energy


def _is_playable_monster_with_energy(card, energy):
    return card.get("type") == "Monster" and _is_playable_with_energy(card, energy)


def draw_beta_starting_hand(deck, size=5, starting_energy=2):
    """Draw a beta-friendly starting hand from a mutable deck list.

    This is a first-session safety net. It avoids a dead mobile opening where
    the player has no playable card or no playable monster.
    """
    hand = draw_starting_hand(deck, size)

    has_playable = any(_is_playable_with_energy(card, starting_energy) for card in hand)
    has_playable_monster = any(_is_playable_monster_with_energy(card, starting_energy) for card in hand)

    if has_playable and has_playable_monster:
        return hand

    def swap_in(predicate):
        for deck_index, candidate in enumerate(deck):
            if predicate(candidate):
                # Prefer replacing the highest-cost non-matching card.
                replace_index = None
                replacement_score = -1

                for hand_index, current in enumerate(hand):
                    if predicate(current):
                        continue

                    score = _card_cost_value(current)

                    if score > replacement_score:
                        replacement_score = score
                        replace_index = hand_index

                if replace_index is None and hand:
                    replace_index = len(hand) - 1

                if replace_index is not None:
                    removed = hand[replace_index]
                    hand[replace_index] = candidate
                    deck[deck_index] = removed
                return

    if not has_playable_monster:
        swap_in(lambda card: _is_playable_monster_with_energy(card, starting_energy))

    has_playable = any(_is_playable_with_energy(card, starting_energy) for card in hand)

    if not has_playable:
        swap_in(lambda card: _is_playable_with_energy(card, starting_energy))

    return hand


def get_existing_table_names():
    try:
        inspector = sql_inspect(db.engine)
        return set(inspector.get_table_names())
    except Exception as error:
        print("Table inspection failed:", type(error).__name__, error)
        return set()


GAMEPLAY_CLEANUP_TABLES = (
    "system_logs",
    "feedback_reports",
    "feedback_report",
    "booster_history",
    "booster_histories",
    "match_history",
    "match_histories",
    "card_stats",
    "beta_invites",
    "sessions",
    "password_reset_tokens",
    "mission_progress",
    "missions",
    "user_missions",
)

NON_ADMIN_USER_DEPENDENCY_TABLES = (
    "user_missions",
    "system_logs",
    "feedback_reports",
    "feedback_report",
    "booster_history",
    "booster_histories",
    "match_history",
    "match_histories",
    "card_stats",
    "beta_invites",
)

CLEANUP_ALLOWED_TABLES = frozenset(GAMEPLAY_CLEANUP_TABLES + NON_ADMIN_USER_DEPENDENCY_TABLES + ("users",))


def quote_cleanup_table_name(table_name):
    if table_name not in CLEANUP_ALLOWED_TABLES:
        raise ValueError(f"Table is not allowed for cleanup: {table_name}")

    return f'"{table_name}"'


def safe_delete_table_rows(connection, table_name, where_clause=None, params=None):
    """Delete rows from a table only if it exists. Works on SQLite and PostgreSQL."""
    try:
        existing_tables = get_existing_table_names()

        if table_name not in existing_tables:
            print(f"Cleanup skipped; table does not exist: {table_name}")
            return False

        quoted_table = quote_cleanup_table_name(table_name)

        if where_clause:
            query = f"DELETE FROM {quoted_table} WHERE {where_clause}"  # nosec B608
            connection.execute(sql_text(query), params or {})
        else:
            query = f"DELETE FROM {quoted_table}"  # nosec B608
            connection.execute(sql_text(query))

        print(f"Cleanup OK: {table_name}")
        return True

    except Exception as error:
        print(f"Cleanup ERROR on {table_name}: {type(error).__name__}: {error}")
        return False


def cleanup_gameplay_tables():
    """Clear operational/gameplay tables while preserving users."""
    cleared = []

    with db.engine.begin() as connection:
        for table in GAMEPLAY_CLEANUP_TABLES:
            if safe_delete_table_rows(connection, table):
                cleared.append(table)

    return cleared


def cleanup_non_admin_users():
    """Clear test data and delete only non-admin users, safely handling FK tables."""
    cleared = []

    confirmation_redirect = require_danger_confirmation_or_redirect()

    if confirmation_redirect:
        return confirmation_redirect

    admin_audit("Reset non-admin users requested")

    deleted_users = 0

    with db.engine.begin() as connection:
        existing_tables = get_existing_table_names()

        for table in NON_ADMIN_USER_DEPENDENCY_TABLES:
            if table in existing_tables:
                try:
                    quoted_table = quote_cleanup_table_name(table)
                    connection.execute(sql_text(f"DELETE FROM {quoted_table}"))  # nosec B608
                    cleared.append(table)
                    print(f"Cleanup OK: {table}")
                except Exception as error:
                    print(f"Cleanup ERROR on {table}: {type(error).__name__}: {error}")

        if "users" not in existing_tables:
            return {
                "cleared_tables": cleared,
                "deleted_users": 0,
            }

        try:
            result = connection.execute(
                sql_text('DELETE FROM "users" WHERE COALESCE(is_admin, false) = false')
            )
            deleted_users = result.rowcount or 0
            print(f"Deleted non-admin users: {deleted_users}")
        except Exception as error:
            print("\n--- DELETE NON ADMIN USERS ERROR ---")
            print("Error type:", type(error).__name__)
            print("Error:", error)
            print("\n------------------------------------\n")
            raise

    return {
        "cleared_tables": cleared,
        "deleted_users": deleted_users,
    }



def safe_admin_user_id():
    user = current_user()

    if not user:
        return None

    return getattr(user, "id", None)




# AMBITIONZ ADMIN STABILITY HELPERS
def get_session_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None


def admin_required_redirect():
    user = get_session_user()

    if not user:
        flash("Login required.")
        return redirect("/login")

    if not bool(getattr(user, "is_admin", False)):
        flash("Admin access required.")
        return redirect("/")

    if getattr(user, "account_status", "active") in ["banned", "disabled"]:
        flash("Account is not allowed to access admin.")
        return redirect("/login")

    return None


register_security_ops_routes(app, {
    "db": db,
    "User": User,
    "admin_required_redirect": admin_required_redirect,
    "current_user": current_user,
    "get_session_user": get_session_user,
    "hash_url_token": hash_url_token,
    "issue_password_reset_token": issue_password_reset_token,
    "log_system_event": log_system_event,
    "password_errors": password_errors,
    "reset_token_is_expired": reset_token_is_expired,
    "send_password_reset_email": send_password_reset_email,
})


@app.route("/admin/ping")
def admin_ping():
    auth_redirect = admin_required_redirect()
    if auth_redirect:
        return auth_redirect

    return {
        "ok": True,
        "admin": True,
        "message": "Admin session is valid.",
    }


@app.route("/debug/routes")
def debug_routes():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            "rule": str(rule),
            "endpoint": rule.endpoint,
            "methods": sorted([m for m in rule.methods if m not in ["HEAD", "OPTIONS"]]),
        })

    return {"ok": True, "routes": routes}


@app.route("/admin/dev-tools")
def admin_dev_tools():
    auth_redirect = dev_tools_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    users = User.query.order_by(User.id.asc()).all()

    return render_template("admin_dev_tools.html", user=user, users=users)


@app.route("/admin/test-email", methods=["POST"])
def admin_test_email():
    auth_redirect = dev_tools_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    email = request.form.get("email", "").strip().lower()

    if not email:
        flash("Email is required.")
        return redirect("/admin/dev-tools")

    try:
        sent = send_smtp_test_email(email)

        if sent:
            flash("SMTP test email sent.")
            try:
                log_system_event("info", "email", f"SMTP test sent to {email}", user_id=safe_admin_user_id())
            except Exception as log_error:
                print("LOG ERROR AFTER SMTP SUCCESS:", log_error)
        else:
            flash("SMTP test failed. Check Render logs.")
            try:
                log_system_event("error", "email", f"SMTP test failed to {email}", user_id=safe_admin_user_id())
            except Exception as log_error:
                print("LOG ERROR AFTER SMTP FAILURE:", log_error)

    except Exception as error:
        print("\n--- ADMIN SMTP TEST ROUTE ERROR ---")
        print("Error type:", type(error).__name__)
        print("Error:", error)
        print("Destination:", email)
        print("\n-----------------------------------\n")

        flash(f"SMTP test crashed: {type(error).__name__}. Check Render logs.")

    return redirect("/admin/dev-tools")


@app.route("/admin/reset-test-users", methods=["POST"])
def admin_reset_test_users():
    auth_redirect = dev_tools_required_redirect()

    if auth_redirect:
        return auth_redirect

    confirmation_redirect = require_danger_confirmation_or_redirect()

    if confirmation_redirect:
        return confirmation_redirect

    try:
        result = delete_non_admin_users(db)
        admin_audit(f"Reset non-admin users. Deleted users: {result['deleted_users']}")
        flash(f"Cleanup complete. Deleted non-admin users: {result['deleted_users']}.")

    except Exception as error:
        print("\n--- ADMIN RESET TEST USERS ERROR ---")
        print("Error type:", type(error).__name__)
        print("Error:", error)
        print("\n------------------------------------\n")
        flash(f"Cleanup failed: {type(error).__name__}. Check Render logs.")

    return redirect("/admin/dev-tools")


@app.route("/admin/clear-gameplay-data", methods=["POST"])
def admin_clear_gameplay_data():
    auth_redirect = dev_tools_required_redirect()

    if auth_redirect:
        return auth_redirect

    confirmation_redirect = require_danger_confirmation_or_redirect()

    if confirmation_redirect:
        return confirmation_redirect

    try:
        result = clear_gameplay_data(db)
        admin_audit(f"Gameplay data cleared. Tables: {result['cleared_tables']}")
        flash(f"Gameplay data cleared. Tables cleared: {result['cleared_count']}.")

    except Exception as error:
        print("\n--- ADMIN CLEAR GAMEPLAY DATA ERROR ---")
        print("Error type:", type(error).__name__)
        print("Error:", error)
        print("\n---------------------------------------\n")
        flash(f"Cleanup failed: {type(error).__name__}. Check Render logs.")

    return redirect("/admin/dev-tools")


@app.route("/admin/system")
def admin_system():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    if not user or not user.is_admin:
        flash("Admin access required.")
        return redirect("/")

    db_ok = True
    db_error = None

    try:
        User.query.first()
    except Exception as error:
        db_ok = False
        db_error = str(error)

    return render_template(
        "admin_system.html",
        user=user,
        smtp_enabled=is_smtp_configured(),
        db_ok=db_ok,
        db_error=db_error,
        app_version="Ambitionz V1.02",
        environment=app.config.get("ENVIRONMENT"),
        total_users=User.query.count(),
        verified_users=User.query.filter_by(account_status="active").count(),
        total_matches=MatchHistory.query.count(),
        open_feedbacks=FeedbackReport.query.filter_by(status="open").count(),
        liveops=build_liveops_observability(),
        recent_logs=SystemLog.query.order_by(SystemLog.created_at.desc()).limit(20).all(),
    )


@app.route("/admin/users")
def admin_users():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    if not user or not user.is_admin:
        flash("Admin access required.")
        return redirect("/")

    users = User.query.order_by(User.id.desc()).limit(200).all()

    return render_template("admin_users.html", user=user, users=users)


@app.route("/admin/users/<int:user_id>/toggle-admin", methods=["POST"])
def admin_toggle_admin(user_id):
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    current = current_user()

    if not current or not current.is_admin:
        flash("Admin access required.")
        return redirect("/")

    target = db.session.get(User, user_id)

    if target:
        if target.id == current.id and target.is_admin:
            flash("You cannot remove your own admin access.")
            return redirect("/admin/users")

        if target.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
            flash("At least one admin account must remain active.")
            return redirect("/admin/users")

        target.is_admin = not target.is_admin
        db.session.commit()
        log_system_event("warning", "admin", f"Admin toggled for {target.email}", user_id=current.id)

    return redirect("/admin/users")


@app.route("/admin/users/<int:user_id>/toggle-tester", methods=["POST"])
def admin_toggle_tester(user_id):
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    current = current_user()

    if not current or not current.is_admin:
        flash("Admin access required.")
        return redirect("/")

    target = db.session.get(User, user_id)

    if target:
        target.is_tester = not target.is_tester
        db.session.commit()
        log_system_event("info", "admin", f"Tester toggled for {target.email}", user_id=current.id)

    return redirect("/admin/users")


@app.route("/admin/users/<int:user_id>/verify", methods=["POST"])
def admin_verify_user(user_id):
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    current = current_user()

    if not current or not current.is_admin:
        flash("Admin access required.")
        return redirect("/")

    target = db.session.get(User, user_id)

    if target:
        normalize_email_verification_state(target)
        db.session.commit()
        log_system_event("info", "admin", f"User activated manually: {target.email}", user_id=current.id)

    return redirect("/admin/users")


@app.route("/admin/users/<int:user_id>/ban", methods=["POST"])
def admin_ban_user(user_id):
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    current = current_user()

    if not current or not current.is_admin:
        flash("Admin access required.")
        return redirect("/")

    target = db.session.get(User, user_id)

    if target:
        target.account_status = "banned"
        db.session.commit()
        log_system_event("warning", "admin", f"User banned: {target.email}", user_id=current.id)

    return redirect("/admin/users")


@app.route("/admin/users/<int:user_id>/unban", methods=["POST"])
def admin_unban_user(user_id):
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    current = current_user()

    if not current or not current.is_admin:
        flash("Admin access required.")
        return redirect("/")

    target = db.session.get(User, user_id)

    if target:
        normalize_email_verification_state(target)
        target.account_status = "active"
        db.session.commit()
        log_system_event("info", "admin", f"User unbanned: {target.email}", user_id=current.id)

    return redirect("/admin/users")


@app.route("/admin/invites", methods=["GET", "POST"])
def admin_invites():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    if not user or not user.is_admin:
        flash("Admin access required.")
        return redirect("/")

    if request.method == "POST":
        max_uses = int(request.form.get("max_uses", "1") or 1)
        code = request.form.get("code", "").strip().upper() or generate_invite_code()

        invite = BetaInvite(
            code=code,
            created_by_user_id=safe_admin_user_id(),
            max_uses=max_uses,
            used_count=0,
            is_active=True,
        )

        db.session.add(invite)
        db.session.commit()

        log_system_event("info", "admin", f"Beta invite created: {code}", user_id=safe_admin_user_id())
        flash("Invite created.")
        return redirect("/admin/invites")

    invites = BetaInvite.query.order_by(BetaInvite.created_at.desc()).limit(100).all()
    return render_template("admin_invites.html", user=user, invites=invites)



# AMBITIONZ V1.41C — ADMIN BETA EVENTS PANEL
@app.route("/admin/beta-events")
def admin_beta_events():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    events = []

    try:
        events = (
            SystemLog.query
            .filter_by(category="beta_event")
            .order_by(SystemLog.created_at.desc())
            .limit(300)
            .all()
        )
    except Exception as error:
        print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)

    summary = {
        "total_loaded": len(events),
        "unique_users": len({event.user_id for event in events if getattr(event, "user_id", None)}),
        "page_views": len([event for event in events if "page_view" in str(getattr(event, "message", ""))]),
        "clicks": len([event for event in events if "action_link_click" in str(getattr(event, "message", ""))]),
        "forms": len([event for event in events if "form_submit" in str(getattr(event, "message", ""))]),
    }

    return render_template(
        "admin_beta_events.html",
        user=user,
        events=events,
        summary=summary,
    )


@app.route("/admin/feedback")
def admin_feedback():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    if not user or not user.is_admin:
        flash("Admin access required.")
        return redirect("/")

    reports = FeedbackReport.query.order_by(FeedbackReport.created_at.desc()).limit(200).all()
    return render_template("admin_feedback.html", user=user, reports=reports)


@app.route("/admin/feedback/<int:report_id>/update", methods=["POST"])
def admin_feedback_update(report_id):
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    if not user or not user.is_admin:
        flash("Admin access required.")
        return redirect("/")

    report = db.session.get(FeedbackReport, report_id)

    if report:
        report.status = request.form.get("status", report.status)
        db.session.commit()
        log_system_event("info", "feedback", f"Feedback status updated: {report.title}", user_id=safe_admin_user_id())

    return redirect("/admin/feedback")


def check_route_status(path):
    try:
        with app.test_client() as client:
            response = client.get(path, follow_redirects=False)
            return response.status_code
    except Exception:
        return 500


def build_internal_rc_status():
    checks = []

    def add_check(key, label, ok, detail, priority="required"):
        checks.append({
            "key": key,
            "label": label,
            "ok": bool(ok),
            "detail": detail,
            "priority": priority,
        })

    db_ok = True
    db_detail = "Database query OK"

    try:
        db.session.execute(sql_text("SELECT 1"))
    except Exception as error:
        db_ok = False
        db_detail = f"{type(error).__name__}: {error}"

    add_check("database", "Database responds", db_ok, db_detail)
    add_check(
        "smtp",
        "Email delivery configured or optional",
        True,
        (
            "SMTP is configured"
            if is_smtp_configured()
            else "Email verification disabled; SMTP is optional for password reset only"
        ),
        priority="recommended",
    )

    route_results = []
    route_ok = True

    for path in ["/", "/health", "/login", "/register", "/training", "/arena", "/feedback", "/missions", "/shop"]:
        status = check_route_status(path)
        route_results.append(f"{path}={status}")
        if status >= 500:
            route_ok = False

    add_check(
        "critical_routes",
        "Critical routes do not 500",
        route_ok,
        ", ".join(route_results),
    )

    open_critical_feedbacks = 0
    open_feedbacks = 0
    recent_errors = 0
    total_users = 0
    verified_users = 0
    total_matches = 0
    average_rounds = 0
    recent_match_sample_size = 0

    try:
        open_feedbacks = FeedbackReport.query.filter_by(status="open").count()
        open_critical_feedbacks = FeedbackReport.query.filter_by(status="open", severity="critical").count()
    except Exception as error:
        add_check("feedback_query", "Feedback can be queried", False, f"{type(error).__name__}: {error}")

    add_check(
        "critical_feedback",
        "No open critical feedback",
        open_critical_feedbacks == 0,
        f"{open_critical_feedbacks} open critical reports",
    )

    try:
        recent_errors = (
            SystemLog.query
            .filter(SystemLog.level.in_(["error", "critical"]))
            .filter(SystemLog.category != "email")
            .filter_by(is_resolved=False)
            .count()
        )
    except Exception as error:
        add_check("system_log_query", "System logs can be queried", False, f"{type(error).__name__}: {error}")

    add_check(
        "runtime_errors",
        "No unresolved runtime errors",
        recent_errors == 0,
        f"{recent_errors} unresolved error logs",
        priority="recommended",
    )

    try:
        total_users = User.query.count()
        verified_users = User.query.filter_by(account_status="active").count()
        total_matches = MatchHistory.query.count()
        recent_matches = MatchHistory.query.order_by(MatchHistory.id.desc()).limit(20).all()
        recent_match_sample_size = len(recent_matches)

        if recent_matches:
            average_rounds = round(
                sum(int(match.total_rounds or 0) for match in recent_matches) / len(recent_matches),
                1,
            )
    except Exception as error:
        add_check("core_metrics", "Core metrics can be queried", False, f"{type(error).__name__}: {error}")

    add_check(
        "tester_accounts",
        "Tester accounts exist",
        total_users > 0,
        f"{total_users} total users, {verified_users} active",
        priority="recommended",
    )
    add_check(
        "match_history",
        "Match history records exist",
        total_matches > 0,
        f"{total_matches} saved matches",
        priority="recommended",
    )
    add_check(
        "balance_sample",
        "Recent match length is readable",
        total_matches == 0 or recent_match_sample_size < 20 or 2 <= average_rounds <= 12,
        (
            "No match sample yet"
            if total_matches == 0
            else f"{average_rounds} average rounds over {recent_match_sample_size}/20 recent matches"
        ),
        priority="recommended",
    )

    required_ok = all(check["ok"] for check in checks if check["priority"] == "required")
    recommended_ok = all(check["ok"] for check in checks)

    return {
        "checks": checks,
        "required_ok": required_ok,
        "recommended_ok": recommended_ok,
        "status_label": "READY" if required_ok else "BLOCKED",
        "open_feedbacks": open_feedbacks,
        "open_critical_feedbacks": open_critical_feedbacks,
        "recent_errors": recent_errors,
        "active_matches": len(active_matches),
        "waiting_queue": 1 if socket_state.get("waiting_player") else 0,
        "private_waiting_rooms": len(private_waiting_rooms),
        "total_users": total_users,
        "verified_users": verified_users,
        "total_matches": total_matches,
        "average_rounds": average_rounds,
    }


@app.route("/admin/release-candidate")
def admin_release_candidate():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    rc_status = build_internal_rc_status()
    recent_feedbacks = []
    recent_logs = []

    try:
        recent_feedbacks = FeedbackReport.query.order_by(FeedbackReport.created_at.desc()).limit(8).all()
    except Exception as error:
        print("RC FEEDBACK QUERY ERROR:", type(error).__name__, error)

    try:
        recent_logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(12).all()
    except Exception as error:
        print("RC LOG QUERY ERROR:", type(error).__name__, error)

    return render_template(
        "admin_release_candidate.html",
        user=current_user(),
        rc_status=rc_status,
        recent_feedbacks=recent_feedbacks,
        recent_logs=recent_logs,
    )



@app.route("/")
def index():
    user = current_user()
    return render_template("index.html", user=user)



@app.route("/health")
def health():
    db_status = "ok"

    try:
        db.session.execute(sql_text("SELECT 1"))
    except Exception as error:
        db_status = f"error:{type(error).__name__}"

    return {
        "status": "ok",
        "app": "Ambitionz",
        "version": "Ambitionz Internal RC",
        "environment": app.config["ENVIRONMENT"],
        "database": db_status,
        "smtp_configured": is_smtp_configured(),
        "active_matches": len(active_matches),
    }



@app.route("/manifest.webmanifest")
def pwa_manifest():
    response = make_response(app.send_static_file("manifest.webmanifest"))
    response.headers["Content-Type"] = "application/manifest+json"
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response
@app.route("/service-worker.js")
def service_worker():
    response = make_response(app.send_static_file("js/service-worker.js"))
    response.headers["Content-Type"] = "text/javascript; charset=utf-8"
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.errorhandler(500)
def internal_server_error(error):
    try:
        user = current_user()
        log_rc_event(
            "runtime_error",
            "Unhandled server error",
            details={
                "path": request.path,
                "method": request.method,
                "error": str(error)[:500],
            },
            user_id=getattr(user, "id", None) if user else None,
            level="error",
        )
    except Exception as log_error:
        print("500 LOG ERROR:", type(log_error).__name__, log_error)

    if request.path.startswith("/api/"):
        return {"status": "error", "message": "Internal server error"}, 500

    return "Internal server error", 500



@app.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            normalize_email_verification_state(user)
            db.session.commit()

        try:
            log_system_event(
                level="info",
                category="account",
                message="Verification bypass requested",
                user_id=getattr(user, "id", None),
            )
        except Exception as error:
            print("Verification bypass log failed:", error)

        flash("Email verification is disabled. You can login now.")
        return redirect("/login")

    flash("Email verification is disabled. You can login now.")
    return redirect("/login")





# =========================================================
# AMBITIONZ V1.18 — COSMETIC INVENTORY FOUNDATION
# =========================================================

COSMETIC_CATALOG_V118 = {
    "titles": [
        {
            "id": "beta_climber",
            "name": "Beta Climber",
            "rarity": "Common",
            "unlock": "Default beta title.",
        },
        {
            "id": "arena_spark",
            "name": "Arena Spark",
            "rarity": "Common",
            "unlock": "Play early beta matches.",
        },
        {
            "id": "overreach_tactician",
            "name": "Overreach Tactician",
            "rarity": "Uncommon",
            "unlock": "Future reward for Overreach mastery.",
        },
    ],
    "avatar_frames": [
        {
            "id": "plain_beta_frame",
            "name": "Plain Beta Frame",
            "rarity": "Common",
            "unlock": "Default profile frame.",
        },
        {
            "id": "violet_founder_frame",
            "name": "Violet Founder Frame",
            "rarity": "Uncommon",
            "unlock": "Future founder cosmetic.",
        },
    ],
    "card_backs": [
        {
            "id": "default_ambition_back",
            "name": "Default Ambition Back",
            "rarity": "Common",
            "unlock": "Default card back.",
        },
        {
            "id": "sigil_mark_back",
            "name": "Sigil Mark Back",
            "rarity": "Uncommon",
            "unlock": "Future Sigil progression reward.",
        },
    ],
    "arena_skins": [
        {
            "id": "beta_arena",
            "name": "Beta Arena",
            "rarity": "Common",
            "unlock": "Default arena skin.",
        },
        {
            "id": "void_table",
            "name": "Void Table",
            "rarity": "Uncommon",
            "unlock": "Future season reward.",
        },
    ],
}


def get_cosmetic_foundation_for_user(user, profile_stats=None):
    if not user:
        return {
            "equipped": {},
            "inventory": {},
            "slots": [],
        }

    beta_tier = "Unranked"

    if profile_stats:
        beta_tier = profile_stats.get("beta_tier", "Unranked")

    equipped = {
        "title": beta_tier if beta_tier != "Unranked" else "Beta Climber",
        "avatar_frame": "Plain Beta Frame",
        "card_back": "Default Ambition Back",
        "arena_skin": "Beta Arena",
    }

    inventory = {
        "titles": COSMETIC_CATALOG_V118["titles"],
        "avatar_frames": COSMETIC_CATALOG_V118["avatar_frames"],
        "card_backs": COSMETIC_CATALOG_V118["card_backs"],
        "arena_skins": COSMETIC_CATALOG_V118["arena_skins"],
    }

    slots = [
        {
            "label": "Title",
            "value": equipped["title"],
            "description": "Shown on your profile and future ranking cards.",
        },
        {
            "label": "Avatar Frame",
            "value": equipped["avatar_frame"],
            "description": "Visual border around your player identity.",
        },
        {
            "label": "Card Back",
            "value": equipped["card_back"],
            "description": "Future cosmetic for cards in hand and deck.",
        },
        {
            "label": "Arena Skin",
            "value": equipped["arena_skin"],
            "description": "Future visual theme for the match table.",
        },
    ]

    return {
        "equipped": equipped,
        "inventory": inventory,
        "slots": slots,
    }


@app.route("/profile")
def profile():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    total_matches = int(user.wins or 0) + int(user.losses or 0)
    winrate = 0

    if total_matches > 0:
        winrate = round((int(user.wins or 0) / total_matches) * 100, 1)

    if int(user.wins or 0) >= 10 and winrate >= 65:
        beta_tier = "Champion"
    elif int(user.wins or 0) >= 5 and winrate >= 55:
        beta_tier = "Contender"
    elif total_matches >= 3:
        beta_tier = "Climber"
    else:
        beta_tier = "Unranked"

    recent_matches = []
    user_matches = []
    history_draws = 0
    mode_counts = {}
    latest_result = "No matches yet"

    try:
        user_matches = (
            MatchHistory.query
            .filter(
                (MatchHistory.player1_id == user.id) |
                (MatchHistory.player2_id == user.id)
            )
            .order_by(MatchHistory.id.desc())
            .all()
        )

        recent_matches = user_matches[:5]

        for match in user_matches:
            opponent_name = match.player2_name if match.player1_id == user.id else match.player1_name
            mode_label = "Training" if "bot" in str(opponent_name or "").lower() else "PvP"
            mode_counts[mode_label] = mode_counts.get(mode_label, 0) + 1

            if match.result == "DRAW" or not match.winner_id:
                history_draws += 1

        if user_matches:
            latest = user_matches[0]
            if latest.result == "DRAW" or not latest.winner_id:
                latest_result = "Draw"
            elif latest.winner_id == user.id:
                latest_result = "Win"
            else:
                latest_result = "Loss"
    except Exception as error:
        print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
        recent_matches = []
        user_matches = []

    played_matches = max(total_matches, len(user_matches))
    mode_most_played = "Not played yet" if not mode_counts else max(
        mode_counts.items(),
        key=lambda item: (item[1], item[0]),
    )[0]

    profile_stats = {
        "total_matches": played_matches,
        "wins": int(user.wins or 0),
        "losses": int(user.losses or 0),
        "draws": history_draws,
        "winrate": winrate,
        "beta_tier": beta_tier,
        "level": int(user.level or 1),
        "xp": int(user.xp or 0),
        "next_level_xp": user.next_level_xp,
        "level_progress_percent": user.level_progress_percent,
        "coins": int(user.coins or 0),
        "mode_most_played": mode_most_played,
        "latest_result": latest_result,
        "xp_to_next": max(0, int(user.next_level_xp or 0) - int(user.xp or 0)),
    }

    identity = {
        "title": beta_tier,
        "avatar_letter": (user.username or "A")[0].upper(),
        "status": getattr(user, "account_status", "beta"),
        "is_tester": bool(getattr(user, "is_tester", False)),
        "is_verified": bool(getattr(user, "is_verified", False)),
    }

    cosmetics = get_cosmetic_foundation_for_user(user, profile_stats)

    return render_template(
        "profile.html",
        user=user,
        profile_stats=profile_stats,
        identity=identity,
        cosmetics=cosmetics,
        recent_matches=recent_matches,
    )



@app.route("/leaderboard")
def leaderboard():
    users = (
        User.query
        .order_by(User.level.desc(), User.xp.desc(), User.coins.desc(), User.id.asc())
        .limit(100)
        .all()
    )

    ranked_users = []
    current = current_user()
    current_rank = None

    for index, player in enumerate(users, start=1):
        row = {
            "rank": index,
            "user": player,
            "score": int(player.level or 1) * 10000 + int(player.xp or 0) * 10 + int(player.coins or 0),
            "is_current_user": bool(current and player.id == current.id),
        }

        if row["is_current_user"]:
            current_rank = index

        ranked_users.append(row)

    local_rows = ranked_users

    if current and current_rank:
        start = max(0, current_rank - 4)
        end = min(len(ranked_users), current_rank + 3)
        local_rows = ranked_users[start:end]

    return render_template(
        "leaderboard.html",
        user=current,
        ranked_users=ranked_users,
        local_rows=local_rows,
        current_rank=current_rank,
    )


@app.route("/ranking")
def ranking():
    users = (
        User.query
        .order_by(User.wins.desc(), User.level.desc(), User.xp.desc())
        .limit(50)
        .all()
    )

    total_players = User.query.count()
    total_matches = 0

    try:
        total_matches = MatchHistory.query.count()
    except Exception as error:
        print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
        total_matches = 0

    ranked_users = []

    for index, player in enumerate(users, start=1):
        total = int(player.wins or 0) + int(player.losses or 0)
        winrate = 0

        if total > 0:
            winrate = round((int(player.wins or 0) / total) * 100, 1)

        if int(player.wins or 0) >= 10 and winrate >= 65:
            tier = "Champion"
        elif int(player.wins or 0) >= 5 and winrate >= 55:
            tier = "Contender"
        elif total >= 3:
            tier = "Climber"
        else:
            tier = "Unranked"

        ranked_users.append({
            "rank": index,
            "username": player.username,
            "wins": int(player.wins or 0),
            "losses": int(player.losses or 0),
            "level": int(player.level or 1),
            "xp": int(player.xp or 0),
            "total_matches": total,
            "winrate": winrate,
            "tier": tier,
        })

    season = {
        "name": "Beta Season",
        "status": "Foundation",
        "total_players": total_players,
        "total_matches": total_matches,
        "ranked_count": len(ranked_users),
    }

    return render_template(
        "ranking.html",
        users=users,
        ranked_users=ranked_users,
        season=season,
    )




@app.route("/how-to-play")
def how_to_play():
    return render_template("how_to_play.html")



@app.route("/first-session")
def first_session():
    user = current_user()

    steps = [
        {
            "title": "Create your account",
            "text": "Start with registration or login so your XP, coins, missions and deck progress can be saved.",
            "cta": "Create Account",
            "endpoint": "register",
        },
        {
            "title": "Play training",
            "text": "Run one training match to test battle loading, card flow, intent selection and match completion.",
            "cta": "Play Training",
            "endpoint": "training",
        },
        {
            "title": "Check rewards",
            "text": "After the match, confirm XP, coins, missions and profile progress updated correctly.",
            "cta": "Open Profile",
            "endpoint": "profile",
        },
        {
            "title": "Open a booster",
            "text": "Use the shop to test collection growth and card reward feeling.",
            "cta": "Open Shop",
            "endpoint": "shop",
        },
        {
            "title": "Improve your deck",
            "text": "Open deck builder and confirm the fixed 30-card beta deck flow is readable on Android.",
            "cta": "Deck Builder",
            "endpoint": "deck_builder",
        },
        {
            "title": "Send feedback",
            "text": "Report bugs, layout issues, confusing moments, balance concerns or Android-specific problems.",
            "cta": "Send Feedback",
            "endpoint": "feedback",
        },
    ]

    return render_template("first_session.html", user=user, steps=steps)


@app.route("/closed-test")
def closed_test():
    user = current_user()

    tester_steps = [
        "Create or access your account",
        "Play one training match",
        "Check rewards, missions and profile",
        "Open booster shop and deck builder",
        "Send feedback if anything breaks or feels confusing",
    ]

    tester_checklist = [
        "App opens without browser address bar",
        "Login and register work",
        "Training match starts and ends",
        "Post-match rewards appear",
        "Missions and profile update",
        "Booster shop opens",
        "Deck builder opens",
        "Feedback form submits",
        "Android back button behaves correctly",
        "Portrait layout remains readable",
    ]

    return render_template(
        "closed_test.html",
        user=user,
        tester_steps=tester_steps,
        tester_checklist=tester_checklist,
    )



@app.route("/terms")
def terms():
    return render_template("terms.html")




@app.route("/data-deletion")
def data_deletion():
    return render_template("data_deletion.html")




@app.route("/support")
def support():
    return render_template("support.html", user=current_user())


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/offline")
def offline():
    return render_template("offline.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        invite_code = request.form.get("invite_code", "").strip().upper()

        if not username or not email or not password:
            flash("Fill all fields.")
            return redirect("/register")

        errors = password_errors(password)

        if errors:
            for error in errors:
                flash(error)
            return redirect("/register")

        invite = None

        if app.config.get("BETA_INVITE_REQUIRED"):
            if not invite_code:
                flash("Beta invite code is required.")
                return redirect("/register")

            invite = BetaInvite.query.filter_by(code=invite_code).first()

            if not invite or not invite.can_be_used():
                flash("Invalid or expired invite code.")
                return redirect("/register")

        if User.query.filter_by(email=email).first():
            flash("Email already exists.")
            return redirect("/register")

        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect("/register")

        new_user = User(
            username=username,
            email=email,
            account_status="active",
            is_tester=True if invite else False,
            is_verified=True,
            verified_at=datetime.now(timezone.utc),
        )
        new_user.set_password(password)

        db.session.add(new_user)

        if invite:
            invite.used_count += 1

        db.session.commit()

        flash("Registered successfully. You can login and play now.")

        log_rc_event(
            "account",
            "User registered with instant beta access",
            user_id=new_user.id,
        )

        return redirect("/login")

    return render_template("register.html")



@app.route("/confirm_email/<token>")
def confirm_email(token):
    try:
        email = serializer.loads(token, salt="email-confirm", max_age=3600)
    except Exception:
        return "Verification link expired."

    user = User.query.filter_by(email=email).first_or_404()
    normalize_email_verification_state(user)

    db.session.commit()
    log_rc_event("account", "Legacy verification link accepted", user_id=user.id)

    flash("Email verification is disabled. You can login now.")
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        invite_code = request.form.get("invite_code", "").strip().upper()

        attempt_key = login_attempt_fingerprint(email)
        attempts = recent_failed_login_count(attempt_key)

        if attempts >= app.config.get("LOGIN_ATTEMPT_LIMIT", 8):
            flash("Too many login attempts. Try again later.")
            return redirect("/login")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            record_failed_login(attempt_key)
            flash("Invalid login.")
            return redirect("/login")

        can_login, login_message = account_can_login(user)

        if not can_login:
            log_rc_event(
                "auth",
                "Blocked login attempt",
                details={"email": email, "reason": login_message},
                user_id=getattr(user, "id", None),
                level="warning",
            )
            flash(login_message)
            return redirect("/login")

        reset_login_attempts(attempt_key)
        normalize_email_verification_state(user)

        user.last_login_at = datetime.now(timezone.utc)
        user.login_count = int(user.login_count or 0) + 1
        db.session.commit()

        session["user_id"] = user.id
        log_rc_event("auth", "User logged in", user_id=user.id)

        try:
            if not getattr(user, "has_completed_onboarding", False):
                return redirect("/welcome")
        except Exception as error:
            print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)

        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    user_id = session.get("user_id")
    session.clear()
    if user_id:
        log_rc_event("auth", "User logged out", user_id=user_id)
    return redirect("/")


@app.route("/collection")
def collection():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    # COLLECTION_REAL_OWNERSHIP_V1
    try:
        ensure_user_has_playable_inventory(user)
        db.session.commit()
    except Exception as error:
        print("COLLECTION INVENTORY RECOVERY ERROR:", type(error).__name__, error)
        db.session.rollback()

    cards = build_collection_from_inventory(user, include_zero=True)
    inventory_counts = user_inventory_counts(user)
    owned_cards = [card for card in cards if int(card.get("count") or 0) > 0]
    catalog_total = len(cards)
    unique_owned = len(owned_cards)
    element_order = ["Fire", "Water", "Earth", "Plant", "Global", "Neutral"]
    rarity_order = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]
    owned_element_counts = Counter(str(card.get("element") or "Neutral") for card in owned_cards)
    catalog_element_counts = Counter(str(card.get("element") or "Neutral") for card in cards)
    owned_rarity_counts = Counter(str(card.get("rarity") or "Common") for card in owned_cards)
    catalog_rarity_counts = Counter(str(card.get("rarity") or "Common") for card in cards)
    element_names = [name for name in element_order if catalog_element_counts.get(name, 0)]
    element_names.extend(sorted(name for name in catalog_element_counts if name not in element_names))
    rarity_names = [name for name in rarity_order if catalog_rarity_counts.get(name, 0)]
    rarity_names.extend(sorted(name for name in catalog_rarity_counts if name not in rarity_names))
    collection_stats = {
        "unique_cards": unique_owned,
        "total_cards": sum(int(card.get("count") or 0) for card in owned_cards),
        "catalog_cards": catalog_total,
        "completion_percent": int(round((unique_owned / catalog_total) * 100)) if catalog_total else 0,
        "catalog_label": "Starter Collection" if unique_owned else "Beta Catalog",
        "monsters": sum(int(card.get("count") or 0) for card in owned_cards if card.get("type") == "Monster"),
        "spells": sum(int(card.get("count") or 0) for card in owned_cards if card.get("type") == "Spell"),
        "traps": sum(int(card.get("count") or 0) for card in owned_cards if card.get("type") == "Trap"),
        "element_counts": [
            {
                "name": name,
                "owned": int(owned_element_counts.get(name, 0)),
                "total": int(catalog_element_counts.get(name, 0)),
                "css": "element-" + name.lower(),
            }
            for name in element_names
        ],
        "rarity_counts": [
            {
                "name": name,
                "owned": int(owned_rarity_counts.get(name, 0)),
                "total": int(catalog_rarity_counts.get(name, 0)),
                "css": "rarity-" + name.lower(),
            }
            for name in rarity_names
        ],
    }

    return render_template(
        "collection.html",
        user=user,
        cards=cards,
        inventory_counts=inventory_counts,
        collection_stats=collection_stats,
    )


@app.route("/economy")
def economy():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    entries = (
        EconomyLedger.query
        .filter_by(user_id=user.id)
        .order_by(EconomyLedger.id.desc())
        .limit(80)
        .all()
    )

    cosmetics = cosmetic_catalog_for_user(user)

    return render_template(
        "economy.html",
        user=user,
        entries=entries,
        cosmetics=cosmetics,
    )


@app.route("/economy/grant-founder", methods=["POST"])
def economy_grant_founder():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    ok, message = grant_cosmetic(user, "founder_title", source="beta_founder")

    flash(message)

    return redirect(url_for("economy"))


@app.route("/economy/test-gems", methods=["POST"])
def economy_test_gems():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    if not bool(getattr(user, "is_admin", False)):
        abort(403)

    ok, message = add_currency(
        user=user,
        currency=PREMIUM_CURRENCY_KEY,
        amount=100,
        source="admin_test",
        reason="Admin test gems for economy validation.",
    )

    flash(message)

    return redirect(url_for("economy"))




# =========================================================
# Booster Shop Helpers
# Stable fallback for shop route.
# =========================================================

BOOSTER_PACKS = {
    "elemental": {
        "key": "elemental",
        "name": "Elemental Booster",
        "cost": 300,
        "size": 5,
        "description": "Common and Uncommon beta cards for collection growth.",
        "rarities": {
            "Common": 78,
            "Uncommon": 22,
        },
    },
}


def get_booster_pack(pack_key=None):
    key = str(pack_key or "elemental").strip().lower()

    if key not in BOOSTER_PACKS:
        key = "elemental"

    return dict(BOOSTER_PACKS[key])


def booster_pull_from_pack(pack):
    import random

    from game.cards import CARD_CATALOG

    cards = list(CARD_CATALOG)

    if not cards:
        raise ValueError("Card catalog is empty.")

    rarity_roll = random.randint(1, 100)
    target_rarity = "Common"

    rarities = (pack or {}).get("rarities") or {}

    if rarity_roll > int(rarities.get("Common", 78)):
        target_rarity = "Uncommon"

    pool = [
        card for card in cards
        if str(card.get("rarity", "")).lower() == target_rarity.lower()
    ]

    if not pool:
        pool = cards

    card = dict(random.choice(pool))

    element = str(card.get("element") or "Neutral")
    rarity = str(card.get("rarity") or "Common")

    card.setdefault("description", card.get("effect") or "Beta card.")
    card.setdefault("effect", card.get("description") or "Beta card.")
    card.setdefault("cost", 1)
    card.setdefault("power", card.get("attack") or card.get("value") or 0)
    card.setdefault("value", card.get("power") or 0)
    card.setdefault("sigil", "Neutral")

    card["element_css"] = "element-" + element.lower()
    card["rarity_css"] = "rarity-" + rarity.lower()

    return card


@app.route("/shop", methods=["GET", "POST"])
def shop():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    selected_pack_key = request.form.get("pack_key") or request.args.get("pack") or "elemental"
    selected_pack = get_booster_pack(selected_pack_key)

    booster_cost = int(selected_pack.get("cost", 300))
    booster_size = int(selected_pack.get("size", 5))
    pulled_cards = []
    can_afford_booster = int(user.coins or 0) >= booster_cost

    if request.method == "POST":
        if not can_afford_booster:
            flash("Not enough coins to open this booster.")
            return redirect(f"/shop?pack={selected_pack['key']}")

        user.coins -= booster_cost

        collection_ids = owned_card_ids_for_user(user)

        for _ in range(booster_size):
            card = booster_pull_from_pack(selected_pack)
            pulled_cards.append(card)
            collection_ids.append(card["id"])

        user.collection_json = json.dumps(collection_ids)

        common_count = len([card for card in pulled_cards if card.get("rarity") == "Common"])
        uncommon_count = len([card for card in pulled_cards if card.get("rarity") == "Uncommon"])

        history_payload = []
        for card in pulled_cards:
            history_payload.append({
                **card,
                "pack_key": selected_pack["key"],
                "pack_name": selected_pack["name"],
            })

        history = BoosterHistory(
            user_id=user.id,
            username=user.username,
            cost=booster_cost,
            cards_json=json.dumps(history_payload),
            common_count=common_count,
            uncommon_count=uncommon_count,
        )

        db.session.add(history)

        # BOOSTER_TO_INVENTORY_V1
        for index, card in enumerate(pulled_cards):
            grant_card(
                user=user,
                card_id=card["id"],
                quantity=1,
                source="booster",
                idempotency_key=f"booster-{user.id}-{selected_pack['key']}-{datetime.utcnow().timestamp()}-{index}-{card['id']}",
                metadata={
                    "pack_key": selected_pack["key"],
                    "pack_name": selected_pack["name"],
                    "card_name": card.get("name"),
                    "rarity": card.get("rarity"),
                    "element": card.get("element"),
                },
            )

        increment_mission(user, "open_1_booster", 1)
        log_rc_event(
            "progression",
            "Booster opened",
            details={"pack": selected_pack["key"], "size": booster_size, "cost": booster_cost},
            user_id=user.id,
        )
        db.session.commit()

        flash(f"{selected_pack['name']} opened: {booster_size} cards added to your collection.")

    return render_template(
        "shop.html",
        user=user,
        pulled_cards=pulled_cards,
        booster_cost=booster_cost,
        booster_size=booster_size,
        can_afford_booster=can_afford_booster,
        booster_packs=list(BOOSTER_PACKS.values()),
        selected_pack=selected_pack,
    )






@app.route("/auto-build-deck", methods=["POST"])
def auto_build_deck():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    collection_ids = owned_card_ids_for_user(user)

    user.deck_json = build_auto_deck_from_inventory(user)
    db.session.commit()

    flash("Auto deck created with beta structure: 21 monsters, 6 spells, 3 traps.")
    return redirect("/deck-builder")




@app.route("/booster-history")
def booster_history():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    histories = (
        BoosterHistory.query
        .filter_by(user_id=user.id)
        .order_by(BoosterHistory.created_at.desc())
        .limit(30)
        .all()
    )

    return render_template(
        "booster_history.html",
        user=user,
        histories=histories,
        json=json,
    )


@app.route("/deck-builder", methods=["GET", "POST"])
def deck_builder():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    try:
        ensure_user_has_playable_inventory(user)
        db.session.commit()
    except Exception as error:
        print("DECK BUILDER INVENTORY RECOVERY ERROR:", type(error).__name__, error)
        db.session.rollback()

    collection_ids = owned_card_ids_for_user(user)
    deck_ids = load_card_ids(user.deck_json)

    if request.method == "POST":
        selected_cards = request.form.getlist("deck_cards")
        errors = validate_deck(selected_cards, collection_ids)

        if errors:
            for error in errors:
                flash(error)
        else:
            user.deck_json = json.dumps(selected_cards)
            log_rc_event(
                "deck",
                "Deck saved",
                details={"cards": len(selected_cards)},
                user_id=user.id,
            )
            db.session.commit()
            flash("Deck saved successfully.")

        return redirect("/deck-builder")

    collection_cards = sorted(collection_summary(collection_ids), key=card_sort_key)
    current_deck = sorted(deck_summary(deck_ids), key=card_sort_key)

    collection_cards = enrich_cards_for_view(collection_cards)
    current_deck = enrich_cards_for_view(current_deck)

    deck_validation_errors = validate_deck(deck_ids, collection_ids)
    deck_analysis = full_deck_analysis(deck_ids)
    deck_counter = Counter(deck_ids)
    deck_status = {
        "is_valid": len(deck_validation_errors) == 0,
        "error_count": len(deck_validation_errors),
        "total": len(deck_ids),
        "duplicates": len([card_id for card_id, amount in deck_counter.items() if amount > 1]),
        "max_copies_used": max(deck_counter.values()) if deck_counter else 0,
        "max_copies_allowed": 3,
        "rules_label": "30 cards · 21 monsters · 6 spells · 3 traps · max 3 copies",
    }

    return render_template(
        "deck_builder.html",
        user=user,
        collection_cards=collection_cards,
        current_deck=current_deck,
        deck_ids=deck_ids,
        deck_validation_errors=deck_validation_errors,
        deck_analysis=deck_analysis_v115(deck_ids),
        deck_status=deck_status,
    )


@app.route("/arena")
def arena():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    collection_ids = owned_card_ids_for_user(user)
    deck_ids = load_card_ids(user.deck_json)
    errors = validate_deck(deck_ids, collection_ids)

    if errors:
        flash("Your deck is invalid. Fix it before entering the arena.")
        return redirect("/deck-builder")

    match_mode = request.args.get("mode", "random")
    private_code = normalize_room_code(request.args.get("code", ""))

    if match_mode not in ["random", "private", "bot"]:
        match_mode = "random"

    if match_mode == "private" and not is_valid_room_code(private_code):
        flash("Invalid private room code.")
        return redirect("/")

    arena_renderer = "3d" if request.args.get("renderer") == "3d" else "dom"

    return render_template(
        "arena.html",
        user=user,
        match_mode=match_mode,
        private_code=private_code,
        arena_renderer=arena_renderer,
    )


def emit_log(room_id, message):
    match = active_matches.get(room_id)

    if match is not None:
        match.setdefault("logs", [])
        match["logs"].append(str(message))

    socketio.emit("battle_log", {"msg": message}, to=room_id)


def emit_battle_events(match, events):
    if not events:
        return

    for player_key in ["p1", "p2"]:
        player = match.get(player_key, {})

        if player.get("is_bot") or not player.get("sid"):
            continue

        socketio.emit(
            "battle_events",
            perspective_battle_events(events, player_key),
            to=player["sid"],
        )


def emit_state(room_id):
    match = active_matches.get(room_id)

    if not match:
        return

    for sid, state in build_game_state_payloads(room_id, match):
        socketio.emit("game_state_update", state, to=sid)

    try:
        emit_arena_state_v8(match, phase="sync")
    except Exception as error:
        print("ARENA V8 SYNC PATCH ERROR:", type(error).__name__, error)

    try:
        emit_arena_clean_state_to_match(match)
    except Exception as error:
        print("ARENA CLEAN STATE PATCH ERROR:", type(error).__name__, error)


def create_player_object(user, sid):
    deck = build_playable_deck(user.deck_json)
    hand = draw_beta_starting_hand(deck, 5, starting_energy=2)

    player = create_player_state(user, sid, deck, hand)

    reset_player_energy(player, 1)

    return player



def emit_v105_match_end_summary(room_id, match, winner_key):
    try:
        for line in build_match_summary_lines(match, winner_key):
            emit_log(room_id, line)

        mode = "training" if match.get("training") else "pvp"
        difficulty = match.get("bot_difficulty")

        if winner_key == "DRAW":
            emit_log(room_id, reward_line("Both players", mode, "draw", difficulty))
            return

        loser_key = "p2" if winner_key == "p1" else "p1"
        winner = match.get(winner_key, {})
        loser = match.get(loser_key, {})

        emit_log(room_id, reward_line(winner.get("name", "Winner"), mode, "win", difficulty))
        emit_log(room_id, reward_line(loser.get("name", "Loser"), mode, "loss", difficulty))

    except Exception as error:
        print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)












def find_match_for_sid(sid):
    room = player_rooms.get(sid)

    if room and room in active_matches:
        return room, active_matches[room]

    for room_code, match in active_matches.items():
        if (match.get("p1") or {}).get("sid") == sid:
            player_rooms[sid] = room_code
            return room_code, match

        if (match.get("p2") or {}).get("sid") == sid:
            player_rooms[sid] = room_code
            return room_code, match

    return None, None


def viewer_key_for_sid(match, sid):
    if (match.get("p2") or {}).get("sid") == sid:
        return "p2"

    return "p1"


def emit_arena_clean_state_to_match(match, message=None):
    """Emit the clean Arena state contract used by the single-screen client."""
    try:
        payloads = build_arena_clean_payloads(match, message=message)

        p1_sid = (match.get("p1") or {}).get("sid")
        p2_sid = (match.get("p2") or {}).get("sid")

        if p1_sid:
            socketio.emit("az48_state", payloads["p1"], room=p1_sid)

        if p2_sid:
            socketio.emit("az48_state", payloads["p2"], room=p2_sid)

    except Exception as error:
        print("ARENA CLEAN STATE EMIT ERROR:", type(error).__name__, error)


def emit_arena_state_v8(match, phase=None, message=None):
    """Emit canonical Arena V8 state payloads without replacing legacy payloads."""
    try:
        payloads = build_arena_payloads_for_match(match, phase=phase, message=message)

        p1_sid = (match.get("p1") or {}).get("sid")
        p2_sid = (match.get("p2") or {}).get("sid")

        if p1_sid:
            socketio.emit("game_state_update", payloads["p1"], room=p1_sid)
            socketio.emit("arena_state_update", payloads["p1"], room=p1_sid)

        if p2_sid:
            socketio.emit("game_state_update", payloads["p2"], room=p2_sid)
            socketio.emit("arena_state_update", payloads["p2"], room=p2_sid)

    except Exception as error:
        print("ARENA V8 PAYLOAD EMIT ERROR:", type(error).__name__, error)


def emit_v107_post_match_summary(match, viewer_key, result, rewards):
    try:
        viewer = match.get(viewer_key, {})

        if viewer.get("is_bot"):
            return

        sid = viewer.get("sid")

        if not sid:
            return

        socketio.emit(
            "post_match_summary",
            build_post_match_payload(match, viewer_key, result, rewards),
            to=sid,
        )
    except Exception as error:
        print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)


def end_match(room_id, winner_key, ending_reason="completed"):
    match = active_matches.get(room_id)

    if not match:
        return

    p1 = match["p1"]
    p2 = match["p2"]

    battle_logs = match.get("logs", [])
    is_bot_match = bool(match.get("is_bot_match") or match.get("training"))
    reward_difficulty = match.get("bot_difficulty")

    if winner_key == "DRAW":
        socketio.emit("game_over", {"result": "DRAW"}, to=p1["sid"])

        if not p2.get("is_bot"):
            socketio.emit("game_over", {"result": "DRAW"}, to=p2["sid"])

        winner_id = None
        winner_name = None
        result = history_result_for_ending(winner_key, ending_reason)

        p1_user = db.session.get(User, safe_user_id(p1)) if safe_user_id(p1) else None
        p2_user = db.session.get(User, safe_user_id(p2)) if safe_user_id(p2) else None

        p1_rewards = {"coins": 0, "xp": 0}
        p2_rewards = {"coins": 0, "xp": 0}

        if p1_user:
            p1_rewards = apply_match_rewards(
                p1_user,
                is_bot_match=is_bot_match,
                did_win=False,
                award_xp_function=award_xp,
                difficulty=reward_difficulty,
                result="draw",
            )
            increment_mission(p1_user, "play_1_match", 1)
            increment_mission(p1_user, "play_3_matches", 1)

        if p2_user:
            p2_rewards = apply_match_rewards(
                p2_user,
                is_bot_match=is_bot_match,
                did_win=False,
                award_xp_function=award_xp,
                difficulty=reward_difficulty,
                result="draw",
            )
            increment_mission(p2_user, "play_1_match", 1)
            increment_mission(p2_user, "play_3_matches", 1)

        emit_v107_post_match_summary(match, "p1", "DRAW", p1_rewards)

        if not p2.get("is_bot"):
            emit_v107_post_match_summary(match, "p2", "DRAW", p2_rewards)

        if is_bot_match:
            for training_user in [p1_user, p2_user]:
                if training_user:
                    training_user.first_training_completed = True
                    increment_mission(training_user, "play_1_training", 1)

    else:
        loser_key = "p2" if winner_key == "p1" else "p1"

        winner = match[winner_key]
        loser = match[loser_key]

        result = history_result_for_ending(winner_key, ending_reason)
        winner_id = safe_user_id(winner)
        winner_name = player_display_name(winner)

        if not winner.get("is_bot"):
            socketio.emit("game_over", {"result": "WIN"}, to=winner["sid"])

        if not loser.get("is_bot"):
            socketio.emit("game_over", {"result": "LOSE"}, to=loser["sid"])

        winner_user = db.session.get(User, safe_user_id(winner)) if safe_user_id(winner) else None
        loser_user = db.session.get(User, safe_user_id(loser)) if safe_user_id(loser) else None

        winner_rewards = {"coins": 0, "xp": 0}
        loser_rewards = {"coins": 0, "xp": 0}

        if winner_user:
            winner_user.wins += 1
            winner_rewards = apply_match_rewards(
                winner_user,
                is_bot_match=is_bot_match,
                did_win=True,
                award_xp_function=award_xp,
                difficulty=reward_difficulty,
            )

            increment_mission(winner_user, "play_1_match", 1)
            increment_mission(winner_user, "play_3_matches", 1)
            increment_mission(winner_user, "win_1_match", 1)

            if is_bot_match:
                winner_user.first_training_completed = True
                increment_mission(winner_user, "play_1_training", 1)
                increment_mission(winner_user, "win_1_training", 1)

        if loser_user:
            loser_user.losses += 1
            loser_rewards = apply_match_rewards(
                loser_user,
                is_bot_match=is_bot_match,
                did_win=False,
                award_xp_function=award_xp,
                difficulty=reward_difficulty,
            )

            increment_mission(loser_user, "play_1_match", 1)
            increment_mission(loser_user, "play_3_matches", 1)

            if is_bot_match:
                loser_user.first_training_completed = True
                increment_mission(loser_user, "play_1_training", 1)

        emit_v107_post_match_summary(match, winner_key, "WIN", winner_rewards)
        emit_v107_post_match_summary(match, loser_key, "LOSE", loser_rewards)

    history = MatchHistory(
        player1_id=safe_user_id(p1),
        player2_id=safe_user_id(p2),
        winner_id=winner_id,
        player1_name=player_display_name(p1),
        player2_name=player_display_name(p2),
        winner_name=winner_name,
        result=result,
        player1_final_hp=max(0, int(p1.get("hp", 0))),
        player2_final_hp=max(0, int(p2.get("hp", 0))),
        total_rounds=int(match.get("round", 1)),
        battle_log_json=json.dumps(battle_logs),
    )

    db.session.add(history)
    if winner_key == "DRAW":
        telemetry_reason = "draw" if ending_reason == "completed" else ending_reason
        record_match_telemetry(room_id, match, "p1", "p2", ending_reason=telemetry_reason)
    else:
        loser_key = "p2" if winner_key == "p1" else "p1"
        record_match_telemetry(room_id, match, winner_key, loser_key, ending_reason=ending_reason)

    update_card_stats_after_match(match, winner_key)

    log_rc_event(
        "match",
        "Match completed",
        details={
            "room_id": room_id,
            "winner_key": winner_key,
            "mode": "fallback_bot" if match.get("matchmaking_fallback") else "training" if match.get("training") else "bot" if match.get("is_bot_match") else "pvp",
            "round": match.get("round"),
        },
        user_id=safe_user_id(p1),
    )

    db.session.commit()

    player_rooms.pop(p1["sid"], None)

    if not p2.get("is_bot"):
        player_rooms.pop(p2["sid"], None)

    active_matches.pop(room_id, None)


def register_socket_handlers():
    from sockets.game_socket import register_game_socket_handlers

    register_game_socket_handlers(socketio, {
        "active_matches": active_matches,
        "player_rooms": player_rooms,
        "private_waiting_rooms": private_waiting_rooms,
        "socket_state": socket_state,
        "socket_event_hits": socket_event_hits,
        "db": db,
        "User": User,
        "bot_choose_play": bot_choose_play,
        "can_pay_cost": can_pay_cost,
        "cancel_unleash": cancel_unleash,
        "create_player_object": create_player_object,
        "current_user": current_user,
        "emit_battle_events": emit_battle_events,
        "emit_log": emit_log,
        "emit_state": emit_state,
        "end_match": end_match,
        "find_player_key": find_player_key,
        "increment_mission": increment_mission,
        "is_valid_room_code": is_valid_room_code,
        "log_rc_event": log_rc_event,
        "match_engine_factory": lambda: be2_engine(),
        "normalize_intent": normalize_intent,
        "normalize_room_code": normalize_room_code,
        "pay_card_cost": pay_card_cost,
        "register_card_played_for_ambition": register_card_played_for_ambition,
        "request_unleash": request_unleash,
        "resolve_battle": resolve_battle,
        "safe_user_id": safe_user_id,
        "set_player_intent": set_player_intent,
        "app": app,
    })


register_socket_handlers()




@app.route("/tutorial")
def tutorial():
    steps = [
        {
            "number": "01",
            "title": "Enter the Duel",
            "subtitle": "Ambitionz is a fantasy tactical card battler.",
            "description": "You win by reading the board, protecting your hero and turning small round choices into lasting pressure.",
            "objective": "Know the goal before entering Training.",
            "rule": "Protect your HP. Break the enemy hero.",
            "cta_label": "Start Training",
            "cta_url": url_for("training"),
        },
        {
            "number": "02",
            "title": "Choose Intent",
            "subtitle": "Strike, Guard or Focus defines the round.",
            "description": "Strike pressures, Guard survives, and Focus builds Ambition for future turns. Pick one before committing cards.",
            "objective": "Understand the intent triangle.",
            "rule": "Intent first. Cards second.",
            "cta_label": "Practice Intent",
            "cta_url": url_for("training"),
        },
        {
            "number": "03",
            "title": "Play Cards",
            "subtitle": "Spend Energy on one card each round.",
            "description": "Creatures claim lanes. Spells and traps apply their server-resolved effects. Your hand is a set of commitments, not a script.",
            "objective": "Learn hand, Energy and card timing.",
            "rule": "One card per round.",
            "cta_label": "View Deck",
            "cta_url": url_for("deck_builder"),
        },
        {
            "number": "04",
            "title": "Command Lanes",
            "subtitle": "Left, center and right decide combat.",
            "description": "Creatures fight across matching lanes. Empty enemy lanes let attackers hit the hero directly.",
            "objective": "Read where pressure will land.",
            "rule": "Lane-to-lane, then hero.",
            "cta_label": "See Collection",
            "cta_url": url_for("collection"),
        },
        {
            "number": "05",
            "title": "Ready and Resolve",
            "subtitle": "Ready locks your choice and reveals the result.",
            "description": "When both sides are ready, the backend resolves the round, updates HP, Ambition, deaths and the Round Summary.",
            "objective": "Trust the server as the source of truth.",
            "rule": "Ready resolves. Ambition grows.",
            "cta_label": "Start Training",
            "cta_url": url_for("training"),
        },
    ]

    return render_template("tutorial.html", user=current_user(), steps=steps)


@app.route("/campaign")
def campaign():
    chapters = [
        {
            "number": "01",
            "title": "The First Spark",
            "difficulty": "Beginner",
            "status": "Available",
            "objective": "Play your first training match and learn the basic duel rhythm.",
            "reward": "Starter XP, Coins and Training mission progress.",
            "url": url_for("training"),
        },
        {
            "number": "02",
            "title": "Broken Arena",
            "difficulty": "Beginner",
            "status": "Available",
            "objective": "Test your 30-card beta deck against the bot.",
            "reward": "Deck confidence and match reward progress.",
            "url": url_for("deck_builder"),
        },
        {
            "number": "03",
            "title": "The Ambition Trial",
            "difficulty": "Normal",
            "status": "Available",
            "objective": "Use Focus and Ambition to prepare a stronger round.",
            "reward": "Progression loop momentum.",
            "url": url_for("progression"),
        },
        {
            "number": "04",
            "title": "Rival Duel",
            "difficulty": "Normal",
            "status": "Coming Soon",
            "objective": "Face a stronger scripted rival with a clearer strategy.",
            "reward": "Future campaign chest.",
            "url": url_for("training"),
        },
        {
            "number": "05",
            "title": "Ascension Gate",
            "difficulty": "Hard",
            "status": "Coming Soon",
            "objective": "Clear the first campaign arc and prepare for ranked play.",
            "reward": "Future Founder cosmetic track.",
            "url": url_for("ranking"),
        },
    ]

    return render_template("campaign.html", user=current_user(), chapters=chapters)


@app.route("/training")
def training():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    arena_renderer = "3d" if request.args.get("renderer") == "3d" else "dom"

    return render_template(
        "arena.html",
        user=current_user(),
        training_mode=True,
        arena_renderer=arena_renderer,
    )






# =========================================================
# AMBITIONZ V1.20 — FEEDBACK COLLECTION 2.0
# =========================================================

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    categories = [
        {"value": "android_issue", "label": "Android issue"},
        {"value": "login_register", "label": "Login / Register"},
        {"value": "training_battle", "label": "Training battle"},
        {"value": "deck_builder", "label": "Deck builder"},
        {"value": "booster_shop", "label": "Booster shop"},
        {"value": "rewards_missions", "label": "Rewards / Missions"},
        {"value": "balance", "label": "Balance"},
        {"value": "visual_ui", "label": "Visual / UI"},
        {"value": "bug", "label": "Bug"},
        {"value": "suggestion", "label": "Suggestion"},
        {"value": "general", "label": "General"},
    ]

    severities = [
        {"value": "low", "label": "Low"},
        {"value": "normal", "label": "Normal"},
        {"value": "high", "label": "High"},
        {"value": "critical", "label": "Critical"},
    ]

    if request.method == "POST":
        category = request.form.get("category", "general").strip() or "general"
        severity = request.form.get("severity", "normal").strip() or "normal"
        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()
        page_url = request.form.get("page_url", "").strip()

        valid_categories = {item["value"] for item in categories}
        valid_severities = {item["value"] for item in severities}

        if category not in valid_categories:
            category = "general"

        if severity not in valid_severities:
            severity = "normal"

        if not title or len(title) < 4:
            flash("Feedback title must have at least 4 characters.")
            return redirect("/feedback")

        if not message or len(message) < 10:
            flash("Feedback message must have at least 10 characters.")
            return redirect("/feedback")

        try:
            daily_limit = int(app.config.get("FEEDBACK_DAILY_LIMIT", 10) or 10)
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            submitted_today = (
                FeedbackReport.query
                .filter_by(user_id=user.id)
                .filter(FeedbackReport.created_at >= today_start)
                .count()
            )

            if submitted_today >= daily_limit:
                flash("Daily feedback limit reached. Try again tomorrow.")
                log_rc_event(
                    "feedback",
                    "Feedback daily limit reached",
                    details={"limit": daily_limit},
                    user_id=user.id,
                    level="warning",
                )
                return redirect("/feedback")
        except Exception as error:
            print("FEEDBACK LIMIT CHECK ERROR:", type(error).__name__, error)

        report = FeedbackReport(
            user_id=user.id,
            username=user.username,
            category=category,
            severity=severity,
            title=title[:160],
            message=message,
            page_url=page_url[:255] if page_url else None,
            status="open",
        )

        db.session.add(report)

        try:
            log_system_event(
                "info",
                "feedback",
                f"Feedback submitted: {title[:80]}",
                user_id=user.id,
            )
        except Exception as error:
            print("FEEDBACK LOG ERROR:", type(error).__name__, error)

        db.session.commit()

        flash("Feedback sent. Thank you for helping improve the beta.")
        return redirect("/feedback")

    recent_reports = (
        FeedbackReport.query
        .filter_by(user_id=user.id)
        .order_by(FeedbackReport.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "feedback.html",
        user=user,
        categories=categories,
        severities=severities,
        recent_reports=recent_reports,
    )


@app.route("/admin/reports")
def admin_reports():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    reports = [
        {
            "title": "Balance Report",
            "description": "Catalog distribution, starter deck summary and outlier detection.",
            "endpoint": "admin_balance",
            "cta": "Open Balance",
            "status": "Active",
        },
        {
            "title": "System Health",
            "description": "Environment, database, SMTP, users, matches and logs.",
            "endpoint": "admin_system",
            "cta": "Open System",
            "status": "Active",
        },
        {
            "title": "Feedback Ops",
            "description": "Tester feedback and beta report pipeline.",
            "endpoint": "admin_feedback",
            "cta": "Open Feedback",
            "status": "Active",
        },
        {
            "title": "User Ops",
            "description": "Users, tester status, access and account actions.",
            "endpoint": "admin_users",
            "cta": "Open Users",
            "status": "Active",
        },
        {
            "title": "Dev Tools",
            "description": "SMTP test, cleanup tools and dangerous beta operations.",
            "endpoint": "admin_dev_tools",
            "cta": "Open Tools",
            "status": "Restricted",
        },
    ]

    return render_template(
        "admin_reports.html",
        user=current_user(),
        reports=reports,
    )


@app.route("/admin/balance")
def admin_balance():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    try:
        from collections import Counter
        from game.cards import CARD_CATALOG
        from game.deck import get_fixed_starter_deck_ids
        from tools.balance_report import cards_from_ids, find_outliers, summarize_monsters

        cards = list(CARD_CATALOG)
        starter_ids = get_fixed_starter_deck_ids()
        starter_cards = cards_from_ids(starter_ids)

        type_dist = Counter(card.get("type", "Unknown") for card in cards)
        element_dist = Counter(card.get("element", "Unknown") for card in cards)
        sigil_dist = Counter(card.get("sigil", "Unknown") for card in cards)
        rarity_dist = Counter(card.get("rarity", "Unknown") for card in cards)

        starter_type_dist = Counter(card.get("type", "Unknown") for card in starter_cards)
        starter_element_dist = Counter(card.get("element", "Unknown") for card in starter_cards)
        starter_sigil_dist = Counter(card.get("sigil", "Unknown") for card in starter_cards)
        starter_rarity_dist = Counter(card.get("rarity", "Unknown") for card in starter_cards)

        outliers = find_outliers(cards)[:12]
        starter_outliers = find_outliers(starter_cards)

        missing_starter_ids = [
            card_id for card_id in starter_ids
            if not any(card.get("id") == card_id for card in starter_cards)
        ]

        return render_template(
            "admin_balance.html",
            user=current_user(),
            total_cards=len(cards),
            monster_summary=summarize_monsters(cards),
            starter_total=len(starter_ids),
            starter_found=len(starter_cards),
            missing_starter_ids=missing_starter_ids,
            starter_monster_summary=summarize_monsters(starter_cards),
            type_dist=type_dist,
            element_dist=element_dist,
            sigil_dist=sigil_dist,
            rarity_dist=rarity_dist,
            starter_type_dist=starter_type_dist,
            starter_element_dist=starter_element_dist,
            starter_sigil_dist=starter_sigil_dist,
            starter_rarity_dist=starter_rarity_dist,
            outliers=outliers,
            starter_outliers=starter_outliers,
        )

    except Exception as error:
        print("ADMIN BALANCE ERROR:", type(error).__name__, error)
        flash("Could not load balance dashboard. Check server logs.")
        return redirect("/admin/reports")




@app.route("/beta-launch")
def beta_launch():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    return render_template("beta_launch.html", user=current_user())


@app.route("/admin")
def admin():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    try:
        total_users = User.query.count()
        verified_users = User.query.filter_by(account_status="active").count()
    except Exception as error:
        print("Admin dashboard query failed:", error)
        total_users = 0
        verified_users = 0

    return render_template(
        "admin.html",
        user=current_user(),
        total_users=total_users,
        verified_users=verified_users,
        total_matches=0,
        open_feedbacks=0,
        intent_metrics={
            "Strike": 0,
            "Guard": 0,
            "Focus": 0,
            "Unleash": 0,
            "Overreach": 0,
        },
        sigil_metrics={
            "Fury": 0,
            "Resolve": 0,
            "Insight": 0,
            "Ruin": 0,
            "Harmony": 0,
        },
        recent_feedback=[],
    )



@app.route("/complete-onboarding", methods=["POST"])
def complete_onboarding():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    if user:
        try:
            user.has_completed_onboarding = True
            log_rc_event("onboarding", "Onboarding completed", user_id=user.id)
            db.session.commit()
        except Exception as error:
            print("Complete onboarding failed:", error)
            db.session.rollback()

    return redirect("/training")



@app.route("/missions")
def missions():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    missions = []

    try:
        ensure_daily_missions(user)
        missions = (
            UserMission.query
            .filter_by(user_id=user.id)
            .order_by(UserMission.id.desc())
            .all()
        )

    except Exception as error:
        print("MISSIONS PAGE ERROR:", type(error).__name__, error)
        db.session.rollback()
        missions = []

    return render_template(
        "missions.html",
        user=user,
        missions=missions,
    )


@app.route("/missions/claim/<int:mission_id>", methods=["POST"])
def claim_user_mission(mission_id):
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    try:
        success, message = claim_mission(user, mission_id)

        if success:
            flash(message)
        else:
            flash(message)

    except Exception as error:
        print("MISSION CLAIM ERROR:", type(error).__name__, error)
        db.session.rollback()
        flash("Mission claim failed. Try again.")

    return redirect("/missions")




@app.route("/match-history")
def match_history():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    matches = []
    user = current_user()

    stats = {
        "total": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "winrate": 0,
    }

    try:
        if "MatchHistory" in globals():
            matches = (
                MatchHistory.query
                .order_by(MatchHistory.id.desc())
                .limit(50)
                .all()
            )

            user_matches = []

            for match in matches:
                if match.player1_id == user.id or match.player2_id == user.id:
                    user_matches.append(match)

            stats["total"] = len(user_matches)

            for match in user_matches:
                if match.result == "DRAW" or not match.winner_id:
                    stats["draws"] += 1
                elif match.winner_id == user.id:
                    stats["wins"] += 1
                else:
                    stats["losses"] += 1

            decided = stats["wins"] + stats["losses"]

            if decided > 0:
                stats["winrate"] = round((stats["wins"] / decided) * 100, 1)

    except Exception as error:
        print("Match history query failed:", error)
        matches = []

    return render_template(
        "match_history.html",
        user=user,
        matches=matches,
        stats=stats,
    )





@app.route("/welcome")
def welcome():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    try:
        return render_template("welcome.html", user=current_user())
    except Exception as error:
        print("WELCOME RENDER ERROR:", type(error).__name__, error)
        return redirect("/")





@app.route("/daily")
def daily():
    user = current_user()
    missions = ensure_daily_missions(user) if user else []

    return render_template(
        "daily.html",
        user=user,
        missions=missions,
    )


@app.route("/api/retention/event", methods=["POST"])
def api_retention_event():
    try:
        payload = request.get_json(silent=True) or {}
    except Exception:
        payload = {}

    event_key = str(payload.get("event_key") or "unknown").strip()[:120]

    if event_key not in ALLOWED_RETENTION_EVENTS:
        return jsonify({"ok": True})

    user = current_user()
    user_id = user.id if user else None
    rate_key = request_rate_limit_key(
        request,
        session,
        app.config.get("SECRET_KEY", ""),
        "retention_event",
        identity=str(user_id or "anonymous"),
    )

    try:
        limit = int(app.config.get("RETENTION_EVENT_RATE_LIMIT", 120) or 120)
        window_seconds = int(app.config.get("RETENTION_EVENT_RATE_WINDOW_SECONDS", 60) or 60)
    except (TypeError, ValueError):
        limit = 120
        window_seconds = 60

    if not retention_event_limiter.allow(rate_key, limit, window_seconds):
        return jsonify({"ok": True, "limited": True})

    page = str(payload.get("page") or request.referrer or "")[:220]
    metadata = payload.get("metadata") or {}

    if not isinstance(metadata, dict):
        metadata = {}

    event = RetentionEvent(
        user_id=user_id,
        event_key=event_key,
        page=page,
        metadata_json=json.dumps(metadata, ensure_ascii=False)[:4000],
    )

    db.session.add(event)
    db.session.commit()

    return jsonify({"ok": True})





@app.route("/match-history/<int:history_id>")
def match_history_detail(history_id):
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    history = MatchHistory.query.filter_by(id=history_id, user_id=user.id).first_or_404()

    summary = {}

    try:
        summary = json.loads(history.summary_json or "{}")
    except Exception:
        summary = {}

    return render_template(
        "match_history_detail.html",
        user=user,
        history=history,
        summary=summary,
    )






@app.route("/admin/economy-audit")
def admin_economy_audit():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    source = request.args.get("source", "").strip()
    q = request.args.get("q", "").strip()
    user_id = request.args.get("user_id", "").strip()

    premium_query = PremiumCurrencyLedger.query

    if source:
        premium_query = premium_query.filter(PremiumCurrencyLedger.source == source)

    if user_id.isdigit():
        premium_query = premium_query.filter(PremiumCurrencyLedger.user_id == int(user_id))

    if q:
        like = f"%{q}%"
        premium_query = premium_query.filter(
            db.or_(
                PremiumCurrencyLedger.transaction_key.like(like),
                PremiumCurrencyLedger.provider_receipt_id.like(like),
                PremiumCurrencyLedger.idempotency_key.like(like),
            )
        )

    premium_entries = premium_query.order_by(PremiumCurrencyLedger.id.desc()).limit(120).all()
    inventory_entries = InventoryOwnershipLedger.query.order_by(InventoryOwnershipLedger.id.desc()).limit(80).all()

    return render_template(
        "admin_economy_audit.html",
        user=user,
        premium_entries=premium_entries,
        inventory_entries=inventory_entries,
        source=source,
        q=q,
        user_id=user_id,
    )



@app.route("/inventory/repair", methods=["POST"])
def inventory_repair():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    result = repair_user_inventory_and_deck(user)

    flash(result.get("message", "Inventory repair complete."))

    return redirect(url_for("inventory"))


@app.route("/admin/users/<int:user_id>/repair-inventory", methods=["POST"])
def admin_repair_user_inventory(user_id):
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = User.query.get_or_404(user_id)
    result = repair_user_inventory_and_deck(user)

    flash(f"{user.username}: {result.get('message', 'Inventory repair complete.')}")

    return redirect(url_for("admin_economy_audit"))


@app.route("/inventory")
def inventory():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    # FIRST_LOGIN_INVENTORY_RECOVERY_V1
    ensure_user_has_playable_inventory(user)
    db.session.commit()

    items = InventoryOwnership.query.filter_by(user_id=user.id).order_by(InventoryOwnership.id.desc()).all()

    return render_template("inventory.html", user=user, items=items)


@app.route("/inventory/test-card-grant", methods=["POST"])
def inventory_test_card_grant():
    auth_redirect = dev_tools_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    card_id = request.form.get("card_id") or "base_test_card"

    ok, payload = grant_card(
        user=user,
        card_id=card_id,
        quantity=1,
        source="test_grant",
        idempotency_key=f"manual-card-grant-{user.id}-{card_id}",
        metadata={"reason": "local beta inventory test"},
    )

    if ok:
        db.session.commit()
        flash("Inventory updated.")
    else:
        db.session.rollback()
        flash(payload.get("message", "Inventory update failed."))

    return redirect(url_for("inventory"))


@app.route("/economy/premium-ledger")
def premium_ledger():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    entries = (
        PremiumCurrencyLedger.query
        .filter_by(user_id=user.id)
        .order_by(PremiumCurrencyLedger.id.desc())
        .limit(50)
        .all()
    )

    return render_template(
        "premium_ledger.html",
        user=user,
        entries=entries,
    )


@app.route("/economy/test-premium-grant", methods=["POST"])
def economy_test_premium_grant():
    auth_redirect = dev_tools_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    ok, payload = credit_gems(
        user=user,
        amount=10,
        source="test_grant",
        idempotency_key=f"manual-test-grant-{user.id}",
        metadata={"reason": "local beta test grant"},
    )

    if ok:
        db.session.commit()
        flash(payload.get("message", "Premium currency updated."))
    else:
        db.session.rollback()
        flash(payload.get("message", "Premium currency update failed."))

    return redirect(url_for("premium_ledger"))


@app.route("/progression")
def progression():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    missions = []
    progression_stats = {
        "username": user.username,
        "level": int(user.level or 1),
        "xp": int(user.xp or 0),
        "next_level_xp": int(user.next_level_xp or 100),
        "level_progress_percent": user.level_progress_percent,
        "wins": int(user.wins or 0),
        "losses": int(user.losses or 0),
        "total_matches": int(user.wins or 0) + int(user.losses or 0),
        "first_training_completed": bool(getattr(user, "first_training_completed", False)),
    }

    try:
        ensure_daily_missions(user)
        missions = UserMission.query.filter_by(user_id=user.id).order_by(UserMission.id.desc()).limit(6).all()
    except Exception as error:
        print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
        db.session.rollback()
        missions = []

    next_steps = [
        {
            "title": "Play a Match",
            "description": "Earn XP and coins from training or PvP.",
            "url": url_for("training"),
            "cta": "Play Training",
        },
        {
            "title": "Claim Missions",
            "description": "Convert completed objectives into XP and coins.",
            "url": url_for("missions"),
            "cta": "View Missions",
        },
        {
            "title": "Open Booster",
            "description": "Spend coins to grow your card collection.",
            "url": url_for("shop"),
            "cta": "Open Shop",
        },
        {
            "title": "Improve Deck",
            "description": "Tune your 30-card beta deck after pulling new cards.",
            "url": url_for("deck_builder"),
            "cta": "Edit Deck",
        },
        {
            "title": "Climb Ranking",
            "description": "Track your wins and sharpen your strategy.",
            "url": url_for("ranking"),
            "cta": "View Ranking",
        },
    ]

    return render_template(
        "progression.html",
        user=user,
        missions=missions,
        next_steps=next_steps,
        progression_stats=progression_stats,
    )


def emit_az48_state(match, viewer_sid=None, message=None):
    """Emit canonical clean-arena state to the current client/room."""
    try:
        payload = build_arena_clean_state(match, "p1", message=message)
        socketio.emit("az48_state", payload, room=viewer_sid) if viewer_sid else socketio.emit("az48_state", payload)
        socketio.emit("game_state_update", payload, room=viewer_sid) if viewer_sid else socketio.emit("game_state_update", payload)
        return payload
    except Exception as error:
        print("AZ48 STATE EMIT ERROR:", type(error).__name__, error)
        return None



def emit_az48_state_for_sid(sid=None, message=None):
    """Best-effort canonical state emit for clean arena."""
    try:
        sid = sid or request.sid

        candidates = []

        for name in ("active_matches", "matches", "MATCHES", "training_matches", "rooms", "game_rooms"):
            value = globals().get(name)

            if isinstance(value, dict):
                candidates.extend(value.values())

        for match in candidates:
            if not isinstance(match, dict):
                continue

            p1 = match.get("p1") or {}
            p2 = match.get("p2") or {}

            viewer_key = "p1"

            if str(p2.get("sid")) == str(sid):
                viewer_key = "p2"

            if str(p1.get("sid")) == str(sid) or str(p2.get("sid")) == str(sid):
                payload = build_arena_clean_state(match, viewer_key, message=message)
                socketio.emit("az48_state", payload, room=sid)
                return payload

        return None

    except Exception as error:
        print("AZ48 EMIT FOR SID ERROR:", type(error).__name__, error)
        return None




# =========================================================
# BE2 Battle Engine Bridge
# Card battler bridge for Arena Clean.
# =========================================================

def be2_room_for_sid(sid):
    return MatchEngineFacade.room_for_sid(sid)


def finalize_be2_match(room_code, match):
    winner = match.get("winner")

    if not winner:
        return

    if winner == "draw":
        winner_key = "DRAW"
    else:
        winner_key = "p1" if winner == "player" else "p2"

    try:
        match["p1"] = match.get("player") or match.get("p1") or {}
        match["p2"] = match.get("opponent") or match.get("p2") or {}
        match["logs"] = match.get("log") or match.get("logs") or []
        end_match(room_code, winner_key)
    except Exception as error:
        db.session.rollback()
        print("BE2 FINALIZE ERROR:", type(error).__name__, error)


def be2_engine():
    return MatchEngineFacade(active_matches, player_rooms, socketio.emit, finish_match=finalize_be2_match)


def be2_match_for_sid(sid):
    return be2_engine().match_for_sid(sid)


def be2_match_is_finished(match):
    return MatchEngineFacade.is_finished(match)


def emit_be2_finished_guard(sid, match=None):
    return be2_engine().emit_finished_guard(sid)


def emit_be2_state(sid, message=None):
    return be2_engine().emit_state(sid, message=message)


def start_be2_for_sid(sid, user=None, message="Battle Engine V2 started."):
    return be2_engine().start_training(sid, user=user, message=message)

# =========================================================
# AZ48 Clean Arena Socket Aliases
# Stable event names for the clean single-renderer arena.
# =========================================================

@socketio.on("arena_command_v1")
def arena_command_v1(data=None):
    sid = request.sid

    try:
        user = current_user()
    except Exception:
        user = None

    try:
        be2_engine().run_command(sid, data or {}, user=user)
    except Exception as error:
        socketio.emit("action_error", arena_command_error_payload(error), room=sid)
        emit_be2_state(sid)


@socketio.on("az48_start_training")
def az48_start_training(data=None):
    sid = request.sid

    try:
        user = current_user()
    except Exception:
        user = None

    start_be2_for_sid(sid, user=user, message="Battle Engine V2 started. Summon a creature, cast a spell, then press Ready.")


@socketio.on("az48_request_state")
def az48_request_state(data=None):
    sid = request.sid
    payload = emit_be2_state(sid)

    if not payload:
        try:
            user = current_user()
        except Exception:
            user = None

        start_be2_for_sid(sid, user=user, message="Battle Engine V2 started. Summon a creature, cast a spell, then press Ready.")


@socketio.on("az48_set_intent")
def az48_set_intent(data=None):
    sid = request.sid
    data = data or {}
    intent = data.get("intent") or "Focus"

    room, match = be2_match_for_sid(sid)

    if not match:
        try:
            user = current_user()
        except Exception:
            user = None
        start_be2_for_sid(sid, user=user, message="Battle Engine V2 started.")

    room, match = be2_match_for_sid(sid)

    if be2_match_is_finished(match):
        emit_be2_finished_guard(sid, match)
        return

    try:
        be2_engine().set_intent(sid, intent, message=f"{intent} selected. Play a creature, spell, guard or support.")
    except Exception as error:
        socketio.emit("action_error", {"code": "BE2_SET_INTENT_FAILED", "message": str(error)}, room=sid)
        emit_be2_state(sid)


@socketio.on("az48_play_card")
def az48_play_card(data=None):
    sid = request.sid
    data = data or {}

    room, match = be2_match_for_sid(sid)

    if not match:
        try:
            user = current_user()
        except Exception:
            user = None
        start_be2_for_sid(sid, user=user, message="Battle Engine V2 started.")

    room, match = be2_match_for_sid(sid)

    if be2_match_is_finished(match):
        emit_be2_finished_guard(sid, match)
        return

    try:
        be2_engine().play_card(
            sid,
            card_id=data.get("card_id") or data.get("id"),
            card_index=data.get("card_index"),
            lane=data.get("lane"),
            target=data.get("target"),
            message="Card played. Press Ready to resolve combat.",
        )
    except Exception as error:
        socketio.emit("action_error", {"code": "BE2_PLAY_CARD_FAILED", "message": str(error)}, room=sid)
        emit_be2_state(sid)


@socketio.on("az48_declare_ready")
def az48_declare_ready(data=None):
    sid = request.sid

    room, match = be2_match_for_sid(sid)

    if not match:
        try:
            user = current_user()
        except Exception:
            user = None
        start_be2_for_sid(sid, user=user, message="Battle Engine V2 started.")

    room, match = be2_match_for_sid(sid)

    if be2_match_is_finished(match):
        emit_be2_finished_guard(sid, match)
        return

    try:
        payload = be2_engine().ready(sid, message="Round resolved.")
        if payload and payload.get("winner"):
            socketio.emit("battle_log", {"message": payload.get("message")}, room=sid)
    except Exception as error:
        socketio.emit("action_error", {"code": "BE2_READY_FAILED", "message": str(error)}, room=sid)
        emit_be2_state(sid)


@socketio.on("az48_unleash")
def az48_unleash(data=None):
    sid = request.sid

    room, match = be2_match_for_sid(sid)

    if not match:
        try:
            user = current_user()
        except Exception:
            user = None
        start_be2_for_sid(sid, user=user, message="Battle Engine V2 started.")

    room, match = be2_match_for_sid(sid)

    if be2_match_is_finished(match):
        emit_be2_finished_guard(sid, match)
        return

    try:
        be2_engine().unleash(sid, message="Ambition Unleash prepared. Press Ready to resolve.")
    except Exception as error:
        socketio.emit("action_error", {"code": "BE2_UNLEASH_FAILED", "message": str(error)}, room=sid)
        emit_be2_state(sid)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "127.0.0.1")

    socketio.run(
        app,
        debug=app.config["DEBUG_MODE"],
        host=host,
        port=port,
        allow_unsafe_werkzeug=True,
    )

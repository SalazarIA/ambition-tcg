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
    deck_analysis_v115,
    create_starter_deck_from_collection,
)
from models import ensure_liveops_schema, BetaInvite, SystemLog, BoosterHistory, FeedbackReport, MatchHistory, User, UserMission, db, ensure_database_schema, ensure_beta_loop_schema, RetentionEvent, EconomyLedger, UserCosmetic, RewardLedger, ensure_reward_ledger_schema, PremiumCurrencyLedger, ensure_premium_currency_schema, InventoryOwnership, InventoryOwnershipLedger, ensure_inventory_ownership_schema
from game.progression import BETA_MISSION_DEFINITIONS, award_xp, claim_mission, ensure_beta_missions, ensure_daily_missions, increment_beta_mission, increment_mission, today_key
from services.admin.cleanup_service import clear_gameplay_data, delete_non_admin_users
from services.battle_summary import build_match_summary_lines
from services.card_stats import update_card_stats_after_match
from services.arena_payload import build_arena_payloads_for_match, build_arena_state_payload
from services.arena_command_v1 import arena_command_error_payload
from services.ascension_bot import run_bot_turn as run_ascension_bot_turn
from services.ascension_cards import build_ascension_starter_deck, get_ascension_catalog, validate_ascension_deck
from services.ascension_engine import (
    AscensionActionError,
    attempt_dominate as ascension_attempt_dominate,
    choose_intent as ascension_choose_intent,
    create_match as create_ascension_match,
    legal_actions as ascension_legal_actions,
    play_card as ascension_play_card,
    resolve_clash as ascension_resolve_clash,
)
from services.ascension_history import append_history_record, build_history_record, read_history_records
from services.ascension_payloads import action_response as ascension_action_response, public_match_state as public_ascension_match_state
from services.ascension_progression import build_ascension_rewards, progression_event_from_match
from services.ascension_taxonomy import ascension_deck_summary, enrich_ascension_card
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
from services.beta_telemetry import append_jsonl, normalize_feedback_payload, normalize_telemetry_payload, utc_iso
from routes.security_ops import register_security_ops_routes
from game.rules import can_pay_cost, pay_card_cost, reset_player_energy
from game.engine import register_card_played_for_ambition, request_unleash, cancel_unleash
from game.state import create_player_state, set_player_intent
from game.matchmaking import generate_private_room_code, is_valid_room_code, normalize_room_code
from game.bot_ai import bot_choose_play
from game.rewards import apply_match_rewards
from services.economy_service import cosmetic_catalog_for_user, grant_cosmetic, spend_currency, add_currency, get_balance, record_ledger, PREMIUM_CURRENCY_KEY, SOFT_CURRENCY_KEY
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
ascension_training_matches = {}
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
wallet_event_limiter = SlidingWindowRateLimiter()
economy_action_limiter = SlidingWindowRateLimiter()
beta_telemetry_limiter = SlidingWindowRateLimiter()
beta_feedback_limiter = SlidingWindowRateLimiter()

GOLD_CURRENCY_KEY = SOFT_CURRENCY_KEY
GOLD_DISPLAY_NAME = "Gold"
GUEST_GOLD_SESSION_KEY = "ambitionz_guest_gold_balance"
GUEST_GOLD_STARTING_BALANCE = 300
DAILY_GOLD_REWARD = 75

CSRF_EXEMPT_ENDPOINTS = {
    "beta_event",
    "api_retention_event",
    "api_beta_telemetry",
    "api_beta_feedback",
    "api_ascension_start",
    "api_ascension_state",
    "api_ascension_intent",
    "api_ascension_play",
    "api_ascension_commit",
    "api_ascension_dominate",
}
CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
ALLOWED_RETENTION_EVENTS = {
    "campaign_result",
    "campaign_start",
    "campaign_view",
    "collection_view",
    "daily_view",
    "daily_claim",
    "daily_claimed",
    "deck_builder_view",
    "deck_save_attempt",
    "feedback_submit",
    "feedback_view",
    "booster_opened",
    "currency_credit",
    "currency_debit",
    "home_cta_play",
    "match_recorded",
    "mission_complete",
    "mission_cta_click",
    "mission_progress",
    "mission_reward_claimed",
    "onboarding_view",
    "page_view",
    "post_match_summary_view",
    "roadmap_view",
    "shop_purchase",
    "training_result_view",
    "training_start_click",
    "tutorial_start",
    "ui_click",
    "xp_awarded",
}


def create_database_tables():
    with app.app_context():
        db.create_all()
        try:
            ensure_database_schema()
            ensure_beta_loop_schema()
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


def beta_deck_status(user):
    status = {
        "is_valid": False,
        "selected_count": 0,
        "errors": [],
        "label": "Login required",
    }

    if not user:
        return status

    try:
        collection_ids = owned_card_ids_for_user(user)
        deck_ids = load_card_ids(user.deck_json)
        errors = validate_deck(deck_ids, collection_ids)
        status.update(
            {
                "is_valid": len(errors) == 0,
                "selected_count": len(deck_ids),
                "errors": errors,
                "label": "Valid 30-card beta deck" if len(errors) == 0 else "Deck needs attention",
            }
        )
    except Exception as error:
        print("BETA DECK STATUS ERROR:", type(error).__name__, error)
        status["errors"] = ["Deck status unavailable."]
        status["label"] = "Deck status unavailable"

    return status


def beta_collection_progress(user):
    progress = {
        "owned_unique": 0,
        "catalog_total": len(CARD_CATALOG),
        "completion_percent": 0,
        "total_owned": 0,
        "label": "Collection preview",
    }

    if not user:
        return progress

    try:
        ensure_user_has_playable_inventory(user)
        db.session.commit()
        cards = build_collection_from_inventory(user, include_zero=True)
        owned_cards = [card for card in cards if int(card.get("count") or 0) > 0]
        catalog_total = len(cards) or len(CARD_CATALOG)
        owned_unique = len(owned_cards)
        progress.update(
            {
                "owned_unique": owned_unique,
                "catalog_total": catalog_total,
                "completion_percent": int(round((owned_unique / catalog_total) * 100)) if catalog_total else 0,
                "total_owned": sum(int(card.get("count") or 0) for card in owned_cards),
                "label": "Starter collection" if owned_unique else "Beta catalog",
            }
        )
    except Exception as error:
        print("BETA COLLECTION PROGRESS ERROR:", type(error).__name__, error)
        db.session.rollback()

    return progress


def beta_daily_reward_for_streak(streak):
    try:
        streak = int(streak or 1)
    except (TypeError, ValueError):
        streak = 1

    streak = max(1, streak)
    gold = min(150, DAILY_GOLD_REWARD + ((streak - 1) * 15))
    xp = min(55, 35 + ((streak - 1) * 5))

    return {
        "streak": streak,
        "xp": xp,
        "gold": gold,
        "label": f"{xp} XP + {gold} Gold",
    }


def projected_daily_streak(user, today=None):
    if not user:
        return 1

    today = today or today_key()
    last_claim = str(getattr(user, "daily_last_checkin_date", "") or "")
    current_streak = int(getattr(user, "daily_streak", 0) or 0)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    if last_claim == today:
        return max(1, current_streak)

    if last_claim == yesterday:
        return max(1, current_streak + 1)

    return 1


def build_first_session_questline(user=None, deck_status=None, wallet=None, collection_progress=None):
    deck_status = deck_status or beta_deck_status(user)
    wallet = wallet or gold_wallet_payload(user)
    collection_progress = collection_progress or beta_collection_progress(user)
    total_matches = int(getattr(user, "wins", 0) or 0) + int(getattr(user, "losses", 0) or 0) if user else 0
    trained = bool(getattr(user, "first_training_completed", False)) if user else False
    reward_seen = bool(user and (int(getattr(user, "total_xp", 0) or 0) > 0 or int(wallet.get("balance", 0) or 0) > GUEST_GOLD_STARTING_BALANCE))
    booster_count = 0

    if user:
        try:
            booster_count = BoosterHistory.query.filter_by(user_id=user.id).count()
        except Exception as error:
            print("FIRST SESSION BOOSTER COUNT ERROR:", type(error).__name__, error)
            booster_count = 0

    can_buy_booster = bool(user and int(wallet.get("balance", 0) or 0) >= int(get_booster_pack("elemental").get("cost", 300)))
    collection_seen = bool(user and (int(collection_progress.get("owned_unique", 0) or 0) > 0 or bool(deck_status.get("is_valid"))))

    steps = [
        {
            "key": "enter",
            "number": "01",
            "title": "Enter the beta",
            "description": "Open or create a duelist profile so progress can persist.",
            "complete": bool(user),
            "url": url_for("progression") if user else url_for("register"),
            "cta": "Open Progression" if user else "Register",
        },
        {
            "key": "training",
            "number": "02",
            "title": "Play Ascension Duel",
            "description": "Finish one compact duel and read the Chronicle.",
            "complete": bool(trained or total_matches > 0),
            "url": url_for("training"),
            "cta": "Play Ascension Duel",
        },
        {
            "key": "reward",
            "number": "03",
            "title": "Collect progress",
            "description": "Review XP, Gold, missions and the post-match reward reveal.",
            "complete": reward_seen,
            "url": url_for("missions") if user else url_for("login"),
            "cta": "Claim Rewards" if user else "Login",
        },
        {
            "key": "booster",
            "number": "04",
            "title": "Open a booster",
            "description": "Spend earned Gold on a beta booster when your wallet is ready.",
            "complete": booster_count > 0,
            "ready": can_buy_booster,
            "url": url_for("shop") if user else url_for("login"),
            "cta": "Open Shop" if user else "Login",
        },
        {
            "key": "collection_deck",
            "number": "05",
            "title": "Inspect Collection / Deck",
            "description": "Check unlocks, keep the Ascension deck legal, then play again.",
            "complete": collection_seen,
            "url": url_for("deck_builder_ascension") if user else url_for("collection_ascension"),
            "cta": "Improve Deck",
        },
    ]

    completed = sum(1 for step in steps if step.get("complete"))
    next_step = next((step for step in steps if not step.get("complete")), steps[-1])

    return {
        "title": "First Session Questline",
        "subtitle": "A five-minute path from first click to a stronger next match.",
        "steps": steps,
        "completed": completed,
        "total": len(steps),
        "percent": int(round((completed / max(1, len(steps))) * 100)),
        "next_step": next_step,
        "dismiss_key": "ambitionz_first_session_questline_dismissed_v1",
        "is_complete": completed == len(steps),
    }


def build_deck_readiness_coach(user=None, deck_ids=None, collection_ids=None, deck_status=None, deck_analysis=None):
    if user and deck_ids is None:
        deck_ids = load_card_ids(getattr(user, "deck_json", "[]") or "[]")

    if user and collection_ids is None:
        collection_ids = owned_card_ids_for_user(user)

    deck_ids = deck_ids or []
    collection_ids = collection_ids or []
    deck_status = deck_status or beta_deck_status(user)
    deck_analysis = deck_analysis or deck_analysis_v115(deck_ids)
    stats = deck_analysis.get("stats", {}) if isinstance(deck_analysis, dict) else {}
    energy = deck_analysis.get("energy", {}) if isinstance(deck_analysis, dict) else {}
    elements = deck_analysis.get("elements", {}) if isinstance(deck_analysis, dict) else {}
    deck_counter = Counter(deck_ids)
    collection_counter = Counter(collection_ids)
    locked_count = sum(
        max(0, int(amount or 0) - int(collection_counter.get(card_id, 0) or 0))
        for card_id, amount in deck_counter.items()
    )
    recommendations = []
    total = int(stats.get("total", len(deck_ids)) or 0)
    monsters = int(stats.get("monsters", 0) or 0)
    spells = int(stats.get("spells", 0) or 0)
    traps = int(stats.get("traps", 0) or 0)
    average_cost = float(energy.get("average_cost", 0) or 0)
    early_curve = int((energy.get("curve", {}) or {}).get(1, 0) or 0) + int((energy.get("curve", {}) or {}).get(2, 0) or 0)

    if total == 0:
        status = "empty"
        label = "Deck empty"
        recommendations.append("Use Auto Build to restore the legal 30-card beta starter deck.")
    elif total < 30:
        status = "incomplete"
        label = "Deck incomplete"
        recommendations.append(f"Add {30 - total} more card{'s' if 30 - total != 1 else ''} before testing.")
    elif not bool(deck_status.get("is_valid")):
        status = "needs_attention"
        label = "Deck needs attention"
    else:
        status = "ready"
        label = "Training ready"
        recommendations.append("Deck is legal. Test it in Training and watch the post-match coach.")

    if locked_count > 0:
        recommendations.append(f"{locked_count} selected card copy/copies are not owned yet. Open boosters or run Auto Build.")
    if monsters < 21:
        recommendations.append("Add more creatures so lanes do not fall behind.")
    if spells > 8 or traps > 5:
        recommendations.append("Avoid too many spells/traps; the beta deck wants reliable lane bodies.")
    if average_cost > 3.2:
        recommendations.append("Reduce average cost so early turns stay playable.")
    if total and early_curve < 12:
        recommendations.append("Add more cost 1-2 cards for cleaner openings.")
    if len([name for name, amount in elements.items() if name != "Global" and int(amount or 0) > 0]) < 2 and total:
        recommendations.append("Consider a second element so matchups have more flexibility.")

    if not recommendations:
        recommendations.append("Deck shape is stable. Play Training, then adjust from real match results.")

    primary_url = url_for("training") if status == "ready" else url_for("deck_builder")
    primary_cta = "Test in Training" if status == "ready" else "Fix Deck"

    if locked_count > 0:
        primary_url = url_for("shop")
        primary_cta = "Open Booster"

    return {
        "status": status,
        "label": label,
        "total": total,
        "monsters": monsters,
        "spells": spells,
        "traps": traps,
        "average_cost": average_cost,
        "elements": elements,
        "early_curve": early_curve,
        "locked_count": locked_count,
        "recommendations": recommendations[:4],
        "primary_url": primary_url,
        "primary_cta": primary_cta,
    }


def build_post_match_next_best_action(user, rewards=None, mission_updates=None, deck_status=None):
    rewards = rewards or {}
    mission_updates = mission_updates or []
    deck_status = deck_status or beta_deck_status(user)
    gold_balance = get_gold_balance(user) if user else 0
    booster_cost = int(get_booster_pack("elemental").get("cost", 300) or 300)
    gained_gold = int(rewards.get("coins", 0) or 0)
    mission_ready = any(update.get("completed") or update.get("is_complete") or update.get("just_completed") for update in mission_updates if isinstance(update, dict))

    if user and gold_balance >= booster_cost:
        return {
            "kind": "shop",
            "label": "Open Booster",
            "title": "You have enough Gold for a booster.",
            "description": f"{gold_balance} Gold is ready. Open a beta pack or keep saving.",
            "url": url_for("shop"),
            "reason": "gold_ready",
        }

    if mission_ready:
        return {
            "kind": "missions",
            "label": "Claim Mission",
            "title": "A mission moved forward.",
            "description": "Claim completed objectives before the next Training run.",
            "url": url_for("missions"),
            "reason": "mission_ready",
        }

    if user and not bool(deck_status.get("is_valid")):
        return {
            "kind": "deck",
            "label": "Fix Deck",
            "title": "Your deck needs attention.",
            "description": "Deck Coach can restore or tune the legal 30-card beta deck.",
            "url": url_for("deck_builder"),
            "reason": "deck_invalid",
        }

    if gained_gold > 0:
        return {
            "kind": "progression",
            "label": "Review Progress",
            "title": "Gold and XP were added.",
            "description": "Check level progress, Daily streak and the next reward target.",
            "url": url_for("progression") if user else url_for("login"),
            "reason": "reward_review",
        }

    return {
        "kind": "training",
        "label": "Play Again",
        "title": "Run it back.",
        "description": "Play another Training match with the same deck and cleaner decisions.",
        "url": url_for("training"),
        "reason": "fallback",
    }


def build_beta_journey(user=None, deck_status=None):
    deck_status = deck_status or beta_deck_status(user)
    total_matches = int(getattr(user, "wins", 0) or 0) + int(getattr(user, "losses", 0) or 0) if user else 0
    trained = bool(getattr(user, "first_training_completed", False)) if user else False
    onboarded = bool(getattr(user, "has_completed_onboarding", False)) if user else False
    deck_ready = bool(deck_status.get("is_valid"))

    return [
        {
            "number": "01",
            "title": "Enter",
            "description": "Create or open your beta account so progress can be saved.",
            "url": url_for("progression") if user else url_for("login"),
            "cta": "Open Progression" if user else "Login",
            "status": "Done" if user else "Next",
        },
        {
            "number": "02",
            "title": "Learn",
            "description": "Read the Intent, Champion and Commit flow before the first duel.",
            "url": url_for("tutorial"),
            "cta": "Tutorial",
            "status": "Done" if onboarded else "Recommended",
        },
        {
            "number": "03",
            "title": "Play Training",
            "description": "Run a quick Ascension Duel against the bot.",
            "url": url_for("training"),
            "cta": "Play Ascension Duel",
            "status": "Done" if trained else "Next",
        },
        {
            "number": "04",
            "title": "Review Reward",
            "description": "Check XP, Gold and the post-match reward preview.",
            "url": url_for("progression") if user else url_for("login"),
            "cta": "Progression",
            "status": "Done" if total_matches > 0 else "After match",
        },
        {
            "number": "05",
            "title": "Inspect Collection",
            "description": "See owned and locked cards before tuning the deck.",
            "url": url_for("collection_ascension"),
            "cta": "Collection",
            "status": "Available" if user else "Login",
        },
        {
            "number": "06",
            "title": "Tune Deck",
            "description": "Keep the Ascension beta deck legal at 30 cards.",
            "url": url_for("deck_builder_ascension"),
            "cta": "Deck Builder",
            "status": "Done" if deck_ready else "Check deck",
        },
        {
            "number": "07",
            "title": "Play Again",
            "description": "Return to Training with a clearer plan.",
            "url": url_for("training"),
            "cta": "Play Again",
            "status": "Recommended" if total_matches > 0 else "Future",
        },
    ]


def build_campaign_chapters(user=None, deck_status=None):
    deck_status = deck_status or beta_deck_status(user)
    completed_chapters = set()

    if user:
        try:
            completed_chapters = {
                str(chapter_id)
                for (chapter_id,) in (
                    db.session.query(MatchHistory.campaign_chapter_id)
                    .filter(
                        MatchHistory.player1_id == user.id,
                        MatchHistory.campaign_chapter_id.isnot(None),
                    )
                    .distinct()
                    .all()
                )
                if chapter_id
            }
        except Exception as error:
            print("CAMPAIGN CHAPTER STATE ERROR:", type(error).__name__, error)
            completed_chapters = set()

    chapter_defs = [
        {
            "number": "01",
            "chapter_id": "first_signal",
            "title": "First Signal",
            "description": "Learn the rhythm of Intent, Champion focus and Commit in a short bot duel.",
            "lore": "A quiet signal rises from the first arena floor, asking for discipline before glory.",
            "difficulty": "easy",
            "reward": "35 XP beta + campaign mission progress.",
            "cta_label": "Start Chapter",
        },
        {
            "number": "02",
            "chapter_id": "ember_vault",
            "title": "Ember Vault",
            "description": "Play a short duel after reviewing how owned cards shape the starter plan.",
            "lore": "The vault does not promise riches; it shows what your current deck can actually use.",
            "difficulty": "easy",
            "reward": "40 XP beta + reward preview in match summary.",
            "cta_label": "Play Chapter",
        },
        {
            "number": "03",
            "chapter_id": "thirty_card_oath",
            "title": "Thirty-Card Oath",
            "description": "Confirm your beta deck discipline in a normal training encounter.",
            "lore": "A deck is not a pile of power. It is a promise: thirty cards, one plan.",
            "difficulty": "normal",
            "reward": "45 XP beta + deck confidence checkpoint.",
            "cta_label": "Play Chapter",
        },
        {
            "number": "04",
            "chapter_id": "ambition_trial",
            "title": "Ambition Trial",
            "description": "Use Focus and tempo to set up a stronger round in a campaign-marked duel.",
            "lore": "Ambition grows when patience survives the first strike.",
            "difficulty": "normal",
            "reward": "55 XP beta + mission progress.",
            "cta_label": "Play Chapter",
        },
        {
            "number": "05",
            "chapter_id": "gate_rival",
            "title": "Gate Rival",
            "description": "A hard beta duel that marks the end of the first campaign path.",
            "lore": "A rival waits beyond the beta gate, testing whether the first plan can hold.",
            "difficulty": "hard",
            "reward": "70 XP beta + first arc completion preview.",
            "cta_label": "Play Chapter",
        },
    ]

    chapters = []
    previous_complete = True

    for definition in chapter_defs:
        chapter = dict(definition)
        chapter["completed"] = chapter["chapter_id"] in completed_chapters
        chapter["locked"] = not bool(user) or not previous_complete
        chapter["url"] = url_for("campaign_start", chapter_id=chapter["chapter_id"]) if not chapter["locked"] else url_for("campaign")

        if chapter["completed"]:
            chapter["status"] = "completed"
        elif not user:
            chapter["status"] = "login"
        elif chapter["locked"]:
            chapter["status"] = "locked"
        else:
            chapter["status"] = "recommended" if previous_complete else "available"

        chapter["difficulty_label"] = chapter["difficulty"].title()
        chapter["requires_deck_check"] = chapter["chapter_id"] == "thirty_card_oath" and not bool(deck_status.get("is_valid"))

        if chapter["requires_deck_check"] and not chapter["completed"]:
            chapter["status"] = "deck check"
            chapter["url"] = url_for("deck_builder")
            chapter["cta_label"] = "Check Deck"
            chapter["locked"] = False

        chapters.append(chapter)
        previous_complete = chapter["completed"]

    return chapters


def get_campaign_chapter(chapter_id, user=None, deck_status=None):
    chapter_id = str(chapter_id or "").strip()

    for chapter in build_campaign_chapters(user, deck_status):
        if chapter.get("chapter_id") == chapter_id:
            return chapter

    return None


def build_beta_mission_guides(user, missions, deck_status=None):
    deck_status = deck_status or beta_deck_status(user)
    mission_by_key = {mission.mission_key: mission for mission in missions or []}

    def mission_progress(definition):
        key = definition["key"]
        mission = mission_by_key.get(key)

        if mission:
            progress = int(mission.progress or 0)
            target = int(mission.target or definition.get("target", 1) or 1)
            complete = bool(mission.is_complete)
        elif key == "complete_tutorial":
            progress = 1 if getattr(user, "has_completed_onboarding", False) else 0
            target = int(definition.get("target", 1) or 1)
            complete = progress >= target
        elif key == "save_or_validate_deck":
            progress = 1 if deck_status.get("is_valid") else 0
            target = int(definition.get("target", 1) or 1)
            complete = progress >= target
        else:
            progress = 0
            target = int(definition.get("target", 1) or 1)
            complete = False

        return progress, target, complete

    guides = []

    for definition in BETA_MISSION_DEFINITIONS:
        progress, target, complete = mission_progress(definition)
        endpoint = str(definition.get("cta_endpoint") or "training")
        mission = mission_by_key.get(definition["key"])
        claimed = bool(mission and mission.is_claimed)

        if endpoint not in {"training", "tutorial", "collection", "deck_builder", "campaign", "daily"}:
            endpoint = "training"

        guides.append({
            "id": definition["key"],
            "mission_id": mission.id if mission else None,
            "title": definition["title"],
            "description": definition["description"],
            "category": definition.get("category") or "Beta",
            "progress": progress,
            "target": target,
            "progress_label": f"{progress}/{target}",
            "percent": min(100, round((progress / max(1, target)) * 100)),
            "reward": definition.get("reward_preview") or f"{definition.get('xp_reward', 0)} XP",
            "status": "Preview" if not user else "Claimed" if claimed else "Complete" if complete else "Active",
            "claimable": bool(mission and complete and not claimed),
            "url": url_for(endpoint),
            "cta": definition.get("cta_label") or "Open",
        })

    return guides


def build_mission_board_summary(mission_guides, daily_missions):
    guides = mission_guides or []
    daily_missions = daily_missions or []
    category_counts = Counter(guide.get("category") or "Beta" for guide in guides)
    completed_guides = sum(1 for guide in guides if guide.get("status") in {"Complete", "Claimed"})
    claimable_daily = sum(1 for mission in daily_missions if mission.is_complete and not mission.is_claimed)

    return {
        "total_beta": len(guides),
        "completed_beta": completed_guides,
        "active_beta": max(0, len(guides) - completed_guides),
        "daily_total": len(daily_missions),
        "daily_claimable": claimable_daily,
        "categories": [
            {"name": name, "count": count}
            for name, count in sorted(category_counts.items(), key=lambda item: (item[0] != "Battle", item[0]))
        ],
    }


def build_daily_checkin(user, missions):
    complete_count = sum(1 for mission in missions or [] if mission.is_complete)
    claimed_count = sum(1 for mission in missions or [] if mission.is_claimed)
    claimable_count = sum(1 for mission in missions or [] if mission.is_complete and not mission.is_claimed)
    active_count = len(missions or [])
    today = today_key()
    last_claim = str(getattr(user, "daily_last_checkin_date", "") or "") if user else ""
    claimed_today = bool(user and last_claim == today)
    streak = int(getattr(user, "daily_streak", 0) or 0) if user else 0
    best_streak = int(getattr(user, "daily_best_streak", 0) or 0) if user else 0
    claim_streak = projected_daily_streak(user, today) if user else 1
    claim_reward = beta_daily_reward_for_streak(claim_streak)
    next_reward_streak = (streak + 1) if claimed_today and streak else (claim_streak + 1)
    next_reward = beta_daily_reward_for_streak(next_reward_streak)

    if not user:
        state = "Beta preview"
        message = "Login to activate daily missions, XP and Gold reward previews."
    elif claimed_today:
        state = "Checked in"
        message = f"Daily XP and Gold claimed. Come back tomorrow for {next_reward['label']}."
    elif claimable_count:
        state = "Reward ready"
        message = "Daily check-in is ready, and completed missions can still be claimed."
    else:
        state = "Available today"
        message = "Claim today's scaling XP and Gold, then play Training to move the mission board forward."

    return {
        "state": state,
        "message": message,
        "today": today,
        "claimed_today": claimed_today,
        "can_claim": bool(user and not claimed_today),
        "claim_reward": claim_reward["label"],
        "next_reward": f"Tomorrow: {next_reward['label']} + mission progress",
        "claim_xp": claim_reward["xp"],
        "claim_gold": claim_reward["gold"],
        "next_xp": next_reward["xp"],
        "next_gold": next_reward["gold"],
        "projected_streak": claim_streak,
        "reward_card": {
            "label": "Daily Reward",
            "available": bool(user and not claimed_today),
            "claimed": claimed_today,
            "preview": claim_reward["label"],
            "tomorrow": "Next reward tomorrow",
        },
        "active_count": active_count,
        "complete_count": complete_count,
        "claimed_count": claimed_count,
        "claimable_count": claimable_count,
        "streak": streak,
        "best_streak": best_streak,
        "streak_label": f"{streak} day streak" if user else "Preview only",
        "reset_label": "Resets tomorrow at local midnight",
        "calendar": [
            {"day": f"Day {day}", "reward": beta_daily_reward_for_streak(day)["label"], "status": "Claimed" if claimed_today and streak >= day else "Current streak" if streak >= day else "Next" if day == claim_streak and not claimed_today else "Future"}
            for day in range(1, 6)
        ],
    }


def combat_card_element(card_id):
    card_id = str(card_id or "").strip()
    if not card_id:
        return ""

    for card in CARD_CATALOG:
        if str(card.get("id") or "") == card_id:
            return str(card.get("element") or "")

    return ""


def build_match_mission_metrics(match, player_key):
    side = "player" if player_key in {"p1", "player"} else "opponent"
    opponent_side = "opponent" if side == "player" else "player"

    def safe_int(value):
        try:
            return int(value or 0)
        except Exception:
            return 0

    metrics = {
        "cards_played": 0,
        "damage_dealt": 0,
        "ambition_gained": 0,
        "elements": Counter(),
        "intents": Counter(),
    }
    events = [
        event
        for event in (match.get("combat_log") or [])
        if isinstance(event, dict)
    ]

    if not events:
        for source_key in ("round_events", "events"):
            value = match.get(source_key)
            if isinstance(value, list):
                events.extend(event for event in value if isinstance(event, dict))

    for event in events:
        event_type = str(event.get("type") or event.get("kind") or "").lower()
        event_side = str(event.get("side") or event.get("actor") or "").lower()

        if event_type == "card_played" and event_side == side:
            metrics["cards_played"] += 1
            element = combat_card_element(event.get("card_id"))
            if element:
                metrics["elements"][element] += 1

        if (
            event_type == "hero_damage"
            and str(event.get("attacker_side") or "").lower() == side
            and str(event.get("target_side") or "").lower() == opponent_side
        ):
            metrics["damage_dealt"] += max(0, safe_int(event.get("damage") or event.get("amount") or 0))

        if event_type == "ambition_gain" and event_side == side:
            metrics["ambition_gained"] += max(0, safe_int(event.get("amount") or 0))

        if event_type == "intent_selected" and event_side == side:
            intent = str(event.get("intent") or "").strip().title()
            if intent in {"Strike", "Guard", "Focus"}:
                metrics["intents"][intent] += 1

    return metrics


def track_match_mission_v2(user, room_id, match_mode, result_label, player_key, match):
    if not user:
        return []

    updates = []
    metrics = build_match_mission_metrics(match, player_key)

    def append_update(key, amount=1, metadata=None):
        update = track_beta_mission(
            user,
            key,
            amount=amount,
            page="/arena",
            metadata={
                "room_id": room_id,
                "mode": match_mode,
                "result": result_label,
                **(metadata or {}),
            },
        )
        if update:
            updates.append(update)

    if result_label == "WIN" and match_mode in {"training", "campaign", "fallback_bot"}:
        append_update("win_training_match")

    if metrics["damage_dealt"]:
        append_update("deal_damage_total", metrics["damage_dealt"], {"damage": metrics["damage_dealt"]})

    if metrics["cards_played"]:
        append_update("play_cards_total", metrics["cards_played"], {"cards_played": metrics["cards_played"]})

    for element, amount in metrics["elements"].items():
        mission_key = {
            "Fire": "play_fire_card",
            "Water": "play_water_card",
            "Earth": "play_earth_card",
            "Plant": "play_plant_card",
        }.get(element)
        if mission_key:
            append_update(mission_key, amount, {"element": element, "cards_played": amount})

    if metrics["ambition_gained"]:
        append_update("gain_ambition_total", metrics["ambition_gained"], {"ambition": metrics["ambition_gained"]})

    for intent, amount in metrics["intents"].items():
        mission_key = {
            "Strike": "use_strike_intent",
            "Guard": "use_guard_intent",
            "Focus": "use_focus_intent",
        }.get(intent)
        if mission_key:
            append_update(mission_key, amount, {"intent": intent, "uses": amount})

    return updates


def record_retention_event(user, event_key, page="", metadata=None, commit=False):
    event_key = str(event_key or "").strip()[:120]

    if event_key not in ALLOWED_RETENTION_EVENTS:
        return None

    metadata = metadata if isinstance(metadata, dict) else {}

    try:
        event = RetentionEvent(
            user_id=getattr(user, "id", None),
            event_key=event_key,
            page=str(page or "")[:220],
            metadata_json=json.dumps(metadata, ensure_ascii=False)[:4000],
        )
        db.session.add(event)

        if commit:
            db.session.commit()

        return event
    except Exception as error:
        print("RETENTION EVENT RECORD ERROR:", type(error).__name__, error)
        if commit:
            db.session.rollback()
        return None


def normalize_gold_amount(amount, default=0, maximum=100000):
    try:
        value = int(amount)
    except (TypeError, ValueError):
        value = int(default)

    return max(0, min(int(maximum), value))


def get_guest_gold_balance():
    balance = session.get(GUEST_GOLD_SESSION_KEY)

    try:
        balance = int(balance)
    except (TypeError, ValueError):
        balance = GUEST_GOLD_STARTING_BALANCE

    balance = max(0, balance)
    session[GUEST_GOLD_SESSION_KEY] = balance
    return balance


def set_guest_gold_balance(balance):
    balance = max(0, int(balance or 0))
    session[GUEST_GOLD_SESSION_KEY] = balance
    return balance


def get_gold_balance(user=None):
    if user:
        return max(0, int(get_balance(user, GOLD_CURRENCY_KEY) or 0))

    return get_guest_gold_balance()


def gold_wallet_payload(user=None, message=None, ok=True):
    balance = get_gold_balance(user)
    recent = []

    if user:
        try:
            recent = (
                EconomyLedger.query
                .filter_by(user_id=user.id, currency=GOLD_CURRENCY_KEY)
                .order_by(EconomyLedger.id.desc())
                .limit(5)
                .all()
            )
        except Exception as error:
            print("GOLD WALLET RECENT ERROR:", type(error).__name__, error)
            recent = []

    return {
        "ok": bool(ok),
        "currency": GOLD_DISPLAY_NAME,
        "currency_key": GOLD_CURRENCY_KEY,
        "balance": balance,
        "is_guest": not bool(user),
        "message": message or f"{balance} {GOLD_DISPLAY_NAME} available.",
        "recent_rewards": [
            {
                "amount": int(entry.amount or 0),
                "source": entry.source,
                "reason": entry.reason or "",
                "balance_after": int(entry.balance_after or 0),
            }
            for entry in recent
        ],
    }


def wallet_mutation_allowed(user=None):
    return bool(
        app.config.get("TESTING")
        or app.config.get("DEV_TOOLS_ENABLED")
        or getattr(user, "is_admin", False)
    )


def wallet_rate_limited(action, limit=12, window_seconds=60):
    key = request_rate_limit_key(
        request,
        session,
        app.config.get("SECRET_KEY", ""),
        f"wallet:{action}",
        identity=str(getattr(current_user(), "id", None) or "guest"),
    )
    return not wallet_event_limiter.allow(key, limit, window_seconds)


def economy_rate_limited(action, limit=8, window_seconds=20):
    key = request_rate_limit_key(
        request,
        session,
        app.config.get("SECRET_KEY", ""),
        f"economy:{action}",
        identity=str(getattr(current_user(), "id", None) or "guest"),
    )
    return not economy_action_limiter.allow(key, limit, window_seconds)


def credit_gold(user, amount, source="system", reason=None, reference_type=None, reference_id=None, metadata=None, commit=False):
    amount = normalize_gold_amount(amount)

    if amount <= 0:
        return {
            "ok": False,
            "error": "invalid_amount",
            "message": "Gold amount must be positive.",
            "balance": get_gold_balance(user),
        }

    if user:
        ok, message = add_currency(
            user=user,
            currency=GOLD_CURRENCY_KEY,
            amount=amount,
            source=source,
            reason=reason or f"{GOLD_DISPLAY_NAME} credited.",
            reference_type=reference_type,
            reference_id=reference_id,
            metadata=metadata or {},
            commit=False,
        )

        if not ok:
            return {
                "ok": False,
                "error": "credit_failed",
                "message": message,
                "balance": get_gold_balance(user),
            }
    else:
        set_guest_gold_balance(get_guest_gold_balance() + amount)

    balance = get_gold_balance(user)
    record_retention_event(
        user,
        "currency_credit",
        page=str((metadata or {}).get("page") or getattr(request, "path", "")),
        metadata={
            "currency": GOLD_DISPLAY_NAME,
            "amount": amount,
            "source": source,
            "balance": balance,
            **(metadata or {}),
        },
    )

    if commit and user:
        db.session.commit()

    return {
        "ok": True,
        "amount": amount,
        "balance": balance,
        "currency": GOLD_DISPLAY_NAME,
        "message": f"+{amount} {GOLD_DISPLAY_NAME}",
    }


def debit_gold(user, amount, source="system", reason=None, reference_type=None, reference_id=None, metadata=None, commit=False):
    amount = normalize_gold_amount(amount)
    balance_before = get_gold_balance(user)

    if amount <= 0:
        return {
            "ok": False,
            "error": "invalid_amount",
            "message": "Gold amount must be positive.",
            "balance": balance_before,
        }

    if balance_before < amount:
        return {
            "ok": False,
            "error": "insufficient_gold",
            "message": "Not enough Gold.",
            "balance": balance_before,
        }

    if user:
        ok, message = spend_currency(
            user=user,
            currency=GOLD_CURRENCY_KEY,
            amount=amount,
            source=source,
            reason=reason or f"{GOLD_DISPLAY_NAME} spent.",
            reference_type=reference_type,
            reference_id=reference_id,
            metadata=metadata or {},
            commit=False,
        )

        if not ok:
            return {
                "ok": False,
                "error": "debit_failed",
                "message": message,
                "balance": get_gold_balance(user),
            }
    else:
        set_guest_gold_balance(balance_before - amount)

    balance = get_gold_balance(user)
    record_retention_event(
        user,
        "currency_debit",
        page=str((metadata or {}).get("page") or getattr(request, "path", "")),
        metadata={
            "currency": GOLD_DISPLAY_NAME,
            "amount": amount,
            "source": source,
            "balance": balance,
            **(metadata or {}),
        },
    )

    if commit and user:
        db.session.commit()

    return {
        "ok": True,
        "amount": amount,
        "balance": balance,
        "currency": GOLD_DISPLAY_NAME,
        "message": f"-{amount} {GOLD_DISPLAY_NAME}",
    }


@app.route("/api/wallet", methods=["GET"])
def api_wallet_balance():
    user = current_user()
    return jsonify(gold_wallet_payload(user))


@app.route("/api/wallet/credit", methods=["POST"])
def api_wallet_credit():
    user = current_user()

    if wallet_rate_limited("credit"):
        return jsonify({"ok": False, "error": "rate_limited", "message": "Too many wallet requests."}), 429

    if not wallet_mutation_allowed(user):
        return jsonify({"ok": False, "error": "forbidden", "message": "Wallet credit is disabled outside controlled beta tools."}), 403

    payload = request.get_json(silent=True) or request.form or {}
    result = credit_gold(
        user,
        payload.get("amount", 0),
        source="wallet_api_controlled",
        reason="Controlled beta wallet credit.",
        metadata={"page": "/api/wallet/credit", "controlled": True},
        commit=bool(user),
    )
    return jsonify(result), 200 if result.get("ok") else 400


@app.route("/api/wallet/debit", methods=["POST"])
def api_wallet_debit():
    user = current_user()

    if wallet_rate_limited("debit"):
        return jsonify({"ok": False, "error": "rate_limited", "message": "Too many wallet requests."}), 429

    if not wallet_mutation_allowed(user):
        return jsonify({"ok": False, "error": "forbidden", "message": "Wallet debit is disabled outside controlled beta tools."}), 403

    payload = request.get_json(silent=True) or request.form or {}
    result = debit_gold(
        user,
        payload.get("amount", 0),
        source="wallet_api_controlled",
        reason="Controlled beta wallet debit.",
        metadata={"page": "/api/wallet/debit", "controlled": True},
        commit=bool(user),
    )
    return jsonify(result), 200 if result.get("ok") else 400


def track_beta_mission(user, mission_key, amount=1, page="", metadata=None):
    if not user:
        return None

    try:
        update = increment_beta_mission(user, mission_key, amount)

        if update:
            retention_payload = dict(metadata or {})
            retention_payload.update({
                "mission_key": mission_key,
                "progress": update.get("progress"),
                "target": update.get("target"),
                "completed": update.get("completed"),
            })
            record_retention_event(user, "mission_progress", page=page, metadata=retention_payload)

            if update.get("just_completed"):
                record_retention_event(user, "mission_complete", page=page, metadata=retention_payload)

        return update
    except Exception as error:
        print("BETA MISSION TRACK ERROR:", type(error).__name__, error)
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
    deck_status = beta_deck_status(user)
    collection_progress = beta_collection_progress(user)
    wallet = gold_wallet_payload(user)
    return render_template(
        "index.html",
        user=user,
        wallet=wallet,
        beta_journey=build_beta_journey(user, deck_status),
        first_session_questline=build_first_session_questline(user, deck_status, wallet, collection_progress),
        deck_coach=build_deck_readiness_coach(user, deck_status=deck_status),
        beta_version="RC V8.1 Visual Architecture",
    )



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
            match_mode_label = str(getattr(match, "mode", "") or "").strip().lower()
            if match_mode_label == "campaign":
                mode_label = "Campaign"
            elif match_mode_label:
                mode_label = match_mode_label.title()
            else:
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
        "total_xp": int(getattr(user, "total_xp", 0) or 0),
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
    profile_mission_guides = []
    daily_checkin = build_daily_checkin(user, [])
    deck_status = beta_deck_status(user)
    collection_progress = beta_collection_progress(user)
    wallet = gold_wallet_payload(user)

    try:
        ensure_beta_missions(user)
        daily_missions = ensure_daily_missions(user)
        beta_missions = (
            UserMission.query
            .filter_by(user_id=user.id, mission_date="beta")
            .order_by(UserMission.id.desc())
            .all()
        )
        profile_mission_guides = build_beta_mission_guides(user, beta_missions, deck_status)[:4]
        daily_checkin = build_daily_checkin(user, daily_missions)
        db.session.commit()
    except Exception as error:
        print("PROFILE PRODUCT POLISH ERROR:", type(error).__name__, error)
        db.session.rollback()

    return render_template(
        "profile.html",
        user=user,
        profile_stats=profile_stats,
        identity=identity,
        cosmetics=cosmetics,
        recent_matches=recent_matches,
        profile_mission_guides=profile_mission_guides,
        daily_checkin=daily_checkin,
        wallet=wallet,
        first_session_questline=build_first_session_questline(user, deck_status, wallet, collection_progress),
        deck_coach=build_deck_readiness_coach(user, deck_status=deck_status),
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
        player_matches = int(player.wins or 0) + int(player.losses or 0)
        winrate = round((int(player.wins or 0) / player_matches) * 100, 1) if player_matches else 0
        row = {
            "rank": index,
            "user": player,
            "score": int(player.level or 1) * 10000 + int(player.xp or 0) * 10 + int(player.coins or 0),
            "is_current_user": bool(current and player.id == current.id),
            "record": f"{int(player.wins or 0)}W / {int(player.losses or 0)}L",
            "winrate": winrate,
            "matches": player_matches,
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
        criteria=[
            "Progression score uses level, XP and Gold during beta.",
            "Win/loss record appears when Training or PvP results are recorded.",
            "No real-money purchase or paid ranking advantage is active.",
        ],
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
    current = current_user()
    current_rank = None

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
            "is_current_user": bool(current and player.id == current.id),
        })

        if current and player.id == current.id:
            current_rank = index

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
        current_user=current,
        current_rank=current_rank,
        criteria=[
            "Wins are the first beta ordering signal.",
            "Level and XP break early ties.",
            "Tier labels are informational until ranked seasons ship.",
        ],
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
            "text": "Start with registration or login so your XP, Gold, missions and deck progress can be saved.",
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
            "text": "After the match, confirm XP, Gold, missions and profile progress updated correctly.",
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


@app.route("/roadmap")
def roadmap():
    user = current_user()
    roadmap_data = {
        "version": "RC V8.1 Visual Architecture",
        "status": "Ascension correction pass",
        "recent": [
            {
                "title": "Ascension Duel rebirth",
                "summary": "Training agora usa um Duel Altar com um Champion ativo, Ambition Core, Bound Souls, Schemes e Chronicle.",
            },
            {
                "title": "Visual architecture lock",
                "summary": "Home, Arena, Collection, Deck Builder, Chronicle, Tutorial e Roadmap compartilham o mesmo shell Ascension.",
            },
            {
                "title": "Compact viewport contract",
                "summary": "A Arena principal foi comprimida para manter Champion, Intent, hand e Commit no fluxo acima da dobra.",
            },
            {
                "title": "Public beta polish",
                "summary": "Copy pública reforça one-card duel architecture, Champion progression e beta sem pagamentos reais.",
            },
            {
                "title": "Reward beta",
                "summary": "XP, Gold, Champion progress e unlock progress continuam defensivos e ajustáveis durante a beta.",
            },
        ],
        "planned": [
            {
                "title": "Beta balancing pass",
                "summary": "Ajustes finos em cartas, dificuldade e pacing usando simulações e feedback real.",
            },
            {
                "title": "Campaign expansion",
                "summary": "Mais capítulos simples, recompensas defensivas e contexto narrativo original.",
            },
            {
                "title": "Collection depth",
                "summary": "Melhor leitura de progresso, desbloqueios recentes e metas de deck por role estratégico.",
            },
        ],
        "rc_checklist": [
            {"item": "Ascension Duel", "status": "Ready", "note": "Duel Altar, Ambition Core, Chronicle e compact viewport ativos."},
            {"item": "Training", "status": "Ready", "note": "Modo principal para beta pública e first session."},
            {"item": "Collection", "status": "Ready", "note": "Champion, Technique, Relic, Scheme e Ascension visíveis."},
            {"item": "Deck Builder", "status": "Ready", "note": "Ascension Deck mantém a regra beta de 30 cartas legível."},
            {"item": "Missions", "status": "Ready", "note": "Objetivos persistentes e rewards beta."},
            {"item": "Daily", "status": "Ready", "note": "Streak simples, XP e Gold sem farm por refresh."},
            {"item": "Gold", "status": "Ready", "note": "Moeda interna beta, sem pagamento real."},
            {"item": "Shop beta", "status": "Ready", "note": "Boosters com Gold e supporter pack bloqueado."},
            {"item": "Booster", "status": "Ready", "note": "Opening V1 com histórico e collection update quando possível."},
            {"item": "Profile/Progression", "status": "Ready", "note": "Hub de XP, Gold, daily, missions e próximos passos."},
            {"item": "Feedback", "status": "Ready", "note": "Formulário público defensivo para testers."},
            {"item": "PWA", "status": "Ready", "note": "Manifest e service worker versionados."},
            {"item": "QA status", "status": "Required per RC", "note": "Rodar suíte completa antes de commit/deploy."},
        ],
    }

    if user:
        record_retention_event(user, "roadmap_view", page="/roadmap", metadata={"version": roadmap_data["version"]}, commit=True)

    return render_template("roadmap.html", user=user, roadmap=roadmap_data)


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
    owned_faction_counts = Counter(str(card.get("faction") or "") for card in owned_cards)
    catalog_faction_counts = Counter(str(card.get("faction") or "") for card in cards)
    owned_role_counts = Counter(str(card.get("role") or "Card") for card in owned_cards)
    catalog_role_counts = Counter(str(card.get("role") or "Card") for card in cards)
    element_names = [name for name in element_order if catalog_element_counts.get(name, 0)]
    element_names.extend(sorted(name for name in catalog_element_counts if name not in element_names))
    rarity_names = [name for name in rarity_order if catalog_rarity_counts.get(name, 0)]
    rarity_names.extend(sorted(name for name in catalog_rarity_counts if name not in rarity_names))
    faction_names = sorted(name for name in catalog_faction_counts if name)
    role_names = sorted(name for name in catalog_role_counts if name)
    recent_unlocks = [
        str(card_id)
        for card_id in (session.pop("recent_unlocked_cards", []) or [])
        if str(card_id or "").strip()
    ]
    collection_stats = {
        "unique_cards": unique_owned,
        "total_cards": sum(int(card.get("count") or 0) for card in owned_cards),
        "catalog_cards": catalog_total,
        "locked_cards": max(0, catalog_total - unique_owned),
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
        "faction_counts": [
            {
                "name": name,
                "owned": int(owned_faction_counts.get(name, 0)),
                "total": int(catalog_faction_counts.get(name, 0)),
            }
            for name in faction_names
        ],
        "role_counts": [
            {
                "name": name,
                "owned": int(owned_role_counts.get(name, 0)),
                "total": int(catalog_role_counts.get(name, 0)),
            }
            for name in role_names
        ],
    }

    try:
        track_beta_mission(user, "view_collection", page="/collection", metadata={"unique_owned": unique_owned})
        record_retention_event(user, "collection_view", page="/collection", metadata={"unique_owned": unique_owned})
        db.session.commit()
    except Exception as error:
        print("COLLECTION BETA TRACK ERROR:", type(error).__name__, error)
        db.session.rollback()

    return render_template(
        "collection.html",
        user=user,
        cards=cards,
        inventory_counts=inventory_counts,
        collection_stats=collection_stats,
        recent_unlocks=recent_unlocks,
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


def booster_pull_from_pack(pack, rng=None):
    import random

    from game.cards import CARD_CATALOG

    rng = rng or random
    cards = list(CARD_CATALOG)

    if not cards:
        raise ValueError("Card catalog is empty.")

    rarity_roll = rng.randint(1, 100)
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

    card = dict(rng.choice(pool))

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


def shop_offer_catalog():
    pack = get_booster_pack("elemental")

    return [
        {
            "key": "basic_booster",
            "title": "Basic Booster Pack",
            "kind": "booster",
            "pack_key": pack["key"],
            "cost": int(pack.get("cost", 300)),
            "cards": int(pack.get("size", 5)),
            "description": "Open 5 beta catalog cards using Gold earned in play.",
            "reward_preview": "5 cards from the current beta catalog",
            "cta": "Buy Booster",
        },
        {
            "key": "daily_deal",
            "title": "Daily Deal",
            "kind": "daily_deal",
            "pack_key": pack["key"],
            "cost": 120,
            "cards": 2,
            "description": "A once-per-day small pull for returning beta players.",
            "reward_preview": "2 bonus cards today",
            "cta": "Claim Deal",
        },
        {
            "key": "founder_supporter",
            "title": "Founder / Supporter Pack",
            "kind": "coming_soon",
            "pack_key": None,
            "cost": None,
            "cards": 0,
            "description": "A future supporter bundle. No real-money checkout is active in this beta.",
            "reward_preview": "Coming soon",
            "cta": "Coming Soon",
            "locked": True,
        },
    ]


def daily_deal_claimed(user):
    if not user:
        return False

    return bool(
        EconomyLedger.query
        .filter_by(
            user_id=user.id,
            source="shop_daily_deal",
            reference_type="daily_deal",
            reference_id=today_key(),
        )
        .first()
    )


def build_shop_purchase_token():
    token = secrets.token_urlsafe(24)
    session["shop_purchase_token"] = token
    return token


def consume_shop_purchase_token(token):
    expected = session.pop("shop_purchase_token", "")
    return bool(expected and token and hmac.compare_digest(str(expected), str(token)))


def build_shop_offers(user, wallet=None):
    wallet = wallet or gold_wallet_payload(user)
    balance = int(wallet.get("balance", 0) or 0)
    offers = []

    for offer in shop_offer_catalog():
        item = dict(offer)
        cost = item.get("cost")
        locked = bool(item.get("locked"))
        claimed = item["key"] == "daily_deal" and daily_deal_claimed(user)

        if locked:
            status = "coming_soon"
            status_label = "Coming soon"
            disabled = True
            message = "No real-money checkout is active in this beta."
        elif claimed:
            status = "claimed"
            status_label = "Claimed today"
            disabled = True
            message = "This Daily Deal refreshes tomorrow."
        elif balance < int(cost or 0):
            status = "insufficient"
            status_label = "Need more Gold"
            disabled = True
            message = f"Earn {int(cost or 0) - balance} more Gold through Daily, Missions or Training."
        else:
            status = "available"
            status_label = "Available"
            disabled = False
            message = "Spend earned Gold. This is beta currency, not real money."

        item.update({
            "status": status,
            "status_label": status_label,
            "disabled": disabled,
            "message": message,
            "cost_label": f"{cost} Gold" if cost is not None else "No checkout",
        })
        offers.append(item)

    return offers


def open_booster_for_user(user, pack_key="elemental", size_override=None, seed=None, source="booster_open", cost=0, metadata=None):
    if not user:
        return {"ok": False, "error": "login_required", "message": "Login required to open boosters."}

    import random

    selected_pack = get_booster_pack(pack_key)
    booster_size = max(1, min(10, int(size_override or selected_pack.get("size", 5) or 5)))
    seed_material = seed if seed is not None else f"{user.id}:{selected_pack['key']}:{datetime.utcnow().isoformat()}:{source}"
    rng = random.Random(str(seed_material))
    pulled_cards = []
    collection_ids = owned_card_ids_for_user(user)

    for _ in range(booster_size):
        card = booster_pull_from_pack(selected_pack, rng=rng)
        pulled_cards.append(card)
        collection_ids.append(card["id"])

    user.collection_json = json.dumps(collection_ids)

    common_count = len([card for card in pulled_cards if card.get("rarity") == "Common"])
    uncommon_count = len([card for card in pulled_cards if card.get("rarity") == "Uncommon"])

    history_payload = [
        {
            **card,
            "pack_key": selected_pack["key"],
            "pack_name": selected_pack["name"],
        }
        for card in pulled_cards
    ]

    history = BoosterHistory(
        user_id=user.id,
        username=user.username,
        cost=int(cost or 0),
        cards_json=json.dumps(history_payload),
        common_count=common_count,
        uncommon_count=uncommon_count,
    )

    db.session.add(history)
    db.session.flush()

    for index, card in enumerate(pulled_cards):
        grant_card(
            user=user,
            card_id=card["id"],
            quantity=1,
            source=source,
            idempotency_key=f"booster-{history.id}-{index}-{card['id']}",
            metadata={
                "pack_key": selected_pack["key"],
                "pack_name": selected_pack["name"],
                "card_name": card.get("name"),
                "rarity": card.get("rarity"),
                "element": card.get("element"),
                **(metadata or {}),
            },
        )

    increment_mission(user, "open_1_booster", 1)
    record_retention_event(
        user,
        "booster_opened",
        page="/shop",
        metadata={
            "pack_key": selected_pack["key"],
            "size": booster_size,
            "history_id": history.id,
            "source": source,
            **(metadata or {}),
        },
    )

    return {
        "ok": True,
        "pack": selected_pack,
        "cards": pulled_cards,
        "history_id": history.id,
        "count": booster_size,
        "common_count": common_count,
        "uncommon_count": uncommon_count,
    }


def purchase_shop_offer(user, offer_key, seed=None):
    if not user:
        return {"ok": False, "error": "login_required", "message": "Login required to use the beta shop."}

    offer_key = str(offer_key or "").strip()
    offer = next((item for item in shop_offer_catalog() if item["key"] == offer_key), None)

    if not offer:
        return {"ok": False, "error": "unknown_offer", "message": "Shop offer not found.", "balance": get_gold_balance(user)}

    if offer.get("locked"):
        return {
            "ok": False,
            "error": "locked_offer",
            "message": "That offer is coming soon. No real-money checkout is active.",
            "balance": get_gold_balance(user),
        }

    if offer_key == "daily_deal" and daily_deal_claimed(user):
        return {
            "ok": False,
            "error": "already_claimed",
            "message": "Daily Deal already claimed today.",
            "balance": get_gold_balance(user),
        }

    cost = int(offer.get("cost") or 0)
    source = "shop_daily_deal" if offer_key == "daily_deal" else "shop_purchase"
    reference_type = "daily_deal" if offer_key == "daily_deal" else "shop_offer"
    reference_id = today_key() if offer_key == "daily_deal" else offer_key
    metadata = {"page": "/shop", "offer_key": offer_key, "pack_key": offer.get("pack_key")}

    debit_result = debit_gold(
        user,
        cost,
        source=source,
        reason=f"Purchased {offer['title']} with beta Gold.",
        reference_type=reference_type,
        reference_id=reference_id,
        metadata=metadata,
    )

    if not debit_result.get("ok"):
        return debit_result

    open_result = open_booster_for_user(
        user,
        pack_key=offer.get("pack_key") or "elemental",
        size_override=offer.get("cards") or None,
        seed=seed,
        source=source,
        cost=cost,
        metadata=metadata,
    )

    if not open_result.get("ok"):
        db.session.rollback()
        return open_result

    balance = get_gold_balance(user)
    record_retention_event(
        user,
        "shop_purchase",
        page="/shop",
        metadata={
            "offer_key": offer_key,
            "cost": cost,
            "balance": balance,
            "history_id": open_result.get("history_id"),
        },
    )
    db.session.commit()

    return {
        "ok": True,
        "message": f"{offer['title']} opened.",
        "offer": offer,
        "spent": cost,
        "balance": balance,
        **open_result,
    }


@app.route("/shop", methods=["GET", "POST"])
def shop():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    if request.method == "POST":
        return shop_purchase()

    wallet = gold_wallet_payload(user)
    last_opening = session.pop("last_booster_opening", None)
    pulled_cards = (last_opening or {}).get("cards") or []
    selected_pack = get_booster_pack("elemental")

    return render_template(
        "shop.html",
        user=user,
        pulled_cards=pulled_cards,
        booster_cost=selected_pack.get("cost", 300),
        booster_size=selected_pack.get("size", 5),
        can_afford_booster=int(wallet.get("balance", 0) or 0) >= int(selected_pack.get("cost", 300)),
        booster_packs=list(BOOSTER_PACKS.values()),
        selected_pack=selected_pack,
        wallet=wallet,
        shop_offers=build_shop_offers(user, wallet),
        purchase_token=build_shop_purchase_token(),
        last_opening=last_opening,
    )


@app.route("/shop/purchase", methods=["POST"])
def shop_purchase():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    is_json = request.is_json
    payload = request.get_json(silent=True) or request.form or {}

    if economy_rate_limited("shop_purchase"):
        response = {"ok": False, "error": "rate_limited", "message": "Too many shop actions. Try again shortly.", "balance": get_gold_balance(user)}
        return (jsonify(response), 429) if is_json else (flash(response["message"]) or redirect(url_for("shop")))

    if not is_json and not consume_shop_purchase_token(payload.get("purchase_token")):
        flash("Shop request expired. Please try again.")
        return redirect(url_for("shop"))

    try:
        result = purchase_shop_offer(user, payload.get("offer_key"), seed=payload.get("seed"))

        if result.get("ok"):
            cards = result.get("cards") or []
            session["last_booster_opening"] = {
                "cards": cards,
                "offer": result.get("offer") or {},
                "spent": result.get("spent", 0),
                "balance": result.get("balance", 0),
                "history_id": result.get("history_id"),
            }
            session["recent_unlocked_cards"] = [str(card.get("id")) for card in cards if card.get("id")]
            flash(f"{result.get('message', 'Offer opened')} - {len(cards)} cards added to your Collection.")
            return jsonify(result) if is_json else redirect(url_for("shop"))

        status = 400 if result.get("error") != "insufficient_gold" else 402
        if is_json:
            return jsonify(result), status

        flash(result.get("message") or "Shop purchase failed.")
        return redirect(url_for("shop"))
    except Exception as error:
        print("SHOP PURCHASE ERROR:", type(error).__name__, error)
        db.session.rollback()
        result = {"ok": False, "error": "purchase_failed", "message": "Shop purchase failed safely. No Gold was spent.", "balance": get_gold_balance(user)}
        return (jsonify(result), 500) if is_json else (flash(result["message"]) or redirect(url_for("shop")))


@app.route("/api/booster/open", methods=["POST"])
def api_booster_open():
    user = current_user()

    if not user:
        return jsonify({"ok": False, "error": "login_required", "message": "Login required to open boosters."}), 401

    if economy_rate_limited("booster_open"):
        return jsonify({"ok": False, "error": "rate_limited", "message": "Too many booster actions. Try again shortly.", "balance": get_gold_balance(user)}), 429

    payload = request.get_json(silent=True) or {}
    result = purchase_shop_offer(user, payload.get("offer_key") or "basic_booster", seed=payload.get("seed"))

    if result.get("ok"):
        session["recent_unlocked_cards"] = [str(card.get("id")) for card in result.get("cards") or [] if card.get("id")]
        return jsonify(result)

    status = 402 if result.get("error") == "insufficient_gold" else 400
    return jsonify(result), status






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
        record_retention_event(
            user,
            "deck_save_attempt",
            page="/deck-builder",
            metadata={"cards": len(selected_cards), "valid": not bool(errors)},
        )

        if errors:
            for error in errors:
                flash(error)
            db.session.commit()
        else:
            user.deck_json = json.dumps(selected_cards)
            track_beta_mission(user, "save_or_validate_deck", page="/deck-builder", metadata={"cards": len(selected_cards)})
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
    deck_analysis = deck_analysis_v115(deck_ids)
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

    try:
        record_retention_event(user, "deck_builder_view", page="/deck-builder", metadata={"deck_valid": deck_status["is_valid"]})
        if deck_status["is_valid"]:
            track_beta_mission(user, "save_or_validate_deck", page="/deck-builder", metadata={"validated": True})
        db.session.commit()
    except Exception as error:
        print("DECK BUILDER BETA TRACK ERROR:", type(error).__name__, error)
        db.session.rollback()

    return render_template(
        "deck_builder.html",
        user=user,
        collection_cards=collection_cards,
        current_deck=current_deck,
        deck_ids=deck_ids,
        collection_ids=collection_ids,
        deck_validation_errors=deck_validation_errors,
        deck_analysis=deck_analysis,
        deck_status=deck_status,
        deck_coach=build_deck_readiness_coach(
            user,
            deck_ids=deck_ids,
            collection_ids=collection_ids,
            deck_status=deck_status,
            deck_analysis=deck_analysis,
        ),
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

    if match.get("_end_match_recorded"):
        return

    match["_end_match_recorded"] = True

    p1 = match["p1"]
    p2 = match["p2"]

    battle_logs = match.get("logs", [])
    campaign_context = match.get("campaign") or {}
    campaign_chapter_id = str(match.get("campaign_chapter_id") or campaign_context.get("chapter_id") or "").strip()[:80]
    is_bot_match = bool(match.get("is_bot_match") or match.get("training"))
    is_campaign_match = bool(campaign_chapter_id)
    reward_difficulty = str(campaign_context.get("difficulty") or match.get("bot_difficulty") or "normal").lower()
    match_mode = (
        "campaign"
        if is_campaign_match
        else "fallback_bot"
        if match.get("matchmaking_fallback")
        else "training"
        if is_bot_match
        else "pvp"
    )
    post_match_extras = {}
    mission_updates = {}

    if is_campaign_match:
        is_bot_match = True

    def apply_rewards_for(user, player_key, result_label, did_win):
        rewards = {"coins": 0, "xp": 0}

        if not user:
            return rewards

        rewards = apply_match_rewards(
            user,
            is_bot_match=is_bot_match,
            did_win=did_win,
            award_xp_function=award_xp,
            difficulty=reward_difficulty,
            result="draw" if result_label == "DRAW" else None,
            source="campaign_match" if is_campaign_match else "training_match" if is_bot_match else "match_reward",
            metadata={
                "room_id": room_id,
                "result": result_label,
                "mode": match_mode,
                "campaign_chapter_id": campaign_chapter_id or None,
            },
            reward_key=f"match:{room_id}:{player_key}:{user.id}:{result_label}",
        )

        if is_campaign_match:
            campaign_bonus = {"easy": 20, "normal": 30, "hard": 45}.get(reward_difficulty, 30)
            bonus_result = award_xp(
                user,
                campaign_bonus,
                source="campaign_chapter",
                metadata={
                    "room_id": room_id,
                    "chapter_id": campaign_chapter_id,
                    "result": result_label,
                },
                reward_key=f"campaign:{room_id}:{player_key}:{user.id}:{campaign_chapter_id}",
            )
            rewards["campaign_bonus_xp"] = int(bonus_result.get("xp", 0) or 0)
            rewards["xp"] = int(rewards.get("xp", 0) or 0) + int(bonus_result.get("xp", 0) or 0)
            rewards["campaign_xp_result"] = bonus_result

        record_retention_event(
            user,
            "xp_awarded",
            page="/arena",
            metadata={
                "source": "match",
                "mode": match_mode,
                "xp": int(rewards.get("xp", 0) or 0),
                "campaign_chapter_id": campaign_chapter_id or None,
            },
        )

        gold_awarded = int(rewards.get("coins", 0) or 0)

        if gold_awarded > 0:
            record_ledger(
                user=user,
                currency=GOLD_CURRENCY_KEY,
                amount=gold_awarded,
                source="match_reward",
                reason="Post-match Gold reward.",
                reference_type="match",
                reference_id=room_id,
                metadata={
                    "room_id": room_id,
                    "result": result_label,
                    "mode": match_mode,
                    "campaign_chapter_id": campaign_chapter_id or None,
                },
            )
            record_retention_event(
                user,
                "currency_credit",
                page="/arena",
                metadata={
                    "currency": GOLD_DISPLAY_NAME,
                    "amount": gold_awarded,
                    "source": "match_reward",
                    "mode": match_mode,
                    "balance": get_gold_balance(user),
                },
            )

        return rewards

    def track_after_match(user, player_key, result_label):
        if not user:
            return

        updates = []

        if is_bot_match:
            user.first_training_completed = True
            increment_mission(user, "play_1_training", 1)
            updates.append(track_beta_mission(
                user,
                "play_training_match",
                page="/arena",
                metadata={"room_id": room_id, "result": result_label, "mode": match_mode},
            ))

            if result_label == "WIN":
                increment_mission(user, "win_1_training", 1)

        if is_campaign_match:
            updates.append(track_beta_mission(
                user,
                "play_campaign_chapter",
                page="/campaign",
                metadata={"room_id": room_id, "chapter_id": campaign_chapter_id, "result": result_label},
            ))
            record_retention_event(
                user,
                "campaign_result",
                page="/campaign",
                metadata={
                    "room_id": room_id,
                    "chapter_id": campaign_chapter_id,
                    "result": result_label,
                },
            )

        updates.extend(track_match_mission_v2(user, room_id, match_mode, result_label, player_key, match))
        mission_updates[player_key] = [update for update in updates if update]

    if winner_key == "DRAW":
        socketio.emit("game_over", {"result": "DRAW"}, to=p1["sid"])

        if not p2.get("is_bot"):
            socketio.emit("game_over", {"result": "DRAW"}, to=p2["sid"])

        winner_id = None
        winner_name = None
        result = history_result_for_ending(winner_key, ending_reason)

        p1_user = db.session.get(User, safe_user_id(p1)) if safe_user_id(p1) else None
        p2_user = db.session.get(User, safe_user_id(p2)) if safe_user_id(p2) else None

        if p1_user:
            increment_mission(p1_user, "play_1_match", 1)
            increment_mission(p1_user, "play_3_matches", 1)

        if p2_user:
            increment_mission(p2_user, "play_1_match", 1)
            increment_mission(p2_user, "play_3_matches", 1)

        p1_rewards = apply_rewards_for(p1_user, "p1", "DRAW", False)
        p2_rewards = apply_rewards_for(p2_user, "p2", "DRAW", False)
        track_after_match(p1_user, "p1", "DRAW")
        track_after_match(p2_user, "p2", "DRAW")

        result_by_key = {"p1": "DRAW", "p2": "DRAW"}
        rewards_by_key = {"p1": p1_rewards, "p2": p2_rewards}

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
            winner_rewards = apply_rewards_for(winner_user, winner_key, "WIN", True)

            increment_mission(winner_user, "play_1_match", 1)
            increment_mission(winner_user, "play_3_matches", 1)
            increment_mission(winner_user, "win_1_match", 1)
            track_after_match(winner_user, winner_key, "WIN")

        if loser_user:
            loser_user.losses += 1
            loser_rewards = apply_rewards_for(loser_user, loser_key, "LOSE", False)

            increment_mission(loser_user, "play_1_match", 1)
            increment_mission(loser_user, "play_3_matches", 1)
            track_after_match(loser_user, loser_key, "LOSE")

        result_by_key = {winner_key: "WIN", loser_key: "LOSE"}
        rewards_by_key = {winner_key: winner_rewards, loser_key: loser_rewards}

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
        mode=match_mode,
        xp_gained=int((rewards_by_key.get("p1") or {}).get("xp", 0) or 0),
        reward_summary=json.dumps({
            "p1": rewards_by_key.get("p1") or {},
            "p2": rewards_by_key.get("p2") or {},
        }, ensure_ascii=False),
        campaign_chapter_id=campaign_chapter_id or None,
        campaign_result=result_by_key.get("p1") if is_campaign_match else None,
        battle_log_json=json.dumps(battle_logs),
    )

    db.session.add(history)
    db.session.flush()

    for player_key, rewards in rewards_by_key.items():
        user_id = safe_user_id(match.get(player_key) or {})
        viewer_user = db.session.get(User, user_id) if user_id else None
        xp_result = (rewards or {}).get("xp_result") or (rewards or {}).get("campaign_xp_result") or {}
        mission_progress = mission_updates.get(player_key, [])
        next_best_action = build_post_match_next_best_action(
            viewer_user,
            rewards or {},
            mission_progress,
            beta_deck_status(viewer_user) if viewer_user else None,
        )
        post_match_extras[player_key] = {
            "history_id": history.id,
            "history_url": url_for("match_history_detail", history_id=history.id),
            "xp_gained": int((rewards or {}).get("xp", 0) or 0),
            "gold_gained": int((rewards or {}).get("coins", 0) or 0),
            "gold_balance": get_gold_balance(viewer_user) if viewer_user else 0,
            "level": int(getattr(viewer_user, "level", 1) or 1) if viewer_user else 1,
            "level_progress_percent": getattr(viewer_user, "level_progress_percent", 0) if viewer_user else 0,
            "next_level_xp": getattr(viewer_user, "next_level_xp", 100) if viewer_user else 100,
            "mission_progress": mission_progress,
            "campaign_chapter_id": campaign_chapter_id or None,
            "campaign_result": result_by_key.get(player_key),
            "campaign_reward_preview": campaign_context.get("reward") if is_campaign_match else None,
            "xp_result": xp_result,
            "next_best_action": next_best_action,
            "next_actions": {
                "primary": next_best_action.get("url"),
                "play_again": url_for("training"),
                "campaign": url_for("campaign"),
                "deck": url_for("deck_builder"),
                "collection": url_for("collection"),
                "history": url_for("match_history_detail", history_id=history.id),
                "missions": url_for("missions"),
                "shop": url_for("shop"),
                "progression": url_for("progression") if viewer_user else url_for("login"),
                "menu": url_for("index"),
            },
        }

        if viewer_user:
            record_retention_event(
                viewer_user,
                "match_recorded",
                page="/arena",
                metadata={
                    "match_history_id": history.id,
                    "mode": match_mode,
                    "result": result_by_key.get(player_key),
                    "campaign_chapter_id": campaign_chapter_id or None,
                },
            )

    match["post_match_extras_by_key"] = post_match_extras

    emit_v107_post_match_summary(match, "p1", result_by_key.get("p1", "DRAW"), rewards_by_key.get("p1") or {"coins": 0, "xp": 0})

    if not p2.get("is_bot"):
        emit_v107_post_match_summary(match, "p2", result_by_key.get("p2", "DRAW"), rewards_by_key.get("p2") or {"coins": 0, "xp": 0})

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
            "mode": match_mode,
            "campaign_chapter_id": campaign_chapter_id or None,
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
            "title": "Champion",
            "subtitle": "One active Champion anchors your side.",
            "description": "You win by reading the rival, protecting your Champion pressure and choosing when to replace, bind or burn.",
            "objective": "Know the goal before entering Training.",
            "rule": "One active Champion per side.",
            "cta_label": "Start Training",
            "cta_url": url_for("training"),
        },
        {
            "number": "02",
            "title": "Choose Intent",
            "subtitle": "Strike, Guard, Focus or Scheme defines the Round.",
            "description": "Strike pressures, Guard contains, Focus builds Ambition and Scheme punishes predictable patterns.",
            "objective": "Understand the intent triangle.",
            "rule": "Intent first. Commit second.",
            "cta_label": "Practice Intent",
            "cta_url": url_for("training"),
        },
        {
            "number": "03",
            "title": "One-card Play",
            "subtitle": "Each card has a purpose.",
            "description": "Summon a Champion, bind a Soul, burn for Ambition, equip a Relic, set a Scheme or push an Ascension.",
            "objective": "Learn hand and card timing.",
            "rule": "One card per round.",
            "cta_label": "View Deck",
            "cta_url": url_for("deck_builder_ascension"),
        },
        {
            "number": "04",
            "title": "Ambition Core",
            "subtitle": "Ambition is your rule-breaking resource.",
            "description": "Focus, burn decisions and pressure recovery fill the Core for Overrule, Ascension and Domination.",
            "objective": "Read when to spend or hold.",
            "rule": "Ambition creates decisive turns.",
            "cta_label": "See Collection",
            "cta_url": url_for("collection_ascension"),
        },
        {
            "number": "05",
            "title": "Commit and Resolve",
            "subtitle": "Commit locks your choice and reveals the result.",
            "description": "When the Round resolves, the server updates HP, Ambition, Echo, Champion state and the Chronicle.",
            "objective": "Trust the server as the source of truth.",
            "rule": "Commit resolves. Ambition grows.",
            "cta_label": "Start Training",
            "cta_url": url_for("training"),
        },
        {
            "number": "06",
            "title": "Reward",
            "subtitle": "Every finished duel feeds progression.",
            "description": "XP, Gold, Champion progress and unlock progress appear after the duel resolves.",
            "objective": "Know why the next match matters.",
            "rule": "Rewards are beta only.",
            "cta_label": "Read Chronicle",
            "cta_url": url_for("ascension_history"),
        },
    ]

    user = current_user()

    return render_template(
        "tutorial.html",
        user=user,
        steps=steps,
        beta_journey=build_beta_journey(user, beta_deck_status(user)),
    )


@app.route("/campaign")
def campaign():
    user = current_user()
    deck_status = beta_deck_status(user)
    chapters = build_campaign_chapters(user, deck_status)

    if user:
        record_retention_event(user, "campaign_view", page="/campaign", metadata={"chapters": len(chapters)}, commit=True)

    return render_template(
        "campaign.html",
        user=user,
        chapters=chapters,
        beta_journey=build_beta_journey(user, deck_status),
    )


@app.route("/campaign/start/<chapter_id>")
def campaign_start(chapter_id):
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    deck_status = beta_deck_status(user)
    chapter = get_campaign_chapter(chapter_id, user, deck_status)

    if not chapter:
        flash("Campaign chapter not found.")
        return redirect(url_for("campaign"))

    if chapter.get("locked"):
        flash("Complete the previous beta chapter before starting this one.")
        return redirect(url_for("campaign"))

    if chapter.get("requires_deck_check"):
        flash("Check your 30-card beta deck before this chapter.")
        return redirect(url_for("deck_builder"))

    session["campaign_chapter_id"] = chapter["chapter_id"]
    session["campaign_chapter_title"] = chapter["title"]
    session["campaign_chapter_difficulty"] = chapter["difficulty"]
    session["campaign_chapter_reward"] = chapter["reward"]

    record_retention_event(
        user,
        "campaign_start",
        page="/campaign",
        metadata={
            "chapter_id": chapter["chapter_id"],
            "difficulty": chapter["difficulty"],
        },
        commit=True,
    )

    return redirect(url_for("training", campaign_chapter_id=chapter["chapter_id"]))


def _build_training_campaign_context(user):
    campaign_context = None
    chapter_id = str(request.args.get("campaign_chapter_id") or "").strip()

    if chapter_id and user:
        chapter = get_campaign_chapter(chapter_id, user, beta_deck_status(user))
        if chapter and not chapter.get("locked") and not chapter.get("requires_deck_check"):
            session["campaign_chapter_id"] = chapter["chapter_id"]
            session["campaign_chapter_title"] = chapter["title"]
            session["campaign_chapter_difficulty"] = chapter["difficulty"]
            session["campaign_chapter_reward"] = chapter["reward"]
            campaign_context = {
                "chapter_id": chapter["chapter_id"],
                "title": chapter["title"],
                "difficulty": chapter["difficulty"],
                "reward": chapter["reward"],
            }
        else:
            session.pop("campaign_chapter_id", None)
            session.pop("campaign_chapter_title", None)
            session.pop("campaign_chapter_difficulty", None)
            session.pop("campaign_chapter_reward", None)
    elif not chapter_id:
        session.pop("campaign_chapter_id", None)
        session.pop("campaign_chapter_title", None)
        session.pop("campaign_chapter_difficulty", None)
        session.pop("campaign_chapter_reward", None)

    return campaign_context


def _ascension_owned_card_ids(user=None):
    deck = build_ascension_starter_deck(seed=f"owned:{getattr(user, 'id', 'guest')}")
    return {card["id"] for card in deck}


def _ascension_new_card_ids():
    recent = session.get("ascension_recent_unlocks") or []
    return {str(card_id) for card_id in recent}


@app.route("/collection-ascension")
def collection_ascension():
    user = current_user()
    owned_ids = _ascension_owned_card_ids(user)
    new_ids = _ascension_new_card_ids()
    cards = [enrich_ascension_card(card, owned_ids=owned_ids, new_ids=new_ids) for card in get_ascension_catalog()]
    type_counts = Counter(card["type_key"] for card in cards)

    return render_template(
        "collection_ascension.html",
        user=user,
        cards=cards,
        type_counts=type_counts,
    )


@app.route("/deck-builder-ascension")
def deck_builder_ascension():
    user = current_user()
    deck = build_ascension_starter_deck(seed=f"builder:{getattr(user, 'id', 'guest')}")
    summary = ascension_deck_summary(deck)
    validation = validate_ascension_deck(deck)
    cards = [enrich_ascension_card(card) for card in deck]

    return render_template(
        "deck_builder_ascension.html",
        user=user,
        cards=cards,
        summary=summary,
        validation=validation,
    )


@app.route("/training")
def training():
    user = current_user()
    campaign_context = _build_training_campaign_context(user)

    return render_template(
        "arena_ascension.html",
        user=user,
        training_mode=True,
        campaign_context=campaign_context,
    )


@app.route("/training-legacy")
def training_legacy():
    user = current_user()
    arena_renderer = "3d" if request.args.get("renderer") == "3d" else "dom"
    campaign_context = _build_training_campaign_context(user)

    return render_template(
        "arena.html",
        user=user,
        training_mode=True,
        arena_renderer=arena_renderer,
        campaign_context=campaign_context,
    )


def _ascension_request_payload():
    try:
        return request.get_json(silent=True) or {}
    except Exception:
        return {}


def _store_ascension_match(match):
    ascension_training_matches[match["id"]] = match
    session["ascension_match_id"] = match["id"]
    return match


def _get_ascension_match(create_if_missing=True):
    match_id = session.get("ascension_match_id")
    match = ascension_training_matches.get(match_id) if match_id else None
    if match or not create_if_missing:
        return match

    seed = session.get("ascension_seed") or secrets.token_hex(6)
    session["ascension_seed"] = seed
    return _store_ascension_match(create_ascension_match(seed=seed))


def _ascension_json(match, ok=True, error=None, status=200, extra=None):
    payload = ascension_action_response(match, ok=ok, error=error)
    if extra:
        payload.update(extra)
    return jsonify(payload), status


def _ascension_error(match, error, status=400):
    if isinstance(error, AscensionActionError):
        return _ascension_json(match, ok=False, error=error.to_dict(), status=status)
    return _ascension_json(
        match,
        ok=False,
        error={"code": "ascension_error", "message": str(error)},
        status=status,
    )


def _record_finished_ascension_match(match):
    if not match or not match.get("winner"):
        return None

    session_key = f"ascension_result_recorded:{match['id']}"
    if session.get(session_key):
        return match.get("ascension_progression_event")

    rewards = build_ascension_rewards(match, perspective="player")
    match["ascension_reward"] = rewards
    event = progression_event_from_match(match, perspective="player")
    match["ascension_progression_event"] = event

    try:
        record = build_history_record(match, reward=rewards, perspective="player")
        append_history_record(app.instance_path, record)
    except Exception as error:
        print("ASCENSION HISTORY ERROR:", type(error).__name__, error)

    if rewards.get("unlock"):
        session["ascension_recent_unlocks"] = [rewards["unlock"]["id"]]

    record_retention_event(
        current_user(),
        event["event_key"],
        page=event["page"],
        metadata=event["metadata"],
        commit=True,
    )
    session[session_key] = True
    return event


@app.route("/api/ascension/start", methods=["POST"])
def api_ascension_start():
    payload = _ascension_request_payload()
    seed = payload.get("seed") or secrets.token_hex(6)
    bot_profile = payload.get("bot_profile") or payload.get("profile") or "Controller"
    session["ascension_seed"] = seed
    match = _store_ascension_match(create_ascension_match(seed=seed, bot_profile=bot_profile))
    return _ascension_json(match)


@app.route("/api/ascension/state", methods=["GET"])
def api_ascension_state():
    match = _get_ascension_match(create_if_missing=True)
    return jsonify(
        {
            "ok": True,
            "error": None,
            "match": public_ascension_match_state(match, perspective="player"),
            "actions": ascension_legal_actions(match, "player"),
        }
    )


@app.route("/api/ascension/intent", methods=["POST"])
def api_ascension_intent():
    match = _get_ascension_match(create_if_missing=True)
    payload = _ascension_request_payload()
    try:
        ascension_choose_intent(match, "player", payload.get("intent"))
        return _ascension_json(match)
    except AscensionActionError as error:
        return _ascension_error(match, error)


@app.route("/api/ascension/play", methods=["POST"])
def api_ascension_play():
    match = _get_ascension_match(create_if_missing=True)
    payload = _ascension_request_payload()
    try:
        ascension_play_card(match, "player", payload.get("card_id"), mode=payload.get("mode"))
        _record_finished_ascension_match(match)
        return _ascension_json(match, extra={"reward": match.get("ascension_reward")})
    except AscensionActionError as error:
        return _ascension_error(match, error)


@app.route("/api/ascension/commit", methods=["POST"])
def api_ascension_commit():
    match = _get_ascension_match(create_if_missing=True)
    try:
        if not match["player"].get("intent"):
            raise AscensionActionError("intent_required", "Choose an Intent before you Commit.")
        run_ascension_bot_turn(match)
        ascension_resolve_clash(match)
        event = _record_finished_ascension_match(match)
        return _ascension_json(match, extra={"progression_event": event, "reward": match.get("ascension_reward")})
    except AscensionActionError as error:
        return _ascension_error(match, error)


@app.route("/api/ascension/dominate", methods=["POST"])
def api_ascension_dominate():
    match = _get_ascension_match(create_if_missing=True)
    try:
        result = ascension_attempt_dominate(match, "player")
        event = _record_finished_ascension_match(match)
        return _ascension_json(match, ok=bool(result.get("ok")), error=None if result.get("ok") else result, extra={"domination": result, "progression_event": event, "reward": match.get("ascension_reward")})
    except AscensionActionError as error:
        return _ascension_error(match, error)


@app.route("/ascension-history")
def ascension_history():
    records = read_history_records(app.instance_path, limit=30)
    return render_template("ascension_history.html", user=current_user(), records=records)






# =========================================================
# AMBITIONZ V1.20 — FEEDBACK COLLECTION 2.0
# =========================================================

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    user = current_user()

    categories = [
        {"value": "bug", "label": "Bug"},
        {"value": "balance", "label": "Balanceamento"},
        {"value": "suggestion", "label": "Suggestion"},
        {"value": "visual", "label": "Visual"},
        {"value": "training_battle", "label": "Training battle"},
        {"value": "rewards_missions", "label": "Rewards / Missions"},
        {"value": "deck_builder", "label": "Deck builder"},
        {"value": "android_issue", "label": "Android issue"},
        {"value": "other", "label": "Outro"},
    ]

    severities = [
        {"value": "low", "label": "Low"},
        {"value": "normal", "label": "Normal"},
        {"value": "high", "label": "High"},
        {"value": "critical", "label": "Critical"},
    ]

    if request.method == "POST":
        category = (request.form.get("category") or request.form.get("type") or "other").strip() or "other"
        severity = request.form.get("severity", "normal").strip() or "normal"
        title = request.form.get("title", "").strip()
        message = request.form.get("message", "").strip()
        page_url = request.form.get("page_url", "").strip()
        contact = request.form.get("contact", "").strip()

        valid_categories = {item["value"] for item in categories}
        valid_severities = {item["value"] for item in severities}

        if category not in valid_categories:
            category = "other"

        if severity not in valid_severities:
            severity = "normal"

        if not message or len(message) < 10:
            flash("Feedback message must have at least 10 characters.")
            return redirect("/feedback")

        if not title:
            category_label = next((item["label"] for item in categories if item["value"] == category), "Beta")
            context_label = page_url or "Ambitionz beta"
            title = f"{category_label} feedback: {context_label}"[:160]

        try:
            if user:
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

        stored_message = message
        if contact:
            stored_message = f"{stored_message}\n\nContact: {contact[:120]}"

        report = FeedbackReport(
            user_id=user.id if user else None,
            username=user.username if user else "Guest Beta Tester",
            category=category,
            severity=severity,
            title=title[:160],
            message=stored_message,
            page_url=page_url[:255] if page_url else None,
            status="open",
        )

        db.session.add(report)

        try:
            log_system_event(
                "info",
                "feedback",
                f"Feedback submitted: {title[:80]}",
                user_id=user.id if user else None,
            )
            record_retention_event(
                user,
                "feedback_submit",
                page="/feedback",
                metadata={"category": category, "severity": severity, "has_contact": bool(contact)},
            )
        except Exception as error:
            print("FEEDBACK LOG ERROR:", type(error).__name__, error)

        db.session.commit()

        flash("Feedback sent. Thank you for helping improve the beta.")
        return redirect("/feedback")

    recent_reports = []

    if user:
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
            track_beta_mission(user, "complete_tutorial", page="/tutorial")
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
    beta_missions = []
    deck_status = beta_deck_status(user)

    try:
        ensure_beta_missions(user)
        ensure_daily_missions(user)
        all_missions = (
            UserMission.query
            .filter_by(user_id=user.id)
            .order_by(UserMission.id.desc())
            .all()
        )
        missions = [mission for mission in all_missions if mission.mission_date != "beta"]
        beta_missions = [mission for mission in all_missions if mission.mission_date == "beta"]

    except Exception as error:
        print("MISSIONS PAGE ERROR:", type(error).__name__, error)
        db.session.rollback()
        missions = []
        beta_missions = []

    mission_guides = build_beta_mission_guides(user, beta_missions, deck_status)

    return render_template(
        "missions.html",
        user=user,
        missions=missions,
        mission_guides=mission_guides,
        mission_board_summary=build_mission_board_summary(mission_guides, missions),
        deck_status=deck_status,
        beta_journey=build_beta_journey(user, deck_status),
        wallet=gold_wallet_payload(user),
    )


@app.route("/missions/claim/<int:mission_id>", methods=["POST"])
def claim_user_mission(mission_id):
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    try:
        mission = UserMission.query.filter_by(id=mission_id, user_id=user.id).first()
        gold_reward = int(getattr(mission, "coin_reward", 0) or 0) if mission else 0
        mission_key = str(getattr(mission, "mission_key", "") or "")
        success, message = claim_mission(user, mission_id)

        if success:
            record_retention_event(user, "xp_awarded", page="/missions", metadata={"source": "mission_claim", "mission_id": mission_id})
            record_retention_event(
                user,
                "mission_reward_claimed",
                page="/missions",
                metadata={
                    "mission_id": mission_id,
                    "mission_key": mission_key,
                    "gold": gold_reward,
                },
            )

            if gold_reward > 0:
                record_retention_event(
                    user,
                    "currency_credit",
                    page="/missions",
                    metadata={
                        "currency": GOLD_DISPLAY_NAME,
                        "amount": gold_reward,
                        "source": "mission_claim",
                        "mission_key": mission_key,
                        "balance": get_gold_balance(user),
                    },
                )

            db.session.commit()
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
            user_matches = (
                MatchHistory.query
                .filter(
                    (MatchHistory.player1_id == user.id) |
                    (MatchHistory.player2_id == user.id)
                )
                .order_by(MatchHistory.id.desc())
                .limit(50)
                .all()
            )

            matches = user_matches
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
    deck_status = beta_deck_status(user)

    if user:
        record_retention_event(user, "daily_view", page="/daily", metadata={"today": today_key()}, commit=True)

    return render_template(
        "daily.html",
        user=user,
        missions=missions,
        daily_checkin=build_daily_checkin(user, missions),
        beta_journey=build_beta_journey(user, deck_status),
        wallet=gold_wallet_payload(user),
    )


@app.route("/daily/claim", methods=["POST"])
def claim_daily_checkin():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    today = today_key()
    last_claim = str(getattr(user, "daily_last_checkin_date", "") or "")

    if last_claim == today:
        flash("Daily check-in already claimed today.")
        return redirect(url_for("daily"))

    try:
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        previous_streak = int(getattr(user, "daily_streak", 0) or 0)

        if last_claim == yesterday:
            user.daily_streak = previous_streak + 1
        else:
            user.daily_streak = 1

        user.daily_best_streak = max(int(getattr(user, "daily_best_streak", 0) or 0), int(user.daily_streak or 0))
        user.daily_last_checkin_date = today
        daily_reward = beta_daily_reward_for_streak(user.daily_streak)

        xp_result = award_xp(
            user,
            daily_reward["xp"],
            source="daily_checkin",
            metadata={"date": today, "streak": user.daily_streak},
            reward_key=f"daily:{user.id}:{today}",
        )
        gold_result = credit_gold(
            user,
            daily_reward["gold"],
            source="daily_checkin",
            reason="Daily check-in Gold reward.",
            reference_type="daily",
            reference_id=today,
            metadata={"page": "/daily", "date": today, "streak": user.daily_streak},
        )
        mission_update = track_beta_mission(
            user,
            "return_daily",
            page="/daily",
            metadata={"date": today, "streak": user.daily_streak},
        )
        record_retention_event(
            user,
            "daily_claim",
            page="/daily",
            metadata={
                "date": today,
                "streak": user.daily_streak,
                "xp": xp_result.get("xp", 0),
                "gold": gold_result.get("amount", 0) if gold_result.get("ok") else 0,
                "reward": daily_reward["label"],
                "mission_completed": bool(mission_update and mission_update.get("completed")),
            },
        )
        record_retention_event(
            user,
            "daily_claimed",
            page="/daily",
            metadata={
                "date": today,
                "streak": user.daily_streak,
                "xp": xp_result.get("xp", 0),
                "gold": gold_result.get("amount", 0) if gold_result.get("ok") else 0,
                "reward": daily_reward["label"],
            },
        )
        record_retention_event(
            user,
            "xp_awarded",
            page="/daily",
            metadata={"source": "daily_checkin", "xp": xp_result.get("xp", 0)},
        )
        db.session.commit()
        flash(f"Daily check-in claimed: +{xp_result.get('xp', 0)} XP and +{gold_result.get('amount', 0) if gold_result.get('ok') else 0} Gold.")
    except Exception as error:
        print("DAILY CLAIM ERROR:", type(error).__name__, error)
        db.session.rollback()
        flash("Daily check-in could not be claimed. Try again.")

    return redirect(url_for("daily"))


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


@app.route("/api/beta/telemetry", methods=["POST"])
def api_beta_telemetry():
    try:
        payload = request.get_json(silent=True) or {}
    except Exception:
        payload = {}

    normalized, error_code = normalize_telemetry_payload(payload)

    if error_code:
        return jsonify({"ok": False, "error": error_code, "message": "Telemetry event was not accepted."}), 400

    user = current_user()
    user_id = user.id if user else None
    rate_key = request_rate_limit_key(
        request,
        session,
        app.config.get("SECRET_KEY", ""),
        "beta_telemetry",
        identity=str(user_id or "anonymous"),
    )

    if not beta_telemetry_limiter.allow(rate_key, int(app.config.get("BETA_TELEMETRY_RATE_LIMIT", 90) or 90), 60):
        return jsonify({"ok": True, "limited": True, "event": normalized["event"]})

    record = {
        "event": normalized["event"],
        "page": normalized["page"],
        "metadata": normalized["metadata"],
        "user_id": user_id,
        "is_guest": user_id is None,
        "recorded_at": utc_iso(),
    }

    try:
        event = RetentionEvent(
            user_id=user_id,
            event_key=normalized["event"],
            page=normalized["page"],
            metadata_json=json.dumps(record["metadata"], ensure_ascii=False)[:4000],
        )
        db.session.add(event)
        db.session.commit()
        return jsonify({"ok": True, "event": normalized["event"], "stored": "retention_events", "id": event.id})
    except Exception as error:
        print("BETA TELEMETRY DB ERROR:", type(error).__name__, error)
        db.session.rollback()

    try:
        path = append_jsonl(app, "beta_telemetry.jsonl", record)
        return jsonify({"ok": True, "event": normalized["event"], "stored": "jsonl", "path": path.name})
    except Exception as error:
        print("BETA TELEMETRY JSONL ERROR:", type(error).__name__, error)
        return jsonify({"ok": False, "error": "persist_failed", "message": "Telemetry could not be stored."}), 500


@app.route("/api/beta/feedback", methods=["POST"])
def api_beta_feedback():
    try:
        payload = request.get_json(silent=True) or {}
    except Exception:
        payload = {}

    normalized, error_code = normalize_feedback_payload(payload)

    if error_code:
        return jsonify({"ok": False, "error": error_code, "message": "Feedback message needs a little more detail."}), 400

    user = current_user()
    user_id = user.id if user else None
    rate_key = request_rate_limit_key(
        request,
        session,
        app.config.get("SECRET_KEY", ""),
        "beta_feedback",
        identity=str(user_id or "anonymous"),
    )

    if not beta_feedback_limiter.allow(rate_key, int(app.config.get("BETA_FEEDBACK_RATE_LIMIT", 8) or 8), 60):
        return jsonify({"ok": False, "error": "rate_limited", "message": "Too many feedback reports. Try again shortly."}), 429

    title = f"Beta widget: {normalized['type'].title()}"[:160]
    stored_message = normalized["message"]

    if normalized.get("page"):
        stored_message = f"{stored_message}\n\nPage: {normalized['page'][:220]}"

    record = {
        "type": normalized["type"],
        "message": normalized["message"],
        "page": normalized.get("page") or "",
        "user_id": user_id,
        "username": user.username if user else "Guest Beta Tester",
        "recorded_at": utc_iso(),
    }

    try:
        report = FeedbackReport(
            user_id=user_id,
            username=user.username if user else "Guest Beta Tester",
            category=normalized["type"],
            severity="normal",
            title=title,
            message=stored_message,
            page_url=normalized.get("page") or None,
            status="open",
        )
        db.session.add(report)
        db.session.add(RetentionEvent(
            user_id=user_id,
            event_key="beta_feedback_submit",
            page=normalized.get("page") or request.referrer or "",
            metadata_json=json.dumps({"type": normalized["type"], "source": "widget"}, ensure_ascii=False),
        ))
        db.session.commit()
        return jsonify({"ok": True, "id": report.id, "stored": "feedback_reports", "message": "Feedback received. Thank you."})
    except Exception as error:
        print("BETA FEEDBACK DB ERROR:", type(error).__name__, error)
        db.session.rollback()

    try:
        path = append_jsonl(app, "beta_feedback.jsonl", record)
        return jsonify({"ok": True, "stored": "jsonl", "path": path.name, "message": "Feedback received. Thank you."})
    except Exception as error:
        print("BETA FEEDBACK JSONL ERROR:", type(error).__name__, error)
        return jsonify({"ok": False, "error": "persist_failed", "message": "Feedback could not be stored."}), 500





@app.route("/match-history/<int:history_id>")
def match_history_detail(history_id):
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()

    history = (
        MatchHistory.query
        .filter(
            MatchHistory.id == history_id,
            (MatchHistory.player1_id == user.id) | (MatchHistory.player2_id == user.id),
        )
        .first_or_404()
    )

    try:
        raw_events = json.loads(history.battle_log_json or "[]")
    except Exception:
        raw_events = []

    events = []

    for item in raw_events[:60]:
        if isinstance(item, dict):
            events.append(item)
        else:
            events.append({"type": "log", "message": str(item)})

    viewer_key = "p1" if history.player1_id == user.id else "p2"
    opponent_name = history.player2_name if viewer_key == "p1" else history.player1_name
    mode = str(getattr(history, "mode", "") or "").strip().lower()

    if not mode:
        mode = "training" if "bot" in str(opponent_name or "").lower() else "pvp"

    try:
        reward_summary = json.loads(history.reward_summary or "{}")
    except Exception:
        reward_summary = {}

    perspective_reward = {}

    if isinstance(reward_summary, dict):
        perspective_reward = reward_summary.get(viewer_key) or reward_summary

    summary = {
        "mode": mode,
        "round": history.total_rounds,
        "reward": perspective_reward if isinstance(perspective_reward, dict) else {},
        "xp_gained": int((perspective_reward or {}).get("xp", getattr(history, "xp_gained", 0)) or 0) if isinstance(perspective_reward, dict) else int(getattr(history, "xp_gained", 0) or 0),
        "campaign_chapter_id": getattr(history, "campaign_chapter_id", None),
        "campaign_result": getattr(history, "campaign_result", None),
        "winner": history.winner_name or "Draw",
        "opponent_name": opponent_name,
        "events": events,
    }

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
    daily_missions = []
    deck_status = beta_deck_status(user)
    collection_progress = beta_collection_progress(user)
    wallet = gold_wallet_payload(user)
    progression_stats = {
        "username": user.username,
        "level": int(user.level or 1),
        "xp": int(user.xp or 0),
        "total_xp": int(getattr(user, "total_xp", 0) or 0),
        "next_level_xp": int(user.next_level_xp or 100),
        "level_progress_percent": user.level_progress_percent,
        "wins": int(user.wins or 0),
        "losses": int(user.losses or 0),
        "total_matches": int(user.wins or 0) + int(user.losses or 0),
        "first_training_completed": bool(getattr(user, "first_training_completed", False)),
        "gold_balance": get_gold_balance(user),
        "daily_streak": int(getattr(user, "daily_streak", 0) or 0),
        "daily_best_streak": int(getattr(user, "daily_best_streak", 0) or 0),
    }

    try:
        ensure_beta_missions(user)
        ensure_daily_missions(user)
        missions = (
            UserMission.query
            .filter(UserMission.user_id == user.id, UserMission.mission_date != "beta")
            .order_by(UserMission.id.desc())
            .limit(6)
            .all()
        )
        daily_missions = missions
    except Exception as error:
        print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
        db.session.rollback()
        missions = []
        daily_missions = []

    next_steps = [
        {
            "title": "Play a Match",
            "description": "Earn XP and Gold from the fastest beta loop.",
            "url": url_for("training"),
            "cta": "Play Training",
        },
        {
            "title": "Daily Check-In",
            "description": "See today's defensive reward preview.",
            "url": url_for("daily"),
            "cta": "Open Daily",
        },
        {
            "title": "Claim Missions",
            "description": "Convert completed objectives into XP and Gold.",
            "url": url_for("missions"),
            "cta": "View Missions",
        },
        {
            "title": "Start Campaign",
            "description": "Follow the first beta chapter path without a separate ruleset.",
            "url": url_for("campaign"),
            "cta": "Campaign",
        },
        {
            "title": "Improve Deck",
            "description": "Tune your 30-card beta deck and return to Training.",
            "url": url_for("deck_builder"),
            "cta": "Edit Deck",
        },
        {
            "title": "Review History",
            "description": "Check recent outcomes and plan the next run.",
            "url": url_for("match_history"),
            "cta": "Match History",
        },
    ]

    return render_template(
        "progression.html",
        user=user,
        missions=missions,
        next_steps=next_steps,
        progression_stats=progression_stats,
        collection_progress=collection_progress,
        deck_status=deck_status,
        daily_checkin=build_daily_checkin(user, daily_missions),
        beta_journey=build_beta_journey(user, deck_status),
        wallet=wallet,
        first_session_questline=build_first_session_questline(user, deck_status, wallet, collection_progress),
        deck_coach=build_deck_readiness_coach(user, deck_status=deck_status),
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
            card_type=data.get("card_type"),
            official_type=data.get("official_type"),
            target_type=data.get("target_type"),
            target_owner=data.get("target_owner"),
            target_lane=data.get("target_lane"),
            target_id=data.get("target_id"),
            cast_mode=data.get("cast_mode"),
            prepared=data.get("prepared"),
            client_selected_target=data.get("client_selected_target"),
            source=data.get("source"),
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

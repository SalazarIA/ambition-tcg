import json
import os
import random
import secrets
from datetime import datetime, timezone, timedelta, timezone

import itsdangerous
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_socketio import SocketIO, join_room
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import text as sql_text
from sqlalchemy import inspect as sql_inspect

from config import Config
from game.battle import resolve_battle
from game.cards import CARD_CATALOG, card_sort_key, get_card_by_id
from game.deck import (
    build_playable_deck,
    collection_summary,
    deck_summary,
    draw_starting_hand,
    load_card_ids,
    validate_deck,
    full_deck_analysis,
    create_starter_deck_from_collection,
)
from models import ensure_liveops_schema, BetaInvite, SystemLog, BoosterHistory, CardStat, FeedbackReport, MatchHistory, User, db, ensure_database_schema
from game.progression import award_xp, claim_mission, ensure_daily_missions, increment_mission
from services.admin.cleanup_service import clear_gameplay_data, delete_non_admin_users
from services.email_service import send_verification_email, send_password_reset_email, send_smtp_test_email, is_smtp_configured
from game.rules import can_pay_cost, pay_card_cost, reset_player_energy
from game.engine import register_card_played_for_ambition, request_unleash, cancel_unleash
from game.state import create_player_state, set_player_intent
from game.matchmaking import generate_private_room_code, is_valid_room_code, normalize_room_code
from game.bot_ai import bot_choose_play
from game.bot import create_bot_player, bot_play_turn
from game.rewards import apply_match_rewards
from game.match_utils import safe_user_id, player_display_name, get_match_result_label
from game.card_view import enrich_cards_for_view
from game.state import create_player_state, normalize_intent


app = Flask(__name__)
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

socketio = SocketIO(
    app,
    async_mode="threading",
    cors_allowed_origins="*",
    manage_session=False,
)

serializer = itsdangerous.URLSafeTimedSerializer(app.config["SECRET_KEY"])

active_matches = {}
player_rooms = {}
waiting_player = None
private_waiting_rooms = {}
login_attempts = {}


def create_database_tables():
    with app.app_context():
        db.create_all()


create_database_tables()


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


def generate_invite_code():
    return secrets.token_hex(4).upper()


def account_can_login(user):
    if not user:
        return False, "Invalid account."

    if getattr(user, "account_status", "active") in ["banned", "disabled"]:
        return False, "Account is not allowed to login."

    return True, ""


def mark_user_verified(user):
    user.is_verified = True
    user.account_status = "active"
    user.verified_at = datetime.now(timezone.utc)


def get_public_base_url():
    return app.config.get("PUBLIC_BASE_URL", request.url_root.rstrip("/"))




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
    return bool(app.config.get("DEV_TOOLS_ENABLED", False))


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


def admin_required_redirect():
    auth_redirect = login_required_redirect()


def get_existing_table_names():
    try:
        inspector = sql_inspect(db.engine)
        return set(inspector.get_table_names())
    except Exception as error:
        print("Table inspection failed:", type(error).__name__, error)
        return set()


def safe_delete_table_rows(connection, table_name, where_clause=None, params=None):
    """Delete rows from a table only if it exists. Works on SQLite and PostgreSQL."""
    try:
        existing_tables = get_existing_table_names()

        if table_name not in existing_tables:
            print(f"Cleanup skipped; table does not exist: {table_name}")
            return False

        if where_clause:
            query = f'DELETE FROM "{table_name}" WHERE {where_clause}'
            connection.execute(sql_text(query), params or {})
        else:
            query = f'DELETE FROM "{table_name}"'
            connection.execute(sql_text(query))

        print(f"Cleanup OK: {table_name}")
        return True

    except Exception as error:
        print(f"Cleanup ERROR on {table_name}: {type(error).__name__}: {error}")
        return False


def cleanup_gameplay_tables():
    """Clear operational/gameplay tables while preserving users."""
    tables = [
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
    ]

    cleared = []

    with db.engine.begin() as connection:
        for table in tables:
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

    dependency_tables = [
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
    ]

    deleted_users = 0

    with db.engine.begin() as connection:
        existing_tables = get_existing_table_names()

        for table in dependency_tables:
            if table in existing_tables:
                try:
                    connection.execute(sql_text(f'DELETE FROM "{table}"'))
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
            print("--- DELETE NON ADMIN USERS ERROR ---")
            print("Error type:", type(error).__name__)
            print("Error:", error)
            print("------------------------------------")
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
        print("--- ADMIN SMTP TEST ROUTE ERROR ---")
        print("Error type:", type(error).__name__)
        print("Error:", error)
        print("Destination:", email)
        print("-----------------------------------")

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
        print("--- ADMIN RESET TEST USERS ERROR ---")
        print("Error type:", type(error).__name__)
        print("Error:", error)
        print("------------------------------------")
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
        print("--- ADMIN CLEAR GAMEPLAY DATA ERROR ---")
        print("Error type:", type(error).__name__)
        print("Error:", error)
        print("---------------------------------------")
        flash(f"Cleanup failed: {type(error).__name__}. Check Render logs.")

    return redirect("/admin/dev-tools")


@app.route("/admin/system")
def admin_system():
    auth_redirect = login_required_redirect()

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
        verified_users=User.query.filter_by(is_verified=True).count(),
        total_matches=MatchHistory.query.count(),
        open_feedbacks=FeedbackReport.query.filter_by(status="open").count(),
        recent_logs=SystemLog.query.order_by(SystemLog.created_at.desc()).limit(20).all(),
    )


@app.route("/admin/users")
def admin_users():
    auth_redirect = login_required_redirect()

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
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    current = current_user()

    if not current or not current.is_admin:
        flash("Admin access required.")
        return redirect("/")

    target = db.session.get(User, user_id)

    if target:
        target.is_admin = not target.is_admin
        db.session.commit()
        log_system_event("warning", "admin", f"Admin toggled for {target.email}", user_id=current.id)

    return redirect("/admin/users")


@app.route("/admin/users/<int:user_id>/toggle-tester", methods=["POST"])
def admin_toggle_tester(user_id):
    auth_redirect = login_required_redirect()

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
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    current = current_user()

    if not current or not current.is_admin:
        flash("Admin access required.")
        return redirect("/")

    target = db.session.get(User, user_id)

    if target:
        mark_user_verified(target)
        db.session.commit()
        log_system_event("info", "admin", f"User verified manually: {target.email}", user_id=current.id)

    return redirect("/admin/users")


@app.route("/admin/users/<int:user_id>/ban", methods=["POST"])
def admin_ban_user(user_id):
    auth_redirect = login_required_redirect()

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
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    current = current_user()

    if not current or not current.is_admin:
        flash("Admin access required.")
        return redirect("/")

    target = db.session.get(User, user_id)

    if target:
        target.account_status = "active" if target.is_verified else "unverified"
        db.session.commit()
        log_system_event("info", "admin", f"User unbanned: {target.email}", user_id=current.id)

    return redirect("/admin/users")


@app.route("/admin/invites", methods=["GET", "POST"])
def admin_invites():
    auth_redirect = login_required_redirect()

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


@app.route("/admin/feedback")
def admin_feedback():
    auth_redirect = login_required_redirect()

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
    auth_redirect = login_required_redirect()

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



@app.route("/")
def index():
    user = current_user()
    return render_template("index.html", user=user)



@app.route("/health")
def health():
    return {
        "status": "ok",
        "app": "Ambitionz",
        "version": "Ambitionz V1.03",
        "environment": app.config["ENVIRONMENT"],
    }



@app.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("If this email exists, a verification link will be sent.")
            return redirect("/resend-verification")

        if user.is_verified:
            flash("This account is already verified. You can login.")
            return redirect("/login")

        token = serializer.dumps(user.email, salt="email-confirm")
        verification_url = url_for("confirm_email", token=token, _external=True)

        sent = send_verification_email(user, verification_url)

        if sent:
            flash("Verification email sent.")
        else:
            flash("SMTP failed or is not configured. Check server logs.")

        try:
            log_system_event(
                level="info",
                category="email",
                message="Verification email requested",
                user_id=getattr(user, "id", None),
            )
        except Exception as error:
            print("Resend verification log failed:", error)

        return redirect("/login")

    return render_template("resend_verification.html")



@app.route("/ranking")
def ranking():
    users = (
        User.query
        .filter_by(is_verified=True)
        .order_by(User.wins.desc(), User.level.desc(), User.xp.desc())
        .limit(100)
        .all()
    )

    return render_template("ranking.html", users=users)



@app.route("/how-to-play")
def how_to_play():
    return render_template("how_to_play.html")



@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("If this email exists, a password reset link will be sent.")
            return redirect("/forgot-password")

        token = serializer.dumps(user.email, salt="password-reset")
        reset_url = url_for("reset_password", token=token, _external=True)

        sent = send_password_reset_email(user, reset_url)

        if sent:
            flash("Password reset email sent.")
        else:
            flash("SMTP failed or is not configured. Check server logs.")

        try:
            log_system_event("info", "email", "Password reset requested", user_id=getattr(user, "id", None))
        except Exception as error:
            print("Password reset log failed:", error)

        return redirect("/login")

    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        email = serializer.loads(token, salt="password-reset", max_age=3600)
    except Exception:
        return "Password reset link expired."

    user = User.query.filter_by(email=email).first_or_404()

    if request.method == "POST":
        password = request.form.get("password", "").strip()

        if len(password) < 6:
            flash("Password must have at least 6 characters.")
            return redirect(request.url)

        user.set_password(password)
        db.session.commit()

        flash("Password updated. You can login now.")
        return redirect("/login")

    return render_template("reset_password.html")



@app.route("/terms")
def terms():
    return render_template("terms.html")



@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


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

        if len(password) < 6:
            flash("Password must have at least 6 characters.")
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
            account_status="unverified",
            is_tester=True if invite else False,
        )
        new_user.set_password(password)

        db.session.add(new_user)

        if invite:
            invite.used_count += 1

        db.session.commit()

        token = serializer.dumps(email, salt="email-confirm")
        verification_url = url_for("confirm_email", token=token, _external=True)

        send_verification_email(new_user, verification_url)

        print("\n--- AMBITIONZ VERIFICATION LINK ---")
        print(verification_url)
        print("----------------------------------\n")

        flash("Registered. Check your email for the verification link. If email is not configured, check server logs.")
        return redirect("/login")

    return render_template("register.html")


@app.route("/confirm_email/<token>")
def confirm_email(token):
    try:
        email = serializer.loads(token, salt="email-confirm", max_age=3600)
    except Exception:
        return "Verification link expired."

    user = User.query.filter_by(email=email).first_or_404()
    mark_user_verified(user)

    db.session.commit()

    flash("Account verified. You can login now.")
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        invite_code = request.form.get("invite_code", "").strip().upper()

        attempt_key = f"{request.remote_addr}:{email}"
        attempts = login_attempts.get(attempt_key, 0)

        if attempts >= app.config.get("LOGIN_ATTEMPT_LIMIT", 8):
            flash("Too many login attempts. Try again later.")
            return redirect("/login")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            login_attempts[attempt_key] = attempts + 1
            flash("Invalid login.")
            return redirect("/login")

        can_login, login_message = account_can_login(user)

        if not can_login:
            flash(login_message)
            return redirect("/login")

        if not user.is_verified:
            flash("Verify your email first. You can resend the verification email below.")
            return redirect("/resend-verification")

        login_attempts.pop(attempt_key, None)

        user.last_login_at = datetime.now(timezone.utc)
        user.login_count = int(user.login_count or 0) + 1
        db.session.commit()

        session["user_id"] = user.id

        try:
            if not getattr(user, "has_completed_onboarding", False):
                return redirect("/welcome")
        except Exception as error:
            print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)

        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/collection")
def collection():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    collection_ids = load_card_ids(user.collection_json)
    cards = collection_summary(collection_ids)
    cards = sorted(cards, key=card_sort_key)
    cards = enrich_cards_for_view(cards)

    return render_template("collection.html", user=user, cards=cards)


@app.route("/shop", methods=["GET", "POST"])
def shop():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    pulled_cards = []

    if request.method == "POST":
        pack_cost = 300

        if user.coins < pack_cost:
            flash("Not enough coins.")
            return redirect("/shop")

        user.coins -= pack_cost

        collection_ids = load_card_ids(user.collection_json)

        for _ in range(5):
            card = booster_pull()
            pulled_cards.append(card)
            collection_ids.append(card["id"])

        common_count = len([card for card in pulled_cards if card.get("rarity") == "Common"])
        uncommon_count = len([card for card in pulled_cards if card.get("rarity") == "Uncommon"])

        history = BoosterHistory(
            user_id=safe_admin_user_id(),
            username=user.username,
            cost=pack_cost,
            cards_json=json.dumps(pulled_cards),
            common_count=common_count,
            uncommon_count=uncommon_count,
        )

        db.session.add(history)

        user.collection_json = json.dumps(collection_ids)
        increment_mission(user, "open_1_booster", 1)
        db.session.commit()

    return render_template("shop.html", user=user, pulled_cards=pulled_cards)




@app.route("/auto-build-deck", methods=["POST"])
def auto_build_deck():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    collection_ids = load_card_ids(user.collection_json)

    user.deck_json = create_starter_deck_from_collection(collection_ids)
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
        .filter_by(user_id=safe_admin_user_id())
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

    collection_ids = load_card_ids(user.collection_json)
    deck_ids = load_card_ids(user.deck_json)

    if request.method == "POST":
        selected_cards = request.form.getlist("deck_cards")
        errors = validate_deck(selected_cards, collection_ids)

        if errors:
            for error in errors:
                flash(error)
        else:
            user.deck_json = json.dumps(selected_cards)
            db.session.commit()
            flash("Deck saved successfully.")

        return redirect("/deck-builder")

    collection_cards = sorted(collection_summary(collection_ids), key=card_sort_key)
    current_deck = sorted(deck_summary(deck_ids), key=card_sort_key)

    collection_cards = enrich_cards_for_view(collection_cards)
    current_deck = enrich_cards_for_view(current_deck)

    deck_validation_errors = validate_deck(deck_ids, collection_ids)
    deck_analysis = full_deck_analysis(deck_ids)

    return render_template(
        "deck_builder.html",
        user=user,
        collection_cards=collection_cards,
        current_deck=current_deck,
        deck_ids=deck_ids,
        deck_validation_errors=deck_validation_errors,
        deck_analysis=deck_analysis,
    )


@app.route("/arena")
def arena():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    user = current_user()
    collection_ids = load_card_ids(user.collection_json)
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

    return render_template(
        "arena.html",
        user=user,
        match_mode=match_mode,
        private_code=private_code,
    )


def find_player_key(match, sid):
    if match["p1"]["sid"] == sid:
        return "p1"

    if match["p2"]["sid"] == sid:
        return "p2"

    return None


def emit_log(room_id, message):
    match = active_matches.get(room_id)

    if match is not None:
        match.setdefault("logs", [])
        match["logs"].append(str(message))

    socketio.emit("battle_log", {"msg": message}, to=room_id)


def emit_state(room_id):
    match = active_matches.get(room_id)

    if not match:
        return

    for player_key, enemy_key in [("p1", "p2"), ("p2", "p1")]:
        player = match[player_key]
        enemy = match[enemy_key]

        if player.get("is_bot"):
            continue

        enemy_monster_status = "EMPTY"

        if enemy.get("field_m"):
            enemy_monster_status = "REVEALED" if match["resolving"] else "HIDDEN"

        enemy_st_status = "EMPTY"

        if enemy.get("field_st"):
            enemy_st_status = "SET"

        state = {
            "room_id": room_id,
            "round": match["round"],
            "phase": match.get("phase", "Set Phase"),
            "resolving": match["resolving"],
            "me": {
                "name": player["name"],
                "hp": player["hp"],
                "deck_count": len(player["deck"]),
                "graveyard_count": len(player["graveyard"]),
                "hand": player["hand"],
                "field_m": player["field_m"],
                "field_st": player["field_st"],
                "ready": player["ready"],
                "energy": player.get("energy", 0),
                "max_energy": player.get("max_energy", 0),
                "ambition": player.get("ambition", 0),
                "ambition_unleashed": player.get("ambition_unleashed", False),
                "wants_unleash": player.get("wants_unleash", False),
                "overreach_count": player.get("overreach_count", 0),
                "intent": player.get("intent", "Strike"),
            },
            "enemy": {
                "name": enemy["name"],
                "hp": enemy["hp"],
                "deck_count": len(enemy["deck"]),
                "graveyard_count": len(enemy["graveyard"]),
                "hand_count": len(enemy["hand"]),
                "ready": enemy["ready"],
                "energy": enemy.get("energy", 0),
                "max_energy": enemy.get("max_energy", 0),
                "ambition": enemy.get("ambition", 0),
                "ambition_unleashed": enemy.get("ambition_unleashed", False),
                "wants_unleash": enemy.get("wants_unleash", False),
                "overreach_count": enemy.get("overreach_count", 0),
                "intent": enemy.get("intent", "Strike"),
                "field_m_status": enemy_monster_status,
                "field_m_rev": enemy["field_m"] if match["resolving"] else None,
                "field_st_status": enemy_st_status,
            },
        }

        socketio.emit("game_state_update", state, to=player["sid"])


def create_player_object(user, sid):
    deck = build_playable_deck(user.deck_json)
    hand = draw_starting_hand(deck, 5)

    player = create_player_state(user, sid, deck, hand)

    reset_player_energy(player, 1)

    return player


def end_match(room_id, winner_key):
    match = active_matches.get(room_id)

    if not match:
        return

    p1 = match["p1"]
    p2 = match["p2"]

    battle_logs = match.get("logs", [])

    if winner_key == "DRAW":
        socketio.emit("game_over", {"result": "DRAW"}, to=p1["sid"])

        if not p2.get("is_bot"):
            socketio.emit("game_over", {"result": "DRAW"}, to=p2["sid"])

        winner_id = None
        winner_name = None
        result = "DRAW"

    else:
        loser_key = "p2" if winner_key == "p1" else "p1"

        winner = match[winner_key]
        loser = match[loser_key]

        result = "FINISHED"
        winner_id = safe_user_id(winner)
        winner_name = player_display_name(winner)

        if not winner.get("is_bot"):
            socketio.emit("game_over", {"result": "WIN"}, to=winner["sid"])

        if not loser.get("is_bot"):
            socketio.emit("game_over", {"result": "LOSE"}, to=loser["sid"])

        winner_user = db.session.get(User, safe_user_id(winner)) if safe_user_id(winner) else None
        loser_user = db.session.get(User, safe_user_id(loser)) if safe_user_id(loser) else None

        is_bot_match = bool(match.get("is_bot_match"))

        if winner_user:
            winner_user.wins += 1
            apply_match_rewards(
                winner_user,
                is_bot_match=is_bot_match,
                did_win=True,
                award_xp_function=award_xp,
            )

            increment_mission(winner_user, "play_1_match", 1)
            increment_mission(winner_user, "play_3_matches", 1)
            increment_mission(winner_user, "win_1_match", 1)

        if loser_user:
            loser_user.losses += 1
            apply_match_rewards(
                loser_user,
                is_bot_match=is_bot_match,
                did_win=False,
                award_xp_function=award_xp,
            )

            increment_mission(loser_user, "play_1_match", 1)
            increment_mission(loser_user, "play_3_matches", 1)

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
    update_card_stats_after_match(match, winner_key)

    db.session.commit()

    player_rooms.pop(p1["sid"], None)

    if not p2.get("is_bot"):
        player_rooms.pop(p2["sid"], None)

    active_matches.pop(room_id, None)


@socketio.on("join_training")
def handle_join_training():
    user_id = session.get("user_id")

    if not user_id:
        return

    user = db.session.get(User, user_id)

    if not user:
        return

    sid = request.sid

    if sid in player_rooms:
        return

    try:
        player_object = create_player_object(user, sid)

        bot_user = type("BotUser", (), {})()
        bot_user.id = 0
        bot_user.username = "Ambitionz Bot"
        bot_user.deck_json = user.deck_json

        bot_object = create_player_object(bot_user, f"bot_{sid}")
        bot_object["name"] = "Ambitionz Bot"
        bot_object["sid"] = f"bot_{sid}"

        room_id = f"training_{sid}"

        join_room(room_id, sid=sid)

        active_matches[room_id] = {
            "p1": player_object,
            "p2": bot_object,
            "round": 1,
            "phase": "Set Phase",
            "resolving": False,
            "logs": [],
            "training": True,
        }

        player_rooms[sid] = room_id

        socketio.emit("match_found", {"msg": "Training started against Ambitionz Bot."}, to=sid)
        emit_log(room_id, "Training started. Choose an Intent, set cards, then press Ready.")
        emit_state(room_id)

    except Exception as error:
        print("TRAINING START ERROR:", type(error).__name__, error)
        socketio.emit("queue_status", {"msg": "Training failed to start. Check your deck."}, to=sid)




@socketio.on("join_queue")
def handle_join_queue():
    global waiting_player

    user_id = session.get("user_id")

    if not user_id:
        return

    user = db.session.get(User, user_id)

    if not user:
        return

    current_sid = request.sid

    if current_sid in player_rooms:
        return

    player_object = create_player_object(user, current_sid)

    if waiting_player is None:
        waiting_player = player_object
        socketio.emit("queue_status", {"msg": "Searching for opponent..."}, to=current_sid)
        return

    if waiting_player["sid"] == current_sid:
        return

    room_id = f"room_{waiting_player['sid']}_{current_sid}"

    join_room(room_id, sid=waiting_player["sid"])
    join_room(room_id, sid=current_sid)

    active_matches[room_id] = {
        "p1": waiting_player,
        "p2": player_object,
        "round": 1,
        "phase": "Set Phase",
        "resolving": False,
        "logs": [],
    }

    player_rooms[waiting_player["sid"]] = room_id
    player_rooms[current_sid] = room_id

    socketio.emit("match_found", {"msg": "Opponent found. Duel started."}, to=room_id)

    waiting_player = None

    emit_log(room_id, "Match started.")
    emit_state(room_id)



@socketio.on("set_intent")
def set_intent(data):
    room_id = player_rooms.get(request.sid)

    if not room_id:
        return

    match = active_matches.get(room_id)

    if not match or match["resolving"]:
        return

    player_key = find_player_key(match, request.sid)

    if not player_key:
        return

    player = match[player_key]

    if player["ready"]:
        return

    intent = normalize_intent(data.get("intent"))
    set_player_intent(player, intent, match.setdefault("logs", []))

    socketio.emit("battle_log", {"msg": f"{player['name']} chose {intent} intent."}, to=request.sid)
    emit_state(room_id)


@socketio.on("toggle_unleash")
def toggle_unleash():
    room_id = player_rooms.get(request.sid)

    if not room_id:
        return

    match = active_matches.get(room_id)

    if not match or match["resolving"]:
        return

    player_key = find_player_key(match, request.sid)

    if not player_key:
        return

    player = match[player_key]

    if player["ready"]:
        return

    success, message = request_unleash(player, match.setdefault("logs", []))

    socketio.emit("battle_log", {"msg": message}, to=request.sid)
    emit_state(room_id)

@socketio.on("play_to_field")
def play_to_field(data):
    room_id = player_rooms.get(request.sid)

    if not room_id:
        return

    match = active_matches.get(room_id)

    if not match or match["resolving"]:
        return

    player_key = find_player_key(match, request.sid)

    if not player_key:
        return

    player = match[player_key]

    if player["ready"]:
        return

    try:
        index = int(data.get("index"))
    except Exception:
        return

    if index < 0 or index >= len(player["hand"]):
        return

    card = player["hand"][index]
    card_type = card.get("type")
    card_cost = int(card.get("cost", 1))

    if not can_pay_cost(player, card):
        socketio.emit(
            "battle_log",
            {"msg": f"{player['name']} tried to play {card['name']}, but needs {card_cost} energy."},
            to=request.sid,
        )
        return

    if card_type == "Monster":
        if player["field_m"] is not None:
            emit_log(room_id, f"{player['name']} tried to play another monster, but the monster zone is occupied.")
            return

        pay_card_cost(player, card)
        player["field_m"] = player["hand"].pop(index)
        register_card_played_for_ambition(player, card, match.setdefault("logs", []))
        emit_log(room_id, f"{player['name']} set a monster: {card['name']} for {card_cost} energy.")

    elif card_type in ["Spell", "Trap"]:
        if player["field_st"] is not None:
            emit_log(room_id, f"{player['name']} tried to play another spell/trap, but the zone is occupied.")
            return

        pay_card_cost(player, card)
        player["field_st"] = player["hand"].pop(index)
        register_card_played_for_ambition(player, card, match.setdefault("logs", []))
        emit_log(room_id, f"{player['name']} set a spell/trap: {card['name']} for {card_cost} energy.")

    emit_state(room_id)




@socketio.on("choose_intent")
def choose_intent(data):
    room_id = player_rooms.get(request.sid)

    if not room_id:
        return

    match = active_matches.get(room_id)

    if not match or match["resolving"]:
        return

    player_key = find_player_key(match, request.sid)

    if not player_key:
        return

    player = match[player_key]

    if player["ready"]:
        return

    intent = data.get("intent", "Strike")
    set_player_intent(player, intent)

    emit_log(room_id, f"{player['name']} selected {player['intent']} intent.")
    emit_state(room_id)


@socketio.on("toggle_unleash")
def toggle_unleash():
    room_id = player_rooms.get(request.sid)

    if not room_id:
        return

    match = active_matches.get(room_id)

    if not match or match["resolving"]:
        return

    player_key = find_player_key(match, request.sid)

    if not player_key:
        return

    player = match[player_key]

    if player["ready"]:
        return

    if player.get("wants_unleash"):
        cancel_unleash(player)
        emit_log(room_id, f"{player['name']} cancelled Ambition Unleash.")
    else:
        success = request_unleash(player)

        if success:
            emit_log(room_id, f"{player['name']} prepared Ambition Unleash for this battle.")
        else:
            socketio.emit(
                "battle_log",
                {"msg": "You need 5 Ambition and a monster on the field to unleash."},
                to=request.sid,
            )

    emit_state(room_id)


@socketio.on("declare_ready")
def declare_ready():
    room_id = player_rooms.get(request.sid)

    if not room_id:
        return

    match = active_matches.get(room_id)

    if not match or match["resolving"]:
        return

    player_key = find_player_key(match, request.sid)

    if not player_key:
        return

    player = match[player_key]
    player["ready"] = True

    if match.get("training"):
        enemy_key = "p2" if player_key == "p1" else "p1"
        enemy = match[enemy_key]

        bot_result = bot_choose_play(enemy, player, difficulty=match.get("bot_difficulty", "normal"))
        emit_log(room_id, f"Ambitionz Bot chose {bot_result['intent']} intent.")

        if bot_result.get("monster"):
            emit_log(room_id, f"Ambitionz Bot set a monster: {bot_result['monster'].get('name', 'Unknown')}.")

        if bot_result.get("spell_or_trap"):
            emit_log(room_id, "Ambitionz Bot set a spell/trap.")

    emit_log(room_id, f"{player['name']} is ready.")
    emit_state(room_id)

    if match.get("is_bot_match") and player_key == "p1" and not match["p2"]["ready"]:
        bot_play_turn(match["p2"], match.setdefault("logs", []))
        emit_log(room_id, f"{match['p2']['name']} is ready.")
        emit_state(room_id)

    if match["p1"]["ready"] and match["p2"]["ready"]:
        battle_result = resolve_battle(match)

        match.setdefault("logs", []).extend(battle_result["logs"])

        for log_message in battle_result["logs"]:
            emit_log(room_id, log_message)

        emit_state(room_id)

        if battle_result["winner"]:
            end_match(room_id, battle_result["winner"])






@socketio.on("join_bot_match")
def handle_join_bot_match():
    user_id = session.get("user_id")

    if not user_id:
        return

    user = db.session.get(User, user_id)

    if not user:
        return

    current_sid = request.sid

    if current_sid in player_rooms:
        return

    player_object = create_player_object(user, current_sid)
    bot_object = create_bot_player(user.deck_json)

    room_id = f"bot_{current_sid}"

    join_room(room_id, sid=current_sid)

    active_matches[room_id] = {
        "p1": player_object,
        "p2": bot_object,
        "round": 1,
        "phase": "Set Phase",
        "resolving": False,
        "logs": [],
        "is_bot_match": True,
    }

    player_rooms[current_sid] = room_id

    socketio.emit("match_found", {"msg": "Training match started against bot."}, to=current_sid)

    emit_log(room_id, "Training match started.")
    emit_log(room_id, f"Opponent: {bot_object['name']}.")
    emit_state(room_id)


@socketio.on("join_private_room")
def handle_join_private_room(data):
    user_id = session.get("user_id")

    if not user_id:
        return

    user = db.session.get(User, user_id)

    if not user:
        return

    current_sid = request.sid

    if current_sid in player_rooms:
        return

    code = normalize_room_code(data.get("code", ""))

    if not is_valid_room_code(code):
        socketio.emit("queue_status", {"msg": "Invalid private room code."}, to=current_sid)
        return

    player_object = create_player_object(user, current_sid)

    if code not in private_waiting_rooms:
        private_waiting_rooms[code] = player_object
        socketio.emit("queue_status", {"msg": f"Private room {code} created. Waiting for opponent..."}, to=current_sid)
        return

    waiting = private_waiting_rooms.get(code)

    if waiting["sid"] == current_sid:
        socketio.emit("queue_status", {"msg": f"Waiting in private room {code}..."}, to=current_sid)
        return

    room_id = f"private_{code}_{waiting['sid']}_{current_sid}"

    start_match_between_players(waiting, player_object, room_id)

    private_waiting_rooms.pop(code, None)


@socketio.on("disconnect")
def handle_disconnect():
    global waiting_player

    sid = request.sid

    if waiting_player and waiting_player["sid"] == sid:
        waiting_player = None
        return

    for room_code, private_player in list(private_waiting_rooms.items()):
        if private_player["sid"] == sid:
            private_waiting_rooms.pop(room_code, None)
            return

    room_id = player_rooms.get(sid)

    if not room_id:
        return

    match = active_matches.get(room_id)

    if not match:
        return

    player_key = find_player_key(match, sid)

    if not player_key:
        return

    enemy_key = "p2" if player_key == "p1" else "p1"
    enemy = match[enemy_key]

    socketio.emit("opponent_left", {"msg": "Opponent disconnected. You win."}, to=enemy["sid"])

    end_match(room_id, enemy_key)







@app.route("/training")
def training():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    return render_template("arena.html", user=current_user(), training_mode=True)





@app.route("/admin")
def admin():
    auth_redirect = admin_required_redirect()

    if auth_redirect:
        return auth_redirect

    try:
        total_users = User.query.count()
        verified_users = User.query.filter_by(is_verified=True).count()
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
            db.session.commit()
        except Exception as error:
            print("Complete onboarding failed:", error)
            db.session.rollback()

    return redirect("/training")



@app.route("/missions/claim/<int:mission_id>", methods=["POST"])
def claim_user_mission(mission_id):
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    flash("Mission rewards are being stabilized for beta.")
    return redirect("/missions")



@app.route("/match-history")
def match_history():
    auth_redirect = login_required_redirect()

    if auth_redirect:
        return auth_redirect

    matches = []

    try:
        if "MatchHistory" in globals():
            matches = (
                MatchHistory.query
                .order_by(MatchHistory.id.desc())
                .limit(50)
                .all()
            )
    except Exception as error:
        print("Match history query failed:", error)
        matches = []

    return render_template("match_history.html", user=current_user(), matches=matches)





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



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    socketio.run(
        app,
        debug=app.config["DEBUG_MODE"],
        host="0.0.0.0",
        port=port,
        allow_unsafe_werkzeug=True,
    )

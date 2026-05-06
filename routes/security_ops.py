from datetime import datetime, timezone

from flask import flash, redirect, render_template, request, session, url_for

from services.security.rate_limit import SlidingWindowRateLimiter, request_rate_limit_key


ALLOWED_BETA_EVENTS = {
    "page_view",
    "action_link_click",
    "form_submit",
    "page_hide",
}

beta_event_limiter = SlidingWindowRateLimiter()
password_reset_limiter = SlidingWindowRateLimiter()


def reset_security_ops_rate_limits():
    beta_event_limiter.clear()
    password_reset_limiter.clear()


def _int_config(app, key, default):
    try:
        return int(app.config.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _safe_text(value, limit, fallback=""):
    cleaned = str(value or fallback).strip()
    return cleaned[:limit]


def register_security_ops_routes(app, deps):
    db = deps["db"]
    User = deps["User"]
    admin_required_redirect = deps["admin_required_redirect"]
    current_user = deps["current_user"]
    get_session_user = deps["get_session_user"]
    hash_url_token = deps["hash_url_token"]
    issue_password_reset_token = deps["issue_password_reset_token"]
    log_system_event = deps["log_system_event"]
    reset_token_is_expired = deps["reset_token_is_expired"]
    send_password_reset_email = deps["send_password_reset_email"]

    @app.route("/admin/whoami")
    def admin_whoami():
        auth_redirect = admin_required_redirect()

        if auth_redirect:
            return auth_redirect

        user = get_session_user()

        return {
            "ok": True,
            "logged_in": True,
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_admin": bool(user.is_admin),
            "is_verified": bool(user.is_verified),
            "is_tester": bool(getattr(user, "is_tester", False)),
            "account_status": getattr(user, "account_status", None),
            "session_user_id": session.get("user_id"),
        }

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            rate_key = request_rate_limit_key(
                request,
                session,
                app.config.get("SECRET_KEY", ""),
                "password_reset",
                identity=email,
            )
            allowed = password_reset_limiter.allow(
                rate_key,
                _int_config(app, "PASSWORD_RESET_RATE_LIMIT", 5),
                _int_config(app, "PASSWORD_RESET_RATE_WINDOW_MINUTES", 60) * 60,
            )

            if not allowed:
                flash("If this email exists, a password reset link will be sent.")
                try:
                    log_system_event(
                        "warning",
                        "security",
                        "Password reset rate limit reached",
                        details={"scope": "password_reset"},
                    )
                except Exception as error:
                    print("PASSWORD RESET RATE LOG ERROR:", type(error).__name__)
                return redirect("/forgot-password")

            user = User.query.filter_by(email=email).first()

            if not user:
                flash("If this email exists, a password reset link will be sent.")
                return redirect("/forgot-password")

            token = issue_password_reset_token(user)
            db.session.commit()
            reset_url = url_for("reset_password", token=token, _external=True)
            sent = send_password_reset_email(user, reset_url)

            flash("If this email exists, a password reset link will be sent.")

            try:
                log_system_event(
                    "info" if sent else "warning",
                    "email",
                    "Password reset requested" if sent else "Password reset requested but SMTP is missing",
                    user_id=getattr(user, "id", None),
                )
            except Exception as error:
                print("Password reset log failed:", error)

            return redirect("/forgot-password")

        return render_template("forgot_password.html")

    @app.route("/reset-password/<token>", methods=["GET", "POST"])
    def reset_password(token):
        token_hash = hash_url_token(token)
        user = User.query.filter_by(reset_token=token_hash).first()

        if not user or reset_token_is_expired(user.reset_token_expires_at):
            return "Password reset link expired."

        if request.method == "POST":
            password = request.form.get("password", "").strip()
            errors = deps["password_errors"](password)

            if errors:
                for error in errors:
                    flash(error)
                return redirect(request.url)

            user.set_password(password)
            user.reset_token = None
            user.reset_token_expires_at = None
            db.session.commit()

            flash("Password updated. You can login now.")
            return redirect("/login")

        return render_template("reset_password.html")

    @app.route("/api/beta-event", methods=["POST"])
    def beta_event():
        user = current_user()

        try:
            payload = request.get_json(silent=True) or request.form.to_dict() or {}
        except Exception:
            payload = {}

        event_name = _safe_text(payload.get("event"), 80, "unknown_event")

        if event_name not in ALLOWED_BETA_EVENTS:
            return ("", 204)

        user_id = getattr(user, "id", None) if user else None
        rate_key = request_rate_limit_key(
            request,
            session,
            app.config.get("SECRET_KEY", ""),
            "beta_event",
            identity=str(user_id or "anonymous"),
        )
        allowed = beta_event_limiter.allow(
            rate_key,
            _int_config(app, "BETA_EVENT_RATE_LIMIT", 60),
            _int_config(app, "BETA_EVENT_RATE_WINDOW_SECONDS", 60),
        )

        if not allowed:
            return ("", 204)

        page_path = _safe_text(payload.get("path") or request.headers.get("Referer"), 180, "unknown_path")
        source = _safe_text(payload.get("source"), 40, "web")
        username = getattr(user, "username", "anonymous") if user else "anonymous"
        message = f"{event_name} | {page_path} | source={source} | user={username}"

        try:
            log_system_event(
                "info",
                "beta_event",
                message,
                details={
                    "event": event_name,
                    "path": page_path,
                    "source": source,
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                },
                user_id=user_id,
            )
            db.session.commit()
        except Exception as error:
            try:
                db.session.rollback()
            except Exception as rollback_error:
                print("BETA EVENT ROLLBACK ERROR:", type(rollback_error).__name__, rollback_error)
            print("BETA EVENT LOG ERROR:", type(error).__name__, error)

        return ("", 204)

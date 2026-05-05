from datetime import datetime, timezone

from flask import render_template, request, redirect, flash, session, url_for
from werkzeug.security import generate_password_hash


def register_auth_routes(app, deps):
    """Auth routes migrated from app.py.

    V1.06:
    - /login
    - /logout
    - /register
    - /confirm_email/<token> (legacy compatibility)
    - /resend-verification (legacy compatibility)
    - /forgot-password
    - /reset-password/<token>
    """

    User = deps["User"]
    BetaInvite = deps.get("BetaInvite")
    db = deps["db"]
    serializer = deps["serializer"]

    check_password_hash = deps["check_password_hash"]
    mark_user_login = deps["mark_user_login"]
    send_password_reset_email = deps["send_password_reset_email"]

    create_starter_deck_from_collection = deps.get("create_starter_deck_from_collection")

    def normalize_email_verification_state(user):
        if not user:
            return

        if not bool(getattr(user, "is_verified", False)):
            user.is_verified = True

        if getattr(user, "account_status", "active") in ["unverified", "pending_verification"]:
            user.account_status = "active"

        if not getattr(user, "verified_at", None):
            user.verified_at = datetime.now(timezone.utc)

    @app.route("/login", methods=["GET", "POST"], endpoint="login")
    def login_route():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            user = User.query.filter_by(email=email).first()

            if not user or not check_password_hash(user.password_hash, password):
                flash("Invalid email or password.")
                return redirect("/login")

            if getattr(user, "account_status", "active") == "banned":
                flash("This account is banned.")
                return redirect("/login")

            session["user_id"] = user.id

            try:
                normalize_email_verification_state(user)
                mark_user_login(user)
                db.session.commit()
            except Exception as error:
                print("LOGIN TRACKING ERROR:", type(error).__name__, error)
                db.session.rollback()

            try:
                if not getattr(user, "has_completed_onboarding", False):
                    return redirect("/welcome")
            except Exception as error:
                print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)

            return redirect("/")

        return render_template("login.html")

    @app.route("/logout", endpoint="logout")
    def logout_route():
        session.clear()
        return redirect("/")

    @app.route("/register", methods=["GET", "POST"], endpoint="register")
    def register_route():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "").strip()
            invite_code = request.form.get("invite_code", "").strip().upper()

            if not username or not email or not password:
                flash("Username, email and password are required.")
                return redirect("/register")

            if len(password) < 6:
                flash("Password must have at least 6 characters.")
                return redirect("/register")

            if User.query.filter_by(email=email).first():
                flash("Email already exists.")
                return redirect("/register")

            if User.query.filter_by(username=username).first():
                flash("Username already exists.")
                return redirect("/register")

            invite = None

            if BetaInvite and invite_code:
                invite = BetaInvite.query.filter_by(code=invite_code).first()

                if not invite:
                    flash("Invalid invite code.")
                    return redirect("/register")

                if not getattr(invite, "is_active", True):
                    flash("Invite code is not active.")
                    return redirect("/register")

                if getattr(invite, "max_uses", 0) and getattr(invite, "used_count", 0) >= getattr(invite, "max_uses", 0):
                    flash("Invite code has reached its limit.")
                    return redirect("/register")

            starter_collection = []
            starter_deck = []

            try:
                if create_starter_deck_from_collection:
                    starter_collection, starter_deck = create_starter_deck_from_collection()
            except Exception as error:
                print("STARTER DECK CREATE ERROR:", type(error).__name__, error)
                starter_collection = []
                starter_deck = []

            new_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                is_verified=True,
                verified_at=datetime.now(timezone.utc),
                account_status="active",
                coins=0,
                deck_json=starter_deck,
                collection_json=starter_collection,
                wins=0,
                losses=0,
                xp=0,
                level=1,
                is_admin=False,
                is_tester=bool(invite),
                has_completed_onboarding=False,
            )

            db.session.add(new_user)

            if invite:
                invite.used_count += 1

            db.session.commit()

            flash("Registered successfully. You can login and play now.")
            return redirect("/login")

        return render_template("register.html")

    @app.route("/confirm_email/<token>", endpoint="confirm_email")
    def confirm_email_route(token):
        try:
            email = serializer.loads(token, salt="email-confirm", max_age=3600)
        except Exception:
            return "Verification link expired."

        user = User.query.filter_by(email=email).first_or_404()

        normalize_email_verification_state(user)
        db.session.commit()

        flash("Email verification is disabled. You can login now.")
        return redirect("/login")

    @app.route("/resend-verification", methods=["GET", "POST"], endpoint="resend_verification")
    def resend_verification_route():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = User.query.filter_by(email=email).first()

            if user:
                normalize_email_verification_state(user)
                db.session.commit()

            flash("Email verification is disabled. You can login now.")
            return redirect("/login")

        flash("Email verification is disabled. You can login now.")
        return redirect("/login")

    @app.route("/forgot-password", methods=["GET", "POST"], endpoint="forgot_password")
    def forgot_password_route():
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

            return redirect("/login")

        return render_template("forgot_password.html")

    @app.route("/reset-password/<token>", methods=["GET", "POST"], endpoint="reset_password")
    def reset_password_route(token):
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

            user.password_hash = generate_password_hash(password)
            db.session.commit()

            flash("Password updated. You can login now.")
            return redirect("/login")

        return render_template("reset_password.html")

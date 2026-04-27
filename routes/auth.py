from flask import render_template, request, redirect, flash, session


def register_auth_routes(app, deps):
    """Auth routes migrated from app.py.

    V1.06 Bloco 1.2A:
    - /login
    - /logout
    """

    User = deps["User"]
    db = deps["db"]
    check_password_hash = deps["check_password_hash"]
    mark_user_login = deps["mark_user_login"]

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

            if not user.is_verified:
                flash("Please verify your email before logging in.")
                return redirect("/login")

            session["user_id"] = user.id

            try:
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

from flask import render_template, redirect


def register_public_routes(app, deps):
    """Public/support routes migrated from app.py.

    Migrated endpoints:
    - index
    - health
    - terms
    - privacy
    - how_to_play
    - ranking
    - welcome
    - complete_onboarding
    - match_history
    """

    current_user = deps["current_user"]
    login_required_redirect = deps["login_required_redirect"]
    db = deps["db"]
    User = deps["User"]
    MatchHistory = deps.get("MatchHistory")

    @app.route("/", endpoint="index")
    def index_route():
        user = current_user()
        return render_template("index.html", user=user)

    @app.route("/health", endpoint="health")
    def health_route():
        return {
            "status": "ok",
            "app": "Ambitionz",
            "version": "Ambitionz V1.06",
            "environment": app.config.get("ENVIRONMENT", "development"),
        }

    @app.route("/terms", endpoint="terms")
    def terms_route():
        return render_template("terms.html")

    @app.route("/privacy", endpoint="privacy")
    def privacy_route():
        return render_template("privacy.html")

    @app.route("/how-to-play", endpoint="how_to_play")
    def how_to_play_route():
        return render_template("how_to_play.html")

    @app.route("/ranking", endpoint="ranking")
    def ranking_route():
        try:
            users = (
                User.query
                .filter_by(is_verified=True)
                .order_by(User.wins.desc(), User.level.desc(), User.xp.desc())
                .limit(100)
                .all()
            )
        except Exception as error:
            print("Ranking query failed:", type(error).__name__, error)
            users = []

        return render_template("ranking.html", users=users)

    @app.route("/welcome", endpoint="welcome")
    def welcome_route():
        auth_redirect = login_required_redirect()

        if auth_redirect:
            return auth_redirect

        try:
            return render_template("welcome.html", user=current_user())
        except Exception as error:
            print("WELCOME RENDER ERROR:", type(error).__name__, error)
            return redirect("/")

    @app.route("/complete-onboarding", methods=["POST"], endpoint="complete_onboarding")
    def complete_onboarding_route():
        auth_redirect = login_required_redirect()

        if auth_redirect:
            return auth_redirect

        user = current_user()

        if user:
            try:
                user.has_completed_onboarding = True
                db.session.commit()
            except Exception as error:
                print("Complete onboarding failed:", type(error).__name__, error)
                db.session.rollback()

        return redirect("/training")

    @app.route("/match-history", endpoint="match_history")
    def match_history_route():
        auth_redirect = login_required_redirect()

        if auth_redirect:
            return auth_redirect

        matches = []

        try:
            if MatchHistory:
                matches = (
                    MatchHistory.query
                    .order_by(MatchHistory.id.desc())
                    .limit(50)
                    .all()
                )
        except Exception as error:
            print("Match history query failed:", type(error).__name__, error)
            matches = []

        return render_template("match_history.html", user=current_user(), matches=matches)

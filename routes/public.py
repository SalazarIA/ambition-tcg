from flask import render_template


def register_public_routes(app, deps):
    """Public/support routes migrated from app.py.

    V1.06:
    - /health
    - /terms
    - /privacy
    - /how-to-play
    - /ranking
    """

    User = deps["User"]

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

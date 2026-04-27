from flask import render_template


def register_public_routes(app, deps):
    """Public/support routes migrated from app.py.

    V1.06:
    - /health
    - /terms
    - /privacy
    """

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

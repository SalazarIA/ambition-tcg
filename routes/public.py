def register_public_routes(app, deps):
    """Public/support routes migrated from app.py.

    V1.06 Bloco 1.1A:
    - /health moved safely first.
    """

    @app.route("/health", endpoint="health")
    def health_route():
        return {
            "status": "ok",
            "app": "Ambitionz",
            "version": "Ambitionz V1.06",
            "environment": app.config.get("ENVIRONMENT", "development"),
        }

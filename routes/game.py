from flask import render_template, redirect, flash


def register_game_routes(app, deps):
    """Game page routes migrated from app.py.

    V1.06 Bloco 1.3A:
    - /arena
    - /training
    """

    current_user = deps["current_user"]
    login_required_redirect = deps["login_required_redirect"]
    deck_summary = deps.get("deck_summary")
    validate_deck = deps.get("validate_deck")

    def user_has_valid_deck(user):
        if not user:
            return False

        if not validate_deck:
            return True

        try:
            return bool(validate_deck(user.deck_json))
        except Exception as error:
            print("Deck validation failed:", type(error).__name__, error)
            return True

    @app.route("/arena", endpoint="arena")
    def arena_route():
        auth_redirect = login_required_redirect()

        if auth_redirect:
            return auth_redirect

        user = current_user()

        if not user_has_valid_deck(user):
            flash("Your deck is not valid yet. Please review your deck.")
            return redirect("/deck-builder")

        summary = None

        try:
            if deck_summary:
                summary = deck_summary(user.deck_json)
        except Exception as error:
            print("Arena deck summary failed:", type(error).__name__, error)

        return render_template(
            "arena.html",
            user=user,
            training_mode=False,
            deck_summary=summary,
        )

    @app.route("/training", endpoint="training")
    def training_route():
        auth_redirect = login_required_redirect()

        if auth_redirect:
            return auth_redirect

        user = current_user()

        summary = None

        try:
            if deck_summary:
                summary = deck_summary(user.deck_json)
        except Exception as error:
            print("Training deck summary failed:", type(error).__name__, error)

        return render_template(
            "arena.html",
            user=user,
            training_mode=True,
            deck_summary=summary,
        )

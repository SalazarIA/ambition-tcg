import json

from flask import render_template, redirect, flash, request


def safe_list(value):
    if isinstance(value, list):
        return value

    if not value:
        return []

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []

    return []


def register_game_routes(app, deps):
    """Game page routes migrated from app.py.

    V1.06:
    - /arena
    - /training
    - /collection
    - /deck-builder
    - /shop
    - /booster-history
    """

    current_user = deps["current_user"]
    login_required_redirect = deps["login_required_redirect"]

    db = deps["db"]

    CARD_CATALOG = deps.get("CARD_CATALOG", [])
    BoosterHistory = deps.get("BoosterHistory")

    deck_summary = deps.get("deck_summary")
    validate_deck = deps.get("validate_deck")
    full_deck_analysis = deps.get("full_deck_analysis")
    create_starter_deck_from_collection = deps.get("create_starter_deck_from_collection")

    def catalog_by_id():
        return {card.get("id"): card for card in CARD_CATALOG if isinstance(card, dict)}

    def user_collection_ids(user):
        return safe_list(getattr(user, "collection_json", []))

    def user_deck_ids(user):
        return safe_list(getattr(user, "deck_json", []))

    def user_collection_cards(user):
        by_id = catalog_by_id()
        return [by_id.get(card_id) for card_id in user_collection_ids(user) if by_id.get(card_id)]

    def user_deck_cards(user):
        by_id = catalog_by_id()
        return [by_id.get(card_id) for card_id in user_deck_ids(user) if by_id.get(card_id)]

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

    @app.route("/collection", endpoint="collection")
    def collection_route():
        auth_redirect = login_required_redirect()

        if auth_redirect:
            return auth_redirect

        user = current_user()
        collection_ids = user_collection_ids(user)
        collection_cards = user_collection_cards(user)

        return render_template(
            "collection.html",
            user=user,
            collection_ids=collection_ids,
            collection=collection_cards,
            collection_cards=collection_cards,
            cards=collection_cards,
            catalog=CARD_CATALOG,
        )

    @app.route("/deck-builder", methods=["GET", "POST"], endpoint="deck_builder")
    def deck_builder_route():
        auth_redirect = login_required_redirect()

        if auth_redirect:
            return auth_redirect

        user = current_user()

        if request.method == "POST":
            selected_ids = []

            selected_ids.extend(request.form.getlist("deck"))
            selected_ids.extend(request.form.getlist("deck[]"))
            selected_ids.extend(request.form.getlist("card_ids"))
            selected_ids.extend(request.form.getlist("card_ids[]"))

            raw_deck = request.form.get("deck_json", "").strip()

            if raw_deck:
                try:
                    parsed = json.loads(raw_deck)
                    if isinstance(parsed, list):
                        selected_ids.extend([str(item) for item in parsed])
                except Exception as error:
                    print("Deck JSON parse failed:", type(error).__name__, error)

            selected_ids = [str(card_id).strip() for card_id in selected_ids if str(card_id).strip()]

            if selected_ids:
                try:
                    user.deck_json = selected_ids
                    db.session.commit()
                    flash("Deck saved.")
                except Exception as error:
                    print("Deck save failed:", type(error).__name__, error)
                    db.session.rollback()
                    flash("Deck save failed.")
            else:
                flash("No deck changes detected.")

            return redirect("/deck-builder")

        collection_ids = user_collection_ids(user)
        deck_ids = user_deck_ids(user)
        collection_cards = user_collection_cards(user)
        deck_cards = user_deck_cards(user)

        summary = None
        analysis = None
        is_valid = True

        try:
            if deck_summary:
                summary = deck_summary(deck_ids)
        except Exception as error:
            print("Deck summary failed:", type(error).__name__, error)

        try:
            if full_deck_analysis:
                analysis = full_deck_analysis(deck_ids)
        except Exception as error:
            print("Deck analysis failed:", type(error).__name__, error)

        try:
            if validate_deck:
                is_valid = bool(validate_deck(deck_ids))
        except Exception as error:
            print("Deck validation failed:", type(error).__name__, error)

        return render_template(
            "deck_builder.html",
            user=user,
            collection_ids=collection_ids,
            deck_ids=deck_ids,
            collection=collection_cards,
            collection_cards=collection_cards,
            deck=deck_cards,
            deck_cards=deck_cards,
            catalog=CARD_CATALOG,
            deck_summary=summary,
            deck_analysis=analysis,
            is_valid_deck=is_valid,
        )

    @app.route("/shop", endpoint="shop")
    def shop_route():
        auth_redirect = login_required_redirect()

        if auth_redirect:
            return auth_redirect

        user = current_user()

        return render_template(
            "shop.html",
            user=user,
            coins=getattr(user, "coins", 0),
        )

    @app.route("/booster-history", endpoint="booster_history")
    def booster_history_route():
        auth_redirect = login_required_redirect()

        if auth_redirect:
            return auth_redirect

        user = current_user()
        history = []

        try:
            if BoosterHistory:
                history = (
                    BoosterHistory.query
                    .filter_by(user_id=user.id)
                    .order_by(BoosterHistory.id.desc())
                    .limit(100)
                    .all()
                )
        except Exception as error:
            print("Booster history failed:", type(error).__name__, error)
            history = []

        return render_template(
            "booster_history.html",
            user=user,
            history=history,
            booster_history=history,
        )

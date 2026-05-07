
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _safe_len(value):
    try:
        return len(value or [])
    except Exception:
        return 0


def run_deck_inventory_flow():
    logs = []
    failures = []

    try:
        from app import app
        from models import User
        from game.deck import load_card_ids, build_playable_deck, validate_deck, full_deck_analysis
        from game.cards import CARD_CATALOG
        from services.economy.deck_inventory import (
            owned_card_ids_for_user,
            build_auto_deck_from_inventory,
            validate_deck_against_inventory,
        )
        from services.economy.inventory_cards import (
            build_collection_from_inventory,
            user_inventory_counts,
        )

        catalog_ids = {
            str(card.get("id") or card.get("card_id") or card.get("name"))
            for card in CARD_CATALOG
        }

        with app.app_context():
            user = User.query.first()

            if not user:
                failures.append("No local user found.")
                return {
                    "name": "deck_inventory_flow",
                    "status": "FAIL",
                    "error": "; ".join(failures),
                    "logs": logs,
                }

            logs.append(f"user: id={user.id} username={user.username}")

            owned_with_fallback = owned_card_ids_for_user(user)
            owned_real = owned_card_ids_for_user(user, include_legacy_fallback=False)
            inventory_counts = user_inventory_counts(user)
            collection_cards = build_collection_from_inventory(user, include_zero=False)

            logs.append(f"owned_with_fallback={len(owned_with_fallback)}")
            logs.append(f"owned_real_inventory={len(owned_real)}")
            logs.append(f"inventory_unique_cards={len(inventory_counts)}")
            logs.append(f"collection_cards_from_inventory={len(collection_cards)}")

            if len(owned_with_fallback) <= 0:
                failures.append("User has no owned cards even with fallback.")

            if len(owned_real) <= 0:
                failures.append("User has no real inventory ownership cards.")

            if len(inventory_counts) <= 0:
                failures.append("Inventory counts are empty.")

            if len(collection_cards) <= 0:
                failures.append("Collection from inventory is empty.")

            deck_ids = load_card_ids(user.deck_json)
            logs.append(f"saved_deck_size={len(deck_ids)}")
            logs.append(f"saved_deck_first_10={deck_ids[:10]}")

            if len(deck_ids) != 30:
                failures.append(f"Saved deck must have 30 cards, got {len(deck_ids)}.")

            missing_catalog = [cid for cid in deck_ids if str(cid) not in catalog_ids]
            logs.append(f"missing_catalog_cards={missing_catalog[:20]} count={len(missing_catalog)}")

            if missing_catalog:
                failures.append(f"Saved deck has missing catalog card ids: {missing_catalog[:10]}")

            playable_saved = build_playable_deck(deck_ids)
            logs.append(f"playable_saved_size={len(playable_saved)}")

            if len(playable_saved) != 30:
                failures.append(f"build_playable_deck(saved deck) should return 30 cards, got {len(playable_saved)}.")

            inventory_validation = validate_deck_against_inventory(user, deck_ids)
            logs.append(f"validate_deck_against_inventory={inventory_validation}")

            if isinstance(inventory_validation, dict):
                if not inventory_validation.get("valid", False):
                    failures.append(f"Saved deck invalid against inventory: {inventory_validation}")
            elif isinstance(inventory_validation, tuple):
                if inventory_validation and inventory_validation[0] is False:
                    failures.append(f"Saved deck invalid against inventory: {inventory_validation}")
            elif inventory_validation is False:
                failures.append("Saved deck invalid against inventory.")

            try:
                rules_errors = validate_deck(deck_ids, owned_with_fallback)
                logs.append(f"validate_deck_errors={rules_errors}")
                if rules_errors:
                    failures.append(f"Saved deck rule errors: {rules_errors[:5] if isinstance(rules_errors, list) else rules_errors}")
            except TypeError as exc:
                failures.append(f"validate_deck signature/type error: {type(exc).__name__}: {exc}")

            try:
                analysis = full_deck_analysis(deck_ids)
                logs.append(f"full_deck_analysis={analysis}")
            except Exception as exc:
                failures.append(f"full_deck_analysis failed: {type(exc).__name__}: {exc}")

            auto_deck = build_auto_deck_from_inventory(user)
            logs.append(f"auto_deck_size={len(auto_deck)}")
            logs.append(f"auto_deck_first_10={auto_deck[:10]}")

            if len(auto_deck) != 30:
                failures.append(f"Auto deck should have 30 cards, got {len(auto_deck)}.")

            playable_auto = build_playable_deck(auto_deck)
            logs.append(f"playable_auto_size={len(playable_auto)}")

            if len(playable_auto) != 30:
                failures.append(f"build_playable_deck(auto deck) should return 30 cards, got {len(playable_auto)}.")

            auto_missing_catalog = [cid for cid in auto_deck if str(cid) not in catalog_ids]
            logs.append(f"auto_missing_catalog_cards={auto_missing_catalog[:20]} count={len(auto_missing_catalog)}")

            if auto_missing_catalog:
                failures.append(f"Auto deck has missing catalog card ids: {auto_missing_catalog[:10]}")

            auto_inventory_validation = validate_deck_against_inventory(user, auto_deck)
            logs.append(f"auto_validate_deck_against_inventory={auto_inventory_validation}")

            client = app.test_client()

            route_paths = [
                "/inventory",
                "/collection",
                "/deck-builder",
            ]

            logs.append("")
            logs.append("route_audit:")

            for path in route_paths:
                response = client.get(path)
                logs.append(f"{path}: status={response.status_code} content_type={response.content_type} location={response.headers.get('Location')}")

                if response.status_code >= 500:
                    failures.append(f"{path} returned {response.status_code}")

                if response.status_code not in (200, 302, 401, 403):
                    failures.append(f"{path} unexpected status {response.status_code}")

        status = "FAIL" if failures else "PASS"

        return {
            "name": "deck_inventory_flow",
            "status": status,
            "error": "; ".join(failures) if failures else None,
            "logs": logs,
        }

    except Exception as exc:
        return {
            "name": "deck_inventory_flow",
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "logs": logs,
        }

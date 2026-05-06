from collections import Counter
import json

from game.cards import CARD_CATALOG
from game.deck import load_card_ids, create_starter_deck_from_collection
from models import db
from services.economy.inventory_ownership import grant_card, get_quantity


def valid_card_ids():
    ids = set()

    for card in CARD_CATALOG:
        card_id = str(card.get("id") or card.get("card_id") or card.get("name") or "").strip()

        if card_id:
            ids.add(card_id)

    return ids


def legacy_collection_ids(user):
    if not user:
        return []

    raw = getattr(user, "collection_json", None)

    if not raw:
        return []

    try:
        return [str(card_id) for card_id in load_card_ids(raw)]
    except Exception:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(card_id) for card_id in parsed]
        except Exception:
            return []

    return []


def migrate_legacy_collection_to_inventory(user, source="legacy_collection_migration"):
    if not user:
        return {
            "ok": False,
            "message": "Invalid user.",
            "posted": 0,
            "duplicates": 0,
            "invalid": 0,
        }

    allowed_ids = valid_card_ids()
    ids = legacy_collection_ids(user)
    counts = Counter(ids)

    posted = 0
    duplicates = 0
    invalid = 0
    details = []

    for card_id, quantity in counts.items():
        if card_id not in allowed_ids:
            invalid += quantity
            continue

        current = get_quantity(user.id, "card", card_id)

        if current >= quantity:
            duplicates += quantity
            continue

        delta = quantity - current

        ok, payload = grant_card(
            user=user,
            card_id=card_id,
            quantity=delta,
            source=source,
            idempotency_key=f"{source}-{user.id}-{card_id}-{quantity}",
            metadata={
                "reason": "migrate_collection_json_to_inventory",
                "legacy_quantity": quantity,
                "current_quantity": current,
                "delta": delta,
            },
        )

        if ok and payload.get("posted"):
            posted += delta
            details.append(payload)
        elif ok and payload.get("duplicate"):
            duplicates += delta
        else:
            invalid += delta

    return {
        "ok": True,
        "message": f"Migration complete: {posted} card copies posted, {duplicates} already present, {invalid} invalid.",
        "posted": posted,
        "duplicates": duplicates,
        "invalid": invalid,
        "details": details,
    }


def ensure_user_has_playable_inventory(user, source="starter_inventory_recovery"):
    if not user:
        return {
            "ok": False,
            "message": "Invalid user.",
            "posted": 0,
        }

    migration = migrate_legacy_collection_to_inventory(user)

    owned_ids = legacy_collection_ids(user)

    if migration.get("posted", 0) > 0 or migration.get("duplicates", 0) > 0:
        return {
            "ok": True,
            "message": "Legacy collection migrated or already present.",
            "posted": migration.get("posted", 0),
            "migration": migration,
        }

    # Conservative fallback: if no legacy collection exists, use the first valid cards
    # through the existing starter deck builder path.
    all_ids = list(valid_card_ids())
    starter_ids = create_starter_deck_from_collection(all_ids)

    posted = 0

    for index, card_id in enumerate(starter_ids):
        ok, payload = grant_card(
            user=user,
            card_id=card_id,
            quantity=1,
            source=source,
            idempotency_key=f"{source}-{user.id}-{index}-{card_id}",
            metadata={
                "reason": "first_login_playable_inventory_recovery",
            },
        )

        if ok and payload.get("posted"):
            posted += 1

    return {
        "ok": True,
        "message": f"Starter inventory recovery complete: {posted} card copies posted.",
        "posted": posted,
        "migration": migration,
    }


def repair_user_inventory_and_deck(user):
    result = ensure_user_has_playable_inventory(user)

    try:
        from services.economy.deck_inventory import build_auto_deck_from_inventory

        deck = build_auto_deck_from_inventory(user)

        if deck:
            user.deck_json = json.dumps(deck)

        db.session.commit()

        result["deck_size"] = len(deck)
        result["deck_repaired"] = bool(deck)
        return result

    except Exception as error:
        db.session.rollback()
        result["deck_repaired"] = False
        result["error"] = str(error)
        return result

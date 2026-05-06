from collections import Counter

from game.deck import create_starter_deck_from_collection, load_card_ids
from services.economy.inventory_cards import user_inventory_counts


def owned_card_ids_for_user(user, include_legacy_fallback=True):
    if not user:
        return []

    counts = user_inventory_counts(user)
    owned_ids = []

    for card_id, quantity in counts.items():
        owned_ids.extend([str(card_id)] * int(quantity or 0))

    if owned_ids or not include_legacy_fallback:
        return owned_ids

    legacy_json = getattr(user, "collection_json", None)

    if legacy_json:
        return load_card_ids(legacy_json)

    return []


def inventory_has_cards(user):
    return len(owned_card_ids_for_user(user, include_legacy_fallback=False)) > 0


def validate_deck_against_inventory(user, deck_ids):
    if not user:
        return ["Invalid user inventory."]

    owned_ids = owned_card_ids_for_user(user, include_legacy_fallback=True)

    if not owned_ids:
        return ["You do not own cards yet. Open boosters first."]

    owned = Counter(str(card_id) for card_id in owned_ids)
    deck = Counter(str(card_id) for card_id in deck_ids)

    errors = []

    for card_id, used_quantity in deck.items():
        owned_quantity = owned.get(card_id, 0)

        if used_quantity > owned_quantity:
            errors.append(
                f"Card {card_id} uses {used_quantity} copy/copies but inventory owns {owned_quantity}."
            )

    return errors


def build_auto_deck_from_inventory(user):
    owned_ids = owned_card_ids_for_user(user, include_legacy_fallback=True)
    return create_starter_deck_from_collection(owned_ids)

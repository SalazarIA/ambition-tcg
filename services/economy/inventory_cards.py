from collections import Counter

from game.cards import CARD_CATALOG
from game.card_view import enrich_cards_for_view
from models import InventoryOwnership


def normalize_card_id(card):
    return str(card.get("id") or card.get("card_id") or card.get("name") or "")


def card_catalog_by_id():
    mapping = {}
    for card in CARD_CATALOG:
        cid = normalize_card_id(card)
        if cid:
            mapping[cid] = card
    return mapping


def user_inventory_counts(user):
    if not user:
        return Counter()

    rows = InventoryOwnership.query.filter_by(
        user_id=user.id,
        item_type="card",
    ).all()

    counts = Counter()

    for row in rows:
        quantity = int(row.quantity or 0)

        if quantity > 0:
            counts[str(row.item_id)] += quantity

    return counts


def build_collection_from_inventory(user, include_zero=False):
    counts = user_inventory_counts(user)
    catalog = card_catalog_by_id()
    cards = []

    for cid, base_card in catalog.items():
        count = int(counts.get(cid, 0))

        if not include_zero and count <= 0:
            continue

        card = dict(base_card)
        card["id"] = cid
        card["count"] = count
        card["owned"] = count > 0
        cards.append(card)

    return enrich_cards_for_view(cards)

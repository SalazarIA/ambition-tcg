# =========================================================
# Ambitionz Starter Deck V1
# Balanced 30-card beta starter deck.
# Current base set has many Finishers/Balancers, so this selector
# prioritizes playable curve and role diversity.
# =========================================================

from copy import deepcopy
from collections import Counter

from game.cards import CARD_CATALOG


TARGET_DECK_SIZE = 30
TARGET_TYPES = {
    "Monster": 21,
    "Spell": 6,
    "Trap": 3,
}

PREFERRED_ROLE_ORDER = [
    "Aggressor",
    "Defender",
    "Controller",
    "Balancer",
    "Finisher",
]

PREFERRED_CURVE = {
    1: 8,
    2: 8,
    3: 6,
    4: 4,
    5: 3,
    6: 1,
}


def card_type(card):
    return str(card.get("type") or "Monster")


def card_role(card):
    return str(card.get("role") or "Balancer")


def card_cost(card):
    try:
        return int(card.get("cost") or card.get("energy_cost") or 1)
    except Exception:
        return 1


def card_power(card):
    try:
        return int(card.get("attack") or card.get("power") or card.get("value") or card_cost(card) or 1)
    except Exception:
        return 1


def card_id(card):
    return str(card.get("id") or card.get("card_id") or card.get("name") or "")


def sort_score(card):
    ctype = card_type(card)
    role = card_role(card)
    cost = card_cost(card)
    power = card_power(card)

    type_bias = {
        "Monster": 0,
        "Spell": 10,
        "Trap": 20,
    }.get(ctype, 30)

    role_bias = PREFERRED_ROLE_ORDER.index(role) if role in PREFERRED_ROLE_ORDER else 9

    # Prefer playable early-mid curve, then useful power.
    curve_bias = abs(cost - 2) * 2

    return (
        type_bias,
        curve_bias,
        role_bias,
        cost,
        -power,
        str(card.get("name") or ""),
    )


def quota_available(deck, card):
    counts = Counter(card_type(c) for c in deck)
    return counts[card_type(card)] < TARGET_TYPES.get(card_type(card), 0)


def select_by_type(cards, ctype, amount):
    pool = [deepcopy(card) for card in cards if card_type(card) == ctype]
    pool.sort(key=sort_score)

    selected = []
    used_names = set()

    # Pass 1: prefer non-Finisher where possible.
    for card in pool:
        if len(selected) >= amount:
            break

        name = str(card.get("name") or card_id(card))

        if name in used_names:
            continue

        if ctype == "Monster" and card_role(card) == "Finisher" and len(selected) < max(12, amount - 5):
            continue

        selected.append(card)
        used_names.add(name)

    # Pass 2: fill remaining.
    for card in pool:
        if len(selected) >= amount:
            break

        name = str(card.get("name") or card_id(card))

        if name in used_names:
            continue

        selected.append(card)
        used_names.add(name)

    return selected[:amount]


def rebalance_curve(deck):
    deck = list(deck)

    def curve_counts():
        return Counter(min(6, max(1, card_cost(card))) for card in deck)

    # Simple safety: if too many high-cost cards, swap with lower-cost cards from catalog.
    counts = curve_counts()
    high_count = sum(v for k, v in counts.items() if k >= 5)

    if high_count <= 4:
        return deck

    low_pool = [
        deepcopy(card)
        for card in CARD_CATALOG
        if card_type(card) == "Monster" and card_cost(card) <= 2
    ]
    low_pool.sort(key=sort_score)

    used = {str(card.get("name") or card_id(card)) for card in deck}

    for i, card in enumerate(list(deck)):
        if high_count <= 4:
            break

        if card_type(card) != "Monster" or card_cost(card) < 5:
            continue

        replacement = None

        for candidate in low_pool:
            name = str(candidate.get("name") or card_id(candidate))

            if name not in used:
                replacement = candidate
                break

        if replacement:
            old_name = str(card.get("name") or card_id(card))
            used.discard(old_name)
            used.add(str(replacement.get("name") or card_id(replacement)))
            deck[i] = replacement
            high_count -= 1

    return deck


def build_balanced_starter_deck():
    monsters = select_by_type(CARD_CATALOG, "Monster", TARGET_TYPES["Monster"])
    spells = select_by_type(CARD_CATALOG, "Spell", TARGET_TYPES["Spell"])
    traps = select_by_type(CARD_CATALOG, "Trap", TARGET_TYPES["Trap"])

    deck = monsters + spells + traps
    deck = rebalance_curve(deck)

    return deck[:TARGET_DECK_SIZE]


def analyze_starter_deck(deck):
    return {
        "total": len(deck),
        "types": dict(Counter(card_type(card) for card in deck)),
        "roles": dict(Counter(card_role(card) for card in deck)),
        "curve": dict(Counter(min(6, max(1, card_cost(card))) for card in deck)),
        "avg_cost": round(sum(card_cost(card) for card in deck) / max(1, len(deck)), 2),
        "monster_count": sum(1 for card in deck if card_type(card) == "Monster"),
        "spell_count": sum(1 for card in deck if card_type(card) == "Spell"),
        "trap_count": sum(1 for card in deck if card_type(card) == "Trap"),
    }


def validate_starter_deck(deck):
    analysis = analyze_starter_deck(deck)
    errors = []

    if analysis["total"] != TARGET_DECK_SIZE:
        errors.append(f"Expected {TARGET_DECK_SIZE} cards, got {analysis['total']}.")

    for ctype, target in TARGET_TYPES.items():
        got = analysis["types"].get(ctype, 0)

        if got != target:
            errors.append(f"Expected {target} {ctype}, got {got}.")

    if analysis["avg_cost"] > 3.35:
        errors.append(f"Average cost too high: {analysis['avg_cost']}.")

    if analysis["curve"].get(1, 0) + analysis["curve"].get(2, 0) < 8:
        errors.append("Not enough early cards cost 1-2.")

    return errors, analysis

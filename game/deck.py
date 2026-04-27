import json
import random
from collections import Counter

from game.cards import (
    CARD_CATALOG,
    ELEMENTS,
    get_card_by_id,
    get_monsters,
    get_spells,
    get_traps,
)


STARTER_DECK_SIZE = 30

STARTER_MONSTER_COUNT = 21
STARTER_SPELL_COUNT = 6
STARTER_TRAP_COUNT = 3


DECK_RULES = {
    "exact_cards": 30,
    "max_copies": 3,
    "exact_monsters": 21,
    "exact_spells": 6,
    "exact_traps": 3,
}


# =========================================================
# AMBITIONZ V1.08 — RANDOM STARTER DECK RULES
# =========================================================

STARTER_DECK_MONSTER_RATIO = 0.70
STARTER_DECK_SPELL_RATIO = 0.20
STARTER_DECK_TRAP_RATIO = 0.10


def get_fixed_starter_deck_ids():
    """Compatibility helper for reports.

    The starter deck is intentionally generated from the beta starter rules.
    It returns one valid 30-card sample deck:
    - 21 monsters
    - 6 spells
    - 3 traps
    - monsters distributed across Fire, Water, Earth and Plant
    """
    return load_card_ids(create_starter_deck())


def get_fixed_starter_collection_ids():
    """Compatibility helper for reports and tools."""
    return load_card_ids(create_starter_collection())


def validate_fixed_starter_deck_catalog():
    missing = []

    for card_id in get_fixed_starter_deck_ids():
        if not get_card_by_id(card_id):
            missing.append(card_id)

    return missing


def load_card_ids(json_text):
    try:
        data = json.loads(json_text or "[]")

        if isinstance(data, list):
            return data

        return []
    except Exception:
        return []


def cards_from_ids(card_ids):
    cards = []

    for card_id in card_ids:
        card = get_card_by_id(card_id)

        if card:
            cards.append(card)

    return cards


def choose_cards_with_duplicates(pool, amount):
    if not pool:
        return []

    selected = []

    while len(selected) < amount:
        card = random.choice(pool)
        selected.append(card["id"])

    return selected


def choose_unique_cards(pool, amount):
    if amount >= len(pool):
        return [card["id"] for card in pool]

    return [card["id"] for card in random.sample(pool, amount)]


def create_starter_collection():
    collection_ids = []

    monsters = get_monsters()
    spells = get_spells()
    traps = get_traps()

    for element in ELEMENTS:
        element_monsters = [card for card in monsters if card["element"] == element]
        common_pool = [card for card in element_monsters if card["rarity"] == "Common"]
        uncommon_pool = [card for card in element_monsters if card["rarity"] == "Uncommon"]

        collection_ids.extend(choose_unique_cards(common_pool, 14))
        collection_ids.extend(choose_unique_cards(uncommon_pool, 4))

    common_spells = [card for card in spells if card["rarity"] == "Common"]
    uncommon_spells = [card for card in spells if card["rarity"] == "Uncommon"]

    collection_ids.extend(choose_unique_cards(common_spells, 9))
    collection_ids.extend(choose_unique_cards(uncommon_spells, 3))

    common_traps = [card for card in traps if card["rarity"] == "Common"]
    uncommon_traps = [card for card in traps if card["rarity"] == "Uncommon"]

    collection_ids.extend(choose_unique_cards(common_traps, 6))
    collection_ids.extend(choose_unique_cards(uncommon_traps, 2))

    return json.dumps(collection_ids)


def create_starter_deck_from_collection(collection_ids):
    collection_cards = cards_from_ids(collection_ids)

    monsters = [card for card in collection_cards if card["type"] == "Monster"]
    spells = [card for card in collection_cards if card["type"] == "Spell"]
    traps = [card for card in collection_cards if card["type"] == "Trap"]

    deck_ids = []

    valid_elements = ["Fire", "Water", "Earth", "Plant"]
    monsters_by_element = {
        element: [card for card in monsters if card["element"] == element]
        for element in valid_elements
    }

    base_per_element = STARTER_MONSTER_COUNT // len(valid_elements)
    remainder = STARTER_MONSTER_COUNT % len(valid_elements)

    for index, element in enumerate(valid_elements):
        amount = base_per_element

        if index < remainder:
            amount += 1

        pool = monsters_by_element[element]

        if len(pool) >= amount:
            deck_ids.extend(choose_unique_cards(pool, amount))
        else:
            deck_ids.extend([card["id"] for card in pool])
            deck_ids.extend(choose_cards_with_duplicates(pool, amount - len(pool)))

    if len(spells) >= STARTER_SPELL_COUNT:
        deck_ids.extend(choose_unique_cards(spells, STARTER_SPELL_COUNT))
    else:
        deck_ids.extend([card["id"] for card in spells])
        deck_ids.extend(choose_cards_with_duplicates(spells, STARTER_SPELL_COUNT - len(spells)))

    if len(traps) >= STARTER_TRAP_COUNT:
        deck_ids.extend(choose_unique_cards(traps, STARTER_TRAP_COUNT))
    else:
        deck_ids.extend([card["id"] for card in traps])
        deck_ids.extend(choose_cards_with_duplicates(traps, STARTER_TRAP_COUNT - len(traps)))

    random.shuffle(deck_ids)

    return json.dumps(deck_ids)


def create_starter_deck():
    collection_ids = load_card_ids(create_starter_collection())
    return create_starter_deck_from_collection(collection_ids)


def create_new_player_card_data():
    collection_ids = load_card_ids(create_starter_collection())
    deck_json = create_starter_deck_from_collection(collection_ids)

    return {
        "collection_json": json.dumps(collection_ids),
        "deck_json": deck_json,
    }


def build_playable_deck(deck_json):
    deck_ids = load_card_ids(deck_json)
    deck = cards_from_ids(deck_ids)
    random.shuffle(deck)
    return deck


def draw_starting_hand(deck, amount=5):
    hand = []

    for _ in range(amount):
        if deck:
            hand.append(deck.pop(0))

    return hand


def draw_card(player):
    if len(player["deck"]) <= 0:
        player["hp"] -= 300
        return None

    card = player["deck"].pop(0)
    player["hand"].append(card)
    return card


def count_types(deck_ids):
    counts = {
        "Monster": 0,
        "Spell": 0,
        "Trap": 0,
    }

    for card_id in deck_ids:
        card = get_card_by_id(card_id)

        if card:
            counts[card["type"]] += 1

    return counts


def validate_deck(deck_ids, collection_ids):
    errors = []

    if len(deck_ids) != DECK_RULES["exact_cards"]:
        errors.append(f"Beta deck must have exactly {DECK_RULES['exact_cards']} cards.")

    deck_counter = Counter(deck_ids)
    collection_counter = Counter(collection_ids)

    for card_id, amount in deck_counter.items():
        if amount > DECK_RULES["max_copies"]:
            card = get_card_by_id(card_id)
            name = card["name"] if card else card_id
            errors.append(f"{name} exceeds max copies: {DECK_RULES['max_copies']}.")

        if amount > collection_counter.get(card_id, 0):
            card = get_card_by_id(card_id)
            name = card["name"] if card else card_id
            errors.append(f"You do not own enough copies of {name}.")

    for card_id in deck_ids:
        if not get_card_by_id(card_id):
            errors.append(f"Invalid card ID: {card_id}")

    type_counts = count_types(deck_ids)

    if type_counts["Monster"] != DECK_RULES["exact_monsters"]:
        errors.append(f"Beta deck must have exactly {DECK_RULES['exact_monsters']} monsters.")

    if type_counts["Spell"] != DECK_RULES["exact_spells"]:
        errors.append(f"Beta deck must have exactly {DECK_RULES['exact_spells']} spells.")

    if type_counts["Trap"] != DECK_RULES["exact_traps"]:
        errors.append(f"Beta deck must have exactly {DECK_RULES['exact_traps']} traps.")

    return errors


def collection_summary(collection_ids):
    counter = Counter(collection_ids)
    summary = []

    for card in CARD_CATALOG:
        owned = counter.get(card["id"], 0)

        summary.append({
            **card,
            "owned": owned,
        })

    return summary


def deck_summary(deck_ids):
    counter = Counter(deck_ids)
    summary = []

    for card_id, amount in counter.items():
        card = get_card_by_id(card_id)

        if card:
            summary.append({
                **card,
                "amount": amount,
            })

    return summary


def starter_deck_stats(deck_ids):
    counts = count_types(deck_ids)
    total = len(deck_ids) or 1

    return {
        "total": len(deck_ids),
        "monsters": counts["Monster"],
        "spells": counts["Spell"],
        "traps": counts["Trap"],
        "monster_percent": round((counts["Monster"] / total) * 100, 2),
        "spell_percent": round((counts["Spell"] / total) * 100, 2),
        "trap_percent": round((counts["Trap"] / total) * 100, 2),
    }


# === AMBITION REWORK 10/11 DECK ANALYTICS ===

def deck_energy_curve(deck_ids):
    curve = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        "6+": 0,
    }

    total_cost = 0
    valid_cards = 0

    for card_id in deck_ids:
        card = get_card_by_id(card_id)

        if not card:
            continue

        cost = int(card.get("cost", 1))
        total_cost += cost
        valid_cards += 1

        if cost <= 1:
            curve[1] += 1
        elif cost == 2:
            curve[2] += 1
        elif cost == 3:
            curve[3] += 1
        elif cost == 4:
            curve[4] += 1
        elif cost == 5:
            curve[5] += 1
        else:
            curve["6+"] += 1

    average_cost = 0

    if valid_cards > 0:
        average_cost = round(total_cost / valid_cards, 2)

    return {
        "curve": curve,
        "average_cost": average_cost,
    }


def deck_element_counts(deck_ids):
    counts = {}

    for card_id in deck_ids:
        card = get_card_by_id(card_id)

        if not card:
            continue

        element = card.get("element", "Global")
        counts[element] = counts.get(element, 0) + 1

    return counts


def full_deck_analysis(deck_ids):
    stats = starter_deck_stats(deck_ids)
    energy = deck_energy_curve(deck_ids)
    elements = deck_element_counts(deck_ids)

    warnings = []

    if stats["total"] != 30:
        warnings.append("Deck must have exactly 30 cards.")

    if stats["monsters"] != 21:
        warnings.append("Beta deck should have exactly 21 monsters.")

    if stats["spells"] != 6:
        warnings.append("Beta deck should have exactly 6 spells.")

    if stats["traps"] != 3:
        warnings.append("Beta deck should have exactly 3 traps.")

    if energy["average_cost"] > 3.2:
        warnings.append("Average cost is high. The deck may feel slow in early rounds.")

    if energy["curve"][1] + energy["curve"][2] < 12:
        warnings.append("Low early-game count. Add more cost 1-2 cards.")

    return {
        "stats": stats,
        "energy": energy,
        "elements": elements,
        "warnings": warnings,
    }

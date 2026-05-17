"""Canonical card catalog for Ambitionz Ascension Duel.

The Ascension card layer is intentionally independent from the legacy lane
catalog. Cards are small dictionaries because the existing backend stores and
serializes gameplay state as JSON-like structures.
"""

from __future__ import annotations

import copy
import random
from collections import Counter


CARD_TYPES = ("champion", "technique", "relic", "scheme", "ascension")

STARTER_COUNTS = {
    "champion": 11,
    "technique": 9,
    "relic": 4,
    "scheme": 4,
    "ascension": 2,
}

REQUIRED_CARD_FIELDS = {
    "id",
    "name",
    "type",
    "rarity",
    "faction",
    "text",
    "modes",
    "resolve",
}


ASCENSION_CATALOG = [
    {
        "id": "ember_vowbound",
        "name": "Ember Vowbound",
        "type": "champion",
        "rarity": "common",
        "faction": "Ember Court",
        "text": "A pledged duelist who turns every promise into pressure.",
        "modes": ["summon", "bind", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "hp": 8,
            "pressure": 3,
            "guard": 1,
            "soul_bonus": {"Strike": {"pressure": 1}, "Focus": {"ambition": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "glass_tyrant",
        "name": "Glass Tyrant",
        "type": "champion",
        "rarity": "rare",
        "faction": "Mirror Choir",
        "text": "Fragile authority. Terrible when believed.",
        "modes": ["summon", "bind", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "hp": 6,
            "pressure": 4,
            "guard": 0,
            "soul_bonus": {"Strike": {"pressure": 2}, "Scheme": {"pressure": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "crownless_warden",
        "name": "Crownless Warden",
        "type": "champion",
        "rarity": "common",
        "faction": "Iron Choir",
        "text": "Keeps the gate after the throne has vanished.",
        "modes": ["summon", "bind", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "hp": 10,
            "pressure": 2,
            "guard": 3,
            "soul_bonus": {"Guard": {"guard": 2}, "Focus": {"ambition": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "hollow_orchard",
        "name": "Hollow Orchard",
        "type": "champion",
        "rarity": "uncommon",
        "faction": "Verdant Pact",
        "text": "A living grove with a person-shaped absence at its center.",
        "modes": ["summon", "bind", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "hp": 9,
            "pressure": 2,
            "guard": 2,
            "soul_bonus": {"Guard": {"heal": 1}, "Focus": {"draw": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "velvet_martyr",
        "name": "Velvet Martyr",
        "type": "champion",
        "rarity": "uncommon",
        "faction": "Velvet Accord",
        "text": "Loses beautifully, then makes the loss contagious.",
        "modes": ["summon", "bind", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "hp": 7,
            "pressure": 3,
            "guard": 1,
            "soul_bonus": {"Scheme": {"pressure": 2}, "Guard": {"ambition": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "sunken_oathbearer",
        "name": "Sunken Oathbearer",
        "type": "champion",
        "rarity": "common",
        "faction": "Tideborn Order",
        "text": "Remembers vows made where no witness could breathe.",
        "modes": ["summon", "bind", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "hp": 8,
            "pressure": 2,
            "guard": 2,
            "soul_bonus": {"Focus": {"ambition": 2}, "Guard": {"guard": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "thorn_pact_heir",
        "name": "Thorn Pact Heir",
        "type": "champion",
        "rarity": "common",
        "faction": "Verdant Pact",
        "text": "Every inheritance arrives with a wound attached.",
        "modes": ["summon", "bind", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "hp": 8,
            "pressure": 3,
            "guard": 1,
            "soul_bonus": {"Strike": {"pressure": 1}, "Guard": {"guard": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "mirror_hunger",
        "name": "Mirror Hunger",
        "type": "champion",
        "rarity": "rare",
        "faction": "Mirror Choir",
        "text": "It does not copy you. It becomes the part you refuse.",
        "modes": ["summon", "bind", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "hp": 7,
            "pressure": 3,
            "guard": 2,
            "soul_bonus": {"Scheme": {"ambition": 1, "pressure": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "iron_prayer_adept",
        "name": "Iron Prayer Adept",
        "type": "champion",
        "rarity": "common",
        "faction": "Iron Choir",
        "text": "A ritualist who kneels only to leverage.",
        "modes": ["summon", "bind", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "hp": 9,
            "pressure": 2,
            "guard": 3,
            "soul_bonus": {"Guard": {"guard": 1, "ambition": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "ashen_notary",
        "name": "Ashen Notary",
        "type": "champion",
        "rarity": "common",
        "faction": "Ember Court",
        "text": "Writes the contract after the duel has already begun.",
        "modes": ["summon", "bind", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "hp": 7,
            "pressure": 3,
            "guard": 1,
            "soul_bonus": {"Focus": {"ambition": 1}, "Strike": {"pressure": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "starless_debtor",
        "name": "Starless Debtor",
        "type": "champion",
        "rarity": "uncommon",
        "faction": "Starless Bank",
        "text": "Carries a debt large enough to blot out inheritance.",
        "modes": ["summon", "bind", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "hp": 8,
            "pressure": 3,
            "guard": 2,
            "soul_bonus": {"Scheme": {"pressure": 1}, "Focus": {"ambition": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "black_sun_witness",
        "name": "Black Sun Witness",
        "type": "champion",
        "rarity": "rare",
        "faction": "Starless Bank",
        "text": "Saw the crown fail and kept the receipt.",
        "modes": ["summon", "bind", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "hp": 9,
            "pressure": 3,
            "guard": 1,
            "soul_bonus": {"Strike": {"pressure": 1}, "Scheme": {"ambition": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "ashen_pulse",
        "name": "Ashen Pulse",
        "type": "technique",
        "rarity": "common",
        "faction": "Ember Court",
        "text": "A short command that makes hesitation bleed.",
        "modes": ["cast", "burn"],
        "ambition_cost": 0,
        "resolve": {"damage": 3, "burn_ambition": 2},
    },
    {
        "id": "debt_of_the_starless",
        "name": "Debt of the Starless",
        "type": "technique",
        "rarity": "uncommon",
        "faction": "Starless Bank",
        "text": "Collects from the future before the present can object.",
        "modes": ["cast", "burn"],
        "ambition_cost": 0,
        "resolve": {"damage": 2, "ambition": 1, "burn_ambition": 2},
    },
    {
        "id": "iron_prayer",
        "name": "Iron Prayer",
        "type": "technique",
        "rarity": "common",
        "faction": "Iron Choir",
        "text": "Turns fear into posture.",
        "modes": ["cast", "burn"],
        "ambition_cost": 0,
        "resolve": {"heal": 3, "ambition": 1, "burn_ambition": 2},
    },
    {
        "id": "velvet_rupture",
        "name": "Velvet Rupture",
        "type": "technique",
        "rarity": "uncommon",
        "faction": "Velvet Accord",
        "text": "A polite disaster at conversational distance.",
        "modes": ["cast", "burn"],
        "ambition_cost": 0,
        "resolve": {"damage": 4, "self_damage": 1, "burn_ambition": 2},
    },
    {
        "id": "oath_severance",
        "name": "Oath Severance",
        "type": "technique",
        "rarity": "common",
        "faction": "Tideborn Order",
        "text": "Cuts the promise without cutting the speaker.",
        "modes": ["cast", "burn"],
        "ambition_cost": 0,
        "resolve": {"damage": 2, "draw": 1, "burn_ambition": 2},
    },
    {
        "id": "cinder_mandate",
        "name": "Cinder Mandate",
        "type": "technique",
        "rarity": "common",
        "faction": "Ember Court",
        "text": "The room agrees because the room is burning.",
        "modes": ["cast", "burn"],
        "ambition_cost": 0,
        "resolve": {"damage": 2, "pressure_next": 1, "burn_ambition": 2},
    },
    {
        "id": "quiet_guillotine",
        "name": "Quiet Guillotine",
        "type": "technique",
        "rarity": "rare",
        "faction": "Mirror Choir",
        "text": "No spectacle. Just a decision with a blade inside.",
        "modes": ["cast", "burn"],
        "ambition_cost": 0,
        "resolve": {"damage": 5, "requires_active": True, "burn_ambition": 2},
    },
    {
        "id": "black_sun_rehearsal",
        "name": "Black Sun Rehearsal",
        "type": "technique",
        "rarity": "uncommon",
        "faction": "Starless Bank",
        "text": "Practice the ending until the ending recognizes you.",
        "modes": ["cast", "burn"],
        "ambition_cost": 0,
        "resolve": {"ambition": 2, "draw": 1, "burn_ambition": 2},
    },
    {
        "id": "mirror_break",
        "name": "Mirror Break",
        "type": "technique",
        "rarity": "common",
        "faction": "Mirror Choir",
        "text": "Shatters the easiest version of the opponent.",
        "modes": ["cast", "burn"],
        "ambition_cost": 0,
        "resolve": {"damage": 2, "mark": 1, "burn_ambition": 2},
    },
    {
        "id": "sunken_oath",
        "name": "Sunken Oath",
        "type": "scheme",
        "rarity": "common",
        "faction": "Tideborn Order",
        "text": "Prepared pressure for opponents who repeat themselves.",
        "modes": ["set", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "trigger": "repeat_intent",
            "pressure": 3,
            "ambition": 1,
            "burn_ambition": 1,
        },
    },
    {
        "id": "thorn_pact",
        "name": "Thorn Pact",
        "type": "scheme",
        "rarity": "common",
        "faction": "Verdant Pact",
        "text": "Prepared punishment for a Strike walking into Guard.",
        "modes": ["set", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "trigger": "strike_into_guard",
            "pressure": 2,
            "guard": 2,
            "burn_ambition": 1,
        },
    },
    {
        "id": "velvet_blackmail",
        "name": "Velvet Blackmail",
        "type": "scheme",
        "rarity": "uncommon",
        "faction": "Velvet Accord",
        "text": "The secret waits until timing becomes cruelty.",
        "modes": ["set", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "trigger": "opponent_focus",
            "pressure": 3,
            "ambition": 1,
            "burn_ambition": 1,
        },
    },
    {
        "id": "mirror_ledger",
        "name": "Mirror Ledger",
        "type": "scheme",
        "rarity": "rare",
        "faction": "Mirror Choir",
        "text": "Records the repeated lie and charges interest.",
        "modes": ["set", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "trigger": "mirror_intent",
            "pressure": 2,
            "draw": 1,
            "burn_ambition": 1,
        },
    },
    {
        "id": "last_crown_protocol",
        "name": "Last Crown Protocol",
        "type": "ascension",
        "rarity": "mythic",
        "faction": "Starless Bank",
        "text": "Ascend the active Champion and make the duel answer to you.",
        "modes": ["ascend", "burn"],
        "ambition_cost": 6,
        "resolve": {"hp": 4, "pressure": 2, "damage": 3, "burn_ambition": 2},
    },
    {
        "id": "dominion_of_ash",
        "name": "Dominion of Ash",
        "type": "ascension",
        "rarity": "mythic",
        "faction": "Ember Court",
        "text": "Ascend through refusal, then leave the altar changed.",
        "modes": ["ascend", "burn"],
        "ambition_cost": 6,
        "resolve": {"hp": 2, "pressure": 3, "damage": 3, "burn_ambition": 2},
    },
    {
        "id": "obsidian_ledger",
        "name": "Obsidian Ledger",
        "type": "relic",
        "rarity": "common",
        "faction": "Starless Bank",
        "text": "A persistent account of every pressure paid forward.",
        "modes": ["equip", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "intent_bonus": {"Focus": {"ambition": 1}, "Scheme": {"pressure": 1}},
            "dominate_bonus": 1,
            "burn_ambition": 1,
        },
    },
    {
        "id": "cinder_halo",
        "name": "Cinder Halo",
        "type": "relic",
        "rarity": "common",
        "faction": "Ember Court",
        "text": "A crown-shaped ember that rewards direct ambition.",
        "modes": ["equip", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "intent_bonus": {"Strike": {"pressure": 1}},
            "dominate_bonus": 1,
            "burn_ambition": 1,
        },
    },
    {
        "id": "saint_engine",
        "name": "Saint Engine",
        "type": "relic",
        "rarity": "uncommon",
        "faction": "Iron Choir",
        "text": "Mercy made mechanical, therefore suspicious.",
        "modes": ["equip", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "intent_bonus": {"Guard": {"guard": 2}, "Focus": {"heal": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "veil_of_thorns",
        "name": "Veil of Thorns",
        "type": "relic",
        "rarity": "uncommon",
        "faction": "Verdant Pact",
        "text": "Protective ornamentation with hostile memory.",
        "modes": ["equip", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "intent_bonus": {"Guard": {"guard": 1}, "Scheme": {"pressure": 1}},
            "burn_ambition": 1,
        },
    },
    {
        "id": "altar_of_refusal",
        "name": "Altar of Refusal",
        "type": "relic",
        "rarity": "rare",
        "faction": "Mirror Choir",
        "text": "A small altar that makes no sound unless someone compromises.",
        "modes": ["equip", "burn"],
        "ambition_cost": 0,
        "resolve": {
            "intent_bonus": {"Scheme": {"ambition": 1}, "Focus": {"guard": 1}},
            "dominate_bonus": 2,
            "burn_ambition": 1,
        },
    },
]


def _clone(card):
    return copy.deepcopy(card)


def get_ascension_catalog():
    """Return a defensive copy of the canonical Ascension catalog."""

    return [_clone(card) for card in ASCENSION_CATALOG]


def get_card_by_id(card_id):
    """Return a defensive copy of a card by id, or None when unknown."""

    card_id = str(card_id or "").strip()
    for card in ASCENSION_CATALOG:
        if card["id"] == card_id:
            return _clone(card)
    return None


def build_ascension_starter_deck(seed=None):
    """Build a deterministic 30-card starter deck with the required mix."""

    rng = random.Random("ambitionz-ascension-starter" if seed is None else seed)
    cards_by_type = {card_type: [] for card_type in CARD_TYPES}

    for card in get_ascension_catalog():
        cards_by_type[card["type"]].append(card)

    deck = []
    for card_type, count in STARTER_COUNTS.items():
        bucket = sorted(cards_by_type[card_type], key=lambda item: item["id"])
        rng.shuffle(bucket)
        if len(bucket) < count:
            raise ValueError(f"Ascension catalog lacks {count} {card_type} cards.")
        deck.extend(bucket[:count])

    rng.shuffle(deck)
    return deck


def validate_ascension_deck(deck):
    """Validate a 30-card Ascension Duel deck.

    The return value is structured so route handlers and tests can report exact
    failures without parsing exception text.
    """

    errors = []
    normalized = []

    if not isinstance(deck, list):
        return {"valid": False, "errors": ["deck_must_be_list"], "counts": {}}

    for entry in deck:
        card = get_card_by_id(entry) if isinstance(entry, str) else entry
        if not isinstance(card, dict):
            errors.append("unknown_card")
            continue
        missing = sorted(REQUIRED_CARD_FIELDS - set(card.keys()))
        if missing:
            errors.append(f"{card.get('id', 'card')}:missing:{','.join(missing)}")
            continue
        if card.get("type") not in CARD_TYPES:
            errors.append(f"{card.get('id', 'card')}:invalid_type")
            continue
        normalized.append(card)

    counts = Counter(card["type"] for card in normalized)

    if len(normalized) != 30:
        errors.append("deck_must_contain_30_cards")

    for card_type, minimum in {
        "champion": 10,
        "technique": 8,
        "relic": 4,
        "scheme": 4,
    }.items():
        if counts.get(card_type, 0) < minimum:
            errors.append(f"not_enough_{card_type}")

    if counts.get("ascension", 0) > 2:
        errors.append("too_many_ascensions")

    return {"valid": not errors, "errors": errors, "counts": dict(counts)}


def migrate_legacy_card_to_ascension(card):
    """Map a legacy card shape into the new Ascension model.

    This is intentionally conservative. It preserves the old id in metadata and
    emits a playable new-purpose card rather than trying to carry lane rules
    forward.
    """

    legacy = card if isinstance(card, dict) else {}
    legacy_type = str(legacy.get("type") or legacy.get("card_type") or "").lower()
    name = str(legacy.get("name") or legacy.get("id") or "Legacy Echo")
    legacy_id = str(legacy.get("id") or name.lower().replace(" ", "_"))

    if legacy_type in {"monster", "creature", "unit", "champion"}:
        card_type = "champion"
        modes = ["summon", "bind", "burn"]
        resolve = {
            "hp": max(6, int(legacy.get("hp") or legacy.get("health") or 8)),
            "pressure": max(1, int(legacy.get("attack") or legacy.get("power") or 2)),
            "guard": max(0, int(legacy.get("defense") or legacy.get("guard") or 1)),
            "soul_bonus": {"Strike": {"pressure": 1}},
            "burn_ambition": 1,
        }
    elif legacy_type in {"trap", "scheme"}:
        card_type = "scheme"
        modes = ["set", "burn"]
        resolve = {"trigger": "repeat_intent", "pressure": 2, "ambition": 1, "burn_ambition": 1}
    elif legacy_type in {"artifact", "equipment", "relic"}:
        card_type = "relic"
        modes = ["equip", "burn"]
        resolve = {"intent_bonus": {"Focus": {"ambition": 1}}, "burn_ambition": 1}
    elif legacy_type in {"ultimate", "ascension"}:
        card_type = "ascension"
        modes = ["ascend", "burn"]
        resolve = {"hp": 2, "pressure": 2, "damage": 3, "burn_ambition": 2}
    else:
        card_type = "technique"
        modes = ["cast", "burn"]
        resolve = {"damage": max(1, int(legacy.get("damage") or 2)), "burn_ambition": 2}

    return {
        "id": f"legacy_{legacy_id}",
        "name": name,
        "type": card_type,
        "rarity": str(legacy.get("rarity") or "legacy"),
        "faction": str(legacy.get("faction") or legacy.get("element") or "Legacy Echo"),
        "text": f"Legacy card migrated into Ascension Duel as a {card_type}.",
        "modes": modes,
        "ambition_cost": int(legacy.get("ambition_cost") or 0),
        "resolve": resolve,
        "legacy": {"id": legacy_id, "type": legacy_type or "unknown"},
    }

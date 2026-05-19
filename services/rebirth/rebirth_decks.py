import random
from copy import deepcopy

from services.rebirth.rebirth_cards import get_rebirth_card


DEFAULT_REBIRTH_DECK_ID = "ember_oath"


REBIRTH_DECK_DEFINITIONS = [
    {
        "id": "ember_oath",
        "name": "Ember Oath",
        "tagline": "Fast vows, bright pressure, little patience.",
        "difficulty": "Easy",
        "playstyle": "Aggressive Fire/Light pressure with clean Strike turns.",
        "featured_elements": ["Fire", "Light"],
        "card_ids": [
            "ember_vowblade",
            "ashen_duelist",
            "cinder_saint",
            "helios_breaker",
            "solar_oathkeeper",
            "aurora_myrmidon",
            "ember_vowblade",
            "ashen_duelist",
            "cinder_saint",
            "helios_breaker",
            "aurora_myrmidon",
            "solar_oathkeeper",
        ],
    },
    {
        "id": "deepguard",
        "name": "Deepguard",
        "tagline": "Hold the line until the rival runs out of certainty.",
        "difficulty": "Medium",
        "playstyle": "Defensive Water/Earth guard, sustain and slower tactical pressure.",
        "featured_elements": ["Water", "Earth"],
        "card_ids": [
            "tideglass_oracle",
            "deepwell_monk",
            "glassreef_bulwark",
            "ironroot_sentinel",
            "rootscript_hermit",
            "verdant_colossus",
            "glassreef_bulwark",
            "ironroot_sentinel",
            "rootscript_hermit",
            "deepwell_monk",
            "tideglass_oracle",
            "verdant_colossus",
        ],
    },
    {
        "id": "null_circuit",
        "name": "Null Circuit",
        "tagline": "Win by turning the round into a machine prayer.",
        "difficulty": "Advanced",
        "playstyle": "Technical Tech/Shadow control built around Ambition and disruption.",
        "featured_elements": ["Tech", "Shadow"],
        "card_ids": [
            "null_circuit",
            "pulsewire_savant",
            "static_ronin",
            "neon_wraith",
            "obsidian_fox",
            "black_neon_magistrate",
            "pulsewire_savant",
            "null_circuit",
            "black_neon_magistrate",
            "obsidian_fox",
            "static_ronin",
            "neon_wraith",
        ],
    },
]


def get_default_rebirth_deck_id():
    return DEFAULT_REBIRTH_DECK_ID


def _definition(deck_id):
    resolved_id = deck_id or DEFAULT_REBIRTH_DECK_ID
    for definition in REBIRTH_DECK_DEFINITIONS:
        if definition["id"] == resolved_id:
            return definition
    raise ValueError("Invalid Rebirth deck.")


def _cards_for(definition):
    cards = []
    for card_id in definition["card_ids"]:
        card = get_rebirth_card(card_id)
        if not card:
            raise ValueError(f"Rebirth deck references unknown card: {card_id}")
        cards.append(card)
    return cards


def build_rebirth_deck(deck_id=None, seed=None):
    definition = _definition(deck_id)
    cards = _cards_for(definition)
    random.Random(seed).shuffle(cards)
    return {
        "id": definition["id"],
        "name": definition["name"],
        "tagline": definition["tagline"],
        "difficulty": definition["difficulty"],
        "playstyle": definition["playstyle"],
        "featured_elements": list(definition["featured_elements"]),
        "cards": cards,
    }


def list_rebirth_decks():
    return [build_rebirth_deck(definition["id"]) for definition in REBIRTH_DECK_DEFINITIONS]


def compact_rebirth_deck(deck):
    return {
        "id": deck["id"],
        "name": deck["name"],
        "tagline": deck["tagline"],
        "difficulty": deck["difficulty"],
        "playstyle": deck["playstyle"],
        "card_count": len(deck.get("cards", [])),
        "featured_elements": list(deck.get("featured_elements", [])),
    }


def clone_deck_cards(deck):
    return deepcopy(deck.get("cards", []))

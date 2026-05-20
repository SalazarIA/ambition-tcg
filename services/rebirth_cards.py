from copy import deepcopy

from services.rebirth_art import attach_art_profile


CARD_ABILITY_KEYS = {
    "dreadclaw": "rending_strike",
    "dreadmaw": "apex_rend",
    "stoneshell": "brace",
    "stonewarden": "immovable",
    "shadewisp": "fade_cut",
    "nightfang": "bleed_mark",
    "skywarden": "high_guard",
    "stormwarden": "storm_dive",
    "ironbastion": "bulwark",
    "ironbulwark": "fortress_hit",
    "embermaw": "molten_bite",
    "embermaw_alpha": "inferno_bite",
    "voidstalker": "silent_pursuit",
}


def _card(
    card_id,
    name,
    family,
    role,
    tier,
    attack,
    guard,
    element,
    evolution_id,
    ability_name,
    ability_text,
    flavor,
    art,
):
    art_file = art if "." in art else f"{art}.svg"
    card = {
        "id": card_id,
        "name": name,
        "family": family,
        "role": role,
        "tier": tier,
        "attack": attack,
        "guard": guard,
        "power": attack,
        "element": element,
        "evolution_id": evolution_id,
        "ability_key": CARD_ABILITY_KEYS[card_id],
        "ability_name": ability_name,
        "ability_text": ability_text,
        "flavor": flavor,
        "art": f"/static/assets/rebirth/cards/{art_file}",
    }
    return attach_art_profile(card)


BASE_MONSTERS = [
    _card(
        "dreadclaw",
        "Dreadclaw",
        "Dreadclaw",
        "Beast",
        1,
        6,
        6,
        "Fire",
        "dreadmaw",
        "Rending Strike",
        "If this hits an already wounded target, deal +2 damage.",
        "A volcanic beast that turns pressure into a finish.",
        "dreadclaw-art.png",
    ),
    _card(
        "stoneshell",
        "Stoneshell",
        "Stoneshell",
        "Guardian",
        1,
        2,
        5,
        "Earth",
        "stonewarden",
        "Brace",
        "When this loses a clash, reduce incoming damage by 2.",
        "A walking wall built for the first answer.",
        "stoneshell",
    ),
    _card(
        "shadewisp",
        "Shadewisp",
        "Shadewisp",
        "Assassin",
        1,
        3,
        2,
        "Shadow",
        "nightfang",
        "Fade Cut",
        "Wins attack ties against wounded targets.",
        "A blade-shaped shadow that hates being seen.",
        "shadewisp",
    ),
    _card(
        "skywarden",
        "Skywarden",
        "Skywarden",
        "Avian",
        1,
        4,
        3,
        "Air",
        "stormwarden",
        "High Guard",
        "Gains +1 clash attack against cards with 3 guard or less.",
        "A high sentinel watching the duel from above.",
        "skywarden",
    ),
    _card(
        "ironbastion",
        "Ironbastion",
        "Ironbastion",
        "Guardian",
        1,
        3,
        6,
        "Metal",
        "ironbulwark",
        "Bulwark",
        "When hit by 4 attack or less, reduce incoming damage by 3.",
        "Armor so heavy it becomes a strategy.",
        "ironbastion",
    ),
    _card(
        "embermaw",
        "Embermaw",
        "Embermaw",
        "Wyrm",
        1,
        7,
        6,
        "Fire",
        "embermaw_alpha",
        "Molten Bite",
        "Deals +1 damage when it wins a clash.",
        "A furnace with wings and teeth.",
        "embermaw",
    ),
    _card(
        "voidstalker",
        "Voidstalker",
        "Voidstalker",
        "Hunter",
        1,
        5,
        2,
        "Void",
        None,
        "Silent Pursuit",
        "Gains +1 clash attack during turns 1 and 2.",
        "It arrives where the answer should have been.",
        "voidstalker",
    ),
]


EVOLVED_MONSTERS = [
    _card(
        "dreadmaw",
        "Dreadmaw",
        "Dreadclaw",
        "Apex Beast",
        2,
        9,
        7,
        "Fire",
        None,
        "Apex Rend",
        "If this hits an already wounded target, deal +3 damage.",
        "Dreadclaw after the second roar.",
        "dreadclaw-art.png",
    ),
    _card(
        "stonewarden",
        "Stonewarden",
        "Stoneshell",
        "Guardian",
        2,
        4,
        8,
        "Earth",
        None,
        "Immovable",
        "When this loses a clash, reduce incoming damage by 3. When it wins, deal +2 damage.",
        "The shield finally learned to walk forward.",
        "stoneshell",
    ),
    _card(
        "nightfang",
        "Nightfang",
        "Shadewisp",
        "Apex Assassin",
        2,
        6,
        3,
        "Shadow",
        None,
        "Bleed Mark",
        "Wins attack ties against wounded targets and deals +1 damage when it wins.",
        "A dark sprint with a bright wound behind it.",
        "nightfang",
    ),
    _card(
        "stormwarden",
        "Stormwarden",
        "Skywarden",
        "Avian",
        2,
        7,
        5,
        "Air",
        None,
        "Storm Dive",
        "Deals +2 damage when it wins against cards with 3 guard or less.",
        "The sky answers with a blade.",
        "skywarden",
    ),
    _card(
        "ironbulwark",
        "Ironbulwark",
        "Ironbastion",
        "Guardian",
        2,
        5,
        9,
        "Metal",
        None,
        "Fortress Hit",
        "Reduces incoming damage by 4 and deals at least 3 damage when it wins.",
        "A fortress deciding it has legs.",
        "ironbastion",
    ),
    _card(
        "embermaw_alpha",
        "Embermaw Alpha",
        "Embermaw",
        "Wyrm",
        2,
        10,
        7,
        "Fire",
        None,
        "Inferno Bite",
        "Deals +3 damage when it wins a clash.",
        "A furnace that became a crown.",
        "embermaw",
    ),
]


CARD_CATALOG = BASE_MONSTERS + EVOLVED_MONSTERS
CARD_BY_ID = {card["id"]: card for card in CARD_CATALOG}

PLAYER_DECK = [
    "dreadclaw",
    "dreadclaw",
    "stoneshell",
    "shadewisp",
    "skywarden",
    "ironbastion",
    "embermaw",
    "voidstalker",
    "shadewisp",
    "stoneshell",
    "skywarden",
    "ironbastion",
    "embermaw",
    "shadewisp",
    "dreadclaw",
    "voidstalker",
]

BOT_DECK = [
    "dreadclaw",
    "dreadclaw",
    "voidstalker",
    "shadewisp",
    "stoneshell",
    "skywarden",
    "ironbastion",
    "embermaw",
    "shadewisp",
    "stoneshell",
    "voidstalker",
    "shadewisp",
    "ironbastion",
    "skywarden",
    "embermaw",
    "shadewisp",
]


def get_card(card_id):
    try:
        return deepcopy(CARD_BY_ID[card_id])
    except KeyError as exc:
        raise ValueError(f"Unknown Rebirth card: {card_id}") from exc


def create_card_instance(card_id, owner, sequence):
    card = get_card(card_id)
    card["instance_id"] = f"{owner}-{sequence:02d}-{card_id}"
    return card


def build_deck(owner, card_ids=None):
    if card_ids is None:
        card_ids = PLAYER_DECK if owner == "player" else BOT_DECK
    return [create_card_instance(card_id, owner, index + 1) for index, card_id in enumerate(card_ids)]


def catalog_payload():
    return deepcopy(CARD_CATALOG)

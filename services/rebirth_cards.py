from copy import deepcopy

from services.rebirth_art import attach_art_profile


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
        "Deal attack damage. If the target is wounded, deal 2 extra damage.",
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
        "Reduce incoming clash damage with heavy guard.",
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
        "Wins ties against wounded targets.",
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
        "Balanced pressure with clean defensive reach.",
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
        "Punishes low attack cards by absorbing their clash.",
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
        "High attack pressure with strong guard.",
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
        "Fast pressure that tries to end the turn early.",
        "It arrives where the answer should have been.",
        "voidstalker",
    ),
    _card(
        "nightfang",
        "Nightfang",
        "Nightfang",
        "Beast",
        1,
        4,
        2,
        "Shadow",
        None,
        "Bleed Mark",
        "Leaves the target exposed for the next clash.",
        "A dark sprint with a bright wound behind it.",
        "nightfang",
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
        "Deal attack damage and add 2 if the target is wounded.",
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
        "Turns guard into a punishing counter-clash.",
        "The shield finally learned to walk forward.",
        "stoneshell",
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
        "Wins cleanly against low guard cards.",
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
        "High guard, steady damage and no drama.",
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
        "The cleanest finisher in the prototype set.",
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
    "nightfang",
    "stoneshell",
    "skywarden",
    "ironbastion",
    "embermaw",
    "shadewisp",
    "dreadclaw",
    "voidstalker",
]

BOT_DECK = [
    "voidstalker",
    "nightfang",
    "stoneshell",
    "skywarden",
    "ironbastion",
    "embermaw",
    "shadewisp",
    "dreadclaw",
    "stoneshell",
    "voidstalker",
    "nightfang",
    "ironbastion",
    "skywarden",
    "embermaw",
    "dreadclaw",
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

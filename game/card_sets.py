# =========================================================
# Ambitionz Card Set Foundation
# Base Set = first 250 cards already in the project.
# Future sets/seasons/rarities should extend this system.
# =========================================================

BASE_SET_KEY = "base_250"
BASE_SET_NAME = "Ambitionz Base Set"
BASE_SET_SEASON = "Beta Genesis"
BASE_SET_SIZE_TARGET = 250

RARITY_ORDER = {
    "Common": 1,
    "Uncommon": 2,
    "Rare": 3,
    "Ultra Rare": 4,
    "Unique": 5,
}

RARITY_STYLE = {
    "Common": {
        "label": "Common",
        "css": "rarity-common",
        "dust": 10,
        "frame": "iron",
    },
    "Uncommon": {
        "label": "Uncommon",
        "css": "rarity-uncommon",
        "dust": 30,
        "frame": "silver",
    },
    "Rare": {
        "label": "Rare",
        "css": "rarity-rare",
        "dust": 100,
        "frame": "gold",
    },
    "Ultra Rare": {
        "label": "Ultra Rare",
        "css": "rarity-ultra-rare",
        "dust": 400,
        "frame": "mythic",
    },
    "Unique": {
        "label": "Unique",
        "css": "rarity-unique",
        "dust": 1200,
        "frame": "legend",
    },
}

TYPE_STYLE = {
    "Monster": {
        "css": "type-monster",
        "slot": "monster",
        "color": "gold",
    },
    "Spell": {
        "css": "type-spell",
        "slot": "spell",
        "color": "blue",
    },
    "Trap": {
        "css": "type-trap",
        "slot": "trap",
        "color": "red",
    },
}

SIGIL_STYLE = {
    "Fury": "sigil-fury",
    "Resolve": "sigil-resolve",
    "Insight": "sigil-insight",
    "Ruin": "sigil-ruin",
    "Harmony": "sigil-harmony",
    "Global": "sigil-global",
    "None": "sigil-none",
}

ROLE_STYLE = {
    "Aggressor": "role-aggressor",
    "Defender": "role-defender",
    "Controller": "role-controller",
    "Balancer": "role-balancer",
    "Finisher": "role-finisher",
    "Support": "role-support",
    "Utility": "role-utility",
    "None": "role-none",
}

FUTURE_COLLECTIONS = [
    {
        "key": "season_01",
        "name": "Season I",
        "status": "future",
        "purpose": "First ranked season card expansion.",
    },
    {
        "key": "fury_expansion",
        "name": "Fury Expansion",
        "status": "future",
        "purpose": "Aggressive Fire/Fury package.",
    },
    {
        "key": "unique_relics",
        "name": "Unique Relics",
        "status": "future",
        "purpose": "Limited unique cosmetic/gameplay-safe collectibles.",
    },
]


def normalize_rarity(value):
    raw = str(value or "Common").strip()

    aliases = {
        "common": "Common",
        "uncommon": "Uncommon",
        "rare": "Rare",
        "ultra": "Ultra Rare",
        "ultra rare": "Ultra Rare",
        "ultrarare": "Ultra Rare",
        "unique": "Unique",
        "legendary": "Unique",
    }

    return aliases.get(raw.lower(), raw if raw in RARITY_ORDER else "Common")


def normalize_type(value):
    raw = str(value or "Monster").strip().title()

    if raw not in TYPE_STYLE:
        return "Monster"

    return raw


def normalize_sigil(value):
    raw = str(value or "None").strip()

    if not raw:
        return "None"

    return raw if raw in SIGIL_STYLE else raw.title()


def normalize_role(value):
    raw = str(value or "None").strip()

    if not raw:
        return "None"

    return raw if raw in ROLE_STYLE else raw.title()


def card_power_bucket(card):
    card_type = normalize_type(card.get("type"))

    if card_type != "Monster":
        return "Tactical"

    power = int(card.get("power") or card.get("attack") or 0)

    if power <= 2:
        return "Early"
    if power <= 4:
        return "Mid"
    if power <= 6:
        return "Heavy"

    return "Finisher"


def get_card_runtime_identity(card, index=0):
    rarity = normalize_rarity(card.get("rarity"))
    card_type = normalize_type(card.get("type"))
    sigil = normalize_sigil(card.get("sigil"))
    role = normalize_role(card.get("role"))

    card_id = (
        card.get("id")
        or card.get("card_id")
        or card.get("slug")
        or f"base-{index + 1:03d}"
    )

    image = (
        card.get("image")
        or card.get("img")
        or "cards/placeholders/card_placeholder.svg"
    )

    return {
        "runtime_id": str(card_id),
        "set_key": card.get("set_key") or BASE_SET_KEY,
        "set_name": card.get("set_name") or BASE_SET_NAME,
        "season": card.get("season") or BASE_SET_SEASON,
        "rarity": rarity,
        "rarity_css": RARITY_STYLE.get(rarity, RARITY_STYLE["Common"])["css"],
        "rarity_rank": RARITY_ORDER.get(rarity, 1),
        "type": card_type,
        "type_css": TYPE_STYLE.get(card_type, TYPE_STYLE["Monster"])["css"],
        "sigil": sigil,
        "sigil_css": SIGIL_STYLE.get(sigil, "sigil-none"),
        "role": role,
        "role_css": ROLE_STYLE.get(role, "role-none"),
        "power_bucket": card_power_bucket(card),
        "image": image,
        "is_base_set": True,
        "is_future_expansion": False,
    }


def enrich_card_runtime(card, index=0):
    enriched = dict(card)
    enriched.update(get_card_runtime_identity(card, index=index))

    enriched.setdefault("name", f"Unnamed Card {index + 1}")
    enriched.setdefault("description", enriched.get("effect") or "")
    enriched.setdefault("effect", enriched.get("description") or "")
    enriched.setdefault("element", enriched.get("element") or "Neutral")
    enriched.setdefault("cost", enriched.get("cost") or enriched.get("energy_cost") or 1)
    enriched.setdefault("value", enriched.get("value") or enriched.get("power") or 0)
    enriched.setdefault("count", enriched.get("count") or 0)

    return enriched


def enrich_card_catalog(cards):
    return [
        enrich_card_runtime(card, index=index)
        for index, card in enumerate(cards or [])
    ]

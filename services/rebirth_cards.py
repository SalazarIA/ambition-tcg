from copy import deepcopy


BASE_MONSTERS = [
    {
        "id": "ember_cub",
        "name": "Ember Cub",
        "family": "Ember",
        "tier": 1,
        "power": 2,
        "element": "Fire",
        "evolution_id": "ember_fang",
        "flavor": "Small flame. Big nerve.",
    },
    {
        "id": "tide_imp",
        "name": "Tide Imp",
        "family": "Tide",
        "tier": 1,
        "power": 2,
        "element": "Water",
        "evolution_id": "tide_brute",
        "flavor": "Laughs first, splashes later.",
    },
    {
        "id": "stone_pup",
        "name": "Stone Pup",
        "family": "Stone",
        "tier": 1,
        "power": 3,
        "element": "Earth",
        "evolution_id": "stone_golem",
        "flavor": "A loyal rock with teeth.",
    },
    {
        "id": "night_sprout",
        "name": "Night Sprout",
        "family": "Night",
        "tier": 1,
        "power": 1,
        "element": "Shadow",
        "evolution_id": "night_bloom",
        "flavor": "It grows where the light hesitates.",
    },
    {
        "id": "spark_hare",
        "name": "Spark Hare",
        "family": "Spark",
        "tier": 1,
        "power": 4,
        "element": "Volt",
        "evolution_id": None,
        "flavor": "Too fast to regret anything.",
    },
    {
        "id": "glass_moth",
        "name": "Glass Moth",
        "family": "Glass",
        "tier": 1,
        "power": 3,
        "element": "Air",
        "evolution_id": None,
        "flavor": "Fragile wings. Perfect timing.",
    },
    {
        "id": "iron_beetle",
        "name": "Iron Beetle",
        "family": "Iron",
        "tier": 1,
        "power": 5,
        "element": "Metal",
        "evolution_id": None,
        "flavor": "A tiny tank with opinions.",
    },
    {
        "id": "mist_lynx",
        "name": "Mist Lynx",
        "family": "Mist",
        "tier": 1,
        "power": 4,
        "element": "Water",
        "evolution_id": None,
        "flavor": "You see it after it leaves.",
    },
    {
        "id": "sun_ram",
        "name": "Sun Ram",
        "family": "Sun",
        "tier": 1,
        "power": 3,
        "element": "Light",
        "evolution_id": None,
        "flavor": "Charges like morning.",
    },
    {
        "id": "void_tadpole",
        "name": "Void Tadpole",
        "family": "Void",
        "tier": 1,
        "power": 2,
        "element": "Void",
        "evolution_id": None,
        "flavor": "Small enough to be ignored. Once.",
    },
]


EVOLVED_MONSTERS = [
    {
        "id": "ember_fang",
        "name": "Ember Fang",
        "family": "Ember",
        "tier": 2,
        "power": 5,
        "element": "Fire",
        "evolution_id": None,
        "flavor": "The cub learns to bite in flames.",
    },
    {
        "id": "tide_brute",
        "name": "Tide Brute",
        "family": "Tide",
        "tier": 2,
        "power": 5,
        "element": "Water",
        "evolution_id": None,
        "flavor": "The wave stands up and swings.",
    },
    {
        "id": "stone_golem",
        "name": "Stone Golem",
        "family": "Stone",
        "tier": 2,
        "power": 6,
        "element": "Earth",
        "evolution_id": None,
        "flavor": "No longer loyal. Now inevitable.",
    },
    {
        "id": "night_bloom",
        "name": "Night Bloom",
        "family": "Night",
        "tier": 2,
        "power": 4,
        "element": "Shadow",
        "evolution_id": None,
        "flavor": "A quiet flower with sharp petals.",
    },
]


CARD_CATALOG = BASE_MONSTERS + EVOLVED_MONSTERS
CARD_BY_ID = {card["id"]: card for card in CARD_CATALOG}

PLAYER_DECK = [
    "ember_cub",
    "ember_cub",
    "iron_beetle",
    "spark_hare",
    "stone_pup",
    "tide_imp",
    "night_sprout",
    "tide_imp",
    "stone_pup",
    "night_sprout",
    "spark_hare",
    "glass_moth",
    "iron_beetle",
    "mist_lynx",
    "sun_ram",
    "void_tadpole",
    "ember_cub",
    "tide_imp",
]

BOT_DECK = [
    "tide_imp",
    "spark_hare",
    "stone_pup",
    "glass_moth",
    "ember_cub",
    "iron_beetle",
    "night_sprout",
    "mist_lynx",
    "sun_ram",
    "void_tadpole",
    "stone_pup",
    "tide_imp",
    "ember_cub",
    "night_sprout",
    "iron_beetle",
    "glass_moth",
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


def build_deck(owner):
    card_ids = PLAYER_DECK if owner == "player" else BOT_DECK
    return [create_card_instance(card_id, owner, index + 1) for index, card_id in enumerate(card_ids)]


def catalog_payload():
    return deepcopy(CARD_CATALOG)

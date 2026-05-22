from copy import deepcopy


CARD_IMAGE_TEMPLATE = "static/img/cards/{card_id}.png"
CARD_TYPES = {"MONSTER", "SPELL", "TRAP"}
MONSTER_FAMILIES = ("FIRE", "WATER", "EARTH", "SHADOW")
STARTER_DECK_SIZE = 30
MONSTER_DECK_MIN = 18
MONSTER_DECK_MAX = 22
TURN_ONE_TEST_CARD_IDS = {"card_001", "card_002", "card_021", "card_041", "card_061"}


FAMILY_CONFIGS = {
    "FIRE": {
        "element": "Fire",
        "role": "Direct damage / burn",
        "palette": ["#ff5b35", "#ffb347", "#2a0f0b"],
        "base_start": 1,
        "evolved_start": 11,
        "base_names": [
            "Cinder Lynx",
            "Ashen Brawler",
            "Blazewing Adept",
            "Coalheart Runner",
            "Flareblade Cub",
            "Scorchscale Imp",
            "Emberhorn Raider",
            "Sunstoke Duelist",
            "Pyrebound Hound",
            "Volcanic Herald",
        ],
        "evolved_names": [
            "Cinder Lynx Alpha",
            "Ashen Brawler Rex",
            "Blazewing Tyrant",
            "Coalheart Champion",
            "Flareblade Matriarch",
            "Scorchscale Infernal",
            "Emberhorn Warlord",
            "Sunstoke Archon",
            "Pyrebound Cerberus",
            "Volcanic Avatar",
        ],
        "abilities": [
            ("fire_direct", "Direct Spark", "Deals extra pressure when it wins combat."),
            ("fire_burn", "Burn Brand", "Applies burn after a winning combat."),
            ("fire_surge", "Heat Surge", "Gains early combat attack."),
            ("fire_execute", "Cinder Execute", "Punishes wounded targets."),
        ],
    },
    "WATER": {
        "element": "Water",
        "role": "Healing / cleanse",
        "palette": ["#37c7ff", "#b8fff6", "#092033"],
        "base_start": 21,
        "evolved_start": 31,
        "base_names": [
            "Mistcall Tactician",
            "Riverglass Medic",
            "Tidepool Acolyte",
            "Pearlfin Guard",
            "Rainspire Oracle",
            "Coldstream Sentry",
            "Brineveil Seer",
            "Moonwell Keeper",
            "Foamfang Skirmisher",
            "Riptide Maven",
        ],
        "evolved_names": [
            "Mistcall Strategist",
            "Riverglass Saint",
            "Tidepool Hierophant",
            "Pearlfin Bastion",
            "Rainspire Prophet",
            "Coldstream Paladin",
            "Brineveil Highseer",
            "Moonwell Archkeeper",
            "Foamfang Tempest",
            "Riptide Grandmaster",
        ],
        "abilities": [
            ("water_heal", "Healing Tide", "Restores HP after combat pressure."),
            ("water_cleanse", "Cleanse Current", "Clears one harmful status after combat."),
            ("water_tide", "Rising Tide", "Improves combat attack after turn two."),
            ("water_guard", "Flowing Guard", "Reduces incoming combat damage."),
        ],
    },
    "EARTH": {
        "element": "Earth",
        "role": "Shield / defense",
        "palette": ["#8bd05f", "#f0e2a0", "#17220d"],
        "base_start": 41,
        "evolved_start": 51,
        "base_names": [
            "Stonehide Recruit",
            "Rootwall Tender",
            "Amberplate Cub",
            "Granite Pactbearer",
            "Mossback Brute",
            "Bramblehorn Knight",
            "Quartzroot Sentinel",
            "Ironbark Veteran",
            "Terrashield Monk",
            "Boulderwake Colossus",
        ],
        "evolved_names": [
            "Stonehide Bulwark",
            "Rootwall Ancient",
            "Amberplate Titan",
            "Granite Pactlord",
            "Mossback Behemoth",
            "Bramblehorn Paragon",
            "Quartzroot Citadel",
            "Ironbark Warden",
            "Terrashield Ascetic",
            "Boulderwake Primordial",
        ],
        "abilities": [
            ("earth_shield", "Shield Bloom", "Adds a persistent shield after combat."),
            ("earth_fortify", "Fortify", "Turns guard into extra combat value."),
            ("earth_counter", "Stone Counter", "Counters low-attack enemies."),
            ("earth_bulwark", "Bulwark", "Heavily reduces incoming combat damage."),
        ],
    },
    "SHADOW": {
        "element": "Shadow",
        "role": "Persistent statuses / lifesteal",
        "palette": ["#9b5cff", "#221437", "#f2d9ff"],
        "base_start": 61,
        "evolved_start": 71,
        "base_names": [
            "Duskwisp Thief",
            "Hollowmark Stalker",
            "Nightchain Adept",
            "Graveveil Duelist",
            "Umbral Lurker",
            "Voidkiss Assassin",
            "Cryptsong Reaper",
            "Shadeglass Scout",
            "Blackthorn Revenant",
            "Eclipse Herald",
        ],
        "evolved_names": [
            "Duskwisp Shade",
            "Hollowmark Predator",
            "Nightchain Archmage",
            "Graveveil Champion",
            "Umbral Horror",
            "Voidkiss Executioner",
            "Cryptsong Harvester",
            "Shadeglass Phantom",
            "Blackthorn Lich",
            "Eclipse Avatar",
        ],
        "abilities": [
            ("shadow_lifesteal", "Lifesteal", "Heals its controller after dealing damage."),
            ("shadow_decay", "Decay", "Applies persistent decay to the target."),
            ("shadow_mark", "Wound Mark", "Wins ties against wounded enemies."),
            ("shadow_drain", "Soul Drain", "Steals HP through the effect stack."),
        ],
    },
}


SPELL_DEFINITIONS = [
    ("DrawTwoCards", "Arcane Refill", "Draw two cards.", [{"type": "draw", "target": "self", "amount": 2}], 2),
    ("CleanseAll", "Tidal Cleanse", "Remove all harmful statuses from your side.", [{"type": "cleanse", "target": "self", "mode": "all"}], 2),
    ("DestroyShield", "Shardbreaker Hex", "Destroy the opponent shield.", [{"type": "destroy_shield", "target": "opponent"}], 1),
    ("Fireball", "Arena Fireball", "Deal direct damage to the opponent.", [{"type": "damage", "target": "opponent", "amount": 3}], 2),
    ("HealingRain", "Healing Rain", "Restore HP to your side.", [{"type": "heal", "target": "self", "amount": 4}], 2),
    ("Fortify", "Runic Fortify", "Gain a shield.", [{"type": "shield", "target": "self", "amount": 3, "turns": 2}], 1),
    ("BurningEdict", "Burning Edict", "Apply burn to the opponent.", [{"type": "status", "target": "opponent", "status": "burn", "potency": 1, "turns": 2}], 2),
    ("TidalRenewal", "Tidal Renewal", "Cleanse and heal yourself.", [{"type": "cleanse", "target": "self", "mode": "all"}, {"type": "heal", "target": "self", "amount": 2}], 3),
    ("StoneSkin", "Stone Skin", "Gain a stronger shield.", [{"type": "shield", "target": "self", "amount": 5, "turns": 1}], 3),
    ("ShadowDrain", "Shadow Drain", "Damage the opponent and heal yourself.", [{"type": "damage", "target": "opponent", "amount": 2}, {"type": "heal", "target": "self", "amount": 2}], 3),
]


TRAP_DEFINITIONS = [
    ("NegateAttack", "Null Sigil", "Negate the next combat attack.", "opponent_attacks", "negate_attack", 2),
    ("ReflectDamage", "Mirror Thorns", "Reflect damage during combat.", "opponent_attacks", "reflect_damage", 2),
    ("BurnAttacker", "Ash Snare", "Burn the attacker.", "opponent_attacks", "burn_attacker", 1),
    ("EmergencyShield", "Last Wall", "Raise a shield before combat damage.", "owner_attacked", "shield_owner", 1),
    ("CleanseAmbush", "Pure Reversal", "Cleanse statuses before combat.", "owner_attacked", "cleanse_owner", 1),
    ("FreezeStrike", "Frost Lock", "Freeze the attacker.", "opponent_attacks", "freeze_attacker", 2),
    ("DrainCounter", "Night Toll", "Drain HP when attacked.", "owner_attacked", "drain_attacker", 2),
    ("GuardBreakTrap", "Fault Line", "Destroy shields before combat.", "opponent_attacks", "destroy_shield", 1),
    ("SecondWind", "Hidden Spring", "Heal when pressured.", "owner_attacked", "heal_owner", 1),
    ("StunRune", "Stun Rune", "Lower the attacker's combat power.", "opponent_attacks", "weaken_attacker", 2),
]


def _image_path(card_id):
    return CARD_IMAGE_TEMPLATE.format(card_id=card_id)


def _art_payload(card_id, family, palette):
    return {
        "art": _image_path(card_id),
        "art_key": f"rebirth.card.{card_id}.v1",
        "art_version": "v1",
        "art_status": "default_png_path",
        "art_finish": "tcg_card_frame",
        "palette": list(palette),
        "silhouette": f"{family.lower()}_sigil",
    }


def _monster_card(card_number, *, family, name, tier, slot):
    config = FAMILY_CONFIGS[family]
    card_id = f"card_{card_number:03d}"
    evolved_number = config["evolved_start"] + slot
    is_evolved = tier > 1
    ability_key, ability_name, ability_text = config["abilities"][slot % len(config["abilities"])]
    attack_curve = [4, 5, 5, 6, 6, 7, 7, 8, 8, 9]
    guard_curve = [3, 3, 4, 2, 4, 3, 5, 2, 4, 5]
    attack = attack_curve[slot] + (1 if is_evolved else 0)
    guard = guard_curve[slot] + (1 if is_evolved else 0)
    rarity = "UNCOMMON" if is_evolved else "COMMON"
    card = {
        "id": card_id,
        "name": name,
        "type": "MONSTER",
        "card_type": "MONSTER",
        "family": family,
        "role": config["role"],
        "tier": tier,
        "rarity": rarity,
        "cost": 2 if is_evolved else 1,
        "attack": attack,
        "power": attack,
        "guard": guard,
        "element": config["element"],
        "evolution_id": None if is_evolved else f"card_{evolved_number:03d}",
        "ability_key": ability_key,
        "ability_name": ability_name,
        "ability_text": ability_text,
        "flavor": f"{name} carries the {family.lower()} line into the living arena.",
        "status_affinity": family.lower(),
    }
    card.update(_art_payload(card_id, family, config["palette"]))
    return card


def _spell_card(offset, definition):
    action, name, text, stack_effects, cost = definition
    card_number = 81 + offset
    card_id = f"card_{card_number:03d}"
    card = {
        "id": card_id,
        "name": name,
        "type": "SPELL",
        "card_type": "SPELL",
        "family": "SPELL",
        "role": "Instant stack effect",
        "tier": 1,
        "rarity": "UNCOMMON",
        "cost": min(2, cost),
        "attack": 0,
        "power": 0,
        "guard": 0,
        "element": "Arcane",
        "evolution_id": None,
        "ability_key": f"spell_{action.lower()}",
        "ability_name": action,
        "ability_text": text,
        "flavor": f"{name} bends the stack before the next clash.",
        "action": action,
        "stack_effects": deepcopy(stack_effects),
    }
    card.update(_art_payload(card_id, "spell", ["#f9e27d", "#2f245f", "#ffffff"]))
    return card


def _trap_card(offset, definition):
    action, name, text, trigger, trap_effect, cost = definition
    card_number = 91 + offset
    card_id = f"card_{card_number:03d}"
    card = {
        "id": card_id,
        "name": name,
        "type": "TRAP",
        "card_type": "TRAP",
        "family": "TRAP",
        "role": "Hidden combat trigger",
        "tier": 1,
        "rarity": "UNCOMMON",
        "cost": min(2, cost),
        "attack": 0,
        "power": 0,
        "guard": 0,
        "element": "Hidden",
        "evolution_id": None,
        "ability_key": f"trap_{action.lower()}",
        "ability_name": action,
        "ability_text": text,
        "flavor": f"{name} waits face down for the combat phase.",
        "action": action,
        "face_down": True,
        "trigger_phase": "COMBAT_PHASE",
        "trigger": trigger,
        "trap_effect": trap_effect,
    }
    card.update(_art_payload(card_id, "trap", ["#ff4f8b", "#181022", "#ffc6df"]))
    return card


def _build_catalog_dict():
    cards = {}
    for family in MONSTER_FAMILIES:
        config = FAMILY_CONFIGS[family]
        for slot, name in enumerate(config["base_names"]):
            card = _monster_card(config["base_start"] + slot, family=family, name=name, tier=1, slot=slot)
            cards[card["id"]] = card
        for slot, name in enumerate(config["evolved_names"]):
            card = _monster_card(config["evolved_start"] + slot, family=family, name=name, tier=2, slot=slot)
            cards[card["id"]] = card
    for offset, definition in enumerate(SPELL_DEFINITIONS):
        card = _spell_card(offset, definition)
        cards[card["id"]] = card
    for offset, definition in enumerate(TRAP_DEFINITIONS):
        card = _trap_card(offset, definition)
        cards[card["id"]] = card
    expected = [f"card_{index:03d}" for index in range(1, 101)]
    if list(cards.keys()) != expected:
        raise RuntimeError("Rebirth catalog generation must produce card_001 through card_100 in order.")
    return cards


CARD_CATALOG_DICT = _build_catalog_dict()
CARD_BY_ID = CARD_CATALOG_DICT
CARD_CATALOG = [deepcopy(card) for card in CARD_CATALOG_DICT.values()]
BASE_MONSTERS = [deepcopy(card) for card in CARD_CATALOG_DICT.values() if card["type"] == "MONSTER" and int(card["tier"]) == 1]
EVOLVED_MONSTERS = [deepcopy(card) for card in CARD_CATALOG_DICT.values() if card["type"] == "MONSTER" and int(card["tier"]) > 1]
SPELL_CARDS = [deepcopy(card) for card in CARD_CATALOG_DICT.values() if card["type"] == "SPELL"]
TRAP_CARDS = [deepcopy(card) for card in CARD_CATALOG_DICT.values() if card["type"] == "TRAP"]
CARD_ABILITY_KEYS = {card_id: card["ability_key"] for card_id, card in CARD_CATALOG_DICT.items()}

PLAYER_DECK = [
    "card_001",
    "card_001",
    "card_002",
    "card_021",
    "card_041",
    "card_061",
    "card_003",
    "card_022",
    "card_042",
    "card_062",
    "card_004",
    "card_023",
    "card_043",
    "card_063",
    "card_005",
    "card_024",
    "card_044",
    "card_064",
    "card_006",
    "card_025",
    "card_081",
    "card_082",
    "card_083",
    "card_084",
    "card_085",
    "card_091",
    "card_092",
    "card_093",
    "card_094",
    "card_095",
]

BOT_DECK = [
    "card_041",
    "card_041",
    "card_042",
    "card_061",
    "card_021",
    "card_001",
    "card_043",
    "card_062",
    "card_022",
    "card_002",
    "card_044",
    "card_063",
    "card_023",
    "card_003",
    "card_045",
    "card_064",
    "card_024",
    "card_004",
    "card_046",
    "card_065",
    "card_086",
    "card_087",
    "card_088",
    "card_089",
    "card_090",
    "card_096",
    "card_097",
    "card_098",
    "card_099",
    "card_100",
]


def card_type(card_or_id):
    card = get_card(card_or_id) if isinstance(card_or_id, str) else card_or_id
    explicit = str(card.get("type") or card.get("card_type") or "").upper()
    if explicit:
        return explicit
    if "attack" in card or "guard" in card:
        return "MONSTER"
    return ""


def is_monster(card_or_id):
    return card_type(card_or_id) == "MONSTER"


def is_spell(card_or_id):
    return card_type(card_or_id) == "SPELL"


def is_trap(card_or_id):
    return card_type(card_or_id) == "TRAP"


def cards_by_type(card_ids):
    counts = {"MONSTER": 0, "SPELL": 0, "TRAP": 0}
    for card_id in card_ids:
        ctype = card_type(card_id)
        if ctype not in counts:
            raise ValueError(f"{card_id} is not a supported Rebirth card type.")
        counts[ctype] += 1
    return counts


def validate_deck_distribution(card_ids, *, deck_size=STARTER_DECK_SIZE):
    if not isinstance(card_ids, list):
        raise ValueError("Deck card_ids must be a list.")
    if len(card_ids) != deck_size:
        raise ValueError(f"Rebirth deck requires exactly {deck_size} cards.")
    counts = cards_by_type(card_ids)
    if not MONSTER_DECK_MIN <= counts["MONSTER"] <= MONSTER_DECK_MAX:
        raise ValueError("Rebirth deck requires between 18 and 22 monsters.")
    if abs(counts["SPELL"] - counts["TRAP"]) > 1:
        raise ValueError("Rebirth deck spells and traps must be balanced.")
    return counts


def get_card(card_id):
    try:
        return deepcopy(CARD_CATALOG_DICT[str(card_id)])
    except KeyError as exc:
        raise ValueError(f"Unknown Rebirth card: {card_id}") from exc


def create_card_instance(card_id, owner, sequence):
    card = get_card(card_id)
    card["owner"] = owner
    card["sequence"] = int(sequence or 0)
    card["instance_id"] = f"{owner}-{int(sequence or 0):02d}-{card['id']}"
    card["status_effects"] = []
    return card


def build_deck(owner, card_ids=None):
    source_ids = list(card_ids or (BOT_DECK if owner == "bot" else PLAYER_DECK))
    return [create_card_instance(card_id, owner, index + 1) for index, card_id in enumerate(source_ids)]


def catalog_payload():
    return [get_card(card_id) for card_id in CARD_CATALOG_DICT]

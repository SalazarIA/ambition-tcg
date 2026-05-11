# =========================================================
# Ambitionz Arena Clean State V50
# Canonical state contract for the clean single-renderer arena.
# =========================================================

from copy import deepcopy

from game.cards import CARD_CATALOG
from game.card_sets import enrich_card_runtime


ARENA_STATE_SCHEMA = "arena_state_v50"
LEGACY_ARENA_SCHEMA = "ambitionz_arena_clean_v50"
ARENA_CLEAN_SCHEMA = ARENA_STATE_SCHEMA


def _int(value, default=0):
    try:
        return int(value if value is not None else default)
    except Exception:
        return default


def _bool(value):
    return bool(value)


def _str(value, default=""):
    if value is None:
        return default
    value = str(value)
    return value if value else default


def card_catalog_by_id():
    catalog = {}

    for card in CARD_CATALOG:
        card_id = (
            card.get("id")
            or card.get("card_id")
            or card.get("runtime_id")
            or card.get("name")
        )

        if card_id:
            catalog[str(card_id)] = card

    return catalog


def hydrate_card(card, index=0):
    if not card:
        return None

    catalog = card_catalog_by_id()

    if isinstance(card, str):
        base = deepcopy(catalog.get(str(card)) or {
            "id": str(card),
            "name": str(card),
            "type": "Monster",
            "element": "Neutral",
            "rarity": "Common",
            "sigil": "None",
            "role": "Balancer",
            "cost": 1,
            "power": 1,
            "value": 1,
            "effect": "",
            "description": "",
        })
    elif isinstance(card, dict):
        raw_id = (
            card.get("id")
            or card.get("card_id")
            or card.get("runtime_id")
            or card.get("name")
        )

        base = deepcopy(catalog.get(str(raw_id)) or {})
        base.update(deepcopy(card))
    else:
        base = {
            "id": f"card-{index}",
            "name": f"Card {index + 1}",
            "type": "Monster",
            "element": "Neutral",
            "rarity": "Common",
            "sigil": "None",
            "role": "Balancer",
            "cost": 1,
            "power": 1,
            "value": 1,
            "effect": "",
            "description": "",
        }

    enriched = enrich_card_runtime(base, index=index)

    card_id = (
        enriched.get("id")
        or enriched.get("card_id")
        or enriched.get("runtime_id")
        or enriched.get("name")
        or f"card-{index}"
    )

    card_type = _str(enriched.get("type"), "Monster")
    is_monster = card_type == "Monster"

    cost = _int(
        enriched.get("cost")
        or enriched.get("energy_cost")
        or enriched.get("mana_cost"),
        1,
    )

    power = _int(
        enriched.get("power")
        or enriched.get("attack")
        or enriched.get("atk")
        or enriched.get("value"),
        0,
    )

    value = _int(
        enriched.get("value")
        or enriched.get("power")
        or enriched.get("attack")
        or enriched.get("atk"),
        0,
    )

    # Hard guard: monsters should never visually render as PWR 0
    # unless the catalog explicitly defines a zero-power monster.
    if is_monster and power <= 0:
        power = max(1, value, cost)

    if not is_monster and value <= 0:
        value = max(1, power, cost)

    return {
        "id": str(card_id),
        "card_id": str(card_id),
        "name": _str(enriched.get("name"), f"Card {index + 1}"),
        "type": card_type,
        "element": _str(enriched.get("element"), "Neutral"),
        "rarity": _str(enriched.get("rarity"), "Common"),
        "sigil": _str(enriched.get("sigil"), "None"),
        "role": _str(enriched.get("role"), "Balancer"),
        "cost": cost,
        "power": power,
        "attack": _int(enriched.get("attack") or power, power),
        "value": value,
        "combat_label": "PWR" if is_monster else "VAL",
        "display_stat": power if is_monster else value,
        "effect": _str(enriched.get("effect") or enriched.get("description"), ""),
        "description": _str(enriched.get("description") or enriched.get("effect"), ""),
        "image": _str(enriched.get("image"), "cards/placeholders/card_placeholder.svg"),
        "set_key": _str(enriched.get("set_key"), "base_250"),
        "set_name": _str(enriched.get("set_name"), "Ambitionz Base Set"),
        "is_monster": is_monster,
    }


def hydrate_cards(cards):
    return [
        hydrated
        for hydrated in (
            hydrate_card(card, index=index)
            for index, card in enumerate(cards or [])
        )
        if hydrated
    ]


def first_card(value):
    if not value:
        return None

    if isinstance(value, list):
        return value[0] if value else None

    return value


def normalize_field(player):
    player = player or {}
    field = player.get("field") or player.get("board") or player.get("zones") or {}

    monster = (
        player.get("field_m")
        or player.get("monster")
        or player.get("monster_zone")
        or player.get("active_monster")
        or field.get("monster")
        or field.get("monster_zone")
        or field.get("active_monster")
    )

    spell = (
        player.get("field_st")
        or player.get("spell")
        or player.get("spell_zone")
        or player.get("support")
        or field.get("spell")
        or field.get("spell_zone")
        or field.get("support")
    )

    trap = (
        player.get("field_t")
        or player.get("trap")
        or player.get("trap_zone")
        or field.get("trap")
        or field.get("trap_zone")
    )

    return {
        "monster": hydrate_card(first_card(monster), 0),
        "spell": hydrate_card(first_card(spell), 1),
        "trap": hydrate_card(first_card(trap), 2),
    }


def normalize_player(player, viewer=False):
    player = player or {}

    raw_hand = player.get("hand") or []
    hand = hydrate_cards(raw_hand) if viewer else []

    energy = _int(player.get("energy") or player.get("current_energy"), 0)
    max_energy = _int(
        player.get("max_energy")
        or player.get("energy_max")
        or player.get("base_energy")
        or energy,
        energy,
    )

    intent = player.get("intent") or player.get("selected_intent")

    if not viewer and intent:
        intent = "Hidden"

    return {
        "sid": player.get("sid"),
        "user_id": player.get("user_id"),
        "name": _str(player.get("name") or player.get("username"), "You" if viewer else "Opponent"),
        "hp": _int(player.get("hp") or player.get("health"), 3600),
        "energy": energy,
        "max_energy": max_energy,
        "ambition": _int(player.get("ambition"), 0),
        "intent": intent or "",
        "ready": _bool(player.get("ready") or player.get("is_ready")),
        "hand": hand,
        "hand_count": len(raw_hand),
        "field": normalize_field(player),
        "deck_count": len(player.get("deck") or []),
        "graveyard_count": len(player.get("graveyard") or player.get("discard") or []),
    }


def resolve_viewer_keys(match, viewer_key="p1"):
    match = match or {}

    if viewer_key == "p2":
        return "p2", "p1"

    viewer_text = str(viewer_key or "")

    p1 = match.get("p1") or {}
    p2 = match.get("p2") or {}

    if viewer_text:
        if viewer_text == str(p2.get("sid")):
            return "p2", "p1"
        if viewer_text == str(p2.get("user_id")):
            return "p2", "p1"
        if viewer_text == str(p2.get("name")):
            return "p2", "p1"

    return "p1", "p2"


def phase_from_match(match, me):
    explicit = match.get("phase")

    if explicit:
        return explicit

    if not me.get("hand"):
        return "start"

    if not me.get("intent"):
        return "intent"

    if not me.get("ready"):
        return "main"

    return "waiting"


def zone_for_card(card):
    ctype = _str(card.get("type") or card.get("card_type") or "Monster").strip().title()

    if ctype == "Spell":
        return "spell"

    if ctype == "Trap":
        return "trap"

    return "monster"


def legal_actions_for(me, phase):
    hand = me.get("hand") or []
    energy = _int(me.get("energy"), 0)
    ready = _bool(me.get("ready"))
    intent = me.get("intent")
    field = me.get("field") or {}

    playable_ids = []

    for card in hand:
        card_id = _str(card.get("id") or card.get("card_id") or card.get("name"), "")
        cost = _int(card.get("cost"), 1)
        zone = zone_for_card(card)

        if not card_id:
            continue

        if cost > energy:
            continue

        if field.get(zone):
            continue

        playable_ids.append(card_id)

    can_start = phase == "start" or not hand
    can_choose_intent = bool(hand) and not ready and phase in ("intent", "main")
    can_play_cards = bool(playable_ids) and not ready and phase in ("main", "intent")
    can_ready = bool(hand) and not ready and phase in ("main", "intent", "waiting")

    return {
        "can_start": can_start,
        "can_choose_intent": can_choose_intent,
        "can_play_cards": can_play_cards,
        "can_ready": can_ready,
        "show_start": can_start,
        "show_intents": can_choose_intent,
        "show_ready": can_ready,
        "playable_card_ids": playable_ids,
        "selected_intent": intent or "",
    }


def message_for(match, me, legal_actions):
    if match.get("message"):
        return match.get("message")

    if not me.get("hand"):
        return "Press Start to draw your hand."

    if not me.get("intent"):
        return "Choose your intent: Strike, Guard or Focus."

    if legal_actions.get("can_play_cards"):
        return "Play a card or press Ready."

    if legal_actions.get("can_ready"):
        return "No playable card with current energy. Press Ready."

    return "Waiting for opponent."


def build_arena_clean_state(match, viewer_key="p1", message=None):
    match = match or {}

    me_key, enemy_key = resolve_viewer_keys(match, viewer_key)
    me = normalize_player(match.get(me_key) or {}, viewer=True)
    enemy = normalize_player(match.get(enemy_key) or {}, viewer=False)

    phase = phase_from_match(match, me)
    legal_actions = legal_actions_for(me, phase)

    return {
        "schema": ARENA_CLEAN_SCHEMA,
        "schema_version": ARENA_CLEAN_SCHEMA,
        "legacy_schema": LEGACY_ARENA_SCHEMA,
        "contract": {
            "name": ARENA_CLEAN_SCHEMA,
            "legacy": LEGACY_ARENA_SCHEMA,
        },
        "match_id": _str(match.get("id") or match.get("match_id") or match.get("room"), ""),
        "viewer_key": me_key,
        "enemy_key": enemy_key,
        "mode": (
            "training"
            if match.get("training") or match.get("mode") == "training"
            else "bot"
            if match.get("is_bot_match")
            else "pvp"
        ),
        "phase": phase,
        "round": _int(match.get("round") or match.get("round_number") or match.get("turn"), 1),
        "message": message or message_for(match, me, legal_actions),
        "me": me,
        "enemy": enemy,
        "legal_actions": legal_actions,
        "events": match.get("events") or [],
        "winner": match.get("winner"),
    }


def build_arena_clean_payloads(match, message=None):
    return {
        "p1": build_arena_clean_state(match, "p1", message=message),
        "p2": build_arena_clean_state(match, "p2", message=message),
    }

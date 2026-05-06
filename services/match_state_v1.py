# =========================================================
# Ambitionz Match State V1
# Canonical payload contract for the rebuilt Arena frontend.
# This does not replace legacy engine logic yet.
# =========================================================

from game.card_sets import enrich_card_runtime


MATCH_STATE_SCHEMA = "ambitionz_match_v1"


def _int(value, default=0):
    try:
        return int(value or default)
    except Exception:
        return default


def _bool(value):
    return bool(value)


def normalize_card(card, index=0):
    if not card:
        return None

    if isinstance(card, str):
        card = {
            "id": card,
            "name": card,
            "type": "Monster",
            "rarity": "Common",
            "effect": "",
        }

    enriched = enrich_card_runtime(card, index=index)

    card_id = (
        enriched.get("id")
        or enriched.get("runtime_id")
        or enriched.get("card_id")
        or enriched.get("name")
        or f"card-{index}"
    )

    return {
        "id": str(card_id),
        "card_id": str(card_id),
        "name": enriched.get("name") or f"Card {index + 1}",
        "type": enriched.get("type") or "Monster",
        "element": enriched.get("element") or "Neutral",
        "rarity": enriched.get("rarity") or "Common",
        "sigil": enriched.get("sigil") or "None",
        "role": enriched.get("role") or "Balancer",
        "cost": _int(enriched.get("cost") or enriched.get("energy_cost"), 1),
        "power": _int(enriched.get("power") or enriched.get("attack") or enriched.get("value"), 0),
        "attack": _int(enriched.get("attack") or enriched.get("power") or enriched.get("value"), 0),
        "defense": _int(enriched.get("defense") or enriched.get("hp") or enriched.get("toughness") or enriched.get("value"), 0),
        "value": _int(enriched.get("value") or enriched.get("power") or enriched.get("attack"), 0),
        "combat_label": "ATK" if (enriched.get("type") or "Monster") == "Monster" else "VALUE",
        "effect": enriched.get("effect") or enriched.get("description") or "",
        "description": enriched.get("description") or enriched.get("effect") or "",
        "image": enriched.get("image") or "cards/placeholders/card_placeholder.svg",
        "set_key": enriched.get("set_key") or "base_250",
        "set_name": enriched.get("set_name") or "Ambitionz Base Set",
        "rarity_css": enriched.get("rarity_css") or "rarity-common",
        "type_css": enriched.get("type_css") or "type-monster",
        "sigil_css": enriched.get("sigil_css") or "sigil-none",
        "role_css": enriched.get("role_css") or "role-balancer",
    }


def normalize_cards(cards):
    return [
        normalized
        for normalized in (
            normalize_card(card, index=index)
            for index, card in enumerate(cards or [])
        )
        if normalized
    ]


def first_zone_card(value):
    if not value:
        return None

    if isinstance(value, list):
        return value[0] if value else None

    return value


def get_from_any(*values):
    for value in values:
        if value is not None:
            return value
    return None


def normalize_field(player):
    player = player or {}
    field = player.get("field") or player.get("board") or player.get("zones") or {}

    monster = get_from_any(
        player.get("monster"),
        player.get("monster_zone"),
        player.get("active_monster"),
        field.get("monster"),
        field.get("monster_zone"),
        field.get("active_monster"),
    )

    spell = get_from_any(
        player.get("spell"),
        player.get("spell_zone"),
        player.get("support"),
        field.get("spell"),
        field.get("spell_zone"),
        field.get("support"),
    )

    trap = get_from_any(
        player.get("trap"),
        player.get("trap_zone"),
        field.get("trap"),
        field.get("trap_zone"),
    )

    field_cards = []

    for key in ("cards", "field_cards", "board_cards"):
        value = field.get(key)

        if isinstance(value, list):
            field_cards.extend(value)

    if isinstance(player.get("field_cards"), list):
        field_cards.extend(player.get("field_cards"))

    return {
        "monster": normalize_card(first_zone_card(monster), 0),
        "spell": normalize_card(first_zone_card(spell), 1),
        "trap": normalize_card(first_zone_card(trap), 2),
        "cards": normalize_cards(field_cards),
    }


def playable_card_ids(player):
    player = player or {}
    hand = normalize_cards(player.get("hand") or [])
    energy = _int(player.get("energy") or player.get("current_energy"), 0)

    ids = []

    for card in hand:
        if _int(card.get("cost"), 1) <= energy:
            ids.append(card["id"])

    return ids


def normalize_player(player, viewer=False):
    player = player or {}
    hand_raw = player.get("hand") or []
    hand = normalize_cards(hand_raw) if viewer else []

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
        "name": player.get("name") or player.get("username") or ("You" if viewer else "Opponent"),
        "hp": _int(player.get("hp") or player.get("health"), 3600),
        "energy": energy,
        "max_energy": max_energy,
        "ambition": _int(player.get("ambition"), 0),
        "intent": intent,
        "ready": _bool(player.get("ready") or player.get("is_ready")),
        "hand": hand,
        "hand_count": len(hand_raw),
        "field": normalize_field(player),
        "deck_count": len(player.get("deck") or []),
        "graveyard_count": len(player.get("graveyard") or player.get("discard") or []),
    }


def viewer_keys(viewer_key):
    if viewer_key == "p2":
        return "p2", "p1"

    return "p1", "p2"


def current_phase(match, me):
    if match.get("phase"):
        return match.get("phase")

    if not me.get("intent"):
        return "intent"

    if not me.get("ready"):
        return "main"

    return "waiting"


def build_legal_actions(me):
    playable = playable_card_ids({
        "hand": me.get("hand") or [],
        "energy": me.get("energy") or 0,
    })

    return {
        "can_choose_intent": not bool(me.get("ready")),
        "can_play_cards": bool(playable) and not bool(me.get("ready")),
        "can_ready": not bool(me.get("ready")),
        "playable_card_ids": playable,
    }


def build_message(me, legal_actions):
    if not me.get("hand"):
        return "Your hand is empty or not synced yet."

    if not me.get("intent"):
        return "Choose Strike, Guard or Focus."

    if legal_actions.get("can_play_cards"):
        return "Play a card or press Ready."

    if legal_actions.get("can_ready"):
        return "No playable card with current energy. Press Ready."

    return "Waiting for opponent."


def build_match_state_v1(match, viewer_key="p1", message=None):
    match = match or {}

    me_key, enemy_key = viewer_keys(viewer_key)

    me = normalize_player(match.get(me_key) or {}, viewer=True)
    enemy = normalize_player(match.get(enemy_key) or {}, viewer=False)

    phase = current_phase(match, me)
    legal_actions = build_legal_actions(me)

    return {
        "schema": MATCH_STATE_SCHEMA,
        "match_id": str(match.get("id") or match.get("match_id") or match.get("room") or ""),
        "mode": (
            "training"
            if match.get("training")
            else "bot"
            if match.get("is_bot_match")
            else "pvp"
        ),
        "round": _int(match.get("round") or match.get("round_number") or match.get("turn"), 1),
        "phase": phase,
        "viewer_key": me_key,
        "enemy_key": enemy_key,
        "me": me,
        "enemy": enemy,
        "legal_actions": legal_actions,
        "message": message or build_message(me, legal_actions),
        "events": match.get("events", [])[-8:],
        "winner": match.get("winner"),
    }


def build_match_state_payloads(match, message=None):
    return {
        "p1": build_match_state_v1(match, viewer_key="p1", message=message),
        "p2": build_match_state_v1(match, viewer_key="p2", message=message),
    }

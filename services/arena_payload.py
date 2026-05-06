# =========================================================
# Ambitionz Arena Payload Builder
# Canonical frontend payload for Arena V8+.
# =========================================================

from game.card_sets import enrich_card_runtime


def safe_int(value, default=0):
    try:
        return int(value or default)
    except Exception:
        return default


def normalize_card_for_payload(card, index=0):
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

    return {
        "id": str(enriched.get("id") or enriched.get("runtime_id") or enriched.get("name") or f"card-{index}"),
        "card_id": str(enriched.get("id") or enriched.get("runtime_id") or enriched.get("name") or f"card-{index}"),
        "name": enriched.get("name") or f"Card {index + 1}",
        "type": enriched.get("type") or "Monster",
        "element": enriched.get("element") or "Neutral",
        "rarity": enriched.get("rarity") or "Common",
        "rarity_css": enriched.get("rarity_css") or "rarity-common",
        "sigil": enriched.get("sigil") or "None",
        "sigil_css": enriched.get("sigil_css") or "sigil-none",
        "role": enriched.get("role") or "Balancer",
        "role_css": enriched.get("role_css") or "role-balancer",
        "cost": safe_int(enriched.get("cost") or enriched.get("energy_cost"), 1),
        "power": safe_int(enriched.get("power") or enriched.get("attack") or enriched.get("value"), 0),
        "value": safe_int(enriched.get("value") or enriched.get("power"), 0),
        "effect": enriched.get("effect") or enriched.get("description") or "",
        "description": enriched.get("description") or enriched.get("effect") or "",
        "set_key": enriched.get("set_key") or "base_250",
        "set_name": enriched.get("set_name") or "Ambitionz Base Set",
        "image": enriched.get("image") or "cards/placeholders/card_placeholder.svg",
    }


def normalize_card_list(cards):
    return [
        normalized
        for normalized in (
            normalize_card_for_payload(card, index=index)
            for index, card in enumerate(cards or [])
        )
        if normalized
    ]


def first_card(zone):
    if not zone:
        return None

    if isinstance(zone, list):
        return zone[0] if zone else None

    return zone


def normalize_field(player):
    if not player:
        return {
            "monster": None,
            "spell": None,
            "trap": None,
            "cards": [],
        }

    field = player.get("field") or player.get("board") or {}

    monster = (
        player.get("monster")
        or player.get("monster_zone")
        or field.get("monster")
        or field.get("monster_zone")
        or field.get("active_monster")
    )

    spell = (
        player.get("spell")
        or player.get("spell_zone")
        or field.get("spell")
        or field.get("spell_zone")
        or field.get("support")
    )

    trap = (
        player.get("trap")
        or player.get("trap_zone")
        or field.get("trap")
        or field.get("trap_zone")
    )

    cards = []

    for key in ["cards", "field_cards", "board_cards"]:
        if isinstance(field.get(key), list):
            cards.extend(field.get(key))

    if isinstance(player.get("field_cards"), list):
        cards.extend(player.get("field_cards"))

    return {
        "monster": normalize_card_for_payload(first_card(monster), 0),
        "spell": normalize_card_for_payload(first_card(spell), 1),
        "trap": normalize_card_for_payload(first_card(trap), 2),
        "cards": normalize_card_list(cards),
    }


def normalize_player(player, viewer=False):
    player = player or {}

    hand = normalize_card_list(player.get("hand") or [])

    max_energy = (
        player.get("max_energy")
        or player.get("energy_max")
        or player.get("base_energy")
        or player.get("energy")
        or 0
    )

    return {
        "sid": player.get("sid"),
        "user_id": player.get("user_id"),
        "name": player.get("name") or player.get("username") or ("You" if viewer else "Opponent"),
        "hp": safe_int(player.get("hp") or player.get("health"), 3600),
        "energy": safe_int(player.get("energy") or player.get("current_energy"), 0),
        "max_energy": safe_int(max_energy, 0),
        "ambition": safe_int(player.get("ambition"), 0),
        "intent": player.get("intent") or player.get("selected_intent") or "Hidden",
        "ready": bool(player.get("ready") or player.get("is_ready")),
        "deck_count": len(player.get("deck") or []),
        "graveyard_count": len(player.get("graveyard") or player.get("discard") or []),
        "hand": hand if viewer else [],
        "hand_count": len(player.get("hand") or []),
        "field": normalize_field(player),
    }


def get_player_keys(match, viewer_key=None):
    if viewer_key in ("p1", "p2"):
        me_key = viewer_key
    else:
        me_key = "p1"

    enemy_key = "p2" if me_key == "p1" else "p1"
    return me_key, enemy_key


def build_arena_state_payload(match, viewer_key=None, phase=None, message=None):
    match = match or {}
    me_key, enemy_key = get_player_keys(match, viewer_key=viewer_key)

    me = normalize_player(match.get(me_key) or {}, viewer=True)
    enemy = normalize_player(match.get(enemy_key) or {}, viewer=False)

    round_number = (
        match.get("round")
        or match.get("round_number")
        or match.get("turn")
        or 1
    )

    resolved_phase = (
        phase
        or match.get("phase")
        or match.get("turn_phase")
        or "Battle"
    )

    status_message = message

    if not status_message:
        if not me["hand"]:
            status_message = "Start the duel or wait for your hand."
        elif not me["intent"] or me["intent"] == "Hidden":
            status_message = "Choose your intent."
        elif not me["ready"]:
            status_message = "Play a card if possible, then press Ready."
        else:
            status_message = "Waiting for opponent."

    return {
        "schema": "arena_state_v8",
        "round": safe_int(round_number, 1),
        "phase": resolved_phase,
        "message": status_message,
        "viewer_key": me_key,
        "enemy_key": enemy_key,
        "me": me,
        "enemy": enemy,
        "my_hand": me["hand"],
        "hand": me["hand"],
        "enemy_hand_count": enemy["hand_count"],
        "can_act": not me["ready"],
        "training": bool(match.get("training")),
        "is_bot_match": bool(match.get("is_bot_match") or match.get("training")),
    }


def build_arena_payloads_for_match(match, phase=None, message=None):
    return {
        "p1": build_arena_state_payload(match, viewer_key="p1", phase=phase, message=message),
        "p2": build_arena_state_payload(match, viewer_key="p2", phase=phase, message=message),
    }

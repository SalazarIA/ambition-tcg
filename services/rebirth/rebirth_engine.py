from copy import deepcopy

from services.rebirth.rebirth_state import (
    activate_card_from_hand,
    create_rebirth_match,
    draw_card,
    get_opponent_side,
    get_side,
)


VALID_REBIRTH_INTENTS = {"STRIKE", "GUARD", "FOCUS"}
DAMAGE_CAP = 10


def add_log(match, event_type, payload=None):
    log = match.setdefault("combat_log", [])
    entry = {
        "id": len(log) + 1,
        "round": match.get("round", 1),
        "phase": match.get("phase", "START"),
        "type": event_type,
        "payload": payload or {},
    }
    entry["message"] = _message_for_event(entry)
    log.append(entry)
    return entry


def _message_for_event(entry):
    payload = entry.get("payload") or {}
    event_type = entry.get("type")
    if event_type == "match_start":
        return "Rebirth match initialized."
    if event_type == "round_start":
        return f"Round {payload.get('round', entry.get('round'))} begins."
    if event_type == "draw":
        return f"{payload.get('side', 'A side').title()} draws {payload.get('count', 1)} card(s)."
    if event_type == "intent_selected":
        return f"{payload.get('side', 'A side').title()} chooses {payload.get('intent')}."
    if event_type == "active_card_replaced":
        return f"{payload.get('side', 'A side').title()} replaces {payload.get('old_card_name')} with {payload.get('new_card_name')}."
    if event_type == "card_activated":
        return f"{payload.get('card_name')} enters for {payload.get('side', 'a side').title()}."
    if event_type == "attack_calculated":
        return f"{payload.get('side', 'A side').title()} prepares {payload.get('attack', 0)} pressure."
    if event_type == "guard_applied":
        return f"{payload.get('side', 'A side').title()} absorbs {payload.get('amount', 0)} pressure."
    if event_type == "ambition_gained":
        return f"{payload.get('side', 'A side').title()} gains {payload.get('amount', 0)} Ambition."
    if event_type == "damage_dealt":
        return f"{payload.get('target', 'A side').title()} takes {payload.get('amount', 0)} damage."
    if event_type == "round_resolved":
        return f"Round {payload.get('round', entry.get('round'))} resolves."
    if event_type == "match_finished":
        return f"{payload.get('winner', 'A side').title()} wins the duel."
    if event_type == "round_end":
        return f"Round {payload.get('round')} ends."
    return event_type.replace("_", " ").title()


def _cinematic(match, event_type, payload=None):
    normalized = str(event_type or "ROUND_END").upper()
    details = payload or {}
    titles = {
        "MATCH_START": ("Core Online", "The Rebirth arena wakes.", "low"),
        "ROUND_START": ("Round Ignition", f"Round {match.get('round', 1)} begins.", "low"),
        "STRIKE": ("Strike Declared", f"{details.get('side', 'A side').title()} commits to pressure.", "medium"),
        "GUARD": ("Guard Raised", f"{details.get('side', 'A side').title()} braces for impact.", "medium"),
        "FOCUS": ("Ambition Focused", f"{details.get('side', 'A side').title()} draws power inward.", "medium"),
        "CARD_ACTIVATED": ("Card Activated", f"{details.get('card_name') or 'A card'} takes the arena.", "medium"),
        "DAMAGE": ("Damage Lands", f"{details.get('target', 'A side').title()} takes {details.get('amount', 0)} damage.", "high"),
        "KO": ("Will Broken", f"{details.get('winner', 'A side').title()} ends the duel.", "high"),
        "ROUND_END": ("Round Sealed", f"Round {details.get('round', match.get('round', 1))} closes.", "low"),
    }
    title, message, intensity = titles.get(normalized, ("Arena Shift", normalized.replace("_", " ").title(), "low"))
    match["cinematic_event"] = {
        "type": normalized,
        "title": title,
        "message": message,
        "intensity": intensity,
        "payload": details,
        "round": match.get("round", 1),
    }
    return match["cinematic_event"]


def start_rebirth_match(seed=None):
    match = create_rebirth_match(seed=seed)
    add_log(match, "match_start", {"match_id": match["match_id"]})
    _cinematic(match, "MATCH_START", {"match_id": match["match_id"]})
    start_rebirth_round(match)
    return match


def start_rebirth_round(match):
    if match.get("is_finished"):
        return match
    match["phase"] = "START"
    add_log(match, "round_start", {"round": match.get("round", 1)})
    _cinematic(match, "ROUND_START", {"round": match.get("round", 1)})
    if match.get("round", 1) > 1:
        match["phase"] = "DRAW"
        for side in ("player", "opponent"):
            if draw_card(match[side]):
                add_log(match, "draw", {"side": side, "count": 1})
    match["player"]["selected_intent"] = None
    match["opponent"]["selected_intent"] = None
    match["phase"] = "INTENT"
    return match


def select_intent(match, side, intent):
    if match.get("is_finished"):
        raise ValueError("Match is finished.")
    intent_key = str(intent or "").upper()
    if intent_key not in VALID_REBIRTH_INTENTS:
        raise ValueError("Invalid Rebirth intent.")
    get_side(match, side)["selected_intent"] = intent_key
    match["phase"] = "ACTION"
    add_log(match, "intent_selected", {"side": side, "intent": intent_key})
    _cinematic(match, intent_key, {"side": side, "intent": intent_key})
    return match


def play_rebirth_card(match, side, card_id):
    if match.get("is_finished"):
        raise ValueError("Match is finished.")
    side_state = get_side(match, side)
    previous = deepcopy(side_state.get("active_card")) if side_state.get("active_card") else None
    card = activate_card_from_hand(match, side, card_id)
    match["phase"] = "ACTION"
    if previous:
        add_log(
            match,
            "active_card_replaced",
            {
                "side": side,
                "old_card_id": previous.get("id"),
                "old_card_name": previous.get("name"),
                "new_card_id": card.get("id"),
                "new_card_name": card.get("name"),
            },
        )
    add_log(match, "card_activated", {"side": side, "card_id": card["id"], "card_name": card["name"]})
    _cinematic(match, "CARD_ACTIVATED", {"side": side, "card_id": card["id"], "card_name": card["name"], "card": deepcopy(card)})
    return card


def _choose_bot_card(match):
    opponent = match["opponent"]
    if opponent.get("active_card") or not opponent.get("hand"):
        return None
    return sorted(
        opponent["hand"],
        key=lambda card: (
            int(card.get("attack", 0)) + int(card.get("guard", 0)) + int(card.get("ambition", 0)),
            card.get("id", ""),
        ),
        reverse=True,
    )[0]


def _choose_bot_intent(match):
    opponent = match["opponent"]
    if opponent.get("hp", 0) <= 10:
        return "GUARD"
    if match["player"].get("hp", 0) <= 8:
        return "STRIKE"
    return "FOCUS"


def bot_select_action(match):
    if match.get("is_finished"):
        return match
    card = _choose_bot_card(match)
    if card:
        play_rebirth_card(match, "opponent", card["id"])
    if not match["opponent"].get("selected_intent"):
        select_intent(match, "opponent", _choose_bot_intent(match))
    return match


def _base_attack(side_state):
    active = side_state.get("active_card") or {}
    return max(1, int(active.get("attack", 1) or 1))


def _incoming_guard(side_state):
    return 3 if side_state.get("selected_intent") == "GUARD" else 0


def _outgoing_attack(side_state):
    attack = _base_attack(side_state)
    if side_state.get("selected_intent") == "STRIKE":
        attack += 2
    if side_state.get("selected_intent") == "FOCUS" and int(side_state.get("ambition", 0) or 0) >= 6:
        attack += 1
    return attack


def _apply_focus(match, side):
    side_state = match[side]
    if side_state.get("selected_intent") == "FOCUS":
        side_state["ambition"] = int(side_state.get("ambition", 0) or 0) + 2
        add_log(match, "ambition_gained", {"side": side, "amount": 2, "total": side_state["ambition"]})
        _cinematic(match, "FOCUS", {"side": side, "amount": 2, "total": side_state["ambition"]})


def _deal_damage(match, source, target, amount):
    amount = max(0, int(amount or 0))
    match[target]["hp"] = max(0, int(match[target].get("hp", 0) or 0) - amount)
    add_log(match, "damage_dealt", {"source": source, "target": target, "amount": amount, "target_hp": match[target]["hp"]})
    if amount > 0:
        _cinematic(match, "DAMAGE", {"source": source, "target": target, "amount": amount, "target_hp": match[target]["hp"]})


def _check_winner(match):
    player_down = match["player"]["hp"] <= 0
    opponent_down = match["opponent"]["hp"] <= 0
    if player_down and opponent_down:
        winner = "draw"
    elif opponent_down:
        winner = "player"
    elif player_down:
        winner = "opponent"
    else:
        return None

    match["winner"] = winner
    match["is_finished"] = True
    add_log(match, "match_finished", {"winner": winner})
    _cinematic(match, "KO", {"winner": winner})
    return winner


def _damage_to_apply(match, source, target):
    source_state = match[source]
    target_state = match[target]
    attack = _outgoing_attack(source_state)
    add_log(
        match,
        "attack_calculated",
        {
            "side": source,
            "intent": source_state.get("selected_intent"),
            "base_attack": _base_attack(source_state),
            "attack": attack,
        },
    )
    guard = _incoming_guard(target_state)
    if guard:
        add_log(match, "guard_applied", {"side": target, "amount": guard})
        _cinematic(match, "GUARD", {"side": target, "amount": guard})
    return min(DAMAGE_CAP, max(0, attack - guard))


def resolve_rebirth_round(match):
    if match.get("is_finished"):
        return match
    bot_select_action(match)
    if not match["player"].get("selected_intent"):
        select_intent(match, "player", "FOCUS")
    if not match["opponent"].get("selected_intent"):
        select_intent(match, "opponent", "FOCUS")

    match["phase"] = "RESOLVE"
    _apply_focus(match, "player")
    _apply_focus(match, "opponent")

    player_damage = _damage_to_apply(match, "player", "opponent")
    opponent_damage = _damage_to_apply(match, "opponent", "player")

    _deal_damage(match, "player", "opponent", player_damage)
    _deal_damage(match, "opponent", "player", opponent_damage)
    _check_winner(match)
    if not match.get("is_finished"):
        add_log(
            match,
            "round_resolved",
            {
                "round": match.get("round", 1),
                "player_damage": player_damage,
                "opponent_damage": opponent_damage,
            },
        )
        cleanup_rebirth_round(match)
    return match


def cleanup_rebirth_round(match):
    ended_round = match.get("round", 1)
    match["phase"] = "CLEANUP"
    add_log(match, "round_end", {"round": ended_round})
    _cinematic(match, "round_end", {"round": ended_round})
    match["round"] = ended_round + 1
    start_rebirth_round(match)
    return match

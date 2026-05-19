from copy import deepcopy

from services.rebirth.rebirth_state import (
    activate_card_from_hand,
    create_rebirth_match,
    draw_card,
    get_opponent_side,
    get_side,
)


VALID_REBIRTH_INTENTS = {"STRIKE", "GUARD", "FOCUS"}


def add_log(match, event_type, payload=None):
    entry = {
        "round": match.get("round", 1),
        "phase": match.get("phase", "START"),
        "type": event_type,
        "payload": payload or {},
    }
    entry["message"] = _message_for_event(entry)
    match.setdefault("combat_log", []).append(entry)
    return entry


def _message_for_event(entry):
    payload = entry.get("payload") or {}
    event_type = entry.get("type")
    if event_type == "match_start":
        return "Rebirth match initialized."
    if event_type == "draw":
        return f"{payload.get('side', 'A side')} draws {payload.get('count', 1)} card(s)."
    if event_type == "intent_selected":
        return f"{payload.get('side', 'A side')} chooses {payload.get('intent')}."
    if event_type == "card_activated":
        return f"{payload.get('side', 'A side')} activates {payload.get('card_name')}."
    if event_type == "focus":
        return f"{payload.get('side', 'A side')} gains {payload.get('amount', 0)} Ambition."
    if event_type == "damage":
        return f"{payload.get('source', 'A side')} deals {payload.get('amount', 0)} damage to {payload.get('target', 'the rival')}."
    if event_type == "ko":
        return f"{payload.get('winner', 'A side')} wins the clash."
    if event_type == "round_end":
        return f"Round {payload.get('round')} ends."
    return event_type.replace("_", " ").title()


def _cinematic(match, event_type, payload=None):
    match["cinematic_event"] = {"type": event_type, "payload": payload or {}, "round": match.get("round", 1)}
    return match["cinematic_event"]


def start_rebirth_match(seed=None):
    match = create_rebirth_match(seed=seed)
    add_log(match, "match_start", {"match_id": match["match_id"]})
    _cinematic(match, "match_start", {"match_id": match["match_id"]})
    start_rebirth_round(match)
    return match


def start_rebirth_round(match):
    if match.get("is_finished"):
        return match
    match["phase"] = "DRAW"
    if match.get("round", 1) > 1:
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
    _cinematic(match, intent_key.lower(), {"side": side, "intent": intent_key})
    return match


def play_rebirth_card(match, side, card_id):
    if match.get("is_finished"):
        raise ValueError("Match is finished.")
    card = activate_card_from_hand(match, side, card_id)
    match["phase"] = "ACTION"
    add_log(match, "card_activated", {"side": side, "card_id": card["id"], "card_name": card["name"]})
    _cinematic(match, "card_activated", {"side": side, "card": deepcopy(card)})
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
    active = opponent.get("active_card") or {}
    if opponent.get("hp", 0) <= 12:
        return "GUARD"
    if opponent.get("ambition", 0) < 4 and match.get("round", 1) % 2 == 0:
        return "FOCUS"
    if int(active.get("attack", 0) or 0) >= 4:
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
    return int(active.get("attack", 1) or 1)


def _incoming_guard(side_state):
    return 3 if side_state.get("selected_intent") == "GUARD" else 0


def _outgoing_attack(side_state):
    attack = _base_attack(side_state)
    if side_state.get("selected_intent") == "STRIKE":
        attack += 2
    return attack


def _apply_focus(match, side):
    side_state = match[side]
    if side_state.get("selected_intent") == "FOCUS":
        side_state["ambition"] = int(side_state.get("ambition", 0) or 0) + 2
        add_log(match, "focus", {"side": side, "amount": 2})
        _cinematic(match, "focus", {"side": side, "amount": 2})


def _deal_damage(match, source, target, amount):
    amount = max(0, int(amount or 0))
    match[target]["hp"] = max(0, int(match[target].get("hp", 0) or 0) - amount)
    add_log(match, "damage", {"source": source, "target": target, "amount": amount, "target_hp": match[target]["hp"]})
    _cinematic(match, "damage", {"source": source, "target": target, "amount": amount})


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
    add_log(match, "ko", {"winner": winner})
    _cinematic(match, "ko", {"winner": winner})
    return winner


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

    player_damage = max(0, _outgoing_attack(match["player"]) - _incoming_guard(match["opponent"]))
    opponent_damage = max(0, _outgoing_attack(match["opponent"]) - _incoming_guard(match["player"]))

    _deal_damage(match, "player", "opponent", player_damage)
    _deal_damage(match, "opponent", "player", opponent_damage)
    _check_winner(match)
    if not match.get("is_finished"):
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


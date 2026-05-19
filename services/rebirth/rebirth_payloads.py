from copy import deepcopy


def compact_card(card):
    if not card:
        return None
    keys = [
        "id",
        "name",
        "element",
        "archetype",
        "rarity",
        "cost",
        "attack",
        "guard",
        "ambition",
        "text",
        "role",
        "model_key",
        "fx_key",
    ]
    return {key: deepcopy(card.get(key)) for key in keys}


def _public_side(side_state, include_hand=False):
    payload = {
        "name": side_state.get("name"),
        "hp": int(side_state.get("hp", 0) or 0),
        "ambition": int(side_state.get("ambition", 0) or 0),
        "active_card": compact_card(side_state.get("active_card")),
        "selected_intent": side_state.get("selected_intent"),
    }
    if include_hand:
        payload["hand"] = [compact_card(card) for card in side_state.get("hand", [])]
    return payload


def available_actions(match, side="player"):
    side_state = match.get(side, {})
    if match.get("is_finished"):
        return [{"type": "restart", "enabled": True}]

    actions = [
        {"type": "intent", "intent": "STRIKE", "enabled": True},
        {"type": "intent", "intent": "GUARD", "enabled": True},
        {"type": "intent", "intent": "FOCUS", "enabled": True},
    ]
    actions.extend(
        {
            "type": "play_card",
            "card_id": card.get("id"),
            "enabled": True,
        }
        for card in side_state.get("hand", [])
    )
    actions.append({"type": "resolve", "enabled": bool(side_state.get("selected_intent"))})
    actions.append({"type": "restart", "enabled": True})
    return actions


def public_rebirth_state(match):
    player = _public_side(match["player"], include_hand=True)
    opponent = _public_side(match["opponent"], include_hand=False)
    actions = available_actions(match, "player")
    return {
        "match_id": match.get("match_id"),
        "phase": match.get("phase"),
        "round": match.get("round"),
        "player": player,
        "opponent": opponent,
        "active_card": player.get("active_card"),
        "hand": player.get("hand", []),
        "available_actions": actions,
        "selected_intent": player.get("selected_intent"),
        "combat_log": list(match.get("combat_log", []))[-12:],
        "cinematic_event": match.get("cinematic_event"),
        "ui_flags": {
            "can_resolve": any(action["type"] == "resolve" and action.get("enabled") for action in actions),
            "can_play_card": any(action["type"] == "play_card" and action.get("enabled") for action in actions),
            "is_finished": bool(match.get("is_finished")),
        },
        "winner": match.get("winner"),
        "is_finished": bool(match.get("is_finished")),
    }

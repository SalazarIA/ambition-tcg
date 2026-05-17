"""Deterministic bot policy for Ascension Duel training."""

from __future__ import annotations

from services.ascension_engine import (
    AscensionActionError,
    attempt_dominate,
    can_dominate,
    choose_intent,
    draw_cards,
    get_side,
    play_card,
)


BOT_PROFILES = {
    "Aggressor": {
        "label": "Aggressor",
        "description": "Presses Strike, direct Techniques and early Domination windows.",
        "intent_bias": "Strike",
    },
    "Controller": {
        "label": "Controller",
        "description": "Reads the player's Intent and answers with containment.",
        "intent_bias": "Scheme",
    },
    "Opportunist": {
        "label": "Opportunist",
        "description": "Burns for Ambition and pivots when the player repeats a pattern.",
        "intent_bias": "Scheme",
    },
    "Defensive": {
        "label": "Defensive",
        "description": "Protects HP, equips Relics and wins by attrition.",
        "intent_bias": "Guard",
    },
    "Ascender": {
        "label": "Ascender",
        "description": "Focuses Ambition and seeks Ascension before committing pressure.",
        "intent_bias": "Focus",
    },
}


def normalize_bot_profile(profile):
    if isinstance(profile, dict):
        profile = profile.get("label") or profile.get("name")
    value = str(profile or "").strip().title()
    return value if value in BOT_PROFILES else "Controller"


def bot_profile_payload(profile):
    key = normalize_bot_profile(profile)
    payload = dict(BOT_PROFILES[key])
    payload["key"] = key
    return payload


def _profile_for_match(match, profile=None):
    return normalize_bot_profile(profile or match.get("bot_profile") or "Controller")


def _first_card(side_state, card_type):
    for card in side_state.get("hand", []):
        if card.get("type") == card_type:
            return card
    return None


def choose_bot_intent(match, profile=None):
    profile = _profile_for_match(match, profile)
    bot = get_side(match, "opponent")
    player = get_side(match, "player")

    if profile == "Aggressor" and bot.get("hp", 30) > 8:
        return "Strike"
    if profile == "Ascender" and bot.get("ambition", 0) < 7:
        return "Focus"
    if profile == "Defensive" and bot.get("hp", 30) <= 20:
        return "Guard"
    if player.get("previous_intent") and player.get("intent") == player.get("previous_intent"):
        return "Scheme"
    if profile == "Opportunist" and player.get("previous_intent"):
        return "Scheme"
    if bot.get("ambition", 0) < 4:
        return "Focus"
    if bot.get("hp", 30) <= 12:
        return "Guard"
    if bot.get("active_champion") and len(bot.get("bound_souls", [])) >= 2:
        return "Strike"

    player_intent = player.get("intent") or player.get("previous_intent")
    if player_intent == "Focus":
        return "Strike"
    if player_intent == "Strike":
        return "Guard"
    if player_intent == "Guard":
        return "Focus"
    return "Strike"


def ensure_bot_has_active_champion(match):
    bot = get_side(match, "opponent")
    if bot.get("active_champion"):
        return None

    champion = _first_card(bot, "champion")
    if champion:
        play_card(match, "opponent", champion["id"], mode="summon")
        return {"card_id": champion["id"], "mode": "summon"}

    draw_cards(match, "opponent", 1)
    champion = _first_card(bot, "champion")
    if champion:
        play_card(match, "opponent", champion["id"], mode="summon")
        return {"card_id": champion["id"], "mode": "summon"}
    return None


def choose_bot_card_action(match, profile=None):
    profile = _profile_for_match(match, profile)
    bot = get_side(match, "opponent")

    if not bot.get("active_champion"):
        champion = _first_card(bot, "champion")
        if champion:
            return {"card_id": champion["id"], "mode": "summon"}

    if profile == "Ascender" and bot.get("active_champion"):
        ascension = _first_card(bot, "ascension")
        if ascension and bot.get("ambition", 0) >= ascension.get("ambition_cost", 99):
            return {"card_id": ascension["id"], "mode": "ascend"}

    if bot.get("active_champion") and len(bot.get("bound_souls", [])) < 3 and profile != "Aggressor":
        champion = _first_card(bot, "champion")
        if champion:
            return {"card_id": champion["id"], "mode": "bind"}

    if not bot.get("relic"):
        relic = _first_card(bot, "relic")
        if relic:
            return {"card_id": relic["id"], "mode": "equip"}

    if len(bot.get("schemes", [])) < 2 and profile in {"Controller", "Opportunist", "Defensive"}:
        scheme = _first_card(bot, "scheme")
        if scheme:
            return {"card_id": scheme["id"], "mode": "set"}

    if bot.get("active_champion"):
        ascension = _first_card(bot, "ascension")
        if ascension and bot.get("ambition", 0) >= ascension.get("ambition_cost", 99):
            return {"card_id": ascension["id"], "mode": "ascend"}

    technique = _first_card(bot, "technique")
    if technique and profile in {"Aggressor", "Opportunist", "Controller"}:
        return {"card_id": technique["id"], "mode": "cast"}

    if bot.get("hand") and (bot.get("ambition", 0) < 6 or profile in {"Ascender", "Opportunist"}):
        return {"card_id": bot["hand"][0]["id"], "mode": "burn"}

    if technique:
        return {"card_id": technique["id"], "mode": "cast"}

    return None


def maybe_choose_dominate(match, profile=None):
    profile = _profile_for_match(match, profile)
    bot = get_side(match, "opponent")
    player = get_side(match, "player")
    threshold = 18 if profile == "Aggressor" else 16 if profile == "Opportunist" else 12
    if profile == "Defensive" and not bot.get("ascended"):
        return {"ok": False, "code": "dominate_deferred"}
    if can_dominate(match, "opponent") and (player.get("hp", 30) <= threshold or bot.get("ascended")):
        return attempt_dominate(match, "opponent")
    return {"ok": False, "code": "dominate_deferred"}


def run_bot_turn(match, profile=None):
    """Choose bot intent and one useful card action without getting stuck."""

    if match.get("winner"):
        return match

    profile = _profile_for_match(match, profile)
    match["bot_profile"] = profile
    ensure_bot_has_active_champion(match)

    if not get_side(match, "opponent").get("intent"):
        choose_intent(match, "opponent", choose_bot_intent(match, profile=profile))

    maybe_choose_dominate(match, profile=profile)

    action = choose_bot_card_action(match, profile=profile)
    if not action:
        return match

    try:
        play_card(match, "opponent", action["card_id"], mode=action["mode"])
    except AscensionActionError:
        bot = get_side(match, "opponent")
        if bot.get("hand"):
            try:
                play_card(match, "opponent", bot["hand"][0]["id"], mode="burn")
            except AscensionActionError:
                return match
    return match

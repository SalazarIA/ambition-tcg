"""Deterministic Ascension Duel engine for Ambitionz."""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timezone

from services.ascension_cards import build_ascension_starter_deck, get_card_by_id


VERSION = "ascension_duel_v1"
VALID_SIDES = ("player", "opponent")
VALID_INTENTS = ("Strike", "Guard", "Focus", "Scheme")
MAX_BOUND_SOULS = 3
MAX_SCHEMES = 3
MAX_HP = 30
DOMINATE_COST = 20


class AscensionActionError(Exception):
    """Controlled engine error with a stable public payload."""

    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self):
        return {"code": self.code, "message": self.message, "details": self.details}


def _copy(value):
    return copy.deepcopy(value)


def _seed_text(seed):
    return "ambitionz-ascension" if seed is None else str(seed)


def _match_id(seed):
    digest = hashlib.sha1(_seed_text(seed).encode("utf-8")).hexdigest()[:12]
    return f"asc-{digest}"


def _normalize_deck(deck, seed):
    if deck is None:
        return build_ascension_starter_deck(seed=seed)

    normalized = []
    for entry in deck:
        card = get_card_by_id(entry) if isinstance(entry, str) else _copy(entry)
        if not isinstance(card, dict) or not card.get("id"):
            raise AscensionActionError("invalid_deck", "Deck contains an unknown Ascension card.")
        normalized.append(card)
    return normalized


def _make_side(name, deck):
    return {
        "name": name,
        "hp": MAX_HP,
        "ambition": 0,
        "deck": deck,
        "hand": [],
        "echo": [],
        "active_champion": None,
        "bound_souls": [],
        "relic": None,
        "schemes": [],
        "intent": None,
        "previous_intent": None,
        "status": {},
        "last_actions": [],
        "domination_marks": 0,
        "ascended": False,
    }


def create_match(seed=None, player_deck=None, opponent_deck=None, bot_profile=None):
    """Create and start a deterministic Ascension Duel match."""

    bot_profile = str(bot_profile or "Controller").strip() or "Controller"
    match = {
        "id": _match_id(seed),
        "version": VERSION,
        "round": 0,
        "phase": "created",
        "player": _make_side("You", _normalize_deck(player_deck, f"{_seed_text(seed)}:player")),
        "opponent": _make_side("Rival", _normalize_deck(opponent_deck, f"{_seed_text(seed)}:opponent")),
        "bot_profile": bot_profile,
        "chronicle": [],
        "winner": None,
        "seed": seed,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _chronicle(match, "match_created", "The Duel Altar wakes. Two ambitions answer.")
    start_round(match)
    return match


def get_side(match, side):
    if side not in VALID_SIDES:
        raise AscensionActionError("invalid_side", "Side must be player or opponent.", {"side": side})
    return match[side]


def get_opponent_side(side):
    if side == "player":
        return "opponent"
    if side == "opponent":
        return "player"
    raise AscensionActionError("invalid_side", "Side must be player or opponent.", {"side": side})


def _chronicle(match, event_type, message, side=None, payload=None):
    match.setdefault("chronicle", []).append(
        {
            "round": match.get("round", 0),
            "type": event_type,
            "side": side,
            "message": message,
            "payload": payload or {},
        }
    )


def draw_cards(match, side, count):
    side_state = get_side(match, side)
    drawn = []
    for _index in range(max(0, int(count or 0))):
        if not side_state["deck"]:
            _fatigue(match, side)
            break
        card = side_state["deck"].pop(0)
        side_state["hand"].append(card)
        drawn.append(card)
    if drawn:
        _chronicle(match, "draw", f"{side_state['name']} draws {len(drawn)} card(s).", side, {"count": len(drawn)})
    return drawn


def start_round(match):
    if match.get("winner"):
        match["phase"] = "finished"
        return match

    first_round = match.get("phase") == "created"
    match["round"] = 1 if first_round else int(match.get("round", 0)) + 1
    match["phase"] = "intent"

    for side in VALID_SIDES:
        side_state = get_side(match, side)
        side_state["intent"] = None
        side_state["last_actions"] = []
        if side_state["status"].get("vulnerable", 0) > 0:
            side_state["status"]["vulnerable"] -= 1
        draw_cards(match, side, 5 if first_round else 1)

    _chronicle(match, "round_start", f"Round {match['round']} begins on the Duel Altar.")
    return match


def choose_intent(match, side, intent):
    if match.get("winner"):
        raise AscensionActionError("match_finished", "This duel has already ended.")
    if intent not in VALID_INTENTS:
        raise AscensionActionError("invalid_intent", "Intent must be Strike, Guard, Focus, or Scheme.", {"intent": intent})

    side_state = get_side(match, side)
    side_state["intent"] = intent
    side_state["last_actions"].append({"type": "intent", "intent": intent})
    match["phase"] = "action"
    _chronicle(match, "intent_selected", f"{side_state['name']} commits to {intent}.", side, {"intent": intent})
    return match


def gain_ambition(match, side, amount, reason=None):
    amount = max(0, int(amount or 0))
    side_state = get_side(match, side)
    side_state["ambition"] += amount
    if amount:
        _chronicle(
            match,
            "ambition_gain",
            f"{side_state['name']} gains {amount} Ambition{f' from {reason}' if reason else ''}.",
            side,
            {"amount": amount, "reason": reason},
        )
    return side_state["ambition"]


def spend_ambition(match, side, amount, reason=None):
    amount = max(0, int(amount or 0))
    side_state = get_side(match, side)
    if side_state["ambition"] < amount:
        raise AscensionActionError(
            "not_enough_ambition",
            "The Ambition Core is not full enough for that action.",
            {"required": amount, "available": side_state["ambition"], "reason": reason},
        )
    side_state["ambition"] -= amount
    if amount:
        _chronicle(
            match,
            "ambition_spent",
            f"{side_state['name']} spends {amount} Ambition{f' on {reason}' if reason else ''}.",
            side,
            {"amount": amount, "reason": reason},
        )
    return side_state["ambition"]


def _find_hand_card(side_state, card_id):
    for index, card in enumerate(side_state["hand"]):
        if card.get("id") == card_id:
            return index, card
    raise AscensionActionError("card_not_in_hand", "That card is not in hand.", {"card_id": card_id})


def _default_mode(card):
    return {
        "champion": "summon",
        "technique": "cast",
        "relic": "equip",
        "scheme": "set",
        "ascension": "ascend",
    }.get(card.get("type"))


def _legal_modes_for_card(side_state, card):
    card_type = card.get("type")
    modes = ["burn"]
    if card_type == "champion":
        modes.insert(0, "summon")
        if side_state.get("active_champion") and len(side_state.get("bound_souls", [])) < MAX_BOUND_SOULS:
            modes.insert(1, "bind")
    elif card_type == "technique":
        modes.insert(0, "cast")
    elif card_type == "relic":
        modes.insert(0, "equip")
    elif card_type == "scheme":
        if len(side_state.get("schemes", [])) < MAX_SCHEMES:
            modes.insert(0, "set")
    elif card_type == "ascension":
        modes.insert(0, "ascend")
    return [mode for mode in modes if mode in card.get("modes", []) or mode == "burn"]


def play_card(match, side, card_id, mode=None):
    if match.get("winner"):
        raise AscensionActionError("match_finished", "This duel has already ended.")

    side_state = get_side(match, side)
    card_index, card = _find_hand_card(side_state, str(card_id or ""))
    mode = mode or _default_mode(card)
    legal_modes = _legal_modes_for_card(side_state, card)

    if card.get("type") == "champion" and mode == "bind":
        if not side_state.get("active_champion"):
            raise AscensionActionError("no_active_champion", "A Bound Soul needs an active Champion.")
        if len(side_state.get("bound_souls", [])) >= MAX_BOUND_SOULS:
            raise AscensionActionError("bound_soul_limit", "Only three Souls can be bound to a Champion.")

    if mode not in legal_modes:
        raise AscensionActionError(
            "illegal_mode",
            "That card cannot be used that way right now.",
            {"card_id": card.get("id"), "mode": mode, "legal_modes": legal_modes},
        )

    card = side_state["hand"].pop(card_index)

    if mode == "burn":
        side_state["echo"].append(card)
        gain_ambition(match, side, card.get("resolve", {}).get("burn_ambition", 1), reason=f"burning {card['name']}")
        side_state["last_actions"].append({"type": "burn", "card_id": card["id"]})
        _chronicle(match, "card_burned", f"{side_state['name']} burns {card['name']} into Echo.", side, {"card": card["id"]})
        return match

    if card["type"] == "champion" and mode == "summon":
        previous = side_state.get("active_champion")
        if previous:
            side_state["echo"].append(previous)
            _chronicle(match, "champion_replaced", f"{previous['name']} falls into Echo as a new Champion rises.", side)
        champion = _champion_instance(card)
        side_state["active_champion"] = champion
        side_state["last_actions"].append({"type": "summon", "card_id": card["id"]})
        _chronicle(match, "champion_summoned", f"{side_state['name']} summons {card['name']} as active Champion.", side, {"card": card["id"]})
        return match

    if card["type"] == "champion" and mode == "bind":
        if not side_state.get("active_champion"):
            side_state["hand"].insert(card_index, card)
            raise AscensionActionError("no_active_champion", "A Bound Soul needs an active Champion.")
        if len(side_state["bound_souls"]) >= MAX_BOUND_SOULS:
            side_state["hand"].insert(card_index, card)
            raise AscensionActionError("bound_soul_limit", "Only three Souls can be bound to a Champion.")
        soul = _copy(card)
        soul["bound_at_round"] = match.get("round", 0)
        side_state["bound_souls"].append(soul)
        side_state["last_actions"].append({"type": "bind", "card_id": card["id"]})
        _chronicle(match, "soul_bound", f"{card['name']} becomes a Bound Soul.", side, {"card": card["id"]})
        return match

    if card["type"] == "relic" and mode == "equip":
        previous = side_state.get("relic")
        if previous:
            side_state["echo"].append(previous)
            _chronicle(match, "relic_replaced", f"{previous['name']} is sealed into Echo.", side)
        side_state["relic"] = card
        side_state["last_actions"].append({"type": "equip", "card_id": card["id"]})
        _chronicle(match, "relic_equipped", f"{side_state['name']} equips {card['name']}.", side, {"card": card["id"]})
        return match

    if card["type"] == "scheme" and mode == "set":
        side_state["schemes"].append({"card": card, "revealed": False, "set_round": match.get("round", 0)})
        side_state["last_actions"].append({"type": "set", "card_id": card["id"]})
        _chronicle(match, "scheme_set", f"{side_state['name']} prepares a Scheme.", side, {"card": card["id"]})
        return match

    if card["type"] == "technique" and mode == "cast":
        _apply_card_effect(match, side, card)
        side_state["echo"].append(card)
        side_state["last_actions"].append({"type": "cast", "card_id": card["id"]})
        _chronicle(match, "technique_cast", f"{side_state['name']} casts {card['name']}.", side, {"card": card["id"]})
        return match

    if card["type"] == "ascension" and mode == "ascend":
        if not side_state.get("active_champion"):
            side_state["hand"].insert(card_index, card)
            raise AscensionActionError("no_active_champion", "Ascension requires an active Champion.")
        spend_ambition(match, side, card.get("ambition_cost", 0), reason=card["name"])
        effects = card.get("resolve", {})
        champion = side_state["active_champion"]
        champion["max_hp"] += int(effects.get("hp", 0) or 0)
        champion["current_hp"] = min(champion["max_hp"], champion["current_hp"] + int(effects.get("hp", 0) or 0))
        champion["resolve"]["pressure"] = champion.get("resolve", {}).get("pressure", 0) + int(effects.get("pressure", 0) or 0)
        champion["ascended"] = True
        side_state["ascended"] = True
        side_state["echo"].append(card)
        side_state["last_actions"].append({"type": "ascend", "card_id": card["id"]})
        if effects.get("damage"):
            _damage(match, get_opponent_side(side), int(effects["damage"]), source=card["name"])
        _chronicle(match, "champion_ascended", f"{champion['name']} ascends through {card['name']}.", side, {"card": card["id"]})
        _check_winner(match)
        return match

    side_state["hand"].insert(card_index, card)
    raise AscensionActionError("illegal_mode", "That card mode is not supported.", {"card_id": card.get("id"), "mode": mode})


def _champion_instance(card):
    champion = _copy(card)
    hp = int(champion.get("resolve", {}).get("hp", 8) or 8)
    champion["max_hp"] = hp
    champion["current_hp"] = hp
    champion["ascended"] = False
    return champion


def _apply_card_effect(match, side, card):
    effects = card.get("resolve", {})
    side_state = get_side(match, side)
    opponent_side = get_opponent_side(side)

    if effects.get("requires_active") and not side_state.get("active_champion"):
        raise AscensionActionError("no_active_champion", f"{card['name']} requires an active Champion.")
    if effects.get("damage"):
        _damage(match, opponent_side, int(effects["damage"]), source=card["name"])
    if effects.get("self_damage"):
        _damage(match, side, int(effects["self_damage"]), source=card["name"])
    if effects.get("heal"):
        _heal(match, side, int(effects["heal"]), source=card["name"])
    if effects.get("ambition"):
        gain_ambition(match, side, int(effects["ambition"]), reason=card["name"])
    if effects.get("draw"):
        draw_cards(match, side, int(effects["draw"]))
    if effects.get("mark"):
        side_state["domination_marks"] = min(3, side_state.get("domination_marks", 0) + int(effects["mark"]))
    if effects.get("pressure_next"):
        side_state.setdefault("status", {})["pressure_bonus"] = side_state.get("status", {}).get("pressure_bonus", 0) + int(effects["pressure_next"])
    _check_winner(match)


def resolve_clash(match):
    if match.get("winner"):
        match["phase"] = "finished"
        return match

    for side in VALID_SIDES:
        if not get_side(match, side).get("intent"):
            choose_intent(match, side, "Focus")
            _chronicle(match, "intent_defaulted", f"{get_side(match, side)['name']} defaults to Focus.", side)

    player_score = _score_side(match, "player")
    opponent_score = _score_side(match, "opponent")
    _trigger_schemes(match, "player", player_score)
    _trigger_schemes(match, "opponent", opponent_score)

    _apply_score_rewards(match, "player", player_score)
    _apply_score_rewards(match, "opponent", opponent_score)

    player_damage = max(0, player_score["pressure"] - opponent_score["guard"])
    opponent_damage = max(0, opponent_score["pressure"] - player_score["guard"])

    if not get_side(match, "opponent").get("active_champion") and player_damage > 0:
        player_damage += 2
    if not get_side(match, "player").get("active_champion") and opponent_damage > 0:
        opponent_damage += 2

    if player_damage:
        _damage(match, "opponent", player_damage, source="clash")
    if opponent_damage:
        _damage(match, "player", opponent_damage, source="clash")

    _chronicle(
        match,
        "clash_resolved",
        f"Mind Clash resolves: you press {player_damage}, rival presses {opponent_damage}.",
        payload={
            "player": player_score,
            "opponent": opponent_score,
            "player_damage": player_damage,
            "opponent_damage": opponent_damage,
        },
    )

    if player_damage > opponent_damage and player_damage >= 4:
        get_side(match, "player")["domination_marks"] = min(3, get_side(match, "player").get("domination_marks", 0) + 1)
    if opponent_damage > player_damage and opponent_damage >= 4:
        get_side(match, "opponent")["domination_marks"] = min(3, get_side(match, "opponent").get("domination_marks", 0) + 1)

    for side in VALID_SIDES:
        side_state = get_side(match, side)
        side_state["previous_intent"] = side_state.get("intent")
        side_state["intent"] = None
        side_state["status"].pop("pressure_bonus", None)

    _check_winner(match)
    if match.get("winner"):
        match["phase"] = "finished"
    else:
        match["phase"] = "round_end"
        start_round(match)
    return match


def _score_side(match, side):
    side_state = get_side(match, side)
    opponent_state = get_side(match, get_opponent_side(side))
    intent = side_state.get("intent") or "Focus"
    opponent_intent = opponent_state.get("intent") or "Focus"
    active = side_state.get("active_champion")
    score = {"pressure": 0, "guard": 0, "ambition": 0, "heal": 0, "draw": 0, "notes": []}

    if active:
        score["pressure"] += int(active.get("resolve", {}).get("pressure", 0) or 0)
        score["guard"] += int(active.get("resolve", {}).get("guard", 0) or 0)
    else:
        score["notes"].append("exposed")

    if intent == "Strike":
        score["pressure"] += 3
        if opponent_intent == "Focus":
            score["pressure"] += 2
            score["notes"].append("strike_pressures_focus")
    elif intent == "Guard":
        score["guard"] += 4
        if opponent_intent == "Strike":
            score["guard"] += 3
            score["ambition"] += 1
            score["notes"].append("guard_contains_strike")
    elif intent == "Focus":
        score["ambition"] += 2
        score["pressure"] += 1
        if opponent_intent == "Guard":
            score["pressure"] += 2
            score["ambition"] += 2
            score["notes"].append("focus_outscales_guard")
    elif intent == "Scheme":
        score["pressure"] += 1
        repeated = opponent_state.get("previous_intent") and opponent_state.get("previous_intent") == opponent_intent
        if repeated:
            score["pressure"] += 3
            score["ambition"] += 1
            score["notes"].append("scheme_punishes_repetition")
        else:
            score["ambition"] += 1

    if intent == opponent_intent:
        if intent == "Strike":
            score["pressure"] += 1
            score["notes"].append("mirror_strike")
        elif intent == "Guard":
            score["guard"] += 2
            score["ambition"] += 1
            score["notes"].append("mirror_guard")
        elif intent == "Focus":
            score["pressure"] = max(0, score["pressure"] - 1)
            score["ambition"] += 3
            score["notes"].append("mirror_focus")
        elif intent == "Scheme":
            score["pressure"] = max(0, score["pressure"] - 1)
            score["draw"] += 1
            score["notes"].append("mirror_scheme")

    for soul in side_state.get("bound_souls", []):
        _merge_bonus(score, soul.get("resolve", {}).get("soul_bonus", {}).get(intent, {}), note=f"soul:{soul.get('id')}")

    relic = side_state.get("relic")
    if relic:
        _merge_bonus(score, relic.get("resolve", {}).get("intent_bonus", {}).get(intent, {}), note=f"relic:{relic.get('id')}")

    if side_state.get("status", {}).get("pressure_bonus"):
        score["pressure"] += int(side_state["status"]["pressure_bonus"])
        score["notes"].append("stored_pressure")

    return score


def _merge_bonus(score, bonus, note=None):
    if not bonus:
        return
    for key in ("pressure", "guard", "ambition", "heal", "draw"):
        if bonus.get(key):
            score[key] += int(bonus[key])
    if note:
        score["notes"].append(note)


def _trigger_schemes(match, side, score):
    side_state = get_side(match, side)
    opponent_state = get_side(match, get_opponent_side(side))
    remaining = []

    for scheme in side_state.get("schemes", []):
        card = scheme.get("card") or {}
        effects = card.get("resolve", {})
        trigger = effects.get("trigger")
        triggered = (
            trigger == "repeat_intent" and opponent_state.get("previous_intent") == opponent_state.get("intent")
        ) or (
            trigger == "strike_into_guard" and side_state.get("intent") == "Guard" and opponent_state.get("intent") == "Strike"
        ) or (
            trigger == "opponent_focus" and opponent_state.get("intent") == "Focus"
        ) or (
            trigger == "mirror_intent" and side_state.get("intent") == opponent_state.get("intent")
        )

        if triggered:
            scheme["revealed"] = True
            _merge_bonus(score, effects, note=f"scheme:{card.get('id')}")
            side_state["echo"].append(card)
            _chronicle(match, "scheme_triggered", f"{card.get('name', 'A Scheme')} is revealed.", side, {"card": card.get("id")})
        else:
            remaining.append(scheme)

    side_state["schemes"] = remaining


def _apply_score_rewards(match, side, score):
    if score.get("ambition"):
        gain_ambition(match, side, int(score["ambition"]), reason="Mind Clash")
    if score.get("heal"):
        _heal(match, side, int(score["heal"]), source="Mind Clash")
    if score.get("draw"):
        draw_cards(match, side, int(score["draw"]))


def _damage(match, side, amount, source=None):
    amount = max(0, int(amount or 0))
    side_state = get_side(match, side)
    if side_state.get("status", {}).get("vulnerable"):
        amount += 2
    side_state["hp"] = max(0, int(side_state.get("hp", MAX_HP)) - amount)
    if amount:
        gain_ambition(match, side, 1 if amount >= 3 else 0, reason="receiving pressure")
        _chronicle(
            match,
            "pressure_damage",
            f"{side_state['name']} takes {amount} pressure{f' from {source}' if source else ''}.",
            side,
            {"amount": amount, "source": source},
        )
    _check_winner(match)


def _heal(match, side, amount, source=None):
    amount = max(0, int(amount or 0))
    side_state = get_side(match, side)
    before = side_state["hp"]
    side_state["hp"] = min(MAX_HP, side_state["hp"] + amount)
    healed = side_state["hp"] - before
    if healed:
        _chronicle(match, "recover", f"{side_state['name']} recovers {healed} HP.", side, {"amount": healed, "source": source})


def _fatigue(match, side):
    _damage(match, side, 1, source="empty deck")
    _chronicle(match, "echo_fatigue", f"{get_side(match, side)['name']} strains against an empty deck.", side)


def _check_winner(match):
    player_hp = get_side(match, "player")["hp"]
    opponent_hp = get_side(match, "opponent")["hp"]
    if player_hp <= 0 and opponent_hp <= 0:
        match["winner"] = "draw"
    elif player_hp <= 0:
        match["winner"] = "opponent"
    elif opponent_hp <= 0:
        match["winner"] = "player"

    if match.get("winner"):
        match["phase"] = "finished"
        _chronicle(match, "match_finished", f"Winner: {match['winner']}.", payload={"winner": match["winner"]})


def can_dominate(match, side):
    side_state = get_side(match, side)
    return bool(
        not match.get("winner")
        and side_state.get("active_champion")
        and side_state.get("ambition", 0) >= DOMINATE_COST
    )


def attempt_dominate(match, side):
    side_state = get_side(match, side)
    opponent_side = get_opponent_side(side)
    opponent = get_side(match, opponent_side)

    if not can_dominate(match, side):
        return {
            "ok": False,
            "code": "dominate_unavailable",
            "message": "Domination requires an active Champion and a full Ambition Core.",
        }

    spend_ambition(match, side, DOMINATE_COST, reason="Domination")
    relic_bonus = int((side_state.get("relic") or {}).get("resolve", {}).get("dominate_bonus", 0) or 0)
    success = bool(side_state.get("ascended") or side_state.get("domination_marks", 0) + relic_bonus >= 2 or opponent.get("hp", MAX_HP) <= 14)

    if success:
        damage = 12 + relic_bonus
        _damage(match, opponent_side, damage, source="Domination")
        side_state["domination_marks"] = 0
        _chronicle(match, "domination_success", f"{side_state['name']} dominates the Duel Altar.", side, {"damage": damage})
        _check_winner(match)
        return {"ok": True, "success": True, "damage": damage}

    side_state["status"]["vulnerable"] = max(2, int(side_state["status"].get("vulnerable", 0) or 0))
    side_state["domination_marks"] = 0
    _chronicle(match, "domination_failed", f"{side_state['name']} fails to Dominate and becomes vulnerable.", side)
    return {"ok": True, "success": False, "damage": 0}


def legal_actions(match, side):
    side_state = get_side(match, side)
    return {
        "phase": match.get("phase"),
        "intents": list(VALID_INTENTS),
        "can_dominate": can_dominate(match, side),
        "cards": [
            {
                "id": card.get("id"),
                "name": card.get("name"),
                "type": card.get("type"),
                "modes": _legal_modes_for_card(side_state, card),
            }
            for card in side_state.get("hand", [])
        ],
    }


def serialize_match(match):
    return _copy(match)

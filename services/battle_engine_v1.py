# =========================================================
# Ambitionz Battle Engine V1
# Motor de batalha isolado, determinístico e testável.
# Não depende de Flask, SocketIO ou frontend.
# =========================================================

from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


STARTING_HP = 28
STARTING_ENERGY = 2
MAX_ENERGY = 10
STARTING_HAND_SIZE = 5
DRAW_PER_ROUND = 1
MAX_ROUNDS = 60

VALID_INTENTS = {"Strike", "Guard", "Focus"}

CARD_CATALOG_V1 = {
    "quick_jab": {
        "id": "quick_jab",
        "name": "Quick Jab",
        "cost": 1,
        "damage": 4,
        "guard": 0,
        "ambition": 1,
        "type": "attack",
    },
    "heavy_hit": {
        "id": "heavy_hit",
        "name": "Heavy Hit",
        "cost": 2,
        "damage": 6,
        "guard": 0,
        "ambition": 1,
        "type": "attack",
    },
    "focus_spark": {
        "id": "focus_spark",
        "name": "Focus Spark",
        "cost": 1,
        "damage": 1,
        "guard": 0,
        "ambition": 3,
        "type": "focus",
    },
    "steady_guard": {
        "id": "steady_guard",
        "name": "Steady Guard",
        "cost": 1,
        "damage": 0,
        "guard": 4,
        "ambition": 1,
        "type": "guard",
    },
    "counter_stance": {
        "id": "counter_stance",
        "name": "Counter Stance",
        "cost": 2,
        "damage": 2,
        "guard": 3,
        "ambition": 1,
        "type": "guard",
    },
    "ambition_burst": {
        "id": "ambition_burst",
        "name": "Ambition Burst",
        "cost": 3,
        "damage": 8,
        "guard": 0,
        "ambition": 2,
        "type": "attack",
    },
}


BETA_DECK_V1 = [
    "quick_jab", "quick_jab", "quick_jab", "quick_jab", "quick_jab",
    "heavy_hit", "heavy_hit", "heavy_hit", "heavy_hit",
    "focus_spark", "focus_spark", "focus_spark", "focus_spark", "focus_spark",
    "steady_guard", "steady_guard", "steady_guard", "steady_guard", "steady_guard",
    "counter_stance", "counter_stance", "counter_stance", "counter_stance",
    "ambition_burst", "ambition_burst", "ambition_burst",
    "quick_jab", "focus_spark", "steady_guard", "heavy_hit",
]


def _card(card_id: str) -> Dict[str, Any]:
    if card_id not in CARD_CATALOG_V1:
        raise ValueError(f"Invalid card id: {card_id}")
    return deepcopy(CARD_CATALOG_V1[card_id])


def build_beta_deck(seed: Optional[int] = None) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    deck = [_card(card_id) for card_id in BETA_DECK_V1]
    rng.shuffle(deck)
    return deck


def create_player(name: str, seed: Optional[int] = None) -> Dict[str, Any]:
    return {
        "name": name,
        "hp": STARTING_HP,
        "max_hp": STARTING_HP,
        "energy": STARTING_ENERGY,
        "max_energy": STARTING_ENERGY,
        "ambition": 0,
        "deck": build_beta_deck(seed),
        "hand": [],
        "discard": [],
        "intent": None,
        "played_card": None,
        "guard": 0,
    }


def draw_cards(player: Dict[str, Any], amount: int, log: Optional[List[str]] = None) -> None:
    for _ in range(amount):
        if not player["deck"]:
            if player["discard"]:
                player["deck"] = player["discard"]
                player["discard"] = []
                random.shuffle(player["deck"])
                if log is not None:
                    log.append(f"{player['name']} reshuffled discard into deck.")
            else:
                return

        player["hand"].append(player["deck"].pop(0))


def create_match(
    player_name: str = "Player",
    opponent_name: str = "Ambitionz Bot",
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    player_seed = seed
    bot_seed = None if seed is None else seed + 999

    match = {
        "version": "battle_engine_v1",
        "phase": "created",
        "round": 0,
        "winner": None,
        "reason": None,
        "player": create_player(player_name, player_seed),
        "opponent": create_player(opponent_name, bot_seed),
        "log": [],
    }

    draw_cards(match["player"], STARTING_HAND_SIZE, match["log"])
    draw_cards(match["opponent"], STARTING_HAND_SIZE, match["log"])

    match["phase"] = "round_start"
    match["log"].append("Match created.")
    return match


def start_round(match: Dict[str, Any]) -> Dict[str, Any]:
    if match["winner"]:
        return match

    match["round"] += 1

    if match["round"] > MAX_ROUNDS:
        match["winner"] = "draw"
        match["reason"] = "max_rounds_reached"
        match["phase"] = "finished"
        match["log"].append("Match ended by max rounds.")
        return match

    for side in ("player", "opponent"):
        p = match[side]
        p["max_energy"] = min(MAX_ENERGY, STARTING_ENERGY + match["round"] - 1)
        p["energy"] = p["max_energy"]
        p["guard"] = 0
        p["intent"] = None
        p["played_card"] = None
        draw_cards(p, DRAW_PER_ROUND, match["log"])

    match["phase"] = "choose_action"
    match["log"].append(f"Round {match['round']} started.")
    return match


def playable_cards(player: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [c for c in player["hand"] if c["cost"] <= player["energy"]]


def choose_action(
    match: Dict[str, Any],
    side: str,
    intent: str,
    hand_index: Optional[int] = None,
) -> Dict[str, Any]:
    if match["winner"]:
        return match

    if match["phase"] not in {"choose_action", "round_start"}:
        raise ValueError(f"Cannot choose action during phase: {match['phase']}")

    if side not in {"player", "opponent"}:
        raise ValueError(f"Invalid side: {side}")

    if intent not in VALID_INTENTS:
        raise ValueError(f"Invalid intent: {intent}")

    player = match[side]
    player["intent"] = intent

    if hand_index is None:
        cards = playable_cards(player)
        selected = cards[0] if cards else None
        if selected is not None:
            original_index = player["hand"].index(selected)
            hand_index = original_index

    if hand_index is not None:
        if hand_index < 0 or hand_index >= len(player["hand"]):
            raise ValueError("Invalid hand index.")

        selected_card = player["hand"][hand_index]
        if selected_card["cost"] > player["energy"]:
            raise ValueError("Not enough energy to play this card.")

        player["energy"] -= selected_card["cost"]
        player["played_card"] = selected_card
        player["hand"].pop(hand_index)

    match["log"].append(f"{player['name']} chose {intent}.")
    return match


def bot_choose_action(match: Dict[str, Any]) -> Dict[str, Any]:
    bot = match["opponent"]
    human = match["player"]

    cards = playable_cards(bot)

    if not cards:
        return choose_action(match, "opponent", "Focus", None)

    if bot["hp"] <= 10:
        guard_cards = [c for c in cards if c["guard"] > 0]
        if guard_cards:
            chosen = max(guard_cards, key=lambda c: (c["guard"], c["damage"]))
            return choose_action(match, "opponent", "Guard", bot["hand"].index(chosen))

    attack_cards = [c for c in cards if c["damage"] > 0]

    if human["hp"] <= 12 and attack_cards:
        chosen = max(attack_cards, key=lambda c: (c["damage"], c["ambition"]))
        return choose_action(match, "opponent", "Strike", bot["hand"].index(chosen))

    strong_attack_cards = [c for c in attack_cards if c["damage"] >= 6]
    if strong_attack_cards:
        chosen = max(strong_attack_cards, key=lambda c: (c["damage"], c["ambition"]))
        return choose_action(match, "opponent", "Strike", bot["hand"].index(chosen))

    focus_cards = [c for c in cards if c["ambition"] >= 3]
    if bot["ambition"] < 5 and focus_cards:
        chosen = max(focus_cards, key=lambda c: c["ambition"])
        return choose_action(match, "opponent", "Focus", bot["hand"].index(chosen))

    chosen = max(cards, key=lambda c: (c["damage"], c["guard"], c["ambition"]))
    intent = "Strike" if chosen["damage"] >= chosen["guard"] else "Guard"
    return choose_action(match, "opponent", intent, bot["hand"].index(chosen))


def _intent_modifiers(intent: str) -> Dict[str, float]:
    if intent == "Strike":
        return {"damage": 1.35, "guard": 0.65, "ambition": 1.0}
    if intent == "Guard":
        return {"damage": 0.65, "guard": 1.35, "ambition": 1.0}
    if intent == "Focus":
        return {"damage": 0.75, "guard": 0.75, "ambition": 1.75}
    raise ValueError(f"Invalid intent: {intent}")


def _resolve_side(actor: Dict[str, Any]) -> Dict[str, int]:
    card = actor["played_card"]
    intent = actor["intent"] or "Focus"
    mods = _intent_modifiers(intent)

    if card is None:
        base_damage = 0
        base_guard = 0
        base_ambition = 2
    else:
        base_damage = card["damage"]
        base_guard = card["guard"]
        base_ambition = card["ambition"]

    damage = int(round(base_damage * mods["damage"]))
    guard = int(round(base_guard * mods["guard"]))
    ambition = int(round(base_ambition * mods["ambition"]))

    return {
        "damage": max(0, damage),
        "guard": max(0, guard),
        "ambition": max(0, ambition),
    }


def resolve_round(match: Dict[str, Any]) -> Dict[str, Any]:
    if match["winner"]:
        return match

    if match["phase"] not in {"choose_action", "round_start"}:
        raise ValueError(f"Cannot resolve during phase: {match['phase']}")

    if not match["player"]["intent"]:
        choose_action(match, "player", "Focus", None)

    if not match["opponent"]["intent"]:
        bot_choose_action(match)

    p = match["player"]
    o = match["opponent"]

    p_effect = _resolve_side(p)
    o_effect = _resolve_side(o)

    p["guard"] = p_effect["guard"]
    o["guard"] = o_effect["guard"]

    damage_to_o = max(0, p_effect["damage"] - o["guard"])
    damage_to_p = max(0, o_effect["damage"] - p["guard"])

    o["hp"] = max(0, o["hp"] - damage_to_o)
    p["hp"] = max(0, p["hp"] - damage_to_p)

    p["ambition"] += p_effect["ambition"]
    o["ambition"] += o_effect["ambition"]

    if p["played_card"]:
        p["discard"].append(p["played_card"])
    if o["played_card"]:
        o["discard"].append(o["played_card"])

    match["log"].append(
        f"Round {match['round']} resolved: "
        f"{p['name']} dealt {damage_to_o}, "
        f"{o['name']} dealt {damage_to_p}."
    )

    if p["hp"] <= 0 and o["hp"] <= 0:
        if damage_to_o > damage_to_p:
            match["winner"] = "player"
            match["reason"] = "double_ko_player_damage_tiebreak"
        elif damage_to_p > damage_to_o:
            match["winner"] = "opponent"
            match["reason"] = "double_ko_opponent_damage_tiebreak"
        elif p["ambition"] > o["ambition"]:
            match["winner"] = "player"
            match["reason"] = "double_ko_player_ambition_tiebreak"
        elif o["ambition"] > p["ambition"]:
            match["winner"] = "opponent"
            match["reason"] = "double_ko_opponent_ambition_tiebreak"
        else:
            match["winner"] = "draw"
            match["reason"] = "true_double_ko_draw"
        match["phase"] = "finished"
    elif o["hp"] <= 0:
        match["winner"] = "player"
        match["reason"] = "opponent_hp_zero"
        match["phase"] = "finished"
    elif p["hp"] <= 0:
        match["winner"] = "opponent"
        match["reason"] = "player_hp_zero"
        match["phase"] = "finished"
    else:
        match["phase"] = "round_start"

    return match


def play_full_bot_match(seed: Optional[int] = None) -> Dict[str, Any]:
    match = create_match(seed=seed)

    while not match["winner"]:
        start_round(match)

        if match["winner"]:
            break

        player = match["player"]
        cards = playable_cards(player)

        if cards:
            chosen = max(cards, key=lambda c: (c["damage"], c["ambition"], c["guard"]))
            intent = "Strike" if chosen["damage"] >= 3 else "Focus"
            choose_action(match, "player", intent, player["hand"].index(chosen))
        else:
            choose_action(match, "player", "Focus", None)

        bot_choose_action(match)
        resolve_round(match)

    return match


def serialize_state(match: Dict[str, Any], public_only: bool = True) -> Dict[str, Any]:
    state = deepcopy(match)

    if public_only:
        state["opponent"]["deck"] = []
        state["opponent"]["hand"] = [
            {"id": "hidden", "name": "Hidden Card"} for _ in state["opponent"]["hand"]
        ]

    return state


def validate_match_integrity(match: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = []

    for side in ("player", "opponent"):
        p = match[side]

        if p["hp"] < 0:
            errors.append(f"{side} has negative hp")

        if p["energy"] < 0:
            errors.append(f"{side} has negative energy")

        if p["max_energy"] > MAX_ENERGY:
            errors.append(f"{side} max energy above cap")

        for zone in ("deck", "hand", "discard"):
            for card in p[zone]:
                if "id" not in card or card["id"] not in CARD_CATALOG_V1:
                    errors.append(f"{side} has invalid card in {zone}")

        if p["intent"] is not None and p["intent"] not in VALID_INTENTS:
            errors.append(f"{side} has invalid intent")

    if match["round"] > MAX_ROUNDS:
        errors.append("round above max rounds")

    return len(errors) == 0, errors

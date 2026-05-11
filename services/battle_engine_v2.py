# =========================================================
# Ambitionz Battle Engine V2
# Card battler engine with active creature, support, spells,
# visible intent, shield, ambition and unleash.
# Isolated from Flask/SocketIO/frontend.
# =========================================================

from __future__ import annotations

import random
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from game.cards import CARD_CATALOG as OFFICIAL_CARD_CATALOG
from game.deck import STARTER_MONSTER_COUNT, STARTER_SPELL_COUNT, STARTER_TRAP_COUNT


ENGINE_VERSION = "battle_engine_v2"

STARTING_HP = 28
STARTING_ENERGY = 2
MAX_ENERGY = 10
STARTING_HAND_SIZE = 5
DRAW_PER_ROUND = 1
MAX_ROUNDS = 40
TRAINING_BOT_HP = 24

UNLEASH_COST = 10
UNLEASH_DAMAGE = 10
UNLEASH_SHIELD = 3

VALID_INTENTS = {"Strike", "Guard", "Focus"}
LANES = ("left", "center", "right")


CARD_CATALOG_V2 = {
    # =====================================================
    # Creatures
    # =====================================================
    "street_challenger": {
        "id": "street_challenger",
        "name": "Street Challenger",
        "kind": "creature",
        "cost": 2,
        "atk": 3,
        "hp": 5,
        "ambition": 1,
        "text": "Reliable fighter. Gains Ambition when attacking.",
    },
    "iron_wolf": {
        "id": "iron_wolf",
        "name": "Iron Wolf",
        "kind": "creature",
        "cost": 3,
        "atk": 5,
        "hp": 4,
        "ambition": 1,
        "text": "Aggressive creature with high attack.",
    },
    "silent_guardian": {
        "id": "silent_guardian",
        "name": "Silent Guardian",
        "kind": "creature",
        "cost": 2,
        "atk": 2,
        "hp": 7,
        "ambition": 1,
        "text": "Defensive creature with high HP.",
    },
    "spark_runner": {
        "id": "spark_runner",
        "name": "Spark Runner",
        "kind": "creature",
        "cost": 1,
        "atk": 2,
        "hp": 3,
        "ambition": 2,
        "text": "Cheap creature that builds Ambition quickly.",
    },
    "arena_brute": {
        "id": "arena_brute",
        "name": "Arena Brute",
        "kind": "creature",
        "cost": 4,
        "atk": 6,
        "hp": 6,
        "ambition": 1,
        "text": "Heavy midgame threat.",
    },

    # =====================================================
    # Spells
    # =====================================================
    "pressure_move": {
        "id": "pressure_move",
        "name": "Pressure Move",
        "kind": "spell",
        "cost": 1,
        "damage": 2,
        "ambition": 1,
        "text": "Deal 2 damage. Strike adds +1 damage.",
    },
    "clean_hit": {
        "id": "clean_hit",
        "name": "Clean Hit",
        "kind": "spell",
        "cost": 2,
        "damage": 4,
        "ambition": 1,
        "text": "Deal 4 damage to the enemy hero.",
    },
    "focus_surge": {
        "id": "focus_surge",
        "name": "Focus Surge",
        "kind": "spell",
        "cost": 1,
        "damage": 0,
        "ambition": 4,
        "draw": 1,
        "text": "Gain Ambition and draw 1 card.",
    },

    # =====================================================
    # Guards
    # =====================================================
    "hold_position": {
        "id": "hold_position",
        "name": "Hold Position",
        "kind": "guard",
        "cost": 1,
        "shield": 5,
        "ambition": 1,
        "text": "Gain 5 shield this round.",
    },
    "counter_wall": {
        "id": "counter_wall",
        "name": "Counter Wall",
        "kind": "guard",
        "cost": 2,
        "shield": 6,
        "damage": 2,
        "ambition": 1,
        "text": "Gain shield and deal 2 damage.",
    },

    # =====================================================
    # Support
    # =====================================================
    "battle_banner": {
        "id": "battle_banner",
        "name": "Battle Banner",
        "kind": "support",
        "cost": 2,
        "atk_bonus": 1,
        "ambition": 1,
        "text": "Support: your active creature has +1 ATK.",
    },
    "focus_relic": {
        "id": "focus_relic",
        "name": "Focus Relic",
        "kind": "support",
        "cost": 2,
        "ambition_bonus": 1,
        "ambition": 2,
        "text": "Support: gain +1 extra Ambition each round.",
    },
}


BETA_DECK_V2 = [
    "spark_runner", "spark_runner", "spark_runner",
    "street_challenger", "street_challenger", "street_challenger", "street_challenger",
    "silent_guardian", "silent_guardian", "silent_guardian",
    "iron_wolf", "iron_wolf", "iron_wolf",
    "arena_brute", "arena_brute",
    "pressure_move", "pressure_move", "pressure_move", "pressure_move",
    "clean_hit", "clean_hit", "clean_hit",
    "focus_surge", "focus_surge", "focus_surge",
    "hold_position", "hold_position", "hold_position",
    "counter_wall", "counter_wall",
    "battle_banner", "battle_banner",
    "focus_relic", "focus_relic",
]


def _copy_card(card_id: str) -> Dict[str, Any]:
    if card_id not in CARD_CATALOG_V2:
        raise ValueError(f"Invalid card id: {card_id}")
    return deepcopy(CARD_CATALOG_V2[card_id])


def _empty_board() -> Dict[str, Optional[Dict[str, Any]]]:
    return {lane: None for lane in LANES}


def ensure_board(player: Dict[str, Any]) -> Dict[str, Optional[Dict[str, Any]]]:
    board = player.get("board")

    if not isinstance(board, dict):
        field = player.setdefault("field", {})
        lanes = field.get("lanes")
        board = lanes if isinstance(lanes, dict) else _empty_board()
        player["board"] = board

    for lane in LANES:
        board.setdefault(lane, None)

    field = player.setdefault("field", {})
    field["lanes"] = board
    return board


def normalize_lane(lane: Optional[str]) -> Optional[str]:
    if lane is None:
        return None
    value = str(lane).strip().lower()
    aliases = {"l": "left", "c": "center", "centre": "center", "r": "right"}
    return aliases.get(value, value)


def validate_lane(lane: Optional[str]) -> str:
    normalized = normalize_lane(lane)
    if normalized not in LANES:
        raise ValueError("Invalid lane.")
    return str(normalized)


def empty_lanes(player: Dict[str, Any]) -> List[str]:
    board = ensure_board(player)
    return [lane for lane in LANES if not board.get(lane)]


def first_empty_lane(player: Dict[str, Any]) -> Optional[str]:
    lanes = empty_lanes(player)
    return lanes[0] if lanes else None


def _official_card_to_be2(card: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt official Ambitionz catalog cards into Battle Engine V2 combat cards."""
    card_type = str(card.get("type") or "").strip()
    effect = str(card.get("effect") or "")
    cost = int(card.get("cost") or 1)
    power = int(card.get("power") or card.get("value") or 1000)
    value = int(card.get("value") or 0)

    adapted = {
        "id": str(card.get("id")),
        "name": str(card.get("name") or card.get("id")),
        "official_type": card_type,
        "element": str(card.get("element") or "Neutral"),
        "rarity": str(card.get("rarity") or "Common"),
        "cost": max(1, min(10, cost)),
        "ambition": 1,
        "text": str(card.get("description") or card.get("tactical_hint") or card.get("type_identity") or ""),
        "image": str(card.get("image") or "cards/placeholders/card_placeholder.svg"),
        "sigil": str(card.get("sigil") or ""),
        "role": str(card.get("role") or ""),
        "archetype": str(card.get("archetype") or ""),
        "effect_key": effect,
        "source": "official_catalog",
    }

    if card_type == "Monster":
        atk = max(2, min(9, round(power / 260)))
        hp = max(3, min(10, round(power / 230)))

        element = adapted["element"]

        if element == "Fire":
            atk += 1
        elif element == "Earth":
            hp += 1
        elif element == "Water":
            adapted["ambition"] = 2
        elif element == "Plant":
            hp += 1

        adapted.update({
            "kind": "creature",
            "atk": max(1, min(10, atk)),
            "hp": max(1, min(12, hp)),
        })
        return adapted

    if card_type == "Spell":
        damage = max(1, min(6, value or cost + 1))
        shield = 0

        if effect in {"Shield", "Heal"}:
            damage = 0
            shield = max(3, min(8, value or cost + 3))
        elif effect in {"Boost", "Draw"}:
            damage = max(0, min(3, value or cost))
            adapted["ambition"] = 2
        elif effect in {"Burn", "Drain", "Weaken"}:
            damage = max(2, min(6, value or cost + 2))

        adapted.update({
            "kind": "spell",
            "damage": damage,
            "shield": shield,
        })
        return adapted

    if card_type == "Trap":
        shield = max(4, min(9, value or cost + 4))
        damage = 0

        if effect in {"Counter", "Burn"}:
            damage = max(1, min(4, value or cost))
        elif effect == "Weaken":
            damage = 1
        elif effect == "Heal":
            adapted["ambition"] = 2

        adapted.update({
            "kind": "guard",
            "shield": shield,
            "damage": damage,
        })
        return adapted

    adapted.update({
        "kind": "spell",
        "damage": max(1, min(4, cost)),
    })
    return adapted


def _official_pool(card_type: str) -> List[Dict[str, Any]]:
    return [
        card for card in OFFICIAL_CARD_CATALOG
        if str(card.get("type") or "") == card_type
    ]


def _choose_official_cards(rng: random.Random, pool: List[Dict[str, Any]], amount: int) -> List[Dict[str, Any]]:
    if not pool or amount <= 0:
        return []

    if len(pool) >= amount:
        return rng.sample(pool, amount)

    selected = list(pool)

    while len(selected) < amount:
        selected.append(rng.choice(pool))

    return selected


def build_beta_deck(seed: Optional[int] = None) -> List[Dict[str, Any]]:
    """Build a BE2 combat deck from the official 250-card Ambitionz catalog.

    Production rule:
    - 30 cards
    - 21 monsters
    - 6 spells
    - 3 traps
    """
    rng = random.Random(4248 if seed is None else seed)

    monsters = _choose_curated_official_cards("Monster", STARTER_MONSTER_COUNT)
    spells = _choose_curated_official_cards("Spell", STARTER_SPELL_COUNT)
    traps = _choose_curated_official_cards("Trap", STARTER_TRAP_COUNT)

    if len(monsters) < STARTER_MONSTER_COUNT:
        monsters = _choose_official_cards(rng, _official_pool("Monster"), STARTER_MONSTER_COUNT)
    if len(spells) < STARTER_SPELL_COUNT:
        spells = _choose_official_cards(rng, _official_pool("Spell"), STARTER_SPELL_COUNT)
    if len(traps) < STARTER_TRAP_COUNT:
        traps = _choose_official_cards(rng, _official_pool("Trap"), STARTER_TRAP_COUNT)

    deck = [_official_card_to_be2(card) for card in monsters + spells + traps]
    rng.shuffle(deck)

    return deck


def _choose_curated_official_cards(card_type: str, amount: int) -> List[Dict[str, Any]]:
    """Return a stable starter slice with low early-turn friction.

    The full catalog remains available, but a random starter deck can open with
    too many expensive or unclear cards. This keeps training readable while the
    engine matures.
    """
    pool = _official_pool(card_type)
    if not pool or amount <= 0:
        return []

    if card_type == "Monster":
        by_element: Dict[str, List[Dict[str, Any]]] = {}
        for card in pool:
            if int(card.get("cost") or 99) > 3:
                continue
            by_element.setdefault(str(card.get("element") or "Neutral"), []).append(card)

        for cards in by_element.values():
            cards.sort(key=lambda c: (int(c.get("cost") or 0), int(c.get("power") or 0), str(c.get("id") or "")))

        selected: List[Dict[str, Any]] = []
        element_order = ["Fire", "Water", "Earth", "Plant"]
        index = 0

        while len(selected) < amount and any(index < len(by_element.get(element, [])) for element in element_order):
            for element in element_order:
                cards = by_element.get(element, [])
                if index < len(cards):
                    selected.append(cards[index])
                    if len(selected) >= amount:
                        break
            index += 1

        return selected

    preferred_effects = {
        "Spell": ["Heal", "Boost", "Burn", "Weaken", "Draw", "Shield"],
        "Trap": ["Burn", "Heal", "Counter"],
    }.get(card_type, [])

    selected = []
    for effect in preferred_effects:
        candidates = [
            card for card in pool
            if str(card.get("effect") or "") == effect and int(card.get("cost") or 99) <= 3
        ]
        candidates.sort(key=lambda c: (int(c.get("cost") or 0), str(c.get("rarity") or ""), str(c.get("id") or "")))
        if candidates:
            selected.append(candidates[0])
        if len(selected) >= amount:
            return selected

    remaining = [card for card in pool if card not in selected]
    remaining.sort(key=lambda c: (int(c.get("cost") or 0), str(c.get("id") or "")))
    return (selected + remaining)[:amount]


def create_player(
    name: str,
    seed: Optional[int] = None,
    sid: Optional[str] = None,
    user_id: Any = None,
    is_bot: bool = False,
) -> Dict[str, Any]:
    board = _empty_board()
    return {
        "name": name,
        "sid": sid,
        "user_id": user_id,
        "is_bot": is_bot,
        "hp": STARTING_HP,
        "max_hp": STARTING_HP,
        "energy": STARTING_ENERGY,
        "max_energy": STARTING_ENERGY,
        "ambition": 0,
        "shield": 0,
        "deck": build_beta_deck(seed),
        "hand": [],
        "discard": [],
        "board": board,
        "field": {
            "active": None,
            "support": None,
            "lanes": board,
        },
        "intent": None,
        "ready": False,
        "played_card": None,
        "played_this_round": False,
        "unleash": False,
        "last_damage_dealt": 0,
    }


def draw_cards(player: Dict[str, Any], amount: int, log: Optional[List[str]] = None) -> None:
    for _ in range(amount):
        if not player["deck"]:
            if not player["discard"]:
                return
            player["deck"] = player["discard"]
            player["discard"] = []
            random.shuffle(player["deck"])
            if log is not None:
                log.append(f"{player['name']} reshuffled the discard pile.")

        player["hand"].append(player["deck"].pop(0))


def create_match(
    player_name: str = "Player",
    opponent_name: str = "Ambitionz Bot",
    seed: Optional[int] = None,
    player_sid: Optional[str] = None,
    user_id: Any = None,
    opponent_sid: Optional[str] = None,
    opponent_user_id: Any = None,
    opponent_is_bot: bool = True,
) -> Dict[str, Any]:
    match = {
        "version": ENGINE_VERSION,
        "phase": "created",
        "round": 0,
        "winner": None,
        "reason": None,
        "player": create_player(player_name, seed=seed, sid=player_sid, user_id=user_id),
        "opponent": create_player(
            opponent_name,
            seed=None if seed is None else seed + 555,
            sid=opponent_sid,
            user_id=opponent_user_id,
            is_bot=opponent_is_bot,
        ),
        "enemy_preview": None,
        "log": [],
        "events": [],
        "round_events": [],
        "combat_log": [],
        "next_instance_id": 1,
    }

    draw_cards(match["player"], STARTING_HAND_SIZE, match["log"])
    draw_cards(match["opponent"], STARTING_HAND_SIZE, match["log"])

    match["log"].append("Battle V2 created.")
    return match


def playable_cards(player: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [card for card in player["hand"] if int(card.get("cost") or 0) <= player["energy"]]


def active_creature(player: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    board = ensure_board(player)
    for lane in LANES:
        creature = board.get(lane)
        if creature:
            return creature
    return None


def board_creatures(player: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    board = ensure_board(player)
    return [(lane, board[lane]) for lane in LANES if board.get(lane)]


def support_card(player: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return (player.get("field") or {}).get("support")


def support_atk_bonus(player: Dict[str, Any]) -> int:
    support = support_card(player)
    return int((support or {}).get("atk_bonus") or 0)


def support_ambition_bonus(player: Dict[str, Any]) -> int:
    support = support_card(player)
    return int((support or {}).get("ambition_bonus") or 0)


def start_round(match: Dict[str, Any]) -> Dict[str, Any]:
    if match.get("winner"):
        return match

    match["round"] += 1

    if match["round"] > MAX_ROUNDS:
        finish_by_tiebreak(match, reason="max_rounds_tiebreak")
        return match

    match["round_events"] = []
    for side in ("player", "opponent"):
        player = match[side]
        player["max_energy"] = min(MAX_ENERGY, STARTING_ENERGY + match["round"] - 1)
        player["energy"] = player["max_energy"]
        player["shield"] = 0
        player["intent"] = None
        player["ready"] = False
        player["played_card"] = None
        player["played_this_round"] = False
        player["unleash"] = False
        player["last_damage_dealt"] = 0
        ensure_board(player)

        bonus = support_ambition_bonus(player)
        if bonus:
            player["ambition"] += bonus
            match["log"].append(f"{player['name']} gained {bonus} Ambition from support.")
            add_event(
                match,
                "ambition",
                actor=side,
                text=f"{player['name']} gained {bonus} Ambition from support.",
                amount=bonus,
            )

        if match["round"] > 1 or len(player.get("hand") or []) < STARTING_HAND_SIZE:
            draw_cards(player, DRAW_PER_ROUND, match["log"])

    match["phase"] = "choose_action"
    match["enemy_preview"] = preview_bot_intent(match)
    match["log"].append(f"Round {match['round']} started.")
    add_event(match, "round_start", text=f"Round {match['round']} started.")
    add_combat_event(match, "round_start", phase=match["phase"])
    return match


def choose_intent(match: Dict[str, Any], side: str, intent: str) -> Dict[str, Any]:
    if match.get("winner") or str(match.get("phase") or "").lower() == "finished":
        raise ValueError("Match is finished.")
    if match.get("phase") != "choose_action":
        raise ValueError("Intent can only be chosen during the action phase.")
    if side not in {"player", "opponent"}:
        raise ValueError("Invalid side.")
    if intent not in VALID_INTENTS:
        raise ValueError(f"Invalid intent: {intent}")

    player = match[side]
    if player.get("ready"):
        raise ValueError("Round is already ready.")
    if player.get("played_card"):
        raise ValueError("Action is locked after playing a card.")

    player["intent"] = intent
    match["log"].append(f"{player['name']} chose {intent}.")
    add_event(match, "intent", actor=side, text=f"{player['name']} chose {intent}.", intent=intent)
    return match


def _find_card_in_hand(player: Dict[str, Any], card_id: Optional[str] = None, card_index: Optional[int] = None) -> Tuple[int, Dict[str, Any]]:
    hand = player.get("hand") or []

    index = None
    has_explicit_card_id = card_id is not None and str(card_id) != ""

    if card_index is not None:
        try:
            index = int(card_index)
        except Exception:
            index = None

    if index is None and card_id:
        for idx, card in enumerate(hand):
            if str(card.get("id")) == str(card_id):
                index = idx
                break

    if index is None and has_explicit_card_id:
        raise ValueError("Card not found in hand.")

    if index is None:
        raise ValueError("Card selection required.")

    if index < 0 or index >= len(hand):
        raise ValueError("Invalid hand index.")

    card = hand[index]

    if has_explicit_card_id and str(card.get("id")) != str(card_id):
        raise ValueError("Card index does not match card id.")

    if int(card.get("cost") or 0) > player["energy"]:
        raise ValueError("Not enough energy.")

    return index, card


def _remove_card_from_hand(player: Dict[str, Any], index: int) -> Dict[str, Any]:
    hand = player.get("hand") or []
    card = hand[index]
    player["energy"] -= int(card.get("cost") or 0)
    return hand.pop(index)


def _next_instance_id(match: Dict[str, Any], side: str, lane: str, card: Dict[str, Any]) -> str:
    current = int(match.get("next_instance_id") or 1)
    match["next_instance_id"] = current + 1
    card_id = str(card.get("id") or "card")
    return f"{side}-{lane}-{card_id}-{current}"


def _field_creature_instance(match: Dict[str, Any], side: str, lane: str, card: Dict[str, Any]) -> Dict[str, Any]:
    hp = int(card.get("hp") or card.get("max_hp") or 1)
    attack = int(card.get("atk") or card.get("attack") or card.get("power") or 0)
    keywords = card.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [keywords]

    instance_id = _next_instance_id(match, side, lane, card)
    return {
        **deepcopy(card),
        "id": instance_id,
        "instance_id": instance_id,
        "card_id": str(card.get("id") or card.get("card_id") or card.get("name") or "card"),
        "name": str(card.get("name") or card.get("id") or "Creature"),
        "kind": "creature",
        "atk": attack,
        "attack": attack,
        "power": attack,
        "hp": hp,
        "current_hp": hp,
        "max_hp": hp,
        "owner": side,
        "lane": lane,
        "keywords": list(keywords),
        "exhausted": False,
        "played_round": int(match.get("round") or 0),
    }


def _validate_target(match: Dict[str, Any], side: str, card: Dict[str, Any], target: Optional[str]) -> Optional[str]:
    if target is None or target == "":
        return None

    target = str(target)
    valid_targets = {"enemy_hero", "self"}
    if target.startswith("lane:"):
        validate_lane(target.split(":", 1)[1])
        valid_targets.add(target)

    if card.get("kind") in {"creature", "support"}:
        raise ValueError("Target is not valid for this card.")
    if target not in valid_targets:
        raise ValueError("Invalid target.")
    return target


def play_card(
    match: Dict[str, Any],
    side: str,
    card_id: Optional[str] = None,
    card_index: Optional[int] = None,
    lane: Optional[str] = None,
    target: Optional[str] = None,
) -> Dict[str, Any]:
    if match.get("winner") or str(match.get("phase") or "").lower() == "finished":
        raise ValueError("Match is finished.")
    if match.get("phase") != "choose_action":
        raise ValueError("Cards can only be played during the action phase.")
    if side not in {"player", "opponent"}:
        raise ValueError("Invalid side.")

    player = match[side]
    ensure_board(player)

    if player.get("ready"):
        raise ValueError("Round is already ready.")
    if not player.get("intent"):
        raise ValueError("Choose Strike, Guard or Focus before playing a card.")
    if player.get("played_this_round") or player.get("played_card"):
        raise ValueError("Only one card can be played each round.")

    index, card = _find_card_in_hand(player, card_id=card_id, card_index=card_index)
    kind = card.get("kind")
    lane = validate_lane(lane) if kind == "creature" or lane not in {None, ""} else None
    _validate_target(match, side, card, target)

    if kind == "creature":
        board = ensure_board(player)
        if board.get(lane):
            raise ValueError("Lane is occupied.")

        card = _remove_card_from_hand(player, index)
        instance = _field_creature_instance(match, side, str(lane), card)
        board[str(lane)] = instance
        player["played_card"] = card
        player["played_this_round"] = True
        player["ambition"] += int(card.get("ambition") or 0)
        match["log"].append(f"{player['name']} summoned {card['name']} to {lane}.")
        add_event(match, "card_played", actor=side, text=f"{player['name']} summoned {card['name']} to {lane}.", card_id=card.get("id"), card_name=card.get("name"), instance_id=instance.get("instance_id"), kind=kind, lane=lane)

    elif kind == "support":
        old = player["field"].get("support")
        if old:
            player["discard"].append(old)
            match["log"].append(f"{player['name']} replaced support {old['name']}.")
            add_event(match, "card_replaced", actor=side, text=f"{player['name']} replaced support {old['name']}.", card_id=old.get("id"))

        card = _remove_card_from_hand(player, index)
        player["field"]["support"] = deepcopy(card)
        player["played_card"] = card
        player["played_this_round"] = True
        player["ambition"] += int(card.get("ambition") or 0)
        match["log"].append(f"{player['name']} played support {card['name']}.")
        add_event(match, "card_played", actor=side, text=f"{player['name']} played support {card['name']}.", card_id=card.get("id"), card_name=card.get("name"), kind=kind)

    else:
        card = _remove_card_from_hand(player, index)
        player["played_card"] = card
        player["played_this_round"] = True
        player["discard"].append(card)
        apply_instant_card(match, side, card)
        match["log"].append(f"{player['name']} cast {card['name']}.")
        add_event(match, "card_played", actor=side, text=f"{player['name']} cast {card['name']}.", card_id=card.get("id"), card_name=card.get("name"), kind=kind)

    return match


def apply_instant_card(match: Dict[str, Any], side: str, card: Dict[str, Any]) -> None:
    actor = match[side]
    enemy_side = "opponent" if side == "player" else "player"
    enemy = match[enemy_side]

    intent = actor.get("intent") or "Focus"
    damage = int(card.get("damage") or 0)
    shield = int(card.get("shield") or 0)
    ambition = int(card.get("ambition") or 0)
    draw = int(card.get("draw") or 0)

    if card.get("id") == "pressure_move" and intent == "Strike":
        damage += 1

    if intent == "Guard":
        shield += 2

    if intent == "Focus":
        ambition += 1

    if shield:
        actor["shield"] += shield
        add_event(match, "shield", actor=side, text=f"{actor['name']} gained {shield} shield.", amount=shield, card_id=card.get("id"))

    if damage:
        deal_hero_damage(enemy, damage)
        actor["last_damage_dealt"] += damage
        add_event(match, "direct_damage", actor=side, target=enemy_side, text=f"{actor['name']} dealt {damage} direct damage.", amount=damage, card_id=card.get("id"))

    actor["ambition"] += ambition
    if ambition:
        add_event(match, "ambition", actor=side, text=f"{actor['name']} gained {ambition} Ambition.", amount=ambition, card_id=card.get("id"))

    if draw:
        draw_cards(actor, draw, match["log"])
        add_event(match, "draw", actor=side, text=f"{actor['name']} drew {draw} card.", amount=draw, card_id=card.get("id"))


def request_unleash(match: Dict[str, Any], side: str) -> Dict[str, Any]:
    player = match[side]

    if player["ambition"] < UNLEASH_COST:
        raise ValueError("Not enough Ambition to Unleash.")

    player["ambition"] -= UNLEASH_COST
    player["unleash"] = True
    match["log"].append(f"{player['name']} prepared Ambition Unleash.")
    add_event(match, "unleash_armed", actor=side, text=f"{player['name']} prepared Ambition Unleash.", amount=UNLEASH_COST)
    return match


def deal_hero_damage(target: Dict[str, Any], amount: int) -> int:
    amount = max(0, int(amount or 0))
    blocked = min(target.get("shield") or 0, amount)
    target["shield"] = max(0, (target.get("shield") or 0) - blocked)
    damage = amount - blocked
    target["hp"] = max(0, target["hp"] - damage)
    return damage


def damage_active_creature(owner: Dict[str, Any], amount: int) -> Tuple[int, int]:
    creature = active_creature(owner)

    if not creature:
        return 0, max(0, int(amount or 0))

    damage = max(0, int(amount or 0))
    current_hp = int(creature.get("current_hp") or creature.get("hp") or 1)
    overflow = max(0, damage - current_hp)

    creature["current_hp"] = current_hp - damage

    if creature["current_hp"] <= 0:
        owner["discard"].append(creature)
        owner["field"]["active"] = None

    return min(damage, current_hp), overflow


def creature_attack_value(player: Dict[str, Any], creature: Optional[Dict[str, Any]]) -> int:
    if not creature:
        return 0

    value = int(creature.get("atk") or 0) + support_atk_bonus(player)

    if player.get("intent") == "Strike":
        value += 2
    elif player.get("intent") == "Guard":
        value -= 1

    return max(0, value)


def attack_value(player: Dict[str, Any]) -> int:
    return sum(creature_attack_value(player, creature) for _lane, creature in board_creatures(player))


def guard_value(player: Dict[str, Any]) -> int:
    value = 0

    if player.get("intent") == "Guard":
        value += 4

    creature = active_creature(player)
    if creature and player.get("intent") == "Guard":
        value += 1

    return value


def ambition_gain_from_intent(player: Dict[str, Any]) -> int:
    intent = player.get("intent") or "Focus"

    if intent == "Focus":
        return 3
    if intent == "Guard":
        return 1
    return 1


def _card_name(card: Optional[Dict[str, Any]]) -> str:
    return str((card or {}).get("name") or "No card")


def _active_name(player: Dict[str, Any]) -> str:
    creature = active_creature(player)
    return str((creature or {}).get("name") or "no active creature")


def _board_snapshot(player: Dict[str, Any]) -> Dict[str, Optional[str]]:
    board = ensure_board(player)
    return {
        lane: str((board.get(lane) or {}).get("name") or "") or None
        for lane in LANES
    }


def _cleanup_dead_creatures(match: Dict[str, Any], side: str) -> None:
    player = match[side]
    board = ensure_board(player)

    for lane in LANES:
        creature = board.get(lane)
        if not creature:
            continue

        current_hp = creature.get("current_hp")
        if current_hp is None:
            current_hp = creature.get("hp") or 0
        if int(current_hp or 0) > 0:
            continue

        board[lane] = None
        player["discard"].append(creature)
        text = f"{creature.get('name', 'Creature')} died in {lane}."
        match["log"].append(text)
        add_event(
            match,
            "creature_destroyed",
            actor=side,
            text=text,
            lane=lane,
            card_id=creature.get("card_id") or creature.get("id"),
            instance_id=creature.get("instance_id"),
        )
        add_combat_event(
            match,
            "creature_death",
            side=side,
            lane=lane,
            card_id=creature.get("card_id") or creature.get("id"),
            instance_id=creature.get("instance_id"),
            name=creature.get("name"),
            current_hp=int(current_hp or 0),
        )


def _hp_delta(before: int, after: int) -> int:
    return max(0, int(before or 0) - int(after or 0))


def add_event(match: Dict[str, Any], event_type: str, **data: Any) -> Dict[str, Any]:
    event = {
        "round": int(match.get("round") or 0),
        "type": event_type,
        **{key: value for key, value in data.items() if value is not None},
    }

    events = match.setdefault("events", [])
    events.append(event)
    if len(events) > 100:
        del events[:-100]

    match.setdefault("round_events", []).append(event)
    return event


def add_combat_event(match: Dict[str, Any], event_type: str, **data: Any) -> Dict[str, Any]:
    event = {
        "round": int(match.get("round") or 0),
        "type": event_type,
        **{key: value for key, value in data.items() if value is not None},
    }

    combat_log = match.setdefault("combat_log", [])
    combat_log.append(event)
    if len(combat_log) > 200:
        del combat_log[:-200]

    return event


def build_round_summary(
    match: Dict[str, Any],
    p_hp_before: int,
    o_hp_before: int,
    p_board_before: Dict[str, Optional[str]],
    o_board_before: Dict[str, Optional[str]],
    p_atk: int,
    o_atk: int,
    lane_results: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    player = match["player"]
    opponent = match["opponent"]
    lane_results = lane_results or []

    p_hp_after = int(player.get("hp") or 0)
    o_hp_after = int(opponent.get("hp") or 0)

    player_card = _card_name(player.get("played_card"))
    enemy_card = _card_name(opponent.get("played_card"))

    player_lost = _hp_delta(p_hp_before, p_hp_after)
    enemy_lost = _hp_delta(o_hp_before, o_hp_after)

    lines = []

    lines.append(f"You chose {player.get('intent') or 'Focus'} and played {player_card}.")
    lines.append(f"Enemy chose {opponent.get('intent') or 'Focus'} and played {enemy_card}.")

    if player.get("unleash"):
        lines.append("You prepared Ambition Unleash and released a special attack.")
    if opponent.get("unleash"):
        lines.append("Enemy prepared Ambition Unleash and released a special attack.")

    for result in lane_results:
        lane = result.get("lane")
        if result.get("player_creature") and result.get("enemy_creature"):
            lines.append(
                f"{lane}: {result['player_creature']} and {result['enemy_creature']} traded damage."
            )
        elif result.get("player_creature"):
            lines.append(f"{lane}: your {result['player_creature']} hit enemy HP for {result.get('player_damage', 0)}.")
        elif result.get("enemy_creature"):
            lines.append(f"{lane}: enemy {result['enemy_creature']} hit your HP for {result.get('enemy_damage', 0)}.")

    if enemy_lost:
        lines.append(f"Enemy lost {enemy_lost} HP: {o_hp_before} → {o_hp_after}.")
    else:
        lines.append(f"Enemy HP stayed at {o_hp_after}.")

    if player_lost:
        lines.append(f"You lost {player_lost} HP: {p_hp_before} → {p_hp_after}.")
    else:
        lines.append(f"Your HP stayed at {p_hp_after}.")

    if match.get("winner"):
        if match["winner"] == "player":
            lines.append("You won the duel.")
        elif match["winner"] == "opponent":
            lines.append("You lost the duel.")
        else:
            lines.append("The duel ended in a draw.")

    short_result = f"You dealt {enemy_lost} HP damage. Enemy dealt {player_lost} HP damage."

    return {
        "round": int(match.get("round") or 0),
        "player_intent": player.get("intent") or "Focus",
        "enemy_intent": opponent.get("intent") or "Focus",
        "player_card": player_card,
        "enemy_card": enemy_card,
        "player_attack": int(p_atk or 0),
        "enemy_attack": int(o_atk or 0),
        "player_hp_before": p_hp_before,
        "player_hp_after": p_hp_after,
        "enemy_hp_before": o_hp_before,
        "enemy_hp_after": o_hp_after,
        "player_active_before": next((name for name in p_board_before.values() if name), "no active creature"),
        "player_active_after": _active_name(player),
        "enemy_active_before": next((name for name in o_board_before.values() if name), "no active creature"),
        "enemy_active_after": _active_name(opponent),
        "player_board_before": p_board_before,
        "player_board_after": _board_snapshot(player),
        "enemy_board_before": o_board_before,
        "enemy_board_after": _board_snapshot(opponent),
        "lane_results": lane_results,
        "short_result": short_result,
        "lines": lines,
        "events": list(match.get("round_events") or []),
    }



def resolve_combat(match: Dict[str, Any]) -> Dict[str, Any]:
    if match.get("winner"):
        return match

    player = match["player"]
    opponent = match["opponent"]

    def creature_ref(side: str, creature: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "side": side,
            "instance_id": creature.get("instance_id"),
            "card_id": creature.get("card_id") or creature.get("id"),
            "name": creature.get("name"),
        }

    p_hp_before = int(player.get("hp") or 0)
    o_hp_before = int(opponent.get("hp") or 0)
    p_board_before = _board_snapshot(player)
    o_board_before = _board_snapshot(opponent)

    if not player.get("intent"):
        raise ValueError("Player intent is required before resolving.")

    if not opponent.get("intent"):
        raise ValueError("Opponent intent is required before resolving.")

    add_combat_event(
        match,
        "round_resolve",
        player_intent=player.get("intent"),
        opponent_intent=opponent.get("intent"),
        player_ready=bool(player.get("ready")),
        opponent_ready=bool(opponent.get("ready")),
    )

    player_guard = guard_value(player)
    opponent_guard = guard_value(opponent)
    player["shield"] += player_guard
    opponent["shield"] += opponent_guard

    if player_guard:
        add_event(match, "shield", actor="player", text=f"{player['name']} guarded for {player_guard} shield.", amount=player_guard)
    if opponent_guard:
        add_event(match, "shield", actor="opponent", text=f"{opponent['name']} guarded for {opponent_guard} shield.", amount=opponent_guard)

    if player.get("unleash"):
        hp_before = int(opponent.get("hp") or 0)
        dealt = deal_hero_damage(opponent, UNLEASH_DAMAGE)
        hp_after = int(opponent.get("hp") or 0)
        player["shield"] += UNLEASH_SHIELD
        player["last_damage_dealt"] += dealt
        match["log"].append(f"{player['name']} used Unleash for {dealt} damage.")
        add_event(match, "unleash", actor="player", target="opponent", text=f"{player['name']} used Unleash for {dealt} damage.", amount=dealt)
        add_combat_event(
            match,
            "hero_damage",
            source="unleash",
            attacker_side="player",
            target_side="opponent",
            damage=dealt,
            hp_before=hp_before,
            hp_after=hp_after,
        )

    if opponent.get("unleash"):
        hp_before = int(player.get("hp") or 0)
        dealt = deal_hero_damage(player, UNLEASH_DAMAGE)
        hp_after = int(player.get("hp") or 0)
        opponent["shield"] += UNLEASH_SHIELD
        opponent["last_damage_dealt"] += dealt
        match["log"].append(f"{opponent['name']} used Unleash for {dealt} damage.")
        add_event(match, "unleash", actor="opponent", target="player", text=f"{opponent['name']} used Unleash for {dealt} damage.", amount=dealt)
        add_combat_event(
            match,
            "hero_damage",
            source="unleash",
            attacker_side="opponent",
            target_side="player",
            damage=dealt,
            hp_before=hp_before,
            hp_after=hp_after,
        )

    p_atk = attack_value(player)
    o_atk = attack_value(opponent)
    lane_results = []
    player_board = ensure_board(player)
    opponent_board = ensure_board(opponent)

    for lane in LANES:
        p_creature = player_board.get(lane)
        o_creature = opponent_board.get(lane)
        p_lane_atk = creature_attack_value(player, p_creature)
        o_lane_atk = creature_attack_value(opponent, o_creature)
        result = {
            "lane": lane,
            "player_creature": (p_creature or {}).get("name"),
            "enemy_creature": (o_creature or {}).get("name"),
            "player_damage": 0,
            "enemy_damage": 0,
        }

        if p_creature and o_creature:
            o_before = int(o_creature.get("current_hp") or o_creature.get("hp") or 1)
            p_before = int(p_creature.get("current_hp") or p_creature.get("hp") or 1)
            o_creature["current_hp"] = o_before - p_lane_atk
            p_creature["current_hp"] = p_before - o_lane_atk
            o_after = int(o_creature.get("current_hp") or 0)
            p_after = int(p_creature.get("current_hp") or 0)
            result["player_damage"] = p_lane_atk
            result["enemy_damage"] = o_lane_atk
            add_combat_event(
                match,
                "lane_attack",
                lane=lane,
                attacker=creature_ref("player", p_creature),
                defender=creature_ref("opponent", o_creature),
                damage=p_lane_atk,
            )
            add_combat_event(
                match,
                "lane_attack",
                lane=lane,
                attacker=creature_ref("opponent", o_creature),
                defender=creature_ref("player", p_creature),
                damage=o_lane_atk,
            )
            add_combat_event(
                match,
                "creature_damage",
                lane=lane,
                attacker=creature_ref("player", p_creature),
                defender=creature_ref("opponent", o_creature),
                damage=p_lane_atk,
                hp_before=o_before,
                hp_after=o_after,
            )
            add_combat_event(
                match,
                "creature_damage",
                lane=lane,
                attacker=creature_ref("opponent", o_creature),
                defender=creature_ref("player", p_creature),
                damage=o_lane_atk,
                hp_before=p_before,
                hp_after=p_after,
            )
            add_event(
                match,
                "lane_clash",
                actor="player",
                target="opponent",
                text=f"{lane}: {p_creature['name']} and {o_creature['name']} traded damage.",
                lane=lane,
                amount=p_lane_atk,
                counter_amount=o_lane_atk,
                attacker_instance_id=p_creature.get("instance_id"),
                defender_instance_id=o_creature.get("instance_id"),
            )
        elif p_creature:
            hp_before = int(opponent.get("hp") or 0)
            dealt = deal_hero_damage(opponent, p_lane_atk)
            hp_after = int(opponent.get("hp") or 0)
            player["last_damage_dealt"] += dealt
            result["player_damage"] = dealt
            add_combat_event(
                match,
                "direct_attack",
                lane=lane,
                attacker=creature_ref("player", p_creature),
                target_side="opponent",
                damage=p_lane_atk,
            )
            add_combat_event(
                match,
                "hero_damage",
                lane=lane,
                attacker=creature_ref("player", p_creature),
                target_side="opponent",
                damage=dealt,
                hp_before=hp_before,
                hp_after=hp_after,
            )
            add_event(
                match,
                "lane_hero_damage",
                actor="player",
                target="opponent",
                text=f"{lane}: {p_creature['name']} hit enemy HP for {dealt}.",
                lane=lane,
                amount=dealt,
                attacker_instance_id=p_creature.get("instance_id"),
            )
        elif o_creature:
            hp_before = int(player.get("hp") or 0)
            dealt = deal_hero_damage(player, o_lane_atk)
            hp_after = int(player.get("hp") or 0)
            opponent["last_damage_dealt"] += dealt
            result["enemy_damage"] = dealt
            add_combat_event(
                match,
                "direct_attack",
                lane=lane,
                attacker=creature_ref("opponent", o_creature),
                target_side="player",
                damage=o_lane_atk,
            )
            add_combat_event(
                match,
                "hero_damage",
                lane=lane,
                attacker=creature_ref("opponent", o_creature),
                target_side="player",
                damage=dealt,
                hp_before=hp_before,
                hp_after=hp_after,
            )
            add_event(
                match,
                "lane_hero_damage",
                actor="opponent",
                target="player",
                text=f"{lane}: {o_creature['name']} hit your HP for {dealt}.",
                lane=lane,
                amount=dealt,
                attacker_instance_id=o_creature.get("instance_id"),
            )

        if p_creature or o_creature:
            lane_results.append(result)

    _cleanup_dead_creatures(match, "player")
    _cleanup_dead_creatures(match, "opponent")

    player["ambition"] += ambition_gain_from_intent(player)
    opponent["ambition"] += ambition_gain_from_intent(opponent)
    add_event(match, "ambition", actor="player", text=f"{player['name']} gained Ambition from {player.get('intent') or 'Focus'}.", amount=ambition_gain_from_intent(player))
    add_event(match, "ambition", actor="opponent", text=f"{opponent['name']} gained Ambition from {opponent.get('intent') or 'Focus'}.", amount=ambition_gain_from_intent(opponent))

    check_winner(match)
    if match.get("winner"):
        add_event(match, "match_end", text=f"Match finished. Winner: {match['winner']}.", winner=match.get("winner"), reason=match.get("reason"))

    summary = build_round_summary(
        match,
        p_hp_before=p_hp_before,
        o_hp_before=o_hp_before,
        p_board_before=p_board_before,
        o_board_before=o_board_before,
        p_atk=p_atk,
        o_atk=o_atk,
        lane_results=lane_results,
    )

    match["round_summary"] = summary
    match["log"].append(f"Round {summary['round']}: {summary['short_result']}")

    for line in summary["lines"][-4:]:
        match["log"].append(line)

    add_combat_event(
        match,
        "round_end",
        player_hp=player.get("hp"),
        opponent_hp=opponent.get("hp"),
        winner=match.get("winner"),
        reason=match.get("reason"),
    )

    if not match.get("winner"):
        match["phase"] = "round_start"

    return match


def check_winner(match: Dict[str, Any]) -> None:
    player = match["player"]
    opponent = match["opponent"]

    if player["hp"] <= 0 and opponent["hp"] <= 0:
        finish_by_tiebreak(match, reason="double_ko_tiebreak")
    elif opponent["hp"] <= 0:
        match["winner"] = "player"
        match["reason"] = "opponent_hp_zero"
        match["phase"] = "finished"
    elif player["hp"] <= 0:
        match["winner"] = "opponent"
        match["reason"] = "player_hp_zero"
        match["phase"] = "finished"


def finish_by_tiebreak(match: Dict[str, Any], reason: str) -> None:
    p = match["player"]
    o = match["opponent"]

    if p["hp"] > o["hp"]:
        winner = "player"
    elif o["hp"] > p["hp"]:
        winner = "opponent"
    elif p["ambition"] > o["ambition"]:
        winner = "player"
    elif o["ambition"] > p["ambition"]:
        winner = "opponent"
    elif p.get("last_damage_dealt", 0) > o.get("last_damage_dealt", 0):
        winner = "player"
    elif o.get("last_damage_dealt", 0) > p.get("last_damage_dealt", 0):
        winner = "opponent"
    else:
        winner = "draw"

    match["winner"] = winner
    match["reason"] = reason if winner != "draw" else f"{reason}_draw"
    match["phase"] = "finished"


def bot_choose_action(match: Dict[str, Any]) -> Dict[str, Any]:
    bot = match["opponent"]
    if bot.get("ready"):
        return match

    if not bot.get("intent"):
        intent = "Strike" if board_creatures(bot) or any(card.get("kind") == "creature" for card in playable_cards(bot)) else "Focus"
        choose_intent(match, "opponent", intent)

    lane = first_empty_lane(bot)
    if lane and not bot.get("played_this_round"):
        creatures = [card for card in playable_cards(bot) if card.get("kind") == "creature"]
        if creatures:
            chosen = min(creatures, key=lambda c: (int(c.get("cost") or 0), -int(c.get("atk") or 0), str(c.get("id") or "")))
            play_card(match, "opponent", card_index=bot["hand"].index(chosen), lane=lane)

    bot["ready"] = True
    add_event(match, "ready", actor="opponent", text=f"{bot['name']} is ready.")
    return match


def preview_bot_intent(match: Dict[str, Any]) -> Dict[str, Any]:
    bot = match["opponent"]

    if bot["ambition"] >= UNLEASH_COST:
        return {
            "intent": "Unleash",
            "message": "Enemy has enough Ambition for a special attack.",
        }

    if bot["hp"] <= 12:
        return {
            "intent": "Guard",
            "message": "Enemy is wounded and may defend.",
        }

    if not active_creature(bot):
        return {
            "intent": "Summon",
            "message": "Enemy is likely to summon a creature.",
        }

    return {
        "intent": "Strike",
        "message": "Enemy is preparing pressure.",
    }


def player_auto_action(match: Dict[str, Any]) -> Dict[str, Any]:
    player = match["player"]

    if player["ambition"] >= UNLEASH_COST and match["opponent"]["hp"] <= 14:
        request_unleash(match, "player")

    cards = playable_cards(player)

    if not player.get("intent"):
        choose_intent(match, "player", "Strike")

    lane = first_empty_lane(player)
    if lane:
        creatures = [card for card in cards if card.get("kind") == "creature"]
        if creatures:
            chosen = max(creatures, key=lambda c: (c.get("atk", 0) + c.get("hp", 0), -c.get("cost", 0)))
            play_card(match, "player", card_index=player["hand"].index(chosen), lane=lane)

    player["ready"] = True
    return match


def resolve_round(match: Dict[str, Any]) -> Dict[str, Any]:
    if match.get("opponent", {}).get("is_bot") and not match.get("opponent", {}).get("ready"):
        bot_choose_action(match)

    if not match.get("player", {}).get("ready") or not match.get("opponent", {}).get("ready"):
        raise ValueError("Both players must be ready before resolving.")

    resolve_combat(match)

    if not match.get("winner"):
        start_round(match)

    return match


def play_full_bot_match(seed: Optional[int] = None) -> Dict[str, Any]:
    match = create_match(seed=seed)
    start_round(match)

    while not match.get("winner"):
        player_auto_action(match)
        resolve_round(match)

    return match


def serialize_state(match: Dict[str, Any], public_only: bool = True) -> Dict[str, Any]:
    state = deepcopy(match)

    if public_only:
        state["opponent"]["hand"] = [
            {"id": "hidden", "name": "Hidden Card", "kind": "hidden"}
            for _ in state["opponent"].get("hand", [])
        ]
        state["opponent"]["deck"] = []

    return state


def validate_match_integrity(match: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = []

    if match.get("round", 0) > MAX_ROUNDS + 1:
        errors.append("round above max")

    for side in ("player", "opponent"):
        player = match.get(side) or {}

        if player.get("hp", 0) < 0:
            errors.append(f"{side} negative hp")

        if player.get("energy", 0) < 0:
            errors.append(f"{side} negative energy")

        if player.get("max_energy", 0) > MAX_ENERGY:
            errors.append(f"{side} energy above cap")

        if player.get("intent") and player["intent"] not in VALID_INTENTS:
            errors.append(f"{side} invalid intent")

        field = player.get("field") or {}
        board = ensure_board(player)

        for lane in LANES:
            creature = board.get(lane)
            if not creature:
                continue
            current_hp = creature.get("current_hp")
            if current_hp is None:
                current_hp = creature.get("hp") or 0
            if int(current_hp or 0) <= 0:
                errors.append(f"{side} dead creature still in {lane}")
            if creature.get("lane") != lane:
                errors.append(f"{side} creature lane mismatch in {lane}")

        zones = ["hand", "deck", "discard"]
        for zone in zones:
            for card in player.get(zone) or []:
                if not isinstance(card, dict):
                    errors.append(f"{side} non-dict card in {zone}")
                    continue
                catalog_id = card.get("card_id") or card.get("id")
                if catalog_id not in CARD_CATALOG_V2 and card.get("source") != "official_catalog":
                    errors.append(f"{side} invalid card {catalog_id} in {zone}")

        for slot in ("support",):
            card = field.get(slot)
            catalog_id = (card or {}).get("card_id") or (card or {}).get("id")
            if card and catalog_id not in CARD_CATALOG_V2 and card.get("source") != "official_catalog":
                errors.append(f"{side} invalid field card {catalog_id}")

    return len(errors) == 0, errors

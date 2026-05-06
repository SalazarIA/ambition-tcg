# =========================================================
# Ambitionz Match Actions V1
# Safe action layer for Arena App V1.
# Does not remove legacy handlers yet.
# =========================================================

from copy import deepcopy

from game.cards import CARD_CATALOG
from game.deck import build_playable_deck, draw_starting_hand
from game.state import create_player_state
from game.bot_ai import bot_choose_play


VALID_INTENTS = {"Strike", "Guard", "Focus"}


def _card_id(card):
    if not card:
        return None

    return str(
        card.get("id")
        or card.get("card_id")
        or card.get("runtime_id")
        or card.get("name")
        or ""
    )


def _card_type(card):
    return str(card.get("type") or "Monster")


def _card_cost(card):
    try:
        return int(card.get("cost") or card.get("energy_cost") or 1)
    except Exception:
        return 1


def _card_power(card):
    try:
        return int(card.get("power") or card.get("attack") or card.get("value") or 0)
    except Exception:
        return 0


def ensure_field(player):
    if player is None:
        return {}

    field = player.get("field")

    if not isinstance(field, dict):
        field = {}

    field.setdefault("monster", None)
    field.setdefault("spell", None)
    field.setdefault("trap", None)
    field.setdefault("cards", [])

    player["field"] = field

    return field


def ensure_match_shape(match):
    match.setdefault("round", 1)
    match.setdefault("phase", "intent")
    match.setdefault("training", True)
    match.setdefault("is_bot_match", True)

    for key in ("p1", "p2"):
        player = match.get(key)

        if not player:
            continue

        player.setdefault("hand", [])
        player.setdefault("deck", [])
        player.setdefault("graveyard", [])
        player.setdefault("energy", 2)
        player.setdefault("max_energy", player.get("energy", 2))
        player.setdefault("ambition", 0)
        player.setdefault("intent", None)
        player.setdefault("ready", False)
        ensure_field(player)

    return match


def card_catalog_by_id():
    catalog = {}

    for card in CARD_CATALOG:
        cid = _card_id(card)

        if cid:
            catalog[cid] = card

        if card.get("name"):
            catalog[str(card["name"])] = card

    return catalog


def hydrate_deck_card(card_id):
    catalog = card_catalog_by_id()
    return deepcopy(catalog.get(str(card_id)) or {
        "id": str(card_id),
        "name": str(card_id),
        "type": "Monster",
        "cost": 1,
        "power": 1,
        "rarity": "Common",
        "effect": "",
    })


def build_default_training_deck():
    monsters = [card for card in CARD_CATALOG if str(card.get("type")) == "Monster"]
    spells = [card for card in CARD_CATALOG if str(card.get("type")) == "Spell"]
    traps = [card for card in CARD_CATALOG if str(card.get("type")) == "Trap"]

    chosen = []
    chosen.extend(monsters[:21])
    chosen.extend(spells[:6])
    chosen.extend(traps[:3])

    if len(chosen) < 30:
        chosen.extend(CARD_CATALOG[: 30 - len(chosen)])

    return [deepcopy(card) for card in chosen[:30]]


def create_training_match_v1(user, sid, room_code):
    deck = build_default_training_deck()
    bot_deck = build_default_training_deck()

    hand = deck[:5]
    bot_hand = bot_deck[:5]

    remaining_deck = deck[5:]
    remaining_bot_deck = bot_deck[5:]

    username = getattr(user, "username", None) or "Player"
    user_id = getattr(user, "id", None)

    p1 = {
        "sid": sid,
        "user_id": user_id,
        "name": username,
        "hp": 3600,
        "energy": 2,
        "max_energy": 2,
        "ambition": 0,
        "intent": None,
        "ready": False,
        "hand": hand,
        "deck": remaining_deck,
        "graveyard": [],
        "field": {
            "monster": None,
            "spell": None,
            "trap": None,
            "cards": [],
        },
    }

    p2 = {
        "sid": None,
        "user_id": None,
        "name": "Ambitionz Bot",
        "hp": 3600,
        "energy": 2,
        "max_energy": 2,
        "ambition": 0,
        "intent": "Strike",
        "ready": False,
        "hand": bot_hand,
        "deck": remaining_bot_deck,
        "graveyard": [],
        "field": {
            "monster": None,
            "spell": None,
            "trap": None,
            "cards": [],
        },
    }

    return {
        "id": room_code,
        "room": room_code,
        "mode": "training",
        "training": True,
        "is_bot_match": True,
        "round": 1,
        "phase": "intent",
        "p1": p1,
        "p2": p2,
        "events": [],
    }


def find_card_in_hand(player, card_id):
    hand = player.get("hand") or []

    for index, card in enumerate(hand):
        if _card_id(card) == str(card_id) or str(card.get("name")) == str(card_id):
            return index, card

    return None, None


def zone_for_card(card):
    ctype = _card_type(card)

    if ctype == "Spell":
        return "spell"

    if ctype == "Trap":
        return "trap"

    return "monster"


def can_play_card(player, card):
    if not card:
        return False, "Card not found in hand."

    if player.get("ready"):
        return False, "You already declared Ready."

    cost = _card_cost(card)
    energy = int(player.get("energy") or 0)

    if cost > energy:
        return False, f"Not enough energy. Need {cost}, have {energy}."

    zone = zone_for_card(card)
    field = ensure_field(player)

    if field.get(zone):
        return False, f"{zone.title()} slot is already occupied."

    return True, "OK"


def play_card(match, player_key, card_id):
    ensure_match_shape(match)

    player = match.get(player_key)

    if not player:
        return False, "Player not found."

    index, card = find_card_in_hand(player, card_id)

    if card is None:
        return False, "Card not found in hand."

    ok, message = can_play_card(player, card)

    if not ok:
        return False, message

    hand = player.get("hand") or []
    hand.pop(index)

    cost = _card_cost(card)
    player["energy"] = max(0, int(player.get("energy") or 0) - cost)

    zone = zone_for_card(card)
    field = ensure_field(player)
    field[zone] = card
    field.setdefault("cards", [])

    event = {
        "type": "play_card",
        "player": player_key,
        "card_id": _card_id(card),
        "card_name": card.get("name"),
        "zone": zone,
        "cost": cost,
    }

    match.setdefault("events", []).append(event)
    match["phase"] = "main"

    return True, f"Played {card.get('name', 'card')}."


def set_intent(match, player_key, intent):
    ensure_match_shape(match)

    if intent not in VALID_INTENTS:
        return False, "Invalid intent."

    player = match.get(player_key)

    if not player:
        return False, "Player not found."

    if player.get("ready"):
        return False, "You already declared Ready."

    player["intent"] = intent
    match["phase"] = "main"

    match.setdefault("events", []).append({
        "type": "set_intent",
        "player": player_key,
        "intent": intent,
    })

    return True, f"Intent set to {intent}."


def bot_prepare(match):
    bot = match.get("p2")

    if not bot:
        return

    if not bot.get("intent"):
        bot["intent"] = "Strike"

    # Simple bot: play first affordable card into empty slot.
    for card in list(bot.get("hand") or []):
        ok, _ = can_play_card(bot, card)

        if ok:
            index, found = find_card_in_hand(bot, _card_id(card))

            if found:
                bot["hand"].pop(index)
                bot["energy"] = max(0, int(bot.get("energy") or 0) - _card_cost(found))
                ensure_field(bot)[zone_for_card(found)] = found
                match.setdefault("events", []).append({
                    "type": "bot_play_card",
                    "player": "p2",
                    "card_name": found.get("name"),
                })
                break

    bot["ready"] = True


def simple_damage_from_player(player):
    field = ensure_field(player)
    monster = field.get("monster")

    if not monster:
        return 0

    return max(1, _card_power(monster))


def resolve_round_if_ready(match):
    ensure_match_shape(match)

    p1 = match.get("p1") or {}
    p2 = match.get("p2") or {}

    if not p1.get("ready"):
        return False, "Player is not ready."

    if match.get("training") or match.get("is_bot_match"):
        bot_prepare(match)

    if not p2.get("ready"):
        return False, "Waiting for opponent."

    p1_damage = simple_damage_from_player(p1)
    p2_damage = simple_damage_from_player(p2)

    if p1.get("intent") == "Strike":
        p1_damage += 1

    if p2.get("intent") == "Strike":
        p2_damage += 1

    if p1.get("intent") == "Guard":
        p2_damage = max(0, p2_damage - 1)

    if p2.get("intent") == "Guard":
        p1_damage = max(0, p1_damage - 1)

    if p1.get("intent") == "Focus":
        p1["ambition"] = int(p1.get("ambition") or 0) + 1

    if p2.get("intent") == "Focus":
        p2["ambition"] = int(p2.get("ambition") or 0) + 1

    p2["hp"] = max(0, int(p2.get("hp") or 0) - p1_damage)
    p1["hp"] = max(0, int(p1.get("hp") or 0) - p2_damage)

    match.setdefault("events", []).append({
        "type": "resolve_round",
        "p1_damage": p1_damage,
        "p2_damage": p2_damage,
        "p1_hp": p1.get("hp"),
        "p2_hp": p2.get("hp"),
    })

    # Reset ready and grow energy for next round.
    for player in (p1, p2):
        player["ready"] = False
        player["intent"] = None
        player["max_energy"] = min(10, int(player.get("max_energy") or 2) + 1)
        player["energy"] = int(player.get("max_energy") or 2)

        # Draw one card if possible.
        deck = player.get("deck") or []

        if deck:
            player.setdefault("hand", []).append(deck.pop(0))

    match["round"] = int(match.get("round") or 1) + 1
    match["phase"] = "intent"

    if p1.get("hp", 0) <= 0 or p2.get("hp", 0) <= 0:
        match["phase"] = "finished"

        if p1.get("hp", 0) > p2.get("hp", 0):
            match["winner"] = "p1"
        elif p2.get("hp", 0) > p1.get("hp", 0):
            match["winner"] = "p2"
        else:
            match["winner"] = "draw"

    return True, "Round resolved."


def declare_ready(match, player_key):
    ensure_match_shape(match)

    player = match.get(player_key)

    if not player:
        return False, "Player not found."

    if not player.get("intent"):
        return False, "Choose an intent first."

    player["ready"] = True
    match.setdefault("events", []).append({
        "type": "declare_ready",
        "player": player_key,
    })

    resolved, message = resolve_round_if_ready(match)

    if resolved:
        return True, message

    return True, "Ready declared."

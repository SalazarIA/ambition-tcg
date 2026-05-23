from copy import deepcopy
import hashlib

from services.rebirth_cards import is_monster


BOT_PERSONALITY_ORDER = ("defensive", "aggressive", "opportunist")

BOT_PERSONALITIES = {
    "defensive": {
        "id": "defensive",
        "name": "Bot Defensivo",
        "copy": "Prioriza guarda e respostas estáveis antes de picos de dano.",
        "policy": "vence com corpos protegidos; caso contrário, absorve com a maior guarda",
    },
    "aggressive": {
        "id": "aggressive",
        "name": "Bot Agressivo",
        "copy": "Pressiona com a maior linha de ataque e tenta encerrar combates rapidamente.",
        "policy": "joga o maior ataque disponível, priorizando ataques vencedores",
    },
    "opportunist": {
        "id": "opportunist",
        "name": "Bot Oportunista",
        "copy": "Busca viradas por habilidades, finalizações e janelas de pressão.",
        "policy": "prefere cartas de virada por habilidade e depois a menor vitória limpa",
    },
}

ABILITY_PRIORITIES = {
    "fire_execute": 9,
    "shadow_drain": 9,
    "shadow_lifesteal": 8,
    "shadow_mark": 8,
    "fire_burn": 7,
    "fire_direct": 7,
    "earth_counter": 6,
    "water_tide": 6,
    "shadow_decay": 6,
    "fire_surge": 5,
    "earth_shield": 5,
    "water_heal": 5,
    "earth_fortify": 4,
    "earth_bulwark": 4,
    "water_cleanse": 4,
    "water_guard": 3,
    "bleed_mark": 8,
    "fade_cut": 7,
    "inferno_bite": 7,
    "apex_rend": 7,
    "storm_dive": 6,
    "silent_pursuit": 6,
    "rending_strike": 5,
    "molten_bite": 4,
    "fortress_hit": 4,
    "immovable": 3,
    "bulwark": 3,
    "brace": 2,
    "high_guard": 2,
}


def card_attack(card):
    return int(card.get("attack", card.get("power", 0)) or 0)


def card_guard(card):
    return int(card.get("guard", 0) or 0)


def ability_priority(card):
    return ABILITY_PRIORITIES.get(str(card.get("ability_key") or ""), int(card.get("ability_weight", 0) or 0))


def ability_key(card):
    return str(card.get("ability_key") or "")


def estimated_attack(card, opponent_card, turn=1):
    attack = card_attack(card)
    key = ability_key(card)
    if key == "high_guard" and card_guard(opponent_card) <= 3:
        attack += 1
    elif key == "silent_pursuit" and int(turn or 1) <= 2:
        attack += 1
    return attack


def tie_priority(card, defender_wounded=False):
    return 2 if ability_key(card) in {"fade_cut", "bleed_mark"} and defender_wounded else 0


def estimated_damage(attacker, defender, defender_wounded=False):
    amount = max(1, card_attack(attacker) - card_guard(defender) // 2)
    attacker_key = ability_key(attacker)
    defender_key = ability_key(defender)
    if attacker_key == "rending_strike" and defender_wounded:
        amount += 2
    elif attacker_key == "apex_rend" and defender_wounded:
        amount += 3
    elif attacker_key == "molten_bite":
        amount += 1
    elif attacker_key == "inferno_bite":
        amount += 3
    elif attacker_key == "bleed_mark":
        amount += 1
    elif attacker_key == "storm_dive" and card_guard(defender) <= 3:
        amount += 2
    elif attacker_key == "immovable":
        amount += 2
    if attacker_key == "fortress_hit":
        amount = max(3, amount)

    reductions = {
        "brace": 2,
        "immovable": 3,
        "fortress_hit": 4,
    }
    reduction = reductions.get(defender_key, 0)
    if defender_key == "bulwark" and card_attack(attacker) <= 4:
        reduction = 3
    return max(1, amount - reduction) if reduction else amount


def response_projection(card, player_card, *, turn=1, player_wounded=False, bot_wounded=False):
    bot_attack = estimated_attack(card, player_card, turn=turn)
    player_attack = estimated_attack(player_card, card, turn=turn)
    if bot_attack > player_attack:
        damage = estimated_damage(card, player_card, defender_wounded=player_wounded)
        return {"outcome": "win", "damage_dealt": damage, "damage_taken": 0}
    if player_attack > bot_attack:
        damage = estimated_damage(player_card, card, defender_wounded=bot_wounded)
        return {"outcome": "loss", "damage_dealt": 0, "damage_taken": damage}

    bot_priority = tie_priority(card, defender_wounded=player_wounded)
    player_priority = tie_priority(player_card, defender_wounded=bot_wounded)
    if bot_priority > player_priority:
        damage = estimated_damage(card, player_card, defender_wounded=player_wounded)
        return {"outcome": "win", "damage_dealt": damage, "damage_taken": 0}
    if player_priority > bot_priority:
        damage = estimated_damage(player_card, card, defender_wounded=bot_wounded)
        return {"outcome": "loss", "damage_dealt": 0, "damage_taken": damage}
    return {"outcome": "tie", "damage_dealt": 0, "damage_taken": 0}


def normalize_personality(profile_id=None):
    profile_id = str(profile_id or "defensive").strip().lower()
    if profile_id not in BOT_PERSONALITIES:
        return "defensive"
    return profile_id


def personality_payload(profile_id=None):
    return deepcopy(BOT_PERSONALITIES[normalize_personality(profile_id)])


def choose_personality(seed=None, match_id=None):
    source = str(seed or match_id or "rebirth-bot")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return BOT_PERSONALITY_ORDER[int(digest[:2], 16) % len(BOT_PERSONALITY_ORDER)]


def winning_cards(bot_hand, player_card, **context):
    return [
        card
        for card in bot_hand
        if response_projection(card, player_card, **context)["outcome"] == "win"
    ]


def choose_defensive(bot_hand, player_card, **context):
    def key(card):
        projection = response_projection(card, player_card, **context)
        outcome_rank = {"loss": 0, "tie": 1, "win": 2}[projection["outcome"]]
        return (
            outcome_rank,
            -projection["damage_taken"],
            card_guard(card),
            projection["damage_dealt"],
            card_attack(card),
            card["name"],
        )

    return sorted(bot_hand, key=key)[-1]


def choose_aggressive(bot_hand, player_card, **context):
    def key(card):
        projection = response_projection(card, player_card, **context)
        return (
            card_attack(card),
            ability_priority(card),
            projection["damage_dealt"],
            -projection["damage_taken"],
            card_guard(card),
            card["name"],
        )

    return sorted(bot_hand, key=key)[-1]


def choose_opportunist(bot_hand, player_card, **context):
    def key(card):
        projection = response_projection(card, player_card, **context)
        swing = projection["damage_dealt"] - projection["damage_taken"]
        return (
            ability_priority(card),
            card_attack(card),
            swing,
            projection["damage_dealt"],
            card_guard(card),
            card["name"],
        )

    return sorted(bot_hand, key=key)[-1]


def choose_projected_counter(bot_hand, player_card, **context):
    def key(card):
        projection = response_projection(card, player_card, **context)
        outcome_rank = {"loss": 0, "tie": 1, "win": 2}[projection["outcome"]]
        swing = projection["damage_dealt"] - projection["damage_taken"]
        return (
            outcome_rank,
            swing,
            projection["damage_dealt"],
            -projection["damage_taken"],
            ability_priority(card),
            card_attack(card),
            card_guard(card),
            card["name"],
        )

    return sorted(bot_hand, key=key)[-1]


def counter_window(profile_id, bot_hand, player_card, turn=1, match_id=None):
    if not match_id:
        return False
    rates = {
        "defensive": 0.45,
        "aggressive": 0.45,
        "opportunist": 0.85,
    }
    source = "|".join(
        [
            str(profile_id),
            str(match_id or ""),
            str(turn or 1),
            str(player_card.get("id") or ""),
            ",".join(str(card.get("id") or "") for card in bot_hand),
        ]
    )
    roll = int(hashlib.sha256(source.encode("utf-8")).hexdigest()[:4], 16) / 0xFFFF
    return roll < rates.get(profile_id, 0.3)


def bot_decision_payload(bot_hand, player_card, profile_id=None, *, turn=1, player_wounded=False, bot_wounded=False, match_id=None):
    return {
        "profile_id": normalize_personality(profile_id),
        "bot_hand": [deepcopy(card) for card in bot_hand if is_monster(card)],
        "player_card": deepcopy(player_card),
        "context": {
            "turn": int(turn or 1),
            "player_wounded": bool(player_wounded),
            "bot_wounded": bool(bot_wounded),
            "match_id": match_id,
        },
    }


def resolve_bot_decision_payload(payload):
    payload = deepcopy(payload or {})
    profile_id = normalize_personality(payload.get("profile_id"))
    bot_hand = [card for card in payload.get("bot_hand", []) if is_monster(card)]
    player_card = payload.get("player_card")
    if not bot_hand:
        return {"profile_id": profile_id, "decision": None, "mode": "payload"}

    context = payload.get("context") or {}
    decision_context = {
        "turn": int(context.get("turn", 1) or 1),
        "player_wounded": bool(context.get("player_wounded", False)),
        "bot_wounded": bool(context.get("bot_wounded", False)),
    }
    match_id = context.get("match_id")
    if counter_window(profile_id, bot_hand, player_card, turn=decision_context["turn"], match_id=match_id):
        choice = choose_projected_counter(bot_hand, player_card, **decision_context)
    elif profile_id == "aggressive":
        choice = choose_aggressive(bot_hand, player_card, **decision_context)
    elif profile_id == "opportunist":
        choice = choose_opportunist(bot_hand, player_card, **decision_context)
    else:
        choice = choose_defensive(bot_hand, player_card, **decision_context)
    return {
        "profile_id": profile_id,
        "decision": deepcopy(choice),
        "decision_card_id": choice.get("id"),
        "decision_instance_id": choice.get("instance_id"),
        "mode": "payload",
    }


async def choose_response_async(payload):
    return resolve_bot_decision_payload(payload)


def choose_response(bot_hand, player_card, profile_id=None, *, turn=1, player_wounded=False, bot_wounded=False, match_id=None):
    payload = bot_decision_payload(
        bot_hand,
        player_card,
        profile_id,
        turn=turn,
        player_wounded=player_wounded,
        bot_wounded=bot_wounded,
        match_id=match_id,
    )
    return resolve_bot_decision_payload(payload)["decision"]

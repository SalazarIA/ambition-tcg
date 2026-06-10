from copy import deepcopy
import hashlib

from services.rebirth_cards import is_monster
from services.rebirth_contracts import FIELD_SLOT_COUNT
from services.rebirth_profiler import current_profiler


BOT_PERSONALITY_ORDER = ("defensive", "aggressive", "opportunist")
MAX_SIMULATION_TIME_MS = 35
MCTS_ROLLOUT_DEPTH_LIMIT = 4
MCTS_BEAM_WIDTH = 6
MCTS_SIMULATION_BUDGET = 48
CI_SAFE_SIMULATION_CEILING = 24

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
    # Primeiro duelo: bot intencionalmente comete erro tático invocando a carta
    # mais fraca da mão e nunca aciona counter_window. Garante que o jogador
    # novo tenha uma "leitura óbvia" para vencer.
    "novice": {
        "id": "novice",
        "name": "Bot Iniciante",
        "copy": "Recém-treinado. Comete erros de leitura e abre janelas claras de contra-ataque.",
        "policy": "invoca a carta mais leve da mão e ignora janelas de counter",
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


def card_tier(card):
    return max(1, int(card.get("tier", 1) or 1))


def current_guard(card):
    return int(card.get("current_guard", card.get("guard", 0)) or 0)


def card_utility_value(card):
    vector = heuristic_vector(card)
    return (
        card_attack(card) * 3
        + card_guard(card) * 2
        + card_tier(card) * 8
        + normalize_heuristic(vector["trigger_threat"]) * 2
        + threat_score(card)
        + passive_prediction(card)
    )


def normalize_heuristic(value, *, ceiling=10):
    value = max(0, int(value or 0))
    ceiling = max(1, int(ceiling or 1))
    return min(ceiling, value)


def heuristic_vector(card):
    vector = card.get("heuristic_vector") if isinstance(card, dict) else None
    vector = vector if isinstance(vector, dict) else {}
    attack = card_attack(card)
    guard = max(card_guard(card), current_guard(card))
    return {
        "scaling_potential": normalize_heuristic(vector.get("scaling_potential", int(card.get("permanent_attack_bonus", 0) or 0))),
        "survivability": normalize_heuristic(vector.get("survivability", guard)),
        "trigger_threat": normalize_heuristic(vector.get("trigger_threat", ability_priority(card))),
        "board_tempo": normalize_heuristic(vector.get("board_tempo", attack + card_tier(card))),
        "value_persistence": normalize_heuristic(vector.get("value_persistence", card_tier(card) + int(card.get("permanent_attack_bonus", 0) or 0))),
        "future_resource_swing": normalize_heuristic(vector.get("future_resource_swing", 0)),
    }


GENERIC_THREAT_WEIGHTS = {
    "scaling_potential": 4,
    "survivability": 3,
    "trigger_threat": 4,
    "board_tempo": 3,
    "value_persistence": 3,
    "future_resource_swing": 2,
}


def threat_score(card):
    vector = heuristic_vector(card)
    return sum(vector[name] * weight for name, weight in GENERIC_THREAT_WEIGHTS.items())


def passive_prediction(card):
    vector = heuristic_vector(card)
    exhausted_penalty = 4 if card.get("has_acted", card.get("has_attacked", False)) else 0
    return max(
        0,
        vector["scaling_potential"] * 2
        + vector["trigger_threat"]
        + vector["future_resource_swing"]
        + vector["value_persistence"]
        - exhausted_penalty,
    )


def _card_identity(card):
    return card.get("instance_id") or card.get("id") or id(card)


def _can_act_now(card):
    if card.get("exhausted") or card.get("has_attacked") or card.get("has_acted"):
        return False
    if card.get("just_summoned") and "RUSH" not in (card.get("keywords") or []):
        return False
    return True


def _ready_board_cards(cards, excluded=None):
    excluded_key = _card_identity(excluded) if excluded else None
    return [
        card
        for card in cards or []
        if card and _card_identity(card) != excluded_key and _can_act_now(card)
    ]


def _combat_context(context):
    return {
        "turn": int(context.get("turn", 1) or 1),
        "player_wounded": bool(context.get("player_wounded", False)),
        "bot_wounded": bool(context.get("bot_wounded", False)),
    }


def remaining_damage_vector(bot_battlefield, *, excluded_attacker=None):
    cards = _ready_board_cards(bot_battlefield, excluded=excluded_attacker)
    return {
        "total": sum(card_attack(card) for card in cards),
        "cards": [
            {
                "id": card.get("id"),
                "instance_id": card.get("instance_id"),
                "attack": card_attack(card),
                "tier": card_tier(card),
            }
            for card in cards
        ],
    }


# v69: Breakthrough threat awareness. O engine concede até +2 de dano direto
# ao herói quando o attack supera a guard do defender (services/rebirth_engine.py:1109).
# A heurística ignorava esse vazamento, então defensive/aggressive deixavam Bramblehorn
# Knight encadear pressão hero. Esta função estima a pressão por ataque
# adversário sobre uma pool de guard agregada, capada no mesmo teto do engine.
BREAKTHROUGH_CAP = 2


def breakthrough_potential(opponent_card, defender_guard_pool):
    """Estima hero damage que opponent_card causaria se atacasse contra a pool agregada de guards."""
    if not opponent_card:
        return 0
    atk = card_attack(opponent_card)
    if atk <= 0:
        return 0
    pool = max(0, int(defender_guard_pool or 0))
    excess = atk - pool
    return max(0, min(BREAKTHROUGH_CAP, excess))


def opponent_breakthrough_pressure(opponent_battlefield, defender_battlefield, *, excluded_defender=None):
    """Pressão total de Breakthrough do board oponente contra a pool de defenders.

    Pareia cada attacker oponente com o maior blocker disponível; sobrando attackers,
    cada um contribui com o teto de breakthrough contra guard zero.
    """
    excluded_key = _card_identity(excluded_defender) if excluded_defender else None
    defender_pool = sorted(
        (
            current_guard(card)
            for card in defender_battlefield or []
            if card and _card_identity(card) != excluded_key and current_guard(card) > 0
        ),
        reverse=True,
    )
    pressure = 0
    for opponent in opponent_battlefield or []:
        if not opponent:
            continue
        blocker = defender_pool.pop(0) if defender_pool else 0
        pressure += breakthrough_potential(opponent, blocker)
    return pressure


def attack_utility_projection(
    attacker,
    target,
    *,
    bot_battlefield=None,
    player_battlefield=None,
    player_hp=30,
    turn=1,
    player_wounded=False,
    bot_wounded=False,
):
    if not attacker:
        return {"allowed": False, "utility": -100000, "reason": "missing_attacker"}
    if not target:
        direct_damage = card_attack(attacker)
        remaining_damage = remaining_damage_vector(bot_battlefield or [], excluded_attacker=attacker)
        lethal_window = direct_damage + remaining_damage["total"] >= int(player_hp or 0)
        direct_weight = 10 if int(turn or 1) >= 4 else 7
        return {
            "allowed": direct_damage > 0,
            "utility": direct_damage * direct_weight + (5000 if lethal_window else 0),
            "reason": "direct_lethal" if lethal_window else "direct_pressure",
            "outcome": "direct",
            "damage_dealt": direct_damage,
            "damage_taken": 0,
            "attacker_destroyed": False,
            "target_destroyed": False,
            "symmetric_suicide": False,
            "lethal_window": lethal_window,
            "remaining_damage": remaining_damage,
        }

    combat = _combat_context({"turn": turn, "player_wounded": player_wounded, "bot_wounded": bot_wounded})
    projection = response_projection(attacker, target, **combat)
    bot_attack = estimated_attack(attacker, target, turn=combat["turn"])
    player_attack = estimated_attack(target, attacker, turn=combat["turn"])
    attacker_guard_after = current_guard(attacker)
    target_guard_after = current_guard(target)

    if projection["outcome"] == "win":
        target_guard_after -= max(1, projection["damage_dealt"])
    elif projection["outcome"] == "loss":
        attacker_guard_after -= max(1, projection["damage_taken"])
    else:
        attacker_guard_after -= max(1, player_attack)
        target_guard_after -= max(1, bot_attack)

    attacker_destroyed = attacker_guard_after <= 0
    target_destroyed = target_guard_after <= 0
    target_value = card_utility_value(target) if target_destroyed else max(1, bot_attack) + threat_score(target) // 3
    own_loss = card_utility_value(attacker) if attacker_destroyed else max(0, current_guard(attacker) - attacker_guard_after)
    remaining_player_cards = [
        card
        for card in player_battlefield or [target]
        if card and (_card_identity(card) != _card_identity(target) or not target_destroyed)
    ]
    remaining_damage = remaining_damage_vector(bot_battlefield or [attacker], excluded_attacker=attacker)
    lethal_window = not remaining_player_cards and remaining_damage["total"] >= int(player_hp or 0)
    symmetric_suicide = projection["outcome"] == "tie" and attacker_destroyed and target_destroyed
    high_tier_suicide = symmetric_suicide and card_tier(attacker) >= 2
    allowed = not high_tier_suicide or lethal_window
    utility = (
        target_value
        + projection["damage_dealt"] * 5
        - own_loss
        - projection["damage_taken"] * 4
        + passive_prediction(attacker)
        + (threat_score(target) // 2 if target_destroyed else 0)
        + (5000 if lethal_window else 0)
    )
    future_lethal_risk = bool(target and not target_destroyed and threat_score(target) >= 32 and attacker_destroyed)
    if future_lethal_risk:
        utility -= 12000
        allowed = False
    if high_tier_suicide and not lethal_window:
        utility -= 100000

    # v69: bônus/penalidade por Breakthrough threat. defender_guard_pool é a pool de
    # blockers do bot disponível APÓS este ataque (descontando o próprio attacker, que
    # fica exhausto). Se target sobreviver, vamos pagar essa pressão no próximo turno
    # do player; se cair, o board fica mais limpo pra absorver os demais.
    defender_guard_pool = sum(
        current_guard(card)
        for card in (bot_battlefield or [])
        if card and _card_identity(card) != _card_identity(attacker) and current_guard(card) > 0
    )
    target_breakthrough = breakthrough_potential(target, defender_guard_pool)
    breakthrough_reason = None
    if target_breakthrough > 0:
        if target_destroyed:
            utility += target_breakthrough * 40
            breakthrough_reason = "neutralize_breakthrough"
        else:
            utility -= target_breakthrough * 15
            breakthrough_reason = "leaves_breakthrough_alive"

    reason = (
        "lethal_window" if lethal_window
        else "avoid_future_lethal" if future_lethal_risk
        else "refuse_high_tier_suicide" if not allowed
        else breakthrough_reason or "trade_value"
    )

    return {
        "allowed": allowed,
        "utility": utility,
        "reason": reason,
        "outcome": projection["outcome"],
        "damage_dealt": projection["damage_dealt"],
        "damage_taken": projection["damage_taken"],
        "attacker_destroyed": attacker_destroyed,
        "target_destroyed": target_destroyed,
        "symmetric_suicide": symmetric_suicide,
        "remaining_damage": remaining_damage,
        "breakthrough_pressure": target_breakthrough,
    }


def tactical_utility_matrix(
    bot_battlefield,
    player_battlefield,
    *,
    player_hp=30,
    turn=1,
    player_wounded=False,
    bot_wounded=False,
):
    rows = []
    attackers = deterministic_move_order((bot_battlefield or [])[:FIELD_SLOT_COUNT])[:MCTS_BEAM_WIDTH]
    for attacker in attackers:
        if not attacker or not _can_act_now(attacker):
            continue
        targets = deterministic_move_order((player_battlefield or [])[:FIELD_SLOT_COUNT])[:MCTS_BEAM_WIDTH] or [None]
        for target in targets:
            projection = attack_utility_projection(
                attacker,
                target,
                bot_battlefield=bot_battlefield,
                player_battlefield=player_battlefield,
                player_hp=player_hp,
                turn=turn,
                player_wounded=player_wounded,
                bot_wounded=bot_wounded,
            )
            rows.append(
                {
                    "attacker_id": attacker.get("id"),
                    "attacker_instance_id": attacker.get("instance_id"),
                    "target_id": target.get("id") if target else None,
                    "target_instance_id": target.get("instance_id") if target else None,
                    **projection,
                }
            )
    return rows


def deterministic_move_order(cards):
    return sorted(
        [card for card in cards or [] if card],
        key=lambda card: (
            -threat_score(card),
            -card_attack(card),
            -card_guard(card),
            int(card.get("field_slot", card.get("slot", 0)) or 0),
            str(card.get("instance_id") or card.get("id") or ""),
        ),
    )


def beam_prune_moves(rows, width=MCTS_BEAM_WIDTH):
    return sorted(
        rows or [],
        key=lambda row: (
            -int(row.get("utility", 0) or 0),
            str(row.get("attacker_instance_id") or ""),
            str(row.get("target_instance_id") or ""),
        ),
    )[: max(1, int(width or 1))]


class MCTSAgent:
    """Deterministic, CI-safe rollout facade for future full MCTS work."""

    def __init__(self, *, budget=MCTS_SIMULATION_BUDGET, depth_limit=MCTS_ROLLOUT_DEPTH_LIMIT, beam_width=MCTS_BEAM_WIDTH):
        self.budget = min(int(budget or 0), CI_SAFE_SIMULATION_CEILING)
        self.depth_limit = max(1, min(int(depth_limit or 1), MCTS_ROLLOUT_DEPTH_LIMIT))
        self.beam_width = max(1, min(int(beam_width or 1), MCTS_BEAM_WIDTH))
        self.max_simulation_time_ms = MAX_SIMULATION_TIME_MS

    def rank_attacks(self, bot_battlefield, player_battlefield, **context):
        matrix = tactical_utility_matrix(bot_battlefield, player_battlefield, **context)
        pruned = beam_prune_moves(matrix, width=self.beam_width)
        return pruned[: self.budget]

    def choose_attack(self, bot_battlefield, player_battlefield, **context):
        profiler = current_profiler()
        if profiler:
            with profiler.timer("MCTS_simulation_cost", detail="choose_attack"):
                ranked = self.rank_attacks(bot_battlefield, player_battlefield, **context)
        else:
            ranked = self.rank_attacks(bot_battlefield, player_battlefield, **context)
        if not ranked:
            return None
        allowed = [row for row in ranked if row.get("allowed")]
        if not allowed:
            return None
        return allowed[0]


def choose_bot_attack(bot_battlefield, player_battlefield, **context):
    return MCTSAgent().choose_attack(bot_battlefield, player_battlefield, **context)


def estimated_attack(card, opponent_card, turn=1):
    # Espelha clash_attack do engine — os pontos cegos antigos (water_tide,
    # fire_surge, earth_fortify) faziam o bot errar trocas contra ÁGUA/TERRA.
    attack = card_attack(card)
    key = ability_key(card)
    if key == "high_guard" and card_guard(opponent_card) <= 3:
        attack += 1
    elif key == "silent_pursuit" and int(turn or 1) <= 2:
        attack += 1
    elif key == "fire_surge" and int(turn or 1) <= 2:
        attack += 2
    elif key == "water_tide" and int(turn or 1) >= 3:
        attack += 2
    elif key == "earth_fortify":
        attack += min(2, max(0, card_guard(card) // 4))
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
    elif attacker_key == "fire_direct":
        amount += 2
    elif attacker_key == "fire_execute" and defender_wounded:
        amount += 2
    elif attacker_key == "shadow_decay":
        amount += 1
    elif attacker_key == "shadow_drain":
        amount += 1
    if attacker_key == "fortress_hit":
        amount = max(3, amount)

    reductions = {
        "brace": 2,
        "immovable": 3,
        "fortress_hit": 4,
        "water_guard": 2,
        "earth_bulwark": 3,
    }
    reduction = reductions.get(defender_key, 0)
    if defender_key in {"bulwark", "earth_counter"} and card_attack(attacker) <= 4:
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
        if response_projection(card, player_card, **_combat_context(context))["outcome"] == "win"
        and attack_utility_projection(
            card,
            player_card,
            bot_battlefield=context.get("bot_battlefield") or bot_hand,
            player_battlefield=context.get("player_battlefield") or [player_card],
            player_hp=context.get("player_hp", 30),
            **_combat_context(context),
        )["allowed"]
    ]


def choose_defensive(bot_hand, player_card, **context):
    def key(card):
        combat_context = _combat_context(context)
        projection = response_projection(card, player_card, **combat_context)
        utility = attack_utility_projection(
            card,
            player_card,
            bot_battlefield=context.get("bot_battlefield") or bot_hand,
            player_battlefield=context.get("player_battlefield") or [player_card],
            player_hp=context.get("player_hp", 30),
            **combat_context,
        )
        outcome_rank = {"loss": 0, "tie": 1, "win": 2}[projection["outcome"]]
        return (
            1 if utility["allowed"] else 0,
            outcome_rank,
            -projection["damage_taken"],
            card_guard(card),
            projection["damage_dealt"],
            ability_priority(card),
            utility["utility"],
            card_attack(card),
            card["name"],
        )

    return sorted(bot_hand, key=key)[-1]


def choose_aggressive(bot_hand, player_card, **context):
    def key(card):
        combat_context = _combat_context(context)
        projection = response_projection(card, player_card, **combat_context)
        utility = attack_utility_projection(
            card,
            player_card,
            bot_battlefield=context.get("bot_battlefield") or bot_hand,
            player_battlefield=context.get("player_battlefield") or [player_card],
            player_hp=context.get("player_hp", 30),
            **combat_context,
        )
        outcome_rank = {"loss": 0, "tie": 1, "win": 2}[projection["outcome"]]
        lethal_rank = 1 if utility.get("reason") == "lethal_window" or utility.get("lethal_window") else 0
        return (
            1 if utility["allowed"] else 0,
            lethal_rank,
            outcome_rank,
            card_attack(card),
            ability_priority(card),
            projection["damage_dealt"],
            -projection["damage_taken"],
            utility["utility"],
            card_guard(card),
            card["name"],
        )

    return sorted(bot_hand, key=key)[-1]


def choose_opportunist(bot_hand, player_card, **context):
    def key(card):
        combat_context = _combat_context(context)
        projection = response_projection(card, player_card, **combat_context)
        utility = attack_utility_projection(
            card,
            player_card,
            bot_battlefield=context.get("bot_battlefield") or bot_hand,
            player_battlefield=context.get("player_battlefield") or [player_card],
            player_hp=context.get("player_hp", 30),
            **combat_context,
        )
        swing = projection["damage_dealt"] - projection["damage_taken"]
        return (
            1 if utility["allowed"] else 0,
            ability_priority(card),
            card_attack(card),
            swing,
            projection["damage_dealt"],
            utility["utility"],
            card_guard(card),
            card["name"],
        )

    return sorted(bot_hand, key=key)[-1]


def choose_novice(bot_hand, player_card, **context):
    """Picks the weakest viable card in hand — by design.

    Goal is a scripted-feeling "enemy mistake" on the very first duel. We sort
    ascending by attack, so the bot summons a low-pressure body that the
    player's stacked opener can usually trade up against."""

    def key(card):
        return (
            card_attack(card),
            ability_priority(card),
            card_guard(card),
            card["name"],
        )

    # asc sort → first card is the weakest
    return sorted(bot_hand, key=key)[0]


def choose_projected_counter(bot_hand, player_card, **context):
    def key(card):
        combat_context = _combat_context(context)
        projection = response_projection(card, player_card, **combat_context)
        utility = attack_utility_projection(
            card,
            player_card,
            bot_battlefield=context.get("bot_battlefield") or bot_hand,
            player_battlefield=context.get("player_battlefield") or [player_card],
            player_hp=context.get("player_hp", 30),
            **combat_context,
        )
        outcome_rank = {"loss": 0, "tie": 1, "win": 2}[projection["outcome"]]
        swing = projection["damage_dealt"] - projection["damage_taken"]
        return (
            1 if utility["allowed"] else 0,
            outcome_rank,
            swing,
            projection["damage_dealt"],
            -projection["damage_taken"],
            utility["utility"],
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
        "defensive": 0.78,
        # Aggressive já joga linhas de pressão por padrão; counter rate alto
        # somado ao MCTS deixava o perfil ler o jogador com precisão demais.
        "aggressive": 0.0,
        # Opportunist baixo demais fica predatório; alto demais alonga partidas
        # e entrega vitórias grátis. 0.35 mantém a personalidade reativa sem
        # estourar o spread de dificuldade entre perfis (recalibrado pós-keywords).
        "opportunist": 0.35,
        # Novice nunca abre janela de counter — primeira partida não pode
        # punir o jogador com leituras avançadas.
        "novice": 0.0,
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


def bot_decision_payload(
    bot_hand,
    player_card,
    profile_id=None,
    *,
    turn=1,
    player_wounded=False,
    bot_wounded=False,
    match_id=None,
    bot_battlefield=None,
    player_battlefield=None,
    player_hp=30,
):
    return {
        "profile_id": normalize_personality(profile_id),
        "bot_hand": [deepcopy(card) for card in bot_hand if is_monster(card)],
        "player_card": deepcopy(player_card),
        "context": {
            "turn": int(turn or 1),
            "player_wounded": bool(player_wounded),
            "bot_wounded": bool(bot_wounded),
            "match_id": match_id,
            "bot_battlefield": [deepcopy(card) for card in (bot_battlefield or []) if is_monster(card)],
            "player_battlefield": [deepcopy(card) for card in (player_battlefield or []) if is_monster(card)],
            "player_hp": int(player_hp or 0),
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
        "bot_battlefield": [card for card in context.get("bot_battlefield", []) if is_monster(card)] or bot_hand,
        "player_battlefield": [card for card in context.get("player_battlefield", []) if is_monster(card)] or ([player_card] if player_card else []),
        "player_hp": int(context.get("player_hp", 30) or 0),
    }
    match_id = context.get("match_id")
    if profile_id == "novice":
        # novice ignora counter window e simplesmente joga sua menor carta
        choice = choose_novice(bot_hand, player_card, **decision_context)
    elif counter_window(profile_id, bot_hand, player_card, turn=decision_context["turn"], match_id=match_id):
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


def choose_response(
    bot_hand,
    player_card,
    profile_id=None,
    *,
    turn=1,
    player_wounded=False,
    bot_wounded=False,
    match_id=None,
    bot_battlefield=None,
    player_battlefield=None,
    player_hp=30,
):
    payload = bot_decision_payload(
        bot_hand,
        player_card,
        profile_id,
        turn=turn,
        player_wounded=player_wounded,
        bot_wounded=bot_wounded,
        match_id=match_id,
        bot_battlefield=bot_battlefield,
        player_battlefield=player_battlefield,
        player_hp=player_hp,
    )
    return resolve_bot_decision_payload(payload)["decision"]

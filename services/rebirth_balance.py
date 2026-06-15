import hashlib
from collections import Counter, defaultdict

from services.rebirth_bot import BOT_PERSONALITY_ORDER, BOT_PERSONALITIES
from services.rebirth_cards import (
    BASE_MONSTERS,
    LEGENDARY_CARDS,
    SPELL_CARDS,
    TRAP_CARDS,
    catalog_payload,
    is_monster,
    is_spell,
    is_trap,
    validate_deck_distribution,
)
from services.rebirth_contracts import FIELD_SLOT_COUNT, RebirthError
from services.rebirth_engine import (
    compare_clash,
    damage_details,
    start_match,
)
from services.rebirth_dispatcher import (
    DeclareAttackCommand,
    EndTurnCommand,
    EvolveDuplicateCommand,
    SummonCardCommand,
    dispatch_command,
)
from services.rebirth_state import available_evolutions
from services.rebirth_bot import ability_priority, choose_response


# audit P1.3: the balance lab must exercise the SAME command dispatcher the HTTP
# layer uses, not the engine directly. dispatch_command delegates to the same
# engine functions and adds the command/event log, canonical state hash and
# parity checkpoints — so match outcomes are identical while the simulation
# gains production fidelity. These thin wrappers keep every call site unchanged.
def play_card(match, card_instance_id=None, card_id=None, field_slot=None, target_instance_id=None):
    return dispatch_command(
        match,
        SummonCardCommand(
            card_instance_id=card_instance_id,
            card_id=card_id,
            field_slot=field_slot,
            target_instance_id=target_instance_id,
        ),
    )


def declare_attack(match, attacker_instance_id=None, target_instance_id=None):
    return dispatch_command(
        match,
        DeclareAttackCommand(attacker_instance_id=attacker_instance_id, target_instance_id=target_instance_id),
    )


def next_turn(match):
    return dispatch_command(match, EndTurnCommand())


def evolve_duplicate(match, card_id):
    return dispatch_command(match, EvolveDuplicateCommand(card_id=card_id))


def choose_player_card(hand):
    hand = [card for card in hand if is_monster(card)]
    if not hand:
        return None
    return sorted(
        hand,
        key=lambda card: (
            int(card.get("attack", 0)),
            ability_priority(card),
            int(card.get("guard", 0)),
            card["name"],
        ),
        reverse=True,
    )[0]


def _rotating_ids(pool, start, count):
    if not pool:
        return []
    return [pool[(start + offset) % len(pool)]["id"] for offset in range(count)]


def seasonal_balance_deck(index, *, side="player", profile_id=None):
    """Build a legal deterministic lab deck that rotates through Season 0.

    Production players keep their saved loadout. The balance lab needs broader
    coverage, otherwise a healthy engine can look like 60+ cards are dead just
    because fixed starter decks never draw them.
    """
    index = max(0, int(index or 0))
    side_offset = 0 if side == "bot" and profile_id == "defensive" else (7 if side == "bot" else 0)
    profile_offset = {"defensive": 0, "aggressive": 5, "opportunist": 11}.get(str(profile_id or ""), 3)
    seed = index * 3 + side_offset + profile_offset
    monster_pool = sorted(BASE_MONSTERS, key=lambda card: (card["family"], card["id"]))
    legendary_pool = sorted(LEGENDARY_CARDS, key=lambda card: (card["family"], card["id"]))
    spell_pool = sorted(SPELL_CARDS, key=lambda card: card["id"])
    trap_pool = sorted(TRAP_CARDS, key=lambda card: card["id"])

    duplicate_count = 6 if side == "bot" else 5
    monster_count = 22 if side == "bot" else 20
    support_count = (30 - monster_count) // 2
    legendary_ids = _rotating_ids(legendary_pool, seed + index, 1)
    base_monster_count = monster_count - len(legendary_ids)
    duplicate_count = min(duplicate_count, base_monster_count // 2)
    duplicate_bases = _rotating_ids(monster_pool, seed, duplicate_count)
    singles = [
        card_id
        for card_id in _rotating_ids(monster_pool, seed + duplicate_count, 18)
        if card_id not in set(duplicate_bases)
    ][: base_monster_count - (duplicate_count * 2)]
    monsters = []
    for card_id in duplicate_bases:
        monsters.extend([card_id, card_id])
    monsters.extend(singles)
    monsters.extend(legendary_ids)
    monsters = monsters[:monster_count]
    spells = _rotating_ids(spell_pool, seed + index, support_count)
    traps = _rotating_ids(trap_pool, seed + index, 30 - monster_count - support_count)
    deck = monsters + spells + traps
    validate_deck_distribution(deck)
    return deck


def card_cost(card):
    if is_monster(card):
        return max(1, min(10, int(card.get("cost") or card.get("tier") or 1)))
    return max(0, int(card.get("cost", 0) or 0))


def choose_player_evolution(match):
    options = available_evolutions(match["player"])
    if not options:
        return None
    catalog = {card["id"]: card for card in catalog_payload()}
    return sorted(
        options,
        key=lambda option: (
            int(catalog[option["evolution_id"]].get("attack", 0)),
            ability_priority(catalog[option["evolution_id"]]),
            int(catalog[option["evolution_id"]].get("guard", 0)),
        ),
    )[-1]


def projected_player_score(match, player_card):
    bot_profile_id = (match.get("bot_profile") or {}).get("id")
    bot_card = choose_response(
        match["bot"]["hand"],
        player_card,
        profile_id=bot_profile_id,
        turn=match.get("turn", 1),
        player_wounded=match["player"].get("wounded", False),
        bot_wounded=match["bot"].get("wounded", False),
        match_id=None,
    )
    if not bot_card:
        return 1000
    winner, clash = compare_clash(match, player_card, bot_card)
    player_damage = 0
    bot_damage = 0
    if winner == "player":
        player_damage = damage_details(player_card, bot_card, match["bot"].get("wounded", False))["amount"]
    elif winner == "bot":
        bot_damage = damage_details(bot_card, player_card, match["player"].get("wounded", False))["amount"]
    return (
        player_damage * 8
        - bot_damage * 8
        + (8 if winner == "player" else 0)
        - (8 if winner == "bot" else 0)
        + int(player_card.get("attack", 0))
        + ability_priority(player_card)
        + int(player_card.get("guard", 0)) * 0.25
        + int(clash["player_attack"]) * 0.5
    )


def choose_tactical_player_card(match):
    energy = int(match["player"].get("energy", 0) or 0)
    hand = [card for card in match["player"]["hand"] if is_monster(card) and card_cost(card) <= energy]
    if not hand:
        return None
    ranked = sorted(
        hand,
        key=lambda card: (projected_player_score(match, card), int(card.get("guard", 0)), card["name"]),
        reverse=True,
    )
    top_window = ranked[: min(3, len(ranked))]
    source = f"{match.get('match_id')}:{match.get('turn')}:{energy}:{len(match['player'].get('battlefield', []))}"
    index = int(hashlib.sha256(source.encode("utf-8")).hexdigest()[:2], 16) % len(top_window)
    return top_window[index]


def side_has_ready_attackers(side):
    return any(
        card
        and not card.get("exhausted")
        and not card.get("has_attacked")
        and not card.get("has_acted")
        for card in side.get("battlefield", [])
    )


def ready_attacker_count(side):
    return sum(
        1
        for card in side.get("battlefield", [])
        if card
        and not card.get("exhausted")
        and not card.get("has_attacked")
        and not card.get("has_acted")
    )


def side_has_breakable_shield(match, side_name):
    side = match[side_name]
    if "shield" in (side.get("statuses") or {}):
        return True
    return any(
        "aegis_sentinel_shield" in (card.get("statuses") or {})
        or int(card.get("current_guard", card.get("guard", 0)) or 0) > 0
        for card in side.get("battlefield", [])
    )


def support_card_score(match, side_name, card):
    if not (is_spell(card) or is_trap(card)):
        return -1
    side = match[side_name]
    energy = int(side.get("energy", 0) or 0)
    cost = card_cost(card)
    if cost > energy:
        return -1
    opponent_name = "bot" if side_name == "player" else "player"
    opponent = match[opponent_name]
    opponent_ready = side_has_ready_attackers(opponent)
    opponent_pressure = len(opponent.get("battlefield", []))
    side_hp = int(side.get("hp", 30) or 0)
    side_max_hp = int(side.get("max_hp", 30) or 30)
    opponent_hp = int(opponent.get("hp", 30) or 0)
    action = str(card.get("action") or "").lower()
    opponent_profile_id = (match.get("bot_profile") or {}).get("id") if side_name == "player" else None
    aggressive_pressure = opponent_profile_id == "aggressive"

    if is_trap(card):
        trap_limit = 1 if side_name == "player" else 2
        if len(side.get("traps") or []) >= trap_limit:
            return -1
        if side_name == "player":
            ready_count = ready_attacker_count(opponent)
            turn = int(match.get("turn", 1) or 1)
            under_pressure = side_hp <= side_max_hp - (5 if aggressive_pressure else 10)
            wide_board_pressure = ready_count >= 2 and turn >= (4 if aggressive_pressure else 6)
            if opponent_ready and (under_pressure or (wide_board_pressure and side_hp <= side_max_hp - (3 if aggressive_pressure else 5))):
                return 5 - cost
            if opponent_pressure >= 3 and turn >= 8:
                return 3 - cost
            return -1
        if opponent_ready:
            return 15 - cost
        if opponent_pressure and int(match.get("turn", 1) or 1) >= 2:
            return 12 - cost
        if int(match.get("turn", 1) or 1) >= 4:
            return 7 - cost
        return -1

    if action == "drawtwocards" and side.get("deck"):
        hand_size = len(side.get("hand") or [])
        turn = int(match.get("turn", 1) or 1)
        if hand_size <= 3:
            return 15 - cost
        if hand_size <= 5 and turn >= 3:
            return 11 - cost
        if hand_size <= 6 and turn >= 6:
            return 7 - cost
    if action in {"cleanseall", "tidalrenewal"} and side.get("statuses"):
        return 12 - cost
    if action == "destroyshield":
        return 13 - cost if side_has_breakable_shield(match, opponent_name) else -1
    if action in {"healingrain", "tidalrenewal"} and side_hp <= side_max_hp - (6 if aggressive_pressure else 7):
        return 12 - cost
    if (
        action in {"fortify", "stoneskin"}
        and "shield" not in (side.get("statuses") or {})
        and opponent_ready
        and side_hp <= (24 if aggressive_pressure else 22)
    ):
        return 11 - cost
    if action == "shadowdrain" and (side_hp <= side_max_hp - (7 if aggressive_pressure else 8) or opponent_hp <= (9 if aggressive_pressure else 7)):
        return 10 - cost
    if action == "fireball" and opponent_hp <= (14 if aggressive_pressure else 11):
        return 9 - cost
    if action == "burningedict" and opponent_pressure and "burn" not in (opponent.get("statuses") or {}):
        return 7 - cost
    return -1


def choose_tactical_support_card(match):
    scored = [
        (support_card_score(match, "player", card), card)
        for card in match["player"]["hand"]
        if is_spell(card) or is_trap(card)
    ]
    scored = [(score, card) for score, card in scored if score > 0]
    if not scored:
        return None
    best_score, best_card = sorted(scored, key=lambda item: (item[0], -card_cost(item[1]), item[1]["name"]))[-1]
    energy = int(match["player"].get("energy", 0) or 0)
    board_can_grow = len(match["player"].get("battlefield", [])) < FIELD_SLOT_COUNT
    has_ready_attack = choose_ready_attacker(match) is not None
    if board_can_grow and not has_ready_attack:
        trap_setup = (
            is_trap(best_card)
            and (len(match["bot"].get("battlefield", [])) > 0 or int(match.get("turn", 1) or 1) >= 2)
        )
        affordable_after_support = [
            card
            for card in match["player"]["hand"]
            if is_monster(card) and card_cost(card) <= energy - min(card_cost(item[1]) for item in scored)
        ]
        lethal_support = any(str(card.get("action") or "").lower() in {"fireball", "shadowdrain"} for _score, card in scored)
        if not trap_setup and not affordable_after_support and not lethal_support:
            return None
    return best_card


def choose_ready_attacker(match):
    ready = [
        card
        for card in match["player"].get("battlefield", [])
        if not card.get("exhausted")
        and not card.get("has_attacked")
        and not card.get("has_acted")
        # O jogador simulado respeita summoning sickness como um humano.
        and not (card.get("just_summoned") and "RUSH" not in (card.get("keywords") or []))
    ]
    if not ready:
        return None
    return sorted(
        ready,
        key=lambda card: (
            int(card.get("attack", card.get("power", 0)) or 0),
            ability_priority(card),
            int(card.get("current_guard", card.get("guard", 0)) or 0),
            card["name"],
        ),
    )[-1]


def choose_bot_target(match, attacker=None):
    candidates = match["bot"].get("battlefield") or []
    if not candidates:
        return None
    # Provocar obriga o alvo — o jogador simulado respeita TAUNT.
    taunts = [card for card in candidates if "TAUNT" in (card.get("keywords") or [])]
    pool = taunts or candidates
    attack_value = int((attacker or {}).get("attack", (attacker or {}).get("power", 0)) or 0)
    if attacker and not taunts:
        # Targeting de jogador de verdade: remove a maior ameaça que o golpe
        # MATA; sem kill disponível, vai de dano direto (chip no herói).
        killable = [
            card for card in pool
            if int(card.get("current_guard", card.get("guard", 0)) or 0) <= max(1, attack_value - int(card.get("guard", 0) or 0) // 2)
        ]
        if killable:
            return sorted(
                killable,
                key=lambda field_card: (
                    -int(field_card.get("attack", field_card.get("power", 0)) or 0),
                    int(field_card.get("current_guard", field_card.get("guard", 0)) or 0),
                    field_card["name"],
                ),
            )[0]
        return None
    return sorted(
        pool,
        key=lambda field_card: (
            int(field_card.get("current_guard", field_card.get("guard", 0)) or 0),
            -int(field_card.get("attack", field_card.get("power", 0)) or 0),
            field_card["name"],
        ),
    )[0]


def declare_best_attack(match, attacker):
    target = choose_bot_target(match, attacker)
    if target is None and int(match.get("turn", 1) or 1) == 1:
        return None
    try:
        return declare_attack(
            match,
            attacker_instance_id=attacker["instance_id"],
            target_instance_id=target["instance_id"] if target else None,
        )
    except RebirthError:
        # Alvo morreu na cadeia anterior / taunt apareceu: o turno segue.
        return None


def simulate_match(seed=None, max_turns=30, bot_profile_id=None, player_card_ids=None, bot_card_ids=None):
    match = start_match(
        seed=seed,
        bot_profile_id=bot_profile_id,
        player_card_ids=player_card_ids,
        bot_card_ids=bot_card_ids,
    )
    card_usage = Counter()
    card_wins = Counter()
    card_damage = Counter()
    card_match_uses = Counter()
    ability_usage = Counter()
    ability_wins = Counter()
    ability_damage = Counter()
    ability_match_uses = Counter()
    ability_events = Counter()
    evolution_usage = Counter()
    first_turn_cards = Counter()
    first_turn_wins = Counter()
    turns = 0
    dead_turns = 0
    while not match.get("is_finished") and turns < max_turns:
        turn_event_start = len(match.get("events") or [])
        evolution = choose_player_evolution(match)
        if evolution:
            evolved = evolve_duplicate(match, evolution["card_id"])
            evolution_usage[evolved["id"]] += 1
        support_card = choose_tactical_support_card(match)
        if support_card:
            try:
                play_card(match, card_instance_id=support_card["instance_id"])
            except RebirthError:
                pass
            if match.get("is_finished"):
                break
        # Ataques primeiro: com summoning sickness, os corpos prontos batem
        # antes de gastar mana — o mesmo loop de um jogador humano.
        for _attack_round in range(FIELD_SLOT_COUNT):
            pre_attacker = choose_ready_attacker(match)
            if not pre_attacker or match.get("is_finished"):
                break
            declare_best_attack(match, pre_attacker)
        if match.get("is_finished"):
            break
        # Desenvolvimento: gasta a mana do turno como um humano (até 3 jogadas),
        # em vez de uma única carta por turno.
        played_anything = False
        for _play_round in range(FIELD_SLOT_COUNT):
            card = choose_tactical_player_card(match)
            if not card:
                # Fallback anti-turno-morto: a reserva tática pode segurar
                # demais; com slot e mana, baixar o monstro mais barato é
                # estritamente melhor que passar.
                energy = int(match["player"].get("energy", 0) or 0)
                field_full = len(match["player"].get("battlefield", [])) >= FIELD_SLOT_COUNT
                open_slot = not field_full
                fallback = sorted(
                    (
                        hand_card
                        for hand_card in match["player"].get("hand", [])
                        if is_monster(hand_card) and card_cost(hand_card) <= energy
                    ),
                    key=lambda hand_card: (card_cost(hand_card), -int(hand_card.get("attack", 0) or 0)),
                )
                card = fallback[0] if (fallback and open_slot) else None
            if not card:
                break
            try:
                play_card(match, card_instance_id=card["instance_id"])
                played_anything = True
            except RebirthError:
                break
            if match.get("is_finished"):
                break
        if match.get("is_finished"):
            break
        # RUSH recém-invocado ainda pode bater neste turno.
        rush_attacker = next(
            (
                field_card
                for field_card in match["player"].get("battlefield", [])
                if "RUSH" in (field_card.get("keywords") or [])
                and not field_card.get("exhausted")
                and not field_card.get("has_attacked")
                and not field_card.get("has_acted")
            ),
            None,
        )
        if rush_attacker:
            declare_best_attack(match, rush_attacker)
            played_anything = True
        if not played_anything and not choose_ready_attacker(match):
            if match.get("phase") in {"choose", "result"}:
                dead_turns += 1
                next_turn(match)
                turns += 1
                continue
            break
        clash = match.get("last_clash") or {}
        result = match.get("result") or {}
        played_cards = [
            ("player", clash.get("player_card"), int((result.get("damage") or {}).get("bot", 0) or 0)),
            ("bot", clash.get("bot_card"), int((result.get("damage") or {}).get("player", 0) or 0)),
        ]
        winner = result.get("winner")
        for side, played_card, damage in played_cards:
            if not played_card:
                continue
            card_id = played_card["id"]
            key = played_card.get("ability_key") or "none"
            card_usage[card_id] += 1
            card_damage[card_id] += damage
            ability_usage[key] += 1
            ability_damage[key] += damage
            if winner == side:
                card_wins[card_id] += 1
                ability_wins[key] += 1
            if turns == 0:
                first_turn_cards[card_id] += 1
                if winner == side:
                    first_turn_wins[card_id] += 1
        for event in result.get("ability_events") or []:
            ability_events[str(event)] += 1
        turn_event_types = {
            event.get("event_type") or event.get("type")
            for event in (match.get("events") or [])[turn_event_start:]
        }
        if not turn_event_types.intersection({"ATTACK_DECLARED", "DAMAGE_RESOLVED", "TRAP_TRIGGERED", "UNIT_DESTROYED"}):
            dead_turns += 1
        turns += 1
        if not match.get("is_finished"):
            next_turn(match)

    events = match.get("events") or []
    catalog = {card["id"]: card for card in catalog_payload()}
    card_usage = Counter()
    card_wins = Counter()
    card_damage = Counter()
    card_match_uses = Counter()
    ability_usage = Counter()
    ability_wins = Counter()
    ability_damage = Counter()
    ability_match_uses = Counter()
    evolution_usage = Counter()
    first_turn_cards = Counter()
    first_turn_wins = Counter()
    played_by_side = defaultdict(set)
    abilities_by_side = defaultdict(set)
    first_turn_by_side = defaultdict(set)

    for event in events:
        event_type = event.get("event_type") or event.get("type")
        actor = event.get("actor")
        payload = event.get("payload") or {}
        card_id = None
        if event_type == "CARD_PLAYED":
            card_id = payload.get("card_id") or event.get("source_card_id")
        elif event_type == "TRAP_ARMED":
            card_id = payload.get("card_id") or event.get("source_card_id")
        elif event_type == "CARD_EVOLVED":
            card_id = payload.get("evolution_id")
            if card_id:
                evolution_usage[card_id] += 1
        if card_id and card_id in catalog and actor in {"player", "bot"}:
            key = catalog[card_id].get("ability_key") or "none"
            card_usage[card_id] += 1
            ability_usage[key] += 1
            played_by_side[actor].add(card_id)
            abilities_by_side[actor].add(key)
            if int(event.get("turn", 0) or 0) == 1:
                first_turn_cards[card_id] += 1
                first_turn_by_side[actor].add(card_id)

        if event_type == "DAMAGE_RESOLVED":
            source_id = event.get("source_card_id")
            if source_id and source_id in catalog:
                damage_payload = payload or {}
                amount = int(damage_payload.get("amount", 0) or 0)
                amount += int(damage_payload.get("player", 0) or 0)
                amount += int(damage_payload.get("bot", 0) or 0)
                hero_damage = damage_payload.get("hero_damage") or {}
                if isinstance(hero_damage, dict):
                    amount += int(hero_damage.get("player", 0) or 0)
                    amount += int(hero_damage.get("bot", 0) or 0)
                card_damage[source_id] += amount
                ability_damage[catalog[source_id].get("ability_key") or "none"] += amount

    winner_side = match.get("winner")
    for side_name, card_ids in played_by_side.items():
        for card_id in card_ids:
            card_match_uses[card_id] += 1
            if side_name == winner_side:
                card_wins[card_id] += 1
    for side_name, ability_keys in abilities_by_side.items():
        for ability_key in ability_keys:
            ability_match_uses[ability_key] += 1
            if side_name == winner_side:
                ability_wins[ability_key] += 1
    for card_id in first_turn_by_side.get(winner_side, set()):
        first_turn_wins[card_id] += 1

    routine_turn_events = {
        "TURN_ENDED",
        "PLAYED_CARDS_CLEARED",
        "TURN_STATUS_TICKED",
        "CARDS_DRAWN",
        "UNITS_READIED",
        "ENERGY_REFRESHED",
        "TURN_STARTED",
    }
    chains = Counter(
        event.get("effect_chain_id")
        for event in events
        if event.get("effect_chain_id") and (event.get("event_type") or event.get("type")) not in routine_turn_events
    )
    destroyed_by_chain = Counter(
        event.get("effect_chain_id")
        for event in events
        if (event.get("event_type") or event.get("type")) == "UNIT_DESTROYED"
    )
    trigger_events = sum(
        1
        for event in events
        if (event.get("event_type") or event.get("type")) in {"ABILITY_TRIGGERED", "EFFECT_RESOLVED", "TRAP_TRIGGERED", "STATUS_APPLIED"}
    )
    return {
        "winner": match.get("winner") or "unfinished",
        "turns": turns,
        "player_hp": match["player"]["hp"],
        "bot_hp": match["bot"]["hp"],
        "bot_profile": match.get("bot_profile") or {},
        "card_usage": dict(card_usage),
        "card_wins": dict(card_wins),
        "card_damage": dict(card_damage),
        "ability_usage": dict(ability_usage),
        "ability_wins": dict(ability_wins),
        "ability_damage": dict(ability_damage),
        "card_match_uses": dict(card_match_uses),
        "ability_match_uses": dict(ability_match_uses),
        "ability_events": dict(ability_events),
        "evolution_usage": dict(evolution_usage),
        "first_turn_cards": dict(first_turn_cards),
        "first_turn_wins": dict(first_turn_wins),
        "dead_cards": dict(Counter(card["id"] for card in match["player"]["hand"])),
        "dead_turns": dead_turns,
        "event_count": len(events),
        "trigger_events": trigger_events,
        "max_chain_events": max(chains.values()) if chains else 0,
        "symmetric_destroy_chains": sum(1 for count in destroyed_by_chain.values() if count > 1),
        "lethal": bool(match.get("is_finished")),
        "stalemate": not bool(match.get("is_finished")),
    }


def _simulate_balance_core(matches=40, *, seed_prefix="balance", max_turns=30):
    matches = max(1, int(matches or 40))
    winners = Counter()
    card_usage = Counter()
    card_wins = Counter()
    card_damage = Counter()
    card_match_uses = Counter()
    ability_usage = Counter()
    ability_wins = Counter()
    ability_damage = Counter()
    ability_match_uses = Counter()
    evolution_usage = Counter()
    first_turn_cards = Counter()
    first_turn_wins = Counter()
    dead_cards = Counter()
    profile_winners = defaultdict(Counter)
    profile_turns = Counter()
    profile_matches = Counter()
    ability_events = Counter()
    total_turns = 0
    total_dead_turns = 0
    total_events = 0
    total_trigger_events = 0
    total_symmetric_destroy_chains = 0
    lethal_matches = 0
    max_chain_events = 0
    samples = []
    for index in range(matches):
        profile_id = BOT_PERSONALITY_ORDER[index % len(BOT_PERSONALITY_ORDER)]
        result = simulate_match(
            seed=f"{seed_prefix}-{index}",
            max_turns=max_turns,
            bot_profile_id=profile_id,
            player_card_ids=seasonal_balance_deck(index, side="player", profile_id=profile_id),
            bot_card_ids=seasonal_balance_deck(index, side="bot", profile_id=profile_id),
        )
        winners[result["winner"]] += 1
        card_usage.update(result["card_usage"])
        card_wins.update(result["card_wins"])
        card_damage.update(result["card_damage"])
        card_match_uses.update(result.get("card_match_uses") or {})
        ability_usage.update(result["ability_usage"])
        ability_wins.update(result["ability_wins"])
        ability_damage.update(result["ability_damage"])
        ability_match_uses.update(result.get("ability_match_uses") or {})
        evolution_usage.update(result["evolution_usage"])
        first_turn_cards.update(result["first_turn_cards"])
        first_turn_wins.update(result["first_turn_wins"])
        dead_cards.update(result["dead_cards"])
        ability_events.update(result["ability_events"])
        total_turns += result["turns"]
        total_dead_turns += result["dead_turns"]
        total_events += result["event_count"]
        total_trigger_events += result["trigger_events"]
        total_symmetric_destroy_chains += result["symmetric_destroy_chains"]
        lethal_matches += int(result["lethal"])
        max_chain_events = max(max_chain_events, result["max_chain_events"])
        profile_winners[profile_id][result["winner"]] += 1
        profile_turns[profile_id] += result["turns"]
        profile_matches[profile_id] += 1
        if index < 5:
            samples.append(result)

    player_wins = winners.get("player", 0)
    bot_wins = winners.get("bot", 0)
    catalog = {card["id"]: card for card in catalog_payload()}
    card_stats = []
    for card_id, card in sorted(catalog.items(), key=lambda item: (item[1]["family"], item[1]["tier"], item[1]["name"])):
        plays = card_usage.get(card_id, 0)
        match_uses = card_match_uses.get(card_id, 0)
        wins = card_wins.get(card_id, 0)
        damage = card_damage.get(card_id, 0)
        first_turns = first_turn_cards.get(card_id, 0)
        card_stats.append(
            {
                "card_id": card_id,
                "name": card["name"],
                "ability_key": card["ability_key"],
                "plays": plays,
                "match_uses": match_uses,
                "pick_rate": round(match_uses / max(1, matches * 2), 3),
                "wins": wins,
                "win_rate": round(wins / match_uses, 3) if match_uses else 0,
                "total_damage": damage,
                "avg_damage": round(damage / plays, 2) if plays else 0,
                "evolve_rate": round(evolution_usage.get(card_id, 0) / matches, 3),
                "dead_card_rate": round(dead_cards.get(card_id, 0) / matches, 3),
                "first_turn_impact": round(first_turn_wins.get(card_id, 0) / first_turns, 3) if first_turns else 0,
                "flags": balance_flags(
                    plays,
                    match_uses,
                    wins,
                    damage,
                    matches,
                    dead_cards.get(card_id, 0),
                    evolution_usage.get(card_id, 0),
                ),
            }
        )
    ability_stats = []
    ability_labels = {card["ability_key"]: card["ability_name"] for card in catalog.values()}
    for key, plays in ability_usage.most_common():
        match_uses = ability_match_uses.get(key, 0)
        wins = ability_wins.get(key, 0)
        damage = ability_damage.get(key, 0)
        ability_stats.append(
            {
                "ability_key": key,
                "name": ability_labels.get(key, key.replace("_", " ").title()),
                "plays": plays,
                "match_uses": match_uses,
                "wins": wins,
                "win_rate": round(wins / match_uses, 3) if match_uses else 0,
                "total_damage": damage,
                "avg_damage": round(damage / plays, 2) if plays else 0,
            }
        )
    profile_results = []
    for profile_id in BOT_PERSONALITY_ORDER:
        count = profile_matches.get(profile_id, 0)
        profile = BOT_PERSONALITIES[profile_id]
        profile_results.append(
            {
                "profile_id": profile_id,
                "name": profile["name"],
                "matches": count,
                "player_win_rate": round(profile_winners[profile_id].get("player", 0) / count, 3) if count else 0,
                "bot_win_rate": round(profile_winners[profile_id].get("bot", 0) / count, 3) if count else 0,
                "average_turns": round(profile_turns[profile_id] / count, 2) if count else 0,
            }
        )
    return {
        "matches": matches,
        "seed_prefix": seed_prefix,
        "summary": {
            "player_win_rate": round(player_wins / matches, 3),
            "bot_win_rate": round(bot_wins / matches, 3),
            "unfinished_rate": round(winners.get("unfinished", 0) / matches, 3),
            "average_turns": round(total_turns / matches, 2),
            "lethal_frequency": round(lethal_matches / matches, 3),
            "dead_turn_rate": round(total_dead_turns / max(1, total_turns), 3),
            "stalemate_frequency": round(winners.get("unfinished", 0) / matches, 3),
            "events_per_turn": round(total_events / max(1, total_turns), 2),
            "trigger_events_per_turn": round(total_trigger_events / max(1, total_turns), 2),
            "symmetric_destroy_chains_per_match": round(total_symmetric_destroy_chains / matches, 2),
            "max_chain_events": max_chain_events,
        },
        "winners": dict(winners),
        "most_used_cards": [{"card_id": card_id, "plays": plays} for card_id, plays in card_usage.most_common(8)],
        "card_stats": card_stats,
        "ability_stats": ability_stats,
        "profile_results": profile_results,
        "top_ability_events": [
            {"event": event, "count": count}
            for event, count in ability_events.most_common(6)
        ],
        "evolution_usage": [{"card_id": card_id, "count": count} for card_id, count in evolution_usage.most_common()],
        "samples": samples,
        "bot_tuning": {
            "policy": "alterna perfis defensivo, agressivo e oportunista; o jogador evolui duplicatas e escolhe linhas táticas projetadas",
            "status": "season 0 parity lab",
        },
    }


def simulate_balance(matches=40):
    return _simulate_balance_core(matches=max(1, min(int(matches or 40), 200)), seed_prefix="balance")


def simulate_controlled_balance(matches=1000, *, seed_prefix="controlled-balance", max_turns=30):
    return _simulate_balance_core(
        matches=max(1, min(int(matches or 1000), 5000)),
        seed_prefix=seed_prefix,
        max_turns=max(1, min(int(max_turns or 30), 120)),
    )


def balance_flags(plays, match_uses, wins, damage, matches, dead_count, evolve_count):
    flags = []
    if not plays:
        flags.append("unused")
    elif plays >= max(3, matches * 0.2) and match_uses >= max(8, matches * 0.18):
        win_rate = wins / max(1, match_uses)
        avg_damage = damage / plays
        if win_rate >= 0.78 and avg_damage >= 1.5:
            flags.append("dominant")
        if win_rate <= 0.2 and avg_damage <= 0.75:
            flags.append("low-impact")
    if dead_count >= matches * 0.4:
        flags.append("dead-hand-risk")
    if evolve_count >= matches * 0.5:
        flags.append("evolution-core")
    return flags


# ---------------------------------------------------------------------------
# Lab CASUAL (auditoria olhos-de-jogador, 2026-06-11)
#
# O lab tático acima joga otimizado (kill-targeting, reserva de mana,
# evolução). Um humano casual não faz nada disso — e era a diferença entre o
# WR 0.47 reportado e a impotência real vista em partidas de verdade. Este
# simulador joga como um novato: monstros na ordem da mão, ataca o primeiro
# alvo vivo (ou o herói), nunca lê trade. As metas de saúde do produto valem
# para ELE: WR 0.40-0.60 e board presence >= 1.0.
# ---------------------------------------------------------------------------

def simulate_casual_match(seed=None, max_turns=30, bot_profile_id=None):
    match = start_match(seed=seed, bot_profile_id=bot_profile_id)
    turns = 0
    board_samples = []
    while not match.get("is_finished") and turns < max_turns:
        # 1) ataca com todos os prontos, no alvo mais óbvio (primeiro slot vivo)
        for _ in range(FIELD_SLOT_COUNT):
            ready = next(
                (
                    card
                    for card in match["player"].get("battlefield", [])
                    if not card.get("exhausted")
                    and not card.get("has_attacked")
                    and not card.get("has_acted")
                    and not (card.get("just_summoned") and "RUSH" not in (card.get("keywords") or []))
                ),
                None,
            )
            if not ready or match.get("is_finished"):
                break
            # Alvo de humano casual: a unidade mais machucada que ele vê
            # (sem projeção de trade); com campo vazio, vai direto.
            field = match["bot"].get("battlefield", []) or []
            enemy = min(
                field,
                key=lambda c: int(c.get("current_guard", c.get("guard", 0)) or 0),
            ) if field else None
            try:
                declare_attack(
                    match,
                    attacker_instance_id=ready["instance_id"],
                    target_instance_id=(enemy or {}).get("instance_id"),
                )
            except RebirthError:
                break
        if match.get("is_finished"):
            break
        # 2) invoca até 2 monstros pagáveis, na ordem da mão (sem otimizar)
        for _ in range(2):
            energy = int(match["player"].get("energy", 0) or 0)
            slot_free = len(match["player"].get("battlefield", [])) < FIELD_SLOT_COUNT
            card = next(
                (
                    hand_card
                    for hand_card in match["player"].get("hand", [])
                    if is_monster(hand_card) and card_cost(hand_card) <= energy
                ),
                None,
            )
            if not card or not slot_free or match.get("is_finished"):
                break
            try:
                play_card(match, card_instance_id=card["instance_id"])
            except RebirthError:
                break
        if match.get("is_finished"):
            break
        # 2b) humano casual joga a magia que couber (o botão brilha, ele
        # aperta) mirando a unidade inimiga mais machucada.
        energy = int(match["player"].get("energy", 0) or 0)
        spell = next(
            (
                hand_card
                for hand_card in match["player"].get("hand", [])
                if is_spell(hand_card) and card_cost(hand_card) <= energy
            ),
            None,
        )
        if spell:
            bot_field = match["bot"].get("battlefield", []) or []
            weakest = min(
                bot_field,
                key=lambda c: int(c.get("current_guard", c.get("guard", 0)) or 0),
            ) if bot_field else None
            try:
                play_card(
                    match,
                    card_instance_id=spell["instance_id"],
                    target_instance_id=(weakest or {}).get("instance_id"),
                )
            except RebirthError:
                try:
                    play_card(match, card_instance_id=spell["instance_id"])
                except RebirthError:
                    pass
        if match.get("is_finished"):
            break
        # 3) presença de board no fim do MEU turno (antes do bot agir)
        board_samples.append(len(match["player"].get("battlefield", [])))
        turns += 1
        next_turn(match)

    return {
        "winner": match.get("winner") or ("unfinished" if not match.get("is_finished") else "draw"),
        "turns": turns,
        "board_presence": round(sum(board_samples) / len(board_samples), 3) if board_samples else 0.0,
        "final_player_units": len(match["player"].get("battlefield", [])),
    }


def simulate_casual_balance(matches=120, *, seed_prefix="casual"):
    matches = max(1, min(int(matches or 120), 1000))
    winners = Counter()
    profile_winners = defaultdict(Counter)
    profile_matches = Counter()
    profile_presence = defaultdict(list)
    total_turns = 0
    presence = []
    for index in range(matches):
        profile_id = BOT_PERSONALITY_ORDER[index % len(BOT_PERSONALITY_ORDER)]
        result = simulate_casual_match(seed=f"{seed_prefix}-{index}", bot_profile_id=profile_id)
        winners[result["winner"]] += 1
        profile_winners[profile_id][result["winner"]] += 1
        profile_matches[profile_id] += 1
        profile_presence[profile_id].append(result["board_presence"])
        presence.append(result["board_presence"])
        total_turns += result["turns"]
    profile_results = []
    for profile_id in BOT_PERSONALITY_ORDER:
        count = profile_matches.get(profile_id, 0)
        wins = profile_winners[profile_id]
        samples = profile_presence.get(profile_id) or [0]
        profile_results.append(
            {
                "profile_id": profile_id,
                "player_win_rate": round(wins.get("player", 0) / count, 3) if count else 0,
                "board_presence": round(sum(samples) / len(samples), 3),
            }
        )
    return {
        "matches": matches,
        "summary": {
            "player_win_rate": round(winners.get("player", 0) / matches, 3),
            "bot_win_rate": round(winners.get("bot", 0) / matches, 3),
            "unfinished_rate": round(winners.get("unfinished", 0) / matches, 3),
            "average_turns": round(total_turns / matches, 2),
            "board_presence": round(sum(presence) / len(presence), 3) if presence else 0.0,
        },
        "profile_results": profile_results,
    }

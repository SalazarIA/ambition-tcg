from collections import Counter, defaultdict

from services.rebirth_bot import BOT_PERSONALITY_ORDER, BOT_PERSONALITIES
from services.rebirth_cards import catalog_payload, is_monster, is_spell, is_trap
from services.rebirth_contracts import FIELD_SLOT_COUNT, RebirthError
from services.rebirth_engine import (
    compare_clash,
    declare_attack,
    damage_details,
    evolve_duplicate,
    next_turn,
    play_card,
    start_match,
)
from services.rebirth_state import available_evolutions
from services.rebirth_bot import ability_priority, choose_response


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
    return sorted(
        hand,
        key=lambda card: (projected_player_score(match, card), int(card.get("guard", 0)), card["name"]),
    )[-1]


def side_has_ready_attackers(side):
    return any(
        card
        and not card.get("exhausted")
        and not card.get("has_attacked")
        and not card.get("has_acted")
        for card in side.get("battlefield", [])
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
        if len(side.get("traps") or []) >= 2:
            return -1
        if opponent_ready:
            return 13 - cost
        if opponent_pressure and int(match.get("turn", 1) or 1) >= 3:
            return 8 - cost
        return -1

    if action == "drawtwocards" and len(side.get("hand") or []) <= 3 and side.get("deck"):
        return 10 - cost
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
    if action == "fireball" and opponent_hp <= (8 if aggressive_pressure else 6):
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
    energy = int(match["player"].get("energy", 0) or 0)
    board_can_grow = len(match["player"].get("battlefield", [])) < FIELD_SLOT_COUNT
    has_ready_attack = choose_ready_attacker(match) is not None
    if board_can_grow and not has_ready_attack:
        affordable_after_support = [
            card
            for card in match["player"]["hand"]
            if is_monster(card) and card_cost(card) <= energy - min(card_cost(item[1]) for item in scored)
        ]
        lethal_support = any(str(card.get("action") or "").lower() in {"fireball", "shadowdrain"} for _score, card in scored)
        if not affordable_after_support and not lethal_support:
            return None
    return sorted(scored, key=lambda item: (item[0], -card_cost(item[1]), item[1]["name"]))[-1][1]


def choose_ready_attacker(match):
    ready = [
        card
        for card in match["player"].get("battlefield", [])
        if not card.get("exhausted") and not card.get("has_attacked") and not card.get("has_acted")
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


def choose_bot_target(match):
    if not match["bot"].get("battlefield"):
        return None
    return sorted(
        match["bot"]["battlefield"],
        key=lambda field_card: (
            int(field_card.get("current_guard", field_card.get("guard", 0)) or 0),
            -int(field_card.get("attack", field_card.get("power", 0)) or 0),
            field_card["name"],
        ),
    )[0]


def declare_best_attack(match, attacker):
    target = choose_bot_target(match)
    if target is None and int(match.get("turn", 1) or 1) == 1:
        return None
    return declare_attack(
        match,
        attacker_instance_id=attacker["instance_id"],
        target_instance_id=target["instance_id"] if target else None,
    )


def simulate_match(seed=None, max_turns=30, bot_profile_id=None):
    match = start_match(seed=seed, bot_profile_id=bot_profile_id)
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
        field_full = len(match["player"].get("battlefield", [])) >= FIELD_SLOT_COUNT
        ready_attacker = choose_ready_attacker(match)
        if field_full and ready_attacker:
            declare_best_attack(match, ready_attacker)
        else:
            card = choose_tactical_player_card(match)
            if not card:
                if ready_attacker:
                    declare_best_attack(match, ready_attacker)
                elif match.get("phase") in {"choose", "result"}:
                    dead_turns += 1
                    next_turn(match)
                    turns += 1
                    continue
                else:
                    break
            else:
                play_card(match, card_instance_id=card["instance_id"])
                if not match.get("is_finished"):
                    attacker = next(
                        (
                            field_card
                            for field_card in match["player"].get("battlefield", [])
                            if field_card.get("instance_id") == card["instance_id"]
                            and not field_card.get("exhausted")
                            and not field_card.get("has_attacked")
                        ),
                        None,
                    )
                    if attacker:
                        declare_best_attack(match, attacker)
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


def simulate_balance(matches=40):
    matches = max(1, min(int(matches or 40), 200))
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
        result = simulate_match(seed=f"balance-{index}", bot_profile_id=profile_id)
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


def balance_flags(plays, match_uses, wins, damage, matches, dead_count, evolve_count):
    flags = []
    if not plays:
        flags.append("unused")
    elif plays >= max(3, matches * 0.2):
        win_rate = wins / max(1, match_uses)
        avg_damage = damage / plays
        if win_rate >= 0.7:
            flags.append("dominant")
        if win_rate <= 0.25 and avg_damage <= 1:
            flags.append("low-impact")
    if dead_count >= matches * 0.4:
        flags.append("dead-hand-risk")
    if evolve_count >= matches * 0.5:
        flags.append("evolution-core")
    return flags

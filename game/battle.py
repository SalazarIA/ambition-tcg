from game.deck import draw_card
from game.balance import (
    CLASH_MIN_DAMAGE,
    CLASH_MIN_NET_DAMAGE,
    CLASH_NET_TEMPO_DAMAGE_PER_ROUND,
    CLASH_NET_TEMPO_MAX_BONUS,
    CLASH_TEMPO_DAMAGE_PER_ROUND,
    CLASH_TEMPO_MAX_BONUS,
    CLASH_TEMPO_START_ROUND,
    DUEL_STORM_DAMAGE,
    DUEL_STORM_DAMAGE_PER_ROUND,
    DUEL_STORM_MAX_DAMAGE,
    DUEL_STORM_START_ROUND,
)
from game.engine import add_ambition, resolve_manual_unleash
from game.rules import (
    apply_damage,
    apply_spell,
    apply_summon_effect,
    apply_trap,
    calculate_final_power,
    elemental_log,
    energy_for_round,
    has_elemental_advantage,
    piercing_bonus_damage,
    reset_player_energy,
)
from game.sigils import (
    apply_sigil_ambition_bonus,
    calculate_sigil_damage_bonus,
    calculate_sigil_damage_reduction,
    calculate_sigil_power_bonus,
)
from game.state import get_intent_rule, reset_round_flags


def apply_intent_damage_modifier(defender, damage, logs):
    rule = get_intent_rule(defender)

    reduction = int(rule.get("damage_reduction", 0))

    if reduction > 0 and damage > 0:
        blocked = min(reduction, damage)
        damage -= blocked
        logs.append(f"{defender['name']} used Guard and blocked {blocked} damage.")

    return max(0, damage)


def apply_strike_loss_penalty(defender, damage, logs):
    rule = get_intent_rule(defender)

    extra = int(rule.get("lose_extra_damage", 0))

    if extra > 0 and damage > 0:
        damage += extra
        logs.append(f"{defender['name']} used Strike but lost the clash: +{extra} extra damage received.")

    return damage


def strike_win_bonus(player, logs):
    rule = get_intent_rule(player)
    bonus = int(rule.get("win_power_bonus", 0))

    if bonus > 0:
        logs.append(f"{player['name']} used Strike and committed to aggression: +{bonus} clash power.")

    return bonus


def clash_damage_floor(round_number):
    round_number = max(1, int(round_number or 1))
    bonus_rounds = max(0, round_number - CLASH_TEMPO_START_ROUND + 1)
    tempo_bonus = min(CLASH_TEMPO_MAX_BONUS, bonus_rounds * CLASH_TEMPO_DAMAGE_PER_ROUND)

    return CLASH_MIN_DAMAGE + tempo_bonus


def clash_net_damage_floor(round_number):
    round_number = max(1, int(round_number or 1))
    bonus_rounds = max(0, round_number - CLASH_TEMPO_START_ROUND + 1)
    tempo_bonus = min(CLASH_NET_TEMPO_MAX_BONUS, bonus_rounds * CLASH_NET_TEMPO_DAMAGE_PER_ROUND)

    return CLASH_MIN_NET_DAMAGE + tempo_bonus


def duel_storm_damage(round_number):
    round_number = max(1, int(round_number or 1))

    if round_number < DUEL_STORM_START_ROUND:
        return 0

    bonus_rounds = round_number - DUEL_STORM_START_ROUND
    storm_damage = DUEL_STORM_DAMAGE + (bonus_rounds * DUEL_STORM_DAMAGE_PER_ROUND)

    return min(DUEL_STORM_MAX_DAMAGE, storm_damage)


def apply_clash_pressure(raw_damage, match, logs):
    damage_floor = clash_damage_floor(match.get("round", 1))

    if 0 < raw_damage < damage_floor:
        logs.append(f"Duel pressure raised clash damage from {raw_damage} to {damage_floor}.")
        return damage_floor

    return raw_damage


def apply_duel_storm_pressure(match, logs):
    damage = duel_storm_damage(match.get("round", 1))

    if damage <= 0:
        return

    p1_damage = apply_damage(match["p1"], damage)
    p2_damage = apply_damage(match["p2"], damage)

    logs.append(
        "Ambition Storm pressured the duel: "
        f"{match['p1']['name']} took {p1_damage} damage and "
        f"{match['p2']['name']} took {p2_damage} damage."
    )


def apply_focus_survival(player, logs):
    rule = get_intent_rule(player)
    ambition_gain = int(rule.get("survive_ambition", 0))

    if ambition_gain > 0 and player["hp"] > 0:
        add_ambition(player, ambition_gain, "stayed composed with Focus", logs)


def apply_damage_package(attacker, defender, attacker_monster, defender_monster, raw_damage, logs, minimum_damage=0):
    raw_damage += calculate_sigil_damage_bonus(attacker, attacker_monster, defender_monster, logs)

    raw_damage = apply_strike_loss_penalty(defender, raw_damage, logs)
    raw_damage = apply_intent_damage_modifier(defender, raw_damage, logs)

    sigil_reduction = calculate_sigil_damage_reduction(
        defender,
        defender_monster,
        attacker_monster,
        raw_damage,
        logs,
    )

    raw_damage = max(0, raw_damage - sigil_reduction)

    if 0 < raw_damage < minimum_damage:
        logs.append(f"Duel pressure pushed final damage from {raw_damage} to {minimum_damage}.")
        raw_damage = minimum_damage

    return apply_damage(defender, raw_damage)


def _card_label(card):
    if not card:
        return None

    return card.get("name") or card.get("title") or "Unknown Card"


def _player_snapshot(player):
    return {
        "name": player.get("name", "Player"),
        "hp": int(player.get("hp", 0)),
        "energy": int(player.get("energy", 0)),
        "ambition": int(player.get("ambition", 0)),
        "intent": player.get("intent", "Strike"),
        "field_m": player.get("field_m"),
        "field_st": player.get("field_st"),
        "hand_count": len(player.get("hand", [])),
        "graveyard_count": len(player.get("graveyard", [])),
    }


def _battle_snapshot(match):
    return {
        "round": int(match.get("round", 1)),
        "p1": _player_snapshot(match["p1"]),
        "p2": _player_snapshot(match["p2"]),
    }


def _append_player_change_events(events, before_player, after_player, side, target):
    before_hp = int(before_player.get("hp", 0))
    after_hp = int(after_player.get("hp", 0))

    if after_hp < before_hp:
        events.append({"type": "damage_dealt", "to": target, "amount": before_hp - after_hp})

    if after_hp != before_hp:
        events.append({"type": "hp_changed", "side": side, "value": after_hp})

    before_ambition = int(before_player.get("ambition", 0))
    after_ambition = int(after_player.get("ambition", 0))

    if after_ambition > before_ambition:
        events.append({"type": "ambition_gained", "side": side, "amount": after_ambition - before_ambition})

    if after_ambition != before_ambition:
        events.append({"type": "ambition_changed", "side": side, "value": after_ambition})

    after_energy = int(after_player.get("energy", 0))

    if after_energy != int(before_player.get("energy", 0)):
        events.append({"type": "energy_changed", "side": side, "value": after_energy})

    if len(after_player.get("hand", [])) > int(before_player.get("hand_count", 0)):
        events.append({"type": "card_drawn", "side": side, "amount": 1})


def build_battle_events(match, before, logs, winner):
    events = [{"type": "round_started", "round": before["round"]}]

    p1_before = before["p1"]
    p2_before = before["p2"]

    events.append({"type": "intent_revealed", "side": "player", "intent": p1_before["intent"]})
    events.append({"type": "intent_revealed", "side": "enemy", "intent": p2_before["intent"]})

    for side, player_before in [("player", p1_before), ("enemy", p2_before)]:
        monster_name = _card_label(player_before.get("field_m"))
        spell_trap_name = _card_label(player_before.get("field_st"))

        if monster_name:
            events.append({"type": "card_played", "side": side, "card_name": monster_name, "zone": "monster"})

        if spell_trap_name:
            events.append({"type": "card_played", "side": side, "card_name": spell_trap_name, "zone": "spell_trap"})

    _append_player_change_events(events, p1_before, match["p1"], "player", "player")
    _append_player_change_events(events, p2_before, match["p2"], "enemy", "enemy")

    if winner == "p1":
        title = f"{match['p1']['name']} won the match"
    elif winner == "p2":
        title = f"{match['p2']['name']} won the match"
    elif winner == "DRAW":
        title = "Match ended in a draw"
    else:
        title = f"Round {before['round']} resolved"

    events.append({
        "type": "round_summary",
        "title": title,
        "description": logs[-1] if logs else "Battle resolved.",
    })

    events.append({
        "type": "unleash_ready",
        "side": "player",
        "ready": int(match["p1"].get("ambition", 0)) >= 5 and bool(match["p1"].get("field_m")),
    })
    events.append({
        "type": "unleash_ready",
        "side": "enemy",
        "ready": int(match["p2"].get("ambition", 0)) >= 5 and bool(match["p2"].get("field_m")),
    })

    return events


def resolve_battle(match):
    p1 = match["p1"]
    p2 = match["p2"]
    before = _battle_snapshot(match)

    logs = []
    match["resolving"] = True
    match["phase"] = "Battle Phase"

    p1["shield"] = 0
    p2["shield"] = 0

    logs.append(f"Round {match['round']} entered Battle Phase.")
    logs.append(f"{p1['name']} chose {p1.get('intent', 'Strike')} intent.")
    logs.append(f"{p2['name']} chose {p2.get('intent', 'Strike')} intent.")

    if p1.get("field_m"):
        logs.extend(apply_summon_effect(p1, p2, p1["field_m"]))

    if p2.get("field_m"):
        logs.extend(apply_summon_effect(p2, p1, p2["field_m"]))

    if p1.get("field_st"):
        if p1["field_st"]["type"] == "Spell":
            logs.extend(apply_spell(p1, p2, p1["field_st"]))
        elif p1["field_st"]["type"] == "Trap":
            logs.extend(apply_trap(p1, p2, p1["field_st"]))

    if p2.get("field_st"):
        if p2["field_st"]["type"] == "Spell":
            logs.extend(apply_spell(p2, p1, p2["field_st"]))
        elif p2["field_st"]["type"] == "Trap":
            logs.extend(apply_trap(p2, p1, p2["field_st"]))

    p1_monster = p1.get("field_m")
    p2_monster = p2.get("field_m")

    p1_ambition_bonus = resolve_manual_unleash(p1, logs)
    p2_ambition_bonus = resolve_manual_unleash(p2, logs)

    if p1_monster:
        apply_sigil_ambition_bonus(p1, p1_monster, p2_monster, logs)

    if p2_monster:
        apply_sigil_ambition_bonus(p2, p2_monster, p1_monster, logs)

    if p1_monster and p2_monster:
        p1_advantage_log = elemental_log(p1_monster, p2_monster, p1["name"])
        p2_advantage_log = elemental_log(p2_monster, p1_monster, p2["name"])

        if p1_advantage_log:
            logs.append(p1_advantage_log)
            add_ambition(p1, 1, "won elemental reading", logs)

        if p2_advantage_log:
            logs.append(p2_advantage_log)
            add_ambition(p2, 1, "won elemental reading", logs)

        p1_power = calculate_final_power(p1_monster, p2_monster)
        p2_power = calculate_final_power(p2_monster, p1_monster)

        p1_power += p1_ambition_bonus
        p2_power += p2_ambition_bonus

        p1_power += strike_win_bonus(p1, logs)
        p2_power += strike_win_bonus(p2, logs)

        p1_power += calculate_sigil_power_bonus(p1, p1_monster, p2_monster, logs)
        p2_power += calculate_sigil_power_bonus(p2, p2_monster, p1_monster, logs)

        logs.append(f"{p1['name']} revealed {p1_monster['name']} with {p1_power} final power.")
        logs.append(f"{p2['name']} revealed {p2_monster['name']} with {p2_power} final power.")

        if p1_power > p2_power:
            raw_damage = p1_power - p2_power
            raw_damage = apply_clash_pressure(raw_damage, match, logs)
            pierce = piercing_bonus_damage(p1_monster)
            raw_damage += pierce

            if pierce > 0:
                logs.append(f"{p1_monster['name']} triggered Piercing: +{pierce} damage.")

            final_damage = apply_damage_package(
                p1,
                p2,
                p1_monster,
                p2_monster,
                raw_damage,
                logs,
                minimum_damage=clash_net_damage_floor(match.get("round", 1)),
            )

            add_ambition(p1, 1, "caused battle damage", logs)

            if has_elemental_advantage(p1_monster.get("element"), p2_monster.get("element")):
                add_ambition(p1, 1, "converted elemental advantage into damage", logs)

            logs.append(f"{p1_monster['name']} defeated {p2_monster['name']}. {p2['name']} took {final_damage} damage.")

        elif p2_power > p1_power:
            raw_damage = p2_power - p1_power
            raw_damage = apply_clash_pressure(raw_damage, match, logs)
            pierce = piercing_bonus_damage(p2_monster)
            raw_damage += pierce

            if pierce > 0:
                logs.append(f"{p2_monster['name']} triggered Piercing: +{pierce} damage.")

            final_damage = apply_damage_package(
                p2,
                p1,
                p2_monster,
                p1_monster,
                raw_damage,
                logs,
                minimum_damage=clash_net_damage_floor(match.get("round", 1)),
            )

            add_ambition(p2, 1, "caused battle damage", logs)

            if has_elemental_advantage(p2_monster.get("element"), p1_monster.get("element")):
                add_ambition(p2, 1, "converted elemental advantage into damage", logs)

            logs.append(f"{p2_monster['name']} defeated {p1_monster['name']}. {p1['name']} took {final_damage} damage.")

        else:
            logs.append("Clash ended in a deadlock. Both monsters matched final power. No battle damage was dealt.")

    elif p1_monster and not p2_monster:
        raw_damage = p1_monster.get("power", 0)
        raw_damage += piercing_bonus_damage(p1_monster)
        raw_damage += p1_ambition_bonus
        raw_damage += calculate_sigil_power_bonus(p1, p1_monster, None, logs)
        raw_damage += calculate_sigil_damage_bonus(p1, p1_monster, None, logs)

        final_damage = apply_damage_package(
            p1,
            p2,
            p1_monster,
            None,
            raw_damage,
            logs,
        )

        add_ambition(p1, 2, "attacked directly", logs)
        logs.append(f"{p1['name']} attacked directly with {p1_monster['name']}. {p2['name']} took {final_damage} damage.")

    elif p2_monster and not p1_monster:
        raw_damage = p2_monster.get("power", 0)
        raw_damage += piercing_bonus_damage(p2_monster)
        raw_damage += p2_ambition_bonus
        raw_damage += calculate_sigil_power_bonus(p2, p2_monster, None, logs)
        raw_damage += calculate_sigil_damage_bonus(p2, p2_monster, None, logs)

        final_damage = apply_damage_package(
            p2,
            p1,
            p2_monster,
            None,
            raw_damage,
            logs,
        )

        add_ambition(p2, 2, "attacked directly", logs)
        logs.append(f"{p2['name']} attacked directly with {p2_monster['name']}. {p1['name']} took {final_damage} damage.")

    else:
        logs.append("No monsters were played. Round ended with no battle damage.")

    apply_duel_storm_pressure(match, logs)

    apply_focus_survival(p1, logs)
    apply_focus_survival(p2, logs)

    p1["graveyard"].extend([card for card in [p1.get("field_m"), p1.get("field_st")] if card])
    p2["graveyard"].extend([card for card in [p2.get("field_m"), p2.get("field_st")] if card])

    p1["field_m"] = None
    p1["field_st"] = None
    p2["field_m"] = None
    p2["field_st"] = None

    p1["ready"] = False
    p2["ready"] = False

    p1_draw = draw_card(p1)
    p2_draw = draw_card(p2)

    if p1_draw:
        logs.append(f"{p1['name']} drew 1 card for the next round.")
    else:
        logs.append(f"{p1['name']} had no cards to draw and took fatigue damage.")

    if p2_draw:
        logs.append(f"{p2['name']} drew 1 card for the next round.")
    else:
        logs.append(f"{p2['name']} had no cards to draw and took fatigue damage.")

    match["round"] += 1
    match["phase"] = "Set Phase"
    match["resolving"] = False

    reset_round_flags(p1)
    reset_round_flags(p2)

    reset_player_energy(p1, match["round"])
    reset_player_energy(p2, match["round"])

    logs.append(f"Round {match['round']} started. Each player has {energy_for_round(match['round'])} energy.")

    winner = None

    if p1["hp"] <= 0 and p2["hp"] <= 0:
        winner = "DRAW"
    elif p1["hp"] <= 0:
        winner = "p2"
    elif p2["hp"] <= 0:
        winner = "p1"

    events = build_battle_events(match, before, logs, winner)
    match.setdefault("events", []).extend(events)

    return {
        "logs": logs,
        "winner": winner,
        "events": events,
    }

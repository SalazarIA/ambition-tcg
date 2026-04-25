from game.deck import draw_card
from game.rules import (
    apply_damage,
    apply_spell,
    apply_summon_effect,
    apply_trap,
    calculate_final_power,
    piercing_bonus_damage,
)


def resolve_battle(match):
    p1 = match["p1"]
    p2 = match["p2"]

    logs = []
    match["resolving"] = True

    p1["shield"] = 0
    p2["shield"] = 0

    logs.append(f"Round {match['round']} started.")

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

    if p1_monster and p2_monster:
        p1_power = calculate_final_power(p1_monster, p2_monster)
        p2_power = calculate_final_power(p2_monster, p1_monster)

        logs.append(f"{p1['name']} revealed {p1_monster['name']} with {p1_power} power.")
        logs.append(f"{p2['name']} revealed {p2_monster['name']} with {p2_power} power.")

        if p1_power > p2_power:
            raw_damage = p1_power - p2_power
            raw_damage += piercing_bonus_damage(p1_monster)

            final_damage = apply_damage(p2, raw_damage)

            logs.append(f"{p1_monster['name']} defeated {p2_monster['name']}. {p2['name']} took {final_damage} damage.")

        elif p2_power > p1_power:
            raw_damage = p2_power - p1_power
            raw_damage += piercing_bonus_damage(p2_monster)

            final_damage = apply_damage(p1, raw_damage)

            logs.append(f"{p2_monster['name']} defeated {p1_monster['name']}. {p1['name']} took {final_damage} damage.")

        else:
            logs.append("Both monsters had equal power. No damage was dealt.")

    elif p1_monster and not p2_monster:
        raw_damage = p1_monster.get("power", 0)
        raw_damage += piercing_bonus_damage(p1_monster)

        final_damage = apply_damage(p2, raw_damage)

        logs.append(f"{p1['name']} attacked directly with {p1_monster['name']}. {p2['name']} took {final_damage} damage.")

    elif p2_monster and not p1_monster:
        raw_damage = p2_monster.get("power", 0)
        raw_damage += piercing_bonus_damage(p2_monster)

        final_damage = apply_damage(p1, raw_damage)

        logs.append(f"{p2['name']} attacked directly with {p2_monster['name']}. {p1['name']} took {final_damage} damage.")

    else:
        logs.append("No monsters were played. Round ended with no battle damage.")

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
        logs.append(f"{p1['name']} drew 1 card.")
    else:
        logs.append(f"{p1['name']} had no cards to draw and took fatigue damage.")

    if p2_draw:
        logs.append(f"{p2['name']} drew 1 card.")
    else:
        logs.append(f"{p2['name']} had no cards to draw and took fatigue damage.")

    match["round"] += 1
    match["resolving"] = False

    winner = None

    if p1["hp"] <= 0 and p2["hp"] <= 0:
        winner = "DRAW"
    elif p1["hp"] <= 0:
        winner = "p2"
    elif p2["hp"] <= 0:
        winner = "p1"

    return {
        "logs": logs,
        "winner": winner,
    }
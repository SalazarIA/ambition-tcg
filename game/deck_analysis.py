from game.cards import get_card_by_id


def count_card_types(deck_ids):
    counts = {
        "Monster": 0,
        "Spell": 0,
        "Trap": 0,
    }

    for card_id in deck_ids:
        card = get_card_by_id(card_id)

        if card:
            counts[card["type"]] += 1

    return counts


def starter_deck_stats(deck_ids):
    counts = count_card_types(deck_ids)
    total = len(deck_ids) or 1

    return {
        "total": len(deck_ids),
        "monsters": counts["Monster"],
        "spells": counts["Spell"],
        "traps": counts["Trap"],
        "monster_percent": round((counts["Monster"] / total) * 100, 2),
        "spell_percent": round((counts["Spell"] / total) * 100, 2),
        "trap_percent": round((counts["Trap"] / total) * 100, 2),
    }


def deck_energy_curve(deck_ids):
    curve = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        "6+": 0,
    }

    total_cost = 0
    valid_cards = 0

    for card_id in deck_ids:
        card = get_card_by_id(card_id)

        if not card:
            continue

        cost = int(card.get("cost", 1))
        total_cost += cost
        valid_cards += 1

        if cost <= 1:
            curve[1] += 1
        elif cost == 2:
            curve[2] += 1
        elif cost == 3:
            curve[3] += 1
        elif cost == 4:
            curve[4] += 1
        elif cost == 5:
            curve[5] += 1
        else:
            curve["6+"] += 1

    average_cost = 0

    if valid_cards > 0:
        average_cost = round(total_cost / valid_cards, 2)

    return {
        "curve": curve,
        "average_cost": average_cost,
    }


def deck_element_counts(deck_ids):
    return _count_card_field(deck_ids, "element", "Global")


def deck_sigil_counts(deck_ids):
    return _count_card_field(deck_ids, "sigil", "Global")


def deck_rarity_counts(deck_ids):
    return _count_card_field(deck_ids, "rarity", "Common")


def deck_archetype_counts(deck_ids):
    return _count_card_field(deck_ids, "archetype", "Ambition Core")


def _count_card_field(deck_ids, field_name, fallback):
    counts = {}

    for card_id in deck_ids:
        card = get_card_by_id(card_id)

        if not card:
            continue

        value = card.get(field_name, fallback)
        counts[value] = counts.get(value, 0) + 1

    return counts


def full_deck_analysis(deck_ids):
    stats = starter_deck_stats(deck_ids)
    energy = deck_energy_curve(deck_ids)
    elements = deck_element_counts(deck_ids)

    warnings = []

    if stats["total"] != 30:
        warnings.append("Deck must have exactly 30 cards.")

    if stats["monsters"] != 21:
        warnings.append("Beta deck should have exactly 21 monsters.")

    if stats["spells"] != 6:
        warnings.append("Beta deck should have exactly 6 spells.")

    if stats["traps"] != 3:
        warnings.append("Beta deck should have exactly 3 traps.")

    if energy["average_cost"] > 3.2:
        warnings.append("Average cost is high. The deck may feel slow in early rounds.")

    if energy["curve"][1] + energy["curve"][2] < 12:
        warnings.append("Low early-game count. Add more cost 1-2 cards.")

    return {
        "stats": stats,
        "energy": energy,
        "elements": elements,
        "warnings": warnings,
    }


def deck_analysis_v115(deck_ids):
    stats = starter_deck_stats(deck_ids)
    energy = deck_energy_curve(deck_ids)
    elements = deck_element_counts(deck_ids)
    sigils = deck_sigil_counts(deck_ids)
    rarities = deck_rarity_counts(deck_ids)
    archetypes = deck_archetype_counts(deck_ids)

    warnings = []
    strengths = []
    total = stats["total"]

    if total == 30:
        strengths.append("Deck size is complete at 30/30.")
    else:
        warnings.append(f"Deck has {total}/30 cards.")

    if stats["monsters"] == 21:
        strengths.append("Monster count is correct at 21.")
    else:
        warnings.append(f"Monster count should be 21. Current: {stats['monsters']}.")

    if stats["spells"] == 6:
        strengths.append("Spell count is correct at 6.")
    else:
        warnings.append(f"Spell count should be 6. Current: {stats['spells']}.")

    if stats["traps"] == 3:
        strengths.append("Trap count is correct at 3.")
    else:
        warnings.append(f"Trap count should be 3. Current: {stats['traps']}.")

    early_count = int(energy["curve"].get(1, 0)) + int(energy["curve"].get(2, 0))

    if early_count >= 12:
        strengths.append("Early curve is healthy with 12+ cost 1-2 cards.")
    else:
        warnings.append("Low early-game count. Add more cost 1-2 cards.")

    if energy["average_cost"] > 3.2:
        warnings.append("Average cost is high. The deck may feel slow.")
    elif energy["average_cost"] <= 2.7:
        strengths.append("Average cost is fast and tempo-friendly.")
    else:
        strengths.append("Average cost is balanced.")

    focused_elements = [
        key for key, value in elements.items()
        if key != "Global" and int(value) >= 6
    ]

    if focused_elements:
        strengths.append("Element identity detected: " + ", ".join(focused_elements) + ".")
    else:
        warnings.append("No strong element identity yet. Consider focusing one element.")

    focused_sigils = [
        key for key, value in sigils.items()
        if key != "Global" and int(value) >= 6
    ]

    if focused_sigils:
        strengths.append("Sigil identity detected: " + ", ".join(focused_sigils) + ".")
    else:
        warnings.append("No strong Sigil identity yet. Consider focusing one Sigil.")

    return {
        "stats": stats,
        "energy": energy,
        "elements": elements,
        "sigils": sigils,
        "rarities": rarities,
        "archetypes": archetypes,
        "warnings": warnings,
        "strengths": strengths,
    }

def safe_name(player):
    return str((player or {}).get("name", "Unknown"))


def safe_hp(player):
    try:
        return int((player or {}).get("hp", 0) or 0)
    except Exception:
        return 0


def safe_card_name(card):
    if not card:
        return "No card"

    return str(card.get("name", "Unknown Card"))


def build_match_summary_lines(match, winner_key):
    p1 = match.get("p1", {})
    p2 = match.get("p2", {})

    round_number = match.get("round", 0)
    mode = "Training" if match.get("training") else "PvP"
    difficulty = match.get("bot_difficulty")

    lines = []
    lines.append(f"Match ended after round {round_number}. Mode: {mode}.")

    if difficulty:
        lines.append(f"Bot difficulty: {difficulty}.")

    if winner_key == "DRAW":
        lines.append("Result: Draw.")
    else:
        loser_key = "p2" if winner_key == "p1" else "p1"
        winner = match.get(winner_key, {})
        loser = match.get(loser_key, {})

        lines.append(f"Winner: {safe_name(winner)} with {safe_hp(winner)} HP remaining.")
        lines.append(f"Defeated: {safe_name(loser)}.")

    lines.append(
        f"{safe_name(p1)} final monster: {safe_card_name(p1.get('field_m'))}."
    )
    lines.append(
        f"{safe_name(p2)} final monster: {safe_card_name(p2.get('field_m'))}."
    )

    return lines

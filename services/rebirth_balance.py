from collections import Counter

from services.rebirth_engine import next_turn, play_card, start_match


def choose_player_card(hand):
    if not hand:
        return None
    return sorted(
        hand,
        key=lambda card: (int(card.get("attack", 0)), int(card.get("guard", 0)), card["name"]),
        reverse=True,
    )[0]


def simulate_match(seed=None, max_turns=12):
    match = start_match(seed=seed)
    card_usage = Counter()
    turns = 0
    while not match.get("is_finished") and turns < max_turns:
        card = choose_player_card(match["player"]["hand"])
        if not card:
            break
        card_usage[card["id"]] += 1
        play_card(match, card_instance_id=card["instance_id"])
        turns += 1
        if not match.get("is_finished"):
            next_turn(match)

    return {
        "winner": match.get("winner") or "unfinished",
        "turns": turns,
        "player_hp": match["player"]["hp"],
        "bot_hp": match["bot"]["hp"],
        "card_usage": dict(card_usage),
    }


def simulate_balance(matches=40):
    matches = max(1, min(int(matches or 40), 200))
    winners = Counter()
    card_usage = Counter()
    total_turns = 0
    samples = []
    for index in range(matches):
        result = simulate_match(seed=f"balance-{index}")
        winners[result["winner"]] += 1
        card_usage.update(result["card_usage"])
        total_turns += result["turns"]
        if index < 5:
            samples.append(result)

    player_wins = winners.get("player", 0)
    bot_wins = winners.get("bot", 0)
    return {
        "matches": matches,
        "summary": {
            "player_win_rate": round(player_wins / matches, 3),
            "bot_win_rate": round(bot_wins / matches, 3),
            "unfinished_rate": round(winners.get("unfinished", 0) / matches, 3),
            "average_turns": round(total_turns / matches, 2),
        },
        "winners": dict(winners),
        "most_used_cards": [{"card_id": card_id, "plays": plays} for card_id, plays in card_usage.most_common(8)],
        "samples": samples,
        "bot_tuning": {
            "policy": "answer with the smallest winning attack; otherwise maximize guard",
            "status": "deterministic baseline",
        },
    }

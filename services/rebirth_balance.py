from collections import Counter, defaultdict

from services.rebirth_bot import BOT_PERSONALITY_ORDER, BOT_PERSONALITIES
from services.rebirth_cards import catalog_payload
from services.rebirth_engine import next_turn, play_card, start_match


def choose_player_card(hand):
    if not hand:
        return None
    return sorted(
        hand,
        key=lambda card: (int(card.get("attack", 0)), int(card.get("guard", 0)), card["name"]),
        reverse=True,
    )[0]


def simulate_match(seed=None, max_turns=12, bot_profile_id=None):
    match = start_match(seed=seed, bot_profile_id=bot_profile_id)
    card_usage = Counter()
    card_wins = Counter()
    card_damage = Counter()
    ability_usage = Counter()
    ability_wins = Counter()
    ability_damage = Counter()
    ability_events = Counter()
    turns = 0
    while not match.get("is_finished") and turns < max_turns:
        card = choose_player_card(match["player"]["hand"])
        if not card:
            break
        play_card(match, card_instance_id=card["instance_id"])
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
        for event in result.get("ability_events") or []:
            ability_events[str(event)] += 1
        turns += 1
        if not match.get("is_finished"):
            next_turn(match)

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
        "ability_events": dict(ability_events),
    }


def simulate_balance(matches=40):
    matches = max(1, min(int(matches or 40), 200))
    winners = Counter()
    card_usage = Counter()
    card_wins = Counter()
    card_damage = Counter()
    ability_usage = Counter()
    ability_wins = Counter()
    ability_damage = Counter()
    profile_winners = defaultdict(Counter)
    profile_turns = Counter()
    profile_matches = Counter()
    ability_events = Counter()
    total_turns = 0
    samples = []
    for index in range(matches):
        profile_id = BOT_PERSONALITY_ORDER[index % len(BOT_PERSONALITY_ORDER)]
        result = simulate_match(seed=f"balance-{index}", bot_profile_id=profile_id)
        winners[result["winner"]] += 1
        card_usage.update(result["card_usage"])
        card_wins.update(result["card_wins"])
        card_damage.update(result["card_damage"])
        ability_usage.update(result["ability_usage"])
        ability_wins.update(result["ability_wins"])
        ability_damage.update(result["ability_damage"])
        ability_events.update(result["ability_events"])
        total_turns += result["turns"]
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
        wins = card_wins.get(card_id, 0)
        damage = card_damage.get(card_id, 0)
        card_stats.append(
            {
                "card_id": card_id,
                "name": card["name"],
                "ability_key": card["ability_key"],
                "plays": plays,
                "wins": wins,
                "win_rate": round(wins / plays, 3) if plays else 0,
                "avg_damage": round(damage / plays, 2) if plays else 0,
            }
        )
    ability_stats = []
    ability_labels = {card["ability_key"]: card["ability_name"] for card in catalog.values()}
    for key, plays in ability_usage.most_common():
        wins = ability_wins.get(key, 0)
        damage = ability_damage.get(key, 0)
        ability_stats.append(
            {
                "ability_key": key,
                "name": ability_labels.get(key, key.replace("_", " ").title()),
                "plays": plays,
                "wins": wins,
                "win_rate": round(wins / plays, 3) if plays else 0,
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
        "samples": samples,
        "bot_tuning": {
            "policy": "rotate defensive, aggressive and opportunist profiles across deterministic simulations",
            "status": "personality lab",
        },
    }

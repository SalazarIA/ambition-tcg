#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
import argparse
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.ascension_bot import BOT_PROFILES, run_bot_turn  # noqa: E402
from services.ascension_engine import attempt_dominate, can_dominate, choose_intent, create_match, play_card, resolve_clash  # noqa: E402


INTENTS = ["Focus", "Strike", "Guard", "Scheme"]


def _record(counter, card_id):
    if card_id:
        counter[str(card_id)] += 1


def player_action(match, card_counter):
    player = match["player"]
    if not player.get("active_champion"):
        champion = next((card for card in player["hand"] if card["type"] == "champion"), None)
        if champion:
            play_card(match, "player", champion["id"], mode="summon")
            _record(card_counter, champion["id"])
            return

    if player.get("active_champion") and len(player.get("bound_souls", [])) < 2:
        champion = next((card for card in player["hand"] if card["type"] == "champion"), None)
        if champion:
            play_card(match, "player", champion["id"], mode="bind")
            _record(card_counter, champion["id"])
            return

    if player.get("active_champion"):
        ascension = next((card for card in player["hand"] if card["type"] == "ascension"), None)
        if ascension and player.get("ambition", 0) >= ascension.get("ambition_cost", 99):
            play_card(match, "player", ascension["id"], mode="ascend")
            _record(card_counter, ascension["id"])
            return

    relic = next((card for card in player["hand"] if card["type"] == "relic" and not player.get("relic")), None)
    if relic:
        play_card(match, "player", relic["id"], mode="equip")
        _record(card_counter, relic["id"])
        return

    scheme = next((card for card in player["hand"] if card["type"] == "scheme" and len(player.get("schemes", [])) < 2), None)
    if scheme:
        play_card(match, "player", scheme["id"], mode="set")
        _record(card_counter, scheme["id"])
        return

    technique = next((card for card in player["hand"] if card["type"] == "technique"), None)
    if technique:
        play_card(match, "player", technique["id"], mode="cast")
        _record(card_counter, technique["id"])
        return

    if player["hand"]:
        card = player["hand"][0]
        play_card(match, "player", card["id"], mode="burn")
        _record(card_counter, card["id"])


def simulate(matches=500, max_rounds=32):
    results = Counter()
    durations = []
    dominate_count = 0
    card_counter = Counter()
    profile_counter = Counter()

    profiles = list(BOT_PROFILES)
    for index in range(matches):
        profile = profiles[index % len(profiles)]
        profile_counter[profile] += 1
        match = create_match(seed=f"balance-{index}", bot_profile=profile)
        for round_index in range(max_rounds):
            if match.get("winner"):
                break
            intent = INTENTS[(index + round_index) % len(INTENTS)]
            choose_intent(match, "player", intent)
            player_action(match, card_counter)
            if can_dominate(match, "player") and (match["opponent"].get("hp", 30) <= 15 or match["player"].get("ascended")):
                attempt_dominate(match, "player")
                if match.get("winner"):
                    break
            run_bot_turn(match, profile=profile)
            resolve_clash(match)

        winner = match.get("winner") or "unresolved"
        results[winner] += 1
        durations.append(match.get("round", 0))
        dominate_count += sum(1 for event in match.get("chronicle", []) if event.get("type") == "domination_success")

    average_duration = sum(durations) / len(durations) if durations else 0
    return {
        "matches": matches,
        "results": dict(results),
        "player_winrate": round(results.get("player", 0) / matches, 4) if matches else 0,
        "bot_winrate": round(results.get("opponent", 0) / matches, 4) if matches else 0,
        "draw_rate": round(results.get("draw", 0) / matches, 4) if matches else 0,
        "average_duration": round(average_duration, 2),
        "dominate_rate": round(dominate_count / matches, 4) if matches else 0,
        "most_used_cards": card_counter.most_common(12),
        "profile_mix": dict(profile_counter),
    }


def report_text(metrics):
    high = metrics["most_used_cards"][:3]
    low = metrics["most_used_cards"][-3:]
    return "\n".join(
        [
            "# Ascension Balance Report",
            "",
            f"Matches simulated: {metrics['matches']}",
            f"Player winrate: {metrics['player_winrate']:.2%}",
            f"Bot winrate: {metrics['bot_winrate']:.2%}",
            f"Draw rate: {metrics['draw_rate']:.2%}",
            f"Average duration: {metrics['average_duration']} rounds",
            f"Dominate rate: {metrics['dominate_rate']:.2%}",
            "",
            "## Most Used Cards",
            *[f"- {card_id}: {count}" for card_id, count in metrics["most_used_cards"]],
            "",
            "## Impact Read",
            f"High exposure cards: {', '.join(card for card, _count in high) if high else 'none'}",
            f"Low exposure cards: {', '.join(card for card, _count in low) if low else 'none'}",
            "",
            "## Tuning Notes",
            "- Black Sun Witness was softened from extreme pressure into a more readable rare Champion profile.",
            "- Iron Prayer was nudged upward as a recovery Technique so defensive decks can survive fast starts.",
            "- Dominion of Ash was trimmed to keep Domination and Ascension from stacking into abrupt executions.",
            "- Domination now requires 20 Ambition so it reads as a risky finisher rather than a routine midgame action.",
            "",
            "## Possible Nerfs/Buffs",
            "- Watch aggressive rare Champions if bot winrate stays above 58%.",
            "- Watch recovery cards if average duration rises above 12 rounds.",
            "- Keep Domination rate below 20% for beta readability.",
        ]
    ) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--matches", type=int, default=500)
    parser.add_argument("--max-rounds", type=int, default=32)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)

    metrics = simulate(matches=args.matches, max_rounds=args.max_rounds)
    text = report_text(metrics)
    if not args.no_write:
        (PROJECT_ROOT / "docs" / "ASCENSION_BALANCE_REPORT.md").write_text(text, encoding="utf-8")
    print(text)
    return metrics


if __name__ == "__main__":
    main()

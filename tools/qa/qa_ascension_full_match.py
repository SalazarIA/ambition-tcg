#!/usr/bin/env python3
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.ascension_bot import run_bot_turn  # noqa: E402
from services.ascension_engine import choose_intent, create_match, play_card, resolve_clash  # noqa: E402


def player_action(match):
    player = match["player"]
    if not player.get("active_champion"):
        champion = next((card for card in player["hand"] if card["type"] == "champion"), None)
        if champion:
            play_card(match, "player", champion["id"], mode="summon")
            return
    relic = next((card for card in player["hand"] if card["type"] == "relic" and not player.get("relic")), None)
    if relic:
        play_card(match, "player", relic["id"], mode="equip")
        return
    technique = next((card for card in player["hand"] if card["type"] == "technique"), None)
    if technique:
        play_card(match, "player", technique["id"], mode="cast")
        return
    if player["hand"]:
        play_card(match, "player", player["hand"][0]["id"], mode="burn")


def main():
    match = create_match(seed="qa-full-match")
    for index in range(30):
        if match.get("winner"):
            break
        choose_intent(match, "player", ["Focus", "Strike", "Guard", "Scheme"][index % 4])
        player_action(match)
        run_bot_turn(match)
        resolve_clash(match)

    assert match["phase"] in {"intent", "finished"}
    assert match["round"] >= 2
    assert len(match["chronicle"]) >= 10
    print(f"PASS ascension_full_match rounds={match['round']} winner={match.get('winner')}")


if __name__ == "__main__":
    main()

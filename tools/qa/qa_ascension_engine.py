#!/usr/bin/env python3
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.ascension_cards import get_card_by_id  # noqa: E402
from services.ascension_engine import choose_intent, create_match, play_card, resolve_clash  # noqa: E402


def main():
    deck = [
        get_card_by_id("ember_vowbound"),
        get_card_by_id("ashen_pulse"),
        get_card_by_id("cinder_halo"),
        get_card_by_id("sunken_oath"),
        get_card_by_id("iron_prayer"),
    ]
    rival = [
        get_card_by_id("crownless_warden"),
        get_card_by_id("debt_of_the_starless"),
        get_card_by_id("saint_engine"),
        get_card_by_id("thorn_pact"),
        get_card_by_id("mirror_break"),
    ]
    match_a = create_match(seed="qa-engine", player_deck=deck, opponent_deck=rival)
    match_b = create_match(seed="qa-engine", player_deck=deck, opponent_deck=rival)

    assert [card["id"] for card in match_a["player"]["hand"]] == [card["id"] for card in match_b["player"]["hand"]]
    play_card(match_a, "player", "ember_vowbound", mode="summon")
    play_card(match_a, "opponent", "crownless_warden", mode="summon")
    choose_intent(match_a, "player", "Strike")
    choose_intent(match_a, "opponent", "Focus")
    resolve_clash(match_a)

    assert match_a["round"] == 2
    assert match_a["phase"] == "intent"
    assert any(event["type"] == "clash_resolved" for event in match_a["chronicle"])
    print("PASS ascension_engine")


if __name__ == "__main__":
    main()

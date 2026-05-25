#!/usr/bin/env python3
"""CI-safe MCTS stress harness for Rebirth tactical search."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rebirth_bot import MCTSAgent
from services.rebirth_cards import create_card_instance
from services.rebirth_profiler import debug_profile


def _battlefield_card(card_id, owner, sequence, slot, *, attack=None, guard=None):
    card = create_card_instance(card_id, owner, sequence)
    if attack is not None:
        card["attack"] = attack
        card["power"] = attack
    if guard is not None:
        card["guard"] = guard
    card["owner_side"] = owner
    card["field_slot"] = slot
    card["slot"] = slot + 1
    card["current_guard"] = int(card.get("guard", 0) or 0)
    card["max_guard"] = int(card.get("guard", 0) or 0)
    card["exhausted"] = False
    card["has_attacked"] = False
    card["has_acted"] = False
    card["statuses"] = {}
    return card


def run_stress(iterations: int = 800):
    bot_cards = [
        _battlefield_card("card_010", "bot", 1, 0, attack=9, guard=5),
        _battlefield_card("card_041", "bot", 2, 1, attack=4, guard=6),
        _battlefield_card("card_021", "bot", 3, 2, attack=4, guard=4),
    ]
    player_cards = [
        _battlefield_card("legend_infernus_core", "player", 1, 0),
        _battlefield_card("legend_shadow_reaper", "player", 2, 1),
        _battlefield_card("card_001", "player", 3, 2),
    ]
    started = perf_counter()
    choices = 0
    with debug_profile(enabled=True) as profiler:
        for index in range(iterations):
            choice = MCTSAgent(budget=800).choose_attack(
                bot_cards,
                player_cards,
                player_hp=30,
                turn=index % 8 + 1,
                player_wounded=index % 2 == 0,
                bot_wounded=index % 3 == 0,
            )
            if choice:
                choices += 1
    elapsed_ms = (perf_counter() - started) * 1000
    return {
        "ok": True,
        "iterations": iterations,
        "choices": choices,
        "elapsed_ms": round(elapsed_ms, 3),
        "simulations_per_second": round(iterations / (elapsed_ms / 1000), 3) if elapsed_ms else 0.0,
        "profiler": profiler.summary(),
    }


def main():
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 800
    print(json.dumps(run_stress(iterations=iterations), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Deterministic BE2 balance simulation.

Runs headless bot-vs-bot style training matches through the canonical BE2
functions. It is intentionally lightweight and does not require Flask,
Socket.IO or a browser.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.battle_engine_v2 import (  # noqa: E402
    board_creatures,
    bot_choose_action,
    choose_intent,
    create_match,
    empty_lanes,
    finish_by_tiebreak,
    first_empty_lane,
    play_card,
    playable_cards,
    resolve_round,
    start_round,
    validate_match_integrity,
)


def _catalog_card_id(card: Optional[Dict[str, Any]]) -> str:
    if not card:
        return "unknown"
    value = str(card.get("card_id") or card.get("catalog_id") or card.get("id") or "unknown")
    for prefix in ("player-left-", "player-center-", "player-right-", "opponent-left-", "opponent-center-", "opponent-right-"):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    if "-" in value and value.rsplit("-", 1)[1].isdigit():
        value = value.rsplit("-", 1)[0]
    return value or "unknown"


def _attack_pressure(player: Dict[str, Any]) -> int:
    return sum(int(card.get("atk") or 0) for _lane, card in board_creatures(player))


def _choose_player_intent(match: Dict[str, Any]) -> str:
    player = match["player"]
    opponent = match["opponent"]
    incoming = _attack_pressure(opponent)

    if int(player.get("hp") or 0) <= 10 and incoming >= 4:
        return "Guard"
    if int(player.get("ambition") or 0) < 5 and int(player.get("hp") or 0) > 12 and incoming <= 4:
        return "Focus"
    return "Strike"


def _card_score(match: Dict[str, Any], card: Dict[str, Any], intent: str) -> tuple:
    player = match["player"]
    opponent = match["opponent"]
    kind = card.get("kind")
    cost = int(card.get("cost") or 0)

    if kind == "creature":
        empty_bonus = 18 if not board_creatures(player) else 6
        return (empty_bonus + int(card.get("atk") or 0) * 2 + int(card.get("hp") or 0), -cost, str(card.get("id") or ""))
    if kind == "guard":
        urgency = 14 if int(player.get("hp") or 0) <= 12 or _attack_pressure(opponent) >= 5 else 4
        return (urgency + int(card.get("shield") or 0) + int(card.get("damage") or 0), -cost, str(card.get("id") or ""))
    if kind == "support":
        return (8 + int(card.get("atk_bonus") or 0) * 3 + int(card.get("ambition_bonus") or 0) * 3, -cost, str(card.get("id") or ""))

    damage = int(card.get("damage") or 0)
    if card.get("id") == "pressure_move" and intent == "Strike":
        damage += 1
    lethal = 30 if damage >= int(opponent.get("hp") or 0) and damage > 0 else 0
    return (lethal + damage * 4 + int(card.get("ambition") or 0), -cost, str(card.get("id") or ""))


def _target_for_card(match: Dict[str, Any], card: Dict[str, Any]) -> Optional[str]:
    if card.get("kind") == "creature":
        return None
    if card.get("kind") == "support":
        return None
    if card.get("kind") == "guard":
        return "enemy_hero" if int(card.get("damage") or 0) > 0 else "self"
    return "enemy_hero"


def _player_choose_action(match: Dict[str, Any]) -> None:
    player = match["player"]

    if not player.get("intent"):
        choose_intent(match, "player", _choose_player_intent(match))

    if player.get("played_this_round"):
        player["ready"] = True
        return

    cards = playable_cards(player)
    if cards:
        intent = player.get("intent") or "Strike"
        if first_empty_lane(player):
            creatures = [card for card in cards if card.get("kind") == "creature"]
            if creatures:
                chosen = max(creatures, key=lambda card: _card_score(match, card, intent))
                play_card(match, "player", card_index=player["hand"].index(chosen), lane=empty_lanes(player)[0])
                player["ready"] = True
                return

        chosen = max(cards, key=lambda card: _card_score(match, card, intent))
        if chosen.get("kind") != "creature":
            play_card(match, "player", card_index=player["hand"].index(chosen), target=_target_for_card(match, chosen))

    player["ready"] = True


def run_single_match(seed: int, max_rounds: int) -> Dict[str, Any]:
    match = create_match(seed=seed)
    start_round(match)
    intent_counts = Counter()
    cards_played_by_id = Counter()
    cards_played = 0
    integrity_errors = []
    timeout = False

    while not match.get("winner"):
        if int(match.get("round") or 0) >= max_rounds:
            finish_by_tiebreak(match, reason="balance_sim_round_cap")
            break

        _player_choose_action(match)
        bot_choose_action(match)
        intent_counts.update([
            f"player:{match['player'].get('intent') or 'None'}",
            f"bot:{match['opponent'].get('intent') or 'None'}",
        ])
        for side in ("player", "opponent"):
            played = match[side].get("played_card")
            if played:
                cards_played += 1
                cards_played_by_id[_catalog_card_id(played)] += 1
        resolve_round(match)

        ok, errors = validate_match_integrity(match)
        if not ok:
            integrity_errors.extend(errors)
            break

    dead_hand_by_id = Counter()
    for side in ("player", "opponent"):
        for card in match[side].get("hand") or []:
            dead_hand_by_id[_catalog_card_id(card)] += 1

    return {
        "seed": seed,
        "winner": match.get("winner") or "draw",
        "rounds": int(match.get("round") or 0),
        "player_hp": int(match["player"].get("hp") or 0),
        "enemy_hp": int(match["opponent"].get("hp") or 0),
        "intent_counts": dict(intent_counts),
        "cards_played_by_id": dict(cards_played_by_id),
        "dead_hand_by_id": dict(dead_hand_by_id),
        "cards_played_count": cards_played,
        "timeout": timeout,
        "integrity_errors": integrity_errors,
    }


def run_simulation(matches: int, seed: int, max_rounds: int) -> Dict[str, Any]:
    results = [run_single_match(seed + index, max_rounds) for index in range(matches)]
    rounds = [result["rounds"] for result in results]
    player_wins = sum(1 for result in results if result["winner"] == "player")
    bot_wins = sum(1 for result in results if result["winner"] == "opponent")
    timeouts = sum(1 for result in results if result["timeout"])
    intent_counts = Counter()
    cards_played_by_id = Counter()
    dead_hand_by_id = Counter()
    for result in results:
        intent_counts.update(result["intent_counts"])
        cards_played_by_id.update(result["cards_played_by_id"])
        dead_hand_by_id.update(result["dead_hand_by_id"])

    total = max(1, len(results))
    metrics = {
        "total_matches": len(results),
        "player_wins": player_wins,
        "bot_wins": bot_wins,
        "draws_or_timeouts": total - player_wins - bot_wins,
        "win_rate": round(player_wins / total, 4),
        "average_rounds": round(sum(rounds) / total, 2),
        "min_rounds": min(rounds) if rounds else 0,
        "max_rounds": max(rounds) if rounds else 0,
        "average_player_hp_end": round(sum(result["player_hp"] for result in results) / total, 2),
        "average_enemy_hp_end": round(sum(result["enemy_hp"] for result in results) / total, 2),
        "intent_counts": dict(sorted(intent_counts.items())),
        "top_cards_played": cards_played_by_id.most_common(10),
        "least_played_cards": sorted(
            [(card_id, count) for card_id, count in cards_played_by_id.items()],
            key=lambda item: (item[1], item[0]),
        )[:10],
        "dead_hand_cards": dead_hand_by_id.most_common(10),
        "cards_played_count": sum(result["cards_played_count"] for result in results),
        "timeout_count": timeouts,
        "integrity_error_count": sum(len(result["integrity_errors"]) for result in results),
    }
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic BE2 battle balance simulations.")
    parser.add_argument("--matches", type=int, default=100)
    parser.add_argument("--seed", type=int, default=49056)
    parser.add_argument("--max-rounds", type=int, default=30)
    parser.add_argument("--json", action="store_true", help="Print JSON only.")
    args = parser.parse_args()

    metrics = run_simulation(max(1, args.matches), args.seed, max(1, args.max_rounds))
    ok = (
        metrics["timeout_count"] == 0
        and metrics["integrity_error_count"] == 0
        and 2 <= metrics["average_rounds"] <= args.max_rounds
    )

    if args.json:
        print(json.dumps(metrics, sort_keys=True))
    else:
        print("=== BE2 Battle Balance Simulation ===")
        for key, value in metrics.items():
            print(f"{key}: {value}")
        print("PASS" if ok else "FAIL")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

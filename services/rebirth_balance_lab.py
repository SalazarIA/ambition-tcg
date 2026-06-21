"""Paired balance experiments that separate deck strength from side advantage."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import fmean
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, Union

from services.rebirth_balance import simulate_match


Simulator = Callable[..., Dict[str, Any]]


def decision_regret(chosen_score: Any, best_score: Any) -> Optional[float]:
    try:
        chosen = float(chosen_score)
        best = float(best_score)
    except (TypeError, ValueError, OverflowError):
        return None
    return round(max(0.0, best - chosen), 6)


def summarize_regret(
    decisions: Iterable[Mapping[str, Any]],
    *,
    meaningful_threshold: float = 1.0,
) -> Dict[str, Any]:
    regrets = sorted(
        regret
        for decision in decisions or []
        if (regret := decision_regret(decision.get("chosen_score"), decision.get("best_score"))) is not None
    )
    meaningful = sum(1 for regret in regrets if regret >= float(meaningful_threshold))
    p95_index = max(0, int(len(regrets) * 0.95 + 0.999999) - 1) if regrets else None
    return {
        "decision_count": len(regrets),
        "average_regret": round(fmean(regrets), 4) if regrets else None,
        "regret_p95": round(regrets[p95_index], 4) if p95_index is not None else None,
        "max_regret": round(regrets[-1], 4) if regrets else None,
        "meaningful_threshold": float(meaningful_threshold),
        "meaningful_regret_count": meaningful,
        "meaningful_regret_rate": round(meaningful / len(regrets), 3) if regrets else None,
    }


def _seed_values(seeds: Union[int, Sequence[str]], prefix: str) -> list[str]:
    if isinstance(seeds, int):
        return [f"{prefix}-{index}" for index in range(max(1, seeds))]
    values = [str(seed) for seed in seeds]
    return values or [f"{prefix}-0"]


def _winner_deck(winner: str, player_deck: str, bot_deck: str) -> Optional[str]:
    if winner == "player":
        return player_deck
    if winner == "bot":
        return bot_deck
    return None


def paired_matchup(
    deck_a: Sequence[str],
    deck_b: Sequence[str],
    *,
    deck_a_name: str = "A",
    deck_b_name: str = "B",
    seeds: Union[int, Sequence[str]] = 20,
    seed_prefix: str = "paired",
    bot_profile_id: str = "opportunist",
    max_turns: int = 30,
    simulator: Simulator = simulate_match,
) -> Dict[str, Any]:
    """Run every seed twice, swapping which deck occupies the player side."""
    seed_values = _seed_values(seeds, seed_prefix)
    deck_wins = Counter()
    side_wins = Counter()
    turns = []
    games = []
    assignments = (
        (deck_a_name, list(deck_a), deck_b_name, list(deck_b), "ab"),
        (deck_b_name, list(deck_b), deck_a_name, list(deck_a), "ba"),
    )
    for seed in seed_values:
        for player_name, player_ids, bot_name, bot_ids, orientation in assignments:
            result = simulator(
                seed=seed,
                max_turns=max_turns,
                bot_profile_id=bot_profile_id,
                player_card_ids=player_ids,
                bot_card_ids=bot_ids,
            )
            winner = str(result.get("winner") or "unfinished")
            side_wins[winner] += 1
            winning_deck = _winner_deck(winner, player_name, bot_name)
            if winning_deck:
                deck_wins[winning_deck] += 1
            turns.append(int(result.get("turns", 0) or 0))
            games.append(
                {
                    "seed": seed,
                    "orientation": orientation,
                    "player_deck": player_name,
                    "bot_deck": bot_name,
                    "winner_side": winner,
                    "winner_deck": winning_deck,
                    "turns": int(result.get("turns", 0) or 0),
                }
            )

    total_games = len(games)
    finished = side_wins["player"] + side_wins["bot"]
    deck_games = max(1, total_games)
    player_rate = side_wins["player"] / max(1, finished)
    return {
        "version": "paired-balance-v1",
        "decks": [deck_a_name, deck_b_name],
        "seed_count": len(seed_values),
        "game_count": total_games,
        "summary": {
            "deck_win_rates": {
                deck_a_name: round(deck_wins[deck_a_name] / deck_games, 3),
                deck_b_name: round(deck_wins[deck_b_name] / deck_games, 3),
            },
            "player_side_win_rate": round(player_rate, 3),
            "bot_side_win_rate": round(side_wins["bot"] / max(1, finished), 3),
            "initiative_bias": round(player_rate - 0.5, 3),
            "unfinished_rate": round(side_wins["unfinished"] / max(1, total_games), 3),
            "average_turns": round(fmean(turns), 2) if turns else 0,
        },
        "deck_wins": dict(deck_wins),
        "side_wins": dict(side_wins),
        "games": games,
    }


def initiative_report(matchups: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    player_wins = bot_wins = unfinished = games = 0
    for matchup in matchups or []:
        side_wins = matchup.get("side_wins") or {}
        player_wins += int(side_wins.get("player", 0) or 0)
        bot_wins += int(side_wins.get("bot", 0) or 0)
        unfinished += int(side_wins.get("unfinished", 0) or 0)
        games += int(matchup.get("game_count", 0) or 0)
    finished = player_wins + bot_wins
    player_rate = player_wins / max(1, finished)
    return {
        "game_count": games,
        "player_side_win_rate": round(player_rate, 3),
        "bot_side_win_rate": round(bot_wins / max(1, finished), 3),
        "initiative_bias": round(player_rate - 0.5, 3),
        "unfinished_rate": round(unfinished / max(1, games), 3),
    }


def round_robin(
    decks: Mapping[str, Sequence[str]],
    *,
    seeds: Union[int, Sequence[str]] = 10,
    seed_prefix: str = "round-robin",
    bot_profile_id: str = "opportunist",
    max_turns: int = 30,
    simulator: Simulator = simulate_match,
) -> Dict[str, Any]:
    names = sorted(str(name) for name in decks)
    matchups = []
    aggregate = defaultdict(lambda: {"wins": 0, "games": 0})
    matrix: Dict[str, Dict[str, float]] = {name: {} for name in names}
    for left_index, left in enumerate(names):
        for right in names[left_index:]:
            report = paired_matchup(
                decks[left],
                decks[right],
                deck_a_name=left,
                deck_b_name=right,
                seeds=seeds,
                seed_prefix=f"{seed_prefix}:{left}:{right}",
                bot_profile_id=bot_profile_id,
                max_turns=max_turns,
                simulator=simulator,
            )
            matchups.append(report)
            rates = report["summary"]["deck_win_rates"]
            matrix[left][right] = rates[left]
            matrix[right][left] = rates[right]
            aggregate[left]["wins"] += report["deck_wins"].get(left, 0)
            aggregate[left]["games"] += report["game_count"]
            if right != left:
                aggregate[right]["wins"] += report["deck_wins"].get(right, 0)
                aggregate[right]["games"] += report["game_count"]
    standings = [
        {
            "deck": name,
            "wins": aggregate[name]["wins"],
            "games": aggregate[name]["games"],
            "win_rate": round(aggregate[name]["wins"] / max(1, aggregate[name]["games"]), 3),
        }
        for name in names
    ]
    standings.sort(key=lambda row: (-row["win_rate"], row["deck"]))
    return {
        "version": "round-robin-v1",
        "deck_count": len(names),
        "matrix": matrix,
        "standings": standings,
        "initiative": initiative_report(matchups),
        "matchups": matchups,
    }


def dominant_cards(balance_report: Mapping[str, Any]) -> list[Dict[str, Any]]:
    """Cartas marcadas como ``dominant`` pelo lab — base do gate de balance de CI.

    O gate é simples e duro: se o laboratório tático sinaliza qualquer carta
    como dominante (win-rate e dano acima do teto saudável), a build não passa.
    """
    flagged: list[Dict[str, Any]] = []
    for stat in (balance_report or {}).get("card_stats") or []:
        if "dominant" in (stat.get("flags") or []):
            flagged.append(
                {
                    "card_id": stat.get("card_id"),
                    "name": stat.get("name"),
                    "win_rate": stat.get("win_rate"),
                    "avg_damage": stat.get("avg_damage"),
                }
            )
    return flagged

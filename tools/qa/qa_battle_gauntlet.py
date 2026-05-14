#!/usr/bin/env python3
"""Battle Core QA gauntlet for BE2."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from typing import Callable, Dict, List


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.battle_engine_v2 import (  # noqa: E402
    CARD_CATALOG_V2,
    MAX_ROUNDS,
    bot_choose_action,
    choose_intent,
    create_match,
    empty_lanes,
    play_card,
    play_full_bot_match,
    resolve_combat,
    resolve_round,
    stable_match_snapshot,
    start_round,
    validate_match_integrity,
)


def card(card_id: str) -> Dict:
    return deepcopy(CARD_CATALOG_V2[card_id])


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def prepare(seed: int = 5600, bot: bool = False) -> Dict:
    match = create_match(seed=seed, opponent_is_bot=bot)
    start_round(match)
    return match


def scenario_complete_match() -> None:
    match = play_full_bot_match(seed=5601)
    assert_true(match.get("winner") in {"player", "opponent", "draw"}, "complete match should finish")
    ok, errors = validate_match_integrity(match)
    assert_true(ok, f"integrity errors: {errors}")


def scenario_victory() -> None:
    match = prepare(5602)
    match["opponent"]["hp"] = 3
    match["player"]["hand"] = [card("clean_hit")]
    match["player"]["energy"] = 10
    choose_intent(match, "player", "Strike")
    choose_intent(match, "opponent", "Focus")
    play_card(match, "player", card_id="clean_hit", target="enemy_hero")
    match["player"]["ready"] = True
    match["opponent"]["ready"] = True
    resolve_combat(match)
    assert_true(match.get("winner") == "player", "player should win")


def scenario_defeat() -> None:
    match = prepare(5603)
    match["player"]["hp"] = 2
    match["opponent"]["hand"] = [card("spark_runner")]
    match["opponent"]["energy"] = 10
    choose_intent(match, "player", "Focus")
    choose_intent(match, "opponent", "Strike")
    play_card(match, "opponent", card_id="spark_runner", lane="left")
    match["player"]["ready"] = True
    match["opponent"]["ready"] = True
    resolve_combat(match)
    assert_true(match.get("winner") == "opponent", "opponent should win")


def scenario_ready_without_card() -> None:
    match = prepare(5604, bot=True)
    choose_intent(match, "player", "Focus")
    match["player"]["hand"] = []
    match["player"]["ready"] = True
    resolve_round(match)
    assert_true(match["round"] >= 2 or match.get("winner"), "ready without card should advance")


def scenario_invalid_card() -> None:
    match = prepare(5605)
    choose_intent(match, "player", "Strike")
    try:
        play_card(match, "player", card_id="not-real")
    except ValueError:
        return
    raise AssertionError("invalid card should be rejected")


def scenario_invalid_target() -> None:
    match = prepare(5606)
    match["player"]["hand"] = [card("clean_hit")]
    match["player"]["energy"] = 10
    choose_intent(match, "player", "Strike")
    try:
        play_card(match, "player", card_id="clean_hit", target="lane:diagonal")
    except ValueError:
        return
    raise AssertionError("invalid target should be rejected")


def scenario_lane_full() -> None:
    match = prepare(5607)
    match["player"]["hand"] = [card("spark_runner"), card("street_challenger")]
    match["player"]["energy"] = 10
    choose_intent(match, "player", "Strike")
    play_card(match, "player", card_id="spark_runner", lane="left")
    match["player"]["played_card"] = None
    match["player"]["played_this_round"] = False
    try:
        play_card(match, "player", card_id="street_challenger", lane="left")
    except ValueError:
        return
    raise AssertionError("full lane should be rejected")


def scenario_energy_insufficient() -> None:
    match = prepare(5608)
    match["player"]["hand"] = [card("arena_brute")]
    match["player"]["energy"] = 0
    choose_intent(match, "player", "Strike")
    try:
        play_card(match, "player", card_id="arena_brute", lane="center")
    except ValueError:
        return
    raise AssertionError("insufficient energy should be rejected")


def scenario_spell_lane_target() -> None:
    match = prepare(5609)
    match["player"]["hand"] = [card("clean_hit")]
    match["opponent"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    match["opponent"]["energy"] = 10
    choose_intent(match, "player", "Strike")
    choose_intent(match, "opponent", "Focus")
    play_card(match, "opponent", card_id="spark_runner", lane="left")
    play_card(match, "player", card_id="clean_hit", target="lane:left")
    assert_true(match["opponent"]["board"]["left"] is None, "lane spell should remove defeated creature")


def scenario_guard_trap() -> None:
    match = prepare(5610)
    match["player"]["hand"] = [card("hold_position")]
    match["player"]["energy"] = 10
    choose_intent(match, "player", "Guard")
    play_card(match, "player", card_id="hold_position", target="self")
    assert_true(match["player"]["shield"] >= 7, "guard card should grant boosted shield")


def scenario_simultaneous_death() -> None:
    match = prepare(5611)
    match["player"]["hand"] = [card("spark_runner")]
    match["opponent"]["hand"] = [card("spark_runner")]
    match["player"]["energy"] = 10
    match["opponent"]["energy"] = 10
    choose_intent(match, "player", "Strike")
    choose_intent(match, "opponent", "Strike")
    play_card(match, "player", card_id="spark_runner", lane="center")
    play_card(match, "opponent", card_id="spark_runner", lane="center")
    match["player"]["ready"] = True
    match["opponent"]["ready"] = True
    resolve_combat(match)
    assert_true(match["player"]["board"]["center"] is None, "player creature should die")
    assert_true(match["opponent"]["board"]["center"] is None, "opponent creature should die")


def scenario_seed_deterministic() -> None:
    first = play_full_bot_match(seed=5612)
    second = play_full_bot_match(seed=5612)
    assert_true(stable_match_snapshot(first) == stable_match_snapshot(second), "same seed should match")


def scenario_bot_no_playable() -> None:
    match = prepare(5613, bot=True)
    match["opponent"]["hand"] = [card("arena_brute")]
    match["opponent"]["energy"] = 0
    bot_choose_action(match)
    assert_true(match["opponent"]["ready"] is True, "bot should ready with no playable card")


def scenario_max_rounds_no_loop() -> None:
    match = play_full_bot_match(seed=5614)
    assert_true(int(match.get("round") or 0) <= MAX_ROUNDS + 1, "match should respect max rounds")


SCENARIOS: List[tuple[str, Callable[[], None]]] = [
    ("partida completa", scenario_complete_match),
    ("vitória", scenario_victory),
    ("derrota", scenario_defeat),
    ("ready sem carta", scenario_ready_without_card),
    ("carta inválida", scenario_invalid_card),
    ("target inválido", scenario_invalid_target),
    ("lane cheia", scenario_lane_full),
    ("energia insuficiente", scenario_energy_insufficient),
    ("spell em alvo correto", scenario_spell_lane_target),
    ("trap/guard funcionando", scenario_guard_trap),
    ("morte simultânea", scenario_simultaneous_death),
    ("seed determinística", scenario_seed_deterministic),
    ("bot sem carta jogável", scenario_bot_no_playable),
    ("max rounds sem loop infinito", scenario_max_rounds_no_loop),
]


def main() -> int:
    failures = []
    print("=== BE2 Battle QA Gauntlet ===")
    for name, scenario in SCENARIOS:
        try:
            scenario()
            print(f"PASS {name}")
        except Exception as error:
            failures.append((name, error))
            print(f"FAIL {name}: {type(error).__name__}: {error}")

    if failures:
        print(f"FAIL {len(failures)} scenario(s)")
        return 1

    print("PASS battle_gauntlet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

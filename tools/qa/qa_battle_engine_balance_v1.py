# =========================================================
# QA Battle Engine Balance V1
# Mede distribuição de vitórias, empates e motivos.
# =========================================================

from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.battle_engine_v1 import (
    MAX_ROUNDS,
    play_full_bot_match,
    validate_match_integrity,
)


def main():
    total = 500
    winners = Counter()
    reasons = Counter()
    rounds = []
    bad_matches = []

    for seed in range(total):
        match = play_full_bot_match(seed=seed)
        ok, errors = validate_match_integrity(match)

        if not ok:
            bad_matches.append((seed, errors))

        winners[match["winner"]] += 1
        reasons[match["reason"]] += 1
        rounds.append(match["round"])

    avg_rounds = sum(rounds) / len(rounds)
    min_rounds = min(rounds)
    max_rounds = max(rounds)

    print("=== BATTLE ENGINE BALANCE V1 ===")
    print(f"Matches: {total}")
    print(f"Average rounds: {avg_rounds:.2f}")
    print(f"Min rounds: {min_rounds}")
    print(f"Max rounds: {max_rounds}")
    print("")
    print("Winners:")
    for key, value in winners.items():
        print(f"- {key}: {value} ({value / total:.1%})")

    print("")
    print("Reasons:")
    for key, value in reasons.items():
        print(f"- {key}: {value} ({value / total:.1%})")

    print("")
    if bad_matches:
        print("INTEGRITY FAILURES:")
        for seed, errors in bad_matches[:20]:
            print(f"- seed {seed}: {errors}")
        raise SystemExit(1)

    draw_count = winners.get("draw", 0)
    if draw_count > total * 0.08:
        print("")
        print(f"BALANCE_WARNING: draw rate too high: {draw_count / total:.1%}")
        raise SystemExit(2)

    if max_rounds >= MAX_ROUNDS:
        print("")
        print("BALANCE_WARNING: at least one match reached max rounds")
        raise SystemExit(3)

    print("PASS: balance distribution is acceptable")


if __name__ == "__main__":
    main()

"""Item 6: P0.1 regression guard — a casual player must keep a board.

The "olhos-de-jogador" audit (2026-06-11) P0.1 was: a casual player never has a
board (presence ~0-1), losing helplessly (WR ~0.17). The casual lab now drives
through the real dispatcher; this locks the floor so the impotence bug can't
silently return. (Note: WR currently overshoots the 0.40-0.60 health band — see
docs/REBIRTH_P01_REVALIDATION.md — that is a tuning nudge, not impotence.)
"""
from services.rebirth_balance import simulate_casual_balance


def test_casual_player_keeps_board_and_is_not_impotent():
    report = simulate_casual_balance(matches=60)
    summary = report["summary"]
    # P0.1 floor: casual board presence stays >= 1.0 (was ~0 at the bug).
    assert summary["board_presence"] >= 1.0, summary
    # …and the casual player is not impotent (WR was ~0.17 at the bug).
    assert summary["player_win_rate"] >= 0.40, summary
    # Every bot profile keeps the floor (no single profile wipes the board).
    for profile in report["profile_results"]:
        assert profile["board_presence"] >= 1.0, profile

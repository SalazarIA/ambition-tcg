# Ambitionz Rebirth Balance Watchlist

Generated: 2026-06-02 local Season 0 lab.

## Simulation Snapshot

- Command: `python3 tools/rebirth_balance_report.py --matches 200 --output docs/REBIRTH_BALANCE_REPORT.md`
- total_matches: 200
- player_win_rate: 47.5%
- bot_win_rate: 51.5%
- unfinished_rate: 1.0%
- average_turns: 15.77

## Bot Profiles

- defensive: 67 matches, player WR 47.8%, bot WR 52.2%, avg turns 18.18
- aggressive: 67 matches, player WR 47.8%, bot WR 50.7%, avg turns 14.37
- opportunist: 66 matches, player WR 47.0%, bot WR 51.5%, avg turns 14.74

## Catalog Coverage

- total_cards: 103
- used_cards: 103
- unused_cards: 0
- cards_above_30_percent_dead_rate: 0
- supports_above_30_percent_dead_rate: 0
- flagged_dominant_or_low_impact_cards: 0

## Former Unused Card Investigation

- Aegis Sentinel: 56 plays, 56 match uses, 42.9% WR, 0.2 avg damage.
- Infernus Core: 21 plays, 21 match uses, 14.3% WR, 0.48 avg damage.
- Shadow Reaper: 11 plays, 11 match uses, 18.2% WR, 0.45 avg damage.
- Recarga Arcana: 40 plays, 40 match uses, 37.5% WR, 0 avg damage.

## Current Notes

- The defensive profile is now below the 52% ideal player-WR target in the deterministic lab.
- The old dominant/low-impact flags were removed by better catalog coverage and stricter signal thresholds.
- Infernus Core and Shadow Reaper are used but still low-win in deterministic play; keep them on the live telemetry watchlist before changing card text.
- This lab is deterministic and useful for regression detection, but it is not a substitute for human closed-beta telemetry.

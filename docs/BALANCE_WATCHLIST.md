# Ambitionz Beta Balance Watchlist

Generated: 2026-05-16 01:26 UTC

## Simulation Snapshot

- total_matches: 100
- player_wins: 50
- bot_wins: 50
- win_rate: 0.5
- average_rounds: 13.91
- timeout_count: 0
- integrity_error_count: 0

## Intent Signals

- bot:Guard: 520
- bot:Strike: 871
- player:Focus: 100
- player:Guard: 308
- player:Strike: 983

## Top Cards Played

- water_002: 126
- plant_005: 126
- fire_005: 124
- earth_002: 122
- fire_002: 119
- fire_007: 118
- plant_006: 117
- earth_003: 116
- earth_005: 115
- fire_003: 114

## Local Telemetry

- total_events: 1464
- db_source: ok
- jsonl_source: checked instance/beta_telemetry.jsonl, logs/beta_telemetry.jsonl
- buy_booster: 0
- claim_daily: 0
- finish_match: 1
- open_booster: 0
- save_deck: 0
- start_training: 38
- view_collection: 0
- view_roadmap: 0
- visit_home: 0

## Alerts

- Intent variety may be narrow in telemetry: Strike is over 75% of tracked intent events.

## Notes

- This watchlist is local and defensive; it does not require an external analytics provider.
- RC V6 includes Intent Balance V2: Strike is leaner, Guard absorbs more damage and Focus generates clearer Ambition value.
- Confirm post-deploy telemetry before declaring Strike usage fixed; local historical events may still overrepresent old behavior.
- Gold, boosters and rewards are internal beta systems with no real-money payment flow.
- Use this file to decide what to inspect before changing card balance or bot behavior.

# Persist Arena V1 Rewards + Match History Integration

Implemented:
- services/match_rewards_v1.py
- reward preview now comes from reward service
- claim_match_rewards_v1 socket event
- auto persist reward after V1 match finish
- reward_result socket event in Arena App
- reward modal triggers claim
- MatchHistory V1 persistence service
- match_history page visual polish

Backup:
backups/persist_rewards_match_history_20260506_170209

Important:
- Rewards are protected against duplicate claims per active match object.
- Persistent idempotency across server restarts can be added later with a reward ledger table.

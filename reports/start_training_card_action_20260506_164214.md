# Start Training Contract + Real Card Action Contract

Implemented:
- services/match_actions_v1.py
- start_training socket handler
- play_card socket handler
- declare_ready socket handler
- set_intent V1 early path
- request_match_state auto-starts training when no active match exists
- arena_app.js emits start_training on /training
- tools/start_training_action_audit.py

Backup:
backups/start_training_card_action_20260506_164214

Expected result:
- /training creates a V1 match.
- match_state includes starting hand.
- clicking playable card moves it from hand to field.
- Ready resolves a simple training round.

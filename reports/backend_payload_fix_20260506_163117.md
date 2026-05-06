# Backend Payload Fix — Arena V8

Implemented:
- services/arena_payload.py
- Canonical arena_state_v8 payload
- me.hand / hand / my_hand included
- enemy hand count included
- me/enemy stats included
- me/enemy field included
- app.py helper emit_arena_state_v8
- bridge listens to arena_state_update
- tools/arena_payload_audit.py

Backup: backups/backend_payload_fix_20260506_163117

Next:
- Real browser QA on /training.
- If duplicated game_state_update causes too many events, switch frontend to arena_state_update only.

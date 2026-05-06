# Restore Arena + Engine Audit

Implemented:
- Disabled visual overlay layers from templates/arena.html.
- Preserved overlay files in repository.
- Created tools/engine_contract_audit.py.
- This prepares the fullstack arena rebuild.

Overlays disabled:
- arena_v7
- arena_v5
- arena_state_bridge
- arena_animations
- ambitionz_tutorial

Backup:
backups/restore_and_engine_audit_20260506_163741

Next:
- Run Engine Contract Audit.
- Build match_state_v1 backend.
- Build arena_app frontend.

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.arena_training_actions import (
    create_training_match,
    build_training_payload,
    play_card,
    set_intent,
    declare_ready,
)


class User:
    id = 1
    username = "audit_player"


match = create_training_match(User(), "sid_audit", "room_audit")

state = build_training_payload(match, "p1")
print("# Start Training Action Audit")
print("initial_hand", len(state["me"]["hand"]))
print("initial_energy", state["me"]["energy"])
print("initial_phase", state["phase"])

if not state["me"]["hand"]:
    raise SystemExit("FAILED: no starting hand")

card_id = (state["legal_actions"].get("playable_card_ids") or [state["me"]["hand"][0]["id"]])[0]

ok, message = set_intent(match, "p1", "Strike")
print("set_intent", ok, message)

if not ok:
    raise SystemExit("FAILED: set_intent")

ok, message = play_card(match, "p1", card_id)
print("play_card", ok, message)

if not ok:
    raise SystemExit("FAILED: play_card")

state = build_training_payload(match, "p1")
print("hand_after_play", len(state["me"]["hand"]))
print("monster_slot", bool(state["me"]["field"]["monster"] or state["me"]["field"]["spell"] or state["me"]["field"]["trap"]))

ok, message = declare_ready(match, "p1")
print("declare_ready", ok, message)

if not ok:
    raise SystemExit("FAILED: declare_ready")

state = build_training_payload(match, "p1")
print("round_after_ready", state["round"])
print("phase_after_ready", state["phase"])
print("message", state["message"])

print("START_TRAINING_ACTION_AUDIT_PASSED")

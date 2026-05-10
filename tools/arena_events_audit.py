from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.arena_training_actions import (
    create_training_match,
    build_training_payload,
    set_intent,
    play_card,
    declare_ready,
)


class User:
    id = 1
    username = "audit_player"


match = create_training_match(User(), "sid", "room")
payload = build_training_payload(match, "p1")
card_id = (payload["legal_actions"].get("playable_card_ids") or [payload["me"]["hand"][0]["id"]])[0]

set_intent(match, "p1", "Strike")
play_card(match, "p1", card_id)
declare_ready(match, "p1")

payload = build_training_payload(match, "p1")

print("# Arena Events Audit")
print("log_count", len(payload.get("log", [])))

for line in payload.get("log", []):
    print(line)

log_text = "\n".join(payload.get("log", []))

required = ["chose Strike", "Round 1", "dealt"]

missing = [needle for needle in required if needle not in log_text]

if not any(needle in log_text for needle in ["summoned", "cast", "played support", "replaced"]):
    missing.append("card action")

if missing:
    raise SystemExit(f"FAILED: missing BE2 log markers {missing}")

print("ARENA_EVENTS_AUDIT_PASSED")

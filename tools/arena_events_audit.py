from services.match_actions_v1 import (
    create_training_match_v1,
    set_intent,
    play_card,
    declare_ready,
)
from services.match_state_v1 import build_match_state_v1


class User:
    id = 1
    username = "audit_player"


match = create_training_match_v1(User(), "sid", "room")
payload = build_match_state_v1(match, "p1")
card_id = payload["me"]["hand"][0]["id"]

set_intent(match, "p1", "Strike")
play_card(match, "p1", card_id)
declare_ready(match, "p1")

payload = build_match_state_v1(match, "p1")

print("# Arena Events Audit")
print("events_count", len(payload.get("events", [])))

for event in payload.get("events", []):
    print(event)

types = {event.get("type") for event in payload.get("events", [])}

required = {"set_intent", "play_card", "declare_ready", "resolve_round"}

missing = required - types

if missing:
    raise SystemExit(f"FAILED: missing events {missing}")

print("ARENA_EVENTS_AUDIT_PASSED")

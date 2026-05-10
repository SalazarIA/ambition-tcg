from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.arena_training_actions import create_training_match, build_training_payload


class User:
    id = 1
    username = "audit_player"


match = create_training_match(User(), "sid", "room")
payload = build_training_payload(match, "p1")

print("# Arena Card Stats Audit")
print("hand_count", len(payload["me"]["hand"]))

if not payload["me"]["hand"]:
    raise SystemExit("FAILED: no cards in hand")

for card in payload["me"]["hand"][:5]:
    print(card["name"], {
        "type": card.get("type"),
        "cost": card.get("cost"),
        "power": card.get("power"),
        "attack": card.get("attack"),
        "defense": card.get("defense"),
        "value": card.get("value"),
        "combat_label": card.get("combat_label"),
    })

    if card.get("type") == "Monster" and int(card.get("attack") or 0) <= 0:
        raise SystemExit(f"FAILED: monster without attack: {card.get('name')}")

print("ARENA_CARD_STATS_AUDIT_PASSED")

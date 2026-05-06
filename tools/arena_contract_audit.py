from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app
from models import User
from services.match_actions_v1 import create_training_match_v1, play_card
from services.arena_clean_state import build_arena_clean_state


def check_payload(label, payload):
    print("")
    print("===", label, "===")
    print("schema", payload.get("schema"))
    print("phase", payload.get("phase"))
    print("message", payload.get("message"))
    print("me.hand", len((payload.get("me") or {}).get("hand") or []))
    print("enemy.hand_count", (payload.get("enemy") or {}).get("hand_count"))
    print("legal", payload.get("legal_actions"))

    hand = (payload.get("me") or {}).get("hand") or []

    for index, card in enumerate(hand[:5], start=1):
        print(
            "HAND",
            index,
            card.get("id"),
            card.get("name"),
            card.get("type"),
            "cost", card.get("cost"),
            "power", card.get("power"),
            "display", card.get("display_stat"),
        )

    broken = [
        card
        for card in hand
        if card.get("type") == "Monster" and int(card.get("power") or 0) <= 0
    ]

    if broken:
        raise SystemExit(f"FAILED - monster card in hand with zero power: {broken[:3]}")


with app.app_context():
    user = User.query.first()

    if not user:
        print("SKIP - no user.")
        raise SystemExit(0)

    match = create_training_match_v1(user, "AUDIT_SID", "audit_room")

    payload = build_arena_clean_state(match, "p1")
    check_payload("initial", payload)

    first_card = payload["me"]["hand"][0]
    ok, msg = play_card(match, "p1", first_card["id"])
    print("")
    print("play_card", ok, msg)

    payload2 = build_arena_clean_state(match, "p1", message=msg)
    check_payload("after_play_card", payload2)

    if len(payload2["me"]["hand"]) != 4:
        raise SystemExit("FAILED - hand did not decrease to 4 after play card")

    monster = payload2["me"]["field"]["monster"]
    if not monster:
        raise SystemExit("FAILED - monster not in field after play card")

    if int(monster.get("power") or 0) <= 0:
        raise SystemExit("FAILED - field monster has zero power")

    print("")
    print("ARENA_CONTRACT_AUDIT_PASSED")

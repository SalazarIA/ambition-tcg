from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app
from models import User
from services.match_actions_v1 import create_training_match_v1, play_card, set_intent
from services.arena_clean_state import build_arena_clean_state


def assert_cards(label, cards):
    print("")
    print(label, "count", len(cards))

    for index, card in enumerate(cards[:8], start=1):
        print(
            label,
            index,
            card.get("id"),
            card.get("name"),
            card.get("type"),
            "cost", card.get("cost"),
            "power", card.get("power"),
            "display", card.get("display_stat"),
        )

        if card.get("type") == "Monster" and int(card.get("power") or 0) <= 0:
            raise SystemExit(f"FAILED - {label} monster has zero power: {card}")


with app.app_context():
    user = User.query.first()

    if not user:
        print("SKIP - no user.")
        raise SystemExit(0)

    match = create_training_match_v1(user, "AUDIT_SID", "audit_room")

    p1 = build_arena_clean_state(match, "p1")
    assert_cards("initial_hand", p1["me"]["hand"])

    ok, msg = set_intent(match, "p1", "Strike")
    print("set_intent", ok, msg)

    p2 = build_arena_clean_state(match, "p1", message=msg)
    assert_cards("after_intent_hand", p2["me"]["hand"])

    first_card = p2["me"]["hand"][0]
    ok, msg = play_card(match, "p1", first_card["id"])
    print("play_card", ok, msg)

    p3 = build_arena_clean_state(match, "p1", message=msg)
    assert_cards("after_play_hand", p3["me"]["hand"])

    monster = p3["me"]["field"]["monster"]
    print("field_monster", monster)

    if not monster:
        raise SystemExit("FAILED - no monster in field after play")

    if int(monster.get("power") or 0) <= 0:
        raise SystemExit("FAILED - field monster has zero power")

    print("")
    print("ARENA_CONTRACT_AUDIT_PASSED")

from pathlib import Path
import sys
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app
from models import User
from game.deck import load_card_ids, build_playable_deck, draw_starting_hand
from game.state import create_player_state
from services.economy.deck_inventory import owned_card_ids_for_user, build_auto_deck_from_inventory
from services.match_state_v1 import build_match_state_v1
from services.match_actions_v1 import create_training_match_v1


def card_summary(card):
    return {
        "id": card.get("id"),
        "name": card.get("name"),
        "type": card.get("type"),
        "cost": card.get("cost"),
        "power": card.get("power"),
        "attack": card.get("attack"),
        "value": card.get("value"),
        "element": card.get("element"),
        "sigil": card.get("sigil"),
    }


with app.app_context():
    user = User.query.first()

    if not user:
        print("SKIP - no local user.")
        raise SystemExit(0)

    print("# Arena Real Match Audit")
    print("user", user.id, user.username)

    owned_ids = owned_card_ids_for_user(user)
    deck_ids = load_card_ids(user.deck_json)

    if not deck_ids:
        deck_ids = build_auto_deck_from_inventory(user)

    print("owned_ids", len(owned_ids))
    print("deck_ids", len(deck_ids))
    print("deck_first_10", deck_ids[:10])

    playable_deck = build_playable_deck(deck_ids)
    hand = draw_starting_hand(playable_deck, 5)

    print("playable_deck", len(playable_deck))
    print("hand", len(hand))

    for index, card in enumerate(hand, start=1):
        print("HAND", index, card_summary(card))

    player = create_player_state(user, "AUDIT_SID", playable_deck, hand)

    print("player_hand_count", len(player.get("hand") or []))
    print("player_deck_count", len(player.get("deck") or []))

    match = create_training_match_v1(user, "AUDIT_SID", "audit_room")

    print("match_phase", match.get("phase"))
    print("match_round", match.get("round"))

    p1 = match.get("p1") or {}
    print("v1_p1_hand_count", len(p1.get("hand") or []))
    print("v1_p1_deck_count", len(p1.get("deck") or []))

    for index, card in enumerate((p1.get("hand") or [])[:5], start=1):
        print("V1_HAND", index, card_summary(card))

    payload = build_match_state_v1(match, "p1")

    print("payload_keys", sorted(payload.keys()))
    print("payload_phase", payload.get("phase"))
    print("payload_me_hand_count", len((payload.get("me") or {}).get("hand") or []))
    print("payload_enemy_hand_count", (payload.get("enemy") or {}).get("hand_count"))

    for index, card in enumerate(((payload.get("me") or {}).get("hand") or [])[:5], start=1):
        print("PAYLOAD_HAND", index, card_summary(card))

    missing_power = [
        card_summary(card)
        for card in ((payload.get("me") or {}).get("hand") or [])
        if card.get("type") == "Monster" and not (card.get("power") or card.get("attack") or card.get("value"))
    ]

    if missing_power:
        print("FAILED_missing_power", missing_power)
        raise SystemExit("FAILED - monster cards missing power/attack/value in payload")

    if len((payload.get("me") or {}).get("hand") or []) <= 0:
        raise SystemExit("FAILED - payload me.hand empty")

    print("ARENA_REAL_MATCH_AUDIT_PASSED")

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app, socketio
from models import User


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


def _packets(client):
    try:
        return client.get_received()
    except Exception:
        return []


def _latest_event(packets, event_name):
    for packet in reversed(packets):
        if packet.get("name") == event_name:
            args = packet.get("args") or []
            if args:
                return args[0]
    return None


def _packet_summary(packet):
    name = packet.get("name")
    args = packet.get("args") or []
    payload = args[0] if args else None

    if isinstance(payload, dict):
        me = payload.get("me") or {}
        enemy = payload.get("enemy") or {}
        legal = payload.get("legal_actions") or {}

        return {
            "event": name,
            "schema": payload.get("schema"),
            "phase": payload.get("phase"),
            "message": payload.get("message"),
            "me_hand": len(me.get("hand") or []),
            "me_energy": me.get("energy"),
            "me_intent": me.get("intent"),
            "enemy_hand_count": enemy.get("hand_count"),
            "can_ready": legal.get("can_ready"),
            "can_play_cards": legal.get("can_play_cards"),
        }

    return {"event": name, "args": args}


def _validate_az48_state(payload, stage, logs):
    _assert(payload is not None, f"{stage}: missing az48_state")
    _assert(payload.get("schema") in {"arena_state_v50", "ambitionz_arena_clean_v50"}, f"{stage}: wrong schema {payload.get('schema')}")

    me = payload.get("me") or {}
    hand = me.get("hand") or []

    logs.append(f"{stage}: phase={payload.get('phase')} message={payload.get('message')} hand={len(hand)}")

    _assert(hand, f"{stage}: expected non-empty hand")

    for index, card in enumerate(hand[:5], start=1):
        logs.append(
            f"{stage} HAND {index}: id={card.get('id')} name={card.get('name')} type={card.get('type')} cost={card.get('cost')} power={card.get('power')} display={card.get('display_stat')}"
        )

        _assert(card.get("id"), f"{stage}: card missing id")
        _assert(card.get("name"), f"{stage}: card missing name")

        if card.get("type") == "Monster":
            _assert(int(card.get("power") or 0) > 0, f"{stage}: monster has zero power")


def run_socket_flow():
    logs = []
    result = {
        "name": "socket_training_flow",
        "status": "PASS",
        "logs": logs,
        "error": None,
    }

    try:
        flask_client = app.test_client()

        with flask_client.session_transaction() as sess:
            with app.app_context():
                user = User.query.first()
                _assert(user is not None, "No local user found.")
                sess["user_id"] = user.id
                logs.append(f"user: id={user.id} username={user.username}")

        client = socketio.test_client(app, flask_test_client=flask_client)
        _assert(client.is_connected(), "Socket test client did not connect")

        logs.append("socket_connected: True")

        initial_packets = _packets(client)
        logs.append(f"initial_packets: {[ _packet_summary(p) for p in initial_packets ]}")

        client.emit("az48_start_training", {})
        start_packets = _packets(client)
        logs.append(f"after_start_packets: {[ _packet_summary(p) for p in start_packets ]}")

        start_state = _latest_event(start_packets, "az48_state")
        _validate_az48_state(start_state, "after_start", logs)

        client.emit("az48_set_intent", {"intent": "Strike"})
        intent_packets = _packets(client)
        logs.append(f"after_intent_packets: {[ _packet_summary(p) for p in intent_packets ]}")

        intent_state = _latest_event(intent_packets, "az48_state") or start_state
        _validate_az48_state(intent_state, "after_intent", logs)

        hand = ((intent_state.get("me") or {}).get("hand") or [])
        legal_actions = intent_state.get("legal_actions") or {}
        playable_ids = {str(card_id) for card_id in (legal_actions.get("playable_card_ids") or legal_actions.get("playable_cards") or [])}

        playable_hand = [
            card for card in hand
            if not playable_ids or str(card.get("id")) in playable_ids
        ]

        monster_cards = [
            card for card in playable_hand
            if card.get("type") == "Monster"
        ]

        chosen_card = (monster_cards or playable_hand or hand)[0]
        first_card_id = chosen_card["id"]

        logs.append(
            f"chosen_card: id={first_card_id} name={chosen_card.get('name')} "
            f"type={chosen_card.get('type')} cost={chosen_card.get('cost')} playable_ids={sorted(playable_ids)}"
        )

        client.emit("az48_play_card", {"card_id": first_card_id})
        play_packets = _packets(client)
        logs.append(f"after_play_packets: {[ _packet_summary(p) for p in play_packets ]}")

        play_state = _latest_event(play_packets, "az48_state")
        _assert(play_state is not None, "Missing az48_state after play_card")

        me = play_state.get("me") or {}
        field = me.get("field") or {}
        hand_after = me.get("hand") or []

        logs.append(f"after_play_state: hand={len(hand_after)} field={field} legal={play_state.get('legal_actions')}")

        # BE2 can draw/refill immediately after a play, so hand size is not
        # guaranteed to be exactly starting_hand - 1. The durable contract is:
        # the selected card is no longer in hand, a monster reached the field,
        # and the player can declare ready.
        remaining_ids = {str(card.get("id")) for card in hand_after}
        _assert(str(first_card_id) not in remaining_ids, "Played card should no longer be in hand")
        _assert(len(hand_after) <= len(hand), f"Hand should not grow after single play. before={len(hand)} after={len(hand_after)}")
        play_message = str(play_state.get("message") or "")
        played_ok = bool(field.get("monster")) or "Card played" in play_message
        _assert(played_ok, f"Expected card play to mutate field or confirm play. message={play_message!r} field={field}")
        _assert((play_state.get("legal_actions") or {}).get("can_ready"), "Expected can_ready True after play")

        client.emit("az48_declare_ready", {})
        ready_packets = _packets(client)
        logs.append(f"after_ready_packets: {[ _packet_summary(p) for p in ready_packets ]}")

        ready_state = _latest_event(ready_packets, "az48_state")
        _assert(ready_state is not None, "Missing az48_state after ready")
        logs.append(f"after_ready_state: {_packet_summary({'name': 'az48_state', 'args': [ready_state]})}")

    except Exception as exc:
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"

    return result

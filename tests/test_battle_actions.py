from services.match_payloads import find_player_key
from sockets.battle_actions import BattleActionController


class FakeSocketIO:
    def __init__(self):
        self.emitted = []

    def emit(self, event, payload, to=None):
        self.emitted.append((event, payload, to))


class FakeRuntime:
    def __init__(self):
        self.active_matches = {}
        self.player_rooms = {}
        self.allowed_events = []
        self.released_matches = []
        self.bot_turns = []
        self.allow_events = True

    def allow_socket_event(self, event_name, **kwargs):
        self.allowed_events.append((event_name, kwargs))
        return self.allow_events

    def play_bot_turn_if_needed(self, match, room_id, player_key):
        self.bot_turns.append((room_id, player_key))
        match["p2"]["ready"] = True

    def release_match_presence(self, match):
        self.released_matches.append(match)


class User:
    id = 1


def make_player(name="Player", sid="sid-p1"):
    return {
        "name": name,
        "sid": sid,
        "ready": False,
        "energy": 2,
        "hand": [
            {"id": "m1", "name": "Spark Adept", "type": "Monster", "cost": 1},
        ],
        "field_m": None,
        "field_st": None,
        "wants_unleash": False,
        "can_unleash": True,
        "intent": "Strike",
    }


def make_controller():
    socketio = FakeSocketIO()
    runtime = FakeRuntime()
    logs = []
    states = []
    missions = []
    battle_events = []
    ended_matches = []

    def emit_log(room_id, message):
        logs.append((room_id, message))

    def emit_state(room_id):
        states.append(room_id)

    def request_unleash(player):
        if not player.get("can_unleash", False):
            return False

        player["wants_unleash"] = True
        return True

    deps = {
        "can_pay_cost": lambda player, card: int(player.get("energy", 0)) >= int(card.get("cost", 1)),
        "cancel_unleash": lambda player: player.update({"wants_unleash": False}),
        "current_user": lambda: User(),
        "emit_battle_events": lambda match, events: battle_events.append((match, events)),
        "emit_log": emit_log,
        "emit_state": emit_state,
        "end_match": lambda room_id, winner_key: ended_matches.append((room_id, winner_key)),
        "find_player_key": find_player_key,
        "increment_mission": lambda user, mission, amount: missions.append((user.id, mission, amount)),
        "normalize_intent": lambda intent: intent if intent in {"Strike", "Guard", "Focus"} else "Strike",
        "pay_card_cost": lambda player, card: player.update({"energy": player["energy"] - int(card.get("cost", 1))}),
        "register_card_played_for_ambition": lambda player, card, match_logs: match_logs.append(f"played:{card['id']}"),
        "request_unleash": request_unleash,
        "resolve_battle": lambda match: {
            "logs": ["Battle resolved."],
            "winner": "p1",
            "events": [{"type": "damage", "amount": 100}],
        },
        "set_player_intent": lambda player, intent: player.update({"intent": intent}),
    }

    controller = BattleActionController(socketio, deps, runtime)
    return controller, runtime, socketio, logs, states, missions, battle_events, ended_matches


def attach_match(runtime, p1=None, p2=None, *, room_id="room-1"):
    p1 = p1 or make_player("Alice", "sid-p1")
    p2 = p2 or make_player("Bob", "sid-p2")
    match = {
        "p1": p1,
        "p2": p2,
        "resolving": False,
        "logs": [],
    }
    runtime.active_matches[room_id] = match
    runtime.player_rooms[p1["sid"]] = room_id
    runtime.player_rooms[p2["sid"]] = room_id
    return match


def test_play_to_field_moves_monster_and_pays_cost():
    controller, runtime, _socketio, logs, states, _missions, _battle_events, _ended_matches = make_controller()
    match = attach_match(runtime)

    controller.play_to_field("sid-p1", {"index": 0})

    player = match["p1"]
    assert player["energy"] == 1
    assert player["field_m"]["id"] == "m1"
    assert player["hand"] == []
    assert match["logs"] == ["played:m1"]
    assert logs == [("room-1", "Alice set a monster: Spark Adept for 1 energy.")]
    assert states == ["room-1"]


def test_choose_intent_unleash_success_logs_and_tracks_mission():
    controller, runtime, _socketio, logs, states, missions, _battle_events, _ended_matches = make_controller()
    match = attach_match(runtime)

    controller.choose_intent("sid-p1", {"intent": "Overreach"})

    assert match["p1"]["wants_unleash"] is True
    assert missions == [(1, "use_overreach_1", 1)]
    assert logs == [("room-1", "Alice prepared Ambition Unleash for this battle.")]
    assert states == ["room-1"]


def test_set_intent_unleash_failure_sends_private_message():
    controller, runtime, socketio, _logs, states, missions, _battle_events, _ended_matches = make_controller()
    player = make_player("Alice", "sid-p1")
    player["can_unleash"] = False
    attach_match(runtime, p1=player)

    controller.set_intent("sid-p1", {"intent": "Ambition Unleash"})

    assert missions == []
    assert socketio.emitted == [
        (
            "battle_log",
            {"msg": "You need 5 Ambition and a monster on the field to unleash."},
            "sid-p1",
        )
    ]
    assert states == ["room-1"]


def test_declare_ready_resolves_battle_and_ends_match():
    controller, runtime, _socketio, logs, states, missions, battle_events, ended_matches = make_controller()
    p2 = make_player("Bob", "sid-p2")
    p2["ready"] = True
    match = attach_match(runtime, p2=p2)

    controller.declare_ready("sid-p1")

    assert match["p1"]["ready"] is True
    assert missions == [(1, "declare_ready_1", 1)]
    assert logs == [
        ("room-1", "Alice is ready."),
        ("room-1", "Battle resolved."),
    ]
    assert states == ["room-1", "room-1"]
    assert battle_events == [(match, [{"type": "damage", "amount": 100}])]
    assert match["v2_events"] == [{"type": "damage", "amount": 100}]
    assert ended_matches == [("room-1", "p1")]
    assert runtime.released_matches == [match]

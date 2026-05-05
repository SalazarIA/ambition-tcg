from sockets.matchmaking import MatchmakingController
from sockets.runtime import GameSocketRuntime


class FakeServer:
    def __init__(self):
        self.rooms = []

    def enter_room(self, sid, room_id, namespace="/"):
        self.rooms.append((sid, room_id, namespace))


class FakeSocketIO:
    def __init__(self):
        self.server = FakeServer()
        self.emitted = []
        self.background_tasks = []

    def emit(self, event, payload, to=None):
        self.emitted.append((event, payload, to))

    def start_background_task(self, fn, *args):
        self.background_tasks.append((fn, args))

    def sleep(self, seconds):
        return None


class User:
    def __init__(self, user_id=1, username="Player", deck_json="[]"):
        self.id = user_id
        self.username = username
        self.deck_json = deck_json


def make_player(name="Player", sid="sid-a", user_id=1):
    return {
        "name": name,
        "sid": sid,
        "user_id": user_id,
        "ready": False,
    }


def make_controller():
    socketio = FakeSocketIO()
    logs = []
    states = []
    events = []

    def create_player_object(user, sid):
        return make_player(
            name=getattr(user, "username", "Bot"),
            sid=sid,
            user_id=getattr(user, "id", None),
        )

    deps = {
        "active_matches": {},
        "player_rooms": {},
        "private_waiting_rooms": {},
        "socket_state": {},
        "socket_event_hits": {},
        "bot_choose_play": lambda bot, player, difficulty="normal": {
            "intent": "Strike",
            "profile": difficulty,
            "logs": [],
        },
        "create_player_object": create_player_object,
        "emit_log": lambda room_id, message: logs.append((room_id, message)),
        "emit_state": lambda room_id: states.append(room_id),
        "is_valid_room_code": lambda code: len(code) == 4 and code.isalnum(),
        "log_rc_event": lambda *args, **kwargs: events.append((args, kwargs)),
        "normalize_room_code": lambda code: str(code or "").strip().upper(),
        "safe_user_id": lambda player: player.get("user_id"),
    }

    runtime = GameSocketRuntime(socketio, deps)
    controller = MatchmakingController(socketio, deps, runtime)
    return controller, runtime, socketio, logs, states, events


def test_join_training_starts_bot_training_room():
    controller, runtime, socketio, logs, states, events = make_controller()
    runtime.online_players()["sid-a"] = {"status": "online"}
    user = User(1, "Alice")

    controller.join_training("sid-a", user, {"difficulty": "hard"})

    match = runtime.active_matches["training_sid-a"]
    assert match["training"] is True
    assert match["is_bot_match"] is True
    assert match["bot_difficulty"] == "hard"
    assert match["p1"]["name"] == "Alice"
    assert match["p2"]["is_bot"] is True
    assert runtime.player_rooms["sid-a"] == "training_sid-a"
    assert runtime.online_players()["sid-a"]["status"] == "in_match"
    assert ("sid-a", "training_sid-a", "/") in socketio.server.rooms
    assert logs == [("training_sid-a", "Training started. Choose an Intent, set cards, then press Ready.")]
    assert states == ["training_sid-a"]
    assert events


def test_join_queue_enqueues_first_player_and_starts_fallback_timer():
    controller, runtime, socketio, _logs, _states, events = make_controller()
    runtime.online_players()["sid-a"] = {"status": "online"}
    user = User(1, "Alice", deck_json="[\"c1\"]")

    controller.join_queue("sid-a", user)

    assert runtime.socket_state["waiting_player"]["sid"] == "sid-a"
    assert runtime.socket_state["waiting_deck_json"] == "[\"c1\"]"
    assert runtime.online_players()["sid-a"]["status"] == "queued"
    assert socketio.background_tasks
    assert socketio.background_tasks[0][1] == ("sid-a", 1, 10.0)
    assert socketio.emitted[0][0] == "queue_status"
    assert events


def test_join_queue_matches_second_player_with_waiting_player():
    controller, runtime, socketio, logs, states, _events = make_controller()
    runtime.online_players()["sid-a"] = {"status": "queued"}
    runtime.online_players()["sid-b"] = {"status": "online"}
    runtime.socket_state["waiting_player"] = make_player("Alice", "sid-a", user_id=1)
    user = User(2, "Bob")

    controller.join_queue("sid-b", user)

    room_id = "room_sid-a_sid-b"
    assert runtime.socket_state["waiting_player"] is None
    assert room_id in runtime.active_matches
    assert runtime.player_rooms == {"sid-a": room_id, "sid-b": room_id}
    assert runtime.online_players()["sid-a"]["status"] == "in_match"
    assert runtime.online_players()["sid-b"]["status"] == "in_match"
    assert ("sid-a", room_id, "/") in socketio.server.rooms
    assert ("sid-b", room_id, "/") in socketio.server.rooms
    assert logs == [(room_id, "PvP duel started. Choose an Intent, set cards, then press Ready.")]
    assert states == [room_id]


def test_cancel_queue_clears_waiting_player():
    controller, runtime, socketio, _logs, _states, _events = make_controller()
    runtime.online_players()["sid-a"] = {"status": "queued"}
    runtime.socket_state["waiting_player"] = make_player("Alice", "sid-a", user_id=1)

    controller.cancel_queue("sid-a")

    assert runtime.socket_state["waiting_player"] is None
    assert runtime.online_players()["sid-a"]["status"] == "online"
    assert (
        "queue_status",
        {"msg": "Match search cancelled."},
        "sid-a",
    ) in socketio.emitted


def test_join_bot_match_starts_direct_bot_match():
    controller, runtime, socketio, logs, states, _events = make_controller()
    runtime.online_players()["sid-a"] = {"status": "online"}
    user = User(1, "Alice")

    controller.join_bot_match("sid-a", user)

    match = runtime.active_matches["bot_sid-a"]
    assert match["is_bot_match"] is True
    assert match["p2"]["is_bot"] is True
    assert runtime.player_rooms["sid-a"] == "bot_sid-a"
    assert runtime.online_players()["sid-a"]["status"] == "in_match"
    assert ("sid-a", "bot_sid-a", "/") in socketio.server.rooms
    assert logs == [
        ("bot_sid-a", "Training match started."),
        ("bot_sid-a", "Opponent: Ambitionz Bot."),
    ]
    assert states == ["bot_sid-a"]


def test_private_room_waits_then_matches_second_player():
    controller, runtime, socketio, _logs, _states, _events = make_controller()
    runtime.online_players()["sid-a"] = {"status": "online"}
    runtime.online_players()["sid-b"] = {"status": "online"}

    controller.join_private_room("sid-a", User(1, "Alice"), {"code": "abcd"})

    assert "ABCD" in runtime.private_waiting_rooms
    assert runtime.online_players()["sid-a"]["status"] == "private_queue"
    assert (
        "queue_status",
        {"msg": "Private room ABCD created. Waiting for opponent..."},
        "sid-a",
    ) in socketio.emitted

    controller.join_private_room("sid-b", User(2, "Bob"), {"code": "ABCD"})

    room_id = "private_ABCD_sid-a_sid-b"
    assert "ABCD" not in runtime.private_waiting_rooms
    assert room_id in runtime.active_matches
    assert runtime.player_rooms == {"sid-a": room_id, "sid-b": room_id}

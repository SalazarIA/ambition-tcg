from services.match_payloads import find_player_key
from sockets.lifecycle import SocketLifecycleController


class FakeSocketIO:
    def __init__(self):
        self.emitted = []

    def emit(self, event, payload, to=None):
        self.emitted.append((event, payload, to))


class FakeSession:
    def __init__(self, users):
        self.users = users

    def get(self, _model, user_id):
        return self.users.get(user_id)


class FakeDb:
    def __init__(self, users):
        self.session = FakeSession(users)


class User:
    def __init__(self, user_id=1, username="Player"):
        self.id = user_id
        self.username = username


class FakeRuntime:
    def __init__(self):
        self.active_matches = {}
        self.player_rooms = {}
        self.private_waiting_rooms = {}
        self.socket_event_hits = {}
        self.socket_state = {
            "waiting_player": None,
            "waiting_since": None,
            "waiting_deck_json": None,
            "queue_generation": 0,
            "online_players": {},
        }
        self.presence_emits = []
        self.events = []
        self.released_matches = []

    def online_players(self):
        return self.socket_state["online_players"]

    def emit_presence(self, to=None):
        self.presence_emits.append(to)

    def log_event(self, *args, **kwargs):
        self.events.append((args, kwargs))

    def clear_waiting_player(self):
        self.socket_state["waiting_player"] = None
        self.socket_state["waiting_since"] = None
        self.socket_state["waiting_deck_json"] = None
        self.socket_state["queue_generation"] += 1

    def release_match_presence(self, match):
        self.released_matches.append(match)


def make_player(name="Player", sid="sid-a", user_id=1, is_bot=False):
    return {
        "name": name,
        "sid": sid,
        "user_id": user_id,
        "is_bot": is_bot,
    }


def make_lifecycle(users=None):
    socketio = FakeSocketIO()
    runtime = FakeRuntime()
    end_calls = []
    deps = {
        "db": FakeDb(users or {}),
        "User": User,
        "end_match": lambda room_id, winner_key, ending_reason="completed": end_calls.append((room_id, winner_key, ending_reason)),
        "find_player_key": find_player_key,
        "safe_user_id": lambda player: None if player.get("is_bot") else player.get("user_id"),
    }
    lifecycle = SocketLifecycleController(socketio, deps, runtime)
    return lifecycle, runtime, socketio, end_calls


def test_connect_registers_authenticated_user_presence():
    lifecycle, runtime, _socketio, _end_calls = make_lifecycle({1: User(1, "Alice")})

    lifecycle.connect("sid-a", 1)

    assert runtime.online_players()["sid-a"]["user_id"] == 1
    assert runtime.online_players()["sid-a"]["username"] == "Alice"
    assert runtime.online_players()["sid-a"]["status"] == "online"
    assert runtime.presence_emits == ["sid-a", None]


def test_disconnect_clears_waiting_queue_and_rate_limit_hits():
    lifecycle, runtime, _socketio, _end_calls = make_lifecycle()
    waiting_player = make_player("Alice", "sid-a", 1)
    runtime.online_players()["sid-a"] = {"status": "queued"}
    runtime.socket_event_hits[("sid-a", "join_queue")] = [1, 2]
    runtime.socket_state["waiting_player"] = waiting_player
    runtime.socket_state["waiting_deck_json"] = "[]"
    runtime.socket_state["waiting_since"] = 123

    lifecycle.disconnect("sid-a")

    assert "sid-a" not in runtime.online_players()
    assert ("sid-a", "join_queue") not in runtime.socket_event_hits
    assert runtime.socket_state["waiting_player"] is None
    assert runtime.socket_state["waiting_deck_json"] is None
    assert runtime.socket_state["waiting_since"] is None
    assert runtime.socket_state["queue_generation"] == 1
    assert runtime.events == [(("match", "Player left PvP queue"), {"user_id": 1})]
    assert runtime.presence_emits == [None]


def test_disconnect_clears_private_waiting_room():
    lifecycle, runtime, _socketio, _end_calls = make_lifecycle()
    runtime.private_waiting_rooms["ABCD"] = make_player("Alice", "sid-a", 1)

    lifecycle.disconnect("sid-a")

    assert runtime.private_waiting_rooms == {}
    assert runtime.events == [
        (
            ("match", "Player left private room queue"),
            {"details": {"room_code": "ABCD"}, "user_id": 1},
        )
    ]
    assert runtime.presence_emits == [None]


def test_disconnect_active_match_awards_enemy_and_releases_presence():
    lifecycle, runtime, socketio, end_calls = make_lifecycle()
    match = {
        "p1": make_player("Alice", "sid-a", 1),
        "p2": make_player("Bob", "sid-b", 2),
    }
    runtime.active_matches["room-1"] = match
    runtime.player_rooms["sid-a"] = "room-1"

    lifecycle.disconnect("sid-a")

    assert socketio.emitted == [
        ("opponent_left", {"msg": "Opponent disconnected. You win."}, "sid-b")
    ]
    assert runtime.events == [
        (
            ("match", "Player disconnected from active match"),
            {
                "details": {"room_id": "room-1", "player_key": "p1"},
                "user_id": 1,
                "level": "warning",
            },
        )
    ]
    assert end_calls == [("room-1", "p2", "disconnect")]
    assert runtime.released_matches == [match]

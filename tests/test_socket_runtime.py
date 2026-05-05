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
        self.sleeps = []

    def emit(self, event, payload, to=None):
        self.emitted.append((event, payload, to))

    def sleep(self, seconds):
        self.sleeps.append(seconds)


def make_player(name="Player", sid="sid-1", user_id=1):
    return {
        "name": name,
        "sid": sid,
        "user_id": user_id,
        "ready": False,
    }


def make_runtime():
    socketio = FakeSocketIO()
    logs = []
    state_emits = []
    events = []

    def create_player_object(user, sid):
        return {
            "name": getattr(user, "username", "Bot"),
            "sid": sid,
            "user_id": getattr(user, "id", None),
            "ready": False,
            "is_bot": False,
        }

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
        "emit_state": lambda room_id: state_emits.append(room_id),
        "log_rc_event": lambda *args, **kwargs: events.append((args, kwargs)),
        "safe_user_id": lambda player: player.get("user_id"),
    }

    runtime = GameSocketRuntime(socketio, deps)
    return runtime, socketio, logs, state_emits, events


def test_runtime_presence_payload_and_waiting_clear():
    runtime, _socketio, _logs, _state_emits, _events = make_runtime()
    runtime.online_players()["sid-1"] = {"status": "online"}
    runtime.active_matches["pvp-room"] = {"is_bot_match": False}
    runtime.active_matches["bot-room"] = {"is_bot_match": True}

    payload = runtime.presence_payload()

    assert payload == {
        "online": 1,
        "queued": 0,
        "active_matches": 2,
        "pvp_matches": 1,
        "bot_matches": 1,
    }

    runtime.socket_state["waiting_player"] = make_player()
    runtime.socket_state["waiting_deck_json"] = "[]"
    runtime.socket_state["waiting_since"] = 123
    runtime.clear_waiting_player()

    assert runtime.socket_state["waiting_player"] is None
    assert runtime.socket_state["waiting_deck_json"] is None
    assert runtime.socket_state["waiting_since"] is None
    assert runtime.socket_state["queue_generation"] == 1


def test_runtime_rate_limit_tracks_events_per_sid():
    runtime, socketio, _logs, _state_emits, _events = make_runtime()

    assert runtime.allow_socket_event("ready", limit=2, window_seconds=10, sid="sid-1", now=100)
    assert runtime.allow_socket_event("ready", limit=2, window_seconds=10, sid="sid-1", now=101)
    assert not runtime.allow_socket_event("ready", limit=2, window_seconds=10, sid="sid-1", now=102)
    assert socketio.emitted[-1] == (
        "queue_status",
        {"msg": "Too many actions. Slow down."},
        "sid-1",
    )

    assert runtime.allow_socket_event("ready", limit=2, window_seconds=10, sid="sid-1", now=113)


def test_runtime_starts_pvp_match_and_updates_presence():
    runtime, socketio, logs, state_emits, events = make_runtime()
    waiting_player = make_player("Waiting", "sid-a", user_id=10)
    player_object = make_player("Joining", "sid-b", user_id=20)
    runtime.online_players()["sid-a"] = {"status": "queued"}
    runtime.online_players()["sid-b"] = {"status": "online"}

    runtime.start_match_between_players(waiting_player, player_object, "room-1")

    assert "room-1" in runtime.active_matches
    assert runtime.player_rooms == {"sid-a": "room-1", "sid-b": "room-1"}
    assert runtime.online_players()["sid-a"]["status"] == "in_match"
    assert runtime.online_players()["sid-b"]["status"] == "in_match"
    assert ("sid-a", "room-1", "/") in socketio.server.rooms
    assert ("sid-b", "room-1", "/") in socketio.server.rooms
    assert state_emits == ["room-1"]
    assert logs == [("room-1", "PvP duel started. Choose an Intent, set cards, then press Ready.")]
    assert events


def test_runtime_fallback_starts_bot_match_after_timeout():
    runtime, socketio, _logs, state_emits, _events = make_runtime()
    waiting_player = make_player("Waiting", "sid-a", user_id=10)
    runtime.online_players()["sid-a"] = {"status": "queued"}
    runtime.socket_state["waiting_player"] = waiting_player
    runtime.socket_state["waiting_deck_json"] = "[]"
    runtime.socket_state["queue_generation"] = 7

    runtime.run_fallback_after_timeout("sid-a", 7, 5)

    assert socketio.sleeps == [5]
    assert runtime.socket_state["waiting_player"] is None
    assert runtime.player_rooms["sid-a"] == "quick_bot_sid-a"
    assert runtime.active_matches["quick_bot_sid-a"]["matchmaking_fallback"] is True
    assert runtime.active_matches["quick_bot_sid-a"]["p2"]["is_bot"] is True
    assert state_emits == ["quick_bot_sid-a"]

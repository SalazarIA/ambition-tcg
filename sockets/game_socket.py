import time

from flask import request, session

from sockets.battle_actions import BattleActionController
from sockets.matchmaking import MatchmakingController
from sockets.runtime import GameSocketRuntime


def register_game_socket_handlers(socketio, deps):
    runtime = GameSocketRuntime(socketio, deps)

    active_matches = runtime.active_matches
    player_rooms = runtime.player_rooms
    private_waiting_rooms = runtime.private_waiting_rooms
    socket_state = runtime.socket_state
    socket_event_hits = runtime.socket_event_hits

    db = deps["db"]
    User = deps["User"]
    end_match = deps["end_match"]
    find_player_key = deps["find_player_key"]
    safe_user_id = deps["safe_user_id"]

    battle_actions = BattleActionController(socketio, deps, runtime)
    matchmaking = MatchmakingController(socketio, deps, runtime)

    online_players = runtime.online_players
    emit_presence = runtime.emit_presence
    log_event = runtime.log_event
    clear_waiting_player = runtime.clear_waiting_player
    release_match_presence = runtime.release_match_presence

    @socketio.on("connect")
    def handle_connect(auth=None):
        sid = request.sid
        user_id = session.get("user_id")

        if user_id:
            user = db.session.get(User, user_id)

            if user:
                online_players()[sid] = {
                    "user_id": user.id,
                    "username": user.username,
                    "connected_at": time.time(),
                    "status": "online",
                }

        emit_presence(to=sid)
        emit_presence()

    @socketio.on("join_training")
    def handle_join_training(data=None):
        user_id = session.get("user_id")

        if not user_id:
            return

        user = db.session.get(User, user_id)

        if not user:
            return

        matchmaking.join_training(request.sid, user, data)

    @socketio.on("join_queue")
    def handle_join_queue():
        user_id = session.get("user_id")

        if not user_id:
            return

        user = db.session.get(User, user_id)

        if not user:
            return

        matchmaking.join_queue(request.sid, user)

    @socketio.on("cancel_queue")
    def handle_cancel_queue():
        matchmaking.cancel_queue(request.sid)

    @socketio.on("set_intent")
    def set_intent(data):
        battle_actions.set_intent(request.sid, data)

    @socketio.on("play_to_field")
    def play_to_field(data):
        battle_actions.play_to_field(request.sid, data)

    @socketio.on("choose_intent")
    def choose_intent(data):
        battle_actions.choose_intent(request.sid, data)

    @socketio.on("toggle_unleash")
    def toggle_unleash():
        battle_actions.toggle_unleash(request.sid)

    @socketio.on("declare_ready")
    def declare_ready():
        battle_actions.declare_ready(request.sid)

    @socketio.on("join_bot_match")
    def handle_join_bot_match():
        user_id = session.get("user_id")

        if not user_id:
            return

        user = db.session.get(User, user_id)

        if not user:
            return

        matchmaking.join_bot_match(request.sid, user)

    @socketio.on("join_private_room")
    def handle_join_private_room(data):
        user_id = session.get("user_id")

        if not user_id:
            return

        user = db.session.get(User, user_id)

        if not user:
            return

        matchmaking.join_private_room(request.sid, user, data)

    @socketio.on("disconnect")
    def handle_disconnect(reason=None):
        sid = request.sid
        online_players().pop(sid, None)

        for hit_key in [key for key in list(socket_event_hits.keys()) if key and key[0] == sid]:
            socket_event_hits.pop(hit_key, None)

        waiting_player = socket_state.get("waiting_player")

        if waiting_player and waiting_player["sid"] == sid:
            log_event("match", "Player left PvP queue", user_id=safe_user_id(waiting_player))
            clear_waiting_player()
            emit_presence()
            return

        for room_code, private_player in list(private_waiting_rooms.items()):
            if private_player["sid"] == sid:
                private_waiting_rooms.pop(room_code, None)
                log_event(
                    "match",
                    "Player left private room queue",
                    details={"room_code": room_code},
                    user_id=safe_user_id(private_player),
                )
                emit_presence()
                return

        room_id = player_rooms.get(sid)

        if not room_id:
            emit_presence()
            return

        match = active_matches.get(room_id)

        if not match:
            emit_presence()
            return

        player_key = find_player_key(match, sid)

        if not player_key:
            emit_presence()
            return

        enemy_key = "p2" if player_key == "p1" else "p1"
        enemy = match[enemy_key]

        if not enemy.get("is_bot") and enemy.get("sid"):
            socketio.emit("opponent_left", {"msg": "Opponent disconnected. You win."}, to=enemy["sid"])

        log_event(
            "match",
            "Player disconnected from active match",
            details={"room_id": room_id, "player_key": player_key},
            user_id=safe_user_id(match[player_key]),
            level="warning",
        )

        finished_match = match
        end_match(room_id, enemy_key, ending_reason="disconnect")
        release_match_presence(finished_match)

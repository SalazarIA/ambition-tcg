import time

from flask import request, session
from flask_socketio import join_room

from sockets.battle_actions import BattleActionController
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
    create_player_object = deps["create_player_object"]
    emit_log = deps["emit_log"]
    emit_state = deps["emit_state"]
    end_match = deps["end_match"]
    find_player_key = deps["find_player_key"]
    is_valid_room_code = deps["is_valid_room_code"]
    log_rc_event = deps["log_rc_event"]
    normalize_room_code = deps["normalize_room_code"]
    safe_user_id = deps["safe_user_id"]

    battle_actions = BattleActionController(socketio, deps, runtime)

    matchmaking_fallback_seconds = runtime.matchmaking_fallback_seconds
    online_players = runtime.online_players
    set_presence_status = runtime.set_presence_status
    presence_payload = runtime.presence_payload
    emit_presence = runtime.emit_presence
    emit_matchmaking_status = runtime.emit_matchmaking_status
    log_event = runtime.log_event
    add_sid_to_room = runtime.add_sid_to_room
    clear_waiting_player = runtime.clear_waiting_player
    release_match_presence = runtime.release_match_presence
    create_ambitionz_bot = runtime.create_ambitionz_bot
    start_match_between_players = runtime.start_match_between_players
    run_fallback_after_timeout = runtime.run_fallback_after_timeout
    allow_socket_event = runtime.allow_socket_event

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
        if not allow_socket_event("join_training", limit=12, window_seconds=30):
            return

        user_id = session.get("user_id")

        if not user_id:
            return

        user = db.session.get(User, user_id)

        if not user:
            return

        sid = request.sid

        if sid in player_rooms:
            return

        try:
            data = data or {}
            difficulty = str(data.get("difficulty") or "normal").lower()

            if difficulty not in {"easy", "normal", "hard"}:
                difficulty = "normal"

            player_object = create_player_object(user, sid)

            bot_user = type("BotUser", (), {})()
            bot_user.id = 0
            bot_user.username = "Ambitionz Bot"
            bot_user.deck_json = user.deck_json

            bot_object = create_player_object(bot_user, f"bot_{sid}")
            bot_object["name"] = "Ambitionz Bot"
            bot_object["sid"] = f"bot_{sid}"
            bot_object["is_bot"] = True
            bot_object["difficulty"] = difficulty

            room_id = f"training_{sid}"

            join_room(room_id, sid=sid)

            active_matches[room_id] = {
                "p1": player_object,
                "p2": bot_object,
                "round": 1,
                "phase": "Set Phase",
                "resolving": False,
                "logs": [],
                "training": True,
                "is_bot_match": True,
                "bot_difficulty": difficulty,
            }

            player_rooms[sid] = room_id
            set_presence_status(sid, "in_match")

            socketio.emit("match_found", {"msg": "Training started against Ambitionz Bot."}, to=sid)
            emit_matchmaking_status(sid, "matched", mode="training")
            emit_log(room_id, "Training started. Choose an Intent, set cards, then press Ready.")
            log_rc_event(
                "match",
                "Training match started",
                details={"room_id": room_id, "difficulty": difficulty},
                user_id=user.id,
            )
            emit_state(room_id)
            emit_presence()

        except Exception as error:
            print("TRAINING START ERROR:", type(error).__name__, error)
            log_rc_event(
                "match",
                "Training failed to start",
                details={"error": f"{type(error).__name__}: {error}"},
                user_id=user.id,
                level="error",
            )
            socketio.emit("queue_status", {"msg": "Training failed to start. Check your deck."}, to=sid)

    @socketio.on("join_queue")
    def handle_join_queue():
        if not allow_socket_event("join_queue", limit=12, window_seconds=30):
            return

        user_id = session.get("user_id")

        if not user_id:
            return

        user = db.session.get(User, user_id)

        if not user:
            return

        current_sid = request.sid

        if current_sid in player_rooms:
            room_id = player_rooms.get(current_sid)
            socketio.emit("queue_status", {"msg": "You are already in a match."}, to=current_sid)

            if room_id in active_matches:
                emit_state(room_id)

            return

        try:
            player_object = create_player_object(user, current_sid)
        except Exception as error:
            print("QUEUE PLAYER CREATE ERROR:", type(error).__name__, error)
            socketio.emit("queue_status", {"msg": "Could not create your player. Check your deck."}, to=current_sid)
            log_rc_event(
                "match",
                "Player failed to enter matchmaking",
                details={"error": f"{type(error).__name__}: {error}"},
                user_id=user.id,
                level="error",
            )
            return

        waiting_player = socket_state.get("waiting_player")

        if waiting_player and waiting_player.get("sid") == current_sid:
            socketio.emit("queue_status", {"msg": "Already searching for opponent..."}, to=current_sid)
            emit_matchmaking_status(
                current_sid,
                "searching",
                mode="pvp",
                queued=presence_payload()["queued"],
            )
            return

        if waiting_player and safe_user_id(waiting_player) == user.id:
            socketio.emit("queue_status", {"msg": "You are already searching from another tab."}, to=current_sid)
            emit_matchmaking_status(current_sid, "searching", mode="pvp")
            return

        if waiting_player and waiting_player.get("sid") not in online_players():
            clear_waiting_player()
            waiting_player = None

        if waiting_player and waiting_player.get("sid") not in player_rooms:
            room_id = f"room_{waiting_player['sid']}_{current_sid}"

            clear_waiting_player()
            start_match_between_players(waiting_player, player_object, room_id, log_message="PvP match started")
            return

        clear_waiting_player()
        socket_state["waiting_player"] = player_object
        socket_state["waiting_since"] = time.time()
        socket_state["waiting_deck_json"] = user.deck_json
        queue_generation = int(socket_state.get("queue_generation", 0) or 0)
        fallback_seconds = matchmaking_fallback_seconds()
        set_presence_status(current_sid, "queued")

        socketio.emit(
            "queue_status",
            {"msg": f"Searching for a real opponent. Bot fallback in {int(round(fallback_seconds))}s."},
            to=current_sid,
        )
        emit_matchmaking_status(
            current_sid,
            "searching",
            mode="pvp",
            fallback_seconds=fallback_seconds,
            queued=1,
        )
        log_event(
            "match",
            "Player entered PvP matchmaking queue",
            details={"fallback_seconds": fallback_seconds},
            user_id=user.id,
        )
        emit_presence()
        socketio.start_background_task(run_fallback_after_timeout, current_sid, queue_generation, fallback_seconds)

    @socketio.on("cancel_queue")
    def handle_cancel_queue():
        if not allow_socket_event("cancel_queue", limit=20, window_seconds=30):
            return

        sid = request.sid
        waiting_player = socket_state.get("waiting_player")

        if waiting_player and waiting_player.get("sid") == sid:
            clear_waiting_player()
            set_presence_status(sid, "online")
            socketio.emit("queue_status", {"msg": "Match search cancelled."}, to=sid)
            emit_matchmaking_status(sid, "cancelled", mode="pvp")
            log_event("match", "Player cancelled PvP matchmaking", user_id=safe_user_id(waiting_player))
            emit_presence()
            return

        socketio.emit("queue_status", {"msg": "No active match search to cancel."}, to=sid)
        emit_matchmaking_status(sid, "idle", mode="pvp")

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
        if not allow_socket_event("join_bot_match", limit=12, window_seconds=30):
            return

        user_id = session.get("user_id")

        if not user_id:
            return

        user = db.session.get(User, user_id)

        if not user:
            return

        current_sid = request.sid

        if current_sid in player_rooms:
            return

        difficulty = "normal"
        player_object = create_player_object(user, current_sid)
        bot_object = create_ambitionz_bot(user.deck_json, current_sid, difficulty)

        room_id = f"bot_{current_sid}"

        add_sid_to_room(current_sid, room_id)

        active_matches[room_id] = {
            "p1": player_object,
            "p2": bot_object,
            "round": 1,
            "phase": "Set Phase",
            "resolving": False,
            "logs": [],
            "is_bot_match": True,
            "bot_difficulty": difficulty,
        }

        player_rooms[current_sid] = room_id
        set_presence_status(current_sid, "in_match")

        socketio.emit("match_found", {"msg": "Training match started against bot."}, to=current_sid)
        emit_matchmaking_status(current_sid, "matched", mode="bot")

        emit_log(room_id, "Training match started.")
        emit_log(room_id, f"Opponent: {bot_object['name']}.")
        emit_state(room_id)
        emit_presence()

    @socketio.on("join_private_room")
    def handle_join_private_room(data):
        if not allow_socket_event("join_private_room", limit=12, window_seconds=30):
            return

        data = data or {}
        user_id = session.get("user_id")

        if not user_id:
            return

        user = db.session.get(User, user_id)

        if not user:
            return

        current_sid = request.sid

        if current_sid in player_rooms:
            return

        code = normalize_room_code(data.get("code", ""))

        if not is_valid_room_code(code):
            socketio.emit("queue_status", {"msg": "Invalid private room code."}, to=current_sid)
            return

        player_object = create_player_object(user, current_sid)

        if code not in private_waiting_rooms:
            private_waiting_rooms[code] = player_object
            set_presence_status(current_sid, "private_queue")
            socketio.emit("queue_status", {"msg": f"Private room {code} created. Waiting for opponent..."}, to=current_sid)
            emit_matchmaking_status(current_sid, "searching", mode="private", room_code=code)
            emit_presence()
            return

        waiting = private_waiting_rooms.get(code)

        if waiting["sid"] == current_sid:
            socketio.emit("queue_status", {"msg": f"Waiting in private room {code}..."}, to=current_sid)
            return

        room_id = f"private_{code}_{waiting['sid']}_{current_sid}"

        start_match_between_players(waiting, player_object, room_id, log_message="Private PvP match started")

        private_waiting_rooms.pop(code, None)

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

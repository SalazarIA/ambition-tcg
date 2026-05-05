import time


class MatchmakingController:
    def __init__(self, socketio, deps, runtime):
        self.socketio = socketio
        self.active_matches = runtime.active_matches
        self.player_rooms = runtime.player_rooms
        self.private_waiting_rooms = runtime.private_waiting_rooms
        self.socket_state = runtime.socket_state

        self.create_player_object = deps["create_player_object"]
        self.emit_log = deps["emit_log"]
        self.emit_state = deps["emit_state"]
        self.is_valid_room_code = deps["is_valid_room_code"]
        self.normalize_room_code = deps["normalize_room_code"]
        self.safe_user_id = deps["safe_user_id"]

        self.add_sid_to_room = runtime.add_sid_to_room
        self.allow_socket_event = runtime.allow_socket_event
        self.clear_waiting_player = runtime.clear_waiting_player
        self.create_ambitionz_bot = runtime.create_ambitionz_bot
        self.emit_matchmaking_status = runtime.emit_matchmaking_status
        self.emit_presence = runtime.emit_presence
        self.log_event = runtime.log_event
        self.matchmaking_fallback_seconds = runtime.matchmaking_fallback_seconds
        self.online_players = runtime.online_players
        self.presence_payload = runtime.presence_payload
        self.run_fallback_after_timeout = runtime.run_fallback_after_timeout
        self.set_presence_status = runtime.set_presence_status
        self.start_match_between_players = runtime.start_match_between_players

    def join_training(self, sid, user, data=None):
        if not self.allow_socket_event("join_training", limit=12, window_seconds=30, sid=sid):
            return

        if not user or sid in self.player_rooms:
            return

        try:
            data = data or {}
            difficulty = str(data.get("difficulty") or "normal").lower()

            if difficulty not in {"easy", "normal", "hard"}:
                difficulty = "normal"

            player_object = self.create_player_object(user, sid)
            bot_object = self.create_ambitionz_bot(user.deck_json, sid, difficulty)
            room_id = f"training_{sid}"

            self.add_sid_to_room(sid, room_id)

            self.active_matches[room_id] = {
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

            self.player_rooms[sid] = room_id
            self.set_presence_status(sid, "in_match")

            self.socketio.emit("match_found", {"msg": "Training started against Ambitionz Bot."}, to=sid)
            self.emit_matchmaking_status(sid, "matched", mode="training")
            self.emit_log(room_id, "Training started. Choose an Intent, set cards, then press Ready.")
            self.log_event(
                "match",
                "Training match started",
                details={"room_id": room_id, "difficulty": difficulty},
                user_id=user.id,
            )
            self.emit_state(room_id)
            self.emit_presence()

        except Exception as error:
            print("TRAINING START ERROR:", type(error).__name__, error)
            self.log_event(
                "match",
                "Training failed to start",
                details={"error": f"{type(error).__name__}: {error}"},
                user_id=user.id,
                level="error",
            )
            self.socketio.emit("queue_status", {"msg": "Training failed to start. Check your deck."}, to=sid)

    def join_queue(self, sid, user):
        if not self.allow_socket_event("join_queue", limit=12, window_seconds=30, sid=sid):
            return

        if not user:
            return

        if sid in self.player_rooms:
            room_id = self.player_rooms.get(sid)
            self.socketio.emit("queue_status", {"msg": "You are already in a match."}, to=sid)

            if room_id in self.active_matches:
                self.emit_state(room_id)

            return

        try:
            player_object = self.create_player_object(user, sid)
        except Exception as error:
            print("QUEUE PLAYER CREATE ERROR:", type(error).__name__, error)
            self.socketio.emit("queue_status", {"msg": "Could not create your player. Check your deck."}, to=sid)
            self.log_event(
                "match",
                "Player failed to enter matchmaking",
                details={"error": f"{type(error).__name__}: {error}"},
                user_id=user.id,
                level="error",
            )
            return

        waiting_player = self.socket_state.get("waiting_player")

        if waiting_player and waiting_player.get("sid") == sid:
            self.socketio.emit("queue_status", {"msg": "Already searching for opponent..."}, to=sid)
            self.emit_matchmaking_status(
                sid,
                "searching",
                mode="pvp",
                queued=self.presence_payload()["queued"],
            )
            return

        if waiting_player and self.safe_user_id(waiting_player) == user.id:
            self.socketio.emit("queue_status", {"msg": "You are already searching from another tab."}, to=sid)
            self.emit_matchmaking_status(sid, "searching", mode="pvp")
            return

        if waiting_player and waiting_player.get("sid") not in self.online_players():
            self.clear_waiting_player()
            waiting_player = None

        if waiting_player and waiting_player.get("sid") not in self.player_rooms:
            room_id = f"room_{waiting_player['sid']}_{sid}"

            self.clear_waiting_player()
            self.start_match_between_players(waiting_player, player_object, room_id, log_message="PvP match started")
            return

        self.clear_waiting_player()
        self.socket_state["waiting_player"] = player_object
        self.socket_state["waiting_since"] = time.time()
        self.socket_state["waiting_deck_json"] = user.deck_json
        queue_generation = int(self.socket_state.get("queue_generation", 0) or 0)
        fallback_seconds = self.matchmaking_fallback_seconds()
        self.set_presence_status(sid, "queued")

        self.socketio.emit(
            "queue_status",
            {"msg": f"Searching for a real opponent. Bot fallback in {int(round(fallback_seconds))}s."},
            to=sid,
        )
        self.emit_matchmaking_status(
            sid,
            "searching",
            mode="pvp",
            fallback_seconds=fallback_seconds,
            queued=1,
        )
        self.log_event(
            "match",
            "Player entered PvP matchmaking queue",
            details={"fallback_seconds": fallback_seconds},
            user_id=user.id,
        )
        self.emit_presence()
        self.socketio.start_background_task(self.run_fallback_after_timeout, sid, queue_generation, fallback_seconds)

    def cancel_queue(self, sid):
        if not self.allow_socket_event("cancel_queue", limit=20, window_seconds=30, sid=sid):
            return

        waiting_player = self.socket_state.get("waiting_player")

        if waiting_player and waiting_player.get("sid") == sid:
            self.clear_waiting_player()
            self.set_presence_status(sid, "online")
            self.socketio.emit("queue_status", {"msg": "Match search cancelled."}, to=sid)
            self.emit_matchmaking_status(sid, "cancelled", mode="pvp")
            self.log_event("match", "Player cancelled PvP matchmaking", user_id=self.safe_user_id(waiting_player))
            self.emit_presence()
            return

        self.socketio.emit("queue_status", {"msg": "No active match search to cancel."}, to=sid)
        self.emit_matchmaking_status(sid, "idle", mode="pvp")

    def join_bot_match(self, sid, user):
        if not self.allow_socket_event("join_bot_match", limit=12, window_seconds=30, sid=sid):
            return

        if not user or sid in self.player_rooms:
            return

        difficulty = "normal"
        player_object = self.create_player_object(user, sid)
        bot_object = self.create_ambitionz_bot(user.deck_json, sid, difficulty)
        room_id = f"bot_{sid}"

        self.add_sid_to_room(sid, room_id)

        self.active_matches[room_id] = {
            "p1": player_object,
            "p2": bot_object,
            "round": 1,
            "phase": "Set Phase",
            "resolving": False,
            "logs": [],
            "is_bot_match": True,
            "bot_difficulty": difficulty,
        }

        self.player_rooms[sid] = room_id
        self.set_presence_status(sid, "in_match")

        self.socketio.emit("match_found", {"msg": "Training match started against bot."}, to=sid)
        self.emit_matchmaking_status(sid, "matched", mode="bot")
        self.emit_log(room_id, "Training match started.")
        self.emit_log(room_id, f"Opponent: {bot_object['name']}.")
        self.emit_state(room_id)
        self.emit_presence()

    def join_private_room(self, sid, user, data):
        if not self.allow_socket_event("join_private_room", limit=12, window_seconds=30, sid=sid):
            return

        if not user or sid in self.player_rooms:
            return

        data = data or {}
        code = self.normalize_room_code(data.get("code", ""))

        if not self.is_valid_room_code(code):
            self.socketio.emit("queue_status", {"msg": "Invalid private room code."}, to=sid)
            return

        player_object = self.create_player_object(user, sid)

        if code not in self.private_waiting_rooms:
            self.private_waiting_rooms[code] = player_object
            self.set_presence_status(sid, "private_queue")
            self.socketio.emit("queue_status", {"msg": f"Private room {code} created. Waiting for opponent..."}, to=sid)
            self.emit_matchmaking_status(sid, "searching", mode="private", room_code=code)
            self.emit_presence()
            return

        waiting = self.private_waiting_rooms.get(code)

        if waiting["sid"] == sid:
            self.socketio.emit("queue_status", {"msg": f"Waiting in private room {code}..."}, to=sid)
            return

        room_id = f"private_{code}_{waiting['sid']}_{sid}"

        self.start_match_between_players(waiting, player_object, room_id, log_message="Private PvP match started")
        self.private_waiting_rooms.pop(code, None)

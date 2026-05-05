import time


class SocketLifecycleController:
    def __init__(self, socketio, deps, runtime):
        self.socketio = socketio
        self.active_matches = runtime.active_matches
        self.player_rooms = runtime.player_rooms
        self.private_waiting_rooms = runtime.private_waiting_rooms
        self.socket_state = runtime.socket_state
        self.socket_event_hits = runtime.socket_event_hits

        self.db = deps["db"]
        self.User = deps["User"]
        self.end_match = deps["end_match"]
        self.find_player_key = deps["find_player_key"]
        self.safe_user_id = deps["safe_user_id"]

        self.clear_waiting_player = runtime.clear_waiting_player
        self.emit_presence = runtime.emit_presence
        self.log_event = runtime.log_event
        self.online_players = runtime.online_players
        self.release_match_presence = runtime.release_match_presence

    def user_from_id(self, user_id):
        if not user_id:
            return None

        return self.db.session.get(self.User, user_id)

    def connect(self, sid, user_id=None):
        user = self.user_from_id(user_id)

        if user:
            self.online_players()[sid] = {
                "user_id": user.id,
                "username": user.username,
                "connected_at": time.time(),
                "status": "online",
            }

        self.emit_presence(to=sid)
        self.emit_presence()

    def disconnect(self, sid):
        self.online_players().pop(sid, None)

        for hit_key in [key for key in list(self.socket_event_hits.keys()) if key and key[0] == sid]:
            self.socket_event_hits.pop(hit_key, None)

        waiting_player = self.socket_state.get("waiting_player")

        if waiting_player and waiting_player["sid"] == sid:
            self.log_event("match", "Player left PvP queue", user_id=self.safe_user_id(waiting_player))
            self.clear_waiting_player()
            self.emit_presence()
            return

        for room_code, private_player in list(self.private_waiting_rooms.items()):
            if private_player["sid"] == sid:
                self.private_waiting_rooms.pop(room_code, None)
                self.log_event(
                    "match",
                    "Player left private room queue",
                    details={"room_code": room_code},
                    user_id=self.safe_user_id(private_player),
                )
                self.emit_presence()
                return

        room_id = self.player_rooms.get(sid)

        if not room_id:
            self.emit_presence()
            return

        match = self.active_matches.get(room_id)

        if not match:
            self.emit_presence()
            return

        player_key = self.find_player_key(match, sid)

        if not player_key:
            self.emit_presence()
            return

        enemy_key = "p2" if player_key == "p1" else "p1"
        enemy = match[enemy_key]

        if not enemy.get("is_bot") and enemy.get("sid"):
            self.socketio.emit("opponent_left", {"msg": "Opponent disconnected. You win."}, to=enemy["sid"])

        self.log_event(
            "match",
            "Player disconnected from active match",
            details={"room_id": room_id, "player_key": player_key},
            user_id=self.safe_user_id(match[player_key]),
            level="warning",
        )

        finished_match = match
        self.end_match(room_id, enemy_key, ending_reason="disconnect")
        self.release_match_presence(finished_match)

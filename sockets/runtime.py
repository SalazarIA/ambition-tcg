import time

from flask import has_app_context, request

from services.match_engine_facade import MatchEngineFacade


class GameSocketRuntime:
    def __init__(self, socketio, deps):
        self.socketio = socketio
        self.active_matches = deps["active_matches"]
        self.player_rooms = deps["player_rooms"]
        self.private_waiting_rooms = deps["private_waiting_rooms"]
        self.socket_state = deps["socket_state"]
        self.socket_event_hits = deps.setdefault("socket_event_hits", {})

        self.app = deps.get("app")
        self.create_player_object = deps["create_player_object"]
        self.emit_log = deps["emit_log"]
        self.emit_state = deps["emit_state"]
        self.log_rc_event = deps["log_rc_event"]
        self.match_engine_factory = deps.get("match_engine_factory") or self.match_engine
        self.safe_user_id = deps["safe_user_id"]

        self.socket_state.setdefault("waiting_player", None)
        self.socket_state.setdefault("waiting_since", None)
        self.socket_state.setdefault("waiting_deck_json", None)
        self.socket_state.setdefault("queue_generation", 0)
        self.socket_state.setdefault("online_players", {})

    def matchmaking_fallback_seconds(self):
        try:
            return max(0.0, float(self.app.config.get("MATCHMAKING_BOT_FALLBACK_SECONDS", 10)))
        except Exception:
            return 10.0

    def online_players(self):
        return self.socket_state.setdefault("online_players", {})

    def set_presence_status(self, sid, status):
        player = self.online_players().get(sid)

        if player:
            player["status"] = status

    def presence_payload(self):
        online = self.online_players()

        return {
            "online": len(online),
            "queued": 1 if self.socket_state.get("waiting_player") else 0,
            "active_matches": len(self.active_matches),
            "pvp_matches": sum(1 for match in self.active_matches.values() if not match.get("is_bot_match")),
            "bot_matches": sum(1 for match in self.active_matches.values() if match.get("is_bot_match")),
        }

    def emit_presence(self, to=None):
        payload = self.presence_payload()

        if to:
            self.socketio.emit("presence_update", payload, to=to)
        else:
            self.socketio.emit("presence_update", payload)

    def emit_matchmaking_status(self, sid, status, **extra):
        payload = {
            "status": status,
            "fallback_seconds": self.matchmaking_fallback_seconds(),
            **extra,
        }
        self.socketio.emit("matchmaking_status", payload, to=sid)

    def log_event(self, *args, **kwargs):
        if self.app and not has_app_context():
            with self.app.app_context():
                return self.log_rc_event(*args, **kwargs)

        return self.log_rc_event(*args, **kwargs)

    def emit_engine_event(self, event, payload, room=None):
        try:
            return self.socketio.emit(event, payload, room=room)
        except TypeError:
            return self.socketio.emit(event, payload, to=room)

    def match_engine(self):
        return MatchEngineFacade(self.active_matches, self.player_rooms, self.emit_engine_event)

    def add_sid_to_room(self, sid, room_id):
        self.socketio.server.enter_room(sid, room_id, namespace="/")

    def clear_waiting_player(self):
        self.socket_state["waiting_player"] = None
        self.socket_state["waiting_since"] = None
        self.socket_state["waiting_deck_json"] = None
        self.socket_state["queue_generation"] = int(self.socket_state.get("queue_generation", 0) or 0) + 1

    def release_match_presence(self, match):
        for player_key in ("p1", "p2"):
            sid = match.get(player_key, {}).get("sid")

            if sid and sid in self.online_players():
                self.set_presence_status(sid, "online")

        self.emit_presence()

    def start_match_between_players(self, waiting_player, player_object, room_id, log_message="PvP match started"):
        self.add_sid_to_room(waiting_player["sid"], room_id)
        self.add_sid_to_room(player_object["sid"], room_id)

        engine = self.match_engine_factory()
        engine.start_pvp_match(
            waiting_player,
            player_object,
            room_id,
            message="Battle Engine V2 PvP duel started. Choose an intent, play a card, then press Ready.",
        )
        self.set_presence_status(waiting_player["sid"], "in_match")
        self.set_presence_status(player_object["sid"], "in_match")

        self.socketio.emit("match_found", {"msg": "Opponent found. BE2 duel started."}, to=room_id)
        self.emit_matchmaking_status(waiting_player["sid"], "matched", mode="pvp")
        self.emit_matchmaking_status(player_object["sid"], "matched", mode="pvp")
        self.log_event(
            "match",
            log_message,
            details={"room_id": room_id, "engine": "be2"},
            user_id=self.safe_user_id(waiting_player),
        )
        self.emit_presence()

    def start_bot_fallback_match(self, player_object, deck_json, sid, reason="timeout"):
        difficulty = "normal"
        room_id = f"quick_bot_{sid}"

        self.add_sid_to_room(sid, room_id)

        engine = self.match_engine_factory()
        engine.start_bot_match_for_player(
            player_object,
            room_id,
            message="No online opponent was available. Battle Engine V2 bot duel started.",
            matchmaking_fallback=True,
        )
        self.set_presence_status(sid, "in_match")
        self.socketio.emit("queue_status", {"msg": "No online opponent found. Starting BE2 bot duel..."}, to=sid)
        self.socketio.emit("match_found", {"msg": "Bot opponent found. BE2 duel started."}, to=sid)
        self.emit_matchmaking_status(sid, "fallback", mode="bot", reason=reason)
        self.log_event(
            "match",
            "Matchmaking fallback BE2 bot match started",
            details={"room_id": room_id, "difficulty": difficulty, "reason": reason, "engine": "be2"},
            user_id=self.safe_user_id(player_object),
        )
        self.emit_presence()

    def play_bot_turn_if_needed(self, match, room_id, player_key):
        if isinstance(match, dict) and match.get("be2"):
            return self.match_engine_factory().emit_match_state(room_id, message="BE2 bot turns resolve through the board engine.")
        return None

    def run_fallback_after_timeout(self, sid, queue_generation, fallback_seconds):
        self.socketio.sleep(fallback_seconds)

        waiting_player = self.socket_state.get("waiting_player")

        if not waiting_player or waiting_player.get("sid") != sid:
            return

        if int(self.socket_state.get("queue_generation", 0) or 0) != int(queue_generation):
            return

        if sid in self.player_rooms or sid not in self.online_players():
            self.clear_waiting_player()
            self.emit_presence()
            return

        deck_json = self.socket_state.get("waiting_deck_json")
        self.clear_waiting_player()

        try:
            self.start_bot_fallback_match(waiting_player, deck_json, sid, reason="timeout")
        except Exception as error:
            print("QUEUE BOT FALLBACK ERROR:", type(error).__name__, error)
            self.set_presence_status(sid, "online")
            self.socketio.emit("queue_status", {"msg": "Matchmaking failed. Try Training mode."}, to=sid)
            self.emit_matchmaking_status(sid, "error", mode="bot")
            self.log_event(
                "match",
                "Matchmaking fallback failed",
                details={"error": f"{type(error).__name__}: {error}"},
                user_id=self.safe_user_id(waiting_player),
                level="error",
            )
            self.emit_presence()

    def allow_socket_event(self, event_name, limit=80, window_seconds=10, sid=None, now=None):
        sid = sid or getattr(request, "sid", None) or "unknown"
        key = (sid, event_name)
        current_time = time.monotonic() if now is None else now
        hits = [hit for hit in self.socket_event_hits.get(key, []) if current_time - hit <= window_seconds]

        if len(hits) >= limit:
            self.socket_event_hits[key] = hits
            self.socketio.emit("queue_status", {"msg": "Too many actions. Slow down."}, to=sid)
            return False

        hits.append(current_time)
        self.socket_event_hits[key] = hits
        return True

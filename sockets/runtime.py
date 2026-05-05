import time

from flask import has_app_context, request


class GameSocketRuntime:
    def __init__(self, socketio, deps):
        self.socketio = socketio
        self.active_matches = deps["active_matches"]
        self.player_rooms = deps["player_rooms"]
        self.private_waiting_rooms = deps["private_waiting_rooms"]
        self.socket_state = deps["socket_state"]
        self.socket_event_hits = deps.setdefault("socket_event_hits", {})

        self.app = deps.get("app")
        self.bot_choose_play = deps["bot_choose_play"]
        self.create_player_object = deps["create_player_object"]
        self.emit_log = deps["emit_log"]
        self.emit_state = deps["emit_state"]
        self.log_rc_event = deps["log_rc_event"]
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

    def create_ambitionz_bot(self, deck_json, sid, difficulty="normal"):
        bot_user = type("BotUser", (), {})()
        bot_user.id = 0
        bot_user.username = "Ambitionz Bot"
        bot_user.deck_json = deck_json

        bot_object = self.create_player_object(bot_user, f"bot_{sid}")
        bot_object["name"] = "Ambitionz Bot"
        bot_object["sid"] = f"bot_{sid}"
        bot_object["is_bot"] = True
        bot_object["difficulty"] = difficulty
        return bot_object

    def start_match_between_players(self, waiting_player, player_object, room_id, log_message="PvP match started"):
        self.add_sid_to_room(waiting_player["sid"], room_id)
        self.add_sid_to_room(player_object["sid"], room_id)

        self.active_matches[room_id] = {
            "p1": waiting_player,
            "p2": player_object,
            "round": 1,
            "phase": "Set Phase",
            "resolving": False,
            "logs": [],
        }

        self.player_rooms[waiting_player["sid"]] = room_id
        self.player_rooms[player_object["sid"]] = room_id
        self.set_presence_status(waiting_player["sid"], "in_match")
        self.set_presence_status(player_object["sid"], "in_match")

        self.socketio.emit("match_found", {"msg": "Opponent found. Duel started."}, to=room_id)
        self.emit_matchmaking_status(waiting_player["sid"], "matched", mode="pvp")
        self.emit_matchmaking_status(player_object["sid"], "matched", mode="pvp")
        self.emit_log(room_id, "PvP duel started. Choose an Intent, set cards, then press Ready.")
        self.log_event(
            "match",
            log_message,
            details={"room_id": room_id},
            user_id=self.safe_user_id(waiting_player),
        )
        self.emit_state(room_id)
        self.emit_presence()

    def start_bot_fallback_match(self, player_object, deck_json, sid, reason="timeout"):
        difficulty = "normal"
        bot_object = self.create_ambitionz_bot(deck_json, sid, difficulty)
        room_id = f"quick_bot_{sid}"

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
            "matchmaking_fallback": True,
        }

        self.player_rooms[sid] = room_id
        self.set_presence_status(sid, "in_match")

        self.socketio.emit("queue_status", {"msg": "No online opponent found. Starting bot duel..."}, to=sid)
        self.socketio.emit("match_found", {"msg": "Bot opponent found. Duel started."}, to=sid)
        self.emit_matchmaking_status(sid, "fallback", mode="bot", reason=reason)
        self.emit_log(room_id, "No online opponent was available. Bot duel started automatically.")
        self.emit_log(room_id, "Choose an Intent, set cards, then press Ready.")
        self.log_event(
            "match",
            "Matchmaking fallback bot match started",
            details={"room_id": room_id, "difficulty": difficulty, "reason": reason},
            user_id=self.safe_user_id(player_object),
        )
        self.emit_state(room_id)
        self.emit_presence()

    def play_bot_turn_if_needed(self, match, room_id, player_key):
        if not match.get("is_bot_match") or player_key != "p1" or match["p2"].get("ready"):
            return

        bot_result = self.bot_choose_play(
            match["p2"],
            match["p1"],
            difficulty=match.get("bot_difficulty", "normal"),
        )

        self.emit_log(room_id, f"Ambitionz Bot difficulty: {bot_result.get('profile', match.get('bot_difficulty', 'normal'))}.")
        self.emit_log(room_id, f"Ambitionz Bot chose {bot_result['intent']} intent.")

        if bot_result.get("monster"):
            self.emit_log(room_id, f"Ambitionz Bot set a monster: {bot_result['monster'].get('name', 'Unknown')}.")

        if bot_result.get("spell_or_trap"):
            self.emit_log(room_id, "Ambitionz Bot set a spell/trap.")

        for line in bot_result.get("logs", []):
            self.emit_log(room_id, line)

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

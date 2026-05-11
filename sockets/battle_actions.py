class BattleActionController:
    def __init__(self, socketio, deps, runtime):
        self.socketio = socketio
        self.active_matches = runtime.active_matches
        self.player_rooms = runtime.player_rooms
        self.allow_socket_event = runtime.allow_socket_event
        self.match_engine_factory = runtime.match_engine_factory
        self.play_bot_turn_if_needed = runtime.play_bot_turn_if_needed
        self.release_match_presence = runtime.release_match_presence

        self.can_pay_cost = deps["can_pay_cost"]
        self.cancel_unleash = deps["cancel_unleash"]
        self.current_user = deps["current_user"]
        self.emit_battle_events = deps["emit_battle_events"]
        self.emit_log = deps["emit_log"]
        self.emit_state = deps["emit_state"]
        self.end_match = deps["end_match"]
        self.find_player_key = deps["find_player_key"]
        self.increment_mission = deps["increment_mission"]
        self.normalize_intent = deps["normalize_intent"]
        self.pay_card_cost = deps["pay_card_cost"]
        self.register_card_played_for_ambition = deps["register_card_played_for_ambition"]
        self.request_unleash = deps["request_unleash"]
        self.resolve_battle = deps["resolve_battle"]
        self.set_player_intent = deps["set_player_intent"]

    def _engine(self):
        return self.match_engine_factory()

    def _action_error(self, sid, code, error):
        self.socketio.emit("action_error", {"code": code, "message": str(error)}, to=sid)

    def set_intent(self, sid, data):
        if not self.allow_socket_event("set_intent", sid=sid):
            return

        data = data or {}
        raw_intent = data.get("intent")

        if raw_intent in ["Ambition Unleash", "Overreach"]:
            try:
                self._engine().unleash(sid, message="Ambition Unleash prepared for this battle.")
            except Exception as error:
                self._action_error(sid, "BE2_UNLEASH_FAILED", error)
            return

        intent = self.normalize_intent(raw_intent)
        try:
            self._engine().set_intent(sid, intent, message=f"{intent} selected. Play a creature, spell, guard or support.")
        except Exception as error:
            self._action_error(sid, "BE2_SET_INTENT_FAILED", error)

    def play_to_field(self, sid, data):
        if not self.allow_socket_event("play_to_field", sid=sid):
            return

        data = data or {}
        try:
            self._engine().play_card(
                sid,
                card_id=data.get("card_id") or data.get("id"),
                card_index=data.get("card_index", data.get("index")),
                lane=data.get("lane"),
                target=data.get("target"),
                message="Card played. Press Ready to resolve combat.",
            )
        except Exception as error:
            self._action_error(sid, "BE2_PLAY_CARD_FAILED", error)

    def choose_intent(self, sid, data):
        if not self.allow_socket_event("choose_intent", sid=sid):
            return

        data = data or {}
        intent = data.get("intent", "Strike")

        if intent in ["Ambition Unleash", "Overreach"]:
            try:
                self._engine().unleash(sid, message="Ambition Unleash prepared for this battle.")
            except Exception as error:
                self._action_error(sid, "BE2_UNLEASH_FAILED", error)
            return

        intent = self.normalize_intent(intent)
        try:
            self._engine().set_intent(sid, intent, message=f"{intent} selected. Play a creature, spell, guard or support.")
        except Exception as error:
            self._action_error(sid, "BE2_SET_INTENT_FAILED", error)

    def toggle_unleash(self, sid):
        if not self.allow_socket_event("toggle_unleash", sid=sid):
            return

        try:
            self._engine().unleash(sid, message="Ambition Unleash prepared for this battle.")
        except Exception as error:
            self._action_error(sid, "BE2_UNLEASH_FAILED", error)

    def declare_ready(self, sid):
        if not self.allow_socket_event("declare_ready", sid=sid):
            return

        user = self.current_user()

        if user:
            self.increment_mission(user, "declare_ready_1", 1)

        try:
            self._engine().ready(sid, message="Round resolved.")
        except Exception as error:
            self._action_error(sid, "BE2_READY_FAILED", error)

    def _editable_player_context(self, sid):
        room_id = self.player_rooms.get(sid)

        if not room_id:
            return None

        match = self.active_matches.get(room_id)

        if not match or match["resolving"]:
            return None

        player_key = self.find_player_key(match, sid)

        if not player_key:
            return None

        player = match[player_key]

        if player["ready"]:
            return None

        return room_id, match, player_key, player

    def _prepare_unleash(self, room_id, sid, player, success_message, private_success=False):
        success = self.request_unleash(player)

        if success:
            user = self.current_user()

            if user:
                self.increment_mission(user, "use_overreach_1", 1)

            if private_success:
                self.socketio.emit("battle_log", {"msg": success_message}, to=sid)
            else:
                self.emit_log(room_id, success_message)
        else:
            self.socketio.emit(
                "battle_log",
                {"msg": "You need 5 Ambition and a monster on the field to unleash."},
                to=sid,
            )

        self.emit_state(room_id)

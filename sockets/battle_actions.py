class BattleActionController:
    def __init__(self, socketio, deps, runtime):
        self.socketio = socketio
        self.active_matches = runtime.active_matches
        self.player_rooms = runtime.player_rooms
        self.allow_socket_event = runtime.allow_socket_event
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

    def set_intent(self, sid, data):
        if not self.allow_socket_event("set_intent", sid=sid):
            return

        context = self._editable_player_context(sid)

        if not context:
            return

        room_id, _match, _player_key, player = context
        data = data or {}
        raw_intent = data.get("intent")

        if raw_intent in ["Ambition Unleash", "Overreach"]:
            self._prepare_unleash(
                room_id,
                sid,
                player,
                success_message="Ambition Unleash prepared for this battle.",
                private_success=True,
            )
            return

        intent = self.normalize_intent(raw_intent)
        self.set_player_intent(player, intent)

        self.socketio.emit("battle_log", {"msg": f"{player['name']} chose {intent} intent."}, to=sid)
        self.emit_state(room_id)

    def play_to_field(self, sid, data):
        if not self.allow_socket_event("play_to_field", sid=sid):
            return

        context = self._editable_player_context(sid)

        if not context:
            return

        room_id, match, _player_key, player = context
        data = data or {}

        try:
            index = int(data.get("index"))
        except Exception:
            return

        if index < 0 or index >= len(player["hand"]):
            return

        card = player["hand"][index]
        card_type = card.get("type")
        card_cost = int(card.get("cost", 1))

        if not self.can_pay_cost(player, card):
            self.socketio.emit(
                "battle_log",
                {"msg": f"{player['name']} tried to play {card['name']}, but needs {card_cost} energy."},
                to=sid,
            )
            return

        if card_type == "Monster":
            if player["field_m"] is not None:
                self.emit_log(room_id, f"{player['name']} tried to play another monster, but the monster zone is occupied.")
                return

            self.pay_card_cost(player, card)
            player["field_m"] = player["hand"].pop(index)
            self.register_card_played_for_ambition(player, card, match.setdefault("logs", []))
            self.emit_log(room_id, f"{player['name']} set a monster: {card['name']} for {card_cost} energy.")

        elif card_type in ["Spell", "Trap"]:
            if player["field_st"] is not None:
                self.emit_log(room_id, f"{player['name']} tried to play another spell/trap, but the zone is occupied.")
                return

            self.pay_card_cost(player, card)
            player["field_st"] = player["hand"].pop(index)
            self.register_card_played_for_ambition(player, card, match.setdefault("logs", []))
            self.emit_log(room_id, f"{player['name']} set a spell/trap: {card['name']} for {card_cost} energy.")

        self.emit_state(room_id)

    def choose_intent(self, sid, data):
        if not self.allow_socket_event("choose_intent", sid=sid):
            return

        context = self._editable_player_context(sid)

        if not context:
            return

        room_id, _match, _player_key, player = context
        data = data or {}
        intent = data.get("intent", "Strike")

        if intent in ["Ambition Unleash", "Overreach"]:
            self._prepare_unleash(
                room_id,
                sid,
                player,
                success_message=f"{player['name']} prepared Ambition Unleash for this battle.",
            )
            return

        intent = self.normalize_intent(intent)
        self.set_player_intent(player, intent)

        self.emit_log(room_id, f"{player['name']} selected {player['intent']} intent.")
        self.emit_state(room_id)

    def toggle_unleash(self, sid):
        if not self.allow_socket_event("toggle_unleash", sid=sid):
            return

        context = self._editable_player_context(sid)

        if not context:
            return

        room_id, _match, _player_key, player = context

        if player.get("wants_unleash"):
            self.cancel_unleash(player)
            self.emit_log(room_id, f"{player['name']} cancelled Ambition Unleash.")
        else:
            self._prepare_unleash(
                room_id,
                sid,
                player,
                success_message=f"{player['name']} prepared Ambition Unleash for this battle.",
            )
            return

        self.emit_state(room_id)

    def declare_ready(self, sid):
        if not self.allow_socket_event("declare_ready", sid=sid):
            return

        context = self._editable_player_context(sid)

        if not context:
            return

        room_id, match, player_key, player = context
        player["ready"] = True

        user = self.current_user()

        if user:
            self.increment_mission(user, "declare_ready_1", 1)

        self.emit_log(room_id, f"{player['name']} is ready.")
        self.emit_state(room_id)

        if match.get("is_bot_match") and player_key == "p1" and not match["p2"]["ready"]:
            self.play_bot_turn_if_needed(match, room_id, player_key)
            self.emit_log(room_id, f"{match['p2']['name']} is ready.")
            self.emit_state(room_id)

        if match["p1"]["ready"] and match["p2"]["ready"]:
            battle_result = self.resolve_battle(match)

            try:
                events = battle_result.get("events", [])
                self.emit_battle_events(match, events)
                match.setdefault("v2_events", []).extend(events)
            except Exception as error:
                print("V2 BATTLE EVENTS EMIT ERROR:", type(error).__name__, error)

            for log_message in battle_result["logs"]:
                self.emit_log(room_id, log_message)

            self.emit_state(room_id)

            if battle_result["winner"]:
                finished_match = match
                self.end_match(room_id, battle_result["winner"])
                self.release_match_presence(finished_match)

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

import time

from flask import has_app_context, request, session
from flask_socketio import join_room


def register_game_socket_handlers(socketio, deps):
    active_matches = deps["active_matches"]
    player_rooms = deps["player_rooms"]
    private_waiting_rooms = deps["private_waiting_rooms"]
    socket_state = deps["socket_state"]
    socket_event_hits = deps.setdefault("socket_event_hits", {})

    db = deps["db"]
    User = deps["User"]

    bot_choose_play = deps["bot_choose_play"]
    can_pay_cost = deps["can_pay_cost"]
    cancel_unleash = deps["cancel_unleash"]
    create_player_object = deps["create_player_object"]
    current_user = deps["current_user"]
    emit_battle_events = deps["emit_battle_events"]
    emit_log = deps["emit_log"]
    emit_state = deps["emit_state"]
    end_match = deps["end_match"]
    find_player_key = deps["find_player_key"]
    increment_mission = deps["increment_mission"]
    is_valid_room_code = deps["is_valid_room_code"]
    log_rc_event = deps["log_rc_event"]
    normalize_intent = deps["normalize_intent"]
    normalize_room_code = deps["normalize_room_code"]
    pay_card_cost = deps["pay_card_cost"]
    register_card_played_for_ambition = deps["register_card_played_for_ambition"]
    request_unleash = deps["request_unleash"]
    resolve_battle = deps["resolve_battle"]
    safe_user_id = deps["safe_user_id"]
    set_player_intent = deps["set_player_intent"]
    app = deps.get("app")

    socket_state.setdefault("waiting_player", None)
    socket_state.setdefault("waiting_since", None)
    socket_state.setdefault("waiting_deck_json", None)
    socket_state.setdefault("queue_generation", 0)
    socket_state.setdefault("online_players", {})

    def matchmaking_fallback_seconds():
        try:
            return max(0.0, float(app.config.get("MATCHMAKING_BOT_FALLBACK_SECONDS", 10)))
        except Exception:
            return 10.0

    def online_players():
        return socket_state.setdefault("online_players", {})

    def set_presence_status(sid, status):
        player = online_players().get(sid)

        if player:
            player["status"] = status

    def presence_payload():
        online = online_players()
        return {
            "online": len(online),
            "queued": 1 if socket_state.get("waiting_player") else 0,
            "active_matches": len(active_matches),
            "pvp_matches": sum(1 for match in active_matches.values() if not match.get("is_bot_match")),
            "bot_matches": sum(1 for match in active_matches.values() if match.get("is_bot_match")),
        }

    def emit_presence(to=None):
        payload = presence_payload()

        if to:
            socketio.emit("presence_update", payload, to=to)
        else:
            socketio.emit("presence_update", payload)

    def emit_matchmaking_status(sid, status, **extra):
        payload = {
            "status": status,
            "fallback_seconds": matchmaking_fallback_seconds(),
            **extra,
        }
        socketio.emit("matchmaking_status", payload, to=sid)

    def log_event(*args, **kwargs):
        if app and not has_app_context():
            with app.app_context():
                return log_rc_event(*args, **kwargs)

        return log_rc_event(*args, **kwargs)

    def add_sid_to_room(sid, room_id):
        socketio.server.enter_room(sid, room_id, namespace="/")

    def clear_waiting_player():
        socket_state["waiting_player"] = None
        socket_state["waiting_since"] = None
        socket_state["waiting_deck_json"] = None
        socket_state["queue_generation"] = int(socket_state.get("queue_generation", 0) or 0) + 1

    def release_match_presence(match):
        for player_key in ("p1", "p2"):
            sid = match.get(player_key, {}).get("sid")

            if sid and sid in online_players():
                set_presence_status(sid, "online")

        emit_presence()

    def create_ambitionz_bot(deck_json, sid, difficulty="normal"):
        bot_user = type("BotUser", (), {})()
        bot_user.id = 0
        bot_user.username = "Ambitionz Bot"
        bot_user.deck_json = deck_json

        bot_object = create_player_object(bot_user, f"bot_{sid}")
        bot_object["name"] = "Ambitionz Bot"
        bot_object["sid"] = f"bot_{sid}"
        bot_object["is_bot"] = True
        bot_object["difficulty"] = difficulty
        return bot_object

    def start_match_between_players(waiting_player, player_object, room_id, log_message="PvP match started"):
        add_sid_to_room(waiting_player["sid"], room_id)
        add_sid_to_room(player_object["sid"], room_id)

        active_matches[room_id] = {
            "p1": waiting_player,
            "p2": player_object,
            "round": 1,
            "phase": "Set Phase",
            "resolving": False,
            "logs": [],
        }

        player_rooms[waiting_player["sid"]] = room_id
        player_rooms[player_object["sid"]] = room_id
        set_presence_status(waiting_player["sid"], "in_match")
        set_presence_status(player_object["sid"], "in_match")

        socketio.emit("match_found", {"msg": "Opponent found. Duel started."}, to=room_id)
        emit_matchmaking_status(waiting_player["sid"], "matched", mode="pvp")
        emit_matchmaking_status(player_object["sid"], "matched", mode="pvp")
        emit_log(room_id, "PvP duel started. Choose an Intent, set cards, then press Ready.")
        log_event(
            "match",
            log_message,
            details={"room_id": room_id},
            user_id=safe_user_id(waiting_player),
        )
        emit_state(room_id)
        emit_presence()

    def start_bot_fallback_match(player_object, deck_json, sid, reason="timeout"):
        difficulty = "normal"
        bot_object = create_ambitionz_bot(deck_json, sid, difficulty)
        room_id = f"quick_bot_{sid}"

        add_sid_to_room(sid, room_id)

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
            "matchmaking_fallback": True,
        }

        player_rooms[sid] = room_id
        set_presence_status(sid, "in_match")

        socketio.emit("queue_status", {"msg": "No online opponent found. Starting bot duel..."}, to=sid)
        socketio.emit("match_found", {"msg": "Bot opponent found. Duel started."}, to=sid)
        emit_matchmaking_status(sid, "fallback", mode="bot", reason=reason)
        emit_log(room_id, "No online opponent was available. Bot duel started automatically.")
        emit_log(room_id, "Choose an Intent, set cards, then press Ready.")
        log_event(
            "match",
            "Matchmaking fallback bot match started",
            details={"room_id": room_id, "difficulty": difficulty, "reason": reason},
            user_id=safe_user_id(player_object),
        )
        emit_state(room_id)
        emit_presence()

    def play_bot_turn_if_needed(match, room_id, player_key):
        if not match.get("is_bot_match") or player_key != "p1" or match["p2"].get("ready"):
            return

        bot_result = bot_choose_play(
            match["p2"],
            match["p1"],
            difficulty=match.get("bot_difficulty", "normal"),
        )

        emit_log(room_id, f"Ambitionz Bot difficulty: {bot_result.get('profile', match.get('bot_difficulty', 'normal'))}.")
        emit_log(room_id, f"Ambitionz Bot chose {bot_result['intent']} intent.")

        if bot_result.get("monster"):
            emit_log(room_id, f"Ambitionz Bot set a monster: {bot_result['monster'].get('name', 'Unknown')}.")

        if bot_result.get("spell_or_trap"):
            emit_log(room_id, "Ambitionz Bot set a spell/trap.")

        for line in bot_result.get("logs", []):
            emit_log(room_id, line)

    def run_fallback_after_timeout(sid, queue_generation, fallback_seconds):
        socketio.sleep(fallback_seconds)

        waiting_player = socket_state.get("waiting_player")

        if not waiting_player or waiting_player.get("sid") != sid:
            return

        if int(socket_state.get("queue_generation", 0) or 0) != int(queue_generation):
            return

        if sid in player_rooms or sid not in online_players():
            clear_waiting_player()
            emit_presence()
            return

        deck_json = socket_state.get("waiting_deck_json")
        clear_waiting_player()

        try:
            start_bot_fallback_match(waiting_player, deck_json, sid, reason="timeout")
        except Exception as error:
            print("QUEUE BOT FALLBACK ERROR:", type(error).__name__, error)
            set_presence_status(sid, "online")
            socketio.emit("queue_status", {"msg": "Matchmaking failed. Try Training mode."}, to=sid)
            emit_matchmaking_status(sid, "error", mode="bot")
            log_event(
                "match",
                "Matchmaking fallback failed",
                details={"error": f"{type(error).__name__}: {error}"},
                user_id=safe_user_id(waiting_player),
                level="error",
            )
            emit_presence()


    def allow_socket_event(event_name, limit=80, window_seconds=10):
        sid = getattr(request, "sid", None) or "unknown"
        key = (sid, event_name)
        now = time.monotonic()
        hits = [hit for hit in socket_event_hits.get(key, []) if now - hit <= window_seconds]

        if len(hits) >= limit:
            socket_event_hits[key] = hits
            socketio.emit("queue_status", {"msg": "Too many actions. Slow down."}, to=sid)
            return False

        hits.append(now)
        socket_event_hits[key] = hits
        return True

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
        if not allow_socket_event("set_intent"):
            return

        data = data or {}
        room_id = player_rooms.get(request.sid)

        if not room_id:
            return

        match = active_matches.get(room_id)

        if not match or match["resolving"]:
            return

        player_key = find_player_key(match, request.sid)

        if not player_key:
            return

        player = match[player_key]

        if player["ready"]:
            return

        raw_intent = data.get("intent")

        if raw_intent in ["Ambition Unleash", "Overreach"]:
            success = request_unleash(player)

            if success:
                user = current_user()

                if user:
                    increment_mission(user, "use_overreach_1", 1)

                socketio.emit("battle_log", {"msg": "Ambition Unleash prepared for this battle."}, to=request.sid)
            else:
                socketio.emit("battle_log", {"msg": "You need 5 Ambition and a monster on the field to unleash."}, to=request.sid)

            emit_state(room_id)
            return

        intent = normalize_intent(raw_intent)
        set_player_intent(player, intent)

        socketio.emit("battle_log", {"msg": f"{player['name']} chose {intent} intent."}, to=request.sid)
        emit_state(room_id)

    @socketio.on("play_to_field")
    def play_to_field(data):
        if not allow_socket_event("play_to_field"):
            return

        data = data or {}
        room_id = player_rooms.get(request.sid)

        if not room_id:
            return

        match = active_matches.get(room_id)

        if not match or match["resolving"]:
            return

        player_key = find_player_key(match, request.sid)

        if not player_key:
            return

        player = match[player_key]

        if player["ready"]:
            return

        try:
            index = int(data.get("index"))
        except Exception:
            return

        if index < 0 or index >= len(player["hand"]):
            return

        card = player["hand"][index]
        card_type = card.get("type")
        card_cost = int(card.get("cost", 1))

        if not can_pay_cost(player, card):
            socketio.emit(
                "battle_log",
                {"msg": f"{player['name']} tried to play {card['name']}, but needs {card_cost} energy."},
                to=request.sid,
            )
            return

        if card_type == "Monster":
            if player["field_m"] is not None:
                emit_log(room_id, f"{player['name']} tried to play another monster, but the monster zone is occupied.")
                return

            pay_card_cost(player, card)
            player["field_m"] = player["hand"].pop(index)
            register_card_played_for_ambition(player, card, match.setdefault("logs", []))
            emit_log(room_id, f"{player['name']} set a monster: {card['name']} for {card_cost} energy.")

        elif card_type in ["Spell", "Trap"]:
            if player["field_st"] is not None:
                emit_log(room_id, f"{player['name']} tried to play another spell/trap, but the zone is occupied.")
                return

            pay_card_cost(player, card)
            player["field_st"] = player["hand"].pop(index)
            register_card_played_for_ambition(player, card, match.setdefault("logs", []))
            emit_log(room_id, f"{player['name']} set a spell/trap: {card['name']} for {card_cost} energy.")

        emit_state(room_id)

    @socketio.on("choose_intent")
    def choose_intent(data):
        if not allow_socket_event("choose_intent"):
            return

        data = data or {}
        room_id = player_rooms.get(request.sid)

        if not room_id:
            return

        match = active_matches.get(room_id)

        if not match or match["resolving"]:
            return

        player_key = find_player_key(match, request.sid)

        if not player_key:
            return

        player = match[player_key]

        if player["ready"]:
            return

        intent = data.get("intent", "Strike")

        if intent in ["Ambition Unleash", "Overreach"]:
            success = request_unleash(player)

            if success:
                user = current_user()

                if user:
                    increment_mission(user, "use_overreach_1", 1)

                emit_log(room_id, f"{player['name']} prepared Ambition Unleash for this battle.")
            else:
                socketio.emit(
                    "battle_log",
                    {"msg": "You need 5 Ambition and a monster on the field to unleash."},
                    to=request.sid,
                )

            emit_state(room_id)
            return

        intent = normalize_intent(intent)
        set_player_intent(player, intent)

        emit_log(room_id, f"{player['name']} selected {player['intent']} intent.")
        emit_state(room_id)

    @socketio.on("toggle_unleash")
    def toggle_unleash():
        if not allow_socket_event("toggle_unleash"):
            return

        room_id = player_rooms.get(request.sid)

        if not room_id:
            return

        match = active_matches.get(room_id)

        if not match or match["resolving"]:
            return

        player_key = find_player_key(match, request.sid)

        if not player_key:
            return

        player = match[player_key]

        if player["ready"]:
            return

        if player.get("wants_unleash"):
            cancel_unleash(player)
            emit_log(room_id, f"{player['name']} cancelled Ambition Unleash.")
        else:
            success = request_unleash(player)

            if success:
                user = current_user()

                if user:
                    increment_mission(user, "use_overreach_1", 1)

                emit_log(room_id, f"{player['name']} prepared Ambition Unleash for this battle.")
            else:
                socketio.emit(
                    "battle_log",
                    {"msg": "You need 5 Ambition and a monster on the field to unleash."},
                    to=request.sid,
                )

        emit_state(room_id)

    @socketio.on("declare_ready")
    def declare_ready():
        if not allow_socket_event("declare_ready"):
            return

        room_id = player_rooms.get(request.sid)

        if not room_id:
            return

        match = active_matches.get(room_id)

        if not match or match["resolving"]:
            return

        player_key = find_player_key(match, request.sid)

        if not player_key:
            return

        player = match[player_key]
        player["ready"] = True

        user = current_user()

        if user:
            increment_mission(user, "declare_ready_1", 1)

        emit_log(room_id, f"{player['name']} is ready.")
        emit_state(room_id)

        if match.get("is_bot_match") and player_key == "p1" and not match["p2"]["ready"]:
            play_bot_turn_if_needed(match, room_id, player_key)
            emit_log(room_id, f"{match['p2']['name']} is ready.")
            emit_state(room_id)

        if match["p1"]["ready"] and match["p2"]["ready"]:
            battle_result = resolve_battle(match)

            try:
                events = battle_result.get("events", [])
                emit_battle_events(match, events)
                match.setdefault("v2_events", []).extend(events)
            except Exception as error:
                print("V2 BATTLE EVENTS EMIT ERROR:", type(error).__name__, error)

            for log_message in battle_result["logs"]:
                emit_log(room_id, log_message)

            emit_state(room_id)

            if battle_result["winner"]:
                finished_match = match
                end_match(room_id, battle_result["winner"])
                release_match_presence(finished_match)

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

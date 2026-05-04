import time

from flask import request, session
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
    bot_play_turn = deps["bot_play_turn"]
    can_pay_cost = deps["can_pay_cost"]
    cancel_unleash = deps["cancel_unleash"]
    create_bot_player = deps["create_bot_player"]
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
    def start_match_between_players(waiting_player, player_object, room_id):
        join_room(room_id, sid=waiting_player["sid"])
        join_room(room_id, sid=player_object["sid"])

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

        socketio.emit("match_found", {"msg": "Opponent found. Duel started."}, to=room_id)
        emit_log(room_id, "Private duel started. Choose an Intent, set cards, then press Ready.")
        log_rc_event(
            "match",
            "Private PvP match started",
            details={"room_id": room_id},
            user_id=safe_user_id(waiting_player),
        )
        emit_state(room_id)


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

            socketio.emit("match_found", {"msg": "Training started against Ambitionz Bot."}, to=sid)
            emit_log(room_id, "Training started. Choose an Intent, set cards, then press Ready.")
            log_rc_event(
                "match",
                "Training match started",
                details={"room_id": room_id, "difficulty": difficulty},
                user_id=user.id,
            )
            emit_state(room_id)

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
            return

        if waiting_player and waiting_player.get("sid") not in player_rooms:
            room_id = f"room_{waiting_player['sid']}_{current_sid}"

            join_room(room_id, sid=waiting_player["sid"])
            join_room(room_id, sid=current_sid)

            active_matches[room_id] = {
                "p1": waiting_player,
                "p2": player_object,
                "round": 1,
                "phase": "Set Phase",
                "resolving": False,
                "logs": [],
            }

            player_rooms[waiting_player["sid"]] = room_id
            player_rooms[current_sid] = room_id

            socket_state["waiting_player"] = None

            socketio.emit("match_found", {"msg": "Opponent found. Duel started."}, to=room_id)
            emit_log(room_id, "PvP match started. Choose an Intent, set cards, then press Ready.")
            log_rc_event(
                "match",
                "PvP match started",
                details={"room_id": room_id},
                user_id=safe_user_id(waiting_player),
            )
            emit_state(room_id)
            return

        socket_state["waiting_player"] = None

        try:
            bot_user = type("BotUser", (), {})()
            bot_user.id = 0
            bot_user.username = "Ambitionz Bot"
            bot_user.deck_json = user.deck_json

            bot_object = create_player_object(bot_user, f"bot_{current_sid}")
            bot_object["name"] = "Ambitionz Bot"
            bot_object["sid"] = f"bot_{current_sid}"
            bot_object["is_bot"] = True
            bot_object["difficulty"] = "normal"

            room_id = f"quick_bot_{current_sid}"

            join_room(room_id, sid=current_sid)

            active_matches[room_id] = {
                "p1": player_object,
                "p2": bot_object,
                "round": 1,
                "phase": "Set Phase",
                "resolving": False,
                "logs": [],
                "training": True,
                "is_bot_match": True,
                "bot_difficulty": "normal",
                "matchmaking_fallback": True,
            }

            player_rooms[current_sid] = room_id

            socketio.emit("queue_status", {"msg": "No online opponent found. Starting bot duel..."}, to=current_sid)
            socketio.emit("match_found", {"msg": "Bot opponent found. Duel started."}, to=current_sid)
            emit_log(room_id, "No online opponent was available. Bot duel started automatically.")
            emit_log(room_id, "Choose an Intent, set cards, then press Ready.")
            log_rc_event(
                "match",
                "Matchmaking fallback bot match started",
                details={"room_id": room_id, "difficulty": "normal"},
                user_id=user.id,
            )
            emit_state(room_id)

        except Exception as error:
            print("QUEUE BOT FALLBACK ERROR:", type(error).__name__, error)
            socketio.emit("queue_status", {"msg": "Matchmaking failed. Try Training mode."}, to=current_sid)
            log_rc_event(
                "match",
                "Matchmaking fallback failed",
                details={"error": f"{type(error).__name__}: {error}"},
                user_id=user.id,
                level="error",
            )

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

        intent = normalize_intent(data.get("intent"))
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
        set_player_intent(player, intent)

        if intent == "Overreach":
            user = current_user()

            if user:
                increment_mission(user, "use_overreach_1", 1)

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

        if match.get("training"):
            enemy_key = "p2" if player_key == "p1" else "p1"
            enemy = match[enemy_key]

            bot_result = bot_choose_play(enemy, player, difficulty=match.get("bot_difficulty", "normal"))
            emit_log(room_id, f"Ambitionz Bot difficulty: {bot_result.get('profile', match.get('bot_difficulty', 'normal'))}.")
            emit_log(room_id, f"Ambitionz Bot chose {bot_result['intent']} intent.")

            if bot_result.get("monster"):
                emit_log(room_id, f"Ambitionz Bot set a monster: {bot_result['monster'].get('name', 'Unknown')}.")

            if bot_result.get("spell_or_trap"):
                emit_log(room_id, "Ambitionz Bot set a spell/trap.")

        emit_log(room_id, f"{player['name']} is ready.")
        emit_state(room_id)

        if match.get("is_bot_match") and player_key == "p1" and not match["p2"]["ready"]:
            bot_play_turn(match["p2"], match.setdefault("logs", []))
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
                end_match(room_id, battle_result["winner"])

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

        player_object = create_player_object(user, current_sid)
        bot_object = create_bot_player(user.deck_json)

        room_id = f"bot_{current_sid}"

        join_room(room_id, sid=current_sid)

        active_matches[room_id] = {
            "p1": player_object,
            "p2": bot_object,
            "round": 1,
            "phase": "Set Phase",
            "resolving": False,
            "logs": [],
            "is_bot_match": True,
        }

        player_rooms[current_sid] = room_id

        socketio.emit("match_found", {"msg": "Training match started against bot."}, to=current_sid)

        emit_log(room_id, "Training match started.")
        emit_log(room_id, f"Opponent: {bot_object['name']}.")
        emit_state(room_id)

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
            socketio.emit("queue_status", {"msg": f"Private room {code} created. Waiting for opponent..."}, to=current_sid)
            return

        waiting = private_waiting_rooms.get(code)

        if waiting["sid"] == current_sid:
            socketio.emit("queue_status", {"msg": f"Waiting in private room {code}..."}, to=current_sid)
            return

        room_id = f"private_{code}_{waiting['sid']}_{current_sid}"

        start_match_between_players(waiting, player_object, room_id)

        private_waiting_rooms.pop(code, None)

    @socketio.on("disconnect")
    def handle_disconnect(reason=None):
        sid = request.sid

        for hit_key in list(socket_event_hits.keys()):
            try:
                if hit_key[0] == sid:
                    socket_event_hits.pop(hit_key, None)
            except Exception:
                continue

        waiting_player = socket_state.get("waiting_player")

        if waiting_player and waiting_player["sid"] == sid:
            log_rc_event("match", "Player left PvP queue", user_id=safe_user_id(waiting_player))
            socket_state["waiting_player"] = None
            return

        for room_code, private_player in list(private_waiting_rooms.items()):
            if private_player["sid"] == sid:
                private_waiting_rooms.pop(room_code, None)
                log_rc_event(
                    "match",
                    "Player left private room queue",
                    details={"room_code": room_code},
                    user_id=safe_user_id(private_player),
                )
                return

        room_id = player_rooms.get(sid)

        if not room_id:
            return

        match = active_matches.get(room_id)

        if not match:
            return

        player_key = find_player_key(match, sid)

        if not player_key:
            return

        enemy_key = "p2" if player_key == "p1" else "p1"
        enemy = match[enemy_key]

        if not enemy.get("is_bot") and enemy.get("sid"):
            socketio.emit("opponent_left", {"msg": "Opponent disconnected. You win."}, to=enemy["sid"])

        log_rc_event(
            "match",
            "Player disconnected from active match",
            details={"room_id": room_id, "player_key": player_key},
            user_id=safe_user_id(match[player_key]),
            level="warning",
        )

        end_match(room_id, enemy_key)

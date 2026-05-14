from flask import request, session

from services.arena_command_v1 import arena_command_error_payload, normalize_arena_command
from sockets.battle_actions import BattleActionController
from sockets.lifecycle import SocketLifecycleController
from sockets.matchmaking import MatchmakingController
from sockets.runtime import GameSocketRuntime


def register_game_socket_handlers(socketio, deps):
    runtime = GameSocketRuntime(socketio, deps)

    battle_actions = BattleActionController(socketio, deps, runtime)
    lifecycle = SocketLifecycleController(socketio, deps, runtime)
    matchmaking = MatchmakingController(socketio, deps, runtime)

    def with_campaign_context(data=None):
        payload = dict(data or {})
        chapter_id = str(session.get("campaign_chapter_id") or "").strip()

        if chapter_id and not payload.get("campaign_chapter_id"):
            payload["campaign_chapter_id"] = chapter_id
            payload["campaign_title"] = session.get("campaign_chapter_title")
            payload["campaign_difficulty"] = session.get("campaign_chapter_difficulty")
            payload["campaign_reward"] = session.get("campaign_chapter_reward")

        return payload

    @socketio.on("connect")
    def handle_connect(auth=None):
        lifecycle.connect(request.sid, session.get("user_id"))

    @socketio.on("join_training")
    def handle_join_training(data=None):
        user = lifecycle.user_from_id(session.get("user_id"))

        if not user:
            return

        matchmaking.join_training(request.sid, user, with_campaign_context(data))

    @socketio.on("join_queue")
    def handle_join_queue():
        user = lifecycle.user_from_id(session.get("user_id"))

        if not user:
            return

        matchmaking.join_queue(request.sid, user)

    @socketio.on("cancel_queue")
    def handle_cancel_queue():
        matchmaking.cancel_queue(request.sid)

    @socketio.on("arena_command_v1")
    def arena_command_v1(data=None):
        try:
            command = normalize_arena_command(data or {})
        except Exception as error:
            socketio.emit("action_error", arena_command_error_payload(error), to=request.sid)
            return

        action = command["action"]

        if action == "start_training":
            user = lifecycle.user_from_id(session.get("user_id"))
            if user:
                matchmaking.join_training(request.sid, user, with_campaign_context(command))
            return

        if action == "request_state":
            payload = runtime.match_engine_factory().emit_state(request.sid)
            if not payload:
                user = lifecycle.user_from_id(session.get("user_id"))
                if user:
                    matchmaking.join_training(request.sid, user, with_campaign_context(command))
            return

        if action == "set_intent":
            battle_actions.set_intent(request.sid, {"intent": command.get("intent")})
            return

        if action == "play_card":
            battle_actions.play_to_field(request.sid, command)
            return

        if action == "ready":
            battle_actions.declare_ready(request.sid)
            return

        if action == "unleash":
            battle_actions.toggle_unleash(request.sid)
            return

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
        user = lifecycle.user_from_id(session.get("user_id"))

        if not user:
            return

        matchmaking.join_bot_match(request.sid, user)

    @socketio.on("join_private_room")
    def handle_join_private_room(data):
        user = lifecycle.user_from_id(session.get("user_id"))

        if not user:
            return

        matchmaking.join_private_room(request.sid, user, data)

    @socketio.on("disconnect")
    def handle_disconnect(reason=None):
        lifecycle.disconnect(request.sid)

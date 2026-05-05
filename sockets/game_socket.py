from flask import request, session

from sockets.battle_actions import BattleActionController
from sockets.lifecycle import SocketLifecycleController
from sockets.matchmaking import MatchmakingController
from sockets.runtime import GameSocketRuntime


def register_game_socket_handlers(socketio, deps):
    runtime = GameSocketRuntime(socketio, deps)

    battle_actions = BattleActionController(socketio, deps, runtime)
    lifecycle = SocketLifecycleController(socketio, deps, runtime)
    matchmaking = MatchmakingController(socketio, deps, runtime)

    @socketio.on("connect")
    def handle_connect(auth=None):
        lifecycle.connect(request.sid, session.get("user_id"))

    @socketio.on("join_training")
    def handle_join_training(data=None):
        user = lifecycle.user_from_id(session.get("user_id"))

        if not user:
            return

        matchmaking.join_training(request.sid, user, data)

    @socketio.on("join_queue")
    def handle_join_queue():
        user = lifecycle.user_from_id(session.get("user_id"))

        if not user:
            return

        matchmaking.join_queue(request.sid, user)

    @socketio.on("cancel_queue")
    def handle_cancel_queue():
        matchmaking.cancel_queue(request.sid)

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

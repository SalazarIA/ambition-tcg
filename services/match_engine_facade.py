"""Canonical match-engine facade for Arena Clean clients.

This keeps socket handlers thin while BE2 becomes the source of truth for
training, bot and future PvP renderers.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, Tuple

from services.battle_engine_v2_adapter import (
    be2_play_card,
    be2_ready,
    be2_set_intent,
    be2_start,
    be2_unleash,
    build_be2_arena_payload,
    create_be2_bot_match,
    create_be2_match_from_players,
    create_be2_training_match,
    side_for_sid,
)

EmitFn = Callable[..., None]
Match = Dict[str, Any]
Payload = Dict[str, Any]


_MATCH_LOCKS: Dict[str, threading.RLock] = {}
_MATCH_LOCKS_GUARD = threading.Lock()


def _lock_for_room(room_code: str) -> threading.RLock:
    with _MATCH_LOCKS_GUARD:
        lock = _MATCH_LOCKS.get(room_code)
        if lock is None:
            lock = threading.RLock()
            _MATCH_LOCKS[room_code] = lock
        return lock


class MatchEngineFacade:
    def __init__(
        self,
        active_matches: Dict[str, Match],
        player_rooms: Dict[str, str],
        emit: EmitFn,
        finish_match: Optional[Callable[[str, Match], None]] = None,
    ):
        self.active_matches = active_matches
        self.player_rooms = player_rooms
        self.emit = emit
        self.finish_match = finish_match

    @staticmethod
    def room_for_sid(sid: str) -> str:
        return f"be2_training_{sid}"

    @staticmethod
    def is_finished(match: Optional[Match]) -> bool:
        return bool(match and (match.get("winner") or str(match.get("phase") or "").lower() == "finished"))

    def match_for_sid(self, sid: str) -> Tuple[Optional[str], Optional[Match]]:
        room_code = self.player_rooms.get(sid)

        if room_code and room_code in self.active_matches:
            match = self.active_matches.get(room_code)
            if isinstance(match, dict) and match.get("be2"):
                return room_code, match

        room_code = self.room_for_sid(sid)
        match = self.active_matches.get(room_code)

        if isinstance(match, dict) and match.get("be2"):
            self.player_rooms[sid] = room_code
            return room_code, match

        return None, None

    def emit_state(self, sid: str, message: Optional[str] = None) -> Optional[Payload]:
        room_code, match = self.match_for_sid(sid)

        if not match:
            return None

        payload = build_be2_arena_payload(match, message=message, viewer_side=side_for_sid(match, sid))
        self.emit("az48_state", payload, room=sid)
        self.emit("game_state_update", payload, room=sid)

        if payload.get("winner"):
            result = "WIN" if payload.get("winner") == "player" else ("LOSE" if payload.get("winner") == "opponent" else "DRAW")
            self.emit("game_over", {"result": result}, room=sid)
            self.finalize_if_finished(room_code, match)

        return payload

    def emit_match_state(self, room_code: str, message: Optional[str] = None) -> Optional[Match]:
        match = self.active_matches.get(room_code)

        if not isinstance(match, dict) or not match.get("be2"):
            return None

        for side in ("player", "opponent"):
            sid = (match.get(side) or {}).get("sid")
            if not sid:
                continue

            payload = build_be2_arena_payload(match, message=message, viewer_side=side)
            self.emit("az48_state", payload, room=sid)
            self.emit("game_state_update", payload, room=sid)

            if payload.get("winner"):
                result = "WIN" if payload.get("winner") == "player" else ("LOSE" if payload.get("winner") == "opponent" else "DRAW")
                self.emit("game_over", {"result": result}, room=sid)

        self.finalize_if_finished(room_code, match)
        return match

    def finalize_if_finished(self, room_code: Optional[str], match: Optional[Match]) -> None:
        if not room_code or not match or not self.finish_match:
            return

        if match.get("be2_finalized"):
            return

        if not self.is_finished(match):
            return

        match["be2_finalized"] = True
        self.finish_match(room_code, match)

    @contextmanager
    def match_lock(self, room_code: Optional[str]):
        if not room_code:
            yield
            return

        lock = _lock_for_room(room_code)
        with lock:
            yield

    def _processed_actions(self, match: Match) -> Dict[str, Payload]:
        actions = match.setdefault("processed_actions", {})
        if not isinstance(actions, dict):
            match["processed_actions"] = {}
            return match["processed_actions"]
        return actions

    def _action_key(self, match: Match, sid: str, action: str, action_id: Optional[str]) -> Optional[str]:
        if not action_id:
            return None

        side = side_for_sid(match, sid)
        round_number = int(match.get("round") or 0)
        return f"{round_number}:{side}:{action}:{action_id}"

    def _emit_idempotent(self, sid: str, match: Match, action_key: Optional[str], message: Optional[str]) -> Optional[Payload]:
        if not action_key:
            return None

        processed = self._processed_actions(match)
        if action_key not in processed:
            return None

        return self.emit_state(sid, message=message or "Action already processed.")

    def _mark_processed(self, match: Match, action_key: Optional[str]) -> None:
        if not action_key:
            return

        processed = self._processed_actions(match)
        processed[action_key] = {
            "round": int(match.get("round") or 0),
            "phase": str(match.get("phase") or ""),
            "winner": match.get("winner"),
        }

        if len(processed) > 128:
            keys = list(processed.keys())
            for key in keys[:-128]:
                processed.pop(key, None)

    def emit_finished_guard(self, sid: str) -> Optional[Payload]:
        return self.emit_state(sid, message="Match finished. Start a new training match or go back to Arena.")

    def start_training(self, sid: str, user: Any = None, message: str = "Battle Engine V2 started.") -> Optional[Payload]:
        room_code = self.room_for_sid(sid)
        match = create_be2_training_match(user=user, sid=sid)
        be2_start(match)

        self.active_matches[room_code] = match
        self.player_rooms[sid] = room_code

        self.emit("battle_log", {"message": message}, room=sid)
        return self.emit_state(sid, message=message)

    def start_bot_match(
        self,
        sid: str,
        user: Any = None,
        room_code: Optional[str] = None,
        message: str = "Battle Engine V2 bot match started.",
        matchmaking_fallback: bool = False,
    ) -> Optional[Payload]:
        room_code = room_code or f"be2_bot_{sid}"
        match = create_be2_bot_match(user=user, sid=sid, room_code=room_code, matchmaking_fallback=matchmaking_fallback)
        be2_start(match)

        self.active_matches[room_code] = match
        self.player_rooms[sid] = room_code

        self.emit("battle_log", {"message": message}, room=sid)
        return self.emit_state(sid, message=message)

    def start_bot_match_for_player(
        self,
        player_object: Match,
        room_code: str,
        message: str = "Battle Engine V2 bot match started.",
        matchmaking_fallback: bool = False,
    ) -> Optional[Match]:
        sid = player_object.get("sid")
        proxy_user = type("BE2QueuedUser", (), {})()
        proxy_user.id = player_object.get("user_id")
        proxy_user.username = player_object.get("name") or "Player"
        match = create_be2_bot_match(user=proxy_user, sid=sid, room_code=room_code, matchmaking_fallback=matchmaking_fallback)
        be2_start(match)

        self.active_matches[room_code] = match
        if sid:
            self.player_rooms[sid] = room_code
            self.emit("battle_log", {"message": message}, room=sid)

        return self.emit_match_state(room_code, message=message)

    def start_pvp_match(
        self,
        waiting_player: Match,
        player_object: Match,
        room_code: str,
        message: str = "Battle Engine V2 PvP duel started.",
    ) -> Optional[Match]:
        match = create_be2_match_from_players(waiting_player, player_object, room_code)
        be2_start(match)

        self.active_matches[room_code] = match
        self.player_rooms[waiting_player["sid"]] = room_code
        self.player_rooms[player_object["sid"]] = room_code

        self.emit("battle_log", {"message": message}, room=room_code)
        return self.emit_match_state(room_code, message=message)

    def set_intent(self, sid: str, intent: str, message: Optional[str] = None, action_id: Optional[str] = None) -> Optional[Payload]:
        room_code, match = self.match_for_sid(sid)

        with self.match_lock(room_code):
            if not match:
                return None
            if self.is_finished(match):
                return self.emit_finished_guard(sid)

            action_key = self._action_key(match, sid, "set_intent", action_id)
            idempotent = self._emit_idempotent(sid, match, action_key, message)
            if idempotent:
                return idempotent

            be2_set_intent(match, intent, side=side_for_sid(match, sid))
            self._mark_processed(match, action_key)
            if room_code:
                self.emit_match_state(room_code, message=message)
            return self.emit_state(sid, message=message)

    def play_card(
        self,
        sid: str,
        card_id: Optional[str] = None,
        card_index: Optional[int] = None,
        message: Optional[str] = None,
        action_id: Optional[str] = None,
        target_id: Optional[str] = None,
        lane: Optional[str] = None,
    ) -> Optional[Payload]:
        room_code, match = self.match_for_sid(sid)

        with self.match_lock(room_code):
            if not match:
                return None
            if self.is_finished(match):
                return self.emit_finished_guard(sid)

            action_key = self._action_key(match, sid, "play_card", action_id)
            idempotent = self._emit_idempotent(sid, match, action_key, message)
            if idempotent:
                return idempotent

            be2_play_card(
                match,
                card_id=card_id,
                card_index=card_index,
                side=side_for_sid(match, sid),
                target_id=target_id,
                lane=lane,
            )
            self._mark_processed(match, action_key)
            if room_code:
                self.emit_match_state(room_code, message=message)
            return self.emit_state(sid, message=message)

    def ready(self, sid: str, message: Optional[str] = None, action_id: Optional[str] = None) -> Optional[Payload]:
        room_code, match = self.match_for_sid(sid)

        with self.match_lock(room_code):
            if not match:
                return None
            if self.is_finished(match):
                return self.emit_finished_guard(sid)

            action_key = self._action_key(match, sid, "ready", action_id)
            idempotent = self._emit_idempotent(sid, match, action_key, message)
            if idempotent:
                return idempotent

            before_round = int(match.get("round") or 0)
            before_phase = str(match.get("phase") or "")
            current_side = side_for_sid(match, sid)
            other_side = "opponent" if current_side == "player" else "player"
            other_was_ready = bool((match.get(other_side) or {}).get("ready") or (match.get(other_side) or {}).get("is_bot"))

            be2_ready(match, side=current_side)
            self._mark_processed(match, action_key)

            resolved = (
                bool(match.get("winner")) or
                int(match.get("round") or 0) != before_round or
                str(match.get("phase") or "") != before_phase or
                other_was_ready
            )

            if room_code and resolved:
                self.emit_match_state(room_code, message=message)
                return self.emit_state(sid, message=message)

            return self.emit_state(sid, message=message)

    def unleash(self, sid: str, message: Optional[str] = None, action_id: Optional[str] = None) -> Optional[Payload]:
        room_code, match = self.match_for_sid(sid)

        with self.match_lock(room_code):
            if not match:
                return None
            if self.is_finished(match):
                return self.emit_finished_guard(sid)

            action_key = self._action_key(match, sid, "unleash", action_id)
            idempotent = self._emit_idempotent(sid, match, action_key, message)
            if idempotent:
                return idempotent

            be2_unleash(match, side=side_for_sid(match, sid))
            self._mark_processed(match, action_key)
            if room_code:
                self.emit_match_state(room_code, message=message)
            return self.emit_state(sid, message=message)

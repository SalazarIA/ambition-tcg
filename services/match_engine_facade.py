"""Canonical match-engine facade for Arena Clean clients.

This keeps socket handlers thin while BE2 becomes the source of truth for
training, bot and future PvP renderers.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from services.arena_command_v1 import normalize_arena_command
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

    def emit_finished_guard(self, sid: str) -> Optional[Payload]:
        return self.emit_state(sid, message="Match finished. Start a new training match or go back to Arena.")

    @staticmethod
    def normalize_difficulty(value: Optional[str]) -> str:
        difficulty = str(value or "normal").strip().lower()
        return difficulty if difficulty in {"easy", "normal", "hard"} else "normal"

    @staticmethod
    def campaign_context_from_command(command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        chapter_id = str(command.get("campaign_chapter_id") or "").strip()[:80]
        if not chapter_id:
            return None
        return {
            "chapter_id": chapter_id,
            "title": str(command.get("campaign_title") or "Campaign Chapter")[:120],
            "difficulty": MatchEngineFacade.normalize_difficulty(command.get("campaign_difficulty") or command.get("difficulty")),
            "reward": str(command.get("campaign_reward") or "Campaign reward preview.")[:220],
        }

    def start_training(
        self,
        sid: str,
        user: Any = None,
        message: str = "Battle Engine V2 started.",
        difficulty: str = "normal",
        campaign_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Payload]:
        room_code = self.room_for_sid(sid)
        difficulty = self.normalize_difficulty(difficulty)
        match = create_be2_training_match(user=user, sid=sid, difficulty=difficulty)

        if campaign_context:
            match["mode"] = "campaign"
            match["campaign_chapter_id"] = str(campaign_context.get("chapter_id") or "")[:80]
            match["campaign"] = {
                "chapter_id": match["campaign_chapter_id"],
                "title": str(campaign_context.get("title") or "Campaign Chapter")[:120],
                "difficulty": self.normalize_difficulty(campaign_context.get("difficulty") or difficulty),
                "reward": str(campaign_context.get("reward") or "Campaign reward preview.")[:220],
            }
            match["bot_difficulty"] = match["campaign"]["difficulty"]

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
        training: bool = False,
        difficulty: str = "normal",
        campaign_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Payload]:
        room_code = room_code or f"be2_bot_{sid}"
        match = create_be2_bot_match(
            user=user,
            sid=sid,
            room_code=room_code,
            matchmaking_fallback=matchmaking_fallback,
            training=training,
            difficulty=difficulty,
        )
        if campaign_context:
            match["mode"] = "campaign"
            match["campaign_chapter_id"] = str(campaign_context.get("chapter_id") or "")[:80]
            match["campaign"] = {
                "chapter_id": match["campaign_chapter_id"],
                "title": str(campaign_context.get("title") or "Campaign Chapter")[:120],
                "difficulty": str(campaign_context.get("difficulty") or difficulty or "normal")[:40],
                "reward": str(campaign_context.get("reward") or "Campaign reward preview.")[:220],
            }
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

    def set_intent(self, sid: str, intent: str, message: Optional[str] = None) -> Optional[Payload]:
        room_code, match = self.match_for_sid(sid)

        if not match:
            raise ValueError("No active BE2 match.")
        if self.is_finished(match):
            return self.emit_finished_guard(sid)

        be2_set_intent(match, intent, side=side_for_sid(match, sid))
        if room_code:
            self.emit_match_state(room_code, message=message)
        return self.emit_state(sid, message=message)

    def play_card(
        self,
        sid: str,
        card_id: Optional[str] = None,
        card_index: Optional[int] = None,
        lane: Optional[str] = None,
        target: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Optional[Payload]:
        room_code, match = self.match_for_sid(sid)

        if not match:
            raise ValueError("No active BE2 match.")
        if self.is_finished(match):
            return self.emit_finished_guard(sid)

        be2_play_card(match, card_id=card_id, card_index=card_index, side=side_for_sid(match, sid), lane=lane, target=target)
        if room_code:
            self.emit_match_state(room_code, message=message)
        return self.emit_state(sid, message=message)

    def ready(self, sid: str, message: Optional[str] = None) -> Optional[Payload]:
        room_code, match = self.match_for_sid(sid)

        if not match:
            raise ValueError("No active BE2 match.")
        if self.is_finished(match):
            return self.emit_finished_guard(sid)

        before_round = int(match.get("round") or 0)
        before_phase = str(match.get("phase") or "")
        current_side = side_for_sid(match, sid)
        other_side = "opponent" if current_side == "player" else "player"
        other_was_ready = bool((match.get(other_side) or {}).get("ready") or (match.get(other_side) or {}).get("is_bot"))

        be2_ready(match, side=current_side)

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

    def unleash(self, sid: str, message: Optional[str] = None) -> Optional[Payload]:
        room_code, match = self.match_for_sid(sid)

        if not match:
            raise ValueError("No active BE2 match.")
        if self.is_finished(match):
            return self.emit_finished_guard(sid)

        be2_unleash(match, side=side_for_sid(match, sid))
        if room_code:
            self.emit_match_state(room_code, message=message)
        return self.emit_state(sid, message=message)

    def run_command(
        self,
        sid: str,
        payload: Optional[Dict[str, Any]] = None,
        user: Any = None,
    ) -> Optional[Payload]:
        command = normalize_arena_command(payload)
        action = command["action"]

        if action == "start_training":
            difficulty = self.normalize_difficulty(command.get("difficulty"))
            campaign_context = self.campaign_context_from_command(command)
            return self.start_training(
                sid,
                user=user,
                message=(
                    "Campaign chapter started. Choose an intent, then play a card or press Ready."
                    if campaign_context
                    else f"{difficulty.title()} Training started. Choose an intent, then play a card or press Ready."
                ),
                difficulty=difficulty,
                campaign_context=campaign_context,
            )

        if action == "request_state":
            state = self.emit_state(sid)
            if state:
                return state
            if user is not None:
                difficulty = self.normalize_difficulty(command.get("difficulty"))
                campaign_context = self.campaign_context_from_command(command)
                return self.start_training(
                    sid,
                    user=user,
                    message=(
                        "Campaign chapter started. Choose an intent, then play a card or press Ready."
                        if campaign_context
                        else f"{difficulty.title()} Training started. Choose an intent, then play a card or press Ready."
                    ),
                    difficulty=difficulty,
                    campaign_context=campaign_context,
                )
            raise ValueError("No active BE2 match.")

        if action == "set_intent":
            intent = str(command.get("intent") or "Focus")
            return self.set_intent(sid, intent, message=f"{intent} selected. Play a creature, spell, guard or support.")

        if action == "play_card":
            return self.play_card(
                sid,
                card_id=command.get("card_id"),
                card_index=command.get("card_index"),
                lane=command.get("lane"),
                target=command.get("target"),
                message="Card played. Press Ready to resolve combat.",
            )

        if action == "ready":
            return self.ready(sid, message="Round resolved.")

        if action == "unleash":
            return self.unleash(sid, message="Ambition Unleash prepared. Press Ready to resolve.")

        raise ValueError("Invalid arena command.")

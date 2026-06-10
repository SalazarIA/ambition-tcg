"""Deterministic replay helpers for Rebirth matches."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List

from services.rebirth_domain import (
    CARD_SET_VERSION,
    ENGINE_VERSION,
    REDUCER_VERSION,
    REPLAY_FORMAT_VERSION,
    REPLAY_SCHEMA_VERSION,
    RULESET_VERSION,
    canonical_state_hash,
)
from services.rebirth_dispatcher import (
    DeclareAttackCommand,
    EndTurnCommand,
    EvolveDuplicateCommand,
    FuseFieldPairCommand,
    MulliganCommand,
    SummonCardCommand,
    dispatch_command,
)
from services.rebirth_engine import start_match
from services.rebirth_contracts import RebirthError
from services.rebirth_profiler import current_profiler


SUPPORTED_COMMANDS = {"PLAY_CARD", "DECLARE_ATTACK", "EVOLVE_DUPLICATE", "FUSE_FIELD_PAIR", "NEXT_TURN", "MULLIGAN"}


def build_replay_envelope(match: Dict[str, Any], *, include_stream: bool = True) -> Dict[str, Any]:
    initial = deepcopy(match.get("initial") or {})
    final_hash = canonical_state_hash(match)
    player_uses_default_deck = bool(initial.get("player_uses_default_deck", False))
    bot_uses_default_deck = bool(initial.get("bot_uses_default_deck", False))
    initial_payload = {
        "player_card_ids": [] if player_uses_default_deck else list(initial.get("player_card_ids") or []),
        "bot_card_ids": [] if bot_uses_default_deck else list(initial.get("bot_card_ids") or []),
        "player_uses_default_deck": player_uses_default_deck,
        "bot_uses_default_deck": bot_uses_default_deck,
        "player_name": initial.get("player_name") or (match.get("player") or {}).get("name") or "Voc\u00ea",
        "bot_profile_id": initial.get("bot_profile_id") or (match.get("bot_profile") or {}).get("id"),
        "first_duel": bool(initial.get("first_duel", False)),
        "shuffle": bool(initial.get("shuffle", True)),
    }
    if initial.get("campaign_node"):
        initial_payload.update(
            {
                "player_hp": int(initial.get("player_hp", 30) or 30),
                "bot_hp": int(initial.get("bot_hp", 30) or 30),
                "campaign_version": initial.get("campaign_version"),
                "campaign_node": initial.get("campaign_node"),
                "campaign_attempt": int(initial.get("campaign_attempt", 1) or 1),
                "campaign_modifiers": deepcopy(initial.get("campaign_modifiers") or []),
                "campaign_presentation": deepcopy(initial.get("campaign_presentation") or {}),
                "campaign_advice": deepcopy(initial.get("campaign_advice") or {}),
            }
        )
    envelope = {
        "format_version": REPLAY_FORMAT_VERSION,
        "replay_schema_version": REPLAY_SCHEMA_VERSION,
        "engine_version": match.get("engine_version") or ENGINE_VERSION,
        "card_set_version": match.get("card_set_version") or CARD_SET_VERSION,
        "ruleset_version": match.get("ruleset_version") or RULESET_VERSION,
        "reducer_version": match.get("reducer_version") or REDUCER_VERSION,
        "match_id": match.get("match_id"),
        "game_seed": str(match.get("game_seed", match.get("seed", "")) or ""),
        "deterministic_seed": str(match.get("game_seed", match.get("seed", "")) or ""),
        "display_seed": str(match.get("seed", "") or ""),
        "initial": initial_payload,
        "commands": deepcopy(match.get("commands") or []),
        "checkpoints": deepcopy(match.get("checkpoints") or []),
        "expected_canonical_state_hash": final_hash,
        "canonical_state_hash": final_hash,
        "replay_frame_count": len(match.get("events") or []),
    }
    if include_stream:
        envelope["snapshots"] = deepcopy(match.get("snapshots") or [])
        envelope["events"] = deepcopy(match.get("events") or [])
    return envelope


def replay_stream_frames(match: Dict[str, Any], *, after_frame: int = 0) -> List[Dict[str, Any]]:
    """Return already-resolved frames for spectators without re-execution."""
    threshold = max(0, int(after_frame or 0))
    return [
        deepcopy(event)
        for event in match.get("events") or []
        if int(event.get("replay_frame", event.get("sequence_id", 0)) or 0) > threshold
    ]


def build_sync_payload(
    match: Dict[str, Any],
    *,
    after_command_id: int = 0,
    after_frame: int = 0,
) -> Dict[str, Any]:
    """Build the minimal deterministic wire-ready payload, without transport."""
    command_threshold = max(0, int(after_command_id or 0))
    frame_threshold = max(0, int(after_frame or 0))
    commands = [
        deepcopy(command)
        for command in match.get("commands") or []
        if int(command.get("id", 0) or 0) > command_threshold
    ]
    frames = replay_stream_frames(match, after_frame=frame_threshold)
    checkpoints = [
        deepcopy(checkpoint)
        for checkpoint in match.get("checkpoints") or []
        if int(checkpoint.get("replay_frame", 0) or 0) > frame_threshold
    ]
    return {
        "format_version": REPLAY_FORMAT_VERSION,
        "replay_schema_version": REPLAY_SCHEMA_VERSION,
        "engine_version": match.get("engine_version") or ENGINE_VERSION,
        "card_set_version": match.get("card_set_version") or CARD_SET_VERSION,
        "ruleset_version": match.get("ruleset_version") or RULESET_VERSION,
        "reducer_version": match.get("reducer_version") or REDUCER_VERSION,
        "match_id": match.get("match_id"),
        "game_seed": str(match.get("game_seed", match.get("seed", "")) or ""),
        "commands": commands,
        "replay_frames": frames,
        "checkpoints": checkpoints,
        "latest_command_id": len(match.get("commands") or []),
        "latest_replay_frame": int((match.get("events") or [{}])[-1].get("replay_frame", 0) or 0),
        "canonical_state_hash": canonical_state_hash(match),
    }


def _commands_from(source: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    commands = source.get("commands") or []
    return sorted(commands, key=lambda command: int(command.get("id", 0) or 0))


def _assert_replay_versions(envelope: Dict[str, Any]) -> None:
    engine_version = envelope.get("engine_version")
    card_set_version = envelope.get("card_set_version")
    if engine_version != ENGINE_VERSION:
        raise RebirthError(f"Replay engine incompativel: {engine_version}", "replay_engine_mismatch", status=409)
    if card_set_version != CARD_SET_VERSION:
        raise RebirthError(f"Replay card set incompativel: {card_set_version}", "replay_card_set_mismatch", status=409)
    if envelope.get("ruleset_version") != RULESET_VERSION:
        raise RebirthError(f"Replay ruleset incompativel: {envelope.get('ruleset_version')}", "replay_ruleset_mismatch", status=409)
    if envelope.get("reducer_version") != REDUCER_VERSION:
        raise RebirthError(f"Replay reducer incompativel: {envelope.get('reducer_version')}", "replay_reducer_mismatch", status=409)
    if envelope.get("replay_schema_version") != REPLAY_SCHEMA_VERSION:
        raise RebirthError(f"Replay schema incompativel: {envelope.get('replay_schema_version')}", "replay_schema_mismatch", status=409)


def replay_match(source: Dict[str, Any]) -> Dict[str, Any]:
    envelope = build_replay_envelope(source, include_stream=False) if source.get("match_id") and "format_version" not in source else deepcopy(source)
    _assert_replay_versions(envelope)
    profiler = current_profiler()
    initial = envelope.get("initial") or {}
    match = start_match(
        seed=envelope.get("game_seed"),
        player_card_ids=initial.get("player_card_ids") or None,
        player_name=initial.get("player_name") or "Voc\u00ea",
        bot_profile_id=initial.get("bot_profile_id"),
        runtime_mode="replay",
        apply_reducers_inline=True,
        bot_card_ids=initial.get("bot_card_ids") or None,
        player_hp=initial.get("player_hp"),
        bot_hp=initial.get("bot_hp"),
        campaign_version=initial.get("campaign_version"),
        campaign_node=initial.get("campaign_node"),
        campaign_attempt=initial.get("campaign_attempt"),
        campaign_modifiers=initial.get("campaign_modifiers"),
        campaign_presentation=initial.get("campaign_presentation"),
        campaign_advice=initial.get("campaign_advice"),
        first_duel=bool(initial.get("first_duel", False)),
        shuffle=bool(initial.get("shuffle", True)),
    )
    match["seed"] = str(envelope.get("display_seed", "") or "")

    replay_timer = profiler.timer("replay_cost", detail="replay_match") if profiler else None
    if replay_timer:
        replay_timer.__enter__()
    try:
        for command in _commands_from(envelope):
            command_type = str(command.get("type") or "")
            payload = command.get("payload") or {}
            if command_type not in SUPPORTED_COMMANDS:
                raise RebirthError(f"Comando de replay nao suportado: {command_type}", "replay_command_unsupported", status=409)
            frame_timer = profiler.timer("replay_cost", detail=command_type) if profiler else None
            if frame_timer:
                frame_timer.__enter__()
            try:
                if command_type == "PLAY_CARD":
                    dispatch_command(
                        match,
                        SummonCardCommand(
                            card_instance_id=payload.get("card_instance_id"),
                            card_id=payload.get("card_id"),
                            field_slot=payload.get("field_slot"),
                            target_instance_id=payload.get("target_instance_id"),
                        ),
                    )
                elif command_type == "MULLIGAN":
                    dispatch_command(match, MulliganCommand())
                elif command_type == "DECLARE_ATTACK":
                    dispatch_command(
                        match,
                        DeclareAttackCommand(
                            attacker_instance_id=payload.get("attacker_instance_id"),
                            target_instance_id=payload.get("target_instance_id"),
                        ),
                    )
                elif command_type == "EVOLVE_DUPLICATE":
                    dispatch_command(match, EvolveDuplicateCommand(card_id=payload.get("card_id")))
                elif command_type == "FUSE_FIELD_PAIR":
                    dispatch_command(
                        match,
                        FuseFieldPairCommand(
                            player_id=payload.get("player_id"),
                            source_instance_a=payload.get("source_instance_a"),
                            source_instance_b=payload.get("source_instance_b"),
                        ),
                    )
                elif command_type == "NEXT_TURN":
                    dispatch_command(match, EndTurnCommand(turn=payload.get("turn")))
            finally:
                if frame_timer:
                    frame_timer.__exit__(None, None, None)
    finally:
        if replay_timer:
            replay_timer.__exit__(None, None, None)
    return match


def verify_replay(source: Dict[str, Any]) -> Dict[str, Any]:
    envelope = build_replay_envelope(source) if source.get("match_id") and "format_version" not in source else deepcopy(source)
    replayed = replay_match(envelope)
    actual = canonical_state_hash(replayed)
    expected = envelope.get("expected_canonical_state_hash")
    replay_sequence = [int(event.get("sequence_id", event.get("version", 0)) or 0) for event in replayed.get("events", [])]
    replay_frames = [int(event.get("replay_frame", event.get("sequence_id", 0)) or 0) for event in replayed.get("events", [])]
    snapshots = envelope.get("snapshots") or []
    snapshot_hashes_ok = all(
        isinstance(snapshot.get("canonical_state_hash"), str) and len(snapshot.get("canonical_state_hash")) == 64
        for snapshot in snapshots
    )
    return {
        "ok": actual == expected,
        "expected_canonical_state_hash": expected,
        "actual_canonical_state_hash": actual,
        "command_count": len(list(_commands_from(envelope))),
        "snapshot_count": len(snapshots),
        "replay_frame_count": len(replayed.get("events", []) or []),
        "event_ordering_ok": replay_sequence == sorted(replay_sequence),
        "replay_frame_consistency_ok": replay_frames == replay_sequence,
        "snapshot_hash_consistency_ok": snapshot_hashes_ok,
        "engine_version": ENGINE_VERSION,
        "card_set_version": CARD_SET_VERSION,
        "ruleset_version": RULESET_VERSION,
        "reducer_version": REDUCER_VERSION,
        "replay_schema_version": REPLAY_SCHEMA_VERSION,
    }

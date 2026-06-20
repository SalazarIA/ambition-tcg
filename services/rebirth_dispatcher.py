"""Command model and operational dispatcher for deterministic Rebirth actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from services.rebirth_contracts import RebirthError
from services.rebirth_profiler import current_profiler


PIPELINE_STAGES = (
    "COMMAND",
    "VALIDATE",
    "BUILD_EVENT_STACK",
    "RESOLVE_EFFECTS",
    "REDUCER_PHASE",
    "EMIT_EVENTS",
    "PERSIST_SNAPSHOT",
)

PHASED_RESOLUTION_STAGES = (
    "PRE_RESOLUTION",
    "TRIGGER_COLLECTION",
    "PRIORITY_SORT",
    "REDUCER_PHASE",
    "POST_RESOLUTION",
    "CLEANUP_PHASE",
)

PRIORITY_MODEL = (
    ("Replacement Effects", 1),
    ("Interrupts / Traps", 2),
    ("Reactive Spells", 3),
    ("Active Spell Effects", 4),
    ("Passive Triggered Effects", 5),
    ("Delayed / Expiration Effects", 6),
)


def _tag_runtime_mutation(match: Dict[str, Any], origin: str) -> None:
    match["_canonical_hash_dirty"] = True
    match["_last_canonical_state_hash"] = None
    if match.get("_debug_mutation_tracking") or match.get("_parity_tracking_enabled"):
        match["_mutation_dirty"] = True
        match.setdefault("_mutation_origins", []).append(str(origin))


@dataclass(frozen=True)
class RebirthCommand:
    actor: str = "player"
    payload: Dict[str, Any] = field(default_factory=dict)

    @property
    def command_type(self) -> str:
        return self.__class__.__name__.replace("Command", "").upper()

    def as_payload(self) -> Dict[str, Any]:
        return dict(self.payload)


@dataclass(frozen=True)
class SummonCardCommand(RebirthCommand):
    card_instance_id: Optional[str] = None
    card_id: Optional[str] = None
    field_slot: Optional[int] = None
    target_instance_id: Optional[str] = None

    @property
    def command_type(self) -> str:
        return "PLAY_CARD"

    def as_payload(self) -> Dict[str, Any]:
        return {
            "card_instance_id": self.card_instance_id,
            "card_id": self.card_id,
            "field_slot": self.field_slot,
            "target_instance_id": self.target_instance_id,
        }


@dataclass(frozen=True)
class MulliganCommand(RebirthCommand):
    @property
    def command_type(self) -> str:
        return "MULLIGAN"

    def as_payload(self) -> Dict[str, Any]:
        return {}


@dataclass(frozen=True)
class DeclareAttackCommand(RebirthCommand):
    attacker_instance_id: Optional[str] = None
    target_instance_id: Optional[str] = None

    @property
    def command_type(self) -> str:
        return "DECLARE_ATTACK"

    def as_payload(self) -> Dict[str, Any]:
        return {"attacker_instance_id": self.attacker_instance_id, "target_instance_id": self.target_instance_id}


@dataclass(frozen=True)
class EndTurnCommand(RebirthCommand):
    turn: Optional[int] = None

    @property
    def command_type(self) -> str:
        return "NEXT_TURN"

    def as_payload(self) -> Dict[str, Any]:
        return {"turn": self.turn}


@dataclass(frozen=True)
class ApplyEffectCommand(RebirthCommand):
    effect_type: str = ""
    effect_payload: Dict[str, Any] = field(default_factory=dict)

    @property
    def command_type(self) -> str:
        return "APPLY_EFFECT"

    def as_payload(self) -> Dict[str, Any]:
        return {"effect_type": self.effect_type, "effect_payload": dict(self.effect_payload)}


@dataclass(frozen=True)
class EvolveDuplicateCommand(RebirthCommand):
    card_id: Optional[str] = None

    @property
    def command_type(self) -> str:
        return "EVOLVE_DUPLICATE"

    def as_payload(self) -> Dict[str, Any]:
        return {"card_id": self.card_id}


@dataclass(frozen=True)
class FuseFieldPairCommand(RebirthCommand):
    player_id: Optional[str] = None
    source_instance_a: Optional[str] = None
    source_instance_b: Optional[str] = None

    @property
    def command_type(self) -> str:
        return "FUSE_FIELD_PAIR"

    def as_payload(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "source_instance_a": self.source_instance_a,
            "source_instance_b": self.source_instance_b,
        }


class CommandDispatcher:
    """Single operational entrypoint for authoritative Rebirth commands."""

    def dispatch(self, match: Dict[str, Any], command: RebirthCommand):
        if not isinstance(command, RebirthCommand):
            raise RebirthError("Comando Rebirth inválido.", "invalid_command")
        previous_depth = int(match.get("_command_dispatch_depth", 0) or 0)
        invariant_baseline = None
        if previous_depth == 0 and match.get("_validate_invariants_after_command"):
            from services.rebirth_invariants import capture_card_baseline

            invariant_baseline = capture_card_baseline(match)
        command_event_start = len(match.get("events", []) or [])
        match["_command_dispatch_depth"] = previous_depth + 1
        _tag_runtime_mutation(match, f"command:{command.command_type}")
        try:
            from services import rebirth_engine

            def execute_command():
                if isinstance(command, SummonCardCommand):
                    return rebirth_engine.play_card(
                        match,
                        card_instance_id=command.card_instance_id,
                        card_id=command.card_id,
                        field_slot=command.field_slot,
                        target_instance_id=command.target_instance_id,
                    )
                if isinstance(command, MulliganCommand):
                    return rebirth_engine.mulligan(match)
                if isinstance(command, DeclareAttackCommand):
                    return rebirth_engine.declare_attack(
                        match,
                        attacker_instance_id=command.attacker_instance_id,
                        target_instance_id=command.target_instance_id,
                    )
                if isinstance(command, EndTurnCommand):
                    return rebirth_engine.next_turn(match)
                if isinstance(command, EvolveDuplicateCommand):
                    return rebirth_engine.evolve_duplicate(match, command.card_id)
                if isinstance(command, FuseFieldPairCommand):
                    return rebirth_engine.resolve_labs_fusion(
                        match,
                        player_id=command.player_id,
                        source_instance_a=command.source_instance_a,
                        source_instance_b=command.source_instance_b,
                    )
                raise RebirthError(f"Comando não suportado: {command.command_type}", "unsupported_command")

            profiler = current_profiler()
            if profiler:
                with profiler.timer("command_cost", detail=command.command_type):
                    result = execute_command()
            else:
                result = execute_command()
            if previous_depth == 0:
                from services.rebirth_effects import finalize_canonical_state_hash, purge_effect_runtime_caches
                from services.rebirth_events import append_snapshot

                command_event_ids = [
                    int(event.get("event_id", 0) or 0)
                    for event in (match.get("events", []) or [])[command_event_start:]
                    if event.get("event_id")
                ]
                finalize_canonical_state_hash(match, event_ids=command_event_ids)
                append_snapshot(match, "action_checkpoint")
                purge_effect_runtime_caches(match)
                if match.get("_parity_validate_after_command") and match.get("_apply_reducers_inline") is False:
                    from services.rebirth_parity import DeterministicParityRunner

                    DeterministicParityRunner().verify(match)
                if match.get("_validate_invariants_after_command"):
                    from services.rebirth_invariants import validate_rebirth_state

                    validate_rebirth_state(match, baseline=invariant_baseline).raise_if_invalid()
            return result
        finally:
            match["_command_dispatch_depth"] = max(0, int(match.get("_command_dispatch_depth", 1) or 1) - 1)


DEFAULT_COMMAND_DISPATCHER = CommandDispatcher()


def dispatch_command(match: Dict[str, Any], command: RebirthCommand):
    return DEFAULT_COMMAND_DISPATCHER.dispatch(match, command)

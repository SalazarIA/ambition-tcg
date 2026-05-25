"""Command model and pipeline names for the deterministic Rebirth dispatcher."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


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

    @property
    def command_type(self) -> str:
        return "PLAY_CARD"

    def as_payload(self) -> Dict[str, Any]:
        return {"card_instance_id": self.card_instance_id, "card_id": self.card_id, "field_slot": self.field_slot}


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

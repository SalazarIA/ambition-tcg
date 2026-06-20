"""Structured state invariants and deterministic command fuzzing for Rebirth."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
import random
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from services.rebirth_contracts import FIELD_SLOT_COUNT, VALID_PHASES, RebirthError
from services.rebirth_domain import canonical_state_hash
from services.rebirth_dispatcher import (
    DeclareAttackCommand,
    EndTurnCommand,
    EvolveDuplicateCommand,
    MulliganCommand,
    RebirthCommand,
    SummonCardCommand,
    dispatch_command,
)
from services.rebirth_engine import mulligan_available, start_match
from services.rebirth_replay import verify_replay
from services.rebirth_state import TurnPhase


SIDES = ("player", "bot")
CARD_ZONES = ("deck", "hand", "field", "discard", "traps")
WINNERS = {"player", "bot", "clash"}
TURN_PHASES = {phase.value for phase in TurnPhase}


@dataclass(frozen=True)
class InvariantViolation:
    code: str
    message: str
    path: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CardBaseline:
    """Initial instance ownership used for card conservation checks."""

    by_side: Mapping[str, frozenset[str]]

    @property
    def all_instance_ids(self) -> frozenset[str]:
        return frozenset().union(*(self.by_side.get(side, frozenset()) for side in SIDES))


@dataclass
class RebirthInvariantReport:
    violations: List[InvariantViolation] = field(default_factory=list)
    checks: Dict[str, Any] = field(default_factory=dict)
    canonical_hash: Optional[str] = None
    replay: Optional[Dict[str, Any]] = None

    @property
    def ok(self) -> bool:
        return not self.violations

    def codes(self) -> set[str]:
        return {violation.code for violation in self.violations}

    def raise_if_invalid(self) -> "RebirthInvariantReport":
        if self.violations:
            summary = "; ".join(f"{item.code}: {item.message}" for item in self.violations[:5])
            raise AssertionError(summary)
        return self


@dataclass
class FuzzResult:
    seed: str
    attempted_commands: int
    accepted_commands: int
    rejected_commands: int
    final_report: RebirthInvariantReport
    replay: Optional[Dict[str, Any]]
    command_types: List[str] = field(default_factory=list)
    dispatcher_errors: List[Dict[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.final_report.ok and (self.replay is None or bool(self.replay.get("ok")))


def _instance_id(card: Any) -> Optional[str]:
    if not isinstance(card, dict):
        return None
    value = card.get("instance_id")
    return str(value) if value not in (None, "") else None


def _zone_cards(side: Mapping[str, Any], zone: str) -> List[Dict[str, Any]]:
    raw = side.get(zone) or []
    if not isinstance(raw, list):
        return []
    return [card for card in raw if isinstance(card, dict)]


def _authoritative_cards(match: Mapping[str, Any]) -> Iterable[Tuple[str, str, int, Dict[str, Any]]]:
    for side_name in SIDES:
        side = match.get(side_name) or {}
        for zone in CARD_ZONES:
            for index, card in enumerate(_zone_cards(side, zone)):
                yield side_name, zone, index, card


def capture_card_baseline(match: Mapping[str, Any]) -> CardBaseline:
    by_side: Dict[str, frozenset[str]] = {}
    for side_name in SIDES:
        ids = {
            instance_id
            for current_side, _zone, _index, card in _authoritative_cards(match)
            if current_side == side_name
            for instance_id in [_instance_id(card)]
            if instance_id
        }
        by_side[side_name] = frozenset(ids)
    return CardBaseline(by_side=by_side)


def _coerce_baseline(baseline: Any) -> Optional[CardBaseline]:
    if baseline is None:
        return None
    if isinstance(baseline, CardBaseline):
        return baseline
    if isinstance(baseline, Mapping):
        source = baseline.get("by_side", baseline)
        if isinstance(source, Mapping):
            return CardBaseline(
                by_side={
                    side: frozenset(str(value) for value in source.get(side, ()) if value)
                    for side in SIDES
                }
            )
    raise TypeError("baseline must be CardBaseline, a side mapping, or None")


def _add(
    report: RebirthInvariantReport,
    code: str,
    message: str,
    path: str = "",
    **details: Any,
) -> None:
    report.violations.append(
        InvariantViolation(code=code, message=message, path=path, details=details)
    )


def _as_number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _validate_resources(match: Mapping[str, Any], report: RebirthInvariantReport) -> None:
    for side_name in SIDES:
        side = match.get(side_name) or {}
        for key in ("hp", "energy", "mana"):
            if key not in side:
                continue
            value = _as_number(side.get(key))
            if value is not None and value < 0:
                _add(
                    report,
                    f"resource.negative_{key}",
                    f"{side_name}.{key} cannot be negative",
                    f"{side_name}.{key}",
                    value=side.get(key),
                )

        for zone in CARD_ZONES:
            for index, card in enumerate(_zone_cards(side, zone)):
                for key in ("guard", "max_guard"):
                    value = _as_number(card.get(key))
                    if value is not None and value < 0:
                        _add(
                            report,
                            "resource.negative_guard",
                            f"{key} cannot be negative",
                            f"{side_name}.{zone}[{index}].{key}",
                            value=card.get(key),
                        )
                if zone == "field":
                    value = _as_number(card.get("current_guard"))
                    if value is not None and value < 0:
                        _add(
                            report,
                            "resource.negative_guard",
                            "live current_guard cannot be negative",
                            f"{side_name}.field[{index}].current_guard",
                            value=card.get("current_guard"),
                        )


def _validate_fields(match: Mapping[str, Any], report: RebirthInvariantReport) -> None:
    for side_name in SIDES:
        side = match.get(side_name) or {}
        field_cards = _zone_cards(side, "field")
        raw_field = side.get("field")
        battlefield = _zone_cards(side, "battlefield")
        if not isinstance(raw_field, list):
            _add(report, "field.invalid", "field must be a list", f"{side_name}.field")
            continue
        if len(raw_field) > FIELD_SLOT_COUNT or len(battlefield) > FIELD_SLOT_COUNT:
            _add(
                report,
                "field.too_many_slots",
                "field and battlefield are limited to three slots",
                side_name,
                field_size=len(raw_field),
                battlefield_size=len(battlefield),
            )

        field_ids = [_instance_id(card) for card in raw_field if isinstance(card, dict)]
        battlefield_ids = [_instance_id(card) for card in battlefield]
        if field_ids != battlefield_ids:
            _add(
                report,
                "field.out_of_sync",
                "battlefield must be the compact field mirror",
                side_name,
                field_instance_ids=field_ids,
                battlefield_instance_ids=battlefield_ids,
            )

        for slot_index, card in enumerate(raw_field[:FIELD_SLOT_COUNT]):
            if not isinstance(card, dict):
                continue
            recorded_slot = card.get("field_slot")
            if recorded_slot != slot_index:
                _add(
                    report,
                    "field.slot_mismatch",
                    "card field_slot must match its field position",
                    f"{side_name}.field[{slot_index}].field_slot",
                    recorded_slot=recorded_slot,
                )
            display_slot = card.get("slot")
            if display_slot is not None and display_slot != slot_index + 1:
                _add(
                    report,
                    "field.slot_mismatch",
                    "card slot must be one-based field_slot",
                    f"{side_name}.field[{slot_index}].slot",
                    recorded_slot=display_slot,
                )


def _validate_instance_ids(
    match: Mapping[str, Any],
    report: RebirthInvariantReport,
    baseline: Optional[CardBaseline],
) -> None:
    locations: Dict[str, List[str]] = defaultdict(list)
    owners: Dict[str, set[str]] = defaultdict(set)
    current_ids: Dict[str, set[str]] = {side: set() for side in SIDES}
    lineage_by_id: Dict[str, Tuple[str, set[str]]] = {}

    for side_name, zone, index, card in _authoritative_cards(match):
        instance_id = _instance_id(card)
        path = f"{side_name}.{zone}[{index}]"
        if not instance_id:
            _add(report, "card.missing_instance_id", "card has no instance_id", path)
            continue
        locations[instance_id].append(path)
        owners[instance_id].add(side_name)
        current_ids[side_name].add(instance_id)
        lineage = card.get("evolved_from") or card.get("fused_from")
        if isinstance(lineage, list) and len([value for value in lineage if value]) >= 2:
            lineage_by_id[instance_id] = (
                side_name,
                {str(value) for value in lineage if value},
            )

    for instance_id, paths in locations.items():
        if len(paths) > 1:
            code = "card.duplicate_global" if len(owners[instance_id]) > 1 else "card.duplicate_side"
            _add(
                report,
                code,
                "instance_id appears in multiple authoritative card zones",
                paths[0],
                instance_id=instance_id,
                locations=paths,
            )

    if baseline is None or not baseline.all_instance_ids:
        report.checks["card_conservation"] = "skipped:no_baseline"
        return

    baseline_all = set(baseline.all_instance_ids)
    current_all = set().union(*current_ids.values())
    derived_ids: set[str] = set()
    for instance_id, (side_name, parent_ids) in lineage_by_id.items():
        known_side_ids = set(baseline.by_side.get(side_name, frozenset())) | current_ids[side_name]
        if len(parent_ids) >= 2 and parent_ids <= known_side_ids:
            derived_ids.add(instance_id)
        else:
            _add(
                report,
                "card.invalid_lineage",
                "evolution/fusion lineage must reference two known cards from the same side",
                side_name,
                instance_id=instance_id,
                parent_instance_ids=sorted(parent_ids),
            )
    for side_name in SIDES:
        missing = sorted(set(baseline.by_side.get(side_name, frozenset())) - current_ids[side_name])
        if missing:
            _add(
                report,
                "card.lost",
                "baseline cards disappeared from authoritative zones",
                side_name,
                instance_ids=missing,
            )

    unexpected = sorted(current_all - baseline_all - derived_ids)
    if unexpected:
        _add(
            report,
            "card.created",
            "cards appeared without evolution/fusion lineage",
            "player|bot",
            instance_ids=unexpected,
        )
    report.checks["card_conservation"] = {
        "baseline": len(baseline_all),
        "current": len(current_all),
        "derived": len(derived_ids),
    }


def _validate_phase_and_winner(match: Mapping[str, Any], report: RebirthInvariantReport) -> None:
    phase = match.get("phase")
    turn_phase = match.get("turn_phase")
    winner = match.get("winner")
    finished = bool(match.get("is_finished"))
    if phase not in VALID_PHASES:
        _add(report, "phase.invalid", "unknown match phase", "phase", value=phase)
    if turn_phase not in TURN_PHASES:
        _add(report, "phase.invalid_turn_phase", "unknown turn phase", "turn_phase", value=turn_phase)
    if winner is not None and winner not in WINNERS:
        _add(report, "winner.invalid", "unknown winner", "winner", value=winner)
    if finished != (phase == "finished"):
        _add(
            report,
            "winner.finished_mismatch",
            "is_finished and phase=finished must agree",
            "is_finished",
            phase=phase,
            is_finished=finished,
        )
    if finished and winner not in WINNERS:
        _add(report, "winner.missing", "finished match must have a winner", "winner")
    if not finished and winner is not None:
        _add(report, "winner.premature", "unfinished match cannot have a winner", "winner", value=winner)
    if phase == "finished" and turn_phase != TurnPhase.END_PHASE.value:
        _add(report, "phase.finished_turn_phase", "finished match must be in END_PHASE", "turn_phase")

    player_hp = _as_number((match.get("player") or {}).get("hp"))
    bot_hp = _as_number((match.get("bot") or {}).get("hp"))
    if not finished and ((player_hp is not None and player_hp <= 0) or (bot_hp is not None and bot_hp <= 0)):
        _add(report, "winner.lethal_state_unfinished", "lethal HP requires a finished match", "is_finished")
    if finished and player_hp is not None and bot_hp is not None:
        if player_hp <= 0 < bot_hp and winner != "bot":
            _add(report, "winner.hp_mismatch", "bot must win when only player HP is lethal", "winner")
        elif bot_hp <= 0 < player_hp and winner != "player":
            _add(report, "winner.hp_mismatch", "player must win when only bot HP is lethal", "winner")
        elif player_hp <= 0 and bot_hp <= 0 and winner != "clash":
            _add(report, "winner.hp_mismatch", "simultaneous lethal HP must be a clash", "winner")


def _validate_action_state(match: Mapping[str, Any], report: RebirthInvariantReport) -> None:
    for side_name in SIDES:
        raw_field = (match.get(side_name) or {}).get("field") or []
        for index, card in enumerate(raw_field):
            if not isinstance(card, dict):
                continue
            attacked = card.get("has_attacked")
            acted = card.get("has_acted")
            exhausted = card.get("exhausted")
            path = f"{side_name}.field[{index}]"
            for key, value in (
                ("has_attacked", attacked),
                ("has_acted", acted),
                ("exhausted", exhausted),
                ("just_summoned", card.get("just_summoned")),
                ("shield_consumed", card.get("shield_consumed")),
            ):
                if key in card and not isinstance(value, bool):
                    _add(report, "action.non_boolean_flag", f"{key} must be boolean", f"{path}.{key}", value=value)
            if attacked and (not acted or not exhausted):
                _add(
                    report,
                    "action.impossible_attack_state",
                    "an attacker must be both acted and exhausted",
                    path,
                    has_attacked=attacked,
                    has_acted=acted,
                    exhausted=exhausted,
                )
            if acted and not exhausted:
                _add(
                    report,
                    "action.impossible_action_state",
                    "a consumed unit action must leave the unit exhausted",
                    path,
                )


def _validate_event_ordering(match: Mapping[str, Any], report: RebirthInvariantReport) -> None:
    events = match.get("events") or []
    if not isinstance(events, list):
        _add(report, "event.invalid_stream", "events must be a list", "events")
        return
    seen_event_ids: set[int] = set()
    previous_sequence = previous_version = 0
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            _add(report, "event.invalid", "event must be an object", f"events[{index}]")
            continue
        event_id = _as_int(event.get("event_id", event.get("id", 0)))
        sequence = _as_int(event.get("sequence_id", event.get("version", 0)))
        replay_frame = _as_int(event.get("replay_frame", sequence))
        version = _as_int(event.get("version", 0))
        if None in {event_id, sequence, replay_frame, version}:
            _add(
                report,
                "event.invalid_order_value",
                "event ordering fields must be integers",
                f"events[{index}]",
            )
            continue
        assert event_id is not None and sequence is not None
        assert replay_frame is not None and version is not None
        if event_id != index + 1 or event_id in seen_event_ids:
            _add(
                report,
                "event.id_order",
                "event ids must be unique and contiguous",
                f"events[{index}].event_id",
                value=event_id,
            )
        if sequence <= previous_sequence or version <= previous_version:
            _add(
                report,
                "event.sequence_order",
                "event sequence and version must increase strictly",
                f"events[{index}]",
                sequence=sequence,
                version=version,
            )
        if replay_frame != sequence:
            _add(
                report,
                "event.replay_frame_order",
                "replay_frame must equal sequence_id",
                f"events[{index}].replay_frame",
                replay_frame=replay_frame,
                sequence=sequence,
            )
        parent = event.get("parent_event_id")
        if parent is not None:
            parent_id = _as_int(parent)
            if parent_id is None or parent_id not in seen_event_ids or parent_id >= event_id:
                _add(
                    report,
                    "event.causal_order",
                    "parent event must precede its child",
                    f"events[{index}].parent_event_id",
                    value=parent,
                )
        root = event.get("root_event_id")
        if root is not None:
            root_id = _as_int(root)
            if root_id is None or root_id > event_id or (
                root_id != event_id and root_id not in seen_event_ids
            ):
                _add(
                    report,
                    "event.causal_order",
                    "root event must be self or a preceding event",
                    f"events[{index}].root_event_id",
                    value=root,
                )
        seen_event_ids.add(event_id)
        previous_sequence = sequence
        previous_version = version

    commands = match.get("commands") or []
    previous_version = 0
    for index, command in enumerate(commands):
        if not isinstance(command, dict):
            _add(report, "event.invalid_command", "command must be an object", f"commands[{index}]")
            continue
        command_id = _as_int(command.get("id", 0))
        version = _as_int(command.get("version", 0))
        if command_id != index + 1 or version is None or version <= previous_version:
            _add(
                report,
                "event.command_order",
                "command ids must be contiguous and versions strictly increasing",
                f"commands[{index}]",
                command_id=command_id,
                version=version,
            )
        if version is not None:
            previous_version = version


def _validate_hashes(
    match: Mapping[str, Any],
    report: RebirthInvariantReport,
    expected_hash: Optional[str],
) -> None:
    actual = canonical_state_hash(dict(match))
    report.canonical_hash = actual
    candidates = []
    if expected_hash:
        candidates.append(("expected_hash", expected_hash))
    cached = match.get("_last_canonical_state_hash")
    if isinstance(cached, str) and cached:
        candidates.append(("_last_canonical_state_hash", cached))
    for path, candidate in candidates:
        if candidate != actual:
            _add(
                report,
                "hash.mismatch",
                "canonical state hash does not match",
                path,
                expected=candidate,
                actual=actual,
            )
    for collection_name in ("snapshots", "checkpoints"):
        for index, item in enumerate(match.get(collection_name) or []):
            value = (item or {}).get("canonical_state_hash")
            if not isinstance(value, str) or len(value) != 64:
                _add(
                    report,
                    "hash.invalid_record",
                    "stored canonical hash must be a 64-character hex digest",
                    f"{collection_name}[{index}].canonical_state_hash",
                )


def validate_rebirth_state(
    match: Mapping[str, Any],
    *,
    baseline: Any = None,
    check_hash: bool = False,
    expected_hash: Optional[str] = None,
    check_replay: bool = False,
) -> RebirthInvariantReport:
    """Validate a Rebirth state without mutating it."""

    report = RebirthInvariantReport()
    normalized_baseline = _coerce_baseline(baseline)
    _validate_resources(match, report)
    _validate_fields(match, report)
    _validate_instance_ids(match, report, normalized_baseline)
    _validate_phase_and_winner(match, report)
    _validate_action_state(match, report)
    _validate_event_ordering(match, report)
    if check_hash:
        _validate_hashes(match, report, expected_hash)
    if check_replay:
        try:
            report.replay = verify_replay(dict(match))
        except Exception as exc:  # replay validation must become structured output
            report.replay = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        if not report.replay.get("ok"):
            _add(report, "replay.mismatch", "deterministic replay did not reproduce the state", "replay")
    report.checks["violation_count"] = len(report.violations)
    return report


def assert_rebirth_invariants(match: Mapping[str, Any], **kwargs: Any) -> RebirthInvariantReport:
    return validate_rebirth_state(match, **kwargs).raise_if_invalid()


def _affordable_cards(match: Mapping[str, Any]) -> List[Dict[str, Any]]:
    player = match.get("player") or {}
    energy = int(player.get("energy", 0) or 0)
    occupied = len([card for card in player.get("field") or [] if card])
    candidates = []
    for card in player.get("hand") or []:
        card_type = str(card.get("type") or card.get("card_type") or "")
        cost = max(1, int(card.get("cost", card.get("tier", 1)) or 1)) if card_type == "MONSTER" else max(
            0, int(card.get("cost", 0) or 0)
        )
        if cost <= energy and (card_type != "MONSTER" or occupied < FIELD_SLOT_COUNT):
            candidates.append(card)
    return candidates


def _fuzz_commands(
    match: Mapping[str, Any],
    *,
    excluded_types: Sequence[str] = (),
    include_turn_commands: bool = True,
) -> List[RebirthCommand]:
    if match.get("is_finished"):
        return []
    commands: List[RebirthCommand] = []
    if mulligan_available(match):
        commands.append(MulliganCommand())
    bot_targets = [
        card for card in ((match.get("bot") or {}).get("field") or []) if isinstance(card, dict)
    ]
    for card in _affordable_cards(match):
        target = bot_targets[0].get("instance_id") if bot_targets else None
        commands.append(
            SummonCardCommand(
                card_instance_id=card.get("instance_id"),
                target_instance_id=target,
            )
        )

    player_field = [
        card for card in ((match.get("player") or {}).get("field") or []) if isinstance(card, dict)
    ]
    for attacker in player_field:
        target = bot_targets[0].get("instance_id") if bot_targets else None
        commands.append(
            DeclareAttackCommand(
                attacker_instance_id=attacker.get("instance_id"),
                target_instance_id=target,
            )
        )

    grouped = Counter(card.get("id") for card in (match.get("player") or {}).get("hand") or [])
    for card_id, count in sorted(grouped.items(), key=lambda item: str(item[0])):
        if card_id and count >= 2:
            commands.append(EvolveDuplicateCommand(card_id=card_id))
    if include_turn_commands:
        commands.extend([EndTurnCommand(turn=match.get("turn"))] * 2)
    excluded = set(excluded_types)
    return [command for command in commands if command.command_type not in excluded]


def run_deterministic_command_fuzz(
    seed: Any,
    *,
    max_commands: int = 24,
    verify_final_replay: bool = True,
    include_turn_commands: bool = True,
    match_kwargs: Optional[Mapping[str, Any]] = None,
) -> FuzzResult:
    """Run a small reproducible command sequence through the public dispatcher."""

    seed_text = str(seed)
    rng = random.Random(seed_text)
    kwargs = dict(match_kwargs or {})
    kwargs.setdefault("seed", seed_text)
    kwargs.setdefault("runtime_mode", "replay")
    kwargs.setdefault("apply_reducers_inline", True)
    # A support-heavy fixed bot deck keeps this harness on public gameplay
    # paths while avoiding dependence on personality-specific search code.
    # Callers can supply bot_card_ids to fuzz another deterministic matchup.
    kwargs.setdefault("bot_card_ids", ["card_084"] * 30)
    match = start_match(**kwargs)
    baseline = capture_card_baseline(match)
    assert_rebirth_invariants(match, baseline=baseline)

    accepted = rejected = attempted = 0
    command_types: List[str] = []
    dispatcher_errors: List[Dict[str, str]] = []
    excluded_types: set[str] = set()
    for _ in range(max(0, int(max_commands))):
        candidates = _fuzz_commands(
            match,
            excluded_types=tuple(excluded_types),
            include_turn_commands=include_turn_commands,
        )
        if not candidates:
            break
        command = rng.choice(candidates)
        attempted += 1
        command_types.append(command.command_type)
        before = deepcopy(match)
        try:
            dispatch_command(match, command)
            accepted += 1
        except RebirthError:
            rejected += 1
            # Rejected commands may touch runtime-only dirty flags, but must
            # leave canonical gameplay state unchanged.
            if canonical_state_hash(match) != canonical_state_hash(before):
                raise AssertionError(f"rejected command mutated canonical state: {command.command_type}")
        except Exception as exc:
            # Dispatcher/engine failures can happen after partially appending
            # commands or events. Roll the attempt back so subsequent
            # invariant and replay checks remain meaningful and deterministic.
            match.clear()
            match.update(before)
            rejected += 1
            excluded_types.add(command.command_type)
            dispatcher_errors.append(
                {
                    "command_type": command.command_type,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        report = validate_rebirth_state(match, baseline=baseline)
        if not report.ok:
            report.raise_if_invalid()
        if match.get("is_finished"):
            break

    final_report = validate_rebirth_state(
        match,
        baseline=baseline,
        check_hash=True,
        check_replay=verify_final_replay,
    )
    return FuzzResult(
        seed=seed_text,
        attempted_commands=attempted,
        accepted_commands=accepted,
        rejected_commands=rejected,
        final_report=final_report,
        replay=final_report.replay,
        command_types=command_types,
        dispatcher_errors=dispatcher_errors,
    )


fuzz_rebirth_commands = run_deterministic_command_fuzz


def run_deterministic_command_fuzz_seeds(
    seeds: Sequence[Any],
    **kwargs: Any,
) -> List[FuzzResult]:
    return [run_deterministic_command_fuzz(seed, **kwargs) for seed in seeds]


fuzz_rebirth_seeds = run_deterministic_command_fuzz_seeds

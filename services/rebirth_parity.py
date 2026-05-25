"""Runtime parity verification between fast and reducer-backed Rebirth modes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from services.rebirth_domain import canonical_json, canonical_state, canonical_state_hash, serialize_canonical_state
from services.rebirth_reducers import reduce_event
from services.rebirth_replay import build_replay_envelope, replay_match
from services.rebirth_engine import start_match


FAST_RUNTIME_MODE = "singleplayer"
DETERMINISTIC_RUNTIME_MODE = "replay"


class ParityViolationError(RuntimeError):
    def __init__(self, message: str, dump: Dict[str, Any]):
        super().__init__(message)
        self.dump = dump


def _initial_match_from_envelope(envelope: Dict[str, Any]) -> Dict[str, Any]:
    initial = envelope.get("initial") or {}
    match = start_match(
        seed=envelope.get("game_seed"),
        player_card_ids=initial.get("player_card_ids") or None,
        player_name=initial.get("player_name") or "Você",
        bot_profile_id=initial.get("bot_profile_id"),
        runtime_mode=DETERMINISTIC_RUNTIME_MODE,
        apply_reducers_inline=True,
    )
    match["seed"] = str(envelope.get("display_seed", "") or "")
    return match


def state_diff_summary(left: Any, right: Any, *, max_diffs: int = 32) -> List[Dict[str, Any]]:
    diffs: List[Dict[str, Any]] = []

    def walk(path: str, a: Any, b: Any) -> None:
        if len(diffs) >= max_diffs:
            return
        if type(a) is not type(b):
            diffs.append({"path": path, "left": a, "right": b, "reason": "type_mismatch"})
            return
        if isinstance(a, dict):
            keys = sorted(set(a) | set(b))
            for key in keys:
                if key not in a:
                    diffs.append({"path": f"{path}.{key}", "left": None, "right": b[key], "reason": "missing_left"})
                elif key not in b:
                    diffs.append({"path": f"{path}.{key}", "left": a[key], "right": None, "reason": "missing_right"})
                else:
                    walk(f"{path}.{key}", a[key], b[key])
                if len(diffs) >= max_diffs:
                    return
            return
        if isinstance(a, list):
            if len(a) != len(b):
                diffs.append({"path": f"{path}.length", "left": len(a), "right": len(b), "reason": "length_mismatch"})
            for index, (left_item, right_item) in enumerate(zip(a, b)):
                walk(f"{path}[{index}]", left_item, right_item)
                if len(diffs) >= max_diffs:
                    return
            return
        if a != b:
            diffs.append({"path": path, "left": a, "right": b, "reason": "value_mismatch"})

    walk("$", left, right)
    return diffs


def replay_chain_trace(events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    trace = []
    for event in sorted(events or [], key=lambda item: int(item.get("sequence_id", item.get("version", 0)) or 0)):
        trace.append(
            {
                "event_id": int(event.get("event_id", event.get("id", 0)) or 0),
                "sequence_id": int(event.get("sequence_id", event.get("version", 0)) or 0),
                "replay_frame": int(event.get("replay_frame", event.get("sequence_id", 0)) or 0),
                "type": event.get("event_type") or event.get("type"),
                "effect_chain_id": event.get("effect_chain_id"),
                "resolution_phase": event.get("resolution_phase"),
                "priority_level": event.get("priority_level"),
                "parent_event_id": event.get("parent_event_id"),
                "root_event_id": event.get("root_event_id"),
                "canonical_state_hash": event.get("canonical_state_hash"),
            }
        )
    return trace


def effect_chain_ordering(events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "sequence_id": item["sequence_id"],
            "type": item["type"],
            "effect_chain_id": item["effect_chain_id"],
            "resolution_phase": item["resolution_phase"],
            "priority_level": item["priority_level"],
            "parent_event_id": item["parent_event_id"],
            "root_event_id": item["root_event_id"],
        }
        for item in replay_chain_trace(events)
    ]


def compare_checkpoint_hashes(local: Dict[str, Any], remote: Dict[str, Any]) -> Dict[str, Any]:
    """Detect the earliest shared turn boundary that diverges."""
    local_points = {
        (int(item.get("turn", 0) or 0), str(item.get("reason") or "")): item
        for item in local.get("checkpoints") or []
    }
    remote_points = {
        (int(item.get("turn", 0) or 0), str(item.get("reason") or "")): item
        for item in remote.get("checkpoints") or []
    }
    shared = sorted(set(local_points) & set(remote_points))
    for key in shared:
        left = local_points[key]
        right = remote_points[key]
        if left.get("canonical_state_hash") != right.get("canonical_state_hash"):
            return {
                "ok": False,
                "desync_detected": True,
                "turn": key[0],
                "reason": key[1],
                "local_hash": left.get("canonical_state_hash"),
                "remote_hash": right.get("canonical_state_hash"),
            }
    return {
        "ok": True,
        "desync_detected": False,
        "shared_checkpoint_count": len(shared),
        "latest_shared_turn": shared[-1][0] if shared else None,
    }


def runtime_projection(match: Dict[str, Any]) -> Dict[str, Any]:
    state = canonical_state(match)
    return {
        "phase": state.get("phase"),
        "turn_phase": state.get("turn_phase"),
        "turn": state.get("turn"),
        "winner": state.get("winner"),
        "is_finished": state.get("is_finished"),
        "board_entities": {
            "player": {"field": state["player"]["field"], "battlefield": state["player"]["battlefield"]},
            "bot": {"field": state["bot"]["field"], "battlefield": state["bot"]["battlefield"]},
        },
        "player_resources": {
            "hp": state["player"]["hp"],
            "max_hp": state["player"]["max_hp"],
            "energy": state["player"]["energy"],
            "max_energy": state["player"]["max_energy"],
        },
        "bot_resources": {
            "hp": state["bot"]["hp"],
            "max_hp": state["bot"]["max_hp"],
            "energy": state["bot"]["energy"],
            "max_energy": state["bot"]["max_energy"],
        },
        "graveyard_state": {
            "player": state["player"]["discard"],
            "bot": state["bot"]["discard"],
        },
        "active_statuses": {
            "player": {
                "side": state["player"]["statuses"],
                "field": [
                    (card or {}).get("statuses", {}) if isinstance(card, dict) else {}
                    for card in state["player"]["field"]
                ],
            },
            "bot": {
                "side": state["bot"]["statuses"],
                "field": [
                    (card or {}).get("statuses", {}) if isinstance(card, dict) else {}
                    for card in state["bot"]["field"]
                ],
            },
        },
        "result": state.get("result"),
        "last_clash": state.get("last_clash"),
    }


def _reducer_trace(envelope: Dict[str, Any], events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    state = _initial_match_from_envelope(envelope)
    start_index = len(state.get("events", []) or [])
    trace = []
    for index, event in enumerate(list(events or [])[start_index:], start=start_index + 1):
        before_hash = canonical_state_hash(state)
        state = reduce_event(state, event)
        after_hash = canonical_state_hash(state)
        trace.append(
            {
                "frame": index,
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type") or event.get("type"),
                "effect_chain_id": event.get("effect_chain_id"),
                "resolution_phase": event.get("resolution_phase"),
                "before_hash": before_hash,
                "after_hash": after_hash,
            }
        )
    return {"state": state, "hash": canonical_state_hash(state), "trace": trace}


def _first_trace_diff(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for index, (left_item, right_item) in enumerate(zip(left, right)):
        if left_item != right_item:
            return {"index": index, "fast": left_item, "reducer": right_item}
    if len(left) != len(right):
        return {"index": min(len(left), len(right)), "fast_count": len(left), "reducer_count": len(right)}
    return None


def parity_failure_dump(
    fast_match: Dict[str, Any],
    reducer_match: Dict[str, Any],
    checks: Dict[str, Any],
    *,
    envelope: Dict[str, Any],
    fast_reducer_trace: Dict[str, Any],
    reducer_reducer_trace: Dict[str, Any],
) -> Dict[str, Any]:
    fast_state = canonical_state(fast_match)
    reducer_state = canonical_state(reducer_match)
    fast_trace = replay_chain_trace(fast_match.get("events", []))
    reducer_trace = replay_chain_trace(reducer_match.get("events", []))
    return {
        "message": "Rebirth runtime parity violation",
        "match_id": fast_match.get("match_id"),
        "game_seed": envelope.get("game_seed"),
        "runtime_modes": {
            "fast": fast_match.get("_runtime_mode"),
            "reducer": reducer_match.get("_runtime_mode"),
        },
        "checks": checks,
        "hashes": {
            "fast_canonical_state_hash": canonical_state_hash(fast_match),
            "reducer_canonical_state_hash": canonical_state_hash(reducer_match),
            "fast_reducer_state_hash": fast_reducer_trace.get("hash"),
            "reducer_reducer_state_hash": reducer_reducer_trace.get("hash"),
        },
        "phase": {
            "fast": {"phase": fast_match.get("phase"), "turn_phase": fast_match.get("turn_phase"), "turn": fast_match.get("turn")},
            "reducer": {"phase": reducer_match.get("phase"), "turn_phase": reducer_match.get("turn_phase"), "turn": reducer_match.get("turn")},
        },
        "state_diffs": state_diff_summary(fast_state, reducer_state),
        "projection_diffs": state_diff_summary(runtime_projection(fast_match), runtime_projection(reducer_match)),
        "first_event_divergence": _first_trace_diff(fast_trace, reducer_trace),
        "first_reducer_divergence": _first_trace_diff(
            fast_reducer_trace.get("trace", []),
            reducer_reducer_trace.get("trace", []),
        ),
        "replay_trace": {"fast": fast_trace, "reducer": reducer_trace},
        "reducer_trace": {
            "fast": fast_reducer_trace.get("trace", []),
            "reducer": reducer_reducer_trace.get("trace", []),
        },
        "command_log": deepcopy(envelope.get("commands") or []),
        "replay_metadata": {
            "format_version": envelope.get("format_version"),
            "replay_schema_version": envelope.get("replay_schema_version"),
            "engine_version": envelope.get("engine_version"),
            "card_set_version": envelope.get("card_set_version"),
            "ruleset_version": envelope.get("ruleset_version"),
            "reducer_version": envelope.get("reducer_version"),
        },
    }


@dataclass
class DeterministicParityRunner:
    strict: bool = True

    def verify(self, fast_match: Dict[str, Any]) -> Dict[str, Any]:
        if fast_match.get("_apply_reducers_inline") is not False:
            raise ParityViolationError(
                "Parity runner expects a fast runtime match with _apply_reducers_inline=False.",
                {
                    "runtime_mode": fast_match.get("_runtime_mode"),
                    "_apply_reducers_inline": fast_match.get("_apply_reducers_inline"),
                },
            )

        envelope = build_replay_envelope(fast_match, include_stream=False)
        reducer_match = replay_match(envelope)
        fast_reducer_trace = _reducer_trace(envelope, fast_match.get("events", []))
        reducer_reducer_trace = _reducer_trace(envelope, reducer_match.get("events", []))
        fast_bytes = serialize_canonical_state(fast_match)
        reducer_bytes = serialize_canonical_state(reducer_match)
        fast_projection = canonical_json(runtime_projection(fast_match))
        reducer_projection = canonical_json(runtime_projection(reducer_match))

        checks = {
            "canonical_state_hash": canonical_state_hash(fast_match) == canonical_state_hash(reducer_match),
            "reducer_state_hash": fast_reducer_trace["hash"] == reducer_reducer_trace["hash"],
            "byte_equivalent": fast_bytes == reducer_bytes,
            "runtime_projection": fast_projection == reducer_projection,
            "replay_frame_count": len(fast_match.get("events", []) or []) == len(reducer_match.get("events", []) or []),
            "effect_chain_ordering": effect_chain_ordering(fast_match.get("events", [])) == effect_chain_ordering(reducer_match.get("events", [])),
        }
        ok = all(checks.values())
        report = {
            "ok": ok,
            "checks": checks,
            "fast_canonical_state_hash": canonical_state_hash(fast_match),
            "reducer_canonical_state_hash": canonical_state_hash(reducer_match),
            "fast_reducer_state_hash": fast_reducer_trace["hash"],
            "reducer_reducer_state_hash": reducer_reducer_trace["hash"],
            "command_count": len(envelope.get("commands") or []),
            "event_count": len(fast_match.get("events", []) or []),
            "replay_frame_count": len(reducer_match.get("events", []) or []),
            "game_seed": envelope.get("game_seed"),
            "replay_metadata": {
                "format_version": envelope.get("format_version"),
                "replay_schema_version": envelope.get("replay_schema_version"),
                "engine_version": envelope.get("engine_version"),
                "card_set_version": envelope.get("card_set_version"),
                "ruleset_version": envelope.get("ruleset_version"),
                "reducer_version": envelope.get("reducer_version"),
            },
        }
        if not ok and self.strict:
            dump = parity_failure_dump(
                fast_match,
                reducer_match,
                checks,
                envelope=envelope,
                fast_reducer_trace=fast_reducer_trace,
                reducer_reducer_trace=reducer_reducer_trace,
            )
            raise ParityViolationError("Fast runtime diverged from reducer runtime.", dump)
        if not ok:
            report["failure_dump"] = parity_failure_dump(
                fast_match,
                reducer_match,
                checks,
                envelope=envelope,
                fast_reducer_trace=fast_reducer_trace,
                reducer_reducer_trace=reducer_reducer_trace,
            )
        return report

    def verify_many(self, matches: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.verify(match) for match in matches]

import hashlib
import json

from services.rebirth_domain import (
    CARD_SET_VERSION,
    ENGINE_VERSION,
    MAX_CAUSAL_CHAIN_DEPTH,
    REDUCER_VERSION,
    RULESET_VERSION,
    canonical_json,
    SNAPSHOT_FORMAT_VERSION,
    REPLAY_SCHEMA_VERSION,
    compress_canonical_state,  # noqa: F401 — re-exportado via monkeypatch nos testes v65
    compress_serialized_state,
    canonical_state_hash,
    serialize_canonical_state,
)
from services.rebirth_profiler import current_profiler


def _safe_payload(payload=None):
    if payload is None:
        return {}
    return json.loads(canonical_json(payload))


def _next_version(match):
    match["version"] = int(match.get("version", 0) or 0) + 1
    return match["version"]


def ensure_event_contract(match):
    match.setdefault("version", 0)
    match.setdefault("commands", [])
    match.setdefault("events", [])
    match.setdefault("snapshots", [])
    match.setdefault("checkpoints", [])
    match.setdefault("_effect_chain_counter", 0)
    return match


SNAPSHOT_LIFECYCLE_REASONS = {"match_started", "TURN_ENDED", "MATCH_FINISHED", "MATCH_EXHAUSTED"}
SNAPSHOT_EXPLICIT_REASONS = {"debug", "debug_sync", "network_sync", "sync", "audit"}


def should_persist_snapshot(match, reason, *, force=False):
    if force or match.pop("_force_snapshot", False):
        return True
    reason = str(reason)
    if reason in SNAPSHOT_LIFECYCLE_REASONS or reason.startswith("debug_") or reason.startswith("sync_"):
        return True
    if reason in SNAPSHOT_EXPLICIT_REASONS:
        return True
    command_count = len(match.get("commands", []) or [])
    if command_count and command_count % 15 == 0:
        last_checkpoint = int(match.get("_last_snapshot_command_count", 0) or 0)
        if last_checkpoint != command_count:
            match["_last_snapshot_command_count"] = command_count
            return True
    return False


def _event_by_id(match, event_id):
    if event_id is None:
        return None
    wanted = int(event_id)
    for event in match.get("events", []):
        if int(event.get("event_id", event.get("id", 0)) or 0) == wanted:
            return event
    return None


def _causal_depth(match, parent_event_id):
    depth = 0
    seen = set()
    current = _event_by_id(match, parent_event_id)
    while current:
        event_id = int(current.get("event_id", current.get("id", 0)) or 0)
        if event_id in seen:
            from services.rebirth_contracts import RebirthError

            raise RebirthError("Ciclo detectado na árvore causal de eventos.", "causal_cycle_detected")
        seen.add(event_id)
        depth += 1
        if depth > MAX_CAUSAL_CHAIN_DEPTH:
            from services.rebirth_contracts import RebirthError

            raise RebirthError("Profundidade máxima da cadeia causal excedida.", "causal_chain_depth_exceeded")
        current = _event_by_id(match, current.get("parent_event_id"))
    return depth


def new_effect_chain_id(match, prefix="effect"):
    ensure_event_contract(match)
    match["_effect_chain_counter"] = int(match.get("_effect_chain_counter", 0) or 0) + 1
    return f"{prefix}-{int(match['_effect_chain_counter']):06d}"


def append_command(match, command_type, *, actor="player", payload=None):
    ensure_event_contract(match)
    version = _next_version(match)
    command = {
        "id": len(match["commands"]) + 1,
        "version": version,
        "engine_version": match.get("engine_version") or ENGINE_VERSION,
        "card_set_version": match.get("card_set_version") or CARD_SET_VERSION,
        "correlation_id": f"{match.get('match_id', 'match')}:{version}",
        "turn": int(match.get("turn", 0) or 0),
        "type": str(command_type),
        "actor": str(actor),
        "payload": _safe_payload(payload),
    }
    match["commands"].append(command)
    return command


def append_event(
    match,
    event_type,
    *,
    actor="system",
    payload=None,
    message=None,
    source_card_id=None,
    target_id=None,
    owner_id=None,
    effect_chain_id=None,
    replay_frame=None,
    sequence_id=None,
    parent_event_id=None,
    root_event_id=None,
    resolution_phase=None,
    priority_level=None,
):
    ensure_event_contract(match)
    version = _next_version(match)
    payload = _safe_payload(payload)
    chain_id = effect_chain_id or match.get("current_effect_chain_id") or f"event-{version:06d}"
    sequence = int(sequence_id or version)
    event_id = len(match["events"]) + 1
    parent = parent_event_id if parent_event_id is not None else match.get("current_parent_event_id")
    if parent is not None:
        _causal_depth(match, parent)
    parent_event = _event_by_id(match, parent)
    root = root_event_id or (parent_event or {}).get("root_event_id") or parent or event_id
    if int(root or event_id) == event_id and parent is not None:
        from services.rebirth_contracts import RebirthError

        raise RebirthError("Evento derivado não pode apontar para si mesmo como raiz causal.", "causal_cycle_detected")
    event = {
        "id": event_id,
        "event_id": event_id,
        "version": version,
        "engine_version": match.get("engine_version") or ENGINE_VERSION,
        "card_set_version": match.get("card_set_version") or CARD_SET_VERSION,
        "correlation_id": f"{match.get('match_id', 'match')}:{version}",
        "turn": int(match.get("turn", 0) or 0),
        "turn_number": int(match.get("turn", 0) or 0),
        "type": str(event_type),
        "event_type": str(event_type),
        "actor": str(actor),
        "payload": payload,
        "source_card_id": source_card_id,
        "target_id": target_id,
        "owner_id": owner_id if owner_id is not None else str(actor),
        "sequence_id": sequence,
        "effect_chain_id": chain_id,
        "replay_frame": int(replay_frame or sequence),
        "canonical_state_hash": None,
        "parent_event_id": parent,
        "root_event_id": root,
        "reducer_version": match.get("reducer_version") or REDUCER_VERSION,
        "ruleset_version": match.get("ruleset_version") or RULESET_VERSION,
    }
    if resolution_phase:
        event["resolution_phase"] = str(resolution_phase)
    if priority_level is not None:
        event["priority_level"] = int(priority_level)
    if message:
        event["message"] = str(message)
    match["events"].append(event)
    return event


def validate_event_ordering(events):
    sequence = [int(event.get("sequence_id", event.get("version", 0)) or 0) for event in events or []]
    return sequence == sorted(sequence)


def state_hash(match):
    publicish = {
        "match_id": match.get("match_id"),
        "version": match.get("version"),
        "turn": match.get("turn"),
        "phase": match.get("phase"),
        "winner": match.get("winner"),
        "is_finished": bool(match.get("is_finished")),
        "player": {
            "hp": (match.get("player") or {}).get("hp"),
            "deck_count": len((match.get("player") or {}).get("deck", [])),
            "hand_ids": [card.get("id") for card in (match.get("player") or {}).get("hand", [])],
            "discard_count": len((match.get("player") or {}).get("discard", [])),
            "played": ((match.get("player") or {}).get("played_card") or {}).get("id"),
        },
        "bot": {
            "hp": (match.get("bot") or {}).get("hp"),
            "deck_count": len((match.get("bot") or {}).get("deck", [])),
            "hand_count": len((match.get("bot") or {}).get("hand", [])),
            "discard_count": len((match.get("bot") or {}).get("discard", [])),
            "played": ((match.get("bot") or {}).get("played_card") or {}).get("id"),
        },
        "last_event": (match.get("events") or [{}])[-1].get("type"),
    }
    encoded = json.dumps(publicish, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _snapshot_payload(match, reason):
    encoded = serialize_canonical_state(match)
    canonical_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    snapshot = {
        "format_version": SNAPSHOT_FORMAT_VERSION,
        "replay_schema_version": REPLAY_SCHEMA_VERSION,
        "ruleset_version": match.get("ruleset_version") or RULESET_VERSION,
        "reducer_version": match.get("reducer_version") or REDUCER_VERSION,
        "version": int(match.get("version", 0) or 0),
        "turn": int(match.get("turn", 0) or 0),
        "phase": match.get("phase"),
        "reason": str(reason),
        "state_hash": state_hash(match),
        "canonical_state_hash": canonical_hash,
        "state_encoding": "gzip+base64+json",
        "canonical_state": compress_serialized_state(encoded),
    }
    match["_last_canonical_state_hash"] = canonical_hash
    match["_canonical_hash_dirty"] = False
    return snapshot


def append_checkpoint(match, reason, *, canonical_hash=None):
    """Store a compact turn boundary for future peer/spectator validation."""
    ensure_event_contract(match)
    events = match.get("events") or []
    last_event = events[-1] if events else {}
    checkpoint = {
        "turn": int(match.get("turn", 0) or 0),
        "version": int(match.get("version", 0) or 0),
        "reason": str(reason),
        "command_count": len(match.get("commands") or []),
        "replay_frame": int(last_event.get("replay_frame", last_event.get("sequence_id", 0)) or 0),
        "canonical_state_hash": canonical_hash or canonical_state_hash(match),
    }
    existing = match["checkpoints"][-1] if match["checkpoints"] else None
    signature = (checkpoint["reason"], checkpoint["turn"], checkpoint["replay_frame"])
    if existing and signature == (existing.get("reason"), existing.get("turn"), existing.get("replay_frame")):
        return existing
    match["checkpoints"].append(checkpoint)
    match["checkpoints"] = match["checkpoints"][-128:]
    return checkpoint


def append_snapshot(match, reason, *, force=False):
    ensure_event_contract(match)
    if not should_persist_snapshot(match, reason, force=force):
        return None
    profiler = current_profiler()
    if profiler:
        with profiler.timer("snapshot_cost", detail=str(reason)):
            snapshot = _snapshot_payload(match, reason)
        profiler.observe_snapshot_size(len(str(snapshot.get("canonical_state") or "")), reason=str(reason))
    else:
        snapshot = _snapshot_payload(match, reason)
    match["snapshots"].append(snapshot)
    match["snapshots"] = match["snapshots"][-20:]
    if str(reason) in SNAPSHOT_LIFECYCLE_REASONS:
        append_checkpoint(match, reason, canonical_hash=snapshot["canonical_state_hash"])
    return snapshot

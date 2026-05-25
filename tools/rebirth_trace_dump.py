#!/usr/bin/env python3
"""Show reducer state diffs event-by-event for a Rebirth JSON trace."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.rebirth_domain import canonical_json, canonical_state_hash
from services.rebirth_reducers import reduce_event


def _load(path):
    raw = sys.stdin.read() if path == "-" else open(path, "r", encoding="utf-8").read()
    return json.loads(raw)


def _changed(before, after, prefix=""):
    keys = sorted(set(before if isinstance(before, dict) else {}) | set(after if isinstance(after, dict) else {}))
    for key in keys:
        left = before.get(key) if isinstance(before, dict) else None
        right = after.get(key) if isinstance(after, dict) else None
        name = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(left, dict) and isinstance(right, dict):
            yield from _changed(left, right, name)
        elif left != right:
            yield name


def dump(payload):
    state = payload.get("base_state") or payload.get("initial_state") or {}
    events = sorted(payload.get("events") or [], key=lambda event: int(event.get("sequence_id", event.get("version", 0)) or 0))
    for event in events:
        before = state
        after = reduce_event(before, event)
        print(
            f"{event.get('sequence_id')} {event.get('event_type', event.get('type'))} "
            f"chain={event.get('effect_chain_id')} frame={event.get('replay_frame')} "
            f"phase={event.get('resolution_phase', '-')} priority={event.get('priority_level', '-')}"
        )
        print(f"  before={canonical_state_hash(before) if before else 'empty'}")
        print(f"  after={canonical_state_hash(after) if after else 'empty'}")
        changes = list(_changed(before, after))
        print(f"  changed={canonical_json(changes)}")
        state = after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="-", help="Trace JSON path, or '-' for stdin.")
    args = parser.parse_args()
    dump(_load(args.path))


if __name__ == "__main__":
    main()

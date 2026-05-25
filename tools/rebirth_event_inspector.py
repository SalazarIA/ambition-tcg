#!/usr/bin/env python3
"""Print a deterministic causal tree for a Rebirth replay or match JSON."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict


def _load(path):
    raw = sys.stdin.read() if path == "-" else open(path, "r", encoding="utf-8").read()
    return json.loads(raw)


def _events(payload):
    return sorted(payload.get("events") or [], key=lambda event: int(event.get("sequence_id", event.get("version", 0)) or 0))


def _label(event):
    return (
        f"{event.get('event_type', event.get('type'))}"
        f" seq={event.get('sequence_id')} frame={event.get('replay_frame')}"
        f" phase={event.get('resolution_phase', '-')}"
        f" priority={event.get('priority_level', '-')}"
        f" chain={event.get('effect_chain_id')} reducer={event.get('reducer_version')}"
        f" hash={str(event.get('canonical_state_hash') or '')[:12]}"
    )


def print_tree(payload):
    events = _events(payload)
    by_parent = defaultdict(list)
    by_id = {}
    for event in events:
        event_id = int(event.get("event_id", event.get("id", 0)) or 0)
        by_id[event_id] = event
        by_parent[event.get("parent_event_id")].append(event)

    def walk(event, prefix=""):
        event_id = int(event.get("event_id", event.get("id", 0)) or 0)
        print(f"{prefix}{_label(event)}")
        children = sorted(by_parent.get(event_id, []), key=lambda item: int(item.get("sequence_id", item.get("version", 0)) or 0))
        for index, child in enumerate(children):
            branch = "`-- " if index == len(children) - 1 else "|-- "
            walk(child, prefix + branch)

    roots = [event for event in events if not event.get("parent_event_id") or event.get("parent_event_id") not in by_id]
    for root in roots:
        walk(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="-", help="Replay/match JSON path, or '-' for stdin.")
    args = parser.parse_args()
    print_tree(_load(args.path))


if __name__ == "__main__":
    main()

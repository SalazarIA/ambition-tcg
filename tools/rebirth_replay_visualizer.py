#!/usr/bin/env python3
"""Render a deterministic event timeline for a Rebirth replay or match JSON."""

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


def _short(value, length=12):
    return str(value or "")[:length]


def _event_id(event):
    return int(event.get("event_id", event.get("id", 0)) or 0)


def print_timeline(payload):
    print("Replay Timeline")
    print("seq frame phase priority event parent root chain hash")
    for event in _events(payload):
        print(
            f"{event.get('sequence_id')} "
            f"{event.get('replay_frame')} "
            f"{event.get('resolution_phase', '-'):<16} "
            f"{event.get('priority_level', '-')!s:<8} "
            f"{event.get('event_type', event.get('type')):<24} "
            f"{event.get('parent_event_id') or '-'} "
            f"{event.get('root_event_id') or '-'} "
            f"{event.get('effect_chain_id') or '-'} "
            f"{_short(event.get('canonical_state_hash'))}"
        )


def print_tree(payload):
    events = _events(payload)
    by_parent = defaultdict(list)
    by_id = {}
    for event in events:
        by_id[_event_id(event)] = event
        by_parent[event.get("parent_event_id")].append(event)

    def label(event):
        marker = ""
        priority = int(event.get("priority_level", 99) or 99)
        if priority == 1:
            marker = " [replacement]"
        elif priority == 2:
            marker = " [interrupt]"
        return (
            f"{event.get('event_type', event.get('type'))}{marker} "
            f"seq={event.get('sequence_id')} phase={event.get('resolution_phase', '-')} "
            f"chain={event.get('effect_chain_id')} hash={_short(event.get('canonical_state_hash'))}"
        )

    def walk(event, prefix=""):
        print(f"{prefix}{label(event)}")
        children = sorted(by_parent.get(_event_id(event), []), key=lambda item: int(item.get("sequence_id", item.get("version", 0)) or 0))
        for index, child in enumerate(children):
            branch = "`-- " if index == len(children) - 1 else "|-- "
            walk(child, prefix + branch)

    roots = [event for event in events if not event.get("parent_event_id") or event.get("parent_event_id") not in by_id]
    print("\nCausal Tree")
    for root in roots:
        walk(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="-", help="Replay/match JSON path, or '-' for stdin.")
    parser.add_argument("--tree-only", action="store_true", help="Print only the causal tree.")
    args = parser.parse_args()
    payload = _load(args.path)
    if not args.tree_only:
        print_timeline(payload)
    print_tree(payload)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Render a deterministic event timeline for a Rebirth replay or match JSON."""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rebirth_domain import decompress_snapshot_state


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


def _flatten(value, path="$"):
    if isinstance(value, dict):
        rows = {}
        for key, item in value.items():
            rows.update(_flatten(item, f"{path}.{key}"))
        return rows
    if isinstance(value, list):
        rows = {}
        for index, item in enumerate(value):
            rows.update(_flatten(item, f"{path}[{index}]"))
        return rows
    return {path: value}


def _snapshot_diffs(payload):
    snapshots = payload.get("snapshots") or []
    decoded = []
    for snapshot in snapshots:
        encoded = snapshot.get("canonical_state")
        if encoded:
            decoded.append((snapshot, _flatten(decompress_snapshot_state(encoded))))
    changes = []
    for (previous, left), (current, right) in zip(decoded, decoded[1:]):
        keys = sorted(set(left) | set(right))
        changed = [key for key in keys if left.get(key) != right.get(key)]
        changes.append(
            {
                "from": previous.get("reason"),
                "to": current.get("reason"),
                "paths": changed[:18],
                "count": len(changed),
            }
        )
    return changes


def render_html(payload, output_path):
    events = _events(payload)
    chain_groups = defaultdict(list)
    for event in events:
        chain_groups[event.get("effect_chain_id") or "sem-cadeia"].append(event)
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(event.get('replay_frame', '-')))}</td>"
        f"<td>{html.escape(str(event.get('turn_number', event.get('turn', '-'))))}</td>"
        f"<td>{html.escape(str(event.get('resolution_phase', '-')))}</td>"
        f"<td>{html.escape(str(event.get('priority_level', '-')))}</td>"
        f"<td>{html.escape(str(event.get('event_type', event.get('type', '-'))))}</td>"
        f"<td>{html.escape(str(event.get('effect_chain_id', '-')))}</td>"
        "</tr>"
        for event in events
    )
    chains = "".join(
        f"<article><strong>{html.escape(str(chain))}</strong>"
        f"<small>{len(items)} frames</small>"
        + "".join(
            f"<span class=\"{'interrupt' if int(item.get('priority_level', 0) or 0) == 2 else ''}\">"
            f"{html.escape(str(item.get('event_type', item.get('type'))))}</span>"
            for item in items
        )
        + "</article>"
        for chain, items in sorted(chain_groups.items())
    )
    diffs = "".join(
        f"<article><strong>{html.escape(str(diff['from']))} -> {html.escape(str(diff['to']))}</strong>"
        f"<small>{diff['count']} campos alterados</small>"
        + "".join(f"<code>{html.escape(path)}</code>" for path in diff["paths"])
        + "</article>"
        for diff in _snapshot_diffs(payload)
    ) or "<p>Sem snapshots consecutivos para comparar.</p>"
    content = f"""<!doctype html>
<meta charset="utf-8">
<title>Rebirth Debug Timeline</title>
<style>
* {{ box-sizing:border-box }} body {{ margin:0;background:#07090c;color:#f4f3ef;font:14px system-ui,sans-serif }}
header {{ padding:22px 28px;border-bottom:1px solid #28303a;display:flex;gap:18px;align-items:baseline }}
h1 {{ margin:0;font-size:22px }} small {{ color:#9fa8b3 }} main {{ display:grid;grid-template-columns:1.3fr .9fr;gap:18px;padding:18px }}
section {{ min-width:0;border:1px solid #27303a;background:#0d1116;padding:14px }} h2 {{ margin:0 0 12px;font-size:14px;color:#f4ad26;text-transform:uppercase }}
table {{ width:100%;border-collapse:collapse;font-size:12px }} th,td {{ padding:7px;border-bottom:1px solid #202832;text-align:left }}
th {{ color:#58d6ff }} .stack {{ display:grid;gap:8px }} article {{ display:grid;gap:5px;padding:9px;border:1px solid #202832 }}
span,code {{ display:inline-block;margin:2px;padding:3px 6px;background:#151b22;color:#b9c6d2;font-size:11px }}
.interrupt {{ color:#ff735f;border:1px solid #713128 }} .diffs {{ grid-column:1/-1 }}
</style>
<header><h1>Replay Timeline</h1><small>{len(events)} frames / debug-only / hash {html.escape(_short(payload.get('canonical_state_hash') or payload.get('expected_canonical_state_hash')))}</small></header>
<main>
<section><h2>Phase Timeline</h2><table><thead><tr><th>Frame</th><th>Turno</th><th>Fase</th><th>Prio</th><th>Evento</th><th>Cadeia</th></tr></thead><tbody>{rows}</tbody></table></section>
<section><h2>Event Chain / Interrupts</h2><div class="stack">{chains}</div></section>
<section class="diffs"><h2>Reducer Diff Viewer (checkpoints)</h2><div class="stack">{diffs}</div></section>
</main>"""
    Path(output_path).write_text(content, encoding="utf-8")
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="-", help="Replay/match JSON path, or '-' for stdin.")
    parser.add_argument("--tree-only", action="store_true", help="Print only the causal tree.")
    parser.add_argument("--html", dest="html_path", help="Write an isolated visual debug timeline HTML file.")
    args = parser.parse_args()
    payload = _load(args.path)
    if args.html_path:
        render_html(payload, args.html_path)
        print(f"Visual timeline written to {args.html_path}")
        return
    if not args.tree_only:
        print_timeline(payload)
    print_tree(payload)


if __name__ == "__main__":
    main()

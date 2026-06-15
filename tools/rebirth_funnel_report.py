#!/usr/bin/env python3
"""CLI: first-session funnel + D1/D7 retention from a telemetry events export.

Usage:
    python tools/rebirth_funnel_report.py events.json [--out report.json]

`events.json` is a JSON array of telemetry event records (see
services/rebirth_funnel for the expected shape). This keeps the analysis
decoupled from the persistence read path — point it at whatever export the ops
pipeline produces.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.rebirth_funnel import build_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebirth funnel + retention report")
    parser.add_argument("events", help="Path to a JSON array of telemetry events")
    parser.add_argument("--out", help="Write the report JSON here instead of stdout")
    args = parser.parse_args()

    events = json.loads(Path(args.events).read_text(encoding="utf-8"))
    if not isinstance(events, list):
        print("error: events file must be a JSON array", file=sys.stderr)
        return 1

    report = build_report(events)
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

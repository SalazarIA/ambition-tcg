#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.rebirth_balance import simulate_controlled_balance
from tools.rebirth_balance_report import render_report, write_csv_bundle, write_dashboard


def main():
    parser = argparse.ArgumentParser(
        description="Run a large deterministic Ambitionz Rebirth PvE balance batch."
    )
    parser.add_argument("--matches", type=int, default=1000)
    parser.add_argument("--seed-prefix", default="controlled-balance")
    parser.add_argument("--max-turns", type=int, default=30)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--csv-dir", type=Path)
    parser.add_argument("--dashboard", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    payload = simulate_controlled_balance(
        matches=args.matches,
        seed_prefix=args.seed_prefix,
        max_turns=args.max_turns,
    )
    report = render_report(payload)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    if args.csv_dir:
        write_csv_bundle(payload, args.csv_dir)
    if args.dashboard:
        write_dashboard(payload, args.dashboard)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(report)


if __name__ == "__main__":
    main()

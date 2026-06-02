#!/usr/bin/env python3
"""Validate Rebirth card content and art coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rebirth_content_pipeline import content_pipeline_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Rebirth content pipeline.")
    parser.add_argument("--report-only", action="store_true", help="Print JSON without failing on content errors.")
    args = parser.parse_args()
    report = content_pipeline_report()
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    if not args.report_only and not report["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

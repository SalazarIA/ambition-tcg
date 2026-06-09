#!/usr/bin/env python3
"""Report Public Beta KPI gates from Rebirth telemetry."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rebirth_persistence import RebirthRepository  # noqa: E402
from services.rebirth_public_beta_gate import public_beta_gate_payload  # noqa: E402


def _open_repo() -> RebirthRepository:
    database_url = os.environ.get("REBIRTH_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if database_url:
        return RebirthRepository(database_url=database_url)
    db_path = os.environ.get("REBIRTH_DB_PATH") or str(ROOT / "instance" / "database.db")
    return RebirthRepository(db_path=db_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Ambitionz Rebirth Public Beta KPI gates.")
    parser.add_argument("--limit", type=int, default=5000, help="Maximum telemetry events to read.")
    parser.add_argument("--release-version", default=os.environ.get("REBIRTH_RELEASE_VERSION"), help="Release label for the report.")
    parser.add_argument("--require-ready", action="store_true", help="Exit non-zero when the gate is not ready.")
    args = parser.parse_args()

    report = public_beta_gate_payload(
        _open_repo(),
        limit=args.limit,
        release_version=args.release_version,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    return 1 if args.require_ready and not report["ready"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

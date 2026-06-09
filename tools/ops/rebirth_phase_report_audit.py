#!/usr/bin/env python3
"""Audit Rebirth phase reports against the execution-plan deliverable."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rebirth_phase_reports import audit_phase_reports  # noqa: E402


def main() -> int:
    payload = audit_phase_reports()
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build secret-free Rebirth legal-review evidence.

This tool does not approve anything by itself. It only formats the operator or
counsel review record into the evidence shape required by the external gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rebirth_gate_evidence import LEGAL_SCOPE, validate_external_gate_evidence  # noqa: E402


SCOPE_FLAGS = {
    "terms": "terms_reviewed",
    "privacy": "privacy_reviewed",
    "data_deletion": "data_deletion_reviewed",
    "billing_disabled": "billing_disabled_reviewed",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_evidence_payload(
    *,
    approved: bool,
    reviewer: str,
    evidence_ref: str,
    scope: list[str],
    approved_at: str | None = None,
) -> dict:
    return {
        "legal_review": {
            "approved": bool(approved),
            "reviewer": reviewer,
            "approved_at": approved_at or utc_now(),
            "scope": sorted(set(scope)),
            "evidence_ref": evidence_ref,
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Rebirth legal-review evidence block.")
    parser.add_argument("--approved", action="store_true", help="Set only after the review is actually approved.")
    parser.add_argument("--reviewer", default="", help="Responsible operator/counsel name or role.")
    parser.add_argument("--evidence-ref", default="", help="Private ticket, signed note or operator-log reference.")
    parser.add_argument("--approved-at", default="", help="ISO timestamp for the approval. Defaults to now.")
    parser.add_argument("--all-required-scopes-reviewed", action="store_true", help="Confirm all required legal scopes.")
    parser.add_argument("--terms-reviewed", action="store_true")
    parser.add_argument("--privacy-reviewed", action="store_true")
    parser.add_argument("--data-deletion-reviewed", action="store_true")
    parser.add_argument("--billing-disabled-reviewed", action="store_true")
    args = parser.parse_args()

    scope = sorted(LEGAL_SCOPE) if args.all_required_scopes_reviewed else [
        scope_key
        for scope_key, flag_name in SCOPE_FLAGS.items()
        if getattr(args, flag_name)
    ]
    evidence = build_evidence_payload(
        approved=args.approved,
        reviewer=args.reviewer.strip(),
        evidence_ref=args.evidence_ref.strip(),
        scope=scope,
        approved_at=args.approved_at.strip() or None,
    )
    validation = validate_external_gate_evidence(evidence)["legal_review"]
    payload = {
        "ok": validation["valid"],
        "evidence": evidence,
        "validation": validation,
        "notes": [
            "This output is valid only when it references a real private legal/operator approval record.",
            "Merge this legal_review block into the private external evidence JSON; do not commit that filled file.",
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if validation["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

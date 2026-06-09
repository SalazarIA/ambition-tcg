#!/usr/bin/env python3
"""Evaluate the full Rebirth public beta readiness gate."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rebirth_beta_ops import external_gate_payload  # noqa: E402
from services.rebirth_persistence import RebirthRepository  # noqa: E402
from services.rebirth_phase_reports import audit_phase_reports  # noqa: E402
from services.rebirth_public_beta_gate import public_beta_gate_payload  # noqa: E402
from services.rebirth_release_readiness import release_readiness_report  # noqa: E402
from tools.ops.rebirth_pre_external_gate import _config_from_env, _load_evidence, _workflow_status  # noqa: E402


def _open_repo() -> RebirthRepository:
    database_url = os.environ.get("REBIRTH_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if database_url:
        return RebirthRepository(database_url=database_url)
    db_path = os.environ.get("REBIRTH_DB_PATH") or str(ROOT / "instance" / "database.db")
    return RebirthRepository(db_path=db_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the complete Ambitionz Rebirth public beta gate.")
    parser.add_argument("--report-only", action="store_true", help="Print JSON but do not fail on blocked gates.")
    parser.add_argument("--limit", type=int, default=5000, help="Maximum telemetry events to read.")
    parser.add_argument("--since", default=None, help="ISO timestamp lower bound for the public beta cohort/event window.")
    parser.add_argument("--release-version", default=os.environ.get("REBIRTH_RELEASE_VERSION"), help="Release label for the report.")
    parser.add_argument(
        "--evidence",
        default=os.environ.get("REBIRTH_EXTERNAL_EVIDENCE_PATH"),
        help="Path to a secret-free external gate evidence JSON file.",
    )
    parser.add_argument(
        "--workflow-branch",
        default=os.environ.get("REBIRTH_GITHUB_QA_BRANCH"),
        help="Git branch used to find the Rebirth closed-beta QA workflow run. Defaults to the current branch.",
    )
    parser.add_argument(
        "--workflow-head-sha",
        default=os.environ.get("REBIRTH_GITHUB_QA_HEAD_SHA"),
        help="Commit SHA that must have a green Rebirth closed-beta QA workflow run. Defaults to HEAD.",
    )
    args = parser.parse_args()

    workflow = _workflow_status(branch=args.workflow_branch, head_sha=args.workflow_head_sha)
    evidence, evidence_file = _load_evidence(args.evidence)
    external_gates = external_gate_payload(
        _config_from_env(),
        workflow=workflow,
        evidence=evidence,
        require_external_evidence=True,
    )
    public_beta_gate = public_beta_gate_payload(
        _open_repo(),
        limit=args.limit,
        since=args.since,
        release_version=args.release_version,
    )
    phase_report_audit = audit_phase_reports()
    readiness = release_readiness_report(
        external_gates,
        public_beta_gate,
        phase_report_audit=phase_report_audit,
    )
    payload = {
        "ok": readiness["ready"],
        "workflow": workflow,
        "evidence_file": evidence_file,
        "external_gates": external_gates,
        "public_beta_gate": public_beta_gate,
        "phase_report_audit": phase_report_audit,
        "readiness": readiness,
        "notes": [
            "This command is the final Phase 8 gate: external proof, phase reports and human/product KPIs must all pass.",
            "It never treats local flags as a replacement for real legal, restore, error-tracking or human telemetry evidence.",
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str))
    if not args.report_only and not readiness["ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

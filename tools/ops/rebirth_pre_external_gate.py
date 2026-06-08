#!/usr/bin/env python3
"""Pre-external-tester gate for Ambitionz Rebirth.

This script intentionally fails when human/external checks are not proven.
Use --report-only for release dashboards or local audits that should not fail
the shell.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rebirth_beta_ops import external_gate_payload, truthy


WORKFLOW_NAME = "rebirth-closed-beta-qa.yml"


def _workflow_status():
    workflow_path = ROOT / ".github" / "workflows" / WORKFLOW_NAME
    status = {
        "workflow": WORKFLOW_NAME,
        "exists": workflow_path.exists(),
        "status": None,
        "conclusion": None,
        "headSha": None,
        "source": "local_file",
    }
    gh = shutil.which("gh")
    if not gh:
        status["error"] = "gh_cli_missing"
        return status
    try:
        result = subprocess.run(
            [
                gh,
                "run",
                "list",
                "--workflow",
                WORKFLOW_NAME,
                "--limit",
                "1",
                "--json",
                "status,conclusion,headSha",
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
            timeout=20,
        )
        runs = json.loads(result.stdout or "[]")
        if runs:
            status.update(runs[0])
            status["source"] = "github"
    except Exception as exc:
        status["error"] = f"gh_query_failed:{type(exc).__name__}"
    return status


def _config_from_env():
    return {
        "REBIRTH_ENABLE_BILLING": truthy(os.environ.get("REBIRTH_ENABLE_BILLING")),
        "REBIRTH_ALLOW_STRIPE_LIVE": truthy(os.environ.get("REBIRTH_ALLOW_STRIPE_LIVE")),
        "REBIRTH_LEGAL_REVIEWED": truthy(os.environ.get("REBIRTH_LEGAL_REVIEWED")),
        "REBIRTH_BACKUP_RESTORE_DRILL": truthy(os.environ.get("REBIRTH_BACKUP_RESTORE_DRILL")),
        "REBIRTH_GITHUB_QA_GREEN": truthy(os.environ.get("REBIRTH_GITHUB_QA_GREEN")),
        "SENTRY_DSN": os.environ.get("SENTRY_DSN"),
    }


def _load_evidence(path):
    if not path:
        return None, {"path": None, "loaded": False}
    evidence_path = Path(path)
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, {"path": str(evidence_path), "loaded": False, "error": f"{type(exc).__name__}:{exc}"}
    return evidence, {"path": str(evidence_path), "loaded": True}


def main():
    parser = argparse.ArgumentParser(description="Check Rebirth external tester readiness gates.")
    parser.add_argument("--report-only", action="store_true", help="Print JSON but do not fail on blocked gates.")
    parser.add_argument(
        "--evidence",
        default=os.environ.get("REBIRTH_EXTERNAL_EVIDENCE_PATH"),
        help="Path to a secret-free JSON evidence file for legal, backup/restore and error-tracking gates.",
    )
    args = parser.parse_args()

    workflow = _workflow_status()
    evidence, evidence_file = _load_evidence(args.evidence)
    gates = external_gate_payload(_config_from_env(), workflow=workflow, evidence=evidence)
    payload = {
        "ok": gates["ready"],
        "workflow": workflow,
        "evidence_file": evidence_file,
        "gates": gates,
        "notes": [
            "Legal review, Render/Postgres restore drill and error tracking are external proof points.",
            "Use --evidence or REBIRTH_EXTERNAL_EVIDENCE_PATH with a secret-free evidence JSON when available.",
            "Stripe/live payments must stay disabled unless explicit compliance flags are set.",
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    if not args.report_only and not gates["ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

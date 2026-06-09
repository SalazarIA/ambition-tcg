import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.rebirth_beta_ops import external_gate_payload
from services.rebirth_gate_evidence import current_legal_document_hashes, validate_external_gate_evidence
from tools.ops.rebirth_backup_restore_drill import build_evidence_payload as build_backup_evidence_payload
from tools.ops.rebirth_external_evidence_bundle import merge_evidence_blocks
from tools.ops.rebirth_error_tracking_smoke import build_evidence_payload
from tools.ops.rebirth_legal_review_evidence import build_evidence_payload as build_legal_evidence_payload
from tools.ops import rebirth_phase_report_audit, rebirth_pre_external_gate


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _valid_external_evidence():
    now = _now_iso()
    return {
        "legal_review": {
            "approved": True,
            "reviewer": "Operator",
            "approved_at": now,
            "scope": ["terms", "privacy", "data_deletion", "billing_disabled"],
            "document_hashes": current_legal_document_hashes(),
            "evidence_ref": "private-ticket-legal-1",
        },
        "backup_restore": {
            "validated": True,
            "drill_at": now,
            "operator": "Operator",
            "source_commit": "abc123",
            "restore_target": "redacted-restore-db",
            "dump_bytes": 42,
            "schema_check": "passed",
            "health_check": "passed",
            "support_export_check": "passed",
            "evidence_ref": "private-ticket-dr-1",
        },
        "error_tracking": {
            "validated": True,
            "provider": "glitchtip",
            "environment": "closed-beta",
            "test_event_id": "event-123",
            "tested_at": now,
            "evidence_ref": "private-ticket-sentry-1",
        },
    }


def test_error_tracking_smoke_evidence_requires_operator_confirmation():
    candidate = build_evidence_payload(
        provider="glitchtip",
        environment="closed-beta",
        event_id="event-123",
    )
    valid = build_evidence_payload(
        provider="glitchtip",
        environment="closed-beta",
        event_id="event-123",
        confirmed_evidence_ref="private-ticket-123",
        tested_at=_now_iso(),
    )

    assert validate_external_gate_evidence(candidate)["error_tracking"]["valid"] is False
    assert validate_external_gate_evidence(valid)["error_tracking"]["valid"] is True


def test_legal_review_evidence_requires_real_approval_record():
    candidate = build_legal_evidence_payload(
        approved=False,
        reviewer="",
        evidence_ref="",
        scope=["terms"],
        approved_at=_now_iso(),
    )
    valid = build_legal_evidence_payload(
        approved=True,
        reviewer="Operator",
        evidence_ref="private-legal-1",
        scope=["terms", "privacy", "data_deletion", "billing_disabled"],
        approved_at=_now_iso(),
    )

    candidate_report = validate_external_gate_evidence(candidate)["legal_review"]
    valid_report = validate_external_gate_evidence(valid)["legal_review"]

    assert candidate_report["valid"] is False
    assert "approved_required" in candidate_report["errors"]
    assert "reviewer_required" in candidate_report["errors"]
    assert "scope_missing:billing_disabled,data_deletion,privacy" in candidate_report["errors"]
    assert "evidence_ref_required" in candidate_report["errors"]
    assert valid_report["valid"] is True


def test_legal_review_evidence_rejects_stale_document_hashes():
    evidence = build_legal_evidence_payload(
        approved=True,
        reviewer="Operator",
        evidence_ref="private-legal-1",
        scope=["terms", "privacy", "data_deletion", "billing_disabled"],
        approved_at=_now_iso(),
    )
    evidence["legal_review"]["document_hashes"]["terms"] = "0" * 64

    report = validate_external_gate_evidence(evidence)["legal_review"]

    assert report["valid"] is False
    assert "document_hash_mismatch:terms" in report["errors"]


def test_legal_review_evidence_command_builds_valid_scope_block():
    result = subprocess.run(
        [
            sys.executable,
            "tools/ops/rebirth_legal_review_evidence.py",
            "--approved",
            "--reviewer",
            "Operator",
            "--evidence-ref",
            "private-legal-1",
            "--all-required-scopes-reviewed",
        ],
        cwd=os.getcwd(),
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["ok"] is True
    assert payload["validation"]["valid"] is True
    assert sorted(payload["evidence"]["legal_review"]["scope"]) == [
        "billing_disabled",
        "data_deletion",
        "privacy",
        "terms",
    ]
    assert sorted(payload["evidence"]["legal_review"]["document_hashes"]) == [
        "data_deletion",
        "privacy",
        "terms",
    ]


def test_external_evidence_bundle_command_merges_helper_outputs(tmp_path):
    dump = tmp_path / "rebirth.dump"
    dump.write_bytes(b"backup")
    legal = {
        "ok": True,
        "evidence": build_legal_evidence_payload(
            approved=True,
            reviewer="Operator",
            evidence_ref="private-legal-1",
            scope=["terms", "privacy", "data_deletion", "billing_disabled"],
            approved_at=_now_iso(),
        ),
    }
    backup = {
        "ok": True,
        "evidence": build_backup_evidence_payload(
            validated=True,
            operator="Operator",
            source_commit="abc123",
            dump_path=dump,
            restore_target="redacted-restore-db",
            schema_check="passed",
            health_check="passed",
            support_export_check="passed",
            evidence_ref="private-drill-1",
            drill_at=_now_iso(),
        ),
    }
    error = {
        "ok": True,
        "evidence": build_evidence_payload(
            provider="glitchtip",
            environment="closed-beta",
            event_id="event-123",
            confirmed_evidence_ref="private-ticket-123",
            tested_at=_now_iso(),
        ),
    }
    paths = []
    for index, payload in enumerate((legal, backup, error)):
        path = tmp_path / f"evidence-{index}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths.append(path)
    output = tmp_path / "rebirth-external-evidence.json"

    result = subprocess.run(
        [
            sys.executable,
            "tools/ops/rebirth_external_evidence_bundle.py",
            *[str(path) for path in paths],
            "--output",
            str(output),
        ],
        cwd=os.getcwd(),
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result.returncode == 0
    assert payload["ok"] is True
    assert payload["validation"]["legal_review"]["valid"] is True
    assert payload["validation"]["backup_restore"]["valid"] is True
    assert payload["validation"]["error_tracking"]["valid"] is True
    assert sorted(written) == ["backup_restore", "error_tracking", "legal_review"]


def test_external_evidence_bundle_redacts_secret_like_values(tmp_path):
    secret = {
        "backup_restore": {
            "validated": True,
            "drill_at": _now_iso(),
            "operator": "Operator",
            "source_commit": "abc123",
            "restore_target": "postgresql://user:password@example.invalid/db",
            "dump_bytes": 42,
            "schema_check": "passed",
            "health_check": "passed",
            "support_export_check": "passed",
            "evidence_ref": "private-drill-1",
        }
    }
    path = tmp_path / "secret.json"
    output = tmp_path / "should-not-write.json"
    path.write_text(json.dumps(secret), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/ops/rebirth_external_evidence_bundle.py",
            str(path),
            "--output",
            str(output),
            "--report-only",
        ],
        cwd=os.getcwd(),
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["secret_like_value_detected"] is True
    assert payload["evidence_redacted"] is True
    assert payload["output"] is None
    assert not output.exists()
    assert "postgresql://" not in result.stdout
    assert "password" not in result.stdout


def test_external_evidence_bundle_preserves_example_marker():
    report = validate_external_gate_evidence(
        merge_evidence_blocks(
            [
                {
                    "example": True,
                    **_valid_external_evidence(),
                }
            ]
        )
    )

    assert report["legal_review"]["valid"] is False
    assert report["backup_restore"]["valid"] is False
    assert report["error_tracking"]["valid"] is False
    assert "example_evidence_file" in report["legal_review"]["errors"]
    assert "example_evidence_file" in report["backup_restore"]["errors"]
    assert "example_evidence_file" in report["error_tracking"]["errors"]


def test_external_evidence_bundle_rejects_duplicate_blocks():
    legal = build_legal_evidence_payload(
        approved=True,
        reviewer="Operator",
        evidence_ref="private-legal-1",
        scope=["terms", "privacy", "data_deletion", "billing_disabled"],
        approved_at=_now_iso(),
    )

    try:
        merge_evidence_blocks([legal, legal])
    except ValueError as exc:
        assert str(exc) == "duplicate_evidence_key:legal_review"
    else:
        raise AssertionError("duplicate legal evidence block was accepted")


def test_phase_report_audit_covers_all_execution_plan_reports():
    report = rebirth_phase_report_audit.audit_phase_reports()

    assert report["ok"] is True
    assert [phase["phase"] for phase in report["phases"]] == list(range(9))
    assert report["required_sections"] == [
        "coverage",
        "files_changed",
        "implemented",
        "next_steps",
        "project_status",
        "risks",
        "status",
        "tests_executed",
    ]


def test_closed_beta_workflow_runs_release_governance_checks():
    workflow = Path(".github/workflows/rebirth-closed-beta-qa.yml").read_text(encoding="utf-8")

    assert "actions: read" in workflow
    assert "python tools/ops/rebirth_phase_report_audit.py" in workflow
    assert "python tools/ops/rebirth_release_readiness.py" in workflow
    assert "--report-only" in workflow
    assert "REBIRTH_GITHUB_QA_BRANCH: ${{ github.ref_name }}" in workflow
    assert "REBIRTH_GITHUB_QA_HEAD_SHA: ${{ github.sha }}" in workflow


def test_error_tracking_smoke_dry_run_without_dsn_does_not_fail_shell():
    env = dict(os.environ)
    env.pop("SENTRY_DSN", None)
    result = subprocess.run(
        [sys.executable, "tools/ops/rebirth_error_tracking_smoke.py"],
        cwd=os.getcwd(),
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["ok"] is False
    assert payload["sent"] is False
    assert payload["error"] == "SENTRY_DSN_missing"


def test_backup_restore_evidence_requires_health_and_support_checks(tmp_path):
    dump = tmp_path / "rebirth.dump"
    dump.write_bytes(b"backup")

    pending = build_backup_evidence_payload(
        validated=False,
        operator="Operator",
        source_commit="abc123",
        dump_path=dump,
        restore_target="redacted-restore",
        schema_check="passed",
        health_check="pending",
        support_export_check="passed",
        evidence_ref="private-drill-1",
        drill_at=_now_iso(),
    )
    valid = build_backup_evidence_payload(
        validated=True,
        operator="Operator",
        source_commit="abc123",
        dump_path=dump,
        restore_target="redacted-restore",
        schema_check="passed",
        health_check="passed",
        support_export_check="passed",
        evidence_ref="private-drill-1",
        drill_at=_now_iso(),
    )
    unresolved = build_backup_evidence_payload(
        validated=True,
        operator="Operator",
        source_commit="abc123",
        dump_path=dump,
        restore_target="redacted-restore",
        schema_check="passed",
        health_check="passed",
        support_export_check="passed",
        evidence_ref="private-drill-1",
        drill_at=_now_iso(),
        unresolved_issues=["support-export mismatch under investigation"],
    )

    assert validate_external_gate_evidence(pending)["backup_restore"]["valid"] is False
    assert validate_external_gate_evidence(valid)["backup_restore"]["valid"] is True
    unresolved_report = validate_external_gate_evidence(unresolved)
    assert unresolved_report["backup_restore"]["valid"] is False
    assert "unresolved_issues_present" in unresolved_report["backup_restore"]["errors"]


def test_external_evidence_rejects_stale_operational_proof(tmp_path):
    dump = tmp_path / "rebirth.dump"
    dump.write_bytes(b"backup")
    now = datetime(2026, 6, 9, 12, tzinfo=timezone.utc)
    stale_backup = build_backup_evidence_payload(
        validated=True,
        operator="Operator",
        source_commit="abc123",
        dump_path=dump,
        restore_target="redacted-restore",
        schema_check="passed",
        health_check="passed",
        support_export_check="passed",
        evidence_ref="private-drill-1",
        drill_at=(now - timedelta(days=31)).isoformat(),
    )
    stale_error = build_evidence_payload(
        provider="glitchtip",
        environment="closed-beta",
        event_id="event-123",
        confirmed_evidence_ref="private-ticket-123",
        tested_at=(now - timedelta(days=15)).isoformat(),
    )

    evidence = {**stale_backup, **stale_error}
    report = validate_external_gate_evidence(evidence, now=now)

    assert report["backup_restore"]["valid"] is False
    assert "drill_at_stale:>30d" in report["backup_restore"]["errors"]
    assert report["error_tracking"]["valid"] is False
    assert "tested_at_stale:>14d" in report["error_tracking"]["errors"]


def test_backup_restore_drill_dry_run_does_not_print_database_url():
    env = dict(os.environ)
    env["REBIRTH_DATABASE_URL"] = "postgresql://user:password@example.invalid:5432/prod"
    env["REBIRTH_RESTORE_DATABASE_URL"] = "postgresql://user:password@example.invalid:5432/restore"
    result = subprocess.run(
        [sys.executable, "tools/ops/rebirth_backup_restore_drill.py"],
        cwd=os.getcwd(),
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["executed"] is False
    assert "password" not in result.stdout
    assert "postgresql://" not in result.stdout
    assert payload["source"]["database"] == "prod"
    assert payload["restore"]["database"] == "restore"


def test_external_gate_requires_workflow_for_expected_head():
    gates = external_gate_payload(
        {"REBIRTH_GITHUB_QA_GREEN": "true"},
        workflow={
            "conclusion": "success",
            "expectedHeadSha": "abc123",
            "matchedExpectedHead": False,
            "branch": "fix/current",
            "matchedExpectedBranch": True,
        },
    )
    states = {check["key"]: check["state"] for check in gates["checks"]}

    assert states["github_workflow"] == "pending"


def test_external_gate_requires_workflow_for_expected_branch():
    gates = external_gate_payload(
        {"REBIRTH_GITHUB_QA_GREEN": "true"},
        workflow={
            "conclusion": "success",
            "expectedHeadSha": "abc123",
            "matchedExpectedHead": True,
            "branch": "fix/current",
            "matchedExpectedBranch": False,
        },
    )
    states = {check["key"]: check["state"] for check in gates["checks"]}

    assert states["github_workflow"] == "pending"


def test_strict_external_gate_rejects_local_flags_without_evidence():
    gates = external_gate_payload(
        {
            "REBIRTH_LEGAL_REVIEWED": "true",
            "REBIRTH_BACKUP_RESTORE_DRILL": "true",
            "REBIRTH_GITHUB_QA_GREEN": "true",
            "SENTRY_DSN": "https://example.invalid/1",
        },
        workflow={"conclusion": "success"},
        require_external_evidence=True,
    )
    states = {check["key"]: check["state"] for check in gates["checks"]}

    assert gates["ready"] is False
    assert gates["require_external_evidence"] is True
    assert states["legal_review"] == "blocked"
    assert states["backup_restore"] == "blocked"
    assert states["error_tracking"] == "blocked"
    assert states["github_workflow"] == "passed"


def test_strict_external_gate_accepts_valid_evidence():
    gates = external_gate_payload(
        {
            "REBIRTH_ENABLE_BILLING": "false",
            "REBIRTH_ALLOW_STRIPE_LIVE": "false",
        },
        workflow={"conclusion": "success"},
        evidence=_valid_external_evidence(),
        require_external_evidence=True,
    )
    states = {check["key"]: check["state"] for check in gates["checks"]}

    assert gates["ready"] is True
    assert states["legal_review"] == "passed"
    assert states["backup_restore"] == "passed"
    assert states["error_tracking"] == "passed"
    assert states["billing_off"] == "passed"


def test_workflow_status_filters_github_run_by_expected_head(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)

        class Result:
            stdout = json.dumps(
                [
                    {
                        "status": "completed",
                        "conclusion": "success",
                        "headSha": "abc123",
                        "headBranch": "fix/current",
                        "databaseId": 123,
                        "url": "https://example.invalid/run",
                        "createdAt": "2026-06-09T12:00:00Z",
                    }
                ]
            )

        return Result()

    monkeypatch.setattr(rebirth_pre_external_gate.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(rebirth_pre_external_gate.subprocess, "run", fake_run)

    status = rebirth_pre_external_gate._workflow_status(branch="fix/current", head_sha="abc123")

    assert calls
    assert "--branch" in calls[0]
    assert "fix/current" in calls[0]
    assert "--commit" in calls[0]
    assert "abc123" in calls[0]
    assert status["conclusion"] == "success"
    assert status["matchedExpectedHead"] is True
    assert status["matchedExpectedBranch"] is True
    assert status["expectedHeadSha"] == "abc123"

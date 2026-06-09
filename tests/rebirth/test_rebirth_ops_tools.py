import json
import os
import subprocess
import sys

from services.rebirth_beta_ops import external_gate_payload
from services.rebirth_gate_evidence import validate_external_gate_evidence
from tools.ops.rebirth_backup_restore_drill import build_evidence_payload as build_backup_evidence_payload
from tools.ops.rebirth_error_tracking_smoke import build_evidence_payload
from tools.ops import rebirth_pre_external_gate


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
        tested_at="2026-06-08T12:00:00Z",
    )

    assert validate_external_gate_evidence(candidate)["error_tracking"]["valid"] is False
    assert validate_external_gate_evidence(valid)["error_tracking"]["valid"] is True


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
        drill_at="2026-06-08T12:00:00Z",
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
        drill_at="2026-06-08T12:00:00Z",
    )

    assert validate_external_gate_evidence(pending)["backup_restore"]["valid"] is False
    assert validate_external_gate_evidence(valid)["backup_restore"]["valid"] is True


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

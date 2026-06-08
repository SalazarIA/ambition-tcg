import json
import os
import subprocess
import sys

from services.rebirth_gate_evidence import validate_external_gate_evidence
from tools.ops.rebirth_error_tracking_smoke import build_evidence_payload


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

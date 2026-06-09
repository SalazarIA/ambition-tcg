# Rebirth Phase 8 Report - Public Beta Gate

Updated: 2026-06-09

## Status

Phase 8 is not complete.

Current status: **blocked**.

## Gate Checklist

- QA green: passed locally and on GitHub. Current local suite:
  `1295 passed, 5 skipped, 19 deselected`. GitHub
  `rebirth-closed-beta-qa` is green for the pushed branch according to the
  pre-external gate.
- Error tracking active: blocked until `SENTRY_DSN` or compatible GlitchTip DSN
  is configured in the target environment and a smoke event is confirmed in a
  valid evidence record.
- Backup validated: blocked until a real PostgreSQL backup is recorded.
- Restore validated: blocked until a disposable PostgreSQL restore drill passes.
- Legal complete: blocked until owner/counsel approves LGPD, Privacy and Terms.
- Tutorial > 80%: blocked until real-player telemetry exists.
- First Match > 70%: blocked until real-player telemetry exists.
- D1 > 35%: blocked until real cohort data exists.
- D7 > 20%: blocked until real cohort data exists.
- Crash Rate < 1%: blocked until production error tracking is active.
- Telemetry active: local infrastructure is active; production verification
  still required.
- Balance healthy: blocked until 500+ human matches are collected.
- External evidence path: supported through
  `tools/ops/rebirth_pre_external_gate.py --evidence /secure/path/rebirth-external-gates.json`.
- Public beta KPI gate: supported through
  `tools/ops/rebirth_public_beta_gate.py --since <cohort-start-iso> --require-ready`.
- Final readiness gate: supported through
  `tools/ops/rebirth_release_readiness.py --since <cohort-start-iso> --evidence /secure/path/rebirth-external-gates.json`.
  This Phase 8 gate is strict: local flags and DSNs are not accepted as
  substitutes for the secret-free evidence JSON, complete phase reports or
  real human telemetry.

## What Was Implemented

No public beta gate bypass was implemented.
Secret-free evidence validation was added so remaining Phase 0 gates can be
proven by operator records without committing secrets or relying only on manual
boolean flags.
Backup/restore and error-tracking evidence now has freshness checks, preventing
stale operational proof from satisfying the final gate.
Backup/restore evidence with unresolved drill issues is also rejected.
The release dashboard now displays the evidence validity/errors and the
operator command for passing a private evidence file.
An error-tracking smoke command now exists for Sentry/GlitchTip target
environment validation without printing `SENTRY_DSN`.
A backup/restore drill command now exists for redacted dry-runs and guarded
execution against disposable restore databases.
A public beta KPI gate evaluator now exists and is surfaced on `/rebirth/release`
and `/api/rebirth/release`; it blocks unless tutorial, first-match, D1, D7,
crash/error rate, telemetry coverage, human sample and balance checks all pass.
Those release surfaces accept `?since=<cohort-start-iso>` so the dashboard,
live balance and public beta gate can be reviewed against the same beta cohort
window as the CLI gates.
A final readiness evaluator now composes the external evidence gate with the
public beta KPI gate, so Phase 8 has a single `ready=false/true` operator report
without weakening either source gate.
The final readiness evaluator now calls the external gate in strict evidence
mode, so `REBIRTH_LEGAL_REVIEWED`, `REBIRTH_BACKUP_RESTORE_DRILL`,
`REBIRTH_GITHUB_QA_GREEN` and `SENTRY_DSN` cannot make Phase 8 pass without a
matching workflow run and valid legal, restore and error-tracking evidence.
GitHub QA proof is matched to the expected branch/head commit, preventing an
unrelated older workflow run or manual override from satisfying or blocking the
release gate.
The closed-beta QA workflow and PR `tests` workflow now use Node 24-compatible
official GitHub Actions majors, removing the runner deprecation warning from
the release path without changing gameplay.
A phase-report audit command now verifies that every Phase 0-8 report exists
and keeps the mandatory technical sections required by the execution plan.
That audit is now included in the final release readiness report, `/rebirth/release`
and `/api/rebirth/release`, so the public beta gate has one shared view of
external proof, phase reports and product KPIs.
The release dashboard/API now run external gates in strict evidence mode too,
so they cannot appear public-beta ready from local flags or a configured DSN
alone.
The closed-beta QA workflow now runs the Phase 0-8 report audit as a blocking
step and emits a report-only release readiness snapshot for the current
branch/SHA, with GitHub `actions: read` permission for workflow lookup.

## Files Changed

- `services/rebirth_gate_evidence.py`
- `services/rebirth_beta_ops.py`
- `services/rebirth_live_balance.py`
- `services/rebirth_public_beta_gate.py`
- `services/rebirth_release_readiness.py`
- `services/rebirth_phase_reports.py`
- `services/rebirth_product.py`
- `app.py`
- `templates/rebirth_product.html`
- `tools/ops/rebirth_pre_external_gate.py`
- `tools/ops/rebirth_error_tracking_smoke.py`
- `tools/ops/rebirth_backup_restore_drill.py`
- `tools/ops/rebirth_public_beta_gate.py`
- `tools/ops/rebirth_release_readiness.py`
- `tools/ops/rebirth_phase_report_audit.py`
- `docs/REBIRTH_EXTERNAL_GATE_EVIDENCE.example.json`
- `tests/rebirth/test_rebirth_public_beta_gate.py`
- `tests/rebirth/test_rebirth_release_readiness.py`
- `tests/rebirth/test_rebirth_ops_tools.py`
- `tests/rebirth/test_rebirth_product_shell.py`
- `.github/workflows/rebirth-closed-beta-qa.yml`
- `.github/workflows/test.yml`

## Tests Executed

Phase 8-specific public-beta validation now exists through
`tests/rebirth/test_rebirth_public_beta_gate.py` and the release payload
contract. The gate is expected to report `ready=false` until real production
evidence and human telemetry exist.
The final readiness composition is covered by
`tests/rebirth/test_rebirth_release_readiness.py`.
The current local Rebirth suite passed with `1295 passed, 5 skipped,
19 deselected`.
The external pre-gate report was run with `--report-only` and returned
`ok=false`.
The evidence template was also run through `--evidence` and correctly rejected
with `example_evidence_file`.
The GitHub Actions workflow YAML was parsed locally, and old Node 20 action
pins were searched for and removed from `.github`.
The phase-report audit was run and returned `ok=true` for reports Phase 0
through Phase 8.
The final release readiness command was run in report-only mode and returned
`phase_reports_ready=true`, `phase_reports_passed=9/9`, and `ok=false` because
external proof and human KPI gates remain blocked.
The release API contract now asserts `require_external_evidence=true` and keeps
legal, backup/restore, error tracking and GitHub workflow blocked/pending when
only local readiness flags are supplied.
The closed-beta QA workflow contract now asserts that phase-report audit and
release-readiness snapshot commands remain wired into CI.

Current external gate states:

- `legal_review`: blocked.
- `backup_restore`: blocked.
- `error_tracking`: blocked.
- `github_workflow`: passed.
- `billing_off`: passed.
- `public_beta_gate`: blocked by missing human/KPI evidence.

## Coverage

Coverage was not reduced. New governance coverage asserts that the closed-beta
QA workflow keeps phase-report audit and release-readiness snapshot checks wired
to the current branch/head SHA.

## Risks

- Moving to marketing/acquisition/monetization before these gates are green
  would violate the project plan and increase operational risk.
- The project can look locally healthy while still failing public beta due to
  missing production evidence.
- Local readiness flags can no longer close the Phase 8 gate by themselves;
  operators must provide the private evidence JSON and real cohort window.
- Passing phase reports prove governance coverage only; they do not replace
  legal, restore, error-tracking or human telemetry evidence.
- GitHub Actions major updates can change CI behavior; the current workflow
  must stay green on GitHub after each push before using it as release proof.
- The readiness snapshot inside the same workflow is report-only because a run
  cannot prove its own final successful conclusion while it is still executing.
- A synthetic passing gate only proves evaluator behavior. Real public beta
  readiness still requires production events and external evidence records.

## Next Steps

1. Finish Phase 0 external proof gates.
2. Run controlled closed beta.
3. Collect Phase 1, Phase 2 and Phase 5 KPIs.
4. Re-run the public beta checklist only when every prior gate has evidence.

## Project Status

Public beta, marketing, acquisition, monetization and scale remain blocked.

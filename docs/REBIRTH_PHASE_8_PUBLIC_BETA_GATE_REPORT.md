# Rebirth Phase 8 Report - Public Beta Gate

Updated: 2026-06-08

## Status

Phase 8 is not complete.

Current status: **blocked**.

## Gate Checklist

- QA green: passed locally and on GitHub. Current local suite:
  `1274 passed, 5 skipped, 19 deselected`. GitHub
  `rebirth-closed-beta-qa` is green for the pushed branch according to the
  pre-external gate.
- Error tracking active: blocked until `SENTRY_DSN` or compatible GlitchTip DSN
  is configured in the target environment.
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

## What Was Implemented

No public beta gate bypass was implemented.
Secret-free evidence validation was added so remaining Phase 0 gates can be
proven by operator records without committing secrets or relying only on manual
boolean flags.
The release dashboard now displays the evidence validity/errors and the
operator command for passing a private evidence file.

## Files Changed

- `services/rebirth_gate_evidence.py`
- `services/rebirth_product.py`
- `templates/rebirth_product.html`
- `tools/ops/rebirth_pre_external_gate.py`
- `docs/REBIRTH_EXTERNAL_GATE_EVIDENCE.example.json`

## Tests Executed

No Phase 8-specific public-beta validation was run because the gate is blocked.
The external pre-gate report was run with `--report-only` and returned
`ok=false`.
The evidence template was also run through `--evidence` and correctly rejected
with `example_evidence_file`.

Current external gate states:

- `legal_review`: blocked.
- `backup_restore`: blocked.
- `error_tracking`: blocked.
- `github_workflow`: passed.
- `billing_off`: passed.

## Coverage

Coverage was not reduced.

## Risks

- Moving to marketing/acquisition/monetization before these gates are green
  would violate the project plan and increase operational risk.
- The project can look locally healthy while still failing public beta due to
  missing production evidence.

## Next Steps

1. Finish Phase 0 external proof gates.
2. Run controlled closed beta.
3. Collect Phase 1, Phase 2 and Phase 5 KPIs.
4. Re-run the public beta checklist only when every prior gate has evidence.

## Project Status

Public beta, marketing, acquisition, monetization and scale remain blocked.

# Rebirth Phase 0 Readiness Report

Updated: 2026-06-08

## Status

Phase 0 implementation work is complete locally for this pass, the local
Rebirth suite is green, and GitHub QA is green on the pushed branch. The phase
itself is not complete until external evidence is attached for error tracking,
backup/restore and legal review.

Current status: **blocked on external proof**.

## Implemented In This Pass

1. Mobile E2E flake root cause addressed.
   - GitHub Actions failure showed `#rebirth-tutorial` intercepting
     `#next-turn-button` in the mobile variant of
     `test_authenticated_first_turn_blocks_direct_damage_until_bot_responds`.
   - The tutorial overlay now lets battlefield controls receive pointer input.
   - The tutorial balloon remains interactive for skip/next controls.
   - The E2E asserts the overlay contract directly.

2. Client observability strengthened.
   - Backend Sentry/GlitchTip initialization already exists through
     `SENTRY_DSN`.
   - Browser `error` and `unhandledrejection` capture already existed in
     `rebirth_global.js`.
   - API failures now report `client_error` telemetry from global/product/arena
     fetch wrappers with endpoint, status and error code metadata.

3. Public legal pages made reachable from the active Flask runtime.
   - `/terms`, `/privacy` and `/data-deletion` now render their existing pages.
   - `/feedback`, `/closed-test` and `/first-session` route users to the active
     Rebirth support/release/onboarding surfaces.
   - Privacy, terms and deletion copy now mention LGPD-oriented data rights,
     Rebirth support export/deletion and closed-beta billing restrictions.

4. Operational documentation added.
   - `docs/REBIRTH_DISASTER_RECOVERY_RUNBOOK.md` documents PostgreSQL backup,
     restore drill, validation and incident decision flow.
   - `docs/REBIRTH_CLOSED_BETA_RUNBOOK.md` links the DR runbook and clarifies
     evidence required before setting `REBIRTH_BACKUP_RESTORE_DRILL=true`.

## Files Changed

- `app.py`
- `static/css/rebirth.css`
- `static/js/rebirth.js`
- `static/js/rebirth_global.js`
- `static/js/rebirth_product.js`
- `templates/privacy.html`
- `templates/terms.html`
- `templates/data_deletion.html`
- `tests/rebirth/e2e/test_navigation_and_auth.py`
- `tests/rebirth/test_rebirth_frontend_contract.py`
- `tests/rebirth/test_rebirth_product_shell.py`
- `tests/rebirth/test_rebirth_routes.py`
- `docs/REBIRTH_CLOSED_BETA_RUNBOOK.md`
- `docs/REBIRTH_DISASTER_RECOVERY_RUNBOOK.md`
- `docs/REBIRTH_PHASE_0_READINESS_REPORT.md`

## Tests Executed

- `node --check static/js/rebirth_global.js`
- `node --check static/js/rebirth_product.js`
- `node --check static/js/rebirth.js`
- `node --check static/js/service-worker.js`
- `node tests/js/test_rebirth_audio_chain_dedup.cjs`
- `.venv/bin/python -m py_compile app.py services/rebirth_telemetry.py services/rebirth_beta_ops.py services/rebirth_schema.py services/rebirth_persistence.py`
- `.venv/bin/python -m pytest tests/rebirth/test_rebirth_frontend_contract.py tests/rebirth/test_rebirth_routes.py::test_client_error_telemetry_records_api_failure_metadata -q`
- `.venv/bin/python -m pytest tests/rebirth/test_rebirth_product_shell.py::test_phase0_legal_pages_are_publicly_reachable tests/rebirth/test_rebirth_frontend_contract.py tests/rebirth/test_rebirth_routes.py::test_client_error_telemetry_records_api_failure_metadata -q`
- `.venv/bin/python -m pytest -q -m e2e 'tests/rebirth/e2e/test_navigation_and_auth.py::test_authenticated_first_turn_blocks_direct_damage_until_bot_responds[mobile]' --capture=no`
- `.venv/bin/python -m pytest -q -m e2e tests/rebirth/e2e/test_navigation_and_auth.py --capture=no`
- `.venv/bin/python -m pytest tests/rebirth -q`
- `.venv/bin/python tools/rebirth_content_validate.py`
- `.venv/bin/python tools/qa/qa_rebirth_visual_screenshots.py --output-dir /tmp/rebirth-phase0-visual`
- `.venv/bin/python tools/rebirth_balance_report.py --matches 120 --output /tmp/rebirth-phase0-balance.md`
- `.venv/bin/python tools/ops/rebirth_pre_external_gate.py --report-only`
- `git diff --check`

Key local results:

- Full Rebirth test suite: `1272 passed, 5 skipped, 19 deselected`.
- Full navigation/auth E2E suite: `19 passed`.
- Phase 0 focused tests: `12 passed`.
- Visual screenshots: `RESULT=PASS`, no issues.
- Content validation: `ok=true`, `103` cards, art coverage `1.0`.
- Balance smoke report: player winrate `45.8%`, bot winrate `53.3%`,
  unfinished `0.8%`, average turns `15.57`, cards used `103/103`.
- GitHub `rebirth-closed-beta-qa`: passed on the pushed branch; the
  pre-external gate reports `github_workflow=passed` against the latest GitHub
  workflow result.
- Pre-external gate report: blocked on external proof for legal review,
  backup/restore and error tracking.

## Coverage

Coverage was not reduced. New regression coverage was added for:

- tutorial overlay pointer-event contract;
- mobile authenticated first-turn E2E overlay contract;
- API failure telemetry payload persistence;
- public reachability of legal pages and active Rebirth support redirects.

## Current Risks

- `SENTRY_DSN` must be configured in the target environment before the
  error-tracking gate can pass.
- A real PostgreSQL backup/restore drill must be executed and recorded outside
  the repo before setting `REBIRTH_BACKUP_RESTORE_DRILL=true`.
- LGPD/Terms/Privacy copy still requires owner/counsel review before setting
  `REBIRTH_LEGAL_REVIEWED=true`.
- Phase 0 cannot be closed from code alone.

## Next Steps

1. Configure `SENTRY_DSN` / GlitchTip-compatible DSN.
2. Execute the PostgreSQL restore drill using
   `docs/REBIRTH_DISASTER_RECOVERY_RUNBOOK.md`.
3. Complete external legal review and record approval.
4. Re-run `tools/ops/rebirth_pre_external_gate.py` without `--report-only`.

## Project Status

Ambitionz Rebirth remains a strong closed-beta candidate. Phase 0 is materially
closer to external tester readiness, but public beta remains blocked until all
external proof gates are green.

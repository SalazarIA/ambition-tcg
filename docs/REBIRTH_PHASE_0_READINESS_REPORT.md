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
   - The console sanity E2E keeps failing on JS/page errors but ignores known
     Chromium runner network blips such as `ERR_NETWORK_CHANGED`.

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
   - `docs/REBIRTH_EXTERNAL_GATE_EVIDENCE.example.json` documents the
     secret-free evidence shape for legal, backup/restore and error tracking.
   - `tools/ops/rebirth_pre_external_gate.py` can now validate an external
     evidence file with `--evidence`.
   - `/rebirth/release` now surfaces external-evidence validity/errors so the
     operator can see why legal, backup/restore or error tracking remain
     blocked.
   - `tools/ops/rebirth_error_tracking_smoke.py` can emit a Sentry/GlitchTip
     smoke event without printing the DSN and can produce the evidence snippet
     after operator confirmation.
   - `tools/ops/rebirth_backup_restore_drill.py` can dry-run or execute the
     PostgreSQL restore drill without printing database URLs.
   - External backup/restore evidence now expires after 30 days, and
     error-tracking smoke evidence expires after 14 days.
   - The final Phase 8 release gate now requires strict external evidence, so
     local flags and DSNs cannot substitute for legal, restore or
     error-tracking proof.

5. GitHub Actions runner deprecation risk addressed.
   - `rebirth-closed-beta-qa` and the PR `tests` workflow now use
     Node 24-compatible official Actions majors.
   - The change is CI infrastructure only; no gameplay, balance or engine rules
     were changed.

6. Phase report governance added.
   - `tools/ops/rebirth_phase_report_audit.py` now verifies that Phase 0-8
     reports all exist and keep the mandatory report sections from the
     execution plan.
   - The release readiness command and release dashboard/API now include this
     phase-report audit as a first-class gate group.
   - The release dashboard/API also use strict external evidence mode, so local
     flags and DSNs cannot make the web readiness surface greener than the
     final Phase 8 CLI gate.
   - `rebirth-closed-beta-qa` now runs the phase report audit as a CI gate and
     prints a report-only release readiness snapshot for the current branch/SHA.
   - This does not mark blocked phases complete; it only prevents missing or
     under-specified phase reports.

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
- `docs/REBIRTH_EXTERNAL_GATE_EVIDENCE.example.json`
- `docs/REBIRTH_PHASE_0_READINESS_REPORT.md`
- `.github/workflows/rebirth-closed-beta-qa.yml`
- `.github/workflows/test.yml`
- `services/rebirth_gate_evidence.py`
- `services/rebirth_phase_reports.py`
- `services/rebirth_product.py`
- `services/rebirth_release_readiness.py`
- `templates/rebirth_product.html`
- `app.py`
- `tools/ops/rebirth_error_tracking_smoke.py`
- `tools/ops/rebirth_backup_restore_drill.py`
- `tools/ops/rebirth_phase_report_audit.py`
- `tools/ops/rebirth_release_readiness.py`
- `tests/rebirth/test_rebirth_ops_tools.py`
- `tests/rebirth/test_rebirth_product_shell.py`
- `tests/rebirth/test_rebirth_release_readiness.py`

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
- `.venv/bin/python tools/ops/rebirth_pre_external_gate.py --report-only --evidence docs/REBIRTH_EXTERNAL_GATE_EVIDENCE.example.json`
- `.venv/bin/python tools/ops/rebirth_error_tracking_smoke.py`
- `.venv/bin/python tools/ops/rebirth_backup_restore_drill.py`
- `.venv/bin/python -m pytest tests/rebirth/test_rebirth_ops_tools.py tests/rebirth/test_rebirth_product_shell.py -q`
- `.venv/bin/python -m pytest tests/rebirth/test_rebirth_product_shell.py -q`
- `.venv/bin/python -m pytest tests/rebirth/test_rebirth_ops_tools.py::test_closed_beta_workflow_runs_release_governance_checks -q`
- `.venv/bin/python -c "import yaml; [yaml.safe_load(open(path, encoding='utf-8')) for path in ['.github/workflows/test.yml', '.github/workflows/rebirth-closed-beta-qa.yml']]; print('workflow_yaml_ok')"`
- `rg -n "actions/checkout@v4|actions/setup-python@v5|node20|Node.js 20" .github`
- `.venv/bin/python tools/ops/rebirth_phase_report_audit.py`
- `.venv/bin/python tools/ops/rebirth_release_readiness.py --report-only --since 2026-06-01T00:00:00+00:00 --release-version phase-report-gate`
- `git diff --check`

Key local results:

- Current full Rebirth test suite: `1295 passed, 5 skipped, 19 deselected`.
- External evidence, error-tracking smoke and backup/restore drill contracts are
  covered by focused ops/product tests and the current full suite.
- Full navigation/auth E2E suite: `19 passed`.
- Phase 0 focused tests: `12 passed`.
- Visual screenshots: `RESULT=PASS`, no issues.
- Content validation: `ok=true`, `103` cards, art coverage `1.0`.
- Balance smoke report: player winrate `45.8%`, bot winrate `53.3%`,
  unfinished `0.8%`, average turns `15.57`, cards used `103/103`.
- GitHub `rebirth-closed-beta-qa`: passed on the pushed branch; the
  pre-external gate reports `github_workflow=passed` only when the GitHub
  workflow result matches the expected branch/head commit.
- GitHub Actions workflow YAML parses locally, and the repo no longer contains
  the Node 20-deprecated action pins that were warning on the QA run.
- Phase report audit: `ok=true` for Phase 0 through Phase 8 report files.
- The closed-beta QA workflow now gates on the Phase 0-8 report audit and
  records a report-only release readiness snapshot with `actions: read` and the
  current branch/head SHA.
- Release readiness report now surfaces `phase_reports_ready=true` and
  `phase_reports_passed=9/9` while still blocking on external proof and human
  KPI evidence.
- Release dashboard/API external gates run in strict evidence mode and reject
  local flags as final readiness proof.
- Pre-external gate report: blocked on external proof for legal review,
  backup/restore and error tracking.
- Example evidence file: rejected intentionally with `example_evidence_file`.

## Coverage

Coverage was not reduced. New regression coverage was added for:

- tutorial overlay pointer-event contract;
- mobile authenticated first-turn E2E overlay contract;
- arena console sanity still catches app/JS errors while tolerating transient
  browser network errors from the CI runner;
- API failure telemetry payload persistence;
- public reachability of legal pages and active Rebirth support redirects.
- secret-free external gate evidence validation.
- external evidence template rejection for source-control examples and common
  secret-like values.
- mandatory Phase 0-8 report structure.
- final release readiness composition includes external proof, phase reports
  and public beta KPIs.
- release dashboard/API cannot pass final external gates with local flags or a
  configured DSN alone.
- release dashboard rendering for evidence errors and `--evidence` command.
- error-tracking smoke evidence requires operator confirmation before the gate
  can pass.
- dry-run error-tracking smoke does not fail the shell or print a DSN.
- dry-run backup/restore drill does not execute restore or print database URLs.
- backup/restore evidence requires schema, health and support-export checks
  before it can pass the gate.
- backup/restore and error-tracking evidence must be fresh enough for an
  external tester gate.
- backup/restore evidence with unresolved issues cannot pass the external gate.
- GitHub QA evidence is scoped to the expected branch/head commit instead of
  any latest workflow run or manual override.
- closed-beta QA workflow coverage asserts that release governance checks stay
  wired into CI without turning blocked external/human gates into a bypass.

## Risks

- `SENTRY_DSN` must be configured in the target environment before the
  pre-external error-tracking gate can pass, and a confirmed smoke-event
  evidence record is required before the strict Phase 8 gate can pass.
- A real PostgreSQL backup/restore drill must be executed and recorded outside
  the repo before setting `REBIRTH_BACKUP_RESTORE_DRILL=true`.
- LGPD/Terms/Privacy copy still requires owner/counsel review before setting
  `REBIRTH_LEGAL_REVIEWED=true`.
- Evidence JSONs must stay outside source control when filled with real
  operator references.
- Local readiness flags are useful for closed-beta operations only after real
  evidence exists; they do not close the final public-beta gate.
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

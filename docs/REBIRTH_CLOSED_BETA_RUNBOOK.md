# Ambitionz Rebirth Closed Beta Runbook

Updated on 2026-06-09.

## Entry Gate

- `pytest -q` passes locally.
- `pytest -q -m e2e tests/rebirth/e2e/test_navigation_and_auth.py` passes.
- `python tools/qa/qa_rebirth_visual_screenshots.py --output-dir /tmp/rebirth-closed-beta-qa` passes with no blocking overlap. Committed baselines live in `tests/rebirth/visual_baselines/`.
- `python tools/rebirth_balance_report.py --matches 200 --output docs/REBIRTH_BALANCE_REPORT.md` shows global/profile player win rate inside the 44% to 53% closed-beta gate, with 44% to 52% kept as the next tuning target.
- `pip-audit -r requirements.txt` and `pip-audit -r requirements-dev.txt` pass in the supported Python 3.11.9 environment used by Render/CI.
- Support export, reset, feedback capture and permanent account deletion are tested.
- Terms, Privacy, Data Deletion and Support are reachable from the account/support surfaces.
- `python tools/ops/rebirth_pre_external_gate.py --report-only` records the
  external-test readiness gates.
- When external checks exist, pass a secret-free evidence file with
  `python tools/ops/rebirth_pre_external_gate.py --evidence /secure/path/rebirth-external-gates.json`.
  Use `docs/REBIRTH_EXTERNAL_GATE_EVIDENCE.example.json` only as a template;
  the example file is intentionally rejected by the validator.
- Public beta KPIs are checked separately with
  `python tools/ops/rebirth_public_beta_gate.py --since <cohort-start-iso> --require-ready`.
- The final Phase 8 gate composes external proof and product KPIs with
  `python tools/ops/rebirth_release_readiness.py --since <cohort-start-iso> --evidence /secure/path/rebirth-external-gates.json`.
- Monetization remains off by default. `REBIRTH_ENABLE_BILLING=true` is required
  for checkout, and Stripe live keys also require `REBIRTH_ALLOW_STRIPE_LIVE=true`.
- The current local pre-external gate is expected to be **not ready** until
  external legal, Render/Postgres, Sentry/GlitchTip and GitHub workflow evidence
  are supplied.

## Beta Tester Loop

1. Tester creates an account and accepts age/privacy terms.
2. Tester plays the guided first match.
3. Tester opens `/rebirth/onboarding` for keyword glossary if confused.
4. Tester claims daily reward after first clash.
5. Tester opens a free beta booster.
6. Tester adjusts deck and plays at least 3 matches.
7. Tester reports friction from the support or feedback surfaces.

## Metrics To Watch

- First match completion: target 70%+.
- Tutorial completion: target 80%+.
- Median matches per active tester/day: target 3+.
- D1 retention: target 35%+.
- D7 retention: target 20%+.
- Crash/error rate: target below 1% once error tracking has at least 100
  telemetry events.
- Human telemetry sample: 500+ finished human matches before public beta or
  major balance patches.
- Balance coverage: 60%+ of catalog used in deterministic lab.
- Dead-hand cards above 30%: target zero unless intentionally flagged.
- Match API p95: target below 300 ms in beta load.

## Operational Checks

- Run the scheduled `rebirth-closed-beta-qa` workflow daily.
- Keep a fresh 200-match balance report after balance changes.
- Review `/health` after deploy.
- Configure `SENTRY_DSN` for Sentry, GlitchTip or a compatible endpoint before
  inviting external testers.
- Confirm and date a Render/Postgres backup restore drill before inviting
  external testers. Use `docs/REBIRTH_DISASTER_RECOVERY_RUNBOOK.md` as the
  operator checklist.
- Keep a manual rollback target: last green commit on `main`.
- Keep Stripe live keys unset during closed beta unless compliance and backup checks are done.
- Use `/rebirth/release` to watch Readiness Final, external gates, D1/D7,
  first-match completion, tutorial completion, feedback and client errors.
- Use `/rebirth/release?since=<cohort-start-iso>` or
  `/api/rebirth/release?since=<cohort-start-iso>` when reviewing a specific
  closed-beta cohort window.
- Run `python tools/ops/rebirth_release_readiness.py --report-only --since <cohort-start-iso> --evidence /secure/path/rebirth-external-gates.json`
  after each evidence update or KPI review.
- Add `--since 2026-06-09T00:00:00+00:00` to KPI/readiness commands when
  reviewing a specific closed-beta cohort window; use the real cohort start.

## External Proof Checklist

- Legal: have counsel or the responsible operator review Terms, Privacy,
  deletion/export language and monetization/refund copy. Set
  `REBIRTH_LEGAL_REVIEWED=true` only after that review is recorded, or provide
  a valid external evidence JSON through `--evidence`.
- Backup/restore: run a real Postgres drill against a disposable restore
  database, compare `/health` plus a signed-in export, then set
  `REBIRTH_BACKUP_RESTORE_DRILL=true`, or provide a valid external evidence
  JSON through `--evidence`. Use
  `python tools/ops/rebirth_backup_restore_drill.py` for a redacted dry-run and
  add `--execute --i-understand-restore-target-is-disposable` only when the
  restore target is disposable.
- Error tracking: set `SENTRY_DSN` for Sentry, GlitchTip or a compatible DSN.
  Keep `SENTRY_ENVIRONMENT=closed-beta` and a conservative
  `SENTRY_TRACES_SAMPLE_RATE` until traffic is understood. A valid external
  evidence JSON can also prove the target environment received a test event
  without storing the DSN in source control.
  Use `python tools/ops/rebirth_error_tracking_smoke.py --send` in the target
  environment to emit a smoke event. After confirming the event in the provider,
  re-run with `--confirmed-evidence-ref` or copy the printed evidence fields
  into the private gate evidence file.
- GitHub QA: run or schedule `rebirth-closed-beta-qa.yml`; the gate checks the
  current `HEAD` by default. When auditing manually, use `gh run list
  --workflow rebirth-closed-beta-qa.yml --branch <branch> --commit <head-sha> --limit 1 --json status,conclusion,headSha`
  and require `conclusion=success` for that exact branch and commit.
- Stripe: keep `REBIRTH_ENABLE_BILLING=false`, `REBIRTH_ALLOW_STRIPE_LIVE=false`
  and live Stripe keys unset for closed beta.

Example backup drill commands:

```bash
pg_dump "$REBIRTH_DATABASE_URL" --format=custom --file=/tmp/rebirth-drill.dump
createdb rebirth_restore_drill
pg_restore --clean --if-exists --no-owner --dbname=rebirth_restore_drill /tmp/rebirth-drill.dump
```

The drill is not complete until a disposable restored database passes
`python -m services.rebirth_schema check`, `/health`, and a signed-in support
export check. Store the evidence record outside source control before setting
`REBIRTH_BACKUP_RESTORE_DRILL=true`.

Evidence files must not contain raw database URLs, DSNs, passwords, Stripe keys
or unredacted host credentials. The validator rejects the repository template
and common secret-like values.

## Incident Response

- Payment or billing issue: disable checkout env vars first, then investigate.
- Account/data issue: use support export before reset or deletion when possible.
- Balance break: revert balance patch or lower `REBIRTH_BALANCE_INTERACTIVE_MATCH_LIMIT` only for lab load, not gameplay.
- UI overlap: run visual QA, capture screenshots, then patch the smallest affected surface.
- Data loss suspicion: stop inviting testers, snapshot DB, inspect audit/economy ledgers, then restore only with owner approval.

## Exit Gate To Public Beta

- 100 closed beta testers can play one week without manual DB fixes.
- No P0/P1 account, reward or deletion bugs open.
- Legal review completed for Terms, Privacy, deletion/export and monetization copy.
- Backup restore drill completed.
- Error tracking configured through Sentry, GlitchTip or equivalent.
- `python tools/ops/rebirth_release_readiness.py --since <cohort-start-iso> --evidence /secure/path/rebirth-external-gates.json`
  exits with success.
- Public beta KPI gate is green: tutorial 80%+, first match 70%+, D1 35%+,
  D7 20%+, crash/error below 1%, 500+ finished human matches and healthy
  balance.
- GTM assets ready: current screenshots, gameplay clip, landing copy and community/support channel.

# Ambitionz Rebirth Closed Beta Runbook

Updated on 2026-06-01.

## Entry Gate

- `pytest -q` passes locally.
- `pytest -q -m e2e tests/rebirth/e2e/test_navigation_and_auth.py` passes.
- `python tools/qa/qa_rebirth_visual_screenshots.py --output-dir /tmp/rebirth-closed-beta-qa` passes with no blocking overlap.
- `python tools/rebirth_balance_report.py --matches 200 --output docs/REBIRTH_BALANCE_REPORT.md` shows global/profile player win rate inside the 44% to 53% closed-beta gate, with 44% to 52% kept as the next tuning target.
- Support export, reset and permanent account deletion are tested.
- Terms, Privacy, Data Deletion and Support are reachable from the account/support surfaces.
- Monetization remains beta/sandbox unless legal and ops review approve live payments.

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
- Tutorial completion: target 60%+.
- Median matches per active tester/day: target 3+.
- D1 retention: target 40%+.
- D7 retention: target 20%+.
- Balance coverage: 60%+ of catalog used in deterministic lab.
- Dead-hand cards above 30%: target zero unless intentionally flagged.
- Match API p95: target below 300 ms in beta load.

## Operational Checks

- Run the scheduled `rebirth-closed-beta-qa` workflow daily.
- Keep a fresh 200-match balance report after balance changes.
- Review `/health` after deploy.
- Confirm Render/Postgres backup policy before inviting external testers.
- Keep a manual rollback target: last green commit on `main`.
- Keep Stripe live keys unset during closed beta unless compliance and backup checks are done.

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
- GTM assets ready: current screenshots, gameplay clip, landing copy and community/support channel.

# Ambitionz Internal Release Candidate Checklist

Use this checklist after deploying a candidate build to Render.

## Automated Gate

1. Open `/health` and confirm database is `ok`.
2. Open `/admin/release-candidate`.
3. Confirm every required check is `OK`.
4. Review open critical feedback and unresolved error logs.

## Manual Smoke Path

1. Register a fresh account.
2. Verify the account or manually verify it in Admin > Users.
3. Log in and complete onboarding.
4. Start Training on normal difficulty.
5. Select intent, play a monster, press Ready, and finish the match.
6. Confirm post-match rewards, missions, XP, coins, profile, and match history.
7. Open a booster and confirm booster history.
8. Edit and save the deck.
9. Submit feedback and confirm it appears in Admin > Feedback Ops.

## RC Exit Criteria

- No 500s in core routes.
- No open critical feedback.
- Training rewards use PvE values.
- Training missions progress.
- Feedback and beta event logs arrive in admin.
- A complete match can start, resolve, reward, and clean up.

# Ambitionz Internal Release Candidate Checklist

Use this checklist after deploying a candidate build to Render.

## Automated Gate

1. Open `/health` and confirm database is `ok`.
2. Open `/admin/release-candidate`.
3. Confirm every required check is `OK`.
4. Review open critical feedback and unresolved error logs.
5. Confirm Render has `PUBLIC_BASE_URL`, `SOCKETIO_CORS_ALLOWED_ORIGINS`, `WTF_CSRF_ENABLED=true`, `SESSION_COOKIE_SECURE=true`, and SMTP env vars configured.
6. Run `python tools/preflight.py`, `pip-audit -r requirements.txt`, and `npm audit` before promoting the build.

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
- CSRF-protected forms submit normally from the deployed domain.
- Socket.IO connects only from the expected public origin.

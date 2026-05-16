# Arena V6 Production Validation

Use this checklist after deploying Arena V6 changes to Render.

Production URL: https://ambition-tcg.onrender.com/training

## Quick Smoke

- Open `https://ambition-tcg.onrender.com/health`.
- Confirm the response is JSON and includes `status: ok` or an equivalent healthy status.
- Open `https://ambition-tcg.onrender.com/training`.
- If Render is sleeping, wait for the first request to wake it and retry.
- Confirm the page does not show a server traceback, raw JSON, or a missing static asset error.

## Service Worker And Cache

- Open DevTools > Application > Service Workers.
- Confirm the active service worker is the latest deployed build.
- Confirm `service-worker.js` includes the expected cache name for the release, currently `ambitionz-web-app-v191` locally.
- Hard refresh once with DevTools open.
- Test in an anonymous/private window to avoid stale service worker cache.
- Confirm `/static/css/arena_clean_v48.css` and `/static/js/arena_clean_v48.js` load with the deployed cache-bust query.

## Cache Guard / Hard Refresh

- Set `AMBITIONZ_EXPECTED_SW_VERSION=ambitionz-web-app-v191` when validating RC V6 production.
- Use DevTools > Application > Clear site data before judging a visual regression.
- Hard refresh with DevTools open after clearing site data.
- Test one anonymous/private window to avoid a stale service worker from a previous RC.
- Confirm both `/service-worker.js` and `/static/js/service-worker.js` contain the expected cache name.
- If production still shows an older Arena, check the Render deploy status before debugging frontend code.

## Arena Boot

- On `/training`, confirm the Arena shell renders without a vertical dashboard feel.
- Confirm the compact HUD appears at the top with enemy HP/EN/status, round/phase, and player HP/EN/AMB/Intent.
- Confirm the battlefield is the dominant area of the screen.
- Confirm the enemy row and player row are visible at the same time on desktop.
- Confirm the hand/action row is visible below the battlefield.
- Confirm the info drawer shows compact tabs: `Next`, `Card`, `Log`, `Summary`.

## Training Flow

- Press `Start Training`.
- Confirm the opening hand appears.
- Confirm the first-battle tutorial is visible only when expected and does not block all gameplay clicks.
- Choose `Strike`, `Guard`, and `Focus` in separate runs when possible.
- Select a Creature card and confirm valid player lanes highlight.
- Click a valid lane and confirm the card is removed from hand and appears on the player row.
- Select a Spell and confirm the UI gives a clear target/cast-now instruction.
- Select a Trap and confirm the UI gives a clear Trap Zone/prepared-trap instruction.
- Press `Ready` and confirm the round resolves.
- Open `Summary` and confirm the round explains damage, shield, Ambition, cards played, and deaths without raw JSON.
- Open `Log` and confirm recent events are readable and the newest event is visually distinct.

## Mobile

- Test around 390px width.
- Confirm HUD remains compact.
- Confirm lanes do not disappear.
- Confirm hand cards are readable in a horizontal carousel.
- Confirm the primary action button does not cover the hand.
- Confirm the info drawer stays compact.
- Confirm the tutorial can be skipped and replayed.

## Recovery

- Hard refresh during `/training`.
- Confirm the page reconnects without a broken socket state.
- Use a private window to confirm a clean load.
- Confirm guest/fallback mode still reaches the training entry or redirects safely.

## Local Script

Run:

```bash
python3 tools/qa/qa_production_smoke.py
```

The script is intentionally defensive. It checks `/health`, `/training`, service worker, and key static assets. If production is protected or redirects `/training`, it reports that as a warning instead of requiring credentials.

Optional environment:

```bash
AMBITIONZ_PROD_URL=https://ambition-tcg.onrender.com \
AMBITIONZ_EXPECTED_SW_VERSION=ambitionz-web-app-v191 \
python3 tools/qa/qa_production_smoke.py
```

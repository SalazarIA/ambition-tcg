# Rebirth Last 3 Days Roadmap

Updated: 2026-06-02

Window reviewed: 2026-05-30 through 2026-06-02.

## Executive Read

The last three-day push moved Ambitionz Rebirth from a visually unstable but promising web duel into a closed-beta candidate with Python-owned production foundations.

The most important change is not one feature. It is the direction:

- The game is now explicitly Python-first and server-authoritative.
- The browser is being pushed toward renderer/input responsibilities.
- Closed-beta operations, content validation, telemetry balance and async competition now have concrete Python contracts.
- Visual identity moved from generic arena styling toward dark-fantasy tactical card presentation.
- The remaining work is less "invent the game" and more "operate, measure, modularize and polish it like a studio product."

## Git Snapshot

From 2026-05-30 00:00 through 2026-06-02:

- Commits: 34
- Date distribution:
  - 2026-05-30: 6 commits
  - 2026-05-31: 22 commits
  - 2026-06-01: 5 commits
  - 2026-06-02: 2 commits
- Aggregate diff from the first reviewed commit through HEAD:
  - 128 files changed
  - 12,641 insertions
  - 38,292 deletions
- The large deletion count is mainly historical QA/report cleanup, not active game removal.

Most frequently changed files:

- `static/css/rebirth.css`
- `app.py`
- `tests/rebirth/test_rebirth_frontend_contract.py`
- `static/js/service-worker.js`
- `static/assets/rebirth/manifest.json`
- `services/rebirth_art.py`
- `static/js/rebirth.js`
- `services/rebirth_engine.py`
- `services/rebirth_persistence.py`

## What Changed

### 1. Visual Identity Became A Real Direction

The visual pass moved through dark-fantasy, Duel of Champions/Fates-inspired work, hero portraits, battlefield framing, card frames, 2.5D card motion, game-feel FX, mobile web layout fixes and desktop arena stabilization.

What this means:

- The game now has a recognizable visual target.
- The arena is more readable and more premium than three days ago.
- The CSS grew into a production risk, but the identity finally has enough signal to modularize without losing direction.

Current risk:

- `static/css/rebirth.css` remains too large for fast studio iteration.
- Visual baselines now exist, but they need a routine review/pixel-diff process before public beta.

### 2. Core Combat And Card Systems Advanced

The core loop received:

- 8 mechanical keywords.
- Conditional synergies.
- REGEN and TAUNT semantic hooks.
- Better bot personality/balance support.
- V96 core loop stabilization.
- Balance reporting improvements.
- Coverage for all 103 cards in deterministic balance lab.

Latest 200-match balance signal:

- Player win rate: 47.5%
- Bot win rate: 51.5%
- Unfinished: 1.0%
- Average turns: 15.77
- Card usage: 103/103
- Dominant/low-impact flags: none in the 200-match pass

What this means:

- The game is no longer just visually playable; it has a measurable combat core.
- Simulation is useful for regression.
- Human telemetry is still required before calling balance "real."

### 3. Product Surfaces Became Beta-Shaped

Added or strengthened:

- In-game tutorial.
- Deck builder visual + persistence.
- Ranked ELO and leaderboard.
- Billing checkout/webhook path, then beta-safe live-payment gating.
- SEO/sitemap/robots.
- Account support surfaces.
- Export/delete/reset flows.
- Feedback capture.
- Post-match recap.
- Deck coaching after boosters and matches.
- Release hygiene dashboard.

What this means:

- The game now has a real beta loop: play, learn, recap, collect, adjust, return.
- Monetization code exists, but the current product stance is correct: Stripe/live payments stay off during closed beta.

### 4. Closed-Beta Readiness Became Explicit

The beta gate now covers:

- Legal review flags.
- Backup/restore drill flag.
- Sentry/GlitchTip-compatible error tracking via `SENTRY_DSN`.
- GitHub workflow `rebirth-closed-beta-qa`.
- Billing-off enforcement.
- Visual baselines.
- Content validation.
- Balance report automation.

What this means:

- The team has a go/no-go system instead of relying on memory.
- External tester readiness is visible in `/rebirth/release`.

Still missing:

- Actual external legal signoff.
- Actual Render/Postgres restore drill proof.
- Actual GitHub run confirmation after this latest push.
- Actual Sentry/GlitchTip project configured in the target environment.

### 5. AAA Python Foundations Were Added

The latest pass created Python-owned contracts for:

- First 10 minutes: `services/rebirth_first_session.py`
- Retention loop: `services/rebirth_retention.py`
- Content/art validation: `services/rebirth_content_pipeline.py`
- Real telemetry balance: `services/rebirth_live_balance.py`
- Async replay/ghost competition: `services/rebirth_async_competition.py`
- Telemetry event shape: `services/rebirth_telemetry.py`

New or strengthened APIs:

- `GET /api/rebirth/first-session`
- `GET /api/rebirth/content/validate`
- `GET /api/rebirth/balance/telemetry`
- `GET /api/rebirth/async/share/<match_id>`
- `GET /api/rebirth/async/ghosts`
- guest session resume through `/api/rebirth/resume`

What this means:

- The roadmap is no longer only docs.
- The next production systems now have Python surfaces that tests can lock.
- Async competition exists as a verified contract, not yet as a player-facing social product.

## Current State

Rebirth is now a closed-beta candidate, not a public-beta product yet.

Strong enough for controlled testing:

- Core PvE loop.
- Auth/account persistence.
- Collection/loadout/progression.
- No-payment boosters.
- Tutorial/recap/deck suggestions.
- Feedback and release dashboard.
- Deterministic replay foundations.
- Content validation.
- Visual baselines.
- Closed-beta QA workflow.

Not strong enough for public scale yet:

- No real human telemetry sample.
- No external legal/restore/error-tracking proof.
- CSS/JS/app/persistence files are too large.
- Guest reconnect is session-memory only, not durable across process/browser loss.
- Async competition has backend contracts but no polished UX.
- Live ops, season tooling and support workflows are still minimal.
- Realtime PvP should still wait.

## Roadmap From Here

### Phase 0 - Prove External Tester Readiness

Timeframe: now to next release gate.

Must happen:

- Confirm `rebirth-closed-beta-qa` green on GitHub after commit `48b815c`.
- Configure `SENTRY_DSN` or GlitchTip-compatible DSN in the beta environment.
- Run and document a real Render/Postgres backup/restore drill.
- Get legal review for Terms, Privacy, deletion/export and monetization copy.
- Keep `REBIRTH_ENABLE_BILLING=false` and `REBIRTH_ALLOW_STRIPE_LIVE=false`.

Exit criteria:

- `/rebirth/release` shows every external gate passed.
- One tester account can export data after a restore drill.
- No live payment path is reachable.

### Phase 1 - First 10 Minutes V2

Timeframe: first closed-beta week.

Must happen:

- Measure first-session actions from `services/rebirth_first_session.py`.
- Track first match started, first match completed, tutorial step views, post-match recap, booster open and deck edit.
- Improve the first match based on real confusion, not assumptions.
- Make post-match recap more actionable if feedback says players still do not know why they lost.

Exit criteria:

- First match completion target: 70%+.
- Tutorial completion target: 60%+.
- Most common onboarding complaint is no longer "I do not know what to do."

### Phase 2 - Human Balance And Retention Read

Timeframe: 1-2 beta weeks.

Must happen:

- Collect enough human matches for `services/rebirth_live_balance.py`.
- Compare human data with deterministic lab.
- Watch defensive bot profile, match length and cards dead in hand.
- Track D1, D7, tutorial completion, first-match completion, errors and feedback volume.

Exit criteria:

- 500+ human finished matches before major balance patch.
- Balance patch notes include before/after telemetry.
- Defensive target stays near or below the intended bot win ceiling.

### Phase 3 - Modularization Sprint

Timeframe: after beta blockers, before public beta.

Must happen:

- Split `services/rebirth_persistence.py` by domain:
  - users/auth
  - collection/loadout/decks
  - economy/ledger/billing
  - match history/replay
  - telemetry/admin
- Split `app.py` into Rebirth route modules or blueprints.
- Split `static/js/rebirth.js` into renderer/input modules.
- Split `static/css/rebirth.css` into domain CSS files while keeping visual baselines stable.

Exit criteria:

- No gameplay authority moves into JS.
- Tests stay green after each extraction.
- New features no longer require touching giant files by default.

### Phase 4 - Content And Art Production

Timeframe: before public beta.

Must happen:

- Turn `tools/rebirth_content_validate.py` into a required content gate.
- Define Season 0 card bible.
- Prioritize bespoke art for starter cards, legendaries and campaign bosses.
- Add manifest checks for every new card.
- Add copy length checks for mobile containers.

Exit criteria:

- Content pipeline blocks invalid card additions.
- First-session cards have finished art.
- No card text breaks the UI.

### Phase 5 - Async Competition Productization

Timeframe: after replay-share contract stabilizes.

Must happen:

- Build UI for replay share.
- Build ghost challenge entry points.
- Add privacy-safe share links.
- Add audit view for async results.
- Add weekly PvE ladder before realtime PvP.

Exit criteria:

- Players can share/replay a match without exposing account data.
- Async results are server-verifiable.
- Competition improves retention without realtime networking risk.

### Phase 6 - Public Beta Gate

Timeframe: only after closed-beta metrics are good.

Must happen:

- Durable reconnect for authenticated and guest flows.
- Load test expected public-beta traffic.
- Rate limits beyond auth.
- Admin audit views for feedback, economy, errors and account actions.
- Visual screenshot baseline workflow.
- Public support/recovery runbook.

Exit criteria:

- 100-500 users can play for a week without manual DB fixes.
- Error rate stays below target.
- Backup restore drill repeats cleanly.
- No critical onboarding/balance issue remains open.

## What Not To Do Yet

- Do not launch realtime PvP yet.
- Do not enable live payments yet.
- Do not rewrite the renderer in Pyodide/native before retention is proven.
- Do not add more big features into `app.py`, `rebirth.js` or `rebirth.css` before the modularization sprint.
- Do not balance around simulation alone once human data starts arriving.

## Studio North Star

For the next phase, the question is not "what else can we add?"

The question is:

> Can a new tester understand the first match, finish it, know why they won or lost, want to improve the deck, and come back tomorrow?

Everything that helps that answer become "yes" moves up.

Everything else waits.

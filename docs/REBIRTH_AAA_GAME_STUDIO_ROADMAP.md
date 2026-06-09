# Ambitionz Rebirth AAA Game Studio Roadmap

Updated: 2026-06-02

## Executive Vision

Ambitionz Rebirth should become a Python-authored, server-authoritative tactical card battler with the readability of a premium mobile game, the deterministic rigor of a competitive TCG backend, and the production discipline of a small AAA strike team.

The game should not grow by adding disconnected pages. It should grow by making one promise deeper:

> Build a battlefield, read the opponent, evolve your monsters, win through tactical card decisions, and keep improving your collection over seasons.

The current game is a credible closed-beta foundation. The AAA path is not "more features everywhere"; it is tighter ownership, stronger first-session direction, real telemetry, better content production, disciplined live operations, and a Python-first architecture where the rules, simulation, content validation, economy and tooling all live in Python.

## Implemented Studio Foundation Pass - 2026-06-02

This pass converts the roadmap into shipped Python-owned contracts:

- First-session planning lives in `services/rebirth_first_session.py` and is exposed to the arena as data.
- Daily/weekly retention loop decisions live in `services/rebirth_retention.py`.
- Content and art validation live in `services/rebirth_content_pipeline.py`.
- Human telemetry balance reporting lives in `services/rebirth_live_balance.py` and requires a real-match sample before balance claims.
- Async competition starts with replay-share and ghost-challenge contracts in `services/rebirth_async_competition.py`.
- Telemetry event shapes live in `services/rebirth_telemetry.py`.
- Guest reconnect now resumes the active match inside the same browser session; authenticated reconnect remains PostgreSQL-backed.

This does not mean every AAA phase is complete. It means the product now has concrete Python seams for external testing, first-session measurement, content validation, human balance analysis, retention iteration and async competition.

## Python-First Mandate

The product direction is Python-first.

Non-negotiables:

- Gameplay rules live in Python.
- Card effects live in Python.
- Bot logic, balance simulation, replay, telemetry analysis and economy rules live in Python.
- Persistence and migration logic live in Python.
- Content validation and release gates live in Python.
- Browser JavaScript must stay a renderer/input shell, not a gameplay authority.

Practical browser-game boundary:

- The current browser client still needs HTML/CSS/JavaScript to render, animate and collect input.
- The AAA mandate is not to move game authority into JavaScript. It is to keep JavaScript thin enough that replacing it with a Python client, Pyodide layer, native shell or future renderer would not change the game.
- Any feature that changes outcomes must be implemented and tested first in Python, then exposed to the client as data.

Long-term Python client options:

- Keep Flask/Python authoritative and use JS only as a view layer. This is the recommended beta/public-launch path.
- Prototype a Pyodide/Python client shell only after public-beta stability, if "all Python in browser" remains a hard brand/engineering requirement.
- Avoid rewriting the game in a new engine before retention is proven. A rewrite now would burn the current deterministic advantage.

## Directory-Wide Snapshot

Repo scan on 2026-06-02:

| Area | Current signal |
| --- | --- |
| Total tracked/visible files scanned | 820 |
| Python files | 265 |
| Markdown docs | 129 |
| HTML templates | 62 |
| JavaScript files | 32 |
| CSS files | 14 |
| Current counted LOC sample | 98,042 lines |
| Active catalog | 103 cards |
| Latest full suite | 1268 passed, 5 skipped, 19 deselected |
| Latest E2E | 19 passed |
| Latest balance lab | Player WR 47.5%, Bot WR 51.5%, 103/103 cards used |

Largest active risk files:

| File | LOC | Studio read |
| --- | ---: | --- |
| `static/css/rebirth.css` | 14,270 | Visual identity works, but this must become modular CSS before public scale. |
| `static/js/rebirth.js` | 3,966 | Acceptable for closed beta; not acceptable as a long-term feature surface. |
| `services/rebirth_persistence.py` | 3,157 | Needs repository/domain split before more economy, telemetry or social systems. |
| `app.py` | 2,327 | Flask routes should move into blueprints before launch/open beta. |
| `services/rebirth_engine.py` | 2,051 | Strong core, but new mechanics need smaller rules modules. |

The repo is already Python-heavy where it matters. The remaining problem is not "there is JS"; it is that the JS/CSS/templates are still too large and too central for AAA iteration speed.

## Current Product Truth

What is strong:

- Python deterministic engine with command/event log, replay and state hashes.
- PostgreSQL-authoritative account, collection, loadout, progression and history.
- Closed-beta gates for legal, backup/restore, Sentry/GlitchTip, GitHub QA and billing-off.
- Balance lab now covers 103/103 cards.
- Visual baseline screenshots are versioned.
- Support export/delete and feedback capture exist.
- Post-match recap, first-match guidance, first-session plan and deck suggestions exist.
- Content/art validation and live telemetry balance contracts exist.
- Async replay-share/ghost contracts exist behind authenticated APIs.

What is not AAA yet:

- No real player telemetry sample yet.
- No legal/backup/Sentry/GitHub external proof yet.
- First session is improved, but not measured.
- Card art coverage and content pipeline are not production-grade.
- CSS/JS/persistence/app files are too large.
- Reconnect is improved for guest session memory but not yet durable across browser/process loss.
- No live config, no season tooling, no content authoring workflow.
- No PvP, no async rivals, no ranked ladder; replay share is only a verified contract, not a social product.

## AAA Product Pillars

### 1. Tactical Clarity

Every turn must answer three questions instantly:

- What can I do?
- What will probably happen?
- Why did the result happen?

Needed improvements:

- Risk preview before attack.
- Cleaner combat recap hierarchy.
- Better action-state copy in the main CTA.
- Tutorial beats driven by real player confusion telemetry.
- Field/trap/spell readability at a glance.

### 2. Collection Desire

Players should want cards before they understand every rule.

Needed improvements:

- More bespoke art for high-usage and chase cards.
- Clear rarity fantasy and set identity.
- Card mastery/progression per favorite card.
- Deck archetype labels: Fire pressure, Earth fortress, Shadow drain, Water sustain.
- Pack opening that teaches "why this card matters" instead of only revealing cards.

### 3. Fair Competitive Foundation

The game must feel readable before it feels deep.

Needed improvements:

- Real telemetry balancing after closed beta.
- Bot tuning by cohort: novice, learning, standard, expert.
- Deterministic replay for support and future anti-cheat.
- Matchmaking path starts with async ghost/rival before realtime PvP.
- Balance changes must be versioned and reversible.

### 4. Live Game Operations

AAA discipline means production can change safely.

Needed improvements:

- Sentry/GlitchTip live.
- Postgres backup/restore drill completed and documented.
- Daily QA workflow green on GitHub.
- Release dashboard with real D1/D7, tutorial, errors and first-match completion.
- Live config for balance/content flags.
- Incident runbooks for data loss, exploit, economy bug and broken deploy.

### 5. Python Authorship

Designers and engineers should be able to inspect, simulate and validate the game from Python.

Needed improvements:

- Python content schema for cards, sets, campaigns, rewards and seasons.
- Python CLI for content validation.
- Python balance notebooks/reports from real telemetry.
- Python replay debugger that can reconstruct any reported match.
- Python-generated frontend contracts so JS only renders declared state.

## Roadmap By Studio Phase

### Phase 0 - External Closed-Beta Gate

Goal: do not invite external testers until the product can be observed, restored and legally defended.

Status: code gates implemented; external proof still blocked.

Must finish:

- Legal review of Terms, Privacy, deletion/export and monetization copy.
- Render/Postgres backup and restore drill.
- Sentry/GlitchTip DSN configured.
- `rebirth-closed-beta-qa` green on GitHub.
- Stripe/live payments remain disabled.

Exit criteria:

- `/rebirth/release` shows every external gate passed.
- A signed-in export still works after restore drill.
- Full suite, E2E, visual QA and balance report pass in CI.

### Phase 1 - First Session Vertical Slice

Goal: the first 10 minutes must feel like a finished game.

Must improve:

- Arena starts with one obvious tactical goal.
- Tutorial reacts to player state, not just fixed text.
- First match recap explains cause of win/loss.
- Booster after first match gives a useful deck suggestion.
- Mobile first viewport is less crowded.
- Audio/haptics/impact moments are tuned for clarity, not noise.

Exit criteria:

- 70%+ first-match completion in closed-beta telemetry.
- 80%+ tutorial completion.
- Less than 10% of first-match users hit support/help before first summon.
- Median first completed match under target session length.

### Phase 2 - Python Core Refactor

Goal: make future mechanics safe and fast to build.

Must improve:

- Split `services/rebirth_engine.py` by rule domain:
  - combat resolution
  - spells
  - traps
  - passive abilities
  - turn lifecycle
  - reward/reason builders
- Split `services/rebirth_persistence.py`:
  - schema repo
  - user/auth repo
  - match repo
  - economy repo
  - collection/deck repo
  - telemetry repo
- Split `app.py` into Flask blueprints:
  - arena API
  - account/auth
  - product shell
  - economy/shop
  - support/admin
  - release/ops
- Keep deterministic replay and tests green after each extraction.

Exit criteria:

- No single Python module above an agreed studio threshold without an exception.
- Gameplay rules remain importable and testable without Flask.
- New card effect can be added with localized Python changes and catalog tests.

### Phase 3 - Frontend Renderer Slimming

Goal: keep browser code as a presentation layer.

Must improve:

- Split `static/js/rebirth.js` into renderer modules without changing gameplay authority:
  - API client
  - state store
  - card renderer
  - battlefield renderer
  - tutorial renderer
  - combat motion
  - input map
- Move UI text decisions that depend on game state into Python payloads when possible.
- Keep `test_rebirth_frontend_contract.py` as the public selector/contract lock.
- Modularize `static/css/rebirth.css` into domain files while preserving the current visual identity.

Exit criteria:

- JS contains no combat, economy or card-effect outcomes.
- Frontend modules are small enough for focused review.
- Visual baseline remains stable after modularization.

### Phase 4 - Content Pipeline And Art Direction

Goal: make the game feel collectible, not only functional.

Must improve:

- Define Season 0 set bible:
  - factions
  - roles
  - rarity promise
  - archetypes
  - card art tone
- Prioritize bespoke art:
  - starter deck cards
  - most-played cards
  - all legendaries
  - campaign boss cards
- Build a Python content validator:
  - card schema
  - deck legality
  - text length
  - rarity distribution
  - art manifest coverage
  - balance metadata
- Add content review checklist before any card ships.

Exit criteria:

- Every first-session card has finished art.
- All legendaries have premium art and unique presentation moments.
- Card text is short, localized and tested in UI containers.

### Phase 5 - Balance From Human Telemetry

Goal: stop balancing only from deterministic lab data.

Must improve:

- Store player cohort and version in telemetry.
- Analyze by:
  - first match
  - tutorial complete/incomplete
  - bot profile
  - deck archetype
  - player level
  - match length
  - cards drawn/played/dead in hand
- Use deterministic lab for regression, not final truth.
- Build weekly balance report from real matches.

Current watchlist:

- Infernus Core and Shadow Reaper are now used but still need live validation.
- Defensive profile is inside target in lab, but longer average turns need human feel data.
- No dominant/low-impact lab flags remain, but that can change with real decks.

Exit criteria:

- 500+ human matches before major balance patch.
- Balance patches include before/after telemetry.
- No balance change ships without rollback version.

### Phase 6 - Retention And Live Loop

Goal: give players a reason to return without fake grind.

Must improve:

- Daily and weekly quests tied to real verbs.
- Card mastery and deck archetype milestones.
- Campaign arcs with boss mechanics.
- Limited-time PvE events before PvP.
- Better profile identity and collection goals.
- Reward economy tuned from retention data.

Exit criteria:

- D1 >= 35% in closed beta.
- D7 >= 20% in closed beta.
- Median returning player plays 3+ matches per active day.
- Feedback volume decreases for the same onboarding issues.

### Phase 7 - Public Beta Production Hardening

Goal: scale from trusted testers to controlled public traffic.

Must improve:

- Durable reconnect for authenticated and guest flows.
- Postgres-only rehydration path or external match cache.
- Load test target for concurrent matches.
- Rate limits beyond auth.
- Admin audit views for economy, feedback, errors and account actions.
- CDN/cache policy for assets.
- Pixel-diff or review workflow for visual baselines.

Exit criteria:

- 100-500 users can play for a week without manual DB fixes.
- Match API p95 stays below target under expected beta load.
- Error rate stays below agreed threshold.
- Backup restore drill repeats successfully before public beta.

### Phase 8 - Async Competitive Layer

Goal: add competition without risking realtime PvP too early.

Recommended order:

- Replay share.
- Ghost deck battles.
- Async rival challenges.
- Weekly boss/ranked PvE ladder.
- Deck sharing.
- Only then realtime PvP.

Why:

- The existing Python deterministic replay is a competitive asset.
- Async competition gives social retention without realtime networking complexity.
- Realtime PvP should wait for reconnect, anti-cheat, abuse handling and live ops maturity.

Exit criteria:

- Replays are deterministic and inspectable.
- Shared links do not leak private account data.
- Async results can be audited server-side.

### Phase 9 - Realtime PvP And Live Ops

Goal: become a real live game.

Must exist before realtime PvP:

- Deterministic server authority.
- Signed command stream.
- Reconnect and timeout policy.
- Abuse/report system.
- Match cancellation/refund policy.
- Observability and alerting.
- Season reset tooling.
- Balance hotfix pipeline.

Exit criteria:

- Solo/async retention proves demand.
- PvP state can be replayed server-side.
- Exploit response has a written runbook.
- Live ops can rollback config without code deploy.

## Production Discipline: AAA Operating Model

Suggested lanes:

- Game Director: owns pillars, player fantasy and release scope.
- Combat Designer: owns rules, cards, archetypes and balance hypotheses.
- Backend/Python Lead: owns engine, replay, persistence, telemetry and ops gates.
- Frontend/UX Lead: owns renderer, interaction clarity, mobile, accessibility and visual baseline.
- Art Director: owns card identity, factions, UI mood and asset acceptance.
- QA/Release Lead: owns regression matrix, E2E, visual QA, release readiness and incident drills.
- Live Ops/Community: owns feedback triage, patch notes, events and player communication.

AAA habit to adopt now:

- Every feature has an owner.
- Every release has a gate.
- Every balance change has a before/after report.
- Every incident has a written timeline.
- Every content addition has a validation script.
- Every player-facing promise is either implemented or removed.

## Highest Priority Improvements

### P0 - Before External Testers

- Complete legal review.
- Complete backup/restore drill.
- Configure Sentry/GlitchTip.
- Run GitHub closed-beta QA green.
- Keep billing off.

### P1 - Before Public Beta

- Modularize `rebirth_persistence.py`, `rebirth.js`, `rebirth.css`, `app.py` and `rebirth_engine.py`.
- Build durable reconnect for guest and authenticated in-progress matches.
- Add real telemetry analysis for D1/D7, first-match completion and balance.
- Finish first-session art and UX polish.
- Move balance/content configuration toward versioned Python data.

### P2 - Before Live Game

- Add content pipeline and art production process.
- Add async competition and replay sharing.
- Add live config, rollback and season tooling.
- Add load testing and rate limits.
- Add community/support operations.

## North Star

Ambitionz Rebirth should feel like a handcrafted tactical card duel where every match is readable, every card has identity, every progression step suggests a smarter deck, and every production decision can be replayed, audited and improved through Python.

The game becomes AAA not by becoming huge. It becomes AAA by becoming precise.

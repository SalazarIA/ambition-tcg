# Ambitionz Rebirth Roadmap

Verified on 2026-06-02 after the external-beta readiness pass, guided-first-match polish, product telemetry pass, versioned visual baseline capture, focused tests, and a fresh 200-match balance simulation.

## Review Of The Attached Analysis

The analysis is directionally useful: Rebirth should move from clarity, to onboarding, to retention, to scalable operations, and the roadmap needs measurable gates. It is also right that compliance, tech debt, DevOps/Ops, and GTM should be explicit phases instead of implicit background work.

The analysis is not accurate as a current state snapshot:

- V0.0/V0 visual fixes are now shipped and tested: desktop nav/auth, result/rematch actions, direct-damage lock copy, card truncation, card proportions, turn CTA, guest empty states, mana/readability, and finite damage aura behavior.
- Current full suite result is `1262 passed, 5 skipped, 19 deselected`, not `1252/1252`.
- The repo already has Python 3.11 pinning, Render config, CI for Rebirth tests, public terms/privacy routes, a data deletion information page, and support export UI/API.
- Compliance is now beta-gated instead of missing: signup captures age/privacy consent, support export/delete remain available, billing is disabled by default, and the external tester gate blocks launch until legal review, backup/restore, error tracking and GitHub QA evidence are present.
- Current balance simulation is healthier than the attached numbers: player win rate is 47.5% over 200 deterministic matches, profile spread is 47.0% to 47.8%, and tier-2 evolution usage is present.
- The remaining balance/content problem moved from catalog coverage to live-telemetry validation: 103/103 cards were used, the 4 previously unused cards now appear in the lab, and no card is currently flagged dominant/low-impact/dead-hand in the deterministic report.
- Current size risk is still real: `services/rebirth_persistence.py` has 3157 lines, `static/css/rebirth.css` has 14270 lines, `static/js/rebirth.js` has 3961 lines, `app.py` has 2195 lines, and `services/rebirth_engine.py` has 2051 lines.

## Verified Baseline

| Area | Current evidence |
| --- | --- |
| Product shell | `/rebirth` desktop nav/auth visible; profile/progression guest states visible |
| Arena UX | result/rematch actions visible; turn CTA prominent; first-turn direct damage explains the lock |
| Focused tests | `82 passed` for product shell, persistence, compliance hardening, frontend contracts and bot/balance contracts |
| E2E tests | `19 passed` for Rebirth navigation/auth/arena coverage |
| Visual QA | PASS, no overflow in arena/shop/collection/campaign/mobile screenshots; baseline committed under `tests/rebirth/visual_baselines/` |
| Full suite | `1262 passed, 5 skipped, 19 deselected` |
| Balance 200 | Player WR 47.5%, Bot WR 51.5%, Avg Turns 15.77 |
| Bot profiles | Defensive 47.8%, Aggressive 47.8%, Opportunist 47.0% player WR |
| Card utilization | 103/103 used, 0/103 unused |
| Dead-hand risk | No broad dead-hand issue in the closed-beta lab; no current dominant/low-impact/dead-hand flags |
| Evolution usage | `card_020`, `card_060`, `card_077`, `card_080`, `card_055` lead the current lab |

## Phase 0 - Stabilized Foundation

Status: done.

Scope:

- Restore visible desktop navigation and auth affordances.
- Keep result/rematch actions accessible without covering the hand during normal play.
- Show visible first-turn direct damage lock copy.
- Make the end-turn button a primary combat action.
- Normalize field/hand card proportions and truncate long card names cleanly.
- Add stronger guest empty states for profile and progression.
- Prevent hit/damage visual state from becoming a permanent aura.

Acceptance:

- Focused route/frontend tests pass.
- E2E navigation/auth tests pass.
- Visual QA screenshots show no obvious overlap or overflow.

## Phase 1 - Compliance Hardening

Status: beta gate implemented; legal review remains before public beta or monetization.

Already present:

- Public terms and privacy pages.
- Data deletion information page.
- Support export UI and `GET /api/rebirth/support/export`.
- Authenticated self-service account deletion via `POST /api/rebirth/support/delete-account`.
- Signup age confirmation and privacy acceptance.
- Render config, Python 3.11 pinning, and Rebirth CI.

Open work:

- Add cookie/privacy consent if analytics, ads, or third-party tracking are enabled.
- Review terms, privacy, refund, billing, and monetization copy before enabling real-money payments.
- Complete an external legal review before public beta.

Acceptance:

- Terms/privacy/deletion/export links are reachable from auth, support, and billing-relevant surfaces.
- Authenticated export and deletion paths are covered by tests.
- No live monetization launch before legal/compliance review.

## Phase 2 - Onboarding And Teachability

Status: closed-beta first pass implemented; in-match guided tutorial and post-match recap added.

Goal: make the first real match understandable without external explanation.

Scope:

- Tutorial steps now cover summon, attack, direct damage lock, ending turn, evolution and the post-match loop inside the first match.
- Finished matches now return a post-match recap explaining the likely win/loss causes and next action.
- Keyword glossary is exposed from `/rebirth/onboarding`.
- Practice goals point players through summon, attack, evolve duplicate, claim daily and open booster.
- Remaining polish: use closed-beta telemetry to shorten or reorder steps that players skip.

Acceptance:

- Tutorial completion at or above 80% in beta telemetry.
- First-match completion at or above 70%.
- Less than 10% of first-match users open help before their first summon.
- No tutorial step blocks a returning player from skipping quickly.

## Phase 3 - Content Utilization And Balance

Status: closed-beta lab gate met; live telemetry validation remains.

Goal: use the 103-card catalog more intentionally.

Scope:

- Seasonal balance decks now rotate through the Season 0 catalog.
- Used-card coverage increased from 40/103 to 103/103 in the deterministic 200-match lab.
- Global player win-rate is 47.5%; profile player WR stays inside 47.0% to 47.8%.
- The 4 previously unused cards now appear in the lab: Aegis Sentinel, Infernus Core, Shadow Reaper and Recarga Arcana.
- Remaining tuning: validate Infernus Core and Shadow Reaper with real player telemetry before buffing them.
- Make tier-2 evolution lines more visible without letting one line dominate.
- Keep player win-rate target near a 44% to 52% ideal band, with a 44% to 53% closed-beta gate across bot profiles.

Acceptance:

- Fresh 200-match report is committed after every balance patch.
- Used-card coverage is at least 60%.
- No card exceeds 30% dead-rate unless intentionally flagged.
- Player win-rate stays between 44% and 53% globally and by profile for closed beta, then tightens toward 44% to 52%.

## Phase 4 - Retention Loop

Status: closed-beta first pass implemented.

Goal: give players a reason to return after the novelty of the first match.

Scope:

- Daily quest panel, retention next-goal copy and beta loop strip are visible in progression.
- Existing rewards expose XP, gold, daily readiness and booster ownership.
- Remaining polish: weekly quests and streak/comeback rewards.
- Deck suggestions now appear after boosters and on profile/progression surfaces based on collection, loadout and recent context.
- Profile history with meaningful match and collection milestones.

Acceptance:

- D1 retention target: at least 35% in beta cohort.
- D7 retention target: at least 20% in beta cohort.
- Median returning user plays at least 3 matches per active day.
- Reward grants are idempotent and covered by persistence tests.

## Phase 5 - Tech Debt And Operations

Status: closed-beta ops lane added; scale hardening and external proof remain.

Goal: reduce product risk before scale.

Scope:

- Split `services/rebirth_persistence.py` into smaller ownership areas.
- Modularize `static/css/rebirth.css` around shell, arena, cards, modals, and responsive rules.
- Keep route/API ownership documented and tested.
- Scheduled closed-beta QA workflow added for dependency audit, tests, E2E, visual screenshots and balance report.
- Closed-beta runbook added for entry gate, tester loop, metrics, operational checks and incident response.
- Error tracking initialization is wired for Sentry, GlitchTip or a compatible DSN; production still needs `SENTRY_DSN`.
- External gate script checks legal review, backup/restore drill, error tracking, GitHub QA and Stripe-off status.
- Visual screenshot baselines are now versioned under `tests/rebirth/visual_baselines/`.
- Add dependency/security checks such as `pip-audit` or equivalent.

Acceptance:

- Persistence and CSS modules have clear boundaries and focused tests.
- CI keeps a fast lane and a scheduled full QA lane.
- Production errors are observable.
- Backup restore is tested before public beta.

## Phase 6 - MVP Beta

Status: closed-beta entry package produced; final invite decision depends on external ops/legal checks.

Goal: controlled public learning without pretending the game is finished.

Scope:

- Invite-only or small public beta.
- Instrument onboarding, match completion, balance, retention, errors, and economy events.
- Keep monetization disabled or sandboxed unless compliance and operations gates are complete.
- Beta feedback capture is wired from Support with release version, account context and optional last match.

Acceptance:

- 100 beta users can play within one week without manual data fixes.
- Match API p95 stays below 300ms under expected beta load.
- Error rate stays below agreed threshold for beta sessions.
- Feedback can be traced to version, account state, and recent match context.

## Phase 7 - GTM And Community

Goal: make the game legible outside the dev bubble.

Scope:

- Landing page that shows the actual product and core fantasy quickly.
- Short gameplay trailer or capture reel.
- Press kit with logo, screenshots, core description, and contact.
- Discord/community entry point.
- Creator outreach and referral loop only after onboarding is stable.

Acceptance:

- Landing page conversion and waitlist/join metrics are tracked.
- Public screenshots match the current product.
- Community moderation and support expectations are documented.

## Phase 8 - Social And Competitive

Goal: add social proof after the solo loop has signal.

Scope:

- Replay or match-share links.
- Weekly boss/event format.
- Deck sharing.
- Lightweight tournaments or leaderboard seasons.

Acceptance:

- Social surfaces do not expose private account data.
- Shared match/deck links are stable and reversible if moderation requires removal.
- Competitive rewards do not break the economy.

## Phase 9 - PvP V2

Goal: add real PvP only after solo retention and operations are proven.

Scope:

- Deterministic state contract for PvP.
- Anti-cheat and replay/audit logs.
- Matchmaking and disconnect handling.
- Live or async PvP decision after retention data.

Acceptance:

- Solo beta metrics justify multiplayer investment.
- PvP state can be replayed deterministically server-side.
- Disconnect and abuse cases have product decisions before launch.

## Immediate Order

1. Complete legal/privacy copy review, Render/Postgres backup-restore proof, `SENTRY_DSN` and a green GitHub `rebirth-closed-beta-qa` run.
2. Invite a tiny closed-beta cohort only after the external gate is green.
3. Watch D1/D7, first-match completion, tutorial completion, client errors, feedback and balance telemetry daily from `/rebirth/release`.
4. Validate Infernus Core, Shadow Reaper and defensive pacing with human matches before changing card text again.
5. Pay down persistence/CSS/JS modularization before public beta.
6. Harden durable reconnect for guest and in-progress match cases.
7. Run MVP beta and GTM.
8. Add social systems.
9. Delay PvP until solo retention proves the game deserves that complexity.

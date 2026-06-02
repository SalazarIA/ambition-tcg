# Ambitionz Rebirth Roadmap

Verified on 2026-06-01 after the V0.0 stabilization pass, V0 visual polish pass, focused E2E runs, visual QA, full test suite, and a fresh 200-match balance simulation.

## Review Of The Attached Analysis

The analysis is directionally useful: Rebirth should move from clarity, to onboarding, to retention, to scalable operations, and the roadmap needs measurable gates. It is also right that compliance, tech debt, DevOps/Ops, and GTM should be explicit phases instead of implicit background work.

The analysis is not accurate as a current state snapshot:

- V0.0/V0 visual fixes are now shipped and tested: desktop nav/auth, result/rematch actions, direct-damage lock copy, card truncation, card proportions, turn CTA, guest empty states, mana/readability, and finite damage aura behavior.
- Current full suite result is `1256 passed, 5 skipped, 19 deselected`, not `1252/1252`.
- The repo already has Python 3.11 pinning, Render config, CI for Rebirth tests, public terms/privacy routes, a data deletion information page, and support export UI/API.
- Compliance still has real gaps: account deletion is not yet a complete tested product flow, legal copy needs review before monetization, and signup/billing need clearer consent/age/privacy handling.
- Current balance simulation is healthier than the attached numbers: player win rate is 46.5% over 200 deterministic matches, profile spread is 44.8% to 48.5%, and tier-2 evolution usage is present.
- The remaining balance/content problem is utilization, not a global spell failure: 40/103 cards were used, 63/103 were unused, only 2 cards had dead-rate above 30%, and no support/spell/trap exceeded 30% dead-rate in the latest run.
- Current size risk is still real: `services/rebirth_persistence.py` has 3104 lines and `static/css/rebirth.css` has 14217 lines.

## Verified Baseline

| Area | Current evidence |
| --- | --- |
| Product shell | `/rebirth` desktop nav/auth visible; profile/progression guest states visible |
| Arena UX | result/rematch actions visible; turn CTA prominent; first-turn direct damage explains the lock |
| Focused tests | `37 passed` for frontend contract, shell, and routes |
| E2E tests | `19 passed` for Rebirth navigation/auth/arena coverage |
| Visual QA | PASS, no detected overflow in desktop arena/profile/progression screenshots |
| Full suite | `1256 passed, 5 skipped, 19 deselected` |
| Balance 200 | Player WR 46.5%, Bot WR 51.0%, Avg Turns 18.77 |
| Bot profiles | Defensive 44.8%, Aggressive 46.3%, Opportunist 48.5% player WR |
| Card utilization | 40/103 used, 63/103 unused |
| Dead-hand risk | 2 cards above 30%; supports/spells/traps max at 25% |
| Evolution usage | `card_011`, `card_071`, `card_053`, `card_072`, `card_033` recorded |

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

Status: next pre-public gate.

Already present:

- Public terms and privacy pages.
- Data deletion information page.
- Support export UI and `GET /api/rebirth/support/export`.
- Render config, Python 3.11 pinning, and Rebirth CI.

Open work:

- Add a complete authenticated account data deletion flow or a clearly tracked manual deletion request path with tests.
- Add account export/deletion coverage that verifies real persisted Rebirth data, not only page availability.
- Add age confirmation and consent language to signup/account surfaces.
- Add cookie/privacy consent if analytics, ads, or third-party tracking are enabled.
- Review terms, privacy, refund, billing, and monetization copy before enabling real-money payments.

Acceptance:

- Terms/privacy/deletion/export links are reachable from auth, support, and billing-relevant surfaces.
- Authenticated export and deletion paths are covered by tests.
- No live monetization launch before legal/compliance review.

## Phase 2 - Onboarding And Teachability

Goal: make the first real match understandable without external explanation.

Scope:

- First-match tutorial for summon, mana, guard, attack, direct damage lock, spells/traps, evolution, and win/loss.
- Lightweight keyword glossary available from card detail and match UI.
- Post-match recap that explains why the player won or lost.
- Guided first reward/deck edit flow.

Acceptance:

- Tutorial completion at or above 60% in beta telemetry.
- First-match completion at or above 70%.
- Less than 10% of first-match users open help before their first summon.
- No tutorial step blocks a returning player from skipping quickly.

## Phase 3 - Content Utilization And Balance

Goal: use the 103-card catalog more intentionally.

Scope:

- Investigate the 63 unused cards from the latest 200-match report.
- Distinguish cards missing from pools/rewards from cards that are technically playable but strategically bad.
- Raise used-card coverage from 38.8% to at least 60% in deterministic balance simulation.
- Reduce cards above 30% dead-rate to zero.
- Make tier-2 evolution lines more visible without letting one line dominate.
- Keep player win-rate target inside a 44% to 52% band across bot profiles.

Acceptance:

- Fresh 200-match report is committed after every balance patch.
- Used-card coverage is at least 60%.
- No card exceeds 30% dead-rate unless intentionally flagged.
- Player win-rate stays between 44% and 52% globally and by profile.

## Phase 4 - Retention Loop

Goal: give players a reason to return after the novelty of the first match.

Scope:

- Daily and weekly quests.
- Streak and comeback rewards that do not punish missed days too harshly.
- Post-match reward panel with clear XP, gold, unlock, and next-goal progress.
- Deck suggestions based on recently used cards and missing curve pieces.
- Profile history with meaningful match and collection milestones.

Acceptance:

- D1 retention target: at least 40% in beta cohort.
- D7 retention target: at least 20% in beta cohort.
- Median returning user plays at least 3 matches per active day.
- Reward grants are idempotent and covered by persistence tests.

## Phase 5 - Tech Debt And Operations

Goal: reduce product risk before scale.

Scope:

- Split `services/rebirth_persistence.py` into smaller ownership areas.
- Modularize `static/css/rebirth.css` around shell, arena, cards, modals, and responsive rules.
- Keep route/API ownership documented and tested.
- Add a scheduled E2E/visual QA lane, separate from fast PR tests.
- Add error reporting such as Sentry or GlitchTip.
- Add DB backup, restore drill, and operational runbook.
- Add dependency/security checks such as `pip-audit` or equivalent.

Acceptance:

- Persistence and CSS modules have clear boundaries and focused tests.
- CI keeps a fast lane and a scheduled full QA lane.
- Production errors are observable.
- Backup restore is tested before public beta.

## Phase 6 - MVP Beta

Goal: controlled public learning without pretending the game is finished.

Scope:

- Invite-only or small public beta.
- Instrument onboarding, match completion, balance, retention, errors, and economy events.
- Keep monetization disabled or sandboxed unless compliance and operations gates are complete.
- Add beta feedback capture from support/profile surfaces.

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

1. Close compliance gaps for export/deletion/consent/legal review.
2. Build onboarding and first-match teachability.
3. Improve content utilization and balance using fresh reports.
4. Add retention quests, rewards, and profile history.
5. Pay down persistence/CSS/ops risk.
6. Run MVP beta and GTM.
7. Add social systems.
8. Delay PvP until solo retention proves the game deserves that complexity.

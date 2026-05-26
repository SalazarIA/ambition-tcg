# Gameplay Gap Analysis / Game Feel Review / UX Playtest

- Generated: 2026-05-26 12:26:55
- Target: `http://127.0.0.1:8097/rebirth`
- Scope: active Rebirth arena first-match flow, desktop 1280x720, mobile 390x844, deterministic gameplay health

## Verification

- `python3 tools/qa/qa_rebirth_smoke.py`: PASS
- `python3 -m pytest tests/rebirth/test_user_journey_e2e.py tests/rebirth/test_rebirth_frontend_contract.py -q`: 8 passed
- `python3 -m pytest tests/rebirth/e2e/test_navigation_and_auth.py -q -m e2e`: 19 passed, 1 skipped
- `python3 tools/rebirth_gameplay_health.py 120`: flags `match_duration_high`, `chain_readability_risk`

## Evidence

- Screenshots: `reports/qa/playtest_assets/20260526_122655/`
- Gameplay health sample: 120 deterministic matches
- Desktop first hand: selected `CINDER LYNX`, recommended `ASHEN BRAWLER`
- Desktop combat result: `Cinder Lynx` attacks `Granite Pactbearer`, player drops to 28 HP, result is `Seu ataque foi contido.`
- Mobile first viewport: body class `rb-mobile-native`, board height about 1534px, action buttons are 64px tall, but hand/actions sit below the first viewport

## Findings

### P1 - Coaching and default action disagree

What the player sees: the hand marks `ASHEN BRAWLER` as `Best`, while `CINDER LYNX` is selected and the primary CTA is ready to `INVOCAR 1`.

Why it matters: the game is teaching the player two different recommendations at once. A new player will often press the CTA, trust that it is the recommended action, then immediately learn a different card was considered best.

Likely owner: `static/js/rebirth.js`. `RebirthStore.setState()` defaults to `state.player.hand[0]`, while `RebirthTactics.recommendedCard()` scores independently.

Recommendation: either auto-select the recommended/evolution card, or make the recommendation panel explicitly say "Best card is Ashen Brawler, selected card is Cinder Lynx." The cleaner game-feel move is to align default selection with the strongest recommendation unless the evolution tutorial intentionally overrides it.

### P1 - Mobile first viewport delays the first real action

What the player sees: on 390x844 mobile, the top nav, HUD and battlefield fill the first screen. The actual hand and action buttons require scrolling.

Why it matters: mobile first-time play should reveal the verb quickly. Right now the first visible screen explains the board, but the thing the player can actually do is below the fold.

Likely owner: `static/css/rebirth.css` mobile layout and `templates/rebirth.html` nav/action placement.

Recommendation: add a sticky mobile action tray for selected card + primary CTA, or collapse the global nav into a shorter mobile header while in the arena. The player should see "selected card + invoke/evolve/end turn" without scrolling.

### P2 - Primary CTA helper text is stale across modes

What the player sees: after summoning, the primary button becomes `ATACAR`, but the helper still says `Gaste mana para jogar`. After combat resolves, the disabled primary button can read `JOGAR` with the same helper, while the real next action is `PRÓXIMO TURNO`.

Why it matters: buttons change state, but the microcopy underneath keeps describing a different verb. That creates a small but constant friction in the main loop.

Likely owner: `templates/rebirth.html` hardcodes the primary helper; `static/js/rebirth.js` updates only the secondary helper.

Recommendation: give the primary helper an id and update it alongside `#play-button`: "Gaste mana para invocar", "Escolha um alvo", "Resolvido - avance o turno", "Sem mana suficiente", etc.

### P2 - Clash preview does not prevent obvious bad attacks

What the player sees: the tactical strip describes roles and hidden hand pressure, but it does not warn that `Cinder Lynx` into `Granite Pactbearer` is likely a bad clash. The player learns only after losing the unit and 2 HP.

Why it matters: Rebirth is a tactical game, but first-session learning should make risk legible before the irreversible click.

Likely owner: tactical read layer in `static/js/rebirth.js` plus engine-facing public state from `services/rebirth_serializers.py`.

Recommendation: when an attacker and defender are selected, show a compact predicted outcome: "Risky: 4 ATK into 2 GUARD + Baluarte. Likely unit loss." It does not need perfect math; it needs to teach matchup reading.

### P2 - Combat/result density is high

What the player sees: the arena gives strong hit feedback and the result headline is clear, but the supporting text, chain id, tactical strip and log compete for attention. The deterministic health check also flagged `max_chain_events: 15`.

Why it matters: the game can be mechanically correct while still feeling noisy. Dense event chains are where players stop understanding cause and effect.

Likely owner: result panel, turn log, and event rendering in `static/js/rebirth.js`.

Recommendation: keep the headline and HP delta as the primary read, then collapse chain metadata behind a detail affordance. Show only the last 1-3 causal events inline.

## What Feels Good

- The core flow boots cleanly, with no console errors in the tested pass.
- The arena framing, side colors, HP bars and card positions make ownership clear.
- Summon -> bot response -> attack -> result is functionally playable and visually coherent.
- The result headline `Seu ataque foi contido.` is a good high-level summary before the detailed log.

## Priority Fix Order

1. Align default selection with the recommended card or explain the mismatch.
2. Make the mobile primary action visible without scrolling.
3. Add dynamic helper copy under the primary CTA.
4. Add a lightweight clash-risk preview.
5. Reduce inline chain/log density during combat results.

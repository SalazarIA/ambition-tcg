# Ambitionz RC V6 Release Notes

RC V6 focuses on making the battle loop more real, more teachable and easier to validate in production.

## Highlights

- Arena V6 polish keeps the compact HUD, readable board rows, hand/action flow and Combat Explanation V2 from the recent hotfix.
- Spell/Trap Backend Contract V1 adds an additive payload for `card_type`, target fields, cast mode and prepared traps while preserving legacy `card_id`/`lane` payloads.
- Spell Resolver V1 gives spells minimum real effects: damage, heal, shield and Ambition gain.
- Trap Resolver V1 adds prepared trap state, trigger checks and consumed trap flow.
- Intent Balance V2 makes Strike leaner, Guard more protective and Focus more visibly useful.
- Starter Deck Teaching Pass keeps the beta deck at 30 cards with 21 creatures, 6 spells and 3 traps.
- Card Identity Pack V1 annotates the 30 starter cards with role, simple use text, short lore and stronger art prompts.
- Collection and Deck Builder Teaching UX expose role, how-to-use text and deck scores.
- Production Smoke/Cache Guard now supports env-configured production URL and expected service worker version.

## Main Files

- `services/battle_engine_v2.py`
- `services/card_effect_resolver.py`
- `services/battle_engine_v2_adapter.py`
- `services/match_engine_facade.py`
- `services/arena_command_v1.py`
- `static/js/arena_clean_v48.js`
- `static/js/arena_renderer_adapter.js`
- `static/js/card_art_manifest.js`
- `static/assets/cards/card_art_manifest.json`
- `templates/collection.html`
- `templates/deck_builder.html`
- `tools/qa/qa_production_smoke.py`
- `tools/qa/card_art_manifest_check.py`
- `tools/qa/battle_balance_sim.py`

## Known Issues

- Spell and trap behavior is intentionally V1. Multi-step effects, draw effects and advanced targeting should remain conservative until more telemetry exists.
- Final card art is not included; the manifest/fallback system is the canonical placeholder layer.
- Balance watchlist may include historical telemetry from earlier builds. Confirm post-deploy behavior before declaring Strike usage fixed.
- Production smoke can warn when Render has not yet deployed the latest service worker.

## QA Gate

RC V6 requires py_compile, pytest, backend QA, Arena matrix, playability audit, 100-match and 500-match battle simulations, battle gauntlet, browser QA, balance watchlist, card art manifest check, production smoke, node checks, `git diff --check`, status review and untracked-file review.


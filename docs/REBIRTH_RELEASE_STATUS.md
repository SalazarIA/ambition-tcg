# Rebirth Release Status

## Checklist

- [x] Block 141 docs
- [x] Block 142 services
- [x] Block 143 route
- [x] Block 144 frontend template
- [x] Block 145 premium CSS
- [x] Block 146 frontend JS
- [x] Block 147 3D adapter
- [x] Block 148 tests
- [x] Block 149 QA smoke
- [x] Block 150 service worker/cache
- [x] Block 151 validation
- [x] Block 152 final status
- [x] Block 153 browser contract QA
- [x] Block 154 premium product shell
- [x] Block 155 cinematic CSS hardening
- [x] Block 156 frontend UX hardening
- [x] Block 157 advanced 3D placeholder adapter
- [x] Block 158 engine game feel V1
- [x] Block 159 embedded onboarding
- [x] Block 160 premium end states
- [x] Block 161 home bridge to Rebirth
- [x] Block 162 product migration docs
- [x] Block 163 frontend contract tests
- [x] Block 164 expanded engine tests
- [x] Block 165 QA smoke V2
- [x] Block 166 service worker cache bump
- [x] Block 167 release status update
- [x] Block 171 legacy cleanup map
- [x] Block 172 Rebirth-first home
- [x] Block 173 Rebirth deck selection backend
- [x] Block 174 Rebirth deck APIs
- [x] Block 175 deck selection UI
- [x] Block 176 difficulty V1
- [x] Block 177 bot personalities V1
- [x] Block 178 match summary V1
- [x] Block 179 reward mock V1
- [x] Block 180 premium card detail
- [x] Block 181 quick duel mode
- [x] Block 182 legacy nav lowered
- [x] Block 183 route promotion plan
- [x] Block 184 home and legacy cleanup tests
- [x] Block 185 productization QA
- [x] Block 186 service worker cache bump
- [x] Block 187 docs status

## Files Created

- `tests/test_rebirth_frontend_contract.py`
- `tests/test_rebirth_home_promotion.py`
- `tests/test_legacy_rebirth_bridge.py`
- `tools/qa/qa_rebirth_browser_contract.py`
- `tools/qa/qa_rebirth_productization.py`
- `services/rebirth/rebirth_decks.py`
- `docs/LEGACY_CLEANUP_MAP.md`
- `docs/REBIRTH_ALPHA_ROADMAP.md`
- `templates/_legacy_rebirth_banner.html`

## Files Changed

- `docs/REBIRTH_PRODUCT_RESET.md`
- `docs/REBIRTH_ARCHITECTURE.md`
- `docs/REBIRTH_GAMEPLAY_CORE.md`
- `docs/REBIRTH_UI_CONTRACT.md`
- `docs/REBIRTH_3D_MODEL_CONTRACT.md`
- `docs/REBIRTH_RELEASE_STATUS.md`
- `docs/LEGACY_CLEANUP_MAP.md`
- `docs/REBIRTH_ALPHA_ROADMAP.md`
- `services/rebirth/rebirth_cards.py`
- `services/rebirth/rebirth_decks.py`
- `services/rebirth/rebirth_state.py`
- `services/rebirth/rebirth_engine.py`
- `services/rebirth/rebirth_payloads.py`
- `templates/rebirth.html`
- `templates/index.html`
- `templates/_legacy_rebirth_banner.html`
- `templates/arena.html`
- `templates/arena_ascension.html`
- `templates/collection.html`
- `templates/deck_builder.html`
- `templates/shop.html`
- `templates/roadmap.html`
- `static/css/rebirth.css`
- `static/css/ambitionz_ascension.css`
- `static/css/style.css`
- `static/css/arena_clean_v48.css`
- `static/js/rebirth.js`
- `static/js/rebirth_3d_adapter.js`
- `static/js/service-worker.js`
- `static/assets/rebirth3d/manifest.json`
- `tests/test_rebirth_engine.py`
- `tests/test_rebirth_payload_contract.py`
- `tests/test_rebirth_routes.py`
- `tests/test_rebirth_home_promotion.py`
- `tests/test_legacy_rebirth_bridge.py`
- `tests/test_ascension_visual_architecture.py`
- `tests/test_ascension_taxonomy_routes.py`
- `tests/test_frontend_structure.py`
- `tests/test_release_candidate_smoke.py`
- `tests/test_ascension_frontend_structure.py`
- `tools/qa/qa_rebirth_smoke.py`
- `tools/qa/qa_rebirth_browser_contract.py`
- `tools/qa/qa_rebirth_productization.py`
- `tools/qa/qa_ascension_viewport_contract.py`
- `tools/qa/qa_ascension_frontend_contract.py`
- `tools/qa/qa_ascension_product_surface.py`
- `docs/RC_V8_1_VISUAL_ARCHITECTURE_STATUS.md`
- `docs/ASCENSION_MIGRATION_REPORT.md`

## Routes

- `GET /rebirth`
- `GET /api/rebirth/decks`
- `GET /api/rebirth/decks/<deck_id>`
- `GET /api/rebirth/new`
- `POST /api/rebirth/intent`
- `POST /api/rebirth/play-card`
- `POST /api/rebirth/resolve`
- `POST /api/rebirth/restart`

Legacy routes remain intact, including `/training-legacy` and `/arena`.

## Current Product Notes

- `/rebirth` now presents a premium product shell with topbar, hero, pillars, decision panel, compact log, embedded onboarding and winner state.
- Home is now Rebirth-first with Legacy Access grouped below the main product CTA.
- Rebirth has starter deck archetypes: Ember Oath, Deepguard and Null Circuit.
- Rebirth supports Easy, Normal and Hard difficulty.
- Rival profiles now include The Warden, The Duelist and The Oracle.
- Finished matches expose `match_summary` and `reward_preview`.
- Card detail now requires explicit activation instead of accidental hand-card play.
- Quick Duel starts the default deck on Normal.
- Legacy beta surfaces now show a Rebirth migration banner where safe.
- Rebirth gameplay remains one active card per side.
- HP starts at 32.
- STRIKE adds 2 pressure, GUARD absorbs 3 pressure, FOCUS grants 2 Ambition and adds 1 pressure when Ambition reaches 6.
- Starter damage is capped at 10.
- The frontend uses fetch only, not Socket.IO.
- The 3D adapter remains DOM-based but now owns scene depth, arena orbit, energy core, avatar nodes, active card frame, FX ring and particles.
- The home page now includes a clear Rebirth bridge while preserving Ascension and legacy fallback routes.

## Validation

- `python3 -m py_compile app.py services/rebirth/__init__.py services/rebirth/rebirth_cards.py services/rebirth/rebirth_decks.py services/rebirth/rebirth_state.py services/rebirth/rebirth_engine.py services/rebirth/rebirth_payloads.py tools/qa/qa_rebirth_smoke.py tools/qa/qa_rebirth_browser_contract.py tools/qa/qa_rebirth_productization.py`
- `python3 -m pytest -q tests/test_rebirth_engine.py tests/test_rebirth_payload_contract.py tests/test_rebirth_routes.py tests/test_rebirth_frontend_contract.py tests/test_rebirth_home_promotion.py tests/test_legacy_rebirth_bridge.py`
- `python3 tools/qa/qa_rebirth_smoke.py`
- `python3 tools/qa/qa_rebirth_browser_contract.py`
- `python3 tools/qa/qa_rebirth_productization.py`
- `node --check static/js/rebirth.js`
- `node --check static/js/rebirth_3d_adapter.js`
- `python3 -m pytest -q`

Current result: targeted Rebirth productization tests pass with `32 passed, 1 warning`; smoke prints `REBIRTH_SMOKE_V2_OK`; browser contract prints `REBIRTH_BROWSER_CONTRACT_OK`; productization QA prints `REBIRTH_PRODUCTIZATION_OK`; JS checks pass; full suite passes with `242 passed, 1 warning`.

## Pending

- Three.js/GLB arena implementation is not built yet.
- Real multiplayer is not implemented yet.
- Database persistence for Rebirth match history is not implemented yet.
- Manual visual QA on physical mobile devices is still recommended.

## Next Recommended Blocks

- Build the first real Three.js arena behind `Rebirth3D`.
- Add Rebirth balance simulations and card tuning.
- Add Rebirth match persistence after the state contract stabilizes.
- Add screenshot-based desktop/mobile visual QA for `/rebirth`.

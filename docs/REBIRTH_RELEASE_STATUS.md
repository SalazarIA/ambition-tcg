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

## Files Created

- `tests/test_rebirth_frontend_contract.py`
- `tools/qa/qa_rebirth_browser_contract.py`

## Files Changed

- `docs/REBIRTH_PRODUCT_RESET.md`
- `docs/REBIRTH_ARCHITECTURE.md`
- `docs/REBIRTH_GAMEPLAY_CORE.md`
- `docs/REBIRTH_UI_CONTRACT.md`
- `docs/REBIRTH_3D_MODEL_CONTRACT.md`
- `docs/REBIRTH_RELEASE_STATUS.md`
- `services/rebirth/rebirth_state.py`
- `services/rebirth/rebirth_engine.py`
- `services/rebirth/rebirth_payloads.py`
- `templates/rebirth.html`
- `templates/index.html`
- `static/css/rebirth.css`
- `static/css/ambitionz_ascension.css`
- `static/js/rebirth.js`
- `static/js/rebirth_3d_adapter.js`
- `static/js/service-worker.js`
- `static/assets/rebirth3d/manifest.json`
- `tests/test_rebirth_engine.py`
- `tests/test_rebirth_payload_contract.py`
- `tests/test_rebirth_routes.py`
- `tests/test_ascension_visual_architecture.py`
- `tests/test_ascension_taxonomy_routes.py`
- `tests/test_frontend_structure.py`
- `tests/test_release_candidate_smoke.py`
- `tests/test_ascension_frontend_structure.py`
- `tools/qa/qa_rebirth_smoke.py`
- `tools/qa/qa_ascension_viewport_contract.py`
- `tools/qa/qa_ascension_frontend_contract.py`
- `tools/qa/qa_ascension_product_surface.py`
- `docs/RC_V8_1_VISUAL_ARCHITECTURE_STATUS.md`
- `docs/ASCENSION_MIGRATION_REPORT.md`

## Routes

- `GET /rebirth`
- `GET /api/rebirth/new`
- `POST /api/rebirth/intent`
- `POST /api/rebirth/play-card`
- `POST /api/rebirth/resolve`
- `POST /api/rebirth/restart`

Legacy routes remain intact, including `/training-legacy` and `/arena`.

## Current Product Notes

- `/rebirth` now presents a premium product shell with topbar, hero, pillars, decision panel, compact log, embedded onboarding and winner state.
- Rebirth gameplay remains one active card per side.
- HP starts at 32.
- STRIKE adds 2 pressure, GUARD absorbs 3 pressure, FOCUS grants 2 Ambition and adds 1 pressure when Ambition reaches 6.
- Starter damage is capped at 10.
- The frontend uses fetch only, not Socket.IO.
- The 3D adapter remains DOM-based but now owns scene depth, arena orbit, energy core, avatar nodes, active card frame, FX ring and particles.
- The home page now includes a clear Rebirth bridge while preserving Ascension and legacy fallback routes.

## Validation

- `python3 -m py_compile app.py services/rebirth/__init__.py services/rebirth/rebirth_cards.py services/rebirth/rebirth_state.py services/rebirth/rebirth_engine.py services/rebirth/rebirth_payloads.py tools/qa/qa_rebirth_smoke.py tools/qa/qa_rebirth_browser_contract.py`
- `python3 -m pytest -q tests/test_rebirth_engine.py tests/test_rebirth_payload_contract.py tests/test_rebirth_routes.py tests/test_rebirth_frontend_contract.py`
- `python3 tools/qa/qa_rebirth_smoke.py`
- `python3 tools/qa/qa_rebirth_browser_contract.py`
- `node --check static/js/rebirth.js`
- `node --check static/js/rebirth_3d_adapter.js`
- `python3 -m pytest -q`

Current result: targeted Rebirth tests pass with `24 passed, 1 warning`; smoke prints `REBIRTH_SMOKE_V2_OK`; browser contract prints `REBIRTH_BROWSER_CONTRACT_OK`; full suite passes with `234 passed, 1 warning`.

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

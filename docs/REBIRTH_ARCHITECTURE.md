# Rebirth Architecture

Ambitionz Rebirth is an isolated product slice inside the existing repo. It does not delete or replace the old Arena, BE2, Ascension Duel or economy systems.

## Canonical File Structure

```text
services/rebirth/
    __init__.py
    rebirth_state.py
    rebirth_engine.py
    rebirth_payloads.py
    rebirth_cards.py

templates/rebirth.html

static/css/rebirth.css
static/js/rebirth.js
static/js/rebirth_3d_adapter.js
static/assets/rebirth3d/manifest.json

tests/test_rebirth_engine.py
tests/test_rebirth_routes.py
tests/test_rebirth_payload_contract.py
tests/test_rebirth_frontend_contract.py

tools/qa/qa_rebirth_smoke.py
tools/qa/qa_rebirth_browser_contract.py
```

## Boundaries

- `rebirth_cards.py` owns the initial premium card catalog.
- `rebirth_state.py` owns serializable match and player state.
- `rebirth_engine.py` owns deterministic gameplay rules and bot decisions.
- `rebirth_payloads.py` owns the public frontend contract and hides decks.
- `rebirth.html`, `rebirth.css`, `rebirth.js` own the DOM product surface.
- `rebirth_3d_adapter.js` owns the bridge to the future 3D scene.

## Runtime Policy

The simulation is the source of truth. The DOM UI and 3D adapter are renderers. Future Three.js or GLB work should plug into the adapter without moving gameplay rules into the renderer.

## Migration Rule

Rebirth is now the preferred path for new product gameplay work. Legacy Arena, BE2 and Ascension routes remain intact, but they are compatibility surfaces unless a task explicitly targets them.

## Product Migration Phases

- Phase 1: parallel prototype under `/rebirth`.
- Phase 2: playable alpha with hardened engine events, onboarding, premium shell and browser QA.
- Phase 3: public home promotion once manual visual QA and balance tuning are complete.
- Phase 4: legacy retirement after the Rebirth contract replaces the old public loop.

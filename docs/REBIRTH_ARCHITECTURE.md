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

tools/qa/qa_rebirth_smoke.py
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

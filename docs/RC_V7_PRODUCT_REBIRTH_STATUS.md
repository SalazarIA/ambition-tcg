# RC V7 Product Rebirth Status

## Completed Changes

- `/training` now renders the Ascension Duel experience.
- `/training-legacy` preserves the old lane-based Arena.
- New Ascension services were added.
- New Ascension frontend template, CSS and JS were added.
- Ascension APIs were added under `/api/ascension/*`.
- Service worker cache moved to `ambitionz-web-app-v193`.

## Old Main Experience Retired

The old Arena is no longer the default Training route. It remains reachable as legacy fallback.

## New Main Experience Route

- `/training`

## Legacy Route

- `/training-legacy`

## Known Limitations

- Collection and deck builder still expose old card taxonomy in several places.
- Ascension progression currently records a compatibility event but does not yet award a full new rewards package.
- No Socket.IO Ascension layer is active; fetch JSON is the stable first public contract.

## QA Commands

- `python3 -m pytest -q`
- `python3 -m py_compile services/ascension_cards.py services/ascension_engine.py services/ascension_bot.py services/ascension_payloads.py services/ascension_progression.py`
- `node --check static/js/ambitionz_ascension.js`
- `python3 tools/qa/qa_ascension_engine.py`
- `python3 tools/qa/qa_ascension_full_match.py`
- `python3 tools/qa/qa_ascension_routes.py`
- `python3 tools/qa/qa_ascension_frontend_contract.py`
- `python3 tools/qa/qa_product_rebirth_report.py`

## Manual Test Checklist

- Open `/training`.
- Confirm the Duel Altar appears without legacy lanes.
- Start a duel.
- Summon a Champion.
- Choose an Intent.
- Commit a round.
- Confirm the Chronicle updates.
- Open `/training-legacy`.
- Confirm the old Arena still loads for fallback.

# RC V8 Ascension Status

## Executive Summary

RC V8 completes the public migration layer around Ascension Duel. The main product route is now one-Champion, Ambition Core-led, and supported by Ascension-native collection, deck, rewards, history, balance and onboarding surfaces.

## Current Architecture

- `/training` is Ascension Duel.
- `/training-legacy` preserves the retired Arena.
- `/collection-ascension` is the new card library.
- `/deck-builder-ascension` is the new deck builder.
- `/ascension-history` reads defensive JSONL match records.
- `/api/ascension/*` is the fetch JSON combat contract.

## QA

Run:

- `python3 -m pytest -q`
- `python3 tools/qa/qa_ascension_release_matrix.py`

## Risks

- Legacy economy, collection inventory and deck persistence still exist beside Ascension-native surfaces.
- Ascension history uses JSONL fallback instead of a database migration.
- Real card art is intentionally deferred.

## Recommended Next Blocks

- Persist Ascension deck choices per user.
- Promote Ascension rewards into the main reward ledger.
- Add authored Champion portrait assets.
- Add accessibility QA with screenshots across mobile sizes.

## Main Files

- `services/ascension_cards.py`
- `services/ascension_engine.py`
- `services/ascension_bot.py`
- `services/ascension_progression.py`
- `services/ascension_history.py`
- `templates/arena_ascension.html`
- `templates/collection_ascension.html`
- `templates/deck_builder_ascension.html`
- `static/css/ambitionz_ascension.css`
- `static/js/ambitionz_ascension.js`

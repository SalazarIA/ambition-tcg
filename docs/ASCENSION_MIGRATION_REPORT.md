# Ascension Migration Report

## New Files

- `services/ascension_cards.py`
- `services/ascension_engine.py`
- `services/ascension_bot.py`
- `services/ascension_payloads.py`
- `services/ascension_progression.py`
- `templates/arena_ascension.html`
- `static/css/ambitionz_ascension.css`
- `static/js/ambitionz_ascension.js`
- Ascension tests under `tests/`
- Ascension QA tools under `tools/qa/`

## Changed Files

- `app.py`
- `templates/index.html`
- `static/js/service-worker.js`

## Canonical Now

- Ascension Duel combat engine.
- Ascension card catalog and starter deck.
- Ambition Core.
- Mind Clash.
- One active Champion per side.
- Public JSON payloads from `services/ascension_payloads.py`.

## Still Legacy

- BE2.
- Old Arena sockets.
- Old Training renderer under `/training-legacy`.
- Old card taxonomy in collection and deck builder.
- Existing match history and reward logic built around BE2.

## Next Blocks Needed

- Migrate collection and deck builder taxonomy.
- Add Ascension reward payouts.
- Add match history rows for Ascension Duel.
- Tune card balance with larger simulations.
- Add optional art pipeline for Champion portraits.

## RC V8 Closing Notes

- Ascension-native Collection is available at `/collection-ascension`.
- Ascension-native Deck Builder is available at `/deck-builder-ascension`.
- Ascension Chronicle is available at `/ascension-history`.
- Post-match Ascension rewards now return XP, Gold, Champion progress, unlock progress and summary text.
- Match history uses defensive JSONL fallback while legacy database systems remain untouched.
- Bot profiles now include Aggressor, Controller, Opportunist, Defensive and Ascender.
- Art pipeline folders and manifest are present without external assets.

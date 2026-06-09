# Rebirth Phase 1 Report - First 10 Minutes Experience

Updated: 2026-06-08

## Status

Phase 1 received a local implementation pass, but cannot be closed as complete
until Phase 0 external gates are green and real-player KPIs are measured.

Current status: **implemented locally, blocked on beta-player evidence**.

## Implemented In This Pass

1. Arena tutorial clarity improved.
   - Evolution and field fusion are now separate tutorial moments.
   - The Python-owned first-session plan now teaches: hand reading, mana,
     summon, combat, direct-damage lock, evolution, field fusion, turn ending
     and post-match recap.
   - The browser fallback tutorial mirrors the same sequence.

2. Existing first-session systems were preserved.
   - `services/rebirth_first_session.py` remains the source of truth for the
     first-ten-minute journey.
   - `/api/rebirth/first-session` and `/rebirth/onboarding` remain active.
   - Tutorial step telemetry remains best-effort and non-blocking.

3. Existing recap/deck/booster support was verified by code inspection.
   - `services/rebirth_postmatch.py` explains why the player won/lost and
     suggests a next step.
   - `services/rebirth_deck_coach.py` powers deck suggestions.
   - Booster opening already returns post-booster deck suggestions.

## Files Changed

- `services/rebirth_first_session.py`
- `static/js/rebirth.js`
- `tests/rebirth/test_rebirth_aaa_studio_foundations.py`

## Tests Executed

- `node --check static/js/rebirth.js`
- `.venv/bin/python -m py_compile app.py services/rebirth_first_session.py services/rebirth_telemetry.py services/rebirth_live_balance.py`
- `.venv/bin/python -m pytest tests/rebirth/test_rebirth_aaa_studio_foundations.py tests/rebirth/test_v73_telemetry_analyzer.py -q`
- `.venv/bin/python -m pytest tests/rebirth -q`

Focused result: `12 passed`.
Full Rebirth suite: `1287 passed, 5 skipped, 19 deselected`.

## Coverage

Coverage was not reduced. New coverage asserts that the first-session plan has
8 arena tutorial steps and explicitly includes the field-fusion learning step.

## KPI Status

- Tutorial Completion > 80%: not proven; requires beta-player telemetry.
- First Match Completion > 70%: not proven; requires beta-player telemetry.
- Time to first turn < 30 seconds: not proven; requires real-session telemetry.

## Risks

- More copy and guidance can still overwhelm mobile players until observed with
  real users.
- Tutorial completion persistence still uses the existing completion flag and
  reward path. No schema migration was introduced in this pass.
- Phase 1 should not be declared complete from local QA alone.

## Next Steps

1. Complete Phase 0 external gates.
2. Run closed-beta sessions and measure tutorial completion, first-match
   completion and time-to-first-turn.
3. Use real drop-off points to decide whether tutorial steps should be shorter,
   delayed or contextualized further.

## Project Status

The first-session path is stronger and more explicit, especially around the
difference between evolution and field fusion. Product readiness still depends
on human evidence.

# Rebirth Phase 2 Report - Human Telemetry

Updated: 2026-06-09

## Status

Phase 2 telemetry infrastructure received a local implementation pass, but the
phase cannot be closed until the project collects the required human sample.

Current status: **implemented locally, blocked on 500+ human matches**.

## Implemented In This Pass

1. Match telemetry payloads were enriched.
   - Terminal payloads now include `match_duration_ms`.
   - Payloads now include `player_deck_size` and a privacy-safe
     `player_deck_signature`.

2. Explicit terminal outcome events were added.
   - Finished player wins emit `match_won`.
   - Finished bot wins emit `match_lost`.
   - Non-standard terminal winners can emit `match_drawn`.
   - These events are derived telemetry only; they do not alter deterministic
     match state, replay or balance rules.

3. Live balance/dashboard payload was expanded.
   - Existing winrate, turn count, abandon rate and card usage remain.
   - Added average match duration.
   - Added deck usage summary.
   - Added evolution usage summary.
   - Added fusion count.
   - Added explicit terminal win/loss event counters.

4. Public beta KPI gate evaluator was added.
   - `services/rebirth_public_beta_gate.py` converts telemetry events into
     explicit tutorial, first-match, D1, D7, crash/error, telemetry-coverage,
     human-sample and balance checks.
   - The evaluator is conservative: D1/D7 only count matured cohorts, crash
     rate requires a minimum telemetry sample and balance cannot pass below
     500 finished human matches.
   - `tools/ops/rebirth_public_beta_gate.py --since <cohort-start-iso> --require-ready`
     gives operators a repeatable JSON report against the active database.
   - `--since <ISO timestamp>` scopes KPI reads to a real closed-beta cohort
     window so D1/D7 retention is not mixed with earlier local or test events.

## Files Changed

- `app.py`
- `services/rebirth_telemetry.py`
- `services/rebirth_live_balance.py`
- `services/rebirth_public_beta_gate.py`
- `tools/ops/rebirth_public_beta_gate.py`
- `tests/rebirth/test_rebirth_aaa_studio_foundations.py`
- `tests/rebirth/test_rebirth_public_beta_gate.py`
- `tests/rebirth/test_v73_telemetry_analyzer.py`

## Tests Executed

- `node --check static/js/rebirth.js`
- `.venv/bin/python -m py_compile app.py services/rebirth_first_session.py services/rebirth_telemetry.py services/rebirth_live_balance.py`
- `.venv/bin/python -m pytest tests/rebirth/test_rebirth_aaa_studio_foundations.py tests/rebirth/test_v73_telemetry_analyzer.py -q`
- `.venv/bin/python -m pytest tests/rebirth/test_rebirth_public_beta_gate.py -q`
- `.venv/bin/python -m pytest tests/rebirth -q`

Focused result: `12 passed`.
Full Rebirth suite: `1285 passed, 5 skipped, 19 deselected`.

## Coverage

Coverage was not reduced. New coverage asserts:

- live balance exposes deck usage, evolution usage, fusion count, terminal
  outcome counters and average duration;
- `record_match_telemetry` persists deck signature, deck size, duration and a
  derived `match_won` event.

## Required Metrics Status

- Winrate: implemented in live balance.
- Match duration: implemented in live balance.
- Turn count: implemented in live balance.
- Abandon rate: implemented in live balance.
- Card usage: implemented in live balance.
- Deck usage: implemented in live balance.
- Retention: the public beta gate computes event-sourced D1/D7 rates from
  matured user cohorts, but real D1/D7 retention still requires production
  cohort data.

## Human Sample Gate

The system still requires 500+ human matches before major balance decisions.
`services/rebirth_live_balance.py` keeps this gate explicit through
`HUMAN_MATCH_TARGET = 500` and reports `insufficient_sample` below the target.

## Risks

- Local tests prove event shape, not player behavior.
- Privacy-safe deck signatures show deck usage without exposing full private
  collections, but they must be monitored for usefulness once real samples
  arrive.
- Balance patches remain blocked until the human sample exists.

## Next Steps

1. Complete Phase 0 external gates and invite controlled testers.
2. Collect 500+ human finished/abandoned matches.
3. Export live telemetry through `/api/rebirth/balance/telemetry`.
4. Run `tools/rebirth_telemetry_analyzer.py` against the production database.
5. Run `tools/ops/rebirth_public_beta_gate.py --since <cohort-start-iso> --require-ready`
   once cohorts have matured.
6. Only then consider large balance or content changes.

## Project Status

Telemetry infrastructure is materially ready for closed-beta learning. Phase 2
is blocked by data collection, not by local code structure.

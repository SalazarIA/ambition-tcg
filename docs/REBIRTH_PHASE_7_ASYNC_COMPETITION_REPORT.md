# Rebirth Phase 7 Report - Async Competition

Updated: 2026-06-08

## Status

Phase 7 was not implemented in this pass.

Current status: **blocked by earlier product-validation gates**.

## Existing Foundation Observed

The deterministic infrastructure for async competition already exists in a
limited form:

- `services/rebirth_async_competition.py` builds privacy-safe replay share and
  ghost challenge payloads.
- `/api/rebirth/async/share/<match_id>` returns verified async competition
  payloads for finished matches.
- `/api/rebirth/async/ghosts` returns recent finished-match ghost payloads.
- Replay verification is built on deterministic replay envelopes.
- No WebSocket or real-time PvP architecture is required for this path.

## What Was Implemented

No new async competition features were added. This avoids premature leaderboard
or rival systems before the core product KPIs are proven.

## Files Changed

None specifically for Phase 7.

## Tests Executed

Existing focused tests still cover the async share contract indirectly through
`tests/rebirth/test_rebirth_aaa_studio_foundations.py`.

Focused result from this pass: `12 passed`.

## Coverage

Coverage was not reduced.

## Risks

- Async competition can amplify balance problems if launched before telemetry
  and retention are healthy.
- Public replay sharing needs product/legal review around privacy and abuse.

## Next Steps

1. Complete Phase 1-6 gates.
2. Promote existing replay/ghost payloads into a player-facing UI only after
   core retention is healthy.
3. Add deck challenges, rivals and leaderboards as deterministic, server-
   verifiable contracts.

## Project Status

The foundation is present and aligned with the roadmap. Shipping it as a full
phase now would be premature.

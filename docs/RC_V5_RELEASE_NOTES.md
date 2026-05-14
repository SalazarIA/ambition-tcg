# Ambitionz RC V5 Release Notes

## Summary

RC V5 prepares Ambitionz for a more professional public beta freeze without adding external analytics, payments or heavy dependencies.

- Block 99: public beta copy pass for the main player-facing product surfaces.
- Block 100: local beta telemetry endpoint and defensive browser tracking.
- Block 101: compact beta feedback widget and JSON feedback endpoint.
- Block 102: public Known Issues / Beta Notes section on Roadmap.
- Block 103: local balance watchlist script and generated Markdown report.
- Block 104: service worker v186, structural coverage and full release-candidate QA.

## Primary Files

- `app.py`
- `services/beta_telemetry.py`
- `static/js/beta_telemetry.js`
- `static/js/beta_feedback.js`
- `static/js/service-worker.js`
- `static/css/style.css`
- `templates/index.html`
- `templates/roadmap.html`
- `templates/arena.html`
- `templates/profile.html`
- `templates/progression.html`
- `tools/qa/balance_watchlist.py`
- `docs/RC_PUBLIC_CHECKLIST.md`
- `docs/BALANCE_WATCHLIST.md`

## QA Executed

Run the RC V5 validation list before commit or deploy:

- `python3 -m py_compile app.py`
- `python3 -m py_compile services/battle_engine_v2.py services/battle_engine_v2_adapter.py services/match_engine_facade.py services/match_payloads.py services/match_telemetry.py services/card_effect_resolver.py`
- `python3 -m py_compile tools/qa/balance_watchlist.py`
- `python3 -m pytest -q`
- `python3 tools/qa/qa_backend.py`
- `python3 tools/qa/qa_arena_matrix.py`
- `python3 tools/qa/playability_audit.py`
- `python3 tools/qa/battle_balance_sim.py --matches 100 --seed 99104 --max-rounds 30`
- `python3 tools/qa/qa_battle_gauntlet.py`
- `python3 tools/qa/run_local_browser_qa.py`
- `python3 tools/qa/balance_watchlist.py`
- `node --check` for Arena, PWA, progression, tutorial and new beta scripts.
- `git diff --check`, `git status --short`, `git ls-files -o --exclude-standard`

## Known Risks

- Telemetry is local and intentionally minimal; it should guide beta triage, not replace production analytics.
- Feedback persistence uses the existing feedback table when available and JSONL fallback if database writes fail.
- Gold, boosters and rewards are internal beta economy systems and may be rebalanced or reset.
- Balance watchlist depends on available local data; with no real traffic it relies on deterministic simulation.

## Recommended Next Steps

- Review the generated `docs/BALANCE_WATCHLIST.md` after real playtest sessions.
- Use feedback submissions to prioritize first-session friction and battle clarity.
- Keep the next cycle focused on evidence from telemetry, match outcomes and player feedback before adding larger systems.

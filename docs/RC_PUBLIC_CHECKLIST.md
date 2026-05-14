# Ambitionz Public Beta RC Checklist

This checklist is a human-readable beta readiness snapshot. It avoids sensitive operational details and does not promise features before they are implemented.

## Ready For Review

- Arena jogavel: BE2, Arena Clean, structured combat feedback and recovery checks are active.
- Training: canonical first-session mode for learning, rewards and progression.
- Collection: owned, locked and newly unlocked states are visible with defensive fallbacks.
- Deck Builder: 30-card beta deck rules, validation and Deck Readiness Coach are visible.
- Missions: beta objectives progress from real loop actions where available.
- Daily: defensive streak, XP and Gold reward loop is present.
- Gold: internal beta currency only, with no real-money checkout active.
- Shop beta: Gold booster offers and locked supporter copy are separated from payment language.
- Booster: opening flow returns cards, history and collection feedback where supported.
- Profile/Progression: account level, XP, Gold, missions, daily and next steps are connected.
- Feedback: testers can submit bug, balance, visual and suggestion reports.
- PWA: manifest and service worker are versioned for static asset changes.
- QA status: full RC QA must pass before commit, push or deploy.

## Next Human Review Focus

- Confirm mobile spacing on Home, Progression, Daily, Deck Builder and post-match screens.
- Verify first-session copy stays clear for both guest and logged-in users.
- Review balance sim output before public release notes.

## RC V5 Beta Freeze Addendum

- Public copy pass: Home, Roadmap, Shop, Daily, Profile, Progression, Collection, Deck Builder, Arena, Ranking and Leaderboard should present Ambitionz as a playable public beta.
- Local telemetry: beta events are accepted through a defensive local endpoint and stored in existing retention data or JSONL fallback.
- Feedback widget: Roadmap, Arena, Profile and Progression can surface a compact beta feedback panel without blocking gameplay.
- Known issues: Roadmap now explains what works, what is still beta, known limits, feedback flow and next-cycle focus.
- Balance watchlist: `tools/qa/balance_watchlist.py` generates `docs/BALANCE_WATCHLIST.md` from telemetry when available and BE2 simulation otherwise.
- Economy notice: Gold, boosters and rewards remain internal beta systems; no real-money payment flow is active.
- QA status: RC V5 requires py_compile, pytest, backend QA, Arena matrix, playability audit, battle sim, gauntlet, browser QA, node checks, diff check and status review before commit/deploy.

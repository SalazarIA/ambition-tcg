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

## Arena V6 Combat Clarity Addendum

- Arena V6: premium fantasy neon battlefield, clearer lanes, stronger HUD hierarchy and compact Ready guidance.
- Combat clarity: Battle Highlights, normalized timeline and Round Summary explain strategy, card, damage, shield, death and result events.
- Card types: Creature, Spell and Trap cards now carry stronger visual labels and simple "how to use" education.
- Spell targeting: the frontend highlights valid or inferred targets and falls back to backend-compatible targets where BE2 is still limited.
- Trap Zone: traps are presented as prepared cards instead of lane creatures, with local defensive fallback until canonical state updates.
- First battle tutorial: Training can show a light in-arena tutorial with Skip, Next and Replay controls.
- Card art pipeline: `static/assets/cards/card_art_manifest.json`, `docs/CARD_ART_DIRECTION.md`, `docs/CARD_ART_PROMPTS_STARTER.md` and `tools/qa/card_art_manifest_check.py` define and validate placeholder/final card art.
- Known issue: Spell/Trap behavior is V1 and conservative; advanced chained effects and card draw remain future work.

## RC V6 Battle Systems Addendum

- Spell/Trap contract: Arena can send card type, cast mode and target metadata while legacy card play payloads remain compatible.
- Spell Resolver V1: damage, shield, heal and Ambition effects resolve in BE2 with safe fallbacks.
- Trap Resolver V1: traps prepare into canonical state, trigger during incoming attacks and are consumed safely.
- Intent Balance V2: Strike remains pressure, Guard protects harder and Focus produces clearer Ambition value.
- Starter Deck Teaching Pass: the beta deck remains 30 cards with 21 creatures, 6 spells and 3 traps.
- Card Identity Pack V1: the 30 starter cards now carry role, short lore and how-to-use copy in the art manifest.
- Collection/Deck Builder teaching UX: role filters, preview text and deck scores help explain why cards belong in a deck.
- Production smoke/cache guard: production checks accept `AMBITIONZ_PROD_URL` and `AMBITIONZ_EXPECTED_SW_VERSION` for release validation.

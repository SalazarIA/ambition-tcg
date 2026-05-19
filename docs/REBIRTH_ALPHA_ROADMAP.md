# Rebirth Alpha Roadmap

## Alpha V1: Playable One-Card Duel

- `/rebirth` isolated from old Arena.
- One active card per side.
- Intent loop: Strike, Guard, Focus.
- DOM-based 3D adapter placeholder.
- Rebirth tests and QA smoke.

## Alpha V2: Deck Selection + Difficulty

- Ember Oath, Deepguard and Null Circuit starter archetypes.
- Easy, Normal and Hard difficulty.
- Rival profiles: The Warden, The Duelist and The Oracle.
- Quick Duel mode.
- Premium card detail panel.

## Alpha V3: Rewards / Progression Bridge

- Mock reward preview now exists after match end.
- Next step is account-safe persistence for XP, Gold and unlock progress.
- Reward copy must remain clear while persistence is preview-only.

## Alpha V4: Real 3D

- Replace DOM placeholder with a real Three.js/GLB scene behind `Rebirth3D`.
- Preserve event boundary: match start, intent, card activation, strike, guard, focus, damage, KO and round end.
- Keep DOM HUD lightweight so the scene remains readable.

## Alpha V5: Account Persistence

- Store Rebirth match history.
- Persist selected deck, difficulty and reward grants server-side.
- Add migration bridge from legacy account state only after QA signs off.

## Alpha V6: Multiplayer / Async

- Add real player-vs-player or async rival mode.
- Keep Rebirth state contract deterministic and serializable.
- Do not reuse old Socket.IO Arena gameplay payloads as the Rebirth source of truth.

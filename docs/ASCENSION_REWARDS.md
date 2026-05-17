# Ascension Rewards

Ascension Duel rewards are deterministic and returned in the post-match API payload.

Reward fields:

- `xp`
- `gold`
- `champion_progress`
- `unlock_progress`
- `unlock`
- `summary`

The reward calculation considers result, round count, Ascension, Domination and Champion participation. It is intentionally conservative so it can coexist with the existing economy while the full progression migration continues.

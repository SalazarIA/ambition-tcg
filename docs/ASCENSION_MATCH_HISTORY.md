# Ascension Match History

Ascension Duel history uses a defensive JSONL fallback at `instance/ascension_history.jsonl`.

Recorded fields:

- result
- rounds
- Champion
- bot profile
- opponent
- decisive card
- reward
- timestamp

This avoids a risky database migration in the RC V8 phase while still giving QA and players a visible Chronicle route at `/ascension-history`.

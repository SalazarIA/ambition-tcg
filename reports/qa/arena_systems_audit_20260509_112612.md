# Ambitionz Arena Systems Audit

- Generated: 20260509_112612

## 1. Contract Audit

### DOM IDs
```text
- az48-start: OK
- az48-strike: OK
- az48-guard: OK
- az48-focus: OK
- az48-ready: OK
- az48-hand: OK
- az48-me-field: OK
- az48-enemy-field: OK
- az48-message: OK
- az48-round: OK
- az48-phase: OK
```

### Socket/Event Contract
```text
- az48_start_training: JS=OK | backend=OK
- az48_set_intent: JS=OK | backend=OK
- az48_play_card: JS=OK | backend=OK
- az48_declare_ready: JS=OK | backend=OK
- az48_state: JS=OK | backend=OK
```

## 2. Legacy Conflict Audit

```text
- choose_intent: 1
- declare_ready: 9
- start_training: 6
- game_state_update: 6
```

### Risk Summary
```text
No P0/P1 legacy renderer risk detected.
```

## 3. Play Card Function Audit

```text
function playCard(id) {
        const hand = arr((latestState && latestState.me && latestState.me.hand) || []);
        const index = hand.findIndex((card, cardIndex) => normalizeCard(card, cardIndex).id === String(id));

        if (index < 0) {
            setMessage("Card is no longer in hand.");
            return;
        }

        setMessage("Playing card...");
        emit("az48_play_card", { card_id: id, card_index: index });
    }
```

### Assertions
```text
- Uses az48_play_card: OK
- Does not use play_to_field: OK
- Does not use undefined c.id: OK
- Sends card_id from id: OK
- Sends card_index: OK
```

## 4. Backend Handler Audit

```text
- @socketio.on("az48_start_training"): OK
- @socketio.on("az48_request_state"): OK
- @socketio.on("az48_set_intent"): OK
- @socketio.on("az48_play_card"): OK
- @socketio.on("az48_declare_ready"): OK
- def emit_az48_state_for_sid: OK
- build_arena_clean_state: OK
```

### Relevant Lines
```text
1: from services.arena_clean_state import build_arena_clean_state, build_arena_clean_payloads
3801:     emit_az48_state_for_sid(sid, message="Training started. Choose your intent.")
3824:     emit_az48_state_for_sid(sid, message=message)
3850:     emit_az48_state_for_sid(sid, message=message)
3906:         emit_az48_state_for_sid(sid, message="Training started. Choose your intent.")
3917:     emit_az48_state_for_sid(sid)
3940:     emit_az48_state_for_sid(sid, message=message)
3948:         payload = build_arena_clean_state(match, "p1", message=message)
3959: def emit_az48_state_for_sid(sid=None, message=None):
3985:                 payload = build_arena_clean_state(match, viewer_key, message=message)
4001: @socketio.on("az48_start_training")
4002: def az48_start_training(data=None):
4004:     emit_az48_state_for_sid(message="Training started. Choose your intent.")
4009:     payload = emit_az48_state_for_sid()
4014: @socketio.on("az48_set_intent")
4015: def az48_set_intent(data=None):
4018:     emit_az48_state_for_sid(message=f"{intent} selected. Play a card or press Ready.")
4021: @socketio.on("az48_play_card")
4022: def az48_play_card(data=None):
4032:         emit_az48_state_for_sid(sid, message=bot_message)
4034:         emit_az48_state_for_sid(sid)
4037: @socketio.on("az48_declare_ready")
4038: def az48_declare_ready(data=None):
4054:         emit_az48_state_for_sid(sid, message=bot_message)
4056:         emit_az48_state_for_sid(sid, message="Ready. Waiting for battle resolution.")
```

## 5. State Architecture Audit

```text
- arena_clean_state has build_arena_clean_state: OK
- arena_clean_state includes legal_actions: OK
- arena_clean_state includes playable_card_ids: OK
- match_actions has play_card: OK
- match_actions mutates hand: OK
- match_actions has declare_ready: OK
- match_actions references round/resolve: OK
```

## 6. Engineering Recommendations

```text
- Architecture target: one arena renderer, one payload schema, one event namespace.
- Clean arena should prefer az48_state and ignore incompatible legacy payloads.
- Browser QA must verify hand decreases, field increases, round/HP changes, and no stuck message.
- Production QA must verify cache version after deploy.
```
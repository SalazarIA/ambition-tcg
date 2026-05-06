# Ambitionz — Engine Contract Audit

## Purpose

This audit maps the current battle engine, socket events, payloads and frontend dependencies before the fullstack Arena rebuild.

## Socket Events

### backend_socket_emits
- arena_state_update: 2
- battle_log: 1
- game_over: 4
- game_state_update: 3

### frontend_socket_emits
- cancel_queue: 1
- declare_ready: 1
- join_bot_match: 1
- join_private_room: 1
- join_queue: 1
- join_training: 1
- play_to_field: 1
- set_intent: 1
- toggle_unleash: 2

### frontend_socket_listeners
- battle_events: 1
- battle_log: 1
- connect: 1
- disconnect: 1
- game_over: 1
- game_state_update: 1
- match_found: 1
- matchmaking_status: 1
- opponent_left: 1
- post_match_summary: 1
- presence_update: 1
- queue_status: 1

### backend_socket_listeners
- None

## Socket Contract Gaps

- Frontend emits but backend listener missing: `cancel_queue`
- Frontend emits but backend listener missing: `declare_ready`
- Frontend emits but backend listener missing: `join_bot_match`
- Frontend emits but backend listener missing: `join_private_room`
- Frontend emits but backend listener missing: `join_queue`
- Frontend emits but backend listener missing: `join_training`
- Frontend emits but backend listener missing: `play_to_field`
- Frontend emits but backend listener missing: `set_intent`
- Frontend emits but backend listener missing: `toggle_unleash`
- Backend emits but frontend listener missing: `arena_state_update`

## Keyword Counts

### app.py
- ambition: 22
- battle_log: 4
- deck: 88
- energy: 23
- field: 1
- game_state_update: 3
- hand: 30
- hp: 6
- intent: 10
- monster: 18
- post_match_summary: 6
- ready: 3
- reward: 48
- spell: 1
- trap: 1

### game/state.py
- ambition: 6
- deck: 3
- energy: 2
- field: 2
- graveyard: 1
- hand: 3
- hp: 3
- intent: 20
- ready: 1

### game/battle.py
- ambition: 41
- deck: 1
- energy: 14
- field: 32
- graveyard: 4
- hand: 4
- hp: 19
- intent: 19
- monster: 68
- ready: 6
- spell: 9
- trap: 9

### game/deck.py
- ambition: 1
- deck: 80
- energy: 1
- hand: 5
- hp: 1
- intent: 1
- monster: 24
- spell: 28
- trap: 28

### game/engine.py
- ambition: 37
- field: 2
- hp: 1
- monster: 2

### game/cards.py
- ambition: 2
- hp: 4
- monster: 34
- spell: 21
- trap: 21

### game/match_utils.py
- No relevant keywords found.

### game/matchmaking.py
- No relevant keywords found.

### game/bot_ai.py
- ambition: 5
- field: 7
- hand: 15
- hp: 31
- intent: 23
- monster: 13
- ready: 2
- spell: 14
- trap: 14

### services/match_payloads.py
- ambition: 8
- deck: 4
- energy: 8
- field: 10
- graveyard: 4
- hand: 4
- hp: 14
- intent: 6
- monster: 3
- ready: 4
- reward: 5

### services/arena_payload.py
- ambition: 4
- deck: 2
- energy: 11
- field: 18
- graveyard: 2
- hand: 14
- hp: 2
- intent: 6
- monster: 11
- ready: 6
- spell: 8
- trap: 8

### services/battle_summary.py
- field: 2
- hp: 4
- monster: 2

### services/match_telemetry.py
- hp: 6

### static/js/game.js
- ambition: 30
- battle_log: 1
- deck: 4
- declare_ready: 1
- energy: 11
- field: 16
- game_state_update: 1
- graveyard: 1
- hand: 18
- hp: 17
- intent: 37
- monster: 9
- post_match_summary: 1
- ready: 47
- reward: 5
- set_intent: 1
- spell: 5
- trap: 5

### templates/arena.html
- ambition: 6
- deck: 4
- energy: 2
- field: 10
- graveyard: 1
- hand: 9
- hp: 5
- intent: 14
- monster: 5
- ready: 11
- spell: 5
- trap: 3

## Functions Found

### app.py
Python:
- create_database_tables
- ensure_economy_schema
- log_system_event
- log_rc_event
- csrf_enabled
- generate_csrf_token
- inject_security_helpers
- validate_csrf_token
- attach_security_headers
- generate_invite_code
- account_can_login
- normalize_email_verification_state
- password_errors
- login_attempt_fingerprint
- recent_failed_login_count
- record_failed_login
- reset_login_attempts
- hash_url_token
- issue_password_reset_token
- reset_token_is_expired
- mark_user_verified
- get_public_base_url
- log_sensitive_link_for_local_dev
- current_user
- login_required_redirect
- dev_tools_enabled
- dev_tools_required_redirect
- danger_confirmation_matches
- require_danger_confirmation_or_redirect
- build_liveops_observability
- has_message
- admin_audit
- _card_cost_value
- _is_playable_with_energy
- _is_playable_monster_with_energy
- draw_beta_starting_hand
- swap_in
- get_existing_table_names
- quote_cleanup_table_name
- safe_delete_table_rows
- cleanup_gameplay_tables
- cleanup_non_admin_users
- safe_admin_user_id
- get_session_user
- admin_required_redirect
- admin_ping
- debug_routes
- admin_dev_tools
- admin_test_email
- admin_reset_test_users
- admin_clear_gameplay_data
- admin_system
- admin_users
- admin_toggle_admin
- admin_toggle_tester
- admin_verify_user
- admin_ban_user
- admin_unban_user
- admin_invites
- admin_beta_events
- admin_feedback
- admin_feedback_update
- check_route_status
- build_internal_rc_status
- add_check
- admin_release_candidate
- index
- health
- pwa_manifest
- service_worker
- internal_server_error
- resend_verification
- get_cosmetic_foundation_for_user
- profile
- leaderboard
- ranking
- how_to_play
- first_session
- closed_test
- terms
- data_deletion
- support
- privacy
- offline
- register
- confirm_email
- login
- logout
- collection
- get_booster_pack
- weighted_card_pool_for_pack
- booster_pull_from_pack
- economy
- economy_grant_founder
- economy_test_gems
- shop
- auto_build_deck
- booster_history
- deck_builder
- arena
- emit_log
- emit_battle_events
- emit_state
- create_player_object
- emit_v105_match_end_summary
- emit_arena_state_v8
- emit_v107_post_match_summary
- end_match
- register_socket_handlers
- tutorial
- campaign
- training
- feedback
- admin_reports
- admin_balance
- beta_launch
- admin
- complete_onboarding
- missions
- claim_user_mission
- match_history
- welcome
- daily
- api_retention_event
- progression

### game/state.py
Python:
- create_player_state
- create_match_state
- normalize_intent
- set_player_intent
- get_intent_rule
- reset_round_flags

### game/battle.py
Python:
- apply_intent_damage_modifier
- apply_strike_loss_penalty
- strike_win_bonus
- clash_damage_floor
- clash_net_damage_floor
- duel_storm_damage
- apply_clash_pressure
- apply_duel_storm_pressure
- apply_focus_survival
- apply_damage_package
- _card_label
- _player_snapshot
- _battle_snapshot
- _append_player_change_events
- build_battle_events
- resolve_battle

### game/deck.py
Python:
- get_fixed_starter_deck_ids
- get_fixed_starter_collection_ids
- validate_fixed_starter_deck_catalog
- load_card_ids
- cards_from_ids
- choose_cards_with_duplicates
- choose_unique_cards
- create_starter_collection
- create_starter_deck_from_collection
- create_starter_deck
- create_new_player_card_data
- build_playable_deck
- draw_starting_hand
- draw_card
- count_types
- validate_deck
- collection_summary
- deck_summary

### game/engine.py
Python:
- clamp_ambition
- add_ambition
- spend_ambition
- can_unleash_ambition
- request_unleash
- cancel_unleash
- resolve_manual_unleash
- trigger_overreach
- card_generates_ambition
- register_card_played_for_ambition

### game/cards.py
Python:
- rarity_for_index
- monster_effect_for_index
- element_power_base
- generate_monsters
- spell_effect_for_index
- generate_spells
- trap_effect_for_index
- generate_traps
- get_card_by_id
- get_cards_by_type
- get_cards_by_element
- get_cards_by_rarity
- get_all_cards
- get_monsters
- get_spells
- get_traps
- card_sort_key
- beta_catalog_stats
- calculate_card_cost
- apply_card_costs
- infer_card_sigil
- infer_card_role
- enrich_card_identity

### game/match_utils.py
Python:
- is_bot_player
- safe_user_id
- player_display_name
- get_match_result_label

### game/matchmaking.py
Python:
- generate_private_room_code
- normalize_room_code
- is_valid_room_code

### game/bot_ai.py
Python:
- profile_for
- weighted_choice
- card_score
- choose_intent
- choose_card_index
- play_index
- bot_choose_play

### services/match_payloads.py
Python:
- find_player_key
- match_mode
- perspective_battle_events
- build_game_state_payloads
- build_post_match_payload
- _safe_hp
- history_result_for_ending
- build_v8_arena_payloads
- build_v8_arena_payload

### services/arena_payload.py
Python:
- safe_int
- normalize_card_for_payload
- normalize_card_list
- first_card
- normalize_field
- normalize_player
- get_player_keys
- build_arena_state_payload
- build_arena_payloads_for_match

### services/battle_summary.py
Python:
- safe_name
- safe_hp
- safe_card_name
- build_match_summary_lines

### services/match_telemetry.py
Python:
- safe_player_user_id
- safe_player_name
- safe_player_hp
- match_mode
- record_match_telemetry

### static/js/game.js
JavaScript:
- setElementClass
- setBodyBattleState
- updateReadyVisuals
- updateIntentVisuals
- getCardPlayStatus
- scorePlayableCard
- findRecommendedPlayableCard
- hasPlayableCard
- canUseAmbitionUnleash
- setArenaButtonState
- updateArenaEaseState
- normalizeBattleLogMessage
- showPostMatchSummary
- closePostMatchSummary
- logLine
- renderCard
- updateHud
- renderField
- renderHand
- renderState
- setButtonBusy
- setQueueStatus
- clearMatchmakingCountdown
- tickMatchmakingCountdown
- startMatchmakingCountdown
- setSearchUi
- updatePresence
- setIntent
- bootArenaControls

### templates/arena.html
- None

## Important Snippets

### app.py:1923
```text
1919:                 flash("Invalid or expired invite code.")
1920:                 return redirect("/register")
1921: 
1922:         if User.query.filter_by(email=email).first():
1923:             flash("Email already exists.")
1924:             return redirect("/register")
1925: 
1926:         if User.query.filter_by(username=username).first():
1927:             flash("Username already exists.")
1928:             return redirect("/register")
1929: 
1930:         new_user = User(
1931:             username=username,
```

### app.py:1927
```text
1923:             flash("Email already exists.")
1924:             return redirect("/register")
1925: 
1926:         if User.query.filter_by(username=username).first():
1927:             flash("Username already exists.")
1928:             return redirect("/register")
1929: 
1930:         new_user = User(
1931:             username=username,
1932:             email=email,
1933:             account_status="active",
1934:             is_tester=True if invite else False,
1935:             is_verified=True,
```

### app.py:2537
```text
2533:     if not match:
2534:         return
2535: 
2536:     for sid, state in build_game_state_payloads(room_id, match):
2537:         socketio.emit("game_state_update", state, to=sid)
2538:         try:
2539:             emit_arena_state_v8(match, phase="sync")
2540:         except Exception as error:
2541:             print("ARENA V8 SYNC PATCH ERROR:", type(error).__name__, error)
2542: 
2543: 
2544: def create_player_object(user, sid):
2545:     deck = build_playable_deck(user.deck_json)
```

### app.py:2592
```text
2588:         p1_sid = (match.get("p1") or {}).get("sid")
2589:         p2_sid = (match.get("p2") or {}).get("sid")
2590: 
2591:         if p1_sid:
2592:             socketio.emit("game_state_update", payloads["p1"], room=p1_sid)
2593:             try:
2594:                 emit_arena_state_v8(match, phase="sync")
2595:             except Exception as error:
2596:                 print("ARENA V8 SYNC PATCH ERROR:", type(error).__name__, error)
2597:             socketio.emit("arena_state_update", payloads["p1"], room=p1_sid)
2598: 
2599:         if p2_sid:
2600:             socketio.emit("game_state_update", payloads["p2"], room=p2_sid)
```

### app.py:2600
```text
2596:                 print("ARENA V8 SYNC PATCH ERROR:", type(error).__name__, error)
2597:             socketio.emit("arena_state_update", payloads["p1"], room=p1_sid)
2598: 
2599:         if p2_sid:
2600:             socketio.emit("game_state_update", payloads["p2"], room=p2_sid)
2601:             try:
2602:                 emit_arena_state_v8(match, phase="sync")
2603:             except Exception as error:
2604:                 print("ARENA V8 SYNC PATCH ERROR:", type(error).__name__, error)
2605:             socketio.emit("arena_state_update", payloads["p2"], room=p2_sid)
2606: 
2607:     except Exception as error:
2608:         print("ARENA V8 PAYLOAD EMIT ERROR:", type(error).__name__, error)
```

### game/state.py:26
```text
0022:         "hand": hand,
0023:         "graveyard": [],
0024:         "field_m": None,
0025:         "field_st": None,
0026:         "ready": False,
0027:         "shield": 0,
0028:         "energy": 0,
0029:         "max_energy": 0,
0030:         "ambition": 0,
0031:         "wants_unleash": False,
0032:         "ambition_unleashed": False,
0033:         "overreach_count": 0,
0034:         "intent": "Strike",
```

### game/battle.py:252
```text
0248:         "description": logs[-1] if logs else "Battle resolved.",
0249:     })
0250: 
0251:     events.append({
0252:         "type": "unleash_ready",
0253:         "side": "player",
0254:         "ready": int(match["p1"].get("ambition", 0)) >= 5 and bool(match["p1"].get("field_m")),
0255:     })
0256:     events.append({
0257:         "type": "unleash_ready",
0258:         "side": "enemy",
0259:         "ready": int(match["p2"].get("ambition", 0)) >= 5 and bool(match["p2"].get("field_m")),
0260:     })
```

### game/battle.py:254
```text
0250: 
0251:     events.append({
0252:         "type": "unleash_ready",
0253:         "side": "player",
0254:         "ready": int(match["p1"].get("ambition", 0)) >= 5 and bool(match["p1"].get("field_m")),
0255:     })
0256:     events.append({
0257:         "type": "unleash_ready",
0258:         "side": "enemy",
0259:         "ready": int(match["p2"].get("ambition", 0)) >= 5 and bool(match["p2"].get("field_m")),
0260:     })
0261: 
0262:     return events
```

### game/battle.py:257
```text
0253:         "side": "player",
0254:         "ready": int(match["p1"].get("ambition", 0)) >= 5 and bool(match["p1"].get("field_m")),
0255:     })
0256:     events.append({
0257:         "type": "unleash_ready",
0258:         "side": "enemy",
0259:         "ready": int(match["p2"].get("ambition", 0)) >= 5 and bool(match["p2"].get("field_m")),
0260:     })
0261: 
0262:     return events
0263: 
0264: 
0265: def resolve_battle(match):
```

### game/battle.py:259
```text
0255:     })
0256:     events.append({
0257:         "type": "unleash_ready",
0258:         "side": "enemy",
0259:         "ready": int(match["p2"].get("ambition", 0)) >= 5 and bool(match["p2"].get("field_m")),
0260:     })
0261: 
0262:     return events
0263: 
0264: 
0265: def resolve_battle(match):
0266:     p1 = match["p1"]
0267:     p2 = match["p2"]
```

### game/battle.py:447
```text
0443:     p1["field_st"] = None
0444:     p2["field_m"] = None
0445:     p2["field_st"] = None
0446: 
0447:     p1["ready"] = False
0448:     p2["ready"] = False
0449: 
0450:     p1_draw = draw_card(p1)
0451:     p2_draw = draw_card(p2)
0452: 
0453:     if p1_draw:
0454:         logs.append(f"{p1['name']} drew 1 card for the next round.")
0455:     else:
```

### game/battle.py:448
```text
0444:     p2["field_m"] = None
0445:     p2["field_st"] = None
0446: 
0447:     p1["ready"] = False
0448:     p2["ready"] = False
0449: 
0450:     p1_draw = draw_card(p1)
0451:     p2_draw = draw_card(p2)
0452: 
0453:     if p1_draw:
0454:         logs.append(f"{p1['name']} drew 1 card for the next round.")
0455:     else:
0456:         logs.append(f"{p1['name']} had no cards to draw and took fatigue damage.")
```

### game/bot_ai.py:242
```text
0238: def bot_choose_play(bot, opponent, difficulty="normal"):
0239:     profile = profile_for(difficulty)
0240:     logs = []
0241: 
0242:     if bot.get("ready"):
0243:         return {
0244:             "intent": bot.get("intent", "Strike"),
0245:             "monster": bot.get("field_m"),
0246:             "spell_or_trap": bot.get("field_st"),
0247:             "difficulty": difficulty,
0248:             "profile": profile["name"],
0249:             "logs": logs,
0250:         }
```

### game/bot_ai.py:274
```text
0270:     ):
0271:         if request_unleash(bot):
0272:             logs.append(f"{bot['name']} prepared Ambition Unleash.")
0273: 
0274:     bot["ready"] = True
0275: 
0276:     return {
0277:         "intent": intent,
0278:         "monster": monster,
0279:         "spell_or_trap": spell_or_trap,
0280:         "difficulty": difficulty,
0281:         "profile": profile["name"],
0282:         "logs": logs,
```

### services/match_payloads.py:90
```text
0086:                     "graveyard_count": len(player["graveyard"]),
0087:                     "hand": player["hand"],
0088:                     "field_m": player["field_m"],
0089:                     "field_st": player["field_st"],
0090:                     "ready": player["ready"],
0091:                     "energy": player.get("energy", 0),
0092:                     "max_energy": player.get("max_energy", 0),
0093:                     "ambition": player.get("ambition", 0),
0094:                     "ambition_unleashed": player.get("ambition_unleashed", False),
0095:                     "wants_unleash": player.get("wants_unleash", False),
0096:                     "overreach_count": player.get("overreach_count", 0),
0097:                     "intent": player.get("intent", "Strike"),
0098:                 },
```

### services/match_payloads.py:105
```text
0101:                     "hp": enemy["hp"],
0102:                     "deck_count": len(enemy["deck"]),
0103:                     "graveyard_count": len(enemy["graveyard"]),
0104:                     "hand_count": len(enemy["hand"]),
0105:                     "ready": enemy["ready"],
0106:                     "energy": enemy.get("energy", 0),
0107:                     "max_energy": enemy.get("max_energy", 0),
0108:                     "ambition": enemy.get("ambition", 0),
0109:                     "ambition_unleashed": enemy.get("ambition_unleashed", False),
0110:                     "wants_unleash": enemy.get("wants_unleash", False),
0111:                     "overreach_count": enemy.get("overreach_count", 0),
0112:                     "intent": enemy_intent,
0113:                     "field_m_status": enemy_monster_status,
```

### services/arena_payload.py:148
```text
0144:         "energy": safe_int(player.get("energy") or player.get("current_energy"), 0),
0145:         "max_energy": safe_int(max_energy, 0),
0146:         "ambition": safe_int(player.get("ambition"), 0),
0147:         "intent": player.get("intent") or player.get("selected_intent") or "Hidden",
0148:         "ready": bool(player.get("ready") or player.get("is_ready")),
0149:         "deck_count": len(player.get("deck") or []),
0150:         "graveyard_count": len(player.get("graveyard") or player.get("discard") or []),
0151:         "hand": hand if viewer else [],
0152:         "hand_count": len(player.get("hand") or []),
0153:         "field": normalize_field(player),
0154:     }
0155: 
0156: 
```

### services/arena_payload.py:195
```text
0191:         if not me["hand"]:
0192:             status_message = "Start the duel or wait for your hand."
0193:         elif not me["intent"] or me["intent"] == "Hidden":
0194:             status_message = "Choose your intent."
0195:         elif not me["ready"]:
0196:             status_message = "Play a card if possible, then press Ready."
0197:         else:
0198:             status_message = "Waiting for opponent."
0199: 
0200:     return {
0201:         "schema": "arena_state_v8",
0202:         "round": safe_int(round_number, 1),
0203:         "phase": resolved_phase,
```

### services/arena_payload.py:212
```text
0208:         "enemy": enemy,
0209:         "my_hand": me["hand"],
0210:         "hand": me["hand"],
0211:         "enemy_hand_count": enemy["hand_count"],
0212:         "can_act": not me["ready"],
0213:         "training": bool(match.get("training")),
0214:         "is_bot_match": bool(match.get("is_bot_match") or match.get("training")),
0215:     }
0216: 
0217: 
0218: def build_arena_payloads_for_match(match, phase=None, message=None):
0219:     return {
0220:         "p1": build_arena_state_payload(match, viewer_key="p1", phase=phase, message=message),
```

### static/js/game.js:29
```text
0025:     const phase = String(state?.phase || "").toLowerCase();
0026: 
0027:     body.classList.toggle("battle-active-v112", Boolean(state));
0028:     body.classList.toggle("battle-resolving-v112", Boolean(state?.resolving) || phase.includes("resolve"));
0029:     body.classList.toggle("battle-ready-v112", Boolean(me.ready));
0030:     body.classList.toggle("enemy-ready-v112", Boolean(enemy.ready));
0031: }
0032: 
0033: function updateReadyVisuals(state) {
0034:     const me = state?.me || {};
0035:     const enemy = state?.enemy || {};
0036: 
0037:     setElementClass("my-ready", "ready-pill-v112", Boolean(me.ready));
```

### static/js/game.js:30
```text
0026: 
0027:     body.classList.toggle("battle-active-v112", Boolean(state));
0028:     body.classList.toggle("battle-resolving-v112", Boolean(state?.resolving) || phase.includes("resolve"));
0029:     body.classList.toggle("battle-ready-v112", Boolean(me.ready));
0030:     body.classList.toggle("enemy-ready-v112", Boolean(enemy.ready));
0031: }
0032: 
0033: function updateReadyVisuals(state) {
0034:     const me = state?.me || {};
0035:     const enemy = state?.enemy || {};
0036: 
0037:     setElementClass("my-ready", "ready-pill-v112", Boolean(me.ready));
0038:     setElementClass("enemy-ready", "ready-pill-v112", Boolean(enemy.ready));
```

### static/js/game.js:37
```text
0033: function updateReadyVisuals(state) {
0034:     const me = state?.me || {};
0035:     const enemy = state?.enemy || {};
0036: 
0037:     setElementClass("my-ready", "ready-pill-v112", Boolean(me.ready));
0038:     setElementClass("enemy-ready", "ready-pill-v112", Boolean(enemy.ready));
0039:     setElementClass("ready-btn", "ready-btn-active-v112", Boolean(me.ready));
0040: }
0041: 
0042: function updateIntentVisuals() {
0043:     const overreachActive = selectedIntent === "Ambition Unleash" || Boolean(latestState?.me?.wants_unleash);
0044: 
0045:     document.body.classList.toggle("overreach-armed-v112", overreachActive);
```

### static/js/game.js:38
```text
0034:     const me = state?.me || {};
0035:     const enemy = state?.enemy || {};
0036: 
0037:     setElementClass("my-ready", "ready-pill-v112", Boolean(me.ready));
0038:     setElementClass("enemy-ready", "ready-pill-v112", Boolean(enemy.ready));
0039:     setElementClass("ready-btn", "ready-btn-active-v112", Boolean(me.ready));
0040: }
0041: 
0042: function updateIntentVisuals() {
0043:     const overreachActive = selectedIntent === "Ambition Unleash" || Boolean(latestState?.me?.wants_unleash);
0044: 
0045:     document.body.classList.toggle("overreach-armed-v112", overreachActive);
0046: 
```

### static/js/game.js:39
```text
0035:     const enemy = state?.enemy || {};
0036: 
0037:     setElementClass("my-ready", "ready-pill-v112", Boolean(me.ready));
0038:     setElementClass("enemy-ready", "ready-pill-v112", Boolean(enemy.ready));
0039:     setElementClass("ready-btn", "ready-btn-active-v112", Boolean(me.ready));
0040: }
0041: 
0042: function updateIntentVisuals() {
0043:     const overreachActive = selectedIntent === "Ambition Unleash" || Boolean(latestState?.me?.wants_unleash);
0044: 
0045:     document.body.classList.toggle("overreach-armed-v112", overreachActive);
0046: 
0047:     DOM.qsa(".intent-btn-v103").forEach((button) => {
```

### static/js/game.js:67
```text
0063:     const cost = Number(card?.cost || 0);
0064:     const type = String(card?.type || "");
0065:     const monsterOccupied = Boolean(me.field_m);
0066:     const spellTrapOccupied = Boolean(me.field_st);
0067:     const lockedByState = Boolean(me.ready || state?.resolving);
0068:     const zoneBlocked = (type === "Monster" && monsterOccupied) || (["Spell", "Trap"].includes(type) && spellTrapOccupied);
0069: 
0070:     return {
0071:         playable: !lockedByState && !zoneBlocked && cost <= energy,
0072:         cost,
0073:         type,
0074:         zoneBlocked,
0075:         canAfford: cost <= energy,
```

### static/js/game.js:174
```text
0170: 
0171: function setArenaButtonState(state) {
0172:     const hasBattle = Boolean(state?.room_id);
0173:     const me = state?.me || {};
0174:     const lockedByBattle = Boolean(state?.resolving || me.ready);
0175:     const readyButton = DOM.byId("ready-btn");
0176:     const canUnleash = canUseAmbitionUnleash(state);
0177: 
0178:     DOM.qsa(".intent-btn-v103").forEach((button) => {
0179:         const isUnleash = button.dataset.intent === "Ambition Unleash";
0180:         button.disabled = !hasBattle || lockedByBattle || (isUnleash && !canUnleash);
0181:         button.title = isUnleash && !canUnleash
0182:             ? "Needs 5 Ambition and a monster in play"
```

### static/js/game.js:175
```text
0171: function setArenaButtonState(state) {
0172:     const hasBattle = Boolean(state?.room_id);
0173:     const me = state?.me || {};
0174:     const lockedByBattle = Boolean(state?.resolving || me.ready);
0175:     const readyButton = DOM.byId("ready-btn");
0176:     const canUnleash = canUseAmbitionUnleash(state);
0177: 
0178:     DOM.qsa(".intent-btn-v103").forEach((button) => {
0179:         const isUnleash = button.dataset.intent === "Ambition Unleash";
0180:         button.disabled = !hasBattle || lockedByBattle || (isUnleash && !canUnleash);
0181:         button.title = isUnleash && !canUnleash
0182:             ? "Needs 5 Ambition and a monster in play"
0183:             : "";
```

### static/js/game.js:186
```text
0182:             ? "Needs 5 Ambition and a monster in play"
0183:             : "";
0184:     });
0185: 
0186:     if (readyButton) {
0187:         readyButton.disabled = !hasBattle || lockedByBattle;
0188:     }
0189: }
0190: 
0191: function updateArenaEaseState(state) {
0192:     const body = document.body;
0193: 
0194:     if (!body) {
```

### static/js/game.js:187
```text
0183:             : "";
0184:     });
0185: 
0186:     if (readyButton) {
0187:         readyButton.disabled = !hasBattle || lockedByBattle;
0188:     }
0189: }
0190: 
0191: function updateArenaEaseState(state) {
0192:     const body = document.body;
0193: 
0194:     if (!body) {
0195:         return;
```

### static/js/game.js:204
```text
0200:     const enemy = state?.enemy || {};
0201:     const recommended = hasBattle ? findRecommendedPlayableCard(state) : null;
0202:     const playableCard = Boolean(recommended);
0203:     const canUnleash = hasBattle && canUseAmbitionUnleash(state);
0204:     const needsReady = hasBattle && !state?.resolving && !me.ready;
0205: 
0206:     body.classList.toggle("arena-has-match-v152", hasBattle);
0207:     body.classList.toggle("arena-needs-match-v152", !hasBattle);
0208:     body.classList.toggle("arena-needs-card-v152", playableCard);
0209:     body.classList.toggle("arena-needs-ready-v152", needsReady && !playableCard);
0210:     body.classList.toggle("arena-waiting-v152", Boolean(hasBattle && me.ready && !state?.resolving));
0211:     body.classList.toggle("arena-resolving-v152", Boolean(state?.resolving));
0212: 
```

### static/js/game.js:209
```text
0205: 
0206:     body.classList.toggle("arena-has-match-v152", hasBattle);
0207:     body.classList.toggle("arena-needs-match-v152", !hasBattle);
0208:     body.classList.toggle("arena-needs-card-v152", playableCard);
0209:     body.classList.toggle("arena-needs-ready-v152", needsReady && !playableCard);
0210:     body.classList.toggle("arena-waiting-v152", Boolean(hasBattle && me.ready && !state?.resolving));
0211:     body.classList.toggle("arena-resolving-v152", Boolean(state?.resolving));
0212: 
0213:     if (!hasBattle) {
0214:         DOM.setText("arena-action-hint", "Start a duel to draw your hand.");
0215:     } else if (state?.resolving) {
0216:         DOM.setText("arena-action-hint", "Round resolving. Watch the Battle Log.");
0217:     } else if (me.ready) {
```

### static/js/game.js:210
```text
0206:     body.classList.toggle("arena-has-match-v152", hasBattle);
0207:     body.classList.toggle("arena-needs-match-v152", !hasBattle);
0208:     body.classList.toggle("arena-needs-card-v152", playableCard);
0209:     body.classList.toggle("arena-needs-ready-v152", needsReady && !playableCard);
0210:     body.classList.toggle("arena-waiting-v152", Boolean(hasBattle && me.ready && !state?.resolving));
0211:     body.classList.toggle("arena-resolving-v152", Boolean(state?.resolving));
0212: 
0213:     if (!hasBattle) {
0214:         DOM.setText("arena-action-hint", "Start a duel to draw your hand.");
0215:     } else if (state?.resolving) {
0216:         DOM.setText("arena-action-hint", "Round resolving. Watch the Battle Log.");
0217:     } else if (me.ready) {
0218:         DOM.setText("arena-action-hint", "Ready locked. Waiting for the round.");
```

### static/js/game.js:217
```text
0213:     if (!hasBattle) {
0214:         DOM.setText("arena-action-hint", "Start a duel to draw your hand.");
0215:     } else if (state?.resolving) {
0216:         DOM.setText("arena-action-hint", "Round resolving. Watch the Battle Log.");
0217:     } else if (me.ready) {
0218:         DOM.setText("arena-action-hint", "Ready locked. Waiting for the round.");
0219:     } else if (playableCard) {
0220:         DOM.setText("arena-action-hint", `Best play: ${recommended.card?.name || "play a card"}, then press Ready.`);
0221:     } else if (canUnleash) {
0222:         DOM.setText("arena-action-hint", "Ambition Unleash is ready, or choose intent and press Ready.");
0223:     } else {
0224:         DOM.setText("arena-action-hint", "Choose intent, then press Ready.");
0225:     }
```

### static/js/game.js:222
```text
0218:         DOM.setText("arena-action-hint", "Ready locked. Waiting for the round.");
0219:     } else if (playableCard) {
0220:         DOM.setText("arena-action-hint", `Best play: ${recommended.card?.name || "play a card"}, then press Ready.`);
0221:     } else if (canUnleash) {
0222:         DOM.setText("arena-action-hint", "Ambition Unleash is ready, or choose intent and press Ready.");
0223:     } else {
0224:         DOM.setText("arena-action-hint", "Choose intent, then press Ready.");
0225:     }
0226: 
0227:     DOM.setText("my-field-status", me.ready ? "Ready" : (playableCard ? "Play a card" : "Choose intent"));
0228:     DOM.setText("enemy-field-status", enemy.ready ? "Ready" : (hasBattle ? "Choosing" : "Waiting"));
0229:     setArenaButtonState(state);
0230: }
```

### static/js/game.js:227
```text
0223:     } else {
0224:         DOM.setText("arena-action-hint", "Choose intent, then press Ready.");
0225:     }
0226: 
0227:     DOM.setText("my-field-status", me.ready ? "Ready" : (playableCard ? "Play a card" : "Choose intent"));
0228:     DOM.setText("enemy-field-status", enemy.ready ? "Ready" : (hasBattle ? "Choosing" : "Waiting"));
0229:     setArenaButtonState(state);
0230: }
0231: 
0232: function normalizeBattleLogMessage(message) {
0233:     const text = String(message || "Battle event.");
0234: 
0235:     if (text.toLowerCase().includes("overreach")) {
```

### static/js/game.js:228
```text
0224:         DOM.setText("arena-action-hint", "Choose intent, then press Ready.");
0225:     }
0226: 
0227:     DOM.setText("my-field-status", me.ready ? "Ready" : (playableCard ? "Play a card" : "Choose intent"));
0228:     DOM.setText("enemy-field-status", enemy.ready ? "Ready" : (hasBattle ? "Choosing" : "Waiting"));
0229:     setArenaButtonState(state);
0230: }
0231: 
0232: function normalizeBattleLogMessage(message) {
0233:     const text = String(message || "Battle event.");
0234: 
0235:     if (text.toLowerCase().includes("overreach")) {
0236:         return "⚠ OVERREACH: " + text;
```

### static/js/game.js:239
```text
0235:     if (text.toLowerCase().includes("overreach")) {
0236:         return "⚠ OVERREACH: " + text;
0237:     }
0238: 
0239:     if (text.toLowerCase().includes("ready")) {
0240:         return "READY: " + text;
0241:     }
0242: 
0243:     if (text.toLowerCase().includes("damage")) {
0244:         return "DAMAGE: " + text;
0245:     }
0246: 
0247:     if (text.toLowerCase().includes("heal")) {
```

### static/js/game.js:377
```text
0373:     DOM.setText("my-ambition", me.wants_unleash ? `${me.ambition ?? 0} armed` : `${me.ambition ?? 0}`);
0374:     DOM.setText("my-intent", me.wants_unleash ? "Unleash" : (me.intent || "Strike"));
0375:     DOM.setText("my-deck", me.deck_count ?? 0);
0376:     DOM.setText("my-gy", me.graveyard_count ?? 0);
0377:     DOM.setText("my-ready", me.ready ? "Yes" : "No");
0378: 
0379:     DOM.setText("enemy-name", enemy.name || "Opponent");
0380:     DOM.setText("enemy-hp", enemy.hp ?? 3600);
0381:     DOM.setText("enemy-energy", `${enemy.energy ?? 0}/${enemy.max_energy ?? 0}`);
0382:     DOM.setText("enemy-ambition", enemy.wants_unleash ? `${enemy.ambition ?? 0} armed` : `${enemy.ambition ?? 0}`);
0383:     DOM.setText("enemy-intent", enemy.intent || "Hidden");
0384:     DOM.setText("enemy-deck", enemy.deck_count ?? 0);
0385:     DOM.setText("enemy-hand", enemy.hand_count ?? 0);
```

### static/js/game.js:386
```text
0382:     DOM.setText("enemy-ambition", enemy.wants_unleash ? `${enemy.ambition ?? 0} armed` : `${enemy.ambition ?? 0}`);
0383:     DOM.setText("enemy-intent", enemy.intent || "Hidden");
0384:     DOM.setText("enemy-deck", enemy.deck_count ?? 0);
0385:     DOM.setText("enemy-hand", enemy.hand_count ?? 0);
0386:     DOM.setText("enemy-ready", enemy.ready ? "Yes" : "No");
0387: }
0388: 
0389: function renderField(state) {
0390:     const me = state.me || {};
0391:     const enemy = state.enemy || {};
0392: 
0393:     DOM.setHtml("my-monster-slot", renderCard(me.field_m, { emptyText: "Empty Monster Zone" }));
0394:     DOM.setHtml("my-st-slot", renderCard(me.field_st, { emptyText: "Empty Spell/Trap Zone" }));
```

### static/js/game.js:439
```text
0435:             ? recommendedPlay
0436:                 ? `Recommended: play ${card?.name || "card"}`
0437:                 : `Play ${card?.name || "card"}`
0438:             : status.zoneBlocked
0439:                 ? "Zone already occupied"
0440:                 : status.canAfford
0441:                     ? "Wait until your next action"
0442:                     : `Needs ${status.cost} energy`;
0443:         wrapper.innerHTML = renderCard(card);
0444: 
0445:         wrapper.addEventListener("click", () => {
0446:             if (!playable) {
0447:                 return;
```

### static/js/game.js:586
```text
0582:         if (shouldLog) {
0583:             logLine("Ambition Unleash selected. Commit only when the reward is worth the exposure.");
0584:         }
0585:     } else {
0586:         socket.emit("set_intent", { intent: selectedIntent });
0587:         if (shouldLog) {
0588:             logLine(`Intent selected: ${selectedIntent}`);
0589:         }
0590:     }
0591: }
0592: 
0593: function bootArenaControls() {
0594:     DOM.qsa(".intent-btn-v103").forEach((button) => {
```

### static/js/game.js:615
```text
0611:             socket.emit("join_queue");
0612:         }
0613:     });
0614: 
0615:     DOM.onClick("ready-btn", () => {
0616:         socket.emit("declare_ready");
0617:         setQueueStatus("Ready declared. Waiting for battle resolution.");
0618:         logLine("Ready declared.");
0619:     });
0620: 
0621: 
0622:     DOM.onClick("join-private-room-btn", () => {
0623:         const input = DOM.byId("private-room-code");
```

### static/js/game.js:616
```text
0612:         }
0613:     });
0614: 
0615:     DOM.onClick("ready-btn", () => {
0616:         socket.emit("declare_ready");
0617:         setQueueStatus("Ready declared. Waiting for battle resolution.");
0618:         logLine("Ready declared.");
0619:     });
0620: 
0621: 
0622:     DOM.onClick("join-private-room-btn", () => {
0623:         const input = DOM.byId("private-room-code");
0624:         const code = String(input?.value || "").trim().toUpperCase().replace(/\s+/g, "");
```

### static/js/game.js:735
```text
0731: socket.on("presence_update", (data) => {
0732:     updatePresence(data);
0733: });
0734: 
0735: socket.on("game_state_update", (state) => {
0736:     renderState(state);
0737: });
0738: 
0739: socket.on("battle_events", (events) => {
0740:     window.dispatchEvent(new CustomEvent("ambition:battle_events", { detail: events || [] }));
0741: });
0742: 
0743: socket.on("battle_log", (data) => {
```

### templates/arena.html:81
```text
0077: 
0078:             <div class="az-v4-mini-stats">
0079:                 <span>Deck <strong id="my-deck">30</strong></span>
0080:                 <span>GY <strong id="my-graveyard">0</strong></span>
0081:                 <span>Ready <strong id="my-ready">No</strong></span>
0082:             </div>
0083:         </section>
0084: 
0085:         <section class="az-v4-board">
0086:             <div class="az-v4-field az-v4-enemy-field">
0087:                 <div class="az-v4-field-head">
0088:                     <h2>Enemy Field</h2>
0089:                     <span id="enemy-ready">Ready No</span>
```

### templates/arena.html:89
```text
0085:         <section class="az-v4-board">
0086:             <div class="az-v4-field az-v4-enemy-field">
0087:                 <div class="az-v4-field-head">
0088:                     <h2>Enemy Field</h2>
0089:                     <span id="enemy-ready">Ready No</span>
0090:                 </div>
0091: 
0092:                 <div class="az-v4-zones">
0093:                     <article class="az-v4-zone">
0094:                         <span>Monster</span>
0095:                         <div id="enemy-monster-zone" class="az-v4-zone-slot">Hidden</div>
0096:                     </article>
0097: 
```

### templates/arena.html:181
```text
0177:                     <small>Risk</small>
0178:                 </button>
0179:             </div>
0180: 
0181:             <button id="ready-btn" type="button" class="az-v4-ready-btn">
0182:                 {% if training_mode %}Start Training{% else %}Ready{% endif %}
0183:             </button>
0184: 
0185:             <div id="connection-status" class="az-v4-connection">Connecting...</div>
0186:         </section>
0187: 
0188:         <details class="az-v4-log-panel">
0189:             <summary>Battle Log</summary>
```

### templates/arena.html:220
```text
0216:                 Focus
0217:                 <small>Build</small>
0218:             </button>
0219: 
0220:             <button type="button" class="az-v4-dock-btn az-v4-dock-ready" data-v4-click="Ready">
0221:                 Ready
0222:                 <small>Commit</small>
0223:             </button>
0224:         </nav>
0225:     </main>
0226: 
0227:     <script>
0228:         window.AMBITIONZ_TRAINING_MODE = {{ "true" if training_mode else "false" }};
```

## Target Fullstack Contract

```json
{
  "schema": "ambitionz_match_v1",
  "match_id": "string",
  "mode": "training|pvp|bot",
  "round": "number",
  "phase": "draw|intent|main|ready|resolve|finished",
  "me": {
    "hp": "number",
    "energy": "number",
    "max_energy": "number",
    "ambition": "number",
    "intent": "Strike|Guard|Focus|null",
    "ready": "boolean",
    "hand": "card[]",
    "field": {
      "monster": "card|null",
      "spell": "card|null",
      "trap": "card|null"
    },
    "deck_count": "number",
    "graveyard_count": "number"
  },
  "enemy": {
    "hp": "number",
    "energy": "number",
    "max_energy": "number",
    "ambition": "number",
    "intent": "hidden|revealed",
    "ready": "boolean",
    "hand_count": "number",
    "field": {
      "monster": "card|null",
      "spell": "card|null",
      "trap": "card|null"
    }
  },
  "legal_actions": {
    "can_choose_intent": "boolean",
    "can_play_cards": "boolean",
    "can_ready": "boolean",
    "playable_card_ids": "string[]"
  },
  "message": "string"
}
```

## Recommended Rebuild Order

1. Create `services/match_state_v1.py` as the only payload builder.
2. Add `request_match_state` socket event.
3. Emit `match_state` while keeping legacy `game_state_update` temporarily.
4. Create `static/js/arena_app.js` to render only from `match_state`.
5. Replace DOM-dependent card actions with `play_card(card_id)`.
6. Remove V5/V7/V8 overlay fallback files from Arena only after stable QA.
7. Reintroduce animations only after card movement is real.

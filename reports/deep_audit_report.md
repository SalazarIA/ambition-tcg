# Ambitionz Deep Audit Report

## Git status

```
?? tools/deep_audit.py

```

## Python compileall

Exit code: 0
```
Listing 'game'...
Listing 'services'...
Listing 'services/admin'...
Listing 'services/database'...
Listing 'services/security'...
Listing 'tools'...
Compiling 'tools/deep_audit.py'...

```

## JavaScript syntax check

- `static/js/game.js`: OK
- `static/js/mobile-native.js`: OK
- `static/js/card_ui_v103.js`: OK
- `static/js/service-worker.js`: OK
- `static/js/ambitionz_dom.js`: OK
- `static/js/ambition_battle_events.js`: OK
- `static/js/deck_builder.js`: OK
- `static/js/pwa.js`: OK
- `backups/deck_builder_v112_manual_20260503_103302/static/js/deck_builder.js`: OK
- `backups/beta_core_v111_20260503_102709/static/js/game.js`: OK
- `backups/deck_builder_v112_20260503_103121/static/js/deck_builder.js`: OK

## Flask routes

- `admin_dev_tools`: `"/admin/dev-tools"`
- `admin_test_email`: `"/admin/test-email", methods=["POST"]`
- `admin_reset_test_users`: `"/admin/reset-test-users", methods=["POST"]`
- `admin_clear_gameplay_data`: `"/admin/clear-gameplay-data", methods=["POST"]`
- `admin_system`: `"/admin/system"`
- `admin_users`: `"/admin/users"`
- `admin_toggle_admin`: `"/admin/users/<int:user_id>/toggle-admin", methods=["POST"]`
- `admin_toggle_tester`: `"/admin/users/<int:user_id>/toggle-tester", methods=["POST"]`
- `admin_verify_user`: `"/admin/users/<int:user_id>/verify", methods=["POST"]`
- `admin_ban_user`: `"/admin/users/<int:user_id>/ban", methods=["POST"]`
- `admin_unban_user`: `"/admin/users/<int:user_id>/unban", methods=["POST"]`
- `admin_invites`: `"/admin/invites", methods=["GET", "POST"]`
- `admin_beta_events`: `"/admin/beta-events"`
- `admin_feedback`: `"/admin/feedback"`
- `admin_feedback_update`: `"/admin/feedback/<int:report_id>/update", methods=["POST"]`
- `admin_release_candidate`: `"/admin/release-candidate"`
- `index`: `"/"`
- `health`: `"/health"`
- `resend_verification`: `"/resend-verification", methods=["GET", "POST"]`
- `profile`: `"/profile"`
- `ranking`: `"/ranking"`
- `how_to_play`: `"/how-to-play"`
- `forgot_password`: `"/forgot-password", methods=["GET", "POST"]`
- `reset_password`: `"/reset-password/<token>", methods=["GET", "POST"]`
- `first_session`: `"/first-session"`
- `closed_test`: `"/closed-test"`
- `beta_event`: `"/api/beta-event", methods=["POST"]`
- `terms`: `"/terms"`
- `data_deletion`: `"/data-deletion"`
- `privacy`: `"/privacy"`
- `offline`: `"/offline"`
- `register`: `"/register", methods=["GET", "POST"]`
- `confirm_email`: `"/confirm_email/<token>"`
- `login`: `"/login", methods=["GET", "POST"]`
- `logout`: `"/logout"`
- `collection`: `"/collection"`
- `shop`: `"/shop", methods=["GET", "POST"]`
- `auto_build_deck`: `"/auto-build-deck", methods=["POST"]`
- `booster_history`: `"/booster-history"`
- `deck_builder`: `"/deck-builder", methods=["GET", "POST"]`
- `arena`: `"/arena"`
- `training`: `"/training"`
- `feedback`: `"/feedback", methods=["GET", "POST"]`
- `admin_reports`: `"/admin/reports"`
- `admin_balance`: `"/admin/balance"`
- `beta_launch`: `"/beta-launch"`
- `admin`: `"/admin"`
- `complete_onboarding`: `"/complete-onboarding", methods=["POST"]`
- `missions`: `"/missions"`
- `claim_user_mission`: `"/missions/claim/<int:mission_id>", methods=["POST"]`
- `match_history`: `"/match-history"`
- `welcome`: `"/welcome"`
- `progression`: `"/progression"`

## Socket.IO handlers

- `join_training` -> `handle_join_training`
- `join_queue` -> `handle_join_queue`
- `set_intent` -> `set_intent`
- `play_to_field` -> `play_to_field`
- `choose_intent` -> `choose_intent`
- `toggle_unleash` -> `toggle_unleash`
- `declare_ready` -> `declare_ready`
- `join_bot_match` -> `handle_join_bot_match`
- `join_private_room` -> `handle_join_private_room`
- `disconnect` -> `handle_disconnect`

No duplicate socket handlers found.

## Auth/login scan

87: `login_attempts = {}`
166: `request.form.get("_csrf_token")`
192: `if getattr(user, "account_status", "active") in ["banned", "disabled"]:`
199: `user.is_verified = True`
200: `user.account_status = "active"`
278: `received = request.form.get("confirmation", "").strip()`
571: `email = request.form.get("email", "").strip().lower()`
690: `verified_users=User.query.filter_by(is_verified=True).count(),`
800: `target.account_status = "banned"`
823: `target.account_status = "active" if target.is_verified else "unverified"`
844: `max_uses = int(request.form.get("max_uses", "1") or 1)`
845: `code = request.form.get("code", "").strip().upper() or generate_invite_code()`
940: `report.status = request.form.get("status", report.status)`
1043: `verified_users = User.query.filter_by(is_verified=True).count()`
1184: `email = request.form.get("email", "").strip().lower()`
1192: `if user.is_verified:`
1408: `"status": getattr(user, "account_status", "beta"),`
1410: `"is_verified": bool(getattr(user, "is_verified", False)),`
1500: `email = request.form.get("email", "").strip().lower()`
1537: `password = request.form.get("password", "").strip()`
1641: `payload = request.get_json(silent=True) or request.form.to_dict() or {}`
1701: `username = request.form.get("username", "").strip()`
1702: `email = request.form.get("email", "").strip().lower()`
1703: `password = request.form.get("password", "").strip()`
1704: `invite_code = request.form.get("invite_code", "").strip().upper()`
1738: `account_status="unverified",`
1798: `email = request.form.get("email", "").strip().lower()`
1799: `password = request.form.get("password", "").strip()`
1800: `invite_code = request.form.get("invite_code", "").strip().upper()`
1803: `attempts = login_attempts.get(attempt_key, 0)`
1811: `if not user or not user.check_password(password):`
1812: `login_attempts[attempt_key] = attempts + 1`
1835: `if not user.is_verified:`
1846: `login_attempts.pop(attempt_key, None)`
2064: `selected_pack_key = request.form.get("pack_key") or request.args.get("pack") or "elemental"`
2193: `selected_cards = request.form.getlist("deck_cards")`
3308: `category = request.form.get("category", "general").strip() or "general"`
3309: `severity = request.form.get("severity", "normal").strip() or "normal"`
3310: `title = request.form.get("title", "").strip()`
3311: `message = request.form.get("message", "").strip()`
3312: `page_url = request.form.get("page_url", "").strip()`
3534: `verified_users = User.query.filter_by(is_verified=True).count()`

## Model scan

12: `class User(db.Model):`
20: `account_status = db.Column(db.String(40), nullable=False, default="unverified", index=True)`
27: `password_hash = db.Column(db.String(256), nullable=False)`
28: `is_verified = db.Column(db.Boolean, default=False, nullable=False)`
41: `is_admin = db.Column(db.Boolean, default=False, nullable=False)`
63: `def set_password(self, password):`
64: `self.password_hash = pbkdf2_sha256.hash(password)`
66: `def check_password(self, password):`
67: `return pbkdf2_sha256.verify(password, self.password_hash)`
175: `class UserMission(db.Model):`
230: `"ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE",`
239: `"ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0",`
400: `"ALTER TABLE users ADD COLUMN IF NOT EXISTS account_status VARCHAR(40) DEFAULT 'active' NOT NULL",`
407: `"UPDATE users SET account_status = 'active' WHERE is_verified = true AND (account_status IS NULL OR account_status = 'unverified')",`
408: `"UPDATE users SET account_status = 'unverified' WHERE is_verified = false AND account_status IS NULL",`
420: `"account_status": "account_status VARCHAR(40) DEFAULT 'active' NOT NULL",`

## Rough undefined function scan in app.py

- `abort`
- `apply_match_rewards`
- `bot_choose_play`
- `bot_play_turn`
- `build_match_summary_lines`
- `build_playable_deck`
- `can_pay_cost`
- `cancel_unleash`
- `cards_from_ids`
- `claim_mission`
- `clear_gameplay_data`
- `collection_summary`
- `create_bot_player`
- `create_player_state`
- `create_starter_deck_from_collection`
- `deck_analysis_v115`
- `deck_summary`
- `delete_non_admin_users`
- `draw_starting_hand`
- `enrich_cards_for_view`
- `ensure_daily_missions`
- `find_outliers`
- `full_deck_analysis`
- `get_card_by_id`
- `get_fixed_starter_deck_ids`
- `increment_mission`
- `is_smtp_configured`
- `is_valid_room_code`
- `join_room`
- `load_card_ids`
- `normalize_intent`
- `normalize_room_code`
- `pay_card_cost`
- `player_display_name`
- `predicate`
- `record_match_telemetry`
- `register_card_played_for_ambition`
- `request_unleash`
- `reset_player_energy`
- `resolve_battle`
- `reward_line`
- `safe_user_id`
- `send_password_reset_email`
- `send_smtp_test_email`
- `send_verification_email`
- `set_player_intent`
- `sql_inspect`
- `sql_text`
- `start_match_between_players`
- `summarize_monsters`
- `validate_deck`

## TODO/FIXME/Error strings

- `models.py:249` except Exception:
- `app.py:118` except Exception as error:
- `app.py:119` print("SYSTEM LOG ERROR:", error)
- `app.py:131` except Exception as error:
- `app.py:132` print("RC EVENT LOG ERROR:", type(error).__name__, error)
- `app.py:300` except Exception as error:
- `app.py:406` except Exception as error:
- `app.py:472` except Exception as error:
- `app.py:512` except Exception as error:
- `app.py:527` except Exception as error:
- `app.py:530` print("Error:", error)
- `app.py:584` except Exception as log_error:
- `app.py:590` except Exception as log_error:
- `app.py:593` except Exception as error:
- `app.py:596` print("Error:", error)
- `app.py:622` except Exception as error:
- `app.py:625` print("Error:", error)
- `app.py:649` except Exception as error:
- `app.py:652` print("Error:", error)
- `app.py:677` except Exception as error:
- `app.py:888` except Exception as error:
- `app.py:889` print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)
- `app.py:952` except Exception:
- `app.py:973` except Exception as error:
- `app.py:1013` except Exception as error:
- `app.py:1030` except Exception as error:
- `app.py:1052` except Exception as error:
- `app.py:1111` except Exception as error:
- `app.py:1112` print("RC FEEDBACK QUERY ERROR:", type(error).__name__, error)
- `app.py:1116` except Exception as error:
- `app.py:1117` print("RC LOG QUERY ERROR:", type(error).__name__, error)
- `app.py:1142` except Exception as error:
- `app.py:1143` db_status = f"error:{type(error).__name__}"
- `app.py:1171` except Exception as log_error:
- `app.py:1172` print("500 LOG ERROR:", type(log_error).__name__, log_error)
- `app.py:1213` except Exception as error:
- `app.py:1388` except Exception as error:
- `app.py:1389` print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
- `app.py:1439` except Exception as error:
- `app.py:1440` print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
- `app.py:1519` except Exception as error:
- `app.py:1531` except Exception:
- `app.py:1642` except Exception:
- `app.py:1666` except Exception as error:
- `app.py:1669` except Exception:
- `app.py:1671` print("BETA EVENT LOG ERROR:", type(error).__name__, error)
- `app.py:1782` except Exception:
- `app.py:1858` except Exception as error:
- `app.py:1859` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `app.py:2484` except Exception as error:
- `app.py:2485` print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)
- `app.py:2527` except Exception as error:
- `app.py:2528` print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
- `app.py:2558` except Exception as error:
- `app.py:2559` print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)
- `app.py:2797` except Exception as error:
- `app.py:2798` print("TRAINING START ERROR:", type(error).__name__, error)
- `app.py:2926` except Exception:
- `app.py:3098` except Exception as error:
- `app.py:3099` print("V2 BATTLE EVENTS EMIT ERROR:", type(error).__name__, error)
- `app.py:3351` except Exception as error:
- `app.py:3352` print("FEEDBACK LIMIT CHECK ERROR:", type(error).__name__, error)
- `app.py:3374` except Exception as error:
- `app.py:3375` print("FEEDBACK LOG ERROR:", type(error).__name__, error)
- `app.py:3507` except Exception as error:
- `app.py:3508` print("ADMIN BALANCE ERROR:", type(error).__name__, error)
- `app.py:3535` except Exception as error:
- `app.py:3580` except Exception as error:
- `app.py:3607` except Exception as error:
- `app.py:3608` print("MISSIONS PAGE ERROR:", type(error).__name__, error)
- `app.py:3636` except Exception as error:
- `app.py:3637` print("MISSION CLAIM ERROR:", type(error).__name__, error)
- `app.py:3694` except Exception as error:
- `app.py:3718` except Exception as error:
- `app.py:3719` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `app.py:3738` except Exception as error:
- `app.py:3739` print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
- `migrations/env.py:31` except AttributeError:
- `tools/audit_routes.py:43` except Exception as error:
- `tools/audit_database.py:49` except Exception as error:
- `tools/audit_database.py:52` except Exception as error:
- `tools/balance_report.py:16` except Exception:
- `tools/audit_cards.py:23` except Exception as error:
- `tools/audit_cards.py:62` except Exception:
- `tools/audit_cards.py:74` except Exception:
- `tools/fix_deck_builder_v112_manual.py:115` raise SystemExit("ERROR: old checkbox block not found exactly. No changes made.")
- `tools/deep_audit.py:30` except Exception as e:
- `tools/deep_audit.py:125` # 8. Broken references: function calls not defined in same file rough scan
- `tools/deep_audit.py:144` except Exception as e:
- `tools/deep_audit.py:147` # 9. TODO/FIXME/errors
- `tools/deep_audit.py:148` section("TODO/FIXME/Error strings")
- `tools/deep_audit.py:156` except Exception:
- `tools/deep_audit.py:160` if any(k in low for k in ["todo", "fixme", "hack", "broken", "error:", "except exception", "pass  #"]):
- `tools/deep_audit.py:179` except Exception:
- `tools/internal_rc_check.py:42` print("ERROR:", failure)
- `tools/fix_beta_core_v111.py:118` # The common broken shape has two const cost declarations close together.
- `tools/preflight.py:31` except Exception as error:
- `tools/preflight.py:38` print("ERROR:", error)
- `tools/preflight.py:70` print("ERROR:", error)
- `game/deck.py:76` except Exception:
- `game/cards.py:165` "Mastodonte Antigo",
- `game/match_utils.py:16` except Exception:
- `templates/first_session.html:67` If anything blocks the path, feels confusing, looks broken on Android,
- `backups/beta_final_stability_v113_20260503_103647/app.py:104` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:105` print("SYSTEM LOG ERROR:", error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:214` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:226` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:250` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:319` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:334` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:337` print("Error:", error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:391` except Exception as log_error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:397` except Exception as log_error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:400` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:403` print("Error:", error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:429` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:432` print("Error:", error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:456` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:459` print("Error:", error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:484` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:695` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:696` print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:805` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:980` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:981` print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:1031` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:1032` print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:1111` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:1123` except Exception:
- `backups/beta_final_stability_v113_20260503_103647/app.py:1234` except Exception:
- `backups/beta_final_stability_v113_20260503_103647/app.py:1258` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:1261` except Exception:
- `backups/beta_final_stability_v113_20260503_103647/app.py:1263` print("BETA EVENT LOG ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:1356` except Exception:
- `backups/beta_final_stability_v113_20260503_103647/app.py:1410` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:1411` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:1922` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:1923` print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:1965` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:1966` print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:1996` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:1997` print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:2162` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:2163` print("TRAINING START ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:2304` except Exception:
- `backups/beta_final_stability_v113_20260503_103647/app.py:2708` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:2709` print("FEEDBACK LOG ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:2841` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:2842` print("ADMIN BALANCE ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:2869` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:2913` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:2940` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:2941` print("MISSIONS PAGE ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:2969` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:2970` print("MISSION CLAIM ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:3027` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:3051` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:3052` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `backups/beta_final_stability_v113_20260503_103647/app.py:3071` except Exception as error:
- `backups/beta_final_stability_v113_20260503_103647/app.py:3072` print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:104` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:105` print("SYSTEM LOG ERROR:", error)
- `backups/beta_core_v111_20260503_102709/app.py:214` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:226` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:250` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:319` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:334` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:337` print("Error:", error)
- `backups/beta_core_v111_20260503_102709/app.py:391` except Exception as log_error:
- `backups/beta_core_v111_20260503_102709/app.py:397` except Exception as log_error:
- `backups/beta_core_v111_20260503_102709/app.py:400` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:403` print("Error:", error)
- `backups/beta_core_v111_20260503_102709/app.py:429` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:432` print("Error:", error)
- `backups/beta_core_v111_20260503_102709/app.py:456` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:459` print("Error:", error)
- `backups/beta_core_v111_20260503_102709/app.py:484` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:695` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:696` print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:805` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:980` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:981` print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:1031` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:1032` print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:1111` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:1123` except Exception:
- `backups/beta_core_v111_20260503_102709/app.py:1234` except Exception:
- `backups/beta_core_v111_20260503_102709/app.py:1258` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:1261` except Exception:
- `backups/beta_core_v111_20260503_102709/app.py:1263` print("BETA EVENT LOG ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:1356` except Exception:
- `backups/beta_core_v111_20260503_102709/app.py:1410` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:1411` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:1922` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:1923` print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:1965` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:1966` print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:1996` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:1997` print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:2162` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:2163` print("TRAINING START ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:2304` except Exception:
- `backups/beta_core_v111_20260503_102709/app.py:2708` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:2709` print("FEEDBACK LOG ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:2841` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:2842` print("ADMIN BALANCE ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:2869` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:2913` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:2940` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:2941` print("MISSIONS PAGE ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:2969` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:2970` print("MISSION CLAIM ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:3027` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:3051` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:3052` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `backups/beta_core_v111_20260503_102709/app.py:3071` except Exception as error:
- `backups/beta_core_v111_20260503_102709/app.py:3072` print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:104` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:105` print("SYSTEM LOG ERROR:", error)
- `backups/email_delivery_v114_20260503_104855/app.py:214` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:320` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:344` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:413` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:428` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:431` print("Error:", error)
- `backups/email_delivery_v114_20260503_104855/app.py:485` except Exception as log_error:
- `backups/email_delivery_v114_20260503_104855/app.py:491` except Exception as log_error:
- `backups/email_delivery_v114_20260503_104855/app.py:494` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:497` print("Error:", error)
- `backups/email_delivery_v114_20260503_104855/app.py:523` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:526` print("Error:", error)
- `backups/email_delivery_v114_20260503_104855/app.py:550` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:553` print("Error:", error)
- `backups/email_delivery_v114_20260503_104855/app.py:578` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:789` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:790` print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:899` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:1074` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:1075` print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:1125` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:1126` print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:1205` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:1217` except Exception:
- `backups/email_delivery_v114_20260503_104855/app.py:1328` except Exception:
- `backups/email_delivery_v114_20260503_104855/app.py:1352` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:1355` except Exception:
- `backups/email_delivery_v114_20260503_104855/app.py:1357` print("BETA EVENT LOG ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:1450` except Exception:
- `backups/email_delivery_v114_20260503_104855/app.py:1504` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:1505` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:2016` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:2017` print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:2059` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:2060` print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:2090` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:2091` print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:2256` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:2257` print("TRAINING START ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:2398` except Exception:
- `backups/email_delivery_v114_20260503_104855/app.py:2802` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:2803` print("FEEDBACK LOG ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:2935` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:2936` print("ADMIN BALANCE ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:2963` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:3007` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:3034` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:3035` print("MISSIONS PAGE ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:3063` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:3064` print("MISSION CLAIM ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:3121` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:3145` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:3146` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/app.py:3165` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/app.py:3166` print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
- `backups/email_delivery_v114_20260503_104855/services/email_service.py:58` except Exception as error:
- `backups/email_delivery_v114_20260503_104855/services/email_service.py:61` print("Error:", error)
- `routes/auth.py:68` except Exception as error:
- `routes/auth.py:69` print("LOGIN TRACKING ERROR:", type(error).__name__, error)
- `routes/auth.py:75` except Exception as error:
- `routes/auth.py:76` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `routes/auth.py:134` except Exception as error:
- `routes/auth.py:135` print("STARTER DECK CREATE ERROR:", type(error).__name__, error)
- `routes/auth.py:180` except Exception:
- `routes/auth.py:187` except Exception:
- `routes/auth.py:253` except Exception:
- `routes/public.py:61` except Exception as error:
- `routes/public.py:76` except Exception as error:
- `routes/public.py:77` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `routes/public.py:93` except Exception as error:
- `routes/public.py:116` except Exception as error:
- `routes/game.py:17` except Exception:
- `routes/game.py:74` except Exception as error:
- `routes/game.py:96` except Exception as error:
- `routes/game.py:120` except Exception as error:
- `routes/game.py:175` except Exception as error:
- `routes/game.py:185` except Exception as error:
- `routes/game.py:206` except Exception as error:
- `routes/game.py:212` except Exception as error:
- `routes/game.py:218` except Exception as error:
- `routes/game.py:270` except Exception as error:
- `routes/admin.py:44` except Exception as error:
- `routes/admin.py:50` except Exception as error:
- `routes/admin.py:56` except Exception as error:
- `routes/admin.py:80` except Exception as error:
- `routes/admin.py:97` except Exception as error:
- `routes/admin.py:120` except Exception as error:
- `routes/admin.py:137` except Exception as error:
- `services/match_telemetry.py:8` except Exception:
- `services/match_telemetry.py:19` except Exception:
- `services/match_telemetry.py:56` except Exception as error:
- `services/match_telemetry.py:57` print("MATCH TELEMETRY ERROR:", type(error).__name__, error)
- `services/battle_summary.py:8` except Exception:
- `services/email_service.py:62` except Exception as error:
- `services/email_service.py:65` print("Error:", error)
- `services/database/schema_tools.py:12` except Exception as error:
- `services/database/schema_tools.py:34` except Exception as error:
- `services/database/schema_tools.py:46` except Exception as error:

## Security quick scan

- Secret key: `config.py:60`
- Email body logging: `app.py:210`
- Secret key: `tools/audit_config.py:34`
- Email body logging: `tools/deep_audit.py:170`
- CORS wildcard: `backups/beta_final_stability_v113_20260503_103647/app.py:66`
- CORS wildcard: `backups/beta_core_v111_20260503_102709/app.py:66`
- CORS wildcard: `backups/email_delivery_v114_20260503_104855/app.py:66`
- Email body logging: `routes/auth.py:36`
- Email body logging: `services/email_service.py:38`
- Email body logging: `services/email_service.py:75`

## Existing project checks

### /Users/lucassilverio/Desktop/Ambition/.venv/bin/python3 tools/preflight.py
Exit code: 0
```
\n========================================================================
FILES
========================================================================
FILE OK: app.py
FILE OK: models.py
FILE OK: config.py
FILE OK: services/email_service.py
FILE OK: templates/index.html
FILE OK: templates/login.html
FILE OK: templates/register.html
FILE OK: templates/arena.html
FILE OK: templates/admin_dev_tools.html
FILE OK: templates/terms.html
FILE OK: templates/privacy.html
FILE OK: templates/data_deletion.html
FILE OK: templates/closed_test.html
FILE OK: templates/first_session.html
FILE OK: templates/beta_launch.html
FILE OK: templates/admin.html
FILE OK: templates/booster_history.html
FILE OK: templates/shop.html
FILE OK: templates/deck_builder.html
FILE OK: templates/how_to_play.html
FILE OK: templates/welcome.html
FILE OK: templates/profile.html
FILE OK: templates/feedback.html
FILE OK: static/css/style.css
FILE OK: static/js/game.js
FILE OK: static/js/card_ui_v103.js
FILE OK: static/js/ambitionz_dom.js
FILE OK: services/admin/cleanup_service.py
FILE OK: services/security/admin_security.py
FILE OK: services/database/schema_tools.py
FILE OK: services/match_telemetry.py
FILE OK: tools/match_telemetry_report.py
FILE OK: services/battle_summary.py
FILE OK: services/reward_tuning.py
FILE OK: tools/rewards_report.py
FILE OK: routes/__init__.py
FILE OK: routes/public.py
FILE OK: routes/auth.py
FILE OK: routes/admin.py
FILE OK: routes/game.py
FILE OK: sockets/__init__.py
FILE OK: sockets/game_socket.py
FILE OK: docs/DATABASE_MIGRATIONS.md
FILE OK: game/card_identity.py
FILE OK: tools/card_identity_report.py
FILE OK: game/progression_loop.py
FILE OK: tools/progression_loop_report.py
FILE OK: game/card_identity_applied.py
FILE OK: tools/applied_card_identity_report.py
FILE OK: templates/progression.html
FILE OK: templates/admin_reports.html
FILE OK: templates/admin_balance.html
FILE OK: templates/admin_beta_events.html
FILE OK: static/manifest.webmanifest
FILES: OK
\n========================================================================
CONFIG
========================================================================
ENVIRONMENT: development
DEBUG_MODE: False
DATABASE URI PREFIX: sqlite
PRODUCTION MODE: False
WTF_CSRF_ENABLED: True
SOCKETIO_CORS_EFFECTIVE_ORIGINS: ['http://127.0.0.1:5000', 'http://127.0.0.1:8080', 'http://localhost:5000', 'http://localhost:8080']
SMTP_HOST configured: False
SMTP_USERNAME configured: False
SMTP_PASSWORD configured: False
MAIL_FROM configured: True
DEV_TOOLS_ENABLED: False
CONFIG WARNINGS:
- SECRET_KEY is weak/default locally. Acceptable for local dev, not for production.
- SMTP incomplete locally. Missing: ['SMTP_HOST', 'SMTP_USERNAME', 'SMTP_PASSWORD']
CONFIG: OK
\n========================================================================
DATABASE
========================================================================
DATABASE TABLES: ['alembic_version', 'beta_invites', 'booster_history', 'card_stats', 'feedback_reports', 'match_history', 'match_telemetry', 'system_logs', 'user', 'user_missions', 'users']
USERS TOTAL: 4
DATABASE: OK
\n========================================================================
ROUTES
========================================================================
ROUTE /: 200 
ROUTE /health: 200 
ROUTE /login: 200 
ROUTE /register: 200 
ROUTE /resend-verification: 200 
ROUTE /forgot-password: 200 
ROUTE /how-to-play: 200 
ROUTE /ranking: 200 
ROUTE /terms: 200 
ROUTE /privacy: 200 
ROUTE /offline: 200 
ROUTE /training: 302 /login
ROUTE /arena: 302 /login
ROUTE /collection: 302 /login
ROUTE /deck-builder: 302 /login
ROUTE /shop: 302 /login
ROUTE /admin: 302 /login
ROUTE /admin/dev-tools: 302 /login
ROUTE /admin/system: 302 /login
ROUTE /admin/release-candidate: 302 /login
ROUTE /admin/users: 302 /login
ROUTES: OK
\n========================================================================
TEMPLATE ENDPOINTS
========================================================================
REGISTERED ENDPOINTS: 54
CALLED ENDPOINTS: ['admin', 'admin_balance', 'admin_ban_user', 'admin_beta_events', 'admin_dev_tools', 'admin_feedback', 'admin_feedback_update', 'admin_invites', 'admin_release_candidate', 'admin_reports', 'admin_system', 'admin_toggle_admin', 'admin_toggle_tester', 'admin_unban_user', 'admin_users', 'admin_verify_user', 'arena', 'beta_launch', 'booster_history', 'claim_user_mission', 'closed_test', 'collection', 'complete_onboarding', 'data_deletion', 'deck_builder', 'feedback', 'first_session', 'forgot_password', 'how_to_play', 'index', 'login', 'logout', 'match_history', 'missions', 'privacy', 'profile', 'progression', 'ranking', 'register', 'resend_verification', 'shop', 'terms', 'training']
MISSING ENDPOINTS: []
TEMPLATE ENDPOINTS: OK
\n========================================================================
INTERNAL RC
========================================================================
INTERNAL RC STATUS: READY
REQUIRED OK: True
RECOMMENDED OK: False
OK: Database responds [required] - Database query OK
FAIL: Email delivery configured [recommended] - SMTP missing or incomplete
OK: Critical routes do not 500 [required] - /=200, /health=200, /login=200, /register=200, /training=302, /arena=302, /feedback=302, /missions=302, /shop=302
OK: No open critical feedback [required] - 0 open critical reports
FAIL: No unresolved runtime errors [recommended] - 1 unresolved error logs
OK: Tester accounts exist [recommended] - 4 total users, 4 verified
OK: Match history records exist [recommended] - 8 saved matches
FAIL: Recent match length is readable [recommended] - 1.6 average rounds over recent matches
INTERNAL RC: OK
\n========================================================================
CARDS
========================================================================
CARDS TOTAL: 250
CARD IDS UNIQUE: 250
CARDS: OK
\n========================================================================
BALANCE REPORT
========================================================================
Balance report written to reports/balance_report_v105.md
# Ambitionz V1.08 Balance Report

## Catalog Summary

- Total cards: 250
- Monster summary: {'count': 200, 'min': 1017, 'max': 2056, 'avg': 1551.1, 'median': 1567.5}

### Type Distribution

- Monster: 200
- Spell: 30
- Trap: 20

### Element Distribution

- Fire: 50
- Water: 50
- Earth: 50
- Plant: 50
- Global: 50

### Sigil Distribution

- Fury: 50
- Insight: 50
- Resolve: 50
- Harmony: 50
- Global: 50

### Rarity Distribution

- Common: 192
- Uncommon: 58


## Starter/Beta Deck Summary

- Starter deck IDs: 30
- Starter deck cards found: 30
- Missing starter IDs: []
- Monster summary: {'count': 21, 'min': 1288, 'max': 1988, 'avg': 1603.5, 'median': 1577}

### Starter Type Distribution

- Monster: 21
- Spell: 6
- Trap: 3

### Starter Element Distribution

- Global: 9
- Fire: 6
- Earth: 5
- Water: 5
- Plant: 5

### Starter Sigil Distribution

- Global: 9
- Fury: 6
- Resolve: 5
- Insight: 5
- Harmony: 5

### Starter Rarity Distribution

- Common: 18
- Uncommon: 12


## Catalog Outliers

- **Fada do Bosque** `plant_005` score=1085.0 cost=1 power=1085 sigil=Harmony rarity=Common reasons=high power per cost
- **Serpente Abissal** `water_002` score=1084.0 cost=1 power=1084 sigil=Insight rarity=Common reasons=high power per cost
- **Guardiao das Mares** `water_001` score=1067.0 cost=1 power=1067 sigil=Insight rarity=Common reasons=high power per cost
- **Ent Florido** `plant_003` score=1051.0 cost=1 power=1051 sigil=Harmony rarity=Common reasons=high power per cost
- **Lobo Espinheiro** `plant_002` score=1034.0 cost=1 power=1034 sigil=Harmony rarity=Common reasons=high power per cost
- **Druida das Raizes** `plant_001` score=1017.0 cost=1 power=1017 sigil=Harmony rarity=Common reasons=high power per cost

## Starter Deck Outliers

- No major starter deck outliers detected.

BALANCE REPORT: OK
\n========================================================================
MATCH TELEMETRY REPORT
========================================================================
MATCH TELEMETRY REPORT: OK
\n========================================================================
REWARDS REPORT
========================================================================
Rewards report written to reports/rewards_report_v105.md
# Ambitionz V1.05 Rewards Report

## Reward Table

### PVP

- win: 80 coins / 120 XP
- loss: 25 coins / 45 XP
- draw: 40 coins / 70 XP

### TRAINING

- win: 35 coins / 70 XP
- loss: 15 coins / 35 XP
- draw: 20 coins / 45 XP

## Training Difficulty Multipliers

- easy: x0.85 | win=30 coins/60 XP | loss=13 coins/30 XP
- normal: x1.0 | win=35 coins/70 XP | loss=15 coins/35 XP
- hard: x1.25 | win=44 coins/88 XP | loss=19 coins/44 XP

## Design Notes

- PvP rewards are intentionally higher than training rewards.
- Training rewards scale with difficulty.
- Loss rewards still grant progression to reduce early churn.
- This report defines the reward baseline for later admin/balance tuning.

REWARDS REPORT: OK
\n========================================================================
CARD IDENTITY REPORT
========================================================================
Card identity report written to reports/card_identity_report_v106.md
# Ambitionz V1.06 Card Identity Report

- Version: Ambitionz V1.06 Card Identity Pack

## Element Identities

### Fire

- Fantasy: pressure, burst, ambition and aggressive tempo
- Mechanical focus: damage spikes, attack pressure, Overreach payoff
- Naming style: volcanic, solar, furious, royal, explosive
- Lore direction: Fire cards are born from players who choose action before certainty.

### Water

- Fantasy: adaptation, flow, patience and tactical recovery
- Mechanical focus: healing, draw smoothing, flexible defense, tempo reset
- Naming style: tide, mirror, abyss, rain, moon, current
- Lore direction: Water cards reward players who bend without breaking.

### Earth

- Fantasy: endurance, structure, protection and inevitability
- Mechanical focus: guard value, durability, stable board presence, comeback defense
- Naming style: stone, iron, mountain, root, fortress, relic
- Lore direction: Earth cards turn patience into pressure.

### Plant

- Fantasy: growth, synergy, sustain and delayed advantage
- Mechanical focus: combo growth, healing, board cohesion, scaling rewards
- Naming style: bloom, thorn, seed, grove, vine, ancient forest
- Lore direction: Plant cards are weakest alone and dangerous together.

### Global

- Fantasy: neutral ambition, utility and universal tactics
- Mechanical focus: flexible tools, low complexity support, tutorial-friendly cards
- Naming style: oath, pact, emblem, tactic, signal, ambition
- Lore direction: Global cards carry the rules of Ambitionz itself.

## Archetypes

### Blaze Rush

- Elements: Fire
- Sigils: Fury
- Style: fast pressure and decisive Overreach turns
- Risk: runs out of stability if the first attack fails

### Stonewall Resolve

- Elements: Earth
- Sigils: Resolve
- Style: survive pressure, punish reckless attacks, win late
- Risk: can be too slow against resource engines

### Tide Insight

- Elements: Water
- Sigils: Insight
- Style: draw, adapt, read the opponent and choose perfect timing
- Risk: needs decisions to matter; weak if effects are too passive

### Thorn Harmony

- Elements: Plant
- Sigils: Harmony
- Style: grow board synergy and convert sustain into pressure
- Risk: falls behind if key pieces are removed early

### Ruin Breaker

- Elements: Fire, Earth, Global
- Sigils: Ruin
- Style: deny opponent plans, punish overextension and force bad trades
- Risk: can feel frustrating if disruption is not clearly explained

## Sigil Card Directions

### Fury

- Effect direction: bonus damage, tempo pressure, Strike/Overreach payoff
- Ideal text length: short
- Avoid: complex conditional chains

### Resolve

- Effect direction: damage reduction, Guard payoff, comeback triggers
- Ideal text length: short to medium
- Avoid: stall loops with no end condition

### Insight

- Effect direction: draw, preview, hand smoothing, Focus payoff
- Ideal text length: medium
- Avoid: too much hidden information for new players

### Ruin

- Effect direction: destroy, weaken, tax, punish Overreach or exposed fields
- Ideal text length: medium
- Avoid: unreadable hard control

### Harmony

- Effect direction: heal, buff allies, scale when cards share element or Sigil
- Ideal text length: short to medium
- Avoid: passive effects that do not change decisions

### Global

- Effect direction: basic utility, tutorial cards, flexible support
- Ideal text length: short
- Avoid: stealing identity from specialized Sigils

## Card Writing Rules

- Every card needs a tactical purpose.
- Every card name should suggest element, Sigil or role.
- Effects should be readable in one quick glance.
- Lore should be short: one sentence maximum for beta.
- Avoid effects that require reading five other cards to understand.
- Starter deck cards must teach the game before they impress the expert.

## Beta Deck Goals

- 30 cards fixed for testing.
- At least one clear aggressive line.
- At least one defensive comeback line.
- At least one draw/planning line.
- At least one synergy/combo line.
- Overreach should be tempting but not automatic.

CARD IDENTITY REPORT: OK
\n========================================================================
APPLIED CARD IDENTITY REPORT
========================================================================
Applied card identity report written to reports/applied_card_identity_report_v109.md
# Ambitionz V1.09 Applied Card Identity Report

## Summary

- Total cards: 250
- Cards missing lore: 0
- Cards missing tactical hint: 0

## Archetype Distribution

- Blaze Rush: 50
- Tide Insight: 50
- Stonewall Resolve: 50
- Thorn Harmony: 50
- Ambition Core: 50

## Identity Role Distribution

- Burst: 50
- Control: 50
- Comeback: 50
- Synergy: 50
- Utility: 50

## Starter Samples

- **Draco Magma** `fire_001` | Fire / Fury | Blaze Rush / Burst | lore: Draco Magma carries fire ambition: Born from ambition before certainty.
- **Fenix Infernal** `fire_002` | Fire / Fury | Blaze Rush / Burst | lore: Fenix Infernal carries fire ambition: Born from ambition before certainty.
- **Cavaleiro Igneo** `fire_003` | Fire / Fury | Blaze Rush / Burst | lore: Cavaleiro Igneo carries fire ambition: Born from ambition before certainty.
- **Golem Incandescente** `fire_004` | Fire / Fury | Blaze Rush / Burst | lore: Golem Incandescente carries fire ambition: Born from ambition before certainty.
- **Behemoth de Lava** `fire_005` | Fire / Fury | Blaze Rush / Burst | lore: Behemoth de Lava carries fire ambition: Born from ambition before certainty.
- **Salamandra Rubra** `fire_006` | Fire / Fury | Blaze Rush / Burst | lore: Salamandra Rubra carries fire ambition: Born from ambition before certainty.
- **Imp de Chama** `fire_007` | Fire / Fury | Blaze Rush / Burst | lore: Imp de Chama carries fire ambition: Born from ambition before certainty.
- **Urso de Lava** `fire_008` | Fire / Fury | Blaze Rush / Burst | lore: Urso de Lava carries fire ambition: Born from ambition before certainty.
- **Escorpiao Vulcanico** `fire_009` | Fire / Fury | Blaze Rush / Burst | lore: Escorpiao Vulcanico carries fire ambition: Born from ambition before certainty.
- **Serpente Ardente** `fire_010` | Fire / Fury | Blaze Rush / Burst | lore: Serpente Ardente carries fire ambition: Born from ambition before certainty.
- **Lobo Flamejante** `fire_011` | Fire / Fury | Blaze Rush / Burst | lore: Lobo Flamejante carries fire ambition: Born from ambition before certainty.
- **Touro de Cinzas** `fire_012` | Fire / Fury | Blaze Rush / Burst | lore: Touro de Cinzas carries fire ambition: Born from ambition before certainty.

APPLIED CARD IDENTITY REPORT: OK
\n========================================================================
PROGRESSION LOOP REPORT
========================================================================
Progression loop report written to reports/progression_loop_report_v106.md
# Ambitionz V1.06 Progression Loop Report

- Version: Ambitionz V1.06 Progression Loop Pack

## Core Loop

### 1. Play Match

- Purpose: Start the engagement loop with a quick duel.
- Player feeling: I can play one more match quickly.

### 2. Earn XP and Coins

- Purpose: Reward time spent even after losses.
- Player feeling: My time was not wasted.

### 3. Complete Missions

- Purpose: Give short-term goals beyond simply winning.
- Player feeling: I have a reason to return today.

### 4. Open Booster

- Purpose: Create anticipation and collection growth.
- Player feeling: Maybe I unlock something useful or rare.

### 5. Improve Deck

- Purpose: Turn rewards into strategic expression.
- Player feeling: My deck is becoming mine.

### 6. Climb Ranking

- Purpose: Create competitive progression.
- Player feeling: I am getting better and proving it.

### 7. Unlock Cosmetic or Card Identity

- Purpose: Create long-term attachment and personalization.
- Player feeling: My account has history and identity.

## Progression Systems

### XP

- Role: Measures account growth and unlock pacing.
- Design rule: XP should reward both wins and participation.
- Future use: Unlock levels, cosmetics, missions and beta milestones.

### COINS

- Role: Soft currency for boosters and future cosmetic purchases.
- Design rule: Coins should feel useful but not inflate too fast.
- Future use: Booster purchases, event entries, cosmetics.

### MISSIONS

- Role: Daily and onboarding goals.
- Design rule: Missions must teach good gameplay behavior.
- Future use: Daily retention, tutorial progression, beta tasks.

### BOOSTERS

- Role: Collection expansion and excitement.
- Design rule: Boosters should support deck improvement without overwhelming new players.
- Future use: Element packs, Sigil packs, event packs.

### RANKING

- Role: Competitive identity.
- Design rule: Ranking should reward consistency, not only grind.
- Future use: Seasons, tiers, leaderboard rewards.

### COSMETICS

- Role: Long-term personalization.
- Design rule: Cosmetics should not affect gameplay power.
- Future use: Card backs, frames, titles, avatars, arena skins.

## Reward Philosophy

- win: Winning should feel clearly better, especially in PvP.
- loss: Losing should still advance the player slightly to reduce early churn.
- draw: Draws should reward time but less than clean wins.
- training: Training rewards should teach and encourage experimentation.
- pvp: PvP rewards should be the main competitive progression source.

## Mission Design Rules

- A mission should teach or reinforce a useful behavior.
- Avoid missions that force bad gameplay decisions.
- Use simple verbs: play, win, use, complete, open, claim.
- Early missions should be easy and fast.
- Daily missions should create variety without forcing frustration.
- Beta missions should generate testing data.

## Booster Design Rules

- Starter boosters should be readable and low complexity.
- Element boosters should help players pursue identity.
- Sigil boosters should help players pursue playstyle.
- Rare cards should feel exciting but not mandatory.
- Beta booster economy should be generous enough for testing.

## Retention Targets

- The first match should happen quickly.
- The first reward should be immediate.
- The first booster should be reachable early.
- The first deck edit should feel meaningful.
- The first ranking improvement should feel achievable.

PROGRESSION LOOP REPORT: OK
\n========================================================================
AMBITIONZ PREFLIGHT RESULT
========================================================================
AMBITIONZ PREFLIGHT PASSED
/Users/lucassilverio/Desktop/Ambition/.venv/lib/python3.9/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'. See: https://github.com/urllib3/urllib3/issues/3020
  warnings.warn(
```
### /Users/lucassilverio/Desktop/Ambition/.venv/bin/python3 tools/internal_rc_check.py
Exit code: 0
```
INTERNAL RC STATUS: READY
REQUIRED OK: True
RECOMMENDED OK: False
OK: Database responds [required] - Database query OK
FAIL: Email delivery configured [recommended] - SMTP missing or incomplete
OK: Critical routes do not 500 [required] - /=200, /health=200, /login=200, /register=200, /training=302, /arena=302, /feedback=302, /missions=302, /shop=302
OK: No open critical feedback [required] - 0 open critical reports
FAIL: No unresolved runtime errors [recommended] - 1 unresolved error logs
OK: Tester accounts exist [recommended] - 4 total users, 4 verified
OK: Match history records exist [recommended] - 8 saved matches
FAIL: Recent match length is readable [recommended] - 1.6 average rounds over recent matches
/Users/lucassilverio/Desktop/Ambition/.venv/lib/python3.9/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'. See: https://github.com/urllib3/urllib3/issues/3020
  warnings.warn(
```
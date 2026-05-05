# Ambitionz Deep Audit Report

## Git status

```
M .env.example
 M app.py
 M config.py
 M env.example
 M render.yaml
 M reports/balance_report_v105.md
 M reports/deep_audit_report.md
 M sockets/game_socket.py
 M static/css/style.css
 M static/js/game.js
 M templates/arena.html
 M tests/conftest.py
 M tests/test_release_candidate_smoke.py

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

- `admin_whoami`: `"/admin/whoami"`
- `admin_ping`: `"/admin/ping"`
- `debug_routes`: `"/debug/routes"`
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


No duplicate socket handlers found.

## Auth/login scan

96: `login_attempts = {}`
175: `request.form.get("_csrf_token")`
206: `if getattr(user, "account_status", "active") in ["banned", "disabled"]:`
240: `return login_attempts.get(fingerprint, 0)`
253: `login_attempts[fingerprint] = login_attempts.get(fingerprint, 0) + 1`
256: `def reset_login_attempts(fingerprint):`
257: `login_attempts.pop(fingerprint, None)`
285: `user.is_verified = True`
286: `user.account_status = "active"`
364: `received = request.form.get("confirmation", "").strip()`
660: `if not bool(getattr(user, "is_verified", False)):`
664: `if getattr(user, "account_status", "active") in ["banned", "disabled"]:`
690: `"is_verified": bool(user.is_verified),`
692: `"account_status": getattr(user, "account_status", None),`
749: `email = request.form.get("email", "").strip().lower()`
868: `verified_users=User.query.filter_by(is_verified=True).count(),`
986: `target.account_status = "banned"`
1009: `target.account_status = "active" if target.is_verified else "unverified"`
1030: `max_uses = int(request.form.get("max_uses", "1") or 1)`
1031: `code = request.form.get("code", "").strip().upper() or generate_invite_code()`
1126: `report.status = request.form.get("status", report.status)`
1231: `verified_users = User.query.filter_by(is_verified=True).count()`
1377: `email = request.form.get("email", "").strip().lower()`
1385: `if user.is_verified:`
1601: `"status": getattr(user, "account_status", "beta"),`
1603: `"is_verified": bool(getattr(user, "is_verified", False)),`
1693: `email = request.form.get("email", "").strip().lower()`
1732: `password = request.form.get("password", "").strip()`
1840: `payload = request.get_json(silent=True) or request.form.to_dict() or {}`
1900: `username = request.form.get("username", "").strip()`
1901: `email = request.form.get("email", "").strip().lower()`
1902: `password = request.form.get("password", "").strip()`
1903: `invite_code = request.form.get("invite_code", "").strip().upper()`
1942: `account_status="active" if auto_verify else "unverified",`
1944: `is_verified=auto_verify,`
2004: `email = request.form.get("email", "").strip().lower()`
2005: `password = request.form.get("password", "").strip()`
2006: `invite_code = request.form.get("invite_code", "").strip().upper()`
2017: `if not user or not user.check_password(password):`
2035: `if not bool(getattr(user, "is_verified", False)):`
2045: `reset_login_attempts(attempt_key)`
2263: `selected_pack_key = request.form.get("pack_key") or request.args.get("pack") or "elemental"`
2392: `selected_cards = request.form.getlist("deck_cards")`
3022: `category = request.form.get("category", "general").strip() or "general"`
3023: `severity = request.form.get("severity", "normal").strip() or "normal"`
3024: `title = request.form.get("title", "").strip()`
3025: `message = request.form.get("message", "").strip()`
3026: `page_url = request.form.get("page_url", "").strip()`
3248: `verified_users = User.query.filter_by(is_verified=True).count()`

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
244: `"is_admin": "is_admin BOOLEAN NOT NULL DEFAULT 0",`
403: `"ALTER TABLE users ADD COLUMN IF NOT EXISTS account_status VARCHAR(40) DEFAULT 'active' NOT NULL",`
410: `"UPDATE users SET account_status = 'active' WHERE is_verified = true AND (account_status IS NULL OR account_status = 'unverified')",`
411: `"UPDATE users SET account_status = 'unverified' WHERE is_verified = false AND account_status IS NULL",`
423: `"account_status": "account_status VARCHAR(40) DEFAULT 'active' NOT NULL",`

## Rough undefined function scan in app.py

- `abort`
- `apply_match_rewards`
- `apply_security_headers`
- `build_match_summary_lines`
- `build_playable_deck`
- `cards_from_ids`
- `claim_mission`
- `clear_gameplay_data`
- `collection_summary`
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
- `load_card_ids`
- `normalize_room_code`
- `password_policy_errors`
- `player_display_name`
- `predicate`
- `record_match_telemetry`
- `register_game_socket_handlers`
- `reset_player_energy`
- `reward_line`
- `safe_user_id`
- `send_password_reset_email`
- `send_smtp_test_email`
- `send_verification_email`
- `sql_inspect`
- `sql_text`
- `summarize_monsters`
- `timedelta`
- `validate_deck`

## TODO/FIXME/Error strings

- `app.py:127` except Exception as error:
- `app.py:128` print("SYSTEM LOG ERROR:", error)
- `app.py:140` except Exception as error:
- `app.py:141` print("RC EVENT LOG ERROR:", type(error).__name__, error)
- `app.py:238` except Exception as error:
- `app.py:239` print("LOGIN RATE QUERY ERROR:", type(error).__name__, error)
- `app.py:251` except Exception as error:
- `app.py:252` print("LOGIN RATE LOG ERROR:", type(error).__name__, error)
- `app.py:386` except Exception as error:
- `app.py:492` except Exception as error:
- `app.py:558` except Exception as error:
- `app.py:598` except Exception as error:
- `app.py:613` except Exception as error:
- `app.py:616` print("Error:", error)
- `app.py:645` except Exception:
- `app.py:762` except Exception as log_error:
- `app.py:768` except Exception as log_error:
- `app.py:771` except Exception as error:
- `app.py:774` print("Error:", error)
- `app.py:800` except Exception as error:
- `app.py:803` print("Error:", error)
- `app.py:827` except Exception as error:
- `app.py:830` print("Error:", error)
- `app.py:855` except Exception as error:
- `app.py:1074` except Exception as error:
- `app.py:1075` print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)
- `app.py:1138` except Exception:
- `app.py:1159` except Exception as error:
- `app.py:1200` except Exception as error:
- `app.py:1218` except Exception as error:
- `app.py:1241` except Exception as error:
- `app.py:1304` except Exception as error:
- `app.py:1305` print("RC FEEDBACK QUERY ERROR:", type(error).__name__, error)
- `app.py:1309` except Exception as error:
- `app.py:1310` print("RC LOG QUERY ERROR:", type(error).__name__, error)
- `app.py:1335` except Exception as error:
- `app.py:1336` db_status = f"error:{type(error).__name__}"
- `app.py:1364` except Exception as log_error:
- `app.py:1365` print("500 LOG ERROR:", type(log_error).__name__, log_error)
- `app.py:1406` except Exception as error:
- `app.py:1581` except Exception as error:
- `app.py:1582` print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
- `app.py:1632` except Exception as error:
- `app.py:1633` print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
- `app.py:1715` except Exception as error:
- `app.py:1841` except Exception:
- `app.py:1865` except Exception as error:
- `app.py:1868` except Exception as rollback_error:
- `app.py:1869` print("BETA EVENT ROLLBACK ERROR:", type(rollback_error).__name__, rollback_error)
- `app.py:1870` print("BETA EVENT LOG ERROR:", type(error).__name__, error)
- `app.py:1988` except Exception:
- `app.py:2057` except Exception as error:
- `app.py:2058` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `app.py:2683` except Exception as error:
- `app.py:2684` print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)
- `app.py:2726` except Exception as error:
- `app.py:2727` print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
- `app.py:2757` except Exception as error:
- `app.py:2758` print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)
- `app.py:3065` except Exception as error:
- `app.py:3066` print("FEEDBACK LIMIT CHECK ERROR:", type(error).__name__, error)
- `app.py:3088` except Exception as error:
- `app.py:3089` print("FEEDBACK LOG ERROR:", type(error).__name__, error)
- `app.py:3221` except Exception as error:
- `app.py:3222` print("ADMIN BALANCE ERROR:", type(error).__name__, error)
- `app.py:3249` except Exception as error:
- `app.py:3294` except Exception as error:
- `app.py:3321` except Exception as error:
- `app.py:3322` print("MISSIONS PAGE ERROR:", type(error).__name__, error)
- `app.py:3350` except Exception as error:
- `app.py:3351` print("MISSION CLAIM ERROR:", type(error).__name__, error)
- `app.py:3408` except Exception as error:
- `app.py:3432` except Exception as error:
- `app.py:3433` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `app.py:3452` except Exception as error:
- `app.py:3453` print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
- `migrations/env.py:31` except AttributeError:
- `tools/audit_routes.py:43` except Exception as error:
- `tools/register_audit.py:20` except Exception:
- `tools/register_audit.py:86` except Exception:
- `tools/register_audit.py:100` except Exception:
- `tools/audit_database.py:49` except Exception as error:
- `tools/audit_database.py:52` except Exception as error:
- `tools/balance_report.py:16` except Exception:
- `tools/balance_snapshot.py:19` except Exception:
- `tools/balance_snapshot.py:26` except Exception:
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
- `sockets/game_socket.py:51` except Exception:
- `sockets/game_socket.py:216` except Exception as error:
- `sockets/game_socket.py:217` print("QUEUE BOT FALLBACK ERROR:", type(error).__name__, error)
- `sockets/game_socket.py:336` except Exception as error:
- `sockets/game_socket.py:337` print("TRAINING START ERROR:", type(error).__name__, error)
- `sockets/game_socket.py:375` except Exception as error:
- `sockets/game_socket.py:376` print("QUEUE PLAYER CREATE ERROR:", type(error).__name__, error)
- `sockets/game_socket.py:524` except Exception:
- `sockets/game_socket.py:701` except Exception as error:
- `sockets/game_socket.py:702` print("V2 BATTLE EVENTS EMIT ERROR:", type(error).__name__, error)
- `game/deck.py:77` except Exception:
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
- `reports/register_audit_report.md:57` except Exception:
- `reports/register_audit_report.md:148` except Exception:
- `reports/deep_audit_report.md:217` ## TODO/FIXME/Error strings
- `reports/deep_audit_report.md:219` - `app.py:121` except Exception as error:
- `reports/deep_audit_report.md:220` - `app.py:122` print("SYSTEM LOG ERROR:", error)
- `reports/deep_audit_report.md:221` - `app.py:134` except Exception as error:
- `reports/deep_audit_report.md:222` - `app.py:135` print("RC EVENT LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:223` - `app.py:232` except Exception as error:
- `reports/deep_audit_report.md:224` - `app.py:233` print("LOGIN RATE QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:225` - `app.py:245` except Exception as error:
- `reports/deep_audit_report.md:226` - `app.py:246` print("LOGIN RATE LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:227` - `app.py:380` except Exception as error:
- `reports/deep_audit_report.md:228` - `app.py:486` except Exception as error:
- `reports/deep_audit_report.md:229` - `app.py:552` except Exception as error:
- `reports/deep_audit_report.md:230` - `app.py:592` except Exception as error:
- `reports/deep_audit_report.md:231` - `app.py:607` except Exception as error:
- `reports/deep_audit_report.md:232` - `app.py:610` print("Error:", error)
- `reports/deep_audit_report.md:233` - `app.py:639` except Exception:
- `reports/deep_audit_report.md:234` - `app.py:756` except Exception as log_error:
- `reports/deep_audit_report.md:235` - `app.py:762` except Exception as log_error:
- `reports/deep_audit_report.md:236` - `app.py:765` except Exception as error:
- `reports/deep_audit_report.md:237` - `app.py:768` print("Error:", error)
- `reports/deep_audit_report.md:238` - `app.py:794` except Exception as error:
- `reports/deep_audit_report.md:239` - `app.py:797` print("Error:", error)
- `reports/deep_audit_report.md:240` - `app.py:821` except Exception as error:
- `reports/deep_audit_report.md:241` - `app.py:824` print("Error:", error)
- `reports/deep_audit_report.md:242` - `app.py:849` except Exception as error:
- `reports/deep_audit_report.md:243` - `app.py:1068` except Exception as error:
- `reports/deep_audit_report.md:244` - `app.py:1069` print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:245` - `app.py:1132` except Exception:
- `reports/deep_audit_report.md:246` - `app.py:1153` except Exception as error:
- `reports/deep_audit_report.md:247` - `app.py:1194` except Exception as error:
- `reports/deep_audit_report.md:248` - `app.py:1212` except Exception as error:
- `reports/deep_audit_report.md:249` - `app.py:1235` except Exception as error:
- `reports/deep_audit_report.md:250` - `app.py:1298` except Exception as error:
- `reports/deep_audit_report.md:251` - `app.py:1299` print("RC FEEDBACK QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:252` - `app.py:1303` except Exception as error:
- `reports/deep_audit_report.md:253` - `app.py:1304` print("RC LOG QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:254` - `app.py:1329` except Exception as error:
- `reports/deep_audit_report.md:255` - `app.py:1330` db_status = f"error:{type(error).__name__}"
- `reports/deep_audit_report.md:256` - `app.py:1358` except Exception as log_error:
- `reports/deep_audit_report.md:257` - `app.py:1359` print("500 LOG ERROR:", type(log_error).__name__, log_error)
- `reports/deep_audit_report.md:258` - `app.py:1400` except Exception as error:
- `reports/deep_audit_report.md:259` - `app.py:1575` except Exception as error:
- `reports/deep_audit_report.md:260` - `app.py:1576` print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:261` - `app.py:1626` except Exception as error:
- `reports/deep_audit_report.md:262` - `app.py:1627` print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:263` - `app.py:1709` except Exception as error:
- `reports/deep_audit_report.md:264` - `app.py:1835` except Exception:
- `reports/deep_audit_report.md:265` - `app.py:1859` except Exception as error:
- `reports/deep_audit_report.md:266` - `app.py:1862` except Exception as rollback_error:
- `reports/deep_audit_report.md:267` - `app.py:1863` print("BETA EVENT ROLLBACK ERROR:", type(rollback_error).__name__, rollback_error)
- `reports/deep_audit_report.md:268` - `app.py:1864` print("BETA EVENT LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:269` - `app.py:1982` except Exception:
- `reports/deep_audit_report.md:270` - `app.py:2051` except Exception as error:
- `reports/deep_audit_report.md:271` - `app.py:2052` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:272` - `app.py:2677` except Exception as error:
- `reports/deep_audit_report.md:273` - `app.py:2678` print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:274` - `app.py:2720` except Exception as error:
- `reports/deep_audit_report.md:275` - `app.py:2721` print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:276` - `app.py:2751` except Exception as error:
- `reports/deep_audit_report.md:277` - `app.py:2752` print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:278` - `app.py:3058` except Exception as error:
- `reports/deep_audit_report.md:279` - `app.py:3059` print("FEEDBACK LIMIT CHECK ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:280` - `app.py:3081` except Exception as error:
- `reports/deep_audit_report.md:281` - `app.py:3082` print("FEEDBACK LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:282` - `app.py:3214` except Exception as error:
- `reports/deep_audit_report.md:283` - `app.py:3215` print("ADMIN BALANCE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:284` - `app.py:3242` except Exception as error:
- `reports/deep_audit_report.md:285` - `app.py:3287` except Exception as error:
- `reports/deep_audit_report.md:286` - `app.py:3314` except Exception as error:
- `reports/deep_audit_report.md:287` - `app.py:3315` print("MISSIONS PAGE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:288` - `app.py:3343` except Exception as error:
- `reports/deep_audit_report.md:289` - `app.py:3344` print("MISSION CLAIM ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:290` - `app.py:3401` except Exception as error:
- `reports/deep_audit_report.md:291` - `app.py:3425` except Exception as error:
- `reports/deep_audit_report.md:292` - `app.py:3426` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:293` - `app.py:3445` except Exception as error:
- `reports/deep_audit_report.md:294` - `app.py:3446` print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:295` - `migrations/env.py:31` except AttributeError:
- `reports/deep_audit_report.md:296` - `tools/audit_routes.py:43` except Exception as error:
- `reports/deep_audit_report.md:297` - `tools/register_audit.py:20` except Exception:
- `reports/deep_audit_report.md:298` - `tools/register_audit.py:86` except Exception:
- `reports/deep_audit_report.md:299` - `tools/register_audit.py:100` except Exception:
- `reports/deep_audit_report.md:300` - `tools/audit_database.py:49` except Exception as error:
- `reports/deep_audit_report.md:301` - `tools/audit_database.py:52` except Exception as error:
- `reports/deep_audit_report.md:302` - `tools/balance_report.py:16` except Exception:
- `reports/deep_audit_report.md:303` - `tools/balance_snapshot.py:19` except Exception:
- `reports/deep_audit_report.md:304` - `tools/balance_snapshot.py:26` except Exception:
- `reports/deep_audit_report.md:305` - `tools/audit_cards.py:23` except Exception as error:
- `reports/deep_audit_report.md:306` - `tools/audit_cards.py:62` except Exception:
- `reports/deep_audit_report.md:307` - `tools/audit_cards.py:74` except Exception:
- `reports/deep_audit_report.md:308` - `tools/fix_deck_builder_v112_manual.py:115` raise SystemExit("ERROR: old checkbox block not found exactly. No changes made.")
- `reports/deep_audit_report.md:309` - `tools/deep_audit.py:30` except Exception as e:
- `reports/deep_audit_report.md:310` - `tools/deep_audit.py:125` # 8. Broken references: function calls not defined in same file rough scan
- `reports/deep_audit_report.md:311` - `tools/deep_audit.py:144` except Exception as e:
- `reports/deep_audit_report.md:312` - `tools/deep_audit.py:147` # 9. TODO/FIXME/errors
- `reports/deep_audit_report.md:313` - `tools/deep_audit.py:148` section("TODO/FIXME/Error strings")
- `reports/deep_audit_report.md:314` - `tools/deep_audit.py:156` except Exception:
- `reports/deep_audit_report.md:315` - `tools/deep_audit.py:160` if any(k in low for k in ["todo", "fixme", "hack", "broken", "error:", "except exception", "pass  #"]):
- `reports/deep_audit_report.md:316` - `tools/deep_audit.py:179` except Exception:
- `reports/deep_audit_report.md:317` - `tools/internal_rc_check.py:42` print("ERROR:", failure)
- `reports/deep_audit_report.md:318` - `tools/fix_beta_core_v111.py:118` # The common broken shape has two const cost declarations close together.
- `reports/deep_audit_report.md:319` - `tools/preflight.py:31` except Exception as error:
- `reports/deep_audit_report.md:320` - `tools/preflight.py:38` print("ERROR:", error)
- `reports/deep_audit_report.md:321` - `tools/preflight.py:70` print("ERROR:", error)
- `reports/deep_audit_report.md:322` - `sockets/game_socket.py:150` except Exception as error:
- `reports/deep_audit_report.md:323` - `sockets/game_socket.py:151` print("TRAINING START ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:324` - `sockets/game_socket.py:189` except Exception as error:
- `reports/deep_audit_report.md:325` - `sockets/game_socket.py:190` print("QUEUE PLAYER CREATE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:326` - `sockets/game_socket.py:283` except Exception as error:
- `reports/deep_audit_report.md:327` - `sockets/game_socket.py:284` print("QUEUE BOT FALLBACK ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:328` - `sockets/game_socket.py:354` except Exception:
- `reports/deep_audit_report.md:329` - `sockets/game_socket.py:531` except Exception as error:
- `reports/deep_audit_report.md:330` - `sockets/game_socket.py:532` print("V2 BATTLE EVENTS EMIT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:331` - `sockets/game_socket.py:641` except Exception:
- `reports/deep_audit_report.md:332` - `game/deck.py:77` except Exception:
- `reports/deep_audit_report.md:333` - `game/cards.py:165` "Mastodonte Antigo",
- `reports/deep_audit_report.md:334` - `game/match_utils.py:16` except Exception:
- `reports/deep_audit_report.md:335` - `templates/first_session.html:67` If anything blocks the path, feels confusing, looks broken on Android,
- `reports/deep_audit_report.md:336` - `backups/beta_final_stability_v113_20260503_103647/app.py:104` except Exception as error:
- `reports/deep_audit_report.md:337` - `backups/beta_final_stability_v113_20260503_103647/app.py:105` print("SYSTEM LOG ERROR:", error)
- `reports/deep_audit_report.md:338` - `backups/beta_final_stability_v113_20260503_103647/app.py:214` except Exception as error:
- `reports/deep_audit_report.md:339` - `backups/beta_final_stability_v113_20260503_103647/app.py:226` except Exception as error:
- `reports/deep_audit_report.md:340` - `backups/beta_final_stability_v113_20260503_103647/app.py:250` except Exception as error:
- `reports/deep_audit_report.md:341` - `backups/beta_final_stability_v113_20260503_103647/app.py:319` except Exception as error:
- `reports/deep_audit_report.md:342` - `backups/beta_final_stability_v113_20260503_103647/app.py:334` except Exception as error:
- `reports/deep_audit_report.md:343` - `backups/beta_final_stability_v113_20260503_103647/app.py:337` print("Error:", error)
- `reports/deep_audit_report.md:344` - `backups/beta_final_stability_v113_20260503_103647/app.py:391` except Exception as log_error:
- `reports/deep_audit_report.md:345` - `backups/beta_final_stability_v113_20260503_103647/app.py:397` except Exception as log_error:
- `reports/deep_audit_report.md:346` - `backups/beta_final_stability_v113_20260503_103647/app.py:400` except Exception as error:
- `reports/deep_audit_report.md:347` - `backups/beta_final_stability_v113_20260503_103647/app.py:403` print("Error:", error)
- `reports/deep_audit_report.md:348` - `backups/beta_final_stability_v113_20260503_103647/app.py:429` except Exception as error:
- `reports/deep_audit_report.md:349` - `backups/beta_final_stability_v113_20260503_103647/app.py:432` print("Error:", error)
- `reports/deep_audit_report.md:350` - `backups/beta_final_stability_v113_20260503_103647/app.py:456` except Exception as error:
- `reports/deep_audit_report.md:351` - `backups/beta_final_stability_v113_20260503_103647/app.py:459` print("Error:", error)
- `reports/deep_audit_report.md:352` - `backups/beta_final_stability_v113_20260503_103647/app.py:484` except Exception as error:
- `reports/deep_audit_report.md:353` - `backups/beta_final_stability_v113_20260503_103647/app.py:695` except Exception as error:
- `reports/deep_audit_report.md:354` - `backups/beta_final_stability_v113_20260503_103647/app.py:696` print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:355` - `backups/beta_final_stability_v113_20260503_103647/app.py:805` except Exception as error:
- `reports/deep_audit_report.md:356` - `backups/beta_final_stability_v113_20260503_103647/app.py:980` except Exception as error:
- `reports/deep_audit_report.md:357` - `backups/beta_final_stability_v113_20260503_103647/app.py:981` print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:358` - `backups/beta_final_stability_v113_20260503_103647/app.py:1031` except Exception as error:
- `reports/deep_audit_report.md:359` - `backups/beta_final_stability_v113_20260503_103647/app.py:1032` print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:360` - `backups/beta_final_stability_v113_20260503_103647/app.py:1111` except Exception as error:
- `reports/deep_audit_report.md:361` - `backups/beta_final_stability_v113_20260503_103647/app.py:1123` except Exception:
- `reports/deep_audit_report.md:362` - `backups/beta_final_stability_v113_20260503_103647/app.py:1234` except Exception:
- `reports/deep_audit_report.md:363` - `backups/beta_final_stability_v113_20260503_103647/app.py:1258` except Exception as error:
- `reports/deep_audit_report.md:364` - `backups/beta_final_stability_v113_20260503_103647/app.py:1261` except Exception:
- `reports/deep_audit_report.md:365` - `backups/beta_final_stability_v113_20260503_103647/app.py:1263` print("BETA EVENT LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:366` - `backups/beta_final_stability_v113_20260503_103647/app.py:1356` except Exception:
- `reports/deep_audit_report.md:367` - `backups/beta_final_stability_v113_20260503_103647/app.py:1410` except Exception as error:
- `reports/deep_audit_report.md:368` - `backups/beta_final_stability_v113_20260503_103647/app.py:1411` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:369` - `backups/beta_final_stability_v113_20260503_103647/app.py:1922` except Exception as error:
- `reports/deep_audit_report.md:370` - `backups/beta_final_stability_v113_20260503_103647/app.py:1923` print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:371` - `backups/beta_final_stability_v113_20260503_103647/app.py:1965` except Exception as error:
- `reports/deep_audit_report.md:372` - `backups/beta_final_stability_v113_20260503_103647/app.py:1966` print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:373` - `backups/beta_final_stability_v113_20260503_103647/app.py:1996` except Exception as error:
- `reports/deep_audit_report.md:374` - `backups/beta_final_stability_v113_20260503_103647/app.py:1997` print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:375` - `backups/beta_final_stability_v113_20260503_103647/app.py:2162` except Exception as error:
- `reports/deep_audit_report.md:376` - `backups/beta_final_stability_v113_20260503_103647/app.py:2163` print("TRAINING START ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:377` - `backups/beta_final_stability_v113_20260503_103647/app.py:2304` except Exception:
- `reports/deep_audit_report.md:378` - `backups/beta_final_stability_v113_20260503_103647/app.py:2708` except Exception as error:
- `reports/deep_audit_report.md:379` - `backups/beta_final_stability_v113_20260503_103647/app.py:2709` print("FEEDBACK LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:380` - `backups/beta_final_stability_v113_20260503_103647/app.py:2841` except Exception as error:
- `reports/deep_audit_report.md:381` - `backups/beta_final_stability_v113_20260503_103647/app.py:2842` print("ADMIN BALANCE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:382` - `backups/beta_final_stability_v113_20260503_103647/app.py:2869` except Exception as error:
- `reports/deep_audit_report.md:383` - `backups/beta_final_stability_v113_20260503_103647/app.py:2913` except Exception as error:
- `reports/deep_audit_report.md:384` - `backups/beta_final_stability_v113_20260503_103647/app.py:2940` except Exception as error:
- `reports/deep_audit_report.md:385` - `backups/beta_final_stability_v113_20260503_103647/app.py:2941` print("MISSIONS PAGE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:386` - `backups/beta_final_stability_v113_20260503_103647/app.py:2969` except Exception as error:
- `reports/deep_audit_report.md:387` - `backups/beta_final_stability_v113_20260503_103647/app.py:2970` print("MISSION CLAIM ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:388` - `backups/beta_final_stability_v113_20260503_103647/app.py:3027` except Exception as error:
- `reports/deep_audit_report.md:389` - `backups/beta_final_stability_v113_20260503_103647/app.py:3051` except Exception as error:
- `reports/deep_audit_report.md:390` - `backups/beta_final_stability_v113_20260503_103647/app.py:3052` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:391` - `backups/beta_final_stability_v113_20260503_103647/app.py:3071` except Exception as error:
- `reports/deep_audit_report.md:392` - `backups/beta_final_stability_v113_20260503_103647/app.py:3072` print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:393` - `backups/beta_core_v111_20260503_102709/app.py:104` except Exception as error:
- `reports/deep_audit_report.md:394` - `backups/beta_core_v111_20260503_102709/app.py:105` print("SYSTEM LOG ERROR:", error)
- `reports/deep_audit_report.md:395` - `backups/beta_core_v111_20260503_102709/app.py:214` except Exception as error:
- `reports/deep_audit_report.md:396` - `backups/beta_core_v111_20260503_102709/app.py:226` except Exception as error:
- `reports/deep_audit_report.md:397` - `backups/beta_core_v111_20260503_102709/app.py:250` except Exception as error:
- `reports/deep_audit_report.md:398` - `backups/beta_core_v111_20260503_102709/app.py:319` except Exception as error:
- `reports/deep_audit_report.md:399` - `backups/beta_core_v111_20260503_102709/app.py:334` except Exception as error:
- `reports/deep_audit_report.md:400` - `backups/beta_core_v111_20260503_102709/app.py:337` print("Error:", error)
- `reports/deep_audit_report.md:401` - `backups/beta_core_v111_20260503_102709/app.py:391` except Exception as log_error:
- `reports/deep_audit_report.md:402` - `backups/beta_core_v111_20260503_102709/app.py:397` except Exception as log_error:
- `reports/deep_audit_report.md:403` - `backups/beta_core_v111_20260503_102709/app.py:400` except Exception as error:
- `reports/deep_audit_report.md:404` - `backups/beta_core_v111_20260503_102709/app.py:403` print("Error:", error)
- `reports/deep_audit_report.md:405` - `backups/beta_core_v111_20260503_102709/app.py:429` except Exception as error:
- `reports/deep_audit_report.md:406` - `backups/beta_core_v111_20260503_102709/app.py:432` print("Error:", error)
- `reports/deep_audit_report.md:407` - `backups/beta_core_v111_20260503_102709/app.py:456` except Exception as error:
- `reports/deep_audit_report.md:408` - `backups/beta_core_v111_20260503_102709/app.py:459` print("Error:", error)
- `reports/deep_audit_report.md:409` - `backups/beta_core_v111_20260503_102709/app.py:484` except Exception as error:
- `reports/deep_audit_report.md:410` - `backups/beta_core_v111_20260503_102709/app.py:695` except Exception as error:
- `reports/deep_audit_report.md:411` - `backups/beta_core_v111_20260503_102709/app.py:696` print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:412` - `backups/beta_core_v111_20260503_102709/app.py:805` except Exception as error:
- `reports/deep_audit_report.md:413` - `backups/beta_core_v111_20260503_102709/app.py:980` except Exception as error:
- `reports/deep_audit_report.md:414` - `backups/beta_core_v111_20260503_102709/app.py:981` print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:415` - `backups/beta_core_v111_20260503_102709/app.py:1031` except Exception as error:
- `reports/deep_audit_report.md:416` - `backups/beta_core_v111_20260503_102709/app.py:1032` print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:417` - `backups/beta_core_v111_20260503_102709/app.py:1111` except Exception as error:
- `reports/deep_audit_report.md:418` - `backups/beta_core_v111_20260503_102709/app.py:1123` except Exception:
- `reports/deep_audit_report.md:419` - `backups/beta_core_v111_20260503_102709/app.py:1234` except Exception:
- `reports/deep_audit_report.md:420` - `backups/beta_core_v111_20260503_102709/app.py:1258` except Exception as error:
- `reports/deep_audit_report.md:421` - `backups/beta_core_v111_20260503_102709/app.py:1261` except Exception:
- `reports/deep_audit_report.md:422` - `backups/beta_core_v111_20260503_102709/app.py:1263` print("BETA EVENT LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:423` - `backups/beta_core_v111_20260503_102709/app.py:1356` except Exception:
- `reports/deep_audit_report.md:424` - `backups/beta_core_v111_20260503_102709/app.py:1410` except Exception as error:
- `reports/deep_audit_report.md:425` - `backups/beta_core_v111_20260503_102709/app.py:1411` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:426` - `backups/beta_core_v111_20260503_102709/app.py:1922` except Exception as error:
- `reports/deep_audit_report.md:427` - `backups/beta_core_v111_20260503_102709/app.py:1923` print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:428` - `backups/beta_core_v111_20260503_102709/app.py:1965` except Exception as error:
- `reports/deep_audit_report.md:429` - `backups/beta_core_v111_20260503_102709/app.py:1966` print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:430` - `backups/beta_core_v111_20260503_102709/app.py:1996` except Exception as error:
- `reports/deep_audit_report.md:431` - `backups/beta_core_v111_20260503_102709/app.py:1997` print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:432` - `backups/beta_core_v111_20260503_102709/app.py:2162` except Exception as error:
- `reports/deep_audit_report.md:433` - `backups/beta_core_v111_20260503_102709/app.py:2163` print("TRAINING START ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:434` - `backups/beta_core_v111_20260503_102709/app.py:2304` except Exception:
- `reports/deep_audit_report.md:435` - `backups/beta_core_v111_20260503_102709/app.py:2708` except Exception as error:
- `reports/deep_audit_report.md:436` - `backups/beta_core_v111_20260503_102709/app.py:2709` print("FEEDBACK LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:437` - `backups/beta_core_v111_20260503_102709/app.py:2841` except Exception as error:
- `reports/deep_audit_report.md:438` - `backups/beta_core_v111_20260503_102709/app.py:2842` print("ADMIN BALANCE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:439` - `backups/beta_core_v111_20260503_102709/app.py:2869` except Exception as error:
- `reports/deep_audit_report.md:440` - `backups/beta_core_v111_20260503_102709/app.py:2913` except Exception as error:
- `reports/deep_audit_report.md:441` - `backups/beta_core_v111_20260503_102709/app.py:2940` except Exception as error:
- `reports/deep_audit_report.md:442` - `backups/beta_core_v111_20260503_102709/app.py:2941` print("MISSIONS PAGE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:443` - `backups/beta_core_v111_20260503_102709/app.py:2969` except Exception as error:
- `reports/deep_audit_report.md:444` - `backups/beta_core_v111_20260503_102709/app.py:2970` print("MISSION CLAIM ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:445` - `backups/beta_core_v111_20260503_102709/app.py:3027` except Exception as error:
- `reports/deep_audit_report.md:446` - `backups/beta_core_v111_20260503_102709/app.py:3051` except Exception as error:
- `reports/deep_audit_report.md:447` - `backups/beta_core_v111_20260503_102709/app.py:3052` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:448` - `backups/beta_core_v111_20260503_102709/app.py:3071` except Exception as error:
- `reports/deep_audit_report.md:449` - `backups/beta_core_v111_20260503_102709/app.py:3072` print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:450` - `backups/email_delivery_v114_20260503_104855/app.py:104` except Exception as error:
- `reports/deep_audit_report.md:451` - `backups/email_delivery_v114_20260503_104855/app.py:105` print("SYSTEM LOG ERROR:", error)
- `reports/deep_audit_report.md:452` - `backups/email_delivery_v114_20260503_104855/app.py:214` except Exception as error:
- `reports/deep_audit_report.md:453` - `backups/email_delivery_v114_20260503_104855/app.py:320` except Exception as error:
- `reports/deep_audit_report.md:454` - `backups/email_delivery_v114_20260503_104855/app.py:344` except Exception as error:
- `reports/deep_audit_report.md:455` - `backups/email_delivery_v114_20260503_104855/app.py:413` except Exception as error:
- `reports/deep_audit_report.md:456` - `backups/email_delivery_v114_20260503_104855/app.py:428` except Exception as error:
- `reports/deep_audit_report.md:457` - `backups/email_delivery_v114_20260503_104855/app.py:431` print("Error:", error)
- `reports/deep_audit_report.md:458` - `backups/email_delivery_v114_20260503_104855/app.py:485` except Exception as log_error:
- `reports/deep_audit_report.md:459` - `backups/email_delivery_v114_20260503_104855/app.py:491` except Exception as log_error:
- `reports/deep_audit_report.md:460` - `backups/email_delivery_v114_20260503_104855/app.py:494` except Exception as error:
- `reports/deep_audit_report.md:461` - `backups/email_delivery_v114_20260503_104855/app.py:497` print("Error:", error)
- `reports/deep_audit_report.md:462` - `backups/email_delivery_v114_20260503_104855/app.py:523` except Exception as error:
- `reports/deep_audit_report.md:463` - `backups/email_delivery_v114_20260503_104855/app.py:526` print("Error:", error)
- `reports/deep_audit_report.md:464` - `backups/email_delivery_v114_20260503_104855/app.py:550` except Exception as error:
- `reports/deep_audit_report.md:465` - `backups/email_delivery_v114_20260503_104855/app.py:553` print("Error:", error)
- `reports/deep_audit_report.md:466` - `backups/email_delivery_v114_20260503_104855/app.py:578` except Exception as error:
- `reports/deep_audit_report.md:467` - `backups/email_delivery_v114_20260503_104855/app.py:789` except Exception as error:
- `reports/deep_audit_report.md:468` - `backups/email_delivery_v114_20260503_104855/app.py:790` print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:469` - `backups/email_delivery_v114_20260503_104855/app.py:899` except Exception as error:
- `reports/deep_audit_report.md:470` - `backups/email_delivery_v114_20260503_104855/app.py:1074` except Exception as error:
- `reports/deep_audit_report.md:471` - `backups/email_delivery_v114_20260503_104855/app.py:1075` print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:472` - `backups/email_delivery_v114_20260503_104855/app.py:1125` except Exception as error:
- `reports/deep_audit_report.md:473` - `backups/email_delivery_v114_20260503_104855/app.py:1126` print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:474` - `backups/email_delivery_v114_20260503_104855/app.py:1205` except Exception as error:
- `reports/deep_audit_report.md:475` - `backups/email_delivery_v114_20260503_104855/app.py:1217` except Exception:
- `reports/deep_audit_report.md:476` - `backups/email_delivery_v114_20260503_104855/app.py:1328` except Exception:
- `reports/deep_audit_report.md:477` - `backups/email_delivery_v114_20260503_104855/app.py:1352` except Exception as error:
- `reports/deep_audit_report.md:478` - `backups/email_delivery_v114_20260503_104855/app.py:1355` except Exception:
- `reports/deep_audit_report.md:479` - `backups/email_delivery_v114_20260503_104855/app.py:1357` print("BETA EVENT LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:480` - `backups/email_delivery_v114_20260503_104855/app.py:1450` except Exception:
- `reports/deep_audit_report.md:481` - `backups/email_delivery_v114_20260503_104855/app.py:1504` except Exception as error:
- `reports/deep_audit_report.md:482` - `backups/email_delivery_v114_20260503_104855/app.py:1505` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:483` - `backups/email_delivery_v114_20260503_104855/app.py:2016` except Exception as error:
- `reports/deep_audit_report.md:484` - `backups/email_delivery_v114_20260503_104855/app.py:2017` print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:485` - `backups/email_delivery_v114_20260503_104855/app.py:2059` except Exception as error:
- `reports/deep_audit_report.md:486` - `backups/email_delivery_v114_20260503_104855/app.py:2060` print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:487` - `backups/email_delivery_v114_20260503_104855/app.py:2090` except Exception as error:
- `reports/deep_audit_report.md:488` - `backups/email_delivery_v114_20260503_104855/app.py:2091` print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:489` - `backups/email_delivery_v114_20260503_104855/app.py:2256` except Exception as error:
- `reports/deep_audit_report.md:490` - `backups/email_delivery_v114_20260503_104855/app.py:2257` print("TRAINING START ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:491` - `backups/email_delivery_v114_20260503_104855/app.py:2398` except Exception:
- `reports/deep_audit_report.md:492` - `backups/email_delivery_v114_20260503_104855/app.py:2802` except Exception as error:
- `reports/deep_audit_report.md:493` - `backups/email_delivery_v114_20260503_104855/app.py:2803` print("FEEDBACK LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:494` - `backups/email_delivery_v114_20260503_104855/app.py:2935` except Exception as error:
- `reports/deep_audit_report.md:495` - `backups/email_delivery_v114_20260503_104855/app.py:2936` print("ADMIN BALANCE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:496` - `backups/email_delivery_v114_20260503_104855/app.py:2963` except Exception as error:
- `reports/deep_audit_report.md:497` - `backups/email_delivery_v114_20260503_104855/app.py:3007` except Exception as error:
- `reports/deep_audit_report.md:498` - `backups/email_delivery_v114_20260503_104855/app.py:3034` except Exception as error:
- `reports/deep_audit_report.md:499` - `backups/email_delivery_v114_20260503_104855/app.py:3035` print("MISSIONS PAGE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:500` - `backups/email_delivery_v114_20260503_104855/app.py:3063` except Exception as error:
- `reports/deep_audit_report.md:501` - `backups/email_delivery_v114_20260503_104855/app.py:3064` print("MISSION CLAIM ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:502` - `backups/email_delivery_v114_20260503_104855/app.py:3121` except Exception as error:
- `reports/deep_audit_report.md:503` - `backups/email_delivery_v114_20260503_104855/app.py:3145` except Exception as error:
- `reports/deep_audit_report.md:504` - `backups/email_delivery_v114_20260503_104855/app.py:3146` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:505` - `backups/email_delivery_v114_20260503_104855/app.py:3165` except Exception as error:
- `reports/deep_audit_report.md:506` - `backups/email_delivery_v114_20260503_104855/app.py:3166` print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:507` - `backups/email_delivery_v114_20260503_104855/services/email_service.py:58` except Exception as error:
- `reports/deep_audit_report.md:508` - `backups/email_delivery_v114_20260503_104855/services/email_service.py:61` print("Error:", error)
- `reports/deep_audit_report.md:509` - `routes/auth.py:68` except Exception as error:
- `reports/deep_audit_report.md:510` - `routes/auth.py:69` print("LOGIN TRACKING ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:511` - `routes/auth.py:75` except Exception as error:
- `reports/deep_audit_report.md:512` - `routes/auth.py:76` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:513` - `routes/auth.py:134` except Exception as error:
- `reports/deep_audit_report.md:514` - `routes/auth.py:135` print("STARTER DECK CREATE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:515` - `routes/auth.py:180` except Exception:
- `reports/deep_audit_report.md:516` - `routes/auth.py:187` except Exception:
- `reports/deep_audit_report.md:517` - `routes/auth.py:253` except Exception:
- `reports/deep_audit_report.md:518` - `routes/public.py:61` except Exception as error:
- `reports/deep_audit_report.md:519` - `routes/public.py:76` except Exception as error:
- `reports/deep_audit_report.md:520` - `routes/public.py:77` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:521` - `routes/public.py:93` except Exception as error:
- `reports/deep_audit_report.md:522` - `routes/public.py:116` except Exception as error:
- `reports/deep_audit_report.md:523` - `routes/game.py:17` except Exception:
- `reports/deep_audit_report.md:524` - `routes/game.py:74` except Exception as error:
- `reports/deep_audit_report.md:525` - `routes/game.py:96` except Exception as error:
- `reports/deep_audit_report.md:526` - `routes/game.py:120` except Exception as error:
- `reports/deep_audit_report.md:527` - `routes/game.py:175` except Exception as error:
- `reports/deep_audit_report.md:528` - `routes/game.py:185` except Exception as error:
- `reports/deep_audit_report.md:529` - `routes/game.py:206` except Exception as error:
- `reports/deep_audit_report.md:530` - `routes/game.py:212` except Exception as error:
- `reports/deep_audit_report.md:531` - `routes/game.py:218` except Exception as error:
- `reports/deep_audit_report.md:532` - `routes/game.py:270` except Exception as error:
- `reports/deep_audit_report.md:533` - `routes/admin.py:44` except Exception as error:
- `reports/deep_audit_report.md:534` - `routes/admin.py:50` except Exception as error:
- `reports/deep_audit_report.md:535` - `routes/admin.py:56` except Exception as error:
- `reports/deep_audit_report.md:536` - `routes/admin.py:80` except Exception as error:
- `reports/deep_audit_report.md:537` - `routes/admin.py:97` except Exception as error:
- `reports/deep_audit_report.md:538` - `routes/admin.py:120` except Exception as error:
- `reports/deep_audit_report.md:539` - `routes/admin.py:137` except Exception as error:
- `reports/deep_audit_report.md:540` - `services/match_telemetry.py:8` except Exception:
- `reports/deep_audit_report.md:541` - `services/match_telemetry.py:19` except Exception:
- `reports/deep_audit_report.md:542` - `services/match_telemetry.py:56` except Exception as error:
- `reports/deep_audit_report.md:543` - `services/match_telemetry.py:57` print("MATCH TELEMETRY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:544` - `services/battle_summary.py:8` except Exception:
- `reports/deep_audit_report.md:545` - `services/email_service.py:62` except Exception as error:
- `reports/deep_audit_report.md:546` - `services/email_service.py:65` print("Error:", error)
- `reports/deep_audit_report.md:547` - `services/database/schema_tools.py:12` except Exception as error:
- `reports/deep_audit_report.md:548` - `services/database/schema_tools.py:34` except Exception as error:
- `reports/deep_audit_report.md:549` - `services/database/schema_tools.py:46` except Exception as error:
- `reports/deep_audit_report.md:550` - `reports/register_audit_report.md:57` except Exception:
- `reports/deep_audit_report.md:551` - `reports/register_audit_report.md:148` except Exception:
- `reports/deep_audit_report.md:552` - `reports/deep_audit_report.md:227` ## TODO/FIXME/Error strings
- `reports/deep_audit_report.md:553` - `reports/deep_audit_report.md:229` - `models.py:249` except Exception:
- `reports/deep_audit_report.md:554` - `reports/deep_audit_report.md:230` - `app.py:118` except Exception as error:
- `reports/deep_audit_report.md:555` - `reports/deep_audit_report.md:231` - `app.py:119` print("SYSTEM LOG ERROR:", error)
- `reports/deep_audit_report.md:556` - `reports/deep_audit_report.md:232` - `app.py:131` except Exception as error:
- `reports/deep_audit_report.md:557` - `reports/deep_audit_report.md:233` - `app.py:132` print("RC EVENT LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:558` - `reports/deep_audit_report.md:234` - `app.py:300` except Exception as error:
- `reports/deep_audit_report.md:559` - `reports/deep_audit_report.md:235` - `app.py:406` except Exception as error:
- `reports/deep_audit_report.md:560` - `reports/deep_audit_report.md:236` - `app.py:472` except Exception as error:
- `reports/deep_audit_report.md:561` - `reports/deep_audit_report.md:237` - `app.py:512` except Exception as error:
- `reports/deep_audit_report.md:562` - `reports/deep_audit_report.md:238` - `app.py:527` except Exception as error:
- `reports/deep_audit_report.md:563` - `reports/deep_audit_report.md:239` - `app.py:530` print("Error:", error)
- `reports/deep_audit_report.md:564` - `reports/deep_audit_report.md:240` - `app.py:584` except Exception as log_error:
- `reports/deep_audit_report.md:565` - `reports/deep_audit_report.md:241` - `app.py:590` except Exception as log_error:
- `reports/deep_audit_report.md:566` - `reports/deep_audit_report.md:242` - `app.py:593` except Exception as error:
- `reports/deep_audit_report.md:567` - `reports/deep_audit_report.md:243` - `app.py:596` print("Error:", error)
- `reports/deep_audit_report.md:568` - `reports/deep_audit_report.md:244` - `app.py:622` except Exception as error:
- `reports/deep_audit_report.md:569` - `reports/deep_audit_report.md:245` - `app.py:625` print("Error:", error)
- `reports/deep_audit_report.md:570` - `reports/deep_audit_report.md:246` - `app.py:649` except Exception as error:
- `reports/deep_audit_report.md:571` - `reports/deep_audit_report.md:247` - `app.py:652` print("Error:", error)
- `reports/deep_audit_report.md:572` - `reports/deep_audit_report.md:248` - `app.py:677` except Exception as error:
- `reports/deep_audit_report.md:573` - `reports/deep_audit_report.md:249` - `app.py:888` except Exception as error:
- `reports/deep_audit_report.md:574` - `reports/deep_audit_report.md:250` - `app.py:889` print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:575` - `reports/deep_audit_report.md:251` - `app.py:952` except Exception:
- `reports/deep_audit_report.md:576` - `reports/deep_audit_report.md:252` - `app.py:973` except Exception as error:
- `reports/deep_audit_report.md:577` - `reports/deep_audit_report.md:253` - `app.py:1013` except Exception as error:
- `reports/deep_audit_report.md:578` - `reports/deep_audit_report.md:254` - `app.py:1030` except Exception as error:
- `reports/deep_audit_report.md:579` - `reports/deep_audit_report.md:255` - `app.py:1052` except Exception as error:
- `reports/deep_audit_report.md:580` - `reports/deep_audit_report.md:256` - `app.py:1111` except Exception as error:
- `reports/deep_audit_report.md:581` - `reports/deep_audit_report.md:257` - `app.py:1112` print("RC FEEDBACK QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:582` - `reports/deep_audit_report.md:258` - `app.py:1116` except Exception as error:
- `reports/deep_audit_report.md:583` - `reports/deep_audit_report.md:259` - `app.py:1117` print("RC LOG QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:584` - `reports/deep_audit_report.md:260` - `app.py:1142` except Exception as error:
- `reports/deep_audit_report.md:585` - `reports/deep_audit_report.md:261` - `app.py:1143` db_status = f"error:{type(error).__name__}"
- `reports/deep_audit_report.md:586` - `reports/deep_audit_report.md:262` - `app.py:1171` except Exception as log_error:
- `reports/deep_audit_report.md:587` - `reports/deep_audit_report.md:263` - `app.py:1172` print("500 LOG ERROR:", type(log_error).__name__, log_error)
- `reports/deep_audit_report.md:588` - `reports/deep_audit_report.md:264` - `app.py:1213` except Exception as error:
- `reports/deep_audit_report.md:589` - `reports/deep_audit_report.md:265` - `app.py:1388` except Exception as error:
- `reports/deep_audit_report.md:590` - `reports/deep_audit_report.md:266` - `app.py:1389` print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:591` - `reports/deep_audit_report.md:267` - `app.py:1439` except Exception as error:
- `reports/deep_audit_report.md:592` - `reports/deep_audit_report.md:268` - `app.py:1440` print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:593` - `reports/deep_audit_report.md:269` - `app.py:1519` except Exception as error:
- `reports/deep_audit_report.md:594` - `reports/deep_audit_report.md:270` - `app.py:1531` except Exception:
- `reports/deep_audit_report.md:595` - `reports/deep_audit_report.md:271` - `app.py:1642` except Exception:
- `reports/deep_audit_report.md:596` - `reports/deep_audit_report.md:272` - `app.py:1666` except Exception as error:
- `reports/deep_audit_report.md:597` - `reports/deep_audit_report.md:273` - `app.py:1669` except Exception:
- `reports/deep_audit_report.md:598` - `reports/deep_audit_report.md:274` - `app.py:1671` print("BETA EVENT LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:599` - `reports/deep_audit_report.md:275` - `app.py:1782` except Exception:
- `reports/deep_audit_report.md:600` - `reports/deep_audit_report.md:276` - `app.py:1858` except Exception as error:
- `reports/deep_audit_report.md:601` - `reports/deep_audit_report.md:277` - `app.py:1859` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:602` - `reports/deep_audit_report.md:278` - `app.py:2484` except Exception as error:
- `reports/deep_audit_report.md:603` - `reports/deep_audit_report.md:279` - `app.py:2485` print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:604` - `reports/deep_audit_report.md:280` - `app.py:2527` except Exception as error:
- `reports/deep_audit_report.md:605` - `reports/deep_audit_report.md:281` - `app.py:2528` print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:606` - `reports/deep_audit_report.md:282` - `app.py:2558` except Exception as error:
- `reports/deep_audit_report.md:607` - `reports/deep_audit_report.md:283` - `app.py:2559` print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:608` - `reports/deep_audit_report.md:284` - `app.py:2797` except Exception as error:
- `reports/deep_audit_report.md:609` - `reports/deep_audit_report.md:285` - `app.py:2798` print("TRAINING START ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:610` - `reports/deep_audit_report.md:286` - `app.py:2926` except Exception:
- `reports/deep_audit_report.md:611` - `reports/deep_audit_report.md:287` - `app.py:3098` except Exception as error:
- `reports/deep_audit_report.md:612` - `reports/deep_audit_report.md:288` - `app.py:3099` print("V2 BATTLE EVENTS EMIT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:613` - `reports/deep_audit_report.md:289` - `app.py:3351` except Exception as error:
- `reports/deep_audit_report.md:614` - `reports/deep_audit_report.md:290` - `app.py:3352` print("FEEDBACK LIMIT CHECK ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:615` - `reports/deep_audit_report.md:291` - `app.py:3374` except Exception as error:
- `reports/deep_audit_report.md:616` - `reports/deep_audit_report.md:292` - `app.py:3375` print("FEEDBACK LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:617` - `reports/deep_audit_report.md:293` - `app.py:3507` except Exception as error:
- `reports/deep_audit_report.md:618` - `reports/deep_audit_report.md:294` - `app.py:3508` print("ADMIN BALANCE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:619` - `reports/deep_audit_report.md:295` - `app.py:3535` except Exception as error:
- `reports/deep_audit_report.md:620` - `reports/deep_audit_report.md:296` - `app.py:3580` except Exception as error:
- `reports/deep_audit_report.md:621` - `reports/deep_audit_report.md:297` - `app.py:3607` except Exception as error:
- `reports/deep_audit_report.md:622` - `reports/deep_audit_report.md:298` - `app.py:3608` print("MISSIONS PAGE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:623` - `reports/deep_audit_report.md:299` - `app.py:3636` except Exception as error:
- `reports/deep_audit_report.md:624` - `reports/deep_audit_report.md:300` - `app.py:3637` print("MISSION CLAIM ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:625` - `reports/deep_audit_report.md:301` - `app.py:3694` except Exception as error:
- `reports/deep_audit_report.md:626` - `reports/deep_audit_report.md:302` - `app.py:3718` except Exception as error:
- `reports/deep_audit_report.md:627` - `reports/deep_audit_report.md:303` - `app.py:3719` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:628` - `reports/deep_audit_report.md:304` - `app.py:3738` except Exception as error:
- `reports/deep_audit_report.md:629` - `reports/deep_audit_report.md:305` - `app.py:3739` print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:630` - `reports/deep_audit_report.md:306` - `migrations/env.py:31` except AttributeError:
- `reports/deep_audit_report.md:631` - `reports/deep_audit_report.md:307` - `tools/audit_routes.py:43` except Exception as error:
- `reports/deep_audit_report.md:632` - `reports/deep_audit_report.md:308` - `tools/audit_database.py:49` except Exception as error:
- `reports/deep_audit_report.md:633` - `reports/deep_audit_report.md:309` - `tools/audit_database.py:52` except Exception as error:
- `reports/deep_audit_report.md:634` - `reports/deep_audit_report.md:310` - `tools/balance_report.py:16` except Exception:
- `reports/deep_audit_report.md:635` - `reports/deep_audit_report.md:311` - `tools/audit_cards.py:23` except Exception as error:
- `reports/deep_audit_report.md:636` - `reports/deep_audit_report.md:312` - `tools/audit_cards.py:62` except Exception:
- `reports/deep_audit_report.md:637` - `reports/deep_audit_report.md:313` - `tools/audit_cards.py:74` except Exception:
- `reports/deep_audit_report.md:638` - `reports/deep_audit_report.md:314` - `tools/fix_deck_builder_v112_manual.py:115` raise SystemExit("ERROR: old checkbox block not found exactly. No changes made.")
- `reports/deep_audit_report.md:639` - `reports/deep_audit_report.md:315` - `tools/deep_audit.py:30` except Exception as e:
- `reports/deep_audit_report.md:640` - `reports/deep_audit_report.md:316` - `tools/deep_audit.py:125` # 8. Broken references: function calls not defined in same file rough scan
- `reports/deep_audit_report.md:641` - `reports/deep_audit_report.md:317` - `tools/deep_audit.py:144` except Exception as e:
- `reports/deep_audit_report.md:642` - `reports/deep_audit_report.md:318` - `tools/deep_audit.py:147` # 9. TODO/FIXME/errors
- `reports/deep_audit_report.md:643` - `reports/deep_audit_report.md:319` - `tools/deep_audit.py:148` section("TODO/FIXME/Error strings")
- `reports/deep_audit_report.md:644` - `reports/deep_audit_report.md:320` - `tools/deep_audit.py:156` except Exception:
- `reports/deep_audit_report.md:645` - `reports/deep_audit_report.md:321` - `tools/deep_audit.py:160` if any(k in low for k in ["todo", "fixme", "hack", "broken", "error:", "except exception", "pass  #"]):
- `reports/deep_audit_report.md:646` - `reports/deep_audit_report.md:322` - `tools/deep_audit.py:179` except Exception:
- `reports/deep_audit_report.md:647` - `reports/deep_audit_report.md:323` - `tools/internal_rc_check.py:42` print("ERROR:", failure)
- `reports/deep_audit_report.md:648` - `reports/deep_audit_report.md:324` - `tools/fix_beta_core_v111.py:118` # The common broken shape has two const cost declarations close together.
- `reports/deep_audit_report.md:649` - `reports/deep_audit_report.md:325` - `tools/preflight.py:31` except Exception as error:
- `reports/deep_audit_report.md:650` - `reports/deep_audit_report.md:326` - `tools/preflight.py:38` print("ERROR:", error)
- `reports/deep_audit_report.md:651` - `reports/deep_audit_report.md:327` - `tools/preflight.py:70` print("ERROR:", error)
- `reports/deep_audit_report.md:652` - `reports/deep_audit_report.md:328` - `game/deck.py:76` except Exception:
- `reports/deep_audit_report.md:653` - `reports/deep_audit_report.md:329` - `game/cards.py:165` "Mastodonte Antigo",
- `reports/deep_audit_report.md:654` - `reports/deep_audit_report.md:330` - `game/match_utils.py:16` except Exception:
- `reports/deep_audit_report.md:655` - `reports/deep_audit_report.md:331` - `templates/first_session.html:67` If anything blocks the path, feels confusing, looks broken on Android,
- `reports/deep_audit_report.md:656` - `reports/deep_audit_report.md:332` - `backups/beta_final_stability_v113_20260503_103647/app.py:104` except Exception as error:
- `reports/deep_audit_report.md:657` - `reports/deep_audit_report.md:333` - `backups/beta_final_stability_v113_20260503_103647/app.py:105` print("SYSTEM LOG ERROR:", error)
- `reports/deep_audit_report.md:658` - `reports/deep_audit_report.md:334` - `backups/beta_final_stability_v113_20260503_103647/app.py:214` except Exception as error:
- `reports/deep_audit_report.md:659` - `reports/deep_audit_report.md:335` - `backups/beta_final_stability_v113_20260503_103647/app.py:226` except Exception as error:
- `reports/deep_audit_report.md:660` - `reports/deep_audit_report.md:336` - `backups/beta_final_stability_v113_20260503_103647/app.py:250` except Exception as error:
- `reports/deep_audit_report.md:661` - `reports/deep_audit_report.md:337` - `backups/beta_final_stability_v113_20260503_103647/app.py:319` except Exception as error:
- `reports/deep_audit_report.md:662` - `reports/deep_audit_report.md:338` - `backups/beta_final_stability_v113_20260503_103647/app.py:334` except Exception as error:
- `reports/deep_audit_report.md:663` - `reports/deep_audit_report.md:339` - `backups/beta_final_stability_v113_20260503_103647/app.py:337` print("Error:", error)
- `reports/deep_audit_report.md:664` - `reports/deep_audit_report.md:340` - `backups/beta_final_stability_v113_20260503_103647/app.py:391` except Exception as log_error:
- `reports/deep_audit_report.md:665` - `reports/deep_audit_report.md:341` - `backups/beta_final_stability_v113_20260503_103647/app.py:397` except Exception as log_error:
- `reports/deep_audit_report.md:666` - `reports/deep_audit_report.md:342` - `backups/beta_final_stability_v113_20260503_103647/app.py:400` except Exception as error:
- `reports/deep_audit_report.md:667` - `reports/deep_audit_report.md:343` - `backups/beta_final_stability_v113_20260503_103647/app.py:403` print("Error:", error)
- `reports/deep_audit_report.md:668` - `reports/deep_audit_report.md:344` - `backups/beta_final_stability_v113_20260503_103647/app.py:429` except Exception as error:
- `reports/deep_audit_report.md:669` - `reports/deep_audit_report.md:345` - `backups/beta_final_stability_v113_20260503_103647/app.py:432` print("Error:", error)
- `reports/deep_audit_report.md:670` - `reports/deep_audit_report.md:346` - `backups/beta_final_stability_v113_20260503_103647/app.py:456` except Exception as error:
- `reports/deep_audit_report.md:671` - `reports/deep_audit_report.md:347` - `backups/beta_final_stability_v113_20260503_103647/app.py:459` print("Error:", error)
- `reports/deep_audit_report.md:672` - `reports/deep_audit_report.md:348` - `backups/beta_final_stability_v113_20260503_103647/app.py:484` except Exception as error:
- `reports/deep_audit_report.md:673` - `reports/deep_audit_report.md:349` - `backups/beta_final_stability_v113_20260503_103647/app.py:695` except Exception as error:
- `reports/deep_audit_report.md:674` - `reports/deep_audit_report.md:350` - `backups/beta_final_stability_v113_20260503_103647/app.py:696` print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:675` - `reports/deep_audit_report.md:351` - `backups/beta_final_stability_v113_20260503_103647/app.py:805` except Exception as error:
- `reports/deep_audit_report.md:676` - `reports/deep_audit_report.md:352` - `backups/beta_final_stability_v113_20260503_103647/app.py:980` except Exception as error:
- `reports/deep_audit_report.md:677` - `reports/deep_audit_report.md:353` - `backups/beta_final_stability_v113_20260503_103647/app.py:981` print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:678` - `reports/deep_audit_report.md:354` - `backups/beta_final_stability_v113_20260503_103647/app.py:1031` except Exception as error:
- `reports/deep_audit_report.md:679` - `reports/deep_audit_report.md:355` - `backups/beta_final_stability_v113_20260503_103647/app.py:1032` print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:680` - `reports/deep_audit_report.md:356` - `backups/beta_final_stability_v113_20260503_103647/app.py:1111` except Exception as error:
- `reports/deep_audit_report.md:681` - `reports/deep_audit_report.md:357` - `backups/beta_final_stability_v113_20260503_103647/app.py:1123` except Exception:
- `reports/deep_audit_report.md:682` - `reports/deep_audit_report.md:358` - `backups/beta_final_stability_v113_20260503_103647/app.py:1234` except Exception:
- `reports/deep_audit_report.md:683` - `reports/deep_audit_report.md:359` - `backups/beta_final_stability_v113_20260503_103647/app.py:1258` except Exception as error:
- `reports/deep_audit_report.md:684` - `reports/deep_audit_report.md:360` - `backups/beta_final_stability_v113_20260503_103647/app.py:1261` except Exception:
- `reports/deep_audit_report.md:685` - `reports/deep_audit_report.md:361` - `backups/beta_final_stability_v113_20260503_103647/app.py:1263` print("BETA EVENT LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:686` - `reports/deep_audit_report.md:362` - `backups/beta_final_stability_v113_20260503_103647/app.py:1356` except Exception:
- `reports/deep_audit_report.md:687` - `reports/deep_audit_report.md:363` - `backups/beta_final_stability_v113_20260503_103647/app.py:1410` except Exception as error:
- `reports/deep_audit_report.md:688` - `reports/deep_audit_report.md:364` - `backups/beta_final_stability_v113_20260503_103647/app.py:1411` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:689` - `reports/deep_audit_report.md:365` - `backups/beta_final_stability_v113_20260503_103647/app.py:1922` except Exception as error:
- `reports/deep_audit_report.md:690` - `reports/deep_audit_report.md:366` - `backups/beta_final_stability_v113_20260503_103647/app.py:1923` print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:691` - `reports/deep_audit_report.md:367` - `backups/beta_final_stability_v113_20260503_103647/app.py:1965` except Exception as error:
- `reports/deep_audit_report.md:692` - `reports/deep_audit_report.md:368` - `backups/beta_final_stability_v113_20260503_103647/app.py:1966` print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:693` - `reports/deep_audit_report.md:369` - `backups/beta_final_stability_v113_20260503_103647/app.py:1996` except Exception as error:
- `reports/deep_audit_report.md:694` - `reports/deep_audit_report.md:370` - `backups/beta_final_stability_v113_20260503_103647/app.py:1997` print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:695` - `reports/deep_audit_report.md:371` - `backups/beta_final_stability_v113_20260503_103647/app.py:2162` except Exception as error:
- `reports/deep_audit_report.md:696` - `reports/deep_audit_report.md:372` - `backups/beta_final_stability_v113_20260503_103647/app.py:2163` print("TRAINING START ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:697` - `reports/deep_audit_report.md:373` - `backups/beta_final_stability_v113_20260503_103647/app.py:2304` except Exception:
- `reports/deep_audit_report.md:698` - `reports/deep_audit_report.md:374` - `backups/beta_final_stability_v113_20260503_103647/app.py:2708` except Exception as error:
- `reports/deep_audit_report.md:699` - `reports/deep_audit_report.md:375` - `backups/beta_final_stability_v113_20260503_103647/app.py:2709` print("FEEDBACK LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:700` - `reports/deep_audit_report.md:376` - `backups/beta_final_stability_v113_20260503_103647/app.py:2841` except Exception as error:
- `reports/deep_audit_report.md:701` - `reports/deep_audit_report.md:377` - `backups/beta_final_stability_v113_20260503_103647/app.py:2842` print("ADMIN BALANCE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:702` - `reports/deep_audit_report.md:378` - `backups/beta_final_stability_v113_20260503_103647/app.py:2869` except Exception as error:
- `reports/deep_audit_report.md:703` - `reports/deep_audit_report.md:379` - `backups/beta_final_stability_v113_20260503_103647/app.py:2913` except Exception as error:
- `reports/deep_audit_report.md:704` - `reports/deep_audit_report.md:380` - `backups/beta_final_stability_v113_20260503_103647/app.py:2940` except Exception as error:
- `reports/deep_audit_report.md:705` - `reports/deep_audit_report.md:381` - `backups/beta_final_stability_v113_20260503_103647/app.py:2941` print("MISSIONS PAGE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:706` - `reports/deep_audit_report.md:382` - `backups/beta_final_stability_v113_20260503_103647/app.py:2969` except Exception as error:
- `reports/deep_audit_report.md:707` - `reports/deep_audit_report.md:383` - `backups/beta_final_stability_v113_20260503_103647/app.py:2970` print("MISSION CLAIM ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:708` - `reports/deep_audit_report.md:384` - `backups/beta_final_stability_v113_20260503_103647/app.py:3027` except Exception as error:
- `reports/deep_audit_report.md:709` - `reports/deep_audit_report.md:385` - `backups/beta_final_stability_v113_20260503_103647/app.py:3051` except Exception as error:
- `reports/deep_audit_report.md:710` - `reports/deep_audit_report.md:386` - `backups/beta_final_stability_v113_20260503_103647/app.py:3052` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:711` - `reports/deep_audit_report.md:387` - `backups/beta_final_stability_v113_20260503_103647/app.py:3071` except Exception as error:
- `reports/deep_audit_report.md:712` - `reports/deep_audit_report.md:388` - `backups/beta_final_stability_v113_20260503_103647/app.py:3072` print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:713` - `reports/deep_audit_report.md:389` - `backups/beta_core_v111_20260503_102709/app.py:104` except Exception as error:
- `reports/deep_audit_report.md:714` - `reports/deep_audit_report.md:390` - `backups/beta_core_v111_20260503_102709/app.py:105` print("SYSTEM LOG ERROR:", error)
- `reports/deep_audit_report.md:715` - `reports/deep_audit_report.md:391` - `backups/beta_core_v111_20260503_102709/app.py:214` except Exception as error:
- `reports/deep_audit_report.md:716` - `reports/deep_audit_report.md:392` - `backups/beta_core_v111_20260503_102709/app.py:226` except Exception as error:
- `reports/deep_audit_report.md:717` - `reports/deep_audit_report.md:393` - `backups/beta_core_v111_20260503_102709/app.py:250` except Exception as error:
- `reports/deep_audit_report.md:718` - `reports/deep_audit_report.md:394` - `backups/beta_core_v111_20260503_102709/app.py:319` except Exception as error:
- `reports/deep_audit_report.md:719` - `reports/deep_audit_report.md:395` - `backups/beta_core_v111_20260503_102709/app.py:334` except Exception as error:
- `reports/deep_audit_report.md:720` - `reports/deep_audit_report.md:396` - `backups/beta_core_v111_20260503_102709/app.py:337` print("Error:", error)
- `reports/deep_audit_report.md:721` - `reports/deep_audit_report.md:397` - `backups/beta_core_v111_20260503_102709/app.py:391` except Exception as log_error:
- `reports/deep_audit_report.md:722` - `reports/deep_audit_report.md:398` - `backups/beta_core_v111_20260503_102709/app.py:397` except Exception as log_error:
- `reports/deep_audit_report.md:723` - `reports/deep_audit_report.md:399` - `backups/beta_core_v111_20260503_102709/app.py:400` except Exception as error:
- `reports/deep_audit_report.md:724` - `reports/deep_audit_report.md:400` - `backups/beta_core_v111_20260503_102709/app.py:403` print("Error:", error)
- `reports/deep_audit_report.md:725` - `reports/deep_audit_report.md:401` - `backups/beta_core_v111_20260503_102709/app.py:429` except Exception as error:
- `reports/deep_audit_report.md:726` - `reports/deep_audit_report.md:402` - `backups/beta_core_v111_20260503_102709/app.py:432` print("Error:", error)
- `reports/deep_audit_report.md:727` - `reports/deep_audit_report.md:403` - `backups/beta_core_v111_20260503_102709/app.py:456` except Exception as error:
- `reports/deep_audit_report.md:728` - `reports/deep_audit_report.md:404` - `backups/beta_core_v111_20260503_102709/app.py:459` print("Error:", error)
- `reports/deep_audit_report.md:729` - `reports/deep_audit_report.md:405` - `backups/beta_core_v111_20260503_102709/app.py:484` except Exception as error:
- `reports/deep_audit_report.md:730` - `reports/deep_audit_report.md:406` - `backups/beta_core_v111_20260503_102709/app.py:695` except Exception as error:
- `reports/deep_audit_report.md:731` - `reports/deep_audit_report.md:407` - `backups/beta_core_v111_20260503_102709/app.py:696` print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:732` - `reports/deep_audit_report.md:408` - `backups/beta_core_v111_20260503_102709/app.py:805` except Exception as error:
- `reports/deep_audit_report.md:733` - `reports/deep_audit_report.md:409` - `backups/beta_core_v111_20260503_102709/app.py:980` except Exception as error:
- `reports/deep_audit_report.md:734` - `reports/deep_audit_report.md:410` - `backups/beta_core_v111_20260503_102709/app.py:981` print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:735` - `reports/deep_audit_report.md:411` - `backups/beta_core_v111_20260503_102709/app.py:1031` except Exception as error:
- `reports/deep_audit_report.md:736` - `reports/deep_audit_report.md:412` - `backups/beta_core_v111_20260503_102709/app.py:1032` print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:737` - `reports/deep_audit_report.md:413` - `backups/beta_core_v111_20260503_102709/app.py:1111` except Exception as error:
- `reports/deep_audit_report.md:738` - `reports/deep_audit_report.md:414` - `backups/beta_core_v111_20260503_102709/app.py:1123` except Exception:
- `reports/deep_audit_report.md:739` - `reports/deep_audit_report.md:415` - `backups/beta_core_v111_20260503_102709/app.py:1234` except Exception:
- `reports/deep_audit_report.md:740` - `reports/deep_audit_report.md:416` - `backups/beta_core_v111_20260503_102709/app.py:1258` except Exception as error:
- `reports/deep_audit_report.md:741` - `reports/deep_audit_report.md:417` - `backups/beta_core_v111_20260503_102709/app.py:1261` except Exception:
- `reports/deep_audit_report.md:742` - `reports/deep_audit_report.md:418` - `backups/beta_core_v111_20260503_102709/app.py:1263` print("BETA EVENT LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:743` - `reports/deep_audit_report.md:419` - `backups/beta_core_v111_20260503_102709/app.py:1356` except Exception:
- `reports/deep_audit_report.md:744` - `reports/deep_audit_report.md:420` - `backups/beta_core_v111_20260503_102709/app.py:1410` except Exception as error:
- `reports/deep_audit_report.md:745` - `reports/deep_audit_report.md:421` - `backups/beta_core_v111_20260503_102709/app.py:1411` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:746` - `reports/deep_audit_report.md:422` - `backups/beta_core_v111_20260503_102709/app.py:1922` except Exception as error:
- `reports/deep_audit_report.md:747` - `reports/deep_audit_report.md:423` - `backups/beta_core_v111_20260503_102709/app.py:1923` print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:748` - `reports/deep_audit_report.md:424` - `backups/beta_core_v111_20260503_102709/app.py:1965` except Exception as error:
- `reports/deep_audit_report.md:749` - `reports/deep_audit_report.md:425` - `backups/beta_core_v111_20260503_102709/app.py:1966` print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:750` - `reports/deep_audit_report.md:426` - `backups/beta_core_v111_20260503_102709/app.py:1996` except Exception as error:
- `reports/deep_audit_report.md:751` - `reports/deep_audit_report.md:427` - `backups/beta_core_v111_20260503_102709/app.py:1997` print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:752` - `reports/deep_audit_report.md:428` - `backups/beta_core_v111_20260503_102709/app.py:2162` except Exception as error:
- `reports/deep_audit_report.md:753` - `reports/deep_audit_report.md:429` - `backups/beta_core_v111_20260503_102709/app.py:2163` print("TRAINING START ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:754` - `reports/deep_audit_report.md:430` - `backups/beta_core_v111_20260503_102709/app.py:2304` except Exception:
- `reports/deep_audit_report.md:755` - `reports/deep_audit_report.md:431` - `backups/beta_core_v111_20260503_102709/app.py:2708` except Exception as error:
- `reports/deep_audit_report.md:756` - `reports/deep_audit_report.md:432` - `backups/beta_core_v111_20260503_102709/app.py:2709` print("FEEDBACK LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:757` - `reports/deep_audit_report.md:433` - `backups/beta_core_v111_20260503_102709/app.py:2841` except Exception as error:
- `reports/deep_audit_report.md:758` - `reports/deep_audit_report.md:434` - `backups/beta_core_v111_20260503_102709/app.py:2842` print("ADMIN BALANCE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:759` - `reports/deep_audit_report.md:435` - `backups/beta_core_v111_20260503_102709/app.py:2869` except Exception as error:
- `reports/deep_audit_report.md:760` - `reports/deep_audit_report.md:436` - `backups/beta_core_v111_20260503_102709/app.py:2913` except Exception as error:
- `reports/deep_audit_report.md:761` - `reports/deep_audit_report.md:437` - `backups/beta_core_v111_20260503_102709/app.py:2940` except Exception as error:
- `reports/deep_audit_report.md:762` - `reports/deep_audit_report.md:438` - `backups/beta_core_v111_20260503_102709/app.py:2941` print("MISSIONS PAGE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:763` - `reports/deep_audit_report.md:439` - `backups/beta_core_v111_20260503_102709/app.py:2969` except Exception as error:
- `reports/deep_audit_report.md:764` - `reports/deep_audit_report.md:440` - `backups/beta_core_v111_20260503_102709/app.py:2970` print("MISSION CLAIM ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:765` - `reports/deep_audit_report.md:441` - `backups/beta_core_v111_20260503_102709/app.py:3027` except Exception as error:
- `reports/deep_audit_report.md:766` - `reports/deep_audit_report.md:442` - `backups/beta_core_v111_20260503_102709/app.py:3051` except Exception as error:
- `reports/deep_audit_report.md:767` - `reports/deep_audit_report.md:443` - `backups/beta_core_v111_20260503_102709/app.py:3052` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:768` - `reports/deep_audit_report.md:444` - `backups/beta_core_v111_20260503_102709/app.py:3071` except Exception as error:
- `reports/deep_audit_report.md:769` - `reports/deep_audit_report.md:445` - `backups/beta_core_v111_20260503_102709/app.py:3072` print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:770` - `reports/deep_audit_report.md:446` - `backups/email_delivery_v114_20260503_104855/app.py:104` except Exception as error:
- `reports/deep_audit_report.md:771` - `reports/deep_audit_report.md:447` - `backups/email_delivery_v114_20260503_104855/app.py:105` print("SYSTEM LOG ERROR:", error)
- `reports/deep_audit_report.md:772` - `reports/deep_audit_report.md:448` - `backups/email_delivery_v114_20260503_104855/app.py:214` except Exception as error:
- `reports/deep_audit_report.md:773` - `reports/deep_audit_report.md:449` - `backups/email_delivery_v114_20260503_104855/app.py:320` except Exception as error:
- `reports/deep_audit_report.md:774` - `reports/deep_audit_report.md:450` - `backups/email_delivery_v114_20260503_104855/app.py:344` except Exception as error:
- `reports/deep_audit_report.md:775` - `reports/deep_audit_report.md:451` - `backups/email_delivery_v114_20260503_104855/app.py:413` except Exception as error:
- `reports/deep_audit_report.md:776` - `reports/deep_audit_report.md:452` - `backups/email_delivery_v114_20260503_104855/app.py:428` except Exception as error:
- `reports/deep_audit_report.md:777` - `reports/deep_audit_report.md:453` - `backups/email_delivery_v114_20260503_104855/app.py:431` print("Error:", error)
- `reports/deep_audit_report.md:778` - `reports/deep_audit_report.md:454` - `backups/email_delivery_v114_20260503_104855/app.py:485` except Exception as log_error:
- `reports/deep_audit_report.md:779` - `reports/deep_audit_report.md:455` - `backups/email_delivery_v114_20260503_104855/app.py:491` except Exception as log_error:
- `reports/deep_audit_report.md:780` - `reports/deep_audit_report.md:456` - `backups/email_delivery_v114_20260503_104855/app.py:494` except Exception as error:
- `reports/deep_audit_report.md:781` - `reports/deep_audit_report.md:457` - `backups/email_delivery_v114_20260503_104855/app.py:497` print("Error:", error)
- `reports/deep_audit_report.md:782` - `reports/deep_audit_report.md:458` - `backups/email_delivery_v114_20260503_104855/app.py:523` except Exception as error:
- `reports/deep_audit_report.md:783` - `reports/deep_audit_report.md:459` - `backups/email_delivery_v114_20260503_104855/app.py:526` print("Error:", error)
- `reports/deep_audit_report.md:784` - `reports/deep_audit_report.md:460` - `backups/email_delivery_v114_20260503_104855/app.py:550` except Exception as error:
- `reports/deep_audit_report.md:785` - `reports/deep_audit_report.md:461` - `backups/email_delivery_v114_20260503_104855/app.py:553` print("Error:", error)
- `reports/deep_audit_report.md:786` - `reports/deep_audit_report.md:462` - `backups/email_delivery_v114_20260503_104855/app.py:578` except Exception as error:
- `reports/deep_audit_report.md:787` - `reports/deep_audit_report.md:463` - `backups/email_delivery_v114_20260503_104855/app.py:789` except Exception as error:
- `reports/deep_audit_report.md:788` - `reports/deep_audit_report.md:464` - `backups/email_delivery_v114_20260503_104855/app.py:790` print("ADMIN BETA EVENTS QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:789` - `reports/deep_audit_report.md:465` - `backups/email_delivery_v114_20260503_104855/app.py:899` except Exception as error:
- `reports/deep_audit_report.md:790` - `reports/deep_audit_report.md:466` - `backups/email_delivery_v114_20260503_104855/app.py:1074` except Exception as error:
- `reports/deep_audit_report.md:791` - `reports/deep_audit_report.md:467` - `backups/email_delivery_v114_20260503_104855/app.py:1075` print("PROFILE MATCH QUERY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:792` - `reports/deep_audit_report.md:468` - `backups/email_delivery_v114_20260503_104855/app.py:1125` except Exception as error:
- `reports/deep_audit_report.md:793` - `reports/deep_audit_report.md:469` - `backups/email_delivery_v114_20260503_104855/app.py:1126` print("RANKING MATCH COUNT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:794` - `reports/deep_audit_report.md:470` - `backups/email_delivery_v114_20260503_104855/app.py:1205` except Exception as error:
- `reports/deep_audit_report.md:795` - `reports/deep_audit_report.md:471` - `backups/email_delivery_v114_20260503_104855/app.py:1217` except Exception:
- `reports/deep_audit_report.md:796` - `reports/deep_audit_report.md:472` - `backups/email_delivery_v114_20260503_104855/app.py:1328` except Exception:
- `reports/deep_audit_report.md:797` - `reports/deep_audit_report.md:473` - `backups/email_delivery_v114_20260503_104855/app.py:1352` except Exception as error:
- `reports/deep_audit_report.md:798` - `reports/deep_audit_report.md:474` - `backups/email_delivery_v114_20260503_104855/app.py:1355` except Exception:
- `reports/deep_audit_report.md:799` - `reports/deep_audit_report.md:475` - `backups/email_delivery_v114_20260503_104855/app.py:1357` print("BETA EVENT LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:800` - `reports/deep_audit_report.md:476` - `backups/email_delivery_v114_20260503_104855/app.py:1450` except Exception:
- `reports/deep_audit_report.md:801` - `reports/deep_audit_report.md:477` - `backups/email_delivery_v114_20260503_104855/app.py:1504` except Exception as error:
- `reports/deep_audit_report.md:802` - `reports/deep_audit_report.md:478` - `backups/email_delivery_v114_20260503_104855/app.py:1505` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:803` - `reports/deep_audit_report.md:479` - `backups/email_delivery_v114_20260503_104855/app.py:2016` except Exception as error:
- `reports/deep_audit_report.md:804` - `reports/deep_audit_report.md:480` - `backups/email_delivery_v114_20260503_104855/app.py:2017` print("V1.05 MATCH SUMMARY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:805` - `reports/deep_audit_report.md:481` - `backups/email_delivery_v114_20260503_104855/app.py:2059` except Exception as error:
- `reports/deep_audit_report.md:806` - `reports/deep_audit_report.md:482` - `backups/email_delivery_v114_20260503_104855/app.py:2060` print("V1.07 POST MATCH PAYLOAD ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:807` - `reports/deep_audit_report.md:483` - `backups/email_delivery_v114_20260503_104855/app.py:2090` except Exception as error:
- `reports/deep_audit_report.md:808` - `reports/deep_audit_report.md:484` - `backups/email_delivery_v114_20260503_104855/app.py:2091` print("V1.07 POST MATCH EMIT ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:809` - `reports/deep_audit_report.md:485` - `backups/email_delivery_v114_20260503_104855/app.py:2256` except Exception as error:
- `reports/deep_audit_report.md:810` - `reports/deep_audit_report.md:486` - `backups/email_delivery_v114_20260503_104855/app.py:2257` print("TRAINING START ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:811` - `reports/deep_audit_report.md:487` - `backups/email_delivery_v114_20260503_104855/app.py:2398` except Exception:
- `reports/deep_audit_report.md:812` - `reports/deep_audit_report.md:488` - `backups/email_delivery_v114_20260503_104855/app.py:2802` except Exception as error:
- `reports/deep_audit_report.md:813` - `reports/deep_audit_report.md:489` - `backups/email_delivery_v114_20260503_104855/app.py:2803` print("FEEDBACK LOG ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:814` - `reports/deep_audit_report.md:490` - `backups/email_delivery_v114_20260503_104855/app.py:2935` except Exception as error:
- `reports/deep_audit_report.md:815` - `reports/deep_audit_report.md:491` - `backups/email_delivery_v114_20260503_104855/app.py:2936` print("ADMIN BALANCE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:816` - `reports/deep_audit_report.md:492` - `backups/email_delivery_v114_20260503_104855/app.py:2963` except Exception as error:
- `reports/deep_audit_report.md:817` - `reports/deep_audit_report.md:493` - `backups/email_delivery_v114_20260503_104855/app.py:3007` except Exception as error:
- `reports/deep_audit_report.md:818` - `reports/deep_audit_report.md:494` - `backups/email_delivery_v114_20260503_104855/app.py:3034` except Exception as error:
- `reports/deep_audit_report.md:819` - `reports/deep_audit_report.md:495` - `backups/email_delivery_v114_20260503_104855/app.py:3035` print("MISSIONS PAGE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:820` - `reports/deep_audit_report.md:496` - `backups/email_delivery_v114_20260503_104855/app.py:3063` except Exception as error:
- `reports/deep_audit_report.md:821` - `reports/deep_audit_report.md:497` - `backups/email_delivery_v114_20260503_104855/app.py:3064` print("MISSION CLAIM ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:822` - `reports/deep_audit_report.md:498` - `backups/email_delivery_v114_20260503_104855/app.py:3121` except Exception as error:
- `reports/deep_audit_report.md:823` - `reports/deep_audit_report.md:499` - `backups/email_delivery_v114_20260503_104855/app.py:3145` except Exception as error:
- `reports/deep_audit_report.md:824` - `reports/deep_audit_report.md:500` - `backups/email_delivery_v114_20260503_104855/app.py:3146` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:825` - `reports/deep_audit_report.md:501` - `backups/email_delivery_v114_20260503_104855/app.py:3165` except Exception as error:
- `reports/deep_audit_report.md:826` - `reports/deep_audit_report.md:502` - `backups/email_delivery_v114_20260503_104855/app.py:3166` print("PROGRESSION HUB MISSIONS ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:827` - `reports/deep_audit_report.md:503` - `backups/email_delivery_v114_20260503_104855/services/email_service.py:58` except Exception as error:
- `reports/deep_audit_report.md:828` - `reports/deep_audit_report.md:504` - `backups/email_delivery_v114_20260503_104855/services/email_service.py:61` print("Error:", error)
- `reports/deep_audit_report.md:829` - `reports/deep_audit_report.md:505` - `routes/auth.py:68` except Exception as error:
- `reports/deep_audit_report.md:830` - `reports/deep_audit_report.md:506` - `routes/auth.py:69` print("LOGIN TRACKING ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:831` - `reports/deep_audit_report.md:507` - `routes/auth.py:75` except Exception as error:
- `reports/deep_audit_report.md:832` - `reports/deep_audit_report.md:508` - `routes/auth.py:76` print("LOGIN ONBOARDING CHECK ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:833` - `reports/deep_audit_report.md:509` - `routes/auth.py:134` except Exception as error:
- `reports/deep_audit_report.md:834` - `reports/deep_audit_report.md:510` - `routes/auth.py:135` print("STARTER DECK CREATE ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:835` - `reports/deep_audit_report.md:511` - `routes/auth.py:180` except Exception:
- `reports/deep_audit_report.md:836` - `reports/deep_audit_report.md:512` - `routes/auth.py:187` except Exception:
- `reports/deep_audit_report.md:837` - `reports/deep_audit_report.md:513` - `routes/auth.py:253` except Exception:
- `reports/deep_audit_report.md:838` - `reports/deep_audit_report.md:514` - `routes/public.py:61` except Exception as error:
- `reports/deep_audit_report.md:839` - `reports/deep_audit_report.md:515` - `routes/public.py:76` except Exception as error:
- `reports/deep_audit_report.md:840` - `reports/deep_audit_report.md:516` - `routes/public.py:77` print("WELCOME RENDER ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:841` - `reports/deep_audit_report.md:517` - `routes/public.py:93` except Exception as error:
- `reports/deep_audit_report.md:842` - `reports/deep_audit_report.md:518` - `routes/public.py:116` except Exception as error:
- `reports/deep_audit_report.md:843` - `reports/deep_audit_report.md:519` - `routes/game.py:17` except Exception:
- `reports/deep_audit_report.md:844` - `reports/deep_audit_report.md:520` - `routes/game.py:74` except Exception as error:
- `reports/deep_audit_report.md:845` - `reports/deep_audit_report.md:521` - `routes/game.py:96` except Exception as error:
- `reports/deep_audit_report.md:846` - `reports/deep_audit_report.md:522` - `routes/game.py:120` except Exception as error:
- `reports/deep_audit_report.md:847` - `reports/deep_audit_report.md:523` - `routes/game.py:175` except Exception as error:
- `reports/deep_audit_report.md:848` - `reports/deep_audit_report.md:524` - `routes/game.py:185` except Exception as error:
- `reports/deep_audit_report.md:849` - `reports/deep_audit_report.md:525` - `routes/game.py:206` except Exception as error:
- `reports/deep_audit_report.md:850` - `reports/deep_audit_report.md:526` - `routes/game.py:212` except Exception as error:
- `reports/deep_audit_report.md:851` - `reports/deep_audit_report.md:527` - `routes/game.py:218` except Exception as error:
- `reports/deep_audit_report.md:852` - `reports/deep_audit_report.md:528` - `routes/game.py:270` except Exception as error:
- `reports/deep_audit_report.md:853` - `reports/deep_audit_report.md:529` - `routes/admin.py:44` except Exception as error:
- `reports/deep_audit_report.md:854` - `reports/deep_audit_report.md:530` - `routes/admin.py:50` except Exception as error:
- `reports/deep_audit_report.md:855` - `reports/deep_audit_report.md:531` - `routes/admin.py:56` except Exception as error:
- `reports/deep_audit_report.md:856` - `reports/deep_audit_report.md:532` - `routes/admin.py:80` except Exception as error:
- `reports/deep_audit_report.md:857` - `reports/deep_audit_report.md:533` - `routes/admin.py:97` except Exception as error:
- `reports/deep_audit_report.md:858` - `reports/deep_audit_report.md:534` - `routes/admin.py:120` except Exception as error:
- `reports/deep_audit_report.md:859` - `reports/deep_audit_report.md:535` - `routes/admin.py:137` except Exception as error:
- `reports/deep_audit_report.md:860` - `reports/deep_audit_report.md:536` - `services/match_telemetry.py:8` except Exception:
- `reports/deep_audit_report.md:861` - `reports/deep_audit_report.md:537` - `services/match_telemetry.py:19` except Exception:
- `reports/deep_audit_report.md:862` - `reports/deep_audit_report.md:538` - `services/match_telemetry.py:56` except Exception as error:
- `reports/deep_audit_report.md:863` - `reports/deep_audit_report.md:539` - `services/match_telemetry.py:57` print("MATCH TELEMETRY ERROR:", type(error).__name__, error)
- `reports/deep_audit_report.md:864` - `reports/deep_audit_report.md:540` - `services/battle_summary.py:8` except Exception:
- `reports/deep_audit_report.md:865` - `reports/deep_audit_report.md:541` - `services/email_service.py:62` except Exception as error:
- `reports/deep_audit_report.md:866` - `reports/deep_audit_report.md:542` - `services/email_service.py:65` print("Error:", error)
- `reports/deep_audit_report.md:867` - `reports/deep_audit_report.md:543` - `services/database/schema_tools.py:12` except Exception as error:
- `reports/deep_audit_report.md:868` - `reports/deep_audit_report.md:544` - `services/database/schema_tools.py:34` except Exception as error:
- `reports/deep_audit_report.md:869` - `reports/deep_audit_report.md:545` - `services/database/schema_tools.py:46` except Exception as error:

## Security quick scan

- Secret key: `config.py:60`
- Email body logging: `app.py:296`
- Hardcoded password: `tools/ensure_admin.py:13`
- Secret key: `tools/audit_config.py:34`
- Email body logging: `tools/deep_audit.py:170`
- Hardcoded password: `tests/conftest.py:82`
- Hardcoded password: `tests/test_release_candidate_smoke.py:87`
- Hardcoded password: `tests/test_release_candidate_smoke.py:109`
- Hardcoded password: `tests/test_release_candidate_smoke.py:138`
- CORS wildcard: `backups/beta_final_stability_v113_20260503_103647/app.py:66`
- CORS wildcard: `backups/beta_core_v111_20260503_102709/app.py:66`
- CORS wildcard: `backups/email_delivery_v114_20260503_104855/app.py:66`
- Email body logging: `routes/auth.py:36`
- Email body logging: `services/email_service.py:38`
- Email body logging: `services/email_service.py:75`

## Existing project checks

### /Users/lucassilverio/Desktop/Ambition/.venv/bin/python tools/preflight.py
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
USERS TOTAL: 5
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
REGISTERED ENDPOINTS: 57
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
OK: No unresolved runtime errors [recommended] - 0 unresolved error logs
OK: Tester accounts exist [recommended] - 5 total users, 5 verified
OK: Match history records exist [recommended] - 9 saved matches
OK: Recent match length is readable [recommended] - 1.6 average rounds over 9/20 recent matches
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
- Monster summary: {'count': 21, 'min': 1235, 'max': 1950, 'avg': 1550.9, 'median': 1527}

### Starter Type Distribution

- Monster: 21
- Spell: 6
- Trap: 3

### Starter Element Distribution

- Global: 9
- Fire: 6
- Water: 5
- Earth: 5
- Plant: 5

### Starter Sigil Distribution

- Global: 9
- Fury: 6
- Insight: 5
- Resolve: 5
- Harmony: 5

### Starter Rarity Distribution

- Common: 21
- Uncommon: 9


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
### /Users/lucassilverio/Desktop/Ambition/.venv/bin/python tools/internal_rc_check.py
Exit code: 0
```
INTERNAL RC STATUS: READY
REQUIRED OK: True
RECOMMENDED OK: False
OK: Database responds [required] - Database query OK
FAIL: Email delivery configured [recommended] - SMTP missing or incomplete
OK: Critical routes do not 500 [required] - /=200, /health=200, /login=200, /register=200, /training=302, /arena=302, /feedback=302, /missions=302, /shop=302
OK: No open critical feedback [required] - 0 open critical reports
OK: No unresolved runtime errors [recommended] - 0 unresolved error logs
OK: Tester accounts exist [recommended] - 5 total users, 5 verified
OK: Match history records exist [recommended] - 9 saved matches
OK: Recent match length is readable [recommended] - 1.6 average rounds over 9/20 recent matches
/Users/lucassilverio/Desktop/Ambition/.venv/lib/python3.9/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'. See: https://github.com/urllib3/urllib3/issues/3020
  warnings.warn(
```
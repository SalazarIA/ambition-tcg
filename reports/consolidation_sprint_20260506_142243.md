# Ambitionz — Consolidation Sprint Audit

=== STATUS ===
?? reports/consolidation_sprint_20260506_142243.md

=== PYTHON COMPILE ===

=== JS CHECK ===
Checking static/js/ambition_battle_events.js
Checking static/js/ambitionz_dom.js
Checking static/js/battle_premium.js
Checking static/js/card_ui_v103.js
Checking static/js/deck_builder.js
Checking static/js/deck_builder_premium.js
Checking static/js/game.js
Checking static/js/mobile-native.js
Checking static/js/pwa.js
Checking static/js/service-worker.js

=== CSS / PWA FILES ===
OK static/manifest.webmanifest
OK static/js/service-worker.js
OK static/js/pwa.js
OK static/css/style.css
OK static/css/gameplay_premium.css
OK static/icons/icon-192.png
OK static/icons/icon-512.png
OK static/icons/maskable-icon-192.png
OK static/icons/maskable-icon-512.png
OK static/icons/apple-touch-icon.png

=== FLASK ROUTE AUDIT ===
/Users/lucassilverio/Desktop/Ambition/.venv/lib/python3.9/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'. See: https://github.com/urllib3/urllib3/issues/3020
  warnings.warn(
Registered routes:
/                                             GET        -> index
/admin                                        GET        -> admin
/admin/balance                                GET        -> admin_balance
/admin/beta-events                            GET        -> admin_beta_events
/admin/clear-gameplay-data                    POST       -> admin_clear_gameplay_data
/admin/dev-tools                              GET        -> admin_dev_tools
/admin/feedback                               GET        -> admin_feedback
/admin/feedback/<int:report_id>/update        POST       -> admin_feedback_update
/admin/invites                                GET,POST   -> admin_invites
/admin/ping                                   GET        -> admin_ping
/admin/release-candidate                      GET        -> admin_release_candidate
/admin/reports                                GET        -> admin_reports
/admin/reset-test-users                       POST       -> admin_reset_test_users
/admin/system                                 GET        -> admin_system
/admin/test-email                             POST       -> admin_test_email
/admin/users                                  GET        -> admin_users
/admin/users/<int:user_id>/ban                POST       -> admin_ban_user
/admin/users/<int:user_id>/toggle-admin       POST       -> admin_toggle_admin
/admin/users/<int:user_id>/toggle-tester      POST       -> admin_toggle_tester
/admin/users/<int:user_id>/unban              POST       -> admin_unban_user
/admin/users/<int:user_id>/verify             POST       -> admin_verify_user
/admin/whoami                                 GET        -> admin_whoami
/api/beta-event                               POST       -> beta_event
/api/retention/event                          POST       -> api_retention_event
/arena                                        GET        -> arena
/auto-build-deck                              POST       -> auto_build_deck
/beta-launch                                  GET        -> beta_launch
/booster-history                              GET        -> booster_history
/campaign                                     GET        -> campaign
/closed-test                                  GET        -> closed_test
/collection                                   GET        -> collection
/complete-onboarding                          POST       -> complete_onboarding
/confirm_email/<token>                        GET        -> confirm_email
/daily                                        GET        -> daily
/data-deletion                                GET        -> data_deletion
/debug/routes                                 GET        -> debug_routes
/deck-builder                                 GET,POST   -> deck_builder
/feedback                                     GET,POST   -> feedback
/first-session                                GET        -> first_session
/forgot-password                              GET,POST   -> forgot_password
/health                                       GET        -> health
/how-to-play                                  GET        -> how_to_play
/leaderboard                                  GET        -> leaderboard
/login                                        GET,POST   -> login
/logout                                       GET        -> logout
/manifest.webmanifest                         GET        -> pwa_manifest
/match-history                                GET        -> match_history
/missions                                     GET        -> missions
/missions/claim/<int:mission_id>              POST       -> claim_user_mission
/offline                                      GET        -> offline
/privacy                                      GET        -> privacy
/profile                                      GET        -> profile
/progression                                  GET        -> progression
/ranking                                      GET        -> ranking
/register                                     GET,POST   -> register
/resend-verification                          GET,POST   -> resend_verification
/reset-password/<token>                       GET,POST   -> reset_password
/service-worker.js                            GET        -> service_worker
/shop                                         GET,POST   -> shop
/static/<path:filename>                       GET        -> static
/support                                      GET        -> support
/terms                                        GET        -> terms
/training                                     GET        -> training
/tutorial                                     GET        -> tutorial
/welcome                                      GET        -> welcome

=== TEMPLATE URL_FOR AUDIT ===
/Users/lucassilverio/Desktop/Ambition/.venv/lib/python3.9/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'. See: https://github.com/urllib3/urllib3/issues/3020
  warnings.warn(
BAD URL_FOR REFERENCES:
templates/daily.html: missing endpoint 'claim_mission_route'

=== PUBLIC ROUTE RESPONSE AUDIT ===
/Users/lucassilverio/Desktop/Ambition/.venv/lib/python3.9/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'. See: https://github.com/urllib3/urllib3/issues/3020
  warnings.warn(
OK   /health                                  200 application/json                    155
OK   /                                        200 text/html; charset=utf-8            8277
OK   /tutorial                                200 text/html; charset=utf-8            5081
OK   /campaign                                200 text/html; charset=utf-8            5994
OK   /daily                                   200 text/html; charset=utf-8            2907
OK   /leaderboard                             200 text/html; charset=utf-8            8732
OK   /ranking                                 200 text/html; charset=utf-8            6962
OK   /profile                                 302 text/html; charset=utf-8            199
OK   /progression                             302 text/html; charset=utf-8            199
OK   /missions                                302 text/html; charset=utf-8            199
OK   /shop                                    302 text/html; charset=utf-8            199
OK   /collection                              302 text/html; charset=utf-8            199
OK   /deck-builder                            302 text/html; charset=utf-8            199
OK   /arena                                   302 text/html; charset=utf-8            199
OK   /training                                302 text/html; charset=utf-8            199
OK   /match-history                           302 text/html; charset=utf-8            199
OK   /feedback                                302 text/html; charset=utf-8            199
OK   /how-to-play                             200 text/html; charset=utf-8            4953
OK   /manifest.webmanifest                    200 application/manifest+json           1820
OK   /service-worker.js                       200 text/javascript; charset=utf-8      2517
OK   /static/manifest.webmanifest             200 application/manifest+json           1820
OK   /static/js/service-worker.js             200 text/javascript; charset=utf-8      2517
OK   /static/js/pwa.js                        200 text/javascript; charset=utf-8      12441
OK   /static/js/game.js                       200 text/javascript; charset=utf-8      23938
OK   /static/js/deck_builder.js               200 text/javascript; charset=utf-8      8825
OK   /static/js/battle_premium.js             200 text/javascript; charset=utf-8      4650
OK   /static/js/deck_builder_premium.js       200 text/javascript; charset=utf-8      4544
OK   /static/css/style.css                    200 text/css; charset=utf-8             181095
OK   /static/css/gameplay_premium.css         200 text/css; charset=utf-8             4014
OK   /static/icons/icon-192.png               200 image/png                           41954
OK   /static/icons/icon-512.png               200 image/png                           243761
OK   /static/icons/maskable-icon-192.png      200 image/png                           44120
OK   /static/icons/maskable-icon-512.png      200 image/png                           254651
OK   /static/icons/apple-touch-icon.png       200 image/png                           38059

=== RETENTION EVENT API AUDIT ===
/Users/lucassilverio/Desktop/Ambition/.venv/lib/python3.9/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'. See: https://github.com/urllib3/urllib3/issues/3020
  warnings.warn(
400 text/html; charset=utf-8 <!doctype html>
<html lang=en>
<title>400 Bad Request</title>
<h1>Bad Request</h1>
<p>Invalid CSRF token.</p>


=== GIT DIFF STAT ===

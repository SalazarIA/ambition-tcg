from pathlib import Path

files = {
    "app": Path("app.py").read_text(errors="ignore"),
    "arena_js": Path("static/js/arena_clean_v48.js").read_text(errors="ignore"),
    "arena_css": Path("static/css/arena_clean_v48.css").read_text(errors="ignore"),
    "card_css": Path("static/css/card_system_v1.css").read_text(errors="ignore"),
    "profile": Path("templates/profile.html").read_text(errors="ignore"),
}

checks = {
    "be2_reward_finalizer": "finalize_be2_match" in files["app"],
    "post_match_summary_backend": "post_match_summary" in files["app"],
    "clean_arena_handles_game_over": "game_over" in files["arena_js"],
    "clean_arena_logs_results": "appendLog(message)" in files["arena_js"],
    "clean_arena_statusbar": "az48-statusbar" in files["arena_css"],
    "profile_css": "Profile Progression AAA Polish" in files["card_css"],
    "profile_hero": "az-profile-hero-v1" in files["profile"],
    "profile_stats": "az-profile-stat-grid-v1" in files["profile"],
    "profile_actions": "az-profile-action-grid-v1" in files["profile"],
}

print("# Reward Modal + Profile Polish Audit")

failed = False

for key, ok in checks.items():
    print(("OK" if ok else "FAIL"), key)
    if not ok:
        failed = True

if failed:
    raise SystemExit("REWARD_PROFILE_AUDIT_FAILED")

print("REWARD_PROFILE_AUDIT_PASSED")

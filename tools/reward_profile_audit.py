from pathlib import Path

files = {
    "state": Path("services/match_state_v1.py").read_text(errors="ignore"),
    "arena_js": Path("static/js/arena_app.js").read_text(errors="ignore"),
    "arena_css": Path("static/css/arena_app.css").read_text(errors="ignore"),
    "card_css": Path("static/css/card_system_v1.css").read_text(errors="ignore"),
    "profile": Path("templates/profile.html").read_text(errors="ignore"),
}

checks = {
    "reward_preview_backend": "reward_preview" in files["state"],
    "reward_modal_js": "function showRewardModal(match)" in files["arena_js"],
    "reward_modal_css": "Match Result Reward Modal" in files["arena_css"],
    "reward_actions": "az-reward-actions" in files["arena_js"],
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

from pathlib import Path

files = {
    "models": Path("models.py").read_text(errors="ignore"),
    "app": Path("app.py").read_text(errors="ignore"),
    "rewards": Path("services/match_rewards_v1.py").read_text(errors="ignore"),
    "history_detail": Path("templates/match_history_detail.html").read_text(errors="ignore") if Path("templates/match_history_detail.html").exists() else "",
    "history": Path("templates/match_history.html").read_text(errors="ignore"),
    "css": Path("static/css/card_system_v1.css").read_text(errors="ignore"),
}

checks = {
    "reward_ledger_model": "class RewardLedger" in files["models"],
    "reward_ledger_schema": "ensure_reward_ledger_schema" in files["models"],
    "app_import_ledger": "ensure_reward_ledger_schema" in files["app"],
    "reward_service_ledger": "create_reward_ledger" in files["rewards"],
    "already_rewarded_ledger": "ledger_exists" in files["rewards"],
    "history_detail_route": '"/match-history/<int:history_id>"' in files["app"],
    "history_detail_template": "match-detail-hero-v1" in files["history_detail"],
    "history_css": "Match History Details Polish" in files["css"],
}

print("# Reward Ledger + Match History Details Audit")

failed = False

for key, ok in checks.items():
    print(("OK" if ok else "FAIL"), key)
    if not ok:
        failed = True

if failed:
    raise SystemExit("REWARD_LEDGER_HISTORY_AUDIT_FAILED")

print("REWARD_LEDGER_HISTORY_AUDIT_PASSED")

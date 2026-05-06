from services.match_actions_v1 import create_training_match_v1, set_intent, play_card, declare_ready
from services.match_rewards_v1 import preview_reward_for_match, persist_rewards_for_user


class FakeUser:
    id = 999999
    username = "audit_user"
    coins = 0
    xp = 0
    level = 1


match = create_training_match_v1(FakeUser(), "sid", "room")
card_id = match["p1"]["hand"][0]["id"]

set_intent(match, "p1", "Strike")
play_card(match, "p1", card_id)
declare_ready(match, "p1")

# Force finish for service audit without DB commit.
match["phase"] = "finished"
match["winner"] = "p1"

preview = preview_reward_for_match(match, "p1")

print("# Reward History V1 Audit")
print("preview", preview)

if not preview.get("available"):
    raise SystemExit("FAILED: reward preview unavailable")

if preview.get("xp", 0) <= 0 or preview.get("coins", 0) <= 0:
    raise SystemExit("FAILED: reward preview has no reward")

print("REWARD_HISTORY_V1_AUDIT_PASSED")

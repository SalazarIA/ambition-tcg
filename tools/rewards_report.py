from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.reward_tuning import REWARD_TABLE, DIFFICULTY_MULTIPLIER, calculate_reward


def generate_report():
    lines = []
    lines.append("# Ambitionz V1.05 Rewards Report\n")

    lines.append("## Reward Table\n")
    for mode, results in REWARD_TABLE.items():
        lines.append(f"### {mode.upper()}\n")
        for result, reward in results.items():
            lines.append(f"- {result}: {reward['coins']} coins / {reward['xp']} XP")
        lines.append("")

    lines.append("## Training Difficulty Multipliers\n")
    for difficulty, multiplier in DIFFICULTY_MULTIPLIER.items():
        win = calculate_reward("training", "win", difficulty)
        loss = calculate_reward("training", "loss", difficulty)
        lines.append(
            f"- {difficulty}: x{multiplier} | win={win['coins']} coins/{win['xp']} XP | "
            f"loss={loss['coins']} coins/{loss['xp']} XP"
        )

    lines.append("\n## Design Notes\n")
    lines.append("- PvP rewards are intentionally higher than training rewards.")
    lines.append("- Training rewards scale with difficulty.")
    lines.append("- Loss rewards still grant progression to reduce early churn.")
    lines.append("- This report defines the reward baseline for later admin/balance tuning.")

    return "\n".join(lines) + "\n"


def main():
    output_path = Path("reports/rewards_report_v105.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = generate_report()
    output_path.write_text(report, encoding="utf-8")

    print(f"Rewards report written to {output_path}")
    print(report)


if __name__ == "__main__":
    main()

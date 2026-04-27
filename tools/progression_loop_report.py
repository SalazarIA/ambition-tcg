from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game.progression_loop import (
    PROGRESSION_LOOP_VERSION,
    CORE_LOOP,
    PROGRESSION_SYSTEMS,
    REWARD_PHILOSOPHY,
    MISSION_DESIGN_RULES,
    BOOSTER_DESIGN_RULES,
    RETENTION_TARGETS,
)


def generate_report():
    lines = []
    lines.append("# Ambitionz V1.06 Progression Loop Report\\n")
    lines.append("- Version: {}\\n".format(PROGRESSION_LOOP_VERSION))

    lines.append("## Core Loop\\n")
    for index, item in enumerate(CORE_LOOP, start=1):
        lines.append("### {}. {}\\n".format(index, item["step"]))
        lines.append("- Purpose: {}".format(item["purpose"]))
        lines.append("- Player feeling: {}\\n".format(item["player_feeling"]))

    lines.append("## Progression Systems\\n")
    for name, data in PROGRESSION_SYSTEMS.items():
        lines.append("### {}\\n".format(name.upper()))
        lines.append("- Role: {}".format(data["role"]))
        lines.append("- Design rule: {}".format(data["design_rule"]))
        lines.append("- Future use: {}\\n".format(data["future_use"]))

    lines.append("## Reward Philosophy\\n")
    for key, value in REWARD_PHILOSOPHY.items():
        lines.append("- {}: {}".format(key, value))

    lines.append("\\n## Mission Design Rules\\n")
    for rule in MISSION_DESIGN_RULES:
        lines.append("- {}".format(rule))

    lines.append("\\n## Booster Design Rules\\n")
    for rule in BOOSTER_DESIGN_RULES:
        lines.append("- {}".format(rule))

    lines.append("\\n## Retention Targets\\n")
    for target in RETENTION_TARGETS:
        lines.append("- {}".format(target))

    return "\\n".join(lines) + "\\n"


def main():
    output_path = Path("reports/progression_loop_report_v106.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = generate_report()
    output_path.write_text(report, encoding="utf-8")
    print("Progression loop report written to {}".format(output_path))
    print(report)


if __name__ == "__main__":
    main()

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game.card_identity import (
    CARD_IDENTITY_VERSION,
    ELEMENT_IDENTITIES,
    ARCHETYPES,
    SIGIL_CARD_DIRECTIONS,
    CARD_WRITING_RULES,
    BETA_DECK_GOALS,
)


def generate_report():
    lines = []
    lines.append("# Ambitionz V1.06 Card Identity Report\n")
    lines.append("- Version: {}\n".format(CARD_IDENTITY_VERSION))

    lines.append("## Element Identities\n")
    for element, data in ELEMENT_IDENTITIES.items():
        lines.append("### {}\n".format(element))
        lines.append("- Fantasy: {}".format(data["fantasy"]))
        lines.append("- Mechanical focus: {}".format(data["mechanical_focus"]))
        lines.append("- Naming style: {}".format(data["naming_style"]))
        lines.append("- Lore direction: {}\n".format(data["sample_lore"]))

    lines.append("## Archetypes\n")
    for name, data in ARCHETYPES.items():
        lines.append("### {}\n".format(name))
        lines.append("- Elements: {}".format(", ".join(data["elements"])))
        lines.append("- Sigils: {}".format(", ".join(data["sigils"])))
        lines.append("- Style: {}".format(data["style"]))
        lines.append("- Risk: {}\n".format(data["risk"]))

    lines.append("## Sigil Card Directions\n")
    for sigil, data in SIGIL_CARD_DIRECTIONS.items():
        lines.append("### {}\n".format(sigil))
        lines.append("- Effect direction: {}".format(data["effect_direction"]))
        lines.append("- Ideal text length: {}".format(data["ideal_text_length"]))
        lines.append("- Avoid: {}\n".format(data["avoid"]))

    lines.append("## Card Writing Rules\n")
    for rule in CARD_WRITING_RULES:
        lines.append("- {}".format(rule))

    lines.append("\n## Beta Deck Goals\n")
    for goal in BETA_DECK_GOALS:
        lines.append("- {}".format(goal))

    return "\n".join(lines) + "\n"


def main():
    output_path = Path("reports/card_identity_report_v106.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = generate_report()
    output_path.write_text(report, encoding="utf-8")

    print("Card identity report written to {}".format(output_path))
    print(report)


if __name__ == "__main__":
    main()

from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game.cards import CARD_CATALOG


def generate_report():
    archetypes = Counter(card.get("archetype", "Unknown") for card in CARD_CATALOG)
    identity_roles = Counter(card.get("identity_role", "Unknown") for card in CARD_CATALOG)
    missing_lore = [card["id"] for card in CARD_CATALOG if not card.get("lore")]
    missing_hint = [card["id"] for card in CARD_CATALOG if not card.get("tactical_hint")]

    lines = []
    lines.append("# Ambitionz V1.09 Applied Card Identity Report\n")

    lines.append("## Summary\n")
    lines.append(f"- Total cards: {len(CARD_CATALOG)}")
    lines.append(f"- Cards missing lore: {len(missing_lore)}")
    lines.append(f"- Cards missing tactical hint: {len(missing_hint)}\n")

    lines.append("## Archetype Distribution\n")
    for archetype, amount in archetypes.most_common():
        lines.append(f"- {archetype}: {amount}")

    lines.append("\n## Identity Role Distribution\n")
    for role, amount in identity_roles.most_common():
        lines.append(f"- {role}: {amount}")

    lines.append("\n## Starter Samples\n")
    for card in CARD_CATALOG[:12]:
        lines.append(
            f"- **{card.get('name')}** `{card.get('id')}` "
            f"| {card.get('element')} / {card.get('sigil')} "
            f"| {card.get('archetype')} / {card.get('identity_role')} "
            f"| lore: {card.get('lore')}"
        )

    if missing_lore:
        lines.append("\n## Missing Lore IDs\n")
        for card_id in missing_lore[:50]:
            lines.append(f"- {card_id}")

    if missing_hint:
        lines.append("\n## Missing Tactical Hint IDs\n")
        for card_id in missing_hint[:50]:
            lines.append(f"- {card_id}")

    return "\n".join(lines) + "\n"


def main():
    output_path = Path("reports/applied_card_identity_report_v109.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = generate_report()
    output_path.write_text(report, encoding="utf-8")

    print(f"Applied card identity report written to {output_path}")
    print(report)


if __name__ == "__main__":
    main()

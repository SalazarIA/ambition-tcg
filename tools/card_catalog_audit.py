from collections import Counter, defaultdict
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from game.cards import CARD_CATALOG
from game.card_sets import (
    BASE_SET_SIZE_TARGET,
    enrich_card_catalog,
    normalize_type,
    normalize_rarity,
)


def main():
    cards = enrich_card_catalog(CARD_CATALOG)

    total = len(cards)
    types = Counter(normalize_type(card.get("type")) for card in cards)
    rarities = Counter(normalize_rarity(card.get("rarity")) for card in cards)
    elements = Counter(card.get("element") or "Neutral" for card in cards)
    sigils = Counter(card.get("sigil") or "None" for card in cards)
    roles = Counter(card.get("role") or "None" for card in cards)

    names = [card.get("name") for card in cards]
    duplicate_names = [name for name, count in Counter(names).items() if count > 1]

    missing = defaultdict(list)

    required = ["name", "type", "rarity", "effect"]

    for index, card in enumerate(cards, start=1):
        for field in required:
            if not card.get(field):
                missing[field].append(index)

    report = []
    report.append("# Ambitionz Base Set 250 Audit")
    report.append("")
    report.append(f"Total cards: {total}")
    report.append(f"Target cards: {BASE_SET_SIZE_TARGET}")
    report.append(f"Base set status: {'OK' if total == BASE_SET_SIZE_TARGET else 'CHECK'}")
    report.append("")

    report.append("## Type Distribution")
    for key, value in sorted(types.items()):
        report.append(f"- {key}: {value}")

    report.append("")
    report.append("## Rarity Distribution")
    for key, value in sorted(rarities.items()):
        report.append(f"- {key}: {value}")

    report.append("")
    report.append("## Element Distribution")
    for key, value in sorted(elements.items()):
        report.append(f"- {key}: {value}")

    report.append("")
    report.append("## Sigil Distribution")
    for key, value in sorted(sigils.items()):
        report.append(f"- {key}: {value}")

    report.append("")
    report.append("## Role Distribution")
    for key, value in sorted(roles.items()):
        report.append(f"- {key}: {value}")

    report.append("")
    report.append("## Duplicate Names")
    if duplicate_names:
        for name in duplicate_names:
            report.append(f"- {name}")
    else:
        report.append("- None")

    report.append("")
    report.append("## Missing Fields")
    if missing:
        for field, rows in missing.items():
            report.append(f"- {field}: {rows[:30]}{'...' if len(rows) > 30 else ''}")
    else:
        report.append("- None")

    report.append("")
    report.append("## Recommended Future Rarity Model")
    report.append("- Common: foundation, simple cards, starter friendly.")
    report.append("- Uncommon: synergy cards and role-defining tools.")
    report.append("- Rare: build-around cards and strong identity pieces.")
    report.append("- Ultra Rare: high excitement, low count, not mandatory.")
    report.append("- Unique: limited identity/cosmetic or special seasonal cards.")

    Path("reports").mkdir(exist_ok=True)
    out = Path("reports/base_set_250_audit.md")
    out.write_text("\n".join(report))

    print("\n".join(report))
    print("")
    print(f"REPORT_WRITTEN={out}")


if __name__ == "__main__":
    main()

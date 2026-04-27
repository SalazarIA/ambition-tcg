from collections import Counter
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game.cards import CARD_CATALOG, get_card_by_id
from game.deck import get_fixed_starter_deck_ids


def safe_int(value, default=0):
    try:
        return int(value or default)
    except Exception:
        return default


def card_score(card):
    card_type = card.get("type")

    if card_type != "Monster":
        return 0

    power = safe_int(card.get("power"))
    cost = max(1, safe_int(card.get("cost"), 1))

    return round(power / cost, 2)


def summarize_monsters(cards):
    monsters = [card for card in cards if card.get("type") == "Monster"]

    if not monsters:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "avg": 0,
            "median": 0,
        }

    powers = [safe_int(card.get("power")) for card in monsters]

    return {
        "count": len(monsters),
        "min": min(powers),
        "max": max(powers),
        "avg": round(sum(powers) / len(powers), 1),
        "median": round(statistics.median(powers), 1),
    }


def format_counter(counter):
    if not counter:
        return "- None\n"

    lines = []

    for key, value in counter.most_common():
        lines.append(f"- {key}: {value}")

    return "\n".join(lines) + "\n"


def find_outliers(cards):
    outliers = []

    for card in cards:
        if card.get("type") != "Monster":
            continue

        score = card_score(card)
        cost = safe_int(card.get("cost"))
        power = safe_int(card.get("power"))
        reasons = []

        if cost <= 1 and power >= 1300:
            reasons.append("low-cost high-power")

        if cost <= 2 and power >= 1500:
            reasons.append("aggressive stat spike")

        if cost >= 5 and power <= 1600:
            reasons.append("expensive low-power")

        if score >= 700:
            reasons.append("high power per cost")

        if reasons:
            outliers.append(
                {
                    "id": card.get("id"),
                    "name": card.get("name"),
                    "type": card.get("type"),
                    "element": card.get("element"),
                    "sigil": card.get("sigil"),
                    "rarity": card.get("rarity"),
                    "cost": cost,
                    "power": power,
                    "score": score,
                    "reasons": reasons,
                }
            )

    return sorted(outliers, key=lambda item: item["score"], reverse=True)


def cards_from_ids(card_ids):
    cards = []

    for card_id in card_ids:
        card = get_card_by_id(card_id)

        if card:
            cards.append(card)

    return cards


def generate_report():
    cards = list(CARD_CATALOG)
    starter_deck_ids = get_fixed_starter_deck_ids()
    starter_cards = cards_from_ids(starter_deck_ids)

    missing_starter_ids = [
        card_id for card_id in starter_deck_ids if not get_card_by_id(card_id)
    ]

    type_dist = Counter(card.get("type", "Unknown") for card in cards)
    element_dist = Counter(card.get("element", "Unknown") for card in cards)
    sigil_dist = Counter(card.get("sigil", "Unknown") for card in cards)
    rarity_dist = Counter(card.get("rarity", "Unknown") for card in cards)

    deck_type_dist = Counter(card.get("type", "Unknown") for card in starter_cards)
    deck_element_dist = Counter(card.get("element", "Unknown") for card in starter_cards)
    deck_sigil_dist = Counter(card.get("sigil", "Unknown") for card in starter_cards)
    deck_rarity_dist = Counter(card.get("rarity", "Unknown") for card in starter_cards)

    outliers = find_outliers(cards)
    deck_outliers = find_outliers(starter_cards)

    report = []

    report.append("# Ambitionz V1.08 Balance Report\n")

    report.append("## Catalog Summary\n")
    report.append(f"- Total cards: {len(cards)}")
    report.append(f"- Monster summary: {summarize_monsters(cards)}\n")

    report.append("### Type Distribution\n")
    report.append(format_counter(type_dist))

    report.append("### Element Distribution\n")
    report.append(format_counter(element_dist))

    report.append("### Sigil Distribution\n")
    report.append(format_counter(sigil_dist))

    report.append("### Rarity Distribution\n")
    report.append(format_counter(rarity_dist))

    report.append("\n## Starter/Beta Deck Summary\n")
    report.append(f"- Starter deck IDs: {len(starter_deck_ids)}")
    report.append(f"- Starter deck cards found: {len(starter_cards)}")
    report.append(f"- Missing starter IDs: {missing_starter_ids}")
    report.append(f"- Monster summary: {summarize_monsters(starter_cards)}\n")

    report.append("### Starter Type Distribution\n")
    report.append(format_counter(deck_type_dist))

    report.append("### Starter Element Distribution\n")
    report.append(format_counter(deck_element_dist))

    report.append("### Starter Sigil Distribution\n")
    report.append(format_counter(deck_sigil_dist))

    report.append("### Starter Rarity Distribution\n")
    report.append(format_counter(deck_rarity_dist))

    report.append("\n## Catalog Outliers\n")

    if outliers:
        for item in outliers[:40]:
            report.append(
                f"- **{item['name']}** `{item['id']}` "
                f"score={item['score']} cost={item['cost']} power={item['power']} "
                f"sigil={item['sigil']} rarity={item['rarity']} "
                f"reasons={', '.join(item['reasons'])}"
            )
    else:
        report.append("- No major outliers detected.")

    report.append("\n## Starter Deck Outliers\n")

    if deck_outliers:
        for item in deck_outliers:
            report.append(
                f"- **{item['name']}** `{item['id']}` "
                f"score={item['score']} cost={item['cost']} power={item['power']} "
                f"reasons={', '.join(item['reasons'])}"
            )
    else:
        report.append("- No major starter deck outliers detected.")

    return "\n".join(report) + "\n"


def main():
    output_path = Path("reports/balance_report_v105.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = generate_report()
    output_path.write_text(report, encoding="utf-8")

    print(f"Balance report written to {output_path}")
    print(report)


if __name__ == "__main__":
    main()

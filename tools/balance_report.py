from collections import Counter, defaultdict
from pathlib import Path
import statistics
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))



VALID_ELEMENTS = ["Fire", "Water", "Earth", "Plant", "Global", "Neutral"]
VALID_SIGILS = ["Fury", "Resolve", "Insight", "Ruin", "Harmony", "Global", "None"]
VALID_RARITIES = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]


def safe_int(value, default=0):
    try:
        return int(value or default)
    except Exception:
        return default


def get_cards():
    from game.cards import CARD_CATALOG
    return list(CARD_CATALOG)


def get_beta_deck_cards():
    cards = get_cards()

    try:
        from game.deck import STARTER_DECK_IDS
        starter_ids = list(STARTER_DECK_IDS)
    except Exception:
        starter_ids = []

    by_id = {card.get("id"): card for card in cards}

    deck_cards = []
    missing_ids = []

    for card_id in starter_ids:
        card = by_id.get(card_id)

        if card:
            deck_cards.append(card)
        else:
            missing_ids.append(card_id)

    return deck_cards, starter_ids, missing_ids


def summarize_distribution(cards, field):
    return Counter(str(card.get(field, "Unknown")) for card in cards)


def summarize_monster_power(cards):
    monsters = [card for card in cards if card.get("type") == "Monster"]
    powers = [safe_int(card.get("power")) for card in monsters]

    if not powers:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "avg": 0,
            "median": 0,
        }

    return {
        "count": len(powers),
        "min": min(powers),
        "max": max(powers),
        "avg": round(sum(powers) / len(powers), 2),
        "median": round(statistics.median(powers), 2),
    }


def expected_power_for_cost(cost):
    # Baseline inicial para o beta.
    # Não é regra final; serve para detectar outliers.
    return 650 + (safe_int(cost) * 280)


def score_card_balance(card):
    card_type = card.get("type")
    cost = safe_int(card.get("cost"))
    power = safe_int(card.get("power"))
    sigil = str(card.get("sigil", "Global"))
    rarity = str(card.get("rarity", "Common"))

    score = 0
    reasons = []

    if cost < 0:
        score += 100
        reasons.append("negative cost")

    if cost > 8:
        score += 20
        reasons.append("high cost")

    if card_type == "Monster":
        expected = expected_power_for_cost(cost)
        diff = power - expected

        if diff > 700:
            score += 45
            reasons.append(f"power too high for cost (+{diff})")
        elif diff > 450:
            score += 25
            reasons.append(f"power above curve (+{diff})")
        elif diff < -700:
            score += 30
            reasons.append(f"power too low for cost ({diff})")

        if power <= 0:
            score += 100
            reasons.append("monster with no power")

    if sigil == "Fury" and card_type == "Monster":
        score += 5

    if sigil == "Ruin":
        score += 8

    if rarity in {"Epic", "Legendary"}:
        score -= 5

    return max(score, 0), reasons


def find_outliers(cards):
    outliers = []

    for card in cards:
        score, reasons = score_card_balance(card)

        if score >= 25:
            outliers.append({
                "id": card.get("id"),
                "name": card.get("name"),
                "type": card.get("type"),
                "element": card.get("element"),
                "cost": card.get("cost"),
                "power": card.get("power"),
                "sigil": card.get("sigil"),
                "rarity": card.get("rarity"),
                "score": score,
                "reasons": reasons,
            })

    return sorted(outliers, key=lambda item: item["score"], reverse=True)


def format_counter(counter):
    if not counter:
        return "- None\n"

    lines = []

    for key, value in counter.most_common():
        lines.append(f"- {key}: {value}")

    return "\n".join(lines) + "\n"


def generate_report():
    cards = get_cards()
    deck_cards, starter_ids, missing_ids = get_beta_deck_cards()

    all_type_dist = summarize_distribution(cards, "type")
    all_element_dist = summarize_distribution(cards, "element")
    all_sigil_dist = summarize_distribution(cards, "sigil")
    all_rarity_dist = summarize_distribution(cards, "rarity")
    all_power_summary = summarize_monster_power(cards)

    deck_type_dist = summarize_distribution(deck_cards, "type")
    deck_element_dist = summarize_distribution(deck_cards, "element")
    deck_sigil_dist = summarize_distribution(deck_cards, "sigil")
    deck_rarity_dist = summarize_distribution(deck_cards, "rarity")
    deck_power_summary = summarize_monster_power(deck_cards)

    outliers = find_outliers(cards)
    deck_outliers = find_outliers(deck_cards)

    report = []

    report.append("# Ambitionz V1.05 Balance Report\n")
    report.append("## Catalog Summary\n")
    report.append(f"- Total cards: {len(cards)}")
    report.append(f"- Monster summary: {all_power_summary}\n")

    report.append("### Type Distribution\n")
    report.append(format_counter(all_type_dist))

    report.append("### Element Distribution\n")
    report.append(format_counter(all_element_dist))

    report.append("### Sigil Distribution\n")
    report.append(format_counter(all_sigil_dist))

    report.append("### Rarity Distribution\n")
    report.append(format_counter(all_rarity_dist))

    report.append("\n## Starter/Beta Deck Summary\n")
    report.append(f"- Starter deck IDs: {len(starter_ids)}")
    report.append(f"- Starter deck cards found: {len(deck_cards)}")
    report.append(f"- Missing starter IDs: {missing_ids}")
    report.append(f"- Monster summary: {deck_power_summary}\n")

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

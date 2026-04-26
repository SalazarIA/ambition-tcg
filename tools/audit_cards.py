VALID_TYPES = {"Monster", "Spell", "Trap"}
VALID_ELEMENTS = {"Fire", "Water", "Earth", "Plant", "Global", "Neutral"}
VALID_RARITIES = {"Common", "Uncommon", "Rare", "Epic", "Legendary"}
VALID_SIGILS = {"Fury", "Resolve", "Insight", "Ruin", "Harmony", "Global", "None", None}


REQUIRED_FIELDS = [
    "id",
    "name",
    "type",
    "element",
    "rarity",
    "cost",
    "effect",
]


def audit_cards():
    errors = []

    try:
        from game.cards import CARD_CATALOG
    except Exception as error:
        return [f"Could not import CARD_CATALOG: {type(error).__name__}: {error}"]

    seen_ids = set()

    for card in CARD_CATALOG:
        card_id = card.get("id", "<missing-id>")

        if card_id in seen_ids:
            errors.append(f"Duplicate card id: {card_id}")

        seen_ids.add(card_id)

        for field in REQUIRED_FIELDS:
            if field not in card:
                errors.append(f"Card {card_id} missing field: {field}")

        card_type = card.get("type")
        element = card.get("element")
        rarity = card.get("rarity")
        sigil = card.get("sigil")

        if card_type not in VALID_TYPES:
            errors.append(f"Card {card_id} has invalid type: {card_type}")

        if element not in VALID_ELEMENTS:
            errors.append(f"Card {card_id} has invalid element: {element}")

        if rarity not in VALID_RARITIES:
            errors.append(f"Card {card_id} has invalid rarity: {rarity}")

        if sigil not in VALID_SIGILS:
            errors.append(f"Card {card_id} has invalid sigil: {sigil}")

        try:
            cost = int(card.get("cost", 0))

            if cost < 0 or cost > 10:
                errors.append(f"Card {card_id} has suspicious cost: {cost}")
        except Exception:
            errors.append(f"Card {card_id} cost is not numeric: {card.get('cost')}")

        if card_type == "Monster":
            if "power" not in card:
                errors.append(f"Monster {card_id} missing power")
            else:
                try:
                    power = int(card.get("power", 0))

                    if power <= 0 or power > 5000:
                        errors.append(f"Monster {card_id} has suspicious power: {power}")
                except Exception:
                    errors.append(f"Monster {card_id} power is not numeric: {card.get('power')}")

    print("CARDS TOTAL:", len(CARD_CATALOG))
    print("CARD IDS UNIQUE:", len(seen_ids))

    return errors

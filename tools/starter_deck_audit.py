from services.starter_deck_v1 import (
    build_balanced_starter_deck,
    validate_starter_deck,
    analyze_starter_deck,
)

deck = build_balanced_starter_deck()
errors, analysis = validate_starter_deck(deck)

print("# Starter Deck V1 Audit")
print("total", analysis["total"])
print("types", analysis["types"])
print("roles", analysis["roles"])
print("curve", analysis["curve"])
print("avg_cost", analysis["avg_cost"])

print("")
print("Cards:")
for card in deck:
    print("-", card.get("name"), "|", card.get("type"), "|", card.get("role"), "| cost", card.get("cost"), "| power", card.get("power") or card.get("value"))

if errors:
    print("")
    print("ERRORS:")
    for error in errors:
        print("-", error)
    raise SystemExit("STARTER_DECK_AUDIT_FAILED")

print("STARTER_DECK_AUDIT_PASSED")

from app import app
from models import User
from services.economy.deck_inventory import (
    owned_card_ids_for_user,
    validate_deck_against_inventory,
    build_auto_deck_from_inventory,
)

with app.app_context():
    user = User.query.first()

    if not user:
        print("SKIP - no local user.")
        raise SystemExit(0)

    owned_ids = owned_card_ids_for_user(user)
    auto_deck = build_auto_deck_from_inventory(user)
    errors = validate_deck_against_inventory(user, auto_deck)

    print("# Deck Inventory Audit")
    print("user", user.id, user.username)
    print("owned_ids", len(owned_ids))
    print("auto_deck", len(auto_deck))
    print("ownership_errors", len(errors))

    if owned_ids and not auto_deck:
        raise SystemExit("FAILED - owned cards exist but auto deck is empty")

    if auto_deck and errors:
        print("errors", errors[:5])
        raise SystemExit("FAILED - auto deck violates ownership")

    print("DECK_INVENTORY_AUDIT_PASSED")

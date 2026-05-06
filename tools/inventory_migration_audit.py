from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app, db
from models import User
from services.economy.inventory_migration import (
    legacy_collection_ids,
    migrate_legacy_collection_to_inventory,
    ensure_user_has_playable_inventory,
)
from services.economy.deck_inventory import owned_card_ids_for_user, build_auto_deck_from_inventory

with app.app_context():
    user = User.query.first()

    if not user:
        print("SKIP - no local user.")
        raise SystemExit(0)

    before_owned = len(owned_card_ids_for_user(user, include_legacy_fallback=False))
    legacy_count = len(legacy_collection_ids(user))

    result = migrate_legacy_collection_to_inventory(user)
    db.session.commit()

    after_migration_owned = len(owned_card_ids_for_user(user, include_legacy_fallback=False))

    recovery = ensure_user_has_playable_inventory(user)
    db.session.commit()

    after_recovery_owned = len(owned_card_ids_for_user(user, include_legacy_fallback=False))
    auto_deck = build_auto_deck_from_inventory(user)

    print("# Inventory Migration Audit")
    print("user", user.id, user.username)
    print("legacy_count", legacy_count)
    print("before_owned", before_owned)
    print("after_migration_owned", after_migration_owned)
    print("after_recovery_owned", after_recovery_owned)
    print("migration", result)
    print("recovery", recovery)
    print("auto_deck_size", len(auto_deck))

    if after_recovery_owned <= 0:
        raise SystemExit("FAILED - user still has no owned inventory after recovery")

    if len(auto_deck) <= 0:
        raise SystemExit("FAILED - auto deck empty after recovery")

    print("INVENTORY_MIGRATION_AUDIT_PASSED")

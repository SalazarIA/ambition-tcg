
from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _ledger_count(model, **filters):
    try:
        query = model.query
        for key, value in filters.items():
            query = query.filter(getattr(model, key) == value)
        return query.count()
    except Exception:
        return None


def run_economy_flow():
    logs = []
    failures = []

    try:
        from app import app, db
        from models import User, PremiumCurrencyLedger, InventoryOwnershipLedger
        from services.economy.inventory_ownership import grant_card, get_quantity
        from services.economy.inventory_cards import user_inventory_counts
        from game.cards import CARD_CATALOG

        # Optional imports: project names may differ. Keep defensive.
        try:
            from services.economy.premium_currency import add_premium_currency, get_premium_balance
        except Exception:
            add_premium_currency = None
            get_premium_balance = None

        with app.app_context():
            user = User.query.first()

            if not user:
                failures.append("No local user found.")
                return {
                    "name": "economy_booster_flow",
                    "status": "FAIL",
                    "error": "; ".join(failures),
                    "logs": logs,
                }

            logs.append(f"user: id={user.id} username={user.username}")
            logs.append(f"coins={getattr(user, 'coins', None)} gems={getattr(user, 'gems', None)} xp={getattr(user, 'xp', None)} level={getattr(user, 'level', None)}")

            inventory_before = user_inventory_counts(user)
            logs.append(f"inventory_unique_before={len(inventory_before)}")

            if len(inventory_before) <= 0:
                failures.append("Inventory is empty before economy QA.")

            # Idempotent inventory grant test.
            card = CARD_CATALOG[0] if CARD_CATALOG else None
            if not card:
                failures.append("CARD_CATALOG is empty.")
            else:
                card_id = str(card.get("id") or card.get("card_id") or card.get("name"))
                key = f"qa-economy-grant-{user.id}-{card_id}"

                qty_before = get_quantity(user.id, "card", card_id)
                ok1, payload1 = grant_card(user, card_id, 1, source="qa_economy", idempotency_key=key)

                if ok1 and payload1.get("posted"):
                    db.session.commit()
                else:
                    db.session.rollback()

                qty_after_first = get_quantity(user.id, "card", card_id)

                ok2, payload2 = grant_card(user, card_id, 1, source="qa_economy", idempotency_key=key)

                if ok2 and payload2.get("posted"):
                    db.session.commit()
                else:
                    db.session.rollback()

                qty_after_second = get_quantity(user.id, "card", card_id)

                logs.append(f"grant_card_card_id={card_id}")
                logs.append(f"grant_qty_before={qty_before}")
                logs.append(f"grant_qty_after_first={qty_after_first}")
                logs.append(f"grant_qty_after_second={qty_after_second}")
                logs.append(f"grant_payload1={payload1}")
                logs.append(f"grant_payload2={payload2}")

                if not payload1.get("duplicate") and qty_after_first != qty_before + 1:
                    failures.append("Inventory grant did not increase quantity on first post.")

                if qty_after_second != qty_after_first:
                    failures.append("Inventory grant idempotency failed: second post changed quantity.")

                if not payload2.get("duplicate"):
                    failures.append("Second grant did not report duplicate=True.")

            inv_ledger_count = _ledger_count(InventoryOwnershipLedger, user_id=user.id)
            premium_ledger_count = _ledger_count(PremiumCurrencyLedger, user_id=user.id)

            logs.append(f"inventory_ownership_ledger_count={inv_ledger_count}")
            logs.append(f"premium_currency_ledger_count={premium_ledger_count}")

            if inv_ledger_count is None:
                failures.append("InventoryOwnershipLedger count failed.")

            if premium_ledger_count is None:
                failures.append("PremiumCurrencyLedger count failed.")

            # Premium currency service sanity if available.
            if get_premium_balance:
                try:
                    balance = get_premium_balance(user)
                    logs.append(f"premium_balance_service={balance}")
                except Exception as exc:
                    failures.append(f"get_premium_balance failed: {type(exc).__name__}: {exc}")
            else:
                logs.append("premium_currency_service_balance=SKIP import unavailable")

            # HTTP route checks.
            client = app.test_client()

            route_paths = [
                "/shop",
                "/booster-history",
                "/economy/premium-ledger",
                "/inventory",
                "/collection",
            ]

            logs.append("")
            logs.append("route_audit:")

            for path in route_paths:
                response = client.get(path)
                logs.append(f"{path}: status={response.status_code} content_type={response.content_type} location={response.headers.get('Location')}")

                if response.status_code >= 500:
                    failures.append(f"{path} returned {response.status_code}")

                if response.status_code not in (200, 302, 401, 403):
                    failures.append(f"{path} unexpected status {response.status_code}")

            # Static catalog sanity.
            rarity_counts = {}
            type_counts = {}

            for c in CARD_CATALOG:
                rarity_counts[c.get("rarity") or "Unknown"] = rarity_counts.get(c.get("rarity") or "Unknown", 0) + 1
                type_counts[c.get("type") or "Unknown"] = type_counts.get(c.get("type") or "Unknown", 0) + 1

            logs.append(f"catalog_size={len(CARD_CATALOG)}")
            logs.append(f"catalog_type_counts={type_counts}")
            logs.append(f"catalog_rarity_counts={rarity_counts}")

            if len(CARD_CATALOG) <= 0:
                failures.append("CARD_CATALOG empty.")

            if type_counts.get("Monster", 0) <= 0:
                failures.append("CARD_CATALOG has no Monsters.")

            if type_counts.get("Spell", 0) <= 0:
                failures.append("CARD_CATALOG has no Spells.")

            if type_counts.get("Trap", 0) <= 0:
                failures.append("CARD_CATALOG has no Traps.")

        status = "FAIL" if failures else "PASS"

        return {
            "name": "economy_booster_flow",
            "status": status,
            "error": "; ".join(failures) if failures else None,
            "logs": logs,
        }

    except Exception as exc:
        return {
            "name": "economy_booster_flow",
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "logs": logs,
        }

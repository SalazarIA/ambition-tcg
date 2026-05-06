import json
import hashlib
from datetime import datetime, timezone

from models import db, InventoryOwnership, InventoryOwnershipLedger


def make_inventory_transaction_key(user_id, item_type, item_id, source, idempotency_key):
    raw = f"{user_id}:{item_type}:{item_id}:{source}:{idempotency_key}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return f"inventory_{digest}"


def get_inventory_row(user_id, item_type, item_id):
    return InventoryOwnership.query.filter_by(
        user_id=user_id,
        item_type=item_type,
        item_id=str(item_id),
    ).first()


def get_quantity(user_id, item_type, item_id):
    row = get_inventory_row(user_id, item_type, item_id)
    return int(row.quantity or 0) if row else 0


def post_inventory_delta(user, item_id, delta, item_type="card", source="system", idempotency_key=None, metadata=None):
    if not user:
        return False, {"ok": False, "message": "Invalid user.", "posted": False}

    try:
        delta = int(delta)
    except Exception:
        return False, {"ok": False, "message": "Delta must be integer.", "posted": False}

    if delta == 0:
        return False, {"ok": False, "message": "Delta cannot be zero.", "posted": False}

    if not idempotency_key:
        idempotency_key = f"{source}:{item_type}:{item_id}:{delta}:{datetime.now(timezone.utc).isoformat()}"

    transaction_key = make_inventory_transaction_key(user.id, item_type, item_id, source, idempotency_key)
    existing = InventoryOwnershipLedger.query.filter_by(transaction_key=transaction_key).first()

    if existing:
        return True, {
            "ok": True,
            "posted": False,
            "duplicate": True,
            "transaction_key": existing.transaction_key,
            "balance_after": existing.balance_after,
        }

    row = get_inventory_row(user.id, item_type, item_id)

    if not row:
        row = InventoryOwnership(
            user_id=user.id,
            item_type=item_type,
            item_id=str(item_id),
            quantity=0,
            source=source,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
        db.session.add(row)

    before = int(row.quantity or 0)
    after = before + delta

    if after < 0:
        return False, {"ok": False, "message": "Insufficient item quantity.", "posted": False}

    row.quantity = after
    row.source = source
    row.metadata_json = json.dumps(metadata or {}, ensure_ascii=False)

    entry = InventoryOwnershipLedger(
        transaction_key=transaction_key,
        user_id=user.id,
        item_type=item_type,
        item_id=str(item_id),
        delta=delta,
        balance_after=after,
        source=source,
        status="posted",
        idempotency_key=idempotency_key,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    db.session.add(entry)

    return True, {
        "ok": True,
        "posted": True,
        "duplicate": False,
        "transaction_key": transaction_key,
        "balance_before": before,
        "balance_after": after,
        "delta": delta,
        "item_type": item_type,
        "item_id": str(item_id),
    }


def grant_card(user, card_id, quantity=1, source="system", idempotency_key=None, metadata=None):
    return post_inventory_delta(
        user=user,
        item_id=card_id,
        delta=quantity,
        item_type="card",
        source=source,
        idempotency_key=idempotency_key,
        metadata=metadata,
    )


def remove_card(user, card_id, quantity=1, source="system", idempotency_key=None, metadata=None):
    return post_inventory_delta(
        user=user,
        item_id=card_id,
        delta=-abs(int(quantity)),
        item_type="card",
        source=source,
        idempotency_key=idempotency_key,
        metadata=metadata,
    )

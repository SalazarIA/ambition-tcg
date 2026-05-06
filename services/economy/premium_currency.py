import json
import hashlib
from datetime import datetime, timezone

from models import db, PremiumCurrencyLedger

VALID_CURRENCIES = {"gems"}
VALID_DIRECTIONS = {"credit", "debit"}
VALID_SOURCES = {
    "system",
    "founder_grant",
    "admin_adjustment",
    "test_grant",
    "purchase_pending",
    "purchase_verified",
    "refund",
    "chargeback",
    "reward",
}


def make_transaction_key(user_id, source, idempotency_key, currency="gems"):
    raw = f"{user_id}:{source}:{idempotency_key}:{currency}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return f"premium_{digest}"


def existing_transaction(transaction_key):
    if not transaction_key:
        return None
    return PremiumCurrencyLedger.query.filter_by(transaction_key=transaction_key).first()


def current_balance(user, currency="gems"):
    if currency != "gems":
        return 0
    return int(getattr(user, "gems", 0) or 0)


def set_balance(user, currency, value):
    if currency != "gems":
        raise ValueError(f"Unsupported currency: {currency}")
    user.gems = max(0, int(value))


def validate_currency_operation(user, amount, currency, direction, source):
    if not user:
        return False, "Invalid user."

    if currency not in VALID_CURRENCIES:
        return False, f"Unsupported currency: {currency}"

    if direction not in VALID_DIRECTIONS:
        return False, f"Unsupported direction: {direction}"

    if source not in VALID_SOURCES:
        return False, f"Unsupported source: {source}"

    try:
        amount = int(amount)
    except Exception:
        return False, "Amount must be an integer."

    if amount <= 0:
        return False, "Amount must be positive."

    if direction == "debit" and current_balance(user, currency) < amount:
        return False, "Insufficient balance."

    return True, "OK"


def post_premium_currency_transaction(
    user,
    amount,
    currency="gems",
    direction="credit",
    source="system",
    idempotency_key=None,
    provider=None,
    provider_receipt_id=None,
    metadata=None,
):
    ok, message = validate_currency_operation(user, amount, currency, direction, source)

    if not ok:
        return False, {"ok": False, "message": message, "posted": False}

    if not idempotency_key:
        idempotency_key = f"{source}:{currency}:{direction}:{amount}:{datetime.now(timezone.utc).isoformat()}"

    transaction_key = make_transaction_key(user.id, source, idempotency_key, currency=currency)
    existing = existing_transaction(transaction_key)

    if existing:
        return True, {
            "ok": True,
            "message": "Transaction already posted.",
            "posted": False,
            "duplicate": True,
            "transaction_key": existing.transaction_key,
            "balance_after": existing.balance_after,
            "amount": existing.amount,
            "currency": existing.currency,
        }

    before = current_balance(user, currency)
    after = before + int(amount) if direction == "credit" else before - int(amount)
    set_balance(user, currency, after)

    entry = PremiumCurrencyLedger(
        transaction_key=transaction_key,
        user_id=user.id,
        currency=currency,
        amount=int(amount),
        balance_after=after,
        direction=direction,
        source=source,
        status="posted",
        provider=provider,
        provider_receipt_id=provider_receipt_id,
        idempotency_key=idempotency_key,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )

    db.session.add(entry)

    return True, {
        "ok": True,
        "message": "Transaction posted.",
        "posted": True,
        "duplicate": False,
        "transaction_key": transaction_key,
        "balance_before": before,
        "balance_after": after,
        "amount": int(amount),
        "currency": currency,
        "direction": direction,
        "source": source,
    }


def credit_gems(user, amount, source="system", idempotency_key=None, metadata=None):
    return post_premium_currency_transaction(
        user=user,
        amount=amount,
        currency="gems",
        direction="credit",
        source=source,
        idempotency_key=idempotency_key,
        metadata=metadata,
    )


def debit_gems(user, amount, source="system", idempotency_key=None, metadata=None):
    return post_premium_currency_transaction(
        user=user,
        amount=amount,
        currency="gems",
        direction="debit",
        source=source,
        idempotency_key=idempotency_key,
        metadata=metadata,
    )

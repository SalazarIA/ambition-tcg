import json

from models import EconomyLedger, UserCosmetic, db


PREMIUM_CURRENCY_KEY = "gems"
SOFT_CURRENCY_KEY = "coins"


COSMETIC_CATALOG = [
    {
        "key": "founder_title",
        "type": "title",
        "name": "Founder",
        "description": "Early Ambitionz identity title.",
        "price_gems": 0,
        "status": "beta",
    },
    {
        "key": "obsidian_card_back",
        "type": "card_back",
        "name": "Obsidian Back",
        "description": "Dark premium card back for future cosmetic loadouts.",
        "price_gems": 250,
        "status": "preview",
    },
    {
        "key": "golden_frame",
        "type": "frame",
        "name": "Golden Frame",
        "description": "Premium card frame concept. Cosmetic only.",
        "price_gems": 400,
        "status": "preview",
    },
    {
        "key": "forest_arena_skin",
        "type": "arena_skin",
        "name": "Forest Arena",
        "description": "Arena board cosmetic concept. Cosmetic only.",
        "price_gems": 600,
        "status": "preview",
    },
]


def ensure_user_wallet_fields(user):
    if not user:
        return

    if not hasattr(user, "gems"):
        return

    if user.gems is None:
        user.gems = 0


def get_balance(user, currency):
    if not user:
        return 0

    if currency == SOFT_CURRENCY_KEY:
        return int(user.coins or 0)

    if currency == PREMIUM_CURRENCY_KEY and hasattr(user, "gems"):
        return int(user.gems or 0)

    return 0


def set_balance(user, currency, value):
    if not user:
        return 0

    value = int(value)

    if currency == SOFT_CURRENCY_KEY:
        user.coins = value
        return value

    if currency == PREMIUM_CURRENCY_KEY and hasattr(user, "gems"):
        user.gems = value
        return value

    return 0


def record_ledger(user, currency, amount, source, reason=None, reference_type=None, reference_id=None, metadata=None):
    balance_after = get_balance(user, currency)

    entry = EconomyLedger(
        user_id=user.id if user else None,
        currency=currency,
        amount=int(amount),
        balance_after=balance_after,
        source=str(source)[:80],
        reason=str(reason or "")[:180],
        reference_type=str(reference_type or "")[:80] or None,
        reference_id=str(reference_id or "")[:120] or None,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False)[:4000],
    )

    db.session.add(entry)
    return entry


def add_currency(user, currency, amount, source, reason=None, reference_type=None, reference_id=None, metadata=None, commit=True):
    if not user:
        return False, "Invalid user."

    amount = int(amount)

    if amount <= 0:
        return False, "Amount must be positive."

    current = get_balance(user, currency)
    set_balance(user, currency, current + amount)

    record_ledger(
        user=user,
        currency=currency,
        amount=amount,
        source=source,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
        metadata=metadata,
    )

    if commit:
        db.session.commit()

    return True, f"+{amount} {currency}"


def spend_currency(user, currency, amount, source, reason=None, reference_type=None, reference_id=None, metadata=None, commit=True):
    if not user:
        return False, "Invalid user."

    amount = int(amount)

    if amount <= 0:
        return False, "Amount must be positive."

    current = get_balance(user, currency)

    if current < amount:
        return False, f"Not enough {currency}."

    set_balance(user, currency, current - amount)

    record_ledger(
        user=user,
        currency=currency,
        amount=-amount,
        source=source,
        reason=reason,
        reference_type=reference_type,
        reference_id=reference_id,
        metadata=metadata,
    )

    if commit:
        db.session.commit()

    return True, f"-{amount} {currency}"


def user_owns_cosmetic(user, cosmetic_key):
    if not user:
        return False

    return UserCosmetic.query.filter_by(user_id=user.id, cosmetic_key=cosmetic_key).first() is not None


def grant_cosmetic(user, cosmetic_key, source="grant", commit=True):
    if not user:
        return False, "Invalid user."

    cosmetic = next((item for item in COSMETIC_CATALOG if item["key"] == cosmetic_key), None)

    if not cosmetic:
        return False, "Cosmetic not found."

    if user_owns_cosmetic(user, cosmetic_key):
        return False, "Already owned."

    owned = UserCosmetic(
        user_id=user.id,
        cosmetic_key=cosmetic["key"],
        cosmetic_type=cosmetic["type"],
        name=cosmetic["name"],
        acquired_source=source,
    )

    db.session.add(owned)

    if commit:
        db.session.commit()

    return True, "Cosmetic granted."


def cosmetic_catalog_for_user(user):
    owned_keys = set()

    if user:
        owned_keys = {
            row.cosmetic_key
            for row in UserCosmetic.query.filter_by(user_id=user.id).all()
        }

    result = []

    for item in COSMETIC_CATALOG:
        row = dict(item)
        row["owned"] = row["key"] in owned_keys
        result.append(row)

    return result

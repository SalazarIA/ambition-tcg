import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, JSON, String, case, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from services.rebirth_cards import (
    CARD_CATALOG,
    PLAYER_DECK,
    STARTER_DECK_SIZE,
    get_card,
    is_monster,
    is_spell,
    is_trap,
    validate_deck_distribution,
)


DEFAULT_LOADOUT = list(PLAYER_DECK)

HASH_ITERATIONS = 180000
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,24}$")


class Base(DeclarativeBase):
    pass


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class UserCollection(Base):
    __tablename__ = "user_collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    card_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evolved_tier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class GameSession(Base):
    __tablename__ = "game_sessions"

    match_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    player_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    bot_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ACTIVE")
    current_turn: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    turn_phase: Mapped[str] = mapped_column(String(32), nullable=False, default="MAIN_PHASE")
    live_match_state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    state_hash: Mapped[str] = mapped_column(String(96), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class EconomyTransaction(Base):
    __tablename__ = "economy_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(24), nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class WalletLedger(Base):
    __tablename__ = "wallet_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    entry_type: Mapped[str] = mapped_column(String(8), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class MarketOffer(Base):
    __tablename__ = "market_offers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    seller_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    card_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


ASYNC_DATABASE_ENV_NAMES = ("REBIRTH_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL")
_async_engine: Optional[AsyncEngine] = None
_async_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None
_async_schema_initialized = False

ACHIEVEMENTS = [
    {
        "key": "founder",
        "name": "Rebirth Founder",
        "copy": "Create a Rebirth account.",
    },
    {
        "key": "first_clash",
        "name": "First Clash",
        "copy": "Resolve one persisted Rebirth clash.",
    },
    {
        "key": "first_win",
        "name": "First Victory",
        "copy": "Win a persisted Rebirth match.",
    },
    {
        "key": "first_booster",
        "name": "Booster Opened",
        "copy": "Open one no-payment Rebirth booster.",
    },
    {
        "key": "daily_claimed",
        "name": "Daily Spark",
        "copy": "Claim the first-clash daily reward.",
    },
    {
        "key": "tutorial_complete",
        "name": "Awakened",
        "copy": "Complete the Rebirth onboarding path.",
    },
]


class RebirthPersistenceError(ValueError):
    def __init__(self, message, code="persistence_error", status=400):
        super().__init__(message)
        self.code = code
        self.status = status


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def utc_datetime():
    return datetime.now(timezone.utc)


def _normalize_async_database_url(database_url):
    database_url = str(database_url or "").strip()
    if not database_url:
        return ""
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql://") and "+asyncpg" not in database_url.split("://", 1)[0]:
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


def async_database_url():
    for env_name in ASYNC_DATABASE_ENV_NAMES:
        value = os.environ.get(env_name)
        if value:
            return _normalize_async_database_url(value)
    return ""


def configure_async_database(database_url=None, *, engine=None, session_factory=None):
    global _async_engine, _async_sessionmaker, _async_schema_initialized
    _async_schema_initialized = False
    if session_factory is not None:
        _async_sessionmaker = session_factory
        _async_engine = engine
        return _async_sessionmaker
    if engine is not None:
        _async_engine = engine
        _async_sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
        return _async_sessionmaker
    database_url = _normalize_async_database_url(database_url) or async_database_url()
    if not database_url:
        _async_engine = None
        _async_sessionmaker = None
        return None
    _async_engine = create_async_engine(database_url, pool_pre_ping=True)
    _async_sessionmaker = async_sessionmaker(_async_engine, expire_on_commit=False)
    return _async_sessionmaker


def async_session_factory():
    global _async_sessionmaker
    if _async_sessionmaker is None:
        configure_async_database()
    if _async_sessionmaker is None:
        raise RebirthPersistenceError(
            "REBIRTH_DATABASE_URL is required for PostgreSQL async persistence.",
            "database_not_configured",
            status=503,
        )
    return _async_sessionmaker


async def ensure_async_schema():
    global _async_engine
    if _async_engine is None:
        configure_async_database()
    if _async_engine is None:
        raise RebirthPersistenceError(
            "REBIRTH_DATABASE_URL is required for PostgreSQL async schema creation.",
            "database_not_configured",
            status=503,
        )
    async with _async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def ensure_async_schema_once():
    global _async_schema_initialized
    if _async_schema_initialized:
        return
    await ensure_async_schema()
    _async_schema_initialized = True


def _stable_state_hash(state_dict):
    return hashlib.sha256(json.dumps(state_dict or {}, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:32]


async def _ensure_async_user_account(session, user_id, *, username=None, password_hash="external-account"):
    user_id = int(user_id or 0)
    if user_id <= 0:
        raise RebirthPersistenceError("A valid user_id is required.", "invalid_user", status=400)
    account = await session.get(UserAccount, user_id)
    if account:
        await _ensure_async_starter_wallet(session, account)
        return account
    account = UserAccount(
        id=user_id,
        username=normalize_username(username) or f"rebirth_user_{user_id}",
        password_hash=str(password_hash or "external-account"),
        xp=0,
        level=1,
        created_at=utc_datetime(),
    )
    session.add(account)
    await session.flush()
    await _seed_async_user_collection(session, account, f"{account.id}:{account.username}")
    _add_async_wallet_entry(
        session,
        int(account.id),
        "GOLD",
        "CREDIT",
        1000,
        "MATCH_REWARD",
        f"starter:{account.id}",
    )
    return account


async def _ensure_async_starter_wallet(session, account):
    result = await session.execute(
        select(func.count(WalletLedger.id)).where(
            WalletLedger.user_id == int(account.id),
            WalletLedger.currency == "GOLD",
        )
    )
    if int(result.scalar_one() or 0) > 0:
        return
    _add_async_wallet_entry(
        session,
        int(account.id),
        "GOLD",
        "CREDIT",
        1000,
        "MATCH_REWARD",
        f"starter:{account.id}",
    )


async def _seed_async_user_collection(session, account, seed_source):
    deck = deterministic_starter_deck(seed_source)
    for card_id in deck:
        card = get_card(card_id)
        session.add(
            UserCollection(
                user_id=int(account.id),
                card_id=card_id,
                quantity=1,
                locked_quantity=0,
                evolved_tier=int(card.get("tier", 1) or 1),
            )
        )


async def save_match_state(match_id: str, state_dict: dict) -> bool:
    if not match_id:
        raise RebirthPersistenceError("match_id is required.", "missing_match", status=400)
    if not isinstance(state_dict, dict):
        raise RebirthPersistenceError("state_dict must be a dictionary.", "malformed_request", status=400)

    await ensure_async_schema_once()
    session_maker = async_session_factory()
    now = utc_datetime()
    player_id = state_dict.get("owner_user_id") or state_dict.get("player_id") or state_dict.get("user_id")
    bot_id = state_dict.get("bot_id")
    status = "FINISHED" if state_dict.get("is_finished") or state_dict.get("winner") else "ACTIVE"
    turn_phase = str(state_dict.get("turn_phase") or state_dict.get("phase") or "MAIN_PHASE")
    state_hash = str(state_dict.get("state_hash") or _stable_state_hash(state_dict))

    try:
        async with session_maker() as session:
            async with session.begin():
                existing = await session.get(GameSession, match_id)
                if existing:
                    existing.player_id = int(player_id) if player_id else existing.player_id
                    existing.bot_id = int(bot_id) if bot_id else existing.bot_id
                    existing.status = status
                    existing.current_turn = int(state_dict.get("turn", existing.current_turn) or existing.current_turn)
                    existing.turn_phase = turn_phase
                    existing.live_match_state = state_dict
                    existing.version = int(existing.version or 0) + 1
                    existing.state_hash = state_hash
                    existing.updated_at = now
                else:
                    session.add(
                        GameSession(
                            match_id=str(match_id),
                            player_id=int(player_id) if player_id else None,
                            bot_id=int(bot_id) if bot_id else None,
                            status=status,
                            current_turn=int(state_dict.get("turn", 1) or 1),
                            turn_phase=turn_phase,
                            live_match_state=state_dict,
                            version=int(state_dict.get("version", 1) or 1),
                            state_hash=state_hash,
                            updated_at=now,
                        )
                    )
        return True
    except SQLAlchemyError as exc:
        raise RebirthPersistenceError("Failed to save live match state.", "database_write_failed", status=500) from exc


async def load_match_state(match_id: str) -> dict:
    if not match_id:
        raise RebirthPersistenceError("match_id is required.", "missing_match", status=400)

    await ensure_async_schema_once()
    session_maker = async_session_factory()
    try:
        async with session_maker() as session:
            game_session = await session.get(GameSession, match_id)
            return dict(game_session.live_match_state or {}) if game_session else {}
    except SQLAlchemyError as exc:
        raise RebirthPersistenceError("Failed to load live match state.", "database_read_failed", status=500) from exc


async def log_transaction(user_id: int, t_type: str, amount: int, currency: str) -> None:
    await ensure_async_schema_once()
    session_maker = async_session_factory()
    try:
        async with session_maker() as session:
            async with session.begin():
                await _ensure_async_user_account(session, user_id)
                session.add(
                    EconomyTransaction(
                        user_id=int(user_id),
                        transaction_type=str(t_type or "").strip() or "UNKNOWN",
                        amount=int(amount or 0),
                        currency=str(currency or "").strip() or "coins",
                        reference_id=None,
                        timestamp=utc_datetime(),
                    )
                )
    except SQLAlchemyError as exc:
        raise RebirthPersistenceError("Failed to log economy transaction.", "database_write_failed", status=500) from exc


async def credit_verified_purchase(
    user_id: int,
    *,
    amount: int,
    currency: str,
    reference_id: str,
    username: Optional[str] = None,
    transaction_type: str = "IN_APP_PURCHASE",
) -> dict:
    await ensure_async_schema_once()
    session_maker = async_session_factory()
    try:
        async with session_maker() as session:
            async with session.begin():
                await _set_serializable_if_postgres(session)
                await _ensure_async_user_account(session, user_id, username=username)
                account = (
                    await session.execute(
                        select(UserAccount).where(UserAccount.id == int(user_id)).with_for_update()
                    )
                ).scalar_one()
                amount = int(amount or 0)
                currency = normalize_wallet_currency(currency)
                if amount <= 0:
                    raise RebirthPersistenceError("Purchase amount must be positive.", "invalid_purchase", status=400)
                _add_async_wallet_entry(
                    session,
                    int(user_id),
                    currency,
                    "CREDIT",
                    amount=amount,
                    source="SHOP_PURCHASE",
                    reference_id=str(reference_id or ""),
                )
                session.add(
                    EconomyTransaction(
                        user_id=int(user_id),
                        transaction_type=str(transaction_type or "IN_APP_PURCHASE"),
                        amount=amount,
                        currency=currency,
                        reference_id=str(reference_id or ""),
                        timestamp=utc_datetime(),
                    )
                )
                await session.flush()
                wallet = {
                    "GOLD": await get_user_balance(int(user_id), "GOLD", session=session),
                    "COINZ": await get_user_balance(int(user_id), "COINZ", session=session),
                    "ledger_source": "wallet_ledger",
                }
                return {
                    "user_id": account.id,
                    "balance_gold": wallet["GOLD"],
                    "balance_coinz": wallet["COINZ"],
                    "wallet": wallet,
                    "xp": int(account.xp or 0),
                    "level": int(account.level or 1),
                    "amount": amount,
                    "currency": currency,
                    "reference_id": str(reference_id or ""),
                }
    except RebirthPersistenceError:
        raise
    except SQLAlchemyError as exc:
        raise RebirthPersistenceError("Failed to credit verified purchase.", "database_write_failed", status=500) from exc


WALLET_CURRENCY_ALIASES = {
    "GOLD": "GOLD",
    "COIN": "COINZ",
    "COINS": "COINZ",
    "COINZ": "COINZ",
    "PREMIUM": "COINZ",
    "GEM": "COINZ",
    "GEMS": "COINZ",
}


def normalize_wallet_currency(currency):
    normalized = str(currency or "GOLD").strip().upper()
    normalized = WALLET_CURRENCY_ALIASES.get(normalized, normalized)
    if normalized not in {"GOLD", "COINZ"}:
        raise RebirthPersistenceError("currency must be GOLD or COINZ.", "invalid_wallet_currency", status=400)
    return normalized


def normalize_market_currency(currency_type):
    try:
        return normalize_wallet_currency(currency_type or "GOLD")
    except RebirthPersistenceError as exc:
        raise RebirthPersistenceError("currency_type must be GOLD or COINZ.", "invalid_market_currency", status=400) from exc


def _normalize_market_price(price):
    try:
        price = int(price)
    except (TypeError, ValueError) as exc:
        raise RebirthPersistenceError("Market price must be a positive integer.", "invalid_market_price", status=400) from exc
    if price <= 0:
        raise RebirthPersistenceError("Market price must be a positive integer.", "invalid_market_price", status=400)
    return price


def _market_fee(price):
    return max(1, int(price * 5 // 100)) if price >= 20 else 1


def _normalize_wallet_entry(entry_type, amount):
    entry_type = str(entry_type or "").strip().upper()
    if entry_type not in {"CREDIT", "DEBIT"}:
        raise RebirthPersistenceError("Wallet entry_type must be CREDIT or DEBIT.", "invalid_wallet_entry", status=400)
    amount = int(amount or 0)
    if amount <= 0:
        raise RebirthPersistenceError("Wallet ledger amount must be positive.", "invalid_wallet_amount", status=400)
    return entry_type, amount


def _wallet_balance_expression():
    return func.coalesce(
        func.sum(case((WalletLedger.entry_type == "CREDIT", WalletLedger.amount), else_=-WalletLedger.amount)),
        0,
    )


async def _wallet_balance_in_session(session, user_id: int, currency: str) -> int:
    currency = normalize_wallet_currency(currency)
    result = await session.execute(
        select(_wallet_balance_expression()).where(
            WalletLedger.user_id == int(user_id),
            WalletLedger.currency == currency,
        )
    )
    return int(result.scalar_one() or 0)


async def get_user_balance(user_id: int, currency: str, *, session: Optional[AsyncSession] = None) -> int:
    if session is not None:
        return await _wallet_balance_in_session(session, user_id, currency)
    await ensure_async_schema_once()
    session_maker = async_session_factory()
    try:
        async with session_maker() as owned_session:
            return await _wallet_balance_in_session(owned_session, user_id, currency)
    except SQLAlchemyError as exc:
        raise RebirthPersistenceError("Failed to calculate wallet balance.", "database_read_failed", status=500) from exc


def _add_async_wallet_entry(session, user_id, currency, entry_type, amount, source, reference_id):
    entry_type, amount = _normalize_wallet_entry(entry_type, amount)
    session.add(
        WalletLedger(
            id=str(uuid.uuid4()),
            user_id=int(user_id),
            currency=normalize_wallet_currency(currency),
            entry_type=entry_type,
            amount=amount,
            source=str(source or "MATCH_REWARD").strip().upper(),
            reference_id=str(reference_id or ""),
            timestamp=utc_datetime(),
        )
    )


async def _set_serializable_if_postgres(session):
    bind = session.get_bind()
    if bind is not None and getattr(bind.dialect, "name", "") == "postgresql":
        await session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))


def _market_offer_payload(offer, *, seller_name=None):
    card = get_card(offer.card_id)
    return {
        "id": str(offer.id),
        "seller_id": int(offer.seller_id),
        "seller_name": seller_name,
        "card_id": offer.card_id,
        "card": card,
        "price": int(offer.price),
        "currency_type": normalize_market_currency(offer.currency_type),
        "status": str(offer.status),
        "created_at": offer.created_at.isoformat() if hasattr(offer.created_at, "isoformat") else str(offer.created_at),
    }


async def create_market_offer(user_id: int, card_id: str, price: int, currency_type: str, *, username: Optional[str] = None) -> dict:
    card = get_card(card_id)
    price = _normalize_market_price(price)
    currency_type = normalize_market_currency(currency_type)
    await ensure_async_schema_once()
    session_maker = async_session_factory()
    try:
        async with session_maker() as session:
            async with session.begin():
                await _set_serializable_if_postgres(session)
                await _ensure_async_user_account(session, user_id, username=username)
                rows = (
                    await session.execute(
                        select(UserCollection)
                        .where(UserCollection.user_id == int(user_id), UserCollection.card_id == card["id"])
                        .with_for_update()
                    )
                ).scalars().all()
                available = sum(max(0, int(row.quantity or 0) - int(row.locked_quantity or 0)) for row in rows)
                if available <= 0:
                    raise RebirthPersistenceError("Card is not available for market listing.", "card_not_available", status=409)
                for row in rows:
                    if int(row.quantity or 0) - int(row.locked_quantity or 0) > 0:
                        row.locked_quantity = int(row.locked_quantity or 0) + 1
                        break
                offer = MarketOffer(
                    id=str(uuid.uuid4()),
                    seller_id=int(user_id),
                    card_id=card["id"],
                    price=price,
                    currency_type=currency_type,
                    status="ACTIVE",
                    created_at=utc_datetime(),
                )
                session.add(offer)
                await session.flush()
                return _market_offer_payload(offer, seller_name=username)
    except RebirthPersistenceError:
        raise
    except SQLAlchemyError as exc:
        raise RebirthPersistenceError("Failed to list card on market.", "database_write_failed", status=500) from exc


async def active_market_offers(exclude_user_id: Optional[int] = None, limit: int = 40) -> list[dict]:
    await ensure_async_schema_once()
    session_maker = async_session_factory()
    limit = max(1, min(int(limit or 40), 100))
    try:
        async with session_maker() as session:
            statement = select(MarketOffer).where(MarketOffer.status == "ACTIVE").order_by(MarketOffer.created_at.desc()).limit(limit)
            if exclude_user_id:
                statement = statement.where(MarketOffer.seller_id != int(exclude_user_id))
            rows = (await session.execute(statement)).scalars().all()
            return [_market_offer_payload(row) for row in rows]
    except SQLAlchemyError as exc:
        raise RebirthPersistenceError("Failed to load market offers.", "database_read_failed", status=500) from exc


async def buy_market_offer(user_id: int, offer_id: str, *, username: Optional[str] = None) -> dict:
    if not offer_id:
        raise RebirthPersistenceError("offer_id is required.", "missing_market_offer", status=400)
    await ensure_async_schema_once()
    session_maker = async_session_factory()
    try:
        async with session_maker() as session:
            async with session.begin():
                await _set_serializable_if_postgres(session)
                await _ensure_async_user_account(session, user_id, username=username)
                buyer = (
                    await session.execute(
                        select(UserAccount).where(UserAccount.id == int(user_id)).with_for_update()
                    )
                ).scalar_one()
                offer = (
                    await session.execute(
                        select(MarketOffer).where(MarketOffer.id == str(offer_id)).with_for_update()
                    )
                ).scalar_one_or_none()
                if not offer or offer.status != "ACTIVE":
                    raise RebirthPersistenceError("Market offer is no longer active.", "market_offer_unavailable", status=409)
                if int(offer.seller_id) == int(user_id):
                    raise RebirthPersistenceError("Players cannot buy their own market offer.", "market_self_buy", status=409)
                seller = (
                    await session.execute(
                        select(UserAccount).where(UserAccount.id == int(offer.seller_id)).with_for_update()
                    )
                ).scalar_one_or_none()
                if not seller:
                    raise RebirthPersistenceError("Market seller account is missing.", "market_seller_missing", status=409)

                currency_type = normalize_market_currency(offer.currency_type)
                price = int(offer.price)
                buyer_balance = await get_user_balance(int(user_id), currency_type, session=session)
                if buyer_balance < price:
                    raise RebirthPersistenceError("Insufficient balance for market purchase.", "insufficient_balance", status=409)
                fee = _market_fee(price)
                seller_net = price - fee

                collection_rows = (
                    await session.execute(
                        select(UserCollection)
                        .where(
                            UserCollection.user_id == int(offer.seller_id),
                            UserCollection.card_id == offer.card_id,
                            UserCollection.locked_quantity > 0,
                        )
                        .with_for_update()
                    )
                ).scalars().all()
                locked_row = next((row for row in collection_rows if int(row.locked_quantity or 0) > 0), None)
                if not locked_row:
                    raise RebirthPersistenceError("Locked market item is missing.", "market_item_lock_missing", status=409)
                locked_row.quantity = max(0, int(locked_row.quantity or 0) - 1)
                locked_row.locked_quantity = max(0, int(locked_row.locked_quantity or 0) - 1)
                session.add(
                    UserCollection(
                        user_id=int(user_id),
                        card_id=offer.card_id,
                        quantity=1,
                        locked_quantity=0,
                        evolved_tier=int(get_card(offer.card_id).get("tier", 1) or 1),
                    )
                )
                offer.status = "SOLD"
                reference_id = str(offer.id)
                _add_async_wallet_entry(session, int(user_id), currency_type, "DEBIT", price, "MARKET_SALE", reference_id)
                _add_async_wallet_entry(session, int(offer.seller_id), currency_type, "CREDIT", price, "MARKET_SALE", reference_id)
                _add_async_wallet_entry(session, int(offer.seller_id), currency_type, "DEBIT", fee, "MARKET_SALE", reference_id)
                session.add_all(
                    [
                        EconomyTransaction(
                            user_id=int(user_id),
                            transaction_type="MARKET_BUY",
                            amount=-price,
                            currency=currency_type,
                            reference_id=reference_id,
                            timestamp=utc_datetime(),
                        ),
                        EconomyTransaction(
                            user_id=int(offer.seller_id),
                            transaction_type="MARKET_SALE",
                            amount=seller_net,
                            currency=currency_type,
                            reference_id=reference_id,
                            timestamp=utc_datetime(),
                        ),
                        EconomyTransaction(
                            user_id=int(offer.seller_id),
                            transaction_type="MARKET_FEE",
                            amount=-fee,
                            currency=currency_type,
                            reference_id=reference_id,
                            timestamp=utc_datetime(),
                        ),
                    ]
                )
                await session.flush()
                buyer_wallet = {
                    "GOLD": await get_user_balance(int(user_id), "GOLD", session=session),
                    "COINZ": await get_user_balance(int(user_id), "COINZ", session=session),
                    "ledger_source": "wallet_ledger",
                }
                seller_wallet = {
                    "GOLD": await get_user_balance(int(offer.seller_id), "GOLD", session=session),
                    "COINZ": await get_user_balance(int(offer.seller_id), "COINZ", session=session),
                    "ledger_source": "wallet_ledger",
                }
                return {
                    "offer": _market_offer_payload(offer),
                    "buyer_id": int(user_id),
                    "seller_id": int(offer.seller_id),
                    "price": price,
                    "fee": fee,
                    "seller_net": seller_net,
                    "currency_type": currency_type,
                    "buyer_balance": buyer_wallet[currency_type],
                    "seller_balance": seller_wallet[currency_type],
                    "buyer_wallet": buyer_wallet,
                    "seller_wallet": seller_wallet,
                }
    except RebirthPersistenceError:
        raise
    except SQLAlchemyError as exc:
        raise RebirthPersistenceError("Failed to buy market offer.", "database_write_failed", status=500) from exc


def normalize_email(email):
    return str(email or "").strip().lower()


def normalize_username(username):
    return str(username or "").strip()


def calculate_level(xp):
    return max(1, int(xp or 0) // 500 + 1)


def next_level_xp(level):
    return int(level) * 500


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt.encode("utf-8"),
        HASH_ITERATIONS,
    ).hex()
    return salt, digest


def verify_password(password, salt, expected_digest):
    _, digest = hash_password(password, salt=salt)
    return hmac.compare_digest(digest, expected_digest)


def _stable_rank(seed, card_id, salt):
    payload = f"{seed}:{salt}:{card_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _ranked_ids(seed, card_ids, salt):
    return sorted(card_ids, key=lambda card_id: (_stable_rank(seed, card_id, salt), card_id))


def deterministic_starter_deck(seed_source):
    seed = str(seed_source or "rebirth-starter")
    monster_pool = [card["id"] for card in CARD_CATALOG if is_monster(card) and int(card.get("tier", 1) or 1) == 1]
    spell_pool = [card["id"] for card in CARD_CATALOG if is_spell(card)]
    trap_pool = [card["id"] for card in CARD_CATALOG if is_trap(card)]
    monster_count = 18 + (int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:2], 16) % 5)
    remaining = STARTER_DECK_SIZE - monster_count
    spell_count = remaining // 2
    trap_count = remaining - spell_count

    ranked_monsters = _ranked_ids(seed, monster_pool, "monster")
    duplicate_anchor = ranked_monsters[0]
    monsters = [duplicate_anchor, duplicate_anchor]
    monsters.extend([card_id for card_id in ranked_monsters[1:] if card_id != duplicate_anchor][: monster_count - 2])
    spells = _ranked_ids(seed, spell_pool, "spell")[:spell_count]
    traps = _ranked_ids(seed, trap_pool, "trap")[:trap_count]
    deck = monsters + spells + traps
    validate_deck_distribution(deck)
    return deck


def starter_collection_counts(seed_source=None):
    return Counter(deterministic_starter_deck(seed_source or "rebirth-starter"))


class RebirthRepository:
    def __init__(self, db_path):
        self.db_path = db_path

    def connect(self):
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def ensure_schema(self):
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_collection (
                    user_id INTEGER NOT NULL,
                    card_id TEXT NOT NULL,
                    copies INTEGER NOT NULL DEFAULT 0,
                    locked_copies INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, card_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS user_loadout (
                    user_id INTEGER NOT NULL,
                    slot INTEGER NOT NULL,
                    card_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, slot),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS user_progress (
                    user_id INTEGER PRIMARY KEY,
                    xp INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    clashes INTEGER NOT NULL DEFAULT 0,
                    boosters_opened INTEGER NOT NULL DEFAULT 0,
                    tutorial_step INTEGER NOT NULL DEFAULT 0,
                    tutorial_complete INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS reward_claims (
                    user_id INTEGER NOT NULL,
                    reward_key TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, reward_key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS booster_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    booster_id TEXT NOT NULL,
                    seed TEXT NOT NULL,
                    cards_json TEXT NOT NULL,
                    opened_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id INTEGER NOT NULL,
                    achievement_key TEXT NOT NULL,
                    unlocked_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, achievement_key),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS match_history (
                    match_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    seed TEXT,
                    bot_profile_id TEXT,
                    status TEXT NOT NULL,
                    winner TEXT,
                    started_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    final_state_hash TEXT,
                    final_state_json TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS match_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    command_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    command_type TEXT NOT NULL,
                    command_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (match_id, command_id),
                    FOREIGN KEY (match_id) REFERENCES match_history(match_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS match_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    event_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (match_id, event_id),
                    FOREIGN KEY (match_id) REFERENCES match_history(match_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS economy_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    resource TEXT NOT NULL,
                    delta INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    reference_type TEXT,
                    reference_id TEXT,
                    balance_after INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS economy_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    reference_id TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS wallet_ledger (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    currency TEXT NOT NULL CHECK(currency IN ('GOLD', 'COINZ')),
                    entry_type TEXT NOT NULL CHECK(entry_type IN ('CREDIT', 'DEBIT')),
                    amount INTEGER NOT NULL CHECK(amount > 0),
                    source TEXT NOT NULL,
                    reference_id TEXT NOT NULL DEFAULT '',
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS admin_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    user_id INTEGER,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS market_offers (
                    id TEXT PRIMARY KEY,
                    seller_id INTEGER NOT NULL,
                    card_id TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    currency_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_market_offers_status_created
                    ON market_offers(status, created_at);
                CREATE INDEX IF NOT EXISTS idx_market_offers_seller_status
                    ON market_offers(seller_id, status);
                CREATE INDEX IF NOT EXISTS idx_wallet_ledger_user_currency
                    ON wallet_ledger(user_id, currency, timestamp);
                CREATE INDEX IF NOT EXISTS idx_wallet_ledger_reference
                    ON wallet_ledger(reference_id);
                """
            )
            self._ensure_sqlite_column(db, "user_collection", "locked_copies", "INTEGER NOT NULL DEFAULT 0")
            self._backfill_wallet_ledger(db)

    def _ensure_sqlite_column(self, db, table, column, definition):
        columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _sqlite_columns(self, db, table):
        return {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}

    def _backfill_wallet_ledger(self, db):
        columns = self._sqlite_columns(db, "user_progress")
        legacy_currencies = []
        if "gold" in columns:
            legacy_currencies.append(("gold", "GOLD"))
        if "premium" in columns:
            legacy_currencies.append(("premium", "COINZ"))
        if not legacy_currencies:
            return
        now = utc_now()
        select_columns = ", ".join(["user_id"] + [column for column, _currency in legacy_currencies])
        rows = db.execute(f"SELECT {select_columns} FROM user_progress").fetchall()
        for row in rows:
            user_id = int(row["user_id"])
            for column, currency in legacy_currencies:
                amount = int(row[column] or 0)
                if amount <= 0:
                    continue
                existing = db.execute(
                    "SELECT 1 FROM wallet_ledger WHERE user_id = ? AND currency = ? LIMIT 1",
                    (user_id, currency),
                ).fetchone()
                if existing:
                    continue
                self._record_wallet_entry(
                    db,
                    user_id,
                    currency=currency,
                    entry_type="CREDIT",
                    amount=amount,
                    source="MATCH_REWARD",
                    reference_id=f"legacy:{user_id}:{currency}",
                    now=now,
                )

    def _record_wallet_entry(self, db, user_id, *, currency, entry_type, amount, source, reference_id, now=None):
        entry_type, amount = _normalize_wallet_entry(entry_type, amount)
        db.execute(
            """
            INSERT INTO wallet_ledger (id, user_id, currency, entry_type, amount, source, reference_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                int(user_id),
                normalize_wallet_currency(currency),
                entry_type,
                amount,
                str(source or "MATCH_REWARD").strip().upper(),
                str(reference_id or ""),
                now or utc_now(),
            ),
        )

    def get_user_balance(self, user_id, currency):
        self.ensure_schema()
        currency = normalize_wallet_currency(currency)
        with self.connect() as db:
            row = db.execute(
                """
                SELECT COALESCE(SUM(CASE WHEN entry_type = 'CREDIT' THEN amount ELSE -amount END), 0) AS balance
                FROM wallet_ledger
                WHERE user_id = ? AND currency = ?
                """,
                (int(user_id), currency),
            ).fetchone()
        return int(row["balance"] or 0)

    def wallet_payload(self, user_id):
        return {
            "GOLD": self.get_user_balance(user_id, "GOLD"),
            "COINZ": self.get_user_balance(user_id, "COINZ"),
            "ledger_source": "wallet_ledger",
        }

    def create_user(self, username, email, password):
        self.ensure_schema()
        username = normalize_username(username)
        email = normalize_email(email)
        password = str(password or "")
        if not USERNAME_RE.match(username):
            raise RebirthPersistenceError(
                "Username must be 3-24 characters and use letters, numbers or underscores.",
                "invalid_auth_payload",
            )
        if "@" not in email or "." not in email.split("@")[-1]:
            raise RebirthPersistenceError("A valid email is required.", "invalid_auth_payload")
        if len(password) < 8:
            raise RebirthPersistenceError("Password must be at least 8 characters.", "invalid_auth_payload")

        salt, digest = hash_password(password)
        now = utc_now()
        try:
            with self.connect() as db:
                cursor = db.execute(
                    """
                    INSERT INTO users (username, email, password_salt, password_hash, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (username, email, salt, digest, now),
                )
                user_id = int(cursor.lastrowid)
                self._seed_user_state(db, user_id, now, seed_source=f"{user_id}:{username}:{email}")
        except sqlite3.IntegrityError as exc:
            raise RebirthPersistenceError(
                "A Rebirth account with this username or email already exists.",
                "auth_conflict",
                status=409,
            ) from exc
        return self.get_user(user_id)

    def authenticate(self, email, password):
        self.ensure_schema()
        email = normalize_email(email)
        with self.connect() as db:
            row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row or not verify_password(password, row["password_salt"], row["password_hash"]):
            raise RebirthPersistenceError("Invalid email or password.", "invalid_credentials", status=401)
        return self.get_user(row["id"])

    def change_password(self, user_id, current_password, new_password):
        self.ensure_schema()
        new_password = str(new_password or "")
        if len(new_password) < 8:
            raise RebirthPersistenceError("Password must be at least 8 characters.", "invalid_auth_payload")
        with self.connect() as db:
            row = db.execute(
                "SELECT password_salt, password_hash FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if not row or not verify_password(current_password, row["password_salt"], row["password_hash"]):
                raise RebirthPersistenceError("Current password is invalid.", "invalid_credentials", status=401)
            salt, digest = hash_password(new_password)
            db.execute(
                "UPDATE users SET password_salt = ?, password_hash = ? WHERE id = ?",
                (salt, digest, user_id),
            )
        return self.get_user(user_id)

    def get_user(self, user_id):
        if not user_id:
            return None
        self.ensure_schema()
        with self.connect() as db:
            row = db.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def _seed_user_state(self, db, user_id, now, seed_source=None):
        starter_deck = deterministic_starter_deck(seed_source or f"{user_id}:starter")
        for card_id, copies in Counter(starter_deck).items():
            db.execute(
                """
                INSERT INTO user_collection (user_id, card_id, copies, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, card_id, int(copies), now),
            )
            self._record_ledger_entry(
                db,
                user_id,
                resource=f"card:{card_id}",
                delta=int(copies),
                reason="starter_collection",
                reference_type="account",
                reference_id=str(user_id),
                metadata={"card_id": card_id, "copies": int(copies), "starter_deck_size": len(starter_deck)},
                now=now,
            )
        for slot, card_id in enumerate(starter_deck, start=1):
            db.execute(
                """
                INSERT INTO user_loadout (user_id, slot, card_id, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, slot, card_id, now),
            )
        db.execute(
            """
            INSERT INTO user_progress (user_id, xp, wins, losses, clashes, boosters_opened, tutorial_step, tutorial_complete, updated_at)
            VALUES (?, 0, 0, 0, 0, 0, 0, 0, ?)
            """,
            (user_id, now),
        )
        self._record_wallet_entry(
            db,
            user_id,
            currency="GOLD",
            entry_type="CREDIT",
            amount=1000,
            source="MATCH_REWARD",
            reference_id=f"starter:{user_id}",
            now=now,
        )
        self._record_ledger_entry(
            db,
            user_id,
            resource="gold",
            delta=1000,
            reason="starter_wallet",
            reference_type="account",
            reference_id=str(user_id),
            metadata={"currency_type": "GOLD"},
            now=now,
        )
        self._unlock_achievements(db, user_id, ["founder"], now)

    def _record_ledger_entry(
        self,
        db,
        user_id,
        *,
        resource,
        delta,
        reason,
        reference_type=None,
        reference_id=None,
        metadata=None,
        now=None,
    ):
        now = now or utc_now()
        delta = int(delta or 0)
        row = db.execute(
            "SELECT COALESCE(SUM(delta), 0) AS balance FROM economy_ledger WHERE user_id = ? AND resource = ?",
            (user_id, resource),
        ).fetchone()
        balance_after = int(row["balance"] or 0) + delta
        db.execute(
            """
            INSERT INTO economy_ledger
                (user_id, resource, delta, reason, reference_type, reference_id, balance_after, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                resource,
                delta,
                reason,
                reference_type,
                reference_id,
                balance_after,
                json.dumps(metadata or {}, sort_keys=True),
                now,
            ),
        )
        return balance_after

    def _unlock_achievements(self, db, user_id, keys, now=None):
        now = now or utc_now()
        valid_keys = {achievement["key"] for achievement in ACHIEVEMENTS}
        for key in keys:
            if key not in valid_keys:
                continue
            db.execute(
                """
                INSERT OR IGNORE INTO user_achievements (user_id, achievement_key, unlocked_at)
                VALUES (?, ?, ?)
                """,
                (user_id, key, now),
            )

    def _sync_achievements(self, db, user_id, now=None):
        now = now or utc_now()
        user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return

        keys = ["founder"]
        progress = db.execute("SELECT * FROM user_progress WHERE user_id = ?", (user_id,)).fetchone()
        if progress:
            if int(progress["clashes"]) > 0:
                keys.append("first_clash")
            if int(progress["wins"]) > 0:
                keys.append("first_win")
            if int(progress["boosters_opened"]) > 0:
                keys.append("first_booster")
            if bool(progress["tutorial_complete"]):
                keys.append("tutorial_complete")
        daily = db.execute(
            "SELECT 1 FROM reward_claims WHERE user_id = ? AND reward_key = ?",
            (user_id, "daily_first_clash"),
        ).fetchone()
        if daily:
            keys.append("daily_claimed")
        self._unlock_achievements(db, user_id, keys, now)

    def collection_counts(self, user_id):
        self.ensure_schema()
        with self.connect() as db:
            rows = db.execute(
                "SELECT card_id, copies, locked_copies FROM user_collection WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        return Counter(
            {
                row["card_id"]: max(0, int(row["copies"] or 0) - int(row["locked_copies"] or 0))
                for row in rows
                if max(0, int(row["copies"] or 0) - int(row["locked_copies"] or 0)) > 0
            }
        )

    def locked_collection_counts(self, user_id):
        self.ensure_schema()
        with self.connect() as db:
            rows = db.execute(
                "SELECT card_id, locked_copies FROM user_collection WHERE user_id = ? AND locked_copies > 0",
                (user_id,),
            ).fetchall()
        return Counter({row["card_id"]: int(row["locked_copies"] or 0) for row in rows})

    def loadout_card_ids(self, user_id):
        self.ensure_schema()
        with self.connect() as db:
            rows = db.execute(
                "SELECT card_id FROM user_loadout WHERE user_id = ? ORDER BY slot ASC",
                (user_id,),
            ).fetchall()
        card_ids = [row["card_id"] for row in rows]
        if card_ids:
            try:
                validate_deck_distribution(card_ids)
                return card_ids
            except ValueError:
                return list(DEFAULT_LOADOUT)
        return list(DEFAULT_LOADOUT)

    def validate_and_save_loadout(self, user_id, card_ids):
        selected = self._validate_owned_cards(user_id, card_ids)
        now = utc_now()
        with self.connect() as db:
            db.execute("DELETE FROM user_loadout WHERE user_id = ?", (user_id,))
            for slot, card_id in enumerate(selected, start=1):
                db.execute(
                    """
                    INSERT INTO user_loadout (user_id, slot, card_id, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, slot, card_id, now),
                )
        return selected

    def _validate_owned_cards(self, user_id, card_ids):
        if not isinstance(card_ids, list):
            raise RebirthPersistenceError("card_ids must be a list.", "invalid_loadout")
        selected = [str(card_id) for card_id in card_ids if str(card_id or "").strip()]
        try:
            validate_deck_distribution(selected)
        except ValueError as exc:
            raise RebirthPersistenceError(str(exc), "invalid_loadout") from exc
        owned = self.collection_counts(user_id)
        selected_counts = Counter(selected)
        for card_id, amount in selected_counts.items():
            try:
                get_card(card_id)
            except ValueError as exc:
                raise RebirthPersistenceError(f"{card_id} is not a Rebirth card.", "invalid_loadout") from exc
            if owned.get(card_id, 0) < amount:
                raise RebirthPersistenceError(f"{card_id} exceeds owned copies.", "invalid_loadout")
        return selected

    def _currency_balance(self, db, user_id, currency_type):
        user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise RebirthPersistenceError("Account wallet is missing.", "missing_wallet", status=409)
        currency_type = normalize_market_currency(currency_type)
        row = db.execute(
            """
            SELECT COALESCE(SUM(CASE WHEN entry_type = 'CREDIT' THEN amount ELSE -amount END), 0) AS balance
            FROM wallet_ledger
            WHERE user_id = ? AND currency = ?
            """,
            (int(user_id), currency_type),
        ).fetchone()
        return int(row["balance"] or 0)

    def _record_economy_transaction(self, db, user_id, transaction_type, amount, currency, reference_id, now=None):
        db.execute(
            """
            INSERT INTO economy_transactions (user_id, transaction_type, amount, currency, reference_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (int(user_id), str(transaction_type), int(amount), str(currency), str(reference_id or ""), now or utc_now()),
        )

    def _sqlite_offer_payload(self, row):
        if not row:
            return None
        return {
            "id": row["id"],
            "seller_id": int(row["seller_id"]),
            "seller_name": row["seller_name"] if "seller_name" in row.keys() else None,
            "card_id": row["card_id"],
            "card": get_card(row["card_id"]),
            "price": int(row["price"]),
            "currency_type": normalize_market_currency(row["currency_type"]),
            "status": row["status"],
            "created_at": row["created_at"],
        }

    def market_offers(self, exclude_user_id=None, limit=40):
        self.ensure_schema()
        limit = max(1, min(int(limit or 40), 100))
        params = []
        where = ["market_offers.status = 'ACTIVE'"]
        if exclude_user_id:
            where.append("market_offers.seller_id != ?")
            params.append(int(exclude_user_id))
        params.append(limit)
        with self.connect() as db:
            rows = db.execute(
                f"""
                SELECT market_offers.*, users.username AS seller_name
                FROM market_offers
                JOIN users ON users.id = market_offers.seller_id
                WHERE {' AND '.join(where)}
                ORDER BY market_offers.created_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._sqlite_offer_payload(row) for row in rows]

    def create_market_offer(self, user_id, card_id, price, currency_type):
        self.ensure_schema()
        card = get_card(card_id)
        price = _normalize_market_price(price)
        currency_type = normalize_market_currency(currency_type)
        offer_id = str(uuid.uuid4())
        now = utc_now()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                raise RebirthPersistenceError("Seller account was not found.", "missing_user", status=404)
            row = db.execute(
                "SELECT copies, locked_copies FROM user_collection WHERE user_id = ? AND card_id = ?",
                (user_id, card["id"]),
            ).fetchone()
            copies = int(row["copies"] or 0) if row else 0
            locked = int(row["locked_copies"] or 0) if row else 0
            available = max(0, copies - locked)
            if available <= 0:
                raise RebirthPersistenceError("Card is not available for market listing.", "card_not_available", status=409)
            loadout_count = db.execute(
                "SELECT COUNT(*) AS amount FROM user_loadout WHERE user_id = ? AND card_id = ?",
                (user_id, card["id"]),
            ).fetchone()["amount"]
            if int(loadout_count or 0) > available - 1:
                raise RebirthPersistenceError(
                    "This card is still required by the active 30-card loadout.",
                    "card_locked_by_loadout",
                    status=409,
                )
            db.execute(
                "UPDATE user_collection SET locked_copies = locked_copies + 1, updated_at = ? WHERE user_id = ? AND card_id = ?",
                (now, user_id, card["id"]),
            )
            db.execute(
                """
                INSERT INTO market_offers (id, seller_id, card_id, price, currency_type, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?)
                """,
                (offer_id, user_id, card["id"], price, currency_type, now),
            )
            offer = db.execute(
                """
                SELECT market_offers.*, users.username AS seller_name
                FROM market_offers
                JOIN users ON users.id = market_offers.seller_id
                WHERE market_offers.id = ?
                """,
                (offer_id,),
            ).fetchone()
        return self._sqlite_offer_payload(offer)

    def buy_market_offer(self, buyer_id, offer_id):
        self.ensure_schema()
        if not offer_id:
            raise RebirthPersistenceError("offer_id is required.", "missing_market_offer", status=400)
        now = utc_now()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            buyer = db.execute("SELECT id FROM users WHERE id = ?", (buyer_id,)).fetchone()
            if not buyer:
                raise RebirthPersistenceError("Buyer account was not found.", "missing_user", status=404)
            offer = db.execute(
                """
                SELECT market_offers.*, users.username AS seller_name
                FROM market_offers
                JOIN users ON users.id = market_offers.seller_id
                WHERE market_offers.id = ? AND market_offers.status = 'ACTIVE'
                """,
                (str(offer_id),),
            ).fetchone()
            if not offer:
                raise RebirthPersistenceError("Market offer is no longer active.", "market_offer_unavailable", status=409)
            seller_id = int(offer["seller_id"])
            if seller_id == int(buyer_id):
                raise RebirthPersistenceError("Players cannot buy their own market offer.", "market_self_buy", status=409)

            currency_type = normalize_market_currency(offer["currency_type"])
            price = int(offer["price"])
            buyer_balance = self._currency_balance(db, buyer_id, currency_type)
            if buyer_balance < price:
                raise RebirthPersistenceError("Insufficient balance for market purchase.", "insufficient_balance", status=409)
            seller_balance = self._currency_balance(db, seller_id, currency_type)
            fee = _market_fee(price)
            seller_net = price - fee
            self._record_wallet_entry(
                db,
                buyer_id,
                currency=currency_type,
                entry_type="DEBIT",
                amount=price,
                source="MARKET_SALE",
                reference_id=offer["id"],
                now=now,
            )
            self._record_wallet_entry(
                db,
                seller_id,
                currency=currency_type,
                entry_type="CREDIT",
                amount=price,
                source="MARKET_SALE",
                reference_id=offer["id"],
                now=now,
            )
            self._record_wallet_entry(
                db,
                seller_id,
                currency=currency_type,
                entry_type="DEBIT",
                amount=fee,
                source="MARKET_SALE",
                reference_id=offer["id"],
                now=now,
            )

            collection = db.execute(
                """
                SELECT copies, locked_copies
                FROM user_collection
                WHERE user_id = ? AND card_id = ? AND locked_copies > 0
                """,
                (seller_id, offer["card_id"]),
            ).fetchone()
            if not collection:
                raise RebirthPersistenceError("Locked market item is missing.", "market_item_lock_missing", status=409)
            db.execute(
                """
                UPDATE user_collection
                SET copies = MAX(copies - 1, 0),
                    locked_copies = MAX(locked_copies - 1, 0),
                    updated_at = ?
                WHERE user_id = ? AND card_id = ?
                """,
                (now, seller_id, offer["card_id"]),
            )
            db.execute(
                """
                INSERT INTO user_collection (user_id, card_id, copies, locked_copies, updated_at)
                VALUES (?, ?, 1, 0, ?)
                ON CONFLICT(user_id, card_id) DO UPDATE SET
                    copies = copies + 1,
                    updated_at = excluded.updated_at
                """,
                (buyer_id, offer["card_id"], now),
            )
            db.execute("UPDATE market_offers SET status = 'SOLD' WHERE id = ?", (offer["id"],))
            self._record_economy_transaction(db, buyer_id, "MARKET_BUY", -price, currency_type, offer["id"], now)
            self._record_economy_transaction(db, seller_id, "MARKET_SALE", seller_net, currency_type, offer["id"], now)
            self._record_economy_transaction(db, seller_id, "MARKET_FEE", -fee, currency_type, offer["id"], now)
            self._record_ledger_entry(
                db,
                buyer_id,
                resource=currency_type.lower(),
                delta=-price,
                reason="market_buy",
                reference_type="market_offer",
                reference_id=offer["id"],
                metadata={"card_id": offer["card_id"], "seller_id": seller_id, "fee": fee},
                now=now,
            )
            self._record_ledger_entry(
                db,
                seller_id,
                resource=currency_type.lower(),
                delta=price,
                reason="market_sale_gross",
                reference_type="market_offer",
                reference_id=offer["id"],
                metadata={"card_id": offer["card_id"], "buyer_id": buyer_id},
                now=now,
            )
            self._record_ledger_entry(
                db,
                seller_id,
                resource=currency_type.lower(),
                delta=-fee,
                reason="market_fee_sink",
                reference_type="market_offer",
                reference_id=offer["id"],
                metadata={"card_id": offer["card_id"], "buyer_id": buyer_id, "fee_rate": "5%"},
                now=now,
            )
            self._record_ledger_entry(
                db,
                seller_id,
                resource=f"card:{offer['card_id']}",
                delta=-1,
                reason="market_card_sold",
                reference_type="market_offer",
                reference_id=offer["id"],
                metadata={"buyer_id": buyer_id},
                now=now,
            )
            self._record_ledger_entry(
                db,
                buyer_id,
                resource=f"card:{offer['card_id']}",
                delta=1,
                reason="market_card_bought",
                reference_type="market_offer",
                reference_id=offer["id"],
                metadata={"seller_id": seller_id},
                now=now,
            )
            sold_offer = db.execute(
                """
                SELECT market_offers.*, users.username AS seller_name
                FROM market_offers
                JOIN users ON users.id = market_offers.seller_id
                WHERE market_offers.id = ?
                """,
                (offer["id"],),
            ).fetchone()
            buyer_wallet = {
                "GOLD": self._currency_balance(db, buyer_id, "GOLD"),
                "COINZ": self._currency_balance(db, buyer_id, "COINZ"),
                "ledger_source": "wallet_ledger",
            }
            seller_wallet = {
                "GOLD": self._currency_balance(db, seller_id, "GOLD"),
                "COINZ": self._currency_balance(db, seller_id, "COINZ"),
                "ledger_source": "wallet_ledger",
            }
        return {
            "offer": self._sqlite_offer_payload(sold_offer),
            "buyer_id": int(buyer_id),
            "seller_id": seller_id,
            "price": price,
            "fee": fee,
            "seller_net": seller_net,
            "currency_type": currency_type,
            "buyer_balance": buyer_wallet[currency_type],
            "seller_balance": seller_wallet[currency_type],
            "buyer_wallet": buyer_wallet,
            "seller_wallet": seller_wallet,
        }

    def add_cards(self, user_id, cards):
        self.ensure_schema()
        now = utc_now()
        with self.connect() as db:
            for card in cards:
                db.execute(
                    """
                    INSERT INTO user_collection (user_id, card_id, copies, updated_at)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(user_id, card_id) DO UPDATE SET
                        copies = copies + 1,
                        updated_at = excluded.updated_at
                    """,
                    (user_id, card["id"], now),
                )
                self._record_ledger_entry(
                    db,
                    user_id,
                    resource=f"card:{card['id']}",
                    delta=1,
                    reason="card_granted",
                    reference_type="collection",
                    reference_id=card["id"],
                    metadata={"card_id": card["id"], "name": card.get("name")},
                    now=now,
                )

    def record_booster(self, user_id, booster, seed):
        self.ensure_schema()
        cards = booster.get("cards", [])
        now = utc_now()
        with self.connect() as db:
            for card in cards:
                db.execute(
                    """
                    INSERT INTO user_collection (user_id, card_id, copies, updated_at)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(user_id, card_id) DO UPDATE SET
                        copies = copies + 1,
                        updated_at = excluded.updated_at
                    """,
                    (user_id, card["id"], now),
                )
                self._record_ledger_entry(
                    db,
                    user_id,
                    resource=f"card:{card['id']}",
                    delta=1,
                    reason="booster_card",
                    reference_type="booster",
                    reference_id=booster.get("booster_id", "starter_booster_demo"),
                    metadata={"card_id": card["id"], "name": card.get("name"), "seed": str(seed or "")},
                    now=now,
                )
            db.execute(
                """
                INSERT INTO booster_history (user_id, booster_id, seed, cards_json, opened_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    booster.get("booster_id", "starter_booster_demo"),
                    str(seed or ""),
                    json.dumps([card["id"] for card in cards]),
                    now,
                ),
            )
            db.execute(
                """
                UPDATE user_progress
                SET boosters_opened = boosters_opened + 1,
                    xp = xp + 40,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (now, user_id),
            )
            self._record_ledger_entry(
                db,
                user_id,
                resource="xp",
                delta=40,
                reason="booster_opened",
                reference_type="booster",
                reference_id=booster.get("booster_id", "starter_booster_demo"),
                metadata={"seed": str(seed or ""), "cards": [card["id"] for card in cards]},
                now=now,
            )
            self._unlock_achievements(db, user_id, ["first_booster"], now)

    def booster_history(self, user_id, limit=5):
        self.ensure_schema()
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT booster_id, cards_json, opened_at
                FROM booster_history
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        history = []
        for row in rows:
            try:
                card_ids = json.loads(row["cards_json"])
            except (TypeError, json.JSONDecodeError):
                card_ids = []
            cards = []
            invalid_card_ids = []
            for card_id in card_ids:
                try:
                    cards.append(get_card(card_id))
                except ValueError:
                    invalid_card_ids.append(str(card_id))
            history.append(
                {
                    "booster_id": row["booster_id"],
                    "opened_at": row["opened_at"],
                    "cards": cards,
                    "invalid_card_ids": invalid_card_ids,
                }
            )
        return history

    def progression(self, user_id):
        self.ensure_schema()
        with self.connect() as db:
            row = db.execute("SELECT * FROM user_progress WHERE user_id = ?", (user_id,)).fetchone()
            daily_claimed = bool(
                db.execute(
                    "SELECT 1 FROM reward_claims WHERE user_id = ? AND reward_key = ?",
                    (user_id, "daily_first_clash"),
                ).fetchone()
            )
        if not row:
            return None
        xp = int(row["xp"])
        level = calculate_level(xp)
        wallet = self.wallet_payload(user_id)
        return {
            "level": level,
            "xp": xp,
            "next_level_xp": next_level_xp(level),
            "wins": int(row["wins"]),
            "losses": int(row["losses"]),
            "clashes": int(row["clashes"]),
            "boosters_opened": int(row["boosters_opened"]),
            "tutorial_step": int(row["tutorial_step"]),
            "tutorial_complete": bool(row["tutorial_complete"]),
            "daily_claimed": daily_claimed,
            "gold": wallet["GOLD"],
            "coinz": wallet["COINZ"],
            "premium": wallet["COINZ"],
            "wallet": wallet,
        }

    def record_clash_result(self, user_id, public_match_state):
        if not user_id:
            return None
        now = utc_now()
        is_finished = bool(public_match_state.get("is_finished"))
        winner = public_match_state.get("winner")
        win_delta = 1 if is_finished and winner == "player" else 0
        loss_delta = 1 if is_finished and winner == "bot" else 0
        xp_delta = 25 + (75 if win_delta else 0) + (25 if loss_delta else 0)
        with self.connect() as db:
            db.execute(
                """
                UPDATE user_progress
                SET clashes = clashes + 1,
                    wins = wins + ?,
                    losses = losses + ?,
                    xp = xp + ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (win_delta, loss_delta, xp_delta, now, user_id),
            )
            self._record_ledger_entry(
                db,
                user_id,
                resource="xp",
                delta=xp_delta,
                reason="match_clash",
                reference_type="match",
                reference_id=public_match_state.get("match_id"),
                metadata={
                    "winner": winner,
                    "is_finished": is_finished,
                    "turn": public_match_state.get("turn"),
                    "outcome": (public_match_state.get("result") or {}).get("outcome"),
                },
                now=now,
            )
            unlocked = ["first_clash"]
            if win_delta:
                unlocked.append("first_win")
            self._unlock_achievements(db, user_id, unlocked, now)
        return self.progression(user_id)

    def claim_daily_reward(self, user_id):
        progress = self.progression(user_id)
        if not progress or progress["clashes"] < 1:
            raise RebirthPersistenceError("Play at least one clash before claiming the daily reward.", "reward_locked", 409)
        reward_key = "daily_first_clash"
        now = utc_now()
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO reward_claims (user_id, reward_key, claimed_at) VALUES (?, ?, ?)",
                    (user_id, reward_key, now),
                )
                db.execute(
                    "UPDATE user_progress SET xp = xp + 25, updated_at = ? WHERE user_id = ?",
                    (now, user_id),
                )
                self._record_ledger_entry(
                    db,
                    user_id,
                    resource="xp",
                    delta=25,
                    reason="daily_first_clash",
                    reference_type="reward",
                    reference_id=reward_key,
                    metadata={"reward_key": reward_key},
                    now=now,
                )
                self._unlock_achievements(db, user_id, ["daily_claimed"], now)
        except sqlite3.IntegrityError as exc:
            raise RebirthPersistenceError("Daily reward already claimed.", "reward_already_claimed", 409) from exc
        return {"reward_key": reward_key, "xp": 25, "progression": self.progression(user_id)}

    def complete_tutorial_step(self, user_id, step):
        step = max(1, min(4, int(step or 1)))
        now = utc_now()
        current = self.progression(user_id)
        if not current:
            raise RebirthPersistenceError("Account progress is missing.", "missing_progress", 404)
        xp_delta = 60 if not current["tutorial_complete"] and step >= 4 else 10
        with self.connect() as db:
            db.execute(
                """
                UPDATE user_progress
                SET tutorial_step = MAX(tutorial_step, ?),
                    tutorial_complete = CASE WHEN ? >= 4 THEN 1 ELSE tutorial_complete END,
                    xp = xp + ?,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (step, step, xp_delta, now, user_id),
            )
            self._record_ledger_entry(
                db,
                user_id,
                resource="xp",
                delta=xp_delta,
                reason="tutorial_step",
                reference_type="tutorial",
                reference_id=str(step),
                metadata={"step": step},
                now=now,
            )
            if step >= 4:
                self._unlock_achievements(db, user_id, ["tutorial_complete"], now)
        return {"step": step, "xp": xp_delta, "progression": self.progression(user_id)}

    def achievements(self, user_id):
        self.ensure_schema()
        with self.connect() as db:
            self._sync_achievements(db, user_id)
            rows = db.execute(
                """
                SELECT achievement_key, unlocked_at
                FROM user_achievements
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchall()
        unlocked = {row["achievement_key"]: row["unlocked_at"] for row in rows}
        payload = []
        for achievement in ACHIEVEMENTS:
            key = achievement["key"]
            payload.append(
                {
                    "key": key,
                    "name": achievement["name"],
                    "copy": achievement["copy"],
                    "unlocked": key in unlocked,
                    "unlocked_at": unlocked.get(key),
                }
            )
        return payload

    def profile(self, user_id):
        user = self.get_user(user_id)
        if not user:
            return None
        collection = self.collection_counts(user_id)
        loadout = self.loadout_card_ids(user_id)
        history = self.booster_history(user_id, limit=3)
        achievements = self.achievements(user_id)
        unlocked = [achievement for achievement in achievements if achievement["unlocked"]]
        return {
            "user": user,
            "progression": self.progression(user_id),
            "collection": {
                "owned_cards": sum(collection.values()),
                "unique_owned": len([card_id for card_id, copies in collection.items() if copies > 0]),
                "loadout_size": len(loadout),
            },
            "achievements": achievements,
            "unlocked_achievements": len(unlocked),
            "recent_boosters": history,
        }

    def upsert_match_history(self, user_id, match):
        if not user_id or not match:
            return None
        self.ensure_schema()
        from services.rebirth_events import state_hash
        from services.rebirth_serializers import public_state

        now = utc_now()
        public = public_state(match)
        status = "finished" if match.get("is_finished") else "active"
        bot_profile = match.get("bot_profile") or {}
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO match_history
                    (match_id, user_id, seed, bot_profile_id, status, winner, started_at, updated_at, final_state_hash, final_state_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id) DO UPDATE SET
                    status = excluded.status,
                    winner = excluded.winner,
                    updated_at = excluded.updated_at,
                    final_state_hash = excluded.final_state_hash,
                    final_state_json = excluded.final_state_json
                """,
                (
                    match["match_id"],
                    user_id,
                    match.get("seed"),
                    bot_profile.get("id"),
                    status,
                    match.get("winner"),
                    now,
                    now,
                    state_hash(match),
                    json.dumps(public, sort_keys=True),
                ),
            )
            for command in match.get("commands", []):
                db.execute(
                    """
                    INSERT OR IGNORE INTO match_commands
                        (match_id, user_id, command_id, version, command_type, command_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        match["match_id"],
                        user_id,
                        int(command.get("id", 0) or 0),
                        int(command.get("version", 0) or 0),
                        command.get("type"),
                        json.dumps(command, sort_keys=True),
                        now,
                    ),
                )
            for event in match.get("events", []):
                db.execute(
                    """
                    INSERT OR IGNORE INTO match_events
                        (match_id, user_id, event_id, version, event_type, event_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        match["match_id"],
                        user_id,
                        int(event.get("id", 0) or 0),
                        int(event.get("version", 0) or 0),
                        event.get("type"),
                        json.dumps(event, sort_keys=True),
                        now,
                    ),
                )
        return self.match_history(user_id, limit=1)[0]

    def match_history(self, user_id, limit=10):
        self.ensure_schema()
        limit = max(1, min(int(limit or 10), 50))
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT match_id, seed, bot_profile_id, status, winner, started_at, updated_at, final_state_hash, final_state_json
                FROM match_history
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            history = []
            for row in rows:
                command_count = db.execute(
                    "SELECT COUNT(*) AS amount FROM match_commands WHERE match_id = ?",
                    (row["match_id"],),
                ).fetchone()["amount"]
                event_count = db.execute(
                    "SELECT COUNT(*) AS amount FROM match_events WHERE match_id = ?",
                    (row["match_id"],),
                ).fetchone()["amount"]
                history.append(
                    {
                        "match_id": row["match_id"],
                        "seed": row["seed"],
                        "bot_profile_id": row["bot_profile_id"],
                        "status": row["status"],
                        "winner": row["winner"],
                        "started_at": row["started_at"],
                        "updated_at": row["updated_at"],
                        "state_hash": row["final_state_hash"],
                        "command_count": int(command_count),
                        "event_count": int(event_count),
                        "state": json.loads(row["final_state_json"]),
                    }
                )
        return history

    def match_events(self, user_id, match_id, limit=50):
        self.ensure_schema()
        limit = max(1, min(int(limit or 50), 200))
        with self.connect() as db:
            owner = db.execute(
                "SELECT 1 FROM match_history WHERE user_id = ? AND match_id = ?",
                (user_id, match_id),
            ).fetchone()
            if not owner:
                raise RebirthPersistenceError("Match history not found.", "missing_match", status=404)
            rows = db.execute(
                """
                SELECT event_json
                FROM match_events
                WHERE match_id = ?
                ORDER BY event_id ASC
                LIMIT ?
                """,
                (match_id, limit),
            ).fetchall()
        return [json.loads(row["event_json"]) for row in rows]

    def economy_ledger(self, user_id, limit=30):
        self.ensure_schema()
        limit = max(1, min(int(limit or 30), 100))
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT resource, delta, reason, reference_type, reference_id, balance_after, metadata_json, created_at
                FROM economy_ledger
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [
            {
                "resource": row["resource"],
                "delta": int(row["delta"]),
                "reason": row["reason"],
                "reference_type": row["reference_type"],
                "reference_id": row["reference_id"],
                "balance_after": int(row["balance_after"]),
                "metadata": json.loads(row["metadata_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def support_export(self, user_id):
        return {
            "user": self.get_user(user_id),
            "progression": self.progression(user_id),
            "wallet": self.wallet_payload(user_id),
            "collection": dict(self.collection_counts(user_id)),
            "loadout": self.loadout_card_ids(user_id),
            "achievements": self.achievements(user_id),
            "boosters": self.booster_history(user_id, limit=20),
            "matches": self.match_history(user_id, limit=20),
            "ledger": self.economy_ledger(user_id, limit=50),
        }

    def reset_account(self, user_id):
        self.ensure_schema()
        now = utc_now()
        with self.connect() as db:
            db.execute("DELETE FROM user_collection WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM user_loadout WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM reward_claims WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM booster_history WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM user_achievements WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM economy_ledger WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM wallet_ledger WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM match_history WHERE user_id = ?", (user_id,))
            db.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))
            self._seed_user_state(db, user_id, now)
        return self.support_export(user_id)

    def admin_grant(self, actor, user_id, *, resource, amount=1, card_id=None, reason="admin_grant"):
        self.ensure_schema()
        now = utc_now()
        amount = int(amount or 1)
        resource = str(resource or "").strip()
        with self.connect() as db:
            user = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                raise RebirthPersistenceError("Target Rebirth user was not found.", "missing_user", 404)
            if resource == "xp":
                db.execute(
                    "UPDATE user_progress SET xp = xp + ?, updated_at = ? WHERE user_id = ?",
                    (amount, now, user_id),
                )
                self._record_ledger_entry(
                    db,
                    user_id,
                    resource="xp",
                    delta=amount,
                    reason=reason,
                    reference_type="admin",
                    reference_id=str(actor),
                    metadata={"actor": actor},
                    now=now,
                )
            elif resource.upper() in {"GOLD", "COINZ", "COINS", "PREMIUM", "GEMS"}:
                currency = normalize_wallet_currency(resource)
                self._record_wallet_entry(
                    db,
                    user_id,
                    currency=currency,
                    entry_type="CREDIT" if amount >= 0 else "DEBIT",
                    amount=abs(amount),
                    source="MATCH_REWARD",
                    reference_id=str(actor),
                    now=now,
                )
                self._record_ledger_entry(
                    db,
                    user_id,
                    resource=currency.lower(),
                    delta=amount,
                    reason=reason,
                    reference_type="admin",
                    reference_id=str(actor),
                    metadata={"actor": actor, "currency": currency},
                    now=now,
                )
            elif resource == "card":
                card = get_card(card_id)
                db.execute(
                    """
                    INSERT INTO user_collection (user_id, card_id, copies, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(user_id, card_id) DO UPDATE SET
                        copies = copies + excluded.copies,
                        updated_at = excluded.updated_at
                    """,
                    (user_id, card["id"], amount, now),
                )
                self._record_ledger_entry(
                    db,
                    user_id,
                    resource=f"card:{card['id']}",
                    delta=amount,
                    reason=reason,
                    reference_type="admin",
                    reference_id=str(actor),
                    metadata={"actor": actor, "card_id": card["id"], "name": card["name"]},
                    now=now,
                )
            else:
                raise RebirthPersistenceError("Admin grant supports resource xp, card, GOLD or COINZ.", "invalid_admin_grant", 400)
            db.execute(
                """
                INSERT INTO admin_audit_log (actor, action, user_id, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(actor),
                    "grant",
                    user_id,
                    json.dumps(
                        {"resource": resource, "amount": amount, "card_id": card_id, "reason": reason},
                        sort_keys=True,
                    ),
                    now,
                ),
            )
        return self.support_export(user_id)

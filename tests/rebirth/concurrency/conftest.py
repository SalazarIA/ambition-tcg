"""Fixtures for the concurrency / race-condition suite.

Why testcontainers and not SQLite:
    The market transactions in services.rebirth_persistence call
    `SET TRANSACTION ISOLATION LEVEL SERIALIZABLE` only when the bound dialect
    is PostgreSQL. With SQLite the statement is a no-op and the locking
    behavior is completely different (BEGIN IMMEDIATE serializes writers
    globally). Validating the production isolation contract therefore
    requires a real Postgres instance.

    `testcontainers` boots a throwaway container per pytest session. If the
    user's Docker is not running, the `requires_postgres` marker pre-filters
    the suite (pytest.ini addopts), so these tests don't block the default
    fast run. We additionally skip cleanly inside the fixture if the
    container fails to start.

Schema lifecycle:
    - Session scope: container up, configure_async_database pointed at it,
      schema created once.
    - Function scope: TRUNCATE all rebirth tables between tests so each test
      starts from a clean state without paying the container-boot cost again.
"""
from __future__ import annotations

import asyncio
import os
from typing import Iterator

import pytest

# Skip everything in this directory if docker / testcontainers is unavailable.
docker = pytest.importorskip("docker", reason="docker SDK required for testcontainers")
postgres_module = pytest.importorskip(
    "testcontainers.postgres", reason="testcontainers package required"
)

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from services import rebirth_persistence  # noqa: E402


pytestmark = pytest.mark.requires_postgres


# Tables that get dirty during market / wallet tests. Order matters for
# truncate when foreign keys exist; we use CASCADE to keep it robust.
DIRTY_TABLES = (
    "market_offers",
    "user_collections",
    "wallet_ledger",
    "economy_transactions",
    "user_accounts",
)


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[str]:
    """Boot a Postgres 16 container once per pytest session.

    Yields the asyncpg-compatible URL. The container is torn down after the
    session even if a test errored.
    """
    PostgresContainer = postgres_module.PostgresContainer
    try:
        container = PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as exc:  # docker daemon not running, image pull failed, etc.
        pytest.skip(f"Could not start Postgres testcontainer: {exc}")

    try:
        # testcontainers returns a psycopg2-style URL; normalize for asyncpg.
        raw_url = container.get_connection_url()
        # Strip the +psycopg2 / +psycopg / driver suffix if present.
        if "://" in raw_url:
            scheme, rest = raw_url.split("://", 1)
            scheme = scheme.split("+", 1)[0]  # 'postgresql'
            raw_url = f"{scheme}://{rest}"
        yield raw_url
    finally:
        container.stop()


@pytest.fixture(scope="session")
def configured_async_db(postgres_container: str) -> Iterator[str]:
    """Wire services.rebirth_persistence to the testcontainer DB and create the schema.

    NullPool is critical here: asyncpg connections are bound to the event loop
    that opened them. The default QueuePool would cache a connection from the
    first test's loop and then explode on the next test with a different loop
    ("attached to a different loop"). NullPool forces a fresh connection per
    session checkout on the current loop and disposes it on close. Slower per
    test (microseconds), but correct under pytest-asyncio's per-function loop
    scope.
    """
    previous = {name: os.environ.get(name) for name in rebirth_persistence.ASYNC_DATABASE_ENV_NAMES}
    os.environ["REBIRTH_DATABASE_URL"] = postgres_container

    normalized_url = rebirth_persistence._normalize_async_database_url(postgres_container)
    engine = create_async_engine(normalized_url, poolclass=NullPool)
    rebirth_persistence.configure_async_database(engine=engine)

    asyncio.run(rebirth_persistence.ensure_async_schema())

    try:
        yield postgres_container
    finally:
        # Dispose the engine on its own loop so asyncpg can close its
        # connections cleanly. Running engine.dispose() on a fresh asyncio.run
        # is safe because NullPool means there are no live pooled connections
        # to drain at this point.
        try:
            asyncio.run(engine.dispose())
        except Exception:
            pass
        # Restore env to whatever it was.
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        rebirth_persistence.configure_async_database(None)


@pytest.fixture()
def clean_db(configured_async_db):
    """Truncate all dirty tables before each test."""
    async def _truncate():
        session_maker = rebirth_persistence.async_session_factory()
        async with session_maker() as session:
            async with session.begin():
                # Single TRUNCATE with CASCADE handles FK ordering and is faster
                # than per-table DELETE.
                table_list = ", ".join(DIRTY_TABLES)
                await session.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))

    asyncio.run(_truncate())
    yield


async def _seed_user(user_id: int, username: str, *, gold: int = 0, coinz: int = 0):
    """Create a UserAccount and credit its wallet ledger. Returns the account id.

    The starter wallet auto-credits 1000 GOLD on first contact via
    `_ensure_async_starter_wallet`; we add extra on top if requested.
    """
    session_maker = rebirth_persistence.async_session_factory()
    async with session_maker() as session:
        async with session.begin():
            await rebirth_persistence._ensure_async_user_account(session, user_id, username=username)
            if gold:
                rebirth_persistence._add_async_wallet_entry(
                    session, user_id, "GOLD", "CREDIT", gold, "TEST_TOPUP", f"topup:{user_id}"
                )
            if coinz:
                rebirth_persistence._add_async_wallet_entry(
                    session, user_id, "COINZ", "CREDIT", coinz, "TEST_TOPUP", f"topup:{user_id}"
                )
    return user_id


async def _grant_card(user_id: int, card_id: str, *, quantity: int = 1):
    """Give a card to a user's collection so they can list it on the market."""
    from services.rebirth_cards import get_card
    from services.rebirth_persistence import UserCollection

    session_maker = rebirth_persistence.async_session_factory()
    async with session_maker() as session:
        async with session.begin():
            tier = int(get_card(card_id).get("tier", 1) or 1)
            session.add(
                UserCollection(
                    user_id=int(user_id),
                    card_id=card_id,
                    quantity=int(quantity),
                    locked_quantity=0,
                    evolved_tier=tier,
                )
            )


@pytest.fixture()
def seed_user():
    """Async helper to seed users from inside tests."""
    return _seed_user


@pytest.fixture()
def grant_card():
    """Async helper to grant a card to a user's collection."""
    return _grant_card

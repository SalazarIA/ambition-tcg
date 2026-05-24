"""Real PostgreSQL fixtures for the synchronous production repository."""

from __future__ import annotations

from typing import Iterator

import pytest

from services.rebirth_cards import get_card
from services.rebirth_persistence import RebirthRepository
from services.rebirth_schema import upgrade_schema
from tests.rebirth.concurrency.availability import (
    POSTGRES_TESTCONTAINERS_AVAILABLE,
    POSTGRES_TESTCONTAINERS_SKIP_REASON,
    PostgresContainer,
)


pytestmark = pytest.mark.requires_postgres

DIRTY_TABLES = (
    "telemetry_events",
    "admin_audit_log",
    "match_events",
    "match_commands",
    "match_history",
    "market_offers",
    "wallet_ledger",
    "economy_transactions",
    "economy_idempotency_keys",
    "economy_ledger",
    "user_achievements",
    "booster_history",
    "reward_claims",
    "user_progress",
    "user_loadout",
    "user_collection",
    "user_sessions",
    "users",
)


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[str]:
    if not POSTGRES_TESTCONTAINERS_AVAILABLE or PostgresContainer is None:
        pytest.skip(POSTGRES_TESTCONTAINERS_SKIP_REASON)

    try:
        container = PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as exc:
        pytest.skip(f"Could not start Postgres testcontainer: {exc}")
    try:
        raw_url = container.get_connection_url()
        scheme, rest = raw_url.split("://", 1)
        yield f"{scheme.split('+', 1)[0]}://{rest}"
    finally:
        container.stop()


@pytest.fixture(scope="session")
def postgres_repo(postgres_container) -> RebirthRepository:
    upgrade_schema(postgres_container)
    return RebirthRepository(database_url=postgres_container)


@pytest.fixture()
def clean_db(postgres_repo):
    postgres_repo.ensure_schema()
    with postgres_repo.connect() as db:
        db.execute(f"TRUNCATE TABLE {', '.join(DIRTY_TABLES)} RESTART IDENTITY CASCADE")
    yield postgres_repo


@pytest.fixture()
def seed_user(clean_db):
    def _seed(username: str):
        return clean_db.create_user(username, f"{username}@example.com", "password123")

    return _seed


@pytest.fixture()
def grant_card(clean_db):
    def _grant(user_id: int, card_id: str, *, quantity: int = 1):
        clean_db.add_cards(user_id, [get_card(card_id)] * quantity)

    return _grant

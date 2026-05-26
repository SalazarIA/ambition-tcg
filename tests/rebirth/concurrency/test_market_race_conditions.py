"""Concurrency and restart integrity for the PostgreSQL-only runtime."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from services.rebirth_persistence import RebirthPersistenceError, RebirthRepository
from services.rebirth_schema import SCHEMA_VERSION, validate_schema
from tests.rebirth.concurrency.availability import (
    POSTGRES_TESTCONTAINERS_AVAILABLE,
    POSTGRES_TESTCONTAINERS_SKIP_REASON,
)


pytestmark = [
    pytest.mark.requires_postgres,
    pytest.mark.skipif(
        not POSTGRES_TESTCONTAINERS_AVAILABLE,
        reason=POSTGRES_TESTCONTAINERS_SKIP_REASON,
    ),
]

# This card is outside the deterministic starter loadouts used below, so each
# test measures only the explicitly granted market copy.
CARD_ID = "card_011"
PRICE = 50


def _available_copies(repo, user_id):
    return int(repo.collection_counts(user_id).get(CARD_ID, 0))


def test_concurrent_buyers_exactly_one_wins(clean_db, seed_user, grant_card):
    seller = seed_user("race_seller")
    grant_card(seller["id"], CARD_ID)
    offer = clean_db.create_market_offer(seller["id"], CARD_ID, PRICE, "GOLD")
    buyers = [seed_user(f"buyer_{index}") for index in range(10)]

    def buy(buyer):
        try:
            return clean_db.buy_market_offer(buyer["id"], offer["id"])
        except Exception as exc:
            return exc

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(buy, buyers))

    successes = [item for item in results if isinstance(item, dict)]
    failures = [item for item in results if isinstance(item, Exception)]
    assert len(successes) == 1
    assert len(failures) == 9
    assert all(isinstance(item, RebirthPersistenceError) for item in failures)
    assert all(item.code in {"market_offer_unavailable", "database_write_failed", "serialization_retry_exhausted"} for item in failures)
    winner_id = successes[0]["buyer_id"]
    assert _available_copies(clean_db, seller["id"]) == 0
    assert _available_copies(clean_db, winner_id) == 1
    assert clean_db.get_user_balance(winner_id, "GOLD") == 1000 - PRICE
    assert sum(_available_copies(clean_db, buyer["id"]) for buyer in buyers) == 1


def test_concurrent_listing_attempts_lock_one_copy(clean_db, seed_user, grant_card):
    seller = seed_user("listing_seller")
    grant_card(seller["id"], CARD_ID)

    def list_offer(index):
        try:
            return clean_db.create_market_offer(seller["id"], CARD_ID, PRICE + index, "GOLD")
        except Exception as exc:
            return exc

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(list_offer, range(5)))

    assert len([item for item in results if isinstance(item, dict)]) == 1
    failures = [item for item in results if isinstance(item, Exception)]
    assert all(isinstance(item, RebirthPersistenceError) for item in failures)


def test_premium_market_currency_is_disabled(clean_db, seed_user, grant_card):
    seller = seed_user("premium_seller")
    grant_card(seller["id"], CARD_ID)
    with pytest.raises(RebirthPersistenceError) as error:
        clean_db.create_market_offer(seller["id"], CARD_ID, PRICE, "COINZ")
    assert error.value.code == "premium_market_disabled"


def test_repository_survives_new_instance_restart(clean_db, postgres_container, seed_user):
    user = seed_user("restart_user")
    restarted = RebirthRepository(database_url=postgres_container)
    assert restarted.get_user(user["id"])["username"] == "restart_user"
    assert restarted.wallet_payload(user["id"])["GOLD"] == 1000


def test_migration_schema_is_current(postgres_repo):
    status = validate_schema(postgres_repo.engine)
    assert status["ok"] is True
    assert status["version"] == SCHEMA_VERSION

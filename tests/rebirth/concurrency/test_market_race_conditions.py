"""Race-condition tests against the market.

These tests target the actual transactional contract in
services.rebirth_persistence.buy_market_offer / create_market_offer:
SERIALIZABLE isolation + SELECT ... FOR UPDATE on the seller's locked row.

They run against a real Postgres testcontainer (see ./conftest.py). The
`requires_postgres` marker keeps them out of the default fast run; opt in
with `pytest -m requires_postgres` (Docker must be running).

The tests call the async service functions directly via asyncio.gather —
*not* through the Flask test_client. Flask's test_client serializes
requests in a single thread, which would defeat the entire point of
racing them.
"""
from __future__ import annotations

import asyncio
import uuid
from collections import Counter

import pytest
from sqlalchemy import select

from services.rebirth_persistence import (
    MarketOffer,
    RebirthPersistenceError,
    UserCollection,
    async_session_factory,
    buy_market_offer,
    create_market_offer,
    get_user_balance,
)


pytestmark = [pytest.mark.requires_postgres, pytest.mark.asyncio]


SELLER_ID = 9001
BUYER_IDS = list(range(9100, 9110))  # 10 concurrent buyers
CARD_ID = "card_023"  # a Water tier-1 monster — arbitrary but stable
PRICE = 50  # in GOLD; starter wallet credits 1000 → buyers can afford.


async def _seed_one_seller_with_card(seed_user, grant_card):
    await seed_user(SELLER_ID, "race-seller")
    await grant_card(SELLER_ID, CARD_ID, quantity=1)


async def _seed_buyers(seed_user, *, count: int):
    for buyer_id in BUYER_IDS[:count]:
        await seed_user(buyer_id, f"race-buyer-{buyer_id}")


async def _list_offer() -> str:
    payload = await create_market_offer(SELLER_ID, CARD_ID, PRICE, "GOLD", username="race-seller")
    return payload["id"]


async def _final_offer_status(offer_id: str) -> str:
    session_maker = async_session_factory()
    async with session_maker() as session:
        row = (
            await session.execute(select(MarketOffer).where(MarketOffer.id == offer_id))
        ).scalar_one()
        return row.status


async def _count_card_copies(user_id: int) -> int:
    session_maker = async_session_factory()
    async with session_maker() as session:
        rows = (
            await session.execute(
                select(UserCollection).where(
                    UserCollection.user_id == int(user_id),
                    UserCollection.card_id == CARD_ID,
                )
            )
        ).scalars().all()
        return sum(int(r.quantity or 0) for r in rows)


# --- the headline test -----------------------------------------------------


async def test_concurrent_buyers_exactly_one_wins(clean_db, seed_user, grant_card):
    """10 buyers race for 1 listed card. Exactly 1 wins, 9 fail cleanly.

    This is the double-spend test: if SERIALIZABLE + FOR UPDATE is broken,
    we'll see either (a) multiple successes (catastrophic), (b) total
    quantity in collections != 1 (catastrophic), or (c) ledger debit/credit
    imbalance.
    """
    await _seed_one_seller_with_card(seed_user, grant_card)
    await _seed_buyers(seed_user, count=10)
    offer_id = await _list_offer()

    results = await asyncio.gather(
        *(buy_market_offer(buyer_id, offer_id, username=f"race-buyer-{buyer_id}") for buyer_id in BUYER_IDS),
        return_exceptions=True,
    )

    successes = [r for r in results if isinstance(r, dict)]
    failures = [r for r in results if isinstance(r, BaseException)]

    # --- ACID assertions ---
    assert len(successes) == 1, f"expected exactly 1 buyer to win, got {len(successes)}"
    assert len(failures) == 9, f"expected 9 buyers to fail, got {len(failures)}"

    # Every failure must be a known controlled error, not a crash.
    for failure in failures:
        assert isinstance(failure, RebirthPersistenceError), (
            f"unexpected exception type {type(failure).__name__}: {failure!r}"
        )
        # In Postgres serializable mode, contenders can either hit the
        # business check (offer no longer active) OR be aborted by the
        # serialization detector. Both are acceptable; what's not acceptable
        # is a silent success.
        assert failure.code in {
            "market_offer_unavailable",
            "database_write_failed",  # wraps SerializationFailure
        }, f"unexpected failure code: {failure.code!r}"

    # --- inventory invariants ---
    winner_id = successes[0]["buyer_id"]
    assert winner_id in BUYER_IDS
    assert await _count_card_copies(winner_id) == 1
    assert await _count_card_copies(SELLER_ID) == 0
    losers = [b for b in BUYER_IDS if b != winner_id]
    for loser_id in losers:
        assert await _count_card_copies(loser_id) == 0, f"buyer {loser_id} got a phantom copy"

    # --- offer state ---
    assert await _final_offer_status(offer_id) == "SOLD"

    # --- ledger conservation ---
    # Winner paid PRICE in GOLD; seller received PRICE - fee. No other buyer was charged.
    starter_credit = 1000
    expected_winner_balance = starter_credit - PRICE
    actual_winner_balance = await get_user_balance(winner_id, "GOLD")
    assert actual_winner_balance == expected_winner_balance, (
        f"winner balance {actual_winner_balance} != expected {expected_winner_balance}"
    )
    for loser_id in losers:
        loser_balance = await get_user_balance(loser_id, "GOLD")
        assert loser_balance == starter_credit, (
            f"loser {loser_id} balance {loser_balance} drifted from starter {starter_credit}"
        )


# --- supporting integrity tests -------------------------------------------


async def test_seller_cannot_buy_own_offer(clean_db, seed_user, grant_card):
    """Listing your own card and then trying to buy it must fail loudly."""
    await _seed_one_seller_with_card(seed_user, grant_card)
    offer_id = await _list_offer()

    with pytest.raises(RebirthPersistenceError) as exc_info:
        await buy_market_offer(SELLER_ID, offer_id, username="race-seller")
    assert exc_info.value.code == "market_self_buy"


async def test_cannot_list_card_without_available_copy(clean_db, seed_user, grant_card):
    """Listing the same single-copy card twice must fail the second time.

    This is the loadout-lock cousin from the briefing: a card already in the
    pipeline (locked_quantity) cannot be re-listed if no free copy remains.
    """
    await _seed_one_seller_with_card(seed_user, grant_card)
    await _list_offer()  # locks the one available copy

    with pytest.raises(RebirthPersistenceError) as exc_info:
        await create_market_offer(SELLER_ID, CARD_ID, PRICE, "GOLD", username="race-seller")
    assert exc_info.value.code == "card_not_available"


async def test_concurrent_listing_attempts_only_one_consumes_the_copy(
    clean_db, seed_user, grant_card
):
    """Race 5 list attempts of the same single-copy card. Exactly 1 succeeds.

    Catches a different race than the buy test: if the lock-quantity bump in
    create_market_offer isn't under SERIALIZABLE + FOR UPDATE, two parallel
    listings could each see "1 available" and both lock it.
    """
    await _seed_one_seller_with_card(seed_user, grant_card)

    results = await asyncio.gather(
        *(
            create_market_offer(SELLER_ID, CARD_ID, PRICE + i, "GOLD", username="race-seller")
            for i in range(5)
        ),
        return_exceptions=True,
    )

    successes = [r for r in results if isinstance(r, dict)]
    failures = [r for r in results if isinstance(r, BaseException)]

    assert len(successes) == 1, f"expected exactly 1 listing to win, got {len(successes)}"
    assert len(failures) == 4
    for failure in failures:
        assert isinstance(failure, RebirthPersistenceError)
        assert failure.code in {"card_not_available", "database_write_failed"}


async def test_distinct_offers_for_distinct_card_copies_all_succeed(
    clean_db, seed_user, grant_card
):
    """Sanity check: if the seller has 5 copies, 5 parallel listings all succeed.

    Ensures the lock isn't *too* aggressive — we want it to block double-spends
    of a single copy, not legitimate listings of separate copies.
    """
    await seed_user(SELLER_ID, "race-seller-multi")
    await grant_card(SELLER_ID, CARD_ID, quantity=5)

    results = await asyncio.gather(
        *(
            create_market_offer(SELLER_ID, CARD_ID, PRICE + i, "GOLD", username="race-seller-multi")
            for i in range(5)
        ),
        return_exceptions=True,
    )
    successes = [r for r in results if isinstance(r, dict)]
    assert len(successes) == 5, f"all 5 distinct-copy listings should succeed, got {len(successes)}"
    # All offers must have distinct ids.
    assert len({s["id"] for s in successes}) == 5

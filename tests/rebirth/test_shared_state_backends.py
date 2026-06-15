"""Multi-worker readiness: shared match store + rate limiter backends.

These exercise the Redis backend with fakeredis (no server needed) and the
memory backend with an injected clock, so the sliding-window and TTL logic is
verified deterministically.
"""
import importlib

import pytest

from services.rebirth_contracts import RebirthError
from services import rebirth_redis
from services.rebirth_match_store import RedisMatchStore, RebirthMatchStore, create_match_store
from services.rebirth_rate_limit import (
    MemoryRateLimiter,
    RedisRateLimiter,
    create_rate_limiter,
)

fakeredis = pytest.importorskip("fakeredis")


@pytest.fixture()
def fake_client():
    client = fakeredis.FakeStrictRedis(decode_responses=True)
    yield client
    client.flushall()


@pytest.fixture(autouse=True)
def _reset_redis_cache():
    rebirth_redis.reset_cache()
    yield
    rebirth_redis.reset_cache()


# ---- RedisMatchStore ----

def test_redis_match_store_roundtrip_and_missing(fake_client):
    store = RedisMatchStore(fake_client, ttl_seconds=60)
    store.save({"match_id": "abc123", "owner_user_id": 7, "turn": 3})
    assert store.get("abc123")["turn"] == 3
    assert len(store) == 1
    assert "abc123" in store.raw()
    with pytest.raises(RebirthError) as exc:
        store.get("does-not-exist")
    assert exc.value.code == "missing_match"


def test_redis_match_store_sets_ttl_and_clears(fake_client):
    store = RedisMatchStore(fake_client, ttl_seconds=120, namespace="rbmatch")
    store.save({"match_id": "ttlkey"})
    assert 0 < fake_client.ttl("rbmatch:ttlkey") <= 120
    store.clear()
    assert len(store) == 0


def test_create_match_store_selects_redis_when_configured(monkeypatch, fake_client):
    monkeypatch.setenv("REBIRTH_MATCH_BACKEND", "redis")
    rebirth_redis.set_client(fake_client)
    store = create_match_store()
    assert isinstance(store, RedisMatchStore)


def test_create_match_store_falls_back_to_memory_without_redis(monkeypatch):
    monkeypatch.setenv("REBIRTH_MATCH_BACKEND", "redis")
    monkeypatch.delenv("REBIRTH_REDIS_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    rebirth_redis.set_client(None)
    store = create_match_store()
    assert isinstance(store, RebirthMatchStore)  # graceful fallback


# ---- Rate limiters ----

def _drive(limiter, keys, limit, window):
    return [limiter.hit(keys, limit, window) for _ in range(limit + 1)]


def test_memory_limiter_blocks_after_limit_and_recovers():
    clock = {"t": 1000.0}
    limiter = MemoryRateLimiter(clock=lambda: clock["t"])
    results = _drive(limiter, ("ip:1",), 3, 60)
    assert results == [False, False, False, True]  # 4th attempt blocked
    clock["t"] += 61  # window elapsed
    assert limiter.hit(("ip:1",), 3, 60) is False


def test_redis_limiter_blocks_after_limit_and_recovers(fake_client):
    clock = {"t": 5000.0}
    limiter = RedisRateLimiter(fake_client, namespace="t", clock=lambda: clock["t"])
    results = _drive(limiter, ("ip:1",), 3, 60)
    assert results == [False, False, False, True]
    clock["t"] += 61
    assert limiter.hit(("ip:1",), 3, 60) is False


def test_redis_limiter_isolates_keys(fake_client):
    limiter = RedisRateLimiter(fake_client, namespace="t")
    assert limiter.hit(("a",), 1, 60) is False
    assert limiter.hit(("a",), 1, 60) is True   # 'a' exhausted
    assert limiter.hit(("b",), 1, 60) is False  # 'b' independent


def test_create_rate_limiter_selects_redis(monkeypatch, fake_client):
    monkeypatch.setenv("REBIRTH_RATE_LIMIT_BACKEND", "redis")
    rebirth_redis.set_client(fake_client)
    assert isinstance(create_rate_limiter("x"), RedisRateLimiter)


def test_create_rate_limiter_defaults_to_memory(monkeypatch):
    monkeypatch.delenv("REBIRTH_RATE_LIMIT_BACKEND", raising=False)
    monkeypatch.delenv("REBIRTH_MATCH_BACKEND", raising=False)
    assert isinstance(create_rate_limiter("x"), MemoryRateLimiter)


def test_limiter_disabled_when_limit_nonpositive():
    limiter = MemoryRateLimiter()
    assert limiter.hit(("k",), 0, 60) is False
    assert limiter.hit(("k",), 5, 0) is False

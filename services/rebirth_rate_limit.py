"""Sliding-window rate limiter with a pluggable backend.

The memory backend (default) is correct under a single gunicorn worker. The
Redis backend keeps the window shared across workers — required once the app
scales beyond ``-w 1``. Without it, an attacker simply spreads attempts across
workers and each worker only counts its own slice (the audit flagged that
``AUTH_RATE_LIMITS`` was a per-process dict that also reset on restart).

Backend is selected by ``REBIRTH_RATE_LIMIT_BACKEND`` (falls back to
``REBIRTH_MATCH_BACKEND``, default ``memory``).
"""
from __future__ import annotations

import logging
import os
import threading
import time

from services.rebirth_redis import redis_client_from_env

logger = logging.getLogger(__name__)


class MemoryRateLimiter:
    """Per-process sliding window. Correct for a single worker."""

    backend = "memory"

    def __init__(self, clock=time.time):
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self._clock = clock

    def hit(self, keys, limit, window_seconds) -> bool:
        """Record an attempt against every key; return True if rate-limited.

        When blocked, the attempt is NOT recorded (so a client cannot push its
        own window forward by hammering), mirroring the original behaviour.
        """
        if limit <= 0 or window_seconds <= 0:
            return False
        now = self._clock()
        keys = tuple(keys)
        with self._lock:
            buckets = {
                key: [s for s in self._buckets.get(key, []) if now - s < window_seconds]
                for key in keys
            }
            blocked = any(len(stamps) >= limit for stamps in buckets.values())
            if blocked:
                self._buckets.update(buckets)
            else:
                for key, stamps in buckets.items():
                    stamps.append(now)
                    self._buckets[key] = stamps
            return blocked

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


class RedisRateLimiter:
    """Shared sliding window backed by Redis sorted sets (multi-worker safe)."""

    backend = "redis"

    def __init__(self, client, namespace="rbrl", clock=time.time):
        self._r = client
        self._ns = namespace
        self._clock = clock

    def hit(self, keys, limit, window_seconds) -> bool:
        if limit <= 0 or window_seconds <= 0:
            return False
        now = self._clock()
        keys = tuple(keys)
        floor = now - window_seconds

        pipe = self._r.pipeline()
        for key in keys:
            rk = f"{self._ns}:{key}"
            pipe.zremrangebyscore(rk, 0, floor)
            pipe.zcard(rk)
        counts = pipe.execute()[1::2]
        blocked = any(int(count) >= limit for count in counts)

        if not blocked:
            pipe = self._r.pipeline()
            for key in keys:
                rk = f"{self._ns}:{key}"
                member = f"{now:.6f}:{os.urandom(5).hex()}"
                pipe.zadd(rk, {member: now})
                pipe.expire(rk, int(window_seconds) + 1)
            pipe.execute()
        return blocked

    def reset(self) -> None:
        for key in self._r.scan_iter(match=f"{self._ns}:*"):
            self._r.delete(key)


def create_rate_limiter(namespace="rbrl"):
    """Build the limiter for the configured backend (memory unless redis)."""
    backend = (
        os.environ.get("REBIRTH_RATE_LIMIT_BACKEND")
        or os.environ.get("REBIRTH_MATCH_BACKEND")
        or "memory"
    ).strip().lower()
    if backend == "redis":
        client = redis_client_from_env()
        if client is not None:
            logger.info("rebirth.rate_limit: using shared Redis backend (ns=%s)", namespace)
            return RedisRateLimiter(client, namespace=namespace)
        logger.warning(
            "REBIRTH_RATE_LIMIT_BACKEND=redis but Redis is unavailable; using memory limiter"
        )
    return MemoryRateLimiter()

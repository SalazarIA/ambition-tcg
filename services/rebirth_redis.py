"""Lazy Redis client helper for the optional shared backend (multi-worker).

Redis is an OPTIONAL dependency. The import is lazy so the default in-process
memory backend keeps working when redis-py is not installed. This helper never
raises: it returns ``None`` whenever Redis is unavailable (not configured, not
installed, or unreachable) so every caller can fall back to the memory backend
gracefully instead of crashing the boot.

Configure with ``REBIRTH_REDIS_URL`` (or the conventional ``REDIS_URL``).
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_SENTINEL = object()
_cached = _SENTINEL


def redis_client_from_env(url: str | None = None, *, force: bool = False):
    """Return a connected redis client, or ``None`` if unavailable.

    The result is cached for the process; pass ``force=True`` to rebuild (used
    by tests that inject a fake client via :func:`set_client`).
    """
    global _cached
    if _cached is not _SENTINEL and not force:
        return _cached

    target = url or os.environ.get("REBIRTH_REDIS_URL") or os.environ.get("REDIS_URL")
    if not target:
        _cached = None
        return None

    try:
        import redis  # lazy import — optional dependency
    except Exception:
        logger.warning("rebirth.redis: redis-py not installed; shared backend disabled")
        _cached = None
        return None

    try:
        client = redis.Redis.from_url(
            target, socket_timeout=2, socket_connect_timeout=2, decode_responses=True
        )
        client.ping()
    except Exception as exc:  # connection refused, auth, timeout, DNS…
        logger.warning("rebirth.redis: connection failed (%s); shared backend disabled", exc)
        _cached = None
        return None

    logger.info("rebirth.redis: shared backend connected")
    _cached = client
    return client


def set_client(client) -> None:
    """Inject a client (e.g. fakeredis) and bypass env discovery. For tests."""
    global _cached
    _cached = client


def reset_cache() -> None:
    """Forget the cached client so the next call re-discovers from env."""
    global _cached
    _cached = _SENTINEL

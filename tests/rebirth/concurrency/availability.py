"""Runtime availability checks for PostgreSQL concurrency tests."""

from __future__ import annotations

from typing import Any


try:
    from testcontainers.postgres import PostgresContainer
except Exception as exc:  # pragma: no cover - exercised only when dependency is absent
    PostgresContainer: Any | None = None
    TESTCONTAINERS_IMPORT_ERROR: Exception | None = exc
else:
    TESTCONTAINERS_IMPORT_ERROR = None


def _docker_skip_reason() -> str:
    if TESTCONTAINERS_IMPORT_ERROR is not None:
        return f"testcontainers[postgres] package required: {TESTCONTAINERS_IMPORT_ERROR}"

    try:
        import docker
    except Exception as exc:  # pragma: no cover - depends on local dev environment
        return f"Docker SDK unavailable: {exc}"

    client = None
    try:
        client = docker.from_env(timeout=3)
        client.ping()
    except Exception as exc:  # pragma: no cover - depends on local Docker daemon
        return f"Docker daemon unavailable for PostgreSQL testcontainers: {exc}"
    finally:
        if client is not None:
            close = getattr(client, "close", None)
            if callable(close):
                close()

    return ""


POSTGRES_TESTCONTAINERS_SKIP_REASON = _docker_skip_reason()
POSTGRES_TESTCONTAINERS_AVAILABLE = not POSTGRES_TESTCONTAINERS_SKIP_REASON

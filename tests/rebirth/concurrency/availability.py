"""Runtime availability checks for PostgreSQL concurrency tests.

Two backends are supported, in priority order:

1. **Local binary** — `pg_ctl` / `initdb` / `postgres` on PATH or under a
   well-known Homebrew prefix. Lightweight; no daemon required. Each test
   session spins up a throwaway cluster on a free port.
2. **Docker via testcontainers** — fallback for environments where
   PostgreSQL isn't installed locally but Docker is.

If neither is available the suite skips with a single explicit reason.
"""

from __future__ import annotations

import os
import shutil
from typing import Any, Optional


try:
    from testcontainers.postgres import PostgresContainer
except Exception as exc:  # pragma: no cover - exercised only when dependency is absent
    PostgresContainer: Any | None = None
    TESTCONTAINERS_IMPORT_ERROR: Exception | None = exc
else:
    TESTCONTAINERS_IMPORT_ERROR = None


HOMEBREW_PREFIXES = (
    "/opt/homebrew/opt/postgresql@15/bin",
    "/opt/homebrew/opt/postgresql@16/bin",
    "/opt/homebrew/opt/postgresql/bin",
    "/usr/local/opt/postgresql@15/bin",
    "/usr/local/opt/postgresql@16/bin",
    "/usr/local/opt/postgresql/bin",
)


def find_local_postgres_bin() -> Optional[str]:
    """Return the directory containing pg_ctl/initdb/postgres, or None."""
    override = os.environ.get("REBIRTH_POSTGRES_BIN_DIR")
    candidates = []
    if override:
        candidates.append(override)
    candidates.extend(HOMEBREW_PREFIXES)
    for candidate in candidates:
        if not candidate:
            continue
        if all(
            shutil.which(name, path=candidate) for name in ("pg_ctl", "initdb", "postgres")
        ):
            return candidate
    if all(shutil.which(name) for name in ("pg_ctl", "initdb", "postgres")):
        path_pg_ctl = shutil.which("pg_ctl")
        return os.path.dirname(path_pg_ctl) if path_pg_ctl else None
    return None


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


LOCAL_POSTGRES_BIN_DIR: Optional[str] = find_local_postgres_bin()
LOCAL_POSTGRES_AVAILABLE: bool = LOCAL_POSTGRES_BIN_DIR is not None

DOCKER_SKIP_REASON: str = _docker_skip_reason()
DOCKER_POSTGRES_AVAILABLE: bool = not DOCKER_SKIP_REASON

POSTGRES_TESTCONTAINERS_AVAILABLE: bool = LOCAL_POSTGRES_AVAILABLE or DOCKER_POSTGRES_AVAILABLE


def _build_skip_reason() -> str:
    if POSTGRES_TESTCONTAINERS_AVAILABLE:
        return ""
    return (
        "PostgreSQL unavailable for concurrency tests — install postgresql@15 "
        "via Homebrew (`brew install postgresql@15`) or start Docker. "
        f"Local binary check: not found. Docker check: {DOCKER_SKIP_REASON}"
    )


POSTGRES_TESTCONTAINERS_SKIP_REASON: str = _build_skip_reason()

"""Spawn a throwaway PostgreSQL cluster for concurrency tests.

This is the no-Docker path. We bootstrap a private cluster in a tmp dir,
start `postgres` on a free port, expose the same `start()/stop()/
get_connection_url()` interface that `testcontainers.postgres.PostgresContainer`
provides, and tear it down at session end.

Why a per-session cluster instead of reusing the user's local one:
- Tests need to TRUNCATE arbitrary tables; we don't want to clobber dev data.
- Tests run TestRunUnreplayable migrations; isolation matters.
- Cleanup is a single `rm -rf` of the data dir.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class LocalPostgresCluster:
    """Manages a single-session embedded-style Postgres cluster.

    Mirrors `testcontainers.postgres.PostgresContainer` enough that the
    existing fixture can swap one for the other.
    """

    def __init__(self, *, bin_dir: str, base_dir: Path, database: str = "rebirth_concurrency", username: str = "rebirth_test"):
        self.bin_dir = bin_dir
        self.base_dir = Path(base_dir)
        self.database = database
        self.username = username
        self.port: Optional[int] = None
        self.data_dir: Optional[Path] = None
        self.socket_dir: Optional[Path] = None
        self.process: Optional[subprocess.Popen] = None

    def _bin(self, name: str) -> str:
        return os.path.join(self.bin_dir, name)

    def start(self) -> "LocalPostgresCluster":
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = self.base_dir / "data"
        # Postgres' unix-domain socket path is capped at ~103 bytes on
        # darwin; pytest's tmp paths blow past that. Use a short /tmp dir
        # for the socket, but only as a fallback — we disable unix sockets
        # entirely in the postgres args below and connect via TCP.
        self.socket_dir = None
        pwfile = self.base_dir / "pwfile"
        pwfile.write_text("rebirth-test-password\n", encoding="utf-8")

        env = os.environ.copy()
        env.setdefault("LC_ALL", "en_US.UTF-8")
        env.setdefault("LANG", "en_US.UTF-8")
        subprocess.run(
            [
                self._bin("initdb"),
                "-D", str(self.data_dir),
                "-U", self.username,
                "-A", "trust",
                "--pwfile", str(pwfile),
                "--locale=C",
                "-E", "UTF8",
            ],
            check=True,
            capture_output=True,
            env=env,
        )

        self.port = _pick_free_port()
        log_path = self.base_dir / "postgres.log"
        log_handle = open(log_path, "ab")
        # TCP-only listener. unix_socket_directories='' disables the
        # AF_UNIX socket entirely so the macOS 103-byte path cap doesn't
        # bite us inside pytest's deep tmp dirs.
        self.process = subprocess.Popen(
            [
                self._bin("postgres"),
                "-D", str(self.data_dir),
                "-p", str(self.port),
                "-h", "127.0.0.1",
                "-c", "unix_socket_directories=",
                "-c", "fsync=off",
                "-c", "synchronous_commit=off",
                "-c", "full_page_writes=off",
                "-c", "max_connections=64",
            ],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env=env,
        )

        self._wait_until_ready()
        self._create_database()
        return self

    def _wait_until_ready(self, timeout: float = 20.0) -> None:
        deadline = time.time() + timeout
        last_error: Optional[Exception] = None
        while time.time() < deadline:
            if self.process and self.process.poll() is not None:
                raise RuntimeError(
                    f"postgres exited early with code {self.process.returncode}; "
                    f"see {self.base_dir / 'postgres.log'}"
                )
            try:
                import psycopg
            except ImportError:
                import psycopg2 as psycopg  # type: ignore
            try:
                conn = psycopg.connect(
                    host="127.0.0.1",
                    port=self.port,
                    user=self.username,
                    dbname="postgres",
                    connect_timeout=2,
                )
                conn.close()
                return
            except Exception as exc:
                last_error = exc
                time.sleep(0.2)
        raise RuntimeError(f"local postgres did not come up within {timeout}s: {last_error!r}")

    def _create_database(self) -> None:
        try:
            import psycopg
            conn = psycopg.connect(
                host="127.0.0.1",
                port=self.port,
                user=self.username,
                dbname="postgres",
                autocommit=True,
            )
        except ImportError:
            import psycopg2 as psycopg  # type: ignore
            conn = psycopg.connect(
                host="127.0.0.1",
                port=self.port,
                user=self.username,
                dbname="postgres",
            )
            conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(f'CREATE DATABASE "{self.database}"')
        finally:
            conn.close()

    def get_connection_url(self) -> str:
        if self.port is None:
            raise RuntimeError("cluster not started")
        return f"postgresql://{self.username}@127.0.0.1:{self.port}/{self.database}"

    def stop(self) -> None:
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None
        if self.data_dir is not None and self.data_dir.exists():
            shutil.rmtree(self.data_dir, ignore_errors=True)

"""Fixtures for the Playwright E2E suite.

These tests spawn the real Flask app in a subprocess and drive it with a
headless Chromium. They're slow (browser cold start + page navigation), so
they live behind the `e2e` marker. The default pytest run excludes them;
opt in with `pytest -m e2e`.

The dev server runs against a temporary SQLite DB so tests don't pollute
the dev environment. We pick a free port at fixture setup, set
`REBIRTH_DB_PATH` to a tmp file, and wait for /rebirth to respond before
yielding the base URL.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Iterator

import pytest

# Skip the whole module if Playwright's browser binaries aren't installed.
pytest.importorskip("playwright.sync_api", reason="playwright not installed")
from playwright.sync_api import sync_playwright  # noqa: E402

pytestmark = pytest.mark.e2e

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(url: str, *, timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status < 500:
                    return
        except Exception as exc:  # connection refused, etc.
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"Flask dev server did not come up at {url}: {last_error!r}")


@pytest.fixture(scope="session")
def live_server(tmp_path_factory) -> Iterator[str]:
    """Spawn the Flask app in a subprocess and yield its base URL."""
    port = _pick_free_port()
    db_path = tmp_path_factory.mktemp("rebirth-e2e") / "rebirth-e2e.db"

    env = os.environ.copy()
    env.update(
        {
            "PORT": str(port),
            "REBIRTH_DB_PATH": str(db_path),
            "REBIRTH_REQUIRE_CSRF": "false",
            "SECRET_KEY": "rebirth-e2e-secret",
            # Avoid debug=True (auto-reloader fights pytest)
            "DEBUG_MODE": "false",
            # Make sure the subprocess picks up our project root, not the
            # tmpdir cwd, when importing services.
            "PYTHONPATH": str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
        }
    )

    process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_server(f"{base_url}/rebirth")
    except Exception:
        # Surface server stderr so the failure is debuggable.
        process.terminate()
        try:
            stdout, _ = process.communicate(timeout=2.0)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, _ = process.communicate()
        raise RuntimeError(
            f"dev server failed to start. logs:\n{(stdout or b'').decode(errors='replace')[-2000:]}"
        )

    try:
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@pytest.fixture(
    params=[
        pytest.param({"width": 1280, "height": 720}, id="desktop"),
        pytest.param({"width": 390, "height": 844}, id="mobile"),
    ]
)
def page(live_server, request):
    """Parametrized over desktop + mobile viewports so the same test runs on both.

    Important: `sync_playwright()` is scoped per-test (not session) on
    purpose. Session-scoped Playwright leaves an asyncio event loop bound
    to the main thread for the duration of the session, which then breaks
    *unrelated* legacy tests that call `asyncio.run(...)` later in the
    same pytest invocation. Per-test cleanup avoids the cross-test
    pollution at a cost of ~500ms per test for Chromium cold-start.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            # service_workers="block" prevents the Rebirth PWA's service-worker
            # (pwa.js / sw.js) from registering during tests. Without this, the
            # SW intercepts navigations and triggers a phantom reload mid-test
            # that races the navbar assertions and produces flaky failures.
            context = browser.new_context(
                viewport=request.param,
                service_workers="block",
            )
            page = context.new_page()
            try:
                yield page
            finally:
                context.close()
        finally:
            browser.close()

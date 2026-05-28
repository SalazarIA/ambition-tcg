#!/usr/bin/env python3
"""Capture permanent visual QA screenshots for the active Rebirth surfaces."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = PROJECT_ROOT / "reports" / "qa" / "screenshots"

DESKTOP_VIEWPORT = {"width": 1366, "height": 768}
MOBILE_VIEWPORT = {"width": 390, "height": 844}

VISUAL_STATES = [
    {"name": "arena", "path": "/rebirth", "viewport": DESKTOP_VIEWPORT, "wait": "[data-rebirth-app] .rb-mini-card"},
    {"name": "shop", "path": "/rebirth/shop", "viewport": DESKTOP_VIEWPORT, "wait": ".rb-shop-gacha"},
    {"name": "collection", "path": "/rebirth/collection", "viewport": DESKTOP_VIEWPORT, "wait": ".rb-curated-collection"},
    {"name": "campaign", "path": "/rebirth/campaign", "viewport": DESKTOP_VIEWPORT, "wait": ".rb-campaign-node"},
    {"name": "mobile_arena", "path": "/rebirth", "viewport": MOBILE_VIEWPORT, "wait": "[data-rebirth-app] .rb-mini-card"},
]


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
        handle.bind(("127.0.0.1", 0))
        return int(handle.getsockname()[1])


def wait_for_server(url: str, timeout: float = 25.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status < 500:
                    return
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"Server did not come up at {url}: {last_error!r}")


def start_local_server() -> tuple[str, subprocess.Popen[bytes], tempfile.TemporaryDirectory[str]]:
    temp_dir = tempfile.TemporaryDirectory(prefix="ambition-rebirth-visual-")
    port = pick_free_port()
    env = os.environ.copy()
    env.pop("REBIRTH_DATABASE_URL", None)
    env.pop("DATABASE_URL", None)
    env.update(
        {
            "PORT": str(port),
            "REBIRTH_DB_PATH": str(Path(temp_dir.name) / "rebirth-visual.db"),
            "REBIRTH_ALLOW_SQLITE_TESTING": "true",
            "REBIRTH_REQUIRE_CSRF": "false",
            "SECRET_KEY": "rebirth-visual-qa",
            "DEBUG_MODE": "false",
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
        wait_for_server(f"{base_url}/rebirth")
    except Exception:
        process.terminate()
        try:
            output, _ = process.communicate(timeout=2.0)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()
        temp_dir.cleanup()
        raise RuntimeError(f"Local server failed to start:\n{(output or b'').decode(errors='replace')[-2000:]}")
    return base_url, process, temp_dir


def is_ignored_request_failure(url: str, failure: str) -> bool:
    return "/api/rebirth/telemetry" in url and "ERR_ABORTED" in failure


def capture_state(page, base_url: str, shot_dir: Path, state: dict[str, object], issues: list[str]) -> dict[str, object]:
    name = str(state["name"])
    path = str(state["path"])
    viewport = dict(state["viewport"])
    wait_selector = str(state["wait"])
    page.set_viewport_size(viewport)
    page.goto(base_url.rstrip("/") + path, wait_until="domcontentloaded")
    page.locator(wait_selector).first.wait_for(state="visible", timeout=15000)
    page.wait_for_load_state("networkidle", timeout=15000)
    page.evaluate("() => document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()")

    overflow = page.evaluate(
        """() => ({
            width: window.innerWidth,
            scrollWidth: document.documentElement.scrollWidth,
            bodyScrollWidth: document.body ? document.body.scrollWidth : 0,
        })"""
    )
    if int(overflow["scrollWidth"]) > int(overflow["width"]) + 2:
        issues.append(f"{name}: horizontal overflow {overflow['scrollWidth']} > {overflow['width']}")

    screenshot_path = shot_dir / f"{name}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    return {
        "name": name,
        "path": path,
        "viewport": viewport,
        "screenshot": str(screenshot_path),
        "overflow": overflow,
    }


def run(base_url: str | None, headed: bool, output_dir: str | None) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print(f"RESULT=FAIL rebirth_visual_screenshots missing_playwright {type(exc).__name__}: {exc}")
        return 1

    process = None
    temp_dir = None
    if not base_url:
        base_url, process, temp_dir = start_local_server()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shot_dir = Path(output_dir) if output_dir else REPORT_ROOT / f"rebirth_visual_{stamp}"
    shot_dir.mkdir(parents=True, exist_ok=True)
    report_path = shot_dir / "manifest.json"

    issues: list[str] = []
    captures: list[dict[str, object]] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    failed_requests: list[str] = []
    server_errors: list[str] = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not headed)
            context = browser.new_context(service_workers="block")
            page = context.new_page()
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type in {"error"} else None)
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))

            def on_request_failed(request):
                failure = request.failure or ""
                if not is_ignored_request_failure(request.url, failure):
                    failed_requests.append(f"{request.url} {failure}")

            def on_response(response):
                if response.status >= 500:
                    server_errors.append(f"{response.status} {response.url}")

            page.on("requestfailed", on_request_failed)
            page.on("response", on_response)

            for state in VISUAL_STATES:
                captures.append(capture_state(page, base_url, shot_dir, state, issues))

            context.close()
            browser.close()
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if temp_dir is not None:
            temp_dir.cleanup()

    issues.extend(f"console: {item}" for item in console_errors)
    issues.extend(f"pageerror: {item}" for item in page_errors)
    issues.extend(f"requestfailed: {item}" for item in failed_requests)
    issues.extend(f"server: {item}" for item in server_errors)

    report = {
        "ok": not issues,
        "base_url": base_url,
        "generated_at": stamp,
        "screenshots": captures,
        "issues": issues,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if issues:
        print(f"RESULT=FAIL rebirth_visual_screenshots manifest={report_path}")
        return 1
    print(f"RESULT=PASS rebirth_visual_screenshots manifest={report_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture visual QA screenshots for Rebirth.")
    parser.add_argument("--base-url", default=os.environ.get("REBIRTH_VISUAL_BASE_URL"))
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    return run(args.base_url, headed=args.headed, output_dir=args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())

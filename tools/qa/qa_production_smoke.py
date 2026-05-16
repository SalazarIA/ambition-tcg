#!/usr/bin/env python3
"""Defensive production smoke check for Ambitionz public beta Arena V6."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://ambition-tcg.onrender.com"
EXPECTED_SW = "ambitionz-web-app-v189"
USER_AGENT = "Ambitionz-Production-Smoke/1.0"


@dataclass
class FetchResult:
    path: str
    url: str
    final_url: str
    status: Optional[int]
    content_type: str
    body: str
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status is not None and self.status < 500 and not self.error


def fetch(base_url: str, path: str, timeout: int) -> FetchResult:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )

    try:
        with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            body = response.read().decode("utf-8", errors="ignore")
            return FetchResult(
                path=path,
                url=url,
                final_url=response.geturl(),
                status=response.status,
                content_type=response.headers.get("Content-Type", ""),
                body=body,
            )
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
        return FetchResult(
            path=path,
            url=url,
            final_url=url,
            status=exc.code,
            content_type=exc.headers.get("Content-Type", "") if exc.headers else "",
            body=body,
            error=f"HTTPError: {exc}",
        )
    except URLError as exc:
        return FetchResult(path=path, url=url, final_url=url, status=None, content_type="", body="", error=f"URLError: {exc}")
    except Exception as exc:  # pragma: no cover - defensive production edge
        return FetchResult(path=path, url=url, final_url=url, status=None, content_type="", body="", error=f"{type(exc).__name__}: {exc}")


def fetch_with_retry(base_url: str, path: str, timeout: int, retries: int, sleep_seconds: float) -> FetchResult:
    last = fetch(base_url, path, timeout)
    for attempt in range(retries):
        if last.ok:
            return last
        print(f"retry path={path} attempt={attempt + 1} status={last.status} error={last.error}")
        time.sleep(sleep_seconds)
        last = fetch(base_url, path, timeout)
    return last


def short(result: FetchResult) -> Dict[str, object]:
    return {
        "path": result.path,
        "status": result.status,
        "content_type": result.content_type,
        "final_url": result.final_url,
        "error": result.error,
        "body_preview": result.body[:160].replace("\n", " "),
    }


def assert_contains(body: str, tokens: List[str], warnings: List[str], context: str) -> None:
    for token in tokens:
        if token not in body:
            warnings.append(f"{context}: missing optional token {token!r}")


def run(base_url: str, timeout: int, retries: int) -> int:
    failures: List[str] = []
    warnings: List[str] = []
    results: Dict[str, FetchResult] = {}

    paths = [
        "/health",
        "/training",
        "/service-worker.js",
        "/static/css/arena_clean_v48.css",
        "/static/js/arena_clean_v48.js",
    ]

    print("=== Ambitionz Production Smoke ===")
    print(f"base_url={base_url.rstrip('/')}")

    for path in paths:
        result = fetch_with_retry(base_url, path, timeout=timeout, retries=retries, sleep_seconds=4)
        results[path] = result
        print(f"fetch {path}: {json.dumps(short(result), ensure_ascii=True)}")

    health = results["/health"]
    if not health.ok:
        failures.append(f"/health unreachable: status={health.status} error={health.error}")
    elif "ok" not in health.body.lower() and "status" not in health.body.lower():
        failures.append("/health responded but does not look healthy")

    training = results["/training"]
    if not training.ok:
        failures.append(f"/training unreachable: status={training.status} error={training.error}")
    elif training.final_url.rstrip("/") != training.url.rstrip("/"):
        warnings.append(f"/training redirected to {training.final_url}; protected flow is acceptable for guest smoke")

    training_body = training.body or ""
    if "az48-arena-v6" in training_body or "az48-game-shell" in training_body:
        assert_contains(
            training_body,
            ["arena_clean_v48.css", "arena_clean_v48.js", "az48-compact-hud", "az48-hand-action-shell"],
            warnings,
            "/training HTML",
        )
    else:
        warnings.append("/training HTML did not expose Arena V6 markers; route may be protected or not yet deployed")

    service_worker = results["/service-worker.js"]
    if not service_worker.ok:
        failures.append(f"/service-worker.js unreachable: status={service_worker.status} error={service_worker.error}")
    else:
        if "CACHE_NAME" not in service_worker.body:
            failures.append("service worker missing CACHE_NAME")
        if EXPECTED_SW not in service_worker.body:
            warnings.append(f"service worker does not yet contain {EXPECTED_SW}; production may not have this local hotfix deployed")

    css = results["/static/css/arena_clean_v48.css"]
    js = results["/static/js/arena_clean_v48.js"]
    if not css.ok:
        failures.append(f"arena CSS unreachable: status={css.status} error={css.error}")
    else:
        assert_contains(css.body, ["az48-game-shell", "az48-info-tabs", "az48-hand-action-shell"], warnings, "arena CSS")

    if not js.ok:
        failures.append(f"arena JS unreachable: status={js.status} error={js.error}")
    else:
        assert_contains(js.body, ["arena_command_v1", "az48_play_card", "playCard"], warnings, "arena JS")

    for warning in warnings:
        print(f"WARN: {warning}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print("RESULT=FAIL production_smoke")
        return 1

    print("RESULT=PASS production_smoke")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a defensive Ambitionz production smoke check.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--retries", type=int, default=4)
    args = parser.parse_args()
    return run(args.base_url, timeout=args.timeout, retries=args.retries)


if __name__ == "__main__":
    sys.exit(main())

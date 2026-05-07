
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
import ssl


DEFAULT_BASE_URL = "https://ambitionzgame.com"


def _fetch(url, timeout=20):
    request = Request(
        url,
        headers={
            "User-Agent": "Ambitionz-QA-Agent/1.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )

    try:
        with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            body = response.read().decode("utf-8", errors="ignore")
            return {
                "url": url,
                "status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "body": body,
                "error": None,
            }
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
        return {
            "url": url,
            "status": exc.code,
            "content_type": exc.headers.get("Content-Type") if exc.headers else None,
            "body": body,
            "error": f"HTTPError: {exc}",
        }
    except URLError as exc:
        return {
            "url": url,
            "status": None,
            "content_type": None,
            "body": "",
            "error": f"URLError: {exc}",
        }
    except Exception as exc:
        return {
            "url": url,
            "status": None,
            "content_type": None,
            "body": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _short(result):
    return {
        "url": result.get("url"),
        "status": result.get("status"),
        "content_type": result.get("content_type"),
        "error": result.get("error"),
        "body_preview": (result.get("body") or "")[:180].replace("\n", " "),
    }


def run_production_flow(base_url=DEFAULT_BASE_URL):
    logs = []
    failures = []

    base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")

    logs.append(f"base_url={base_url}")

    paths = [
        "/health",
        "/",
        "/login",
        "/register",
        "/training",
        "/static/js/arena_clean_v48.js",
        "/static/css/arena_clean_v48.css",
        "/static/js/pwa.js",
        "/static/manifest.webmanifest",
    ]

    results = {}

    for path in paths:
        url = urljoin(base_url + "/", path.lstrip("/"))
        result = _fetch(url)
        results[path] = result
        logs.append(f"fetch {path}: {_short(result)}")

        status = result.get("status")

        if status is None:
            failures.append(f"{path}: no response: {result.get('error')}")
            continue

        if path in ["/health", "/", "/login", "/register"]:
            if status >= 400:
                failures.append(f"{path}: expected public success, got {status}")

        if path == "/training":
            if status not in (200, 302, 401, 403):
                failures.append(f"{path}: expected protected status/redirect, got {status}")

        if path.startswith("/static/"):
            if status >= 400:
                failures.append(f"{path}: static asset failed with {status}")

    health_body = results.get("/health", {}).get("body") or ""
    if "ok" not in health_body.lower() and "status" not in health_body.lower():
        failures.append("/health does not look healthy")

    home_body = results.get("/", {}).get("body") or ""
    login_body = results.get("/login", {}).get("body") or ""
    arena_js = results.get("/static/js/arena_clean_v48.js", {}).get("body") or ""
    pwa_js = results.get("/static/js/pwa.js", {}).get("body") or ""

    if "Ambitionz" not in (home_body + login_body):
        failures.append("Home/login does not contain Ambitionz branding")

    if "az48_play_card" not in arena_js:
        failures.append("production arena_clean_v48.js missing az48_play_card")

    if "play_to_field" in arena_js:
        failures.append("production arena_clean_v48.js still contains legacy play_to_field")

    if "card_id: id" not in arena_js and "card_id:id" not in arena_js.replace(" ", ""):
        failures.append("production arena_clean_v48.js may not send card_id from id")

    if "PWA_FORCE_UPDATE_V1" not in pwa_js:
        failures.append("production pwa.js missing PWA_FORCE_UPDATE_V1 marker")

    # Try to infer arena cache version from training/login HTML if available.
    combined_html = "\n".join([
        results.get("/", {}).get("body") or "",
        results.get("/training", {}).get("body") or "",
        results.get("/login", {}).get("body") or "",
    ])

    if "arena_clean_v48.js" in combined_html and "?v=59" not in combined_html:
        failures.append("production HTML references arena_clean_v48.js but not cache bust v59")

    status = "FAIL" if failures else "PASS"

    return {
        "name": "production_smoke_cache_flow",
        "status": status,
        "error": "; ".join(failures) if failures else None,
        "logs": logs,
    }

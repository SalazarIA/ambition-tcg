
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def summarize_response(path, response):
    return {
        "path": path,
        "status": response.status_code,
        "content_type": response.content_type,
        "location": response.headers.get("Location"),
    }


def run_routes_flow():
    logs = []

    try:
        from app import app

        client = app.test_client()

        public_paths = [
            "/",
            "/health",
            "/login",
            "/register",
            "/forgot-password",
            "/terms",
            "/privacy",
            "/offline",
        ]

        protected_paths = [
            "/training",
            "/arena",
            "/profile",
            "/deck-builder",
            "/collection",
            "/inventory",
            "/shop",
            "/economy/premium-ledger",
        ]

        static_paths = [
            "/static/js/arena_clean_v48.js",
            "/static/css/arena_clean_v48.css",
            "/static/js/pwa.js",
            "/static/manifest.webmanifest",
            "/static/icons/icon.svg",
        ]

        failures = []

        logs.append("## Public Routes")
        for path in public_paths:
            response = client.get(path)
            item = summarize_response(path, response)
            logs.append(str(item))

            if response.status_code >= 500:
                failures.append(f"Public route 500: {path}")

        logs.append("")
        logs.append("## Protected Routes")
        for path in protected_paths:
            response = client.get(path)
            item = summarize_response(path, response)
            logs.append(str(item))

            if response.status_code >= 500:
                failures.append(f"Protected route 500: {path}")

            if response.status_code not in (200, 302, 401, 403):
                failures.append(f"Unexpected protected status {response.status_code}: {path}")

        logs.append("")
        logs.append("## Static Assets")
        for path in static_paths:
            response = client.get(path)
            item = summarize_response(path, response)
            logs.append(str(item))

            if response.status_code >= 400:
                failures.append(f"Static asset failed {response.status_code}: {path}")

        logs.append("")
        logs.append("## Arena Template Contract")
        arena_html = client.get("/training", follow_redirects=False)
        logs.append(str(summarize_response("/training", arena_html)))

        # Protected route should redirect when unauthenticated.
        if arena_html.status_code not in (302, 401, 403):
            failures.append("/training should not be public without auth")

        status = "FAIL" if failures else "PASS"

        return {
            "name": "routes_auth_static_flow",
            "status": status,
            "error": "; ".join(failures) if failures else None,
            "logs": logs,
        }

    except Exception as exc:
        return {
            "name": "routes_auth_static_flow",
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "logs": logs,
        }

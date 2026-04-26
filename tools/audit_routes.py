from pathlib import Path
import re


CRITICAL_ROUTES = [
    "/",
    "/health",
    "/login",
    "/register",
    "/resend-verification",
    "/forgot-password",
    "/how-to-play",
    "/ranking",
    "/terms",
    "/privacy",
    "/training",
    "/arena",
    "/collection",
    "/deck-builder",
    "/shop",
    "/admin",
    "/admin/dev-tools",
    "/admin/system",
    "/admin/users",
]


def audit_routes(app):
    errors = []

    with app.test_client() as client:
        for route in CRITICAL_ROUTES:
            try:
                response = client.get(route, follow_redirects=False)
                status = response.status_code

                if status >= 500:
                    errors.append(f"{route} returned {status}")

                print(f"ROUTE {route}: {status} {response.headers.get('Location') or ''}")
            except Exception as error:
                errors.append(f"{route} crashed: {type(error).__name__}: {error}")

    return errors


def audit_template_endpoints(app):
    errors = []
    registered = set(app.view_functions.keys())
    called = set()

    pattern = re.compile(r"url_for\(\s*['\"]([^'\"]+)['\"]")

    for template in Path("templates").glob("*.html"):
        text = template.read_text(encoding="utf-8")

        for match in pattern.findall(text):
            if not match.startswith("static"):
                called.add(match)

    missing = sorted(called - registered)

    print("REGISTERED ENDPOINTS:", len(registered))
    print("CALLED ENDPOINTS:", sorted(called))
    print("MISSING ENDPOINTS:", missing)

    if missing:
        errors.append(f"Missing template endpoints: {missing}")

    return errors

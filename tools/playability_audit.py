from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app

PUBLIC_OK = {
    "/health": [200],
    "/": [200],
    "/tutorial": [200],
    "/campaign": [200],
    "/daily": [200, 302],
    "/training": [200, 302],
    "/arena": [200, 302],
    "/collection": [200, 302],
    "/deck-builder": [200, 302],
    "/shop": [200, 302],
    "/leaderboard": [200],
    "/ranking": [200],
    "/missions": [200, 302],
    "/progression": [200, 302],
    "/profile": [200, 302],
    "/match-history": [200, 302],
    "/manifest.webmanifest": [200],
    "/service-worker.js": [200],
    "/static/css/arena_clean_v48.css": [200],
    "/static/css/arena3d.css": [200],
    "/static/css/ambitionz_tutorial.css": [200],
    "/static/js/arena_renderer_adapter.js": [200],
    "/static/js/arena_clean_v48.js": [200],
    "/static/js/arena_sound.js": [200],
    "/static/dist/arena3d/arena3d.js": [200],
    "/static/js/ambitionz_tutorial.js": [200],
}

def run():
    client = app.test_client()
    failed = False

    print("# Ambitionz Playability Audit")
    print()

    for path, expected in PUBLIC_OK.items():
        r = client.get(path)
        ok = r.status_code in expected
        print(f"{'OK' if ok else 'FAIL'} {path:42s} {r.status_code:3d} {r.content_type}")

        if not ok:
            failed = True

    payload = {
        "event_key": "playability_audit",
        "page": "/tools/playability_audit.py",
        "metadata": {"source": "audit"}
    }

    r = client.post("/api/retention/event", json=payload)
    ok = r.status_code == 200
    print(f"{'OK' if ok else 'FAIL'} {'/api/retention/event':42s} {r.status_code:3d} {r.content_type}")

    if not ok:
        failed = True

    visual_contracts = [
        (
            "arena_command_v1_js",
            PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js",
            "arena_command_v1",
        ),
        (
            "lane_selection_js",
            PROJECT_ROOT / "static" / "js" / "arena_clean_v48.js",
            "data-az48-lane",
        ),
        (
            "target_selection_template",
            PROJECT_ROOT / "templates" / "arena.html",
            'data-az48-target="enemy_hero"',
        ),
        (
            "lane_selection_css",
            PROJECT_ROOT / "static" / "css" / "arena_clean_v48.css",
            ".az48-selecting-lane",
        ),
        (
            "keyword_registry_adapter",
            PROJECT_ROOT / "static" / "js" / "arena_renderer_adapter.js",
            "keywordRegistry",
        ),
    ]

    for label, path, needle in visual_contracts:
        body = path.read_text(errors="ignore")
        ok = needle in body
        print(f"{'OK' if ok else 'FAIL'} {label:42s} {'contract':>3s} {path.relative_to(PROJECT_ROOT)}")
        if not ok:
            failed = True

    if failed:
        raise SystemExit(1)

    print()
    print("PLAYABILITY AUDIT PASSED")

if __name__ == "__main__":
    run()

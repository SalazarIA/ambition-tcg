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
    "/static/css/arena_v7.css": [200],
    "/static/css/arena_animations.css": [200],
    "/static/css/ambitionz_tutorial.css": [200],
    "/static/js/arena_v7.js": [200],
    "/static/js/arena_animations.js": [200],
    "/static/js/ambitionz_tutorial.js": [200],
    "/static/js/game.js": [200],
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

    if failed:
        raise SystemExit(1)

    print()
    print("PLAYABILITY AUDIT PASSED")

if __name__ == "__main__":
    run()

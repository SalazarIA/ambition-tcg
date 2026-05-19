#!/usr/bin/env python3
import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{Path(tempfile.gettempdir()) / 'ambition_ascension_surface_qa.db'}")
os.environ.setdefault("SECRET_KEY", "qa-secret-key")
os.environ.setdefault("WTF_CSRF_ENABLED", "false")
os.environ.setdefault("ENVIRONMENT", "testing")

from app import app  # noqa: E402


ROUTES = {
    "/": ["Ambitionz", "Ascension Duel", "Champion progression"],
    "/training": ["Ascension Duel", "Duel Altar", "Ambition Core"],
    "/collection-ascension": ["Ascension Collection", "Champion", "Technique"],
    "/deck-builder-ascension": ["Ascension Deck", "Champion", "Technique"],
    "/ascension-history": ["Ascension Chronicle", "Duel Altar"],
    "/roadmap": ["Roadmap & Patch Notes", "Ascension Duel", "no real-money payments"],
    "/tutorial": ["First Oath", "Ascension Duel", "Commit"],
}

OLD_PUBLIC_LABELS = ["monster", "spell", "trap", "lane"]


def main():
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()

    for path, required in ROUTES.items():
        response = client.get(path)
        body = response.get_data(as_text=True)
        lower = body.lower()
        assert response.status_code == 200, f"{path} returned {response.status_code}"
        for token in required:
            assert token in body, f"{path} missing {token}"
        if path == "/":
            assert "az-rebirth-bridge" in body, "/ missing Rebirth bridge"
            assert "Legacy Arena" in body, "/ missing explicit legacy fallback label"
        else:
            assert "/training-legacy" not in body, f"{path} exposes legacy as public route"
            assert "Legacy Arena" not in body, f"{path} presents legacy as product"
        for label in OLD_PUBLIC_LABELS:
            assert label not in lower, f"{path} exposes old label {label}"

    print("PASS ascension_product_surface")


if __name__ == "__main__":
    main()

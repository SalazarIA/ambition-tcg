#!/usr/bin/env python3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main():
    template = (PROJECT_ROOT / "templates" / "arena_ascension.html").read_text()
    css = (PROJECT_ROOT / "static" / "css" / "ambitionz_ascension.css").read_text()
    js = (PROJECT_ROOT / "static" / "js" / "ambitionz_ascension.js").read_text()
    service_worker = (PROJECT_ROOT / "static" / "js" / "service-worker.js").read_text()
    combined = "\n".join([template, css, js]).lower()

    for token in ["ax-duel-altar", "ax-ambition-core", "ax-intent-ring", "ax-chronicle", "ax-commit-button"]:
        assert token in template or token in css or token in js

    assert "lane" not in combined
    assert "az48" not in combined
    assert "arena_clean_v48" not in template
    assert 'CACHE_NAME = "ambitionz-web-app-v194"' in service_worker
    assert "/static/css/ambitionz_ascension.css" in service_worker
    assert "/static/js/ambitionz_ascension.js" in service_worker
    print("PASS ascension_frontend_contract")


if __name__ == "__main__":
    main()

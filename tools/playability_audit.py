#!/usr/bin/env python3
"""Ambitionz Rebirth — Playability smoke audit (reescrito sobre rebirth_*).

A versão anterior checava a arena ANTIGA (arena_clean_v48.*, arena_sound.js,
/api/retention/event, style.css) — assets/rotas que não existem mais — e por isso
falhava/crashava por engano. Esta versão valida as superfícies e assets reais do
produto atual (rebirth_*). Sem dependências de módulos removidos.

Uso: python tools/playability_audit.py   (exit 0 = OK, 1 = falha)
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app

# Rotas do produto atual. 200 = pública; {200,302} = pode redirecionar
# (visitante / gate de login).
ROUTES = {
    "/": [200],
    "/rebirth": [200],
    "/rebirth/shop": [200],
    "/rebirth/collection": [200],
    "/rebirth/deck-builder": [200],
    "/rebirth/campaign": [200],
    "/rebirth/profile": [200],
    "/rebirth/progression": [200],
    "/service-worker.js": [200],
    "/manifest.webmanifest": [200],
}

# Assets reais que precisam existir no disco (cache-busted em runtime).
ASSETS = [
    "static/css/rebirth.css",
    "static/js/rebirth.js",
    "static/js/service-worker.js",
    "static/js/rebirth_product.js",
]

# Marcadores que a arena precisa renderizar (contrato leve de UI).
ARENA_MARKERS = [
    'id="rebirth-board"',
    'id="rebirth-avatar-overlay"',   # seletor de foto de perfil (P1.3)
    "rebirth.js",
]


def run() -> int:
    client = app.test_client()
    failed = False
    print("# Ambitionz Rebirth — Playability Audit\n")

    print("## Rotas")
    for path, expected in ROUTES.items():
        status = client.get(path).status_code
        ok = status in expected
        failed = failed or not ok
        print(f"{'OK  ' if ok else 'FAIL'} {path:28s} {status} (esperado {expected})")

    print("\n## Assets no disco")
    for rel in ASSETS:
        exists = (PROJECT_ROOT / rel).is_file()
        failed = failed or not exists
        print(f"{'OK  ' if exists else 'FAIL'} {rel}")

    print("\n## Contrato leve da arena (/rebirth)")
    body = client.get("/rebirth").get_data(as_text=True)
    for marker in ARENA_MARKERS:
        present = marker in body
        failed = failed or not present
        print(f"{'OK  ' if present else 'FAIL'} contém {marker!r}")

    print()
    if failed:
        print("RESULT=FAIL playability_audit")
        return 1
    print("RESULT=PASS playability_audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

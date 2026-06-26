#!/usr/bin/env python3
"""Fecha a temporada — GATILHO MANUAL (não roda sozinho; você executa).

Concede recompensa por faixa de ELO, soft-reseta o ELO (1500 + (elo-1500)//2) e
bumpa ranking_season. Idempotente por (usuário, season). Sem --confirm é dry-run.

Uso:
    DATABASE_URL=... python tools/ops/rebirth_season_reset.py            # dry-run
    DATABASE_URL=... python tools/ops/rebirth_season_reset.py --confirm  # aplica
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from services.rebirth_persistence import RebirthRepository  # noqa: E402


def _repo() -> RebirthRepository:
    url = os.environ.get("REBIRTH_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if url:
        return RebirthRepository(database_url=url)
    db_path = os.environ.get("REBIRTH_DB_PATH") or str(PROJECT_ROOT / "instance" / "database.db")
    return RebirthRepository(db_path=db_path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Fecha a temporada (recompensa + soft-reset + bump).")
    ap.add_argument("--confirm", action="store_true", help="Aplica de verdade (escreve no DB). Sem isso, é dry-run.")
    args = ap.parse_args()

    repo = _repo()
    repo.ensure_schema()
    tiers = {name: {"min_elo": floor, "gold": gold, "dust": dust} for floor, name, gold, dust in repo.SEASON_TIERS}
    print("Faixas de recompensa:", tiers)
    print("Soft-reset: novo_elo = 1500 + (elo - 1500) // 2")

    if not args.confirm:
        print("\nDRY-RUN — nada foi alterado. Rode com --confirm para conceder recompensas e resetar o ELO.")
        return 0

    summary = repo.close_season()
    print("\nSEASON FECHADA:", summary)
    print("RESULT=PASS rebirth_season_reset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Camada de dados self-hosted (Fase 0.2): lê telemetry_events do DB e produz
funil de 1ª sessão + balance de PRODUÇÃO + sinais de legibilidade/onboarding.

Custo zero, sem segredo, sem serviço externo. Funciona com SQLite (dev/teste) e
Postgres (produção) — pega a URL de REBIRTH_DATABASE_URL/DATABASE_URL ou cai no
SQLite local. Reusa services.rebirth_funnel.build_report (que já existia, mas só
lia de um export JSON — esta ferramenta conecta a lógica ao DB real).

Uso:
    python tools/ops/rebirth_metrics_report.py            # imprime resumo
    python tools/ops/rebirth_metrics_report.py --json out.json --html dash.html
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, text  # noqa: E402
from services.rebirth_schema import normalize_database_url  # noqa: E402
from services.rebirth_funnel import build_report  # noqa: E402


def resolve_db_url() -> str:
    raw = os.environ.get("REBIRTH_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if raw:
        return normalize_database_url(raw)
    path = os.environ.get("REBIRTH_DB_PATH") or str(PROJECT_ROOT / "instance" / "database.db")
    return f"sqlite:///{path}"


def load_events(url: str) -> list[dict]:
    engine = create_engine(url, future=True)
    events: list[dict] = []
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT user_id, event_type, event_json, created_at FROM telemetry_events ORDER BY created_at")
        ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row.event_json)
        except Exception:
            payload = {}
        created = row.created_at
        events.append({
            "user_id": str(row.user_id) if row.user_id is not None else None,
            "event_type": row.event_type,
            "created_at": created.isoformat() if hasattr(created, "isoformat") else str(created),
            "payload": payload if isinstance(payload, dict) else {},
        })
    return events


def _winrate(finished: list[dict], key: str) -> dict:
    groups: dict = defaultdict(lambda: {"matches": 0, "player_wins": 0})
    for p in finished:
        g = groups[p.get(key) or "?"]
        g["matches"] += 1
        if p.get("winner") == "player":
            g["player_wins"] += 1
    return {
        k: {"matches": v["matches"],
            "player_winrate": round(v["player_wins"] / v["matches"], 3) if v["matches"] else 0.0}
        for k, v in sorted(groups.items(), key=lambda kv: -kv[1]["matches"])
    }


def production_balance(events: list[dict]) -> dict:
    finished = [e["payload"] for e in events
                if e["event_type"] == "match_finished" or e["payload"].get("is_finished")]
    chains = [int(p.get("max_chain_length") or 0) for p in finished]
    chains_sorted = sorted(chains)
    turns = [int(p.get("turn") or 0) for p in finished if p.get("turn")]
    first_duels = [p for p in finished if p.get("first_duel")]
    return {
        "matches_finished": len(finished),
        "winrate_by_difficulty": _winrate(finished, "bot_difficulty_id"),
        "winrate_by_profile": _winrate(finished, "bot_profile_id"),
        "winrate_by_cohort": _winrate(finished, "cohort"),
        "avg_turns": round(sum(turns) / len(turns), 2) if turns else 0,
        "chain_readability": {
            "avg_max_chain": round(sum(chains) / len(chains), 2) if chains else 0,
            "p95_max_chain": chains_sorted[int(len(chains_sorted) * 0.95)] if chains_sorted else 0,
            "risk": bool(chains_sorted and chains_sorted[int(len(chains_sorted) * 0.95)] >= 8),
        },
        "onboarding": {
            "first_duels_finished": len(first_duels),
            "first_duel_player_winrate": round(
                sum(1 for p in first_duels if p.get("winner") == "player") / len(first_duels), 3
            ) if first_duels else 0.0,
        },
    }


def render_html(report: dict) -> str:
    def tbl(d: dict) -> str:
        if not d:
            return "<p>sem dados</p>"
        rows = "".join(
            f"<tr><td>{k}</td><td>{v['matches']}</td><td>{v['player_winrate']:.1%}</td></tr>"
            for k, v in d.items()
        )
        return f"<table><tr><th>grupo</th><th>partidas</th><th>winrate jogador</th></tr>{rows}</table>"
    b = report["production_balance"]
    f = report["funnel"].get("funnel", {})
    return f"""<!doctype html><meta charset=utf-8><title>Rebirth — Métricas</title>
<style>body{{font:14px system-ui;background:#0b0a09;color:#e8d4a4;padding:24px}}
h1{{color:#f4ad26}}table{{border-collapse:collapse;margin:8px 0 20px}}td,th{{border:1px solid #54421f;padding:6px 12px;text-align:left}}
.kpi{{display:inline-block;margin:0 24px 16px 0}}.kpi b{{display:block;font-size:24px;color:#fff}}</style>
<h1>Rebirth — Métricas (telemetria de produção)</h1>
<div class=kpi><b>{f.get('matches_started',0)}</b>partidas iniciadas</div>
<div class=kpi><b>{f.get('match_completion_rate',0):.0%}</b>taxa de conclusão</div>
<div class=kpi><b>{f.get('first_match_completion_rate',0):.0%}</b>conclusão 1ª sessão</div>
<div class=kpi><b>{b['matches_finished']}</b>partidas finalizadas</div>
<div class=kpi><b>{b['avg_turns']}</b>turnos/partida</div>
<h2>Balance por dificuldade</h2>{tbl(b['winrate_by_difficulty'])}
<h2>Balance por perfil do bot</h2>{tbl(b['winrate_by_profile'])}
<h2>Balance por coorte</h2>{tbl(b['winrate_by_cohort'])}
<h2>Legibilidade de chain</h2><p>média {b['chain_readability']['avg_max_chain']} · p95 {b['chain_readability']['p95_max_chain']} · risco: {'SIM' if b['chain_readability']['risk'] else 'não'}</p>
<h2>Onboarding (1º duelo)</h2><p>{b['onboarding']['first_duels_finished']} finalizados · winrate {b['onboarding']['first_duel_player_winrate']:.0%}</p>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Rebirth — relatório de métricas (funil + balance de produção)")
    ap.add_argument("--json", help="grava o relatório JSON aqui")
    ap.add_argument("--html", help="grava um dashboard HTML aqui")
    args = ap.parse_args()

    url = resolve_db_url()
    try:
        events = load_events(url)
    except Exception as exc:
        print(f"RESULT=FAIL rebirth_metrics_report db_error {type(exc).__name__}: {exc}")
        return 1

    report = {
        "db": url.split("@")[-1],  # esconde credenciais
        "events_total": len(events),
        "funnel": build_report(events),
        "production_balance": production_balance(events),
    }
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"json -> {args.json}")
    if args.html:
        Path(args.html).write_text(render_html(report), encoding="utf-8")
        print(f"html -> {args.html}")
    f = report["funnel"].get("funnel", {}); b = report["production_balance"]
    print(f"eventos={report['events_total']} | iniciadas={f.get('matches_started',0)} "
          f"conclusão={f.get('match_completion_rate',0):.0%} | finalizadas={b['matches_finished']} "
          f"avg_turns={b['avg_turns']} chain_p95={b['chain_readability']['p95_max_chain']}")
    print("RESULT=PASS rebirth_metrics_report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

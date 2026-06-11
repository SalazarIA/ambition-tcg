"""Orçamentos de performance (estudo v103) — regressão barra travada.

Metodologia de estúdio: cada métrica tem um budget e o CI reprova quem o
estourar. Tempos têm margem 4-6x sobre o baseline (CI compartilhada flutua);
tamanhos são determinísticos e apertados. Baseline 2026-06-11 (dev local):
start 2.1ms · play 0.12ms · attack 1.2ms · next_turn 2.4ms p50;
estado público ~24KB p50 / ~4KB gzip no fio.
"""
import gzip
import json
from time import perf_counter

from services.rebirth_balance import card_cost
from services.rebirth_cards import is_monster
from services.rebirth_contracts import RebirthError
from services.rebirth_engine import declare_attack, next_turn, play_card, start_match
from services.rebirth_serializers import public_state


def _play_turns(match, turns=10):
    for _ in range(turns):
        if match.get("is_finished"):
            break
        for _ in range(3):
            ready = next(
                (
                    card
                    for card in match["player"]["battlefield"]
                    if not card.get("exhausted")
                    and not card.get("has_attacked")
                    and not card.get("has_acted")
                    and not (card.get("just_summoned") and "RUSH" not in (card.get("keywords") or []))
                ),
                None,
            )
            if not ready or match.get("is_finished"):
                break
            enemy = next(iter(match["bot"].get("battlefield", []) or []), None)
            try:
                declare_attack(
                    match,
                    attacker_instance_id=ready["instance_id"],
                    target_instance_id=(enemy or {}).get("instance_id"),
                )
            except RebirthError:
                break
        if match.get("is_finished"):
            break
        for _ in range(2):
            energy = int(match["player"].get("energy", 0) or 0)
            card = next(
                (c for c in match["player"]["hand"] if is_monster(c) and card_cost(c) <= energy),
                None,
            )
            if not card or len(match["player"]["battlefield"]) >= 3:
                break
            try:
                play_card(match, card_instance_id=card["instance_id"])
            except RebirthError:
                break
        if match.get("is_finished"):
            break
        next_turn(match)
    return match


def test_v103_engine_command_latency_budget():
    samples = {"next_turn": [], "attack": []}
    for index in range(6):
        match = start_match(seed=f"budget-{index}", bot_profile_id="defensive")
        for _ in range(8):
            if match.get("is_finished"):
                break
            ready = next(
                (
                    card
                    for card in match["player"]["battlefield"]
                    if not card.get("exhausted") and not card.get("has_acted") and not card.get("just_summoned")
                ),
                None,
            )
            if ready:
                enemy = next(iter(match["bot"].get("battlefield", []) or []), None)
                started = perf_counter()
                try:
                    declare_attack(
                        match,
                        attacker_instance_id=ready["instance_id"],
                        target_instance_id=(enemy or {}).get("instance_id"),
                    )
                except RebirthError:
                    pass
                samples["attack"].append((perf_counter() - started) * 1000)
            energy = int(match["player"].get("energy", 0) or 0)
            card = next(
                (c for c in match["player"]["hand"] if is_monster(c) and card_cost(c) <= energy),
                None,
            )
            if card and len(match["player"]["battlefield"]) < 3:
                play_card(match, card_instance_id=card["instance_id"])
            if match.get("is_finished"):
                break
            started = perf_counter()
            next_turn(match)
            samples["next_turn"].append((perf_counter() - started) * 1000)

    def p95(values):
        ordered = sorted(values)
        return ordered[max(0, int(round(0.95 * (len(ordered) - 1))))] if ordered else 0.0

    # Budgets com folga 5x+ sobre baseline; estourar isso = regressão real.
    assert p95(samples["attack"]) < 25.0, samples["attack"]
    assert p95(samples["next_turn"]) < 40.0, samples["next_turn"]


def test_v103_public_state_size_budget_and_shape():
    match = _play_turns(start_match(seed="budget-size", bot_profile_id="defensive"))
    state = public_state(match)
    blob = json.dumps(state, ensure_ascii=False).encode("utf-8")

    # JSON cru e no fio (gzip nível do flask-compress) com teto.
    assert len(blob) / 1024 < 40.0, f"estado público {len(blob)/1024:.1f}KB"
    assert len(gzip.compress(blob, 6)) / 1024 < 10.0

    # Shape do emagrecimento: uma única cópia dos slots viaja, e eventos
    # públicos não embutem cartas inteiras (o replay usa as tabelas).
    assert "field" not in state["player"] and "field" not in state["bot"]
    assert state["player_field"] is not None and state["bot_field"] is not None
    for event in state["events"]:
        payload = event.get("payload") or {}
        assert "card" not in payload and "cards" not in payload, event.get("event_type") or event.get("type")


def test_v103_api_responses_are_gzip_compressed(client):
    response = client.post(
        "/api/rebirth/start",
        json={"seed": "budget-gzip"},
        headers={"Accept-Encoding": "gzip"},
    )
    assert response.status_code == 200
    assert response.headers.get("Content-Encoding") == "gzip"
    assert "Server-Timing" in response.headers

"""Contrato de saúde do jogador CASUAL (auditoria olhos-de-jogador 2026-06-11).

O lab tático sempre reportou WR saudável porque joga otimizado; a experiência
real era 0.175 de WR com o bot deletando o board do jogador todo turno. Este
teste trava as garantias para quem joga "normal": monstros na ordem da mão,
magia quando o botão acende, ataque no alvo óbvio.
"""

from services.rebirth_balance import simulate_casual_balance


def test_v102_casual_player_wins_and_keeps_a_board():
    payload = simulate_casual_balance(60, seed_prefix="casual-ci")
    summary = payload["summary"]

    # Quem joga casual vence a maioria dos duelos de arena (retenção) sem o
    # jogo virar vitória automática.
    assert 0.5 <= summary["player_win_rate"] <= 0.9, summary
    # O board do jogador EXISTE: média de unidades vivas ao fim dos turnos
    # dele. Antes da política de clemência/pressão isso era ~1.3 com o bot
    # removendo 1 por turno.
    assert summary["board_presence"] >= 1.5, summary
    assert summary["unfinished_rate"] <= 0.1, summary
    assert summary["average_turns"] <= 22, summary


def test_v102_every_profile_is_beatable_by_casual_play():
    payload = simulate_casual_balance(60, seed_prefix="casual-profiles-ci")
    rates = {profile["profile_id"]: profile["player_win_rate"] for profile in payload["profile_results"]}

    for profile_id, rate in rates.items():
        assert rate >= 0.35, f"{profile_id} voltou a ser muro para jogador casual: {rates}"

# Rebirth — Relatório de Segurança Adversarial (Top10 #2)

Data: 2026-06-15 · Evidência: `tests/rebirth/test_adversarial_security.py` (8 testes, verdes)

Objetivo (Codex Fase 0): **provar** que não há P0 explorável escondido antes de
ampliar o beta — autorização de match, abuso de payload e idempotência de
economia — dirigindo a superfície HTTP real como um segundo ator hostil.

## Resultado: nenhum P0 explorável encontrado

A superfície já estava defendida estruturalmente; esta suíte transforma a
defesa em contrato testado (antes só havia `test_v74_guest_match_uniqueness`).

| # | Vetor testado | Resultado | Defesa no código |
|---|---|---|---|
| 1 | Usuário B age (play/attack) no match de A | **Bloqueado** 403 `match_forbidden` | `ensure_match_access` em todas as rotas mutantes |
| 2 | Usuário B lê eventos/histórico do match de A | **Sem vazamento** (`missing_match`) | leituras escopadas por `user_id` |
| 3 | Convidado B retoma o match de outro convidado | **Bloqueado** 403 `match_forbidden` | `resume` valida `match_id` da sessão |
| 4 | Mutação sem/!= token CSRF (quando habilitado) | **Bloqueado** 403 `csrf_required` | `protect_rebirth_mutations` |
| 5 | Payload com campo inesperado (`winner`) | **Rejeitado** 400 `unexpected_combat_fields` | allowlist `COMBAT_PAYLOAD_ALLOWED_FIELDS` |
| 6 | Payload com estado autoritativo (`has_attacked`) | **Rejeitado** 400 | `reject_authoritative_combat_fields` |
| 7 | Daily reward sem clash | **Bloqueado** 409 `reward_locked` | `claim_daily_reward` |
| 8 | Daily reward resgatado 2× | **Sem grant duplo** 409 `transaction_replayed` | idempotência de economia |

## Notas de hardening (não-P0, já endereçadas)

- **Estado/limite em memória** (match store + rate limit): worker-local até o
  Top10 #1, que adicionou backend Redis compartilhável. Crítico antes de `-w 2+`.
- **Rate limit de rotas de jogo**: adicionado no Top10 #7 (`/start`, ações,
  telemetria), defesa-em-profundidade contra scraping de seeds.
- **CSRF**: `REBIRTH_REQUIRE_CSRF` é `true` por padrão em produção; os testes o
  desligam por conveniência, então o teste #4 o reativa explicitamente.

## Lacunas de cobertura a fechar depois

- Concorrência real de 2 jogadores no mesmo match pelo caminho Postgres (hoje
  os testes de corrida cobrem só o mercado).
- Fuzzing de payload mais amplo (tipos, tamanhos) nas rotas de auth/economia.
- Teste de replay determinístico adversarial (hash divergente rejeitado).

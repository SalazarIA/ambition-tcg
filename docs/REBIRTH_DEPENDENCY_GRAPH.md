# Ambitionz Rebirth — Grafo de dependências dos serviços (`services/rebirth_*`)

**Gerado:** 2026-06-24 (análise AST de imports). Atualize quando adicionar
dependências entre módulos.

Objetivo: documentar as camadas e, principalmente, **por que existem imports
"lazy" (dentro de função)** — eles são quebra-ciclos deliberados. Sem este mapa,
é fácil reintroduzir um ciclo de import ao "promover" um import lazy para o topo.

## Resultado-chave
- **Não há ciclos no nível de módulo** (o load é um DAG acíclico). ✅
- Os pontos onde um ciclo *apareceria* são quebrados por **import lazy** (import
  feito dentro da função que precisa dele, não no topo do arquivo).

## Camadas (de baixo (folhas) para cima (orquestração))

**Folhas (sem dependência de outro `rebirth_*`):**
`contracts`, `profiler`, `keywords`, `schema`, `redis`, `telemetry`,
`live_balance`, `first_session`, `funnel`, `gate_evidence`, `phase_reports`,
`postmatch`, `release_readiness`, `retention`.

**Fundação (modelo + eventos):**
- `domain` → profiler
- `events` → domain, profiler  *(lazy: contracts)*
- `reducers` → domain, profiler
- `cards` → keywords
- `combat_rules` → *(lazy: keywords)*

**Estado / serialização (par mutuamente dependente):**
- `state` → bot, cards, contracts, domain, events  *(lazy: **serializers**)*
- `serializers` → contracts, domain, events, **state**

**Efeitos / IA:**
- `effects` → contracts, domain, events, profiler, reducers, state
- `bot` → cards, combat_rules, contracts, profiler  *(lazy: keywords)*

**Orquestração:**
- `engine` → bot, cards, combat_rules, contracts, effects, events, state  *(lazy: keywords)*
- `dispatcher` → contracts, profiler  *(lazy: **effects, events, invariants, parity**)*

**Validação / replay (importam engine+dispatcher no topo):**
- `invariants` → contracts, **dispatcher**, domain, **engine**, replay, state
- `parity` → domain, **engine**, reducers, replay
- `replay` → contracts, **dispatcher**, domain, **engine**, profiler

**Produto / persistência:**
- `product` → beta_ops, cards, content_pipeline, deck_coach, first_session, keywords, retention
- `persistence` → campaign, cards, schema  *(lazy: cards, domain, schema, serializers)*
- `campaign` → cards
- `match_store` → contracts  *(lazy: redis)*  ·  `rate_limit` → redis
- `beta_ops` → gate_evidence, public_beta_gate  ·  `public_beta_gate` → live_balance
- `balance_lab` → balance

## Quebra-ciclos lazy (NÃO promova para o topo sem repensar)

1. **`dispatcher` ⇄ {`invariants`, `parity`, `effects`, `events`}**
   `invariants`/`parity`/`replay` importam `engine` + `dispatcher` no topo para
   **re-executar comandos de forma determinística** (validação/replay). O
   `dispatcher`, por sua vez, só precisa deles **quando uma flag de validação
   está ligada** (`_validate_invariants_after_command`, `_parity_validate_after_command`).
   Importar lazy mantém: (a) sem ciclo de load, (b) custo zero quando a validação
   está desligada (o caminho de produção).

2. **`state` ⇄ `serializers`**
   `serializers` precisa do modelo de `state` no topo; `state` só precisa de
   `serializers` na hora de serializar (lazy). Promover o import em `state` para o
   topo cria ciclo.

3. **`engine`/`bot`/`combat_rules` → `keywords` (lazy)**
   `keywords` é folha (não geraria ciclo), mas é importado lazy nos caminhos
   quentes para evitar custo de import desnecessário fora da resolução de combate.
   Seguro promover, mas sem ganho.

4. **`persistence` (lazy: cards/domain/schema/serializers)** e
   **`match_store`/`rate_limit` → `redis` (lazy)**
   Adiam dependências pesadas/opcionais (DB/Redis) para quando realmente usadas.

## Regra para novos imports entre módulos
- Prefira import **no topo** se a dependência for "para baixo" (em direção às
  folhas) e não criar ciclo.
- Se precisar importar "para cima" (em direção a `engine`/`dispatcher`) a partir
  de um módulo que eles consomem, use **import lazy** e **adicione uma linha aqui**
  explicando o porquê.
- Antes de promover um import lazy para o topo, rode a checagem rápida:
  ```sh
  python - <<'PY'
  import ast,pathlib
  # (script de detecção de ciclo top-level — ver histórico do PR de revisão)
  PY
  ```
  Se aparecer ciclo, mantenha lazy.

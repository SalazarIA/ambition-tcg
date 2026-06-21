# Ambitionz Rebirth — Play Store Screenshots

Conjunto atual, capturado em 20 de junho de 2026 a partir do runtime Rebirth real:

| Arquivo | Rota/estado |
| --- | --- |
| `01-arena.png` | `/rebirth`, mão mantida e uma criatura invocada no turno 1 |
| `02-auth.png` | `/rebirth`, modal real de entrar/cadastrar |
| `03-campaign.png` | `/rebirth/campaign`, primeiro encontro disponível |
| `04-collection.png` | `/rebirth/collection`, coleção visível para visitante |
| `05-deck-builder.png` | `/rebirth/deck-builder`, catálogo e deck atual |
| `06-shop.png` | `/rebirth/shop`, booster Rebirth no estado de visitante |

## Contrato dos assets

- PNG RGB de 24 bits, sem alpha.
- 1080 × 1920 px, retrato 9:16.
- Captura Playwright em viewport móvel 432 × 768, ampliada sem recorte para 1080 × 1920.
- Somente UI real do produto: sem moldura de aparelho, barra do navegador, texto promocional sobreposto ou estado fabricado.
- Estado de visitante é mantido quando autenticação seria necessária; não simular carteira, progresso, coleção ou compra.

Esse formato segue a recomendação atual do Google Play para screenshots de jogos em retrato: 9:16 e no mínimo 1080 × 1920. A regra geral aceita dimensões entre 320 e 3840 px, com o lado maior limitado a duas vezes o menor:
https://support.google.com/googleplay/android-developer/answer/9866151

## Captura reproduzível

Suba o Flask com banco SQLite temporário fora do repositório:

```bash
env -u DATABASE_URL -u REBIRTH_DATABASE_URL \
  PORT=5093 \
  REBIRTH_DB_PATH=/tmp/ambition-rebirth-playstore-qa.db \
  REBIRTH_ALLOW_SQLITE_TESTING=true \
  REBIRTH_REQUIRE_CSRF=false \
  SECRET_KEY=rebirth-playstore-qa \
  DEBUG_MODE=false \
  PYTHONPATH="$PWD" \
  .venv/bin/python app.py
```

Use um script Playwright temporário em `/tmp`, com:

```python
browser.new_context(
    viewport={"width": 432, "height": 768},
    service_workers="block",
    locale="pt-BR",
    color_scheme="dark",
)
```

Capture apenas a viewport, nunca a página inteira. Para a Arena, mantenha a mão inicial e invoque uma criatura antes da captura. Nas páginas longas, posicione a viewport no primeiro conteúdo que explica honestamente a superfície.

## Checklist antes de substituir

- Título e rota correspondem ao arquivo.
- Não há overlay de erro do framework.
- Console e `pageerror` estão vazios.
- `document.documentElement.scrollWidth <= 432`.
- Texto, cartas, saldo e progresso correspondem ao estado realmente carregado.
- O PNG final é `1080 x 1920`, `RGB`, sem alpha e não está distorcido.
- Só remover screenshots antigos quando forem claramente de uma superfície aposentada.

O conjunto roxo antigo foi removido porque era duplicado e mostrava o produto pré-Rebirth, incluindo a alegação desatualizada de 250 cartas.

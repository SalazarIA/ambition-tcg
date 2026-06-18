# Rebirth — Play Internal Testing Readiness

Data da auditoria: 17 de junho de 2026  
Branch observada: `fix/arena-cache-overlap`  
Escopo: PWA, cache/versionamento, páginas legais, headers e preparação documental para teste interno. Android, credenciais, Play Console e deploy foram somente inspecionados ou listados como gates; não foram alterados.

## Resultado executivo

| Área | Estado | Evidência local |
|---|---|---|
| Manifest PWA | Pronto localmente | Metadados pt-BR, `id`/`scope` estáveis, ícones PNG `any` e `maskable` em 192/512, SVG com `sizes: any`. |
| Service worker | Pronto localmente | Cache com namespace próprio, versão de asset separada, allowlist exata, APIs/navegações sempre na rede e revalidação protegida por `event.waitUntil`. |
| Privacidade/Termos/Exclusão | Pronto para revisão jurídica | Páginas públicas em pt-BR, datadas, com responsável, prestadores, retenção, LGPD e fluxo self-service real. Qualquer aprovação jurídica anterior foi invalidada pela mudança de hash. |
| Headers | Contrato local aprovado | CSP, `nosniff`, `DENY`, Referrer Policy e Permissions Policy presentes também nas páginas legais, manifest, service worker e resposta 405. |
| Android App Bundle | Bloqueado fora deste escopo | Nenhum `.aab` foi encontrado. Existem dois identificadores/configurações Android diferentes e o owner precisa escolher o pacote canônico antes do primeiro upload. |
| Play Console | Não verificável no repositório | App signing, ficha, declarações, track, lista de testers e resultado do review dependem da conta do Play Console. |

## PWA e cache

- `ASSET_VERSION` permanece alinhada ao runtime web: `v106_ARENA_ACTIONS`.
- O nome físico do Cache Storage agora é `ambitionz-rebirth-shell-${ASSET_VERSION}`. Isso evita usar uma versão genérica como namespace global da origem e mantém a limpeza dos caches Rebirth legados.
- Apenas URLs exatas de `CORE_ASSETS` podem entrar no cache. Query strings arbitrárias não criam variações sobrepostas do mesmo asset.
- Autenticação, carteira, perfil, mercado, loadout, progressão, tutorial, demais APIs e toda navegação HTML continuam network-only para não servir estado de outro jogador.
- A estratégia de asset é cache-first com revalidação. A atualização em segundo plano mantém o worker vivo até `cache.put` e a poda terminarem.
- Não há fallback offline de HTML. Isso é intencional enquanto páginas autenticadas e estado de partida forem autoritativos no servidor; a instalação PWA não deve prometer jogo offline.

## Privacidade e exclusão

URLs públicas a informar, usando o domínio canônico realmente implantado:

- Política de Privacidade: `https://<dominio-canonico>/privacy`
- Termos: `https://<dominio-canonico>/terms`
- Exclusão de conta: `https://<dominio-canonico>/data-deletion`

O fluxo implementado e documentado é:

1. Abrir `/rebirth/support` no app ou navegador.
2. Autenticar a conta.
3. Selecionar **Excluir Minha Conta**.
4. Confirmar com `DELETE REBIRTH`.
5. O backend remove a conta e dados principais e encerra a sessão.

### Lacuna local que ainda exige correção de backend

`delete_account` coloca `telemetry_events.user_id` como `NULL`, mas o JSON de um feedback autenticado pode continuar contendo `user_id` dentro de `event_json`. A página legal agora descreve essa retenção com transparência, mas a situação deve ser corrigida ou formalmente coberta por uma política de retenção aprovada antes de teste externo ampliado. A correção pertence ao backend e ficou fora deste worker.

## Headers e validação em produção

O contrato local cobre:

- `Content-Security-Policy` com `object-src 'none'`, `base-uri 'self'`, `form-action 'self'` e `frame-ancestors 'none'`;
- `X-Content-Type-Options: nosniff`;
- `X-Frame-Options: DENY`;
- `Referrer-Policy: strict-origin-when-cross-origin`;
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`;
- `Service-Worker-Allowed: /` e `Cache-Control: no-cache` no service worker.

`Strict-Transport-Security` não é definido pelo Flask atual. Antes de liberar testers, confirmar no domínio HTTPS se a camada de hospedagem injeta HSTS; se não injetar, o owner de runtime deve implementar a política com parâmetros compatíveis com todos os subdomínios. Também confirmar `Secure` no cookie de sessão no ambiente de produção.

## Gate técnico Android observado (somente leitura)

- `android/app/build.gradle` usa `applicationId com.elementra.ambitiontcg`, `versionCode 1` e `versionName 1.0`.
- `mobile/AmbitionzAndroid/capacitor.config.ts` declara `com.ambitionzgame.app` e outro domínio de produção.
- O wrapper raiz aponta para `https://ambition-tcg.onrender.com`; o wrapper em `mobile/` aponta para `https://ambitionzgame.com`.
- O projeto raiz declara `compileSdkVersion 35` e `targetSdkVersion 35`. Isso atende o mínimo atual para submissão, mas o Google informa que API 36 será exigida a partir de agosto de 2026.
- Nenhum AAB foi encontrado e nenhum build Android foi executado nesta auditoria.

Escolher package ID e domínio canônicos antes do primeiro upload é bloqueante: o package ID identifica permanentemente o app no Play Console, e a política/legal listing deve corresponder ao mesmo produto e desenvolvedor.

## Itens que dependem do Play Console

1. Confirmar tipo e verificação da conta de desenvolvedor e quem possui permissão de release.
2. Escolher o package ID canônico e habilitar Play App Signing/keystore sem registrar segredo no repositório.
3. Gerar um AAB assinado com `versionCode` inédito, fazer upload no track **Internal testing** e resolver todos os erros do upload.
4. Definir lista de testers com contas Google/Workspace, publicar o release interno e distribuir o link de opt-in.
5. Conferir nome do app/desenvolvedor, idioma padrão, categoria Game, países, email/site de suporte e ficha mínima exigida pela conta.
6. Preencher App access com instruções/credencial de review quando telas autenticadas precisarem ser avaliadas.
7. Declarar ads, target audience, content rating e qualquer permissão sensível. O Android observado pede apenas `INTERNET`, mas o AAB enviado é a fonte final.
8. Informar os URLs públicos de privacidade e exclusão e confirmar `HTTP 200`, HTTPS, ausência de geoblock e descoberta clara do botão de exclusão.
9. Enquanto o app estiver **exclusivamente** em internal testing, o formulário Data safety é dispensado; ele passa a ser obrigatório em closed/open/production e deve refletir app, backend e SDKs de terceiros.
10. Revisar pre-launch report, Android vitals, policy status e qualquer aviso do Play Console antes de convidar testers.

Para contas pessoais criadas depois de 13 de novembro de 2023, o requisito de 12 testers por 14 dias contínuos é do teste **fechado** necessário para pedir acesso à produção; não bloqueia o track interno.

## Validação executada

```text
node --check static/js/service-worker.js
.venv/bin/python -m pytest <contratos focados> -q
```

Resultado final: `51 passed`. A inspeção no navegador local validou `/privacy` → `/data-deletion` → `/terms` em viewport mobile e desktop, com títulos e conteúdo significativos, navegação funcional e nenhum warning/error de console.

## Fontes oficiais consultadas

- [Configurar teste interno, fechado ou aberto](https://support.google.com/googleplay/android-developer/answer/9845334?hl=en)
- [Requisitos de teste para novas contas pessoais](https://support.google.com/googleplay/android-developer/answer/14151465?hl=en)
- [Requisito de exclusão de conta](https://support.google.com/googleplay/android-developer/answer/13327111?hl=en)
- [Política de dados do usuário e privacidade](https://support.google.com/googleplay/android-developer/answer/15402170?hl=en)
- [Formulário Data safety](https://support.google.com/googleplay/android-developer/answer/10787469?hl=en)
- [Requisitos atuais de target API](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en)
- [Migração e prazo da API 36](https://developer.android.com/develop/adaptive-apps/guides/app-orientation-aspect-ratio-resizability)

## Decisão

O web/PWA está tecnicamente pronto para integrar um candidato de teste interno. O release no Play ainda não está pronto para upload até o owner escolher o wrapper/package ID canônico e produzir o AAB assinado. O avanço para testers externos deve aguardar também a correção/revisão da retenção de feedback/telemetria, nova aprovação jurídica dos hashes atuais e a confirmação dos itens exclusivos do Play Console.

# Rebirth — Play Internal Testing Readiness

Data da reauditoria: 24 de junho de 2026<br>
Branch observada: `main`<br>
Escopo autorizado: `mobile/AmbitionzAndroid/playstore/*.md`, `mobile/AmbitionzAndroid/playstore/texts/**` e este relatório. Android build, Play Console, produção e credenciais foram somente inspecionados; não houve upload, publicação ou deploy por esta auditoria.

## Resultado executivo

| Área | Estado | Evidência |
|---|---|---|
| Produção Rebirth | Operacional com divergências | `ambitionzgame.com` entrega Arena, campanha, coleção, deck builder, loja, recompensas, ranking, perfil e suporte; o suporte expõe `v125_NOVIDADES`. |
| Android beta.2 | Candidato encontrado | AAB de 3,3 MB presente, assinatura verificada, pacote `com.ambitionzgame.app`, `versionName 1.0.0-beta.2`, candidato `versionCode 2` e servidor canônico incorporado. |
| Ondas 1–3 | Refletidas sem sobrepromessa | Release notes registram dificuldade/consistência do bot, Água/Sombra/Cerco e interação reativa; listing descreve somente recursos visíveis e não promete PvP, offline ou quantidade exata de cartas. |
| Textos Play | Prontos para copy/paste | Listing, release notes, convite, instruções e checklists descrevem Internal testing e Rebirth v121; release notes pt-BR têm 464 caracteres sem a quebra final do arquivo. |
| Screenshots Play | Alinhados ao Rebirth | Seis PNGs atuais em `1080x1920`, RGB e sem alpha; as capturas antigas com training/250 cartas não estão mais no conjunto atual. |
| Ícone e feature graphic | Formato corrigido; aprovação visual pendente | Atualização concorrente de 21/06 deixou feature graphic em RGB `1024x500` e ícone em RGBA `512x512`, ambos abaixo do limite; crop/legibilidade ainda dependem do owner e do Console. |
| Privacidade/Termos/Exclusão | Públicas com copy inconsistente | URLs respondem por HTTPS e a exclusão é encontrável, mas produção ainda usa “beta fechada”/“Teste Fechado” em partes do conteúdo. |
| Headers/cache | Parcial | CSP, `nosniff`, `DENY`, Referrer Policy, Permissions Policy e cookie `Secure` confirmados em auditoria anterior; HSTS não foi observado. O contrato local do service worker agora exige `Cache-Control: no-cache`. |
| Play Console | Não verificado | Package ownership, histórico de `versionCode`, app signing, declarações, track, testers, review e relatórios dependem da conta. Nenhum upload foi feito. |

## Identidade do candidato Android

Artefato observado:

`mobile/AmbitionzAndroid/android/app/build/outputs/bundle/release/app-release.aab`

- Modificação local: 20 de junho de 2026.
- SHA-256: `4beae3778a59d074fdbab9d7d1b9ca56df8901f79e2fa67730995310c77a297b`.
- `jarsigner`: `jar verified`; certificado de upload autoassinado, como é comum para chaves de upload.
- O manifesto binário contém `com.ambitionzgame.app` e `android.permission.INTERNET`.
- O `capacitor.config.json` incorporado contém `appId com.ambitionzgame.app`, servidor `https://ambitionzgame.com` e user agent `AmbitionzAndroid/1.0.0-beta.2`.
- A configuração fonte do wrapper móvel declara `versionCode 2`, `versionName 1.0.0-beta.2`, `minSdk 24`, `compileSdk 36` e `targetSdk 36`.
- Nenhuma biblioteca nativa `base/lib/*.so` foi encontrada no AAB. Isso reduz o risco do requisito de páginas de 16 KB, mas a validação final é a do Play Console.

O repositório também contém um projeto Android raiz legado com outro package ID. Para esta beta, somente o artefato sob `mobile/AmbitionzAndroid` corresponde ao pacote e domínio documentados. O package ID se torna permanente após o primeiro upload.

`versionCode 2` é apenas candidato até consulta ao Play Console. Se já tiver sido usado, será necessário gerar outro AAB com código inédito fora deste escopo.

## Auditoria das Ondas 1–3 contra os textos

### Onda 1 — observabilidade, honestidade e robustez

- Entregue no candidato: lab-gate contra cartas dominantes, telemetria de decisão por arquétipo, gradiente de erro por dificuldade e invariantes/replay determinísticos.
- Copy adotada: “dificuldades do bot mais distintas e decisões de combate mais consistentes”.
- Limite de marketing: telemetria, CI e replay são garantias internas; não foram vendidos como recursos ao jogador.

### Onda 2 — diversidade de arquétipos

- Entregue no candidato: WATER com sinergia de vida alta, SHADOW com sinergia de vida baixa, EARTH com Guarda e SIEGE/Cerco como counter estrutural.
- Copy adotada: listing fala em estilos de cura, atrito, defesa e Cerco; release notes nomeiam Água, Sombra e Cerco contra Guarda.
- Limite de marketing: nenhuma taxa de vitória, dominância de meta ou promessa de balanceamento perfeito foi publicada.

### Onda 3 — interação reativa

- Entregue no candidato: dez armadilhas reativas na cadeia de interrupção e magias com alvo em unidade, cobertas por invariantes, replay e determinismo.
- O engine atual também permite ao bot armar armadilhas por `_bot_auto_play_support`; portanto, o backlog anterior “bot não arma nem usa traps” não deve aparecer nos materiais desta release.
- Copy adotada: “armadilhas reativas e magias com alvo em unidades”, sem afirmar PvP ou controle manual de uma stack.

Correções aplicadas à ficha:

- removida a alegação incorreta de “evoluções de monstros, magias e armadilhas”; a evolução por duplicata é de monstros;
- removida a promessa de “partidas rápidas”, pois a auditoria não sustenta um limite de duração;
- mantida a omissão de quantidade exata de cartas enquanto produção divergir entre `100` e `103`.

## Produção `ambitionzgame.com`

Auditoria HTTP reexecutada em 21 de junho de 2026 e documentação reconciliada em 24 de junho de 2026:

- `/` promove Ambitionz Rebirth, duelos, coleção, loja e progressão.
- `/rebirth` carrega a Arena contra bot.
- `/rebirth/campaign` expõe campanha para um jogador com dez encontros.
- `/rebirth/collection` e `/rebirth/deck-builder` expõem coleção e baralho de 30 cartas.
- `/rebirth/shop` expõe boosters gratuitos durante a beta e mercado em moeda virtual.
- `/rebirth/progression`, `/rebirth/ranking` e `/rebirth/profile` carregam.
- `/feedback` redireciona para `/rebirth/support`; os textos Play agora usam a URL canônica direta.
- `/privacy`, `/terms` e `/data-deletion` respondem `HTTP 200` em HTTPS.
- A página de suporte mostra `Versão v125_NOVIDADES`.

### Divergências encontradas

- A produção mostra “100 cartas” em um bloco e “103 no catálogo” em outros. O listing atualizado evita quantidade exata até a UI ser normalizada.
- Privacidade, termos e exclusão ainda exibem “Teste Fechado” em links de rodapé; termos também usam “beta fechada”. Isso não foi alterado por estar fora do escopo, mas conflita com Internal testing beta.2.

## PWA, cache e headers

- `ASSET_VERSION` permanece alinhada ao runtime web: `v125_NOVIDADES`.
- O nome físico do Cache Storage é `ambitionz-rebirth-shell-${ASSET_VERSION}`.
- Apenas URLs exatas de `CORE_ASSETS` podem entrar no cache.
- Autenticação, carteira, perfil, mercado, loadout, progressão, tutorial, demais APIs e navegação HTML são network-only.
- Não há fallback offline de HTML; a ficha não deve prometer jogo offline.

Produção confirmou:

- `Content-Security-Policy`;
- `X-Content-Type-Options: nosniff`;
- `X-Frame-Options: DENY`;
- `Referrer-Policy: strict-origin-when-cross-origin`;
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`;
- cookie de sessão com `Secure`, `HttpOnly` e `SameSite=Lax`.

Lacunas de produção:

- `Strict-Transport-Security` não apareceu nas respostas auditadas.
- A rota local `/service-worker.js` é coberta por teste e deve responder `Cache-Control: no-cache` e `Service-Worker-Allowed: /`. Se produção divergir após deploy, isso deve ser tratado como bloqueio de cache-bust.

## Privacidade e exclusão

URLs canônicas:

- Política de Privacidade: `https://ambitionzgame.com/privacy`
- Termos: `https://ambitionzgame.com/terms`
- Suporte e feedback: `https://ambitionzgame.com/rebirth/support`
- Exclusão de conta: `https://ambitionzgame.com/data-deletion`

Fluxo documentado:

1. Abrir `/rebirth/support` no app ou navegador.
2. Autenticar a conta.
3. Selecionar **Excluir Minha Conta**.
4. Confirmar com `DELETE REBIRTH`.
5. O backend remove a conta e dados principais e encerra a sessão.

### Lacuna de retenção fora deste escopo

`delete_account` coloca `telemetry_events.user_id` como `NULL`, mas o JSON de um feedback autenticado pode continuar contendo `user_id` dentro de `event_json`. A página legal descreve essa retenção, mas a situação deve ser corrigida ou formalmente coberta por política aprovada antes de ampliar o teste.

## Requisitos oficiais atuais relevantes

- Internal testing distribui para até 100 testers por app e pode começar antes da configuração completa da ficha.
- A lista interna usa contas Google; o Console fornece link de opt-in e permite configurar URL/email de feedback.
- O requisito de 12 testers por 14 dias contínuos pertence ao closed test exigido para produção em determinadas contas pessoais novas. Ele não bloqueia Internal testing.
- Apps exclusivamente ativos em Internal testing são dispensados do formulário Data safety. A dispensa termina quando houver closed, open ou production ativo.
- Se o app exige login para revisar funcionalidades, App access deve fornecer credenciais reutilizáveis, válidas de qualquer localidade, sem OTP bloqueante e com instruções em inglês.
- Como o app permite criação de conta, deve oferecer exclusão dentro do serviço e uma URL pública funcional para iniciar a exclusão fora do app.
- A página pública atual de target API informa API 35 como mínimo para novos apps e updates desde 31 de agosto de 2025. O wrapper móvel já declara API 36.
- Desde 1º de novembro de 2025, apps novos/updates que miram Android 15+ devem suportar páginas de memória de 16 KB em dispositivos 64-bit. O AAB observado não contém `.so`, mas o resultado do Play Console é definitivo.
- Nome, descrição curta e descrição completa têm limites de 30, 80 e 4.000 caracteres.
- Release notes aceitam até 500 caracteres Unicode por idioma; o texto pt-BR preparado tem 464 caracteres sem a quebra final do arquivo.
- Ícone: PNG 32-bit com alpha, `512x512`, até 1.024 KB.
- Feature graphic: JPEG ou PNG 24-bit sem alpha, `1024x500`.
- Screenshots: JPEG ou PNG 24-bit sem alpha; para jogos, pelo menos três capturas `9:16` em `1080x1920` atendem a recomendação de elegibilidade.

## Gate de assets

Screenshots atuais:

- `01-arena.png`
- `02-auth.png`
- `03-campaign.png`
- `04-collection.png`
- `05-deck-builder.png`
- `06-shop.png`

Todos foram observados como PNG RGB `1080x1920`, sem alpha e com hashes distintos. As capturas mostram o produto Rebirth atual e não incluem `250` cartas ou training legado.

Pendências:

- aprovar o crop e a legibilidade do texto da feature graphic no preview da Play;
- aprovar a silhueta arredondada e a leitura do pequeno wordmark do ícone em tamanhos reduzidos;
- evitar quantidade exata de cartas em qualquer futuro asset até a produção resolver a divergência 100/103.

Revalidação após a atualização concorrente:

- feature graphic: PNG RGB `1024x500`, 661 KB, SHA-256 `c582e691d81d152d3a6c6d44834ac9be16f60e09d241015ad330693b20e0c47d`;
- ícone: PNG RGBA `512x512`, 166 KB, SHA-256 `434cc8dac79dad3c7dc81edbab745216bdabc30defc2d744545d43c8cc960f59`.

Não resta bloqueio técnico conhecido de formato. A validação final é a do Play Console.

## Itens que dependem do Play Console

1. Confirmar tipo e verificação da conta de desenvolvedor e quem possui permissão de release.
2. Confirmar que o app do Console pertence a `com.ambitionzgame.app` antes do primeiro upload.
3. Confirmar que `versionCode 2` é inédito; se não for, um novo artefato será necessário.
4. Habilitar Play App Signing/keystore sem registrar segredo no repositório.
5. Fazer upload do AAB no track **Internal testing** e resolver todos os erros do upload.
6. Validar compatibilidade de 16 KB, dispositivos suportados e qualquer aviso de SDK.
7. Definir lista de testers com contas Google/Workspace, publicar o release interno e distribuir o link de opt-in.
8. Conferir nome do app/desenvolvedor, idioma pt-BR, categoria Game/Card, países, email/site de suporte e ficha mínima.
9. Preencher App access com instruções em inglês e credencial de review reutilizável.
10. Declarar ads, target audience, content rating e qualquer permissão sensível com base no AAB enviado.
11. Informar URLs públicas de privacidade e exclusão.
12. Manter Data safety pendente somente enquanto o app estiver exclusivamente em Internal testing.
13. Revisar pre-launch report, Android vitals, policy status e qualquer aviso antes de convidar testers.

## Checklist de decisão

- [x] Branch e escopo autorizados confirmados.
- [x] AAB beta.2 encontrado e assinatura verificada sem rebuild.
- [x] Domínio, runtime v121 e páginas públicas auditados/reconciliados.
- [x] Textos/checklists migrados de closed/training legado para Internal/Rebirth.
- [x] Listing e release notes auditados contra Onda 1–3 e produção.
- [x] Evolução corrigida para monstros por duplicata; promessa de partida rápida removida.
- [x] Release notes pt-BR validadas com 464/500 caracteres sem a quebra final do arquivo.
- [x] Claims textuais de 250 cartas removidos do escopo editável.
- [x] Screenshots atuais validados em leitura como Rebirth, RGB e `1080x1920`.
- [x] Formato de ícone e feature graphic corrigido por atualização concorrente.
- [ ] Obter aprovação visual final do owner e validação do Play Console para os dois assets.
- [ ] Normalizar em produção “beta fechada” versus Internal testing.
- [ ] Resolver ou aceitar formalmente HSTS ausente; revalidar em produção que `/service-worker.js` mantém `Cache-Control: no-cache`.
- [ ] Confirmar `versionCode 2` e package no Play Console.
- [ ] Completar declarações, reviewer access e lista de até 100 testers.
- [ ] Fazer upload e revisar o relatório do Play Console.

Nenhum item desmarcado foi executado por esta auditoria.

## Fontes oficiais consultadas

- [Configurar teste interno, fechado ou aberto](https://support.google.com/googleplay/android-developer/answer/9845334?hl=en)
- [Preparar e lançar um release](https://support.google.com/googleplay/android-developer/answer/9859348?hl=en)
- [Requisitos de teste para novas contas pessoais](https://support.google.com/googleplay/android-developer/answer/14151465?hl=en)
- [Preparar o app para review](https://support.google.com/googleplay/android-developer/answer/9859455?hl=en)
- [Credenciais de acesso para review](https://support.google.com/googleplay/android-developer/answer/15748846?hl=en)
- [Requisito de exclusão de conta](https://support.google.com/googleplay/android-developer/answer/13327111?hl=en)
- [Política de dados do usuário e privacidade](https://support.google.com/googleplay/android-developer/answer/15402170?hl=en)
- [Formulário Data safety](https://support.google.com/googleplay/android-developer/answer/10787469?hl=en)
- [Requisitos atuais de target API](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en)
- [Suporte a páginas de memória de 16 KB](https://developer.android.com/guide/practices/page-sizes)
- [Configuração e limites da ficha](https://support.google.com/googleplay/android-developer/answer/9859152?hl=en)
- [Requisitos de preview assets](https://support.google.com/googleplay/android-developer/answer/9866151?hl=en)

## Decisão

O AAB móvel beta.2 está pronto para ser apresentado ao Play Console como candidato de Internal testing, sujeito à confirmação de package e `versionCode 2` e às validações do upload. Listing, release notes e instruções agora estão coerentes com as Ondas 1–3 e com produção, sem promessas de PvP, offline, duração curta ou contagem exata de cartas. Screenshots, ícone e feature graphic atendem aos formatos documentados; os dois últimos ainda exigem aprovação visual do owner e validação no Console. As divergências de copy “Teste Fechado”, catálogo 100/103, HSTS e confirmação do cache `no-cache` em produção para `/service-worker.js` seguem registradas para os owners responsáveis.

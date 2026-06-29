# Rebirth — Checklist de Deploy Mobile (Top10 #9)

Data: 2026-06-19 · Validação Android atualizada em 2026-06-20 · Escopo: Web
(PWA) + Android (existente) + iOS (a criar)

## Estado atual (verificado)

| Plataforma | Estado |
|---|---|
| Web/PWA | Render + `/health` + schema upgrade ok; manifest corrigido (Top10 #8). |
| Android | Canônico em `mobile/AmbitionzAndroid`; pacote `com.ambitionzgame.app`; `versionCode 2` / `1.0.0-beta.2`; API 36. |
| iOS | **Não existe** `ios/`. `@capacitor/ios` está em `package.json` mas não instalado. |
| Toolchain local | `xcodebuild` presente; **CocoaPods (`pod`) ausente** → `cap add ios` falha no `pod install`. |
| Capacitor | `server.url` aponta para `https://ambitionzgame.com` por HTTPS (WebView remoto). |

> Por isso o projeto iOS **não foi gerado neste passo**: sem CocoaPods, `cap add
> ios` deixaria um `ios/` meio-inicializado. Abaixo está o caminho completo para
> um Mac com a toolchain e conta Apple.

## 1. Gerar o projeto iOS (Mac com Xcode + Apple Developer)

```bash
npm ci
sudo gem install cocoapods          # ou: brew install cocoapods
npx cap add ios                     # cria ios/ e roda pod install
npx cap sync ios                    # copia webDir + plugins
npx cap open ios                    # abre no Xcode
```

No Xcode: selecionar Team de signing, definir Bundle Identifier (ver §3),
incrementar build, Archive → distribuir para TestFlight.

## 2. Cookies / sessão / CSRF no WebView

O app carrega o site remoto (Render) dentro do WebView, então a origem do
WebView **é** a origem do site — cookies são first-party:

- `SESSION_COOKIE_SECURE=true` + `SameSite=Lax`: ok sob HTTPS first-party; os
  POSTs do jogo são same-site, não são bloqueados.
- CSRF (`X-Rebirth-CSRF`): o JS busca `/api/rebirth/csrf` e envia no header —
  funciona igual ao browser.
- WKWebView (iOS) e Android WebView aceitam cookies por padrão.
- **Validar no device**: registrar, logar, jogar uma partida e resgatar o diário
  dentro do app — confirmando persistência de sessão e CSRF ponta a ponta.

## 3. Decisão de appId / branding (outward-facing — requer aprovação do owner)

`mobile/AmbitionzAndroid/capacitor.config.ts`:
`appId = com.ambitionzgame.app`, `appName = "Ambitionz"`.

- **Não alterar o `appId`** — `com.ambitionzgame.app` é a identidade canônica e
  deve permanecer estável para atualizações da listagem existente.
- O nome de exibição permanece **Ambitionz**.

## 4. Assets de loja

- Play Store: pacote atual em `mobile/AmbitionzAndroid/playstore/` já descreve
  o Rebirth e o alvo **Internal testing**, com screenshots `1080x1920`, ícone
  `512x512` e feature graphic `1024x500`; aprovação visual do owner e validação
  do Play Console ainda são definitivas.
- App Store: criar screenshots + descrição próprios antes de TestFlight/App
  Store (mesma narrativa, sem prometer PvP, offline ou quantidade exata de
  cartas).
- Ícones/splash Android: launcher, round icon, adaptive foreground, splash e
  ícone Play regenerados deterministicamente a partir de
  `static/icons/icon-512.png` (Rebirth gold/dark). O foreground usa a safe zone
  central 66/108 e o splash preserva o footprint anterior sobre `#070711`.

## 5. Auditoria Android (2026-06-19; smoke em 2026-06-20)

- `compileSdk` / `targetSdk`: 36; `minSdk`: 24.
- Google Play exige API 35+ para novos apps/updates desde 31/08/2025; API 36
  atende ao requisito.
- Manifest: somente `INTERNET` é declarado pelo app; `VIBRATE` vem do plugin
  Haptics. Não há permissões perigosas/runtime.
- Tráfego cleartext desativado no Capacitor e no manifest/network security.
- Backup, restore em nuvem e transferência device-to-device desativados, com
  regras para Android 11- e Android 12+.
- `FileProvider` template removido porque nenhum plugin instalado o utiliza.
- Testes de identidade corrigidos para `com.ambitionzgame.app`.
- Dependências Capacitor/npm fixadas nas versões presentes no lockfile.
- Arquivos locais de assinatura permanecem ignorados/não rastreados e foram
  restringidos para permissão `0600`; nenhum segredo foi exposto.

### Evidências locais

- `npm ci --ignore-scripts`: ok.
- `npm run cap:sync`: ok; 5 plugins Android sincronizados.
- `npx cap doctor`: Android ok.
- `npm audit`: 0 vulnerabilidades.
- `./gradlew clean test lint assembleDebug bundleRelease --no-daemon`: ok com
  Gradle 8.14.5; `assembleDebugAndroidTest`: ok.
- Teste unitário de identidade passou em debug e release.
- Lint: 0 erros, 20 avisos. O `roundIcon` foi corrigido para máscara circular.
  Pendências relevantes: orientação portrait será ignorada em parte dos
  cenários de tela grande no Android 16; o ícone adaptativo ainda não fornece
  variante monochrome/themed.
- APK debug:
  `mobile/AmbitionzAndroid/android/artifacts/ambitionz-1.0.0-beta.2-debug.apk`
  — SHA-256
  `f9f511c30ab9c0e281b476cd1e8eea9d084c401382b6060629e80cae11675745`.
- AAB release assinado:
  `mobile/AmbitionzAndroid/android/artifacts/ambitionz-1.0.0-beta.2-release.aab`
  — SHA-256
  `4beae3778a59d074fdbab9d7d1b9ca56df8901f79e2fa67730995310c77a297b`.
- Certificado de upload do AAB: SHA-256
  `03:13:08:13:6A:2D:C4:CC:A8:30:88:4D:E7:6E:8A:01:43:CC:BD:E4:BE:14:43:B8:D5:72:25:CD:42:29:BF:19`;
  assinatura JAR verificada.
- Manifest mesclado e `aapt`: pacote `com.ambitionzgame.app`, `versionCode 2`,
  `versionName 1.0.0-beta.2`, min API 24, target/compile API 36, backup e
  cleartext desativados.
- AVD `Pixel_7` iniciado com Android 17/API 37 no Android Emulator 36.5.11.0.
- `assembleDebugAndroidTest`: ok; o `app-debug.apk` reconstruído manteve
  exatamente o SHA-256 do artefato beta.2 listado acima.
- APK beta.2 instalado via `adb`; `dumpsys package` confirmou
  `com.ambitionzgame.app`, `versionCode 2` e `versionName 1.0.0-beta.2`.
- Teste instrumentado executado contra o APK instalado:
  `AppIdentityInstrumentedTest.targetContextUsesCanonicalPackage` passou
  (`OK (1 test)`, 1,601 s).
- Smoke via `adb`/UI tree/screenshot: cold launch de `.MainActivity`, home
  Rebirth renderizada pelo WebView remoto, rolagem respondendo e árvore
  acessível com navegação e CTA `ENTRAR / CADASTRAR`.
- O CTA abriu o diálogo `Entrar / Cadastrar` com campos de login/cadastro; o
  fechamento retornou à home. Ao fim, o processo permaneceu vivo e o crash
  buffer estava vazio, sem `FATAL EXCEPTION` ou ANR do app.
- Na primeira passagem, o AVD sob pressão de memória exibiu um ANR do System UI
  e o Play Store encerrou o app ao atualizar o WebView (`installPackageLI`,
  versão 145 → 149.0.7827.91). O smoke foi repetido após a atualização e ficou
  estável.
- Nenhum upload foi realizado.

## 6. Risco estrutural: wrapper de WebView remoto

O app é um wrapper do site remoto. Implicações a decidir antes de publicar:

- **Sem modo offline** e **downtime do Render derruba o app publicado**.
- Apple/Google podem reprovar apps de "funcionalidade mínima" (mero wrapper).
- Mitigações: empacotar os assets localmente (PWA offline com `webDir`) e usar a
  rede só para a API de partida; ou assumir o modelo remoto com tela de fallback
  offline e SLA do Render.

## Checklist de submissão (resumo)

- [ ] `ios/` gerado e `cap sync` ok
- [ ] Bundle id + signing definidos; build no TestFlight
- [ ] Login + partida + resgate validados no device (cookies/CSRF)
- [ ] appId/appName decididos com o owner
- [x] Screenshots/textos Play Store refeitos para o Rebirth/Internal testing
- [ ] Screenshots/textos App Store refeitos para o Rebirth
- [ ] Decisão sobre offline/wrapper documentada
- [x] APK debug instalado e smoke testado em device/emulador
- [x] AAB Android `versionCode 2` reconstruído e validado antes de upload

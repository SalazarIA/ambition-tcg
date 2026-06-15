# Rebirth — Checklist de Deploy Mobile (Top10 #9)

Data: 2026-06-15 · Escopo: Web (PWA) + Android (existente) + iOS (a criar)

## Estado atual (verificado)

| Plataforma | Estado |
|---|---|
| Web/PWA | Render + `/health` + schema upgrade ok; manifest corrigido (Top10 #8). |
| Android | Projeto existe (`android/`, `mobile/AmbitionzAndroid`); AAB defasado. |
| iOS | **Não existe** `ios/`. `@capacitor/ios` está em `package.json` mas não instalado. |
| Toolchain local | `xcodebuild` presente; **CocoaPods (`pod`) ausente** → `cap add ios` falha no `pod install`. |
| Capacitor | `server.url` aponta para `https://ambition-tcg.onrender.com` (WebView remoto). |

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

`capacitor.config.json`: `appId = com.elementra.ambitiontcg`, `appName = "Ambitionz"`.

- **Não alterar o `appId` se já houver app publicado** — mudar cria uma listagem
  nova e quebra atualizações para quem já instalou.
- Recomendação: manter o `appId` atual e alinhar o `appName` para
  **"Ambitionz Rebirth"** (nome de exibição) **antes** da primeira submissão.
- Decidir isto explicitamente antes de publicar (por isso não foi alterado aqui).

## 4. Assets de loja (defasados — refazer para o Rebirth atual)

- Play Store: screenshots/textos ainda descrevem o Ambitionz antigo. Refazer com
  o duelo de 3 campos atual, em pt-BR (e en se internacionalizar).
- App Store: criar screenshots + descrição próprios (mesma narrativa).
- Ícones/splash: já existem (`static/icons/*`, splash do Capacitor).

## 5. Risco estrutural: wrapper de WebView remoto

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
- [ ] Screenshots/textos Play Store + App Store refeitos para o Rebirth
- [ ] Decisão sobre offline/wrapper documentada
- [ ] AAB Android reconstruído a partir do estado atual

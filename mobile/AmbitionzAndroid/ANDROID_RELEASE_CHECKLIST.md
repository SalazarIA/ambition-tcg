# Ambitionz Android Release Checklist

Current target:
Internal testing on Google Play.

App identity:
- App name: Ambitionz
- Package name: com.ambitionzgame.app
- Official domain: https://ambitionzgame.com

Required Play Console links:
- Website: https://ambitionzgame.com
- Privacy Policy: https://ambitionzgame.com/privacy
- Terms: https://ambitionzgame.com/terms
- Support: https://ambitionzgame.com/rebirth/support
- Account deletion: https://ambitionzgame.com/data-deletion

Before release build:
- Run `npm ci` and `npm run cap:sync`.
- Run `cd android && ./gradlew test lint assembleDebug bundleRelease`.
- Confirm `versionCode 2` and `versionName 1.0.0-beta.2`.
- Confirm package `com.ambitionzgame.app`.
- Confirm merged permissions are limited to `INTERNET`, `VIBRATE` and AndroidX's signature permission.
- Confirm backup/data extraction remain disabled.
- Confirm launcher, round icon, adaptive foreground, splash and Play icon use
  the gold/dark Rebirth artwork sourced from `static/icons/icon-512.png`.
- Test login.
- Test registration.
- Test one Rebirth Arena duel.
- Test post-match rewards.
- Test one campaign encounter.
- Test booster shop.
- Test deck builder.
- Test feedback form.
- Test export and permanent deletion with a disposable account.
- Test Android back button behavior.
- Test portrait layout.
- Test slow network behavior.

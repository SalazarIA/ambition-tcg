# Ambitionz — Internal Testing Guide

## Release Identity

- Track: Google Play **Internal testing**
- Release label: `beta.2`
- Web runtime: `v132_PVP_ROBUST`
- Package: `com.ambitionzgame.app`
- Candidate `versionName`: `1.0.0-beta.2`
- Candidate `versionCode`: `2`
- Canonical server: `https://ambitionzgame.com`

`versionCode 2` must still be confirmed as unused in Play Console. Google Play does not accept a version code that was uploaded previously, even if that release was discarded.

## Candidate Artifact

`mobile/AmbitionzAndroid/android/app/build/outputs/bundle/release/app-release.aab`

Artifact audit from June 20, 2026; hash and file presence rechecked on June 28, 2026:

- SHA-256: `4beae3778a59d074fdbab9d7d1b9ca56df8901f79e2fa67730995310c77a297b`
- JAR signature verification: passed
- Embedded Capacitor server: `https://ambitionzgame.com`
- Embedded app ID: `com.ambitionzgame.app`
- Source configuration: `minSdk 24`, `compileSdk 36`, `targetSdk 36`
- Native `.so` libraries in the AAB: none observed

No upload was performed during this audit.

## Main Test Areas

1. Join the internal test with the invited Google account and install from Google Play.
2. Confirm the app launches into Ambitionz Rebirth without browser chrome.
3. Confirm the support page reports `v132_PVP_ROBUST`.
4. Create an account, sign out, and sign back in.
5. Start and finish a Rebirth clash against the bot.
6. Confirm post-match XP, rewards, match history, and saved progression.
7. Start the campaign and verify that encounter progress is persisted.
8. Open the collection and edit a 30-card deck.
9. Open a free beta booster and confirm that the collection updates.
10. Check rewards, profile, ranking, and wallet values.
11. If a second invited tester account is available, attempt the experimental PvP queue and record whether matchmaking starts, times out, or completes a duel.
12. Submit feedback through `/rebirth/support`.
13. Test Android back navigation and portrait layout.
14. Test slow or interrupted connectivity and recovery.
15. Close and reopen the app; confirm login and progression persistence.
16. With a disposable account, verify export and account deletion separately.

## Onda 1–3 + PvP Coverage

- **Onda 1 — observability, bot honesty, determinism:** complete at least two matches and report invalid actions, impossible bot information, frozen turns, mismatched rewards, or result/replay inconsistencies.
- **Onda 2 — archetype diversity:** when the required cards are available, exercise WATER at high HP, SHADOW at low HP, and SIEGE/Cerco against a Guard-heavy defender.
- **Onda 3 — reactive interaction:** arm a trap and verify it triggers only when its owner is attacked; cast a unit-targeted spell; if the bot arms a face-down card, verify the interrupt resolves without blocking the turn.

The card-specific scenarios are directed coverage, not a prerequisite for every tester account. Record “cards unavailable” instead of fabricating state.

## Pass Criteria

The internal beta passes when:

- Installation and updates work through the Play opt-in flow.
- Launch, registration, login, logout, and session restoration work.
- A bot clash and a campaign encounter can start and finish.
- Experimental PvP is attempted with two invited accounts when available, with any queue timeout or duel failure recorded.
- Deck, collection, booster, reward, profile, and ranking pages load without a blocking error.
- Progression changes persist after reopening the app.
- Feedback can be submitted and includes runtime context.
- No critical portrait-layout or Android back-navigation issue blocks play.
- Account deletion is discoverable in the app and through `https://ambitionzgame.com/data-deletion`.

## Known Gates

- The concurrently updated Play icon and feature graphic now meet the documented dimensions, color-mode, alpha, and file-size requirements.
- Final owner approval is still needed for feature-graphic crop/text legibility and icon readability at small sizes; Play Console validation is authoritative.
- Production must be revalidated after the legal-copy normalization is deployed.
- Play Console access, package ownership, `versionCode` availability, declarations, review status, and the tester opt-in link were not verified.

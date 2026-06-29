# Ambitionz — Google Play Upload Checklist

Target: **Internal testing**, release `beta.2`, runtime `v131_PVP_POLISH`.

No upload was performed during the June 28, 2026 audit.

## A. Verified in the Repository and Production

- [x] `app-release.aab` exists.
- [x] AAB SHA-256 is `4beae3778a59d074fdbab9d7d1b9ca56df8901f79e2fa67730995310c77a297b`.
- [x] Candidate source configuration uses `versionCode 2`.
- [x] Candidate source configuration uses `versionName 1.0.0-beta.2`.
- [x] Candidate package is `com.ambitionzgame.app`.
- [x] Candidate targets `https://ambitionzgame.com`.
- [x] Candidate source configuration uses `targetSdk 36`.
- [x] AAB signature verification passes.
- [x] No native `.so` libraries were observed in the AAB.
- [x] Privacy, terms, support, and account-deletion pages load over HTTPS.
- [x] Production support exposes `v131_PVP_POLISH`.
- [x] Current Rebirth screenshots are `1080x1920` RGB PNGs without alpha.
- [x] Current feature graphic is `1024x500` RGB PNG without alpha.
- [x] Current Play icon is `512x512` RGBA PNG and below 1,024 KB.
- [x] Listing describes PvP only as experimental and avoids offline play, exact card-count, and real-money-purchase claims.
- [x] Release notes cover Onda 1–3 plus experimental PvP and fit the 500-character pt-BR limit.

## B. Owner/Console Confirmation Before Upload

- [ ] Confirm the selected Play app already owns, or will permanently use, `com.ambitionzgame.app`.
- [ ] Confirm `versionCode 2` has never been uploaded to that Play app.
- [ ] Confirm the uploader has release permission and the intended Play App Signing setup.
- [ ] Confirm the tester owner/list and feedback owner.

Do not upload until the package and version code are confirmed. The package becomes fixed on first artifact upload.

## C. Store-Listing Asset Approval

- [x] Feature graphic replaced with current dark/gold Rebirth art.
- [x] Feature graphic exported as `1024x500` 24-bit PNG without alpha.
- [x] Play icon exported as `512x512` 32-bit PNG with alpha.
- [ ] Owner approves feature-graphic crop and text legibility in the Play preview.
- [ ] Owner approves the icon's rounded silhouette and small wordmark at small sizes.
- [x] Keep the six current screenshots; upload in the order from `PLAY_SCREENSHOT_GUIDE.md`.
- [ ] Add alt text for every screenshot and the feature graphic.

No technical format blocker remains. Play Console image validation and final visual approval are still required.

## D. Play Console App Setup

- [ ] Select the existing app or create it only after section B is complete.
- [ ] App name: Ambitionz.
- [ ] Default language: Portuguese (Brazil), matching the current production UI.
- [ ] App/game: Game.
- [ ] Free/paid: Free.
- [ ] Category: Card.
- [ ] Contact email and website added.
- [ ] Privacy policy added.
- [x] Public account-deletion page responds over HTTPS.
- [ ] Account-deletion URL entered in Data safety when that form becomes required.
- [ ] Main store listing completed with the validated assets.
- [ ] Ads declaration completed accurately.
- [ ] Target audience and content completed accurately.
- [ ] Content rating questionnaire completed.
- [ ] App access includes reusable credentials and English instructions that work globally without OTP/2FA blockers.
- [ ] Any declaration requested from the uploaded AAB completed accurately.
- [ ] Data safety left deferred only if the app is exclusively active on Internal testing.

## E. Create and Validate the Release

- [ ] Open **Testing > Internal testing**.
- [ ] Create release `beta.2`.
- [ ] app-release.aab uploaded.
- [ ] Upload result confirms package `com.ambitionzgame.app`, `versionCode 2`, and target API 36.
- [ ] pt-BR release notes added from `COPY_PASTE_RELEASE_NOTES.txt`.
- [ ] Play's 16 KB compatibility result passes.
- [ ] Device catalog and supported-device changes reviewed.
- [ ] All blocking errors, policy issues, and required declarations resolved.
- [ ] Pre-launch report reviewed if generated.
- [ ] Release reviewed and rollout to Internal testing started.
- [ ] Changes sent for review if the Console requests review.

## F. Configure and Invite Testers

- [ ] Tester list contains at most 100 Google accounts.
- [ ] Feedback URL is `https://ambitionzgame.com/rebirth/support`.
- [ ] Internal release shows as available before the invite is sent.
- [ ] Opt-in link and `COPY_PASTE_TESTER_INVITE.txt` sent to testers.
- [ ] Testers instructed to use the same invited account for opt-in and Play Store installation.
- [ ] Testers instructed not to sideload an APK for this distribution test.
- [ ] Tester matrix records account, device, Android version, install/update status, and checklist result.
- [ ] If two invited accounts are available, testers attempt PvP queue/duel and record timeout or completion.

## G. Minimum Acceptance Before Expanding the List

- [ ] Install/update from Google Play succeeds on at least one supported Android device.
- [ ] Cold launch reaches Rebirth without browser chrome.
- [ ] Registration, login, logout, and session restoration pass.
- [ ] One Arena clash and one campaign encounter complete.
- [ ] XP, rewards, history, deck, collection, and booster state persist after reopen.
- [ ] Android Back, portrait layout, interrupted network, and recovery pass.
- [ ] In-app feedback reaches the support flow.
- [ ] Export and permanent deletion pass with a disposable account.
- [ ] Directed Onda 2–3 checks attempted or marked “cards unavailable”.

## Internal Testing Rules

- [x] The 12-testers/14-days rule belongs to qualifying closed testing for production access, not to this internal release.
- [ ] If any closed, open, or production track becomes active, complete and approve Data safety before proceeding.
- [ ] Do not share the internal opt-in link publicly.

## Required URLs

- Website: `https://ambitionzgame.com`
- Privacy: `https://ambitionzgame.com/privacy`
- Terms: `https://ambitionzgame.com/terms`
- Support: `https://ambitionzgame.com/rebirth/support`
- Account deletion: `https://ambitionzgame.com/data-deletion`

## Artifact

Upload only:

`mobile/AmbitionzAndroid/android/app/build/outputs/bundle/release/app-release.aab`

Never upload `.jks`, `key.properties`, or source code.

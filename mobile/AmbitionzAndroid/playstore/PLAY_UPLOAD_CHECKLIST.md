# Ambitionz — Google Play Upload Checklist

Target: **Internal testing**, release `beta.2`, runtime `v107_LOGIC_SEARCH`.

No upload was performed during the June 20, 2026 audit.

## Verified Read-Only

- [x] `app-release.aab` exists.
- [x] Candidate source configuration uses `versionCode 2`.
- [x] Candidate source configuration uses `versionName 1.0.0-beta.2`.
- [x] Candidate package is `com.ambitionzgame.app`.
- [x] Candidate targets `https://ambitionzgame.com`.
- [x] Candidate source configuration uses `targetSdk 36`.
- [x] AAB signature verification passes.
- [x] No native `.so` libraries were observed in the AAB.
- [x] Privacy, terms, support, and account-deletion pages load over HTTPS.
- [x] Production support exposes `v107_LOGIC_SEARCH`.
- [x] Current Rebirth screenshots are `1080x1920` RGB PNGs without alpha.

## Blocking Before Upload

- [ ] Confirm in Play Console that `versionCode 2` has never been uploaded.
- [ ] Confirm the Play app package is or will permanently be `com.ambitionzgame.app`.
- [ ] Re-export the feature graphic as JPEG or 24-bit PNG without alpha.
- [ ] Re-export/verify the Play icon as a 32-bit PNG with alpha.
- [ ] Run the candidate on at least one supported Android device or emulator.
- [ ] Confirm install, launch, registration, login, clash completion, persistence, and feedback.
- [ ] Confirm Play's 16 KB compatibility validation passes.

## Play Console Setup
- [ ] Create app in Play Console.
- [ ] App name: Ambitionz.
- [ ] Default language: Portuguese (Brazil), matching the current production UI.
- [ ] App/game: Game.
- [ ] Free/paid: Free.
- [ ] App access includes reusable review credentials and English instructions.
- [ ] Ads declaration completed accurately.
- [ ] Target audience and content completed accurately.
- [ ] Content rating questionnaire completed.
- [ ] Sensitive-permission declarations completed if the uploaded AAB requests any.
- [ ] Privacy policy added.
- [ ] Account deletion URL added.
- [ ] Store listing completed.
- [ ] Internal testing track selected.
- [ ] Tester emails/list added.
- [ ] Feedback channel set to `https://ambitionzgame.com/rebirth/support`.
- [ ] app-release.aab uploaded.
- [ ] Release notes added.
- [ ] Play validation errors and warnings resolved.
- [ ] Release submitted for review.
- [ ] Opt-in link shared only after the internal release is available.

## Internal Testing Rules

- [ ] Keep the internal tester list at 100 accounts or fewer.
- [ ] Testers use the same invited Google account for opt-in and Play Store installation.
- [ ] Do not apply the 12-testers/14-days closed-test rule to this internal release.
- [ ] If any closed, open, or production track becomes active, complete Data safety before proceeding.

## Required URLs
Website:
https://ambitionzgame.com

Privacy:
https://ambitionzgame.com/privacy

Terms:
https://ambitionzgame.com/terms

Support:
https://ambitionzgame.com/rebirth/support

Account deletion:
https://ambitionzgame.com/data-deletion

## Artifact
Upload:
mobile/AmbitionzAndroid/android/app/build/outputs/bundle/release/app-release.aab

Do not upload:

- .jks file
- key.properties
- source code
- an icon or feature graphic that fails Play's image-format validation

# Ambitionz — Final Internal Testing Upload Guide

This guide prepares the `beta.2` / `v107_LOGIC_SEARCH` candidate for Google Play Internal testing. The June 21, 2026 audit did not upload or publish anything.

## 1. Files to Prepare

AAB:
mobile/AmbitionzAndroid/android/app/build/outputs/bundle/release/app-release.aab

Icon:
mobile/AmbitionzAndroid/playstore/assets/icons/play-icon-512.png

Feature Graphic:
mobile/AmbitionzAndroid/playstore/assets/feature_graphic/feature-graphic-1024x500.png

Screenshots:
mobile/AmbitionzAndroid/playstore/assets/screenshots/*.png

Copy/paste texts:

- Store listing: `mobile/AmbitionzAndroid/playstore/texts/COPY_PASTE_STORE_LISTING.txt`
- Release notes: `mobile/AmbitionzAndroid/playstore/texts/COPY_PASTE_RELEASE_NOTES.txt`
- Tester invite: `mobile/AmbitionzAndroid/playstore/texts/COPY_PASTE_TESTER_INVITE.txt`

## 2. Store-Listing Asset Status

- **Feature graphic:** current asset is dark/gold Rebirth artwork, `1024x500` RGB PNG without alpha and below the Play size limit.
- **Play icon:** current asset is a `512x512` RGBA PNG below the Play size limit.
- **Screenshots:** ready in format. Upload them in the order documented in `PLAY_SCREENSHOT_GUIDE.md`, with alt text.

No image-format blocker remains after the concurrent June 21 asset update. Before submission, the owner should still approve the feature-graphic crop/text at Play preview size and the icon's rounded silhouette plus small wordmark at small sizes. Play Console validation remains definitive.

## 3. Confirm Identity Before First Upload

- Select the existing Ambitionz app if it already owns `com.ambitionzgame.app`.
- If no app exists, create it only after the owner confirms that `com.ambitionzgame.app` is the permanent package.
- Confirm that `versionCode 2` has never been uploaded to this Play app.
- Confirm the release artifact SHA-256 is `4beae3778a59d074fdbab9d7d1b9ca56df8901f79e2fa67730995310c77a297b`.

The package becomes fixed as soon as the first artifact is uploaded. A reused `versionCode` requires a new build and is outside this documentation-only scope.

## 4. Configure the Store and App Content

1. Set app name `Ambitionz`, default language `Portuguese (Brazil)`, type `Game`, category `Card`, and price `Free`.
2. Paste the pt-BR listing and upload the validated icon, feature graphic, and screenshots.
3. Add the contact email, website, and privacy policy. Keep terms, support, and account-deletion pages public; use Support as the tester feedback URL and enter the deletion URL in Data safety when that form becomes required.
4. Complete Ads, Target audience and content, and Content rating accurately.
5. Add App access credentials and instructions if review must reach signed-in progression.
6. Complete any declaration requested from the uploaded AAB. No high-risk permission is currently expected, but the Play result is authoritative.
7. Keep Data safety deferred only if this app remains exclusively active on Internal testing.

## Required Review Access

Because saved progression and account tools require authentication, provide Play reviewers with reusable credentials and English access instructions. The credentials must remain valid, work from any location, and avoid OTP, 2FA, or expiring-password blockers.

## 5. Create the Internal Release

1. Open **Testing > Internal testing**.
2. Select or create the tester list, with at most 100 accounts.
3. Set feedback to `https://ambitionzgame.com/rebirth/support`.
4. Create release `beta.2` and upload the AAB.
5. Paste the pt-BR release notes; the supplied text is under the 500-character limit.
6. Resolve all upload errors, policy blockers, device exclusions, and 16 KB compatibility results.
7. Review the release, start rollout to Internal testing, and send changes for review if the Console requests it.
8. Wait until the release is available before sharing the opt-in link.

## 6. Invite and Verify Testers

1. Send the opt-in link and `COPY_PASTE_TESTER_INVITE.txt`.
2. Testers must open the link and Play Store with the same invited Google account.
3. Testers must install from Google Play, not from a sideloaded APK.
4. Record tester email, device, Android version, install/update result, and checklist status.
5. Run the core checklist on at least one supported device before broadening the list.
6. Use disposable accounts for export and permanent deletion tests.

## Internal-Only Rules

- Internal testing supports up to 100 testers.
- The 12-testers-for-14-days rule applies to qualifying closed tests for production access, not to this internal release.
- Data safety is exempt only while the app is exclusively active on Internal testing.
- Store listing assets are shared across test tracks after they are added.

# Ambitionz — Internal Testing Console Preparation Guide

This guide prepares the `beta.2` / `v107_LOGIC_SEARCH` candidate for Google Play Internal testing. The June 20, 2026 audit did not upload or publish anything.

## Upload Files

AAB:
mobile/AmbitionzAndroid/android/app/build/outputs/bundle/release/app-release.aab

Icon:
mobile/AmbitionzAndroid/playstore/assets/icons/play-icon-512.png

Feature Graphic:
mobile/AmbitionzAndroid/playstore/assets/feature_graphic/feature-graphic-1024x500.png

Screenshots:
mobile/AmbitionzAndroid/playstore/assets/screenshots/*.png

## Asset Status

- The current Rebirth screenshots are `1080x1920`, RGB PNGs without alpha and no longer contain the legacy training/250-card surface.
- The feature graphic is `1024x500` but is RGBA; re-export it as JPEG or 24-bit PNG without alpha.
- The icon is `512x512` RGB; Play specifies a 32-bit PNG with alpha, so re-export or verify it before use.

## Copy/Paste Texts

Store listing:
mobile/AmbitionzAndroid/playstore/texts/COPY_PASTE_STORE_LISTING.txt

Release notes:
mobile/AmbitionzAndroid/playstore/texts/COPY_PASTE_RELEASE_NOTES.txt

Tester invite:
mobile/AmbitionzAndroid/playstore/texts/COPY_PASTE_TESTER_INVITE.txt

## Console Path

1. Open Google Play Console and select the existing Ambitionz app, or create it only if it does not exist.
2. Before the first artifact upload, confirm the permanent package must be `com.ambitionzgame.app`.
3. Confirm `versionCode 2` has never been uploaded to this app.
4. Complete the minimum required app-content declarations and add reviewer access instructions.
5. Add the privacy and account-deletion URLs.
6. Add the refreshed pt-BR store listing and validated current-product assets.
7. Open **Testing > Internal testing**.
8. Add an email list with up to 100 internal testers.
9. Set the feedback channel to `https://ambitionzgame.com/rebirth/support`.
10. Create a new internal release and upload the AAB.
11. Add the beta.2 release notes.
12. Resolve every Play validation error or policy warning.
13. Review the release and submit it for internal testing.
14. Share the generated opt-in link only after the release is available.

## Required Review Access

Because saved progression and account tools require authentication, provide Play reviewers with reusable credentials and English access instructions. The credentials must remain valid, work from any location, and avoid OTP or expiring-password blockers.

## Internal-Only Notes

- Internal testing supports up to 100 testers.
- The 12-testers-for-14-days rule applies to qualifying closed tests for production access, not to the internal track.
- Data safety is exempt only while the app is exclusively active on internal testing.
- The package name becomes permanent after the first artifact upload.

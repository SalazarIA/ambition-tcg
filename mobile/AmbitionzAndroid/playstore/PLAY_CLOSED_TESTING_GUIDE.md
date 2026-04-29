# Ambitionz — Closed Testing Guide

## Target
Google Play Closed Testing.

## Package
com.ambitionzgame.app

## Version
versionName: 1.0.0-beta.1
versionCode: 1

## Release Artifact
android/app/build/outputs/bundle/release/app-release.aab

## Main Test Areas
1. Install from Google Play closed testing.
2. Open app.
3. Register account.
4. Login.
5. Play training match.
6. Confirm post-match rewards.
7. Open missions.
8. Open booster shop.
9. Check collection.
10. Edit deck builder.
11. Open profile.
12. Submit feedback.
13. Test Android back button.
14. Test portrait layout.
15. Test slow connection behavior.
16. Test app reopen after closing.
17. Test login persistence.

## Pass Criteria
The beta is acceptable if:
- App installs without issue.
- App opens directly into Ambitionz.
- Core pages load on Android.
- Login and register work.
- Training match can start and finish.
- Rewards and missions update.
- Feedback can be submitted.
- No critical mobile layout break blocks play.

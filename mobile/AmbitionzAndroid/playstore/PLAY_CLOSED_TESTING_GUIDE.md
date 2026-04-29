# Ambitionz — Closed Testing Guide

## Target

Google Play Closed Testing.

## Current Android Package

com.ambitionzgame.app

## Current Version

versionName: 1.0.0-beta.1
versionCode: 1

## Release Artifact

Upload this file to Google Play Console:

android/app/build/outputs/bundle/release/app-release.aab

## Test Objective

Validate whether Ambitionz is stable enough for a first external Android beta.

## Main Test Areas

1. Install from Google Play closed testing.
2. Open app.
3. Register account.
4. Login.
5. Complete onboarding if shown.
6. Play training match.
7. Confirm post-match rewards.
8. Open Missions.
9. Claim available rewards.
10. Open Booster Shop.
11. Open booster if coins are available.
12. Check Collection.
13. Edit Deck Builder.
14. Open Profile.
15. Submit Feedback.
16. Test Android back button.
17. Test portrait layout.
18. Test slow connection behavior.
19. Test app reopen after closing.
20. Test login persistence.

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

## Fail Criteria

The release must be fixed before expansion if:
- App does not install.
- App does not open.
- Login/register breaks.
- Training cannot be completed.
- WebView is blank.
- Android back button traps the user.
- Feedback cannot be submitted.
- Layout makes combat unusable.

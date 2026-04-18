# Android Codemagic + Firebase CI/CD Plan

## Goal

Use Codemagic as the single build/distribution system, with GitHub tags as the
human-controlled release switch. Normal commits and PRs keep using GitHub
quality gates; tester builds only go out when we intentionally create a release
tag.

## Release Label Standard

Use one tag format for coordinated beta releases:

```text
field-guide-beta-v<version>+<build>
```

Example:

```text
field-guide-beta-v0.1.3+42
```

This maps directly to Flutter's shared version fields:

- `0.1.3` becomes Android `versionName` and iOS `CFBundleShortVersionString`.
- `42` becomes Android `versionCode` and iOS `CFBundleVersion`.
- The build integer must always increase. Do not reuse it.

## Current Repo Wiring

- `codemagic.yaml` now has an `android-firebase` workflow.
- `codemagic.yaml` now has tag triggers for `android-firebase` and
  `ios-testflight` using `field-guide-beta-v*`.
- Android publishes a signed release APK to Firebase App Distribution.
- Android Firebase publishing currently targets app id
  `1:860372996401:android:157920afc316bffc962010`.
- Android tester group alias expected by the workflow:
  `field-guide-android-testers`.
- Android release signing now fails on CI if Codemagic signing is missing,
  instead of silently using debug signing.

## One-Time Setup In Codemagic

1. In Codemagic, add or confirm the GitHub app/repository integration for this
   repo.
2. In Team settings, add an Android keystore under
   `codemagic.yaml settings > Code signing identities > Android keystores`.
3. Set the keystore reference name exactly to:

   ```text
   field-guide-android-upload
   ```

4. Back up the keystore file and passwords outside Codemagic. Codemagic cannot
   be used as the only copy of the signing key.
5. In Environment variables, create group `android_firebase`.
6. Add secret `ANDROID_GOOGLE_SERVICES_JSON_B64`, containing base64-encoded
   contents of `android/app/google-services.json`.

   PowerShell helper:

   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("android/app/google-services.json"))
   ```

7. In Environment variables, create group `firebase_distribution`.
8. Add secret `FIREBASE_SERVICE_ACCOUNT`, containing the Firebase service
   account JSON text.
9. Confirm the existing `supabase_credentials` group contains:
   `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and optional runtime telemetry keys.

## One-Time Setup In Firebase

1. Open Firebase Console for `field-guide-42e1a`.
2. Confirm the Android app package is:

   ```text
   com.fieldguideapp.inspector
   ```

3. Open App Distribution.
4. Create tester group alias:

   ```text
   field-guide-android-testers
   ```

5. Add the initial testers to that group.
6. Create a Google service account with the Firebase App Distribution Admin
   role.
7. Download the JSON key and place its full JSON text into Codemagic variable
   `FIREBASE_SERVICE_ACCOUNT`.

## Normal Development Flow

1. Work on feature branches.
2. Open PRs to `main`.
3. Let GitHub `Quality Gate` run on PRs.
4. Merge only after the regular checks are clean.
5. Do not create a beta tag until we want a tester build.

## Tester Release Flow

1. Decide the next public beta label, for example:

   ```text
   field-guide-beta-v0.1.3+42
   ```

2. Create the tag from the verified commit on `main`.
3. Push the tag to GitHub.

   PowerShell/Git helper:

   ```powershell
   git checkout main
   git pull --ff-only
   git tag field-guide-beta-v0.1.3+42
   git push origin field-guide-beta-v0.1.3+42
   ```

4. Codemagic sees the tag and starts:
   `ios-testflight` and `android-firebase`.
5. iOS uploads to TestFlight.
6. Android uploads to Firebase App Distribution.
7. Record the tag and Codemagic build URLs in the active release notes/tracker.

## Why APK First

Firebase App Distribution can distribute APKs directly. AAB distribution through
Firebase requires the Firebase project to be linked to Google Play, so the first
Android tester lane uses a signed APK. When Google Play internal testing is
ready, add a separate `android-play-internal` workflow that builds an AAB and
uses the same `field-guide-beta-v<version>+<build>` label.

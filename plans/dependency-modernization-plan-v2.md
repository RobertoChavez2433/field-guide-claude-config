# Full Dependency Modernization Plan (v2)

## Summary

Upgrade all direct dependencies and dev_dependencies to the latest stable versions and apply required code/config changes in PR-sized phases.

**Total Changes:**
- 27 dependency upgrades (10+ major bumps)
- 25+ files likely touched (code + native configs + docs)
- 6+ native/toolchain updates (Android/iOS/macOS tooling + Patrol CLI)

---

# Dependency Upgrade Table

| Package | Current | Target | Breaking Changes |
|---------|---------|--------|------------------|
| **app_links** | 6.3.4 | 7.0.0 | iOS 13+ / Flutter 3.38+ |
| **collection** | 1.19.0 | 1.19.1 | Patch only |
| **connectivity_plus** | 6.1.1 | 7.0.0 | Returns List; newer Android toolchain |
| **crypto** | 3.0.6 | 3.0.7 | Patch only |
| **cupertino_icons** | 1.0.8 | 1.0.8 | None |
| **device_info_plus** | 11.1.0 | 12.3.0 | Android toolchain requirements |
| **file_picker** | 8.0.0 | 10.3.10 | macOS entitlement required |
| **flutter_secure_storage** | 9.2.2 | 10.0.0 | iOS Keychain entitlement guidance |
| **geocoding** | 3.0.0 | 4.0.0 | API adjustments possible |
| **geolocator** | 13.0.2 | 14.0.2 | LocationSettings API (already in code) |
| **go_router** | 14.6.2 | 17.0.1 | Case-sensitive paths; API updates |
| **http** | 1.2.2 | 1.6.0 | Minor changes |
| **image_picker** | 1.1.2 | 1.2.1 | Patch only |
| **intl** | 0.19.0 | 0.20.2 | Minor changes |
| **path** | 1.9.0 | 1.9.1 | Patch only |
| **path_provider** | 2.1.5 | 2.1.5 | None |
| **pdf** | 3.11.1 | 3.11.3 | Patch only |
| **permission_handler** | 11.3.1 | 12.0.1 | Minor API changes |
| **printing** | 5.13.4 | 5.14.2 | Minor changes |
| **provider** | 6.1.2 | 6.1.5+1 | Patch only |
| **shared_preferences** | 2.3.4 | 2.5.4 | Async API options added |
| **sqflite** | 2.4.1 | 2.4.2 | Patch only |
| **sqflite_common_ffi** | 2.3.4 | 2.4.0+2 | Patch only |
| **supabase_flutter** | 2.8.3 | 2.12.0 | Minor changes |
| **syncfusion_flutter_pdf** | 28.2.12 | 32.1.25 | Text extraction fixes |
| **syncfusion_flutter_pdfviewer** | 28.2.12 | 32.1.25 | Widget property updates |
| **table_calendar** | 3.1.3 | 3.2.0 | Minor changes |
| **uuid** | 4.5.1 | 4.5.2 | Patch only |
| **flutter_lints** (dev) | 6.0.0 | 6.0.0 | None |
| **patrol** (dev) | 3.20.0 | 4.1.0 | $.native deprecated → $.platform.mobile |

---

# Stage 0: Toolchain & Platform Baseline (PR0)

**Logic:** Newer package versions require newer Flutter/Dart and Android build tooling. Lock this first to prevent wasted work.

## Subphase A: Toolchain Baseline
- Verify Flutter/Dart versions satisfy minimums in new packages.
- Record the toolchain in a version file or README to prevent drift.

**Files**
- `README.md`
- Optional: `.tool-versions` or `.fvmrc` (create if you want locked versions)

## Subphase B: Android Build Tooling
- Ensure Java 17 and Gradle 8.13+ are used.
- Confirm Kotlin plugin version meets device_info_plus requirements.
- Align `targetSdk` to 36 if you want full Android 16 compliance (currently 35).

**Files**
- `android/app/build.gradle.kts`
- `android/gradle/wrapper/gradle-wrapper.properties`
- `android/build.gradle.kts` or `android/build.gradle` (if present)

## Verification
```bash
flutter --version
flutter doctor -v
```

---

# Stage 1: Low-Risk Core Updates (PR1)

**Logic:** Patch/minor upgrades with near-zero API changes.

## Subphase A: pubspec.yaml Changes
```yaml
path: ^1.9.1
collection: ^1.19.1
crypto: ^3.0.7
uuid: ^4.5.2
pdf: ^3.11.3
printing: ^5.14.2
sqflite: ^2.4.2
sqflite_common_ffi: ^2.4.0+2
```

## Subphase B: Impacted Files (sanity scan only)
- `lib/services/` (SQL usage)
- `lib/features/pdf/` (printing/pdf)

## Verification
```bash
flutter pub get
flutter analyze
flutter test
```

---

# Stage 2: State & Storage Utilities (PR2)

**Logic:** Core state/prefs/security changes can ripple across many screens; isolate them.

## Subphase A: pubspec.yaml Changes
```yaml
provider: ^6.1.5+1
shared_preferences: ^2.5.4
flutter_secure_storage: ^10.0.0
```

## Subphase B: Code Review (likely minimal)
- Confirm prefs wrappers still compatible.
- If adopting new async prefs APIs, update the wrapper to avoid stale cache issues.

**Files**
- `lib/shared/services/preferences_service.dart` (if present)
- `lib/main.dart` (prefs init)

## Subphase C: Platform Security Notes
- flutter_secure_storage recommends Android backup exclusions and iOS Keychain Sharing entitlements; plan changes only if needed.

**Files**
- `android/app/src/main/AndroidManifest.xml`
- `ios/Runner/Runner.entitlements` (if added later)

## Verification
```bash
flutter analyze
flutter test test/shared/
```

---

# Stage 3: Networking & Connectivity (PR3)

**Logic:** Sync health depends on connectivity and HTTP behavior.

## Subphase A: pubspec.yaml Changes
```yaml
http: ^1.6.0
connectivity_plus: ^7.0.0
```

## Subphase B: Code Review
- Confirm `List<ConnectivityResult>` usage in `SyncService` is correct.

**Files**
- `lib/services/sync_service.dart`
- `test/services/sync_service_test.dart`

## Verification
```bash
flutter analyze
# Manual: toggle airplane mode; verify sync status changes
```

---

# Stage 4: Location, Permissions, Device Info (PR4)

**Logic:** Location flows and permission prompts must stay stable.

## Subphase A: pubspec.yaml Changes
```yaml
geolocator: ^14.0.2
geocoding: ^4.0.0
permission_handler: ^12.0.1
device_info_plus: ^12.3.0
```

## Subphase B: Code Review
- You already use `LocationSettings` in weather/photo services; verify nothing regresses.

**Files**
- `lib/features/weather/services/weather_service.dart`
- `lib/services/photo_service.dart`
- `lib/services/permission_service.dart`

## Subphase C: Android Manifest Check
- Only add `FOREGROUND_SERVICE_LOCATION` if you actually run a foreground location service.

**Files**
- `android/app/src/main/AndroidManifest.xml`

## Verification
```bash
flutter analyze
# Manual: weather fetch + photo GPS tagging
```

---

# Stage 5: Files, Media, Pickers (PR5)

**Logic:** File selection and media access are user-facing; isolate and test.

## Subphase A: pubspec.yaml Changes
```yaml
file_picker: ^10.3.10
image_picker: ^1.2.1
path_provider: ^2.1.5
```

## Subphase B: Code Review
**Files**
- `lib/features/projects/presentation/screens/project_setup_screen.dart`
- `lib/features/quantities/presentation/screens/quantities_screen.dart`
- `lib/features/toolbox/presentation/providers/form_import_provider.dart`
- `lib/features/pdf/services/pdf_service.dart`
- `lib/features/toolbox/data/services/form_pdf_service.dart`

## Subphase C: Platform Notes
- macOS entitlements are required *only if* macOS is added later.
- iOS Info.plist already includes camera/photo usage; verify if any new keys are required.

**Files**
- `ios/Runner/Info.plist`
- `macos/Runner/DebugProfile.entitlements` (conditional)
- `macos/Runner/Release.entitlements` (conditional)

## Verification
```bash
flutter analyze
# Manual: PDF file picker + image picker
```

---

# Stage 6: PDF Stack (PR6)

**Logic:** PDF import/export is critical and should be isolated for regression testing.

## Subphase A: pubspec.yaml Changes
```yaml
syncfusion_flutter_pdf: ^32.1.25
syncfusion_flutter_pdfviewer: ^32.1.25
pdf: ^3.11.3
printing: ^5.14.2
```

## Subphase B: Code Review
**Files**
- `lib/features/pdf/services/pdf_service.dart`
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/pdf/services/photo_pdf_service.dart`
- `lib/features/pdf/services/parsers/column_layout_parser.dart`
- `lib/features/pdf/services/parsers/clumped_text_parser.dart`
- `lib/features/toolbox/data/services/form_pdf_service.dart`
- `lib/features/toolbox/data/services/field_discovery_service.dart`
- `lib/features/toolbox/presentation/widgets/form_preview_tab.dart`

## Verification
```bash
flutter test test/features/pdf/
# Manual: PDF import (bid schedule)
# Manual: PDF export (IDR report)
```

---

# Stage 7: Navigation & Deep Links (PR7)

**Logic:** Router + deep link packages should be updated together to avoid auth callback regressions.

## Subphase A: pubspec.yaml Changes
```yaml
go_router: ^17.0.1
app_links: ^7.0.0
```

## Subphase B: Code Review
- Verify `state.matchedLocation` compatibility with go_router 17.
- Confirm deep link handler still triggers on cold start and warm start.

**Files**
- `lib/core/router/app_router.dart`
- `lib/main.dart`

## Verification
```bash
flutter analyze
# Manual: login/logout redirects, deep link auth callback
```

---

# Stage 8: Supabase + App Links Safety (PR8)

**Logic:** Auth and session recovery are critical; keep this isolated.

## Subphase A: pubspec.yaml Changes
```yaml
supabase_flutter: ^2.12.0
```

## Subphase B: Code Review
**Files**
- `lib/main.dart`
- `lib/core/config/supabase_config.dart`

## Verification
```bash
flutter analyze
# Manual: sign-in, sign-out, deep link session recovery
```

---

# Stage 9: UI + Date/Calendar (PR9)

**Logic:** UI-level dependencies can affect screens and widget tests.

## Subphase A: pubspec.yaml Changes
```yaml
table_calendar: ^3.2.0
intl: ^0.20.2
```

## Subphase B: Code Review
**Files**
- `lib/features/entries/presentation/screens/home_screen.dart` (calendar usage)
- `lib/features/entries/presentation/providers/calendar_format_provider.dart`

## Verification
```bash
flutter test test/features/entries/
```

---

# Stage 10: Test Tooling (PR10)

**Logic:** Patrol 4.x changes are wide-reaching and should be isolated.

## Subphase A: pubspec.yaml Changes
```yaml
patrol: ^4.1.0
```

## Subphase B: Code Changes
- Replace `$.native` usages with `$.platform.mobile`.
- Configure Patrol CLI test directory if it defaults away from `integration_test`.

**Files**
- `integration_test/patrol/helpers/patrol_test_helpers.dart`
- `integration_test/patrol/isolated/*.dart`
- `integration_test/patrol/e2e_tests/*.dart`
- `integration_test/patrol/README.md`
- `integration_test/patrol/isolated/README.md`
- `pubspec.yaml` (Patrol CLI config)

## Verification
```bash
dart pub global activate patrol_cli
pwsh -File run_patrol_batched.ps1
```

---

# Native Configuration Updates

## Android: `android/app/build.gradle.kts`

Verify or update:
```kotlin
android {
    compileSdk = 36
    defaultConfig {
        minSdk = 24
        targetSdk = 36
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
```

## Android: Gradle Wrapper
```properties
distributionUrl=https\://services.gradle.org/distributions/gradle-8.14-all.zip
```

## iOS (conditional)
- Ensure iOS deployment target meets package minimums (app_links and shared_preferences require newer iOS).
- Confirm `Info.plist` privacy keys are present (camera/photos/location already included).

**Files**
- `ios/Runner/Info.plist`
- `ios/Podfile` (if present; may need to set platform)

## macOS (conditional)
- If macOS platform is added later, add file picker entitlement:
```xml
<key>com.apple.security.files.user-selected.read-only</key>
<true/>
```
**Files**
- `macos/Runner/DebugProfile.entitlements`
- `macos/Runner/Release.entitlements`

---

# Complete pubspec.yaml Diff (Target State)

```yaml
dependencies:
  cupertino_icons: ^1.0.8
  provider: ^6.1.5+1
  go_router: ^17.0.1
  sqflite: ^2.4.2
  sqflite_common_ffi: ^2.4.0+2
  path: ^1.9.1
  supabase_flutter: ^2.12.0
  app_links: ^7.0.0
  table_calendar: ^3.2.0
  intl: ^0.20.2
  pdf: ^3.11.3
  printing: ^5.14.2
  syncfusion_flutter_pdf: ^32.1.25
  syncfusion_flutter_pdfviewer: ^32.1.25
  image_picker: ^1.2.1
  geolocator: ^14.0.2
  geocoding: ^4.0.0
  connectivity_plus: ^7.0.0
  http: ^1.6.0
  path_provider: ^2.1.5
  file_picker: ^10.3.10
  permission_handler: ^12.0.1
  device_info_plus: ^12.3.0
  uuid: ^4.5.2
  shared_preferences: ^2.5.4
  collection: ^1.19.1
  crypto: ^3.0.7
  flutter_secure_storage: ^10.0.0

dev_dependencies:
  flutter_lints: ^6.0.0
  patrol: ^4.1.0
```

---

# Implementation Checklist

## Stage 0: Toolchain
- [ ] Verify Flutter/Dart versions
- [ ] Confirm Android Gradle + Kotlin versions
- [ ] Commit: "chore: lock toolchain baseline"

## Stage 1: Low-Risk Core
- [ ] Update basic utilities (path, collection, crypto, uuid, pdf, printing, sqflite)
- [ ] `flutter analyze` + `flutter test`
- [ ] Commit: "chore: update core utilities"

## Stage 2: State & Storage
- [ ] Update provider/shared_preferences/flutter_secure_storage
- [ ] Verify prefs + secure storage flows
- [ ] Commit: "chore: update state and storage utilities"

## Stage 3: Networking
- [ ] Update http + connectivity_plus
- [ ] Verify offline/online sync
- [ ] Commit: "chore: update networking stack"

## Stage 4: Location/Permissions/Device Info
- [ ] Update geolocator/geocoding/permission_handler/device_info_plus
- [ ] Verify location flows
- [ ] Commit: "chore: update location and permissions"

## Stage 5: Files & Media
- [ ] Update file_picker/image_picker/path_provider
- [ ] Verify file selection + image capture
- [ ] Commit: "chore: update pickers"

## Stage 6: PDF
- [ ] Update syncfusion + pdf/printing
- [ ] Verify PDF import/export
- [ ] Commit: "chore: update pdf stack"

## Stage 7: Navigation
- [ ] Update go_router + app_links
- [ ] Verify deep links + redirects
- [ ] Commit: "chore: update routing"

## Stage 8: Supabase
- [ ] Update supabase_flutter
- [ ] Verify auth/session flows
- [ ] Commit: "chore: update supabase"

## Stage 9: UI + Calendar
- [ ] Update table_calendar + intl
- [ ] Verify calendar screens
- [ ] Commit: "chore: update calendar + intl"

## Stage 10: Patrol
- [ ] Update patrol + replace $.native usages
- [ ] Run Patrol tests
- [ ] Commit: "chore: update patrol to v4"

## Final
- [ ] Full regression test on device
- [ ] Build release: `flutter build apk --release`
- [ ] Commit: "chore: complete dependency modernization"

---

# Rollback Plan

If a stage breaks the build or tests:

1. Revert the stage commit(s).
2. Run `flutter pub get`.
3. Re-run the stage’s verification steps to confirm rollback.

---

# Sources

- go_router changelog: https://pub.dev/packages/go_router/changelog
- app_links package: https://pub.dev/packages/app_links
- shared_preferences package: https://pub.dev/packages/shared_preferences
- connectivity_plus package: https://pub.dev/packages/connectivity_plus
- device_info_plus package: https://pub.dev/packages/device_info_plus
- geolocator package: https://pub.dev/packages/geolocator
- geocoding package: https://pub.dev/packages/geocoding
- file_picker package: https://pub.dev/packages/file_picker
- permission_handler package: https://pub.dev/packages/permission_handler
- flutter_secure_storage package: https://pub.dev/packages/flutter_secure_storage
- syncfusion_flutter_pdf package: https://pub.dev/packages/syncfusion_flutter_pdf
- syncfusion_flutter_pdfviewer package: https://pub.dev/packages/syncfusion_flutter_pdfviewer
- printing package: https://pub.dev/packages/printing
- pdf package: https://pub.dev/packages/pdf
- table_calendar package: https://pub.dev/packages/table_calendar
- intl package: https://pub.dev/packages/intl
- provider package: https://pub.dev/packages/provider
- patrol package: https://pub.dev/packages/patrol

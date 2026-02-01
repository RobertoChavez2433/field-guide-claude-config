# Full Dependency Modernization Plan

## Summary

Comprehensive upgrade of all dependencies to latest stable versions with required code changes.

**Total Changes:**
- 12 package upgrades (8 major version bumps)
- 18+ files requiring code modifications
- 4 native configuration updates

---

# Dependency Upgrade Table

| Package | Current | Target | Breaking Changes |
|---------|---------|--------|------------------|
| **go_router** | 14.6.2 | 17.0.1 | Case-sensitive paths, GoRouteData changes |
| **syncfusion_flutter_pdf** | 28.2.12 | 32.1.25 | Text extraction fixes |
| **syncfusion_flutter_pdfviewer** | 28.2.12 | 32.1.25 | Widget property updates |
| **file_picker** | 8.0.0 | 10.3.10 | macOS entitlement required |
| **geolocator** | 13.0.2 | 14.0.2 | LocationSettings API change |
| **connectivity_plus** | 6.1.1 | 7.0.0 | Returns List instead of single result |
| **permission_handler** | 11.3.1 | 12.0.1 | Minor API changes |
| **patrol** | 3.20.0 | 4.1.0 | $.native deprecated → $.platform.mobile |
| **supabase_flutter** | 2.8.3 | 2.12.0 | Minor improvements |
| **image_picker** | 1.1.2 | 1.2.1 | Patch only |
| **provider** | 6.1.2 | 6.1.5 | Patch only |
| **sqflite** | 2.4.1 | 2.4.2 | Patch only |

---

# Stage 1: Low-Risk Updates (No Code Changes)

## pubspec.yaml Changes
```yaml
# Line 39
provider: ^6.1.5

# Line 45
sqflite: ^2.4.2

# Line 66
image_picker: ^1.2.1

# Line 50
supabase_flutter: ^2.12.0
```

## Verification
```bash
flutter pub get
flutter analyze
flutter test
```

---

# Stage 2: Syncfusion Upgrade (PDF Fix Priority)

## pubspec.yaml Changes
```yaml
# Lines 62-63
syncfusion_flutter_pdf: ^32.1.25
syncfusion_flutter_pdfviewer: ^32.1.25
```

## Code Changes Required: NONE EXPECTED
Syncfusion maintains backward compatibility. The upgrade includes text extraction fixes.

## Files to Test (11 files use Syncfusion)
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
# Manual: Test PDF import with bid schedule PDFs
# Manual: Test PDF export (IDR report)
# Manual: Test form preview tab
```

---

# Stage 3: Geolocator Upgrade

## pubspec.yaml Changes
```yaml
# Line 69
geolocator: ^14.0.2
```

## Code Changes Required

### File: `lib/features/weather/services/weather_service.dart`
**Lines 90-94** - Update getCurrentPosition call:

```dart
// BEFORE (v13)
final position = await Geolocator.getCurrentPosition(
  desiredAccuracy: LocationAccuracy.medium,
  timeLimit: const Duration(seconds: 10),
);

// AFTER (v14) - Use LocationSettings
final position = await Geolocator.getCurrentPosition(
  locationSettings: const LocationSettings(
    accuracy: LocationAccuracy.medium,
    timeLimit: Duration(seconds: 10),
  ),
);
```

### File: `lib/services/photo_service.dart`
**Lines 229-234** - Same change:

```dart
// BEFORE (v13)
final position = await Geolocator.getCurrentPosition(
  desiredAccuracy: LocationAccuracy.medium,
  timeLimit: const Duration(seconds: 10),
);

// AFTER (v14)
final position = await Geolocator.getCurrentPosition(
  locationSettings: const LocationSettings(
    accuracy: LocationAccuracy.medium,
    timeLimit: Duration(seconds: 10),
  ),
);
```

### File: `android/app/src/main/AndroidManifest.xml`
**Add for Android 14+ background location** (if needed):
```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION"/>
```

## Verification
```bash
flutter analyze
# Manual: Test weather fetch with GPS
# Manual: Test photo capture with GPS tagging
```

---

# Stage 4: Connectivity Plus Upgrade

## pubspec.yaml Changes
```yaml
# Line 73
connectivity_plus: ^7.0.0
```

## Code Changes Required

### File: `lib/services/sync_service.dart`

**Lines 194-207** - Update stream listener (ALREADY CORRECT):
```dart
// Current code already handles List<ConnectivityResult>
Connectivity().onConnectivityChanged.listen((results) {
  final isNowOnline = !results.contains(ConnectivityResult.none);
  // ... rest of code
});
```

**Lines 210-215** - Update checkConnectivity (ALREADY CORRECT):
```dart
// Current code already handles List<ConnectivityResult>
Connectivity().checkConnectivity().then((results) {
  _isOnline = !results.contains(ConnectivityResult.none);
  // ...
});
```

**NOTE**: Your code already uses the v7.0 API pattern (List<ConnectivityResult>). Verify this during testing.

## Verification
```bash
flutter analyze
# Manual: Toggle airplane mode, verify sync status updates
```

---

# Stage 5: File Picker Upgrade

## pubspec.yaml Changes
```yaml
# Line 78
file_picker: ^10.3.10
```

## Code Changes Required

### macOS Entitlement (Required for macOS builds)
**File: `macos/Runner/DebugProfile.entitlements`** and **`macos/Runner/Release.entitlements`**

Add if not present:
```xml
<key>com.apple.security.files.user-selected.read-only</key>
<true/>
```

## Files Using file_picker (5 files - verify API compatibility)
- `lib/features/projects/presentation/screens/project_setup_screen.dart:611-621`
- `lib/features/quantities/presentation/screens/quantities_screen.dart:302-312`
- `lib/features/toolbox/presentation/providers/form_import_provider.dart:39-57`
- `lib/features/pdf/services/pdf_service.dart:420-431, 463`
- `lib/features/toolbox/data/services/form_pdf_service.dart`

## API Pattern (should remain compatible)
```dart
final result = await FilePicker.platform.pickFiles(
  type: FileType.custom,
  allowedExtensions: ['pdf'],
  withData: true,
);
```

## Verification
```bash
flutter analyze
# Manual: Test PDF import file selection
# Manual: Test PDF export save dialog
```

---

# Stage 6: Permission Handler Upgrade

## pubspec.yaml Changes
```yaml
# Line 79
permission_handler: ^12.0.1
```

## Code Changes Required: LIKELY NONE

Current usage in `lib/services/permission_service.dart` uses stable APIs:
- `Permission.manageExternalStorage.status`
- `Permission.storage.status`
- `.request()` method
- `openAppSettings()`

## Verification
```bash
flutter analyze
# Manual: Test storage permission flow on Android
```

---

# Stage 7: go_router Upgrade (HIGH RISK)

## pubspec.yaml Changes
```yaml
# Line 42
go_router: ^17.0.1
```

## Breaking Changes to Address

### 1. Case-Sensitive Paths (v15+)
Routes are now case-sensitive by default. Verify all route paths use consistent casing.

**File: `lib/core/router/app_router.dart`**
- All paths already use lowercase (e.g., `/login`, `/calendar`, `/settings`)
- No changes needed unless routes are accessed with different casing elsewhere

### 2. GoRouteData Changes (v15+)
If using type-safe routing with `go_router_builder`, update to `go_router_builder: ^3.1.0`.
- **Current codebase does NOT use go_router_builder** - no changes needed

### 3. Minimum SDK
Requires Flutter 3.29+, Dart 3.7+
- Verify your Flutter version: `flutter --version`

## Files Using go_router (18 files)

### Core Router
- `lib/core/router/app_router.dart` (326 lines)
  - Router configuration
  - Redirect logic (lines 34-54)
  - Route definitions (lines 57-254)
  - ScaffoldWithNavBar (lines 259-326)

### Feature Screens (17 files)
1. `lib/features/auth/presentation/screens/login_screen.dart`
2. `lib/features/auth/presentation/screens/register_screen.dart`
3. `lib/features/auth/presentation/screens/forgot_password_screen.dart`
4. `lib/features/entries/presentation/screens/home_screen.dart`
5. `lib/features/entries/presentation/screens/entry_wizard_screen.dart`
6. `lib/features/entries/presentation/screens/entries_list_screen.dart`
7. `lib/features/entries/presentation/screens/report_screen.dart`
8. `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`
9. `lib/features/projects/presentation/screens/project_list_screen.dart`
10. `lib/features/projects/presentation/screens/project_setup_screen.dart`
11. `lib/features/quantities/presentation/screens/quantities_screen.dart`
12. `lib/features/settings/presentation/widgets/sign_out_dialog.dart`
13. `lib/features/toolbox/presentation/screens/toolbox_home_screen.dart`
14. `lib/features/toolbox/presentation/screens/forms_list_screen.dart`
15. `lib/features/toolbox/presentation/screens/form_fill_screen.dart`
16. `lib/features/toolbox/presentation/screens/form_import_screen.dart`
17. `lib/features/toolbox/presentation/screens/field_mapping_screen.dart`

## API Patterns Used (verify compatibility)

### Navigation Methods
```dart
context.goNamed('dashboard')
context.pushNamed('report', pathParameters: {'entryId': id})
context.push('/forgot-password')
context.pushReplacementNamed('report', pathParameters: {...})
context.pushNamed<bool>('preview', extra: data)  // Returns value
```

### State Access
```dart
state.pathParameters['projectId']
state.uri.queryParameters['tab']
state.extra as PdfImportResult
GoRouterState.of(context).uri.path
```

### Redirect Function
```dart
redirect: (context, state) {
  final isAuthenticated = ...;
  final isAuthRoute = state.matchedLocation.startsWith('/login');
  if (!isAuthenticated && !isAuthRoute) return '/login';
  return null;
}
```

## Verification Strategy
1. Run `flutter analyze` - fix any deprecation warnings
2. Test all navigation flows:
   - Auth: Login → Home, Logout → Login
   - Bottom nav: Dashboard ↔ Calendar ↔ Projects ↔ Settings
   - Deep navigation: Project → Entry → Report
   - Back navigation: Verify back button behavior
   - Route params: Entry wizard with date/location params
   - Extra data: PDF import preview with PdfImportResult
3. Test deep links if applicable

---

# Stage 8: Patrol Upgrade (Testing)

## pubspec.yaml Changes
```yaml
# Line 105
patrol: ^4.1.0
```

## Breaking Changes

### Deprecated: `$.native` and `$.native2`
Replace with `$.platform.mobile`:

```dart
// BEFORE (v3)
await $.native.pressBack();
await $.native.grantPermissionWhenInUse();

// AFTER (v4)
await $.platform.mobile.pressBack();
await $.platform.mobile.grantPermissionWhenInUse();
```

## Files to Update
Search for `$.native` in `test/e2e/` directory:

```bash
grep -r "\.native" test/e2e/
```

### Common Replacements
| Old (v3) | New (v4) |
|----------|----------|
| `$.native.pressBack()` | `$.platform.mobile.pressBack()` |
| `$.native.grantPermissionWhenInUse()` | `$.platform.mobile.grantPermissionWhenInUse()` |
| `$.native.enableWifi()` | `$.platform.mobile.enableWifi()` |
| `$.native.disableWifi()` | `$.platform.mobile.disableWifi()` |

## Verification
```bash
# Update patrol_cli too
dart pub global activate patrol_cli

# Run E2E tests
pwsh -File run_patrol_batched.ps1
```

---

# Native Configuration Updates

## Android: `android/app/build.gradle.kts`

Verify these settings meet requirements:
```kotlin
android {
    compileSdk = 36  // Current: 36 ✓

    defaultConfig {
        minSdk = 24      // Current: 24 ✓
        targetSdk = 36   // Current: 36 ✓
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17  // Required for connectivity_plus 7
        targetCompatibility = JavaVersion.VERSION_17
    }
}
```

## Android: `android/gradle.properties`

Verify Gradle version:
```properties
# Should be 8.4+ for connectivity_plus 7
distributionUrl=https\://services.gradle.org/distributions/gradle-8.14-all.zip
```

## macOS: Entitlements

**Files:**
- `macos/Runner/DebugProfile.entitlements`
- `macos/Runner/Release.entitlements`

Add for file_picker:
```xml
<key>com.apple.security.files.user-selected.read-only</key>
<true/>
```

---

# Complete pubspec.yaml Diff

```yaml
dependencies:
  # State Management
  provider: ^6.1.5              # was ^6.1.2

  # Navigation
  go_router: ^17.0.1            # was ^14.6.2 ⚠️ HIGH RISK

  # Database
  sqflite: ^2.4.2               # was ^2.4.1

  # Cloud Backend
  supabase_flutter: ^2.12.0     # was ^2.8.3

  # PDF
  syncfusion_flutter_pdf: ^32.1.25        # was ^28.2.12
  syncfusion_flutter_pdfviewer: ^32.1.25  # was ^28.2.12

  # Camera & Photos
  image_picker: ^1.2.1          # was ^1.1.2

  # GPS Location
  geolocator: ^14.0.2           # was ^13.0.2

  # Network & Connectivity
  connectivity_plus: ^7.0.0     # was ^6.1.1

  # File System
  file_picker: ^10.3.10         # was ^8.0.0
  permission_handler: ^12.0.1   # was ^11.3.1

dev_dependencies:
  patrol: ^4.1.0                # was ^3.20.0
```

---

# Implementation Checklist

## Stage 1: Low-Risk Patches
- [ ] Update provider, sqflite, image_picker, supabase_flutter in pubspec.yaml
- [ ] Run `flutter pub get`
- [ ] Run `flutter analyze`
- [ ] Run `flutter test`
- [ ] Commit: "chore: Update low-risk dependencies"

## Stage 2: Syncfusion
- [ ] Update syncfusion packages in pubspec.yaml
- [ ] Run `flutter pub get`
- [ ] Run `flutter test test/features/pdf/`
- [ ] Manual test: PDF import
- [ ] Manual test: PDF export
- [ ] Commit: "chore: Update Syncfusion PDF to v32"

## Stage 3: Geolocator
- [ ] Update geolocator in pubspec.yaml
- [ ] Update `weather_service.dart` - LocationSettings API
- [ ] Update `photo_service.dart` - LocationSettings API
- [ ] Run `flutter analyze`
- [ ] Manual test: Weather fetch
- [ ] Manual test: Photo GPS tagging
- [ ] Commit: "chore: Update geolocator to v14"

## Stage 4: Connectivity Plus
- [ ] Update connectivity_plus in pubspec.yaml
- [ ] Verify List<ConnectivityResult> handling (should already work)
- [ ] Run `flutter analyze`
- [ ] Manual test: Offline/online sync status
- [ ] Commit: "chore: Update connectivity_plus to v7"

## Stage 5: File Picker
- [ ] Update file_picker in pubspec.yaml
- [ ] Add macOS entitlement if building for macOS
- [ ] Run `flutter analyze`
- [ ] Manual test: PDF file selection
- [ ] Commit: "chore: Update file_picker to v10"

## Stage 6: Permission Handler
- [ ] Update permission_handler in pubspec.yaml
- [ ] Run `flutter analyze`
- [ ] Manual test: Storage permissions
- [ ] Commit: "chore: Update permission_handler to v12"

## Stage 7: go_router
- [ ] Update go_router in pubspec.yaml
- [ ] Run `flutter analyze` - fix deprecations
- [ ] Test all navigation flows
- [ ] Test route parameters
- [ ] Test extra data passing
- [ ] Test auth redirect
- [ ] Commit: "chore: Update go_router to v17"

## Stage 8: Patrol
- [ ] Update patrol in pubspec.yaml
- [ ] Search/replace `$.native` → `$.platform.mobile`
- [ ] Update patrol_cli: `dart pub global activate patrol_cli`
- [ ] Run E2E tests
- [ ] Commit: "chore: Update patrol to v4"

## Final
- [ ] Full regression test on device
- [ ] Build release APK: `pwsh -Command "flutter build apk --release"`
- [ ] Commit: "chore: Complete dependency modernization"

---

# Rollback Plan

If critical issues arise after any stage:

1. Revert pubspec.yaml changes: `git checkout pubspec.yaml`
2. Run `flutter pub get`
3. Revert any code changes: `git checkout -- <file>`

Keep each stage as a separate commit for easy rollback.

---

# Sources

- [go_router changelog](https://pub.dev/packages/go_router/changelog)
- [geolocator changelog](https://pub.dev/packages/geolocator/changelog)
- [connectivity_plus changelog](https://pub.dev/packages/connectivity_plus/changelog)
- [file_picker changelog](https://pub.dev/packages/file_picker/changelog)
- [Patrol 4.0 Release](https://leancode.co/blog/patrol-4-0-release)
- [syncfusion_flutter_pdf changelog](https://pub.dev/packages/syncfusion_flutter_pdf/changelog)

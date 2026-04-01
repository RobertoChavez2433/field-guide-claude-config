# Source Excerpts — By Concern

## Concern 1: AppInitializer Decomposition (Findings #2, #9)

### Current: God Method (app_initializer.dart:361-885)
The 525-line `initialize()` method handles:
1. PreferencesService init (lines 365-370)
2. Aptabase analytics (lines 375-393)
3. Debug logging (lines 395)
4. SQLite init (lines 406-410)
5. TrashRepository/SoftDeleteService (lines 415-420)
6. Tesseract OCR (lines 425-445)
7. Supabase.initialize() (lines 448-465)
8. Firebase.initializeApp() (lines 468-478)
9. ProjectLifecycleService with `Supabase.instance.client` (lines 465-470)
10. 15+ local datasources (lines 475-500)
11. 10+ repositories (lines 500-525)
12. ProjectRemoteDatasource with `Supabase.instance.client` (line 529)
13. Use cases (lines 530-555)
14. CompanyMembersRepository with `Supabase.instance.client` (line 550)
15. Export datasources/repos (lines 560-575)
16. Form seeding (lines 578-582)
17. PhotoService (line 585)
18. Auth datasources with `Supabase.instance.client` (lines 588-600)
19. Auth use cases (lines 602-640)
20. AuthProvider with `Supabase.instance.client` (line 644)
21. ProjectSettingsProvider (lines 655-660)
22. App lifecycle/version gate (lines 662-690)
23. AppConfigProvider with `Supabase.instance.client` (line 681)
24. SyncProviders.initialize() with `Supabase.instance.client` (line 694)
25. BackgroundSyncHandler (line 706)
26. Auth state listener (lines 715-740)
27. Inactivity check + config check (lines 745-760)
28. AppRouter creation (line 751) — DEAD
29. Return AppDependencies (lines 765-885)

### Target: CoreDeps.create() extracts items 1-8 + supabaseClient field (replaces 9 Supabase.instance.client calls)
### Target: Feature initializers extract items 9-23 (each receives CoreDeps)
### Target: SyncInitializer extracts item 24
### Target: AppBootstrap.configure() handles post-init wiring (from main.dart)

---

## Concern 2: Router Split (Findings #1, #6, #11)

### Redirect Matrix (app_router.dart:155-340)
Full redirect code in patterns/router-redirect.md. Key issues:
- `ConsentProvider?` nullable (line 91) — spec says required
- `context.read<AppConfigProvider>()` with try-catch (lines 218-230) — spec says constructor-injected required

### ScaffoldWithNavBar (app_router.dart:747-931)
Full source in by-file.md. Key imports that move with it:
```dart
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/projects/presentation/widgets/project_switcher.dart';
import 'package:construction_inspector/core/theme/field_guide_colors.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';
// Banner imports:
import 'package:construction_inspector/features/pdf/presentation/widgets/extraction_banner.dart';
// (VersionBanner, StaleConfigWarning are likely in shared/widgets)
```

### Route Table (app_router.dart:345-745)
42 routes stay in app_router.dart. All screen imports stay with the route table.

---

## Concern 3: Entrypoint Consolidation (Findings #1, #7, #8)

### Duplicated Auth Listener
**main.dart:157-175**:
```dart
bool wasAuth = deps.authProvider.isAuthenticated;
deps.authProvider.addListener(() {
  final isNowAuth = deps.authProvider.isAuthenticated;
  if (wasAuth && !isNowAuth) {
    consentProvider.clearOnSignOut();
    Analytics.disable();
  }
  if (!wasAuth && isNowAuth && deps.authProvider.userId != null) {
    final appVersion = deps.appConfigProvider.appVersion;
    consentProvider.writeDeferredAuditRecordsIfNeeded(appVersion: appVersion);
  }
  wasAuth = isNowAuth;
});
```

**main_driver.dart:86-104**: Identical listener with "mirror" comment.

### Duplicated AppRouter Construction
**main.dart:178-181**:
```dart
final appRouter = AppRouter(
  authProvider: deps.authProvider,
  consentProvider: consentProvider,
);
```

**main_driver.dart:108-111**: Identical construction.

### Duplicated Consent Loading
**main.dart:140-150**: `consentProvider.loadConsentState()` + `enableSentryReporting()`
**main_driver.dart:82-85**: Identical sequence.

### Target: AppBootstrap.configure() absorbs all three duplicated blocks.

---

## Concern 4: SyncProviders Business Logic Extraction (Finding #3)

### Enrollment Logic (sync_providers.dart:91-187)
```dart
syncOrchestrator.onPullComplete = (tableName, pulledCount) async {
  if (tableName != 'project_assignments') return;
  if (pulledCount == 0) return;
  final userId = authProvider.userId;
  if (userId == null) return;
  final localDb = await dbService.database;
  if (authProvider.userId != userId) return;  // Auth state guard

  // Query project_assignments for this user
  final assignments = await localDb.query('project_assignments', ...);
  final assignedProjectIds = assignments.map(...).toSet();

  // Query synced_projects scoped via INNER JOIN
  final syncedProjectRows = await localDb.rawQuery('''
    SELECT sp.project_id, sp.unassigned_at
    FROM synced_projects sp
    INNER JOIN project_assignments pa
      ON sp.project_id = pa.project_id AND pa.user_id = ?
  ''', [userId]);

  // Transaction: enrollment inserts + unassignment detection
  await localDb.transaction((txn) async {
    // Insert new enrollments
    for (final projectId in assignedProjectIds) {
      if (!syncedMap.containsKey(projectId)) {
        await txn.insert('synced_projects', {...}, conflictAlgorithm: ConflictAlgorithm.ignore);
      }
    }
    // Mark unassigned projects
    for (final entry in syncedMap.entries) {
      if (!assignedProjectIds.contains(projectId) && currentUnassigned == null) {
        await txn.update('synced_projects', {'unassigned_at': ...}, ...);
      }
      // Re-assigned: clear unassigned_at
      if (assignedProjectIds.contains(projectId) && currentUnassigned != null) {
        await txn.update('synced_projects', {'unassigned_at': null}, ...);
      }
    }
  });

  // Queue notifications
  for (final _ in newlyEnrolled) {
    syncOrchestrator.onNewAssignmentDetected?.call('You\'ve been assigned...');
  }
};
```

### FCM Init (sync_providers.dart:189-198)
```dart
if (Platform.isAndroid || Platform.isIOS) {
  final fcmHandler = FcmHandler(authService: authService, syncOrchestrator: syncOrchestrator);
  fcmHandler.initialize(userId: authProvider.userId);
}
```

### Lifecycle Wiring (sync_providers.dart:200-235)
Full source in patterns/lifecycle-callback.md.

### Target: SyncEnrollmentService gets enrollment logic. FcmHandler absorbs FCM init. SyncInitializer orchestrates.

---

## Concern 5: Stale Entrypoints (Finding #10)

### driver_main.dart (9 lines)
```dart
void main() {
  enableFlutterDriverExtension();
  app.main();
}
```
Uses `flutter_driver` extension — DELETE.

### test_harness.dart (135 lines)
Uses `enableFlutterDriverExtension()` + screen/flow registry — DELETE (port registry to DriverServer).

### flutter_driver dep (pubspec.yaml:119)
```yaml
  flutter_driver:
```
DELETE.

### test_harness/ directory (6 files)
- `harness_providers.dart` — 230 lines of provider construction. Port relevant parts to DriverServer.
- `stub_services.dart` — 100% dead code. DELETE.
- `screen_registry.dart`, `flow_registry.dart`, `stub_router.dart`, `harness_seed_data.dart` — Port to `lib/core/driver/`.

---

## Concern 6: Dead AppRouter in AppDependencies (Finding #5)

### Dead field (app_initializer.dart:275)
```dart
class AppDependencies {
  ...
  final AppRouter appRouter;  // DEAD — main.dart and main_driver.dart create their own
```

### Dead construction (app_initializer.dart:751)
```dart
final appRouter = AppRouter(authProvider: authProvider);  // No consentProvider — unusable
```

### Dead copyWith entry (app_initializer.dart:354)
```dart
appRouter: appRouter,  // Carried through copyWith but never used
```

### Target: Remove `appRouter` field, constructor param, and `copyWith` reference from AppDependencies.

---

## Concern 7: Provider Split Assembly (Finding #7)

### Current: Two-step assembly
**Step 1** — `buildAppProviders(deps)` in `app_providers.dart` (missing consent/support)
**Step 2** — `ConstructionInspectorApp.build()` in `main.dart:205-209` splices consent/support

### Target: Single-step — `buildAppProviders(deps)` includes consent/support providers.

---

## Concern 8: Test Coverage (Finding #4)

### Missing test files (confirmed via filesystem)
- `test/core/di/app_initializer_test.dart` — does NOT exist
- `test/core/router/app_router_test.dart` — does NOT exist
- `test/features/sync/di/sync_providers_test.dart` — does NOT exist
- `test/features/sync/application/background_sync_handler_test.dart` — does NOT exist

### Spec creates 12 new test files covering all decomposed modules.

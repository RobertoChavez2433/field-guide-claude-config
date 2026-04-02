# Plan: Resolve Issue #8 — no_business_logic_in_di (33 violations)

**Goal**: Eliminate all 33 `no_business_logic_in_di` violations by moving business logic out of `/di/` files. Zero lint rule modifications.

**Branch**: `codebase_hygiene` (existing)

---

## Phase 1: Move `app_initializer.dart` out of `/di/` (21 violations)

### 1A: Extract debug logging to its own module

**Create** `lib/core/bootstrap/debug_logging_initializer.dart`

Move the `_initDebugLogging` method (lines 158-199) and `_ensureLogDirectoryWritable` (lines 201-210) from `app_initializer.dart` into a new static class:

```dart
class DebugLoggingInitializer {
  static Future<void> initialize(
    PreferencesService preferencesService, {
    String logDirOverride = '',
  }) async {
    // ... move full body of _initDebugLogging here ...
  }

  static Future<bool> _ensureLogDirectoryWritable(String path) async {
    // ... move full body here ...
  }
}
```

**Update** `lib/core/bootstrap/core_services_initializer.dart`:
- Replace the `initDebugLogging` callback parameter with a direct call to `DebugLoggingInitializer.initialize()`
- Remove the callback parameter from `create()` signature

**Update** `lib/core/di/app_initializer.dart`:
- Remove `_initDebugLogging` and `_ensureLogDirectoryWritable` methods
- Remove the callback reference in `CoreServicesInitializer.create()` call

### 1B: Extract version/lifecycle detection to its own module

**Create** `lib/core/bootstrap/app_lifecycle_initializer.dart`

Move lines 70-87 from `app_initializer.dart` into:

```dart
class AppLifecycleInitializer {
  static Future<void> handleVersionCheck({
    required AuthProvider authProvider,
    required PreferencesService preferencesService,
  }) async {
    final packageInfo = await PackageInfo.fromPlatform();
    final currentVersion = packageInfo.version;
    final storedVersion = preferencesService.getString('app_version');
    final isUpgrade = storedVersion != null && storedVersion != currentVersion;
    final isFreshInstall = storedVersion == null;

    if (isUpgrade) {
      Logger.auth('App upgrade detected: ...');
      await authProvider.forceReauthOnly();
      await preferencesService.clearLastRoute();
    } else if (isFreshInstall) {
      Logger.auth('Fresh install detected ...');
    }
    await preferencesService.setString('app_version', currentVersion);
  }
}
```

**Update** `lib/core/di/app_initializer.dart`:
- Replace lines 70-87 with `await AppLifecycleInitializer.handleVersionCheck(...)`

### 1C: Move `app_initializer.dart` from `lib/core/di/` to `lib/core/bootstrap/`

**Move** `lib/core/di/app_initializer.dart` → `lib/core/bootstrap/app_initializer.dart`

The file keeps `AppInitializer` class but now lives in bootstrap/ where it belongs.

**Update imports in all consumers** (11 files found by grep):
- `lib/main.dart`
- `lib/main_driver.dart`
- `lib/core/di/app_bootstrap.dart`
- `lib/core/di/app_dependencies.dart`
- `lib/core/di/core_deps.dart`
- `lib/core/bootstrap/startup_gate.dart`
- `test/core/di/app_initializer_test.dart`
- `test/core/di/core_deps_test.dart`
- `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_direct_database_construction.dart` (allowlist path reference)
- `fg_lint_packages/field_guide_lints/lib/architecture/rules/avoid_supabase_singleton.dart` (allowlist path reference)
- `fg_lint_packages/field_guide_lints/lib/architecture/rules/max_import_count.dart` (allowlist path reference)

Change import from:
```dart
import 'package:construction_inspector/core/di/app_initializer.dart';
```
to:
```dart
import 'package:construction_inspector/core/bootstrap/app_initializer.dart';
```

**CRITICAL**: Also update lint rule allowlists that reference `app_initializer.dart` path — the path-based allowlists in `no_direct_database_construction.dart`, `avoid_supabase_singleton.dart`, and `max_import_count.dart` must be updated from `core/di/app_initializer.dart` to `core/bootstrap/app_initializer.dart`.

**Kills**: All 21 violations (file no longer in `/di/` scope)

---

## Phase 2: Fix feature initializer violations (4 violations)

### 2A: Move auth hydration to bootstrap orchestrator (2 violations)

**Edit** `lib/features/auth/di/auth_initializer.dart`:
- Remove lines 101-102 (`await appConfigProvider.loadAppVersion()` and `await appConfigProvider.restoreLastCheckTimestamp()`)
- The method can now potentially become synchronous (return `AuthDeps` instead of `Future<AuthDeps>`) — BUT check if any other `await` exists in the method body. If none, change signature to `static AuthDeps create(CoreDeps coreDeps)`.

**Edit** `lib/core/bootstrap/app_initializer.dart` (new location):
- After `AuthInitializer.create(coreDeps)` returns, add:
```dart
await authDeps.appConfigProvider.loadAppVersion();
await authDeps.appConfigProvider.restoreLastCheckTimestamp();
```
This is fine because `app_initializer.dart` is now in bootstrap/, not di/.

**Kills**: 2 violations in `auth_initializer.dart`

### 2B: Move form seed to bootstrap orchestrator (1 violation)

**Edit** `lib/features/forms/di/form_initializer.dart`:
- Remove line 39 (`await seedBuiltinForms(inspectorFormRepository)`)
- Change method signature from `Future<FormDeps>` to `FormDeps` (now synchronous)
- Keep `registerFormScreens()` call (synchronous, not a violation)

**Edit** `lib/core/bootstrap/app_initializer.dart`:
- After `FormInitializer.create(coreDeps)` returns, add:
```dart
await seedBuiltinForms(formDeps.inspectorFormRepository);
```
- Add import for `form_seed_service.dart`

**Kills**: 1 violation in `form_initializer.dart`

### 2C: Refactor `ProjectLifecycleService` to accept `DatabaseService` (1 violation)

**Edit** `lib/features/projects/data/services/project_lifecycle_service.dart`:
- Change constructor from `ProjectLifecycleService(this._db, {SupabaseClient? supabaseClient})` to `ProjectLifecycleService(this._dbService, {SupabaseClient? supabaseClient})`
- Change field from `final Database _db` to `final DatabaseService _dbService`
- Add private getter: `Future<Database> get _db async => _dbService.database;`
- Update each method that uses `_db` to `await _db` (they are all already async, so this is a mechanical change):
  - `enrollProject`: `final db = await _db;` then use `db.insert(...)`
  - `removeFromDevice`: `final db = await _db;` at top, then `await SyncControlService.suppressedWithDb(db, () async { await db.transaction(...)... })`
  - `getUnsyncedChangeCount`: `final db = await _db;` then `db.rawQuery(...)`
  - `getAllUnsyncedCounts`: `final db = await _db;` then `db.rawQuery(...)`
  - `canDeleteFromDatabase`: `final db = await _db;` then `db.query(...)`
  - `deleteFromSupabase`: `final db = await _db;` then `db.delete(...)`
- Remove `import 'package:sqflite/sqflite.dart';` — add `import 'package:construction_inspector/core/database/database_service.dart';`

**Edit** `lib/features/projects/di/project_initializer.dart`:
- Remove `final db = await dbService.database;` (line 39)
- Change `ProjectLifecycleService(db, supabaseClient: supabaseClient)` to `ProjectLifecycleService(dbService, supabaseClient: supabaseClient)`
- Method signature changes from `Future<ProjectDeps>` to `ProjectDeps` (now synchronous — verify no other `await` remains)

**Update all test files** that construct `ProjectLifecycleService` directly:
- `test/features/projects/data/services/project_lifecycle_service_test.dart` — change constructor call
- `test/features/projects/integration/project_lifecycle_integration_test.dart` — change constructor call
- `test/features/projects/wiring/provider_wiring_smoke_test.dart` — change constructor call if applicable

**Also update**:
- `lib/features/sync/di/sync_providers.dart` — if it passes raw `Database` to `ProjectLifecycleService`
- `lib/core/driver/driver_server.dart` — if it constructs `ProjectLifecycleService`

**Kills**: 1 violation in `project_initializer.dart`

---

## Phase 3: Move `sync_initializer.dart` out of `/di/` (6 violations)

### 3A: Move `SyncInitializer` to application layer

**Move** `lib/features/sync/di/sync_initializer.dart` → `lib/features/sync/application/sync_initializer.dart`

**Update imports** in:
- `lib/features/sync/di/sync_providers.dart` — change import path

**Kills**: All 6 violations (file no longer in `/di/` scope)

---

## Phase 4: Extract sync_providers.dart callback (2 violations)

### 4A: Add `refreshFromService` method to `ProjectSyncHealthProvider`

**Edit** `lib/features/projects/presentation/providers/project_sync_health_provider.dart`:
- Add method:
```dart
/// Refresh unsynced counts from the lifecycle service.
/// Called after each sync cycle completes.
Future<void> refreshFromService(ProjectLifecycleService service) async {
  try {
    final counts = await service.getAllUnsyncedCounts();
    updateCounts(counts);
  } catch (e) {
    Logger.sync('Health provider update failed: $e');
  }
}
```
- Add imports for `Logger` and `ProjectLifecycleService`

### 4B: Simplify callback in `sync_providers.dart`

**Edit** `lib/features/sync/di/sync_providers.dart`:
- Replace lines 81-88:
```dart
syncProvider.onSyncCycleComplete = () async {
  try {
    final counts = await projectLifecycleService.getAllUnsyncedCounts();
    projectSyncHealthProvider.updateCounts(counts);
  } catch (e) {
    Logger.sync('Health provider update failed: $e');
  }
};
```
with:
```dart
syncProvider.onSyncCycleComplete = () =>
    projectSyncHealthProvider.refreshFromService(projectLifecycleService);
```

**Kills**: 2 violations (no more `await` or `try/catch` in the `/di/` file)

---

## Phase 5: Cleanup

### 5A: Update lint baseline

**Edit** `lint_baseline.json`:
- Remove all 6 entries for `no_business_logic_in_di` rule (totaling 33 violations)

### 5B: Run tests

```
pwsh -Command "flutter test"
pwsh -Command "flutter analyze"
```

Verify:
- All tests pass
- No new lint violations
- No regressions

### 5C: Verify issue is fully resolved

Run custom lint check to confirm 0 violations for `no_business_logic_in_di` across entire codebase.

---

## Files Created (3)
1. `lib/core/bootstrap/debug_logging_initializer.dart`
2. `lib/core/bootstrap/app_lifecycle_initializer.dart`
3. `lib/core/bootstrap/app_initializer.dart` (moved from `lib/core/di/app_initializer.dart`)

## Files Moved (2)
1. `lib/core/di/app_initializer.dart` → `lib/core/bootstrap/app_initializer.dart`
2. `lib/features/sync/di/sync_initializer.dart` → `lib/features/sync/application/sync_initializer.dart`

## Files Modified (~20)
- `lib/core/bootstrap/core_services_initializer.dart` (remove callback param)
- `lib/core/bootstrap/app_initializer.dart` (extract methods, add hydration/seed calls)
- `lib/features/auth/di/auth_initializer.dart` (remove 2 awaits)
- `lib/features/forms/di/form_initializer.dart` (remove seed await)
- `lib/features/projects/di/project_initializer.dart` (remove db await)
- `lib/features/projects/data/services/project_lifecycle_service.dart` (accept DatabaseService)
- `lib/features/projects/presentation/providers/project_sync_health_provider.dart` (add method)
- `lib/features/sync/di/sync_providers.dart` (simplify callback, update import)
- `lib/main.dart` (update import)
- `lib/main_driver.dart` (update import)
- `lib/core/di/app_bootstrap.dart` (update import)
- `lib/core/di/app_dependencies.dart` (update import)
- `lib/core/di/core_deps.dart` (update import)
- `lib/core/bootstrap/startup_gate.dart` (update import)
- `fg_lint_packages/.../no_direct_database_construction.dart` (update allowlist path)
- `fg_lint_packages/.../avoid_supabase_singleton.dart` (update allowlist path)
- `fg_lint_packages/.../max_import_count.dart` (update allowlist path)
- `lint_baseline.json` (remove 6 entries)
- Test files for `ProjectLifecycleService` (update constructor)
- Test files for `AppInitializer` (update import)

## Violation Resolution Summary

| Source | Count | Resolution |
|--------|-------|-----------|
| `app_initializer.dart` (move to bootstrap/) | 21 | Phase 1C — file exits `/di/` scope |
| `auth_initializer.dart` | 2 | Phase 2A — awaits moved to bootstrap orchestrator |
| `form_initializer.dart` | 1 | Phase 2B — seed moved to bootstrap orchestrator |
| `project_initializer.dart` | 1 | Phase 2C — refactor service to accept DatabaseService |
| `sync_initializer.dart` (move to application/) | 6 | Phase 3A — file exits `/di/` scope |
| `sync_providers.dart` | 2 | Phase 4 — callback extracted to provider method |
| **Total** | **33** | **All resolved, 0 lint rule changes** |

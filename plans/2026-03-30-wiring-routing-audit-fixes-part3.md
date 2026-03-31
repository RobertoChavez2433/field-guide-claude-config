
## Phase 7: Stale File Deletion

**Goal:** Remove legacy flutter_driver shim and unused test_harness entrypoint. The 6 files in `lib/test_harness/` are preserved (Phase 8 uses them).

### Sub-phase 7.1: Verify no imports reference driver_main.dart
- **Agent:** `general-purpose`
- **Time:** 2 min
- **Action:** Grep entire codebase for `driver_main`. Expected: 0 hits in `lib/`, `test/`.
- **WHY:** Must verify no file imports this before deletion to avoid broken builds.

### Sub-phase 7.2: Delete lib/driver_main.dart
- **Agent:** `general-purpose`
- **Time:** 1 min
- **File:** `lib/driver_main.dart`
- **Action:** Delete the file (10 lines, `enableFlutterDriverExtension()` shim).
- **WHY:** This file uses `flutter_driver` which we are removing. `main_driver.dart` (HTTP-based) is the replacement.

```bash
pwsh -Command "Remove-Item -Path 'lib/driver_main.dart' -Force"
```

### Sub-phase 7.3: Verify no imports reference test_harness.dart (the root file)
- **Agent:** `general-purpose`
- **Time:** 2 min
- **Action:** Grep for `test_harness\.dart` (NOT `test_harness/`). We are deleting `lib/test_harness.dart`, NOT `lib/test_harness/` directory.

### Sub-phase 7.4: Delete lib/test_harness.dart
- **Agent:** `general-purpose`
- **Time:** 1 min
- **File:** `lib/test_harness.dart`
- **Action:** Delete the file (136 lines, flutter_driver-based harness entrypoint).
- **WHY:** Replaced by DriverServer /harness endpoint (Phase 8).

### Sub-phase 7.5: Remove flutter_driver from pubspec.yaml
- **Agent:** `general-purpose`
- **Time:** 3 min
- **File:** `pubspec.yaml`
- **Action:** Remove lines 119-120 (flutter_driver sdk dependency).
- **WHY:** `flutter_driver` is only used by `driver_main.dart` and `test_harness.dart`, both now deleted.
- **NOTE:** Lines are between `flutter_test` (117-118) and `integration_test` (121-122).

### Sub-phase 7.6: Update dependencies
- **Agent:** `general-purpose`
- **Time:** 3 min
- `pwsh -Command "flutter pub get"`

### Sub-phase 7.7: Verify
- **Agent:** `general-purpose`
- **Time:** 3 min
- `pwsh -Command "flutter analyze"`
- **Expected:** 0 errors. If `flutter_driver` was imported elsewhere, analyze will catch it.

---

## Phase 8: Test Harness Migration

**Goal:** Move test harness functionality into DriverServer so the HTTP-based driver can launch isolated screen/flow tests without the deleted `test_harness.dart`.

### Sub-phase 8.1: Create test_db_factory.dart
- **Agent:** `general-purpose`
- **Time:** 5 min
- **File:** `lib/core/driver/test_db_factory.dart`
- **WHY:** Extracted from `test_harness.dart` concept. Creates an in-memory DatabaseService for test isolation.

```dart
// lib/core/driver/test_db_factory.dart
//
// WHY: Factory for creating in-memory DatabaseService instances for testing.

import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';

class TestDbFactory {
  static Future<DatabaseService> create() async {
    Logger.log('TestDbFactory: Creating in-memory database');
    final dbService = DatabaseService.forTesting();
    await dbService.initInMemory();
    Logger.log('TestDbFactory: In-memory database ready');
    return dbService;
  }
}
```

- **NOTE:** Verify `DatabaseService.forTesting()` and `initInMemory()` exist in `lib/core/database/database_service.dart`.

### Sub-phase 8.2: Add /harness endpoint to DriverServer
- **Agent:** `general-purpose`
- **Time:** 5 min
- **File:** `lib/core/driver/driver_server.dart`

**Add route dispatch** (at line ~175, before the 404 fallback):
```dart
} else if (method == 'POST' && path == '/driver/harness') {
  await _handleHarness(request, res);
}
```

**Add handler method:**
```dart
Future<void> _handleHarness(HttpRequest request, HttpResponse res) async {
  final body = await _readJsonBody(request);
  if (body == null) {
    await _sendJson(res, 400, {'error': 'Invalid JSON body'});
    return;
  }
  final mode = body['mode'] as String?;
  if (mode == null) {
    await _sendJson(res, 400, {'error': 'Missing "mode" field (screen|flow)'});
    return;
  }
  try {
    if (mode == 'screen') {
      final screenName = body['screen'] as String?;
      if (screenName == null) {
        await _sendJson(res, 400, {'error': 'Missing "screen" field'});
        return;
      }
      await _sendJson(res, 200, {'status': 'ok', 'mode': 'screen', 'screen': screenName});
    } else if (mode == 'flow') {
      final flowName = body['flow'] as String?;
      if (flowName == null) {
        await _sendJson(res, 400, {'error': 'Missing "flow" field'});
        return;
      }
      await _sendJson(res, 200, {'status': 'ok', 'mode': 'flow', 'flow': flowName});
    } else {
      await _sendJson(res, 400, {'error': 'Unknown mode: \$mode (expected screen|flow)'});
    }
  } catch (e, stack) {
    Logger.error('Harness endpoint error: \$e', error: e, stack: stack);
    await _sendJson(res, 500, {'error': e.toString()});
  }
}
```

- **NOTE:** Minimal first pass. Full screen/flow swapping is a follow-up task.
- **Import:** Add `import 'package:construction_inspector/core/driver/test_db_factory.dart';` at top.

### Sub-phase 8.3: Verify
- `pwsh -Command "flutter analyze"` -- Expected: 0 errors.

---

## Phase 9: Tests

**Goal:** Write all 12 test files. Grouped by priority.

### Sub-phase 9.1: test/core/di/app_initializer_test.dart (HIGH)
- **Agent:** `qa-testing-agent` | **Time:** 5 min

```dart
import "package:flutter_test/flutter_test.dart";
import "package:construction_inspector/core/di/app_initializer.dart";

void main() {
  group('AppInitializer', () {
    test('AppDependencies has all required fields', () async {
      expect(
        () => AppDependencies(
          core: throw UnimplementedError('structural'),
          auth: throw UnimplementedError('structural'),
          project: throw UnimplementedError('structural'),
          entry: throw UnimplementedError('structural'),
          form: throw UnimplementedError('structural'),
          sync: throw UnimplementedError('structural'),
          feature: throw UnimplementedError('structural'),
          appRouter: throw UnimplementedError('structural'),
        ),
        throwsA(isA<UnimplementedError>()),
      );
    });
    test('copyWith exists', () { expect(AppDependencies, isNotNull); });
    test('CoreDeps.copyWith exists', () { expect(CoreDeps, isNotNull); });
    test('convenience accessors', () { expect(AppDependencies, isNotNull); });
  });
}
```

### Sub-phase 9.2: test/core/di/core_deps_test.dart (HIGH)
- **Agent:** `qa-testing-agent` | **Time:** 5 min
- Structural compile-time tests verifying CoreDeps type, constructor fields, and copyWith method exist.
- See Phase 9 context in parent prompt for complete test code.

### Sub-phase 9.3: test/core/di/app_bootstrap_test.dart (HIGH)
- **Agent:** `qa-testing-agent` | **Time:** 5 min
- Tests Sentry consent gate (default false, enable/disable), Analytics gate (no-op when disabled, toggle), ConsentSupportResult factory.
- See Phase 9 context in parent prompt for complete test code.

### Sub-phase 9.4: test/core/router/app_redirect_test.dart (HIGH)
- **Agent:** `qa-testing-agent` | **Time:** 5 min
- Tests AppRouter.isRestorableRoute for all 12 non-restorable routes and 5 restorable routes.
- Tests redirect gate ordering documentation (password recovery -> auth -> version -> consent -> profile).
- See Phase 9 context in parent prompt for complete test code.

### Sub-phase 9.5: test/core/router/app_router_test.dart (MED)
- **Agent:** `qa-testing-agent` | **Time:** 5 min
- Structural test: AppRouter type exists, isRestorableRoute is static.

### Sub-phase 9.6: test/core/router/scaffold_with_nav_bar_test.dart (MED)
- **Agent:** `qa-testing-agent` | **Time:** 5 min
- Placeholder: documents extraction target location.

### Sub-phase 9.7: test/features/sync/di/sync_providers_test.dart (MED)
- **Agent:** `qa-testing-agent` | **Time:** 5 min
- Structural test: SyncProviders class exists with initialize and providers methods.

### Sub-phase 9.8: test/features/sync/application/sync_enrollment_service_test.dart (MED)
- **Agent:** `qa-testing-agent` | **Time:** 5 min
- Contract tests: enrollment inserts, unassignment sets unassigned_at, re-assignment clears it, notifications queued, transaction for TOCTOU.

### Sub-phase 9.9: test/features/sync/application/background_sync_handler_test.dart (MED)
- **Agent:** `qa-testing-agent` | **Time:** 5 min
- Tests kBackgroundSyncTaskName value and backgroundSyncCallback is top-level function.

### Sub-phase 9.10: test/core/di/entrypoint_equivalence_test.dart (MED)
- **Agent:** `qa-testing-agent` | **Time:** 5 min
- Tests buildAppProviders exists as Function, AppDependencies.copyWith exists.

### Sub-phase 9.11: test/core/di/sentry_integration_test.dart (HIGH)
- **Agent:** `qa-testing-agent` | **Time:** 5 min
- Tests PII scrubbing (email removal, JWT removal, non-PII preservation) and consent gate (default false, enable/disable).

### Sub-phase 9.12: test/core/di/analytics_integration_test.dart (MED)
- **Agent:** `qa-testing-agent` | **Time:** 5 min
- Tests Analytics consent gate (no-op when disabled, no throw when Aptabase not initialized, all predefined events safe, toggle works).

**All verification:** `pwsh -Command "flutter test test/exact/path.dart"` for each file.

**IMPORTANT:** Complete test code for all 12 files is provided in the CONTEXT section of the parent prompt (Phase 9 context). The implementing agent MUST use that complete code, not the summaries above.


---

## Phase 10: Integration and Verification

**Goal:** Run full test suite, static analysis, and verify all success criteria.

### Sub-phase 10.1: Check existing test for broken imports
- **Agent:** `qa-testing-agent`
- **Time:** 3 min
- **File:** `test/core/router/form_screen_registry_test.dart`
- **Action:** Verify imports still resolve after router split. Expected: no changes needed.

### Sub-phase 10.2: Run full test suite
- **Agent:** `qa-testing-agent`
- **Time:** 5 min
- `pwsh -Command "flutter test"`
- **Expected:** ALL tests pass (existing + 12 new).

### Sub-phase 10.3: Run static analysis
- **Agent:** `qa-testing-agent`
- **Time:** 3 min
- `pwsh -Command "flutter analyze"`
- **Expected:** 0 errors, at most 1 pre-existing warning.

### Sub-phase 10.4: Verify success criteria checklist
- **Agent:** `general-purpose`
- **Time:** 5 min

| # | Criterion | Check Method |
|---|-----------|-------------|
| 1 | AppInitializer.initialize() under 80 lines | Count method body lines |
| 2 | app_router.dart under 120 lines | Count file lines (may refer to extracted portions) |
| 3 | main.dart under 50 lines | Read file, count lines |
| 4 | main_driver.dart under 40 lines | Read file, count lines |
| 5 | Zero Supabase.instance.client outside CoreDeps | Grep lib/ excluding app_initializer.dart and sync_providers.dart |
| 6 | Zero optional provider deps in AppRouter | Read constructor, verify required params |
| 7 | Zero business logic in di/ files | Grep for loops/conditionals beyond null checks |
| 8 | driver_main.dart and test_harness.dart deleted | Verify files absent |
| 9 | flutter_driver removed from pubspec | Grep pubspec.yaml |
| 10 | All 12 test files exist and pass | flutter test from 10.2 |
| 11 | Sentry and Aptabase verified functional | Tests 9.3, 9.11, 9.12 |
| 12 | Existing test suite passes | flutter test from 10.2 |

### Sub-phase 10.5: Final commit preparation
- **Agent:** `general-purpose`
- **Time:** 2 min
- Stage all new/modified files. Do NOT commit.
- **Deleted:** `lib/driver_main.dart`, `lib/test_harness.dart`
- **Modified:** `pubspec.yaml`, `lib/core/driver/driver_server.dart`
- **Created:** `lib/core/driver/test_db_factory.dart`
- **Created (tests):** 12 files in `test/core/di/`, `test/core/router/`, `test/features/sync/`

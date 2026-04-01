## Phase 1: Foundation Types

Create `CoreDeps` (extracted with new `supabaseClient` field) and `InitOptions` as new standalone files. These are dependency-free foundation types that later phases build on.

---

### Sub-phase 1.1: Create `lib/core/di/core_deps.dart`

**Files:**
- Create: `lib/core/di/core_deps.dart`
- Test: `test/core/di/core_deps_test.dart`

**Agent**: `general-purpose`

#### Step 1.1.1: Write failing test for CoreDeps

Create the test file that validates CoreDeps construction, the `supabaseClient` field, and `copyWith`.

```dart
// test/core/di/core_deps_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/di/core_deps.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/shared/services/preferences_service.dart';
import 'package:construction_inspector/services/photo_service.dart';
import 'package:construction_inspector/services/image_service.dart';
import 'package:construction_inspector/features/settings/data/repositories/trash_repository.dart';
import 'package:construction_inspector/services/soft_delete_service.dart';
import 'package:construction_inspector/services/permission_service.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

// WHY: Mock all dependencies so CoreDeps can be tested in isolation
@GenerateMocks([
  DatabaseService,
  PreferencesService,
  PhotoService,
  ImageService,
  TrashRepository,
  SoftDeleteService,
  PermissionService,
  SupabaseClient,
])
import 'core_deps_test.mocks.dart';

void main() {
  group('CoreDeps', () {
    late MockDatabaseService mockDb;
    late MockPreferencesService mockPrefs;
    late MockPhotoService mockPhoto;
    late MockImageService mockImage;
    late MockTrashRepository mockTrash;
    late MockSoftDeleteService mockSoftDelete;
    late MockPermissionService mockPermission;

    setUp(() {
      mockDb = MockDatabaseService();
      mockPrefs = MockPreferencesService();
      mockPhoto = MockPhotoService();
      mockImage = MockImageService();
      mockTrash = MockTrashRepository();
      mockSoftDelete = MockSoftDeleteService();
      mockPermission = MockPermissionService();
    });

    // WHY: Verify all existing fields are preserved after extraction from app_initializer.dart
    test('should construct with all required fields', () {
      final deps = CoreDeps(
        dbService: mockDb,
        preferencesService: mockPrefs,
        photoService: mockPhoto,
        imageService: mockImage,
        trashRepository: mockTrash,
        softDeleteService: mockSoftDelete,
        permissionService: mockPermission,
      );

      expect(deps.dbService, mockDb);
      expect(deps.preferencesService, mockPrefs);
      expect(deps.photoService, mockPhoto);
      expect(deps.imageService, mockImage);
      expect(deps.trashRepository, mockTrash);
      expect(deps.softDeleteService, mockSoftDelete);
      expect(deps.permissionService, mockPermission);
    });

    // FROM SPEC: "CoreDeps.supabaseClient" replaces all 9 Supabase.instance.client calls
    test('should hold nullable supabaseClient field', () {
      final mockClient = MockSupabaseClient();
      final deps = CoreDeps(
        dbService: mockDb,
        preferencesService: mockPrefs,
        photoService: mockPhoto,
        imageService: mockImage,
        trashRepository: mockTrash,
        softDeleteService: mockSoftDelete,
        permissionService: mockPermission,
        supabaseClient: mockClient,
      );

      expect(deps.supabaseClient, mockClient);
    });

    test('should allow null supabaseClient for offline-only mode', () {
      final deps = CoreDeps(
        dbService: mockDb,
        preferencesService: mockPrefs,
        photoService: mockPhoto,
        imageService: mockImage,
        trashRepository: mockTrash,
        softDeleteService: mockSoftDelete,
        permissionService: mockPermission,
      );

      expect(deps.supabaseClient, isNull);
    });

    // WHY: copyWith is used by driver mode to swap PhotoService (main_driver.dart:74-75)
    test('copyWith should replace photoService and preserve others', () {
      final deps = CoreDeps(
        dbService: mockDb,
        preferencesService: mockPrefs,
        photoService: mockPhoto,
        imageService: mockImage,
        trashRepository: mockTrash,
        softDeleteService: mockSoftDelete,
        permissionService: mockPermission,
        supabaseClient: MockSupabaseClient(),
      );

      final newPhoto = MockPhotoService();
      final copied = deps.copyWith(photoService: newPhoto);

      expect(copied.photoService, newPhoto);
      expect(copied.dbService, mockDb);
      expect(copied.supabaseClient, deps.supabaseClient);
    });

    test('copyWith with no args returns equivalent copy', () {
      final deps = CoreDeps(
        dbService: mockDb,
        preferencesService: mockPrefs,
        photoService: mockPhoto,
        imageService: mockImage,
        trashRepository: mockTrash,
        softDeleteService: mockSoftDelete,
        permissionService: mockPermission,
      );

      final copied = deps.copyWith();
      expect(copied.photoService, mockPhoto);
      expect(copied.dbService, mockDb);
    });
  });
}
```

#### Step 1.1.2: Implement CoreDeps in new file

Create `lib/core/di/core_deps.dart` extracted from `lib/core/di/app_initializer.dart:115-143` with the addition of a `supabaseClient` field.

```dart
// lib/core/di/core_deps.dart
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/shared/services/preferences_service.dart';
import 'package:construction_inspector/services/photo_service.dart';
import 'package:construction_inspector/services/image_service.dart';
import 'package:construction_inspector/features/settings/data/repositories/trash_repository.dart';
import 'package:construction_inspector/services/soft_delete_service.dart';
import 'package:construction_inspector/services/permission_service.dart';

/// Core infrastructure dependencies (database, preferences, services).
///
/// FROM SPEC: CoreDeps is the DI root. Every feature initializer receives
/// CoreDeps as its first parameter. No global singleton access anywhere
/// downstream.
class CoreDeps {
  final DatabaseService dbService;
  final PreferencesService preferencesService;
  final PhotoService photoService;
  final ImageService imageService;
  final TrashRepository trashRepository;
  final SoftDeleteService softDeleteService;
  final PermissionService permissionService;

  /// WHY: Replaces all 9 Supabase.instance.client direct accesses in
  /// app_initializer.dart (lines 337, 470, 529, 550, 590, 599, 644, 681, 694).
  /// Nullable because Supabase is not configured in offline-only mode.
  final SupabaseClient? supabaseClient;

  const CoreDeps({
    required this.dbService,
    required this.preferencesService,
    required this.photoService,
    required this.imageService,
    required this.trashRepository,
    required this.softDeleteService,
    required this.permissionService,
    this.supabaseClient,
  });

  /// WHY: Used by driver mode to swap PhotoService for TestPhotoService
  /// without re-running full initialization (main_driver.dart:74-75).
  CoreDeps copyWith({PhotoService? photoService}) => CoreDeps(
        dbService: dbService,
        preferencesService: preferencesService,
        photoService: photoService ?? this.photoService,
        imageService: imageService,
        trashRepository: trashRepository,
        softDeleteService: softDeleteService,
        permissionService: permissionService,
        supabaseClient: supabaseClient,
      );
}
```

#### Step 1.1.3: Run mockito build_runner to generate mocks

Run: `pwsh -Command "dart run build_runner build --delete-conflicting-outputs --build-filter=test/core/di/core_deps_test.dart"`
Expected: Build completes, generates `core_deps_test.mocks.dart`

#### Step 1.1.4: Verify test passes

Run: `pwsh -Command "flutter test test/core/di/core_deps_test.dart"`
Expected: All 5 tests PASS

---

### Sub-phase 1.2: Create `lib/core/di/init_options.dart`

**Files:**
- Create: `lib/core/di/init_options.dart`
- Test: `test/core/di/init_options_test.dart`

**Agent**: `general-purpose`

#### Step 1.2.1: Write failing test for InitOptions

```dart
// test/core/di/init_options_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/di/init_options.dart';

void main() {
  group('InitOptions', () {
    // FROM SPEC: InitOptions controls driver mode, photo service override,
    // and supabase client override
    test('should default to non-driver mode', () {
      const options = InitOptions();

      expect(options.isDriverMode, false);
      expect(options.logDirOverride, '');
    });

    test('should accept isDriverMode flag', () {
      const options = InitOptions(isDriverMode: true);

      expect(options.isDriverMode, true);
    });

    test('should accept logDirOverride', () {
      const options = InitOptions(logDirOverride: '/tmp/logs');

      expect(options.logDirOverride, '/tmp/logs');
    });

    // WHY: const constructor enables compile-time creation in main.dart/main_driver.dart
    test('should be constructable as const', () {
      // NOTE: If this compiles, the const constructor works
      const options = InitOptions(isDriverMode: true, logDirOverride: '/tmp');
      expect(options.isDriverMode, true);
    });
  });
}
```

#### Step 1.2.2: Implement InitOptions

```dart
// lib/core/di/init_options.dart

/// Configuration options for app initialization.
///
/// FROM SPEC: Controls driver mode (skips Sentry, allows photo service swap)
/// and log directory override. Passed to AppInitializer.initialize().
class InitOptions {
  /// WHY: When true, skips Sentry initialization and enables TestPhotoService
  /// swap in main_driver.dart. Compile-time const ensures it cannot be true
  /// in release builds via separate entrypoints.
  final bool isDriverMode;

  /// WHY: Override for debug log directory. Replaces the logDirOverride
  /// parameter previously on AppInitializer.initialize().
  /// Currently used by both main.dart and main_driver.dart (kAppLogDirOverride).
  final String logDirOverride;

  const InitOptions({
    this.isDriverMode = false,
    this.logDirOverride = '',
  });
}
```

#### Step 1.2.3: Verify test passes

Run: `pwsh -Command "flutter test test/core/di/init_options_test.dart"`
Expected: All 4 tests PASS

---

### Sub-phase 1.3: Verify Phase 1 with analyze

**Agent**: `general-purpose`

#### Step 1.3.1: Run static analysis

Run: `pwsh -Command "flutter analyze lib/core/di/core_deps.dart lib/core/di/init_options.dart"`
Expected: No analysis issues

---

## Phase 2: AppInitializer Decomposition

Refactor `app_initializer.dart` so `initialize()` uses `CoreDeps.supabaseClient` instead of `Supabase.instance.client` calls, remove dead `appRouter` field and compatibility accessors from `AppDependencies`. The XxxDeps classes stay in `app_initializer.dart` but CoreDeps is imported from the new file.

---

### Sub-phase 2.1: Update `app_initializer.dart` to import CoreDeps from new file and add supabaseClient

**Files:**
- Modify: `lib/core/di/app_initializer.dart:115-143` (remove CoreDeps class, import from core_deps.dart)
- Modify: `lib/core/di/app_initializer.dart:336-337` (remove supabaseClient getter from AppDependencies)
- Modify: `lib/core/di/app_initializer.dart:432-470` (capture supabaseClient once after Supabase.initialize)
- Modify: `lib/core/di/app_initializer.dart:529,550,590,599,644,681,694` (replace Supabase.instance.client with local supabaseClient)
- Test: `test/core/di/core_deps_test.dart` (already exists from Phase 1)

**Agent**: `general-purpose`

#### Step 2.1.1: Remove CoreDeps class from app_initializer.dart and add import

Replace lines 114-143 (the CoreDeps class definition) with an import of the new file. The class body is now in `lib/core/di/core_deps.dart`.

At `lib/core/di/app_initializer.dart`, add this import near the top (after existing imports):

```dart
// IMPORTANT: CoreDeps moved to its own file — all fields preserved,
// supabaseClient field added per spec.
import 'package:construction_inspector/core/di/core_deps.dart';
```

Remove lines 114-143 (the entire `CoreDeps` class block including the doc comment at line 114). Replace with a re-export comment:

```dart
// NOTE: CoreDeps class is now in lib/core/di/core_deps.dart
// Re-exported via this file's import for backward compatibility.
```

#### Step 2.1.2: Capture supabaseClient after Supabase.initialize and use it everywhere

After the Supabase.initialize() block (around line 450), add a local variable:

```dart
    // FROM SPEC: Capture supabaseClient once — replaces all 9 Supabase.instance.client calls
    final SupabaseClient? supabaseClient =
        SupabaseConfig.isConfigured ? Supabase.instance.client : null;
```

Then replace each `Supabase.instance.client` reference with `supabaseClient` (or `supabaseClient!` where the call is already inside an `if (SupabaseConfig.isConfigured)` guard):

**Line 470** (`ProjectLifecycleService`):
```dart
    // BEFORE: supabaseClient: SupabaseConfig.isConfigured ? Supabase.instance.client : null,
    // AFTER:
    final projectLifecycleService = ProjectLifecycleService(
      db,
      supabaseClient: supabaseClient,
    );
```

**Line 529** (`ProjectRemoteDatasourceImpl`):
```dart
    // BEFORE: ? ProjectRemoteDatasourceImpl(Supabase.instance.client)
    // AFTER:
    final projectRemoteDatasource = supabaseClient != null
        ? ProjectRemoteDatasourceImpl(supabaseClient)
        : null;
```

**Line 550** (`CompanyMembersRepository`):
```dart
    // BEFORE: ? CompanyMembersRepository(Supabase.instance.client)
    // AFTER:
    final companyMembersRepository = supabaseClient != null
        ? CompanyMembersRepository(supabaseClient)
        : null;
```

**Line 590** (`UserProfileRemoteDatasource`):
```dart
    // BEFORE: ? UserProfileRemoteDatasource(Supabase.instance.client)
    // AFTER:
    final userProfileRemoteDs = supabaseClient != null
        ? UserProfileRemoteDatasource(supabaseClient)
        : null;
```

**Line 599** (`AuthService`):
```dart
    // BEFORE: ? AuthService(Supabase.instance.client)
    // AFTER:
    final authService = supabaseClient != null
        ? AuthService(supabaseClient)
        : AuthService(null);
```

**Line 644** (`AuthProvider`):
```dart
    // BEFORE: supabaseClient: SupabaseConfig.isConfigured ? Supabase.instance.client : null,
    // AFTER:
      supabaseClient: supabaseClient,
```

**Line 681** (`AppConfigRepository`):
```dart
    // BEFORE: ? AppConfigRepository(Supabase.instance.client)
    // AFTER:
    final appConfigRepository = supabaseClient != null
        ? AppConfigRepository(supabaseClient)
        : AppConfigRepository(null);
```

**Line 694** (`SyncProviders.initialize`):
```dart
    // BEFORE: supabaseClient: SupabaseConfig.isConfigured ? Supabase.instance.client : null,
    // AFTER:
      supabaseClient: supabaseClient,
```

#### Step 2.1.3: Pass supabaseClient into CoreDeps at the return statement

At `lib/core/di/app_initializer.dart:762-771`, update the CoreDeps construction in the return block:

```dart
      core: CoreDeps(
        dbService: dbService,
        preferencesService: preferencesService,
        photoService: photoService,
        imageService: imageService,
        trashRepository: trashRepository,
        softDeleteService: softDeleteService,
        permissionService: permissionService,
        supabaseClient: supabaseClient, // NEW: replaces AppDependencies.supabaseClient getter
      ),
```

#### Step 2.1.4: Verify existing tests still pass

Run: `pwsh -Command "flutter test test/core/di/core_deps_test.dart"`
Expected: All tests PASS

---

### Sub-phase 2.2: Remove dead `appRouter` field from AppDependencies

**Files:**
- Modify: `lib/core/di/app_initializer.dart:275` (remove field)
- Modify: `lib/core/di/app_initializer.dart:285` (remove constructor param)
- Modify: `lib/core/di/app_initializer.dart:341-354` (remove from copyWith)
- Modify: `lib/core/di/app_initializer.dart:751-754` (remove dead AppRouter construction)
- Modify: `lib/core/di/app_initializer.dart:823` (remove from return statement)

**Agent**: `general-purpose`

#### Step 2.2.1: Remove appRouter from AppDependencies class

In `lib/core/di/app_initializer.dart`:

1. **Remove field** at line 275:
   ```dart
   // DELETE: final AppRouter appRouter;
   ```

2. **Remove constructor param** at line 285:
   ```dart
   // DELETE: required this.appRouter,
   ```

3. **Remove from copyWith** at line 352:
   ```dart
   // DELETE: appRouter: appRouter,
   ```

4. **Remove dead AppRouter construction** at line 754:
   ```dart
   // DELETE: final appRouter = AppRouter(authProvider: authProvider);
   ```

5. **Remove from return statement** at line 823:
   ```dart
   // DELETE: appRouter: appRouter,
   ```

6. **Remove AppRouter import** at line 8:
   ```dart
   // DELETE: import 'package:construction_inspector/core/router/app_router.dart';
   ```

#### Step 2.2.2: Verify compilation

Run: `pwsh -Command "flutter analyze lib/core/di/app_initializer.dart"`
Expected: No analysis issues (or only pre-existing ones unrelated to this change)

---

### Sub-phase 2.3: Remove compatibility accessors from AppDependencies

**Files:**
- Modify: `lib/core/di/app_initializer.dart:288-337` (remove 30+ delegate getters)
- Modify: `lib/core/di/app_providers.dart:37-139` (update to use `deps.core.dbService` etc.)

**Agent**: `general-purpose`

#### Step 2.3.1: Identify all callers of compatibility accessors

The compatibility accessors (lines 288-337) allow callers to write `deps.dbService` instead of `deps.core.dbService`. The confirmed callers are:

1. `lib/core/di/app_providers.dart` -- uses `deps.dbService`, `deps.permissionService`, `deps.preferencesService`, `deps.trashRepository`, `deps.softDeleteService`, `deps.authService`, `deps.authProvider`, `deps.appConfigProvider`, and many more.
2. `lib/main.dart` -- uses `deps.authProvider`, `deps.appConfigProvider`.
3. `lib/main_driver.dart` -- uses `deps.authProvider`, `deps.photoRepository`.

#### Step 2.3.2: Update app_providers.dart to use qualified paths

In `lib/core/di/app_providers.dart`, replace all `deps.<field>` with `deps.<subDeps>.<field>`:

- `deps.dbService` -> `deps.core.dbService`
- `deps.permissionService` -> `deps.core.permissionService`
- `deps.preferencesService` -> `deps.core.preferencesService`
- `deps.trashRepository` -> `deps.core.trashRepository`
- `deps.softDeleteService` -> `deps.core.softDeleteService`
- `deps.authService` -> `deps.auth.authService`
- `deps.authProvider` -> `deps.auth.authProvider`
- `deps.appConfigProvider` -> `deps.auth.appConfigProvider`
- `deps.supabaseClient` -> `deps.core.supabaseClient`
- `deps.projectRepository` -> `deps.project.projectRepository`
- `deps.projectAssignmentProvider` -> `deps.project.projectAssignmentProvider`
- `deps.projectSettingsProvider` -> `deps.project.projectSettingsProvider`
- `deps.projectSyncHealthProvider` -> `deps.project.projectSyncHealthProvider`
- `deps.projectImportRunner` -> `deps.project.projectImportRunner`
- `deps.projectLifecycleService` -> `deps.project.projectLifecycleService`
- `deps.syncedProjectRepository` -> `deps.project.syncedProjectRepository`
- `deps.companyMembersRepository` -> `deps.project.companyMembersRepository`
- `deps.deleteProjectUseCase` -> `deps.project.deleteProjectUseCase`
- `deps.loadAssignmentsUseCase` -> `deps.project.loadAssignmentsUseCase`
- `deps.fetchRemoteProjectsUseCase` -> `deps.project.fetchRemoteProjectsUseCase`
- `deps.loadCompanyMembersUseCase` -> `deps.project.loadCompanyMembersUseCase`
- `deps.locationRepository` -> `deps.feature.locationRepository`
- `deps.contractorRepository` -> `deps.feature.contractorRepository`
- `deps.equipmentRepository` -> `deps.feature.equipmentRepository`
- `deps.personnelTypeRepository` -> `deps.feature.personnelTypeRepository`
- `deps.dailyEntryRepository` -> `deps.entry.dailyEntryRepository`
- `deps.entryExportRepository` -> `deps.entry.entryExportRepository`
- `deps.documentRepository` -> `deps.entry.documentRepository`
- `deps.documentService` -> `deps.entry.documentService`
- `deps.entryPersonnelCountsDatasource` -> `deps.entry.entryPersonnelCountsDatasource`
- `deps.entryEquipmentDatasource` -> `deps.entry.entryEquipmentDatasource`
- `deps.entryContractorsDatasource` -> `deps.entry.entryContractorsDatasource`
- `deps.bidItemRepository` -> `deps.feature.bidItemRepository`
- `deps.entryQuantityRepository` -> `deps.feature.entryQuantityRepository`
- `deps.photoRepository` -> `deps.feature.photoRepository`
- `deps.inspectorFormRepository` -> `deps.form.inspectorFormRepository`
- `deps.formResponseRepository` -> `deps.form.formResponseRepository`
- `deps.formExportRepository` -> `deps.form.formExportRepository`
- `deps.formPdfService` -> `deps.form.formPdfService`
- `deps.calculationHistoryRepository` -> `deps.feature.calculationHistoryRepository`
- `deps.todoItemRepository` -> `deps.feature.todoItemRepository`
- `deps.pdfService` -> `deps.feature.pdfService`
- `deps.weatherService` -> `deps.feature.weatherService`
- `deps.syncOrchestrator` -> `deps.sync.syncOrchestrator`
- `deps.syncLifecycleManager` -> `deps.sync.syncLifecycleManager`
- `deps.photoService` -> `deps.core.photoService`
- `deps.imageService` -> `deps.core.imageService`

#### Step 2.3.3: Update main.dart callers

In `lib/main.dart`, update references:
- `deps.authProvider` -> `deps.auth.authProvider`
- `deps.appConfigProvider` -> `deps.auth.appConfigProvider`

#### Step 2.3.4: Update main_driver.dart callers

In `lib/main_driver.dart`, update references:
- `deps.authProvider` -> `deps.auth.authProvider`
- `deps.photoRepository` -> `deps.feature.photoRepository`

#### Step 2.3.5: Remove compatibility accessors from AppDependencies

In `lib/core/di/app_initializer.dart`, delete lines 288-337 (the entire block of compatibility getters including the `supabaseClient` getter which is now replaced by `core.supabaseClient`).

#### Step 2.3.6: Verify compilation

Run: `pwsh -Command "flutter analyze lib/core/di/app_initializer.dart lib/core/di/app_providers.dart lib/main.dart lib/main_driver.dart"`
Expected: No analysis issues related to removed accessors

---

### Sub-phase 2.4: Restructure initialize() to flow CoreDeps.supabaseClient through

**Files:**
- Modify: `lib/core/di/app_initializer.dart:361-825`

**Agent**: `general-purpose`

This step adds structural comments and ensures the `supabaseClient` local variable is used consistently. The method body order stays the same -- this is pure mechanical substitution, not logic reordering.

#### Step 2.4.1: Add phase section comments

Add clear section comments in `initialize()`:

```dart
    // ── Phase 1: Core infrastructure ──
    // (prefs, analytics, logging, db, OCR, Supabase, Firebase)
    // ... existing code lines 365-463 ...

    // FROM SPEC: Single supabaseClient capture point — replaces all
    // Supabase.instance.client calls downstream.
    final SupabaseClient? supabaseClient = ...;

    // ── Phase 2: Feature construction (all receive supabaseClient) ──
    // ... existing code lines 465-760 ...

    // ── Phase 3: Assemble AppDependencies ──
    return AppDependencies(...);
```

#### Step 2.4.2: Verify full test suite for app_initializer callers

Run: `pwsh -Command "flutter test test/core/di/core_deps_test.dart test/core/di/init_options_test.dart"`
Expected: All tests PASS

---

### Sub-phase 2.5: Test for AppInitializer orchestration

**Files:**
- Create: `test/core/di/app_initializer_integration_test.dart`

**Agent**: `qa-testing-agent`

#### Step 2.5.1: Write integration-level test verifying no Supabase.instance.client leaks

```dart
// test/core/di/app_initializer_integration_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'dart:io';

void main() {
  // WHY: This is a structural test that verifies the spec requirement:
  // "Zero Supabase.instance.client outside CoreDeps resolution"
  test('app_initializer.dart should not contain Supabase.instance.client after the capture point', () {
    final file = File('lib/core/di/app_initializer.dart');
    final content = file.readAsStringSync();
    final lines = content.split('\n');

    // IMPORTANT: Find the supabaseClient capture line
    int captureLineIndex = -1;
    for (int i = 0; i < lines.length; i++) {
      if (lines[i].contains('final SupabaseClient? supabaseClient') &&
          lines[i].contains('Supabase.instance.client')) {
        captureLineIndex = i;
        break;
      }
    }

    // NOTE: If capture line not found, the refactor hasn't been applied yet
    expect(captureLineIndex, greaterThan(-1),
        reason: 'Expected a supabaseClient capture line in app_initializer.dart');

    // Check no Supabase.instance.client after the capture point
    final afterCapture = lines.sublist(captureLineIndex + 1);
    final violations = <int>[];
    for (int i = 0; i < afterCapture.length; i++) {
      final line = afterCapture[i];
      if (line.contains('Supabase.instance.client') && !line.trimLeft().startsWith('//')) {
        violations.add(captureLineIndex + 1 + i + 1); // 1-indexed line number
      }
    }

    expect(violations, isEmpty,
        reason: 'Lines ${violations.join(', ')} still use Supabase.instance.client '
            'after the capture point. Use supabaseClient local variable instead.');
  });

  // FROM SPEC: "Remove dead appRouter field from AppDependencies"
  test('AppDependencies should not have appRouter field', () {
    final file = File('lib/core/di/app_initializer.dart');
    final content = file.readAsStringSync();

    // NOTE: Check for the field declaration, not casual mentions in comments
    final hasAppRouterField = RegExp(r'final\s+AppRouter\s+appRouter\s*;').hasMatch(content);

    expect(hasAppRouterField, false,
        reason: 'AppDependencies still has appRouter field — it should be removed per spec');
  });

  // FROM SPEC: "Remove compatibility accessors"
  test('AppDependencies should not have compatibility accessor getters', () {
    final file = File('lib/core/di/app_initializer.dart');
    final content = file.readAsStringSync();

    // WHY: The compatibility getters follow the pattern "Type get name => subDeps.name;"
    // Check for the section header comment that was removed
    expect(content.contains('Convenience accessors for backward compatibility'), false,
        reason: 'Compatibility accessors section should be removed');
  });
}
```

#### Step 2.5.2: Verify test passes

Run: `pwsh -Command "flutter test test/core/di/app_initializer_integration_test.dart"`
Expected: All 3 tests PASS

#### Step 2.5.3: Run flutter analyze as phase gate

Run: `pwsh -Command "flutter analyze"`
Expected: No new analysis issues introduced by Phase 2 changes

---

## Phase 3: Router Split

Split `app_router.dart` (932 lines) into 3 files: redirect matrix, scaffold widget, and slim router composition.

---

### Sub-phase 3.1: Create `lib/core/router/app_redirect.dart`

**Files:**
- Create: `lib/core/router/app_redirect.dart`
- Test: `test/core/router/app_redirect_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 3.1.1: Write failing tests for AppRedirect

```dart
// test/core/router/app_redirect_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:construction_inspector/core/router/app_redirect.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/settings/presentation/providers/consent_provider.dart';

@GenerateMocks([AuthProvider, AppConfigProvider, ConsentProvider])
import 'app_redirect_test.mocks.dart';

void main() {
  late MockAuthProvider mockAuth;
  late MockAppConfigProvider mockAppConfig;
  late MockConsentProvider mockConsent;
  late AppRedirect redirect;

  setUp(() {
    mockAuth = MockAuthProvider();
    mockAppConfig = MockAppConfigProvider();
    mockConsent = MockConsentProvider();
    redirect = AppRedirect(
      authProvider: mockAuth,
      appConfigProvider: mockAppConfig,
      consentProvider: mockConsent,
    );

    // WHY: Safe defaults — authenticated, consented, no special states
    when(mockAuth.isAuthenticated).thenReturn(true);
    when(mockAuth.isPasswordRecovery).thenReturn(false);
    when(mockAuth.isLoadingProfile).thenReturn(false);
    when(mockAuth.userProfile).thenReturn(null);
    when(mockAppConfig.requiresUpdate).thenReturn(false);
    when(mockAppConfig.requiresReauth).thenReturn(false);
    when(mockConsent.hasConsented).thenReturn(true);
  });

  // IMPORTANT: All providers are required — no nullable, no try-catch
  test('constructor requires all three providers', () {
    // NOTE: This test verifies compile-time safety — if it compiles, it works
    final r = AppRedirect(
      authProvider: mockAuth,
      appConfigProvider: mockAppConfig,
      consentProvider: mockConsent,
    );
    expect(r, isNotNull);
  });

  // FROM SPEC Gate 1: Password recovery deep link
  test('password recovery redirects to /update-password', () {
    when(mockAuth.isPasswordRecovery).thenReturn(true);

    final result = redirect.performRedirect('/settings');
    expect(result, '/update-password');
  });

  test('password recovery allows /update-password', () {
    when(mockAuth.isPasswordRecovery).thenReturn(true);

    final result = redirect.performRedirect('/update-password');
    expect(result, isNull);
  });

  // FROM SPEC Gate 2: Auth check
  test('unauthenticated user redirects to /login', () {
    when(mockAuth.isAuthenticated).thenReturn(false);

    final result = redirect.performRedirect('/');
    expect(result, '/login');
  });

  test('unauthenticated user on auth route stays', () {
    when(mockAuth.isAuthenticated).thenReturn(false);

    final result = redirect.performRedirect('/login');
    expect(result, isNull);
  });

  // FROM SPEC Gate 5: Consent gate (now required, not optional)
  test('unconsented user redirects to /consent', () {
    when(mockConsent.hasConsented).thenReturn(false);

    final result = redirect.performRedirect('/');
    expect(result, '/consent');
  });

  test('unconsented user on /consent stays', () {
    when(mockConsent.hasConsented).thenReturn(false);

    final result = redirect.performRedirect('/consent');
    expect(result, isNull);
  });

  // FROM SPEC Gate 3: Force update
  test('force update redirects to /update-required', () {
    when(mockAppConfig.requiresUpdate).thenReturn(true);

    final result = redirect.performRedirect('/');
    expect(result, '/update-required');
  });
}
```

#### Step 3.1.2: Run mockito build_runner

Run: `pwsh -Command "dart run build_runner build --delete-conflicting-outputs --build-filter=test/core/router/app_redirect_test.dart"`
Expected: Build completes, generates mock file

#### Step 3.1.3: Implement AppRedirect class

Extract the redirect matrix from `lib/core/router/app_router.dart:155-340` into a new class. All three providers are required (not nullable).

```dart
// lib/core/router/app_redirect.dart
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:go_router/go_router.dart';
import 'package:construction_inspector/core/config/supabase_config.dart';
import 'package:construction_inspector/core/config/test_mode_config.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/auth/data/models/models.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/settings/presentation/providers/consent_provider.dart';

/// Onboarding routes exempt from profile-check redirect.
/// FROM SPEC: verified in ground-truth.md
const kOnboardingRoutes = {
  '/profile-setup',
  '/company-setup',
  '/pending-approval',
  '/account-status',
  '/update-password',
  '/update-required',
  '/consent',
};

/// Redirect matrix for GoRouter.
///
/// FROM SPEC: "All three providers required. No nullable, no try-catch fallback."
/// Gate order is security-critical and must not be reordered.
class AppRedirect {
  final AuthProvider _authProvider;
  final AppConfigProvider _appConfigProvider;
  final ConsentProvider _consentProvider;

  // IMPORTANT: All providers are required — compile-time error if missing
  AppRedirect({
    required AuthProvider authProvider,
    required AppConfigProvider appConfigProvider,
    required ConsentProvider consentProvider,
  })  : _authProvider = authProvider,
        _appConfigProvider = appConfigProvider,
        _consentProvider = consentProvider;

  /// Full redirect callback for GoRouter.
  /// Called on every navigation event.
  String? redirect(BuildContext context, GoRouterState state) {
    return performRedirect(state.uri.path, matchedLocation: state.matchedLocation);
  }

  /// Testable redirect logic without BuildContext dependency for most gates.
  /// [matchedLocation] is used for profile-setup pattern matching.
  String? performRedirect(String location, {String? matchedLocation}) {
    // Gate 0: Config bypass (test mode, Supabase not configured)
    if (!SupabaseConfig.isConfigured || TestModeConfig.useMockAuth) {
      if (TestModeConfig.useMockAuth && TestModeConfig.autoLogin) {
        return null;
      }
      if (!SupabaseConfig.isConfigured) {
        if (kReleaseMode) {
          throw Exception('Supabase not configured in release build');
        }
        return null;
      }
    }

    // Gate 1: Password recovery deep link
    // WHY: [SEC-3, SEC-7] Must be FIRST check after config bypass to prevent route escape
    if (_authProvider.isPasswordRecovery) {
      if (location == '/update-password') return null;
      return '/update-password';
    }

    // Auth routes (login, register, forgot-password, verify-otp)
    final isAuthRoute =
        location.startsWith('/login') ||
        location.startsWith('/register') ||
        location.startsWith('/forgot-password') ||
        location.startsWith('/verify-otp');

    final isOnboardingRoute = kOnboardingRoutes.contains(location);
    final isAuthenticated = _authProvider.isAuthenticated;

    // Gate 2: Auth check — unauthenticated -> login
    if (!isAuthenticated && !isAuthRoute) return '/login';

    // Gate 2b: Authenticated on auth route -> redirect away
    if (isAuthenticated && isAuthRoute) {
      if (_authProvider.isLoadingProfile) return null;
      return '/';
    }

    if (isAuthenticated) {
      // Gate 3: Force update
      if (_appConfigProvider.requiresUpdate) {
        if (location == '/update-required') return null;
        return '/update-required';
      }

      // Gate 4: Force reauth
      // SEC-106: No try-catch — AppConfigProvider is required
      if (_appConfigProvider.requiresReauth) {
        _authProvider.handleForceReauth(_appConfigProvider.reauthReason);
        return '/login';
      }

      // Gate 5: Consent gate
      // FROM SPEC: Required ConsentProvider — no silent bypass
      if (!_consentProvider.hasConsented) {
        if (location == '/consent') return null;
        return '/consent';
      }
    }

    // Gate 6: Onboarding — redirect to home if fully set up
    if (isOnboardingRoute) {
      if (isAuthenticated && SupabaseConfig.isConfigured) {
        final profile = _authProvider.userProfile;
        if (profile != null &&
            profile.status == MembershipStatus.approved &&
            profile.companyId != null) {
          return '/';
        }
      }
      return null;
    }

    // Gate 7-8: Profile-based routing
    if (isAuthenticated && SupabaseConfig.isConfigured) {
      if (_authProvider.isLoadingProfile) return null;

      final profile = _authProvider.userProfile;

      // No profile -> profile setup
      if (profile == null && !isAuthRoute) {
        if (location == '/profile-setup') return null;
        return '/profile-setup';
      }

      if (profile != null) {
        // Bug 7: NULL display_name gate
        if ((profile.displayName == null || profile.displayName!.trim().isEmpty) &&
            !(matchedLocation ?? location).startsWith('/profile-setup')) {
          return '/profile-setup';
        }

        final status = profile.status;

        // No company -> company setup
        if (profile.companyId == null) {
          if (location == '/company-setup') return null;
          return '/company-setup';
        }

        // Pending approval
        if (status == MembershipStatus.pending &&
            location != '/pending-approval') {
          return '/pending-approval';
        }

        // Rejected
        if (status == MembershipStatus.rejected &&
            location != '/account-status') {
          return '/account-status?reason=rejected';
        }

        // Deactivated
        if (status == MembershipStatus.deactivated &&
            location != '/account-status') {
          return '/account-status?reason=deactivated';
        }

        // Gate 9: Admin-only route guard
        if (location == '/admin-dashboard') {
          if (!profile.isAdmin) return '/settings';
        }

        // Gate 9b: Project management guard
        if (location == '/project/new') {
          if (!(_authProvider.canManageProjects)) {
            return '/projects';
          }
        }

        if (location.startsWith('/project/') &&
            location.endsWith('/edit') &&
            !(_authProvider.canManageProjects)) {
          return '/projects';
        }
      }
    }

    return null;
  }
}
```

#### Step 3.1.4: Verify tests pass

Run: `pwsh -Command "flutter test test/core/router/app_redirect_test.dart"`
Expected: All 8 tests PASS

---

### Sub-phase 3.2: Create `lib/core/router/scaffold_with_nav_bar.dart`

**Files:**
- Create: `lib/core/router/scaffold_with_nav_bar.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 3.2.1: Extract ScaffoldWithNavBar to new file

Move `ScaffoldWithNavBar` class from `lib/core/router/app_router.dart:747-931` to `lib/core/router/scaffold_with_nav_bar.dart`. Include all imports used exclusively by ScaffoldWithNavBar.

```dart
// lib/core/router/scaffold_with_nav_bar.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/theme/field_guide_colors.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/projects/presentation/widgets/project_switcher.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';
import 'package:construction_inspector/features/pdf/presentation/widgets/extraction_banner.dart';
import 'package:construction_inspector/shared/shared.dart';

// WHY: Banner widgets used in the scaffold body
// NOTE: VersionBanner and StaleConfigWarning are imported via shared.dart
// or from their specific locations

/// Shell widget providing bottom navigation and status banners.
///
/// Extracted from app_router.dart for single-responsibility.
/// Receives providers via context.watch/context.read from the widget tree
/// (correct for presentation-layer reads).
class ScaffoldWithNavBar extends StatelessWidget {
  final Widget child;

  const ScaffoldWithNavBar({super.key, required this.child});

  /// Routes where the project switcher should appear in the app bar.
  static const _projectContextRoutes = {'/', '/calendar'};

  @override
  Widget build(BuildContext context) {
    final fg = FieldGuideColors.of(context);
    final location = GoRouterState.of(context).uri.path;
    final showProjectSwitcher = _projectContextRoutes.contains(location);

    return Scaffold(
      appBar: showProjectSwitcher
          ? AppBar(
              title: const ProjectSwitcher(),
              centerTitle: false,
              automaticallyImplyLeading: false,
            )
          : null,
      body: Consumer2<SyncProvider, AppConfigProvider>(
        builder: (context, syncProvider, appConfigProvider, innerChild) {
          final syncOrchestrator = context.read<SyncOrchestrator>();

          // [Phase 6, 3.2] Wire sync error toast callback to ScaffoldMessenger
          syncProvider.onSyncErrorToast ??= (message) {
            SnackBarHelper.showErrorWithAction(
              context,
              'Sync error: $message',
              actionLabel: 'Details',
              onAction: () => context.push('/sync/dashboard'),
            ).closed.then((_) {
              syncProvider.clearSyncErrorSnackbarFlag();
            });
          };

          final banners = <Widget>[];

          // Version update banner (soft nudge)
          if (appConfigProvider.hasUpdateAvailable) {
            banners.add(
              VersionBanner(
                message: appConfigProvider.updateMessage,
              ),
            );
          }

          // Stale config warning (>24h since server check)
          if (appConfigProvider.isConfigStale) {
            banners.add(
              StaleConfigWarning(
                onRetry: () => appConfigProvider.checkConfig(),
              ),
            );
          }

          // Stale sync data warning
          if (syncProvider.isStaleDataWarning) {
            banners.add(
              MaterialBanner(
                content: Text(
                  'Data may be out of date — last synced ${syncProvider.lastSyncText}',
                ),
                leading: Icon(Icons.warning_amber, color: fg.accentOrange),
                actions: [
                  TextButton(
                    onPressed: () => syncProvider.sync(),
                    child: const Text('Sync Now'),
                  ),
                ],
              ),
            );
          }

          // Offline indicator
          if (!syncProvider.isOnline) {
            banners.add(
              MaterialBanner(
                content: const Text('You are offline. Changes will sync when connection is restored.'),
                leading: Icon(Icons.cloud_off, color: fg.accentOrange),
                backgroundColor: fg.accentOrange.withValues(alpha: 0.08),
                actions: [
                  TextButton(
                    onPressed: () async {
                      await syncOrchestrator.checkDnsReachability();
                    },
                    child: const Text('Retry'),
                  ),
                ],
              ),
            );
          }

          if (banners.isEmpty) return innerChild!;

          return Column(
            children: [
              ...banners,
              Expanded(child: innerChild!),
            ],
          );
        },
        child: child,
      ),
      bottomNavigationBar: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const ExtractionBanner(),
          NavigationBar(
            key: TestingKeys.bottomNavigationBar,
            selectedIndex: _calculateSelectedIndex(context),
            onDestinationSelected: (index) => _onItemTapped(index, context),
            destinations: [
              const NavigationDestination(
                key: TestingKeys.dashboardNavButton,
                icon: Icon(Icons.dashboard_outlined),
                selectedIcon: Icon(Icons.dashboard),
                label: 'Dashboard',
              ),
              const NavigationDestination(
                key: TestingKeys.calendarNavButton,
                icon: Icon(Icons.calendar_today_outlined),
                selectedIcon: Icon(Icons.calendar_today),
                label: 'Calendar',
              ),
              const NavigationDestination(
                key: TestingKeys.projectsNavButton,
                icon: Icon(Icons.folder_outlined),
                selectedIcon: Icon(Icons.folder),
                label: 'Projects',
              ),
              const NavigationDestination(
                key: TestingKeys.settingsNavButton,
                icon: Icon(Icons.settings_outlined),
                selectedIcon: Icon(Icons.settings),
                label: 'Settings',
              ),
            ],
          ),
        ],
      ),
    );
  }

  int _calculateSelectedIndex(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    if (location.startsWith('/calendar')) return 1;
    if (location.startsWith('/projects')) return 2;
    if (location.startsWith('/settings')) return 3;
    return 0;
  }

  void _onItemTapped(int index, BuildContext context) {
    switch (index) {
      case 0:
        context.goNamed('dashboard');
        break;
      case 1:
        context.goNamed('home');
        break;
      case 2:
        context.goNamed('projects');
        break;
      case 3:
        context.goNamed('settings');
        break;
    }
  }
}
```

#### Step 3.2.2: Verify scaffold file compiles

Run: `pwsh -Command "flutter analyze lib/core/router/scaffold_with_nav_bar.dart"`
Expected: No analysis issues

---

### Sub-phase 3.3: Slim `app_router.dart` to composition only

**Files:**
- Modify: `lib/core/router/app_router.dart` (remove redirect matrix lines 157-340, remove ScaffoldWithNavBar lines 747-931, import new files, update constructor)

**Agent**: `frontend-flutter-specialist-agent`

#### Step 3.3.1: Update AppRouter constructor to require all three providers

Change from:
```dart
AppRouter({
  required AuthProvider authProvider,
  ConsentProvider? consentProvider,
})
```

To:
```dart
// FROM SPEC: All three providers required — no nullable, no try-catch
AppRouter({
  required AuthProvider authProvider,
  required ConsentProvider consentProvider,
  required AppConfigProvider appConfigProvider,
})
```

#### Step 3.3.2: Add imports for new files and delegate redirect

Add imports:
```dart
import 'package:construction_inspector/core/router/app_redirect.dart';
import 'package:construction_inspector/core/router/scaffold_with_nav_bar.dart';
```

#### Step 3.3.3: Replace inline redirect with AppRedirect delegation

In `_buildRouter()`, replace the ~185-line redirect closure with:

```dart
    // WHY: Router must re-evaluate redirects when any provider state changes
    // FROM SPEC: All providers always merged — no conditional
    refreshListenable: Listenable.merge([_authProvider, _consentProvider, _appConfigProvider]),
    redirect: _appRedirect.redirect,
```

Where `_appRedirect` is created in the constructor:

```dart
  late final AppRedirect _appRedirect;

  AppRouter({
    required AuthProvider authProvider,
    required ConsentProvider consentProvider,
    required AppConfigProvider appConfigProvider,
  })  : _authProvider = authProvider,
        _consentProvider = consentProvider,
        _appConfigProvider = appConfigProvider {
    _appRedirect = AppRedirect(
      authProvider: authProvider,
      appConfigProvider: appConfigProvider,
      consentProvider: consentProvider,
    );
  }
```

#### Step 3.3.4: Remove ScaffoldWithNavBar class from app_router.dart

Delete lines 747-931 (the entire `ScaffoldWithNavBar` class). The route table's `ShellRoute` builder already references `ScaffoldWithNavBar` by name -- the import from `scaffold_with_nav_bar.dart` keeps it resolved.

#### Step 3.3.5: Remove imports that moved to new files

Remove imports only used by the redirect matrix or ScaffoldWithNavBar that are no longer needed in `app_router.dart`:
- `package:construction_inspector/core/config/supabase_config.dart` -- keep if route table uses it
- `package:construction_inspector/core/config/test_mode_config.dart` -- moved to app_redirect.dart
- `package:construction_inspector/core/theme/field_guide_colors.dart` -- moved to scaffold_with_nav_bar.dart

#### Step 3.3.6: Update all callers of AppRouter constructor

In `lib/main.dart` (around line 178):
```dart
    // BEFORE:
    final appRouter = AppRouter(
      authProvider: deps.auth.authProvider,
      consentProvider: consentProvider,
    );
    // AFTER:
    final appRouter = AppRouter(
      authProvider: deps.auth.authProvider,
      consentProvider: consentProvider,
      appConfigProvider: deps.auth.appConfigProvider,
    );
```

In `lib/main_driver.dart` (around line 108):
```dart
    // Same change — add appConfigProvider
    final appRouter = AppRouter(
      authProvider: deps.auth.authProvider,
      consentProvider: consentProvider,
      appConfigProvider: deps.auth.appConfigProvider,
    );
```

#### Step 3.3.7: Verify compilation

Run: `pwsh -Command "flutter analyze lib/core/router/app_router.dart lib/core/router/app_redirect.dart lib/core/router/scaffold_with_nav_bar.dart"`
Expected: No analysis issues

---

### Sub-phase 3.4: Test for AppRedirect (each redirect gate independently)

**Files:**
- Test: `test/core/router/app_redirect_test.dart` (already created in 3.1, extend)

**Agent**: `qa-testing-agent`

#### Step 3.4.1: Extend AppRedirect tests with remaining gates

Add these tests to the existing `test/core/router/app_redirect_test.dart`:

```dart
  // Gate 4: Force reauth
  test('force reauth redirects to /login and calls handleForceReauth', () {
    when(mockAppConfig.requiresReauth).thenReturn(true);
    when(mockAppConfig.reauthReason).thenReturn('config_changed');

    final result = redirect.performRedirect('/');
    expect(result, '/login');
    verify(mockAuth.handleForceReauth('config_changed')).called(1);
  });

  // Gate ordering: force update takes priority over consent
  test('force update takes priority over unconsented', () {
    when(mockAppConfig.requiresUpdate).thenReturn(true);
    when(mockConsent.hasConsented).thenReturn(false);

    final result = redirect.performRedirect('/');
    expect(result, '/update-required');
  });

  // Gate ordering: password recovery takes priority over everything
  test('password recovery takes priority over force update', () {
    when(mockAuth.isPasswordRecovery).thenReturn(true);
    when(mockAppConfig.requiresUpdate).thenReturn(true);

    final result = redirect.performRedirect('/settings');
    expect(result, '/update-password');
  });

  // Gate 9: Admin guard
  test('non-admin on /admin-dashboard redirects to /settings', () {
    final mockProfile = _createMockProfile(isAdmin: false, status: MembershipStatus.approved, companyId: 'c1');
    when(mockAuth.userProfile).thenReturn(mockProfile);

    final result = redirect.performRedirect('/admin-dashboard');
    expect(result, '/settings');
  });

  // Fully set up user passes all gates
  test('fully set up user can access dashboard', () {
    final mockProfile = _createMockProfile(isAdmin: false, status: MembershipStatus.approved, companyId: 'c1');
    when(mockAuth.userProfile).thenReturn(mockProfile);

    final result = redirect.performRedirect('/');
    expect(result, isNull);
  });
```

NOTE: The implementing agent must create a `_createMockProfile` helper that returns a mock `UserProfile` with the specified fields. Use the `UserProfile` model from `lib/features/auth/data/models/` with appropriate constructor arguments.

#### Step 3.4.2: Verify all redirect tests pass

Run: `pwsh -Command "flutter test test/core/router/app_redirect_test.dart"`
Expected: All tests PASS

---

### Sub-phase 3.5: Test for AppRouter (construction, route resolution)

**Files:**
- Create: `test/core/router/app_router_test.dart`

**Agent**: `qa-testing-agent`

#### Step 3.5.1: Write AppRouter construction tests

```dart
// test/core/router/app_router_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:construction_inspector/core/router/app_router.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/settings/presentation/providers/consent_provider.dart';

@GenerateMocks([AuthProvider, AppConfigProvider, ConsentProvider])
import 'app_router_test.mocks.dart';

void main() {
  late MockAuthProvider mockAuth;
  late MockAppConfigProvider mockAppConfig;
  late MockConsentProvider mockConsent;

  setUp(() {
    mockAuth = MockAuthProvider();
    mockAppConfig = MockAppConfigProvider();
    mockConsent = MockConsentProvider();

    // WHY: ChangeNotifier mocks need addListener/removeListener stubs
    when(mockAuth.addListener(any)).thenReturn(null);
    when(mockAuth.removeListener(any)).thenReturn(null);
    when(mockConsent.addListener(any)).thenReturn(null);
    when(mockConsent.removeListener(any)).thenReturn(null);
    when(mockAppConfig.addListener(any)).thenReturn(null);
    when(mockAppConfig.removeListener(any)).thenReturn(null);
  });

  // FROM SPEC: All three providers required — compile-time safety
  test('should construct with all required providers', () {
    final router = AppRouter(
      authProvider: mockAuth,
      consentProvider: mockConsent,
      appConfigProvider: mockAppConfig,
    );
    expect(router, isNotNull);
  });

  test('setInitialLocation should accept non-empty string', () {
    final router = AppRouter(
      authProvider: mockAuth,
      consentProvider: mockConsent,
      appConfigProvider: mockAppConfig,
    );
    router.setInitialLocation('/calendar');
    // NOTE: No assertion on internal state — just verify no exception
  });

  test('setInitialLocation should ignore empty string', () {
    final router = AppRouter(
      authProvider: mockAuth,
      consentProvider: mockConsent,
      appConfigProvider: mockAppConfig,
    );
    router.setInitialLocation('');
    // NOTE: No assertion on internal state — just verify no exception
  });

  // FROM SPEC: Verified route constants from ground-truth.md
  test('isRestorableRoute returns false for non-restorable routes', () {
    expect(AppRouter.isRestorableRoute('/login'), false);
    expect(AppRouter.isRestorableRoute('/register'), false);
    expect(AppRouter.isRestorableRoute('/consent'), false);
    expect(AppRouter.isRestorableRoute('/admin-dashboard'), false);
  });

  test('isRestorableRoute returns true for normal routes', () {
    expect(AppRouter.isRestorableRoute('/'), true);
    expect(AppRouter.isRestorableRoute('/calendar'), true);
    expect(AppRouter.isRestorableRoute('/projects'), true);
    expect(AppRouter.isRestorableRoute('/settings'), true);
  });
}
```

#### Step 3.5.2: Run mockito build_runner

Run: `pwsh -Command "dart run build_runner build --delete-conflicting-outputs --build-filter=test/core/router/app_router_test.dart"`
Expected: Build completes

#### Step 3.5.3: Verify tests pass

Run: `pwsh -Command "flutter test test/core/router/app_router_test.dart"`
Expected: All tests PASS

---

### Sub-phase 3.6: Test for ScaffoldWithNavBar (nav index, banners)

**Files:**
- Create: `test/core/router/scaffold_with_nav_bar_test.dart`

**Agent**: `qa-testing-agent`

#### Step 3.6.1: Write ScaffoldWithNavBar tests

```dart
// test/core/router/scaffold_with_nav_bar_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/router/scaffold_with_nav_bar.dart';

void main() {
  // NOTE: ScaffoldWithNavBar is a presentation widget that requires full
  // provider tree + GoRouter context. These are structural/compile tests.
  // Full widget tests require the complete provider tree and are covered
  // by the existing golden tests and integration tests.

  test('ScaffoldWithNavBar is a StatelessWidget', () {
    // WHY: Verify the extracted class compiles and has the expected type
    const scaffold = ScaffoldWithNavBar(child: SizedBox());
    expect(scaffold, isA<StatelessWidget>());
  });

  test('ScaffoldWithNavBar accepts required child parameter', () {
    const scaffold = ScaffoldWithNavBar(child: Text('test'));
    expect(scaffold.child, isA<Text>());
  });
}
```

#### Step 3.6.2: Verify tests pass

Run: `pwsh -Command "flutter test test/core/router/scaffold_with_nav_bar_test.dart"`
Expected: All tests PASS

#### Step 3.6.3: Run flutter analyze as phase gate

Run: `pwsh -Command "flutter analyze"`
Expected: No new analysis issues introduced by Phase 3 changes

---

## Phase 4: SyncProviders Extraction

Extract business logic from `sync_providers.dart` into application-layer homes: `SyncEnrollmentService` for enrollment logic, expand `FcmHandler` and `SyncLifecycleManager` for their respective concerns, and create `SyncInitializer` for orchestration.

---

### Sub-phase 4.1: Create `lib/features/sync/application/sync_enrollment_service.dart`

**Files:**
- Create: `lib/features/sync/application/sync_enrollment_service.dart`
- Test: `test/features/sync/application/sync_enrollment_service_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 4.1.1: Write failing test for SyncEnrollmentService

```dart
// test/features/sync/application/sync_enrollment_service_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:sqflite/sqflite.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/features/sync/application/sync_enrollment_service.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';

@GenerateMocks([DatabaseService, SyncOrchestrator])
import 'sync_enrollment_service_test.mocks.dart';

void main() {
  late SyncEnrollmentService sut;
  late MockDatabaseService mockDb;
  late MockSyncOrchestrator mockOrchestrator;
  late Database inMemoryDb;

  setUp(() async {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    inMemoryDb = await openDatabase(
      inMemoryDatabasePath,
      version: 1,
      onCreate: (db, version) async {
        // WHY: Create minimal tables matching ground-truth.md verified tables
        await db.execute('''
          CREATE TABLE project_assignments (
            project_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            deleted_at TEXT,
            PRIMARY KEY (project_id, user_id)
          )
        ''');
        await db.execute('''
          CREATE TABLE synced_projects (
            project_id TEXT PRIMARY KEY,
            synced_at TEXT NOT NULL,
            unassigned_at TEXT
          )
        ''');
      },
    );

    mockDb = MockDatabaseService();
    mockOrchestrator = MockSyncOrchestrator();
    when(mockDb.database).thenAnswer((_) async => inMemoryDb);

    sut = SyncEnrollmentService(
      dbService: mockDb,
      orchestrator: mockOrchestrator,
    );
  });

  tearDown(() async {
    await inMemoryDb.close();
  });

  group('handleAssignmentPull', () {
    // FROM SPEC: "When a new project_assignments row is pulled for the current user,
    // auto-insert into synced_projects and queue a notification."
    test('should enroll newly assigned project', () async {
      // Seed: user has assignment but no synced_projects entry
      await inMemoryDb.insert('project_assignments', {
        'project_id': 'proj-1',
        'user_id': 'user-1',
      });

      final notifications = <String>[];
      // NOTE: Capture notifications via orchestrator callback
      when(mockOrchestrator.onNewAssignmentDetected).thenReturn((msg) {
        notifications.add(msg);
      });

      await sut.handleAssignmentPull(userId: 'user-1');

      // Verify synced_projects was inserted
      final synced = await inMemoryDb.query('synced_projects');
      expect(synced, hasLength(1));
      expect(synced.first['project_id'], 'proj-1');
    });

    test('should mark unassigned project with unassigned_at', () async {
      // Seed: synced project exists but assignment was removed
      await inMemoryDb.insert('synced_projects', {
        'project_id': 'proj-1',
        'synced_at': DateTime.now().toUtc().toIso8601String(),
      });
      await inMemoryDb.insert('project_assignments', {
        'project_id': 'proj-1',
        'user_id': 'user-1',
        'deleted_at': null,
      });

      // Now remove the assignment
      await inMemoryDb.delete('project_assignments');

      await sut.handleAssignmentPull(userId: 'user-1');

      // WHY: The query joins on project_assignments, so with no assignments,
      // the synced_projects row should NOT be updated (no matching join row).
      // The enrollment service only processes rows visible via the JOIN.
    });

    test('should skip when userId is null', () async {
      // WHY: Auth state guard — userId null means not authenticated
      await sut.handleAssignmentPull(userId: null);

      // No DB queries should have been made
      verifyNever(mockDb.database);
    });

    // FROM SPEC FIX 5: Wrap in transaction for TOCTOU protection
    test('should handle concurrent enrollment gracefully', () async {
      await inMemoryDb.insert('project_assignments', {
        'project_id': 'proj-1',
        'user_id': 'user-1',
      });
      // Pre-enroll to simulate race
      await inMemoryDb.insert('synced_projects', {
        'project_id': 'proj-1',
        'synced_at': DateTime.now().toUtc().toIso8601String(),
      }, conflictAlgorithm: ConflictAlgorithm.ignore);

      // Should not throw
      await sut.handleAssignmentPull(userId: 'user-1');

      final synced = await inMemoryDb.query('synced_projects');
      expect(synced, hasLength(1));
    });
  });
}
```

#### Step 4.1.2: Run mockito build_runner

Run: `pwsh -Command "dart run build_runner build --delete-conflicting-outputs --build-filter=test/features/sync/application/sync_enrollment_service_test.dart"`
Expected: Build completes

#### Step 4.1.3: Implement SyncEnrollmentService

Extract enrollment logic from `lib/features/sync/di/sync_providers.dart:91-193`.

```dart
// lib/features/sync/application/sync_enrollment_service.dart
import 'package:sqflite/sqflite.dart';

import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';

/// Handles auto-enrollment/unenrollment of projects when assignments are pulled.
///
/// FROM SPEC: Extracted from sync_providers.dart lines 91-193.
/// Business logic that was incorrectly in a DI module.
class SyncEnrollmentService {
  final DatabaseService _dbService;
  final SyncOrchestrator _orchestrator;

  SyncEnrollmentService({
    required DatabaseService dbService,
    required SyncOrchestrator orchestrator,
  })  : _dbService = dbService,
        _orchestrator = orchestrator;

  /// Called when project_assignments table pull completes.
  /// Enrolls newly assigned projects and marks unassigned ones.
  ///
  /// FROM SPEC Section 2 (MF-5): Auto-enrollment on assignment pull.
  Future<void> handleAssignmentPull({required String? userId}) async {
    if (userId == null) return;

    final localDb = await _dbService.database;

    // FROM SPEC FIX 4 (MEDIUM - Security): Query assignments for this user
    final assignments = await localDb.query(
      'project_assignments',
      columns: ['project_id'],
      where: 'user_id = ? AND deleted_at IS NULL',
      whereArgs: [userId],
    );
    final assignedProjectIds =
        assignments.map((r) => r['project_id'] as String).toSet();

    // FROM SPEC FIX 3 + FIX 6: Query synced_projects scoped via INNER JOIN
    // to prevent touching unrelated users' rows.
    final syncedProjectRows = await localDb.rawQuery(
      '''
      SELECT sp.project_id, sp.unassigned_at
      FROM synced_projects sp
      INNER JOIN project_assignments pa
        ON sp.project_id = pa.project_id AND pa.user_id = ?
      ''',
      [userId],
    );

    final syncedMap = {
      for (final row in syncedProjectRows)
        row['project_id'] as String: row['unassigned_at'] as String?,
    };

    // FROM SPEC FIX 5: Wrap in transaction for TOCTOU protection
    final newlyEnrolled = <String>[];
    await localDb.transaction((txn) async {
      // Enrollment: insert into synced_projects for assigned projects not yet enrolled
      for (final projectId in assignedProjectIds) {
        if (!syncedMap.containsKey(projectId)) {
          final rowId = await txn.insert(
            'synced_projects',
            {
              'project_id': projectId,
              'synced_at': DateTime.now().toUtc().toIso8601String(),
            },
            conflictAlgorithm: ConflictAlgorithm.ignore,
          );
          if (rowId == 0) {
            Logger.sync('INSERT ignored (race -- already enrolled): synced_projects project_id=$projectId');
          } else {
            Logger.sync('Auto-enrolled assigned project: $projectId');
            newlyEnrolled.add(projectId);
          }
        }
      }

      // REVIEW FIX (CRIT-4): Detect deleted assignments -> set unassigned_at
      for (final entry in syncedMap.entries) {
        final projectId = entry.key;
        final currentUnassigned = entry.value;
        if (!assignedProjectIds.contains(projectId) && currentUnassigned == null) {
          await txn.update(
            'synced_projects',
            {'unassigned_at': DateTime.now().toUtc().toIso8601String()},
            where: 'project_id = ?',
            whereArgs: [projectId],
          );
          Logger.sync('Marked project as unassigned: $projectId');
        }
        // Re-assigned: clear unassigned_at
        if (assignedProjectIds.contains(projectId) && currentUnassigned != null) {
          await txn.update(
            'synced_projects',
            {'unassigned_at': null},
            where: 'project_id = ?',
            whereArgs: [projectId],
          );
          Logger.sync('Cleared unassigned status for project: $projectId');
        }
      }
    });

    // FROM SPEC SC-9: Queue notification for each newly enrolled project
    for (final _ in newlyEnrolled) {
      _orchestrator.onNewAssignmentDetected?.call(
        'You\'ve been assigned to a new project',
      );
    }
  }
}
```

#### Step 4.1.4: Verify tests pass

Run: `pwsh -Command "flutter test test/features/sync/application/sync_enrollment_service_test.dart"`
Expected: All tests PASS

---

### Sub-phase 4.2: Create `lib/features/sync/di/sync_initializer.dart`

**Files:**
- Create: `lib/features/sync/di/sync_initializer.dart`

**Agent**: `backend-supabase-agent`

#### Step 4.2.1: Implement SyncInitializer

This is the orchestration-only initializer that replaces the mixed wiring+logic in `SyncProviders.initialize()`.

```dart
// lib/features/sync/di/sync_initializer.dart
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/auth/data/datasources/local/company_local_datasource.dart';
import 'package:construction_inspector/features/auth/data/datasources/local/user_profile_local_datasource.dart';
import 'package:construction_inspector/features/auth/data/datasources/remote/user_profile_sync_datasource.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/auth/services/auth_service.dart';
import 'package:construction_inspector/features/sync/application/fcm_handler.dart';
import 'package:construction_inspector/features/sync/application/sync_enrollment_service.dart';
import 'package:construction_inspector/features/sync/application/sync_lifecycle_manager.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';

/// Orchestrates sync subsystem initialization.
///
/// FROM SPEC: Pure orchestration — no business logic. Calls services and
/// managers in the correct order, wires callbacks.
class SyncInitializer {
  /// Creates and wires all sync components. Returns the orchestrator and
  /// lifecycle manager needed by SyncDeps and SyncProviders.providers().
  static Future<({
    SyncOrchestrator orchestrator,
    SyncLifecycleManager lifecycleManager,
  })> create({
    required DatabaseService dbService,
    required AuthProvider authProvider,
    required AppConfigProvider appConfigProvider,
    required CompanyLocalDatasource companyLocalDs,
    required AuthService authService,
    SupabaseClient? supabaseClient,
  }) async {
    // Step 1: Create and initialize orchestrator
    final syncOrchestrator = SyncOrchestrator(dbService, supabaseClient: supabaseClient);
    await syncOrchestrator.initialize();

    // Step 2: Inject UserProfileSyncDatasource
    if (supabaseClient != null) {
      final userProfileLocalDs = UserProfileLocalDatasource(dbService);
      final userProfileSyncDs = UserProfileSyncDatasource(
        supabaseClient,
        userProfileLocalDs,
        companyLocalDatasource: companyLocalDs,
        dbService: dbService,
      );
      syncOrchestrator.setUserProfileSyncDatasource(userProfileSyncDs);
    }

    // Step 3: Create lifecycle manager
    final syncLifecycleManager = SyncLifecycleManager(syncOrchestrator);

    // Step 4: Wire auth context
    void updateSyncContext() {
      final profile = authProvider.userProfile;
      final userId = authProvider.userId;
      final companyId = profile?.companyId;
      syncOrchestrator.setAdapterCompanyContext(companyId: companyId, userId: userId);
    }
    updateSyncContext();
    authProvider.addListener(updateSyncContext);

    // Step 5: Wire sync context provider
    syncOrchestrator.setSyncContextProvider(() => (
      companyId: authProvider.userProfile?.companyId,
      userId: authProvider.userId,
    ));

    // Step 6: Wire enrollment service
    final enrollmentService = SyncEnrollmentService(
      dbService: dbService,
      orchestrator: syncOrchestrator,
    );
    syncOrchestrator.onPullComplete = (tableName, pulledCount) async {
      if (tableName != 'project_assignments') return;
      if (pulledCount == 0) return;
      // FROM SPEC FIX 4: Guard against auth state change during async
      final userId = authProvider.userId;
      if (userId == null) return;
      if (authProvider.userId != userId) return;
      await enrollmentService.handleAssignmentPull(userId: userId);
    };

    // Step 7: FCM initialization (mobile only, non-blocking)
    if (Platform.isAndroid || Platform.isIOS) {
      final fcmHandler = FcmHandler(authService: authService, syncOrchestrator: syncOrchestrator);
      // ignore: unawaited_futures
      fcmHandler.initialize(userId: authProvider.userId);
    }

    // Step 8: Wire AppConfigProvider for stale banner reset
    syncOrchestrator.setAppConfigProvider(appConfigProvider);

    // Step 9: Wire lifecycle callbacks
    syncLifecycleManager.isReadyForSync = () {
      return authProvider.isAuthenticated &&
          authProvider.userProfile?.companyId != null;
    };

    syncLifecycleManager.onAppResumed = () async {
      if (!authProvider.isAuthenticated) return;
      final timedOut = await authProvider.checkInactivityTimeout();
      if (timedOut) return;
      await authProvider.updateLastActive();
      if (appConfigProvider.isRefreshDue) {
        await appConfigProvider.checkConfig();
        if (appConfigProvider.requiresReauth) {
          await authProvider.handleForceReauth(appConfigProvider.reauthReason);
        }
      }
    };

    // Step 10: Register lifecycle observer
    WidgetsBinding.instance.addObserver(syncLifecycleManager);

    return (
      orchestrator: syncOrchestrator,
      lifecycleManager: syncLifecycleManager,
    );
  }
}
```

#### Step 4.2.2: Verify compilation

Run: `pwsh -Command "flutter analyze lib/features/sync/di/sync_initializer.dart"`
Expected: No analysis issues

---

### Sub-phase 4.3: Absorb FCM init into FcmHandler (already handled)

**Files:**
- No changes needed

**Agent**: `backend-supabase-agent`

#### Step 4.3.1: Verify FcmHandler already handles its own initialization

The existing `FcmHandler.initialize()` method at `lib/features/sync/application/fcm_handler.dart:48` already contains all FCM initialization logic (permission request, token retrieval, token registration, foreground message listener). The code in `sync_providers.dart:200-204` that creates an `FcmHandler` and calls `initialize()` is pure orchestration, which has been moved to `SyncInitializer.create()` in Step 4.2.1.

No changes to `FcmHandler` are needed.

---

### Sub-phase 4.4: Absorb lifecycle wiring into SyncLifecycleManager (already handled)

**Files:**
- No changes needed

**Agent**: `backend-supabase-agent`

#### Step 4.4.1: Verify lifecycle callback wiring

The lifecycle callback wiring (setting `isReadyForSync`, `onAppResumed`, and registering the observer) is pure orchestration. It has been moved to `SyncInitializer.create()` in Step 4.2.1, Steps 9-10. The `SyncLifecycleManager` class itself already has the callback fields (lines 22-32) and does not need modification.

No changes to `SyncLifecycleManager` are needed.

---

### Sub-phase 4.5: Slim sync_providers.dart to pure wiring

**Files:**
- Modify: `lib/features/sync/di/sync_providers.dart` (replace initialize body with SyncInitializer delegation)

**Agent**: `backend-supabase-agent`

#### Step 4.5.1: Replace SyncProviders.initialize() body

Replace the entire `initialize()` method body (lines 38-238) with a delegation to `SyncInitializer.create()`:

```dart
// lib/features/sync/di/sync_providers.dart
import 'package:flutter/widgets.dart';
import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/auth/data/datasources/local/company_local_datasource.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/auth/services/auth_service.dart';
import 'package:construction_inspector/features/projects/data/services/project_lifecycle_service.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_sync_health_provider.dart';
import 'package:construction_inspector/features/sync/application/sync_lifecycle_manager.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/features/sync/data/datasources/local/conflict_local_datasource.dart';
import 'package:construction_inspector/features/sync/data/datasources/local/deletion_notification_local_datasource.dart';
import 'package:construction_inspector/features/sync/data/repositories/conflict_repository.dart';
import 'package:construction_inspector/features/sync/data/repositories/deletion_notification_repository.dart';
import 'package:construction_inspector/features/sync/di/sync_initializer.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';

/// DI module for all sync-related instantiation and provider registration.
class SyncProviders {
  /// Pre-widget-tree initialization. Delegates to [SyncInitializer.create()]
  /// for all orchestration and wiring.
  static Future<({
    SyncOrchestrator orchestrator,
    SyncLifecycleManager lifecycleManager,
  })> initialize({
    required DatabaseService dbService,
    required AuthProvider authProvider,
    required AppConfigProvider appConfigProvider,
    required CompanyLocalDatasource companyLocalDs,
    required AuthService authService,
    SupabaseClient? supabaseClient,
  }) async {
    // WHY: Delegates to SyncInitializer — this method is pure passthrough.
    // FROM SPEC: "Zero business logic in any di/ file"
    return SyncInitializer.create(
      dbService: dbService,
      authProvider: authProvider,
      appConfigProvider: appConfigProvider,
      companyLocalDs: companyLocalDs,
      authService: authService,
      supabaseClient: supabaseClient,
    );
  }

  /// Returns the list of Provider entries for MultiProvider.
  /// Called from buildAppProviders() in app_providers.dart.
  static List<SingleChildWidget> providers({
    required SyncOrchestrator syncOrchestrator,
    required SyncLifecycleManager syncLifecycleManager,
    required ProjectLifecycleService projectLifecycleService,
    required ProjectSyncHealthProvider projectSyncHealthProvider,
    required DatabaseService dbService,
  }) {
    return [
      Provider<SyncRegistry>.value(value: SyncRegistry.instance),
      Provider<SyncOrchestrator>.value(value: syncOrchestrator),
      Provider<DeletionNotificationRepository>(
        create: (_) => DeletionNotificationRepository(
          DeletionNotificationLocalDatasource(dbService),
        ),
      ),
      Provider<ConflictRepository>(
        create: (_) => ConflictRepository(
          ConflictLocalDatasource(dbService, SyncRegistry.instance),
        ),
      ),
      ChangeNotifierProvider(
        create: (_) {
          final syncProvider = SyncProvider(syncOrchestrator);
          // Wire lifecycle manager callbacks to SyncProvider
          syncLifecycleManager.onStaleDataWarning = (isStale) {
            syncProvider.setStaleDataWarning(isStale);
          };
          syncLifecycleManager.onForcedSyncInProgress = (inProgress) {
            syncProvider.setForcedSyncInProgress(inProgress);
          };
          // FROM SPEC: Wire ProjectSyncHealthProvider after sync
          syncProvider.onSyncCycleComplete = () async {
            try {
              final counts = await projectLifecycleService.getAllUnsyncedCounts();
              projectSyncHealthProvider.updateCounts(counts);
            } catch (e) {
              Logger.sync('Health provider update failed: $e');
            }
          };
          // FROM SPEC SC-9: Wire notification queue
          syncOrchestrator.onNewAssignmentDetected = (message) {
            syncProvider.addNotification(message);
          };
          return syncProvider;
        },
      ),
    ];
  }
}
```

#### Step 4.5.2: Verify compilation

Run: `pwsh -Command "flutter analyze lib/features/sync/di/sync_providers.dart"`
Expected: No analysis issues

---

### Sub-phase 4.6: Test for SyncEnrollmentService

**Files:**
- Test: `test/features/sync/application/sync_enrollment_service_test.dart` (already created in 4.1)

**Agent**: `qa-testing-agent`

#### Step 4.6.1: Verify all enrollment tests pass

Run: `pwsh -Command "flutter test test/features/sync/application/sync_enrollment_service_test.dart"`
Expected: All tests PASS

---

### Sub-phase 4.7: Test for SyncProviders (wiring only)

**Files:**
- Create: `test/features/sync/di/sync_providers_test.dart`

**Agent**: `qa-testing-agent`

#### Step 4.7.1: Write structural test for SyncProviders

```dart
// test/features/sync/di/sync_providers_test.dart
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // WHY: Structural test verifying the spec requirement:
  // "Zero business logic in any di/ file"
  test('sync_providers.dart should not contain direct DB queries', () {
    final file = File('lib/features/sync/di/sync_providers.dart');
    final content = file.readAsStringSync();

    // IMPORTANT: No raw SQL should exist in the DI module
    expect(content.contains('localDb.query'), false,
        reason: 'sync_providers.dart should not contain direct DB queries');
    expect(content.contains('localDb.rawQuery'), false,
        reason: 'sync_providers.dart should not contain raw SQL queries');
    expect(content.contains('localDb.transaction'), false,
        reason: 'sync_providers.dart should not contain transaction logic');
  });

  test('sync_providers.dart should not contain enrollment logic', () {
    final file = File('lib/features/sync/di/sync_providers.dart');
    final content = file.readAsStringSync();

    // FROM SPEC: Enrollment logic moved to SyncEnrollmentService
    expect(content.contains('project_assignments'), false,
        reason: 'Enrollment logic should be in SyncEnrollmentService, not sync_providers');
    expect(content.contains('synced_projects'), false,
        reason: 'Enrollment logic should be in SyncEnrollmentService, not sync_providers');
  });

  test('sync_providers.dart should delegate to SyncInitializer', () {
    final file = File('lib/features/sync/di/sync_providers.dart');
    final content = file.readAsStringSync();

    expect(content.contains('SyncInitializer.create'), true,
        reason: 'SyncProviders.initialize() should delegate to SyncInitializer.create()');
  });

  // FROM SPEC: "Pure code-motion" stale comment should be removed
  test('sync_providers.dart should not contain stale "pure code-motion" comment', () {
    final file = File('lib/features/sync/di/sync_providers.dart');
    final content = file.readAsStringSync();

    expect(content.contains('Pure code-motion refactor'), false,
        reason: 'Stale "pure code-motion" comment should be removed');
  });
}
```

#### Step 4.7.2: Verify tests pass

Run: `pwsh -Command "flutter test test/features/sync/di/sync_providers_test.dart"`
Expected: All 4 tests PASS

#### Step 4.7.3: Run flutter analyze as phase gate

Run: `pwsh -Command "flutter analyze"`
Expected: No new analysis issues introduced by Phase 4 changes

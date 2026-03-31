# Codebase Cleanup Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Fix all scaffolded-but-unwired code, implement deferred TODOs, fix layer violations, wire unreachable features to UI, and centralize inline DI.
**Spec:** Audit findings from 5 parallel opus agents (2026-03-30)
**Analysis:** `.claude/dependency_graphs/2026-03-30-codebase-cleanup/`

**Architecture:** Provider + Clean Architecture (data → domain → presentation). DI via `AppInitializer` + per-feature `*_providers.dart`. GoRouter for navigation. SQLite local, Supabase remote.
**Tech Stack:** Flutter/Dart, Provider, GoRouter, SQLite (sqflite), Supabase
**Blast Radius:** ~50 direct, ~80 dependent, ~30 tests, ~15 new files

**Parts:**
- Part 1 (Phases 1-5): Critical fixes + DI wiring
- Part 2 (Phases 6-10): UI-unreachable feature wiring
- Part 3 (Phases 11-15): Deferred implementations + layer fixes
- Part 4 (Phases 16-22): Scaffolded method wiring + miscellaneous

---


## Phase 1: Critical Architecture Bugs

### Sub-phase 1.1: TrashScreen + SettingsScreen — SoftDeleteService & TrashRepository DI (C1 + D3)

**Files:**
- Modify: `lib/features/settings/di/settings_providers.dart`
- Modify: `lib/core/di/app_initializer.dart` (lines 373–374 area — after `final db = await dbService.database`)
- Modify: `lib/core/di/app_initializer.dart` (`AppDependencies` class — add convenience accessors)
- Modify: `lib/features/settings/presentation/screens/trash_screen.dart` (lines 56–61)
- Modify: `lib/features/settings/presentation/screens/settings_screen.dart` (lines 31–33)
- Test: `test/features/settings/di/settings_providers_test.dart`

**Agent**: `general-purpose` (spans DI + presentation)

#### Step 1.1.1: Add TrashRepository and SoftDeleteService to AppInitializer

In `lib/core/di/app_initializer.dart`, after `final db = await dbService.database;` (line 374):

```dart
// WHY: TrashRepository and SoftDeleteService were created inline in TrashScreen
// and SettingsScreen, bypassing the DI singleton. Creating them here ensures
// all consumers share the same DatabaseService instance.
final trashRepository = TrashRepository(dbService);
final softDeleteService = SoftDeleteService(db);
```

Add imports at top:
```dart
import 'package:construction_inspector/features/settings/data/repositories/trash_repository.dart';
import 'package:construction_inspector/services/soft_delete_service.dart';
```

Add `trashRepository` and `softDeleteService` to the `CoreDeps` class:

```dart
class CoreDeps {
  final DatabaseService dbService;
  final PreferencesService preferencesService;
  final PhotoService photoService;
  final ImageService imageService;
  final TrashRepository trashRepository;
  final SoftDeleteService softDeleteService;

  const CoreDeps({
    required this.dbService,
    required this.preferencesService,
    required this.photoService,
    required this.imageService,
    required this.trashRepository,
    required this.softDeleteService,
  });

  CoreDeps copyWith({PhotoService? photoService}) => CoreDeps(
        dbService: dbService,
        preferencesService: preferencesService,
        photoService: photoService ?? this.photoService,
        imageService: imageService,
        trashRepository: trashRepository,
        softDeleteService: softDeleteService,
      );
}
```

Add convenience accessors to `AppDependencies`:
```dart
TrashRepository get trashRepository => core.trashRepository;
SoftDeleteService get softDeleteService => core.softDeleteService;
```

Update the `AppDependencies` return in `initialize()` to pass `trashRepository` and `softDeleteService` into `CoreDeps`.

#### Step 1.1.2: Register in settingsProviders

In `lib/features/settings/di/settings_providers.dart`:

```dart
import 'package:construction_inspector/features/settings/data/repositories/trash_repository.dart';
import 'package:construction_inspector/services/soft_delete_service.dart';

List<SingleChildWidget> settingsProviders({
  required PreferencesService preferencesService,
  required TrashRepository trashRepository,
  required SoftDeleteService softDeleteService,
}) {
  return [
    ChangeNotifierProvider.value(value: preferencesService),
    ChangeNotifierProvider(create: (_) => ThemeProvider()),
    Provider<TrashRepository>.value(value: trashRepository),
    Provider<SoftDeleteService>.value(value: softDeleteService),
  ];
}
```

Update call site in `lib/core/di/app_providers.dart`:
```dart
...settingsProviders(
  preferencesService: deps.preferencesService,
  trashRepository: deps.trashRepository,
  softDeleteService: deps.softDeleteService,
),
```

#### Step 1.1.3: Fix TrashScreen to use DI

In `lib/features/settings/presentation/screens/trash_screen.dart`, replace `_initService()` (lines 56–62):

```dart
Future<void> _initService() async {
  // WHY: C1 fix — was creating new DatabaseService() inline, bypassing DI singleton.
  // Now reads from Provider tree where TrashRepository and SoftDeleteService are
  // registered via settingsProviders.
  _trashRepository = context.read<TrashRepository>();
  _softDeleteService = context.read<SoftDeleteService>();
  _loadDeletedItems();
}
```

Remove the `DatabaseService` import (line 3) since it's no longer used.

#### Step 1.1.4: Fix SettingsScreen to use DI

In `lib/features/settings/presentation/screens/settings_screen.dart`, replace `_loadTrashCount()` (lines 31–34):

```dart
Future<void> _loadTrashCount() async {
  // WHY: C1 fix — was creating SoftDeleteService(database) inline.
  final count = await context.read<SoftDeleteService>().getTotalDeletedCount();
  if (mounted) setState(() => _trashCount = count);
}
```

Remove the `DatabaseService` import (line 7) and `SoftDeleteService` import (line 9) — wait, `SoftDeleteService` is still needed for `context.read`. Keep the `SoftDeleteService` import, remove `DatabaseService`.

Actually: add `import 'package:provider/provider.dart';` if not present (it is already at line 3). Remove `DatabaseService` import only.

#### Step 1.1.5: Verify

```
Run: `pwsh -Command "flutter test test/features/settings/"`
Run: `pwsh -Command "flutter analyze lib/features/settings/ lib/core/di/"`
```

---

### Sub-phase 1.2: ImageService Provider — eliminate per-widget instantiation (C2 + D7)

**Files:**
- Modify: `lib/features/photos/presentation/widgets/photo_thumbnail.dart` (line 57)
- Modify: `lib/features/photos/presentation/widgets/photo_name_dialog.dart` (line 85)
- Test: `test/features/photos/presentation/widgets/photo_thumbnail_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 1.2.1: Fix PhotoThumbnail to use Provider

ImageService is already registered as a Provider in `photoProviders()` (line 24 of `photos_providers.dart`): `Provider<ImageService>.value(value: imageService)`.

In `lib/features/photos/presentation/widgets/photo_thumbnail.dart`, change:

```dart
// OLD (line 57):
final ImageService _imageService = ImageService();

// NEW:
late final ImageService _imageService;
```

Add to `initState()` — but `context.read` is not available in `initState`. Since the thumbnail future is created in `initState`, we need `didChangeDependencies`:

```dart
@override
void initState() {
  super.initState();
  // Thumbnail future initialized in didChangeDependencies (needs context)
}

bool _thumbnailInitialized = false;

@override
void didChangeDependencies() {
  super.didChangeDependencies();
  if (!_thumbnailInitialized) {
    _thumbnailInitialized = true;
    // WHY: C2 fix — ImageService was created per-widget (hundreds of instances
    // in a photo gallery). Now uses the singleton from Provider tree.
    _imageService = context.read<ImageService>();
    _thumbnailFuture = _imageService.getThumbnail(
      widget.photo.filePath,
      maxSize: widget.thumbnailSize,
    );
  }
}
```

Remove the `_thumbnailFuture` init from the old `initState` and remove the direct `ImageService` import if it was only used for inline creation. Actually, `ImageService` is still needed for the type — keep the import.

#### Step 1.2.2: Fix PhotoNameDialog to use Provider

In `lib/features/photos/presentation/widgets/photo_name_dialog.dart`, change:

```dart
// OLD (line 85):
final ImageService _imageService = ImageService();

// NEW:
late final ImageService _imageService;
```

In `initState()`, add after existing controller setup:
```dart
// WHY: C2 fix — use DI singleton instead of creating per-dialog instance.
_imageService = context.read<ImageService>();
```

Wait — `context.read` is not safe in `initState`. But `PhotoNameDialog` is shown via `showDialog`, so its context should have the Provider tree. Use `didChangeDependencies` with a guard:

```dart
bool _serviceInitialized = false;

@override
void didChangeDependencies() {
  super.didChangeDependencies();
  if (!_serviceInitialized) {
    _serviceInitialized = true;
    _imageService = context.read<ImageService>();
  }
}
```

Add import: `import 'package:provider/provider.dart';`

#### Step 1.2.3: Verify

```
Run: `pwsh -Command "flutter analyze lib/features/photos/"`
Run: `pwsh -Command "flutter test test/features/photos/"`
```

---

### Sub-phase 1.3: SupportProvider — extract LogUploadRemoteDatasource (C3)

**Files:**
- Create: `lib/features/settings/data/datasources/remote/log_upload_remote_datasource.dart`
- Modify: `lib/features/settings/presentation/providers/support_provider.dart` (lines 154, 206)
- Modify: `lib/features/settings/di/consent_support_factory.dart` (pass datasource)
- Test: `test/features/settings/data/datasources/remote/log_upload_remote_datasource_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 1.3.1: Create LogUploadRemoteDatasource

Create `lib/features/settings/data/datasources/remote/log_upload_remote_datasource.dart`:

```dart
import 'dart:typed_data';

import 'package:supabase_flutter/supabase_flutter.dart';

/// WHY: C3 fix — SupportProvider was directly accessing Supabase.instance.client
/// from the presentation layer. This datasource wraps storage operations to
/// maintain Clean Architecture layer boundaries.
class LogUploadRemoteDatasource {
  final SupabaseClient? _client;

  const LogUploadRemoteDatasource(this._client);

  /// Whether an authenticated session exists.
  bool get hasSession => _client?.auth.currentSession != null;

  /// Upload a zip bundle to the support-logs storage bucket.
  /// Returns the remote path on success.
  Future<String> uploadLogBundle({
    required String remotePath,
    required Uint8List zipBytes,
  }) async {
    if (_client == null) {
      throw StateError('Supabase client not configured');
    }
    await _client.storage.from('support-logs').uploadBinary(
      remotePath,
      zipBytes,
      fileOptions: const FileOptions(contentType: 'application/zip'),
    );
    return remotePath;
  }
}
```

#### Step 1.3.2: Inject into SupportProvider

In `lib/features/settings/presentation/providers/support_provider.dart`:

Add import:
```dart
import 'package:construction_inspector/features/settings/data/datasources/remote/log_upload_remote_datasource.dart';
```

Modify constructor:
```dart
class SupportProvider extends ChangeNotifier {
  final SupportRepository _supportRepository;
  final LogUploadRemoteDatasource _logUploadDatasource;

  SupportProvider({
    required SupportRepository supportRepository,
    required LogUploadRemoteDatasource logUploadDatasource,
  })  : _supportRepository = supportRepository,
        _logUploadDatasource = logUploadDatasource;
```

Replace line 154 (`Supabase.instance.client.auth.currentSession == null`):
```dart
if (!_logUploadDatasource.hasSession) {
```

Replace lines 205–210 (the storage upload block):
```dart
// WHY: C3 fix — storage access moved to LogUploadRemoteDatasource.
await _logUploadDatasource.uploadLogBundle(
  remotePath: remotePath,
  zipBytes: zipBytes,
);
```

Remove the `import 'package:supabase_flutter/supabase_flutter.dart';` (line 5).

#### Step 1.3.3: Update consent_support_factory.dart

Find `lib/features/settings/di/consent_support_factory.dart` and update to pass `LogUploadRemoteDatasource` when creating `SupportProvider`. The datasource is created with `Supabase.instance.client` when Supabase is configured, or `null` otherwise.

```dart
import 'package:construction_inspector/features/settings/data/datasources/remote/log_upload_remote_datasource.dart';
import 'package:construction_inspector/core/config/supabase_config.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

// Inside the factory function, when creating SupportProvider:
final logUploadDatasource = LogUploadRemoteDatasource(
  SupabaseConfig.isConfigured ? Supabase.instance.client : null,
);

SupportProvider(
  supportRepository: supportRepository,
  logUploadDatasource: logUploadDatasource,
)
```

#### Step 1.3.4: Verify

```
Run: `pwsh -Command "flutter analyze lib/features/settings/"`
Run: `pwsh -Command "flutter test test/features/settings/"`
```

---

## Phase 2: Inline DI → Move to Providers

### Sub-phase 2.1: Entry junction datasources (D1)

**Files:**
- Modify: `lib/core/di/app_initializer.dart` (add 3 datasources after existing datasource block ~line 432)
- Modify: `lib/core/di/app_initializer.dart` (`EntryDeps` class — add 3 fields)
- Modify: `lib/core/di/app_providers.dart` (pass to `entryProviders`)
- Modify: `lib/features/entries/di/entries_providers.dart` (accept + register as Providers)
- Modify: `lib/features/entries/presentation/screens/home_screen.dart` (lines 183–188)
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart` (lines 159–162)
- Test: `test/features/entries/di/entries_providers_test.dart`

**Agent**: `general-purpose` (spans DI + presentation)

#### Step 2.1.1: Create datasources in AppInitializer

In `lib/core/di/app_initializer.dart`, after the existing datasource block (around line 447, after `todoItemDatasource`):

```dart
// WHY: D1 fix — these junction datasources were created inline in HomeScreen
// and EntryEditorScreen. Moving to AppInitializer ensures single instances.
final entryPersonnelCountsDatasource = EntryPersonnelCountsLocalDatasource(dbService);
final entryEquipmentDatasource = EntryEquipmentLocalDatasource(dbService);
final entryContractorsDatasource = EntryContractorsLocalDatasource(dbService);
```

Add imports:
```dart
import 'package:construction_inspector/features/entries/data/datasources/local/entry_personnel_counts_local_datasource.dart';
import 'package:construction_inspector/features/contractors/data/datasources/local/entry_equipment_local_datasource.dart';
import 'package:construction_inspector/features/contractors/data/datasources/local/entry_contractors_local_datasource.dart';
```

**IMPORTANT**: The `EntryEquipmentLocalDatasource` import is from `contractors/data/datasources/local/`, NOT `entries/`. Verify the actual import path from the existing barrel exports.

Add to `EntryDeps`:
```dart
class EntryDeps {
  final DailyEntryRepository dailyEntryRepository;
  final EntryExportRepository entryExportRepository;
  final DocumentRepository documentRepository;
  final DocumentService documentService;
  final EntryPersonnelCountsLocalDatasource entryPersonnelCountsDatasource;
  final EntryEquipmentLocalDatasource entryEquipmentDatasource;
  final EntryContractorsLocalDatasource entryContractorsDatasource;

  const EntryDeps({
    required this.dailyEntryRepository,
    required this.entryExportRepository,
    required this.documentRepository,
    required this.documentService,
    required this.entryPersonnelCountsDatasource,
    required this.entryEquipmentDatasource,
    required this.entryContractorsDatasource,
  });
}
```

Add convenience accessors to `AppDependencies`:
```dart
EntryPersonnelCountsLocalDatasource get entryPersonnelCountsDatasource => entry.entryPersonnelCountsDatasource;
EntryEquipmentLocalDatasource get entryEquipmentDatasource => entry.entryEquipmentDatasource;
EntryContractorsLocalDatasource get entryContractorsDatasource => entry.entryContractorsDatasource;
```

Wire into the `EntryDeps(...)` construction in `initialize()`.

#### Step 2.1.2: Register as Providers in entries_providers.dart

In `lib/features/entries/di/entries_providers.dart`, add parameters and registrations:

```dart
import 'package:construction_inspector/features/entries/data/datasources/local/entry_personnel_counts_local_datasource.dart';
import 'package:construction_inspector/features/contractors/data/datasources/local/entry_equipment_local_datasource.dart';
import 'package:construction_inspector/features/contractors/data/datasources/local/entry_contractors_local_datasource.dart';

List<SingleChildWidget> entryProviders({
  required DailyEntryRepository dailyEntryRepository,
  required EntryExportRepository entryExportRepository,
  required FormResponseRepository formResponseRepository,
  required AuthProvider authProvider,
  required EntryPersonnelCountsLocalDatasource entryPersonnelCountsDatasource,
  required EntryEquipmentLocalDatasource entryEquipmentDatasource,
  required EntryContractorsLocalDatasource entryContractorsDatasource,
}) {
  // ... existing use case construction ...
  return [
    // ... existing providers ...
    Provider<EntryPersonnelCountsLocalDatasource>.value(value: entryPersonnelCountsDatasource),
    Provider<EntryEquipmentLocalDatasource>.value(value: entryEquipmentDatasource),
    Provider<EntryContractorsLocalDatasource>.value(value: entryContractorsDatasource),
  ];
}
```

Update call site in `app_providers.dart`:
```dart
...entryProviders(
  dailyEntryRepository: deps.dailyEntryRepository,
  entryExportRepository: deps.entryExportRepository,
  formResponseRepository: deps.formResponseRepository,
  authProvider: deps.authProvider,
  entryPersonnelCountsDatasource: deps.entryPersonnelCountsDatasource,
  entryEquipmentDatasource: deps.entryEquipmentDatasource,
  entryContractorsDatasource: deps.entryContractorsDatasource,
),
```

#### Step 2.1.3: Fix HomeScreen

In `lib/features/entries/presentation/screens/home_screen.dart`, replace lines 183–188 in `didChangeDependencies`:

```dart
if (!_controllersInitialized) {
  _controllersInitialized = true;
  // WHY: D1 fix — junction datasources now come from Provider tree
  // instead of being created inline with DatabaseService.
  _contractorController = ContractorEditingController(
    countsDatasource: context.read<EntryPersonnelCountsLocalDatasource>(),
    equipmentDatasource: context.read<EntryEquipmentLocalDatasource>(),
    contractorsDatasource: context.read<EntryContractorsLocalDatasource>(),
  );
}
```

Remove the `DatabaseService` read from this block (line 183: `final dbService = context.read<DatabaseService>();`). Keep the `DatabaseService` import only if used elsewhere in the file.

#### Step 2.1.4: Fix EntryEditorScreen

In `lib/features/entries/presentation/screens/entry_editor_screen.dart`, replace lines 159–162 in `_initAndLoad`:

```dart
Future<void> _initAndLoad() async {
  // WHY: D1 fix — junction datasources from Provider tree.
  _equipmentDatasource = context.read<EntryEquipmentLocalDatasource>();
  _contractorsDatasource = context.read<EntryContractorsLocalDatasource>();
  _countsDatasource = context.read<EntryPersonnelCountsLocalDatasource>();

  _contractorController ??= ContractorEditingController(
    countsDatasource: _countsDatasource,
    equipmentDatasource: _equipmentDatasource,
    contractorsDatasource: _contractorsDatasource,
  );

  await _loadEntryData();
}
```

Remove the `DatabaseService` read (line 159) if not used elsewhere.

#### Step 2.1.5: Verify

```
Run: `pwsh -Command "flutter analyze lib/features/entries/ lib/core/di/"`
Run: `pwsh -Command "flutter test test/features/entries/"`
```

---

### Sub-phase 2.2: PermissionService Provider (D2)

**Files:**
- Modify: `lib/core/di/app_initializer.dart` (create PermissionService instance)
- Modify: `lib/core/di/app_initializer.dart` (`CoreDeps` — add field)
- Modify: `lib/core/di/app_providers.dart` (register as Provider)
- Modify: `lib/features/entries/presentation/controllers/pdf_data_builder.dart` (line 61)
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_pdf_actions_dialog.dart` (line 64)
- Modify: `lib/features/entries/presentation/screens/report_widgets/report_debug_pdf_actions_dialog.dart` (line 62)
- Test: existing entry tests cover this indirectly

**Agent**: `general-purpose`

#### Step 2.2.1: Create PermissionService in AppInitializer

In `lib/core/di/app_initializer.dart`, near the other service creations (around line 710):

```dart
final permissionService = PermissionService();
```

Add to `CoreDeps`:
```dart
final PermissionService permissionService;
```

Update `CoreDeps` constructor and `copyWith` accordingly.

Add convenience accessor to `AppDependencies`:
```dart
PermissionService get permissionService => core.permissionService;
```

Register in `app_providers.dart` at Tier 0 level:
```dart
Provider<PermissionService>.value(value: deps.permissionService),
```

Import: `import 'package:construction_inspector/services/permission_service.dart';`

#### Step 2.2.2: Fix PdfDataBuilder

In `lib/features/entries/presentation/controllers/pdf_data_builder.dart`, the `generate()` static method creates `PermissionService()` at line 61. Since this is a static method that receives `BuildContext`, add a `PermissionService` parameter:

```dart
static Future<PdfGenerationResult?> generate({
  required BuildContext context,
  required DailyEntry entry,
  required PdfService pdfService,
  required PermissionService permissionService,  // NEW
  // ... rest of params ...
}) async {
  // ...
  if (Platform.isAndroid) {
    // WHY: D2 fix — PermissionService from DI instead of inline creation.
    if (!await permissionService.hasStoragePermission()) {
```

Update all callers of `PdfDataBuilder.generate()` to pass `context.read<PermissionService>()`.

#### Step 2.2.3: Fix report_pdf_actions_dialog.dart

In `lib/features/entries/presentation/screens/report_widgets/report_pdf_actions_dialog.dart`, the `showReportPdfActionsDialog` function creates `PermissionService()` at line 64. Add parameter:

```dart
Future<void> showReportPdfActionsDialog({
  required BuildContext context,
  required Uint8List pdfBytes,
  required IdrPdfData pdfData,
  required PdfService pdfService,
  required PermissionService permissionService,  // NEW
}) async {
```

Replace line 64:
```dart
final permissionService = PermissionService();  // DELETE
// Use the injected permissionService parameter
```

Update all callers.

#### Step 2.2.4: Fix report_debug_pdf_actions_dialog.dart

Same pattern — add `PermissionService` parameter to `showReportDebugPdfActionsDialog`, replace inline creation at line 62.

#### Step 2.2.5: Verify

```
Run: `pwsh -Command "flutter analyze lib/features/entries/ lib/core/di/"`
Run: `pwsh -Command "flutter test test/features/entries/"`
```

---

### Sub-phase 2.3: CalculatorService injection (D4)

**Files:**
- Modify: `lib/features/calculator/presentation/providers/calculator_provider.dart` (line 10)
- Modify: `lib/features/calculator/di/calculator_providers.dart`
- Test: `test/features/calculator/`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.3.1: Inject CalculatorService via constructor

In `lib/features/calculator/presentation/providers/calculator_provider.dart`:

```dart
// OLD (line 10):
final CalculatorService _service = CalculatorService();

// NEW:
final CalculatorService _service;

CalculatorProvider(this._repository, {CalculatorService? calculatorService})
    : _service = calculatorService ?? CalculatorService();
```

Using optional parameter with default keeps backward compatibility and avoids DI overhead for a stateless service.

#### Step 2.3.2: Verify

```
Run: `pwsh -Command "flutter analyze lib/features/calculator/"`
Run: `pwsh -Command "flutter test test/features/calculator/"`
```

---

### Sub-phase 2.4: AutoFillService + Mdot0582BCalculator injection (D5)

**Files:**
- Modify: `lib/features/forms/presentation/screens/mdot_hub_screen.dart` (lines 33–34)
- Modify: `lib/features/forms/presentation/screens/form_viewer_screen.dart` (line 29)
- Test: `test/features/forms/`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.4.1: Assessment

Both `AutoFillService` and `Mdot0582BCalculator` are `const` stateless classes with no dependencies. They use `const AutoFillService()` and `const Mdot0582BCalculator()` constructors. Registering them as full Providers adds overhead with zero benefit since they hold no state and have no dependencies to inject.

**Decision**: Keep as `const` field initializers but add `// WHY:` annotation documenting the decision. These are value objects, not services with dependencies.

In `lib/features/forms/presentation/screens/mdot_hub_screen.dart`:
```dart
// WHY: AutoFillService and Mdot0582BCalculator are const stateless utilities
// with no dependencies — Provider registration would add overhead with no benefit.
final _autoFillService = const AutoFillService();
final _calculator = const Mdot0582BCalculator();
```

In `lib/features/forms/presentation/screens/form_viewer_screen.dart`:
```dart
// WHY: AutoFillService is a const stateless utility — no DI needed.
final _autoFillService = const AutoFillService();
```

#### Step 2.4.2: Verify

```
Run: `pwsh -Command "flutter analyze lib/features/forms/presentation/screens/"`
```

---

### Sub-phase 2.5: PdfImportService + MpExtractionService injection (D6)

**Files:**
- Modify: `lib/features/pdf/presentation/helpers/pdf_import_helper.dart` (line 99)
- Modify: `lib/features/pdf/presentation/helpers/mp_import_helper.dart` (line 128)
- Modify: `lib/features/pdf/di/pdf_providers.dart`
- Modify: `lib/core/di/app_initializer.dart` (create instances)
- Test: `test/features/pdf/`

**Agent**: `general-purpose`

#### Step 2.5.1: Assessment

`PdfImportService()` is a default constructor (no args) — it's essentially stateless. `MpExtractionService` has a complex constructor with function params created per-invocation (takes a page render callback).

Looking at MpExtractionService constructor: it takes a `Future<String> Function(int pageIndex, ...)` — this is created at call site with local OCR state. This cannot be meaningfully moved to DI because the construction parameters change per invocation.

`PdfImportService()` is similarly stateless — it's created, used, and discarded. No shared state benefits from DI.

**Decision**: These are task-scoped service objects, not singleton services. Add `// WHY:` annotations explaining why they remain inline rather than forcing them into DI.

In `lib/features/pdf/presentation/helpers/pdf_import_helper.dart` (line 99):
```dart
// WHY: PdfImportService is a task-scoped processor (one import = one instance).
// No shared state or dependencies benefit from DI singleton registration.
final importService = PdfImportService();
```

In `lib/features/pdf/presentation/helpers/mp_import_helper.dart` (line 128):
```dart
// WHY: MpExtractionService takes per-invocation function params (page renderer
// callback) — it's task-scoped, not a shared singleton.
final service = MpExtractionService();
```

#### Step 2.5.2: Verify

```
Run: `pwsh -Command "flutter analyze lib/features/pdf/presentation/helpers/"`
```

---

## Phase 3: Implement Thumbnail Resize (H5)

### Sub-phase 3.1: Implement actual resize in _generateThumbnailIsolate

**Files:**
- Modify: `lib/services/image_service.dart` (lines 131–153)
- Test: `test/services/image_service_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 3.1.1: Implement resize using `image` package

The `image` package is already in pubspec (`image: ^4.0.0`). The isolate function runs outside the main thread, so `image` package is safe to use.

Replace `_generateThumbnailIsolate` in `lib/services/image_service.dart`:

```dart
import 'package:image/image.dart' as img;

/// Isolate function to generate thumbnail.
/// Decodes the source image, resizes to [maxSize] dimensions, and re-encodes as JPEG.
Future<Uint8List?> _generateThumbnailIsolate(Map<String, dynamic> params) async {
  final sourcePath = params['sourcePath'] as String;
  final maxSize = params['maxSize'] as int;

  try {
    final sourceFile = File(sourcePath);
    if (!await sourceFile.exists()) {
      return null;
    }

    final bytes = await sourceFile.readAsBytes();

    // WHY: H5 fix — previously returned raw bytes regardless of size, wasting
    // memory in photo-heavy views. Now actually resizes to maxSize dimensions.
    final decoded = img.decodeImage(bytes);
    if (decoded == null) {
      // Failed to decode — return raw bytes as fallback
      return bytes;
    }

    // Only resize if the image exceeds maxSize in either dimension
    if (decoded.width <= maxSize && decoded.height <= maxSize) {
      // Small enough already — re-encode as JPEG for consistent format
      return Uint8List.fromList(img.encodeJpg(decoded, quality: 85));
    }

    // Resize maintaining aspect ratio (interpolation: linear for speed in isolate)
    final resized = img.copyResize(
      decoded,
      width: decoded.width > decoded.height ? maxSize : null,
      height: decoded.height >= decoded.width ? maxSize : null,
      interpolation: img.Interpolation.linear,
    );

    return Uint8List.fromList(img.encodeJpg(resized, quality: 85));
  } catch (e) {
    return null;
  }
}
```

Add import at top of file: `import 'package:image/image.dart' as img;`

**IMPORTANT**: Remove the `dart:typed_data` import only if `Uint8List` is available from `dart:io` (it is — via `dart:typed_data` re-export). Actually, keep the import since it's already there and `Uint8List.fromList` is used.

#### Step 3.1.2: Clear existing disk cache

Since existing cached thumbnails are unresized raw bytes, add a one-time cache invalidation. The simplest approach: change the cache key format to include a version. In `_getThumbnailPath`:

```dart
String _getThumbnailPath(String imagePath, int maxSize) {
  final fileName = p.basenameWithoutExtension(imagePath);
  final hash = imagePath.hashCode.abs();
  // WHY: v2 suffix invalidates pre-resize cache entries from H5 fix.
  return p.join(_thumbnailCacheDir!, '${fileName}_${hash}_${maxSize}_v2.jpg');
}
```

#### Step 3.1.3: Write test

Create `test/services/image_service_test.dart`:

```dart
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:image/image.dart' as img;

// Test the isolate function directly (it's a top-level function)
// We can't import private functions, so test via ImageService.getThumbnail

void main() {
  group('ImageService thumbnail resize', () {
    late Directory tempDir;

    setUp(() async {
      tempDir = await Directory.systemTemp.createTemp('image_service_test');
    });

    tearDown(() async {
      if (await tempDir.exists()) {
        await tempDir.delete(recursive: true);
      }
    });

    test('generates resized thumbnail for large image', () async {
      // Create a test image larger than 300px
      final largeImage = img.Image(width: 1000, height: 800);
      img.fill(largeImage, color: img.ColorRgb8(255, 0, 0));
      final jpgBytes = img.encodeJpg(largeImage);
      final testFile = File('${tempDir.path}/test_large.jpg');
      await testFile.writeAsBytes(jpgBytes);

      // Verify the file exists and is large
      expect(await testFile.exists(), isTrue);
      expect(jpgBytes.length, greaterThan(100));

      // The actual resize is tested via the isolate function
      // Since _generateThumbnailIsolate is private, we test through ImageService
      // but that requires Flutter bindings for compute(). Unit test the logic:
      final decoded = img.decodeJpg(Uint8List.fromList(jpgBytes));
      expect(decoded, isNotNull);
      expect(decoded!.width, 1000);

      final resized = img.copyResize(decoded, width: 300);
      expect(resized.width, 300);
      expect(resized.height, lessThanOrEqualTo(300));
    });
  });
}
```

#### Step 3.1.4: Verify

```
Run: `pwsh -Command "flutter test test/services/image_service_test.dart"`
Run: `pwsh -Command "flutter analyze lib/services/image_service.dart"`
```

---

## Phase 4: Implement Log Rotation (H2)

### Sub-phase 4.1: Implement _rotateLogsIfNeeded in Logger

**Files:**
- Modify: `lib/core/logging/logger.dart` (lines 113–117, and in `_doInit`)
- Test: `test/core/logging/logger_rotation_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 4.1.1: Implement rotation method

In `lib/core/logging/logger.dart`, remove the `// ignore: unused_field` comments on lines 114 and 116.

Add the rotation method (place after `_doInit` method):

```dart
/// Rotate log files: delete files older than [_retentionDays] and enforce
/// [_maxLogSizeBytes] total cap by deleting oldest files first.
///
/// WHY: H2 fix — constants _retentionDays and _maxLogSizeBytes were declared
/// but never used. Without rotation, logs grow unbounded on long-lived devices.
static Future<void> _rotateLogsIfNeeded() async {
  if (_appLogDirPath == null) return;

  try {
    final logDir = Directory(_appLogDirPath!);
    if (!await logDir.exists()) return;

    final now = DateTime.now();
    final cutoff = now.subtract(Duration(days: _retentionDays));
    final files = <File>[];
    int totalSize = 0;

    await for (final entity in logDir.list()) {
      if (entity is File) {
        final stat = await entity.stat();

        // Delete files older than retention period
        if (stat.modified.isBefore(cutoff)) {
          try {
            await entity.delete();
            lifecycle('[Logger] Rotated old log: ${entity.path}');
          } catch (e) {
            // WHY: Don't let rotation failure crash the app
            debugPrint('[Logger] Failed to delete old log: $e');
          }
          continue;
        }

        files.add(entity);
        totalSize += stat.size;
      }
    }

    // Enforce size cap — delete oldest files first
    if (totalSize > _maxLogSizeBytes) {
      // Sort by modification time, oldest first
      final fileStat = <File, FileStat>{};
      for (final f in files) {
        fileStat[f] = await f.stat();
      }
      files.sort((a, b) =>
          fileStat[a]!.modified.compareTo(fileStat[b]!.modified));

      for (final file in files) {
        if (totalSize <= _maxLogSizeBytes) break;

        // WHY: Never delete the current session's log file
        if (_appLogFile != null && file.path == _appLogFile!.path) continue;

        final size = fileStat[file]!.size;
        try {
          await file.delete();
          totalSize -= size;
          lifecycle('[Logger] Rotated oversized log: ${file.path}');
        } catch (e) {
          debugPrint('[Logger] Failed to delete oversized log: $e');
        }
      }
    }
  } catch (e) {
    debugPrint('[Logger] Log rotation failed: $e');
  }
}
```

#### Step 4.1.2: Call rotation in _doInit

In `_doInit`, after the app log file is opened (after line 363 — `_appLogSink = _appLogFile!.openWrite(...)`) and before HTTP transport init:

```dart
// WHY: H2 — rotate old/oversized logs on each init to bound disk usage.
await _rotateLogsIfNeeded();
```

#### Step 4.1.3: Also rotate session directories

The session logs under `Troubleshooting/Detailed App Wide Logs/` also need rotation. Add a second rotation for session directories:

```dart
/// Rotate old session directories under the Troubleshooting folder.
static Future<void> _rotateSessionDirsIfNeeded() async {
  if (_sessionDir == null) return;

  try {
    // Parent of the current session dir = "Detailed App Wide Logs"
    final sessionsParent = Directory(path.dirname(_sessionDir!));
    if (!await sessionsParent.exists()) return;

    final now = DateTime.now();
    final cutoff = now.subtract(Duration(days: _retentionDays));

    await for (final entity in sessionsParent.list()) {
      if (entity is Directory && entity.path != _sessionDir) {
        final stat = await entity.stat();
        if (stat.modified.isBefore(cutoff)) {
          try {
            await entity.delete(recursive: true);
            debugPrint('[Logger] Rotated old session: ${entity.path}');
          } catch (_) {}
        }
      }
    }
  } catch (e) {
    debugPrint('[Logger] Session rotation failed: $e');
  }
}
```

Call after `_rotateLogsIfNeeded()`:
```dart
await _rotateSessionDirsIfNeeded();
```

#### Step 4.1.4: Write test

Create `test/core/logging/logger_rotation_test.dart`:

```dart
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/logging/logger.dart';

void main() {
  group('Logger rotation', () {
    late Directory tempLogDir;

    setUp(() async {
      tempLogDir = await Directory.systemTemp.createTemp('logger_rotation_test');
    });

    tearDown(() async {
      // Reset logger state for next test
      if (await tempLogDir.exists()) {
        await tempLogDir.delete(recursive: true);
      }
    });

    test('deletes log files older than 14 days', () async {
      // Create a log file with old modification time
      final oldFile = File('${tempLogDir.path}/app_log_old.txt');
      await oldFile.writeAsString('old log content');
      // Set modification time to 15 days ago
      final oldDate = DateTime.now().subtract(const Duration(days: 15));
      await oldFile.setLastModified(oldDate);

      // Create a recent log file
      final recentFile = File('${tempLogDir.path}/app_log_recent.txt');
      await recentFile.writeAsString('recent log content');

      // Initialize logger with the temp dir as base
      await Logger.init(baseDir: tempLogDir);

      // After init + rotation, old file should be deleted
      expect(await oldFile.exists(), isFalse);
      expect(await recentFile.exists(), isTrue);
    });
  });
}
```

**NOTE**: This test depends on Logger.init calling _rotateLogsIfNeeded. The test may need adjustment based on Logger's actual init flow (it creates subdirectories). The implementing agent should verify the test logic matches the actual directory structure.

#### Step 4.1.5: Verify

```
Run: `pwsh -Command "flutter test test/core/logging/logger_rotation_test.dart"`
Run: `pwsh -Command "flutter analyze lib/core/logging/logger.dart"`
```

---

## Phase 5: Remove Unused Dependencies (H7/H8)

### Sub-phase 5.1: Remove connectivity_plus and geocoding from pubspec

**Files:**
- Modify: `pubspec.yaml` (remove 2 entries)
- Test: verify build succeeds

**Agent**: `general-purpose`

#### Step 5.1.1: Confirm zero imports

Pre-verified: `connectivity_plus` and `geocoding` have zero imports across the entire `lib/` directory. `app_links` is listed with comment `# Constrained by supabase_flutter (requires ^6.x)` — this is a transitive dependency pinned for compatibility; do NOT remove.

#### Step 5.1.2: Remove from pubspec.yaml

Remove these lines:
```yaml
  geocoding: ^4.0.0       # (line 83)
  connectivity_plus: ^7.0.0  # (line 86)
```

#### Step 5.1.3: Verify

```
Run: `pwsh -Command "flutter pub get"`
Run: `pwsh -Command "flutter analyze"`
```

If `flutter pub get` fails due to other packages depending transitively on these, they may be needed as overrides. Check error output and re-add if necessary.

---

## Verification Checklist

After all phases complete:

```
Run: `pwsh -Command "flutter analyze"` — zero errors
Run: `pwsh -Command "flutter test"` — all passing
```

### Manual smoke test:
1. Launch app, navigate to Settings > Trash — verify trash count loads and items display
2. Open a project with photos — verify thumbnails render (and are noticeably smaller in memory)
3. Submit a support ticket with logs — verify upload succeeds
4. Open entry editor, verify contractor personnel/equipment panels load
5. Generate a PDF from an entry — verify permission check works

---

## Dependency Graph

```
Phase 1.1 (TrashRepository + SoftDeleteService DI)  →  independent
Phase 1.2 (ImageService Provider)                    →  independent
Phase 1.3 (LogUploadRemoteDatasource)                →  independent
Phase 2.1 (Entry junction datasources)               →  independent
Phase 2.2 (PermissionService)                        →  independent
Phase 2.3 (CalculatorService)                        →  independent
Phase 2.4 (AutoFillService annotations)              →  independent
Phase 2.5 (PdfImportService annotations)             →  independent
Phase 3.1 (Thumbnail resize)                         →  depends on 1.2 (ImageService Provider)
Phase 4.1 (Log rotation)                             →  independent
Phase 5.1 (Unused deps)                              →  independent (run last to verify no regressions)
```

### Recommended dispatch groups:
- **Group A** (parallel): Phase 1.1, 1.2, 1.3, 2.3, 2.4, 2.5
- **Group B** (parallel, after A): Phase 2.1, 2.2 (touch same DI files as 1.1 — wait to avoid merge conflicts)
- **Group C** (after B): Phase 3.1 (depends on 1.2 being merged)
- **Group D** (parallel with any): Phase 4.1
- **Group E** (last): Phase 5.1 (final verification)

---


## Phase 6: Wire Unreachable Screens

### Sub-phase 6.1: U1 — PersonnelTypesScreen Navigation

**Files:**
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart`
- Test: `test/features/projects/presentation/screens/project_setup_screen_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 6.1.1: Add "Manage Personnel Types" button to contractors tab

In `_buildContractorsTab()` (line 518), add a button between the contractor list and the "Add Contractor" button. Insert after the `Expanded` block (line 611) and before the `if (canManageProjects)` block (line 612).

```dart
// WHY: U1 — PersonnelTypesScreen is fully built with route /personnel-types/:projectId
// but no navigation path exists. This button provides access from the contractors tab
// where personnel types are contextually relevant.
if (canManageProjects && contractors.isNotEmpty)
  Padding(
    padding: const EdgeInsets.fromLTRB(
      AppTheme.space4,
      AppTheme.space2,
      AppTheme.space4,
      0,
    ),
    child: SizedBox(
      width: double.infinity,
      child: TextButton.icon(
        onPressed: () => context.push('/personnel-types/$_projectId'),
        icon: const Icon(Icons.people_outline),
        label: const Text('Manage Personnel Types'),
      ),
    ),
  ),
```

Insert this inside the `Column.children` list, after the existing `Expanded` widget that renders the contractor list (or empty state), and before the existing `if (canManageProjects)` "Add Contractor" `Padding` at line 612.

The exact insertion point is between lines 611 and 612 in `_buildContractorsTab()`:
```
// Line 611: closing paren of Expanded
),
// >>> INSERT NEW BUTTON HERE <<<
if (canManageProjects)
  Padding(  // existing "Add Contractor" button at line 612
```

#### Step 6.1.2: Verify

Run: `pwsh -Command "flutter test test/features/projects/presentation/screens/project_setup_screen_test.dart"`

If no existing test file, add a widget test verifying:
- The "Manage Personnel Types" button is visible when `canManageProjects == true` and contractors list is non-empty
- Tapping it calls `context.push('/personnel-types/$projectId')`
- The button is hidden when contractors list is empty

---

### Sub-phase 6.2: U2 — QuantityCalculatorScreen Navigation

**Files:**
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart`
- Test: `test/features/entries/presentation/screens/entry_editor_screen_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 6.2.1: Add calculator icon to the entry editor overflow menu

The entry editor has a `PopupMenuButton<String>` in the AppBar `actions` (line 877). Add a new `PopupMenuItem` for the quantity calculator before the delete item.

Insert at line 900 (inside `itemBuilder`), before the debug PDF item:

```dart
// WHY: U2 — QuantityCalculatorScreen is fully built with route
// /quantity-calculator/:entryId but no navigation path exists.
// The overflow menu is the natural home since calculation is an
// occasional action, not a primary workflow.
if (_entry != null)
  PopupMenuItem(
    value: 'calculator',
    child: const ListTile(
      leading: Icon(Icons.calculate_outlined),
      title: Text('Quantity Calculator'),
      contentPadding: EdgeInsets.zero,
    ),
  ),
```

Then handle the selection in `onSelected` (line 879). Add before the `if (value == 'delete')` check:

```dart
if (value == 'calculator' && _entry != null) {
  final result = await context.push<QuantityCalculatorResult>(
    '/quantity-calculator/${_entry!.id}',
  );
  // WHY: QuantityCalculatorScreen returns a QuantityCalculatorResult via Navigator.pop.
  // If the user completed a calculation, the result can be used to populate quantity fields.
  if (result != null && mounted) {
    // TODO(U2): Wire result into quantity entry field when quantity section is implemented
    SnackBarHelper.showSuccess(context, '${result.description}: ${result.value} ${result.unit}');
  }
}
```

Add the import at the top of `entry_editor_screen.dart`:
```dart
import 'package:construction_inspector/features/quantities/presentation/screens/quantity_calculator_screen.dart';
import 'package:go_router/go_router.dart';
```

Note: `go_router` may already be imported transitively — check before adding.

#### Step 6.2.2: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`

Verify:
- "Quantity Calculator" menu item appears in overflow menu when entry exists
- Tapping navigates to `/quantity-calculator/:entryId`

---

### Sub-phase 6.3: U3 — FormViewerScreen Routing

**Files:**
- Modify: `lib/features/forms/data/registries/form_screen_registry.dart`
- Modify: `lib/core/router/app_router.dart` (line 687-708)
- Test: `test/features/forms/data/registries/form_screen_registry_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 6.3.1: Register FormViewerScreen as the fallback in the router

The current `/form/:responseId` route (app_router.dart line 687) falls back to `MdotHubScreen` when the registry has no builder for the `formType`. This is incorrect — `MdotHubScreen` is 0582B-specific and should not render arbitrary form types.

Replace the fallback at line 707:
```dart
// BEFORE:
// NOTE: Fallback to MdotHubScreen for 0582B when registry not yet populated.
return MdotHubScreen(responseId: responseId);

// AFTER:
// WHY: U3 — FormViewerScreen is the generic viewer with PDF preview + auto-fill.
// It handles any form type gracefully, unlike MdotHubScreen which is 0582B-specific.
// MdotHubScreen is registered in FormScreenRegistry as 'mdot_0582b', so it's
// still reached via the registry path for 0582B forms.
return FormViewerScreen(responseId: responseId);
```

Add the import at the top of `app_router.dart`:
```dart
import 'package:construction_inspector/features/forms/presentation/screens/form_viewer_screen.dart';
```

Verify `MdotHubScreen` is registered in `FormScreenRegistry` for `mdot_0582b`. Check the seeding code:

Search for where `FormScreenRegistry.instance.register` is called. If `mdot_0582b` is not registered, add registration in the form infrastructure startup code (likely in `main.dart` or a form bootstrap file):

```dart
FormScreenRegistry.instance.register('mdot_0582b', ({
  required String formId,
  required String responseId,
  required String projectId,
}) => MdotHubScreen(responseId: responseId));
```

#### Step 6.3.2: Verify

Run: `pwsh -Command "flutter test test/features/forms/"`

Verify:
- Known form type `mdot_0582b` still routes to `MdotHubScreen` via registry
- Unknown form type falls back to `FormViewerScreen`

---

## Phase 7: Wire Export Providers to UI

### Sub-phase 7.1: U4 — EntryExportProvider "Export All Forms" Button

**Files:**
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart`
- Test: `test/features/entries/presentation/screens/entry_editor_screen_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.1.1: Add "Export All Forms" to the overflow menu

In `entry_editor_screen.dart`, the `PopupMenuButton` `itemBuilder` (line 900) already has items. Add a new entry:

```dart
// WHY: U4 — EntryExportProvider has a full stack (Provider -> UseCase -> Repository -> DB)
// but no UI button triggers it. This gives users access to batch-export all forms
// attached to an entry as PDFs.
if (_entry != null)
  const PopupMenuItem(
    value: 'export_forms',
    child: ListTile(
      leading: Icon(Icons.file_copy_outlined),
      title: Text('Export All Forms'),
      contentPadding: EdgeInsets.zero,
    ),
  ),
```

Handle in `onSelected`:
```dart
if (value == 'export_forms' && _entry != null) {
  final authProvider = context.read<AuthProvider>();
  final exportProvider = context.read<EntryExportProvider>();

  // WHY: Show progress indicator while exporting
  SnackBarHelper.showInfo(context, 'Exporting forms...');

  final paths = await exportProvider.exportAllFormsForEntry(
    _entry!.id,
    currentUserId: authProvider.userId,
  );

  if (!mounted) return;
  if (paths.isEmpty) {
    SnackBarHelper.showError(
      context,
      exportProvider.errorMessage ?? 'No forms to export',
    );
  } else {
    SnackBarHelper.showSuccess(
      context,
      'Exported ${paths.length} form(s)',
    );
    // WHY: Use the printing package's Printing.sharePdf for cross-platform sharing.
    // For multiple files, share the first and note the rest in the message.
    // TODO(U4): Consider a file list dialog for multi-file sharing UX.
  }
}
```

Add import:
```dart
import 'package:construction_inspector/features/entries/presentation/providers/entry_export_provider.dart';
```

#### Step 7.1.2: Verify

Run: `pwsh -Command "flutter test test/features/entries/"`

Verify:
- "Export All Forms" menu item appears when entry exists
- Tapping calls `EntryExportProvider.exportAllFormsForEntry`
- Error state shows snackbar

---

### Sub-phase 7.2: U5 — FormExportProvider "Export PDF" Button

**Files:**
- Modify: `lib/features/forms/presentation/screens/mdot_hub_screen.dart`
- Test: `test/features/forms/presentation/screens/mdot_hub_screen_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.2.1: Add "Export PDF" button to MdotHubScreen app bar

In `mdot_hub_screen.dart`, the AppBar `actions` (line 796-808) currently have a preview button and a save button. Add an export button between them:

```dart
// WHY: U5 — FormExportProvider has a full stack (Provider -> UseCase -> Repository -> DB)
// but no UI button triggers exportFormToPdf(). This button generates a finalized PDF
// (not just a preview) that can be shared or saved.
if (_headerConfirmed)
  IconButton(
    onPressed: _loading || _saving ? null : _exportPdf,
    icon: const Icon(Icons.ios_share),
    tooltip: 'Export PDF',
  ),
```

Add the `_exportPdf` method in the state class, near `_previewPdf`:

```dart
Future<void> _exportPdf() async {
  if (_response == null) return;
  final exportProvider = context.read<FormExportProvider>();
  final authProvider = context.read<AuthProvider>();

  final path = await exportProvider.exportFormToPdf(
    _response!.id,
    currentUserId: authProvider.userId,
  );

  if (!mounted) return;
  if (path != null) {
    SnackBarHelper.showSuccess(context, 'PDF exported');
    // WHY: Use Printing.sharePdf for cross-platform PDF sharing
    await Printing.sharePdf(
      bytes: await File(path).readAsBytes(),
      filename: 'MDOT_0582B_${_response!.id.substring(0, 8)}.pdf',
    );
  } else {
    SnackBarHelper.showError(
      context,
      exportProvider.errorMessage ?? 'Export failed',
    );
  }
}
```

Add imports:
```dart
import 'dart:io';
import 'package:construction_inspector/features/forms/presentation/providers/form_export_provider.dart';
```

Note: `dart:io` and `printing` are already imported in this file.

#### Step 7.2.2: Verify

Run: `pwsh -Command "flutter test test/features/forms/"`

Verify:
- Export button visible when header is confirmed
- Calls `FormExportProvider.exportFormToPdf` with correct responseId
- Error handling shows snackbar

---

## Phase 8: Wire Project Fields for Form Auto-Fill

### Sub-phase 8.1: U6 — Project Header Fields (controlSectionId, routeStreet, constructionEng)

**Files:**
- Modify: `lib/features/projects/presentation/widgets/project_details_form.dart`
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart`
- Test: `test/features/projects/presentation/widgets/project_details_form_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.1.1: Add controllers to ProjectSetupScreen

In `project_setup_screen.dart`, add three new `TextEditingController` declarations after the existing controllers (line 55):

```dart
final _controlSectionIdController = TextEditingController();
final _routeStreetController = TextEditingController();
final _constructionEngController = TextEditingController();
```

Dispose them in `dispose()` (after line 208):
```dart
_controlSectionIdController.dispose();
_routeStreetController.dispose();
_constructionEngController.dispose();
```

#### Step 8.1.2: Load values in _loadProjectData

In `_loadProjectData()` (line 130), after line 140 (`_descriptionController.text = project.description ?? '';`), add:

```dart
_controlSectionIdController.text = project.controlSectionId ?? '';
_routeStreetController.text = project.routeStreet ?? '';
_constructionEngController.text = project.constructionEng ?? '';
```

#### Step 8.1.3: Save values in _saveProject

In `_saveProject()`, the `copyWith` call for editing (line 925) needs the new fields:

```dart
final updated = existing.copyWith(
  name: _nameController.text,
  projectNumber: _numberController.text,
  clientName: _clientController.text.isEmpty ? null : _clientController.text,
  description: _descriptionController.text.isEmpty ? null : _descriptionController.text,
  controlSectionId: _controlSectionIdController.text.isEmpty ? null : _controlSectionIdController.text,
  routeStreet: _routeStreetController.text.isEmpty ? null : _routeStreetController.text,
  constructionEng: _constructionEngController.text.isEmpty ? null : _constructionEngController.text,
);
```

Also update the `Project(...)` constructor call for new projects (line 962):

```dart
final project = Project(
  id: _projectId,
  name: _nameController.text,
  projectNumber: _numberController.text,
  clientName: _clientController.text.isEmpty ? null : _clientController.text,
  description: _descriptionController.text.isEmpty ? null : _descriptionController.text,
  controlSectionId: _controlSectionIdController.text.isEmpty ? null : _controlSectionIdController.text,
  routeStreet: _routeStreetController.text.isEmpty ? null : _routeStreetController.text,
  constructionEng: _constructionEngController.text.isEmpty ? null : _constructionEngController.text,
  companyId: companyId,
  createdByUserId: userId,
);
```

#### Step 8.1.4: Update ProjectDetailsForm widget

In `project_details_form.dart`, add three new controller parameters:

```dart
class ProjectDetailsForm extends StatelessWidget {
  final GlobalKey<FormState> formKey;
  final TextEditingController nameController;
  final TextEditingController numberController;
  final TextEditingController clientController;
  final TextEditingController descriptionController;
  // WHY: U6 — These fields feed form auto-fill (0582B header).
  // Without them, auto-fill always gets null for control section, route, and construction engineer.
  final TextEditingController? controlSectionIdController;
  final TextEditingController? routeStreetController;
  final TextEditingController? constructionEngController;
  final bool readOnly;
  // ...
```

Make them optional (nullable) for backward compatibility.

Add to the constructor:
```dart
const ProjectDetailsForm({
  super.key,
  required this.formKey,
  required this.nameController,
  required this.numberController,
  required this.clientController,
  required this.descriptionController,
  this.controlSectionIdController,
  this.routeStreetController,
  this.constructionEngController,
  this.readOnly = false,
});
```

Add fields after the Description field (after line 93) in the `Column.children`:

```dart
// WHY: U6 — These fields are read by MdotHubScreen auto-fill service.
// Null controllers mean these are optional — only shown when provided.
if (controlSectionIdController != null) ...[
  const SizedBox(height: AppTheme.space4),
  const Divider(),
  const SizedBox(height: AppTheme.space2),
  Text(
    'Form Auto-Fill Fields',
    style: Theme.of(context).textTheme.titleSmall,
  ),
  const SizedBox(height: AppTheme.space2),
  TextFormField(
    controller: controlSectionIdController,
    readOnly: readOnly,
    decoration: const InputDecoration(
      labelText: 'Control Section ID',
      hintText: 'e.g., 12345',
      helperText: 'Used in 0582B form header',
    ),
  ),
],
if (routeStreetController != null) ...[
  const SizedBox(height: AppTheme.space4),
  TextFormField(
    controller: routeStreetController,
    readOnly: readOnly,
    decoration: const InputDecoration(
      labelText: 'Route / Street',
      hintText: 'e.g., M-37 or Main St',
      helperText: 'Used in 0582B form header',
    ),
  ),
],
if (constructionEngController != null) ...[
  const SizedBox(height: AppTheme.space4),
  TextFormField(
    controller: constructionEngController,
    readOnly: readOnly,
    decoration: const InputDecoration(
      labelText: 'Construction Engineer',
      hintText: 'e.g., John Smith, PE',
      helperText: 'Used in 0582B form header',
    ),
  ),
],
```

#### Step 8.1.5: Pass controllers in _buildDetailsTab

In `project_setup_screen.dart`, `_buildDetailsTab()` (line 366), update the `ProjectDetailsForm` instantiation:

```dart
ProjectDetailsForm(
  formKey: _formKey,
  nameController: _nameController,
  numberController: _numberController,
  clientController: _clientController,
  descriptionController: _descriptionController,
  controlSectionIdController: _controlSectionIdController,
  routeStreetController: _routeStreetController,
  constructionEngController: _constructionEngController,
  readOnly: !canManageProjects,
),
```

#### Step 8.1.6: Verify

Run: `pwsh -Command "flutter test test/features/projects/"`

Verify:
- New fields appear in the Details tab
- Values load from existing project data
- Values save correctly on project save
- Auto-fill in MdotHubScreen receives non-null values for these fields

---

### Sub-phase 8.2: U7 — MDOT Project Mode and Fields

**Files:**
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart`
- Modify: `lib/features/projects/presentation/widgets/project_details_form.dart`
- Test: `test/features/projects/presentation/widgets/project_details_form_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 8.2.1: Add mode and MDOT controllers to ProjectSetupScreen

After the controllers added in U6, add:

```dart
ProjectMode _projectMode = ProjectMode.localAgency;
final _mdotContractIdController = TextEditingController();
final _mdotProjectCodeController = TextEditingController();
final _mdotCountyController = TextEditingController();
final _mdotDistrictController = TextEditingController();
```

Dispose all four in `dispose()`.

#### Step 8.2.2: Load mode and MDOT fields in _loadProjectData

After loading U6 fields:

```dart
_projectMode = project.mode;
_mdotContractIdController.text = project.mdotContractId ?? '';
_mdotProjectCodeController.text = project.mdotProjectCode ?? '';
_mdotCountyController.text = project.mdotCounty ?? '';
_mdotDistrictController.text = project.mdotDistrict ?? '';
```

#### Step 8.2.3: Save mode and MDOT fields in _saveProject

Add to both `copyWith` (edit path) and `Project(...)` (create path):

```dart
mode: _projectMode,
mdotContractId: _mdotContractIdController.text.isEmpty ? null : _mdotContractIdController.text,
mdotProjectCode: _mdotProjectCodeController.text.isEmpty ? null : _mdotProjectCodeController.text,
mdotCounty: _mdotCountyController.text.isEmpty ? null : _mdotCountyController.text,
mdotDistrict: _mdotDistrictController.text.isEmpty ? null : _mdotDistrictController.text,
```

#### Step 8.2.4: Add mode selector and MDOT fields to ProjectDetailsForm

Add parameters to `ProjectDetailsForm`:

```dart
final ProjectMode? projectMode;
final ValueChanged<ProjectMode?>? onProjectModeChanged;
final TextEditingController? mdotContractIdController;
final TextEditingController? mdotProjectCodeController;
final TextEditingController? mdotCountyController;
final TextEditingController? mdotDistrictController;
```

Import `ProjectMode`:
```dart
import 'package:construction_inspector/features/projects/data/models/project_mode.dart';
```

Add a project mode dropdown at the top of the form (before the name field):

```dart
// WHY: U7 — Project mode determines terminology (IDR vs DWR) and which
// backend the project syncs to. Without this selector, mode is always localAgency.
if (projectMode != null && onProjectModeChanged != null) ...[
  DropdownButtonFormField<ProjectMode>(
    value: projectMode,
    decoration: const InputDecoration(
      labelText: 'Project Mode',
    ),
    items: ProjectMode.values.map((mode) => DropdownMenuItem(
      value: mode,
      child: Text(mode.displayName),
    )).toList(),
    onChanged: readOnly ? null : onProjectModeChanged,
  ),
  const SizedBox(height: AppTheme.space4),
],
```

Add MDOT-specific fields that appear only when mode is `mdot`:

```dart
if (projectMode == ProjectMode.mdot) ...[
  const Divider(),
  const SizedBox(height: AppTheme.space2),
  Text(
    'MDOT Fields',
    style: Theme.of(context).textTheme.titleSmall,
  ),
  const SizedBox(height: AppTheme.space2),
  if (mdotContractIdController != null)
    TextFormField(
      controller: mdotContractIdController,
      readOnly: readOnly,
      decoration: const InputDecoration(
        labelText: 'MDOT Contract ID',
        hintText: 'AASHTOWare contract reference',
      ),
    ),
  if (mdotProjectCodeController != null) ...[
    const SizedBox(height: AppTheme.space4),
    TextFormField(
      controller: mdotProjectCodeController,
      readOnly: readOnly,
      decoration: const InputDecoration(
        labelText: 'MDOT Project Code',
      ),
    ),
  ],
  if (mdotCountyController != null) ...[
    const SizedBox(height: AppTheme.space4),
    TextFormField(
      controller: mdotCountyController,
      readOnly: readOnly,
      decoration: const InputDecoration(
        labelText: 'County',
        hintText: 'e.g., Washtenaw',
      ),
    ),
  ],
  if (mdotDistrictController != null) ...[
    const SizedBox(height: AppTheme.space4),
    TextFormField(
      controller: mdotDistrictController,
      readOnly: readOnly,
      decoration: const InputDecoration(
        labelText: 'District',
        hintText: 'e.g., University Region',
      ),
    ),
  ],
  const SizedBox(height: AppTheme.space4),
],
```

#### Step 8.2.5: Pass mode and MDOT controllers in _buildDetailsTab

Update the `ProjectDetailsForm` call:

```dart
ProjectDetailsForm(
  formKey: _formKey,
  nameController: _nameController,
  numberController: _numberController,
  clientController: _clientController,
  descriptionController: _descriptionController,
  controlSectionIdController: _controlSectionIdController,
  routeStreetController: _routeStreetController,
  constructionEngController: _constructionEngController,
  projectMode: _projectMode,
  onProjectModeChanged: (mode) {
    if (mode != null) setState(() => _projectMode = mode);
  },
  mdotContractIdController: _mdotContractIdController,
  mdotProjectCodeController: _mdotProjectCodeController,
  mdotCountyController: _mdotCountyController,
  mdotDistrictController: _mdotDistrictController,
  readOnly: !canManageProjects,
),
```

#### Step 8.2.6: Verify

Run: `pwsh -Command "flutter test test/features/projects/"`

Verify:
- Project mode dropdown appears and defaults to Local Agency
- Selecting MDOT reveals MDOT-specific fields
- Values persist through save/load cycle

---

### Sub-phase 8.3: U8 — UserCertification Read-Only View

**Files:**
- Create: `lib/features/settings/data/models/user_certification.dart`
- Create: `lib/features/settings/data/datasources/local/user_certification_local_datasource.dart`
- Modify: `lib/features/settings/presentation/screens/settings_screen.dart` (or profile screen)
- Test: `test/features/settings/data/models/user_certification_test.dart`

**Agent**: `backend-data-layer-agent` (model + datasource), then `frontend-flutter-specialist-agent` (UI)

#### Step 8.3.1: Create UserCertification model

```dart
// lib/features/settings/data/models/user_certification.dart

/// Read-only model for user certifications synced from Supabase.
/// WHY: U8 — The user_certifications table exists in SQLite (sync_engine_tables.dart)
/// but has no model class, repository, or UI. Data is managed server-side;
/// this is a view-only mirror.
class UserCertification {
  final String id;
  final String userId;
  final String certType;
  final String certNumber;
  final DateTime? expiryDate;
  final DateTime createdAt;
  final DateTime updatedAt;

  const UserCertification({
    required this.id,
    required this.userId,
    required this.certType,
    required this.certNumber,
    this.expiryDate,
    required this.createdAt,
    required this.updatedAt,
  });

  factory UserCertification.fromMap(Map<String, dynamic> map) {
    return UserCertification(
      id: map['id'] as String,
      userId: map['user_id'] as String,
      certType: map['cert_type'] as String,
      certNumber: map['cert_number'] as String,
      expiryDate: map['expiry_date'] != null
          ? DateTime.parse(map['expiry_date'] as String)
          : null,
      createdAt: DateTime.parse(map['created_at'] as String),
      updatedAt: DateTime.parse(map['updated_at'] as String),
    );
  }

  /// Human-readable certification type for display.
  String get displayType {
    switch (certType) {
      case 'nuclear_gauge':
        return 'Nuclear Gauge';
      case 'aci':
        return 'ACI Concrete';
      case 'mdot':
        return 'MDOT Certification';
      default:
        return certType.replaceAll('_', ' ');
    }
  }

  /// Whether this certification has expired.
  bool get isExpired =>
      expiryDate != null && expiryDate!.isBefore(DateTime.now());
}
```

#### Step 8.3.2: Create read-only local datasource

```dart
// lib/features/settings/data/datasources/local/user_certification_local_datasource.dart

import 'package:construction_inspector/core/database/database_service.dart';
import '../../models/user_certification.dart';

/// Read-only datasource for user_certifications table.
/// WHY: U8 — Data is synced from Supabase. Local access is read-only.
class UserCertificationLocalDatasource {
  final DatabaseService _db;

  UserCertificationLocalDatasource(this._db);

  Future<List<UserCertification>> getByUserId(String userId) async {
    final db = await _db.database;
    final rows = await db.query(
      'user_certifications',
      where: 'user_id = ?',
      whereArgs: [userId],
      orderBy: 'cert_type ASC',
    );
    return rows.map(UserCertification.fromMap).toList();
  }
}
```

#### Step 8.3.3: Add certifications display to settings/profile

Add a "My Certifications" section in the Settings screen or Edit Profile screen. The exact location depends on the current settings screen layout. Display as a simple list of cards showing cert type, number, and expiry status.

This is a lightweight read-only widget — a `FutureBuilder` that queries `UserCertificationLocalDatasource.getByUserId()` on load and displays the results.

```dart
// Widget sketch — integrate into settings or profile screen
Widget _buildCertificationsSection(String userId) {
  return FutureBuilder<List<UserCertification>>(
    future: _certDatasource.getByUserId(userId),
    builder: (context, snapshot) {
      if (!snapshot.hasData || snapshot.data!.isEmpty) {
        return const SizedBox.shrink(); // WHY: Hide section when no certs exist
      }
      final certs = snapshot.data!;
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Certifications'),
          ...certs.map((cert) => ListTile(
            title: Text(cert.displayType),
            subtitle: Text(cert.certNumber),
            trailing: cert.isExpired
                ? const Chip(label: Text('Expired'))
                : cert.expiryDate != null
                    ? Text('Exp: ${DateFormat.yMMMd().format(cert.expiryDate!)}')
                    : null,
          )),
        ],
      );
    },
  );
}
```

#### Step 8.3.4: Verify

Run: `pwsh -Command "flutter test test/features/settings/"`

Verify:
- `UserCertification.fromMap` correctly parses all fields
- Read-only datasource queries by userId
- Widget renders correctly with empty list (hidden) and populated list

---

## Phase 9: Activate AppTerminology MDOT Mode

### Sub-phase 9.1: U9 — Call AppTerminology.setMode on Project Switch

**Files:**
- Modify: `lib/features/projects/presentation/providers/project_provider.dart`
- Test: `test/features/projects/presentation/providers/project_provider_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 9.1.1: Add setMode call in setSelectedProject and selectProject

In `project_provider.dart`, the `setSelectedProject()` method (line 401) sets `_selectedProject` and persists selection. Add the terminology activation after setting the project.

Import AppTerminology:
```dart
import 'package:construction_inspector/core/config/app_terminology.dart';
```

In `setSelectedProject()` (line 409), after `_selectedProject = project;`:

```dart
// WHY: U9 — AppTerminology.setMode() exists with full dual-terminology support
// but is never called. Activating it here ensures the UI uses correct terms
// (IDR vs DWR, Bid Item vs Pay Item) based on the selected project's mode.
AppTerminology.setMode(mdotMode: project?.isMdotProject ?? false);
```

In `selectProject()` (line 372), after `_selectedProject = project;` (line 382):

```dart
AppTerminology.setMode(mdotMode: project.isMdotProject);
```

Also add the call in `clearSelectedProject()` (line 415):

```dart
AppTerminology.setMode(mdotMode: false);
```

And in `clearScreenCache()` (line 424), after `_selectedProject = null;`:

```dart
AppTerminology.setMode(mdotMode: false);
```

#### Step 9.1.2: Verify

Run: `pwsh -Command "flutter test test/features/projects/"`

Verify:
- `AppTerminology.useMdotTerms` is true when an MDOT project is selected
- `AppTerminology.useMdotTerms` is false when a local agency project is selected
- `AppTerminology.useMdotTerms` resets to false on clear

---

## Phase 10: Design System Adoption (Progressive)

### Sub-phase 10.1: U10 — Proof-of-Concept Design System Migration

**Files:**
- Modify: `lib/features/settings/presentation/screens/trash_screen.dart`
- Modify: `lib/features/todos/presentation/screens/todos_screen.dart`
- Modify: `lib/features/gallery/presentation/screens/gallery_screen.dart`
- Modify: `lib/features/entries/presentation/screens/entries_list_screen.dart`
- Modify: `lib/features/entries/presentation/screens/drafts_list_screen.dart`
- Test: `test/features/settings/presentation/screens/trash_screen_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 10.1.1: Identify priority components

The design system has 24 components in `lib/core/design_system/`. Only `AppBudgetWarningChip` and `AppToggle` are used in production code. Priority adoption order:

1. **`AppEmptyState`** — Replace inline "no items" patterns (icon + text column)
2. **`AppErrorState`** — Replace inline error displays
3. **`AppLoadingState`** — Replace `Center(child: CircularProgressIndicator())`

These three replace the most common inline patterns across screens.

#### Step 10.1.2: Migrate 5 screens as proof of concept

Target screens (chosen because they have clear empty/loading/error patterns):

**Screen 1: `trash_screen.dart`**
Replace inline empty state with `AppEmptyState`:
```dart
// BEFORE:
const Center(child: Text('Trash is empty'))

// AFTER:
const AppEmptyState(
  icon: Icons.delete_outline,
  title: 'Trash is empty',
  subtitle: 'Deleted items will appear here',
)
```

**Screen 2: `todos_screen.dart`**
Replace inline empty/loading patterns.

**Screen 3: `gallery_screen.dart`**
Replace inline empty state and loading indicator.

**Screen 4: `entries_list_screen.dart`**
Replace inline empty/loading states.

**Screen 5: `drafts_list_screen.dart`**
Replace inline empty state.

For each screen:
1. Replace `Center(child: CircularProgressIndicator())` with `const AppLoadingState()`
2. Replace inline empty state columns (icon + text) with `AppEmptyState(icon: ..., title: ..., subtitle: ...)`
3. Add import: `import 'package:construction_inspector/core/design_system/design_system.dart';`

**IMPORTANT:** Preserve all existing `TestingKeys` and `Key` annotations. The design system components accept a `key` parameter — pass the existing keys through.

#### Step 10.1.3: Document the migration pattern

Add a `// WHY: Design system migration` comment on the first replacement in each file. This establishes the pattern for ongoing adoption across the codebase.

Pattern for future migration (not in this phase):
- `AppTextField` replacing raw `TextField` — deferred (requires controller refactoring)
- `AppDialog` / `AppBottomSheet` — deferred (requires call-site audit)
- `AppSectionCard` / `AppSectionHeader` — deferred (lower priority)

#### Step 10.1.4: Verify

Run: `pwsh -Command "flutter test test/features/settings/ test/features/todos/ test/features/gallery/ test/features/entries/"`

Verify:
- All migrated screens render correctly
- Empty states show proper icon, title, and subtitle
- Loading states show spinner
- No regressions in existing tests

---

## Execution Notes

### Phase Dependencies
```
Phase 6 (wire screens) — independent, can run first
Phase 7 (wire exports) — independent of Phase 6
Phase 8 (project fields) — U6 and U7 should run together (both modify ProjectDetailsForm)
Phase 9 (terminology) — depends on Phase 8 (U7 adds mode selector; U9 reads mode)
Phase 10 (design system) — independent, can run in parallel with any phase
```

### Recommended Dispatch Groups
- **Group A** (parallel): Phase 6 (6.1, 6.2, 6.3) + Phase 10
- **Group B** (sequential): Phase 8 (8.1 then 8.2 then 8.3)
- **Group C** (after Group B): Phase 9
- **Group D** (parallel with any): Phase 7 (7.1, 7.2)

### Risk Areas
| Item | Risk | Mitigation |
|------|------|------------|
| U3 (FormViewer fallback) | Could break 0582B routing if MdotHubScreen not registered | Verify registry seeding first |
| U7 (Project mode) | Null `mode` in existing projects | Default to `localAgency` already handled in `Project.fromMap` |
| U9 (Terminology) | Global static state, not reactive | Acceptable for now — screens rebuild on project switch via Provider |
| U6/U7 (ProjectDetailsForm) | Two sub-phases modify same widget | Must run sequentially |
| U4/U5 (Export) | Use cases may not be registered in Provider tree | Verify `EntryExportProvider` and `FormExportProvider` are in `main.dart` provider list |

### No-Touch Files
These files are NOT modified in this plan:
- `lib/core/database/` — schema already has all needed columns
- `lib/features/sync/` — no sync changes needed
- `lib/features/auth/` — no auth changes needed
- `supabase/migrations/` — no migration changes needed

---


## Phase 11: Layer Violation Fixes

### Sub-phase 11.1: DeletionNotificationBanner — Extract Raw SQL to Datasource + Repository

**Files:**
- Create: `lib/features/sync/data/datasources/local/deletion_notification_local_datasource.dart`
- Create: `lib/features/sync/data/repositories/deletion_notification_repository.dart`
- Modify: `lib/features/sync/presentation/widgets/deletion_notification_banner.dart`
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart` (wire injection)
- Test: `test/features/sync/data/datasources/deletion_notification_local_datasource_test.dart`
- Test: `test/features/sync/presentation/widgets/deletion_notification_banner_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 11.1.1: Create DeletionNotificationLocalDatasource

Create `lib/features/sync/data/datasources/local/deletion_notification_local_datasource.dart`:

```dart
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';

/// Datasource for deletion_notifications table.
///
/// WHY: Extracted from DeletionNotificationBanner to eliminate raw SQL in presentation layer.
/// Does NOT extend GenericLocalDatasource — non-standard API (no CRUD, no soft-delete).
class DeletionNotificationLocalDatasource {
  final DatabaseService _dbService;

  DeletionNotificationLocalDatasource(this._dbService);

  /// Get unseen deletion notifications (up to [limit]), newest first.
  ///
  /// Returns empty list if table doesn't exist (first-run startup race).
  Future<List<Map<String, dynamic>>> getUnseenNotifications({int limit = 10}) async {
    try {
      final db = await _dbService.database;
      return await db.query(
        'deletion_notifications',
        where: 'seen = 0',
        orderBy: 'deleted_at DESC',
        limit: limit,
      );
    } catch (e) {
      // WHY: Table may not exist yet during first run — known startup race
      if (e.toString().contains('no such table')) {
        Logger.db('deletion_notifications table not ready: $e');
        return [];
      }
      Logger.db('DeletionNotificationLocalDatasource.getUnseenNotifications: $e');
      return [];
    }
  }

  /// Mark all unseen notifications as seen.
  Future<void> markAllAsSeen() async {
    try {
      final db = await _dbService.database;
      await db.update(
        'deletion_notifications',
        {'seen': 1},
        where: 'seen = 0',
      );
    } catch (e) {
      Logger.db('DeletionNotificationLocalDatasource.markAllAsSeen: $e');
    }
  }
}
```

#### Step 11.1.2: Create DeletionNotificationRepository

Create `lib/features/sync/data/repositories/deletion_notification_repository.dart`:

```dart
import '../datasources/local/deletion_notification_local_datasource.dart';

/// Repository for deletion notifications shown after sync.
///
/// WHY: Thin wrapper to complete the data layer hierarchy.
/// Does NOT implement BaseRepository — non-standard API (no save/getAll/delete).
class DeletionNotificationRepository {
  final DeletionNotificationLocalDatasource _datasource;

  DeletionNotificationRepository(this._datasource);

  /// Get unseen notifications (up to [limit]).
  Future<List<Map<String, dynamic>>> getUnseenNotifications({int limit = 10}) {
    return _datasource.getUnseenNotifications(limit: limit);
  }

  /// Mark all notifications as seen (dismiss action).
  Future<void> markAllAsSeen() {
    return _datasource.markAllAsSeen();
  }
}
```

#### Step 11.1.3: Wire repository and refactor DeletionNotificationBanner

Modify `lib/features/sync/presentation/widgets/deletion_notification_banner.dart`:

1. Remove `import 'package:construction_inspector/core/database/database_service.dart';`
2. Add `import 'package:construction_inspector/features/sync/data/repositories/deletion_notification_repository.dart';`
3. Replace `_loadNotifications()` body (lines 37-56):
```dart
Future<void> _loadNotifications() async {
  // WHY: Delegates to repository instead of raw SQL in presentation layer
  final repo = context.read<DeletionNotificationRepository>();
  final results = await repo.getUnseenNotifications();
  if (mounted) {
    setState(() => _unseenNotifications = results);
  }
}
```
4. Replace `_dismiss()` body (lines 59-73):
```dart
Future<void> _dismiss() async {
  // WHY: Delegates to repository instead of raw SQL in presentation layer
  final repo = context.read<DeletionNotificationRepository>();
  await repo.markAllAsSeen();
  if (mounted) {
    setState(() => _dismissed = true);
  }
}
```
5. Remove the two `// TODO: Extract to repository` comments (lines 38, 61).

Wire the repository into the Provider tree — add to the sync providers or `app_initializer.dart` where `DatabaseService` is available. The `DeletionNotificationRepository` needs to be registered as a `Provider<DeletionNotificationRepository>` above where `DeletionNotificationBanner` is used.

#### Step 11.1.4: Test

Create unit test for datasource:
```dart
// test/features/sync/data/datasources/deletion_notification_local_datasource_test.dart
// Test getUnseenNotifications returns empty list when table missing
// Test getUnseenNotifications returns results ordered by deleted_at DESC
// Test markAllAsSeen sets seen=1 on all unseen rows
```

Run: `pwsh -Command "flutter test test/features/sync/data/datasources/deletion_notification_local_datasource_test.dart"`

---

### Sub-phase 11.2: ConflictViewerScreen — Extract Raw SQL to Datasource

**Files:**
- Create: `lib/features/sync/data/datasources/local/conflict_local_datasource.dart`
- Create: `lib/features/sync/data/repositories/conflict_repository.dart`
- Modify: `lib/features/sync/presentation/screens/conflict_viewer_screen.dart`
- Test: `test/features/sync/data/datasources/conflict_local_datasource_test.dart`
- Test: `test/features/sync/presentation/screens/conflict_viewer_screen_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 11.2.1: Create ConflictLocalDatasource

Create `lib/features/sync/data/datasources/local/conflict_local_datasource.dart`:

```dart
import 'dart:convert';
import 'package:sqflite/sqflite.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';

/// Datasource for the conflict_log table.
///
/// WHY: Extracted from ConflictViewerScreen to eliminate 6 raw SQL calls in presentation layer.
/// SECURITY: restoreConflict validates tableName against SyncRegistry.knownTableNames
/// to prevent arbitrary table writes from tampered conflict_log data.
class ConflictLocalDatasource {
  final DatabaseService _dbService;
  final SyncRegistry _syncRegistry;

  ConflictLocalDatasource(this._dbService, this._syncRegistry);

  /// Allowed table names for restore operations.
  /// WHY: SECURITY — prevents arbitrary table writes from tampered conflict_log data.
  Set<String> get _knownTableNames =>
      _syncRegistry.adapters.map((a) => a.tableName).toSet();

  /// Get all unresolved conflicts, newest first.
  Future<List<Map<String, dynamic>>> getUnresolvedConflicts() async {
    final db = await _dbService.database;
    return db.query(
      'conflict_log',
      where: 'dismissed_at IS NULL',
      orderBy: 'detected_at DESC',
    );
  }

  /// Dismiss a conflict by setting dismissed_at.
  Future<void> dismissConflict(int conflictId) async {
    final db = await _dbService.database;
    await db.update(
      'conflict_log',
      {'dismissed_at': DateTime.now().toUtc().toIso8601String()},
      where: 'id = ?',
      whereArgs: [conflictId],
    );
  }

  /// Restore lost data from a conflict record into the target table.
  ///
  /// SECURITY: Validates [tableName] against SyncRegistry's known tables.
  /// Strips protected columns (company_id, role, status, created_by_user_id,
  /// id, deleted_at, deleted_by, updated_at, updated_by_user_id) to prevent
  /// privilege escalation or ownership tampering.
  ///
  /// Throws [ArgumentError] if tableName is not in SyncRegistry.
  /// Throws [StateError] if the target record has been permanently deleted.
  /// Throws [FormatException] if lostDataJson is null/empty or malformed.
  Future<void> restoreConflict({
    required int conflictId,
    required String tableName,
    required String recordId,
    required String? lostDataJson,
  }) async {
    // WHY: SECURITY — validate tableName against known sync tables
    if (!_knownTableNames.contains(tableName)) {
      throw ArgumentError(
        'ConflictLocalDatasource: tableName "$tableName" not in SyncRegistry. '
        'Refusing to write to unknown table.',
      );
    }

    if (lostDataJson == null || lostDataJson.isEmpty) {
      throw const FormatException('No lost data available to restore.');
    }

    final lostData = jsonDecode(lostDataJson) as Map<String, dynamic>;
    final db = await _dbService.database;

    // Read current record
    final records = await db.query(
      tableName,
      where: 'id = ?',
      whereArgs: [recordId],
    );

    if (records.isEmpty) {
      throw StateError(
        'This record has been permanently deleted and cannot be restored.',
      );
    }

    final currentRecord = Map<String, dynamic>.from(records.first);

    // WHY: Strip protected columns from lostData before merge to prevent
    // privilege escalation or ownership tampering (Phase 6 HIGH finding).
    final strippedLostData = Map<String, dynamic>.from(lostData)
      ..remove('company_id')
      ..remove('role')
      ..remove('status')
      ..remove('created_by_user_id')
      ..remove('id')
      ..remove('deleted_at')
      ..remove('deleted_by')
      ..remove('updated_at')
      ..remove('updated_by_user_id');

    // Merge stripped lost_data into current record
    final merged = {...currentRecord, ...strippedLostData};

    // Validate via adapter (validate throws on invalid data)
    final adapter = _syncRegistry.adapterFor(tableName);
    await adapter.validate(merged);

    // Apply merged data
    await db.update(
      tableName,
      merged,
      where: 'id = ?',
      whereArgs: [recordId],
    );

    // Mark conflict as dismissed
    await dismissConflict(conflictId);

    Logger.sync('[ConflictLocalDatasource] restored conflict $conflictId '
        'table=$tableName record=$recordId');
  }
}
```

#### Step 11.2.2: Create ConflictRepository

Create `lib/features/sync/data/repositories/conflict_repository.dart`:

```dart
import '../datasources/local/conflict_local_datasource.dart';

/// Repository for sync conflict resolution.
///
/// WHY: Thin wrapper around ConflictLocalDatasource.
/// Does NOT implement BaseRepository — non-standard API.
class ConflictRepository {
  final ConflictLocalDatasource _datasource;

  ConflictRepository(this._datasource);

  Future<List<Map<String, dynamic>>> getUnresolvedConflicts() {
    return _datasource.getUnresolvedConflicts();
  }

  Future<void> dismissConflict(int conflictId) {
    return _datasource.dismissConflict(conflictId);
  }

  /// Restore lost data. Throws on validation failure, missing record, or unknown table.
  Future<void> restoreConflict({
    required int conflictId,
    required String tableName,
    required String recordId,
    required String? lostDataJson,
  }) {
    return _datasource.restoreConflict(
      conflictId: conflictId,
      tableName: tableName,
      recordId: recordId,
      lostDataJson: lostDataJson,
    );
  }
}
```

#### Step 11.2.3: Refactor ConflictViewerScreen

Modify `lib/features/sync/presentation/screens/conflict_viewer_screen.dart`:

1. Remove imports: `import 'package:sqflite/sqflite.dart';`, `import '../../engine/sync_registry.dart';`
2. Remove: `import 'package:construction_inspector/core/database/database_service.dart';`
3. Add: `import 'package:construction_inspector/features/sync/data/repositories/conflict_repository.dart';`
4. Remove `_getDatabase()` method (line 32-34) and `_syncRegistry` getter (line 37)
5. Replace `_loadConflicts()` (lines 45-64):
```dart
Future<void> _loadConflicts() async {
  try {
    // WHY: Delegates to repository instead of raw SQL in presentation layer
    final repo = context.read<ConflictRepository>();
    final results = await repo.getUnresolvedConflicts();
    if (mounted) {
      setState(() {
        _conflicts = results;
        _isLoading = false;
      });
    }
  } catch (e) {
    Logger.sync('[ConflictViewer] loadConflicts error: $e');
    if (mounted) {
      setState(() => _isLoading = false);
    }
  }
}
```
6. Replace `_dismissConflict()` (lines 67-82):
```dart
Future<void> _dismissConflict(Map<String, dynamic> conflict) async {
  try {
    final repo = context.read<ConflictRepository>();
    await repo.dismissConflict(conflict['id'] as int);
    await _loadConflicts();
  } catch (e) {
    if (mounted) {
      SnackBarHelper.showError(context, 'Failed to dismiss: $e');
    }
  }
}
```
7. Replace `_restoreConflict()` (lines 84-163):
```dart
Future<void> _restoreConflict(Map<String, dynamic> conflict) async {
  try {
    final repo = context.read<ConflictRepository>();
    await repo.restoreConflict(
      conflictId: conflict['id'] as int,
      tableName: conflict['table_name'] as String,
      recordId: conflict['record_id'] as String,
      lostDataJson: conflict['lost_data'] as String?,
    );
    await _loadConflicts();
    if (mounted) {
      SnackBarHelper.showSuccess(context, 'Conflict resolved — data restored.');
    }
  } on ArgumentError catch (e) {
    _showError('Security error: ${e.message}');
  } on StateError catch (e) {
    _showError(e.message);
  } on FormatException catch (e) {
    _showError(e.message);
  } catch (e) {
    _showError('Restore failed: $e');
  }
}
```

Wire `ConflictRepository` into the Provider tree alongside `DeletionNotificationRepository`.

#### Step 11.2.4: Test

Create unit test for ConflictLocalDatasource:
```dart
// test/features/sync/data/datasources/conflict_local_datasource_test.dart
// Test getUnresolvedConflicts returns only non-dismissed conflicts
// Test dismissConflict sets dismissed_at
// Test restoreConflict rejects unknown tableName (ArgumentError)
// Test restoreConflict strips protected columns before merge
// Test restoreConflict throws StateError when record permanently deleted
// Test restoreConflict throws FormatException when lostDataJson is empty
```

Run: `pwsh -Command "flutter test test/features/sync/data/datasources/conflict_local_datasource_test.dart"`

---

### Sub-phase 11.3: FormQuickActionRegistry — Remove BuildContext from Data Layer

**Files:**
- Modify: `lib/features/forms/data/registries/form_quick_action_registry.dart`
- Modify: Any callers of `FormQuickAction.execute` (search for `.execute(`)
- Test: `test/features/forms/data/registries/form_quick_action_registry_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 11.3.1: Replace BuildContext with Action Descriptor

Modify `lib/features/forms/data/registries/form_quick_action_registry.dart`:

1. Remove `import 'package:flutter/material.dart';` — replace with `import 'package:flutter/widgets.dart';` (still need `IconData`)
2. Replace `FormQuickAction` class:
```dart
/// Descriptor for a quick action that the presentation layer interprets.
///
/// WHY: Data layer must not take BuildContext. The execute callback returns
/// a FormQuickActionResult that the presentation layer interprets (navigate,
/// show dialog, etc.).
class FormQuickAction {
  final IconData icon;
  final String label;

  /// Returns a route path or action descriptor. The presentation layer
  /// is responsible for navigation/dialog display.
  final FormQuickActionResult Function(FormResponse response) execute;

  const FormQuickAction({
    required this.icon,
    required this.label,
    required this.execute,
  });
}

/// Result from executing a quick action.
/// WHY: Decouples data layer from Flutter navigation. Presentation layer
/// interprets the result type and performs the appropriate action.
class FormQuickActionResult {
  final FormQuickActionType type;
  final String? routePath;
  final Map<String, String>? queryParameters;

  const FormQuickActionResult({
    required this.type,
    this.routePath,
    this.queryParameters,
  });

  const FormQuickActionResult.navigate({
    required String route,
    Map<String, String>? params,
  })  : type = FormQuickActionType.navigate,
        routePath = route,
        queryParameters = params;

  const FormQuickActionResult.noOp()
      : type = FormQuickActionType.noOp,
        routePath = null,
        queryParameters = null;
}

enum FormQuickActionType { navigate, noOp }
```

#### Step 11.3.2: Update All Callers

Search for all callers of `FormQuickAction.execute` and update them to:
1. Call `action.execute(response)` (no BuildContext)
2. Interpret the `FormQuickActionResult` — if `type == navigate`, call `context.push(result.routePath!, queryParameters: result.queryParameters)`

Also update any `FormQuickAction` registrations that currently capture `BuildContext` in their `execute` callback — change them to return `FormQuickActionResult.navigate(...)` instead.

#### Step 11.3.3: Test

Run: `pwsh -Command "flutter test test/features/forms/"`

---

### Sub-phase 11.4: Auth Layer — Wrap Supabase Exceptions + Constructor Injection Fixes

**Files:**
- Modify: `lib/features/auth/presentation/providers/auth_provider.dart` (line 431 — wrap AuthException)
- Modify: `lib/features/auth/presentation/screens/update_password_screen.dart` (catch domain exception)
- Modify: `lib/features/auth/data/repositories/user_attribution_repository.dart` (line 77 — inject SupabaseClient)
- Modify: `lib/features/projects/data/services/project_lifecycle_service.dart` (line 362 — use injected client)
- Test: `test/features/auth/presentation/providers/auth_provider_test.dart`

**Agent**: `auth-agent`

#### Step 11.4.1: Wrap AuthException in AuthProvider.resetPassword

In `lib/features/auth/presentation/providers/auth_provider.dart`, the `resetPassword` method (line 431) catches `AuthException` directly. This is acceptable for now since `AuthProvider` already imports `supabase_flutter` for `AuthState` and `User` types.

**Note as tech debt:** Full domain auth type abstraction (M14/M15) would require:
- Creating `lib/features/auth/domain/models/auth_state.dart` wrapping Supabase `AuthState`
- Creating `lib/features/auth/domain/exceptions/auth_exception.dart`
- Mapping in `AuthService`

This is out of scope for this cleanup. The current import is a known deviation documented in the codebase.

For `update_password_screen.dart` (line 4 imports `supabase_flutter` for `AuthException`):

Modify `lib/features/auth/presentation/providers/auth_provider.dart` — wrap the `updatePassword` method so it catches `AuthException` and rethrows as a domain-level exception:

```dart
/// Update the current user's password during a recovery flow.
///
/// WHY: Wraps AuthService.updatePassword to catch Supabase-specific exceptions
/// and rethrow as domain exceptions so screens don't import supabase_flutter.
Future<void> updatePassword(String newPassword) async {
  try {
    await _authService.updatePassword(newPassword);
  } on AuthException catch (e) {
    // WHY: Map Supabase exceptions to user-friendly messages
    if (e.message.contains('expired') || e.message.contains('session')) {
      throw PasswordUpdateException(
        'Your recovery session has expired. Please request a new reset link.',
        isExpired: true,
      );
    }
    throw PasswordUpdateException(AuthErrorParser.parse(e.message));
  }
}
```

Create a simple domain exception class in `lib/features/auth/domain/exceptions/password_update_exception.dart`:

```dart
/// Domain exception for password update failures.
/// WHY: Screens catch this instead of importing supabase_flutter for AuthException.
class PasswordUpdateException implements Exception {
  final String message;
  final bool isExpired;

  const PasswordUpdateException(this.message, {this.isExpired = false});

  @override
  String toString() => message;
}
```

Then modify `update_password_screen.dart` to:
1. Remove `import 'package:supabase_flutter/supabase_flutter.dart';`
2. Add `import 'package:construction_inspector/features/auth/domain/exceptions/password_update_exception.dart';`
3. Replace `on AuthException catch (e)` with `on PasswordUpdateException catch (e)` — use `e.isExpired` for the expired-link detection logic.

#### Step 11.4.2: UserAttributionRepository — Inject SupabaseClient

Modify `lib/features/auth/data/repositories/user_attribution_repository.dart`:

Replace line 77 (`final client = Supabase.instance.client;`) with constructor injection:

```dart
class UserAttributionRepository {
  final SupabaseClient? _client;

  // WHY: Constructor injection replaces Supabase.instance.client inline usage.
  // Nullable because client may not be configured in offline/mock mode.
  UserAttributionRepository({SupabaseClient? client}) : _client = client;

  // ... existing _cache field ...

  Future<String> _fetchFromRemote(String userId) async {
    if (_client == null) return 'Unknown';
    try {
      final row = await _client
          .from('user_profiles')
          .select('display_name')
          .eq('id', userId)
          .maybeSingle();
      final name = row?['display_name'] as String?;
      if (name != null && name.isNotEmpty) return name;
    } catch (e) {
      Logger.auth('[UserAttributionRepository] Remote fetch failed for $userId: $e');
    }
    return 'Unknown';
  }
```

Update the `attributionRepository` field in `AuthProvider` (line 56-57) to use the injected client. Since `AuthProvider` receives `AuthService` which wraps the Supabase client, the cleanest approach is to pass `SupabaseClient?` as an optional param to `AuthProvider` and forward it:

In `AuthProvider` constructor, add `SupabaseClient? supabaseClient` param:
```dart
final UserAttributionRepository attributionRepository;

AuthProvider(
  this._authService, {
  // ... existing params ...
  SupabaseClient? supabaseClient,
}) : // ... existing initializers ...
     attributionRepository = UserAttributionRepository(client: supabaseClient) {
```

Update all call sites that construct `AuthProvider` to pass the client:
- `lib/core/di/app_initializer.dart` (search for `AuthProvider(` — line ~588 area)
- `lib/test_harness/harness_providers.dart` (search for `AuthProvider(`)
- Any test files in `test/features/auth/` that construct `AuthProvider` directly

#### Step 11.4.3: ProjectLifecycleService — Use Injected Client

Modify `lib/features/projects/data/services/project_lifecycle_service.dart`:

The constructor already accepts `Database _db`. For the Supabase RPC call on line 362, the service needs a `SupabaseClient`. Check if there's already one — the class only has `final Database _db;`.

Add a `SupabaseClient?` field:

```dart
class ProjectLifecycleService {
  final Database _db;
  final SupabaseClient? _supabaseClient;

  ProjectLifecycleService(this._db, {SupabaseClient? supabaseClient})
      : _supabaseClient = supabaseClient;
```

Replace line 362 (`await Supabase.instance.client.rpc(`) with:
```dart
    // WHY: Use injected client instead of Supabase.instance.client singleton
    final client = _supabaseClient;
    if (client == null) {
      throw StateError('deleteFromSupabase requires a SupabaseClient');
    }
    await client.rpc(
      'admin_soft_delete_project',
      params: {'p_project_id': projectId},
    );
```

Update the call site in `lib/core/di/app_initializer.dart` (line ~378 area) where
`ProjectLifecycleService(db)` is constructed — add `supabaseClient: SupabaseConfig.isConfigured ? Supabase.instance.client : null`.

#### Step 11.4.4: Test

Run: `pwsh -Command "flutter test test/features/auth/"`
Run: `pwsh -Command "flutter test test/features/projects/"`

---

### Sub-phase 11.5: FormQuickActionRegistry BuildContext Caller Update

This is covered in Sub-phase 11.3 Step 11.3.2. Listing separately to ensure the presentation-layer callers are found and updated.

**Agent**: `frontend-flutter-specialist-agent`

#### Step 11.5.1: Find All Callers

Search for:
- `FormQuickAction(` — registration sites that pass `(BuildContext context, FormResponse response)` lambdas
- `.execute(context,` — invocation sites

Update registrations to return `FormQuickActionResult` instead of taking `BuildContext`.
Update invocations to handle the result in the presentation layer.

#### Step 11.5.2: Test

Run: `pwsh -Command "flutter test test/features/forms/"`

---

## Phase 12: Implement Document Opening

### Sub-phase 12.1: Replace _openDocument Placeholder with Real Implementation

**Files:**
- Modify: `lib/features/entries/presentation/widgets/entry_forms_section.dart` (lines 304-312)
- Test: `test/features/entries/presentation/widgets/entry_forms_section_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 12.1.1: Implement _openDocument with url_launcher

`url_launcher` is already in `pubspec.yaml` (v6.3.1). No new dependency needed.

Replace `_openDocument` method (lines 304-312) in `lib/features/entries/presentation/widgets/entry_forms_section.dart`:

```dart
Future<void> _openDocument(BuildContext context, Document doc) async {
  // WHY: Replaces placeholder snackbar with actual document opening.
  // Uses url_launcher (already in pubspec) for file:// URIs.
  if (doc.filePath == null || doc.filePath!.isEmpty) {
    SnackBarHelper.showError(context, 'Document file not available locally.');
    return;
  }

  final file = File(doc.filePath!);
  if (!await file.exists()) {
    // TODO: Remote signed URL support can be added when DocumentService supports it.
    SnackBarHelper.showError(
      context,
      'File not found on device. Re-sync to download.',
    );
    return;
  }

  final uri = Uri.file(doc.filePath!);
  try {
    final launched = await launchUrl(
      uri,
      // WHY: externalApplication ensures the OS opens the file with its
      // native viewer (PDF reader, image viewer, etc.) rather than in-app.
      mode: LaunchMode.externalApplication,
    );
    if (!launched && context.mounted) {
      SnackBarHelper.showError(
        context,
        'No app available to open ${doc.filename}.',
      );
    }
  } catch (e) {
    Logger.ui('_openDocument error: $e');
    if (context.mounted) {
      SnackBarHelper.showError(context, 'Failed to open document.');
    }
  }
}
```

Add imports at the top of the file:
```dart
import 'dart:io';
import 'package:url_launcher/url_launcher.dart';
```

Remove the `// TODO: Integrate open_file...` comment.

#### Step 12.1.2: Test

Verify that the method compiles and no regressions in the entry forms section:

Run: `pwsh -Command "flutter test test/features/entries/"`

---

## Phase 13: Implement Support/Consent Sync

### Sub-phase 13.1: SupportTicketAdapter — Push-Only Sync

**Files:**
- Create: `lib/features/sync/adapters/support_ticket_adapter.dart`
- Modify: `lib/features/sync/engine/sync_registry.dart` (register adapter)
- Modify: `lib/features/settings/data/repositories/support_repository.dart` (remove TODO comment)
- Test: `test/features/sync/adapters/support_ticket_adapter_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 13.1.1: Create SupportTicketAdapter

Create `lib/features/sync/adapters/support_ticket_adapter.dart`:

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

/// Adapter for support_tickets table.
///
/// WHY: Enables sync for support tickets (previously local-only).
/// Push-only initially — client creates tickets, server updates status.
/// Pull brings status updates from admin dashboard back to client.
///
/// The Supabase support_tickets table was created in pre-release hardening migrations.
class SupportTicketAdapter extends TableAdapter {
  @override
  String get tableName => 'support_tickets';

  /// WHY: Support tickets are user-scoped, not project-scoped.
  /// ScopeType enum only has: direct, viaProject, viaEntry, viaContractor.
  /// There is no viaUser. We use ScopeType.direct (company-scoped) and override
  /// the pull filter to add user_id filtering so users only pull their own tickets.
  @override
  ScopeType get scopeType => ScopeType.direct;

  /// WHY: Override pull filter to scope by user_id instead of just company_id.
  /// The base direct scope filters by company_id, but support tickets must also
  /// filter by user_id so users only see their own tickets.
  @override
  Map<String, dynamic> pullFilter(String companyId, String userId) {
    return {
      'company_id': companyId,
      'user_id': userId,
    };
  }

  /// No FK dependencies — support tickets are standalone.
  @override
  List<String> get fkDependencies => const [];

  /// WHY: support_tickets does not use soft-delete. Tickets are append-only
  /// from the client. The server may update status but never soft-deletes.
  @override
  bool get supportsSoftDelete => false;

  @override
  String extractRecordName(Map<String, dynamic> record) {
    return record['subject']?.toString() ??
        record['id']?.toString() ??
        'Unknown';
  }
}
```

**NOTE:** The `pullFilter` override method may not exist on `TableAdapter` base class yet. If not, add it:
1. In `lib/features/sync/adapters/table_adapter.dart`, add: `Map<String, dynamic> pullFilter(String companyId, String userId) => {'company_id': companyId};`
2. In `lib/features/sync/engine/sync_engine.dart`, update `_applyScopeFilter()` to call `adapter.pullFilter()` for `ScopeType.direct` instead of hardcoding `company_id` only.
This ensures user-scoped tables work without polluting the ScopeType enum.

#### Step 13.1.2: Register in SyncRegistry

Modify `lib/features/sync/engine/sync_registry.dart`:

1. Add import: `import 'package:construction_inspector/features/sync/adapters/support_ticket_adapter.dart';`
2. Add `SupportTicketAdapter()` to the `registerSyncAdapters()` list, after `CalculationHistoryAdapter()` (no FK deps, so order doesn't matter — append at end):

```dart
    CalculationHistoryAdapter(),
    SupportTicketAdapter(),  // WHY: Push-only, no FK deps, appended at end
  ]);
```

#### Step 13.1.3: Remove TODO from SupportRepository

Modify `lib/features/settings/data/repositories/support_repository.dart`:

Remove the TODO comment block (lines 8-12). Replace with:

```dart
  // WHY: Sync handled by SupportTicketAdapter in SyncRegistry.
  // Client pushes new tickets; pulls bring status updates from admin dashboard.
```

#### Step 13.1.4: Column Mapping Verification

Verify that the local `support_tickets` SQLite columns match the Supabase table columns. Check `lib/core/database/database_service.dart` (or schema files) for the CREATE TABLE statement and compare against the Supabase migration. If column names differ, add entries to the `converters` map in the adapter.

#### Step 13.1.5: Test

Run: `pwsh -Command "flutter test test/features/sync/"`

---

### Sub-phase 13.2: ConsentRecordAdapter — Push-Only Sync

**Files:**
- Create: `lib/features/sync/adapters/consent_record_adapter.dart`
- Modify: `lib/features/sync/engine/sync_registry.dart` (register adapter)
- Modify: `lib/features/settings/data/repositories/consent_repository.dart` (remove TODO comment)
- Test: `test/features/sync/adapters/consent_record_adapter_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 13.2.1: Create ConsentRecordAdapter

Create `lib/features/sync/adapters/consent_record_adapter.dart`:

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

/// Adapter for user_consent_records table.
///
/// WHY: Enables sync for consent records (previously local-only).
/// Push-only, no pull/conflict resolution needed — append-only table with
/// server-side triggers that enforce immutability.
///
/// FROM SPEC: ConsentRecord model uses accepted_at (not created_at) as timestamp.
class ConsentRecordAdapter extends TableAdapter {
  @override
  String get tableName => 'user_consent_records';

  /// WHY: User-scoped, not project-scoped. Same pattern as SupportTicketAdapter.
  @override
  ScopeType get scopeType => ScopeType.direct;

  /// WHY: Override pull filter to scope by user_id.
  @override
  Map<String, dynamic> pullFilter(String companyId, String userId) {
    return {
      'company_id': companyId,
      'user_id': userId,
    };
  }

  /// No FK dependencies — consent records are standalone.
  @override
  List<String> get fkDependencies => const [];

  /// WHY: Consent records are append-only. Never soft-deleted.
  @override
  bool get supportsSoftDelete => false;

  /// WHY: Override push to INSERT-only (never upsert). Consent records are
  /// immutable once written — server-side triggers enforce this, but we also
  /// enforce client-side to prevent accidental updates from tampering with
  /// the consent audit trail.
  @override
  bool get insertOnly => true;

  @override
  String extractRecordName(Map<String, dynamic> record) {
    final type = record['policy_type']?.toString() ?? 'unknown';
    final version = record['policy_version']?.toString() ?? '?';
    return '$type v$version';
  }
}
```

**NOTE:** The `insertOnly` getter may not exist on `TableAdapter` base class yet. If not, add `bool get insertOnly => false;` to `TableAdapter` and check it in `SyncEngine._pushRecords()` — when true, always INSERT (never upsert/update).

#### Step 13.2.2: Register in SyncRegistry

Modify `lib/features/sync/engine/sync_registry.dart`:

1. Add import: `import 'package:construction_inspector/features/sync/adapters/consent_record_adapter.dart';`
2. Add `ConsentRecordAdapter()` to the list:

```dart
    SupportTicketAdapter(),
    ConsentRecordAdapter(),  // WHY: Push-only, append-only, no FK deps
  ]);
```

#### Step 13.2.3: Remove TODO from ConsentRepository

Modify `lib/features/settings/data/repositories/consent_repository.dart`:

Remove the TODO comment block (lines 9-12). Replace with:

```dart
  // WHY: Sync handled by ConsentRecordAdapter in SyncRegistry.
  // Push-only — no pull or conflict resolution (append-only with server triggers).
```

#### Step 13.2.4: Test

Run: `pwsh -Command "flutter test test/features/sync/"`

---

## Phase 14: Hardcoded Value Fixes

### Sub-phase 14.1: Remove Hardcoded formType Default in Router

**Files:**
- Modify: `lib/core/router/app_router.dart` (lines 694-695)
- Test: Manual verification (router test if exists)

**Agent**: `general-purpose`

#### Step 14.1.1: Move formType Resolution Into the Form Screen's initState

**REVIEW FIX:** FutureBuilder inside a GoRouter builder is an anti-pattern — GoRouter builders
must return widgets synchronously. Instead, keep the route builder simple and let the form
screen itself resolve its formType if not provided.

Modify `lib/core/router/app_router.dart` at the `/form/:responseId` route (line 694-695):

```dart
builder: (context, state) {
  final responseId = state.pathParameters['responseId']!;
  final projectId = state.uri.queryParameters['projectId'] ?? '';
  // WHY: Pass formType as nullable. The screen resolves it from the DB if missing.
  // This avoids FutureBuilder in the router (anti-pattern) and keeps routing synchronous.
  final formType = state.uri.queryParameters['formType'];

  // WHY: When formType is known, dispatch via registry (fast path).
  if (formType != null && formType.isNotEmpty) {
    final registry = FormScreenRegistry.instance;
    final builder = registry.get(formType);
    if (builder != null) {
      return builder(
        formId: formType,
        responseId: responseId,
        projectId: projectId,
      );
    }
  }

  // WHY: When formType is missing, fall back to MdotHubScreen which can resolve
  // the form type in its own initState via FormResponseRepository lookup.
  // Remove the hardcoded 'mdot_0582b' default — let the screen handle it.
  return MdotHubScreen(responseId: responseId);
},
```

**PREREQUISITE:** `MdotHubScreen` (and any future form screens) should handle the case where
`formType` is not passed as a constructor param. In `initState`, query `FormResponseRepository`
for the response's `form_type` column and configure accordingly. Add a method to `FormResponseRepository`:

In `lib/features/forms/domain/repositories/form_response_repository.dart`:
```dart
/// Look up the form_type for a response by ID.
/// WHY: Form screens need to resolve formType when not provided via route query params.
Future<String?> getFormTypeForResponse(String responseId);
```

Implement in the concrete repository — a simple `SELECT form_type FROM form_responses WHERE id = ?`.

Remove the `// TODO: Remove hardcoded default` comment from app_router.dart.

#### Step 14.1.2: Test

Run: `pwsh -Command "flutter test test/core/router/"`

---

### Sub-phase 14.2: Enable Sentry Performance Tracing

**Files:**
- Modify: `lib/main.dart` (lines 75-79)
- Test: Manual verification (Sentry doesn't need unit tests)

**Agent**: `general-purpose`

#### Step 14.2.1: Set tracesSampleRate and Add Consent Check

Modify `lib/main.dart` lines 75-79:

Replace:
```dart
      // NOTE: tracesSampleRate intentionally kept at 0.0. Performance tracing requires
      // a beforeSendTransaction consent check. Deferred to a future hardening phase
      // (consent UI wiring complete as of Phase 7, but transaction tracing not prioritized
      // for initial release).
      options.tracesSampleRate = 0.0;
```

With:
```dart
      // WHY: 10% sampling rate for performance tracing. Consent is checked
      // in beforeSendTransaction — transactions are dropped when user has
      // not granted analytics consent.
      options.tracesSampleRate = 0.1;
      options.beforeSendTransaction = _beforeSendTransaction;
```

Add the callback function near `_beforeSendSentry`:

```dart
/// Drop performance transactions when the user has not consented to analytics.
/// WHY: GDPR compliance — no telemetry without explicit consent.
SentryTransaction? _beforeSendTransaction(SentryTransaction transaction, Hint hint) {
  if (!sentryConsentGranted) return null;
  return transaction;
}
```

Add import if not already present:
```dart
import 'package:construction_inspector/core/config/sentry_consent.dart';
```

#### Step 14.2.2: Test

Run: `pwsh -Command "flutter analyze"`

---

### Sub-phase 14.3: Fetch Consent Policy Version from app_config

**Files:**
- Modify: `lib/features/settings/presentation/providers/consent_provider.dart` (lines 26-28)
- Modify: `lib/features/auth/presentation/providers/app_config_provider.dart` (expose policy version)
- Test: `test/features/settings/presentation/providers/consent_provider_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 14.3.1: Add Policy Version to AppConfigProvider

Modify `lib/features/auth/presentation/providers/app_config_provider.dart`:

Add a new cached field:
```dart
String? _currentPolicyVersion;
```

Add a getter:
```dart
/// Current consent policy version from remote config.
/// Falls back to '1.0.0' when not configured remotely.
String get currentPolicyVersion => _currentPolicyVersion ?? '1.0.0';
```

In the method that parses the fetched config map (wherever `configMap` is processed), add:
```dart
_currentPolicyVersion = configMap['current_policy_version'];
```

**PREREQUISITE:** Add a `current_policy_version` key-value pair to the Supabase `app_config` table. This is a data migration, not a code change:

```sql
INSERT INTO app_config (key, value) VALUES ('current_policy_version', '1.0.0')
ON CONFLICT (key) DO NOTHING;
```

#### Step 14.3.2: Update ConsentProvider to Use AppConfigProvider

Modify `lib/features/settings/presentation/providers/consent_provider.dart`:

1. Add `AppConfigProvider` as a dependency:
```dart
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
```

2. Add field and constructor param:
```dart
final AppConfigProvider? _appConfigProvider;

ConsentProvider({
  required PreferencesService preferencesService,
  required ConsentRepository consentRepository,
  required AuthProvider authProvider,
  AppConfigProvider? appConfigProvider,
})  : _prefs = preferencesService,
      _consentRepository = consentRepository,
      _authProvider = authProvider,
      _appConfigProvider = appConfigProvider;
```

3. Replace the static constant (line 28):
```dart
/// Current policy version. Fetched from app_config table via AppConfigProvider.
/// Falls back to '1.0.0' when remote config is unavailable.
/// WHY: Remote versioning allows forcing re-consent on policy updates
/// without an app update.
String get currentPolicyVersion =>
    _appConfigProvider?.currentPolicyVersion ?? _fallbackPolicyVersion;

static const String _fallbackPolicyVersion = '1.0.0';
```

4. Update all internal references from `currentPolicyVersion` (static) to the new getter. Since it was `static const`, callers may reference it as `ConsentProvider.currentPolicyVersion` — search and update those to use the instance getter instead.

#### Step 14.3.3: Test

Run: `pwsh -Command "flutter test test/features/settings/"`

---

## Phase 15: Deprecated Code Migration

### Sub-phase 15.1: Remove NormalizeProctorRowUseCase — Migrate to Calculator

**Files:**
- Modify: `lib/features/forms/data/registries/form_calculator_registry.dart` (add normalization logic)
- Modify: `lib/features/forms/presentation/providers/inspector_form_provider.dart` (remove deprecated field, lines 8,19-20,29-30,38,389-414)
- Modify: `lib/features/forms/di/forms_providers.dart` (remove use case, lines 14,45-46,67)
- Modify: `lib/test_harness/harness_providers.dart` (lines 181,301-302)
- Modify: `lib/features/forms/presentation/screens/mdot_hub_screen.dart` (2 call sites)
- Delete: `lib/features/forms/domain/usecases/normalize_proctor_row_use_case.dart`
- Test: `test/features/forms/presentation/providers/inspector_form_provider_test.dart`

**Agent**: `general-purpose`

#### Step 15.1.1: Move Normalization Logic into Mdot0582bCalculator

Locate the Mdot0582bCalculator in `lib/features/forms/data/registries/form_calculator_registry.dart` or a sub-file. Add a method that handles the 0582B-specific weight normalization (the logic currently in `normalize_proctor_row_use_case.dart` lines 27-38):

```dart
/// Normalize 0582B proctor row data before appending.
/// WHY: Migrated from deprecated NormalizeProctorRowUseCase.
/// Strips chart_type, normalizes weights_20_10 list, sets wet_soil_mold_g.
Map<String, dynamic> normalizeProctorRow(Map<String, dynamic> row) {
  final normalized = Map<String, dynamic>.from(row);
  normalized.remove('chart_type');
  final weights =
      (normalized['weights_20_10'] as List?)
          ?.map((value) => '$value'.trim())
          .where((value) => value.isNotEmpty)
          .toList() ??
      <String>[];
  normalized['weights_20_10'] = weights;
  if (weights.isNotEmpty) {
    normalized['wet_soil_mold_g'] = weights.last;
  }
  return normalized;
}
```

#### Step 15.1.2: Update appendMdot0582bProctorRow Callers

In `lib/features/forms/presentation/screens/mdot_hub_screen.dart`, the two call sites (lines 512 and 564) call `provider.appendMdot0582bProctorRow(responseId: ..., row: ...)`.

These need to be migrated to use the calculator normalization + `appendRow()`. However, `appendRow` uses `CalculateFormFieldUseCase` which calls the calculator registry. The normalization needs to happen before the row is appended.

**Option A (simpler):** Keep `appendMdot0582bProctorRow` in InspectorFormProvider but inline the normalization (remove the deprecated use case dependency):

```dart
Future<FormResponse?> appendMdot0582bProctorRow({
  required String responseId,
  required Map<String, dynamic> row,
}) async {
  // WHY: Normalization moved from NormalizeProctorRowUseCase into calculator
  final calculator = FormCalculatorRegistry.instance.get('mdot_0582b');
  final normalizedRow = calculator?.normalizeProctorRow(row) ?? row;

  // Append via the save use case directly
  final result = await _saveFormResponseUseCase.appendProctorRow(
    responseId: responseId,
    row: normalizedRow,
  );
  // ... update _responses list ...
}
```

Remove the `@Deprecated` annotation since this is now the canonical path.

#### Step 15.1.3: Remove NormalizeProctorRowUseCase from DI

In `lib/features/forms/di/forms_providers.dart`:
1. Remove import (line 14)
2. Remove `final normalizeProctorRowUseCase = ...` (line 46)
3. Remove `normalizeProctorRowUseCase: normalizeProctorRowUseCase,` from InspectorFormProvider construction (line 67)

In `lib/test_harness/harness_providers.dart`:
1. Remove `final normalizeProctorRowUseCase = ...` (line 181)
2. Remove `normalizeProctorRowUseCase: normalizeProctorRowUseCase,` (line 302)

In `lib/features/forms/presentation/providers/inspector_form_provider.dart`:
1. Remove import of `normalize_proctor_row_use_case.dart` (line 8)
2. Remove `final NormalizeProctorRowUseCase _normalizeProctorRowUseCase;` field (line 20)
3. Remove constructor param and initializer (lines 29-30, 38)

#### Step 15.1.4: Delete Deprecated Use Case

Delete `lib/features/forms/domain/usecases/normalize_proctor_row_use_case.dart`.

#### Step 15.1.5: Test

Run: `pwsh -Command "flutter test test/features/forms/"`

---

### Sub-phase 15.2: Remove Deprecated deleteByEntryId Methods

**Files:**
- Modify: `lib/features/photos/data/datasources/local/photo_local_datasource.dart` (line 62-67)
- Modify: `lib/features/contractors/data/datasources/local/entry_equipment_local_datasource.dart` (line 89-94)
- Modify: `lib/features/quantities/data/datasources/local/entry_quantity_local_datasource.dart` (line 125-130)
- Modify: `lib/features/forms/data/datasources/local/form_response_local_datasource.dart` (line 104-110)
- Test: Verify no callers remain first

**Agent**: `backend-data-layer-agent`

#### Step 15.2.1: Verify No Active Callers

Search for all invocations of each deprecated `deleteByEntryId` on the 4 local datasource classes. The grep output shows:
- `photo_local_datasource.dart:63` — deprecated method. Callers: `photo_repository_test.dart` (test mock uses it)
- `entry_equipment_local_datasource.dart:90` — deprecated method. No production callers found.
- `entry_quantity_local_datasource.dart:126` — deprecated method. Test callers in `entry_quantity_repository_test.dart` (mock datasource)
- `form_response_local_datasource.dart:105` — deprecated method. No production callers found.

**WARNING:** Test mocks reference `deleteByEntryId`. Before removing, verify test mocks call `softDeleteByEntryId` instead. If test mocks still reference the deprecated method, update them first.

#### Step 15.2.2: Update Test Mocks

In `test/helpers/mocks/mock_repositories.dart` (line 636), `test/data/repositories/photo_repository_test.dart` (line 46), and `test/data/repositories/entry_quantity_repository_test.dart` (line 58):

Rename `deleteByEntryId` to `softDeleteByEntryId` if the mock is implementing the datasource interface. If it's implementing the repository interface (which uses `softDeleteByEntryId`), no change needed — just verify.

#### Step 15.2.3: Remove Deprecated Methods

From each of the 4 files, remove the `@Deprecated` method and its doc comment:

1. `photo_local_datasource.dart` — remove lines 61-67 (`deleteByEntryId`)
2. `entry_equipment_local_datasource.dart` — remove lines 88-94 (`deleteByEntryId`)
3. `entry_quantity_local_datasource.dart` — remove lines 124-130 (`deleteByEntryId`)
4. `form_response_local_datasource.dart` — remove lines 103-110 (`deleteByEntryId`)

#### Step 15.2.4: Test

Run: `pwsh -Command "flutter test test/features/photos/ test/features/contractors/ test/features/quantities/ test/features/forms/ test/data/repositories/"`

---

### Sub-phase 15.3: Extract SyncControlService

**Files:**
- Create: `lib/features/sync/engine/sync_control_service.dart`
- Modify: `lib/features/projects/data/repositories/project_repository.dart` (lines 68-77)
- Modify: `lib/features/projects/data/services/project_lifecycle_service.dart` (sync_control usage)
- Test: `test/features/sync/engine/sync_control_service_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 15.3.1: Create SyncControlService

Create `lib/features/sync/engine/sync_control_service.dart`:

```dart
import 'package:sqflite/sqflite.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';

/// Service that suppresses change_log triggers during operations that
/// should not generate sync events (draft saves, device removal, etc.).
///
/// WHY: Extracted from project_repository.saveDraftSuppressed() and
/// project_lifecycle_service.removeFromDevice() to eliminate duplicate
/// sync_control SQL across the codebase.
///
/// Uses the sync_control table's 'pulling' key — when set to '1',
/// SQLite triggers skip change_log inserts.
class SyncControlService {
  final DatabaseService _dbService;

  SyncControlService(this._dbService);

  /// Run [operation] with sync triggers suppressed.
  ///
  /// Sets sync_control.pulling = '1' before the operation and '0' after,
  /// guaranteeing cleanup via try/finally even on exception.
  Future<T> runSuppressed<T>(Future<T> Function() operation) async {
    final db = await _dbService.database;
    await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
    try {
      return await operation();
    } finally {
      await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
    }
  }

  /// Run [operation] with sync triggers suppressed, using an existing [Database].
  ///
  /// WHY: Some callers (e.g. ProjectLifecycleService) already hold a Database
  /// reference and should not re-acquire it.
  Future<T> runSuppressedWithDb<T>(Database db, Future<T> Function() operation) async {
    await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
    try {
      return await operation();
    } finally {
      await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
    }
  }
}
```

#### Step 15.3.2: Refactor ProjectRepository

Modify `lib/features/projects/data/repositories/project_repository.dart`:

Add `SyncControlService` as a constructor dependency. Replace `saveDraftSuppressed` (lines 70-78):

```dart
final SyncControlService _syncControlService;

// In constructor:
// ProjectRepository(this._localDatasource, this._databaseService, this._syncControlService);

/// Saves a project draft while suppressing change_log triggers.
/// WHY: Draft saves should not trigger sync — the project isn't finalized yet.
Future<void> saveDraftSuppressed(Project project) async {
  await _syncControlService.runSuppressed(() => save(project));
}
```

Similarly refactor `discardDraft` (lines 83-97) to use `_syncControlService.runSuppressed(...)`.

Remove the `// TODO: Extract sync_control suppression` comment (line 68).

#### Step 15.3.3: Refactor ProjectLifecycleService

Modify `lib/features/projects/data/services/project_lifecycle_service.dart`:

Replace inline sync_control SQL (lines 108, 273) with `SyncControlService.runSuppressedWithDb(db, ...)`. Add `SyncControlService` as a constructor param, or pass the `DatabaseService` and use `runSuppressed`.

**NOTE:** `ProjectLifecycleService` constructor takes `Database _db` directly (not `DatabaseService`). Use `runSuppressedWithDb(db, ...)` variant.

#### Step 15.3.4: Test

Create unit test:
```dart
// test/features/sync/engine/sync_control_service_test.dart
// Test runSuppressed sets pulling=1 before and pulling=0 after
// Test runSuppressed resets pulling=0 even on exception
// Test runSuppressedWithDb works with an existing Database instance
```

Run: `pwsh -Command "flutter test test/features/sync/engine/sync_control_service_test.dart"`
Run: `pwsh -Command "flutter test test/features/projects/"`

---

### Sub-phase 15.4: Clean Up app_theme.dart Self-Deprecated References

**Files:**
- Modify: `lib/core/theme/app_theme.dart`
- Test: `pwsh -Command "flutter analyze"`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 15.4.1: Audit Internal References

The file has ~16 `@Deprecated` annotations. The deprecated constants in `AppTheme` forward to `AppColors.*` values. Internal references within `app_theme.dart` that use deprecated constants (e.g., `primaryCyan`, `statusSuccess`, `surfaceElevated`) should be replaced with their `AppColors.*` sources directly.

Example replacements within `app_theme.dart`:
- `primaryCyan` → `AppColors.primaryCyan`  (already what it forwards to, but remove the self-reference if the deprecated constant is used internally)
- `statusSuccess` → `AppColors.statusSuccess`
- `surfaceElevated` → `AppColors.surfaceElevated`

**IMPORTANT:** Do NOT remove the deprecated constants themselves — they exist for external backward compat. Only replace *internal* usage of the deprecated names with the non-deprecated `AppColors.*` sources.

Search within `app_theme.dart` for uses of each deprecated constant name in theme definitions (colorScheme, etc.) and replace with the `AppColors.*` direct reference.

#### Step 15.4.2: Test

Run: `pwsh -Command "flutter analyze"`

The analyze output should show no new warnings. Existing deprecation warnings from external callers are expected and will be addressed separately.

---

## Execution Order & Dependencies

```
Phase 11 (Layer Violations)
├── 11.1 DeletionNotificationBanner ──┐
├── 11.2 ConflictViewerScreen ────────┤ (independent, can parallel)
├── 11.3+11.5 FormQuickActionRegistry ┤
└── 11.4 Auth + Injection ────────────┘

Phase 12 (Document Opening) ← independent

Phase 13 (Sync Adapters)
├── 13.1 SupportTicketAdapter ──┐ (independent, can parallel)
└── 13.2 ConsentRecordAdapter ──┘

Phase 14 (Hardcoded Values)
├── 14.1 Router formType ← needs FormResponseRepository method
├── 14.2 Sentry tracing  ← independent
└── 14.3 Policy version  ← needs app_config migration

Phase 15 (Deprecated Code)
├── 15.1 NormalizeProctorRowUseCase ← independent
├── 15.2 deleteByEntryId methods ← independent
├── 15.3 SyncControlService ← independent
└── 15.4 app_theme cleanup ← independent
```

**Parallelism:** Sub-phases within each phase are independent unless noted. Phases 11-15 can be executed in order, but sub-phases within each can be dispatched to parallel agents.

## Verification

After all phases, run full test suite and static analysis:

```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
```

---

---

## Phase 16: Wire DailyEntry Methods to Provider/UI

### Sub-phase 16.1: Add Filtering Use Case

**Files:**
- Create: `lib/features/entries/domain/usecases/filter_entries_use_case.dart`
- Test: `test/features/entries/domain/usecases/filter_entries_use_case_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 16.1.1: Create FilterEntriesUseCase

Create `lib/features/entries/domain/usecases/filter_entries_use_case.dart`:

```dart
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';
import 'package:construction_inspector/features/entries/domain/repositories/daily_entry_repository.dart';

/// WHY: Pass-through use case for entry filtering operations.
/// Keeps provider decoupled from repository interface details.
class FilterEntriesUseCase {
  final DailyEntryRepository _repository;

  FilterEntriesUseCase({required DailyEntryRepository repository})
      : _repository = repository;

  /// Filter entries by date range within a project.
  Future<List<DailyEntry>> byDateRange(
    String projectId,
    DateTime startDate,
    DateTime endDate,
  ) =>
      _repository.getByDateRange(projectId, startDate, endDate);

  /// Filter entries by location within a project.
  Future<List<DailyEntry>> byLocation(String locationId) =>
      _repository.getByLocationId(locationId);

  /// Filter entries by status within a project.
  Future<List<DailyEntry>> byStatus(String projectId, EntryStatus status) =>
      _repository.getByStatus(projectId, status);

  /// Update the status of a single entry.
  Future<void> updateStatus(String id, EntryStatus status) =>
      _repository.updateStatus(id, status);

  /// Get total entry count for a project.
  /// REVIEW FIX: getCountByProject exists on concrete DailyEntryRepositoryImpl but NOT
  /// on the domain interface DailyEntryRepository. Must add it to the domain interface first:
  /// In lib/features/entries/domain/repositories/daily_entry_repository.dart, add:
  ///   Future<int> getCountByProject(String projectId);
  Future<int> countForProject(String projectId) =>
      _repository.getCountByProject(projectId);
}
```

**PREREQUISITE:** Add `Future<int> getCountByProject(String projectId);` to the domain interface
at `lib/features/entries/domain/repositories/daily_entry_repository.dart`. The method already
exists on the concrete `DailyEntryRepositoryImpl` — this just adds the interface declaration.

#### Step 16.1.2: Write unit test

Create `test/features/entries/domain/usecases/filter_entries_use_case_test.dart` with mock repository tests verifying:
- `byDateRange` delegates to `repository.getByDateRange`
- `byLocation` delegates to `repository.getByLocationId`
- `byStatus` delegates to `repository.getByStatus`
- `updateStatus` delegates to `repository.updateStatus`
- `countForProject` delegates to `repository.getCountByProject`

#### Step 16.1.3: Verify

Run: `pwsh -Command "flutter test test/features/entries/domain/usecases/filter_entries_use_case_test.dart"`

### Sub-phase 16.2: Wire Filtering Methods to DailyEntryProvider

**Files:**
- Modify: `lib/features/entries/presentation/providers/daily_entry_provider.dart`
- Modify: `lib/main.dart` (add FilterEntriesUseCase to provider construction)
- Test: `test/features/entries/presentation/providers/daily_entry_provider_filter_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 16.2.1: Add FilterEntriesUseCase dependency to DailyEntryProvider

In `lib/features/entries/presentation/providers/daily_entry_provider.dart`:

1. Add import for `FilterEntriesUseCase`.
2. Add `final FilterEntriesUseCase _filterEntriesUseCase;` field.
3. Add to constructor: `required FilterEntriesUseCase filterEntriesUseCase,` and wire in initializer list.
4. Add filter state fields after line 57:

```dart
  // Filter state
  // WHY: Tracks active filter for the entry list view — enables UI to show
  // which filter is active and clear it.
  EntryFilterType? _activeFilter;
  List<DailyEntry> _filteredEntries = [];
  bool _filterLoading = false;

  EntryFilterType? get activeFilter => _activeFilter;
  List<DailyEntry> get filteredEntries => _filteredEntries;
  bool get filterLoading => _filterLoading;
```

5. Add filter enum above the class:

```dart
/// WHY: Typed filter categories for the entry list view.
enum EntryFilterType { dateRange, location, status }
```

6. Add methods after the `loadMoreEntries` method (after line 362):

```dart
  /// Filter entries by date range.
  /// WHY: Enables calendar range selection on HomeScreen.
  Future<void> filterByDateRange(
    String projectId,
    DateTime startDate,
    DateTime endDate,
  ) async {
    _filterLoading = true;
    _activeFilter = EntryFilterType.dateRange;
    notifyListeners();
    try {
      _filteredEntries = await _filterEntriesUseCase.byDateRange(
        projectId, startDate, endDate,
      );
    } catch (e) {
      Logger.ui('[DailyEntryProvider] filterByDateRange error: $e');
      _filteredEntries = [];
    } finally {
      _filterLoading = false;
      notifyListeners();
    }
  }

  /// Filter entries by location.
  /// WHY: Enables location-based filtering from the location picker.
  Future<void> filterByLocation(String locationId) async {
    _filterLoading = true;
    _activeFilter = EntryFilterType.location;
    notifyListeners();
    try {
      _filteredEntries = await _filterEntriesUseCase.byLocation(locationId);
    } catch (e) {
      Logger.ui('[DailyEntryProvider] filterByLocation error: $e');
      _filteredEntries = [];
    } finally {
      _filterLoading = false;
      notifyListeners();
    }
  }

  /// Filter entries by status.
  /// WHY: Enables draft/submitted toggle in the entry list.
  Future<void> filterByStatus(String projectId, EntryStatus status) async {
    _filterLoading = true;
    _activeFilter = EntryFilterType.status;
    notifyListeners();
    try {
      _filteredEntries = await _filterEntriesUseCase.byStatus(projectId, status);
    } catch (e) {
      Logger.ui('[DailyEntryProvider] filterByStatus error: $e');
      _filteredEntries = [];
    } finally {
      _filterLoading = false;
      notifyListeners();
    }
  }

  /// Clear any active filter, returning to the full entry list.
  void clearFilter() {
    _activeFilter = null;
    _filteredEntries = [];
    notifyListeners();
  }

  /// Get total entry count for a project (async from DB).
  /// WHY: Enables "X entries" display on project dashboard card.
  Future<int> getEntryCount(String projectId) async {
    try {
      return await _filterEntriesUseCase.countForProject(projectId);
    } catch (e) {
      Logger.ui('[DailyEntryProvider] getEntryCount error: $e');
      return 0;
    }
  }
```

7. Update `clear()` (line 502-513) to also reset filter state:

```dart
    _activeFilter = null;
    _filteredEntries = [];
    _filterLoading = false;
```

#### Step 16.2.2: Wire FilterEntriesUseCase in main.dart

In `lib/main.dart`, find where `DailyEntryProvider` is constructed and add `FilterEntriesUseCase` to the dependency injection. The use case takes `DailyEntryRepository` as its only dependency.

#### Step 16.2.3: Write provider tests

Test in `test/features/entries/presentation/providers/daily_entry_provider_filter_test.dart`:
- `filterByDateRange` sets `activeFilter`, populates `filteredEntries`, resets `filterLoading`
- `filterByLocation` sets `activeFilter` to `location`
- `filterByStatus` sets `activeFilter` to `status`
- `clearFilter` resets all filter state
- `getEntryCount` returns count from use case
- Error handling: each filter method catches exceptions, logs, returns empty list

#### Step 16.2.4: Verify

Run: `pwsh -Command "flutter test test/features/entries/presentation/providers/"`

---

## Phase 17: Wire Todo Methods to Provider/UI

### Sub-phase 17.1: Add Filter and Query Methods to TodoProvider

**Files:**
- Modify: `lib/features/todos/presentation/providers/todo_provider.dart`
- Test: `test/features/todos/presentation/providers/todo_provider_filter_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 17.1.1: Add repository-backed query methods

In `lib/features/todos/presentation/providers/todo_provider.dart`, add the following methods after `deleteCompleted()` (after line 204):

```dart
  /// Load todos linked to a specific daily entry.
  /// WHY: Entry editor shows related todos in a "Linked Todos" section.
  Future<List<TodoItem>> getByEntryId(String entryId) async {
    try {
      return await _repository.getByEntryId(entryId);
    } catch (e) {
      Logger.ui('[TodoProvider] getByEntryId error: $e');
      return [];
    }
  }

  /// Load todos filtered by priority.
  /// WHY: Priority filter chip on TodosScreen.
  Future<void> loadByPriority(TodoPriority priority) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _todos = await _repository.getByPriority(priority, projectId: _currentProjectId);
    } catch (e) {
      _error = 'Failed to filter by priority: $e';
      Logger.ui('[TodoProvider] loadByPriority error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Load only overdue todos.
  /// WHY: "Overdue" filter chip on TodosScreen.
  Future<void> loadOverdue() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _todos = await _repository.getOverdue(projectId: _currentProjectId);
    } catch (e) {
      _error = 'Failed to load overdue todos: $e';
      Logger.ui('[TodoProvider] loadOverdue error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Load todos due today.
  /// WHY: "Due Today" filter chip on TodosScreen.
  Future<void> loadDueToday() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _todos = await _repository.getDueToday(projectId: _currentProjectId);
    } catch (e) {
      _error = 'Failed to load due today todos: $e';
      Logger.ui('[TodoProvider] loadDueToday error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Get incomplete count from the database.
  /// WHY: Badge count on the Toolbox hub card — shows actionable items.
  Future<int> getIncompleteCount({String? projectId}) async {
    try {
      return await _repository.getIncompleteCount(projectId: projectId ?? _currentProjectId);
    } catch (e) {
      Logger.ui('[TodoProvider] getIncompleteCount error: $e');
      return 0;
    }
  }

  /// Delete all todos for a project.
  /// WHY: Cleanup when a project is removed from device.
  Future<bool> deleteByProject(String projectId) async {
    if (!canWrite()) {
      Logger.ui('[TodoProvider] deleteByProject blocked: canWrite returned false');
      return false;
    }
    try {
      await _repository.deleteByProjectId(projectId);
      if (_currentProjectId == projectId) {
        _todos = [];
        notifyListeners();
      }
      return true;
    } catch (e) {
      _error = 'Failed to delete project todos: $e';
      Logger.ui('[TodoProvider] deleteByProject error: $e');
      notifyListeners();
      return false;
    }
  }
```

#### Step 17.1.2: Write tests

Create `test/features/todos/presentation/providers/todo_provider_filter_test.dart`:
- `getByEntryId` returns list from repository
- `loadByPriority` replaces `_todos` with filtered results
- `loadOverdue` replaces `_todos` with overdue items
- `loadDueToday` replaces `_todos` with due-today items
- `getIncompleteCount` returns int from repository
- `deleteByProject` clears local state when current project matches
- Error handling for each method

#### Step 17.1.3: Verify

Run: `pwsh -Command "flutter test test/features/todos/presentation/providers/"`

### Sub-phase 17.2: Wire Filter Chips to TodosScreen

**Files:**
- Modify: `lib/features/todos/presentation/screens/todos_screen.dart`
- Test: `test/features/todos/presentation/screens/todos_screen_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 17.2.1: Add filter chip bar

In `lib/features/todos/presentation/screens/todos_screen.dart`, add a horizontal row of `FilterChip` widgets above the todo list:

- "All" chip: calls `provider.loadTodos(projectId: projectId)` (existing)
- "Overdue" chip: calls `provider.loadOverdue()`
- "Due Today" chip: calls `provider.loadDueToday()`
- "High Priority" chip: calls `provider.loadByPriority(TodoPriority.high)`

Track the selected chip in local state (`_selectedFilter`). Each chip tap sets the filter and reloads.

#### Step 17.2.2: Write widget test

Test that each filter chip is present and tapping triggers the appropriate provider method (use mock provider).

#### Step 17.2.3: Verify

Run: `pwsh -Command "flutter test test/features/todos/presentation/screens/todos_screen_test.dart"`

---

## Phase 18: Wire Document Methods to Provider/UI

### Sub-phase 18.1: Add Project-Level Document Loading to DocumentProvider

**Files:**
- Modify: `lib/features/forms/presentation/providers/document_provider.dart`
- Modify: `lib/features/forms/domain/usecases/manage_documents_use_case.dart`
- Test: `test/features/forms/presentation/providers/document_provider_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 18.1.1: Add getByProjectId pass-through to ManageDocumentsUseCase

In `lib/features/forms/domain/usecases/manage_documents_use_case.dart`, add:

```dart
  /// Get all documents for a project (all entries).
  /// WHY: Project-level document view shows all attached files.
  Future<List<Document>> getProjectDocuments(String projectId) =>
      _documentRepository.getByProjectId(projectId);
```

This requires the use case to hold a reference to `DocumentRepository`. Verify it already does; if not, add it as a constructor parameter.

#### Step 18.1.2: Add project document loading to DocumentProvider

In `lib/features/forms/presentation/providers/document_provider.dart`, add state and method after the `_entryDocuments` field (after line 15):

```dart
  List<Document> _projectDocuments = [];
  List<Document> get projectDocuments => _projectDocuments;
  bool _isLoadingProjectDocuments = false;
  bool get isLoadingProjectDocuments => _isLoadingProjectDocuments;
```

Update the `isLoading` getter (line 26) to include the new flag:

```dart
  bool get isLoading => _isLoadingDocuments || _isLoadingEntryDocuments || _isLoadingProjectDocuments;
```

Add method after `loadEntryDocuments` (after line 69):

```dart
  /// Load all documents for a project across all entries.
  /// WHY: Enables project-level document view showing all attached files.
  Future<void> loadProjectDocuments(String projectId) async {
    _isLoadingProjectDocuments = true;
    notifyListeners();
    try {
      _projectDocuments = await _useCase.getProjectDocuments(projectId);
    } catch (e) {
      _error = 'Failed to load project documents: $e';
    } finally {
      _isLoadingProjectDocuments = false;
      notifyListeners();
    }
  }
```

#### Step 18.1.3: Write tests

Create `test/features/forms/presentation/providers/document_provider_test.dart`:
- `loadProjectDocuments` sets loading state, populates `projectDocuments`, resets loading
- Error case: sets `_error`, resets loading

#### Step 18.1.4: Verify

Run: `pwsh -Command "flutter test test/features/forms/presentation/providers/document_provider_test.dart"`

---

## Phase 19: Wire Export Methods to Provider/UI

### Sub-phase 19.1: Add Export History to EntryExportProvider

**Files:**
- Modify: `lib/features/entries/presentation/providers/entry_export_provider.dart`
- Modify: `lib/features/entries/domain/usecases/export_entry_use_case.dart`
- Test: `test/features/entries/presentation/providers/entry_export_provider_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 19.1.1: Add repository query methods to ExportEntryUseCase

In `lib/features/entries/domain/usecases/export_entry_use_case.dart`, add methods that delegate to `EntryExportRepository`:

```dart
  /// Get all exports for a project.
  /// WHY: "Previous Exports" section in project detail screen.
  Future<List<EntryExport>> getByProjectId(String projectId) =>
      _entryExportRepository.getByProjectId(projectId);

  /// Get exports for a specific entry.
  /// WHY: "Previous Exports" section in entry detail screen.
  Future<List<EntryExport>> getByEntryId(String entryId) =>
      _entryExportRepository.getByEntryId(entryId);
```

This requires `ExportEntryUseCase` to hold a reference to `EntryExportRepository`. Verify it already does; if not, add it.

#### Step 19.1.2: Add export history state to EntryExportProvider

In `lib/features/entries/presentation/providers/entry_export_provider.dart`, add after the `_errorMessage` field (line 19):

```dart
  List<EntryExport> _exportHistory = [];
  List<EntryExport> get exportHistory => _exportHistory;
  bool _isLoadingHistory = false;
  bool get isLoadingHistory => _isLoadingHistory;
```

Add methods after `exportAllFormsForEntry` (after line 51):

```dart
  /// Load export history for a project.
  /// WHY: Enables "Previous Exports" section showing all past PDF exports.
  Future<void> loadExportHistory(String projectId) async {
    _isLoadingHistory = true;
    notifyListeners();
    try {
      _exportHistory = await _exportEntryUseCase.getByProjectId(projectId);
    } catch (e) {
      Logger.error('[EntryExportProvider] loadExportHistory error', error: e);
      _exportHistory = [];
    } finally {
      _isLoadingHistory = false;
      notifyListeners();
    }
  }

  /// Load export history for a specific entry.
  /// WHY: Entry detail screen shows past exports for that entry.
  Future<void> loadEntryExportHistory(String entryId) async {
    _isLoadingHistory = true;
    notifyListeners();
    try {
      _exportHistory = await _exportEntryUseCase.getByEntryId(entryId);
    } catch (e) {
      Logger.error('[EntryExportProvider] loadEntryExportHistory error', error: e);
      _exportHistory = [];
    } finally {
      _isLoadingHistory = false;
      notifyListeners();
    }
  }
```

Add necessary import for `EntryExport` model.

#### Step 19.1.3: Verify

Run: `pwsh -Command "flutter test test/features/entries/presentation/providers/"`

### Sub-phase 19.2: Add Export History to FormExportProvider

**Files:**
- Modify: `lib/features/forms/presentation/providers/form_export_provider.dart`
- Modify: `lib/features/forms/domain/usecases/export_form_use_case.dart`
- Test: `test/features/forms/presentation/providers/form_export_provider_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 19.2.1: Add repository query methods to ExportFormUseCase

In `lib/features/forms/domain/usecases/export_form_use_case.dart`, add:

```dart
  /// Get all form exports for a project.
  Future<List<FormExport>> getByProjectId(String projectId) =>
      _formExportRepository.getByProjectId(projectId);

  /// Get form exports for a specific entry.
  Future<List<FormExport>> getByEntryId(String entryId) =>
      _formExportRepository.getByEntryId(entryId);

  /// Get exports for a specific form response.
  Future<List<FormExport>> getByFormResponseId(String responseId) =>
      _formExportRepository.getByFormResponseId(responseId);
```

Verify `ExportFormUseCase` holds `FormExportRepository`; add if missing.

#### Step 19.2.2: Add export history state to FormExportProvider

In `lib/features/forms/presentation/providers/form_export_provider.dart`, add after `_errorMessage` (line 14):

```dart
  List<FormExport> _exportHistory = [];
  List<FormExport> get exportHistory => _exportHistory;
  bool _isLoadingHistory = false;
  bool get isLoadingHistory => _isLoadingHistory;
```

Add methods after `exportFormToPdf` (after line 43):

```dart
  /// Load export history for a project.
  /// WHY: Shows all past form exports across the project.
  Future<void> loadProjectExportHistory(String projectId) async {
    _isLoadingHistory = true;
    notifyListeners();
    try {
      _exportHistory = await _exportFormUseCase.getByProjectId(projectId);
    } catch (e) {
      Logger.error('[FormExportProvider] loadProjectExportHistory error', error: e);
      _exportHistory = [];
    } finally {
      _isLoadingHistory = false;
      notifyListeners();
    }
  }

  /// Load export history for a specific form response.
  /// WHY: Form detail screen shows "Previous Exports" for that response.
  Future<void> loadResponseExportHistory(String responseId) async {
    _isLoadingHistory = true;
    notifyListeners();
    try {
      _exportHistory = await _exportFormUseCase.getByFormResponseId(responseId);
    } catch (e) {
      Logger.error('[FormExportProvider] loadResponseExportHistory error', error: e);
      _exportHistory = [];
    } finally {
      _isLoadingHistory = false;
      notifyListeners();
    }
  }
```

Add necessary import for `FormExport` model.

#### Step 19.2.3: Verify

Run: `pwsh -Command "flutter test test/features/forms/presentation/providers/"`

---

## Phase 20: Wire Photo Utility Methods

### Sub-phase 20.1: Add Photo Count Methods to PhotoProvider

**Files:**
- Modify: `lib/features/photos/presentation/providers/photo_provider.dart`
- Test: `test/features/photos/presentation/providers/photo_provider_count_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 20.1.1: Add count and bulk-delete methods

In `lib/features/photos/presentation/providers/photo_provider.dart`, add after `getPhotoById` (after line 139):

```dart
  /// Get photo count for an entry (async DB query).
  /// WHY: Enables photo count badges on entry list items without loading full photo objects.
  Future<int> getPhotoCountForEntry(String entryId) async {
    final result = await _repository.getPhotoCountForEntry(entryId);
    if (result.isSuccess) {
      return result.data ?? 0;
    }
    Logger.photo('[PhotoProvider] getPhotoCountForEntry error: ${result.error}');
    return 0;
  }

  /// Get photo count for a project (async DB query).
  /// WHY: Enables project dashboard stats showing total photos.
  Future<int> getPhotoCountForProject(String projectId) async {
    final result = await _repository.getPhotoCountForProject(projectId);
    if (result.isSuccess) {
      return result.data ?? 0;
    }
    Logger.photo('[PhotoProvider] getPhotoCountForProject error: ${result.error}');
    return 0;
  }

  /// Delete all photos for an entry.
  /// WHY: Cascade cleanup when an entry is deleted.
  Future<bool> deletePhotosForEntry(String entryId) async {
    if (!canWrite()) {
      Logger.photo('[PhotoProvider] deletePhotosForEntry blocked: canWrite returned false');
      return false;
    }
    final result = await _repository.deletePhotosForEntry(entryId);
    if (result.isSuccess) {
      _photos.removeWhere((p) => p.entryId == entryId);
      notifyListeners();
      return true;
    }
    _error = result.error;
    Logger.photo('[PhotoProvider] deletePhotosForEntry error: ${result.error}');
    notifyListeners();
    return false;
  }
```

#### Step 20.1.2: Write tests

Create `test/features/photos/presentation/providers/photo_provider_count_test.dart`:
- `getPhotoCountForEntry` returns count on success, 0 on error
- `getPhotoCountForProject` returns count on success, 0 on error
- `deletePhotosForEntry` removes matching photos from local state
- `deletePhotosForEntry` blocked when `canWrite` returns false

#### Step 20.1.3: Verify

Run: `pwsh -Command "flutter test test/features/photos/presentation/providers/"`

---

## Phase 21: Wire EntryQuantity Utility Methods

### Sub-phase 21.1: Add Bid Item Query and Bulk Delete to EntryQuantityProvider

**Files:**
- Modify: `lib/features/quantities/presentation/providers/entry_quantity_provider.dart`
- Test: `test/features/quantities/presentation/providers/entry_quantity_provider_extra_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 21.1.1: Add methods

In `lib/features/quantities/presentation/providers/entry_quantity_provider.dart`, add after `getQuantitiesForBidItem` (after line 289):

```dart
  /// Load all quantities across all entries for a specific bid item.
  /// WHY: Enables bid item detail view showing every entry that reported
  /// quantities against this item, with running total.
  Future<List<EntryQuantity>> getQuantitiesForBidItemFromDb(String bidItemId) async {
    try {
      return await _repository.getByBidItemId(bidItemId);
    } catch (e) {
      Logger.db('[EntryQuantityProvider] getQuantitiesForBidItemFromDb error: $e');
      return [];
    }
  }

  /// Delete all quantities for a specific entry.
  /// WHY: Cascade cleanup when an entry is deleted.
  Future<bool> deleteQuantitiesForEntry(String entryId) async {
    try {
      await _repository.deleteByEntryId(entryId);
      if (_currentEntryId == entryId) {
        _quantities = [];
        notifyListeners();
      }
      return true;
    } catch (e) {
      Logger.db('[EntryQuantityProvider] deleteQuantitiesForEntry error: $e');
      _error = 'Failed to delete quantities: $e';
      notifyListeners();
      return false;
    }
  }

  /// Delete all quantities for a specific bid item.
  /// WHY: Cascade cleanup when a bid item is removed from a project.
  Future<bool> deleteQuantitiesForBidItem(String bidItemId) async {
    try {
      await _repository.deleteByBidItemId(bidItemId);
      _quantities.removeWhere((q) => q.bidItemId == bidItemId);
      _usedByBidItem.remove(bidItemId);
      notifyListeners();
      return true;
    } catch (e) {
      Logger.db('[EntryQuantityProvider] deleteQuantitiesForBidItem error: $e');
      _error = 'Failed to delete bid item quantities: $e';
      notifyListeners();
      return false;
    }
  }

  /// Get count of quantities for an entry (async DB query).
  /// WHY: Enables showing quantity count badges on entry list items.
  Future<int> getCountForEntry(String entryId) async {
    try {
      return await _repository.getCountByEntry(entryId);
    } catch (e) {
      Logger.db('[EntryQuantityProvider] getCountForEntry error: $e');
      return 0;
    }
  }
```

#### Step 21.1.2: Write tests

Create `test/features/quantities/presentation/providers/entry_quantity_provider_extra_test.dart`:
- `getQuantitiesForBidItemFromDb` returns list from repository
- `deleteQuantitiesForEntry` clears local state when current entry matches
- `deleteQuantitiesForBidItem` removes from local list and `_usedByBidItem` map
- `getCountForEntry` returns count, 0 on error

#### Step 21.1.3: Verify

Run: `pwsh -Command "flutter test test/features/quantities/presentation/providers/"`

---

## Phase 22: Miscellaneous Remaining Items

### Sub-phase 22.1: Fix Driver isSyncing Hardcoded False (L1)

**Files:**
- Modify: `lib/features/sync/application/sync_orchestrator.dart`
- Modify: `lib/core/driver/driver_server.dart`
- Test: `test/core/driver/driver_server_sync_status_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 22.1.1: Add isSyncing getter to SyncOrchestrator

In `lib/features/sync/application/sync_orchestrator.dart`, add a public getter:

```dart
  /// WHY: Exposes live syncing state to the driver endpoint.
  /// The driver's /sync-status response was hardcoded false.
  bool _isSyncing = false;
  bool get isSyncing => _isSyncing;
```

Then wrap the existing sync execution logic to set `_isSyncing = true` before the sync starts and `_isSyncing = false` in a `finally` block when it completes. Find the main sync method (likely `syncLocalAgencyProjects` or `syncAll`) and add the flag management.

#### Step 22.1.2: Wire to driver response

In `lib/core/driver/driver_server.dart` at line 1250-1252, replace:

```dart
        // TODO: Expose isSyncing getter on SyncOrchestrator for accurate status
        'isSyncing': false,
```

with:

```dart
        // WHY: Live syncing state from SyncOrchestrator (was hardcoded false).
        'isSyncing': syncOrchestrator?.isSyncing ?? false,
```

This requires the driver server to have a reference to `SyncOrchestrator`. Verify it does (check the class fields for `syncOrchestrator`); if not, add `SyncOrchestrator? syncOrchestrator;` as a settable field.

#### Step 22.1.3: Write test

Test that `/driver/sync-status` returns `isSyncing: true` when orchestrator is syncing, `false` when idle.

#### Step 22.1.4: Verify

Run: `pwsh -Command "flutter test test/core/driver/"`

### Sub-phase 22.2: Add Foreground Fraction Alert (L2)

**Files:**
- Modify: `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
- Test: `test/features/pdf/services/extraction/stages/grid_line_remover_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 22.2.1: Add logger warning

In `lib/features/pdf/services/extraction/stages/grid_line_remover.dart` at line 494, replace:

```dart
    // TODO: Alert if foregroundFraction < 0.01 or > 0.90 (threshold mismatch indicator)
    final foregroundPixels = cv.countNonZero(binary);
    final foregroundFraction = foregroundPixels / (rows * cols);
```

with:

```dart
    // WHY: Extreme foreground fractions indicate threshold mismatch —
    // too low = nearly all background (blank page?), too high = everything is foreground.
    final foregroundPixels = cv.countNonZero(binary);
    final foregroundFraction = foregroundPixels / (rows * cols);
    if (foregroundFraction < 0.01 || foregroundFraction > 0.90) {
      Logger.ocr('WARNING: foregroundFraction=$foregroundFraction '
          '(pixels=$foregroundPixels, total=${rows * cols}). '
          'Possible threshold mismatch — check image quality.');
    }
```

Ensure `Logger` is imported at the top of the file.

#### Step 22.2.2: Write test

Add test case to existing grid_line_remover tests (or create new test file) that verifies the warning is logged when foreground fraction is below 0.01 or above 0.90. Use a mock Logger or verify Logger output.

#### Step 22.2.3: Verify

Run: `pwsh -Command "flutter test test/features/pdf/services/extraction/stages/"`

### Sub-phase 22.3: Fix Sentry setExtra Deprecated (L4)

**Files:**
- Modify: `lib/core/logging/logger.dart`
- Test: `test/core/logging/logger_test.dart`

**Agent**: `general-purpose`

#### Step 22.3.1: Replace deprecated setExtra with setContexts

In `lib/core/logging/logger.dart` at line 248-250, replace:

```dart
          if (scrubbedStack != null) {
            scope.setExtra('stack_trace', scrubbedStack);
          }
```

with:

```dart
          if (scrubbedStack != null) {
            // WHY: setExtra is deprecated in Sentry SDK.
            // Use setContexts to attach stack trace as structured context.
            scope.setContexts('stack_trace', {'value': scrubbedStack});
          }
```

#### Step 22.3.2: Verify

Run: `pwsh -Command "flutter test test/core/logging/"`

### Sub-phase 22.4: Implement Form Sub-Screen Stubs (L6)

**Files:**
- Modify: `lib/features/forms/presentation/screens/mdot_hub_screen.dart`
- Test: `test/features/forms/presentation/screens/form_sub_screens_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 22.4.1: Implement FormFillScreen

Replace the stub at lines 1071-1078 with a proper screen that:
1. Reads the `FormResponse` via `InspectorFormProvider.loadResponseById(responseId)`
2. Displays the full form with all sections (header + proctor + test) in a read/edit view
3. This is effectively the same as `MdotHubScreen` but with all sections expanded

Since `FormFillScreen` currently just delegates to `MdotHubScreen`, and the hub screen IS the form fill experience, this stub is actually correct behavior. Add a `// WHY:` comment explaining the delegation:

```dart
class FormFillScreen extends StatelessWidget {
  final String responseId;

  const FormFillScreen({super.key, required this.responseId});

  @override
  // WHY: FormFillScreen is the full-form entry point. The MdotHubScreen
  // already implements the complete fill experience (header + proctor + test
  // sections). This delegation is intentional, not a stub.
  Widget build(BuildContext context) => MdotHubScreen(responseId: responseId);
}
```

#### Step 22.4.2: Implement QuickTestEntryScreen

Replace the stub at lines 1080-1087. This screen should open the `MdotHubScreen` but auto-expand to the test section (section index 2):

```dart
class QuickTestEntryScreen extends StatelessWidget {
  final String responseId;

  const QuickTestEntryScreen({super.key, required this.responseId});

  @override
  // WHY: Quick Test Entry jumps directly to the test section.
  // Pass initialSection to MdotHubScreen to auto-expand section 2.
  Widget build(BuildContext context) => MdotHubScreen(
    responseId: responseId,
    initialSection: 2,
  );
}
```

This requires adding an `initialSection` parameter to `MdotHubScreen`:

In the `MdotHubScreen` widget (line 21-28), add:

```dart
  final int? initialSection;

  const MdotHubScreen({super.key, required this.responseId, this.initialSection});
```

In `_MdotHubScreenState._hydrate` (line 246), update the default expanded logic:

```dart
    _expanded = widget.initialSection ??
        (!_headerConfirmed ? 0 : (proctors.isEmpty ? 1 : 2));
```

#### Step 22.4.3: Implement ProctorEntryScreen

Replace the stub at lines 1089-1096. Opens hub at proctor section (index 1):

```dart
class ProctorEntryScreen extends StatelessWidget {
  final String responseId;

  const ProctorEntryScreen({super.key, required this.responseId});

  @override
  // WHY: Proctor Entry jumps directly to the proctor section.
  Widget build(BuildContext context) => MdotHubScreen(
    responseId: responseId,
    initialSection: 1,
  );
}
```

#### Step 22.4.4: Implement WeightsEntryScreen

Replace the stub at lines 1098-1105. Opens hub at proctor section (index 1) since weights are part of the proctor workflow:

```dart
class WeightsEntryScreen extends StatelessWidget {
  final String responseId;

  const WeightsEntryScreen({super.key, required this.responseId});

  @override
  // WHY: Weights entry is part of the proctor workflow (section 1).
  // The weight readings input is inside HubProctorContent.
  Widget build(BuildContext context) => MdotHubScreen(
    responseId: responseId,
    initialSection: 1,
  );
}
```

#### Step 22.4.5: Write tests

Create `test/features/forms/presentation/screens/form_sub_screens_test.dart`:
- `FormFillScreen` renders `MdotHubScreen` with no `initialSection`
- `QuickTestEntryScreen` renders `MdotHubScreen` with `initialSection: 2`
- `ProctorEntryScreen` renders `MdotHubScreen` with `initialSection: 1`
- `WeightsEntryScreen` renders `MdotHubScreen` with `initialSection: 1`

#### Step 22.4.6: Verify

Run: `pwsh -Command "flutter test test/features/forms/presentation/screens/"`

### Sub-phase 22.5: FCM Foreground Messages Trigger Sync (L8)

**Files:**
- Modify: `lib/features/sync/application/fcm_handler.dart`
- Test: `test/features/sync/application/fcm_handler_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 22.5.1: Add SyncOrchestrator dependency to FcmHandler

In `lib/features/sync/application/fcm_handler.dart`, modify the class:

1. Add import for `SyncOrchestrator`:

```dart
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
```

2. Add field and constructor parameter:

```dart
class FcmHandler {
  final AuthService? _authService;
  final SyncOrchestrator? _syncOrchestrator;
  bool _isInitialized = false;
  // SECURITY FIX: Rate-limit field to prevent FCM DoS
  DateTime? _lastFcmSyncTrigger;

  FcmHandler({AuthService? authService, SyncOrchestrator? syncOrchestrator})
      : _authService = authService,
        _syncOrchestrator = syncOrchestrator;
```

3. Replace the foreground handler (lines 72-77):

```dart
      // Handle foreground messages
      FirebaseMessaging.onMessage.listen((message) {
        Logger.sync('FCM foreground message messageId=${message.messageId}');
        final messageType = message.data['type'];
        if (messageType == 'daily_sync') {
          // SECURITY FIX: Rate-limit FCM-triggered syncs to prevent DoS from
          // spoofed or misconfigured FCM messages flooding the device with sync cycles.
          final now = DateTime.now();
          if (_lastFcmSyncTrigger != null &&
              now.difference(_lastFcmSyncTrigger!).inSeconds < 60) {
            Logger.sync('FCM sync trigger throttled (< 60s since last)');
            return;
          }
          _lastFcmSyncTrigger = now;
          Logger.sync('FCM daily sync trigger (foreground) — triggering sync');
          _syncOrchestrator?.syncLocalAgencyProjects();
        }
      });
```

#### Step 22.5.2: Update FcmHandler construction site

Find where `FcmHandler` is constructed (likely in `lib/main.dart` or a service locator) and pass `SyncOrchestrator` to it.

#### Step 22.5.3: Write test

Create `test/features/sync/application/fcm_handler_test.dart`:
- Verify that when a foreground message with `type: 'daily_sync'` arrives, `syncOrchestrator.syncLocalAgencyProjects()` is called
- Verify non-daily_sync messages do not trigger sync

#### Step 22.5.4: Verify

Run: `pwsh -Command "flutter test test/features/sync/application/"`

### Sub-phase 22.6: Surface Circuit Breaker Trips to UI (M4)

**Files:**
- Modify: `lib/features/sync/engine/sync_engine.dart`
- Modify: `lib/features/sync/application/sync_orchestrator.dart`
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart`
- Modify: `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`
- Test: `test/features/sync/engine/sync_engine_circuit_breaker_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 22.6.1: Add callback to SyncEngine

In `lib/features/sync/engine/sync_engine.dart`, add a callback field:

```dart
  /// WHY: Callback invoked when the circuit breaker trips for a record.
  /// Enables SyncOrchestrator to propagate trip events to the UI layer.
  void Function(String tableName, String recordId, int conflictCount)?
      onCircuitBreakerTrip;
```

At line 1650-1652, where the circuit breaker logs, invoke the callback:

```dart
              // WHY: Surface circuit breaker trips to UI via callback chain.
              Logger.sync('CIRCUIT BREAKER: Skipping re-push for ${adapter.tableName}/$recordId '
                  '(conflict count: $conflictCount). Record stuck — check conflict viewer.');
              onCircuitBreakerTrip?.call(adapter.tableName, recordId, conflictCount);
```

#### Step 22.6.2: Propagate through SyncOrchestrator

In `lib/features/sync/application/sync_orchestrator.dart`, add:

```dart
  /// WHY: Callback chain — SyncEngine → SyncOrchestrator → SyncProvider.
  void Function(String tableName, String recordId, int conflictCount)?
      onCircuitBreakerTrip;
```

Where the `SyncEngine` is created/configured, wire the callback:

```dart
  engine.onCircuitBreakerTrip = (tableName, recordId, count) {
    onCircuitBreakerTrip?.call(tableName, recordId, count);
  };
```

#### Step 22.6.3: Surface in SyncProvider

In `lib/features/sync/presentation/providers/sync_provider.dart`, add state:

```dart
  /// Records that are stuck in the circuit breaker (table/recordId pairs).
  final List<({String tableName, String recordId, int conflictCount})>
      _circuitBreakerTrips = [];

  List<({String tableName, String recordId, int conflictCount})>
      get circuitBreakerTrips => List.unmodifiable(_circuitBreakerTrips);
```

Wire the orchestrator callback in the constructor or init:

```dart
    _syncOrchestrator.onCircuitBreakerTrip = (tableName, recordId, count) {
      _circuitBreakerTrips.add((
        tableName: tableName,
        recordId: recordId,
        conflictCount: count,
      ));
      notifyListeners();
    };
```

Add a method to clear trips:

```dart
  /// Clear circuit breaker trip records after user acknowledges.
  void clearCircuitBreakerTrips() {
    _circuitBreakerTrips.clear();
    notifyListeners();
  }
```

#### Step 22.6.4: Display in SyncDashboard

In `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`, add a section that displays circuit breaker trips when `syncProvider.circuitBreakerTrips.isNotEmpty`:

- Show a warning card with amber background
- List each tripped record: `"[Table] Record stuck (X conflicts)"`
- Add a "Dismiss" button that calls `syncProvider.clearCircuitBreakerTrips()`

#### Step 22.6.5: Write test

Create `test/features/sync/engine/sync_engine_circuit_breaker_test.dart`:
- Verify callback is invoked when conflict count exceeds threshold
- Verify SyncProvider accumulates trip records
- Verify `clearCircuitBreakerTrips` resets list

#### Step 22.6.6: Verify

Run: `pwsh -Command "flutter test test/features/sync/"`

### Sub-phase 22.7: Extract ExtractionMetrics Datasource (M9)

**Files:**
- Create: `lib/features/pdf/data/datasources/local/extraction_metrics_local_datasource.dart`
- Modify: `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart`
- Test: `test/features/pdf/data/datasources/local/extraction_metrics_local_datasource_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 22.7.1: Create the datasource

Create `lib/features/pdf/data/datasources/local/extraction_metrics_local_datasource.dart`:

Read the full `ExtractionMetrics` class at `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart` to understand all raw SQL operations. Extract them into the datasource:

```dart
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// WHY: Moves raw SQL out of ExtractionMetrics service class into a proper
/// datasource following Clean Architecture layering. The service class should
/// call datasource methods, not execute SQL directly.
class ExtractionMetricsLocalDatasource {
  final Database _db;

  ExtractionMetricsLocalDatasource(this._db);

  /// Insert a top-level extraction metrics row.
  Future<void> insertExtractionMetric(Map<String, dynamic> values) async {
    await _db.insert('extraction_metrics', values);
  }

  /// Insert a stage metrics row.
  Future<void> insertStageMetric(Map<String, dynamic> values) async {
    await _db.insert('stage_metrics', values);
  }

  /// Query extraction metrics by extraction ID.
  Future<Map<String, dynamic>?> getByExtractionId(String extractionId) async {
    final results = await _db.query(
      'extraction_metrics',
      where: 'id = ?',
      whereArgs: [extractionId],
    );
    return results.isNotEmpty ? results.first : null;
  }

  /// Query stage metrics for an extraction run.
  Future<List<Map<String, dynamic>>> getStagesForExtraction(String extractionId) async {
    return await _db.query(
      'stage_metrics',
      where: 'extraction_id = ?',
      whereArgs: [extractionId],
    );
  }
}
```

#### Step 22.7.2: Refactor ExtractionMetrics to use datasource

In `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart`:

1. Change constructor to accept `ExtractionMetricsLocalDatasource` instead of `Database`:

```dart
class ExtractionMetrics {
  final ExtractionMetricsLocalDatasource _datasource;

  ExtractionMetrics(this._datasource);
```

2. Replace all `_db.insert(...)` calls with `_datasource.insertExtractionMetric(...)` and `_datasource.insertStageMetric(...)`.

3. Update all construction sites of `ExtractionMetrics` to pass the datasource instead of the raw `Database`. Search for `ExtractionMetrics(` to find them.

#### Step 22.7.3: Write tests

Create `test/features/pdf/data/datasources/local/extraction_metrics_local_datasource_test.dart`:
- `insertExtractionMetric` inserts a row into `extraction_metrics`
- `insertStageMetric` inserts a row into `stage_metrics`
- `getByExtractionId` returns row or null
- `getStagesForExtraction` returns list of stage rows

Use an in-memory SQLite database for testing.

#### Step 22.7.4: Verify

Run: `pwsh -Command "flutter test test/features/pdf/"`

---

## Dispatch Groups

### Group A (Phases 16-17): Entry and Todo Provider Wiring
- Phase 16: Wire DailyEntry filtering/count methods
- Phase 17: Wire Todo filter/query methods + TodosScreen filter chips
- **Agent**: `frontend-flutter-specialist-agent` (primary), `backend-data-layer-agent` (use case)

### Group B (Phases 18-19): Document and Export Provider Wiring
- Phase 18: Wire Document project-level loading
- Phase 19: Wire EntryExport and FormExport history
- **Agent**: `frontend-flutter-specialist-agent`

### Group C (Phases 20-21): Photo and Quantity Provider Wiring
- Phase 20: Wire Photo count/bulk-delete methods
- Phase 21: Wire EntryQuantity bid-item query/bulk-delete methods
- **Agent**: `frontend-flutter-specialist-agent`

### Group D (Phase 22.1-22.3): Miscellaneous Backend Fixes
- Sub-phase 22.1: Driver isSyncing fix
- Sub-phase 22.2: Foreground fraction alert
- Sub-phase 22.3: Sentry setExtra deprecated
- **Agent**: `general-purpose`

### Group E (Phase 22.4): Form Sub-Screen Implementation
- Sub-phase 22.4: Implement 4 form sub-screen stubs
- **Agent**: `frontend-flutter-specialist-agent`

### Group F (Phase 22.5-22.7): Sync and Extraction Fixes
- Sub-phase 22.5: FCM foreground sync trigger
- Sub-phase 22.6: Circuit breaker UI surfacing
- Sub-phase 22.7: ExtractionMetrics datasource extraction
- **Agent**: `backend-supabase-agent` (22.5-22.6), `backend-data-layer-agent` (22.7)

### Dependencies
- Groups A-F are independent and can run in parallel
- Within Phase 16: Sub-phase 16.1 (use case) must complete before 16.2 (provider)
- Within Phase 19: Sub-phases 19.1 and 19.2 are independent
- Within Phase 22: All sub-phases are independent

### Verification (after all groups)

Run: `pwsh -Command "flutter test"`
Run: `pwsh -Command "flutter analyze"`

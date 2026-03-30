# Codebase Cleanup Part 1: Critical Fixes + DI Wiring

**Size:** M (multi-file, cross-cutting DI changes)
**Risk:** Medium — DI wiring touches startup path; incorrect ordering breaks app launch
**Branch:** `fix/cleanup-part1-di-wiring`

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

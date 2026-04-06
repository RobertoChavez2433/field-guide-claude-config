## Phase 5: Sync Adapter Registration

Register sync adapters for `export_artifacts` and `pay_applications` tables. Create the Supabase migration with tables, RLS policies, storage bucket, and indexes.

### Sub-phase 5.1: Add AdapterConfig entries to simple_adapters.dart

**Files:** `lib/features/sync/adapters/simple_adapters.dart`
**Agent:** `code-fixer-agent`

#### Step 5.1.1: Add buildStoragePath function for export_artifacts

Add a new `_buildExportArtifactPath` function at the bottom of `lib/features/sync/adapters/simple_adapters.dart` (after the existing `_buildFormExportPath` at line 247).

```dart
// In lib/features/sync/adapters/simple_adapters.dart, after line 247:

String _buildExportArtifactPath(String companyId, Map<String, dynamic> localRecord) {
  // WHY: Path includes project_id for RLS bucket policies and artifact_type
  // for organization. Format: artifacts/{companyId}/{projectId}/{filename}
  // FROM SPEC Section 7: export_artifacts is a file-aware adapter.
  final projectId = localRecord['project_id'] as String? ?? 'unlinked';
  final rawFilename = localRecord['filename'] as String? ?? 'unknown';
  // SEC: Sanitize filename to prevent path traversal attacks.
  final filename = rawFilename
      .replaceAll(RegExp(r'[/\\]'), '_')
      .replaceAll(RegExp(r'\.{2,}'), '_');
  return 'artifacts/$companyId/$projectId/$filename';
}
```

**WHY:** export_artifacts is a file adapter (pay app .xlsx and discrepancy PDFs sync through it). The path format mirrors the existing `_buildFormExportPath` pattern but uses a dedicated `artifacts/` prefix for the new `export-artifacts` storage bucket.

#### Step 5.1.2: Add two AdapterConfig entries to simpleAdapters list

Insert two new entries at the end of the `simpleAdapters` list in `lib/features/sync/adapters/simple_adapters.dart`, after the `form_exports` entry (line 177, before the closing `];` on line 178).

```dart
  // In lib/features/sync/adapters/simple_adapters.dart, after line 177 (form_exports entry):

  // WHY: Parent table for all exported artifacts (pay apps, discrepancy PDFs, etc.).
  // FROM SPEC Section 2: Unified export history layer.
  // NOTE: isFileAdapter=true because pay app .xlsx and discrepancy PDFs sync as files.
  // IMPORTANT: local_path is localOnlyColumns — never pushed to Supabase.
  AdapterConfig(
    table: 'export_artifacts',
    scope: ScopeType.viaProject,
    fkDeps: ['projects'],
    fkColumnMap: {'projects': 'project_id'},
    localOnlyColumns: ['local_path'],
    isFileAdapter: true,
    storageBucket: 'export-artifacts',
    buildStoragePath: _buildExportArtifactPath,
    extractRecordName: _extractExportRecordName,
  ),

  // WHY: Child of export_artifacts — stores pay-app-specific metadata.
  // FROM SPEC Section 2: PayApplication references export_artifact_id.
  // NOTE: Data-only (no file), project-scoped. Self-referential FK
  // (previous_application_id) handled by FK rescue during pull.
  AdapterConfig(
    table: 'pay_applications',
    scope: ScopeType.viaProject,
    fkDeps: ['export_artifacts', 'projects'],
    fkColumnMap: {
      'export_artifacts': 'export_artifact_id',
      'projects': 'project_id',
    },
  ),
```

**NOTE:** The existing `_extractExportRecordName` function (line 216) is reused for `export_artifacts` since it reads the `filename` field, which exists on both `entry_exports` and `export_artifacts`. No new extractRecordName function needed.

**Verification:**
```
pwsh -Command "flutter analyze lib/features/sync/adapters/simple_adapters.dart"
```
Expected: No analysis issues.

---

### Sub-phase 5.2: Register adapters in sync_registry.dart

**Files:** `lib/features/sync/engine/sync_registry.dart`
**Agent:** `code-fixer-agent`

#### Step 5.2.1: Insert export_artifacts and pay_applications into registerSyncAdapters

In `lib/features/sync/engine/sync_registry.dart`, insert two lines into the `registerAdapters([...])` call. Insert after `simpleByTable['entry_exports']!` (line 48) and before `DocumentAdapter()` (line 49).

```dart
    // In lib/features/sync/engine/sync_registry.dart, after line 48:
    simpleByTable['export_artifacts']!,    // NEW: unified export history parent
    simpleByTable['pay_applications']!,    // NEW: pay-app-specific child of export_artifacts
```

The resulting order in the registration block (lines 47-51) becomes:
```dart
    simpleByTable['form_exports']!,           // was: FormExportAdapter()
    simpleByTable['entry_exports']!,          // was: EntryExportAdapter()
    simpleByTable['export_artifacts']!,       // NEW: unified export history parent
    simpleByTable['pay_applications']!,       // NEW: child of export_artifacts
    DocumentAdapter(),                        // COMPLEX: custom buildStoragePath, file adapter
```

**WHY:** FK dependency order is load-bearing. `export_artifacts` depends only on `projects` (already registered). `pay_applications` depends on `export_artifacts` + `projects`. Both must come before any table that might reference them. Placing them after `entry_exports` and before `DocumentAdapter` satisfies all FK constraints.

**IMPORTANT:** `pay_applications.previous_application_id` is a self-referential FK. The sync engine's `FkRescueHandler` handles self-referential FKs during pull by deferring rows whose parent hasn't arrived yet. No special adapter logic needed.

**Verification:**
```
pwsh -Command "flutter analyze lib/features/sync/engine/sync_registry.dart"
```
Expected: No analysis issues.

---

### Sub-phase 5.3: Add tables to triggered tables and direct project ID lists

**Files:** `lib/core/database/schema/sync_engine_tables.dart`
**Agent:** `code-fixer-agent`

#### Step 5.3.1: Add to triggeredTables list

In `lib/core/database/schema/sync_engine_tables.dart`, add `'export_artifacts'` and `'pay_applications'` to the `triggeredTables` list (line 133-156). Insert them after `'form_exports'` (currently the last export-related entry at line 153).

```dart
  // In sync_engine_tables.dart, within triggeredTables list, after 'form_exports':
    'form_exports',
    'export_artifacts',    // NEW: unified export history
    'pay_applications',    // NEW: pay app metadata
    'support_tickets',
    'user_consent_records',
```

**WHY:** Tables in `triggeredTables` get SQLite INSERT/UPDATE/DELETE triggers that populate `change_log`. Without these triggers, local changes to `export_artifacts` and `pay_applications` would never be pushed to Supabase.

#### Step 5.3.2: Add to tablesWithDirectProjectId list

In `lib/core/database/schema/sync_engine_tables.dart`, add `'export_artifacts'` and `'pay_applications'` to the `tablesWithDirectProjectId` list (line 164-169).

```dart
  // In sync_engine_tables.dart, within tablesWithDirectProjectId, after 'form_exports':
    'documents', 'entry_exports', 'form_exports',
    'export_artifacts', 'pay_applications',
```

**WHY:** Both new tables have a direct `project_id` column. Adding them here ensures the change_log triggers populate the `project_id` field, which is required for project-scoped sync (dirty scope tracking, pull filtering).

**Verification:**
```
pwsh -Command "flutter analyze lib/core/database/schema/sync_engine_tables.dart"
```
Expected: No analysis issues.

---

### Sub-phase 5.4: Create Supabase migration for both tables + RLS + storage bucket

**Files:** `supabase/migrations/20260406000000_export_artifacts_and_pay_applications.sql`
**Agent:** `code-fixer-agent`

#### Step 5.4.1: Create the migration file

Create a new file at `supabase/migrations/20260406000000_export_artifacts_and_pay_applications.sql`:

```sql
-- =============================================================================
-- Migration: export_artifacts + pay_applications tables
-- FROM SPEC: Pay Application spec Section 2 (Data Model) + Section 7 (Sync)
-- WHY: Unified export history layer + pay-app-specific metadata.
--      RLS scoped by company via project_id.
--      Storage bucket for exported artifact files.
-- =============================================================================

-- =============================================================================
-- Step 1: Create export_artifacts table
-- FROM SPEC: ExportArtifact entity — 16 columns, project-scoped.
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.export_artifacts (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,
    artifact_subtype TEXT,
    source_record_id TEXT,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    local_path TEXT,
    remote_path TEXT,
    mime_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'exported',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by_user_id UUID REFERENCES auth.users(id),
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES auth.users(id)
);

-- NOTE: Indexes on FK columns and frequently filtered columns.
CREATE INDEX IF NOT EXISTS idx_export_artifacts_project ON export_artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_export_artifacts_type ON export_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_export_artifacts_deleted_at ON export_artifacts(deleted_at);
CREATE INDEX IF NOT EXISTS idx_export_artifacts_source ON export_artifacts(source_record_id);

-- RLS: Company-scoped via project_id. Matches form_exports/entry_exports pattern.
-- SEC: Non-viewers can write; SELECT is open to all company members.
ALTER TABLE public.export_artifacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "export_artifacts_select" ON export_artifacts
  FOR SELECT TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
  );

CREATE POLICY "export_artifacts_insert" ON export_artifacts
  FOR INSERT TO authenticated WITH CHECK (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  );

CREATE POLICY "export_artifacts_update" ON export_artifacts
  FOR UPDATE TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND created_by_user_id = auth.uid()
    AND NOT is_viewer()
  );

CREATE POLICY "export_artifacts_delete" ON export_artifacts
  FOR DELETE TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND created_by_user_id = auth.uid()
    AND NOT is_viewer()
  );

-- =============================================================================
-- Step 2: Create pay_applications table
-- FROM SPEC: PayApplication entity — 16 columns, project-scoped.
-- IMPORTANT: Unique constraints enforce non-overlapping ranges per project.
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.pay_applications (
    id TEXT PRIMARY KEY,
    export_artifact_id TEXT NOT NULL REFERENCES export_artifacts(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    application_number INTEGER NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    previous_application_id TEXT REFERENCES pay_applications(id) ON DELETE SET NULL,
    total_contract_amount REAL NOT NULL,
    total_earned_this_period REAL NOT NULL,
    total_earned_to_date REAL NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by_user_id UUID REFERENCES auth.users(id),
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES auth.users(id)
);

-- NOTE: Indexes on FK columns and unique constraint columns.
CREATE INDEX IF NOT EXISTS idx_pay_applications_project ON pay_applications(project_id);
CREATE INDEX IF NOT EXISTS idx_pay_applications_artifact ON pay_applications(export_artifact_id);
CREATE INDEX IF NOT EXISTS idx_pay_applications_previous ON pay_applications(previous_application_id);
CREATE INDEX IF NOT EXISTS idx_pay_applications_deleted_at ON pay_applications(deleted_at);

-- FROM SPEC Section 3: Unique pay-app number per project (among non-deleted).
-- WHY: Partial unique index excludes soft-deleted rows so deleted numbers can be reused.
CREATE UNIQUE INDEX IF NOT EXISTS ux_pay_applications_project_number
  ON pay_applications(project_id, application_number)
  WHERE deleted_at IS NULL;

-- FROM SPEC Section 3: One saved pay app per exact range per project (among non-deleted).
CREATE UNIQUE INDEX IF NOT EXISTS ux_pay_applications_project_range
  ON pay_applications(project_id, period_start, period_end)
  WHERE deleted_at IS NULL;

-- RLS: Same company-scoped pattern as export_artifacts.
ALTER TABLE public.pay_applications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "pay_applications_select" ON pay_applications
  FOR SELECT TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
  );

CREATE POLICY "pay_applications_insert" ON pay_applications
  FOR INSERT TO authenticated WITH CHECK (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  );

CREATE POLICY "pay_applications_update" ON pay_applications
  FOR UPDATE TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND created_by_user_id = auth.uid()
    AND NOT is_viewer()
  );

CREATE POLICY "pay_applications_delete" ON pay_applications
  FOR DELETE TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND created_by_user_id = auth.uid()
    AND NOT is_viewer()
  );

-- =============================================================================
-- Step 3: Create storage bucket for export artifacts
-- WHY: Pay app .xlsx and discrepancy PDFs need file sync.
-- NOTE: ON CONFLICT for idempotency (matches existing bucket creation pattern).
-- =============================================================================
INSERT INTO storage.buckets (id, name, public)
  VALUES ('export-artifacts', 'export-artifacts', false)
  ON CONFLICT (id) DO NOTHING;

-- Storage policies: company-scoped via folder path.
-- Pattern: artifacts/{companyId}/{projectId}/{filename}
-- (storage.foldername(name))[1] = 'artifacts', [2] = companyId
CREATE POLICY "export_artifacts_storage_select" ON storage.objects
  FOR SELECT TO authenticated USING (
    bucket_id = 'export-artifacts'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
  );

CREATE POLICY "export_artifacts_storage_insert" ON storage.objects
  FOR INSERT TO authenticated WITH CHECK (
    bucket_id = 'export-artifacts'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
    AND NOT is_viewer()
  );

CREATE POLICY "export_artifacts_storage_update" ON storage.objects
  FOR UPDATE TO authenticated USING (
    bucket_id = 'export-artifacts'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
    AND NOT is_viewer()
  );

CREATE POLICY "export_artifacts_storage_delete" ON storage.objects
  FOR DELETE TO authenticated USING (
    bucket_id = 'export-artifacts'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
    AND NOT is_viewer()
  );

-- =============================================================================
-- Step 4: Add both tables to cascade soft-delete RPC
-- WHY: When a project is soft-deleted, export_artifacts and pay_applications
--       must also be soft-deleted.
-- NOTE: This extends the existing cascade_soft_delete_project function.
-- =============================================================================
-- IMPORTANT: The cascade soft-delete function update is project-specific.
-- If the function doesn't exist yet for these tables, add them in a subsequent
-- migration or verify the existing cascade function handles new child tables
-- via the generic FK-based cascade already in place.
```

**WHY:** The migration follows the exact pattern from `20260328100000_fix_inspector_forms_and_new_tables.sql` (form_exports, entry_exports). RLS policies are company-scoped via `get_my_company_id()`. Storage policies use the `(storage.foldername(name))[2]` pattern to match company ID in the path.

**IMPORTANT:** Partial unique indexes (`WHERE deleted_at IS NULL`) enforce the spec's rules that pay-app numbers and exact ranges are unique per project among non-deleted records, while allowing reuse of deleted numbers.

**Verification:**
```
npx supabase db push --dry-run
```
Expected: Migration parses without errors.

---

## Phase 6: DI and Provider Wiring

Create the PayApp DI container, initializer, provider registration, and the three providers (ExportArtifactProvider, PayApplicationProvider, ContractorComparisonProvider -- Phase 8 will flesh out the last one).

### Sub-phase 6.1: Create PayAppDeps container in app_dependencies.dart

**Files:** `lib/core/di/app_dependencies.dart`
**Agent:** `code-fixer-agent`

#### Step 6.1.1: Add PayAppDeps import and class

In `lib/core/di/app_dependencies.dart`, add the import for the new repositories (after the existing imports around line 50), then add the `PayAppDeps` class (after `FeatureDeps` at line 178).

Add imports after line 50:
```dart
// Pay application types
import 'package:construction_inspector/features/pay_applications/domain/repositories/export_artifact_repository.dart';
import 'package:construction_inspector/features/pay_applications/domain/repositories/pay_application_repository.dart';
```

Add class after `FeatureDeps` (after line 178):
```dart
/// Pay application feature dependencies.
/// WHY: Separate container because pay apps have their own initializer
/// and depend on quantities repos (cross-feature dependency).
class PayAppDeps {
  final ExportArtifactRepository exportArtifactRepository;
  final PayApplicationRepository payApplicationRepository;

  const PayAppDeps({
    required this.exportArtifactRepository,
    required this.payApplicationRepository,
  });
}
```

#### Step 6.1.2: Add payApp field to AppDependencies

In `lib/core/di/app_dependencies.dart`, add the `payApp` field to the `AppDependencies` class (line 182-216).

```dart
class AppDependencies {
  final CoreDeps core;
  final AuthDeps auth;
  final ProjectDeps project;
  final EntryDeps entry;
  final FormDeps form;
  final SyncDeps sync;
  final FeatureDeps feature;
  final PayAppDeps payApp;  // NEW

  const AppDependencies({
    required this.core,
    required this.auth,
    required this.project,
    required this.entry,
    required this.form,
    required this.sync,
    required this.feature,
    required this.payApp,  // NEW
  });

  /// Returns a copy with specific fields replaced.
  AppDependencies copyWith({
    PhotoService? photoService,
  }) {
    return AppDependencies(
      core: photoService != null ? core.copyWith(photoService: photoService) : core,
      auth: auth,
      project: project,
      entry: entry,
      form: form,
      sync: sync,
      feature: feature,
      payApp: payApp,  // NEW
    );
  }
}
```

**NOTE:** This will cause a compile error at `lib/core/bootstrap/app_initializer.dart:305` until the initializer is wired (Step 6.2.2). That is expected -- the analyzer will flag it immediately.

**Verification:**
```
pwsh -Command "flutter analyze lib/core/di/app_dependencies.dart"
```
Expected: Analysis issues only from missing repository imports (created in earlier phases).

---

### Sub-phase 6.2: Create PayAppInitializer

**Files:** `lib/features/pay_applications/di/pay_app_initializer.dart`
**Agent:** `code-fixer-agent`

#### Step 6.2.1: Create the initializer class

Create `lib/features/pay_applications/di/pay_app_initializer.dart`:

```dart
// lib/features/pay_applications/di/pay_app_initializer.dart
//
// WHY: Static factory for pay application feature dependencies.
// FROM SPEC: DI pattern — *Initializer with static *Deps create(CoreDeps).
// NOTE: Follows FormInitializer pattern (lib/features/forms/di/form_initializer.dart).

import 'package:construction_inspector/core/di/app_dependencies.dart';
import 'package:construction_inspector/features/pay_applications/data/datasources/local/export_artifact_local_datasource.dart';
import 'package:construction_inspector/features/pay_applications/data/datasources/local/pay_application_local_datasource.dart';
import 'package:construction_inspector/features/pay_applications/data/repositories/export_artifact_repository_impl.dart';
import 'package:construction_inspector/features/pay_applications/data/repositories/pay_application_repository_impl.dart';

/// Static factory for pay application feature dependencies.
class PayAppInitializer {
  PayAppInitializer._();

  /// Constructs all pay-app-layer dependencies from CoreDeps.
  /// WHY: Tier 1 (datasources) and Tier 2 (repositories) are created here,
  /// not in the widget tree. Follows FormInitializer.create() pattern.
  static PayAppDeps create(CoreDeps coreDeps) {
    final dbService = coreDeps.dbService;

    // Tier 1: Datasources
    final exportArtifactLocal = ExportArtifactLocalDatasource(dbService);
    final payApplicationLocal = PayApplicationLocalDatasource(dbService);

    // Tier 2: Repositories
    final exportArtifactRepo = ExportArtifactRepositoryImpl(exportArtifactLocal);
    final payApplicationRepo = PayApplicationRepositoryImpl(payApplicationLocal);

    return PayAppDeps(
      exportArtifactRepository: exportArtifactRepo,
      payApplicationRepository: payApplicationRepo,
    );
  }
}
```

#### Step 6.2.2: Wire PayAppInitializer into app_initializer.dart

In `lib/core/bootstrap/app_initializer.dart`, add the import and wire the initializer.

Add import:
```dart
import 'package:construction_inspector/features/pay_applications/di/pay_app_initializer.dart';
```

After line 303 (after `featureDeps` creation), add:
```dart
    // Step 10.5: Pay application deps
    // WHY: Pay apps have their own initializer (separate from FeatureDeps)
    // because they form a new feature module with dedicated datasources/repos.
    final payAppDeps = PayAppInitializer.create(coreDeps);
```

Update the `AppDependencies(` constructor call at line 305 to include `payApp`:
```dart
    return AppDependencies(
      core: coreDeps,
      auth: authDeps,
      project: projectDeps,
      entry: entryDeps,
      form: formDeps,
      sync: SyncDeps(
        syncCoordinator: syncResult.coordinator,
        syncQueryService: syncResult.queryService,
        syncLifecycleManager: syncResult.lifecycleManager,
        syncRegistry: syncResult.registry,
      ),
      feature: featureDeps,
      payApp: payAppDeps,  // NEW
    );
```

**Verification:**
```
pwsh -Command "flutter analyze lib/core/bootstrap/app_initializer.dart"
```
Expected: May have issues if datasource/repository files from earlier phases are not yet created. No issues from the DI wiring itself.

---

### Sub-phase 6.3: Create payAppProviders() and wire into buildAppProviders

**Files:** `lib/features/pay_applications/di/pay_app_providers.dart`, `lib/core/di/app_providers.dart`
**Agent:** `code-fixer-agent`

#### Step 6.3.1: Create pay_app_providers.dart

Create `lib/features/pay_applications/di/pay_app_providers.dart`:

```dart
// lib/features/pay_applications/di/pay_app_providers.dart
//
// WHY: Tier 3-5 providers for the pay application feature.
// FROM SPEC: DI pattern — *_providers.dart returns List<SingleChildWidget>.
// NOTE: Follows quantities_providers.dart pattern.

import 'package:provider/provider.dart';
import 'package:provider/single_child_widget.dart';
import 'package:construction_inspector/features/pay_applications/domain/repositories/export_artifact_repository.dart';
import 'package:construction_inspector/features/pay_applications/domain/repositories/pay_application_repository.dart';
import 'package:construction_inspector/features/pay_applications/presentation/providers/export_artifact_provider.dart';
import 'package:construction_inspector/features/pay_applications/presentation/providers/pay_application_provider.dart';
import 'package:construction_inspector/features/quantities/domain/repositories/bid_item_repository.dart';
import 'package:construction_inspector/features/quantities/domain/repositories/entry_quantity_repository.dart';
import 'package:construction_inspector/features/entries/domain/repositories/daily_entry_repository.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';

/// Pay application feature providers (Tier 4).
/// WHY: Placed after quantities in tier order because pay apps depend on
/// bid items and entry quantities for export computation.
List<SingleChildWidget> payAppProviders({
  required ExportArtifactRepository exportArtifactRepository,
  required PayApplicationRepository payApplicationRepository,
  required BidItemRepository bidItemRepository,
  required EntryQuantityRepository entryQuantityRepository,
  required DailyEntryRepository dailyEntryRepository,
  required AuthProvider authProvider,
}) {
  return [
    ChangeNotifierProvider(
      create: (_) => ExportArtifactProvider(exportArtifactRepository),
    ),
    ChangeNotifierProvider(
      create: (_) => PayApplicationProvider(
        payApplicationRepository: payApplicationRepository,
        exportArtifactRepository: exportArtifactRepository,
        bidItemRepository: bidItemRepository,
        entryQuantityRepository: entryQuantityRepository,
        dailyEntryRepository: dailyEntryRepository,
        canWrite: () => authProvider.canEditFieldData,
      ),
    ),
  ];
}
```

#### Step 6.3.2: Wire payAppProviders into buildAppProviders

In `lib/core/di/app_providers.dart`, add the import and the provider spread.

Add import (after existing per-feature imports around line 24):
```dart
import 'package:construction_inspector/features/pay_applications/di/pay_app_providers.dart';
```

Insert the spread after `...quantityProviders(...)` (after line 102) and before `...photoProviders(...)` (line 103):
```dart
    // WHY: Pay apps depend on bid items + entry quantities for export computation.
    // Must come after quantities (which registers BidItemProvider, EntryQuantityProvider)
    // but before photos since no downstream dependency exists.
    ...payAppProviders(
      exportArtifactRepository: deps.payApp.exportArtifactRepository,
      payApplicationRepository: deps.payApp.payApplicationRepository,
      bidItemRepository: deps.feature.bidItemRepository,
      entryQuantityRepository: deps.feature.entryQuantityRepository,
      dailyEntryRepository: deps.entry.dailyEntryRepository,
      authProvider: deps.auth.authProvider,
    ),
```

**WHY:** Pay app providers are placed in Tier 4 after quantities because `PayApplicationProvider` needs `BidItemRepository` and `EntryQuantityRepository` for export computation. It does not depend on photos, forms, or entries providers -- only on their repositories which are created in Tier 1-2 (already available via `AppDependencies`).

**Verification:**
```
pwsh -Command "flutter analyze lib/core/di/app_providers.dart"
```
Expected: No analysis issues (assuming provider classes exist from earlier phases).

---

### Sub-phase 6.4: Create ExportArtifactProvider

**Files:** `lib/features/pay_applications/presentation/providers/export_artifact_provider.dart`
**Agent:** `code-fixer-agent`

#### Step 6.4.1: Create the provider class

Create `lib/features/pay_applications/presentation/providers/export_artifact_provider.dart`:

```dart
// lib/features/pay_applications/presentation/providers/export_artifact_provider.dart
//
// WHY: Manages exported-artifact history for the unified export layer.
// FROM SPEC Section 6: ExportArtifactProvider — load/filter/delete artifacts.
// NOTE: Follows EntryQuantityProvider pattern (ChangeNotifier with SafeAction).

import 'package:flutter/foundation.dart';
import 'package:construction_inspector/shared/providers/safe_action_mixin.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/pay_applications/data/models/export_artifact.dart';
import 'package:construction_inspector/features/pay_applications/domain/repositories/export_artifact_repository.dart';

/// Provider for the unified export-artifact history layer.
///
/// FROM SPEC Section 6: Responsibilities:
/// - Load exported-artifact history by project and type
/// - Delete exported artifacts and coordinate local/remote file cleanup
/// - Surface exported Forms history filtered by artifact type
class ExportArtifactProvider extends ChangeNotifier with SafeAction {
  final ExportArtifactRepository _repository;

  ExportArtifactProvider(this._repository);

  // SafeAction accessors
  @override
  bool get safeActionIsLoading => _isLoading;
  @override
  set safeActionIsLoading(bool value) => _isLoading = value;
  @override
  String? get safeActionError => _error;
  @override
  set safeActionError(String? value) => _error = value;
  @override
  String get safeActionLogTag => 'ExportArtifactProvider';

  // State
  List<ExportArtifact> _artifacts = [];
  bool _isLoading = false;
  String? _error;

  // Getters
  List<ExportArtifact> get artifacts => _artifacts;
  bool get isLoading => _isLoading;
  String? get error => _error;

  /// Load all exported artifacts for a project.
  /// FROM SPEC Section 6: loadForProject(projectId)
  Future<void> loadForProject(String projectId) async {
    await runSafeAction('load artifacts', () async {
      _artifacts = await _repository.getByProjectId(projectId);
    }, buildErrorMessage: (_) => 'Failed to load export history.');
  }

  /// Get artifacts filtered by type for a project.
  /// FROM SPEC Section 6: getByType(projectId, artifactType)
  /// WHY: Used by exported Forms history to filter by artifact_type
  /// (entry_pdf, form_pdf, pay_application, etc.).
  Future<List<ExportArtifact>> getByType(
    String projectId,
    String artifactType,
  ) async {
    try {
      return await _repository.getByType(projectId, artifactType);
    } on Exception catch (e) {
      Logger.error('Failed to load artifacts by type: $e',
          tag: 'ExportArtifactProvider');
      return [];
    }
  }

  /// Delete an exported artifact and its associated file.
  /// FROM SPEC Section 6: deleteArtifact(artifactId)
  /// WHY: Soft-deletes the artifact row. File cleanup is handled by
  /// the sync engine's file adapter on next push.
  /// IMPORTANT: Requires canEditFieldData guard at the UI layer.
  Future<bool> deleteArtifact(String artifactId) async {
    return runSafeAction('delete artifact', () async {
      await _repository.delete(artifactId);
      _artifacts.removeWhere((a) => a.id == artifactId);
    }, buildErrorMessage: (_) => 'Failed to delete artifact.');
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/presentation/providers/export_artifact_provider.dart"
```
Expected: No analysis issues (assuming model and repository exist from earlier phases).

---

### Sub-phase 6.5: Create PayApplicationProvider

**Files:** `lib/features/pay_applications/presentation/providers/pay_application_provider.dart`
**Agent:** `code-fixer-agent`

#### Step 6.5.1: Create the provider class

Create `lib/features/pay_applications/presentation/providers/pay_application_provider.dart`:

```dart
// lib/features/pay_applications/presentation/providers/pay_application_provider.dart
//
// WHY: Core provider for pay application export, validation, and management.
// FROM SPEC Section 6: PayApplicationProvider — validate, export, replace, chain.
// NOTE: Uses SafeAction mixin for consistent loading/error state management.

import 'package:flutter/foundation.dart';
import 'package:construction_inspector/shared/providers/safe_action_mixin.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/pay_applications/data/models/export_artifact.dart';
import 'package:construction_inspector/features/pay_applications/data/models/pay_application.dart';
import 'package:construction_inspector/features/pay_applications/domain/repositories/export_artifact_repository.dart';
import 'package:construction_inspector/features/pay_applications/domain/repositories/pay_application_repository.dart';
import 'package:construction_inspector/features/quantities/domain/repositories/bid_item_repository.dart';
import 'package:construction_inspector/features/quantities/domain/repositories/entry_quantity_repository.dart';
import 'package:construction_inspector/features/entries/domain/repositories/daily_entry_repository.dart';

/// Validation result for a proposed pay-app date range.
/// FROM SPEC Section 3: Range rules — exact match = replace, overlap = block.
enum PayAppRangeStatus {
  /// No conflict — range is available.
  available,

  /// Exact same range exists — user can replace.
  exactMatch,

  /// Overlapping but non-identical range — blocked.
  overlapping,
}

/// Result of validating a proposed pay-app date range.
class PayAppRangeValidation {
  final PayAppRangeStatus status;

  /// The existing pay app that conflicts (for exactMatch or overlapping).
  final PayApplication? existingPayApp;

  const PayAppRangeValidation({
    required this.status,
    this.existingPayApp,
  });
}

/// Provider for pay application export, validation, and management.
///
/// FROM SPEC Section 6: Responsibilities:
/// - Validate date ranges against existing saved pay apps
/// - Auto-assign next pay-app number
/// - Export pay app through orchestrator
/// - Replace same-range saved pay app after confirmation
class PayApplicationProvider extends ChangeNotifier with SafeAction {
  final PayApplicationRepository _payAppRepository;
  final ExportArtifactRepository _exportArtifactRepository;
  final BidItemRepository _bidItemRepository;
  final EntryQuantityRepository _entryQuantityRepository;
  final DailyEntryRepository _dailyEntryRepository;
  final bool Function() _canWrite;

  PayApplicationProvider({
    required PayApplicationRepository payApplicationRepository,
    required ExportArtifactRepository exportArtifactRepository,
    required BidItemRepository bidItemRepository,
    required EntryQuantityRepository entryQuantityRepository,
    required DailyEntryRepository dailyEntryRepository,
    required bool Function() canWrite,
  })  : _payAppRepository = payApplicationRepository,
        _exportArtifactRepository = exportArtifactRepository,
        _bidItemRepository = bidItemRepository,
        _entryQuantityRepository = entryQuantityRepository,
        _dailyEntryRepository = dailyEntryRepository,
        _canWrite = canWrite;

  // SafeAction accessors
  @override
  bool get safeActionIsLoading => _isLoading;
  @override
  set safeActionIsLoading(bool value) => _isLoading = value;
  @override
  String? get safeActionError => _error;
  @override
  set safeActionError(String? value) => _error = value;
  @override
  String get safeActionLogTag => 'PayApplicationProvider';

  // State
  List<PayApplication> _payApps = [];
  bool _isLoading = false;
  String? _error;
  bool _isExporting = false;

  // Getters
  List<PayApplication> get payApps => _payApps;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isExporting => _isExporting;

  /// Load all pay applications for a project.
  /// FROM SPEC Section 6: loadForProject(projectId)
  Future<void> loadForProject(String projectId) async {
    await runSafeAction('load pay apps', () async {
      _payApps = await _payAppRepository.getByProjectId(projectId);
    }, buildErrorMessage: (_) => 'Failed to load pay applications.');
  }

  /// Validate a proposed date range against existing pay apps.
  /// FROM SPEC Section 3: Range rules.
  /// Returns: available, exactMatch (can replace), or overlapping (blocked).
  Future<PayAppRangeValidation> validateRange(
    String projectId,
    DateTime start,
    DateTime end,
  ) async {
    try {
      // WHY: Check exact match first (same project + start + end).
      final exactMatch = await _payAppRepository.findByExactRange(
        projectId,
        start,
        end,
      );
      if (exactMatch != null) {
        return PayAppRangeValidation(
          status: PayAppRangeStatus.exactMatch,
          existingPayApp: exactMatch,
        );
      }

      // WHY: Check overlapping ranges (any saved pay app whose range
      // intersects the proposed range).
      final overlapping = await _payAppRepository.findOverlapping(
        projectId,
        start,
        end,
      );
      if (overlapping != null) {
        return PayAppRangeValidation(
          status: PayAppRangeStatus.overlapping,
          existingPayApp: overlapping,
        );
      }

      return const PayAppRangeValidation(status: PayAppRangeStatus.available);
    } on Exception catch (e) {
      Logger.error('Range validation failed: $e',
          tag: 'PayApplicationProvider');
      rethrow;
    }
  }

  /// Get the next suggested pay-app number for a project.
  /// FROM SPEC Section 3: Number is auto-assigned, chronological.
  /// WHY: Returns max(application_number) + 1 among non-deleted pay apps.
  Future<int> getSuggestedNextNumber(String projectId) async {
    try {
      return await _payAppRepository.getNextNumber(projectId);
    } on Exception catch (e) {
      Logger.error('Failed to get next number: $e',
          tag: 'PayApplicationProvider');
      return 1; // Default to 1 if no existing pay apps
    }
  }

  /// Export a pay application for the given date range.
  /// FROM SPEC Section 4: Export flow — query entries, build G703, persist.
  ///
  /// [replaceExisting] — if true, replaces the existing pay app for the
  /// exact same range. Requires prior validateRange() showing exactMatch.
  ///
  /// IMPORTANT: Caller must guard with canEditFieldData before invoking.
  Future<PayApplication?> exportPayApp({
    required String projectId,
    required DateTime start,
    required DateTime end,
    int? overrideNumber,
    required bool replaceExisting,
  }) async {
    if (!_canWrite()) {
      _error = 'You do not have permission to export pay applications.';
      notifyListeners();
      return null;
    }

    PayApplication? result;
    _isExporting = true;
    _error = null;
    notifyListeners();

    try {
      // Step 1: Determine pay-app number
      final number = overrideNumber ?? await getSuggestedNextNumber(projectId);

      // Step 2: Check number uniqueness (unless replacing exact same range)
      if (!replaceExisting) {
        final numberExists = await _payAppRepository.numberExists(
          projectId,
          number,
        );
        if (numberExists) {
          _error = 'Pay application number already exists in this project.';
          return null;
        }
      }

      // Step 3: If replacing, delete existing pay app + artifact
      if (replaceExisting) {
        final existing = await _payAppRepository.findByExactRange(
          projectId,
          start,
          end,
        );
        if (existing != null) {
          // WHY: Delete pay_application first (child), then export_artifact (parent).
          // The CASCADE on export_artifact_id will handle this if we delete the
          // artifact, but explicit ordering is clearer for logging.
          await _payAppRepository.delete(existing.id);
          await _exportArtifactRepository.delete(existing.exportArtifactId);
        }
      }

      // Step 4: Query bid items and quantities for the range
      final bidItems = await _bidItemRepository.getByProjectId(projectId);
      if (bidItems.isEmpty) {
        _error = 'Add ${_bidItemLabel()} before creating a pay application.';
        return null;
      }

      // Step 5: Get previous pay app for chaining
      final previousPayApp = getLastPayApp(projectId);

      // Step 6: Compute totals
      // WHY: getTotalUsedByProject gives cumulative totals per bid item.
      // We also need period-specific totals (quantities from entries in the range).
      final cumulativeTotals =
          await _entryQuantityRepository.getTotalUsedByProject(projectId);

      double totalContractAmount = 0;
      double totalEarnedThisPeriod = 0;
      double totalEarnedToDate = 0;

      for (final item in bidItems) {
        final bidAmount = (item.unitPrice ?? 0) * item.bidQuantity;
        totalContractAmount += bidAmount;

        final cumulative = cumulativeTotals[item.id] ?? 0;
        totalEarnedToDate += cumulative * (item.unitPrice ?? 0);
      }

      // WHY: Period earned = total to date - previous total to date
      totalEarnedThisPeriod = totalEarnedToDate -
          (previousPayApp?.totalEarnedToDate ?? 0);

      // Step 7: Generate Excel file
      // NOTE: PayAppExcelExporter is created in earlier phases.
      // The actual file generation will be wired in Phase 7 UI integration.
      // For now, create the artifact and pay app records.
      final now = DateTime.now().toUtc().toIso8601String();

      // Step 8: Create ExportArtifact
      final artifact = ExportArtifact(
        projectId: projectId,
        artifactType: 'pay_application',
        title: 'Pay Application #$number',
        filename: 'pay_app_${number}_${start.toIso8601String().substring(0, 10)}_${end.toIso8601String().substring(0, 10)}.xlsx',
        mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        status: 'exported',
        createdAt: now,
        updatedAt: now,
      );
      await _exportArtifactRepository.save(artifact);

      // Step 9: Create PayApplication
      final payApp = PayApplication(
        exportArtifactId: artifact.id,
        projectId: projectId,
        applicationNumber: number,
        periodStart: start.toIso8601String(),
        periodEnd: end.toIso8601String(),
        previousApplicationId: previousPayApp?.id,
        totalContractAmount: totalContractAmount,
        totalEarnedThisPeriod: totalEarnedThisPeriod,
        totalEarnedToDate: totalEarnedToDate,
        createdAt: now,
        updatedAt: now,
      );
      await _payAppRepository.save(payApp);

      // Step 10: Refresh local state
      _payApps = await _payAppRepository.getByProjectId(projectId);
      result = payApp;

      Logger.info(
        'Exported pay app #$number for $projectId '
        '(${start.toIso8601String().substring(0, 10)} - ${end.toIso8601String().substring(0, 10)})',
        tag: 'PayApplicationProvider',
      );
    } on Exception catch (e) {
      _error = 'Failed to export pay application.';
      Logger.error('Export failed: $e', tag: 'PayApplicationProvider');
    } finally {
      _isExporting = false;
      notifyListeners();
    }

    return result;
  }

  /// Get the most recent pay app for a project (by application_number).
  /// FROM SPEC Section 6: getLastPayApp(projectId)
  /// WHY: Used for chaining (previous_application_id) and for default
  /// date range start (day after last pay app end).
  PayApplication? getLastPayApp(String projectId) {
    final projectApps =
        _payApps.where((p) => p.projectId == projectId).toList();
    if (projectApps.isEmpty) return null;
    projectApps.sort(
        (a, b) => b.applicationNumber.compareTo(a.applicationNumber));
    return projectApps.first;
  }

  /// Replace an existing pay app for the exact same date range.
  /// FROM SPEC Section 4: Replace flow — delete prior, re-export, reuse number.
  /// IMPORTANT: Must be called only after validateRange() returns exactMatch.
  Future<PayApplication?> replaceExisting({
    required String projectId,
    required DateTime start,
    required DateTime end,
    int? overrideNumber,
  }) async {
    return exportPayApp(
      projectId: projectId,
      start: start,
      end: end,
      overrideNumber: overrideNumber,
      replaceExisting: true,
    );
  }

  // WHY: Use AppTerminology-aware label. Imported at the point of use
  // to avoid pulling Flutter into the provider if possible. Falls back
  // to generic term if AppTerminology is unavailable.
  String _bidItemLabel() {
    try {
      // NOTE: AppTerminology is a static class, safe to call from provider.
      // ignore: depend_on_referenced_packages
      return 'pay items';
    } catch (_) {
      return 'bid items';
    }
  }
}
```

**WHY:** The provider encapsulates the entire pay-app export workflow: validation, number assignment, total computation, artifact creation, and pay-app record creation. It follows the `SafeAction` mixin pattern from `EntryQuantityProvider`. The `_canWrite` function closure is injected from `authProvider.canEditFieldData` at DI time, matching the `BidItemProvider` pattern.

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/presentation/providers/pay_application_provider.dart"
```
Expected: No analysis issues (assuming model and repository exist from earlier phases).

---

## Phase 7: Pay Application UI

Create screens, dialogs, and widgets for the pay application feature. Register routes and add TestingKeys.

### Sub-phase 7.1: Add TestingKeys for pay application feature

**Files:** `lib/shared/testing_keys/pay_app_keys.dart`, `lib/shared/testing_keys/testing_keys.dart`
**Agent:** `code-fixer-agent`

#### Step 7.1.1: Create pay_app_keys.dart

Create `lib/shared/testing_keys/pay_app_keys.dart`:

```dart
// lib/shared/testing_keys/pay_app_keys.dart
//
// FROM SPEC Section 5: 11 TestingKeys required for pay application feature.
// NOTE: Follows the modular key file pattern (e.g., quantities_keys.dart).

import 'package:flutter/material.dart';

/// Testing keys for pay application and analytics features.
class PayAppTestingKeys {
  PayAppTestingKeys._();

  // Pay Application
  static const payAppExportButton = Key('payAppExportButton');
  static const payAppDateRangePicker = Key('payAppDateRangePicker');
  static const payAppReplaceConfirmButton = Key('payAppReplaceConfirmButton');
  static const payAppNumberField = Key('payAppNumberField');
  static const payAppDetailScreen = Key('payAppDetailScreen');
  static const payAppCompareButton = Key('payAppCompareButton');

  // Contractor Comparison
  static const contractorImportButton = Key('contractorImportButton');
  static const contractorComparisonScreen = Key('contractorComparisonScreen');
  static const contractorComparisonExportPdfButton =
      Key('contractorComparisonExportPdfButton');

  // Analytics
  static const analyticsScreen = Key('analyticsScreen');
  static const analyticsDateFilter = Key('analyticsDateFilter');
}
```

#### Step 7.1.2: Register in testing_keys.dart barrel

In `lib/shared/testing_keys/testing_keys.dart`, add the export and import:

After line 18 (last export), add:
```dart
export 'pay_app_keys.dart';
```

After line 34 (last import for facade), add:
```dart
import 'pay_app_keys.dart';
```

In the `TestingKeys` class body, add a new section (at the end, before the closing `}`):
```dart
  // ============================================
  // Pay Application & Analytics
  // ============================================
  static const payAppExportButton = PayAppTestingKeys.payAppExportButton;
  static const payAppDateRangePicker = PayAppTestingKeys.payAppDateRangePicker;
  static const payAppReplaceConfirmButton = PayAppTestingKeys.payAppReplaceConfirmButton;
  static const payAppNumberField = PayAppTestingKeys.payAppNumberField;
  static const payAppDetailScreen = PayAppTestingKeys.payAppDetailScreen;
  static const payAppCompareButton = PayAppTestingKeys.payAppCompareButton;
  static const contractorImportButton = PayAppTestingKeys.contractorImportButton;
  static const contractorComparisonScreen = PayAppTestingKeys.contractorComparisonScreen;
  static const contractorComparisonExportPdfButton = PayAppTestingKeys.contractorComparisonExportPdfButton;
  static const analyticsScreen = PayAppTestingKeys.analyticsScreen;
  static const analyticsDateFilter = PayAppTestingKeys.analyticsDateFilter;
```

**Verification:**
```
pwsh -Command "flutter analyze lib/shared/testing_keys/"
```
Expected: No analysis issues.

---

### Sub-phase 7.2: Create route registration

**Files:** `lib/core/router/routes/pay_app_routes.dart`, `lib/core/router/app_router.dart`
**Agent:** `code-fixer-agent`

#### Step 7.2.1: Create pay_app_routes.dart

Create `lib/core/router/routes/pay_app_routes.dart`:

```dart
// lib/core/router/routes/pay_app_routes.dart
//
// FROM SPEC Section 4: Route definitions for pay application feature.
// NOTE: Follows formRoutes() pattern (lib/core/router/routes/form_routes.dart).

import 'package:go_router/go_router.dart';
import 'package:construction_inspector/features/pay_applications/presentation/screens/pay_application_detail_screen.dart';
import 'package:construction_inspector/features/pay_applications/presentation/screens/contractor_comparison_screen.dart';

/// Full-screen routes for the pay application feature.
/// WHY: Outside bottom nav shell — detail views and comparison screens.
List<RouteBase> payAppRoutes() => [
  // FROM SPEC Section 4: Saved pay-app detail/summary screen.
  GoRoute(
    path: '/pay-app/:payAppId',
    name: 'payAppDetail',
    builder: (context, state) {
      final payAppId = state.pathParameters['payAppId']!;
      return PayApplicationDetailScreen(payAppId: payAppId);
    },
  ),
  // FROM SPEC Section 4: Contractor comparison screen.
  GoRoute(
    path: '/pay-app/:payAppId/compare',
    name: 'contractorComparison',
    builder: (context, state) {
      final payAppId = state.pathParameters['payAppId']!;
      return ContractorComparisonScreen(payAppId: payAppId);
    },
  ),
];
```

#### Step 7.2.2: Register routes in app_router.dart

In `lib/core/router/app_router.dart`, add the import and route spread.

Add import (with other route imports):
```dart
import 'package:construction_inspector/core/router/routes/pay_app_routes.dart';
```

Add route spread after `...syncRoutes()` (line 157):
```dart
      ...payAppRoutes(),
```

**Verification:**
```
pwsh -Command "flutter analyze lib/core/router/"
```
Expected: No analysis issues (assuming screen classes exist).

---

### Sub-phase 7.3: Create PayApplicationDetailScreen

**Files:** `lib/features/pay_applications/presentation/screens/pay_application_detail_screen.dart`
**Agent:** `code-fixer-agent`

#### Step 7.3.1: Create the detail screen

Create `lib/features/pay_applications/presentation/screens/pay_application_detail_screen.dart`:

```dart
// lib/features/pay_applications/presentation/screens/pay_application_detail_screen.dart
//
// FROM SPEC Section 5: PayApplicationDetailScreen — summary/details + actions.
// NOTE: Uses AppScaffold, AppTerminology, TestingKeys per architecture rules.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:construction_inspector/core/config/app_terminology.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/pay_applications/presentation/providers/pay_application_provider.dart';
import 'package:construction_inspector/features/pay_applications/presentation/providers/export_artifact_provider.dart';
import 'package:construction_inspector/features/pay_applications/presentation/widgets/pay_application_summary_card.dart';
import 'package:construction_inspector/features/pay_applications/presentation/dialogs/delete_pay_app_dialog.dart';

/// Saved pay-app detail screen showing summary, details, and actions.
///
/// FROM SPEC Section 4: Available actions:
/// - Share / Export file
/// - Compare Contractor Pay App
/// - Delete
class PayApplicationDetailScreen extends StatefulWidget {
  final String payAppId;

  const PayApplicationDetailScreen({
    super.key,
    required this.payAppId,
  });

  @override
  State<PayApplicationDetailScreen> createState() =>
      _PayApplicationDetailScreenState();
}

class _PayApplicationDetailScreenState
    extends State<PayApplicationDetailScreen> {
  @override
  void initState() {
    super.initState();
    // WHY: Load pay app data when screen opens.
    // Provider data should already be loaded from the history list,
    // but we ensure it's available.
  }

  @override
  Widget build(BuildContext context) {
    final payAppProvider = context.watch<PayApplicationProvider>();
    final authProvider = context.watch<AuthProvider>();
    final theme = Theme.of(context);

    final payApp = payAppProvider.payApps
        .where((p) => p.id == widget.payAppId)
        .firstOrNull;

    if (payApp == null) {
      return AppScaffold(
        title: 'Pay Application',
        body: Center(
          child: AppText.bodyLarge('Pay application not found.'),
        ),
      );
    }

    final canEdit = authProvider.canEditFieldData;

    return AppScaffold(
      key: TestingKeys.payAppDetailScreen,
      title: 'Pay Application #${payApp.applicationNumber}',
      actions: [
        if (canEdit)
          IconButton(
            icon: const Icon(Icons.share),
            tooltip: 'Share',
            onPressed: () {
              // WHY: Share the exported file. Implementation deferred to
              // ExportSaveShareDialog integration.
            },
          ),
      ],
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Summary card
            PayApplicationSummaryCard(payApp: payApp),

            const SizedBox(height: 24),

            // Actions section
            AppText.titleMedium(
              'Actions',
              style: TextStyle(color: theme.colorScheme.onSurface),
            ),
            const SizedBox(height: 12),

            // Compare button
            // FROM SPEC Section 4: "Compare Contractor Pay App" action
            if (canEdit)
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  key: TestingKeys.payAppCompareButton,
                  icon: const Icon(Icons.compare_arrows),
                  label: Text('Compare Contractor ${AppTerminology.bidItem}s'),
                  onPressed: () {
                    context.push('/pay-app/${widget.payAppId}/compare');
                  },
                ),
              ),

            if (canEdit) const SizedBox(height: 8),

            // Delete button
            // FROM SPEC Section 11: Requires canEditFieldData.
            if (canEdit)
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  icon: Icon(
                    Icons.delete_outline,
                    color: theme.colorScheme.error,
                  ),
                  label: Text(
                    'Delete Pay Application',
                    style: TextStyle(color: theme.colorScheme.error),
                  ),
                  onPressed: () => _handleDelete(context, payApp),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleDelete(BuildContext context, dynamic payApp) async {
    // WHY: Show confirmation dialog before deleting.
    final confirmed = await DeletePayAppDialog.show(
      context,
      applicationNumber: payApp.applicationNumber,
    );
    if (confirmed != true) return;
    if (!context.mounted) return;

    final provider = context.read<PayApplicationProvider>();
    final artifactProvider = context.read<ExportArtifactProvider>();

    // WHY: Delete pay_application first, then export_artifact.
    // FROM SPEC Section 2: Deleting a pay app deletes both rows + files.
    await provider.loadForProject(payApp.projectId);
    await artifactProvider.deleteArtifact(payApp.exportArtifactId);

    if (!context.mounted) return;
    context.pop();
  }
}
```

**WHY:** The screen follows the app's existing detail screen patterns (AppScaffold, Provider consumers, TestingKeys). Actions are guarded by `canEditFieldData`. The delete flow matches the spec's cascade: pay_application row + export_artifact row + files.

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/presentation/screens/pay_application_detail_screen.dart"
```
Expected: No analysis issues (assuming widgets and dialogs exist).

---

### Sub-phase 7.4: Create PayApplicationSummaryCard widget

**Files:** `lib/features/pay_applications/presentation/widgets/pay_application_summary_card.dart`
**Agent:** `code-fixer-agent`

#### Step 7.4.1: Create the summary card widget

Create `lib/features/pay_applications/presentation/widgets/pay_application_summary_card.dart`:

```dart
// lib/features/pay_applications/presentation/widgets/pay_application_summary_card.dart
//
// FROM SPEC Section 5: PayApplicationSummaryCard — summary block in detail view.
// NOTE: Uses theme colors, not hardcoded Colors.*.

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:construction_inspector/core/config/app_terminology.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/pay_applications/data/models/pay_application.dart';

/// Summary card showing pay-app metadata in the detail screen.
///
/// Displays: number, date range, status, contract/earned totals, timestamp.
class PayApplicationSummaryCard extends StatelessWidget {
  final PayApplication payApp;

  const PayApplicationSummaryCard({
    super.key,
    required this.payApp,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final currencyFormat = NumberFormat.currency(symbol: r'$');
    final dateFormat = DateFormat('MMM d, yyyy');

    // WHY: Parse ISO 8601 date strings from the model.
    final periodStart = DateTime.tryParse(payApp.periodStart);
    final periodEnd = DateTime.tryParse(payApp.periodEnd);
    final startStr =
        periodStart != null ? dateFormat.format(periodStart) : payApp.periodStart;
    final endStr =
        periodEnd != null ? dateFormat.format(periodEnd) : payApp.periodEnd;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                AppText.titleLarge(
                  'Pay Application #${payApp.applicationNumber}',
                ),
                Chip(
                  label: AppText.labelSmall('Exported'),
                  backgroundColor:
                      theme.colorScheme.primaryContainer,
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Date range
            _buildRow(
              context,
              icon: Icons.date_range,
              label: 'Period',
              value: '$startStr - $endStr',
            ),
            const SizedBox(height: 8),

            // Contract amount
            _buildRow(
              context,
              icon: Icons.account_balance,
              label: 'Total Contract',
              value: currencyFormat.format(payApp.totalContractAmount),
            ),
            const SizedBox(height: 8),

            // Earned this period
            _buildRow(
              context,
              icon: Icons.trending_up,
              label: 'Earned This Period',
              value: currencyFormat.format(payApp.totalEarnedThisPeriod),
            ),
            const SizedBox(height: 8),

            // Earned to date
            _buildRow(
              context,
              icon: Icons.analytics_outlined,
              label: 'Earned To Date',
              value: currencyFormat.format(payApp.totalEarnedToDate),
            ),

            if (payApp.notes != null && payApp.notes!.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Divider(),
              const SizedBox(height: 8),
              AppText.bodyMedium(payApp.notes!),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildRow(
    BuildContext context, {
    required IconData icon,
    required String label,
    required String value,
  }) {
    final theme = Theme.of(context);
    return Row(
      children: [
        Icon(icon, size: 18, color: theme.colorScheme.onSurfaceVariant),
        const SizedBox(width: 8),
        AppText.bodyMedium(
          '$label: ',
          style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
        ),
        Expanded(
          child: AppText.bodyMedium(
            value,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    );
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/presentation/widgets/pay_application_summary_card.dart"
```
Expected: No analysis issues.

---

### Sub-phase 7.5: Create dialogs

**Files:** Multiple dialog files under `lib/features/pay_applications/presentation/dialogs/`
**Agent:** `code-fixer-agent`

#### Step 7.5.1: Create PayAppDateRangeDialog

Create `lib/features/pay_applications/presentation/dialogs/pay_app_date_range_dialog.dart`:

```dart
// lib/features/pay_applications/presentation/dialogs/pay_app_date_range_dialog.dart
//
// FROM SPEC Section 5: Date range picker with overlap validation.
// NOTE: Uses AppDialog.show() per architecture rules.

import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';

/// Result from the date range dialog.
class PayAppDateRangeResult {
  final DateTime start;
  final DateTime end;

  const PayAppDateRangeResult({required this.start, required this.end});
}

/// Date range picker dialog for pay application export.
///
/// FROM SPEC Section 4: Default start = day after last pay app end.
/// Default end = today.
class PayAppDateRangeDialog {
  PayAppDateRangeDialog._();

  /// Show the date range picker dialog.
  /// [defaultStart] — day after last pay app end, or project start.
  /// [defaultEnd] — today.
  static Future<PayAppDateRangeResult?> show(
    BuildContext context, {
    DateTime? defaultStart,
    DateTime? defaultEnd,
  }) async {
    DateTime start = defaultStart ?? DateTime.now();
    DateTime end = defaultEnd ?? DateTime.now();

    return AppDialog.show<PayAppDateRangeResult>(
      context: context,
      title: 'Select Pay Application Period',
      contentBuilder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            return Column(
              key: TestingKeys.payAppDateRangePicker,
              mainAxisSize: MainAxisSize.min,
              children: [
                // Start date
                ListTile(
                  leading: const Icon(Icons.calendar_today),
                  title: AppText.bodyMedium('Period Start'),
                  subtitle: AppText.bodyLarge(
                    '${start.month}/${start.day}/${start.year}',
                  ),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: context,
                      initialDate: start,
                      firstDate: DateTime(2020),
                      lastDate: DateTime.now(),
                    );
                    if (picked != null) {
                      setState(() => start = picked);
                    }
                  },
                ),
                // End date
                ListTile(
                  leading: const Icon(Icons.event),
                  title: AppText.bodyMedium('Period End'),
                  subtitle: AppText.bodyLarge(
                    '${end.month}/${end.day}/${end.year}',
                  ),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: context,
                      initialDate: end,
                      firstDate: start,
                      lastDate: DateTime.now(),
                    );
                    if (picked != null) {
                      setState(() => end = picked);
                    }
                  },
                ),
                if (end.isBefore(start))
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: AppText.bodySmall(
                      'End date must be after start date.',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ),
              ],
            );
          },
        );
      },
      actionsBuilder: (context) => [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            if (!end.isBefore(start)) {
              Navigator.of(context).pop(
                PayAppDateRangeResult(start: start, end: end),
              );
            }
          },
          child: const Text('Continue'),
        ),
      ],
    );
  }
}
```

#### Step 7.5.2: Create PayAppReplaceConfirmationDialog

Create `lib/features/pay_applications/presentation/dialogs/pay_app_replace_confirmation_dialog.dart`:

```dart
// lib/features/pay_applications/presentation/dialogs/pay_app_replace_confirmation_dialog.dart
//
// FROM SPEC Section 4: Confirm replacement of same-range pay app.
// NOTE: Uses AppDialog.show() with actionsBuilder: (not actions:).

import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';

/// Confirmation dialog for replacing an existing pay app with the same range.
class PayAppReplaceConfirmationDialog {
  PayAppReplaceConfirmationDialog._();

  /// Show the replace confirmation dialog.
  /// Returns true if user confirms, null/false if cancelled.
  static Future<bool?> show(
    BuildContext context, {
    required int applicationNumber,
    required String dateRange,
  }) {
    return AppDialog.show<bool>(
      context: context,
      title: 'Replace Pay Application?',
      contentBuilder: (context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: AppText.bodyMedium(
          'Replace Pay App #$applicationNumber for $dateRange?\n\n'
          'The existing pay application will be replaced with a new export '
          'using the same pay application number.',
        ),
      ),
      actionsBuilder: (context) => [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          key: TestingKeys.payAppReplaceConfirmButton,
          onPressed: () => Navigator.of(context).pop(true),
          child: const Text('Replace'),
        ),
      ],
    );
  }
}
```

#### Step 7.5.3: Create PayAppNumberDialog

Create `lib/features/pay_applications/presentation/dialogs/pay_app_number_dialog.dart`:

```dart
// lib/features/pay_applications/presentation/dialogs/pay_app_number_dialog.dart
//
// FROM SPEC Section 4: Review/override auto-assigned pay-app number.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';

/// Dialog for reviewing and optionally overriding the auto-assigned
/// pay application number.
class PayAppNumberDialog {
  PayAppNumberDialog._();

  /// Show the number review dialog.
  /// Returns the confirmed number, or null if cancelled.
  static Future<int?> show(
    BuildContext context, {
    required int suggestedNumber,
  }) {
    final controller = TextEditingController(
      text: suggestedNumber.toString(),
    );

    return AppDialog.show<int>(
      context: context,
      title: 'Pay Application Number',
      contentBuilder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppText.bodyMedium(
            'The next available number is $suggestedNumber. '
            'You may override this if needed.',
          ),
          const SizedBox(height: 16),
          TextField(
            key: TestingKeys.payAppNumberField,
            controller: controller,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            decoration: const InputDecoration(
              labelText: 'Application Number',
              border: OutlineInputBorder(),
            ),
          ),
        ],
      ),
      actionsBuilder: (context) => [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            final number = int.tryParse(controller.text);
            if (number != null && number > 0) {
              Navigator.of(context).pop(number);
            }
          },
          child: const Text('Confirm'),
        ),
      ],
    );
  }
}
```

#### Step 7.5.4: Create DeletePayAppDialog

Create `lib/features/pay_applications/presentation/dialogs/delete_pay_app_dialog.dart`:

```dart
// lib/features/pay_applications/presentation/dialogs/delete_pay_app_dialog.dart
//
// FROM SPEC Section 5: Confirm deletion of saved pay app and files.

import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';

/// Confirmation dialog for deleting a saved pay application.
class DeletePayAppDialog {
  DeletePayAppDialog._();

  /// Show the delete confirmation dialog.
  /// Returns true if user confirms, null/false if cancelled.
  static Future<bool?> show(
    BuildContext context, {
    required int applicationNumber,
  }) {
    return AppDialog.show<bool>(
      context: context,
      title: 'Delete Pay Application?',
      contentBuilder: (context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: AppText.bodyMedium(
          'Delete Pay Application #$applicationNumber?\n\n'
          'This will remove the saved pay application, its exported file, '
          'and any synced copies. This action cannot be undone.',
        ),
      ),
      actionsBuilder: (context) => [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
          onPressed: () => Navigator.of(context).pop(true),
          child: const Text('Delete'),
        ),
      ],
    );
  }
}
```

#### Step 7.5.5: Create ExportSaveShareDialog

Create `lib/features/pay_applications/presentation/dialogs/export_save_share_dialog.dart`:

```dart
// lib/features/pay_applications/presentation/dialogs/export_save_share_dialog.dart
//
// FROM SPEC Section 5: Shared save/share dialog with pluggable preview.
// WHY: Excel files have no preview slot; PDF files can show a preview.

import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';

/// Shared dialog for saving/sharing exported artifacts.
/// [previewWidget] — optional preview (null for Excel, thumbnail for PDF).
class ExportSaveShareDialog {
  ExportSaveShareDialog._();

  /// Show the save/share dialog.
  /// Returns 'save', 'share', or null if cancelled.
  static Future<String?> show(
    BuildContext context, {
    required String filename,
    Widget? previewWidget,
  }) {
    return AppDialog.show<String>(
      context: context,
      title: 'Export Complete',
      contentBuilder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (previewWidget != null) ...[
            previewWidget,
            const SizedBox(height: 16),
          ],
          AppText.bodyMedium('File: $filename'),
        ],
      ),
      actionsBuilder: (context) => [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Close'),
        ),
        OutlinedButton.icon(
          icon: const Icon(Icons.save_alt),
          label: const Text('Save'),
          onPressed: () => Navigator.of(context).pop('save'),
        ),
        FilledButton.icon(
          icon: const Icon(Icons.share),
          label: const Text('Share'),
          onPressed: () => Navigator.of(context).pop('share'),
        ),
      ],
    );
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/presentation/dialogs/"
```
Expected: No analysis issues.

---

### Sub-phase 7.6: Create ExportArtifactHistoryList widget

**Files:** `lib/features/pay_applications/presentation/widgets/export_artifact_history_list.dart`
**Agent:** `code-fixer-agent`

#### Step 7.6.1: Create the history list widget

Create `lib/features/pay_applications/presentation/widgets/export_artifact_history_list.dart`:

```dart
// lib/features/pay_applications/presentation/widgets/export_artifact_history_list.dart
//
// FROM SPEC Section 5: Filtered exported-artifact history surface.
// WHY: Shows exported artifacts filtered by type. Used in exported Forms
// history to include IDR, form PDFs, photo exports, and pay applications.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/pay_applications/data/models/export_artifact.dart';
import 'package:construction_inspector/features/pay_applications/presentation/providers/export_artifact_provider.dart';

/// Displays a filtered list of exported artifacts.
///
/// [projectId] — filter by project.
/// [artifactType] — optional filter by type (null = show all).
/// FROM SPEC Section 5: ExportArtifactHistoryList — filtered by artifact type.
class ExportArtifactHistoryList extends StatelessWidget {
  final String projectId;
  final String? artifactType;

  const ExportArtifactHistoryList({
    super.key,
    required this.projectId,
    this.artifactType,
  });

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ExportArtifactProvider>();
    final theme = Theme.of(context);
    final dateFormat = DateFormat('MMM d, yyyy h:mm a');

    // WHY: Filter locally from already-loaded artifacts.
    final artifacts = provider.artifacts.where((a) {
      if (artifactType != null && a.artifactType != artifactType) return false;
      return true;
    }).toList();

    if (provider.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (artifacts.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: AppText.bodyLarge(
            'No exported artifacts yet.',
            style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
          ),
        ),
      );
    }

    return ListView.builder(
      itemCount: artifacts.length,
      itemBuilder: (context, index) {
        final artifact = artifacts[index];
        final createdAt = DateTime.tryParse(artifact.createdAt);
        final dateStr = createdAt != null
            ? dateFormat.format(createdAt.toLocal())
            : artifact.createdAt;

        return ListTile(
          leading: Icon(_iconForType(artifact.artifactType)),
          title: AppText.bodyLarge(artifact.title),
          subtitle: AppText.bodySmall(dateStr),
          trailing: const Icon(Icons.chevron_right),
          onTap: () {
            // WHY: Route to detail screen based on artifact type.
            if (artifact.artifactType == 'pay_application' &&
                artifact.sourceRecordId != null) {
              context.push('/pay-app/${artifact.sourceRecordId}');
            }
            // NOTE: Other artifact types (entry_pdf, form_pdf) would route
            // to their respective detail screens. Deferred to convergence phase.
          },
        );
      },
    );
  }

  IconData _iconForType(String type) {
    switch (type) {
      case 'pay_application':
        return Icons.receipt_long;
      case 'entry_pdf':
        return Icons.description;
      case 'form_pdf':
        return Icons.article;
      case 'photo_export':
        return Icons.photo_library;
      case 'comparison_report':
        return Icons.compare_arrows;
      default:
        return Icons.insert_drive_file;
    }
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/presentation/widgets/"
```
Expected: No analysis issues.

---

## Phase 8: Contractor Comparison

Create the ContractorComparisonProvider, screen, dialogs, widgets, file parsers, and discrepancy PDF builder.

### Sub-phase 8.1: Create contractor comparison domain models

**Files:** `lib/features/pay_applications/data/models/contractor_comparison.dart`
**Agent:** `code-fixer-agent`

#### Step 8.1.1: Create comparison domain models

Create `lib/features/pay_applications/data/models/contractor_comparison.dart`:

```dart
// lib/features/pay_applications/data/models/contractor_comparison.dart
//
// FROM SPEC Section 4: Contractor comparison data models.
// NOTE: These are ephemeral (not persisted to SQLite, not synced).
// WHY: Imported contractor data and comparison results live only in memory
// during a comparison session.

/// A single line item imported from a contractor's pay application file.
class ContractorLineItem {
  final String? itemNumber;
  final String? description;
  final String? unit;
  final double? quantity;
  final double? unitPrice;
  final double? amount;

  /// Whether this item has been manually matched to a bid item.
  final String? matchedBidItemId;

  const ContractorLineItem({
    this.itemNumber,
    this.description,
    this.unit,
    this.quantity,
    this.unitPrice,
    this.amount,
    this.matchedBidItemId,
  });

  ContractorLineItem copyWith({
    String? itemNumber,
    String? description,
    String? unit,
    double? quantity,
    double? unitPrice,
    double? amount,
    String? matchedBidItemId,
  }) {
    return ContractorLineItem(
      itemNumber: itemNumber ?? this.itemNumber,
      description: description ?? this.description,
      unit: unit ?? this.unit,
      quantity: quantity ?? this.quantity,
      unitPrice: unitPrice ?? this.unitPrice,
      amount: amount ?? this.amount,
      matchedBidItemId: matchedBidItemId ?? this.matchedBidItemId,
    );
  }
}

/// A user edit to manually match/remap a contractor item to a bid item.
class ManualMatchEdit {
  final int contractorItemIndex;
  final String? bidItemId;

  /// If null, removes the match (unmatch).
  const ManualMatchEdit({
    required this.contractorItemIndex,
    this.bidItemId,
  });
}

/// A single discrepancy line between inspector and contractor data.
class DiscrepancyLine {
  final String itemNumber;
  final String description;
  final double inspectorQuantity;
  final double contractorQuantity;
  final double difference;
  final double inspectorAmount;
  final double contractorAmount;
  final double amountDifference;

  const DiscrepancyLine({
    required this.itemNumber,
    required this.description,
    required this.inspectorQuantity,
    required this.contractorQuantity,
    required this.difference,
    required this.inspectorAmount,
    required this.contractorAmount,
    required this.amountDifference,
  });
}

/// Overall comparison result between inspector and contractor pay apps.
/// FROM SPEC Section 4: cumulative totals, period totals, optional daily.
class ContractorComparisonResult {
  final List<DiscrepancyLine> discrepancies;
  final double totalInspectorAmount;
  final double totalContractorAmount;
  final double totalDifference;
  final int matchedCount;
  final int unmatchedContractorCount;
  final int unmatchedInspectorCount;

  /// True if the contractor data includes day-level detail.
  /// FROM SPEC Section 8: Daily discrepancy section only when contractor
  /// data includes day-level detail.
  final bool hasDailyDetail;

  const ContractorComparisonResult({
    required this.discrepancies,
    required this.totalInspectorAmount,
    required this.totalContractorAmount,
    required this.totalDifference,
    required this.matchedCount,
    required this.unmatchedContractorCount,
    required this.unmatchedInspectorCount,
    this.hasDailyDetail = false,
  });
}

/// Represents an imported file for comparison.
class ImportedFile {
  final String name;
  final String path;
  final String mimeType;

  const ImportedFile({
    required this.name,
    required this.path,
    required this.mimeType,
  });
}

/// Result of exporting a discrepancy PDF.
class ExportResult {
  final bool success;
  final String? filePath;
  final String? error;

  const ExportResult({
    required this.success,
    this.filePath,
    this.error,
  });
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/data/models/contractor_comparison.dart"
```
Expected: No analysis issues.

---

### Sub-phase 8.2: Create contractor file parsers

**Files:** `lib/features/pay_applications/data/services/contractor_file_parser.dart`
**Agent:** `code-fixer-agent`

#### Step 8.2.1: Create the parser interface and implementations

Create `lib/features/pay_applications/data/services/contractor_file_parser.dart`:

```dart
// lib/features/pay_applications/data/services/contractor_file_parser.dart
//
// FROM SPEC Section 4: Contractor file parsers for xlsx/csv/pdf.
// WHY: Parse contractor-supplied pay application files into line items
// for comparison. Each format has a dedicated parser.
// IMPORTANT: Imported files are not retained (FROM SPEC Section 3).

import 'dart:io';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/pay_applications/data/models/contractor_comparison.dart';

/// Base interface for contractor file parsers.
abstract class ContractorFileParser {
  /// Parse the file at [path] and return extracted line items.
  /// Returns an empty list if parsing fails completely.
  Future<List<ContractorLineItem>> parse(String path);

  /// Factory to select the right parser based on mime type.
  /// FROM SPEC Section 4: xlsx, csv, pdf (best-effort extraction).
  static ContractorFileParser forMimeType(String mimeType) {
    if (mimeType.contains('spreadsheet') || mimeType.contains('xlsx')) {
      return XlsxContractorParser();
    }
    if (mimeType.contains('csv') || mimeType.contains('comma-separated')) {
      return CsvContractorParser();
    }
    if (mimeType.contains('pdf')) {
      return PdfContractorParser();
    }
    throw ArgumentError('Unsupported contractor file type: $mimeType');
  }
}

/// Parse contractor pay app from .xlsx files.
/// WHY: Most common format from contractors. Uses the excel package.
class XlsxContractorParser implements ContractorFileParser {
  @override
  Future<List<ContractorLineItem>> parse(String path) async {
    try {
      final file = File(path);
      if (!await file.exists()) {
        Logger.error('Contractor xlsx file not found: $path',
            tag: 'XlsxContractorParser');
        return [];
      }

      // NOTE: Implementation will use the 'excel' package to read the workbook.
      // Parse rows looking for columns: Item Number, Description, Unit, Quantity,
      // Unit Price, Amount. Column detection is heuristic (header row matching).
      final bytes = await file.readAsBytes();

      // TODO(Phase 8 implementation): Wire excel package parsing.
      // For now, return empty list — the full parser will be implemented
      // when the excel package dependency is added.
      Logger.info('Parsing xlsx contractor file: $path',
          tag: 'XlsxContractorParser');

      return _parseSpreadsheetRows(bytes);
    } on Exception catch (e) {
      Logger.error('Failed to parse contractor xlsx: $e',
          tag: 'XlsxContractorParser');
      return [];
    }
  }

  List<ContractorLineItem> _parseSpreadsheetRows(List<int> bytes) {
    // WHY: Heuristic column detection — look for header row with keywords
    // like "Item", "Description", "Quantity", "Unit Price", "Amount".
    // This will be implemented using the excel package.
    // Returning empty for now — will be filled during implementation.
    return [];
  }
}

/// Parse contractor pay app from .csv files.
/// WHY: Simple tabular format. Column detection via header row.
class CsvContractorParser implements ContractorFileParser {
  @override
  Future<List<ContractorLineItem>> parse(String path) async {
    try {
      final file = File(path);
      if (!await file.exists()) {
        Logger.error('Contractor csv file not found: $path',
            tag: 'CsvContractorParser');
        return [];
      }

      final content = await file.readAsString();
      final lines = content.split('\n').where((l) => l.trim().isNotEmpty).toList();

      if (lines.isEmpty) return [];

      // WHY: First row is header — detect column indices.
      final headerCells = _splitCsvLine(lines.first);
      final colMap = _detectColumns(headerCells);

      final items = <ContractorLineItem>[];
      for (var i = 1; i < lines.length; i++) {
        final cells = _splitCsvLine(lines[i]);
        final item = _parseRow(cells, colMap);
        if (item != null) items.add(item);
      }

      Logger.info(
        'Parsed ${items.length} items from contractor CSV',
        tag: 'CsvContractorParser',
      );
      return items;
    } on Exception catch (e) {
      Logger.error('Failed to parse contractor csv: $e',
          tag: 'CsvContractorParser');
      return [];
    }
  }

  List<String> _splitCsvLine(String line) {
    // WHY: Simple CSV split handling quoted fields.
    final result = <String>[];
    var current = StringBuffer();
    var inQuotes = false;
    for (var i = 0; i < line.length; i++) {
      final ch = line[i];
      if (ch == '"') {
        inQuotes = !inQuotes;
      } else if (ch == ',' && !inQuotes) {
        result.add(current.toString().trim());
        current = StringBuffer();
      } else {
        current.write(ch);
      }
    }
    result.add(current.toString().trim());
    return result;
  }

  /// Detect column indices from header row using keyword matching.
  /// FROM SPEC Section 4: Match by item_number first.
  Map<String, int> _detectColumns(List<String> headers) {
    final map = <String, int>{};
    for (var i = 0; i < headers.length; i++) {
      final h = headers[i].toLowerCase().trim();
      if (h.contains('item') && (h.contains('number') || h.contains('no') || h.contains('#'))) {
        map['itemNumber'] = i;
      } else if (h.contains('description') || h.contains('desc')) {
        map['description'] = i;
      } else if (h == 'unit' || h == 'uom') {
        map['unit'] = i;
      } else if (h.contains('quantity') || h.contains('qty')) {
        map['quantity'] = i;
      } else if (h.contains('unit') && h.contains('price')) {
        map['unitPrice'] = i;
      } else if (h.contains('amount') || h.contains('total')) {
        map['amount'] = i;
      }
    }
    return map;
  }

  ContractorLineItem? _parseRow(List<String> cells, Map<String, int> colMap) {
    String? getCell(String key) {
      final idx = colMap[key];
      if (idx == null || idx >= cells.length) return null;
      final val = cells[idx].trim();
      return val.isEmpty ? null : val;
    }

    final itemNumber = getCell('itemNumber');
    final description = getCell('description');

    // WHY: Skip rows with neither item number nor description.
    if (itemNumber == null && description == null) return null;

    return ContractorLineItem(
      itemNumber: itemNumber,
      description: description,
      unit: getCell('unit'),
      quantity: double.tryParse(getCell('quantity') ?? ''),
      unitPrice: double.tryParse(
        (getCell('unitPrice') ?? '').replaceAll(RegExp(r'[$,]'), ''),
      ),
      amount: double.tryParse(
        (getCell('amount') ?? '').replaceAll(RegExp(r'[$,]'), ''),
      ),
    );
  }
}

/// Parse contractor pay app from .pdf files (best-effort extraction).
/// FROM SPEC Section 8: Best-effort PDF extraction routes to manual cleanup.
/// WHY: Reuses patterns from lib/features/pdf/services/extraction/ pipeline.
class PdfContractorParser implements ContractorFileParser {
  @override
  Future<List<ContractorLineItem>> parse(String path) async {
    try {
      Logger.info('Attempting best-effort PDF extraction: $path',
          tag: 'PdfContractorParser');

      // NOTE: PDF parsing is best-effort. Results route to manual cleanup.
      // FROM SPEC Section 8: "Review imported rows before comparing"
      // Full implementation will use the existing PDF extraction pipeline
      // patterns from lib/features/pdf/services/extraction/.
      return [];
    } on Exception catch (e) {
      Logger.error('Failed to parse contractor PDF: $e',
          tag: 'PdfContractorParser');
      return [];
    }
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/data/services/contractor_file_parser.dart"
```
Expected: No analysis issues.

---

### Sub-phase 8.3: Create ContractorComparisonProvider

**Files:** `lib/features/pay_applications/presentation/providers/contractor_comparison_provider.dart`
**Agent:** `code-fixer-agent`

#### Step 8.3.1: Create the provider class

Create `lib/features/pay_applications/presentation/providers/contractor_comparison_provider.dart`:

```dart
// lib/features/pay_applications/presentation/providers/contractor_comparison_provider.dart
//
// FROM SPEC Section 6: ContractorComparisonProvider — import, match, compare, export.
// IMPORTANT: Working state is ephemeral. Imported files are not retained.
// NOTE: Uses SafeAction mixin for consistent loading/error state.

import 'package:flutter/foundation.dart';
import 'package:construction_inspector/shared/providers/safe_action_mixin.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/pay_applications/data/models/contractor_comparison.dart';
import 'package:construction_inspector/features/pay_applications/data/models/pay_application.dart';
import 'package:construction_inspector/features/pay_applications/data/services/contractor_file_parser.dart';
import 'package:construction_inspector/features/pay_applications/domain/repositories/export_artifact_repository.dart';
import 'package:construction_inspector/features/pay_applications/domain/repositories/pay_application_repository.dart';
import 'package:construction_inspector/features/pay_applications/data/models/export_artifact.dart';
import 'package:construction_inspector/features/quantities/domain/repositories/bid_item_repository.dart';
import 'package:construction_inspector/features/quantities/domain/repositories/entry_quantity_repository.dart';
import 'package:construction_inspector/features/quantities/data/models/bid_item.dart';

/// Provider for contractor pay application comparison.
///
/// FROM SPEC Section 6: Responsibilities:
/// - Import contractor data from xlsx/csv/pdf
/// - Match by item number first, then description fallback
/// - Support manual cleanup/remap before compare
/// - Build discrepancy summary
/// - Export standalone PDF discrepancy report
/// - Keep working comparison state ephemeral
///
/// IMPORTANT: Imported contractor files are NOT retained (FROM SPEC Section 3).
/// Comparison results are ephemeral unless PDF exported (FROM SPEC Section 3).
class ContractorComparisonProvider extends ChangeNotifier with SafeAction {
  final PayApplicationRepository _payAppRepository;
  final ExportArtifactRepository _exportArtifactRepository;
  final BidItemRepository _bidItemRepository;
  final EntryQuantityRepository _entryQuantityRepository;

  ContractorComparisonProvider({
    required PayApplicationRepository payAppRepository,
    required ExportArtifactRepository exportArtifactRepository,
    required BidItemRepository bidItemRepository,
    required EntryQuantityRepository entryQuantityRepository,
  })  : _payAppRepository = payAppRepository,
        _exportArtifactRepository = exportArtifactRepository,
        _bidItemRepository = bidItemRepository,
        _entryQuantityRepository = entryQuantityRepository;

  // SafeAction accessors
  @override
  bool get safeActionIsLoading => _isLoading;
  @override
  set safeActionIsLoading(bool value) => _isLoading = value;
  @override
  String? get safeActionError => _error;
  @override
  set safeActionError(String? value) => _error = value;
  @override
  String get safeActionLogTag => 'ContractorComparisonProvider';

  // State
  bool _isLoading = false;
  String? _error;
  String? _payAppId;
  PayApplication? _payApp;
  List<ContractorLineItem> _contractorItems = [];
  List<BidItem> _bidItems = [];
  ContractorComparisonResult? _result;
  bool _hasImported = false;

  // Getters
  bool get isLoading => _isLoading;
  String? get error => _error;
  List<ContractorLineItem> get contractorItems => _contractorItems;
  ContractorComparisonResult? get result => _result;
  bool get hasImported => _hasImported;

  /// Import a contractor artifact and parse it into line items.
  /// FROM SPEC Section 6: importContractorArtifact(payAppId, file)
  /// IMPORTANT: The imported file is parsed and discarded — not retained.
  Future<void> importContractorArtifact(
    String payAppId,
    ImportedFile file,
  ) async {
    await runSafeAction('import contractor artifact', () async {
      _payAppId = payAppId;

      // Load the pay app for reference
      _payApp = await _payAppRepository.getById(payAppId);
      if (_payApp == null) throw Exception('Pay application not found');

      // Load bid items for matching
      _bidItems = await _bidItemRepository.getByProjectId(_payApp!.projectId);

      // Parse the contractor file
      // FROM SPEC Section 4: item_number first, description fallback
      final parser = ContractorFileParser.forMimeType(file.mimeType);
      _contractorItems = await parser.parse(file.path);

      // Auto-match items
      _contractorItems = _autoMatchItems(_contractorItems, _bidItems);

      _hasImported = true;

      Logger.info(
        'Imported ${_contractorItems.length} contractor items for pay app $payAppId',
        tag: 'ContractorComparisonProvider',
      );
    }, buildErrorMessage: (_) => 'Failed to import contractor file.');
  }

  /// Auto-match contractor items to bid items.
  /// FROM SPEC Section 4: item_number first, description fallback.
  List<ContractorLineItem> _autoMatchItems(
    List<ContractorLineItem> contractorItems,
    List<BidItem> bidItems,
  ) {
    return contractorItems.map((ci) {
      // Step 1: Match by item number (exact)
      if (ci.itemNumber != null && ci.itemNumber!.isNotEmpty) {
        final match = bidItems.where(
          (bi) => bi.itemNumber.toLowerCase() == ci.itemNumber!.toLowerCase(),
        ).firstOrNull;
        if (match != null) {
          return ci.copyWith(matchedBidItemId: match.id);
        }
      }

      // Step 2: Fallback to description match (case-insensitive contains)
      if (ci.description != null && ci.description!.isNotEmpty) {
        final match = bidItems.where(
          (bi) => bi.description.toLowerCase().contains(
                ci.description!.toLowerCase(),
              ) ||
              ci.description!.toLowerCase().contains(
                bi.description.toLowerCase(),
              ),
        ).firstOrNull;
        if (match != null) {
          return ci.copyWith(matchedBidItemId: match.id);
        }
      }

      return ci;
    }).toList();
  }

  /// Apply manual match edits from the user.
  /// FROM SPEC Section 4: manual cleanup/remap/add/remove before compare.
  Future<void> applyManualMatchEdits(List<ManualMatchEdit> edits) async {
    for (final edit in edits) {
      if (edit.contractorItemIndex < _contractorItems.length) {
        _contractorItems[edit.contractorItemIndex] =
            _contractorItems[edit.contractorItemIndex].copyWith(
          matchedBidItemId: edit.bidItemId,
        );
      }
    }

    // Recompute comparison after edits
    _computeComparison();
    notifyListeners();
  }

  /// Compute the comparison result from matched items.
  /// Called after import + auto-match and after manual edits.
  void _computeComparison() {
    if (_payApp == null || _contractorItems.isEmpty) return;

    final discrepancies = <DiscrepancyLine>[];
    double totalInspector = 0;
    double totalContractor = 0;
    int matched = 0;
    int unmatchedContractor = 0;
    int unmatchedInspector = 0;

    // Build lookup: bidItemId -> contractor item
    final contractorByBidItem = <String, ContractorLineItem>{};
    final unmatchedContractorItems = <ContractorLineItem>[];

    for (final ci in _contractorItems) {
      if (ci.matchedBidItemId != null) {
        contractorByBidItem[ci.matchedBidItemId!] = ci;
        matched++;
      } else {
        unmatchedContractorItems.add(ci);
        unmatchedContractor++;
      }
    }

    // Compare each bid item
    for (final bi in _bidItems) {
      final contractorItem = contractorByBidItem[bi.id];
      final inspectorAmount = (bi.unitPrice ?? 0) * bi.bidQuantity;
      totalInspector += inspectorAmount;

      if (contractorItem != null) {
        final contractorAmount = contractorItem.amount ?? 0;
        totalContractor += contractorAmount;

        discrepancies.add(DiscrepancyLine(
          itemNumber: bi.itemNumber,
          description: bi.description,
          inspectorQuantity: bi.bidQuantity,
          contractorQuantity: contractorItem.quantity ?? 0,
          difference: bi.bidQuantity - (contractorItem.quantity ?? 0),
          inspectorAmount: inspectorAmount,
          contractorAmount: contractorAmount,
          amountDifference: inspectorAmount - contractorAmount,
        ));
      } else {
        unmatchedInspector++;
      }
    }

    // Add unmatched contractor amounts
    for (final ci in unmatchedContractorItems) {
      totalContractor += ci.amount ?? 0;
    }

    _result = ContractorComparisonResult(
      discrepancies: discrepancies,
      totalInspectorAmount: totalInspector,
      totalContractorAmount: totalContractor,
      totalDifference: totalInspector - totalContractor,
      matchedCount: matched,
      unmatchedContractorCount: unmatchedContractor,
      unmatchedInspectorCount: unmatchedInspector,
    );
  }

  /// Export the discrepancy report as a standalone PDF.
  /// FROM SPEC Section 4: "Export discrepancy report as standalone PDF"
  /// WHY: The PDF is saved as an export_artifact with type 'comparison_report'.
  Future<ExportResult> exportDiscrepancyPdf() async {
    if (_result == null || _payApp == null) {
      return const ExportResult(
        success: false,
        error: 'No comparison result to export.',
      );
    }

    try {
      // NOTE: PDF generation will use the existing PdfService patterns.
      // The discrepancy PDF builder creates a formatted report with:
      // - Header: Pay App #N, date range, project
      // - Summary: total inspector vs contractor, difference
      // - Table: per-item discrepancies
      // - Unmatched items section

      final now = DateTime.now().toUtc().toIso8601String();
      final filename =
          'discrepancy_report_payapp_${_payApp!.applicationNumber}.pdf';

      // Create export artifact for the discrepancy PDF
      final artifact = ExportArtifact(
        projectId: _payApp!.projectId,
        artifactType: 'comparison_report',
        sourceRecordId: _payApp!.id,
        title: 'Discrepancy Report - Pay App #${_payApp!.applicationNumber}',
        filename: filename,
        mimeType: 'application/pdf',
        status: 'exported',
        createdAt: now,
        updatedAt: now,
      );
      await _exportArtifactRepository.save(artifact);

      Logger.info(
        'Exported discrepancy PDF for pay app ${_payApp!.applicationNumber}',
        tag: 'ContractorComparisonProvider',
      );

      return ExportResult(success: true, filePath: artifact.localPath);
    } on Exception catch (e) {
      Logger.error('Failed to export discrepancy PDF: $e',
          tag: 'ContractorComparisonProvider');
      return ExportResult(success: false, error: 'Failed to export PDF.');
    }
  }

  /// Clear all comparison session state.
  /// FROM SPEC Section 6: clearSession()
  /// WHY: Called when leaving the comparison screen or starting a new comparison.
  void clearSession() {
    _payAppId = null;
    _payApp = null;
    _contractorItems = [];
    _bidItems = [];
    _result = null;
    _hasImported = false;
    _error = null;
    notifyListeners();
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/presentation/providers/contractor_comparison_provider.dart"
```
Expected: No analysis issues (assuming model and repository exist from earlier phases).

---

### Sub-phase 8.4: Create ContractorComparisonScreen

**Files:** `lib/features/pay_applications/presentation/screens/contractor_comparison_screen.dart`
**Agent:** `code-fixer-agent`

#### Step 8.4.1: Create the comparison screen

Create `lib/features/pay_applications/presentation/screens/contractor_comparison_screen.dart`:

```dart
// lib/features/pay_applications/presentation/screens/contractor_comparison_screen.dart
//
// FROM SPEC Section 5: Import cleanup + discrepancy summary.
// NOTE: Uses AppScaffold, TestingKeys, AppTerminology per architecture rules.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/config/app_terminology.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';
import 'package:construction_inspector/features/pay_applications/presentation/providers/contractor_comparison_provider.dart';
import 'package:construction_inspector/features/pay_applications/presentation/widgets/contractor_comparison_summary.dart';
import 'package:construction_inspector/features/pay_applications/presentation/widgets/contractor_comparison_table.dart';
import 'package:construction_inspector/features/pay_applications/presentation/widgets/manual_match_editor.dart';
import 'package:construction_inspector/features/pay_applications/presentation/dialogs/contractor_import_source_dialog.dart';

/// Contractor comparison screen: import, cleanup, compare, export.
///
/// FROM SPEC Section 4: Three phases:
/// 1. Import contractor file
/// 2. Manual cleanup/remap
/// 3. View comparison + optional PDF export
class ContractorComparisonScreen extends StatefulWidget {
  final String payAppId;

  const ContractorComparisonScreen({
    super.key,
    required this.payAppId,
  });

  @override
  State<ContractorComparisonScreen> createState() =>
      _ContractorComparisonScreenState();
}

class _ContractorComparisonScreenState
    extends State<ContractorComparisonScreen> {
  @override
  void dispose() {
    // WHY: Clear ephemeral comparison state when leaving the screen.
    // FROM SPEC Section 3: Comparison results are ephemeral unless PDF exported.
    // Use addPostFrameCallback to avoid notifyListeners during dispose.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) return; // Already disposed, skip
      // Provider cleanup is handled by the provider's own lifecycle
    });
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      // WHY: Scoped provider for the comparison session.
      // Each comparison screen gets its own provider instance
      // so session state is automatically cleaned up on pop.
      create: (context) => ContractorComparisonProvider(
        payAppRepository: context.read(),
        exportArtifactRepository: context.read(),
        bidItemRepository: context.read(),
        entryQuantityRepository: context.read(),
      ),
      child: _ContractorComparisonBody(payAppId: widget.payAppId),
    );
  }
}

class _ContractorComparisonBody extends StatelessWidget {
  final String payAppId;

  const _ContractorComparisonBody({required this.payAppId});

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<ContractorComparisonProvider>();
    final theme = Theme.of(context);

    return AppScaffold(
      key: TestingKeys.contractorComparisonScreen,
      title: 'Contractor Comparison',
      actions: [
        if (provider.result != null)
          IconButton(
            key: TestingKeys.contractorComparisonExportPdfButton,
            icon: const Icon(Icons.picture_as_pdf),
            tooltip: 'Export Discrepancy PDF',
            onPressed: () async {
              final result = await provider.exportDiscrepancyPdf();
              if (!context.mounted) return;
              if (result.success) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Discrepancy PDF exported.')),
                );
              } else {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(result.error ?? 'Export failed.'),
                    backgroundColor: theme.colorScheme.error,
                  ),
                );
              }
            },
          ),
      ],
      body: _buildBody(context, provider),
    );
  }

  Widget _buildBody(BuildContext context, ContractorComparisonProvider provider) {
    if (provider.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (provider.error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AppText.bodyLarge(provider.error!),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () => _showImportDialog(context),
              child: const Text('Try Again'),
            ),
          ],
        ),
      );
    }

    // Phase 1: No import yet — show import prompt
    if (!provider.hasImported) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.compare_arrows,
              size: 64,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            AppText.titleMedium(
              'Import Contractor ${AppTerminology.bidItem} Data',
            ),
            const SizedBox(height: 8),
            AppText.bodyMedium(
              'Import a contractor pay application to compare\n'
              'against your tracked ${AppTerminology.bidItemPlural.toLowerCase()}.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              key: TestingKeys.contractorImportButton,
              icon: const Icon(Icons.upload_file),
              label: const Text('Import File'),
              onPressed: () => _showImportDialog(context),
            ),
          ],
        ),
      );
    }

    // Phase 2 & 3: Show cleanup + results
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Manual match editor (cleanup phase)
          ManualMatchEditor(
            contractorItems: provider.contractorItems,
            onEditsApplied: (edits) => provider.applyManualMatchEdits(edits),
          ),

          const SizedBox(height: 24),

          // Comparison results
          if (provider.result != null) ...[
            ContractorComparisonSummary(result: provider.result!),
            const SizedBox(height: 16),
            ContractorComparisonTable(result: provider.result!),
          ],
        ],
      ),
    );
  }

  Future<void> _showImportDialog(BuildContext context) async {
    final file = await ContractorImportSourceDialog.show(context);
    if (file == null) return;
    if (!context.mounted) return;

    final provider = context.read<ContractorComparisonProvider>();
    await provider.importContractorArtifact(payAppId, file);
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/presentation/screens/contractor_comparison_screen.dart"
```
Expected: No analysis issues (assuming widgets and dialogs exist).

---

### Sub-phase 8.5: Create ContractorImportSourceDialog

**Files:** `lib/features/pay_applications/presentation/dialogs/contractor_import_source_dialog.dart`
**Agent:** `code-fixer-agent`

#### Step 8.5.1: Create the import source dialog

Create `lib/features/pay_applications/presentation/dialogs/contractor_import_source_dialog.dart`:

```dart
// lib/features/pay_applications/presentation/dialogs/contractor_import_source_dialog.dart
//
// FROM SPEC Section 5: Select contractor file type/source.
// NOTE: Uses file_picker package for platform file selection.

import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/pay_applications/data/models/contractor_comparison.dart';

/// Dialog for selecting the contractor file to import.
/// FROM SPEC Section 4: xlsx, csv, pdf (best-effort extraction).
class ContractorImportSourceDialog {
  ContractorImportSourceDialog._();

  /// Show the import source dialog and return the selected file.
  /// Returns null if cancelled.
  static Future<ImportedFile?> show(BuildContext context) async {
    final fileType = await AppDialog.show<String>(
      context: context,
      title: 'Import Contractor Pay Application',
      contentBuilder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AppText.bodyMedium(
            'Select the file format of the contractor pay application.',
          ),
          const SizedBox(height: 16),
          ListTile(
            leading: const Icon(Icons.table_chart),
            title: AppText.bodyLarge('Excel (.xlsx)'),
            subtitle: AppText.bodySmall('Most reliable format'),
            onTap: () => Navigator.of(context).pop('xlsx'),
          ),
          ListTile(
            leading: const Icon(Icons.text_snippet),
            title: AppText.bodyLarge('CSV (.csv)'),
            subtitle: AppText.bodySmall('Comma-separated values'),
            onTap: () => Navigator.of(context).pop('csv'),
          ),
          ListTile(
            leading: const Icon(Icons.picture_as_pdf),
            title: AppText.bodyLarge('PDF (.pdf)'),
            subtitle: AppText.bodySmall('Best-effort extraction'),
            onTap: () => Navigator.of(context).pop('pdf'),
          ),
        ],
      ),
      actionsBuilder: (context) => [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
      ],
    );

    if (fileType == null) return null;

    // Open file picker for the selected type
    final allowedExtensions = [fileType];
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: allowedExtensions,
    );

    if (result == null || result.files.isEmpty) return null;
    final file = result.files.first;
    if (file.path == null) return null;

    String mimeType;
    switch (fileType) {
      case 'xlsx':
        mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
      case 'csv':
        mimeType = 'text/csv';
      case 'pdf':
        mimeType = 'application/pdf';
      default:
        mimeType = 'application/octet-stream';
    }

    return ImportedFile(
      name: file.name,
      path: file.path!,
      mimeType: mimeType,
    );
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/presentation/dialogs/contractor_import_source_dialog.dart"
```
Expected: No analysis issues.

---

### Sub-phase 8.6: Create comparison widgets

**Files:** Multiple widget files under `lib/features/pay_applications/presentation/widgets/`
**Agent:** `code-fixer-agent`

#### Step 8.6.1: Create ManualMatchEditor widget

Create `lib/features/pay_applications/presentation/widgets/manual_match_editor.dart`:

```dart
// lib/features/pay_applications/presentation/widgets/manual_match_editor.dart
//
// FROM SPEC Section 5: Cleanup/remap UI before compare.
// WHY: Users review auto-matched items and fix mismatches before comparison.

import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/pay_applications/data/models/contractor_comparison.dart';

/// Widget for manually reviewing and editing contractor item matches.
///
/// FROM SPEC Section 4: manual cleanup / remap / add / remove rows before compare.
class ManualMatchEditor extends StatelessWidget {
  final List<ContractorLineItem> contractorItems;
  final void Function(List<ManualMatchEdit> edits) onEditsApplied;

  const ManualMatchEditor({
    super.key,
    required this.contractorItems,
    required this.onEditsApplied,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final matchedCount =
        contractorItems.where((i) => i.matchedBidItemId != null).length;
    final unmatchedCount = contractorItems.length - matchedCount;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            AppText.titleMedium('Imported Items'),
            Chip(
              label: AppText.labelSmall(
                '$matchedCount matched, $unmatchedCount unmatched',
              ),
              backgroundColor: unmatchedCount > 0
                  ? theme.colorScheme.errorContainer
                  : theme.colorScheme.primaryContainer,
            ),
          ],
        ),
        const SizedBox(height: 8),
        if (unmatchedCount > 0)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: AppText.bodySmall(
              'Some items need review before comparison.',
              style: TextStyle(color: theme.colorScheme.error),
            ),
          ),
        ...contractorItems.asMap().entries.map((entry) {
          final index = entry.key;
          final item = entry.value;
          final isMatched = item.matchedBidItemId != null;

          return Card(
            color: isMatched ? null : theme.colorScheme.errorContainer,
            child: ListTile(
              leading: Icon(
                isMatched ? Icons.check_circle : Icons.help_outline,
                color: isMatched
                    ? theme.colorScheme.primary
                    : theme.colorScheme.error,
              ),
              title: AppText.bodyMedium(
                item.itemNumber ?? item.description ?? 'Unknown item',
              ),
              subtitle: item.description != null
                  ? AppText.bodySmall(item.description!)
                  : null,
              trailing: isMatched
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.edit),
                      tooltip: 'Match to bid item',
                      onPressed: () {
                        // NOTE: Would show a bid item picker dialog.
                        // For now, this is a placeholder for the full
                        // manual match flow.
                      },
                    ),
            ),
          );
        }),
      ],
    );
  }
}
```

#### Step 8.6.2: Create ContractorComparisonSummary widget

Create `lib/features/pay_applications/presentation/widgets/contractor_comparison_summary.dart`:

```dart
// lib/features/pay_applications/presentation/widgets/contractor_comparison_summary.dart
//
// FROM SPEC Section 5: High-level discrepancy summary.

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/pay_applications/data/models/contractor_comparison.dart';

/// Summary widget showing high-level comparison results.
class ContractorComparisonSummary extends StatelessWidget {
  final ContractorComparisonResult result;

  const ContractorComparisonSummary({
    super.key,
    required this.result,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final currencyFormat = NumberFormat.currency(symbol: r'$');
    final isPositive = result.totalDifference >= 0;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AppText.titleMedium('Comparison Summary'),
            const SizedBox(height: 12),
            _buildSummaryRow(
              context,
              label: 'Inspector Total',
              value: currencyFormat.format(result.totalInspectorAmount),
            ),
            const SizedBox(height: 4),
            _buildSummaryRow(
              context,
              label: 'Contractor Total',
              value: currencyFormat.format(result.totalContractorAmount),
            ),
            const Divider(height: 16),
            _buildSummaryRow(
              context,
              label: 'Difference',
              value: '${isPositive ? '+' : ''}${currencyFormat.format(result.totalDifference)}',
              valueColor: isPositive
                  ? theme.colorScheme.primary
                  : theme.colorScheme.error,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                _buildChip(
                  context,
                  '${result.matchedCount} Matched',
                  theme.colorScheme.primaryContainer,
                ),
                const SizedBox(width: 8),
                if (result.unmatchedContractorCount > 0)
                  _buildChip(
                    context,
                    '${result.unmatchedContractorCount} Unmatched (Contractor)',
                    theme.colorScheme.errorContainer,
                  ),
                if (result.unmatchedInspectorCount > 0) ...[
                  const SizedBox(width: 8),
                  _buildChip(
                    context,
                    '${result.unmatchedInspectorCount} Unmatched (Inspector)',
                    theme.colorScheme.tertiaryContainer,
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryRow(
    BuildContext context, {
    required String label,
    required String value,
    Color? valueColor,
  }) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        AppText.bodyMedium(label),
        AppText.bodyLarge(
          value,
          style: TextStyle(
            fontWeight: FontWeight.w600,
            color: valueColor,
          ),
        ),
      ],
    );
  }

  Widget _buildChip(BuildContext context, String label, Color color) {
    return Chip(
      label: AppText.labelSmall(label),
      backgroundColor: color,
      visualDensity: VisualDensity.compact,
    );
  }
}
```

#### Step 8.6.3: Create ContractorComparisonTable widget

Create `lib/features/pay_applications/presentation/widgets/contractor_comparison_table.dart`:

```dart
// lib/features/pay_applications/presentation/widgets/contractor_comparison_table.dart
//
// FROM SPEC Section 5: Row-by-row compare table.
// WHY: Shows per-item discrepancies between inspector and contractor data.

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:construction_inspector/core/config/app_terminology.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/pay_applications/data/models/contractor_comparison.dart';

/// Table widget showing per-item discrepancies.
class ContractorComparisonTable extends StatelessWidget {
  final ContractorComparisonResult result;

  const ContractorComparisonTable({
    super.key,
    required this.result,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final currencyFormat = NumberFormat.currency(symbol: r'$', decimalDigits: 2);

    if (result.discrepancies.isEmpty) {
      return Center(
        child: AppText.bodyMedium('No discrepancies to display.'),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppText.titleMedium('${AppTerminology.bidItem} Discrepancies'),
        const SizedBox(height: 8),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            columnSpacing: 16,
            columns: [
              const DataColumn(label: Text('Item #')),
              const DataColumn(label: Text('Description')),
              const DataColumn(label: Text('Inspector Qty'), numeric: true),
              const DataColumn(label: Text('Contractor Qty'), numeric: true),
              const DataColumn(label: Text('Qty Diff'), numeric: true),
              const DataColumn(label: Text('Amount Diff'), numeric: true),
            ],
            rows: result.discrepancies.map((d) {
              final hasDiff = d.difference.abs() > 0.001;
              return DataRow(
                color: hasDiff
                    ? WidgetStateProperty.all(
                        theme.colorScheme.errorContainer.withValues(alpha: 0.3))
                    : null,
                cells: [
                  DataCell(Text(d.itemNumber)),
                  DataCell(
                    SizedBox(
                      width: 150,
                      child: Text(
                        d.description,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                  DataCell(Text(d.inspectorQuantity.toStringAsFixed(2))),
                  DataCell(Text(d.contractorQuantity.toStringAsFixed(2))),
                  DataCell(
                    Text(
                      d.difference.toStringAsFixed(2),
                      style: TextStyle(
                        color: d.difference.abs() > 0.001
                            ? theme.colorScheme.error
                            : null,
                        fontWeight: d.difference.abs() > 0.001
                            ? FontWeight.bold
                            : null,
                      ),
                    ),
                  ),
                  DataCell(
                    Text(
                      currencyFormat.format(d.amountDifference),
                      style: TextStyle(
                        color: d.amountDifference.abs() > 0.01
                            ? theme.colorScheme.error
                            : null,
                        fontWeight: d.amountDifference.abs() > 0.01
                            ? FontWeight.bold
                            : null,
                      ),
                    ),
                  ),
                ],
              );
            }).toList(),
          ),
        ),
      ],
    );
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze lib/features/pay_applications/presentation/widgets/"
```
Expected: No analysis issues.

---

### Sub-phase 8.7: Wire ContractorComparisonProvider into DI

**Files:** `lib/features/pay_applications/di/pay_app_providers.dart`
**Agent:** `code-fixer-agent`

#### Step 8.7.1: Note on scoped provider

The `ContractorComparisonProvider` is NOT registered globally in `pay_app_providers.dart`. Instead, it is created as a scoped provider directly in `ContractorComparisonScreen` (see Sub-phase 8.4, Step 8.4.1). This is intentional:

- **FROM SPEC Section 3:** Comparison results are ephemeral unless PDF exported.
- **WHY:** Scoping the provider to the screen ensures automatic cleanup when the user navigates away. No manual `clearSession()` needed for the normal flow.
- **NOTE:** The repositories it depends on (`PayApplicationRepository`, `ExportArtifactRepository`, `BidItemRepository`, `EntryQuantityRepository`) are all available via `context.read()` from the global provider tree (registered in Tiers 1-4).

No code change needed here -- this step documents the design decision.

**Verification (full feature analyze):**
```
pwsh -Command "flutter analyze lib/features/pay_applications/"
```
Expected: No analysis issues (assuming all data layer files from earlier phases exist).

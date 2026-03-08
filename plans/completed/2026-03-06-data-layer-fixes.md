# Implementation Plan: Data Layer Fixes (REVISED)

**Created**: 2026-03-06
**Revised**: 2026-03-06 (incorporates adversarial review fixes for 7 critical + 5 high issues)
**Status**: READY
**Branch**: `feat/data-layer-fixes` (new branch off `feat/sync-engine-rewrite`)

---

## Executive Summary

Three independent defects in the data layer must be corrected before the sync engine rewrite branch is merged to main.

1. **Sync registry never populated** — The SyncEngine exists but does nothing. `SyncRegistry.registerAdapters()` is never called, so `_registry.dependencyOrder` and `_registry.adapters` are always empty collections. Push/pull loops iterate zero adapters and silently succeed. This is a low-risk fix across 2 files.

2. **Legacy `entry_personnel` table** — A hardcoded three-column table (foreman/operator/laborer) is being replaced by the dynamic `entry_personnel_counts` table. A dual-write bridge is keeping both alive, but the bridge adds write complexity and the old table's presence in `_onCreate` means new installs still create dead weight. A backfill-then-drop migration eliminates this debt.

3. **Permissions UX** — The role system (Admin > Engineer/Inspector > Viewer) is correctly wired at the provider level, but viewer write attempts fail silently (no feedback) and most screens lack a ViewOnly indicator.

**Execution order**: Workstream 1 (sync fix) → Workstream 2 (legacy table, 5 phases) → Workstream 3 (permissions UX).

---

## Adversarial Review Fixes Applied

| # | Issue | Fix |
|---|-------|-----|
| C1 | Backfill SQL used wrong `type_id` values (`'type-foreman'` vs actual `personnel-type-{projectId}-F`) | Rewrote backfill to JOIN `personnel_types` and resolve actual type_ids dynamically |
| C2 | Background sync runs in **separate Dart isolate** — static singletons not shared | Added `registerSyncAdapters()` top-level function; called in both foreground init and background callback |
| C3 | Wrong import path (`../data/registry/`) | Fixed to `../engine/sync_registry.dart` |
| C4 | Wrong file path for `entry_contractors_section.dart` | Fixed to `lib/features/entries/presentation/widgets/` |
| C5 | Wrong file path for `pdf_data_builder.dart` | Fixed to `lib/features/entries/presentation/controllers/` |
| C6 | `entry_editor_screen.dart` missing from WS2 file list | Added to Phase 2.3 and 2.5 |
| C7 | `database_service_test.dart:66` will break after table drop | Added to Phase 2.4 test updates |
| H1 | Backfill didn't filter soft-deleted rows | Added `AND ep.deleted_at IS NULL` to backfill queries |
| H2 | Deactivated/rejected user redirect already exists in router | Removed redundant Task C Fix 2; kept admin redirect improvement only |
| H3 | PDF mapped unknown custom types to "laborer" silently | Changed to resolve types by `personnel_types.short_code`, skip unknown |
| H4 | Not all providers have `_error` field | Added prerequisite check step before applying pattern |
| H5 | No migration test for v32 backfill | Added to test plan |

---

## Workstream Dependency Map

```
WS1 (sync registry fix)         — independent, do first
  └── commits to: sync_orchestrator.dart + background_sync_handler.dart

WS2 (entry_personnel deprecation) — 5 sequential phases, each builds on prior
  Phase 2.1: DB v32 backfill migration
  Phase 2.2: remove display fallbacks
  Phase 2.3: remove backend dual-write + update entry_editor_screen.dart
  Phase 2.4: DB v33 drop table + update tests
  Phase 2.5: code cleanup

WS3 (permissions UX)             — parallelizable across agents
  Task A: provider silent-failure fix (backend-data-layer-agent)
  Task B: ViewOnlyBanner screens  (frontend-flutter-specialist-agent)
  Task C: admin dashboard redirect only (frontend-flutter-specialist-agent)
```

---

## Phase 0: Branch Setup

```bash
git checkout feat/sync-engine-rewrite
git checkout -b feat/data-layer-fixes
```

---

## Workstream 1: Fix Sync Registry (CRITICAL — Sync Does Nothing)

**Agent**: `backend-data-layer-agent`
**Files**: 2 (`sync_orchestrator.dart`, `background_sync_handler.dart`)
**Risk**: LOW — purely additive, no logic changed

### Root Cause

`SyncEngine._push()` (line 254) and `SyncEngine._pull()` (line 631) iterate `_registry.dependencyOrder` / `_registry.adapters`. The registry is populated only by `SyncRegistry.registerAdapters()`, which is never called in production. Both loops iterate zero times. Sync silently succeeds with 0 pushed / 0 pulled.

### Fix A: Create shared registration function

**File**: `lib/features/sync/engine/sync_registry.dart`

Add a top-level function after the class definition:

```dart
/// Register all 16 table adapters in FK dependency order.
/// Called from both foreground (SyncOrchestrator) and background
/// (backgroundSyncCallback) initialization paths.
///
/// Order MUST match SyncEngineTables.triggeredTables.
/// Safe to call multiple times — clears and re-registers.
void registerSyncAdapters() {
  SyncRegistry.instance.registerAdapters([
    ProjectAdapter(),
    LocationAdapter(),
    ContractorAdapter(),
    EquipmentAdapter(),
    BidItemAdapter(),
    PersonnelTypeAdapter(),
    DailyEntryAdapter(),
    PhotoAdapter(),
    EntryEquipmentAdapter(),
    EntryQuantitiesAdapter(),
    EntryContractorsAdapter(),
    EntryPersonnelCountsAdapter(),
    InspectorFormAdapter(),
    FormResponseAdapter(),
    TodoItemAdapter(),
    CalculationHistoryAdapter(),
  ]);
}
```

**Imports to add** (at top of `sync_registry.dart`):

```dart
import '../adapters/project_adapter.dart';
import '../adapters/location_adapter.dart';
import '../adapters/contractor_adapter.dart';
import '../adapters/equipment_adapter.dart';
import '../adapters/bid_item_adapter.dart';
import '../adapters/personnel_type_adapter.dart';
import '../adapters/daily_entry_adapter.dart';
import '../adapters/photo_adapter.dart';
import '../adapters/entry_equipment_adapter.dart';
import '../adapters/entry_quantities_adapter.dart';
import '../adapters/entry_contractors_adapter.dart';
import '../adapters/entry_personnel_counts_adapter.dart';
import '../adapters/inspector_form_adapter.dart';
import '../adapters/form_response_adapter.dart';
import '../adapters/todo_item_adapter.dart';
import '../adapters/calculation_history_adapter.dart';
```

### Fix B: Call from foreground init

**File**: `lib/features/sync/application/sync_orchestrator.dart`

**Location**: Inside `initialize()`, after the mock-adapter block (line 107), before `sync_metadata` query.

```dart
if (!_isMockMode) {
  registerSyncAdapters();
  DebugLogger.sync('SyncOrchestrator: Registered ${SyncRegistry.instance.adapters.length} adapters');
}
```

**Import to add**:
```dart
import '../engine/sync_registry.dart';
```

### Fix C: Call from background sync isolate

**File**: `lib/features/sync/application/background_sync_handler.dart`

**Location**: Inside `backgroundSyncCallback()`, after Supabase init (line 38), before `SyncEngine.createForBackgroundSync()` (line 41).

```dart
// Register adapters in this isolate (isolates don't share static state)
registerSyncAdapters();
```

**Import to add**:
```dart
import '../engine/sync_registry.dart';
```

### First-Sync Considerations

After WS1 is deployed, the first real sync will push all accumulated `change_log` entries. For apps used extensively without sync, this could be thousands of records. The SyncEngine already has batch processing and error handling built in, but monitor logs for timeouts on first sync.

### Verification — WS1

1. `pwsh -Command "flutter analyze"` — 0 issues
2. `pwsh -Command "flutter test test/features/sync/"` — all pass
3. Manual device test: trigger sync from dashboard — push/pull counts > 0 in debug logs
4. Kill app, wait for WorkManager background trigger — background sync logs should also show counts > 0

---

## Workstream 2: Deprecate `entry_personnel` Table

**Total phases**: 5 (strictly sequential)
**Risk**: MEDIUM — involves DB migrations

### Context

The `entry_personnel` table has three hardcoded columns: `foreman_count`, `operator_count`, `laborer_count`. The replacement `entry_personnel_counts` uses dynamic types via `personnel_types` table. A dual-write bridge in `ContractorEditingController` writes to both.

Current DB version: `31` (set in `database_service.dart` line 53 and line 79).

The v3→v4 migration created type IDs with format `personnel-type-{projectId}-{shortCode}` (e.g., `personnel-type-proj123-F`). The backfill in Phase 2.1 must use these actual IDs, not hardcoded strings.

### Phase 2.1 — Safety Backfill (DB v32)

**Agent**: `backend-data-layer-agent`
**Files**:
- `lib/core/database/database_service.dart` — add v32 migration, bump version

**Migration logic** (add inside `_onUpgrade`, after `oldVersion < 31` block):

```dart
if (oldVersion < 32) {
  DebugLogger.db('v32 migration: safety backfill entry_personnel → entry_personnel_counts');

  // Find entry_personnel rows with no equivalent in entry_personnel_counts.
  // Must JOIN personnel_types to resolve actual type_id values (format:
  // 'personnel-type-{projectId}-{shortCode}'), NOT hardcoded strings.
  // Filter out soft-deleted rows (deleted_at IS NOT NULL).
  final orphaned = await db.rawQuery('''
    SELECT ep.*, de.project_id
    FROM entry_personnel ep
    JOIN daily_entries de ON ep.entry_id = de.id
    WHERE ep.deleted_at IS NULL
      AND NOT EXISTS (
        SELECT 1 FROM entry_personnel_counts epc
        WHERE epc.entry_id = ep.entry_id
          AND epc.contractor_id = ep.contractor_id
      )
  ''');

  if (orphaned.isNotEmpty) {
    DebugLogger.db('v32: Found ${orphaned.length} orphaned entry_personnel rows to backfill');
    final now = DateTime.now().toUtc().toIso8601String();

    for (final ep in orphaned) {
      final entryId = ep['entry_id'] as String;
      final contractorId = ep['contractor_id'] as String;
      final projectId = ep['project_id'] as String;
      final foremanCount = ep['foreman_count'] as int? ?? 0;
      final operatorCount = ep['operator_count'] as int? ?? 0;
      final laborerCount = ep['laborer_count'] as int? ?? 0;

      // Look up actual personnel_types for this project
      final types = await db.query(
        'personnel_types',
        columns: ['id', 'short_code'],
        where: 'project_id = ? AND deleted_at IS NULL',
        whereArgs: [projectId],
      );
      final typeByCode = <String, String>{};
      for (final t in types) {
        final code = t['short_code'] as String?;
        if (code != null) typeByCode[code] = t['id'] as String;
      }

      // Insert counts using real type_ids from personnel_types table
      if (foremanCount > 0 && typeByCode['F'] != null) {
        await db.insert('entry_personnel_counts', {
          'id': 'epc-bkfill-$entryId-$contractorId-F',
          'entry_id': entryId,
          'contractor_id': contractorId,
          'type_id': typeByCode['F'],
          'count': foremanCount,
          'project_id': projectId,
          'created_at': now,
          'updated_at': now,
        }, conflictAlgorithm: ConflictAlgorithm.ignore);
      }
      if (operatorCount > 0 && typeByCode['O'] != null) {
        await db.insert('entry_personnel_counts', {
          'id': 'epc-bkfill-$entryId-$contractorId-O',
          'entry_id': entryId,
          'contractor_id': contractorId,
          'type_id': typeByCode['O'],
          'count': operatorCount,
          'project_id': projectId,
          'created_at': now,
          'updated_at': now,
        }, conflictAlgorithm: ConflictAlgorithm.ignore);
      }
      if (laborerCount > 0 && typeByCode['L'] != null) {
        await db.insert('entry_personnel_counts', {
          'id': 'epc-bkfill-$entryId-$contractorId-L',
          'entry_id': entryId,
          'contractor_id': contractorId,
          'type_id': typeByCode['L'],
          'count': laborerCount,
          'project_id': projectId,
          'created_at': now,
          'updated_at': now,
        }, conflictAlgorithm: ConflictAlgorithm.ignore);
      }
    }
    DebugLogger.db('v32: Backfill complete');
  }
}
```

**Version bump**:
- `database_service.dart` line 53: `version: 31` → `version: 32`
- `database_service.dart` line 79: `version: 31` → `version: 32`

**Verification**:
- Write a migration test: create v31 DB with entry_personnel rows, run upgrade, verify entry_personnel_counts has matching data
- Run app on device from v31 → v32 upgrade path

### Phase 2.2 — Remove Display Fallbacks

**Agent**: `frontend-flutter-specialist-agent`
**Files**:
- `lib/features/entries/presentation/screens/home_screen.dart`
- `lib/features/entries/presentation/widgets/entry_contractors_section.dart`

**home_screen.dart**: Delete legacy fallback at lines ~1347-1365 (`if (contractorsWithData.isEmpty)` block that reads `controller.personnel`) and lines ~1389-1392 (fallback `totalPersonnel` sum). Replace with:

```dart
int totalPersonnel = personnelCounts.values
    .fold(0, (sum, c) => sum + c.values.fold(0, (s, v) => s + v));
```

**entry_contractors_section.dart**: Delete legacy fallback at lines ~75-94 and ~112-115. Same pattern — remove `if (contractorsWithData.isEmpty)` block and fallback total.

**Verification**: Rebuild and verify personnel counts display correctly. No crash if counts are empty (show 0).

### Phase 2.3 — Remove Backend Dual-Write

**Agent**: `backend-data-layer-agent`
**Files**:
- `lib/features/entries/presentation/controllers/contractor_editing_controller.dart`
- `lib/features/entries/presentation/controllers/pdf_data_builder.dart`
- `lib/features/entries/presentation/screens/entry_editor_screen.dart`
- `lib/features/entries/presentation/screens/home_screen.dart`
- `lib/features/contractors/data/datasources/local/contractor_local_datasource.dart`

#### contractor_editing_controller.dart

**Remove**:
- `_personnelDatasource` field (line 34)
- `_personnel` state list (line 53)
- `personnel` getter (line 74)
- Dual-write block (lines 250-299): foreman/operator/laborer mapping + legacy save
- Legacy save call `_personnelDatasource.saveForEntry(...)` (line 324)
- `EntryPersonnelLocalDatasource` from constructor params and initialization (line 40, 44)

**Keep**: All `_countsDatasource` paths (entry_personnel_counts writes).

#### pdf_data_builder.dart

**Correct path**: `lib/features/entries/presentation/controllers/pdf_data_builder.dart`

Change parameter from `EntryPersonnelLocalDatasource personnelDatasource` to `EntryPersonnelCountsLocalDatasource personnelCountsDatasource`. Read from `getCountsByEntryId()`, then map to transient `EntryPersonnel` structs using `personnel_types.short_code`:

```dart
// Load dynamic counts
final countsByContractor = await personnelCountsDatasource.getCountsByEntryId(entry.id);

// Resolve type short_codes for mapping to PDF fields
final types = personnelTypeProvider.types; // already loaded
final typeShortCodes = <String, String>{}; // typeId -> shortCode
for (final t in types) {
  if (t.shortCode != null) typeShortCodes[t.id] = t.shortCode!;
}

// Map to transient EntryPersonnel structs for PDF compatibility
final personnelByContractorId = <String, EntryPersonnel>{};
for (final entry in countsByContractor.entries) {
  int foreman = 0, operator = 0, laborer = 0;
  for (final typeEntry in entry.value.entries) {
    final code = typeShortCodes[typeEntry.key];
    if (code == 'F') foreman += typeEntry.value;
    else if (code == 'O') operator += typeEntry.value;
    else if (code == 'L') laborer += typeEntry.value;
    // Custom types (no F/O/L code) are excluded from PDF — PDF template
    // only has foreman/operator/laborer fields
  }
  personnelByContractorId[entry.key] = EntryPersonnel(
    entryId: entry.id,
    contractorId: entry.key,
    foremanCount: foreman,
    operatorCount: operator,
    laborerCount: laborer,
  );
}
```

NOTE: `EntryPersonnel` model stays alive through Phase 2.3 as a transient PDF bridge. Deleted in Phase 2.5.

#### entry_editor_screen.dart

**Remove**: `_personnelDatasource` field (line 112) and its initialization (line 146). Update `ContractorEditingController` construction (line 150) to remove `personnelDatasource:` parameter. Update PDF generation call to pass `EntryPersonnelCountsLocalDatasource` instead.

#### home_screen.dart

**Update**: `ContractorEditingController` construction (line 114) to remove `personnelDatasource:` parameter.

#### contractor_local_datasource.dart — getMostFrequentIds()

Rewrite SQL (lines 49-57) to join `entry_personnel_counts`:

```sql
SELECT epc.contractor_id, COUNT(DISTINCT epc.entry_id) as usage_count
FROM entry_personnel_counts epc
JOIN daily_entries de ON epc.entry_id = de.id
WHERE de.project_id = ? AND epc.deleted_at IS NULL
GROUP BY epc.contractor_id
ORDER BY usage_count DESC
LIMIT ?
```

**Verification**: Generate a PDF with personnel data. Verify personnel section populated correctly. Run `flutter test`.

### Phase 2.4 — Drop Table (DB v33)

**Agent**: `backend-data-layer-agent`
**Files**:
- `lib/core/database/database_service.dart`
- `lib/core/database/schema/personnel_tables.dart`
- `lib/core/database/schema_verifier.dart` (line 91-96)
- `lib/features/auth/services/auth_service.dart` (line 311)
- `test/core/database/database_service_test.dart` (line 66)
- `test/helpers/mock_database.dart` (line 124)

#### database_service.dart

1. Add v33 migration:
```dart
if (oldVersion < 33) {
  await db.execute('DROP INDEX IF EXISTS idx_entry_personnel_entry');
  await db.execute('DROP INDEX IF EXISTS idx_entry_personnel_deleted_at');
  await db.execute('DROP TABLE IF EXISTS entry_personnel');
  DebugLogger.db('v33 migration: dropped legacy entry_personnel table');
}
```

2. Remove from `_onCreate`: delete `await db.execute(PersonnelTables.createEntryPersonnelTable);`

3. Bump version: `32` → `33` (both line 53 and line 79)

#### personnel_tables.dart

Delete `createEntryPersonnelTable` const (lines 44-61) and 2 legacy indexes from `indexes` list (lines 71-72).

#### schema_verifier.dart

Remove `'entry_personnel'` block (lines 91-96) from expected schema.

#### auth_service.dart

Remove `'entry_personnel',` from `clearLocalCompanyData` table list (line 311).

#### database_service_test.dart

Remove `expect(tableNames, contains('entry_personnel'));` assertion (line 66). Keep the `entry_personnel_counts` assertion.

#### mock_database.dart

Remove `CREATE TABLE entry_personnel` block (line 124).

**Verification**:
- Fresh install: `entry_personnel` table must NOT exist
- Upgrade from v32: table dropped
- `flutter analyze` — 0 issues
- `flutter test` — all pass

### Phase 2.5 — Code Cleanup

**Agent**: `backend-data-layer-agent`
**Files**:
- `lib/features/contractors/data/models/entry_personnel.dart` — DELETE
- `lib/features/contractors/data/datasources/local/entry_personnel_local_datasource.dart` — DELETE (counts methods already exist in `entry_personnel_counts_local_datasource.dart`)
- `lib/features/contractors/data/models/models.dart` — remove barrel export
- `lib/features/contractors/data/datasources/local/local_datasources.dart` — remove barrel export
- `test/features/contractors/data/models/entry_personnel_test.dart` — DELETE
- `test/services/pdf_service_test.dart` — update fixtures to use dynamic counts
- `test/helpers/test_helpers.dart` — remove `createEntryPersonnel` factory + import

**Check before deleting**: `flutter analyze` must show zero references to deleted symbols.

**Verification**:
- `flutter analyze` — 0 issues
- `flutter test` — all pass
- Grep `entry_personnel` in `lib/` — 0 results except migration SQL strings

---

## Workstream 3: Permissions Flow Improvements

**Parallelizable**: Tasks A and B can run in parallel. Task C is a small addition.

### Current State (Verified)

- `ViewOnlyBanner` exists at `lib/shared/widgets/view_only_banner.dart`
- `canWrite` wired in `main.dart` to all 10 data providers
- Admin dashboard guard exists at `app_router.dart:213-217`
- Deactivated/rejected/pending redirects **already exist** at `app_router.dart:191-207` — NO additional redirect logic needed

### Task A: Standardize Provider Silent Failures

**Agent**: `backend-data-layer-agent`
**Files (10 providers)**:

| Provider File | Path |
|---|---|
| LocationProvider | `lib/features/locations/presentation/providers/location_provider.dart` |
| ContractorProvider | `lib/features/contractors/presentation/providers/contractor_provider.dart` |
| EquipmentProvider | `lib/features/contractors/presentation/providers/equipment_provider.dart` |
| BidItemProvider | `lib/features/quantities/presentation/providers/bid_item_provider.dart` |
| DailyEntryProvider | `lib/features/entries/presentation/providers/daily_entry_provider.dart` |
| PhotoProvider | `lib/features/photos/presentation/providers/photo_provider.dart` |
| PersonnelTypeProvider | `lib/features/contractors/presentation/providers/personnel_type_provider.dart` |
| InspectorFormProvider | `lib/features/forms/presentation/providers/inspector_form_provider.dart` |
| CalculatorProvider | `lib/features/calculator/presentation/providers/calculator_provider.dart` |
| TodoProvider | `lib/features/todos/presentation/providers/todo_provider.dart` |

**Prerequisite**: Before applying the pattern, verify each provider has:
1. A `String? _error` field (or equivalent)
2. A public `String? get error` getter
3. A `clearError()` method

If any provider is missing these, add them first.

**Pattern to apply** — add a helper to each provider:

```dart
bool _checkWritePermission(String action) {
  if (canWrite?.call() ?? true) return true;
  _error = 'View-only mode: $action is not available';
  notifyListeners();
  return false;
}
```

Replace all existing ad-hoc `canWrite` checks with:

```dart
Future<bool> deleteItem(String id) async {
  if (!_checkWritePermission('delete item')) return false;
  // ... existing logic
}
```

**Verification**: In test mode (Viewer role), write operation → `_error` set → `notifyListeners()` called → UI shows snackbar.

### Task B: Add ViewOnlyBanner to Data-Editing Screens

**Agent**: `frontend-flutter-specialist-agent`
**Files (7 screens)**:

| Screen | Path |
|---|---|
| todos_screen.dart | `lib/features/todos/presentation/screens/` |
| form_viewer_screen.dart | `lib/features/forms/presentation/screens/` |
| calculator_screen.dart | `lib/features/calculator/presentation/screens/` |
| quantity_calculator_screen.dart | `lib/features/quantities/presentation/screens/` |
| entries_list_screen.dart | `lib/features/entries/presentation/screens/` |
| project_setup_screen.dart | `lib/features/projects/presentation/screens/` |
| home_screen.dart | `lib/features/entries/presentation/screens/` |

NOTE: `entry_editor_screen.dart` already has ViewOnlyBanner — do NOT duplicate.

**Pattern** (match entry_editor_screen.dart):

```dart
body: Column(
  children: [
    if (context.watch<AuthProvider>().isViewer) const ViewOnlyBanner(),
    Expanded(child: /* existing body */),
  ],
),
```

**Also**: Ensure each screen shows a SnackBar when its provider's `error` is set. Use `addPostFrameCallback` to avoid setState-during-build.

### Task C: Admin Dashboard Redirect

**Agent**: `frontend-flutter-specialist-agent`
**File**: `lib/core/router/app_router.dart`

Change `return '/'` to `return '/settings'` at line 216 so non-admins who somehow reach `/admin-dashboard` land on settings (which has admin section visibility) instead of the root.

NOTE: Deactivated/rejected/pending user redirects **already work correctly** at lines 191-207. No changes needed for those flows.

**Verification**:
- Non-admin → `/admin-dashboard` → redirected to `/settings`
- Viewer → todos → ViewOnlyBanner visible
- Viewer → save todo → SnackBar "View-only mode: ..."
- Deactivated user → any screen → `/account-status` (already works)

---

## Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Adapter order wrong | LOW | HIGH | Order verified against `SyncEngineTables.triggeredTables` |
| Background sync still broken | LOW | HIGH | `registerSyncAdapters()` called in both isolates |
| v32 backfill FK violation | LOW | HIGH | JOINs `personnel_types` for real type_ids; filters soft-deleted rows |
| First sync pushes thousands of records | MEDIUM | MEDIUM | SyncEngine has batch processing; monitor logs |
| PDF personnel section breaks | MEDIUM | HIGH | Phase 2.3 verified with PDF test before Phase 2.4 |
| `entry_personnel` referenced after drop | MEDIUM | HIGH | `flutter analyze` after each phase |
| SnackBar during build | LOW | MEDIUM | Use `addPostFrameCallback` |

---

## Agent Assignment Summary

| Agent | Tasks |
|-------|-------|
| `backend-data-layer-agent` | WS1, WS2 Phases 2.1 + 2.3 + 2.4 + 2.5, WS3 Task A |
| `frontend-flutter-specialist-agent` | WS2 Phase 2.2, WS3 Tasks B + C |

---

## Full Test Plan

### After WS1

```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test test/features/sync/"
# Manual: foreground sync → push/pull > 0
# Manual: kill app → wait for background sync → logs show counts > 0
```

### After Each WS2 Phase

```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
# Phase 2.1: Write migration test — v31 DB with entry_personnel → upgrade → verify counts
# Phase 2.4: Fresh install → entry_personnel absent; upgrade from v32 → table dropped
# Phase 2.5: Grep lib/ for entry_personnel → 0 (except migration SQL)
```

### After WS3

```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
# [ ] Admin → admin dashboard accessible
# [ ] Inspector → admin dashboard → redirected to /settings
# [ ] Viewer → todos → ViewOnlyBanner visible
# [ ] Viewer → save todo → SnackBar "View-only mode: ..."
```

---

## Rollback Strategy

**WS1** — Revert `sync_orchestrator.dart` and `background_sync_handler.dart`. Sync returns to silent no-op.

**WS2 Phase 2.1 (v32)** — `INSERT ... conflictAlgorithm: ignore` is safe to leave. Cannot un-apply migration.

**WS2 Phase 2.4 (v33)** — Cannot restore dropped table from migration. Restore from git, increment to v34 with CREATE TABLE. Production data safe — `entry_personnel_counts` is authoritative.

**WS3** — All additive. Revert individual files.

---

## Commit Structure

```
feat(sync): register 16 adapters in foreground + background init
feat(db): v32 safety backfill entry_personnel_counts from entry_personnel
refactor(entries): remove entry_personnel display fallbacks
refactor(contractors): remove dual-write bridge, update PDF path, update entry_editor
feat(db): v33 drop entry_personnel table, update tests
chore(cleanup): delete entry_personnel model, datasource, and tests
fix(permissions): standardize provider write-guard error messages
feat(ui): add ViewOnlyBanner to all data-editing screens
fix(router): redirect non-admins from admin-dashboard to /settings
```

---

## Files Modified (Complete List)

### WS1 — Sync Registry Fix (2 files)
- `lib/features/sync/engine/sync_registry.dart` (add `registerSyncAdapters()` function + 16 imports)
- `lib/features/sync/application/sync_orchestrator.dart` (call in `initialize()`)
- `lib/features/sync/application/background_sync_handler.dart` (call in callback)

### WS2 — entry_personnel Deprecation (19 files)
- `lib/core/database/database_service.dart` (v32 + v33 migrations, version bump, remove from _onCreate)
- `lib/core/database/schema/personnel_tables.dart` (remove legacy table/indexes)
- `lib/core/database/schema_verifier.dart` (remove entry_personnel from expected schema)
- `lib/features/auth/services/auth_service.dart` (remove from clearLocalCompanyData)
- `lib/features/entries/presentation/screens/home_screen.dart` (remove fallback + update controller init)
- `lib/features/entries/presentation/widgets/entry_contractors_section.dart` (remove fallback)
- `lib/features/entries/presentation/controllers/contractor_editing_controller.dart` (remove dual-write)
- `lib/features/entries/presentation/controllers/pdf_data_builder.dart` (switch to counts datasource)
- `lib/features/entries/presentation/screens/entry_editor_screen.dart` (remove _personnelDatasource, update controller init)
- `lib/features/contractors/data/datasources/local/contractor_local_datasource.dart` (rewrite SQL)
- `lib/features/contractors/data/models/entry_personnel.dart` (DELETE in Phase 2.5)
- `lib/features/contractors/data/datasources/local/entry_personnel_local_datasource.dart` (DELETE in Phase 2.5)
- `lib/features/contractors/data/models/models.dart` (remove barrel export)
- `lib/features/contractors/data/datasources/local/local_datasources.dart` (remove barrel export)
- `test/features/contractors/data/models/entry_personnel_test.dart` (DELETE)
- `test/services/pdf_service_test.dart` (update fixtures)
- `test/helpers/test_helpers.dart` (remove createEntryPersonnel)
- `test/helpers/mock_database.dart` (remove entry_personnel table)
- `test/core/database/database_service_test.dart` (remove entry_personnel assertion)

### WS3 — Permissions Flow (18 files)
- 10 provider files (Task A — add `_checkWritePermission`)
- 7 screen files (Task B — add ViewOnlyBanner)
- `lib/core/router/app_router.dart` (Task C — admin redirect to /settings)

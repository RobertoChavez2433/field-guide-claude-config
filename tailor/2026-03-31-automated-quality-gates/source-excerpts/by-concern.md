# Source Excerpts — By Concern

## Concern 1: Architecture Lint Rules (A1-A17)

### Supabase Singleton (A1)
**Target**: `Supabase.instance.client` outside DI root
**Violations**: 8 across 6 files (see ground-truth.md for full list)
**Allowed location**: `lib/core/di/app_initializer.dart` (lines 468, 527, 548, 588, 597, 642, 679)
**Key file**: `lib/shared/datasources/base_remote_datasource.dart:11` — `SupabaseClient get supabase => Supabase.instance.client;`

### DatabaseService Construction (A2)
**Target**: `DatabaseService()` outside DI root
**Violations**: 3 files (pdf_import_service:193, user_profile_sync_datasource:86, background_sync_handler:30)
**Allowed location**: `lib/core/di/app_initializer.dart:400`

### Raw SQL in Presentation (A3)
**Target**: `db.query`, `rawQuery` in `**/presentation/**`
**Source of truth**: GenericLocalDatasource methods should be used instead

### Deprecated AppTheme (A12)
**Target**: `AppTheme.*` color constants
**Violations**: 797 across 76 files
**Migration map**: See patterns/three-tier-color-system.md — each @Deprecated annotation in app_theme.dart specifies replacement

### Single Composition Root (A7)
**Target**: Provider construction outside buildAppProviders()
**Key file**: `lib/core/di/app_providers.dart:37` — the one composition root
**Pattern**: `lib/main.dart` calls `buildAppProviders(deps)` → `MultiProvider`

## Concern 2: Data Safety Lint Rules (D1-D12)

### Raw Database Delete (D1)
**Allowed locations**:
- `lib/services/soft_delete_service.dart` (SoftDeleteService methods)
- `lib/shared/datasources/generic_local_datasource.dart` (hardDelete method at L155)
- `lib/features/sync/engine/` (sync engine internals)
**Pattern**: All other code must use `softDelete()` or `SoftDeleteService.hardDeleteWithSync()`

### Soft Delete Filter (D2)
**Key implementation**: `GenericLocalDatasource._whereWithDeletedFilter` at L46
```dart
String _whereWithDeletedFilter([String? additionalWhere]) {
  // Returns "deleted_at IS NULL" or "deleted_at IS NULL AND ..."
}
```
**Target**: Raw `database.query()` bypassing GenericLocalDatasource must include this filter

### Mounted Check (D5)
**Target**: `context.read` or `context.watch` after `await` without `if (!mounted) return`
**Pattern**: Standard Flutter async safety check

### Schema Column Consistency (D9)
**Source of truth**: `lib/core/database/database_service.dart` `_onCreate` method (L104)
**Cross-check**: `fromMap` keys in model files must match CREATE TABLE columns

## Concern 3: Sync Integrity Lint Rules (S1-S9)

### ConflictAlgorithm.ignore Guard (S1)
**Correct pattern** (sync engine, sync_engine.dart):
```dart
final rowId = await db.insert(tableName, record, conflictAlgorithm: ConflictAlgorithm.ignore);
if (rowId == 0) {
  // Fallback: UPDATE instead
  await db.update(tableName, record, where: 'id = ?', whereArgs: [id]);
}
```
**Violations**: 7 usages outside sync engine that lack the rowId==0 fallback

### change_log Cleanup (S2)
**Correct pattern** (soft_delete_service.dart:175):
```dart
if (rpcSucceeded) {
  await txn.delete('change_log', where: 'project_id = ? AND processed = 0', whereArgs: [projectId]);
} else {
  Logger.db('CHANGE_LOG_KEPT: RPC failed...');
}
```
**Target**: Unconditional change_log DELETE without success check

### sync_control Transaction (S3)
**Correct pattern** (soft_delete_service.dart:399):
```dart
await _db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
try { ... } finally {
  await _db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
}
```
**Target**: sync_control writes outside try/finally transaction blocks

## Concern 4: Test Quality Lint Rules (T1-T8)

### Hardcoded Keys (T1, T2, T7)
**Correct pattern**: `key: TestingKeys.settingsScreen` or `key: TestingKeys.entryCard(entryId)`
**Key file**: `lib/shared/testing_keys/testing_keys.dart` — 90 static Key methods
**Violations**: 12 hardcoded Key('...') in runtime code, 41 TestingKeys bypasses in 12 files

### Hardcoded Delays (T3)
**Target**: `Future.delayed` in test/ files
**Violations**: 63 across 7 test files
**Replace with**: Proper async test patterns (pumpAndSettle, expectLater, etc.)

## Concern 5: Pre-Commit Hook

**Existing**: `.claude/hooks/pre-commit.ps1` (to be replaced)
**New**: Orchestrator that runs analyze → custom_lint → grep checks → targeted tests
**Test targeting**: `lib/features/{feature}/.../file.dart` → `test/features/{feature}/.../file_test.dart`

## Concern 6: CI Workflows

**Delete**: `.github/workflows/e2e-tests.yml`, `.github/workflows/nightly-e2e.yml`
**Create**: `quality-gate.yml` (3 parallel jobs), `labeler.yml`, `sync-defects.yml`, `stale-branches.yml`
**Config**: `.github/labeler.yml` (label→path mapping), `.github/dependabot.yml` (weekly pub updates)

## Concern 7: Branch Protection

**Target**: `main` branch
**Rules**: Require CI pass, block direct push, auto-delete head branches
**Required checks**: `analyze-and-test`, `architecture-validation`, `security-scanning`

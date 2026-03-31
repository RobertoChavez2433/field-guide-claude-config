# Blast Radius — Automated Quality Gates

## Per-Symbol Impact

### AppTheme (HIGHEST IMPACT — color migration)
- **File**: `lib/core/theme/app_theme.dart:9`
- **Risk Score**: 0.92
- **Direct dependents**: 101 files (confirmed references)
- **Potential dependents**: 25 files (import only, may use namespace)
- **Total importers**: 126
- **Breakdown**: 76 lib/ files + 25 test/ files with confirmed references
- **Top impacted files** (by reference count):
  - `home_screen.dart` — 94 refs
  - `project_dashboard_screen.dart` — 60 refs
  - `contractor_editor_widget.dart` — 47 refs
  - `form_viewer_screen.dart` — 35 refs
  - `bid_item_detail_sheet.dart` — 30 refs

### DatabaseService (HIGH IMPACT — DI migration)
- **File**: `lib/core/database/database_service.dart:8`
- **Risk Score**: 0.86
- **Direct dependents**: 92 files (confirmed)
- **Potential dependents**: 52 files
- **Total importers**: 144
- **Note**: Most consumers are already DI-injected. Only 3 violations need fixing.

### FieldGuideColors (MEDIUM — already correct pattern)
- **File**: `lib/core/theme/field_guide_colors.dart:12`
- **Importers**: 86 files
- **Note**: This is the target pattern. No changes needed to this file — files migrating FROM AppTheme will add this import.

### SoftDeleteService (MEDIUM)
- **File**: `lib/services/soft_delete_service.dart:9`
- **Risk Score**: 0.85
- **Direct dependents**: 9 files (confirmed)
- **Total importers**: 15
- **Note**: Lint rules enforce its usage patterns. No changes to the service itself.

### GenericLocalDatasource (MEDIUM — datasource base)
- **File**: `lib/shared/datasources/generic_local_datasource.dart:22`
- **Risk Score**: 0.73
- **Direct dependents**: 8 concrete implementations
- **Descendant classes**: 19 total (8 direct + 11 via ProjectScopedDatasource)
- **Note**: D1 lint rule (`avoid_raw_database_delete`) targets consumers of this class.

### SyncEngine (MEDIUM — sync integrity rules target)
- **File**: `lib/features/sync/engine/sync_engine.dart:83`
- **Direct imports**: 11 files
- **Importers**: 6 lib/ + many test files
- **Dependency graph**: sync_engine → change_tracker, conflict_resolver, scope_type, integrity_checker, orphan_scanner, storage_cleanup, sync_mutex, sync_registry

### AppColors (LOW — static constants)
- **File**: `lib/core/theme/colors.dart:5`
- **Importers**: 6 files
- **Note**: Correct Tier 3 pattern. Some AppTheme refs will migrate here.

### TestingKeys (LOW — testing rules target)
- **File**: `lib/shared/testing_keys/testing_keys.dart:64`
- **Importers**: 24 files (16 lib/ + 8 test/)
- **Note**: T1/T2/T7 lint rules enforce TestingKeys usage.

## Dead Code Targets

Dead code scan returned 713 "dead files" — mostly config/resource files (Android XML, iOS Swift, YAML, integration tests) that CodeMunch can't trace through non-Dart import graphs. Relevant Dart dead code:
- Broken workflow files: `.github/workflows/e2e-tests.yml`, `.github/workflows/nightly-e2e.yml` (confirmed for deletion)

## Summary Counts

| Category | Count |
|----------|-------|
| Files with AppTheme violations | 101 confirmed + 25 potential |
| Files with DatabaseService refs | 92 confirmed |
| Supabase singleton violations | 8 (across 6 files) |
| DatabaseService() violations | 3 (across 3 files) |
| GenericLocalDatasource descendants | 19 classes |
| Sync adapters | 22 (20 bidirectional + 2 push-only) |
| Logger categories | 11 |
| TestingKeys importers | 24 |

# Dependency Graph — Automated Quality Gates

## Direct Changes (New Files to Create)

| File | Change Type | Notes |
|------|-------------|-------|
| `fg_lint_packages/field_guide_lints/pubspec.yaml` | CREATE | Lint package definition |
| `fg_lint_packages/field_guide_lints/analysis_options.yaml` | CREATE | Lint package analysis options |
| `fg_lint_packages/field_guide_lints/lib/field_guide_lints.dart` | CREATE | Plugin entry, registers all rules |
| `fg_lint_packages/field_guide_lints/lib/architecture/` | CREATE | 17 architecture lint rules |
| `fg_lint_packages/field_guide_lints/lib/data_safety/` | CREATE | 12 data safety lint rules |
| `fg_lint_packages/field_guide_lints/lib/sync_integrity/` | CREATE | 9 sync integrity lint rules |
| `fg_lint_packages/field_guide_lints/lib/test_quality/` | CREATE | 8 test quality lint rules |
| `.github/workflows/quality-gate.yml` | CREATE | Main CI workflow |
| `.github/workflows/labeler.yml` | CREATE | PR auto-labeling |
| `.github/workflows/sync-defects.yml` | CREATE | Defect-to-Issues sync |
| `.github/workflows/stale-branches.yml` | CREATE | Post-merge branch cleanup |
| `.github/labeler.yml` | CREATE | Label-to-path mapping |
| `.github/dependabot.yml` | CREATE | Weekly pub dependency updates |
| `.claude/hooks/pre-commit.ps1` | REPLACE | New orchestrator |
| `.claude/hooks/checks/run-analyze.ps1` | CREATE | dart analyze check |
| `.claude/hooks/checks/run-custom-lint.ps1` | CREATE | custom_lint check |
| `.claude/hooks/checks/run-tests.ps1` | CREATE | Targeted flutter test |
| `.claude/hooks/checks/grep-checks.ps1` | CREATE | Text pattern checks |

## Files to Modify

| File | Change Type | Notes |
|------|-------------|-------|
| `analysis_options.yaml` | REWRITE | Upgrade to `lints`, enable strict rules |
| `pubspec.yaml` | MODIFY | Replace `flutter_lints` with `lints`, add `custom_lint` + `custom_lint_builder` dev deps |
| 76+ presentation files | MODIFY | Replace `AppTheme.*` → theme tokens (Phase 2 bulk cleanup) |
| 7 files | MODIFY | Replace `Supabase.instance.client` → injected client |
| 3 files | MODIFY | Replace `DatabaseService()` → injected instance |
| 5 files | MODIFY | Replace hardcoded `Key('...')` → `TestingKeys.*` |
| 12 files | MODIFY | Replace `*TestingKeys.*` bypasses → `TestingKeys.*` facade |
| 9 files | MODIFY | Add `Logger.*` calls to silent catch blocks |
| 7 files | MODIFY | Add rowId==0 fallback after ConflictAlgorithm.ignore |

## Files to Delete

| File | Reason |
|------|--------|
| `.github/workflows/e2e-tests.yml` | Replaced by quality-gate.yml |
| `.github/workflows/nightly-e2e.yml` | Fully deprecated |

## Key Dependency Chains

### DI Root Chain
```
lib/main.dart
  → lib/core/di/app_initializer.dart (creates AppDependencies)
    → lib/core/di/app_providers.dart (buildAppProviders)
      → auth/di/auth_providers.dart
      → projects/di/projects_providers.dart
      → sync/di/sync_providers.dart
      → settings/di/settings_providers.dart
      → (10+ feature provider modules)
```

### Theme Chain
```
lib/core/theme/app_theme.dart (DEPRECATED — source of 797 violations)
  ← 101 presentation files import this

lib/core/theme/field_guide_colors.dart (TARGET — ThemeExtension)
  ← 86 files already use this correctly

lib/core/theme/colors.dart (TARGET — static constants)
  ← 6 files use this
```

### Sync Engine Chain
```
lib/features/sync/engine/sync_engine.dart
  → sync_registry.dart (22 adapters)
  → change_tracker.dart (change_log queries)
  → conflict_resolver.dart (LWW)
  → integrity_checker.dart
  → orphan_scanner.dart
  → storage_cleanup.dart
  → sync_mutex.dart
  ← background_sync_handler.dart
  ← sync_orchestrator.dart
```

### Datasource Hierarchy
```
BaseLocalDatasource<T> (abstract interface)
  └── GenericLocalDatasource<T> (abstract, 23 methods)
      ├── CalculationHistoryLocalDatasource
      ├── EntryEquipmentLocalDatasource
      ├── EquipmentLocalDatasource
      ├── FormResponseLocalDatasource
      ├── InspectorFormLocalDatasource
      ├── ProjectLocalDatasource
      ├── EntryQuantityLocalDatasource
      ├── TodoItemLocalDatasource
      └── ProjectScopedDatasource<T> (abstract, adds project_id filter)
          ├── ContractorLocalDatasource
          ├── PersonnelTypeLocalDatasource
          ├── DailyEntryLocalDatasource
          ├── DocumentLocalDatasource
          ├── EntryExportLocalDatasource
          ├── FormExportLocalDatasource
          ├── LocationLocalDatasource
          ├── PhotoLocalDatasource
          └── BidItemLocalDatasource
```

### Data Flow (for lint rule context)
```
Screen (presentation/)
  → Provider (presentation/providers/)
    → UseCase (domain/usecases/) or Repository (data/repositories/)
      → LocalDatasource (data/datasources/local/) → SQLite via DatabaseService
      → RemoteDatasource (data/datasources/remote/) → Supabase via SupabaseClient
        → SyncEngine (sync/engine/) → change_log → push/pull
```

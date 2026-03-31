# Ground Truth — Automated Quality Gates

## Verified Literals

### File Paths & Directories

| Literal | Source | Status |
|---------|--------|--------|
| `analysis_options.yaml` | Project root | VERIFIED — exists, includes `package:flutter_lints/flutter.yaml` |
| `.github/workflows/e2e-tests.yml` | Project root | VERIFIED — exists (to be deleted) |
| `.github/workflows/nightly-e2e.yml` | Project root | VERIFIED — exists (to be deleted) |
| `fg_lint_packages/` | Project root | VERIFIED — does NOT exist yet (to be created) |
| `.claude/hooks/pre-commit.ps1` | Project root | VERIFIED — exists (to be replaced) |
| `.claude/hooks/archived/` | Project root | VERIFIED — exists |
| `lib/core/theme/app_theme.dart` | L9 | VERIFIED — AppTheme class with @Deprecated annotations |
| `lib/core/theme/field_guide_colors.dart` | L12 | VERIFIED — FieldGuideColors ThemeExtension |
| `lib/core/theme/colors.dart` | L5 | VERIFIED — AppColors static constants |
| `lib/core/di/app_initializer.dart` | L358 | VERIFIED — AppInitializer.initialize() |
| `lib/core/di/app_providers.dart` | L37 | VERIFIED — buildAppProviders() |
| `lib/services/soft_delete_service.dart` | L9 | VERIFIED — SoftDeleteService class |
| `lib/shared/datasources/generic_local_datasource.dart` | L22 | VERIFIED — abstract GenericLocalDatasource<T> |
| `lib/core/logging/logger.dart` | L27 | VERIFIED — Logger class with 11 category methods |
| `lib/shared/testing_keys/testing_keys.dart` | L64 | VERIFIED — TestingKeys class (90 methods) |
| `lib/features/sync/engine/sync_registry.dart` | L63 | VERIFIED — SyncRegistry with 22 adapters |
| `lib/features/sync/engine/change_tracker.dart` | L43 | VERIFIED — ChangeTracker class |
| `lib/features/sync/engine/sync_engine.dart` | L83 | VERIFIED — SyncEngine class |
| `lib/core/database/schema/sync_engine_tables.dart` | L5 | VERIFIED — SyncEngineTables class |
| `lib/core/router/app_router.dart` | L77 | VERIFIED — AppRouter class |
| `lib/core/database/database_service.dart` | L8 | VERIFIED — DatabaseService (singleton factory) |

### Package Dependencies

| Literal | Source | Line | Status |
|---------|--------|------|--------|
| `flutter_lints: ^6.0.0` | `pubspec.yaml` | 129 | VERIFIED — spec says upgrade to `lints` |

### Sync Registry Adapter Count

| Literal | Source | Line | Status |
|---------|--------|------|--------|
| 22 adapters | `sync_registry.dart` | 30-52 | VERIFIED — 22 adapters in registerSyncAdapters() |
| 2 push-only | `sync_registry.dart` | 51-52 | VERIFIED — SupportTicketAdapter, ConsentRecordAdapter |

### Logger Categories

| Category | Method | Line | Status |
|----------|--------|------|--------|
| sync | `Logger.sync()` | L135 | VERIFIED |
| pdf | `Logger.pdf()` | L139 | VERIFIED |
| db | `Logger.db()` | L143 | VERIFIED |
| auth | `Logger.auth()` | L147 | VERIFIED |
| ocr | `Logger.ocr()` | L151 | VERIFIED |
| nav | `Logger.nav()` | L155 | VERIFIED |
| ui | `Logger.ui()` | L159 | VERIFIED |
| photo | `Logger.photo()` | L163 | VERIFIED |
| lifecycle | `Logger.lifecycle()` | L167 | VERIFIED |
| bg | `Logger.bg()` | L171 | VERIFIED |
| error | `Logger.error()` | L176 | VERIFIED |

### Color System

| Literal | Source | Status |
|---------|--------|--------|
| `FieldGuideColors.of(context)` | field_guide_colors.dart:149 | VERIFIED — static accessor |
| `AppColors.*` | colors.dart:5 | VERIFIED — static constants class |
| `AppTheme.*` @Deprecated | app_theme.dart:15+ | VERIFIED — members have @Deprecated annotations |
| `Theme.of(context).colorScheme.*` | Material 3 standard | VERIFIED — used throughout |

### Supabase Singleton Violations (AUDIT RESULTS)

| File | Line(s) | Status |
|------|---------|--------|
| `lib/shared/datasources/base_remote_datasource.dart` | 11 | VIOLATION |
| `lib/features/auth/di/auth_providers.dart` | 57 | VIOLATION |
| `lib/features/settings/di/consent_support_factory.dart` | 46 | VIOLATION |
| `lib/features/sync/di/sync_providers.dart` | 58 | VIOLATION |
| `lib/features/sync/application/background_sync_handler.dart` | 49, 151 | VIOLATION (2x) |
| `lib/features/sync/application/sync_orchestrator.dart` | 225, 384 | VIOLATION (2x) |
| `lib/core/di/app_initializer.dart` | 468,527,548,588,597,642,679 | ALLOWED (DI root) |

### DatabaseService() Direct Construction Violations

| File | Line | Status |
|------|------|--------|
| `lib/features/pdf/services/pdf_import_service.dart` | 193 | VIOLATION |
| `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart` | 86 | VIOLATION |
| `lib/features/sync/application/background_sync_handler.dart` | 30 | VIOLATION |

### Hook Infrastructure

| Literal | Source | Status |
|---------|--------|--------|
| `.githooks/pre-commit` | Project root | VERIFIED — shell script delegates to `pwsh -File ".claude/hooks/pre-commit.ps1"` |
| `.claude/hooks/pre-commit.ps1` | Project root | VERIFIED — exists (to be replaced) |
| `.claude/hooks/archived/` | Project root | VERIFIED — exists |

### Violation Counts (Opus Re-Verified)

| Item | Spec Count | Actual Count | Status |
|------|-----------|--------------|--------|
| @Deprecated in app_theme.dart | "797 violations" | 16 @Deprecated annotations → 797 references across 76 files | VERIFIED |
| `.first` without guard | 158 across 70 files | ~150 raw `.first` across 67 files (44 `.firstOrNull` + 6 `.firstWhere` exist) | VERIFIED (close) |
| `Future.delayed` in tests | 63 across 7 files | 7 files confirmed | VERIFIED |
| `ConflictAlgorithm.ignore` | 7 outside sync engine | 8 files total (incl. sync_engine with correct pattern) | VERIFIED |
| `custom_lint` in pubspec | Should NOT exist | Not found | VERIFIED |
| `is_deleted` column | Should NOT exist | Not found (only `deleted_at`/`deleted_by`) | VERIFIED |
| GoRoute paths | Not enumerated in spec | 35 routes verified | VERIFIED |
| DB tables (canonical) | Not enumerated in spec | 35 tables verified | VERIFIED |

## Flagged Discrepancies

| Item | Spec Says | Actual | Severity |
|------|-----------|--------|----------|
| `analysis_options.yaml` | "currently empty" (Section 16) | Contains `include: package:flutter_lints/flutter.yaml` with comments and empty rules block | LOW — spec wording is misleading but the intent (needs complete rewrite) is correct |
| `.first` count | 158 across 70 files | ~150 across 67 files | LOW — ballpark matches, exact count depends on guard detection |

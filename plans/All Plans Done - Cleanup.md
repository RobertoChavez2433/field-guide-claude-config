# Codebase Cleanup Plan

**Created**: 2026-01-29 | **Session**: 187

## Summary

Comprehensive cleanup after feature-first reorganization (Phases 1-16). Four PRs:
1. Safe deletions + archive
2. Photo-related barrel migration
3. Provider & repository barrel migration
4. Models barrel migration

---

## PR 1: Safe Deletions + Archive (LOW RISK)

### 1.1 Delete Dead Code Files

| File | Lines | Reason |
|------|-------|--------|
| `lib/core/transitions/page_transitions.dart` | 170 | Zero imports - unused custom transitions |
| `lib/core/database/seed_data_service.dart.backup` | ~2000 | Backup file - should not exist |
| `lib/services/weather_service.dart` | 159 | Duplicate - feature version is canonical |
| `integration_test/patrol/helpers/example_usage.dart` | 73 | Marked "NOT A REAL TEST" |

### 1.2 Remove Deprecated Testing Key

**File**: `lib/shared/testing_keys/projects_keys.dart`
- Remove `dashboardLocationsCard` constant (lines 17-19)

### 1.3 Delete Zero-Import Barrel

| File | Importers |
|------|-----------|
| `lib/data/datasources/remote/remote_datasources.dart` | **0** - safe to delete |

### 1.4 Migrate Local Datasources Barrel (3 files)

**Barrel**: `lib/data/datasources/local/local_datasources.dart`

**Files to update**:
1. `lib/features/entries/data/repositories/daily_entry_repository.dart`
2. `lib/features/entries/presentation/screens/report_screen.dart`
3. `lib/features/entries/presentation/screens/home_screen.dart`

**Migration**: Replace `import 'package:construction_inspector/data/datasources/local/local_datasources.dart'` with feature-specific imports.

### 1.5 Archive .claude Files

**Create**: `.claude/archive/plans/` and `.claude/archive/docs/`

**Plans to archive** (6 files):
- `CODEX.md`, `Need to finish Phase 14.md`, `CODE_REVIEW_BACKLOG.md`
- `new_fixes.md`, `Phase-14-DRY-KISS-Implementation-Plan.md`, `CODE_REVIEW_REMAINING.md`

**Docs to archive** (9 files):
- `phase-5-wiring-summary.md`, `phase-5-completion-checklist.md`
- `phase-13.4-summary.md`, `PHASE_13_4_COMPLETE.md`
- `chunked-sync-implementation.md`, `chunked-sync-usage-examples.md`
- `phase-d-auto-fill-context-hydration.md`, `form-fill-provider-usage.md`
- `auto-fill-architecture.md`

### PR 1 Verification
```bash
pwsh -Command "flutter analyze lib/"  # 0 errors
pwsh -Command "flutter test"          # 363 tests pass
```

### PR 1 Commit
```
chore: Remove dead code, backup files, and archive completed plans
```

---

## PR 2: Photo-Related Barrel Migration (~35 files)

### 2.1 Barrels to Migrate

| Barrel | Importers |
|--------|-----------|
| `lib/data/models/photo.dart` | 27 |
| `lib/data/repositories/photo_repository.dart` | 4 |
| `lib/presentation/providers/photo_provider.dart` | 4 |

### 2.2 Target Imports (Feature Paths)

```dart
// OLD
import 'package:construction_inspector/data/models/photo.dart';
// NEW
import 'package:construction_inspector/features/photos/data/models/photo.dart';

// OLD
import 'package:construction_inspector/data/repositories/photo_repository.dart';
// NEW
import 'package:construction_inspector/features/photos/data/repositories/photo_repository.dart';

// OLD
import 'package:construction_inspector/presentation/providers/photo_provider.dart';
// NEW
import 'package:construction_inspector/features/photos/presentation/providers/photo_provider.dart';
```

### 2.3 Files to Update (27 unique + test files)

**lib/** (production):
- `lib/services/photo_service.dart`
- `lib/features/photos/presentation/providers/photo_provider.dart`
- `lib/features/photos/data/repositories/photo_repository.dart`
- `lib/features/sync/application/sync_orchestrator.dart`
- `lib/features/photos/data/datasources/local/photo_local_datasource.dart`
- `lib/features/pdf/services/pdf_service.dart`
- `lib/services/sync_service.dart`
- `lib/features/sync/data/adapters/mock_sync_adapter.dart`
- `lib/features/sync/data/adapters/supabase_sync_adapter.dart`
- `lib/features/sync/domain/sync_adapter.dart`
- `lib/features/entries/presentation/screens/report_screen.dart`
- `lib/features/entries/presentation/screens/entry_wizard_screen.dart`
- `lib/features/photos/presentation/widgets/photo_thumbnail.dart`
- `lib/features/entries/presentation/screens/report_widgets/report_photo_detail_dialog.dart`
- `lib/features/entries/presentation/widgets/photo_detail_dialog.dart`
- `lib/features/toolbox/presentation/providers/gallery_provider.dart`
- `lib/features/toolbox/presentation/screens/gallery_screen.dart`
- `lib/features/pdf/services/photo_pdf_service.dart`
- `lib/features/photos/data/datasources/remote/photo_remote_datasource.dart`
- `lib/main.dart`

**test/** (tests):
- `test/features/toolbox/presentation/screens/gallery_screen_test.dart`
- `test/services/pdf_service_test.dart`
- `integration_test/patrol/fixtures/test_seed_data.dart`
- `test/helpers/mocks/mock_repositories.dart`
- `test/services/photo_service_test.dart`
- `test/data/models/photo_test.dart`
- `test/data/repositories/photo_repository_test.dart`
- `test/helpers/test_helpers.dart`

### 2.4 Delete Barrels After Migration
- `lib/data/models/photo.dart`
- `lib/data/repositories/photo_repository.dart`
- `lib/presentation/providers/photo_provider.dart`

### PR 2 Verification
```bash
pwsh -Command "flutter analyze lib/"
pwsh -Command "flutter test"
pwsh -Command "flutter test test/data/models/photo_test.dart"
pwsh -Command "flutter test test/data/repositories/photo_repository_test.dart"
pwsh -Command "flutter test test/services/photo_service_test.dart"
```

### PR 2 Commit
```
refactor: Migrate photo-related imports to feature paths
```

---

## PR 3: Provider & Repository Barrel Migration (~28 files)

### 3.1 Barrels to Migrate

| Barrel | Importers |
|--------|-----------|
| `lib/presentation/providers/providers.dart` | 11 |
| `lib/presentation/providers/sync_provider.dart` | 6 |
| `lib/presentation/providers/calendar_format_provider.dart` | 4 |
| `lib/data/repositories/repositories.dart` | 7 |

### 3.2 Target Imports

```dart
// sync_provider
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';

// calendar_format_provider
import 'package:construction_inspector/features/entries/presentation/providers/calendar_format_provider.dart';

// providers.dart re-exports from multiple features - replace with specific imports
// repositories.dart re-exports from multiple features - replace with specific imports
```

### 3.3 Files to Update

**sync_provider.dart** (6 files):
- `lib/main.dart`
- `lib/features/settings/presentation/widgets/sync_section.dart`
- `lib/features/entries/presentation/screens/entry_wizard_screen.dart`
- `lib/features/settings/presentation/screens/personnel_types_screen.dart`
- `test/features/sync/presentation/providers/sync_provider_test.dart`
- `lib/presentation/providers/sync_provider.dart` (delete this barrel)

**calendar_format_provider.dart** (4 files):
- `lib/main.dart`
- `lib/features/entries/presentation/screens/home_screen.dart`
- `test/features/entries/presentation/providers/calendar_format_provider_test.dart`
- `lib/presentation/providers/calendar_format_provider.dart` (delete this barrel)

**providers.dart** (11 files - need to identify what each imports):
- `lib/features/toolbox/presentation/screens/form_fill_screen.dart`
- `lib/features/quantities/presentation/screens/quantities_screen.dart`
- `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`
- `lib/features/toolbox/presentation/screens/field_mapping_screen.dart`
- `lib/features/toolbox/presentation/screens/form_import_screen.dart`
- `lib/features/entries/presentation/screens/report_screen.dart`
- `lib/features/toolbox/presentation/screens/calculator_screen.dart`
- `lib/features/toolbox/presentation/screens/forms_list_screen.dart`
- `lib/features/entries/presentation/screens/entries_list_screen.dart`
- `lib/presentation/providers/providers.dart` (delete this barrel)
- `lib/features/auth/presentation/providers/providers.dart` (update or keep?)

**repositories.dart** (7 files):
- `lib/features/quantities/presentation/providers/bid_item_provider.dart`
- `lib/features/entries/presentation/providers/daily_entry_provider.dart`
- `lib/features/toolbox/presentation/providers/inspector_form_provider.dart`
- `lib/features/contractors/presentation/providers/personnel_type_provider.dart`
- `lib/features/contractors/presentation/providers/contractor_provider.dart`
- `lib/features/quantities/presentation/providers/entry_quantity_provider.dart`
- `lib/features/contractors/presentation/providers/equipment_provider.dart`

### 3.4 Delete Barrels After Migration
- `lib/presentation/providers/providers.dart`
- `lib/presentation/providers/sync_provider.dart`
- `lib/presentation/providers/calendar_format_provider.dart`
- `lib/data/repositories/repositories.dart`

### PR 3 Verification
```bash
pwsh -Command "flutter analyze lib/"
pwsh -Command "flutter test"
pwsh -Command "flutter test test/features/sync/"
pwsh -Command "flutter test test/features/entries/"
```

### PR 3 Commit
```
refactor: Migrate provider and repository imports to feature paths
```

---

## PR 4: Models Barrel Migration (64 files)

### 4.1 Barrel to Migrate

| Barrel | Importers |
|--------|-----------|
| `lib/data/models/models.dart` | 64 |

### 4.2 Strategy

The `models.dart` barrel re-exports from 6 feature modules. Each importing file needs to import only the models it actually uses.

**Example transformation**:
```dart
// OLD - imports everything
import 'package:construction_inspector/data/models/models.dart';

// NEW - import only what's used
import 'package:construction_inspector/features/projects/data/models/project.dart';
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';
```

### 4.3 Files to Update (64 files)

**By feature area**:

**toolbox/** (18 files):
- `lib/features/toolbox/presentation/screens/form_fill_screen.dart`
- `lib/features/toolbox/presentation/widgets/form_fields_config.dart`
- `lib/features/toolbox/presentation/widgets/auto_fill_indicator.dart`
- `lib/features/toolbox/presentation/widgets/form_test_history_card.dart`
- `lib/features/toolbox/presentation/widgets/form_preview_tab.dart`
- `lib/features/toolbox/data/services/form_pdf_service.dart`
- `lib/features/toolbox/data/datasources/remote/*.dart` (6 files)
- `lib/features/toolbox/data/services/field_registry_service.dart`
- `lib/features/toolbox/presentation/widgets/dynamic_form_field.dart`
- `lib/features/toolbox/presentation/widgets/form_status_card.dart`
- `lib/features/toolbox/presentation/providers/inspector_form_provider.dart`
- `lib/features/toolbox/presentation/screens/forms_list_screen.dart`

**entries/** (10 files):
- `lib/features/entries/presentation/providers/daily_entry_provider.dart`
- `lib/features/entries/data/repositories/daily_entry_repository.dart`
- `lib/features/entries/presentation/screens/report_screen.dart`
- `lib/features/entries/presentation/screens/home_screen.dart`
- `lib/features/entries/presentation/screens/report_widgets/*.dart` (5 files)
- `lib/features/entries/presentation/widgets/contractor_editor_widget.dart`
- `lib/features/entries/presentation/screens/entries_list_screen.dart`
- `lib/features/entries/presentation/models/contractor_ui_state.dart`

**contractors/** (12 files):
- `lib/features/contractors/data/repositories/*.dart` (3 files)
- `lib/features/contractors/presentation/providers/*.dart` (4 files)
- `lib/features/contractors/data/datasources/local/*.dart` (4 files)
- `lib/features/contractors/data/datasources/remote/*.dart` (5 files)

**sync/** (5 files):
- `lib/features/sync/application/sync_orchestrator.dart`
- `lib/features/sync/data/adapters/mock_sync_adapter.dart`
- `lib/features/sync/data/adapters/supabase_sync_adapter.dart`
- `lib/features/sync/domain/sync_adapter.dart`

**quantities/** (4 files):
- `lib/features/quantities/presentation/screens/quantities_screen.dart`
- `lib/features/quantities/presentation/widgets/bid_item_detail_sheet.dart`
- `lib/features/quantities/presentation/widgets/bid_item_card.dart`
- `lib/features/quantities/presentation/providers/*.dart` (2 files)

**pdf/** (2 files):
- `lib/features/pdf/services/pdf_service.dart`
- `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`
- `lib/features/pdf/services/pdf_import_service.dart`

**test/** (7 files):
- `test/features/toolbox/services/form_pdf_service_cache_test.dart`
- `test/features/toolbox/services/form_pdf_service_test.dart`
- `test/features/toolbox/services/template_validation_test.dart`
- `test/services/pdf_service_test.dart`
- `test/helpers/test_sorting.dart`
- `test/data/models/project_test.dart`

### 4.4 Approach

For each file:
1. Read file to identify which models are actually used
2. Replace single barrel import with specific feature imports
3. Run `flutter analyze` on file to catch any missing imports
4. Proceed to next file

### 4.5 Delete Barrel After Migration
- `lib/data/models/models.dart`

### PR 4 Verification
```bash
pwsh -Command "flutter analyze lib/"
pwsh -Command "flutter test"
# Run full test suite - this is the biggest change
```

### PR 4 Commit
```
refactor: Migrate model imports to feature paths

Completes barrel export deprecation. All imports now use
feature-specific paths per feature-first architecture.
```

---

## Final Cleanup

After all 4 PRs merged, verify:

1. **No deprecated barrel files remain**:
```bash
ls lib/data/models/          # Should only have feature re-exports or be empty
ls lib/data/repositories/    # Should be empty
ls lib/data/datasources/     # Should be empty
ls lib/presentation/providers/  # Should be empty
```

2. **Analyzer clean**:
```bash
pwsh -Command "flutter analyze lib/"
# Should show 0 errors, ~10 info warnings (non-barrel deprecations)
```

3. **All tests pass**:
```bash
pwsh -Command "flutter test"  # 363 tests
```

---

## Risk Mitigation

### Per-File Verification
- After each file edit, run `flutter analyze <file>` to catch issues immediately
- Don't batch too many changes before testing

### Test Coverage
- Run feature-specific tests after migrating each feature area
- Run full test suite before each PR

### Rollback Strategy
- Each PR is independent and can be reverted
- Keep git commits granular within PRs

---

## Critical Files Summary

### PR 1 - Delete
- `lib/core/transitions/page_transitions.dart`
- `lib/core/database/seed_data_service.dart.backup`
- `lib/services/weather_service.dart`
- `integration_test/patrol/helpers/example_usage.dart`
- `lib/data/datasources/remote/remote_datasources.dart`

### PR 2 - Delete After Migration
- `lib/data/models/photo.dart`
- `lib/data/repositories/photo_repository.dart`
- `lib/presentation/providers/photo_provider.dart`

### PR 3 - Delete After Migration
- `lib/presentation/providers/providers.dart`
- `lib/presentation/providers/sync_provider.dart`
- `lib/presentation/providers/calendar_format_provider.dart`
- `lib/data/repositories/repositories.dart`
- `lib/data/datasources/local/local_datasources.dart`

### PR 4 - Delete After Migration
- `lib/data/models/models.dart`

---

## Estimated Scope

| PR | Files Modified | Files Deleted | Risk |
|----|---------------|---------------|------|
| 1 | 6 | 6 | LOW |
| 2 | 35 | 3 | MEDIUM |
| 3 | 28 | 5 | MEDIUM |
| 4 | 64 | 1 | MEDIUM-HIGH |
| **Total** | **~133** | **15** | - |

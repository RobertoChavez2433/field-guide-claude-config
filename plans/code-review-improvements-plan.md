# Code Review Improvements Plan

**Created**: 2026-01-27
**Status**: Draft
**Scope**: ALL review notes and backlog items in 2 PRs

---

## Overview

This plan consolidates ALL improvement items from:
- Toolbox Phases 5-8 Code Review (Session 137)
- Project Status pending tasks
- Session 148 backlog items
- Exploration findings

**Total Items**: 22 improvements across 2 PRs (nothing deferred)

---

## PR 1: File Decomposition, Service Injection & Provider Fixes

**Goal**: Reduce large screens, improve testability, and fix provider patterns.

### 1.1 Extract Widget Builders from form_fill_screen.dart

Reduce `form_fill_screen.dart` from 1,180 lines to ~400 lines.

Create new widget files in `lib/features/toolbox/presentation/widgets/`:

| Widget File | Source Method | Lines |
|-------------|---------------|-------|
| `parsing_preview_widget.dart` | `_buildParsingPreview()` | 123 |
| `table_row_card.dart` | `_buildTableRowCard()` | 90 |
| `form_field_widget.dart` | `_buildField()` | 82 |
| `quick_entry_section.dart` | `_buildQuickEntrySection()` | 60 |
| `parsed_field_chip.dart` | `_buildParsedFieldChip()` | 49 |
| `form_status_indicator.dart` | `_buildStatusCard()` | 37 |

**Files to create** (6):
- `lib/features/toolbox/presentation/widgets/parsing_preview_widget.dart`
- `lib/features/toolbox/presentation/widgets/table_row_card.dart`
- `lib/features/toolbox/presentation/widgets/form_field_widget.dart`
- `lib/features/toolbox/presentation/widgets/quick_entry_section.dart`
- `lib/features/toolbox/presentation/widgets/parsed_field_chip.dart`
- `lib/features/toolbox/presentation/widgets/form_status_indicator.dart`

**Files to modify**:
- `lib/features/toolbox/presentation/widgets/widgets.dart`
- `lib/features/toolbox/presentation/screens/form_fill_screen.dart`

### 1.2 Extract Mega-Screen Dialogs (entry_wizard, report)

Extract large inline dialogs to separate widget files.

**entry_wizard_screen.dart dialogs to extract**:
- Add Personnel Type dialog
- Add Equipment dialog
- Photo source dialog (if inline)

**report_screen.dart dialogs to extract**:
- Add Contractor sheet
- Confirmation dialogs

**Files to create**:
- `lib/features/entries/presentation/widgets/add_personnel_type_dialog.dart`
- `lib/features/entries/presentation/widgets/add_equipment_dialog.dart`
- `lib/features/entries/presentation/widgets/entry_dialogs.dart` (barrel)
- `lib/features/entries/presentation/screens/report_widgets/add_contractor_sheet.dart`

**Files to modify**:
- `lib/features/entries/presentation/screens/entry_wizard_screen.dart`
- `lib/features/entries/presentation/screens/report_screen.dart`

### 1.3 Service Injection via Provider

**Current pattern** (form_fill_screen.dart lines 44-45):
```dart
final _parsingService = FormParsingService();
final _pdfService = FormPdfService();
```

**New pattern**: Register services in `main.dart` and inject via Provider.

**Files to modify**:
- `lib/main.dart` - Add Provider registrations
- `lib/features/toolbox/presentation/screens/form_fill_screen.dart` - Use `context.read<>()`

### 1.4 Immutable List Updates in Provider

Fix 4 direct mutations in `inspector_form_provider.dart`:

| Line | Method | Fix |
|------|--------|-----|
| 97 | `updateForm` | Spread operator pattern |
| 200 | `updateResponse` | Spread operator pattern |
| 219 | `submitResponse` | Spread operator pattern |
| 238 | `markResponseAsExported` | Spread operator pattern |

**Files to modify**:
- `lib/features/toolbox/presentation/providers/inspector_form_provider.dart`

### 1.5 Rename Test Files (datasource → model)

| Current Name | New Name |
|--------------|----------|
| `inspector_form_local_datasource_test.dart` | `inspector_form_model_test.dart` |
| `todo_item_local_datasource_test.dart` | `todo_item_model_test.dart` |

**Files to rename** (2):
- `test/features/toolbox/data/datasources/inspector_form_local_datasource_test.dart`
- `test/features/toolbox/data/datasources/todo_item_local_datasource_test.dart`

### 1.6 Migrate Deprecated Barrel Imports

Update imports from legacy `lib/data/` and `lib/presentation/` paths to feature-first paths.

**Search and replace patterns**:
- `import 'package:construction_inspector/data/` → feature-specific imports
- `import 'package:construction_inspector/presentation/` → feature-specific imports

**Files to modify**: All files with deprecated imports (run grep to identify)

---

## PR 2: Error Handling, DRY Utilities, Database & All Remaining Items

**Goal**: Error handling, shared utilities, database migrations, and all remaining improvements.

### 2.1 Template Loading Error Handling

Wrap `rootBundle.load()` in try-catch in `form_pdf_service.dart` (line 47-49):

```dart
try {
  final templateBytes = await rootBundle.load(data.form.templatePath);
} on FlutterError catch (e) {
  debugPrint('[FormPDF] Template not found: ${data.form.templatePath}');
  return (null, 'PDF template not found. Please reinstall the app.');
}
```

**Files to modify**:
- `lib/features/toolbox/data/services/form_pdf_service.dart`

### 2.2 Create Shared Field Formatting Utility

Extract duplicate `_formatFieldName()` to shared utility.

**Create**: `lib/shared/utils/field_formatter.dart`

```dart
class FieldFormatter {
  static String snakeToTitleCase(String fieldName) { ... }
  static String snakeToCamelCase(String fieldName) { ... }
  static String snakeToPascalCase(String fieldName) { ... }
  static List<String> generateVariations(String fieldName) { ... }
}
```

**Files to modify**:
- `lib/shared/utils/field_formatter.dart` (create)
- `lib/shared/utils/utils.dart` (add export)
- `lib/features/toolbox/data/services/form_pdf_service.dart` (use shared)
- `lib/features/toolbox/presentation/screens/form_fill_screen.dart` (use shared)

### 2.3 Extract Regex Patterns to Constants

Create parsing patterns class in `form_parsing_service.dart`:

```dart
class ParsingPatterns {
  ParsingPatterns._();
  static final segmentDelimiter = RegExp(r'[,;\n|]+');
  static final colonFormat = RegExp(r'^(.+?)\s*[:=]\s*(.+)$');
  static final spaceSeparated = RegExp(r'^([a-z]+(?:\s+[a-z]+)?)\s+([\d.%]+)$');
  static final reversedFormat = RegExp(r'^([\d.%]+)\s+([a-z]+(?:\s+[a-z]+)?)$');
  static final fuzzyWithUnits = RegExp(r'([\d.]+)\s*(%|in|pcf|cy)?\s*([a-z]+)');
  static final percentSuffix = RegExp(r'%$');
  static final unitSuffix = RegExp(r'\s*(in|pcf|cy|f|°f)$', caseSensitive: false);
  static final invalidFilenameChars = RegExp(r'[^a-zA-Z0-9]');
}
```

**Files to modify**:
- `lib/features/toolbox/data/services/form_parsing_service.dart`

### 2.4 Fix Unsafe firstWhere in Tests

Add `orElse` to 9 `firstWhere` calls in parsing service test (lines 53, 57, 60, 70, 87, 104, 113, 122, 125, 202-204).

**Files to modify**:
- `test/features/toolbox/services/form_parsing_service_test.dart`

### 2.5 Externalize Form Definitions to JSON Assets

Move form field definitions from code to JSON files.

**Create asset files**:
- `assets/data/forms/mdot_1174r_concrete.json`
- `assets/data/forms/mdot_0582b_density.json`

**Files to modify**:
- `lib/features/toolbox/data/services/form_seed_service.dart` (load from assets)
- `pubspec.yaml` (add assets/data/forms/)

### 2.6 Extract Sync Queue Pattern (DRY)

Create mixin to reduce boilerplate in providers that queue sync operations.

**Create**: `lib/shared/providers/sync_notifying_mixin.dart`

```dart
mixin SyncNotifyingMixin on ChangeNotifier {
  SyncService? get syncService;

  Future<void> updateItemWithSync<T>({
    required List<T> items,
    required T item,
    required String Function(T) getId,
    required String syncTable,
    required void Function(List<T>) setItems,
  }) async { ... }
}
```

**Files to modify**:
- `lib/shared/providers/sync_notifying_mixin.dart` (create)
- `lib/shared/providers/providers.dart` (add export)
- `lib/features/toolbox/presentation/providers/inspector_form_provider.dart` (use mixin)
- `lib/features/toolbox/presentation/providers/todo_provider.dart` (use mixin)

### 2.7 DRY Refactoring in Data Layer

Identify and consolidate duplicate patterns across repositories.

**Common patterns to extract**:
- Error handling wrappers
- Validation logic
- Query building helpers

**Files to audit and refactor**:
- `lib/features/*/data/repositories/*.dart`

### 2.8 Run Supabase Migrations

Execute pending database migrations.

**Migrations to run**:
- `supabase/migrations/supabase_schema_v3.sql` (personnel_types tables)
- `supabase/migrations/supabase_schema_v4_rls.sql` (RLS policies)

**Verification**:
```bash
# Connect to Supabase and run migrations
supabase db push

# Verify tables exist
supabase db diff
```

### 2.9 Separate Photos/Attachments in Report Screen

Split the current combined photos section into separate Photos and Form Attachments sections.

**Files to modify**:
- `lib/features/entries/presentation/screens/report_screen.dart`
- May need new widget: `lib/features/entries/presentation/widgets/attachments_section.dart`

---

## File Change Summary

### PR 1 Files (~15 new, ~12 modified, 2 renamed)

| Action | File |
|--------|------|
| Create | `lib/features/toolbox/presentation/widgets/parsing_preview_widget.dart` |
| Create | `lib/features/toolbox/presentation/widgets/table_row_card.dart` |
| Create | `lib/features/toolbox/presentation/widgets/form_field_widget.dart` |
| Create | `lib/features/toolbox/presentation/widgets/quick_entry_section.dart` |
| Create | `lib/features/toolbox/presentation/widgets/parsed_field_chip.dart` |
| Create | `lib/features/toolbox/presentation/widgets/form_status_indicator.dart` |
| Create | `lib/features/entries/presentation/widgets/add_personnel_type_dialog.dart` |
| Create | `lib/features/entries/presentation/widgets/add_equipment_dialog.dart` |
| Create | `lib/features/entries/presentation/widgets/entry_dialogs.dart` |
| Create | `lib/features/entries/presentation/screens/report_widgets/add_contractor_sheet.dart` |
| Modify | `lib/features/toolbox/presentation/widgets/widgets.dart` |
| Modify | `lib/features/toolbox/presentation/screens/form_fill_screen.dart` |
| Modify | `lib/features/toolbox/presentation/providers/inspector_form_provider.dart` |
| Modify | `lib/features/entries/presentation/screens/entry_wizard_screen.dart` |
| Modify | `lib/features/entries/presentation/screens/report_screen.dart` |
| Modify | `lib/main.dart` |
| Modify | Multiple files with deprecated imports |
| Rename | `test/.../inspector_form_local_datasource_test.dart` → `inspector_form_model_test.dart` |
| Rename | `test/.../todo_item_local_datasource_test.dart` → `todo_item_model_test.dart` |

### PR 2 Files (~8 new, ~15 modified)

| Action | File |
|--------|------|
| Create | `lib/shared/utils/field_formatter.dart` |
| Create | `lib/shared/providers/sync_notifying_mixin.dart` |
| Create | `assets/data/forms/mdot_1174r_concrete.json` |
| Create | `assets/data/forms/mdot_0582b_density.json` |
| Create | `lib/features/entries/presentation/widgets/attachments_section.dart` |
| Modify | `lib/shared/utils/utils.dart` |
| Modify | `lib/shared/providers/providers.dart` |
| Modify | `lib/features/toolbox/data/services/form_pdf_service.dart` |
| Modify | `lib/features/toolbox/data/services/form_parsing_service.dart` |
| Modify | `lib/features/toolbox/data/services/form_seed_service.dart` |
| Modify | `lib/features/toolbox/presentation/providers/todo_provider.dart` |
| Modify | `lib/features/entries/presentation/screens/report_screen.dart` |
| Modify | `test/features/toolbox/services/form_parsing_service_test.dart` |
| Modify | `pubspec.yaml` |
| Modify | Multiple repository files (DRY refactor) |
| Execute | `supabase/migrations/supabase_schema_v3.sql` |
| Execute | `supabase/migrations/supabase_schema_v4_rls.sql` |

---

## Excluded from 2-PR Scope (Separate Epic)

**AASHTOWare Integration** - This is a major feature requiring 12-17 weeks per existing plan.
- Full implementation plan: `.claude/implementation/AASHTOWARE_Implementation_Plan.md`
- Should remain as separate epic, not bundled with code quality improvements

---

## Verification

### After PR 1
```bash
# Run analyzer
flutter analyze

# Run all tests
flutter test

# Verify form_fill_screen line count
wc -l lib/features/toolbox/presentation/screens/form_fill_screen.dart
# Expected: ~400 lines

# Verify entry_wizard_screen line count reduced
wc -l lib/features/entries/presentation/screens/entry_wizard_screen.dart

# Verify no deprecated imports remain
grep -r "import.*construction_inspector/data/" lib/
grep -r "import.*construction_inspector/presentation/" lib/
# Expected: No matches
```

### After PR 2
```bash
# Run full analyzer
flutter analyze

# Run all tests
flutter test

# Verify shared utility usage
grep -r "FieldFormatter" lib/
grep -r "ParsingPatterns\." lib/
grep -r "SyncNotifyingMixin" lib/

# Verify Supabase migrations applied
supabase db diff
# Expected: No pending changes

# Manual: Test PDF export with missing template
# Manual: Verify Photos and Attachments are separate sections in report
```

---

## Acceptance Criteria

### PR 1
- [ ] form_fill_screen.dart < 500 lines
- [ ] entry_wizard_screen.dart dialogs extracted
- [ ] report_screen.dart dialogs extracted
- [ ] 6+ new widget files created and exported
- [ ] Services injected via Provider
- [ ] No direct list mutations in inspector_form_provider.dart
- [ ] Test files renamed
- [ ] No deprecated barrel imports remain
- [ ] All tests pass
- [ ] Analyzer: 0 errors

### PR 2
- [ ] Template loading has user-friendly error message
- [ ] FieldFormatter utility created and used
- [ ] ParsingPatterns constants used throughout
- [ ] All firstWhere calls have orElse in tests
- [ ] Form definitions load from JSON assets
- [ ] SyncNotifyingMixin created and used in 2+ providers
- [ ] Data layer DRY patterns extracted
- [ ] Supabase migrations executed successfully
- [ ] Photos and Attachments separated in report screen
- [ ] All tests pass
- [ ] Analyzer: 0 errors

 ---
 Out of Scope (Backlog)

 These items were identified but deferred:
 - JSON externalization of form definitions (low priority, 2 forms manageable)
 - Sync queue pattern extraction (complex refactor, minimal benefit)
 - Test file renaming (datasource → model naming)
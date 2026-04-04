# Analyzer Zero Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Eliminate all 1054 remaining `flutter analyze` violations to reach zero issues.
**Spec:** `.claude/specs/2026-04-04-analyzer-zero.md`
**Tailor:** `.claude/tailor/2026-04-04-analyzer-zero/`

**Architecture:** Policy changes in analysis_options.yaml, followed by mechanical catch/annotation/wrapper fixes, then three new abstractions (SafeRow extension, SafeAction mixin, RepositoryResult.safeCall), and finally copyWith type-promotion fixes. Each phase is independently verifiable via `flutter analyze` count reduction.
**Tech Stack:** Dart, Flutter, sqflite, Supabase, provider
**Blast Radius:** 2 new files (safe_row.dart, safe_action_mixin.dart), 1 modified shared file (base_repository.dart += safeCall), ~190 modified files total (incl. ~30 providers + ~10 repositories refactored for DRY), 0 test files broken

---

## Phase 1: Policy Decisions

### Sub-phase 1.1: analysis_options.yaml Cleanup

**Files:**
- Modify: `analysis_options.yaml:57,65`

**Agent**: general-purpose

#### Step 1.1.1: Remove `do_not_use_environment` and `strict_raw_type`

```yaml
# WHY: All 42 do_not_use_environment violations are legitimate static const fromEnvironment usage.
# WHY: strict_raw_type is not recognized by the current Dart analyzer (undefined_lint).

# In the linter rules section:
# Line 57: DELETE the line `do_not_use_environment: true`
# Line 65: DELETE the line `strict_raw_type: true`
```

#### Step 1.1.2: Verify with flutter analyze

Run: `pwsh -Command "flutter analyze 2>&1 | Select-String 'issues found'"`
Expected: Count drops by ~43 (42 do_not_use_environment + 1 undefined_lint)

---

## Phase 2: Mechanical Catch Fixes

### Sub-phase 2.1: Bare catch → on Exception catch (all production code)

**Files:**
- Modify: ~90 files in `lib/` containing `catch (e)` or `catch (e, stack)` or `catch (_)`

**Agent**: general-purpose

#### Step 2.1.1: Replace all bare catches in lib/

For every file in `lib/` with `avoid_catches_without_on_clauses` violations, apply these mechanical transformations:

```dart
// PATTERN A: catch (e) → on Exception catch (e)
// Before:
} catch (e) {
// After:
} on Exception catch (e) {

// PATTERN B: catch (e, stack) → on Exception catch (e, stack)
// Before:
} catch (e, stack) {
// After:
} on Exception catch (e, stack) {

// PATTERN C: catch (e, stackTrace) → on Exception catch (e, stackTrace)
// Before:
} catch (e, stackTrace) {
// After:
} on Exception catch (e, stackTrace) {

// PATTERN D: catch (_) → on Exception catch (_)
// Before:
} catch (_) {
// After:
} on Exception catch (_) {
```

// IMPORTANT: JSON decode methods (form_response.dart, inspector_form.dart,
// calculation_history.dart) should use `on FormatException catch (e)` instead
// when the only possible exception is from jsonDecode().

// IMPORTANT — SECURITY: The following catch blocks handle Error subclasses
// (StateError from company_id mismatch, ArgumentError from invalid storage path,
// RangeError from corrupt image EXIF). They MUST use `catch (Object e)` instead
// of `on Exception catch (e)` to preserve graceful degradation:
//   - sync_engine.dart lines: 324, 587, 596, 812, 1295, 1385, 1531, 1682, 2214
//   - database_service.dart lines: 86, 809, 1900
//   - sync_orchestrator.dart line: 351
// Converting these to `on Exception catch` would let Error subclasses propagate
// unhandled, crashing sync instead of degrading gracefully.

**File list by feature (highest violation count first):**

| Feature | Files | ~Violations |
|---------|-------|:-----------:|
| sync | sync_engine.dart, sync_orchestrator.dart, sync_lifecycle_manager.dart, background_sync_handler.dart, change_tracker.dart, integrity_checker.dart | 62 |
| forms | form_response_repository.dart, inspector_form_repository.dart, form_pdf_service.dart, form_export_repository.dart | 59 |
| core | logger.dart, driver_server.dart, database_service.dart, app_initializer.dart, core_services_initializer.dart | 52 |
| auth | auth_provider.dart, app_config_provider.dart, company_setup_screen.dart, auth_service.dart | 39 |
| entries | daily_entry_provider.dart, entry_editor_screen.dart, entry_export_provider.dart, daily_entry_repository.dart, document_repository.dart | 35 |
| settings | admin_provider.dart, trash_screen.dart, consent_provider.dart, support_provider.dart | 32 |
| pdf | text_recognizer_v2.dart, page_renderer_v2.dart, image_preprocessor_v2.dart, extraction_pipeline.dart, + stages | 32 |
| projects | project_provider.dart, project_list_screen.dart, project_setup_screen.dart, project_repository.dart | 31 |
| services | image_service.dart, soft_delete_service.dart, photo_service.dart, document_service.dart | 22 |
| photos | photo_repository_impl.dart, photo_remote_datasource.dart, photo_provider.dart | 17 |
| quantities | entry_quantity_provider.dart, bid_item_provider.dart, bid_item_repository_impl.dart, entry_quantity_repository_impl.dart | 15 |
| todos | todo_provider.dart | 12 |
| shared | base_list_provider.dart, paged_list_provider.dart, preferences_service.dart | 11 |
| contractors | equipment_provider.dart, contractor_provider.dart | 9 |
| calculator | calculator_provider.dart, calculation_history.dart | 5 |
| weather | weather_service.dart | 3 |
| gallery | gallery_provider.dart | 1 |

#### Step 2.1.2: Replace all bare catches in test/ and integration_test/

// NOTE: The spec (Phase 1B) originally called for excluding test/ and integration_test/
// from `avoid_catches_without_on_clauses` via analysis_options.yaml. However, Dart's
// analyzer does not support per-rule per-directory exclusions natively. Rather than
// adding `// ignore_for_file:` to ~65 test files, we apply the same mechanical fix
// here. This replaces the spec's policy approach with consistent mechanical fixes
// across the entire codebase.

Same mechanical transformation for ~65 violations in test code:

**Key test files:**
- `test/helpers/mocks/mock_providers.dart` (22)
- `test/helpers/mocks/mock_repositories.dart` (2)
- `test/presentation/providers/daily_entry_provider_test.dart` (6)
- `test/features/sync/engine/sync_engine_test.dart` (~5)
- `integration_test/*.dart` (7)
- Other test files (~23)

#### Step 2.1.3: Verify with flutter analyze

Run: `pwsh -Command "flutter analyze 2>&1 | Select-String 'issues found'"`
Expected: `avoid_catches_without_on_clauses` drops to 0. Total count should drop by ~502.

### Sub-phase 2.2: Add @immutable annotations

**Files:**
- Modify: 35 model class files

**Agent**: backend-data-layer-agent

#### Step 2.2.1: Add @immutable to PDF extraction models (~25 classes)

All in `lib/features/pdf/services/extraction/models/`:

```dart
// WHY: All fields are already final. Adding @immutable satisfies
// avoid_equals_and_hash_code_on_mutable_classes since these ARE immutable.
import 'package:meta/meta.dart';

@immutable
class ClassifiedRow {
  // ... existing code unchanged
}
```

**Files and classes:**
- `classified_rows.dart` — ClassifiedRow, ClassifiedRows
- `cell_grid.dart` — CellGrid, Cell (NOTE: Cell may be nested, annotate both)
- `column_map.dart` — ColumnSpec, ColumnMap
- `confidence.dart` — ConfidenceScore, FieldConfidence
- `detected_regions.dart` — DetectedRegion, DetectedRegions
- `document_checksum.dart` — DocumentChecksum
- `document_profile.dart` — DocumentProfile, DocumentProfileHeader
- `extraction_result.dart` — UnifiedExtractionResult
- `ocr_element.dart` — OcrElement, OcrPage
- `parsed_items.dart` — ParsedItem, ParsedItems
- `pipeline_config.dart` — PipelineConfig
- `processed_items.dart` — ProcessedItems
- `quality_report.dart` — QualityReport
- `sidecar.dart` — SidecarEntry, Sidecar
- `stage_report.dart` — StageReport

Also in extraction pipeline/OCR:
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` — PipelineResult
- `lib/features/pdf/services/extraction/stages/tesseract_config_v2.dart` — TesseractConfigV2

#### Step 2.2.2: Add @immutable to data models (~10 classes)

```dart
import 'package:meta/meta.dart';

@immutable
class Company {
  // ... existing code unchanged
}
```

**Files and classes:**
- `lib/features/auth/data/models/company.dart` — Company
- `lib/features/auth/data/models/company_join_request.dart` — CompanyJoinRequest
- `lib/features/auth/data/models/user_profile.dart` — UserProfile
- `lib/features/calculator/data/models/calculation_history.dart` — CalculationHistory
- `lib/features/forms/data/models/form_response.dart` — FormResponse
- `lib/features/forms/data/models/inspector_form.dart` — InspectorForm
- `lib/features/settings/data/models/consent_record.dart` — ConsentRecord
- `lib/features/settings/data/models/support_ticket.dart` — SupportTicket
- `lib/features/todos/data/models/todo_item.dart` — TodoItem
- `lib/core/database/schema_verifier.dart` — ColumnDrift

#### Step 2.2.3: Verify with flutter analyze

Expected: `avoid_equals_and_hash_code_on_mutable_classes` drops to 0 (~70 violations eliminated).

### Sub-phase 2.3: Replace $runtimeType with StageNames constants

**Files:**
- Modify: 18 files in `lib/features/pdf/services/extraction/stages/`

**Agent**: pdf-agent

#### Step 2.3.1: Add _logTag constant and replace $runtimeType in each stage class

For each of the 18 stage classes, add a static constant and replace all `$runtimeType` occurrences:

```dart
// WHY: no_runtimetype_tostring — using runtimeType.toString() is unsafe in production.
// NOTE: StageNames constants already exist and are used in StageReport creation.
import 'package:construction_inspector/features/pdf/services/extraction/stages/stage_names.dart';

class CellExtractorV2 {
  static const _logTag = StageNames.cellExtraction;

  // Replace:  Logger.pdf('STAGE_START stage=$runtimeType');
  // With:     Logger.pdf('STAGE_START stage=$_logTag');

  // Replace:  Logger.pdf('STAGE_COMPLETE stage=$runtimeType elapsed=...');
  // With:     Logger.pdf('STAGE_COMPLETE stage=$_logTag elapsed=...');

  // Replace:  Logger.pdf('MEMORY_SNAPSHOT stage=$runtimeType ...');
  // With:     Logger.pdf('MEMORY_SNAPSHOT stage=$_logTag ...');
}
```

**Complete mapping (from ground-truth.md):**

| Stage Class | StageNames Constant |
|-------------|---------------------|
| CellExtractorV2 | `StageNames.cellExtraction` |
| ColumnDetectorV2 | `StageNames.columnDetection` |
| DocumentQualityProfiler | `StageNames.documentAnalysis` |
| ElementValidator | `StageNames.elementValidation` |
| FieldConfidenceScorer | `StageNames.fieldConfidenceScoring` |
| GridLineDetector | `StageNames.gridLineDetection` |
| GridLineRemover | `StageNames.gridLineRemoval` |
| HeaderConsolidator | `StageNames.headerConsolidationFinal` |
| ImagePreprocessorV2 | `StageNames.imagePreprocessing` |
| NumericInterpreter | `StageNames.numericInterpretation` |
| PageRendererV2 | `StageNames.pageRendering` |
| PostProcessorV2 | `StageNames.postProcessing` |
| QualityValidator | `StageNames.qualityValidation` |
| RegionDetectorV2 | `StageNames.regionDetection` |
| RowClassifierV3 | `StageNames.rowClassification` |
| RowMerger | `StageNames.rowMerging` |
| RowParserV3 | `StageNames.rowParsing` |
| TextRecognizerV2 | `StageNames.textRecognition` |

#### Step 2.3.2: Verify with flutter analyze

Expected: `no_runtimetype_tostring` drops to 0 (42 violations eliminated).

### Sub-phase 2.4: Wrap fire-and-forget calls with unawaited()

**Files:**
- Modify: ~40 files in `lib/` with `discarded_futures` violations

**Agent**: frontend-flutter-specialist-agent

#### Step 2.4.1: Add unawaited() wrappers for navigation, dialogs, platform channels

For each file with fire-and-forget Future calls, add the import and wrap:

```dart
import 'dart:async' show unawaited;

// Navigation calls (onTap/onPressed callbacks):
onTap: () {
  unawaited(context.pushNamed('forms'));
},

// Dialog shows (result unused):
unawaited(AppDialog.show(context: context, ...));

// Platform channels (fire-and-forget):
unawaited(HapticFeedback.lightImpact());
unawaited(Clipboard.setData(ClipboardData(text: value)));

// Lifecycle methods (can't be made async):
@override
void didChangeAppLifecycleState(AppLifecycleState state) {
  if (state == AppLifecycleState.paused) {
    unawaited(_saveIfEditing());
  }
}

// Logger internals (fire-and-forget by design):
unawaited(_writeToSink(message));
```

**Files by category:**
- Navigation (~38): toolbox_home_screen.dart, settings_screen.dart, home_screen.dart, project_list_screen.dart, entries_list_screen.dart, calculator_screen.dart, etc.
- Dialogs (~20): todos_screen.dart, extraction_banner.dart, personnel_types_screen.dart, etc.
- Platform channels (~10): home_screen.dart, calculator_screen.dart
- Lifecycle (~12): home_screen.dart, entry_editor_screen.dart, consent_screen.dart, legal_document_screen.dart
- Logger (6): logger.dart (lines 213, 237, 241, 243, 248, 724)
- Sync debug (1): sync_engine.dart

#### Step 2.4.2: Convert provider load methods to async/await

For ~30 violations where methods SHOULD await:

```dart
// WHY: These are called from addPostFrameCallback — making them async is safe
// and ensures proper error handling.

// Before:
void _loadTodos() {
  todoProvider.loadTodos(projectId: projectId);  // discarded_futures
}

// After:
Future<void> _loadTodos() async {
  await todoProvider.loadTodos(projectId: projectId);
}
```

**Files:** todos_screen.dart, home_screen.dart, entries_list_screen.dart, drafts_list_screen.dart, admin_dashboard_screen.dart, project_list_screen.dart, and similar presentation screens.

#### Step 2.4.3: Fix test file violations

For ~9 test violations, make test callbacks async and add await:

```dart
// Before:
setUp(() {
  provider.loadData();  // discarded_futures
});

// After:
setUp(() async {
  await provider.loadData();
});
```

#### Step 2.4.4: Verify with flutter analyze

Expected: `discarded_futures` and `unawaited_futures` drop to 0 (~131 + ~18 = ~149 violations eliminated).

### Sub-phase 2.5: Fix missing_whitespace_between_adjacent_strings

**Files:**
- Modify: ~30 files in `lib/` with 54 violations

**Agent**: general-purpose

#### Step 2.5.1: Add missing whitespace in adjacent string literals

Each violation is a string concatenation where adjacent strings lack a space:

```dart
// Before (missing space at boundary):
'Error retrieving''response data'
// After:
'Error retrieving response data'

// Before (SQL string adjacency):
'SELECT * FROM table'
'WHERE id = ?'
// After:
'SELECT * FROM table '
'WHERE id = ?'
```

// IMPORTANT: Review each instance — some are intentional multi-line strings.
// The fix may be adding a trailing space or a leading space, depending on context.

#### Step 2.5.2: Verify with flutter analyze

Expected: `missing_whitespace_between_adjacent_strings` drops to 0 (54 violations eliminated).

### Sub-phase 2.6: Add reasons to // ignore: comments

**Files:**
- Modify: ~35 files with 42 `document_ignores` violations

**Agent**: general-purpose

#### Step 2.6.1: Add reason text to all ignore comments

```dart
// Before:
// ignore: avoid_print
print('diagnostic output');

// After:
// ignore: avoid_print, diagnostic output for integration test runner

// Before:
// ignore_for_file: avoid_print

// After:
// ignore_for_file: avoid_print, test diagnostic output requires print
```

**Common reasons by context:**
- Integration tests: `diagnostic output for test runner`
- `deprecated_member_use_from_same_package`: `legacy field access preserved for backward compatibility`
- `experimental_member_use`: `Sentry SDK experimental API required for zone error capture`

#### Step 2.6.2: Verify with flutter analyze

Expected: `document_ignores` drops to 0 (42 violations eliminated).

### Sub-phase 2.7: Fix avoid_dynamic_calls

**Files:**
- Modify: ~8 files in `test/`, ~4 files in `lib/`

**Agent**: general-purpose

#### Step 2.7.1: Fix SQLite query result access in tests (39 violations)

Concentrated in `test/core/database/extraction_schema_migration_test.dart`:

```dart
// Before:
expect(tables.first['name'], equals('extraction_metrics'));

// After:
expect(tables.first['name'] as String, equals('extraction_metrics'));
```

#### Step 2.7.2: Fix JSON decoded list access in tests (22 violations)

```dart
// Before:
final parsed = jsonDecode(result!) as List;
expect(parsed[0]['text'], 'Poured section 3');

// After:
final parsed = (jsonDecode(result!) as List).cast<Map<String, dynamic>>();
expect(parsed[0]['text'], 'Poured section 3');
```

**Files:** activities_serialization_test.dart, generate_mp_fixtures_test.dart, mp_stage_trace_diagnostic_test.dart

#### Step 2.7.3: Fix Supabase PostgrestList access in production code (4 violations)

```dart
// Before (sync_engine.dart):
final page = await query.order('created_at').range(offset, offset + batchSize - 1);
if (page.isEmpty) break;

// After:
final page = await query.order('created_at').range(offset, offset + batchSize - 1);
final typedPage = List<Map<String, dynamic>>.from(page);
if (typedPage.isEmpty) break;
```

**Files:** sync_engine.dart (3), orphan_scanner.dart (1)

#### Step 2.7.4: Fix Supabase RPC response in company_members_repository.dart (3 violations)

```dart
// Before:
final data = List<dynamic>.from(response);
return data.map((row) {
  return AssignableMember(userId: row['id'] as String, ...);
});

// After:
final data = (response as List).cast<Map<String, dynamic>>();
return data.map((row) {
  return AssignableMember(userId: row['id'] as String, ...);
});
```

#### Step 2.7.5: Fix remaining test map chains (16 violations)

Add intermediate casts in test assertions:

```dart
// Before:
expect(result.qualityMetrics['pageDetails']['page_1'], ...);

// After:
final details = result.qualityMetrics['pageDetails'] as Map<String, dynamic>;
expect(details['page_1'], ...);
```

#### Step 2.7.6: Fix export_entry_use_case.dart generic (1 violation)

Ensure proper type flow so list element type is `FormResponse`, not `dynamic`.

#### Step 2.7.7: Verify with flutter analyze

Expected: `avoid_dynamic_calls` drops to 0 (~94 violations eliminated).

### Sub-phase 2.8: Fix remaining small rules

**Files:**
- Modify: ~25 files with 28 violations across multiple rules

**Agent**: general-purpose

#### Step 2.8.1: Fix matching_super_parameters (~17 violations)

Rename super parameters to match parent constructor parameter names:

```dart
// Before:
LocationRemoteDatasource(super.supabaseClient)
// After (parent param is named 'supabase'):
LocationRemoteDatasource(super.supabase)
```

// NOTE: All ~17 violations are `super.supabaseClient` → `super.supabase` in remote
// datasource constructors. Check each parent class constructor to verify the name.

#### Step 2.8.2: Fix close_sinks (3 violations)

Ensure StreamControllers are properly closed in dispose():

```dart
@override
void dispose() {
  _controller.close();  // Add if missing
  super.dispose();
}
```

#### Step 2.8.3: Fix parameter_assignments (3 violations)

Don't reassign method parameters — use a local variable instead:

```dart
// Before:
void method(String value) {
  value = value.trim();
}
// After:
void method(String value) {
  final trimmed = value.trim();
}
```

#### Step 2.8.4: Fix avoid_catching_errors (7 violations)

Convert `.catchError()` callbacks to try/await/on Exception:

```dart
// Before:
future.catchError((e) { Logger.error('...', error: e); });

// After:
try {
  await future;
} on Exception catch (e) {
  Logger.error('...', error: e);
}
```

// NOTE: .catchError() inherently catches Object (including Error), which is why the
// lint fires. Converting to try/on Exception is the correct fix.

#### Step 2.8.5: Fix unreachable_from_main (12 violations)

For each unreachable public symbol:
- If truly unused: delete it
- If used only from tests: make it private or add `@visibleForTesting`
- If exported but unused: remove the export

#### Step 2.8.6: Fix remaining singles

- `use_if_null_to_convert_nulls_to_bools`: Replace `x == null ? false : x` with `x ?? false`
- `no_adjacent_strings_in_list` (2): Fix string list entries
- `no_literal_bool_comparisons` (2): Replace `== true`/`== false` with direct bool
- `avoid_implementing_value_types` (2): Fix test mock implementations
- `unnecessary_import` (1): Remove unused import
- `avoid_unused_constructor_parameters` (1): Remove or use the parameter

#### Step 2.8.7: Verify with flutter analyze

Expected: All remaining small rules drop to 0. Run full `flutter analyze` — should show only `cast_nullable_to_non_nullable` violations remaining.

---

## Phase 3: SafeRow Extension + SQLite Cast Fixes

### Sub-phase 3.1: Create SafeRow extension

**Files:**
- Create: `lib/shared/utils/safe_row.dart`

**Agent**: backend-data-layer-agent

#### Step 3.1.1: Create the SafeRow extension file

```dart
// WHY: SQLite queries return Map<String, Object?>. Every column access requires
// a cast from Object? to the target type, triggering cast_nullable_to_non_nullable.
// This extension provides null-checked accessors that eliminate the lint.
// NOTE: The null check promotes Object? to Object, making the subsequent cast
// from Object to T a non-nullable-to-non-nullable cast (no lint).

/// Type-safe accessors for SQLite query result rows.
///
/// Eliminates `cast_nullable_to_non_nullable` lint violations when accessing
/// SQLite query results (which return `Map<String, Object?>`).
extension SafeRow on Map<String, Object?> {
  /// Get a non-null String value. Throws [StateError] if null.
  /// Only safe for NOT NULL columns — use optionalString for nullable columns.
  String requireString(String key) {
    final value = this[key];
    if (value == null) {
      throw StateError('Expected non-null String for column "$key", got null');
    }
    return value as String;
  }

  /// Get a non-null int value. Throws [StateError] if null.
  /// Only safe for NOT NULL columns — use optionalInt for nullable columns.
  int requireInt(String key) {
    final value = this[key];
    if (value == null) {
      throw StateError('Expected non-null int for column "$key", got null');
    }
    return value as int;
  }

  /// Get a non-null double value. Throws [StateError] if null.
  /// Only safe for NOT NULL columns — use a nullable variant for nullable columns.
  double requireDouble(String key) {
    final value = this[key];
    if (value == null) {
      throw StateError('Expected non-null double for column "$key", got null');
    }
    return value as double;
  }

  /// Get an optional String value.
  String? optionalString(String key) => this[key] as String?;

  /// Get an optional int value.
  int? optionalInt(String key) => this[key] as int?;

  /// Get a non-null bool from SQLite int (0/1). Throws [StateError] if null.
  /// Only safe for NOT NULL columns.
  bool requireBool(String key) => requireInt(key) != 0;

  /// Get an optional bool from SQLite int (0/1).
  bool? optionalBool(String key) {
    final value = this[key];
    return value != null ? (value as int) != 0 : null;
  }

  /// Get an int value with a default. Common for COUNT/SUM aggregates.
  int intOrDefault(String key, [int defaultValue = 0]) {
    final value = this[key];
    return value != null ? value as int : defaultValue;
  }
}
```

### Sub-phase 3.2: Apply SafeRow across production code

**Files:**
- Modify: ~20 files in `lib/`

**Agent**: backend-data-layer-agent

#### Step 3.2.1: Replace SQLite row casts in database_service.dart (~20 violations)

```dart
import 'package:construction_inspector/shared/utils/safe_row.dart';

// Before:
final name = c['name'] as String;
final type = c['type'] as String;

// After:
final name = c.requireString('name');
final type = c.requireString('type');

// Before (aggregate):
final count = result.first['cnt'] as int;

// After:
final count = result.first.requireInt('cnt');
```

#### Step 3.2.2: Replace SQLite row casts in sync engine files

**Files:** sync_engine.dart (~9), change_tracker.dart (~6), integrity_checker.dart (~4)

Same pattern as Step 3.2.1.

#### Step 3.2.3: Replace SQLite row casts in remaining lib/ files

**Files:** schema_verifier.dart, driver_server.dart, project_lifecycle_service.dart, various local datasources (~15 violations total)

#### Step 3.2.4: Replace SQLite row casts in test files

**Files:** ~10 test files with ~40 violations. Same import + method replacement.

#### Step 3.2.5: Verify with flutter analyze

Expected: SQLite-related `cast_nullable_to_non_nullable` violations eliminated (~120 violations).

---

## Phase 4: SafeAction Mixin + Provider Refactor

// NOTE: Spec Phase 4. The catch violations in providers were already fixed mechanically
// in Phase 2.1 (bare catch -> on Exception catch). This phase refactors those same
// providers to use a shared SafeAction mixin for DRY — eliminating the duplicated
// try/catch/finally + _isLoading/_error/notifyListeners boilerplate across 30+ providers.

### Sub-phase 4.1: Create SafeAction mixin

**Files:**
- Create: `lib/shared/providers/safe_action_mixin.dart`

**Agent**: frontend-flutter-specialist-agent

#### Step 4.1.1: Create the SafeAction mixin file

```dart
// WHY: 30+ providers duplicate the same try/catch/finally + _isLoading/_error/notifyListeners
// boilerplate. This mixin standardizes the pattern and uses `on Exception catch` consistently.
// FROM SPEC: Phase 4A — "Eliminates the duplicated try/catch/finally + _isLoading/_error/
// notifyListeners block that appears across 30+ providers."

import 'package:flutter/foundation.dart';
import 'package:construction_inspector/core/logging/logger.dart';

/// Mixin for ChangeNotifier providers that provides standardized
/// error handling, loading state, and notification patterns.
mixin SafeAction on ChangeNotifier {
  bool _isLoading = false;
  String? _error;

  bool get isLoading => _isLoading;
  String? get error => _error;

  /// Wraps an async action with loading state, error handling, and notification.
  Future<bool> safeAction(String label, Future<void> Function() fn) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      await fn();
      return true;
    } on Exception catch (e) {
      _error = 'Failed to $label: $e';
      Logger.error('[$label] failed', error: e);
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Variant for actions that return a value.
  Future<T?> safeGet<T>(String label, Future<T> Function() fn) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final result = await fn();
      return result;
    } on Exception catch (e) {
      _error = 'Failed to $label: $e';
      Logger.error('[$label] failed', error: e);
      return null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
```

// NOTE: The mixin uses `on Exception catch` (not bare catch) to satisfy
// avoid_catches_without_on_clauses. Error subclasses propagate unhandled — this
// is correct for provider-level code which should never encounter Error.

### Sub-phase 4.2: Refactor providers to use SafeAction

**Files:**
- Modify: ~30 provider files

**Agent**: frontend-flutter-specialist-agent

#### Step 4.2.1: Refactor standalone providers (highest violation count first)

For each provider, add `with SafeAction` and replace the duplicated try/catch/finally blocks:

```dart
// FROM SPEC: Phase 4B exemplar

// Before (from provider-catch-pattern.md):
Future<void> loadTodos({String? projectId}) async {
  _isLoading = true;
  _error = null;
  notifyListeners();
  try {
    _todos = await _repository.getByProjectId(projectId);
  } on Exception catch (e) {
    _error = 'Failed to load todos: $e';
    Logger.ui('[Todo] $_error');
  } finally {
    _isLoading = false;
    notifyListeners();
  }
}

// After:
Future<void> loadTodos({String? projectId}) async {
  await safeAction('load todos', () async {
    _todos = await _repository.getByProjectId(projectId);
  });
}
```

// IMPORTANT: Remove duplicate `_isLoading` and `_error` field declarations from
// providers that adopt SafeAction — the mixin provides these.

**Providers to refactor (standalone, not extending BaseListProvider):**

| Provider | ~Catch Blocks | Notes |
|----------|:-------------:|-------|
| TodoProvider | 12 | Canonical exemplar |
| AuthProvider | 12 | Has `on AuthException` specific catches — keep those, use SafeAction for fallback catches only |
| EntryQuantityProvider | 11 | |
| ProjectProvider | 10 | |
| AdminProvider | 9 | |
| EquipmentProvider | 7 | |
| AppConfigProvider | 7 | |
| BidItemProvider | 4 | |
| ConsentProvider | 4 | |
| SupportProvider | 4 | |
| CalculatorProvider | 3 | |
| GalleryProvider | 1 | |

#### Step 4.2.2: Refactor BaseListProvider and its subclasses

```dart
// BaseListProvider already has _isLoading/_error — add `with SafeAction`
// and refactor loadItems/createItem/updateItem/deleteItem to use safeAction.

abstract class BaseListProvider<T> extends ChangeNotifier with SafeAction {
  // Remove duplicate _isLoading/_error fields (provided by mixin)
  // ...
}
```

**Subclasses:** ContractorProvider, LocationProvider, PhotoProvider, and others extending BaseListProvider.

#### Step 4.2.3: Skip providers with multiple loading states

// NOTE: Providers with multiple loading states (e.g., DailyEntryProvider has
// _isLoadingList + _isSaving, PhotoProvider has _isUploading) may need partial
// adoption or variants. If a provider has more than `_isLoading`/`_error`, only
// refactor methods that use the standard pattern. Leave multi-state methods as-is.

#### Step 4.2.4: Verify with flutter analyze

Run: `pwsh -Command "flutter analyze 2>&1 | Select-String 'issues found'"`
Expected: No new violations introduced. Provider catch count reduced via DRY refactoring.

---

## Phase 5: RepositoryResult.safeCall + Repository Refactor

// NOTE: Spec Phase 5. Like Phase 4, the catch violations in repositories were already
// fixed mechanically in Phase 2.1. This phase refactors those same repositories to use
// a shared `safeCall` static method for DRY — eliminating the duplicated
// try/catch + Logger.db + RepositoryResult.failure boilerplate across 10+ repositories.

### Sub-phase 5.1: Add safeCall to RepositoryResult

**Files:**
- Modify: `lib/shared/repositories/base_repository.dart`

**Agent**: backend-data-layer-agent

#### Step 5.1.1: Add safeCall static method to RepositoryResult

```dart
// WHY: 10+ repository implementations duplicate the same try/catch + Logger.db +
// RepositoryResult.failure pattern across 5-20 methods each.
// FROM SPEC: Phase 5A — "Wraps a datasource call in standardized error handling."

// Add to the existing RepositoryResult class in base_repository.dart:
/// Wraps a datasource call in standardized error handling.
///
/// Converts any [Exception] into a [RepositoryResult.failure] with logging.
/// Use for simple wrapper methods that delegate to a single datasource call.
static Future<RepositoryResult<T>> safeCall<T>(
  Future<T> Function() fn,
  String context,
) async {
  try {
    return RepositoryResult.success(await fn());
  } on Exception catch (e) {
    Logger.db('$context error: $e');
    return RepositoryResult.failure('Error in $context: $e');
  }
}
```

### Sub-phase 5.2: Refactor repositories to use safeCall

**Files:**
- Modify: ~10 repository implementation files

**Agent**: backend-data-layer-agent

#### Step 5.2.1: Refactor simple wrapper methods

For each repository method that is a pure datasource wrapper:

```dart
// FROM SPEC: Phase 5B exemplar (from repository-result-pattern.md)

// Before:
Future<RepositoryResult<List<FormResponse>>> getResponsesForForm(String formId) async {
  try {
    final responses = await _localDatasource.getByFormId(formId);
    return RepositoryResult.success(responses);
  } on Exception catch (e) {
    Logger.db('FormResponseRepository.getResponsesForForm error: $e');
    return RepositoryResult.failure('Error retrieving responses: $e');
  }
}

// After:
Future<RepositoryResult<List<FormResponse>>> getResponsesForForm(String formId) =>
  RepositoryResult.safeCall(
    () => _localDatasource.getByFormId(formId),
    'FormResponseRepository.getResponsesForForm',
  );
```

// IMPORTANT: Only refactor simple wrapper methods. Methods with validation logic
// BEFORE the datasource call (e.g., createResponse with formId/projectId checks)
// must keep their own try/catch since validation happens before the datasource call.

**Repositories to refactor:**

| Repository | ~Simple Methods | ~Complex Methods (skip) |
|------------|:--------------:|:----------------------:|
| FormResponseRepositoryImpl | 15 | 6 |
| InspectorFormRepositoryImpl | 10 | 3 |
| PhotoRepositoryImpl | 8 | 4 |
| DocumentRepository | 6 | 2 |
| EntryExportRepository | 5 | 2 |
| FormExportRepository | 4 | 1 |
| DailyEntryRepository | 5 | 3 |
| BidItemRepositoryImpl | 4 | 2 |
| EntryQuantityRepositoryImpl | 4 | 2 |
| ProjectRepositoryImpl | 3 | 4 |

#### Step 5.2.2: Verify with flutter analyze

Run: `pwsh -Command "flutter analyze 2>&1 | Select-String 'issues found'"`
Expected: No new violations introduced. Repository catch code reduced via DRY refactoring.

---

## Phase 6: CopyWith Type-Promotion Fix

### Sub-phase 6.1: Fix cast_nullable_to_non_nullable in copyWith methods

**Files:**
- Modify: ~35 model files

**Agent**: backend-data-layer-agent

// WHY: The sentinel pattern (Object? _sentinel with identical() check) triggers
// cast_nullable_to_non_nullable on `name as String`. Instead of suppressing with
// `// ignore:` comments (which the spec forbids outside Phase 1), we use a
// type-promotion helper that resolves the cast lint-free.
// FROM SPEC: "No lint rule suppression except Phase 1."

#### Step 6.1.1: Add _resolveParam helper to model files

Add a file-level private helper to each model file that uses the sentinel copyWith pattern:

```dart
/// Resolves a sentinel-guarded copyWith parameter without triggering
/// cast_nullable_to_non_nullable. Uses `is T` type promotion.
T _resolveParam<T>(Object? value) {
  if (value is T) return value;
  throw ArgumentError('copyWith: expected $T');
}
```

// NOTE: Do NOT use `${value.runtimeType}` in the error message — that would
// trigger `no_runtimetype_tostring`. The simplified message is sufficient for
// a programming error that should never occur at runtime.

#### Step 6.1.2: Replace sentinel casts in PDF extraction model copyWith methods

For each copyWith method in `lib/features/pdf/services/extraction/models/`:

```dart
// Before:
name: identical(name, _sentinel) ? this.name : name as String,

// After:
name: identical(name, _sentinel) ? this.name : _resolveParam<String>(name),
```

// NOTE: Only non-nullable target types need the helper.
// `as String?`, `as int?`, `as double?` etc. do NOT trigger the lint.
// Nullable casts remain unchanged.

**Files (~25 classes in PDF extraction models):**
- classified_rows.dart, cell_grid.dart, column_map.dart, confidence.dart
- detected_regions.dart, document_checksum.dart, document_profile.dart
- extraction_result.dart, ocr_element.dart, parsed_items.dart
- pipeline_config.dart, processed_items.dart, quality_report.dart
- sidecar.dart, stage_report.dart, extraction_pipeline.dart
- `lib/features/pdf/services/extraction/ocr/tesseract_config_v2.dart` (NOTE: in ocr/, not stages/)
- grid_lines.dart (GridLineResult — 11 sentinel usages)
- interpreted_value.dart (InterpretedValue — 5 sentinel usages)

#### Step 6.1.3: Replace sentinel casts in data model copyWith methods

**Files (~10 classes):**
- company.dart, company_join_request.dart, user_profile.dart
- calculation_history.dart, form_response.dart, inspector_form.dart
- consent_record.dart, support_ticket.dart, todo_item.dart
- schema_verifier.dart (ColumnDrift)

Also check for copyWith in:
- `lib/features/locations/data/models/location.dart`
- `lib/features/contractors/data/models/equipment.dart`
- `lib/features/contractors/data/models/contractor.dart`
- `lib/features/entries/data/models/daily_entry.dart`
- `lib/features/projects/data/models/project.dart`
- `lib/features/sync/domain/sync_types.dart`
- Any other models with the sentinel pattern

#### Step 6.1.4: Verify with flutter analyze

Expected: `cast_nullable_to_non_nullable` drops to 0 (~220 remaining violations eliminated).

### Sub-phase 6.2: Verify zero violations

**Agent**: general-purpose

#### Step 6.2.1: Run final flutter analyze

Run: `pwsh -Command "flutter analyze 2>&1"`
Expected: **0 issues found.**

If any violations remain, identify and fix them — they are edge cases missed by the categorization.

#### Step 6.2.2: Verify no behavioral regressions

Push to branch and let CI run the full test suite. The quality-gate.yml workflow will verify:
- `flutter analyze` passes (0 issues)
- `flutter test` passes (all tests green)
- Architecture validation passes
- Security scan passes

---

## Phase Summary

| Phase | Violations Fixed | Key Changes |
|-------|:----------------:|-------------|
| 1 | ~43 | Remove 2 lint rules from analysis_options.yaml |
| 2.1 | ~502 | `catch (e)` → `on Exception catch (e)` across ~155 files |
| 2.2 | ~70 | `@immutable` annotation on 35 classes |
| 2.3 | ~42 | `$runtimeType` → `StageNames.*` in 18 stage classes |
| 2.4 | ~149 | `unawaited()` wrappers + async/await conversions |
| 2.5 | ~54 | Whitespace fixes in adjacent strings |
| 2.6 | ~42 | Reason text on `// ignore:` comments |
| 2.7 | ~94 | Type casts for dynamic calls |
| 2.8 | ~28 | Small rule fixes (super params, sinks, dead code, etc.) |
| 3 | ~120 | SafeRow extension + SQLite cast replacements |
| 4 | 0 (DRY) | SafeAction mixin + provider refactor (same catches fixed in 2.1, now DRY) |
| 5 | 0 (DRY) | RepositoryResult.safeCall + repository refactor (same catches fixed in 2.1, now DRY) |
| 6 | ~220 | `_resolveParam<T>()` type-promotion helper for sentinel copyWith casts |
| **Total** | **~1054** → **0** | |

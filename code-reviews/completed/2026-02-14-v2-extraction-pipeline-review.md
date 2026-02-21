# V2 Extraction Pipeline Code Review
**Date**: 2026-02-14
**Scope**: All working tree / staged changes for v2 PDF extraction pipeline
**Focus**: DRY/KISS principles, refactor opportunities, logic soundness, duplicated code

---

## HIGH Severity (Must Fix)

### H1. `QualityReport.isValid` Contradicts `QualityValidator._determineStatus`

**Files**:
- `lib/features/pdf/services/extraction/models/quality_report.dart:40-61`
- `lib/features/pdf/services/extraction/stages/quality_validator.dart:304-307`

**Problem**: The `isValid` getter validates that score maps to status correctly, but does NOT account for the `attemptNumber >= 2` override in `QualityValidator._determineStatus`. The validator produces `partialResult` for scores in the 0.45-0.64 range when `attemptNumber >= 2`, but `isValid` expects `reExtract` for that score range. Any code calling `isValid` on a third-attempt report with a 0.50 score will get `false` -- silently marking a legitimate report as invalid.

**Fix**: Extract a single source of truth for score-to-status mapping:

```dart
class QualityThresholds {
  static const double autoAccept = 0.85;
  static const double reviewFlagged = 0.65;
  static const double reExtract = 0.45;

  static QualityStatus statusForScore(double score, {int attemptNumber = 0}) {
    if (score >= autoAccept) return QualityStatus.autoAccept;
    if (score >= reviewFlagged) return QualityStatus.reviewFlagged;
    if (score >= reExtract && attemptNumber < 2) return QualityStatus.reExtract;
    return QualityStatus.partialResult;
  }
}
```

Both `isValid` and `_determineStatus` should call this method.

---

### H2. `PipelineResult.fromMap` Creates Lossy `PipelineContext`

**File**: `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart:93-100`

**Problem**:
```dart
context: PipelineContext(
  documentId: map['document_id'] as String,
  documentHash: '',  // <-- always empty
  sidecar: Sidecar.fromMap(...),  // <-- deserialized twice (also at line 91)
  config: const PipelineConfig(),  // <-- ignores actual config used
),
```

Any code that round-trips a `PipelineResult` through `toMap()`/`fromMap()` silently loses the document hash and actual pipeline config. The `Sidecar` is also deserialized twice from the same map entry.

**Fix**: Either serialize the full context in `toMap()` and restore it in `fromMap()`, or make `context` nullable to indicate it is unavailable after deserialization.

---

### H3. `_handleEmptyItems` Always Returns `higherDpiAutoPsm` Regardless of Attempt

**File**: `lib/features/pdf/services/extraction/stages/quality_validator.dart:516-517`

**Problem**:
```dart
reExtractionStrategy: attemptNumber < 2
    ? ReExtractionStrategy.higherDpiAutoPsm  // attempt 1 AND 2 both get this
    : null,
```

When zero items are extracted on attempt 1, this returns `higherDpiAutoPsm`. On attempt 2 with zero items, it returns `higherDpiAutoPsm` again instead of escalating to `higherDpiSingleBlock`. The existing `_selectStrategy` method already handles attempt-based escalation correctly.

**Fix**: Replace with `reExtractionStrategy: _selectStrategy(attemptNumber)`.

---

### H4. `DocumentAnalyzer` vs `DocumentQualityProfiler` -- ~200 Identical Lines

**Files**:
- `lib/features/pdf/services/extraction/stages/document_analyzer.dart`
- `lib/features/pdf/services/extraction/stages/document_quality_profiler.dart`

**Problem**: `DocumentQualityProfiler` is a near-verbatim copy of `DocumentAnalyzer` with only two behavioral changes: (1) `recommendedStrategy` always returns `'ocr'`, and (2) `overallStrategy` is hardcoded to `'ocr_only'`. These methods are line-for-line identical across both files:

- `_calculateSingleCharRatio` (lines 114-123 in both)
- `_calculateCorruptionScore` (lines 135-177 in both)
- `_calculateMixedCaseScore` (lines 183-213 in both)
- `_calculateCurrencyCorruptionScore` (lines 220-262 in both)
- `_generateWarnings` (lines 266-289 in both)
- `_generateMetrics` (lines 292-311 profiler / 326-345 analyzer)
- `analyzePageText` (nearly identical except strategy return)
- `analyze` (nearly identical except strategy determination)

**Fix**: Extract a `TextQualityAnalyzer` mixin containing all corruption/quality analysis methods. Both classes mix it in, differing only in strategy determination:

```dart
// Proposed: lib/features/pdf/services/extraction/stages/text_quality_analyzer.dart
mixin TextQualityAnalyzer {
  static const int kMinCharsPerPage = 50;
  static const double kMaxSingleCharRatio = 0.30;
  static const int kCorruptionScoreThreshold = 15;

  double calculateSingleCharRatio(String text) { ... }
  int calculateCorruptionScore(String text) { ... }
  int calculateMixedCaseScore(String text) { ... }
  int calculateCurrencyCorruptionScore(String text) { ... }
  List<String> generateWarnings(List<PageProfile> pages) { ... }
  Map<String, dynamic> generateMetrics(List<PageProfile> pages) { ... }
}
```

Then `DocumentQualityProfiler` becomes ~30 lines instead of ~310. **Estimated savings: ~200 lines.**

---

### H5. `StructurePreserver` vs `ElementValidator` -- Near-Complete Duplication

**Files**:
- `lib/features/pdf/services/extraction/stages/structure_preserver.dart`
- `lib/features/pdf/services/extraction/stages/element_validator.dart`

**Problem**: `ElementValidator` is a stripped-down copy of `StructurePreserver` with native/hybrid merge logic removed. These code blocks are identical:

- Bounding box validation and clamping logic (lines 48-66 in `ElementValidator`, lines 80-99 in `StructurePreserver`)
- `_computeMedianConfidence` (lines 118-131 in `ElementValidator`, lines 187-200 in `StructurePreserver`)
- `UnifiedExtractionResult` construction pattern
- Weighted confidence calculation pattern
- StageReport construction with same metrics structure

**Fix**: Since the pipeline has migrated to OCR-only (per `DocumentQualityProfiler` comments):
1. Move `StructurePreserver` to `deprecated/`
2. `ElementValidator` becomes the single active implementation
3. Extract `_computeMedianConfidence` to a shared utility (also used in `QualityValidator` and `ColumnDetectorV2`)

**Estimated savings: ~100 lines.**

---

### H6. Three Versions of DocumentAnalyzer Exist

**Files**:
- `lib/features/pdf/services/extraction/deprecated/document_analyzer.dart` (old deprecated copy)
- `lib/features/pdf/services/extraction/stages/document_analyzer.dart` (NOT exported in barrel)
- `lib/features/pdf/services/extraction/stages/document_quality_profiler.dart` (exported in barrel)

**Problem**: The `stages.dart` barrel does NOT export `document_analyzer.dart` but the file still lives in `stages/`, creating confusion about which is the active implementation. Three files with the same core logic exist simultaneously.

**Fix**: Move `stages/document_analyzer.dart` to `deprecated/`. After H4 refactor, only `DocumentQualityProfiler` (with `TextQualityAnalyzer` mixin) remains in `stages/`.

---

## MEDIUM Severity (Should Fix)

### M1. Quality Threshold Magic Numbers Duplicated Across 3+ Files

**Files**:
- `lib/features/pdf/services/extraction/models/quality_report.dart:6-9, 44-58`
- `lib/features/pdf/services/extraction/stages/quality_validator.dart:304-307`
- `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart:34-38`

**Problem**: Thresholds 0.85, 0.65, 0.45 appear as raw literals in enum comments, `isValid`, `_determineStatus`, and confidence bucket computation.

**Fix**: Define named constants once in `QualityThresholds` (see H1 fix). All files reference the constants.

---

### M2. Duplicated Header Keyword Dictionaries

**Files**:
- `lib/features/pdf/services/extraction/stages/row_classifier_v2.dart:58-81`
- `lib/features/pdf/services/extraction/stages/column_detector_v2.dart:94-121`

**Problem**: Both stages define `_headerKeywords` with the same semantic categories (`itemNumber`, `description`, `unit`, `quantity`, `unitPrice`, `bidAmount`) and largely the same keyword lists. The column detector has extras (e.g., `'DESCRIPTION OF WORK'`) while the row classifier has `"'QUANTITY"` (with a leading quote -- likely an OCR artifact). These should be unified to prevent keyword drift.

**Fix**: Extract to `lib/features/pdf/services/extraction/shared/header_keywords.dart`:
```dart
abstract class HeaderKeywords {
  static const Map<String, List<String>> keywords = {
    'itemNumber': ['ITEM', 'ITEM NO', 'ITEM NO.', 'ITEM NUMBER', ...],
    'description': ['DESCRIPTION', 'DESCRIPTION OF WORK', ...],
    // ... unified superset
  };
}
```

**Estimated savings: ~40 lines.**

---

### M3. `_itemNumberPattern` and `_currencyPattern` Regex Duplicated with Inconsistencies

**Files**:
- `lib/features/pdf/services/extraction/stages/row_classifier_v2.dart:22-25`
- `lib/features/pdf/services/extraction/stages/column_detector_v2.dart:88-91`
- `lib/features/pdf/services/extraction/stages/row_parser_v2.dart:27-29`
- `lib/features/pdf/services/extraction/stages/post_processor_v2.dart:911`

**Problem**: `_itemNumberPattern` appears in 3-4 stages with **inconsistent** definitions:
- Row classifier: `^\d+(\.\d+)?\.?$` (allows trailing dot)
- Row parser: `^\d+(\.\d+)?$` (no trailing dot)
- Post-processor: recreates inline

This means the same text could be classified as an item number in one stage but not another.

**Fix**: Consolidate into `lib/features/pdf/services/extraction/shared/extraction_patterns.dart`:
```dart
abstract class ExtractionPatterns {
  static final itemNumber = RegExp(r'^\d+(\.\d+)?\.?$');
  static final currency = RegExp(r'\$[\d,.]+|\d+\.\d{2}');
  static final numeric = RegExp(r'\b\d{1,3}(,\d{3})*(\.\d+)?\b');
  static final total = RegExp(r'\b(TOTAL|GRAND\s+TOTAL)\b', caseSensitive: false);
}
```

**Estimated savings: ~20 lines, plus eliminates inconsistency bugs.**

---

### M4. Median Computation Duplicated 4 Times (One Is Wrong)

**Files**:
- `lib/features/pdf/services/extraction/stages/structure_preserver.dart:187-200`
- `lib/features/pdf/services/extraction/stages/element_validator.dart:118-131`
- `lib/features/pdf/services/extraction/stages/column_detector_v2.dart:1149-1157`
- `lib/features/pdf/services/extraction/stages/quality_validator.dart:241-249`

**Problem**: Four different median implementations. The column detector's is the most generic. The quality validator's is **wrong for even-length lists** -- it uses `confidences[confidences.length ~/ 2]` (floor division, returns 3rd element for 4 items) instead of averaging the two middle values.

**Fix**: Add `double median(List<double> values)` to shared math utils:
```dart
// lib/features/pdf/services/extraction/shared/math_utils.dart
double median(List<double> values) {
  if (values.isEmpty) return 0.0;
  final sorted = List<double>.from(values)..sort();
  final mid = sorted.length ~/ 2;
  if (sorted.length.isEven) {
    return (sorted[mid - 1] + sorted[mid]) / 2.0;
  }
  return sorted[mid];
}
```

**Estimated savings: ~30 lines, plus fixes the quality validator bug.**

---

### M5. StageReport Construction Boilerplate Across All 12+ Stages

**Files**: All stage files

**Problem**: Every stage repeats the same ~15 lines: capture `startTime`, compute `elapsed`, build `StageReport`. Some stages call `DateTime.now()` multiple times for `elapsed` and `completedAt`, creating slight timing inconsistencies. Additionally, `CellExtractorV2` and `RowParserV2` use `Stopwatch` while all others use `DateTime.now().difference(startTime)`.

**Fix**: Create a `StageTimer` utility:
```dart
// lib/features/pdf/services/extraction/shared/stage_timer.dart
class StageTimer {
  final DateTime _start = DateTime.now();

  StageReport report({
    required String stageName,
    required double stageConfidence,
    required int inputCount,
    required int outputCount,
    int excludedCount = 0,
    List<String> warnings = const [],
    Map<String, dynamic> metrics = const {},
  }) {
    final now = DateTime.now();
    return StageReport(
      stageName: stageName,
      elapsed: now.difference(_start),
      stageConfidence: stageConfidence,
      inputCount: inputCount,
      outputCount: outputCount,
      excludedCount: excludedCount,
      warnings: warnings,
      metrics: metrics,
      completedAt: now,
    );
  }
}
```

**Estimated savings: ~100 lines across all stages.**

---

### M6. `_generateIssues` Double-Iterates Items with `_isGarbled`

**File**: `lib/features/pdf/services/extraction/stages/quality_validator.dart:353-356`

**Problem**: Both `_generateIssues` and `_computeCoherence` iterate all items applying the same regex-based `_isGarbled` check. This is a redundant O(n) pass.

**Fix**: Return the garbled count alongside the coherence score to avoid the double pass.

---

### M7. `PipelineContext` Claims Immutability but Holds Mutable `Stopwatch`

**File**: `lib/features/pdf/services/extraction/pipeline/pipeline_context.dart:17`

**Problem**: Class doc says "Immutable context object" but `Stopwatch` is inherently mutable. The `copyWith` method shares the same instance by default. The pipeline already manages its own `Stopwatch` in `extract()`, so this field appears unused.

**Fix**: Replace with `Duration` or remove the field entirely.

---

### M8. `ExtractionMetrics` Uses Fragile String Matching Instead of `StageNames`

**File**: `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart:52-55`

**Problem**:
```dart
// Current (fragile)
r.stageName.toLowerCase().contains('document') || r.stageName.toLowerCase().contains('stage_0')
```

**Fix**: Use the existing `StageNames` constants:
```dart
r.stageName == StageNames.documentAnalysis
```

---

### M9. `PipelineConfig.operator==` Omits `duplicateSplitOverrides`

**File**: `lib/features/pdf/services/extraction/models/pipeline_config.dart:161-172`

**Problem**: Two configs with different `duplicateSplitOverrides` maps would be considered equal. The field is excluded from both `==` and `hashCode`.

**Fix**: Include `duplicateSplitOverrides` in both operators, or add a comment documenting why it's intentionally excluded.

---

### M10. Pipeline Extract Loop Exit Condition Is Over-Specified

**File**: `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart:295-304`

**Problem**: The loop checks three statuses to decide to exit, but the only status that should continue is `reExtract`.

**Fix**: Simplify to:
```dart
if (status != QualityStatus.reExtract) {
  totalStopwatch.stop();
  return bestAttempt;
}
```

---

### M11. `DocumentAnalyzer`/`DocumentQualityProfiler` Create `PdfTextExtractor` Per Page

**Files**:
- `lib/features/pdf/services/extraction/stages/document_analyzer.dart:37`
- `lib/features/pdf/services/extraction/stages/document_quality_profiler.dart:46`

**Problem**: `PdfTextExtractor(document)` is created inside the page loop on every iteration. Compare with `NativeExtractor` which correctly creates the extractor once before the loop (line 57). `PdfTextExtractor` is stateless.

**Fix**: Move `final textExtractor = PdfTextExtractor(document);` before the loop.

---

### M12. `RowParserV2._mapColumnSemantics` Re-implements Header Matching

**File**: `lib/features/pdf/services/extraction/stages/row_parser_v2.dart:399-445`

**Problem**: This method re-implements header-to-semantic mapping using `contains()` checks that overlap with keyword dictionaries in `RowClassifierV2` and `ColumnDetectorV2`, but with less precision. For example, `headerText.contains('UNIT') && !headerText.contains('PRICE')` could match `'UNIT BID PRICE'` incorrectly.

**Fix**: Use the shared `HeaderKeywords` class (from M2) and existing `_matchesKeyword` logic. The semantic name should already be set by `ColumnDetectorV2`.

---

### M13. `ExtractionMetrics.recordRun` Ignores Available `expectedItemCount`

**File**: `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart:103`

**Problem**: The line `'items_expected': null` ignores `result.context.config.expectedItemCount` which is available and should be recorded.

**Fix**: Use `result.context.config.expectedItemCount`.

---

## LOW Severity (Nice to Have)

### L1. `_inferMissingColumns` Uses `firstWhere` Without `orElse`

**File**: `lib/features/pdf/services/extraction/stages/column_detector_v2.dart:1054-1058`

**Problem**: Uses try/catch around `columns.firstWhere(...)` instead of `.where(...).firstOrNull`. Violates project anti-patterns in `architecture.md`.

**Fix**: Replace with `columns.where((c) => c.headerText == 'unit').firstOrNull`.

---

### L2. `_Gap.center` Field Is Never Read

**File**: `lib/features/pdf/services/extraction/stages/column_detector_v2.dart:1204-1214`

**Problem**: Dead field -- computed but never accessed.

**Fix**: Remove the `center` field from `_Gap`.

---

### L3. Dummy `OcrElement` Objects for X-Overlap Computation

**File**: `lib/features/pdf/services/extraction/stages/column_detector_v2.dart:654-677, 701-725`

**Problem**: Full `OcrElement` instances are created just to call `_computeXOverlap`. The method only needs coordinates.

**Fix**: Refactor `_computeXOverlap` to accept `Rect` or raw `double` parameters.

---

### L4. `QualityReport.operator==` and `PipelineResult.operator==` Only Check `documentId`

**Files**:
- `lib/features/pdf/services/extraction/models/quality_report.dart:130-132`
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart:114-116`

**Problem**: Multiple results for the same document across attempts would compare as equal.

**Fix**: Include `attemptNumber` (and optionally `overallScore`) in equality checks, or document why only `documentId` is used.

---

### L5. `_recordStageMetrics` Inserts Rows Sequentially

**File**: `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart:127-139`

**Problem**: Individual inserts instead of batch for 12+ rows per run.

**Fix**: Use `_db.batch()` for minor performance improvement.

---

### L6. God Class Concerns

**Files**:
- `lib/features/pdf/services/extraction/stages/column_detector_v2.dart` (1215 lines)
- `lib/features/pdf/services/extraction/stages/post_processor_v2.dart` (1261 lines)

**Problem**: Both files are large enough to warrant decomposition. `ColumnDetectorV2` has three detection layers (header, text alignment, whitespace gap) + anchor correction. `PostProcessorV2` has six phases (normalization, splitting, consistency, deduplication, validation, checksum).

**Fix**: Future refactor -- extract phases into separate strategy/helper classes.

---

## TEST-SPECIFIC Findings

### T1. [HIGH] Five Deprecated Test Files (~1,800 Lines of Dead Tests)

**Files**:
- `test/features/pdf/extraction/contracts/stage_0_to_2_contract_test.dart`
- `test/features/pdf/extraction/stages/document_analyzer_integration_test.dart`
- `test/features/pdf/extraction/stages/stage_0_document_analyzer_test.dart`
- `test/features/pdf/extraction/stages/stage_2a_native_extractor_test.dart`
- `test/features/pdf/extraction/stages/stage_3_structure_preserver_test.dart`

**Problem**: All import from `deprecated/` and test dead code paths. They slow CI and create false confidence in coverage.

**Fix**: Delete them entirely, or exclude from CI with `@Tags(['deprecated'])`.

---

### T2. [HIGH] 13 Mock Stage Classes Inline in One Test File (484 Lines)

**File**: `test/features/pdf/extraction/pipeline/re_extraction_loop_test.dart:282-765`

**Problem**: 484 lines of mock stage implementations defined inline.

**Fix**: Extract to `test/features/pdf/extraction/helpers/mock_stages.dart` for reuse.

---

### T3. [MEDIUM] `test_fixtures.dart` Exists But Is Under-Adopted

**File**: `test/features/pdf/extraction/helpers/test_fixtures.dart`

**Problem**: Shared helpers like `testOcrCoordinates()`, `testOcrElement()`, `testParsedBidItem()` exist but are NOT used by most test files. Instead:
- `CoordinateMetadata` boilerplate appears 20+ times across contract tests
- `OcrElement` factory independently defined in 3 files (`_createOcrElement`, `_createMockElement`, inline)
- `DocumentProfile`/`PageProfile` construction duplicated in 4+ files
- `PipelineContext` + `Sidecar` boilerplate repeated 10+ times
- `ParsedBidItem` factory in `stage_6_quality_validation_test.dart:1609` nearly duplicates `testParsedBidItem()` in test_fixtures

**Fix**: Migrate all test files to use `test_fixtures.dart` helpers. Add missing factories for `DocumentProfile`, `PageProfile`, `PipelineContext`, and `Sidecar`.

---

## Estimated Impact Summary

| Category | Refactor | Est. Lines Saved |
|----------|----------|------------------|
| **HIGH -- Bugs** | H1 (isValid mismatch), H2 (lossy fromMap), H3 (wrong strategy) | ~30 (fixes, not removals) |
| **HIGH -- DRY** | H4 (TextQualityAnalyzer mixin) | ~200 |
| **HIGH -- DRY** | H5 (deprecate StructurePreserver) | ~100 |
| **HIGH -- DRY** | H6 (move DocumentAnalyzer to deprecated/) | ~0 (file move) |
| **MEDIUM -- Shared Utils** | M1-M4 (QualityThresholds, HeaderKeywords, ExtractionPatterns, median) | ~90 |
| **MEDIUM -- Shared Utils** | M5 (StageTimer) | ~100 |
| **MEDIUM -- Logic** | M6-M13 (assorted fixes) | ~50 |
| **TEST -- Cleanup** | T1 (delete deprecated tests) | ~1,800 |
| **TEST -- DRY** | T2 (extract mock stages) | ~200 |
| **TEST -- DRY** | T3 (adopt test_fixtures.dart) | ~775 |
| **TOTAL** | | **~3,345 lines** |

---

## Recommended Implementation Order

### Phase 1: Fix Bugs (H1, H2, H3)
Correctness issues that affect runtime behavior. Small, targeted changes.

### Phase 2: Create Shared Utilities (M1, M3, M4)
`QualityThresholds`, `ExtractionPatterns`, `median()` -- these are dependencies for later phases.

### Phase 3: Major Dedup (H4, H5, H6)
Extract `TextQualityAnalyzer` mixin, deprecate `StructurePreserver` and `DocumentAnalyzer`. Largest code reduction.

### Phase 4: Stage Utilities (M2, M5, M8, M10-M12)
`HeaderKeywords`, `StageTimer`, and assorted medium fixes across stages.

### Phase 5: Pipeline Core Cleanup (M6, M7, M9, M13, L4, L5)
Remaining model/pipeline fixes.

### Phase 6: Test Cleanup (T1, T2, T3)
Delete deprecated tests, extract mock stages, adopt shared fixtures.

### Phase 7: Low Priority (L1-L3, L6)
Dead code removal, API cleanup, God Class decomposition planning.

---

## Positives Worth Preserving

- **Excellent stage isolation** -- typed inputs/outputs, no hidden mutable state
- **Strong data conservation invariant** -- `outputCount + excludedCount == inputCount` with `StateError` enforcement
- **Sophisticated corruption detection** -- CMap analysis with mixed-case scoring and currency symbol validation
- **Three-tier column matching** in `CellExtractorV2` with orphan preservation
- **Anchor-based per-page correction** with MAD outlier rejection
- **`StageNames` constants** preventing stringly-typed errors
- **Contract test pattern** (stage-to-stage validation) is architecturally sound
- **Three-layer golden test strategy** (regression, ground truth, convergence)
- **`test_fixtures.dart`** is well-structured -- needs wider adoption, not replacement

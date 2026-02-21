# PDF Extraction Pipeline Refactor Plan

**Date**: 2026-02-20
**Catalog Source**: `.claude/code-reviews/2026-02-20-master-refactor-catalog.md`
**Scope**: PDF extraction pipeline (14 items: P-01 through P-13)
**Context Gathered**: 3 parallel agents + git log + direct file reads (2026-02-20)

---

## Context & Key Findings

The PDF extraction pipeline has 86 files (~21,753 lines). The catalog was written weeks ago — several items have already been resolved:

| Catalog Item | Status |
|---|---|
| "3 orphaned V1 stage files" (document_analyzer, native_extractor, structure_preserver) | **Already deleted** (commit `5bab520`) |
| RowParserV2 | **Already replaced** by V3 (commit `4b9ef77`) |
| 5 "deprecated code" test files (stage_0, stage_2a, stage_3) | **Already cleaned up** — don't exist |
| P-10: `_median` duplication | **Already resolved** — all copies delegate to `MathUtils.median()`, no inline duplication |

**Remaining scope is 11 active items** (P-01 through P-09, P-11 through P-13).

---

## Architecture Decisions (from brainstorming session)

### Fixture Emission Pattern
**Decision: Option B — each sub-class emits its own fixture file.**

Rationale: This matches the existing pattern exactly. PostProcessorV2 phases already have individual fixture files (`springfield_post_normalize.json`, `springfield_post_split.json`, `springfield_post_validate.json`, `springfield_post_sequence_correct.json`, `springfield_post_deduplicate.json`). ColumnDetectorV2 has an aggregated `springfield_column_detection_layers.json` — this will be split into per-layer files following the same precedent.

New fixture files to add (one per extracted sub-component):

| Sub-Component | Fixture File |
|---|---|
| GridLineColumnDetector | `springfield_grid_line_column_detection.json` |
| HeaderDetector | `springfield_header_detection.json` |
| TextAlignmentDetector | `springfield_text_alignment_detection.json` |
| WhitespaceGapDetector | `springfield_whitespace_gap_detection.json` |
| AnchorCorrector | `springfield_anchor_correction.json` |

PostProcessorV2 per-phase fixture slots already exist — implementation just needs to populate assertions in `stage_trace_diagnostic_test.dart`.

### ColumnDetectorV2 Sub-Component Design
**Decision: Injectable sub-components managed by the orchestrator.**

- `ColumnDetectorV2` constructor gains optional parameters: `GridLineColumnDetector?`, `HeaderDetector?`, `TextAlignmentDetector?`, `WhitespaceGapDetector?`, `AnchorCorrector?`
- All default to `null` → orchestrator instantiates defaults internally
- `ExtractionPipeline` interface is **completely unchanged** — it still calls `ColumnDetectorV2()` or injects a custom one as today
- Sub-components are independently testable and mockable
- Follows the same injection pattern as `ExtractionPipeline` itself (18 stages, all optional with defaults)

### PostProcessorV2 Sub-Component Design
**Decision: Pure static utility classes.**

All `PostProcessorV2` methods except `process()` are already `static`. Phase classes become all-static namespaces. The `process()` orchestrator calls `ValueNormalizer.normalize(item)`, `RowSplitter.apply(item, batchAnalysis)`, etc. No constructor changes needed anywhere.

### Stage Trace Test
**Decision: Do not refactor `stage_trace_diagnostic_test.dart` now.**

The file is large (~50k tokens) because it is wide (many stages), not because any section is a god class. The right action is to add new fixture slots for sub-components as they are extracted. The test will naturally grow in meaningful ways. Splitting into stage-group files is a future concern when individual sections exceed ~200 lines of assertions.

---

## Phase 0: Quick Wins (No-Risk, No Dependencies)

These three items are trivially safe and should be done first to build momentum.

### P-01: Delete RowClassifierV2 (951 lines confirmed dead)

**Evidence of dead code:**
- `row_classifier_v2.dart` is NOT in the stages barrel export (`stages/stages.dart`)
- `ExtractionPipeline` uses `RowClassifierV3` at line 159: `final RowClassifierV3 rowClassifier;`
- Only 1 production import of V2 found: `stage_4a_row_classifier_test.dart` (test file, not production code)

**Files to modify:**
1. **Delete**: `lib/features/pdf/services/extraction/stages/row_classifier_v2.dart` (951 lines)
2. **Delete or rewrite**: `test/features/pdf/extraction/stages/stage_4a_row_classifier_test.dart`
   - This file tests `RowClassifierV2`. Since V2 is dead, delete the test file entirely.
   - `RowClassifierV3` already has its own test: `row_classifier_v3_test.dart`
3. **Update**: `test/features/pdf/extraction/contracts/stage_4a_to_4b_contract_test.dart`
   - This references RowClassifierV2 output as input to RegionDetectorV2
   - Update to use `RowClassifierV3` output format — check that the typed contract is still valid with V3

**Verification**: `flutter analyze` → zero errors. `flutter test test/features/pdf/` → all pass.

---

### P-02: Fix firstWhere Crash (Confirmed Critical Bug)

**Location**: `lib/features/pdf/services/extraction/stages/post_processor_v2.dart:369-371`

**Current (crashes)**:
```dart
final originalItem = input.items.firstWhere(
  (item) => item.itemNumber == removedId,
);
```

**Context**: After deduplication, `_deduplicate()` builds a sidecar of removed items. It looks up the original item by `itemNumber`. But `_correctItemNumbersFromSequence()` runs BEFORE deduplication and may have rewritten `itemNumber` values — so the original `removedId` may no longer match any item in `input.items`. The lookup crashes with `StateError`.

**Fix**:
```dart
final originalItem = input.items
    .where((item) => item.itemNumber == removedId)
    .firstOrNull;
if (originalItem == null) continue; // item was sequence-corrected away, skip sidecar entry
```

**Note**: `firstOrNull` requires `import 'package:collection/collection.dart'` or use the extension from the existing codebase — check what's already imported in the file.

**Verification**: `flutter test test/features/pdf/extraction/stages/stage_5_post_processing_test.dart`

---

### P-06: Extract Duplicate Column Ratio Constants

**Location**: Two identical `Map<String, double>` definitions:
- `ExtractionPipeline._provisionalColumnRatios` (lines 142-149)
- `ColumnDetectorV2._fallbackRatios` (lines 107-114)

Both define:
```dart
{
  'itemNumber': 0.08,
  'description': 0.42,
  'unit': 0.10,
  'quantity': 0.12,
  'unitPrice': 0.14,
  'bidAmount': 0.14,
}
```

**Fix**: Extract to `lib/features/pdf/services/extraction/shared/pipeline_constants.dart`:
```dart
/// Default column width ratios used when detection fails or as provisional values.
/// Sum = 1.0. Used by both ExtractionPipeline (provisional) and ColumnDetectorV2 (fallback).
const Map<String, double> kDefaultColumnRatios = {
  'itemNumber': 0.08,
  'description': 0.42,
  'unit': 0.10,
  'quantity': 0.12,
  'unitPrice': 0.14,
  'bidAmount': 0.14,
};
```

Replace both usages with `kDefaultColumnRatios`.

**Verification**: `flutter analyze` → zero errors.

---

## Phase 1: PostProcessorV2 Decomposition (P-04)

**Current state**: 1,509 lines, `process()` is 391-line orchestrator. All other methods are already `static`. Per-phase fixture files already exist but the diagnostic test has no assertions for them yet.

**Self-aware TODO** (lines 20-25):
```
TODO(refactor): Consider decomposing into:
- ValueNormalizer (Phase 2)
- RowSplitter (Phase 3)
- ConsistencyChecker (Phase 4)
- ItemDeduplicator (Phase 5)
with PostProcessorV2 as the orchestrator.
```

### New Files

All new files live in: `lib/features/pdf/services/extraction/stages/`

#### `value_normalizer.dart`

Owns Phase 2 logic from `PostProcessorV2`:
- `static NormalizedItem normalize(ParsedBidItem item, {required RepairLog repairLog})` — wraps `_normalizeItem()`
- Move `_normalizeItem()` (lines 432-563, 132 lines) here
- Depends on: `PostProcessUtils`, `ParsedBidItem`, `RepairLog`

**Fixture emission**: Writes per-item normalization result to `springfield_post_normalize.json` (already loaded in trace test, needs assertion population).

#### `row_splitter.dart`

Owns Phase 3 split logic:
- `static SplitResult apply(ParsedBidItem item, BatchAnalysis batchAnalysis)` — wraps `_applySplitting()`
- Move `_applySplitting()` (lines 566-612, 47 lines) + `_shouldApplyColumnShift()` (lines 929-948, 20 lines)
- Depends on: `ParsedBidItem`, `BatchAnalysis`, `RepairLog`

**Fixture emission**: Writes to `springfield_post_split.json`.

#### `consistency_checker.dart`

Owns Phase 3 consistency + Phase 4 math validation:
- `static ConsistencyResult applyConsistency(ParsedBidItem item, {required RepairLog repairLog})` — wraps `_applyConsistencyRules()`
- `static MathValidationResult validateMath(List<ParsedBidItem> items)` — wraps `_validateMath()`
- Move `_applyConsistencyRules()` (lines 620-758, 139 lines) + `_validateMath()` (lines 1043-1103, 61 lines)
- Move internal types: `_MathValidationResult`, `_MathValidationStatus`, `_MathValidationItem` — make them non-private since they move to their own file

**Fixture emission**: Writes to `springfield_post_validate.json`.

#### `item_deduplicator.dart`

Owns Phase 5 dedup + sequence correction:
- `static DeduplicationResult deduplicate(List<ParsedBidItem> items, {required RepairLog repairLog})` — wraps `_deduplicate()`
- `static SequenceCorrectionResult correctSequence(List<ParsedBidItem> items, {required int? expectedCount})` — wraps `_correctItemNumbersFromSequence()`
- `static SequenceValidationResult validateSequence(List<ParsedBidItem> items)` — wraps `_validateSequence()`
- Move `_deduplicate()` (761-835), `_correctItemNumbersFromSequence()` (951-1005), `_validateSequence()` (838-876), `_computeCompleteness()` (1008-1040), `_analyzeBatch()` (879-926)
- Move internal type: `_BatchAnalysis`, `_BidItemCompleteness` — make non-private

**Fixture emission**: Writes to `springfield_post_deduplicate.json` and `springfield_post_sequence_correct.json`.

### PostProcessorV2 After Decomposition

The `process()` orchestrator (lines 39-429) remains in `post_processor_v2.dart` but becomes ~150 lines of orchestration logic that calls into the 4 phase classes. All the private methods that were moved are deleted. Private helpers that are purely internal to the orchestrator (`_recalculateConfidence`, `_computeFieldConfidence`, `_reconcileWarnings`, `_buildPostStageSnapshot`, `_computeRepairStats`, `_computeChecksum`) stay in `PostProcessorV2`.

### Stage Trace Test Additions

In `stage_trace_diagnostic_test.dart`, populate assertions for the already-loaded nullable fixtures:
- `postNormalizeJson` — assert per-item description cleaning, unit normalization
- `postSplitJson` — assert column shift detection rate, items affected count
- `postValidateJson` — assert math validation rate, items with discrepancies
- `postSequenceCorrectJson` — assert corrections applied count
- `postDeduplicateJson` — assert duplicates removed count, sidecar entries

### Barrel Export Update

Add to `stages/stages.dart`:
```dart
export 'value_normalizer.dart';
export 'row_splitter.dart';
export 'consistency_checker.dart';
export 'item_deduplicator.dart';
```

**Verification**: `flutter test test/features/pdf/extraction/stages/stage_5_post_processing_test.dart` + `flutter test test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`

---

## Phase 2: ColumnDetectorV2 Decomposition (P-03)

**Current state**: 1,948 lines, `detect()` is 346-line orchestrator. 5 detection layers clearly bounded with names matching the self-aware TODO. 6 internal helper types defined at bottom of file.

**Self-aware TODO** (lines 11-16):
```
TODO(refactor): Consider decomposing into:
- HeaderDetector (Layer 1)
- TextAlignmentDetector (Layer 2)
- WhitespaceGapDetector (Layer 2b)
- AnchorCorrector (Layer 3)
with ColumnDetectorV2 as the orchestrator.
```

The TODO does not name Layer 0 — it should be `GridLineColumnDetector`.

### New Files

All new files live in: `lib/features/pdf/services/extraction/stages/`

#### `grid_line_column_detector.dart` (Layer 0)

```dart
class GridLineColumnDetector {
  Future<GridLineColumnResult> detect({
    required DetectedRegions detectedRegions,
    required ClassifiedRows classifiedRows,
    required UnifiedExtractionResult extractionResult,
    required GridLines gridLines,
  }) async { ... }
}
```

Moves from `ColumnDetectorV2`:
- `_detectFromGridLines()` (lines 474-724, 251 lines)
- `_propagateGridPageLabels()` (lines 726-826, 101 lines)
- `_borrowLayer1SemanticsForWeakGridPages()` (lines 828-875, 48 lines)
- `_selectBestGridPage()` (lines 877-898, 22 lines)
- `_gridLayerConfidenceForMatches()` (lines 900-908, 9 lines)
- `_collectColumnHeaderText()` (lines 910-928, 19 lines)
- `_identifySemanticFromHeaderText()` (lines 930-947, 18 lines)
- `_bestSemanticOverlap()` (lines 949-977, 29 lines)
- `_computeBoundaryAgreement()` (lines 979-1020, 42 lines)
- `_computeSemanticAgreement()` (lines 1022-1046, 25 lines)
- `_computeMaxBoundaryOffset()` (lines 1048-1061, 14 lines)

Internal types owned: `_GridLayerResult`, `_PageAnchors`

**Fixture**: `springfield_grid_line_column_detection.json` — layer 0 column boundaries per page, confidence, semantic matches

#### `header_detector.dart` (Layer 1)

```dart
class HeaderDetector {
  HeaderDetectionResult detect({
    required DetectedRegions detectedRegions,
    required ClassifiedRows classifiedRows,
  });
}
```

Moves from `ColumnDetectorV2`:
- `_detectFromHeaders()` (lines 1067-1209, 143 lines)
- `_combineMultiRowHeaders()` (lines 1211-1259, 49 lines)
- `_matchesKeyword()` (lines 1261-1279, 19 lines)
- `_computeXOverlap()` (lines 1285-1292, 8 lines)
- `_computeXOverlapFromCoords()` (lines 1294-1310, 17 lines)

Internal types owned: `_CombinedHeader`, `_HeaderDetectionResult`

**Fixture**: `springfield_header_detection.json` — detected headers, keyword matches, column boundaries from Layer 1

#### `text_alignment_detector.dart` (Layer 2)

```dart
class TextAlignmentDetector {
  TextAlignmentResult detect({
    required DetectedRegions detectedRegions,
    required ClassifiedRows classifiedRows,
    List<ColumnBoundary>? headerColumns, // from Layer 1, for cross-validation boost
  });
}
```

Moves from `ColumnDetectorV2`:
- `_detectFromTextAlignment()` (lines 1325-1472, 148 lines)

**Fixture**: `springfield_text_alignment_detection.json` — cluster positions, elements per cluster, confidence, cross-validation result

#### `whitespace_gap_detector.dart` (Layer 2b)

```dart
class WhitespaceGapDetector {
  WhitespaceGapResult detect({
    required DetectedRegions detectedRegions,
    required ClassifiedRows classifiedRows,
  });
}
```

Moves from `ColumnDetectorV2`:
- `_detectFromWhitespaceGaps()` (lines 1487-1641, 155 lines)

Internal types owned: `_Gap`

**Fixture**: `springfield_whitespace_gap_detection.json` — histogram bin counts, detected gaps, column boundaries from Layer 2b

#### `anchor_corrector.dart` (Layer 3)

```dart
class AnchorCorrector {
  AnchorCorrectionResult correct({
    required List<ColumnBoundary> inputColumns,
    required ClassifiedRows classifiedRows,
    required DetectedRegions detectedRegions,
  });
}
```

Moves from `ColumnDetectorV2`:
- `_correctWithAnchors()` (lines 1652-1785, 134 lines)
- `_inferMissingColumns()` (lines 1791-1837, 47 lines)

**Fixture**: `springfield_anchor_correction.json` — per-page anchor positions, offset/scale corrections applied, final column boundaries

### ColumnDetectorV2 After Decomposition

Constructor becomes:
```dart
ColumnDetectorV2({
  GridLineColumnDetector? gridLineDetector,
  HeaderDetector? headerDetector,
  TextAlignmentDetector? textAlignmentDetector,
  WhitespaceGapDetector? whitespaceGapDetector,
  AnchorCorrector? anchorCorrector,
}) : _gridLineDetector = gridLineDetector ?? GridLineColumnDetector(),
     _headerDetector = headerDetector ?? HeaderDetector(),
     _textAlignmentDetector = textAlignmentDetector ?? TextAlignmentDetector(),
     _whitespaceGapDetector = whitespaceGapDetector ?? WhitespaceGapDetector(),
     _anchorCorrector = anchorCorrector ?? AnchorCorrector();
```

The `detect()` method shrinks from 346 lines to ~80 lines: it calls each layer in sequence, collects results, applies the layer-selection and fallback logic, and calls `_buildFallbackResult()` / `_buildFallbackColumns()` (which stay in the orchestrator since they depend on `kDefaultColumnRatios`).

`ExtractionPipeline` is **unchanged** — it still constructs `ColumnDetectorV2()` with no arguments.

### Internal Helper Types

The 6 internal types at the bottom of `column_detector_v2.dart` (`_CombinedHeader`, `_HeaderDetectionResult`, `_GridLayerResult`, `_PageAnchors`, `_Gap`, and any unnamed helpers) move to their owning sub-class file. They become package-private (non-underscore prefix) since they cross file boundaries within the same feature.

### Stage Trace Test Additions

Add new fixture slots in `stage_trace_diagnostic_test.dart` `setUpAll` block:
```dart
Map<String, dynamic>? gridLineColumnDetectionJson;
Map<String, dynamic>? headerDetectionJson;
Map<String, dynamic>? textAlignmentDetectionJson;
Map<String, dynamic>? whitespaceGapDetectionJson;
Map<String, dynamic>? anchorCorrectionJson;
```

Each loaded with the optional pattern (existing `springfield_column_detection_layers.json` can remain for backwards compatibility or be retired in favor of the 5 per-layer files).

Add assertions for:
- `headerDetectionJson` — keyword matches found, header column count
- `gridLineColumnDetectionJson` — grid pages detected, semantic matches
- `anchorCorrectionJson` — pages corrected, average offset

### Barrel Export Update

Add to `stages/stages.dart`:
```dart
export 'grid_line_column_detector.dart';
export 'header_detector.dart';
export 'text_alignment_detector.dart';
export 'whitespace_gap_detector.dart';
export 'anchor_corrector.dart';
```

**Verification**: `flutter test test/features/pdf/extraction/stages/stage_4c_column_detector_test.dart` + full pipeline test

---

## Phase 3: ExtractionPipeline (P-05)

**Current state**: `_runExtractionStages()` is 563 lines (lines 378-940). The synthetic region merge logic is the most complex extracted section.

### Extract SyntheticRegionBuilder

**New file**: `lib/features/pdf/services/extraction/pipeline/synthetic_region_builder.dart`

```dart
class SyntheticRegionBuilder {
  /// Builds synthetic TableRegions from grid-line geometry for pages with
  /// clear horizontal/vertical grid lines. Returns null if document has
  /// insufficient grid data for synthesis.
  static SyntheticRegionResult? buildFromGridLines({
    required GridLines gridLines,
    required ClassifiedRows classifiedRows,
    required DetectedRegions detectedRegions,
  });
}
```

Moves from `ExtractionPipeline`:
- `_createSyntheticRegions()` (lines 1010-1110, 101 lines) — pure geometric synthesis
- The ~200-line Stage 4B merge block (lines 599-822) that merges synthetic + detector regions, validates data conservation, and builds the decision trace

**Fixture**: No new fixture — the existing `springfield_detected_regions.json` captures the final merged result. Add a diagnostic key `synthetic_region_summary` within it (count of synthetic pages, count of detector pages).

### Remaining `_runExtractionStages` Reduction

After extracting `SyntheticRegionBuilder`, `_runExtractionStages` shrinks from 563 to ~380 lines. At that size it does not warrant further splitting — it is a straight-line stage sequence with no conditional logic between stages.

**Verification**: `flutter test test/features/pdf/extraction/pipeline/extraction_pipeline_test.dart`

---

## Phase 4: Cross-Cutting Smaller Items

### P-07: Row Grouping Utilities from RowClassifierV3

**After P-01 (V2 deletion)**, check `row_classifier_v3.dart` (741 lines) for any row-grouping utility methods that were duplicated with V2. If any remain isolated in V3 but are conceptually general, extract to `lib/features/pdf/services/extraction/shared/row_grouping_utils.dart`. If V3's utilities are tightly coupled to V3's internal state, skip — don't extract for its own sake.

**Decision gate**: Only extract if 2+ callers exist or extraction improves testability. Do not create a single-use utility.

### P-08: `columnsForPage()` to ColumnMap Model

**Current**: `columnsForPage()` defined only in `row_classifier_v3.dart`.

**Check first**: The catalog said this was duplicated in `cell_extractor_v2.dart` as well. Agent finding showed it exists only in `row_classifier_v3.dart`. Verify via `flutter analyze` / grep before moving. If it's a single definition, moving it to `ColumnMap` model is still appropriate since it's semantically a model operation — but it's low priority. If it's truly singular, skip.

**If moving**: Add method to `lib/features/pdf/services/extraction/models/column_map.dart` and update `row_classifier_v3.dart` to call `columnMap.columnsForPage(pageIndex)` instead of its own method.

### P-09: Shared Keyword Matching

**Current**: Keyword matching logic exists in:
1. `ColumnDetectorV2._matchesKeyword()` (will move to `HeaderDetector` in Phase 2)
2. `RowClassifierV3` (verify this — catalog said 3 implementations, agent confirmed V2 deletion removes one)

**After P-01 and Phase 2**: There will be 1 implementation in `HeaderDetector` and potentially 1 in `RowClassifierV3`. If they are functionally identical, extract to `lib/features/pdf/services/extraction/shared/keyword_matcher.dart`:
```dart
class KeywordMatcher {
  static bool matches(String text, List<String> keywords);
}
```

If they differ (different word-boundary rules or tolerances), keep them separate. Do not force unification.

### P-11: Extract `_CropOcrStats` to Own File

**Location**: `text_recognizer_v2.dart` (932 lines) — `_CropOcrStats` is a 190-line stats accumulator class at the bottom of the file.

**New file**: `lib/features/pdf/services/extraction/ocr/crop_ocr_stats.dart`

Remove underscore prefix (it becomes package-visible). Update import in `text_recognizer_v2.dart`.

**Verification**: `flutter test test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart`

### P-12: Data-Drive Encoding Corruption Rules

**Location**: `post_process_utils.dart:25-151` — `cleanDescriptionArtifacts()` is 127 lines with 12+ sequential regex patterns applied in hardcoded order.

**Goal**: Replace hardcoded sequential application with a data-driven list:

```dart
const List<ArtifactCleaningRule> _artifactRules = [
  ArtifactCleaningRule(
    name: 'pipe_removal',
    pattern: r'\|',
    replacement: '',
  ),
  ArtifactCleaningRule(
    name: 'ln_to_in_corruption',
    pattern: r'\bln([a-z])',
    replacement: 'In$1',
    description: '"lnsurance" → "Insurance"',
  ),
  // ... all 12+ rules
];
```

This makes rules individually testable, nameable, and extensible without touching code. The method body becomes a loop over `_artifactRules`.

**New type**: `ArtifactCleaningRule` class in same file or in `shared/artifact_cleaning_rule.dart` if it grows.

**Note**: The ordering of rules is semantically significant (some rules must run before others). Preserve exact order. Add comments explaining any ordering dependencies.

**Verification**: `flutter test test/features/pdf/extraction/stages/stage_5_post_processing_test.dart` (PostProcessUtils is called from PostProcessorV2)

### P-13: Extract Shared OcrTextExtractor for M&P

**Current**: `MpExtractionService` (509 lines) runs stages 0, 2B-i, 2B-ii, 2B-iii with direct instantiation:
```dart
DocumentQualityProfiler(), PageRendererV2(), ImagePreprocessorV2(), TextRecognizerV2(), TesseractEngineV2()
```

This is a simplified version of ExtractionPipeline's OCR stages without the classification/column/post-processing stages.

**New file**: `lib/features/pdf/services/extraction/pipeline/ocr_text_extractor.dart`

```dart
/// Lightweight OCR-only pipeline for documents that don't need full table extraction.
/// Used by MpExtractionService and potentially future simplified extractors.
class OcrTextExtractor {
  OcrTextExtractor({
    DocumentQualityProfiler? profiler,
    PageRendererV2? renderer,
    ImagePreprocessorV2? preprocessor,
    TextRecognizerV2? recognizer,
  });

  Future<OcrExtractionResult> extract({
    required Uint8List pdfBytes,
    required String documentId,
    PipelineConfig config = const PipelineConfig(),
  });
}
```

`MpExtractionService` then uses `OcrTextExtractor` instead of directly instantiating stages. This establishes a reusable base for any future non-table extraction needs.

**Verification**: `flutter test test/features/pdf/services/mp/mp_extraction_service_test.dart`

---

## Test Debt Cleanup (Alongside Phase 0)

| Test File | Action |
|---|---|
| `stage_4a_row_classifier_test.dart` | Delete (tests dead RowClassifierV2) |
| `stage_4a_to_4b_contract_test.dart` | Update — replace V2 reference with V3 output format |

No other deprecated test files exist (stage_0, stage_2a, stage_3 tests were already cleaned up).

---

## File Inventory Summary

### New Files (14)

| File | Phase | Purpose |
|---|---|---|
| `shared/pipeline_constants.dart` | P-06 | Shared `kDefaultColumnRatios` |
| `stages/value_normalizer.dart` | P-04 | PostProcessor Phase 2 |
| `stages/row_splitter.dart` | P-04 | PostProcessor Phase 3 split |
| `stages/consistency_checker.dart` | P-04 | PostProcessor Phase 3 consistency + Phase 4 math |
| `stages/item_deduplicator.dart` | P-04 | PostProcessor Phase 5 |
| `stages/grid_line_column_detector.dart` | P-03 | ColumnDetector Layer 0 |
| `stages/header_detector.dart` | P-03 | ColumnDetector Layer 1 |
| `stages/text_alignment_detector.dart` | P-03 | ColumnDetector Layer 2 |
| `stages/whitespace_gap_detector.dart` | P-03 | ColumnDetector Layer 2b |
| `stages/anchor_corrector.dart` | P-03 | ColumnDetector Layer 3 |
| `pipeline/synthetic_region_builder.dart` | P-05 | ExtractionPipeline Stage 4B synthetic merge |
| `pipeline/ocr_text_extractor.dart` | P-13 | Lightweight OCR-only pipeline for M&P |
| `ocr/crop_ocr_stats.dart` | P-11 | Extracted from text_recognizer_v2 |
| `shared/keyword_matcher.dart` | P-09 | Shared keyword matching (conditional — only if 2+ callers) |

### Deleted Files (2)

| File | Reason |
|---|---|
| `stages/row_classifier_v2.dart` | 951-line dead code — V3 is active |
| `test/.../stage_4a_row_classifier_test.dart` | Tests dead V2 code |

### Heavily Modified Files (5)

| File | Change |
|---|---|
| `stages/post_processor_v2.dart` | ~1,509 → ~250 lines (orchestrator only) |
| `stages/column_detector_v2.dart` | ~1,948 → ~300 lines (orchestrator + constructor) |
| `pipeline/extraction_pipeline.dart` | ~1,246 → ~900 lines (extract synthetic builder) |
| `shared/post_process_utils.dart` | `cleanDescriptionArtifacts` data-driven (~127 → ~50 lines) |
| `stages/text_recognizer_v2.dart` | Remove `_CropOcrStats` (~932 → ~742 lines) |

### New Fixture Files (5)

| File | Stage |
|---|---|
| `fixtures/springfield_grid_line_column_detection.json` | Layer 0 |
| `fixtures/springfield_header_detection.json` | Layer 1 |
| `fixtures/springfield_text_alignment_detection.json` | Layer 2 |
| `fixtures/springfield_whitespace_gap_detection.json` | Layer 2b |
| `fixtures/springfield_anchor_correction.json` | Layer 3 |

---

## Estimated Impact

| Metric | Before | After | Change |
|---|---|---|---|
| Largest file (ColumnDetectorV2) | 1,948 lines | ~300 lines | -85% |
| PostProcessorV2 | 1,509 lines | ~250 lines | -83% |
| ExtractionPipeline | 1,246 lines | ~900 lines | -28% |
| Dead code deleted | 951 lines (V2) | 0 | -951 lines |
| Independently testable components | 2 (V2+V3 row classifiers) | 11+ | +9 |
| Sub-stage fixture slots | 5 (post-processor phases) | 10 | +5 |
| Contract test coverage | Existing contracts unchanged | New per-layer contracts addable | More granular |

---

## Verification Plan

After each phase:
1. `pwsh -Command "flutter analyze"` — zero new warnings
2. `pwsh -Command "flutter test test/features/pdf/"` — all tests pass
3. Regenerate Springfield fixtures and run `stage_trace_diagnostic_test.dart` to confirm new fixture slots are populated

Full pipeline regression check after Phase 2 (ColumnDetectorV2) and Phase 1 (PostProcessorV2) since those touch active extraction stages:
- `pwsh -Command "flutter test"` — all tests across entire codebase pass

---

## Agent Assignments

| Phase | Primary Agent | Support |
|---|---|---|
| Phase 0 (P-01, P-02, P-06) | backend-data-layer-agent | qa-testing-agent (verify no regressions) |
| Phase 1 (P-04 PostProcessorV2) | backend-data-layer-agent | code-review-agent (validate static class design) |
| Phase 2 (P-03 ColumnDetectorV2) | backend-data-layer-agent | code-review-agent (validate injection pattern) |
| Phase 3 (P-05 ExtractionPipeline) | backend-data-layer-agent | — |
| Phase 4 (P-07–P-13 smaller items) | backend-data-layer-agent | code-review-agent (final pass) |
| All phases | qa-testing-agent | flutter test after each phase |

Phases 1 and 2 are **fully independent** (different files) and can be executed in parallel via the dispatching-parallel-agents skill.

---

## Decision Log

| Decision | Choice | Rationale |
|---|---|---|
| Fixture emission pattern | Option B — own file per sub-component | Matches existing per-phase post-processor fixture pattern |
| ColumnDetectorV2 injection | Injectable sub-components, managed by orchestrator | Follows ExtractionPipeline's own injection pattern; ExtractionPipeline interface unchanged |
| PostProcessorV2 phase design | Pure static utility classes | All methods already static; no state to inject |
| Stage trace test | Do not refactor | Wide not tall — size from stages, not complexity per section |
| P-10 (_median) | Skip | Already resolved — all copies delegate to MathUtils.median() |
| V1 stage files | Skip | Already deleted (commit 5bab520) |
| Deprecated tests | Skip most | Already cleaned up; only V2 row classifier tests remain |

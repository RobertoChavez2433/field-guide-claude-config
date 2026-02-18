# Code Review: PDF Extraction Pipeline — KISS/DRY & Code Quality Audit

**Date**: 2026-02-16
**Scope**: Full working tree review of `lib/features/pdf/services/extraction/` and `test/features/pdf/extraction/`
**Reviewers**: 2 parallel code-review agents (production code + test/fixtures)
**Focus**: KISS/DRY violations, dead code, deprecated imports, orphaned files, code quality

---

## Executive Summary

The extraction pipeline is **architecturally strong** — clean stage separation, disciplined coordinate normalization, dependency injection throughout, and solid contract tests between stages. However, it carries **~596 lines of completely dead production code**, **~410 lines of duplicated test helpers**, two acknowledged God classes, and several orphaned files. Total cleanup opportunity: **~1,146 lines**.

### Scorecard

| Category | Grade | Notes |
|----------|-------|-------|
| Dead code | **D** | 596 lines of unused production code across 3 files |
| DRY (production) | **B** | Minor duplication — mostly `_median` implementations |
| DRY (tests) | **D+** | 410+ lines of duplicated helpers across 8+ test files |
| KISS | **C** | Two acknowledged God classes (1,824 and 1,472 lines), one God method (482 lines) |
| File hygiene | **C+** | 2 orphaned files, 1 superseded generator |
| Architecture | **A-** | Clean stage pipeline, good contracts, strong DI, consistent normalization |
| Test quality | **B+** | Excellent golden test design, good coverage, but DRY suffers badly |

---

## Critical Issues (Must Fix)

### C1. Dead method: `_recognizeWithRowStrips` — 270 lines never called

**File**: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:516-770`
**Severity**: HIGH

The entire `_recognizeWithRowStrips` method (254 lines) plus the `_RowStrip` helper class (lines 934-939) are never called anywhere in the codebase. This was superseded by `_recognizeWithCellCrops` but never removed.

**Impact**: 270 lines of dead code that must be maintained, could mislead developers, and inflates test surface.

**Fix**: Delete lines 516-770 (`_recognizeWithRowStrips`) and lines 934-939 (`_RowStrip` class).

---

### C2. Unused `ConcurrencyGateV2` class — entire file dead

**File**: `lib/features/pdf/services/extraction/ocr/concurrency_gate_v2.dart`
**Severity**: HIGH

This 156-line file is never imported by any production code. It is only referenced in its own test file. The OCR processing loop in `text_recognizer_v2.dart` processes pages sequentially and does not use any concurrency gating.

**Fix**: Delete `concurrency_gate_v2.dart` and its test. If concurrency control is needed in the future, it can be reintroduced from git history.

---

### C3. Unused `TesseractPoolV2` class — entire file dead

**File**: `lib/features/pdf/services/extraction/ocr/tesseract_pool_v2.dart`
**Severity**: HIGH

This 170-line singleton pool is never used by any production code. `TesseractEngineV2` manages its own Tesseract instance directly (lines 49-50, 241-262). The pool was designed to reduce initialization overhead but was never wired in.

**Fix**: Delete `tesseract_pool_v2.dart` and its test.

---

### C4. Orphaned fixture: `springfield_ground_truth_quality.json`

**File**: `test/features/pdf/extraction/fixtures/springfield_ground_truth_quality.json`
**Severity**: HIGH

Grep across all test and integration_test directories returns zero references to this file. It appears to be a leftover from an earlier quality ground-truth design that was replaced by `springfield_quality_report.json`.

**Fix**: Delete the file.

---

### C5. Superseded fixture generator — older incomplete copy

**File**: `test/features/pdf/extraction/golden/generate_fixtures_test.dart`
**Severity**: HIGH

This is a simplified, older version of the authoritative generator at `integration_test/generate_golden_fixtures_test.dart`. The golden/ version:
- Maps only 10 stages (missing `pageRendering`, `imagePreprocessing`, `textRecognition`, `elementClamping`, `rowPathways`, `columnDetectionLayers`, `postColumnRefinement`, `orphanElements`, and all post-processing sub-stages)
- Lacks diagnostic image capture
- Lacks multi-attempt support
- Generates identical fixture filenames to the same directory, creating confusion about which to run

**Fix**: Delete `test/features/pdf/extraction/golden/generate_fixtures_test.dart`. The integration test version is the sole authoritative generator.

---

## DRY Violations (Should Fix)

### D1. `_median` duplicated 3x despite `MathUtils.median` existing

**Severity**: MEDIUM
**Files**:
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:826-837` — private `_median` method
- `lib/features/pdf/services/extraction/stages/grid_line_detector.dart:417-428` — top-level `_median` function
- `lib/features/pdf/services/extraction/stages/column_detector_v2.dart:1754` — correctly delegates to `MathUtils.median`

The shared `MathUtils.median` exists at `lib/features/pdf/services/extraction/shared/math_utils.dart` and was created specifically to centralize this. `ColumnDetectorV2` adopted it; the other two files did not.

**Note**: `grid_line_detector.dart`'s `_median` runs inside a `compute()` isolate (line 169), so it cannot import `MathUtils` directly. Either inline the same logic with a comment explaining why, or restructure to pass median via the isolate params.

**Fix**: Replace `text_recognizer_v2.dart`'s `_median` with `MathUtils.median`. Document the isolate constraint for `grid_line_detector.dart`.

**Lines saved**: ~25

---

### D2. `_createOcrElement` helper duplicated 8 times across tests

**Severity**: MEDIUM
**Files**:
1. `test/features/pdf/extraction/contracts/stage_4a_to_4b_contract_test.dart:489`
2. `test/features/pdf/extraction/contracts/stage_4b_to_4c_contract_test.dart:360`
3. `test/features/pdf/extraction/contracts/stage_4c_to_4d_contract_test.dart:538`
4. `test/features/pdf/extraction/contracts/stage_4d_to_4e_contract_test.dart:614`
5. `test/features/pdf/extraction/stages/stage_4b_region_detector_test.dart:498`
6. `test/features/pdf/extraction/stages/stage_4c_column_detector_test.dart:4538`
7. `test/features/pdf/extraction/stages/stage_4d_cell_extractor_test.dart:710`
8. `test/features/pdf/extraction/helpers/mock_stages.dart:18` (as `createMockElement`, slightly different signature)

Each file has its own private `_createOcrElement` with slightly different parameter signatures (some use `xCenter`/`yCenter`, some use `left`/`right`/`top`/`bottom`). A `testOcrElement` function exists in `test/features/pdf/extraction/helpers/test_fixtures.dart` but uses a different pattern and isn't widely adopted.

**Fix**: Expand `test_fixtures.dart` with a flexible `testOcrElement` supporting both center-based and edge-based creation. Update all 8 files to import it.

**Lines saved**: ~200

---

### D3. `_createClassifiedRows` helper duplicated 6 times

**Severity**: MEDIUM
**Files**:
1. `test/features/pdf/extraction/stages/stage_4b_region_detector_test.dart:459`
2. `test/features/pdf/extraction/stages/stage_4c_column_detector_test.dart:4502`
3. `test/features/pdf/extraction/stages/stage_4d_cell_extractor_test.dart:674`
4. `test/features/pdf/extraction/contracts/stage_4b_to_4c_contract_test.dart:337`
5. `test/features/pdf/extraction/contracts/stage_4c_to_4d_contract_test.dart:515`
6. `test/features/pdf/extraction/stages/stage_4a_row_classifier_test.dart:936`

5 of 6 are byte-for-byte identical. One uses named parameters but does the same thing.

**Fix**: Extract to `test_fixtures.dart` as `testClassifiedRows(List<ClassifiedRow> rows)`.

**Lines saved**: ~90

---

### D4. `_createExtractionResult` helper duplicated 3 times

**Severity**: MEDIUM
**Files**:
1. `test/features/pdf/extraction/stages/stage_4c_column_detector_test.dart:4559`
2. `test/features/pdf/extraction/stages/stage_4a_row_classifier_test.dart:870`
3. `test/features/pdf/extraction/contracts/stage_4b_to_4c_contract_test.dart:385`

**Fix**: Extract to `test_fixtures.dart`.

**Lines saved**: ~40

---

### D5. `CoordinateMetadata` boilerplate repeated 12+ times in one file

**Severity**: LOW-MEDIUM
**File**: `test/features/pdf/extraction/contracts/stage_2_to_3_contract_test.dart:30-49`

Every `OcrElement` construction includes 6-line `CoordinateMetadata` blocks with identical values (`normalized`, `Size(612, 792)`, `Size(2448, 3168)`, `300`, `ocr`). Lines 23-67 alone have 3 copies. This file does not import `test_fixtures.dart` at all.

**Fix**: Use the existing `testOcrCoordinates()` helper from `test_fixtures.dart`, or create a normalized variant.

**Lines saved**: ~80

---

### D6. Overlapping OCR artifact cleaning in `PostProcessUtils`

**Severity**: LOW
**File**: `lib/features/pdf/services/extraction/shared/post_process_utils.dart`
- `cleanDescriptionArtifacts` (lines 25-151)
- `_cleanOcrArtifacts` (lines 188-201)

Both methods remove pipes, brackets, em/en dashes, accented E characters, and normalize whitespace. `_cleanOcrArtifacts` additionally strips quotes, semicolons, colons, commas, and exclamation marks. ~60% regex pattern overlap.

**Fix**: Extract a shared `_removeBaseArtifacts(String text)` helper and have both methods call it.

**Lines saved**: ~15

---

## KISS Violations (Consider)

### K1. God Class: `ColumnDetectorV2` — 1,824 lines

**File**: `lib/features/pdf/services/extraction/stages/column_detector_v2.dart`
**Severity**: MEDIUM

The file contains a `TODO(refactor)` comment at lines 11-16 acknowledging decomposition is needed. It handles 4 distinct detection layers (header scanning, text alignment, whitespace gap analysis, anchor correction) plus missing column inference, fallback columns, and multiple utility methods.

**Suggested decomposition**:
- `HeaderDetector` — header keyword scanning layer
- `TextAlignmentDetector` — text alignment clustering layer
- `WhitespaceGapDetector` — whitespace gap analysis layer
- `AnchorCorrector` — anchor-based column correction layer

**Impact**: Violates SRP, difficult to test individual layers in isolation, hard to navigate.

---

### K2. God Class: `PostProcessorV2` — 1,472 lines

**File**: `lib/features/pdf/services/extraction/stages/post_processor_v2.dart`
**Severity**: MEDIUM

Also has a `TODO(refactor)` at lines 20-25 acknowledging decomposition is needed. Handles normalization, splitting, consistency checks, deduplication, sequence correction, math validation, confidence recalculation, and completeness checking.

**Suggested decomposition**:
- `ValueNormalizer` — value normalization and formatting
- `RowSplitter` — multi-item row splitting
- `ConsistencyChecker` — cross-field consistency validation
- `ItemDeduplicator` — duplicate detection and removal

---

### K3. God Method: `_runExtractionStages` — 482 lines

**File**: `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart:352-834`
**Severity**: MEDIUM

The synthetic region merge logic alone (lines 542-740) is ~200 lines of complex branching nested within this already-massive method.

**Fix**: Extract synthetic region merge into `SyntheticRegionMerger` helper class.

---

### K4. God Test: `stage_trace_diagnostic_test.dart` — 1,000+ lines

**File**: `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`
**Severity**: LOW-MEDIUM

Loads 20+ fixture files, declares 15+ nullable `late` variables in a single `main()` scope, and repeats `if (File(path).existsSync()) { json = _loadFixture(path); }` 13 times in `setUpAll`.

**Fix**: Extract `SpringfieldFixtureLoader` class with map-based loading. Adding a new stage currently requires modifying 3 places in this file.

---

## Minor Issues

### M1. Redundant `firstOrNull` extension

**File**: `test/features/pdf/extraction/golden/golden_file_matcher.dart:448-456`

Dart 3.0+ includes `Iterable.firstOrNull` in `dart:core`. This custom `_FirstOrNull` extension shadows the built-in.

**Fix**: Remove the extension and use the built-in `firstOrNull`.

---

### M2. Magic string `'springfield-864130'` duplicated

**Files**:
- `test/features/pdf/extraction/golden/springfield_golden_test.dart:79`
- `integration_test/generate_golden_fixtures_test.dart:101`

**Fix**: Extract to a shared constant in `test_fixtures.dart`.

---

### M3. `_CropOcrStats` — 170 lines of min/max boilerplate

**File**: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:953-1121`

The `record()` and `merge()` methods have extensive manual min/max tracking with repetitive if-else blocks. `merge()` duplicates the logic from `record()`.

**Fix**: Use a list-based approach with `dart:math` `min()`/`max()`.

---

### M4. Magic number `totalStages = 13` drifts

**File**: `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart:364`

Comment says `// Approximate number of stages` — this will drift as stages are added/removed.

**Fix**: Compute from actual stage count or maintain as a verified constant.

---

### M5. Progress callback uses hardcoded stage label strings

**File**: `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart:258`

Strings like `'parsingRows'` and `'locatingTable'` should be constants or enum values (possibly from `stage_names.dart`).

---

### M6. Barrel file mixes model and pipeline concerns

**File**: `lib/features/pdf/services/extraction/models/models.dart:18-22`

Exports pipeline files from `../pipeline/`, mixing model and pipeline barrel concerns.

**Fix**: Consider splitting into `models.dart` and `pipeline.dart` barrel files.

---

### M7. Diagnostic `output/` directory may not be gitignored

**Path**: `test/features/pdf/extraction/output/diagnostic/`

Contains 18 PNG files and coverage text files — generated artifacts that should not be tracked.

**Fix**: Add to `.gitignore` if not already present.

---

## Positive Observations

These patterns are **worth preserving and extending**:

1. **Stage contract enforcement**: `StageReport` with `outputCount + excludedCount == inputCount` validation ensures no silent data loss. `StateError` throws catch violations early.

2. **Coordinate normalization discipline**: All stages work in 0.0-1.0 normalized space via `CoordinateNormalizer`. Eliminates an entire class of coordinate bugs.

3. **Dependency injection**: `ExtractionPipeline` constructor accepts all stages as optional parameters with sensible defaults, enabling comprehensive test mocking.

4. **Diagnostic callbacks**: `onStageOutput` and `onDiagnosticImage` callbacks enable rich debugging without coupling to any logging framework.

5. **Quality thresholds centralization**: `QualityThresholds` prevents threshold divergence across quality-related code.

6. **Grid line detection isolation**: Running pixel scanning in a `compute()` isolate prevents UI thread blocking.

7. **Shared utility adoption**: `HeaderKeywords`, `ExtractionPatterns`, `UnitRegistry`, `FieldFormatValidator` centralize domain knowledge and are consistently used.

8. **`mock_stages.dart` consolidation**: Already eliminated ~484 lines of duplicate mock classes — good precedent.

9. **Three-layer golden test design**: Regression baseline, ground truth comparison, and convergence metrics is a sophisticated approach for tracking quality over time.

10. **Fixture skip/gate pattern**: Explicit readiness checks with clear skip reasons prevent false failures in environments without generated fixtures.

---

## Remediation Priority

### Phase 1: Quick Wins (Low Risk, High Impact)
1. Delete dead `_recognizeWithRowStrips` + `_RowStrip` (C1) — **270 lines**
2. Delete unused `ConcurrencyGateV2` (C2) — **156 lines**
3. Delete unused `TesseractPoolV2` (C3) — **170 lines**
4. Delete orphaned `springfield_ground_truth_quality.json` (C4)
5. Delete superseded `generate_fixtures_test.dart` (C5)
6. Remove redundant `firstOrNull` extension (M1)

**Total Phase 1**: ~596 lines removed, 3 files deleted, 2 orphaned files cleaned

### Phase 2: Test DRY Consolidation (Medium Risk, High Impact)
1. Expand `test_fixtures.dart` with consolidated helpers (D2, D3, D4)
2. Update 8+ test files to use shared helpers
3. Reduce `CoordinateMetadata` boilerplate (D5)
4. Extract `SpringfieldFixtureLoader` (K4)

**Total Phase 2**: ~410 lines consolidated

### Phase 3: Production DRY & KISS (Higher Risk, Medium Impact)
1. Consolidate `_median` to `MathUtils.median` (D1)
2. Extract shared OCR artifact base (D6)
3. Decompose `ColumnDetectorV2` (K1) — requires careful test updates
4. Decompose `PostProcessorV2` (K2) — requires careful test updates
5. Extract `SyntheticRegionMerger` from pipeline (K3)

**Total Phase 3**: ~40 lines + major structural improvement

---

## Cleanup Totals

| Category | Lines Removable | Lines Consolidatable | Files Deletable |
|----------|----------------|---------------------|-----------------|
| Dead production code | 596 | — | 2 |
| Orphaned test files | — | — | 2 |
| Test helper duplication | — | 410 | — |
| Production DRY | — | 40 | — |
| **Total** | **596** | **450** | **4** |

**Grand total opportunity: ~1,046 lines of cleanup across 3 phases.**

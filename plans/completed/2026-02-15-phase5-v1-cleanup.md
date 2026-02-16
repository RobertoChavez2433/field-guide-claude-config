# Phase 5: V1 Remnant Cleanup — OCR-Only Pipeline Purification

**Parent plan**: `2026-02-14-grid-line-detection-row-ocr.md`
**Prerequisite**: Phases 1-4 complete
**Agent**: `frontend-flutter-specialist-agent` (code changes) + `qa-testing-agent` (test verification)
**Branch**: `phase5-v1-cleanup`

---

## Overview

The V2 extraction pipeline is OCR-only by design (per `pdf-v2-constraints.md`), yet v1 remnants — enum values, dead getters, stale comments, incorrect test data, and hardcoded strings — are scattered across 20+ files in both `lib/` and `test/`. This phase performs a systematic cleanup to align all code with the OCR-only reality.

### Success Criteria

- [ ] `ExtractionMethod.native` enum value removed; only `ocr` remains
- [ ] `ConfidenceSource.native` enum value removed
- [ ] `DocumentProfile` and `PageProfile` only accept OCR strategies
- [ ] Dead getters (`nativePages`, `hybridPages`) removed
- [ ] `CoordinateNormalizer.fromNativeText()` removed
- [ ] All test files use `ExtractionMethod.ocr` exclusively
- [ ] All test strategy strings use `'ocr'` / `'ocr_only'` exclusively
- [ ] Hardcoded stage name strings replaced with `StageNames.*` constants
- [ ] Stale v1 comments updated or removed
- [ ] `native_pages` column kept in DB schema (backward compat) but always written as 0
- [ ] `flutter test test/features/pdf/extraction/` — all tests pass
- [ ] `flutter analyze` — no new warnings

---

## Step 1: Remove `ExtractionMethod.native` Enum Value

**File**: `lib/features/pdf/services/extraction/models/ocr_element.dart`

### 1A. Simplify the enum (lines 15-18)

```dart
// BEFORE:
enum ExtractionMethod {
  native, // From PDF text layer
  ocr,    // From Tesseract
}

// AFTER:
enum ExtractionMethod {
  ocr, // From Tesseract OCR
}
```

### 1B. Update `UnifiedExtractionResult.fromMap()` deserialization

**File**: `lib/features/pdf/services/extraction/models/extraction_result.dart` (line 78-79)

The `fromMap` uses `ExtractionMethod.values.firstWhere((e) => e.name == m)` which will throw for `'native'` in any persisted data. Add a migration fallback:

```dart
// AFTER:
methodPerPage: (map['method_per_page'] as List)
    .map((m) => ExtractionMethod.ocr) // OCR-only pipeline: all methods are OCR
    .toList(),
```

### 1C. Update `CoordinateMetadata.fromMap()` similarly

**File**: `lib/features/pdf/services/extraction/models/ocr_element.dart` (line 87-88)

```dart
// AFTER:
source: ExtractionMethod.ocr, // OCR-only pipeline
```

**Impact**: ~45 test file references need updating (Step 6).

---

## Step 2: Remove `ConfidenceSource.native` Enum Value

**File**: `lib/features/pdf/services/extraction/models/confidence.dart` (lines 9-15)

```dart
// BEFORE:
enum ConfidenceSource {
  ocrEngine,
  native,
  inferred,
  repaired,
  calculated,
}

// AFTER:
enum ConfidenceSource {
  ocrEngine,
  inferred,
  repaired,
  calculated,
}
```

**Test impact**: `test/features/pdf/extraction/models/confidence_test.dart` — 7 references to `ConfidenceSource.native` → replace with `ConfidenceSource.ocrEngine`.

---

## Step 3: Clean Up `DocumentProfile` & `PageProfile` Models

**File**: `lib/features/pdf/services/extraction/models/document_profile.dart`

### 3A. Update `PageProfile` (lines 1-93)

1. **Comment** (line 11): `'native' | 'ocr' | 'hybrid'` → `'ocr'`
2. **`isValid`** (line 33): `['native', 'ocr', 'hybrid'].contains(recommendedStrategy)` → `recommendedStrategy == 'ocr'`
3. **Doc comment** (lines 1-4): Remove "whether native text extraction or OCR is needed" → "quality metrics for each page"

### 3B. Update `DocumentProfile` (lines 95-173)

1. **Comment** (line 99): `'native_only' | 'ocr_only' | 'hybrid'` → `'ocr_only'`
2. **Remove dead getters** (lines 110-115): Delete `nativePages` and `hybridPages` entirely. Keep `ocrPages`.
3. **`isValid`** (line 120): `['native_only', 'ocr_only', 'hybrid'].contains(overallStrategy)` → `overallStrategy == 'ocr_only'`

---

## Step 4: Remove `CoordinateNormalizer.fromNativeText()`

**File**: `lib/features/pdf/services/extraction/pipeline/coordinate_normalizer.dart`

Remove lines 8-19 (`fromNativeText` method). Only used in tests — the test for it will also be removed/updated.

**Test file**: `test/features/pdf/extraction/models/coordinate_normalizer_test.dart` — remove the `fromNativeText` test case.

---

## Step 5: Clean Up `ExtractionMetrics` & `TextQualityAnalyzer`

### 5A. `ExtractionMetrics` (extraction_metrics.dart)

**File**: `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart`

- Lines 49, 62-64, 110: Keep the `native_pages` DB column write (backward compat with existing data) but hardcode to `0`:

```dart
// BEFORE (lines 49, 62-64):
int nativePages = 0;
...
if (docAnalyzerStage.metrics.containsKey('native_pages')) {
  nativePages = docAnalyzerStage.metrics['native_pages'] as int;
}

// AFTER:
// native_pages always 0 in OCR-only pipeline (column kept for backward compatibility)
```

Remove the `native_pages` metric read (lines 62-64). Keep writing `'native_pages': 0` to the DB.

### 5B. `TextQualityAnalyzer` (text_quality_analyzer.dart)

**File**: `lib/features/pdf/services/extraction/shared/text_quality_analyzer.dart`

1. **Comment** (line 4): Remove "Extracted from DocumentAnalyzer and" → "Shared text quality analysis for"
2. **Metrics** (lines 193-196): Remove `'native_pages': 0` and `'hybrid_pages': 0` from `generatePageMetrics()` return map

---

## Step 6: Update All Test Files

This is the bulk of the work. Changes are mechanical but numerous.

### 6A. Test Helper: `test_fixtures.dart`

**File**: `test/features/pdf/extraction/helpers/test_fixtures.dart`

1. **Remove `testNativeCoordinates()`** (lines 13-22) entirely
2. **Update `testOcrElement()`** (line 52): default `coordinates` from `testNativeCoordinates()` → `testOcrCoordinates()`
3. **Update `testPageProfile()`** (line 63): default `recommendedStrategy = 'native'` → `recommendedStrategy = 'ocr'`

### 6B. Test Helper: `mock_stages.dart`

**File**: `test/features/pdf/extraction/helpers/mock_stages.dart`

- Line 27: `source: ExtractionMethod.native` → `source: ExtractionMethod.ocr`

### 6C. Contract Tests (ExtractionMethod.native → .ocr)

| File | Lines | Count |
|------|-------|-------|
| `contracts/stage_3_to_4a_contract_test.dart` | 33, 44, 55, 68, 79, 90, 96, 201, 227, 233, 265, 278, 291, 298-300, 329, 343, 350-352 | ~20 |
| `contracts/stage_4a_to_4b_contract_test.dart` | 402, 421, 440, 509 | 4 |
| `contracts/stage_4b_to_4c_contract_test.dart` | 379, 391 | 2 |
| `contracts/stage_4c_to_4d_contract_test.dart` | 553 | 1 |
| `contracts/stage_4d_to_4e_contract_test.dart` | 628 | 1 |

**Also in `stage_3_to_4a_contract_test.dart`:**
- Line 1: Update comment `Stage 3 (StructurePreserver)` → `Stage 3 (ElementValidator)`
- Line 19: Update comment `Simulate StructurePreserver output` → `Simulate ElementValidator output`
- Line 233: Remove comment `// Tagged as native (hybrid preference)`

### 6D. Stage Tests (ExtractionMethod.native → .ocr)

| File | Lines | Count |
|------|-------|-------|
| `stages/stage_4a_row_classifier_test.dart` | 881, 909, 931, 983 | 4 |
| `stages/stage_4b_region_detector_test.dart` | 512 | 1 |
| `stages/stage_4c_column_detector_test.dart` | 2561, 2577 | 2 |

### 6E. Model Tests

| File | Changes |
|------|---------|
| `models/extraction_result_test.dart` | Lines 16, 32, 58, 84, 98: `.native` → `.ocr` |
| `models/ocr_element_enhanced_test.dart` | Line 43: `.native` → `.ocr` |
| `models/confidence_test.dart` | Lines 20, 25, 30, 38, 43, 121, 130: `ConfidenceSource.native` → `.ocrEngine` |
| `models/document_profile_test.dart` | ~20 changes: strategy strings + dead getter tests |

### 6F. `document_profile_test.dart` — Detailed Changes

1. **Remove tests for dead getters** (lines 150-192): Remove `nativePages count correct`, `hybridPages count correct` tests
2. **Update `'hybrid'` strategy** in remaining tests → `'ocr_only'`
3. **Update `recommendedStrategy: 'native'`** → `recommendedStrategy: 'ocr'`
4. **Update validation tests**: `'native_only'` → `'ocr_only'` where appropriate
5. **Add new tests**: Verify `isValid` rejects `'native'`, `'hybrid'`, `'native_only'`

### 6G. Integration Tests

| File | Line | Change |
|------|------|--------|
| `integration/full_pipeline_integration_test.dart` | 230 | `stageName: 'document_analyzer'` → `stageName: StageNames.documentAnalysis` |
| `integration/full_pipeline_integration_test.dart` | 239 | `'native_pages': 6` → `'native_pages': 0` |
| `integration/full_pipeline_integration_test.dart` | 240 | `'ocr_pages': 0` → `'ocr_pages': 6` |
| `integration/full_pipeline_integration_test.dart` | 241 | `'overall_strategy': 'native'` → `'overall_strategy': 'ocr_only'` |
| `integration/type_round_trip_test.dart` | 22 | `overallStrategy: 'hybrid'` → `overallStrategy: 'ocr_only'` |
| `integration/type_round_trip_test.dart` | 39 | `ExtractionMethod.native` → `ExtractionMethod.ocr` |

### 6H. Pipeline Tests

| File | Line | Change |
|------|------|--------|
| `pipeline/extraction_metrics_test.dart` | 274 | `'overall_strategy': 'hybrid'` → `'overall_strategy': 'ocr_only'` |
| `pipeline/extraction_metrics_test.dart` | 294 | `expect(row['strategy'], 'hybrid')` → `expect(row['strategy'], 'ocr_only')` |

---

## Step 7: Update Stale Comments

| File | Line | Change |
|------|------|--------|
| `stages/text_recognizer_v2.dart` | 32 | Remove "Stage 3 (StructurePreserver) will merge native + OCR elements" |
| `stages/element_validator.dart` | 4-5 | Remove "This replaces the deprecated StructurePreserver which handled merging native + OCR results" |
| `shared/text_quality_analyzer.dart` | 4 | Remove "from DocumentAnalyzer and" |
| `models/pipeline_config.dart` | 8 | Remove "This replaces the legacy `PostProcessConfig` from table_extraction for V2 usage" |
| `pipeline/result_converter.dart` | 7 | "Converts v2 PipelineResult to legacy PdfImportResult" → fine as-is (ResultConverter is genuinely a bridge) |
| `pipeline/coordinate_normalizer.dart` | 2-4 | Remove "native PDF points" from description |

---

## Step 8: Database Schema — No Migration Needed

**File**: `lib/core/database/schema/extraction_tables.dart` (line 23)

The `native_pages` column stays in the schema. Removing it would require a DB migration, and existing data may have non-zero values. The code change in Step 5A ensures new records always write `0`.

**No schema migration needed.**

---

## Execution Order & Dependencies

```
Step 1 (enum removal) ──┐
Step 2 (confidence enum) ├── Step 6 (test updates) ── Step 8 (verify)
Step 3 (model cleanup)  ─┤
Step 4 (normalizer)     ─┤
Step 5 (metrics/analyzer)┘
Step 7 (comments) ────────── independent
```

**Recommended execution**: Steps 1-5 in parallel (all lib/ changes), then Step 6 (all test/ changes), then Step 7 (comments), then Step 8 (run tests).

---

## Files Modified Summary

### `lib/` (Production Code) — 7 files

| File | Change |
|------|--------|
| `models/ocr_element.dart` | Remove `ExtractionMethod.native`, update `fromMap` |
| `models/extraction_result.dart` | Update `fromMap` to always use `.ocr` |
| `models/confidence.dart` | Remove `ConfidenceSource.native` |
| `models/document_profile.dart` | Remove dead getters, restrict strategy validation |
| `pipeline/coordinate_normalizer.dart` | Remove `fromNativeText()` method |
| `pipeline/extraction_metrics.dart` | Hardcode `native_pages: 0`, remove metric read |
| `shared/text_quality_analyzer.dart` | Remove `native_pages`/`hybrid_pages` from metrics output |

### Comment-Only Changes — 4 files

| File | Change |
|------|--------|
| `stages/text_recognizer_v2.dart` | Remove StructurePreserver reference |
| `stages/element_validator.dart` | Remove StructurePreserver reference |
| `shared/text_quality_analyzer.dart` | Remove DocumentAnalyzer reference |
| `pipeline/coordinate_normalizer.dart` | Update description |

### `test/` (Test Code) — 17 files

| File | Change Type |
|------|-------------|
| `helpers/test_fixtures.dart` | Remove `testNativeCoordinates`, update defaults |
| `helpers/mock_stages.dart` | `.native` → `.ocr` |
| `contracts/stage_3_to_4a_contract_test.dart` | ~20 enum + comment changes |
| `contracts/stage_4a_to_4b_contract_test.dart` | 4 enum changes |
| `contracts/stage_4b_to_4c_contract_test.dart` | 2 enum changes |
| `contracts/stage_4c_to_4d_contract_test.dart` | 1 enum change |
| `contracts/stage_4d_to_4e_contract_test.dart` | 1 enum change |
| `stages/stage_4a_row_classifier_test.dart` | 4 enum changes |
| `stages/stage_4b_region_detector_test.dart` | 1 enum change |
| `stages/stage_4c_column_detector_test.dart` | 2 enum changes |
| `models/extraction_result_test.dart` | 5 enum changes |
| `models/ocr_element_enhanced_test.dart` | 1 enum change |
| `models/confidence_test.dart` | 7 source changes |
| `models/document_profile_test.dart` | ~20 strategy + getter test changes |
| `models/coordinate_normalizer_test.dart` | Remove `fromNativeText` test |
| `integration/full_pipeline_integration_test.dart` | Stage name + strategy changes |
| `integration/type_round_trip_test.dart` | Strategy + enum changes |
| `pipeline/extraction_metrics_test.dart` | Strategy string changes |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Persisted data has `ExtractionMethod.native` values | `fromMap()` ignores stored value, always returns `.ocr` |
| Existing DB rows have `native_pages > 0` | Column kept in schema; new rows always write `0` |
| Missing a test reference to `.native` | `flutter analyze` + grep verification after changes |
| `ConfidenceSource.native` in serialized data | Same fromMap pattern: ignore stored value |
| Breaking the `testOcrElement()` default chain | Change default from `testNativeCoordinates()` → `testOcrCoordinates()` |

---

## Verification Checklist

- [ ] `grep -r "ExtractionMethod.native" lib/ test/` returns zero results
- [ ] `grep -r "ConfidenceSource.native" lib/ test/` returns zero results
- [ ] `grep -r "'native'" lib/features/pdf/services/extraction/` returns zero results
- [ ] `grep -r "'hybrid'" lib/features/pdf/services/extraction/` returns zero results
- [ ] `grep -r "nativePages\|hybridPages" lib/` returns zero results
- [ ] `grep -r "fromNativeText" lib/` returns zero results
- [ ] `grep -r "'document_analyzer'" test/` returns zero results
- [ ] `grep -r "StructurePreserver" test/` returns zero results (except maybe archive files)
- [ ] `flutter analyze` — no new warnings
- [ ] `flutter test test/features/pdf/extraction/` — all tests pass

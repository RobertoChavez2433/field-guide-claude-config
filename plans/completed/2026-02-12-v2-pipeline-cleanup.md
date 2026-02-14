# Implementation Plan: V2 Pipeline Cleanup (6 Issues)

**Date:** 2026-02-12
**Context:** The OCR-only pipeline migration (per `2026-02-12-ocr-only-pipeline-design.md`) is functionally complete but has 6 residual issues: duplicate V1 files, incomplete re-extraction wiring, QualityValidator logic drift, metrics contract gaps, stale naming, and a duplicate fixture generator.

---

## Issue 1 (High): Delete duplicate V1 files from active path

**Problem:** 3 deprecated files exist in both `stages/` and `deprecated/` — identical copies. No production or test code imports the `stages/` copies.

**Action:** Delete these 3 files from the active path:
- `lib/features/pdf/services/extraction/stages/document_analyzer.dart`
- `lib/features/pdf/services/extraction/stages/native_extractor.dart`
- `lib/features/pdf/services/extraction/stages/structure_preserver.dart`

**Verification:** `flutter analyze` passes; no broken imports.

---

## Issue 2 (High): Wire enhanced preprocessing into re-extraction attempt 2

**Problem:** Plan calls for attempt 2 to use enhanced contrast (1.5x floor). Code comment says "enhanced preprocessing flag" but only changes DPI/PSM. `BenchmarkConfig.enhancedPreprocess` exists but is never passed to `PipelineConfig`.

**Action:**
1. Add `enhancedPreprocess` bool field to `PipelineConfig` (default `false`)
   - File: `lib/features/pdf/services/extraction/models/pipeline_config.dart`
   - Add to constructor, `copyWith`, and any serialization

2. Update `_adjustConfigForAttempt` in extraction_pipeline.dart (line ~534):
   ```dart
   // Attempt 2: Higher DPI + single block + enhanced preprocessing
   return config.copyWith(ocrDpi: 400, tesseractPsmMode: 6, enhancedPreprocess: true);
   ```

3. Consume `enhancedPreprocess` in `ImagePreprocessorV2` to boost contrast floor to 1.5x when enabled
   - File: `lib/features/pdf/services/extraction/stages/image_preprocessor_v2.dart`

4. Pass `enhancedPreprocess` from `BenchmarkConfig` into `PipelineConfig` in benchmark test (line ~154)
   - File: `test/features/pdf/extraction/golden/springfield_benchmark_test.dart`

**Verification:** Benchmark test config #5 (enhanced) produces different results than config #2 (same DPI/PSM without enhanced).

---

## Issue 3 (Medium): Fix QualityValidator no-items fallback strategy

**Problem:** Empty items fallback (line 516) hardcodes `higherDpiAutoPsm` for all retries instead of using `_selectStrategy(attemptNumber)`.

**Action:** Replace hardcoded strategy in `quality_validator.dart` line ~516:
```dart
// Before:
reExtractionStrategy: attemptNumber < 2
    ? ReExtractionStrategy.higherDpiAutoPsm
    : null,

// After:
reExtractionStrategy: _selectStrategy(attemptNumber),
```

**File:** `lib/features/pdf/services/extraction/stages/quality_validator.dart`

**Verification:** Unit test for zero-items + attempt=1 returns `higherDpiSingleBlock`.

---

## Issue 4 (Medium): Add missing metrics keys to DocumentQualityProfiler

**Problem:** `ExtractionMetrics` reads `total_pages` and `overall_strategy` from Stage-0 metrics, but `DocumentQualityProfiler._generateMetrics()` doesn't emit them.

**Action:** Add 2 keys to `_generateMetrics()` return map (line ~302):
```dart
'total_pages': pages.length,
'overall_strategy': 'ocr_only',
```

**File:** `lib/features/pdf/services/extraction/stages/document_quality_profiler.dart`

**Verification:** `ExtractionMetrics` correctly reports page count and strategy without relying on fallback defaults.

---

## Issue 5 (Medium): Fix stale naming across V2 paths and tests

**5a. ElementValidator stage name** — `element_validator.dart:98`
- Change `StageNames.structurePreservation` → add new constant `StageNames.elementValidation = 'element_validation'` in `stage_names.dart`
- Update ElementValidator to use it
- Update `stages.dart` barrel if needed

**5b. "Forced full OCR" wording** — `quality_validator.dart:421`
- Change to: `'Re-extracting with higher DPI/PSM to improve text recognition'`

**5c. Springfield fixture** — `springfield_quality_report.json:20`
- Update suggestion text to match 5b

**5d. Result converter test legacy stage IDs** — `result_converter_test.dart:217,243-244`
- Line 217: Update to use V2 stage names from `StageNames` constants
- Lines 239-244: This test verifies "no OCR" detection with native-only stages. Since native extraction is deprecated, either:
  - Update test to verify that all-OCR pipeline is detected correctly, OR
  - Remove the native-only test case as it tests a deprecated path

**5e. Integration test native strategy** — `full_pipeline_integration_test.dart:241`
- Change `'overall_strategy': 'native'` → `'overall_strategy': 'ocr_only'`

**Files:**
- `lib/features/pdf/services/extraction/stages/stage_names.dart`
- `lib/features/pdf/services/extraction/stages/element_validator.dart`
- `lib/features/pdf/services/extraction/stages/quality_validator.dart`
- `test/features/pdf/extraction/fixtures/springfield_quality_report.json`
- `test/features/pdf/extraction/pipeline/result_converter_test.dart`
- `test/features/pdf/extraction/integration/full_pipeline_integration_test.dart`

---

## Issue 6 (Low): Remove duplicate fixture generator

**Problem:** Two `generate_golden_fixtures_test.dart` files exist. The `integration_test/` version is more capable (multi-attempt, file locking workarounds).

**Action:**
- Delete `integration_test/generate_golden_fixtures_test.dart` (untracked)
- Keep `test/features/pdf/extraction/generate_golden_fixtures_test.dart` as canonical (it's the one referenced in the plan and already tracked by git)

**Verification:** Only one fixture generator exists.

---

## Execution Order

```
1. Issue 1 (delete V1 duplicates) — no dependencies
2. Issue 4 (metrics keys)         — no dependencies
3. Issue 5 (stale naming)         — no dependencies
4. Issue 3 (strategy fix)         — no dependencies
5. Issue 2 (enhanced preprocess)  — builds on pipeline_config.dart
6. Issue 6 (delete duplicate)     — no dependencies
```

Issues 1, 3, 4, 5, 6 are independent. Issue 2 should go last since it adds a new feature.

## Verification

1. `pwsh -Command "flutter analyze"` — zero errors
2. `pwsh -Command "flutter test test/features/pdf/extraction/"` — all extraction tests pass
3. Confirm no imports reference deleted files: `Grep` for old file names

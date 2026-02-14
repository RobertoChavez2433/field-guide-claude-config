# Implementation Plan: V2 Pipeline Code Review Fixes

**Last Updated**: 2026-02-14
**Status**: READY
**Source**: Code review findings (21 items across critical/warning/DRY/cleanup)

## Overview

Address 21 code review findings for the PDF extraction pipeline. Steps are ordered so that deletions happen last (to avoid breaking imports mid-way), and related changes are grouped together.

## Ordering Rationale

1. **Junk file first** -- zero risk, instant win
2. **StageNames changes** -- adds new constant, marks dead ones; needed before files that reference them
3. **ElementValidator + pipeline** -- consumes the new StageNames constant
4. **PipelineConfig fixes** -- self-contained model changes
5. **PostProcessor dead code** -- self-contained removals
6. **Pipeline core fixes** -- SHA-256 hoist, magic number, barrel cleanup
7. **Import style normalization** -- cosmetic, no behavior change
8. **Test fixes** -- update string literals, fix missing import, simplify duplicates
9. **Deprecated code deletion** -- last, because earlier steps must not import deprecated files

---

## Step 1: Delete `temp.txt`

**Finding**: #3
**Agent**: pdf-agent
**Risk**: None

### Action
- Delete `temp.txt` from project root

### Verify
- File no longer exists

---

## Step 2: Update `StageNames` constants

**Findings**: #4, #5
**Agent**: pdf-agent
**Files**:
- `lib/features/pdf/services/extraction/stages/stage_names.dart`

### Steps
1. Add new constant: `static const elementValidation = 'element_validation';`
2. Mark `nativeExtraction` as deprecated with `@Deprecated('Removed in V2 OCR-only pipeline')` comment or remove it entirely (it is only used by deprecated code being deleted in Step 9)
3. Keep `structurePreservation` for now (used by `generate_golden_fixtures_test.dart` fixture mapping) but add a `// Legacy alias -- ElementValidator uses elementValidation` comment

### Verify
- `pwsh -Command "flutter analyze lib/features/pdf/services/extraction/stages/stage_names.dart"`

---

## Step 3: Update ElementValidator and pipeline to use `StageNames.elementValidation`

**Finding**: #5
**Agent**: pdf-agent
**Files**:
- `lib/features/pdf/services/extraction/stages/element_validator.dart` (line 99)
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` (line 427)

### Steps
1. In `element_validator.dart:99`, change `StageNames.structurePreservation` to `StageNames.elementValidation`
2. In `extraction_pipeline.dart:427`, change `StageNames.structurePreservation` to `StageNames.elementValidation`
3. Update the two `generate_golden_fixtures_test.dart` files (both `test/` and `integration_test/` versions) to map `StageNames.elementValidation` instead of `StageNames.structurePreservation` for the unified elements fixture

### Verify
- `pwsh -Command "flutter test test/features/pdf/extraction/"` -- all tests pass
- Grep for remaining references to `structurePreservation` to confirm none are in active (non-deprecated) code

---

## Step 4: Fix `PipelineConfig.copyWith` sentinel for `expectedItemCount`

**Finding**: #7
**Agent**: pdf-agent
**File**: `lib/features/pdf/services/extraction/models/pipeline_config.dart`

### Steps
1. Change `copyWith` signature for `expectedItemCount` to use a sentinel pattern:
   ```dart
   // Add a private sentinel at file top:
   const _sentinel = Object();

   // In copyWith:
   Object? expectedItemCount = _sentinel,

   // In body:
   expectedItemCount: expectedItemCount == _sentinel
       ? this.expectedItemCount
       : expectedItemCount as int?,
   ```
2. This allows `config.copyWith(expectedItemCount: null)` to explicitly reset to null

### Verify
- Existing tests still pass (no test currently tries to reset to null, so no breakage)
- `pwsh -Command "flutter test test/features/pdf/extraction/models/"`

---

## Step 5: Fix `PipelineConfig.==` double comparison

**Finding**: #8
**Agent**: pdf-agent
**File**: `lib/features/pdf/services/extraction/models/pipeline_config.dart`

### Steps
1. Replace direct `amountTolerance != other.amountTolerance` with:
   `(amountTolerance - other.amountTolerance).abs() > 1e-10`
2. Same for `splitConfidenceMultiplier`
3. Update `hashCode` to use rounded values for these doubles:
   `(amountTolerance * 1e10).round()` and `(splitConfidenceMultiplier * 1e10).round()`

### Verify
- `pwsh -Command "flutter test test/features/pdf/extraction/models/"`

---

## Step 6: Remove dead code in `post_processor_v2.dart`

**Findings**: #9, #10, #11
**Agent**: pdf-agent
**File**: `lib/features/pdf/services/extraction/stages/post_processor_v2.dart`

### Steps
1. Remove `_MathValidationStatus.skipped` enum value (line 1251) and its unreachable switch case (grep for `case _MathValidationStatus.skipped:`)
2. Remove `numericUnitRatio` field from `_BatchAnalysis` class (line 1193) and its computation (line 745) and default value (line 708)
3. Remove `_analyzeBatchContext` method (line 850-853) and any call sites

### Verify
- `pwsh -Command "flutter analyze lib/features/pdf/services/extraction/stages/post_processor_v2.dart"`
- `pwsh -Command "flutter test test/features/pdf/extraction/"`

---

## Step 7: Fix pipeline core issues (SHA-256 hoist, magic number)

**Findings**: #14, #15
**Agent**: pdf-agent
**File**: `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`

### Steps
1. **SHA-256 hoist** (line 239): Move `sha256.convert(pdfBytes).toString()` before the retry loop (line ~218) into a local variable `final documentHash = sha256.convert(pdfBytes).toString();` and reference it inside the loop
2. **Magic number** (line 219): Replace `3` with `QualityThresholds.maxReExtractionAttempts + 1` and add the import for `quality_thresholds.dart` if not already present

### Verify
- `pwsh -Command "flutter test test/features/pdf/extraction/pipeline/"`

---

## Step 8: Clean up `models.dart` barrel re-exports

**Finding**: #16
**Agent**: pdf-agent
**File**: `lib/features/pdf/services/extraction/models/models.dart`

### Steps
1. Remove lines 17-23 that re-export pipeline files (`confidence_model.dart`, `coordinate_normalizer.dart`, `extraction_metrics.dart`, `extraction_pipeline.dart`, `pipeline_context.dart`, `result_converter.dart`)
2. Update any import sites that relied on `models.dart` to get pipeline classes -- add direct imports to `../pipeline/extraction_pipeline.dart` etc. where needed
3. Key files to check: `springfield_benchmark_test.dart` (finding #1 -- this uses `ExtractionPipeline` via `models.dart`; after removing the re-export, add explicit import)

### Verify
- `pwsh -Command "flutter analyze lib/features/pdf/services/extraction/"`
- `pwsh -Command "flutter test test/features/pdf/extraction/"`

---

## Step 9: Fix `springfield_benchmark_test.dart` missing import

**Finding**: #1
**Agent**: pdf-agent
**File**: `test/features/pdf/extraction/golden/springfield_benchmark_test.dart`

### Steps
1. Add explicit import: `import 'package:construction_inspector/features/pdf/services/extraction/pipeline/extraction_pipeline.dart';`
2. Note: If Step 8 removes the re-export from `models.dart`, this import becomes required. If Step 8 is deferred, the file already compiles via `models.dart` re-export but adding the explicit import is still correct.

### Verify
- `pwsh -Command "flutter analyze test/features/pdf/extraction/golden/springfield_benchmark_test.dart"`

---

## Step 10: Normalize import style across stages

**Finding**: #12
**Agent**: pdf-agent
**Files** (use relative `../` imports -- matches majority and Dart lint `prefer_relative_imports`):
- `lib/features/pdf/services/extraction/stages/row_classifier_v2.dart` -- lines 14-16 use `package:`, convert to relative
- `lib/features/pdf/services/extraction/stages/quality_validator.dart` -- lines 17-19 use `package:`, convert to relative
- `lib/features/pdf/services/extraction/stages/post_processor_v2.dart` -- lines 3-8 use `package:`, convert to relative
- `lib/features/pdf/services/extraction/stages/row_parser_v2.dart` -- line 16 uses `package:`, convert to relative

### Steps
1. For each file, replace `package:construction_inspector/features/pdf/services/extraction/` with `../` (adjusting path depth)
2. For `package:construction_inspector/core/logging/debug_logger.dart`, keep as `package:` import since it crosses feature boundaries

### Verify
- `pwsh -Command "flutter analyze lib/features/pdf/services/extraction/stages/"`

---

## Step 11: Fix `result_converter_test.dart` old stage name strings

**Finding**: #13
**Agent**: pdf-agent (or qa-testing-agent)
**File**: `test/features/pdf/extraction/pipeline/result_converter_test.dart`

### Steps
1. At line 217-221, replace V1 string literals with `StageNames.*` constants:
   - `'stage_0_document_analyzer'` -> `StageNames.documentAnalysis`
   - `'stage_2bi_page_renderer'` -> `StageNames.pageRendering`
   - `'stage_2bii_image_preprocessor'` -> `StageNames.imagePreprocessing`
   - `'stage_2biii_text_recognizer'` -> `StageNames.textRecognition`
2. Add import for `StageNames` if not present

### Verify
- `pwsh -Command "flutter test test/features/pdf/extraction/pipeline/result_converter_test.dart"`

---

## Step 12: Deduplicate `generate_golden_fixtures_test.dart`

**Finding**: #17
**Agent**: pdf-agent
**Files**:
- `integration_test/generate_golden_fixtures_test.dart` (KEEP -- requires real device/emulator)
- `test/features/pdf/extraction/generate_golden_fixtures_test.dart` (SIMPLIFY or DELETE)

### Steps
1. The `test/` version is a unit-test copy that duplicates the integration test. Since golden fixture generation requires a real PDF and OCR engine, the unit test version cannot actually run in CI.
2. **Option A (recommended)**: Delete the `test/` version entirely. The `integration_test/` version is the canonical one.
3. **Option B**: If keeping for local dev convenience, add `@Tags(['golden_generation'])` (already present) and add a comment explaining it duplicates the integration test.

### Verify
- `pwsh -Command "flutter test test/features/pdf/extraction/"` still passes (the test is tagged and excluded from normal runs)

---

## Step 13: Delete deprecated source and test directories

**Findings**: #2, #6, #18, #19, #20, #21
**Agent**: pdf-agent
**Files to delete**:
- `lib/features/pdf/services/extraction/deprecated/` (entire directory: `document_analyzer.dart`, `native_extractor.dart`, `structure_preserver.dart`, `README.md`)
- `test/features/pdf/extraction/deprecated/` (entire directory: 4 test files)
- `test/features/pdf/extraction/contracts/stage_0_to_2_contract_test.dart` (imports deprecated code)

### Steps
1. Verify no active code imports from `deprecated/` directory (already confirmed -- grep found no imports)
2. Delete `lib/features/pdf/services/extraction/deprecated/` recursively
3. Delete `test/features/pdf/extraction/deprecated/` recursively
4. Delete `test/features/pdf/extraction/contracts/stage_0_to_2_contract_test.dart`
5. If `StageNames.nativeExtraction` was not already removed in Step 2, remove it now (its only consumers are gone)

### Verify
- `pwsh -Command "flutter analyze lib/features/pdf/services/extraction/"`
- `pwsh -Command "flutter test test/features/pdf/extraction/"` -- all remaining tests pass

---

## Final Verification

After all steps:

1. `pwsh -Command "flutter analyze"` -- 0 issues
2. `pwsh -Command "flutter test test/features/pdf/extraction/"` -- all tests pass
3. Manual checks:
   - [ ] `temp.txt` deleted
   - [ ] No files import from `deprecated/`
   - [ ] `StageNames.elementValidation` used by ElementValidator
   - [ ] `PipelineConfig.copyWith(expectedItemCount: null)` works
   - [ ] SHA-256 computed once before retry loop
   - [ ] `models.dart` barrel does not re-export pipeline files
   - [ ] All stage files use relative imports (except cross-feature `package:` imports)

## Agent Assignment Summary

| Step | Agent | Estimated Effort |
|------|-------|-----------------|
| 1-13 | pdf-agent | All steps are within the PDF extraction pipeline domain |

All 13 steps can be executed by a single **pdf-agent** session since they are all within `lib/features/pdf/` and `test/features/pdf/`. The qa-testing-agent could verify afterward if desired.

## Dependencies Between Steps

```
Step 1  (temp.txt)           -- independent
Step 2  (StageNames)         -- independent
Step 3  (ElementValidator)   -- depends on Step 2
Step 4  (copyWith sentinel)  -- independent
Step 5  (double equality)    -- independent
Step 6  (PostProcessor dead) -- independent
Step 7  (pipeline core)      -- independent
Step 8  (barrel cleanup)     -- independent
Step 9  (benchmark import)   -- should run after Step 8
Step 10 (import style)       -- independent
Step 11 (test string lits)   -- depends on Step 2
Step 12 (golden dedup)       -- independent
Step 13 (deprecated delete)  -- MUST be last; depends on Steps 2, 3, 11
```

Safe parallel groups:
- **Group A** (independent): Steps 1, 2, 4, 5, 6, 7, 10, 12
- **Group B** (after Group A): Steps 3, 8, 9, 11
- **Group C** (after Group B): Step 13

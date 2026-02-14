# V2 Extraction Pipeline Refactoring Plan

## Context

Code review of the v2 PDF extraction pipeline found 3 correctness bugs, ~500 lines of duplicated production code, and ~1,800 lines of dead tests. This plan addresses all 28 findings in 7 sequential phases, each independently testable. Full review at `.claude/code-reviews/2026-02-14-v2-extraction-pipeline-review.md`.

---

## Phase 1: Bug Fixes (H1, H3, M9)

**Create** `lib/features/pdf/services/extraction/shared/quality_thresholds.dart`
- `QualityThresholds` class with constants `autoAccept=0.85`, `reviewFlagged=0.65`, `reExtract=0.45`
- `statusForScore(double score, {int attemptNumber = 0})` — single source of truth

**Modify** `lib/features/pdf/services/extraction/models/quality_report.dart`
- `isValid` getter (lines 40-61): delegate to `QualityThresholds.statusForScore()` — fixes bug where attempt >= 2 with score 0.45-0.64 was rejected

**Modify** `lib/features/pdf/services/extraction/stages/quality_validator.dart`
- `_determineStatus` (lines 303-308): delegate to `QualityThresholds.statusForScore()`
- `_handleEmptyItems` (line 516): replace hardcoded `higherDpiAutoPsm` with `_selectStrategy(attemptNumber)` — fixes wrong re-extraction strategy bug
- Replace all 0.85/0.65/0.45 magic numbers with `QualityThresholds.*`

**Modify** `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart`
- Lines 33-39: replace hardcoded thresholds with `QualityThresholds.*`

**Modify** `lib/features/pdf/services/extraction/models/pipeline_config.dart`
- `operator==` and `hashCode` (lines 161-185): include `duplicateSplitOverrides`

**Tests**: Update `quality_report_test.dart` with attempt-number scenarios

**Verify**: `pwsh -Command "flutter test test/features/pdf/extraction/"`

---

## Phase 2: Shared Utilities (M2, M3, M4)

**Create** `lib/features/pdf/services/extraction/shared/extraction_patterns.dart`
- `ExtractionPatterns.itemNumber` (`^\d+(\.\d+)?\.?$`), `.itemNumberStrict` (`^\d+(\.\d+)?$`), `.currency`
- Resolves inconsistent regex across 4 stages

**Create** `lib/features/pdf/services/extraction/shared/math_utils.dart`
- `MathUtils.median(List<double>)` — proper even-length averaging
- Fixes quality_validator.dart bug (floor division only at line 248)

**Create** `lib/features/pdf/services/extraction/shared/header_keywords.dart`
- `HeaderKeywords.byColumn` — merged superset from row_classifier + column_detector
- `HeaderKeywords.standardOrder` — canonical left-to-right column order

**Modify** 6 stage files to import shared utilities instead of local definitions:
- `row_classifier_v2.dart` — patterns + keywords
- `column_detector_v2.dart` — patterns + keywords + median
- `row_parser_v2.dart` — patterns
- `post_processor_v2.dart` — patterns
- `element_validator.dart` — median
- `quality_validator.dart` — median

**Verify**: `pwsh -Command "flutter test test/features/pdf/extraction/"`

---

## Phase 3: Pipeline Core Fixes (H2, M7, M8, M10, M13)

**Modify** `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`
- `toMap()`: add `config` and `document_hash` serialization
- `fromMap()`: restore config/hash properly, fix double Sidecar deserialization
- Exit condition (lines 294-304): simplify to `if (status != QualityStatus.reExtract)`

**Modify** `lib/features/pdf/services/extraction/pipeline/pipeline_context.dart`
- Remove mutable `Stopwatch elapsed` field, replace with `Duration? elapsed`
- Update `copyWith` accordingly

**Modify** `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart`
- Stage matching: use `StageNames.documentAnalysis` instead of `.contains('document')`
- `recordRun` line 103: use `result.context.config.expectedItemCount` instead of `null`

**Verify**: `pwsh -Command "flutter test test/features/pdf/extraction/"`

---

## Phase 4: Major Deduplication (H4, H5, H6, M11)

**Create** `lib/features/pdf/services/extraction/shared/text_quality_analyzer.dart`
- Mixin with 6 methods extracted from document_analyzer/document_quality_profiler:
  - `calculateSingleCharRatio`, `calculateCorruptionScore`, `calculateMixedCaseScore`
  - `calculateCurrencyCorruptionScore`, `generatePageWarnings`, `generatePageMetrics`
- Constants: `kMinCharsPerPage=50`, `kMaxSingleCharRatio=0.30`, `kCorruptionScoreThreshold=15`

**Modify** `lib/features/pdf/services/extraction/stages/document_quality_profiler.dart`
- Add `with TextQualityAnalyzer`, remove 6 duplicated methods (~200 lines removed)
- Move `PdfTextExtractor(document)` before page loop (M11)

**Move** `lib/features/pdf/services/extraction/stages/document_analyzer.dart` → `deprecated/document_analyzer_v2.dart`

**Move** `lib/features/pdf/services/extraction/stages/structure_preserver.dart` → `deprecated/structure_preserver_v2.dart`
- Also move `stages/native_extractor.dart` → `deprecated/` if still in stages/

**Verify barrel**: `stages/stages.dart` should NOT export moved files (confirm already excluded)

**Verify**: `pwsh -Command "flutter test test/features/pdf/extraction/"`

---

## Phase 5: Remaining Medium/Low Fixes (M6, M12, L1-L5)

**Modify** `lib/features/pdf/services/extraction/stages/quality_validator.dart`
- M6: Compute garbled count once in `_computeCoherence`, pass to `_generateIssues`

**Modify** `lib/features/pdf/services/extraction/stages/row_parser_v2.dart`
- M12: Replace `_mapColumnSemantics` inline header matching with `HeaderKeywords.byColumn`

**Modify** `lib/features/pdf/services/extraction/stages/column_detector_v2.dart`
- L1: Replace `firstWhere` + try/catch with `.where(...).firstOrNull`
- L2: Remove dead `_Gap.center` field
- L3: Refactor `_computeXOverlap` to accept `Rect` or raw coordinates instead of dummy `OcrElement`

**Modify** `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart`
- L5: Replace sequential `_db.insert()` in loop with `_db.batch()`

**Document** equality design decisions in `quality_report.dart` and `extraction_pipeline.dart` (L4)

**Verify**: `pwsh -Command "flutter test test/features/pdf/extraction/"`

---

## Phase 6: Test Cleanup (T1, T2, T3)

**Delete or move to `test/.../deprecated/`** — 5 test files testing dead code (~1,800 lines):
- `test/features/pdf/extraction/stages/stage_0_document_analyzer_test.dart`
- `test/features/pdf/extraction/stages/document_analyzer_integration_test.dart`
- `test/features/pdf/extraction/stages/stage_2a_native_extractor_test.dart`
- `test/features/pdf/extraction/stages/stage_3_structure_preserver_test.dart`
- `test/features/pdf/extraction/contracts/stage_2_to_3_contract_test.dart`

**Create** `test/features/pdf/extraction/helpers/mock_stages.dart`
- Extract 13 mock stage classes (~484 lines) from `re_extraction_loop_test.dart`

**Modify** `test/features/pdf/extraction/pipeline/re_extraction_loop_test.dart`
- Import shared mocks instead of inline definitions

**Modify** `test/features/pdf/extraction/helpers/test_fixtures.dart`
- Add missing factories: `testDocumentProfile()`, `testPageProfile()`, `testPipelineContext()`, `testSidecar()`

**Migrate** highest-duplication test files to use `test_fixtures.dart` helpers:
- Contract tests (CoordinateMetadata boilerplate)
- Stage tests (OcrElement construction)
- Pipeline tests (PipelineContext + Sidecar boilerplate)

**Verify**: `pwsh -Command "flutter test test/features/pdf/extraction/"`

---

## Phase 7: Final Polish (L6, barrel verification)

**Add** TODO comments for god class decomposition at top of:
- `column_detector_v2.dart` (1,215 lines)
- `post_processor_v2.dart` (1,261 lines)

**Verify barrels** `stages.dart` and `models.dart` are consistent with actual exports

**Final verification**:
```
pwsh -Command "flutter test test/features/pdf/extraction/"
pwsh -Command "flutter analyze"
```

---

## Summary

| Phase | Scope | Files Created | Files Modified | Est. Lines Saved |
|-------|-------|:---:|:---:|---:|
| 1 - Bug Fixes | H1, H3, M9 | 1 | 4 | ~50 |
| 2 - Shared Utils | M2, M3, M4 | 3 | 6 | ~120 |
| 3 - Pipeline Core | H2, M7, M8, M10, M13 | 0 | 3 | ~30 |
| 4 - Major Dedup | H4, H5, H6, M11 | 1 | 1 | ~500 |
| 5 - Med/Low Fixes | M6, M12, L1-L5 | 0 | 4 | ~80 |
| 6 - Test Cleanup | T1, T2, T3 | 1 | 8+ | ~2,000 |
| 7 - Polish | L6, barrels | 0 | 4 | ~0 |
| **Total** | **28 findings** | **6** | **30+** | **~2,780** |

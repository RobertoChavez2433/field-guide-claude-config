# Code Review: V3 Pipeline Migration
**Date**: 2026-02-19
**Scope**: Working tree — all modified/new files from the v2→v3 row parser migration
**Agents**: 3 parallel code-review-agents (non-overlapping domains)

---

## Domain Coverage

| Agent | Domain | Files Reviewed |
|-------|--------|----------------|
| Agent 1 | New V3 stage implementations | `row_parser_v3`, `field_confidence_scorer`, `header_consolidator`, `numeric_interpreter`, new models, `rules/` |
| Agent 2 | Modified pipeline & stage infrastructure | `extraction_pipeline`, `cell_grid`, `cell_extractor_v2`, `row_classifier_v3`, `text_recognizer_v2`, `stage_names`, `stages` |
| Agent 3 | Test files | All under `test/features/pdf/extraction/`, `integration_test/generate_golden_fixtures_test.dart`, `tool/generate_springfield_fixtures.dart` |

---

## Cross-Cutting Summary

| Priority | Count |
|----------|-------|
| **BUG** | 8 |
| **ARCH** | 5 |
| **QUALITY** | 12 |
| **COVERAGE** | 3 |
| **MINOR** | 8 |

---

## Agent 1: New V3 Stage Implementations

### Bugs

**1. Double-normalization in `_weightedGeometric`**
- `lib/features/pdf/services/extraction/stages/field_confidence_scorer.dart:298-333`
- `_scoreField()` normalizes inputs (lines 298–299), then `_weightedGeometric` calls `_normalizeConfidence` again (lines 325, 329, 333). `interpretationConfidence` is not pre-normalized before passing in — creating asymmetry. Today it's a no-op but will silently mask bugs if `_normalizeConfidence` logic changes.
- **Fix**: Remove `_normalizeConfidence` calls inside `_weightedGeometric`; normalize all inputs once, in `_scoreField`.

**2. European currency regex matches ambiguous inputs without documentation**
- `lib/features/pdf/services/extraction/rules/currency_rules.dart:125`
- `^\$?\d{1,3}(\.\d{3})+\.\d{2}$` matches `$1.000.00` which is ambiguous (OCR-corrupted US comma or European format). Falls through to this rule silently, resolves to `1000.00`. Likely correct but undocumented.
- **Fix**: Add doc comment explaining the ambiguity. Add test case for `$1.000.00`.

**3. Data-accounting hides skip/score distinction**
- `lib/features/pdf/services/extraction/stages/field_confidence_scorer.dart:134-136`
- `excludedCount: 0`, `outputCount: scoredItems.length` — every item (including section headers) always counts as output. `skippedCount` is not surfaced as `excludedCount`. StageReport always passes `isValid` but hides meaningful throughput data.
- **Fix**: Report `excludedCount: skippedCount` and `outputCount: scoredCount`, or document that this stage is an intentional 1:1 transform.

### Architecture Violations

**4. New model types not in barrel export**
- `lib/features/pdf/services/extraction/models/` — barrel `models.dart` does not export `interpreted_value.dart` or `interpretation_rule.dart`.
- **Fix**: Add both to `models.dart`.

**5. Model types defined inside a stage file**
- `lib/features/pdf/services/extraction/stages/numeric_interpreter.dart:13-71`
- `InterpretedCell`, `InterpretedGridRow`, `InterpretedGrid` are model classes defined in the stage file. Consumed by `row_parser_v3.dart` and `field_confidence_scorer.dart`, forcing them to import the stage.
- **Fix**: Extract to `models/interpreted_grid.dart`, export from `models.dart`.

**6. Stage name passed as parameter to `HeaderConsolidator`**
- `lib/features/pdf/services/extraction/stages/header_consolidator.dart:6`
- Every other stage uses `StageNames.*` constants internally. `HeaderConsolidator.consolidate()` receives `stageName` as a parameter — breaks convention.
- **Fix**: Accept a boolean `provisional` and resolve `StageNames.*` internally. Or create two named methods.

### Code Quality

**7. `_displayText` duplicated in two stage files**
- `lib/features/pdf/services/extraction/stages/row_parser_v3.dart:340` and `field_confidence_scorer.dart:400`
- Identical 5-line method. **Fix**: Move to extension on `InterpretedCell` or `shared/interpretation_utils.dart`.

**8. Fallback parsers duplicate NumericInterpreter work**
- `lib/features/pdf/services/extraction/stages/row_parser_v3.dart:360-371`
- `_parsePrice`/`_parseQuantity` are fallbacks for when `_numericValue` returns null. If NumericInterpreter couldn't parse it, the simpler fallback is unlikely to succeed. Two different parsing strategies for the same data.
- **Fix**: Either remove fallback parsers (trust NumericInterpreter) or move the fallback logic into a NumericInterpreter rule.

**9. Redundant `_computeFieldConfidence` in RowParserV3**
- `lib/features/pdf/services/extraction/stages/row_parser_v3.dart:373-426`
- RowParserV3 computes confidence with a 2-factor model. FieldConfidenceScorer immediately re-scores with a 3-factor model and overwrites the value. ~55 lines of dead computation.
- **Fix**: Remove `_computeFieldConfidence`; use a placeholder (`fieldsPresent / 6.0`) and let FieldConfidenceScorer be the single source.

**10. Hardcoded subtotal strings**
- `lib/features/pdf/services/extraction/stages/row_parser_v3.dart:90-92`
- `'SUBTOTAL'`, `'SUB TOTAL'`, `'SUB-TOTAL'` inline. `ExtractionPatterns` already has `total` regex patterns.
- **Fix**: Add subtotal patterns to `ExtractionPatterns`.

### Minor

**11. Dead `mergeLog` variable** — `row_parser_v3.dart:27` — never populated. Pass `const []` directly.

**12. `RegExp` created in loop** — `row_parser_v3.dart:368` — `RegExp(r'[\$,]')` per call. Hoist to `static final`.

**13. Misleading field name** — `currency_rules.dart:149` — `_singleDecimalPattern` used only for string padding, not matching. Rename to `_singleDecimalDigit`.

**14. `parts.removeLast()` mutates list** — `currency_rules.dart:310` — `sublist` would be more idiomatic.

### Positive Observations

- Zero deprecated imports — V2 constraint upheld throughout.
- Zero `firstWhere` without `orElse` across all reviewed files.
- `StageNames` constants used consistently (`StageNames.rowParsing`, `StageNames.numericInterpretation`, `StageNames.fieldConfidenceScoring`).
- Data-accounting assertions present in RowParserV3 (line 294), NumericInterpreter, and HeaderConsolidator.
- `InterpretationRule` abstraction is clean: minimal 3-member contract, composable rule sets, recursive delegation with `_interpretExcluding` preventing infinite loops.
- `InterpretedValue.copyWith` uses sentinel object correctly for nullable fields.
- No pixel coordinates — all these stages operate on text/semantic values only.
- RowParserV3 at 427 lines stays under the 500-line threshold.

---

## Agent 2: Modified Pipeline & Stage Infrastructure

### Bugs

**1. Deprecated `.grid` accessor used in production**
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart:863`
- `cellGrid.grid.length` calls `@Deprecated('Use rows instead.')`. Unnecessary intermediate list allocation.
- **Fix**: Replace with `cellGrid.rows.length`.

**2. `totalStages = 14` is stale**
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart:387`
- Actual stage call count is 13. `totalStages = 14` means the progress bar never reaches 100%. Previously flagged as `totalStages = 13` drifting — now drifted further.
- **Fix**: Update constant to 13, or derive from actual stage list length.

**3. `CellGrid.toMap()` double-serializes via deprecated `grid` key**
- `lib/features/pdf/services/extraction/models/cell_grid.dart:269`
- `toMap()` emits both `'grid': grid.map(...)` (triggering the deprecated `.grid` getter) and `'rows': rows.map(...)`. Every cell is serialized twice.
- **Fix**: Remove the `'grid'` key from `toMap()`. `fromMap` already has legacy fallback via `_rowsFromLegacyGrid`.

### Architecture Violations

**4. `_headerKeywords` duplicated and diverged from `shared/header_keywords.dart`**
- `lib/features/pdf/services/extraction/stages/row_classifier_v3.dart:36-53`
- Local `Set<String>` of 16 keywords vs `HeaderKeywords.byColumn` canonical source. Divergence: local adds `'NO'`, `'EST'`, `'EST.'`, `'BID'` (absent from shared); shared has multi-word phrases like `'DESCRIPTION OF WORK'` that local misses.
- **Recurrence**: Flagged in 2 prior reviews.
- **Fix**: Replace with flattened set derived from `HeaderKeywords.byColumn`.

**5. `_median` duplicated in `text_recognizer_v2.dart`**
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart:919-930`
- 4th instance of `_median` in the codebase. Unlike `grid_line_detector.dart`, this stage has no isolate constraint.
- **Recurrence**: Flagged in 2 prior reviews.
- **Fix**: Replace with `MathUtils.median(values)`.

### Code Quality

**6. `_runExtractionStages` is ~538 lines** — `extraction_pipeline.dart:375-913`
- Grew from the previously flagged 482 lines. Exceeds 100-line method threshold by 5x.
- **Fix**: Extract into `_runOcrStages()`, `_runClassificationStages()`, `_runTableExtractionStages()`.

**7. `ExtractionPipeline` file is 1,184 lines** — god class, previously reviewed 3 times.

**8. `TextRecognizerV2` file is 1,163 lines** — god class.
- `_CropOcrStats` class (lines 994–1162) is 169 lines of bookkeeping that belongs in `models/`.
- Inset computation methods total ~200 lines and form a cohesive module (`shared/whitespace_inset.dart`).

**9. `RowClassifierV3` is 742 lines** — approaching 500-line threshold.
- `_splitRowWithMultipleItemNumbers` (60 lines) and `_groupElementsByRow` (37 lines) could be standalone functions.

### Minor

**10.** `CellGrid` equality uses only `documentId` — same as `PipelineResult` pattern (intentional but worth noting it applies transitively).

**11.** `CellExtractorV2.extract` optional params with runtime `ArgumentError` (`cell_extractor_v2.dart:40-41`) — pipeline always passes `mergedRows` now; make it required.

**12.** `PipelineResult.fromMap` `documentHash` defaults to empty string on missing key (`extraction_pipeline.dart:87`) — silent degradation; should fail explicitly or log a warning.

### Positive Observations

- Clean deletion of `row_parser_v2.dart` — zero orphaned imports found anywhere in `lib/` or `test/`.
- `stages.dart` barrel: 17 exports, all active, correctly versioned, alphabetically ordered, no dead exports.
- `stage_names.dart`: 24 constants covering all pipeline stages including new sub-stages (`headerConsolidationProvisional/Final`, `numericInterpretation`, `fieldConfidenceScoring`, `rowMerging`). No magic strings in stage registrations.
- Data-accounting assertions: `CellExtractorV2` (lines 218–225) and `RowClassifierV3` (lines 143–147) both throw `StateError` on mismatch.
- `CellGrid.fromMap` handles legacy gracefully via `_rowsFromLegacyGrid`.
- `CellGridRow._rowTypeFromName` uses safe `firstWhere` with `orElse`.
- Normalized coordinates throughout — no pixel leakage detected.
- DI injection pattern consistent: all 17 stages use `stage ?? Stage()` constructor pattern.

---

## Agent 3: Test Files

### Bugs

**1. Unsafe `firstWhere` without `orElse` in pipeline integration test**
- `test/features/pdf/extraction/pipeline/extraction_pipeline_test.dart:169, 235, 239`
- 3 calls to `.firstWhere()` on `stageReports` without `orElse`. Crashes with `StateError` instead of meaningful test failure if stage names change.
- **Fix**: Use `.where(...).firstOrNull` with explicit `expect(x, isNotNull)`.

**2. Unsafe `firstWhere` without `orElse` in stage trace diagnostic test**
- `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart:1452, 1833, 2832`
- 3 of 5 `firstWhere` calls on `groundTruth` lack `orElse`. (Lines 2904, 3790 correctly include it.)
- **Fix**: Add `orElse` to the 3 missing callsites for consistency.

### Code Quality

**3. `stage_trace_diagnostic_test.dart` is 3,760 lines** — god test file
- Previously flagged at 1,000+ lines; has tripled. 25+ fixture variables in `setUpAll`.
- **Fix**: Split into per-stage-group files sharing a common fixture loader helper.

**4. `_createClassifiedRows` still duplicated in 3 files**
- `stage_4d_cell_extractor_test.dart:760`, `stage_4a_row_classifier_test.dart:936`, `header_consolidator_test.dart:268`
- `testClassifiedRows()` already exists in `test_fixtures.dart:224` for this exact purpose.
- **Fix**: Import from `test_fixtures.dart`.

**5. `_cell` + `_row` helpers duplicated across 5 test files**
- `stage_4e_row_parser_test.dart:297-312`, `stage_4e_row_parser_isolated_test.dart:159-175`, `row_parser_semantic_mapping_test.dart:286-302`, `stage_4d_to_4e_contract_test.dart:252-268`, `checksum_validation_test.dart:679-695`
- Near-identical `CellGridRow _row(RowType, List<String?>)` and `Cell _cell(String?)` in all five.
- **Fix**: Add `testCell()` and `testCellGridRow()` to `test_fixtures.dart`.

**6. `_standardColumnMap` duplicated with inconsistent header text across 5 files**
- `stage_4e_row_parser_test.dart`, `stage_4e_row_parser_isolated_test.dart`, `stage_4d_to_4e_contract_test.dart`, `checksum_validation_test.dart`, `numeric_interpreter_test.dart`
- Different header spellings (`"ITEM NO."` vs `"Item No."` vs `"Item"`) could mask semantic mapping bugs.
- **Fix**: Add `testStandardColumnMap()` to `test_fixtures.dart` with canonical header text.

**7. `testOcrElementFromEdges` redefined locally in cell extractor test**
- `test/features/pdf/extraction/stages/stage_4d_cell_extractor_test.dart:796-815`
- Already exists in `test_fixtures.dart:202`. The local copy shadows it.
- **Fix**: Remove local definition, import from `test_fixtures.dart`.

**8. Magic string `'springfield-864130'` hardcoded in 3 test files**
- `test/features/pdf/extraction/golden/springfield_golden_test.dart:78, 161, 182`
- **Fix**: Define `const kSpringfieldDocumentId = 'springfield-864130'` in `test_fixtures.dart`.

### Coverage Gaps

**9. New stages missing edge-case tests**
- `field_confidence_scorer_test.dart`: No test for empty `ParsedItems`. No test for items with missing `ocrConfidences`.
- `numeric_interpreter_test.dart`: No test for empty `CellGrid`. No test for cells with `null` values.

**10. Contract test `stage_4a_to_4a1_contract_test.dart` has only 1 test case**
- No empty-input, no multi-page header deduplication, no all-header-input cases.
- **Fix**: Add at minimum an empty-input contract test and a multi-page header contract test.

### Minor

**11. `MockRowParserV3.reportOutputCount = 1` always** — `mock_stages.dart:456-457`
- Data-accounting invariant not faithfully mocked. Tests checking stage report totals may get false passes.
- **Fix**: Set `reportOutputCount = items.length`.

**12.** `_baselineInsetForWidth` and `_plannedDepthForWidth` in `whitespace_inset_test.dart:382-391` duplicate production logic — consider `@visibleForTesting` exposure to avoid drift.

**13.** Quality score assertion `closeTo(0.916, 0.02)` in `springfield_golden_test.dart:163` is narrow; consider widening or documenting the expected range.

**14.** `stageToFilename` map duplicated in `generate_golden_fixtures_test.dart` and `generate_springfield_fixtures.dart` — extract to shared constant.

### Positive Observations

- Zero V2/deprecated imports anywhere in test directory — migration is complete.
- `mock_stages.dart` well-consolidated: 15 mock classes, single file, proper `StageNames` references.
- `test_fixtures.dart` adopted by 20 files with factory methods for all major types.
- Data-loss invariant (`outputCount + excludedCount == inputCount`) checked in every contract test.
- `row_classifier_v3_test.dart`: 13 well-scoped cases covering data rows, price continuations (strict/relaxed/rescue), description continuations, headers, totals, section headers, blanks, orphan price rows, gap detection, and missing-semantic fallback.
- Whitespace inset tests: synthetic coverage (8 cases) + Springfield integration snapshots guarding against pipe artifact regression.
- Golden tests use three-layer validation: regression baseline + GT comparison + convergence tracking.
- Checksum validation tests cover all 4 states + round-trip serialization + quality validator integration.

---

## KISS/DRY Opportunities (All Domains)

| Opportunity | Files | Effort |
|-------------|-------|--------|
| Extract `_displayText` to `InterpretedCell` extension | `row_parser_v3.dart`, `field_confidence_scorer.dart` | Trivial |
| Remove redundant `_computeFieldConfidence` from RowParserV3 | `row_parser_v3.dart` | Small (~55 lines removed) |
| Remove `_parsePrice`/`_parseQuantity` fallbacks | `row_parser_v3.dart` | Small (~12 lines removed) |
| Move `InterpretedCell`/`InterpretedGrid`/`InterpretedGridRow` to `models/` | `numeric_interpreter.dart` | Small |
| Remove deprecated `grid` key from `CellGrid.toMap()` | `cell_grid.dart` | Trivial |
| Replace local `_headerKeywords` with `HeaderKeywords.byColumn` | `row_classifier_v3.dart` | Small |
| Replace local `_median` with `MathUtils.median` | `text_recognizer_v2.dart` | Trivial |
| Extract `_CropOcrStats` to `models/crop_ocr_stats.dart` | `text_recognizer_v2.dart` | Small |
| Decompose `_runExtractionStages` into 3 helpers | `extraction_pipeline.dart` | Medium |
| Extract synthetic region builder from pipeline | `extraction_pipeline.dart` | Medium |
| Add `testCell`, `testCellGridRow`, `testStandardColumnMap` to `test_fixtures.dart` | 5 test files | Small |
| Add `kSpringfieldDocumentId` constant to `test_fixtures.dart` | 3 golden test files | Trivial |
| Extract `stageToFilename` to shared constant | 2 fixture generator files | Trivial |

---

## Recurrence Tracking

Issues flagged in prior reviews that reappear here:

| Issue | Prior Reviews | Status |
|-------|--------------|--------|
| `_headerKeywords` duplicated vs `shared/header_keywords.dart` | v2-pipeline, KISS/DRY | Still unfixed in v3 |
| `_median` duplicated vs `MathUtils` | v2-pipeline, KISS/DRY | Still unfixed in `text_recognizer_v2` |
| God class: `ExtractionPipeline` >500 lines | v2-pipeline (482-line method flagged) | Grew to 1,184 lines |
| God class: `TextRecognizerV2` >500 lines | KISS/DRY | Grew to 1,163 lines |
| `totalStages` magic number drifting | v2-pipeline (`= 13`) | Now `= 14`, actual is 13 |
| `stage_trace_diagnostic_test.dart` god test | springfield-fixture-regen scorecard | Grew from 1,000+ to 3,760 lines |
| Duplicated test helpers vs `test_fixtures.dart` | v2-pipeline, KISS/DRY | Still present in 5 files for `_cell`/`_row`/`_columnMap` |

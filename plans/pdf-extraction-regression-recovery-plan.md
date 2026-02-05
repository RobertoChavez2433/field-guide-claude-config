# PDF Extraction Regression Recovery Plan

**Created**: 2026-02-05  
**Goal**: Restore Springfield extraction to 95%+ (125+/131) and prevent regressions by fixing preprocessing reliability, OCR artifact cleanup, header detection robustness, and column-shift false positives.

## Why This Plan Exists

Recent logs show a regression from 85/131 items (65%) to 67/131 (51%) with heavy OCR artifacts and header detection failures. Multiple fixes appear in the repo but are not reflected in the most recent runtime logs, suggesting build/version drift and missing observability. This plan focuses on:
- Making preprocessing non-optional and visible in logs
- Eliminating gridline OCR artifacts at the source and via cleanup
- Hardening header detection and column matching for multi-line headers
- Preventing false column-shift repairs
- Adding regression guards so we stop bouncing backward

## Phases (Each Phase = One PR)

### Phase 0: Baseline + Observability Lock-In (PR 0)
**Goal**: Ensure logs prove which code path ran and whether preprocessing was applied.

**Scope**
- Add build/version stamp to logs and diagnostics
- Add preprocessing success/failure logging
- Add re-OCR source logging (raw vs preprocessed)
- Add a one-line extraction summary at end of import

**Changes**
- `lib/core/logging/debug_logger.dart`
  - Add `DebugLogger.meta()` or extend `app_session.log` with build SHA, build time, branch.
- `lib/features/pdf/services/pdf_import_service.dart`
  - Log preprocessing start/finish with bytes size and elapsed time.
  - On exception, log reason and mark fallback path.
  - Log which image source is used for OCR and re-OCR.
  - Add a final summary log: items in/out, invalid item numbers, dedupe removals.
- `lib/features/pdf/services/table_extraction/models/extraction_diagnostics.dart`
  - Add fields for `preprocessingUsed`, `preprocessingFailed`, `reOcrUsed`, `reOcrSource`.

**Tests**
- Update `test/core/logging/debug_logger_test.dart` if new log category is added.
- Add a unit test to ensure preprocessing failure logs a fallback warning.

**Acceptance Criteria**
- Logs show build SHA + preprocessing status in the same session.
- pdf_import.log includes "Preprocessing complete" or "Preprocessing failed → fallback".

---

### Phase 1: Preprocessing Reliability + Re-OCR Consistency (PR 1)
**Goal**: Preprocessing never silently disables and re-OCR uses preprocessed images.

**Scope**
- Remove silent fallback to raw images
- Ensure re-OCR uses preprocessed page images
- Keep raw images for line detection

**Changes**
- `lib/features/pdf/services/pdf_import_service.dart`
  - Store both raw `pageImages` (for line detection) and `preprocessedPageImages` (for OCR and re-OCR).
  - If full preprocessing fails, retry with downscaled binarization before falling back to raw.
- `lib/features/pdf/services/table_extraction/table_extractor.dart`
  - Pass `preprocessedPageImages` to cell re-OCR path.
- `lib/features/pdf/services/table_extraction/cell_extractor.dart`
  - Use preprocessed images for `_reOcrMergedBlock`.
- `lib/features/pdf/services/ocr/image_preprocessor.dart`
  - Add a lightweight fallback that still includes adaptive thresholding.
  - Deprecate `preprocessLightweight()` or redirect to full preprocessing + downscale.

**Tests**
- `test/features/pdf/services/ocr/image_preprocessor_test.dart`
  - Add test that fallback preprocessing still produces binarized output (only 0/255).
- `test/features/pdf/table_extraction/cell_extractor_test.dart`
  - Add test verifying re-OCR uses preprocessed images (mock/image flag).

**Acceptance Criteria**
- No preprocessing fallback to raw unless both full and fallback fail.
- reOcr uses preprocessed images (logged per Phase 0).

---

### Phase 2: OCR Artifact Cleanup (PR 2)
**Goal**: Remove gridline artifacts from item numbers and general text.

**Scope**
- Expand `cleanOcrArtifacts`
- Add item-number-specific cleanup before normalization
- Warn on heavy cleaning

**Changes**
- `lib/features/pdf/services/table_extraction/post_process/post_process_normalization.dart`
  - Remove brackets, dashes, tildes, curly quotes, stray punctuation.
- `lib/features/pdf/services/table_extraction/table_row_parser.dart`
  - Add `_cleanItemNumberArtifacts` and call before `_normalizeItemNumber`.
  - Add warning when heavy cleaning occurs.

**Tests**
- `test/features/pdf/table_extraction/post_process/post_process_normalization_test.dart`
  - Add gridline artifact cleaning tests.
- `test/features/pdf/table_extraction/table_row_parser_test.dart`
  - Add item-number artifact cleanup tests.

**Acceptance Criteria**
- Item numbers never include `[ ] ~ — _ =` artifacts after parsing.
- Warnings emitted for heavy cleaning cases.

---

### Phase 3: Header Detection + Multi-Line Matching (PR 3)
**Goal**: Detect headers on page 1 and multi-line header layouts reliably.

**Scope**
- Normalize newlines and whitespace in keyword matching
- Synchronize keyword lists across TableLocator and HeaderColumnDetector
- Add multi-line keyword patterns

**Changes**
- `lib/features/pdf/services/table_extraction/table_locator.dart`
  - Add `_containsAnyNormalized` that removes newlines and collapses spaces.
  - Expand keyword lists for multi-line headers (e.g., `ITEM\nNO.`).
- `lib/features/pdf/services/table_extraction/header_column_detector.dart`
  - Normalize newlines in `_containsAny`.
  - Remove bare `NO` to reduce false positives.
  - Add Springfield-style multi-line patterns (`EST.\nQUANTITY`, `ITEM\nNO.`).
- `lib/features/pdf/services/table_extraction/table_extractor.dart`
  - Add detailed header-element logging for diagnostics (if missing).

**Tests**
- `test/features/pdf/table_extraction/table_locator_test.dart`
  - Add test for multi-line header matching in locator.
- `test/features/pdf/table_extraction/header_column_detector_test.dart`
  - Add test for multi-line keyword matching and 6/6 column detection.

**Acceptance Criteria**
- Header detection succeeds on page 1 with only 1-2 data rows.
- Column detection finds all 6 columns (not fallback).

---

### Phase 4: Column Shift False-Positive Prevention (PR 4)
**Goal**: Stop shifting page-number artifacts into quantity.

**Scope**
- Add page number detection in splitter
- Add batch-level validation in engine

**Changes**
- `lib/features/pdf/services/table_extraction/post_process/post_process_splitter.dart`
  - Add `_isLikelyPageNumber` and skip shift when detected.
- `lib/features/pdf/services/table_extraction/post_process/post_process_engine.dart`
  - Add `_validateColumnShift` using batch context.

**Tests**
- `test/features/pdf/table_extraction/post_process/post_process_splitter_test.dart`
  - Page-number detection tests.
- `test/features/pdf/table_extraction/post_process/post_process_engine_test.dart`
  - Batch-level validation test.

**Acceptance Criteria**
- No "unit held qty" shift for isolated single-digit values.
- Column shift still applies for real systematic misalignments.

---

### Phase 5: Regression Guard + Springfield Verification (PR 5)
**Goal**: Make regressions impossible to miss.

**Scope**
- Strengthen Springfield integration tests
- Add baseline extraction count thresholds
- Log summary metrics per run

**Changes**
- `test/features/pdf/table_extraction/springfield_integration_test.dart`
  - Add regression guard: never below 85/131 items.
  - Add check: item numbers must be numeric post-cleaning.
- `lib/features/pdf/services/table_extraction/table_extractor.dart`
  - Add summary metrics to diagnostics and log output.

**Tests**
- `flutter test test/features/pdf/table_extraction/springfield_integration_test.dart -r expanded`

**Acceptance Criteria**
- Springfield fixture consistently >= 125 items.
- No non-numeric item numbers in final output.

---

### Phase 6: Verification + Cleanup (PR 6)
**Goal**: Confirm stability and update project state.

**Scope**
- Run full PDF table extraction test suite
- Update `_state.md` and plan status

**Verification**
- `flutter test test/features/pdf/table_extraction/ -r expanded`
- `flutter test test/features/pdf/services/ocr/ -r expanded`

**Acceptance Criteria**
- All tests pass.
- Logs show preprocessing path and summary metrics.

---

## Risks + Mitigations
- **Risk**: Preprocessing fallback still too heavy for Windows  
  **Mitigation**: Add downscale before binarization; log sizes and timings.

- **Risk**: New artifact cleanup removes valid characters  
  **Mitigation**: Apply aggressive cleanup only to item numbers, not descriptions.

- **Risk**: Multi-line header matching introduces false positives  
  **Mitigation**: Retain density + data-row lookahead gating.

## Rollback Strategy
Each phase is isolated to a small file set and can be reverted by restoring the specific files touched in that PR.

## Success Definition
1. Springfield extraction is stable at 95%+ (125+/131).
2. Header detection and column detection succeed without fallback.
3. No gridline artifacts appear in item numbers.
4. Logs prove preprocessing and build version.

# PDF Extraction Regression Recovery Plan v2

**Created**: 2026-02-05  
**Goal**: Restore Springfield extraction to 95%+ (125+/131) and stop regressions by fixing build drift, header detection, column detection, preprocessing artifacts, and shift false-positives.

## Why This Plan Exists
Latest logs (`session_2026-02-05_11-10-58`) show:
- `TableLocator` starts at **"3.01 Unit Price Bids"** (wrong header), causing `tableStartY` to be wrong and header elements to be filtered out.
- Column detection falls back to ratios (confidence ~0.17) because header elements are missing.
- Item numbers still contain OCR/gridline artifacts, and header rows are slipping into parsed items.
- `app_session.log` lacks Build SHA/Branch/Time and `pdf_import.log` lacks newer fields like `primary` or `reOcrSource`, indicating **build drift** (running old code).

We need to close implementation gaps, harden header detection, and lock in build observability so we can’t “go backward” without seeing it immediately.

## Root Causes (Observed)
1. **Build/version drift**: Logs do not show Build SHA/Branch/Time or newer log fields, meaning the running app is not the code in the repo.
2. **False header acceptance**: Section heading “3.01 Unit Price Bids” qualifies as a header under permissive rules; it hijacks `tableStartY`.
3. **Header extraction anchored to wrong startY**: Header elements are filtered to within ±100px of `tableStartY`, so real header rows are dropped when startY is wrong.
4. **Residual OCR artifacts**: Item numbers and units retain gridline noise; header rows slip through when “NO” lacks a period.
5. **Column-shift noise**: Numeric artifacts in unit column still trigger shifts without enough batch context or sample-size guard.

## Phases (Each Phase = One PR)

### Phase 0: Build Drift Lock-In (PR 0)
**Goal**: Ensure logs prove exactly which build ran.

Tasks:
- Confirm Build SHA/Branch/Time are printed in `app_session.log` at app start.
- Add a build step (or manual command) to pass `--dart-define=BUILD_SHA=...` etc.
- Add one test to verify preprocessing fallback logs when full preprocessing fails.

Tests:
- `test/core/logging/debug_logger_test.dart`
- `test/features/pdf/services/pdf_import_service_ocr_test.dart` (fallback log test)

Acceptance:
- `app_session.log` shows Build SHA/Branch/Time.
- `pdf_import.log` shows fallback preprocessing messages when forced.

---

### Phase 1: Header Detection Hardening (PR 1)
**Goal**: Stop section headings from becoming table headers.

Tasks:
- Require at least one **core** column keyword (Item/Description/Quantity/Amount) for header acceptance.
- Keep density gating for 2-keyword headers (≥60% density).
- Ensure multi-row headers are combined even when the first row already qualifies.
- Keep lookahead permissive enough to accept page-1 headers with few rows, including cross-page lookahead.

Tests:
- `test/features/pdf/table_extraction/table_locator_test.dart`

Acceptance:
- “3.01 Unit Price Bids” is rejected as header.
- “Description … Bid Amount” + “Quantity” is accepted as multi-row header.

---

### Phase 2: Header Extraction Fallback (PR 2)
**Goal**: Prevent wrong `startY` from zeroing header elements.

Tasks:
- In `TableExtractor`, if filtered header elements are empty or <2, fall back to the nearest header Y positions rather than returning empty.
- Log when fallback header extraction is used.

Tests:
- Add a unit test in `table_extractor_test.dart` for fallback header element selection.

Acceptance:
- Header column detection does not fall back to ratios when a valid header exists but `startY` is wrong.

---

### Phase 3: OCR Artifact Cleanup Expansion (PR 3)
**Goal**: Remove gridline artifacts from all fields used for parsing.

Tasks:
- Apply OCR artifact cleanup to unit text before normalization.
- Extend header-row detection in `TableRowParser` to skip `NO` without a period.
- Log heavy artifact removal for item numbers (already in place, keep).

Tests:
- Add unit cleanup tests in `table_row_parser_test.dart`.
- Update any failing parser tests due to added cleanup.

Acceptance:
- Units like `[FT]`, `—EA`, `_LF` normalize correctly.
- Header rows with item cell “NO” are skipped.

---

### Phase 4: Column Shift False-Positive Guard (PR 4)
**Goal**: Avoid shifting isolated numeric artifacts.

Tasks:
- Add minimum batch size before `hasSystematicShift` can be true (e.g., ≥10 items).
- Keep per-item page-number detection but require additional context (raw unit looks numeric + empty qty + no unit).

Tests:
- `test/features/pdf/table_extraction/post_process/post_process_engine_test.dart`
- `test/features/pdf/table_extraction/post_process/post_process_splitter_test.dart`

Acceptance:
- Isolated “2” values in unit column do NOT shift to quantity.
- Systematic shifts still apply when many rows show the pattern.

---

### Phase 5: Regression Guard + Springfield Verification (PR 5)
**Goal**: Make regressions impossible to miss.

Tasks:
- Run Springfield fixtures and assert ≥125/131 items.
- Log extraction summary metrics per run (already present; confirm in logs).

Tests:
- `test/features/pdf/table_extraction/springfield_integration_test.dart`

Acceptance:
- Springfield extraction stable at ≥125 items.
- Logs show `reOcrSource`, preprocessing flags, and build metadata.

---

### Phase 6: Verification + Cleanup (PR 6)
**Goal**: Confirm stability and update project state.

Tasks:
- Run full PDF extraction test suite.
- Update `_state.md` with current session and status.

Tests:
- `flutter test test/features/pdf/table_extraction/ -r expanded`
- `flutter test test/features/pdf/services/ocr/ -r expanded`

Acceptance:
- All tests pass.
- Logs show expected build metadata and extraction summary.

## Success Definition
1. Springfield extraction ≥95% (125+/131).
2. Header detection/column detection succeed without ratio fallback.
3. No gridline artifacts in item numbers or units.
4. Logs prove build SHA/Branch/Time and preprocessing path.

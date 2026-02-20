# Agent Memory — QA Testing Agent

## Patterns Discovered

### PDF Test Suite Baseline (2026-02-19, post grid_line_remover addition + stage_2b rewrite)
- **Total PDF Tests**: 855 passed, 0 failed (extraction suite only — does not include golden tests)
- **Golden tests**: 76/76 pass, Pipeline Scorecard: **55 OK | 0 LOW | 0 BUG** (57 metrics) — CLEAN!
- **Quality score**: Springfield overall_score = ~0.977 (was 0.916), QualityStatus.autoAccept
- The aspirational 0-BUG/0-LOW assertions in `stage_trace_diagnostic_test.dart` now PASS
- **Changes in this baseline**: Added `grid_line_remover.dart` (Stage 2B-ii.6, OpenCV morphology + inpaint), removed `whitespace_inset_test.dart` (old inset scan methods removed), `text_recognizer_v2.dart` rewritten with cell-level OCR (PSM routing, low-confidence re-OCR, crop upscaling), added `opencv_dart: ^2.2.1+3` dependency, fixtures regenerated
- **Known flutter_tester.exe lock issue**: Multiple flutter_tester.exe processes linger after test runs and lock `build/native_assets/windows/sqlite3.x64.windows.dll`. Run `taskkill /F /IM flutter_tester.exe` to unblock before next test run.
- Test locations now: `test/features/pdf/extraction/` (contracts, golden, integration, models, ocr, pipeline, stages)
- 1 expected skip: Springfield PDF integration test (requires `--dart-define=SPRINGFIELD_PDF` path)
- Production files: `field_confidence_scorer.dart`, `numeric_interpreter.dart`, `row_parser_v3.dart`, `header_consolidator.dart`, `grid_line_remover.dart` + `interpretation_rule.dart`, `interpreted_value.dart`, `rules/` directory

### Skipped Tests Pattern
TesseractInitializer tests skip when `eng.traineddata` asset not available in test environment. This is expected and acceptable - these tests would run in full integration/E2E scenarios.

### DPI Override Bug Pattern (2026-02-07)
**Symptom**: Tesseract returns "Empty page!!" despite correct DPI being set at Dart level.
**Root Cause**: Native C++ code in `packages/flusseract/src/flusseract.cpp` unconditionally overwrites `user_defined_dpi` with 70 DPI fallback in `SetPixImage()`.
**Fix**: Check if `user_defined_dpi` is set via `GetIntVariable()` before applying fallback.
**Prevention**: When adding Tesseract configuration options, ensure native FFI layer respects variable precedence (user-defined > embedded > fallback).

## Gotchas & Quirks

### Flutter Command Execution
ALWAYS use `pwsh -Command "flutter ..."` wrapper. Git Bash silently fails on Flutter commands on Windows.

### Native Plugin Rebuilds
After modifying native C++ code in `packages/flusseract/`, run `flutter clean && flutter build windows --debug` to force rebuild. The plugin is built as part of the app build, not independently.

## Architectural Decisions

### PR Verification Pattern (2026-02-08)
When verifying multiple related PRs:
1. Add model tests first (unit tests for new types like HeaderAnchor)
2. Extend existing model tests for new fields (e.g., TableRegion.headerAnchors)
3. Run incremental test suites (models → feature → services → full suite)
4. Verify implementation by reading actual code changes (Grep for method names)
5. Run full regression suite at end (all PDF tests: 1431 tests)

## Frequently Referenced Files

### Test Directories
- `test/features/pdf/extraction/stages/` - V2 pipeline stage tests
- `test/features/pdf/extraction/ocr/` - OCR engine and preprocessing tests
- `test/features/pdf/extraction/models/` - Model serialization and validation tests
- `test/features/pdf/extraction/contracts/` - Stage-to-stage contract tests
- `test/features/pdf/extraction/pipeline/` - Pipeline orchestration tests
- `test/features/pdf/extraction/integration/` - End-to-end extraction flows
- `test/features/pdf/extraction/golden/` - Golden file tests

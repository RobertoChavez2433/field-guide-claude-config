# Agent Memory — QA Testing Agent

## Patterns Discovered

### PDF Test Suite Baseline (2026-02-08)
- **Total PDF Tests**: 1431 tests passing across 65+ test files (+58 tests since 2026-02-07)
- Test locations: `test/features/pdf/table_extraction/`, `test/features/pdf/services/ocr/`, `test/features/pdf/parsers/`, `test/features/pdf/integration/`
- **Table Extraction Tests**: 704 tests
- **PDF Services Tests**: 327 tests

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

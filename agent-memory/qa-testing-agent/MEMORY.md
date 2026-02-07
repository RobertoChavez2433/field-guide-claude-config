# Agent Memory — QA Testing Agent

## Patterns Discovered

### PDF Test Suite Baseline (2026-02-07)
- **Total PDF Tests**: 1373 tests passing across 64+ test files
- Test locations: `test/features/pdf/table_extraction/`, `test/features/pdf/services/ocr/`, `test/features/pdf/parsers/`, `test/features/pdf/integration/`

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

## Frequently Referenced Files

### Test Directories
- `test/features/pdf/table_extraction/` - Core table extraction logic (614 tests)
- `test/features/pdf/services/ocr/` - OCR engine and preprocessing (202 tests)
- `test/features/pdf/parsers/` - Text parsing strategies
- `test/features/pdf/integration/` - End-to-end extraction flows

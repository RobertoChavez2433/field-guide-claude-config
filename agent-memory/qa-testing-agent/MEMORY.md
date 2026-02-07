# Agent Memory — QA Testing Agent

## Patterns Discovered

### PDF Test Suite Baseline (2026-02-06)
- **Table Extraction Tests**: 614 tests passing (15 test files)
- **OCR Tests**: 202 tests passing (18 test files), 4 skipped (require eng.traineddata asset)
- **Total PDF Tests**: 816+ passing across 64+ test files
- Test locations: `test/features/pdf/table_extraction/`, `test/features/pdf/services/ocr/`, `test/features/pdf/parsers/`, `test/features/pdf/integration/`

### Skipped Tests Pattern
TesseractInitializer tests skip when `eng.traineddata` asset not available in test environment. This is expected and acceptable - these tests would run in full integration/E2E scenarios.

## Gotchas & Quirks

### Flutter Command Execution
ALWAYS use `pwsh -Command "flutter ..."` wrapper. Git Bash silently fails on Flutter commands on Windows.

## Architectural Decisions

## Frequently Referenced Files

### Test Directories
- `test/features/pdf/table_extraction/` - Core table extraction logic (614 tests)
- `test/features/pdf/services/ocr/` - OCR engine and preprocessing (202 tests)
- `test/features/pdf/parsers/` - Text parsing strategies
- `test/features/pdf/integration/` - End-to-end extraction flows

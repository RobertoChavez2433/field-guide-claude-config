# Key Learnings & Patterns

## Project: Field Guide App (Construction Inspector)

### Build Tips
- Build folder lock: kill dart.exe and construction_inspector.exe, wait 5s, then delete build/

### PDF Extraction Pipeline
- TableExtractor pipeline: TableLocator -> ColumnDetector -> CellExtractor -> TableRowParser
- ColumnDetector orchestrates both HeaderColumnDetector (keywords) and LineColumnDetector (gridlines)
- Springfield PDF: 131 items across 6 pages, headers split multi-line ("Item\nNo.", "Est.\nQuantity")
- Page 6 sometimes OCRs text backwards - _detectAndFixReversedText() added to tesseract_ocr_engine.dart
- **New**: RowClassifier (Phase 1A pre-column, Phase 1B post-column) classifies rows into 6 types
- **New**: TableRegionDetector uses two-pass linear scan with cross-page header confirmation

### Logging System
- DebugLogger: 9 categories in `Troubleshooting/Detailed App Wide Logs/session_YYYY-MM-DD_HH-MM-SS/`
- PDF/OCR pipeline has excellent coverage (59+ calls)
- Column detection pipeline now has logging (added Session 284)
- Log files: app_session.log, ocr.log, pdf_import.log, sync.log, database.log, auth.log, navigation.log, errors.log, ui.log

### Agent Usage Patterns
- User prefers ALL work done via agents - research, implementation, testing
- Use parallel agents when tasks are independent
- pdf-agent for PDF analysis; frontend-flutter-specialist-agent for Dart code changes
- code-review-agent for verification; qa-testing-agent for testing
- Agents sometimes revert each other's changes - verify file state after parallel agent runs
- **Background agents often hit permission issues** - main thread has permissions, subagents may not

### Dart/Flutter Gotchas
- Raw strings `r'...'` cannot contain single quotes - use `\x27` instead
- Pre-existing test failure: table_locator_test "rejects section heading" (expects Y=1700, gets 1610)
- post_process_normalization.dart `cleanOcrArtifacts()` removes commas from text (regex `[;:,!]`)

### CRITICAL: Memory File Location
- **ALWAYS** use `.claude/memory/MEMORY.md` (project dir), NOT the auto-memory dir
- Wrong: `C:\Users\rseba\.claude\projects\...\memory\MEMORY.md`
- Right: `C:\Users\rseba\Projects\Field Guide App\.claude\memory\MEMORY.md`

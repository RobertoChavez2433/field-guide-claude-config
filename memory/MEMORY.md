# Key Learnings & Patterns

## Project: Field Guide App (Construction Inspector)

### Build Tips
- Build folder lock: kill dart.exe and construction_inspector.exe, wait 5s, then delete build/

### PDF Extraction Pipeline
- **OCR-ONLY pipeline** — Native text extraction is OFF. CMap corruption across PDFs made native extraction unreliable. 2 weeks spent decoding corruption, scrapped. DO NOT suggest native/hybrid extraction.
- V2 pipeline: DocumentQualityProfiler → PageRenderer → ImagePreprocessor → TextRecognizer → ElementValidator → RowClassifier → RegionDetector → ColumnDetector → CellExtractor → RowParser → PostProcessor → QualityValidator
- Springfield PDF: 131 items across 6 pages, headers split multi-line ("Item\nNo.", "Est.\nQuantity")
- **PSM Mode**: Default PSM=6 (single block) produces garbage on table-heavy pages. Needs investigation for table-structured PDFs.
- RowClassifier (Phase 1A pre-column, Phase 1B post-column) classifies rows into 6 types
- TableRegionDetector uses two-pass linear scan with cross-page header confirmation
- **OCR Preprocessing**: Removed binarization — clean PDFs need grayscale + contrast only. Binarization destroyed 92% of image data.
- **Row Classifier**: Numeric content gate — DATA rows must have numeric values in qty/price/amount columns
- **Post-Processing**: Validation validates item numbers (^\d+(\.\d+)?$) and units (57 known units)

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
- **FIXED (2026-02-11)**: All agents now have `permissionMode: acceptEdits` to prevent file-write failures
- Global `~/.claude/settings.json` has `"defaultMode": "acceptEdits"` so built-in subagents inherit it
- Known Claude Code Windows bugs: #4462, #7032, #5465 - subagent file writes may not persist
- Context handoff: subagents start fresh - always pass full context in Task prompt or write to `.claude/plans/`

### Dart/Flutter Gotchas
- Raw strings `r'...'` cannot contain single quotes - use `\x27` instead
- Pre-existing test failure: table_locator_test "rejects section heading" (expects Y=1700, gets 1610)
- post_process_normalization.dart `cleanOcrArtifacts()` removes commas from text (regex `[;:,!]`)

### CRITICAL: Memory File Location
- **ALWAYS** use `.claude/memory/MEMORY.md` (project dir), NOT the auto-memory dir
- Wrong: `C:\Users\rseba\.claude\projects\...\memory\MEMORY.md`
- Right: `C:\Users\rseba\Projects\Field Guide App\.claude\memory\MEMORY.md`

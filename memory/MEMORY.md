# Key Learnings & Patterns

## Project: Field Guide App (Construction Inspector)

### Build Commands
- **CRITICAL**: Git Bash silently fails on Flutter. Always use: `pwsh -Command "flutter run -d windows"`
- Kill old processes before rebuild: `Stop-Process -Name 'construction_inspector' -Force`
- Build folder lock: kill dart.exe and construction_inspector.exe, wait 5s, then delete build/

### PDF Extraction Pipeline
- TableExtractor pipeline: TableLocator -> ColumnDetector -> CellExtractor -> TableRowParser
- ColumnDetector orchestrates both HeaderColumnDetector (keywords) and LineColumnDetector (gridlines)
- Springfield PDF: 131 items across 6 pages, headers split multi-line ("Item\nNo.", "Est.\nQuantity")
- Page 6 sometimes OCRs text backwards - _detectAndFixReversedText() added to tesseract_ocr_engine.dart

### Pipeline Status (as of Plan v2.1 Review - Session 295, 2026-02-05)
- **Plan v2.1 REVIEWED & UPDATED** — Plan: `.claude/plans/pdf-table-structure-analyzer-v2.md`
- **690/690 tests pass (100%)**: 482 table_extraction + 202 OCR + 6 debug_logger
- 14 design decisions from brainstorming review integrated into plan
- Key decisions: Two-pass classification (1A pre-column, 1B post-column), cross-page header lookahead, item regex `^\d+(\.\d+)?\.?$`, column count 3-8, bootstrap+anchor merge, optional parser integration
- Implementation order: Phase 1A → Phase 2 → Phase 3 → Phase 1B → Phase 4 → Phase 5 → Phase 6
- **NOT YET TESTED against Springfield PDF** — need rebuild + test to measure improvement
- Target: 95%+ (125+/131 items), up from 65% (85/131) baseline

### Logging System
- DebugLogger: 9 categories in `Troubleshooting/Detailed App Wide Logs/session_YYYY-MM-DD_HH-MM-SS/`
- PDF/OCR pipeline has excellent coverage (59+ calls)
- Column detection pipeline now has logging (added Session 284)
- Log files: app_session.log, ocr.log, pdf_import.log, sync.log, database.log, auth.log, navigation.log, errors.log, ui.log

### Claude Directory Modernization (Session 294, 2026-02-05)
- 9-phase modernization complete: cleanup, architecture.md trim, skill frontmatter, commands→skills, agent modernization, CLAUDE.md update, supporting files, agent memory
- architecture.md trimmed from 260→167 lines (~620 tokens saved per .dart file edit)
- 6 skills now have YAML frontmatter; brainstorming + systematic-debugging are user-invocable
- end-session/resume-session migrated from commands/ to skills/ with disable-model-invocation
- 4 agents have memory:project (pdf, qa-testing, code-review, frontend-flutter)
- code-review-agent: disallowedTools Write/Edit/Bash (read-only)
- planning-agent: model upgraded to opus, disallowedTools Edit
- Agent memory dirs at `.claude/agent-memory/<agent-name>/MEMORY.md`

### Agent Usage Patterns
- User prefers ALL work done via agents - research, implementation, testing
- Use parallel agents when tasks are independent
- pdf-agent for PDF analysis; frontend-flutter-specialist-agent for Dart code changes
- code-review-agent for verification; qa-testing-agent for testing
- Agents sometimes revert each other's changes - verify file state after parallel agent runs
- **Background agents often hit permission issues** — main thread has permissions, subagents may not

### Session Management
- `/end-session` and `/resume-session` skills for state persistence
- State: `.claude/autoload/_state.md` (max 10 sessions, archive oldest)
- Defects: `.claude/autoload/_defects.md` (max 15, archive oldest)
- NEVER include "Co-Authored-By" in git commits

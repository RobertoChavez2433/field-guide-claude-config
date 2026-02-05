# Session Log

Historical session log. Current state is in `.claude/autoload/_state.md`.

---

### 2026-02-04 (Session 286)
- Tested Springfield PDF extraction - no improvement (85/131, down from 87). Root cause: TableLocator's startY=1600.5 points at boilerplate text containing "unit prices" keywords, not real table header. Also found `_containsAny()` substring matching bug. Created general-purpose header-detection-hardening-plan.md with 3 layers: word-boundary matching, keyword density gating, data-row lookahead. Identified 18 pre-existing test failures.

### 2026-02-04 (Session 285)
- Springfield PDF Extraction Debugging: Systematic root cause analysis via 6 research agents. Found ROOT CAUSE: 11 headerRowYPositions (should be 2) diluting keyword matching → only 4/6 columns detected. Applied 3 fixes: header Y filtering to startY±100px, else-if→if+continue in keyword matching, 5px cell tolerance + nearest-column fallback. 5 test failures remain to fix.

### 2026-02-04 (Session 284)
- Springfield PDF column detection improvements: 8 fixes applied (multi-row header combining, tolerance increases, keyword additions, OCR punctuation normalization, backwards OCR detection). Got to 4/6 keywords (66.7% confidence), 87/131 items.

### 2026-02-04 (Session 283)
- Comprehensive Logging: Implemented DebugLogger with 9 category-specific log files (ocr, pdf, sync, db, auth, nav, ui, errors, app). Always-on file logging to Troubleshooting/Detailed App Wide Logs/. Integrated across app. 5 tests pass. Created 3 documentation files.

### 2026-02-02 (Session 258)
- PDF Parser Diagnostics: Added comprehensive diagnostic logging (pipeline stages, text stats, OCR preprocessing, state transitions). Implemented mega-line splitting fallback. 6 new tests, 357 total parser tests pass.

### 2026-02-02 (Session 257)
- OCR PDF Import Fix: Created OcrPreprocessor class with 6 correction patterns (s→$, trailing s, spaced letters, period-as-comma). Integrated into parser pipeline. 28 new tests, 351 total parser tests pass.

### 2026-02-01 (Session 255)
- Full project analysis: Ran conversation analyzer on 100 sessions (12,388 messages). Created comprehensive findings report. Researched optimizations with explore agents. Created 5-phase implementation plan (security rules, UTF-8 fixes, test splitting, docs).

### 2026-02-01 (Session 254)
- Conversation Analyzer: Implemented full analyzer (6 files) - transcript_parser.py, pattern_extractors.py, analyze.md, analysis-report.md. 5 analysis dimensions.

### 2026-02-01 (Session 253)
- Fixed VS Code Gradle cache errors (8.9/8.14 mismatch). Committed gradle-wrapper.properties formatting.

### 2026-02-01 (Session 252)
- Skills Implementation: Created 5 skills (21 files) - brainstorming, systematic-debugging, TDD, verification, interface-design. Updated 8 agents with skill refs. Fixed flutter-specialist broken refs.

### 2026-02-01 (Session 251)
- Skills research: Explored Claude Code skills best practices, interface-design, Superpowers. Created skills implementation plan for end-session dual-repo commit + interface-design skill.

### 2026-02-01 (Session 250)
- Analyzer Cleanup v3 Phases 3-4: Function declarations, super parameters, Gradle 8.14→8.13, removed dead TODOs.

### 2026-02-01 (Session 249)
- Analyzer Cleanup v3 Phases 1-2: Async safety fixes, null comparison ignore comments.

### 2026-02-01 (Session 248)
- Analyzer Cleanup v3 planning: Analyzed 30 issues (1 prod, 29 test). Created 4-phase fix plan.

### 2026-02-01 (Session 247)
- Context Management Phases 6-11: Consolidated rules, updated agents, cleaned up folders.

### 2026-02-01 (Session 246)
- Context Management Redesign Phases 1-5: Created autoload/, rules/pdf/, rules/sync/, rules/database/, rules/testing/, backlogged-plans/. Moved state files to autoload/, archives to logs/. Converted 5 docs to rules with paths: frontmatter. Created pdf-generation.md and schema-patterns.md.

<!-- Session history entries go here -->

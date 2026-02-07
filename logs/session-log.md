# Session Log

Historical session log. Current state is in `.claude/autoload/_state.md`.

---

### 2026-02-06 (Session 306)
- First real-world PDF test of native text pipeline. Fixed 3 bugs: (1) empty Uint8List crash in img.decodeImage — added isEmpty guards in 4 files, (2) kMaxDataElements=8 too low for word-level native text — raised to 20 with numeric content guard, (3) kMaxDataRowLookahead=5 too narrow — raised to 15. Also raised kMaxContinuationElements 3→10. 614 tests pass.

### 2026-02-06 (Session 305)
- Implemented all 3 phases of PDF Extraction Pipeline Redesign. Native text first, OCR fallback. 1319 tests pass.

### 2026-02-06 (Session 304)
- Brainstorming session continuing PDF extraction pipeline redesign plan. Resolved all 5 open questions from Session 303 draft: (1) hybrid column detection (text-derived first, image-scan fallback), (2) TextWord→OcrElement→v2 pipeline (preserves post-processing), (3) whole-document routing with TODO for per-page, (4) researched legacy ColumnLayoutParser X-position clustering vs v2 pipeline interfaces, (5) coordinate transform bridge (scaleFactor = renderDPI/72). Plan finalized to "Approved" status with 3 implementation phases.

### 2026-02-06 (Session 303)
- Deep diagnostic session on PDF extraction quality. Analyzed logs across 3 extraction runs (all producing garbage: 3-71 items with 13-31% invalid IDs). Launched 6 parallel research agents. Key findings: (1) binarization debate is a red herring — both approaches produce ~72% confidence garbage, (2) no word-level OCR confidence filtering exists, (3) these PDFs are NOT scanned (Session 226 confirmed native text works), (4) the pipeline always OCRs even digital PDFs. Wrote comprehensive redesign plan: native text extraction as primary path (Syncfusion TextWord -> OcrElement converter), OCR as fallback with confidence filtering + PSM tuning. Plan saved to `.claude/plans/2026-02-06-pdf-extraction-pipeline-redesign.md`.

### 2026-02-06 (Session 302)
- Implemented Phase 2+3 from OCR preprocessing fix plan. Numeric gate + post-processing safeguards. 612 tests pass.

### 2026-02-06 (Session 301)
- Implemented Phase 1 (Remove Binarization) from OCR preprocessing fix plan. Removed adaptive thresholding from 3 functions in image_preprocessor.dart. All 202 OCR + 577 PDF tests pass. Manual verification pending.

### 2026-02-06 (Session 300)
- Diagnostic/brainstorming session. Ran app, imported Springfield PDF, analyzed extraction logs. Systematic root cause analysis: discovered image preprocessing adaptive thresholding destroys clean 300 DPI images (1.7MB→136KB binary), causing 3/6 headers lost, 64% unknown rows, garbage item numbers, post-processing amplification. Created phased fix plan: remove binarization, strengthen classifier, add post-processing safeguards.

### 2026-02-05 (Session 296)
- Claude config structure brainstorming. Analyzed global vs project file separation, identified ~880 tokens/session of duplicated content. Deleted _tech-stack.md (merged into CLAUDE.md), trimmed MEMORY.md (53→26 lines), removed duplicate Git Rules section, cleaned _tech-stack refs from 8 agents. Trimmed limits: 10→5 sessions, 15→7 defects. Created global memory at ~/.claude/memory/.

### 2026-02-05 (Session 295)
- PDF Table Structure Analyzer v2 plan review brainstorming. User raised 14 concerns against 7 production files. 3 parallel research agents analyzed circular dependency, cross-page/integration gaps, and medium-risk gaps. Made 14 design decisions: two-pass classification (1A pre-column, 1B post-column), cross-page header lookahead via RowClassifier, item regex alignment with parser, multi-row header assembly in Phase 2, gridline quality scoring, anchor filtering to DATA rows, SECTION_HEADER termination exclusion, column count 3-8, bootstrap+anchor merge, optional parser integration, math validation as hard diagnostic, adaptive row grouping, artifact cleaning before classification. Plan updated v2.0→v2.1.

### 2026-02-05 (Session 294)
- Implemented 9-phase Claude Directory Modernization: cleanup, architecture.md trim, skill frontmatter, commands→skills, agent modernization, CLAUDE.md update, supporting files, agent memory

### 2026-02-05 (Session 293)
- Claude Directory Modernization Brainstorming: Launched 5 research agents (codebase inventory, web best practices, token analysis, conversation history, stale files). Finalized 9-phase plan: cleanup (3+4+2 files, 2 dirs), architecture.md trim (-620 tokens), context:fork for 2 skills, commands→skills migration, agent memory for 4 agents, skill frontmatter for 6, 15-command Quick Reference + Common Mistakes, supporting file updates. All decisions logged in plan.

### 2026-02-05 (Session 292)
- PDF Table Structure Analyzer brainstorming review. Created merged plan v2 combining regression recovery + analyzer improvements. Key decisions: DP dropped, anchor-based correction, 5 row types, cross-multiplication validation, adaptive upgrade.

### 2026-02-05 (Session 291)
- Completed remaining items from regression recovery plan: build metadata, preprocessing fallback logging, deprecated preprocessLightweight(), expanded cleanOcrArtifacts, header keyword gating, batch-level column shift gating.

### 2026-02-05 (Session 289)
- PDF Extraction Regression Recovery: Implemented full 6-phase plan via parallel agents. Phase 0: observability. Phase 1: preprocessing reliability. Phase 2: OCR artifact cleanup. Phase 3: header detection hardening. Phase 4: column shift prevention. Phase 5: regression guards. 690/690 tests pass. 25 files modified (+3294/-240 lines). App rebuilt, both repos pushed.

### 2026-02-05 (Session 288)
- PDF Pipeline Hardening Phases 2-3: Header detection hardening (density gating, word-boundary matching) and cross-page column bootstrapping. Superseded by Session 289 regression recovery.

### 2026-02-05 (Session 287)
- Root cause analysis of PDF extraction pipeline (8 root causes identified). Created 6-phase pipeline hardening plan. Completed Phase 1 (observability logging to 6 files).

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

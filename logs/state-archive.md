# State Archive

Session history archive. See `.claude/autoload/_state.md` for current state (last 5 sessions).

---

## February 2026

### Session 443 (2026-02-22)
**Work**: Redesigned 20/10 weights as compact 80px inline cards. Convergence-aware display (dim past first Δ≤10g). Auto-select converged reading for calc. Overflow "Add Reading" button when all 5 filled without convergence. Harness fixes for MdotHubScreen.
**Results**: `flutter analyze` clean. Validated via dart-mcp (2-reading, 5-reading, 6-reading overflow scenarios).
**Next**: Run flutter test, fix BUG-1/MINOR-2/MINOR-3, commit changes.

### Session 442 (2026-02-22)
**Work**: Fixed 20/10 weights flow — added `_weightsConfirmed` gate so calc only fires after user confirms weights are done. Fields lock after confirmation, "Edit Weights" to unlock. Max readings 15→5. 4 files changed.
**Results**: `flutter analyze` clean, `flutter test` +2341 all passed.
**Next**: Fix BUG-1/MINOR-2/MINOR-3 in forms; hot reload + UX pass on hub with weights gate.

### Session 439 (2026-02-22)
**Work**: Brainstormed 0582B design plan into detailed 7-phase implementation plan. 3 Explore agents gathered codebase context. 4 architectural decisions made via structured questioning. Full widget hierarchy, state design, provider wiring, file plan, acceptance criteria, and testing keys specified.
**Decisions**: Inline everything (delete 4 old screens). Single StatefulWidget hub. Custom FormAccordion (no ExpansionTile). Auto-advance after SEND. Multi-test stays expanded.
**Next**: Build Phase 1 (scaffold + accordion + pill bar), then Phases 2-7.

## February 2026

### Session 438 (2026-02-22)
**Work**: Prototyped 0582B hub screen via html-sync + Playwright. Created 3 design alternatives (Tabbed, Stepper, Accordion). Option C (Accordion Dashboard) selected and refined. Built full 5-step flow mockup + side-by-side comparison vs current. Updated design plan.
**Decisions**: Option C accordion chosen. One section expanded at a time. Summary tiles on collapsed sections. Status pill bar. All buttons "SEND TO FORM". 48dp touch targets. Completion banner with + New Test / Preview PDF.
**Next**: Build accordion dashboard. Fix 3 bugs from Session 435.

### Session 437 (2026-02-21)
**Work**: Brainstormed 0582B hub screen design. Reviewed MCP token cost model. Created card-based hub design plan replacing FormFillScreen with 4 always-visible cards (header, quick test, proctor, weights).
**Decisions**: Hub replaces FormFillScreen. All fields visible. Header collapses after confirm. Grouped field layout. Last-sent compact summary + edit.
**Next**: Build hub screen starting with header card. Fix 3 bugs from Session 435.

### Session 436 (2026-02-21)
**Work**: Set up UI prototyping toolkit. Researched browser-control MCP servers, configured Playwright + HTML Sync, created Beer CSS workflow guide, rules, updated CLAUDE.md + memory.
**Decisions**: Playwright (vision mode) + HTML Sync Server + Beer CSS v4 for rapid browser mockups. Mockups decoupled from Flutter code.
**Next**: Restart CC, smoke test prototyping loop, prototype 0582B form, fix 3 bugs from Session 435.

### Session 435 (2026-02-21)
**Work**: Full 0582B flow harness test (5 screens) via dart-mcp + flutter_driver. Verified proctor entry, quick test, weights entry, form save. Found 3 issues (1 race condition bug, 2 minor).
**Results**: All screens pass end-to-end. Test report at `.claude/test-results/2026-02-21-0582b-flow-harness-test.md`. Defects filed in `.claude/defects/_defects-forms.md`.
**Next**: Fix BUG-1 FormsListScreen race condition, update architecture.md, start project-based architecture.

### Session 433 (2026-02-21)
**Work**: Full project directory audit and cleanup. 5 Explore agents audited root/lib/test/tools/.claude/config dirs. 12+ agents executed cleanup across 6 phases. Recovered ~5GB, deleted 83K+ files, fixed 106 analyze issues→0, reorganized tests, updated all docs.
**Results**: `flutter analyze` 0 issues; `flutter test` +2343 all passed; 8 app commits + 3 .claude commits pushed.
**Next**: Manual MCP harness pass, update rules/architecture.md feature count.

### Session 432 (2026-02-21)
**Work**: Fully implemented widget test harness plan via implementation/review agents. Added in-memory DB testing path, harness runtime, registry/providers/seeding/stubs, 0582B keys, docs, and validation artifact.
**Results**: Review findings resolved; `flutter analyze` (changed files) clean; full `flutter test` passed (`+2343 -0`).
**Next**: Manual MCP interaction sweep on harness screens and PR creation/merge.

### Session 431 (2026-02-21)
**Work**: Brainstormed widget test harness implementation readiness. Audited codebase, found 6 gaps in original plan. Revised design doc with in-memory SQLite approach, two-tier seeding, onException router, 26-screen registry.
**Decisions**: Real stack over mocks, explicit registry, DatabaseService.forTesting(), two-tier seeding, onException stub router.
**Next**: Merge toolbox PR, implement harness Phases 0-1.

### Session 430 (2026-02-21)
**Work**: Planned toolbox feature split with brainstorming skill. Created comprehensive plan for splitting 4 sub-features out of toolbox into independent feature modules.
**Decisions**: Phase-based split (calculator → todos → gallery → forms → toolbox shell). Each gets own data/presentation layers.
**Next**: Implement toolbox split plan.

### Session 429 (2026-02-21)
**Work**: Fully implemented toolbox split plan with implementation + review agents. Moved calculator/todos/gallery/forms into independent feature folders and converted toolbox to launcher shell only. Added targeted EntryFormCard tests and fixed stale forms doc path.
**Results**: Full `flutter test` passed; migration-scope analyze clean; second review pass closed with no findings.
**Next**: Code quality review and cleanup.

### Session 428 (2026-02-21)
**Work**: Resolved all 6 open harness design questions. Confirmed dart-mcp launch_app lacks --dart-define. Pivoted to config file approach. Wrote 6-phase implementation plan.
**Decisions**: Config file selection, lib/test_harness.dart entry point, universal mock superset, stub GoRouter, start 0582B + design universal.
**Next**: Implement harness (Phases 1-6).

### Session 426 (2026-02-21)
**Work**: Fully implemented 0582B redesign plan (all 6 phases) via implementation agents, including calculator/data-model/schema migration, new quick-entry/viewer screens, PDF mapping/polish, and daily entry integration.
**Results**: Agent review loop completed with one high-severity bug fixed; full suite stabilized to `flutter test` => `+2364 -0`.
**Next**: Targeted UX validation + legacy-response migration/backfill decision.

### Session 424 (2026-02-21)
**Work**: Brainstormed 0582B UI redesign. Made 8 design decisions. Wrote comprehensive plan v2 with integrated OnePointCalculator, 3 quick-entry screens, 6 implementation phases.
**Decisions**: Michigan Cone only, auto-compute MDD/OMC, 3 entry screens, per-proctor 20/10 weights, proctor chip bar.
**Next**: Implement Phase 1 (OnePointCalculator + Data Model).

### Session 423 (2026-02-21)
**Work**: Reverse-engineered MDOT Construction Density APK. Decoded exact algorithm for both T-99 (27-row table) and Cone (21-row table) charts.
**Breakthroughs**: Algorithm is piecewise linear interpolation + polynomial, NOT physics. Verified 14/14 exact match.
**Next**: Plan 0582B UI redesign (done in 424).

### Session 422 (2026-02-21)
**Work**: Implemented PDF pipeline refactor plan via multiple agents (P-01..P-13), completed code-review loop, fixed M&P progress regression.
**Results**: PDF scope tests green; saturation-line model ~85% S_opt discovered.
**Next**: Reverse-engineer calculator (done in 423).

### Session 421 (2026-02-21)
**Work**: Brainstormed Gaussian model + harness design. Obtained MDOT calculator app. Collected 14 ground truth data points.
**Next**: Research published equation (superseded by APK decompilation).

### Session 419 (2026-02-21)
**Work**: One-Point Chart Digitization brainstorm. Extracted boundary data, designed hybrid algorithm.
**Next**: Python prototype (done in 420).

### Session 417 (2026-02-21)
**Work**: Full 6-phase entries refactor. Extracted controllers/widgets/section islands and PdfDataBuilder. Applied critical code-review fixes.
**Next**: Wire PdfDataBuilder, adopt overlay in HomeScreen, continue 0582B form work.

### Session 414 (2026-02-22)
**Work**: Fixed route persistence system — allowlist filter, error recovery UI on FormFillScreen.
**Next**: Continue 0582B redesign.

### Session 413 (2026-02-21)
**Work**: Completed Phase 1 teardown for legacy form-import/registry artifacts.
**Next**: Continue 0582B redesign.

### Session 412 (2026-02-21)
**Work**: Started implementation from 0582B redesign plan. Added export preview gating + preview invalidation on edits, updated leave flow.
**Next**: Phase 1 teardown and Phase 2 schema/model migration.

### Session 409 (2026-02-20)
**Work**: Diagnosed Marionette root cause (empty render tree on Windows). Removed Marionette entirely. Migrated to dart-mcp only. Verified widget tree works. Added `native_assets/windows` build fix to docs.
**Decisions**: dart-mcp replaces Marionette permanently. No third-party UI automation packages.
**Next**: Walk through 0582b form via dart-mcp.

### Session 408 (2026-02-20)
**Work**: Completed Marionette Journeys 6-8. Inline editing (activities, contractors work; temp broken). Quantities screen had 2 High bugs (search + sort). Archive/unarchive, PDF export, calendar views passed.
**Decisions**: Log search/sort as High priority. Temp edit needs investigation.
**Next**: Fix P50 (numeric sort), fix P49 (search filter), fix P34 (temp inline save), fix P15 (Gallery/To-Do's missing).

### Session 407 (2026-02-20)
**Work**: Marionette UI testing — completed Journeys 3-5, started Journey 6. Standardized MCP launch procedure in CLAUDE.md. Found 9 new issues (P5-P30).
**Decisions**: Use `dart-mcp launch_app` (not `flutter run` via bash).
**Next**: Continue Journey 6 (inline editing), then Journeys 7 and 8.

### Session 406 (2026-02-20)
**Work**: Strengthened M&P ground truth with full body text. Scorecard 20/20 OK. BLOCKER-12 fully resolved.
**Decisions**: Full body (no truncation) in fixtures.
**Next**: Verify bodies against native PDF text.

### Session 404 (2026-02-20)
**Work**: Researched anchor-based PDF parsing. Brainstormed metadata-driven two-point anchor. Wrote plan.
**Decisions**: Two-point anchor (regex + known bid item numbers).
**Plan**: `.claude/plans/2026-02-20-mp-parser-anchor-rewrite.md`

### Session 403 (2026-02-20)
**Work**: Built M&P testing harness (fixture generator + 14-metric scorecard + GT traces). Diagnosed "4 items" bug.

### Session 402 (2026-02-20)
**Work**: Discovered `Stop-Process -Name 'dart'` kills MCP servers. Decided hybrid testing approach.

### Session 401 (2026-02-20)
**Work**: Attempted M&P E2E test. Fixed Marionette MCP infra.

### Session 400 (2026-02-20)
**Work**: Dual code review, resolved BLOCKER-11, fixed 5 bugs, verified tests green.

### Session 399 (2026-02-20)
**Work**: Implemented full M&P extraction/enrichment flow. Code reviewed and bug-fixed.
**Plan**: `.claude/plans/2026-02-20-mp-extraction-service.md`

### Session 397 (2026-02-19)
**Work**: Started executing Marionette UI test journeys. Completed Journey 1 and partial Journey 2. Found 4 issues (P1-P4). Marionette crashed during PDF import.
**Findings**: `.claude/test-results/2026-02-19-marionette-findings.md`

### Session 396 (2026-02-19)
**Work**: Brainstormed and designed comprehensive Marionette UI test suite. 8 user journeys, ~340 steps.

### Session 394 (2026-02-19)
**Work**: Implemented 100% extraction plan (math backsolve + zero-conf sentinel + scorecard hardening). 5 commits pushed.
**Scorecard**: 72 metrics: 68 OK / 3 LOW / 0 BUG. Quality 0.993. 131/131 GT match. 850/850 tests green.

### Session 391 (2026-02-19)
**Work**: Regenerated fixtures. Ran scorecard (56 OK/2 LOW/1 BUG). Dispatched 3 agents to audit all 62 metrics. Found 12 silently passing, 7 missing coverage, 1 metric bug (B1). Wrote comprehensive hardening plan covering dynamic pattern classification, 15 threshold tightenings, and 4 new metrics.
**Scorecard**: 56 OK / 2 LOW / 1 BUG. Quality 0.990. 131/131 items, $7,882,926.73 exact.
**Next**: Implement `.claude/plans/2026-02-19-harden-scorecard-metrics.md`.

### Session 390 (2026-02-19)
**Work**: Implemented DPI-target upscaling + observability end-to-end using agents. Completed A1-A4 and B1-B5.
**Next**: Regenerate fixtures, validate scorecard baseline.

### Session 389 (2026-02-19)
**Work**: Brainstorming session. Decided on DPI-target approach (targetDpi=600). Audited stage trace for silent failures (7 found). Designed 5 observability metrics.
**Next**: Implement DPI-target upscaling.

### Session 387 (2026-02-19)
**Work**: Implemented low-confidence numeric re-OCR fallback + whitelist leakage fix. Added 8 tests. Extraction green (+855).

### Session 385 (2026-02-19)
**Work**: Implemented OpenCV grid line removal. Removed legacy inset logic. Extraction green (+847).

### Session 382 (2026-02-19)
**Work**: Deep investigation of 7 missing GT items.

### Session 380 (2026-02-19)
**Work**: Rigorous multi-agent investigation proved drift-correction frame mismatch.

### Session 379 (2026-02-19)
**Work**: Root-cause confirmation for pipe artifacts tied to inset frame mismatch.

### Session 376 (2026-02-18)
**Work**: Systematic debugging of bid_amount gap identified whitespace inset/cropping path as root cause candidate; fix attempts were reverted and blocker documented.

### Session 375 (2026-02-18)
**Work**: Implemented full Row Parser V3 plan, regenerated fixtures, removed V2 parser, and ran review/fix loops.
**Results**: Stage trace 54 OK / 1 LOW / 0 BUG, quality 0.977, extraction suite passing.

### Session 374 (2026-02-18)
**Work**: Unblocked fixture regen, validated 15-item recovery, traced remaining gap root causes, planned Row Parser V3 rewrite.

### Session 373 (2026-02-18)
**Work**: Implemented 3-fix 15-item recovery plan and hardening tests.

### Session 372 (2026-02-18)
**Work**: Systematic debugging of upstream misclassification; created 3-fix plan.

### Session 370 (2026-02-18)
**Work**: Revised blocker impact. 9 uncategorized items traced to boilerplate misclassification. Created fix-and-observe plan.

### Session 369 (2026-02-18)
**Work**: Root cause reconciliation. A1 benign, A2 is the problem. Simpler single fix chosen.

### Session 368 (2026-02-18)
**Work**: 3 parallel agents confirmed ROOT CAUSE: scan starts at grid line center, only sees half width.

### Session 366 (2026-02-18)
**Work**: Regenerated fixtures. Scorecard: 41 OK / 8 LOW / 1 BUG.

### Session 365 (2026-02-18)
**Work**: Header Consolidation stage implementation. Suite green (+837).

### Session 360 (2026-02-16)
**Work**: Ran scorecard (22 OK / 4 LOW / 22 BUG). Brainstormed Row Classifier V3 + Column Label fix and wrote detailed implementation plan.
**Decisions**: Rewrite classifier path (V3), improve column semantics, and prioritize upstream fixes before downstream tuning.
**Next**: Implement planned classifier/label remediation and regenerate fixtures.

### Session 359 (2026-02-16)
**Work**: Regenerated fixtures (+4.6% quality, +18 GT matches). Full pipeline diagnostic. Added scorecard test to stage trace. Identified 2 upstream bugs: 4A row classification and 4C column labels.
**Decisions**: Fix upstream stages to 100% before moving downstream.
**Next**: Fix 4A row classification, 4C column labels, row merging.

### Session 357 (2026-02-16)
**Work**: Root cause analysis of 5 problems -> Problem A (red bg in CropUpscaler) is the single root cause. Fixed with `numChannels: resized.numChannels`. Regenerated fixtures. Pipeline: 137 parsed items, 87/131 GT matches (66%), quality 0.748.
**Decisions**: Problem A fixed. B (DPI 300) is intentional. C (source_dpi) is metadata-only. D+E resolved by fixing A.
**Next**: Row merging, item# OCR noise cleanup, row classification tuning.

### Session 355 (2026-02-16)
**Work**: Systematic debugging of stage trace. Root cause: PSM 7 on full-row strips can't handle grid lines.
**Decisions**: Cell-level OCR is the fix.
**Next**: Implement cell-level OCR (was already done)

---

## February 2026

### Session 354 (2026-02-16)
**Work**: Regenerated fixtures with ROW-STRIP code. 27 items, 26/131 GT matches (20%).
**Decisions**: Row classifier is #1 blocker.

### Session 353 (2026-02-16)
**Work**: Implemented diagnostic image capture system. 14 JSON fixtures, onDiagnosticImage callback.
**Decisions**: Raw images only. Images gitignored.

### Session 352 (2026-02-15)
**Work**: Traced pipeline failure cascade. 0 header rows → 0 regions → everything empty.
**Decisions**: Synthetic regions is Priority 1.

### Session 350 (2026-02-15)
**Work**: Deep OCR brainstorming. Traced actual data through pipeline. Researched community practices, cross-platform OCR, cloud OCR pricing, opencv_dart, textify. Established 3-step escalation path.
**Decisions**: Row-strip OCR first (zero deps). opencv_dart if needed. Cloud Vision as last resort.

### Session 349 (2026-02-15)
**Work**: Code review (3 fixes). Fixture regen revealed 0 regions. Brainstormed grid-aware region detection (Options B/C).

### Session 348 (2026-02-15)
**Work**: Fixed column semantic mapping. Margin detection, anchor-relative inference, content validation. 324 tests pass.

### Session 347 (2026-02-15)
**Work**: Verified cell crop upscaling complete. Upscaling insufficient for narrow columns.

### Session 346 (2026-02-15)
**Work**: Fixed getLuminance bug. Grid detection 0→6 pages. Luminance diagnostic test.

### Session 345 (2026-02-15)
**Work**: Grid line detection implementation. Phase 1+2 code reviewed and fixed.

### Session 344 (2026-02-15)
**Work**: Brainstormed Phase 3 plan (ColumnDetectorV2 grid integration). 7 sections, ~10 design decisions. Explored column detector (1,158 lines), reviewed all test/golden patterns. Identified page 1 grid misclassification root cause.
**Decisions**: Option D (grid boundaries + keywords). Per-page independent. Diagnostic mode (both paths run). Anchor validation-only. Density filtering for page 1. Replace stub entirely.
**Next**: 1) Implement Phase 3 (A: grid fix, B: Layer 0, C: goldens) 2) Implement Phase 4 (pipeline wiring) 3) Benchmark accuracy

### Session 343 (2026-02-15)
**Work**: Code reviewed Phase 1 + Phase 2 implementations (2 parallel agents). Fixed 6 issues: mock type safety (dynamic→typed), DRY _median→MathUtils.median, pre-sort horizontal lines, remove redundant cast, add stageConfidence doc. 717 tests pass.
**Decisions**: All mock overrides must use typed params (not dynamic). Shared MathUtils.median() is canonical median impl.
**Next**: 1) Implement Phase 3 (ColumnDetectorV2 grid integration) 2) Implement Phase 4 (pipeline wiring + fixtures) 3) Benchmark accuracy

### Session 342 (2026-02-14)
**Work**: Brainstormed Phase 2 plan — cell-level cropping for TextRecognizerV2. Reviewed actual PDF, audited all 52 test files. Escalated from row to cell cropping for 100% accuracy. 10 design decisions, 19 new tests, 3 source files.
**Decisions**: Cell-level crop (not row). PSM 7/6 adaptive. Grid-only OCR (drop boilerplate). No vertical line erasing. 2px padding. Sequential engine. PSM 4 fallback.
**Next**: 1) Implement Phase 1 (GridLineDetector) 2) Implement Phase 2 (cell cropping) 3) Phases 3-4 (column integration + wiring)

---

## February 2026

### Session 341 (2026-02-14)
**Work**: Brainstormed Phase 1 implementation plan for GridLineDetector. Reviewed all stage patterns (models, tests, mocks, fixtures, diagnostics). Made 7 design decisions. Exported full plan with 17 tests, 9 files (3 new, 6 modified).
**Decisions**: Plain name (no V2). compute() isolate. GridLines wrapper. toMap/fromMap included. 17 tests. All infrastructure in Phase 1. Fixture diagnostic only.
**Next**: 1) Implement Phase 1 per plan 2) Continue Phases 2-4 3) Regenerate fixtures + validate accuracy

### Session 340 (2026-02-14)
**Work**: Fresh baseline (0/131 match, $0). Root-caused OCR garbage to PSM=6 on table pages. Researched PSM modes. Designed grid line detection + row-level OCR plan (4 phases).
**Decisions**: OCR-only (no native text — CMap corruption). Tier 2: grid line detection → row cropping → PSM 7. Grid vertical lines feed column detection at 0.95 confidence. PSM 4 fallback for non-grid pages.
**Next**: 1) Implement grid line detection plan (phases 1-4) 2) Regenerate fixtures 3) Validate accuracy improvement

## February 2026

### Session 339 (2026-02-14)
**Work**: Status audit — verified OCR migration Phases 2-4 already implemented, PRD R1-R6 mostly complete. Moved 3 completed plans. Updated state files.
**Decisions**: Focus on pipeline accuracy improvement as primary goal.

### Session 337 (2026-02-14)
**Work**: Implemented full V2 extraction pipeline refactoring (28 findings, 7 phases). Created 6 new shared files, modified 30+ files, ~2,500 lines saved. Fixed 3 correctness bugs, eliminated ~500 lines of duplicated prod code, moved ~1,800 lines of dead tests.
**Decisions**: `QualityThresholds` as single source of truth for score thresholds. `TextQualityAnalyzer` mixin for shared corruption detection. `Duration?` replaces mutable `Stopwatch` on `PipelineContext`. Shared mock stages for test reuse.

### Session 338 (2026-02-14)
**Work**: Code review cleanup — 3 parallel review agents found 21 issues. Executed 13-step plan: deleted deprecated dirs, fixed dead code, sentinel pattern for copyWith, epsilon doubles, import normalization, stage name migration, ResultConverter bug fix.
**Decisions**: Skip models barrel cleanup (30+ file blast radius). Delete deprecated dirs entirely (git preserves history). Use StageNames constants everywhere (no substring matching).

### Session 336 (2026-02-14)
**Work**: Full .claude/ reference integrity audit. Ran 4 code-review agents (2 audit + 2 verification). Fixed 42 broken refs across 28 files. Committed in 5 groups and pushed.

### Session 335 (2026-02-13)
**Work**: Ran 3 parallel code-review agents on `.claude/` directory. Fixed ~90+ broken refs, archived 10 stale files, renamed 3 constraint files, deleted _defects.md redirect, fixed all agent/state/constraint file paths.

### Session 333 (2026-02-13)
**Work**: Tested `/resume-session` — removed 4-path intent questions (zero-question flow). Audited `.claude/` directory: found 16 broken refs, 9 orphans, 3 outdated items. Designed 3 native Claude Code hooks (post-edit analyzer, doc staleness, sub-agent pre-flight). Wrote Phase 4 implementation plan.
**Decisions**: Zero-question resume (user's first message = intent). Native hooks over manual scripts. Blocking PostToolUse analyzer. Hook-enforced doc updates (no dedicated docs agent). No PreToolUse gates (V1 patterns moot).

---

### Session 332 (2026-02-13)
**Work**: Fixed 16 issues in `.claude/` directory config across 5 phases. Rewrote session skills (no git), fixed broken references, wired agent feature_docs, created 13 per-feature defect files, migrated existing defects.
**Decisions**: Per-feature defects in `.claude/defects/`, overviews-only for multi-feature agents (token efficiency), original _defects.md kept as redirect.

---

### Session 330 (2026-02-12)
**Work**: Enhanced CMap corruption detection in Stage 0 DocumentAnalyzer. Added mixed-case pattern detection + currency symbol validation. All 6 Springfield pages now route to OCR.

---

## February 2026

### Session 405 (2026-02-20)
Implemented M&P parser anchor rewrite (BLOCKER-12). 25/25 tests green, 0 analysis issues.

### Session 329 (2026-02-12)
Git history restructuring — 10 clean commits pushed to main.

### Session 328 (2026-02-12)
R7 brainstorming. Ground truth verification (131 items, $7,882,926.73). 3-layer golden test architecture.

### Session 327 (2026-02-11)
R5+R6 implementation. 9 golden fixtures. Pipeline quality baseline.

### Session 324 (2026-02-11)
Phase 5 complete — Stages 4A-4E fully implemented, PostProcessorV2 rewritten standalone, pipeline orchestrator expanded 0-6, all legacy imports eliminated. 619 extraction tests pass.

### Session 321 (2026-02-08)
Implemented full 5-PR plan for robust two-line header detection + per-page column recovery. 1431 PDF tests pass, 704 table extraction, 0 regressions.

### Session 320 (2026-02-08)
Diagnosed jumbled Springfield data via pipeline dumps. Found 2 bugs: multi-line header + hardcoded empty header elements.

### Session 319 (2026-02-08)
Runtime Pipeline Dumper Integration — wired PipelineFileSink into PdfImportService. 689 table extraction tests pass. 22 dumper tests.

### Session 313 (2026-02-07)
Implemented all 4 parts of OCR Empty Page + Encoding Corruption fix. RGBA→grayscale, fail-parse, force re-parse, thread encoding flag through 28 call sites. Commit: d808e01.

### Session 311 (2026-02-07)
Encoding-aware currency normalization (z→7, e→3, fail on unmappable), debug image saving, PSM 11 fallback for empty OCR pages. 1386 PDF tests pass. 13 new encoding tests.

### Session 310 (2026-02-07)
Fixed OCR "Empty page" failures — threaded DPI to Tesseract via `user_defined_dpi`, eliminated double recognition in `recognizeWithConfidence`. 1373 PDF tests pass. Commit: `c713c77`.

### Session 307 (2026-02-06)
Font encoding investigation. Added diagnostic logging, ran Springfield PDF, discovered multi-page corruption. Pages 1-4 mild, page 6 catastrophic. OCR fallback needed.

### Session 306 (2026-02-06)
First real-world PDF test of native text pipeline. Fixed 3 bugs: empty Uint8List crash, element count thresholds, data row lookahead.

### Session 305 (2026-02-06)
Implemented all 3 phases of PDF Extraction Pipeline Redesign. Native text first, OCR fallback.

### Session 304 (2026-02-06)
Brainstorming session continuing pipeline redesign plan.

### Session 301 (2026-02-06)
Phase 1: Removed binarization from image preprocessing. 202 OCR + 577 PDF tests pass. Commit: `836b856`.

### Session 299 (2026-02-06)
Table Structure Analyzer v2.1 Phases 5+6 (Parser Integration + Regression Guard). 566/567 tests pass. Commit: `0a4cbb0`.

### Session 298 (2026-02-06)
Implemented Phase 3 (Anchor-Based Column Correction + Gridline Quality Scoring) and Phase 4 (Post-Processing Math Validation) from PDF Table Structure Analyzer v2.1 plan. Commit: `eafae91`.

### Session 297 (2026-02-05)
Implemented Phase 1 (Row Classifier) and Phase 2 (Table Region Detector) from PDF Table Structure Analyzer v2.1 plan. RowClassification model (6 row types), RowClassifier with Phase 1A/1B. TableRegionDetector with two-pass linear scan, cross-page header confirmation, multi-table detection. 523/524 tests pass.

### Session 291 (2026-02-05)
Completed missing items from pdf-extraction-regression-recovery-plan.md: build metadata, preprocessing fallback, re-OCR source logging, deprecated preprocessLightweight(), expanded cleanOcrArtifacts, header primary keyword gating, detailed header-element logging, batch-level gating for column shifts.

### Session 289 (2026-02-05)
Implemented full 6-phase PDF extraction regression recovery plan via parallel agents. 25 files modified (13 production + 12 test), +3294/-240 lines. Commits: app `1b3991f`, config `771fb49`. Tests: 690/690 pass (482 table_extraction + 202 OCR + 6 debug_logger).

### Session 288 (2026-02-05)
Pipeline hardening Phases 2-3: Density gating, word-boundary matching, column bootstrapping. Commits pending (superseded by Session 289).

### Session 287 (2026-02-05)
Root cause analysis of PDF extraction pipeline (8 root causes). Created 6-phase hardening plan. Completed Phase 1 (observability logging). Commits pending.

### Session 286 (2026-02-04)
Tested Springfield PDF — no improvement (85/131). Root cause: TableLocator startY at boilerplate. Created header-detection-hardening-plan.md. Commits pending.

### Session 285 (2026-02-04)
Systematic debugging of Springfield extraction (87/131). Found root cause: 11 headerRowYPositions. Applied 3 fixes. Commits pending (7 modified files).

### Session 284 (2026-02-04)
Springfield PDF column detection improvements: 8 fixes, backwards OCR detection, comprehensive logging. Got to 4/6 keywords, 87/131 items. Commits pending (23 modified files).

### Session 280 (2026-02-04)
Flusseract OCR Migration Phases 4-6: OCR quality safeguards (21 config tests), legacy cleanup (stale ML Kit refs removed, ParserType renamed), performance hardening (pooled disposal fix). 200+ OCR tests pass. `ed267db`

### Session 281 (2026-02-04)
Windows OCR Accuracy Fix Phases 1-3: PNG format for all platforms, adaptive DPI, lightweight preprocessing. Code review 7.5/10.

### Session 331 (2026-02-12)
OCR-only pipeline migration Phase 1. Designed & approved plan via brainstorming. Deprecated 3 native extraction files. Created `DocumentQualityProfiler` + `ElementValidator`. Refactored `ExtractionPipeline` (removed Stage 2A, fixed re-extraction loop). Updated all test mocks/imports. Zero analyze errors.

### Session 282 (2026-02-04)
Springfield PDF extraction debugging: Windows preprocessing skipped binarization. Full preprocessing on all platforms, no-item-number regex, TableLocator improvements (lowered kMinHeaderKeywords to 2, multi-row header detection).

### Session 283 (2026-02-04)
Comprehensive app-wide debug logging: DebugLogger with 9 category-specific log files. Integrated across main.dart, ocr, sync, database, table_extractor. 5 tests pass.

### Session 277 (2026-02-04)
Implemented Tesseract OCR Migration Plan Phases 1-3 using pdf-agents. Phase 1: OCR Abstraction Layer. Phase 2: Tesseract Dependencies. Phase 3: Tesseract Adapter. 95 OCR tests pass. `17a0773`

### Session 276 (2026-02-04)
Implemented PDF Post-Processing Accuracy Plan (5 phases) using pdf-agents with TDD. PostProcessEngine scaffolding, normalization + type enforcement, consistency & inference, split/multi-value repairs, dedupe + sequencing. 182 new tests. `6a0a910`

### Session 275 (2026-02-03)
Implemented PRs 4-6 from Table-Aware PDF Extraction V3 Completion. PR4: Progress UI Wiring. PR5: Integration Tests + Fixtures. PR6: Cleanup + Deprecation. 787 PDF tests pass. `a22c87d`

### Session 274 (2026-02-03)
Implemented PRs 1-3 from Table-Aware PDF Extraction V3 Completion. PR1: Column naming + dimension fix. PR2: Cell-level re-OCR. PR3: Row boundary detection. 218 tests pass. `2bc588e`, `cbb0f8c`

### Session 273 (2026-02-03)
Implemented PRs 9-10 from Table-Aware PDF Extraction V3. PR9: UI integration (PdfImportProgressDialog). PR10: Cleanup & polish (deprecated OcrRowReconstructor, diagnostic logging). `db11078`

### Session 272 (2026-02-03)
Implemented PRs 7-8 from Table-Aware PDF Extraction V3. PR7: TableRowParser (cell-to-typed-field parsing, confidence scoring). PR8: TableExtractor orchestrator (4-stage pipeline). 179 tests pass. `7eeb531`

### Session 271 (2026-02-02)
Implemented PRs 5-6 from Table-Aware PDF Extraction V3. PR5: ColumnDetector unified orchestrator. PR6: CellExtractor with recognizeRegion(). 35 new tests. `e7479a4`

### Session 252 (2026-02-01)
Implemented 5 skills (21 files): brainstorming, systematic-debugging, TDD, verification-before-completion, interface-design. Updated 8 agents with skill references.

### Session 247 (2026-02-01)
Context Management Phases 6-11 - Consolidated rules, updated CLAUDE.md files, rewrote commands, updated 8 agents with workflow markers, deleted old folders.

### Session 246 (2026-02-01)
Context Management Phases 1-5 - Created autoload/, rules/pdf/, rules/sync/, rules/database/, rules/testing/, backlogged-plans/. Moved _state.md, _defects.md, _tech-stack.md to autoload/.

### Session 245 (2026-02-01)
Context Management System Redesign - comprehensive planning session. Created 14-phase plan. No commits (planning only).

### Session 243 (2026-02-01)
Context optimization v2 complete - verified @ references, extracted 5 defect patterns from history. No commits (documentation only).

### Session 241 (2026-01-31)
Phase 7 - Patrol config/docs alignment (README update, patrol.yaml cleanup). `6189ae8`

### Session 240 (2026-01-31)
Session state management and archive rotation.

### Session 239 (2026-01-31)
Phase 6 - Test cleanup: unused imports, dead variables, async safety in tests.

### Session 238 (2026-01-31)
Phase 3 - Deprecated Flutter APIs: WillPopScope to PopScope, withOpacity to withValues. `3ba5f38`

### Session 237 (2026-01-30)
Phase 2 (29 unused imports) + Phase 9 (root logs cleanup) + code review. `e03e8a7`

### Session 236 (2026-01-30)
Phase 1 CRITICAL - Fixed test_bundle.dart for Patrol v4 (patrol_cli 3.11.0 to 4.0.2). `4efc7ff`

### Session 235 (2026-01-30)
Created analyzer cleanup plan for 157 issues. No commits (planning).

### Session 234 (2026-01-29)
Stages 8-10: Supabase ^2.12.0, Calendar ^3.2.0, Patrol ^4.1.0 migration. `c6bf403`, `cf0d6a0`, `e7c922a`

### Session 233 (2026-01-29)
Stages 6-7: PDF Stack (Syncfusion v32), Navigation (go_router v17). `47b5a00`

### Session 232 (2026-01-28)
Stage 5: Files, Media, Pickers - file_picker ^10.3.10, image_picker ^1.2.1. `0fb437d`

### Session 231 (2026-01-28)
Stage 4: Location/Permissions - geolocator ^14, geocoding ^4, permission_handler ^12. `3fe1058`

### Session 230 (2026-01-28)
Stage 3: Networking - connectivity_plus ^7, http ^1.6. `e392d3e`

### Session 229 (2026-01-27)
Stage 2: State/Storage - provider, shared_preferences, flutter_secure_storage v10. `5a8f1bd`

### Session 228 (2026-01-27)
Stages 0-1: Toolchain baseline + low-risk core updates (8 deps). `bab9ae1`, `ef2d00b`

### Session 227 (2026-01-26)
Dependency modernization research + created 10-stage upgrade plan. No commits.

### Session 226 (2026-01-26)
Phase 4: Quality gates + scanned PDF detection in parser. `0c94e42`

### Session 224 (2026-01-25)
Phase 3: Description cap (150 chars) + BoilerplateDetector class. `d1c9270`

### Session 222 (2026-01-24)
Phase 1a-1b: Adaptive clustering + multi-page header detection in ColumnLayoutParser. `e30debe`

### Session 221 (2026-01-24)
Phase 0: DiagnosticsMetadata, DiagnosticsExporter, test fixtures. `ab2c8e0`

### Session 220 (2026-01-23)
Phase 6: ClumpedTextParser integration into fallback chain + code review fixes. `57807d6`, `5658a13`

### Session 219 (2026-01-23)
Phase 5: ClumpedTextParser end-to-end parser (214 tests). `701e26c`

### Session 218 (2026-01-22)
Phase 4: ParsedRowData model + RowStateMachine (58 tests). `8b991b9`

### Session 217 (2026-01-22)
Phase 3: TokenClassifier with context-aware classification (84 tests). `8ca8047`

### Session 216 (2026-01-21)
Phase 2: TextNormalizer for clumped text repair (39 tests). `590c8dd`

### Session 215 (2026-01-21)
Phase 1: ParserDiagnostics + extractRawText shared helper. `9ad11ca`

### Session 214 (2026-01-20)
Created Clumped Text PDF Parser plan + fixed project_setup_screen build error. `bf08638`

### Session 213 (2026-01-20)
Phase 7-8: Addendum handling + MeasurementSpecPreviewScreen. `804aed4`

### Session 212 (2026-01-19)
Phase 6: Preview UI - confidence indicators, warning banners, needsReview highlight. `d420832`

### Session 210 (2026-01-18)
Phase 4: DuplicateStrategy enum + ImportBatchResult + batch import. `86eecb5`

### Session 208 (2026-01-17)
Phase 1: ParsedBidItem model with confidence/warnings + PdfImportResult update. `ea246d0`

### Session 207 (2026-01-17)
3 form preview fixes: hash update, test number position, composite column. `d3b9fe6`

### Session 206 (2026-01-16)
Phase 4: Live preview fix - onFieldChanged updates responseData. `366e8fe`

### Session 205 (2026-01-16)
Phase 3: 0582B form restructure with tableRowConfig + DensityGroupedEntrySection. `5148e96`

### Session 204 (2026-01-15)
Phase 2: Added Start New Form button to report screen. `1a7fa33`

### Session 203 (2026-01-15)
Phase 1: Changed filter toggle default to OFF in form_fill_screen. `6303ffb`

### Session 202 (2026-01-14)
Tested Windows app, identified 4 autofill issues, created plan. No commits.

### Session 201 (2026-01-14)
Form Completion Debug v2: isInitializing flag + verbose debug logging. `fb158a3`

### Session 200 (2026-01-13)
Investigated blank screen + autofill issues, identified race condition. No commits.

### Session 199 (2026-01-13)
Form Completion Debug: isRestoringProject flag + filter toggle + autoFillSource. `4f4256e`

### Session 198 (2026-01-12)
Fixed RenderFlex overflow in entry card + defensive try-catch for autofill. `8d32417`

### Session 197 (2026-01-12)
Code review fixes: mounted check, TestingKeys, magic numbers, calculator refactor. `a909144`

### Session 196 (2026-01-11)
Planned code review fixes from Session 195. No commits.

### Session 195 (2026-01-11)
PR 3: Start New Form button + Attachments section in entry_wizard. `0e03b95`

### Session 194 (2026-01-10)
PR 2: Calculate New Quantity button implementation.

### Session 193 (2026-01-10)
PR 1: Removed Test Results section from entry wizard.

---

## Completed Plans Summary

### Dependency Modernization Plan v2 - COMPLETE (Sessions 227-234)
10-stage upgrade: Toolchain, Core, State/Storage, Networking, Location, Files, PDF, Navigation, Supabase, Test Tooling.

### PDF Parsing Fixes v2 - COMPLETE (Sessions 221-226)
Phases 0-4: Observability, clustering, header detection, structural keywords, description cap, quality gates.

### Clumped Text PDF Parser - COMPLETE (Sessions 214-220)
8-phase state machine parser for clumped PDF text extraction.

### Smart Pay Item PDF Import Parser v2 - COMPLETE (Sessions 208-213)
8-phase parser with confidence scoring, batch import, preview UI, measurement specs.

### Form Completion Debug v3 - COMPLETE (Sessions 203-206)
4-phase fix: toggle default, report screen button, 0582B restructure, live preview.

### Entry Wizard Enhancements - COMPLETE (Sessions 193-197)
3 PRs + code review: Test Results removal, Quantity calculation, Start New Form button.


### Session 427 (2026-02-21)
**Work**: Brainstormed universal dart-mcp widget test harness. Made 5 design decisions. Wrote design document with architecture concept, open questions, and success criteria.
**Decisions**: Compile-time flag selection, test-only entry point, production code untouched, in-memory mock strategy.
**Next**: Continue brainstorming open questions, then implement harness.

# Session State

**Last Updated**: 2026-02-22 | **Session**: 414

## Current Phase
- **Phase**: 0582B Form Redesign — Full teardown + rebuild
- **Status**: Phase 1 teardown complete. Route persistence bug fixed. Phase 2+ implementation pending.

## HOT CONTEXT - Resume Here

### What Was Done This Session (414)

1. **Route persistence/restoration fix**: Implemented three-layer defense against stale route restoration.
   - **Layer 1 (allowlist)**: `_isRestorableRoute()` in `main.dart` — only 12 static routes are persisted; dynamic-ID routes are never saved.
   - **Layer 2 (error recovery)**: `form_fill_screen.dart` — "Form response not found" now shows icon + message + "Go Back" button using `safeGoBack`.
   - **Layer 3 (Driver skip)**: `main.dart` — `FLUTTER_DRIVER` env skips route restoration so tests always start at `/`.
2. **`clearLastRoute()` API**: Added to `preferences_service.dart` for programmatic route reset.
3. All changes pass `flutter analyze` with zero issues.

### What Was NOT Done
- Manual testing of the route restoration fix (needs app launch + kill/restart cycle)
- Phase 2+ of 0582B redesign (data layer completion, shared widgets, UX polish)

## Blockers

### BLOCKER-6: Global Test Suite Has Unrelated Existing Failures
**Impact**: Full-repo `flutter test` remains non-green outside extraction scope.
**Status**: Pre-existing/unrelated.

### BLOCKER-7: Fixture Generator Requires SPRINGFIELD_PDF Runtime Define
**Impact**: Fixture regeneration/strict diagnostics require `--dart-define=SPRINGFIELD_MP_PDF=...`.
**Status**: Open.

## Recent Sessions

### Session 414 (2026-02-22)
**Work**: Fixed route persistence system — allowlist filter (only static routes saved), error recovery UI on FormFillScreen, Flutter Driver skip. Added `clearLastRoute()` to PreferencesService.
**Decisions**: Allowlist > denylist for route saving (new routes default to "not saved"). Error UI follows existing `report_screen.dart` pattern using `safeGoBack`.
**Next**: Manual testing of route fix. Continue Phases 2-6 of 0582B redesign.

### Session 413 (2026-02-21)
**Work**: Completed remaining Phase 1 teardown for legacy form-import/registry artifacts. Removed legacy services/tests/assets, updated DB migration cleanup, and aligned template references to `mdot_0582b_form.pdf`.
**Decisions**: Keep teardown deterministic by deleting residual legacy paths and references rather than leaving compatibility shims.
**Next**: Continue Phases 2-6 of 0582B redesign (data-model completion, widget architecture, preview/export polish, edge-case flows).

### Session 412 (2026-02-21)
**Work**: Started implementation from 0582B redesign plan. Added export preview gating + preview invalidation on edits, updated leave flow (`Discard` + `Leave & Save`), stabilized DB tests, and ran review/test loops.
**Decisions**: Keep targeted, non-destructive progress while preserving existing architecture; defer major teardown/model migration to next slice.
**Next**: Implement Phase 1 teardown and Phase 2 schema/model migration with tests.

### Session 411 (2026-02-20)
**Work**: Brainstorming session — full review of current form system, designed 0582B form redesign. Editable form widget + SmartInputBar + on-demand PDF preview + code-first modularity.
**Decisions**: Full teardown both forms. Generic DB (header_data + response_data). Row-at-a-time entry. Live calcs with visual cue. 6-phase implementation plan.
**Next**: Start Phase 1 (teardown of current form system). Plan: `.claude/plans/2026-02-20-0582b-form-redesign.md`

### Session 410 (2026-02-20)
**Work**: Added Flutter Driver infrastructure (driver_main.dart, flutter_driver dep). Discovered Driver can't interact with dialog overlays on Windows. Added FLUTTER_DRIVER env guard. Rewrote CLAUDE.md dart-mcp docs with limitations table.
**Decisions**: Guard all dialogs with `FLUTTER_DRIVER` env check. Don't retry timed-out driver commands — diagnose and work around.
**Next**: Audit all dialogs for FLUTTER_DRIVER guards. Walk through 0582b form.

## Active Plans

### M&P Parser Rewrite — COMPLETE (BLOCKER-12 RESOLVED)
- **Plan**: `.claude/plans/2026-02-20-mp-parser-anchor-rewrite.md`
- **Status**: Complete. 131/131 parsed, matched, body-validated. 20/20 scorecard metrics OK.

### M&P Extraction Service — COMPLETE, VALIDATED
- **Plan file**: `.claude/plans/2026-02-20-mp-extraction-service.md`

### 0582B Form Redesign — IN PROGRESS
- **Plan**: `.claude/plans/2026-02-20-0582b-form-redesign.md`
- **Status**: Implementation in progress. Guardrails and Phase 1 teardown complete; Phase 2+ buildout pending.
- **Phases**: 6 total (teardown → data layer → shared widgets → form screen → PDF export → polish)

### UI Journeys — COMPLETE (14 issues found)
- **14 issues total**: 3 High (P15, P49, P50), 5 Medium, 4 Low, 2 Infra
- Findings: `.claude/test-results/2026-02-19-marionette-findings.md`

### 100% Extraction Pipeline Fixes — IMPLEMENTED, VALIDATED
- **Plan file**: `.claude/plans/2026-02-19-100pct-extraction-pipeline-fixes.md`

## Reference
- **M&P Parser Rewrite Plan**: `.claude/plans/2026-02-20-mp-parser-anchor-rewrite.md`
- **M&P Extraction Service Plan**: `.claude/plans/2026-02-20-mp-extraction-service.md`
- **M&P PDF**: `C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [319-331) M&P.pdf`
- **Springfield Bid Items PDF**: `C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf`
- **Test findings**: `.claude/test-results/2026-02-19-marionette-findings.md`
- **Archive**: `.claude/logs/state-archive.md` (historical sessions)
- **Defects**: `.claude/defects/_defects-pdf.md`, `.claude/defects/_defects-quantities.md`
- **Ground Truth**: `test/features/pdf/extraction/fixtures/springfield_ground_truth_items.json` (131 items)

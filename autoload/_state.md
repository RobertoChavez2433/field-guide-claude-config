# Session State

**Last Updated**: 2026-02-20 | **Session**: 406

## Current Phase
- **Phase**: M&P Ground Truth + Body Validation — COMPLETE
- **Status**: Full body GT generated, scorecard expanded to 20 metrics, 131/131 body exact matches, 131/131 junk-free. All 4 scorecard tests green.

## HOT CONTEXT - Resume Here

### What Was Done This Session (406)

#### 1. Strengthened M&P Ground Truth + Stage Capture
- **Fixture generator** (`generate_mp_fixtures_test.dart`): Replaced `body_excerpt` (120-char truncation) with `body` (full text). Added `raw_body_tail` (last 150 chars of uncleaned segment). Added `mp_ground_truth_bodies.json` fixture (131 items with full expected body).
- **Scorecard** (`mp_stage_trace_diagnostic_test.dart`): Added 2 new Body metrics (`exact_matches`, `junk_free`). Added "Body Accuracy Report" section. Added "Body Text Accuracy" test group with 2 tests (exact match + junk pattern detection). Updated GT traces to use `body` instead of `body_excerpt`.
- **Fixtures regenerated**: All 7 fixtures generated (including new `mp_ground_truth_bodies.json` at 49KB).

#### 2. Scorecard Results — 20/20 OK
- Body exact_matches: 131/131 (100%)
- Body junk_free: 131/131 (100%)
- All 20 metrics OK, 0 BUG/HIGH, 0 LOW/OVER/SLOW
- Header stripping confirmed working (items 115, 128, 131 clean)

## Blockers

### BLOCKER-12: M&P Parser Regex Finds Only 4 of 131 Items
**Impact**: M&P extraction was non-functional.
**Status**: RESOLVED (Session 405-406). Anchor algorithm implemented, fixtures regenerated, scorecard 20/20 green.

### BLOCKER-6: Global Test Suite Has Unrelated Existing Failures
**Impact**: Full-repo `flutter test` remains non-green outside extraction scope.
**Status**: Pre-existing/unrelated.

### BLOCKER-7: Fixture Generator Requires SPRINGFIELD_PDF Runtime Define
**Impact**: Fixture regeneration/strict diagnostics require `--dart-define=SPRINGFIELD_MP_PDF=...`.
**Status**: Open.

### BLOCKER-8: Marionette MCP Disconnects During Heavy Rendering
**Impact**: Cannot reliably automate full UI journeys through Marionette.
**Status**: Mitigated with hybrid testing approach.

## Recent Sessions

### Session 406 (2026-02-20)
**Work**: Strengthened M&P ground truth with full body text. Added `mp_ground_truth_bodies.json` fixture, `raw_body_tail` stage capture, 2 body accuracy metrics. Scorecard expanded to 20 metrics, all OK. BLOCKER-12 fully resolved.
**Decisions**: Full body (no truncation) in fixtures. Raw tail captured by re-running anchor detection in generator. Junk patterns: page headers + section markers.
**Next**: Verify bodies against native PDF text (plan step 3). Consider non-Springfield PDF validation.

### Session 405 (2026-02-20)
**Work**: Implemented M&P parser anchor rewrite (BLOCKER-12). Rewrote `_parseEntries()` with metadata-driven two-point anchor. Updated 5 test files. Code reviewed (1 critical fix applied). 25/25 tests green, 0 analysis issues.
**Decisions**: Safety-net merge threshold 30 chars. Case-sensitive regex. Fixture generator normalizes item numbers inline.
**Next**: Regenerate M&P fixtures, run scorecard to verify 131/131.

### Session 404 (2026-02-20)
**Work**: Researched community best practices for anchor-based PDF parsing. Brainstormed metadata-driven two-point anchor. Wrote implementation plan.
**Decisions**: Two-point anchor (regex + known bid item numbers). Safety net for short segments. Record return type.
**Plan**: `.claude/plans/2026-02-20-mp-parser-anchor-rewrite.md`

### Session 403 (2026-02-20)
**Work**: Built M&P testing harness (fixture generator + 14-metric scorecard + GT traces). Diagnosed "4 items" bug.
**Decisions**: Parser rewrite needed — anchor-based, not regex-line-start.

### Session 402 (2026-02-20)
**Work**: Discovered `Stop-Process -Name 'dart'` kills MCP servers. Decided hybrid testing approach.

### Session 401 (2026-02-20)
**Work**: Attempted M&P E2E test. Fixed Marionette MCP infra.

## Active Plans

### M&P Parser Rewrite — COMPLETE (BLOCKER-12 RESOLVED)
- **Plan**: `.claude/plans/2026-02-20-mp-parser-anchor-rewrite.md`
- **Algorithm**: Metadata-driven two-point anchor (regex + bid item number whitelist)
- **Status**: Complete. 131/131 parsed, matched, body-validated. 20/20 scorecard metrics OK.

### M&P Extraction Service — COMPLETE, VALIDATED
- **Plan file**: `.claude/plans/2026-02-20-mp-extraction-service.md`
- Core implementation complete, parser rewritten, GT bodies validated, scorecard green

### Testing Strategy — DECIDED, READY TO EXECUTE
- Audit existing 21 Patrol E2E tests + 6 isolated tests
- Run suite, report pass/fail per test

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

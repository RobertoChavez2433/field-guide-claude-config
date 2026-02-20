# Defects: PDF

Active patterns for pdf. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [BLOCKER] 2026-02-20: M&P Parser Regex Finds Only 4 of 131 Items — Anchor-Based Rewrite Needed
**Status**: DIAGNOSED (Session 403). Root cause confirmed via M&P testing harness.
**Symptom**: Springfield M&P extraction returns only 4 items (78-81) instead of 131. All 7 sampled GT items (1, 10, 25, 50, 75, 100, 131) show NOT FOUND.
**Root Cause**: Parser regex `^\s*Item\s+([0-9]+)\.?\s+(.+?)(?::\s*|\.\s+)(.*)$` has two fatal flaws:
1. **`^` line-start anchor**: Requires `Item` at beginning of a line, but Syncfusion's `PdfTextExtractor` does NOT preserve line breaks at item boundaries. The text comes as a continuous blob where items appear inline after previous item's body text (e.g., `...previous text. Item 3. Traffic Control:`).
2. **Title/body split pattern** `(?::\s*|\.\s+)`: Tries to separate title from body in one regex, but colon/period positions vary wildly across items (e.g., `Item 3. Traffic Control:` vs `Item 78. Remove & Salvage Ex. Hydrant` — the period in "Ex." triggers a false split).
**Why only items 78-81 matched**: On page 9 of the PDF, the Syncfusion text extraction happened to place line breaks before those 4 `Item` headers. All other 127 items had `Item` appearing mid-line.
**Quality gate is NOT the issue**: 13 of 14 pages have clean native text (avg corruption 2.1, avg single char ratio 0.044). Only page 1 is blank (cover page). The text content is there — the parser just can't find it.

**Diagnostic Evidence** (from M&P testing harness fixtures):
- `mp_quality_gate.json`: 14 pages, 13 native/1 OCR, avg corruption 2.1 — quality is fine
- `mp_native_text.json`: All 131 `Item N` headers present in raw text (confirmed via PowerShell regex scan)
- `mp_parsed_entries.json`: Only 4 entries (items 78-81), all from page_index 0 (assembled text offset)
- Scorecard: 5 BUG/HIGH metrics (pages_analyzed, max_corruption, entries_parsed, unique_items, matched)

**Proposed Fix — Anchor-Then-Segment Algorithm** (general-purpose, not Springfield-specific):
1. **Strip page headers**: Remove `\d{6}\s+\d{2}\s+\d{2}\s+\d{2}\s*-\s*\d+\s*MEASUREMENT AND PAYMENT` (CSI section numbering — standard across construction M&P docs)
2. **Find anchors**: Unanchored `Item\s+(\d+)` finds ALL 131 items (proven). No `^` needed.
3. **Segment**: Body of item N = text from its anchor position to the next anchor position
4. **Extract title**: Within each segment, split at first `:` or first sentence boundary after the item number + title phrase
5. **Strip preamble**: On first page with content, skip everything before the first `Item \d+` anchor (measurement/payment general clauses like `1.01 SUMMARY`, `1.02 MEASUREMENT OF QUANTITIES`)

This is general-purpose: any M&P PDF using `Item N` headings (standard construction contract format) will work. No Springfield-specific logic.

**Key files**:
- Parser: `lib/features/pdf/services/mp/mp_extraction_service.dart:219-287` (`_parseEntries` method)
- Regex: `lib/features/pdf/services/mp/mp_extraction_service.dart:229-233`
- Fixtures: `test/features/pdf/services/mp/fixtures/` (6 files, generated 2026-02-20)
- Scorecard: `test/features/pdf/services/mp/mp_stage_trace_diagnostic_test.dart`
- Fixture generator: `integration_test/generate_mp_fixtures_test.dart`

**PDF format observations** (from native text analysis):
- Page 1: Blank (0 chars, cover page)
- Page 2: Preamble (SECTION 01 22 00, PART 1 - GENERAL, measurement rules 1.01-1.03), then Item 1 and Item 2 start mid-page
- Pages 3-14: Each starts with header `864130 01 22 00 - N MEASUREMENT AND PAYMENT`, then items continue
- Page 14: Items 129-131, then "Other:" section with non-item notes
- Items use format: `Item N. Title: Body text...` or `Item N. Title\n: Body text...`
- Colon placement inconsistent: sometimes after title on same line, sometimes on next line

**Regeneration commands**:
```
pwsh -Command "flutter test integration_test/generate_mp_fixtures_test.dart -d windows --dart-define='SPRINGFIELD_MP_PDF=C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [319-331) M&P.pdf'"
pwsh -Command "flutter test test/features/pdf/services/mp/mp_stage_trace_diagnostic_test.dart"
```
**Ref**: @lib/features/pdf/services/mp/mp_extraction_service.dart:229-233

### [QUALITY] 2026-02-19: Permissive Scorecard Assertions Can Hide Real Extraction Regressions
**Pattern**: Stage trace scorecard assertions allowed degraded outputs (`parsed>=126`, `withAmount>=122`, `bugCount<=2`) to pass, creating false-green confidence while pipeline quality remained below target.
**Prevention**: Keep strict gates aligned to target outcomes (`parsed>=131`, `withAmount>=131`, `bugCount==0`, `lowCount==0`) and treat failures as upstream blockers instead of relaxing assertions.
**Ref**: @test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart:3900-3905

### [QUALITY] 2026-02-18: RowParserV3 Stage Confidence Can Mask High Skip Rates
**Pattern**: `RowParserV3` computes `StageReport.stageConfidence` from confidences of emitted items, while excluded/skipped rows do not reduce that value. A run can report high stage confidence even when many input rows are skipped.
**Prevention**: Include skip/exclusion ratio as a penalty term in stage confidence, or raise warning severity / fail guard when `excludedCount / inputCount` exceeds threshold.
**Ref**: @lib/features/pdf/services/extraction/stages/row_parser_v3.dart:241-279

### [DATA] 2026-02-18: Relaxed/Rescue PriceContinuation Gates Can Misclassify Rows When Item-Number Semantic Is Missing
**Pattern**: Mixed text+price rows can be incorrectly promoted to `priceContinuation` if `itemNumber` semantic is absent from `columnMap` (or unset per-page). In that case `hasItemNumber` is always false, so continuation gates may absorb legitimate base rows into prior items.
**Prevention**: Require `zones.itemNumberColumn != null` before relaxed mixed-text price-continuation gate and boilerplate rescue sweep are allowed. Add explicit test coverage for missing-item-semantic behavior.
**Ref**: @lib/features/pdf/services/extraction/stages/row_classifier_v3.dart:284,376

<!-- Add defects above this line -->

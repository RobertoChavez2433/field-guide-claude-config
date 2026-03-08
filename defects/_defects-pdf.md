# Defects: PDF

Active patterns for pdf. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [DATA] 2026-03-08: _measureContrast Bug — 70% Underreported After 1-Channel Conversion
**Pattern**: After `processed.convert(numChannels: 1)` at line 229, `_measureContrast(processed)` at line 233 calls `img.getLuminance(pixel)` which computes `0.299*r + 0.587*g + 0.114*b`. On a 1-channel image, `g=0` and `b=0`, so it returns `0.299 * r` instead of `r`. The `contrastAfter` metric is systematically underreported by ~70%. Does not affect downstream logic (metric-only), but corrupts diagnostic output.
**Prevention**: Either move `_measureContrast()` before the 1-channel conversion, or use `pixel.r` directly instead of `getLuminance()` (consistent with `_isDarkPixel` in grid_line_detector).
**Ref**: @lib/features/pdf/services/extraction/stages/image_preprocessor_v2.dart:229-233

### [DATA] 2026-03-07: Cross-Platform Renderer Divergence — $457K OCR Discrepancy
**Pattern**: `pdfx` uses AOSP PdfRenderer on Android (old PDFium fork) but upstream PDFium on Windows. Different font rendering → different OCR output for identical PDFs. DPI was correctly set (600 for crops) but irrelevant — grid pages never call `recognizeImage()`, only `recognizeCrop()`. The renderer pixel differences propagate through the OCR pipeline causing character confusion (5↔S, 9↔0, merged items).
**Prevention**: Use `pdfrx` (bundles upstream PDFium 144.0.7520.0 on ALL platforms). Returns BGRA8888 pixels (not PNG) — use `Image.fromBytes(order: ChannelOrder.bgra)`. Migration plan: `.claude/plans/2026-03-07-pdfrx-renderer-migration.md`.
**Ref**: @lib/features/pdf/services/extraction/stages/page_renderer_v2.dart:165 (Platform.isWindows gate)

### [QUALITY] 2026-03-02: Tesseract x_wconf Unreliable for Dollar Amounts — Root Cause of B1/B2 LOWs
**Pattern**: Tesseract reports 14-52% confidence on perfectly-extracted dollar amounts (e.g., "$860,970.00" at 34% conf, "$4,911.90" at 14%). The 50% OCR weight in `field_confidence_scorer.dart` weighted geometric mean amplifies this into B2 LOW. Also, 5/8 B1 unitPrice correction patterns are comma→period substitution (`european_periods`), not resolution issues.
**Prevention**: Geometry-aware upscaling (2.0→2.71x) confirmed this is NOT a resolution problem. Fixes needed at Tesseract interpretation layer: (1) confidence floor override when format+interpretation both validate, (2) comma-recovery heuristic for european_periods, (3) space-strip for spurious word breaks.
**Ref**: @lib/features/pdf/services/extraction/scoring/field_confidence_scorer.dart:298-306

### [DATA] 2026-03-02: Geometry-Aware Upscaler Causes Comma/Period OCR Confusion — $357B Budget (BLOCKER-19)
**Pattern**: Commit `22f2d7b` replaced uniform 600 DPI with `targetDpi = 600 + 300 * max(0, 1 - cropWidth/500)`. Narrow columns upscaled to 2.28-2.71x instead of uniform 2.0x. At higher DPI, Tesseract misreads commas as periods in quantities (e.g., `9,235` → `9.235`). Math backsolve then inflates `unitPrice` 1000x to compensate. Budget = `sum(qty * inflatedPrice)` = $357B instead of $7.88M. Additionally, `bidAmount` (correctly OCR'd) is LOST at `ResultConverter` boundary — never reaches `BidItem` or SQLite. Dashboard recalculates from corrupted `qty * unitPrice`.
**Prevention**: (1) Revert to uniform 600 DPI. (2) Preserve `bidAmount` through full chain: v2 pipeline → legacy ParsedBidItem → BidItem → SQLite → all 5 display sites. (3) Always use `bidAmount` as source of truth for totals. (4) Add Supabase migration for `bid_amount` column BEFORE app deploy.
**Ref**: @lib/features/pdf/services/extraction/shared/crop_upscaler.dart, @lib/features/pdf/services/extraction/pipeline/result_converter.dart:31, @lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:313

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

### [CONFIG] 2026-03-07: V2 OCR Engine Does Not Thread DPI to Tesseract — 70 DPI Fallback on Android
**Pattern**: `TesseractEngineV2.recognizeImage()` and `recognizeCrop()` compute source DPI via `_computeSourceDpi()` but never call `tess.setVariable("user_defined_dpi", dpi)`. The C++ layer (`flusseract.cpp:95-108`) checks for this variable, falls back to 70 DPI when absent. On Android (pdfx renderer, no embedded DPI metadata), Tesseract processes 300 DPI images as 70 DPI — 4.3x mismatch degrades page segmentation. On Windows (Printing.raster embeds DPI), auto-detection masks the bug. V1 engine had this correct.
**Prevention**: Always call `tess.setVariable("user_defined_dpi", sourceDpi.toString())` before `hocrText()` in both `recognizeImage()` and `recognizeCrop()`. Fix plan: `.claude/plans/2026-03-07-ocr-dpi-fix.md`
**Ref**: @lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart:70-76, :114-119

<!-- Add defects above this line -->

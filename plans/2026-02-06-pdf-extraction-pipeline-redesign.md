# PDF Extraction Pipeline Redesign: Native Text First, OCR Fallback

**Date**: 2026-02-06
**Status**: Approved
**Scope**: Restructure bid schedule import pipeline with intelligent text extraction routing
**Supersedes**: Builds on top of existing Table Structure Analyzer v2 work (not replacing it)

---

## Overview

### Purpose
Restructure `importBidSchedule()` to try Syncfusion native text extraction first, converting `TextWord` objects into `OcrElement` format for the existing v2 table extraction pipeline. OCR becomes a fallback for actual scanned documents.

### Scope
- **Included**: Native text extraction route, TextWord->OcrElement converter with coordinate scaling, routing logic with `needsOcr()` gate, hybrid column detection (text-derived + image-scan fallback)
- **Excluded**: Per-page mixed routing (noted as future enhancement), ClumpedTextParser changes, PSM tuning, word-level OCR confidence filtering (separate Phase 2 work)

### Success Criteria
- [ ] Springfield PDF: 100+ items extracted (currently 23 at best, should have ~130)
- [ ] Item numbers are actual numbers, not OCR garbage ("nN", "(c)", "il")
- [ ] All 6 pages processed (currently only pages 4-5)
- [ ] Scanned PDFs still fall through to OCR path
- [ ] Pipeline automatically routes to native text for digital PDFs

---

## Background & Problem Statement

### What Happened (4-5 days of work)

Over sessions 301+, the PDF extraction pipeline went through multiple iterations:

1. **Table Structure Analyzer v2** (commits `9bd2fa5` through `0a4cbb0`): Built row classifier, region detector, anchor correction, column detection, cell extraction, math validation. 6 phases across 3 commits.
2. **Phase 1** (commit `836b856`): Removed "destructive binarization" from image preprocessing because it was destroying 92% of image data (1.7MB -> 136KB).
3. **Phases 2+3** (commit `fe79596`): Added numeric content gate to row classifier + post-processing safeguards.
4. **Numeric gate fix** (uncommitted): Removed the hard numeric gate, converted to confidence modifier.

### Current Results (All Terrible)

Testing with the Springfield DWSRF 6-page bid schedule PDF:

| Session | Preprocessing | Items Extracted | Invalid IDs | Pages Found | UNKNOWN Rows |
|---------|--------------|-----------------|-------------|-------------|--------------|
| 10:33 (binarized) | 140KB/page, 11s | 71 | 22 (31%) | 2-5 | 181/282 (64%) |
| 16:06 (grayscale) | 1MB/page, 1.5s | 3 | 0 | 4 only | 194/248 (78%) |
| 16:27 (grayscale, no gate) | 1MB/page, 1.5s | 23 | 3 (13%) | 4-5 | 161/248 (65%) |

### Root Cause Analysis

**The cascade**: Bad OCR text -> no confidence filtering -> corrupted item numbers -> rows classified UNKNOWN (65%) -> not enough DATA rows near headers -> table regions not detected on pages 1-3 -> only 23/~130 items extracted.

### The Critical Discovery

**The bid schedule PDFs are NOT scanned documents.** From Session 226:

> "Current PDFs are NOT scanned. Analysis of test fixtures shows the issue is text extraction formatting (clumped columns), not missing text."

This means Syncfusion's `extractTextLines()` CAN extract native text WITH bounding boxes. **The entire OCR pipeline is being used on digital PDFs that don't need OCR.**

---

## Architecture Decisions

| Decision | Choice | Reasoning | Date |
|----------|--------|-----------|------|
| How to connect systems | TextWord -> OcrElement -> v2 pipeline | Preserves all v2 post-processing (math validation, dedup, split-row, consistency). No throwaway work. Both systems get stronger over time. | 2026-02-06 |
| Column detection for native text | Hybrid: text-derived first, image-scan fallback | Clean native text gives precise X positions; HeaderColumnDetector should work well. Only render page images if header detection confidence is low. | 2026-02-06 |
| Routing granularity | Whole-document, with TODO for per-page override | Start simple. Add `// TODO: Upgrade to per-page routing` for future mixed documents (digital pages + scanned addendum). | 2026-02-06 |
| Cascade order | Native text first, OCR fallback | These PDFs are NOT scanned. OCR is the wrong tool for digital PDFs. Pipeline should check first. | 2026-02-06 |
| Don't scrap existing code | Keep both systems | Downstream v2 pipeline works. OCR needed long-term for scanned documents. flusseract chosen for cross-platform. | 2026-02-06 |
| OcrElement is universal format | Both paths produce OcrElements | Downstream pipeline doesn't care about source. Only text + boundingBox + pageIndex matter. | 2026-02-06 |

---

## Data Model

No new entities. We're bridging existing types.

### TextWord -> OcrElement Conversion

| Syncfusion TextWord | OcrElement | Transform |
|---------------------|------------|-----------|
| `text` | `text` | Direct copy |
| `bounds.left` | `boundingBox.left` | x scaleFactor |
| `bounds.top` | `boundingBox.top` | x scaleFactor |
| `bounds.width` | `boundingBox.width` | x scaleFactor |
| `bounds.height` | `boundingBox.height` | x scaleFactor |
| *(n/a)* | `confidence` | `1.0` (native text is exact) |
| *(from loop index)* | `pageIndex` | Page number |

### Coordinate Transform

```
scaleFactor = renderDPI / 72.0
```

Syncfusion uses PDF points (72 DPI). The v2 pipeline uses image pixel coordinates at whatever DPI pages are rendered at. The same `renderDPI` already used in `_runOcrPipeline()` for page image rendering must be used here so coordinates align with any image-based fallback column detection.

### New File

| File | Purpose |
|------|---------|
| `lib/features/pdf/services/text_extraction/native_text_extractor.dart` | Extracts TextLines/TextWords via Syncfusion, converts to `List<List<OcrElement>>` (per-page) |

### Existing Types (Unchanged)

- `OcrElement` -- universal format, no changes needed
- `ColumnBoundaries` / `ColumnDef` -- v2 column format, no changes
- `ParsedBidItem` -- final output, no changes
- `TableExtractionResult` -- v2 result wrapper, no changes

---

## Pipeline Flow

### Updated importBidSchedule() Architecture

```
importBidSchedule()
       |
       v
 Extract native text (Syncfusion extractTextLines)
       |
       v
 needsOcr() check ---- Yes ---> _runOcrPipeline() (existing)
       |                              |
       No                             |
       |                              |
       v                              v
 NativeTextExtractor            Tesseract OCR
 TextWord -> OcrElement         HOCR -> OcrElement
 (confidence = 1.0)             (confidence = variable)
       |                              |
       +----------+-------------------+
                  |
                  v
        List<List<OcrElement>>
                  |
                  v
         v2 TableExtractor.extract()
         (RowClassifier -> RegionDetector ->
          ColumnDetector -> CellExtractor ->
          TableRowParser -> PostProcessing)
                  |
                  v
         ParsedBidItem results
```

Both paths produce `List<List<OcrElement>>` (one list per page), so the downstream pipeline is identical.

### Column Detection Sub-Flow (Native Text Path)

```
OcrElements with precise positions
       |
       v
 HeaderColumnDetector (X-position clustering from header words)
       |
   Confidence >= threshold? --- No ---> Render page images
       |                                      |
       Yes                                    v
       |                              LineColumnDetector
       |                              (image scan fallback)
       |                                      |
       +--------------+-----------------------+
                      v
              ColumnBoundaries
```

### Key Behavior Change

| Before | After |
|--------|-------|
| Always render all pages to images | Only render if `needsOcr()` or column detection needs fallback |
| Always run Tesseract on every page | Skip Tesseract entirely for digital PDFs |
| ~15-20s for OCR pipeline | <1s for native text extraction |
| 23 items with garbage IDs | Expected 100+ items with clean IDs |

---

## Implementation Phases

### Phase 1: NativeTextExtractor + Routing (Core Change)

**Goal**: Wire up Syncfusion native text extraction as the first choice in `importBidSchedule()`.

**Files touched:**

| File | Change |
|------|--------|
| `lib/features/pdf/services/text_extraction/native_text_extractor.dart` | **New** -- TextWord -> OcrElement converter with coordinate scaling |
| `lib/features/pdf/services/pdf_import_service.dart` | Restructure `importBidSchedule()` -- add native text route before OCR, wire `needsOcr()` gate |

**What it does:**

1. Extract text via Syncfusion `extractTextLines()`
2. Run `needsOcr()` on extracted text
3. If native text OK: convert TextWords -> OcrElements, pass to TableExtractor
4. If needs OCR: fall through to existing OCR pipeline (unchanged)
5. Add `// TODO: Upgrade to per-page routing for mixed documents (digital + scanned pages)`

**Pre-work:**
- Commit the uncommitted numeric gate changes in row_classifier.dart first
- Run the spike tool (`dart run tooling/pdf_textline_spike.dart`) on Springfield PDF to verify Syncfusion output before writing any code

**Verification:** Import Springfield PDF, compare item count and quality to current 23-item baseline.

### Phase 2: Hybrid Column Detection

**Goal**: Skip expensive image rendering when text-derived columns are good enough.

**Files touched:**

| File | Change |
|------|--------|
| `lib/features/pdf/services/table_extraction/column_detector.dart` | Add text-derived column source, skip image rendering when text-derived confidence is high |

**What it does:**

1. When native text path is used, let HeaderColumnDetector work with clean OcrElements first
2. If header detection confidence is high enough: skip LineColumnDetector (no image rendering needed)
3. If confidence is low: render page image, run LineColumnDetector as fallback
4. Existing cross-validation and anchor correction continue to apply

**Verification:** Confirm column detection works without page images on Springfield PDF. Verify fallback triggers correctly on edge cases.

### Phase 3: Logging + Metrics

**Goal**: Observability for which extraction path was taken and why.

**Files touched:**

| File | Change |
|------|--------|
| `lib/features/pdf/services/pdf_import_service.dart` | Log route decision (native vs OCR) with reasoning |
| `lib/features/pdf/services/table_extraction/table_extractor.dart` | Track extraction method in diagnostics |

**What it does:** Log native text chars/page, single-char ratio, final decision, and extraction method in results.

### Phase Order

Phase 1 is the big win. Phase 2 is optimization (speed). Phase 3 is observability. Each phase is independently shippable.

---

## Future Work (Not In Scope)

These items are deferred but documented for later:

### OCR Quality Improvements (When OCR IS Needed)

| Item | File | Description |
|------|------|-------------|
| Word-level confidence filtering | `tesseract_ocr_engine.dart` `_parseHocr()` line 406 | Skip words below 0.50 confidence threshold. Single most impactful OCR fix. |
| PSM mode experimentation | `tesseract_ocr_engine.dart` line 165 | Test PSM 6 (single block) and PSM 11 (sparse text) for tables. Currently PSM 3 (auto). |
| Preprocessing tuning | `image_preprocessor.dart` | Otsu's thresholding, higher contrast, conditional preprocessing |

### Per-Page Mixed Routing

Upgrade from whole-document to per-page routing for mixed documents (digital bid schedule + scanned addendum). Check each page individually with `needsOcr()`.

---

## What NOT to Change

- Column detection code structure (works well, 0.90 confidence)
- Math validation (works)
- Post-processing pipeline (works)
- Row classifier logic (sound, just needs clean input)
- Table region detector logic (sound, just needs DATA rows)
- flusseract package (working Tesseract integration)
- Tesseract engine mode (LSTM is correct choice)
- CellExtractor / TableRowParser (work correctly)

---

## Key Technical Notes

### OcrElement Is Format-Agnostic

```dart
class OcrElement {
  final String text;           // Recognized text
  final Rect boundingBox;      // Bounding box (left, top, right, bottom)
  final double? confidence;    // Optional confidence (0.0-1.0)
  final int? pageIndex;        // Page index
}
```

The entire downstream pipeline consumes `List<List<OcrElement>>` and doesn't care whether elements came from Tesseract or Syncfusion.

### Syncfusion Provides Word-Level Bounding Boxes

`PdfTextExtractor.extractTextLines()` returns:
- `TextLine.bounds` -- Rect per line
- `TextLine.wordCollection` -- Array of `TextWord` objects
- `TextWord.bounds` -- Rect per word
- `TextWord.text` -- The word text

The conversion `TextWord -> OcrElement` is trivial. The ColumnLayoutParser already does this extraction (lines 49-81).

### Existing Dead Code to Wire In

| Code | Location | Purpose |
|------|----------|---------|
| `extractRawText()` | pdf_import_service.dart lines 177-248 | Native text extraction (string only, no bounds) |
| `needsOcr()` | pdf_import_service.dart lines 263-294 | Heuristics: empty text, <50 chars/page, >30% single-char words |
| `ColumnLayoutParser` X-clustering | column_layout_parser.dart lines 619-645 | Gap-based clustering algorithm (reference for text-derived columns) |

### Current importBidSchedule() Flow (Before)

```
1. ALWAYS run OCR (Tesseract) -- _runOcrPipeline()
2. Feed OCR -> TableExtractor (v2 pipeline)
3. If v2 fails -> ColumnLayoutParser (Syncfusion native text, separate extraction)
4. If that fails -> ClumpedTextParser
5. If that fails -> RegexFallback
```

The ColumnLayoutParser is already a fallback but tried LAST. It uses Syncfusion native text with X-position clustering and produces `List<ParsedBidItem>`. The new design makes native text the FIRST path, feeding into the v2 pipeline instead of bypassing it.

---

## File References

### Core Pipeline Files
| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `lib/features/pdf/services/pdf_import_service.dart` | Main orchestrator -- needs restructuring | `extractRawText()` 177-248, `needsOcr()` 263-294, `importBidSchedule()` 694+ |
| `lib/features/pdf/services/ocr/tesseract_ocr_engine.dart` | Tesseract wrapper | `_parseHocr()` 406, PSM config 165 |
| `lib/features/pdf/services/ocr/image_preprocessor.dart` | Image preprocessing | `_preprocessIsolate()` 152-171 |
| `lib/features/pdf/services/ocr/ocr_element.dart` | Universal element model | Full file -- simple data class |

### Table Extraction Pipeline
| File | Purpose |
|------|---------|
| `lib/features/pdf/services/table_extraction/table_extractor.dart` | Pipeline orchestrator |
| `lib/features/pdf/services/table_extraction/row_classifier.dart` | Row classification |
| `lib/features/pdf/services/table_extraction/table_region_detector.dart` | Region detection |
| `lib/features/pdf/services/table_extraction/column_detector.dart` | Column detection (header + line + cross-validation + anchor correction) |
| `lib/features/pdf/services/table_extraction/cell_extractor.dart` | Cell extraction |
| `lib/features/pdf/services/table_extraction/table_row_parser.dart` | Row parsing |
| `lib/features/pdf/services/table_extraction/post_process/` | Post-processing directory |

### Legacy Parsers (Reference for X-Position Clustering)
| File | Purpose |
|------|---------|
| `lib/features/pdf/services/parsers/column_layout_parser.dart` | X-position clustering algorithm (lines 619-645), TextWord extraction (lines 49-81) |
| `lib/features/pdf/services/parsers/clumped_text_parser.dart` | Token-based parsing for clumped text (no positions) |

### Thresholds & Constants
| File | Key Constants |
|------|--------------|
| `row_classifier.dart` lines 79-82 | `kMinDataElements=3`, `kMaxDataElements=8` |
| `row_classifier.dart` line 17 | Item number regex: `^\d+(\.\d+)?\.?$` |
| `table_region_detector.dart` line 31 | `kMinDataRowsAfterHeader=2` |
| `table_region_detector.dart` line 37 | `kMaxDataRowLookahead=5` |
| `pdf_import_service.dart` | `kMinCharsPerPage=50`, `kMaxSingleCharRatio=0.30` |
| `column_layout_parser.dart` line 21 | Gap thresholds: `[18.0, 25.0, 35.0, 50.0]` |

### Native Code
| File | Purpose |
|------|---------|
| `packages/flusseract/src/flusseract.cpp` | C++ Tesseract bridge, OEM_LSTM_ONLY (line 52) |
| `packages/flusseract/lib/tesseract.dart` | FFI wrapper, PSM enum |
| `packages/flusseract/lib/pix_image.dart` | PixImage creation from bytes |

### Test PDF
| File | Purpose |
|------|---------|
| `Pre-devolopment and brainstorming/Screenshot examples/Companies IDR Templates and examples/Pay items and M&P/864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf` | Primary test PDF (6 pages, 1.1MB, ~130 bid items) |

### Spike/Testing Tools
| File | Purpose |
|------|---------|
| `tooling/pdf_textline_spike.dart` | CLI tool to inspect Syncfusion TextLine output with bounds |

### Related Plans
| File | Purpose |
|------|---------|
| `.claude/plans/pdf-table-structure-analyzer-v2.md` | Original v2 plan with all 14 design decisions |
| `.claude/plans/2026-02-06-fix-extraction-regression-row-classifier-gate.md` | Numeric gate fix plan |
| `.claude/backlogged-plans/OCR-Fallback-Implementation-Plan.md` | Original OCR plan from Session 226 |

---

## Git Context

### Recent Commits
```
fe79596 feat: OCR preprocessing Phases 2+3 (row classifier + post-processing safeguards)
836b856 feat: remove destructive binarization from OCR preprocessing (Phase 1)
0a4cbb0 feat: PDF Table Structure Analyzer Phases 5+6 (Parser Integration + Regression Guard)
eafae91 feat: PDF Table Structure Analyzer Phases 3+4 (Anchor Correction + Math Validation)
9bd2fa5 feat: PDF Table Structure Analyzer Phases 1+2 (Row Classifier + Region Detector)
```

### Uncommitted Changes (Commit Before Starting)
```
M lib/features/pdf/services/table_extraction/row_classifier.dart     (numeric gate -> confidence modifier)
M test/features/pdf/table_extraction/row_classifier_test.dart        (updated test expectations)
```

---

## Agent Assignments

| Phase | Agent | Task |
|-------|-------|------|
| Pre-work | qa-testing-agent | Run spike tool, verify Syncfusion output on Springfield PDF |
| Phase 1 | backend-data-layer-agent | NativeTextExtractor class, coordinate transform |
| Phase 1 | pdf-agent | Wire routing logic in pdf_import_service.dart |
| Phase 2 | pdf-agent | Hybrid column detection in column_detector.dart |
| Phase 3 | pdf-agent | Logging and metrics |
| Verify | qa-testing-agent | Import Springfield PDF, compare to baseline |

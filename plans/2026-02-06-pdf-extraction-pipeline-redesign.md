# PDF Extraction Pipeline Redesign: Native Text First, OCR Fallback

**Date**: 2026-02-06
**Status**: Draft - Needs review in next session
**Scope**: Restructure bid schedule import pipeline with intelligent text extraction routing
**Supersedes**: Builds on top of existing Table Structure Analyzer v2 work (not replacing it)

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

**Key observation**: Both binarized AND non-binarized approaches produce terrible results. The old binarization found more items (71) but 31% had garbage item numbers like "BEES N| Fi", "BEN on", "oO". The new approach found fewer items but they weren't any cleaner. Average OCR confidence ~0.72-0.75 in all cases.

### Root Cause Analysis (Session Discussion)

We investigated four areas in parallel using research agents:

**1. OCR Preprocessing** - Neither binarization nor grayscale produces good results. Tesseract floods hundreds of "Empty page!!" messages on preprocessed images regardless of approach. The preprocessing debate is a red herring.

**2. No Word-Level Confidence Filtering** - The pipeline has ZERO filtering on individual OCR word confidence. `_parseHocr()` accepts ALL words regardless of confidence score. Words at 40% confidence (garbage) pass through unchanged. Only the average confidence is checked (0.728 passes the 0.60 gate).

**3. Row Classifier** - 65% of rows classified as UNKNOWN because OCR produces garbage item numbers that fail the regex `^\d+(\.\d+)?\.?$`. The classifier logic is sound - it just gets garbage input.

**4. Table Region Detection** - Requires 2+ DATA rows in a 5-row lookahead after each HEADER. With 65% UNKNOWN rows, pages 1-3 never have enough DATA rows near headers. Only pages 4-5 get table regions.

**The cascade**: Bad OCR text -> no confidence filtering -> corrupted item numbers -> rows classified UNKNOWN (65%) -> not enough DATA rows near headers -> table regions not detected on pages 1-3 -> only 23/~130 items extracted.

### The Critical Discovery

**The bid schedule PDFs are NOT scanned documents.** From the backlogged OCR plan (Session 226):

> "Current PDFs are NOT scanned. Analysis of test fixtures shows the issue is text extraction formatting (clumped columns), not missing text. Existing parsers (ClumpedTextParser, ColumnLayoutParser) handle these cases."

This means:
- Syncfusion's `extractTextLines()` CAN extract native text WITH bounding boxes from these PDFs
- The text exists but comes out "clumped" (columns merged together)
- **The entire OCR pipeline is being used on digital PDFs that don't need OCR**

### What We Decided

1. **Don't scrap the existing code** - The downstream pipeline (column detection, row classification, cell extraction, post-processing) is architecturally sound. Column detection consistently finds 6 columns at 0.90 confidence. Math validation works. The problem is at the input stage.

2. **Add a logic check at the beginning of the pipeline** - The pipeline should determine what it's looking at before using the biggest tool in its kit. Try native text extraction first, fall back to OCR only when needed.

3. **Keep OCR as fallback** - We need OCR long-term for actual scanned documents. flusseract was chosen specifically because it works on iOS, Android, and Windows.

4. **Fix OCR quality when OCR IS used** - Word-level confidence filtering and PSM tuning haven't been tried yet.

---

## What Already Exists (Don't Rebuild These)

### Working Components

| Component | Location | Status |
|-----------|----------|--------|
| Column detection (line-based) | `lib/features/pdf/services/table_extraction/column_detector.dart` | Works well (0.90 confidence) |
| Header column detection | `lib/features/pdf/services/table_extraction/header_column_detector.dart` | Works |
| Line column detection | `lib/features/pdf/services/table_extraction/line_column_detector.dart` | Works |
| Anchor correction | Within column_detector.dart | Works |
| Row classifier structure | `lib/features/pdf/services/table_extraction/row_classifier.dart` | Logic is sound, needs clean input |
| Table region detector | `lib/features/pdf/services/table_extraction/table_region_detector.dart` | Logic is sound, needs DATA rows |
| Cell extractor | `lib/features/pdf/services/table_extraction/cell_extractor.dart` | Works |
| Table row parser | `lib/features/pdf/services/table_extraction/table_row_parser.dart` | Works |
| Post-processing (math, dedup, split, consistency) | `lib/features/pdf/services/table_extraction/post_process/` | Works |
| Math validation | `lib/features/pdf/services/table_extraction/post_process/post_process_math_validation.dart` | Works |
| Image preprocessing | `lib/features/pdf/services/ocr/image_preprocessor.dart` | Exists, may need tuning for OCR path |
| Tesseract integration | `lib/features/pdf/services/ocr/tesseract_ocr_engine.dart` | Works, needs config tuning |
| HOCR parsing | Within tesseract_ocr_engine.dart (lines 406-454) | Works, needs confidence filtering |
| OCR pipeline orchestration | `lib/features/pdf/services/pdf_import_service.dart` | Needs restructuring |

### Dead Code That Should Be Wired In

| Code | Location | Purpose |
|------|----------|---------|
| `extractRawText()` | pdf_import_service.dart (lines 177-248) | Native text extraction via Syncfusion PdfTextExtractor |
| `needsOcr()` | pdf_import_service.dart (lines 263-294) | Heuristics to detect if OCR is needed |
| `ColumnLayoutParser` | `lib/features/pdf/services/parsers/column_layout_parser.dart` | Already extracts TextLine/TextWord with bounds from Syncfusion |

### Existing Tools

| Tool | Location | Purpose |
|------|----------|---------|
| `pdf_textline_spike.dart` | `tooling/pdf_textline_spike.dart` | CLI tool to inspect Syncfusion TextLine output |
| `pdf_textline_spike_test.dart` | Test harness for the spike tool |

---

## Key Technical Findings

### OcrElement Is Format-Agnostic

The `OcrElement` class (`lib/features/pdf/services/ocr/ocr_element.dart`) is simple:

```dart
class OcrElement {
  final String text;           // Recognized text
  final Rect boundingBox;      // Bounding box (left, top, right, bottom)
  final double? confidence;    // Optional confidence (0.0-1.0)
  final int? pageIndex;        // Page index
}
```

The entire downstream pipeline (RowClassifier, ColumnDetector, CellExtractor, TableRowParser) consumes `List<List<OcrElement>>` and **doesn't care** whether the elements came from Tesseract or Syncfusion. Only text + boundingBox + pageIndex are used by downstream components. Confidence is optional and only used for diagnostics/quality tracking.

### Syncfusion Provides Word-Level Bounding Boxes

Syncfusion's `PdfTextExtractor.extractTextLines()` returns:
- `TextLine.bounds` - Rect with left, top, width, height per line
- `TextLine.wordCollection` - Array of `TextWord` objects
- `TextWord.bounds` - Rect with left, top, width, height per word
- `TextWord.text` - The word text

This is structurally equivalent to what HOCR parsing produces from Tesseract. The conversion `TextWord -> OcrElement` is trivial.

### The "Clumped Text" Problem (From Session 226)

Native text extraction works but the text comes out "clumped" - columns merged together. This is why the existing `ColumnLayoutParser` and `ClumpedTextParser` were built. However, those parsers are LEGACY fallbacks that don't use the Table Structure Analyzer v2 pipeline.

**The key insight**: If we convert Syncfusion TextWords to OcrElements with bounding boxes, we can feed them into the v2 pipeline (which has proper column detection via vertical line scanning). The "clumped text" problem may not apply when we use word-level bounding boxes rather than line-level text.

### Coordinate System Consideration

**Important**: Syncfusion text extraction returns coordinates in PDF coordinate space (72 DPI, origin at bottom-left on some implementations). The OCR pipeline uses image coordinate space (300 DPI, origin at top-left). Coordinate transformation will be needed when converting TextWord bounds to OcrElement bounds. The page images rendered for column line detection are at a specific DPI, so native text coordinates need to be scaled to match.

### PSM (Page Segmentation Mode) - Unexplored Tuning

PSM is a Tesseract configuration that tells it how to analyze page layout:
- **PSM 3 (auto)** - Current setting. Tesseract guesses the layout (columns, blocks, etc.)
- **PSM 6 (single block)** - Treats entire image as one uniform text block
- **PSM 11 (sparse text)** - Expects text scattered with gaps (good for forms/tables)

For bid schedule tables, PSM 3 may be oversegmenting the page into phantom columns. PSM 6 or 11 might give better results. This has never been tested.

Config location: `lib/features/pdf/services/ocr/tesseract_ocr_engine.dart:165`

### Tesseract Engine Mode

Currently using `OEM_LSTM_ONLY` (neural network engine, set in `packages/flusseract/src/flusseract.cpp:52`). This is the most accurate mode but is sensitive to image quality. The legacy engine (`OEM_TESSERACT_ONLY`) is more tolerant of imperfect images but less accurate overall.

---

## Proposed Pipeline Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   PDF Import Service                      │
│                  importBidSchedule()                       │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  STEP 1: ROUTE DECISION │
              │  Try native text first  │
              │  extractTextLines()     │
              │  + needsOcr() check     │
              └────────────────────────┘
                    │              │
            Native text OK    Needs OCR
                    │              │
                    ▼              ▼
    ┌──────────────────┐  ┌──────────────────┐
    │ STEP 2a: CONVERT  │  │ STEP 2b: OCR     │
    │ TextWord →        │  │ Render → Preproc  │
    │ OcrElement        │  │ → Tesseract       │
    │ (confidence=1.0)  │  │ → HOCR parse      │
    │ Scale coords to   │  │ → Confidence      │
    │ match image space  │  │   filtering       │
    └──────────────────┘  └──────────────────┘
                    │              │
                    └──────┬───────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  STEP 3: TABLE         │
              │  EXTRACTION PIPELINE   │
              │  (Existing v2 code)    │
              │  RowClassifier →       │
              │  RegionDetector →      │
              │  ColumnDetector →      │
              │  CellExtractor →       │
              │  TableRowParser →      │
              │  PostProcessing        │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  STEP 4: RESULTS       │
              │  ParsedBidItems        │
              │  + extraction method   │
              │  + quality metrics     │
              └────────────────────────┘
```

Both paths produce `List<List<OcrElement>>` (one list per page), so the downstream pipeline is identical.

---

## Implementation Plan

### Phase 1: Native Text Extraction Route (PRIMARY)

**Goal**: Wire up Syncfusion native text extraction as the first choice in `importBidSchedule()`.

#### 1A. Verify native text quality on Springfield PDF

Before writing any code, run the existing spike tool to confirm what Syncfusion returns:
```bash
dart run tooling/pdf_textline_spike.dart "<path to Springfield PDF>" --words --pages=1-6
```

**What to verify**:
- Does it return text? (We expect yes - Session 226 confirmed these aren't scanned)
- Does extractTextLines() give word-level bounds? (TextWord.bounds)
- Are the bounds accurate and usable?
- What coordinate system are they in? (PDF points vs pixels)

#### 1B. Build TextWord -> OcrElement converter

Create a converter that transforms Syncfusion's native text output into the OcrElement format the pipeline expects.

**File**: New file, likely `lib/features/pdf/services/text_extraction/native_text_extractor.dart`

**Key considerations**:
- Convert PDF coordinate space to image coordinate space (scale factor = renderDPI / 72)
- Handle coordinate origin differences (PDF may be bottom-left, images are top-left)
- Set confidence = 1.0 for native text (it's reading actual text, not guessing)
- Preserve pageIndex
- Filter empty/whitespace-only words

#### 1C. Wire routing logic into importBidSchedule()

Modify `lib/features/pdf/services/pdf_import_service.dart` to:

1. Call `extractTextLines()` on each page
2. Run `needsOcr()` heuristics on the result
3. If native text is good: convert to OcrElements, skip OCR entirely
4. If native text is bad: fall through to existing OCR pipeline
5. Pass OcrElements (from either source) to TableExtractor

**The `needsOcr()` heuristics already exist** (lines 263-294):
- Empty text → needs OCR
- < 50 chars per page (`kMinCharsPerPage`) → needs OCR
- > 30% single-character words (`kMaxSingleCharRatio`) → needs OCR

#### 1D. Test with Springfield PDF

Run the app, import the Springfield PDF, compare results:
- How many items extracted?
- Are item numbers correct (actual numbers, not "nN" or "©")?
- Are descriptions readable?
- Do quantities/prices parse correctly?

### Phase 2: OCR Quality Improvements (FALLBACK PATH)

**Goal**: When OCR IS needed (scanned documents), make it produce better results.

#### 2A. Add word-level confidence filtering

**File**: `lib/features/pdf/services/ocr/tesseract_ocr_engine.dart`

In `_parseHocr()` (line 406), add filtering:
```dart
// Skip words below confidence threshold
if (confidence != null && confidence < 0.50) continue;
```

This is the single most impactful OCR fix. It prevents garbage words from entering the pipeline at all. The threshold (0.50) can be tuned - start conservative.

#### 2B. Experiment with PSM modes

**File**: `lib/features/pdf/services/ocr/tesseract_ocr_engine.dart`

Test PSM 6 (single block) and PSM 11 (sparse text) on the Springfield PDF when using OCR path. Compare:
- Number of "Empty page!!" messages
- Average confidence
- Items extracted
- Item number accuracy

This is experimental - we don't know which PSM mode will work best. May need to be configurable per document type.

#### 2C. Investigate preprocessing tuning

If PSM changes help, the current grayscale + 1.3x contrast may be sufficient. If not, consider:
- Otsu's thresholding (global, less destructive than adaptive)
- Higher contrast multiplier
- Conditional preprocessing based on image analysis

**File**: `lib/features/pdf/services/ocr/image_preprocessor.dart`

### Phase 3: Integration & Robustness

#### 3A. Add extraction method tracking

Track which method was used (native vs OCR) in the result, so the UI can show appropriate warnings:
- Native text: high confidence, no warnings needed
- OCR: show "Extracted via OCR - please verify accuracy" banner

#### 3B. Add logging for route decision

Log why the pipeline chose native text vs OCR, including:
- Native text chars per page
- Single-char word ratio
- Final decision and reasoning

#### 3C. Handle edge cases

- PDF with mixed pages (some native text, some scanned)
- PDF with native text that's actually garbage (embedded but corrupted)
- Coordinate scaling edge cases (different page sizes, rotated pages)

---

## Decision Log

| Decision | Reasoning | Date |
|----------|-----------|------|
| Don't scrap existing code | Downstream pipeline (column detection, post-processing) works. Problem is at input stage, not processing. | 2026-02-06 |
| Native text first, OCR fallback | These PDFs are NOT scanned (confirmed Session 226). OCR is the wrong tool for digital PDFs. Pipeline should check first. | 2026-02-06 |
| Keep OCR pipeline | Need it long-term for actual scanned documents. flusseract chosen for cross-platform (iOS/Android/Windows). | 2026-02-06 |
| Binarization debate is a red herring | Both binarized (140KB) and non-binarized (1MB) produce similar garbage. Neither approach fixes OCR on digital PDFs. | 2026-02-06 |
| Word-level confidence filtering needed | No filtering exists. 40% confidence words pass through unchanged. Most concrete gap found in research. | 2026-02-06 |
| PSM mode worth testing | Currently PSM 3 (auto), never tested alternatives. PSM 6 or 11 may work better for tables. Experimental. | 2026-02-06 |
| OcrElement is the universal format | Both native text and OCR can produce OcrElements. Downstream pipeline doesn't care about source. | 2026-02-06 |

---

## What NOT to Change

- Column detection code (works well)
- Math validation (works)
- Post-processing pipeline (works)
- Row classifier logic (sound, just needs clean input)
- Table region detector logic (sound, just needs DATA rows)
- flusseract package (working Tesseract integration)
- Tesseract engine mode (LSTM is correct choice)

---

## File References

### Core Pipeline Files
| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `lib/features/pdf/services/pdf_import_service.dart` | Main orchestrator - needs restructuring | `extractRawText()` lines 177-248, `needsOcr()` lines 263-294, `importBidSchedule()` line 694+ |
| `lib/features/pdf/services/ocr/tesseract_ocr_engine.dart` | Tesseract wrapper | `_parseHocr()` line 406 (add confidence filter), PSM config line 165 |
| `lib/features/pdf/services/ocr/image_preprocessor.dart` | Image preprocessing | `_preprocessIsolate()` lines 152-171 |
| `lib/features/pdf/services/ocr/ocr_element.dart` | Universal element model | Full file - simple data class |

### Table Extraction Pipeline
| File | Purpose |
|------|---------|
| `lib/features/pdf/services/table_extraction/table_extractor.dart` | Pipeline orchestrator |
| `lib/features/pdf/services/table_extraction/row_classifier.dart` | Row classification (Phase 1A) |
| `lib/features/pdf/services/table_extraction/table_region_detector.dart` | Region detection |
| `lib/features/pdf/services/table_extraction/column_detector.dart` | Column detection |
| `lib/features/pdf/services/table_extraction/cell_extractor.dart` | Cell extraction |
| `lib/features/pdf/services/table_extraction/table_row_parser.dart` | Row parsing |
| `lib/features/pdf/services/table_extraction/post_process/` | Post-processing directory |

### Legacy Parsers (Reference)
| File | Purpose |
|------|---------|
| `lib/features/pdf/services/parsers/column_layout_parser.dart` | Already uses Syncfusion TextWord with bounds |
| `lib/features/pdf/services/parsers/clumped_text_parser.dart` | Handles clumped column text |

### Thresholds & Constants
| File | Key Constants |
|------|--------------|
| `row_classifier.dart` lines 79-82 | `kMinDataElements=3`, `kMaxDataElements=8` |
| `row_classifier.dart` line 17 | Item number regex: `^\d+(\.\d+)?\.?$` |
| `table_region_detector.dart` line 31 | `kMinDataRowsAfterHeader=2` |
| `table_region_detector.dart` line 37 | `kMaxDataRowLookahead=5` |
| `pdf_import_service.dart` | `kMinCharsPerPage=50`, `kMaxSingleCharRatio=0.30` |

### Native Code
| File | Purpose |
|------|---------|
| `packages/flusseract/src/flusseract.cpp` | C++ Tesseract bridge, OEM_LSTM_ONLY (line 52), resolution handling (lines 90-97) |
| `packages/flusseract/lib/tesseract.dart` | FFI wrapper, PSM enum, variable setters |
| `packages/flusseract/lib/pix_image.dart` | PixImage creation from bytes |

### Test PDF
| File | Purpose |
|------|---------|
| `Pre-devolopment and brainstorming/Screenshot examples/Companies IDR Templates and examples/Pay items and M&P/864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf` | Primary test PDF (6 pages, 1.1MB, ~130 bid items) |

### Session Logs (For Reference)
| Path | Content |
|------|---------|
| `Troubleshooting/Detailed App Wide Logs/session_2026-02-06_16-27-27/pdf_import.log` | Latest extraction run (23 items, most recent) |
| `Troubleshooting/Detailed App Wide Logs/session_2026-02-06_10-33-13/pdf_import.log` | Earlier run with old preprocessing (71 items, garbage) |
| `Troubleshooting/Detailed App Wide Logs/session_2026-02-06_16-06-23/pdf_import.log` | Worst run (3 items) |

### Existing Plans (Context)
| File | Purpose |
|------|---------|
| `.claude/plans/pdf-table-structure-analyzer-v2.md` | Original v2 plan with all 14 design decisions |
| `.claude/plans/2026-02-06-fix-extraction-regression-row-classifier-gate.md` | Numeric gate fix plan |
| `.claude/backlogged-plans/OCR-Fallback-Implementation-Plan.md` | Original OCR plan from Session 226 - confirmed PDFs are NOT scanned |
| `.codex/plans/2026-02-06-pdf-table-structure-analyzer-v2-implementation-plan.md` | Codex implementation plan |

### Spike/Testing Tools
| File | Purpose |
|------|---------|
| `tooling/pdf_textline_spike.dart` | CLI tool to inspect Syncfusion TextLine output with bounds |

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

### Uncommitted Changes
```
M lib/features/pdf/services/table_extraction/row_classifier.dart     (numeric gate removal)
M test/features/pdf/table_extraction/row_classifier_test.dart        (updated test expectations)
```

These uncommitted changes convert the numeric content hard gate to a confidence modifier. They should be committed before starting this work.

---

## Open Questions for Next Session

1. **Coordinate transformation**: What exact DPI does Syncfusion use for TextWord bounds? Is it PDF points (72 DPI)? Need to verify with the spike tool and compare to OCR element coordinates.

2. **Page images for column detection**: The line-based column detector needs page images to scan for vertical lines. When using native text extraction, we still need to render page images for this purpose (or find an alternative column detection method).

3. **Mixed page handling**: What if some pages have native text and others don't? Per-page routing vs whole-document routing?

4. **Commit the numeric gate changes first?**: The uncommitted row_classifier changes should probably be committed before starting this work, since they're a valid improvement regardless of extraction method.

5. **Run the spike tool first**: Before writing any code, verify what Syncfusion returns for the Springfield PDF using the existing spike tool. This takes 10 minutes and validates the entire approach.

---

## Success Criteria

- Springfield PDF: 100+ items extracted (currently 23 at best, should have ~130)
- Item numbers: Actual numbers, not OCR garbage ("nN", "©", "il")
- All 6 pages processed (currently only pages 4-5)
- Pipeline automatically routes to native text for digital PDFs
- Pipeline falls back to OCR for scanned PDFs
- OCR fallback produces better results than current (confidence filtering + PSM tuning)

# PDF Font Encoding Corruption Investigation

## Date: 2026-02-06
## Status: IMPLEMENTATION READY — Per-page OCR fallback needed
## Updated: Session 307

---

## Problem Statement

The Springfield PDF (`864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf`) has font encoding corruption across MULTIPLE pages (not just page 6 as originally thought). Native text extraction produces garbled characters.

## Root Cause: TWO Separate Issues

### Issue 1: Character Reversal (FIXED)
- Page 6 (index 5) stores text in reverse character order
- Fix applied: Two-stage detection in `native_text_extractor.dart`
  - Stage 1: Keyword matching (for pages with headers)
  - Stage 2: Pattern-based fallback (for pages without headers)
- **Status**: WORKING

### Issue 2: Font Encoding / CMap Corruption (UNFIXED)
- Syncfusion v32.1.25 has **NO API** to control font encoding / CMap handling
- Known Syncfusion bug: GitHub issues #775, #810, #1444, #1665
- The library abstracts font decoding internally — no workaround via configuration
- **OCR fallback is the only viable solution**

## Diagnostic Results (Session 307)

### Per-Page Corruption Scores
Diagnostic logging added to `native_text_extractor.dart` — `_analyzeEncodingCorruption()` scores each page.

| Page | Score | Verdict | Apostrophes | Letters in $ | Total $ Amounts |
|------|-------|---------|-------------|-------------|-----------------|
| 1 | 4 | POSSIBLY_CORRUPTED | 0 | 2 | 6 |
| 2 | **8** | **LIKELY_CORRUPTED** | 0 | 4 | 30 |
| 3 | **12** | **LIKELY_CORRUPTED** | 0 | 6 | 22 |
| 4 | **11** | **LIKELY_CORRUPTED** | 1 | 4 | 26 |
| 5 | 2 | CLEAN | 0 | 1 | 21 |
| 6 | **91** | **LIKELY_CORRUPTED** | 13 | 26 | 23 |

### TWO Different Corruption Types

**Pages 1-4: MILD to MODERATE**
- Headers mostly readable: "Item", "No.", "Description", "Unit" appear correct
- Specific character substitutions in item numbers: I↔1, o↔0, l↔1, J↔digit, '↔digit
- Examples: `sEcTroN` (SECTION), `BIODER` (BIDDER), `J5` (35), `Jb` (36), `'13` (13)
- Dollar amounts: 13-33% have letters mixed in
- ~40-50% of "invalid items" are FALSE POSITIVES from construction terms (Tee, Cap, Cross)

**Page 6: CATASTROPHIC**
- Headers completely garbled: `llaus:`, `8!p`, `duca`, `nul` (should be Item, No., Description, Unit)
- ALL text garbled after reversal: `$z'882'629'ze` (should be `$7,882,926.73`)
- Character substitution map: 7→z, 3→e, 9↔6, ','→`'`, '.'→`'`
- 100% corruption — no usable data

### Raw Element Samples (After Reversal)

**Page 1**: `["ADDENDUM","#","I","sEcTroN","00","41","00","BID","FORM","ARTICLE","1",".","OWNER","&","BIODER"]`
**Page 2**: `["ADDENDUM","i","I","Item","No.","Description","Unit","Est.","Quantity","Unit","Price","Bid","Amount","6","Erosion"]`
**Page 5**: `["Item","No.","Description","Unit","Est.","Quantity","Unit","Price","Bid","Amount","87","Water","Service,"]` (CLEAN)
**Page 6**: `["$z'882'629'ze","llaus:","8!p","duca","nul","vll","ol","lolEl","00","sz'aso","00","$2E0","tI","]V","SIUL"]`

### Extraction Results
- 133 items extracted → 114 after dedup
- 23 invalid item numbers (17.3%)
- 57.8% success rate
- Page 6 alone contributes ~19 completely garbled items

## Log Files

| Session | File | Key Data |
|---------|------|----------|
| `session_2026-02-06_21-46-50` | `pdf_import.log` | Full diagnostic output with BEFORE/AFTER reversal + corruption scores |
| `session_2026-02-06_20-42-19` | `pdf_import.log` | Pre-diagnostic run (no corruption scores) |

## Key Files

| File | Role | Changes This Session |
|------|------|---------------------|
| `native_text_extractor.dart` | Native text + reversal + diagnostics | Added `_logRawElements()`, `_analyzeEncodingCorruption()` |
| `pdf_import_service.dart` | Orchestrator — native vs OCR | **NEEDS CHANGE**: per-page routing |
| `tesseract_ocr_engine.dart` | OCR engine | No changes needed |

## Syncfusion Research (Completed)

- **Version**: syncfusion_flutter_pdf v32.1.25
- `PdfTextExtractor.extractTextLines()` — NO encoding parameters, only `startPageIndex` + `endPageIndex`
- `PdfTextExtractor.extractText()` — same limitation
- `PdfTextExtractor.findText()` — same limitation
- **No CMap, ToUnicode, or font encoding config exposed in public API**
- GitHub confirms this is a known limitation

## Implementation Plan: Per-Page OCR Fallback

### Design Doc
`.claude/agent-memory/pdf-agent/per-page-quality-gate-design.md`

### Architecture (Option D from original plan)

```
Current flow (all-or-nothing):
  extractRawText() → needsOcr() → ALL native or ALL OCR

New flow (per-page routing):
  extractRawText() → needsOcr()
    → If OCR needed: full OCR (no change)
    → If native viable:
        1. NativeTextExtractor.extractFromDocument() → elementsPerPage + corruptionScores
        2. For each page: if corruptionScore > threshold → mark for OCR
        3. OCR only marked pages (render → preprocess → Tesseract)
        4. Merge: native elements for good pages, OCR elements for bad pages
        5. Pass merged list to TableExtractor (no changes needed)
```

### Threshold
Based on diagnostic data:
- Page 5 (CLEAN): score = 2
- Pages 2-4 (MILD-MODERATE): scores = 8-12
- Page 6 (CATASTROPHIC): score = 91
- **Recommended threshold: score > 5** (catches pages 2-4 and 6)
- Alternative: **score > 15** (only catches page 6, leaves mild corruption to character mapping)

### Changes Required

**1. `native_text_extractor.dart`** — expose corruption scores
- Make `_analyzeEncodingCorruption()` return scores in extractFromDocument result
- Add `NativeTextExtractionResult` record type with `elementsPerPage` + `corruptionScores`

**2. `pdf_import_service.dart`** — per-page routing
- After native extraction, check corruption scores
- New method: `_ocrCorruptedPages(document, pagesNeedingOcr, nativeElementsPerPage)`
  - For each corrupted page: render → preprocess → Tesseract OCR
  - Returns merged elementsPerPage list
- Modify `importBidSchedule()` native text path (~lines 716-830)

**3. No changes to TableExtractor** — already accepts per-page element lists

### Tests
- 816 existing tests pass (614 table + 202 OCR)
- New tests needed for quality gate scoring
- Integration test with Springfield PDF fixture

## PDF File Location
`Pre-devolopment and brainstorming/Screenshot examples/Companies IDR Templates and examples/Pay items and M&P/864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf`

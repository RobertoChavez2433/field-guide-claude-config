# OCR-First PDF Import Restructuring Plan (v2)

**Date**: 2026-02-02  
**Status**: READY FOR IMPLEMENTATION  
**Methodology**: Test-Driven Development (Red-Green-Refactor)  
**Scope**: Restructure PDF import to be OCR-first with OCR-specific row reconstruction, guarded DPI, and improved diagnostics.

---

## Evidence & Context (What We Verified)

### Live device logs (Android, 2026-02-02 16:13:43)
We captured fresh logcat after a failing import on device (SM_S938U). Key evidence:
- Column parser cannot detect header clusters (max clusters: 1).  
- Only 13 lines extracted from a multi-page bid schedule.  
- Regex fallback parses 0 items; lines look like single-block clumped text.

Sample logs (timestamped):
- `[ColumnParser] Header search stopped after 3 pages`  
- `[ColumnParser] All clustering attempts failed (max clusters: 1)`  
- `[PDF Import] Parsing 13 lines from bid schedule`  
- `[PDF Import] Parsing complete: 0 items found`

This confirms the current extraction is producing **single-block text**, not row-structured lines, which is exactly why parsing fails.

---

## Executive Summary

The current parsing failures are driven by clumped, single-block text output. OCR-first is valid, but OCR output must be **reconstructed into rows/columns** before any parsing can succeed. This plan keeps all requirements from v1 (200 DPI, deskew, 25-page warning, Syncfusion fallback, TDD, fixtures) and adds missing OCR row reconstruction plus guardrails for DPI and memory.

### Key Changes (v2 additions)
1. **OCR Row Reconstruction**: Convert ML Kit blocks/lines into structured rows/columns before parsing.
2. **Guarded 200 DPI**: DPI stays 200 by default, but downscales based on pixel/memory budget and device RAM.
3. **Explicit OCR Diagnostics**: Log OCR start/end, page count, time per page, confidence, and reconstruction metrics.
4. **Parser Routing**: OCR output bypasses column parser and uses OCR-specific row parser.

---

## Success Criteria (Unchanged + v2 additions)
- [ ] All PDFs (scanned or digital) can go through OCR pipeline (v1)
- [ ] Deskewing and rotation detection improve accuracy on angled scans (v1)
- [ ] 200 DPI produces better results than 150 DPI (validate with tests) (v1)
- [ ] PDFs > 25 pages show warning but still process (v1)
- [ ] OCR + parsing pipeline produces ≥80% field accuracy on test fixtures (v1)
- [ ] All tests written BEFORE implementation (TDD) (v1)
- [ ] OCR row reconstruction produces row-aligned text for parsing (v2)
- [ ] OCR diagnostics show per-page confidence + reconstruction stats (v2)

---

## Architecture: OCR-First Pipeline (v2)

### Current Flow (Observed)
```
PDF → Extract Text (Syncfusion) → Column Parser → Regex
                                     ↓
                               Clumped single-block text
                                     ↓
                                0 items parsed
```

### New Flow (v2 OCR-first)
```
PDF → Check page count → Render pages to images (200 DPI, guarded)
          ↓                           ↓
      Warn if > 25         IMAGE PREPROCESSING
                           (grayscale, contrast, deskew,
                            rotation detect, binarize, denoise)
                                      ↓
                              ML KIT OCR (per page)
                                      ↓
                         OCR ROW RECONSTRUCTION (NEW)
                      (blocks/lines → rows/columns)
                                      ↓
                          TEXT PREPROCESSING
                        (OcrPreprocessor: s→$, spacing)
                                      ↓
                        OCR Row Parser (NEW) → Parsed items
                                      ↓
                             Quality Check & Warnings
                                      ↓
                       FALLBACK: Syncfusion Text Extract
                     (only if OCR row parse fails badly)
                                      ↓
                           Column/Regex parser cascade
```

---

## Guardrails for 200 DPI (Required)

We keep 200 DPI as default but protect against memory/time blowups.

### Guardrail Rules
1. **Pixel Budget**:  
   - Estimate page pixels = width * height (after DPI scaling).  
   - If pixels > 12 million, downscale to keep <= 12M.
2. **Memory Budget**:  
   - Raw BGRA = pixels * 4.  
   - If estimated raw image > 64MB, reduce DPI.
3. **Device RAM Heuristic** (use `device_info_plus`):  
   - If total RAM < 6GB, default to 150 DPI unless user opts in.
4. **Time Budget**:  
   - If OCR page > 8s, reduce DPI for remaining pages.
5. **Page Count Guard**:  
   - If > 25 pages, warn and auto-reduce DPI to 150 unless user confirms.

### Implementation Targets
- `lib/features/pdf/services/ocr/pdf_page_renderer.dart`  
  Add `renderPageWithGuardrails()` to compute DPI dynamically.
- `lib/features/pdf/services/pdf_import_service.dart`  
  Use guarded DPI strategy for all OCR renders.

---

## OCR Row Reconstruction (Core Fix)

### Problem
OCR output arrives as a **single block of text**. The parsers expect rows/columns. We must rebuild rows using bounding boxes.

### Proposed Solution
Add a new service that converts ML Kit `TextBlock → TextLine → TextElement` into structured rows:

**New file**: `lib/features/pdf/services/ocr/ocr_row_reconstructor.dart`

**Algorithm (high-level)**
1. Collect all OCR lines with bounding boxes.
2. Sort by Y-center.
3. Group into rows using a Y-threshold (e.g., 0.5× median line height).
4. Within each row, sort by X.
5. Detect columns by clustering X positions (item number, description, unit, qty, price).
6. Emit normalized row objects:
   ```
   OcrRow {
     itemNumber, description, unit, quantity, unitPrice, rawText
   }
   ```
7. Feed `OcrRow` into OCR-specific parser (new).

**New file**: `lib/features/pdf/services/parsers/ocr_row_parser.dart`
This parser will:
- Accept `List<OcrRow>` rather than raw text.
- Apply regex parsing per row.
- Fall back to clumped parsing only if row detection fails.

---

## TDD Approach (Same as v1, with OCR Row tests)

### Test Fixtures Required (unchanged)
- `test/assets/pdfs/digital_bid_schedule.pdf`
- `test/assets/pdfs/scanned_straight.pdf`
- `test/assets/pdfs/scanned_rotated_5deg.pdf`
- `test/assets/pdfs/scanned_faded.pdf`
- `test/assets/pdfs/scanned_noisy.pdf`
- `test/assets/pdfs/30_pages.pdf`
- `test/assets/pdfs/mixed_quality.pdf`

### New OCR Row Fixtures
Add OCR JSON dumps from ML Kit output for unit testing:
- `test/assets/ocr/blocks_simple.json`
- `test/assets/ocr/blocks_clumped.json`
- `test/assets/ocr/blocks_rotated.json`

---

## Implementation Phases (PR-sized)

### PR #1 — OCR Diagnostics + Log Evidence
**Goal**: Capture OCR and parser pipeline signals clearly.  
**Why**: We need definitive visibility into OCR path and reconstruction metrics.

Files:
- `lib/features/pdf/services/pdf_import_service.dart`  
  Add logs: OCR start/end, page count, DPI used, duration, fallback used.
- `lib/features/pdf/services/parsers/parser_diagnostics.dart`  
  Add OCR reconstruction stats to diagnostics metadata.

### PR #2 — Guarded 200 DPI Rendering
**Goal**: Keep 200 DPI but guard against memory/time blowups.

Files:
- `lib/features/pdf/services/ocr/pdf_page_renderer.dart`
- `lib/features/pdf/services/pdf_import_service.dart`

### PR #3 — OCR Row Reconstruction (Core Fix)
**Goal**: Convert OCR blocks into structured rows.

Files:
- `lib/features/pdf/services/ocr/ocr_row_reconstructor.dart` (new)
- `lib/features/pdf/services/ocr/ml_kit_ocr_service.dart`  
  Return blocks + confidence to reconstruction.

### PR #4 — OCR Row Parser
**Goal**: Parse rows directly instead of clumped text.

Files:
- `lib/features/pdf/services/parsers/ocr_row_parser.dart` (new)
- `lib/features/pdf/services/pdf_import_service.dart`  
  Use OCR row parser for OCR pipeline; keep column parser for Syncfusion text only.

### PR #5 — Image Preprocessing Enhancements
**Goal**: Deskew + rotation detection + contrast improvements. (unchanged v1)

Files:
- `lib/features/pdf/services/ocr/image_preprocessor.dart`

### PR #6 — Integration Tests + Fixtures
**Goal**: 7 PDF fixtures + OCR row fixtures, end-to-end validation. (unchanged v1)

Files:
- `test/features/pdf/integration/ocr_first_integration_test.dart`
- `test/assets/pdfs/*`
- `test/assets/ocr/*`

---

## Risk Mitigation (v1 preserved, with v2 additions)

### Risk 1: Deskewing too slow
**Mitigation**:
- Limit rotation detection to ±15°
- Use 1° increments
- Run on downscaled image only

### Risk 2: 200 DPI not sufficient
**Mitigation**:
- Test 250 and 300 DPI
- Add adaptive DPI: start 200, retry at 300 if confidence < 0.6

### Risk 3: OCR accuracy still poor
**Mitigation**:
- Collect problematic PDFs and tune preprocessing
- Add OCR row reconstruction (v2 fix)
- Add PaddleOCR as secondary engine (future)

### Risk 4: Breaking existing imports
**Mitigation**:
- Feature flag OCR-first
- Run full test suite per PR

### Risk 5: Memory blowups on large pages
**Mitigation**:
- DPI guardrails (v2)
- Hard cap on pixels per page
- One-page-at-a-time processing

---

## Verification Checklist (Preserved)

### Per-PR Verification
- [ ] All new tests pass (RED → GREEN achieved)
- [ ] All existing tests still pass
- [ ] `flutter analyze` reports 0 issues
- [ ] Documentation updated

### Final Acceptance
- [ ] All 7 test fixtures import successfully
- [ ] OCR confidence ≥ 0.7 for clean scans
- [ ] OCR confidence ≥ 0.5 for faded/rotated scans
- [ ] Text preprocessing fixes s→$, trailing s, spacing errors
- [ ] Deskewing handles ≤10° rotation accurately
- [ ] 200 DPI vs 150 DPI comparison documented
- [ ] 25+ page warning displays correctly
- [ ] Syncfusion fallback works when OCR fails
- [ ] OCR row reconstruction yields parseable rows
- [ ] Integration tests cover happy path + edge cases
- [ ] Performance targets met (< 30s for 5 pages)

---

## Performance Targets (Preserved)
- 5-page scanned PDF: < 30s
- 10-page digital PDF: < 45s
- 25-page mixed PDF: < 120s
- Memory peak (5 pages): < 200MB

---

## Future Enhancements (Preserved)

### Iteration 1: Adaptive DPI
If 200 DPI is insufficient:
- Test 250/300 DPI
- Retry at higher DPI when confidence low

### Iteration 2: Advanced Preprocessing
- Perspective correction
- Unsharp mask
- Morphological ops

### Iteration 3: Dual-Engine OCR
- Add PaddleOCR as secondary engine
- Compare vs ML Kit

### Iteration 4: Table Structure Detection
- Detect table grid lines
- Extract cells
- Handle merged cells

---

## Timeline (Preserved)
Assuming 1-2 days per PR:
- Week 1: PR #1-2
- Week 2: PR #3-4
- Week 3: PR #5-6

---

## Agent Assignments (Preserved)
| Phase | Primary | Supporting |
|-------|---------|------------|
| PR #1 | pdf-agent | qa-testing-agent |
| PR #2 | pdf-agent | qa-testing-agent |
| PR #3 | pdf-agent | code-review-agent |
| PR #4 | pdf-agent | code-review-agent |
| PR #5 | pdf-agent | flutter-specialist-agent |
| PR #6 | qa-testing-agent | pdf-agent |

---

**End of Plan (v2)**

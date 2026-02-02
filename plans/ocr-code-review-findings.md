# OCR Implementation Plan (PR-Sized, Comprehensive)

**Date**: 2026-02-02  
**Scope**: Complete Phase 1–2 implementation gaps, fix critical OCR pipeline issues, and apply DRY/KISS/YAGNI refactors based on codebase review.

---

## Executive Summary
Phases 1 and 2 are **partially implemented**. Core OCR services exist, and the pipeline is wired into `PdfImportService`, but **critical blockers** remain that prevent OCR from functioning (most notably, page rendering returns blank images). This plan completes missing functionality, eliminates duplication, and simplifies the OCR pipeline while keeping the scope tight and PR-sized.

---

## Key Findings (Mapped to Fixes)

### Critical Blockers
1) **PDF renderer returns blank images**  
   - `lib/features/pdf/services/ocr/pdf_page_renderer.dart` renders white placeholders.  
   - OCR will always return empty text for scanned PDFs.  
   - Must replace with real PDF page rendering.

2) **OCR confidence not populated**  
   - `ocrConfidence` exists in `PdfImportResult` but is never assigned.  
   - Should compute per-page confidence and aggregate.

3) **Text preprocessing after OCR not applied**  
   - The plan references OCR text preprocessing, but pipeline doesn’t run it.  
   - Must apply existing `OcrPreprocessor` (or text normalizer) to OCR output.

### DRY/KISS/YAGNI Opportunities
4) **Duplicate OCR detection logic**  
   - `needsOcr()` overlaps `_isLikelyScannedPdf()` in `PdfImportService`.  
   - Consolidate into a single method with named thresholds.

5) **Magic thresholds**  
   - Hard-coded values for chars/page, single-char ratio, block sizes.  
   - Extract to constants for clarity and tuning.

6) **Repeated document serialization**  
   - `PdfPageRenderer` serializes full document per page render.  
   - Refactor to pass bytes once for multi-page processing.

7) **Over-abstracted interfaces without usage**  
   - `recognizeWithConfidence` exists but unused.  
   - Keep only what is used (YAGNI), or wire it in properly.

---

## PR-Sized Phased Plan

### PR 1 — Fix PDF Page Rendering (Critical Path)
**Goal**: OCR receives real page images.

**Changes**
- Replace placeholder render implementation with real rendering:
  - Preferred: `pdf_render` package (cross-platform, renders to bitmap).
  - Alternative: platform channels (Android PdfRenderer, iOS CGPDFPage).
- Update `PdfPageRenderer` to:
  - Accept document bytes once.
  - Render by page index using actual bitmap output.
  - Return RGBA/BGRA byte format compatible with ML Kit.

**Files**
- `lib/features/pdf/services/ocr/pdf_page_renderer.dart`
- `pubspec.yaml` (add `pdf_render` if chosen)

**Validation**
- Test OCR on a scanned PDF and confirm non-empty OCR text.

---

### PR 2 — OCR Pipeline Completeness
**Goal**: OCR pipeline outputs usable text and confidence.

**Changes**
- Use `recognizeWithConfidence()` in `_runOcrPipeline`.
- Aggregate `ocrConfidence`:
  - Avg of page-level confidences (or weighted by text length).
- Apply OCR text preprocessing:
  - Call existing `OcrPreprocessor.preprocess(text)` on OCR output.

**Files**
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/pdf/services/ocr/ml_kit_ocr_service.dart` (if needed)
- `lib/features/pdf/services/parsers/ocr_preprocessor.dart`

**Validation**
- `PdfImportResult.ocrConfidence` non-null when OCR used.
- Text normalization reduces obvious OCR artifacts.

---

### PR 3 — DRY/KISS Refactors (Low Risk)
**Goal**: Reduce duplication and simplify OCR logic.

**Changes**
- Consolidate `needsOcr()` and `_isLikelyScannedPdf()` into a single helper.
- Extract thresholds into constants:
  - `minCharsPerPage`
  - `maxSingleCharRatio`
  - `imagePreprocessContrastThreshold`
- Remove unused methods or wire them in (YAGNI).

**Files**
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/pdf/services/ocr/image_preprocessor.dart`

---

### PR 4 — Diagnostics + Preview UX
**Goal**: Surface OCR metadata to UI and diagnostics.

**Changes**
- Log OCR confidence per page in diagnostics.
- Display `OCR processed` + confidence in preview header.
- Export OCR path in diagnostics metadata.

**Files**
- `lib/features/pdf/services/parsers/parser_diagnostics.dart`
- `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`

---

### PR 5 — Tests and Fixtures
**Goal**: Ensure regression protection.

**Changes**
- Add scanned PDF test fixture.
- Unit tests:
  - `_needsOcr()`/OCR detection
  - OCR pipeline returns non-empty text for scanned PDFs
  - Confidence aggregation works

**Files**
- `test/features/pdf/services/pdf_import_service_ocr_test.dart`
- `test/assets/scanned_bid_schedule.pdf`

---

## Out of Scope (Later Phases)
- Paddle OCR fallback
- Table structure extraction
- Adaptive DPI/low memory fallback
- Full OCR progress UI

---

## Acceptance Checklist
- [ ] Scanned PDFs produce OCR text (not blank).
- [ ] OCR confidence recorded and displayed.
- [ ] OCR text is normalized with `OcrPreprocessor`.
- [ ] No duplicated OCR detection logic.
- [ ] Tests cover OCR pipeline and detection logic.


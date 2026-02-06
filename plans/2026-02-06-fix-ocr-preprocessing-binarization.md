# Fix OCR Preprocessing: Remove Destructive Binarization

**Date**: 2026-02-06
**Status**: Pending approval
**Scope**: Image preprocessing pipeline for PDF table extraction

## Problem

The image preprocessing pipeline applies **adaptive thresholding (binarization)** to every PDF page image before OCR. This converts clean 300 DPI grayscale images (~1.7MB) into binary black-and-white images (~136KB), destroying **92% of image data**. The result:

- 3 of 6 column headers completely lost (OCR can't see them)
- Header "Item No." fragmented into "Bid" + "id"
- OCR confidence drops to 74.8% (should be 85%+)
- Tesseract produces hundreds of "Empty page!!" warnings
- Cascading downstream failures: bad column assignment, 64% unknown rows, garbage item numbers, post-processing amplification

## Root Cause

`image_preprocessor.dart` `_preprocessIsolate()` unconditionally applies:
1. Grayscale conversion (fine)
2. 30% contrast boost (fine)
3. Gaussian blur radius 1 (only needed for binarization)
4. **Adaptive threshold block size 11, c=5** (DESTRUCTIVE for clean images)

The adaptive thresholding was designed for noisy scans/photocopies. Clean PDF renders don't need it - and it actively destroys fine text (headers, small fonts).

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Fix strategy | Fix preprocessing first | Upstream root cause; fixing it may resolve the entire cascade |
| Binarization handling | Remove entirely | Primary use case is clean PDFs; phone-photo-PDF is a future concern |
| Gaussian blur | Remove (only needed for binarization prep) | Without thresholding, blur just softens clean text |
| Contrast boost | Keep | Harmless, can help with slightly faded PDFs |
| Configurability | Not now | KISS; add toggle later if phone-photo use case arises |

## Phase 1: Remove Binarization (This PR)

### Changes

**File 1: `lib/features/pdf/services/ocr/image_preprocessor.dart`**

1. `_preprocessIsolate()` (lines 152-177): Remove Gaussian blur (step 3) and adaptive thresholding (step 4). Keep grayscale + contrast boost.

2. `_preprocessFallbackIsolate()` (lines 201-229): Remove adaptive thresholding. Keep downscale + grayscale only.

3. `_preprocessWithEnhancementsIsolate()` (lines 715-781): Remove adaptive thresholding (step 5) and post-threshold denoise (step 6).

### What Stays Unchanged
- Rotation/skew detection
- Contrast analysis and adaptive contrast boost
- `preprocessPageImage` fallback chain in `pdf_import_service.dart`
- All downstream code (OCR engine, table extraction, post-processing)

### Expected Impact
- Preprocessing time: ~11s/page -> ~2-3s/page
- Image quality: 256 grayscale levels preserved (vs 2 levels binary)
- OCR accuracy: Dramatic improvement for headers and fine text
- Total extraction time (6 pages): ~2.5min -> ~1.5min

## Testing Strategy

### Automated Tests
1. `flutter test test/features/pdf/table_extraction/` - all existing tests pass
2. `flutter test test/features/pdf/services/ocr/` - all OCR tests pass
3. `springfield_integration_test.dart` specifically

### Manual Verification (rebuild + extract Springfield PDF)

| Metric | Baseline (broken) | Target |
|--------|-------------------|--------|
| OCR confidence | 74.8% | >85% |
| Header elements found | 4 (2 matched) | 6 (5+ matched) |
| Rows classified "unknown" | 181/282 (64%) | <50/282 (<18%) |
| Rows classified "data" | 51/282 (18%) | >150/282 (>53%) |
| Items with valid item # | 49/71 (69%) | >90% |
| Post-processing repairs | 77 | <20 |
| Preprocessing time/page | ~11s | <4s |
| Image output size | 136KB | >400KB |

### Spot Checks
- Item numbers are real (1, 2, 3...) not garbage ("Ww 9 |W", "oO")
- Units are recognizable (EA, LS, CY, FT) not garbage ("UNITEAEALSUM...")
- Descriptions are readable English, not OCR artifacts

## Phase 2: Strengthen Row Classifier (if needed after Phase 1)

Only pursue if Phase 1 doesn't sufficiently fix the cascade.

**Approach**: Column-alignment scoring + numeric content gate
- Score rows by how well elements align to detected column positions
- Require at least one numeric value in quantity/price/amount columns for a row to be classified as "data"
- Stop parsing "unknown" rows as bid items by default

## Phase 3: Post-Processing Safeguards (if needed after Phase 1+2)

Only pursue if post-processing still damages data.

**Approach**: Input validation before each post-processing step
- Validate item numbers before splitting
- Don't infer values from wrong fields (only use rawBidAmount for bidAmount)
- Validate units are in known unit list before accepting
- Add confidence thresholds to deduplication

## Agent Assignments

| Phase | Agent | Task |
|-------|-------|------|
| Phase 1 | pdf-agent | Remove binarization from preprocessing |
| Phase 1 | qa-testing-agent | Run tests + manual verification |
| Phase 2 | pdf-agent | Strengthen row classifier |
| Phase 3 | pdf-agent | Add post-processing safeguards |

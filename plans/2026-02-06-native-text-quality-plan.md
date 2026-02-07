# Native Text Extraction Quality Plan

**Date**: 2026-02-06
**Status**: APPROVED
**Context**: Fix encoding corruption in native PDF text extraction (Springfield PDF)

---

## Problem Summary

The Springfield PDF has font encoding corruption:
- **Pages 1-4**: Mild corruption — character substitutions in item numbers (J→3, b→6, leading apostrophe)
- **Page 5**: Clean (score 2)
- **Page 6**: Catastrophic — 100% garbled text, possibly intentional bid protection

Current extraction: ~96% accuracy on pages 1-5 (~4 invalid item numbers), 0% on page 6.

### Investigation Findings (Session 307-308)
- All three known pipeline bugs (substring matching, else-if chain, element thresholds) are ALREADY FIXED
- Corruption scoring heuristic is accurate — not producing false positives from construction terms
- The `\$[^\s]{2,}` regex correctly requires dollar sign prefix; construction terms (Tee, Cap, Cross) are never captured
- Syncfusion has no CMap/encoding API — confirmed dead end

---

## Phase 1: Shore Up Pages 1-5 (PR 1)

**Goal**: Push pages 1-5 from ~96% to near-100% item number accuracy without OCR.

### Approach: Conditional Chaining Normalizer

Encoding-specific character mappings are applied conditionally:
1. **Pass 1 (safe)**: Apply low-risk mappings (J→3, strip leading apostrophe)
2. **Canary check**: If any encoding-specific mapping fired in Pass 1...
3. **Pass 2 (aggressive)**: Apply higher-risk mappings (b→6) that would be dangerous on clean text

This protects legitimate sub-item numbers (4b, 1a, 12c) from corruption while still fixing encoding artifacts.

### Examples

| Input | Pass 1 | Canary? | Pass 2 | Result | Correct? |
|-------|--------|---------|--------|--------|----------|
| `J5` | J→3 → `35` | Yes | N/A (already valid) | `35` | Yes |
| `Jb` | J→3 → `3b` | Yes | b→6 → `36` | `36` | Yes |
| `'13` | strip ' → `13` | Yes | N/A | `13` | Yes |
| `4b` | no change | No | skipped | `4b` | Yes (protected) |
| `1a` | no change | No | skipped | `1a` | Yes (protected) |
| `O5` | O→0 → `05` | No (OCR, not encoding) | skipped | `05` | Yes |

### Changes Required

**1. `post_process_normalization.dart`** — New centralized method
- Add `normalizeItemNumberEncoding(String text)` static method
- Implements the two-pass conditional chaining logic
- Keeps existing O→0, I→1, l→1 OCR mappings intact (these are Pass 0, always applied)

**2. `row_classifier.dart:665-673`** — Update `_normalizeItemNumber()`
- Call centralized `PostProcessNormalization.normalizeItemNumberEncoding()` after existing OCR normalization

**3. `table_row_parser.dart:460-468`** — Same update
- Call centralized method after existing OCR normalization

**4. `native_text_extractor.dart`** — Diagnostic cleanup
- Keep `_analyzeEncodingCorruption()` (needed for Phase 2)
- Keep `_fixReversedText()` (production code)
- Gate `_logRawElements()` behind diagnostic flag or remove (noisy in production)

**5. `post_process_normalization_test.dart`** — New test cases
- Test all examples from the table above
- Verify existing O→0, I→1 tests still pass
- Test edge cases: empty string, pure digits, mixed legitimate suffixes

### Files Touched
| File | Change |
|------|--------|
| `lib/features/pdf/services/table_extraction/post_process/post_process_normalization.dart` | New method |
| `lib/features/pdf/services/table_extraction/row_classifier.dart` | Call centralized method |
| `lib/features/pdf/services/table_extraction/table_row_parser.dart` | Call centralized method |
| `lib/features/pdf/services/text_extraction/native_text_extractor.dart` | Diagnostic cleanup |
| `test/features/pdf/table_extraction/post_process/post_process_normalization_test.dart` | New tests |

---

## Phase 2: Per-Page OCR Fallback for Page 6 (PR 2)

**Goal**: OCR only catastrophically corrupted pages (score > 15) while keeping good pages on fast native text path.

### Approach

1. Expose corruption scores from `NativeTextExtractor.extractFromDocument()`
2. After native extraction, check per-page corruption scores
3. Pages with score > 15: render → preprocess → Tesseract OCR
4. Merge native elements (good pages) + OCR elements (bad pages)
5. Pass merged list to TableExtractor (no changes needed — already source-agnostic)

### Changes Required

**1. `native_text_extractor.dart`** — Expose corruption scores
- Change `extractFromDocument()` to return a record: `({List<List<OcrElement>> elementsPerPage, List<int> corruptionScores})`
- Promote `_analyzeEncodingCorruption()` from diagnostic to production

**2. `pdf_import_service.dart`** — Per-page routing
- After native extraction, check corruption scores
- New method: `_ocrCorruptedPages()` — renders + OCRs only bad pages
- Merge native + OCR elements per page
- Modify `importBidSchedule()` native text path (~lines 716-830)

**3. No changes to TableExtractor** — already accepts `List<List<OcrElement>>` regardless of source

### Threshold: Score > 15 (Conservative)
- Page 5 (CLEAN): score 2 — native text
- Pages 2-4 (MILD): scores 8-12 — native text (handled by Phase 1 normalizer)
- Page 6 (CATASTROPHIC): score 91 — OCR fallback

### Edge Cases
- All pages fail quality check → fall back to full OCR pipeline
- Non-table pages (cover, notes) → low corruption score, stay native

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Corruption threshold | > 15 (conservative) | Only OCR catastrophic pages; mild corruption handled by normalizer |
| b→6 mapping | Conditional (canary-gated) | Protects legitimate sub-items (4b, 1a) from corruption |
| Page 6 approach | OCR (not character repair) | Character repair only fixes ~40% of columns; descriptions stay garbled |
| Normalizer location | Centralized in PostProcessNormalization | Avoids duplicating conditional chaining logic in 2 files |
| Diagnostic code | Gate behind flag, keep for Phase 2 | Corruption scoring is needed for Phase 2 routing |

---

## References

- Investigation log: `.claude/logs/page6-encoding-investigation.md`
- Design doc (Phase 2 detail): `.claude/agent-memory/pdf-agent/per-page-quality-gate-design.md`
- Session state: `.claude/autoload/_state.md`

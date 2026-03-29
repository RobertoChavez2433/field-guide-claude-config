# Springfield 100% Accuracy — Implementation Spec

**Created**: 2026-03-09 | **Status**: Approved (research-derived)
**Research**: `.claude/plans/2026-03-09-100pct-accuracy-research.md`

## Goal

Raise Springfield PDF extraction from 97 OK / 34 failures to ~129-131 OK / 0-2 failures across 131 ground truth items. Five fixes (R1-R5), ordered by impact and dependency.

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| GT Matched | 129/131 | 131/131 |
| Unit Accuracy | 79.8% (103/129) | 100% (131/131) |
| Description Accuracy | 94.6% (122/129) | ~98%+ (128+/131) |
| bidAmount Accuracy | 99.2% (128/129) | 100% (131/131) |
| Bogus Items | 1 ("94 Boy") | 0 |
| Dollar Delta | $280,158 | ~$0 |
| Quality Score | 0.918 | 0.99+ |

## Fix R1: Stop Unit Normalization (26 items)

**Problem**: `UnitRegistry.normalize()` maps long forms to short forms (LSUM->LS, SYD->SY, etc.). OCR correctly reads long forms. GT expects long forms.

**Fix**: Make `normalize()` cleanup-only (accent stripping, no alias remapping). Add `isLumpSum()` helper. Update 5 hardcoded `== 'LS'` checks.

**Files**:
- `lib/features/pdf/services/extraction/shared/unit_registry.dart` — remove alias remapping from normalize(), add isLumpSum()
- `lib/features/pdf/services/extraction/stages/row_parser_v3.dart:179` — normalize call (keep for cleanup)
- `lib/features/pdf/services/extraction/stages/row_parser_v3.dart:207` — LS check -> isLumpSum()
- `lib/features/pdf/services/extraction/stages/row_parser_v3.dart:247` — LS check -> isLumpSum()
- `lib/features/pdf/services/extraction/shared/post_process_utils.dart:305` — LS check -> isLumpSum()
- `lib/features/pdf/services/extraction/stages/consistency_checker.dart:72` — LS check -> isLumpSum()
- `lib/features/pdf/services/extraction/stages/post_processor_v2.dart:724` — LS check -> isLumpSum()
- `lib/features/pdf/services/extraction/stages/value_normalizer.dart:42-57` — uses PostProcessUtils.normalizeUnit() which chains to normalize()

**Risk**: LOW. knownUnits already contains both long and short forms.

---

## Fix R2: Fix Row Classifier for Items 94/95 (2 MISS + 1 BOGUS)

**Problem**: OCR reads "95" as "Boy" (conf 0.49). Row classifier's `_isMinorTextContent()` checks if item-number-column text matches numeric pattern. "Boy" doesn't match, so returns TRUE (minor), allowing priceContinuation classification. Merger blindly attaches to item 94. Result: "94 Boy" garbled item, items 94+95 both lost.

**Fix (two parts)**:

### R2a: Classifier fix
Modify `_isMinorTextContent()` to return FALSE when ANY text exists in the item-number column (not just numeric matches). An element in the item-number column is a structural signal regardless of content.

**File**: `lib/features/pdf/services/extraction/stages/row_classifier_v3.dart:327-334`

### R2b: Merger grid-line guard (defense-in-depth)
Pass horizontal grid line positions to `row_merger.dart`. Refuse to merge continuation rows that cross a grid line boundary relative to the base data row.

**Files**:
- `lib/features/pdf/services/extraction/stages/row_merger.dart` — add grid line parameter, add boundary check
- `lib/features/pdf/services/extraction/stages/row_classifier_v3.dart` — pass grid lines through classification result
- Pipeline wiring to pass grid line data to merger

### R2c: Downstream rescue
After preventing the bogus merge, rows 213+214 need to be recognized as item 95. Row 214 (with "Boy" + prices) should fall through to a new classification: if a row has item-number-column content + price columns, treat as data with reduced confidence.

**Risk**: MODERATE. Affects all row classification globally. Must verify no other legitimate priceContinuation rows are disrupted. (Agent 1 confirmed only row 214 in Springfield has this pattern.)

---

## Fix R3: Item Number Validation Gate (defense-in-depth)

**Problem**: `row_parser_v3.dart:196-198` adds warning for invalid item numbers but continues outputting the item.

**Fix**: Convert warning to `continue` (skip item) — but ONLY after R2 ensures no data loss. This is a safety net.

**File**: `lib/features/pdf/services/extraction/stages/row_parser_v3.dart:196-198`

**Risk**: LOW (after R2). Must use `ExtractionPatterns.itemNumberLoose` pattern for broader matching.

---

## Fix R4: bidAmount Backsolve Correction (1 item)

**Problem**: Item 96 OCR reads `$177.133.00` (european periods). Parser gets 177133. GT is 177135. Digit '5' misread as '3'. Consistency checker only backsvolves unitPrice, never bidAmount.

**Fix**: Add bidAmount correction branch in `consistency_checker.dart:128` (else branch after unitPrice backsolve fails). Gate on: (1) relative error < 0.5%, (2) rawBidAmount matches european_periods regex.

**File**: `lib/features/pdf/services/extraction/stages/consistency_checker.dart:128`

**Gating**: `rawBidAmount` matches `^\$?\d{1,3}(\.\d{3})+\.\d{2}$`. No model changes needed — re-detect pattern from raw string.

**Risk**: LOW. Only item 96 triggers in Springfield. Zero false positives confirmed.

---

## Fix R5: Position-Based Grid Line Removal (5-8 description items)

**Problem**: Current `GridLineRemover` uses morphological operations (adaptive threshold + morph open + dilate + inpaint) to re-detect grid lines from scratch. This creates a damage zone of ~3-5px beyond each grid line that corrupts adjacent text. Items 121, 123, 125, 130 have leading characters destroyed ("Pavt"->"pavt"/"Dav"/"i"). Items 123, 125, 130 have trailing words ("Yellow"/"White"/"Sym") undetected by OCR despite being visible in cell crops — bottom-edge degradation from grid line inpainting.

**Root cause (verified by diagnostic images)**:
- The trailing words ARE present in both raw and OCR cell crops — Tesseract fails to detect them
- The leading characters are damaged at grid line intersections where horizontal + vertical masks overlap
- The morphological approach re-detects lines redundantly — `GridLineDetector` already provides exact line positions and widths

**Fix**: Replace morphological mask-building in `grid_line_remover.dart` with position-based masking using the already-computed grid line positions and widths from `GridLineDetector`.

**New algorithm**:
1. Receive `GridLineResult` (line positions + widths) as input
2. Create blank mask (same size as page image)
3. For each horizontal line: draw filled rectangle at `(0, center - width/2)` to `(pageWidth, center + width/2)`
4. For each vertical line: draw filled rectangle at `(center - width/2, 0)` to `(center + width/2, pageHeight)`
5. Optional: 1px directional dilation along line direction only (NOT perpendicular)
6. Inpaint with reduced radius (1.0-1.5 instead of 2.0)

**Key changes**:
- **Remove**: adaptive threshold, morphological open, 3x3 dilation (lines 215-251)
- **Add**: position-based mask drawing from GridLineResult data
- **Modify**: pipeline wiring to pass GridLineResult to remover (currently only passes hasGrid boolean)
- **Reduce**: inpaint radius from 2.0 to 1.0-1.5
- **Keep**: grayscale conversion, inpainting step, diagnostic image output

**Files**:
- `lib/features/pdf/services/extraction/stages/grid_line_remover.dart` — replace mask-building
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` — pass GridLineResult to remover
- `test/features/pdf/extraction/stages/grid_line_remover_test.dart` — update tests for new approach
- Fixture regeneration (all springfield_*.json files)

**Risk**: MODERATE. Must verify grid lines are still fully removed. Must verify no regressions in OCR quality. Mask coverage should decrease slightly from 5.3% (morphological overshoot eliminated).

---

## Implementation Order

1. **R1** (unit normalization) — independent, safe, 26 items fixed
2. **R2** (classifier + merger guard) — highest dollar impact ($280K), prerequisite for R3
3. **R3** (validation gate) — defense-in-depth after R2
4. **R4** (bidAmount backsolve) — independent, 1 item fixed
5. **R5** (position-based grid line removal) — largest code change, fixes description items

R1 and R4 are independent and can be implemented in parallel.
R2 must precede R3.
R5 is independent of R1-R4.

## Fixture Regeneration

After ALL fixes: regenerate all Springfield fixtures, update golden test baselines, verify scorecard.

## Testing Strategy

- Unit tests for each modified function
- Golden test baseline update (springfield_golden_test.dart)
- GT trace verification (tools/gt_trace.dart)
- Full `flutter test` suite must pass

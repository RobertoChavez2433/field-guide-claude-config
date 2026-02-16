# Column Semantic Mapping Fix

**Created**: 2026-02-15
**Status**: DRAFT — awaiting approval
**Root cause**: Column detector + row parser mismap grid columns when header OCR fails

---

## Problem Summary

The extraction pipeline produces **0/131 ground truth matches** on Springfield because:

1. **Column detector (Layer 0)** creates 8 grid columns from 7 vertical lines (including 2 margin columns). Header band OCR only identifies 4 of 6 semantic columns (description, quantity, unitPrice, bidAmount). The `itemNumber` and `unit` columns get `null` header_text because OCR misreads their headers ("Nor" instead of "No.", "ou" instead of "Unit").

2. **Row parser `_mapColumnSemantics`** falls back to `standardOrder[i]` for null-header columns, which maps the left **margin** (Col 0, 0→5.3%) to `itemNumber` and the real item number column (Col 1) to `description`. Description then gets duplicated (Col 1 + Col 2), with Col 2 overwriting Col 1 in `cellMap`. Item numbers are completely lost.

### Evidence (from diagnostic tests)

| Grid Col | Width | Actual Content | Currently Mapped As | Should Be |
|----------|-------|----------------|--------------------:|-----------|
| 0 | 5.3% | `\|` pipes (margin) | `itemNumber` | MARGIN (skip) |
| 1 | 5.6% | `"2"`, `"3"`, `"5"` | `description` | `itemNumber` |
| 2 | 35.0% | Real descriptions | `description` | `description` |
| 3 | 8.6% | `"LSUM"`, `"EA"` | `quantity` | `unit` |
| 4 | 11.5% | Quantities | `quantity` | `quantity` |
| 5 | 13.9% | `$390,000.00` | `unitPrice` | `unitPrice` |
| 6 | 14.9% | `$390,000.00` | `bidAmount` | `bidAmount` |
| 7 | 5.3% | Empty (margin) | unmapped | MARGIN (skip) |

### Test files created during investigation

- `test/features/pdf/extraction/shared/crop_upscaler_test.dart` — 20 tests (all pass), confirms upscaler is NOT the bottleneck
- `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart` — 6 tests (all pass), confirms and documents the bugs

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Where does margin detection live? | Column Detector | Single source of truth. Row parser receives clean semantic map. |
| How to identify unrecognized columns? | Anchor-relative inference + 3-row content validation | Uses already-identified columns as context. Handles non-standard column orders. Content sampling catches misassignments. |
| Fix row parser too? | Yes — remove blind position fallback | Defense-in-depth. If column detector sends null-header columns, row parser should skip them, not guess. |

---

## Implementation Plan

### Phase 1: Column Detector Layer 0 — Margin Detection + Semantic Inference

**File**: `lib/features/pdf/services/extraction/stages/column_detector_v2.dart`
**Method**: `_detectFromGridLines` (line 363-482)

#### Step 1a: Add margin detection after grid columns are built

After building `columns` from vertical line boundaries (line 423-456), add a margin detection pass:

```
Margin detection rules:
- Column is at page edge: startX == 0.0 or endX == 1.0
- Column is narrow: width < kMarginWidthThreshold (6% of page = 0.06)
- Mark as `headerText: '_margin'` (sentinel value, not a semantic column)
```

New constant: `static const double kMarginWidthThreshold = 0.06;`

#### Step 1b: Add anchor-relative semantic inference

After margin detection + existing header OCR matching, for any remaining null-header columns:

```
Inference rules (using already-identified columns as anchors):
1. Find first column LEFT of 'description' that is not a margin → infer 'itemNumber'
2. Find first column BETWEEN 'description' and 'quantity' that is not a margin → infer 'unit'
3. If 'description' is unknown but one wide column (>25% width) exists → infer 'description'
```

#### Step 1c: Add 3-row content validation

For each inferred semantic, sample the first 3 non-empty cells from data rows in that column:

```
Validation patterns:
- 'itemNumber': 2/3 cells match ExtractionPatterns.itemNumber (^\d+[A-Za-z]?$)
- 'unit': 2/3 cells match UnitRegistry known units (EA, LSUM, SYD, LFT, etc.)
- If validation fails: revert to null (don't assign wrong semantic)
```

This requires access to data row elements at column detection time. The method already receives `extractionResult` which contains `elementsPerPage`. We can sample elements whose X-center falls within the column bounds.

#### Step 1d: Filter margin columns from output

Before returning the final column list, strip out `_margin` columns so downstream stages (cell extraction, row parser) never see them. The grid will produce 6 data columns instead of 8.

**IMPORTANT**: This affects cell extraction (Stage 4D) because it currently uses column indices that match the grid. If we remove margins from the ColumnMap, the cell extractor will create 6 cells per row instead of 8, which is correct.

However, the **text recognizer** (`text_recognizer_v2.dart:515-558`) creates cell regions from grid lines directly (including margins). Those margin crops still get OCR'd. This is wasteful but harmless — the cell extractor simply won't assign those elements to any column.

### Phase 2: Row Parser — Remove Blind Position Fallback

**File**: `lib/features/pdf/services/extraction/stages/row_parser_v2.dart`
**Method**: `_mapColumnSemantics` (line 400-418)

Replace the current logic:

```dart
// CURRENT (buggy):
} else if (i < HeaderKeywords.standardOrder.length) {
  semantics[i] = HeaderKeywords.standardOrder[i];
}
```

With:

```dart
// NEW: Skip columns with no semantic identity.
// Column detector is responsible for assigning all semantics.
// If a column has null headerText, it's intentionally unmapped
// (e.g., margin column, or genuinely unidentifiable).
// DO NOT fall back to position-based guessing.
```

Additionally, add a warning when expected semantics are missing:

```dart
// After building semantics map, check for missing required columns
const requiredSemantics = ['itemNumber', 'description'];
for (final required in requiredSemantics) {
  if (!semantics.values.contains(required)) {
    warnings.add('Missing required column: $required');
  }
}
```

### Phase 3: Testing

#### 3a: Unit tests for column detector margin detection

**File**: `test/features/pdf/extraction/stages/stage_4c_column_detector_test.dart` (existing, extend)

Tests to add:

1. **Margin detection with standard grid** — 8 columns from Springfield grid lines → 2 margins identified, 6 data columns remain
2. **Margin detection with no margins** — All columns > 6% width → no margins detected
3. **Margin detection with one-sided margin** — Only left edge has narrow column
4. **Margin detection threshold boundary** — Column at exactly 6% width → not a margin

#### 3b: Unit tests for anchor-relative semantic inference

Tests to add:

5. **Standard bid table inference** — description + quantity + unitPrice + bidAmount identified → itemNumber inferred left-of-description, unit inferred between description and quantity
6. **Missing description anchor** — Can't infer itemNumber or unit without description anchor → falls back gracefully
7. **Non-standard column order** — Description is NOT the second column → inference still works relative to anchors
8. **Extra unidentified columns** — More than 2 unidentified non-margin columns → only infer where confident

#### 3c: Unit tests for 3-row content validation

Tests to add:

9. **Item number validation passes** — Inferred itemNumber column has "1", "2", "3" in sample → validated
10. **Item number validation fails** — Inferred column has "LSUM", "EA", "SYD" → rejected, reverts to null
11. **Unit validation passes** — Inferred unit column has "EA", "LSUM" → validated
12. **Unit validation fails** — Inferred column has numbers → rejected
13. **Empty column validation** — Column has <3 non-empty cells → validation inconclusive, accept inference with reduced confidence

#### 3d: Unit tests for row parser _mapColumnSemantics

**File**: `test/features/pdf/extraction/stages/row_parser_semantic_mapping_test.dart` (new)

Tests to add:

14. **Clean 6-column map** — All columns have semantics → maps correctly (happy path)
15. **8-column map with null headers** — Simulates old bug scenario → null columns are SKIPPED, not position-fallback'd
16. **Missing itemNumber in column map** — Warning emitted, parsing continues with degraded output
17. **Duplicate semantics in column map** — Two columns claim 'description' → only first is used, warning emitted

#### 3e: Integration test — full pipeline with Springfield fixture

**File**: `test/features/pdf/extraction/golden/springfield_golden_test.dart` (existing, update expectations)

18. **Update golden expectations** — After fix, itemNumber extraction should jump from 7.8% to >50% (at minimum). Ground truth matches should increase from 0/131.
19. **Update stage trace diagnostic** — Verify the PIPELINE FAILURE CASCADE SUMMARY no longer reports margin-as-itemNumber

#### 3f: Regression test — cell boundary verification

**File**: `test/features/pdf/extraction/stages/cell_boundary_verification_test.dart` (existing, update)

20. **Convert bug-confirming tests to regression guards** — The tests currently confirm the bug exists. After the fix, update them to assert the bug is GONE:
    - Col 0 should NOT map to 'itemNumber'
    - Col 1 should map to 'itemNumber' (or margins should be stripped entirely)
    - No duplicate semantics in the mapping

---

## Implementation Order

```
Phase 1a (margin detection)         → Phase 1b (anchor inference)
                                          ↓
Phase 1c (content validation)       → Phase 1d (filter margins from output)
                                          ↓
Phase 2 (row parser fallback fix)   → Phase 3 (all tests)
```

Phases 1a-1d are sequential (each builds on the previous).
Phase 2 can be done in parallel with Phase 1 since it's a separate file.
Phase 3 (testing) must come after both Phase 1 and Phase 2.

---

## Files Modified

| File | Change | Risk |
|------|--------|------|
| `column_detector_v2.dart` | Add margin detection, anchor inference, content validation, margin filtering | Medium — core pipeline logic |
| `row_parser_v2.dart` | Remove position fallback in `_mapColumnSemantics`, add missing-column warnings | Low — removing broken logic |
| `stage_4c_column_detector_test.dart` | Add 8 new tests (margins, inference, validation) | None — test-only |
| `row_parser_semantic_mapping_test.dart` | New file, 4 tests for semantic mapping | None — test-only |
| `cell_boundary_verification_test.dart` | Update 3 existing tests from bug-confirming → regression guards | None — test-only |
| `springfield_golden_test.dart` | Update expectations for improved extraction | None — test-only |
| Springfield fixture JSONs | May need regeneration after pipeline changes | Low |

---

## Verification Criteria

1. **Springfield itemNumber extraction**: >50% (currently 7.8%)
2. **Springfield ground truth matches**: >20/131 (currently 0/131)
3. **No duplicate semantics** in column mapping for any fixture
4. **No margin columns** in final ColumnMap output
5. **All existing tests pass** (no regressions)
6. **New tests pass**: 20 new tests covering all edge cases
7. **Stage trace diagnostic** shows correct column assignments

---

## Agent Assignments

| Phase | Agent | Notes |
|-------|-------|-------|
| 1a-1d | pdf-agent or backend-data-layer-agent | Core extraction pipeline logic |
| 2 | Same agent (small change, same session) | 5-line change in row_parser |
| 3a-3d | qa-testing-agent | Unit test writing |
| 3e-3f | qa-testing-agent | Integration/regression test updates |

# Fix: Missing Quantity Column + Multi-Row Header Detection

## Context

After implementing the column detection propagation fix (commit `9c361e7`), manual testing of the Springfield PDF still shows **50+ items with merged unit+quantity** ("FT640", "EA48", "SYD27400"). All 1,386 tests pass.

**Root cause**: The propagation fix works correctly but propagates a **5-column layout that's missing the quantity column**. Syncfusion extracts the Springfield PDF's 2-row header as 8 elements, but "Quantity" (on Row 2, ~30px below Row 1) is never collected because `kHeaderYTolerance = 25.0px` is too tight. Without "Quantity", the header detector produces 5 columns where the "unit" column (x=1206-1488) spans both unit text and quantity text. Cell extractor concatenates both: "FT" + "640" = "FT640".

**Evidence** (from app log `2026-02-07T19:55`):
- 8 header elements checked: Item, Description, Unit, **Est.** (unmatched), Unit (dup), Price, Bid (unmatched), Amount
- "Quantity" never reaches keyword matching — filtered out by Y tolerance
- `headerRowYPositions` filtered from 6 → 1 (only page 0's Row 1 at Y=2509.6)
- Row 2 at Y≈2539 is ~30px away, exceeds 25px tolerance

## Fix: 3 Layers (Primary + Safety Nets)

### Layer 1: Increase header Y tolerance (PRIMARY FIX)
**File**: `lib/features/pdf/services/table_extraction/table_extractor.dart`

**Change**: Line 71, increase `kHeaderYTolerance` from `25.0` to `40.0`.

```dart
// Before:
static const double kHeaderYTolerance = 25.0;
// After:
static const double kHeaderYTolerance = 40.0;
```

**Why 40px**: Row 2 is ~30px below Row 1. 40px captures it with margin. Data rows typically start 50-80px below headers, so 40px won't pull in data elements. The broader `kHeaderRegionTolerance = 100.0` filter (line 580) already limits collection to the header region.

**Effect**: "Quantity" element at Y≈2539 now collected (within 40px of Y=2509). Multi-row combiner (`_combineMultiRowHeaders`) groups "Est." + "Quantity" by X proximity (both at x≈1543) → combined text "Est. Quantity" → matches `_qtyKeywords` → 6 columns produced with quantity column.

### Layer 2: Gap-based column inference (SAFETY NET)
**File**: `lib/features/pdf/services/table_extraction/header_column_detector.dart`

**Where**: After `_buildColumnsFromHeaders()` (around line 115), add `_inferMissingColumns()`.

**Logic**:
1. If fewer than 6 columns detected AND "unit" exists but "quantity" doesn't
2. Check gap between "unit" endX and "unitPrice" startX
3. If gap > 0.8x average numeric column width, insert a "quantity" column in the gap
4. Only applies to the specific missing-quantity pattern

### Layer 3: Post-processing split for concatenated unit+qty (SAFETY NET)
**File**: `lib/features/pdf/services/table_extraction/post_process/post_process_splitter.dart`

**Where**: In `splitMergedUnitQuantity()`, before the existing whitespace split at line 165.

**Logic**:
1. Regex match `^([A-Z/]+)(\d+(?:[,.]?\d+)*)$` for patterns like "FT640"
2. Try progressively shorter letter prefixes against `TokenClassifier.knownUnits`
3. If valid unit found and remainder is numeric, split into unit + quantity
4. Examples: "FT640" → FT/640, "EA48" → EA/48, "SYD27400" → SYD/27400
5. "LSUMI" → no split (no clean letter/digit boundary)

## Files Modified

| File | Change | Layer |
|------|--------|-------|
| `table_extractor.dart:71` | `kHeaderYTolerance` 25→40 | 1 |
| `header_column_detector.dart:~115` | Add `_inferMissingColumns()` | 2 |
| `post_process_splitter.dart:~155` | Add concatenated unit+qty regex split | 3 |

## New Tests

| Test | File | Purpose |
|------|------|---------|
| 2-row header with "Est."+"Quantity" | `header_column_detector_test.dart` | Verify 6 columns produced when elements span 2 rows |
| Gap inference for missing quantity | `header_column_detector_test.dart` | Verify quantity inserted when large gap detected |
| "FT640" split | `post_process_splitter_test.dart` | Verify concatenated patterns split correctly |
| "EA48", "SYD27400" splits | `post_process_splitter_test.dart` | Additional concatenated patterns |
| "LSUMI" no-split | `post_process_splitter_test.dart` | Verify non-matching patterns aren't split |

## New Fixture

**File**: `test/features/pdf/table_extraction/fixtures/springfield_2row_header.json`

Mimics real Springfield PDF with split header rows:
- Row 1 (y=100): "Item", "Description", "Unit", "Est.", "Unit", "Price", "Bid", "Amount"
- Row 2 (y=130): "No.", "of Work", "Quantity"
- Data rows with separate unit and quantity elements in distinct X ranges

## Implementation Order

1. Layer 1: Change `kHeaderYTolerance` to 40.0
2. Create 2-row header fixture + tests
3. Run all 1,386 tests → verify no regressions
4. Layer 2: Add gap inference in `header_column_detector.dart`
5. Layer 3: Add concatenated split in `post_process_splitter.dart`
6. Run all tests again → full regression pass

## Session Log Update

**File**: `.claude/logs/session-312-ocr-research.md`

Append after line 656 (end of Issue 3 section). Add new section:

```markdown
---

## Issue 4: Missing "Quantity" Column — Header Y Tolerance Too Tight (Session 316)

### Status of Column Propagation Fix (Issue 3)
The two-change fix from Session 315 (commit `9c361e7`) IS working correctly:
- Change 1 (confidence comparison): Per-page 0% results properly fall back to 83% global
- Change 2 (identity correction): Anchor corrections apply to all pages (offsets -39 to -52px, 100% confidence)
- All 1,386 tests pass

**BUT** the fix propagates a **wrong 5-column layout** that merges unit and quantity.

### Root Cause: "Quantity" Header Element Never Collected

The Springfield PDF header is 2 rows:
```
Row 1 (y≈2509): Item | Description | Unit | Est.     | Unit   | Bid
Row 2 (y≈2539): No.  | of Work     |      | Quantity | Price  | Amount
```

Syncfusion extracts 8 header elements (all from Row 1's Y band):
| # | Text | X Center | Matched To |
|---|------|----------|-----------|
| 1 | "Item" | 186.0 | itemNumber |
| 2 | "Description" | 725.9 | description |
| 3 | "Unit" | 1286.9 | unit |
| 4 | "Est." | 1543.4 | NONE |
| 5 | "Unit" | 1802.9 | NONE (duplicate) |
| 6 | "Price" | 1904.5 | unitPrice |
| 7 | "Bid" | 2116.6 | NONE |
| 8 | "Amount" | 2238.4 | bidAmount |

**"Quantity" is missing entirely** — it's on Row 2 at y≈2539.

### Failure Chain

1. `headerRowYPositions` has 6 entries (one per page), filtered to 1 by `kHeaderRegionTolerance = 100.0`
   - Only Y=2509.6 (page 0, Row 1) survives
   - Row 2 Y (≈2539) either not recorded by table_region_detector, or same as Row 1 entry
2. `_collectHeaderElementsForYs()` uses `kHeaderYTolerance = 25.0px` (line 691)
   - Row 2 elements at y≈2539 are 30px from Row 1 at y≈2509
   - 30 > 25 → "Quantity" filtered out
3. `_combineMultiRowHeaders()` reports `combinedGroups: 0`
   - "Est." (x=1543) has no partner to combine with — "Quantity" was never collected
4. Header detection produces 5 columns (no quantity):
   - `[itemNumber, description, unit, unitPrice, bidAmount]`
   - "unit" column spans x=1206-1488, covering BOTH unit text (x≈1287) and quantity text (x≈1450)
5. Cell extractor concatenates both: "FT" + "640" = "FT640"

### Column Boundaries (83% Header Detection)
```
itemNumber:   135 - 407    (Item at x=186)
description:  407 - 1206   (Description at x=726)
unit:         1206 - 1488  ← Covers BOTH unit and quantity text
unitPrice:    1488 - 2046  (Price at x=1905)
bidAmount:    2046 - 2324  (Amount at x=2238)
```

### App Log Evidence (2026-02-07T19:55)
```
HeaderExtractor: Filtered header Y positions: 6 → 1 (removed 5)
HeaderColumnDetector: Multi-row header combination complete: combinedGroups=0
Columns detected: 5 columns, method: header, confidence: 83.3%
Applied anchor correction to page 1 (offset=-43.0, scale=0.980, confidence=100.0%)
...all pages get corrections with 100% confidence
```

### Three-Layer Fix Strategy
1. **Increase `kHeaderYTolerance` to 40.0** — captures Row 2 elements (30px gap < 40px tolerance)
2. **Gap-based column inference** — if "unit" exists but "quantity" missing and large gap before "unitPrice", infer quantity column
3. **Post-processing split** — regex split "FT640" → FT + 640 using known unit validation

### Key Files
| File | Lines | Issue |
|------|-------|-------|
| `table_extractor.dart` | 71 | `kHeaderYTolerance = 25.0` (too tight) |
| `table_extractor.dart` | 682-698 | `_collectHeaderElementsForYs()` Y filter |
| `table_extractor.dart` | 560-615 | `_extractHeaderRowElements()` region filter |
| `header_column_detector.dart` | 60-69 | `_qtyKeywords` (includes "EST. QUANTITY") |
| `header_column_detector.dart` | 135-212 | `_combineMultiRowHeaders()` (works if elements reach it) |
| `post_process_splitter.dart` | 155-211 | `splitMergedUnitQuantity()` (no concat pattern) |
```

## Verification

1. `pwsh -Command "flutter test test/features/pdf/table_extraction/"` — table extraction tests
2. `pwsh -Command "flutter test test/features/pdf/"` — full PDF suite
3. Manual: Import Springfield PDF, verify pages 2-5 have separate unit/quantity columns

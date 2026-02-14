# Stage 4C ColumnDetectorV2 Implementation Summary

**Status**: ✅ Implemented (Layer 3 deferred due to type constraint)
**Location**: `lib/features/pdf/services/extraction/stages/column_detector_v2.dart`
**Added to barrel**: `lib/features/pdf/services/extraction/stages/stages.dart`

## Overview

Clean-slate v2 implementation following established stage patterns. Detects table column boundaries using three-layer approach (Layer 1 complete, Layers 2-3 deferred).

## Layer 1: Header Keyword Detection (✅ Complete)

### Algorithm
1. Extract header row elements from first detected region (via `headerRowIndices`)
2. Combine multi-row headers (elements within 3% page width horizontally)
   - Sort by Y, join text with spaces
   - Expand bounding box to encompass all combined elements
3. Match against 6 semantic keyword groups (priority order to avoid collisions):
   - `unitPrice`: "UNIT PRICE", "PRICE", "UNIT BID PRICE", "BID PRICE"
   - `bidAmount`: "AMOUNT", "BID AMOUNT", "TOTAL", "EXTENDED AMOUNT", "EXT. AMOUNT"
   - `quantity`: "QUANTITY", "QTY", "EST. QTY", "EST QTY", "EST. QUANTITY", "ESTIMATED QUANTITY"
   - `description`: "DESCRIPTION", "DESC", "ITEM DESCRIPTION", "DESCRIPTION OF WORK"
   - `itemNumber`: "ITEM", "ITEM NO", "ITEM NO.", "ITEM NUMBER", "NO."
   - `unit`: "UNIT", "UNITS", "U/M"
4. Use word-boundary matching for single-word patterns (prevents "BID" matching "BIDDER")
5. Build columns from matched headers:
   - Sort left-to-right by X center
   - First column: `startX = max(0.0, headerLeft - 0.01)`
   - Middle: boundary = midpoint between header edges
   - Large gap handling: if gap > 3× narrower header width, bias boundary toward narrower (30% padding)
   - Last column: `endX = min(1.0, headerRight + 0.01)`
6. If >= 3 keywords matched → success (confidence = matchCount / 6)
7. If < 3 keywords → fallback to fixed ratios (confidence *= 0.5)

### Constants
- `kHeaderXTolerance = 0.03` (3% page width for multi-row assembly)
- `kHeaderPadding = 0.01` (1% page width for column edges)
- `kLargeGapMultiplier = 3.0` (gap threshold for boundary bias)
- `kLargeGapBiasPadding = 0.30` (30% padding for large gaps)
- `kMinKeywordMatches = 3` (threshold for header-based success)

### Fallback Ratios
Used when < 3 keywords matched:
- itemNumber: 8%
- description: 42%
- unit: 10%
- quantity: 12%
- unitPrice: 14%
- bidAmount: 14%

## Layer 2: Line Detection (❌ Not Implemented)

**Why deferred**: Requires raw pixel images, which aren't available in normalized coordinate pipeline. The v2 pipeline works entirely in 0.0-1.0 normalized space.

**Placeholder**: Method `_detectFromLines` exists but returns null with warning.

**Future design**:
- Convert page images to grayscale
- Count dark pixels (<128) at each X position within table Y region
- Qualify as line if consecutive dark pixels >= 5 AND coverage >= 60%
- Cluster nearby positions (tolerance ~0.01 normalized)
- Cross-validate with Layer 1: if >= 50% column starts match → boost confidence

## Layer 3: Anchor Correction (❌ Deferred)

**Blocked by**: Type mismatch in `ColumnMap.perPageAdjustments`
- Current type: `Map<int, ColumnDef>?` (stores ONE column per page)
- Required type: `Map<int, List<ColumnDef>>?` (stores FULL column set per page)

**Algorithm designed** (commented out):
1. Extract reference anchors from base columns (itemNumber left, bidAmount right)
2. Find actual anchors per page from DATA rows:
   - Left: leftmost element matching `^\d+(\.\d+)?\.?$` (item number)
   - Right: rightmost element matching `\$[\d,.]+|\d+\.\d{2}` (currency)
3. Compute offset and scale corrections using MAD outlier rejection (3.5σ threshold)
4. Require >= 60% page coverage for valid anchors
5. Apply corrections to base columns for each page
6. Fill missing pages with base columns

**Constants** (commented out):
- `kAnchorCoverageThreshold = 0.60` (60% of pages must have valid anchors)
- `kMadOutlierThreshold = 3.5` (3.5σ for MAD outlier rejection)
- `kMinScaleCorrection = 0.9`, `kMaxScaleCorrection = 1.1` (clamp range)

## Missing Column Inference (✅ Complete)

If "unit" exists but "quantity" missing:
1. Check gap between unit.endX and next column startX
2. Compute average numeric column width (quantity, unitPrice, bidAmount)
3. If gap > 80% of average width → insert "quantity" column with confidence 0.6

## Methods

- `'header_keyword'` — 3+ keywords matched
- `'fallback_ratio'` — < 3 keywords, using fixed ratios
- `'anchor_corrected'` — (future) per-page adjustments applied
- `'none'` — no table regions detected

## Return Type

`(ColumnMap, StageReport)` tuple following v2 stage pattern.

## Data Accounting

No exclusions in column detection (inputCount = regions.length, excludedCount = 0).

## Test Coverage

**Status**: Not yet implemented — ready for testing

**Recommended tests**:
1. Header keyword matching (exact, partial, fallback)
2. Multi-row header assembly (vertical alignment)
3. Large gap boundary bias
4. Missing column inference
5. Empty regions handling
6. Invalid inputs (no headers, malformed data)

## Known Issues

1. **Layer 3 type mismatch**: Cannot implement per-page adjustments until ColumnMap model is corrected
2. **Line detection unavailable**: Would require passing page images through pipeline (design decision needed)

## Future Work

1. Fix `ColumnMap.perPageAdjustments` type → implement Layer 3 anchor correction
2. Decide on page image passing strategy → implement Layer 2 line detection
3. Write comprehensive test suite
4. Performance profiling on large documents (100+ pages)

## File Changes

- ✅ Created: `lib/features/pdf/services/extraction/stages/column_detector_v2.dart`
- ✅ Updated: `lib/features/pdf/services/extraction/stages/stages.dart` (added barrel export)
- ✅ Static analysis: No errors, all warnings addressed

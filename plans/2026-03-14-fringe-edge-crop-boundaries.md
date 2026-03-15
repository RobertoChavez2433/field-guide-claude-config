# Plan: Fringe-Edge Crop Boundaries

**Status**: `implement`
**Created**: 2026-03-14
**Goal**: Thread per-line fringe measurements from grid_line_remover through the pipeline to text_recognizer_v2's `_computeCellCrops`, so crop boundaries land at the outer fringe edge instead of grid-line centers. This eliminates TELEA gray-pixel contamination that causes OCR pipe `|` artifacts.

---

## Phase 1: GridLine Model — Add Fringe Fields

**Agent**: `pdf-agent`
**File**: `lib/features/pdf/services/extraction/models/grid_lines.dart`

### Step 1.1: Add fringeSide1/fringeSide2 to GridLine (2 min)

**WHY**: GridLine is the carrier for per-line metadata through the pipeline. Adding fringe fields here lets every downstream consumer access fringe data without parallel data structures.

**Fringe Side Semantics (FROM SPEC)**:
- Horizontal lines: side1 = top, side2 = bottom
- Vertical lines: side1 = left, side2 = right

Update the `GridLine` class (lines 6-16):

```dart
class GridLine {
  final double position; // normalized 0.0-1.0
  final int widthPixels; // detected pixel thickness (clamped 0-50)
  // NOTE: fringeSide1/fringeSide2 are FINAL values (after default application),
  // not raw measurements. Clamped 0-10 for safety.
  // WHY: Horizontal: side1=top, side2=bottom. Vertical: side1=left, side2=right.
  final int fringeSide1;
  final int fringeSide2;

  const GridLine({
    required double position,
    required int widthPixels,
    this.fringeSide1 = 0,
    this.fringeSide2 = 0,
  })  : position = position < 0.0 ? 0.0 : (position > 1.0 ? 1.0 : position),
        widthPixels = widthPixels > 50 ? 50 : (widthPixels < 0 ? 0 : widthPixels),
        fringeSide1 = fringeSide1 > 10 ? 10 : (fringeSide1 < 0 ? 0 : fringeSide1),
        fringeSide2 = fringeSide2 > 10 ? 10 : (fringeSide2 < 0 ? 0 : fringeSide2);

  @override
  String toString() =>
      'GridLine(pos=${position.toStringAsFixed(4)}, w=$widthPixels, f1=$fringeSide1, f2=$fringeSide2)';
}
```

**NOTE**: `fringeSide1`/`fringeSide2` default to 0 for backward compat — all existing callers that don't pass fringe will still work.

### Step 1.2: Update GridLineResult.toMap() serialization (2 min)

**WHY**: Diagnostic reports and stage serialization use toMap/fromMap. Fringe data must round-trip.

Update `toMap()` (lines 57-69) — add after the vertical_line_widths entry:

```dart
if (horizontalLines.any((l) => l.fringeSide1 > 0 || l.fringeSide2 > 0))
  'horizontal_fringe_side1': horizontalLines.map((l) => l.fringeSide1).toList(),
if (horizontalLines.any((l) => l.fringeSide1 > 0 || l.fringeSide2 > 0))
  'horizontal_fringe_side2': horizontalLines.map((l) => l.fringeSide2).toList(),
if (verticalLines.any((l) => l.fringeSide1 > 0 || l.fringeSide2 > 0))
  'vertical_fringe_side1': verticalLines.map((l) => l.fringeSide1).toList(),
if (verticalLines.any((l) => l.fringeSide1 > 0 || l.fringeSide2 > 0))
  'vertical_fringe_side2': verticalLines.map((l) => l.fringeSide2).toList(),
```

### Step 1.3: Update GridLineResult.fromMap() deserialization (3 min)

**WHY**: Must deserialize fringe arrays, defaulting to 0 when absent (backward compat with old serialized data).

Update `fromMap()` (lines 73-108) — add after vWidths parsing:

```dart
final hFringeS1 = List<num>.from(map['horizontal_fringe_side1'] as List? ?? const <num>[]).map((v) => v.toInt()).toList();
final hFringeS2 = List<num>.from(map['horizontal_fringe_side2'] as List? ?? const <num>[]).map((v) => v.toInt()).toList();
final vFringeS1 = List<num>.from(map['vertical_fringe_side1'] as List? ?? const <num>[]).map((v) => v.toInt()).toList();
final vFringeS2 = List<num>.from(map['vertical_fringe_side2'] as List? ?? const <num>[]).map((v) => v.toInt()).toList();
```

And update the GridLine constructors in the return statement:

```dart
horizontalLines: [
  for (int i = 0; i < hPositions.length; i++)
    GridLine(
      position: hPositions[i],
      widthPixels: i < hWidths.length ? hWidths[i] : 1,
      fringeSide1: i < hFringeS1.length ? hFringeS1[i] : 0,
      fringeSide2: i < hFringeS2.length ? hFringeS2[i] : 0,
    ),
],
verticalLines: [
  for (int i = 0; i < vPositions.length; i++)
    GridLine(
      position: vPositions[i],
      widthPixels: i < vWidths.length ? vWidths[i] : 1,
      fringeSide1: i < vFringeS1.length ? vFringeS1[i] : 0,
      fringeSide2: i < vFringeS2.length ? vFringeS2[i] : 0,
    ),
],
```

### Step 1.4: Verify Phase 1 compiles (1 min)

```
pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_2b_grid_line_detector_test.dart --no-pub"
```

---

## Phase 2: Grid Line Remover — Thread Fringe Through

**Agent**: `pdf-agent`
**File**: `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`

### Step 2.1: Add detectorIndex to _MergedLine (2 min)

**WHY**: We need to trace each merged line back to its detector-line index so we can assign fringe measurements to the correct GridLine.

Update `_MergedLine` (line 807-811):

```dart
class _MergedLine {
  final int x1, y1, x2, y2;
  final int thickness;
  // WHY: Index into the original detectorLines array, needed to map fringe back to GridLine.
  final int detectorIndex;
  const _MergedLine(this.x1, this.y1, this.x2, this.y2, this.thickness, this.detectorIndex);
}
```

### Step 2.2: Thread detectorIndex through _clusterAndCrossRef (3 min)

**WHY**: `_clusterAndCrossRef` maps Hough segments to detector lines via `bestDetIdx`. This is the only place the mapping is established.

In `_clusterAndCrossRef`, where `_MergedLine` is constructed from cross-referenced clusters (around line 1073), add `bestDetIdx` as the last argument:

```dart
// Existing: _MergedLine(perpAvg, startPix, perpAvg, endPix, thickness)
// Becomes:
_MergedLine(perpAvg, startPix, perpAvg, endPix, thickness, bestDetIdx)
```

**NOTE**: For horizontal lines the constructor order is (x1=perpAvg, y1=startPix, x2=perpAvg, y2=endPix) or similar — match the existing pattern exactly but append `bestDetIdx`.

In `_fallbackLines` (line 1104+), rewrite the loop from `for (final dl in detectorLines)` to index-based so we can track `di`:

```dart
// WHY: _fallbackLines currently uses for-each with no index. Rewrite to
// for(int di=0; ...) so detectorIndex is available for each fallback line.
var fallbackCount = 0;
for (int di = 0; di < detectorLines.length; di++) {
  fallbackCount++;
  final thickness = math.max(1, detectorLines[di].widthPixels);
  if (isHorizontal) {
    final y = (detectorLines[di].position * imageHeight).round().clamp(0, imageHeight - 1);
    lines.add(_MergedLine(0, y, imageWidth - 1, y, thickness, di));
  } else {
    final x = (detectorLines[di].position * imageWidth).round().clamp(0, imageWidth - 1);
    lines.add(_MergedLine(x, 0, x, imageHeight - 1, thickness, di));
  }
}
```

Also update all `_MergedLine` constructor calls in `_clusterAndCrossRef`'s accepted-line block (around lines 1057-1071) and fallback loop (lines 1075-1093) to append `bestDetIdx` or `di` respectively. **Search for ALL `_MergedLine(` constructor calls** in the file and update every one.

### Step 2.3: Add fringe maps to _GridRemovalResult (2 min)

**WHY**: The fringe data needs to flow from `_removeGridLines` up to `remove()` where enriched GridLines are built.

Add two fields to `_GridRemovalResult` (line 277-338):

```dart
// WHY: Maps detector-line index -> final fringe (after default application).
// Parallel to the detectorLines arrays passed to _clusterAndCrossRef.
final Map<int, ({int side1, int side2})> hFringeByDetIdx;
final Map<int, ({int side1, int side2})> vFringeByDetIdx;
```

Add to constructor as optional non-const fields (Dart records in Maps are not const-capable):

```dart
// NOTE: Cannot use `const {}` default because Map<int, ({int side1, int side2})>
// contains records which are not compile-time constants. Use regular default.
this.hFringeByDetIdx = const {},
this.vFringeByDetIdx = const {},
```

**IMPORTANT**: If the `const` on the `_GridRemovalResult` constructor prevents this, remove `const` from the constructor declaration. The class is only instantiated once per page so the performance impact is zero.

### Step 2.4: Build fringe maps in _removeGridLines after Pass 2 (5 min)

**WHY**: After Pass 2, `fringeResults[i]` contains the FINAL fringe (with defaults applied). `allLines[i]` gives us the `_MergedLine` whose `detectorIndex` maps back to the original detector line.

After the Pass 2 loop (around line 693), add:

```dart
// WHY: Build fringe maps using each _MergedLine's detectorIndex field (NOT array index i).
final hFringeByDetIdx = <int, ({int side1, int side2})>{};
final vFringeByDetIdx = <int, ({int side1, int side2})>{};

for (int i = 0; i < allLines.length; i++) {
  final entry = allLines[i];
  final fringe = fringeResults[i];
  final detIdx = entry.line.detectorIndex;

  if (entry.isH) {
    // WHY: If multiple merged lines map to same detector line (shouldn't happen
    // due to matchedDetectorIndices uniqueness), keep the max fringe.
    final existing = hFringeByDetIdx[detIdx];
    if (existing == null ||
        (fringe.side1 + fringe.side2) > (existing.side1 + existing.side2)) {
      hFringeByDetIdx[detIdx] = fringe;
    }
  } else {
    final existing = vFringeByDetIdx[detIdx];
    if (existing == null ||
        (fringe.side1 + fringe.side2) > (existing.side1 + existing.side2)) {
      vFringeByDetIdx[detIdx] = fringe;
    }
  }
}
```

Pass `hFringeByDetIdx` and `vFringeByDetIdx` into the `_GridRemovalResult` constructor at the end of `_removeGridLines`.

### Step 2.5: Change remove() return type to 3-tuple (5 min)

**WHY**: The pipeline needs enriched GridLines (with fringe) alongside cleaned pages and the stage report.

Change signature from:
```dart
Future<(Map<int, PreprocessedPage>, StageReport)> remove(...)
```
to:
```dart
Future<(Map<int, PreprocessedPage>, StageReport, Map<int, GridLineResult>)> remove(...)
```

After processing each page (where `_removeGridLines` returns `_GridRemovalResult`), build enriched `GridLineResult` per page:

```dart
// WHY: Enrich detector GridLines with final fringe measurements from remover.
final enrichedGridLines = <int, GridLineResult>{};

// Inside the per-page loop, after _removeGridLines returns `result`:
final originalGl = gridLines[pageIndex]; // The detector's GridLineResult
if (originalGl != null) {
  enrichedGridLines[pageIndex] = GridLineResult(
    pageIndex: pageIndex,
    horizontalLines: [
      for (int i = 0; i < originalGl.horizontalLines.length; i++)
        GridLine(
          position: originalGl.horizontalLines[i].position,
          widthPixels: originalGl.horizontalLines[i].widthPixels,
          fringeSide1: result.hFringeByDetIdx[i]?.side1 ?? 0,
          fringeSide2: result.hFringeByDetIdx[i]?.side2 ?? 0,
        ),
    ],
    verticalLines: [
      for (int i = 0; i < originalGl.verticalLines.length; i++)
        GridLine(
          position: originalGl.verticalLines[i].position,
          widthPixels: originalGl.verticalLines[i].widthPixels,
          fringeSide1: result.vFringeByDetIdx[i]?.side1 ?? 0,
          fringeSide2: result.vFringeByDetIdx[i]?.side2 ?? 0,
        ),
    ],
    hasGrid: originalGl.hasGrid,
    confidence: originalGl.confidence,
  );
}
```

Return the 3-tuple: `(cleanedPages, report, enrichedGridLines)`.

**IMPORTANT**: The `remove()` method has an early-return path for `preprocessedPages.isEmpty` (around line 63-80) and a catch block that also returns. **Search for ALL `return (` statements** within `remove()` and update every one to return a 3-tuple. The early-return and error paths should return `<int, GridLineResult>{}` as the third element. For passthrough pages (non-grid), carry forward the original `GridLineResult` from `gridLines.pages[pageIndex]` into `enrichedGridLines` with fringe=0.

### Step 2.6: Verify Phase 2 compiles (1 min)

```
pwsh -Command "flutter test test/features/pdf/extraction/stages/grid_line_remover_test.dart --no-pub"
```

Expect failures from return-type mismatch — that's OK, tests are updated in Phase 5.

---

## Phase 3: Pipeline Wiring

**Agent**: `pdf-agent`
**File**: `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`

### Step 3.1: Capture enriched GridLines from remove() (2 min)

**WHY**: The pipeline currently discards fringe data by rebuilding GridLines from the original detector output. We need to use the enriched version.

Update `_runExtractionStages` (line 494-527):

```dart
// FROM: final (cleanedPages, stage2Bii6Report) = await gridLineRemover.remove(...)
// TO:
final (cleanedPages, stage2Bii6Report, enrichedGridLines) = await gridLineRemover.remove(
  preprocessedPages: preprocessedPages,
  gridLines: gridLines,
  onDiagnosticImage: onDiagnosticImage,
);
```

### Step 3.2: Use enriched GridLines in _buildGridLinesForOcr (3 min)

**WHY**: `_buildGridLinesForOcr` currently passes through original detector GridLines. It must use enriched ones (with fringe) so `_computeCellCrops` can access fringe data.

Update the call to `_buildGridLinesForOcr`:

```dart
// WHY: Wrap enrichedGridLines Map in a GridLines object for type compatibility.
// Use the original detectedAt timestamp since fringe enrichment doesn't change detection time.
final enrichedGridLinesWrapped = GridLines(
  pages: enrichedGridLines,
  detectedAt: gridLines.detectedAt,
);

final ocrGridLines = _buildGridLinesForOcr(
  detectedGridLines: enrichedGridLinesWrapped,  // NOTE: was `gridLines`, now enriched
  gridRemovalReport: stage2Bii6Report,
);
```

**NOTE**: `_buildGridLinesForOcr` accepts `GridLines` (not `Map<int, GridLineResult>`), so we must wrap the map. The `detectedAt` timestamp is sourced from the original `gridLines.detectedAt`. `_buildGridLinesForOcr` already handles missing pages by zeroing them out.

### Step 3.3: Verify Phase 3 compiles (1 min)

```
pwsh -Command "flutter test test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart --no-pub"
```

---

## Phase 4: Crop Insets in text_recognizer_v2

**Agent**: `pdf-agent`
**File**: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`

### Step 4.0: Update _computeCellCrops docblock (1 min)

**WHY**: The existing docblock at line 1170-1174 says "No per-edge insets — research confirms no table extraction library does inpaint-then-trim." This is now outdated. Replace with:

```dart
/// WHY: Fringe-edge crop boundaries. After grid lines are inpainted away
/// by Stage 2B-ii.6, crops are inset by (halfWidth + fringe + 1px safety)
/// to exclude TELEA interpolation artifacts at mask boundaries.
/// FROM SPEC: "Place crop boundaries at outer fringe edge"
```

Also update the `_CellCrop` docstring (lines 1229-1235) to remove the "center-to-center" language.

### Step 4.1: Update _computeCellCrops signature (2 min)

**WHY**: Need image dimensions to convert pixel-based fringe values to normalized coordinates.

```dart
List<_CellCrop> _computeCellCrops({
  required List<GridLine> sortedHorizontalLines,
  required List<GridLine> sortedVerticalLines,
  required int imageWidth,
  required int imageHeight,
})
```

### Step 4.2: Apply fringe-based insets (5 min)

**WHY**: The core fix. Instead of cropping at grid-line centers, crop at the outer fringe edge + 1px safety margin. This ensures TELEA gray pixels are excluded from OCR input.

Inside `_computeCellCrops`, replace the direct position usage with inset-adjusted bounds:

```dart
// FROM SPEC: Cell crop inset semantics:
// - top edge: uses top boundary line's side2 (bottom of that line)
// - bottom edge: uses bottom boundary line's side1 (top of that line)
// - left edge: uses left boundary line's side2 (right of that line)
// - right edge: uses right boundary line's side1 (left of that line)

final topLine = sortedHorizontalLines[rowIndex];
final bottomLine = sortedHorizontalLines[rowIndex + 1];
final leftLine = sortedVerticalLines[columnIndex];
final rightLine = sortedVerticalLines[columnIndex + 1];

// WHY: (widthPixels + 1) ~/ 2 matches cv.line's actual half-extent (integer ceil).
// +1 pixel safety margin beyond fringe outer edge.
final topInsetPx = (topLine.widthPixels + 1) ~/ 2 + topLine.fringeSide2 + 1;
final bottomInsetPx = (bottomLine.widthPixels + 1) ~/ 2 + bottomLine.fringeSide1 + 1;
final leftInsetPx = (leftLine.widthPixels + 1) ~/ 2 + leftLine.fringeSide2 + 1;
final rightInsetPx = (rightLine.widthPixels + 1) ~/ 2 + rightLine.fringeSide1 + 1;

// WHY: Convert pixel insets to normalized coordinates.
final topInset = topInsetPx / imageHeight;
final bottomInset = bottomInsetPx / imageHeight;
final leftInset = leftInsetPx / imageWidth;
final rightInset = rightInsetPx / imageWidth;

var topPos = (topLine.position + topInset).clamp(0.0, 1.0);
var bottomPos = (bottomLine.position - bottomInset).clamp(0.0, 1.0);
var leftPos = (leftLine.position + leftInset).clamp(0.0, 1.0);
var rightPos = (rightLine.position - rightInset).clamp(0.0, 1.0);

// WHY: Guard against degenerate crops where insets exceed cell size.
// Fall back to center-to-center if crop would have zero or negative extent.
if (topPos >= bottomPos || leftPos >= rightPos) {
  topPos = topLine.position.clamp(0.0, 1.0);
  bottomPos = bottomLine.position.clamp(0.0, 1.0);
  leftPos = leftLine.position.clamp(0.0, 1.0);
  rightPos = rightLine.position.clamp(0.0, 1.0);
}

crops.add(_CellCrop(
  rowIndex: rowIndex,
  columnIndex: columnIndex,
  bounds: Rect.fromLTRB(leftPos, topPos, rightPos, bottomPos),
));
```

**NOTE**: For edge lines at position 0.0 or 1.0, the `+topInset` / `-bottomInset` arithmetic naturally keeps the crop within bounds thanks to `.clamp(0.0, 1.0)`. The fringe of page-edge lines is typically 0 anyway since there's no grid line there.

### Step 4.3: Update call site (2 min)

Update the call site (around line 430-433) to pass image dimensions:

```dart
final cellCrops = _computeCellCrops(
  sortedHorizontalLines: sortedHorizontal,
  sortedVerticalLines: sortedVertical,
  imageWidth: decodedImage.width,
  imageHeight: decodedImage.height,
);
```

**NOTE**: Confirm `decodedImage` is in scope at this call site. If the cleaned image dimensions differ from the decoded image, use `preprocessedPage.enhancedSizePixels` width/height instead — the fringe was measured on the enhanced image.

### Step 4.4: Verify Phase 4 compiles (1 min)

```
pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart --no-pub"
```

---

## Phase 5: Test Updates

**Agent**: `qa-testing-agent`

### Step 5.1: Update test_fixtures.dart gl() helper (2 min)

**File**: `test/features/pdf/extraction/helpers/test_fixtures.dart`

**WHY**: Test fixtures need to create GridLines with fringe values for new tests.

Add an overload or update `gl()`:

```dart
/// Creates GridLine list. [width] applies to all. [fringes] is optional
/// list of (side1, side2) per line; defaults to (0, 0).
List<GridLine> gl(List<double> positions, [int width = 0, List<(int, int)>? fringes]) {
  return [
    for (int i = 0; i < positions.length; i++)
      GridLine(
        position: positions[i],
        widthPixels: width,
        fringeSide1: fringes != null && i < fringes.length ? fringes[i].$1 : 0,
        fringeSide2: fringes != null && i < fringes.length ? fringes[i].$2 : 0,
      ),
  ];
}
```

### Step 5.2: Update mock_stages.dart for 3-tuple return (3 min)

**File**: `test/features/pdf/extraction/helpers/mock_stages.dart`

**WHY**: Mock GridLineRemover must return the new 3-tuple type.

Find the mock `remove()` method and update its return type to include the enriched GridLines map. Return an empty `<int, GridLineResult>{}` map as the third element (tests that don't exercise fringe don't need real data).

### Step 5.3: Update grid_line_remover_test.dart (5 min)

**File**: `test/features/pdf/extraction/stages/grid_line_remover_test.dart`

**WHY**: Tests destructure the return value as a 2-tuple; must update to 3-tuple.

1. Find all `final (cleanedPages, report) = await ...remove(...)` patterns
2. Change to `final (cleanedPages, report, enrichedGridLines) = await ...remove(...)`
3. Add at least one test that verifies fringe values flow through:

```dart
test('enriched GridLines contain fringe measurements', () async {
  // Use a fixture with known grid lines
  final (_, _, enrichedGl) = await remover.remove(...);
  final pageGl = enrichedGl[0]!;
  // At least some lines should have non-zero fringe
  final hasAnyFringe = [
    ...pageGl.horizontalLines,
    ...pageGl.verticalLines,
  ].any((l) => l.fringeSide1 > 0 || l.fringeSide2 > 0);
  expect(hasAnyFringe, isTrue, reason: 'Expected at least one line with fringe data');
});
```

### Step 5.4: Update stage_2b_grid_line_detector_test.dart (3 min)

**File**: `test/features/pdf/extraction/stages/stage_2b_grid_line_detector_test.dart`

**WHY**: Serialization round-trip tests need to verify fringe fields.

Add a test:

```dart
test('GridLineResult serialization round-trips fringe data', () {
  final original = GridLineResult(
    pageIndex: 0,
    horizontalLines: [
      GridLine(position: 0.1, widthPixels: 3, fringeSide1: 1, fringeSide2: 2),
      GridLine(position: 0.5, widthPixels: 2, fringeSide1: 0, fringeSide2: 1),
    ],
    verticalLines: [
      GridLine(position: 0.2, widthPixels: 4, fringeSide1: 2, fringeSide2: 3),
    ],
    hasGrid: true,
    confidence: 0.95,
  );
  final map = original.toMap();
  final restored = GridLineResult.fromMap(map);

  expect(restored.horizontalLines[0].fringeSide1, equals(1));
  expect(restored.horizontalLines[0].fringeSide2, equals(2));
  expect(restored.horizontalLines[1].fringeSide1, equals(0));
  expect(restored.horizontalLines[1].fringeSide2, equals(1));
  expect(restored.verticalLines[0].fringeSide1, equals(2));
  expect(restored.verticalLines[0].fringeSide2, equals(3));
});

test('GridLineResult.fromMap handles missing fringe data (backward compat)', () {
  final map = {
    'page_index': 0,
    'horizontal_lines': [0.1, 0.5],
    'vertical_lines': [0.2],
    'has_grid': true,
    'confidence': 0.9,
  };
  final result = GridLineResult.fromMap(map);
  expect(result.horizontalLines[0].fringeSide1, equals(0));
  expect(result.horizontalLines[0].fringeSide2, equals(0));
});
```

### Step 5.5: Update stage_2b6_to_2biii_contract_test.dart (3 min)

**File**: `test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart`

**WHY**: Contract test validates the interface between grid remover output and text recognizer input. Must validate fringe fields pass through.

Update any mock GridLineRemover returns to use 3-tuple. Add assertion that GridLines reaching text_recognizer carry fringe data.

### Step 5.6: Update stage_2b_text_recognizer_test.dart (5 min)

**File**: `test/features/pdf/extraction/stages/stage_2b_text_recognizer_test.dart`

**WHY**: Core validation that fringe-based insets actually shrink crop boundaries.

Add test:

```dart
test('_computeCellCrops applies fringe insets', () {
  // 2x2 grid (3 horizontal, 3 vertical lines) on a 1000x1000 image
  final hLines = [
    GridLine(position: 0.0, widthPixels: 4, fringeSide1: 0, fringeSide2: 2),
    GridLine(position: 0.5, widthPixels: 4, fringeSide1: 1, fringeSide2: 1),
    GridLine(position: 1.0, widthPixels: 4, fringeSide1: 2, fringeSide2: 0),
  ];
  final vLines = [
    GridLine(position: 0.0, widthPixels: 4, fringeSide1: 0, fringeSide2: 2),
    GridLine(position: 0.5, widthPixels: 4, fringeSide1: 1, fringeSide2: 1),
    GridLine(position: 1.0, widthPixels: 4, fringeSide1: 2, fringeSide2: 0),
  ];

  // Top-left cell (row=0, col=0):
  // topInset = (4+1)~/2 + 2 + 1 = 2+2+1 = 5px -> 5/1000 = 0.005
  // bottomInset = (4+1)~/2 + 1 + 1 = 2+1+1 = 4px -> 4/1000 = 0.004
  // leftInset = 5/1000 = 0.005
  // rightInset = 4/1000 = 0.004
  // topPos = 0.0 + 0.005 = 0.005
  // bottomPos = 0.5 - 0.004 = 0.496
  // leftPos = 0.0 + 0.005 = 0.005
  // rightPos = 0.5 - 0.004 = 0.496

  // NOTE: Access _computeCellCrops via the test's mechanism (direct call or
  // through recognize()). Adjust based on test file's existing test patterns.
});
```

**NOTE**: If `_computeCellCrops` is private, test through the public `recognize()` API or use `@visibleForTesting`. Match whatever pattern the existing tests use.

### Step 5.7: Verify all tests pass (2 min)

```
pwsh -Command "flutter test test/features/pdf/extraction/ --no-pub"
```

---

## Phase 6: Integration Verification

**Agent**: `pdf-agent`

### Step 6.1: Run full unit test suite (2 min)

```
pwsh -Command "flutter test --no-pub"
```

### Step 6.2: Run Springfield integration test (5 min)

```
pwsh -Command "flutter test integration_test/springfield_report_test.dart --no-pub" -timeout 600000
```

**WHY**: This is the end-to-end validation. With fringe-edge crops, we expect fewer pipe `|` artifacts in OCR output, reducing the 37 FAIL + 15 MISS count.

### Step 6.3: Review Springfield report diff (3 min)

Compare the new extraction_suite_output.txt against the previous baseline. Look for:
- Reduced FAIL count (target: <25)
- Reduced pipe `|` contamination in cell text
- No new regressions (PASS items that became FAIL)

---

## Risk Notes

1. **`_computeCellCrops` degenerate guard**: If fringe insets consume the entire cell (very narrow rows), the fallback to center-to-center preserves existing behavior. This is safe but means those cells won't benefit from the fix.

2. **detectorIndex on _MergedLine**: All constructors of `_MergedLine` must be updated. Search for any other construction sites beyond `_clusterAndCrossRef`.

3. **Image dimension source**: Verify whether `decodedImage.width/height` or `preprocessedPage.enhancedSizePixels` is the correct dimension at the `_computeCellCrops` call site. The fringe was measured on the enhanced/preprocessed image, so dimensions must match.

4. **Backward compatibility**: Old serialized GridLineResult data (without fringe fields) will deserialize with fringe=0, which means no inset adjustment — equivalent to current behavior. Safe.

# Dynamic Fringe Removal Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Add dynamic per-line grayscale fringe measurement to GridLineRemover, expanding the removal mask to cover anti-aliased grid line edges that cause phantom OCR elements.
**Spec:** `.claude/specs/2026-03-14-dynamic-fringe-removal-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-14-dynamic-fringe-removal/`

**Architecture:** Fringe measurement is inserted into `_removeGridLines()` after the existing removal mask is built and before inpainting. It scans the grayscale image perpendicular to each detected line, measures the anti-aliased fringe width (128-200 band), and expands the mask to cover it. No text protection subtraction — inpainting handles contact points.
**Tech Stack:** Dart, opencv_dart (cv.Mat pixel access, cv.line, cv.countNonZero, cv.inpaint)
**Blast Radius:** 1 direct, 0 dependent (public API unchanged), 2 tests modified, 1 test helper added

---

## Phase 1: Test Infrastructure

### 1.1 Add `createAntiAliasedGridImage()` to test_fixtures.dart

**Agent:** `qa-testing-agent`

#### Step 1.1.1: Add the anti-aliased grid image helper

**File:** `test/features/pdf/extraction/helpers/test_fixtures.dart` (after line 340)

```dart
// WHY: Existing createSyntheticGridImage draws binary black/white lines with
// no gradient. To test fringe removal we need lines with anti-aliased edges
// (grayscale pixels in the 128-199 band flanking the solid core).
// FROM SPEC: "fringe band is 128-199"
/// Creates a synthetic grayscale PNG with anti-aliased grid lines.
///
/// Each line has a solid black core ([lineThickness] px) flanked by
/// [fringeWidth] pixels of anti-aliased gradient on each side.
/// Fringe pixels ramp from ~140 (near core) to ~190 (far edge),
/// staying within the 128-199 fringe band.
Uint8List createAntiAliasedGridImage({
  int width = 800,
  int height = 1000,
  List<double> horizontalYs = const [],
  List<double> verticalXs = const [],
  int lineThickness = 3,
  int fringeWidth = 2,
}) {
  final image = img.Image(width: width, height: height);
  img.fill(image, color: img.ColorRgb8(255, 255, 255));

  // NOTE: Fringe pixels linearly interpolate from 140 (near core) to 190 (far edge).
  // This keeps them firmly in the 128-199 detection band.
  int fringeGray(int step, int maxSteps) {
    // step 0 = closest to core (darker), step maxSteps-1 = farthest (lighter)
    if (maxSteps <= 1) return 165;
    return 140 + ((190 - 140) * step ~/ (maxSteps - 1));
  }

  // Draw horizontal lines with fringe
  for (final normY in horizontalYs) {
    final centerY = (normY * height).round();
    // Solid core
    for (int dy = 0; dy < lineThickness; dy++) {
      final row = centerY + dy;
      if (row < 0 || row >= height) continue;
      for (int x = 0; x < width; x++) {
        image.setPixel(x, row, img.ColorRgb8(0, 0, 0));
      }
    }
    // Top fringe (above core)
    for (int f = 0; f < fringeWidth; f++) {
      final row = centerY - 1 - f;
      if (row < 0) continue;
      final g = fringeGray(f, fringeWidth);
      for (int x = 0; x < width; x++) {
        image.setPixel(x, row, img.ColorRgb8(g, g, g));
      }
    }
    // Bottom fringe (below core)
    for (int f = 0; f < fringeWidth; f++) {
      final row = centerY + lineThickness + f;
      if (row >= height) continue;
      final g = fringeGray(f, fringeWidth);
      for (int x = 0; x < width; x++) {
        image.setPixel(x, row, img.ColorRgb8(g, g, g));
      }
    }
  }

  // Draw vertical lines with fringe
  for (final normX in verticalXs) {
    final centerX = (normX * width).round();
    // Solid core
    for (int dx = 0; dx < lineThickness; dx++) {
      final col = centerX + dx;
      if (col < 0 || col >= width) continue;
      for (int y = 0; y < height; y++) {
        image.setPixel(col, y, img.ColorRgb8(0, 0, 0));
      }
    }
    // Left fringe
    for (int f = 0; f < fringeWidth; f++) {
      final col = centerX - 1 - f;
      if (col < 0) continue;
      final g = fringeGray(f, fringeWidth);
      for (int y = 0; y < height; y++) {
        image.setPixel(col, y, img.ColorRgb8(g, g, g));
      }
    }
    // Right fringe
    for (int f = 0; f < fringeWidth; f++) {
      final col = centerX + lineThickness + f;
      if (col >= width) continue;
      final g = fringeGray(f, fringeWidth);
      for (int y = 0; y < height; y++) {
        image.setPixel(col, y, img.ColorRgb8(g, g, g));
      }
    }
  }

  return Uint8List.fromList(img.encodePng(image));
}
```

#### Step 1.1.2: Verify the helper compiles

```bash
pwsh -Command "flutter test test/features/pdf/extraction/helpers/test_fixtures.dart --no-execute"
```

> **NOTE:** If `--no-execute` is not supported, just run the existing grid_line_remover_test to confirm no import errors.

---

## Phase 2: _GridRemovalResult Struct Changes

### 2.1 Add 5 fringe metric fields to _GridRemovalResult

**Agent:** `pdf-agent`

#### Step 2.1.1: Add fields to _GridRemovalResult class

**File:** `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
**Location:** class `_GridRemovalResult` (lines 241-283)

Add these 5 fields after `verticalMaskPixels` (line 257):

```dart
  // WHY: Dynamic fringe measurement metrics for diagnostics and rollback checks.
  // FROM SPEC: "avg_fringe_width > 3.0 → rollback"
  final int fringeLinesScanned;     // Lines where fringe measurement was attempted
  final int fringeLinesExpanded;    // Lines where fringe > 0 and mask was expanded
  final double avgFringeWidth;      // Mean of (side1+side2) across expanded lines
  final double maxFringeWidth;      // Max single-line total fringe width
  final int fringePixelsAdded;      // Additional mask pixels from fringe expansion
```

#### Step 2.1.2: Add constructor parameters

**File:** `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
**Location:** `const _GridRemovalResult({...})` constructor (approx lines 263-283)

Add after `this.verticalMaskPixels,`:

```dart
    // FROM SPEC: fringe metrics for diagnostics
    this.fringeLinesScanned = 0,
    this.fringeLinesExpanded = 0,
    this.avgFringeWidth = 0.0,
    this.maxFringeWidth = 0.0,
    this.fringePixelsAdded = 0,
```

> **NOTE:** Using default values so the existing constructor call at line 575 compiles without changes until Phase 3 wires them up.

#### Step 2.1.3: Add fringe metrics to the per-page metric dict in remove()

**File:** `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
**Location:** `remove()` method, metric dict (lines 133-149)

Add after `'vertical_mask_pixels': processed.verticalMaskPixels,` (line 147):

```dart
          // WHY: Fringe metrics exposed for contract tests and rollback monitoring
          // FROM SPEC: "avg_fringe_width > 3.0 → rollback"
          'fringe_lines_scanned': processed.fringeLinesScanned,
          'fringe_lines_expanded': processed.fringeLinesExpanded,
          'avg_fringe_width': processed.avgFringeWidth,
          'max_fringe_width': processed.maxFringeWidth,
          'fringe_pixels_added': processed.fringePixelsAdded,
```

#### Step 2.1.4: Verify compilation

```bash
pwsh -Command "flutter test test/features/pdf/extraction/stages/grid_line_remover_test.dart"
```

> **NOTE:** All existing tests must still pass since new fields have defaults.

---

## Phase 3: Core Algorithm

### 3.1 Add `_measureLineFringe()` function

**Agent:** `pdf-agent`

#### Step 3.1.1: Add constants for fringe measurement

**File:** `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
**Location:** After existing constants (near top of file, after `_kMaxSegmentsPerAxis`)

```dart
// WHY: Fringe band is the grayscale zone between solid line (< 128) and
// clean background (>= 200). Anti-aliased edges from PDF rasterization land here.
// FROM SPEC: "fringeThreshold = 200, fringe band is 128-199"
const int _kFringeThreshold = 200;

// FROM SPEC: "maxFringeScan = 3 — max pixels outward from line edge per side"
const int _kMaxFringeScan = 3;

// FROM SPEC: "sampleCount = 10 — perpendicular profile samples per line"
const int _kSampleCount = 10;

// FROM SPEC: "minimum 5px span to attempt fringe measurement"
const int _kMinLineSpanForFringe = 5;
```

#### Step 3.1.2: Create `_measureLineFringe()` function

**File:** `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
**Location:** After `_MergedLine` class (after line 639), before `_MergeResult`

```dart
/// Measures the anti-aliased fringe width on each side of a merged line.
///
/// Returns (side1Fringe, side2Fringe) where side1 is top/left and side2 is
/// bottom/right depending on line orientation.
///
/// WHY: PDF rasterizers produce anti-aliased grid line edges (grayscale pixels
/// in 128-199 band) that the binary mask misses. These fringe pixels cause
/// phantom OCR elements. Measuring per-line lets us expand the mask precisely.
/// FROM SPEC: "At each sample: scan perpendicular from line edge"
({int side1, int side2}) _measureLineFringe(
  cv.Mat gray,
  _MergedLine line, {
  bool isHorizontal = true,
}) {
  final rows = gray.rows;
  final cols = gray.cols;

  // FROM SPEC: "Skip if span < 5px"
  final span = isHorizontal
      ? (line.x2 - line.x1).abs()
      : (line.y2 - line.y1).abs();
  if (span < _kMinLineSpanForFringe) return (side1: 0, side2: 0);

  // FROM SPEC: "min(10, max(3, lineSpan/2)), evenly spaced 10%-90%"
  final sampleCount = span < 6 ? 3 : (span ~/ 2).clamp(3, _kSampleCount);

  final side1Measurements = <int>[];
  final side2Measurements = <int>[];

  for (int i = 0; i < sampleCount; i++) {
    // Evenly spaced 10%-90% along the line span
    final fraction = 0.10 + (0.80 * i / (sampleCount - 1).clamp(1, sampleCount));

    int sampleX, sampleY;
    if (isHorizontal) {
      sampleX = (line.x1 + (span * fraction)).round().clamp(0, cols - 1);
      sampleY = ((line.y1 + line.y2) ~/ 2); // center of line
    } else {
      sampleX = ((line.x1 + line.x2) ~/ 2); // center of line
      sampleY = (line.y1 + (span * fraction)).round().clamp(0, rows - 1);
    }

    final halfThick = line.thickness ~/ 2;

    // FROM SPEC: "scan perpendicular from line edge (center +/- thickness/2 + 1)"
    // Side 1: top (H) or left (V)
    {
      final edgeStart = isHorizontal
          ? (sampleY - halfThick - 1)
          : (sampleX - halfThick - 1);

      // FROM SPEC: "If start pixel < 128, skip sample"
      final startCoord = edgeStart.clamp(0, isHorizontal ? rows - 1 : cols - 1);
      final startVal = isHorizontal
          ? gray.at<int>(startCoord, sampleX)
          : gray.at<int>(sampleY, startCoord);
      if (startVal >= _kDarkPixelThreshold) {
        // Walk outward counting fringe pixels
        int count = 0;
        for (int step = 0; step < _kMaxFringeScan; step++) {
          final coord = edgeStart - step;
          if (coord < 0) break;
          final val = isHorizontal
              ? gray.at<int>(coord, sampleX)
              : gray.at<int>(sampleY, coord);
          // FROM SPEC: "Stop at >=200 or <128. Cap at 3px."
          if (val >= _kFringeThreshold || val < _kDarkPixelThreshold) break;
          count++;
        }
        side1Measurements.add(count);
      }
    }

    // Side 2: bottom (H) or right (V)
    {
      final edgeStart = isHorizontal
          ? (sampleY + halfThick + 1)
          : (sampleX + halfThick + 1);

      final startCoord = edgeStart.clamp(0, isHorizontal ? rows - 1 : cols - 1);
      final startVal = isHorizontal
          ? gray.at<int>(startCoord, sampleX)
          : gray.at<int>(sampleY, startCoord);
      if (startVal >= _kDarkPixelThreshold) {
        int count = 0;
        for (int step = 0; step < _kMaxFringeScan; step++) {
          final coord = edgeStart + step;
          if (coord >= (isHorizontal ? rows : cols)) break;
          final val = isHorizontal
              ? gray.at<int>(coord, sampleX)
              : gray.at<int>(sampleY, coord);
          if (val >= _kFringeThreshold || val < _kDarkPixelThreshold) break;
          count++;
        }
        side2Measurements.add(count);
      }
    }
  }

  // FROM SPEC: "Per-line fringe = median of valid measurements per side. If <3 valid, fringe=0."
  int median(List<int> vals) {
    if (vals.length < 3) return 0;
    vals.sort();
    return vals[vals.length ~/ 2];
  }

  return (side1: median(side1Measurements), side2: median(side2Measurements));
}
```

### 3.2 Insert fringe measurement into `_removeGridLines()`

**Agent:** `pdf-agent`

#### Step 3.2.1: Fix H/V mask pixel tracking

**File:** `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
**Location:** Mask drawing section (lines 501-536)

Replace the current mask drawing and metric section. The key changes are:
1. Count H-mask pixels AFTER drawing H-lines but BEFORE drawing V-lines
2. Compute V-mask pixels by subtraction
3. Insert fringe measurement loop
4. Remove dead `notTextProtection` code

**Replace lines 501-558** (from `// Build removal mask` through `final verticalMaskPixels = 0;`):

```dart
    // Build removal mask from merged line coordinates.
    removalMask = cv.Mat.zeros(rows, cols, cv.MatType.CV_8UC1);
    white = cv.Scalar(255, 0, 0, 0);

    // WHY: Draw H-lines first and count, so we can derive V by subtraction.
    // FROM SPEC: "Count H-mask pixels after drawing H-lines but BEFORE drawing V-lines"
    for (final line in mergedH.lines) {
      cv.Point? p1;
      cv.Point? p2;
      try {
        p1 = cv.Point(line.x1, line.y1);
        p2 = cv.Point(line.x2, line.y2);
        cv.line(removalMask, p1, p2, white, thickness: line.thickness);
      } finally {
        p2?.dispose();
        p1?.dispose();
      }
    }

    // FROM SPEC: "Count H-mask pixels after drawing H-lines but BEFORE drawing V-lines (for H/V tracking)"
    final horizontalMaskPixels = cv.countNonZero(removalMask);

    // Draw V-lines on removal mask
    for (final line in mergedV.lines) {
      cv.Point? p1;
      cv.Point? p2;
      try {
        p1 = cv.Point(line.x1, line.y1);
        p2 = cv.Point(line.x2, line.y2);
        cv.line(removalMask, p1, p2, white, thickness: line.thickness);
      } finally {
        p2?.dispose();
        p1?.dispose();
      }
    }

    // FROM SPEC: "Count V-mask pixels = total - H"
    final preFringeMaskPixels = cv.countNonZero(removalMask);
    final verticalMaskPixels = preFringeMaskPixels - horizontalMaskPixels;

    // ================================================================
    // Step 5b: FRINGE MEASUREMENT AND MASK EXPANSION
    // WHY: Anti-aliased grid line edges (128-199 grayscale band) cause phantom
    // OCR elements. We measure the fringe width per line and expand the mask.
    // FROM SPEC: "For each merged line (H and V): measure fringe, expand mask"
    // ================================================================
    int fringeLinesScanned = 0;
    int fringeLinesExpanded = 0;
    double totalFringeWidth = 0.0;
    double maxFringeWidth = 0.0;

    final allLines = [
      ...mergedH.lines.map((l) => (line: l, isH: true)),
      ...mergedV.lines.map((l) => (line: l, isH: false)),
    ];

    for (final entry in allLines) {
      final line = entry.line;
      final isH = entry.isH;
      fringeLinesScanned++;

      final fringe = _measureLineFringe(gray, line, isHorizontal: isH);

      if (fringe.side1 > 0 || fringe.side2 > 0) {
        fringeLinesExpanded++;
        final totalFringe = (fringe.side1 + fringe.side2).toDouble();
        totalFringeWidth += totalFringe;
        if (totalFringe > maxFringeWidth) maxFringeWidth = totalFringe;

        // FROM SPEC: "redraw line with expandedThickness = original + fringeSide1 + fringeSide2,
        // shift center by (side2-side1)/2"
        final expandedThickness = line.thickness + fringe.side1 + fringe.side2;
        final centerShift = (fringe.side2 - fringe.side1) / 2.0;

        cv.Point? p1;
        cv.Point? p2;
        try {
          if (isH) {
            final shiftedY1 = (line.y1 + centerShift).round();
            final shiftedY2 = (line.y2 + centerShift).round();
            p1 = cv.Point(line.x1, shiftedY1);
            p2 = cv.Point(line.x2, shiftedY2);
          } else {
            final shiftedX1 = (line.x1 + centerShift).round();
            final shiftedX2 = (line.x2 + centerShift).round();
            p1 = cv.Point(shiftedX1, line.y1);
            p2 = cv.Point(shiftedX2, line.y2);
          }
          cv.line(removalMask, p1, p2, white, thickness: expandedThickness);
        } finally {
          p2?.dispose();
          p1?.dispose();
        }
      }
    }

    final avgFringeWidth = fringeLinesExpanded > 0
        ? totalFringeWidth / fringeLinesExpanded
        : 0.0;

    // FROM SPEC: "maskedRemovalMask = removalMask (no text protection subtraction)"
    maskedRemovalMask = removalMask.clone();

    final maskPixels = cv.countNonZero(maskedRemovalMask);
    final fringePixelsAdded = maskPixels - preFringeMaskPixels;
```

> **NOTE:** The `notTextProtection` variable is no longer assigned here. This is the dead code removal from the spec.

#### Step 3.2.2: Remove dead `notTextProtection` declaration and disposal

**File:** `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`

**Remove** the declaration at line 318:
```dart
  cv.Mat? notTextProtection;
```

**Remove** the disposal at line 597:
```dart
    notTextProtection?.dispose();
```

> **WHY:** `notTextProtection` was computed but never read (dead code).
> **FROM SPEC:** "remove dead notTextProtection"

#### Step 3.2.3: Wire fringe metrics into _GridRemovalResult construction

**File:** `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
**Location:** The return statement constructing `_GridRemovalResult` (approx lines 575-593)

Add after `verticalMaskPixels: verticalMaskPixels,` (line 589):

```dart
      // WHY: Fringe metrics wired from measurement loop above
      fringeLinesScanned: fringeLinesScanned,
      fringeLinesExpanded: fringeLinesExpanded,
      avgFringeWidth: avgFringeWidth,
      maxFringeWidth: maxFringeWidth,
      fringePixelsAdded: fringePixelsAdded,
```

#### Step 3.2.4: Verify compilation with existing tests

```bash
pwsh -Command "flutter test test/features/pdf/extraction/stages/grid_line_remover_test.dart"
```

> **CRITICAL:** All existing tests must pass. The `horizontalMaskPixels` and `verticalMaskPixels` now have real values instead of hardcoded 0, which is fine because existing assertions only check `isA<int>()`.

---

## Phase 4: Update Existing Tests

### 4.1 Add fringe metric assertions to grid_line_remover_test.dart

**Agent:** `qa-testing-agent`

#### Step 4.1.1: Add fringe metric key assertions to 'reports morph/hough metrics' test

**File:** `test/features/pdf/extraction/stages/grid_line_remover_test.dart`
**Location:** After `containsPair('vertical_mask_pixels', isA<int>())` (line 171)

```dart
      // WHY: Verify fringe metrics are present even when no fringe exists (synthetic binary image)
      // FROM SPEC: "5 new fringe metric fields"
      expect(pageMetrics, containsPair('fringe_lines_scanned', isA<int>()));
      expect(pageMetrics, containsPair('fringe_lines_expanded', isA<int>()));
      expect(pageMetrics, containsPair('avg_fringe_width', isA<double>()));
      expect(pageMetrics, containsPair('max_fringe_width', isA<double>()));
      expect(pageMetrics, containsPair('fringe_pixels_added', isA<int>()));
```

#### Step 4.1.2: Verify existing test assertions still hold

```bash
pwsh -Command "flutter test test/features/pdf/extraction/stages/grid_line_remover_test.dart"
```

---

## Phase 5: New Fringe-Specific Tests

### 5.1 Add fringe measurement tests

**Agent:** `qa-testing-agent`

#### Step 5.1.1: Add fringe-specific test group to grid_line_remover_test.dart

**File:** `test/features/pdf/extraction/stages/grid_line_remover_test.dart`
**Location:** Inside the outer `group('GridLineRemover', ...)`, after the last existing test (after the 'rejects pathological grid line count' test)

```dart
    // WHY: Verify that anti-aliased fringe pixels are detected and the mask is
    // expanded to cover them, which is the core behavior of this feature.
    // FROM SPEC: "Per-line fringe measured dynamically"
    test('detects and removes anti-aliased fringe pixels', () async {
      final sourceBytes = createAntiAliasedGridImage(
        horizontalYs: const [0.3, 0.6],
        verticalXs: const [0.4],
        lineThickness: 3,
        fringeWidth: 2,
      );
      final page = createTestPreprocessedPage(sourceBytes, pageIndex: 0);

      final (_, report) = await remover.remove(
        preprocessedPages: {0: page},
        gridLines: GridLines(
          pages: {
            0: GridLineResult(
              pageIndex: 0,
              horizontalLines: gl([0.3, 0.6], 3),
              verticalLines: gl([0.4], 3),
              hasGrid: true,
              confidence: 1.0,
            ),
          },
          detectedAt: DateTime.utc(2026, 3, 14),
        ),
      );

      final perPage = report.metrics['per_page'] as Map;
      final pageMetrics = perPage['0'] as Map<String, dynamic>;

      // WHY: With 2px anti-aliased fringe on each side, the fringe scanner
      // should detect and expand at least some lines.
      expect(pageMetrics['fringe_lines_scanned'], greaterThan(0),
          reason: 'Should scan all merged lines');
      expect(pageMetrics['fringe_lines_expanded'], greaterThan(0),
          reason: 'Anti-aliased lines should trigger fringe expansion');
      expect(pageMetrics['avg_fringe_width'], greaterThan(0.0),
          reason: 'Fringe width should be non-zero for anti-aliased lines');
      // FROM SPEC: "avg_fringe_width > 3.0 → rollback"
      expect(pageMetrics['avg_fringe_width'], lessThanOrEqualTo(3.0),
          reason: 'Avg fringe should stay within rollback threshold');
      expect(pageMetrics['fringe_pixels_added'], greaterThan(0),
          reason: 'Fringe expansion should add mask pixels');
    });

    // WHY: Binary (non-anti-aliased) lines should produce zero fringe — proves
    // the algorithm doesn't hallucinate fringes on clean edges.
    test('reports zero fringe for binary grid lines', () async {
      final sourceBytes = createSyntheticGridImage(
        horizontalYs: const [0.3, 0.6],
        verticalXs: const [0.4],
        lineThickness: 3,
      );
      final page = createTestPreprocessedPage(sourceBytes, pageIndex: 0);

      final (_, report) = await remover.remove(
        preprocessedPages: {0: page},
        gridLines: GridLines(
          pages: {
            0: GridLineResult(
              pageIndex: 0,
              horizontalLines: gl([0.3, 0.6], 3),
              verticalLines: gl([0.4], 3),
              hasGrid: true,
              confidence: 1.0,
            ),
          },
          detectedAt: DateTime.utc(2026, 3, 14),
        ),
      );

      final perPage = report.metrics['per_page'] as Map;
      final pageMetrics = perPage['0'] as Map<String, dynamic>;

      // WHY: Clean binary edges have no 128-199 band pixels, so no fringe.
      expect(pageMetrics['fringe_lines_expanded'], equals(0),
          reason: 'Binary lines should have no fringe to expand');
      expect(pageMetrics['avg_fringe_width'], equals(0.0),
          reason: 'No fringe means zero avg width');
      expect(pageMetrics['fringe_pixels_added'], equals(0),
          reason: 'No fringe means no extra mask pixels');
    });
```

#### Step 5.1.2: Add import for `createAntiAliasedGridImage` if not already imported

**File:** `test/features/pdf/extraction/stages/grid_line_remover_test.dart`

> **NOTE:** `createAntiAliasedGridImage` is in `test_fixtures.dart` which should already be imported. Verify the existing import covers it — the file likely imports `test_fixtures.dart` already for `createSyntheticGridImage`.

#### Step 5.1.3: Run the new tests

```bash
pwsh -Command "flutter test test/features/pdf/extraction/stages/grid_line_remover_test.dart"
```

---

## Phase 6: Contract Test Updates

### 6.1 Add fringe metric keys to contract test

**Agent:** `qa-testing-agent`

#### Step 6.1.1: Add fringe metric key checks to stage_2b6_to_2biii_contract_test.dart

**File:** `test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart`
**Location:** After `expect(pageMetrics.containsKey('vertical_mask_pixels'), isTrue);` (line 104)

```dart
      // WHY: Contract must verify fringe metrics are emitted for downstream consumers.
      // FROM SPEC: "5 new fringe metric fields"
      expect(pageMetrics.containsKey('fringe_lines_scanned'), isTrue);
      expect(pageMetrics.containsKey('fringe_lines_expanded'), isTrue);
      expect(pageMetrics.containsKey('avg_fringe_width'), isTrue);
      expect(pageMetrics.containsKey('max_fringe_width'), isTrue);
      expect(pageMetrics.containsKey('fringe_pixels_added'), isTrue);
```

#### Step 6.1.2: Run the contract test

```bash
pwsh -Command "flutter test test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart"
```

---

## Phase 7: Verification

### 7.1 Run all affected tests

**Agent:** `qa-testing-agent`

#### Step 7.1.1: Run all grid line remover tests

```bash
pwsh -Command "flutter test test/features/pdf/extraction/stages/grid_line_remover_test.dart"
```

#### Step 7.1.2: Run all contract tests

```bash
pwsh -Command "flutter test test/features/pdf/extraction/contracts/"
```

#### Step 7.1.3: Run the full PDF extraction test suite

```bash
pwsh -Command "flutter test test/features/pdf/"
```

#### Step 7.1.4: Verify no regressions in broader test suite

```bash
pwsh -Command "flutter test"
```

### 7.2 Validate success criteria

**Agent:** `pdf-agent`

#### Step 7.2.1: Review checklist

- [ ] `_measureLineFringe()` function exists and measures per-line fringe dynamically
- [ ] Removal mask is expanded by fringe measurement before inpainting
- [ ] `horizontalMaskPixels` and `verticalMaskPixels` are real counts (not hardcoded 0)
- [ ] Dead `notTextProtection` code is removed
- [ ] 5 fringe metrics emitted in per-page metric dict
- [ ] Existing tests pass with no modification to assertions (defaults handle backward compat)
- [ ] New fringe tests pass: anti-aliased image triggers expansion, binary image triggers zero
- [ ] Contract test verifies all 5 new metric keys
- [ ] No security guards removed or weakened (empty image guard, pathological count guard intact)

---

## Rollback Plan

If any of these conditions are met after integration testing:

- Springfield score drops below 105/131
- `avg_fringe_width` > 3.0 on real PDFs
- Visible text erosion in diagnostic PNGs
- New OCR artifacts from over-removal

**Action:** Revert the fringe measurement loop in `_removeGridLines()` (Phase 3.2) while keeping:
- The `_GridRemovalResult` struct fields (with zero defaults)
- The metric emission in `remove()` (will emit zeros)
- The `createAntiAliasedGridImage()` test helper (useful for future work)
- The dead code removal of `notTextProtection` (independently correct)

This gives a clean rollback that preserves the diagnostic infrastructure.

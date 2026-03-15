# Default Fringe Expansion Fallback Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Add a second-pass fallback to the fringe measurement loop so that grid lines where perpendicular sampling fails (text-adjacent lines) receive the page-level average fringe width instead of zero.
**Spec:** `.claude/specs/2026-03-14-dynamic-fringe-removal-spec.md`
**Parent Plan:** `.claude/plans/2026-03-14-dynamic-fringe-removal.md`

**Architecture:** The existing single-pass fringe loop in `_removeGridLines()` (lines 591-654) measures fringe per-line and immediately expands the mask. The change splits this into: (1) a measurement-only first pass that caches results per line, (2) computation of a page-level default fringe from successful measurements, (3) a second pass that applies the default to lines with zero measurement, then draws all expansions. Two new metric fields (`fringeLinesDefaulted`, `defaultFringeWidth`) are added to `_GridRemovalResult` and emitted in the per-page metric dict.

**Tech Stack:** Dart, opencv_dart (cv.Mat, cv.line, cv.Point)
**Blast Radius:** 1 file modified (grid_line_remover.dart), 1 test file modified (grid_line_remover_test.dart), 1 contract test modified (stage_2b6_to_2biii_contract_test.dart). Public API unchanged.

---

## Phase 1: Core Algorithm Change

### 1.1 Add new metric fields to `_GridRemovalResult`

**Agent:** `pdf-agent`

#### Step 1.1.1: Add `fringeLinesDefaulted` and `defaultFringeWidth` fields

**File:** `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
**Location:** class `_GridRemovalResult`, after `fringePixelsAdded`

Add these 2 fields:

```dart
  // WHY: Tracks how many lines received the page-level default fringe instead
  // of a direct measurement. High ratio signals text-dense pages.
  final int fringeLinesDefaulted;   // Lines where default fringe was applied (measurement was zero)
  final double defaultFringeWidth;  // The page-level default fringe width used (0.0 if not needed)
```

#### Step 1.1.2: Add constructor parameters with defaults

**File:** `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
**Location:** `const _GridRemovalResult({...})` constructor, after `this.fringePixelsAdded = 0,`

```dart
    this.fringeLinesDefaulted = 0,
    this.defaultFringeWidth = 0.0,
```

#### Step 1.1.3: Wire new metrics into per-page metric dict

**File:** `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
**Location:** `remove()` method, metric dict, after `'fringe_pixels_added': processed.fringePixelsAdded,`

```dart
          'fringe_lines_defaulted': processed.fringeLinesDefaulted,
          'default_fringe_width': processed.defaultFringeWidth,
```

Also add the same keys to the passthrough/failed metric dict, after `'fringe_pixels_added': 0,`:

```dart
          'fringe_lines_defaulted': 0,
          'default_fringe_width': 0.0,
```

### 1.2 Refactor the fringe loop into two passes

**Agent:** `pdf-agent`

#### Step 1.2.1: Replace the single-pass fringe loop with a two-pass approach

**File:** `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
**Location:** Lines 591-664 (the entire `// Step 5b: FRINGE MEASUREMENT AND MASK EXPANSION` block)

Replace with:

```dart
    // ================================================================
    // Step 5b: FRINGE MEASUREMENT AND MASK EXPANSION (TWO-PASS)
    // WHY: ~30% of grid lines have text adjacent, causing perpendicular
    // fringe samples to hit text pixels (<128) and skip. These lines get
    // zero fringe measurement, leaving anti-aliased residue that Tesseract
    // reads as "|" characters. The fix: measure all lines first, compute a
    // page-level average from successes, then apply that as fallback.
    // ================================================================
    int fringeLinesScanned = 0;
    int fringeLinesExpanded = 0;
    int fringeLinesDefaulted = 0;
    double totalFringeWidth = 0.0;
    double maxFringeWidth = 0.0;

    final allLines = [
      ...mergedH.lines.map((l) => (line: l, isH: true)),
      ...mergedV.lines.map((l) => (line: l, isH: false)),
    ];

    // --- PASS 1: Measure fringe for all lines, cache results ---
    // WHY: Cache avoids double-measuring. We need all results before we can
    // compute the page-level default for lines that got zero.
    final fringeResults = <({int side1, int side2})>[];
    double successTotal = 0.0;
    int successCount = 0;

    for (final entry in allLines) {
      fringeLinesScanned++;
      final fringe = _measureLineFringe(gray, entry.line, isHorizontal: entry.isH);
      fringeResults.add(fringe);

      if (fringe.side1 > 0 || fringe.side2 > 0) {
        final total = (fringe.side1 + fringe.side2).toDouble();
        successTotal += total;
        successCount++;
      }
    }

    // --- Compute page-level default fringe ---
    // WHY: Average of successful measurements gives a safe fallback.
    // Real-world data shows ~1.554px average. Only apply to anti-aliased pages
    // (successCount > 0 means the page HAS fringe lines).
    final defaultFringeWidth = successCount > 0
        ? successTotal / successCount
        : 0.0;
    // Convert to per-side integer (symmetric split, round up for safety)
    final defaultFringeSide = successCount > 0
        ? (defaultFringeWidth / 2.0).ceil()
        : 0;

    // --- PASS 2: Apply fringe (measured or default) and expand mask ---
    for (int i = 0; i < allLines.length; i++) {
      final entry = allLines[i];
      final line = entry.line;
      final isH = entry.isH;
      var fringe = fringeResults[i];

      // WHY: If measurement returned zero AND we have a valid page default,
      // apply the default. This covers text-adjacent lines.
      final bool usedDefault;
      if (fringe.side1 == 0 && fringe.side2 == 0 && defaultFringeSide > 0) {
        fringe = (side1: defaultFringeSide, side2: defaultFringeSide);
        usedDefault = true;
      } else {
        usedDefault = false;
      }

      if (fringe.side1 > 0 || fringe.side2 > 0) {
        fringeLinesExpanded++;
        if (usedDefault) fringeLinesDefaulted++;
        final totalFringe = (fringe.side1 + fringe.side2).toDouble();
        totalFringeWidth += totalFringe;
        if (totalFringe > maxFringeWidth) maxFringeWidth = totalFringe;

        // WHY: cv.line's actual pixel half-extent = (thickness + 1) ~/ 2. Even and
        // adjacent-odd thicknesses can map to the same half-extent (e.g., t=3 and t=4
        // both give half-extent=2), meaning naively adding fringe pixels to the thickness
        // can produce no new coverage. We compute the required half-extent for the desired
        // fringe coverage and derive the minimum thickness that achieves it.
        final maxFringeSide = math.max(fringe.side1, fringe.side2);
        final origHalfExtent = (line.thickness + 1) ~/ 2;
        final targetHalfExtent = origHalfExtent + maxFringeSide;
        final minExpandedThickness = 2 * targetHalfExtent - 1;
        final expandedThickness = math.max(
          (line.thickness + fringe.side1 + fringe.side2),
          minExpandedThickness,
        ).clamp(1, 30);
        final centerShift = ((fringe.side2 - fringe.side1) / 2.0).clamp(-_kMaxFringeScan / 2.0, _kMaxFringeScan / 2.0);

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
    final fringePixelsAdded = math.max(0, maskPixels - preFringeMaskPixels);
```

#### Step 1.2.2: Wire `fringeLinesDefaulted` and `defaultFringeWidth` into the `_GridRemovalResult` construction

**File:** `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
**Location:** The return statement constructing `_GridRemovalResult`, after `fringePixelsAdded: fringePixelsAdded,`

```dart
      fringeLinesDefaulted: fringeLinesDefaulted,
      defaultFringeWidth: defaultFringeWidth,
```

#### Step 1.2.3: Verify compilation

```bash
pwsh -Command "flutter test test/features/pdf/extraction/stages/grid_line_remover_test.dart"
```

---

## Phase 2: Test Updates

### 2.1 Add new metric assertions and tests

**Agent:** `qa-testing-agent`

#### Step 2.1.1: Add `fringe_lines_defaulted` and `default_fringe_width` to 'reports morph/hough metrics' test

**File:** `test/features/pdf/extraction/stages/grid_line_remover_test.dart`
**Location:** After `expect(pageMetrics, containsPair('fringe_pixels_added', isA<int>()));`

```dart
      expect(pageMetrics, containsPair('fringe_lines_defaulted', isA<int>()));
      expect(pageMetrics, containsPair('default_fringe_width', isA<double>()));
```

#### Step 2.1.2: Add new test -- "applies default fringe to lines blocked by text"

**File:** `test/features/pdf/extraction/stages/grid_line_remover_test.dart`
**Location:** After the 'reports zero fringe for binary grid lines' test, before the closing `});` of the outer group

```dart
    // WHY: When text pixels are adjacent to a grid line, perpendicular fringe
    // samples hit text (<128) and skip. The fallback should apply the page-level
    // average fringe to these blocked lines.
    test('applies default fringe to lines blocked by text', () async {
      final image = img.Image(width: 800, height: 1000);
      img.fill(image, color: img.ColorRgb8(255, 255, 255));

      // Draw 3 horizontal lines at y=200, 400, 600 with 2px fringe
      for (final centerY in [200, 400, 600]) {
        for (int dy = 0; dy < 3; dy++) {
          for (int x = 0; x < 800; x++) {
            image.setPixel(x, centerY + dy, img.ColorRgb8(0, 0, 0));
          }
        }
        for (int f = 0; f < 2; f++) {
          final g = 140 + (50 * f ~/ 1);
          if (centerY - 1 - f >= 0) {
            for (int x = 0; x < 800; x++) {
              image.setPixel(x, centerY - 1 - f, img.ColorRgb8(g, g, g));
            }
          }
          if (centerY + 3 + f < 1000) {
            for (int x = 0; x < 800; x++) {
              image.setPixel(x, centerY + 3 + f, img.ColorRgb8(g, g, g));
            }
          }
        }
      }

      // Paint text pixels (dark, value=50) adjacent to line at y=400 to block fringe samples
      for (int x = 0; x < 800; x++) {
        image.setPixel(x, 398, img.ColorRgb8(50, 50, 50));
        image.setPixel(x, 397, img.ColorRgb8(50, 50, 50));
        image.setPixel(x, 403, img.ColorRgb8(50, 50, 50));
        image.setPixel(x, 404, img.ColorRgb8(50, 50, 50));
      }

      final sourceBytes = Uint8List.fromList(img.encodePng(image));
      final page = createTestPreprocessedPage(sourceBytes, pageIndex: 0);

      final (_, report) = await remover.remove(
        preprocessedPages: {0: page},
        gridLines: GridLines(
          pages: {
            0: GridLineResult(
              pageIndex: 0,
              horizontalLines: [
                const GridLine(position: 0.2, widthPixels: 3),
                const GridLine(position: 0.4, widthPixels: 3),
                const GridLine(position: 0.6, widthPixels: 3),
              ],
              verticalLines: const [],
              hasGrid: true,
              confidence: 1.0,
            ),
          },
          detectedAt: DateTime.utc(2026, 3, 14),
        ),
      );

      final perPage = report.metrics['per_page'] as Map;
      final pageMetrics = perPage['0'] as Map<String, dynamic>;

      expect(pageMetrics['fringe_lines_defaulted'], greaterThan(0),
          reason: 'Text-blocked line should receive default fringe');
      expect(pageMetrics['default_fringe_width'], greaterThan(0.0),
          reason: 'Page-level default should be computed from successful lines');
      expect(pageMetrics['fringe_lines_expanded'],
          equals(pageMetrics['fringe_lines_scanned']),
          reason: 'All lines should be expanded (measured + defaulted)');
    });
```

> **NOTE:** Verify `import 'package:image/image.dart' as img;` is present at top of test file.

#### Step 2.1.3: Add new test -- "no default fringe when all measurements succeed"

**File:** `test/features/pdf/extraction/stages/grid_line_remover_test.dart`
**Location:** After the test added in Step 2.1.2

```dart
    test('no default fringe when all measurements succeed', () async {
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

      expect(pageMetrics['fringe_lines_defaulted'], equals(0),
          reason: 'No lines should need the default when all measure successfully');
      expect(pageMetrics['default_fringe_width'], greaterThan(0.0),
          reason: 'Default should be computed from successful measurements');
    });
```

#### Step 2.1.4: Add new test -- "no default fringe for binary lines"

**File:** `test/features/pdf/extraction/stages/grid_line_remover_test.dart`
**Location:** After the test added in Step 2.1.3

```dart
    test('no default fringe for binary (non-anti-aliased) lines', () async {
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

      expect(pageMetrics['fringe_lines_defaulted'], equals(0),
          reason: 'Binary lines have no fringe; nothing to default');
      expect(pageMetrics['default_fringe_width'], equals(0.0),
          reason: 'No successful measurements means default is 0.0');
    });
```

#### Step 2.1.5: Update contract test with new metric keys

**File:** `test/features/pdf/extraction/contracts/stage_2b6_to_2biii_contract_test.dart`
**Location:** After `expect(pageMetrics.containsKey('fringe_pixels_added'), isTrue);`

```dart
      expect(pageMetrics.containsKey('fringe_lines_defaulted'), isTrue);
      expect(pageMetrics.containsKey('default_fringe_width'), isTrue);
```

---

## Phase 3: Verification

### 3.1 Run all affected tests

**Agent:** `qa-testing-agent`

#### Step 3.1.1: Run grid_line_remover_test.dart

```bash
pwsh -Command "flutter test test/features/pdf/extraction/stages/grid_line_remover_test.dart"
```

#### Step 3.1.2: Run contract tests

```bash
pwsh -Command "flutter test test/features/pdf/extraction/contracts/"
```

#### Step 3.1.3: Run full PDF test suite

```bash
pwsh -Command "flutter test test/features/pdf/"
```

#### Step 3.1.4: Run full test suite

```bash
pwsh -Command "flutter test"
```

### 3.2 Validate success criteria

**Agent:** `pdf-agent`

#### Step 3.2.1: Review checklist

- [ ] First pass measures all lines and caches results (no double measurement)
- [ ] Page-level default computed as mean of successful measurements
- [ ] Second pass applies default to lines with zero measurement only when `defaultFringeSide > 0`
- [ ] `fringeLinesDefaulted` and `defaultFringeWidth` added to `_GridRemovalResult`
- [ ] Both new metrics emitted in per-page metric dict (processed AND passthrough dicts)
- [ ] Existing tests pass unchanged (backward compatible)
- [ ] New test: text-blocked lines receive default fringe (defaulted count > 0)
- [ ] New test: all-success pages have zero defaulted count
- [ ] New test: binary pages have zero default fringe width
- [ ] Contract test verifies both new metric keys
- [ ] No security guards removed or weakened

---

## Rollback Plan

If any of these conditions are met after integration testing:

- Springfield score drops below 105/131
- `avg_fringe_width` > 3.0 on real PDFs
- Visible text erosion in diagnostic PNGs
- New OCR artifacts from over-removal on text-adjacent lines

**Action:** Revert the second pass (the `if (fringe.side1 == 0 && fringe.side2 == 0 && defaultFringeSide > 0)` block and the `fringeLinesDefaulted` / `defaultFringeWidth` tracking) while keeping:
- The first-pass caching structure (independently cleaner than single-pass)
- The `_GridRemovalResult` struct fields (with zero defaults)
- The metric emission in `remove()` (will emit zeros)

This gives a clean rollback that preserves the measurement caching improvement.

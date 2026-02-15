# Phase 1 Implementation Plan: GridLines Model + GridLineDetector Stage

**Parent Plan**: `2026-02-14-grid-line-detection-row-ocr.md`
**Phase**: 1 of 4
**Created**: 2026-02-14

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Stage naming | `GridLineDetector` (plain, no V2) | New stage, no V1 predecessor |
| Isolate usage | `compute()` per page | Performance — 300 DPI pixel scanning is CPU-heavy |
| Return type | `GridLines` wrapper class | Convenience getters (`gridPages`/`nonGridPages`) pay off in Phases 2-3 |
| Serialization | `toMap()`/`fromMap()` included | Needed for Phase 4 fixture generation |
| Test coverage | Core + edge + multi-page (~12-15 tests) | Thorough foundation — this stage feeds all downstream improvements |
| Fixture gen map | Include in Phase 1 | Entry added now, fixture generated in Phase 4 |
| Diagnostic test | Add grid line stage to stage trace | Loads `springfield_grid_lines.json`, prints per-page analysis |
| Mock stage | `MockGridLineDetector` in mock_stages.dart | Needed by pipeline + re-extraction loop tests |
| Benchmark | Fixture diagnostic only | Full pipeline benchmark runs automatically in Phase 4 |

---

## Files to Create (3)

### 1. `lib/features/pdf/services/extraction/models/grid_lines.dart`

**GridLineResult** (per-page result):
```
Fields:
  pageIndex: int
  horizontalLines: List<double>  // normalized Y positions, sorted
  verticalLines: List<double>    // normalized X positions, sorted
  hasGrid: bool                  // true if >= 3 horizontal AND >= 2 vertical
  confidence: double             // 1.0 if hasGrid, 0.0 otherwise

Methods:
  const constructor
  copyWith()
  toMap() → Map<String, dynamic>
  fromMap(Map<String, dynamic>) → GridLineResult (factory)
  toString()
```

**GridLines** (document-level wrapper):
```
Fields:
  pages: Map<int, GridLineResult>
  detectedAt: DateTime

Getters:
  gridPages → List<int>      // page indices where hasGrid == true
  nonGridPages → List<int>   // page indices where hasGrid == false

Methods:
  const constructor
  toMap() → Map<String, dynamic>
  fromMap(Map<String, dynamic>) → GridLines (factory)
  toString()
```

Pattern: Immutable, `final` fields, `const` constructor. Matches existing models (StageReport, DetectedRegions).

### 2. `lib/features/pdf/services/extraction/stages/grid_line_detector.dart`

**GridLineDetector** class:
```
Constants:
  kDarkPixelThreshold = 128      // luminance below this = dark
  kHorizontalCoverage = 0.60     // >60% of row width dark = horizontal line
  kVerticalCoverage = 0.40       // >40% of bounded height dark = vertical line
  kMinHorizontalLines = 3        // minimum H lines for hasGrid
  kMinVerticalLines = 2          // minimum V lines for hasGrid
  kMinLineSpacing = 0.005        // 0.5% page height minimum between lines
  kPageMargin = 0.05             // skip top/bottom 5% of page

Main method:
  Future<(GridLines, StageReport)> detect({
    required Map<int, PreprocessedPage> preprocessedPages,
  })

Algorithm per page (runs in compute() isolate):
  1. Decode enhancedImageBytes via img.decodeImage()
  2. Horizontal scan: For each pixel row, count dark pixels (luminance < 128).
     If >60% of width is dark → part of horizontal line.
     Cluster adjacent dark rows → single line at cluster center Y.
     Normalize Y to 0.0-1.0.
  3. Vertical scan: Only within vertical extent of first-to-last horizontal line.
     For each pixel column, count dark pixels.
     If >40% of bounded height is dark → vertical line.
     Cluster + normalize X to 0.0-1.0.
  4. Filter: skip lines in top/bottom 5%, enforce min spacing (0.5% page height)
  5. hasGrid = horizontalLines.length >= 3 && verticalLines.length >= 2

Isolate structure:
  - Top-level _detectGridLinesIsolate() function
  - _GridLineParams class for isolate input
  - _GridLinePageResult class for isolate output
  - Uses compute() per page (matches ImagePreprocessorV2 pattern)

StageReport:
  stageName: StageNames.gridLineDetection
  inputCount: preprocessedPages.length
  outputCount: pages with hasGrid == true
  excludedCount: pages with hasGrid == false
  metrics: {
    'total_horizontal_lines': int,
    'total_vertical_lines': int,
    'grid_pages': int,
    'non_grid_pages': int,
  }
```

### 3. `test/features/pdf/extraction/stages/stage_2b_grid_line_detector_test.dart`

Synthetic image generation using `image` package. See Test Plan below.

---

## Files to Modify (6)

### 4. `lib/features/pdf/services/extraction/stages/stage_names.dart`

Add:
```dart
static const gridLineDetection = 'grid_line_detection';
```

### 5. `lib/features/pdf/services/extraction/models/models.dart`

Add:
```dart
export 'grid_lines.dart';
```

### 6. `lib/features/pdf/services/extraction/stages/stages.dart`

Add:
```dart
export 'grid_line_detector.dart';
```

### 7. `test/features/pdf/extraction/helpers/mock_stages.dart`

Add `MockGridLineDetector`:
```dart
class MockGridLineDetector extends GridLineDetector {
  @override
  Future<(GridLines, StageReport)> detect({
    required Map<int, PreprocessedPage> preprocessedPages,
  }) async {
    // Return no-grid result by default (hasGrid=false for all pages)
    final pages = <int, GridLineResult>{};
    for (final entry in preprocessedPages.entries) {
      pages[entry.key] = GridLineResult(
        pageIndex: entry.key,
        horizontalLines: [],
        verticalLines: [],
        hasGrid: false,
        confidence: 0.0,
      );
    }
    final gridLines = GridLines(
      pages: pages,
      detectedAt: DateTime.now(),
    );
    final report = StageReport(
      stageName: StageNames.gridLineDetection,
      elapsed: Duration.zero,
      stageConfidence: 0.0,
      inputCount: preprocessedPages.length,
      outputCount: 0,
      excludedCount: preprocessedPages.length,
      completedAt: DateTime.now(),
    );
    return (gridLines, report);
  }
}
```

### 8. `tool/generate_springfield_fixtures.dart`

Add to `stageToFilename` map:
```dart
StageNames.gridLineDetection: 'springfield_grid_lines.json',
```

Update print count from `9` to `10`.

### 9. `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`

Add new fixture load in `setUpAll`:
```dart
late Map<String, dynamic> gridLinesJson;
// ...
gridLinesJson = _loadFixture('$fixtureDir/springfield_grid_lines.json');
```

Add new test: "Stage 2B.5: Grid Line Detection analysis":
- Print per-page: hasGrid, horizontal line count, vertical line count, line positions
- Print summary: total grid pages vs non-grid pages
- Assertion: `gridLinesJson['pages']` is not null

Note: This test will skip gracefully if fixture doesn't exist yet (Phase 4 generates it).

---

## Test Plan (17 tests)

### Group: GridLineResult model (4 tests)

1. **Constructor creates valid result** — verify all fields stored correctly
2. **`hasGrid` true** — 3 horizontal + 2 vertical → `hasGrid == true`
3. **`hasGrid` false** — 2 horizontal + 2 vertical → `hasGrid == false` (below threshold)
4. **`toMap()`/`fromMap()` round-trip** — serialize, deserialize, compare all fields

### Group: GridLines wrapper (4 tests)

5. **`gridPages` getter** — 3 pages, 2 with grid → returns [pageIdx1, pageIdx2]
6. **`nonGridPages` getter** — 3 pages, 1 without grid → returns [pageIdx0]
7. **`toMap()`/`fromMap()` round-trip** — multi-page, preserves all per-page data
8. **`fromMap()` empty pages** — empty map → empty gridPages/nonGridPages

### Group: GridLineDetector — core detection (4 tests)

9. **Detects horizontal lines** — synthetic image with 5 black horizontal bars at known Y positions → returns 5 horizontal lines at correct normalized positions
10. **Detects vertical lines** — synthetic image with 3 black vertical bars between horizontal bounds → returns 3 vertical lines at correct normalized positions
11. **Detects full grid** — synthetic image with 5H + 3V lines → `hasGrid == true`, correct line count
12. **No grid on blank image** — white image → `hasGrid == false`, empty line lists

### Group: GridLineDetector — edge cases (3 tests)

13. **Page margin filter** — horizontal line at Y=2% (top margin) → filtered out
14. **Min spacing merge** — two horizontal lines 0.3% apart → merged into one
15. **StageReport metrics** — verify stageName, inputCount, outputCount, excludedCount, metrics map

### Group: GridLineDetector — multi-page (2 tests)

16. **Mixed pages** — page 0 blank (no grid), page 1 with grid → `gridPages == [1]`, `nonGridPages == [0]`
17. **Per-page independence** — page 0 has grid, page 1 has grid with different line counts → each page has independent correct results

---

## Synthetic Image Generation Helper

```dart
/// Creates a test image with grid lines at specified positions.
/// [horizontalYs] and [verticalXs] are normalized 0.0-1.0 positions.
/// [lineThickness] in pixels.
Uint8List createGridImage({
  int width = 800,
  int height = 1000,
  List<double> horizontalYs = const [],
  List<double> verticalXs = const [],
  int lineThickness = 3,
}) {
  final image = img.Image(width: width, height: height);
  img.fill(image, color: img.ColorRgb8(255, 255, 255)); // white background

  // Draw horizontal lines
  for (final y in horizontalYs) {
    final pixelY = (y * height).round();
    for (int dy = 0; dy < lineThickness; dy++) {
      final row = pixelY + dy;
      if (row >= 0 && row < height) {
        for (int x = 0; x < width; x++) {
          image.setPixel(x, row, img.ColorRgb8(0, 0, 0));
        }
      }
    }
  }

  // Draw vertical lines
  for (final x in verticalXs) {
    final pixelX = (x * width).round();
    for (int dx = 0; dx < lineThickness; dx++) {
      final col = pixelX + dx;
      if (col >= 0 && col < width) {
        for (int y = 0; y < height; y++) {
          image.setPixel(col, y, img.ColorRgb8(0, 0, 0));
        }
      }
    }
  }

  return Uint8List.fromList(img.encodePng(image));
}
```

---

## Verification

```
pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_2b_grid_line_detector_test.dart"
```

All 17 tests pass. No other existing tests should be affected (barrel exports are additive, mock is additive, fixture map entry is additive).

---

## Agent Assignment

| Task | Agent |
|------|-------|
| Model + Stage implementation | `frontend-flutter-specialist-agent` |
| Mock stage + fixture map | `frontend-flutter-specialist-agent` |
| Unit tests | `qa-testing-agent` |
| Diagnostic test update | `qa-testing-agent` |
| Code review | `code-review-agent` |

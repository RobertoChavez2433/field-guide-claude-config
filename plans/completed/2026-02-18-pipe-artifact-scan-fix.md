# Fix: Pipe Artifact Elimination — Scan Termination Fix

## Context

Pipe `|` artifacts appear in OCR output because `_scanWhitespaceInset` uses a "break on first white pixel" termination rule that fails on non-monotonic edge profiles. When `edgePos` lands on the anti-aliased fringe of a grid line (pixel value >=230 at d=0), the scan exits immediately, returning inset=0 (clamped to 1). This leaves the grid line body at d=1..6 (values 18-207) intact in the cell crop, which OCR reads as `|`.

**Why edgePos lands on the fringe**: Grid line detection uses page-wide projection averaging with r<128 threshold. The "center" is a cross-row average that may not align with the true center at any specific row. After normalization → pixel conversion → `floor()`, `edgePos` can end up 1-3px from the local dark core.

**Root cause**: The scan assumes monotonic pixel profiles (dark → white transition). Real profiles are non-monotonic: `white(d=0) → dark(d=1..6) → white(d=7+)`.

## The Fix — Single Change

**File**: `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
**Method**: `_scanWhitespaceInset` (lines 608-628)

Replace "break on first white" with "scan all depths, return furthest dark pixel + 1":

```dart
// CURRENT (breaks on first white — fails on non-monotonic profiles):
for (final perpPos in samplePositions) {
  int inset = 0;
  for (int d = 0; d < maxScanDepth; d++) {
    final scanPos = edgePos + scanDirection * d;
    int px, py;
    if (isHorizontalEdge) {
      px = perpPos.clamp(0, w - 1);
      py = scanPos.clamp(0, h - 1);
    } else {
      px = scanPos.clamp(0, w - 1);
      py = perpPos.clamp(0, h - 1);
    }
    final pixel = image.getPixel(px, py);
    if (pixel.r >= whiteThreshold) {
      break;                          // ← premature exit
    }
    inset = d + 1;
  }
  if (inset > maxInset) {
    maxInset = inset;
  }
}

// FIXED (scans all depths, finds furthest dark pixel):
for (final perpPos in samplePositions) {
  int lastDark = -1;
  for (int d = 0; d < maxScanDepth; d++) {
    final scanPos = edgePos + scanDirection * d;
    int px, py;
    if (isHorizontalEdge) {
      px = perpPos.clamp(0, w - 1);
      py = scanPos.clamp(0, h - 1);
    } else {
      px = scanPos.clamp(0, w - 1);
      py = perpPos.clamp(0, h - 1);
    }
    final pixel = image.getPixel(px, py);
    if (pixel.r < whiteThreshold) {
      lastDark = d;
    }
  }
  final inset = lastDark + 1;        // 0 if no dark pixels found
  if (inset > maxInset) {
    maxInset = inset;
  }
}
```

Also update the doc comment (lines 575-578) to reflect the new behavior.

## Why This Works

| Case | Profile | Current result | Fixed result |
|------|---------|---------------|--------------|
| A2 (pipe-producing) | white(d=0) → dark(d=1..6) → white(d=7+) | break at d=0, inset=1 | lastDark=6, inset=7 |
| A1 (non-pipe) | dark(d=0..1) → white(d=2+) | inset=2 | lastDark=1, inset=2 (unchanged) |
| Clean cell | all white | inset=1 (min clamp) | lastDark=-1, inset=0 → min clamp to 1 |

The 36 confirmed pipe artifacts are ALL A2-type failures. A1 "undersized" entries (226 total) don't produce artifacts because the pixels at d=2+ are already white (255) — the scan returns the correct inset for the visible dark extent.

## Two Root Cause Analyses Reconciled

Two independent analyses identified what appeared to be different failure modes:

**Analysis 1 (Session 368)**: Scan starts at grid line CENTER, only traverses half the line width → 226 "undersized" insets. Proposed fix: `ceil(lineWidth/2)+1` minimum floor.

**Analysis 2 (Code review)**: At specific cells, d=0 pixel is white (anti-aliased fringe), scan breaks immediately → inset clamped to 1. Confirmed with pixel-level evidence at 2 cells.

**Reconciliation**: A1 "undersized" entries are benign — the scan correctly finds all dark pixels, just fewer than the formula predicts. The actual pipe artifacts (36 total) are ALL A2-type failures where the break-on-first-white terminates prematurely. One fix (scan all depths) addresses all confirmed artifacts.

## Verification

1. `pwsh -Command "flutter test test/features/pdf/extraction/"` — full suite (858 tests) should pass
2. Regenerate Springfield fixtures — verify pipe count drops to 0 in `springfield_parsed_items.json`
3. Run scorecard diagnostic — verify no regression

## Deferred Ideas (for future consideration if pipes persist)

1. **LineWidth minimum floor**: Apply `max(scanResult, ceil(lineWidth/2) + 1)` using pre-computed `verticalLineWidths`/`horizontalLineWidths`. Geometric guarantee even if scan misses near-white fringes.

2. **Bidirectional scan**: Scan both directions from `edgePos` to dynamically compute local line width, then set inset to clear inward half. More adaptive than pre-computed widths.

3. **EdgePos alignment investigation**: Why does the projection-averaged center land 1-3px from the true center at specific rows? Page-wide averaging in `_clusterIndicesToNormalized`. Could compute per-row centers.

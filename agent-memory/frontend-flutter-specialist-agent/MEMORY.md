# Agent Memory — Frontend Flutter Specialist Agent

## Patterns Discovered

- `img.Image.getPixel(x, y).r` — use `.r` directly for grayscale pixel reading. `img.getLuminance()` is broken on 1-channel images (returns only 0.299*r when g=0, b=0).

## Gotchas & Quirks

- Static methods on a class can reference `static const` fields from that class (e.g., `_fallbackLineInsetPx`) — they don't need to be top-level functions.

## Architectural Decisions

- `TextRecognizerV2` adaptive whitespace-scan insets: `_scanWhitespaceInset` scans inward from each cell edge pixel-by-pixel, sampling at 25/50/75% along the perpendicular, returning the MAX distance (conservative). Max depth 5px, white threshold r >= 230.

## Frequently Referenced Files

- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart` — OCR cell-crop stage with whitespace-scan insets (lines 348-373, method at ~575)

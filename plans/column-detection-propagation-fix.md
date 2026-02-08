# Fix: Column Detection Propagation to Subsequent Pages

## Context

After session 313's encoding fixes, manual testing of Springfield PDF shows those fixes ARE working — but accuracy is still poor because **column detection fails on pages 2-5**. Page 1 gets 83% confidence header-based detection; pages 2-5 get 0% confidence fallback ratios, causing unit+quantity merging ("FT15", "EA48", etc.).

## Root Cause Chain (3 bugs)

### Bug 1: Per-page detection always produces "wrong but non-empty" columns
**File**: `table_extractor.dart:862`

`_detectColumnsPerPage()` passes `headerRowElements: <OcrElement>[]` for every page. With no headers and no gridlines, `HeaderColumnDetector` falls back to standard ratios (6 columns at 0% confidence). These columns are wrong but non-empty.

### Bug 2: Fallback comparison never triggers
**File**: `table_extractor.dart:873`

```dart
perPage[pageIdx] = detected.columns.isNotEmpty ? detected : fallback;
```

Since standard ratio fallback always produces 6 columns, `isNotEmpty` is always true. The good global result (83%) is never used.

### Bug 3: Anchor correction skips identity corrections
**File**: `table_extractor.dart:971`

The anchor system computes per-page corrections (offset/scale) and would project global boundaries onto each page. But when pages have similar X positions to the reference (identity correction: offset ≈ 0, scale ≈ 1.0), it `continue`s and leaves the bad 0% fallback ratios in place.

```dart
if (correction == null || correction.isIdentity) {
  continue;  // Skips this page, leaving bad per-page result!
}
```

### Pipeline Order
```
1. _detectColumns() [GLOBAL]
   → Header detection (83% on page 1)
   → Anchor correction: computes per-page offsets, stores in pageCorrections
   → Returns: ColumnBoundaries(columns=[5 good], confidence=0.83, pageCorrections={...})

2. _detectColumnsPerPage() [PER-PAGE]
   → For each page: detectColumns(headerElements: []) → 0% fallback (6 wrong columns)
   → Line 873: isNotEmpty? detected : fallback → ALWAYS picks 0% result  ← BUG 2
   → _bootstrapWeakPages(): no strong line-detected pages → no-op
   → _applyAnchorCorrectionsToPerPage(): skips identity corrections → no-op  ← BUG 3
```

## Fix

Two minimal changes, both in `table_extractor.dart`:

### Change 1: Fix fallback comparison (line 873)

Replace `isNotEmpty` with confidence comparison so the good global result wins over 0% fallback.

**Current**:
```dart
perPage[pageIdx] = detected.columns.isNotEmpty ? detected : fallback;
```

**Fix**:
```dart
// Use per-page result only if it's better than the global fallback.
// Standard ratio fallback (0% confidence) should never beat a real header detection.
perPage[pageIdx] = detected.confidence > fallback.confidence ? detected : fallback;
```

### Change 2: Fix identity correction skip (line 969-973)

When corrections are identity, still use the global reference boundaries instead of leaving the bad per-page result.

**Current**:
```dart
for (var pageIdx = start; pageIdx <= end; pageIdx++) {
  final correction = reference.pageCorrections[pageIdx];
  if (correction == null || correction.isIdentity) {
    continue;
  }
  perPage[pageIdx] = _projectReferenceBoundariesToPage(reference, correction, pageIdx);
}
```

**Fix**:
```dart
for (var pageIdx = start; pageIdx <= end; pageIdx++) {
  final correction = reference.pageCorrections[pageIdx];
  if (correction == null) continue;

  if (correction.isIdentity) {
    // Identity correction: no offset needed, but still use reference boundaries
    // if they're better than the current per-page result.
    final current = perPage[pageIdx];
    if (current != null && current.confidence < reference.confidence) {
      perPage[pageIdx] = reference;
    }
    continue;
  }

  perPage[pageIdx] = _projectReferenceBoundariesToPage(reference, correction, pageIdx);
}
```

## Why This Is Sufficient

- **Change 1** makes `_detectColumnsPerPage` use the global 83% result for any page where per-page detection didn't beat it. This alone fixes the 0% fallback problem.
- **Change 2** ensures the anchor correction pass doesn't accidentally leave stale results when corrections are identity. This is a safety net for cases where Change 1's result gets overwritten.
- **No model changes** needed. No new methods. No changes to test fixtures.
- **The ~20px X shifts** are exactly what the anchor system handles — it computes offset/scale per page. If corrections are non-identity (offset > 0.01), `_projectReferenceBoundariesToPage` already adjusts boundaries correctly. If they're identity, Change 2 now propagates the reference directly.

## Files Modified
- `lib/features/pdf/services/table_extraction/table_extractor.dart` — 2 changes (~10 lines total)

## Verification
1. `pwsh -Command "flutter test test/features/pdf/table_extraction/"` — table extraction tests
2. `pwsh -Command "flutter test test/features/pdf/"` — full PDF test suite
3. Manual test: Import Springfield PDF, verify pages 2-5 have correct unit/quantity separation

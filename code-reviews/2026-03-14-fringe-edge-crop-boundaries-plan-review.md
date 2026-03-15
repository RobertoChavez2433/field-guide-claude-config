# Plan Review: Fringe-Edge Crop Boundaries

## Security Review: APPROVE
No security concerns. All bounds clamped, no network surface, defense-in-depth on negative crops.

## Code Review: REJECT → FIXED
5 issues identified and fixed in plan:

### Fixed Issues
1. **`_fallbackLines` loop rewrite** — Plan now shows explicit `for(int di=0; ...)` loop with `detectorIndex` threading
2. **`_GridRemovalResult` const constructor** — Plan notes records in Maps aren't const-capable, instructs to drop `const` if needed
3. **Misleading "parallel indexing" comment** — Changed to correctly reference `detectorIndex` field
4. **`remove()` early-return paths** — Added explicit instruction to search ALL `return (` statements
5. **`GridLines` type wrapping** — Added `GridLines(pages: enrichedGridLines, detectedAt: gridLines.detectedAt)` wrapper

### Addressed Suggestions
- Added Step 4.0 to update `_computeCellCrops` docblock (suggestion 8)
- Suggestion 5 (inset math bounds): noted, max 37px is safe
- Suggestion 7 (stronger fringe test): noted for implementation

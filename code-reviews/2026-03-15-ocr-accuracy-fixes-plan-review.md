# OCR Accuracy Fixes — Plan Review

## Security Review: APPROVE
- Zero security concerns — pure OCR pipeline changes
- 2 LOW pre-existing notes (no input length guard on _scoreCandidate, regex not pre-compiled)

## Code Review: Initially REJECT → Findings addressed in plan v2

### CRITICAL (Fixed)
1. **Fix 2 — Wrong layer**: `UnitRegistry.normalize` already uppercases. Real issue is `pipeline_comparator.dart:216` using case-sensitive `==`. Fixed: two-layer approach (belt-and-suspenders uppercase in `_cleanUnitText` + case-insensitive unit comparison in `pipeline_comparator.dart`).

### HIGH (Fixed)
2. **Fix 5 — Variable name**: `policy` → `columnPolicy` at call site. Fixed in plan.
3. **Fix 5 — kTargetDpi references**: All occurrences in `computeScaleFactor` enumerated. Fixed in plan.
4. **Fix 5 — Field declaration**: Clarified placement in class body alongside `_cropUpscaler`. Fixed in plan.

### MEDIUM (Noted)
5. Fix 6 — score floor vs _selectBestCandidate blank handling: noted for implementing agent to verify
6. Fix 3 — docstring at lines 1170-1172 also mentions fringe: noted for implementing agent
7. Fix 4 — median from all fragments including short ones: acknowledged risk, not a blocker
8. Fix 1 — missing mixed-artifact test case: noted

### LOW (Noted)
- Fix 3: existing tests with fringe assertions need identification
- Phase 5: focus-test-window.ps1 is a NOTE not a required step
- Fix 5: test strategy for column-selective upscaler needs concrete mock approach

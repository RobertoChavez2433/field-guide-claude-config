# Code Review: Column Semantic Mapping Fix (Session 348-349)

**Date**: 2026-02-15
**Reviewer**: code-review-agent + manual fixes
**Files**: column_detector_v2.dart, row_parser_v2.dart, column_map.dart, extraction_patterns.dart

## Plan Completion

| Phase | Status | Location |
|-------|--------|----------|
| 1a: Margin detection | DONE | column_detector_v2.dart:467-478 |
| 1b: Anchor-relative inference | DONE | column_detector_v2.dart:480-528 |
| 1c: 3-row content validation | DONE | column_detector_v2.dart:530-587 |
| 1d: Filter margins from output | DONE | column_detector_v2.dart:589-608 |
| 2: Remove position fallback | DONE | row_parser_v2.dart:404-436 |
| 2: Missing-column warnings | DONE | row_parser_v2.dart:424-434 |
| Bug fix: copyWith sentinel | DONE | column_map.dart:5,31,38 |

## Issues Found & Fixed (Session 349)

### 1. Dead-code logic in description inference (FIXED)
- `c.headerText == null && c.headerText != '_margin'` — second check always true when first is true
- Removed redundant `_margin` guard (margins already have non-null headerText from Phase 1a)

### 2. DRY violation: third item-number regex (FIXED)
- Local `RegExp(r'^\d+[A-Za-z]?$')` diverged from ExtractionPatterns
- Added `ExtractionPatterns.itemNumberLoose` combining decimals + alpha suffixes
- Column detector now uses shared pattern

### 3. Redundant margin check after filtering (FIXED)
- `validSemantics` filter checked `_margin` on already-filtered `nonMarginColumns`
- Simplified to just `c.headerText != null`

## Remaining Suggestions (Not Addressed)

1. **Row parser semantic name coupling**: `HeaderKeywords.identifyColumn()` called with semantic names ('itemNumber') that happen to match keywords by coincidence. Could be fragile if semantic names change. Low risk.

2. **Content validation on OCR-confirmed columns**: Validates all itemNumber/unit columns, not just inferred ones. Could revert valid OCR-confirmed headers with unusual data. Low risk — OCR-confirmed columns unlikely to have 2/3+ non-matching data.

3. **Shared sentinel utility**: Two files define identical `_sentinel` constants. Minor DRY improvement.

## Tests

- 59 column detector tests: ALL PASS
- 324 stage tests: ALL PASS (6 skipped = fixture-dependent)

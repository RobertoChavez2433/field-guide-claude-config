# Header Detection Hardening Plan

**Created**: 2026-02-04 | **Session**: 286
**Goal**: Fix false-positive header detection that mistakes boilerplate text for table headers
**Target**: General-purpose fix - NO PDF-specific rules

## Problem Statement

TableLocator identifies header rows by counting keyword matches (minimum 2 categories). Boilerplate sentences like "Bidder will perform the following Work at the indicated unit prices:" contain keywords and get falsely identified as the table header, while the REAL header below it gets skipped.

**Root Causes:**
1. `_containsAny()` uses substring matching - "BIDDER" matches "BID", "PRICES" matches "PRICE"
2. No keyword density check - 2 keywords in a 12-word sentence scores same as 6 keywords in a 6-word header
3. No structural validation that data rows follow a candidate header

## Recommended Approach: Hybrid (Density + Word Boundary + Data Row Confirmation)

Three layers of defense, each independently valuable:

### Layer 1: Word-Boundary Keyword Matching (Fixes substring false positives)
### Layer 2: Keyword Density Gating (Rejects keyword-sparse sentences)
### Layer 3: Data-Row Lookahead Confirmation (Structural verification)

## Implementation Steps

### Step 1: Fix `_containsAny` in `table_locator.dart` (word-boundary matching)

**File:** `lib/features/pdf/services/table_extraction/table_locator.dart`

Replace substring `.contains()` with word-boundary-aware matching:

```dart
bool _containsAny(String text, List<String> patterns) {
  for (final pattern in patterns) {
    if (pattern.contains(' ')) {
      // Multi-word patterns: use contains (already specific enough)
      if (text.contains(pattern)) return true;
    } else {
      // Single-word patterns: use word boundary matching
      final regex = RegExp(r'\b' + RegExp.escape(pattern) + r'\b');
      if (regex.hasMatch(text)) return true;
    }
  }
  return false;
}
```

**Impact:** "BIDDER" no longer matches "BID", "PRICES" no longer matches "PRICE". Alone this drops the boilerplate from 3 keyword matches to 1.

### Step 2: Create `_HeaderMatchResult` class

```dart
class _HeaderMatchResult {
  final int keywordCount;
  final double keywordDensity;
  final int matchedCharCount;
  final int totalCharCount;

  _HeaderMatchResult({
    required this.keywordCount,
    required this.keywordDensity,
    required this.matchedCharCount,
    required this.totalCharCount,
  });

  bool get isLikelyHeader =>
    (keywordCount >= 3 && keywordDensity >= kMinKeywordDensity) ||
    (keywordCount >= 2 && keywordDensity >= 0.70);
}
```

Dual-path threshold:
- **Path A**: 3+ keywords AND density >= 0.40 (standard headers)
- **Path B**: 2 keywords AND density >= 0.70 (minimal but keyword-dense headers)

### Step 3: Refactor `_countHeaderKeywords` to `_analyzeHeaderKeywords`

Return `_HeaderMatchResult` instead of `int`. Track matched keyword strings and their character lengths. Compute density as `matchedCharCount / totalNonWhitespaceCharCount`.

**Springfield examples:**
- Real header: "Item No. Description Unit Est. Quantity Unit Price Bid Amount" => 6 keywords, density ~0.90. PASS.
- Boilerplate: "Bidder will perform the following Work at the indicated unit prices" => After word-boundary fix: 1 keyword ("UNIT"), density ~0.06. FAIL.

### Step 4: Update header detection logic in `locateTable`

Change:
```dart
final headerKeywordCount = _countHeaderKeywords(row);
final isHeader = headerKeywordCount >= kMinHeaderKeywords;
```
To:
```dart
final headerMatch = _analyzeHeaderKeywords(row);
final isHeader = headerMatch.isLikelyHeader;
```

Same change for multi-row detection combining.

### Step 5: Add data-row lookahead confirmation

After a header candidate is found, scan forward 1-5 rows to verify at least one data row exists:

```dart
if (isHeader || isMultiRowHeader) {
  bool confirmedByDataRow = false;
  final lookAhead = isMultiRowHeader ? 2 : 1;
  for (var j = i + lookAhead; j < rows.length && j < i + lookAhead + 5; j++) {
    if (_looksLikeDataRow(rows[j])) {
      confirmedByDataRow = true;
      break;
    }
  }
  if (!confirmedByDataRow && tableStartPage == null) {
    continue; // Skip false positive - no data rows follow
  }
}
```

### Step 6: Tighten keyword lists

In `table_locator.dart`:
- Remove `'BID'` from `_amountKeywords` (keep `'BID AMOUNT'`) - too many false positives
- Remove bare `'NO'` from `_itemKeywords` (keep `'NO.'`) - too common in regular text

Mirror changes in `header_column_detector.dart` if lists are duplicated.

### Step 7: Fix `_containsAny` in `header_column_detector.dart`

Apply same word-boundary fix to `header_column_detector.dart` `_containsAny` method.

### Step 8: Add constants

```dart
static const double kMinKeywordDensity = 0.40;
static const int kHeaderLookaheadRows = 5;
```

### Step 9: Update tests

**File:** `test/features/pdf/table_extraction/table_locator_test.dart`

New tests:
1. Boilerplate rejection: "Bidder will perform..." must NOT be detected as header
2. Keyword density: 2 keywords in 15-word sentence rejected
3. Real header acceptance: "Item No. Description Unit..." passes with high density
4. Minimal header with high density: "Unit | Qty" (2 keywords, 100% density) still accepted
5. Data-row lookahead: header-like row with no following data rows rejected
6. Update existing 2-keyword test for new gating

### Step 10: Integration testing

Run full test suite and verify Springfield PDF extraction improves.

## Sequencing

```
Step 1 (word boundary)  ──┐
Step 6 (tighten lists)  ──┤── Independent, parallel
Step 7 (fix HCD)        ──┘
         │
Step 2 (result class)
         │
Step 3 (refactor method)
         │
Step 4 (update logic)
         │
Step 5 (data-row lookahead)
         │
Step 8 (constants)
         │
Step 9 (tests)
         │
Step 10 (integration)
```

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Regression on other PDFs | Low | Word-boundary fix only makes matching more precise |
| Minimal headers rejected | Low | Dual-path threshold allows 2 keywords at 70% density |
| Performance | Negligible | RegExp on short strings, 5-row lookahead |
| Edge cases | Low | Fallback data-row pattern detection remains as safety net |

## Files to Modify

| File | Changes |
|------|---------|
| `lib/features/pdf/services/table_extraction/table_locator.dart` | Steps 1-6, 8 |
| `lib/features/pdf/services/table_extraction/header_column_detector.dart` | Steps 6-7 |
| `test/features/pdf/table_extraction/table_locator_test.dart` | Step 9 |

## Also Fix (Pre-existing): 18 Failing PDF Tests

Separate from this plan, there are 18 pre-existing test failures across 6 files:
- `cell_extractor_test.dart` (4) - Column assignment tolerance changes
- `post_process_splitter_test.dart` (4) - extractUnitFromDescription not stripping units
- `post_process_engine_test.dart` (5) - Cascading from splitter + warning filtering
- `post_process_consistency_test.dart` (1) - handleLumpSum null guard
- `post_process_numeric_test.dart` (1) - parseCurrency too permissive
- `springfield_integration_test.dart` (3) - Zero items extracted (cascading from header issue)

These should be fixed AFTER the header detection hardening, as the Springfield integration tests depend on the pipeline working correctly.

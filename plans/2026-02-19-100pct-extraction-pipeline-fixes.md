# Plan: 100% Extraction Completion — Pipeline Fixes

**Created**: 2026-02-19 (Session 393)
**Goal**: Fix 2 remaining GT value errors (items 100, 121) and clear 2 LOW scorecard signals — by hardening the pipeline, not bending tests.
**Current**: 129/131 correct values, 63 OK / 2 LOW / 0 BUG (66 metrics)
**Target**: 131/131 correct values, ~73 OK / 0-1 LOW / 0 BUG (~76 metrics)

---

## Phase 1: Math-Anchored Backsolve (Stage 5 — Post-Processing)

**Impact**: Fixes both value errors (items 100, 121). Highest ROI fix.

### Problem
When `qty × unitPrice ≠ bidAmount`, the pipeline currently **warns but never repairs**. Both errors have correct bidAmount and quantity — only unitPrice is wrong from OCR corruption.

| Item | qty | bidAmount (correct) | unitPrice (wrong) | backsolve: bid/qty | GT |
|------|-----|--------------------|--------------------|---------------------|-----|
| 100 | 410 | $45,100.00 | $119.00 | **$110.00** | $110.00 |
| 121 | 10,000 | $10,000.00 | null→$10.00 | **$1.00** | $1.00 |

### Implementation

**File**: `lib/features/pdf/services/extraction/stages/post_processor_v2.dart`
**Insert at**: Lines 705-718 of `_applyConsistencyRules`, replacing the warn-only math check with conditional repair.

#### A1. Add confidence constant
**File**: `lib/features/pdf/services/extraction/pipeline/confidence_model.dart`
- Add `static const double kAdjMathBacksolve = -0.03;` to `ConfidenceConstants`
- Rationale: light penalty (-0.03) because the backsolve is mathematically exact when bidAmount and qty are both correct. Lighter than `kAdjPriceInferred = -0.05` because backsolve has two known-good inputs vs inference which has one.

#### A2. Add backsolve logic in `_applyConsistencyRules`
**File**: `post_processor_v2.dart`, lines 705-718

Replace the warn-only block with:

```dart
// After inference fills missing fields, check math consistency
if (current.quantity != null && current.unitPrice != null && current.bidAmount != null) {
  final calculated = roundCurrency(current.quantity! * current.unitPrice!);
  final diff = (calculated! - current.bidAmount!).abs();

  if (diff > 0.02) {
    // Attempt backsolve: derive unitPrice from bidAmount / quantity
    final backsolved = roundCurrency(current.bidAmount! / current.quantity!);

    if (backsolved != null && backsolved > 0) {
      final backsolvedCalc = roundCurrency(current.quantity! * backsolved);
      final backsolvedDiff = (backsolvedCalc! - current.bidAmount!).abs();

      if (backsolvedDiff <= 0.02) {
        // Backsolve produces exact math — apply repair
        final before = {'unitPrice': current.unitPrice};
        current = current.copyWith(unitPrice: backsolved);
        repairs.add(RepairEntry(
          itemId: current.itemNumber ?? '',
          type: RepairType.mathValidation,
          before: before,
          after: {'unitPrice': backsolved},
          confidenceAdjustment: ConfidenceConstants.kAdjMathBacksolve,
          reason: 'Math backsolve: qty(${current.quantity}) × price($backsolved) = '
                  'amount(${current.bidAmount}). Original OCR price was ${before['unitPrice']}.',
        ));
        confidenceAdj += ConfidenceConstants.kAdjMathBacksolve;
      } else {
        // Backsolve doesn't produce exact math either — warn only
        warnings.add('Math validation: calculated amount (\$$calculated) does not match '
            'bid amount (\$${current.bidAmount}) for item ${current.itemNumber}');
      }
    }
  }
}
```

#### A3. Guard conditions
- Only backsolve when `quantity > 0` (avoid division by zero)
- Only apply when backsolve result matches bidAmount within $0.02 tolerance
- Only override unitPrice (not bidAmount) — bidAmount is the more reliable field (OCR reads it from its own column, not derived)
- `RepairType.mathValidation` already exists in the enum at `processed_items.dart:17`

#### A4. Downstream effect
- `_validateMath` (batch detection at line 1004) will now see the repaired item as `exact` or `withinRounding`
- `_recalculateConfidence` will NOT apply the ×0.60 major-discrepancy penalty
- Net confidence improvement: item 100 goes from ~0.768 to ~0.93; item 121 goes from ~0.653 to ~0.90

#### A5. Fixture snapshot
The `StageNames.postValidate` snapshot is emitted after `_applyConsistencyRules`. The backsolve repair will be visible in this fixture — no new snapshot needed.

---

## Phase 2: Zero-Confidence Sentinel (Stage 4E.5 — Field Confidence)

**Impact**: Clears B2 LOW signal. Fixes phantom 0.0 confidence on 3 correctly-parsed cells.

### Problem
Items 12, 38, 73 have `ocr_confidence: 0.0` on fields with correct text. The weighted geometric mean formula computes `exp(0.50 × ln(0.01)) = 0.10` for these, dragging bidAmount mean from ~0.93 to 0.887.

### Root cause
`TesseractEngineV2` at line 207-209: when `x_wconf` attribute is absent from HOCR span, confidence defaults to `0.0`. This is correct behavior from the OCR layer — the issue is that the confidence scorer treats 0.0 the same as "very low confidence" when it actually means "confidence not reported."

### Implementation

**File**: `lib/features/pdf/services/extraction/stages/field_confidence_scorer.dart`
**Location**: `_scoreField()` method, around line 292, before `_weightedGeometric` is called.

#### B1. Add sentinel detection
```dart
// Before calling _weightedGeometric:
double effectiveOcrConfidence = ocrConfidence;

// Sentinel: if OCR reported 0.0 confidence but the cell has valid parsed text
// and a standard interpretation pattern, treat as "confidence unknown" not "confidence zero"
if (ocrConfidence == 0.0 && interpretedValue != null && interpretedValue.isNotEmpty) {
  effectiveOcrConfidence = 0.50; // neutral prior — unknown, not bad
  // Tag diagnostic for tracking
  diagnosticFlags.add('zero_conf_sentinel');
}
```

#### B2. Use `effectiveOcrConfidence` in the weighted geometric call
Pass `effectiveOcrConfidence` instead of raw `ocrConfidence` to `_weightedGeometric`.

#### B3. Expected effect
- Items 12, 38, 73: field score goes from 0.10 → ~0.50
- bidAmount mean rises from 0.887 → ~0.92-0.93
- B2 conf gap: Δ0.066 → ~Δ0.02-0.03 → falls within OK threshold (<=0.05)

---

## Phase 3: Scorecard Hardening (Stage Trace Test)

**Impact**: 3 threshold fixes + 6 high/medium priority new metrics. Catches future regressions.

### 3A. Threshold Fixes

**File**: `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`

#### C-1: Header row upper bound (line 3414)
**Current**: `stat(headerRows, 6)` — no upper bound, 17 headers shows OK
**Fix**: Replace with inline logic:
```dart
headerRows > 18 ? 'BUG' : (headerRows > 10 ? 'LOW' : stat(headerRows, 6))
```
**Rationale**: 6 pages × 1 header = 6 expected. Multi-line headers produce 17 raw rows that consolidate to 6 logical. >10 raw headers means consolidation is working harder than expected. >18 means possible misclassification.

#### C-2: Pathway denominator (line 3534)
**Current**: `rowPathwayRatio = rowPathwayDecisions / dataRows` (275/131 = 210%)
**Fix**: Change denominator to total classified rows (not just data rows):
```dart
// Before: final rowPathwayRatio = rowPathwayDecisions / dataRows;
// After:
final totalClassifiedRows = rows.length; // ~286
final rowPathwayRatio = rowPathwayDecisions / totalClassifiedRows;
```
Then 275/286 = 96% → correctly shows OK. Also add upper bound:
```dart
rowPathwayRatio > 1.50 ? 'BUG' : (rowPathwayRatio >= 0.80 ? 'OK' : ...)
```

#### C-3: OCR elements baseline (line 3322-3325)
**Current**: Expected `~1400`, threshold `> 1000`
**Fix**: Update to match stable pipeline output:
```dart
// Expected string: '~1240'
// pct denominator: 1240
// Threshold: totalElements > 1100 ? 'OK' : (totalElements > 900 ? 'LOW' : 'BUG')
```

### 3B. New Metrics (High Priority)

#### NEW-1: Per-page OCR element floor (Stage 2B-iii)
**What**: `min(perPageCounts) / avg(perPageCounts)` — ratio must stay above 0.15
**Note**: Page 0 has only 54 elements (vs 207 avg = 0.26 ratio) because it contains only 5 data rows (partial first page). This is structurally expected. Threshold must accommodate this.
**Threshold**: OK if >= 0.15, LOW if >= 0.05, BUG if < 0.05
**Implementation**:
```dart
final perPageCounts = perPage.values.map((v) => (v as num).toInt()).toList();
final avgPerPage = perPageCounts.reduce((a, b) => a + b) / perPageCounts.length;
final minPerPage = perPageCounts.reduce(min);
final minPageRatio = avgPerPage > 0 ? minPerPage / avgPerPage : 0.0;

tableRows.add([
  '2B-iii',
  'Min page element ratio',
  '>=0.15 of avg',
  '${minPageRatio.toStringAsFixed(2)} (min=$minPerPage, avg=${avgPerPage.toStringAsFixed(0)})',
  '${(minPageRatio * 100).toStringAsFixed(0)}%',
  minPageRatio >= 0.15 ? 'OK' : (minPageRatio >= 0.05 ? 'LOW' : 'BUG'),
  'catches single-page OCR failure',
  'p0=$minPerPage vs avg=${avgPerPage.toStringAsFixed(0)}',
]);
```

#### NEW-3: V-line count per grid page (Stage 2B.5)
**What**: Every grid page must have 6-8 V-lines (Springfield has 7 consistently — 6 column boundaries + outer edges)
**Note**: The fixture shows 7 V-lines on page 0 and 6-7 on other pages. The actual count varies slightly because outer boundary lines may or may not be detected. Use range [5, 9].
**Threshold**: OK if all pages have 5-9 V-lines, BUG if any page has < 5 or > 9
**Implementation**: Iterate `gridPagesMap` (already available at line 2493):
```dart
int vLineMin = 999;
int vLineMax = 0;
for (final entry in gridPagesMap.entries) {
  final page = Map<String, dynamic>.from(entry.value as Map);
  if (page['has_grid'] == true) {
    final vCount = (page['vertical_lines'] as List?)?.length ?? 0;
    vLineMin = min(vLineMin, vCount);
    vLineMax = max(vLineMax, vCount);
  }
}
final vLineStatus = (vLineMin >= 5 && vLineMax <= 9) ? 'OK' : 'BUG';

tableRows.add([
  '2B.5',
  'V-line count range',
  '5-9 per page',
  '$vLineMin–$vLineMax',
  '-',
  vLineStatus,
  'column boundary stability',
  'min=$vLineMin max=$vLineMax across ${gridPagesMap.length} pages',
]);
```

#### NEW-4: Per-page data row floor (Stage 4A)
**What**: Minimum data rows on any single page
**Threshold**: OK if >= 5, LOW if >= 3, BUG if < 3
**Implementation**: Compute from classified rows fixture (already iterated for type breakdown):
```dart
final pageDataCounts = <int, int>{};
for (final row in rows) {
  if (row['type'] == 'data') {
    final page = row['page_index'] as int;
    pageDataCounts[page] = (pageDataCounts[page] ?? 0) + 1;
  }
}
final minPageData = pageDataCounts.values.reduce(min);

tableRows.add([
  '4A',
  'Min page data rows',
  '>=5 per page',
  '$minPageData',
  '-',
  minPageData >= 5 ? 'OK' : (minPageData >= 3 ? 'LOW' : 'BUG'),
  'catches full-page classification failure',
  'per-page: ${pageDataCounts.entries.map((e) => "p${e.key}:${e.value}").join(", ")}',
]);
```

#### NEW-5: Boilerplate row cap (Stage 4A)
**What**: Total boilerplate-classified rows
**Threshold**: OK if <= 10, LOW if <= 20, BUG if > 20
**Current value**: 3 boilerplate rows

#### NEW-9: Absolute bidAmount/unitPrice confidence floor (Stage 4E.5)
**What**: Mean field confidence for dollar-critical fields must stay above absolute floor
**Threshold**: OK if >= 0.85, LOW if >= 0.75, BUG if < 0.75
**Implementation**: Read from field_confidence fixture summary `mean_field_confidence`:
```dart
final bidAmountConf = meanFieldConf['bidAmount'] as double? ?? 0.0;
final unitPriceConf = meanFieldConf['unitPrice'] as double? ?? 0.0;
final minDollarConf = min(bidAmountConf, unitPriceConf);

tableRows.add([
  '4E.5',
  'Dollar field conf floor',
  '>=0.85',
  '${minDollarConf.toStringAsFixed(3)} (price=${unitPriceConf.toStringAsFixed(3)}, amt=${bidAmountConf.toStringAsFixed(3)})',
  pct((minDollarConf * 100).round(), 85),
  minDollarConf >= 0.85 ? 'OK' : (minDollarConf >= 0.75 ? 'LOW' : 'BUG'),
  'absolute floor for dollar-critical fields',
  'unitPrice:${unitPriceConf.toStringAsFixed(3)} bidAmount:${bidAmountConf.toStringAsFixed(3)}',
]);
```

#### NEW-10: Post-processing repair rate (Stage 5)
**What**: `repairs / items` should stay below 20%
**Threshold**: OK if <= 20%, LOW if <= 50%, BUG if > 50%

### 3C. Update final assertions

After adding ~10 new metrics and fixing thresholds:
```dart
// Update LOW tolerance — Phase 2 sentinel should clear B2, but B1 may remain
expect(bugCount, equals(0));
expect(lowCount, lessThanOrEqualTo(2)); // keep at 2 until validated
```

After validation with regenerated fixtures, tighten:
```dart
expect(lowCount, lessThanOrEqualTo(1)); // or even 0 if all LOWs resolve
```

---

## Phase 4: Space-Collapse Defense (Stage 4D.5 — Optional/Deferred)

**Impact**: Defense-in-depth for future spaced-digit OCR errors. Lower priority because Phase 1 backsolve already corrects the values.

### Problem
When OCR produces `$1 19.00` (space in dollar amount), the `unrecognized` pattern fallback strips `$` and spaces, concatenating to `119` — plausible but wrong.

### Implementation (if pursued)
**File**: `lib/features/pdf/services/extraction/rules/currency_rules.dart`
**Location**: Before the `_UnrecognizedCurrencyRule` catch-all (line 280)

Add a new rule `_SpaceCollapseCurrencyRule` that:
1. Detects internal spaces in dollar amounts: `^\$?\d+\s+[\d,.]+$`
2. Collapses the space and re-parses: `$1 19.00` → `$119.00`
3. Tags with pattern `space_collapse` (add to `correctionPatterns` in `interpretation_patterns.dart`)

**Risk**: Space-collapse alone produces `$119.00` not `$110.00` — it cannot recover the lost digit. The backsolve (Phase 1) is required to get the correct value. This phase only helps by producing a parseable number instead of `unrecognized`, which improves confidence scoring.

**Recommendation**: Defer to a future session. Phase 1 + 2 + 3 deliver 100% extraction without this.

---

## Implementation Order

| Phase | Description | Files Modified | Est. Complexity |
|-------|-------------|---------------|-----------------|
| 1 | Math backsolve | `post_processor_v2.dart`, `confidence_model.dart` | Medium (30 lines) |
| 2 | Zero-conf sentinel | `field_confidence_scorer.dart` | Low (10 lines) |
| 3A | Threshold fixes | `stage_trace_diagnostic_test.dart` | Low (3 line changes) |
| 3B | New metrics | `stage_trace_diagnostic_test.dart` | Medium (60 lines) |
| 3C | Assertion update | `stage_trace_diagnostic_test.dart` | Trivial |
| 4 | Space-collapse | `currency_rules.dart`, `interpretation_patterns.dart` | Deferred |

## Validation Steps

1. After Phase 1+2: Regenerate fixtures, verify items 100 and 121 now match GT
2. After Phase 3: Run stage trace test, verify 0 BUG / <=1 LOW
3. Run full extraction suite: `pwsh -Command "flutter test test/features/pdf/extraction/"` — must stay green (~850+ tests)
4. Present updated scorecard in table format for review

## Agent Assignments

| Phase | Agent | Scope |
|-------|-------|-------|
| 1 | `frontend-flutter-specialist-agent` | `post_processor_v2.dart`, `confidence_model.dart` |
| 2 | `frontend-flutter-specialist-agent` | `field_confidence_scorer.dart` |
| 3 | `qa-testing-agent` | `stage_trace_diagnostic_test.dart` |
| Validation | Orchestrator | Fixture regen + test runs |

---

## Key File References

| File | Purpose | Lines |
|------|---------|-------|
| `lib/features/pdf/services/extraction/stages/post_processor_v2.dart` | Math backsolve insert point | 705-718 |
| `lib/features/pdf/services/extraction/pipeline/confidence_model.dart` | Add `kAdjMathBacksolve` | Near line 25 |
| `lib/features/pdf/services/extraction/models/processed_items.dart` | `RepairType.mathValidation` (exists) | Line 17 |
| `lib/features/pdf/services/extraction/stages/field_confidence_scorer.dart` | Zero-conf sentinel | ~Line 292 |
| `lib/features/pdf/services/extraction/stages/field_confidence_scorer.dart` | `_weightedGeometric` formula | Lines 318-341 |
| `lib/features/pdf/services/extraction/stages/field_confidence_scorer.dart` | `_minimumFactor = 0.01` | Line 15 |
| `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart` | Scorecard test | 4362 lines |
| `stage_trace_diagnostic_test.dart` | `stat()` function | Lines 2329-2346 |
| `stage_trace_diagnostic_test.dart` | Header rows metric (C-1) | Lines 3408-3417 |
| `stage_trace_diagnostic_test.dart` | Row pathways metric (C-2) | Lines 3524-3541 |
| `stage_trace_diagnostic_test.dart` | OCR elements metric (C-3) | Lines 3319-3328 |
| `stage_trace_diagnostic_test.dart` | Final assertions | Lines 4353-4356 |
| `stage_trace_diagnostic_test.dart` | `gridPagesMap` (for V-line) | Line 2493 |

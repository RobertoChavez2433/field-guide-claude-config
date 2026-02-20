# Plan: Harden Pipeline Scorecard Metrics

## Context

The pipeline scorecard (stage trace diagnostic test) has 62 metrics tracking Springfield extraction quality. An audit revealed:
- **1 BUG**: B1 pattern alarm — `item_number_cleanup` missing from hardcoded standard patterns set
- **2 LOW**: B2 conf gap (real signal, no fix needed), B4 recovery rate (inflated by B1 bug)
- **12 silently passing metrics**: thresholds so loose they can never fail (`>0`, `>=0`)
- **7 missing coverage gaps**: GridLineRemover has zero metrics, no per-item arithmetic cross-check, etc.

This plan hardens all metrics to be **pipeline-generic** (work for any PDF), not Springfield-specific.

## Files Modified

| File | Change |
|------|--------|
| `lib/features/pdf/services/extraction/rules/interpretation_patterns.dart` | **NEW** — Standalone utility with `standardPatterns` and `correctionPatterns` static sets |
| `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart` | All metric hardening changes (bulk of work) |

## Implementation

### Part 1: Fix B1/B4 — Dynamic Standard Patterns

**New file**: `lib/features/pdf/services/extraction/rules/interpretation_patterns.dart`

```dart
/// Single source of truth for interpretation pattern classification.
/// Standard = expected primary patterns (not OCR corrections).
/// Correction = OCR error recovery or fallback patterns.
class InterpretationPatterns {
  InterpretationPatterns._();

  static const Set<String> standardPatterns = {
    // Currency
    'standard_us',
    'no_comma_us',
    'parenthetical_negative',
    // Quantity
    'comma_grouped',
    'space_grouped',
    'plain_numeric',
    // Item number
    'item_number_cleanup',
    // Text
    'text_pass_through',
  };

  static const Set<String> correctionPatterns = {
    'corrupted_symbol',
    'missing_decimals',
    'european_periods',
    'unrecognized',
  };

  /// Returns true if the pattern indicates OCR correction was needed.
  /// Handles compound patterns like "corrupted_symbol+standard_us".
  static bool isCorrection(String matchedPattern) {
    if (correctionPatterns.contains(matchedPattern)) return true;
    return correctionPatterns.any((p) => matchedPattern.startsWith('$p+'));
  }
}
```

**Test change**: Replace hardcoded `b1StandardPatterns` set with import:
```dart
import 'package:construction_inspector/features/pdf/services/extraction/rules/interpretation_patterns.dart';
```
- Line ~2774: Delete `const b1StandardPatterns = {...}`, use `InterpretationPatterns.standardPatterns`
- Line ~2793: Replace `!b1StandardPatterns.contains(matchedPattern)` with `InterpretationPatterns.isCorrection(matchedPattern)`
- Line ~2908: Same replacement in B4 calculation

**Expected result**: B1 drops from BUG to OK, B4 drops from 32.1% to ~7.1% (OK).

---

### Part 2: Tighten 12 Silently Passing Metrics

Each change replaces a useless threshold with a meaningful ratio-based check. All thresholds are pipeline-generic.

| # | Stage/Metric | Current | New Threshold | Rationale |
|---|---|---|---|---|
| 1 | **3A Element Validation** `>0` | `optionalStatus(... totalValidatedElements > 0)` | `totalValidatedElements >= totalElements * 0.90` — OK if >=90% of OCR elements survive validation, LOW if >=70%, BUG if <70% | A validation stage that drops >10% of elements is losing data |
| 2 | **3B Element Clamping** `>=0` | `totalClampedElements >= 0` | `clampedRatio <= 0.05` OK, `<=0.15` LOW, `>0.15` BUG where `clampedRatio = totalClampedElements / max(totalValidatedElements, 1)` | Massive clamping (>5%) means coordinate issues |
| 3 | **4A Desc cont rows** `>=0` | `descContinuationRows >= 0` | `descContinuationRows <= dataRows * 2` OK, else BUG | >2x data rows in desc continuations = misclassification |
| 4 | **4A.1p Absorbed rows** `N/A` | Hardcoded `'N/A'` | `absorbedRowsProv >= 0 && absorbedRowsProv < headerRows` OK, else LOW | Absorbed should be non-negative and less than raw header count |
| 5 | **4A.1f Absorbed rows** `N/A` | Same | Same logic | Same |
| 6 | **4B.5 Row Pathways** `>0` | `rowPathwayDecisions > 0` | `rowPathwayDecisions >= dataRows * 0.80` OK, `>=0.50` LOW, else BUG | Pathway decisions should approximately match row count |
| 7 | **4C.5 Layer attempts** `>0` | `columnLayerAttempts > 0` | Keep `>0` for existence but also verify layers exist in fixture with at least 1 entry | Minor tightening — check fixture has layer data |
| 8 | **4A.5 Merged rows** `>0` | `mergedRowCount > 0` | `mergedRowCount >= dataRows * 0.80` OK, `>=0.50` LOW, else BUG | Merged rows should track data rows closely |
| 9 | **4D.5 Currency parsed** `>=60%` | `interpretedCurrencyRate >= 0.60` | `>=0.80` OK, `>=0.60` LOW, `<0.60` BUG | Tighten from 60% to 80% — we achieve 94% |
| 10 | **4E.5 Scored items** `>0` | `confidenceScoredItems > 0` | `confidenceScoredItems / confidenceInputItems >= 0.90` OK, `>=0.70` LOW, else BUG | Scoring should cover nearly all items |
| 11-15 | **5.1-5.5 Post-* stages** `>=0` | `postXxxCount >= 0` | Per-stage retention: `postXxxCount / previousStageCount >= 0.90` OK, `>=0.70` LOW, else BUG. Chain: 5.1 vs parsed, 5.2 vs 5.1, 5.3 vs 5.2, 5.4 vs 5.3, 5.5 vs 5.4 | Catches intermediate item drops |

---

### Part 3: Add Missing Coverage (4 new metric rows)

#### 3A: GridLineRemover Coverage (2 new rows after Stage 2B.5)

Read `springfield_grid_line_removal.json` fixture (already loaded as nullable). Add 2 rows:

| Row | Metric | Logic |
|---|---|---|
| `2B-ii.6` "Pages cleaned" | Expected: grid page count. Actual: `pages_cleaned` from fixture. | `stat(pagesCleaned, pagesWithGrid)` |
| `2B-ii.6` "Pages failed" | Expected: 0. Actual: `pages_failed` from `stage_report_metrics`. | `== 0` OK, else BUG |

Fixture structure (already captured):
```json
{ "pages_cleaned": 6, "stage_report_metrics": { "pages_total": 6, "pages_processed": 6, "pages_failed": 0, ... } }
```

Add `'2B-ii.6': (5, 'Grid Line Removal')` to `stageDisplayOrder` and renumber subsequent entries.

#### 3B: Row Merging Orphans (1 new row at Stage 4A.5)

```dart
final orphanContinuations = (mergedRowsJson?['orphan_continuations'] as num?)?.toInt() ?? 0;
```

| Row | Metric | Logic |
|---|---|---|
| `4A.5` "Orphan continuations" | Expected: 0. Actual: `orphan_continuations` from merged rows fixture. | `== 0` OK, `<= 3` LOW, `> 3` BUG |

#### 3C: B6 Arithmetic Cross-Check (1 new B-series row at Stage 4E.5)

For each parsed item with qty, price, and amount all non-null, check `|qty * price - amount| <= 0.02`:

```dart
var b6MathFailures = 0;
var b6MathChecked = 0;
for (final item in parsedItems) {
  final qty = _toDouble(item['quantity']);
  final price = _toDouble(item['unit_price']);
  final amount = _toDouble(item['bid_amount']);
  if (qty != null && price != null && amount != null) {
    b6MathChecked++;
    if ((qty * price - amount).abs() > 0.02) {
      b6MathFailures++;
    }
  }
}
final b6FailRate = b6MathChecked == 0 ? 0.0 : b6MathFailures / b6MathChecked;
// Status: OK if <= 5%, LOW if <= 15%, BUG if > 15%
```

| Row | Metric | Logic |
|---|---|---|
| `4E.5` "B6 math consistency" | Expected: `<=5% fail`. Actual: `failures/checked (rate%)`. | `<=5%` OK, `<=15%` LOW, `>15%` BUG |

---

### Part 4: Update stageDisplayOrder

Add the new stage key for grid line removal. Insert `'2B-ii.6': (5, 'Grid Line Removal')` and renumber `2B-iii` to `(6, ...)` and all subsequent +1.

---

## Summary of Changes

| Category | Count | Detail |
|---|---|---|
| New production file | 1 | `interpretation_patterns.dart` |
| B1/B4 fix | 1 test change | Import + replace hardcoded set |
| Silent metrics tightened | 15 threshold changes | All ratio-based, pipeline-generic |
| New scorecard rows | 4 | GridLineRemover (2), orphans (1), B6 math (1) |
| stageDisplayOrder update | 1 | Add `2B-ii.6` entry |

**Total new scorecard metrics**: 62 existing + 4 new = **66 metrics**

## Verification

1. `pwsh -Command "flutter test test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart"` — scorecard should print with 0 BUG, minimal LOW
2. `pwsh -Command "flutter test test/features/pdf/extraction/"` — all extraction tests green
3. Verify B1 shows OK (not BUG)
4. Verify B4 shows OK (not LOW)
5. Verify new rows (GridLineRemover, orphans, B6) appear and show OK
6. Verify tightened thresholds don't introduce false alarms on Springfield data

## Implementation Order

1. Create `interpretation_patterns.dart` (production code, standalone)
2. Fix B1/B4 in test (import new class, replace hardcoded set)
3. Add GridLineRemover rows + stageDisplayOrder entry
4. Add orphan continuations row
5. Add B6 math consistency row
6. Tighten 15 silent metrics (batch edit)
7. Run tests, verify scorecard

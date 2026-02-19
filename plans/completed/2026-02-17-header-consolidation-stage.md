# Header Consolidation Stage — Implementation Plan

**Date**: 2026-02-17 | **Session**: 364
**Status**: APPROVED — Ready for implementation

## Overview

### Purpose
Merge consecutive `RowType.header` classified rows on the same page into one logical header row per page. This resolves the row merger header blocker (17 physical headers → 6 logical headers) and provides cleaner data to all downstream stages.

### Key Decision: Dual-Pass Consolidation (Option B)
The pipeline classifies rows twice (provisional + final). Consolidation runs after BOTH passes:
- **After provisional classify** → feeds Region Detector (4B) + Column Detector (4C) with clean headers
- **After final classify** → feeds Merger (4A.5) + Cell Extractor (4D) + Row Parser (4E) with clean headers

Region detector and column detector already handle fragmented headers internally, but consolidating before them provides cleaner input and eliminates redundant internal re-grouping logic.

### Pipeline Placement
```
Before:
  provisional classify → 4B Region Detect → 4C Column Detect → 4A Final Classify → 4A.5 Merge → 4D → 4E

After:
  provisional classify → 4A.1p Header Consolidate → 4B Region Detect → 4C Column Detect
                              → 4A Final Classify → 4A.1f Header Consolidate → 4A.5 Merge → 4D → 4E
```

### Success Criteria
- [ ] 17 physical headers → 6 logical headers (Springfield PDF)
- [ ] Each logical header contains ALL OcrElements from constituent physical rows
- [ ] No non-header rows modified
- [ ] StageReport enforces no-data-loss invariant
- [ ] Two fixture files captured via onStageOutput
- [ ] Scorecard updated with consolidation metrics
- [ ] All existing tests pass (no regressions)

---

## Implementation Details

### 1. New File: `lib/features/pdf/services/extraction/stages/header_consolidator.dart`

**Class**: `HeaderConsolidator`

**Signature**:
```dart
(ClassifiedRows, StageReport) consolidate({
  required ClassifiedRows classifiedRows,
  required String stageName,  // StageNames.headerConsolidationProvisional or .headerConsolidationFinal
})
```

**Algorithm** (single linear pass, O(n)):
1. Iterate through `classifiedRows.rows`
2. For each row:
   - If `row.type == RowType.header`:
     - If previous output row is also `RowType.header` AND same `pageIndex`:
       → Combine: `prevRow.copyWith(elements: [...prev.elements, ...current.elements])`
     - Otherwise → add as new output row
   - If `row.type != RowType.header`:
     → Pass through unchanged
3. Recompute `ClassificationStats`:
   - `totalRows` = new output row count
   - `countsByType[RowType.header]` = logical header count
   - All other counts unchanged
   - `averageConfidence` recomputed from output rows

**StageReport**:
```dart
StageReport(
  stageName: stageName,  // parameterized
  elapsed: stopwatch.elapsed,
  stageConfidence: 1.0,  // deterministic transformation
  inputCount: classifiedRows.rows.length,      // 286
  outputCount: outputRows.length,              // 275
  excludedCount: absorbedCount,                // 11
  warnings: warnings,
  metrics: {
    'physical_headers': physicalHeaderCount,    // 17
    'logical_headers': logicalHeaderCount,      // 6
    'absorbed_rows': absorbedCount,             // 11
    'pages_with_headers': pagesWithHeaders,     // 6
    'max_elements_per_header': maxElements,     // largest consolidated header
    'min_elements_per_header': minElements,     // smallest
  },
  completedAt: DateTime.now(),
)
```

**No-data-loss invariant**: `outputCount + excludedCount == inputCount` (275 + 11 = 286)

**Element preservation**: Every OcrElement from every physical header row appears in exactly one consolidated header. No elements dropped or modified.

### 2. Update: `lib/features/pdf/services/extraction/stages/stage_names.dart`

Add two constants:
```dart
static const headerConsolidationProvisional = 'header_consolidation_provisional';
static const headerConsolidationFinal = 'header_consolidation_final';
```

### 3. Update: `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`

**Insertion point 1** — After provisional classification (~line 545), before region detection (~line 549):
```dart
final headerConsolidator = HeaderConsolidator();

// Consolidate provisional headers
final (consolidatedProvisional, hcProvReport) = headerConsolidator.consolidate(
  classifiedRows: provisionalRows,
  stageName: StageNames.headerConsolidationProvisional,
);
reports.add(hcProvReport);
onStageOutput?.call(StageNames.headerConsolidationProvisional, consolidatedProvisional.toMap());

// Use consolidated rows for region detection
// Replace provisionalRows with consolidatedProvisional in subsequent calls
```

**Insertion point 2** — After final classification (~line 808), before row merging (~line 812):
```dart
final (consolidatedFinal, hcFinalReport) = headerConsolidator.consolidate(
  classifiedRows: classifiedRows,
  stageName: StageNames.headerConsolidationFinal,
);
reports.add(hcFinalReport);
onStageOutput?.call(StageNames.headerConsolidationFinal, consolidatedFinal.toMap());

// Use consolidatedFinal for merger and downstream
```

**Variable threading**: Ensure all downstream references use the consolidated ClassifiedRows, not the raw classifier output.

### 4. Fixture Generator Updates

**`tool/generate_springfield_fixtures.dart`** — Add to `stageToFilename` map:
```dart
StageNames.headerConsolidationProvisional: 'springfield_header_consolidation_provisional.json',
StageNames.headerConsolidationFinal: 'springfield_header_consolidation_final.json',
```

**`integration_test/generate_golden_fixtures_test.dart`** — Add same entries to its `stageToFilename` map.

---

## Testing Plan

### 5. New File: `test/features/pdf/extraction/stages/header_consolidator_test.dart`

Following established pattern (single group, helpers at bottom):

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `single header row passes through unchanged` | 1 header → 1 header, elements preserved |
| 2 | `consecutive headers on same page merge` | 3 headers page 0 → 1 merged, all elements present |
| 3 | `headers on different pages stay separate` | header@p0 + header@p1 → 2 separate headers |
| 4 | `non-header rows pass through unchanged` | data, continuation, boilerplate, total unmodified |
| 5 | `mixed sequence preserves order` | header, header, data, data, header → correct order |
| 6 | `page 0 anomaly: 2 headers merge` | Matches Springfield page 0 (2 headers) |
| 7 | `empty input produces empty output` | Edge case |
| 8 | `no headers produces identical output` | All-data input unchanged |
| 9 | `StageReport enforces no-data-loss invariant` | inputCount = outputCount + excludedCount |
| 10 | `stats recomputed correctly` | ClassifiedRows.stats matches actual row counts |

**Helpers**: Reuse pattern from `row_merger_test.dart` — `_classifiedRows()` and `_row()` builders.

### 6. New File: `test/features/pdf/extraction/contracts/stage_4a_to_4a1_contract_test.dart`

Contract validation:
- Input `ClassifiedRows.isValid` → output `ClassifiedRows.isValid`
- All non-header row types preserved (count check per type)
- Total OcrElement count across all headers preserved (sum check)
- `StageReport.isValid`, correct `stageName`
- No-data-loss invariant: `inputCount == outputCount + excludedCount`
- Normalized coordinates in [0.0, 1.0] for all output elements

### 7. Update: `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart`

**New scorecard rows** (add after Stage 4A rows, before Stage 4B):

| Stage | Metric | Expected | Status Logic |
|-------|--------|----------|-------------|
| `4A.1p` | Logical headers (provisional) | 6 | `stat(logicalHeaders, 6)` |
| `4A.1p` | Absorbed rows | 11 | informational (no status) |
| `4A.1f` | Logical headers (final) | 6 | `stat(logicalHeaders, 6)` |
| `4A.1f` | Absorbed rows | 11 | informational (no status) |

**Update existing row**: The `4A Headers` scorecard row currently reads from raw classifier output. After this change, it should still read from the classifier (showing 17 physical), while the new `4A.1` rows show the consolidation result (6 logical). This provides visibility into both.

---

## Implementation Phases

### Phase 1: Core Stage (PR-ready)
1. Create `header_consolidator.dart` with consolidate method
2. Add stage name constants to `stage_names.dart`
3. Create `header_consolidator_test.dart` with all 10 tests
4. Create contract test
5. Run: `pwsh -Command "flutter test test/features/pdf/extraction/stages/header_consolidator_test.dart"`

### Phase 2: Pipeline Integration
1. Wire into `extraction_pipeline.dart` at both insertion points
2. Thread consolidated ClassifiedRows to downstream stages
3. Update fixture generator mappings (both CLI and integration test)
4. Run: `pwsh -Command "flutter test test/features/pdf/extraction/"` — verify no regressions

### Phase 3: Scorecard & Fixtures
1. Add scorecard rows to `stage_trace_diagnostic_test.dart`
2. Regenerate Springfield fixtures (will include new consolidation fixture files)
3. Run full scorecard, verify header metrics show OK
4. Run golden test, verify no regressions

### Phase 4: Verification
1. Run full PDF extraction test suite
2. Verify scorecard improvement (expect headers 6/6 = OK)
3. Check merged rows count decreased (149 → 138 expected)
4. Commit

---

## Agent Assignments

| Phase | Agent | Task |
|-------|-------|------|
| 1 | `frontend-flutter-specialist-agent` | Implement HeaderConsolidator + unit tests |
| 2 | `frontend-flutter-specialist-agent` | Pipeline integration + fixture generator updates |
| 3 | `qa-testing-agent` | Scorecard updates + fixture regeneration + verification |
| 4 | `code-review-agent` | Final review before commit |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `headerRowIndices` stale after consolidation | Low | Consolidation runs BEFORE region detection — indices computed against consolidated list |
| Column detector behaves differently with consolidated headers | Low | It already re-groups by X-position in `_combineMultiRowHeaders()` — same elements, same result |
| Provisional and final classifications produce different header counts | Low | Both use same consolidation logic — any difference would reflect actual classifier behavior |
| Existing tests break | Low | Consolidation only modifies header rows — data/continuation/total unchanged |

---

## Decisions Made

1. **Dual-pass consolidation** (after both provisional and final classification)
2. **Single reusable class** called twice with distinct stage names
3. **Same-page-only merge rule** — consecutive headers on same pageIndex
4. **Consolidation only** — no validation of data rows against headers (future enhancement)
5. **Separate stage with own diagnostic output** — not folded into merger

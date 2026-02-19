# Row Parser V3 — Full Rewrite Plan

**Created**: 2026-02-18 (Session 374)
**Status**: APPROVED
**Goal**: Replace RowParserV2 with 3 focused stages, close $253K checksum gap, achieve 50 OK / 0 LOW / 0 BUG scorecard

## Design Decisions (from brainstorming)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Rewrite scope | Full rewrite (architecture + fix) | Parser has ~50% redundant logic due to upstream pipeline improvements |
| CellGrid metadata | Add `RowType` to rows via `CellGridRow` | Eliminates all 4 re-classification methods in parser |
| Pipeline split | 3 stages: NumericInterpreter (4D.5), RowParserV3 (4E), FieldConfidenceScorer (4E.5) | Maximum modularity, independent testability |
| Parsing philosophy | Transform, don't delete | Past v1/v2 deletion-based parsing was hard to debug; keep raw text intact |
| Currency approach | Column-aware pattern recognition with registered rules | Extensible, no hardcoded if/else chains |
| Format scope | US construction standard + known OCR variants | Covers 99% of US state DOT bid tabs |
| Logging level | Per-cell + full transformation chain (in diagnostics only) | Model stays slim; fixtures get full debug detail |
| Fixtures & scorecard | New fixtures for interpreter + confidence; new scorecard rows | Full visibility into new stages |

## Architecture Overview

### New Pipeline Flow (Stages 4D through 5)

```
Stage 4D:   CellExtractorV2 (existing, minor update)
              |
              v
            CellGrid (NOW with typed CellGridRow)
              |
              v
Stage 4D.5: NumericInterpreter (NEW)
              |
              v
            InterpretedGrid
              |
              v
Stage 4E:   RowParserV3 (REWRITE — pure field mapping)
              |
              v
            ParsedItems
              |
              v
Stage 4E.5: FieldConfidenceScorer (NEW)
              |
              v
            ScoredItems (ParsedItems with confidence populated)
              |
              v
Stage 5:    PostProcessor (existing, unchanged)
```

## Component Designs

### 1. CellGrid Model Change

**File**: `lib/features/pdf/services/extraction/models/cell_grid.dart`

```dart
// NEW
class CellGridRow {
  final RowType type;       // from RowClassifierV3 via MergedRow
  final List<Cell> cells;
  final int pageIndex;

  const CellGridRow({
    required this.type,
    required this.cells,
    required this.pageIndex,
  });
}

// UPDATED
class CellGrid {
  final List<CellGridRow> rows;  // was: List<List<Cell>> grid
  // ... rest of model stays the same
}
```

**Producer update**: `CellExtractorV2` already has access to `MergedRow.type` — thread it into `CellGridRow`.

### 2. NumericInterpreter (Stage 4D.5)

**File**: `lib/features/pdf/services/extraction/stages/numeric_interpreter.dart`

#### InterpretedValue (slim pipeline model)

```dart
class InterpretedValue {
  final String rawText;           // untouched original
  final double? value;            // extracted numeric (null if unrecognized)
  final String? displayText;      // formatted for app display
  final String matchedPattern;    // rule name: "standard_us", "european_periods", etc.
}
```

#### InterpretationRule (extensible registry)

```dart
abstract class InterpretationRule {
  String get name;
  bool matches(String text);
  InterpretedValue interpret(String text);
  // For diagnostics fixture only (not on pipeline model):
  List<TransformStep> describeTransforms(String text);
}

class TransformStep {
  final int step;
  final String rule;
  final String detail;
}
```

#### Column Routing

| Column Semantic | Interpretation Strategy |
|----------------|----------------------|
| `unitPrice` / `bidAmount` | Currency rules (full set) |
| `quantity` | Numeric rules (comma-grouped, space-grouped, plain) |
| `itemNumber` | Item number rules (trailing dot cleanup, pipe/bracket artifacts) |
| `description` / `unit` | Text pass-through (trim only) |

#### Currency Rules (ordered, first match wins)

| # | Rule Name | Pattern | Example | Extracted |
|---|-----------|---------|---------|-----------|
| 1 | `standard_us` | `$N,NNN.NN` | `$1,234.56` | 1234.56 |
| 2 | `no_comma_us` | `$NNNN.NN` | `$1234.56` | 1234.56 |
| 3 | `european_periods` | `$N.NNN.NN` (3-digit middle group) | `$168.470.00` | 168470.00 |
| 4 | `corrupted_symbol` | `[non-$]N,NNN.NN` or trailing `C`/`(` etc. | `£500.00`, `$980.0C` | 500.00, 980.00 |
| 5 | `missing_decimals` | `$NNNN` (no decimal point) | `$1234` | 1234.00 |
| 6 | `parenthetical_negative` | `($N,NNN.NN)` | `($1,234.56)` | -1234.56 |
| 7 | `unrecognized` | No match | anything else | null |

**Combination handling**: Rules 3 and 4 can co-occur (e.g., `£168.470.00` — corrupted symbol AND european periods). The rule registry should allow chained recognition — e.g., first recognize symbol corruption, then recognize the resulting numeric format. Implementation: the `corrupted_symbol` rule normalizes the currency symbol, then delegates to the numeric format rules.

#### Diagnostics (fixture-only, not on pipeline model)

```dart
class CellInterpretation {
  final int rowIndex;
  final int colIndex;
  final String columnSemantic;
  final String rawText;
  final double? value;
  final String? displayText;
  final String matchedPattern;
  final List<TransformStep> transforms;  // full chain
}
```

Saved to `springfield_interpreted_grid.json`.

### 3. RowParserV3 (Stage 4E)

**File**: `lib/features/pdf/services/extraction/stages/row_parser_v3.dart`

**Target**: ~150 lines (vs current ~670)

**Logic**:
```
for each CellGridRow in InterpretedGrid:
  switch (row.type):
    case DATA:
      map interpreted cells -> ParsedBidItem
      (value from InterpretedValue.value, raw from .rawText)
    case TOTAL:
      extract document total (subtotal vs grand total logic — kept from v2)
    case _:
      skip with reason logged
```

**What's GONE** (vs v2):
- `_isHeaderRow()` — replaced by `row.type == RowType.header`
- `_isSectionHeader()` — replaced by `row.type == RowType.sectionHeader`
- `_isContinuationRow()` + `_mergeContinuationRow()` — RowMerger handles this upstream
- `_mapColumnSemantics()` — ColumnDetectorV2 already resolved semantics
- `_parsePrice()`, `_parseQuantity()` — moved to NumericInterpreter
- `_normalizeItemNumber()`, `_cleanDescription()` — moved to NumericInterpreter
- `_computeFieldConfidence()` — moved to FieldConfidenceScorer

**What's KEPT**:
- Total extraction + subtotal vs grand total disambiguation (business logic)
- Item number format validation (warning, not rejection)
- LS unit exception for missing quantity
- StageReport data-loss assertion
- SkippedRow audit trail with `_extractRawElements()`

### 4. FieldConfidenceScorer (Stage 4E.5)

**File**: `lib/features/pdf/services/extraction/stages/field_confidence_scorer.dart`

**3-factor weighted geometric mean**:
- OCR confidence (50%) — from `Cell.confidence`
- Format validation (30%) — does parsed value match expected format?
- Interpretation confidence (20%) — from `InterpretedValue.confidence`

**Diagnostics**: Per-item, per-field confidence breakdown saved to `springfield_field_confidence.json`.

### 5. Fixture & Stage Trace Updates

#### New fixture files

| Fixture | Stage | Contents |
|---------|-------|----------|
| `springfield_interpreted_grid.json` | 4D.5 | Per-cell interpretations with transform chains |
| `springfield_field_confidence.json` | 4E.5 | Per-item, per-field confidence breakdown |
| `springfield_parsed_items.json` | 4E | Updated — now produced by V3 parser |

#### Stage trace test additions

**New stage block — 4D.5 Numeric Interpreter**:
- Cells interpreted: count with non-null value
- Pattern distribution: count per rule (standard_us, european_periods, etc.)
- Unrecognized cells: count + raw values
- Transform count: cells needing transforms vs clean parse

**New stage block — 4E.5 Field Confidence**:
- Mean confidence per field type
- Items with confidence < 0.80

#### New scorecard rows

| Stage | Metric | Expected | Threshold |
|-------|--------|----------|-----------|
| 4D.5 Numeric Interpreter | Interpretation rate (price/amount) | 100% | OK >= 95%, LOW >= 70% |
| 4D.5 Numeric Interpreter | Transform count | informational | N/A |
| 4E.5 Field Confidence | Mean item confidence | > 0.85 | OK >= 0.85 |

#### Fixture generator update

Update `tool/generate_springfield_fixtures.dart` and `integration_test/generate_golden_fixtures_test.dart` to emit:
- `springfield_interpreted_grid.json`
- `springfield_field_confidence.json`
- Updated `springfield_parsed_items.json` (from V3)

## Implementation Phases

### Phase 1: CellGrid Model + Upstream Threading

**Files touched**:
- `lib/features/pdf/services/extraction/models/cell_grid.dart` — add CellGridRow
- `lib/features/pdf/services/extraction/stages/cell_extractor_v2.dart` — thread RowType
- `lib/features/pdf/services/extraction/stages/row_parser_v2.dart` — temporary compat update
- `test/features/pdf/extraction/stages/stage_4d_cell_extractor_test.dart` — update tests
- `test/features/pdf/extraction/contracts/` — update contract tests
- Fixture regeneration

**Verification**: All 842 extraction tests pass. Pipeline output unchanged.

### Phase 2: NumericInterpreter Stage

**New files**:
- `lib/features/pdf/services/extraction/stages/numeric_interpreter.dart`
- `lib/features/pdf/services/extraction/models/interpreted_value.dart`
- `lib/features/pdf/services/extraction/models/interpretation_rule.dart`
- `lib/features/pdf/services/extraction/rules/currency_rules.dart`
- `lib/features/pdf/services/extraction/rules/numeric_rules.dart`
- `lib/features/pdf/services/extraction/rules/text_rules.dart`
- `test/features/pdf/extraction/stages/numeric_interpreter_test.dart`

**Files touched**:
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` — wire new stage
- `lib/features/pdf/services/extraction/stages/stages.dart` — register stage name
- `tool/generate_springfield_fixtures.dart` — emit interpreted_grid fixture

**Verification**: Unit tests for every rule. Integration test with Springfield data. Fixture generated.

### Phase 3: RowParserV3

**New files**:
- `lib/features/pdf/services/extraction/stages/row_parser_v3.dart`
- `test/features/pdf/extraction/stages/row_parser_v3_test.dart`

**Files removed**:
- `lib/features/pdf/services/extraction/stages/row_parser_v2.dart` (move to deprecated/)

**Files touched**:
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` — swap v2 for v3
- `lib/features/pdf/services/extraction/stages/stages.dart` — update stage name
- All parser-consuming tests updated

**Verification**: All extraction tests pass. Parsed items fixture matches or improves on v2 output.

### Phase 4: FieldConfidenceScorer Stage

**New files**:
- `lib/features/pdf/services/extraction/stages/field_confidence_scorer.dart`
- `test/features/pdf/extraction/stages/field_confidence_scorer_test.dart`

**Files touched**:
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` — wire new stage
- `lib/features/pdf/services/extraction/stages/stages.dart` — register stage name
- `tool/generate_springfield_fixtures.dart` — emit field_confidence fixture

**Verification**: Unit tests. Confidence values reasonable (> 0.80 mean).

### Phase 5: Stage Trace & Scorecard + Final Validation

**Files touched**:
- `test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart` — new stage blocks + scorecard rows
- `tool/generate_springfield_fixtures.dart` — final regeneration with complete pipeline
- `integration_test/generate_golden_fixtures_test.dart` — if needed

**Verification**:
- Regenerate ALL fixtures with full new pipeline
- Run stage trace: target **50 OK / 0 LOW / 0 BUG**
- Run full `flutter test test/features/pdf/extraction/` — all pass
- Run full `flutter test` — no regressions

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Scorecard OK | 45 | 50+ |
| Scorecard LOW | 4 | 0 |
| Scorecard BUG | 1 | 0 |
| Quality score | 0.912 | > 0.95 |
| unit_price (parsed) | 123/131 | 131/131 |
| bid_amount (parsed) | 117/131 | 131/131 |
| Checksum | $7,629,312 vs $7,882,927 | Match |
| Parser lines | ~670 | ~150 |
| Redundant methods | 6 | 0 |

## Agent Assignments

| Phase | Primary Agent | Supporting |
|-------|--------------|------------|
| 1 | frontend-flutter-specialist-agent | qa-testing-agent |
| 2 | pdf-agent | qa-testing-agent |
| 3 | pdf-agent | code-review-agent |
| 4 | pdf-agent | qa-testing-agent |
| 5 | qa-testing-agent | pdf-agent |

## Risk Mitigations

- **Phase 1 compat**: V2 parser gets temporary update to consume new CellGrid model before V3 replaces it. Pipeline never breaks.
- **Rule ordering**: Currency rules are ordered most-specific-first to avoid ambiguous matches.
- **Combination patterns**: `corrupted_symbol` rule delegates to other rules after symbol normalization, handling combos like `£168.470.00`.
- **Regression**: Each phase regenerates fixtures and runs full extraction test suite before proceeding.
- **Fixture regen blocker**: If Windows build fails, kill processes + clean build/ first (known fix from S374).

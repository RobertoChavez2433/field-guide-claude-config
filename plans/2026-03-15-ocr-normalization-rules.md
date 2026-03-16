# OCR Normalization Rules + Wrapped Text Fix

**Date**: 2026-03-15
**Status**: READY FOR IMPLEMENTATION
**Spec**: Springfield diagnostic results — 13 description failures across 4 categories
**Goal**: Raise description accuracy from 90% → 98.5% (11 of 13 failures fixed)
**Blast Radius**: 2 source files modified, 1 test file modified, 1 test file created

---

## Phase 1: Cell Extraction Reading-Order Fix

### Step 1.1: Fix `_buildCell()` sort in CellExtractorV2

**File**: `lib/features/pdf/services/extraction/stages/cell_extractor_v2.dart`
**Method**: `_buildCell()` at line 528
**Agent**: `frontend-flutter-specialist-agent`

**Current** (broken for multi-line cells):
```dart
fragments.sort((a, b) => a.boundingBox.left.compareTo(b.boundingBox.left));
```

**Fix**: Replace with Y-band-aware reading order sort:
1. Compute median fragment height from the fragments list
2. Set `yBandTolerance = medianHeight * 0.5`
3. Sort: if Y difference ≤ tolerance → same line → sort by X. Otherwise sort by Y.

**Why generic**: Any multi-line cell in any PDF table has the same reading-order requirement. The sort is purely geometric with no content assumptions.

**False-positive risk**: VERY LOW. Single-line baseline jitter (1-3px) is well within 0.5x median height tolerance (~6-8px). Multi-line gaps always exceed tolerance.

**Fixes**: Items 121, 123, 125, 130 (4 items)

---

## Phase 2: Description Normalization Rules

All rules plug into existing `_descriptionArtifactRules` list in `post_process_utils.dart`.
Insert AFTER the existing `bend_elbow_degree_mark` rule (currently the last entry).
**Order matters** — rules must run in this sequence.

**Agent**: `frontend-flutter-specialist-agent`

### Step 2.1: Rule — `kerning_space_recovery`

**File**: `lib/features/pdf/services/extraction/shared/post_process_utils.dart`

**Purpose**: Insert space around `x` dimension separator when adjacent to a digit after a measurement symbol.

**Pattern**: `(["'°])\s*x(\d)` → `$1 x $2`

**Examples**:
- `Tee, 8" x 8" x6"` → `Tee, 8" x 8" x 6"`
- `Tee, 6" x6" x 6"` → `Tee, 6" x 6" x 6"`

**Why generic**: The `x` dimension separator is universal in construction documents (pipe fittings, structural members, conduit). OCR frequently loses spacing around it.

**False-positive risk**: VERY LOW. Requires measurement symbol before `x` and digit after.

**Fixes**: Items 58, 59 (2 items)

### Step 2.2: Rule — `measurement_delimiter_recovery`

**Purpose**: Insert comma between adjacent measurement values where OCR dropped the delimiter.

**Pattern**: `(\d[\d.]*(?:°|"|'))\s+(?=\d+[\d.]*(?:°|"|'))` → `$1, ` (lookahead)

**Examples**:
- `Bend, 45° 12"` → `Bend, 45°, 12"`
- `Bend, 11.25° 8"` → `Bend, 11.25°, 8"`

**Why generic**: Construction bid items use comma-delimited measurement lists. Both sides must end with measurement symbols (°, ", '), so bare numbers like `45° angle` won't match.

**False-positive risk**: LOW-MEDIUM. The lookahead requiring BOTH sides to have measurement symbols eliminates most false positives.

**Fixes**: Items 63, 65, 68 (3 items)

### Step 2.3: Rule — `post_quote_comma_recovery`

**Purpose**: Insert comma after a dimension when followed by a capitalized descriptive word.

**Pattern**: `(\d["'])\s+([A-Z][a-z]\w*)` → `$1, $2`

**Exclusion list** (measurement-continuation words that naturally follow a dimension without comma):
```
Diameter, Thick, Wide, Long, Deep, High, Tall, Radius, Gauge, Grade,
Pitch, Span, Bore, Wall, Square, Round, Flat, Clear, Nominal, Outside,
Inside, Inner, Outer, Min, Max, Minimum, Maximum
```

**Examples**:
- `24" Stop Bar` → `24", Stop Bar`
- `24" Diameter Pipe` → `24" Diameter Pipe` (excluded — no change)

**Why generic**: Construction bid items follow `Dimension, Description` format. The exclusion list covers standard measurement qualifiers.

**False-positive risk**: MEDIUM. Exclusion list is critical. Extend as needed when new PDFs are tested.

**Fixes**: Item 126 (1 item)

### Step 2.4: Rule — `roman_numeral_confusable_fix`

**Purpose**: After classification keywords, normalize `l` → `I` in Roman numeral tokens.

**Pattern**: `\b(Type|Class|Grade|Series|Mark|Phase|Level|Group)\s+([lIiVvXx]+)\b`
**Transform**: Replace lowercase `l` with `I`, then uppercase the entire token.

**Examples**:
- `Type ll` → `Type II`
- `Class lll` → `Class III`
- `Type II` → `Type II` (already correct — no change)

**Why generic**: Roman numeral classification is universal in construction specs (pipe classes, concrete types, soil classifications). The `l`/`I` confusion is one of the most common OCR errors. The 8-keyword guard prevents false positives.

**False-positive risk**: VERY LOW. Only fires after specific classification keywords.

**Fixes**: Item 22 (1 item)

---

## Phase 3: Tests

### Step 3.1: Add wrapped-text tests to cell extractor test file

**File**: `test/features/pdf/extraction/stages/stage_4d_cell_extractor_test.dart`
**Agent**: `frontend-flutter-specialist-agent`

Add test group `CellExtractorV2 - Wrapped Text Reading Order`:
1. **Multi-line sort test**: Fragments at different Y positions → reading order preserved
2. **Baseline jitter test**: Same-line fragments with minor Y variance → left-to-right order preserved

### Step 3.2: Create normalization rules test file

**File**: `test/features/pdf/extraction/shared/post_process_utils_test.dart` (NEW)
**Agent**: `frontend-flutter-specialist-agent`

Test groups for each rule:
- `kerning_space_recovery`: positive match, no-match (non-measurement x), already-spaced
- `measurement_delimiter_recovery`: degree+inch, inch+inch, no measurement symbol
- `post_quote_comma_recovery`: positive match, exclusion word, lowercase word
- `roman_numeral_confusable_fix`: Type ll, Class lll, no keyword, already correct

### Step 3.3: Run full test suite + Springfield integration

1. `flutter test` — verify no regressions across all ~780 tests
2. Springfield integration — verify description accuracy ≥ 98%

---

## Expected Outcome

| Metric | Before | After |
|--------|--------|-------|
| Description accuracy | 90.0% (13 failures) | 98.5% (2 remaining) |
| Items found | 131/131 | 131/131 |
| Checksum | $0 distance | $0 distance |
| Quantity | 100% | 100% |
| Unit Price | 100% | 100% |
| Bid Amount | 100% | 100% |

### 2 Known Remaining Limitations (not addressable with generic rules)
1. **Item 38**: `20"` vs `20th` — superscript suffix misread as quote mark. Cannot disambiguate `20"` (inches) from `20th` (ordinal) without semantic context.
2. **Item 52**: Trailing `"` dropped from `12"` → `12`. Cannot know whether bare `12` should have an inch mark.

---

## Rule Ordering in `_descriptionArtifactRules` (16 total)

| # | Name | Source |
|---|------|--------|
| 1-12 | (existing rules) | Already in codebase |
| **13** | `kerning_space_recovery` | NEW — Phase 2 |
| **14** | `measurement_delimiter_recovery` | NEW — Phase 2 |
| **15** | `post_quote_comma_recovery` | NEW — Phase 2 |
| **16** | `roman_numeral_confusable_fix` | NEW — Phase 2 |

Order rationale: kerning first (normalizes spacing), then measurement delimiters (specific pattern), then quote-comma (broader pattern), then Roman numerals (independent).

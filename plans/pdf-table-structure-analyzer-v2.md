# PDF Table Structure Analyzer Plan v2 (Merged)

**Created**: 2026-02-05
**Status**: Draft (Pending Review)
**Supersedes**: `pdf-table-structure-analyzer-plan.md`, `pdf-extraction-regression-recovery-plan.md`

## Goal

Create a robust, deterministic, offline algorithm that reliably extracts table data from construction bid PDFs, achieving **95%+ accuracy** (125+/131 items on Springfield) without hardcoded position rules.

---

## Design Decisions (From Brainstorming Session)

| Topic | Decision | Rationale |
|-------|----------|-----------|
| **DP optimization** | Dropped | Real problems are local (pattern matching, cleanup), not global optimization. Two-pass linear scan is simpler and sufficient. |
| **Column priors** | Layers 1-3 only | Headers + gridlines + anchor correction. X-clustering (Layer 4) deferred to future phase. |
| **Anchor system** | Left + right x-anchors | Keyword-based (ITEM NO. header, BID AMOUNT header), not position-based. Y-anchors deferred. |
| **Row types** | 5 types | HEADER, DATA, BOILERPLATE, CONTINUATION, SECTION_HEADER. Column count enforced on DATA only. |
| **Priors integration** | Adaptive upgrade | Fallback by default; promoted to peer if priors.confidence > 0.7 AND header.confidence < 0.5. |
| **Math validation** | Detection only | Flag items where qty × price ≠ amount. Log, don't auto-correct. |
| **Plan merge** | Single coherent plan | Combined recovery plan fixes with new analyzer capabilities. |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PDF Import Service                          │
│  (orchestrates preprocessing → OCR → extraction → post-processing)  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Image Preprocessing (Existing)                   │
│  - Rotation detection    - Deskew correction    - Contrast enhance │
│  - Adaptive thresholding - Denoising            - Fallback path    │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         OCR Engine (Existing)                       │
│  - Tesseract integration - Reversed text detection - Element bbox  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Row Classifier (NEW - Phase 1)                    │
│  - Score each row: HEADER | DATA | BOILERPLATE | CONTINUATION |    │
│    SECTION_HEADER                                                   │
│  - Feature extraction: keywords, digit ratio, legal patterns, etc. │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                Table Region Detector (NEW - Phase 2)                │
│  - Two-pass linear scan (replaces DP)                              │
│  - Find first HEADER with DATA rows following                       │
│  - Multi-table detection for Base Bid / Alternate Bid              │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│               Column Detector (ENHANCED - Phase 3)                  │
│  - Layer 1: Header keywords (existing)                             │
│  - Layer 2: Visual gridlines (existing)                            │
│  - Layer 3: Anchor-based page correction (NEW)                     │
│  - Cross-validation + adaptive priors upgrade                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Cell Extractor (Existing)                       │
│  - Assign elements to columns with tolerance                       │
│  - Re-OCR merged blocks with preprocessed images                   │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Table Row Parser (ENHANCED)                      │
│  - Use row type labels from classifier                             │
│  - Skip BOILERPLATE, merge CONTINUATION, handle SECTION_HEADER     │
│  - Item number artifact cleanup (existing)                         │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│               Post-Process Engine (ENHANCED - Phase 4)              │
│  - Cross-multiplication validation: qty × price ≈ amount?         │
│  - Batch-level column shift detection (existing)                   │
│  - Deduplication, normalization (existing)                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Row Classification Rules (Deterministic)

| Row Type | Detection Rules | Column Count |
|----------|-----------------|--------------|
| **HEADER** | 3+ header keywords (ITEM, NO, DESC, UNIT, QTY, PRICE, AMOUNT) AND compact (few tokens) AND ≥4 column-like tokens | Expected: 4-6 |
| **DATA** | Item-number pattern (`^\d+(\.\d+)?$`) AND ≥2 numeric values | Required: 5-6 |
| **BOILERPLATE** | Legal patterns (ARTICLE, SECTION, BID FORM, BIDDER) OR paragraph ratio >0.7 OR repeats across pages | Ignored |
| **CONTINUATION** | No item number AND 1-3 elements AND y-position within 1.5× row height of previous DATA row | Allowed: 1-3 |
| **SECTION_HEADER** | Full-width text (>80% table width) AND inside table region AND not matching DATA pattern | Allowed: 1 |

**Keywords** (normalized: uppercase, newlines collapsed, punctuation stripped):
- itemNumber: `ITEM NO`, `ITEM NUMBER`, `ITEM#`, `NO.`
- description: `DESCRIPTION`, `DESC`, `ITEM DESCRIPTION`
- unit: `UNIT`, `UNITS`, `U/M`
- quantity: `QUANTITY`, `QTY`, `EST. QUANTITY`, `EST QUANTITY`, `ESTIMATED QUANTITY`
- unitPrice: `UNIT PRICE`, `PRICE`, `UNIT BID`
- bidAmount: `BID AMOUNT`, `AMOUNT`, `TOTAL`, `EXTENSION`, `EXTENDED AMOUNT`

---

## Anchor-Based Page Correction (Layer 3)

### Purpose
Correct per-page x-position drift caused by scanner skew without full x-clustering complexity.

### Algorithm

```
1. From page 1 header detection:
   - left_anchor_x = x-position of ITEM NO. column start
   - right_anchor_x = x-position of BID AMOUNT column end
   - expected_width = right_anchor_x - left_anchor_x

2. For each subsequent page:
   a. Find leftmost element matching item-number pattern → actual_left_x
   b. Find rightmost element matching currency pattern → actual_right_x
   c. actual_width = actual_right_x - actual_left_x

   d. Compute correction:
      - offset = left_anchor_x - actual_left_x
      - scale = expected_width / actual_width (if within 0.9-1.1, else 1.0)

   e. Apply to all elements on page:
      corrected_x = (element_x - actual_left_x) * scale + left_anchor_x
```

### Priors Confidence Formula

```
confidence = min(dataRowsUsed / 10, 1.0) × anchorQuality

Where anchorQuality:
  - Both anchors found on this page = 1.0
  - Only one anchor found = 0.6
  - No anchors, using global average = 0.3
```

### Adaptive Upgrade Rule

```
IF priors.confidence > 0.7 AND header.confidence < 0.5:
    → Priors participate in cross-validation as peer
ELSE:
    → Priors only used as fallback (replace static ratios)
```

---

## Cross-Multiplication Validation

### Purpose
Validate column correctness using mathematical relationship: `bidAmount ≈ unitPrice × quantity`

### Rules

| Scenario | Match Threshold | Confidence Impact |
|----------|-----------------|-------------------|
| Exact match | `abs(amount - qty*price) < 0.01` | 1.0 |
| Within rounding | `abs(amount - qty*price) / amount < 0.01` | 0.95 |
| Minor discrepancy | `0.01 < ratio < 0.05` | 0.7 (flag for review) |
| Major discrepancy | `ratio > 0.05` | 0.3 (likely column error) |

### Exclusions
- LS (Lump Sum) items: use `amount ≈ price` instead
- qty=0 or missing: skip validation
- SECTION_HEADER rows: skip validation
- Subtotal rows: skip validation

### Output
- Per-item: `mathValidation: { expected, actual, ratio, status }`
- Batch-level: `mathValidationRate: validItems / totalItems`

---

## Phases (Each Phase = One PR)

### Phase 0: Observability + Scaffolding ✓ (Completed in Recovery Plan)
**Status**: Already implemented. Keep existing logging infrastructure.

**Preserved from Recovery Plan:**
- Build metadata in logs
- Preprocessing lifecycle logging
- Re-OCR source tracking
- Extraction summary at end of import

---

### Phase 1: Row Classifier
**Goal**: Classify every OCR row into one of 5 types with confidence scores.

**New Files:**
- `lib/features/pdf/services/table_extraction/row_classifier.dart`
- `lib/features/pdf/services/table_extraction/models/row_classification.dart`

**Changes:**
- Add `RowClassifier` class with `classifyRow(List<OcrElement> row, RowContext context) → RowClassification`
- Add `RowClassification` model: `{ rowType, confidence, features, warnings }`
- Add `RowFeatures` struct: keyword hits, digit ratio, currency ratio, legal patterns, etc.

**Tests:**
- `test/features/pdf/table_extraction/row_classifier_test.dart`
  - Springfield-style row samples
  - Boilerplate patterns (legal text, headers)
  - Continuation rows (no item number, short)
  - Section headers (full-width text)

**Acceptance Criteria:**
- Legal text rows classified as BOILERPLATE with confidence > 0.8
- Data rows with item numbers classified as DATA with confidence > 0.9
- Multi-line description continuations classified as CONTINUATION
- Section dividers ("EARTHWORK", "CONCRETE") classified as SECTION_HEADER

---

### Phase 2: Table Region Detector (Two-Pass)
**Goal**: Replace DP with simple, deterministic table region detection.

**Algorithm:**
```
Pass 1: Classify all rows using RowClassifier

Pass 2: Find table regions
  for each row in order:
    if row.type == HEADER and next 2+ rows are DATA:
      table_start = row
      continue scanning until:
        - 3+ consecutive BOILERPLATE rows, or
        - New HEADER with different column structure (multi-table case)
      table_end = last DATA row before break
      emit TableRegion(start, end, header_row)
```

**New Files:**
- `lib/features/pdf/services/table_extraction/table_region_detector.dart`

**Changes:**
- Add `TableRegionDetector.detectRegions(classifiedRows) → List<TableRegion>`
- Integrate with `TableLocator` (or replace if cleaner)

**Multi-Table Support:**
- Detect "BASE BID", "ALTERNATE BID" markers as region separators
- Each region processed independently
- Return `List<TableRegion>` instead of single region

**Tests:**
- `test/features/pdf/table_extraction/table_region_detector_test.dart`
  - Page 1 with boilerplate above table
  - Multi-page table continuation
  - Two separate tables (Base + Alternate)
  - Table with section headers mid-table

**Acceptance Criteria:**
- Boilerplate on page 1 never included in table region
- Table start correctly identified at actual header row
- Multi-table PDFs return separate regions

---

### Phase 3: Anchor-Based Column Correction
**Goal**: Add Layer 3 (anchor correction) to column detection.

**Changes to Existing Files:**
- `lib/features/pdf/services/table_extraction/column_detector.dart`
  - Add `_computeAnchorCorrection(page, headerBoundaries) → PageCorrection`
  - Add `_applyCorrection(elements, correction) → correctedElements`
  - Integrate into `detectColumns()` flow
  - Add adaptive upgrade logic (fallback vs. peer)

- `lib/features/pdf/services/table_extraction/models/page_correction.dart` (new)
  - `PageCorrection { offset, scale, leftAnchorX, rightAnchorX, confidence }`

**Constants:**
```dart
const kMinScaleRatio = 0.9;  // Ignore scale correction if < 10% difference
const kMaxScaleRatio = 1.1;  // Ignore scale correction if > 10% difference
const kPriorsPromotionThreshold = 0.7;  // Promote priors to peer above this
const kHeaderWeakThreshold = 0.5;  // Headers considered weak below this
```

**Tests:**
- `test/features/pdf/table_extraction/column_detector_test.dart`
  - Page with 10px offset → corrected
  - Page with 5% scale difference → corrected
  - Fallback path uses priors instead of static ratios
  - Adaptive upgrade when priors strong + headers weak

**Acceptance Criteria:**
- Per-page x-offset corrected within 5px
- Fallback confidence improves from 0.0-0.3 to 0.3-0.6
- No regression on pages where headers/lines already work

---

### Phase 4: Post-Processing Enhancements
**Goal**: Add cross-multiplication validation and preserve recovery plan fixes.

**Preserved from Recovery Plan:**
- OCR artifact cleanup (`_cleanItemNumberArtifacts`)
- Page number detection in splitter
- Batch-level column shift validation
- Deduplication and normalization

**New Additions:**
- `lib/features/pdf/services/table_extraction/post_process/post_process_math_validation.dart`
  - `validateMathRelationship(items) → MathValidationResult`
  - Per-item flags + batch-level rate
  - Skip LS items, subtotals, section headers

**Changes:**
- `lib/features/pdf/services/table_extraction/post_process/post_process_engine.dart`
  - Add `_runMathValidation()` step after column shift detection
  - Add validation results to diagnostics

**Tests:**
- `test/features/pdf/table_extraction/post_process/post_process_math_validation_test.dart`
  - Correct items pass validation
  - Column-shifted items fail validation
  - LS items handled correctly
  - Batch rate calculated accurately

**Acceptance Criteria:**
- Items with correct columns show > 0.9 math validation rate
- Column shift errors show < 0.5 math validation rate
- Validation results logged and included in diagnostics

---

### Phase 5: Parser Integration
**Goal**: Use row classifications in TableRowParser.

**Changes:**
- `lib/features/pdf/services/table_extraction/table_row_parser.dart`
  - Accept optional `rowClassifications` parameter
  - Skip BOILERPLATE rows explicitly (don't attempt parsing)
  - Merge CONTINUATION rows with previous DATA row
  - Preserve SECTION_HEADER rows in output (as metadata, not items)
  - Handle subtotal rows (parse but don't add to item count)

**Tests:**
- `test/features/pdf/table_extraction/table_row_parser_test.dart`
  - BOILERPLATE rows skipped (no item created)
  - CONTINUATION rows merged with previous item
  - SECTION_HEADER preserved in output
  - Subtotal rows parsed but flagged

**Acceptance Criteria:**
- No legal text appears as items
- Multi-line descriptions fully captured
- Section headers accessible in output
- Item count matches expected (131 for Springfield)

---

### Phase 6: Regression Guard + Verification
**Goal**: Lock in accuracy and prevent future regressions.

**Preserved from Recovery Plan:**
- Springfield baseline ≥ 85 items (hard floor)
- Numeric item number validation

**Enhanced:**
- Springfield target: ≥ 125 items (95%+)
- Math validation rate: ≥ 80% for valid PDFs
- Per-phase logging with metrics

**Tests:**
- `test/features/pdf/table_extraction/springfield_integration_test.dart`
  - Assert item count ≥ 125
  - Assert all item numbers are numeric
  - Assert math validation rate ≥ 0.8
  - Assert no BOILERPLATE rows in output

**Verification Checklist:**
- [ ] All 690+ existing tests pass
- [ ] Springfield extraction ≥ 125/131 items
- [ ] No OCR artifact corruption in item numbers
- [ ] Cross-multiplication validation rate ≥ 80%
- [ ] Logs show row classifications and anchor corrections

---

## Edge Cases Handled

| Edge Case | How Addressed | Phase |
|-----------|---------------|-------|
| **Boilerplate on page 1** | Row classifier marks as BOILERPLATE; region detector skips | 1, 2 |
| **Multi-line descriptions** | CONTINUATION row type; parser merges with previous item | 1, 5 |
| **Multi-line headers** | Existing normalization (collapse newlines); enhanced keyword matching | (existing) |
| **Per-page x-drift** | Anchor-based correction in column detector | 3 |
| **Multiple tables** | Region detector returns List<TableRegion> | 2 |
| **Section headers** | SECTION_HEADER row type; preserved in output | 1, 5 |
| **Subtotal rows** | Detected and flagged; excluded from math validation | 4, 5 |
| **Reversed text (page 6)** | Existing `_detectAndFixReversedText()` preserved | (existing) |
| **Column shift** | Batch-level validation + math validation detect shifts | 4 |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| **Regression on non-Springfield PDFs** | Adaptive upgrade keeps priors conservative; fallback-only by default |
| **CONTINUATION/BOILERPLATE confusion** | CONTINUATION requires y-proximity to previous DATA row |
| **Anchor not found** | Fall back to global average with reduced confidence |
| **Multi-table detection false positives** | Require explicit markers ("BASE BID", "ALTERNATE") |
| **Math validation fails on PDFs with rounding** | 1% tolerance; flag but don't reject |
| **Performance overhead** | Row classification is O(n); anchor correction is O(pages); minimal impact |

---

## Files Changed Summary

**New Files (6):**
- `lib/features/pdf/services/table_extraction/row_classifier.dart`
- `lib/features/pdf/services/table_extraction/models/row_classification.dart`
- `lib/features/pdf/services/table_extraction/table_region_detector.dart`
- `lib/features/pdf/services/table_extraction/models/page_correction.dart`
- `lib/features/pdf/services/table_extraction/post_process/post_process_math_validation.dart`
- Tests for each new file

**Modified Files (~8):**
- `column_detector.dart` (anchor correction + adaptive upgrade)
- `table_row_parser.dart` (use row classifications)
- `post_process_engine.dart` (add math validation step)
- `table_extractor.dart` (orchestrate new components)
- Integration tests

**Preserved Unchanged:**
- All OCR preprocessing (image_preprocessor.dart)
- All existing cleanup logic (post_process_normalization.dart, etc.)
- Debug logging infrastructure
- Reversed text detection in OCR engine

---

## Success Definition

1. **Springfield extraction ≥ 95%** (125+/131 items) consistently
2. **Zero boilerplate pollution** — legal text never parsed as items
3. **Multi-line descriptions captured** — no truncation from CONTINUATION handling
4. **Column detection confidence stable** (> 0.75 average)
5. **Math validation rate ≥ 80%** for correctly extracted items
6. **Logs prove path taken** — row classifications, anchor corrections, validation results all logged
7. **All 690+ existing tests pass** — no regressions

---

## Implementation Order

```
Phase 0: Verify existing observability (no changes needed)
   ↓
Phase 1: Row Classifier (foundation for everything else)
   ↓
Phase 2: Table Region Detector (uses classifier output)
   ↓
Phase 3: Anchor Correction (independent of classifier/region)
   ↓
Phase 4: Math Validation (independent, can parallelize with Phase 3)
   ↓
Phase 5: Parser Integration (uses classifier + region output)
   ↓
Phase 6: Regression Guard (final verification)
```

Phases 3 and 4 can be implemented in parallel if desired.

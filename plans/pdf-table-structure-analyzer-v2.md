# PDF Table Structure Analyzer Plan v2.1 (Post-Review)

**Created**: 2026-02-05
**Last Updated**: 2026-02-05
**Status**: Draft v2.1 (Post-Review)
**Supersedes**: `pdf-table-structure-analyzer-plan.md`, `pdf-extraction-regression-recovery-plan.md`

## Goal

Create a robust, deterministic, offline algorithm that reliably extracts table data from construction bid PDFs, achieving **95%+ accuracy** (125+/131 items on Springfield) without hardcoded position rules.

---

## Design Decisions (From Initial Brainstorming)

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

## Design Decisions (Post-Review - 14 Decisions)

### HIGH-RISK GAPS

1. **Two-pass Row Classification (resolves circular dependency)**: Split Phase 1 into Phase 1A (pre-column) and Phase 1B (post-column). Phase 1A uses ONLY text content and bounding box geometry—no column boundaries. Phase 1B refines UNKNOWN rows after column detection completes.

2. **Cross-page header confirmation in Phase 2**: Phase 2 includes cross-page lookahead when row.type == HEADER and row.yCenter > 70% of page height. Checks next 2-3 rows from following page for DATA rows to confirm table continuation.

3. **Item number regex alignment**: Unified pattern `^\d+(\.\d+)?\.?$` to match TableRowParser._itemNumberPattern and handle trailing dot artifacts from OCR.

4. **Multi-row header assembly in Phase 2**: Region Detector (not Phase 1) handles multi-row header assembly by checking if consecutive HEADER rows have complementary keywords and combining them into a single header region.

### MEDIUM-RISK GAPS

5. **Gridline artifact rejection**: LineColumnDetector applies line quality scoring; rejects lines with <60% coverage ratio (too many gaps = noise, not a real gridline). Falls back to header-only detection if line quality is low.

6. **Anchor candidate filtering**: Restrict anchor selection to DATA rows within table bounds only. Require both anchors found on ≥60% of pages; if missing, use global average with reduced confidence.

7. **Table termination refinement**: SECTION_HEADER rows do NOT count toward the "3+ consecutive BOILERPLATE" termination rule. Only true BOILERPLATE rows trigger termination.

8. **SECTION_HEADER detection hardening**: Phase 1B requires full-width text (>80% detected table width) AND no numeric columns AND no legal patterns AND not matching DATA pattern.

9. **Column count relaxation**: DATA row post-validation changed from "Required: 5-6" to "Post-validation: 3-8" to support lump-sum schedules (min 3) and extended schedules (max 8).

### INTEGRATION GAPS

10. **Bootstrap + Anchor merge strategy**: Bootstrap runs first (base column boundaries from strongest line-detected page). Anchor correction then applies offset/scale adjustment on top of bootstrapped results per-page. Add `ColumnDetectionMethod.anchorCorrected` enum value.

11. **Optional parser integration**: Add optional `rowClassifications` parameter to `TableRowParser.parseRows()`. When provided, classifier takes precedence. When null, existing logic runs unchanged (backward compatible).

12. **Math validation as hard diagnostic**: Keep math validation detection-only (no auto-correction), but explicitly log as hard diagnostic that feeds into regression tests. Assert math validation rate in integration tests.

### OTHER

13. **Adaptive row grouping threshold**: Replace fixed `kRowYThreshold = 15.0` with adaptive threshold computed as median element height per page × multiplier (0.5). Aligns TableLocator to CellExtractor's existing kYThresholdMultiplier approach.

14. **Clean artifacts before classifying**: RowClassifier (Phase 1A) applies `_cleanItemNumberArtifacts()` and text normalization BEFORE checking item number patterns to handle degraded OCR ("4Z" → "42").

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
│               Row Classifier Phase 1A (NEW - Pre-Column)            │
│  - Score each row: HEADER | DATA | BOILERPLATE | CONTINUATION |    │
│    UNKNOWN (no SECTION_HEADER yet)                                 │
│  - Feature extraction: keywords, digit ratio, legal patterns       │
│  - Uses ONLY text content + bbox geometry (no column boundaries)   │
│  - Cleans artifacts BEFORE classification (Decision 14)            │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│            Table Region Detector (NEW - Phase 2)                    │
│  - Two-pass linear scan (replaces DP)                              │
│  - Find first HEADER with DATA rows following                      │
│  - Cross-page lookahead for bottom-of-page headers (Decision 2)    │
│  - Multi-row header assembly (Decision 4)                          │
│  - Multi-table detection for Base Bid / Alternate Bid              │
│  - Adaptive row grouping threshold (Decision 13)                   │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│               Column Detector (ENHANCED - Phase 3)                  │
│  - Layer 1: Header keywords (existing)                             │
│  - Layer 2: Visual gridlines with quality scoring (Decision 5)     │
│  - Layer 3: Anchor-based page correction (NEW)                     │
│    - Bootstrap + anchor merge (Decision 10)                        │
│    - Anchor filtering to DATA rows only (Decision 6)               │
│  - Cross-validation + adaptive priors upgrade                      │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│           Row Classifier Phase 1B (NEW - Post-Column)               │
│  - Refine UNKNOWN rows → SECTION_HEADER (Decision 8)               │
│  - Requires column boundaries now available                        │
│  - Uses detected table width for full-width check                  │
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
│                    Table Row Parser (ENHANCED - Phase 5)            │
│  - Optional rowClassifications parameter (Decision 11)             │
│  - Use row type labels from classifier when provided               │
│  - Skip BOILERPLATE, merge CONTINUATION, handle SECTION_HEADER     │
│  - Item number artifact cleanup (existing)                         │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│               Post-Process Engine (ENHANCED - Phase 4)              │
│  - Cross-multiplication validation: qty × price ≈ amount?         │
│    (Hard diagnostic for regression tests - Decision 12)            │
│  - Batch-level column shift detection (existing)                   │
│  - Deduplication, normalization (existing)                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Row Classification Rules (Deterministic)

| Row Type | Detection Rules | Post-Validation | Notes |
|----------|-----------------|-----------------|-------|
| **HEADER** | 3+ header keywords (ITEM, NO, DESC, UNIT, QTY, PRICE, AMOUNT) AND compact (few tokens) AND ≥4 column-like tokens | Expected: 4-6 elements | Keyword density gating: (3+ keywords & 40%+ density) OR (2+ keywords & 70%+ density) |
| **DATA** | Item-number pattern (`^\d+(\.\d+)?\.?$`) AND ≥1 numeric element AND 3-8 elements | 3-8 elements | Min 3 (lump-sum), max 8 (extended schedules). Artifacts cleaned BEFORE pattern check (Decision 14). |
| **BOILERPLATE** | Legal patterns (ARTICLE, SECTION, BID FORM, BIDDER) OR paragraph ratio >0.7 OR repeats across pages | Ignored | Triggers table termination when 3+ consecutive rows (Decision 7) |
| **CONTINUATION** | No item number AND 1-3 elements AND y-position within 1.5× row height of previous DATA row | Allowed: 1-3 | Merged with previous DATA row in parser |
| **SECTION_HEADER** | Full-width text (>80% detected table width) AND no numeric columns AND no legal patterns AND not matching DATA pattern | Allowed: 1 | ONLY classified in Phase 1B (post-column). Does NOT trigger termination (Decision 7). |
| **UNKNOWN** | Rows that don't match any pattern | N/A | Refined to SECTION_HEADER or BOILERPLATE in Phase 1B |

**Important Notes:**
- Row classification (Phase 1A) uses only text content, bounding box geometry, and keyword patterns. Column boundaries are NOT required.
- "Post-Validation" column refers to element count (# of OCR elements), not column count.
- Item number pattern aligned to TableRowParser._itemNumberPattern (Decision 3).
- Unsupported formats: sub-item numbering ("203.03.1"), letter suffixes ("42a"), Roman numerals.

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
   a. Filter anchor candidates to DATA rows within table bounds (Decision 6)
   b. Find leftmost element matching item-number pattern → actual_left_x
   c. Find rightmost element matching currency pattern → actual_right_x
   d. actual_width = actual_right_x - actual_left_x

   e. Compute correction:
      - offset = left_anchor_x - actual_left_x
      - scale = expected_width / actual_width (if within 0.9-1.1, else 1.0)

   f. Apply to all elements on page:
      corrected_x = (element_x - actual_left_x) * scale + left_anchor_x

3. Integration with Bootstrap (Decision 10):
   - Bootstrap runs FIRST (gives base column boundaries from strongest line-detected page)
   - Anchor correction runs AFTER bootstrap (applies offset/scale adjustment per-page)
   - Add ColumnDetectionMethod.anchorCorrected enum value
   - Precedence: line-detected > cross-validated > anchor-corrected > header-only > fallback
```

### Anchor Validation (Decision 6)
- Require both anchors found on ≥60% of pages
- If anchor missing on a page, use global average with reduced confidence
- Do NOT allow boilerplate, footer, or section header elements as anchor candidates

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

## Cross-Multiplication Validation (Decision 12)

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
- **Hard Diagnostic**: Assert math validation rate in integration tests

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

### Phase 1: Row Classifier (Two-Pass: 1A Pre-Column + 1B Post-Column)
**Goal**: Classify every OCR row into one of 5 types with confidence scores.

**New Files:**
- `lib/features/pdf/services/table_extraction/row_classifier.dart`
- `lib/features/pdf/services/table_extraction/models/row_classification.dart`

**Phase 1A (Pre-Column) - Decision 1:**
- Runs BEFORE Phase 3 (Column Detection)
- Classifies: HEADER, DATA, BOILERPLATE, CONTINUATION, UNKNOWN
- Uses ONLY text content, bounding box geometry, keyword patterns
- No column boundaries required
- Applies `_cleanItemNumberArtifacts()` BEFORE pattern matching (Decision 14)
- Item number pattern: `^\d+(\.\d+)?\.?$` (Decision 3)
- Adaptive row grouping threshold: median element height × 0.5 (Decision 13)

**Phase 1B (Post-Column) - Decisions 1, 8:**
- Runs AFTER Phase 3 (Column Detection)
- Refines UNKNOWN rows → SECTION_HEADER OR BOILERPLATE
- SECTION_HEADER requires:
  - Full-width text (>80% detected table width)
  - No numeric columns (no price/amount patterns)
  - No legal patterns
  - Not matching DATA pattern
- Otherwise → BOILERPLATE

**Changes:**
- Add `RowClassifier` class with `classifyRowPreColumn()` and `refineRowPostColumn()`
- Add `RowClassification` model: `{ rowType, confidence, features, warnings }`
- Add `RowFeatures` struct: keyword hits, digit ratio, currency ratio, legal patterns, etc.

**Tests:**
- `test/features/pdf/table_extraction/row_classifier_test.dart`
  - Springfield-style row samples
  - Boilerplate patterns (legal text, headers)
  - Continuation rows (no item number, short)
  - Section headers (full-width text)
  - Artifact cleaning ("4Z" → "42")
  - Trailing dot handling ("42." → "42")

**Acceptance Criteria:**
- Legal text rows classified as BOILERPLATE with confidence > 0.8
- Data rows with item numbers classified as DATA with confidence > 0.9
- Multi-line description continuations classified as CONTINUATION
- Section dividers ("EARTHWORK", "CONCRETE") classified as SECTION_HEADER (Phase 1B only)
- Degraded OCR artifacts cleaned before classification

---

### Phase 2: Table Region Detector (Two-Pass + Cross-Page Lookahead)
**Goal**: Replace DP with simple, deterministic table region detection.

**Algorithm (Decisions 2, 4, 7, 13):**
```
Pass 1: Classify all rows using RowClassifier Phase 1A (all pages)

Pass 2: Find table regions
  for each row in order:
    if row.type == HEADER:
      # Cross-page header confirmation (Decision 2)
      if row.yCenter > (pageHeight * 0.70):
        if next 5 rows have no DATA type:
          scan first 2-3 rows from next page for DATA type
          if no DATA found: skip this header (likely false positive)

      # Check if DATA rows follow
      if next 2+ rows are DATA:
        table_start = row

        # Multi-row header assembly (Decision 4)
        if next row is ALSO HEADER with complementary keywords:
          combine into single header region
          record both Y positions in headerRowYPositions
          skip consumed row

        continue scanning until:
          - 3+ consecutive BOILERPLATE rows (Decision 7: SECTION_HEADER rows do NOT count)
          - New HEADER with different column structure (multi-table case)
        table_end = last DATA row before break
        emit TableRegion(start, end, header_row)
```

**Constants (Decision 2):**
```dart
const kTypicalPageHeight = 2550.0;
const kPageBottomThreshold = 0.70;  // Cross-page lookahead threshold
const kCrossPageLookaheadRows = 2;  // Number of rows to check on next page
const kAdaptiveRowYMultiplier = 0.5;  // For adaptive threshold (Decision 13)
```

**New Files:**
- `lib/features/pdf/services/table_extraction/table_region_detector.dart`

**Changes:**
- Add `TableRegionDetector.detectRegions(classifiedRows) → List<TableRegion>`
- Integrate with `TableLocator` (or replace if cleaner)
- Replace fixed `kRowYThreshold = 15.0` with adaptive threshold (Decision 13)

**Multi-Table Support:**
- Detect "BASE BID", "ALTERNATE BID" markers as region separators
- Each region processed independently
- Return `List<TableRegion>` instead of single region

**Tests:**
- `test/features/pdf/table_extraction/table_region_detector_test.dart`
  - Page 1 with boilerplate above table
  - Multi-page table continuation
  - Two separate tables (Base + Alternate)
  - Table with section headers mid-table (should not trigger termination)
  - Bottom-of-page headers requiring cross-page lookahead
  - Multi-row headers ("Item\nNo.", "Est.\nQuantity")
  - Repeated page headers (should not count toward termination)

**Acceptance Criteria:**
- Boilerplate on page 1 never included in table region
- Table start correctly identified at actual header row
- Multi-table PDFs return separate regions
- Multi-row headers correctly assembled
- Cross-page header confirmation prevents false positives

---

### Phase 3: Anchor-Based Column Correction + Gridline Quality Scoring
**Goal**: Add Layer 3 (anchor correction) to column detection with gridline artifact rejection.

**Changes to Existing Files:**
- `lib/features/pdf/services/table_extraction/column_detector.dart`
  - Add `_computeAnchorCorrection(page, headerBoundaries) → PageCorrection`
  - Add `_applyCorrection(elements, correction) → correctedElements`
  - Integrate into `detectColumns()` flow
  - Add adaptive upgrade logic (fallback vs. peer)
  - Bootstrap + anchor merge strategy (Decision 10)

- `lib/features/pdf/services/table_extraction/line_column_detector.dart` (Decision 5)
  - Add line quality scoring
  - Reject lines with <60% coverage ratio
  - Fall back to header-only detection if line quality is low

- `lib/features/pdf/services/table_extraction/models/page_correction.dart` (new)
  - `PageCorrection { offset, scale, leftAnchorX, rightAnchorX, confidence }`

- `lib/features/pdf/services/table_extraction/models/column_detection_method.dart`
  - Add `ColumnDetectionMethod.anchorCorrected` enum value (Decision 10)

**Constants:**
```dart
const kMinScaleRatio = 0.9;  // Ignore scale correction if < 10% difference
const kMaxScaleRatio = 1.1;  // Ignore scale correction if > 10% difference
const kPriorsPromotionThreshold = 0.7;  // Promote priors to peer above this
const kHeaderWeakThreshold = 0.5;  // Headers considered weak below this
const kMinAnchorPageCoverage = 0.6;  // Require anchors on 60%+ of pages (Decision 6)
const kLineCoverageThreshold = 0.6;  // Reject lines with <60% coverage (Decision 5)
```

**Tests:**
- `test/features/pdf/table_extraction/column_detector_test.dart`
  - Page with 10px offset → corrected
  - Page with 5% scale difference → corrected
  - Fallback path uses priors instead of static ratios
  - Adaptive upgrade when priors strong + headers weak
  - Anchor filtering to DATA rows only
  - Missing anchors fall back to global average with reduced confidence
  - Gridline quality scoring rejects noisy lines
  - Bootstrap runs before anchor correction

**Acceptance Criteria:**
- Per-page x-offset corrected within 5px
- Fallback confidence improves from 0.0-0.3 to 0.3-0.6
- No regression on pages where headers/lines already work
- Anchor correction only uses DATA rows within table bounds
- Gridline artifacts rejected, fall back to header-only

---

### Phase 4: Post-Processing Enhancements + Math Validation
**Goal**: Add cross-multiplication validation and preserve recovery plan fixes.

**Preserved from Recovery Plan:**
- OCR artifact cleanup (`_cleanItemNumberArtifacts`)
- Page number detection in splitter
- Batch-level column shift validation
- Deduplication and normalization

**New Additions (Decision 12):**
- `lib/features/pdf/services/table_extraction/post_process/post_process_math_validation.dart`
  - `validateMathRelationship(items) → MathValidationResult`
  - Per-item flags + batch-level rate
  - Skip LS items, subtotals, section headers
  - Detection-only (no auto-correction)
  - Hard diagnostic for regression tests

**Changes:**
- `lib/features/pdf/services/table_extraction/post_process/post_process_engine.dart`
  - Add `_runMathValidation()` step after column shift detection
  - Add validation results to diagnostics
  - Log as hard diagnostic for regression tests

**Tests:**
- `test/features/pdf/table_extraction/post_process/post_process_math_validation_test.dart`
  - Correct items pass validation
  - Column-shifted items fail validation
  - LS items handled correctly
  - Batch rate calculated accurately
  - Validation results logged

**Acceptance Criteria:**
- Items with correct columns show > 0.9 math validation rate
- Column shift errors show < 0.5 math validation rate
- Validation results logged and included in diagnostics
- No auto-correction applied (detection only)

---

### Phase 5: Parser Integration (Optional Row Classifications)
**Goal**: Use row classifications in TableRowParser.

**Changes (Decision 11):**
- `lib/features/pdf/services/table_extraction/table_row_parser.dart`
  - Accept optional `rowClassifications` parameter
  - When provided:
    - Classifier takes precedence
    - Skip BOILERPLATE rows explicitly (don't attempt parsing)
    - Merge CONTINUATION rows with previous DATA row
    - Preserve SECTION_HEADER rows in output (as metadata, not items)
    - Handle subtotal rows (parse but don't add to item count)
  - When null:
    - Existing `_isHeaderRow()` and continuation detection run unchanged
    - Backward compatible
  - This allows Phases 1 and 5 to be developed and tested independently

**Tests:**
- `test/features/pdf/table_extraction/table_row_parser_test.dart`
  - BOILERPLATE rows skipped (no item created)
  - CONTINUATION rows merged with previous item
  - SECTION_HEADER preserved in output
  - Subtotal rows parsed but flagged
  - Backward compatibility (null parameter uses existing logic)

**Acceptance Criteria:**
- No legal text appears as items
- Multi-line descriptions fully captured
- Section headers accessible in output
- Item count matches expected (131 for Springfield)
- Backward compatible when rowClassifications is null

---

### Phase 6: Regression Guard + Verification (Hard Diagnostics)
**Goal**: Lock in accuracy and prevent future regressions.

**Preserved from Recovery Plan:**
- Springfield baseline ≥ 85 items (hard floor)
- Numeric item number validation

**Enhanced (Decision 12):**
- Springfield target: ≥ 125 items (95%+)
- Math validation rate: ≥ 80% for valid PDFs
- Per-phase logging with metrics
- Math validation as hard diagnostic in integration tests

**Tests:**
- `test/features/pdf/table_extraction/springfield_integration_test.dart`
  - Assert item count ≥ 125
  - Assert all item numbers are numeric
  - Assert math validation rate ≥ 0.8 (hard diagnostic)
  - Assert no BOILERPLATE rows in output
  - Assert no gridline artifacts in column detection

**Verification Checklist:**
- [ ] All 690+ existing tests pass
- [ ] Springfield extraction ≥ 125/131 items
- [ ] No OCR artifact corruption in item numbers
- [ ] Cross-multiplication validation rate ≥ 80%
- [ ] Logs show row classifications and anchor corrections
- [ ] Math validation logged as hard diagnostic

---

## Edge Cases Handled

| Edge Case | How Addressed | Phase | Decision |
|-----------|---------------|-------|----------|
| **Boilerplate on page 1** | Row classifier marks as BOILERPLATE; region detector skips | 1A, 2 | 1 |
| **Multi-line descriptions** | CONTINUATION row type; parser merges with previous item | 1A, 5 | 1, 11 |
| **Multi-line headers** | Region detector assembles complementary HEADER rows | 2 | 4 |
| **Bottom-of-page headers** | Cross-page lookahead checks next page for DATA rows | 2 | 2 |
| **Per-page x-drift** | Anchor-based correction in column detector | 3 | 6, 10 |
| **Multiple tables** | Region detector returns List<TableRegion> | 2 | - |
| **Section headers** | SECTION_HEADER row type (Phase 1B only); preserved in output | 1B, 5 | 1, 7, 8 |
| **Subtotal rows** | Detected and flagged; excluded from math validation | 4, 5 | 12 |
| **Reversed text (page 6)** | Existing `_detectAndFixReversedText()` preserved | (existing) | - |
| **Column shift** | Batch-level validation + math validation detect shifts | 4 | 12 |
| **Gridline artifacts** | Line quality scoring rejects lines with <60% coverage | 3 | 5 |
| **Degraded OCR artifacts** | Clean artifacts BEFORE classification | 1A | 14 |
| **Lump-sum schedules** | Relaxed column count: 3-8 instead of 5-6 | 1A | 9 |
| **Repeated page headers** | Do not count toward table termination | 2 | 7 |

---

## Risks & Mitigations

| Risk | Mitigation | Decision |
|------|------------|----------|
| **Regression on non-Springfield PDFs** | Adaptive upgrade keeps priors conservative; fallback-only by default | - |
| **CONTINUATION/BOILERPLATE confusion** | CONTINUATION requires y-proximity to previous DATA row | 1 |
| **Anchor not found** | Fall back to global average with reduced confidence | 6 |
| **Anchor quality low** | Require anchors on ≥60% of pages; use global average otherwise | 6 |
| **Multi-table detection false positives** | Require explicit markers ("BASE BID", "ALTERNATE") | - |
| **Math validation fails on PDFs with rounding** | 1% tolerance; flag but don't reject | 12 |
| **Performance overhead** | Row classification is O(n); anchor correction is O(pages); minimal impact | - |
| **Bottom-of-page headers false positives** | Cross-page lookahead confirms DATA rows on next page | 2 |
| **SECTION_HEADER over-detection** | Requires full-width + no numeric columns + no legal patterns (Phase 1B only) | 8 |
| **Gridline artifacts** | Line quality scoring rejects <60% coverage; fall back to header-only | 5 |
| **Circular dependency (row classification needs columns)** | Two-pass: Phase 1A (pre-column) → Phase 3 (columns) → Phase 1B (post-column) | 1 |
| **Bootstrap + anchor conflict** | Bootstrap runs first; anchor correction applies on top | 10 |

---

## Files Changed Summary

**New Files (7):**
- `lib/features/pdf/services/table_extraction/row_classifier.dart`
- `lib/features/pdf/services/table_extraction/models/row_classification.dart`
- `lib/features/pdf/services/table_extraction/table_region_detector.dart`
- `lib/features/pdf/services/table_extraction/models/page_correction.dart`
- `lib/features/pdf/services/table_extraction/post_process/post_process_math_validation.dart`
- Test files for each new file
- Integration test enhancements

**Modified Files (~10):**
- `column_detector.dart` (anchor correction + adaptive upgrade + bootstrap merge)
- `line_column_detector.dart` (line quality scoring)
- `table_row_parser.dart` (optional rowClassifications parameter)
- `post_process_engine.dart` (add math validation step)
- `table_extractor.dart` (orchestrate new components)
- `models/column_detection_method.dart` (add anchorCorrected enum)
- Integration tests (hard diagnostics)

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
5. **Math validation rate ≥ 80%** for correctly extracted items (hard diagnostic in tests)
6. **Logs prove path taken** — row classifications, anchor corrections, validation results all logged
7. **All 690+ existing tests pass** — no regressions
8. **Gridline artifacts rejected** — <60% coverage lines do not influence column detection
9. **Cross-page headers handled** — bottom-of-page headers confirmed via lookahead
10. **Backward compatible** — rowClassifications parameter is optional

---

## Implementation Order

```
Phase 0: Verify existing observability (no changes needed)
   ↓
Phase 1A: Row Classifier (Pre-Column)
   ↓
Phase 2: Table Region Detector (uses Phase 1A output)
   ↓
Phase 3: Column Detection (anchor correction + gridline quality + bootstrap merge)
   ↓
Phase 1B: Row Classifier (Post-Column) — refines UNKNOWN → SECTION_HEADER
   ↓
Phase 4: Math Validation (independent, can parallelize with Phase 1B)
   ↓
Phase 5: Parser Integration (uses Phase 1A/1B output)
   ↓
Phase 6: Regression Guard (final verification + hard diagnostics)
```

**Note**: Phase 1B MUST run after Phase 3 (requires column boundaries). Phases 3 and 4 can be implemented in parallel if desired.

---

## Document Change Log

| Version | Date | Changes |
|---------|------|---------|
| v2.0 | 2026-02-05 | Initial merged plan (combined recovery plan + new analyzer) |
| v2.1 | 2026-02-05 | Post-review update: integrated 14 design decisions from brainstorming session |

---

**End of Plan**

# PDF Extraction Pipeline V2 — PRD 2.0

**Date**: 2026-02-11
**Status**: Approved
**Supersedes**: `2026-02-10-pdf-extraction-pipeline-redesign.md` (PRD 1.0)
**Scope**: Complete specification of the V2 extraction pipeline as-built + all approved enhancements

---

## Table of Contents

1. [Pipeline Architecture](#1-pipeline-architecture)
2. [Stage-by-Stage Specification](#2-stage-by-stage-specification)
3. [Confidence Scoring Model](#3-confidence-scoring-model)
4. [Quality Gate & Re-Extraction Loop](#4-quality-gate--re-extraction-loop)
5. [Coordinate Normalization](#5-coordinate-normalization)
6. [Document Total Checksum Validation](#6-document-total-checksum-validation)
7. [Data Models](#7-data-models)
8. [Diagnostic Feedback Loop](#8-diagnostic-feedback-loop)
9. [Column Detection Strategies](#9-column-detection-strategies)
10. [Testing Strategy](#10-testing-strategy)
11. [Justified Deviations from PRD 1.0](#11-justified-deviations-from-prd-10)
12. [File Map](#12-file-map)
13. [TODO: Implementation Tasks](#13-todo-implementation-tasks)

---

## 1. Pipeline Architecture

### Design Philosophy

Every stage is a **pure function** with:
1. **Typed input** → **Typed output** (no side effects)
2. **Confidence score** attached to output
3. **StageReport** logged before data moves forward
4. **Tests written FIRST** for each stage
5. **No data destruction** — flag, annotate, never delete ("exclude don't delete" principle)

### Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTRACTION PIPELINE                       │
│                                                             │
│  ┌──────────────────────────────────┐                       │
│  │ Stage 0: DOCUMENT ANALYSIS       │                       │
│  │ • Page count, file size          │                       │
│  │ • Has embedded text? (per page)  │                       │
│  │ • Corruption score (per page)    │                       │
│  │ • Output: DocumentProfile        │                       │
│  └───────────────┬──────────────────┘                       │
│                  ▼                                           │
│         ┌────────────────┐                                  │
│         │  Has embedded   │                                  │
│         │  text?          │                                  │
│         └───┬────────┬───┘                                  │
│         YES │        │ NO / SCANNED / CORRUPTED             │
│             ▼        ▼                                       │
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │ Stage 2A:    │  │ Stage 2B: OCR PATH                   │ │
│  │ NATIVE TEXT  │  │  2B-i:   Page Rendering              │ │
│  │ EXTRACTION   │  │  2B-ii:  Image Preprocessing         │ │
│  │              │  │  2B-iii: Text Recognition (Tesseract) │ │
│  └──────┬───────┘  └─────────────────┬────────────────────┘ │
│         │                            │                       │
│         ▼                            ▼                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Stage 3: STRUCTURE PRESERVATION (MERGE)               │   │
│  │ • Merge native + OCR into unified OcrElement list     │   │
│  │ • Normalize all coordinates to 0.0-1.0                │   │
│  │ • Validate coordinate alignment                       │   │
│  │ • Tag extraction method per page                      │   │
│  └───────────────┬──────────────────────────────────────┘   │
│                  ▼                                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Stage 4: TABLE EXTRACTION                             │   │
│  │  4A: Row Classification (data/header/total/boiler.)   │   │
│  │  4B: Table Region Detection (header→total boundaries) │   │
│  │  4C: Column Detection (header + clustering + gaps)    │   │
│  │  4D: Cell Extraction (+ optional cell re-OCR)         │   │
│  │  4E: Row Parsing (→ ParsedBidItem with confidence)    │   │
│  └───────────────┬──────────────────────────────────────┘   │
│                  ▼                                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Stage 5: POST-PROCESSING                              │   │
│  │ • Normalization • Splitting • Consistency              │   │
│  │ • Deduplication • Sequence validation                  │   │
│  │ • Every mutation tracked in RepairLog                  │   │
│  │ • Document total checksum computation                  │   │
│  └───────────────┬──────────────────────────────────────┘   │
│                  ▼                                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Stage 6: QUALITY VALIDATION                           │   │
│  │ • Flat 6-component weighted score                     │   │
│  │ • Completeness, coherence, math, checksum,            │   │
│  │   confidence distribution, structural                 │   │
│  └───────────────┬──────────────────────────────────────┘   │
│                  ▼                                           │
│         ┌────────────────┐                                  │
│         │  Quality OK?   │                                  │
│         └───┬────────┬───┘                                  │
│          YES│        │ NO                                   │
│             ▼        ▼                                       │
│     ┌────────────┐  ┌────────────────────────────────────┐  │
│     │ OUTPUT:    │  │ RE-EXTRACTION (max 3 attempts)      │  │
│     │ Pipeline   │  │ Attempt 1: Force full OCR            │  │
│     │ Result     │  │ Attempt 2: Higher DPI (400) + OCR    │  │
│     └────────────┘  │ After 3: Return best attempt         │  │
│                     │ Loop back to Stage 2B                │  │
│                     └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### OCR Decision Points

| Decision Point | Trigger | OCR Action |
|---|---|---|
| Stage 0 → 2 | `charsPerPage < 50` OR `singleCharRatio > 0.30` | Route entire document to OCR path (2B) |
| Stage 2A → 2B | Per-page corruption score > 15 | Route individual corrupt pages to OCR |
| Stage 4D | Merged cell blocks detected | Cell-level re-OCR on specific cells only |
| Stage 6 → Re-extract | Quality score < 0.65 | Force full OCR at higher DPI |

### Hybrid Path (Native + OCR Merge)

```
Page 1: Native text OK (corruption=2)    → Native elements, conf=1.0
Page 2: Native text OK (corruption=5)    → Native elements, conf=1.0
Page 3: Corrupted (corruption=18)        → OCR elements, conf=0.85
Page 4: Native text OK (corruption=3)    → Native elements, conf=1.0
Page 5: Scanned (chars=12)              → OCR elements, conf=0.78

Stage 3 merges: [native, native, OCR, native, OCR]
Each page tagged with its extraction method
```

### "Exclude Don't Delete" Principle

Every "excluded" row/element goes to a `Sidecar` collection:
- Sidecar items have: `originalData`, `excludedAtStage`, `reason`, `confidence`
- User can review sidecar items in import preview
- Post-process tracks every mutation as a `RepairEntry`
- Deduplication moves lower-confidence duplicates to sidecar (not deleted)
- Total rows go to `skippedRows` with reason `"total_row"`

---

## 2. Stage-by-Stage Specification

### Stage Name Constants

All stages use centralized snake_case constants:

```dart
abstract class StageNames {
  static const documentAnalysis = 'document_analysis';
  static const nativeExtraction = 'native_extraction';
  static const pageRendering = 'page_rendering';
  static const imagePreprocessing = 'image_preprocessing';
  static const textRecognition = 'text_recognition';
  static const structurePreservation = 'structure_preservation';
  static const rowClassification = 'row_classification';
  static const rowRefinement = 'row_refinement';
  static const regionDetection = 'region_detection';
  static const columnDetection = 'column_detection';
  static const cellExtraction = 'cell_extraction';
  static const rowParsing = 'row_parsing';
  static const postProcessing = 'post_processing';
  static const qualityValidation = 'quality_validation';
}
```

### Stage 0: Document Analysis
**File**: `extraction/stages/document_analyzer.dart`

```
INPUT:  PdfDocument + raw bytes
OUTPUT: DocumentProfile {
  pageCount, fileSize,
  pages[]{hasEmbeddedText, charCount, singleCharRatio, corruptionScore, needsOcr},
  recommendedStrategy, documentHash (SHA-256)
}
```

- **Algorithm**: Extract raw text per page, classify each as native/ocr needed
- **Thresholds**: charsPerPage < 50, singleCharRatio > 0.30, corruptionScore > 15
- **Confidence**: 1.0 (deterministic analysis)
- **Document Hash**: SHA-256 content hash (NOT `hashCode` — must be content-based for dedup/caching)

### Stage 2A: Native Text Extraction
**File**: `extraction/stages/native_extractor.dart`

```
INPUT:  PdfDocument + PageProfile[] (native pages only)
OUTPUT: NativeExtractionResult {elementsPerPage, confidencePerPage (always 1.0), methodPerPage}
```

- **Algorithm**: Syncfusion TextWord → OcrElement with normalized coordinates
- **Confidence**: Always 1.0 for native text

### Stage 2B-i: Page Rendering
**File**: `extraction/stages/page_renderer_v2.dart`

```
INPUT:  PdfDocument + PageProfile[] (OCR pages only)
OUTPUT: RenderedPages {rawImages, imageSizes, dpi}
```

- **Algorithm**: Adaptive DPI (≤10 pages → 300, 11-25 → 250, >25 → 200)
- **Re-extraction override**: Attempt 2 uses 400 DPI (deviation from PRD 1.0's 300 — see Section 11)

### Stage 2B-ii: Image Preprocessing
**File**: `extraction/stages/image_preprocessor_v2.dart`

```
INPUT:  RenderedPages
OUTPUT: PreprocessedPages {enhancedImages, statsBeforePreprocess, statsAfterPreprocess}
```

**Algorithm** (3 steps — deviation from PRD 1.0's 6 steps, see Section 11):
1. Grayscale conversion
2. Contrast enhancement
3. 8-bit conversion

### Stage 2B-iii: Text Recognition (OCR)
**File**: `extraction/stages/text_recognizer_v2.dart`

```
INPUT:  PreprocessedPages
OUTPUT: OcrExtractionResult {elementsPerPage, confidencePerPage (median), methodPerPage}
```

- **Algorithm**: Tesseract via TesseractEngineV2, word-level confidence, normalized coordinates
- **Confidence**: Median of word confidences per page (not mean — less sensitive to outliers)

### Stage 3: Structure Preservation (Merge)
**File**: `extraction/stages/structure_preserver.dart`

```
INPUT:  NativeExtractionResult + OcrExtractionResult + DocumentProfile
OUTPUT: UnifiedExtractionResult {
  elementsPerPage (ALL pages), confidencePerPage, methodPerPage, pageImages
}
```

- **Algorithm**: Merge native + OCR, normalize coordinates to 0.0-1.0, validate alignment
- **Validation**: All elements pass `isNormalized()`, dual-extract comparison on hybrid docs

### Stage 4A: Row Classification
**File**: `extraction/stages/row_classifier_v2.dart`

```
INPUT:  UnifiedExtractionResult
OUTPUT: ClassifiedRows {
  rows[], stats{header, data, continuation, boilerplate, sectionHeader, total, unknown, classificationRate}
}
```

- **Algorithm**: Two-phase (1A pre-column, 1B post-column). Adaptive Y-threshold grouping
- **Row types**: `header`, `data`, `continuation`, `boilerplate`, `sectionHeader`, `total`, `unknown`
- **Total row detection**: Keyword regex + structural signals + position (see Section 6.2)
- **ALL rows preserved** — UNKNOWN is a valid classification, nothing is dropped

### Stage 4B: Table Region Detection
**File**: `extraction/stages/region_detector_v2.dart`

```
INPUT:  ClassifiedRows
OUTPUT: DetectedRegions {regions[], excludedRows[] (with reasons, NOT deleted)}
```

- **Algorithm**: Header scan, cross-page validation, multi-row header assembly
- **Total rows**: Serve as strong end-of-table signal
- **Excluded rows preserved** in sidecar with reason

### Stage 4C: Column Detection
**File**: `extraction/stages/column_detector_v2.dart`

```
INPUT:  DetectedRegions + UnifiedExtractionResult
OUTPUT: ColumnMap {columns[], method, confidence, perPageAdjustments}
```

**Layered strategy** (see Section 9 for full detail):
- **Layer 1**: Header keyword detection (primary)
- **Layer 2**: Text alignment clustering (NEW — replaces TODO stub)
- **Layer 2b**: Whitespace gap analysis (NEW — fallback)
- **Layer 3**: Anchor-based correction (existing)
- **Cross-validation**: Multiple agreeing strategies boost confidence by 0.1-0.2

### Stage 4D: Cell Extraction
**File**: `extraction/stages/cell_extractor_v2.dart`

```
INPUT:  ColumnMap + UnifiedExtractionResult + DetectedRegions
OUTPUT: CellGrid {rows[], orphans[] (NOT deleted, with reasons), reOcrAttempts, reOcrSuccesses}
```

- **Algorithm**: X-position assignment, Y-clustering, merged block detection, optional cell re-OCR
- **Orphaned elements preserved** with distance-to-nearest-column metadata

### Stage 4E: Row Parsing
**File**: `extraction/stages/row_parser_v2.dart`

```
INPUT:  CellGrid + ClassifiedRows
OUTPUT: ParsedItems {
  items[], skippedRows[] (NOT deleted, with reasons), mergeLog[],
  extractedDocumentTotal, totalRowDescription
}
```

- **Algorithm**: Classification-aware parsing, continuation merging
- **Total rows**: NOT parsed as bid items. Dollar value extracted and stored as `extractedDocumentTotal`. Row added to `skippedRows` with reason `"total_row"`
- **Confidence per item**: Weighted geometric mean (see Section 3)

### Stage 5: Post-Processing
**File**: `extraction/stages/post_processor_v2.dart`

```
INPUT:  ParsedItems + PipelineContext
OUTPUT: ProcessedItems {items[], repairLog[], inferenceLog[], repairStats, checksum}
```

**Phases**: Normalize → Split → Consistency → Deduplicate → Sequence validate → Checksum compute
- Every mutation tracked as `RepairEntry` with before/after snapshots
- Deduplication: lower-confidence duplicates go to sidecar (not deleted)
- Checksum: computes sum of all bidAmount values, constructs `DocumentChecksum`
- Uses canonical `ConfidenceConstants` from `confidence_model.dart` (single source of truth)

### Stage 6: Quality Validation
**File**: `extraction/stages/quality_validator.dart`

```
INPUT:  ProcessedItems + all StageReports + PipelineConfig + attemptNumber
OUTPUT: QualityReport {overallScore, status, perItemScores, issues, suggestions, reExtractionStrategy?}
```

- **Formula**: Flat 6-component weighted sum (see Section 4)
- **Thresholds**: AUTO_ACCEPT >= 0.85, REVIEW_FLAGGED >= 0.65, RE_EXTRACT >= 0.45, PARTIAL_RESULT < 0.45

---

## 3. Confidence Scoring Model

### Three-Layer Architecture

**Layer 1: Raw OCR Confidence** (from engine)
**Layer 2: Validation Confidence** (from business rules)
**Layer 3: Composite Confidence** (weighted combination)

### Field Level — 4-Factor Weighted Formula

```dart
fieldConfidence = (
  0.40 * ocrConfidence      +  // Raw OCR word averages (1.0 for native)
  0.30 * formatValidation    +  // Pattern match (regex, type check)
  0.20 * consistencyScore    +  // Cross-field agreement (qty * price = amount)
  0.10 * contextScore           // Expected range, sequence position
)
```

**Format validation scores**:

| Field | Validation Rule | Score |
|---|---|---|
| itemNumber | Matches `^\d+(\.\d+)?$` | 1.0 match, 0.0 fail |
| unit | In UnitRegistry (EA, FT, CY, LS...) | 1.0 known, 0.3 unknown |
| quantity | Parses to positive number | 1.0 valid, 0.0 fail |
| unitPrice | Parses to positive number, has currency indicators | 1.0 valid, 0.0 fail |
| bidAmount | Parses to positive number, has currency indicators | 1.0 valid, 0.0 fail |
| description | Non-empty, >3 chars, not all digits | 1.0 valid, 0.5 short, 0.0 empty |

**Consistency scores**:

| Check | Score |
|---|---|
| qty x price = amount (within tolerance) | 1.0 |
| qty x price != amount but close (<5%) | 0.7 |
| qty x price != amount (>5% off) | 0.3 |
| Can't verify (missing fields) | 0.5 (neutral) |

**Context scores**:

| Check | Score |
|---|---|
| Item number in expected sequence | 1.0 |
| Item number out of sequence but valid format | 0.6 |
| Quantity in reasonable range for unit type | 1.0 |
| Quantity seems extreme (>1M for non-LS) | 0.5 |

### Row Level — Weighted Geometric Mean

```dart
rowConfidence = geometricMean([
  fieldConfidence_itemNumber * 1.5,   // weighted higher (critical field)
  fieldConfidence_description,
  fieldConfidence_unit,
  fieldConfidence_quantity * 1.5,      // weighted higher (financial impact)
  fieldConfidence_unitPrice,
  fieldConfidence_bidAmount,
]) * completenessMultiplier
```

**Why geometric mean**: A single bad field (e.g., quantity at 0.10) should tank the row score. Arithmetic mean of [0.95, 0.90, 0.85, 0.10, 0.90, 0.95] = 0.775 (looks fine). Geometric mean = 0.620 (flags for review). Construction bids have multiplicative field relationships — a wrong quantity invalidates the entire line item.

**Completeness multiplier**:
```
6/6 fields present = 1.0
5/6 fields present = 0.95
4/6 fields present = 0.85
3/6 fields present = 0.70
<3 fields present  = 0.50
```

**Zero-confidence handling**: Clamp minimum field confidence to 0.01 to prevent zero-product. Use log-space computation for numerical stability:
```dart
final logProduct = weights.entries.map((e) =>
  e.value * log(fields[e.key]!.clamp(0.01, 1.0))
).reduce((a, b) => a + b);
return exp(logProduct / totalWeight);
```

### Post-Processing Confidence Adjustments

All adjustments use canonical constants from `confidence_model.dart`:

| Repair Type | Adjustment | Rationale |
|---|---|---|
| Whitespace/artifact cleanup | No change | Deterministic, high certainty |
| Unit alias normalization | No change | Known mapping |
| Unit inferred from description | -0.05 field | Heuristic |
| Quantity inferred (amount / price) | -0.05 field | Calculated, reversible |
| Price inferred (amount / qty) | -0.05 field | Calculated, reversible |
| Math validates after inference | +0.05 row bonus | Confirms inference correct |
| Item number sequence correction | -0.10 field | Overriding extracted value |
| Multi-item row split | x0.90 all fields | Structural reinterpretation |
| Column shift repair | x0.85 all fields | Major reinterpretation |

**Single source of truth**: `lib/features/pdf/services/extraction/pipeline/confidence_model.dart`
No duplicate definitions permitted. All stages import from this file.

---

## 4. Quality Gate & Re-Extraction Loop

### Quality Score Formula — Flat 6-Component

```dart
overallScore = (
  0.20 * completeness           +  // Items found vs expected
  0.15 * coherence              +  // Garbled text / artifact detection
  0.25 * math_validation        +  // qty * price = amount verification
  0.15 * checksum_validation    +  // Document total match
  0.10 * confidence_distribution +  // Median item confidence
  0.15 * structural                // Column/region detection quality
)
```

**Weight rationale**:
- **math_validation (0.25)**: Strongest quality signal — if arithmetic checks out, data is likely correct
- **completeness (0.20)**: Partially overlaps with checksum (matching total implies all items present)
- **coherence (0.15)**: Catches garbled OCR, encoding corruption
- **checksum_validation (0.15)**: Aggregate validation — matching document total is strong positive signal
- **structural (0.15)**: Column/region detection confidence from Stages 4B/4C
- **confidence_distribution (0.10)**: Raw OCR confidence distribution across items

**Structural score**: Uses REAL Stage 4B (region_detection) and 4C (column_detection) confidences from StageReports. Requires standardized stage name constants for lookup.

### Quality Thresholds

| Score | Status | Action |
|---|---|---|
| **>= 0.85** | `AUTO_ACCEPT` | Straight-through to import preview |
| **0.65 - 0.84** | `REVIEW_FLAGGED` | Show in preview with low-confidence items highlighted |
| **0.45 - 0.64** | `RE_EXTRACT` | Trigger re-extraction (if attempts remaining) |
| **< 0.45** | `PARTIAL_RESULT` | Return what we have + flag for manual review |

### Re-Extraction Loop

```dart
for (int attempt = 0; attempt < 3; attempt++) {
  final config = _adjustConfigForAttempt(baseConfig, attempt);
  final result = await _runFullPipeline(config, attempt);
  bestAttempt = _selectBest(bestAttempt, result); // highest overallScore

  if (result.status == autoAccept || result.status == reviewFlagged) {
    return bestAttempt; // Success — exit early
  }
  if (result.status == partialResult) {
    return bestAttempt; // Can't improve — exit
  }
  // status == reExtract → continue loop with adjusted config
}
return bestAttempt; // Max attempts reached
```

| Attempt | Config Adjustment | What Changes |
|---|---|---|
| 0 | Original config | Normal extraction |
| 1 | `forceFullOcr: true` | All pages through OCR, ignore native text |
| 2 | `forceFullOcr: true, ocrDpi: 400` | Higher resolution OCR |

**Best attempt selection**: Compares `qualityReport.overallScore`, returns higher.

---

## 5. Coordinate Normalization

### System: Fractional Page Coordinates (0.0 - 1.0)

```
x_normalized = x / page_width
y_normalized = y / page_height
```

Both x and y range from 0.0 (top-left) to 1.0 (bottom-right). Resolution-independent, DPI-agnostic.

### OcrElement Structure

```dart
class OcrElement {
  final String text;
  final Rect boundingBox;              // Always in normalized coords (0.0-1.0)
  final double confidence;
  final int pageIndex;
  final CoordinateMetadata coordinates;
}

class CoordinateMetadata {
  final CoordinateSystem system;       // normalized | pixelDpi | pdfPoints
  final int? sourceDpi;
  final Size pageSize;                 // original page size in PDF points
  final Size? renderSize;              // rendered image size in pixels
  final ExtractionMethod source;       // native | ocr
}
```

### Conversion Functions

**File**: `extraction/pipeline/coordinate_normalizer.dart`

- `fromNativeText()` — PDF points → normalized
- `fromOcrPixels()` — Tesseract pixels → normalized
- `toPixels()` — Normalized → pixels (for re-OCR crops)
- `fromCropRelative()` — Re-OCR crop-relative → page-normalized
- `isNormalized()` — Validates all values in 0.0-1.0

### Downstream Impact

Column boundaries and thresholds are normalized:

| Pixel-dependent | Normalized |
|---|---|
| `kColumnOverlapTolerance = 5.0 px` | `~0.006` (0.6% page width) |
| `kHeaderYTolerance = 40.0 px` | `~0.016` (1.6% page height) |

Works for letter, legal, A4, and tabloid page sizes.

---

## 6. Document Total Checksum Validation

### 6.1 Purpose

Most construction bid schedule PDFs print a grand total. If the sum of all extracted bid amounts equals the printed total, it is very strong evidence that no items were lost, duplicated, or corrupted.

### 6.2 Total Row Detection (Stage 4A)

**Keyword patterns** (case-insensitive):
```
Primary: (?i)\b(total\s+of\s+all|grand\s+total|base\s+bid\s+total|total\s+base\s+bid|bid\s+total|total\s+bid|total\s+bid\s+amount|subtotal)\b
Secondary: (?i)^total\s*[:$]
```

**Structural signals**: Fewer populated columns than data rows, no item number, text spans multiple columns, position after last data row.

**Classification confidence**:
- Keyword + no item number + position after last data row: 0.95+
- Keyword alone: 0.80
- Structural signals only: 0.70

### 6.3 DocumentChecksum Model

```dart
class DocumentChecksum {
  final double? extractedDocumentTotal;   // From PDF's total row
  final double computedTotal;             // Sum of all extracted bidAmounts
  final double? discrepancy;              // |extracted - computed|
  final double? discrepancyPercent;
  final ChecksumStatus status;            // matched, minorDiscrepancy, majorDiscrepancy, noTotalFound
  final String? source;                   // Source text of total row
  final double tolerance;                 // Default: $0.02 (configurable)
  final int? sourcePageIndex;             // Page where total row found
  final double? detectionConfidence;      // Classification confidence of total row

  factory DocumentChecksum.withTotal({...});
  factory DocumentChecksum.noTotalFound({required double computedTotal});
}
```

### 6.4 Checksum Scoring in Quality Gate

| Condition | Score | Notes |
|---|---|---|
| Total extracted AND matches (within tolerance) | 1.0 | +0.05 bonus to overall score |
| Total extracted, minor discrepancy (<1%) | 0.90 | |
| Total extracted, major discrepancy (>=1%) | 0.50 | Issue flagged |
| Total NOT extracted (no total row found) | 0.75 | Neutral — many PDFs omit totals |
| Total row found but value unparseable | 0.75 | Same as not found |

### 6.5 Edge Cases

1. **Multiple subtotals + grand total**: Use last total row (grand total) for checksum. Subtotals go to sidecar.
2. **No total row**: Neutral score (0.75), no penalty, warning logged.
3. **OCR error in total**: Treated as not found, raw text preserved in sidecar.
4. **Total mid-document**: Classified as subtotal, not used for checksum.
5. **Rounding tolerance**: Default $0.02, accounts for penny rounding across 100+ items.

---

## 7. Data Models

### Core Types

| Model | File | Purpose |
|---|---|---|
| `DocumentProfile` | `models/document_profile.dart` | Stage 0 output: per-page analysis |
| `OcrElement` | `models/ocr_element.dart` | Text element with normalized coords |
| `ClassifiedRows` | `models/classified_rows.dart` | Stage 4A output: rows with type tags |
| `DetectedRegions` | `models/detected_regions.dart` | Stage 4B output: table boundaries |
| `ColumnMap` | `models/column_map.dart` | Stage 4C output: column definitions |
| `CellGrid` | `models/cell_grid.dart` | Stage 4D output: cells in grid |
| `ParsedItems` | `models/parsed_items.dart` | Stage 4E output: bid items + metadata |
| `ProcessedItems` | `models/processed_items.dart` | Stage 5 output: repaired items + checksum |
| `QualityReport` | `models/quality_report.dart` | Stage 6 output: scores + status |
| `DocumentChecksum` | `models/document_checksum.dart` | Aggregate validation |
| `Sidecar` | `models/sidecar.dart` | Excluded items preservation |
| `StageReport` | `models/stage_report.dart` | Per-stage metrics + confidence |
| `PipelineConfig` | `models/pipeline_config.dart` | All extraction settings |

### Confidence Types

| Model | File | Purpose |
|---|---|---|
| `ConfidenceScore` | `models/confidence.dart` | Single value with source + penalties/bonuses |
| `FieldConfidence` | `models/confidence.dart` | Per-field confidences (6 fields) with composite |
| `ConfidenceConstants` | `pipeline/confidence_model.dart` | Canonical penalty/bonus values |

### Pipeline Types

| Model | File | Purpose |
|---|---|---|
| `PipelineResult` | `pipeline/extraction_pipeline.dart` | Final output wrapper |
| `PipelineContext` | `pipeline/pipeline_context.dart` | Cross-stage shared state |
| `ExtractionMetrics` | `pipeline/extraction_metrics.dart` | SQLite persistence |
| `ResultConverter` | `pipeline/result_converter.dart` | V2 → legacy domain bridge |
| `CoordinateNormalizer` | `pipeline/coordinate_normalizer.dart` | Coordinate conversions |

### StageReport Contract

Every stage produces a `StageReport` with this invariant:
```dart
assert(outputCount + excludedCount == inputCount, 'Data loss detected');
```

This enforces the "exclude don't delete" rule at the type level.

---

## 8. Diagnostic Feedback Loop

### ExtractionMetrics (SQLite)

```sql
CREATE TABLE extraction_metrics (
  id TEXT PRIMARY KEY,
  document_hash TEXT NOT NULL,       -- SHA-256 content hash
  timestamp TEXT NOT NULL,
  page_count INTEGER NOT NULL,
  strategy TEXT NOT NULL,
  total_elapsed_ms INTEGER NOT NULL,
  extraction_confidence REAL NOT NULL,
  quality_status TEXT NOT NULL,
  items_extracted INTEGER NOT NULL,
  items_expected INTEGER,
  re_extraction_attempts INTEGER DEFAULT 0,
  avg_item_confidence REAL NOT NULL,
  items_above_85 INTEGER NOT NULL,
  items_between_65_85 INTEGER NOT NULL,
  items_below_65 INTEGER NOT NULL,
  native_pages INTEGER NOT NULL,
  ocr_pages INTEGER NOT NULL,
  cell_reocr_count INTEGER DEFAULT 0,
  repairs_applied INTEGER DEFAULT 0,
  inferences_applied INTEGER DEFAULT 0,
  split_count INTEGER DEFAULT 0,
  dedup_count INTEGER DEFAULT 0
);

CREATE TABLE stage_metrics (
  id TEXT PRIMARY KEY,
  extraction_id TEXT NOT NULL REFERENCES extraction_metrics(id),
  stage_name TEXT NOT NULL,
  elapsed_ms INTEGER NOT NULL,
  confidence REAL NOT NULL,
  input_count INTEGER NOT NULL,
  output_count INTEGER NOT NULL,
  excluded_count INTEGER NOT NULL,
  warning_count INTEGER NOT NULL
);
```

### Queryable Insights

- % of PDFs needing OCR over time
- Which stage is the performance bottleneck
- Re-extraction frequency and effectiveness
- Confidence trend analysis
- Repeat-failure document identification (via content hash)

---

## 9. Column Detection Strategies

### Layer 1: Header Keyword Detection (Existing)

Searches for known column header patterns: ITEM, DESCRIPTION, UNIT, QTY/QUANTITY, PRICE/UNIT PRICE, AMOUNT/BID AMOUNT.

**Confidence**: `matchCount / 6` (0.5-1.0 based on headers found)

### Layer 2: Text Alignment Clustering (NEW)

Detects columns by clustering text elements' X-coordinates using 1D agglomerative clustering:

1. Collect all data row element left-edge X positions (normalized 0.0-1.0)
2. Sort and cluster using tolerance ~0.015 (1.5% page width)
3. Cluster centroids = column left edges
4. Estimate right edges from gap analysis between clusters
5. Cross-validate with header keywords for confidence boost

**Confidence**: 0.75 base, 0.85+ when header keywords agree
**Advantages**: Works on both native and OCR paths, no image processing required

### Layer 2b: Whitespace Gap Analysis (NEW — Fallback)

Detects columns by finding consistent vertical gaps in text:

1. Create X-axis histogram of text coverage (200 bins)
2. Identify zero-coverage gaps wider than 1% page width
3. Qualify gaps: consistent across >50% of data rows
4. Column boundaries = gap midpoints

**Confidence**: 0.60 (weak signal, only used when clustering fails)

### Layer 3: Anchor-Based Correction (Existing)

Uses known text patterns and positions to correct column boundaries.

### Cross-Validation

When multiple strategies agree, confidence is boosted by 0.1-0.2. The highest-confidence result is used.

---

## 10. Testing Strategy

### Three Tiers

| Tier | What | Purpose |
|---|---|---|
| **Unit** | Single stage, mocked inputs | Algorithm correctness |
| **Contract** | Stage input → output shape | Data flow between stages |
| **Integration** | Multi-stage with real fixtures | Pipeline end-to-end |

### Contract Tests (9 total)

All enforce the no-data-loss invariant: `outputCount + excludedCount == inputCount`

| Test | Boundary |
|---|---|
| `stage_0_to_2_contract_test.dart` | Document analysis → Text extraction |
| `stage_2_to_3_contract_test.dart` | Text extraction → Structure preservation |
| `stage_3_to_4a_contract_test.dart` | Structure → Row classification |
| `stage_4a_to_4b_contract_test.dart` | Rows → Region detection |
| `stage_4b_to_4c_contract_test.dart` | Regions → Column detection |
| `stage_4c_to_4d_contract_test.dart` | Columns → Cell extraction |
| `stage_4d_to_4e_contract_test.dart` | Cells → Row parsing |
| `stage_4e_to_5_contract_test.dart` | Parsing → Post-processing |
| `stage_5_to_6_contract_test.dart` | Post-processing → Quality validation |

### Per-Stage Golden Files (Springfield PDF)

All 9 fixtures must be generated by running pipeline against Springfield PDF and validated against ground truth (131 items, total $7,882,926.73):

| Stage | Golden File | Status |
|---|---|---|
| Stage 0 | `springfield_document_profile.json` | MISSING |
| Stage 3 | `springfield_unified_elements.json` | MISSING |
| Stage 4A | `springfield_classified_rows.json` | MISSING |
| Stage 4B | `springfield_detected_regions.json` | MISSING |
| Stage 4C | `springfield_column_map.json` | MISSING |
| Stage 4D | `springfield_cell_grid.json` | MISSING |
| Stage 4E | `springfield_parsed_items.json` | MISSING |
| Stage 5 | `springfield_processed_items.json` | EXISTS — needs validation |
| Stage 6 | `springfield_quality_report.json` | EXISTS — needs validation |

### Golden File Matcher

`test/features/pdf/extraction/golden/golden_file_matcher.dart` — fuzzy matching utility:
- String match: 90% Levenshtein similarity
- Numeric tolerance: $0.01 for currency, 0.001 for quantities
- Match rate requirement: >= 95%

### Test Infrastructure

| Component | Location | Files |
|---|---|---|
| Test helpers | `test/features/pdf/extraction/helpers/test_fixtures.dart` | 1 |
| Contract tests | `test/features/pdf/extraction/contracts/` | 9 |
| Golden tests | `test/features/pdf/extraction/golden/` | 4 |
| Model tests | `test/features/pdf/extraction/models/` | 14 |
| Stage tests | `test/features/pdf/extraction/stages/` | 16 |
| Pipeline tests | `test/features/pdf/extraction/pipeline/` | 5 |
| OCR tests | `test/features/pdf/extraction/ocr/` | 4 |
| Integration tests | `test/features/pdf/extraction/integration/` | 2 |
| **Total** | | **55+ test files** |

---

## 11. Justified Deviations from PRD 1.0

These deviations are intentional improvements. They MUST be documented in code comments.

### 11.1 Image Preprocessing: 3 Steps Instead of 6

**PRD 1.0**: 6 steps (grayscale, deskew, noise removal, CLAHE, binarization, border removal)
**Actual**: 3 steps (grayscale, contrast, 8-bit conversion)

**Rationale**: Binarization destroyed 92% of image data on clean PDFs (known defect discovered during implementation). Deskewing is optional for scanned docs only — most construction bid schedules are digitally created. The 3-step pipeline produces better OCR results on real-world PDFs.

### 11.2 Re-Extraction DPI: 400 Instead of 300

**PRD 1.0**: "300 DPI + PSM mode 6"
**Actual**: 400 DPI + PSM mode 6

**Rationale**: Higher DPI provides more detail for text recognition, especially for small text in bid schedules. Marginal memory increase is acceptable for improved accuracy.

### 11.3 Checksum Scoring: Granular Instead of Binary

**PRD 1.0**: matched=1.0 (+0.05 bonus), not matched=0.3, not extracted=0.7
**Actual**: matched=1.0, minorDiscrepancy(<1%)=0.90, majorDiscrepancy(>=1%)=0.50, noTotalFound=0.75

**Rationale**: Real-world PDFs often have minor rounding differences. A $0.50 discrepancy on a $7.8M total should score differently than a $500K discrepancy. Granularity provides more useful quality signals.

### 11.4 Feature Flag Skipped (V1 Deleted Directly)

**PRD 1.0**: "Preserve V1 behind `useNewPipeline` flag"
**Actual**: V1 deleted entirely in Phase 6 cutover

**Rationale**: V2 was fully functional and tested before cutover. No rollback path exists, which is acceptable given the comprehensive test suite. Eliminated ~42,000 lines of dead code.

---

## 12. File Map

### Source Files

```
lib/features/pdf/services/extraction/
├── models/
│   ├── cell_grid.dart
│   ├── classified_rows.dart
│   ├── column_map.dart
│   ├── confidence.dart              # ConfidenceScore, FieldConfidence
│   ├── detected_regions.dart
│   ├── document_checksum.dart
│   ├── document_profile.dart
│   ├── extraction_result.dart
│   ├── models.dart                  # Barrel export
│   ├── ocr_element.dart
│   ├── parsed_items.dart
│   ├── pipeline_config.dart
│   ├── processed_items.dart
│   ├── quality_report.dart
│   ├── sidecar.dart
│   └── stage_report.dart
├── stages/
│   ├── document_analyzer.dart       # Stage 0
│   ├── native_extractor.dart        # Stage 2A
│   ├── page_renderer_v2.dart        # Stage 2B-i
│   ├── image_preprocessor_v2.dart   # Stage 2B-ii
│   ├── text_recognizer_v2.dart      # Stage 2B-iii
│   ├── structure_preserver.dart     # Stage 3
│   ├── row_classifier_v2.dart       # Stage 4A
│   ├── region_detector_v2.dart      # Stage 4B
│   ├── column_detector_v2.dart      # Stage 4C
│   ├── cell_extractor_v2.dart       # Stage 4D
│   ├── row_parser_v2.dart           # Stage 4E
│   ├── post_processor_v2.dart       # Stage 5
│   ├── quality_validator.dart       # Stage 6
│   └── stages.dart                  # Barrel export
├── pipeline/
│   ├── confidence_model.dart        # Canonical ConfidenceConstants
│   ├── coordinate_normalizer.dart
│   ├── extraction_metrics.dart      # SQLite persistence
│   ├── extraction_pipeline.dart     # Orchestrator + re-extraction loop
│   ├── pipeline_context.dart
│   └── result_converter.dart        # V2 → legacy bridge
├── ocr/
│   ├── ocr_engine_v2.dart
│   ├── tesseract_engine_v2.dart
│   ├── tesseract_pool_v2.dart
│   └── concurrency_gate_v2.dart
└── shared/
    └── unit_registry.dart
```

### Test Files

```
test/features/pdf/extraction/
├── contracts/                       # 9 stage-to-stage contract tests
├── fixtures/                        # Golden JSON fixtures (9 total)
├── golden/                          # Golden file matcher + regression tests
├── helpers/                         # Test factory utilities
├── integration/                     # Full pipeline + round-trip tests
├── models/                          # 14 model unit tests
├── ocr/                             # 4 OCR infrastructure tests
├── pipeline/                        # 5 pipeline/metrics tests
└── stages/                          # 16 individual stage tests
```

---

## 13. TODO: Implementation Tasks

All items below require individual research and implementation planning before execution.

### Phase R1: Critical Correctness (Sessions 1-2)

#### R1.1 — Rewrite Quality Formula to Flat 6-Component
- **File**: `lib/features/pdf/services/extraction/stages/quality_validator.dart`
- **What**: Remove hierarchical `tableConfidence` intermediate. Implement flat weighted sum with weights: completeness=0.20, coherence=0.15, math=0.25, checksum=0.15, confidence_dist=0.10, structural=0.15
- **Include mathScore**: Currently computed (line 46) but excluded from formula — add with 0.25 weight
- **Tests**: Update `stage_6_quality_validation_test.dart` with new expected values. Add test vectors pinning scores for representative scenarios (all-good, one-bad-component, edge thresholds)

#### R1.2 — Delete Duplicate ConfidenceConstants
- **File**: `lib/features/pdf/services/extraction/stages/post_processor_v2.dart` (lines 1202-1210)
- **What**: Delete local `class ConfidenceConstants`. Import from `confidence_model.dart`. Verify 3 conflicting values resolve to canonical: `kAdjQuantityInferred=-0.05`, `kAdjPriceInferred=-0.05`, `kAdjItemNumberCorrected=-0.10`
- **Tests**: Update `stage_5_post_processing_test.dart` if any test asserts on the old values

#### R1.3 — Standardize Stage Name Constants
- **Files**: All 14 stage files in `stages/` + `quality_validator.dart`
- **What**: Create `StageNames` abstract class with snake_case constants. Update all stages to use `StageNames.xxx`. Fix QualityValidator lookups (lines 255/258) to match actual names
- **Critical fix**: After this, structural score will use real Stage 4B/4C confidences instead of fallback defaults
- **Tests**: Verify stage name matching in quality validation tests

#### R1.4 — Content-Based Document Hash (SHA-256)
- **File**: `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` (line 228)
- **What**: Replace `pdfBytes.hashCode.abs().toString()` with `sha256.convert(pdfBytes).toString()`. Add `crypto` package if needed
- **Tests**: Verify same PDF bytes produce identical hash across multiple calls

### Phase R2: Model Enhancements (Sessions 3-4)

#### R2.1 — DocumentChecksum: Add Missing Fields + Factories
- **File**: `lib/features/pdf/services/extraction/models/document_checksum.dart`
- **Add fields**: `tolerance` (double, default 0.02), `sourcePageIndex` (int?), `detectionConfidence` (double?)
- **Add factories**: `DocumentChecksum.withTotal(...)` and `DocumentChecksum.noTotalFound(...)`
- **Update**: `post_processor_v2.dart` checksum construction to use factories
- **Tests**: Create `document_checksum_test.dart` (see R5.2)

#### R2.2 — ParsedItems: Add totalRowDescription
- **File**: `lib/features/pdf/services/extraction/models/parsed_items.dart`
- **Add field**: `String? totalRowDescription` alongside `extractedDocumentTotal` (line 223)
- **Propagate**: Stage 4E row parser extracts description text from total row
- **Update**: `copyWith()`, constructor, serialization, tests

#### R2.3 — Weighted Geometric Mean for Row Confidence
- **Files**: `confidence.dart`, `row_parser_v2.dart`, `row_classifier_v2.dart`, `cell_extractor_v2.dart`
- **What**: Add `compositeGeometric` getter to `FieldConfidence` using log-space weighted geometric mean. Replace arithmetic mean in 3 locations. Clamp min at 0.01. Weight itemNumber and quantity 1.5x
- **Threshold adjustment**: Quality gate may need threshold lowered from 0.65 to ~0.60
- **Tests**: Extensive — verify geometric produces lower scores for single-bad-field scenarios. Update all affected test expectations

#### R2.4 — 4-Factor Field Confidence Formula
- **File**: `lib/features/pdf/services/extraction/stages/post_processor_v2.dart` (lines 957-1020)
- **What**: Replace binary presence checks with `0.40*ocrConf + 0.30*formatValidation + 0.20*consistencyScore + 0.10*contextScore` per field
- **Format validation**: Regex-based per PRD Section 3 table (itemNumber, unit, quantity, unitPrice, bidAmount, description)
- **Consistency**: Math check (qty * price = amount within tolerance)
- **Context**: Sequence position, value range reasonableness
- **Tests**: Update all field confidence tests with new expected values

### Phase R3: Column Detection Enhancement (Sessions 5-6)

#### R3.1 — Text Alignment Clustering (Layer 2)
- **File**: `lib/features/pdf/services/extraction/stages/column_detector_v2.dart` (replace TODO at line 473)
- **What**: Implement `_detectFromAlignment()` using 1D agglomerative clustering of element X-coordinates. Tolerance ~0.015 normalized. Cross-validate with headers
- **Confidence**: 0.75 base, 0.85+ with header agreement
- **Tests**: Add test cases for various column layouts, edge cases (ragged edges, indented text)

#### R3.2 — Whitespace Gap Analysis (Layer 2b Fallback)
- **File**: Same as R3.1
- **What**: Implement `_detectFromGaps()` using X-axis histogram. 200 bins, gaps >1% width, consistent >50% rows
- **Confidence**: 0.60 (weak fallback signal)
- **Tests**: Sparse table cases, false positive prevention

### Phase R4: Pipeline Wiring (Session 6)

#### R4.1 — ProgressCallback Wiring
- **Files**: `extraction_pipeline.dart`, `pdf_import_service.dart`
- **What**: Add `ProgressCallback? onProgress` to `extract()`. Invoke at each stage boundary with stage name + index/total. Pass from `importBidSchedule()` to `extract()`
- **Future note**: Add `// TODO: Expand progress detail per-stage (page count, items found)` for UX iteration
- **Tests**: Verify callback invoked correct number of times with correct stage names

### Phase R5: Test Infrastructure (Sessions 7-8)

#### R5.1 — Generate All 9 Springfield Golden Fixtures
- **Location**: `test/features/pdf/extraction/fixtures/`
- **What**: Run pipeline against Springfield PDF, serialize each stage output. Validate ALL 9 fixtures against ground truth (131 items, $7,882,926.73). Verify existing 2 fixtures are correct
- **Requires**: Access to Springfield PDF file, ability to run full pipeline
- **Output**: 7 new JSON files + 2 validated existing files

#### R5.2 — Add document_checksum_test.dart
- **File**: `test/features/pdf/extraction/models/document_checksum_test.dart`
- **Test cases**: Exact match, within tolerance ($0.02), at boundary, beyond tolerance, `noTotalFound()` factory, `withTotal()` factory, large values (Springfield total), new fields (tolerance, sourcePageIndex, detectionConfidence)

#### R5.3 — Add Extraction Schema Migration Test
- **File**: `test/core/database/extraction_schema_test.dart`
- **Test cases**: Create extraction_metrics table (21 columns), create stage_metrics table (8 columns), verify indexes, test v20→v21 upgrade path

### Phase R6: Cleanup (Session 9)

#### R6.1 — Delete Orphaned Golden PNGs
- **Delete**: `test/golden/pdf/goldens/` directory (12 PNG files from deleted test `pdf_import_widgets_test.dart`)

#### R6.2 — Remove enrichWithMeasurementSpecs Dead Code
- **File**: `lib/features/quantities/presentation/providers/bid_item_provider.dart`
- **Delete**: `enrichWithMeasurementSpecs()` method (lines 286-332). No UI path calls it after import type dialog removal

#### R6.3 — Fix Flutter Analyze Warnings
- **Scope**: 19 issues in `lib/features/pdf/services/extraction/`
- **Types**: Unnecessary imports, doc-comment formatting, null-check issues in `page_renderer_v2.dart`
- **Command**: `pwsh -Command "flutter analyze lib/features/pdf/services/extraction"`

#### R6.4 — Document Justified Deviations
- **Add code comments** in 3 files documenting why implementation differs from PRD 1.0:
  - `image_preprocessor_v2.dart`: 3 steps not 6 (binarization destroyed 92% of data)
  - `extraction_pipeline.dart`: 400 DPI not 300 (better results)
  - `quality_validator.dart`: Granular checksum scoring (improvement)

### Phase R7: Enhancements (Sessions 10-15)

#### R7.1 — TEDS/GriTS Structural Metrics (Enhancement #5)
- **File**: `test/features/pdf/extraction/golden/golden_file_matcher.dart`
- **What**: Add `StructuralMetrics` extension implementing TEDS (Tree Edit Distance Score) for table structure similarity and GriTS (Grid Table Similarity) for cell-level precision/recall
- **Research needed**: Study TEDS/GriTS papers, determine how to adapt for bid schedule tables (which are simpler than general HTML tables)
- **Tests**: Dedicated test file for structural metrics

#### R7.2 — Confidence Calibration Pipeline (Enhancement #6)
- **New file**: `lib/features/pdf/services/extraction/pipeline/confidence_calibrator.dart`
- **What**: Implement Platt scaling (logistic regression) or table-based calibration. Compare predicted confidence to actual correctness against Springfield ground truth. Apply monotonic correction curve
- **Research needed**: Platt scaling implementation in Dart, calibration corpus requirements, isotonic regression as alternative
- **Tests**: Calibration test with Springfield fixture, verify monotonicity

#### R7.3 — Stress/Performance Benchmark Suite (Enhancement #7)
- **New directory**: `test/features/pdf/extraction/benchmarks/`
- **Benchmarks**:
  - Extraction time per page (target: <2s native, <5s OCR)
  - Memory usage during extraction (target: <200MB for 25-page PDF)
  - Concurrent extraction limits
  - Large document handling (50+ pages)
- **Research needed**: Dart/Flutter benchmarking best practices, memory profiling tools, CI integration for performance regression detection

---

## Execution Summary

| Phase | Sessions | Scope |
|-------|----------|-------|
| R1: Critical Correctness | 1-2 | Quality formula, constants, stage names, hash |
| R2: Model Enhancements | 3-4 | Checksum model, geometric mean, 4-factor confidence |
| R3: Column Detection | 5-6 | Text clustering, whitespace gaps |
| R4: Pipeline Wiring | 6 | ProgressCallback |
| R5: Test Infrastructure | 7-8 | Golden fixtures, missing tests |
| R6: Cleanup | 9 | PNGs, dead code, warnings, docs |
| R7: Enhancements | 10-15 | TEDS/GriTS, calibration, benchmarks |
| **Total** | **~11-17** | |

---

## Verification Checklist

After each phase:
- [ ] `pwsh -Command "flutter test test/features/pdf/extraction/"` — all pass
- [ ] `pwsh -Command "flutter analyze lib/features/pdf/services/extraction"` — zero issues

After full completion:
- [ ] `pwsh -Command "flutter test"` — full suite passes
- [ ] Springfield: 131 items extracted, checksum matches $7,882,926.73
- [ ] Quality score for Springfield >= 0.85 (AUTO_ACCEPT)
- [ ] All 9 golden fixtures present and validated
- [ ] `flutter analyze` — zero warnings project-wide
- [ ] No duplicate ConfidenceConstants definitions
- [ ] All stage names use StageNames constants (snake_case)
- [ ] Document hash is SHA-256 content-based
- [ ] Geometric mean used for row confidence
- [ ] 4-factor field confidence formula active
- [ ] Text clustering + whitespace gap detection implemented
- [ ] ProgressCallback wired through pipeline
- [ ] TEDS/GriTS metrics in golden matcher
- [ ] Confidence calibration pipeline functional
- [ ] Stress benchmarks passing with budget assertions

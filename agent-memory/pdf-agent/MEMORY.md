# Agent Memory — PDF Agent

## Patterns Discovered

### PSM7 Fails on Right-Aligned Currency in Wide Cell (Item #100 "$110.00" -> "Si")
Root cause confirmed: Tesseract PSM7 (single line) fails when text is right-aligned in a wide crop with 60%+ blank whitespace on the left. The crop (354x92px) is correct and readable, but PSM7 word segmentation breaks "$110.00" into two nonsense fragments "Si" (conf=0.46) + "logo" (conf=0.31). Neighbors $83.25 and $26.55 in the same column read correctly with PSM7 (possibly because they have shorter text that positions differently, or because "1" in "$110" triggers a different LSTM path).

- Cell bounds: page 4, row 14 (H14=0.4319 to H15=0.4595), col 4 (V4=0.6581 to V5=0.7963)
- Crop: 354x92px (no upscaling, exceeds kMinCropWidth=300 and kMinCropHeight=40)
- PSM7 used (not row 0, not tall row)
- Text "$110.00" starts at ~60% from cell left (right-aligned, 213px of blank leading space)
- Fix direction: column-aware numeric whitelist "$0123456789,. -" for qty/price/amount columns prevents letter outputs

### Garbage OCR in Item-Number Column (Page 3 Springfield — Items 64, 74, 75, 77)
Root cause confirmed: TextRecognizerV2 produces per-individual-cell crops (one per grid row × column).
For grid row bands that contain NO item number (because the item number was on the previous row or the band is a price/desc continuation), the item-number column crop contains only horizontal grid line pixels. Tesseract reads those dark pixels as garbage text (`al`, `ot`, `re`, `or`).

- These garbage elements span the FULL column-0 width (left=0.054, right=0.106) matching the column boundary exactly.
- Their Y-ranges correspond to grid row bands 4, 14, 15, 17 on page 3.
- Their confidence is near-zero (0.0–0.35).
- Root fix direction: filter garbage elements whose text has no alphanumeric value AND confidence < threshold, OR whose bounding box matches the full cell width (≥ 90% of column width) with near-zero confidence.

### Font Encoding Corruption in Native Text Extraction
Some PDF pages have corrupted font encoding that produces character substitutions even though text order is correct:
- Digits → Letters: `7→z`, `3→e`, `9↔6`
- Punctuation → Quotes: `,→'`, `.→'`
- Example: `$7,882,926.73` becomes `$z'882'629'ze`

Current pipeline is all-or-nothing (document-level OCR decision). Need per-page quality gate.

Reference: @per-page-quality-gate-design.md

## Gotchas & Quirks

### INSTALL.vcxproj MSBuild Error on Integration Tests
When `flutter test integration_test/... -d windows` fails with `INSTALL.vcxproj` CMake install error:
- Root cause: stale `build/` directory with file handles locked by a previous run
- Fix: `Stop-Process construction_inspector/dart/flutter -Force`, then `Remove-Item -Recurse -Force build/`, then `flutter pub get`, then retry
- The build directory is at `C:\Users\rseba\Projects\Field Guide App\build\`

### Document-Level vs Per-Page Quality
The `needsOcr()` check aggregates stats across ALL pages:
- `charsPerPage = totalChars / pageCount`
- If threshold passes, ALL pages use native text

This breaks when page 6 is corrupted but pages 1-5, 7-12 are clean.

## Architectural Decisions

### Stage 0 DocumentQualityProfiler (✅ Implemented — replaces DocumentAnalyzer)
**Location**: `lib/features/pdf/services/extraction/stages/document_quality_profiler.dart`

Profiles each page's quality to determine extraction strategy. The original `document_analyzer.dart` has been moved to `deprecated/`.

**Key design**: OCR-only pipeline — all pages use OCR extraction. Quality profiling guides preprocessing decisions rather than extraction strategy selection.

### Stage 3 StructurePreserver (✅ Implemented — simplified for OCR-only)
**Location**: `lib/features/pdf/services/extraction/stages/structure_preserver.dart`

Simplified for OCR-only pipeline — no longer needs hybrid merge logic. All pages use OCR extraction with confidence from element confidences.

### Stage 4A RowClassifierV3 (✅ Implemented — replaced V2)
**Location**: `lib/features/pdf/services/extraction/stages/row_classifier_v3.dart`

Classifies rows from UnifiedExtractionResult into types (header, data, continuation, boilerplate, etc.).

**Two-phase design**:
- **Phase 1A (pre-column)**: Classifies using text content and geometry only
- **Phase 1B (post-column)**: Refines UNKNOWN rows using column boundaries → SECTION_HEADER or BOILERPLATE

**v3 improvements over v2**:
1. **Data-loss assertion**: Throws StateError if `inputCount ≠ outputCount` (row grouping must not drop elements)
2. **Edge-to-edge gap measurement**: `yGapToPrevious` measures whitespace between row edges, not center-to-center distance
3. **Unified data likelihood**: Single `dataLikelihood` score (0.0-1.0)

**Test coverage**: `test/features/pdf/extraction/stages/row_classifier_v3_test.dart`

### Stage 4B RegionDetectorV2 (✅ Implemented)
**Location**: `lib/features/pdf/services/extraction/stages/region_detector_v2.dart`

Detects table regions from classified rows using linear scan algorithm:
- **Cross-page header confirmation**: Headers near bottom (Y > 0.70) require DATA on next page
- **Multi-row header assembly**: Consecutive headers with complementary keywords (<50% character overlap)
- **Data row requirement**: Minimum 2 DATA rows after headers to confirm table
- **Termination conditions**: 3 consecutive BOILERPLATE or new HEADER

**Key constants (normalized 0.0-1.0)**:
- `kPageBottomThreshold = 0.70`
- `kMinDataRowsAfterHeader = 2`
- `kConsecutiveBoilerplateTermination = 3`
- `kMaxDataRowLookahead = 15`
- `kEndYEpsilon = 0.001`

**Data-accounting guarantee**: StateError thrown if `inputCount ≠ outputCount + excludedCount` (no data loss).

### Stage 4D CellExtractorV2 (✅ Implemented)
**Location**: `lib/features/pdf/services/extraction/stages/cell_extractor_v2.dart`

Assigns OCR elements to table cells based on column boundaries from Stage 4C using three-tier matching strategy:
1. **Exact/Tolerance Overlap** (primary): ±0.006 normalized tolerance
2. **Nearest Column Fallback** (secondary): distance < 0.10 threshold
3. **Orphan** (tertiary): distance > threshold, preserved with reason

**Data-accounting guarantee**: StateError thrown if `inputCount ≠ outputCount + excludedCount`.

### Stage 4E RowParserV3 (✅ Implemented — replaced V2)
**Location**: `lib/features/pdf/services/extraction/stages/row_parser_v3.dart`

Parses cell grid rows into structured bid items. Works with interpretation pipeline.

**Supporting stages (new in v3)**:
- `lib/features/pdf/services/extraction/stages/field_confidence_scorer.dart` — scores field-level confidence
- `lib/features/pdf/services/extraction/stages/header_consolidator.dart` — consolidates multi-line headers
- `lib/features/pdf/services/extraction/stages/numeric_interpreter.dart` — interprets numeric values with rules

**Models (new in v3)**:
- `lib/features/pdf/services/extraction/models/interpretation_rule.dart` — rules for value interpretation
- `lib/features/pdf/services/extraction/models/interpreted_value.dart` — result of interpretation
- `lib/features/pdf/services/extraction/rules/` — directory of interpretation rule configs

## Current Baseline (2026-02-21, post v3 pipeline)

- **Scorecard**: `68 OK / 3 LOW / 0 BUG`
- **Quality**: `0.993`
- **Parsed**: `131/131`
- **GT matched**: `131/131` (100%)
- **bid_amount**: `131/131`

## Frequently Referenced Files

### Extraction Pipeline (v3 Architecture)
- `lib/features/pdf/services/extraction/stages/document_quality_profiler.dart` - **Stage 0**: Per-page quality profiling
- `lib/features/pdf/services/extraction/stages/structure_preserver.dart` - **Stage 3**: OCR result structuring
- `lib/features/pdf/services/extraction/stages/row_classifier_v3.dart` - **Stage 4A**: Row classification (v3)
- `lib/features/pdf/services/extraction/stages/region_detector_v2.dart` - **Stage 4B**: Table region detection
- `lib/features/pdf/services/extraction/stages/cell_extractor_v2.dart` - **Stage 4D**: Cell extraction and column assignment
- `lib/features/pdf/services/extraction/stages/row_parser_v3.dart` - **Stage 4E**: Row parsing (v3)
- `lib/features/pdf/services/extraction/stages/field_confidence_scorer.dart` - Field confidence scoring
- `lib/features/pdf/services/extraction/stages/header_consolidator.dart` - Header consolidation
- `lib/features/pdf/services/extraction/stages/numeric_interpreter.dart` - Numeric value interpretation
- `lib/features/pdf/services/extraction/models/document_profile.dart` - PageProfile and DocumentProfile types
- `lib/features/pdf/services/extraction/models/extraction_result.dart` - UnifiedExtractionResult type
- `lib/features/pdf/services/extraction/models/classified_rows.dart` - ClassifiedRow, ClassificationStats types
- `lib/features/pdf/services/extraction/models/detected_regions.dart` - TableRegion, ExcludedRow, DetectedRegions types
- `lib/features/pdf/services/extraction/models/column_map.dart` - ColumnDef, ColumnMap types
- `lib/features/pdf/services/extraction/models/cell_grid.dart` - Cell, OrphanElement, CellGrid types
- `lib/features/pdf/services/extraction/models/stage_report.dart` - StageReport with no-data-loss validation
- `lib/features/pdf/services/extraction/models/interpretation_rule.dart` - Interpretation rules (v3)
- `lib/features/pdf/services/extraction/models/interpreted_value.dart` - Interpreted value type (v3)
- `lib/features/pdf/services/extraction/rules/` - Interpretation rule configs (v3)

### Tests
- `test/features/pdf/extraction/stages/stage_0_document_analyzer_test.dart` - Unit tests (34)
- `test/features/pdf/extraction/stages/document_analyzer_integration_test.dart` - Integration tests (3)
- `test/features/pdf/extraction/stages/stage_3_structure_preserver_test.dart` - Unit tests (19)
- `test/features/pdf/extraction/stages/row_classifier_v3_test.dart` - Unit tests (v3)
- `test/features/pdf/extraction/stages/stage_4b_region_detector_test.dart` - Unit tests (18)
- `test/features/pdf/extraction/stages/stage_4d_cell_extractor_test.dart` - Unit tests (15)
- `test/features/pdf/extraction/stages/field_confidence_scorer_test.dart` - Field confidence tests (v3)
- `test/features/pdf/extraction/stages/header_consolidator_test.dart` - Header consolidator tests (v3)
- `test/features/pdf/extraction/stages/numeric_interpreter_test.dart` - Numeric interpreter tests (v3)
- `test/features/pdf/extraction/stages/whitespace_inset_test.dart` - Whitespace inset tests
- `test/features/pdf/extraction/contracts/stage_2_to_3_contract_test.dart` - Contract tests (5)
- `test/features/pdf/extraction/contracts/stage_3_to_4a_contract_test.dart` - Contract tests (5)
- `test/features/pdf/extraction/contracts/stage_4a_to_4b_contract_test.dart` - Contract tests (5)
- `test/features/pdf/extraction/contracts/stage_4a_to_4a1_contract_test.dart` - Contract tests (v3, new)

### Legacy Pipeline (Pre-Stage Architecture — files removed from disk)
- `lib/features/pdf/services/pdf_import_service.dart` - Main import flow (still exists)
- `lib/features/pdf/services/extraction/deprecated/` - Deprecated stages moved here (document_analyzer, native_extractor, structure_preserver)

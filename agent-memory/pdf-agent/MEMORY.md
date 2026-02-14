# Agent Memory — PDF Agent

## Patterns Discovered

### Font Encoding Corruption in Native Text Extraction
Some PDF pages have corrupted font encoding that produces character substitutions even though text order is correct:
- Digits → Letters: `7→z`, `3→e`, `9↔6`
- Punctuation → Quotes: `,→'`, `.→'`
- Example: `$7,882,926.73` becomes `$z'882'629'ze`

Current pipeline is all-or-nothing (document-level OCR decision). Need per-page quality gate.

Reference: @per-page-quality-gate-design.md

## Gotchas & Quirks

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

### Stage 4A RowClassifierV2 (✅ Implemented + Refactored)
**Location**: `lib/features/pdf/services/extraction/stages/row_classifier_v2.dart`

Classifies rows from UnifiedExtractionResult into types (header, data, continuation, boilerplate, etc.).

**Two-phase design**:
- **Phase 1A (pre-column)**: Classifies using text content and geometry only
- **Phase 1B (post-column)**: Refines UNKNOWN rows using column boundaries → SECTION_HEADER or BOILERPLATE

**v2 improvements over v1**:
1. **Data-loss assertion**: Throws StateError if `inputCount ≠ outputCount` (row grouping must not drop elements)
2. **Edge-to-edge gap measurement**: `yGapToPrevious` measures whitespace between row edges, not center-to-center distance
   - More accurate for continuation detection with tall multi-line elements
   - Continuation threshold: gap < 2× median height (previously used 1.5× center distance)
3. **Unified data likelihood**: Single `dataLikelihood` score (0.0-1.0) replaces duplicate `_isDataRow()` and `_looksLikeDataPattern()` logic
   - Computed once per row, used by both Phase 1A and Phase 1B
   - Threshold 0.5 for DATA classification, 0.3 for Phase 1B preservation

**Test coverage**: 35 tests (29 unit + 6 v2-specific) covering classification accuracy, gap measurement, data likelihood, and no-data-loss validation.

### Stage 4B RegionDetectorV2 (✅ Implemented)
**Location**: `lib/features/pdf/services/extraction/stages/region_detector_v2.dart`

Detects table regions from classified rows using linear scan algorithm:
- **Cross-page header confirmation**: Headers near bottom (Y > 0.70) require DATA on next page
- **Multi-row header assembly**: Consecutive headers with complementary keywords (<50% character overlap)
- **Data row requirement**: Minimum 2 DATA rows after headers to confirm table
- **Termination conditions**: 3 consecutive BOILERPLATE or new HEADER
- **SECTION_HEADER aware**: Section headers don't break tables
- **Subtotal vs grand total differentiation**: TOTAL rows are soft signals; only terminate if no DATA follows

**Key constants (normalized 0.0-1.0)**:
- `kPageBottomThreshold = 0.70`
- `kMinDataRowsAfterHeader = 2`
- `kConsecutiveBoilerplateTermination = 3`
- `kMaxDataRowLookahead = 15`
- `kEndYEpsilon = 0.001` (floating-point tolerance only, no arbitrary padding)

**Data-accounting guarantee**: StateError thrown if `inputCount ≠ outputCount + excludedCount` (no data loss).

**ExcludedRows categorization**: All rows either in regions or excluded with reason (no_table_detected, before_first_table, between_tables, after_last_table).

**Test coverage**: 21 tests (18 unit + 5 contract) covering single/multi-table detection, subtotal vs grand total, cross-page boundaries with Y-coordinate warnings, header validation, edge cases, and coordinate validation.

**Critical improvements**:
- Data-accounting assertion prevents silent data loss
- Subtotal rows mid-table don't break table (only grand totals with no DATA ahead)
- endY uses actual element bottom edge + epsilon (no v1 padding workaround)
- Cross-page Y coordinate semantics documented in warnings

### Stage 4D CellExtractorV2 (✅ Implemented)
**Location**: `lib/features/pdf/services/extraction/stages/cell_extractor_v2.dart`

Assigns OCR elements to table cells based on column boundaries from Stage 4C using three-tier matching strategy:

**Matching Strategy**:
1. **Exact/Tolerance Overlap** (primary):
   - Check element overlap with column bounds ± tolerance (0.006 normalized)
   - Single overlap → assign to that column
   - Multiple overlaps → assign to column with greatest overlap width
2. **Nearest Column Fallback** (secondary):
   - If no overlap, calculate distance from element center to all column centers
   - Assign to nearest column if distance < 0.10 (10% page width)
3. **Orphan** (tertiary):
   - If distance > threshold, preserve as OrphanElement with reason

**Key constants (normalized 0.0-1.0)**:
- `kColumnOverlapTolerance = 0.006` (~5px at 850px width)
- `kOrphanDistanceThreshold = 0.10` (10% page width)

**Merged block handling**:
- Elements spanning multiple columns + containing spaces → "merged block" warning
- Assigned to column with greatest overlap (re-OCR deferred to pipeline orchestrator)
- Tracked as `merged_block_count` metric

**Row filtering**:
- Processes: DATA, CONTINUATION, TOTAL, UNKNOWN rows within table regions
- Skips: HEADER, SUBHEADER, BOILERPLATE, SECTION_HEADER rows

**Cell construction**:
- Fragments sorted left-to-right within column
- Text joined with spaces, trimmed
- Confidence averaged across fragments
- Bounding box calculated as union of all fragment bounds
- Empty columns → `Cell(value: null, elements: [], confidence: 0.0, boundingBox: Rect.zero)`

**Data-accounting guarantee**: StateError thrown if `inputCount ≠ outputCount + excludedCount` (no data loss).

**Test coverage**: 15 tests covering exact/tolerance/nearest matching, merged blocks, row filtering, multi-page processing, edge cases, and StageReport validation.

**Critical features**:
- All coordinates normalized 0.0-1.0 (NO pixel values)
- Per-page column adjustments supported via `ColumnMap.perPageAdjustments`
- Orphan elements preserved with distance metrics (never lost)
- No legacy imports from `table_extraction/`

## Frequently Referenced Files

### Extraction Pipeline (New Architecture)
- `lib/features/pdf/services/extraction/stages/document_quality_profiler.dart` - **Stage 0**: Per-page quality profiling
- `lib/features/pdf/services/extraction/stages/structure_preserver.dart` - **Stage 3**: OCR result structuring
- `lib/features/pdf/services/extraction/stages/row_classifier_v2.dart` - **Stage 4A**: Row classification (v2 refactored)
- `lib/features/pdf/services/extraction/stages/region_detector_v2.dart` - **Stage 4B**: Table region detection
- `lib/features/pdf/services/extraction/stages/cell_extractor_v2.dart` - **Stage 4D**: Cell extraction and column assignment
- `lib/features/pdf/services/extraction/models/document_profile.dart` - PageProfile and DocumentProfile types
- `lib/features/pdf/services/extraction/models/extraction_result.dart` - UnifiedExtractionResult type
- `lib/features/pdf/services/extraction/models/classified_rows.dart` - ClassifiedRow, ClassificationStats types
- `lib/features/pdf/services/extraction/models/detected_regions.dart` - TableRegion, ExcludedRow, DetectedRegions types
- `lib/features/pdf/services/extraction/models/column_map.dart` - ColumnDef, ColumnMap types
- `lib/features/pdf/services/extraction/models/cell_grid.dart` - Cell, OrphanElement, CellGrid types
- `lib/features/pdf/services/extraction/models/stage_report.dart` - StageReport with no-data-loss validation
- `test/features/pdf/extraction/stages/stage_0_document_analyzer_test.dart` - Unit tests (34)
- `test/features/pdf/extraction/stages/document_analyzer_integration_test.dart` - Integration tests (3)
- `test/features/pdf/extraction/stages/stage_3_structure_preserver_test.dart` - Unit tests (19)
- `test/features/pdf/extraction/stages/stage_4a_row_classifier_test.dart` - Unit tests (35, includes v2 improvements)
- `test/features/pdf/extraction/stages/stage_4b_region_detector_test.dart` - Unit tests (18)
- `test/features/pdf/extraction/stages/stage_4d_cell_extractor_test.dart` - Unit tests (15)
- `test/features/pdf/extraction/contracts/stage_2_to_3_contract_test.dart` - Contract tests (5)
- `test/features/pdf/extraction/contracts/stage_3_to_4a_contract_test.dart` - Contract tests (5)
- `test/features/pdf/extraction/contracts/stage_4a_to_4b_contract_test.dart` - Contract tests (5)

### Legacy Pipeline (Pre-Stage Architecture — files removed from disk)
- `lib/features/pdf/services/pdf_import_service.dart` - Main import flow (still exists)
- `lib/features/pdf/services/extraction/deprecated/` - Deprecated stages moved here (document_analyzer, native_extractor, structure_preserver)

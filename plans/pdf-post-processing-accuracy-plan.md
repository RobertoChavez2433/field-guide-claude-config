# PDF Import Post-Processing Accuracy Plan (Bid Items)

Date: 2026-02-04
Owner: Extraction pipeline (OCR + TableExtractor + TableRowParser)

## Evidence From Logs + PDF
- OCR now runs at 200 DPI for all pages (time guard disabled for small docs).
- Table region Y is being normalized (start/end were inverted in logs).
- Per-page column bounds are stable across pages (minor drift only).
- Primary failure pattern in logs: missing quantity and/or unit price while bid amount exists (example rows show qty empty but amount and unit price present).
- PDF text layer is inconsistent: page 2 text layer is partially readable but noisy; page 6 text layer is mostly garbage. This confirms we must trust OCR + post-processing rather than the embedded PDF text layer.

## Best-Practice Quality Targets (Applied to Bid Items)
We will implement post-processing rules that target the core data-quality dimensions for document extraction: accuracy, completeness, consistency, validity, and uniqueness. These dimensions are widely used to assess data fitness and should be reflected in our parsing rules and quality metrics. (Refs: GOV.UK/IBM data-quality dimensions, industry guidance on tolerances in matching systems.)

## Post-Processing Techniques -> Concrete Actions in Our Codebase

### 1) Data Normalization (Field-Consistent Canonical Forms)
Applies to:
- itemNumber: normalize whitespace, extract numeric prefix, move trailing text to description.
- description: normalize whitespace, remove OCR artifacts (pipes, stray symbols), preserve casing.
- unit: normalize to canonical unit list via alias mapping (already in TableRowParser).
- quantity/unitPrice/bidAmount: normalize commas, currency markers, OCR "S->$".

Code touchpoints:
- lib/features/pdf/services/table_extraction/table_row_parser.dart
- new: lib/features/pdf/services/table_extraction/post_process/post_process_normalization.dart

### 2) Type Enforcement & Cleaning (Numeric/Format Guarantees)
Applies to:
- quantity and currency fields must parse to double or be explicitly flagged invalid.
- enforce positive quantities (except LS), non-negative prices/amounts.

Code touchpoints:
- table_row_parser.dart: centralize parse helpers
- new: post_process_numeric.dart (parse + sanitize + range checks)

### 3) Enrichment & Transformation (Derive Missing Fields)
Applies to:
- If bidAmount + unitPrice exist -> infer quantity.
- If bidAmount + quantity exist -> infer unitPrice.
- If unit == LS and bidAmount exists -> set quantity=1, unitPrice=bidAmount.
- Derive extended amount (line total) for diagnostics, even if not stored.

Code touchpoints:
- new: post_process_consistency.dart (amount/price/qty inference)
- update TableRowParser or PostProcessEngine to apply repairs

### 4) Handling Missing/Empty Values
Applies to:
- Missing quantity: attempt inference; if still missing, mark needsReview and keep row.
- Missing unitPrice: attempt inference; if still missing, keep row but flag.
- Missing unit: attempt extraction from description tail; otherwise flag.

Code touchpoints:
- table_row_parser.dart (already partially implemented)
- new: PostProcessEngine warnings + flags

### 5) Validation Rules (Regex, Range, and Structural Checks)
Applies to:
- itemNumber must be numeric or numeric with decimal.
- unit must be in known list.
- quantity must be > 0 unless LS.
- unitPrice must be currency-like.
- bidAmount must be currency-like.
- description should not contain currency token; if it does, reassign price.

Code touchpoints:
- table_row_parser.dart
- new: post_process_validation.dart

### 6) Splitting / Multi-Value Handling
Applies to:
- Row may contain two item numbers (OCR row merge) -> split into two items.
- Unit/quantity merged into one field (e.g., "FT 640") -> split.
- Description contains appended unit/qty tokens -> split and reassign.

Code touchpoints:
- new: post_process_splitter.dart
- may reuse token classifier in lib/features/pdf/services/parsers/token_classifier.dart

### 7) Pipeline Efficiency / Fail Gracefully
Applies to:
- Never drop rows; convert failures into warnings + needsReview.
- Keep raw values for audit and corrections.
- Use named regex groups for readability and stable parsing.

Code touchpoints:
- PdfImportService: preserve parsedItems + warnings
- ParsedBidItem: consider attaching a raw/diagnostic struct

## Proposed Architecture (PostProcessEngine)

### Inputs
- ParsedBidItem + raw row data (itemNumberRaw, descriptionRaw, unitRaw, qtyRaw, unitPriceRaw, bidAmountRaw)
- Context: page index, row index, column boundaries (optional)

### Outputs
- ParsedBidItem (possibly corrected)
- Warnings + repair notes + confidence adjustments

### Stages
1) Normalize raw strings
2) Parse types (qty/price/amount)
3) Validate fields
4) Repair via consistency rules
5) Split if multiple items detected
6) Dedupe + sequence sanity checks
7) Update confidence + warnings

## PR-Sized Phases

### Phase 1 -- Post-Processing Scaffolding + Raw Data Capture
Scope:
- Add a PostProcessEngine that operates on ParsedBidItem (no behavior change yet).
- Extend TableRowParser to optionally return raw cell values (or introduce ParsedBidItemRaw wrapper).
- Add PostProcessConfig with tolerance defaults.

Files:
- new: lib/features/pdf/services/table_extraction/post_process/post_process_engine.dart
- new: lib/features/pdf/services/table_extraction/post_process/post_process_config.dart
- update: lib/features/pdf/services/table_extraction/table_row_parser.dart
- update: lib/features/pdf/services/pdf_import_service.dart

Tests:
- unit tests for PostProcessEngine no-op pass-through

### Phase 2 -- Normalization + Type Enforcement
Scope:
- Centralize normalization for currency, quantity, unit.
- Strip OCR artifacts and enforce numeric parsing in one place.
- Provide standard numeric parsing utility shared by TableRowParser and post-processor.

Files:
- new: post_process_normalization.dart
- new: post_process_numeric.dart
- update: table_row_parser.dart (use shared helpers)

Tests:
- unit tests for common OCR artifact cases (S->$, pipes, commas, malformed decimals)

### Phase 3 -- Consistency & Inference (Main Accuracy Gains)
Scope:
- Add amount/price/qty consistency checks with tolerances.
- Infer missing quantity or unit price using bidAmount and known field.
- LS handling (qty=1, price=amount) using explicit rules.

Files:
- new: post_process_consistency.dart
- update: post_process_engine.dart
- update: table_row_parser.dart to pass bidAmount into post-processor

Tests:
- inference cases: amount+price -> qty; amount+qty -> price; LS -> qty=1/price=amount

### Phase 4 -- Split/Multi-Value & Column-Shift Repairs
Scope:
- Detect multi-item rows (e.g., two item numbers in one row) and split.
- Detect unit/qty merged tokens in description and fix.
- Shift or swap cells when consistency check fails but values are present in wrong columns.

Files:
- new: post_process_splitter.dart
- update: post_process_engine.dart
- update: table_row_parser.dart (surface raw cell text for splitter)

Tests:
- split row with two item numbers
- shift fix when qty column holds price

### Phase 5 -- Dedupe, Sequencing, UI Review Flags
Scope:
- Deduplicate by itemNumber (merge identical or keep highest confidence).
- Sequence check (monotonic itemNumber; flag gaps or reversals by page).
- UI surfaces repair notes/warnings in PdfImportPreviewScreen.

Files:
- new: post_process_dedupe.dart
- update: post_process_engine.dart
- update: pdf_import_preview_screen.dart
- update: parser_quality_thresholds.dart (use post-processed values)

Tests:
- dedupe logic
- sequence warnings
- UI warning presentation

## Acceptance Criteria (Per-Doc Quality)
- % missing unit price reduced via inference.
- % missing quantity reduced via inference.
- Consistency check pass rate improves with tolerances.
- Rows that cannot be repaired are flagged for review, never dropped.
- ParserQualityMetrics reflect post-processed values.

## Notes / References
- Data quality dimensions (accuracy, completeness, validity, consistency, uniqueness) are common standards for assessing extraction output quality.
- Tolerance-based consistency checks (amount/price/qty) are standard in matching systems and provide safe variance windows for inferred values.

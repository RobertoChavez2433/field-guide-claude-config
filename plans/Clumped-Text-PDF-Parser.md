# Clumped Text PDF Parser Implementation Plan (Comprehensive)

**Created**: 2026-01-31 | **Status**: Ready for Implementation  
**Scope**: Fix parsing when Syncfusion returns a single concatenated text stream with no column spacing.  
**Key Constraint**: No OCR in scope. Must work inside app using Syncfusion text extraction.

---

## Context Snapshot (Current Codebase)

**Existing parsers and flow**
- `ColumnLayoutParser` uses `extractTextLines()` and X-position clustering:  
  `lib/features/pdf/services/parsers/column_layout_parser.dart`
- Fallback regex parser expects line-based spacing:  
  `lib/features/pdf/services/pdf_import_service.dart` (`_parseBidSchedule`)
- Current chain: Column → Regex (no clumped parser)
- `PdfImportResult` supports `parserUsed`, warnings, confidence, and preview UI.
- `ParsedBidItem` is the preview model with confidence/warnings.

**Observed failure mode**
- Extracted text concatenates columns with no whitespace:
  `ItemNo.DescriptionUnitEst.QuantityUnit PriceBid Amount6Erosion Control...`
- `extractTextLines()` yields one X cluster → column detection fails.

---

## Core Design: Clumped Text Parser

Introduce a **token-based state machine parser** that reconstructs rows without column spacing, driven by normalization + token classification. This becomes a middle fallback between column parsing and regex parsing.

---

## Phase 1 (P1): Shared Extraction + Diagnostics

**Goal**: Add a consistent text extraction path and diagnostics to support debugging.

**Logic**
- Avoid duplicating extraction logic. Provide a shared method that returns:
  - Raw text via `extractText()` or line fallback when empty.
  - Optional lightweight diagnostics (token samples, header detection).
- Keep diagnostics off by default; enable via const env flag.

**Files**
- `lib/features/pdf/services/pdf_import_service.dart`
  - Add a public helper (or internal utility class) to extract raw text for parsers.
- `lib/features/pdf/services/parsers/parser_diagnostics.dart` (NEW)
  - Minimal diagnostics logger (enabled by `PDF_PARSER_DIAGNOSTICS`).

**Deliverable**
- `extractRawText(document)` returns the same text used by all parsers.
- Diagnostics helper can log the first N characters and sample tokens.

---

## Phase 2 (P2): Text Normalization (Clumped Stream Repair)

**Goal**: Turn concatenated text into a token stream that can be parsed.

**Logic**
- Protect decimals before inserting spaces (`12.50` should not split).
- Insert spaces at transitions:
  - digit→letter (`6Erosion` → `6 Erosion`)
  - letter→digit (`Amount6` → `Amount 6`)
  - lower→Upper (`UnitPrice` → `Unit Price`)
  - currency→letter (`$2.80s` → `$2.80 s`)
- Restore decimals and normalize whitespace.
- Add an exception list for common tokens that should *not* split (e.g., `HDPE12`, `TypeB`).

**Files**
- `lib/features/pdf/services/parsers/text_normalizer.dart` (NEW)

**Tests**
- `test/features/pdf/parsers/text_normalizer_test.dart` (NEW)

---

## Phase 3 (P3): Token Classification

**Goal**: Classify each token into types to drive the state machine.

**Logic**
- Token types: `itemNumber`, `unit`, `quantity`, `currency`, `header`, `addendum`, `text`, `unknown`.
- Disambiguation rules:
  - `itemNumber` must match `^\d+(\.\d+)?$` and be followed by text or unit within a window.
  - `quantity` is numeric without currency markers and is expected after a `unit`.
  - `currency` accepts `$` and `\d+\.\d{2}`.
- Public unit list accessor so confidence logic can reuse it.

**Files**
- `lib/features/pdf/services/parsers/token_classifier.dart` (NEW)

**Tests**
- `test/features/pdf/parsers/token_classifier_test.dart` (NEW)

---

## Phase 4 (P4): Row State Machine

**Goal**: Convert classified tokens into rows without positional data.

**Logic**
- Stateful parsing sequence:
  `SEEK_ITEM → READ_DESC → SEEK_UNIT → SEEK_QTY → SEEK_PRICE → COMPLETE`
- Key safeguards:
  - If a second item number appears early, finalize previous row with warnings.
  - If no unit is found within N tokens after description, finalize as partial row.
  - If quantity is missing but price appears, mark quantity missing.
  - Maintain a `flush()` to emit the last row at end-of-stream.
- Add a `ParsedRowData` model with `isValid` and helper coercions.

**Files**
- `lib/features/pdf/services/parsers/row_state_machine.dart` (NEW)
- `lib/features/pdf/services/parsers/parsed_row_data.dart` (NEW)

**Tests**
- `test/features/pdf/parsers/row_state_machine_test.dart` (NEW)

---

## Phase 5 (P5): ClumpedTextParser

**Goal**: End-to-end parsing using normalization + classifier + state machine.

**Logic**
- Extract raw text via the shared extraction helper.
- Normalize text.
- Tokenize → classify.
- Skip header tokens carefully:
  - Do **not** drop tokens after the first item number.
  - Header skip should stop once the first valid item number is detected.
- Detect addendum sections from tokens (not from raw string alone).
- Convert rows to `ParsedBidItem` with confidence + warnings.
- Apply duplicate suffixing and move duplicates to the bottom (same logic as column parser).

**Files**
- `lib/features/pdf/services/parsers/clumped_text_parser.dart` (NEW)

**Tests**
- `test/features/pdf/parsers/clumped_text_parser_test.dart` (NEW)

---

## Phase 6 (P6): Parser Chain Integration

**Goal**: Integrate clumped parser into the fallback chain.

**Logic**
1) ColumnLayoutParser  
2) ClumpedTextParser  
3) Regex fallback

**Files**
- `lib/features/pdf/services/pdf_import_service.dart`
  - Add `ParserType.clumpedText`
  - Add parser instance and chain integration.
- `lib/features/pdf/services/parsers/parsers.dart`
  - Export new parser files.

---

## Phase 7 (P7): Confidence + Warnings

**Goal**: Ensure confidence/warnings are consistent with existing UI.

**Logic**
- Reuse existing confidence formula from column parser.
- Add warnings:
  - “Missing unit/quantity/price”
  - “Description too short”
  - “Possible header bleed into description”
  - “Bid amount mismatch” (if bid amount parsed)
- Ensure `ParsedBidItem` output includes warnings.

**Files**
- `lib/features/pdf/services/parsers/clumped_text_parser.dart`

---

## Phase 8 (P8): Tests + Fixtures

**Goal**: Regression coverage for clumped parsing.

**Fixtures**
- `test/fixtures/pdf/`:
  - `clumped_text_no_spacing.pdf` (current failing sample)
  - `column_layout_normal.pdf`
  - `mixed_formatting.pdf`
  - `addendum_duplicates.pdf`

**Tests**
- `test/features/pdf/parsers/clumped_text_parser_test.dart`
  - Asserts item count, first item fields, confidence thresholds.
- Ensure tests do not rely on OCR.

---

## Parser Selection Logic (Reasoning)

**Why this order?**
- ColumnLayoutParser is fastest and most accurate when text positions are valid.
- ClumpedTextParser is designed specifically for “no spacing” layouts.
- Regex fallback remains a safety net for simple line‑based PDFs.

---

## Known Risks + Mitigations

| Risk | Mitigation |
|------|------------|
| Numeric ambiguity (item vs quantity) | State machine enforces order; item only valid in SEEK_ITEM, quantity only valid after unit |
| Header tokens merged with row 1 | Header skip stops once first valid item is found |
| Over‑splitting during normalization | Exception list for common tokens like HDPE12/TypeB |
| False positives in description | Description tokens must appear between item and unit |
| Large PDFs | Limit diagnostics and avoid storing full token history |

---

## Success Criteria

1. Parses Springfield DWSRF PDF that currently yields 0 items.  
2. Extracts ≥90% bid items with correct fields.  
3. Confidence ≥0.8 for well‑formed rows.  
4. Clear warnings for partial/ambiguous rows.  
5. Performance: 6‑page PDF parses < 2 seconds.  

---

## File Summary

**New**
- `lib/features/pdf/services/parsers/text_normalizer.dart`
- `lib/features/pdf/services/parsers/token_classifier.dart`
- `lib/features/pdf/services/parsers/row_state_machine.dart`
- `lib/features/pdf/services/parsers/parsed_row_data.dart`
- `lib/features/pdf/services/parsers/clumped_text_parser.dart`
- `lib/features/pdf/services/parsers/parser_diagnostics.dart`

**Modified**
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/pdf/services/parsers/parsers.dart`

**Tests**
- `test/features/pdf/parsers/text_normalizer_test.dart`
- `test/features/pdf/parsers/token_classifier_test.dart`
- `test/features/pdf/parsers/row_state_machine_test.dart`
- `test/features/pdf/parsers/clumped_text_parser_test.dart`


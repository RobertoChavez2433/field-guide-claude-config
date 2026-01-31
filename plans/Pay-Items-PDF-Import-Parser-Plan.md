# Implementation Plan: Smart Pay Item PDF Import Parser

**Last Updated**: 2026-01-31
**Status**: DRAFT
**Scope**: Improve pay item PDF import to handle column layouts, wrapped descriptions, and minor layout deviations using Syncfusion text-line bounds. Preserve existing regex parser as fallback. Integrate with existing import preview screen.

---

## Background / Problem
Current import fails on the provided pay item PDF and returns “No pay items found.” The existing parser assumes each item exists on a single text line and matches a strict regex. The provided PDF is column-based with wrapped descriptions, which breaks that assumption.

**Sample PDF (provided):**
`C:\Users\rseba\Projects\Field Guide App\Pre-devolopment and brainstorming\Screenshot examples\Companies IDR Templates and examples\Pay items and M&P\864130 Springfield DWSRF Water System Improvements CTC [16-23] Pay Items.pdf`

**Current code paths:**
- Parser: `lib/features/pdf/services/pdf_import_service.dart`
- Preview UI (already exists): `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`
- Import entry points: `lib/features/projects/presentation/screens/project_setup_screen.dart`, `lib/features/quantities/presentation/screens/quantities_screen.dart`

---

## Goals
- Parse pay items from the provided PDF reliably.
- Be resilient to small deviations in column spacing and line wrapping.
- Preserve current regex parser as a fallback.
- Add diagnostics to quickly troubleshoot future PDFs.
- Handle duplicate item numbers by suffixing (e.g., `1a`, `1b`) and ordering duplicates at the end of the list.

---

## Phase 0: API Verification Spike (Pre-PR)

**Objective**: Confirm Syncfusion `extractTextLines()` API availability and behavior before committing to column-aware approach.

**Tasks**
- Write a throwaway script to call `PdfTextExtractor(document).extractTextLines()`.
- Document return types and available properties (`text`, `bounds`, `wordCollection`).
- Validate that word bounds are stable on the sample PDF.

**Acceptance**
- API behavior documented with sample output and a code snippet.
- Phase 2 approach confirmed viable or adjusted.

---

## Phase 1: Instrumentation + Baseline Diagnostics

**Objective**: Add structured debug output and an optional diagnostic mode to understand why lines fail to parse.

**Tasks**
- Add a `debug` or `diagnostics` parameter in `PdfImportService` import methods to avoid always-on logs.
- Log: total pages, total text length, per-page extracted text size, header detection attempts, and line/token summaries when diagnostics enabled.
- Log “scanned PDF not supported” when no extractable text.

**Files**
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/projects/presentation/screens/project_setup_screen.dart`
- `lib/features/quantities/presentation/screens/quantities_screen.dart`

**Acceptance**
- When diagnostics enabled, logs show extraction and parsing summary.
- Normal mode has no behavior change.

---

## Phase 2: Column-Aware Parser (Primary)

**Objective**: Parse column-based PDFs using text-line bounds and word positions.

**Approach**
1) Extract lines with geometry via `extractTextLines()`.
2) Detect header line by fuzzy keyword match (Item / Description / Unit / Qty / Price).
3) Infer column x‑ranges from header word positions with padding/tolerance.
4) Detect column alignment (left vs right) per column by sampling first data rows.
5) Parse data lines by bucketizing words into columns using x and alignment.
6) Stitch continuation lines into prior row’s description.
7) Normalize values (units, commas, prices, decimals).
8) Track per-line parse metrics (total non-empty lines, candidate lines, parsed rows).

**Continuation line detection**
- Continuation if:
  - No leading digits (no item number), and
  - Text falls primarily within Description column range, and
  - Previous row exists and is not complete.
- Reject continuation if text hits Qty/Price columns (treat as malformed row).

**Multi-page handling**
- Carry forward column ranges if header not detected on a page.
- If page starts with a line that aligns to inherited columns, parse without header.
- If page ends with an incomplete row, buffer it and attempt to stitch with first line of next page.

**Files**
- `lib/features/pdf/services/pdf_import_service.dart`

**Acceptance**
- Provided CTC PDF parses into non-zero items.
- At least 3 known rows match expected item number + description + qty + unit price.

---

## Phase 2.1: Duplicate Item Number Handling (Suffix + Ordering)

**Objective**: Ensure duplicates don’t fail import and are clearly grouped at the end.

**Rules**
- Detect duplicates by item number (case-insensitive) within a single import batch.
- First instance keeps original number (e.g., `1`).
- Subsequent duplicates get suffixed `1a`, `1b`, `1c` in encounter order.
- All suffixed duplicates are moved to the end of the import list (after all unique items).

**Implementation Notes**
- Apply suffixing before preview so the user sees the final item numbers.
- Maintain a stable sort key: `(isDuplicate, baseItemNumber, suffixIndex, originalIndex)`.
- Avoid collisions with existing DB items by checking repository duplicates at import time as well; if collision still happens, surface per-row error and keep the row unimported.

**Files**
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`

**Acceptance**
- Duplicate item numbers do not block import.
- Duplicates appear after all unique items in preview.

---

## Phase 2.2: Addendum Handling

**Objective**: Prevent collisions when multiple addendum sections reuse item numbers.

**Rules**
- Detect addendum boundaries: `/ADDENDUM\s*[A-Z#]?\s*\d*/i`.
- Track current addendum identifier.
- Optional prefix (config flag): `A-33`, `H-60`, `#1-33`.

**Acceptance**
- Addendum prefixing enabled by flag.
- Prefix is applied before duplicate handling.

---

## Phase 3: Robustness + Fallback Strategy

**Objective**: Make the parser resilient and safe for edge cases.

**Fallback thresholds**
- If column parsing yields < 50% of candidate data lines as valid rows → retry with looser tolerances.
- If < 5 rows parsed from a PDF with 50+ non-empty lines → fallback.
- Fallback cascade: Column parser → Looser tolerances → Regex parser → Empty with warning.

**Confidence score (per row)**
- +0.3 item number pattern
- +0.2 unit matches known list
- +0.2 quantity valid
- +0.2 unit price valid
- +0.1 description length (5–200 chars)

**Thresholds**
- < 0.5 flagged in preview
- < 0.3 excluded unless no better results exist

**Files**
- `lib/features/pdf/services/pdf_import_service.dart`

**Acceptance**
- Parser returns items for provided PDF.
- Parser continues to work for known existing PDFs (no regressions).

---

## Phase 4: Preview Enhancements (Existing Screen)

**Objective**: Add confidence/diagnostic context to the existing import preview screen.

**Tasks**
- Display per-row confidence indicator and warnings.
- Provide a summary banner for low-confidence counts.
- Show “scanned PDF / no extractable text” warning when applicable.
- Preserve partial-failure reporting: show per-row import errors (e.g., duplicate item numbers already in DB).
- Ensure quantities screen reloads items after a successful import preview (await the route result and refresh).

**Files**
- `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`
- `lib/features/quantities/presentation/screens/quantities_screen.dart`

**Acceptance**
- Users can identify questionable rows before import.
- Preview remains fully editable and selectable.

---

## Phase 5: Measurement Specs Parser (Enrich Existing Items)

**Objective**: Support measurement specs PDFs that are not in table format by enriching existing bid items (no quantity/unit changes).

**Approach**
- Identify item headers by pattern (e.g., `Item 203.03 - Description`).
- Treat subsequent lines as measurement/payment text until next item header.
- Match to existing bid items by item number (case-insensitive).
- Update only `measurementPayment` (and optionally description if missing).
- Do **not** modify `bidQuantity`, `unit`, or `unitPrice`.

**Notes**
- If a measurement spec item has no matching bid item, skip and add a warning.

---

## Phase 6: Tests + Fixtures

**Objective**: Prevent regressions.

**Add tests for**
1. Provided CTC PDF (baseline column-based format)
2. Simple single-line format (regex fallback)
3. No-header PDF (data starts immediately)
4. Multi-addendum PDF (overlapping item numbers)
5. Scanned PDF (no text extracted)
6. Duplicate item numbers (suffixing + ordering)

**Fixture strategy**
- Prefer storing PDFs if allowed.
- Otherwise, use synthetic extracted text fixtures and unit-test parsing utilities.

**Files**
- `test/services/pdf_import_service_test.dart` (new)
- `test/fixtures/` (optional)

---

## Phase 7 (Optional): Performance Optimization

**Objective**: Ensure parser performs well on large PDFs.

**Tasks**
- Process page-by-page rather than all-at-once.
- Consider isolate for parsing to avoid UI jank.
- Add timeout safeguard (e.g., 30 seconds).

**Acceptance**
- 100-page PDF parses without UI freeze.
- Memory usage remains reasonable.

---

## Notes / Risks
- OCR is out of scope; scanned PDFs will show an explicit warning.
- Column parsing depends on header detection; fuzzy matching reduces fragility.
- Preview UI already exists; the plan focuses on enhancing it rather than creating a new dialog.

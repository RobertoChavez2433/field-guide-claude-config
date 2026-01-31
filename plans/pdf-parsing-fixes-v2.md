# Implementation Plan v2: PDF Bid Schedule Parsing Fixes

## Purpose
Create a PR-sized, phased plan to materially improve PDF import accuracy and observability while minimizing regressions. This v2 incorporates gaps identified in the current plan against the codebase and log evidence.

## Review Findings (Gaps vs Codebase)

- Column parser failure is the first-order issue in the logs. It cannot find headers and clustering collapses to a single column, then falls back to clumped parsing. The current plan does not address ColumnLayoutParser at all.
- There is no “parser acceptance” gate. A parser can return items even when data quality is poor. We need quality-based rejection/auto-fallback to avoid bad previews.
- No instrumentation for raw text/line extraction that’s actually used in production flows. We should persist debug artifacts when diagnostics are enabled.
- Structural keyword filtering is duplicated between TokenClassifier and ClumpedTextParser in the existing plan. That should live in TokenClassifier only.
- The plan assumes currency patterns and boilerplate tokens solve most issues; but current log indicates header detection fails, which will remain unresolved without addressing column layout detection and where parsing starts.
- No plan for “scanned PDF” detection and OCR fallback. Currently, Syncfusion extraction is the only source of text.
- Tests are proposed but missing a fixture strategy. We need a way to pin real-world text extraction output without shipping full PDFs.

## Objectives

1. Improve parse accuracy on the known failing PDFs (contract/boilerplate in the same file).
2. Prevent mis-parsed “boilerplate sections” from surfacing as pay items.
3. Ensure correct parser selection and safe fallback if quality is low.
4. Build repeatable test fixtures for regression prevention.
5. Add an OCR fallback path for scanned or text-extraction failures.

## Phase 0 (PR 1): Observability + Fixtures

Goal: Make parsing debuggable and collect reproducible fixtures without changing output yet.

Changes
- Add a debug export option for PDF imports to save:
  - extracted raw text
  - per-page line samples (from `extractTextLines`)
  - parser used, confidence distribution, warnings count
- Add a small “parser diagnostics” result summary to `PdfImportResult.metadata`.
- Add a test fixture system for extracted text (not full PDFs): store sanitized text samples under `test/fixtures/pdf/`.

Files
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/pdf/services/parsers/parser_diagnostics.dart`
- `lib/features/pdf/services/parsers/clumped_text_parser.dart`
- `lib/features/pdf/services/parsers/column_layout_parser.dart`
- `test/features/pdf/parsers/` (new fixtures)

Tests
- Unit tests for “diagnostics metadata present when enabled”.
- Golden fixture parse tests based on extracted text samples.

Success
- We can reproduce the current failure using fixtures without a full PDF.

## Phase 1 (PR 2): ColumnLayoutParser Recovery + Header Detection

Goal: Improve header detection and ensure column parsing only begins after a reliable header.

Changes
- Expand header search across multiple pages (first N pages, not first 50 lines only).
- Require stronger header match (≥4 keywords or “item+description+qty/price”).
- If header found: only parse rows after header line index; ignore lines before it.
- If header not found: do not attempt to parse rows; return empty to force fallback.
- Add a quality gate for column parsing: if <X% rows have item+unit+qty OR unitPrice, treat as failure and fallback.

Files
- `lib/features/pdf/services/parsers/column_layout_parser.dart`
- `lib/features/pdf/services/pdf_import_service.dart`

Tests
- New tests for:
  - header detection across pages
  - column parser returns empty when no reliable header
  - “quality gate” reject behavior

Success
- Column parser no longer produces junk items from boilerplate sections.

## Phase 2 (PR 3): Clumped Text Parser & TokenClassifier Fixes

Goal: Stop “Section 5 / Article 3” from becoming pay items; allow more currency formats.

Changes
- Move structural keyword logic into `TokenClassifier` only.
- Add `_structuralKeywords` and block itemNumber when preceded by those tokens.
- Make currency parsing more permissive for 1–4 decimals (still requires `$`).
- Normalize `$ 500.00` -> `$500.00` in tokenizer (not in TextNormalizer).

Files
- `lib/features/pdf/services/parsers/token_classifier.dart`
- `lib/features/pdf/services/parsers/clumped_text_parser.dart`
- `lib/features/pdf/services/parsers/text_normalizer.dart` (only if needed)

Tests
- `TokenClassifier` tests for structural keywords and new currency formats.

Success
- “Section 5” lines no longer become item numbers.

## Phase 3 (PR 4): RowStateMachine Guards + Boilerplate Detection

Goal: Keep long legal language from producing fake items.

Changes
- Reduce `_maxTokensBeforeUnit` from 25 to 15, but with a safe fallback: if no unit after threshold, finalize row as invalid and do not add unless it has item+unit.
- Add boilerplate marker detection; when threshold exceeded, mark with warning and heavily reduce confidence.
- Add description length cap with warning (e.g., 150 chars), but keep full text in diagnostics export for review.
- Improve `flush()` warnings and avoid adding partial rows without item+unit.

Files
- `lib/features/pdf/services/parsers/row_state_machine.dart`
- `lib/features/pdf/services/parsers/parsed_row_data.dart`

Tests
- `RowStateMachine` tests for boilerplate threshold and max description.

Success
- No entries with item+description only; boilerplate detected and suppressed.

## Phase 4 (PR 5): Parser Acceptance + Confidence Filters

Goal: Prevent low-quality output even if parsing succeeded technically.

Changes
- Compute per-parser quality metrics (valid item ratio, avg confidence, % missing unit/qty/price).
- If below thresholds, return empty so PdfImportService falls back.
- Add a “confidence summary” for UI (e.g., “71 items need review; 55 missing unit price”).

Files
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/pdf/services/parsers/clumped_text_parser.dart`
- `lib/features/pdf/services/parsers/column_layout_parser.dart`

Tests
- Regression tests for fallback decisions.

Success
- UI no longer shows mostly bad items when parsing quality is low.

## Phase 5 (PR 6): OCR Fallback (Optional but Recommended)

Goal: Handle scanned or image-only PDFs where text extraction fails.

Detection
- If `extractRawText` is empty or below a text-density threshold, mark as “likely scanned”.

Approach Options
- On-device OCR: ML Kit (Android/iOS), Tesseract (desktop).
- Cloud OCR: Azure/AWS/GCP; best accuracy but needs network + cost control.

Implementation Sketch
- Introduce an `OcrService` interface with platform implementations.
- Add a feature flag in config to allow OCR fallback only when enabled.
- OCR output feeds the same clumped parser pipeline.

Risks
- Performance and latency.
- OCR cost and privacy concerns.

Success
- Scanned PDFs no longer fail or return zero items.

## Test Strategy (Overall)

- Unit tests for TokenClassifier, RowStateMachine, and parsing decisions.
- Snapshot tests from real extracted text fixtures.
- Manual tests with the known failing PDF.

## Open Questions

- Do we want to allow OCR automatically, or only after user confirmation?
- Can we store sanitized text fixtures in-repo (privacy review)?

## Verification Checklist

- `flutter test test/features/pdf/parsers/`
- Manual import of failing PDF: verify no boilerplate items, correct unit/qty/price mapping.
- Confirm parserUsed and diagnostics metadata appear in logs.

---

This plan is intended to be executed in 6 PR-sized phases to reduce risk and allow rapid feedback.

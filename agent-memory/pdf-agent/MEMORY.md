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

### Per-Page Quality Gate (Designed, Not Implemented Yet)
Designed a hybrid approach that preserves native text speed for good pages while OCR-ing only corrupted pages:
1. Extract native text from ALL pages
2. Assess quality per page using 4 heuristics
3. If any pages fail (score > 0.35), build mixed-mode element list
4. Pass mixed list to TableExtractor (already supports per-page sources)

Flow diagrams: @quality-gate-flow-diagram.md

## Frequently Referenced Files

### Extraction Pipeline
- `lib/features/pdf/services/pdf_import_service.dart:673-830` - Main import flow
- `lib/features/pdf/services/text_extraction/native_text_extractor.dart:44-115` - Native text extraction
- `lib/features/pdf/services/table_extraction/table_extractor.dart:112-120` - Table extraction (source-agnostic)

### Quality Checking
- `lib/features/pdf/services/pdf_import_service.dart:274-305` - Current `needsOcr()` (document-level)

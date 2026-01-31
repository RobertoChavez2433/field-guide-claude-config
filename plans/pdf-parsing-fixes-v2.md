# Implementation Plan v2: PDF Bid Schedule Parsing Fixes

## Purpose
Create a PR-sized, phased plan to materially improve PDF import accuracy and observability while minimizing regressions. This v2 incorporates gaps identified in the current plan against the codebase and log evidence.

---

## Expert Review Findings (Session 221)

### Key Insight
> "The plan treats symptoms (boilerplate, currency formats) but doesn't fix the **root architectural issue** (brittle header detection and clustering in ColumnLayoutParser)."

### Critical Issues Identified

| Issue | Location | Problem | Impact |
|-------|----------|---------|--------|
| **Clustering Algorithm** | `column_layout_parser.dart:28` | `_columnGapThreshold = 18.0` too small for wide columns | 60% of fallbacks |
| **Header Search Limit** | `column_layout_parser.dart:116` | Limited to first 50 lines, not first 3 pages | Cover sheet failures |
| **Structural Keywords** | `token_classifier.dart` | No filtering for "Section 5", "Article 3" | False positives |
| **Currency Pattern** | `token_classifier.dart:161` | Requires exactly 2 decimals | Misses `$12.5`, `$12.500` |
| **Description Cap** | `row_state_machine.dart` | No length limit on descriptions | 500+ char boilerplate |
| **Boilerplate Detection** | Not implemented | No phrase-based scoring | Legal text becomes items |

### Phase 0 Issues (Minor)
1. Diagnostics not integrated into `importMeasurementSpecs` or `importPayEstimate`
2. Boilerplate fixture test doesn't assert Section/Article numbers are NOT parsed
3. No test coverage for addendum handling in fixtures

### Expected Improvement
- **60-70% reduction** in parser failures
- **40% reduction** in false positives from boilerplate

---

## Review Findings (Gaps vs Codebase)

- Column parser failure is the first-order issue in the logs. It cannot find headers and clustering collapses to a single column, then falls back to clumped parsing. The current plan does not address ColumnLayoutParser at all.
- There is no "parser acceptance" gate. A parser can return items even when data quality is poor. We need quality-based rejection/auto-fallback to avoid bad previews.
- No instrumentation for raw text/line extraction that's actually used in production flows. We should persist debug artifacts when diagnostics are enabled.
- Structural keyword filtering is duplicated between TokenClassifier and ClumpedTextParser in the existing plan. That should live in TokenClassifier only.
- The plan assumes currency patterns and boilerplate tokens solve most issues; but current log indicates header detection fails, which will remain unresolved without addressing column layout detection and where parsing starts.
- No plan for "scanned PDF" detection and OCR fallback. Currently, Syncfusion extraction is the only source of text.
- Tests are proposed but missing a fixture strategy. We need a way to pin real-world text extraction output without shipping full PDFs.

## Objectives

1. Improve parse accuracy on the known failing PDFs (contract/boilerplate in the same file).
2. Prevent mis-parsed "boilerplate sections" from surfacing as pay items.
3. Ensure correct parser selection and safe fallback if quality is low.
4. Build repeatable test fixtures for regression prevention.
5. Add an OCR fallback path for scanned or text-extraction failures.

---

## Phase 0 (PR 1): Observability + Fixtures - COMPLETE

**Status**: ✅ Implemented in Session 221

Goal: Make parsing debuggable and collect reproducible fixtures without changing output yet.

Changes
- Add a debug export option for PDF imports to save:
  - extracted raw text
  - per-page line samples (from `extractTextLines`)
  - parser used, confidence distribution, warnings count
- Add a small "parser diagnostics" result summary to `PdfImportResult.metadata`.
- Add a test fixture system for extracted text (not full PDFs): store sanitized text samples under `test/fixtures/pdf/`.

Files Modified
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/pdf/services/parsers/parser_diagnostics.dart`

Files Created
- `test/fixtures/pdf/well_formatted_schedule.txt`
- `test/fixtures/pdf/clumped_text_schedule.txt`
- `test/fixtures/pdf/boilerplate_heavy.txt`
- `test/features/pdf/parsers/fixture_parser_test.dart`

Tests: 221 PDF parser tests passing

**Follow-up needed:**
- Add diagnostics to `importMeasurementSpecs` and `importPayEstimate`
- Add test assertions for addendum handling
- Add negative assertions for Section/Article numbers in boilerplate test

---

## Phase 1a (PR 2): ColumnLayoutParser Clustering Fix - COMPLETE

**Status**: ✅ Implemented in Session 222

Goal: Fix the root cause of column parser failures - clustering algorithm collapses to single column.

Changes
- **Adaptive gap threshold** based on page width (3% of width, min 18, max 50):
  ```dart
  static double _calculateGapThreshold(List<_TextWord> words) {
    if (words.isEmpty) return 18.0;
    final maxX = words.map((w) => w.left + w.width).reduce(max);
    final minX = words.map((w) => w.left).reduce(min);
    final pageWidth = maxX - minX;
    return (pageWidth * 0.03).clamp(18.0, 50.0);
  }
  ```
- **Multi-pass clustering** with fallback thresholds (18, 25, 35, 50):
  ```dart
  List<_ColumnCluster> _clusterWithMultiplePasses(List<_TextWord> words) {
    for (final threshold in [18.0, 25.0, 35.0, 50.0]) {
      final clusters = _clusterWordsWithThreshold(words, threshold);
      if (clusters.length >= 3) return clusters;
    }
    return [];
  }
  ```
- **Minimum cluster validation**: Require ≥3 clusters for successful detection

Files
- `lib/features/pdf/services/parsers/column_layout_parser.dart`

Tests
- Fixture tests with varying column widths
- Tests for multi-pass fallback behavior

Success
- Column parser successfully clusters 60% more PDFs before falling back

Files Modified
- `lib/features/pdf/services/parsers/column_layout_parser.dart`

Files Created
- `test/features/pdf/parsers/column_layout_parser_test.dart`
- `test/fixtures/pdf/header_on_page_2.txt`

Tests: 235 PDF parser tests passing (14 new tests added)

---

## Phase 1b (PR 3): Header Detection Across Pages - COMPLETE

**Status**: ✅ Implemented in Session 222

Goal: Find headers even when cover sheets or TOCs push them beyond line 50.

Changes
- **Search first N pages** instead of first N lines:
  ```dart
  int _findHeaderLine(List<_TextLine> lines) {
    const maxSearchPages = 3;
    final pagesSearched = <int>{};

    for (int i = 0; i < lines.length; i++) {
      if (pagesSearched.add(lines[i].pageIndex) &&
          pagesSearched.length > maxSearchPages) {
        break;
      }
      if (_isHeaderLine(lines[i])) return i;
    }
    return -1;
  }
  ```
- Require stronger header match (≥4 keywords or "item+description+qty/price")
- **If header found**: only parse rows after header line index; ignore lines before it
- **If header not found**: do not attempt to parse rows; return empty to force fallback
- Add a quality gate for column parsing: if <70% rows have item+unit+qty OR unitPrice, treat as failure and fallback

Files
- `lib/features/pdf/services/parsers/column_layout_parser.dart`

Tests
- `test/fixtures/pdf/header_on_page_2.txt` - new fixture
- Tests for multi-page header search
- Tests for "quality gate" reject behavior

Success
- Handles 90% of cover-sheet scenarios
- Column parser no longer produces junk items from boilerplate sections

**Implementation Note**: Phase 1a and 1b were combined into a single PR since they both modify `column_layout_parser.dart` and are tightly coupled.

---

## Phase 2 (PR 4): Structural Keywords + Currency Fix

Goal: Stop "Section 5 / Article 3" from becoming pay items; handle currency variations.

Changes
- Add structural keyword detection in `TokenClassifier`:
  ```dart
  static const Set<String> _structuralKeywords = {
    'SECTION', 'ARTICLE', 'CHAPTER', 'PART', 'DIVISION',
    'APPENDIX', 'SCHEDULE', 'EXHIBIT',
  };

  bool _isStructuralContext(String token, List<String> preceding) {
    if (preceding.isEmpty) return false;
    final prev = preceding.last.toUpperCase();
    return _structuralKeywords.contains(prev);
  }
  ```
- Fix currency pattern to allow 1-4 decimals:
  ```dart
  static final RegExp _currencyPattern = RegExp(
    r'^\$-?\d{1,3}(?:,\d{3})*(?:\.\d{1,4})?$|^\$-?\d+(?:\.\d{1,4})?$'
  );
  ```
- Normalize `$ 500.00` -> `$500.00` in tokenizer

Files
- `lib/features/pdf/services/parsers/token_classifier.dart`

Tests
- `test/fixtures/pdf/boilerplate_section_5.txt` - new fixture
- `test/fixtures/pdf/currency_variations.txt` - new fixture
- TokenClassifier tests for structural keywords

Success
- "Section 5" lines no longer become item numbers
- Currency variations like `$12.5` and `$12.5000` are parsed correctly

---

## Phase 3 (PR 5): Description Cap + Boilerplate Detection

Goal: Keep long legal language from producing fake items.

Changes
- Add description length cap (150 chars) with warning:
  ```dart
  void _addDescriptionToken(String token) {
    const maxDescriptionLength = 150;
    if (_currentRow.description.length >= maxDescriptionLength) {
      _currentRow = _currentRow.withWarning('Description truncated');
      return;
    }
    _currentRow = _currentRow.withDescriptionToken(token);
  }
  ```
- Add boilerplate phrase detection:
  ```dart
  class BoilerplateDetector {
    static const Set<String> _boilerplatePhrases = {
      'shall', 'must', 'required', 'accordance', 'provisions',
      'contractor', 'engineer', 'specifications', 'standards',
    };

    static bool isLikelyBoilerplate(String description) {
      return calculateBoilerplateScore(description) > 0.30;
    }
  }
  ```
- Reduce `_maxTokensBeforeUnit` from 25 to 12-15, with safe fallback: if no unit after threshold, finalize row as invalid and do not add unless it has item+unit
- Improve `flush()` warnings and avoid adding partial rows without item+unit

Files
- `lib/features/pdf/services/parsers/row_state_machine.dart`
- `lib/features/pdf/services/parsers/parsed_row_data.dart`

Tests
- `test/fixtures/pdf/runaway_description.txt` - new fixture
- RowStateMachine tests for description cap and boilerplate
- RowStateMachine tests for flush() behavior with partial rows

Success
- 70% reduction in boilerplate false positives
- No entries with item+description only; boilerplate detected and suppressed

---

## Phase 4 (PR 6): Quality Gates + Thresholds

Goal: Prevent low-quality output even if parsing succeeded technically.

Changes
- Define concrete quality thresholds:
  ```dart
  class ParserQualityThresholds {
    static const double minValidItemRatio = 0.70;
    static const double minAverageConfidence = 0.60;
    static const double maxMissingUnitRatio = 0.30;
    static const double maxMissingPriceRatio = 0.30;
    static const int minItemCount = 3;
  }
  ```
- Compute per-parser quality metrics (valid item ratio, avg confidence, % missing unit/qty/price)
- Implement quality gate in each parser
- If below thresholds, return empty so PdfImportService falls back
- Add a "confidence summary" for UI (e.g., "71 items need review; 55 missing unit price")
- Add scanned PDF detection:
  ```dart
  bool _isLikelyScannedPdf(PdfDocument document, String extractedText) {
    final charsPerPage = extractedText.length / document.pages.count;
    if (charsPerPage < 50) return true;
    // ... additional heuristics
  }
  ```

Files
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/pdf/services/parsers/clumped_text_parser.dart`
- `lib/features/pdf/services/parsers/column_layout_parser.dart`

Tests
- Regression tests for fallback decisions
- Tests for scanned PDF detection

Success
- UI no longer shows mostly bad items when parsing quality is low

---

## Phase 5 (PR 7): OCR Fallback (Deferred)

**Status**: Defer until Phases 1-4 evaluated

Goal: Handle scanned or image-only PDFs where text extraction fails.

Detection
- If `extractRawText` is empty or below text-density threshold, mark as "likely scanned"

Approach Options
- On-device OCR: ML Kit (Android/iOS), Tesseract (desktop)
- Cloud OCR: Azure/AWS/GCP; best accuracy but needs network + cost control

Implementation Sketch
- Introduce an `OcrService` interface with platform implementations
- Add a feature flag in config to allow OCR fallback only when enabled
- OCR output feeds the same clumped parser pipeline

Risks
- Performance and latency
- OCR cost and privacy concerns

Success
- Scanned PDFs no longer fail or return zero items

---

## Future Enhancements (P3)

Based on expert review, consider for later phases:

1. **Adaptive Timeouts** - Make `_maxTokensBeforeUnit` adapt based on observed description lengths
2. **Fuzzy Header Matching** - Use Levenshtein distance for OCR error tolerance
3. **Confidence Calibration** - Adjust thresholds based on PDF source (MDOT vs unknown)
4. **Incremental Parsing** - Early exit when pattern is clear
5. **Cross-Parser Validation** - Compare column vs clumped results
6. **Multi-Language Support** - Add Spanish/international units (M3, M2, KG, METRO)

---

## Test Strategy (Overall)

- Unit tests for TokenClassifier, RowStateMachine, and parsing decisions
- Snapshot tests from real extracted text fixtures
- **Regression baseline** with expected results per fixture:
  ```yaml
  well_formatted_schedule:
    expected_items: 12
    expected_avg_confidence: 0.95
  clumped_text_schedule:
    expected_items: 10
    expected_avg_confidence: 0.80
  boilerplate_heavy:
    expected_items: 3
    max_false_positives: 0
  ```
- Manual tests with the known failing PDF

## Open Questions

- Do we want to allow OCR automatically, or only after user confirmation?
- Can we store sanitized text fixtures in-repo (privacy review)?

## Verification Checklist

- `flutter test test/features/pdf/parsers/`
- Manual import of failing PDF: verify no boilerplate items, correct unit/qty/price mapping
- Confirm parserUsed and diagnostics metadata appear in logs

---

## Revised Phase Order (Priority-Based)

| Phase | Focus | Est. Lines | Risk | Impact |
|-------|-------|------------|------|--------|
| **0** | ✅ Diagnostics + Fixtures | ~500 | Low | Observability |
| **1a** | ✅ Clustering algorithm fix | ~150 | Medium | **60% fallback reduction** |
| **1b** | ✅ Multi-page header search | ~100 | Low | Cover sheet handling |
| **2** | Structural keywords + currency | ~100 | Low | False positive reduction |
| **3** | Description cap + boilerplate | ~120 | Low | **40% boilerplate reduction** |
| **4** | Quality gates + scanned detection | ~150 | Medium | Bad preview prevention |
| **5** | OCR fallback (deferred) | ~800+ | High | Scanned PDF support |

**Estimated total effort for P0-P4:** 5-7 days
**Expected accuracy improvement:** 60-70% reduction in failures

---

This plan is intended to be executed in PR-sized phases to reduce risk and allow rapid feedback.

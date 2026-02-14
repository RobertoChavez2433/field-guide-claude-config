# OCR-Only Pipeline Migration + Golden Benchmark Framework

**Date:** 2026-02-12
**Status:** Approved
**Drivers:** CMap corruption unreliability (A) + inconsistent native extraction results (B)

---

## Overview

### Purpose
Migrate the PDF extraction pipeline from a native/OCR/hybrid routing model to OCR-only, deprecating native text extraction stages. Simultaneously build a comprehensive golden test and benchmarking framework to establish baselines and measure pipeline improvements.

### Scope

**Included:**
- Deprecate Stage 0 routing, Stage 2A (NativeExtractor), Stage 3 merge logic -> move to `deprecated/` folder
- Refactor pipeline to always take OCR path (render -> preprocess -> recognize)
- Fix re-extraction loop (currently broken with OCR-only - attempts 0 and 1 are identical)
- Repurpose Stage 0 as document quality profiler (keeps metrics, drops routing)
- Simplify Stage 3 to pass-through with coordinate validation
- Regenerate all 9 Springfield fixture JSONs from OCR-only pipeline
- Build 3-layer golden test (regression + ground truth + convergence)
- Build parameterized benchmark suite for DPI/PSM variant testing
- Recalibrate quality score thresholds if needed after OCR baseline data

**Excluded (future work):**
- Actually running the benchmark variants (Option B retry strategy) - comes after goldens established
- Threshold recalibration - needs OCR baseline data first
- Adaptive DPI rework for large documents - separate concern
- Adding additional test PDFs beyond Springfield

### Success Criteria
- Pipeline produces OCR-only results for Springfield PDF
- All 9 stage fixtures regenerated from OCR-only output
- Golden test passes with OCR baseline metrics documented
- Benchmark framework can run N configs against ground truth and produce comparison table
- Deprecated code is isolated in `deprecated/` folder with no imports from active pipeline
- No regressions in Stages 4-6 (table detection, parsing, quality validation)

---

## Pipeline Changes

### Files Moving to `deprecated/`

| File | Current Role | Why Deprecated |
|------|-------------|----------------|
| `stages/native_extractor.dart` | Stage 2A: Syncfusion text extraction | No longer used |
| `stages/document_analyzer.dart` | Stage 0: Native vs OCR routing | Replaced by quality profiler |
| `stages/structure_preserver.dart` | Stage 3: Native + OCR merge | Replaced by OCR pass-through |

Location: `lib/features/pdf/services/extraction/deprecated/`

### New/Modified Files

**Stage 0 replacement: `document_quality_profiler.dart`**
- Keeps: page count, basic text metrics for quality reporting
- Drops: native/OCR/hybrid routing decision
- Output: `DocumentProfile` with `strategy: 'ocr'` for all pages
- Purpose: early warning for problematic PDFs (blank pages, scanned vs digital)

**Stage 3 replacement: `element_validator.dart`**
- Keeps: coordinate bounds validation (clamp to 0.0-1.0), confidence aggregation
- Drops: native/OCR merge logic, hybrid overlap detection
- Input: OCR elements only
- Output: `UnifiedExtractionResult` (same shape, single source)

**Pipeline orchestrator: `extraction_pipeline.dart`**
- Remove Stage 2A call entirely
- Remove `forceFullOcr` config (OCR is always forced)
- Stage 0 -> Stage 2B (render -> preprocess -> recognize) -> Stage 3 -> Stages 4-6
- Fix re-extraction loop differentiation

### Re-extraction Loop (Fixed)

| Attempt | DPI | PSM | Preprocessing | Differentiation |
|---------|-----|-----|--------------|-----------------|
| 0 | 300 | 6 (single block) | Standard | Default config |
| 1 | 400 | 3 (auto segmentation) | Standard | Higher DPI + different segmentation |
| 2 | 400 | 6 (single block) | Enhanced contrast (1.5x floor) | Higher DPI + boosted preprocessing |

### Config Changes (`pipeline_config.dart`)

| Parameter | Action | Reason |
|-----------|--------|--------|
| `forceFullOcr` | Remove | Always OCR now, parameter is meaningless |
| `ocrDpi` | Keep | Still configurable per-document |
| `tesseractPsmMode` | Keep | Used by re-extraction loop |
| `hasEncodingCorruption` | Keep for now | Post-processor still uses it |

---

## Golden Test Framework (B + C + D)

### B: Per-Stage Golden Snapshots

Regenerate all 9 fixture JSONs from OCR-only pipeline output:

```
test/features/pdf/extraction/fixtures/
  springfield_document_profile.json      <- Stage 0 (quality profiler)
  springfield_unified_elements.json      <- Stage 2B-iii (OCR elements)
  springfield_classified_rows.json       <- Stage 4A
  springfield_detected_regions.json      <- Stage 4B
  springfield_column_map.json            <- Stage 4C
  springfield_cell_grid.json             <- Stage 4D
  springfield_parsed_items.json          <- Stage 4E
  springfield_processed_items.json       <- Stage 5
  springfield_quality_report.json        <- Stage 6
  springfield_ground_truth_items.json    <- Unchanged (verified source of truth)
  springfield_ground_truth_quality.json  <- Updated with OCR-only targets
```

`generate_golden_fixtures_test.dart` updated to run OCR-only pipeline.

### C: 3-Layer Golden Test

**File:** `springfield_golden_test.dart` (rewritten for OCR-only)

**Layer 1 - Regression Baseline:**
- Locks OCR-only pipeline output as the new baseline
- Item count, quality score, field distribution
- Assertions are exact: `expect(items.length, X)` where X = whatever OCR produces
- Any pipeline change that shifts these values breaks the test intentionally

**Layer 2 - Ground Truth Comparison:**
- Uses existing `GoldenFileMatcher` (no changes needed)
- Compares OCR output against 131 verified ground truth items
- Per-field accuracy: description (Levenshtein >= 0.90), quantity (+/-0.001), prices (+/-$0.01)
- Reports match rate, unmatched items, failed fields

**Layer 3 - Convergence Metrics:**
- Prints scoreboard (no hard assertions, just tracking):

```
OCR-Only Benchmark (Springfield, 300 DPI, PSM 6):
  Items:        X / 131  (X.X%)
  Match rate:   X.X%
  Total:        $X vs $7,882,926.73  (delta: $X)
  Quality:      X.XXX  (target: 0.850)
  Confidence:   X.X%  (median)
  Qty coverage: X.X%
  Price coverage: X.X%
  Bogus items:  X
```

- Loose guard-rail assertions prevent catastrophic regression:
  - `items.length >= 50` (sanity floor)
  - `matchRate >= 0.10` (sanity floor)
  - These ratchet upward as pipeline improves

### D: Benchmark Variant Suite

**File:** `springfield_benchmark_test.dart` (new)

Parameterized test with configs:

```dart
final configs = [
  BenchmarkConfig(name: '300 DPI, PSM 6', dpi: 300, psm: 6),
  BenchmarkConfig(name: '400 DPI, PSM 6', dpi: 400, psm: 6),
  BenchmarkConfig(name: '300 DPI, PSM 3', dpi: 300, psm: 3),
  BenchmarkConfig(name: '400 DPI, PSM 3', dpi: 400, psm: 3),
  BenchmarkConfig(name: '400 DPI, PSM 6, enhanced', dpi: 400, psm: 6, enhancedPreprocess: true),
];
```

**Per-config metrics:**

| Metric | Description |
|--------|-------------|
| Match rate | % of 131 items matched by itemNumber |
| Field accuracy | Per-field pass rates (description, unit, qty, price, amount) |
| Total accuracy | `|sum - $7,882,926.73| / $7,882,926.73` |
| Quality score | Pipeline's own quality assessment |
| Duration | Wall-clock time for full pipeline run |

Output: Console table + `springfield_benchmark_results.json`

Trigger: Manual only via `--dart-define=SPRINGFIELD_PDF='path/to/pdf'`

---

## Implementation Phases

### Phase 1: Deprecation & Pipeline Refactor
**Agent:** `backend-data-layer-agent`

| Step | Action | Files |
|------|--------|-------|
| 1a | Create `deprecated/` folder | `lib/features/pdf/services/extraction/deprecated/` |
| 1b | Move 3 deprecated files | `native_extractor.dart`, `document_analyzer.dart`, `structure_preserver.dart` |
| 1c | Create `document_quality_profiler.dart` | Slim Stage 0 replacement |
| 1d | Create `element_validator.dart` | Slim Stage 3 replacement |
| 1e | Refactor `extraction_pipeline.dart` | Remove Stage 2A, wire new stages |
| 1f | Update `pipeline_config.dart` | Remove `forceFullOcr` parameter |
| 1g | Fix re-extraction loop | 3 differentiated attempts |
| 1h | Verify compilation | `flutter analyze` passes |

### Phase 2: Regenerate OCR Golden Fixtures
**Agent:** `qa-testing-agent`

| Step | Action |
|------|--------|
| 2a | Update `generate_golden_fixtures_test.dart` for OCR-only |
| 2b | Run fixture generation (9 updated JSONs) |
| 2c | Update `springfield_ground_truth_quality.json` |
| 2d | Verify fixtures are valid |

### Phase 3: Rewrite Golden Test (3-Layer)
**Agent:** `qa-testing-agent`

| Step | Action |
|------|--------|
| 3a | Layer 1: Set OCR regression baselines |
| 3b | Layer 2: Wire ground truth comparison |
| 3c | Layer 3: Convergence metrics scoreboard |
| 3d | Update contract tests for OCR-only |
| 3e | Update `stage_trace_diagnostic_test.dart` |

### Phase 4: Benchmark Variant Suite
**Agent:** `qa-testing-agent`

| Step | Action |
|------|--------|
| 4a | Create `springfield_benchmark_test.dart` |
| 4b | Create `BenchmarkConfig` model |
| 4c | Implement comparison table output |
| 4d | Run initial benchmark for all 5 configs |

### Phase 5: Cleanup & Verification
**Agent:** `code-review-agent` + `qa-testing-agent`

| Step | Action |
|------|--------|
| 5a | Verify no imports reference deprecated files |
| 5b | `flutter analyze` - zero errors |
| 5c | Full test suite passing |
| 5d | Golden test passes with OCR baselines |
| 5e | Benchmark suite generates comparison table |
| 5f | Document results in plan file |

### Dependency Order

```
Phase 1 (refactor) -> Phase 2 (fixtures) -> Phase 3 (golden test)
                                          -> Phase 4 (benchmark suite)
                                                     |
                                               Phase 5 (cleanup)
```

Phases 3 and 4 can run in parallel after Phase 2.

---

## Ground Truth Validation (Confirmed)

| Check | Result |
|-------|--------|
| Item count | 131 |
| Sum of bid_amounts | $7,882,926.73 (exact match) |
| qty x unitPrice = bidAmount | 0 failures (all 131 pass) |
| All 6 fields populated | 131/131 |

## Key Decisions Made

1. **OCR-only because**: CMap corruption is unpredictable across PDF generators; clean digital PDFs perform well with OCR
2. **Deprecate, don't delete**: Keep deprecated code in `deprecated/` folder as fallback
3. **Re-extraction strategy**: Test DPI + PSM + preprocessing variants via benchmark suite before deciding final retry logic
4. **Ground truth**: Existing `springfield_ground_truth_items.json` verified and reused
5. **Golden framework**: B (per-stage snapshots) + C (3-layer test) + D (benchmark variants)

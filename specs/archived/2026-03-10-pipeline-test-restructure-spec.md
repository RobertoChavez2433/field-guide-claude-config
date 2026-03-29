# Pipeline Test Suite Restructure — Spec

**Date**: 2026-03-10 | **Status**: FINAL — All adversarial review items addressed

## Overview

### Purpose
Replace the fragmented, assertion-weak PDF extraction test suite with a unified report-first system that traces every item through every pipeline stage, detects regressions automatically, and produces both machine-readable (JSON) and human-readable (MD) outputs.

### What It Replaces
8 files (~7,400 lines) with:
- 37+ print-only statements with zero assertions
- 3 duplicate comparison implementations (Dart matcher, CLI tool, Python scripts) with inconsistent normalization
- Silently-skipping fixture-gated tests that pass without running
- A benchmark test that produces 0 items and passes (no assertions)
- Hardcoded stale thresholds (quality >= 0.40, item delta <= 131, match rate >= 0.93)

### What It Produces (Every Run)
1. **JSON trace** — every item at every stage, all raw values, per-stage timing, version metadata. Machine-readable. Feeds regression gate.
2. **Stage statistics table (MD)** — per-stage health metrics with timing. What came in, what came out, confidence, errors, compared to previous run.
3. **Item flow table (MD)** — per-item field values as they transform through all data-transforming stages. Where data degrades.

### Key Design Decisions
- **Report-first, assert-second**: Pipeline always saves full report regardless of pass/fail. Assertions evaluate the report.
- **Full stage trace**: Every item traced through every data-transforming stage (22 stages). All data captured. Metadata-only stages (5 stages) traced per-run, not per-item. See Stage Classification Table below.
- **Per-platform regression baselines**: Each platform/device maintains its own `latest-<platform>/` baseline. Cross-platform comparison is a separate CLI operation — not part of the regression gate.
- **Regression gate**: Compare to previous run's platform-specific baseline. No hardcoded thresholds. Ratchet effect — pipeline quality can only go up.
- **No normalization in test layer**: LSUM vs LS is a real mismatch. Pipeline should normalize in Stage 5, not the test.
- **Single comparison implementation**: One Dart tool replaces 3 separate implementations.
- **Integration test**: Runs via `flutter test integration_test/...` — never built into release app. No app bloat.
- **Desktop + device**: Windows for CI baseline, Android devices for cross-platform parity.
- **Multi-attempt handling**: Only the best attempt's stage outputs are captured and reported, matching existing `generate_golden_fixtures_test.dart` behavior. The pipeline runs up to 3 attempts; best attempt is selected by item count (most items = best quality). Attempt metadata (which attempt was selected, total attempts) is recorded in report metadata.
- **Replaces fixture generator**: `springfield_report_test.dart` fully replaces `generate_golden_fixtures_test.dart`. It does everything the fixture generator did (run pipeline, capture all stage outputs) plus reporting, regression gating, and ground truth comparison. The fixture generator is added to the deletion list.

### Success Criteria
- [ ] Every data-transforming stage traced for every item (22 stages x 131 GT items)
- [ ] Every metadata-only stage traced per-run (5 stages)
- [ ] No silent failures — every metric compared or explicitly reported
- [ ] No normalization in comparison layer — straight comparison
- [ ] Single comparison implementation used everywhere
- [ ] Regression gate catches any metric degradation (per-platform baselines)
- [ ] Reports clearly differentiate platform (Windows vs device model)
- [ ] Old tests deleted only after new system verified
- [ ] Documentation header explains how to run on each platform
- [ ] M&P diagnostic test (`mp_stage_trace_diagnostic_test.dart`) will be migrated to this same pattern in a future phase

---

## Stage Classification Table

Definitive mapping of all `StageNames` constants from `lib/features/pdf/services/extraction/stages/stage_names.dart` (27 constants). Classification based on pipeline execution in `extraction_pipeline.dart` and `stageToFilename` wiring in `stage_fixtures.dart`.

### Data-Transforming Stages (22) — Traced Per-Item

These stages transform, classify, or score individual items/elements. Each item's state is captured at each stage.

| # | StageNames Constant | Pipeline Stage | What It Does |
|---|---------------------|---------------|--------------|
| 1 | `documentAnalysis` | Stage 0 | Profiles document (pages, strategy). Per-page, not per-item, but critical metadata. |
| 2 | `elementValidation` | Stage 3 | Validates/normalizes OCR element coordinates |
| 3 | `elementClamping` | Stage 3 (diag) | Clamping diagnostics for out-of-bounds elements |
| 4 | `rowClassification` | Stage 4A | Classifies rows as data/header/bogus |
| 5 | `headerConsolidationProvisional` | Pre-4B | Provisional header consolidation for region detection |
| 6 | `headerConsolidationFinal` | Post-4C | Final header consolidation with semantic columns |
| 7 | `rowMerging` | Stage 4A.5 | Merges continuation rows into parent rows |
| 8 | `regionDetection` | Stage 4B | Detects table regions on pages |
| 9 | `rowPathways` | Stage 4B (diag) | Row pathway diagnostics (which rows assigned to which regions) |
| 10 | `orphanElements` | Stage 4B (diag) | Orphan/excluded row diagnostics |
| 11 | `columnDetection` | Stage 4C | Detects column boundaries |
| 12 | `columnDetectionLayers` | Stage 4C (diag) | Layer-by-layer column detection diagnostics |
| 13 | `cellExtraction` | Stage 4D | Extracts cell contents from grid |
| 14 | `numericInterpretation` | Stage 4D.5 | Interprets numeric values from cell text |
| 15 | `rowParsing` | Stage 4E | Parses rows into structured bid items |
| 16 | `fieldConfidenceScoring` | Stage 4E.5 | Scores per-field confidence |
| 17 | `postNormalize` | Stage 5a | Unit normalization, repairs |
| 18 | `postSplit` | Stage 5b | Splits compound items |
| 19 | `postValidate` | Stage 5c | Math validation (qty x price = amount) |
| 20 | `postSequenceCorrect` | Stage 5d | Reorders items by sequence |
| 21 | `postDeduplicate` | Stage 5e | Merges duplicate items |
| 22 | `qualityValidation` | Stage 6 | Overall quality scoring and status |

### Metadata-Only Stages (5) — Traced Per-Run

These stages operate on pages/images, not individual items. Captured once per run in `stage_metrics`, not in the per-item `items` section.

| # | StageNames Constant | Pipeline Stage | What It Does |
|---|---------------------|---------------|--------------|
| 1 | `pageRendering` | Stage 2B-i | Renders PDF pages to images |
| 2 | `imagePreprocessing` | Stage 2B-ii | Enhances images (contrast, etc.) |
| 3 | `gridLineDetection` | Stage 2B-ii.5 | Detects grid lines on pages |
| 4 | `gridLineRemoval` | Stage 2B-ii.6 | Removes grid lines via inpainting |
| 5 | `textRecognition` | Stage 2B-iii | OCR — produces raw elements (per-page, not per-item) |

### Dead Constants (1) — Not Wired

| Constant | Status |
|----------|--------|
| `postColumnRefinement` | Defined in `StageNames` but never referenced anywhere in the codebase. Unused. |

### Aggregate Stage (1) — Composite

| Constant | Status |
|----------|--------|
| `postProcessing` | Composite output of stages 5a-5e. Contains final `ProcessedItems`. Traced per-item via its sub-stages. |

**Total: 27 constants = 22 data-transforming + 5 metadata-only + 1 dead + 1 aggregate (sub-stages already counted)**

The spec refers to "22 data-transforming stages" (traced per-item) and "5 metadata-only stages" (traced per-run). Combined: 27 `onStageOutput` callbacks in the pipeline.

---

## Architecture

### New Files (4)

| File | Location | Purpose | Est. Lines |
|------|----------|---------|------------|
| `springfield_report_test.dart` | `integration_test/` | Runs live pipeline, captures all stages, generates JSON trace + MD scorecard, runs regression gate. Replaces `generate_golden_fixtures_test.dart`. | ~400-500 |
| `pipeline_comparator.dart` | `test/features/pdf/extraction/golden/` | Library: single comparison implementation — item matching, field comparison, no normalization, regression gate logic | ~600-800 |
| `pipeline_comparator.dart` | `tools/` | CLI entry point: imports the library above, parses args, runs comparison, prints output. Consistent with existing `tools/gt_trace.dart`. | ~80-120 |
| `report_generator.dart` | `test/features/pdf/extraction/golden/` | Takes raw stage data + `PipelineResult`, produces JSON trace + MD scorecard files | ~500-700 |

**Line count guardrail**: If any file exceeds ~1,500 lines during implementation, it must be decomposed. The library `pipeline_comparator.dart` is the largest risk — if comparison logic + regression gate + cross-device mode exceeds the limit, split into `pipeline_comparator.dart` (core comparison) and `regression_gate.dart` (baseline loading, ratchet logic, tolerances).

### Output Structure

```
test/features/pdf/extraction/reports/              ← gitignored (see below)
├── latest-windows/                                ← platform-specific baseline
│   ├── report.json
│   └── scorecard.md
├── latest-sm-s938u/                               ← S25 Ultra baseline
│   ├── report.json
│   └── scorecard.md
├── latest-sm-g996u/                               ← S21+ baseline
│   ├── report.json
│   └── scorecard.md
├── latest-sm-x920/                                ← Tab S10+ baseline
│   ├── report.json
│   └── scorecard.md
├── windows_2026-03-10_1430/                       ← dated archive
│   ├── report.json
│   └── scorecard.md
├── sm-s938u_2026-03-10_1600/                      ← dated archive
│   ├── report.json
│   └── scorecard.md
└── sm-x920_2026-03-11_0900/
    ├── report.json
    └── scorecard.md
```

**Gitignore**: Add `test/features/pdf/extraction/reports/` to `.gitignore`. Only `springfield_ground_truth_items.json` (in fixtures/) is git-tracked. Each dev machine and CI environment establishes its own regression baseline on first run. Rationale: baselines are platform-specific and machine-specific — committing them would cause constant merge conflicts and false regressions.

**Archive Retention**: Keep the last 20 dated report folders per platform. When a new report is saved, if there are more than 20 existing archives for that platform, delete the oldest ones. This prevents unbounded disk growth from repeated test runs.

### How It Works

1. Integration test runs the full extraction pipeline with `onStageOutput` callbacks (same mechanism as current fixture generator)
2. Pipeline may run up to 3 attempts. All stage outputs are captured per-attempt (keyed by attempt number), matching `generate_golden_fixtures_test.dart` behavior (lines 65-96)
3. **Best attempt selection**: After pipeline completes, the best attempt is identified by item count (most items = best quality, same as fixture generator lines 98-115). Only the best attempt's stage outputs are used for reporting.
4. Passes best attempt's stage data to `report_generator.dart` which produces:
   - **JSON trace**: every item at every stage, all raw values, per-stage timing, version metadata
   - **MD scorecard**: stage statistics table + item flow table
5. Passes JSON trace to `pipeline_comparator.dart` which:
   - Loads previous `latest-<platform>/report.json` as regression baseline
   - Compares every metric (regression gate)
   - Loads ground truth from `springfield_ground_truth_items.json` (configurable path via `--ground-truth` parameter in CLI mode) for accuracy reporting
6. Saves new report as both `latest-<platform>/` (overwrites) and dated archive `<platform>_<date>_<time>/`
7. Enforces archive retention (max 20 per platform, oldest auto-deleted)
8. Assertions run against comparison results — fail if any metric regressed (unless `--no-gate` mode is active)

### Android File I/O

Integration tests on Android cannot write to the project's `test/...` path because the test runs on-device, not on the host machine. The mechanism:

1. **On-device**: `springfield_report_test.dart` detects Android platform and writes reports to app-accessible storage: `getApplicationDocumentsDirectory()` → `<app-docs>/extraction_reports/`
2. **Post-test pull**: The test's doc header includes an `adb pull` command to copy reports back to the project directory:
   ```
   adb -s <serial> shell 'run-as com.fieldguideapp.inspector \
     cp -r files/extraction_reports/ /sdcard/extraction_reports/'
   adb -s <serial> pull /sdcard/extraction_reports/ \
     test/features/pdf/extraction/reports/
   ```
3. **Regression gate on-device**: The regression gate still works on-device — it reads the previous `latest-<platform>/` from on-device storage. The gate runs on-device; the pull step is only for archival/inspection on the host.
4. **Ground truth on-device**: The ground truth file is bundled as a test asset or pushed via `adb push` before the test run. The test doc header documents both options.

### `--no-gate` Mode

For exploratory/diagnostic runs where you want the full report without assertions blocking on regressions:

```
flutter test integration_test/springfield_report_test.dart \
  -d windows --dart-define=SPRINGFIELD_PDF="..." --dart-define=NO_GATE=true
```

When `NO_GATE=true`, the test still generates the full report and saves it, but skips all regression gate assertions. The scorecard will show `(NO-GATE MODE — assertions skipped)` in the verdict line.

### `--reset-baseline` Mode

For intentional regressions (e.g., changing normalization rules that correctly reduce match rate):

```
flutter test integration_test/springfield_report_test.dart \
  -d windows --dart-define=SPRINGFIELD_PDF="..." --dart-define=RESET_BASELINE=true
```

When `RESET_BASELINE=true`:
1. Archives the current `latest-<platform>/` baseline to a dated folder (e.g., `windows_2026-03-10_1430_archived/`)
2. Saves the new run as the new `latest-<platform>/` baseline
3. Skips regression gate assertions (since there's no valid previous baseline to compare against)
4. Scorecard shows `(BASELINE RESET — previous baseline archived)`

### Files To Delete (Last Phase)

| File | Lines | Replaced By |
|------|-------|-------------|
| `golden/stage_trace_diagnostic_test.dart` | 4,876 | `springfield_report_test.dart` |
| `golden/springfield_golden_test.dart` | 630 | `springfield_report_test.dart` |
| `golden/springfield_benchmark_test.dart` | 280 | `springfield_report_test.dart` |
| `golden/golden_file_matcher.dart` | 533 | `pipeline_comparator.dart` |
| `golden/golden_file_matcher_test.dart` | ~200 | `pipeline_comparator.dart` (with its own tests) |
| `golden/README.md` | 256 | This spec + new test doc headers |
| `integration_test/generate_golden_fixtures_test.dart` | 260 | `springfield_report_test.dart` (does everything the fixture generator did plus more) |
| `tools/gt_trace.dart` | 218 | `tools/pipeline_comparator.dart` CLI mode |
| `tools/compare_golden.py` | 156 | `tools/pipeline_comparator.dart` CLI mode |
| `tools/compare_stage_dumps.py` | 223 | `tools/pipeline_comparator.dart` cross-device mode |
| **Total** | **~7,632** | **~1,580-2,120 lines** |

**Note**: `integration/full_pipeline_integration_test.dart` imports `golden_file_matcher.dart` (line 28). When `golden_file_matcher.dart` is deleted, update this test's import to use `pipeline_comparator.dart` instead, or remove the import if the comparison logic is no longer needed in that test.

---

## Comparison Logic (`pipeline_comparator.dart`)

### Rules
- **No normalization** — LSUM vs LS is a real mismatch, reported as-is
- **String fields**: exact match (description, unit). Mismatch = FAIL with both values shown
- **Numeric fields**: tolerance of 0.01 for currency, 0.001 for quantity. Beyond tolerance = FAIL with delta shown
- **Item matching**: by item_number (exact). Not found = MISS. Extra items = BOGUS
- **Per-item verdict**: PASS (all fields match), FAIL (found but fields differ), MISS (not in pipeline output), BOGUS (in pipeline but not in ground truth)

### Three Modes, Same Code
1. **Report mode** (called by integration test): takes stage data, returns structured comparison result
2. **CLI mode** (`dart run tools/pipeline_comparator.dart`): point at any two JSON files, prints scorecard to terminal
3. **Cross-device mode** (`dart run tools/pipeline_comparator.dart --cross-device`): compare two report folders (e.g., Windows vs S25)

### Ground Truth Loading
`pipeline_comparator.dart` loads ground truth from `test/features/pdf/extraction/fixtures/springfield_ground_truth_items.json` by default. In CLI mode, the path is configurable via `--ground-truth <path>`. In integration test mode, the path is hardcoded to the fixtures directory (or bundled as a test asset on Android).

### Regression Gate Logic
- Load `latest-<platform>/report.json` as previous baseline (platform-specific)
- Compare every tracked metric: item count, quality, per-field accuracy, per-stage metrics
- Any regression beyond tolerance = test FAIL
- First run (no previous `latest-<platform>/`) = always PASS, establishes baseline
- **Ratchet effect**: as pipeline improves, baseline auto-tightens. 130 items today → 131 tomorrow → 130 next day = FAIL
- Cross-platform comparison is a separate CLI operation — the regression gate only compares within the same platform

### Regression Tolerances
- Item count: no regression (tolerance = 0)
- Quality score: tolerance = -0.01 (can drop 1%)
- Per-field accuracy: tolerance = -0.02 (can drop 2%)
- Checksum delta: tolerance = +$1.31 (derived: `numericTolerance × itemCount` = $0.01 × 131 = $1.31)
- Per-stage element counts: tolerance = 0 (no loss)

**Derivation note**: The checksum tolerance of $1.31 replaces the previous arbitrary $100. It represents the maximum cumulative rounding error if every item's bid_amount rounds to the tolerance limit ($0.01 per item × 131 items). If the ground truth item count changes, this tolerance should be recalculated: `$0.01 × GT_item_count`.

---

## Report Format

### JSON Trace (`report.json`)

Full data for every item at every stage. Structure:

```json
{
  "schema_version": 1,
  "metadata": {
    "date": "2026-03-10T14:30:22",
    "platform": "windows",
    "device_model": null,
    "git_hash": "e4602e7",
    "pipeline_duration_ms": 142000,
    "pdf_document_id": "springfield-864130",
    "attempt_selected": 0,
    "total_attempts": 1,
    "versions": {
      "tesseract": "5.5.2",
      "flutter": "3.32.0",
      "dart": "3.8.0",
      "pdfrx": "1.0.102",
      "flusseract": "0.1.0"
    }
  },
  "summary": {
    "items_extracted": 130,
    "ground_truth_items": 131,
    "overall_quality": 0.918,
    "checksum_extracted": 7602768.73,
    "checksum_ground_truth": 7882926.73,
    "match_rate": 0.992,
    "field_accuracy": {
      "description": 0.946,
      "unit": 0.798,
      "quantity": 0.973,
      "unit_price": 0.962,
      "bid_amount": 0.969
    }
  },
  "stage_metrics": {
    "stage_0_profile": {
      "elapsed_ms": 120,
      "pages": 6,
      "strategy": "ocr_only"
    },
    "stage_2b_render": {
      "elapsed_ms": 8500,
      "pages_rendered": 6,
      "dpi": 300,
      "format": "bgraRaw",
      "image_sizes_bytes": { "0": 14400000, "1": 14400000, "2": 14400000, "3": 14400000, "4": 14400000, "5": 14400000 }
    },
    "stage_2b_preprocess": {
      "elapsed_ms": 3200,
      "pages_preprocessed": 6,
      "contrast_delta": 0.12,
      "image_sizes_bytes": { "0": 245000, "1": 245000, "2": 245000, "3": 245000, "4": 245000, "5": 245000 }
    },
    "stage_2b_grid_detect": {
      "elapsed_ms": 1800,
      "grid_pages": 6,
      "h_lines": 45,
      "v_lines": 30
    },
    "stage_2b_grid_remove": {
      "elapsed_ms": 4200,
      "pages_cleaned": 6,
      "mask_coverage": 0.053
    },
    "stage_2b_ocr": {
      "elapsed_ms": 95000,
      "total_elements": 1249,
      "median_confidence": 0.95,
      "re_ocr_attempts": 42,
      "ocr_calls_per_page": { "0": 1, "1": 1, "2": 1, "3": 1, "4": 2, "5": 1 },
      "cpu_intensive": true
    },
    "stage_3_validate": {
      "elapsed_ms": 15,
      "elements_clamped": 0,
      "elements_total": 1249
    },
    "stage_4a_classify": {
      "elapsed_ms": 45,
      "data_rows": 131,
      "header_rows": 6,
      "bogus_rows": 1
    },
    "stage_4a_header_consol": {
      "elapsed_ms": 8,
      "logical_headers": 6,
      "absorbed_rows": 0
    },
    "stage_4a_merge": {
      "elapsed_ms": 12,
      "merged_rows": 131,
      "orphan_continuations": 0
    },
    "stage_4b_regions": {
      "elapsed_ms": 25,
      "regions": 6,
      "excluded_rows": 0
    },
    "stage_4c_columns": {
      "elapsed_ms": 35,
      "columns": 6,
      "method": "grid_line",
      "confidence": 0.95
    },
    "stage_4d_cells": {
      "elapsed_ms": 22,
      "cells_assigned": 786,
      "orphan_elements": 12
    },
    "stage_4d5_interpret": {
      "elapsed_ms": 18,
      "numeric_parsed": 780,
      "text_fallback": 6
    },
    "stage_4e_parse": {
      "elapsed_ms": 15,
      "items_parsed": 130,
      "rows_skipped": 1
    },
    "stage_4e5_confidence": {
      "elapsed_ms": 10,
      "median_field_confidence": 0.975
    },
    "stage_5_normalize": {
      "elapsed_ms": 5,
      "repairs": 3
    },
    "stage_5_split": {
      "elapsed_ms": 2,
      "items_split": 0
    },
    "stage_5_validate": {
      "elapsed_ms": 8,
      "math_checked": 128,
      "math_failed": 2
    },
    "stage_5_sequence": {
      "elapsed_ms": 3,
      "reordered": 0
    },
    "stage_5_dedup": {
      "elapsed_ms": 2,
      "duplicates_merged": 0
    },
    "stage_6_quality": {
      "elapsed_ms": 12,
      "overall_score": 0.918,
      "status": "autoAccept"
    }
  },
  "performance": {
    "total_pipeline_ms": 142000,
    "stage_breakdown_pct": {
      "ocr": 66.9,
      "rendering": 6.0,
      "preprocessing": 2.3,
      "grid_removal": 3.0,
      "table_extraction": 0.2,
      "post_processing": 0.02,
      "other": 21.6
    },
    "cpu_intensive_stages": ["stage_2b_ocr", "stage_2b_render", "stage_2b_grid_remove"],
    "total_ocr_calls": 7,
    "total_rendered_image_bytes": 86400000,
    "total_preprocessed_image_bytes": 1470000
  },
  "items": {
    "1": {
      "ground_truth": { "description": "Mobilization, Bonds, & Insurance (5% Max)", "unit": "LSUM", "quantity": 1.0, "unit_price": 390000.0, "bid_amount": 390000.0 },
      "stage_2b_ocr": { "found": true, "elements": 6, "confidence": 0.96 },
      "stage_3_validate": { "clamped": 0 },
      "stage_4a_classify": { "found": true, "row_type": "data", "row_idx": 1 },
      "stage_4a_header_consol": { "absorbed": false },
      "stage_4a_merge": { "continuations": 0 },
      "stage_4b_regions": { "region_idx": 0, "included": true },
      "stage_4c_columns": { "method": "grid_line", "confidence": 0.95 },
      "stage_4d_cells": { "description": "Mobilization, Bonds, & Insurance (5% Max)", "unit": "LSUM", "quantity": "1", "unit_price": "$390,000.00", "bid_amount": "$390,000.00", "orphans": 0 },
      "stage_4d5_interpret": { "quantity": 1.0, "unit_price": 390000.0, "bid_amount": 390000.0 },
      "stage_4e_parse": { "item_number": "1", "description": "Mobilization, Bonds, & Insurance (5% Max)", "unit": "LSUM", "quantity": 1.0, "unit_price": 390000.0, "bid_amount": 390000.0 },
      "stage_4e5_confidence": { "description": 0.925, "unit": 0.89, "quantity": 0.96, "unit_price": 0.92, "bid_amount": 0.96 },
      "stage_5_normalize": { "repairs": 0, "unit": "LS" },
      "stage_5_split": { "split": false },
      "stage_5_validate": { "math_ok": true },
      "stage_5_sequence": { "reordered": false },
      "stage_5_dedup": { "merged": false },
      "stage_5_final": { "item_number": "1", "description": "Mobilization, Bonds, & Insurance (5% Max)", "unit": "LS", "quantity": 1.0, "unit_price": 390000.0, "bid_amount": 390000.0, "confidence": 0.975 },
      "stage_6_quality": { "item_score": 0.975 },
      "gt_comparison": { "description": "PASS", "unit": "FAIL", "quantity": "PASS", "unit_price": "PASS", "bid_amount": "PASS", "unit_expected": "LSUM", "unit_actual": "LS" },
      "verdict": "FAIL"
    }
  }
}
```

**Schema versioning**: The `schema_version` field starts at `1`. Any breaking change to the JSON structure (field renames, removals, structural changes) increments the version. `pipeline_comparator.dart` checks schema_version before comparing — if the current report and baseline have different schema versions, it warns and skips regression comparison (baseline must be regenerated).

**Version tracking**: The `versions` object captures tool versions for reproducibility:
- `tesseract`: from `Tesseract.version` (flusseract binding, `packages/flusseract/lib/tesseract.dart:304`)
- `flutter`: from `Platform.version` or `flutter --version` output passed via dart-define
- `dart`: from `Platform.version` (runtime)
- `pdfrx`: from pubspec.lock or hardcoded constant (build-time)
- `flusseract`: from pubspec.lock or hardcoded constant (build-time)

**Note on version retrieval**: `tesseract` and `dart` versions are available at runtime. `flutter`, `pdfrx`, and `flusseract` versions require either build-time injection (dart-define) or reading pubspec.lock. The implementation should prefer runtime detection where possible, falling back to `"unknown"` if not available. A helper function `collectVersionMetadata()` in `report_generator.dart` will centralize this.

Note: In the example above, item 1 shows verdict FAIL because Stage 5 normalized LSUM->LS but ground truth says LSUM. This is exactly the kind of mismatch the no-normalization rule is designed to surface — either fix the pipeline or update the ground truth.

### MD Scorecard (`scorecard.md`)

Two tables:

**Stage Statistics Table** — per-stage health with previous run comparison and timing:

```markdown
# Springfield Extraction Scorecard
> Date: 2026-03-10 14:30 | Platform: Windows 11 | Tesseract: 5.5.2
> Git: e4602e7 | Duration: 142s | Verdict: PASS (0 regressions)
> Versions: Flutter 3.32.0 | Dart 3.8.0 | pdfrx 1.0.102 | flusseract 0.1.0

## Stage Statistics

| Stage | Metric | Current | Previous | Delta | Time (ms) | Status |
|-------|--------|---------|----------|-------|-----------|--------|
| 0 Profile | Pages | 6 | 6 | 0 | 120 | OK |
| 2B-i Render | Pages Rendered | 6 | 6 | 0 | 8500 | OK |
| 2B-i Render | DPI | 300 | 300 | 0 | — | OK |
| 2B-ii Preprocess | Contrast Delta | 0.12 | 0.12 | 0.00 | 3200 | OK |
| 2B-ii.5 Grid Detect | H Lines | 45 | 45 | 0 | 1800 | OK |
| 2B-ii.5 Grid Detect | V Lines | 30 | 30 | 0 | — | OK |
| 2B-ii.6 Grid Remove | Mask Coverage | 5.3% | 5.3% | 0.0% | 4200 | OK |
| 2B-iii OCR | Elements | 1249 | 1249 | 0 | 95000 | OK |
| 2B-iii OCR | Median Conf | 0.950 | 0.950 | 0.000 | — | OK |
| 2B-iii OCR | Re-OCR | 42 | 42 | 0 | — | OK |
| 3 Validate | Clamped | 0 | 0 | 0 | 15 | OK |
| 4A Classify | Data Rows | 131 | 131 | 0 | 45 | OK |
| 4A Classify | Header Rows | 6 | 6 | 0 | — | OK |
| 4A Classify | Bogus | 1 | 1 | 0 | — | OK |
| 4A Merge | Orphan Cont. | 0 | 0 | 0 | 12 | OK |
| 4B Regions | Regions | 6 | 6 | 0 | 25 | OK |
| 4B Regions | Excluded Rows | 0 | 0 | 0 | — | OK |
| 4C Columns | Columns | 6 | 6 | 0 | 35 | OK |
| 4C Columns | Confidence | 0.95 | 0.95 | 0.00 | — | OK |
| 4D Cells | Assigned | 786 | 786 | 0 | 22 | OK |
| 4D Cells | Orphans | 12 | 12 | 0 | — | OK |
| 4D.5 Interpret | Numeric | 780 | 780 | 0 | 18 | OK |
| 4E Parse | Items | 130 | 130 | 0 | 15 | OK |
| 4E Parse | Skipped | 1 | 1 | 0 | — | OK |
| 4E.5 Conf | Median | 0.975 | 0.975 | 0.000 | 10 | OK |
| 5 Post-Process | Repairs | 8 | 8 | 0 | 20 | OK |
| 6 Quality | Score | 0.918 | 0.918 | 0.000 | 12 | OK |
| 6 Quality | Status | autoAccept | autoAccept | — | — | OK |

## Performance Summary

| Metric | Value |
|--------|-------|
| Total Duration | 142s |
| OCR Time | 95.0s (66.9%) |
| Rendering Time | 8.5s (6.0%) |
| Grid Removal Time | 4.2s (3.0%) |
| Preprocessing Time | 3.2s (2.3%) |
| Table Extraction | 0.3s (0.2%) |
| Total OCR Calls | 7 |
| Rendered Image Size | 82.4 MB |
| Preprocessed Image Size | 1.4 MB |
| CPU-Intensive Stages | OCR, Rendering, Grid Removal |
```

**Item Flow Table** — per-item trace showing actual field values at key stages:

```markdown
## Item Flow (131 Ground Truth Items)

| # | OCR Found | Row Type | Cells Desc | Cells Amount | Parsed Amount | Final Amount | GT Amount | $ Delta | Verdict |
|---|-----------|----------|------------|-------------|---------------|-------------|-----------|---------|---------|
| 1 | Y (0.96) | data | Mobilization... | $390,000.00 | 390000.00 | 390000.00 | 390000.00 | $0 | PASS |
| 2 | Y (0.95) | data | Clearing &... | $15,000.00 | 15000.00 | 15000.00 | 15000.00 | $0 | PASS |
| ... | | | | | | | | | |
| 94 | Y (0.91) | data | Remove Exist... | $253,500.00 | 253500.00 | 253500.00 | 253500.00 | $0 | PASS |
| 95 | Y (0.89) | descCont | — | — | — | — | 26656.00 | -$26,656 | MISS |
| ... | | | | | | | | | |
| 131 | Y (0.94) | data | Mobilization... | $8,400.00 | 8400.00 | 8400.00 | 8400.00 | $0 | PASS |

## Summary
- PASS: 129 | FAIL: 0 | MISS: 1 | BOGUS: 1
- Items: 130 / 131 GT (99.2%)
- Checksum: $7,602,768.73 / $7,882,926.73 GT (-$280,158 / -3.55%)
- Field Accuracy: desc 94.6% | unit 79.8% | qty 97.3% | price 96.2% | amount 96.9%
```

---

## Test Documentation Header

The top of `springfield_report_test.dart` will include:

```dart
/// # Springfield Pipeline Report Test
///
/// ## How It Works
/// Runs the full extraction pipeline against the Springfield PDF, capturing
/// output from all 27 stage callbacks (22 data-transforming + 5 metadata-only)
/// for every item. Generates:
/// - JSON trace (report.json): machine-readable, every item at every stage
/// - MD scorecard (scorecard.md): stage statistics table + item flow table
///
/// Multi-attempt handling: Pipeline may run up to 3 attempts. Only the best
/// attempt's stages are captured (selected by item count, matching the fixture
/// generator's behavior). Attempt metadata is recorded in report.json.
///
/// Compares against previous run (regression gate, per-platform baseline).
/// If any metric regresses, the test fails. First run with no previous
/// baseline always passes.
///
/// This test REPLACES generate_golden_fixtures_test.dart — it does everything
/// the fixture generator did plus reporting and regression gating.
///
/// ## Commands
///
/// Windows:
///   flutter test integration_test/springfield_report_test.dart \
///     -d windows --dart-define=SPRINGFIELD_PDF="C:\path\to\springfield.pdf"
///
/// Galaxy S25 Ultra:
///   flutter test integration_test/springfield_report_test.dart \
///     -d R5CY12JTTPX --dart-define=SPRINGFIELD_PDF="/sdcard/springfield.pdf"
///
/// Galaxy S21+:
///   flutter test integration_test/springfield_report_test.dart \
///     -d RFCNC0Y975L --dart-define=SPRINGFIELD_PDF="/sdcard/springfield.pdf"
///
/// Galaxy Tab S10+:
///   flutter test integration_test/springfield_report_test.dart \
///     -d R52X90378YB --dart-define=SPRINGFIELD_PDF="/sdcard/springfield.pdf"
///
/// Exploratory (no regression gate):
///   flutter test integration_test/springfield_report_test.dart \
///     -d windows --dart-define=SPRINGFIELD_PDF="..." --dart-define=NO_GATE=true
///
/// Reset baseline (archive current, establish new):
///   flutter test integration_test/springfield_report_test.dart \
///     -d windows --dart-define=SPRINGFIELD_PDF="..." --dart-define=RESET_BASELINE=true
///
/// Pull reports from Android device:
///   adb -s <serial> shell 'run-as com.fieldguideapp.inspector \
///     cp -r files/extraction_reports/ /sdcard/extraction_reports/'
///   adb -s <serial> pull /sdcard/extraction_reports/ \
///     test/features/pdf/extraction/reports/
///
/// CLI Comparison (any two report folders):
///   dart run tools/pipeline_comparator.dart \
///     reports/latest-windows reports/latest-sm-s938u
///
/// CLI with custom ground truth:
///   dart run tools/pipeline_comparator.dart \
///     --ground-truth path/to/ground_truth.json \
///     reports/latest-windows reports/sm-s938u_2026-03-10
///
/// ## Output Location
/// Desktop: test/features/pdf/extraction/reports/
///   latest-<platform>/  - current run (regression gate baseline, per-platform)
///   <platform>_<date>_<time>/  - dated archive per run (max 20 per platform)
///
/// Android: <app-docs>/extraction_reports/
///   (pull to desktop via adb commands above)
///
/// ## How To Reset Baseline
/// Option A: Delete reports/latest-<platform>/ folder. Next run establishes new baseline.
/// Option B: Use --dart-define=RESET_BASELINE=true (archives current baseline first).
```

---

## Cleanup Plan

### Phase Order

1. **Build `pipeline_comparator.dart`** (library in `test/.../golden/`) — consolidated comparison logic, no normalization, 3 modes (report/CLI/cross-device), regression gate, schema version checking, ground truth loading with configurable path. Est. ~600-800 lines.
2. **Build `tools/pipeline_comparator.dart`** (CLI entry point) — imports library above, parses args (`--ground-truth`, `--cross-device`), runs comparison, prints output. Est. ~80-120 lines.
3. **Build `report_generator.dart`** — takes raw stage data + `PipelineResult`, produces JSON trace (with schema_version, version metadata, per-stage timing, performance metrics) + MD scorecard. Includes `collectVersionMetadata()` helper. Est. ~500-700 lines.
4. **Build `springfield_report_test.dart`** — integration test tying it all together. Multi-attempt handling, platform detection, Android file I/O, `NO_GATE`/`RESET_BASELINE` modes, archive retention enforcement. Est. ~400-500 lines.
5. **Update `.gitignore`** — add `test/features/pdf/extraction/reports/`
6. **Run new system on Windows** — verify outputs are correct, scorecard readable, timing data captured
7. **Run new system on S25** — verify cross-platform, check device folder naming, Android file I/O
8. **Verification phase** — run old tests side-by-side with new system, confirm new system catches everything old tests caught (and more)
9. **Delete old files** — remove 10 files (~7,600 lines) only after verification passes
10. **Update references** — CLAUDE.md, _state.md, defect files, `full_pipeline_integration_test.dart` import update, any imports pointing to deleted files

### Approaches Rejected
- **Hardcoded threshold assertions**: Rejected because thresholds go stale and require manual updating. Regression gate auto-tightens instead.
- **Normalization in comparison layer**: Rejected because it masks real pipeline issues. If LSUM vs LS is a problem, fix it in the pipeline (Stage 5), not the test.
- **Fixture-based testing**: Rejected as primary approach. Fixtures are frozen snapshots that skip silently when empty. Live pipeline testing produces real, current data every run.
- **Multiple comparison implementations**: Rejected because 3 tools with inconsistent behavior caused false results (26 unit mismatches hidden by Python normalization).
- **Keeping old tests alongside new**: Old tests deleted after verification to avoid maintaining dead code.
- **Single `latest/` baseline**: Rejected because different platforms produce legitimately different outputs (OCR engine versions, rendering differences). Each platform needs its own regression baseline.
- **Arbitrary checksum tolerance**: Rejected $100 in favor of mathematically derived $1.31 ($0.01 x 131 items).

---

## Adversarial Review — Addressed Items

All items from the code-review adversarial review have been incorporated into this spec.

### MUST-FIX (6/6 addressed)

| # | Item | Resolution | Spec Section |
|---|------|------------|--------------|
| 1 | Define exact stage list | Added definitive "Stage Classification Table" with all 27 StageNames constants mapped to data-transforming (22), metadata-only (5), dead (1), and aggregate (1) categories | Stage Classification Table |
| 2 | Platform-scope regression baseline | Replaced `latest/` with `latest-<platform>/` (`latest-windows/`, `latest-sm-s938u/`, etc.). Cross-platform comparison is CLI-only, not part of regression gate. | Output Structure, Regression Gate Logic |
| 3 | Handle multi-attempt pipeline runs | Documented best-attempt selection by item count, matching `generate_golden_fixtures_test.dart` lines 98-115. Only best attempt's stages captured. Attempt metadata in report. | How It Works, Key Design Decisions |
| 4 | Address Android file I/O | Added "Android File I/O" section: writes to app-accessible storage on-device, `adb pull` commands in doc header, ground truth bundling options | Android File I/O, Test Documentation Header |
| 5 | Fix CLI invocation | CLI entry point moved to `tools/pipeline_comparator.dart`. Library code stays in `test/.../golden/`. Consistent with existing `tools/gt_trace.dart`. | New Files table, Phase Order |
| 6 | Add missing files to deletion list | Added `golden_file_matcher_test.dart`, `golden/README.md`, and `generate_golden_fixtures_test.dart` to deletion list. Added note about `full_pipeline_integration_test.dart` import update. | Files To Delete |

### SHOULD-CONSIDER (5/5 adopted)

| # | Item | Resolution | Spec Section |
|---|------|------------|--------------|
| 7 | Baseline reset mechanism | Added `RESET_BASELINE` dart-define: archives current baseline, establishes new one, skips gate | `--reset-baseline` Mode |
| 8 | Derive checksum tolerance mathematically | Replaced $100 with $1.31 ($0.01 x 131 items). Added derivation note. | Regression Tolerances |
| 9 | Cap report archive growth | Added retention policy: max 20 dated reports per platform, oldest auto-deleted | Output Structure, How It Works step 7 |
| 10 | Gitignore reports directory | Added `test/features/pdf/extraction/reports/` to gitignore plan. Only ground truth file is git-tracked. | Output Structure (Gitignore note), Phase Order step 5 |
| 12 | State relationship with generate_golden_fixtures_test.dart | Explicitly documented that `springfield_report_test.dart` replaces the fixture generator. Added `generate_golden_fixtures_test.dart` to deletion list. | Key Design Decisions, Files To Delete |

### NICE-TO-HAVE (3/3 adopted)

| # | Item | Resolution | Spec Section |
|---|------|------------|--------------|
| 13 | Add --no-gate flag | Added `NO_GATE` dart-define for exploratory runs. Report still generated, assertions skipped. | `--no-gate` Mode |
| 14 | Schema version + version tracking | Added `schema_version` field and `versions` object with tesseract/flutter/dart/pdfrx/flusseract. Documented retrieval methods. | JSON Trace schema, note on version retrieval |
| 15 | Per-stage timing in metrics | Added `elapsed_ms` to every stage in `stage_metrics`. Pipeline already captures `StageReport.elapsed` per stage. | JSON Trace schema, MD Scorecard |

### ADDITIONAL (4/4 addressed)

| # | Item | Resolution | Spec Section |
|---|------|------------|--------------|
| A1 | Add more performance metrics | Added `performance` top-level section with: stage breakdown percentages, CPU-intensive stage identification, total OCR calls, rendered/preprocessed image sizes (bytes), `ocr_calls_per_page` and `image_sizes_bytes` in per-stage metrics. Peak memory not available in Dart without custom native bindings — omitted with rationale. | JSON Trace schema (`performance` section, per-stage `image_sizes_bytes`, `ocr_calls_per_page`) |
| A2 | Scope M&P test | Added one-line note that `mp_stage_trace_diagnostic_test.dart` will be migrated in a future phase | Success Criteria |
| A3 | Estimate per-file line counts | Added Est. Lines column to New Files table and line counts in Phase Order. Added guardrail: decompose if any file exceeds ~1,500 lines. | New Files table, Phase Order |
| A4 | Ground truth loading | Documented configurable `--ground-truth` path parameter for CLI mode. Default path: `test/features/pdf/extraction/fixtures/springfield_ground_truth_items.json` | Ground Truth Loading, Test Documentation Header |

### Performance Metrics — Design Notes

**What's included** (available from existing pipeline infrastructure):
- `elapsed_ms` per stage — from `StageReport.elapsed` (every stage already has a `Stopwatch`)
- `image_sizes_bytes` at render/preprocess stages — from `RenderedPage` and `PreprocessedPage` byte arrays
- `ocr_calls_per_page` — derivable from `textRecognizer` stage output (`per_page_counts`)
- Total OCR calls, total image bytes — aggregated from per-stage data
- CPU-intensive stage identification — stages where `elapsed_ms` > 5% of total pipeline time
- Stage breakdown percentages — computed from per-stage `elapsed_ms` / total

**What's NOT included** (and why):
- Peak memory per stage — Dart's `ProcessInfo.currentRss` gives process-level RSS, not per-stage deltas. Reliable per-stage memory measurement requires native profiling tools (Android Profiler, Windows Performance Analyzer). Adding it would require custom native bindings with platform-specific implementations and would likely be inaccurate due to GC timing. If memory profiling becomes important, use platform-native tools and correlate with the per-stage timing data from reports.

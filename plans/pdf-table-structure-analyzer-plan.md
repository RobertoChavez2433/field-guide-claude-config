# PDF Table Structure Analyzer Plan

**Created**: 2026-02-05  
**Goal**: Replace ad‑hoc header/boilerplate heuristics with a coherent, **deterministic** algorithm that robustly finds table regions and columns even with heavy legal text on page 1, while staying **offline and non‑AI**.

## Why This Plan Exists
Current logs show the table region can be hijacked by legal headings (e.g., “3.01 Unit Price Bids”) and that header elements are filtered out when startY is wrong. The existing code contains many heuristic checks, but they are not coordinated into a consistent decision process. We need an explicit **Table Structure Analyzer** that scores rows and chooses the most likely header+data sequence across pages. This should be paired with deterministic preprocessing and post‑processing steps (noise/deskew/scale + cleaning/normalization) to reduce OCR artifacts before analysis.

This plan is scoped to be implemented as a series of PR‑sized phases with observable, testable outcomes and a safe fallback to current behavior. Emphasis is on **deterministic decision rules** and **traceable scoring**, not heuristic drift.

---

## Design Summary (Algorithm)
1. **Preprocessing** (deterministic, offline): noise removal, deskew/orientation fix, binarization, and DPI/scale normalization before OCR.  
2. **Page segmentation**: identify candidate content bands and suppress header/footer bands using repetition + density rules.  
3. **Row clustering** from OCR elements (adaptive Y‑clustering) → per‑row feature vectors.  
4. **Deterministic row classification** → `rowType` + `rowScore` using fixed rules and weighted evidence.  
5. **Sequence optimization** (DP) to select the most likely contiguous header→data region across pages.  
6. **Deterministic header selection**: enforce header token rules + column‑count rules + alignment with data rows.  
7. **Column model** derived from data‑row alignment (x‑clusters + anchors) → stable column priors.  
8. **Row boundaries** output → pass into `CellExtractor` instead of generic Y‑cluster.  
9. **Row labels** output → pass to `TableRowParser` to skip boilerplate deterministically.  
10. **Post‑processing**: cleaning, normalization, structured output (JSON/CSV), with strict offline rules.

**Constraints**
- Offline only (no LLMs, no cloud services, no transformer models like TATR/Nougat).
- Deterministic algorithmic rules only (no template matching for now).

---

## Deterministic Logic System (What “Robust” Means Here)
**Row Classification Rules (deterministic)**
- `HEADER` if: at least **3** header tokens (ITEM/NO/DESCRIPTION/UNIT/QTY/PRICE/AMOUNT) **and** row is short/compact **and** column‑count ≥ 4.  
- `DATA` if: item‑number pattern matches (strict digits or dotted) **and** ≥ 2 numeric columns **and** row width coverage ≥ threshold.  
- `BOILERPLATE` if: legal/contract patterns (ARTICLE/SECTION/BID FORM/OWNER/BIDDER) **or** long paragraph ratio **or** repeated across pages.  
- `UNKNOWN` otherwise.
- Header token normalization: uppercase, strip punctuation, and include synonyms (EST QTY/EST. QUANTITY/BID AMOUNT/UNIT PRICE).

**Header Selection Rules (deterministic)**
- Select highest‑scoring header row **above** the first strong data row within the same block.  
- Reject header candidates that are in header/footer bands or match boilerplate patterns.  
- Require alignment with data columns: header token x‑positions must align with data column peaks (within tolerance).  
- Allow multi‑row headers: merge adjacent rows within a small y‑gap and recompute token coverage/alignment.

**Table Region Rules (deterministic)**
- A table block is a contiguous run of rows where `DATA` score stays above threshold with allowed small gaps.  
- Prefer blocks with monotonic item‑number progression and consistent row spacing.  
- Expand upward to include the nearest valid `HEADER` row; if none, allow an inferred header from column priors.

**Column Model Rules (deterministic)**
- Anchor columns using item‑number column (leftmost) and right‑most currency/amount column.  
- Compute x‑clusters from data tokens; enforce monotonic increasing column boundaries.  
- Enforce stable column count across rows; down‑weight rows with misaligned tokens.

**Row Boundary Rules (deterministic)**
- If gridlines detected (Hough + line clustering), use them as hard boundaries.  
- Else use y‑gaps + baseline alignment + row‑height consistency.

---

## Phase 0: Observability + Scaffolding (PR 0)
**Goal**: Add diagnostics and stub analyzer with no behavior change.

**Changes**
- Add `TableStructureAnalysis` model in `lib/features/pdf/services/table_extraction/models/`.
- Add `TableStructureAnalyzer` class that returns a minimal analysis (empty scores, no overrides).
- Extend `TableExtractionDiagnostics` to include:
  - `analysisUsed` (bool)
  - `rowScoreSummary` (counts of header/data/boilerplate by score bucket)
- Add DebugLogger.pdf logs:
  - “Structure analysis started/complete”
  - Summary of candidate header rows + scores
  - Preprocessing summary: deskew/binarize/scale parameters used
  - Header selection reasoning (why chosen / rejected)
  - Table block summary (start/end rows + score)

**Acceptance**
- No behavior change: extractor still uses existing `TableLocator` path.
- New logs appear in `pdf_import.log` when diagnostics are enabled.

---

## Phase 1: Row Feature Extraction + Scoring (PR 1)
**Goal**: Compute row features and assign header/data/boilerplate scores.

**Features**
- Keyword hits (item/desc/unit/qty/amount/price)
- Token count, digit ratio, currency ratio
- Row length, average token width
- Legal/contract patterns (ARTICLE, SECTION, BID FORM, etc.)
- Table‑likeness: multiple columns + mixed numeric/text
- OCR confidence stats (mean/min across row)
- Preprocessing flags (deskew/binarize/scale) to correlate OCR quality to preprocessing
- Row spacing consistency (delta‑Y stability)
- Column alignment score (distance to column peaks)
- Repetition score (row text repeats across pages)

**Changes**
- Implement `RowFeatures` and `RowScore` structs.
- Add row scoring weights (configurable constants).
- Unit tests for scoring on Springfield‑style row samples.

**Acceptance**
- Analyzer identifies legal rows as boilerplate with high confidence.
- Analyzer identifies the true table header near page bottom with higher header score than legal headings.
- When preprocessing is disabled or weak, logs explicitly show it so regressions are visible.

---

## Phase 2: Sequence Optimization (PR 2)
**Goal**: Select the most likely header→data sequence across pages.

**Algorithm**
- DP over ordered rows:
  - States: header, data, boilerplate, unknown
  - Transition penalties: boilerplate after data, data before header, large gaps
  - Rewards: consecutive data rows, stable item‑number progression
  - Constraints: header must precede data within block; boilerplate may not appear inside the chosen block

**Changes**
- Implement `RowSequenceOptimizer`.
- Output `tableRegion` + selected header rows + candidate data region.
- Add tests with synthetic rows that include boilerplate above and below the table.
- Add deterministic header selector with tie‑breakers (highest header score with best column alignment; reject header/footer band; reject paragraph‑like rows).
- Add multi‑row header assembly (merge adjacent header candidates within small y‑gap; recompute token/column alignment).

**Acceptance**
- Table region is selected correctly even if the highest keyword density row is not the true header.
- Cross‑page table continuity is preserved.
- Header selection is stable and deterministic on repeated runs.

---

## Phase 3: Column Priors + Row Boundaries (PR 3)
**Goal**: Use analysis output to stabilize column detection and row extraction.

**Changes**
- Derive column priors from data‑row alignment (x‑centers clustering).
- Add column anchors (item‑number left boundary + right‑most amount boundary).
- Add column‑count sanity checks and reject rows that violate column ordering.
- Provide `rowBoundaries` per page from analysis.
- Feed column priors into `ColumnDetector` (as a prior/override when header detection is weak).
- Pass `rowBoundaries` into `CellExtractor` to reduce row split/merge errors.

**Acceptance**
- Page‑1 column detection improves even without gridlines.
- Re‑OCR is triggered less often due to improved row boundaries.
- Structured output uses normalized units/currency consistently.
- Column model is stable across pages (same ordering and count).

---

## Phase 4: Parser Integration (PR 4)
**Goal**: Use row labels to skip boilerplate and handle continuations more deterministically.

**Changes**
- Add optional `rowType`/`rowScore` to `TableRow` or wrap rows in a new `AnalyzedTableRow`.
- Modify `TableRowParser` to:
  - Skip boilerplate rows explicitly.
  - Handle continuation rows using analyzer hints.
  - Enforce item‑number monotonicity (flag and log breaks instead of merging wrongly).
- Add tests for:
  - “NO” / “ITEM NO.” header rows
  - Legal text rows correctly skipped.
  - Header‑only row followed by data rows (no boilerplate pollution)

**Acceptance**
- No legal text rows are parsed as items.
- Continuation rows merge consistently when labeled.

---

## Phase 5: Rollout + Regression Guard (PR 5)
**Goal**: Safely enable the analyzer and lock in regression checks.

**Changes**
- Add a feature flag: `TableStructureAnalyzer` can run in `advisory` or `active` mode.
- In `active`, the analyzer output overrides `TableLocator` and header row selection.
- Add Springfield regression guard to integration tests if not already present.
- Record extraction metrics in logs: items count, valid item ratio, column confidence.

**Acceptance**
- Springfield extraction ≥125/131 items on fixtures.
- Analyzer logs show selected header rows and table region.
- Preprocessing settings are recorded in logs for each run.

---

## Phase 6: Stabilization + Cleanup (PR 6)
**Goal**: Remove obsolete heuristics and consolidate logic.

**Changes**
- Deprecate redundant `TableLocator` heuristics when analyzer is active.
- Keep fallback path for unsupported PDFs.
- Update docs and `_state.md`.

**Acceptance**
- Test suite passes.
- Logs show stable results across multiple runs.

---

## Risks & Mitigations
- **Risk**: Regression on non‑Springfield PDFs  
  **Mitigation**: advisory mode first, keep fallback path.
- **Risk**: Performance overhead  
  **Mitigation**: cache row features, short‑circuit when header confidence high.
- **Risk**: Wrong row boundaries on grid‑heavy pages  
  **Mitigation**: prefer image‑derived row boundaries when line detection is strong.
- **Risk**: Over‑reliance on AI‑style components  
  **Mitigation**: enforce offline constraints; deterministic rules only.
- **Risk**: Deterministic thresholds too strict → missed tables  
  **Mitigation**: expose thresholds in config, log scores, and keep advisory fallback.

---

## Success Definition
1. Springfield extraction ≥95% (125+/131) consistently.
2. Legal text does not affect table start selection.
3. Column detection confidence stable (>0.75).
4. Build logs prove analyzer path used and record row score summaries.
5. Header detection is stable (including multi‑row headers) across repeated runs.

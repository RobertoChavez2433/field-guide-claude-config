# PDF Grid And OCR Hardening Spec

Date: 2026-03-13
Author: Codex
Status: Approved for planning

## Overview

This effort will fix Springfield and harden the general tabular OCR pipeline by addressing two linked upstream failures:

- `Grid cleanup failure`: the surgical grid-removal path still leaves enough border/grid residue in some crops to confuse OCR, even when the page looks visually clean.
- `Retry-policy failure`: OCR retries are not defined consistently by column, and column `0` was omitted entirely from structured recovery.

The design will keep the current pixel-coordinate, surgical removal model. We will not go back to broad morphology-based clipping. Instead, we will tune the surgical remover and inpainting so the output better satisfies OCR assumptions while preserving text. In parallel, we will replace the current partial retry rules with explicit per-column OCR policies so every column has a defined first-pass strategy, failure trigger, and retry behavior.

### Target outcomes

- recover substantially more missing and corrupted items across the full document, not just the known page 5 cluster
- restore correct row anchoring so logical item boundaries survive OCR and classification
- reduce row collapse into `priceContinuation` and other false continuation paths
- reduce residual grid and border artifacts in OCR crops without reintroducing text clipping
- improve field accuracy across item number, description, unit, quantity, unit price, and bid amount
- move the Springfield extraction materially closer to full-document recovery, with the goal of approaching 100% rather than only fixing a small subset
- preserve generality across table PDFs, not just Springfield
- create a path to lower OCR runtime by making retries more selective and policy-driven

### Non-goals

- replacing Tesseract
- redesigning the whole extraction architecture
- broad document-specific heuristics tied only to Springfield

## Design

### 1. Grid removal and inpainting

Keep the current surgical, pixel-coordinate removal model, but change how it is validated and tuned.

Planned changes:

- separate `line detection accuracy` from `OCR cleanliness`
- add diagnostics for residual line energy inside each OCR crop, not just page-level mask overlap or `excess mask pixels`
- tune removal width and inpaint radius by line orientation and detected line thickness instead of relying on a single broad removal behavior
- explicitly measure post-cleanup residue near crop edges and line centers, especially for narrow single-token cells like item numbers
- preserve text-first behavior: if a tuning choice risks eroding glyph strokes, leave some line residue and rely on downstream OCR policy rather than removing more aggressively
- add a crop-level comparison diagnostic containing:
  - raw crop
  - cleaned crop
  - OCR-prepared crop
  - optional edge/residue overlay
- tune for `minimal residual border signal` rather than `maximal pixel removal`

Likely grid cleanup fixes:

- reduce residual horizontal and vertical border fragments at crop edges
- ensure inpainting smooths line remnants without softening nearby digits
- avoid over-reliance on visual page cleanliness as a proxy for OCR cleanliness

### 2. Column-specific OCR policy

Replace the current implicit retry logic with an explicit policy table per column.

Policy shape per column:

- first-pass OCR config
- failure triggers
- retry config(s)
- acceptance rules
- optional normalization hints

Initial policy direction:

- Column `0` item number:
  - first pass: single-token oriented
  - retry on blank, non-numeric, low-confidence, or corrupted-anchor output
  - retry whitelist: digits plus decimal if needed
  - accept only text matching item-number structure
- Column `1` description:
  - first pass: general text
  - retry only when output is blank or obviously corrupted
  - avoid expensive retries by default
- Column `2` unit:
  - structured short-token policy
  - retry on blank or malformed token
- Columns `3`, `4`, `5` quantity, unit price, bid amount:
  - keep structured numeric retries
  - extend trigger set to include blank first-pass results
  - normalize acceptance around numeric or currency expectations

Continuity rules:

- every column must have an explicit policy, even if that policy is `single pass only`
- no column may be omitted by implicit index lists
- retry decisions must be policy-owned, not scattered through ad hoc conditions

### 3. Retry trigger redesign

Current gap:

- retries only fire for columns `3,4,5`
- blank first-pass results do not retry
- column `0` is excluded entirely

Planned trigger categories:

- blank result
- low-confidence result
- malformed result for that column’s expected structure
- anchor-corrupt result for item-number cells
- conflicting result when row structure strongly suggests the cell should contain a valid token

Retry behavior:

- keep retries conditional
- allow multiple retry profiles only where justified
- stop once a result satisfies the column acceptance rule
- record why a retry happened and which policy won

### 4. Row-anchor safeguards

Even with better OCR, classification should not collapse rows too easily when the left anchor is weak.

Planned safeguards:

- if a row has strong description, unit, quantity, and price structure consistent with a new item row, do not classify it as continuation solely because column `0` is blank or malformed
- allow row classification to use structured-cell evidence as a secondary anchor
- mark anchor-missing rows for targeted OCR recovery before irreversible continuation merging when feasible
- reduce false `priceContinuation` labels caused by item-number loss

This is a safety net, not the primary fix. The primary fix remains better OCR recovery in structured columns.

### 5. Runtime strategy

Accuracy stays first, but this design should also improve OCR cost control.

Low-risk runtime improvements built into this approach:

- fewer accidental retries by using explicit column acceptance rules
- retries only on policy-relevant failure signatures
- no unnecessary retries for strong first-pass description cells
- better diagnostics to identify which retry profiles are wasting time

Later optimization path:

- collect retry-hit-rate metrics per column
- remove retry profiles that rarely win
- consider skipping expensive second-pass OCR where grid cleanup quality is already high

## Validation

### Testing strategy

- add Springfield-focused regression cases for the known failure clusters and for full-document totals
- add crop-level tests for structured columns:
  - column `0` blank first-pass should trigger retry
  - column `0` malformed alpha output should trigger retry
  - numeric columns blank first-pass should trigger retry
  - description column should not over-retry on good text
- add acceptance tests for per-column policy selection so every column has an explicit policy and none can be silently skipped
- add row-classification tests proving a row with strong structured-cell evidence is not demoted to continuation solely because the item anchor is missing
- add grid-cleanup diagnostics tests that assert crop-level residue metrics are emitted and bounded for representative rows
- keep the existing Springfield report run as the main end-to-end gate, but expand what we inspect from it

### Success metrics

Primary:

- materially increase `items_extracted` and `match_rate` on Springfield
- materially reduce missing-item count across the document
- materially reduce false continuation merges
- improve field accuracy for item number, quantity, unit price, and bid amount

Diagnostic:

- reduce malformed item-number anchors such as `ne`, `kd`, `Kd`
- reduce structured-column blank outputs after first-pass plus retry
- reduce residual line artifacts in saved OCR crop diagnostics

Safety:

- no regression back toward broad text clipping
- no significant rise in orphan rows or orphan elements
- no major drop in description accuracy while improving numeric recovery

### Implementation order

1. Introduce explicit per-column OCR policy objects and wire all columns into policy selection.
2. Extend retry triggers to include blank and malformed first-pass results for structured columns.
3. Add column `0` item-number retry path with structured acceptance rules.
4. Add instrumentation so report output captures retry reason, retry count, and winning policy by column.
5. Tune surgical grid removal and inpainting using crop-level diagnostics rather than page-level mask metrics alone.
6. Add row-anchor safeguards to prevent false continuation collapse when other cells strongly indicate a new item row.
7. Re-run Springfield report and diagnostics, then tighten thresholds using evidence rather than intuition.

### Risks

- over-tuning grid cleanup could reintroduce text erosion
- over-eager retries could explode runtime if acceptance rules are weak
- row-anchor safeguards could create duplicate rows if they are allowed to override too much structure
- column policies can drift into hardcoded document heuristics if not kept structure-based

### Review focus

- are the retry triggers specific enough to improve accuracy without multiplying OCR work
- are grid-cleanup diagnostics measuring the right thing, not just visually pretty output
- are row safeguards limited enough to avoid papering over OCR failures with parser heuristics
- does every structured column now have continuity from first pass to retry to acceptance

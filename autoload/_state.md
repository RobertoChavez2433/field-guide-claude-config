# Session State

**Last Updated**: 2026-03-15 | **Session**: 577

## Current Phase
- **Phase**: OCR Accuracy — 131/131 items, 2 description blockers remain (38, 130)
- **Status**: Items 100%. Checksum $0. Description 98.5% (2 failures: items 38, 130). All numerics 100%.

## HOT CONTEXT - Resume Here

### What Was Done This Session (577)

1. **Systematic debug** of remaining 3 failures (items 38, 62, 130) using systematic-debugging skill
2. **Corrected wrong root cause for item 62** — prior session claimed "Tesseract drops 6 from 62, dedup kills it". Actually TWO failure modes exist:
   - Mode A: Tesseract reads "62" correctly, but pipe artifact in amount cell (`| $1,752.40`) causes `_normalizeCorruptedSymbol` to produce `$$1,752.40` (double dollar sign) which fails parsing → bid_amount=null
   - Mode B: Tesseract non-deterministically reads "2" instead of "62" → dedup groups with real item 2 → item 62 dropped
3. **Fixed both failure modes**:
   - Currency fix: `currency_rules.dart` — don't prepend `$` when remaining text already starts with `$`
   - Sequential gap-fill: `item_deduplicator.dart` — before standard dedup, check if a duplicate item number fills a gap between neighbors (e.g., 61, "2", 63 → rename "2" to 62)
4. **Verified**: Springfield 131/131 items, $0 checksum, all numerics 100%
5. **Committed all changes** from sessions 575-577 as 5 logical commits

### Verification Results

| Metric | Previous (S576) | Current (S577) | Delta |
|--------|-----------------|----------------|-------|
| Items | 130/131 | 131/131 | +1 (item 62 recovered) |
| Checksum | $1,752.40 | $0 | Fixed |
| Description | 98.5% | 98.5% | Same (items 38, 130 remain) |
| Unit | 100% | 100% | Same |
| Qty/Price/Amount | 100% | 100% | Same |

### Remaining 2 Failures

#### BLOCKER-34: Item 38 — Superscript `th` → `"` (Tesseract limitation)
- PDF renders "20th" with `th` as superscript ordinal suffix
- Tesseract reads superscript as `"` at confidence 0.87
- **Fix**: Ordinal suffix recovery rule in `_descriptionArtifactRules` — convert `\d{1,3}"` to ordinal when NOT in a measurement context

#### BLOCKER-36: Item 130 — Whitewash destroys `y` descender
- Whitewash at bleed=2 overwrites descender pixels in wrapped text rows
- textProtection mask won't work (descenders overlap gridMask → classified as grid, not text)
- **Fix**: Threshold-based whitewash — only whitewash pixels brighter than ~160 (bleed artifacts are light, text is dark)

### NOT Done — Carry to Next Session

1. **Verify on Android device** — confirm 131/131 on physical device
2. **Fix item 130** — threshold-based whitewash
3. **Fix item 38** — ordinal suffix recovery rule

## Blockers

### BLOCKER-34: Item 38 — Superscript `th` → `"` (Tesseract limitation)
**Status**: OPEN — Ordinal suffix recovery rule needed in post-processing.

### BLOCKER-35: Item 62 — Currency parsing + OCR non-determinism
**Status**: FIXED (S577) — Two fixes: currency double-dollar bug + sequential gap-fill dedup.

### BLOCKER-36: Item 130 — Whitewash destroys `y` descender
**Status**: OPEN — Threshold-based whitewash needed (skip dark text pixels).

### BLOCKER-28: SQLite Encryption (sqlcipher)
**Status**: OPEN — tracked separately.

### BLOCKER-22: Location Field Stuck "Loading"
**Status**: OPEN — HIGH PRIORITY

### BLOCKER-23: Flutter Keys Not Propagating to Android resource-id
**Status**: OPEN — MEDIUM

## Recent Sessions

### Session 577 (2026-03-15)
**Work**: Systematic debug of items 38, 62, 130. Corrected wrong root cause for item 62 (NOT a dedup issue — currency parsing bug + OCR non-determinism). Fixed both: currency double-dollar bug in `_normalizeCorruptedSymbol`, sequential gap-fill in `ItemDeduplicator.deduplicate`. Springfield: 131/131, $0 checksum. Committed 5 logical commits.
**Decisions**: Item 62 had TWO failure modes (Tesseract non-determinism). textProtection won't work for item 130 (descenders classified as grid). Threshold-based whitewash is the correct approach.
**Next**: Verify on Android device. Fix items 130 (threshold whitewash) and 38 (ordinal suffix recovery).

### Session 576 (2026-03-15)
**Work**: Deep systematic debug of all 6 OCR failures. Fixed 3 (items 22, 26, 97). Deep-traced remaining 3 with individual agents. Springfield: 130/131, desc 98.5%, numerics 100%. Tried whitewash bleed reduction — regressed, reverted.
**Decisions**: Pipe stripping must run AFTER rules. `_kWhitewashBleed=2` is essential (bleed=1 causes 126/131 regression). Item 130 needs text-aware whitewash. Item 62 needs sequential dedup or PSM 13. Item 38 needs per-token retry or PDF text layer.
**Next**: Fix item 62 (sequential dedup), fix item 130 (text-aware whitewash), fix item 38 (per-token retry). Commit.

### Session 575 (2026-03-15)
**Work**: Implemented OCR accuracy fixes plan (6 fixes across 4 phases). Springfield: 130/131, desc 96.2%, unit/qty/price/amount 100%. 4 items fixed (36, 37, 52, 106). 2 regressions from 900 DPI upscale (items 22, 97). Cell crop diagnostic confirms all crops pristine — failures are Tesseract misreads.
**Decisions**: 900 DPI description upscale is counterproductive — must revert to 600 max. Need deep debug session for remaining 6 failures.
**Next**: Revert 900 DPI, add pipe to roman numeral regex, deep debug all remaining failures, commit.

### Session 574 (2026-03-15)
**Work**: Implemented post-inpaint whitewash (Option B) in grid_line_remover. Springfield: 131/131 items, $0 checksum (was $1.39M), numeric 100%. Description 90% — investigated 13 failures (4 categories), wrote OCR normalization plan (5 rules across 2 files).
**Decisions**: Whitewash at expandedThickness+4px bleed. Text protection confirmed already disabled. Generic algorithmic rules only (no PDF-specific heuristics). 2 items unfixable (OCR limitations).
**Next**: `/implement` OCR normalization plan. Commit all changes.

### Session 573 (2026-03-15)
**Work**: Phase 6 integration verification — Springfield REGRESSED ($1.39M checksum distance, -63 elements). Root-caused via systematic-debugging: TELEA creates ~2px bleed artifacts beyond mask boundary. Orange diff bands confirmed as diagnostic artifact (hardcoded fringeMargin). Generated 1644 cell crop PNGs. Three-agent investigation: Option B (post-inpaint whitewash in grid_line_remover) is the fix.
**Decisions**: Option A (+2px safety) too marginal. Option C (mask expansion) already working. Option B eliminates TELEA bleed at source.
**Next**: Investigate Option B with 2 agents, implement, re-run Springfield.

## Active Plans

### OCR Accuracy Fixes — COMPLETE (Session 576)
- **Plan**: `.claude/plans/2026-03-15-ocr-accuracy-fixes.md`
- **Status**: All code fixes applied. Items 22, 26, 97 fixed. Items 38, 62, 130 remain as blockers.

### OCR Normalization Rules — IMPLEMENTED (Session 575)
- **Plan**: `.claude/plans/2026-03-15-ocr-normalization-rules.md`
- **Status**: All 3 phases complete.

### Fringe-Edge Crop Boundaries — FIXED (Session 574)
- **Plan**: `.claude/plans/2026-03-14-fringe-edge-crop-boundaries.md`
- **Status**: Complete. Whitewash applied. Springfield: $0 checksum, 131/131 items.

### Debug Framework — IMPLEMENTED (Session 571)
- **Spec**: `.claude/specs/2026-03-14-debug-framework-spec.md`
- **Plan**: `.claude/plans/2026-03-14-debug-framework.md`
- **Status**: All 7 phases complete. 19 files modified. 33 Logger tests pass.

### Sync Engine Hardening — IMPLEMENTED + DEPLOYED (Session 563)
- **Status**: All 9 phases complete. 29 files modified. 476 sync tests pass. Supabase migrations deployed.

### UI Refactor — PLAN REVIEWED + HARDENED (Session 512)
- **Plan**: `.claude/plans/2026-03-06-ui-refactor-comprehensive.md`
- **Status**: 12 phases + Phase 3.5. Reviewed by 3 agents.

## Reference
- **OCR Accuracy Fixes Plan**: `.claude/plans/2026-03-15-ocr-accuracy-fixes.md`
- **OCR Normalization Plan**: `.claude/plans/2026-03-15-ocr-normalization-rules.md`
- **Debug Framework Spec**: `.claude/specs/2026-03-14-debug-framework-spec.md`
- **Debug Framework Plan**: `.claude/plans/2026-03-14-debug-framework.md`
- **Sync Hardening Plan**: `.claude/plans/2026-03-13-sync-engine-hardening.md`
- **Pipeline Report Test**: `integration_test/springfield_report_test.dart`
- **Latest Scorecard**: `test/features/pdf/extraction/reports/latest-windows/scorecard.md`
- **Cell Crop PNGs**: `test/features/pdf/extraction/diagnostics/crops/`
- **Defects**: `.claude/defects/_defects-pdf.md`, `_defects-sync.md`, `_defects-projects.md`

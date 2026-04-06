# Session State

**Last Updated**: 2026-04-06 | **Session**: 743

## Current Phase
- **Phase**: OCR runtime optimization checkpoint on `sync-engine-refactor`
- **Status**: Persistent `2`-worker OCR pool is now green on S25 and beats same-build serial. Sub-`60s` remains open.

## HOT CONTEXT - Resume Here

### What Was Done This Session (743)

1. **OCR runtime / worker execution refactor**:
   - Re-grounded the OCR strategy in official Tesseract and Dart/Flutter isolate guidance
   - Confirmed the correct endpoint shape is bounded OCR-only workers with isolated Tesseract instances, `OMP_THREAD_LIMIT=1`, and serial OCR inside each worker
   - Saved the checkpoint documents in `.codex/plans/`, including a consolidated handoff doc

2. **Root-caused the earlier worker hang correctly**:
   - Found that `packages/flusseract` used process-global stdout/stderr capture around native OCR calls
   - Confirmed that this was unsafe for concurrent OCR workers inside one process
   - Disabled that stream-capture path on Android and Windows
   - Logged the defect in `.claude/defects/_defects-pdf.md`

3. **Replaced short-lived OCR batches with a persistent worker pool**:
   - `TextRecognizerV2` now runs through the page-recognition strategy seam
   - Worker requests/results use isolate-safe DTOs and `TransferableTypedData`
   - Implemented long-lived worker isolates with startup handshake, request IDs, response correlation, explicit shutdown, and one private Tesseract engine per worker
   - Dynamic page scheduling now sends the next page to the next available worker instead of fixed coarse chunk groups

4. **Measured same-build S25 results with debug-server artifacts**:
   - Persistent `2`-worker pool: `131/131`, exact checksum, no bogus rows, about `90s` total, `70831 ms` text recognition
   - Same-build serial control: `131/131`, exact checksum, no bogus rows, about `98s` total, `77655 ms` text recognition
   - Persistent `3`-worker pool: `131/131`, exact checksum, no bogus rows, about `110s` total, `83555 ms` text recognition
   - Conclusion: `2` workers is the correct cap on the S25 and the persistent pool is the first worker path that beats same-build serial

### What Needs to Happen Next

1. **OCR resume point**: Decide whether the next OCR phase is:
   - stronger raw-grid / visual regression enforcement, or
   - pure runtime reduction below the new `~90s` pooled result
2. **OCR optimization**: If resumed, keep the persistent `2`-worker pool as the active runtime candidate and work below that boundary rather than redesigning workers again.
3. **Design system overhaul**: Existing plan remains review-complete and ready for `/implement` when OCR work is parked.

### User Preferences (Critical)
- **Fresh test projects only**: NEVER use existing projects during test runs
- **CI-first testing**: NEVER include `flutter test` in plans or quality gates
- **Always check sync logs** after every sync during test runs
- **No band-aid fixes**: Root-cause only
- **Verify before editing**: Understand root cause first
- **All findings must be fixed**: ALL review findings, not just blocking ones
- **No // ignore to suppress lint**: Fix the root cause

## Blockers

### BLOCKER-34: Item 38 — Superscript `th` → `"` (Tesseract limitation) (#91)
**Status**: OPEN (parked, cosmetic)

### BLOCKER-36: Item 130 — Whitewash destroys `y` descender (#92)
**Status**: OPEN (parked, cosmetic)

### BLOCKER-28: SQLite Encryption (sqlcipher) (#89)
**Status**: OPEN — production readiness blocker

## Recent Sessions

### Session 743 (2026-04-06, Codex)
**Work**: Completed OCR runtime worker refactor. Fixed concurrent flusseract stream capture bug, replaced short-lived page-worker batches with a persistent isolate pool, and benchmarked pooled vs serial Springfield runs on the S25.
**Decisions**: The correct OCR execution model is now validated: persistent OCR-only workers, isolated Tesseract instances, serial OCR inside each worker, `OMP_THREAD_LIMIT=1`, and a cap of `2` workers on the S25. Sub-`60s` remains open.
**Next**: Resume from `.codex/plans/2026-04-06-ocr-runtime-worker-pool-handoff.md` and choose between stricter raw-grid gating or the next runtime-cut below the worker boundary.

### Session 742 (2026-04-06)
**Work**: Full 12-agent adversarial review of design system overhaul plan (4 groups x 3 reviewers), deduplicated findings, dispatched 4 fixer agents. 71 fixes applied.
**Decisions**: Review structure: 4 groups of 3 agents (code-review, security, completeness), each covering 2 phases. Fixers run 1 per group. All security reviews APPROVE. Plan ready for implementation.
**Next**: `/implement` the design system overhaul plan.

### Session 741 (2026-04-06, Codex)
**Work**: Stabilized Android PDF diagnostics/artifact upload, reverified Springfield green at 131/131 on the decomposed pipeline, then pushed single-lane OCR runtime down to ~128s on a faster candidate that regressed to 130/131.
**Decisions**: Treat the ~140s Android 131/131 run as the protected OCR baseline.
**Next**: Tune the default OCR crop target back up from the regressed 400 path.

### Session 740 (2026-04-06)
**Work**: Full tailor + writing-plans pipeline for pay-application spec. 3 parallel writers, 3 parallel reviewers, 1 fixer cycle.
**Next**: Review Cycle 2 → implement.

### Session 739 (2026-04-06, Codex)
**Work**: Reverified live sync on Android/Windows, fixed consent insert-only push and driver-build Help & Support gating.

## Test Results

### Flutter Unit Tests (S726)
- **Full suite**: 3784 pass / 2 fail (pre-existing: OCR test + DLL lock)
- **Analyze**: 0 issues
- **Database tests**: 65 pass, drift=0
- **Sync tests**: 704 pass

### E2E Test Run (S724)
- **Run**: 2026-04-03_10-06 (Windows)
- **Results**: 28 PASS / 0 FAIL / 30 SKIP / 6 MANUAL

## Reference
- **PR #140**: OPEN (7-issue fix)
- **GitHub Issues**: #89 (sqlcipher), #91-#92 (OCR), #127-#129 (enhancements)

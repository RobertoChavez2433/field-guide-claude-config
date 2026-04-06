# Session State

**Last Updated**: 2026-04-06 | **Session**: 741

## Current Phase
- **Phase**: PDF OCR runtime stabilization on `sync-engine-refactor`
- **Status**: Android Springfield is green at 131/131 around 140s on the protected OCR baseline; the newer faster 400/450 crop target is ~128s but regressed to 130/131 and needs another tuning pass before more optimization.

## HOT CONTEXT - Resume Here

### What Was Done This Session (741)

1. **PDF diagnostics path stabilized**:
   - Android artifact uploads to the debug server are working again
   - live stage `display_name` values are visible
   - Springfield integration test initializes Tesseract/logger correctly on Android

2. **Android Springfield reverified green on the decomposed pipeline**:
   - `131/131`
   - exact checksum `$7,882,926.73`
   - `autoAccept`
   - runtime around `140s`

3. **Single-lane OCR runtime optimization continued**:
   - lazy crop PNG generation
   - cheaper OCR PNG compression
   - sampled residue metrics
   - OCR engine pooling by effective OCR lane instead of mutating one instance

4. **Latest faster OCR candidate is not green yet**:
   - new 400/450 crop target split ran in about `128s`
   - regressed to `130/131`
   - checksum fell to `$7,880,946.73`
   - missing item-number fidelity produced a bogus row

5. **Codex handoff plan added**:
   - `.codex/plans/2026-04-06-pdf-ocr-runtime-stabilization-plan.md`
   - this is the next-session reference point for resuming the OCR tuning loop

### What Needs to Happen Next

1. Recover the Android Springfield quality gates on the faster OCR branch:
   - restore `131/131`
   - exact checksum
   - keep uploaded artifacts/live diagnostics green
2. Use the 450-DPI green Android run as the protected baseline and tune the default crop target back upward from the regressed 400 path.
3. Re-run the Android Springfield integration loop after each OCR tuning change until runtime is below the 140s baseline without losing correctness.
4. Keep pay-application work parked where it is:
   - plan exists
   - cycle 2 review is still pending

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

### Session 741 (2026-04-06, Codex)
**Work**: Stabilized Android PDF diagnostics/artifact upload, reverified Springfield green at 131/131 on the decomposed pipeline, then pushed single-lane OCR runtime down to ~128s on a faster candidate that regressed to 130/131.
**Decisions**: Treat the ~140s Android 131/131 run as the protected OCR baseline. Do not start worker-isolate OCR yet; recover correctness first on the faster branch. Track the resume target in `.codex/plans/2026-04-06-pdf-ocr-runtime-stabilization-plan.md`.
**Next**: Tune the default OCR crop target back up from the regressed 400 path and rerun Springfield on Android until 131/131 is restored below the 140s baseline.

### Session 740 (2026-04-06)
**Work**: Full tailor + writing-plans pipeline for pay-application spec. 3 parallel writers, 3 parallel reviewers, 1 fixer cycle.
**Decisions**: Schema v52 (not v51). ExportPayAppUseCase wired into provider (not inline reimpl). DiscrepancyPdfBuilder added. Phase 1.6/1.8 deferred to Phase 5 to avoid duplication.
**Next**: Review Cycle 2 → implement.

### Session 739 (2026-04-06, Codex)
**Work**: Reverified live sync on Android/Windows, fixed consent insert-only push and driver-build Help & Support gating, closed remaining open sync issues.
**Next**: Continue with photo/document/export round-trip verification.

### Session 738 (2026-04-06, Codex)
**Work**: Finished PDF extraction/OCR stage decomposition, closed trace/count/timing gaps.
**Next**: Push sync-engine-refactor, run CI.

### Session 737 (2026-04-05)
**Work**: Sync engine refactor Phase 9 — rewrote docs, verified success metrics.

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

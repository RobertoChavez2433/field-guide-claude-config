# Session State

**Last Updated**: 2026-04-06 | **Session**: 746

## Current Phase
- **Phase**: Sync delete-orchestration hardening on `sync-engine-refactor`
- **Status**: Live S21 + Windows verification proved the sync engine is much stronger, but delete propagation was still suffering from graph drift and scope drift. The immediate direction is to split delete orchestration responsibilities so local cascade, remote delete coordination, scope revocation, storage cleanup, and verification cannot silently diverge.

## HOT CONTEXT - Resume Here

### What Was Done This Session (746)

1. **Delete propagation was verified live on S21 + Windows and real sync defects were exposed**:
   - Real entry delete through the UI initially soft-deleted `daily_entries` but left active `photos` / `documents`
   - Receiver pull initially missed child tombstones after parent deletion because deleted parent IDs dropped out of pull scope
   - Project delete RPC deleted `project_assignments` remotely, but the local project cascade left them active locally

2. **Those delete defects were fixed in code and re-proven live**:
   - `DailyEntryProvider.deleteEntry()` now routes through `SoftDeleteService.cascadeSoftDeleteEntry(...)`
   - Pull scope materialization now retains deleted parent `entry_id` / `contractor_id` values for downstream tombstones
   - `project_assignments` was added to the shared project soft-delete graph so local project delete matches the remote RPC subtree delete
   - Entry delete and project delete now converge correctly across sender, Supabase, and Windows receiver

3. **The architectural direction is now clear**:
   - The problem is not “one larger soft delete service”
   - The problem is orchestration drift between graph definition, local cascade, remote delete path, scope cleanup, and verification
   - The next sync work should explicitly split delete orchestration into separate collaborators and lock them to one shared graph/materialized-scope contract

### What Needs to Happen Next

1. **Keep sync as the main shared-branch priority on `sync-engine-refactor`**:
   - continue from `.codex/plans/2026-04-06-payapp-sync-bulletproof-todo.md`
   - continue from `.codex/plans/2026-04-06-delete-propagation-hardening-plan.md`
   - continue from `.claude/test-results/2026-04-06_193351_codex_sync-delete-live/report.md`
2. **Implement the split delete orchestration structure**:
   - `DeleteGraphRegistry` remains the single topology authority
   - add/strengthen a local cascade orchestrator, remote delete coordinator, scope-revocation cleaner, storage cleanup coordinator, and propagation verifier as separate responsibilities
   - do not let project soft delete, remove-from-device, revocation cleanup, orphan purge, and verification keep separate child-table knowledge
3. **Finish the remaining delete release proof**:
   - verify project-delete storage cleanup explicitly
   - verify deleted entry/project absence in UI on both devices
   - deduplicate `delete-propagation` project snapshot output
   - continue into remaining file-backed and user-scoped sync lanes
4. **OCR remains isolated on `codex/ocr-per-page-runtime-isolation`**:
   - do not mix OCR runtime work back into `sync-engine-refactor`
   - continue OCR separately after the sync release gate is satisfied

### User Preferences (Critical)
- **Fresh test projects only**: NEVER use existing projects during test runs
- **CI-first testing**: NEVER include `flutter test` in plans or quality gates
- **Always check sync logs** after every sync during test runs
- **No band-aid fixes**: Root-cause only
- **Verify before editing**: Understand root cause first
- **All findings must be fixed**: ALL review findings, not just blocking ones
- **No // ignore to suppress lint**: Fix the root cause
- **For OCR runtime work**: use the S25 and the debug server; do not use the S21 for that branch

## Blockers

### BLOCKER-37: Delete orchestration drift causes stale local residues after deletes
**Status**: OPEN — active sync-release blocker

### BLOCKER-34: Item 38 — Superscript `th` → `"` (Tesseract limitation) (#91)
**Status**: OPEN (parked, cosmetic)

### BLOCKER-36: Item 130 — Whitewash destroys `y` descender (#92)
**Status**: OPEN (parked, cosmetic)

### BLOCKER-28: SQLite Encryption (sqlcipher) (#89)
**Status**: OPEN — production readiness blocker

## Recent Sessions

### Session 746 (2026-04-06, Codex)
**Work**: Drove live delete verification on S21 + Windows, fixed entry-delete child cascade, fixed receiver child-tombstone pull scope, fixed project-delete local `project_assignments` parity, and updated the sync proof artifacts/checklists.
**Decisions**: Delete propagation needs split orchestration, not a larger monolith. The shared delete graph and materialized scope must be the only authorities used by local cascade, remote delete, revocation cleanup, and verification.
**Next**: Commit the current sync-engine-refactor delete hardening in logical slices, preserve OCR isolation in its own branch, then continue with project-delete storage cleanup proof, deleted-item UI absence proof, and the remaining sync release lanes.

### Session 745 (2026-04-06, Codex)
**Work**: Re-grounded the OCR runtime work around the page-local bottleneck, wrote the per-page optimization plan/TODO, created a full OCR branch handoff, and isolated the OCR line onto `codex/ocr-per-page-runtime-isolation`.
**Decisions**: The worker-pool boundary is good enough. The next OCR work must target lower per-page OCR cost and/or lower OCR call volume, starting with a lower-overhead OCR result-format seam before row-banded experiments.
**Next**: Resume on `codex/ocr-per-page-runtime-isolation`, keep `2` workers as the protected baseline, add the non-HOCR output seam, then attempt the first lower-call-count page recognizer proof.

### Session 744 (2026-04-06, Codex)
**Work**: Migrated the pay-app/sync hardening work back onto `sync-engine-refactor`, preserved recovery paths, removed the stale verification worktrees, and wrote the sync-verification continuation report and quality gates.
**Decisions**: Sync verification is the top shared-branch priority. Continue from `sync-engine-refactor`, not the removed worktrees. Treat file-backed sync proof across SQLite/`change_log`/Supabase/storage as the acceptance bar.
**Next**: Re-establish S21 runtime verification and execute the first-class `export_artifacts` / `pay_applications` round-trip proof before any lower-priority polish.

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

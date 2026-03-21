# State Archive

Session history archive. See `.claude/autoload/_state.md` for current state (last 5 sessions).

---

### Session 605 (2026-03-20)
**Work**: Full writing-plans pipeline: CodeMunch dependency graph (22 files), opus plan-writer, parallel adversarial review (code-review REJECT + security APPROVE w/ conditions). Fixed 3 CRITICAL + 6 HIGH + 4 MEDIUM findings in plan v2. 15 path corrections.
**Decisions**: Error reset targets change_log (not entity tables). Bug 10 trusts RLS (no .like filter). RPC allowlist required. Eager checkConfig on login.
**Next**: /implement the plan. Push Supabase migrations first. Re-run baseline.

### Session 604 (2026-03-20)
**Work**: Deep exploration of all 17 baseline bugs (4 parallel agents). Brainstormed each bug 1-by-1. Wrote spec v3 with adversarial review (5 MUST-FIX + 7 SHOULD-CONSIDER, all resolved inline). Committed S590+ work (3 commits). Cleaned 137 test screenshots.
**Decisions**: Engine-internal enrollment for sync pull. `toMap()` fix for priority. `didChangeDependencies` for controller init (deviation documented). SyncProvider dedup for snackbar. Profile-completion gate for existing users.

### Session 603 (2026-03-20)
**Work**: Full baseline E2E test. 38 PASS / 1 FAIL / 16 BLOCKED / 39 SKIP. Both roles tested (admin + inspector). 17 bugs catalogued. Sync pull root cause found (synced_projects empty). Todo push root cause found (priority type mismatch). Testing keys agent added 7 missing key sets. Inspector permissions all correct (T85-T90 PASS).
**Decisions**: Sync pull fix is #1 priority (unblocks 12+ flows). Todo priority fix is #2. LateInitError is #3.
**Next**: Fix sync pull + todo priority + _contractorController init. Commit. Re-run baseline.

### Session 602 (2026-03-20)
**Work**: Expanded test registry from 14 to 104 flows (96 automated + 8 manual). 4 parallel exploration agents mapped all 37 routes, 17 synced tables, 3 roles, all dialogs/forms. Organized into 13 tiers with full dependency chain.
**Decisions**: 8 flows marked MANUAL. Separate inspector session. Sync verification tier runs after data creation tiers.

---

## March 2026

### Session 600 (2026-03-19)
**Work**: Test skill redesigned for autonomous overnight mode. Credentials verified. Ghost project defect logged.
**Decisions**: Autonomous mode = orchestrator runs directly. Checkpoint.json for compaction recovery.
**Next**: /test overnight. Commit. Debug APK.

### Session 599 (2026-03-19)
**Work**: First /test run on Windows. Updated test-wave-agent.md and SKILL.md.
**Decisions**: Opus for test agents. python3 replaces jq.
**Next**: Re-run /test. Commit.

### Session 594 (2026-03-19)
**Work**: /writing-plans on E2E sync verification spec. Full pipeline: CodeMunch indexing, dependency graph, Opus plan-writer, parallel adversarial review (code REJECT + security APPROVE WITH CONDITIONS). Fixed 4 critical + 4 high findings inline. 7-phase plan with 12 sub-phases.
**Decisions**: Per-table sync events deferred. Gitignore before .env.secret. _debugServerEnabled gate added.
**Next**: /writing-plans on bug triage spec. /implement both plans. Commit S590 work.

### Session 593 (2026-03-19)
**Work**: Bug triage — read bugs_report.md, dispatched 4 exploration agents (all 13 bugs confirmed), brainstormed fix approach (8 questions), wrote spec, adversarial review (8 MUST-FIX + 9 SHOULD-CONSIDER all resolved). New permission model: canManageProjects + canEditFieldData replacing canWrite.
**Decisions**: Inspector = field data CRUD. canWrite removed. is_viewer() body replaced not dropped. RLS INSERT + UPDATE tightened. BUG-005+002 merged.
**Next**: /writing-plans → /implement bug triage fixes. flutter test. Commit S590 work.

### Session 592 (2026-03-19)
**Work**: Designed E2E sync verification system. Researched testing keys (488 existing, ~30 missing). Brainstormed + spec'd 42-flow test checklist covering 17 tables. Adversarial review (10 MUST-FIX resolved). Architecture: flutter_driver + debug server hybrid.
**Decisions**: flutter_driver for driving, debug server for diagnostics. E2E prefix for test data. `.env.secret` for service role key. flow_registry in .claude/.
**Next**: /writing-plans → /implement verification system. Fix BUG-006 (blocks sync testing). Commit S590 work.

### Session 591 (2026-03-18)
**Work**: Live 2-device testing (S25 admin + Windows inspector). Filed 14 bugs in `bugs_report.md`. Critical: sticky _isOnline kills sync (BUG-006), synced_projects gap (BUG-005), no route guards (BUG-007), canWrite=true for inspector (BUG-008). Permission audit found 10 inspector role gaps.
**Decisions**: BUG-013 dismissed (inspector remove-from-device is intentional). Session ended early — S25 sync blocked.
**Next**: Fix BUG-006 (sticky _isOnline). Fix BUG-005/007/008. Re-run untested flows. Commit S590 work.

### Session 590 (2026-03-18)
**Work**: /implement project state UI plan (11 phases, 9 orchestrator launches, 0 handoffs). 38 files modified. All reviews PASS. New: project_assignments table, adapter, provider, 3-tab list screen, assignment wizard.
**Decisions**: None new — followed S588-S589 spec/plan decisions.
**Next**: flutter test + analyze. Commit. Fix OrphanScanner + display_name bugs. Build + device test.

### Session 587 (2026-03-18)
**Work**: Device testing bug fixes (P1 location, P2 weather, P4/P8 delete-sync, P6/P7 admin offline). CRITICAL: found and fixed sync permanent offline trap (_isOnline never recovers). Debug APK v0.1.2-debug-s587 on GitHub.
**Decisions**: Tombstone check via change_log not separate table. P3/P5 are network, not code.
**Next**: Device test new APK. Commit.

### Session 586 (2026-03-18)
**Work**: /implement project management E2E plan (11 phases, 6 orchestrator launches, 0 handoffs). 30 files modified, 3032 tests passing. All reviews PASS. Bug found: code.contains('503') masks 23503 FK errors.
**Decisions**: Batched final 4 phases into one orchestrator launch. Repair migration deferred as tech debt.
**Next**: Commit. Push Supabase migrations. Build + device test. Fix BLOCKER-22. Fix 503 bug.

---

## March 2026

### Session 585 (2026-03-17)
**Work**: Implemented sync hardening plan (4 orchestrator launches, 2962 tests passing). Device testing found Import broken (missing Provider). Full project lifecycle audit (13 issues). Brainstormed + spec'd + planned project management E2E fix (11 phases). Committed 7 app commits + 2 config commits.
**Decisions**: Metadata auto-sync only (no auto-enroll). Keep canWrite (add new methods alongside). SECURITY DEFINER RPC for remote delete. Remove viewer role. Available Projects from local SQLite.
**Next**: /implement project management E2E plan. Build + device test. Fix BLOCKER-22.

### Session 584 (2026-03-17)
**Work**: Systematic debugging for BLOCKER-38 + BLOCKER-39 + proactive sync audit. Launched 2 deep research agents (found 10 additional sync issues). /writing-plans produced 6-phase plan. Adversarial review (code + security) found 2+2 CRITICAL, 5+4 HIGH findings — all fixed inline. Plan ready for /implement.
**Decisions**: ConflictResolver keeps Future<ConflictWinner> (query-based conflict count). Offline removal guard at service + UI layers. Migration uses DROP POLICY IF EXISTS defensively. fkColumnMap corrected for EntryPersonnelCountsAdapter.
**Next**: Commit S583 bugfixes. /implement sync hardening plan. Test on device.

### Session 583 (2026-03-17)
**Work**: Device testing session. Version bump to 0.1.1. Fixed 8 bugs across auth, sync, and admin flows. Discovered root cause: version-upgrade forced signOutLocally() which wiped all local data. Fixed by adding forceReauthOnly() method. Reverted auto-enrollment of pulled projects.
**Decisions**: forceReauthOnly() preserves local data on upgrade. Draft INSERTs must suppress triggers. Auto-enrollment of pulled projects is WRONG — selective import is intentional.
**Next**: Commit fixes. Fix project import UX gap. RLS migration.

---

## March 2026

### Session 582 (2026-03-16) — Archived from _state.md (Session 587 rotation)
**Work**: /implement for project lifecycle (19 phases, 11 orchestrator launches, 0 handoffs). All reviews PASS. Committed 6 logical commits to app repo + 1 to config repo. ~140 files changed total.
**Decisions**: Merged PR2 phases (15-19) into single orchestrator launch for speed — worked without context exhaustion.
**Next**: Rebuild + test on device. Push Supabase migrations. Fix BLOCKER-22.

### Session 581 (2026-03-16) — Archived from _state.md (Session 586 rotation)
**Work**: /writing-plans for project lifecycle. CodeMunch indexed 850 files/5469 symbols. Opus plan-writer produced 19-phase plan.
**Next**: /implement the plan.

### Session 577 (2026-03-15) — Archived from _state.md (Session 582 rotation)
**Work**: Systematic debug of items 38, 62, 130. Corrected wrong root cause for item 62 (NOT a dedup issue — currency parsing bug + OCR non-determinism). Fixed both: currency double-dollar bug in `_normalizeCorruptedSymbol`, sequential gap-fill in `ItemDeduplicator.deduplicate`. Springfield: 131/131, $0 checksum. Committed 5 logical commits.
**Decisions**: Item 62 had TWO failure modes (Tesseract non-determinism). textProtection won't work for item 130 (descenders classified as grid). Threshold-based whitewash is the correct approach.
**Next**: Verify on Android device. Fix items 130 (threshold whitewash) and 38 (ordinal suffix recovery).

### Session 576 (2026-03-15) — Archived from _state.md (Session 581 rotation)
**Work**: Deep systematic debug of all 6 OCR failures. Fixed 3 (items 22, 26, 97). Deep-traced remaining 3 with individual agents. Springfield: 130/131, desc 98.5%, numerics 100%. Tried whitewash bleed reduction — regressed, reverted.
**Decisions**: Pipe stripping must run AFTER rules. `_kWhitewashBleed=2` is essential (bleed=1 causes 126/131 regression). Item 130 needs text-aware whitewash. Item 62 needs sequential dedup or PSM 13. Item 38 needs per-token retry or PDF text layer.
**Next**: Fix item 62 (sequential dedup), fix item 130 (text-aware whitewash), fix item 38 (per-token retry). Commit.

### Archived PDF Defects (from _defects-pdf.md, Session 580 rotation)

**[DATA] 2026-03-09**: BLOCKER-35 — Cross-Device Checksum Divergence $500K (S530). pdfrx migration: Windows vs S25 checksums differ by $500K. Likely Tesseract non-determinism.
**[DATA] 2026-03-09**: R2 Plan Gap — First priceContinuation Path Unchecked (S527). Both priceContinuation paths must check for item-column text.

### Archived Sync Defects (from _defects-sync.md, Session 580 rotation)

**[FLUTTER] 2026-03-06**: Mock SyncOrchestrator missing `getPendingBuckets()` causes test hang (S511). Override both methods when mocking.
**[ASYNC] 2026-03-06**: `_lastSyncTime` persisted on failure creates 24h dead zone (S511). Only update on success.

### Session 574 (2026-03-15)
**Work**: Implemented post-inpaint whitewash (Option B) in grid_line_remover. Springfield: 131/131 items, $0 checksum (was $1.39M), numeric 100%. Description 90% — investigated 13 failures (4 categories), wrote OCR normalization plan (5 rules across 2 files).
**Decisions**: Whitewash at expandedThickness+4px bleed. Text protection confirmed already disabled. Generic algorithmic rules only (no PDF-specific heuristics). 2 items unfixable (OCR limitations).
**Next**: `/implement` OCR normalization plan. Commit all changes.

### Session 575 (2026-03-15)
**Work**: Implemented OCR accuracy fixes plan (6 fixes across 4 phases). Springfield: 130/131, desc 96.2%, unit/qty/price/amount 100%. 4 items fixed (36, 37, 52, 106). 2 regressions from 900 DPI upscale (items 22, 97). Cell crop diagnostic confirms all crops pristine — failures are Tesseract misreads.
**Decisions**: 900 DPI description upscale is counterproductive — must revert to 600 max. Need deep debug session for remaining 6 failures.
**Next**: Revert 900 DPI, add pipe to roman numeral regex, deep debug all remaining failures, commit.

## March 2026

### Session 573 (2026-03-15)
**Work**: Phase 6 integration verification — Springfield REGRESSED ($1.39M checksum distance, -63 elements). Root-caused via systematic-debugging: TELEA creates ~2px bleed artifacts beyond mask boundary. Orange diff bands confirmed as diagnostic artifact (hardcoded fringeMargin). Generated 1644 cell crop PNGs. Three-agent investigation: Option B (post-inpaint whitewash in grid_line_remover) is the fix.
**Decisions**: Option A (+2px safety) too marginal. Option C (mask expansion) already working. Option B eliminates TELEA bleed at source.
**Next**: Investigate Option B with 2 agents, implement, re-run Springfield.

### Session 568 (2026-03-14)
**Work**: Implemented dynamic fringe removal (4 orchestrator launches, all PASS). Springfield 82→114/131 (+32). Deep root cause analysis: 30% of lines have text-adjacent fringe that can't be measured → residue in crops → Tesseract reads "|" → item# garbled → rows misclassified as priceContinuation → mega-blobs. Option A (lower sample threshold) tested — no effect. Fringe fallback plan written.
**Decisions**: Fix grid_line_remover fringe coverage first. Two-pass: measure all, compute page avg, apply as fallback to zero-measurement lines. Option B (crop inset) is fallback plan.
**Next**: `/implement` fringe fallback plan. Retest Springfield. If insufficient, implement crop boundary inset.

## March 2026

### Session 566 (2026-03-14, Codex)
**Work**: Implemented much of the PDF wave-1 plan: corpus/harness, OCR decision tracing, residue metrics, OCR policy scaffolding, and safe Windows build recovery. Re-ran the Windows Springfield report multiple times and compared against an archived pre-wave baseline.
**Decisions**: Keep the new harness/diagnostics, but do not treat wave 1 as successful. Revert grid-removal behavior changes when they regress controls. Keep work upstream-only; no downstream compensation.
**Next**: Recover or exceed the archived baseline in Stage `2B-iii`, improve item-number corpus performance, and fix the remaining `cell_boundary_verification_test.dart` failure.

### Session 563 (2026-03-13)
**Work**: Verification pass — analyze clean, migration review, fixed `user_id→id` bug in email backfill, deployed both Supabase migrations. Added Supabase CLI to CLAUDE.md.
**Decisions**: `npx supabase` is the CLI access pattern.
**Next**: Commit all changes. On-device smoke test. Decide on text protection.

## March 2026

### Session 561 (2026-03-13)
**Work**: Pipeline report redesign implemented via `/implement`. Orchestrator Phases 1-2, supervisor Phase 3. Manual fixes: column truncation, OCR element limit (3/cell), Performance Summary kept. Springfield test passes 2m17s.
**Decisions**: Performance Summary kept (user override). Column truncation essential for readability. Orchestrator overkill for single-file changes.
**Next**: Commit report changes. `/implement` sync hardening plan.

### Session 560 (2026-03-13)
**Work**: Full `/writing-plans` for sync hardening. CodeMunch dependency graph (14 direct, 6 dependent, 14 test files). Opus plan-writer (9 phases, 24 sub-phases). Parallel adversarial review (code-review + security). All CRITICAL/HIGH findings fixed in plan.
**Decisions**: M-8 false positive (intentional double read). user_certifications not synced (removed). Migration timestamps aligned.
**Next**: `/implement` sync hardening plan.

### Session 559 (2026-03-13)
**Work**: Fixed CodeMunch MCP index_folder hang. Root cause: local fork v0.2.14 (92 commits behind) lacked asyncio.to_thread + os.walk. Switched to PyPI v1.3.8. Fresh index working (828 files, 14.5s).
**Decisions**: PyPI over local fork. AI summaries ON. Context providers OFF. New repo name `local/Field_Guide_App-37debbe5`.
**Next**: `/writing-plans` → `/implement` sync hardening or report redesign.

### Session 558 (2026-03-13)
**Work**: Auth bugfix implemented + deployed. Sync engine audit (20 issues, 3 agents). Full brainstorming (21 items triaged). Sync hardening spec written + adversarial review (both APPROVE, 6 MUST-FIX addressed).
**Decisions**: Local soft-delete (Option A). Pre-check only (no onConflict). Keep pull cursor margin. stamp_deleted_by trigger. Backfill emails. Tighten RLS.
**Next**: `/writing-plans` → `/implement` sync hardening spec.

## March 2026

### Session 557 (2026-03-13)
**Work**: Brainstormed pipeline report redesign with 4 Opus research agents. Spec written + adversarial review.
**Decisions**: Markdown tables mirroring PDF layout. Two tables (clean + OCR). Stage summary one row per stage.
**Next**: `/writing-plans` → `/implement` the report redesign.

### Session 556 (2026-03-13)
**Work**: Disabled text protection. Pipeline: 67 data rows, 61 items, 23 BOGUS, 0.920 median confidence.
**Decisions**: Text protection hurts more than helps. Leading fix: disable + confidence filter.
**Next**: Fix cell grid display format, decide text protection permanently.

### Session 555 (2026-03-13)
**Work**: Systematic debugging of 2 auth/onboarding bugs. Plan written via writing-plans orchestrator.
**Decisions**: Bug 1: isLoadingProfile guard. Bug 2: update search_companies RPC.
**Next**: `/implement` the auth-onboarding-bugfix plan.

### Session 554 (2026-03-13)
**Work**: Deep pipeline tracing (20 stages). Root cause: Grid Removal v3 regressed 130→38 data rows. Anti-aliasing fringe measured.
**Decisions**: Text protection can't be disabled (Tesseract crashes). Need smarter approach.
**Next**: Fix grid removal v3 text protection approach.

### Session 553 (2026-03-12)
**Work**: Implemented grid-aware row classification via /implement (5 files, 10 tests). Pipeline regressed: 37/131 items but 22 BOGUS (was 3). Root cause: OCR noise accumulation.
**Decisions**: Grid-aware grouping correct in principle but requires clean OCR.
**Next**: Revert grid-aware code, fix OCR noise at source.

### Session 552 (2026-03-12)
**Work**: Implemented+tested+reverted Option C (no downstream impact). Disproved boilerplate intrusion hypothesis.
**Decisions**: Option C reverted. Boilerplate NOT entering OCR pipeline.
**Next**: Investigate row classification accuracy.

### Session 550 (2026-03-12)
**Work**: Verified mask fix (0 excess, 35/131 items). Confirmed text protection hypothesis. Wrote Option C plan (table-bounded dilation). Major project cleanup (~1.78 GB, 23K stale lines). Committed all work (5 commits across 2 repos).
**Decisions**: Option C selected for text protection fix. Restrict dilation to grid table bounds using sortedH/sortedV. Margin = maxLineWidth//2 + 3. Degenerate guard falls back to global.
**Next**: `/implement` Option C, re-run pipeline, verify.

### Session 546 (2026-03-12)
**Work**: Full v3 brainstorming session. 5 Opus agents for research. Brainstormed 3 approaches → Option A selected. Spec written (6-step algorithm). Adversarial review (7 MUST-FIX + 6 SHOULD-CONSIDER). All MUST-FIX addressed.
**Decisions**: Morph isolation + HoughLinesP + text protection. No GridLine model changes (YAGNI). 5x5 text dilation. 15px cross-ref tolerance.
**Next**: `/writing-plans` → `/implement` → verify.

### Session 545 (2026-03-12)
**Work**: Ran v2 verification phases. 56/131 items. Mask deviates from grid lines. Root cause: matched filter at perpendicular intersections.
**Decisions**: Matched filter fundamentally flawed. v3 will use HoughLinesP.
**Next**: Research → brainstorm/spec → implement.

### Session 541 (2026-03-11)
**Work**: Pipeline regression verified (81/131 items). 3 root causes confirmed. 6 research agents. 3-way diagnostic comparison.
**Decisions**: Need brainstorming. Matched filter needs multi-sample median.
**Next**: Brainstorm → implement → verify.

### Session 538 (2026-03-11)
**Work**: Full brainstorming on grid removal fix. 4 agents for deep context. Adversarial review (6 MUST-FIX all resolved). Spec finalized.
**Decisions**: Intersection-anchored refinement. `GridLine` struct. `cv.line()` per segment. R1 expanded.
**Next**: `/writing-plans` → `/implement` → measure.

### Session 537 (2026-03-11)
**Work**: Systematic debugging of extraction failures. Created diagnostic test. Visual proof: 25-38% mask excess.
**Decisions**: Grid removal = upstream root cause. Detector output wasted by remover.

### Session 534 (2026-03-11)
**Work**: Updated writing-plans skill. Attempted /implement 4 times — orchestrator writes code directly. Investigated tool restrictions.
**Decisions**: All haiku→sonnet. Writing-plans works. Implement broken.

### Session 533 (2026-03-10)
**Work**: 8-agent test audit. Brainstorming spec for pipeline test restructure. Adversarial review (16 items). Spec finalized.
**Decisions**: Report-first architecture. Regression ratchet. No normalization. Single comparator.

### Session 529 (2026-03-09)
**Work**: Ran `/writing-plans` on pdfrx parity spec. CodeMunch index (681 files). Wrote 7-phase plan with full code. Dual adversarial review (code-review + security). All CRITICAL/HIGH addressed.
**Decisions**: Centralize BGRA→PNG in `RenderedPage.toPngBytes()`. Runtime `if` not `assert` for buffer validation. Verify pdfrx API post-install before coding.

### Session 525 (2026-03-09)
**Work**: Full GT trace (34 failures). 7 research agents + 2 Opus verification. Found 3/5 original fixes had wrong root causes. Revised to R1-R5 plan.
**Decisions**: Opus verification before implementation. GT unit abbreviations are correct — pipeline normalization is wrong.

### Session 524 (2026-03-08)
**Work**: Implemented grid line threshold fix via /implement. `_adaptiveC` -2.0→10.0. Mask coverage 77%→5.3%. Item 96 bid_amount recovered.
**Next**: Commit changes. Create PR.

### Session 523 (2026-03-08)
**Work**: Systematic debugging traced all 3 item failures to grid line removal adaptive threshold bug.
**Next**: Implement fix. Regenerate fixtures. Verify scorecard.

### Session 522 (2026-03-08)
**Work**: Deep root cause investigation via 4 parallel agents. Traced item 96 OCR fragmentation.
**Next**: Decide fix approach. Implement.

### Session 519 (2026-03-08)
**Work**: Full brainstorming → spec → adversarial review → writing-plans pipeline for .claude/ directory baseline audit.
**Next**: Execute audit plan via /implement.

### Session 518 (2026-03-08)
**Work**: Restructured planning pipeline. Implemented via /implement (0 findings). 3-agent post-verification (44/44 PASS).
**Next**: Push .claude repo. pdfrx migration. PR.

### Session 517 (2026-03-08)
**Work**: Rewrote `/implement` skill with per-phase reviews. Implemented via /implement (0 findings). Code review verified (1 LOW fixed).
**Next**: pdfrx migration Phase 0.

### Session 515 (2026-03-07)
**Work**: DPI fix implemented + device-tested (not root cause — grid pages skip recognizeImage). Root-caused to renderer divergence (pdfx AOSP PdfRenderer vs upstream PDFium). Researched pdfrx (4 agents), mapped blast radius (2 agents), wrote 7-phase migration plan, adversarial review (17 findings addressed), brainstormed all decisions (BGRA passthrough, format enum, alias import, Phase 0 verification).
**Decisions**: pdfrx replaces pdfx. Raw BGRA passthrough (no PNG encode/decode). RenderedPage format enum. Image.fromBytes(order: ChannelOrder.bgra). Phase 0 API verification mandatory. pdfrx alias import for PdfDocument collision.
**Next**: Implement pdfrx migration Phase 0, then full migration, device validation.

### Session 514 (2026-03-07)
**Work**: Full overhaul of systematic-debugging skill (7 phases, 6 files updated, 3 deleted). Brainstormed specs, compared vs upstream superpowers, indexed codebase via CodeMunch. Added sync engine traces, 5-layer defense model, ADB/UIAutomator patterns, 3 new defect categories. Dual Opus review caught 4 issues, all fixed.
**Decisions**: Remove pressure tests. Rewrite condition-based-waiting for ADB. 5-layer defense. Add SYNC/MIGRATION/SCHEMA defect categories. Keep codex wrapper.
**Next**: Implement OCR DPI fix, device test, commit, PR.

### Session 513 (2026-03-07)
**Work**: Device-tested sync engine. Diagnosed PDF OCR regression: V2 engine not threading DPI to Tesseract. Added temp stage dumps, pulled 28 stage JSONs, pinpointed divergence at items 94-96 on page 4. Wrote fix plan.
**Decisions**: Fix is 2 setVariable calls. No pdfx changes needed. Temp stage dump code to be removed after verification.
**Next**: Implement OCR DPI fix, re-test on device, remove temp code, commit, PR.

### Session 511 (2026-03-06)
**Work**: Implemented sync auth fix (4 bugs in sync_orchestrator.dart). Fixed hanging test. Full suite passes.
**Decisions**: Adversarial plan superseded original. Guard before _updateStatus to avoid UI flicker.
**Next**: Commit, device test, PR to main. Then start UI refactor.

### Session 510 (2026-03-06)
**Work**: Wrote comprehensive UI refactor implementation plan (12 phases, 50+ subphases, 100+ steps). Encoded all brainstorm decisions, component specs, token gaps, violation registry, and cheat sheets into actionable plan.
**Decisions**: None new — all decisions were locked in session 509. This session was pure planning/writing.
**Next**: Implement sync auth fix. Then start UI refactor Phase 1 (Foundation).

### Session 509 (2026-03-06)
**Work**: Implemented sync UX fixes plan (6 files, 6 quality gates passed). Brainstormed UI refactor approach (12 phases).
**Decisions**: FieldGuideColors ThemeExtension, WeatherProvider, theme-aware colors, Extras & Overruns kept.
**Next**: Write comprehensive UI refactor plan. Commit sync + UX fixes.

### Session 508 (2026-03-06)
**Work**: Implemented consolidated-fixes plan (10 phases, 32 files, 6 quality gates). Device tested → found 3 sync UX bugs. Brainstormed sync UX fixes.
**Decisions**: Auth guard+retry (5s). Unified staleness banner. 4-bucket pending counts.
**Next**: Implement sync-ux-fixes (done in 509).

### Session 507 (2026-03-06)
**Work**: Device testing found 4 critical bugs. Fixed migration + permissions. Brainstormed project selection UX. Consolidated 2 plans into 1.
**Decisions**: Hybrid project list. NO auto-enrollment. Two-section UI.
**Next**: Implement consolidated plan (done in 508).

## March 2026

### Session 506 (2026-03-06)
**Work**: Full data layer audit with jcodemunch MCP. Dead code cleanup (13,450 lines). Found critical sync registry bug.
**Decisions**: entry_personnel safe to deprecate. Background sync needs own adapter registration.
**Next**: Implement data-layer-fixes (superseded by consolidated plan).

### Session 505 (2026-03-06)
**Work**: Full sync engine rewrite implementation. 5 orchestrator cycles, 3 review sweeps, 3 completeness audits. All 8 phases at 100%. 9 logical commits.
**Next**: Data layer audit (done in 506).

### Session 504 (2026-03-05)
**Work**: Round 3 review: 5 part-scoped agents found 14 critical + 15 high + 6 ambiguities.
**Next**: Implementation.

### Session 503 (2026-03-05)
**Work**: 8 per-phase review agents found 31 critical issues.
**Next**: Final plan review.

### Session 502 (2026-03-05)
**Work**: Verified bulletproof plan vs original.
**Next**: Round 3 review.

### Session 500 (2026-03-05)
**Work**: 4 code-review agents reviewed sync rewrite plan vs codebase. 46 findings (5 CRITICAL). Launched Opus agent to write bulletproof plan — hit 32K output limit.
**Decisions**: Original plan preserved. New bulletproof plan will be written to separate file.
**Next**: Create bulletproof plan, cross-reference vs original.

### Session 499 (2026-03-05)
**Work**: CodeMunch gap analysis of sync rewrite plan vs codebase (376 files, 3,757 symbols). Found 18 gaps. Expanded Phase 7 from 13 to 50+ tasks (8 sub-phases). Added 2 Phase 0 prereqs, 1 Phase 2 task, 3 Phase 6 tasks, 14 new tests, 3 risk rows.
**Decisions**: Plan hardened with complete cleanup manifest. Dead code grep gate as merge requirement.
**Next**: Commit BLOCKER-27, start Phase 0 (storage RLS first, 2 prereq checks).

### Session 498 (2026-03-05)
**Work**: Brainstormed 12 design decisions for sync rewrite (trigger gate, lock, push/pull, integrity, cutover, tables, PII, settings, profile). Table audit (1 legacy found). Integrated into plan (1,712 lines). Code review passed. Deleted superseded draft.
**Decisions**: sync_control gate, hybrid 5-min lock, user-driven project selection, no feature flag, Big Bang cutover, 16 adapter tables, user_certifications table, expanded profile, no SharedPrefs fallback.
**Next**: Commit BLOCKER-27, start Phase 0 (storage RLS first).

### Session 497 (2026-03-05)
**Work**: Launched 3 Opus agents to map fixes for all 63 adversarial findings. Draft integrated plan (1,714 lines) written then REVERTED. Explained 10 core functional changes to user. Saved draft as reference.
**Decisions**: User wants to brainstorm each core design change before integration. Original plan restored.
**Next**: Brainstorm 10 core design changes with user, commit BLOCKER-27, then Phase 0.

### Session 496 (2026-03-04)
**Work**: Adversarial review of sync rewrite plan with 3 agents (security, architecture, completeness). 63 findings: 16 CRITICAL, 23 HIGH, 15 MEDIUM, 9 LOW. All appended to plan with full context.
**Decisions**: Plan needs fixes before implementation. Top 5 blockers: trigger-pull infinite loop, LWW spoofing+tiebreaker, no rollback, entry_personnel ghost table, setForEntry poisoning.
**Next**: Brainstorm fixes for 63 findings, commit BLOCKER-27, then Phase 0.

### Session 495 (2026-03-04)
**Work**: Validated sync audit with 5 sonnet agents (confirmed all 19 gaps, found 11 new). Brainstormed sync rewrite (9 design decisions). Audited settings with 2 agents (15 issues). Wrote 8-phase implementation plan with testing strategy.
**Decisions**: SQLite triggers for change tracking. Table adapter registry. LWW + conflict_log. Three-phase photo sync. Incremental pull + daily integrity. Settings full redesign. Stage trace scorecard testing. Firebase deferred.
**Next**: Commit BLOCKER-27, start Phase 0 (schema + security), verify storage RLS.

### Session 493 (2026-03-04)
**Work**: Fixed BLOCKER-27 — sync_status infinite loop. Stripped sync_status from push payloads (3 files), forced 'synced' on pull (1 file), created Supabase migration to drop column. All tests pass.
**Decisions**: sync_status is local-only concept — never push to Supabase, always force 'synced' on pull. Drop column from Supabase entirely.
**Next**: Commit + push + deploy migration, verify BLOCKER-26, fix BLOCKER-24, fix BLOCKER-22.

### Session 492 (2026-03-04)
**Work**: Pushed repos + deployed Supabase migrations. Fixed 2 missing soft-delete tables (entry_contractors, entry_personnel_counts) — DB v29. Brainstormed + implemented app lifecycle safety (schema verifier, version tracking, upgrade re-auth, route restore removal). Fixed trash count refresh. Bumped to v0.76.0. Fixed Gradle lint lock (45s builds). Released v0.76.0.
**Decisions**: Schema verifier on every startup (self-healing). Cold start → dashboard. Upgrade → re-auth. Disable Gradle lint on release builds.
**Next**: Verify trash purge syncs to Supabase (BLOCKER-26), smoke test, fix BLOCKER-24, fix BLOCKER-22.

### Session 491 (2026-03-04)
**Work**: Context-efficient test skill. Investigated + brainstormed + implemented sync-aware soft-delete system (5 phases, 24 files, all quality gates). Committed 6 logical app commits + 2 config commits.
**Decisions**: Soft-delete + 30-day purge. Edit-wins conflict resolution. Trash screen in Settings. DB version 27→28.
**Next**: Push repos, deploy migration, smoke test.

### Session 488 (2026-03-03)
**Work**: Full `/test --all` run (3/5 PASS, 1 FAIL). Redesigned orchestrator + wave agent. Discovered BLOCKER-24.
**Decisions**: Orchestrator gets Task tool. Wave agents get Write/Edit + mandatory logcat.
**Next**: CLI restart, retry `/test --all`, fix BLOCKER-24, fix BLOCKER-22.

### Session 486 (2026-03-03)
**Work**: Brainstormed + implemented `/test` skill (ADB-based on-device testing). 5-question design session, then `/implement` for Phases 0-2. 6 new config files, 2 Dart files modified. All quality gates passed. Phase 3 (dry run) deferred.
**Decisions**: Hybrid UIAutomator+Vision. Wave-based dispatch. SKILL.md convention. Wave agent read-only (Bash+Read). Feature-path map in registry.
**Next**: Fix BLOCKER-22, commit+push, dry run `/test login` with device.

### Session 485 (2026-03-03)
**Work**: Systematic DB debug (7 issues found, all pre-fixed). Deployed 2 Supabase migrations. Fixed build infra (.env + dart-define across all build/run configs). GitHub Releases APK distribution. Confirmed project delete works.
**Decisions**: `.env` + `--dart-define-from-file` over hardcoded defaults. GitHub Releases over Supabase Storage (50MB project limit). `url_launcher` added for in-app download. Versioning starts at v0.0.1.
**Next**: Fix BLOCKER-22 (location loading stuck), commit+push, manual Supabase config.

### Session 484 (2026-03-03)
**Work**: Implemented review-submit-auth plan (5 phases, 50 files, 14 new). Dual code review + security audit. Fixed all 12 findings (2 P0, 1 HIGH, 3 MEDIUM, 5 P1, 2 LOW). 2358 tests green.
**Decisions**: `package_info_plus` upgraded ^8→^9 for Android compat. Foreground resume hooks via SyncLifecycleManager. `DailyEntry.getMissingFields()` extracted as model method. Batch submit timestamp returned from repository.
**Next**: Commit+push, deploy Supabase migration, manual Supabase config (refresh token, secure_password_change).

### Session 483 (2026-03-03)
**Work**: Full brainstorm session for review & submit flow + auth session management. Detailed plan written (Rev 1), dual adversarial review (22 findings), plan updated to Rev 2. No code changes.
**Decisions**: Draft-only editor, separate review screen, batch submit with SQLite transaction, `reauth_before` timestamp (not boolean), `flutter_secure_storage` for security timestamps, server-side status transition trigger, `pub_semver` for version comparison (fail-open), 7-day Supabase refresh token.
**Next**: Commit+push pending changes, then implement plan Phase 0–4.

### Session 482 (2026-03-02)
**Work**: Deployed Supabase migration (bid_amount + test_results drop). Removed bid_amount safety net from sync. Fixed config.toml template path. Pre-flight: 166 pass / 3 pre-existing fail.
**Decisions**: Migration deployed via `supabase db push`. Safety net code removed immediately after confirming deployment.
**Next**: Commit+push. Brainstorm fixes for routing, weather, location bugs + save/submit UX design.

### Session 481 (2026-03-02)
**Work**: Implemented fix plan Rev 3 via `/implement` (4 phases + 6 quality gates). 22 files modified. Column stripping, lastSyncTime persistence, non-transient schema errors, orphan SyncService removal, DNS dedup, onSyncComplete once-firing, upscaler revert, bidAmount preservation, BudgetSanityChecker.
**Decisions**: Task 0.5+1.2 combined in Phase 0. bid_amount stripped from _convertForRemote as safety net. Golden fixtures + sync tests deferred. Gate 4 P0 fix: onSyncComplete in catch block.
**Next**: Commit+push, deploy Supabase migrations, remove bid_amount strip after migration.

### Session 479 (2026-03-02)
**Work**: Investigated PDF extraction regression + sync failure using parallel Opus agents. Fixed auth cold-start race. Created adversarial-reviewed fix plan (3 phases). 4 CRITICAL adversarial findings incorporated.
**Decisions**: Revert upscaler (not tune). Remove adapter callback wiring (not suppress flag). Supabase migration required before app deploy.
**Next**: Implement fix plan (Phase 1+2 parallel), commit+push, deploy Supabase migration.

### Session 476 (2026-03-01)
**Work**: Verified live Android extraction matches golden baseline. Created geometry-aware crop upscaler plan with brainstorming + adversarial review. Final plan saved.
**Decisions**: Column-adaptive DPI (continuous curve) over min-width floor or confidence-retry. Formula: `targetDpi = 600 + 300 * max(0, 1 - cropWidth/500)`.
**Next**: Implement plan (4 phases), push 6 commits, enable secure_password_change.

### Session 475 (2026-03-01)
**Work**: Verified BLOCKER-17 fix already in working tree. Created 6 logical commits (auth fixes, UX, security, PDF fixtures). Wiped Windows app data for clean start.
**Decisions**: Layered fix for BLOCKER-17 (clear on sign-out + defense-in-depth empty list on null companyId). tessdata left intact during wipe.
**Next**: PDF extraction investigation, push commits, enable secure_password_change in Supabase.

### Session 474 (2026-03-01)
**Work**: Regenerated PDF golden fixtures (baseline confirmed: 131 items, 0.993 quality, $7.88M exact). Fixed auth cold-start race condition (4 fixes: FIX-1 cached session load, FIX-2 profile skip stub, FIX-3 joinCompany refresh, SEC-8 recovery flag persistence). Discovered BLOCKER-17 stale SQLite.
**Decisions**: Auth timing fix uses sync `_isLoadingProfile=true` before any notifyListeners. Recovery flag persisted via SharedPreferences (not secure storage — acceptable for boolean flag).
**Next**: Fix BLOCKER-17 (wire clearLocalCompanyData), commit all auth fixes, PDF extraction investigation.

### Session 473 (2026-03-01)
**Work**: Reverted kMinCropWidth=500 crop upscaler. Restored all 25 files. Verified 825+81 tests pass, scorecard 68/3/0.
**Decisions**: kMinCropWidth approach needs geometry investigation before reattempt.
**Next**: Regenerate golden fixtures, establish clean baseline.

### Session 472 (2026-03-01)
**Work**: UX fixes (remove cert number, phone formatter). BLOCKER-15 real root cause found (stale profile cache) + fixed with _preflight().
**Decisions**: kMinCropWidth=500 too aggressive. Needs revert before commit.
**Next**: Revert crop upscaler, regenerate fixtures, commit good changes only.

### Session 471 (2026-03-01)
**Work**: Ran `/implement` on onboarding flow fix (BLOCKER-15). 2 phases + 6 quality gates all passed.
**Decisions**: Added `getPendingJoinRequest()` to AuthService. Loading spinner during pending check.
**Next**: E2E device test, commit.

### Session 470 (2026-03-01)
**Work**: Brainstormed BLOCKER-15 via `/brainstorming`. Decided on companyId null check (Option A, no DB migration).
**Next**: `/implement` the onboarding flow fix plan.

### Session 466 (2026-02-28)
**Work**: E2E tested password reset on Samsung S25 Ultra — FAILED. Logged BLOCKER-14.

---

## February 2026

### Session 465 (2026-02-28)
**Work**: Implemented password reset token_hash fix. Code review + security audit. 8 commits on `feat/password-reset-token-hash`.

### Session 464 (2026-02-28)
**Work**: Diagnosed ARM crash on Samsung S25 Ultra. Created build system. Diagnosed PKCE flow_state_not_found bug. Wrote token_hash fix plan.

### Session 462 (2026-02-28)
**Work**: Implemented /implement skill (421-line SKILL.md). Agent cleanup: 9 agents fixed, 4 memory stubs.

### Session 461 (2026-02-27)
**Work**: Created security-agent. Designed /implement skill. Identified 18 cleanup items.

### Session 458 (2026-02-26)
**Work**: Built Claude Code statusline with real Anthropic OAuth usage API data (5h/7d percentages + reset timers). Installed ccusage for weekly token tracking. Daily CSV logging. Attempted Android APK build — discovered flusseract CMake broken with NDK 28.2 (gold linker removed + regex bug).
**Next**: Fix Android build (CMake regex), widget test strategy decision, revert temp changes.

### Session 457 (2026-02-22)
**Work**: Testing strategy analysis. 2 agents reviewed 5+ sessions of failures. Found 10 issues, recommended widget test approach. Fixed SyncOrchestrator.forTesting() harness crash. Added 4 flow definitions + 2 screen registrations. Dashboard verified via harness.
**Next**: Decide on widget test approach, build StubAuthProvider + widget test harness, write 29 tests.

### Session 456 (2026-02-22)
**Work**: E2E testing continued. T-AUTH-04 PASS, T-AUTH-05 PASS (after INSERT policy fix). T-AUTH-06 partial (3 routing bugs found+fixed). Wrong anon key fixed. Session ended mid-rebuild.
**Next**: Full rebuild, verify routing fix, continue E2E from T-AUTH-06 re-verify onward.

### Session 454 (2026-02-22)
**Work**: E2E testing via dart-mcp. Found CRITICAL bug: pre-existing users have no user_profiles row. Fixed with backfill migration. CMake 4.x fix. Testing keys added.
**Next**: Continue E2E testing — relaunch, verify auth fix, test all remaining flows.

### Session 450 (2026-02-22)
**Work**: Merged 3 worktrees, implemented ALL remaining phases (0, 1A, 3, 4, 5, 6). Two review rounds: 15 fixes from review orchestrator + 30 fixes from exhaustive plan audit = 45 total fixes. 312/312 plan items verified.
**Next**: Commit, flutter test, merge/PR, Firebase external setup, Supabase deploy.

### Session 449 (2026-02-22)
**Work**: Implemented Phases 1B/1C, 2, 7, 8 across 3 parallel worktrees. 48+ files, ~1200 lines. 190/190 plan items verified.
**Next**: Merge worktrees, implement remaining phases.

### Session 448 (2026-02-22)
**Work**: Round 5 adversarial review (91 findings, 106 unique IDs). All inlined into plan. Plan is 1,974 lines, clean and unified.
**Next**: Start Phase 1 implementation.

## February 2026

### Session 447 (2026-02-22)
**Work**: Integrated 12 Round-4 review findings (security + continuity) into plan. Plan finalized at 1736 lines.
**Next**: Start Phase 1 implementation.

### Session 446 (2026-02-22)
**Work**: Brainstormed + resolved all 14 CRITICALs. Launched 2nd adversarial review. Resolved 7 security + 20 continuity findings.
**Next**: Start Phase 1.

### Session 445 (2026-02-22)
**Work**: Adversarial architecture review of multi-tenant plan. 40 findings from code-review agent. RLS viewer policies broken, pending users locked out, SQLite migration unsafe, 5 tables missing columns.
**Next**: Brainstorm fixes for CRITICALs, amend plan, then start Phase 1.

### Session 444 (2026-02-22)
**Work**: Brainstormed multi-tenant architecture plan. Audited Supabase (severely behind). Set up Supabase CLI. Wrote + deployed 3 catch-up migrations. Planning agent produced 102-file implementation plan across 8 phases.
**Decisions**: Fleis and Vandenbrink as company, 3 roles, sequential phases, sync-on-close with debounce, full Firebase/FCM.
**Next**: Start Phase 1 (Supabase foundation + Dart models + SQLite v24), get Roberto's auth UUID.

## February 2026

### Session 443 (2026-02-22)
**Work**: Redesigned 20/10 weights as compact 80px inline cards. Convergence-aware display (dim past first Δ≤10g). Auto-select converged reading for calc. Overflow "Add Reading" button when all 5 filled without convergence. Harness fixes for MdotHubScreen.
**Results**: `flutter analyze` clean. Validated via dart-mcp (2-reading, 5-reading, 6-reading overflow scenarios).
**Next**: Run flutter test, fix BUG-1/MINOR-2/MINOR-3, commit changes.

### Session 442 (2026-02-22)
**Work**: Fixed 20/10 weights flow — added `_weightsConfirmed` gate so calc only fires after user confirms weights are done. Fields lock after confirmation, "Edit Weights" to unlock. Max readings 15→5. 4 files changed.
**Results**: `flutter analyze` clean, `flutter test` +2341 all passed.
**Next**: Fix BUG-1/MINOR-2/MINOR-3 in forms; hot reload + UX pass on hub with weights gate.

### Session 439 (2026-02-22)
**Work**: Brainstormed 0582B design plan into detailed 7-phase implementation plan. 3 Explore agents gathered codebase context. 4 architectural decisions made via structured questioning. Full widget hierarchy, state design, provider wiring, file plan, acceptance criteria, and testing keys specified.
**Decisions**: Inline everything (delete 4 old screens). Single StatefulWidget hub. Custom FormAccordion (no ExpansionTile). Auto-advance after SEND. Multi-test stays expanded.
**Next**: Build Phase 1 (scaffold + accordion + pill bar), then Phases 2-7.

## February 2026

### Session 438 (2026-02-22)
**Work**: Prototyped 0582B hub screen via html-sync + Playwright. Created 3 design alternatives (Tabbed, Stepper, Accordion). Option C (Accordion Dashboard) selected and refined. Built full 5-step flow mockup + side-by-side comparison vs current. Updated design plan.
**Decisions**: Option C accordion chosen. One section expanded at a time. Summary tiles on collapsed sections. Status pill bar. All buttons "SEND TO FORM". 48dp touch targets. Completion banner with + New Test / Preview PDF.
**Next**: Build accordion dashboard. Fix 3 bugs from Session 435.

### Session 437 (2026-02-21)
**Work**: Brainstormed 0582B hub screen design. Reviewed MCP token cost model. Created card-based hub design plan replacing FormFillScreen with 4 always-visible cards (header, quick test, proctor, weights).
**Decisions**: Hub replaces FormFillScreen. All fields visible. Header collapses after confirm. Grouped field layout. Last-sent compact summary + edit.
**Next**: Build hub screen starting with header card. Fix 3 bugs from Session 435.

### Session 436 (2026-02-21)
**Work**: Set up UI prototyping toolkit. Researched browser-control MCP servers, configured Playwright + HTML Sync, created Beer CSS workflow guide, rules, updated CLAUDE.md + memory.
**Decisions**: Playwright (vision mode) + HTML Sync Server + Beer CSS v4 for rapid browser mockups. Mockups decoupled from Flutter code.
**Next**: Restart CC, smoke test prototyping loop, prototype 0582B form, fix 3 bugs from Session 435.

### Session 435 (2026-02-21)
**Work**: Full 0582B flow harness test (5 screens) via dart-mcp + flutter_driver. Verified proctor entry, quick test, weights entry, form save. Found 3 issues (1 race condition bug, 2 minor).
**Results**: All screens pass end-to-end. Test report at `.claude/test-results/2026-02-21-0582b-flow-harness-test.md`. Defects filed in `.claude/defects/_defects-forms.md`.
**Next**: Fix BUG-1 FormsListScreen race condition, update architecture.md, start project-based architecture.

### Session 433 (2026-02-21)
**Work**: Full project directory audit and cleanup. 5 Explore agents audited root/lib/test/tools/.claude/config dirs. 12+ agents executed cleanup across 6 phases. Recovered ~5GB, deleted 83K+ files, fixed 106 analyze issues→0, reorganized tests, updated all docs.
**Results**: `flutter analyze` 0 issues; `flutter test` +2343 all passed; 8 app commits + 3 .claude commits pushed.
**Next**: Manual MCP harness pass, update rules/architecture.md feature count.

### Session 432 (2026-02-21)
**Work**: Fully implemented widget test harness plan via implementation/review agents. Added in-memory DB testing path, harness runtime, registry/providers/seeding/stubs, 0582B keys, docs, and validation artifact.
**Results**: Review findings resolved; `flutter analyze` (changed files) clean; full `flutter test` passed (`+2343 -0`).
**Next**: Manual MCP interaction sweep on harness screens and PR creation/merge.

### Session 431 (2026-02-21)
**Work**: Brainstormed widget test harness implementation readiness. Audited codebase, found 6 gaps in original plan. Revised design doc with in-memory SQLite approach, two-tier seeding, onException router, 26-screen registry.
**Decisions**: Real stack over mocks, explicit registry, DatabaseService.forTesting(), two-tier seeding, onException stub router.
**Next**: Merge toolbox PR, implement harness Phases 0-1.

### Session 430 (2026-02-21)
**Work**: Planned toolbox feature split with brainstorming skill. Created comprehensive plan for splitting 4 sub-features out of toolbox into independent feature modules.
**Decisions**: Phase-based split (calculator → todos → gallery → forms → toolbox shell). Each gets own data/presentation layers.
**Next**: Implement toolbox split plan.

### Session 429 (2026-02-21)
**Work**: Fully implemented toolbox split plan with implementation + review agents. Moved calculator/todos/gallery/forms into independent feature folders and converted toolbox to launcher shell only. Added targeted EntryFormCard tests and fixed stale forms doc path.
**Results**: Full `flutter test` passed; migration-scope analyze clean; second review pass closed with no findings.
**Next**: Code quality review and cleanup.

### Session 428 (2026-02-21)
**Work**: Resolved all 6 open harness design questions. Confirmed dart-mcp launch_app lacks --dart-define. Pivoted to config file approach. Wrote 6-phase implementation plan.
**Decisions**: Config file selection, lib/test_harness.dart entry point, universal mock superset, stub GoRouter, start 0582B + design universal.
**Next**: Implement harness (Phases 1-6).

### Session 426 (2026-02-21)
**Work**: Fully implemented 0582B redesign plan (all 6 phases) via implementation agents, including calculator/data-model/schema migration, new quick-entry/viewer screens, PDF mapping/polish, and daily entry integration.
**Results**: Agent review loop completed with one high-severity bug fixed; full suite stabilized to `flutter test` => `+2364 -0`.
**Next**: Targeted UX validation + legacy-response migration/backfill decision.

### Session 424 (2026-02-21)
**Work**: Brainstormed 0582B UI redesign. Made 8 design decisions. Wrote comprehensive plan v2 with integrated OnePointCalculator, 3 quick-entry screens, 6 implementation phases.
**Decisions**: Michigan Cone only, auto-compute MDD/OMC, 3 entry screens, per-proctor 20/10 weights, proctor chip bar.
**Next**: Implement Phase 1 (OnePointCalculator + Data Model).

### Session 423 (2026-02-21)
**Work**: Reverse-engineered MDOT Construction Density APK. Decoded exact algorithm for both T-99 (27-row table) and Cone (21-row table) charts.
**Breakthroughs**: Algorithm is piecewise linear interpolation + polynomial, NOT physics. Verified 14/14 exact match.
**Next**: Plan 0582B UI redesign (done in 424).

### Session 422 (2026-02-21)
**Work**: Implemented PDF pipeline refactor plan via multiple agents (P-01..P-13), completed code-review loop, fixed M&P progress regression.
**Results**: PDF scope tests green; saturation-line model ~85% S_opt discovered.
**Next**: Reverse-engineer calculator (done in 423).

### Session 421 (2026-02-21)
**Work**: Brainstormed Gaussian model + harness design. Obtained MDOT calculator app. Collected 14 ground truth data points.
**Next**: Research published equation (superseded by APK decompilation).

### Session 419 (2026-02-21)
**Work**: One-Point Chart Digitization brainstorm. Extracted boundary data, designed hybrid algorithm.
**Next**: Python prototype (done in 420).

### Session 417 (2026-02-21)
**Work**: Full 6-phase entries refactor. Extracted controllers/widgets/section islands and PdfDataBuilder. Applied critical code-review fixes.
**Next**: Wire PdfDataBuilder, adopt overlay in HomeScreen, continue 0582B form work.

### Session 414 (2026-02-22)
**Work**: Fixed route persistence system — allowlist filter, error recovery UI on FormFillScreen.
**Next**: Continue 0582B redesign.

### Session 413 (2026-02-21)
**Work**: Completed Phase 1 teardown for legacy form-import/registry artifacts.
**Next**: Continue 0582B redesign.

### Session 412 (2026-02-21)
**Work**: Started implementation from 0582B redesign plan. Added export preview gating + preview invalidation on edits, updated leave flow.
**Next**: Phase 1 teardown and Phase 2 schema/model migration.

### Session 409 (2026-02-20)
**Work**: Diagnosed Marionette root cause (empty render tree on Windows). Removed Marionette entirely. Migrated to dart-mcp only. Verified widget tree works. Added `native_assets/windows` build fix to docs.
**Decisions**: dart-mcp replaces Marionette permanently. No third-party UI automation packages.
**Next**: Walk through 0582b form via dart-mcp.

### Session 408 (2026-02-20)
**Work**: Completed Marionette Journeys 6-8. Inline editing (activities, contractors work; temp broken). Quantities screen had 2 High bugs (search + sort). Archive/unarchive, PDF export, calendar views passed.
**Decisions**: Log search/sort as High priority. Temp edit needs investigation.
**Next**: Fix P50 (numeric sort), fix P49 (search filter), fix P34 (temp inline save), fix P15 (Gallery/To-Do's missing).

### Session 407 (2026-02-20)
**Work**: Marionette UI testing — completed Journeys 3-5, started Journey 6. Standardized MCP launch procedure in CLAUDE.md. Found 9 new issues (P5-P30).
**Decisions**: Use `dart-mcp launch_app` (not `flutter run` via bash).
**Next**: Continue Journey 6 (inline editing), then Journeys 7 and 8.

### Session 406 (2026-02-20)
**Work**: Strengthened M&P ground truth with full body text. Scorecard 20/20 OK. BLOCKER-12 fully resolved.
**Decisions**: Full body (no truncation) in fixtures.
**Next**: Verify bodies against native PDF text.

### Session 404 (2026-02-20)
**Work**: Researched anchor-based PDF parsing. Brainstormed metadata-driven two-point anchor. Wrote plan.
**Decisions**: Two-point anchor (regex + known bid item numbers).
**Plan**: `.claude/plans/2026-02-20-mp-parser-anchor-rewrite.md`

### Session 403 (2026-02-20)
**Work**: Built M&P testing harness (fixture generator + 14-metric scorecard + GT traces). Diagnosed "4 items" bug.

### Session 402 (2026-02-20)
**Work**: Discovered `Stop-Process -Name 'dart'` kills MCP servers. Decided hybrid testing approach.

### Session 401 (2026-02-20)
**Work**: Attempted M&P E2E test. Fixed Marionette MCP infra.

### Session 400 (2026-02-20)
**Work**: Dual code review, resolved BLOCKER-11, fixed 5 bugs, verified tests green.

### Session 399 (2026-02-20)
**Work**: Implemented full M&P extraction/enrichment flow. Code reviewed and bug-fixed.
**Plan**: `.claude/plans/2026-02-20-mp-extraction-service.md`

### Session 397 (2026-02-19)
**Work**: Started executing Marionette UI test journeys. Completed Journey 1 and partial Journey 2. Found 4 issues (P1-P4). Marionette crashed during PDF import.
**Findings**: `.claude/test-results/2026-02-19-marionette-findings.md`

### Session 396 (2026-02-19)
**Work**: Brainstormed and designed comprehensive Marionette UI test suite. 8 user journeys, ~340 steps.

### Session 394 (2026-02-19)
**Work**: Implemented 100% extraction plan (math backsolve + zero-conf sentinel + scorecard hardening). 5 commits pushed.
**Scorecard**: 72 metrics: 68 OK / 3 LOW / 0 BUG. Quality 0.993. 131/131 GT match. 850/850 tests green.

### Session 391 (2026-02-19)
**Work**: Regenerated fixtures. Ran scorecard (56 OK/2 LOW/1 BUG). Dispatched 3 agents to audit all 62 metrics. Found 12 silently passing, 7 missing coverage, 1 metric bug (B1). Wrote comprehensive hardening plan covering dynamic pattern classification, 15 threshold tightenings, and 4 new metrics.
**Scorecard**: 56 OK / 2 LOW / 1 BUG. Quality 0.990. 131/131 items, $7,882,926.73 exact.
**Next**: Implement `.claude/plans/2026-02-19-harden-scorecard-metrics.md`.

### Session 390 (2026-02-19)
**Work**: Implemented DPI-target upscaling + observability end-to-end using agents. Completed A1-A4 and B1-B5.
**Next**: Regenerate fixtures, validate scorecard baseline.

### Session 389 (2026-02-19)
**Work**: Brainstorming session. Decided on DPI-target approach (targetDpi=600). Audited stage trace for silent failures (7 found). Designed 5 observability metrics.
**Next**: Implement DPI-target upscaling.

### Session 387 (2026-02-19)
**Work**: Implemented low-confidence numeric re-OCR fallback + whitelist leakage fix. Added 8 tests. Extraction green (+855).

### Session 385 (2026-02-19)
**Work**: Implemented OpenCV grid line removal. Removed legacy inset logic. Extraction green (+847).

### Session 382 (2026-02-19)
**Work**: Deep investigation of 7 missing GT items.

### Session 380 (2026-02-19)
**Work**: Rigorous multi-agent investigation proved drift-correction frame mismatch.

### Session 379 (2026-02-19)
**Work**: Root-cause confirmation for pipe artifacts tied to inset frame mismatch.

### Session 376 (2026-02-18)
**Work**: Systematic debugging of bid_amount gap identified whitespace inset/cropping path as root cause candidate; fix attempts were reverted and blocker documented.

### Session 375 (2026-02-18)
**Work**: Implemented full Row Parser V3 plan, regenerated fixtures, removed V2 parser, and ran review/fix loops.
**Results**: Stage trace 54 OK / 1 LOW / 0 BUG, quality 0.977, extraction suite passing.

### Session 374 (2026-02-18)
**Work**: Unblocked fixture regen, validated 15-item recovery, traced remaining gap root causes, planned Row Parser V3 rewrite.

### Session 373 (2026-02-18)
**Work**: Implemented 3-fix 15-item recovery plan and hardening tests.

### Session 372 (2026-02-18)
**Work**: Systematic debugging of upstream misclassification; created 3-fix plan.

### Session 370 (2026-02-18)
**Work**: Revised blocker impact. 9 uncategorized items traced to boilerplate misclassification. Created fix-and-observe plan.

### Session 369 (2026-02-18)
**Work**: Root cause reconciliation. A1 benign, A2 is the problem. Simpler single fix chosen.

### Session 368 (2026-02-18)
**Work**: 3 parallel agents confirmed ROOT CAUSE: scan starts at grid line center, only sees half width.

### Session 366 (2026-02-18)
**Work**: Regenerated fixtures. Scorecard: 41 OK / 8 LOW / 1 BUG.

### Session 365 (2026-02-18)
**Work**: Header Consolidation stage implementation. Suite green (+837).

### Session 360 (2026-02-16)
**Work**: Ran scorecard (22 OK / 4 LOW / 22 BUG). Brainstormed Row Classifier V3 + Column Label fix and wrote detailed implementation plan.
**Decisions**: Rewrite classifier path (V3), improve column semantics, and prioritize upstream fixes before downstream tuning.
**Next**: Implement planned classifier/label remediation and regenerate fixtures.

### Session 359 (2026-02-16)
**Work**: Regenerated fixtures (+4.6% quality, +18 GT matches). Full pipeline diagnostic. Added scorecard test to stage trace. Identified 2 upstream bugs: 4A row classification and 4C column labels.
**Decisions**: Fix upstream stages to 100% before moving downstream.
**Next**: Fix 4A row classification, 4C column labels, row merging.

### Session 357 (2026-02-16)
**Work**: Root cause analysis of 5 problems -> Problem A (red bg in CropUpscaler) is the single root cause. Fixed with `numChannels: resized.numChannels`. Regenerated fixtures. Pipeline: 137 parsed items, 87/131 GT matches (66%), quality 0.748.
**Decisions**: Problem A fixed. B (DPI 300) is intentional. C (source_dpi) is metadata-only. D+E resolved by fixing A.
**Next**: Row merging, item# OCR noise cleanup, row classification tuning.

### Session 355 (2026-02-16)
**Work**: Systematic debugging of stage trace. Root cause: PSM 7 on full-row strips can't handle grid lines.
**Decisions**: Cell-level OCR is the fix.
**Next**: Implement cell-level OCR (was already done)

---

## February 2026

### Session 354 (2026-02-16)
**Work**: Regenerated fixtures with ROW-STRIP code. 27 items, 26/131 GT matches (20%).
**Decisions**: Row classifier is #1 blocker.

### Session 353 (2026-02-16)
**Work**: Implemented diagnostic image capture system. 14 JSON fixtures, onDiagnosticImage callback.
**Decisions**: Raw images only. Images gitignored.

### Session 352 (2026-02-15)
**Work**: Traced pipeline failure cascade. 0 header rows → 0 regions → everything empty.
**Decisions**: Synthetic regions is Priority 1.

### Session 350 (2026-02-15)
**Work**: Deep OCR brainstorming. Traced actual data through pipeline. Researched community practices, cross-platform OCR, cloud OCR pricing, opencv_dart, textify. Established 3-step escalation path.
**Decisions**: Row-strip OCR first (zero deps). opencv_dart if needed. Cloud Vision as last resort.

### Session 349 (2026-02-15)
**Work**: Code review (3 fixes). Fixture regen revealed 0 regions. Brainstormed grid-aware region detection (Options B/C).

### Session 348 (2026-02-15)
**Work**: Fixed column semantic mapping. Margin detection, anchor-relative inference, content validation. 324 tests pass.

### Session 347 (2026-02-15)
**Work**: Verified cell crop upscaling complete. Upscaling insufficient for narrow columns.

### Session 346 (2026-02-15)
**Work**: Fixed getLuminance bug. Grid detection 0→6 pages. Luminance diagnostic test.

### Session 345 (2026-02-15)
**Work**: Grid line detection implementation. Phase 1+2 code reviewed and fixed.

### Session 344 (2026-02-15)
**Work**: Brainstormed Phase 3 plan (ColumnDetectorV2 grid integration). 7 sections, ~10 design decisions. Explored column detector (1,158 lines), reviewed all test/golden patterns. Identified page 1 grid misclassification root cause.
**Decisions**: Option D (grid boundaries + keywords). Per-page independent. Diagnostic mode (both paths run). Anchor validation-only. Density filtering for page 1. Replace stub entirely.
**Next**: 1) Implement Phase 3 (A: grid fix, B: Layer 0, C: goldens) 2) Implement Phase 4 (pipeline wiring) 3) Benchmark accuracy

### Session 343 (2026-02-15)
**Work**: Code reviewed Phase 1 + Phase 2 implementations (2 parallel agents). Fixed 6 issues: mock type safety (dynamic→typed), DRY _median→MathUtils.median, pre-sort horizontal lines, remove redundant cast, add stageConfidence doc. 717 tests pass.
**Decisions**: All mock overrides must use typed params (not dynamic). Shared MathUtils.median() is canonical median impl.
**Next**: 1) Implement Phase 3 (ColumnDetectorV2 grid integration) 2) Implement Phase 4 (pipeline wiring + fixtures) 3) Benchmark accuracy

### Session 342 (2026-02-14)
**Work**: Brainstormed Phase 2 plan — cell-level cropping for TextRecognizerV2. Reviewed actual PDF, audited all 52 test files. Escalated from row to cell cropping for 100% accuracy. 10 design decisions, 19 new tests, 3 source files.
**Decisions**: Cell-level crop (not row). PSM 7/6 adaptive. Grid-only OCR (drop boilerplate). No vertical line erasing. 2px padding. Sequential engine. PSM 4 fallback.
**Next**: 1) Implement Phase 1 (GridLineDetector) 2) Implement Phase 2 (cell cropping) 3) Phases 3-4 (column integration + wiring)

---

## February 2026

### Session 341 (2026-02-14)
**Work**: Brainstormed Phase 1 implementation plan for GridLineDetector. Reviewed all stage patterns (models, tests, mocks, fixtures, diagnostics). Made 7 design decisions. Exported full plan with 17 tests, 9 files (3 new, 6 modified).
**Decisions**: Plain name (no V2). compute() isolate. GridLines wrapper. toMap/fromMap included. 17 tests. All infrastructure in Phase 1. Fixture diagnostic only.
**Next**: 1) Implement Phase 1 per plan 2) Continue Phases 2-4 3) Regenerate fixtures + validate accuracy

### Session 340 (2026-02-14)
**Work**: Fresh baseline (0/131 match, $0). Root-caused OCR garbage to PSM=6 on table pages. Researched PSM modes. Designed grid line detection + row-level OCR plan (4 phases).
**Decisions**: OCR-only (no native text — CMap corruption). Tier 2: grid line detection → row cropping → PSM 7. Grid vertical lines feed column detection at 0.95 confidence. PSM 4 fallback for non-grid pages.
**Next**: 1) Implement grid line detection plan (phases 1-4) 2) Regenerate fixtures 3) Validate accuracy improvement

## February 2026

### Session 339 (2026-02-14)
**Work**: Status audit — verified OCR migration Phases 2-4 already implemented, PRD R1-R6 mostly complete. Moved 3 completed plans. Updated state files.
**Decisions**: Focus on pipeline accuracy improvement as primary goal.

### Session 337 (2026-02-14)
**Work**: Implemented full V2 extraction pipeline refactoring (28 findings, 7 phases). Created 6 new shared files, modified 30+ files, ~2,500 lines saved. Fixed 3 correctness bugs, eliminated ~500 lines of duplicated prod code, moved ~1,800 lines of dead tests.
**Decisions**: `QualityThresholds` as single source of truth for score thresholds. `TextQualityAnalyzer` mixin for shared corruption detection. `Duration?` replaces mutable `Stopwatch` on `PipelineContext`. Shared mock stages for test reuse.

### Session 338 (2026-02-14)
**Work**: Code review cleanup — 3 parallel review agents found 21 issues. Executed 13-step plan: deleted deprecated dirs, fixed dead code, sentinel pattern for copyWith, epsilon doubles, import normalization, stage name migration, ResultConverter bug fix.
**Decisions**: Skip models barrel cleanup (30+ file blast radius). Delete deprecated dirs entirely (git preserves history). Use StageNames constants everywhere (no substring matching).

### Session 336 (2026-02-14)
**Work**: Full .claude/ reference integrity audit. Ran 4 code-review agents (2 audit + 2 verification). Fixed 42 broken refs across 28 files. Committed in 5 groups and pushed.

### Session 335 (2026-02-13)
**Work**: Ran 3 parallel code-review agents on `.claude/` directory. Fixed ~90+ broken refs, archived 10 stale files, renamed 3 constraint files, deleted _defects.md redirect, fixed all agent/state/constraint file paths.

### Session 333 (2026-02-13)
**Work**: Tested `/resume-session` — removed 4-path intent questions (zero-question flow). Audited `.claude/` directory: found 16 broken refs, 9 orphans, 3 outdated items. Designed 3 native Claude Code hooks (post-edit analyzer, doc staleness, sub-agent pre-flight). Wrote Phase 4 implementation plan.
**Decisions**: Zero-question resume (user's first message = intent). Native hooks over manual scripts. Blocking PostToolUse analyzer. Hook-enforced doc updates (no dedicated docs agent). No PreToolUse gates (V1 patterns moot).

---

### Session 332 (2026-02-13)
**Work**: Fixed 16 issues in `.claude/` directory config across 5 phases. Rewrote session skills (no git), fixed broken references, wired agent feature_docs, created 13 per-feature defect files, migrated existing defects.
**Decisions**: Per-feature defects in `.claude/defects/`, overviews-only for multi-feature agents (token efficiency), original _defects.md kept as redirect.

---

### Session 330 (2026-02-12)
**Work**: Enhanced CMap corruption detection in Stage 0 DocumentAnalyzer. Added mixed-case pattern detection + currency symbol validation. All 6 Springfield pages now route to OCR.

---

## February 2026

### Session 405 (2026-02-20)
Implemented M&P parser anchor rewrite (BLOCKER-12). 25/25 tests green, 0 analysis issues.

### Session 329 (2026-02-12)
Git history restructuring — 10 clean commits pushed to main.

### Session 328 (2026-02-12)
R7 brainstorming. Ground truth verification (131 items, $7,882,926.73). 3-layer golden test architecture.

### Session 327 (2026-02-11)
R5+R6 implementation. 9 golden fixtures. Pipeline quality baseline.

### Session 324 (2026-02-11)
Phase 5 complete — Stages 4A-4E fully implemented, PostProcessorV2 rewritten standalone, pipeline orchestrator expanded 0-6, all legacy imports eliminated. 619 extraction tests pass.

### Session 321 (2026-02-08)
Implemented full 5-PR plan for robust two-line header detection + per-page column recovery. 1431 PDF tests pass, 704 table extraction, 0 regressions.

### Session 320 (2026-02-08)
Diagnosed jumbled Springfield data via pipeline dumps. Found 2 bugs: multi-line header + hardcoded empty header elements.

### Session 319 (2026-02-08)
Runtime Pipeline Dumper Integration — wired PipelineFileSink into PdfImportService. 689 table extraction tests pass. 22 dumper tests.

### Session 313 (2026-02-07)
Implemented all 4 parts of OCR Empty Page + Encoding Corruption fix. RGBA→grayscale, fail-parse, force re-parse, thread encoding flag through 28 call sites. Commit: d808e01.

### Session 311 (2026-02-07)
Encoding-aware currency normalization (z→7, e→3, fail on unmappable), debug image saving, PSM 11 fallback for empty OCR pages. 1386 PDF tests pass. 13 new encoding tests.

### Session 310 (2026-02-07)
Fixed OCR "Empty page" failures — threaded DPI to Tesseract via `user_defined_dpi`, eliminated double recognition in `recognizeWithConfidence`. 1373 PDF tests pass. Commit: `c713c77`.

### Session 307 (2026-02-06)
Font encoding investigation. Added diagnostic logging, ran Springfield PDF, discovered multi-page corruption. Pages 1-4 mild, page 6 catastrophic. OCR fallback needed.

### Session 306 (2026-02-06)
First real-world PDF test of native text pipeline. Fixed 3 bugs: empty Uint8List crash, element count thresholds, data row lookahead.

### Session 305 (2026-02-06)
Implemented all 3 phases of PDF Extraction Pipeline Redesign. Native text first, OCR fallback.

### Session 304 (2026-02-06)
Brainstorming session continuing pipeline redesign plan.

### Session 301 (2026-02-06)
Phase 1: Removed binarization from image preprocessing. 202 OCR + 577 PDF tests pass. Commit: `836b856`.

### Session 299 (2026-02-06)
Table Structure Analyzer v2.1 Phases 5+6 (Parser Integration + Regression Guard). 566/567 tests pass. Commit: `0a4cbb0`.

### Session 298 (2026-02-06)
Implemented Phase 3 (Anchor-Based Column Correction + Gridline Quality Scoring) and Phase 4 (Post-Processing Math Validation) from PDF Table Structure Analyzer v2.1 plan. Commit: `eafae91`.

### Session 297 (2026-02-05)
Implemented Phase 1 (Row Classifier) and Phase 2 (Table Region Detector) from PDF Table Structure Analyzer v2.1 plan. RowClassification model (6 row types), RowClassifier with Phase 1A/1B. TableRegionDetector with two-pass linear scan, cross-page header confirmation, multi-table detection. 523/524 tests pass.

### Session 291 (2026-02-05)
Completed missing items from pdf-extraction-regression-recovery-plan.md: build metadata, preprocessing fallback, re-OCR source logging, deprecated preprocessLightweight(), expanded cleanOcrArtifacts, header primary keyword gating, detailed header-element logging, batch-level gating for column shifts.

### Session 289 (2026-02-05)
Implemented full 6-phase PDF extraction regression recovery plan via parallel agents. 25 files modified (13 production + 12 test), +3294/-240 lines. Commits: app `1b3991f`, config `771fb49`. Tests: 690/690 pass (482 table_extraction + 202 OCR + 6 debug_logger).

### Session 288 (2026-02-05)
Pipeline hardening Phases 2-3: Density gating, word-boundary matching, column bootstrapping. Commits pending (superseded by Session 289).

### Session 287 (2026-02-05)
Root cause analysis of PDF extraction pipeline (8 root causes). Created 6-phase hardening plan. Completed Phase 1 (observability logging). Commits pending.

### Session 286 (2026-02-04)
Tested Springfield PDF — no improvement (85/131). Root cause: TableLocator startY at boilerplate. Created header-detection-hardening-plan.md. Commits pending.

### Session 285 (2026-02-04)
Systematic debugging of Springfield extraction (87/131). Found root cause: 11 headerRowYPositions. Applied 3 fixes. Commits pending (7 modified files).

### Session 284 (2026-02-04)
Springfield PDF column detection improvements: 8 fixes, backwards OCR detection, comprehensive logging. Got to 4/6 keywords, 87/131 items. Commits pending (23 modified files).

### Session 280 (2026-02-04)
Flusseract OCR Migration Phases 4-6: OCR quality safeguards (21 config tests), legacy cleanup (stale ML Kit refs removed, ParserType renamed), performance hardening (pooled disposal fix). 200+ OCR tests pass. `ed267db`

### Session 281 (2026-02-04)
Windows OCR Accuracy Fix Phases 1-3: PNG format for all platforms, adaptive DPI, lightweight preprocessing. Code review 7.5/10.

### Session 331 (2026-02-12)
OCR-only pipeline migration Phase 1. Designed & approved plan via brainstorming. Deprecated 3 native extraction files. Created `DocumentQualityProfiler` + `ElementValidator`. Refactored `ExtractionPipeline` (removed Stage 2A, fixed re-extraction loop). Updated all test mocks/imports. Zero analyze errors.

### Session 282 (2026-02-04)
Springfield PDF extraction debugging: Windows preprocessing skipped binarization. Full preprocessing on all platforms, no-item-number regex, TableLocator improvements (lowered kMinHeaderKeywords to 2, multi-row header detection).

### Session 283 (2026-02-04)
Comprehensive app-wide debug logging: DebugLogger with 9 category-specific log files. Integrated across main.dart, ocr, sync, database, table_extractor. 5 tests pass.

### Session 277 (2026-02-04)
Implemented Tesseract OCR Migration Plan Phases 1-3 using pdf-agents. Phase 1: OCR Abstraction Layer. Phase 2: Tesseract Dependencies. Phase 3: Tesseract Adapter. 95 OCR tests pass. `17a0773`

### Session 276 (2026-02-04)
Implemented PDF Post-Processing Accuracy Plan (5 phases) using pdf-agents with TDD. PostProcessEngine scaffolding, normalization + type enforcement, consistency & inference, split/multi-value repairs, dedupe + sequencing. 182 new tests. `6a0a910`

### Session 275 (2026-02-03)
Implemented PRs 4-6 from Table-Aware PDF Extraction V3 Completion. PR4: Progress UI Wiring. PR5: Integration Tests + Fixtures. PR6: Cleanup + Deprecation. 787 PDF tests pass. `a22c87d`

### Session 274 (2026-02-03)
Implemented PRs 1-3 from Table-Aware PDF Extraction V3 Completion. PR1: Column naming + dimension fix. PR2: Cell-level re-OCR. PR3: Row boundary detection. 218 tests pass. `2bc588e`, `cbb0f8c`

### Session 273 (2026-02-03)
Implemented PRs 9-10 from Table-Aware PDF Extraction V3. PR9: UI integration (PdfImportProgressDialog). PR10: Cleanup & polish (deprecated OcrRowReconstructor, diagnostic logging). `db11078`

### Session 272 (2026-02-03)
Implemented PRs 7-8 from Table-Aware PDF Extraction V3. PR7: TableRowParser (cell-to-typed-field parsing, confidence scoring). PR8: TableExtractor orchestrator (4-stage pipeline). 179 tests pass. `7eeb531`

### Session 271 (2026-02-02)
Implemented PRs 5-6 from Table-Aware PDF Extraction V3. PR5: ColumnDetector unified orchestrator. PR6: CellExtractor with recognizeRegion(). 35 new tests. `e7479a4`

### Session 252 (2026-02-01)
Implemented 5 skills (21 files): brainstorming, systematic-debugging, TDD, verification-before-completion, interface-design. Updated 8 agents with skill references.

### Session 247 (2026-02-01)
Context Management Phases 6-11 - Consolidated rules, updated CLAUDE.md files, rewrote commands, updated 8 agents with workflow markers, deleted old folders.

### Session 246 (2026-02-01)
Context Management Phases 1-5 - Created autoload/, rules/pdf/, rules/sync/, rules/database/, rules/testing/, backlogged-plans/. Moved _state.md, _defects.md, _tech-stack.md to autoload/.

### Session 245 (2026-02-01)
Context Management System Redesign - comprehensive planning session. Created 14-phase plan. No commits (planning only).

### Session 243 (2026-02-01)
Context optimization v2 complete - verified @ references, extracted 5 defect patterns from history. No commits (documentation only).

### Session 241 (2026-01-31)
Phase 7 - Patrol config/docs alignment (README update, patrol.yaml cleanup). `6189ae8`

### Session 240 (2026-01-31)
Session state management and archive rotation.

### Session 239 (2026-01-31)
Phase 6 - Test cleanup: unused imports, dead variables, async safety in tests.

### Session 238 (2026-01-31)
Phase 3 - Deprecated Flutter APIs: WillPopScope to PopScope, withOpacity to withValues. `3ba5f38`

### Session 237 (2026-01-30)
Phase 2 (29 unused imports) + Phase 9 (root logs cleanup) + code review. `e03e8a7`

### Session 236 (2026-01-30)
Phase 1 CRITICAL - Fixed test_bundle.dart for Patrol v4 (patrol_cli 3.11.0 to 4.0.2). `4efc7ff`

### Session 235 (2026-01-30)
Created analyzer cleanup plan for 157 issues. No commits (planning).

### Session 234 (2026-01-29)
Stages 8-10: Supabase ^2.12.0, Calendar ^3.2.0, Patrol ^4.1.0 migration. `c6bf403`, `cf0d6a0`, `e7c922a`

### Session 233 (2026-01-29)
Stages 6-7: PDF Stack (Syncfusion v32), Navigation (go_router v17). `47b5a00`

### Session 232 (2026-01-28)
Stage 5: Files, Media, Pickers - file_picker ^10.3.10, image_picker ^1.2.1. `0fb437d`

### Session 231 (2026-01-28)
Stage 4: Location/Permissions - geolocator ^14, geocoding ^4, permission_handler ^12. `3fe1058`

### Session 230 (2026-01-28)
Stage 3: Networking - connectivity_plus ^7, http ^1.6. `e392d3e`

### Session 229 (2026-01-27)
Stage 2: State/Storage - provider, shared_preferences, flutter_secure_storage v10. `5a8f1bd`

### Session 228 (2026-01-27)
Stages 0-1: Toolchain baseline + low-risk core updates (8 deps). `bab9ae1`, `ef2d00b`

### Session 227 (2026-01-26)
Dependency modernization research + created 10-stage upgrade plan. No commits.

### Session 226 (2026-01-26)
Phase 4: Quality gates + scanned PDF detection in parser. `0c94e42`

### Session 224 (2026-01-25)
Phase 3: Description cap (150 chars) + BoilerplateDetector class. `d1c9270`

### Session 222 (2026-01-24)
Phase 1a-1b: Adaptive clustering + multi-page header detection in ColumnLayoutParser. `e30debe`

### Session 221 (2026-01-24)
Phase 0: DiagnosticsMetadata, DiagnosticsExporter, test fixtures. `ab2c8e0`

### Session 220 (2026-01-23)
Phase 6: ClumpedTextParser integration into fallback chain + code review fixes. `57807d6`, `5658a13`

### Session 219 (2026-01-23)
Phase 5: ClumpedTextParser end-to-end parser (214 tests). `701e26c`

### Session 218 (2026-01-22)
Phase 4: ParsedRowData model + RowStateMachine (58 tests). `8b991b9`

### Session 217 (2026-01-22)
Phase 3: TokenClassifier with context-aware classification (84 tests). `8ca8047`

### Session 216 (2026-01-21)
Phase 2: TextNormalizer for clumped text repair (39 tests). `590c8dd`

### Session 215 (2026-01-21)
Phase 1: ParserDiagnostics + extractRawText shared helper. `9ad11ca`

### Session 214 (2026-01-20)
Created Clumped Text PDF Parser plan + fixed project_setup_screen build error. `bf08638`

### Session 213 (2026-01-20)
Phase 7-8: Addendum handling + MeasurementSpecPreviewScreen. `804aed4`

### Session 212 (2026-01-19)
Phase 6: Preview UI - confidence indicators, warning banners, needsReview highlight. `d420832`

### Session 210 (2026-01-18)
Phase 4: DuplicateStrategy enum + ImportBatchResult + batch import. `86eecb5`

### Session 208 (2026-01-17)
Phase 1: ParsedBidItem model with confidence/warnings + PdfImportResult update. `ea246d0`

### Session 207 (2026-01-17)
3 form preview fixes: hash update, test number position, composite column. `d3b9fe6`

### Session 206 (2026-01-16)
Phase 4: Live preview fix - onFieldChanged updates responseData. `366e8fe`

### Session 205 (2026-01-16)
Phase 3: 0582B form restructure with tableRowConfig + DensityGroupedEntrySection. `5148e96`

### Session 204 (2026-01-15)
Phase 2: Added Start New Form button to report screen. `1a7fa33`

### Session 203 (2026-01-15)
Phase 1: Changed filter toggle default to OFF in form_fill_screen. `6303ffb`

### Session 202 (2026-01-14)
Tested Windows app, identified 4 autofill issues, created plan. No commits.

### Session 201 (2026-01-14)
Form Completion Debug v2: isInitializing flag + verbose debug logging. `fb158a3`

### Session 200 (2026-01-13)
Investigated blank screen + autofill issues, identified race condition. No commits.

### Session 199 (2026-01-13)
Form Completion Debug: isRestoringProject flag + filter toggle + autoFillSource. `4f4256e`

### Session 198 (2026-01-12)
Fixed RenderFlex overflow in entry card + defensive try-catch for autofill. `8d32417`

### Session 197 (2026-01-12)
Code review fixes: mounted check, TestingKeys, magic numbers, calculator refactor. `a909144`

### Session 196 (2026-01-11)
Planned code review fixes from Session 195. No commits.

### Session 195 (2026-01-11)
PR 3: Start New Form button + Attachments section in entry_wizard. `0e03b95`

### Session 194 (2026-01-10)
PR 2: Calculate New Quantity button implementation.

### Session 193 (2026-01-10)
PR 1: Removed Test Results section from entry wizard.

---

## Completed Plans Summary

### Dependency Modernization Plan v2 - COMPLETE (Sessions 227-234)
10-stage upgrade: Toolchain, Core, State/Storage, Networking, Location, Files, PDF, Navigation, Supabase, Test Tooling.

### PDF Parsing Fixes v2 - COMPLETE (Sessions 221-226)
Phases 0-4: Observability, clustering, header detection, structural keywords, description cap, quality gates.

### Clumped Text PDF Parser - COMPLETE (Sessions 214-220)
8-phase state machine parser for clumped PDF text extraction.

### Smart Pay Item PDF Import Parser v2 - COMPLETE (Sessions 208-213)
8-phase parser with confidence scoring, batch import, preview UI, measurement specs.

### Form Completion Debug v3 - COMPLETE (Sessions 203-206)
4-phase fix: toggle default, report screen button, 0582B restructure, live preview.

### Entry Wizard Enhancements - COMPLETE (Sessions 193-197)
3 PRs + code review: Test Results removal, Quantity calculation, Start New Form button.


### Session 427 (2026-02-21)
**Work**: Brainstormed universal dart-mcp widget test harness. Made 5 design decisions. Wrote design document with architecture concept, open questions, and success criteria.
**Decisions**: Compile-time flag selection, test-only entry point, production code untouched, in-memory mock strategy.
**Next**: Continue brainstorming open questions, then implement harness.

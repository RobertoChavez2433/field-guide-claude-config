# Session State

**Last Updated**: 2026-03-21 | **Session**: 612

## Current Phase
- **Phase**: E2E baseline complete. All 13 tiers tested (T01-T96).
- **Status**: 66 PASS / 12 FAIL / 10 BLOCKED / 7 N/A = **75%** pass rate (excl. N/A: 66/88). Up from 64% baseline.

## HOT CONTEXT - Resume Here

### What Was Done This Session (612)

1. **Completed E2E Tiers 8-12** (T59-T96) — edit mutations, deletes, sync verification, permissions, navigation.
2. **Tier 10 (Sync)**: 5 FAIL — sync has 5 unresolved conflicts (bid_items, contractors, locations, 2x daily_entries). Pull silently skips FK violations and reports 0 errors.
3. **Tier 11 (Permissions)**: 4 BLOCKED — inspector account was on Engineer role from T55. User manually reverted. Engineer permissions confirmed correct by user.
4. **Tier 12 (Navigation)**: 3 PASS, 2 BLOCKED — dashboard nav works but data empty after re-login.
5. **Committed app repo** (7 commits) and claude config repo (2 commits) on `feat/sync-engine-rewrite`.
6. **22 total bugs tracked** in checkpoint.json.

### What Needs to Happen Next

1. **Create PR** for `feat/sync-engine-rewrite` → `main`
2. **Fix sync conflicts** — delete operations create remote conflicts; pull skips FK violations silently
3. **Re-run inspector permission tests** (T85/T89/T90/T91) now that role is reverted to Inspector
4. **Fix data-not-loaded-after-re-login** — dashboard shows 0 data, blocking T95/T96
5. **Address remaining 12 FAILs** — see report.md for categorized list

## Blockers

### BLOCKER-34: Item 38 — Superscript `th` → `"` (Tesseract limitation)
**Status**: OPEN

### BLOCKER-36: Item 130 — Whitewash destroys `y` descender
**Status**: OPEN

### BLOCKER-28: SQLite Encryption (sqlcipher)
**Status**: OPEN

### BLOCKER-23: Flutter Keys Not Propagating to Android resource-id
**Status**: OPEN — MEDIUM

## Recent Sessions

### Session 612 (2026-03-21)
**Work**: Completed E2E Tiers 8-12 (T59-T96). Final: 66/88 PASS (75%). Found 3 new sync bugs (conflicts, pull skips, false success). Inspector permission tests blocked by wrong role. Committed 7 app commits + 2 config commits.
**Decisions**: Engineer role intentionally has project create/edit/archive (user confirmed). Sync conflicts from deletes are real bugs.
**Next**: Create PR. Fix sync conflicts + pull skip bugs. Re-run inspector tests.

### Session 611 (2026-03-20)
**Work**: E2E re-test Tiers 0-7 (T01-T58). 49/58 PASS (87%). Admin dashboard, role change, archive all working. Log review found 2 new bugs: Duplicate GlobalKeys, entry_contractors table name mismatch in integrity RPC.
**Decisions**: None. Testing only.
**Next**: Resume E2E from T59. Revert inspector role. Commit + PR.

### Session 610 (2026-03-20)
**Work**: Committed pre-existing testing keys (4 commits). Executed `/implement` on bugfix plan v2 — 3 orchestrator launches, 4 phases, 16 bugs fixed. 18 files modified, 1 Supabase migration pushed. All reviews PASS.
**Decisions**: None (all design decisions made in S609).
**Next**: Commit implementation. Re-run E2E baseline. Create PR.

### Session 609 (2026-03-20)
**Work**: Full bug mapping (5 parallel agents), design decisions for all 16 bugs, writing-plans pipeline (CodeMunch + opus plan-writer + parallel adversarial reviews). BUG-16 confirmed already fixed. Plan finalized with all review findings addressed.
**Decisions**: BUG-17: don't clear data on logout (add company-switch guard instead). BUG-15: revert RPC to RETURNS TABLE. BUG-5: edit icon on contractor card. BUG-13: delete icon on form response. BUG-14: bundle real test photos. SQL migration uses subquery pattern (not JOINs) with inline soft-delete per branch.
**Next**: /implement the plan. Re-run E2E baseline. Create PR.

### Session 608 (2026-03-20)
**Work**: Full E2E test run (T01-T96). 61 PASS / 23 FAIL / 12 SKIP (64%). 17 bugs found (1 CRITICAL BUG-17: data loss on re-login via broken project enrollment). Retries blocked by BUG-17 data wipe. Final report written.
**Decisions**: ~14 failures are missing keys (not real bugs). BUG-17 is #1 priority. Pass rate should be 78%+ after key fixes + BUG-17.
**Next**: Fix BUG-17 (sync enrollment). Fix remaining HIGH bugs. Re-run baseline.

## Active Plans

### Baseline Bug Fixes v2 — COMPLETE
- **Plan**: `.claude/plans/2026-03-20-baseline-bugfix-v2.md`
- **Bugs**: 16 (all fixed). 4 phases, 12 sub-phases, ~30 steps.
- **Reviews**: All phases PASS (completeness, code review, security).
- **Status**: E2E complete. 75% pass rate. Committed.

## Reference
- **Test Results**: `.claude/test_results/2026-03-20_20-21/` (checkpoint.json + report.md)
- **Test Skill**: `.claude/skills/test/SKILL.md`
- **Test Credentials**: `.claude/test-credentials.secret`
- **Test Registry**: `.claude/test-flows/registry.md`
- **Baseline Report (S608)**: `.claude/test_results/2026-03-20_08-02/baseline-report.md`
- **Bugfix Spec**: `.claude/specs/2026-03-20-baseline-bugfix-spec.md` (v3)
- **Bugfix Plan v2**: `.claude/plans/2026-03-20-baseline-bugfix-v2.md`
- **Dep Graph**: `.claude/dependency_graphs/2026-03-20-baseline-bugfix-v2/analysis.md`
- **Plan Review**: `.claude/code-reviews/2026-03-20-baseline-bugfix-v2-plan-review.md`
- **Defects**: `.claude/defects/_defects-projects.md`, `_defects-pdf.md`, `_defects-sync.md`, `_defects-entries.md`
- **Debug build tag**: `debug-admin-dashboard-v0.1.2` on GitHub releases
- **Release build tag**: `v0.1.1` on GitHub releases

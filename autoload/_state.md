# Session State

**Last Updated**: 2026-04-04 | **Session**: 730

## Current Phase
- **Phase**: Three plans approved and ready for /implement: (1) IDR PDF mapping, (2) Smarter Sync Strategy, (3) Private Sync Hint Channels. No code changes this session.
- **Status**: Clean tree on `codex/reimplement-entry-ui-continuity` branch. Plans in `.claude/plans/`. Review sweeps complete.

## HOT CONTEXT - Resume Here

### What Was Done This Session (730)

1. **Tailor + Writing-Plans** for Private Sync Hint Channels spec:
   - Tailor: 18 files analyzed, 6 patterns discovered, 34 methods mapped, 42 ground truth verified
   - Plan: 7 phases, 10 sub-phases, ~40 steps
   - 3-cycle adversarial review: Cycle 1 all REJECT (4H+5M security, 3C+4S+5M code, 1C+2H+2L completeness) → 18 findings fixed → Cycle 2 (2 APPROVE + 1 CONDITIONAL, 13 findings already pre-applied) → Cycle 3 all 3 APPROVE

2. **Key architectural decisions**:
   - Broadcast fan-out moved from SQL triggers to edge function (eliminates SSRF + unbounded trigger latency)
   - `_callRegistrationRpc()` extracted for DRY (used by both `registerAndSubscribe` and `_refreshRegistration`)
   - RLS split into 4 policies with company_id subquery validation
   - `deviceInstallId` uses async `ensureDeviceInstallId()` pattern (not fire-and-forget)
   - Subscription limit (10/user), channel UNIQUE constraint, ON CONFLICT upsert for race safety

3. **Plan**: `.claude/plans/2026-04-04-private-sync-hint-channels.md`
4. **Tailor**: `.claude/tailor/2026-04-04-private-sync-hint-channels-codex/`
5. **Reviews**: `.claude/plans/review_sweeps/private-sync-hint-channels-2026-04-04/` (9 files, 3 cycles)

### What Needs to Happen Next
1. **Execute plans** via `/implement` — three plans ready: IDR PDF mapping + Sync Strategy + Private Hint Channels
2. **Prior session carry-over**: Commit S726 changes + PR, push Supabase migration, merge PR #140
3. **Run E2E skipped tiers** — Forms (T35-T37), Edits (T59-T67), Deletes (T68-T77)

### User Preferences (Critical)
- **Fresh test projects only**: NEVER use existing projects during test runs — always create from scratch
- **CI-first testing**: Use CI as primary test runner. NEVER include `flutter test` in plans or quality gates.
- **Always check sync logs** after every sync during test runs — never skip log review.
- **No band-aid fixes**: Root-cause fixes only. User explicitly rejected one-off cleanup approaches.
- **Verify before editing**: Do not make speculative edits — understand root cause first.
- **Do NOT suppress errors**: Fix correctly without changing functions. User was emphatic about this.
- **All findings must be fixed**: User requires ALL review findings addressed, not just blocking ones.

## Blockers

### BLOCKER-34: Item 38 — Superscript `th` → `"` (Tesseract limitation) (#91)
**Status**: OPEN (parked, cosmetic)

### BLOCKER-36: Item 130 — Whitewash destroys `y` descender (#92)
**Status**: OPEN (parked, cosmetic)

### BLOCKER-28: SQLite Encryption (sqlcipher) (#89)
**Status**: OPEN — production readiness blocker

## Recent Sessions

### Session 730 (2026-04-04)
**Work**: Tailor + writing-plans for Private Sync Hint Channels. 3-cycle adversarial review (31+ findings across 3 cycles → all fixed). All 3 reviewers APPROVE.
**Decisions**: Fan-out in edge function (not SQL triggers). DRY _callRegistrationRpc extraction. RLS 4-policy split. Async ensureDeviceInstallId. ON CONFLICT upsert. 10-sub limit.
**Next**: /implement 3 plans → commit S726 changes → merge PR #140.

### Session 729 (2026-04-04)
**Work**: 3-cycle adversarial review of Smarter Sync Strategy plan (3867 lines). 34 total findings across 3 cycles → all fixed. All 3 reviewers APPROVE.
**Decisions**: Phase 3/4 consolidated. service_role_key for triggers. Constructor-injected companyId over userMetadata. Nullable DirtyScopeTracker. Security Risk Acceptance for broadcast channel auth.
**Next**: /implement both plans → commit S726 changes → merge PR #140.

### Session 728 (2026-04-03)
**Work**: Writing-plans for IDR PDF mapping + location-scoped activities. 7 phases, 22 sub-phases, ~55 steps. 3-cycle adversarial review (20 findings fixed). All 3 reviewers APPROVE.
**Decisions**: activitiesDisplayText helper for raw JSON display. Signature fallback preserved. _isEmptyDraft delegates to controller. EntryBasicsSection confirmed dead code (delete). Orphaned location chips render from JSON names.
**Next**: /implement → commit S726 changes → merge PR #140.

### Session 727 (2026-04-03)
**Work**: Brainstormed IDR PDF mapping rebuild + location-scoped activities. Spec approved (10 sections). Tailor complete (25 files, 5 patterns, 34 methods, 42 ground truth).
**Decisions**: JSON in existing activities column (not junction table). Remove locationId from DailyEntry. Remove filterByLocation entirely. Template untouchable. Both Python + Dart verification tooling.
**Next**: /writing-plans → /implement → commit S726 changes.

## Test Results

### Flutter Unit Tests (S726)
- **Full suite**: 3784 pass / 2 fail (pre-existing: OCR test + DLL lock)
- **Analyze**: 0 issues
- **Database tests**: 65 pass, drift=0
- **Sync tests**: 704 pass

### E2E Test Run (S724)
- **Run**: 2026-04-03_10-06 (Windows)
- **Results**: 28 PASS / 0 FAIL / 30 SKIP / 6 MANUAL
- **Report**: `.claude/test_results/2026-04-03_10-06/report.md`

## Reference
- **PR #140**: OPEN (7-issue fix — sentry + dialog + schema + sync + pdf + overflow)
- **GitHub Issues**: #89 (sqlcipher), #91-#92 (OCR), #127-#129 (enhancements)

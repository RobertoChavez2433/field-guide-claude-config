# Code Review: 2026-03-24-scenario-ground-truth-fixes

**Verdict: REJECT** — 3 Critical, 5 High, 3 Medium, 3 Low

## Critical (Must Fix)

**C1 — `project_assignments` `insertRecord` will fail due to BEFORE INSERT trigger**
The plan replaces `callRpc('admin_assign_project_member')` with `verifier.insertRecord()`. The `trg_project_assignments_assigned_by` trigger stamps `assigned_by = auth.uid()`. Service role has NULL `auth.uid()`, and `assigned_by` is NOT NULL — insert will fail.
Fix: Use `verifier.authenticateAs('admin')` before inserting project_assignments.

**C2 — Scenario count/coverage gap**
The "no changes needed: 35 files" claim is never enumerated. Every file must be either explicitly fixed or declared clean. Silent omissions create implementation ambiguity.
Fix: Enumerate all clean files explicitly.

**C3 — `daily-entries-S1-push.js` date collision risk**
`new Date().toISOString().split('T')[0]` may load an existing entry. Verification checks `records.length > 0` which passes even if nothing new was created.
Fix: Use a deterministic past date (e.g., `'2020-01-01'`) + embed unique marker in `activities`.

## High (Should Fix)

**H1** — `photos-S3` seeds `file_path` as non-null; should be `null` (stripped before push).
**H2** — `form-responses` inline seeds should use `makeInspectorForm()` not inline objects.
**H3** — `calculation-history-S1` doesn't set active project before calculator navigation.
**H4** — `personnel-types` and `inspector-forms` sub-phases lack complete code (just "same as locations").
**H5** — Phase 2 routing table says 8 files but covers 10.

## Medium

**M1** — `daily-entries-S2` driver-only conversion loses entry wizard submit coverage. Document trade-off.
**M2** — `entry-quantities` may not contain `type: 'general'`; verify before blanket find-replace.
**M3** — `projects-S3` uses random UUID for `deleted_by`; may fail FK constraint to `auth.users`.

## Low

**L1** — Phase 7 verification should include at least one S3 smoke test.
**L2** — Summary count "full rewrites: 30 files" vs body lists 31.
**L3** — `calculation-history-S2/S3` clean status unconfirmed.

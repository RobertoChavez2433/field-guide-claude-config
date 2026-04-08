Date: 2026-04-07
Branch: `sync-engine-refactor`
Owner: Codex
Status: active

# Sync Validation Release Plan

## Goal

Prove this branch is safe to ship by closing the remaining data-loss,
data-drift, and stale-materialization risks across SQLite, `change_log`,
Supabase rows, storage objects, second-client convergence, and UI visibility.

This is a release-proof plan, not a feature plan. Success means every
registered sync lane has evidence, not just passing local tests.

## Release Standard

The branch is release-ready only when all of the following are true:

1. No known sync lane can reproduce data drift, data loss, or stale UI residue.
2. Delete, restore, revocation, fresh-pull, and retry/restart flows are
   idempotent across Windows and S21.
3. Integrity checks return clean after real scope churn, not only after local
   unit tests.
4. Every file-backed lane proves row + storage parity.
5. A final proof matrix exists for all active sync adapters and critical user
   flows.

## Risk-Ordered Execution

### Phase 1: Finish Delete-Proof Gaps

Why first:
- delete propagation is the highest remaining proven regression class
- the live checkpoint is already positioned here

Required proof:
- verify project-delete storage cleanup explicitly
- verify deleted entry is absent from UI on sender and receiver
- verify deleted project is absent from UI on sender and receiver
- verify sender/receiver tombstones for all affected children
- extend delete verification from local SQLite to remote rows, remote storage,
  and second-client convergence evidence

Exit criteria:
- project and entry delete both have full SQLite + queue + Supabase + storage +
  receiver UI proof

### Phase 2: Restore / Hard Delete / Revocation / Fresh Pull

Why next:
- these flows are the highest risk for stale resurrection and graph drift after
  the initial delete succeeds

Required proof:
- restore deleted entry/project and verify child restoration parity
- hard-delete restored items and verify no SQLite/Supabase/storage residue
- revoke scope and verify cleanup does not over-delete active tombstones
- remove from device and fresh-pull on Windows and S21
- prove deleted descendants do not resurrect after cache rebuild

Exit criteria:
- repeated sync after every lifecycle transition is idempotent

### Phase 3: File-Backed Lane Proof

Why next:
- file-backed data is the main remaining data-loss surface

Required proof:
- documents live flow
- `entry_exports` live flow
- `form_exports` live flow
- strengthened photos flow through the real UI path
- delete propagation and remove-from-device proof for each file-backed family
- repeated storage cleanup runs are idempotent

Exit criteria:
- each file-backed lane has SQLite + queue + Supabase + storage + receiver proof

### Phase 4: Integrity / Scope / Maintenance Proof

Why next:
- the branch has narrowed integrity issues, but release confidence requires
  real-device confirmation after scope churn and remote maintenance

Required proof:
- rerun integrity on Windows + S21 after remote `entry_*`.`project_id`
  maintenance/backfill lands
- confirm no recurring drift after delete, revocation, and fresh-pull flows
- verify orphan purge clears stale file-backed and pay-app residue in live runs

Exit criteria:
- forced integrity is clean on both devices after real flow execution

### Phase 5: Retry / Restart / Sync Mode Proof

Why next:
- idempotence under interruption is still unproven

Required proof:
- restart/retry during push
- restart/retry during pull
- restart/retry during delete propagation
- restart/retry during storage cleanup
- verify quick resume, realtime hints, global full sync, dirty-scope isolation,
  private channel register/teardown

Exit criteria:
- no mode or interruption leaves stranded work or resurrected stale state

### Phase 6: User-Scoped / Insert-Only Lane Proof

Required proof:
- support ticket sync live flow
- consent audit live flow
- verify skipped-integrity / insert-only semantics still hold

Exit criteria:
- non-project-scoped tables do not inherit unsupported delete/update behavior

### Phase 7: Final Soak + Proof Matrix

Required proof:
- mixed create/edit/delete/revoke/restore flows across both devices
- app restart and repeat sync after each major state transition
- final proof matrix covering all active sync adapters and critical user flows

Exit criteria:
- artifacts clearly show what was proven, what environment was used, and any
  remaining external blockers

## Immediate Next Action

Resume from `.claude/test-results/2026-04-06_193351_codex_sync-delete-live`
with `project-delete-storage-and-ui-verification`, now that the sync dashboard
and delete-propagation driver endpoints have been refactored into smaller,
UI-aligned components.

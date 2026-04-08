Date: 2026-04-06
Branch: `sync-engine-refactor`
Devices: Windows + S21 (`RFCNC0Y975L`)
Artifact root: `.claude/test-results/2026-04-06_183656_codex_sync-small-table-repair`

# Sync Integrity Forced Verification Update

## Summary

The orchestrators do not need a ground-up rewrite. The release blocker was a
shared-scope consistency problem plus two concrete integrity defects:

1. small-table drift was being tolerated, so real low-count mismatches never
   forced a cursor reset
2. scoped integrity was counting remote tombstones on soft-delete tables,
   which created phantom drift on `export_artifacts`, `pay_applications`, and
   likely `form_responses`

After fixing those defects and forcing maintenance on both active clients, the
current integrity lane is clean.

## Code changes in this wave

- tightened cursor reset tolerance in
  `lib/features/sync/engine/integrity_checker.dart`
  so low-count mismatches always trigger repair
- updated scoped remote integrity reads in
  `lib/features/sync/engine/integrity_checker.dart`
  to exclude rows with `deleted_at` on soft-delete tables
- added regression coverage in
  `test/features/sync/engine/integrity_checker_test.dart`
  for:
  - small-table cursor reset behavior
  - remote scoped tombstones excluded from integrity
- added a debug-only driver endpoint in
  `lib/core/driver/driver_server.dart`:
  `POST /driver/reset-integrity-check`
  so live verification can force the maintenance window without waiting

## What the live runs proved

### Phase 1: before tombstone fix

Artifacts:
- `logs/`

Findings:
- low-count drift now triggered cursor clears instead of being tolerated
- `entry_quantities` on S21 healed after the forced repull path
- `export_artifacts`, `pay_applications`, and `form_responses` still drifted

Interpretation:
- repair loop was now functioning
- remaining mismatch was not a cursor-reset problem

### Phase 2: after tombstone fix

Artifacts:
- `logs-phase2/`
- `logs-phase3-forced/`

Findings:
- forced Windows sync after `reset-integrity-check` ran with no integrity drift
  logs
- forced S21 sync after `reset-integrity-check` also ran with no integrity
  drift logs
- a follow-up sync on each client then logged
  `Full sync: integrity check not due yet`

Interpretation:
- the forced syncs did execute integrity and wrote `last_integrity_check`
- the absence of drift logs on the forced pass indicates the integrity set
  passed cleanly
- the follow-up "not due yet" log proves the forced pass completed the check

## Architectural conclusion

The orchestrator structure is directionally correct. What was fundamentally off
was not "too many orchestrators" by itself, but that pull, integrity, and scope
cleanup were still reasoning over slightly different materialized scopes.

Current conclusion:

- no full orchestrator rewrite is required for release
- the correct direction is to keep consolidating around one
  `MaterializedSyncScope`
- integrity and cleanup must continue to obey the same scope contract as pull
- delete/revocation remains the next major verification lane

## Remaining high-value verification gaps

1. file-backed live flows beyond pay apps:
   `documents`, `entry_exports`, `form_exports`, `photos`
2. delete and delete-propagation under:
   project delete, entry delete, remove-from-device, restore, hard delete
3. role/scoping interactions during delete propagation and revocation
4. restart/retry resilience while cleanup and tombstone propagation are in
   flight

## Useful proof points

- Windows forced-clean pass:
  debug log set showed sync completion with no integrity drift messages
- S21 forced-clean pass:
  debug log set showed sync completion with no integrity drift messages
- follow-up pass on both clients:
  debug log set showed `Full sync: integrity check not due yet`

This lane should now be treated as verified enough to move on to the remaining
delete and file-backed flow gaps, not as an active integrity-drift blocker.

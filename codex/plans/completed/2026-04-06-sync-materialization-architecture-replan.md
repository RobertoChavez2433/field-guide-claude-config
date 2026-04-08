Date: 2026-04-06
Branch: `sync-engine-refactor`
Status: active architecture replan for sync verification

# Sync Materialization Architecture Replan

## Why this artifact exists

The sync engine is no longer blocked on the original stale-shell bug alone.
That bug was real and is now addressed by `ScopeRevocationCleaner`, but the
remaining release risk is broader:

1. different sync subsystems still reason over different scopes
2. `viaEntry` tables still depend on denormalized `project_id` being correct
3. delete/revocation/integrity are still only partially unified

This document records the current repo findings, the current external guidance,
and the concrete implementation order for the next verification wave.

## Current repo findings

### 1. The real architecture gap is a missing shared materialization contract

Today the engine behaves like several mostly-correct orchestrators instead of one
shared scope model:

- Pull uses `synced_projects` to decide what child data to materialize.
- Enrollment/revocation mutates `synced_projects`.
- `ScopeRevocationCleaner` now evicts revoked or no-longer-visible project scope.
- `OrphanPurger` purges some local rows based on server visibility.
- `IntegrityChecker` still compares tables more broadly than the device-local
  materialized view.

Result: a device can be locally healthy for pull/push while still reporting
integrity drift, or can retain stale local data until a different subsystem
cleans it later.

### 2. The remaining drift is not random

Current live drift clusters:

- `entry_quantities`
- `entry_contractors`
- `entry_equipment`
- `inspector_forms`

Observed pattern:

- `entry_*` drift is concentrated in `viaEntry` tables.
- `inspector_forms` drift is concentrated in local builtin/null-project forms.

Interpretation:

- `viaEntry` integrity is not using the same authoritative scope key as pull.
- `inspector_forms` integrity is counting rows that are intentionally not part
  of the remote synchronized materialized view.

### 3. `viaEntry` scoping is still too dependent on denormalized `project_id`

The repo already denormalized `project_id` onto:

- `entry_equipment`
- `entry_quantities`
- `entry_contractors`
- `entry_personnel_counts`

But the remote migrations only added the column and a one-time backfill. There
is no ongoing server-side maintenance trigger ensuring `project_id` stays aligned
with `entry_id -> daily_entries.project_id`.

That means older or externally-created rows can still be:

- visible through RLS by `entry_id`
- counted by server-side access rules
- missed by client pull filters if the client filters only on `project_id`

### 4. Delete logic is directionally correct but still too distributed

The current delete surface is spread across:

- `soft_delete_service.dart`
- `project_lifecycle_service.dart`
- `scope_revocation_cleaner.dart`
- `orphan_purger.dart`
- `storage_cleanup.dart`

This is survivable, but it means "remove from scope", "soft delete", "purge",
"remove from device", and "orphan cleanup" each carry some overlapping rules.

The biggest consequence is not code style. It is drift risk:

- stale local data survives when one path knows a record is gone and another
  path does not
- file-backed rows can be cleaned in one delete path but missed in another
- integrity cannot rely on a single definition of "what should be on device"

## Current external guidance

### Electric

Electric’s client-development model is explicit that the client’s job is to
consume a shape stream and materialize it into a local store. The important
architectural lesson is that the client is responsible for maintaining a local
materialized view of a defined scope, not just "all rows I can see".

Source:
- https://electric-sql.com/docs/guides/client-development
- https://electric-sql.com/openapi.html

Useful points:

- sync is split into initial sync plus live mode
- the client materializes a scoped log into a local store
- shape definitions include explicit filters
- invalidating a shape forces a fresh resync from scratch

Implication for this repo:

- `synced_projects` is effectively our shape definition
- integrity must compare against that shape, not just current RLS visibility
- revocation is shape invalidation for a subset of local data and requires
  explicit local eviction/reset semantics

### RxDB

RxDB’s current replication guidance still assumes:

- records are never physically deleted before delete state has replicated
- deleted state must remain available long enough for offline peers
- cleanup should wait until replication is safely in sync

Source:
- https://rxdb.info/replication.html
- https://rxdb.info/cleanup.html

Useful points:

- remote documents should retain a delete marker instead of disappearing first
- cleanup should wait for replication-safe timing
- cleanup should avoid running while replication is active

Implication for this repo:

- our tombstone + storage cleanup direction is correct
- cleanup/purge should stay downstream of successful replication and scope
  convergence
- delete verification must explicitly prove tombstone survival before purge

### Couchbase Sync Gateway

Couchbase’s current access-revocation model is the closest match to our stale
scope problem: when a user loses access, the local replica should auto-purge the
revoked documents, and if access is later regained, they should be pulled back.
It also explicitly calls out that retroactive cleanup after enabling revocation
handling requires a reset/resync.

Source:
- https://docs.couchbase.com/sync-gateway/3.3/access-control/auto-purge-channel-access-revocation.html

Useful points:

- access revocation should trigger local auto-purge
- regained access should re-pull the data
- revocation handling is not retroactive without a reset/resync path

Implication for this repo:

- `ScopeRevocationCleaner` is the correct direction
- historical stale shells require a repair/reset path, not just forward-only
  revocation cleanup
- we still need a cleaner resync/reset story for scope drift and integrity drift

## Structural conclusion

The sync engine does not need a ground-up rewrite.

It does need one missing architectural boundary:

`MaterializedSyncScope`

This boundary should define, in one place, the exact local replica that a
device is supposed to hold.

That shared scope must drive:

- pull filters
- integrity comparisons
- orphan purge
- revocation cleanup
- fresh-pull/reset behavior

Without that shared boundary, each subsystem remains "mostly right" but the
system as a whole remains vulnerable to stale rows and false drift.

## Concrete weak points to fix now

### P0: unify scope for pull and integrity

Required changes:

- define a scope snapshot from local materialization state:
  - synced project ids
  - synced contractor ids
  - synced entry ids
- make `viaEntry` use `entry_id` as the authoritative remote scope key
- make integrity compare against the same scoped universe as pull
- exclude local-only builtin/null-project `inspector_forms` from integrity

Expected effect:

- eliminates current false drift on `entry_*`
- eliminates current false drift on builtin `inspector_forms`
- makes integrity failures more trustworthy

### P0: make remote `entry_*` denormalization self-healing

Required changes:

- add Supabase trigger(s) that stamp child `project_id` from parent
  `daily_entries.project_id` on insert/update
- add a propagation trigger when `daily_entries.project_id` changes
- backfill any remaining remote nulls

Expected effect:

- prevents future `viaEntry` rows from silently falling out of project-based
  filters
- reduces dependence on client fallback logic alone

### P1: formalize revocation/reset behavior

Required changes:

- keep `ScopeRevocationCleaner` as the authoritative project-scope eviction path
- add a documented reset/resync path when historical scope or integrity drift
  already exists

Expected effect:

- prevents the same stale-shell class from returning in a different subsystem

### P1: split delete orchestration by responsibility

Proposed split after release blocker fixes:

- `CascadeDeletePlanner`
- `RestoreCascadePlanner`
- `StorageCleanupPlanner`
- `ScopeEvictionService`

This is not the first release blocker, but `SoftDeleteService` is already large
enough that future delete bugs will keep clustering there.

## Implementation order

1. Introduce a shared scope snapshot helper for synced projects, contractors,
   and entries.
2. Change `PullScopeState` so `viaEntry` filters by `entry_id` scope.
3. Change `IntegrityChecker` to run scope-aware integrity for `viaProject`,
   `viaEntry`, and `viaContractor` tables.
4. Exclude local builtin/null-project inspector forms from integrity.
5. Add regression tests for:
   - scope-aware integrity
   - `viaEntry` fallback semantics
   - builtin-form integrity exclusion
6. Add a Supabase migration to keep remote `entry_*`.`project_id` in sync.
7. Re-run focused tests and then the S21 + Windows live verification wave.

## Verification consequences

Sync is not "100% verified" until the following are true after the above work:

- live full sync on S21 shows no false integrity drift for the current active
  scope
- live full sync on Windows shows the same
- revoked scope is evicted locally
- regained scope rehydrates cleanly
- delete tombstones still propagate correctly
- file-backed descendants are still cleaned exactly once

## Working recommendation

Do not continue adding delete methods to the current architecture without first
moving pull/integrity/revocation onto the same materialized-scope model.

That shared scope is the missing link.

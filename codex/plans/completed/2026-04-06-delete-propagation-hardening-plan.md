Date: 2026-04-06
Branch: `sync-engine-refactor`
Devices: Windows + S21 (`RFCNC0Y975L`)
Status: active

# Delete Propagation Hardening Plan

## Why this plan exists

The next release risk is no longer broad sync integrity drift. It is delete
propagation and stale local residue after records or scope should be gone.

The current codebase already has:

- local soft-delete cascades
- restore cascades
- hard purge with retention
- file cleanup queueing
- project eviction via `removeFromDevice()`
- scope revocation cleanup via `ScopeRevocationCleaner`

But the delete topology is still duplicated across multiple flows, which means
one path can learn about a new table while another path silently does not.

That is the architecture hole this plan addresses first.

## Updated diagnosis

### 1. The primary architecture gap is duplicated delete topology

Current delete knowledge lives in separate lists or custom SQL in:

- `lib/services/soft_delete_service.dart`
- `lib/features/projects/data/services/project_lifecycle_service.dart`
- `lib/features/sync/engine/orphan_purger.dart`
- `lib/features/sync/engine/storage_cleanup_registry.dart`

Concrete consequence:

- a table can be included in project soft-delete but missed in project
  eviction, or vice versa
- file-backed cleanup can be wired in one path and forgotten in another
- revocation cleanup correctness depends on `removeFromDevice()` staying in
  perfect parity with other delete flows

The earlier `pay_applications` / `export_artifacts` omission was exactly this
failure class.

### 2. The missing abstraction is a first-class delete graph

The system needs one authoritative delete graph that answers:

1. what tables are direct project descendants
2. what tables are entry descendants
3. what tables are contractor descendants
4. what file-backed descendants require local-file cleanup
5. what tables participate in soft delete vs hard eviction vs purge
6. what exceptional guards exist, such as builtin inspector forms

Without this, stale data is not just a bug risk. It is the default outcome of
future schema growth.

### 3. The next missing abstraction is delete verification, not just delete execution

Current architecture executes deletes, but it does not centrally verify that
delete propagation completed across:

- local SQLite
- change_log
- Supabase row tombstones or hard deletes
- storage cleanup queue
- remote storage
- second-client materialized state

This is why delete bugs can survive even when individual methods look correct.

## External guidance that maps to this repo

### Couchbase Sync Gateway

Official docs:

- https://docs.couchbase.com/sync-gateway/3.3/access-control/auto-purge-channel-access-revocation.html

Relevant lesson:

- access revocation cleanup must be a first-class replication behavior, not an
  ad hoc UI cleanup step

Mapping here:

- `ScopeRevocationCleaner` is directionally correct
- we still need deletion and revocation to share one graph and one verification
  contract

### RxDB

Official docs:

- https://rxdb.info/cleanup.html
- https://rxdb.info/replication.html

Relevant lessons:

- deleted records are retained until replication safety conditions are met
- cleanup is a separate lifecycle phase, not the same thing as delete marking
- cleanup should wait until replication is safe

Mapping here:

- our `storage_cleanup_queue` and retention purge are the beginnings of this
- what is still missing is one consistent graph and a stronger verification
  stage before purge/eviction is treated as complete

### Electric

Official docs:

- https://electric-sql.com/docs/guides/client-development
- https://electric-sql.com/openapi.html

Relevant lessons:

- the client materializes a scoped shape
- delete operations and shape invalidation are part of materialization, not a
  separate concern
- invalidating a shape forces a clean resync

Mapping here:

- our delete graph should be treated as part of local materialization
- scope loss, delete propagation, and stale-data cleanup should all operate
  over the same local graph

### Android offline-first guidance

Official docs:

- https://developer.android.com/topic/architecture/data-layer/offline-first

Relevant lessons:

- the local database should be the canonical source of truth
- repositories should write locally first, then synchronize
- queues and persistent work should drive retry/reconciliation

Mapping here:

- delete verification belongs in the local-sync architecture, not just in UI
  workflows
- the app needs stronger persistent reconciliation for delete propagation, not
  just one-shot delete methods

## Implementation order

### Phase 1: Centralize the delete graph

Implement a shared registry used by:

- `SoftDeleteService`
- `ProjectLifecycleService`
- later: `OrphanPurger` / delete verification

Status:

- in progress on this branch
- shared `DeleteGraphRegistry` now exists and is wired into
  `SoftDeleteService` and `ProjectLifecycleService`
- `OrphanPurger` now derives its project-scope tables from the registered sync
  adapters instead of a stale hard-coded subset

### Phase 2: Add delete propagation verification primitives

Introduce a service or helper layer that can verify, per flow:

- local descendants marked or removed
- `change_log` disposition is correct
- storage cleanup queue state is correct
- remote state matches intended delete mode
- second client converges

Status:

- local verification primitives now exist via
  `lib/features/sync/engine/delete_propagation_verifier.dart`
- the verifier currently snapshots:
  - target existence / tombstone state
  - descendant table active/deleted counts across the shared delete graph
  - `storage_cleanup_queue` parity for file-backed deleted rows
  - `synced_projects` enrollment state
  - project-scoped pending `change_log` counts
- the Flutter driver now exposes this checkpoint with
  `GET /driver/delete-propagation?target_type=project|entry&id=<uuid>`
- remote Supabase/storage convergence still needs to be layered on top during
  the live Windows + S21 delete waves

### Phase 3: Re-run live delete lanes

Priority order:

1. project delete cascade
2. entry delete cascade
3. remove-from-device on second client
4. delete plus scope revocation overlap
5. restore and hard delete from trash

## Success criteria

- delete graph exists in one place and is reused by the highest-risk paths
- adding a new synced child table requires changing one authoritative graph
- regression tests fail if a delete path falls out of parity
- live Windows + S21 verification proves delete propagation converges without
  stale local residue

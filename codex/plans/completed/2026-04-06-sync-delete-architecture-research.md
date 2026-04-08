# Sync Delete Architecture Research

Date: 2026-04-06
Branch: `sync-engine-refactor`
Purpose: persistent research artifact for the ongoing sync verification pass, focused on delete propagation, stale-data recurrence, and missing orchestration layers.

## Executive Diagnosis

The recurring stale-data problem does not come from a single broken soft-delete method.

The codebase already has:

- local soft-delete cascades
- restore cascades
- storage cleanup queueing for file-backed tables
- hard-purge retention handling
- manual `removeFromDevice()` project eviction

The missing link is a first-class **scope-revocation / cache-eviction orchestration layer**.

Today the architecture handles:

- `record inside active sync scope was deleted`

But it does not reliably handle:

- `project left synced scope`
- `project was deleted remotely and is no longer visible through RLS`
- `user lost access, so remote tombstones are no longer observable`
- `cached subtree must now be purged or tombstoned locally`

That gap explains why the app can correctly soft-delete active records, yet still accumulate stale local residue over time.

## Repo-Specific Findings

### 1. `SoftDeleteService` is large, but size is not the root cause

`lib/services/soft_delete_service.dart`

It currently mixes at least four concerns:

- delete cascade policy
- restore cascade policy
- file cleanup queueing
- retention purge logic

This is a maintainability smell, but the stale-data recurrence is not primarily caused by method count. The more important architectural gap is that this service is only for local record lifecycle actions. It is not the orchestrator for remote scope loss.

### 2. Enrollment cleanup removes sync scope without cleaning the retained subtree

`lib/features/sync/engine/enrollment_handler.dart`

`cleanOrphanedProjects(...)` removes rows from `synced_projects` once assignment is revoked and there are no pending local changes.

What it does **not** do:

- call `removeFromDevice()`
- soft-delete the local project shell
- purge retained child rows
- queue any explicit local subtree eviction

Result:

- a project can fall out of sync participation
- but its previously synced local rows remain resident forever

### 3. `removeFromDevice()` is the only full subtree local-eviction path

`lib/features/projects/data/services/project_lifecycle_service.dart`

`removeFromDevice(...)` hard-deletes the local project subtree and removes the `synced_projects` enrollment row.

Concrete flaw found during this research pass:

- `removeFromDevice()` had omitted `pay_applications` and `export_artifacts`
- it also failed to collect `export_artifacts.local_path`
- this would allow project eviction to leave pay-app metadata and exported files behind

Status:

- fixed on `sync-engine-refactor`
- regression coverage added in `test/features/projects/data/services/project_lifecycle_service_test.dart`

This means the architecture already has a reliable **manual** local cache-eviction primitive.

What is missing is an automatic orchestrator that invokes equivalent cleanup when:

- remote delete makes a project inaccessible
- assignment revocation removes project scope
- integrity/orphan logic proves the local subtree is no longer part of the remote truth set

### 4. Orphan purge is scoped too narrowly to catch out-of-scope residue

`lib/features/sync/engine/orphan_purger.dart`

Current behavior:

- orphan purge works only against `syncedProjectIds`
- for `projects`, it filters local IDs to those contained in `syncedProjectIds`
- for project-scoped child rows, it only checks rows whose `project_id` is still in `syncedProjectIds`

Effect:

- once a project leaves `synced_projects`, its stale subtree stops being eligible for orphan purge
- retained stale `projects`, `export_artifacts`, `pay_applications`, and other child rows can survive indefinitely

This is the strongest code-level explanation for the recurring stale residue.

Additional implementation finding:

- the old `OrphanPurger` also used a stale hard-coded table subset and omitted
  newer pay-app/file-backed tables from remote-missing cleanup
- direction on this branch is to derive orphan-purge coverage from the
  registered sync adapters instead

### 5. Integrity drift is exposing a real lifecycle gap, not just noisy logging

Observed during live S21 work:

- stale local projects remained active after backend cleanup
- active stale pay-app rows under an old project could still exist locally
- integrity drift then reports mismatched counts even when the newest pay-app create/delete flow is healthy

Meaning:

- the create/delete path for current records can be correct
- while the architecture still leaks stale historical scope

## Architectural Conclusion

The system has tombstone propagation, but it lacks a dedicated **post-scope-loss cleanup phase**.

That missing phase should answer:

1. A project is no longer part of the device’s synced scope. What local data is allowed to remain?
2. If data is retained, how is it excluded from integrity/orphan expectations?
3. If data should be evicted, what component performs that eviction?
4. If access was revoked before this logic existed, how does the system backfill cleanup for already-stale cache?

Right now those answers are split across unrelated components and are not enforced centrally.

## Best-Practice Patterns From Other Sync Systems

### RxDB

Official docs:

- https://rxdb.info/cleanup.html
- https://rxdb.info/replication.html

Relevant guidance:

- deleted documents are intentionally retained so offline clients can still replicate delete state
- cleanup is a separate lifecycle phase
- cleanup should wait until replication is safe to avoid purging before delete propagation completes
- replication explicitly models a deleted flag as part of the sync contract

Why it matters here:

- tombstones and purge are separate responsibilities
- our system already has this partially, but only for row deletion, not for scope revocation

### Couchbase Sync Gateway / Couchbase Lite

Official docs:

- https://docs.couchbase.com/sync-gateway/3.0/auto-purge-channel-access-revocation.html
- https://docs.couchbase.com/sync-gateway/3.1/database-management.html

Relevant guidance:

- when a user loses access to a channel, the next pull can auto-purge previously synced local documents
- revocation cleanup is treated as a first-class replication behavior
- enabling purge later is not retroactive; older revocations require reset/checkpoint reset
- tombstones and purging are separate, retention-aware operations

Why it matters here:

- this is the closest match to the Field Guide stale-data problem
- our architecture lacks the equivalent of `purge_on_removal`
- we also lack a defined backfill/reset strategy for historical stale scope

### ElectricSQL

Official docs:

- https://electric-sql.com/docs/guides/client-development

Relevant guidance:

- sync is organized around materialized shapes
- clients are responsible for materializing updates into a local store
- initial sync and live mode are distinct phases

Why it matters here:

- the client owns the local materialized view and therefore must own removing rows that no longer belong to that view
- this reinforces that stale local scope is a client orchestration problem, not just a backend delete problem

## What The Architecture Is Missing

### Missing Orchestrator 1: Scope Revocation Cleaner

Needed responsibility:

- detect projects leaving effective device scope
- decide whether to retain metadata shell, tombstone locally, or full-evict subtree
- perform cleanup using a single policy
- record why the cleanup happened

Current nearest pieces:

- `EnrollmentHandler.cleanOrphanedProjects(...)`
- `ProjectLifecycleService.removeFromDevice(...)`
- `OrphanPurger.purgeOrphans(...)`

None of them currently own this end to end.

### Missing Orchestrator 2: Historical Revocation Backfill / Reset Path

Needed responsibility:

- clean up already-stale rows that predate the new revocation-cleanup logic
- reset integrity/checkpoint state when the policy changes
- optionally run a one-time repair sweep

This matches Couchbase’s explicit warning that enabling purge later does not retroactively clean older revocations without reset.

### Missing Orchestrator 3: Local Materialized-View Contract

Needed decision:

- should the device keep non-enrolled project shells?
- should it keep data for unassigned or deleted projects?
- should integrity compare against all cached rows or only active materialized scope?

Until this contract is explicit, integrity, orphan purge, and UI behavior will keep disagreeing.

### Missing Orchestrator 4: Deletion Graph Registry

Needed responsibility:

- define delete/restore/purge relationships once
- reuse the graph across:
  - cascade delete
  - restore
  - remove-from-device

## Additional 2026-04-06 implementation finding

The next concrete stale-data risk is not only "scope revocation lacks cleanup."
It is also that delete topology is duplicated across local flows.

Current duplicated graph knowledge exists in:

- `SoftDeleteService`
- `ProjectLifecycleService.removeFromDevice()`
- `OrphanPurger`
- `StorageCleanupRegistry`

That duplication is itself a release risk because:

- a newly added child table can be covered by soft delete but missed by local
  eviction
- file-backed cleanup can stay wired in one path and silently disappear in
  another
- revocation cleanup inherits whatever omissions currently exist in
  `removeFromDevice()`

Direction taken on this branch:

- introduce a shared delete-graph registry as the first concrete abstraction
- refactor the highest-risk local delete paths to consume that registry
- follow it with a delete verification layer so convergence is proven, not
  inferred
  - orphan cleanup
  - integrity scoping
  - storage cleanup

Today the graph knowledge is duplicated across:

- `SoftDeleteService`
- `ProjectLifecycleService`
- datasource helpers
- storage cleanup mapping
- orphan purge logic

That duplication increases drift risk whenever new tables are added.

## Recommended Refactor Direction

### Phase A: Establish explicit cleanup policy

Define per scope-loss scenario:

- remote soft-delete still visible
- remote project inaccessible due to role/scope revocation
- project manually removed from device
- project no longer enrolled but has no pending changes

For each case, decide:

- retain metadata only
- retain nothing
- tombstone locally
- hard-evict subtree

### Phase B: Introduce a scope-revocation cleanup service

Suggested shape:

- `ScopeRevocationCleaner`
- input:
  - current `synced_projects`
  - accessible project IDs
  - local active project IDs
  - pending local changes by project
- output:
  - projects to retain
  - projects to tombstone
  - projects to evict locally
  - integrity/checkpoint resets required

### Phase C: Split `SoftDeleteService`

Suggested extraction:

- `CascadeDeleteExecutor`
- `CascadeRestoreExecutor`
- `RetentionPurger`
- `StorageCleanupQueueWriter`
- shared deletion graph / registry

This would reduce the current service’s surface area while keeping behavior centralized.

### Phase D: Add revocation-specific tests

Required coverage:

- revoked assignment removes project from `synced_projects` and evicts subtree when policy allows
- remote-deleted project no longer visible via RLS is cleaned locally
- stale `export_artifacts` / `pay_applications` from removed scope stop affecting integrity
- historical stale rows are cleaned by the repair/backfill pass
- re-assignment rehydrates correctly after local purge

## Verification Implications For The Current Release Blocker

The sync system is not yet “bulletproof” until the following is explicitly verified:

- delete propagation inside active synced scope
- storage cleanup for all file-backed tables
- revocation/deleted-project local eviction behavior
- integrity behavior after revocation cleanup
- restore / re-assignment recovery after purge
- restart/retry behavior during partially-completed cleanup

## Working Hypothesis To Carry Forward

Current root-cause hypothesis:

1. active-scope delete propagation is mostly working
2. file cleanup for newly deleted pay-app artifacts is now working
3. stale data recurs because local cache eviction is manual-only and not orchestrated on scope loss
4. orphan purge and integrity currently reason over different effective universes of data
5. the architecture needs a dedicated scope-revocation cleanup layer more than it needs more ad hoc delete hooks

## Sources

- RxDB Cleanup: https://rxdb.info/cleanup.html
- RxDB Replication: https://rxdb.info/replication.html
- Couchbase Auto-Purge on Channel Access Revocation: https://docs.couchbase.com/sync-gateway/3.0/auto-purge-channel-access-revocation.html
- Couchbase Database Management / Tombstone Purge / Resync: https://docs.couchbase.com/sync-gateway/3.1/database-management.html
- Electric Client Development Guide: https://electric-sql.com/docs/guides/client-development

# Sync Delete Contract Lints Plan

Date: 2026-04-07
Branch: `sync-engine-refactor`

## Why This Plan Exists

The recent hard-delete / orphan-purge drift investigation exposed a real
architectural gap:

- the codebase has custom lints for generic DB safety and some sync invariants
- but it does **not** enforce the **delete contract** for sync-managed tables
- so a developer can still:
  - physically delete a local row from a soft-delete sync table
  - emit a `change_log.operation = delete`
  - or call a direct remote `.delete()`
  - without the lint layer understanding that this breaks sync semantics

That is exactly the kind of failure that produces long-lived drift, data loss,
and “janky” convergence.

## Core Architectural Finding

We need the delete model to be explicit and lintable.

For sync-managed data there are only three legitimate delete lanes:

1. **Soft delete orchestration**
   Used for normal user-visible deletion of sync tables that support tombstones.
   This must preserve the row, set `deleted_at` / `deleted_by`, and let sync
   propagate the tombstone.

2. **Local-only device eviction**
   Used for remove-from-device / scope-revocation flows. This must suppress sync,
   clear or avoid `change_log`, and never masquerade as a remote delete.

3. **Maintenance hard purge**
   Used only after a prior tombstone already exists. This must preserve enough
   tombstone metadata for remote replay, or be restricted to tables that are
   truly hard-delete only.

The bug we just fixed existed because lane 3 was executed without enough
metadata, and the lint architecture had no rule that understood this.

## Existing Lint Coverage

Current custom lints already help, but they stop short of the real problem:

- `avoid_raw_database_delete`
- `require_soft_delete_filter`
- `change_log_cleanup_requires_success`
- `sync_control_inside_transaction`
- `no_state_reload_after_rpc`
- `tomap_includes_project_id`

## Why Existing Rules Did Not Catch This

### 1. `avoid_raw_database_delete` is too generic and too allowlist-heavy

It broadly forbids `db.delete(...)`, but it explicitly allows:

- `soft_delete_service.dart`
- `project_lifecycle_service.dart`
- `project_repository.dart`
- the entire `lib/features/sync/engine/` subtree

Those are exactly the files where delete semantics are most dangerous.

### 2. Sync lints do not model delete lanes

The sync-integrity rules understand:

- success-gated cleanup
- sync control placement
- soft-delete column presence

But they do **not** understand:

- soft-delete tables vs hard-delete tables
- local-only eviction vs sync-propagating delete
- remote physical delete vs tombstone replay
- change-log delete entries that outlive the local row

### 3. Base remote delete APIs remain legal

The repo still permits dangerous primitives such as:

- `BaseRemoteDatasource.delete(String id)`
- explicit remote `.delete().eq(...)` helpers for entry-scoped child tables

Even if those are not the current hot path, they are architectural footguns.

## Missing Custom Lint Rules

These are the rules that were missing.

### L1. `no_remote_delete_for_soft_delete_tables`

**Intent:** For any sync-registered table whose adapter reports
`supportsSoftDelete == true`, forbid direct Supabase physical delete calls.

**Should flag:**

- `supabase.from(tableName).delete()...`
- inherited use of `BaseRemoteDatasource.delete(...)`
- table-specific remote helpers like `deleteByEntryId(...)`

**Allow only:**

- tables whose adapters declare `supportsSoftDelete == false`
- tightly-scoped maintenance/admin code explicitly allowlisted

### L2. `no_push_hard_delete_for_soft_delete_adapter`

**Intent:** Inside sync-engine code, forbid calling `pushHardDelete(...)` when
the adapter supports soft delete.

**Why:** The engine should replay a tombstone, not physically remove the remote
row, for soft-delete tables.

### L3. `require_preserved_tombstone_metadata_for_local_purge`

**Intent:** If a soft-delete sync row is physically purged locally and a
`change_log` delete entry is emitted, preserved tombstone metadata must be
attached.

**Should enforce for patterns like:**

- `hardDeleteWithSync(...)`
- purge/retention flows
- maintenance cleanup that deletes rows after tombstoning

**Why:** This is the exact rule that would have caught the recent bug.

### L4. `no_local_purge_of_soft_delete_sync_tables_outside_executors`

**Intent:** For sync-registered soft-delete tables, raw local hard deletes are
forbidden outside a narrow executor allowlist.

**Allowed homes:**

- `SoftDeleteService` hard-purge paths
- explicit local-only eviction service(s)
- approved maintenance purgers
- driver seed/reset helpers

**Everything else should fail.**

### L5. `no_delete_contract_bypass_from_presentation_or_domain`

**Intent:** Presentation/domain code must not call low-level delete primitives
for sync tables directly.

**Should force UI and feature use-cases through sanctioned executors, e.g.:**

- `SoftDeleteService`
- `ProjectLifecycleService.removeFromDevice(...)`
- future dedicated delete executors/controllers

**Why:** This is how we keep delete behavior standardized at the endpoint layer.

### L6. `no_base_remote_delete_on_synced_datasource`

**Intent:** If a datasource corresponds to a sync-registered table, the base
remote `.delete()` API should be banned or require an explicit override proving
the table is hard-delete only.

**Why:** The inherited default is too dangerous for a sync system with mixed
soft-delete and insert-only semantics.

### L7. `local_only_eviction_requires_sync_suppression`

**Intent:** Methods that perform local-only device removal of synced data must
also use the approved sync-suppression path and change-log cleanup strategy.

**Should catch:**

- local delete loops over synced tables
- missing `SyncControlService` suppression
- local eviction that leaves delete operations queued for push

### L8. `sync_delete_table_must_come_from_registry`

**Intent:** Delete-capability decisions must derive from `SyncRegistry` /
`TableAdapter`, not hand-maintained per-file allowlists.

**Why:** We already saw drift between the real sync model and local delete code.

This rule may be partly CI-based rather than pure AST lint.

## CI Checks That Should Accompany The Lints

Some of this is easier to prove with cross-file validation than single-file AST
lints.

### C1. Registry-driven delete contract audit

Cross-check all sync-registered tables against:

- `supportsSoftDelete`
- storage cleanup registry
- delete-related allowlists
- remote datasource delete helpers
- maintenance purgers

Fail CI if a soft-delete table appears in an unapproved physical-delete path.

### C2. Soft-delete schema parity audit

For every adapter with `supportsSoftDelete == true`, verify:

- local schema has `deleted_at` and `deleted_by`
- remote schema / migrations preserve the same contract
- integrity tooling treats the table as soft-delete capable

### C3. Executor ownership audit

For all UI/domain delete entry points, verify they route through approved
executor classes rather than directly mutating repositories/datasources.

## Recommended Implementation Order

1. Tighten the current rule instead of adding more broad allowlists.
   Replace the generic `avoid_raw_database_delete` posture with adapter-aware,
   delete-contract-aware rules.

2. Implement the two highest-value blocking rules first:
   - `no_remote_delete_for_soft_delete_tables`
   - `no_push_hard_delete_for_soft_delete_adapter`

3. Implement the purge-protection rule next:
   - `require_preserved_tombstone_metadata_for_local_purge`

4. Add executor-boundary enforcement:
   - `no_local_purge_of_soft_delete_sync_tables_outside_executors`
   - `no_delete_contract_bypass_from_presentation_or_domain`

5. Add CI manifest checks for cross-file parity.

## Practical Design Recommendation

To make the lint rules precise, the architecture should name the lanes
explicitly instead of relying on ad hoc conventions.

Suggested boundary:

- `SyncSoftDeleteExecutor`
- `LocalScopeEvictionExecutor`
- `SyncMaintenancePurgeExecutor`

Whether those names are final or not, the code needs a small set of explicit,
approved delete executors. The lint layer can then enforce:

- soft-delete tables must use the soft-delete executor
- local-only removal must use the eviction executor
- retention/hard-purge must use the purge executor

Without that boundary, lint rules will remain heuristic and weaker than they
should be.

## Immediate Follow-up

Before resuming live validation, the lint backlog should at minimum capture:

- direct remote delete on soft-delete tables
- hard-delete routing for soft-delete adapters
- local purge without preserved tombstone metadata
- UI/domain delete calls that bypass approved executors

That is the foundation we were missing.

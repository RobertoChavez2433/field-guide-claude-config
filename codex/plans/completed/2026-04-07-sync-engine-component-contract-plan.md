# Sync Engine Component Contract Plan

Date: 2026-04-07
Branch: `sync-engine-refactor`

## Why This Plan Exists

The recent delete and hard-purge investigation exposed a broader problem than
Trash or delete propagation:

- the sync engine has been decomposed into many focused classes
- but the lint layer still does not enforce which class owns which sync action
- so developers can bypass the intended boundary and still write code that
  "works" locally while creating drift, stale scope state, duplicate pulls, or
  silent data loss later

This plan defines the missing architectural contracts for the full sync engine,
not just delete semantics.

## Core Finding

The registry and adapter model is already the right foundation.

The repo already has the main sources of sync truth:

- `SyncRegistry` for table membership and dependency order
- `TableAdapter` for per-table behavior
- `ScopeType` plus `pullFilter()` for scope semantics
- `LocalSyncStore` / `LocalRecordStore` for local sync I/O
- `SupabaseSync` for remote sync I/O
- `ChangeTracker` for `change_log` lifecycle
- `SyncedScopeStore` / `EnrollmentHandler` for `synced_projects`
- `DeleteGraphRegistry` / `StorageCleanupRegistry` for cross-table cleanup maps

What is missing is enforcement that these are the only places allowed to own
those concerns.

## Current Blind Spots

### 1. The lints protect symptoms, not ownership

Current sync rules mostly cover local safety details:

- `change_log_cleanup_requires_success`
- `sync_control_inside_transaction`
- `sync_time_on_success_only`
- `tomap_includes_project_id`
- `no_state_reload_after_rpc`

Those rules help, but they do not answer:

- who may touch `change_log`
- who may touch `synced_projects`
- who may build pull scope filters
- who may perform sync-table Supabase I/O
- who may decide soft-delete vs insert-only vs skip-push vs file-backed flow

### 2. The generic delete rule is over-allowlisted

`avoid_raw_database_delete` currently allows several sync hot-zone files,
including the entire `lib/features/sync/engine/` subtree. That makes it too
weak to protect the architecture that actually matters.

### 3. Size rules are too generic for sync components

The repo has generic `max_file_length`, plus UI-specific 300-line rules, but
no sync-specific structural limit. Right now that means a sync class can grow
past the intended endpoint-sized boundary without tripping a targeted rule.

Audit snapshot:

- `sync_coordinator.dart`: 300 lines
- `sync_engine.dart`: 231 lines
- `push_handler.dart`: 237 lines
- `pull_handler.dart`: 291 lines
- `supabase_sync.dart`: 321 lines
- `local_sync_store.dart`: 505 lines

`LocalSyncStore` is already a concrete example of a sync component that needs a
sync-specific cap and a follow-up split.

## Required Component Contracts

These are the contracts the lint layer should make explicit.

### A. UI / Endpoint Contract

Presentation, controllers, providers, and driver endpoints may call:

- `SyncCoordinator`
- `SyncQueryService`
- screen-local sync controllers/providers
- approved lifecycle executors such as project enrollment or delete executors

They must not call:

- `SyncEngine`
- `PushHandler`, `PullHandler`, `MaintenanceHandler`
- `LocalSyncStore`, `LocalRecordStore`, `ChangeTracker`, `SyncedScopeStore`
- `SupabaseSync`
- raw `Database` / raw Supabase sync-table access

### B. Application Orchestrator Contract

`SyncCoordinator` / `SyncRunExecutor` / `SyncEngineFactory` own:

- mode selection
- retry policy
- reachability checks
- status projection
- engine construction

They must not own:

- table-specific routing
- raw sync-table SQL
- direct Supabase row mutation for sync tables
- hand-maintained table allowlists

### C. Engine Coordinator Contract

`SyncEngine` owns:

- mutex
- run lifecycle
- mode routing
- handler invocation order

It must not own:

- direct SQLite I/O
- direct Supabase I/O
- per-table branching

### D. Push Contract

Push behavior must be split as:

- `PushHandler`: batch and action orchestration
- `PushTablePlanner`: per-table eligibility/blocking plan
- `PushExecutionRouter`: soft-delete vs file vs insert-only vs upsert routing
- `PushErrorHandler`: retry/failure classification

The push path must not re-implement table semantics outside adapters or the
execution router.

### E. Pull Contract

Pull behavior must be split as:

- `PullHandler`: pagination, cursor lifecycle, handler loop
- `PullScopeState`: materialized-scope planning and filter application
- `PullRecordApplicator`: remote row application
- `EnrollmentHandler`: assignment-driven scope enrollment
- `FkRescueHandler`: parent rescue only

Scope filtering must not be redefined outside adapters, `PullScopeState`, or
the limited integrity tooling that intentionally mirrors those rules.

### F. Local Sync Storage Contract

`LocalSyncStore` and its sub-stores own:

- trigger suppression
- cursor reads/writes
- sync metadata
- scoped read/write helpers
- approved local sync queries

Direct sync-table SQL in handlers should be treated as a boundary violation.

### G. Change Log Contract

`change_log` ownership must be explicit:

- triggers create normal entries
- `ChangeTracker` owns mark-processed / mark-failed / prune / manual insert
- `LocalRecordStore` may update references during ID remap
- approved delete/purge executors may clean or preserve entries intentionally

Everything else should be considered a contract bypass.

### H. Scope Enrollment Contract

`synced_projects` ownership must be explicit:

- `SyncedScopeStore`
- `EnrollmentHandler`
- `ProjectLifecycleService` for explicit user-driven enroll / local-only removal
- `SyncEnrollmentService` if still retained as an app-layer bridge

Ad hoc `synced_projects` inserts or deletes elsewhere should fail lint.

### I. Registry Contract

All sync-table decisions must derive from registry metadata, not from scattered
string lists:

- soft-delete capability
- insert-only semantics
- scope type
- file-backed behavior
- local-only columns
- FK dependencies

If a sync decision branches on a table name string outside the registry,
adapters, delete graph registry, or storage cleanup registry, that should be
treated as architecture drift.

### J. Storage Contract

For sync-managed file tables:

- `SupabaseSync` owns storage upload/remove primitives
- `FileSyncHandler` owns three-phase push flow
- `StorageCleanup` owns cleanup queue execution
- `StorageCleanupRegistry` owns table-to-bucket/path mapping

Duplicate bucket/path logic outside these owners is a drift risk.

## Missing Custom Lint Rules

### Boundary Rules

1. `no_sync_engine_import_outside_sync_application`
   Ban imports of `features/sync/engine/*` from presentation/domain layers and
   from non-sync features except allowlisted executor bridges.

2. `no_direct_sync_engine_usage_from_ui`
   UI code must not construct or call `SyncEngine`, handlers, or stores
   directly. It should go through `SyncCoordinator` or approved endpoint
   controllers.

3. `no_sync_handler_construction_outside_factory`
   `PushHandler`, `PullHandler`, `MaintenanceHandler`, `SupabaseSync`,
   `LocalSyncStore`, and `ChangeTracker` should only be constructed inside
   `SyncEngineFactory`, startup bootstrap, or tightly scoped tests.

### Remote I/O Rules

4. `no_raw_supabase_sync_table_io_outside_supabase_sync`
   For sync-registered tables, raw `.from(table).select/update/upsert/delete`
   is only legal in `SupabaseSync`, `IntegrityChecker`, or tightly scoped
   verification tooling.

5. `no_sync_storage_io_outside_sync_storage_owners`
   For sync-managed storage buckets, direct `storage.from(bucket)` access is
   only legal in `SupabaseSync`, `StorageCleanup`, `OrphanScanner`, or approved
   non-sync datasources such as support log upload.

### Local I/O Rules

6. `no_raw_sync_sql_outside_store_owners`
   Sync handlers and application orchestrators must not issue raw SQL against
   sync tables directly when an existing store boundary exists.

7. `no_change_log_mutation_outside_sync_owners`
   Raw `change_log` insert/update/delete should be limited to triggers,
   `ChangeTracker`, `LocalRecordStore` remap logic, migrations, tests, and
   approved delete executors.

8. `no_synced_projects_mutation_outside_scope_owners`
   Raw `synced_projects` writes should be limited to `SyncedScopeStore`,
   `EnrollmentHandler`, `ProjectLifecycleService`, `SyncEnrollmentService`,
   migrations, and tests.

### Scope / Registry Rules

9. `no_scope_filter_logic_outside_adapters_and_pull_scope_state`
   Scope predicates such as `project_id IN (...)`, `entry_id IN (...)`,
   `contractor_id IN (...)`, or direct use of `pullFilter()` should be confined
   to adapters, `PullScopeState`, and intentional integrity mirrors.

10. `sync_table_contract_must_come_from_registry`
    Sync behavior must not branch on hard-coded table-name lists when the same
    truth already exists in `SyncRegistry`, `TableAdapter`,
    `DeleteGraphRegistry`, or `StorageCleanupRegistry`.

11. `sync_registered_table_requires_registered_adapter`
    CI check: all sync-managed tables used by change-log triggers, integrity,
    storage cleanup, and verification must have an adapter and registry entry.

### Delete / Lifecycle Rules

12. Carry forward the delete-contract plan from
    `2026-04-07-sync-delete-contract-lints-plan.md`, but treat it as one part
    of this larger boundary system rather than a standalone fix.

### Size / Decomposition Rules

13. `max_sync_component_file_length`
    Sync application and engine components should hard-fail above 350 lines,
    with a stricter cap for `SyncEngine` itself if desired.

14. `max_sync_component_callable_length`
    Methods inside sync application/engine components should hard-fail above
    150 lines so orchestration logic stays endpoint-sized.

15. `no_multi_owner_sync_god_methods`
    Heuristic rule for methods that mix status updates, raw SQL, Supabase I/O,
    and table branching in one callable.

## CI Checks To Add

### C1. Registry contract audit

Generate a machine-readable sync manifest from `SyncRegistry` and fail CI if
other sync-critical files disagree on:

- adapter list
- soft-delete support
- insert-only support
- file-backed tables
- scope types

### C2. Scope parity audit

Cross-check `PullScopeState`, `IntegrityChecker`, and any scope-cleanup code so
they do not silently diverge on direct/viaProject/viaEntry/viaContractor rules.

### C3. Change-log ownership audit

Search for non-test writes to `change_log` and fail CI unless the file is in
the approved ownership list.

### C4. Synced-project ownership audit

Search for non-test writes to `synced_projects` and fail CI unless the file is
in the approved ownership list.

### C5. Storage bucket ownership audit

Search for `storage.from(...)` calls and verify each bucket belongs to an
approved owner.

## Recommended Execution Order

1. Add the boundary docs and TODOs so the architecture direction is durable.
2. Implement the highest-value ownership lints first:
   - `no_raw_supabase_sync_table_io_outside_supabase_sync`
   - `no_change_log_mutation_outside_sync_owners`
   - `no_synced_projects_mutation_outside_scope_owners`
3. Add the sync-specific size caps:
   - `max_sync_component_file_length`
   - `max_sync_component_callable_length`
4. Refactor `LocalSyncStore` below the new cap by splitting query-only and
   metadata-only responsibilities.
5. Tighten the existing delete-contract rules under the new ownership model.
6. Resume the remaining live validation passes after the boundary rules are in
   place and the obvious oversized sync components are split.

## Immediate Outcome We Want

After this wave, a developer should be able to tell immediately:

- which sync component to call from UI
- which component is allowed to touch a sync table locally
- which component is allowed to touch a sync table remotely
- where `change_log` and `synced_projects` may be mutated
- where scope rules are defined
- when a sync component has grown too large and must be split

That is the foundation needed to stop drift from re-entering through new code.

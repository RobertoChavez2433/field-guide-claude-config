Date: 2026-04-07
Branch: `sync-engine-refactor`
Status key: `[ ]` pending, `[-]` in progress, `[x]` done, `[!]` blocked

# Sync Engine Component Contract TODO

## Audit

[x] Audit current sync component ownership boundaries
[x] Audit current custom lint coverage and blind spots
[x] Save the broader component-contract plan

## Contract Rules

[x] Add `no_sync_engine_import_outside_sync_application`
[x] Add `no_direct_sync_engine_usage_from_ui`
[x] Add `no_sync_handler_construction_outside_factory`
[x] Add `no_raw_supabase_sync_table_io_outside_supabase_sync`
[x] Add `no_sync_storage_io_outside_sync_storage_owners`
[x] Add `no_raw_sync_sql_outside_store_owners`
[x] Add `no_change_log_mutation_outside_sync_owners`
[x] Add `no_synced_projects_mutation_outside_scope_owners`
[x] Add `no_scope_filter_logic_outside_adapters_and_pull_scope_state`
[x] Add `sync_table_contract_must_come_from_registry`
[x] Fold the delete-contract lint work into this broader ownership model
Implementation note: tightened `avoid_raw_database_delete` so sync engine is no longer globally exempt.

## Size / Decomposition

[x] Add `max_sync_component_file_length` with a 300-line hard cap
[x] Add `max_sync_component_callable_length` with a 150-line hard cap
[ ] Split `lib/features/sync/engine/local_sync_store.dart` below the new cap
[ ] Re-audit `supabase_sync.dart` against the new sync-component cap
[ ] Re-audit `sync_coordinator.dart` against the new sync-component cap

## CI / Verification

[ ] Add a registry contract audit script
[ ] Add a `change_log` ownership audit script
[ ] Add a `synced_projects` ownership audit script
[ ] Add a storage bucket ownership audit script
[ ] Add lint tests for each new sync rule

## Validation Resume Gate

[x] Hold remaining hard-delete and revocation live validation until ownership rules are in place
Reason: the hard-delete finding exposed a general sync-boundary problem, not an isolated Trash bug.
[-] Resume Windows + S21 live validation after the first ownership lint wave lands

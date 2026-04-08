# Sync Legacy Surface Audit

Date: 2026-04-07
Branch: `sync-engine-refactor`
Source of truth: CodeMunch index `local/Field_Guide_App-37debbe5` plus
`dart run custom_lint`

## Goal

Expose every remaining legacy or hidden sync-adjacent surface that can touch:

- SQLite
- Supabase row data
- local file storage
- remote storage buckets

This audit is intentionally broad. A surface listed here is not automatically a
bug, but it is a place where ownership must be explicit or the sync system will
drift again.

## New Lint Coverage Landed

### `no_sync_table_base_remote_datasource_inheritance`

New rule in
[no_sync_table_base_remote_datasource_inheritance.dart](C:\Users\rseba\Projects\Field_Guide_App\fg_lint_packages\field_guide_lints\lib\sync_integrity\rules\no_sync_table_base_remote_datasource_inheritance.dart).

Purpose:
- prevents registered sync tables from hiding behind
  `BaseRemoteDatasource<T>`
- exposes inheritance-based Supabase row access that the older raw `.from(...)`
  lint only surfaced indirectly

### `no_sync_storage_io_outside_sync_storage_owners`

Broadened existing rule in
[no_sync_storage_io_outside_sync_storage_owners.dart](C:\Users\rseba\Projects\Field_Guide_App\fg_lint_packages\field_guide_lints\lib\sync_integrity\rules\no_sync_storage_io_outside_sync_storage_owners.dart).

New behavior:
- scans all `lib/`, not only `lib/features/sync/`
- only targets sync buckets:
  `entry-photos`, `entry-documents`, `entry-exports`, `form-exports`,
  `export-artifacts`, `signatures`

This exposes file-backed sync bypasses such as
[photo_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\photos\data\datasources\remote\photo_remote_datasource.dart)
and
[pay_app_providers.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\pay_applications\di\pay_app_providers.dart).

## Current Static Snapshot

Latest `dart run custom_lint` now reports `4` findings:

- `0` errors
- `4` warnings

The sync-architecture error backlog exposed by the broad lints has been burned
down in this refactor pass. The remaining warnings are unrelated quality items,
not sync ownership breaches.

### Closed In This Pass

- Removed the dead file-backed remote datasource layer.
- Removed the remaining dead `BaseRemoteDatasource` sync subclasses.
- Removed `BaseRemoteDatasource` itself.
- Routed export-artifact remote downloads through
  [sync_file_access_service.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\application\sync_file_access_service.dart)
  backed by
  [supabase_sync.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\supabase_sync.dart).
- Moved remaining sync-table literal manifests into
  [delete_graph_registry.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\delete_graph_registry.dart).
- Reworked metadata/conflict cleanup deletes to explicit special-case raw SQL.

The broad lint did the right job. The main legacy sync surface was not in the
new orchestrators; it was in old ownership and data-access paths around them.
That exposed surface has now been materially reduced to zero sync-architecture
errors.

## Approved Owners

These are the intended owners the system should converge toward:

### Supabase row I/O

- [supabase_sync.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\supabase_sync.dart)
- [integrity_checker.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\integrity_checker.dart)
- [project_assignment_mutation_service.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\projects\data\services\project_assignment_mutation_service.dart)

### Remote storage I/O

- [supabase_sync.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\supabase_sync.dart)
- [storage_cleanup.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\storage_cleanup.dart)
- [orphan_scanner.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\orphan_scanner.dart)

### SQLite sync-state ownership

- [change_tracker.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\change_tracker.dart)
- [local_record_store.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\local_record_store.dart)
- [local_sync_store.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\local_sync_store.dart)
- [synced_scope_store.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\synced_scope_store.dart)
- [sync_enrollment_service.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\application\sync_enrollment_service.dart)

## Exposed Legacy Surfaces

Most of the surfaces below were exposed at the start of this audit and then
removed in the current refactor pass. They remain documented here so the team
understands what was hiding in the branch and what patterns must not return.

## 1. Generic Supabase Sync Table Access Hidden Behind `BaseRemoteDatasource`

CodeMunch found `19` feature datasources still extending
[base_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\shared\datasources\base_remote_datasource.dart),
which itself still exposes generic `getById/getAll/insert/update/upsert/delete`
against `supabase.from(tableName)`.

Affected sync-backed subclasses:

- [calculation_history_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\calculator\data\datasources\remote\calculation_history_remote_datasource.dart)
- [contractor_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\contractors\data\datasources\remote\contractor_remote_datasource.dart)
- [entry_equipment_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\contractors\data\datasources\remote\entry_equipment_remote_datasource.dart)
- [equipment_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\contractors\data\datasources\remote\equipment_remote_datasource.dart)
- [personnel_type_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\contractors\data\datasources\remote\personnel_type_remote_datasource.dart)
- [daily_entry_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\entries\data\datasources\remote\daily_entry_remote_datasource.dart)
- [document_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\entries\data\datasources\remote\document_remote_datasource.dart)
- [entry_export_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\entries\data\datasources\remote\entry_export_remote_datasource.dart)
- [form_export_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\forms\data\datasources\remote\form_export_remote_datasource.dart)
- [form_response_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\forms\data\datasources\remote\form_response_remote_datasource.dart)
- [inspector_form_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\forms\data\datasources\remote\inspector_form_remote_datasource.dart)
- [location_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\locations\data\datasources\remote\location_remote_datasource.dart)
- [export_artifact_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\pay_applications\data\datasources\remote\export_artifact_remote_datasource.dart)
- [pay_application_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\pay_applications\data\datasources\remote\pay_application_remote_datasource.dart)
- [photo_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\photos\data\datasources\remote\photo_remote_datasource.dart)
- [project_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\projects\data\datasources\remote\project_remote_datasource.dart)
- [bid_item_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\quantities\data\datasources\remote\bid_item_remote_datasource.dart)
- [entry_quantity_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\quantities\data\datasources\remote\entry_quantity_remote_datasource.dart)
- [todo_item_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\todos\data\datasources\remote\todo_item_remote_datasource.dart)

Interpretation:
- this is the largest remaining legacy sync surface
- even the datasources that did not previously appear as bespoke `.from('...')`
  violations were still inheriting sync-table Supabase row access indirectly

## 2. Raw Sync Storage Access Outside Sync Owners

CodeMunch and the broadened lint exposed sync bucket access outside the approved
owners:

- [photo_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\photos\data\datasources\remote\photo_remote_datasource.dart)
  still performs upload, signed URL creation, download, and delete directly on
  `entry-photos`
- [pay_app_providers.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\pay_applications\di\pay_app_providers.dart)
  still injects a direct `export-artifacts` storage download callback into
  `ExportArtifactFileService`

Approved comparison surfaces:

- [supabase_sync.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\supabase_sync.dart)
- [storage_cleanup.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\storage_cleanup.dart)
- [orphan_scanner.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\orphan_scanner.dart)

Non-sync storage path that remains intentionally separate:

- [log_upload_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\settings\data\datasources\remote\log_upload_remote_datasource.dart)
  uses `support-logs`, not a sync bucket

## 3. SQLite Delete And Change-Tracking Leaks

The main SQLite ownership leaks are not generic reads; they are lifecycle and
cleanup paths that can bypass the intended sync stores.

### High-risk delete / cleanup paths

- [database_service.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\core\database\database_service.dart)
  still has one unconditional `change_log` cleanup hit under
  `change_log_cleanup_requires_success`
- [project_repository.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\projects\data\repositories\project_repository.dart)
  directly deletes from `projects` and `change_log`
- [project_lifecycle_service.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\projects\data\services\project_lifecycle_service.dart)
  directly deletes from `projects` and mutates `synced_projects`
- [conflict_resolver.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\conflict_resolver.dart)
  still contains raw database delete behavior
- [sync_metadata_store.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\sync_metadata_store.dart)
  still contains raw database delete behavior

### Duplicate `change_log` mutation owners

CodeMunch still sees `change_log` mutation-related ownership spread across:

- [change_tracker.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\change_tracker.dart)
- [local_record_store.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\local_record_store.dart)
- [project_repository.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\projects\data\repositories\project_repository.dart)
- [project_lifecycle_service.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\projects\data\services\project_lifecycle_service.dart)
- [soft_delete_service.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\services\soft_delete_service.dart)
- [database_service.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\core\database\database_service.dart)

Interpretation:
- some of these are sanctioned today
- the surface is still too wide for a clean architecture story
- `change_log` ownership should keep shrinking, not stay permanently shared

## 4. `synced_projects` Ownership Is Still Wider Than Ideal

CodeMunch shows `synced_projects` surfaces in:

- [synced_project_repository.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\projects\data\repositories\synced_project_repository.dart)
- [project_lifecycle_service.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\projects\data\services\project_lifecycle_service.dart)
- [sync_enrollment_service.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\application\sync_enrollment_service.dart)
- [synced_scope_store.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\synced_scope_store.dart)
- [soft_delete_service.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\services\soft_delete_service.dart)

Interpretation:
- the current lint prevents arbitrary sprawl
- but the owner set is still too broad for long-term clarity
- the architecture should converge toward one read/write store plus one or two
  orchestrators, not five mutation-capable surfaces

## 5. File-Backed Local Cache And Local File I/O Surfaces

These are not all legacy bugs, but they are active file-backed sync-adjacent
surfaces that should be explicitly routed and linted over time.

### Remote-path aware local cache/file surfaces

- [export_artifact_file_service.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\pay_applications\data\services\export_artifact_file_service.dart)
- [pay_app_providers.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\pay_applications\di\pay_app_providers.dart)
- [photo_remote_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\photos\data\datasources\remote\photo_remote_datasource.dart)
- [file_sync_handler.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\file_sync_handler.dart)
- [local_record_store.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\local_record_store.dart)
- [local_sync_store.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\local_sync_store.dart)
- [stale_file_cache_invalidator.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\stale_file_cache_invalidator.dart)
- [storage_cleanup.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\storage_cleanup.dart)

### Local-path mutation / file-write surfaces tied to sync-backed artifacts

- [export_entry_use_case.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\entries\domain\usecases\export_entry_use_case.dart)
- [export_form_use_case.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\forms\domain\usecases\export_form_use_case.dart)
- [export_artifact_local_datasource.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\pay_applications\data\datasources\local\export_artifact_local_datasource.dart)
- [export_artifact_file_service.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\pay_applications\data\services\export_artifact_file_service.dart)
- [pay_app_excel_exporter.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\pay_applications\data\services\pay_app_excel_exporter.dart)
- [contractor_comparison_provider_commands.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\pay_applications\presentation\providers\contractor_comparison_provider_commands.dart)
- [scope_revocation_cleaner.dart](C:\Users\rseba\Projects\Field_Guide_App\lib\features\sync\engine\scope_revocation_cleaner.dart)

Interpretation:
- the remote-storage side is now partly linted
- the local-file side is not yet strongly linted
- this is the next likely place where hidden file-backed drift can re-enter

## What This Audit Says About "Legacy Sync Left"

The branch does not appear to have a second hidden monolithic sync engine.

At the start of this audit, what was still left was:

1. a legacy generic Supabase datasource layer that predated the current sync
   ownership model
2. a few file-backed storage paths living outside the sync file owners
3. overly wide ownership for `change_log`, `synced_projects`, and lifecycle
   deletes

The first two categories have now been collapsed out of the active codepath.
The remaining work is runtime proof and any future tightening of already-owned
cleanup paths.

## Recommended Next Lint Wave

1. Tighten `no_change_log_mutation_outside_sync_owners` so the allowed owner
   list shrinks over time instead of staying permanently broad.
2. Tighten `no_synced_projects_mutation_outside_scope_owners` toward one store
   plus one orchestration layer.
3. Add a new file-backed lint:
   `no_sync_local_file_io_outside_file_cache_owners`
   Purpose: flag direct `File/Directory/readAsBytes/writeAsBytes/delete`
   touching sync-backed artifact paths outside approved file-cache owners.
4. Add a new RPC ownership lint:
   `no_sync_rpc_outside_approved_mutation_services`
   Purpose: keep future sync table mutations from reappearing as hidden RPC
   shortcuts.

## Recommended Execution Order

1. Resume live proof work starting with remove-from-device/fresh-pull parity.
2. Tighten `change_log` and `synced_projects` ownership further over time.
3. Add the local-file and RPC ownership lints before new sync surface is added.

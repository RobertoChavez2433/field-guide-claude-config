# Sync System Comprehensive Audit Report

**Date**: 2026-03-04 | **Session**: 494
**Scope**: SQLite, Supabase, Sync Service, Auth, Data Layer — full system audit
**Purpose**: Ground truth for planned rewrite of storage, sync, and auth integration

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Push Mechanisms (3 Competing Systems)](#2-push-mechanisms)
3. [Pull System](#3-pull-system)
4. [Sync Queue](#4-sync-queue)
5. [Conflict Resolution](#5-conflict-resolution)
6. [Sync Triggers](#6-sync-triggers)
7. [SQLite Schema (Complete)](#7-sqlite-schema)
8. [SQLite Migration History](#8-sqlite-migration-history)
9. [Supabase Schema (Complete)](#9-supabase-schema)
10. [Supabase Migration History](#10-supabase-migration-history)
11. [Schema Divergences](#11-schema-divergences)
12. [RLS Policies](#12-rls-policies)
13. [Database Functions, RPCs, and Triggers](#13-database-functions-rpcs-and-triggers)
14. [Auth System](#14-auth-system)
15. [Data Layer (Repositories, Datasources, Providers)](#15-data-layer)
16. [User Flow Analysis](#16-user-flow-analysis)
17. [Push Coverage Map](#17-push-coverage-map)
18. [Complete Gap Inventory](#18-complete-gap-inventory)
19. [Suggestions for Rewrite](#19-suggestions-for-rewrite)

---

## 1. Architecture Overview

The sync system has three layers:

```
SyncOrchestrator (retry logic, project mode routing, post-sync profile updates)
  └── SupabaseSyncAdapter (thin wrapper, implements SyncAdapter interface)
        └── SyncService (1535 lines, ALL actual SQLite↔Supabase work)
```

- **SyncService** (`lib/services/sync_service.dart`) — labeled "LEGACY SERVICE" at line 34-42 but remains the only working implementation.
- **SupabaseSyncAdapter** (`lib/features/sync/data/adapters/supabase_sync_adapter.dart`) — delegates everything to SyncService.
- **SyncOrchestrator** (`lib/features/sync/application/sync_orchestrator.dart`) — routes by `ProjectMode`, adds retry (3 attempts, exponential backoff), fires post-sync user profile updates.

Data flow: `Screen → Provider → Repository → LocalDatasource → SQLite → (async) SyncService → Supabase`

---

## 2. Push Mechanisms

Three separate, independently-evolved push mechanisms exist. None covers all tables.

### Mechanism 1: `_pushBaseData()` — First-Sync Full Push

**File**: `sync_service.dart:629-688`
**Trigger**: `_lastSyncTime == null` (first ever sync). Guard at line 635-638.
**Behavior**: Pushes ALL local records from every table unconditionally.

Tables pushed (in order): `projects`, `locations`, `contractors`, `equipment`, `bid_items`, `personnel_types`, `daily_entries`, `entry_equipment`, `entry_quantities`, `inspector_forms`, `form_responses`, `todo_items`, `calculation_history`.

**Missing from `_pushBaseData`**: `entry_contractors`, `entry_personnel_counts`, `photos`. Photos have their own path. `entry_contractors` and `entry_personnel_counts` are silently skipped on first sync.

**Risk**: If `sync_metadata` is ever lost or corrupted, `_lastSyncTime` returns null and the full push fires again for every record.

### Mechanism 2: Sync Queue Processing

**File**: `sync_service.dart:521-558` (queue loop), `sync_service.dart:691-717` (`_processSyncQueueItem`)
**Trigger**: Any record in `sync_queue` table.
**Operations handled**: `insert`, `update`, `delete`. The `purge` operation queued by `SoftDeleteService.hardDeleteWithSync()` (`soft_delete_service.dart:380`) is **NOT handled** — the switch statement at line 699-716 has no `case 'purge'` branch. Queued purge items fail silently and count toward the 5-attempt limit before being dropped.

**Who writes to sync_queue**:

| Location | Table | Operation |
|----------|-------|-----------|
| `inspector_form_provider.dart:219` | form_responses | insert |
| `inspector_form_provider.dart:249` | form_responses | update |
| `inspector_form_provider.dart:279` | form_responses | update |
| `inspector_form_provider.dart:305` | form_responses | update |
| `inspector_form_provider.dart:331` | form_responses | delete |
| `todo_provider.dart:125` | todo_items | insert |
| `todo_provider.dart:148` | todo_items | update |
| `todo_provider.dart:167` | todo_items | update |
| `todo_provider.dart:187` | todo_items | delete |
| `todo_provider.dart:210` | todo_items | delete |
| `calculator_provider.dart:151` | calculation_history | insert |
| `calculator_provider.dart:171` | calculation_history | delete |
| `personnel_types_screen.dart:104,239,337,397` | personnel_types | update |
| `sync_service.dart:1358` | (any) | update (edit-wins conflict) |
| `supabase_sync_adapter.dart:110,117,124` | projects/entries/photos | update (convenience methods) |

**Notable**: `InspectorFormProvider.addForm()`, `updateForm()`, `deleteForm()` do NOT queue sync operations. Inspector form templates never sync after first push.

### Mechanism 3: `sync_status` Field Polling

**File**: `sync_service.dart:892-989` (`_pushPendingEntries`, `_pushPendingPhotos`)
**Trigger**: `daily_entries.sync_status = 'pending'` or `photos.sync_status = 'pending'`
**Only two tables use this mechanism.**

Entry flow (`_pushPendingEntries`, line 892): queries pending entries → `DailyEntryRemoteDatasource.upsert()` → strips `sync_status` (BLOCKER-27 fix at `daily_entry_remote_datasource.dart:17`) → on success, updates local `sync_status` to `'synced'` → on failure, updates to `'error'`.

Photo flow (`_pushPendingPhotos`, line 933): queries pending photos → if no `remote_path`, uploads file to Storage bucket `entry-photos` at `entries/{companyId}/{entryId}/{filename}` → upserts metadata row → on success, sets `sync_status = 'synced'` + stores `remote_path` → on failure, sets `SyncStatus.failed`.

**Inconsistency**: `_pushPendingEntries` writes `'error'` (plain string) on failure. `_pushPendingPhotos` writes `SyncStatus.failed.toJson()` on failure. `getPendingCount()` at line 1498 only queries `sync_status = 'pending'` — `error` and `failed` entries are never retried and invisible in the pending count.

---

## 3. Pull System

### `_pullRemoteChanges()` — `sync_service.dart:992-1031`

Pull order (parents before children): `projects`, `locations`, `contractors`, `equipment`, `bid_items`, `personnel_types`, `daily_entries`, `entry_equipment`, `entry_quantities`, `photos`, `inspector_forms`, `form_responses`, `todo_items`, `calculation_history`.

**Tables NOT pulled**:
- `entry_contractors` — absent from pull list entirely
- `entry_personnel_counts` — absent from pull list entirely
- `entry_personnel` — intentionally omitted (CONT-8/LOW-1, legacy dead table, comment at line 1006)
- `companies`, `user_profiles`, `company_join_requests` — pulled separately by `UserProfileSyncDatasource.pullCompanyMembers()` in the orchestrator

### No Incremental Pull

**There is no incremental pull.** Every sync pulls ALL records from every table. `_pullRemoteRecordsInChunks()` at line 1034 does a paginated SELECT with `.range(offset, offset + pullChunkSize - 1).order('created_at', ascending: true)` — no `updated_at > last_sync_time` filter. For large datasets, this is O(n) on every sync.

### Company Scoping on Pull

- `projects`: filtered by `company_id` when `_companyId != null` via `_pullRemoteRecordsWithFilter()` (line 1199)
- `locations`, `contractors`, `bid_items`, `personnel_types`, `daily_entries`: filtered by local project IDs via `_pullRemoteRecordsFilteredByProjects()` (lines 1211-1267) when `_companyId != null`
- `equipment`, `entry_equipment`, `entry_quantities`, `photos`, `inspector_forms`, `form_responses`, `todo_items`, `calculation_history`: **no company-level client-side scoping** — rely entirely on RLS

### `_upsertLocalRecords()` — `sync_service.dart:1306-1391`

For each pulled record:
1. Convert to local format via `_convertForLocal()`
2. Check if record exists locally
3. If not local AND remote has `deleted_at` → skip (new team members never see trashed items, line 1329-1335)
4. If not local AND not deleted → INSERT (line 1338)
5. If local exists AND remote has `deleted_at` AND local was edited AFTER deletion → edit-wins, queue `update` push (lines 1349-1360)
6. If local exists AND remote has `deleted_at` AND no local edit after → apply remote soft-delete, create `deletion_notifications` row (lines 1365-1451)
7. Standard: last-write-wins on `updated_at` (lines 1374-1386)

---

## 4. Sync Queue

**Schema** (`lib/core/database/schema/sync_tables.dart:6-17`):

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| table_name | TEXT | NOT NULL |
| record_id | TEXT | NOT NULL |
| operation | TEXT | NOT NULL ('insert', 'update', 'delete', 'purge') |
| payload | TEXT | nullable (JSON blob) |
| created_at | TEXT | NOT NULL |
| attempts | INTEGER | DEFAULT 0 |
| last_error | TEXT | nullable |

**Indexes**: `idx_sync_queue_table`, `idx_sync_queue_created`

**Retry logic** (`sync_service.dart:537-556`): On failure, `attempts` incremented. At `attempts >= 5` (`SupabaseConfig.syncRetryMaxAttempts`), the row is hard-deleted from the queue. **The change is permanently lost** — no dead-letter queue, no alerting.

**The `purge` operation**: `SoftDeleteService.hardDeleteWithSync()` at `soft_delete_service.dart:362-383` queues `'purge'` but `_processSyncQueueItem()` has no `case 'purge'` handler. Items fail silently, increment attempts, and are eventually discarded.

---

## 5. Conflict Resolution

**Last-write-wins**: Compares `updated_at` strings via `DateTime.parse()` (`sync_service.dart:1374-1378`). If remote is newer, local is overwritten. If local is newer or timestamps are null, local is kept.

**Edit-wins vs delete**: If remote has `deleted_at` but local was edited AFTER the deletion timestamp, the edit wins — local version is preserved and a `queueOperation(tableName, id, 'update')` is queued to push back (line 1358).

**Race condition**: Clock skew across devices can cause edit-wins to misfire. No vector clock or server-side timestamp comparison.

---

## 6. Sync Triggers

| Trigger | Path | Debounced? |
|---------|------|-----------|
| Connectivity restored (offline→online) | `_initConnectivity()` listener at line 224 → `scheduleDebouncedSync()` | Yes, 2s |
| DNS retry recovery | `_scheduleDnsRetry()` timer at line 339 fires after 30s | Yes, 2s |
| App paused | `SyncLifecycleManager._handlePaused()` at line 54 | Yes, 30s timer |
| App detached | `SyncLifecycleManager._handleDetached()` at line 65 | No — immediate |
| App resumed, data stale (>24h) | `SyncLifecycleManager._handleResumed()` at line 74 | No — immediate forced |
| App resumed, data fresh | Nothing | N/A |
| `queueOperation()` called | `sync_service.dart:1491-1494` schedules debounced sync if online | Yes, 2s |
| Manual sync from UI | `SyncProvider.sync()` → `SyncOrchestrator.syncLocalAgencyProjects()` | No |
| Background (mobile) | WorkManager every ~4 hours | No |
| Background (desktop) | Timer every ~4h + random 0-30min jitter | No |

**No periodic foreground timer.** Foreground syncs are event-driven.

**Background sync calls `SyncService.syncAll()` directly** (not through orchestrator), bypassing the orchestrator's 3-attempt exponential backoff retry logic.

---

## 7. SQLite Schema

### Configuration

**File**: `lib/core/database/database_service.dart:52-64`

```
Database: construction_inspector.db
Version: 29
PRAGMA journal_mode = WAL (via rawQuery — Android API 36 compatibility)
PRAGMA foreign_keys = ON
```

Singleton pattern: `DatabaseService._instance`. Testing uses `_testInstance` (in-memory DB).

### Table: `projects`

**File**: `lib/core/database/schema/core_tables.dart:6-29`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| name | TEXT | NOT NULL |
| project_number | TEXT | NOT NULL |
| client_name | TEXT | nullable |
| description | TEXT | nullable |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| is_active | INTEGER | NOT NULL DEFAULT 1 |
| mode | TEXT | NOT NULL DEFAULT 'localAgency' |
| mdot_contract_id | TEXT | nullable |
| mdot_project_code | TEXT | nullable |
| mdot_county | TEXT | nullable |
| mdot_district | TEXT | nullable |
| control_section_id | TEXT | nullable |
| route_street | TEXT | nullable |
| construction_eng | TEXT | nullable |
| company_id | TEXT | nullable (no FK declared) |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

**Indexes**: `idx_locations_project`, `idx_projects_company`, `idx_projects_deleted_at`
**MISSING**: UNIQUE index on `(company_id, project_number)` — BLOCKER-24

**CRITICAL**: `Project.toMap()` at `project.dart:107-128` does NOT write `deleted_at` or `deleted_by`. Those are only written by `softDelete()` in `GenericLocalDatasource`. The Dart model has NO `deletedAt` field.

### Table: `locations`

**File**: `lib/core/database/schema/core_tables.dart:32-47`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| project_id | TEXT | NOT NULL, FK → projects(id) ON DELETE CASCADE |
| name | TEXT | NOT NULL |
| description | TEXT | nullable |
| latitude | REAL | nullable |
| longitude | REAL | nullable |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

### Table: `companies` (local cache)

**File**: `lib/core/database/schema/core_tables.dart:50-57`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| name | TEXT | NOT NULL |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |

No soft-delete columns. `CREATE TABLE IF NOT EXISTS`.

### Table: `user_profiles` (local cache)

**File**: `lib/core/database/schema/core_tables.dart:60-75`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| company_id | TEXT | FK → companies(id) ON DELETE CASCADE |
| role | TEXT | NOT NULL DEFAULT 'inspector' |
| status | TEXT | NOT NULL DEFAULT 'pending' |
| display_name | TEXT | nullable |
| cert_number | TEXT | nullable |
| phone | TEXT | nullable |
| position | TEXT | nullable |
| last_synced_at | TEXT | nullable |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |

### Table: `company_join_requests` (local cache)

**File**: `lib/core/database/schema/core_tables.dart:78-89`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| user_id | TEXT | NOT NULL |
| company_id | TEXT | NOT NULL, FK → companies(id) ON DELETE CASCADE |
| status | TEXT | NOT NULL DEFAULT 'pending' |
| requested_at | TEXT | NOT NULL |
| resolved_at | TEXT | nullable |
| resolved_by | TEXT | nullable |

### Table: `contractors`

**File**: `lib/core/database/schema/contractor_tables.dart:5-21`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| project_id | TEXT | NOT NULL, FK → projects(id) ON DELETE CASCADE |
| name | TEXT | NOT NULL |
| type | TEXT | NOT NULL ('prime' or 'sub') |
| contact_name | TEXT | nullable |
| phone | TEXT | nullable |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

**Indexes**: `idx_contractors_project`, `idx_contractors_deleted_at`

### Table: `equipment`

**File**: `lib/core/database/schema/contractor_tables.dart:24-37`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| contractor_id | TEXT | NOT NULL, FK → contractors(id) ON DELETE CASCADE |
| name | TEXT | NOT NULL |
| description | TEXT | nullable |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

**Indexes**: `idx_equipment_contractor`, `idx_equipment_deleted_at`

### Table: `daily_entries`

**File**: `lib/core/database/schema/entry_tables.dart:6-36`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| project_id | TEXT | NOT NULL, FK → projects(id) ON DELETE CASCADE |
| location_id | TEXT | FK → locations(id) ON DELETE SET NULL (nullable) |
| date | TEXT | NOT NULL |
| weather | TEXT | nullable |
| temp_low | INTEGER | nullable |
| temp_high | INTEGER | nullable |
| activities | TEXT | nullable |
| site_safety | TEXT | nullable |
| sesc_measures | TEXT | nullable |
| traffic_control | TEXT | nullable |
| visitors | TEXT | nullable |
| extras_overruns | TEXT | nullable |
| signature | TEXT | nullable |
| signed_at | TEXT | nullable |
| status | TEXT | NOT NULL DEFAULT 'draft' |
| submitted_at | TEXT | nullable |
| revision_number | INTEGER | NOT NULL DEFAULT 0 |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| sync_status | TEXT | DEFAULT 'pending' (LOCAL ONLY) |
| created_by_user_id | TEXT | nullable |
| updated_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

**Indexes**: `idx_daily_entries_project`, `idx_daily_entries_location`, `idx_daily_entries_date`, `idx_daily_entries_sync_status`, `idx_daily_entries_project_date`, `idx_daily_entries_deleted_at`

### Table: `entry_contractors`

**File**: `lib/core/database/schema/entry_tables.dart:40-54`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY (deterministic: `'ec-$entryId-$contractorId'`) |
| entry_id | TEXT | NOT NULL, FK → daily_entries(id) ON DELETE CASCADE |
| contractor_id | TEXT | NOT NULL, FK → contractors(id) ON DELETE CASCADE |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | nullable (added v24) |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable (added v29) |
| deleted_by | TEXT | nullable (added v29) |

**UNIQUE**: `(entry_id, contractor_id)`
**Indexes**: `idx_entry_contractors_entry`, `idx_entry_contractors_deleted_at`

### Table: `entry_equipment`

**File**: `lib/core/database/schema/entry_tables.dart:57-71`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| entry_id | TEXT | NOT NULL, FK → daily_entries(id) ON DELETE CASCADE |
| equipment_id | TEXT | NOT NULL, FK → equipment(id) ON DELETE CASCADE |
| was_used | INTEGER | NOT NULL DEFAULT 1 |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

**Index**: `idx_entry_equipment_entry`

### Table: `entry_quantities`

**File**: `lib/core/database/schema/quantity_tables.dart:27-42`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| entry_id | TEXT | NOT NULL, FK → daily_entries(id) ON DELETE CASCADE |
| bid_item_id | TEXT | NOT NULL, FK → bid_items(id) ON DELETE CASCADE |
| quantity | REAL | NOT NULL |
| notes | TEXT | nullable |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

**Indexes**: `idx_entry_quantities_entry`, `idx_entry_quantities_deleted_at`
**MISSING**: Index on `bid_item_id` for reverse-lookup `getByBidItemId()`

### Table: `bid_items`

**File**: `lib/core/database/schema/quantity_tables.dart:5-24`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| project_id | TEXT | NOT NULL, FK → projects(id) ON DELETE CASCADE |
| item_number | TEXT | NOT NULL |
| description | TEXT | NOT NULL |
| unit | TEXT | NOT NULL |
| bid_quantity | REAL | NOT NULL |
| unit_price | REAL | nullable |
| bid_amount | REAL | nullable (added v25) |
| measurement_payment | TEXT | nullable (added v7) |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

**Indexes**: `idx_bid_items_project`, `idx_bid_items_deleted_at`

### Table: `personnel_types`

**File**: `lib/core/database/schema/personnel_tables.dart:5-22`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| project_id | TEXT | NOT NULL, FK → projects(id) ON DELETE CASCADE |
| contractor_id | TEXT | FK → contractors(id) ON DELETE CASCADE (nullable) |
| name | TEXT | NOT NULL |
| short_code | TEXT | nullable |
| sort_order | INTEGER | DEFAULT 0 |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

**Indexes**: `idx_personnel_types_project`, `idx_personnel_types_contractor` (composite), `idx_personnel_types_deleted_at`

### Table: `entry_personnel_counts`

**File**: `lib/core/database/schema/personnel_tables.dart:25-41`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY (deterministic: `'epc-$entryId-$contractorId-$typeKey'`) |
| entry_id | TEXT | NOT NULL, FK → daily_entries(id) ON DELETE CASCADE |
| contractor_id | TEXT | NOT NULL, FK → contractors(id) ON DELETE CASCADE |
| type_id | TEXT | NOT NULL, FK → personnel_types(id) ON DELETE CASCADE |
| count | INTEGER | NOT NULL DEFAULT 0 |
| created_at | TEXT | NOT NULL DEFAULT '' (**empty string — breaks timestamp logic**) |
| updated_at | TEXT | NOT NULL DEFAULT '' (**empty string — breaks timestamp logic**) |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable (added v29) |
| deleted_by | TEXT | nullable (added v29) |

**Indexes**: `idx_entry_personnel_counts_entry`, `idx_entry_personnel_counts_type`, `idx_entry_personnel_counts_deleted_at`

### Table: `entry_personnel` (LEGACY)

**File**: `lib/core/database/schema/personnel_tables.dart:44-60`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| entry_id | TEXT | NOT NULL, FK → daily_entries(id) ON DELETE CASCADE |
| contractor_id | TEXT | NOT NULL, FK → contractors(id) ON DELETE CASCADE |
| foreman_count | INTEGER | NOT NULL DEFAULT 0 |
| operator_count | INTEGER | NOT NULL DEFAULT 0 |
| laborer_count | INTEGER | NOT NULL DEFAULT 0 |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

Superseded by `entry_personnel_counts` but still written to by `EntryPersonnelLocalDatasource`. Still used by `ContractorLocalDatasource.getMostFrequentIds()`.

### Table: `photos`

**File**: `lib/core/database/schema/photo_tables.dart:5-30`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| entry_id | TEXT | NOT NULL, FK → daily_entries(id) ON DELETE CASCADE |
| project_id | TEXT | NOT NULL, FK → projects(id) ON DELETE CASCADE |
| file_path | TEXT | NOT NULL |
| filename | TEXT | NOT NULL |
| remote_path | TEXT | nullable (set after upload) |
| notes | TEXT | nullable |
| caption | TEXT | nullable (added v6) |
| location_id | TEXT | FK → locations(id) ON DELETE SET NULL (added v3) |
| latitude | REAL | nullable |
| longitude | REAL | nullable |
| captured_at | TEXT | NOT NULL |
| sync_status | TEXT | DEFAULT 'pending' (LOCAL ONLY) |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

**Indexes**: `idx_photos_entry`, `idx_photos_project`, `idx_photos_sync_status`, `idx_photos_deleted_at`

### Table: `inspector_forms`

**File**: `lib/core/database/schema/toolbox_tables.dart:6-28`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| project_id | TEXT | FK → projects(id) ON DELETE CASCADE (nullable) |
| name | TEXT | NOT NULL |
| template_path | TEXT | NOT NULL |
| field_definitions | TEXT | nullable (JSON) |
| parsing_keywords | TEXT | nullable (JSON) |
| table_row_config | TEXT | nullable (JSON, added v20) |
| is_builtin | INTEGER | NOT NULL DEFAULT 0 |
| template_source | TEXT | DEFAULT 'asset' (added v14) |
| template_hash | TEXT | nullable (added v14) |
| template_version | INTEGER | DEFAULT 1 (added v14) |
| template_field_count | INTEGER | nullable (added v14) |
| template_bytes | BLOB | nullable (added v17) |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

### Table: `form_responses`

**File**: `lib/core/database/schema/toolbox_tables.dart:31-51`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| form_type | TEXT | NOT NULL DEFAULT 'mdot_0582b' (added v22) |
| form_id | TEXT | nullable (FK dropped v22) |
| entry_id | TEXT | FK → daily_entries(id) ON DELETE SET NULL |
| project_id | TEXT | NOT NULL, FK → projects(id) ON DELETE CASCADE |
| header_data | TEXT | NOT NULL DEFAULT '{}' (JSON, added v22) |
| response_data | TEXT | NOT NULL (JSON) |
| table_rows | TEXT | nullable (JSON) |
| response_metadata | TEXT | nullable (JSON, added v18) |
| status | TEXT | NOT NULL DEFAULT 'open' |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

**Indexes**: `idx_form_responses_type`, `idx_form_responses_form`, `idx_form_responses_entry`, `idx_form_responses_project`, `idx_form_responses_status`, `idx_form_responses_deleted_at`

### Table: `todo_items`

**File**: `lib/core/database/schema/toolbox_tables.dart:54-72`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| project_id | TEXT | FK → projects(id) ON DELETE CASCADE (nullable) |
| entry_id | TEXT | FK → daily_entries(id) ON DELETE SET NULL (nullable) |
| title | TEXT | NOT NULL |
| description | TEXT | nullable |
| is_completed | INTEGER | NOT NULL DEFAULT 0 |
| due_date | TEXT | nullable |
| priority | INTEGER | DEFAULT 0 |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

### Table: `calculation_history`

**File**: `lib/core/database/schema/toolbox_tables.dart:75-92`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| project_id | TEXT | FK → projects(id) ON DELETE CASCADE (nullable) |
| entry_id | TEXT | FK → daily_entries(id) ON DELETE SET NULL (nullable) |
| calc_type | TEXT | NOT NULL |
| input_data | TEXT | NOT NULL (JSON) |
| result_data | TEXT | NOT NULL (JSON) |
| notes | TEXT | nullable |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL (added v24) |
| created_by_user_id | TEXT | nullable |
| deleted_at | TEXT | nullable |
| deleted_by | TEXT | nullable |

### Table: `sync_metadata`

**File**: `database_service.dart:162-168` (inline, no schema file)

| Column | Type | Constraint |
|--------|------|------------|
| key | TEXT | PRIMARY KEY |
| value | TEXT | NOT NULL |

Stores: `last_sync_time` (ISO 8601).

### Table: `deletion_notifications` (SQLite-only)

**File**: `lib/core/database/schema/sync_tables.dart:21-33`

| Column | Type | Constraint |
|--------|------|------------|
| id | TEXT | PRIMARY KEY |
| record_id | TEXT | NOT NULL |
| table_name | TEXT | NOT NULL |
| project_id | TEXT | nullable |
| record_name | TEXT | nullable |
| deleted_by | TEXT | nullable |
| deleted_by_name | TEXT | nullable |
| deleted_at | TEXT | NOT NULL |
| seen | INTEGER | NOT NULL DEFAULT 0 |

### Tables: `extraction_metrics`, `stage_metrics` (SQLite-only, PDF telemetry)

**File**: `lib/core/database/schema/extraction_tables.dart:6-45`

Local-only PDF quality monitoring. No soft-delete. `CREATE TABLE IF NOT EXISTS`.

### Schema Verifier

**File**: `lib/core/database/schema_verifier.dart`

- Runs on every startup after `openDatabase` (~50ms)
- Checks 22 tables against `expectedSchema` map (~250 column definitions)
- For each missing column: `ALTER TABLE ... ADD COLUMN`
- Does NOT repair: missing tables, missing indexes, wrong FK constraints
- On failure: logs error, continues (no throw)

---

## 8. SQLite Migration History

All migrations in `_onUpgrade` (`database_service.dart:238-1153`), additive `if (oldVersion < N)` guards:

| Version | Changes | Lines |
|---------|---------|-------|
| v1 | Initial schema (9 tables) | onCreate |
| v2 | sync_queue table + indexes | 240-258 |
| v3 | photos.location_id | 262-263 |
| v4 | personnel_types + entry_personnel_counts + seed data | 267-388 |
| v5 | 3 sync/date indexes | 391-402 |
| v6 | photos.caption | 406-407 |
| v7 | bid_items.measurement_payment | 411-417 |
| v8 | projects: mode, mdot_* fields | 421-433 |
| v9 | updated_at on 6 tables, created_at/updated_at on 3 entry tables | 437-514 |
| v10-v11 | Personnel types: project-scoped → contractor-scoped migration | 517-520, 1159-1256 |
| v12 | entry_contractors table + backfill | 523-550 |
| v13 | Toolbox tables (forms, todos, calculator) + 13 indexes | 553-659 |
| v14 | inspector_forms: template_source, hash, version, field_count | 662-688 |
| v15-v16 | Skipped (version bump without migration block) | — |
| v17 | inspector_forms.template_bytes BLOB | 692-699 |
| v18 | form_responses.response_metadata | 702-710 |
| v19 | Drop daily_entries.test_results | 716-723 |
| v20 | inspector_forms.table_row_config | 726-734 |
| v21 | extraction_metrics + stage_metrics tables | 737-743 |
| v22 | Drop legacy form tables, add form_type/header_data/form_id changes | 746-777 |
| v23 | projects: control_section_id, route_street, construction_eng | 780-784 |
| v24 | Multi-tenant tables (companies, user_profiles, join_requests) + created_by_user_id on all tables | 788-886 |
| v25 | sync_metadata table + bid_items.bid_amount | 891-898 |
| v26 | daily_entries: submitted_at, revision_number, nullable location_id (table rebuild) | 901-1008 |
| v27 | Orphan cleanup + daily_entries rebuild (location_id FK → ON DELETE SET NULL) | 1010-1097 |
| v28 | Soft-delete columns (deleted_at, deleted_by) on 16 tables + deletion_notifications | 1099-1138 |
| v29 | Hotfix: deleted_at/deleted_by on entry_contractors + entry_personnel_counts (missed in v28) | 1140-1153 |

---

## 9. Supabase Schema

All shared tables match SQLite schema above with the following differences documented in [Section 11](#11-schema-divergences).

### Supabase-Only Tables

**`companies`**: UUID PK, `name TEXT UNIQUE` (CHECK length 2-200), `created_at`, `updated_at`. RLS: see own company only. Creation via `create_company()` RPC only.

**`user_profiles`**: UUID PK (FK → auth.users ON DELETE CASCADE), `company_id UUID` (FK → companies ON DELETE SET NULL), `role` (CHECK admin/engineer/inspector/viewer), `status` (CHECK pending/approved/rejected/deactivated), `display_name`, `cert_number`, `phone`, `position`, `last_synced_at`, timestamps.

**`company_join_requests`**: UUID PK, `user_id`, `company_id`, `status`, `requested_at`, `resolved_at`, `resolved_by`. Partial unique index on `(user_id, company_id) WHERE status='pending'`.

**`user_fcm_tokens`**: UUID PK (FK → auth.users ON DELETE CASCADE), `token TEXT`, `updated_at`. RLS: user-scoped only.

**`app_config`**: TEXT PK (CHECK key in allowed set), `value TEXT` (CHECK constraints), `updated_at`. RLS: SELECT only for authenticated. No client writes.

### Storage Buckets

**`entry-photos`**: Private. Path: `entries/{companyId}/{entryId}/{filename}.{jpg|jpeg|png|heic}`. Validated by regex at `photo_remote_datasource.dart:50-55`. RLS: company-scoped via `(storage.foldername(name))[1] = get_my_company_id()::text`. Signed URLs with 1-hour expiry.

**`releases`**: Public read. 500MB limit. APK MIME types only. Service-role writes only.

---

## 10. Supabase Migration History

13 migration files in chronological order:

| Migration | Purpose |
|-----------|---------|
| `20260126000000_toolbox_tables.sql` | Toolbox tables (v13 parity). Broad `authenticated USING(true)` RLS. |
| `20260128000000_registry_tables.sql` | Registry tables (later dropped). |
| `20260222000000_catchup_v23.sql` | Catch-up to SQLite v23. Projects mode/MDOT fields, photos caption/location_id, personnel_types, entry_personnel_counts, entry_equipment, entry_contractors, calculation_history.updated_at. Part 10: `created_by_user_id` on 18 tables. Part 11: `company_id` on projects. |
| `20260222100000_multi_tenant_foundation.sql` | **The security migration.** Creates companies/user_profiles/join_requests. All RPCs. All company-scoped RLS (replaces broad policies). enforce_created_by triggers on 17 tables. Storage RLS. Drops anon policies. |
| `20260222200000_add_fcm_tokens.sql` | FCM token table. |
| `20260222300000_backfill_user_profiles.sql` | Backfill profiles for pre-existing auth.users. |
| `20260222400000_add_profile_insert_policy.sql` | `insert_own_profile` policy (needed for upsert). |
| `20260302000000_add_bid_amount_column.sql` | `bid_items.bid_amount`. Drop `daily_entries.test_results`. |
| `20260303000000_app_config_and_entry_status.sql` | `app_config` table. `daily_entries`: submitted_at, revision_number. Status validation trigger. |
| `20260303100000_releases_storage_bucket.sql` | Releases bucket. |
| `20260304000000_soft_delete_columns.sql` | `deleted_at`/`deleted_by` on 16 tables. `purge_soft_deleted_records()` function. pg_cron daily job. |
| `20260304100000_soft_delete_missing_tables.sql` | Hotfix: entry_contractors + entry_personnel_counts soft-delete columns. |
| `20260304200000_drop_sync_status_from_supabase.sql` | **UNDEPLOYED** (current branch). Drops sync_status from daily_entries + photos. |

---

## 11. Schema Divergences

### Critical Column Mismatches

| Table | Column | Supabase | SQLite | Impact |
|-------|--------|----------|--------|--------|
| `inspector_forms` | `deleted_at` | **MISSING** | TEXT | Soft-deleting forms can never propagate to Supabase. Server-side purge job skips forms. |
| `inspector_forms` | `deleted_by` | **MISSING** | TEXT | Same. |
| `entry_contractors` | `updated_at` | **MISSING** | TEXT (nullable) | Last-write-wins conflict resolution silently skips updates (`remoteUpdated == null`) |
| `entry_personnel_counts` | `updated_at` | **MISSING** | TEXT NOT NULL DEFAULT '' | Same. Plus the empty-string default breaks timestamp parsing. |
| `calculation_history` | `updated_at` | TIMESTAMPTZ (nullable) | TEXT NOT NULL | Nullability mismatch. |
| `daily_entries` | `sync_status` | Pending DROP (migration 13) | TEXT DEFAULT 'pending' | Handled by BLOCKER-27 strip/force logic. |
| `photos` | `sync_status` | Pending DROP (migration 13) | TEXT DEFAULT 'pending' | Same. |

### Type Conversions (handled in `_convertForRemote`/`_convertForLocal`)

| Table | Column | Supabase | SQLite | Conversion |
|-------|--------|----------|--------|------------|
| projects | is_active | BOOLEAN | INTEGER | int↔bool |
| entry_equipment | was_used | BOOLEAN/INTEGER | INTEGER | int↔bool |
| inspector_forms | is_builtin | BOOLEAN | INTEGER | int↔bool |
| todo_items | is_completed | BOOLEAN | INTEGER | int↔bool |
| form_responses | response_data, header_data, table_rows, response_metadata | JSONB | TEXT | jsonEncode/jsonDecode |

### Type Conversions NOT Handled

| Table | Column | Supabase | SQLite | Issue |
|-------|--------|----------|--------|-------|
| inspector_forms | field_definitions | JSONB | TEXT | No explicit conversion — raw string passed |
| inspector_forms | parsing_keywords | JSONB | TEXT | Same |
| calculation_history | input_data | JSONB | TEXT | Same |
| calculation_history | result_data | JSONB | TEXT | Same |
| inspector_forms | template_bytes | BYTEA | BLOB | No explicit conversion |

---

## 12. RLS Policies

All 17 data tables follow the same 4-policy pattern (post multi-tenant migration):

```sql
company_{table}_select — FOR SELECT USING (scope = get_my_company_id())
company_{table}_insert — FOR INSERT WITH CHECK (scope = get_my_company_id() AND NOT is_viewer())
company_{table}_update — FOR UPDATE USING (scope = get_my_company_id() AND NOT is_viewer())
company_{table}_delete — FOR DELETE USING (scope = get_my_company_id() AND NOT is_viewer())
```

Scope resolution:
- **Direct** (`company_id` column): `projects`
- **One-hop** (`project_id → projects`): `locations`, `contractors`, `bid_items`, `personnel_types`, `daily_entries`, `photos`, `inspector_forms`, `form_responses`, `todo_items`, `calculation_history`
- **Two-hop** (`entry_id → daily_entries → projects`): `entry_quantities`, `entry_contractors`, `entry_personnel_counts`, `entry_equipment`, `entry_personnel`
- **Two-hop** (`contractor_id → contractors → projects`): `equipment`

Storage RLS: `entry-photos` bucket scoped by `(storage.foldername(name))[1] = get_my_company_id()::text`.

`user_profiles`: read own + company members. Update own personal fields only (role/status/company_id/last_synced_at locked).

`app_config`: SELECT only for authenticated. No client writes.

---

## 13. Database Functions, RPCs, and Triggers

### Helper Functions (SECURITY DEFINER, STABLE)

- `get_my_company_id()` → UUID: returns caller's company_id only if `status='approved'`. NULL = no company.
- `is_viewer()` → BOOLEAN: returns true if caller's role is viewer and status is approved.

### Admin RPCs (SECURITY DEFINER, all REVOKE'd from anon)

| Function | Purpose |
|----------|---------|
| `create_company(company_name)` | Create company + promote caller to admin |
| `search_companies(query)` | ILIKE search, 3-char min, only if caller has no company |
| `approve_join_request(request_id, assigned_role)` | Admin approves pending request |
| `reject_join_request(request_id)` | Admin rejects |
| `update_member_role(target_user_id, new_role)` | Admin changes role; last-admin guard |
| `deactivate_member(target_user_id)` | Admin deactivates; last-admin guard |
| `reactivate_member(target_user_id)` | Admin reactivates |
| `promote_to_admin(target_user_id)` | Admin promotes; target must be approved |
| `update_last_synced_at()` | SECURITY DEFINER: sets last_synced_at for auth.uid() |

### Triggers

**`update_updated_at_column()`**: BEFORE UPDATE on all major tables. Sets `updated_at = NOW()`.

**`enforce_created_by()`**: BEFORE INSERT on 17 data tables. SECURITY DEFINER. Overwrites `created_by_user_id` with `auth.uid()`.

**`validate_entry_status_transition()`**: BEFORE UPDATE on `daily_entries`. Enforces monotonic revision_number, prevents submitted_at backdating.

**`handle_new_user()`**: AFTER INSERT on `auth.users`. Creates `user_profiles` row.

**`purge_soft_deleted_records()`**: pg_cron daily at 03:00 UTC. Hard-deletes rows where `deleted_at < NOW() - 30 days`. Children-first FK order. **Does NOT cover `inspector_forms`** (missing deleted_at column).

**`update_app_config_timestamp()`**: BEFORE UPDATE on `app_config`.

---

## 14. Auth System

### Auth Flow

- **Type**: PKCE (`lib/main.dart:152-155`)
- **Deep link**: `com.fieldguideapp.inspector://login-callback` (`auth_service.dart:16`)
- **Supabase init**: only when `isConfigured` is true (`main.dart:147`)
- **JWT expiry**: 3600s (1 hour), refresh rotation enabled

### Startup Sequence (`main.dart:85-411`)

1. `PreferencesService.initialize()` — load stored version, recovery flag
2. `DatabaseService.initializeFfi()` + `database` init
3. `Supabase.initialize(url, anonKey, authFlowType: pkce)`
4. `Firebase.initializeApp()` on mobile
5. `BackgroundSyncHandler.initialize()`
6. `AuthProvider` constructed — loads cached user, triggers `loadUserProfile()`
7. App upgrade detection: stored version != current → `signOutLocally()`
8. Inactivity timeout check (7 days via flutter_secure_storage)
9. `AppConfigProvider.checkConfig()` — fetch app_config with 5s timeout
10. Force-reauth check: if `reauth_before` is in future → `signOut()`

### Password Recovery (OTP-based)

1. `resetPasswordForEmail()` → Supabase sends 6-digit OTP
2. User enters OTP → `verifyOTP(type: OtpType.recovery)` → fires `passwordRecovery` event
3. `AuthProvider` catches event → sets `_isPasswordRecovery = true`, persists to SharedPreferences (SEC-8)
4. Router traps user on `/update-password`
5. New password set → `completePasswordRecovery()` → clears flag → `signOut()` (SEC-3: destroys recovery session)

### Auth-Sync Integration

```
AuthProvider.userProfile?.companyId
  → main.dart:289-298 updateSyncContext() closure
  → syncOrchestrator.setAdapterCompanyContext(companyId, userId)
  → SyncService.setCompanyContext(companyId, userId)
  → _companyId, _userId stored in-memory
```

**Sync readiness gate** (`main.dart:344-347`): `isAuthenticated && userProfile?.companyId != null`. Sync blocked until user has approved company.

### Known Auth Defect

**`secure_password_change = false` in `supabase/config.toml`** — any authenticated session (including stolen tokens) can change password without reauthentication. See `_defects-auth.md:26-29`.

---

## 15. Data Layer

### Base Datasource: `GenericLocalDatasource`

**File**: `lib/shared/datasources/generic_local_datasource.dart`

- `_notDeletedFilter = 'deleted_at IS NULL'` prepended to every read query (line 43)
- `delete(id)` → calls `softDelete()` → sets `deleted_at`, `deleted_by`, `updated_at` (lines 111-134). **Does NOT set sync_status. Does NOT write to sync_queue.**
- `softDelete(id, {userId})` — same fields. The `userId` is optional.
- `restore(id)` — clears deleted_at/deleted_by, sets updated_at
- `hardDelete(id)` — actual DELETE statement
- `getDeleted()` — reads `deleted_at IS NOT NULL`
- `insertAll(items)` — uses `database.batch()` with `noResult: true`
- `getByIdIncludingDeleted()` — raw query without soft-delete filter

### ProjectScopedDatasource

**File**: `lib/shared/datasources/project_scoped_datasource.dart`

Extends `GenericLocalDatasource`. Adds `getByProjectId()`, `softDeleteByProjectId()`, `restoreByProjectId()`, `getDeletedByProjectId()`.

### Repository Sync Integration

| Repository | sync_status | sync_queue | Notes |
|------------|:-----------:|:----------:|-------|
| ProjectRepository | No | No | **Zero sync integration** |
| DailyEntryRepository | Yes (set on create/update/submit) | No | Works via `_pushPendingEntries` |
| PhotoRepository | Yes (set on create) | No | Create works. Update/delete: **no sync** |
| LocationRepository | No | No | **Zero sync integration** |
| ContractorRepository | No | No | **Zero sync integration** |
| EquipmentRepository | No | No | **Zero sync integration** |
| BidItemRepository | No | No | **Zero sync integration** |
| PersonnelTypesScreen | No | Yes (directly in UI) | Queues updates from screen |

### Provider Sync Integration

| Provider | Triggers Sync? | How |
|----------|:--------------:|-----|
| ProjectProvider | No | Nothing queued. `deleteProject()` calls `SoftDeleteService` which has no sync integration. |
| DailyEntryProvider | Implicit | Sets `sync_status = 'pending'` on create/update/submit. `delete()` soft-deletes with NO sync trigger. |
| PhotoProvider | Partial | `addPhoto()` creates with pending status. `updatePhoto()` and `deletePhoto()` have NO sync. `deletePhoto()` is a **hard delete**. |
| InspectorFormProvider | Partial | Queues form_responses (insert/update/delete). Does NOT queue inspector_forms CRUD. |
| TodoProvider | Yes | Queues all todo_items operations. |
| CalculatorProvider | Partial | Queues insert/delete. Does NOT queue updates. |
| ContractorProvider | No | No sync integration. |
| LocationProvider | No | No sync integration. |
| BidItemProvider | No | No sync integration. |

### Datasource Gaps

- `PhotoLocalDatasource.deleteByEntryId()` (`photo_local_datasource.dart:42-48`): **hard delete**, not soft-delete. Bypasses soft-delete system.
- `entry_contractors_local_datasource.setForEntry()` (line 132-151): **hard-deletes then re-inserts** in transaction. Not soft-delete aware.
- `daily_entry_local_datasource.getDatesWithEntries()` (line 82-89): raw query **without `deleted_at IS NULL`** — deleted entries appear in calendar.
- `location_local_datasource.search()` (line 29-39): raw query **without soft-delete filter** — deleted locations appear in search.
- `SyncStatusMixin.getPendingSync()`: queries `sync_status != 'synced'` **without filtering `deleted_at IS NULL`** — soft-deleted records with pending status appear in sync queue.

---

## 16. User Flow Analysis

### Create Project

```
ProjectProvider.createProject() → ProjectRepository.create() → ProjectLocalDatasource.insert() → SQLite INSERT → NOTHING ELSE
```

**Reaches Supabase**: Only on first-ever sync via `_pushBaseData()`. After that, NEVER. No `sync_status`, no `queueOperation()`.

### Edit Project

```
ProjectProvider.updateProject() → ProjectRepository.updateProject() → SQLite UPDATE → NOTHING ELSE
```

**Reaches Supabase**: NEVER after first sync.

### Delete (Soft-Delete) Project

```
ProjectProvider.deleteProject() → SoftDeleteService.cascadeSoftDeleteProject() → SQLite transaction: sets deleted_at/deleted_by on project + all children → NOTHING ELSE
```

**Reaches Supabase**: NEVER. No sync_status change, no queue entry. Pull may overwrite local soft-delete with remote (non-deleted) version.

### Create Daily Entry

```
DailyEntryProvider.createEntry() → DailyEntryRepository.create() → SQLite INSERT (syncStatus defaults 'pending') → [next syncAll()] → _pushPendingEntries() → Supabase upsert → local set 'synced'
```

**Works correctly.**

### Take/Attach Photo

```
PhotoProvider.addPhoto() → PhotoRepository.createPhoto() → SQLite INSERT (syncStatus 'pending') → [next syncAll()] → _pushPendingPhotos() → Storage upload + DB upsert → local set 'synced' + remote_path stored
```

**Works for creation.** Photo updates (notes/captions) and deletes do NOT sync.

### Empty Trash

```
TrashScreen._confirmEmptyTrash() → SoftDeleteService.purgeExpiredRecords(retentionDays: 0) → Hard DELETE from SQLite → NOTHING ELSE
```

**Records vanish locally but survive in Supabase. Next pull resurrects them.** This is BLOCKER-26.

### Delete Forever (Single Item)

```
TrashScreen (line 311) → database.delete(tableName, ...) → NOTHING ELSE
```

**Same as Empty Trash — no Supabase notification.**

### Restore from Trash

```
TrashScreen._restoreItem() → SoftDeleteService.restoreWithCascade() → SQLite UPDATE: clear deleted_at/deleted_by → NOTHING ELSE
```

**Propagates to Supabase only if pull's edit-wins conflict resolution detects the local `updated_at` is newer than the remote `deleted_at`. Works but is indirect.**

### App Comes Online After Offline

```
SyncService._initConnectivity() fires → _checkDnsReachability() → scheduleDebouncedSync() (2s) → syncAll() → push + pull
```

---

## 17. Push Coverage Map

After first sync (when `_pushBaseData` no longer fires):

| Table | sync_status | sync_queue | First-sync only | Result |
|-------|:-----------:|:----------:|:---------------:|--------|
| projects | - | - | Yes | **NEVER syncs after first** |
| locations | - | - | Yes | **NEVER syncs after first** |
| contractors | - | - | Yes | **NEVER syncs after first** |
| equipment | - | - | Yes | **NEVER syncs after first** |
| bid_items | - | - | Yes | **NEVER syncs after first** |
| personnel_types | - | Yes (UI) | Yes | Partial (only from screen) |
| daily_entries | Yes | - | Yes | **Works** |
| photos (create) | Yes | - | - | **Works** |
| photos (update) | - | - | - | **NEVER syncs** |
| photos (delete) | - | - | - | **NEVER syncs** (hard delete) |
| entry_quantities | - | - | Yes | **NEVER syncs after first** |
| entry_equipment | - | - | Yes | **NEVER syncs after first** |
| entry_contractors | - | - | **Not even on first** | **NEVER syncs** |
| entry_personnel_counts | - | - | **Not even on first** | **NEVER syncs** |
| inspector_forms | - | - | Yes | **NEVER syncs after first** |
| form_responses | - | Yes (all ops) | Yes | **Works** |
| todo_items | - | Yes (all ops) | Yes | **Works** |
| calculation_history | - | Yes (insert/delete) | Yes | **Update gap** |

**Summary**: 9/16 synced tables have zero push capability after first install. This includes the most critical table: `projects`.

---

## 18. Complete Gap Inventory

### GAP-1: Projects/Locations/Contractors/Equipment/BidItems never sync after first install
**Tables**: projects, locations, contractors, equipment, bid_items
**Root cause**: No `sync_status` column. No `queueOperation()` calls in repositories or providers. `_pushBaseData()` only fires when `_lastSyncTime == null`.
**Impact**: Any CRUD after first login is invisible to Supabase and other team members.

### GAP-2: Soft-deletes never reach Supabase
**Tables**: All 16 soft-delete-capable tables
**Root cause**: `SoftDeleteService.cascadeSoftDeleteProject()` and `GenericLocalDatasource.softDelete()` set `deleted_at` locally but queue nothing. No `sync_status` change.
**Impact**: Deleted projects/entries/items reappear on next sync pull.

### GAP-3: Empty Trash / Delete Forever never cleans Supabase
**Files**: `trash_screen.dart:311` (Delete Forever), `trash_screen.dart:359` (Empty Trash)
**Root cause**: Both use direct `database.delete()` or `purgeExpiredRecords()` — local-only. `hardDeleteWithSync()` exists but is never called. Even if called, `_processSyncQueueItem()` has no `case 'purge'`.
**Impact**: Records survive in Supabase forever, resurrect on next pull.

### GAP-4: Photo updates never sync
**Files**: `photo_repository.dart:74`, `photo_provider.dart` updatePhoto
**Root cause**: `updatePhoto()` does not set `sync_status = 'pending'` or queue operation.
**Impact**: Photo notes/captions are local-only.

### GAP-5: Photo deletes are hard deletes
**Files**: `photo_repository.dart:88` (deletePhoto), `photo_local_datasource.dart:42-48` (deleteByEntryId)
**Root cause**: Uses `database.delete()` directly, bypassing soft-delete. No Supabase delete queued.
**Impact**: Deleted photos remain in Supabase DB and Storage forever.

### GAP-6: entry_contractors and entry_personnel_counts never sync at all
**Root cause**: Missing from `_pushBaseData` table list (lines 653-666). Missing from `_pullRemoteChanges` table list (lines 998-1015). No provider queues operations for them.
**Impact**: These tables are essentially local-only despite existing in Supabase.

### GAP-7: entry_equipment/entry_quantities pull silently fails
**Root cause**: Pull orders by `created_at` but these tables may not have `created_at` reliably in Supabase (the pull query uses `.order('created_at')` which fails if column doesn't exist).
**Impact**: 0 records pulled, error swallowed.

### GAP-8: Inspector forms (templates) never sync after first install
**Root cause**: `InspectorFormProvider.addForm()`, `updateForm()`, `deleteForm()` do not call `queueOperation()`.
**Impact**: Form templates created/modified after first login are local-only.

### GAP-9: Inspector forms missing soft-delete columns in Supabase
**Root cause**: `20260304000000_soft_delete_columns.sql` does NOT add `deleted_at`/`deleted_by` to `inspector_forms`.
**Impact**: Even if sync were fixed, soft-delete state couldn't propagate. Server-side purge job skips forms.

### GAP-10: entry_contractors/entry_personnel_counts missing updated_at in Supabase
**Root cause**: Catchup migration created these tables without `updated_at`. No subsequent migration adds it.
**Impact**: Last-write-wins conflict resolution fails (`remoteUpdated == null` → condition at sync_service.dart:1374 always true, remote always overwrites).

### GAP-11: entry_personnel_counts timestamps use empty-string defaults
**Root cause**: `personnel_tables.dart:32-33` has `created_at TEXT NOT NULL DEFAULT ''` and `updated_at TEXT NOT NULL DEFAULT ''`.
**Impact**: `DateTime.parse('')` throws. Any timestamp comparison logic breaks.

### GAP-12: No incremental pull
**Root cause**: `_pullRemoteRecordsInChunks()` does full-table SELECT with no timestamp filter.
**Impact**: O(n) network calls on every sync. Gets worse as data grows.

### GAP-13: Background sync bypasses orchestrator retry logic
**Root cause**: `BackgroundSyncHandler` calls `SyncService.syncAll()` directly, not through `SyncOrchestrator._syncWithRetry()`.
**Impact**: Background sync failures have no retry with exponential backoff.

### GAP-14: SyncStatus.failed vs 'error' inconsistency
**Root cause**: `_pushPendingEntries` writes `'error'`, `_pushPendingPhotos` writes `SyncStatus.failed.toJson()`. `getPendingCount()` only queries `'pending'`.
**Impact**: Failed entries/photos are never retried and invisible in UI counts.

### GAP-15: Restore from trash has no proactive sync push
**Root cause**: `restoreWithCascade()` clears `deleted_at` locally but doesn't queue a push. Relies on pull's edit-wins conflict path — which only works if Supabase has the record as deleted (often it doesn't, per GAP-2).

### GAP-16: JSONB fields on inspector_forms and calculation_history not explicitly converted
**Root cause**: Only `form_responses` JSONB fields have jsonEncode/jsonDecode conversion in `_convertForLocal()`. `inspector_forms.field_definitions`, `inspector_forms.parsing_keywords`, `calculation_history.input_data`, `calculation_history.result_data` are passed as raw strings.
**Impact**: May work accidentally if Supabase auto-casts, but fragile.

### GAP-17: Deleted entries appear in calendar date markers
**Root cause**: `daily_entry_local_datasource.getDatesWithEntries()` (line 82-89) uses raw query without `deleted_at IS NULL`.

### GAP-18: Deleted locations appear in search
**Root cause**: `location_local_datasource.search()` (line 29-39) uses raw query without soft-delete filter.

### GAP-19: Secure password change disabled in Supabase config
**Root cause**: `secure_password_change = false` in `supabase/config.toml`.
**Impact**: Stolen JWT = password change without reauthentication.

---

## 19. Suggestions for Rewrite

### Unified Change Tracking
- Replace `sync_status` column + `sync_queue` table with a single `change_log` table
- Auto-populate via SQLite triggers on INSERT/UPDATE/DELETE across all synced tables
- No more manual `queueOperation()` or `sync_status` management at the provider/repository level
- Base datasource writes → SQLite trigger fires → change_log entry → next sync processes it

### Incremental Pull
- `SELECT * FROM table WHERE updated_at > last_pull_time` per table
- Store per-table `last_pull_time` in `sync_metadata`
- Falls back to full pull on first sync or when metadata is missing

### Schema Alignment Migration
- Add `updated_at` to `entry_contractors` and `entry_personnel_counts` in Supabase
- Add `deleted_at`/`deleted_by` to `inspector_forms` in Supabase
- Fix empty-string timestamp defaults in SQLite `entry_personnel_counts`
- Add JSONB conversion for `inspector_forms` and `calculation_history` fields
- Add UNIQUE index on `projects(company_id, project_number)` (BLOCKER-24)

### Soft-Delete Sync
- `deleted_at` changes flow in both directions automatically via change_log
- Purge only after confirming Supabase has the `deleted_at` value (sync-then-purge)
- `hardDeleteWithSync()` becomes the only purge path, and the engine handles the Supabase DELETE

### Photo Lifecycle
- Soft-delete photos (not hard delete)
- Track `remote_path` to avoid re-uploads
- Storage cleanup as separate post-sync phase
- Photo updates (notes/captions) tracked by change_log like everything else

### Auth Integration
- Keep existing PKCE/RLS/role system (solid)
- Tighter sync gate: sync only when `isAuthenticated && hasApprovedCompany`
- Company context injected at engine initialization, not per-call
- Fix `secure_password_change = false`

### Modular Architecture
- SyncEngine (push/pull/conflict) — replaces 1535-line SyncService
- ChangeTracker — replaces sync_status + sync_queue
- TableAdapter per table — handles type conversion, column mapping, validation
- Table config registry — declares which tables sync, their column maps, FK order

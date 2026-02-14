# Sync PRD

## Purpose
Sync ensures that data created offline on a mobile device reaches the cloud and vice versa. Construction inspectors work in the field where connectivity is unreliable -- tunnels, basements, rural highways. The sync system must guarantee no data loss while supporting multiple backend targets based on project mode.

## Core Capabilities
- Offline-first queue: all local CRUD operations are captured in a `sync_queue` table before upload
- Dual-backend routing: Local Agency projects sync to Supabase, MDOT projects will sync to AASHTOWare (planned)
- Adapter pattern: abstract `SyncAdapter` interface with concrete `SupabaseSyncAdapter` and `MockSyncAdapter` implementations
- Sync orchestrator: coordinates sync across adapters, tracks overall status, manages callbacks
- Entity-level sync: push/pull projects, daily entries, photos, and related child records
- Debounced sync scheduling: prevents rapid successive syncs during burst edits
- Progress tracking: reports processed/total counts for UI progress indicators
- Error handling: tracks attempt count and last error per queued item; retries on next sync cycle
- Status reporting: idle, syncing, success, error, offline, authRequired states

## Data Model
- Primary entity: Sync Queue (SQLite table: `sync_queue`)
- Key fields: `id`, `table_name`, `record_id`, `operation` (INSERT/UPDATE/DELETE), `payload` (JSON), `created_at`, `attempts`, `last_error`
- Domain types: `SyncResult` (pushed, pulled, errors, errorMessages), `SyncAdapterStatus` enum
- Sync: The sync feature itself is the sync mechanism -- it does not sync its own queue to the cloud. The queue is consumed and cleared upon successful upload.

## User Flow
Sync operates mostly in the background. When inspectors save data, the repository layer enqueues a sync operation. If WiFi auto-sync is enabled, the orchestrator picks it up automatically. Inspectors can also trigger a manual sync from the Settings screen's Cloud Sync section, which shows pending count, last sync time, and current status. A sync indicator appears in the app bar during active sync.

## Offline Behavior
The sync queue is the offline behavior -- it is the mechanism that makes the entire app offline-first. When offline, operations accumulate in `sync_queue`. When connectivity returns, the orchestrator processes the queue in FIFO order. Failed items retain their error state and retry on the next cycle. The system never blocks user interaction waiting for sync.

## Dependencies
- Features: projects (sync per-project), entries (sync entries), photos (sync photos with file upload), auth (Supabase authentication required)
- Packages: `supabase_flutter`, `sqflite`, `connectivity_plus` (network detection)

## Owner Agent
backend-supabase-agent (Supabase adapter, RLS, remote schema), backend-data-layer-agent (sync queue, orchestrator)

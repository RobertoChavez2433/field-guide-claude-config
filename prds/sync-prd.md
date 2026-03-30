# Sync PRD

## Purpose
Sync ensures that data created offline on a mobile device reaches the cloud and vice versa. Construction inspectors work in the field where connectivity is unreliable -- tunnels, basements, rural highways. The sync system must guarantee no data loss while supporting multiple backend targets based on project mode.

## Core Capabilities
- Change-log trigger system: SQLite triggers on INSERT/UPDATE/DELETE write to a `change_log` table automatically, capturing every mutation without repository-layer involvement
- Per-table adapter pattern: one `TableAdapter` subclass per syncable table handles push and pull independently; failures are isolated per adapter, not all-or-nothing
- Ordered sync registry: `SyncRegistry` registers all adapters in dependency order (parents before children) so FK constraints are never violated during pull
- Orchestration: `SyncOrchestrator` coordinates manual sync, push-triggered sync, and lifecycle-driven sync; `SyncEngine` executes the low-level push/pull loop
- Conflict resolution: per-record conflict detection with a dedicated `ConflictViewerScreen` for inspector review
- Post-sync integrity: `IntegrityChecker` verifies FK relationships after every sync run; `OrphanScanner` finds and handles orphaned records
- Concurrency guard: `SyncMutex` ensures only one sync run executes at a time
- Push notifications: `FcmHandler` receives FCM push notifications and triggers a pull sync in response
- Lifecycle integration: `SyncLifecycleManager` starts sync when the app foregrounds and suspends it cleanly on background
- Status reporting: idle, syncing, success, error, offline, authRequired states surfaced through `SyncProvider`

## Data Model
- Change capture: `change_log` SQLite table — fields: `id`, `table_name`, `record_id`, `operation` (INSERT/UPDATE/DELETE), `changed_at`, `payload` (JSON snapshot)
- Change detection: `ChangeTracker` reads `change_log` to build the pending work list for each sync run; entries are deleted from `change_log` only after confirmed remote acknowledgment
- Domain types: `SyncResult` (pushed, pulled, conflicts, errors, errorMessages), `SyncAdapterStatus` enum, `ConflictWinner` enum (in `ConflictResolver`)
- The sync feature does not sync its own tables to the cloud. `change_log` is local-only and consumed during each run.

## Architecture

### Core Engine
| Component | Responsibility |
|-----------|---------------|
| `ChangeTracker` | Reads `change_log`; returns pending changes grouped by table |
| `SyncEngine` | Iterates registered adapters; calls push then pull per adapter; collects results |
| `SyncOrchestrator` | Top-level coordinator; triggers engine on manual request, FCM push, or lifecycle event |
| `SyncRegistry` | Holds ordered list of all concrete adapters; enforces registration order for FK safety |
| `SyncMutex` | Blocks concurrent engine invocations; queues at most one pending run |

### Adapters
- `TableAdapter` — abstract base class defining `push(List<ChangeRecord>)` and `pull()` contracts
- 20+ concrete adapters, one per syncable table (projects, daily_entries, photos, contractors, locations, quantities, forms, todos, settings, consent records, support records, and others)
- Each adapter owns its own error handling; a failing adapter does not abort adapters later in the registry

### Post-Sync Integrity
| Component | Responsibility |
|-----------|---------------|
| `IntegrityChecker` | Runs after every successful sync; queries FK relationships to verify referential integrity |
| `OrphanScanner` | Identifies records whose parent was deleted remotely; applies configured resolution (soft-delete or flag for review) |

### Push Sync
- `FcmHandler` receives an FCM data message, extracts the sync trigger payload, and calls `SyncOrchestrator.triggerPull()`
- Pull-only on FCM to avoid write conflicts from concurrent devices

### Lifecycle
- `SyncLifecycleManager` listens to `AppLifecycleState`; triggers a sync on `resumed`; cancels in-flight operations gracefully on `paused`/`detached`

## User Flow
Sync operates mostly in the background. When inspectors save data, the SQLite trigger writes to `change_log` automatically. If connectivity is available and no sync is already running, `SyncOrchestrator` picks up pending changes. Inspectors can trigger a manual sync from `SyncDashboardScreen`, which shows last sync time, pending change count, per-adapter status, and a manual sync button. A sync indicator appears in the app bar during active sync. Conflicts detected during pull are surfaced on `ConflictViewerScreen` for inspector resolution.

## Offline Behavior
The `change_log` table is the offline mechanism. When offline, all mutations accumulate in `change_log` via triggers. When connectivity returns, `SyncOrchestrator` processes pending changes in `change_log` order. Failed adapter runs retain their error state and retry on the next cycle. The system never blocks user interaction waiting for sync.

## Screens
| Screen | Purpose |
|--------|---------|
| `SyncDashboardScreen` | Shows sync status, last sync time, pending change count, per-adapter status strip, manual trigger button |
| `ConflictViewerScreen` | Lists unresolved conflicts with field-level diff; inspector accepts local or remote version per record |

## Provider
`SyncProvider` — exposes `SyncStatus`, last sync timestamp, pending change count, and conflict count to the widget tree via Provider

## Dependencies
- Features: projects, entries, photos, auth (Supabase session required for push/pull)
- Packages: `supabase_flutter`, `sqflite`, `connectivity_plus`, `firebase_messaging`

## Owner Agent
backend-supabase-agent (remote schema, RLS, FCM), backend-data-layer-agent (change_log triggers, adapters, integrity checks)

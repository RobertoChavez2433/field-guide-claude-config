# Sync PRD

## Purpose
Sync ensures that data created offline on a mobile device reaches the cloud and vice versa. Construction inspectors work in the field where connectivity is unreliable -- tunnels, basements, rural highways. The sync system must guarantee no data loss while supporting multiple backend targets based on project mode.

## Target Direction
- Startup and foreground auto-sync must feel fast and predictable.
- Startup/foreground auto-sync must not run a full project-wide `pushAndPull()` by default.
- Sync must distinguish between user-facing freshness work and heavier maintenance work.
- The system should become smarter about remote changes by combining:
  - local `change_log` for incremental push
  - Supabase-originated foreground invalidation hints delivered over server-issued opaque private channels
  - FCM background invalidation hints for wake-up and catch-up
- A manual full-sync action must be available in the main app chrome, not only in Settings.

## Core Capabilities
- Change-log trigger system: SQLite triggers on INSERT/UPDATE/DELETE write to a `change_log` table automatically, capturing every mutation without repository-layer involvement
- Per-table adapter pattern: one `TableAdapter` subclass per syncable table handles push and pull independently; failures are isolated per adapter, not all-or-nothing
- Ordered sync registry: `SyncRegistry` registers all adapters in dependency order (parents before children) so FK constraints are never violated during pull
- Sync modes: `Quick sync` for startup/foreground freshness, `Full sync` for user-requested broad refresh, and `Maintenance sync` for deferred integrity/profile work
- Orchestration: `SyncOrchestrator` coordinates quick sync, full sync, push-triggered sync, and lifecycle-driven sync; `SyncEngine` executes the low-level push/pull loop
- Conflict resolution: per-record conflict detection with a dedicated `ConflictViewerScreen` for inspector review
- Post-sync integrity: `IntegrityChecker` verifies FK relationships after every sync run; `OrphanScanner` finds and handles orphaned records
- Concurrency guard: `SyncMutex` ensures only one sync run executes at a time
- Remote invalidation:
  - Supabase Broadcast / Realtime hints for foreground responsiveness through opaque per-device channels
  - FCM data messages for background/closed-app wake-up
- Lifecycle integration: `SyncLifecycleManager` starts fast freshness sync when appropriate and suspends it cleanly on background
- Status reporting: idle, syncing, success, error, offline, authRequired states surfaced through `SyncProvider`
- Manual full-sync UI: top-app-chrome sync action for forcing a broader refresh without navigating to Settings

## Data Model
- Change capture: `change_log` SQLite table — fields: `id`, `table_name`, `record_id`, `operation` (INSERT/UPDATE/DELETE), `changed_at`, `processed`, `retry_count`, `error_message`, `metadata`
- Change detection: `ChangeTracker` reads `change_log` to build the pending work list for each sync run; entries are deleted from `change_log` only after confirmed remote acknowledgment
- Domain types: `SyncResult` (pushed, pulled, conflicts, errors, errorMessages), `SyncAdapterStatus` enum, `ConflictWinner` enum (in `ConflictResolver`)
- The sync feature does not sync its own tables to the cloud. `change_log` is local-only and consumed during each run.
- Planned remote freshness model:
  - dirty-scope invalidation hints identify changed company/project/table scopes
  - quick sync pulls only affected scopes where possible
  - full sync remains the fallback/manual recovery path

## Architecture

### Sync Modes
| Mode | Purpose | Expected Work |
|------|---------|---------------|
| `Quick sync` | Startup/foreground freshness | Push local `change_log`; avoid broad full project-wide `pushAndPull()` by default; only limited pull work if needed |
| `Full sync` | User-requested explicit refresh | Broad push + pull sweep across synced scopes |
| `Maintenance sync` | Deferred correctness/housekeeping | Integrity checks, orphan cleanup, company member pulls, `last_synced_at` update |

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

### Remote Invalidation
- `FcmHandler` receives FCM data messages that act as invalidation hints for background/closed-app catch-up
- Supabase-originated invalidation hints are the preferred foreground signal for “what changed remotely,” but they must flow through authenticated private per-device channels backed by `sync_hint_subscriptions`
- Invalidation signals should identify scope, not force a blind full sync
- Broad full-sync remains available as a fallback and user-invoked action

### Lifecycle
- `SyncLifecycleManager` listens to `AppLifecycleState`; should trigger quick freshness sync on launch/foreground when appropriate; cancels in-flight operations gracefully on `paused`/`detached`

## User Flow
Sync operates mostly in the background. When inspectors save data, the SQLite trigger writes to `change_log` automatically. If connectivity is available and no sync is already running, a quick sync should pick up pending changes without forcing a full broad refresh. Inspectors can trigger a manual full sync from the global top-app sync action or from `SyncDashboardScreen`, which shows last sync time, pending change count, per-adapter status, and deeper diagnostics. Conflicts detected during pull are surfaced on `ConflictViewerScreen` for inspector resolution.

## Offline Behavior
The `change_log` table is the offline mechanism. When offline, all mutations accumulate in `change_log` via triggers. When connectivity returns, `SyncOrchestrator` should process pending changes first, then exchange only the remote changes needed for freshness. Failed adapter runs retain their error state and retry on the next cycle. The system never blocks user interaction waiting for sync.

## Screens
| Screen | Purpose |
|--------|---------|
| `SyncDashboardScreen` | Shows sync status, last sync time, pending change count, per-adapter status strip, manual trigger button |
| `ConflictViewerScreen` | Lists unresolved conflicts with field-level diff; inspector accepts local or remote version per record |

## Shared App Chrome
- Global sync action in the main app bar / shell
- Idle state: sync icon
- Active state: spinner / progress state
- Manual action triggers `Full sync`

## Provider
`SyncProvider` — exposes `SyncStatus`, last sync timestamp, pending change count, conflict count, and sync-mode-aware actions to the widget tree via Provider

## Dependencies
- Features: projects, entries, photos, auth (Supabase session required for push/pull)
- Packages: `supabase_flutter`, `sqflite`, `connectivity_plus`, `firebase_messaging`
- Services: Supabase Broadcast / Realtime for foreground invalidation through private per-device channels, FCM for background invalidation

## Security Direction

- Foreground hint channels must be opaque and server-issued, not derived from `company_id`
- Broadcast hints remain advisory metadata only
- Real data access continues to flow through normal auth + RLS-protected sync reads

## Related Specs

- `.claude/specs/2026-04-03-sync-strategy-codex-spec.md`
- `.claude/specs/2026-04-04-private-sync-hint-channels-codex-spec.md`

## Owner Agent
backend-supabase-agent (remote schema, RLS, FCM), backend-data-layer-agent (change_log triggers, adapters, integrity checks)

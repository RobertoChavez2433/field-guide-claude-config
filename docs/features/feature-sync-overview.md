---
feature: sync
type: overview
scope: Cloud Synchronization & Multi-Backend Support
updated: 2026-04-04
---

# Sync Feature Overview

## Purpose

The Sync feature enables offline-first data synchronization between the local SQLite database and cloud backends. It abstracts backend selection (currently Supabase for Local Agency mode, future AASHTOWare for MDOT mode) through an adapter pattern, allowing inspectors to work offline and automatically push/pull changes when connected.

## Target Direction

- Keep incremental local push via `change_log`
- Stop using broad full project-wide sync as the default foreground behavior
- Split sync behavior into `Quick sync`, `Full sync`, and `Maintenance sync`
- Use Supabase-originated foreground invalidation hints over opaque private channels plus FCM background invalidation hints
- Expose a global manual full-sync action in the shared app chrome

## Key Responsibilities

- **Multi-Backend Routing**: Route sync operations to the correct backend adapter based on project mode
- **Push Operations**: Sync local pending changes (projects, entries, photos) to cloud backend
- **Pull Operations**: Fetch remote changes and merge into local SQLite database
- **Sync Modes**: Run low-latency quick sync for startup/foreground, broader full sync for explicit user refresh, and deferred maintenance sync for integrity/profile work
- **Conflict Resolution**: Handle data conflicts when same entity modified offline and remotely
- **Sync Status Tracking**: Maintain pending/synced/error state for all syncable entities
- **Connectivity Monitoring**: Detect online/offline transitions and trigger deferred syncs
- **Rate Limiting**: Debounce rapid sync requests to prevent excessive network traffic
- **Remote Invalidation**: Use private Supabase hint channels while the app is open and FCM data messages while it is backgrounded or closed

## Key Files

### Engine Components

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/sync/engine/sync_engine.dart` | `SyncEngine` | Core sync engine — orchestrates push/pull cycle |
| `lib/features/sync/engine/change_tracker.dart` | `ChangeTracker` | Tracks local changes pending sync |
| `lib/features/sync/engine/conflict_resolver.dart` | `ConflictResolver` | Conflict resolution logic (last-write-wins + merging) |
| `lib/features/sync/engine/integrity_checker.dart` | `IntegrityChecker` | Validates referential integrity after sync |
| `lib/features/sync/engine/sync_mutex.dart` | `SyncMutex` | Prevents concurrent sync runs |
| `lib/features/sync/engine/sync_registry.dart` | `SyncRegistry` | Registers and routes to table adapters |
| `lib/features/sync/engine/orphan_scanner.dart` | `OrphanScanner` | Detects orphaned storage objects |
| `lib/features/sync/engine/storage_cleanup.dart` | `StorageCleanup` | Cleans up orphaned Supabase storage files |
| `lib/features/sync/engine/sync_control_service.dart` | `SyncControlService` | Pause/resume and circuit-breaker controls |

### Application Layer

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/sync/application/sync_orchestrator.dart` | `SyncOrchestrator` | Multi-backend router (ProjectMode → adapter); top-level sync entry point |
| `lib/features/sync/application/sync_lifecycle_manager.dart` | `SyncLifecycleManager` | App lifecycle observer; triggers sync on foreground |
| `lib/features/sync/application/background_sync_handler.dart` | `BackgroundSyncHandler` | Handles workmanager background sync tasks |
| `lib/features/sync/application/fcm_handler.dart` | `FcmHandler` | Handles FCM push notifications to trigger sync |

### Adapters (22 concrete, 1 base)

| File Path | Purpose |
|-----------|---------|
| `lib/features/sync/adapters/table_adapter.dart` | Base `TableAdapter` class for all concrete adapters |
| `lib/features/sync/adapters/project_adapter.dart` | Projects |
| `lib/features/sync/adapters/daily_entry_adapter.dart` | Daily entries |
| `lib/features/sync/adapters/photo_adapter.dart` | Photos (with Supabase Storage) |
| `lib/features/sync/adapters/contractor_adapter.dart` | Contractors |
| `lib/features/sync/adapters/location_adapter.dart` | Locations |
| `lib/features/sync/adapters/bid_item_adapter.dart` | Bid items |
| `lib/features/sync/adapters/calculation_history_adapter.dart` | Calculator history |
| `lib/features/sync/adapters/consent_record_adapter.dart` | Consent records |
| `lib/features/sync/adapters/document_adapter.dart` | Documents |
| `lib/features/sync/adapters/entry_contractors_adapter.dart` | Entry↔contractor junction |
| `lib/features/sync/adapters/entry_equipment_adapter.dart` | Entry equipment |
| `lib/features/sync/adapters/entry_export_adapter.dart` | Entry exports |
| `lib/features/sync/adapters/entry_personnel_counts_adapter.dart` | Entry personnel counts |
| `lib/features/sync/adapters/entry_quantities_adapter.dart` | Entry quantities |
| `lib/features/sync/adapters/equipment_adapter.dart` | Equipment |
| `lib/features/sync/adapters/form_export_adapter.dart` | Form exports |
| `lib/features/sync/adapters/form_response_adapter.dart` | Form responses |
| `lib/features/sync/adapters/inspector_form_adapter.dart` | Inspector forms |
| `lib/features/sync/adapters/personnel_type_adapter.dart` | Personnel types |
| `lib/features/sync/adapters/project_assignment_adapter.dart` | Project assignments |
| `lib/features/sync/adapters/support_ticket_adapter.dart` | Support tickets |
| `lib/features/sync/adapters/todo_item_adapter.dart` | Todo items |

### Configuration & Domain

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/sync/config/sync_config.dart` | `SyncEngineConfig` | Sync tuning (intervals, retries, debounce) |
| `lib/features/sync/domain/sync_types.dart` | — | Value objects and enums (SyncStatus, SyncResult, etc.) |
| `lib/features/sync/data/adapters/mock_sync_adapter.dart` | — | Mock adapter for testing |

### Presentation

| File Path | Class | Purpose |
|-----------|-------|---------|
| `lib/features/sync/presentation/screens/sync_dashboard_screen.dart` | `SyncDashboardScreen` | Full sync status dashboard |
| `lib/features/sync/presentation/screens/conflict_viewer_screen.dart` | `ConflictViewerScreen` | Conflict review and resolution UI |
| `lib/features/sync/presentation/providers/sync_provider.dart` | `SyncProvider` | UI state provider for sync status and actions |
| `lib/features/sync/presentation/widgets/sync_status_icon.dart` | `SyncStatusIcon` | Icon widget showing current sync state |
| `lib/features/sync/presentation/widgets/deletion_notification_banner.dart` | `DeletionNotificationBanner` | Banner alerting user to server-side deletions |

## Data Sources

- **SQLite**: Local database with all syncable entities
- **Supabase**: Cloud backend for Local Agency mode (push/pull via REST API + Storage for photos)
- **AASHTOWare** (future): OpenAPI endpoint for MDOT mode
- **Connectivity Service**: Device connectivity status for online/offline detection
- **FCM**: Push notifications to wake sync on remote changes
- **Supabase Broadcast / Realtime**: Foreground invalidation hints for remote changes, but only over server-issued opaque per-device channels

## Integration Points

**Depends on:**
- `core/database` — SQLite tables for all entities
- `projects`, `entries`, `photos`, `contractors`, `locations`, `todos`, `forms`, `quantities`, `calculator`, `auth` — All syncable feature entities
- `auth` — Authentication status (required before syncing to Supabase)

**Required by:**
- `settings` — Manual sync trigger UI and sync configuration
- `projects` — Sync status display per project
- All data features — Offline/online behavior configuration

## Offline Behavior

Sync is **fully offline-capable**. All local operations queue changes to SQLite with `syncStatus: pending`. When connectivity is restored, sync operations automatically push queued changes and pull remote updates. Users never lose work; offline changes persist until sync completes.

### Read Path (Offline)
- All reads from local SQLite (instant)
- No network dependency
- No "stale data" warnings (data only stale relative to last sync)

### Write Path (Offline)
- All writes to SQLite with `syncStatus: pending`
- Changes queued automatically
- Background sync triggered on reconnect (or user manually via Settings)

### Sync on Reconnect / Foreground
- Connectivity service detects online transition
- Quick sync should handle common freshness work
- FCM push can wake sync remotely for background/closed-app changes
- Supabase-originated hints now drive targeted foreground catch-up through `sync_hint_subscriptions` + `register_sync_hint_channel()` private opaque channels, not predictable tenant channels
- User can also manually trigger a broader full sync from the main app chrome or sync dashboard

## Edge Cases & Limitations

- **No Real-Time Collaboration**: If 2 inspectors edit same project offline, last-write-wins (simple conflict resolution)
- **Current Baseline**: Pull is still broader than ideal because the client lacks a true remote delta feed; this is the main target for improvement
- **Pending Cascade**: If entry has pending photo, entry itself marked pending (transitive pending)
- **No Bandwidth Limits**: Large photo syncs may consume significant bandwidth on metered connections
- **Auth Required**: Supabase adapter requires authentication; offline-only works for local inspection workflows
- **Debounce Window**: Rapid sync requests debounced (coalesced) to reduce server load
- **Circuit Breaker**: `SyncControlService` can pause sync after repeated failures; visible in `SyncDashboardScreen`

## Intent Foundation

The current foundation for the next sync phase is documented in:

- `.claude/specs/2026-04-03-sync-strategy-codex-spec.md`
- `.claude/specs/2026-04-04-private-sync-hint-channels-codex-spec.md`
- `.codex/plans/2026-04-03-startup-sync-performance-plan.md`

## Detailed Specifications

See `architecture-decisions/sync-constraints.md` for:
- Hard rules on conflict resolution strategy
- How pending vs. synced state transitions work
- Error handling and retry logic

See `rules/sync/sync-patterns.md` for:
- SyncAdapter interface documentation
- Multi-backend routing patterns
- Table adapter patterns
- Offline queue management

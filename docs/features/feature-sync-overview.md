---
feature: sync
type: overview
scope: Cloud Synchronization & Multi-Backend Support
updated: 2026-02-13
---

# Sync Feature Overview

## Purpose

The Sync feature enables offline-first data synchronization between the local SQLite database and cloud backends. It abstracts backend selection (currently Supabase for Local Agency mode, future AASHTOWare for MDOT mode) through an adapter pattern, allowing inspectors to work offline and automatically push/pull changes when connected.

## Key Responsibilities

- **Multi-Backend Routing**: Route sync operations to the correct backend adapter based on project mode
- **Push Operations**: Sync local pending changes (projects, entries, photos) to cloud backend
- **Pull Operations**: Fetch remote changes and merge into local SQLite database
- **Conflict Resolution**: Handle data conflicts when same entity modified offline and remotely
- **Sync Status Tracking**: Maintain pending/synced/error state for all syncable entities
- **Connectivity Monitoring**: Detect online/offline transitions and trigger deferred syncs
- **Rate Limiting**: Debounce rapid sync requests to prevent excessive network traffic

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/sync/domain/sync_adapter.dart` | SyncAdapter interface & value objects |
| `lib/features/sync/application/sync_orchestrator.dart` | Multi-backend router (ProjectMode → adapter) |
| `lib/features/sync/data/adapters/supabase_sync_adapter.dart` | Supabase implementation |
| `lib/features/sync/presentation/providers/sync_provider.dart` | UI provider for sync state/actions |
| `lib/services/sync_service.dart` | Legacy Supabase sync engine (wrapped by adapter) |
| `lib/core/database/database_service.dart` | SQLite schema and local persistence |

## Data Sources

- **SQLite**: Local database with projects, entries, photos, contractors, locations
- **Supabase**: Cloud backend for Local Agency mode (push/pull via REST API)
- **AASHTOWare** (future): OpenAPI endpoint for MDOT mode
- **Connectivity Service**: Device connectivity status for online/offline detection

## Integration Points

**Depends on:**
- `core/database` - SQLite tables for all entities
- `projects`, `entries`, `photos`, `contractors`, `locations` - Entities to sync
- `auth` - Authentication status (required before syncing to Supabase)

**Required by:**
- `settings` - Manual sync trigger UI
- `dashboard` - Sync status display and indicators
- All data features - Offline/online behavior configuration

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

### Sync on Reconnect
- Connectivity service detects online transition
- Auto-triggers `syncAll()` if enabled in app settings
- User can also manually trigger from Settings screen

## Edge Cases & Limitations

- **No Real-Time Collaboration**: If 2 inspectors edit same project offline, last-write-wins (simple conflict resolution)
- **No Selective Sync**: Sync operations are all-or-nothing per entity type (all entries or none)
- **Pending Cascade**: If entry has pending photo, entry itself marked pending (transitive pending)
- **No Bandwidth Limits**: Large photo syncs may consume significant bandwidth on metered connections
- **Auth Required**: Supabase adapter requires authentication; offline-only works for local inspection workflows
- **Debounce Window**: Rapid sync requests debounced (coalesced) to reduce server load

## Detailed Specifications

See `architecture-decisions/sync-constraints.md` for:
- Hard rules on conflict resolution strategy
- How pending vs. synced state transitions work
- Error handling and retry logic

See `rules/sync/sync-patterns.md` for:
- SyncAdapter interface documentation
- Multi-backend routing patterns
- Legacy SyncService wrapper usage
- Offline queue management

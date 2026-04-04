# Sync Engine Constraints

## Hard Rules (Violations = Reject Proposal)

- MUST use trigger-based `change_log` for change detection (no hash-based checksums, no per-row sync_status columns)
- MUST process adapters independently (per-adapter success/failure — no all-or-nothing sync)
- MUST use `TableAdapter` as the base class for all sync adapters (not `SyncAdapter`)
- MUST push parent tables before children (FK dependency ordering enforced by `SyncRegistry`)
- MUST acquire `SyncMutex` before any push/pull cycle (prevents concurrent sync runs)
- MUST NOT retry indefinitely (max retry count configured in `SyncEngineConfig`)
- MUST NOT trust client-provided `company_id` in sync payloads — server RLS validates `company_id` from JWT `app_metadata` via `get_my_company_id()`
- MUST keep `change_log` as the local source of truth for incremental push
- MUST NOT default startup/foreground auto-sync to a broad full project-wide `pushAndPull()` path
- MUST keep manual full sync available as an explicit fallback / recovery action
- MUST treat Supabase Broadcast / Realtime and FCM as invalidation-hint channels, not as sources of truth replacing normal sync writes
- MUST NOT use predictable tenant-wide Broadcast channels for foreground invalidation
- MUST use server-issued opaque private hint channels for foreground Broadcast delivery when Broadcast is enabled

## Soft Guidelines (Violations = Discuss)

- Use exponential backoff on sync retry (100ms base, configurable in `SyncEngineConfig`)
- Batch sync operations to reduce API calls (batch size configurable in `SyncEngineConfig`)
- Log all conflicts (timestamp, table, record_id, local vs. remote values)
- Performance target: < 5 seconds for 100-record sync cycle
- Run `IntegrityChecker` post-sync to validate FK consistency
- Run `OrphanScanner` to detect local records with no valid FK parent
- Prefer `Quick sync`, `Full sync`, and `Maintenance sync` as separate orchestration modes
- Prefer targeted remote invalidation over broad cursor sweeps when enough scope information is available
- Use Supabase-originated private-channel hints for foreground responsiveness and FCM data messages for background / closed-app wake-up
- Keep profile/member pull and other housekeeping work off the critical foreground freshness path whenever practical

## Core Components

| Component | File | Purpose |
|-----------|------|---------|
| `SyncEngine` | `engine/sync_engine.dart` | Core push/pull orchestration per adapter |
| `SyncRegistry` | `engine/sync_registry.dart` | Ordered list of all `TableAdapter` instances; FK dependency order |
| `SyncMutex` | `engine/sync_mutex.dart` | Prevents concurrent sync runs |
| `ChangeTracker` | `engine/change_tracker.dart` | Reads `change_log` table; groups pending changes by table |
| `ConflictResolver` | `engine/conflict_resolver.dart` | Last-writer-wins + manual resolution support |
| `IntegrityChecker` | `engine/integrity_checker.dart` | Post-sync FK consistency validation |
| `OrphanScanner` | `engine/orphan_scanner.dart` | Detects orphaned local records |
| `StorageCleanup` | `engine/storage_cleanup.dart` | Deletes local files after successful remote upload |
| `SyncControlService` | `engine/sync_control_service.dart` | Circuit-breaker state + health metrics for UI |
| `FcmHandler` | `application/fcm_handler.dart` | Processes FCM push notifications that signal remote changes |
| `RealtimeHintHandler` | `application/realtime_hint_handler.dart` | Processes foreground invalidation hints delivered over private opaque channels |
| `SyncOrchestrator` | `application/sync_orchestrator.dart` | Multi-backend router (Supabase now, AASHTOWare future) |
| `SyncLifecycleManager` | `application/sync_lifecycle_manager.dart` | Triggers sync on app foreground / reconnect |
| `BackgroundSyncHandler` | `application/background_sync_handler.dart` | Schedules and runs background sync tasks |
| `TableAdapter` | `adapters/table_adapter.dart` | Abstract base class for all 22 concrete adapters |

## Sync Mode Intent

| Mode | Required Intent |
|------|-----------------|
| `Quick sync` | Fast user-facing freshness path; must avoid broad full project-wide sync by default |
| `Full sync` | Explicit user-requested broad refresh and recovery path |
| `Maintenance sync` | Deferred integrity / cleanup / profile maintenance work |

## change_log Schema (Local-Only SQLite)

The `change_log` table is populated automatically by SQLite triggers on every INSERT, UPDATE, and DELETE to syncable tables. It is **local-only** — never synced to Supabase.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment row ID |
| `table_name` | TEXT | Name of the modified table |
| `record_id` | TEXT | UUID of the affected record |
| `operation` | TEXT | One of: `insert`, `update`, `delete` |
| `changed_at` | TEXT | ISO 8601 timestamp of the local change |
| `processed` | INTEGER | 0 = pending, 1 = successfully pushed |
| `retry_count` | INTEGER | Number of failed push attempts |
| `error_message` | TEXT | Last error message (nullable) |
| `metadata` | TEXT | JSON metadata for special cases (nullable) |

**DEPRECATED:** `sync_status` columns on individual tables are deprecated. All change detection is driven by `change_log` entries.

## Adapter Ordering (22 Adapters)

Adapters are registered in `SyncRegistry` in FK dependency order (parents before children). The `SyncEngine` processes them in this order for both push and pull.

| Order | Adapter | Table | Notes |
|-------|---------|-------|-------|
| 1 | `ProjectAdapter` | projects | Root table, no FK deps |
| 2 | `ProjectAssignmentAdapter` | project_assignments | FK: projects |
| 3 | `LocationAdapter` | locations | FK: projects |
| 4 | `ContractorAdapter` | contractors | FK: projects |
| 5 | `EquipmentAdapter` | equipment | FK: projects |
| 6 | `BidItemAdapter` | bid_items | FK: projects |
| 7 | `PersonnelTypeAdapter` | personnel_types | FK: projects |
| 8 | `DailyEntryAdapter` | daily_entries | FK: projects, locations |
| 9 | `PhotoAdapter` | photos | FK: daily_entries; file adapter |
| 10 | `EntryEquipmentAdapter` | entry_equipment | FK: daily_entries, equipment |
| 11 | `EntryQuantitiesAdapter` | entry_quantities | FK: daily_entries, bid_items |
| 12 | `EntryContractorsAdapter` | entry_contractors | FK: daily_entries, contractors |
| 13 | `EntryPersonnelCountsAdapter` | entry_personnel_counts | FK: daily_entries, personnel_types |
| 14 | `InspectorFormAdapter` | inspector_forms | FK: projects; includes null-project builtins |
| 15 | `FormResponseAdapter` | form_responses | FK: inspector_forms |
| 16 | `FormExportAdapter` | form_exports | FK: form_responses; file adapter |
| 17 | `EntryExportAdapter` | entry_exports | FK: daily_entries; file adapter |
| 18 | `DocumentAdapter` | documents | FK: projects; file adapter |
| 19 | `TodoItemAdapter` | todo_items | FK: projects |
| 20 | `CalculationHistoryAdapter` | calculation_history | FK: projects |
| 21 | `SupportTicketAdapter` | support_tickets | Push-only, no FK deps |
| 22 | `ConsentRecordAdapter` | user_consent_records | Push-only, insert-only (legal audit trail) |

## Security: RLS and Company Scoping

- All synced tables use Supabase Row Level Security (RLS) policies
- Company scoping is enforced server-side via `get_my_company_id()` which reads `company_id` from the JWT `app_metadata`
- **The client MUST NOT include `company_id` in sync payloads** — the server determines it from the authenticated session
- RLS denials are tracked in `SyncEngineResult.rlsDenials` and surfaced in the sync dashboard UI
- `ScopeType` enum controls how each table's pull query filters by tenant: `direct` (company_id on the table), `viaProject` (joined through projects), `viaEntry` (joined through daily_entries), `viaContractor`, etc.

## Security: Foreground Invalidation Channels

- Foreground Broadcast delivery must use opaque server-issued channels, not `sync_hints:{company_id}`
- Channel assignment must come from an authenticated server-side registration flow
- Active recipient resolution must come from server-side subscription state (`sync_hint_subscriptions` / `get_active_sync_hint_channels()`), not client-derived channel naming
- Broadcast hints remain metadata-only invalidation signals
- Record contents still require normal auth + RLS-protected sync pull

## Performance Targets

- Single record sync: < 500ms
- Batch sync (100 records): < 5 seconds
- Conflict detection: < 100ms per record
- Retry backoff: exponential with configurable base (max attempts from `SyncEngineConfig`)

## Testing Requirements

- >= 85% test coverage for engine layer
- Unit tests: change_log processing, conflict resolution, adapter ordering, integrity checks
- Integration tests: offline queue -> sync -> error recovery
- Conflict scenario: simultaneous edits on two devices
- Batch scenario: 100+ records with mixed per-adapter success/failure
- **Always use the app UI to create/modify test data** — never raw SQL or REST writes (bypasses triggers)

## References

- See `sync-patterns.md` for full layer diagram, data flow, and file organization
- See `lib/features/sync/config/sync_config.dart` for all configurable thresholds
- See `lib/features/sync/engine/` for engine component implementations
- See `lib/features/sync/adapters/` for all 22 concrete adapters
- See `.claude/specs/2026-04-04-private-sync-hint-channels-codex-spec.md` for the private foreground hint channel direction

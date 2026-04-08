---
paths:
  - "lib/features/sync/**/*.dart"
---

# Sync Architecture — Constraints & Invariants

5-layer sync system: Presentation > Application > Engine > Adapters > Domain.
Entry point is `SyncCoordinator`. The engine owns routing and lifecycle, while
Supabase row I/O stays in `SupabaseSync`, SQLite row I/O stays in
`LocalSyncStore`, and push-side foreground invalidation now stays in
`SyncHintRemoteEmitter`.

## Hard Constraints

- **change_log is trigger-only** — 20 tables have SQLite triggers gated by `sync_control.pulling='0'`. Never manually INSERT into change_log.
- **Trigger suppression MUST use try/finally** — set `pulling='1'` before pull, reset to `'0'` in finally. Owned by `LocalSyncStore` via `TriggerStateStore`.
- **SyncErrorClassifier is the single source of truth** for error classification. No Postgres code matching anywhere else.
- **SyncStatus is the single SOT** for transport state (isUploading, isDownloading, lastSyncedAt, errors, isOnline).
- **SyncDiagnosticsSnapshot** is point-in-time, fetched by `SyncQueryService` — it does NOT stream.
- **SyncRegistry order is load-bearing** — defines FK dependency order for push. Parents before children.
- **is_builtin=1 rows are server-seeded** — triggers skip them, push skips them, cascade-delete skips them.
- **No sync_status column** — only change_log is used for tracking pending changes.
- **SyncOrchestrator no longer exists** — use `SyncCoordinator`.
- **Push-side sync_hint emission is explicit** — production `PushHandler` must be
  wired with `syncHintEmitter:` and emit `emit_sync_hint(...)` through
  `SyncHintRemoteEmitter`.
- **Client sync_hint subscriptions are single-owner** — only
  `RealtimeHintHandler` may call `register_sync_hint_channel`,
  `deactivate_sync_hint_channel`, or `.onBroadcast(event: 'sync_hint', ...)`.
- **Active opaque hint topics come from `sync_hint_subscriptions`** — never
  derive channel names on the client and never depend on `user_profiles` joins
  for active recipient lookup.
- **No raw client broadcast HTTP** — client Dart code must not call
  `/realtime/v1/api/broadcast`.

## Error Classification (Security-Critical)

| SyncErrorKind | Postgres/Network Pattern | Retryable |
|---------------|-------------------------|-----------|
| `rlsDenial` | 42501 | No (permanent) |
| `fkViolation` | 23503 | No (permanent) |
| `uniqueViolation` | 23505 | Yes (up to 2, TOCTOU race) |
| `rateLimited` | 429, 503 | Yes (with backoff) |
| `authExpired` | 401, PGRST301, JWT | Yes (after token refresh) |
| `networkError` | SocketException, Timeout, DNS | Yes (with backoff) |
| `transient` | Other retryable | Yes |
| `permanent` | Other non-retryable | No |

RLS denials (42501) are permanent and MUST NOT be retried — they indicate a security boundary violation.

## Enforced Invariants (Lint Rules)

- **S1**: `ConflictAlgorithm.ignore` MUST have rowId==0 fallback (check return value, UPDATE on 0)
- **S2**: change_log cleanup MUST be conditional on RPC success (never unconditional DELETE)
- **S3**: sync_control flag MUST be inside transaction (set pulling='1' inside try/finally)
- **S4**: No sync_status column (deprecated pattern, only change_log)
- **S5**: `toMap()` MUST include project_id for synced child models
- **S8**: `_lastSyncTime` only updated in success path
- **S12**: production `PushHandler` construction MUST pass `syncHintEmitter:`
- **S13**: sync-hint RPC ownership is restricted to approved owners
- **S14**: sync-hint broadcast subscription stays inside `RealtimeHintHandler`
- **S15**: client Dart must not use raw `/realtime/v1/api/broadcast`

## Key Flows (Summary)

- **Push**: Local write -> SQLite trigger -> change_log -> ChangeTracker -> PushHandler (FK-ordered) -> SupabaseSync -> SyncHintRemoteEmitter
- **Pull**: SyncEngine -> PullHandler (FK-ordered) -> suppress triggers -> SupabaseSync paginated SELECT -> ConflictResolver -> LocalSyncStore -> restore triggers
- **Foreground hint**: RealtimeHintHandler -> mark dirty scope -> throttled quick sync through SyncCoordinator
- **Request**: Trigger source -> SyncTriggerPolicy -> SyncCoordinator -> ConnectivityProbe -> SyncEngine.run(mode) -> PostSyncHooks

## Gotchas

- Adapters are pure config+conversion — handlers do all I/O
- `pulling` flag reset to `'0'` on every app startup in `DatabaseService.onOpen` to recover from crash-during-pull
- `inspector_forms` triggers have additional `AND NEW.is_builtin != 1` guard
- Never use raw SQL or direct change_log inserts for test data — use app UI (triggers won't fire otherwise)
- SyncProvider no longer exposes `get orchestrator` — use `SyncQueryService` for dashboard data
- Foreground invalidation is not “whatever Supabase broadcast happens to do.”
  The owned client contract is `SyncHintRemoteEmitter` + `RealtimeHintHandler`.
- Server trigger fanout still exists, but it is not the only proof path anymore.
- Private channel recipient lookup should use `sync_hint_subscriptions` directly.

> For detailed diagrams, class inventories, and procedures, see `.claude/skills/implement/references/sync-patterns-guide.md`

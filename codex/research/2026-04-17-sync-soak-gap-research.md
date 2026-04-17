# Sync Soak Gap Research

Date: 2026-04-17
Branch: `gocr-integration`
Purpose: Preserve the research and code audit behind the decision to split the
current soak into a backend/RLS soak and a separate enterprise device-sync soak.

## Bottom Line

The clean `12,368/12,368` result is believable because that run is a direct
backend/RLS concurrency test. It is not proof that the app sync engine works on
phones or tablets.

The live device failures are happening in a different system boundary:

- local SQLite change capture,
- `change_log` retry and blocked-row behavior,
- `sync_lock` and app sync coordination,
- file/storage byte transfer,
- app auth/session rebinding,
- realtime dirty-scope behavior,
- UI-triggered sync,
- multi-device state convergence.

The current headless soak does not stress those boundaries, so it can pass while
the S21 still reports blocked/unprocessed local rows.

## External Research Findings

### Load Tests Need Real Concurrent Actors And Failure Criteria

Microsoft's Azure Load Testing concepts define virtual users as independent test
case runners used to simulate concurrent connections. The same page also calls
out ramp-up, response time, throughput, test engine instances, client metrics,
server metrics, and explicit fail criteria.

Reference:
https://learn.microsoft.com/en-us/azure/app-testing/load-testing/concept-load-testing-concepts

Implication for Field Guide:

- A count of successful actions is not enough.
- We need ramp-up, parallel device actors, explicit failure criteria, and both
  device-side and backend-side metrics.
- A direct Supabase client action is a valid server test, but it is not a real
  app-device sync actor.

### Android Release Confidence Requires Multiple Test Layers

Android's testing strategy documentation recommends layered tests and notes that
not everything can be covered by unit tests. It also treats UI, instrumented,
performance, and release-candidate tests as different layers with different
feedback value.

Reference:
https://developer.android.com/training/testing/fundamentals/strategies

Implication for Field Guide:

- We should keep small unit and harness tests, but sync signoff needs real
  device/app tests.
- The enterprise soak should be a release-candidate style gate, not a unit or
  backend-only test.
- Screenshots, navigation, and UI sync entry points belong in acceptance
  evidence because testers use the UI, not internal driver endpoints.

### SQLite WAL Still Has Device-Local Failure Modes

SQLite WAL allows more concurrent read/write behavior than rollback journals,
but SQLite still documents cases where WAL queries can return `SQLITE_BUSY`.
The WAL file and shared-memory behavior are local process/device concerns.

Reference:
https://sqlite.org/wal.html

Implication for Field Guide:

- A backend-only soak does not stress local database contention.
- The device soak must observe local queue growth, blocked rows, stale locks,
  app restart recovery, and WAL/checkpoint pressure.
- Multi-isolate or foreground/background sync contention must be tested on real
  devices, not inferred from direct Supabase CRUD.

### Supabase RLS Is Per-Query Authorization

Supabase RLS policies are attached to tables and run whenever the table is
accessed. Supabase also recommends enabling RLS for exposed schemas.

Reference:
https://supabase.com/docs/guides/database/postgres/row-level-security

Implication for Field Guide:

- The current backend/RLS soak is useful because it proves policy behavior under
  direct concurrent API access.
- It does not prove that the app's local scope cache, local project selection,
  UI state, and assignment revocation behave correctly after sync.
- Role testing must include both backend policy checks and app-visible state.

### Storage RLS Is Separate From Row Metadata

Supabase Storage access control uses policies on `storage.objects`; uploads
require the relevant storage permissions. Overwrite/upsert behavior requires
additional permissions.

Reference:
https://supabase.com/docs/guides/storage/security/access-control

Implication for Field Guide:

- Updating `photos.notes` is not a photo upload soak.
- The enterprise soak must upload actual bytes, verify storage object access,
  verify remote-path bookmarking, then verify download/preview on another
  device.
- File-backed tables need object proof, not only row proof.

### Supabase Realtime Has Connection And Throughput Limits

Supabase Realtime documents per-plan limits for connections, messages, channel
joins, channels per connection, and payload sizes. Limit errors surface in logs
and client WebSocket messages.

Reference:
https://supabase.com/docs/guides/realtime/limits

Implication for Field Guide:

- Realtime hints and dirty-scope quick sync must be part of soak evidence.
- The soak should capture realtime logs/client diagnostics when remote actors
  mutate data during active device sessions.
- A backend-only action loop does not prove channel rebinding, throttling, or
  quick-sync follow-up behavior.

## Codebase Audit Findings

### Current Headless Soak Is Backend/RLS Only

The host soak calls `SoakDriver.forLocalSupabase`:

- `test/harness/soak_ci_10min_test.dart`
- `test/harness/soak_nightly_15min_test.dart`

That path signs in many `SupabaseClient` instances and mutates remote tables
directly:

- `integration_test/sync/soak/soak_driver.dart`
  - `LocalSupabaseSoakActionExecutor.initialize`
  - direct `daily_entries` updates
  - direct `photos` metadata updates
  - assignment RPC calls

What it proves:

- seeded users can sign in,
- RLS blocks/permits expected remote access,
- assignment RPCs behave under concurrent requests,
- direct remote updates round-trip,
- direct project scope reads do not leak unassigned projects.

What it does not prove:

- local SQLite triggers fire,
- local `change_log` drains,
- blocked rows recover,
- sync locks do not stick,
- real app UI sync succeeds,
- storage bytes upload/download,
- local app auth state is clean after switching users,
- two devices converge.

### Real App Sync Depends On Local Change Log

The app's local queue is trigger-populated SQLite `change_log`:

- `lib/core/database/schema/sync_engine_tables.dart`
  - `createChangeLogTable`
  - generated table triggers insert into `change_log`

The production push path reads unprocessed local changes:

- `lib/features/sync/engine/push_handler.dart`
  - `PushHandler.push`
  - `ChangeTracker.getUnprocessedChanges`

The current backend soak bypasses this by mutating Supabase directly. No local
trigger fires and no local retry/blocked-row transition happens.

### Real App Sync Depends On Sync Coordination And Locking

The real engine route is:

- UI `SyncProvider.fullSync`
- `SyncCoordinator.syncLocalAgencyProjects`
- `SyncEngine.pushAndPull`
- `SyncMutex.tryAcquire`
- push, maintenance, pull, housekeeping, dirty-scope cleanup

Key files:

- `lib/features/sync/presentation/providers/sync_provider.dart`
- `lib/features/sync/application/sync_coordinator.dart`
- `lib/features/sync/engine/sync_engine.dart`
- `lib/features/sync/engine/sync_mutex.dart`

The backend soak bypasses this route. The optional driver-app soak triggers the
UI sync button, but it is currently single-driver and not part of CI/staging
evidence.

### File Sync Is Not Being Stressed

The soak action named `photoUpload` changes photo row metadata. It does not
create local files, upload bytes, strip EXIF, verify storage paths, download
objects, or test storage cleanup.

The real file path is:

- `lib/features/sync/engine/file_sync_three_phase_workflow.dart`
  - read local file bytes,
  - optional EXIF GPS stripping,
  - storage path validation,
  - `SupabaseSync.uploadFile`,
  - metadata upsert,
  - local remote-path bookmark,
  - stale remote-path cleanup.

The device soak must use actual file-backed rows.

### Device Evidence Already Contradicts Backend Confidence

The S21 UI-triggered measurement failed after the backend/RLS soak passed. It
observed the sync UI but still ended with blocked/unprocessed local queue rows.

That is the correct interpretation:

- backend/RLS path: passed,
- device local queue path: not proven and currently failing.

The plan must treat those as separate gates.

## Missing Stressors

- Multi-device live actors: S21 and S10 simultaneously, separate driver ports.
- Multi-user app actors: admin, engineer, office technician, inspector.
- Same-device account switching and session rebinding.
- Remote actors mutating assigned and unassigned projects while devices are
  open and syncing.
- Local app writes that generate `change_log`, not raw remote updates.
- Actual file/photo byte upload and download.
- Storage bucket RLS and object access per role.
- `storage_cleanup_queue` and stale object cleanup.
- Large first-sync hydration and project download/import graph proof.
- Form responses, signatures, documents, entry exports, pay-app exports,
  support tickets, consent records, and other file-backed/export tables.
- Offline/online transition during queued changes.
- Timeout/socket failure during push and pull.
- Expired/refreshing auth session during sync.
- Supabase transient/rate-limit behavior.
- App background/foreground during sync.
- App process restart during sync.
- SQLite busy/stale lock recovery.
- Realtime hint flood, dirty-scope overflow, throttled quick sync, and queued
  follow-up quick sync.
- Screen-level evidence: screenshots, navigation state, visible role leakage,
  stale metadata flashes, and sync dashboard state.

## Recommended Naming

Use two explicit layers:

- `backend_rls_soak`
  - Direct Supabase clients.
  - Docker/staging backend.
  - RLS, RPC, direct CRUD, policy leakage, server latency.
  - No claim about device sync.

- `device_sync_soak`
  - Real app/device actors.
  - SQLite `change_log`, `sync_lock`, UI-triggered sync, local storage, auth
    session, realtime hints, screenshots, logs.
  - Required for S21/S10 signoff.

## Acceptance Standard

The sync system is not ready for release confidence until:

- backend/RLS soak is green,
- device sync soak is green on S21 and S10,
- no device has pending or blocked local rows after the run,
- every file-backed row has storage object proof,
- assignment revocation does not flash unauthorized project data,
- same-device account switching leaves no stale state,
- realtime hints produce correct dirty scopes and eventual convergence,
- artifacts include screenshots, logs, sync-status samples, change-log samples,
  backend state, and failure-injection results.


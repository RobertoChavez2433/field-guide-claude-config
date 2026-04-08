# Startup Sync Performance Fix Plan

Date: 2026-04-03
Author: Codex
Status: Proposed

## Problem Summary

Startup auto-sync is inconsistent and too slow when it does run.

Verified findings from live tracing on the S21 and code inspection:

- Cold launch does not reliably trigger a sync at app startup.
- Existing automatic sync behavior depends on incidental triggers:
  - app resume staleness logic
  - auth-change login path
  - `ProjectListScreen` first-frame refresh
- Manual foreground sync completed in about `5.9s` for only `20` pending records, which is too slow for the expected “fresh on open” experience.
- The current sync path includes blocking post-sync work that is not required for the user-facing startup freshness contract:
  - reachability probe
  - full `pushAndPull()`
  - company member profile pull
  - `last_synced_at` RPC

## Root Cause

There are two upstream issues:

1. No dedicated startup sync coordinator

- The app initializes sync infrastructure, but it does not perform a guaranteed one-shot startup sync once auth and company context are ready.
- Current behavior is spread across lifecycle resume logic and screen-specific refreshes.

2. Foreground sync path does too much blocking work

- `syncLocalAgencyProjects()` is used for both user-facing foreground freshness and heavier full-sync maintenance work.
- The user-visible path pays for work that can be deferred or decoupled.

## Goals

- Ensure startup sync reliably runs once on cold launch after auth context is ready.
- Reduce perceived startup sync duration to roughly `1-2s` in the common case.
- Keep data-correctness guarantees for real sync work.
- Avoid duplicate syncs from startup, resume, and project-screen refresh paths.
- Add a manual sync action in the main app chrome so the user can force a full sync without opening Settings.
- Stop running a full project-wide `pushAndPull()` by default on startup/foreground sync.

## Non-Goals

- Full sync engine redesign.
- Replacing the change-log architecture.
- Broad sync schema or adapter rewrites unless profiling proves they are required.

## Fix Strategy

### 1. Add a dedicated one-shot startup sync trigger

Create a startup sync coordinator that:

- runs once per app launch
- waits for valid auth context and `companyId`
- triggers after app initialization completes
- does not depend on a route-specific screen
- guards against overlap with lifecycle/manual sync paths

Recommended location:

- `lib/features/sync/application/sync_initializer.dart`
- optionally a small dedicated helper if the initializer grows too much

Expected behavior:

- If user is authenticated and sync context is ready, app performs a startup freshness sync automatically.
- If user is not ready yet, startup sync waits briefly for readiness instead of relying on resume or project-screen refresh.

### 2. Introduce explicit sync modes

Replace the current “one sync path for everything” behavior with three modes:

- `Quick sync`
  - default for startup and foreground freshness
  - pushes local `change_log`
  - does not run a broad project-wide `pushAndPull()` by default
  - only performs narrowly-scoped pull work if needed

- `Full sync`
  - manual sync button path
  - can run the broader push + pull sweep
  - acceptable to be slower because the user explicitly requested it

- `Maintenance sync`
  - background/deferred path
  - integrity checks
  - orphan cleanup
  - company member pull
  - `last_synced_at` update

### 3. Split foreground startup sync from heavier maintenance tasks

Do not make the startup path wait on all post-sync bookkeeping.

Separate the current sync flow into:

- a user-facing foreground sync path for startup/manual freshness
- deferred maintenance tasks after success

Deferred items should include:

- `pullCompanyMembers(companyId)`
- `updateLastSyncedAt()`

These should either:

- run unawaited after foreground sync success, or
- move to a lower-priority background maintenance path

Target outcome:

- startup sync returns as soon as core project/entry data is up to date
- profile-maintenance work no longer blocks the UI freshness contract

### 4. Reduce startup-context waiting inside sync creation

Current engine creation polls for auth context for up to 15 seconds.

Instead:

- startup trigger should fire only after auth context is known ready
- `_createEngine()` should remain defensive, but it should not be the primary readiness gate for startup

This shifts waiting upstream and removes the “silent stall before sync starts” behavior.

### 5. Prevent duplicate startup and screen refresh syncs

Current project list refresh also triggers sync.

Need a shared guard such as:

- one in-flight sync flag for foreground sync calls
- one “startup sync completed this launch” flag

This prevents:

- startup sync + resume sync overlap
- startup sync + project list first-frame refresh overlap
- redundant foreground syncs immediately after app open

### 6. Re-evaluate freshness threshold behavior

The current lifecycle stale threshold is `24h`, which is too coarse for the user expectation of “sync on open.”

Recommended behavior:

- startup sync is its own explicit path
- resume logic can keep a broader stale threshold
- startup should not be gated by the same `24h` rule

That preserves battery/network tradeoffs on normal app resumes while making cold launch deterministic.

### 7. Add a top-bar manual sync action

Add a global manual sync action in the shared app chrome.

Recommended location:

- `lib/core/router/scaffold_with_nav_bar.dart`

Behavior:

- visible from the main shell screens
- sync icon when idle
- spinner while syncing
- optional pending badge if useful
- manual action uses `Full sync`, not `Quick sync`

This gives the user a deterministic “sync now” control without navigating to Settings.

### 8. Plan smarter remote invalidation

The system already has a local change log for incremental push, but remote freshness still relies on broad per-table cursor polling.

Need a smarter remote invalidation strategy so the app does not have to sweep all synced scopes on every user-facing sync.

Locked direction:

- Supabase-originated foreground invalidation hints
  - via Broadcast / Realtime while the app is open
- FCM data-message invalidation hints
  - for background / closed-app wake-up

Recommendation for implementation planning:

- near-term: add `Quick sync` vs `Full sync`
- mid-term: use Supabase foreground hints + FCM background hints to target only changed scopes
- keep broad full sync as fallback and manual path

## Implementation Phases

### Phase 1. Startup Trigger

Files:

- `lib/features/sync/application/sync_initializer.dart`
- `lib/features/sync/application/sync_orchestrator.dart`

Changes:

- add a one-shot startup sync trigger after orchestrator initialization and readiness wiring
- wait for valid auth context before firing
- add overlap guards

Acceptance:

- cold launch with authenticated user triggers sync without entering Projects screen
- startup sync runs once per launch

### Phase 2. Sync Mode Split

Files:

- `lib/features/sync/application/sync_orchestrator.dart`
- `lib/features/sync/engine/sync_engine.dart`

Changes:

- add `Quick sync`, `Full sync`, and `Maintenance sync` orchestration paths
- ensure startup path does not default to full project-wide `pushAndPull()`
- keep `Full sync` available for explicit user action

Acceptance:

- startup/foreground sync no longer performs broad full-scope pull by default
- manual sync can still perform full data refresh

### Phase 3. Foreground Path Slimming

Files:

- `lib/features/sync/application/sync_orchestrator.dart`
- `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart`

Changes:

- split blocking foreground sync completion from deferred profile-maintenance work
- keep core push/pull awaited
- run member-profile pull and `last_synced_at` update outside the critical path

Acceptance:

- sync success still records properly
- startup/manual sync latency decreases materially

### Phase 4. Manual Sync UI

Files:

- `lib/core/router/scaffold_with_nav_bar.dart`
- `lib/features/sync/presentation/providers/sync_provider.dart`

Changes:

- add top-bar manual sync action
- show progress state cleanly
- wire button to `Full sync`

Acceptance:

- user can force a sync from the main shell without opening Settings
- button state is obvious while sync is active

### Phase 5. Trigger Cleanup

Files:

- `lib/features/projects/presentation/providers/project_provider.dart`
- `lib/features/projects/presentation/screens/project_list_screen.dart`
- `lib/features/sync/application/sync_lifecycle_manager.dart`

Changes:

- keep route-level refresh behavior for explicit user refreshes
- stop relying on project-list first-frame refresh as pseudo-startup sync
- verify lifecycle resume remains useful but not the only freshness path

Acceptance:

- no redundant duplicate syncs on launch
- project list still supports explicit refresh behavior

### Phase 6. Instrumentation

Files:

- `lib/features/sync/application/sync_orchestrator.dart`
- `lib/features/sync/engine/sync_engine.dart`

Changes:

- add explicit timing logs for:
  - readiness wait
  - reachability check
  - push/pull
  - deferred maintenance tasks
- keep logs narrow and actionable

Acceptance:

- one foreground sync log line shows phase timings clearly
- future regressions can be attributed quickly

## Validation Plan

### Functional

- Cold launch authenticated app on S21.
- Confirm sync starts without navigating to Projects.
- Confirm startup sync runs once.
- Confirm manual sync still works.
- Confirm top-bar sync action is visible and usable from main shell screens.
- Confirm project refresh still works.

### Performance

Measure:

- app launch to sync start
- sync start to user-visible completion
- total startup sync duration

Success target:

- common-case startup freshness sync noticeably below current `5.9s`
- target band `1-2s`, acceptable band under `3s`

### Regression Checks

- no duplicate syncs after cold launch
- no sync trigger loop on resume
- no auth-context race causing repeated no-op sync attempts
- pending count and last sync timestamp still update correctly
- manual full sync still performs a broad refresh when requested

### Driver / Debug Verification

Use:

- `/driver/sync-status`
- `/driver/sync`

Confirm:

- startup path changes status automatically
- post-sync state settles to `pendingCount: 0`
- manual sync path remains available as a fallback verification mechanism

## Risks

- Moving post-sync work off the critical path can create hidden failures if not logged clearly.
- Startup trigger can race with auth/profile hydration if readiness is not explicit.
- Duplicate sync suppression must not accidentally block legitimate manual sync.

## Recommended Order

1. Add startup trigger with one-shot/in-flight guards.
2. Defer profile-maintenance work off the foreground critical path.
3. Instrument timings.
4. Clean up overlapping screen-trigger behavior.

## Likely Files To Change

- `lib/features/sync/application/sync_initializer.dart`
- `lib/features/sync/application/sync_orchestrator.dart`
- `lib/features/sync/application/sync_lifecycle_manager.dart`
- `lib/features/sync/engine/sync_engine.dart`
- `lib/features/projects/presentation/providers/project_provider.dart`
- `lib/features/projects/presentation/screens/project_list_screen.dart`
- `lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart`
- `lib/core/router/scaffold_with_nav_bar.dart`

---
feature: sync
type: architecture
scope: Cloud Synchronization & Multi-Backend Support
updated: 2026-04-07
---

# Sync Feature Architecture

## Current Shape

The sync feature now has two equally important public surfaces:

1. the application and engine layers that run sync work
2. the driver-facing UI contract surface that allows sync coordinators,
   orchestrators, and verification flows to drive the UI deterministically

```text
Presentation
  SyncProvider
  SyncDashboardScreen / ConflictViewerScreen
  screen contracts + testing keys + flow definitions

Application
  SyncCoordinator
  SyncLifecycleManager
  SyncRetryPolicy / ConnectivityProbe / SyncTriggerPolicy / PostSyncHooks
  SyncQueryService / SyncEngineFactory
  BackgroundSyncHandler / FcmHandler / RealtimeHintHandler

Engine
  SyncEngine
  PushHandler / PushExecutionRouter / PullHandler / MaintenanceHandler
  LocalSyncStore / SupabaseSync / FileSyncHandler
  SyncHintRemoteEmitter
  EnrollmentHandler / FkRescueHandler / SyncErrorClassifier
  SyncMutex / SyncStatusStore / SyncRunLifecycle / IntegrityChecker
```

The detailed implementation guide remains:
- `.claude/docs/guides/implementation/sync-architecture.md`

## Presentation Layer

### SyncProvider

`lib/features/sync/presentation/providers/sync_provider.dart`

`SyncProvider` is now a thin presentation facade with focused part files:
- `sync_provider_controls.dart`
- `sync_provider_listeners.dart`
- `sync_provider_status_text.dart`

Responsibilities:
- trigger `quick` and `full` sync requests through `SyncCoordinator`
- expose transport state from `SyncStatusStore`
- expose diagnostics reads through `SyncQueryService`
- surface hint-transport and circuit-breaker state for the UI

It must not:
- assemble dashboard queries inline
- duplicate error-classification logic
- become the only entry point for sync verification

### Sync Screens

`SyncDashboardScreen` and `ConflictViewerScreen` are screen shells backed by
stable root sentinels in `TestingKeys`. They are part of the sync-driving
surface and must remain aligned with:
- `lib/core/driver/screen_registry.dart`
- `lib/core/driver/screen_contract_registry.dart`
- `lib/core/driver/flow_registry.dart`
- `lib/core/driver/driver_diagnostics_handler.dart`

## Application Layer

### SyncCoordinator

`lib/features/sync/application/sync_coordinator.dart`

Top-level foreground/background sync entry point. It:
- resolves runtime auth/context before engine creation
- runs retry/backoff policy
- records manual trigger behavior
- schedules background retry after retry exhaustion
- runs post-sync hooks after successful work
- exposes transport-state updates through `SyncStatusStore`

### RealtimeHintHandler

`lib/features/sync/application/realtime_hint_handler.dart`

Owns the client-side foreground invalidation contract. It:
- registers opaque private channels through `register_sync_hint_channel`
- tears them down through `deactivate_sync_hint_channel`
- owns the only client-side `onBroadcast(event: 'sync_hint', ...)` wiring
- marks dirty scope and triggers throttled quick sync through `SyncCoordinator`
- falls back to polling when channel registration or subscription is unhealthy

It must not:
- derive channel names client-side
- issue raw `/realtime/v1/api/broadcast` HTTP requests
- duplicate push-side hint emission logic

### SyncHintRemoteEmitter

`lib/features/sync/engine/sync_hint_remote_emitter.dart`

Owns push-side foreground hint emission. After successful remote writes,
`PushHandler` routes through `PushExecutionRouter`, which now emits
`emit_sync_hint(...)` via this dedicated engine component.

This is the deterministic foreground-hint contract. Remote trigger fanout still
exists as server-side support, but foreground proof now relies on the owned
push-side emitter instead of broad trigger side effects.

### SyncQueryService

`lib/features/sync/application/sync_query_service.dart`

Typed diagnostics read surface for dashboard and verification consumers.
It owns:
- pending bucket counts
- undismissed conflict counts
- persisted last-success metadata
- `SyncDiagnosticsSnapshot` assembly

Dashboard code and driver diagnostics must read through this service rather
than ad hoc SQL.

## Driver Contract Surface

The sync refactor now assumes a first-class driver contract layer:

### Screen Registry

`lib/core/driver/screen_registry.dart`

Bootstraps decomposed screens in isolation. Seed args must stay aligned with
screen contracts.

### Screen Contracts

`lib/core/driver/screen_contract_registry.dart`

Defines the stable verification contract for sync-relevant screens:
- screen id
- root sentinel key
- accepted seed args
- route patterns
- action and state keys

### Flow Registry

`lib/core/driver/flow_registry.dart`

Holds declarative verification journeys. When screens or routes move, flows
must move with them so sync verification stays route-stable.

### Diagnostics

`lib/core/driver/driver_diagnostics_handler.dart`

Provides `/diagnostics/screen_contract`, which is the unified sync-facing
endpoint for:
- active route
- active screen id
- root sentinel key presence
- contract metadata
- breakpoint, density, motion, and theme state

This endpoint is the preferred way for sync coordinators and orchestrators to
inspect UI state.

## Foreground Hint Contract

Foreground invalidation now has explicit ownership boundaries:
- `PushHandler` must be constructed with `syncHintEmitter:`
- `SyncHintRemoteEmitter` is the only normal client owner of `emit_sync_hint`
- `RealtimeHintHandler` is the only normal client owner of
  `register_sync_hint_channel`, `deactivate_sync_hint_channel`, and
  `onBroadcast(event: 'sync_hint', ...)`
- active topic lookup comes from `sync_hint_subscriptions`, not client-derived
  channel naming and not extra `user_profiles` joins
- raw client HTTP calls to `/realtime/v1/api/broadcast` are forbidden

The live contract was proven by foreground delivery of
`entry_quantities/680adba1-50ac-47ee-894b-251ecd059f4f` to S21 without any
manual sync call.

## Status vs Diagnostics

The refactor intentionally split sync state into three shapes:
- `SyncStatus`: live transport state
- `SyncDiagnosticsSnapshot`: point-in-time operational diagnostics
- `SyncEvent`: transient lifecycle events

`SyncStatusStore` is the transport-state source of truth.
`SyncQueryService` owns diagnostics snapshots.
Driver diagnostics owns screen-contract visibility.

## Verification Bar

The current verification model for sync is:
- characterization tests for engine/application behavior
- widget/provider tests for transport and diagnostics surfaces
- flow-driven verification through `flow_registry.dart`
- screen-contract inspection through `/diagnostics/screen_contract`
- no widget-tree archaeology for sync-relevant screens

## Key Files

- `lib/features/sync/application/sync_coordinator.dart`
- `lib/features/sync/application/realtime_hint_handler.dart`
- `lib/features/sync/application/sync_engine_factory.dart`
- `lib/features/sync/application/sync_query_service.dart`
- `lib/features/sync/engine/sync_hint_remote_emitter.dart`
- `lib/features/sync/engine/push_execution_router.dart`
- `lib/features/sync/engine/sync_engine.dart`
- `lib/features/sync/presentation/providers/sync_provider.dart`
- `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`
- `lib/features/sync/presentation/screens/conflict_viewer_screen.dart`
- `lib/core/driver/screen_registry.dart`
- `lib/core/driver/screen_contract_registry.dart`
- `lib/core/driver/flow_registry.dart`
- `lib/core/driver/driver_diagnostics_handler.dart`
- `.claude/rules/sync/sync-patterns.md`
- `.claude/rules/testing/patrol-testing.md`

---
feature: sync
type: overview
scope: Cloud Synchronization & Multi-Backend Support
updated: 2026-04-07
---

# Sync Feature Overview

## Purpose

The sync feature keeps the app SQLite-first while reconciling local changes
with Supabase when connectivity and auth context are available.

Primary goals:
- never lose offline work
- keep foreground sync fast by default
- make failures visible instead of silent
- keep transport state, diagnostics, and UI verification independently inspectable

## Public Entry Points

- `SyncCoordinator` is the application-layer sync entry point
- `SyncProvider` is the presentation-layer transport state and action surface
- `SyncQueryService` serves diagnostics reads
- `RealtimeHintHandler` owns foreground private-channel registration and hint
  consumption
- `SyncHintRemoteEmitter` owns push-side `emit_sync_hint(...)` after successful
  remote writes
- `screen_registry.dart`, `screen_contract_registry.dart`, and `flow_registry.dart`
  expose the UI surface to the sync driver
- `/diagnostics/screen_contract` exposes the active route + screen contract payload

## Foreground Hint Contract

Foreground freshness is no longer an implicit side effect. The enforced shape is:
- push success -> `PushHandler` -> `SyncHintRemoteEmitter` -> `emit_sync_hint`
- client subscribe/consume -> `RealtimeHintHandler`
- active channels -> `sync_hint_subscriptions`
- background/closed-app wakeup -> `FcmHandler`

Raw client broadcast HTTP and ad hoc sync-hint subscriptions are forbidden by
custom lint. This matters because the hosted fix required several migrations;
the repo now treats the owned emitter/subscriber split as an architecture rule,
not an implementation detail.

## Key Files

| File | Purpose |
|------|---------|
| `lib/features/sync/application/sync_coordinator.dart` | Main sync coordinator |
| `lib/features/sync/application/realtime_hint_handler.dart` | Private-channel registration, hint subscription, quick-sync trigger |
| `lib/features/sync/application/sync_query_service.dart` | Typed diagnostics query surface |
| `lib/features/sync/engine/sync_hint_remote_emitter.dart` | Push-side `emit_sync_hint(...)` owner |
| `lib/features/sync/engine/push_execution_router.dart` | Push routing, including hint emission hook |
| `lib/features/sync/presentation/providers/sync_provider.dart` | UI-facing sync state and actions |
| `lib/features/sync/presentation/screens/sync_dashboard_screen.dart` | Diagnostics dashboard |
| `lib/features/sync/presentation/screens/conflict_viewer_screen.dart` | Conflict review UI |
| `lib/core/driver/screen_registry.dart` | Bootstrappable screen builders |
| `lib/core/driver/screen_contract_registry.dart` | Stable screen verification contracts |
| `lib/core/driver/flow_registry.dart` | Declarative sync/UI journeys |
| `lib/core/driver/driver_diagnostics_handler.dart` | Diagnostics endpoints including `/diagnostics/screen_contract` |

## Verification Model

Sync verification now relies on:
- provider/widget tests
- declarative driver flows
- stable testing keys
- screen contracts
- owned sync-hint contract tests plus live private-channel proof

It should not rely on widget-tree archaeology or implicit route assumptions.

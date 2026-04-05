# Pattern: Application Orchestrator (SyncOrchestrator)

## How We Do It

SyncOrchestrator sits between the presentation layer and the engine. It creates SyncEngine instances per sync cycle via SyncEngineFactory, manages retry with exponential backoff, checks DNS reachability, runs post-sync hooks (profile refresh, config freshness), and exposes sync state to the provider. Currently 730 lines with SQL queries that should be in a data layer.

## Exemplar: SyncOrchestrator

### Construction via Builder (sync_orchestrator.dart:113-135)

```dart
SyncOrchestrator.fromBuilder({
  required DatabaseService dbService,
  SupabaseClient? supabaseClient,
  required SyncEngineFactory engineFactory,
  UserProfileSyncDatasource? userProfileSyncDatasource,
  required ({String? companyId, String? userId}) Function() syncContextProvider,
  AppConfigProvider? appConfigProvider,
  DirtyScopeTracker? dirtyScopeTracker,
})
```

### syncLocalAgencyProjects — Main Entry Point (sync_orchestrator.dart:263-365)

```dart
Future<SyncResult> syncLocalAgencyProjects({
  SyncMode mode = SyncMode.full,
  bool recordManualTrigger = false,
})
```

Flow:
1. Cancel background retry timer
2. Check auth context availability
3. Track analytics if manual trigger
4. Set `_isSyncing = true`
5. Call `_syncWithRetry(mode:)`
6. On success: refresh last_sync_time from DB, call `_appConfigProvider?.recordSyncSuccess()`, call `_userProfileSyncDatasource?.pullCompanyMembers()`
7. Fire `onSyncComplete` callback
8. Always set `_isSyncing = false` in finally

### _syncWithRetry — Retry Loop (sync_orchestrator.dart:372-459)

```dart
Future<SyncResult> _syncWithRetry({SyncMode mode = SyncMode.full})
```

- Up to `_maxRetries` (2) attempts
- DNS check before every attempt
- Exponential backoff: `_baseRetryDelay * (1 << attempt)` (10s, 20s)
- On exhaustion: schedules 60s background Timer retry (cancellable)
- Checks `_isTransientError()` to decide if retry is worthwhile

### _isTransientError — Triplicated Error Classification (sync_orchestrator.dart:507-569)

Pattern-matches error messages against string lists. This is one of three error classification sites.

### getPendingBuckets — SQL in Orchestrator (sync_orchestrator.dart:607-666)

Contains 3 raw SQL queries against `change_log`. This is the layer violation being fixed by moving to `SyncQueryService`.

### checkDnsReachability (sync_orchestrator.dart:581-603)

HTTP HEAD to Supabase REST endpoint with 5s timeout. Updates `_isOnline` state. This becomes `ConnectivityProbe`.

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| syncLocalAgencyProjects | sync_orchestrator.dart:263 | `Future<SyncResult> syncLocalAgencyProjects({SyncMode mode, bool recordManualTrigger})` | Main sync trigger |
| checkDnsReachability | sync_orchestrator.dart:581 | `Future<bool> checkDnsReachability()` | Pre-sync reachability |
| getPendingBuckets | sync_orchestrator.dart:607 | `Future<Map<String, BucketCount>> getPendingBuckets()` | Dashboard pending counts |
| getIntegrityResults | sync_orchestrator.dart:682 | `Future<Map<String, String>> getIntegrityResults()` | Dashboard integrity data |
| getUndismissedConflictCount | sync_orchestrator.dart:704 | `Future<int> getUndismissedConflictCount()` | Dashboard conflict count |
| initialize | sync_orchestrator.dart:165 | `Future<void> initialize()` | Load last_sync_time from DB |
| dispose | (present) | `void dispose()` | Cancel timers, set _disposed |

## Callback Fields

| Field | Type | Purpose |
|-------|------|---------|
| `onPullComplete` | `Future<void> Function(String, int)?` | Per-table pull completion |
| `onSyncComplete` | `void Function(SyncResult)?` | Full sync cycle completion |
| `onNewAssignmentDetected` | `void Function(String)?` | Enrollment notification |
| `onCircuitBreakerTrip` | `void Function(String, String, int)?` | Circuit breaker trip event |

## Imports

```dart
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/core/analytics/analytics.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/config/supabase_config.dart';
import 'package:construction_inspector/core/config/test_mode_config.dart';
import 'package:construction_inspector/features/auth/data/datasources/remote/user_profile_sync_datasource.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
import 'package:construction_inspector/features/sync/data/adapters/mock_sync_adapter.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/features/sync/engine/sync_engine.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';
import 'package:construction_inspector/shared/utils/safe_row.dart';
```

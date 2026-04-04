# Pattern: Sync Initialization

## How We Do It

Sync components are wired during app startup through a layered initialization chain: `main.dart` → `AppInitializer.initialize()` → `SyncProviders.initialize()` → `SyncInitializer.create()`. The initializer creates all sync components in dependency order (builder → orchestrator → lifecycle manager → enrollment → FCM → Realtime), then returns them as a named record tuple. The auth listener in `AppInitializer` handles runtime rebinding when auth/company state changes.

## Exemplars

### SyncInitializer.create() (`lib/features/sync/application/sync_initializer.dart:42`)

```dart
static Future<({
  SyncOrchestrator orchestrator,
  SyncLifecycleManager lifecycleManager,
  FcmHandler? fcmHandler,
  RealtimeHintHandler? realtimeHintHandler,
})> create({
  required DatabaseService dbService,
  required AuthProvider authProvider,
  required AppConfigProvider appConfigProvider,
  required CompanyLocalDatasource companyLocalDs,
  required AuthService authService,
  SupabaseClient? supabaseClient,
}) async {
  // Step 1: Build orchestrator via builder pattern
  // Step 2: Wire UserProfileSyncDatasource if online
  // Step 3: Build orchestrator (fully configured, no setters)
  // Step 4: Create lifecycle manager
  // Step 5: Wire enrollment service
  // Step 6: FCM initialization (mobile only, non-blocking)
  // Step 7: Realtime hint handler (if Supabase client available)
  //    ← THIS IS WHERE DEVICE REGISTRATION WILL BE ADDED
  // Step 8: Register lifecycle observer
}
```

**Key architectural decisions:**
- `SupabaseClient?` nullable — offline mode skips network components
- FCM and Realtime are both optional — desktop has neither FCM
- Return type is a named record tuple — no wrapper class needed
- `unawaited()` for non-blocking FCM init — doesn't block startup

### AppInitializer auth listener (`lib/core/bootstrap/app_initializer.dart:183`)

The auth listener handles 3 state transitions:
1. **Sign-out**: dispose handler, clear company binding
2. **Sign-in / company ready**: create or rebind handler, schedule sync
3. **Company change while authenticated**: rebind handler to new channel

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `SyncInitializer.create()` | `sync_initializer.dart:42` | `static Future<(record)> create({...})` | One-time sync wiring at startup |
| `SyncProviders.initialize()` | `sync_providers.dart:28` | `static Future<(record)> initialize({...})` | DI delegation to SyncInitializer |
| `SyncProviders.providers()` | `sync_providers.dart:60` | `static List<SingleChildWidget> providers({...})` | Register sync providers for MultiProvider |

## Imports

```dart
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/auth/services/auth_service.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/features/sync/application/sync_lifecycle_manager.dart';
import 'package:construction_inspector/features/sync/application/fcm_handler.dart';
import 'package:construction_inspector/features/sync/application/realtime_hint_handler.dart';
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
```

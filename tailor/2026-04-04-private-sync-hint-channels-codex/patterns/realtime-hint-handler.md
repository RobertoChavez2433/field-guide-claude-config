# Pattern: Realtime Hint Handler

## How We Do It

The app uses a single `RealtimeHintHandler` instance per session to subscribe to a Supabase Broadcast channel for foreground sync invalidation. The handler parses incoming hint payloads, marks dirty scopes on the `DirtyScopeTracker`, and triggers throttled quick syncs via the `SyncOrchestrator`. The handler supports lifecycle transitions (subscribe, rebind on company change, dispose on sign-out) through a serialized transition queue.

## Exemplars

### RealtimeHintHandler (`lib/features/sync/application/realtime_hint_handler.dart`)

```dart
class RealtimeHintHandler {
  static const Duration _minSyncInterval = Duration(seconds: 30);

  final SupabaseClient _supabaseClient;
  final SyncOrchestrator _syncOrchestrator;
  String? _companyId;

  RealtimeChannel? _channel;
  DateTime? _lastSyncTrigger;
  bool _isSubscribed = false;
  Future<void> _transitionQueue = Future<void>.value();
  bool _queuedQuickSync = false;

  RealtimeHintHandler({
    required SupabaseClient supabaseClient,
    required SyncOrchestrator syncOrchestrator,
    String? companyId,
  }) : _supabaseClient = supabaseClient,
       _syncOrchestrator = syncOrchestrator,
       _companyId = companyId;

  void subscribe(String companyId) {
    if (_isSubscribed) return;
    if (_companyId != null && _companyId != companyId) return;

    final channelName = 'sync_hints:$companyId';  // ← THIS IS THE PREDICTABLE NAME TO REPLACE
    _channel = _supabaseClient
        .channel(channelName)
        .onBroadcast(event: 'sync_hint', callback: _handleHint);

    _channel!.subscribe((status, error) {
      if (status == RealtimeSubscribeStatus.subscribed) {
        _isSubscribed = true;
      }
    });
  }

  Future<void> rebind(String? companyId) {
    return _enqueueTransition(() async {
      if (_companyId == companyId) {
        if (companyId != null && !_isSubscribed) subscribe(companyId);
        return;
      }
      if (_channel != null) await _disposeNow();
      _companyId = companyId;
      if (companyId != null) subscribe(companyId);
    });
  }

  Future<void> _enqueueTransition(Future<void> Function() action) {
    final next = _transitionQueue.then((_) => action());
    _transitionQueue = next.catchError((_) {});
    return next;
  }
}
```

**Key architectural decisions:**
- `_transitionQueue` serializes subscribe/rebind/dispose to prevent races
- `_queuedQuickSync` coalesces multiple hints arriving during an active sync
- 30-second throttle prevents sync storms
- Static methods `parseHintPayload` and `dirtyScopeFromHint` are reused by `FcmHandler`

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `parseHintPayload` | `realtime_hint_handler.dart:49` | `static HintPayload parseHintPayload(Map<String, dynamic> payload)` | Parse any sync hint payload (Broadcast or FCM) |
| `dirtyScopeFromHint` | `realtime_hint_handler.dart:59` | `static ({String? projectId, String? tableName})? dirtyScopeFromHint(HintPayload hint)` | Convert hint to DirtyScope for tracker |
| `subscribe` | `realtime_hint_handler.dart:96` | `void subscribe(String companyId)` | Subscribe to Broadcast channel (to be replaced) |
| `rebind` | `realtime_hint_handler.dart:165` | `Future<void> rebind(String? companyId)` | Re-subscribe on company context change |
| `dispose` | `realtime_hint_handler.dart:190` | `Future<void> dispose()` | Cleanup on sign-out |
| `_handleHint` | `realtime_hint_handler.dart:126` | `void _handleHint(Map<String, dynamic> payload)` | Process incoming hint, mark dirty, trigger sync |
| `_triggerQuickSync` | `realtime_hint_handler.dart:206` | `void _triggerQuickSync({bool bypassThrottle = false})` | Throttled quick sync trigger |
| `_drainQueuedQuickSync` | `realtime_hint_handler.dart:221` | `Future<void> _drainQueuedQuickSync()` | Run follow-up sync after active sync completes |

## Imports

```dart
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
```

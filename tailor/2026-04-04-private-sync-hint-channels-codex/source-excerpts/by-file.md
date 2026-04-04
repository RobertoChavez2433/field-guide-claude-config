# Source Excerpts — By File

## lib/features/sync/application/realtime_hint_handler.dart

### HintPayload (L10-25)

```dart
@immutable
class HintPayload {
  final String? companyId;
  final String? projectId;
  final String? tableName;
  final String? changedAt;
  final String? scopeType;

  const HintPayload({
    this.companyId,
    this.projectId,
    this.tableName,
    this.changedAt,
    this.scopeType,
  });
}
```

### RealtimeHintHandler (L28-237) — full source

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

  static HintPayload parseHintPayload(Map<String, dynamic> payload) {
    return HintPayload(
      companyId: payload['company_id'] as String?,
      projectId: payload['project_id'] as String?,
      tableName: payload['table_name'] as String?,
      changedAt: payload['changed_at'] as String?,
      scopeType: payload['scope_type'] as String?,
    );
  }

  static ({String? projectId, String? tableName})? dirtyScopeFromHint(
    HintPayload hint,
  ) {
    final normalizedScopeType = hint.scopeType?.toLowerCase().replaceAll('-', '_');
    switch (normalizedScopeType) {
      case 'company': case 'companywide': case 'company_wide': case 'global':
        return (projectId: null, tableName: null);
      case 'project': case 'projectwide': case 'project_wide':
        if (hint.projectId != null) return (projectId: hint.projectId, tableName: null);
        if (hint.companyId != null) return (projectId: null, tableName: null);
        return null;
    }
    if (hint.projectId != null || hint.tableName != null) {
      return (projectId: hint.projectId, tableName: hint.tableName);
    }
    if (hint.companyId != null) return (projectId: null, tableName: null);
    return null;
  }

  void subscribe(String companyId) {
    if (_isSubscribed) { Logger.sync('RealtimeHintHandler: already subscribed'); return; }
    if (_companyId != null && _companyId != companyId) {
      Logger.sync('RealtimeHintHandler: refusing to subscribe due to company mismatch');
      return;
    }
    final channelName = 'sync_hints:$companyId';
    _channel = _supabaseClient
        .channel(channelName)
        .onBroadcast(event: 'sync_hint', callback: _handleHint);
    _channel!.subscribe((status, error) {
      if (status == RealtimeSubscribeStatus.subscribed) {
        _isSubscribed = true;
        Logger.sync('RealtimeHintHandler: subscribed to $channelName');
      } else if (status == RealtimeSubscribeStatus.closed) {
        _isSubscribed = false;
      } else if (error != null) {
        Logger.sync('RealtimeHintHandler: subscription error: $error');
      }
    });
  }

  void _handleHint(Map<String, dynamic> payload) {
    final hint = parseHintPayload(payload);
    if (hint.companyId != null && _companyId != null && hint.companyId != _companyId) {
      Logger.sync('RealtimeHintHandler: ignoring hint due to company mismatch');
      return;
    }
    final tracker = _syncOrchestrator.dirtyScopeTracker;
    final dirtyScope = dirtyScopeFromHint(hint);
    if (tracker != null && dirtyScope != null) {
      tracker.markDirty(projectId: dirtyScope.projectId, tableName: dirtyScope.tableName);
    }
    if (_syncOrchestrator.isSyncing) {
      _queuedQuickSync = true;
      return;
    }
    _triggerQuickSync();
  }

  Future<void> rebind(String? companyId) {
    return _enqueueTransition(() async {
      if (_companyId == companyId) {
        if (companyId != null && !_isSubscribed) subscribe(companyId);
        return;
      }
      final previousCompanyId = _companyId;
      if (_channel != null) await _disposeNow();
      _companyId = companyId;
      if (companyId == null) {
        Logger.sync('RealtimeHintHandler: cleared company binding (was ${previousCompanyId ?? 'none'})');
        return;
      }
      Logger.sync('RealtimeHintHandler: rebinding from ${previousCompanyId ?? 'none'} to $companyId');
      subscribe(companyId);
    });
  }

  Future<void> dispose() { return _enqueueTransition(_disposeNow); }

  Future<void> _disposeNow() async {
    final channel = _channel;
    if (channel == null) return;
    await _supabaseClient.removeChannel(channel);
    _channel = null;
    _isSubscribed = false;
  }

  Future<void> _enqueueTransition(Future<void> Function() action) {
    final next = _transitionQueue.then((_) => action());
    _transitionQueue = next.catchError((_) {});
    return next;
  }

  void _triggerQuickSync({bool bypassThrottle = false}) {
    final now = DateTime.now();
    if (!bypassThrottle && _lastSyncTrigger != null &&
        now.difference(_lastSyncTrigger!) < _minSyncInterval) {
      return;
    }
    _lastSyncTrigger = now;
    unawaited(
      _syncOrchestrator.syncLocalAgencyProjects(mode: SyncMode.quick)
          .whenComplete(_drainQueuedQuickSync),
    );
  }

  Future<void> _drainQueuedQuickSync() async {
    if (!_queuedQuickSync || _syncOrchestrator.isSyncing) return;
    _queuedQuickSync = false;
    final tracker = _syncOrchestrator.dirtyScopeTracker;
    if (tracker != null && !tracker.hasDirtyScopes) return;
    _triggerQuickSync(bypassThrottle: true);
  }
}
```

## lib/features/sync/application/sync_initializer.dart

### SyncInitializer.create() — Realtime handler wiring section (L129-142)

```dart
RealtimeHintHandler? realtimeHintHandler;
if (supabaseClient != null) {
  realtimeHintHandler = RealtimeHintHandler(
    supabaseClient: supabaseClient,
    syncOrchestrator: syncOrchestrator,
    companyId: authProvider.userProfile?.companyId,
  );
  final companyId = authProvider.userProfile?.companyId;
  if (companyId != null) {
    realtimeHintHandler.subscribe(companyId);
  }
}
```

## lib/core/bootstrap/app_initializer.dart

### Auth listener — Realtime handler lifecycle (L117-262)

See `source-excerpts/by-concern.md` for the full auth listener with annotations.

## supabase/migrations/20260404000000_sync_hint_broadcast_trigger.sql

### broadcast_sync_hint_company() (L40-104)
### broadcast_sync_hint_project() (L106-179)
### broadcast_sync_hint_contractor() (L181-257)
### 20 trigger bindings (L259-358)

Full source in `patterns/sql-trigger-fanout.md`.

## supabase/functions/daily-sync-push/index.ts

### Company-scoped FCM fan-out (L84-116)

```typescript
let tokensResponse;
if (hintParams?.company_id) {
  const { data: profiles, error: profilesError } = await supabase
    .from("user_profiles")
    .select("id")
    .eq("company_id", hintParams.company_id);

  // ... error handling ...

  const userIds = (profiles ?? []).map((profile) => profile.id as string);
  tokensResponse = await supabase
    .from("user_fcm_tokens")
    .select("user_id, token")
    .in("user_id", userIds);
} else {
  tokensResponse = await supabase
    .from("user_fcm_tokens")
    .select("user_id, token");
}
```

## supabase/migrations/20260222200000_add_fcm_tokens.sql

### user_fcm_tokens table (full)

```sql
CREATE TABLE user_fcm_tokens (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  token TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE user_fcm_tokens ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own_token_only" ON user_fcm_tokens
  FOR ALL TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());
```

## lib/shared/services/preferences_service.dart

### Key constant pattern (L16-21)

```dart
static const String keyGaugeNumber = 'gauge_number';
static const String keyLastRoute = 'last_route_location';
static const String keyDebugLogDir = 'debug_log_dir';
static const String keyPasswordRecoveryActive = 'password_recovery_active';
```

## lib/features/sync/domain/sync_types.dart

### SyncMode enum (L72-81)

```dart
enum SyncMode {
  quick,       // Fast foreground: push + pull dirty scopes
  full,        // Recovery: broad push and pull
  maintenance, // Background: integrity, cleanup, pruning
}
```

### DirtyScope (L84-109)

```dart
@immutable
class DirtyScope {
  final String? projectId;
  final String? tableName;
  final DateTime markedAt;

  const DirtyScope({this.projectId, this.tableName, required this.markedAt});

  bool get isCompanyWide => projectId == null;
  bool get isAllTables => tableName == null;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is DirtyScope && projectId == other.projectId && tableName == other.tableName;

  @override
  int get hashCode => Object.hash(projectId, tableName);
}
```

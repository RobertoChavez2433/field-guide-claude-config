# Source Excerpts — By Concern

## Concern 1: Channel Registration (New)

### What exists today
No channel registration exists. The client constructs `sync_hints:{company_id}` locally and subscribes directly.

### What needs to be built
1. Server-side `sync_hint_subscriptions` table
2. `register_sync_hint_channel()` RPC (auth-protected, returns opaque channel name)
3. Client-side `device_install_id` persistence
4. Client-side registration call in `RealtimeHintHandler` or a new service

### Analogous pattern: FCM token registration
See `patterns/fcm-token-registration.md` — the `user_fcm_tokens` table + `saveFcmToken()` flow is structurally identical.

---

## Concern 2: Client Channel Subscription (Modify)

### Current: predictable channel (`realtime_hint_handler.dart:96-124`)

```dart
void subscribe(String companyId) {
  if (_isSubscribed) return;
  final channelName = 'sync_hints:$companyId';  // ← PREDICTABLE
  _channel = _supabaseClient
      .channel(channelName)
      .onBroadcast(event: 'sync_hint', callback: _handleHint);
  _channel!.subscribe((status, error) { ... });
}
```

### New: opaque channel from registration RPC

The `subscribe` method will be replaced with a flow that:
1. Calls `register_sync_hint_channel(device_install_id, platform, app_version)` RPC
2. Receives `{channel_name, subscription_id, expires_at, refresh_after}`
3. Subscribes to the returned opaque `channel_name`
4. Stores `refresh_after` for periodic re-registration

---

## Concern 3: Auth/Company Rebinding (Modify)

### Current: app_initializer.dart auth listener (L183-262)

```dart
authDeps.authProvider.addListener(() {
  final isNowAuthenticated = authDeps.authProvider.isAuthenticated;
  final companyId = authDeps.authProvider.userProfile?.companyId;

  // Sign-out: dispose handler
  if (wasAuthenticated && !isNowAuthenticated) {
    activeFcmHandler?.updateContext(userId: null, companyId: null);
    if (activeRealtimeHintHandler != null) {
      final handlerToDispose = activeRealtimeHintHandler!;
      unawaited(() async {
        await handlerToDispose.dispose();
        activeRealtimeCompanyId = null;
      }());
      activeRealtimeHintHandler = null;
    }
  }

  // Sign-in / company change: create or rebind handler
  if (isNowAuthenticated && authDeps.authProvider.userId != null) {
    activeFcmHandler?.updateContext(userId: ..., companyId: companyId);
    if (supabaseClient != null) {
      activeRealtimeHintHandler ??= RealtimeHintHandler(
        supabaseClient: supabaseClient,
        syncOrchestrator: syncResult.orchestrator,
        companyId: activeRealtimeCompanyId,
      );
      if (activeRealtimeCompanyId != companyId) {
        unawaited(() async {
          await activeRealtimeHintHandler!.rebind(companyId);
          activeRealtimeCompanyId = companyId;
        }());
      }
    }
  }
});
```

### Changes needed:
- `rebind()` must deactivate old subscription + re-register for new company
- Sign-out should call optional `deactivate_sync_hint_channel()` RPC
- Sign-in should register and subscribe to new opaque channel

---

## Concern 4: Sync Initializer Wiring (Modify)

### Current: `sync_initializer.dart` L129-142

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

### Changes needed:
- Pass `device_install_id` to handler (or inject PreferencesService)
- Replace `subscribe(companyId)` with `registerAndSubscribe(companyId, deviceInstallId)`
- The registration call is async — may need to `await` or fire-and-forget

---

## Concern 5: Server-Side Fan-Out (Modify)

### Current: single-channel broadcast (`broadcast_trigger.sql:79-93`)

```sql
v_channel_name := 'sync_hints:' || v_company_id::text;

PERFORM extensions.http_post(
  url := v_realtime_url || '/api/broadcast',
  headers := jsonb_build_object('Content-Type', 'application/json', 'apikey', v_service_role_key),
  body := jsonb_build_object('channel', v_channel_name, 'event', 'sync_hint', 'payload', v_payload)
);
```

### New: per-device fan-out loop

Replace single `http_post` with:
1. Query `sync_hint_subscriptions` for active, non-expired rows matching `company_id`
2. Loop over results, broadcasting to each device's `channel_name`
3. Keep `invoke_daily_sync_push()` call for FCM fallback

### Performance note:
Advisory lock deduplication already limits broadcasts per table+company per transaction. The loop adds N HTTP calls (N = active devices per company). For small teams (typical: 2-10 inspectors), this is acceptable. For large deployments, consider batching or a helper edge function.

---

## Concern 6: Edge Function FCM Fan-Out (Modify)

### Current: `daily-sync-push/index.ts` L84-116

Queries `user_profiles` by `company_id` → gets user IDs → queries `user_fcm_tokens`. This stays the same — FCM fan-out is already per-device via tokens.

### Changes needed:
None for FCM flow. The edge function may optionally also do Broadcast fan-out if we move the per-device broadcast from SQL triggers to the edge function (architectural choice).

---

## Concern 7: Subscription Cleanup (New)

### What exists today
FCM tokens are cleaned up in the edge function when Firebase returns `UNREGISTERED` or `INVALID_ARGUMENT`.

### What needs to be built
- Periodic cleanup of expired `sync_hint_subscriptions` rows
- `last_seen_at` update on each registration refresh
- Optional: Supabase cron job or edge function for stale subscription pruning

---

## Concern 8: Tests (Modify + New)

### Current test: `test/features/sync/application/realtime_hint_handler_test.dart`

Uses `_TrackingOrchestrator` (extends `SyncOrchestrator`) and `MockRealtimeChannel` to test:
- Hint payload parsing
- Dirty scope conversion
- Subscribe/rebind/dispose lifecycle
- Throttling and queued quick sync

### Changes needed:
- Mock the registration RPC response
- Test opaque channel subscription
- Test re-registration on company change
- Test cleanup on sign-out
- Test expired subscription handling

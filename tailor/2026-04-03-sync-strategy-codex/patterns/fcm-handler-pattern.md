# Pattern: FCM Handler (Push Notification → Sync Trigger)

## How We Do It
FcmHandler initializes Firebase Cloud Messaging on Android/iOS, registers a device token with Supabase `user_fcm_tokens` table, and listens for foreground/background messages. Currently, the only message type handled is `daily_sync`, which triggers a full `syncLocalAgencyProjects()` with 60-second rate limiting. There is no hint parsing, no scope targeting, and no invalidation payload processing.

## Exemplars

### FcmHandler.handleForegroundMessage (fcm_handler.dart:100-116)
```dart
void handleForegroundMessage(RemoteMessage message) {
    Logger.sync('FCM foreground message messageId=${message.messageId}');
    final messageType = message.data['type'];
    if (messageType == 'daily_sync') {
      final now = DateTime.now();
      if (_lastFcmSyncTrigger != null &&
          now.difference(_lastFcmSyncTrigger!).inSeconds < 60) {
        Logger.sync('FCM sync trigger throttled (< 60s since last)');
        return;
      }
      _lastFcmSyncTrigger = now;
      Logger.sync('FCM daily sync trigger (foreground) — triggering sync');
      _syncOrchestrator?.syncLocalAgencyProjects();
    }
  }
```

### FcmHandler.initialize (fcm_handler.dart:48-93)
```dart
Future<void> initialize({String? userId}) async {
    if (_isInitialized) return;
    if (!(Platform.isAndroid || Platform.isIOS)) return;
    try {
      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission(alert: false, badge: false, sound: false);
      final token = await messaging.getToken();
      if (token != null) await _saveFcmToken(userId, token);
      messaging.onTokenRefresh.listen((newToken) => _saveFcmToken(userId, newToken));
      FirebaseMessaging.onBackgroundMessage(fcmBackgroundMessageHandler);
      FirebaseMessaging.onMessage.listen(handleForegroundMessage);
      _isInitialized = true;
    } catch (e) {
      Logger.sync('FCM initialization error: $e');
    }
  }
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `initialize` | `fcm_handler.dart:48` | `Future<void> initialize({String? userId})` | App startup (mobile only) |
| `handleForegroundMessage` | `fcm_handler.dart:100` | `void handleForegroundMessage(RemoteMessage message)` | FCM foreground dispatch |
| `_saveFcmToken` | `fcm_handler.dart:119` | `Future<void> _saveFcmToken(String? userId, String token)` | Token persistence |

## Imports
```dart
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/auth/services/auth_service.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
```

## Gap Analysis for Spec

**No hint parsing**: Current code only checks `data['type'] == 'daily_sync'`. Spec wants:
```json
{
  "company_id": "...",
  "project_id": "...",
  "table_name": "...",
  "changed_at": "...",
  "scope_type": "..."
}
```

**No dirty scope marking**: FCM currently triggers full sync. Spec wants: parse hint → mark scope dirty → trigger quick targeted sync.

**Background handler is a no-op**: `fcmBackgroundMessageHandler` is a top-level function at line 13 that currently just logs. Spec wants it to mark dirty scopes and schedule a quick sync.

**Server-side function exists**: `supabase/functions/daily-sync-push/index.ts` handles the FCM push from server. This needs to be extended to send hint payloads.

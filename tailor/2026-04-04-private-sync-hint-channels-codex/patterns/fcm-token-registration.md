# Pattern: FCM Token Registration

## How We Do It

The `FcmHandler` manages Firebase Cloud Messaging token lifecycle. On mobile startup, it requests FCM permissions, obtains a token, saves it to the `user_fcm_tokens` table via `AuthService.saveFcmToken()`, and listens for token refreshes. The token is scoped to the authenticated user. The `daily-sync-push` edge function queries this table to resolve FCM push targets. This pattern is directly analogous to the new `sync_hint_subscriptions` table — both map devices to server-side resources for targeted push.

## Exemplars

### FcmHandler (`lib/features/sync/application/fcm_handler.dart:57`)

Key lifecycle methods:
- `initialize({String? userId})` — request permissions, get token, save to Supabase
- `updateContext({String? userId, String? companyId})` — rebind on auth changes
- `handleForegroundMessage(RemoteMessage)` — parse hint, mark dirty, trigger sync
- `_saveFcmToken(String? userId, String token)` — persist to `user_fcm_tokens`

### user_fcm_tokens table (`supabase/migrations/20260222200000_add_fcm_tokens.sql`)

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

**Note**: Currently one token per user (PK on user_id). The new `sync_hint_subscriptions` supports multiple devices per user.

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `FcmHandler.initialize()` | `fcm_handler.dart:103` | `Future<void> initialize({String? userId})` | Mobile-only FCM setup at startup |
| `FcmHandler.updateContext()` | `fcm_handler.dart:92` | `void updateContext({String? userId, String? companyId})` | Rebind on auth/company change |
| `FcmHandler.handleForegroundMessage()` | `fcm_handler.dart:145` | `void handleForegroundMessage(RemoteMessage message)` | Parse FCM data message |
| `AuthService.saveFcmToken()` | `auth_service.dart` | `Future<void> saveFcmToken(String userId, String token)` | Persist FCM token to Supabase |

## Imports

```dart
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:construction_inspector/features/auth/services/auth_service.dart';
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
import 'package:construction_inspector/features/sync/application/realtime_hint_handler.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
```

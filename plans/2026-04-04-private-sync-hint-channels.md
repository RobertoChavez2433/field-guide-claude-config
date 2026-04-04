# Private Sync Hint Channels Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Replace predictable tenant-wide Broadcast channels (`sync_hints:{company_id}`) with opaque per-device channels issued by an auth-protected server RPC, eliminating metadata leakage while preserving the existing sync architecture.
**Spec:** `.claude/specs/2026-04-04-private-sync-hint-channels-codex-spec.md`
**Tailor:** `.claude/tailor/2026-04-04-private-sync-hint-channels-codex/`

**Architecture:** Server issues opaque channel names via `register_sync_hint_channel()` RPC backed by a `sync_hint_subscriptions` table. SQL triggers call `invoke_daily_sync_push()` which invokes the `daily-sync-push` edge function. The edge function handles both FCM push AND per-device Broadcast fan-out (querying `sync_hint_subscriptions` for active channels). Client persists a `device_install_id` and registers on auth-ready startup, subscribing only to the returned opaque channel.
**Tech Stack:** PostgreSQL (Supabase), Dart/Flutter, Supabase Realtime Broadcast, SharedPreferences, Deno (edge function)
**Blast Radius:** 5 direct (realtime_hint_handler, sync_initializer, app_initializer, broadcast_trigger.sql, preferences_service), 1 edge function (daily-sync-push/index.ts), 5 dependent (app_bootstrap, app_providers, main, main_driver, fcm_handler_test), 2 tests (realtime_hint_handler_test, new registration tests), 0 cleanup

---

## Phase 1: Server-Side Subscription Infrastructure

### Sub-phase 1.1: Create sync_hint_subscriptions Table and RPCs

**Files:**
- Create: `supabase/migrations/20260405000000_sync_hint_subscriptions.sql`

**Agent**: backend-supabase-agent

#### Step 1.1.1: Create the sync_hint_subscriptions table

```sql
-- FROM SPEC: Subscription Storage (§4) — server-side table for active sync-hint subscriptions
-- WHY: Stores per-device opaque channel assignments so triggers can fan out to individual devices
CREATE TABLE public.sync_hint_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
  device_install_id TEXT NOT NULL,
  channel_name TEXT NOT NULL,
  platform TEXT,
  app_version TEXT,
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '7 days'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at TIMESTAMPTZ
);

-- WHY: Channel names must be globally unique to prevent cross-device collisions
ALTER TABLE public.sync_hint_subscriptions
  ADD CONSTRAINT uq_channel_name UNIQUE (channel_name);

-- WHY: Fan-out queries filter by company_id + active status
CREATE INDEX idx_sync_hint_subs_company_active
  ON public.sync_hint_subscriptions (company_id)
  WHERE revoked_at IS NULL AND expires_at > now();

-- WHY: Registration upserts by user + device
CREATE UNIQUE INDEX idx_sync_hint_subs_user_device
  ON public.sync_hint_subscriptions (user_id, device_install_id)
  WHERE revoked_at IS NULL;

ALTER TABLE public.sync_hint_subscriptions ENABLE ROW LEVEL SECURITY;

-- WHY: Auto-update updated_at on any row modification, consistent with other tables
CREATE TRIGGER trg_sync_hint_subs_updated_at
  BEFORE UPDATE ON public.sync_hint_subscriptions
  FOR EACH ROW
  EXECUTE FUNCTION public.set_updated_at();

-- WHY: Users can only read their own subscriptions
CREATE POLICY "select_own" ON public.sync_hint_subscriptions
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- WHY: Users can only delete their own subscriptions
CREATE POLICY "delete_own" ON public.sync_hint_subscriptions
  FOR DELETE TO authenticated
  USING (user_id = auth.uid());

-- WHY: INSERT/UPDATE must validate both user_id ownership AND company_id matches
-- the caller's actual company from user_profiles (prevents cross-company injection)
CREATE POLICY "write_own_validated" ON public.sync_hint_subscriptions
  FOR INSERT TO authenticated
  WITH CHECK (
    user_id = auth.uid()
    AND company_id = (SELECT up.company_id FROM public.user_profiles up WHERE up.id = auth.uid())
  );

CREATE POLICY "update_own_validated" ON public.sync_hint_subscriptions
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (
    user_id = auth.uid()
    AND company_id = (SELECT up.company_id FROM public.user_profiles up WHERE up.id = auth.uid())
  );
```

#### Step 1.1.2: Create register_sync_hint_channel() RPC

```sql
-- FROM SPEC: Registration Model (§2) — auth-protected RPC that issues opaque channel names
-- WHY: Server generates channel names so clients never construct predictable names
-- SECURITY: SECURITY INVOKER ensures auth.uid() resolves to the caller
CREATE OR REPLACE FUNCTION public.register_sync_hint_channel(
  p_device_install_id TEXT,
  p_platform TEXT DEFAULT NULL,
  p_app_version TEXT DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
  v_user_id UUID;
  v_company_id UUID;
  v_channel_name TEXT;
  v_sub_id UUID;
  v_expires_at TIMESTAMPTZ;
  v_refresh_after TIMESTAMPTZ;
BEGIN
  -- FROM SPEC: auth source is current Supabase session
  v_user_id := auth.uid();
  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'register_sync_hint_channel: not authenticated';
  END IF;

  -- Resolve company_id from user_profiles (server-resolved, not client-supplied)
  -- FROM SPEC: MUST scope fan-out by server-resolved company_id
  SELECT company_id INTO v_company_id
  FROM public.user_profiles
  WHERE id = v_user_id;

  IF v_company_id IS NULL THEN
    RAISE EXCEPTION 'register_sync_hint_channel: user has no company_id';
  END IF;

  -- Validate device_install_id
  IF p_device_install_id IS NULL OR length(trim(p_device_install_id)) < 1 THEN
    RAISE EXCEPTION 'register_sync_hint_channel: device_install_id required';
  END IF;

  -- WHY: Reject excessively long device_install_id to prevent abuse
  IF length(trim(p_device_install_id)) > 255 THEN
    RAISE EXCEPTION 'register_sync_hint_channel: device_install_id too long (max 255)';
  END IF;

  -- WHY: Limit active subscriptions per user to prevent resource exhaustion
  IF (SELECT count(*) FROM public.sync_hint_subscriptions
      WHERE user_id = v_user_id AND revoked_at IS NULL) >= 10 THEN
    RAISE EXCEPTION 'register_sync_hint_channel: too many active subscriptions (max 10)';
  END IF;

  -- FROM SPEC: Channel Naming (§3) — at least 128 bits of randomness
  -- WHY: encode(gen_random_bytes(20), 'hex') gives 160 bits, well above 128-bit minimum
  -- NOTE: Pre-generate channel_name; ON CONFLICT path reuses existing value
  -- DURATIONS: expires_at=7d, refresh_after=6h, cleanup_grace=1d
  -- (see also _minSyncInterval=30s in realtime_hint_handler.dart)
  v_channel_name := 'sync_hint:' || encode(gen_random_bytes(20), 'hex');
  v_expires_at := now() + interval '7 days';
  v_refresh_after := now() + interval '6 hours';

  -- WHY: INSERT ... ON CONFLICT eliminates TOCTOU race between SELECT and INSERT
  -- The partial unique index (user_id, device_install_id) WHERE revoked_at IS NULL
  -- ensures upsert only hits active subscriptions
  INSERT INTO public.sync_hint_subscriptions (
    user_id, company_id, device_install_id, channel_name,
    platform, app_version, expires_at
  ) VALUES (
    v_user_id, v_company_id, p_device_install_id, v_channel_name,
    p_platform, p_app_version, v_expires_at
  )
  ON CONFLICT (user_id, device_install_id) WHERE revoked_at IS NULL
  DO UPDATE SET
    company_id = EXCLUDED.company_id,
    platform = COALESCE(EXCLUDED.platform, sync_hint_subscriptions.platform),
    app_version = COALESCE(EXCLUDED.app_version, sync_hint_subscriptions.app_version),
    last_seen_at = now(),
    expires_at = EXCLUDED.expires_at,
    updated_at = now()
  RETURNING id, channel_name INTO v_sub_id, v_channel_name;

  RETURN jsonb_build_object(
    'subscription_id', v_sub_id::text,
    'channel_name', v_channel_name,
    'expires_at', v_expires_at::text,
    'refresh_after', v_refresh_after::text
  );
END;
$$;
```

#### Step 1.1.3: Create deactivate_sync_hint_channel() RPC

```sql
-- FROM SPEC: optionally call best-effort unregister/deactivate RPC
-- WHY: Clean up on sign-out so stale subscriptions don't accumulate
CREATE OR REPLACE FUNCTION public.deactivate_sync_hint_channel(
  p_device_install_id TEXT
)
RETURNS void
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public
AS $$
BEGIN
  -- WHY: Reject excessively long device_install_id to prevent abuse (matches register RPC)
  IF length(trim(p_device_install_id)) > 255 THEN
    RAISE EXCEPTION 'deactivate_sync_hint_channel: device_install_id too long (max 255)';
  END IF;

  UPDATE public.sync_hint_subscriptions
  SET revoked_at = now(), updated_at = now()
  WHERE user_id = auth.uid()
    AND device_install_id = p_device_install_id
    AND revoked_at IS NULL;
END;
$$;
```

#### Step 1.1.4: Create cleanup function for expired subscriptions

```sql
-- FROM SPEC: optional periodic cleanup job for expired subscriptions
-- WHY: Prevents unbounded table growth from abandoned devices
-- NOTE: Called by pg_cron or manually; not a trigger
CREATE OR REPLACE FUNCTION public.cleanup_expired_sync_hint_subscriptions()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_deleted integer;
BEGIN
  -- WHY: Preserve revoked rows for 1-day audit window before deletion
  DELETE FROM public.sync_hint_subscriptions
  WHERE expires_at < now() - interval '1 day'
     OR (revoked_at IS NOT NULL AND revoked_at < now() - interval '1 day');
  GET DIAGNOSTICS v_deleted = ROW_COUNT;
  RETURN v_deleted;
END;
$$;

-- WHY: SECURITY DEFINER function must not be callable by regular users — only pg_cron or admin
REVOKE EXECUTE ON FUNCTION public.cleanup_expired_sync_hint_subscriptions() FROM public, anon, authenticated;
```

#### Step 1.1.5: Create helper to resolve eligible active channels

```sql
-- FROM SPEC: Server Fan-Out Flow (§6) — resolve eligible active subscriptions
-- WHY: The edge function must not trust a stale company_id copied onto the
-- subscription row. Re-validate current company membership at fan-out time so
-- removed or moved users stop receiving metadata promptly.
CREATE OR REPLACE FUNCTION public.get_active_sync_hint_channels(
  p_company_id UUID
)
RETURNS TABLE(channel_name TEXT)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT shs.channel_name
  FROM public.sync_hint_subscriptions shs
  JOIN public.user_profiles up ON up.id = shs.user_id
  WHERE shs.company_id = p_company_id
    AND up.company_id = p_company_id
    AND shs.revoked_at IS NULL
    AND shs.expires_at > now();
$$;

-- WHY: Helper is for service-role / admin fan-out only, not direct client use.
REVOKE EXECUTE ON FUNCTION public.get_active_sync_hint_channels(UUID)
  FROM public, anon, authenticated;
```

> **NOTE:** Per-device Broadcast fan-out is delegated to the `daily-sync-push` edge function
> instead of a SQL helper that performs the actual broadcast. This keeps trigger write
> latency bounded and removes the SSRF vector from SQL triggers, while still letting
> the server resolve eligible channels through a hardened helper.

---

## Phase 2: Server-Side Fan-Out Migration

### Sub-phase 2.1: Update Trigger Functions for Per-Device Broadcast

**Files:**
- Create: `supabase/migrations/20260405100000_private_channel_fanout.sql`

**Agent**: backend-supabase-agent

#### Step 2.1.1: Replace broadcast_sync_hint_company() with per-device fan-out

```sql
-- FROM SPEC: replace tenant broadcast with per-device fan-out lookup
-- WHY: Eliminates predictable sync_hints:{company_id} channel
CREATE OR REPLACE FUNCTION public.broadcast_sync_hint_company()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row record;
  v_company_id uuid;
  v_payload jsonb;
  v_dedupe_key text;
BEGIN
  v_row := COALESCE(NEW, OLD);
  v_company_id := (v_row).company_id;

  IF v_company_id IS NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  v_dedupe_key := TG_TABLE_NAME || ':' || v_company_id::text;
  IF NOT pg_try_advisory_xact_lock(
    hashtext('sync_hint_company'),
    hashtext(v_dedupe_key)
  ) THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  v_payload := jsonb_build_object(
    'company_id', v_company_id::text,
    'project_id', NULL,
    'table_name', TG_TABLE_NAME,
    'scope_type', 'company_wide',
    'changed_at', now()::text
  );

  -- FROM SPEC: server broadcasts the payload to each active device channel
  -- NOTE: Broadcast fan-out delegated to edge function (see Phase 2.2).
  -- The edge function handles both FCM push AND per-device Broadcast fan-out,
  -- avoiding N blocking HTTP calls inside the trigger.
  PERFORM public.invoke_daily_sync_push(v_payload);

  RETURN COALESCE(NEW, OLD);
EXCEPTION
  WHEN OTHERS THEN
    RAISE WARNING 'broadcast_sync_hint_company failed: %', SQLERRM;
    RETURN COALESCE(NEW, OLD);
END;
$$;
```

#### Step 2.1.2: Replace broadcast_sync_hint_project() with per-device fan-out

```sql
-- WHY: Same per-device fan-out pattern, but resolves company_id from projects table
-- NOTE: Broadcast fan-out delegated to edge function (see Phase 2.2)
CREATE OR REPLACE FUNCTION public.broadcast_sync_hint_project()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row record;
  v_project_id uuid;
  v_company_id uuid;
  v_payload jsonb;
  v_dedupe_key text;
BEGIN
  v_row := COALESCE(NEW, OLD);
  v_project_id := (v_row).project_id;

  IF v_project_id IS NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  SELECT p.company_id INTO v_company_id
  FROM public.projects p
  WHERE p.id = v_project_id;

  IF v_company_id IS NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  v_dedupe_key := TG_TABLE_NAME || ':' || v_project_id::text;
  IF NOT pg_try_advisory_xact_lock(
    hashtext('sync_hint_project'),
    hashtext(v_dedupe_key)
  ) THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  v_payload := jsonb_build_object(
    'company_id', v_company_id::text,
    'project_id', v_project_id::text,
    'table_name', TG_TABLE_NAME,
    'scope_type', 'project_table',
    'changed_at', now()::text
  );

  -- NOTE: Single call — edge function handles both FCM push AND per-device Broadcast fan-out
  PERFORM public.invoke_daily_sync_push(v_payload);

  RETURN COALESCE(NEW, OLD);
EXCEPTION
  WHEN OTHERS THEN
    RAISE WARNING 'broadcast_sync_hint_project failed: %', SQLERRM;
    RETURN COALESCE(NEW, OLD);
END;
$$;
```

#### Step 2.1.3: Replace broadcast_sync_hint_contractor() with per-device fan-out

```sql
-- WHY: Same pattern, resolves company_id via contractors → projects chain
-- NOTE: Broadcast fan-out delegated to edge function (see Phase 2.2)
CREATE OR REPLACE FUNCTION public.broadcast_sync_hint_contractor()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row record;
  v_contractor_id uuid;
  v_project_id uuid;
  v_company_id uuid;
  v_payload jsonb;
  v_dedupe_key text;
BEGIN
  v_row := COALESCE(NEW, OLD);
  v_contractor_id := (v_row).contractor_id;

  IF v_contractor_id IS NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  SELECT c.project_id, p.company_id
  INTO v_project_id, v_company_id
  FROM public.contractors c
  JOIN public.projects p ON p.id = c.project_id
  WHERE c.id = v_contractor_id;

  IF v_project_id IS NULL OR v_company_id IS NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  v_dedupe_key := TG_TABLE_NAME || ':' || v_contractor_id::text;
  IF NOT pg_try_advisory_xact_lock(
    hashtext('sync_hint_contractor'),
    hashtext(v_dedupe_key)
  ) THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  v_payload := jsonb_build_object(
    'company_id', v_company_id::text,
    'project_id', v_project_id::text,
    'table_name', TG_TABLE_NAME,
    'scope_type', 'project_table',
    'changed_at', now()::text
  );

  -- NOTE: Single call — edge function handles both FCM push AND per-device Broadcast fan-out
  PERFORM public.invoke_daily_sync_push(v_payload);

  RETURN COALESCE(NEW, OLD);
EXCEPTION
  WHEN OTHERS THEN
    RAISE WARNING 'broadcast_sync_hint_contractor failed: %', SQLERRM;
    RETURN COALESCE(NEW, OLD);
END;
$$;
```

> **NOTE:** The 20 existing trigger bindings (sync_hint_projects, sync_hint_daily_entries, etc.) do NOT need to be re-created — they reference the function names which are replaced via `CREATE OR REPLACE`.

### Sub-phase 2.2: Update daily-sync-push Edge Function for Broadcast Fan-Out

**Files:**
- Modify: `supabase/functions/daily-sync-push/index.ts`

**Agent**: backend-supabase-agent

> **WHY:** Per F2, moving Broadcast fan-out from SQL triggers to the edge function
> eliminates N blocking HTTP calls per DML inside the trigger and removes the
> SSRF vector (F5). The trigger now makes 1 HTTP call to `invoke_daily_sync_push`.
> The edge function handles both FCM push AND per-device Broadcast fan-out.

#### Step 2.2.1: Add Broadcast fan-out logic to edge function

After existing FCM push logic, add per-device Broadcast fan-out:

```typescript
// FROM SPEC: Server Fan-Out Flow (§6) — server broadcasts to each active device channel
// WHY: Fan-out moved from SQL trigger to edge function to avoid N blocking HTTP
// calls inside a database trigger (unbounded write latency)
// NOTE: `supabase` is the existing admin client (index.ts:65).
//       `hintParams` is the existing parsed payload (index.ts:67).
//       Guard with optional chaining since hintParams is undefined for scheduled invocations.
if (hintParams?.company_id) {
  // FROM SPEC: resolve eligible active subscriptions for the affected company.
  // DO NOT trust sync_hint_subscriptions.company_id alone. The helper must
  // re-check current user_profiles.company_id so stale rows stop receiving hints
  // after membership changes.
  const { data: subscriptions, error: subError } = await supabase.rpc(
    'get_active_sync_hint_channels',
    { p_company_id: hintParams.company_id },
  );

  if (subError) {
    console.error('Failed to query sync_hint_subscriptions:', subError.message);
  } else if (subscriptions && subscriptions.length > 0) {
    // WHY: Use REST API fetch + Promise.allSettled for parallel fan-out.
    // Existing SQL triggers already use REST broadcast (POST /api/broadcast).
    // channel().send() would create N WebSocket round-trips — REST is fire-and-forget.
    const realtimeUrl = Deno.env.get("SUPABASE_URL")!;
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const dataPayload = {
      company_id: hintParams.company_id,
      project_id: hintParams.project_id ?? null,
      table_name: hintParams.table_name,
      scope_type: hintParams.scope_type,
      changed_at: hintParams.changed_at,
    };

    const broadcastPromises = subscriptions.map((sub) =>
      fetch(`${realtimeUrl}/realtime/v1/api/broadcast`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'apikey': serviceRoleKey,
          'Authorization': `Bearer ${serviceRoleKey}`,
        },
        body: JSON.stringify({
          channel: sub.channel_name,
          event: 'sync_hint',
          payload: dataPayload,
        }),
      })
    );

    // NOTE: Promise.allSettled ensures one failure doesn't block others (best-effort)
    const results = await Promise.allSettled(broadcastPromises);
    const failed = results.filter((r) => r.status === 'rejected').length;
    if (failed > 0) {
      console.error(`Broadcast fan-out: ${failed}/${subscriptions.length} failed`);
    }
    console.log(`Broadcast fan-out: sent to ${subscriptions.length} device(s)`);
  } else {
    console.log('Broadcast fan-out: no active subscriptions for company');
  }
}
```

#### Step 2.2.2: Handle zero-subscription edge case

Ensure the edge function completes normally when `subscriptions` is empty (no active
devices for the company). The code above handles this via the `else` branch — log and
continue. FCM push still fires independently.

---

## Phase 3: Client Data Layer — Device Identity

### Sub-phase 3.1: Add device_install_id to PreferencesService

**Files:**
- Modify: `lib/shared/services/preferences_service.dart`

**Agent**: backend-data-layer-agent

#### Step 3.1.1: Add device_install_id key constant and getter

Add after existing key constants (after line ~21):

```dart
// FROM SPEC: Each authenticated app installation maintains a local device_install_id
// WHY: Stable per-install identifier sent to registration RPC
// NOTE: SharedPreferences is acceptable here — device_install_id is a non-sensitive
// UUID. An attacker who reads it still needs valid auth credentials to register.
// flutter_secure_storage is a defense-in-depth option for future hardening.
static const String keyDeviceInstallId = 'device_install_id';
```

Add a sync getter method (after existing typed getters):

```dart
/// Returns the persistent device installation ID, or null if not yet ensured.
///
/// WHY: The server uses this to identify which device a subscription belongs to.
/// Generated locally via UUIDv4, persisted in SharedPreferences.
/// A reinstall generates a new ID — the server issues a fresh channel on re-registration.
///
/// NOTE: This getter never writes. Call ensureDeviceInstallId() during initialize()
/// to guarantee the value is persisted before first read.
String? get deviceInstallId {
  _ensureInitialized();
  return _prefs!.getString(keyDeviceInstallId);
}
```

#### Step 3.1.2: Add ensureDeviceInstallId() async method

Add after the getter:

```dart
/// Generates and persists a device_install_id if one does not already exist.
///
/// WHY: Separating the async write from the sync getter avoids fire-and-forget
/// SharedPreferences.setString() calls that could lose writes. This must be
/// called during PreferencesService.initialize() so the getter always returns
/// a non-null value after initialization completes.
Future<void> ensureDeviceInstallId() async {
  _ensureInitialized();
  final existing = _prefs!.getString(keyDeviceInstallId);
  if (existing == null || existing.isEmpty) {
    final id = const Uuid().v4();
    await _prefs!.setString(keyDeviceInstallId, id);
  }
}
```

#### Step 3.1.3: Call ensureDeviceInstallId() from initialize()

In the existing `initialize()` method, add after `_prefs = await SharedPreferences.getInstance();`:

```dart
await ensureDeviceInstallId();
```

#### Step 3.1.4: Add uuid import

Add at the top of the file:

```dart
import 'package:uuid/uuid.dart';
```

> **NOTE:** The `uuid` package is already a dependency in `pubspec.yaml` (used by models for ID generation).

#### Step 3.1.5: Verify with flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

---

## Phase 4: Client Application — RealtimeHintHandler Refactor

### Sub-phase 4.1: Add Registration State and Methods

**Files:**
- Modify: `lib/features/sync/application/realtime_hint_handler.dart`

**Agent**: backend-supabase-agent

#### Step 4.1.1: Add registration state fields

Add new fields to the class (after existing `_queuedQuickSync` field at ~line 39):

```dart
// FROM SPEC: Registration Model (§2)
String? _deviceInstallId;
String? _appVersion;
String? _subscriptionId;
String? _currentChannelName;
DateTime? _refreshAfter;
Timer? _refreshTimer;
```

#### Step 4.1.2: Update constructor to accept deviceInstallId and appVersion

Replace the existing constructor:

```dart
RealtimeHintHandler({
  required SupabaseClient supabaseClient,
  required SyncOrchestrator syncOrchestrator,
  String? companyId,
  String? deviceInstallId,
  String? appVersion,
}) : _supabaseClient = supabaseClient,
     _syncOrchestrator = syncOrchestrator,
     _companyId = companyId,
     _deviceInstallId = deviceInstallId,
     _appVersion = appVersion;
```

#### Step 4.1.3: Replace subscribe() with registerAndSubscribe()

Replace the existing `subscribe(String companyId)` method entirely:

```dart
/// Call the registration RPC and parse the response.
///
/// WHY (DRY): Both registerAndSubscribe() and _refreshRegistration() need to
/// call the same RPC and parse the same response shape. Extracting this avoids
/// duplicating the RPC call + response parsing logic.
/// Returns null if the RPC fails or returns null.
Future<Map<String, dynamic>?> _callRegistrationRpc() async {
  final response = await _supabaseClient.rpc(
    'register_sync_hint_channel',
    params: {
      'p_device_install_id': _deviceInstallId!,
      'p_platform': _resolvePlatform(),
      'p_app_version': _appVersion,
    },
  );

  if (response == null) return null;

  return response is Map<String, dynamic>
      ? response
      : Map<String, dynamic>.from(response as Map);
}

/// Register with the server and subscribe to the returned opaque channel.
///
/// FROM SPEC: Client Foreground Flow (§5) — register or refresh, then subscribe
/// WHY: Channel names are server-issued opaque tokens, not derived from company_id
Future<void> registerAndSubscribe(String companyId) async {
  if (_isSubscribed) {
    Logger.sync('RealtimeHintHandler: already subscribed');
    return;
  }
  if (_companyId != null && _companyId != companyId) {
    Logger.sync(
      'RealtimeHintHandler: refusing to subscribe due to company mismatch',
    );
    return;
  }
  if (_deviceInstallId == null || _deviceInstallId!.isEmpty) {
    Logger.sync('RealtimeHintHandler: no device_install_id, skipping');
    return;
  }

  try {
    // FROM SPEC: client calls registration RPC with device_install_id
    final result = await _callRegistrationRpc();

    if (result == null) {
      Logger.sync('RealtimeHintHandler: registration returned null');
      return;
    }

    final channelName = result['channel_name'] as String?;
    _subscriptionId = result['subscription_id'] as String?;
    final refreshAfterStr = result['refresh_after'] as String?;

    if (channelName == null || channelName.isEmpty) {
      Logger.sync('RealtimeHintHandler: registration returned no channel_name');
      return;
    }

    _currentChannelName = channelName;

    // Parse refresh_after for periodic re-registration
    if (refreshAfterStr != null) {
      _refreshAfter = DateTime.tryParse(refreshAfterStr);
      _scheduleRefresh();
    }

    // FROM SPEC: client subscribes only to the returned opaque channel
    _channel = _supabaseClient
        .channel(channelName)
        .onBroadcast(event: 'sync_hint', callback: _handleHint);

    _channel!.subscribe((status, error) {
      if (status == RealtimeSubscribeStatus.subscribed) {
        _isSubscribed = true;
        Logger.sync(
          'RealtimeHintHandler: subscribed to private channel '
          '(sub=${_subscriptionId ?? "?"})',
        );
      } else if (status == RealtimeSubscribeStatus.closed) {
        _isSubscribed = false;
        Logger.sync('RealtimeHintHandler: channel closed');
      } else if (error != null) {
        Logger.sync('RealtimeHintHandler: subscription error: $error');
      }
    });
  } catch (e) {
    Logger.sync('RealtimeHintHandler: registration failed: $e');
  }
}

/// Resolve platform string for registration metadata.
static String _resolvePlatform() {
  if (kIsWeb) return 'web';
  if (Platform.isAndroid) return 'android';
  if (Platform.isIOS) return 'ios';
  if (Platform.isWindows) return 'windows';
  if (Platform.isMacOS) return 'macos';
  if (Platform.isLinux) return 'linux';
  return 'unknown';
}
```

#### Step 4.1.4: Add refresh timer logic

```dart
/// Schedule a channel re-registration before expiry.
///
/// FROM SPEC: refresh channel registration on startup and periodically while foregrounded
/// NOTE: device clock skew may cause refresh to fire early or late. 7-day TTL
/// and startup re-registration provide fallback.
void _scheduleRefresh() {
  _refreshTimer?.cancel();
  if (_refreshAfter == null || _companyId == null) return;

  final delay = _refreshAfter!.difference(DateTime.now());
  if (delay.isNegative || delay == Duration.zero) return;

  _refreshTimer = Timer(delay, () {
    if (_companyId != null && _deviceInstallId != null) {
      Logger.sync('RealtimeHintHandler: refreshing registration');
      // WHY: Call _refreshRegistration(), NOT registerAndSubscribe(),
      // because registerAndSubscribe() has an `if (_isSubscribed) return;` guard
      // that would make this timer a no-op while already subscribed.
      unawaited(_refreshRegistration());
    }
  });
}

/// Refresh the server-side registration (last_seen_at / expires_at)
/// WITHOUT re-subscribing to the Broadcast channel.
///
/// WHY: The Broadcast channel subscription is already active. We only need to
/// tell the server we're still alive so it extends our expiry window.
/// This avoids the _isSubscribed guard in registerAndSubscribe().
/// Uses _callRegistrationRpc() to avoid duplicating the RPC call + parsing (DRY).
Future<void> _refreshRegistration() async {
  if (_deviceInstallId == null || _deviceInstallId!.isEmpty) return;

  try {
    final result = await _callRegistrationRpc();

    if (result != null) {
      final refreshAfterStr = result['refresh_after'] as String?;
      if (refreshAfterStr != null) {
        _refreshAfter = DateTime.tryParse(refreshAfterStr);
        _scheduleRefresh();
      }

      // WHY (L3): If the server returned a different channel_name (e.g., after
      // revocation/re-creation), re-subscribe to the new channel.
      final newChannelName = result['channel_name'] as String?;
      if (newChannelName != null && newChannelName != _currentChannelName) {
        Logger.sync(
          'RealtimeHintHandler: channel_name changed during refresh '
          '(was $_currentChannelName, now $newChannelName) — re-subscribing',
        );
        _isSubscribed = false;
        if (_channel != null) {
          await _supabaseClient.removeChannel(_channel!);
          _channel = null;
        }
        if (_companyId != null) {
          await registerAndSubscribe(_companyId!);
        }
        return;
      }

      Logger.sync('RealtimeHintHandler: registration refreshed');
    }
  } catch (e) {
    Logger.sync('RealtimeHintHandler: refresh registration failed: $e');
  }
}
```

#### Step 4.1.5: Update rebind() to use registerAndSubscribe

Replace the existing `rebind` method:

```dart
/// Rebind to a new company context.
///
/// FROM SPEC: If the app changes company context — unsubscribe, clear, re-register
Future<void> rebind(String? companyId) {
  return _enqueueTransition(() async {
    if (_companyId == companyId) {
      if (companyId != null && !_isSubscribed) {
        await registerAndSubscribe(companyId);
      }
      return;
    }

    final previousCompanyId = _companyId;
    if (_channel != null) {
      await _disposeNow();
    }

    _companyId = companyId;
    if (companyId == null) {
      Logger.sync(
        'RealtimeHintHandler: cleared company binding '
        '(was ${previousCompanyId ?? "none"})',
      );
      return;
    }

    Logger.sync(
      'RealtimeHintHandler: rebinding from '
      '${previousCompanyId ?? "none"} to $companyId',
    );
    await registerAndSubscribe(companyId);
  });
}
```

#### Step 4.1.6: Update dispose to deactivate server subscription and cancel refresh timer

Replace the existing `_disposeNow` method:

```dart
Future<void> _disposeNow() async {
  _refreshTimer?.cancel();
  _refreshTimer = null;
  _refreshAfter = null;

  final channel = _channel;
  if (channel == null) return;
  await _supabaseClient.removeChannel(channel);
  _channel = null;
  _isSubscribed = false;

  // FROM SPEC: optionally call best-effort unregister/deactivate RPC
  // NOTE (F10): On sign-out, the auth session may already be invalidated before
  // dispose runs. Since deactivate_sync_hint_channel is SECURITY INVOKER, it
  // requires a valid session. This call is best-effort — if it fails (e.g.,
  // session already revoked), server-side expiry (7-day TTL) handles cleanup.
  if (_deviceInstallId != null) {
    try {
      await _supabaseClient.rpc(
        'deactivate_sync_hint_channel',
        params: {'p_device_install_id': _deviceInstallId!},
      );
    } catch (e) {
      // NOTE: Best-effort — don't fail dispose on deactivation error.
      // Common on sign-out when session is already invalidated.
      Logger.sync(
        'RealtimeHintHandler: deactivate RPC failed (best-effort): $e',
      );
    }
  }

  _subscriptionId = null;
  _currentChannelName = null;
  Logger.sync('RealtimeHintHandler: disposed');
}
```

#### Step 4.1.7: Add dart:io import for Platform

Add at the top of the file if not already present:

```dart
import 'dart:io';
```

#### Step 4.1.8: Verify with flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

---

## Phase 5: Sync Initialization Wiring

### Sub-phase 5.1: Wire device_install_id into SyncInitializer

**Files:**
- Modify: `lib/features/sync/application/sync_initializer.dart`

**Agent**: backend-supabase-agent

#### Step 5.1.1: Add PreferencesService parameter to SyncInitializer.create()

Update the `create()` method signature to accept `PreferencesService`:

Add parameter:
```dart
PreferencesService? preferencesService,
```

#### Step 5.1.2: Update RealtimeHintHandler creation to pass deviceInstallId

Replace the realtime handler wiring block (L129-142):

```dart
RealtimeHintHandler? realtimeHintHandler;
if (supabaseClient != null) {
  // FROM SPEC: persist a local device_install_id
  final deviceInstallId = preferencesService?.deviceInstallId;

  realtimeHintHandler = RealtimeHintHandler(
    supabaseClient: supabaseClient,
    syncOrchestrator: syncOrchestrator,
    companyId: authProvider.userProfile?.companyId,
    deviceInstallId: deviceInstallId,
    appVersion: appConfigProvider.appVersion,
  );
  final companyId = authProvider.userProfile?.companyId;
  if (companyId != null) {
    // NOTE: registerAndSubscribe is async; fire-and-forget like FCM init
    unawaited(() async {
      try {
        await realtimeHintHandler!.registerAndSubscribe(companyId);
      } catch (e) {
        Logger.sync('SyncInitializer: hint channel registration failed: $e');
      }
    }());
  }
}
```

#### Step 5.1.3: Add PreferencesService import

Add to imports:
```dart
import 'package:construction_inspector/shared/services/preferences_service.dart';
```

### Sub-phase 5.2: Update SyncProviders to Pass PreferencesService

**Files:**
- Modify: `lib/features/sync/di/sync_providers.dart`

**Agent**: backend-supabase-agent

#### Step 5.2.1: Add PreferencesService parameter to SyncProviders.initialize()

Update the `initialize()` method signature:

Add parameter:
```dart
PreferencesService? preferencesService,
```

Pass it through to `SyncInitializer.create()`:
```dart
return SyncInitializer.create(
  dbService: dbService,
  authProvider: authProvider,
  appConfigProvider: appConfigProvider,
  companyLocalDs: companyLocalDs,
  authService: authService,
  supabaseClient: supabaseClient,
  preferencesService: preferencesService,
);
```

#### Step 5.2.2: Add PreferencesService import

```dart
import 'package:construction_inspector/shared/services/preferences_service.dart';
```

### Sub-phase 5.3: Update AppInitializer to Pass PreferencesService

**Files:**
- Modify: `lib/core/bootstrap/app_initializer.dart`

**Agent**: backend-supabase-agent

#### Step 5.3.1: Pass preferencesService through to SyncProviders.initialize()

Find the call to `SyncProviders.initialize()` in `app_initializer.dart` and add the parameter:

```dart
preferencesService: coreServices.preferencesService,
```

#### Step 5.3.2: Update auth listener — rebind uses registerAndSubscribe

In the auth listener block (L229-249), the `rebind()` call already delegates to `registerAndSubscribe` via the updated `rebind()` method, so no change needed to the company-change call site.

However, **verify and preserve the unauthenticated / auth-loss branch** so it still:

- awaits `RealtimeHintHandler.dispose()`
- clears the local subscription binding
- best-effort calls `deactivate_sync_hint_channel()` through `dispose()`

If any of those are implicit today, make them explicit while touching this wiring. The
spec intent is not just company rebinding; sign-out and auth loss must also tear down the
private channel promptly.

However, when creating a new handler on sign-in, pass `deviceInstallId` and `appVersion`:

Replace:
```dart
activeRealtimeHintHandler ??= RealtimeHintHandler(
  supabaseClient: supabaseClient,
  syncOrchestrator: syncResult.orchestrator,
  companyId: activeRealtimeCompanyId,
);
```

With:
```dart
activeRealtimeHintHandler ??= RealtimeHintHandler(
  supabaseClient: supabaseClient,
  syncOrchestrator: syncResult.orchestrator,
  companyId: activeRealtimeCompanyId,
  deviceInstallId: coreServices.preferencesService.deviceInstallId,
  appVersion: authDeps.appConfigProvider.appVersion,
);
```

#### Step 5.3.3: Verify with flutter analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No issues

---

## Phase 6: Tests

### Sub-phase 6.1: Update Existing RealtimeHintHandler Tests

**Files:**
- Modify: `test/features/sync/application/realtime_hint_handler_test.dart`

**Agent**: qa-testing-agent

#### Step 6.1.1: Add shared test helper for RPC mock setup

Add a shared helper in the test setUp that mocks both RPCs and returns predictable values.
This ensures all tests use consistent channel names for matcher assertions.

```dart
// WHY: Shared helper avoids duplicating RPC mock setup across every test
// and ensures channel name matchers use a predictable 'sync_hint:test_opaque_token'
const kTestChannelName = 'sync_hint:test_opaque_token';
const kTestSubscriptionId = 'test-sub-id';

/// Sets up mock RPC responses for registration and deactivation.
/// Call in setUp() so all tests share the same mock baseline.
void setupSyncHintRpcMocks(MockSupabaseClient mockSupabase) {
  when(() => mockSupabase.rpc(
    'register_sync_hint_channel',
    params: any(named: 'params'),
  )).thenAnswer((_) async => {
    'subscription_id': kTestSubscriptionId,
    'channel_name': kTestChannelName,
    'expires_at': DateTime.now().add(const Duration(days: 7)).toIso8601String(),
    'refresh_after': DateTime.now().add(const Duration(hours: 6)).toIso8601String(),
  });

  when(() => mockSupabase.rpc(
    'deactivate_sync_hint_channel',
    params: any(named: 'params'),
  )).thenAnswer((_) async => null);
}

class MockSupabaseClient extends Mock implements SupabaseClient {
  // NOTE: rpc() mock configured via setupSyncHintRpcMocks() in setUp
}
```

#### Step 6.1.2: Update subscribe tests to use registerAndSubscribe

Replace all `handler.subscribe(companyId)` calls with:
```dart
await handler.registerAndSubscribe(companyId);
```

Call `setupSyncHintRpcMocks(mockSupabase)` in the test group's `setUp()`.
Update channel name matchers to use `kTestChannelName` instead of `sync_hints:$companyId`.

> **NOTE:** Existing test callbacks that call `registerAndSubscribe()` must be changed
> from `() {` to `() async {` since `registerAndSubscribe()` is async and must be awaited.

#### Step 6.1.3: Add test — registration failure falls back gracefully

```dart
test('registerAndSubscribe logs and returns on RPC failure', () async {
  when(() => mockSupabase.rpc(
    'register_sync_hint_channel',
    params: any(named: 'params'),
  )).thenThrow(Exception('Network error'));

  final handler = RealtimeHintHandler(
    supabaseClient: mockSupabase,
    syncOrchestrator: orchestrator,
    companyId: 'company-1',
    deviceInstallId: 'device-1',
  );

  // WHY: Should not throw — registration failure is non-fatal
  await handler.registerAndSubscribe('company-1');
  // Handler should not be subscribed
  // Verify no channel was created
});
```

#### Step 6.1.4: Add test — dispose calls deactivate RPC

```dart
test('dispose calls deactivate_sync_hint_channel RPC', () async {
  // Setup: register successfully
  when(() => mockSupabase.rpc(
    'register_sync_hint_channel',
    params: any(named: 'params'),
  )).thenAnswer((_) async => {
    'subscription_id': 'sub-1',
    'channel_name': 'sync_hint:opaque123',
    'expires_at': DateTime.now().add(const Duration(days: 7)).toIso8601String(),
    'refresh_after': DateTime.now().add(const Duration(hours: 6)).toIso8601String(),
  });
  when(() => mockSupabase.rpc(
    'deactivate_sync_hint_channel',
    params: any(named: 'params'),
  )).thenAnswer((_) async => null);

  final handler = RealtimeHintHandler(
    supabaseClient: mockSupabase,
    syncOrchestrator: orchestrator,
    companyId: 'company-1',
    deviceInstallId: 'device-1',
  );

  await handler.registerAndSubscribe('company-1');
  await handler.dispose();

  verify(() => mockSupabase.rpc(
    'deactivate_sync_hint_channel',
    params: {'p_device_install_id': 'device-1'},
  )).called(1);
});
```

#### Step 6.1.5: Add test — rebind re-registers with new company

```dart
test('rebind deactivates old channel and registers new one', () async {
  var callCount = 0;
  when(() => mockSupabase.rpc(
    'register_sync_hint_channel',
    params: any(named: 'params'),
  )).thenAnswer((_) async {
    callCount++;
    return {
      'subscription_id': 'sub-$callCount',
      'channel_name': 'sync_hint:opaque_$callCount',
      'expires_at': DateTime.now().add(const Duration(days: 7)).toIso8601String(),
      'refresh_after': DateTime.now().add(const Duration(hours: 6)).toIso8601String(),
    };
  });
  when(() => mockSupabase.rpc(
    'deactivate_sync_hint_channel',
    params: any(named: 'params'),
  )).thenAnswer((_) async => null);

  final handler = RealtimeHintHandler(
    supabaseClient: mockSupabase,
    syncOrchestrator: orchestrator,
    companyId: 'company-1',
    deviceInstallId: 'device-1',
  );

  await handler.registerAndSubscribe('company-1');
  await handler.rebind('company-2');

  // WHY: Should have registered twice (once per company)
  verify(() => mockSupabase.rpc(
    'register_sync_hint_channel',
    params: any(named: 'params'),
  )).called(2);
});
```

#### Step 6.1.6: Add test — no device_install_id skips registration

```dart
test('registerAndSubscribe skips when no deviceInstallId', () async {
  final handler = RealtimeHintHandler(
    supabaseClient: mockSupabase,
    syncOrchestrator: orchestrator,
    companyId: 'company-1',
    // NOTE: no deviceInstallId
  );

  await handler.registerAndSubscribe('company-1');

  // WHY: Should not call RPC without device identity
  verifyNever(() => mockSupabase.rpc(
    'register_sync_hint_channel',
    params: any(named: 'params'),
  ));
});
```

#### Step 6.1.7: Add test — refresh timer calls _refreshRegistration, not registerAndSubscribe

```dart
test('refresh timer calls RPC to refresh registration without re-subscribing', () async {
  // WHY: Verifies F1 fix — refresh timer must NOT call registerAndSubscribe()
  // (which would exit early due to _isSubscribed guard). Instead it calls
  // _refreshRegistration() which only refreshes last_seen_at/expires_at.
  // Setup: register, verify subscribed, then trigger refresh
  // Assert: RPC called again (refresh) but channel subscription unchanged
});
```

#### Step 6.1.8: Add executable server-side verification for cleanup and fan-out

> **NOTE:** The spec explicitly requires tests for stale cleanup and trigger fan-out.
> Do not downgrade these to comments or manual-only instructions.

Add executable verification in repo-owned tests. Acceptable options:

- extend `test/features/sync/application/server_hint_plumbing_test.dart` with source-contract assertions for:
  - `get_active_sync_hint_channels`
  - `cleanup_expired_sync_hint_subscriptions`
  - `daily-sync-push` calling the helper instead of raw company-only lookup
- and/or add Supabase SQL / Deno integration tests if the repo already has a harness

Minimum assertions to land in this plan:

```dart
// cleanup_expired_sync_hint_subscriptions()
// - deletes expired rows older than the 1-day grace window
// - deletes revoked rows older than the 1-day grace window
// - preserves recently expired / recently revoked rows inside the grace window

// daily-sync-push fan-out
// - resolves recipients through get_active_sync_hint_channels()
// - no active channels => Broadcast skipped, FCM path still allowed
// - one Broadcast failure does not abort remaining fan-out
```

#### Step 6.1.9: Add auth-loss teardown guardrail test

Add or extend `test/core/di/app_initializer_test.dart` to assert the auth listener still
tears down the private hint channel on sign-out / auth loss:

```dart
test('auth loss disposes realtime hint handler and clears private channel binding', () {
  final content = File(
    'lib/core/bootstrap/app_initializer.dart',
  ).readAsStringSync();

  expect(content, contains('await handlerToDispose.dispose()'));
  expect(content, contains('activeRealtimeHintHandler = null'));
});
```

---

## Phase 7: Documentation Updates

### Sub-phase 7.1: Update Sync Documentation

**Files:**
- Modify: `.claude/specs/2026-04-03-sync-strategy-codex-spec.md`
- Modify: `.claude/docs/features/feature-sync-overview.md`
- Modify: `.claude/docs/features/feature-sync-architecture.md`
- Modify: `.claude/architecture-decisions/sync-constraints.md`
- Modify: `.claude/prds/sync-prd.md`

**Agent**: general-purpose

#### Step 7.1.1: Update sync-strategy-codex-spec.md

> **FROM SPEC:** Documentation Changes Required (line 208) — this spec must describe
> private sync-hint channels instead of predictable tenant channels.

Find references to `sync_hints:{company_id}` or predictable tenant channels and update to
describe the private per-device channel model. Note that Broadcast fan-out is now handled
by the `daily-sync-push` edge function, not by SQL trigger helpers.

#### Step 7.1.2: Update feature-sync-overview.md

Find references to `sync_hints:{company_id}` or predictable tenant channels and replace with description of private per-device channels:

- Channel names are opaque, server-issued tokens
- Client registers via `register_sync_hint_channel()` RPC
- Server fans out to per-device channels via `sync_hint_subscriptions` table

#### Step 7.1.3: Update feature-sync-architecture.md

Update the Broadcast section to describe:
- `sync_hint_subscriptions` table
- `register_sync_hint_channel()` and `deactivate_sync_hint_channel()` RPCs
- Per-device Broadcast fan-out via `daily-sync-push` edge function (not SQL trigger helpers)
- Triggers now make a single call to `invoke_daily_sync_push()`

#### Step 7.1.4: Update sync-constraints.md

Add constraint:
- Broadcast channel names MUST be opaque, server-issued tokens
- Channel registration MUST go through auth-protected RPC
- Fan-out MUST be scoped by server-resolved company_id

#### Step 7.1.5: Update sync-prd.md

Replace any references to predictable `sync_hints:{company_id}` channels with the private channel model.

#### Step 7.1.6: Verify documentation files exist

Run: `pwsh -Command "flutter analyze"`
Expected: No issues (docs don't affect Dart analysis, but ensures no regressions)

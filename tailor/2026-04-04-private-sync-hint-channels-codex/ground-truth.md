# Ground Truth

All literals verified against the codebase as of 2026-04-04.

## Channel Names & Events

| Literal | Source File | Line | Status |
|---------|------------|------|--------|
| `'sync_hints:$companyId'` | `lib/features/sync/application/realtime_hint_handler.dart` | 113 | VERIFIED — current predictable channel name to be replaced |
| `'sync_hints:' \|\| v_company_id::text` | `supabase/migrations/20260404000000_sync_hint_broadcast_trigger.sql` | 79, 154, 232 | VERIFIED — SQL trigger channel name to be replaced |
| `'sync_hint'` (event name) | `realtime_hint_handler.dart:114` | 114 | VERIFIED — Broadcast event name (stays) |
| `'sync_hint'` (payload type) | `daily-sync-push/index.ts:31` | 31 | VERIFIED |
| `'daily_sync'` (payload type) | `daily-sync-push/index.ts:27` | 27 | VERIFIED |

## Database Tables

| Table | Source | Status |
|-------|--------|--------|
| `user_fcm_tokens` | `supabase/migrations/20260222200000_add_fcm_tokens.sql` | VERIFIED — schema: user_id UUID PK, token TEXT, updated_at TIMESTAMPTZ |
| `user_profiles` | `supabase/migrations/20260222100000_multi_tenant_foundation.sql` | VERIFIED — has company_id column |
| `sync_hint_subscriptions` | (does not exist yet) | NEW — to be created |

## SQL Functions (Triggers)

| Function | Source File | Line | Status |
|----------|------------|------|--------|
| `broadcast_sync_hint_company()` | `20260404000000_sync_hint_broadcast_trigger.sql` | 40 | VERIFIED — SECURITY DEFINER, uses `sync_hints:{company_id}` |
| `broadcast_sync_hint_project()` | `20260404000000_sync_hint_broadcast_trigger.sql` | 106 | VERIFIED — resolves company_id via projects table |
| `broadcast_sync_hint_contractor()` | `20260404000000_sync_hint_broadcast_trigger.sql` | 181 | VERIFIED — resolves via contractors→projects→company_id |
| `invoke_daily_sync_push()` | `20260404000000_sync_hint_broadcast_trigger.sql` | 3 | VERIFIED — calls edge function for FCM |

## Trigger Bindings (20 triggers total)

| Trigger | Table | Function |
|---------|-------|----------|
| `sync_hint_projects` | `projects` | `broadcast_sync_hint_company()` |
| `sync_hint_project_assignments` | `project_assignments` | `broadcast_sync_hint_company()` |
| `sync_hint_daily_entries` | `daily_entries` | `broadcast_sync_hint_project()` |
| `sync_hint_locations` | `locations` | `broadcast_sync_hint_project()` |
| `sync_hint_contractors` | `contractors` | `broadcast_sync_hint_project()` |
| `sync_hint_equipment` | `equipment` | `broadcast_sync_hint_contractor()` |
| `sync_hint_bid_items` | `bid_items` | `broadcast_sync_hint_project()` |
| `sync_hint_personnel_types` | `personnel_types` | `broadcast_sync_hint_project()` |
| `sync_hint_entry_quantities` | `entry_quantities` | `broadcast_sync_hint_project()` |
| `sync_hint_entry_equipment` | `entry_equipment` | `broadcast_sync_hint_project()` |
| `sync_hint_entry_contractors` | `entry_contractors` | `broadcast_sync_hint_project()` |
| `sync_hint_entry_personnel_counts` | `entry_personnel_counts` | `broadcast_sync_hint_project()` |
| `sync_hint_photos` | `photos` | `broadcast_sync_hint_project()` |
| `sync_hint_inspector_forms` | `inspector_forms` | `broadcast_sync_hint_project()` |
| `sync_hint_form_responses` | `form_responses` | `broadcast_sync_hint_project()` |
| `sync_hint_form_exports` | `form_exports` | `broadcast_sync_hint_project()` |
| `sync_hint_entry_exports` | `entry_exports` | `broadcast_sync_hint_project()` |
| `sync_hint_documents` | `documents` | `broadcast_sync_hint_project()` |
| `sync_hint_todo_items` | `todo_items` | `broadcast_sync_hint_project()` |
| `sync_hint_calculation_history` | `calculation_history` | `broadcast_sync_hint_project()` |

## Client Symbols

| Symbol | File | Line | Status |
|--------|------|------|--------|
| `RealtimeHintHandler` (class) | `realtime_hint_handler.dart` | 28 | VERIFIED |
| `HintPayload` (class) | `realtime_hint_handler.dart` | 10 | VERIFIED |
| `subscribe(String companyId)` | `realtime_hint_handler.dart` | 96 | VERIFIED — to be replaced |
| `rebind(String? companyId)` | `realtime_hint_handler.dart` | 165 | VERIFIED — needs update |
| `dispose()` | `realtime_hint_handler.dart` | 190 | VERIFIED |
| `_handleHint(Map<String, dynamic> payload)` | `realtime_hint_handler.dart` | 126 | VERIFIED — stays |
| `parseHintPayload(Map<String, dynamic>)` | `realtime_hint_handler.dart` | 49 | VERIFIED — used by FcmHandler too |
| `dirtyScopeFromHint(HintPayload)` | `realtime_hint_handler.dart` | 59 | VERIFIED — used by FcmHandler too |
| `SyncInitializer.create()` | `sync_initializer.dart` | 42 | VERIFIED |
| `SyncProviders.initialize()` | `sync_providers.dart` | 28 | VERIFIED — delegates to SyncInitializer |
| `DirtyScopeTracker` | `dirty_scope_tracker.dart` | 7 | VERIFIED |
| `PreferencesService` | `shared/services/preferences_service.dart` | 11 | VERIFIED |

## SharedPreferences Keys

| Key | Source File | Line | Status |
|-----|------------|------|--------|
| `'fcm_background_hint_pending'` | `sync_lifecycle_manager.dart` | 60, 73, 74 | VERIFIED |
| `'fcm_background_hint_payloads'` | `sync_lifecycle_manager.dart` | 62, 75 | VERIFIED |
| `device_install_id` | (does not exist yet) | — | NEW — to be created |

## Edge Function

| Item | Value | Status |
|------|-------|--------|
| Function name | `daily-sync-push` | VERIFIED |
| Path | `supabase/functions/daily-sync-push/index.ts` | VERIFIED |
| Auth | `Bearer {SUPABASE_SERVICE_ROLE_KEY}` or `apikey` header | VERIFIED |
| FCM token source | `user_fcm_tokens` table | VERIFIED |
| Company scoping | Queries `user_profiles` by `company_id` → gets `user_id`s → queries `user_fcm_tokens` | VERIFIED |

## Supabase Settings Used in Triggers

| Setting | Used In | Status |
|---------|---------|--------|
| `supabase.realtime_url` | All 3 broadcast functions | VERIFIED |
| `supabase.service_role_key` | All 3 broadcast functions + `invoke_daily_sync_push` | VERIFIED |
| `supabase.functions_url` | `invoke_daily_sync_push` | VERIFIED |
| `supabase.url` | `invoke_daily_sync_push` (fallback) | VERIFIED |

## Lint Rules for New Files

| New File Path | Active Rules | Key Constraints |
|--------------|-------------|-----------------|
| `lib/features/sync/application/*` (new service) | A1, A2, A9, Global rules | No raw Supabase.instance.client, no raw DatabaseService(), log all catches |
| `lib/features/sync/data/datasources/*` (if needed) | A1, A2, A9, Global rules | Same global rules |
| `supabase/migrations/*` | (no Dart lint rules) | SQL only |
| `test/features/sync/application/*` | T2, T3, T4, T5 | Test rules; D3/D11/S1/S3/S4 excluded |

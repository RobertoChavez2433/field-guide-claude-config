# Audit Fix List — 28 Items

All items below were found by exhaustive plan audit against `.claude/plans/2026-02-22-project-based-architecture-plan.md`. Fix ALL items.

**CRITICAL**: Use `pwsh -Command "flutter analyze"` to verify no analysis errors after all fixes.

---

## CRITICAL (3) — Runtime breakage, fix first

### FIX-1: UserProfile.toJson() PK mismatch
- **File**: `lib/features/auth/data/models/user_profile.dart`
- **Problem**: `toJson()` emits `'user_id': userId` but the Supabase `user_profiles` table PK column is `id`
- **Fix**: Change `toJson()` to use `'id': userId` to match the Supabase column name. Check `toMap()` for consistency — it likely already uses `'id'`.

### FIX-2: UserProfileRemoteDatasource.getById() column mismatch
- **File**: `lib/features/auth/data/datasources/remote/user_profile_remote_datasource.dart` (or similar path)
- **Problem**: `getById()` queries `.eq('user_id', userId)` but Supabase column is `id`
- **Fix**: Change to `.eq('id', userId)`

### FIX-3: Join request cancel blocked by RLS
- **File**: `lib/features/auth/data/datasources/remote/join_request_remote_datasource.dart`
- **Problem**: `cancel()` uses `.update({'status': 'cancelled'})` but there's no RLS UPDATE policy for users. Only a DELETE policy (`cancel_own_pending_request`) exists.
- **Fix**: Change `cancel()` to use `.delete().eq('id', id).eq('status', 'pending')` to match the DELETE policy. OR add `AND status = 'cancelled'` is not valid — use DELETE approach.

---

## HIGH (4) — Security/data gaps

### FIX-4: Provider-level viewer guards are dead code
- **File**: `lib/main.dart` — all provider constructions (~lines 560-670)
- **Problem**: Providers like `TodoProvider`, `InspectorFormProvider`, `PhotoProvider`, `ContractorProvider`, `LocationProvider`, `EquipmentProvider`, `PersonnelTypeProvider`, `DailyEntryProvider` accept a `canWrite` callback but it defaults to `() => true`. In `main.dart`, none of them receive the actual `AuthProvider.canWrite` value.
- **Fix**: After constructing `authProvider`, pass `canWrite: () => authProvider.canWrite` to EACH viewer-aware provider in main.dart. Check each provider's constructor to find the parameter name.

### FIX-5: Remote datasources missing company_id filtering on reads
- **File**: `lib/shared/datasources/base_remote_datasource.dart` and/or individual remote datasources
- **Problem**: `getAll()` does unfiltered `select()` without `.eq('company_id', companyId)`. RLS handles server-side, but the plan requires client-side filtering as defense-in-depth.
- **Fix**: Add an optional `companyId` parameter to `getAll()` in `BaseRemoteDatasource`. When provided, add `.eq('company_id', companyId)` to the query. Update callers to pass companyId where available. If BaseRemoteDatasource is too generic, override `getAll()` in the specific datasources that have company_id.

### FIX-6: UserProfileSyncDatasource.pullCompanyMembers() never called
- **File**: `lib/features/sync/application/sync_orchestrator.dart`
- **Problem**: `SyncOrchestrator` never calls `UserProfileSyncDatasource.pullCompanyMembers()` after successful data sync
- **Fix**: Inject `UserProfileSyncDatasource` into `SyncOrchestrator` (via constructor). After successful `syncLocalAgencyProjects()`, call `pullCompanyMembers(companyId)`. Get companyId from the sync context.

### FIX-7: SyncOrchestrator never updates last_synced_at
- **File**: `lib/features/sync/application/sync_orchestrator.dart`
- **Problem**: After successful sync push, should call `updateLastSyncedAt(userId)` on Supabase `user_profiles`
- **Fix**: After successful push in `syncLocalAgencyProjects()`, upsert `last_synced_at = now()` on the user's profile in Supabase. Use the injected datasource or a direct Supabase call.

---

## MEDIUM (7)

### FIX-8: BidItemProvider has no viewer guards
- **File**: `lib/features/quantities/presentation/providers/bid_item_provider.dart`
- **Problem**: No `canWrite` field or guard on any write method
- **Fix**: Add `bool Function() canWrite;` parameter (default `() => true`). Guard `create`, `update`, `delete` methods with `if (!canWrite()) return;`. Wire it in `main.dart` like the other providers (FIX-4).

### FIX-9: UserAttributionRepository._fetchFromRemote() is a stub
- **File**: `lib/features/auth/data/repositories/user_attribution_repository.dart`
- **Problem**: `_fetchFromRemote()` returns `'Unknown'` for any user not in cache
- **Fix**: Replace stub with actual Supabase query: `supabase.from('user_profiles').select('display_name').eq('id', userId).maybeSingle()`. Return the display_name if found, 'Unknown' if not. The repository needs a `SupabaseClient` reference — add it to the constructor if not present.

### FIX-10: Edge Function daily-sync-push/index.ts not created
- **File**: `supabase/functions/daily-sync-push/index.ts` (NEW FILE)
- **Problem**: The Supabase Edge Function for daily cron FCM push was never created
- **Fix**: Create the file as specified in Phase 4E of the plan. It should:
  1. Query `user_fcm_tokens` for all tokens
  2. Send silent FCM push with `data: { type: 'daily_sync' }` to each token
  3. Use `firebase-admin` SDK
  4. Include error handling for expired tokens (delete them)
  5. Be a Deno-based Supabase Edge Function

### FIX-11: admin_resolve_requests WITH CHECK missing user_id lock
- **File**: `supabase/migrations/20260222100000_multi_tenant_foundation.sql`
- **Problem**: `admin_resolve_requests` UPDATE policy WITH CHECK is missing `user_id` immutability
- **Fix**: Add `AND user_id = (SELECT user_id FROM company_join_requests cjr WHERE cjr.id = company_join_requests.id)` to the WITH CHECK clause of the `admin_resolve_requests` policy.

### FIX-12: AdminRepository has no client-side companyId validation
- **File**: `lib/features/settings/data/repositories/admin_repository.dart`
- **Problem**: No client-side assertion that target user's company matches the admin's company
- **Fix**: Add `companyId` parameter to constructor. Add assertion before each RPC call: `assert(companyId != null, 'Company ID required for admin operations')`. Pass companyId in main.dart.

### FIX-13: CalculatorProvider has no viewer guards
- **File**: `lib/features/calculator/presentation/providers/calculator_provider.dart`
- **Problem**: `saveCalculation` and `deleteCalculation` have no viewer check
- **Fix**: Add `bool Function() canWrite;` parameter (default `() => true`). Guard write methods. Wire in main.dart (FIX-4).

### FIX-14: loadProjectsByCompany(companyId) not implemented
- **File**: `lib/features/projects/presentation/providers/project_provider.dart` and `lib/features/projects/data/datasources/local/project_local_datasource.dart`
- **Problem**: Plan specifies `loadProjectsByCompany(String companyId)` which filters to company projects. Current `loadProjects()` loads all local projects.
- **Fix**: Add `getByCompanyId(String companyId)` to `ProjectLocalDatasource` (query WHERE company_id = ?). Add `loadProjectsByCompany(String companyId)` to `ProjectProvider`. Update the initial load in main.dart to use company-scoped loading when companyId is available.

---

## LOW (5)

### FIX-15: project_switcher_sheet.dart not a separate file
- **SKIP**: The private class approach is cleaner. No action needed.

### FIX-16: FirebaseMessaging.onBackgroundMessage registered in FcmHandler not main.dart
- **SKIP**: Functionally equivalent. No action needed.

### FIX-17: PDF field name 'hhhhhhhhhhhwerwer' placeholder
- **File**: `lib/features/pdf/data/services/pdf_service.dart` (~line 129)
- **Problem**: A garbled field name `'hhhhhhhhhhhwerwer'` appears to be a placeholder
- **Fix**: Check what this field maps to in the PDF template. If it's the inspector name field, rename it to the correct template field name. If the PDF template uses this actual field name (some do), leave it. Read the file to determine.

### FIX-18: getByProjectNumberInCompany() uniqueness check not implemented
- **File**: `lib/features/projects/data/datasources/local/project_local_datasource.dart`
- **Problem**: No method to check project number uniqueness within a company
- **Fix**: Add `getByProjectNumberInCompany(String projectNumber, String companyId)` that queries WHERE project_number = ? AND company_id = ?. Use it in project creation flow to prevent duplicates.

### FIX-19: WAL mode — already verified in Phase 1C
- **SKIP**: Already confirmed implemented. No action needed.

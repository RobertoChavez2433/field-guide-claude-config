# Adversarial Review: Project-Based Multi-Tenant Architecture Plan

**Date**: 2026-02-22
**Plan Reviewed**: `.claude/plans/2026-02-22-project-based-architecture-plan.md`
**Review Type**: Security + Codebase Continuity (adversarial)
**Method**: Plan split into 3 parts, each reviewed by 2 independent agents (6 total passes)

---

## Summary

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Security | 7 | 12 | 16 | 11 | 46 |
| Continuity | 6 | 11 | 15 | 13 | 45 |
| **Combined** | **13** | **23** | **31** | **24** | **91** |

### Top 5 Must-Fix Before Implementation

1. **Phase 0+1 must deploy atomically** — `anon USING (true)` policies on 5+ tables are live until Phase 1 drops them. The Supabase anon key is extractable from the APK.
2. **Sync pull has no company filter** — `BaseRemoteDatasource.getAll()` does unfiltered `select()`. If RLS fails on ANY table, cross-tenant data leaks to local SQLite with no audit trail.
3. **Background sync isolate has no authenticated session** — WorkManager callback runs in a fresh isolate with no JWT. Without explicit `recoverSession()`, it operates as anon.
4. **`created_by_user_id` is client-settable** — No server-side trigger enforces `created_by_user_id = auth.uid()`. Audit trail can be spoofed.
5. **Removing "push-all-if-empty" heuristic deletes the only initial-sync path** — Pre-existing local data for migrating users will never reach Supabase without a replacement first-sync mechanism.

---

## PART 1: Phases 0-2 (Foundation, Auth, Onboarding)

### Security Findings

#### CRITICAL

| ID | Title | Description |
|----|-------|-------------|
| SEC-P1-C1 | Phase 0→1 window allows `company_id` injection | Phase 0 adds `company_id` to projects with NO FK constraint. Until Phase 1 deploys `companies` table + FK, any value can be inserted. An attacker who guesses a future company UUID could pre-plant data. **Fix**: Deploy Phase 0 and Phase 1 atomically or within minutes. |
| SEC-P1-C2 | Deactivated users can spam join requests | `create_own_request` INSERT policy checks only `user_id = auth.uid()` — no status check. A deactivated user with a valid JWT (up to 1hr) can flood companies with requests. **Fix**: Add `AND (SELECT status FROM user_profiles WHERE id = auth.uid()) NOT IN ('deactivated', 'rejected')` to the WITH CHECK. |
| SEC-P1-C3 | `entry_personnel` table may retain open anon policies | Plan drops anon policies on listed tables but `entry_personnel` is not in any RLS replacement group. If old anon policies survive, any authenticated user can read all personnel data cross-company. **Fix**: Either DROP the table in Phase 1 or explicitly include it in the policy sweep. |

#### HIGH

| ID | Title | Description |
|----|-------|-------------|
| SEC-P1-H1 | Viewer role assignable before Phase 8 UI guards exist | `approve_join_request` allows 'viewer' role from Phase 1, but viewer UI enforcement is Phase 8. A viewer could create local data that fails on sync, causing dirty SQLite state. **Fix**: Remove 'viewer' from allowed roles until Phase 8, or ensure `canWrite` is enforced at repository layer from Phase 2. |
| SEC-P1-H2 | Company search enables systematic enumeration | Any authenticated user (even deactivated) can scan 17,576 three-letter prefixes to build a company directory. **Fix**: Restrict search to users with `company_id IS NULL` and add rate limiting. |
| SEC-P1-H3 | No CHECK constraints on role/status columns | Plain TEXT with no CHECK means a buggy RPC could write `role = 'superadmin'` and get full write access. **Fix**: Add `CHECK (role IN ('admin','engineer','inspector','viewer'))` and `CHECK (status IN ('pending','approved','rejected','deactivated'))`. |
| SEC-P1-H4 | `last_synced_at` is user-writable | `update_own_profile` locks role/status/company_id but NOT `last_synced_at`. A user can set it to a future date, suppressing admin stale-data warnings. **Fix**: Lock it in WITH CHECK or update only via SECURITY DEFINER RPC. |
| SEC-P1-H5 | Hardcoded predictable seed UUIDs in version control | Company UUID `00000000-...0001` is predictable. Roberto's auth UUID is public. Enables targeted phishing. **Fix**: Use `gen_random_uuid()` for company seed. |
| SEC-P1-H6 | `admin_resolve_requests` UPDATE has no column lock | Admins can UPDATE `user_id` on join requests, potentially force-adding users who never requested. **Fix**: Add WITH CHECK locking `user_id` and `company_id` to existing values. |

#### MEDIUM

| ID | Title | Description |
|----|-------|-------------|
| SEC-P1-M1 | NULL semantics are the only unapproved-user guard | `get_my_company_id()` returning NULL blocks access only because `NULL = NULL` is FALSE in SQL. Fragile. **Fix**: Document the NULL contract. Add explicit status check. |
| SEC-P1-M2 | No UPDATE policy on storage.objects | Photo replacement silently blocked. Fine if intentional — must be documented. |
| SEC-P1-M3 | Storage filename regex allows any characters | `[^/]+` permits `..`, `%00`, etc. Supabase rejects traversal but double-encoding could bypass. **Fix**: Tighten to `[a-zA-Z0-9_.-]+\.(jpg\|jpeg\|png\|heic)$`. |
| SEC-P1-M4 | 10s polling is a DoS vector | 100 pending users = 600 queries/min with RLS subquery evaluation. **Fix**: Exponential backoff or Supabase Realtime. |
| SEC-P1-M5 | No cascade behavior on company deletion | `user_profiles.company_id` FK defaults to RESTRICT. Future company deletion would orphan references. **Fix**: Add `ON DELETE SET NULL`. |
| SEC-P1-M6 | Rejected users can create companies | `create_company` blocks deactivated but not rejected users. **Fix**: Add rejected to the status check. |
| SEC-P1-M7 | Supabase not-configured bypasses all auth | `if (!SupabaseConfig.isConfigured) return null` allows unauthenticated access. **Fix**: Crash in release mode. |
| SEC-P1-M8 | No length validation on company_name | 10MB company name possible. **Fix**: Add 2-200 char length check. |
| SEC-P1-M9 | Weak password policy (min 6, no complexity) | Below industry standards for construction inspection data. **Fix**: Min 8, require mixed case + digits. |
| SEC-P1-M10 | Email confirmation disabled | Users can sign up with any email. Critical when admins approve based on email. **Fix**: Enable confirmations. |

#### LOW

| ID | Title |
|----|-------|
| SEC-P1-L1 | ILIKE escaping misses backslash character |
| SEC-P1-L2 | Company seed uses ON CONFLICT DO NOTHING (inconsistent with user upsert) |
| SEC-P1-L3 | `secure_password_change = false` — no re-auth needed |
| SEC-P1-L4 | Phone/cert_number have no format validation |
| SEC-P1-L5 | No global limit on pending join requests per user |
| SEC-P1-L6 | No audit log for admin actions (deactivate, role change, etc.) |

### Continuity Findings

#### BREAKING

| ID | Title | Description |
|----|-------|-------------|
| CONT-P1-B1 | Sync pull crashes on old app versions | Phase 0 adds columns to Supabase that old SQLite schema doesn't have. `_upsertLocalRecords()` does raw `db.insert()` — SQLite rejects unknown columns. `_convertForLocal()` does NOT strip them. **Fix**: Ship Phase 0 (Supabase) and Phase 1C (SQLite v24) in the same app release, or harden `_convertForLocal()` to strip unknown columns. |
| CONT-P1-B2 | Direct SharedPreferences reads lose inspector data | `pdf_data_builder.dart:120-122` and `entry_photos_section.dart:87-88` read inspector fields directly from SharedPreferences (bypassing PreferencesService). Phase 2F clears these keys after migration. These callers get null → PDFs show "Inspector", photos show "XX". **Fix**: Refactor all direct SharedPreferences callers before clearing keys. |
| CONT-P1-B3 | `toMap()` emits columns before schema exists | Phase 1B models emit `created_by_user_id` but Phase 1C schema hasn't been updated yet. Fresh installs crash. **Fix**: Phases 1B and 1C must be a single atomic commit. |

#### HIGH RISK

| ID | Title | Description |
|----|-------|-------------|
| CONT-P1-H1 | Router refactor creates chicken-and-egg with AuthProvider | Static `AppRouter.router` → instance-based requires AuthProvider, but AuthProvider is created inside MultiProvider which needs the router. **Fix**: Hoist AuthProvider creation before router construction in `_runApp()`. |
| CONT-P1-H2 | 5-state redirect breaks mock auth and test harness | New redirect logic doesn't mention preserving `TestModeConfig.useMockAuth` or `!SupabaseConfig.isConfigured` bypasses. Harness has no UserProfile/Company objects. **Fix**: Explicitly preserve existing early returns for mock/offline modes. |
| CONT-P1-H3 | `entry_contractors` created in Supabase but never synced | Catch-up migration creates the table, but SyncService has no push/pull for it. Local data never reaches Supabase. |
| CONT-P1-H4 | Auth feature has no `data/` directory — plan assumes deep barrel structure | Creating `auth/data/` with 6+ barrel files is a new layer, not a modification. Ordering matters to avoid import errors. |
| CONT-P1-H5 | "Clear local data on company change" risks data loss | HIGH-4 fix deletes local SQLite data on company switch. If unsynced data exists, it's lost forever. **Fix**: Only clear after confirming sync complete. Require user confirmation. |

#### MEDIUM RISK

| ID | Title |
|----|-------|
| CONT-P1-M1 | `company_id` FK-less during Phase 0→1 window |
| CONT-P1-M2 | `toMap()` pushes null `company_id` to Supabase (valid but verify) |
| CONT-P1-M3 | SQLite v24 migration partial failure leaves inconsistent state |
| CONT-P1-M4 | Auto-fill and PDF still read from PreferencesService (migration ordering) |
| CONT-P1-M5 | `calculation_history` CREATE TABLE missing `updated_at` for fresh installs |
| CONT-P1-M6 | Timer.periodic polling has no `mounted` check (race condition with dispose) |

---

## PART 2: Phases 3-5 (Sync, Firebase, Project Switcher)

### Security Findings

#### CRITICAL

| ID | Title | Description |
|----|-------|-------------|
| SEC-P2-C1 | Background sync isolate runs without auth session | WorkManager callback creates fresh Supabase instance. `currentSession` is null unless `recoverSession()` is called. Could operate as anon key. **Fix**: Mandate `recoverSession()` + `if (session == null) return` guard at top of callback. |
| SEC-P2-C2 | Edge Function invocable by anyone without auth | `daily-sync-push` uses `service_role` to read ALL FCM tokens. No Authorization header validation means anyone who finds the URL can trigger it. **Fix**: Validate `Authorization: Bearer <secret>` or use a cron-only invocation pattern. |
| SEC-P2-C3 | Live `anon USING (true)` policies on 5+ tables | Catch-up migration creates wide-open anon policies on `personnel_types`, `entry_personnel_counts`, `entry_equipment`, `entry_personnel`, `entry_contractors`. Anon key is extractable from APK. **Fix**: Deploy Phase 0 and Phase 1 as a SINGLE migration. |
| SEC-P2-C4 | Local SQLite tamper on rooted devices | On company change, old company data persists in local SQLite. No clear/wipe mechanism specified. **Fix**: Wipe local database on sign-out or company change. |

#### HIGH

| ID | Title | Description |
|----|-------|-------------|
| SEC-P2-H1 | No mutex on concurrent sync | App close (30s debounce), app open (>24h stale), and background sync can overlap. Non-atomic check-then-act at `sync_service.dart:302`. **Fix**: Use `Completer` or async Lock pattern. |
| SEC-P2-H2 | "Remote empty → push all" heuristic enables cross-company push | User joins Company B but has Company A data locally. Company B tables appear "empty" (RLS), triggering push-all of Company A's data. **Fix**: Remove heuristic BEFORE multi-tenant goes live (already flagged as CRIT-8, but must be a blocking prerequisite). |
| SEC-P2-H3 | `last_synced_at` client-writable via profile update | Malicious user sets future date, suppressing admin stale-data warnings. Unsynced data could be silently lost. **Fix**: Update only via SECURITY DEFINER RPC. |
| SEC-P2-H4 | FCM tokens not cleaned up on deactivation | Deactivated user's token remains in `user_fcm_tokens`. If device is sold, new owner receives push notifications. **Fix**: `deactivate_member()` RPC should DELETE from `user_fcm_tokens`. |
| SEC-P2-H5 | Local SQLite unencrypted and never cleared on sign-out | Company member profiles (names, phones, cert numbers) cached in plaintext. **Fix**: Clear on sign-out. Consider `sqflite_sqlcipher`. |
| SEC-P2-H6 | Photos still use `getPublicUrl()` in production | `photo_remote_datasource.dart:60` returns public URLs. All photos accessible to anyone who guesses the path. **Fix**: Make `createSignedUrl()` switch a Phase 1 blocker, not a deferral. |

#### MEDIUM

| ID | Title |
|----|-------|
| SEC-P2-M1 | FCM payload has no HMAC — triggerable by any FCM sender |
| SEC-P2-M2 | `BaseRemoteDatasource.deleteAll()` has no company scoping |
| SEC-P2-M3 | `updated_at` client-settable on INSERT (DoS vector for sync) |
| SEC-P2-M4 | Three providers bypass SyncOrchestrator with unscoped `queueOperation()` |
| SEC-P2-M5 | JSONB→String conversion could produce oversized SQLite values |
| SEC-P2-M6 | Company search allows systematic enumeration by any authenticated user |
| SEC-P2-M7 | SharedPreferences not cleared on sign-out (leaks user IDs and project IDs) |

#### LOW

| ID | Title |
|----|-------|
| SEC-P2-L1 | Firebase config files in source control (messaging sender ID exposed) |
| SEC-P2-L2 | Desktop sync timer has no jitter (coordinated load spikes) |
| SEC-P2-L3 | Project number uniqueness check is local-only (race condition) |
| SEC-P2-L4 | `saveFcmToken` has no token format validation |
| SEC-P2-L5 | `pullCompanyMembers` caches PII unencrypted (phone, cert number) |

### Continuity Findings

#### BREAKING

| ID | Title | Description |
|----|-------|-------------|
| CONT-P2-B1 | Three providers lose sync-on-save capability | `InspectorFormProvider`, `CalculatorProvider`, `TodoProvider` call `syncService.queueOperation()`. Plan says "route through SyncOrchestrator" but SyncOrchestrator has no `queueOperation` method. **Without specifying the replacement API, forms/todos/calculations silently stop syncing.** |
| CONT-P2-B2 | Removing push-all-if-empty deletes only initial-sync mechanism | For first-ever sync, there's no `updated_at` baseline. Without "push all if `lastSyncTime == null`" replacement, **all pre-existing local data never reaches Supabase**. Data loss for migration path. |
| CONT-P2-B3 | `entry_contractors` has no `updated_at` column | Added as new sync target but has no `updated_at` in local or remote schema. Sync conflict resolution always falls to "remote wins" branch. Same for `entry_personnel_counts`. |
| CONT-P2-B4 | SyncProvider interface mismatch | `SyncProvider` proxies `_syncService.isOnline` but SyncOrchestrator exposes `isSupabaseOnline`. Property name mismatch breaks `SyncProvider.isOnline`. |

#### HIGH RISK

| ID | Title | Description |
|----|-------|-------------|
| CONT-P2-H1 | JSONB conversion underspecified | Plan says "jsonEncode on pull, jsonDecode on push" but doesn't list ALL affected fields (`response_data`, `header_data`, `response_metadata`, `table_rows`). Developers could miss fields or apply conversion backwards. |
| CONT-P2-H2 | WorkManager isolate can't access main singletons | Background isolate creates second SQLite connection. Two writers → `SQLITE_BUSY`. Plan doesn't address WAL mode or concurrent write handling. |
| CONT-P2-H3 | SyncLifecycleManager fires before auth is ready | Registered in main.dart but user may not be logged in. `paused/detached` callback with no companyId crashes. **Fix**: Guard with `AuthProvider.isAuthenticated` check. |
| CONT-P2-H4 | `loadProjectsByCompany(companyId)` breaks startup | `companyId` comes from AuthProvider which may not have loaded `userProfile` yet (async). Null companyId → zero projects on dashboard. **Fix**: Defer loading until after userProfile loads, or fall back to `loadProjects()`. |
| CONT-P2-H5 | `company_id` column doesn't exist in local SQLite | `loadProjectsByCompany(companyId)` queries `WHERE company_id = ?` but no `company_id` column exists in local schema until Phase 1C migration runs. Cross-phase dependency. |

#### MEDIUM RISK

| ID | Title |
|----|-------|
| CONT-P2-M1 | Per-user pref key migration not specified (old `lastProjectId` orphaned) |
| CONT-P2-M2 | ProjectSwitcher in ScaffoldWithNavBar changes app bar for ALL routes (including Settings) |
| CONT-P2-M3 | Firebase init not guarded by platform — Windows builds crash |
| CONT-P2-M4 | No remote datasources exist for entry_contractors or entry_personnel_counts |
| CONT-P2-M5 | Stale-data banner has no UI specification |
| CONT-P2-M6 | `entry_personnel` removal leaves orphaned remote datasource and imports |

---

## PART 3: Phases 6-8 + Risk Register (Admin, Audit, Viewer)

### Security Findings

#### CRITICAL

| ID | Title | Description |
|----|-------|-------------|
| SEC-P3-C1 | Sync pull fetches ALL records from ALL companies | `BaseRemoteDatasource.getAll()` does unfiltered `select()`. Every `_pullXxx` method in sync service pulls entire tables. If RLS is misconfigured on even one table, cross-tenant data leaks to local SQLite with no server audit. **Fix**: Add explicit `.eq('company_id', companyId)` on ALL pull queries as defense-in-depth. |
| SEC-P3-C2 | Photo storage has no company scoping — cross-tenant access | Upload path is `entries/${entryId}/${filename}` with no company prefix. `getPublicUrl()` returns unauthenticated URLs. Any guessed entry ID exposes photos. **Fix**: Restructure paths to `entries/{companyId}/{entryId}/{filename}` and switch to signed URLs (plan mentions this but defers it). |
| SEC-P3-C3 | Last-admin guard is app-side only — no server enforcement | RPCs `deactivate_member` and `update_member_role` have comment stubs but no confirmed server-side admin count check. Direct API call could lock out a company permanently. **Fix**: Add `IF (SELECT count(*) FROM user_profiles WHERE company_id = v_company_id AND role = 'admin' AND status = 'approved') <= 1 THEN RAISE EXCEPTION` to both RPCs. |
| SEC-P3-C4 | Deactivation window allows 1 hour of full access | "RLS blocks immediately" is incorrect — JWT-based auth means the deactivated user's token is valid until expiry. A fired employee with the app open can export all data. **Fix**: Reduce JWT expiry to 5-10 minutes for sensitive deployments, or add a middleware check on critical operations. |

#### HIGH

| ID | Title | Description |
|----|-------|-------------|
| SEC-P3-H1 | Admin dashboard route has no server-side guard | Non-admin can deep-link to `/admin-dashboard`. RPCs reject unauthorized callers, but the UI renders company member data (names, roles, sync health) before any RPC fails. **Fix**: Add role check in router redirect for `/admin-dashboard`. |
| SEC-P3-H2 | Viewer enforcement incomplete — 6+ write surfaces missing | Missing: `todos_screen.dart` (FAB), `TodoProvider`, `InspectorFormProvider`, `forms_list_screen.dart`, `EquipmentProvider`, `PersonnelTypeProvider`, `BidItemProvider`, `DailyEntryProvider`. **Fix**: Audit ALL providers for write methods and guard them. |
| SEC-P3-H3 | `created_by_user_id` can be spoofed by client | No server-side trigger enforces `created_by_user_id = auth.uid()`. Sync pushes whatever the client sends. A malicious inspector can attribute fraudulent entries to their supervisor. **Fix**: Add `BEFORE INSERT` trigger: `NEW.created_by_user_id = auth.uid()`. |
| SEC-P3-H4 | 52+ `anon USING (true)` policies still active in production | Existing schema + catch-up migration create wide-open anon policies. Plan drops them in Phase 1 but no deployment interlock. **Fix**: Deploy Phase 0+1 atomically, verify with `SELECT policyname FROM pg_policies WHERE roles @> '{anon}'` returning 0 rows. |
| SEC-P3-H5 | No storage bucket RLS policies specified | `entry-photos` bucket may be publicly readable by default. No policies in the plan address storage.objects. **Fix**: Add explicit storage RLS policies in Phase 1. |

#### MEDIUM

| ID | Title |
|----|-------|
| SEC-P3-M1 | `UserAttributionRepository` may leak display names across companies (remote fallback unscoped) |
| SEC-P3-M2 | Phase deployment order creates security windows (viewer blocks before/after RLS) |
| SEC-P3-M3 | AdminRepository relies solely on RLS — no client-side companyId validation |
| SEC-P3-M4 | SyncHealth indicator exposes team activity timing if admin dashboard leaks |
| SEC-P3-M5 | PDF attribution exposes inspector names in exported files (no opt-out) |
| SEC-P3-M6 | No rate limiting on admin RPCs (compromised admin could mass-approve) |

#### LOW

| ID | Title |
|----|-------|
| SEC-P3-L1 | 10s polling interval for pending approval (battery + timing side channel) |
| SEC-P3-L2 | Inspector profile in SharedPreferences stored as plaintext |
| SEC-P3-L3 | Mock auth hardcoded credentials (`test@example.com / Test123!`) |
| SEC-P3-L4 | ViewOnlyBanner is UI-only — no defense for offline writes on rooted device |

### Continuity Findings

#### BREAKING

| ID | Title | Description |
|----|-------|-------------|
| CONT-P3-B1 | Phase 7 audit trail requires columns that don't exist yet | `DailyEntry`, `Photo`, `Project` models have no `createdByUserId` field in current code. SQLite has no such columns. Plan must clarify which earlier phase (1B/1C) adds these — Phase 7 cannot function without them. |
| CONT-P3-B2 | AdminProvider breaks provider wiring pattern | Plan says `AdminProvider(AdminRepository(supabaseClient, authProvider))` but NO current provider takes another provider as constructor arg. `ChangeNotifierProxyProvider` is not used anywhere. **Fix**: Either pre-construct authProvider outside MultiProvider, or use ProxyProvider (and document the new pattern). |

#### HIGH RISK

| ID | Title | Description |
|----|-------|-------------|
| CONT-P3-H1 | Viewer guard list incomplete — 6+ write providers unguarded | TodoProvider, InspectorFormProvider, EquipmentProvider, PersonnelTypeProvider, BidItemProvider, DailyEntryProvider have unrestricted create/update/delete. Plan only guards 3 providers. |
| CONT-P3-H2 | PhotoProvider/ContractorProvider/LocationProvider can't access AuthProvider | These providers take only Repository in constructor. No mechanism to check `canWrite`. **Fix**: Specify injection approach (constructor change, ProxyProvider, or UI-only guards). |
| CONT-P3-H3 | PDF `createdByDisplayName` has no delivery mechanism | `PdfDataBuilder.generate()` takes only providers and datasources. No `UserAttributionRepository` in its parameter list. `IdrPdfData` already has `inspectorName` — relationship to new field unclear. |

#### MEDIUM RISK

| ID | Title |
|----|-------|
| CONT-P3-M1 | Admin Dashboard placement in settings_screen.dart unspecified (which section?) |
| CONT-P3-M2 | `admin_repository.dart` under `settings/data/` is domain mismatch (should be `auth/`) |
| CONT-P3-M3 | `/admin-dashboard` not mentioned for `_isRestorableRoute` exclusion |
| CONT-P3-M4 | `UserAttributionRepository` has no provider wrapper — widgets can't access it |
| CONT-P3-M5 | Viewer enforcement is UI-only, not provider-level defense-in-depth |
| CONT-P3-M6 | `view_only_banner.dart` barrel export in `shared/widgets/widgets.dart` not mentioned |

---

## Missing Risks (Not in the Plan's Risk Register)

| # | Risk | Impact |
|---|------|--------|
| 1 | Cross-tenant sync leak via unfiltered `BaseRemoteDatasource.getAll()` | High — all company data for a table leaks to local SQLite |
| 2 | Photo storage publicly accessible via `getPublicUrl()` | High — inspection photos from all companies exposed |
| 3 | 52+ `anon USING (true)` policies live until Phase 1 drops them | Critical — full CRUD for unauthenticated users |
| 4 | `created_by_user_id` spoofable — no server enforcement | High — audit trail fabrication |
| 5 | Local SQLite retains leaked data permanently | Medium — no "recall" mechanism after cross-tenant leak |
| 6 | Partial migration rollback leaves mixed RLS state | High — some tables secured, others wide open |
| 7 | `BaseRemoteDatasource.deleteAll()` could wipe company data | Medium — `.neq('id', '00...')` deletes everything |
| 8 | Toolbox features (forms, todos, calculator) unguarded for viewers | Medium — viewers can create/edit forms and todos |
| 9 | Mock auth has no concept of roles | Medium — all tests run with undefined role behavior |
| 10 | No rollback plan for provider constructor changes | Medium — bad deployment crashes entire app on startup |
| 11 | UserAttributionText FutureBuilder × 50 entries = 50 concurrent async calls | Low — cold cache performance |
| 12 | JWT refresh token theft allows indefinite access after deactivation | Medium — no token rotation |

---

## Things Done Well

The plan demonstrates strong security awareness in several areas:

- **SECURITY DEFINER RPCs for all admin operations** — Prevents direct table manipulation
- **Separate per-operation RLS (no FOR ALL)** — Eliminates permissive policy anti-pattern
- **`NOT is_viewer()` on write policies from Phase 1** — Proactive, not retrofitted
- **REVOKE EXECUTE from anon on all RPCs** — Prevents unauthenticated function access
- **`update_own_profile` locks role/status/company_id** — Users cannot self-promote
- **No INSERT policy on user_profiles** — Creation exclusively via trigger
- **Signed URLs planned for photos** — 1-hour expiry limits exposure (when implemented)
- **Unique partial index on pending join requests** — Prevents same-company spam
- **Post-deployment verification query** — `SELECT FROM pg_policies WHERE roles @> '{anon}'` = 0 rows
- **FCM tokens in separate table** — Prevents token leakage to company members
- **Passive JWT expiry model** — Avoids complexity of server-initiated session revocation
- **Per-user preference keys** — Prevents cross-user preference leakage
- **`_addColumnIfNotExists()` pattern** — Safe, idempotent SQLite migrations
- **Nullable fields for backwards compatibility** — Existing code won't crash on missing values
- **Comprehensive fix-tag system (SEC-*, CONT-*, CRIT-*, HIGH-*, MED-*, LOW-*)** — Shows iterative review

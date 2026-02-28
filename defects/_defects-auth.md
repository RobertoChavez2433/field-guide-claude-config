# Defects: Auth

Active patterns for auth. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [DATA] 2026-02-22: RLS locks columns that code tries to update
**Pattern**: `update_own_profile` RLS policy locks `last_synced_at` via WITH CHECK subselect. Client-side `.update({'last_synced_at': ...})` silently fails. Required SECURITY DEFINER RPC bypass.
**Prevention**: When RLS locks a column, any client code updating that column needs a SECURITY DEFINER RPC. Audit RLS WITH CHECK clauses against all Dart `.update()` calls.
**Ref**: @supabase/migrations/20260222100000_multi_tenant_foundation.sql, @lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart

### [DATA] 2026-02-22: fromJson/fromMap column name mismatches with Supabase
**Pattern**: Dart model `fromJson()` used `created_at`/`updated_at` but Supabase table has `requested_at`/`resolved_at`. Also `user_id` vs `id` mismatch. Caused null cast crashes at runtime.
**Prevention**: Always cross-reference Supabase table column names with Dart fromJson() factories. Use `?? json['alt_name']` fallback pattern for columns that differ between local/remote schemas.
**Ref**: @lib/features/auth/data/models/company_join_request.dart, @lib/features/auth/data/models/user_profile.dart

### [DATA] 2026-02-22: Enum values must match Supabase CHECK constraints exactly
**Pattern**: Dart `UserRole` enum had `member` but Supabase CHECK enforced `engineer`/`inspector`. RPC calls sent `'member'` which was rejected server-side.
**Prevention**: Enum `.name` values sent to Supabase RPCs must match the CHECK constraint values exactly. Add a `toDbString()` method if Dart enum names differ from DB values.
**Ref**: @lib/features/auth/data/models/user_role.dart

### [FLUTTER] 2026-02-22: Provider canWrite callbacks not wired
**Pattern**: Providers accept `bool Function() canWrite` callback but it defaults to `() => true` and is never connected to `AuthProvider.canWrite` in `main.dart`.
**Prevention**: When adding canWrite guards to providers, also update `main.dart` provider registration to pass `canWrite: () => authProvider.canWrite`.
**Ref**: All 8+ providers with canWrite (contractor, equipment, personnel_type, todo, location, daily_entry, inspector_form, photo)

### [CONFIG] 2026-02-22: Wrong Supabase key type hardcoded
**Pattern**: `sb_publishable_...` (default publishable key) used instead of JWT `anon` key (`eyJhbG...`). Supabase client silently fails auth — no session restored, no profile loaded.
**Prevention**: Supabase anon key is always a ~200-char JWT starting with `eyJ`. The `sb_publishable_*` key is a different key type. Always verify key format.
**Ref**: @lib/core/config/supabase_config.dart

### [FLUTTER] 2026-02-22: createCompany doesn't refresh local profile state
**Pattern**: RPC `create_company` sets `status=approved, role=admin` server-side, but `AuthProvider.createCompany()` only updates `_company`, not `_userProfile`. Router sees stale `status=pending` and redirects to wrong screen.
**Prevention**: After any Supabase RPC that modifies user_profiles server-side, always call `await loadUserProfile()` to sync local state.
**Ref**: @lib/features/auth/presentation/providers/auth_provider.dart:401-419

### [FLUTTER] 2026-02-22: Onboarding routes exempt from profile-based redirect
**Pattern**: `_kOnboardingRoutes` were fully exempt from redirect checks. If profile loads async and user is already on `/profile-setup`, go_router re-evaluates but returns `null` for onboarding routes — user stays stuck even when fully approved.
**Prevention**: Onboarding route exemption must still check if user is fully set up (approved + has company) and redirect to `/` if so.
**Ref**: @lib/core/router/app_router.dart:113-125

<!-- Add defects above this line -->

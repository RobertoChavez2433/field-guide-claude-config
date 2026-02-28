# Multi-Tenant Architecture — E2E Test Report

**Date**: 2026-02-22 | **Session**: 454-456
**Tester**: Claude (dart-mcp)
**Scope**: All flows added/changed in last 36 hours (Sessions 449-453)

## Test Summary

| Category | Total | Pass | Fail | Blocked | Notes |
|----------|-------|------|------|---------|-------|
| Auth & Onboarding | 7 | 4 | 2 | 1 | INSERT policy + routing fixes applied |
| Project Management | 0 | 0 | 0 | 0 | |
| Admin Dashboard | 0 | 0 | 0 | 0 | |
| Settings & Profile | 0 | 0 | 0 | 0 | |
| Data Sync | 0 | 0 | 0 | 0 | |
| Navigation & Routing | 2 | 2 | 0 | 0 | |
| Entry Flows | 0 | 0 | 0 | 0 | |
| Toolbox (Forms/Todos/Calc/Gallery) | 0 | 0 | 0 | 0 | |
| **TOTAL** | **9** | **6** | **2** | **1** | |

---

## Test Plan

### 1. Auth & Onboarding Flows
- [x] T-AUTH-01: App launches to login screen when unauthenticated — **PASS**
- [x] T-AUTH-02: Login with valid credentials succeeds — **PASS**
- [x] T-AUTH-03: After login, profile setup screen appears (new user flow) — **PASS** (redirected correctly)
- [x] T-AUTH-04: Profile setup form validates required fields — **PASS** (Session 456: empty name shows "Please enter your name" error)
- [x] T-AUTH-05: Profile setup saves to Supabase user_profiles table — **PASS** (Session 456: fixed with INSERT policy migration 20260222400000)
- [x] T-AUTH-06: Company setup screen — create new company flow — **FAIL** (Session 456: company created OK but routed to Pending Approval instead of home — see F-AUTH-06/07/08)
- [ ] T-AUTH-07: Company setup screen — search and join existing company — **BLOCKED** (can't get past company setup)
- [ ] T-AUTH-08: Pending approval screen shows after join request — **BLOCKED**
- [ ] T-AUTH-09: Account status screen shows for rejected/deactivated users — **BLOCKED**
- [ ] T-AUTH-10: Sign out clears auth state and returns to login

### 2. Project Management
- [ ] T-PROJ-01: Project list screen loads with company-scoped projects
- [ ] T-PROJ-02: Create new project with required fields
- [ ] T-PROJ-03: Project switcher widget shows in app bar
- [ ] T-PROJ-04: Switch between projects via project switcher
- [ ] T-PROJ-05: Edit existing project details
- [ ] T-PROJ-06: Project setup tabs work (Details, Locations, Contractors, Pay Items)

### 3. Admin Dashboard
- [ ] T-ADMIN-01: Admin dashboard accessible from settings (admin only)
- [ ] T-ADMIN-02: Non-admin cannot access admin dashboard
- [ ] T-ADMIN-03: Pending join requests display correctly
- [ ] T-ADMIN-04: Approve join request with role selection
- [ ] T-ADMIN-05: Reject join request
- [ ] T-ADMIN-06: Team members list shows all company members
- [ ] T-ADMIN-07: Member detail sheet opens on tap
- [ ] T-ADMIN-08: Change member role from detail sheet
- [ ] T-ADMIN-09: Deactivate/reactivate member

### 4. Settings & Profile
- [ ] T-SET-01: Settings screen loads with all sections
- [ ] T-SET-02: Profile section shows user info (name, role, company)
- [ ] T-SET-03: Edit profile screen loads with current data
- [ ] T-SET-04: Save profile changes persists to Supabase
- [ ] T-SET-05: Theme toggle works (light/dark)
- [ ] T-SET-06: Admin dashboard link visible only for admins
- [ ] T-SET-07: Sign out from settings works

### 5. Data Sync (Supabase)
- [ ] T-SYNC-01: Manual sync triggers successfully
- [ ] T-SYNC-02: Projects sync with company_id scoping
- [ ] T-SYNC-03: Entries sync with project scoping
- [ ] T-SYNC-04: User attribution (created_by_user_id) populated on new records
- [ ] T-SYNC-05: Sync status indicator updates correctly
- [ ] T-SYNC-06: Stale data warning appears after 24h without sync

### 6. Navigation & Routing
- [x] T-NAV-01: Bottom nav bar shows 4 tabs (Dashboard, Calendar, Projects, Settings) — **PASS** (verified in offline mode screenshot)
- [ ] T-NAV-02: Tab switching works correctly
- [ ] T-NAV-03: Deep linking to entry editor works
- [x] T-NAV-04: Auth guard redirects unauthenticated users to login — **PASS** (verified: Supabase-enabled app shows login)
- [ ] T-NAV-05: Profile-incomplete guard redirects to profile setup
- [ ] T-NAV-06: Admin route guard blocks non-admins

### 7. Entry Flows
- [ ] T-ENTRY-01: Create new daily entry for selected project
- [ ] T-ENTRY-02: Entry editor loads with all sections
- [ ] T-ENTRY-03: Save entry persists to local DB
- [ ] T-ENTRY-04: Entry list shows entries for current project only
- [ ] T-ENTRY-05: View-only banner shows for viewer role users

### 8. Toolbox (Forms/Todos/Calculator/Gallery)
- [ ] T-TOOL-01: Forms list loads for current project
- [ ] T-TOOL-02: Todo list loads and allows add/complete
- [ ] T-TOOL-03: Calculator screen accessible
- [ ] T-TOOL-04: Gallery screen loads photos for project

---

## Findings Log

### F-BUILD-01: CMake 4.x Incompatibility with Firebase C++ SDK
**Status**: FIXED (workaround applied)
**Severity**: HIGH (blocks all Windows builds)
**Steps**: Launch app on Windows with Firebase dependency
**Expected**: Build succeeds
**Actual**: CMake 4.1.1 rejects `cmake_minimum_required(VERSION 3.1)` in Firebase SDK
**Fix Applied**: Added `set(CMAKE_POLICY_VERSION_MINIMUM 3.5)` to `windows/CMakeLists.txt:4`
**Root Cause**: Firebase C++ SDK ships with CMakeLists targeting CMake 3.1, but CMake 4.x dropped compat for <3.5

### F-AUTH-01: Pre-existing Users Cannot Complete Onboarding (CRITICAL BLOCKER)
**Status**: FAIL
**Severity**: CRITICAL
**Steps**: 1) Login as pre-existing user (created before multi-tenant migration), 2) Fill profile setup, 3) Tap Continue
**Expected**: Profile saved to Supabase user_profiles, navigate to company setup
**Actual**: `PostgrestException(message: new row violates row-level security policy for table "user_profiles", code: 42501)`
**Root Cause**: The `handle_new_user()` trigger only fires on `AFTER INSERT ON auth.users`. Pre-existing users have no `user_profiles` row. The RLS policy has NO INSERT policy on user_profiles (by design: "Profile creation via handle_new_user() trigger only"). The Supabase upsert fails because it needs to INSERT (no existing row) but no INSERT policy exists.
**Impact**: ALL pre-existing users are permanently stuck on profile setup. Create company also fails ("No profile found"). The ENTIRE onboarding flow is broken for any user who existed before migration deployment.
**Fix Options**:
1. Add a SQL backfill: `INSERT INTO user_profiles (id) SELECT id FROM auth.users WHERE id NOT IN (SELECT id FROM user_profiles)`
2. Add a temporary INSERT policy on user_profiles for `id = auth.uid()` (allows self-registration)
3. Make the `updateUserProfile` use a SECURITY DEFINER function instead of direct table upsert

### F-AUTH-02: Profile Setup "Certification Number" Label Too Vague
**Status**: FAIL (UX)
**Severity**: MEDIUM
**Steps**: View profile setup screen
**Expected**: Label clearly identifies this as "Density Certification Number"
**Actual**: Label just says "Certification Number" — ambiguous for construction inspectors
**Fix**: Change label to "Density Certification Number" and hint to "e.g. DC-12345"
**File**: `lib/features/auth/presentation/screens/profile_setup_screen.dart:146`

### F-AUTH-03: Onboarding Screens Missing Testing Keys
**Status**: NOTED (partially fixed during testing)
**Severity**: LOW
**Steps**: Attempt to interact with profile_setup and company_setup screens via flutter_driver
**Expected**: All interactive widgets have ValueKey for testing
**Actual**: TextFormFields on profile_setup (4 fields) and company_setup (2 fields) had no ValueKeys. Flutter driver couldn't target individual fields.
**Fix Applied**: Added keys to company_name_field, company_search_field, profile_name_field, profile_cert_field during testing. Remaining: profile phone/position fields, profile Continue button, company Create button.
**File**: `profile_setup_screen.dart`, `company_setup_screen.dart`

### F-AUTH-04: Error Messages Swallowed in Auth Provider
**Status**: NOTED
**Severity**: MEDIUM
**Steps**: Trigger RPC failure (e.g., createCompany with no profile)
**Expected**: Snackbar shows specific error for debugging
**Actual**: Generic "Failed to create company" shown; actual Supabase error (`No profile found`) is caught and discarded. Snackbar disappears quickly — easy to miss.
**Fix**: Include `e.toString()` in error messages (at least in debug mode). Consider longer snackbar duration.
**File**: `auth_provider.dart:411-416` (createCompany), `auth_provider.dart:384-388` (updateProfile)

### F-BUILD-02: Supabase Credentials Not Passable via dart-mcp launch_app
**Status**: NOTED (workaround applied)
**Severity**: LOW (testing only)
**Steps**: Try to launch app with `--dart-define` via dart-mcp `launch_app` tool
**Expected**: Can pass dart-defines to configure Supabase
**Actual**: `launch_app` doesn't support `--dart-define` parameter
**Workaround Applied**: Temporarily hardcoded Supabase URL/key as defaultValues in `supabase_config.dart`
**TODO**: Revert hardcoded credentials after testing

---

## Progress Tracking

| Phase | Status | Notes |
|-------|--------|-------|
| App Launch | DONE | CMake fix applied, app runs on Windows |
| Auth Flow Testing | IN PROGRESS | F-AUTH-01 FIXED, INSERT policy FIXED, routing FIXED (needs rebuild to verify) |
| Project Flow Testing | NOT STARTED | Blocked until auth onboarding completes |
| Admin Flow Testing | NOT STARTED | |
| Settings Testing | NOT STARTED | |
| Sync Testing | NOT STARTED | |
| Navigation Testing | PARTIAL | Bottom nav verified, auth guard verified |
| Entry Flow Testing | NOT STARTED | |
| Toolbox Testing | NOT STARTED | |

---

### F-RLS-01: Missing INSERT Policy on user_profiles (FIXED)
**Status**: FIXED (Session 456)
**Severity**: CRITICAL
**Steps**: 1) Login as pre-existing user with backfilled profile row, 2) Fill profile, 3) Tap Continue
**Expected**: Profile upserted to Supabase
**Actual**: `PostgrestException: new row violates row-level security policy for table "user_profiles"` — Supabase `upsert()` issues `INSERT ... ON CONFLICT DO UPDATE`, which requires INSERT permission at RLS level even when row exists.
**Fix Applied**: Created migration `20260222400000_add_profile_insert_policy.sql`: `CREATE POLICY "insert_own_profile" ON user_profiles FOR INSERT TO authenticated WITH CHECK (id = auth.uid())`
**Deployed**: Yes (via `supabase db push`)

### F-AUTH-06: createCompany Doesn't Refresh Local Profile State
**Status**: FIXED (Session 456, code change NOT committed)
**Severity**: HIGH
**Steps**: 1) Create company on company-setup screen, 2) App navigates to `/`
**Expected**: Router sees status=approved, routes to dashboard
**Actual**: Router sees stale status=pending (local `_userProfile` not refreshed after RPC), redirects to `/pending-approval`
**Root Cause**: `AuthProvider.createCompany()` only updated `_company`, not `_userProfile`. The `create_company` RPC sets `status='approved', role='admin'` server-side, but the client never re-fetched the profile.
**Fix Applied**: Added `await loadUserProfile()` after `_authService.createCompany(name)` in `auth_provider.dart:409`

### F-AUTH-07: Wrong Supabase Anon Key Hardcoded
**Status**: FIXED (Session 456, code change NOT committed)
**Severity**: CRITICAL
**Steps**: Build app, observe "[ConfigValidator] WARNING: SUPABASE_ANON_KEY appears too short"
**Expected**: Supabase client authenticates and loads user profile
**Actual**: `sb_publishable_lmDJCE9_vCmNkzhY6W6L0g_cF6Mo0JP` is NOT the JWT anon key — it's a different key type. Real anon key is `eyJhbG...` (~200 chars). With wrong key, Supabase session doesn't restore and no profile loads.
**Fix Applied**: Replaced with correct JWT anon key in `supabase_config.dart:22`
**Note**: Both keys are still hardcoded as `defaultValue` — MUST be reverted to empty strings after testing

### F-AUTH-08: Onboarding Routes Don't Redirect Approved Users
**Status**: FIXED (Session 456, code change NOT committed)
**Severity**: HIGH
**Steps**: 1) Approved user with company restarts app, 2) Profile loads async (initially null), 3) Router redirects to /profile-setup, 4) Profile finishes loading (status=approved)
**Expected**: go_router re-evaluates, redirects to `/`
**Actual**: `/profile-setup` is in `_kOnboardingRoutes` which returned `null` unconditionally — user stays stuck on profile-setup
**Fix Applied**: Added check in router: if on onboarding route AND profile is approved+has company, redirect to `/`
**File**: `lib/core/router/app_router.dart:115-125`
**Status of fix**: NOT yet verified (needs full rebuild to pick up const key change)

### F-AUTH-05: Backfill Migration Deployed Successfully
**Status**: FIXED
**Severity**: N/A (deployment fix for F-AUTH-01)
**Action**: Created `supabase/migrations/20260222300000_backfill_user_profiles.sql` and pushed. Inserts user_profiles rows for all auth.users missing them.

### F-BUILD-03: native_assets/windows/ Directory Missing After Stop/Relaunch
**Status**: NOTED (recurring)
**Severity**: MEDIUM (blocks Windows rebuilds)
**Steps**: Stop app via dart-mcp, then relaunch
**Expected**: Build succeeds
**Actual**: cmake install fails with MSB3073 because `build/native_assets/windows/` doesn't exist
**Workaround**: Run `mkdir -p build/native_assets/windows` before building. But the directory gets deleted when build cache is cleaned.
**Root Cause**: Flutter Windows build assumes native_assets dir exists but doesn't create it. Only matters on first build after clean.
**Note**: Using `flutter build windows --debug` first, THEN `launch_app` avoids this since build creates the dir.

---

## Context Notes (for compaction survival)
- **Last test completed**: T-AUTH-04 (PASS), T-AUTH-05 (PASS after INSERT policy), T-AUTH-06 (FAIL — routing bugs, 3 fixes applied but not yet verified)
- **Next test to run**: Full rebuild (flutter clean was done, need `flutter build windows --debug --target lib/driver_main.dart`), then launch, verify T-AUTH-06 (create company → home), continue T-AUTH-07 through T-AUTH-10
- **App state**: STOPPED. Needs full rebuild (const changes in supabase_config.dart).
- **Build strategy**: Always `mkdir -p build/native_assets/windows` then `pwsh flutter build windows --debug --target lib/driver_main.dart`, then `launch_app`
- **Temp changes in code** (MUST REVERT after testing):
  1. `supabase_config.dart` — hardcoded Supabase URL + JWT anon key as defaultValues
  2. `auth_provider.dart:413,387` — added `debugPrint` + detailed error in `$e` for createCompany and updateProfile
- **Permanent changes** (KEEP):
  1. `windows/CMakeLists.txt:4` — CMAKE_POLICY_VERSION_MINIMUM for Firebase CMake compat
  2. `profile_setup_screen.dart` — ValueKeys on name + cert fields
  3. `company_setup_screen.dart` — ValueKeys on company name + search fields
  4. `supabase/migrations/20260222300000_backfill_user_profiles.sql` — backfill for pre-existing users
  5. `supabase/migrations/20260222400000_add_profile_insert_policy.sql` — INSERT policy for user_profiles
  6. `auth_provider.dart:409` — `await loadUserProfile()` after createCompany (profile refresh)
  7. `app_router.dart:115-125` — redirect approved users off onboarding routes
- **Findings so far**: F-BUILD-01 (CMake fix), F-AUTH-01 (pre-existing profiles FIXED), F-AUTH-02 (cert label vague), F-AUTH-03 (missing test keys), F-AUTH-04 (errors swallowed), F-AUTH-05 (backfill deployed), F-RLS-01 (INSERT policy FIXED), F-AUTH-06 (stale profile FIXED), F-AUTH-07 (wrong anon key FIXED), F-AUTH-08 (onboarding redirect FIXED), F-BUILD-02 (dart-define workaround), F-BUILD-03 (native_assets dir)
- **Task list**: Task #1 in progress (auth, 7/10 done), Tasks #2-4 pending, Task #5 pending (revert+report)

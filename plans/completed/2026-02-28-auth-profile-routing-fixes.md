# Auth Profile & Routing Fixes: Stale Session, Router Timing, RLS Upsert

**Created**: 2026-02-28
**Status**: DRAFT — awaiting approval
**Resolves**: FK violation (23503), router timing redirect, RLS upsert violation (42501)
**Priority**: HIGH — profile setup and post-login routing are broken

---

## Problem Statement

Three interconnected bugs in the auth/profile flow:

1. **FK Violation (23503)**: After a DB reset (or if a user is deleted server-side), the app holds a stale cached JWT with a UUID that no longer exists in `auth.users`. Any upsert to `user_profiles` using that UUID fails with "Key is not present in table 'users'".

2. **Router Timing**: `loadUserProfile()` is async, but the router evaluates immediately on `notifyListeners()` before the profile loads. It sees `profile == null` and incorrectly redirects to `/profile-setup`, even for users who already have a profile and company.

3. **RLS Upsert (42501)**: `toJson()` serializes locked columns (`role`, `status`, `company_id`) into the upsert payload. The `update_own_profile` policy's `WITH CHECK` clause validates these haven't changed, but including them in the payload triggers the check unnecessarily and can cause failures.

---

## Implementation Steps

### Phase 1: Fix Router Timing (prevents incorrect redirects)

**File**: `lib/core/router/app_router.dart`

1. Add an `isLoadingProfile` guard **before** the `profile == null` check in the redirect function (~line 139):

```dart
if (isAuthenticated && SupabaseConfig.isConfigured) {
  // Don't make profile-based routing decisions while profile is loading.
  // GoRouter will re-evaluate when loadUserProfile() completes and
  // notifyListeners() fires again.
  if (_authProvider.isLoadingProfile) return null;

  final profile = _authProvider.userProfile;
  // ... existing profile == null check follows
}
```

This ensures the router treats "loading" differently from "doesn't exist".

### Phase 2: Remove Premature notifyListeners() in signIn/signUp

**File**: `lib/features/auth/presentation/providers/auth_provider.dart`

1. In `signIn()` (~line 237): Remove `notifyListeners()` before `await loadUserProfile()`. The `loadUserProfile()` method already calls `notifyListeners()` twice internally (once when setting `_isLoadingProfile = true`, once in `finally`).

2. In `signUp()` (~line 191): Same — remove `notifyListeners()` before `await loadUserProfile()`.

**Before** (both methods):
```dart
_currentUser = response.user;
notifyListeners();           // <-- remove this
await loadUserProfile();
```

**After**:
```dart
_currentUser = response.user;
await loadUserProfile();
```

This eliminates the window where the router sees `isAuthenticated = true` + `profile == null` + `isLoadingProfile == false`.

### Phase 3: Fix Stale Session Detection

**File**: `lib/features/auth/presentation/providers/auth_provider.dart`

1. In `loadUserProfile()`, after the profile fetch returns null, attempt to validate the session is still live on the server. If the session is stale (user deleted server-side), sign out to clear the cached JWT.

Add after the profile fetch (inside `loadUserProfile()`, after the try/catch that fetches the profile):

```dart
if (_userProfile == null && _currentUser != null) {
  // Profile not found — verify the session is still valid server-side.
  // If the user was deleted (e.g., DB reset), refreshSession() will throw.
  try {
    await _authService.refreshSession();
  } on AuthException {
    // Session is stale — user no longer exists server-side.
    await signOut();
    return;
  }
}
```

2. Add `refreshSession()` to `AuthService` if it doesn't already exist:

**File**: `lib/features/auth/services/auth_service.dart`

```dart
/// Re-validate the current session against the server.
/// Throws [AuthException] if the session is invalid or the user no longer exists.
Future<void> refreshSession() async {
  await _client.auth.refreshSession();
}
```

### Phase 4: Fix RLS Upsert — Strip Locked Columns

**File**: `lib/features/auth/data/models/user_profile.dart`

1. Add a `toUpsertJson()` method that only includes user-editable fields:

```dart
/// Serialize only user-editable fields for Supabase upsert.
/// Locked fields (role, status, company_id, last_synced_at) are managed
/// server-side via RPCs and must not be included in the upsert payload.
Map<String, dynamic> toUpsertJson() {
  return {
    'id': userId,
    if (displayName != null) 'display_name': displayName,
    if (certNumber != null) 'cert_number': certNumber,
    if (phone != null) 'phone': phone,
    if (position != null) 'position': position,
    'updated_at': DateTime.now().toUtc().toIso8601String(),
  };
}
```

**File**: `lib/features/auth/data/datasources/remote/user_profile_remote_datasource.dart`

2. Change the upsert call to use `toUpsertJson()`:

```dart
Future<void> upsert(UserProfile profile) async {
  await _client.from(_table).upsert(profile.toUpsertJson());
}
```

This means the INSERT path sends only `id` + editable fields (passes `insert_own_profile` policy). The UPDATE path omits locked columns entirely, so `update_own_profile` WITH CHECK passes trivially (no change to locked values).

### Phase 5: Verify INSERT Policy Exists in Production

**Manual step** — run in Supabase Dashboard SQL Editor:

```sql
SELECT policyname, cmd FROM pg_policies WHERE tablename = 'user_profiles';
```

Confirm `insert_own_profile` exists with `cmd = INSERT`. If missing, run:

```sql
CREATE POLICY "insert_own_profile" ON user_profiles
  FOR INSERT TO authenticated
  WITH CHECK (id = auth.uid());
```

This was added in migration `20260222400000` but should be verified on the live instance.

---

## Files Modified

| File | Change |
|------|--------|
| `lib/core/router/app_router.dart` | Add `isLoadingProfile` guard before profile-based redirects |
| `lib/features/auth/presentation/providers/auth_provider.dart` | Remove premature `notifyListeners()` in signIn/signUp; add stale session detection in `loadUserProfile()` |
| `lib/features/auth/services/auth_service.dart` | Add `refreshSession()` method (if not already present) |
| `lib/features/auth/data/models/user_profile.dart` | Add `toUpsertJson()` omitting locked columns |
| `lib/features/auth/data/datasources/remote/user_profile_remote_datasource.dart` | Use `toUpsertJson()` instead of `toJson()` |

## Files NOT Modified

| File | Why |
|------|-----|
| `supabase/migrations/*` | No schema changes needed — existing policies are correct |
| `lib/features/auth/presentation/screens/*` | Screen code is fine — bugs are in routing/data layer |

## Testing

### Test 1: Fresh signup flow
1. Clear app data → open app → Register new account
2. Should see profile setup screen (no flash/jitter)
3. Fill in fields → Save → should proceed to company setup
4. Create company → should land on dashboard

### Test 2: Existing user login
1. Log out → log back in
2. Should go directly to dashboard (no profile-setup flash)
3. No errors in logs

### Test 3: Stale session detection (simulates DB reset)
1. Log in successfully
2. Delete the user from Supabase Dashboard
3. Kill and restart the app
4. App should detect stale session → redirect to login (not crash or show profile setup)

### Test 4: Profile update
1. Go to Settings → Edit Profile
2. Change display name → Save
3. Should succeed without RLS errors

## Agent Assignments

| Phase | Agent | Files |
|-------|-------|-------|
| 1 | frontend-flutter-specialist-agent | app_router.dart |
| 2 | frontend-flutter-specialist-agent | auth_provider.dart |
| 3 | auth-agent | auth_provider.dart, auth_service.dart |
| 4 | backend-data-layer-agent | user_profile.dart, user_profile_remote_datasource.dart |
| 5 | Manual | Supabase Dashboard SQL Editor |

## Estimated Scope

- ~5 lines added (router guard)
- ~2 lines removed (premature notifyListeners)
- ~15 lines added (stale session detection + refreshSession)
- ~15 lines added (toUpsertJson)
- ~1 line changed (datasource upsert call)
- Net: ~35 lines added, 5 files touched

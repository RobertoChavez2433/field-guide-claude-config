# Auth Agent Memory

## Auth Flow Overview

```
App Start
  → AuthProvider constructor
    → If cached session exists: set _isLoadingProfile=true, call loadUserProfile()
    → If passwordRecoveryActive persisted: restore _isPasswordRecovery=true
    → Subscribe to authStateChanges stream

Sign In
  → AuthProvider.signIn()
    → Company-switch guard: compare cached company_id vs incoming profile
    → If company mismatch: AuthService.clearLocalCompanyData()
    → loadUserProfile(preloadedProfile: guardProfile)

Sign Up
  → AuthProvider.signUp()
    → On success: loadUserProfile()
    → Email verification via deep link: com.fieldguideapp.inspector://login-callback

Password Reset (OTP flow)
  1. AuthProvider.resetPassword(email) → sends OTP email
  2. User reads 6-digit code from email
  3. AuthProvider.verifyRecoveryOtp(email, otp) → Supabase fires passwordRecovery event
  4. Router traps user on /update-password
  5. AuthProvider.updatePassword(newPassword)
  6. AuthProvider.completePasswordRecovery() → signs out recovery session

Sign Out
  → AuthProvider.signOut()
    → AuthService.signOut() (invalidates Supabase session + clears SharedPreferences user keys)
    → BackgroundSyncHandler.dispose()
    → Clear secure storage (last_active_at)
    → Clear in-memory: user, profile, company, attributionRepository cache
    → Does NOT clear local SQLite data (BUG-17 fix)
```

## Session Management

### Persistent Recovery Flag

`isPasswordRecovery` is persisted to `PreferencesService` via `setPasswordRecoveryActive()` / `clearPasswordRecoveryActive()`. On cold start, `AuthProvider` restores this flag synchronously before subscribing to the auth stream. This prevents the router from redirecting away from `/update-password` if the app was killed during a recovery session.

### Cold-Start Race Condition

If a cached session exists at `AuthProvider` construction, `_currentUser` is already non-null. The auth state listener's `previousUser == null` guard would never fire, so profile load would be skipped. Fix: set `_isLoadingProfile = true` and call `loadUserProfile()` synchronously in the constructor.

### Inactivity Timeout

`_inactivityThreshold = Duration(days: 7)`. `last_active_at` stored in `FlutterSecureStorage`. Call `updateLastActive()` on foreground resume. `checkInactivityTimeout()` signs out if threshold exceeded.

### Stale Session Detection

After `loadUserProfile()`, if profile is null but user is authenticated, call `refreshSession()`. If `AuthException` is thrown, the user was deleted server-side — sign out.

## Password Reset Flow Details

### OTP-Based (Current Implementation)

Password reset uses 6-digit OTP codes, NOT deep links:

```dart
// Step 1: Send OTP email
await _client.auth.resetPasswordForEmail(email, redirectTo: redirectUrl);

// Step 2: User enters OTP code in app
await _client.auth.verifyOTP(
  email: email,
  token: otp,         // raw 6-digit code from email
  type: OtpType.recovery,
);

// Step 3: On success, Supabase fires AuthChangeEvent.passwordRecovery
// Step 4: Update password
await _client.auth.updateUser(UserAttributes(password: newPassword));
```

### `secure_password_change=true`

Configured in Supabase `config.toml` (not via SQL). This setting requires the user to complete the recovery flow before other actions are allowed in the session.

### PASSWORD_RECOVERY Event Pattern

```dart
_authSubscription = _authService.authStateChanges.listen((state) {
  // [SEC-7] Check event BEFORE updating _currentUser
  if (state.event == AuthChangeEvent.passwordRecovery) {
    _isPasswordRecovery = true;
    _currentUser = state.session?.user;
    _preferencesService?.setPasswordRecoveryActive();
    notifyListeners();
    return; // Skip profile load — user must update password first
  }
  // ... normal auth state handling
});
```

### Complete Recovery

`completePasswordRecovery()` clears the persisted flag BEFORE calling `signOut()`. This prevents the app from being permanently stuck on `/update-password` if a crash occurs during sign-out.

## Deep Links

```
com.fieldguideapp.inspector://login-callback
```

Used for email verification on sign-up. Must match AndroidManifest.xml intent filter. Deep link token exchange is handled by `supabase_flutter` when `AuthFlowType.pkce` is configured. Do NOT add custom deep link handlers.

## Role-Based Permissions

| Role | `canManageProjects` | `canEditFieldData` | Notes |
|------|--------------------|--------------------|-------|
| admin | yes | yes | Can delete any project |
| engineer | yes | yes | Can delete own projects only |
| inspector | no | yes | Field data only |
| viewer | no | no | Read-only |

### Permission Methods on AuthProvider

- `isAuthenticated` — user is logged in
- `isApproved` — `MembershipStatus.approved`
- `isAdmin` — role == admin
- `isEngineer` — role == engineer
- `canManageProjects` — approved + (admin OR engineer)
- `canEditFieldData` — approved + any edit role
- `canEditEntry({createdByUserId})` — only entry creator can edit (null = legacy, allow any approved editor)
- `canCreateProject` — delegates to `canManageProjects`
- `canDeleteProject({createdByUserId})` — admin can delete any; engineer can delete own

## Cache and Sign-Out Behavior

### What IS cleared on sign-out
- In-memory: `_currentUser`, `_userProfile`, `_company`, `attributionRepository`
- SecureStorage: `last_active_at`
- SharedPreferences: keys prefixed `last_project_`, `recent_projects_`, `inspector_`
- PreferencesService: `passwordRecoveryActive` flag

### What is NOT cleared on sign-out
- Local SQLite data (projects, entries, photos, etc.) — preserved for re-login
- Only cleared on company switch (cross-company data isolation) or explicit delete

### Company-Switch Guard

On `signIn()`, if cached company in SQLite differs from the incoming user's company, `AuthService.clearLocalCompanyData()` wipes all 17 data tables. This prevents cross-company data leakage on device handoff.

## AuthService

Thin wrapper around `SupabaseClient.auth`. Does NOT hold state — all state lives in `AuthProvider`.

| Method | Description |
|--------|-------------|
| `signUp(email, password, fullName?)` | Creates account, sends verification email |
| `signIn(email, password)` | Signs in via password |
| `signOut()` | Signs out + clears user SharedPreferences keys |
| `resetPassword(email)` | Sends OTP recovery email |
| `verifyRecoveryToken(email, token)` | Verifies OTP, fires passwordRecovery event |
| `updatePassword(newPassword)` | Updates password (requires active session) |
| `refreshSession()` | Re-validates session against server |
| `loadUserProfile(userId)` | Fetches UserProfile from Supabase |
| `updateUserProfile(profile)` | Upserts profile to Supabase |
| `createCompany(name)` | Creates company via `create_company` RPC |
| `joinCompany(companyId)` | Submits join request |
| `saveFcmToken(userId, token)` | Saves FCM push token (upsert to `user_fcm_tokens`) |

## User Profile Sync

`UserProfileSyncDatasource` pulls approved company members after each successful sync:

1. Ensures company row exists locally (FK constraint: `user_profiles.company_id -> companies.id`)
2. Fetches all `status=approved` profiles for `company_id` from Supabase
3. Upserts each profile to local `user_profiles` table

`updateLastSyncedAt(userId)` uses a SECURITY DEFINER RPC because RLS blocks client-side update of `last_synced_at`.

## Mock Auth Mode

Enabled with `--dart-define=MOCK_AUTH=true`. Mock mode never runs in release builds (assert guard). Mock credentials:
- Email: `test@example.com`
- Password: `Test123!`
- UserId: `test-user-001`
- Role: admin, status: approved

Mock mode bypasses all Supabase calls. Use `TestModeConfig.useMockAuth` to branch.

**WARNING**: `assert()` guards are stripped in release builds. Verify `TestModeConfig.useMockAuth` has a `kReleaseMode` runtime check, not just an assert.

## Token Storage

- Supabase session tokens: managed by `supabase_flutter` SDK
- `last_active_at`: `flutter_secure_storage` (key: `last_active_at`)
- FCM tokens: stored in `user_fcm_tokens` table (separate from `user_profiles` to prevent token leakage to company members)
- NEVER log tokens or passwords

## Error Handling

`_parseAuthError(message)` maps Supabase error strings to user-friendly messages:

| Supabase message | User message |
|-----------------|--------------|
| Invalid login credentials | Incorrect email or password |
| User already registered | An account with this email already exists |
| Email not confirmed | Please verify your email before signing in |
| Password should be | Password must be at least 8 characters... |

`_parseOtpError(message)` maps OTP errors:

| Pattern | User message |
|---------|-------------|
| expired / otp_expired | Code expired. Please request a new one. |
| invalid / not found | Invalid code. Please check and try again. |

## Common Gotchas

- **`previousUser == null` guard in auth listener**: Only loads profile when transitioning from unauthenticated to authenticated via stream. Cold-start path (constructor) bypasses this — handled separately.
- **`forceReauthOnly()`**: Invalidates Supabase session token (so SDK doesn't auto-restore it) but does NOT wipe SQLite data. Used during app upgrades.
- **`signOutLocally()`**: Same as `signOut()` but does NOT call Supabase. Used when Supabase URL changed between app versions.
- **Company row must exist before profile upsert**: `user_profiles` has FK to `companies`. Always ensure company is in local SQLite before upserting user_profiles.
- **Attribution cache**: `UserAttributionRepository` maps userId → display name for audit trail. Cleared on sign-out, seeded on profile load.
- **FCM token isolation**: Stored in `user_fcm_tokens`, NOT in `user_profiles`. Prevents company members from seeing each other's push tokens.
- **Logging**: Use `Logger.auth(...)` for all auth-related log statements. NEVER log passwords, tokens, or session data.

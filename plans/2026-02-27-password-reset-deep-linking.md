# BLOCKER-13: Password Reset Deep Linking — Implementation Plan

**Created**: 2026-02-27 | **Session**: 461
**Status**: APPROVED — security review incorporated
**Security Review**: Completed 2026-02-27 (15 findings: 1 CRITICAL, 4 HIGH, 4 MEDIUM, 3 LOW, 2 INFO)

## Problem Statement

Tapping the password reset link in email opens `about:blank` in Chrome instead of returning to the app. The entire password reset flow is broken end-to-end: even if deep linking worked, there is no screen to collect the new password, and no routing logic to detect the `PASSWORD_RECOVERY` auth event.

## Root Cause Analysis

Four distinct problems identified:

| # | Problem | Location | Severity |
|---|---------|----------|----------|
| 1 | **PKCE/fragment mismatch** — `_handleDeepLink` checks for `access_token` in URL fragment, but PKCE flow sends `code` as a query parameter. `recoverSession()` is never called. | `main.dart:494-504` | BLOCKER |
| 2 | **No "update password" screen** — after successful deep link, no screen exists to collect the new password. | Missing file | BLOCKER |
| 3 | **No `PASSWORD_RECOVERY` event routing** — AuthProvider and AppRouter don't detect `PASSWORD_RECOVERY` event from Supabase, so user lands on dashboard instead of password update screen. | `auth_provider.dart:44-56`, `app_router.dart:79-170` | BLOCKER |
| 4 | **iOS has no URL scheme** — `Info.plist` has no `CFBundleURLTypes` entry for `com.fieldguideapp.inspector`. | `ios/Runner/Info.plist` | BLOCKER (iOS) |

## Key Design Decision: Let `supabase_flutter` Handle PKCE

`supabase_flutter` (v2.12.0) with `AuthFlowType.pkce` already:
- Registers its own `app_links` listener internally
- Exchanges the `code` query parameter for tokens automatically
- Fires `AuthChangeEvent.passwordRecovery` on the `onAuthStateChange` stream

Our custom `_handleDeepLink` in `main.dart:461-517` is **redundant and conflicting**. With PKCE, `supabase_flutter` intercepts the deep link, exchanges the code, and fires the auth state event — all before our custom handler runs. The custom handler then tries to parse a fragment that doesn't exist (PKCE uses query params, not fragments).

**Plan**: Remove the custom deep link handler entirely. Let `supabase_flutter` handle token exchange. Focus our code on reacting to the `PASSWORD_RECOVERY` auth event.

## Implementation Steps

### Step 1: Remove Custom Deep Link Handler

**File**: `lib/main.dart`

- Delete `_initDeepLinkHandler()` function (lines 461-482)
- Delete `_handleDeepLink()` function (lines 484-517)
- Delete the `_initDeepLinkHandler()` call (line 158)
- Remove `import 'package:app_links/app_links.dart';` (line 9) — `supabase_flutter` handles this internally

**Rationale**: `supabase_flutter` with PKCE already handles the deep link -> code exchange -> session creation pipeline. Our custom handler was written for the legacy implicit flow (fragment-based `access_token`) and is now dead code that silently fails.

**[SEC-2]**: This also eliminates the `debugPrint('Deep link received: $uri')` at line 486, which logged the full URI including the PKCE authorization code to the console.

### Step 2: Remove `autoVerify` From Android Manifest

**File**: `android/app/src/main/AndroidManifest.xml`

**[SEC-4]**: Remove `android:autoVerify="true"` from the custom-scheme intent filter (line 53). `autoVerify` only works with `https://` App Links, not custom URL schemes — it is silently ignored and gives a false sense of security.

Change:
```xml
<intent-filter android:autoVerify="true">
```
To:
```xml
<!-- Custom URL scheme: autoVerify not applicable (only works with https App Links) -->
<intent-filter>
```

### Step 3: Add `updatePassword()` to AuthService

**File**: `lib/features/auth/services/auth_service.dart`

**[SEC-11]**: Route the password update through `AuthService` to maintain the service layer pattern. All other auth operations go through `AuthService` -> `AuthProvider`.

```dart
/// Update the current user's password.
///
/// Requires an active session (e.g., from a PASSWORD_RECOVERY event).
/// Throws [StateError] if Supabase is not configured.
/// Throws [AuthException] if the update fails.
Future<void> updatePassword(String newPassword) async {
  if (_client == null) {
    throw StateError(
      'Supabase not configured. Cannot update password without credentials.',
    );
  }
  await _client.auth.updateUser(
    UserAttributes(password: newPassword),
  );
}
```

### Step 4: Add `PASSWORD_RECOVERY` Event Detection to AuthProvider

**File**: `lib/features/auth/presentation/providers/auth_provider.dart`

Add a new field and update the auth state listener.

**[SEC-7]**: Check the event type BEFORE setting `_currentUser` to prevent a race condition where `signedIn` fires before `passwordRecovery`, causing a brief flash of dashboard access. When recovery is detected, skip `loadUserProfile()` — the user should not access data during recovery.

```dart
// New field
bool _isPasswordRecovery = false;
bool get isPasswordRecovery => _isPasswordRecovery;

// Updated listener (replaces lines 44-57)
_authSubscription = _authService.authStateChanges.listen((state) {
  final previousUser = _currentUser;

  // [SEC-7] Check event type BEFORE updating _currentUser
  // to prevent race condition with router evaluation
  if (state.event == AuthChangeEvent.passwordRecovery) {
    _isPasswordRecovery = true;
    _currentUser = state.session?.user;
    // Skip loadUserProfile — user must update password first
    notifyListeners();
    return;
  }

  _currentUser = state.session?.user;

  if (_currentUser == null) {
    _userProfile = null;
    _company = null;
    _isPasswordRecovery = false;
    attributionRepository.clearCache();
  } else if (previousUser == null && _currentUser != null) {
    // Don't load profile if in password recovery mode
    if (!_isPasswordRecovery) {
      loadUserProfile();
    }
  }
  notifyListeners();
});
```

Add a method for post-update sign-out:

**[SEC-3]**: After successful password update, call `signOut()` to destroy the recovery session entirely. The user must re-authenticate with their new password. This prevents a recovery session JWT from being used for full app access.

```dart
/// Complete the password recovery flow.
/// Signs out to destroy the recovery session, forcing re-login with new credentials.
Future<void> completePasswordRecovery() async {
  _isPasswordRecovery = false;
  await _authService.signOut();
  // signOut triggers the auth state listener, which clears _currentUser etc.
}
```

### Step 5: Create `UpdatePasswordScreen`

**File**: `lib/features/auth/presentation/screens/update_password_screen.dart`

New screen with:
- Two `TextFormField`s: "New Password" and "Confirm Password"
- Password visibility toggle (per-field)
- Pop prevention via `PopScope(canPop: false)` — user must complete or cancel
- No back button in AppBar
- Cancel button signs user out and returns to `/login`
- Follows UI patterns from `forgot_password_screen.dart` (theme, spacing, TestingKeys)

**Password validation rules** **[SEC-6]**:
- Minimum 8 characters
- At least one uppercase letter
- At least one digit
- New password and confirm must match
- Display requirements as helper text below the field

**Submit flow** **[SEC-3]**:
1. Validate form client-side
2. Call `authProvider.updatePassword(newPassword)` (via AuthService)
3. **Never log or persist the password in any variable beyond the controller**
4. **[SEC-12]** Clear `TextEditingController`s immediately after successful API call
5. Call `authProvider.completePasswordRecovery()` — this signs out, destroying the recovery session
6. Show success snackbar: "Password updated. Please sign in with your new password."
7. Navigate to `/login`

**Error handling**:
- `AuthException` → display user-friendly error in snackbar
- Generic exception → "Something went wrong. Please try again."
- **[SEC-9]** If the recovery session has expired (token refresh fails), show: "Your reset link has expired. Please request a new one." and navigate to `/forgot-password`

### Step 6: Add Router Integration

**File**: `lib/core/router/app_router.dart`

6a. Add `/update-password` to route sets:

```dart
const _kOnboardingRoutes = {
  '/profile-setup',
  '/company-setup',
  '/pending-approval',
  '/account-status',
  '/update-password',  // NEW
};

const _kNonRestorableRoutes = {
  '/profile-setup',
  '/company-setup',
  '/pending-approval',
  '/account-status',
  '/edit-profile',
  '/admin-dashboard',
  '/update-password',  // NEW
};
```

6b. Add redirect logic for `PASSWORD_RECOVERY` as the **first check** after the config bypass block (after line 93, before line 94). This placement ensures recovery mode is enforced before any auth-route or profile-based routing can redirect elsewhere.

**[SEC-3, SEC-7]**: This traps ALL routes — including deep links to arbitrary paths like `/projects/123` — when in recovery mode.

```dart
// [SEC-3] Password recovery mode — trap user on update-password screen.
// Must be FIRST check after config bypass to prevent any route escape.
if (_authProvider.isPasswordRecovery) {
  if (location == '/update-password') return null;
  return '/update-password';
}
```

6c. Add the route definition (alongside other auth routes, after line 189):

```dart
GoRoute(
  path: '/update-password',
  name: 'updatePassword',
  builder: (context, state) => const UpdatePasswordScreen(),
),
```

### Step 7: Add iOS URL Scheme

**File**: `ios/Runner/Info.plist`

Add `CFBundleURLTypes` entry inside the top-level `<dict>`:

```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleTypeRole</key>
    <string>Editor</string>
    <key>CFBundleURLName</key>
    <string>com.fieldguideapp.inspector</string>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>com.fieldguideapp.inspector</string>
    </array>
  </dict>
</array>
```

### Step 8: Add 60s Cooldown to ForgotPasswordScreen

**File**: `lib/features/auth/presentation/screens/forgot_password_screen.dart`

**[SEC-5]**: Add client-side rate limiting to prevent rapid reset email spam.

- Add a `Timer` field and `_cooldownSeconds` counter
- After successful send, disable the button for 60 seconds with countdown text: "Resend in 42s"
- Dispose the timer in `dispose()`
- Handle HTTP 429 errors with message: "Please wait before requesting another reset."

### Step 9: Update Auth Screens Barrel Export

**File**: `lib/features/auth/presentation/screens/screens.dart`

Add export for the new screen:

```dart
export 'update_password_screen.dart';
```

### Step 10: Add Testing Keys

**File**: `lib/shared/testing_keys/auth_keys.dart`

Add keys for the new screen:

```dart
// Update Password Screen
static const updatePasswordScreenTitle = Key('updatePasswordScreenTitle');
static const updatePasswordNewField = Key('updatePasswordNewField');
static const updatePasswordConfirmField = Key('updatePasswordConfirmField');
static const updatePasswordSubmitButton = Key('updatePasswordSubmitButton');
static const updatePasswordCancelButton = Key('updatePasswordCancelButton');
static const updatePasswordVisibilityToggle = Key('updatePasswordVisibilityToggle');
static const updatePasswordConfirmVisibilityToggle = Key('updatePasswordConfirmVisibilityToggle');
```

### Step 11: Supabase Dashboard Configuration (Manual)

Verify in the Supabase dashboard (https://supabase.com/dashboard):

1. **Authentication > URL Configuration > Redirect URLs**: Ensure `com.fieldguideapp.inspector://login-callback` is in the allowlist
2. **Authentication > Email Templates > Reset Password**: Verify the template uses `{{ .ConfirmationURL }}` which Supabase auto-appends the redirect
3. **[SEC-5] Authentication > Rate Limits**: Verify email rate limit is configured (recommend: 1 per 60s per email, 5 per hour per IP)
4. **[SEC-5] Authentication > Settings > Security**: Enable "Do not disclose email existence" to prevent account enumeration via reset endpoint
5. **[SEC-6] Authentication > Password Requirements**: Configure minimum 8 characters, require uppercase, require digit

### Step 12: Update Stale Documentation

**File**: `.claude/rules/auth/supabase-auth.md`
- Update callback URL from `com.fvconstruction.construction_inspector://login-callback` to `com.fieldguideapp.inspector://login-callback`
- Remove the `recoverSession(fragment)` code example — `supabase_flutter` handles PKCE internally
- Add note: "Deep link token exchange is handled by `supabase_flutter` when `AuthFlowType.pkce` is configured. Do not add custom deep link handlers."
- Update the Handle Auth Callback section with the new `PASSWORD_RECOVERY` event pattern

## Security Considerations

| # | Category | Detail |
|---|----------|--------|
| 1 | **PKCE flow** | Authorization code exchange uses proof key (code_verifier/code_challenge), preventing interception. Handled entirely by `supabase_flutter`. |
| 2 | **Recovery session scoping** | Router traps user on `/update-password` for ALL routes. Recovery session is destroyed via `signOut()` after password update. User must re-authenticate. [SEC-3] |
| 3 | **No password logging** | Password never logged, printed, or persisted. Controllers cleared immediately after API call. [SEC-12] |
| 4 | **Custom URL scheme risk** | PKCE mitigates code interception. `autoVerify` removed (was no-op). App Links / Universal Links tracked as follow-up. [SEC-4] |
| 5 | **Rate limiting** | Client-side 60s cooldown on reset requests + Supabase server-side rate limits verified. [SEC-5] |
| 6 | **Password complexity** | Client-side: 8+ chars, uppercase, digit. Server-side: Supabase dashboard configured to match. [SEC-6] |
| 7 | **Race condition prevention** | Event type checked before `_currentUser` update. Profile load skipped during recovery. [SEC-7] |
| 8 | **Cancel = sign out** | Destroys recovery session entirely. |
| 9 | **Pop prevention** | `PopScope(canPop: false)` prevents back-nav to dashboard. |
| 10 | **Expired link handling** | Auth exceptions caught and user shown "link expired" message. [SEC-9] |

## Files Modified

| File | Change |
|------|--------|
| `lib/main.dart` | Remove `_initDeepLinkHandler()`, `_handleDeepLink()`, and `app_links` import |
| `android/app/src/main/AndroidManifest.xml` | Remove `autoVerify="true"` from custom scheme intent filter |
| `lib/features/auth/services/auth_service.dart` | Add `updatePassword()` method |
| `lib/features/auth/presentation/providers/auth_provider.dart` | Add `isPasswordRecovery` flag, race-condition-safe listener, `completePasswordRecovery()` |
| `lib/features/auth/presentation/screens/update_password_screen.dart` | **NEW** — Update password form with complexity validation |
| `lib/features/auth/presentation/screens/screens.dart` | Add barrel export |
| `lib/features/auth/presentation/screens/forgot_password_screen.dart` | Add 60s cooldown timer after send |
| `lib/core/router/app_router.dart` | Add `/update-password` route + first-priority redirect |
| `ios/Runner/Info.plist` | Add `CFBundleURLTypes` for URL scheme |
| `lib/shared/testing_keys/auth_keys.dart` | Add widget keys |
| `.claude/rules/auth/supabase-auth.md` | Update stale callback URL and PKCE docs |

## Testing Strategy

1. **Manual test on Android emulator**: Send reset email -> tap link -> verify app opens -> verify update-password screen -> enter new password -> verify sign-out + redirect to login -> sign in with new password
2. **Manual test — expired link**: Wait >1 hour, tap link -> verify "link expired" error message
3. **Manual test — cancel flow**: Open update-password -> tap cancel -> verify signed out + on login
4. **Manual test — cooldown**: Send reset email -> verify button disabled for 60s
5. **Widget test** (after BLOCKER-11 infra): Render `UpdatePasswordScreen` with `StubAuthProvider(isPasswordRecovery: true)`, verify form validation (8+ chars, uppercase, digit, match), verify submit calls `updatePassword`, verify cancel calls sign-out
6. **Router unit test**: Verify `isPasswordRecovery=true` redirects ALL routes to `/update-password`, verify cleared flag allows normal routing

## Follow-Up Items (Not In Scope)

These were identified by the security review as future hardening. Tracked separately:

| Item | Severity | Notes |
|------|----------|-------|
| **Migrate to App Links / Universal Links** | HIGH | Replace custom URL scheme with `https://` verified links. Requires hosting `assetlinks.json` and `apple-app-site-association`. |
| **Remove hardcoded Supabase creds** | CRITICAL | `supabase_config.dart` has hardcoded `defaultValue` fallbacks. Pre-existing issue, not specific to this plan. Needs separate ticket. |
| **Configure `flutter_secure_storage` for Supabase** | MEDIUM | Default token storage is unencrypted `SharedPreferences`. Auth rules doc already recommends secure storage but it's not implemented. |
| **Persist `_isPasswordRecovery` across app kill** | LOW | If app is killed during recovery flow and restarted, recovery flag is lost. Session survives (restored by Supabase) but guard doesn't. Mitigated by recovery session expiry. |

## Estimated Scope

- 1 new file (`update_password_screen.dart`, ~150 lines)
- 7 existing files modified (~80 lines changed)
- 2 config files updated (Info.plist, AndroidManifest.xml)
- 1 doc updated (auth rules)
- 5 manual Supabase dashboard verifications

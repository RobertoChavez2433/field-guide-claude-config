# Password Reset: Switch to token_hash + verifyOtp (PKCE Flow State Fix)

**Created**: 2026-02-28
**Status**: DRAFT — awaiting approval
**Supersedes**: Partial rework of `2026-02-27-password-reset-deep-linking.md` (Steps 1-6 of that plan were implemented and are live; this plan fixes the remaining runtime bug)
**Priority**: BLOCKER — password reset is completely broken on physical devices

---

## Problem Statement

Password reset deep links fail with `flow_state_not_found` on real devices. The flow works only if the app stays alive in memory between requesting the reset email and clicking the link — which almost never happens on a real phone.

### Error from device logs (Samsung S25 Ultra, 2026-02-28)

```
supabase.auth: WARNING: Notifying exception AuthApiException(
  message: invalid flow state, no valid flow state found,
  statusCode: 404,
  code: flow_state_not_found
)
```

### Root Cause

PKCE (Proof Key for Code Exchange) requires the **code verifier** — a random secret generated when the reset email is sent — to be present when the deep link returns. On mobile:

1. User taps "Reset Password" in the app -> PKCE code verifier stored in memory
2. User switches to email client -> Android may kill the app to reclaim memory
3. User taps the reset link in email -> app cold-starts, code verifier is **gone**
4. `supabase_flutter` tries to exchange the auth code but can't find the verifier
5. `flow_state_not_found` error -> auth state listener never fires `passwordRecovery`
6. Router sees no recovery state -> sends user to login page

This is a **fundamental limitation of PKCE on mobile** for server-initiated flows like password reset, documented in [Supabase Discussion #28655](https://github.com/orgs/supabase/discussions/28655).

### What Already Works (from Feb 27 plan)

The following are implemented and correct — this plan does NOT touch them:

- `UpdatePasswordScreen` with password complexity validation (SEC-6)
- Router redirect trapping user on `/update-password` when `isPasswordRecovery == true` (SEC-3, SEC-7)
- `AuthProvider.isPasswordRecovery` flag and `completePasswordRecovery()` method
- `AuthService.updatePassword()` method
- iOS URL scheme in `Info.plist`
- Android intent filter in `AndroidManifest.xml`
- 60s cooldown on `ForgotPasswordScreen`
- Testing keys for update password screen
- Barrel export in `screens.dart`

### What This Plan Fixes

The deep link -> session establishment step. Instead of relying on PKCE code exchange (which fails when app is killed), we switch to **token_hash + verifyOtp** — the officially recommended Supabase approach for this exact scenario.

---

## Solution: token_hash + verifyOtp

### How It Works

1. **Supabase email template** is configured to include `{{ .TokenHash }}` and the user's email in the reset link URL
2. When user clicks the link, the app receives a deep link like:
   `com.fieldguideapp.inspector://login-callback?token_hash=abc123&type=recovery&email=user@example.com`
3. The app intercepts this deep link **before** `supabase_flutter` tries (and fails) PKCE exchange
4. The app calls `supabase.auth.verifyOTP(email: email, token: tokenHash, type: OtpType.recovery)`
5. This establishes a valid recovery session **without needing the code verifier**
6. `AuthProvider` detects the `passwordRecovery` event and sets `isPasswordRecovery = true`
7. Router redirects to `/update-password` — existing flow takes over

### Security Analysis

| Concern | Assessment |
|---------|-----------|
| **Token hash strength** | SHA-256 hash of the OTP token — cryptographically strong, not guessable |
| **Token lifetime** | Controlled by Supabase `otp_expiry` setting (default: 3600s / 1 hour). Configurable in dashboard |
| **Single use** | Token hash is consumed on `verifyOTP` call — cannot be replayed |
| **No tokens in URL history** | Token hash is not an access token — it's a one-time verification hash. Even if intercepted, it can only establish a recovery session (not full access) |
| **PKCE preserved for other flows** | Login, signup, email verification all continue using PKCE. Only password reset switches to token_hash |
| **Recovery session scoping** | Unchanged — router still traps user on `/update-password`, session destroyed after password change (SEC-3) |
| **Officially recommended** | Supabase team recommends this in [Discussion #28655](https://github.com/orgs/supabase/discussions/28655) |

---

## Implementation Steps

### Phase 1: Supabase Dashboard Configuration

#### Step 1.1: Customize Password Reset Email Template

**Location**: Supabase Dashboard > Authentication > Email Templates > Reset Password

Change the email template's reset link to include `token_hash`, `type`, and `email` as query parameters instead of the default PKCE `code` parameter.

**Current template link** (default Supabase):
```
{{ .SiteURL }}/auth/v1/verify?token={{ .Token }}&type=recovery&redirect_to={{ .RedirectTo }}
```

**New template link**:
```
{{ .RedirectTo }}?token_hash={{ .TokenHash }}&type=recovery&email={{ .Email }}
```

This sends the user directly to the app's deep link URL with the token hash, bypassing the Supabase `/auth/v1/verify` redirect entirely.

**Why this is secure**: `{{ .TokenHash }}` is a server-generated SHA-256 hash of the recovery token. It cannot be reversed to obtain the original token. It is single-use and time-limited.

#### Step 1.2: Verify Redirect URL Allowlist

**Location**: Supabase Dashboard > Authentication > URL Configuration > Redirect URLs

Confirm `com.fieldguideapp.inspector://login-callback` is in the allowlist. (Already done per Feb 27 plan — verify still present.)

#### Step 1.3: Verify OTP Expiry Setting

**Location**: Supabase Dashboard > Authentication > Settings (or `supabase/config.toml` for local dev)

Current setting in `config.toml` line 213: `otp_expiry = 3600` (1 hour). This is appropriate. Verify the production dashboard matches.

---

### Phase 2: Deep Link Interception

#### Step 2.1: Disable Supabase Auto Deep Link Handling

**File**: `lib/main.dart` (line 150-153)

Change Supabase initialization to disable automatic deep link detection. This prevents `supabase_flutter` from trying (and failing) PKCE code exchange on password reset links.

**Current code** (`main.dart:147-153`):
```dart
await Supabase.initialize(
  url: SupabaseConfig.url,
  anonKey: SupabaseConfig.anonKey,
  authOptions: const FlutterAuthClientOptions(
    authFlowType: AuthFlowType.pkce,
  ),
);
```

**New code**:
```dart
await Supabase.initialize(
  url: SupabaseConfig.url,
  anonKey: SupabaseConfig.anonKey,
  authOptions: FlutterAuthClientOptions(
    authFlowType: AuthFlowType.pkce,
    // Disable auto deep link handling so we can intercept password reset
    // links with token_hash before supabase_flutter attempts PKCE exchange.
    // Email verification and other PKCE flows still work because we
    // manually call exchangeCodeForSession for non-recovery links.
  ),
);
```

**IMPORTANT**: We need to check if `supabase_flutter` supports `detectSessionInUri: false` or if we need to handle this differently. The `FlutterAuthClientOptions` class may or may not expose this parameter. Research required during implementation.

**Alternative approach if `detectSessionInUri` is not available**: Keep auto-detection enabled but add a custom `app_links` listener that fires FIRST and intercepts recovery links before `supabase_flutter` processes them. Since `app_links` listeners fire in registration order, register ours before Supabase initializes.

#### Step 2.2: Add Custom Deep Link Handler for Recovery Links

**File**: `lib/main.dart` — add after Supabase initialization, before `runApp()`

```dart
/// Handle deep links for password reset (token_hash approach).
/// For non-recovery deep links, delegate to supabase_flutter's built-in handler.
void _initPasswordResetDeepLinkHandler(AuthProvider authProvider) {
  final appLinks = AppLinks();

  // Listen for incoming deep links
  appLinks.uriLinkStream.listen((Uri uri) async {
    final params = uri.queryParameters;
    final tokenHash = params['token_hash'];
    final type = params['type'];
    final email = params['email'];

    // Only intercept recovery links with token_hash
    if (tokenHash != null && type == 'recovery' && email != null) {
      try {
        // Exchange token_hash for a recovery session via verifyOTP
        await Supabase.instance.client.auth.verifyOTP(
          email: email,
          token: tokenHash,
          type: OtpType.recovery,
        );
        // Success: supabase_flutter will fire AuthChangeEvent.passwordRecovery
        // which AuthProvider already handles (sets isPasswordRecovery = true)
      } on AuthException catch (e) {
        debugPrint('[AUTH] Recovery token verification failed: ${e.message}');
        // Token expired or invalid — AuthProvider won't enter recovery mode,
        // user stays on login screen. No action needed.
      }
    }
    // Non-recovery deep links (email verification, OAuth) are handled
    // by supabase_flutter's built-in app_links listener automatically.
  });
}
```

**Security notes**:
- Only intercepts links where ALL three params (`token_hash`, `type=recovery`, `email`) are present
- Non-recovery deep links fall through to `supabase_flutter`'s built-in PKCE handler
- Failed verification silently drops — user stays on login, no error state corruption
- No sensitive data logged (token_hash is NOT printed)

#### Step 2.3: Register the Handler in `_runApp()`

**File**: `lib/main.dart` — add after `authProvider` creation (after line 252), before `runApp()`

```dart
// Handle password reset deep links via token_hash + verifyOtp
// (PKCE code exchange fails when app is killed between reset request and link click)
if (SupabaseConfig.isConfigured) {
  _initPasswordResetDeepLinkHandler(authProvider);
}
```

#### Step 2.4: Add `app_links` Import Back

**File**: `lib/main.dart`

The Feb 27 plan removed the `app_links` import since `supabase_flutter` handled it internally. We now need it back for our custom recovery handler:

```dart
import 'package:app_links/app_links.dart';
```

**Note**: `app_links` is already a dependency in `pubspec.yaml` (used by `supabase_flutter` transitively). Verify it's accessible as a direct dependency; if not, add it to `dependencies:` in `pubspec.yaml`.

---

### Phase 3: Handle Initial Deep Link (Cold Start)

#### Step 3.1: Handle the Initial/Launch Deep Link

**File**: `lib/main.dart`

When the app is cold-started by a deep link tap, `uriLinkStream` may not catch the initial URI. We need to also check for the launch URI.

Add to `_initPasswordResetDeepLinkHandler`:

```dart
void _initPasswordResetDeepLinkHandler(AuthProvider authProvider) {
  final appLinks = AppLinks();

  // Handle the INITIAL deep link that launched/resumed the app
  appLinks.getInitialLink().then((Uri? uri) {
    if (uri != null) _handleRecoveryDeepLink(uri);
  });

  // Handle subsequent deep links while app is running
  appLinks.uriLinkStream.listen((Uri uri) {
    _handleRecoveryDeepLink(uri);
  });
}

Future<void> _handleRecoveryDeepLink(Uri uri) async {
  final params = uri.queryParameters;
  final tokenHash = params['token_hash'];
  final type = params['type'];
  final email = params['email'];

  if (tokenHash == null || type != 'recovery' || email == null) return;

  try {
    await Supabase.instance.client.auth.verifyOTP(
      email: email,
      token: tokenHash,
      type: OtpType.recovery,
    );
    // AuthChangeEvent.passwordRecovery will fire -> AuthProvider handles it
  } on AuthException catch (e) {
    debugPrint('[AUTH] Recovery token verification failed: ${e.message}');
  }
}
```

**Critical timing note**: This handler must be registered AFTER `Supabase.initialize()` completes but BEFORE `runApp()`. The initial link check should happen after the auth state listener is set up in `AuthProvider` so the `passwordRecovery` event is caught.

#### Step 3.2: Prevent Double-Handling of Recovery Links

**File**: `lib/main.dart`

`supabase_flutter` also registers an `app_links` listener internally. When a recovery link arrives, both our handler AND supabase's handler will see it. Our handler calls `verifyOTP` (which works). Supabase's handler tries `exchangeCodeForSession` (which fails because there's no `code` param — the link has `token_hash` instead).

This is safe because:
- Our handler succeeds first → session established
- Supabase's handler sees no `code` query parameter → silently does nothing (PKCE exchange requires `code`)

**Verify during implementation**: Confirm that `supabase_flutter`'s built-in listener only acts on links with a `code` parameter and ignores links with `token_hash`. If it throws on unexpected params, we may need `detectSessionInUri: false`.

---

### Phase 4: Auth Service Updates

#### Step 4.1: Add `verifyRecoveryToken` to AuthService

**File**: `lib/features/auth/services/auth_service.dart`

Add a dedicated method for token_hash verification to maintain the service layer pattern:

```dart
/// Verify a password recovery token hash received via deep link.
///
/// This is the token_hash approach recommended by Supabase for PKCE
/// environments where the code verifier may be lost (e.g., app killed
/// between reset request and link click).
///
/// On success, establishes a recovery session and triggers
/// [AuthChangeEvent.passwordRecovery] on the auth state stream.
///
/// Throws [AuthException] if the token is expired or invalid.
/// Throws [StateError] if Supabase is not configured.
Future<AuthResponse> verifyRecoveryToken({
  required String email,
  required String tokenHash,
}) async {
  if (_client == null) {
    throw StateError(
      'Supabase not configured. Cannot verify recovery token.',
    );
  }
  return await _client.auth.verifyOTP(
    email: email,
    token: tokenHash,
    type: OtpType.recovery,
  );
}
```

#### Step 4.2: Update Deep Link Handler to Use AuthService

**File**: `lib/main.dart`

Update `_handleRecoveryDeepLink` to go through `AuthService` instead of calling Supabase directly:

```dart
Future<void> _handleRecoveryDeepLink(Uri uri, AuthService authService) async {
  final params = uri.queryParameters;
  final tokenHash = params['token_hash'];
  final type = params['type'];
  final email = params['email'];

  if (tokenHash == null || type != 'recovery' || email == null) return;

  try {
    await authService.verifyRecoveryToken(
      email: email,
      tokenHash: tokenHash,
    );
  } on AuthException catch (e) {
    debugPrint('[AUTH] Recovery token verification failed: ${e.message}');
  }
}
```

---

### Phase 5: Edge Case Handling

#### Step 5.1: Handle Expired Token Hash in UpdatePasswordScreen

**File**: `lib/features/auth/presentation/screens/update_password_screen.dart`

Already implemented (SEC-9 from Feb 27 plan). The existing error handling catches `AuthException` with "expired"/"invalid"/"token" messages and redirects to `/forgot-password`. **No changes needed.**

#### Step 5.2: Handle Email Client Link Prefetching

Some email clients (Outlook, Gmail) prefetch links in emails, which can consume the token before the user clicks. Mitigation:

- Supabase's `verifyOTP` is single-use — if prefetched, the user's click will fail
- The `otp_expiry` is 1 hour, giving the user time to click before server-side expiry
- If the token is consumed by prefetch, user sees "link expired" and can request a new one
- **No code change needed** — existing expired link handling covers this

#### Step 5.3: Handle Race Between Custom and Supabase Handlers

If both handlers fire and both somehow succeed (shouldn't happen with token_hash links, but defensive):

- The auth state listener in `AuthProvider` is idempotent — receiving `passwordRecovery` twice just sets `_isPasswordRecovery = true` again
- **No code change needed**

#### Step 5.4: Persist `isPasswordRecovery` Across App Restart (Future Enhancement)

If the app is killed while on the `/update-password` screen, the recovery flag is lost on restart. The session persists (Supabase restores it from secure storage), but the router won't know it's a recovery session.

**Current mitigation**: The recovery session JWT has limited scope. If the user restarts the app, they land on login (no recovery flag) and can just request a new reset.

**Future enhancement** (not in this plan): Persist `_isPasswordRecovery` to `SharedPreferences` or `flutter_secure_storage`. Clear it on `completePasswordRecovery()` and on `signOut()`.

---

### Phase 6: Local Development (Supabase CLI)

#### Step 6.1: Update `supabase/config.toml` Email Template

**File**: `supabase/config.toml`

For local development with `supabase start`, the email templates need to be customized. Add a custom reset password template:

**Create file**: `supabase/templates/reset_password.html`

```html
<h2>Reset Your Password</h2>
<p>Click the link below to reset your password:</p>
<p>
  <a href="{{ .RedirectTo }}?token_hash={{ .TokenHash }}&type=recovery&email={{ .Email }}">
    Reset Password
  </a>
</p>
<p>This link expires in 1 hour.</p>
```

**Update `config.toml`** — add after line 226:

```toml
[auth.email.template.recovery]
subject = "Reset Your Password"
content_path = "./supabase/templates/reset_password.html"
```

---

### Phase 7: Testing

#### Step 7.1: Manual Test — Full Flow on Physical Device

1. Install release APK on Samsung S25 Ultra via `tools/build.ps1 -Platform android`
2. Open app, navigate to login, tap "Forgot Password"
3. Enter registered email, tap Send
4. **Kill the app** (swipe away from recents)
5. Open email, tap reset link
6. Verify: app opens to Update Password screen
7. Enter new password meeting complexity requirements
8. Tap "Update Password"
9. Verify: redirected to login with success message
10. Sign in with new password
11. Verify: successfully authenticated

#### Step 7.2: Manual Test — Expired Token

1. Send reset email
2. Wait for `otp_expiry` to pass (or manually invalidate in Supabase dashboard)
3. Tap the link
4. Verify: app shows "link expired" message, redirects to forgot-password

#### Step 7.3: Manual Test — Double Link Click

1. Send reset email
2. Click the link (app opens, lands on update password screen)
3. Don't submit — go back to email and click the link again
4. Verify: second click has no adverse effect (token already consumed, session already active)

#### Step 7.4: Manual Test — Cancel Flow

1. Click reset link, land on update password screen
2. Tap "Cancel"
3. Verify: signed out, redirected to login
4. Verify: cannot navigate to `/update-password` or any authenticated route

#### Step 7.5: Manual Test — App Kill During Password Update

1. Click reset link, land on update password screen
2. Kill the app (swipe away)
3. Reopen the app
4. Verify: lands on login page (recovery flag lost, session may or may not survive)
5. Verify: can request a new reset and complete the flow

#### Step 7.6: Emulator Regression Test

1. Run on Android emulator (app stays alive in memory)
2. Verify the PKCE flow for email verification still works
3. Verify login/signup deep links are unaffected
4. Verify password reset works on emulator too (both cold-start and warm-start)

---

## Files Modified

| File | Change | Lines |
|------|--------|-------|
| `lib/main.dart` | Add custom deep link handler for recovery, add `app_links` import, register handler | ~40 new |
| `lib/features/auth/services/auth_service.dart` | Add `verifyRecoveryToken()` method | ~20 new |
| `supabase/config.toml` | Add custom recovery email template path | ~3 new |
| **NEW**: `supabase/templates/reset_password.html` | Custom email template with token_hash link | ~10 new |

## Files NOT Modified (Already Correct from Feb 27 Plan)

| File | Why |
|------|-----|
| `update_password_screen.dart` | Screen works, just needs the session to be established |
| `auth_provider.dart` | `isPasswordRecovery` flag and listener already correct |
| `app_router.dart` | Recovery redirect already in place |
| `AndroidManifest.xml` | Intent filter already correct |
| `ios/Runner/Info.plist` | URL scheme already added |
| `forgot_password_screen.dart` | 60s cooldown already implemented |
| `testing_keys/auth_keys.dart` | Keys already added |
| `screens.dart` | Barrel export already added |

## Supabase Dashboard Changes (Manual)

| Setting | Location | Change |
|---------|----------|--------|
| Reset Password email template | Auth > Email Templates > Reset Password | Change link to `{{ .RedirectTo }}?token_hash={{ .TokenHash }}&type=recovery&email={{ .Email }}` |
| Verify redirect URL | Auth > URL Configuration | Confirm `com.fieldguideapp.inspector://login-callback` present |
| Verify OTP expiry | Auth > Settings | Confirm 3600s (1 hour) |

## Estimated Scope

- ~70 lines of new code across 2 existing files
- 1 new file (email template HTML, ~10 lines)
- 1 config file update (3 lines)
- 1 Supabase dashboard change (email template)
- 6 manual test scenarios

## Dependencies

- Supabase dashboard access (to change email template)
- Physical Android device (Samsung S25 Ultra connected via USB)
- Working email delivery from Supabase (for end-to-end test)

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `supabase_flutter` internal handler conflicts with custom handler | Low | Token_hash links have no `code` param, so PKCE handler ignores them |
| `app_links` double-fires (initial + stream) | Medium | `verifyOTP` is idempotent after first use — second call fails silently |
| Email client prefetches link, consuming token | Low | User sees "expired" message, requests new reset |
| `verifyOTP` API changes in future supabase_flutter versions | Low | Using stable public API, well-documented |

## References

- [Supabase Discussion #28655 — Official recommendation for token_hash](https://github.com/orgs/supabase/discussions/28655)
- [Supabase PKCE Flow Docs](https://supabase.com/docs/guides/auth/sessions/pkce-flow)
- [Supabase Password Reset Docs](https://supabase.com/docs/guides/auth/auth-password-reset)
- [supabase-flutter Issue #937 — Deep link handling](https://github.com/supabase/supabase-flutter/issues/937)
- [supabase-flutter Issue #664 — passwordRecovery event with PKCE](https://github.com/supabase/supabase-flutter/issues/664)
- Previous plan: `.claude/plans/2026-02-27-password-reset-deep-linking.md`

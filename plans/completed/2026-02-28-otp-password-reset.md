# Password Reset: Switch to OTP Code Entry (Replace Deep Linking)

**Created**: 2026-02-28
**Status**: DRAFT — awaiting approval
**Supersedes**: `2026-02-28-password-reset-token-hash-fix.md` (deep link approach — BLOCKER-14 killed it)
**Resolves**: BLOCKER-14 (email link delivery), BLOCKER-13 (deep linking), custom scheme hijacking security blocker, desktop custom scheme blocker
**Priority**: BLOCKER — password reset is completely broken

---

## Problem Statement

Deep-link-based password reset is a dead end:
1. `{{ .RedirectTo }}` resolves to Supabase's server URL, consuming the token via PKCE before the app gets it
2. Hardcoding custom scheme (`com.fieldguideapp.inspector://`) makes links unclickable in email clients
3. Custom schemes don't work on desktop browsers at all
4. Custom schemes are hijackable on Android < 12

## Solution: In-App OTP Code Entry

Replace the deep link flow with a 6-digit OTP code that the user reads from their email and types into the app. No deep link needed at all.

**Supabase already supports this**: `otp_length = 6` in config.toml, and `verifyOTP(type: recovery)` accepts the raw 6-digit token from `{{ .Token }}` in the email template.

---

## Flow

```
ForgotPasswordScreen         OtpVerificationScreen        UpdatePasswordScreen
┌──────────────────┐        ┌──────────────────┐         ┌──────────────────┐
│ Enter email       │        │ "Enter the 6-digit│         │ New password      │
│ [Send Code]       │──OK──> │  code we emailed" │──OK──>  │ Confirm password  │
│                   │        │ [  _ _ _ _ _ _  ] │         │ [Update]          │
│ 60s cooldown      │        │ [Verify]          │         │                   │
└──────────────────┘        │ [Resend Code] 60s │         └──────────────────┘
                             │ [Back]            │
                             └──────────────────┘
```

1. `ForgotPasswordScreen`: User enters email → calls `resetPasswordForEmail()` → navigates to `/verify-otp?email=...`
2. `OtpVerificationScreen`: User types 6-digit code from email → calls `verifyOTP(email, token, type: recovery)` → Supabase fires `passwordRecovery` event → router redirects to `/update-password`
3. `UpdatePasswordScreen`: Already implemented — no changes needed

---

## Implementation Steps

### Phase 1: New OTP Verification Screen

#### Step 1.1: Create `OtpVerificationScreen`

**File**: `lib/features/auth/presentation/screens/otp_verification_screen.dart` (NEW)

Screen with:
- Title: "Enter Verification Code"
- Subtitle: "We sent a 6-digit code to {email}"
- 6 individual `TextFormField` boxes for code entry (auto-advance on digit input)
- "Verify" button — calls `AuthProvider.verifyRecoveryOtp(email, code)`
- "Resend Code" button — calls `AuthProvider.resetPassword(email)` with same 60s cooldown
- "Back" text button — navigates back to forgot password screen
- Error display for expired/invalid codes

**Key behaviors**:
- Auto-focus first digit field on mount
- Auto-advance cursor to next field on input
- Auto-submit when 6th digit entered
- Paste support: if user pastes 6 digits, fill all fields
- Numeric keyboard only (`TextInputType.number`)

#### Step 1.2: Add Testing Keys

**File**: `lib/shared/testing_keys/auth_keys.dart`

Add to `AuthTestingKeys`:
```dart
// Authentication - OTP Verification
static const otpVerificationScreenTitle = Key('otp_verification_screen_title');
static const otpDigitField0 = Key('otp_digit_field_0');
static const otpDigitField1 = Key('otp_digit_field_1');
static const otpDigitField2 = Key('otp_digit_field_2');
static const otpDigitField3 = Key('otp_digit_field_3');
static const otpDigitField4 = Key('otp_digit_field_4');
static const otpDigitField5 = Key('otp_digit_field_5');
static const otpVerifyButton = Key('otp_verify_button');
static const otpResendButton = Key('otp_resend_button');
static const otpBackButton = Key('otp_back_button');
```

#### Step 1.3: Add to Barrel Export

**File**: `lib/features/auth/presentation/screens/screens.dart`

Add:
```dart
export 'otp_verification_screen.dart';
```

### Phase 2: AuthProvider + AuthService Changes

#### Step 2.1: Add `verifyRecoveryOtp()` to AuthProvider

**File**: `lib/features/auth/presentation/providers/auth_provider.dart`

Add method that wraps `AuthService.verifyRecoveryToken` (reusing existing method — the OTP code IS the token):

```dart
/// Verify a 6-digit OTP code for password recovery.
///
/// On success, Supabase fires [AuthChangeEvent.passwordRecovery],
/// which sets [isPasswordRecovery] = true and triggers router redirect
/// to /update-password.
Future<bool> verifyRecoveryOtp({
  required String email,
  required String otp,
}) async {
  _isLoading = true;
  _error = null;
  notifyListeners();

  try {
    await _authService.verifyRecoveryToken(
      email: email,
      tokenHash: otp,
    );
    _isLoading = false;
    notifyListeners();
    return true;
  } on AuthException catch (e) {
    _isLoading = false;
    _error = _parseOtpError(e.message);
    notifyListeners();
    return false;
  } catch (e) {
    _isLoading = false;
    _error = 'Verification failed. Please try again.';
    notifyListeners();
    return false;
  }
}
```

Add helper:
```dart
String _parseOtpError(String message) {
  if (message.contains('expired') || message.contains('otp_expired')) {
    return 'Code expired. Please request a new one.';
  }
  if (message.contains('invalid') || message.contains('not found')) {
    return 'Invalid code. Please check and try again.';
  }
  return 'Verification failed. Please try again.';
}
```

#### Step 2.2: Rename `verifyRecoveryToken` in AuthService

**File**: `lib/features/auth/services/auth_service.dart`

Rename the parameter from `tokenHash` to `token` for clarity (it now accepts a raw 6-digit OTP, not a hash). The underlying Supabase call is the same — `verifyOTP` accepts both raw tokens and hashes.

```dart
Future<AuthResponse> verifyRecoveryToken({
  required String email,
  required String token,
}) async {
  ...
  return await _client.auth.verifyOTP(
    email: email,
    token: token,
    type: OtpType.recovery,
  );
}
```

Update the doc comment to reflect OTP code usage instead of deep link token_hash.

### Phase 3: Update ForgotPasswordScreen

**File**: `lib/features/auth/presentation/screens/forgot_password_screen.dart`

Changes:
1. After successful `resetPassword()`, navigate to `/verify-otp?email={email}` instead of showing the success view
2. Update button text from "Send Reset Link" to "Send Code"
3. Update description text from "...send you a link..." to "...send you a code..."
4. Remove `_buildSuccessView()` entirely — the OTP screen replaces it
5. Keep the 60s cooldown logic (still needed to prevent spam)

### Phase 4: Router

**File**: `lib/core/router/app_router.dart`

Add route:
```dart
GoRoute(
  path: '/verify-otp',
  name: 'verifyOtp',
  builder: (context, state) {
    final email = state.uri.queryParameters['email'] ?? '';
    return OtpVerificationScreen(email: email);
  },
),
```

Add `/verify-otp` to auth routes check so unauthenticated users can access it:
```dart
final isAuthRoute =
    location.startsWith('/login') ||
    location.startsWith('/register') ||
    location.startsWith('/forgot-password') ||
    location.startsWith('/verify-otp');
```

### Phase 5: Remove Deep Link Code

#### Step 5.1: Remove deep link handler from main.dart

**File**: `lib/main.dart`

Remove:
- Lines 255-261: `_initPasswordResetDeepLinkHandler` call block
- Lines 461-508: `_initPasswordResetDeepLinkHandler()` and `_handleRecoveryDeepLink()` functions
- `import 'package:app_links/app_links.dart';` — IF no other code in main.dart uses it (check first)

#### Step 5.2: Update email template

**File**: `supabase/templates/reset_password.html`

Change from deep link to showing the OTP code:

```html
<h2>Reset Your Password</h2>
<p>Enter this code in the Field Guide app to reset your password:</p>
<div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; text-align: center; padding: 20px; background: #f5f5f5; border-radius: 8px; margin: 20px 0;">
  {{ .Token }}
</div>
<p>This code expires in 1 hour.</p>
<p>If you didn't request this, you can safely ignore this email.</p>
```

#### Step 5.3: Update Supabase Dashboard

**Manual action**: Update the production email template in Supabase Dashboard > Authentication > Email Templates > Reset Password to match the template above.

#### Step 5.4: Update config.toml recovery template path

**File**: `supabase/config.toml` — no change needed (already points to `./templates/reset_password.html`)

### Phase 6: Clean Up AuthService Doc Comment

**File**: `lib/features/auth/services/auth_service.dart`

- Update `resetPassword()` doc comment: change "deep link" to "OTP code"
- Update `redirectUrl` doc comment — still used by signup email verification, just not password reset
- Update `verifyRecoveryToken()` doc comment to reflect OTP usage

---

## Files Modified

| File | Change |
|------|--------|
| `lib/features/auth/presentation/screens/otp_verification_screen.dart` | **NEW** — 6-digit OTP entry screen |
| `lib/features/auth/presentation/screens/forgot_password_screen.dart` | Navigate to OTP screen, update text, remove success view |
| `lib/features/auth/presentation/providers/auth_provider.dart` | Add `verifyRecoveryOtp()` + `_parseOtpError()` |
| `lib/features/auth/services/auth_service.dart` | Rename param, update doc comments |
| `lib/features/auth/presentation/screens/screens.dart` | Add barrel export |
| `lib/shared/testing_keys/auth_keys.dart` | Add OTP testing keys |
| `lib/core/router/app_router.dart` | Add `/verify-otp` route |
| `lib/main.dart` | Remove deep link handler (~50 lines) |
| `supabase/templates/reset_password.html` | Show OTP code instead of deep link |

## Files NOT Modified

| File | Why |
|------|-----|
| `update_password_screen.dart` | Works as-is after recovery session established |
| `auth_provider.dart` (auth listener) | `passwordRecovery` event handling unchanged |
| `AndroidManifest.xml` | Keep intent filters for future email verification deep links |
| `ios/Runner/Info.plist` | Keep URL scheme for future use |
| `pubspec.yaml` | No new dependencies |
| `config.toml` | Template path already correct |

## Security Impact

| Concern | Assessment |
|---------|-----------|
| **OTP brute force** | Supabase rate-limits OTP attempts server-side. 6-digit = 1M combinations. |
| **OTP in email** | Same security as link-in-email (email is the channel). No worse than current. |
| **Custom scheme hijacking** | **RESOLVED** — no custom scheme used for password reset anymore |
| **Email in URL** | **RESOLVED** — email passed as route query param within the app, not in an external URL |
| **Desktop support** | **RESOLVED** — OTP works everywhere, no browser/OS dependency |
| **Email prefetch** | **RESOLVED** — codes are typed, not clicked. Prefetch can't consume them. |

## Blockers Resolved

- **BLOCKER-14**: Email link delivery — eliminated (no link needed)
- **BLOCKER-13**: Deep linking — bypassed (in-app flow)
- **Security: Custom URI scheme hijackable** — resolved (no custom scheme for reset)
- **Config: Desktop browsers** — resolved (OTP works on desktop)

## Blockers Remaining (Unchanged)

- **secure_password_change**: Still need to enable in Supabase (separate config change)
- **Recovery flag persistence**: Still in-memory only (lower priority, existing mitigation adequate)

## Testing

### Manual Test — Full Flow
1. Open app → Login → Forgot Password → enter email → Send Code
2. Check email for 6-digit code
3. Enter code in OTP screen → Verify
4. Should land on Update Password screen
5. Set new password → should redirect to login
6. Sign in with new password

### Manual Test — Expired Code
1. Send code, wait >1 hour (or manually expire in Supabase)
2. Enter code → should show "Code expired" error
3. Tap "Resend Code" → new code arrives

### Manual Test — Wrong Code
1. Enter wrong 6 digits → should show "Invalid code" error
2. Can retry immediately

### Manual Test — Resend
1. Send code → tap "Resend Code"
2. Should show 60s cooldown
3. New code should arrive

### Manual Test — Desktop (Windows)
1. Run app on Windows
2. Complete full OTP flow
3. Should work identically to mobile

---

## Agent Assignments

| Phase | Agent | Files |
|-------|-------|-------|
| 1 | frontend-flutter-specialist-agent | otp_verification_screen.dart, auth_keys.dart, screens.dart |
| 2 | backend-data-layer-agent | auth_provider.dart, auth_service.dart |
| 3 | frontend-flutter-specialist-agent | forgot_password_screen.dart |
| 4 | frontend-flutter-specialist-agent | app_router.dart |
| 5 | backend-data-layer-agent | main.dart, reset_password.html |
| 6 | backend-data-layer-agent | auth_service.dart doc comments |

## Estimated Scope

- ~150 lines new (OTP screen)
- ~30 lines modified (forgot password, provider, service, router)
- ~50 lines removed (deep link handler)
- 1 new file, 8 modified files
- Net: ~130 lines added

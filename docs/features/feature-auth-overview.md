---
feature: auth
type: overview
scope: User Authentication & Session Management
updated: 2026-02-13
---

# Auth Feature Overview

## Purpose

The Auth feature manages user authentication with Supabase, including sign-up, sign-in, password reset, and session lifecycle. It securely handles user credentials and maintains authentication state across app lifecycle, with deep linking support for email verification and password reset flows.

## Key Responsibilities

- **User Sign-Up**: Register new users with email and password; send email verification links
- **User Sign-In**: Authenticate existing users and establish sessions
- **Password Reset**: Send password reset emails with deep links for recovery
- **Session Management**: Maintain authentication state across app restarts and deep link callbacks
- **Token Storage**: Securely store access and refresh tokens using platform-specific storage
- **State Broadcasting**: Stream authentication state changes to UI layer for reactive updates
- **Error Handling**: Parse and present user-friendly authentication error messages

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/auth/services/auth_service.dart` | Supabase authentication service |
| `lib/features/auth/presentation/providers/auth_provider.dart` | ChangeNotifier for UI state |
| `lib/features/auth/presentation/screens/login_screen.dart` | Sign-in UI |
| `lib/features/auth/presentation/screens/register_screen.dart` | Sign-up UI |
| `lib/features/auth/presentation/screens/forgot_password_screen.dart` | Password reset UI |
| `lib/core/config/supabase_config.dart` | Supabase client initialization |

## Data Sources

- **Supabase Auth**: Remote authentication backend (email/password provider)
- **Flutter Secure Storage**: Platform-specific token storage (iOS Keychain, Android Keystore)
- **Device Deep Links**: App URL scheme for email verification and password reset callbacks
- **SQLite** (future): Optional local user profile caching

## Integration Points

**Depends on:**
- `core/config` - Supabase client initialization
- `services` - Secure storage for tokens

**Required by:**
- `sync` - Authentication required before Supabase sync
- `settings` - User profile display and sign-out trigger
- `dashboard` - Authentication guard for main app screens

## Offline Behavior

Auth is **mostly offline-capable** but with limitations:

### Initial Authentication (Requires Network)
- Sign-up, sign-in, and password reset require network connection
- Offline sign-in is not supported (no local auth fallback)

### Authenticated Operations (Offline-Safe)
- Current user session accessible offline (cached in memory)
- Token refresh deferred until reconnect
- Features that depend on auth (sync, etc.) available for offline work

### Session Persistence
- Access token cached in memory during session
- Refresh token stored securely on device
- Session survives app kill/restart via token refresh on app launch

## Edge Cases & Limitations

- **No Biometric Login**: Password-only authentication (no fingerprint/face ID)
- **Email Verification Required**: Users must verify email before full access (configurable)
- **Rate Limiting**: Supabase enforces rate limits on auth endpoints (typically 5 attempts per minute)
- **No Session Timeout**: Sessions persist until user explicitly signs out or token expires
- **Deep Link Routing**: Password reset links may fail if app isn't installed or deep link not configured
- **No Multi-Factor Authentication**: Not implemented (single-factor email+password only)

## Detailed Specifications

See `architecture-decisions/auth-constraints.md` for:
- Hard rules on token handling and session lifecycle
- Authentication flow diagrams and state transitions
- Error handling patterns and retry logic

See `rules/auth/supabase-auth.md` for:
- Supabase configuration and Dart client patterns
- Deep linking setup for Android/iOS
- Security checklist for authentication code
- Logging guidelines (never log tokens/passwords)

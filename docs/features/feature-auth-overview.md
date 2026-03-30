---
feature: auth
type: overview
scope: Authentication, Authorization, Company Management, Profile Management, Onboarding
updated: 2026-03-30
---

# Auth Feature Overview

## Purpose

The Auth feature manages user authentication with Supabase, company membership, user profile management, and onboarding flows. It handles sign-up, sign-in, password reset, OTP verification, company creation/joining, role-based authorization, and session lifecycle. It is the root feature — all other features depend on the auth context it establishes.

## Key Responsibilities

- **User Sign-Up / Sign-In**: Register and authenticate users via email/password; send email verification links
- **Password Reset**: OTP-based password reset flow (no deep link dependency)
- **Session Management**: Maintain authentication state across app restarts
- **Company Management**: Create companies, submit and approve join requests, switch active company
- **Profile Management**: Set up and update user profiles; load profile on session restore
- **Role-Based Authorization**: Enforce `UserRole` across the app via `AuthProvider`
- **App Config**: Fetch remote feature flags and minimum version requirements via `AppConfigProvider`
- **Inactivity Detection**: Auto-lock sessions after inactivity via `CheckInactivityUseCase`
- **Preference Migration**: Migrate legacy shared preferences on upgrade via `MigratePreferencesUseCase`
- **Error Handling**: Parse and present user-friendly authentication error messages

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/auth/di/auth_providers.dart` | DI wiring — registers `AuthProvider`, `AppConfigProvider`, `AuthService`, `AdminProvider` |
| `lib/features/auth/services/auth_service.dart` | Supabase authentication and profile operations |
| `lib/features/auth/services/password_validator.dart` | Password strength and validation rules |
| `lib/features/auth/presentation/providers/auth_provider.dart` | Root auth state — current user, role, company, session lifecycle |
| `lib/features/auth/presentation/providers/app_config_provider.dart` | Remote app config — feature flags, minimum version |
| `lib/features/auth/presentation/screens/login_screen.dart` | Sign-in UI |
| `lib/features/auth/presentation/screens/register_screen.dart` | Sign-up UI |
| `lib/features/auth/presentation/screens/forgot_password_screen.dart` | Password reset request UI |
| `lib/features/auth/presentation/screens/otp_verification_screen.dart` | OTP code entry UI |
| `lib/features/auth/presentation/screens/update_password_screen.dart` | New password entry after OTP |
| `lib/features/auth/presentation/screens/profile_setup_screen.dart` | Onboarding — user profile creation |
| `lib/features/auth/presentation/screens/company_setup_screen.dart` | Onboarding — create or join a company |
| `lib/features/auth/presentation/screens/pending_approval_screen.dart` | Waiting room while join request is reviewed |
| `lib/features/auth/presentation/screens/account_status_screen.dart` | Displays deactivated/suspended account state |
| `lib/features/auth/presentation/screens/update_required_screen.dart` | Forces upgrade when app version is below minimum |
| `lib/features/auth/domain/usecases/sign_in_use_case.dart` | Sign-in orchestration |
| `lib/features/auth/domain/usecases/sign_up_use_case.dart` | Registration orchestration |
| `lib/features/auth/domain/usecases/sign_out_use_case.dart` | Sign-out and session teardown |
| `lib/features/auth/domain/usecases/load_profile_use_case.dart` | Load user profile and company on session restore |
| `lib/features/auth/domain/usecases/switch_company_use_case.dart` | Switch active company context |
| `lib/features/auth/domain/usecases/check_inactivity_use_case.dart` | Detect and trigger inactivity lock |
| `lib/features/auth/domain/usecases/migrate_preferences_use_case.dart` | Migrate legacy shared preferences on upgrade |
| `lib/features/auth/data/models/user_profile.dart` | UserProfile model |
| `lib/features/auth/data/models/user_role.dart` | UserRole enum (admin, inspector, etc.) |
| `lib/features/auth/data/models/company.dart` | Company model |
| `lib/features/auth/data/models/company_join_request.dart` | CompanyJoinRequest model |
| `lib/features/auth/data/repositories/user_profile_repository.dart` | UserProfile read/write (local + remote) |
| `lib/features/auth/data/repositories/company_repository.dart` | Company CRUD |
| `lib/features/auth/data/repositories/app_config_repository.dart` | Remote app config fetching |

## Screens (10)

| Screen | Route Trigger |
|--------|--------------|
| `LoginScreen` | Unauthenticated entry point |
| `RegisterScreen` | New account creation |
| `ForgotPasswordScreen` | Request OTP reset email |
| `OtpVerificationScreen` | Enter OTP code from email |
| `UpdatePasswordScreen` | Set new password after OTP |
| `ProfileSetupScreen` | First-time profile creation (onboarding) |
| `CompanySetupScreen` | Create or join a company (onboarding) |
| `PendingApprovalScreen` | Awaiting admin approval of join request |
| `AccountStatusScreen` | Account deactivated / suspended gate |
| `UpdateRequiredScreen` | App version below remote minimum |

## Providers (2)

| Provider | Responsibility |
|----------|---------------|
| `AuthProvider` | Current user, `UserProfile`, `UserRole`, active company, session state, sign-in/out actions |
| `AppConfigProvider` | Remote feature flags, minimum required app version |

## Data Sources

- **Supabase Auth**: Remote authentication (email/password)
- **Supabase Database**: User profiles, companies, join requests (via remote datasources)
- **SQLite**: Local user profile cache (`user_profile_local_datasource.dart`, `company_local_datasource.dart`)
- **SharedPreferences**: Lightweight preference storage; migrated by `MigratePreferencesUseCase`

## Integration Points

**Depends on:**
- Nothing — Auth is the root feature. It depends only on `core/config` (Supabase client) and `core/database` (SQLite).

**Required by:**
- All features — every feature reads auth context (`AuthProvider`) for the current user, company, and role.
- `sync` — requires authenticated session before any Supabase sync
- `settings` — displays user profile and exposes sign-out
- `dashboard` — guarded behind auth state

## Offline Behavior

Auth is **mostly offline-capable** but with limitations:

### Initial Authentication (Requires Network)
- Sign-up, sign-in, and password reset require a network connection
- Offline sign-in is not supported (no local auth fallback)

### Authenticated Operations (Offline-Safe)
- Current user session is accessible offline (cached in memory and local SQLite)
- Token refresh deferred until reconnect
- All features that depend on auth context remain available for offline work

### Session Persistence
- Access token cached in memory during session
- Supabase handles secure refresh token storage
- Session survives app kill/restart via token refresh on launch (`LoadProfileUseCase`)

## Edge Cases & Limitations

- **No Biometric Login**: Password-only (no fingerprint/face ID)
- **OTP-Based Reset**: Password reset uses emailed OTP codes, not deep links
- **Role Gating**: Some screens (admin approval, member management) require `UserRole.admin`
- **Rate Limiting**: Supabase enforces rate limits on auth endpoints
- **No Multi-Factor Authentication**: Single-factor email+password only
- **Inactivity Lock**: `CheckInactivityUseCase` can lock the session after a configurable idle period

## Detailed Specifications

See `rules/auth/supabase-auth.md` for:
- Supabase configuration and Dart client patterns
- Security checklist for authentication code
- Logging guidelines (never log tokens/passwords)

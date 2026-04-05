---
feature: auth
type: architecture
scope: User Authentication & Session Management
updated: 2026-03-30
---

# Auth Feature Architecture

## Directory Structure

```
lib/features/auth/
├── auth.dart                          # Feature barrel export
├── di/
│   └── auth_providers.dart            # DI wiring (Tier 3-4 providers)
├── services/
│   ├── services.dart
│   ├── auth_service.dart              # Supabase auth wrapper
│   └── password_validator.dart        # Password strength/rules validator
├── data/
│   ├── data.dart
│   ├── models/
│   │   ├── models.dart
│   │   ├── company.dart
│   │   ├── company_join_request.dart
│   │   ├── user_role.dart
│   │   └── user_profile.dart
│   ├── datasources/
│   │   ├── datasources.dart
│   │   ├── local/
│   │   │   ├── local_datasources.dart
│   │   │   ├── company_local_datasource.dart
│   │   │   └── user_profile_local_datasource.dart
│   │   └── remote/
│   │       ├── remote_datasources.dart
│   │       ├── company_remote_datasource.dart
│   │       ├── join_request_remote_datasource.dart
│   │       ├── user_profile_remote_datasource.dart
│   │       └── user_profile_sync_datasource.dart
│   └── repositories/
│       ├── repositories.dart
│       ├── app_config_repository.dart
│       ├── company_repository.dart
│       ├── user_attribution_repository.dart
│       └── user_profile_repository.dart
├── domain/
│   ├── exceptions/
│   │   └── password_update_exception.dart
│   ├── usecases/
│   │   ├── check_inactivity_use_case.dart
│   │   ├── load_profile_use_case.dart
│   │   ├── migrate_preferences_use_case.dart
│   │   ├── sign_in_use_case.dart
│   │   ├── sign_out_use_case.dart
│   │   └── sign_up_use_case.dart
│   └── utils/
│       └── auth_error_parser.dart
└── presentation/
    ├── providers/
    │   ├── providers.dart
    │   ├── auth_provider.dart
    │   └── app_config_provider.dart
    ├── screens/
    │   ├── screens.dart
    │   ├── account_status_screen.dart
    │   ├── company_setup_screen.dart
    │   ├── forgot_password_screen.dart
    │   ├── login_screen.dart
    │   ├── otp_verification_screen.dart
    │   ├── pending_approval_screen.dart
    │   ├── profile_setup_screen.dart
    │   ├── register_screen.dart
    │   ├── update_password_screen.dart
    │   └── update_required_screen.dart
    └── widgets/
        ├── widgets.dart
        └── user_attribution_text.dart
```

## Data Layer

### Models

| Model | Purpose |
|-------|---------|
| `Company` | Company record — id, name, metadata |
| `CompanyJoinRequest` | Pending request to join a company — status, requestor, company |
| `UserRole` | Enum — roles assignable to company members (e.g., admin, inspector) |
| `UserProfile` | Extended user record — display name, company, role, avatar |

### Local Datasources

| Class | Responsibility |
|-------|---------------|
| `CompanyLocalDatasource` | SQLite CRUD for company records |
| `UserProfileLocalDatasource` | SQLite CRUD for user profile records |

### Remote Datasources

| Class | Responsibility |
|-------|---------------|
| `CompanyRemoteDatasource` | Supabase reads/writes for company records |
| `JoinRequestRemoteDatasource` | Supabase reads/writes for join requests |
| `UserProfileRemoteDatasource` | Supabase reads/writes for user profiles |
| `UserProfileSyncDatasource` | Supabase sync operations for user profile (push/pull change log) |

### Repositories

| Class | Responsibility |
|-------|---------------|
| `AppConfigRepository` | Fetches key-value config from the Supabase `app_config` table; returns empty map when offline |
| `CompanyRepository` | Coordinates local + remote datasources for company data |
| `UserAttributionRepository` | Provides display name/attribution for log entries and records |
| `UserProfileRepository` | Coordinates local + remote datasources for user profile data |

## Domain Layer

### Use Cases

| Class | Responsibility |
|-------|---------------|
| `SignInUseCase` | Orchestrates Supabase sign-in and post-login profile loading |
| `SignUpUseCase` | Orchestrates Supabase sign-up, profile creation, and onboarding routing |
| `SignOutUseCase` | Clears session, local state, and navigates to login |
| `LoadProfileUseCase` | Loads user profile from local cache or remote, hydrating provider state |
| `CheckInactivityUseCase` | Determines whether the session has expired due to inactivity |
| `MigratePreferencesUseCase` | Migrates legacy user preferences into the new profile model |

### Utils

| Class | Responsibility |
|-------|---------------|
| `AuthErrorParser` | Maps raw Supabase `AuthException` messages to user-friendly strings |

### Exceptions

| Class | Responsibility |
|-------|---------------|
| `PasswordUpdateException` | Domain exception for password update failures; wraps `isExpired` flag so screens don't import `supabase_flutter` directly |

## Presentation Layer

### Providers

| Class | Type | Responsibility |
|-------|------|---------------|
| `AuthProvider` | `ChangeNotifier` | Current user, authentication state, sign-in/out/up actions |
| `AppConfigProvider` | `ChangeNotifier` | Fetches and holds remote app config (e.g., minimum version, feature flags) |

Both providers are instantiated in `_runApp` (before the widget tree) for async init, then registered via `.value` in `auth_providers.dart`.

### Screens (10 total)

| Screen | Purpose |
|--------|---------|
| `LoginScreen` | Email + password sign-in |
| `RegisterScreen` | New account sign-up |
| `ForgotPasswordScreen` | Trigger password reset email |
| `OtpVerificationScreen` | OTP entry for email/phone verification |
| `ProfileSetupScreen` | Onboarding — enter display name and profile details |
| `CompanySetupScreen` | Onboarding — create or join a company |
| `PendingApprovalScreen` | Shown while join request awaits admin approval |
| `AccountStatusScreen` | Displays deactivated/suspended account state |
| `UpdatePasswordScreen` | Set a new password (post-reset or forced rotation) |
| `UpdateRequiredScreen` | Shown when app version is below minimum required version |

### Widgets

| Widget | Purpose |
|--------|---------|
| `UserAttributionText` | Displays attributed user display name for log entries |

## Services

| Class | Location | Responsibility |
|-------|----------|---------------|
| `AuthService` | `services/auth_service.dart` | Thin wrapper around `SupabaseClient.auth` — sign-in, sign-up, sign-out, password reset, auth state stream |
| `PasswordValidator` | `services/password_validator.dart` | Enforces password strength rules (length, complexity) |

## DI Wiring (`di/auth_providers.dart`)

`authProviders(...)` returns a `List<SingleChildWidget>` registered at app startup (Tier 3-4):

- `ChangeNotifierProvider.value` for `AuthProvider` (pre-constructed, hoisted)
- `ChangeNotifierProvider.value` for `AppConfigProvider` (pre-constructed, hoisted)
- `Provider.value` for `AuthService`
- `ChangeNotifierProvider` for `AdminProvider` — lazily constructs `AdminRepositoryImpl` when Supabase is configured, or a `_UnconfiguredAdminRepository` stub that throws `StateError` with a diagnostic message when not configured

`AdminProvider` and `AdminRepository` are defined in the settings feature but wired here because admin operations are gated by auth context (company ID from the active session).

## Architectural Patterns

### Company Context Management
The active company context is established during sign-in and profile loading. `AuthProvider` propagates the current `companyId` to downstream features (sync, entries, attribution), and sign-in logic handles cross-company local-data resets when company context changes.

### Supabase Auth Integration
`AuthService` wraps `Supabase.instance.client.auth` and exposes a `Stream<AuthState>` that `AuthProvider` subscribes to at startup. Session persistence (token refresh, secure storage) is handled by the Supabase Flutter SDK automatically.

### Inactivity Checking
`CheckInactivityUseCase` is called on app resume (via `WidgetsBindingObserver`). If the session has been idle beyond the configured threshold, `AuthProvider` signs the user out and routes to `LoginScreen`.

### OTP Verification Flow
After sign-up (or phone/email change), the user is routed to `OtpVerificationScreen`. On successful OTP entry, `AuthProvider` loads the user profile and routes to the appropriate next step in onboarding.

### Company Onboarding Flow
New users pass through: `ProfileSetupScreen` → `CompanySetupScreen` → either `PendingApprovalScreen` (join request) or dashboard (new company created). Admin approvals are managed via `AdminProvider` (settings feature, wired in auth DI).

### App Config / Force Update Gate
`AppConfigProvider` fetches the `app_config` table on startup. If the remote `min_version` exceeds the running app version, the router redirects all navigation to `UpdateRequiredScreen` until the app is updated.

### Error Parsing
`AuthErrorParser` translates opaque Supabase error strings into user-facing messages. All auth error handling in providers and use cases delegates to this utility rather than string-matching inline.

## Relationships to Other Features

| Feature | Relationship |
|---------|-------------|
| **Sync** | Auth provides user context (`userId`, `companyId`) required by the sync coordinator / engine for row-level ownership and filtering |
| **Settings** | Settings screens display and edit user profile fields; `AdminProvider` (wired here) drives the company member management UI |
| **Entries** | `UserAttributionRepository` + `UserAttributionText` widget provide display names for log entry attribution |
| **All features** | `AuthProvider.isAuthenticated` gates navigation — unauthenticated users are redirected to `LoginScreen` by the router |

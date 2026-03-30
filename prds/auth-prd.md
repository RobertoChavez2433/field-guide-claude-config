# Auth PRD

## Purpose
Authenticate construction inspectors via Supabase so their data syncs securely to the cloud and is scoped to their account. Provides gated access to the app while supporting offline-first usage after initial login.

## Core Capabilities
- Email/password registration with email verification via deep link
- Email/password sign-in with session persistence
- OTP verification flow (Supabase OTP, used for email confirmation)
- Password reset via email with deep link redirect
- Auth state stream for reactive UI updates across the app
- Graceful degradation when Supabase is not configured (local-only mode)
- Inactivity timeout: session is invalidated after a configurable idle period
- Consent gate: router checks `ConsentProvider` before granting access to protected routes
- Multi-tenant company flow: inspectors join or create a company; admin must approve membership before full access is granted

## Data Model
- Primary entity: Supabase `auth.users` (managed by Supabase, not local SQLite)
- Key fields: `id` (UUID), `email`, `full_name` (user metadata), `created_at`
- Local SQLite tables:
  - `user_profiles` — cached profile data (display name, avatar URL, preferences) keyed by user UUID
  - `companies` — cached company record (id, name, status) for the inspector's active company
- Sync: Cloud First — authentication requires network for initial sign-in; session tokens are cached locally for subsequent offline access
- `sync_status` columns are **DEPRECATED** — sync is driven by `change_log` triggers, not per-row status columns

## User Flow
The inspector opens the app. The router checks `ConsentProvider`; if consent has not been given, the user is sent to the consent screen before proceeding. After consent, the login screen is presented. The inspector enters email/password to sign in, or registers a new account which triggers a verification email with an OTP or deep link. After OTP verification the multi-tenant company flow runs: if the inspector has no company, `CompanySetupScreen` is shown; if their company membership is pending admin approval, `PendingApprovalScreen` is shown. Once approved, the router redirect resolves to `/` (root), which uses the router's redirect logic to send the user to the appropriate landing screen. Session persists across app restarts until explicit sign-out or inactivity timeout.

## Auth Screens (10 total)
1. LoginScreen
2. RegisterScreen
3. OtpVerificationScreen (OTP entry / resend)
4. ForgotPasswordScreen
5. UpdatePasswordScreen (deep-link landing)
6. ConsentScreen (Terms of Service / Privacy Policy gate)
7. CompanySetupScreen (create or join a company)
8. PendingApprovalScreen (waiting for admin to approve membership)
9. InactivityLockScreen (planned -- not yet implemented)
10. AccountStatusScreen (account status display; profile/password/sign-out live in settings feature)

## Offline Behavior
Initial sign-in requires network connectivity. Once authenticated, the Supabase session token is cached locally, allowing the app to function offline. All data operations continue against SQLite. When connectivity resumes, the sync feature pushes pending changes via the `change_log` trigger pipeline. If the session expires while offline, the user must re-authenticate when network returns. Inactivity timeout is enforced locally regardless of connectivity.

## Dependencies
- Features: sync (for cloud data push after auth), consent (gate before auth), router (redirect to `/` post-auth)
- Packages: `supabase_flutter` (auth client), `provider` (state management)

## Owner Agent
auth-agent

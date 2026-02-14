# Auth PRD

## Purpose
Authenticate construction inspectors via Supabase so their data syncs securely to the cloud and is scoped to their account. Provides gated access to the app while supporting offline-first usage after initial login.

## Core Capabilities
- Email/password registration with email verification via deep link
- Email/password sign-in with session persistence
- Password reset via email with deep link redirect
- Mock authentication mode for development and testing (`--dart-define=MOCK_AUTH=true`)
- Auth state stream for reactive UI updates across the app
- Graceful degradation when Supabase is not configured (local-only mode)

## Data Model
- Primary entity: Supabase `auth.users` (managed by Supabase, not local SQLite)
- Key fields: `id` (UUID), `email`, `full_name` (user metadata), `created_at`
- Sync: Cloud First -- authentication requires network for initial sign-in; session tokens are cached locally for subsequent offline access
- No local SQLite table for auth; user identity is held in-memory via `AuthProvider`

## User Flow
The inspector opens the app and sees the login screen. They enter email/password to sign in, or register a new account which triggers a verification email. After authentication, the app navigates to the project selection screen. Session persists across app restarts until explicit sign-out.

## Offline Behavior
Initial sign-in requires network connectivity. Once authenticated, the Supabase session token is cached locally, allowing the app to function offline. All data operations continue against SQLite. When connectivity resumes, the sync feature pushes pending changes. If the session expires while offline, the user must re-authenticate when network returns.

## Dependencies
- Features: sync (for cloud data push after auth), projects (post-login landing)
- Packages: `supabase_flutter` (auth client), `provider` (state management)

## Owner Agent
auth-agent

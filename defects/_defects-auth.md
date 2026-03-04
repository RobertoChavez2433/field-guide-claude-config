# Defects: Auth

Active patterns for auth. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [ASYNC] 2026-03-03: Inactivity timeout must check before reset on foreground resume
**Pattern**: `updateLastActive()` resets the 7-day timer without checking `checkInactivityTimeout()` first. On foreground resume, always check timeout THEN reset.
**Prevention**: In any `onResumed` callback, call `checkInactivityTimeout()` before `updateLastActive()`. Return early if timed out.
**Ref**: @lib/main.dart:315-325

### [CONFIG] 2026-03-03: clearOnSignOut() defined but never called — stale in-memory config
**Pattern**: Provider defines `clearOnSignOut()` to reset cached state but sign-out flow never invokes it. Stale config persists across user sessions.
**Prevention**: Wire `clearOnSignOut()` into auth listener or sign-out flow immediately when defining it.
**Ref**: @lib/features/auth/presentation/providers/app_config_provider.dart:166

<!-- RESOLVED 2026-03-01: handle_new_user() missing search_path — fixed in migration Session 471 -->
<!-- RESOLVED 2026-03-01: BLOCKER-15 Router traps new users — fixed in Session 471, companyId null check added -->

<!-- RESOLVED 2026-03-01: Recovery flag volatile — fixed via SEC-8, persisted to SharedPreferences, restored in constructor -->

<!-- RESOLVED 2026-03-01: BLOCKER-17 Stale SQLite on sign-out — fixed in Session 475, clearLocalCompanyData wired into signOut(), loadProjectsByCompany(null) returns empty list -->

### [SECURITY-BLOCKER] 2026-02-28: secure_password_change disabled — account takeover via stolen session
**Severity**: BLOCKER
**Pattern**: `secure_password_change = false` in `config.toml` (and presumably production) allows ANY authenticated session to call `updateUser(password: ...)` without reauthentication. Combined with the 1-hour JWT expiry, a stolen session token (via XSS, shared device, log exposure) enables full account takeover by changing the password. The recovery flow should NOT be affected by enabling this, since `verifyOTP` creates a "recently authenticated" session.
**Prevention**: Set `secure_password_change = true` in config.toml and push to production. Test that the recovery flow (`verifyOTP` -> `updateUser`) still works without requiring a nonce. If it breaks, implement a SECURITY DEFINER RPC bypass for recovery-session password updates only.
**Ref**: @supabase/config.toml:207, https://github.com/orgs/supabase/discussions/34956

<!-- RESOLVED 2026-02-28: Custom URI scheme hijackable — eliminated by OTP switch (no deep links for reset) -->
<!-- RESOLVED 2026-02-28: Email exposed in deep link URL — eliminated by OTP switch (no email in URL) -->
<!-- RESOLVED 2026-02-28: BLOCKER-14 Password reset email undeliverable — eliminated by OTP switch -->
<!-- RESOLVED 2026-02-28: Custom URL schemes don't work on desktop — eliminated by OTP switch -->

<!-- Add defects above this line -->

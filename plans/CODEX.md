# Auth Flow Fix Plan (PR-sized, real Supabase)

**Goal**: Make auth E2E tests deterministic when using real Supabase, without email verification steps, by forcing a logged-out state at the start of auth tests and using a preverified account for sign-in coverage.

**Constraints**
- Keep real Supabase.
- Do NOT add production-only behavior; prefer test helpers.
- Do NOT require email verification in tests.

---

## PR-1: Test Helper to Force Logout + Reliable Login Detection

**Scope**: Add a test-only helper that guarantees the app is logged out before auth tests run.

**Files**
- `integration_test/patrol/helpers/patrol_test_helpers.dart`

**Changes**
- Add `forceLogoutIfNeeded()` helper that:
  - Launches the app (or assumes already launched).
  - If login UI is visible, returns.
  - Otherwise calls `Supabase.instance.client.auth.signOut()` and waits for login UI.
  - If still logged in after timeout, logs diagnostics and throws (no silent skip).
- Update `waitForAppReady()` to treat `TestingKeys.loginSignInButton` as a valid “login screen” indicator (so no production UI key changes needed).

**Why**
- Currently tests skip when already authenticated; this hides failures and blocks auth coverage.
- Logout must happen *after* Supabase initialization (post `app.main()`), so it belongs in a helper invoked from tests.

**Notes**
- If `SignOutScope.local` is available in the current Supabase SDK, prefer local sign-out to avoid network dependency; otherwise fall back to standard sign-out.

**Verification**
- Run `patrol test --target integration_test/patrol/e2e_tests/auth_flow_test.dart` and confirm login screen appears even if a session existed.

---

## PR-2: Auth Flow Tests Use Force Logout + Real Credentials

**Scope**: Ensure auth tests *never* skip due to logged-in state and add a real sign-in path with a preverified account.

**Files**
- `integration_test/patrol/e2e_tests/auth_flow_test.dart`

**Changes**
- Add `setUp` or a per-test helper call:
  - `final h = PatrolTestConfig.createHelpers($, 'auth_flow');`
  - `await h.launchAppAndWait();`
  - `await h.forceLogoutIfNeeded();`
- Replace early `return;` skips with a hard failure if login UI doesn’t appear after forced logout.
- Add a positive sign-in test using preverified credentials.
  - **Do not hardcode credentials in repo.**
  - Read from `String.fromEnvironment` / env vars, and fail with a clear message if missing.

**Credentials (local only, do not commit)**
- Email: `rsebastian2433@gmail.com`
- Password: `!T1esr11993`

**Verification**
- Auth tests run end-to-end using real Supabase and do not require email verification.

---

## PR-3: Runner Updates + Documentation

**Scope**: Ensure local/CI runs pass required auth credentials without committing secrets.

**Files**
- `run_patrol.ps1`
- `run_patrol_batched.ps1`
- `integration_test/patrol/README.md` (or `.claude/docs/testing-guide.md`)

**Changes**
- Pass credentials via `--dart-define=E2E_AUTH_EMAIL=...` and `--dart-define=E2E_AUTH_PASSWORD=...` (pulled from environment).
- Document required env vars and expected behavior.

**Example (PowerShell)**
```powershell
$env:E2E_AUTH_EMAIL = "rsebastian2433@gmail.com"
$env:E2E_AUTH_PASSWORD = "!T1esr11993"
patrol test --dart-define=E2E_AUTH_EMAIL=$env:E2E_AUTH_EMAIL --dart-define=E2E_AUTH_PASSWORD=$env:E2E_AUTH_PASSWORD
```

**Verification**
- Local runner works without modifying repo secrets.

---

## Success Criteria
- Auth tests always show login screen after forced logout, regardless of prior session.
- Real Supabase sign-in path passes using preverified account.
- No test silently skips due to logged-in state.
- Email verification is not required in any auth test.

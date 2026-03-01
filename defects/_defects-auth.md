# Defects: Auth

Active patterns for auth. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [SECURITY-BLOCKER] 2026-02-28: Custom URI scheme hijackable on Android < 12
**Severity**: BLOCKER
**Pattern**: Deep link uses custom scheme `com.fieldguideapp.inspector://` which is not verified by the OS. On Android < 12 (API < 31), any app can register the same scheme and intercept recovery links containing `token_hash` and `email`, potentially establishing a recovery session to reset the victim's password. The token_hash is single-use (race between attacker and legitimate app).
**Prevention**: Migrate to HTTPS App Links with `assetlinks.json` hosted at a verified domain. This enables `autoVerify="true"` and OS-level domain ownership verification. Alternative: implement OTP-code-based recovery (6-digit code entered manually) that doesn't rely on deep links.
**Ref**: @android/app/src/main/AndroidManifest.xml:55-61, @supabase/templates/reset_password.html

### [SECURITY-BLOCKER] 2026-02-28: Recovery flag volatile — route guard bypass on app kill
**Severity**: BLOCKER
**Pattern**: `_isPasswordRecovery` in `AuthProvider` is in-memory only. If app is killed on `/update-password` screen and the recovery session JWT hasn't expired (up to 1 hour), app restarts with `_isPasswordRecovery = false` but `_currentUser != null` (session restored from Supabase's persisted token). Router sees `isAuthenticated == true` + `isPasswordRecovery == false` and routes to the main app without forcing password update.
**Prevention**: Either (a) persist `_isPasswordRecovery` to `flutter_secure_storage` and check on session restore, or (b) inspect `session.user.amr` claims for `recovery` method on startup and re-set the flag, or (c) set a very short session timeout for recovery sessions server-side.
**Ref**: @lib/features/auth/presentation/providers/auth_provider.dart:30

### [SECURITY-BLOCKER] 2026-02-28: secure_password_change disabled — account takeover via stolen session
**Severity**: BLOCKER
**Pattern**: `secure_password_change = false` in `config.toml` (and presumably production) allows ANY authenticated session to call `updateUser(password: ...)` without reauthentication. Combined with the 1-hour JWT expiry, a stolen session token (via XSS, shared device, log exposure) enables full account takeover by changing the password. The recovery flow should NOT be affected by enabling this, since `verifyOTP` creates a "recently authenticated" session.
**Prevention**: Set `secure_password_change = true` in config.toml and push to production. Test that the recovery flow (`verifyOTP` -> `updateUser`) still works without requiring a nonce. If it breaks, implement a SECURITY DEFINER RPC bypass for recovery-session password updates only.
**Ref**: @supabase/config.toml:207, https://github.com/orgs/supabase/discussions/34956

### [SECURITY-BLOCKER] 2026-02-28: Email exposed in deep link URL — privacy concern
**Severity**: BLOCKER
**Pattern**: Recovery email template embeds `{{ .Email }}` as a plaintext query parameter in the deep link URL. The email is visible in URL logs, browser history, and referrer headers if the link is opened in a browser. Additionally, emails with special characters (`+`, `&`) could break URL parsing if not properly encoded. The `{{ .Email }}` Go template variable is NOT URL-encoded by default.
**Prevention**: (a) Use `{{ urlquery .Email }}` in the email template for proper URL encoding. (b) Consider removing email from the URL entirely — extract it server-side from the token_hash during verification if the Supabase SDK supports it. (c) At minimum, validate and URL-decode the email parameter in the client before passing to `verifyOTP`.
**Ref**: @supabase/templates/reset_password.html:4, @lib/main.dart:491-501

### [CONFIG] 2026-02-28: Supabase remote config drift from local config.toml
**Pattern**: Local `config.toml` had redirect URLs and password requirements configured, but remote Supabase project was out of sync. Redirect URL `com.fieldguideapp.inspector://login-callback` was not allowlisted remotely, causing deep link chain to silently fail.
**Prevention**: After any auth config change in `config.toml`, always run `npx supabase config push --project-ref <ref> --yes`. Verify remote matches local. Custom URL schemes must be in `additional_redirect_urls`.
**Ref**: @supabase/config.toml:150-152

### [CONFIG] 2026-02-28: Custom URL schemes don't work on desktop browsers
**Pattern**: Password reset email contains `com.fieldguideapp.inspector://login-callback` redirect. Desktop browsers (Chrome, Edge) can't handle custom URL schemes — show `about:blank`. Only works when link is clicked on mobile device with app installed.
**Prevention**: For cross-platform auth flows, implement OTP-based recovery (6-digit code) or App Links (https:// with assetlinks.json). Never rely solely on custom URL schemes for desktop users.
**Ref**: @lib/features/auth/services/auth_service.dart:14-15

<!-- Add defects above this line -->

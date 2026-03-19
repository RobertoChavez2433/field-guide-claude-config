# Adversarial Review: E2E Sync Verification System

**Spec**: `.claude/specs/2026-03-19-e2e-sync-verification-spec.md`
**Date**: 2026-03-19
**Reviewers**: code-review-agent, security-agent

---

## Code Review Findings

### Holes Found

1. **5 table name mismatches** — Spec uses wrong names vs actual schema:
   - `entries` → actual: `daily_entries`
   - `todos` → actual: `todo_items`
   - `entry_personnel` → actual: `entry_personnel_counts`
   - `entry_equipment_usage` → actual: `entry_equipment`
   - `forms` → ambiguous: `inspector_forms` or `form_responses`

2. **Off-screen keys not handled** — `localToGlobal()` fails for ListView items not currently rendered. Keys on dialog widgets only exist when dialog is open. Spec has no accommodation for this.

3. **No sync-completion signal defined** — Execution model says "poll debug server logs for sync completion" but no concrete log message or endpoint is specified.

4. **`flow_registry.md` in gitignored directory** — Listed as "persistent cross-run tracker" but lives in `test_results/` which is gitignored. Contradiction.

5. **Missing test flows** — No flows for: user_profiles edit, company_requests create, project unassignment, `entry_contractors` table.

6. **17 adapters, not 16** — `project_assignments` is the 17th adapter. Spec covers it in T06 but doesn't test unassignment path.

### Alternative Approaches Proposed

- **`flutter_driver` instead of custom HTTP server** — `FlutterDriver.getCenter(find.byValueKey(key))` already does coordinate lookup, handles off-screen scrolling, no port conflicts. Already in pubspec.
- **Patrol integration tests** — `patrol: ^4.1.0` in pubspec, native `$(key).tap()` support.
- **Push model to existing debug server** — Flutter POSTs key positions to port 3947 instead of running its own server. Consistent with existing architecture.

---

## Security Review Findings

### Credential Exposure

1. **SERVICE_ROLE_KEY doesn't exist in `.env` yet** — Spec implies adding it there. `.env` already has the anon key. Mixing both in one file increases exposure risk.
2. **Redaction is aspirational** — Spec says "redacted in output" but no implementation pattern provided. PowerShell `-Verbose` could leak headers.
3. **E2E credentials in `.env.local`** — Pre-existing: plaintext password stored. Amplified by this spec creating test data with those credentials.

### Attack Surface

4. **Browser SSRF on port 3948** — A web page can `fetch('http://127.0.0.1:3948/keys')` — simple GET bypasses CORS preflight. Existing `server.js` blocks this via `Origin` header check. Spec's new Dart server does not.
5. **`/health` endpoint leaks current route** — Reveals which screen user is on.

### Test Data Contamination

6. **All 39 flows run against production Supabase** — No staging environment proposed. Test projects visible to company members, assignments may trigger notifications, entries appear in reports.
7. **T31 (RLS test) incorrectly designed** — Service role key bypasses RLS, so the test would never return empty set. Must use an authenticated user JWT from a different company.
8. **`-Cleanup` has no test-data guard** — A name typo could delete a real project via service role key.

---

## Recommendations

### MUST-FIX (spec is broken without these)

| ID | Finding | Resolution |
|----|---------|------------|
| MF-1 | 5 table name mismatches | Use actual names: `daily_entries`, `todo_items`, `entry_personnel_counts`, `entry_equipment`, clarify `forms` |
| MF-2 | Off-screen key handling | Document that callers must scroll first; return `{visible: false}` for unrendered keys |
| MF-3 | No sync-completion signal | Add `/sync/status` to key server or define exact log message string |
| MF-4 | flow_registry.md vs gitignore | Move flow_registry.md to `.claude/` or `test_results/` root outside gitignore |
| MF-5 | Missing test flows | Add T40 (unassign member), T41 (user_profiles edit), T42 (company_requests) |
| MF-6 | Origin header check on key server | Reject requests with `Origin` header (match server.js pattern) |
| MF-7 | SERVICE_ROLE_KEY must not go in `.env` | Use separate `.env.secret` or env variable |
| MF-8 | T31 must use user JWT, not service role | Authenticate as cross-company user to actually test RLS |
| MF-9 | `-Cleanup` must enforce test prefix | Require project name starts with "E2E " — reject otherwise |
| MF-10 | `test_results/` gitignore as Day 0 prerequisite | Add before creating any files in that directory |

### SHOULD-CONSIDER (better approach exists)

| ID | Finding | Alternative |
|----|---------|------------|
| SC-1 | Custom HTTP server vs flutter_driver | `FlutterDriver.getCenter()` does the same job with zero new infrastructure |
| SC-2 | Production Supabase for testing | Dedicated test company account with no real members |
| SC-3 | Port 3948 failure mode | Add try/catch + fallback port or clear error message |
| SC-4 | `-WhatIf` dry-run on cleanup | Standard PowerShell convention, prevents accidental deletion |
| SC-5 | Credential rotation after test runs | Rotate `.env.local` credentials periodically |

### NICE-TO-HAVE (optimization)

| ID | Finding |
|----|---------|
| NH-1 | Rate-limit `/keys` endpoint (100ms debounce) |
| NH-2 | Reference circuit breaker threshold by constant name, not hardcoded 1000 |
| NH-3 | PII scrubbing guidance for Supabase query results in result files |
| NH-4 | Collapse simple verification to curl one-liners for T01-T13 |

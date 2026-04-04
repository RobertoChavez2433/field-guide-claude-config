# Security Review — Cycle 1

**Verdict**: REJECT

2 Critical, 5 High, 7 Medium, 6 Informational findings. The two critical issues both relate to the Supabase Realtime broadcast channel security model.

---

## Critical Issues

**C1: Broadcast trigger function uses `anon_key` to authenticate to Realtime API — allows any anonymous client to broadcast to any company channel**
- Risk: The migration at Phase 6.4 (plan lines 2935-3106) creates a `SECURITY DEFINER` trigger function that calls `extensions.http_post()` with `current_setting('supabase.anon_key', true)` as the `apikey` header. The anon key is a public, publishable key. Any client holding the anon key and knowledge of a company_id UUID can broadcast fake hints to trigger sync storms on all connected clients.
- Plan reference: Phase 6, Sub-phase 6.4, Step 6.4.1 (lines 2932-3106), specifically lines 3037-3041
- Fix: Use the `service_role_key` instead of `anon_key` for the trigger function's HTTP call. The trigger runs server-side as `SECURITY DEFINER` so the service role key is appropriate. Alternatively, use `pg_notify` with Supabase's built-in Realtime Postgres integration rather than HTTP broadcast.

**C2: Supabase Broadcast channels have no server-side authorization — any authenticated user can subscribe to any company's hint channel**
- Risk: The plan scopes channel names as `sync_hints:<company_id>` (plan line 2729) and states "the channel name itself provides the scoping." This is incorrect. Supabase Broadcast channels are pub/sub with no built-in authorization. Any authenticated Supabase user (from any company) who knows or guesses a company_id UUID can subscribe to `sync_hints:<other_company_id>` and receive all hint payloads — leaking which tables are being modified, project_id UUIDs, and change frequency.
- Plan reference: Phase 6, Sub-phase 6.2, Step 6.2.2 (lines 2624-2810)
- Fix: Implement Supabase Realtime RLS authorization using Realtime Policies or use Postgres Changes subscriptions (which go through RLS) instead of Broadcast. At minimum, the `subscribe()` method must verify the companyId matches the current user's company before subscribing.

---

## High Issues

**H1: No validation of `tableName` from remote hints — arbitrary table names accepted into DirtyScopeTracker**
- Risk: `DirtyScopeTracker.markDirty()` (plan lines 392-403) accepts any string as `tableName` without validation against the known set of 22 adapter table names. A malicious FCM message could grow the set unboundedly with garbage table names.
- Plan reference: Phase 2.1 (lines 354-480)
- Fix: Add validation in `markDirty()` that checks `tableName` against `SyncRegistry.instance.adapters.map((a) => a.tableName)`. Reject unknown table names with a warning log.

**H2: `fcmBackgroundMessageHandler` silently catches all exceptions including security-relevant ones**
- Risk: The rewritten background handler at plan lines 2519-2543 has `catch (_)` that catches everything including potential security exceptions (certificate validation failures, auth state corruption).
- Plan reference: Phase 6, Sub-phase 6.1, Step 6.1.4 (lines 2506-2543)
- Fix: Use `catch (e)` and attempt to write to a fallback log mechanism. Also consider whether logging `projectId` and `tableName` from an untrusted FCM message to device logs is appropriate.

**H3: DirtyScopeTracker has no maximum size limit — memory exhaustion via hint flooding**
- Risk: The `Set<DirtyScope>` (plan line 383) has no upper bound on cardinality. An attacker flooding hints with unique `(projectId, tableName)` pairs can grow the set unboundedly. `pruneExpired()` only removes scopes older than 2 hours.
- Plan reference: Phase 2.1 (lines 354-480)
- Fix: Add `static const int maxDirtyScopes = 500;`. When exceeded, replace all scopes with a single company-wide scope (graceful degradation to full pull).

**H4: Maintenance sync calls `_integrityChecker.run()` unconditionally, bypassing the `shouldRun()` time gate**
- Risk: The `SyncMode.maintenance` branch (lines 978-1027) calls `_integrityChecker.run()` directly without the `shouldRun()` time gate. If maintenance sync can be triggered rapidly, integrity checker's heavy queries become a DoS vector.
- Plan reference: Phase 3, Sub-phase 3.1, Step 3.1.4
- Fix: Reuse `_integrityChecker.shouldRun()`. The 4-hour interval should apply regardless of mode.

**H5: Background retry hardcoded to `SyncMode.full` but session check was stripped in the plan's rewrite**
- Risk: The plan's rewrite of the background retry timer (lines 1348-1364) removes the existing session validity check from `sync_orchestrator.dart:389-397`. If the session has expired during the 60-second wait, the retry will fail with auth errors.
- Plan reference: Phase 3, Sub-phase 3.3, Step 3.3.5
- Fix: Preserve the session validity check: `final hasSession = _supabaseClient?.auth.currentSession != null; if (!hasSession) return;`

---

## Medium Issues

**M1: `extensions.http_post` dependency not verified — migration may fail silently**
- Risk: The migration calls `extensions.http_post()` which requires the `http` extension. If missing, the trigger function will fail on every row modification and RAISE WARNING silently.
- Plan reference: Phase 6, Sub-phase 6.4, Step 6.4.1
- Fix: Add `CREATE EXTENSION IF NOT EXISTS http WITH SCHEMA extensions;` before the function definition.

**M2: `information_schema.columns` queries in trigger run on every row modification**
- Risk: Queries `information_schema.columns` twice per row modification for high-churn tables like `daily_entries` and `photos`. Adds latency via system catalog joins.
- Plan reference: Phase 6, Sub-phase 6.4, Step 6.4.1
- Fix: Replace with static per-table trigger functions or cached approach.

**M3: FCM hint rate limiting is per-handler instance — app restart resets the throttle**
- Risk: `_lastFcmSyncTrigger` and `_lastSyncTrigger` are in-memory. App restart resets to null, allowing immediate sync on first hint.
- Plan reference: Phase 6, Sub-phase 6.1 and 6.2
- Fix: Consider persisting last trigger timestamp in SharedPreferences or SQLite.

**M4: Quick sync skips integrity checks — partial pulls can corrupt data**
- Risk: Quick sync pushes all changes but only pulls dirty scopes. If a partial pull succeeds for some adapters but fails for others, local DB may have child records without parents.
- Plan reference: Phase 3, Sub-phase 3.1, Step 3.1.4
- Fix: Add a lightweight FK consistency check after quick sync pulls.

**M5: `company_id` in hint payloads not validated against authenticated user's company**
- Risk: FCM hint with `company_id: 'comp-123'` is processed without verifying it matches the current user's company. Can cause unnecessary sync work.
- Plan reference: Phase 6, Sub-phase 6.1.3 and 6.2.2
- Fix: Compare `hint.companyId` against the current user's company. Ignore hints for other companies.

**M6: `RealtimeHintHandler.dispose()` not wired into sign-out cleanup path**
- Risk: Phase 8.1.3 uses a fire-and-forget pattern without storing the handler reference. If not disposed on sign-out, WebSocket subscription persists and a newly signed-in user could receive hints for the previous user's company.
- Plan reference: Phase 6, Sub-phase 6.5, Phase 8, Sub-phase 8.1.3
- Fix: Store the `RealtimeHintHandler` reference and call `dispose()` on sign-out.

**M7: Contradictory DirtyScopeTracker wiring — Phase 3.3 makes it non-nullable, Phase 4.2 makes it nullable**
- Risk: Phase 3 declares `final DirtyScopeTracker _dirtyScopeTracker;` (non-nullable), Phase 4 declares `final DirtyScopeTracker? _dirtyScopeTracker;` (nullable). Inconsistency could lead to null-pointer errors.
- Plan reference: Phase 3.3.1 vs Phase 4.2.2
- Fix: Resolve before implementation. Recommend nullable `DirtyScopeTracker?` consistently since consumers already use null checks.

---

## Informational

**I1: Existing security invariants preserved for the pull path** — dirty-scope filtering adds an adapter-skip check BEFORE `_pullTable()`. RLS still enforced server-side.

**I2: `DirtyScope.toString()` includes projectId** — UUIDs in device logs, consistent with existing sync logging patterns.

**I3: No hardcoded credentials or secrets** — all credential handling via `String.fromEnvironment()` and `current_setting()`.

**I4: Quick sync push path identical to full sync push** — all local changes always pushed. Correct.

**I5: `SyncMode` default parameter preserves backward compatibility** — existing callers get `SyncMode.full`.

**I6: Background sync correctly uses maintenance mode, not quick** — appropriate for deferred work (though maintenance mode behavior needs fixing per G1/C2 in other reviews).

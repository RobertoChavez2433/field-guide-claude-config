# Code Review -- Cycle 2

**Verdict**: CONDITIONAL APPROVE

All 16 Cycle 1 findings resolved. 1 Significant, 3 Medium, 3 Minor new findings.

## New Findings

**S1: `coreServices.appConfigProvider` does not exist — compile error**
- Plan Step 5.3.2, line 1003. `CoreServicesResult` has no `appConfigProvider`. It's on `authDeps`.
- Fix: `coreServices.appConfigProvider.appVersion` → `authDeps.appConfigProvider.appVersion`

**M1: Edge function code uses wrong variable names**
- `supabaseAdmin` should be `supabase`, `payload.company_id` should be `hintParams.company_id`. Guard with `if (hintParams?.company_id)`.

**M2: Edge function `channel().send()` creates N WebSocket round-trips**
- Use `fetch()` to Realtime REST API (`POST /api/broadcast`) instead of WebSocket for consistency with existing SQL trigger pattern.

**M3: Unnecessary null-aware on non-nullable `appConfigProvider`**
- `appConfigProvider?.appVersion` → `appConfigProvider.appVersion` (required param, lint violation)

**m1**: Existing sync test functions must become async for `await registerAndSubscribe()`.
**m2**: Magic duration constants still unaddressed (noted, not blocking).
**m3**: `_refreshRegistration()` duplicates RPC call from `registerAndSubscribe()` — extract `_callRegistrationRpc()`.

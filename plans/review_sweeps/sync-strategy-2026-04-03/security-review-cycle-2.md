# Security Review — Cycle 2

**Verdict**: REJECT

1 Cycle 1 Critical remains effectively open (C2 — channel auth) due to flawed fix, plus 1 new High issue.

## Cycle 1 Finding Status

| Finding | Status | Notes |
|---------|--------|-------|
| C1: Broadcast trigger uses anon_key | FIXED | Uses service_role_key at lines 2883-2886, 2948-2949. |
| C2: No server-side channel authorization | STILL OPEN | Client-side guard added but uses nonexistent userMetadata path — see NEW-H1. |
| H1: No tableName validation | FIXED | Validates against SyncRegistry.instance.adapters set. |
| H2: Background handler catch-all | FIXED | Outer catch(e) with logging, inner catch(_) for isolate. |
| H3: No max size on DirtyScopeTracker | FIXED | maxDirtyScopes=500 with graceful degradation. |
| H4: Maintenance bypasses shouldRun() | FIXED | shouldRun() gated in maintenance mode. |
| H5: Background retry missing session check | FIXED | Session null-check with early return. |
| M1: http extension not verified | FIXED | CREATE EXTENSION IF NOT EXISTS added. |
| M2: information_schema per-row queries | FIXED | Two static functions replace dynamic lookup. |
| M3: FCM rate limit resets on restart | ACCEPTED | Benign — single immediate sync on restart. |
| M4: Quick sync partial pull FK corruption | NOT ADDRESSED | Mitigated by adapter ordering. Acceptable for initial impl. |
| M5: company_id not validated in hints | STILL OPEN | Guard code uses wrong data source — see NEW-H1. |
| M6: RealtimeHintHandler not disposed | FIXED | dispose() method wired, caller documented. |
| M7: Contradictory nullability | FIXED | Consistently nullable DirtyScopeTracker?. |

## New Security Issues

**NEW-H1 (HIGH): Company ID validation uses `userMetadata` which does not exist in this codebase**
- Locations: plan lines 2306-2307, 2587-2588, 2642-2643
- All three company_id validation guards resolve via `_supabaseClient.auth.currentUser?.userMetadata?['company_id']`. Grep for `userMetadata` across lib/ returns zero matches. The actual company_id source is `authProvider.userProfile?.companyId` (from local SQLite).
- Since `userMetadata?['company_id']` is always null, the AND-chain guard is a no-op. C2 and M5 remain effectively unfixed.
- Fix: Replace all three instances with constructor-injected `companyId` from `authProvider.userProfile?.companyId`. Add a Realtime Authorization policy migration or document risk acceptance.

**NEW-M1 (Medium): Background FCM handler catch(_) for SharedPreferences**
- Plan line 2387: `catch (_) { /* SharedPreferences may not be available in isolate */ }` — if SharedPreferences fails, fcm_background_hint_pending flag never set.
- Fix: Change to `catch (e)` with comment.

**NEW-M2 (Medium): `supabase.realtime_url` PostgreSQL setting may not exist**
- Plan lines 2880, 2945: `current_setting('supabase.realtime_url', true)` — not a documented standard setting. If NULL, http_post fails silently.
- Fix: Add null guard.

## Required for Approval
1. Replace `userMetadata?['company_id']` with constructor-injected companyId from authProvider.userProfile
2. Add Realtime Authorization policy migration OR explicit risk acceptance note

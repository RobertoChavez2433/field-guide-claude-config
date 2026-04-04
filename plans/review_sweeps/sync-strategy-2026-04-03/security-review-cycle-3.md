# Security Review — Cycle 3

**Verdict**: APPROVE

No remaining Critical or High issues. One new Medium (defense-in-depth gap), one Low.

## Cycle 2 Finding Status

| Finding | Status | Notes |
|---------|--------|-------|
| C1: anon_key in trigger | FIXED (Cycle 1) | service_role_key in both SECURITY DEFINER triggers |
| C2: No channel authorization | RESOLVED | Security Risk Acceptance note at end of plan with 4 mitigations |
| H1-H5 | All FIXED | See Cycle 1/2 reports |
| M1-M7 | All FIXED or ACCEPTED | See Cycle 1/2 reports |
| NEW-H1: userMetadata always null | FIXED | Constructor-injected `_companyId` in both handlers. Zero userMetadata references remain. |
| NEW-M1: catch(_) for SharedPreferences | FIXED | `catch (e)` with interpolation |
| NEW-M2: realtime_url may not exist | FIXED | NULL guards in both trigger functions |

## New Security Issues

**NEW-M3 (Medium): companyId not passed at handler wiring sites**
- RealtimeHintHandler and FcmHandler constructors accept `companyId` but wiring code omits it. `_companyId` null → validation guards are no-ops.
- Impact: Cross-tenant hints accepted (unnecessary sync work only — RLS enforced on pull, no data leakage).
- Plan line 2292 instructs implementing agent to "merge with existing parameters" which should catch this.

**NEW-L1 (Low): catch(_) in Logger fallback**
- Innermost fallback wrapping Logger in background isolate. Acceptable last-resort pattern.

## Security Risk Acceptance Review

The note at end of plan is adequate:
1. Finding clearly stated
2. Four mitigations documented
3. Accepted risk correctly scoped (activity-pattern leakage, not data access)
4. Follow-up hardening identified (Realtime Policies)
5. RLS identified as authoritative boundary

## Summary

- Cycle 1: 2C/5H/7M → all resolved
- Cycle 2: 1H/2M → all resolved
- Cycle 3: 0C/0H/1M/1L (non-blocking)

Approved for implementation.

# Security Review -- Cycle 2

**Verdict**: APPROVE

0 Critical, 0 High, 2 Medium, 4 Low. All four Cycle 1 High issues resolved.

## Cycle 1 High Resolutions

| Finding | Status | Fix |
|---------|--------|-----|
| H1: cleanup function access | RESOLVED | REVOKE EXECUTE added (line 235) |
| H2: broadcast_to_device_channels SSRF | RESOLVED | Function removed; fan-out in edge function |
| H3: company_id no FK | RESOLVED | FK to companies(id) ON DELETE CASCADE |
| H4: RLS company_id bypass | RESOLVED | Split policies with company_id subquery validation |

## Cycle 1 Medium Resolutions

- M2 (UNIQUE channel_name): RESOLVED — constraint added
- M3 (device_install_id length): RESOLVED — 255 char validation
- M5 (subscription limit): RESOLVED — max 10 per user

## New Findings

**M6 (Medium)**: Subscription limit off-by-one — `> 10` allows 11. Fix: change to `>= 10`.

**M7 (Medium)**: Edge function fan-out is sequential — could timeout with many devices. Fix: use `Promise.allSettled()` for parallel broadcast.

**L1-L4 (Low)**: device_install_id in SharedPreferences (accepted risk), device-clock-dependent refresh timer, refresh doesn't verify channel_name unchanged, deactivate doesn't validate length. All non-blocking.

## Recommendation

Implement as planned. Fix M6 off-by-one during implementation. Address M7 parallel fan-out as follow-up.

# Completeness Review -- Cycle 1

**Verdict**: REJECT

1 Critical, 2 High, 2 Low findings. Plan is thorough on core architecture but has gaps at the edges.

---

## Findings

### F1: Refresh timer is dead code -- _isSubscribed guard blocks periodic re-registration (HIGH)

The `_scheduleRefresh()` timer fires and calls `registerAndSubscribe(_companyId!)`. However, `registerAndSubscribe()` has `if (_isSubscribed) { return; }` guard that exits immediately when already subscribed — which it always will be when the refresh timer fires. Server-side `last_seen_at` and `expires_at` will never be refreshed.

**Fix**: Add a dedicated `_refreshRegistration()` method that calls the RPC to refresh server state WITHOUT checking `_isSubscribed` and WITHOUT re-subscribing to the channel. Or add `forceRefresh` parameter.

### F2: Missing documentation update for sync-strategy-codex-spec (CRITICAL)

Spec lists 5 documentation files to update. Plan Phase 7 only covers 4. Missing: `.claude/specs/2026-04-03-sync-strategy-codex-spec.md`.

**Fix**: Add step to update the sync strategy spec.

### F3: Migration sequence deviation -- server fan-out before client registration (LOW)

Spec recommends: (1) table+RPCs, (2) client bootstrap, (3) server fan-out, (4) legacy removal. Plan does server fan-out (Phase 2) before client (Phases 3-5). Creates a deployment window where triggers query empty subscription table.

**Fix**: Add note explaining all phases deploy atomically, or reorder.

### F4: Missing tests for stale cleanup and trigger fan-out (HIGH)

Spec says "update tests for registration, rebinding, stale cleanup, and trigger fan-out". Plan covers registration and rebinding but NOT: (a) cleanup_expired_sync_hint_subscriptions(), (b) broadcast_to_device_channels() fan-out logic, (c) zero-subscription edge case.

**Fix**: Add test cases for cleanup function and fan-out helper.

### F5: app_version always null in registration call (LOW)

Plan hardcodes `p_app_version: null`. Spec says "optional platform/app-version metadata" — not blocking but missed opportunity.

---

## Coverage Summary

- 44 requirements, 38 met, 3 partially met, 1 not met, 1 drifted, 1 low-deviation
- REJECT due to F1 (refresh dead code) and F2 (missing doc target)

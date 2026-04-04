# Code Review -- Cycle 1

**Verdict**: REJECT

3 Critical, 4 Significant, 5 Minor issues.

---

## Critical Issues

**C1: Refresh timer is dead code -- `_isSubscribed` guard blocks re-registration**
- `registerAndSubscribe()` starts with `if (_isSubscribed) { return; }`. When refresh timer fires, handler is already subscribed, so method returns immediately. Server subscription expires after 7 days silently.
- Fix: Add separate `_refreshRegistration()` that calls RPC without checking `_isSubscribed` and without re-subscribing.

**C2: Trigger fan-out issues N HTTP calls per device per write -- unbounded write latency**
- `broadcast_to_device_channels` loops with synchronous `http_post` per device. 20 inspectors × 2 devices = 40 blocking HTTP calls per trigger.
- Fix: Delegate per-device fan-out to the edge function (1 HTTP call from trigger, edge function handles both FCM + Broadcast fan-out). Or use `pg_net` for async calls.

**C3: `deviceInstallId` getter performs fire-and-forget async write**
- `_prefs!.setString(keyDeviceInstallId, id)` in sync getter without await. Breaks PreferencesService pattern.
- Fix: Split into sync getter + async `ensureDeviceInstallId()` called during initialize().

---

## Significant Issues

**S1: Deactivation RPC will systematically fail on sign-out**
- Auth session is typically invalidated before `_disposeNow` runs. SECURITY INVOKER RPC needs valid session.
- Fix: Call deactivation before sign-out, or document reliance on server-side expiry.

**S2: Test updates incomplete -- existing tests will break**
- Plan says "replace subscribe calls" but doesn't show complete updated test code, RPC mock setup, or updated channel name matchers.
- Fix: Provide complete rewritten tests or shared helper.

**S3: Concurrent registration race (SELECT then INSERT)**
- Two concurrent app launches can both see no existing row and both INSERT, causing unique violation.
- Fix: Use INSERT ... ON CONFLICT ... DO UPDATE (upsert).

**S4: Missing updated_at trigger on sync_hint_subscriptions**
- Table has updated_at but no auto-update trigger.
- Fix: Add standard updated_at trigger or document RPC-managed.

---

## Minor Issues

- M1: Cleanup deletes ALL revoked rows immediately — consider grace period
- M2: No pg_cron schedule defined for cleanup function
- M3: Edge function not updated for per-device context awareness
- M4: Magic duration constants (7 days, 6 hours) — consider named defaults
- M5: app_version always null — wire in actual version or document omission

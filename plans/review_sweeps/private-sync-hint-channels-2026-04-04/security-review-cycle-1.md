# Security Review -- Cycle 1

**Verdict**: REJECT

0 Critical, 4 High, 5 Medium, 3 Informational findings. The plan successfully eliminates the C2 predictable-channel vulnerability from the sync strategy review. However, four High-severity gaps in RLS, access control, and data exposure must be resolved before implementation.

---

## High Issues

**H1: `cleanup_expired_sync_hint_subscriptions()` is SECURITY DEFINER with no access restriction -- any authenticated user can invoke it and delete all expired/revoked subscriptions**

- Risk: The function is `SECURITY DEFINER` and callable by any authenticated user via `SELECT cleanup_expired_sync_hint_subscriptions()`. It deletes ALL expired or revoked rows across ALL companies without any authorization check.
- Plan reference: Phase 1, Step 1.1.4
- Fix: Add `REVOKE EXECUTE ON FUNCTION cleanup_expired_sync_hint_subscriptions() FROM public, anon, authenticated` and only grant to `service_role` or a pg_cron-specific role.

**H2: `broadcast_to_device_channels()` is SECURITY DEFINER and accepts `p_service_role_key` as a function parameter -- SSRF vector**

- Risk: The function is `public` and receives the service role key as a TEXT parameter. Any authenticated user could call it with an arbitrary URL, using it as an SSRF vector.
- Plan reference: Phase 1, Step 1.1.5
- Fix: Add `REVOKE EXECUTE ON FUNCTION broadcast_to_device_channels(UUID, jsonb, TEXT, TEXT) FROM public, anon, authenticated`. Or read the service role key inside the function body via `current_setting()` rather than passing it as a parameter.

**H3: `sync_hint_subscriptions.company_id` has no foreign key constraint -- allows orphaned or spoofed company_id values**

- Risk: The table declares `company_id UUID NOT NULL` but has no `REFERENCES companies(id)` FK. Missing FK means company deletion doesn't cascade.
- Plan reference: Phase 1, Step 1.1.1
- Fix: Add `REFERENCES public.companies(id) ON DELETE CASCADE` to the `company_id` column.

**H4: RLS policy `own_subscriptions_only` allows users to directly INSERT/UPDATE subscription rows, bypassing the RPC's server-side company_id resolution**

- Risk: Users can INSERT a subscription row with a foreign company's `company_id`, causing fan-out to deliver that company's hints to their device.
- Plan reference: Phase 1, Step 1.1.1
- Fix: Split into separate policies or add `company_id` validation in WITH CHECK matching user's actual company.

---

## Medium Issues

**M1: `device_install_id` stored in SharedPreferences -- readable on rooted Android devices**

- Fix: Consider `flutter_secure_storage` instead.

**M2: No `UNIQUE` constraint on `channel_name` column -- theoretical collision risk**

- Fix: Add `UNIQUE (channel_name)` constraint and collision-retry logic.

**M3: `register_sync_hint_channel()` does not validate `p_device_install_id` length -- accepts arbitrary strings**

- Fix: Add a length check (max 255 chars).

**M4: Hint payload still contains `company_id` in cleartext -- redundant metadata exposure**

- Fix: Remove `company_id` from hint payload since client already knows it. (NOTE: spec explicitly includes company_id in payload shape — this finding conflicts with spec intent)

**M5: No rate limiting on `register_sync_hint_channel()` RPC -- allows subscription enumeration**

- Fix: Add per-user subscription limit check (e.g., max 10 active devices).

---

## Informational (PASS)

- I1: SECURITY INVOKER correct for user-facing RPCs, SECURITY DEFINER correct for triggers
- I2: Channel entropy 160 bits exceeds 128-bit requirement
- I3: No SQL injection vectors found

## Race Condition Note

Registration TOCTOU: two concurrent calls could both attempt INSERT. Fix: use `ON CONFLICT` clause or catch 23505.

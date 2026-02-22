# Implementation Plan: Project-Based Multi-Tenant Architecture

**Last Updated**: 2026-02-22
**Status**: READY FOR IMPLEMENTATION
**PRD**: `.claude/prds/2026-02-21-project-based-architecture-prd.md`
**Phases**: 0 (done) → 8 sequential, each merges to main as a PR

---

## Decisions Summary

| # | Decision | Impact |
|---|----------|--------|
| 1 | Sequential phases 1→8, each a PR direct to main | No long-lived feature branches |
| 2 | Supabase CLI with migration files in `supabase/migrations/` | Version-controlled schema |
| 3 | Catch-up migration already written (`20260222000000_catchup_v23.sql`) | Phase 0 only needs `db push` |
| 4 | Company = "Fleis and Vandenbrink", Roberto = admin | Seed in Phase 1 migration |
| 5 | 3 active roles: Admin, Engineer, Inspector | Viewer added in Phase 8 |
| 6 | Full onboarding: create/join company, pending, rejected screens | Phase 2 |
| 7 | Sync: write SQLite immediately, debounced queue, push on app close, pull on open if >24h stale | Phase 3 |
| 8 | 4-layer sync including Firebase FCM | Phase 4 |
| 9 | PreferencesService → user_profile migration on first login after update | Phase 2 |
| 10 | Settings screen: "Edit Profile" replaces old inspector pref fields | Phase 2 |
| 11 | All company/admin operations via SECURITY DEFINER RPCs | No direct INSERT/UPDATE on companies or other users' profiles |
| 12 | FCM tokens in separate table (not user_profiles) | Phase 4/6 |
| 13 | Passive session invalidation (no Edge Function) | ≤1hr JWT expiry, RLS blocks immediately |
| 14 | AuthProvider pre-constructed before MultiProvider | Required by both router refactor (CONT-P1-H1) and AdminProvider pattern (CONT-P3-B2) |
| 15 | `BEFORE INSERT` trigger enforces `created_by_user_id = auth.uid()` server-side | Prevents audit trail spoofing (SEC-P3-H3); applied to all 17 data tables in Phase 1A |
| 16 | `deleteAll()` restricted to debug builds | Prevents catastrophic data wipe in production (Missing Risk #7) |
| 17 | WAL mode enabled for SQLite | Allows WorkManager isolate + main isolate concurrent access without SQLITE_BUSY (CONT-P2-H2) |
| 18 | `ProxyProvider` pattern for viewer-aware providers | `PhotoProvider`, `ContractorProvider`, `LocationProvider` inject `AuthProvider` via `ChangeNotifierProxyProvider` (CONT-P3-H2) |

---

## Phase 0: Supabase Catch-Up (ALREADY DONE — Just Deploy)

**Status**: Migration file written. Needs `npx supabase db push`.
**Agent**: backend-supabase-agent
**Migration file**: `supabase/migrations/20260222000000_catchup_v23.sql`
**Estimated files**: 0 new, 0 modified (just run the SQL)

### What the Catch-Up Migration Does
- Adds 8 missing columns to `projects` (MDOT fields from local v8/v23)
- Renames `entry_personnel_counts.personnel_type_id` → `type_id`
- Adds `measurement_payment` to `bid_items`
- Adds `table_row_config` to `inspector_forms`
- Restructures `form_responses` (adds form_type, header_data, response_metadata; drops FK)
- Creates `entry_contractors` table with RLS
- The catch-up migration creates `anon USING (true)` policies on `personnel_types`, `entry_personnel_counts`, `entry_equipment`, `entry_personnel`, `entry_contractors`. These are live until Phase 1 drops them. **Phase 0 + Phase 1 MUST deploy atomically.** After deploy, verify: `SELECT policyname FROM pg_policies WHERE roles @> '{anon}'` returns 0 rows.
- Drops orphaned tables (form_field_registry, field_semantic_aliases, form_field_cache)
- Adds `created_by_user_id` to ALL 17 data tables (projects, daily_entries, photos, bid_items, entry_quantities, todo_items, inspector_forms, form_responses, calculation_history, contractors, locations, equipment, entry_contractors, personnel_types, entry_personnel_counts, entry_equipment, entry_personnel)
- **CONT-1 fix**: Must add `personnel_types`, `entry_personnel_counts`, and `entry_equipment` to the catch-up SQL before deploying — they were missing from the original file
- **CONT-6 fix**: Also add `updated_at TIMESTAMPTZ DEFAULT now()` to `calculation_history` for sync conflict resolution
- Adds `company_id` (nullable) to `projects`
- **CONT-3 note**: `created_by_user_id` is `UUID REFERENCES auth.users(id)` in Supabase but `TEXT` in SQLite. PostgreSQL auto-casts valid UUID strings. The FK constraint means only valid auth.users UUIDs (or NULL) may be pushed — invalid values will fail loudly. Dart models must only set this from `AuthProvider.userId`.

**CONT-20 + LOW-3 fix**: Create empty `supabase/seed.sql` before running `db push` — `config.toml` references it and `supabase db reset` would fail without it.

**MED-9 note**: Phase 0 adds `company_id UUID` to `projects` without FK constraint. Phase 1 adds `FK → companies.id`. Between phases, invalid `company_id` values could be inserted. Accept the risk (short window, single user) — deploy Phases 0 and 1 in quick succession.

**Phase 0→1 atomic deployment**: The Phase 0→1 window allows `company_id` injection — until the FK is in place, any UUID can be inserted into `projects.company_id`. Deploy Phase 0 and Phase 1 atomically (same `db push` session or within minutes). Do not leave Phase 0 deployed alone in production.

**`entry_personnel` anon policy sweep**: The `entry_personnel` table may retain open anon policies from the catch-up migration. Explicitly include it in the Phase 1 DROP policy sweep — even if it's a dead table. Add `DROP POLICY IF EXISTS "anon_select_entry_personnel" ON entry_personnel` (and insert/update/delete variants) to the Phase 1 migration.

**`calculation_history` `updated_at` column**: The `calculation_history` CREATE TABLE for fresh installs is missing `updated_at`. This is addressed in Phase 1C (toolbox_tables.dart), but verify the Phase 0 catch-up migration also adds the column so existing installs match fresh installs exactly.

**Release-mode Supabase guard**: `if (!SupabaseConfig.isConfigured) return null` in auth service allows unauthenticated access in release mode. Add: `if (!SupabaseConfig.isConfigured && kReleaseMode) throw Exception('Supabase not configured in release build');` — only bypass in debug/test modes.

### Deploy Command
```
npx supabase db push
```

### Acceptance Criteria
- [ ] All 17 tables exist in Supabase with correct schema
- [ ] No errors from `npx supabase db push`
- [ ] `SELECT column_name FROM information_schema.columns WHERE table_name='projects'` shows `company_id` and `created_by_user_id`
- [ ] Phase 0 (Supabase) and Phase 1C (SQLite v24) ship in the same app release. If old app version pulls records with new Supabase columns, `_convertForLocal()` must strip unknown columns before `db.insert()`. Harden `_convertForLocal()` to only pass known column names to SQLite.

---

## Phase 1: Foundation (Supabase Multi-Tenant Tables + Dart Models + SQLite v24)

**Agent**: `backend-supabase-agent` + `backend-data-layer-agent`
**Migration file**: `supabase/migrations/20260222100000_multi_tenant_foundation.sql`
**Estimated files**: 7 new, 12 modified
**Dependencies**: Phase 0 deployed

### 1A — Supabase Work (backend-supabase-agent)

**File to create**: `supabase/migrations/20260222100000_multi_tenant_foundation.sql`

This migration handles everything after the catch-up:

#### New Tables
```sql
-- companies table
-- Length constraint (2-200 chars) prevents oversized names
CREATE TABLE companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE CHECK (length(name) BETWEEN 2 AND 200),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- user_profiles table (1:1 with auth.users)
-- CHECK constraints prevent a buggy RPC from writing arbitrary role/status values
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  company_id UUID REFERENCES companies(id) ON DELETE SET NULL,  -- SET NULL on company deletion (not RESTRICT)
  role TEXT NOT NULL DEFAULT 'inspector' CHECK (role IN ('admin','engineer','inspector','viewer')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected','deactivated')),
  display_name TEXT,
  cert_number TEXT,
  phone TEXT,
  position TEXT,
  last_synced_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- company_join_requests table
CREATE TABLE company_join_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  company_id UUID NOT NULL REFERENCES companies(id),
  status TEXT NOT NULL DEFAULT 'pending',  -- 'pending'|'approved'|'rejected'
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ,
  resolved_by UUID REFERENCES auth.users(id)
);

-- MED-6 fix: Prevent duplicate pending requests to the same company
CREATE UNIQUE INDEX idx_unique_pending_request
  ON company_join_requests (user_id, company_id) WHERE status = 'pending';
```

#### Auto-Profile Trigger
```sql
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO user_profiles (id) VALUES (NEW.id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();
```

#### Helper Function for RLS
```sql
CREATE OR REPLACE FUNCTION get_my_company_id()
RETURNS UUID AS $$
  SELECT company_id FROM user_profiles
  WHERE id = auth.uid() AND status = 'approved'
$$ LANGUAGE sql SECURITY DEFINER STABLE;
```

#### Helper Function: Viewer Check (CRIT-1 fix)
```sql
-- is_viewer() needed from Phase 1 so write policies can exclude viewers upfront
-- SEC-7 fix: Also check status = 'approved' for defense-in-depth
CREATE OR REPLACE FUNCTION is_viewer()
RETURNS BOOLEAN AS $$
  SELECT role = 'viewer' FROM user_profiles
  WHERE id = auth.uid() AND status = 'approved'
$$ LANGUAGE sql SECURITY DEFINER STABLE;
```

#### Company Search RPC (CRIT-3 fix)
```sql
-- SECURITY DEFINER RPC so unapproved users can search without seeing all company names
-- SEC-3 fix: Escape ILIKE wildcards and enforce minimum 3-char query length
-- Restrict search to users with company_id IS NULL (no-company users only) — prevents enumeration by existing members
-- Escape backslash character as well to prevent ILIKE injection
CREATE OR REPLACE FUNCTION search_companies(query TEXT)
RETURNS TABLE (id UUID, name TEXT) AS $$
DECLARE
  caller_company_id UUID;
BEGIN
  IF auth.uid() IS NULL THEN RAISE EXCEPTION 'Not authenticated'; END IF;
  IF length(query) < 3 THEN RETURN; END IF;
  SELECT company_id INTO caller_company_id FROM user_profiles WHERE id = auth.uid();
  -- Only users without a company can search (prevents enumeration by existing members)
  IF caller_company_id IS NOT NULL THEN RETURN; END IF;
  RETURN QUERY
    SELECT c.id, c.name FROM companies c
    WHERE c.name ILIKE '%' || replace(replace(replace(query, '\', '\\'), '%', '\%'), '_', '\_') || '%' ESCAPE '\'
    LIMIT 10;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
```

#### Admin Approval RPC (SEC-5 fix)
```sql
-- SECURITY DEFINER RPC — admins approve/reject join requests via this workflow only
-- Prevents admins from arbitrarily modifying user_profiles via direct API
CREATE OR REPLACE FUNCTION approve_join_request(
  request_id UUID,
  assigned_role TEXT DEFAULT 'inspector'
) RETURNS VOID AS $$
DECLARE
  v_company_id UUID;
  v_target_user_id UUID;
BEGIN
  -- Validate caller is admin of the request's company
  SELECT jr.company_id, jr.user_id INTO v_company_id, v_target_user_id
  FROM company_join_requests jr
  WHERE jr.id = request_id AND jr.status = 'pending';

  IF NOT FOUND THEN RAISE EXCEPTION 'Request not found or not pending'; END IF;
  IF v_company_id != get_my_company_id() THEN RAISE EXCEPTION 'Not your company'; END IF;
  IF (SELECT role FROM user_profiles WHERE id = auth.uid()) != 'admin'
    THEN RAISE EXCEPTION 'Not an admin'; END IF;
  IF assigned_role NOT IN ('inspector', 'engineer', 'viewer')
    THEN RAISE EXCEPTION 'Invalid role'; END IF;

  -- Atomically update both tables
  UPDATE company_join_requests
  SET status = 'approved', resolved_at = now(), resolved_by = auth.uid()
  WHERE id = request_id;

  UPDATE user_profiles
  SET company_id = v_company_id, role = assigned_role, status = 'approved', updated_at = now()
  WHERE id = v_target_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION reject_join_request(request_id UUID)
RETURNS VOID AS $$
DECLARE
  v_company_id UUID;
BEGIN
  SELECT company_id INTO v_company_id
  FROM company_join_requests WHERE id = request_id AND status = 'pending';

  IF NOT FOUND THEN RAISE EXCEPTION 'Request not found or not pending'; END IF;
  IF v_company_id != get_my_company_id() THEN RAISE EXCEPTION 'Not your company'; END IF;
  IF (SELECT role FROM user_profiles WHERE id = auth.uid()) != 'admin'
    THEN RAISE EXCEPTION 'Not an admin'; END IF;

  UPDATE company_join_requests
  SET status = 'rejected', resolved_at = now(), resolved_by = auth.uid()
  WHERE id = request_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

#### Company Creation RPC (SEC-NEW-1 fix)
```sql
-- SECURITY DEFINER RPC — only way to create a company
-- No INSERT policy on companies table needed
CREATE OR REPLACE FUNCTION create_company(company_name TEXT)
RETURNS companies
LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
  caller_profile user_profiles;
  new_company companies;
BEGIN
  IF auth.uid() IS NULL THEN RAISE EXCEPTION 'Not authenticated'; END IF;

  SELECT * INTO caller_profile FROM user_profiles WHERE id = auth.uid();
  IF caller_profile IS NULL THEN RAISE EXCEPTION 'No profile found'; END IF;
  IF caller_profile.company_id IS NOT NULL THEN RAISE EXCEPTION 'Already in a company'; END IF;
  -- Block rejected users as well (not just deactivated)
  IF caller_profile.status IN ('deactivated', 'rejected') THEN RAISE EXCEPTION 'Account deactivated or rejected'; END IF;

  INSERT INTO companies (name) VALUES (company_name) RETURNING * INTO new_company;

  UPDATE user_profiles
  SET company_id = new_company.id, role = 'admin', status = 'approved', updated_at = now()
  WHERE id = auth.uid();

  RETURN new_company;
END;
$$;
```

#### Admin Member Management RPCs (SEC-NEW-2 fix)
```sql
CREATE OR REPLACE FUNCTION update_member_role(target_user_id UUID, new_role TEXT)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
-- Validates: caller is admin of same company, new_role in (inspector, engineer, viewer)
-- Guard: can't demote last admin
$$;

CREATE OR REPLACE FUNCTION deactivate_member(target_user_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
-- Validates: caller is admin of same company
-- Sets status = 'deactivated'
-- Guard: can't deactivate last admin
-- SEC-NEW-4 fix: No admin.signOut() call — passive JWT expiry (≤1hr)
$$;

CREATE OR REPLACE FUNCTION reactivate_member(target_user_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
-- Validates: caller is admin of same company
-- Sets status = 'approved'
$$;

CREATE OR REPLACE FUNCTION promote_to_admin(target_user_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
-- Validates: caller is admin of same company
-- Target must be approved status
-- Sets role = 'admin'
$$;
```

#### REVOKE anon Access on All RPCs (SEC-NEW-3 fix)
```sql
-- SEC-NEW-3 fix: Lock all RPCs to authenticated role only
REVOKE EXECUTE ON FUNCTION search_companies FROM anon;
REVOKE EXECUTE ON FUNCTION approve_join_request FROM anon;
REVOKE EXECUTE ON FUNCTION reject_join_request FROM anon;
REVOKE EXECUTE ON FUNCTION create_company FROM anon;
REVOKE EXECUTE ON FUNCTION update_member_role FROM anon;
REVOKE EXECUTE ON FUNCTION deactivate_member FROM anon;
REVOKE EXECUTE ON FUNCTION reactivate_member FROM anon;
REVOKE EXECUTE ON FUNCTION promote_to_admin FROM anon;
```

**Last-admin guard (server-side)**: Enforce this in BOTH `deactivate_member` and `update_member_role` RPC bodies (not just client-side). Add to each RPC body:
```sql
IF (SELECT count(*) FROM user_profiles
    WHERE company_id = v_company_id AND role = 'admin' AND status = 'approved') <= 1
THEN RAISE EXCEPTION 'Cannot remove last admin'; END IF;
```

**`created_by_user_id` server enforcement**: `created_by_user_id` can be spoofed by the client on sync push. Add a `BEFORE INSERT` trigger to ALL 17 data tables to enforce server-side attribution:
```sql
CREATE OR REPLACE FUNCTION enforce_created_by()
RETURNS TRIGGER AS $$
BEGIN NEW.created_by_user_id = auth.uid(); RETURN NEW; END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
-- Apply to: projects, daily_entries, photos, bid_items, entry_quantities,
--           contractors, locations, equipment, entry_contractors, todo_items,
--           inspector_forms, form_responses, calculation_history,
--           personnel_types, entry_personnel_counts, entry_equipment, entry_personnel
```

#### RLS Policies — Replace All Permissive `anon` Policies
For each existing table, drop ALL `anon` policies (including those from catch-up migration on `personnel_types`, `entry_personnel_counts`, `entry_contractors`) and create company-scoped `authenticated` policies.

**CRITICAL (CRIT-13 fix)**: Drop `anon` policies on EVERY table, not just the 14 listed below. After deployment, verify with:
```sql
SELECT policyname, tablename FROM pg_policies WHERE roles @> '{anon}';
-- Must return 0 rows
```

**CRITICAL (CRIT-1 fix)**: Do NOT use `FOR ALL`. Create separate `FOR SELECT` / `FOR INSERT` / `FOR UPDATE` / `FOR DELETE` policies with `NOT is_viewer()` on write policies from the start. This eliminates the need for Phase 8 viewer RLS work.

**HIGH-8 note**: PRD says "edit own records only" — if enforced, `FOR UPDATE` policies should also include `created_by_user_id = auth.uid()`. Currently not enforced; all company members can edit each other's records. Add owner-only UPDATE policies if this becomes a requirement.

Pattern for `projects` (direct `company_id`):
```sql
-- Drop ALL old anon policies
DROP POLICY IF EXISTS "anon_select_projects" ON projects;
DROP POLICY IF EXISTS "anon_insert_projects" ON projects;
DROP POLICY IF EXISTS "anon_update_projects" ON projects;
DROP POLICY IF EXISTS "anon_delete_projects" ON projects;
DROP POLICY IF EXISTS "Authenticated users can manage projects" ON projects;

-- New company-scoped policies (separate per operation, viewer-aware)
CREATE POLICY "company_projects_select" ON projects
  FOR SELECT TO authenticated
  USING (company_id = get_my_company_id());

CREATE POLICY "company_projects_insert" ON projects
  FOR INSERT TO authenticated
  WITH CHECK (company_id = get_my_company_id() AND NOT is_viewer());

CREATE POLICY "company_projects_update" ON projects
  FOR UPDATE TO authenticated
  USING (company_id = get_my_company_id() AND NOT is_viewer());

CREATE POLICY "company_projects_delete" ON projects
  FOR DELETE TO authenticated
  USING (company_id = get_my_company_id() AND NOT is_viewer());
```

Pattern for one-hop tables (have `project_id`):
```sql
-- Example: daily_entries (has project_id → projects)
CREATE POLICY "company_daily_entries_select" ON daily_entries
  FOR SELECT TO authenticated
  USING (project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id()));

CREATE POLICY "company_daily_entries_insert" ON daily_entries
  FOR INSERT TO authenticated
  WITH CHECK (project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id()) AND NOT is_viewer());

CREATE POLICY "company_daily_entries_update" ON daily_entries
  FOR UPDATE TO authenticated
  USING (project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id()) AND NOT is_viewer());

CREATE POLICY "company_daily_entries_delete" ON daily_entries
  FOR DELETE TO authenticated
  USING (project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id()) AND NOT is_viewer());
```

Apply the one-hop pattern to: `daily_entries`, `photos`, `bid_items`, `entry_quantities`, `locations`, `contractors`, `equipment`, `entry_contractors`, `todo_items`, `inspector_forms`, `form_responses`, `calculation_history`.

**CRIT-14 fix**: Two-hop pattern for tables without `project_id` (have `entry_id` → `daily_entries` → `projects`):
```sql
-- Example: entry_personnel_counts (entry_id → daily_entries.id → projects.id)
CREATE POLICY "company_entry_personnel_counts_select" ON entry_personnel_counts
  FOR SELECT TO authenticated
  USING (entry_id IN (
    SELECT id FROM daily_entries WHERE project_id IN (
      SELECT id FROM projects WHERE company_id = get_my_company_id()
    )
  ));

CREATE POLICY "company_entry_personnel_counts_insert" ON entry_personnel_counts
  FOR INSERT TO authenticated
  WITH CHECK (entry_id IN (
    SELECT id FROM daily_entries WHERE project_id IN (
      SELECT id FROM projects WHERE company_id = get_my_company_id()
    )
  ) AND NOT is_viewer());

-- (same pattern for UPDATE/DELETE)
```

Apply the two-hop pattern to: `entry_personnel_counts`, `entry_equipment`.

**MED-1 note**: Two-hop nested subqueries may be slow on large datasets. If performance is an issue, consider adding `project_id` denormalization to junction tables or using materialized views. Monitor query times post-deployment.

**Defense-in-depth pull scoping**: `BaseRemoteDatasource.getAll()` does an unfiltered `select()`. Even with RLS, if a policy is misconfigured on any table, cross-tenant data leaks to local SQLite with no audit trail. Add explicit `.eq('company_id', companyId)` on all pull queries for direct-company tables as defense-in-depth. For child tables, add `.in_('project_id', companyProjectIds)`. This is specified in Phase 3 sync scoping but applies here as the RLS policy companion.

**`deleteAll()` production guard**: `BaseRemoteDatasource.deleteAll()` has no company scoping (uses `.neq('id', '00...')` which deletes everything). Ensure `deleteAll()` is never called in production paths. If used for test teardown only, restrict the method to debug builds with an assertion.

**`updated_at` client-settable risk**: `updated_at` is client-settable on INSERT — a malicious client can set a future `updated_at`, making their record always "win" sync conflict resolution. Consider adding a `BEFORE INSERT` trigger to set `updated_at = now()` server-side for all data tables.

**CRIT-9 fix**: Exclude `sync_queue` from RLS — it is local-only (SQLite). Drop the Supabase table entirely:
```sql
DROP TABLE IF EXISTS sync_queue;
```

Apply the one-hop pattern to: `daily_entries`, `photos`, `bid_items`, `entry_quantities`, `locations`, `contractors`, `equipment`, `entry_contractors`, `todo_items`, `inspector_forms`, `form_responses`, `calculation_history`, `personnel_types`.

New tables RLS:
```sql
-- companies: see own company only (locked down — search via RPC only, CRIT-3 fix)
CREATE POLICY "see_own_company" ON companies
  FOR SELECT TO authenticated USING (id = get_my_company_id());

-- user_profiles: see all company members + always see own row (CRIT-2 fix)
CREATE POLICY "read_own_profile" ON user_profiles
  FOR SELECT TO authenticated USING (id = auth.uid());
CREATE POLICY "see_company_members" ON user_profiles
  FOR SELECT TO authenticated USING (company_id = get_my_company_id());
-- SEC-1 fix: Lock role/status/company_id — users can only update personal fields
-- Also lock last_synced_at — user-writable last_synced_at lets users suppress admin stale-data warnings by setting a future date.
CREATE POLICY "update_own_profile" ON user_profiles
  FOR UPDATE TO authenticated
  USING (id = auth.uid())
  WITH CHECK (
    id = auth.uid()
    AND role = (SELECT role FROM user_profiles WHERE id = auth.uid())
    AND status = (SELECT status FROM user_profiles WHERE id = auth.uid())
    AND company_id IS NOT DISTINCT FROM (SELECT company_id FROM user_profiles WHERE id = auth.uid())
    AND last_synced_at IS NOT DISTINCT FROM (SELECT last_synced_at FROM user_profiles WHERE id = auth.uid())
  );
-- SEC-NEW-8 fix: No insert_own_profile policy. Profile creation is
-- handled exclusively by handle_new_user() trigger (single authoritative path).

-- join requests: users create their own, only admins see company requests (HIGH-6 fix)
-- Block deactivated/rejected users from spamming join requests (valid JWT up to 1hr)
CREATE POLICY "create_own_request" ON company_join_requests
  FOR INSERT TO authenticated WITH CHECK (
    user_id = auth.uid()
    AND (SELECT status FROM user_profiles WHERE id = auth.uid()) NOT IN ('deactivated', 'rejected')
  );
CREATE POLICY "view_own_request" ON company_join_requests
  FOR SELECT TO authenticated
  USING (
    user_id = auth.uid()
    OR (
      company_id = get_my_company_id()
      AND (SELECT role FROM user_profiles WHERE id = auth.uid()) = 'admin'
    )
  );
-- WITH CHECK locks user_id and company_id — prevents force-adding users
CREATE POLICY "admin_resolve_requests" ON company_join_requests
  FOR UPDATE TO authenticated
  USING (
    company_id = get_my_company_id()
    AND (SELECT role FROM user_profiles WHERE id = auth.uid()) = 'admin'
  )
  WITH CHECK (
    user_id = (SELECT user_id FROM company_join_requests WHERE id = company_join_requests.id)
    AND company_id = get_my_company_id()
  );

-- SEC-NEW-5 fix: Users can cancel their own pending requests
CREATE POLICY "cancel_own_pending_request" ON company_join_requests
  FOR DELETE TO authenticated
  USING (user_id = auth.uid() AND status = 'pending');
```

Enable RLS on new tables:
```sql
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_join_requests ENABLE ROW LEVEL SECURITY;
```

**`get_my_company_id()` NULL contract**: `get_my_company_id()` returning NULL is the only guard for unapproved users. This relies on NULL comparison semantics (`NULL = NULL` is FALSE). The contract is explicitly covered by `AND status = 'approved'` in the function body — document this and add an explicit status check where possible.

**Photos as immutable**: No UPDATE policy on `storage.objects` — photo replacement is silently blocked. This is intentional (photos are immutable once uploaded). If photo replacement is ever needed, add a `FOR UPDATE` policy matching the `company_photo_insert` pattern.

**Storage filename regex**: Tighten the storage filename regex in upload path validation from `[^/]+` (allows `..`, `%00`) to `[a-zA-Z0-9_.-]+\.(jpg|jpeg|png|heic)$`. Update `_validateStoragePath()` regex accordingly.

#### Supabase Storage Bucket RLS (SEC-2 fix, MED-10 fix)
```sql
-- CRITICAL: Restructure photo paths to: entries/{companyId}/{entryId}/{filename}
-- Without company prefix, any guessed entry UUID exposes photos cross-tenant.
-- Old path: entries/{entryId}/{filename} — NO company scoping, publicly accessible via getPublicUrl().
-- New path: entries/{companyId}/{entryId}/{filename} — company-scoped, RLS policies key on companyId folder.
-- Switch from getPublicUrl() to createSignedUrl() with 1-hour expiry in Dart code
CREATE POLICY "company_photo_select" ON storage.objects
  FOR SELECT TO authenticated
  USING (bucket_id = 'entry-photos'
    AND (storage.foldername(name))[1] = get_my_company_id()::text);

CREATE POLICY "company_photo_insert" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'entry-photos'
    AND (storage.foldername(name))[1] = get_my_company_id()::text
    AND NOT is_viewer());

CREATE POLICY "company_photo_delete" ON storage.objects
  FOR DELETE TO authenticated
  USING (bucket_id = 'entry-photos'
    AND (storage.foldername(name))[1] = get_my_company_id()::text
    AND NOT is_viewer());
```
**Dart changes** (Phase 3 or Phase 1B):
- `photo_remote_datasource.dart`: Change `getPublicUrl()` → `createSignedUrl(expiresIn: 3600)`
- Update upload path from `entries/{entryId}/{filename}` → `entries/{companyId}/{entryId}/{filename}`
- **SEC-NEW-7 fix**: Add path validation before upload in `photo_remote_datasource.dart`:
  ```dart
  void _validateStoragePath(String path) {
    final pattern = RegExp(r'^entries/[a-f0-9-]+/[a-f0-9-]+/[^/]+$');
    if (!pattern.hasMatch(path)) {
      throw ArgumentError('Invalid storage path: $path');
    }
  }
  ```
  Supabase Storage already rejects `..` traversal at API layer. This is defense-in-depth.

#### FK, Indexes, Constraints
```sql
-- FK from projects.company_id to companies.id
ALTER TABLE projects ADD CONSTRAINT fk_projects_company
  FOREIGN KEY (company_id) REFERENCES companies(id);

-- Indexes
CREATE INDEX idx_user_profiles_company ON user_profiles(company_id);
CREATE INDEX idx_user_profiles_status ON user_profiles(status);
CREATE INDEX idx_join_requests_user ON company_join_requests(user_id);
CREATE INDEX idx_join_requests_company ON company_join_requests(company_id);
CREATE INDEX idx_join_requests_status ON company_join_requests(status);

-- updated_at trigger for new tables
CREATE TRIGGER update_companies_updated_at
  BEFORE UPDATE ON companies
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_profiles_updated_at
  BEFORE UPDATE ON user_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Hardcoded company UUID**: The hardcoded predictable company UUID `00000000-...0001` is guessable and enables targeted phishing. For production, switch to `gen_random_uuid()`. The hardcoded UUID is acceptable for development/single-tenant bootstrap only — it must be replaced before onboarding a second company. Roberto's auth UUID is already in version control; accept that risk for the seed.

**Seed conflict strategy asymmetry**: The company seed uses `ON CONFLICT DO NOTHING` while the user profile upsert uses `ON CONFLICT DO UPDATE`. This is intentional (company name shouldn't be overwritten by migrations). Document this asymmetry to avoid confusion.

#### Seed + Backfill
```sql
-- Seed: create company "Fleis and Vandenbrink"
INSERT INTO companies (id, name)
VALUES ('00000000-0000-0000-0000-000000000001', 'Fleis and Vandenbrink')
ON CONFLICT DO NOTHING;

-- Seed: Roberto as admin (replace e21e828d-69e5-48bb-92fb-70847c340298 with real UUID)
-- CRIT-4 fix: Use upsert — trigger only fires for NEW auth.users, Roberto already exists
INSERT INTO user_profiles (id, company_id, role, status, display_name, created_at, updated_at)
VALUES (
  'e21e828d-69e5-48bb-92fb-70847c340298',
  '00000000-0000-0000-0000-000000000001',
  'admin',
  'approved',
  'Roberto Chavez',
  now(),
  now()
)
ON CONFLICT (id) DO UPDATE SET
  company_id = EXCLUDED.company_id,
  role = EXCLUDED.role,
  status = EXCLUDED.status,
  display_name = EXCLUDED.display_name,
  updated_at = now();

-- Backfill: all existing projects get company_id and created_by
UPDATE projects
SET company_id = '00000000-0000-0000-0000-000000000001',
    created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
WHERE company_id IS NULL;

-- Make company_id NOT NULL after backfill
ALTER TABLE projects ALTER COLUMN company_id SET NOT NULL;

-- Unique constraint: project number unique within company
CREATE UNIQUE INDEX idx_project_number_company ON projects(company_id, project_number);

-- CRIT-12 fix: Backfill ALL 14 data tables with created_by_user_id
UPDATE daily_entries SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
UPDATE photos SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
UPDATE bid_items SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
UPDATE entry_quantities SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
UPDATE contractors SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
UPDATE locations SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
UPDATE equipment SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
UPDATE entry_contractors SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
UPDATE todo_items SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
UPDATE inspector_forms SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
UPDATE form_responses SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
UPDATE calculation_history SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
UPDATE personnel_types SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
UPDATE entry_personnel_counts SET created_by_user_id = 'e21e828d-69e5-48bb-92fb-70847c340298'
  WHERE created_by_user_id IS NULL;
```

**NOTE**: Roberto's UUID (`e21e828d-69e5-48bb-92fb-70847c340298`) has been substituted for all placeholder references above.

### 1B — Dart Model Work (backend-data-layer-agent)

**Atomic 1B+1C deployment**: `toMap()` must NOT emit `created_by_user_id` or `company_id` before Phase 1C (SQLite v24) is deployed. Phase 1B and Phase 1C MUST be committed and deployed as a single atomic PR. The models in 1B and the schema in 1C must land in the same app release to prevent fresh-install crashes.

**`auth/data/` directory creation order**: The `auth/data/` directory does not yet exist. Creating it with 6+ barrel files is a new directory layer. In Phase 1B, create the directories first, then the files in dependency order: models → local datasources → remote datasources → repositories → barrels. Import errors will occur if barrel files are created before the files they export.

**`phone` and `cert_number` validation**: These fields have no format validation in the model or UI. Add client-side validation in `ProfileSetupScreen` and `EditProfileScreen` (Phase 2). Server-side, add CHECK constraints or leave as free-text and document the decision.

#### Files to Create

**`lib/features/auth/data/models/company.dart`**
- Fields: `id`, `name`, `createdAt`, `updatedAt`
- Methods: `copyWith()`, `toMap()`, `fromMap()`

**`lib/features/auth/data/models/user_profile.dart`**
- Enum: `UserRole { admin, engineer, inspector, viewer }`
- Enum: `UserStatus { pending, approved, rejected, deactivated }`
- Fields: `id`, `companyId`, `role` (UserRole), `status` (UserStatus), `displayName`, `certNumber`, `phone`, `position`, `lastSyncedAt`, `createdAt`, `updatedAt`
- Methods: `copyWith()`, `toMap()`, `fromMap()`
- Getters: `isAdmin`, `isApproved`, `canWrite` (not viewer)

**`lib/features/auth/data/models/company_join_request.dart`**
- Enum: `JoinRequestStatus { pending, approved, rejected }`
- Fields: `id`, `userId`, `companyId`, `status`, `requestedAt`, `resolvedAt`, `resolvedBy`
- Methods: `copyWith()`, `toMap()`, `fromMap()`

**`lib/features/auth/data/models/models.dart`** (barrel export)
- Exports: `company.dart`, `user_profile.dart`, `company_join_request.dart`

**CONT-4 fix**: Also create ALL barrel files for the new `auth/data/` directory:
- `lib/features/auth/data/data.dart`
- `lib/features/auth/data/datasources/datasources.dart`
- `lib/features/auth/data/datasources/local/local_datasources.dart`
- `lib/features/auth/data/datasources/remote/remote_datasources.dart`
- `lib/features/auth/data/repositories/repositories.dart`
- Update `lib/features/auth/auth.dart` to export `data/data.dart`

#### Files to Modify

**`lib/features/projects/data/models/project.dart`**
- Add fields: `companyId` (String?, nullable until migration confirmed), `createdByUserId` (String?)
- Update `copyWith()`, `toMap()`, `fromMap()` to include new fields
- `toMap()`: adds `'company_id': companyId`, `'created_by_user_id': createdByUserId`
- `fromMap()`: reads `map['company_id'] as String?`, `map['created_by_user_id'] as String?`

**`lib/features/entries/data/models/daily_entry.dart`**
- Add fields: `createdByUserId` (String?), `updatedByUserId` (String?)
- Update `copyWith()`, `toMap()`, `fromMap()`

**`lib/features/photos/data/models/photo.dart`**
- Add field: `createdByUserId` (String?)
- Update `copyWith()`, `toMap()`, `fromMap()`

**`lib/features/quantities/data/models/bid_item.dart`**
- Add field: `createdByUserId` (String?)
- Update `copyWith()`, `toMap()`, `fromMap()`

**`lib/features/quantities/data/models/entry_quantity.dart`**
- Add field: `createdByUserId` (String?)
- Update `copyWith()`, `toMap()`, `fromMap()`

**HIGH-3 fix**: The following 9 models also need `createdByUserId` (String?) added with `copyWith()`, `toMap()`, `fromMap()` updates:
- `lib/features/contractors/data/models/contractor.dart`
- `lib/features/locations/data/models/location.dart`
- `lib/features/contractors/data/models/equipment.dart`
- `lib/features/todos/data/models/todo_item.dart`
- `lib/features/forms/data/models/inspector_form.dart`
- `lib/features/forms/data/models/form_response.dart`
- `lib/features/calculator/data/models/calculation_history.dart`
- `lib/features/entries/data/models/entry_contractor.dart`
- `lib/features/contractors/data/models/personnel_type.dart`

### 1C — SQLite Schema Migration (backend-data-layer-agent)

#### Files to Modify

**`lib/core/database/database_service.dart`**
- Change `version: 23` → `version: 24` (appears twice: `_initDatabase()` and `_initInMemoryDatabase()`)
- Add `onUpgrade` block for v24:
```dart
if (oldVersion < 24) {
  // CRIT-5 fix: Use _addColumnIfNotExists() — safe for re-runs and partial migrations
  // CRIT-6 fix: Add created_by_user_id to ALL 14 tables, not just 8
  await _addColumnIfNotExists(db, 'projects', 'company_id', 'TEXT');
  await _addColumnIfNotExists(db, 'projects', 'created_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'daily_entries', 'created_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'daily_entries', 'updated_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'photos', 'created_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'bid_items', 'created_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'entry_quantities', 'created_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'contractors', 'created_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'locations', 'created_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'equipment', 'created_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'entry_contractors', 'created_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'todo_items', 'created_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'inspector_forms', 'created_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'form_responses', 'created_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'calculation_history', 'created_by_user_id', 'TEXT');
  // CONT-2 fix: These two tables were missing from the original plan
  await _addColumnIfNotExists(db, 'personnel_types', 'created_by_user_id', 'TEXT');
  await _addColumnIfNotExists(db, 'entry_personnel_counts', 'created_by_user_id', 'TEXT');
  // CONT-7 fix: entry_equipment is actively synced and needs the column
  await _addColumnIfNotExists(db, 'entry_equipment', 'created_by_user_id', 'TEXT');
  // CONT-NEW-4 fix: Include legacy entry_personnel for consistency (truly 17 tables)
  await _addColumnIfNotExists(db, 'entry_personnel', 'created_by_user_id', 'TEXT');
  // CONT-6 fix: Add updated_at to calculation_history for sync conflict resolution
  await _addColumnIfNotExists(db, 'calculation_history', 'updated_at', 'TEXT');

  // Create local cache tables for company and user profile
  await db.execute('''
    CREATE TABLE IF NOT EXISTS companies (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  ''');

  await db.execute('''
    CREATE TABLE IF NOT EXISTS user_profiles (
      id TEXT PRIMARY KEY,
      company_id TEXT,
      role TEXT NOT NULL DEFAULT 'inspector',
      status TEXT NOT NULL DEFAULT 'pending',
      display_name TEXT,
      cert_number TEXT,
      phone TEXT,
      position TEXT,
      last_synced_at TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  ''');

  await db.execute('''
    CREATE TABLE IF NOT EXISTS company_join_requests (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      company_id TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      requested_at TEXT NOT NULL,
      resolved_at TEXT,
      resolved_by TEXT
    )
  ''');

  // Indexes
  await db.execute('CREATE INDEX IF NOT EXISTS idx_projects_company ON projects(company_id)');
  await db.execute('CREATE INDEX IF NOT EXISTS idx_user_profiles_company ON user_profiles(company_id)');
}
```

**Partial migration failure guard**: A SQLite v24 migration partial failure (e.g., crash mid-`onUpgrade`) leaves a mixed state — some columns exist, others don't. Because `_addColumnIfNotExists()` is idempotent, re-running the upgrade is safe. However, the database version will not be incremented if the upgrade throws. Wrap the entire v24 upgrade block in a try/catch and re-throw so SQLite rolls back to v23 rather than leaving a partially-upgraded v24.

**CRIT-7 fix**: Update ALL `CREATE TABLE` definitions so fresh installs at v24 match upgraded installs exactly.

**`lib/core/database/schema/core_tables.dart`**
- Add `company_id TEXT` and `created_by_user_id TEXT` columns to `createProjectsTable`
- Add index `CREATE INDEX idx_projects_company ON projects(company_id)` to `indexes` list
- Add new table creation strings for `companies`, `user_profiles`, `company_join_requests`
- These new strings are used by `_onCreate` only (fresh installs get v24 from the start)

**`lib/core/database/schema/entry_tables.dart`**
- Add `created_by_user_id TEXT` and `updated_by_user_id TEXT` to `createDailyEntriesTable`
- Add `created_by_user_id TEXT` to `entry_contractors` table
- Add `created_by_user_id TEXT` to `entry_equipment` table (if defined here)

**`lib/core/database/schema/photo_tables.dart`**
- Add `created_by_user_id TEXT` to photos table

**`lib/core/database/schema/quantity_tables.dart`**
- Add `created_by_user_id TEXT` to `bid_items` and `entry_quantities` tables

**`lib/core/database/schema/contractor_tables.dart`**
- Add `created_by_user_id TEXT` to `contractors` and `equipment` tables

**CONT-5 fix**: Correct file paths for remaining schema tables:

**`lib/core/database/schema/toolbox_tables.dart`**
- **CONT-6 fix (IMPORTANT)**: Add `updated_at TEXT NOT NULL` to `calculation_history` CREATE TABLE definition — required for sync conflict resolution. This column is missing from the current fresh-install schema. Without it, fresh installs will have a schema mismatch with upgraded installs.
- Add `created_by_user_id TEXT` to `todo_items`, `inspector_forms`, `form_responses`, `calculation_history` CREATE TABLE definitions

**`lib/core/database/schema/personnel_tables.dart`**
- Add `created_by_user_id TEXT` to `personnel_types` and `entry_personnel_counts` CREATE TABLE definitions

**`lib/core/database/schema/entry_tables.dart`** (if `entry_equipment` is defined here)
- Add `created_by_user_id TEXT` to `entry_equipment` CREATE TABLE definition (CONT-7 fix)

**Verify**: ALL 17 data tables have `created_by_user_id TEXT` in their CREATE TABLE statement (16 active + legacy `entry_personnel`)

#### Files to Create (local data layer)

**`lib/features/auth/data/datasources/local/company_local_datasource.dart`**
- `getById(String id)`, `getAll()`, `insert(Company)`, `update(Company)`, `delete(String id)`, `upsert(Company)`

**`lib/features/auth/data/datasources/local/user_profile_local_datasource.dart`**
- `getById(String id)`, `getAll()`, `getByCompanyId(String companyId)`, `insert(UserProfile)`, `update(UserProfile)`, `upsert(UserProfile)`

**`lib/features/auth/data/datasources/local/local_datasources.dart`** (barrel)
- Exports: `company_local_datasource.dart`, `user_profile_local_datasource.dart`

**`lib/features/auth/data/repositories/company_repository.dart`**
- `getById(String id)`, `save(Company)`, `getMyCompany()`, `getAll()`

**`lib/features/auth/data/repositories/user_profile_repository.dart`**
- `getById(String id)`, `getByCompanyId(String companyId)`, `save(UserProfile)`, `getAll()`, `getMyProfile(String userId)`

### Phase 1 Acceptance Criteria
- [ ] `flutter analyze` — zero errors
- [ ] `flutter test` — all pass
- [ ] All Dart models compile with new fields (nullable — backwards-compatible)
- [ ] SQLite migrates cleanly from v23 → v24: create a db at v23, open at v24, no crash
- [ ] Fresh install at v24: `companies`, `user_profiles`, `company_join_requests` tables exist
- [ ] Supabase `db push` runs without errors
- [ ] Supabase tables exist: `companies`, `user_profiles`, `company_join_requests`
- [ ] RLS blocks: User A (company 1) cannot SELECT User B's (company 2) projects
- [ ] **MED-3 fix**: Concrete RLS test: create 2 companies, 2 users, verify cross-company SELECT/INSERT/UPDATE/DELETE blocked. Run `SELECT policyname, tablename FROM pg_policies WHERE roles @> '{anon}'` and confirm 0 rows.
- [ ] Existing data backfilled: all `projects` have `company_id` and `created_by_user_id`

---

## Phase 2: Auth & User Profile

**Agent**: `auth-agent` + `frontend-flutter-specialist-agent`
**Estimated files**: 12 new, 8 modified
**Dependencies**: Phase 1 complete

**`AuthProvider` chicken-and-egg**: The router refactor (static → instance) creates a bootstrap ordering issue: `AuthProvider` is needed by the router, but `AuthProvider` is created inside `MultiProvider` which builds after the router. Fix: hoist `AuthProvider` creation before `MultiProvider` in `_runApp()`. Create `final authProvider = AuthProvider(authService)` before `MaterialApp.router`, then include `ChangeNotifierProvider.value(value: authProvider)` inside `MultiProvider`.

**Redirect function early guards**: The 5-state redirect logic must preserve existing early returns for `TestModeConfig.useMockAuth` and `!SupabaseConfig.isConfigured`. The redirect function must check these flags FIRST, before any profile/company state checks. Add an explicit guard at the top of the redirect function: `if (!SupabaseConfig.isConfigured || TestModeConfig.useMockAuth) return null;`

**Company change data clearing**: "Clear local data on company change" (HIGH-4 fix in auth_service.dart) must only execute AFTER confirming sync is complete. Add: (1) check `SyncOrchestrator.hasPendingOperations()` before clearing, (2) if pending operations exist, show a confirmation dialog warning about potential data loss, (3) require explicit user confirmation before clearing. Never auto-clear silently.

**Password complexity (Supabase dashboard)**: Password minimum is 6 characters with no complexity requirement. For construction inspection data, recommend min 8 with mixed case + digits in the Supabase Auth settings (`minimum_password_length: 8`). This is a Supabase dashboard configuration change, not a code change.

**Email confirmation (Supabase dashboard)**: Email confirmation is disabled — users can sign up with any email. Since admins approve users by email identity, a user could sign up with someone else's email. Enable `mailer_autoconfirm: false` in Supabase Auth settings. This is a Supabase dashboard configuration change.

### 2A — Auth Service & Provider Updates (auth-agent)

#### Files to Modify

**`lib/features/auth/services/auth_service.dart`**
- Add dependency: `SupabaseClient _client`
- Add method `loadUserProfile(String userId) → Future<UserProfile?>`
  - Queries Supabase `user_profiles` table, maps to `UserProfile`
- Add method `updateUserProfile(UserProfile profile) → Future<void>`
  - Upserts to Supabase `user_profiles`
- **HIGH-4 fix**: On company change (leave → join new), clear local SQLite data from the old company before pulling new company data. Or scope all local queries by `company_id` so old data is invisible.
- Add method `createCompany(String name) → Future<Company>`
  - **SEC-NEW-1 fix**: Calls `create_company` SECURITY DEFINER RPC (not direct inserts)
  - `final result = await supabase.rpc('create_company', params: {'company_name': name})`
  - Returns `Company.fromMap(result)`
- Add method `joinCompany(String companyId) → Future<CompanyJoinRequest>`
  - Inserts into `company_join_requests`
- Add method `cancelJoinRequest(String requestId) → Future<void>`
- Add method `searchCompanies(String query) → Future<List<Company>>`
  - **CRIT-3 fix**: Call `search_companies` SECURITY DEFINER RPC instead of direct SELECT. Users never see all company names — only search results for their query.
  - `await supabase.rpc('search_companies', params: {'query': query})`
- Add method `pollJoinRequestStatus(String requestId) → Future<JoinRequestStatus>`
  - SELECT status FROM `company_join_requests` WHERE id = requestId

**`lib/features/auth/presentation/providers/auth_provider.dart`**
- Add private field: `UserProfile? _userProfile`
- Add private field: `Company? _company`
- Add public getters: `userProfile`, `company`, `isAdmin`, `isApproved`, `userRole`, `canWrite`
- Add method `loadUserProfile()` — called after successful sign-in
- Update `signIn()` — after success, call `loadUserProfile()`
- Update `signUp()` — after success, call `loadUserProfile()` (may return null for new user)
- Add method `updateProfile(UserProfile profile)` — calls AuthService, updates `_userProfile`, notifyListeners
- Add method `createCompany(String name)` — delegates to AuthService
- Add method `joinCompany(String companyId)` — delegates to AuthService
- Add method `refreshUserProfile()` — re-fetch from Supabase (for pending approval polling)

#### Files to Create

**`lib/features/auth/data/datasources/remote/user_profile_remote_datasource.dart`**
- `getById(String userId) → Future<UserProfile?>`
- `upsert(UserProfile profile) → Future<void>`
- `getByCompanyId(String companyId) → Future<List<UserProfile>>`

**`lib/features/auth/data/datasources/remote/company_remote_datasource.dart`**
- `create(Company company) → Future<Company>`
- `getById(String id) → Future<Company?>`
- `search(String query) → Future<List<Company>>`

**`lib/features/auth/data/datasources/remote/join_request_remote_datasource.dart`**
- `create(CompanyJoinRequest request) → Future<CompanyJoinRequest>`
- `getById(String id) → Future<CompanyJoinRequest?>`
- `cancel(String id) → Future<void>`
- `getByUser(String userId) → Future<List<CompanyJoinRequest>>`

**`lib/features/auth/data/datasources/remote/remote_datasources.dart`** (barrel)
- Exports remote datasource files

**`lib/features/auth/data/datasources/datasources.dart`** (barrel)
- Exports local and remote datasource barrels

### 2B — Onboarding Screens (frontend-flutter-specialist-agent)

#### Files to Create

**`lib/features/auth/presentation/screens/profile_setup_screen.dart`**
- StatefulWidget
- Fields: display_name (required hint), cert_number (optional), phone (optional), position (optional)
- "Skip for now" button → proceeds to company setup without saving profile data
- "Continue" button → saves profile to Supabase, proceeds to company setup
- Company step embedded OR separate screen (see below)
- Reads from `AuthProvider.userProfile` to pre-fill if returning to screen

**`lib/features/auth/presentation/screens/company_setup_screen.dart`**
- Two tabs or cards: "Create New Company" / "Join Existing Company"
- Create flow: TextField for company name → uniqueness check → create → navigate to app
- Join flow: search TextField with debounced autocomplete from `AuthService.searchCompanies()` → select → submit request → navigate to pending screen

**`lib/features/auth/presentation/screens/pending_approval_screen.dart`**
- Displays company name from join request
- "Cancel Request" button
- Polls `AuthProvider.refreshUserProfile()` every 10s (**MED-5 note**: Consider Supabase Realtime as enhancement, or reduce to 30s with exponential backoff to save battery if user leaves screen open)
- Use exponential backoff for polling: start at 5s, double each miss up to 60s max — 10s polling with 100 pending users creates 600 RLS-subquery evaluations/min (DoS vector). Supabase Realtime subscription is an alternative.
- Store the timer in a nullable `Timer? _pollTimer` field. In `dispose()`, call `_pollTimer?.cancel()`. Add a `mounted` check inside the timer callback before calling `setState()` or navigating to prevent race conditions.
- On approved status → navigate to app (`context.go('/')`)
- Uses `Timer.periodic` in `initState`, cancelled in `dispose`

**`lib/features/auth/presentation/screens/account_status_screen.dart`**
- Handles `rejected` and `deactivated` status
- Rejected: "Your request was declined" + "Try a different company" button (→ company_setup)
- Deactivated: "Your account has been deactivated. Contact your administrator."
- Sign out button

#### Files to Modify

**`lib/features/auth/presentation/screens/screens.dart`**
- Add exports: `profile_setup_screen.dart`, `company_setup_screen.dart`, `pending_approval_screen.dart`, `account_status_screen.dart`

### 2C — Settings: Edit Profile (frontend-flutter-specialist-agent)

#### Files to Create

**`lib/features/settings/presentation/screens/edit_profile_screen.dart`**
- Reads from `AuthProvider.userProfile`
- Fields: display_name, cert_number, phone, position
- Save → calls `AuthProvider.updateProfile()`
- Back button (no auto-save)

#### Files to Modify

**`lib/features/settings/presentation/screens/settings_screen.dart`**
- Replace "Inspector Profile" section with "Profile" section
- Remove: `InspectorProfileSection` widget and all the `_saveInspector*` / `_showEdit*` dialog methods
- Remove: `_inspectorName`, `_inspectorInitials`, `_inspectorPhone`, `_inspectorCertNumber`, `_inspectorAgency` state variables
- Remove: `_loadSettings()` calls to PreferencesService for inspector fields
- Add: `Consumer<AuthProvider>` showing display_name, role, company name
- Add: "Edit Profile" `ListTile` → navigates to `/edit-profile`
- Keep: Appearance, Auto-Fill, Project, Account, Sync, PDF Export, Weather, Data, About sections unchanged

**`lib/features/settings/presentation/screens/screens.dart`**
- Add export: `edit_profile_screen.dart`

### 2D — Router Updates (auth-agent)

#### Files to Modify

**`lib/core/router/app_router.dart`**
- Add new routes (outside shell, no bottom nav):
  - `/profile-setup` → `ProfileSetupScreen`
  - `/company-setup` → `CompanySetupScreen`
  - `/pending-approval` → `PendingApprovalScreen`
  - `/account-status` → `AccountStatusScreen`
  - `/edit-profile` → `EditProfileScreen`
- Update `redirect` logic:
  ```dart
  // After auth check, add profile/company state checks:
  // 1. isAuthenticated but no userProfile row → /profile-setup
  // 2. profile exists but status == 'pending' → /pending-approval
  // 3. profile exists but status == 'rejected' → /account-status
  // 4. profile exists but status == 'deactivated' → /account-status
  // 5. status == 'approved' → null (allow through)
  ```
- **CONT-18 fix**: NONE of the new routes should be added to `_isRestorableRoute` (`/profile-setup`, `/company-setup`, `/pending-approval`, `/account-status`, `/edit-profile`, `/admin-dashboard`)
- **MED-8 fix**: Ensure router redirect runs after deep link processing. Auth deep link callback (`recoverSession()`) should NOT navigate directly — let the redirect function handle routing based on profile state. This prevents deep links from interrupting onboarding.
- **CONT-17 fix**: Add `isOnboardingRoute` set to the redirect function. Current `isAuthRoute` checks `/login`, `/register`, `/forgot-password`. New onboarding routes (`/profile-setup`, `/company-setup`, `/pending-approval`, `/account-status`) must be exempted from the "if authenticated and isAuthRoute, redirect to /" check. The full revised redirect function should:
  1. Check authentication (existing)
  2. If authenticated but on auth route → redirect to `/` (existing)
  3. If authenticated, run 5-state profile check (new — before allowing through)
  4. If on an onboarding route matching current state → allow through
  5. If state mismatch → redirect to correct onboarding route
- **CONT-19 fix**: Update `ProjectRepository.create()` to use `getByProjectNumberInCompany()` instead of `getByProjectNumber()` — uniqueness is per-company, not global

**CRIT-11 fix**: Refactor router from static singleton to instance that receives `AuthProvider`.
  - Pass `AuthProvider` into `AppRouter` constructor
  - Use `GoRouter`'s `refreshListenable` parameter with `AuthProvider` so redirects re-evaluate on auth state changes
  - Router redirect reads `authProvider.userProfile?.status` for the 5-state redirect logic
  - Update `main.dart` to create `AppRouter(authProvider: authProvider)` after `AuthProvider` is initialized

**`/admin-dashboard` router guard**: The `/admin-dashboard` route has no server-side guard — non-admins can deep-link directly. Add a router redirect: if `authProvider.userRole != UserRole.admin`, redirect to `/`. This prevents the UI from rendering company member data before any RPC fails. Also add `/admin-dashboard` to the `_isNonRestorableRoute` set (alongside the new onboarding routes) so the app never tries to restore a session directly to the admin dashboard.

**Accepted risk — password re-auth**: `secure_password_change` is false — no re-auth required to change password. For a field app, this is an acceptable UX trade-off.

**Low priority — join request spam limit**: No global limit on pending join requests per user — a user can join-request many companies. Consider adding a check in the `create_own_request` policy or a trigger: if user already has 3+ pending requests, reject new ones. Low priority for single-company deployment.

**Future enhancement — admin audit log**: No audit log for admin actions (deactivate, role change, etc.). Consider adding an `admin_audit_log` table (action, admin_id, target_user_id, timestamp) as a future enhancement. Log inserts from within each SECURITY DEFINER RPC.

### 2E — PreferencesService Migration (auth-agent)

**CRITICAL — Direct SharedPreferences callers**: `pdf_data_builder.dart:120-122` and `entry_photos_section.dart:87-88` read inspector fields DIRECTLY from `SharedPreferences` (bypassing PreferencesService). Phase 2E clears these keys after migration. These callers will get null AFTER keys are cleared — PDFs will show "Inspector" and photos will show "XX". Refactor ALL direct SharedPreferences callers to read from `AuthProvider.userProfile` BEFORE clearing any PreferencesService keys. Do this as a prerequisite step in Phase 2E before the key-clearing logic.

**Audit all PreferencesService callers**: Auto-fill and PDF features still read from `PreferencesService` at the time Phase 2E runs. Before clearing old keys, audit all callers: search for `PreferencesService.getInspector*` and `SharedPreferences.getString('inspector_*')` across the codebase. Each must be migrated to read from `AuthProvider.userProfile` before Phase 2E's key-clearing executes.

#### Files to Modify

**`lib/features/auth/presentation/providers/auth_provider.dart`**
- In `loadUserProfile()`: if profile exists but `certNumber` or `phone` is null, check `PreferencesService` for legacy values
- If found in PreferencesService: call `updateProfile()` with merged data, then clear the old keys from PreferencesService
- **MED-4 fix**: After migrating, clear the pref keys. Use cleared keys as the "already migrated" signal — prevents re-running migration logic on every login.
- This one-time migration runs on first login after the update

**`lib/main.dart`**
- No changes needed for migration (handled inside AuthProvider)
- Add `UserProfileLocalDatasource` and `CompanyLocalDatasource` initialization
- Add `CompanyRepository` and `UserProfileRepository` initialization
- Register new datasources in provider list if needed
- **MED-2 note**: `main.dart` constructor is growing from ~20 to ~30 parameters across phases. Consider service locator (GetIt) or module-based provider registration to manage complexity.

### Phase 2 Acceptance Criteria
- [ ] `flutter analyze` — zero errors
- [ ] `flutter test` — all pass
- [ ] New user signup → email + password → profile setup → create company → lands at `/` as admin
- [ ] Second user signup → join company → pending screen → admin approves → pending screen auto-navigates to app
- [ ] Rejected user → account_status screen, can retry with different company
- [ ] Deactivated user → account_status screen, cannot proceed
- [ ] Settings screen: "Edit Profile" opens edit_profile_screen with pre-filled values
- [ ] Edit Profile saves to Supabase and AuthProvider updates
- [ ] Old PreferencesService cert/phone values migrated to user_profile on first login
- [ ] Router redirect gates: no unapproved user can reach the main app shell
- [ ] **HIGH-9 fix**: Mock auth mode returns stub `UserProfile` with configurable role/status so onboarding flow is testable in E2E

---

## Phase 3: Sync Scoping + Debounced Sync

**Agent**: `backend-data-layer-agent` + `backend-supabase-agent`
**Estimated files**: 4 new, 14 modified
**Dependencies**: Phase 2 complete (AuthProvider exposes `userProfile` with `companyId`)

### 3A — Sync Adapter: Company Scoping (backend-supabase-agent)

#### Files to Modify

**`lib/features/sync/data/adapters/supabase_sync_adapter.dart`**
- The adapter currently wraps `legacy.SyncService`. The legacy service needs the company_id for scoped queries.
- Add `_companyId` property read from `AuthProvider` or passed in constructor
- Override all push/pull calls to include company filter
- **HIGH-11 fix**: Add client-side `.eq('company_id', companyId)` as defense-in-depth on pull queries for direct-company tables (projects). RLS enforces server-side, but client-side filtering adds safety if RLS is misconfigured.

**`lib/services/sync_service.dart`** (the legacy service this adapter wraps)
- Add `companyId` parameter to `syncAll()` and `syncProject()`
- Update all `supabase.from('projects').select()` calls → `.eq('company_id', companyId)`
- Update all write calls to include `'created_by_user_id': currentUserId`
- **MED-7 fix**: Use `updated_at > lastSyncTimestamp` for incremental pulls instead of pulling ALL records every time. Already supported by `BaseRemoteDatasource.getUpdatedAfter()`.
- **CRIT-8 fix + CONT-13 fix**: Remove ALL 14 `if (remote*.isEmpty) { push all local }` heuristic blocks in `_pushBaseData()` (method spans lines 485-676, pattern repeats for every table). Replace with proper incremental sync using `updated_at` comparison. New users start with empty local AND remote — no push-all trigger needed.
- **CONT-8 fix + LOW-1 fix**: Remove `entry_personnel` from sync entirely — delete the push block in `_pushBaseData()` and the `_pullEntryPersonnel()` method. It's a legacy dead table.
- **LOW-2 fix**: Add JSONB→String conversion in `_convertForLocal` for `form_responses.header_data` and `form_responses.response_metadata`. Supabase returns `Map` (JSONB), SQLite expects `String` (TEXT). Use `jsonEncode()` on pull, `jsonDecode()` on push.
- Write pattern:
  ```dart
  await supabase.from('daily_entries').upsert({
    ...entry.toMap(),
    'created_by_user_id': currentUserId,
  });
  ```
- Pull pattern:
  ```dart
  // projects (direct company_id filter)
  final projects = await supabase
    .from('projects')
    .select()
    .eq('company_id', companyId);

  // child tables (join filter via project_id)
  final entries = await supabase
    .from('daily_entries')
    .select()
    .in_('project_id', projectIds);
  ```

**`lib/features/sync/application/sync_orchestrator.dart`**
- Accept `AuthProvider` or `UserProfile` reference to get `companyId` and `userId`
- Pass these to `SupabaseSyncAdapter` when invoking sync

### 3B — Sync on App Close (backend-data-layer-agent)

#### Files to Create

**`lib/features/sync/application/sync_lifecycle_manager.dart`**
- **HIGH-2 fix**: Use lazy initialization — register observer after providers are ready, or inject a `ValueNotifier<String?>` for companyId to avoid circular dependency with `AuthProvider`
- `SyncLifecycleManager` class implementing `WidgetsBindingObserver`
- `didChangeAppLifecycleState(AppLifecycleState state)`:
  - On `paused` or `detached` → trigger debounced sync push
- Debounce: maintain a `Timer? _debounceTimer`, cancel and restart on each call, fire after 30s of no new calls (or immediately on detached)
- Holds reference to `SyncOrchestrator`
- Registered in `main.dart` via `WidgetsBinding.instance.addObserver(syncLifecycleManager)`

#### Files to Modify

**`lib/main.dart`**
- Create `SyncLifecycleManager` instance after `SyncOrchestrator`
- Register as `WidgetsBindingObserver`
- Pass `authService`/`authProvider` or `userProfile` to lifecycle manager so it can call company-scoped sync

### 3C — Sync on App Open (Stale Check) (backend-data-layer-agent)

#### Files to Modify

**`lib/features/sync/application/sync_lifecycle_manager.dart`**
- In `didChangeAppLifecycleState()` on `resumed`:
  - Check `lastSyncTime` from `SyncOrchestrator.lastSyncTime`
  - If `> 24h` AND online → trigger full forced sync (non-dismissible UI)
  - If `> 24h` AND offline → emit event for stale-data banner

**`lib/features/sync/presentation/providers/sync_provider.dart`**
- **CRIT-10 fix + CONT-9 fix**: Migrate `SyncProvider` to use `SyncOrchestrator` instead of `SyncService` directly. Concrete changes:
  - Constructor: change `SyncProvider(legacy.SyncService syncService)` → `SyncProvider(SyncOrchestrator syncOrchestrator)`
  - `_setupListeners()`: rewire from `_syncService.onStatusChanged` to `SyncOrchestrator` status stream
  - `sync()`: change from `_syncService.syncAll()` → `_syncOrchestrator.syncLocalAgencyProjects()`
  - `main.dart:543`: change `SyncProvider(syncService)` → `SyncProvider(syncOrchestrator)`
- Add `bool isStaleDataWarning` getter
- Add `bool isForcedSyncInProgress` getter
- Add method `markSyncComplete()` — updates `lastSyncAt` in user_profiles

**CONT-16 fix**: Three other providers also take `syncService` directly and must be updated:
- `InspectorFormProvider` (`main.dart:549`) — change `syncService: syncService` → route through `SyncOrchestrator`
- `CalculatorProvider` (`main.dart:554`) — same change
- `TodoProvider` (`main.dart:563`) — same change
- All three call `syncService.queueOperation()` — this must go through a company-scoped interface

The replacement API for `syncService.queueOperation()` must be explicitly defined before implementing this change. `SyncOrchestrator` has no `queueOperation()` method. Specify the new method signature in `SyncOrchestrator`: `void queueOperation(SyncOperation op, {required String companyId})` — or define a `SyncQueue` delegate pattern. Without specifying this, forms/todos/calculations will silently stop syncing.

`SyncProvider` proxies `_syncService.isOnline` but `SyncOrchestrator` exposes `isSupabaseOnline`. Rename or alias: `bool get isOnline => _syncOrchestrator.isSupabaseOnline;` in the updated `SyncProvider`.

After the CONT-16 fix, verify that `InspectorFormProvider`, `CalculatorProvider`, and `TodoProvider` route ALL write operations through company-scoped sync — not directly to the legacy service. These three providers bypass `SyncOrchestrator` with unscoped `queueOperation()` and must be audited.

`SyncLifecycleManager` is registered in `main.dart` but the user may not be logged in when the observer fires. On `paused`/`detached` callbacks, guard with `AuthProvider.isAuthenticated` and `AuthProvider.companyId != null` before invoking sync. A null `companyId` on sync triggers will crash.

Removing the "push-all-if-empty" heuristic (CRIT-8/CONT-13) deletes the only initial-sync path for migrating users. Replace with: `if (SyncOrchestrator.lastSyncTime == null) { await syncAll(fullSync: true); }` — this triggers a full push for users who have never synced, without using the "remote empty" heuristic which is the cross-company attack vector.

App close (30s debounce), app open (>24h stale), and background sync can overlap — non-atomic check-then-act at `sync_service.dart:302`. Add an async lock using `Completer` or the `synchronized` package: `if (_syncInProgress) return; _syncInProgress = true; try { ... } finally { _syncInProgress = false; }`

### 3D — Remote Datasource Updates: Add company_id + created_by (backend-data-layer-agent)

**HIGH-7 fix**: ALL remote datasources need company scoping, not just 7. Every table that syncs to Supabase must include `created_by_user_id` on writes and company-scoped filtering on reads.

#### Files to Modify

**`lib/features/projects/data/datasources/remote/project_remote_datasource.dart`**
- `getAll()` → add `.eq('company_id', companyId)` filter
- `insert(Project)` → include `'company_id': companyId`, `'created_by_user_id': userId`

**`lib/features/entries/data/datasources/remote/daily_entry_remote_datasource.dart`**
- `getAll()` / `getByProject()` → filter by project_ids within company
- `insert()` / `update()` → include `'created_by_user_id': userId`, `'updated_by_user_id': userId`

**`lib/features/photos/data/datasources/remote/photo_remote_datasource.dart`**
- `getAll()` → filter by project scope
- `insert()` → include `'created_by_user_id': userId`

**`lib/features/quantities/data/datasources/remote/bid_item_remote_datasource.dart`**
- `getAll()` → filter by company's projects
- `insert()` → include `'created_by_user_id': userId`

**`lib/features/quantities/data/datasources/remote/entry_quantity_remote_datasource.dart`**
- `getAll()` → filter by company's projects
- `insert()` → include `'created_by_user_id': userId`

**`lib/features/contractors/data/datasources/remote/contractor_remote_datasource.dart`**
- `getAll()` → filter by company's projects
- `insert()` → include `'created_by_user_id': userId`

**`lib/features/locations/data/datasources/remote/location_remote_datasource.dart`**
- `getAll()` → filter by company's projects
- `insert()` → include `'created_by_user_id': userId`

**CONT-NEW-1 fix**: The following tables are NOT currently synced in `sync_service.dart`. They must be added as **new explicit sync targets** in Phase 3, matching the flat push/pull block pattern used by the existing 14 tables (now 16 after adding these):

New sync targets to add to `_pushBaseData()`:
- `entry_contractors` — push block after `entry_equipment`
- `entry_personnel_counts` — push block after `entry_personnel` (legacy, being removed)

New sync targets to add to `_pullRemoteChanges()`:
- Pull `entry_contractors`
- Pull `entry_personnel_counts`

Remote datasources needed (or inline sync logic):
- `entry_contractor_remote_datasource.dart` (or add to existing entry datasource)
- `entry_personnel_count_remote_datasource.dart` (or add to existing personnel datasource)

`entry_contractors` and `entry_personnel_counts` have no `updated_at` column in local or remote schema. Without `updated_at`, sync conflict resolution always falls to "remote wins." Add `updated_at TIMESTAMPTZ DEFAULT now()` to both tables in the catch-up migration AND add `updated_at TEXT` to the local SQLite schema (Phase 1C).

No remote datasources currently exist for `entry_contractors` or `entry_personnel_counts`. CONT-NEW-1 above adds them. Ensure the new datasource files follow the `BaseRemoteDatasource` pattern and are registered in the appropriate barrel exports. Note that `entry_contractors` was created in the catch-up migration but has no push/pull in `SyncService` — local data never reaches Supabase until the CONT-NEW-1 fix is applied. Verify it is not missed.

JSONB conversion must explicitly list ALL affected fields: `response_data`, `header_data`, `response_metadata`, and `table_rows` in `form_responses`. Add a comment in `_convertForLocal()` listing each field by name. Apply `jsonEncode()` on pull and `jsonDecode()` on push for each. Developers must not miss fields or apply the conversion backwards. Additionally, add a size guard for oversized values: if `jsonEncode(value).length > 1_000_000`, log a warning and truncate or skip the field.

Remaining tables using inline sync (no dedicated remote datasource — company scoping via RLS only):
- `inspector_forms`, `form_responses`, `todo_items`, `calculation_history` — one-hop RLS via project_id
- `entry_equipment` — two-hop RLS via entry → daily_entries → projects

Tables with existing dedicated remote datasources (update these files):
- **`lib/features/contractors/data/datasources/remote/personnel_type_remote_datasource.dart`** (CONT-15 fix: correct path) — filter by project_id scope

`loadProjectsByCompany(companyId)` is called at app startup but `companyId` comes from `AuthProvider.userProfile` which may not be loaded yet (async). Add a loading guard: listen to `AuthProvider` changes, and only call `loadProjectsByCompany` after `userProfile != null`. Alternatively, fall back to `loadProjects()` (unfiltered local query) until the profile loads, then re-filter.

`loadProjectsByCompany(companyId)` queries `WHERE company_id = ?` in local SQLite, but the `company_id` column does not exist until the Phase 1C migration runs. Phase 5's `ProjectProvider` changes have a cross-phase dependency on Phase 1C. Verify Phase 1C migration has run before Phase 5 code is active. Add a schema version check or guard in `getByCompanyId()`.

### 3E — User Profiles Sync (backend-data-layer-agent)

#### Files to Create

**`lib/features/auth/data/datasources/remote/user_profile_sync_datasource.dart`**
- `pullCompanyMembers(String companyId) → Future<List<UserProfile>>`
  - Fetches all `user_profiles` WHERE `company_id = companyId` AND `status = 'approved'`
- Cache result to local SQLite `user_profiles` table via `UserProfileLocalDatasource`

#### Files to Modify

**`lib/features/sync/application/sync_orchestrator.dart`**
- After successful data sync, call `UserProfileSyncDatasource.pullCompanyMembers(companyId)`
- After successful sync push, call `updateLastSyncedAt(userId)` on Supabase `user_profiles`

On company change, old company data persists in local SQLite. Wipe all local data tables on sign-out and on confirmed company change (after sync complete per CONT-P1-H5 fix). `clearLocalCompanyData()` should execute `DELETE FROM projects`, `DELETE FROM daily_entries`, etc. for all 17 data tables, plus `DELETE FROM user_profiles WHERE id != currentUserId`.

The "remote empty → push all" heuristic (CRIT-8/CONT-13 fix) is the cross-company push attack vector and its removal is a BLOCKING prerequisite before multi-tenant goes live — not a deferral. This overlaps with the CRIT-8 fix already specified in Phase 3.

`photo_remote_datasource.dart:60` returns `getPublicUrl()` (unauthenticated). Phase 1A already adds signed URL storage policies. Ensure the Dart-side switch from `getPublicUrl()` → `createSignedUrl(expiresIn: 3600)` is included in Phase 1B or Phase 3, not deferred indefinitely. Mark as a Phase 1 blocker alongside storage bucket RLS. Verify that the storage bucket RLS policies (`company_photo_select`, `company_photo_insert`, `company_photo_delete`) specified in Phase 1A are included in the Phase 1 migration file — not accidentally omitted.

`toMap()` in models may push `null` `company_id` to Supabase on INSERT for existing records before migration backfill runs. This is acceptable (nullable column) but verify that pushing `null` does not violate any in-progress RLS policies. After Phase 1 backfill and `NOT NULL` constraint is set, this can no longer occur.

`pullCompanyMembers()` caches company member profiles (names, phones, cert numbers) in plaintext local SQLite. On sign-out, this cache must be cleared. In Phase 3, add `clearLocalCompanyData()` to `AuthService` that is called on sign-out and on company change. Consider `sqflite_sqlcipher` for encryption as a future enhancement.

SharedPreferences are not cleared on sign-out — this leaks user IDs and project IDs across device users. Add SharedPreferences clearing to the sign-out flow in `AuthService.signOut()`. Clear all user-scoped keys: `'last_project_$userId'`, `'recent_projects_$userId'`, and any other user-keyed prefs.

Removing `entry_personnel` from sync leaves an orphaned remote datasource and imports. Verify and delete (or mark deprecated): `entry_personnel_remote_datasource.dart` and any import references to it. Run `flutter analyze` to catch dead imports.

### 3F — Supabase: No New Migration Needed for Phase 3

Phase 3 is purely Dart-side. RLS already enforces company scoping server-side (from Phase 1). The `last_synced_at` column already exists on `user_profiles` (from Phase 1 migration).

The stale-data banner must be specified before implementation: implement it as a non-dismissible `MaterialBanner` at the top of the main shell showing "Data may be out of date — last synced [time]" with a "Sync Now" action button. Show it when `SyncProvider.isStaleDataWarning == true`.

### Phase 3 Acceptance Criteria
- [ ] `flutter analyze` — zero errors
- [ ] `flutter test` — all pass
- [ ] User A (company 1) creates entry → syncs → User B (company 1) pulls → sees entry
- [ ] User C (company 2) cannot see company 1's data (RLS blocks)
- [ ] App goes to background → sync fires within 30s
- [ ] App opens after 24h → forced non-dismissible sync runs before content loads
- [ ] App opens offline after 24h → stale-data banner visible
- [ ] `user_profiles.last_synced_at` updates after each successful sync
- [ ] `created_by_user_id` populated on all new records in Supabase

---

## Phase 4: Firebase + Background Sync

**Agent**: `backend-data-layer-agent`
**Estimated files**: 4 new, 4 modified
**Dependencies**: Phase 3 complete

**HIGH-12 fix**: WorkManager and FCM do not work on Windows/desktop. Phase 4 needs a fallback strategy: periodic timer-based sync (e.g., every 4 hours) on desktop platforms instead of FCM push notifications.

Firebase initialization must be guarded by a platform check. Wrap `Firebase.initializeApp()` with `if (Platform.isAndroid || Platform.isIOS)` — Windows builds will crash otherwise. Apply the same guard for `FcmHandler.initialize()` and WorkManager registration.

The background sync isolate (WorkManager callback) runs in a fresh Dart isolate with no JWT. `currentSession` is null unless `recoverSession()` is called. Add at the TOP of `backgroundSyncCallback()`:
```dart
final session = await supabase.auth.recoverSession(/* stored refresh token */);
if (session == null) return; // abort — cannot sync without auth
```
Store the refresh token in `FlutterSecureStorage` (not SharedPreferences) for isolate access.

The WorkManager isolate creates a second SQLite connection. Two concurrent writers cause `SQLITE_BUSY`. Enable WAL mode in `DatabaseService._initDatabase()`: `await db.execute('PRAGMA journal_mode=WAL');`. WAL allows one writer + multiple readers concurrently.

The `daily-sync-push` Edge Function uses `service_role` and has no Authorization header check — anyone who finds the URL can trigger mass FCM sends. Add: `const authHeader = req.headers.get('Authorization'); if (authHeader !== 'Bearer ' + Deno.env.get('CRON_SECRET')) return new Response('Unauthorized', { status: 401 });` Set `CRON_SECRET` in Supabase Edge Function environment variables.

FCM tokens are not cleaned up on deactivation. Add `DELETE FROM user_fcm_tokens WHERE user_id = target_user_id` inside the `deactivate_member()` SECURITY DEFINER RPC body (Phase 1A amendment). This prevents push notifications reaching a sold/reassigned device.

Firebase config files (`google-services.json`, `GoogleService-Info.plist`) contain the FCM messaging sender ID and are typically in source control. These are public identifiers (not secrets) — they cannot be used to send messages without the Firebase Admin SDK private key. Accept this as a known, documented risk.

The desktop sync timer has no jitter — if many users open the app simultaneously, they create coordinated load spikes. Add random jitter to the desktop periodic timer: `Duration(hours: 4) + Duration(minutes: Random().nextInt(30))`.

`saveFcmToken()` has no token format validation. Add a minimal guard: `if (token.isEmpty || token.length > 512) return;` to prevent obviously invalid tokens being stored.

**NOTE**: This phase requires external setup before coding:
1. Create Firebase project at console.firebase.google.com
2. Add Android app, download `google-services.json` → `android/app/google-services.json`
3. Add iOS app, download `GoogleService-Info.plist` → `ios/Runner/GoogleService-Info.plist`
4. Note the FCM Server Key for the Supabase Edge Function

### 4A — Flutter Dependencies

#### Files to Modify

**`pubspec.yaml`**
- Add dependencies:
  ```yaml
  firebase_core: ^3.x.x
  firebase_messaging: ^15.x.x
  workmanager: ^0.5.x
  ```
- Run `flutter pub get`

### 4B — Android Configuration

#### Files to Modify

**`android/app/build.gradle`**
- Ensure `google-services` plugin is applied at the bottom:
  ```gradle
  apply plugin: 'com.google.gms.google-services'
  ```

**`android/build.gradle`**
- Add to `buildscript.dependencies`:
  ```gradle
  classpath 'com.google.gms:google-services:4.4.x'
  ```

**`android/app/src/main/AndroidManifest.xml`**
- Add `INTERNET` permission (likely already present)
- Add `FCM_FALLBACK_NOTIFICATION_CHANNEL_ID` meta-data if needed
- Register background service for WorkManager

#### Files to Create

**`android/app/src/main/kotlin/.../BackgroundSyncService.kt`** (or Dart isolate via WorkManager)
- WorkManager callback that triggers Dart background sync isolate

### 4C — iOS Configuration

#### Files to Modify

**`ios/Runner/AppDelegate.swift`**
- Add Firebase initialization: `FirebaseApp.configure()`
- Register BGProcessingTask identifier

**`ios/Runner/Info.plist`**
- Add `BGTaskSchedulerPermittedIdentifiers` array with `com.fvconstruction.fieldfguide.sync`
- Add `UIBackgroundModes`: `remote-notification`, `background-fetch`

### 4D — Dart: Firebase + Background Sync Handler

#### Files to Create

**`lib/features/sync/application/background_sync_handler.dart`**
- `@pragma('vm:entry-point') void backgroundSyncCallback()` — top-level function for WorkManager
- Initializes Firebase, Supabase, database, then runs sync
- Handles Android WorkManager task
- Updates `last_synced_at` on `user_profiles` after completion

**`lib/features/sync/application/fcm_handler.dart`**
- `FcmHandler` class
- `initialize()` — sets up `FirebaseMessaging` instance, requests permissions
- `onBackgroundMessage(RemoteMessage message)` — top-level handler `@pragma('vm:entry-point')`
- Checks `message.data['type'] == 'daily_sync'` → triggers background sync
- Note: FCM payload has no HMAC signature. The FCM sender ID is in Firebase config files (source control). Any entity with the sender ID can send push notifications to trigger fake "sync now" pushes. Accepted risk for now — the only action is a silent data sync which is idempotent. If social-engineering risk grows, add a server-generated HMAC in the FCM `data` payload and validate it client-side before triggering sync.

#### Files to Modify

**`lib/main.dart`**
- Add `await Firebase.initializeApp()` before Supabase init
- Initialize `FcmHandler` and call `fcmHandler.initialize()`
- Register WorkManager `Workmanager().initialize(backgroundSyncCallback)`
- Register FCM background message handler: `FirebaseMessaging.onBackgroundMessage(_fcmBackgroundHandler)`

### 4E — Supabase Edge Function: Daily Cron

#### Files to Create

**`supabase/functions/daily-sync-push/index.ts`**
- Supabase Edge Function (Deno)
- Triggered by cron (set up in Supabase dashboard: `0 2 * * *` = 2:00 AM UTC)
- Fetches all approved users' FCM tokens from `user_fcm_tokens` table (SEC-NEW-6 fix: uses service_role, bypasses RLS)
- Sends silent FCM data message to each token via Firebase Admin SDK

**`supabase/migrations/20260222200000_add_fcm_tokens.sql`**
- SEC-NEW-6 fix: Separate table instead of column on user_profiles (prevents token leakage to company members)
  ```sql
  CREATE TABLE user_fcm_tokens (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
  );
  ALTER TABLE user_fcm_tokens ENABLE ROW LEVEL SECURITY;
  CREATE POLICY "own_token_only" ON user_fcm_tokens
    FOR ALL TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());
  ```

#### Files to Modify (Dart side for FCM token storage)

**`lib/features/auth/services/auth_service.dart`**
- Add `saveFcmToken(String userId, String token) → Future<void>`
- Upserts to `user_fcm_tokens` table (SEC-NEW-6 fix: separate table, not user_profiles column)

**`lib/features/sync/application/fcm_handler.dart`**
- In `initialize()`, after `getToken()`, call `AuthService.saveFcmToken(userId, token)`
- Also call `FirebaseMessaging.instance.onTokenRefresh.listen(...)` to update on refresh

### Phase 4 Acceptance Criteria
- [ ] `flutter analyze` — zero errors
- [ ] `flutter test` — all pass
- [ ] Android: kill app → FCM push arrives → background sync runs → `last_synced_at` updates
- [ ] iOS: background sync runs (best-effort, may take up to system discretion)
- [ ] FCM token saved to `user_fcm_tokens` table after app launch
- [ ] Edge Function deployed and visible in Supabase dashboard
- [ ] No battery abuse: sync fires at most once per day from FCM, not continuously

---

## Phase 5: Project Switcher

**Agent**: `frontend-flutter-specialist-agent`
**Estimated files**: 2 new, 5 modified
**Dependencies**: Phase 2 complete (AuthProvider has userProfile)

### 5A — Project Switcher Widget

#### Files to Create

**`lib/features/projects/presentation/widgets/project_switcher.dart`**
- `ProjectSwitcher` widget — a `DropdownButton`-style widget or custom `PopupMenuButton`
- Shows: current project name or "Select Project" if none
- Opens: overlay/bottom sheet with:
  - "RECENT PROJECTS" section (last 3 from `ProjectSettingsProvider`)
  - Active project marked with filled circle icon
  - "View All Projects" link → `context.goNamed('projects')`
  - "+ New Project" link → `context.goNamed('project-new')`
- On project tap: calls `ProjectProvider.selectProject(project.id)` (CONT-11 fix: method takes String id, not Project object)

**`lib/features/projects/presentation/widgets/project_switcher_sheet.dart`**
- Bottom sheet content for the switcher
- `ProjectSwitcherSheet` widget with `Consumer<ProjectProvider>`
- Shows all active projects grouped as recent (last 3) + all others

#### Files to Modify

**`lib/features/projects/presentation/widgets/widgets.dart`**
- Add exports: `project_switcher.dart`, `project_switcher_sheet.dart`

**`lib/core/router/app_router.dart`**
- Update `ScaffoldWithNavBar` builder to wrap content with a project switcher
- Add `ProjectSwitcher` widget to the app bar of the shell
- OR update each shell route's `AppBar` — prefer updating `ScaffoldWithNavBar`

**`lib/features/projects/presentation/providers/project_settings_provider.dart`**
- **HIGH-1 fix**: Migrate `lastProjectId` from global pref key to per-user key: `'last_project_$userId'` — prevents multi-user device conflicts
- Add `List<String> recentProjectIds` (last 3 project IDs, stored in prefs, keyed by user_id)
- Add `addRecentProject(String userId, String projectId)` method
- Key format: `'recent_projects_$userId'` — different per user
- On first run after upgrade, check if the old global `'lastProjectId'` key exists in prefs and migrate its value to `'last_project_$userId'`, then delete the old key. This prevents the project switcher from opening with no selection for existing users.

The `ProjectSwitcher` placed in `ScaffoldWithNavBar` (shell app bar) will appear on ALL routes including Settings, which has no concept of a "current project." Consider showing the project switcher only on project-context routes (dashboard, entries, quantities, etc.) by checking the current route in `ScaffoldWithNavBar`.

**`lib/features/projects/presentation/providers/project_provider.dart`**
- Update `selectProject(String id)` → also calls `projectSettingsProvider.addRecentProject(userId, id)`
- Update `loadProjects()` → only loads projects for the current company
  - Will need `companyId` from `AuthProvider`
  - Add `loadProjectsByCompany(String companyId)` method
  - `_localDatasource.getAll()` → `_localDatasource.getByCompanyId(companyId)`

**`lib/features/projects/data/datasources/local/project_local_datasource.dart`**
- Add `getByCompanyId(String companyId)` — queries `SELECT * FROM projects WHERE company_id = ?`

### 5B — Project Creation Updates

#### Files to Modify

**`lib/features/projects/presentation/screens/project_setup_screen.dart`**
- On project save, auto-set `companyId` from `context.read<AuthProvider>().userProfile?.companyId`
- Auto-set `createdByUserId` from `context.read<AuthProvider>().userId`
- Uniqueness check: before saving, call `ProjectRepository.getByProjectNumberInCompany(number, companyId)` — if exists, show error "Project number already exists in your company."

**`lib/features/projects/data/repositories/project_repository.dart`**
- Add `getByProjectNumberInCompany(String projectNumber, String companyId) → Future<Project?>`
- Queries: `SELECT * FROM projects WHERE project_number = ? AND company_id = ? LIMIT 1`
- Add `getByCompanyId(String companyId) → Future<List<Project>>`

**`lib/features/projects/data/datasources/local/project_local_datasource.dart`**
- Add `getByProjectNumberInCompany(String projectNumber, String companyId) → Future<Project?>`
- Add `getByCompanyId(String companyId) → Future<List<Project>>`

The project number uniqueness check is local-only (race condition if two users create the same project number simultaneously). The `UNIQUE INDEX idx_project_number_company ON projects(company_id, project_number)` in Phase 1A is the authoritative server-side check. The local check is UX-only. Handle the Supabase unique constraint violation gracefully in `ProjectRepository.create()` → show "Project number already exists."

### Phase 5 Acceptance Criteria
- [ ] `flutter analyze` — zero errors
- [ ] `flutter test` — all pass
- [ ] App opens → last project auto-loads (same as before, but now per-user)
- [ ] Tap switcher → overlay opens with recent projects
- [ ] Tap different project → all providers refresh, dashboard shows new project's data
- [ ] "View All" → navigates to project list
- [ ] "+ New Project" → navigates to project setup
- [ ] New project creation: company_id auto-set, uniqueness validated within company
- [ ] Duplicate project number → error message shown, save blocked
- [ ] Two users in same company: each sees all company projects in switcher

---

## Phase 6: Admin Dashboard

**Agent**: `frontend-flutter-specialist-agent` + `backend-data-layer-agent`
**Estimated files**: 4 new, 3 modified
**Dependencies**: Phase 2 complete (AuthProvider has role), Phase 3 complete (user_profiles synced)

### 6A — Admin Data Layer (backend-data-layer-agent)

#### Files to Create

Note on placement: `admin_repository.dart` is placed under `settings/data/` but admin operations are auth-domain logic. Consider placing it under `auth/data/repositories/` instead. At minimum, document the placement rationale. If it stays in `settings/`, ensure it is clearly separated from settings-specific repos.

`AdminProvider(AdminRepository(supabaseClient, authProvider))` breaks the current pattern — no existing provider takes another provider as a constructor argument. Fix: pre-construct `AuthProvider` outside `MultiProvider` (already required by CONT-P1-H1 fix), then pass it directly to `AdminRepository` constructor. Alternatively, use `ChangeNotifierProxyProvider<AuthProvider, AdminProvider>` and document this as the new pattern for auth-dependent providers.

**`lib/features/settings/data/repositories/admin_repository.dart`**
- `getPendingJoinRequests(String companyId) → Future<List<CompanyJoinRequest>>`
  - Queries Supabase `company_join_requests` WHERE `company_id = companyId AND status = 'pending'`
- `approveJoinRequest(String requestId, UserRole role) → Future<void>`
  - **SEC-5 fix**: Calls `approve_join_request` SECURITY DEFINER RPC instead of direct table updates
  - `await supabase.rpc('approve_join_request', params: {'request_id': requestId, 'assigned_role': role.name})`
- `rejectJoinRequest(String requestId) → Future<void>`
  - **SEC-5 fix**: Calls `reject_join_request` SECURITY DEFINER RPC
  - `await supabase.rpc('reject_join_request', params: {'request_id': requestId})`
- `getCompanyMembers(String companyId) → Future<List<UserProfile>>`
  - Queries `user_profiles` WHERE `company_id = companyId AND status != 'pending'`
- `updateMemberRole(String userId, UserRole role) → Future<void>`
  - Calls `supabase.rpc('update_member_role', params: {'target_user_id': userId, 'new_role': role.name})`
- `deactivateMember(String userId) → Future<void>`
  - Calls `supabase.rpc('deactivate_member', params: {'target_user_id': userId})`
  - SEC-NEW-4 fix: Passive JWT expiry. RLS blocks deactivated users immediately. JWT expires within ≤1 hour. App checks profile status on every launch — forces local sign-out if deactivated.
- `reactivateMember(String userId) → Future<void>`
  - Calls `supabase.rpc('reactivate_member', params: {'target_user_id': userId})`
- `promoteToAdmin(String userId) → Future<void>`
  - Calls `supabase.rpc('promote_to_admin', params: {'target_user_id': userId})`

**`lib/features/settings/presentation/providers/admin_provider.dart`**
- `AdminProvider extends ChangeNotifier`
- Holds: `List<CompanyJoinRequest> pendingRequests`, `List<UserProfile> companyMembers`
- Methods: `loadPendingRequests()`, `loadCompanyMembers()`, `approveRequest(...)`, `rejectRequest(...)`, `updateRole(...)`, `deactivate(...)`, `reactivate(...)`
- Stale flag helpers: `isSynced(UserProfile p)` → compare `p.lastSyncedAt` to `DateTime.now()`
  - `< 24h` → `SyncHealth.green`
  - `24-48h` → `SyncHealth.yellow`
  - `> 48h` → `SyncHealth.red`
  - `null` → `SyncHealth.never`

#### Files to Modify

**`lib/features/settings/presentation/providers/providers.dart`**
- Add export: `admin_provider.dart`

### 6B — Admin Dashboard Screen (frontend-flutter-specialist-agent)

#### Files to Create

**`lib/features/settings/presentation/screens/admin_dashboard_screen.dart`**
- Full-screen route (not in shell)
- AppBar: "Admin Dashboard" + back button
- Sections:
  1. **PENDING REQUESTS** — `Consumer<AdminProvider>`: list of `CompanyJoinRequest` rows
     - Each row: user email, requested date, "Approve as [DropdownButton]" button, "Reject" button
     - Approve dropdown: Inspector / Engineer / Viewer (Admin not offered to prevent accidental admin grants)
     - Confirm dialog before approve/reject
  2. **TEAM MEMBERS** — list of `UserProfile` rows
     - Each row: display_name (or email prefix), role badge, last_synced_at with color-coded stale indicator
     - Stale indicator: green dot (<24h), yellow warning icon (24-48h), red alert icon (>48h) or "Never"
     - Tap → opens member detail bottom sheet

**`lib/features/settings/presentation/widgets/member_detail_sheet.dart`**
- Bottom sheet for tapping a team member
- Shows: display_name, email (if available), role, status, last_synced_at
- Actions:
  - Change role: dropdown selector + "Save" → calls `AdminProvider.updateRole()`
  - Deactivate / Reactivate toggle button
  - Guard: "Cannot remove last admin" — show error if they try to demote/deactivate only admin

#### Files to Modify

**`lib/features/settings/presentation/screens/settings_screen.dart`**
- In the Account section, add `Consumer<AuthProvider>` block:
  ```dart
  if (authProvider.isAdmin)
    ListTile(
      leading: const Icon(Icons.admin_panel_settings),
      title: const Text('Admin Dashboard'),
      trailing: const Icon(Icons.chevron_right),
      onTap: () => context.push('/admin-dashboard'),
    ),
  ```

**`lib/core/router/app_router.dart`**
- Add route:
  ```dart
  GoRoute(
    path: '/admin-dashboard',
    name: 'admin-dashboard',
    builder: (context, state) => const AdminDashboardScreen(),
  ),
  ```

**`lib/main.dart`**
- Add `AdminProvider` to the provider list
- Initialize with `AdminRepository(supabaseClient, authProvider)`

Admin Dashboard placement: insert the "Admin Dashboard" `ListTile` as the FIRST item in the Account section in `settings_screen.dart`, before "Edit Profile." This ensures admins see it prominently.

Deactivation window: "RLS blocks immediately" is not fully accurate — JWT-based auth means the deactivated user's token remains valid until expiry (up to 1 hour). A fired employee with the app open can read all data. For sensitive deployments, reduce JWT expiry to 5-10 minutes in Supabase Auth settings. Document as an accepted risk for standard deployments.

`AdminRepository` relies solely on Supabase RLS for authorization. Add client-side `companyId` validation in each admin method: assert that the `target_user_id`'s `company_id` matches `AuthProvider.companyId` before calling any RPC, as defense-in-depth against accidental cross-company admin operations.

The `SyncHealth` indicator in the admin dashboard exposes team activity timing — an attacker who gains read-only admin access can infer when inspectors are in the field. Accepted risk for this use case; `last_synced_at` is considered non-sensitive internal data.

There is no rate limiting on admin RPCs — a compromised admin account could mass-approve all pending requests. Consider adding a rate limit in the RPC or middleware. Low priority for single-company deployment; document as a future enhancement.

### Phase 6 Acceptance Criteria
- [ ] `flutter analyze` — zero errors
- [ ] `flutter test` — all pass
- [ ] Non-admin: "Admin Dashboard" not visible in Settings
- [ ] Admin: "Admin Dashboard" visible in Settings
- [ ] Pending requests list shows all pending join requests for the company
- [ ] Approve request → user gains access, user's pending screen auto-navigates
- [ ] Reject request → user sees rejected screen
- [ ] Change role → updated in Supabase, user sees role change on next sync
- [ ] Deactivate → user's next request blocked (RLS / status check)
- [ ] Reactivate → user regains access
- [ ] Last-admin guard: error shown if admin attempts to demote/deactivate last admin
- [ ] Stale sync flags: green/yellow/red displayed correctly per `last_synced_at`

---

## Phase 7: Audit Trail UI

**Agent**: `frontend-flutter-specialist-agent` + `pdf-agent`
**Estimated files**: 2 new, 8 modified
**Dependencies**: Phase 3 complete (user_profiles cached locally)

**Prerequisite check**: Phase 7 audit trail requires `createdByUserId` on `DailyEntry`, `Photo`, and `Project` models in current code AND in SQLite schema. These MUST be added in Phase 1B (models) and Phase 1C (SQLite). Phase 7 cannot function without them. Before beginning Phase 7, confirm `DailyEntry.createdByUserId`, `Photo.createdByUserId`, and `Project.createdByUserId` fields exist.

`UserAttributionRepository` has no provider wrapper — widgets cannot access it via `context.read<>()`. Add `ChangeNotifierProvider` or `Provider<UserAttributionRepository>` in `main.dart`. Register it in the provider list alongside other repositories.

### 7A — User Attribution Service (frontend-flutter-specialist-agent)

#### Files to Create

**`lib/features/auth/data/repositories/user_attribution_repository.dart`**
- `getDisplayName(String? userId) → Future<String>`
  - Returns `UserProfile.displayName` if exists
  - Else returns email prefix (split `@`) from `user_profiles.id` → look up in Supabase auth — skip: just show "Unknown"
  - Falls back to "Unknown" if null or not found
  - Uses `UserProfileLocalDatasource` first (offline-capable), then remote on cache miss
- `getDisplayNames(List<String> userIds) → Future<Map<String, String>>`
  - Batch fetch for efficiency

**`lib/features/auth/presentation/widgets/user_attribution_text.dart`**
- `UserAttributionText` widget
- Parameters: `userId` (String?), `prefix` (String, e.g., "Recorded by:"), `style` (TextStyle?)
- Uses `FutureBuilder` backed by `UserAttributionRepository.getDisplayName(userId)`
- Shows `"$prefix [Display Name]"` or `"$prefix Unknown"` on error/null
- Graceful offline: always resolves from local cache
- The `getDisplayName()` remote fallback (on cache miss) must scope the Supabase query to `company_id = get_my_company_id()` — otherwise it could return display names from other companies. Always add `.eq('company_id', companyId)` to the remote profile lookup.
- Avoid per-widget `FutureBuilder` calls: `UserAttributionText` with one `FutureBuilder` per entry × 50 entries = 50 concurrent async calls on cold cache. Use the `getDisplayNames(List<String> userIds)` batch method and a single `FutureBuilder` at the list level to pre-fetch all names before rendering.

### 7B — UI: Attribution Display (frontend-flutter-specialist-agent)

#### Files to Modify

**`lib/features/entries/presentation/screens/entries_list_screen.dart`** (or the entry card widget)
- Add `UserAttributionText(userId: entry.createdByUserId, prefix: 'Recorded by:')` to each entry card
- Place below the date/location info, small secondary text style

**`lib/features/entries/presentation/screens/entry_editor_screen.dart`**
- In view mode (not editing), show attribution below the header

**`lib/features/photos/presentation/widgets/photo_thumbnail.dart`** (or photo detail dialog)
- Add "Uploaded by: [Name]" to photo detail view

**`lib/features/entries/presentation/screens/report_widgets/report_photo_detail_dialog.dart`**
- Add "Uploaded by: [Name]" row using `UserAttributionText`

**`lib/features/projects/presentation/screens/project_setup_screen.dart`** (in view mode)
- Add "Created by: [Name]" in project details header

### 7C — PDF Attribution (pdf-agent)

#### Files to Modify

**`lib/features/pdf/services/pdf_service.dart`**
- Update PDF generation to include author name on daily entry reports
- Read `DailyEntry.createdByUserId`, resolve to display name via `UserAttributionRepository`
- Add "Inspector: [Name]" or "Recorded by: [Name]" to the entry header in the PDF template

**`lib/features/entries/presentation/controllers/pdf_data_builder.dart`**
- Add `createdByDisplayName` field to the PDF data model
- Fetch from `UserAttributionRepository` before building PDF data
- `PdfDataBuilder.generate()` currently takes only providers and datasources — no `UserAttributionRepository` in its parameter list. `IdrPdfData` already has `inspectorName` from `PreferencesService`. Map `createdByDisplayName` to `inspectorName` (replace the legacy PreferencesService source). Add `UserAttributionRepository userAttributionRepository` as a required named parameter to `PdfDataBuilder` or `PdfService`. Note: `pdf_data_builder.dart:120-122` reads inspector fields directly from SharedPreferences — this must be replaced with `UserAttributionRepository.getDisplayName(entry.createdByUserId)` in Phase 7 (if not already fixed in Phase 2E).

PDF exports include inspector name with no opt-out. For privacy compliance, consider adding a "Include inspector name in PDF" toggle in Settings (PDF Export section). Document as a future enhancement; default is "on" for audit trail integrity.

### Phase 7 Acceptance Criteria
- [ ] `flutter analyze` — zero errors
- [ ] `flutter test` — all pass
- [ ] Entry created by User A shows "Recorded by: John Doe" when User B views it
- [ ] Works offline: uses cached user_profiles — no network required
- [ ] Graceful fallback: "Recorded by: Unknown" when display_name is null
- [ ] Photo detail shows "Uploaded by: [Name]"
- [ ] Project detail shows "Created by: [Name]"
- [ ] Generated PDFs include "Inspector: [Name]" or "Recorded by: [Name]" in header/footer

---

## Phase 8: Viewer Role Enforcement

**Agent**: `frontend-flutter-specialist-agent`
**Estimated files**: 1 new, 12 modified
**Dependencies**: Phase 2 complete (AuthProvider has role), Phase 1 (viewer role in enum)

**Note**: `UserRole.viewer` was already added to the enum in Phase 1. Phase 8 makes it functional.

The viewer role is assignable from Phase 1 but viewer UI enforcement is Phase 8. Between Phases 1 and 8, a viewer could create local data that fails on sync (RLS blocks write). To mitigate: ensure `canWrite` is checked at the repository layer from Phase 2 onward — return early from any repository write method if `authProvider.canWrite == false`. Do not wait until Phase 8 for repository-level guards.

Note: `updated_at` is client-settable. For Phase 8, verify that viewer sync attempts (blocked by RLS) do not corrupt the local `sync_queue` with zombie operations that repeatedly fail.

### 8A — Supabase: Viewer Write Blocks — NO MIGRATION NEEDED

**CRIT-1 fix applied in Phase 1**: Viewer write blocks are already built into Phase 1's RLS policies. Every `FOR INSERT`, `FOR UPDATE`, and `FOR DELETE` policy includes `AND NOT is_viewer()`. The `is_viewer()` helper function is also created in Phase 1. No separate Phase 8 migration required.

Phase 8 is now **app-side only** (UI guards below).

### 8B — App-Side: Viewer UI Changes

#### Files to Create

**`lib/shared/widgets/view_only_banner.dart`**
- `ViewOnlyBanner` widget — a subtle non-intrusive info bar
- Shows when `AuthProvider.userRole == UserRole.viewer`
- Text: "View-only mode" with an eye icon
- Shown at top of screens that have create/edit capabilities
- Add barrel export for `view_only_banner.dart` to `lib/shared/widgets/widgets.dart`. Without this, screens importing from the barrel won't find the widget.

#### Files to Modify

**`lib/features/entries/presentation/screens/entries_list_screen.dart`**
- Hide FAB (add new entry button) when `userProfile.role == UserRole.viewer`
- `Consumer<AuthProvider>` wrapping the FAB: `if (!authProvider.canWrite) return const SizedBox()`

**`lib/features/entries/presentation/screens/entry_editor_screen.dart`**
- Hide save/edit buttons for viewers
- Show `ViewOnlyBanner` at top
- All form fields read-only when viewer

**`lib/features/entries/presentation/screens/home_screen.dart`**
- Hide "New Entry" / "+" FABs for viewers

**`lib/features/photos/presentation/providers/photo_provider.dart`**
- In `addPhoto()` / `deletePhoto()`: check `canWrite` (from AuthProvider passed in or read from context)
- If viewer: throw or return early with error message
- `PhotoProvider`, `ContractorProvider`, and `LocationProvider` currently take only their `Repository` in the constructor — no mechanism to check `canWrite`. Specify the injection approach: add `AuthProvider authProvider` as a constructor parameter, OR use `ProxyProvider<AuthProvider, PhotoProvider>` in `main.dart`. Document this as the new pattern for viewer-aware providers.

**`lib/features/quantities/presentation/screens/quantities_screen.dart`**
- Hide "Add Bid Item" button for viewers

**`lib/features/projects/presentation/screens/project_setup_screen.dart`**
- In edit mode: guard with `authProvider.canWrite` — redirect to view-only display

**`lib/features/projects/presentation/screens/project_list_screen.dart`**
- Hide "+ New Project" FAB for viewers

**`lib/features/settings/presentation/screens/settings_screen.dart`**
- Hide "Edit Profile" for viewers (they can view but not edit)
- Hide Admin Dashboard (viewers can't be admins, but defensive check)

**`lib/features/contractors/presentation/providers/contractor_provider.dart`**
- Block add/edit/delete operations for viewers

**`lib/features/locations/presentation/providers/location_provider.dart`**
- Block add/edit/delete operations for viewers

The viewer guard list in the section above is not exhaustive — 6+ additional write surfaces must be covered. Add viewer blocks to ALL of the following providers and screens:
- `lib/features/todos/presentation/providers/todo_provider.dart` — guard `createTodo()`, `updateTodo()`, `deleteTodo()`; hide FAB in `todos_screen.dart`
- `lib/features/forms/presentation/providers/inspector_form_provider.dart` — guard form creation/submission
- `lib/features/forms/presentation/screens/forms_list_screen.dart` — hide "New Form" FAB
- `lib/features/contractors/data/providers/equipment_provider.dart` (or equivalent) — guard add/edit/delete
- `lib/features/contractors/data/providers/personnel_type_provider.dart` — guard add/edit/delete
- `lib/features/quantities/presentation/providers/bid_item_provider.dart` (or equivalent) — guard add/edit/delete
- `lib/features/entries/presentation/providers/daily_entry_provider.dart` — guard create/update/delete

Viewer enforcement should be defense-in-depth: UI-only guards are not sufficient. Add provider-level guards (return early from write methods) so that even if a UI guard is missed, the provider prevents the write attempt. This avoids confusing sync failure errors for viewers who hit the RLS 403 on next sync.

Inspector profile fields (display_name, cert_number, phone) are stored in SharedPreferences as plaintext during migration. After Phase 2E migration completes and keys are cleared, this is no longer an issue. Verify keys are cleared after migration.

Mock auth has hardcoded `test@example.com / Test123!` credentials in version control. Acceptable for a test/dev build, but add a check: `assert(!kReleaseMode, 'Mock auth is not allowed in release builds');`

`ViewOnlyBanner` is UI-only — a rooted device can make write calls directly to SQLite or bypass the UI. The RLS server-side guard is the authoritative defense. Document this explicitly. Offline writes by a rooted viewer will fail on next sync with a 403, and the sync error handler must surface this gracefully.

The 10s polling interval for pending approval (SEC-P1-M4 / CONT-P1-M6 fix) applies to viewer-state polling as well. The exponential backoff fix in `pending_approval_screen.dart` covers this case.

Phase deployment order creates a security window — viewer UI blocks are Phase 8, but a viewer is assignable from Phase 1. Between Phase 1 and Phase 8, a viewer with the old app version sees all write UI. RLS server-side is the authoritative guard. Document this window; it is acceptable for a sequential deployment where Phase 1→8 happens in one sprint.

### 8C — canWrite Helper

**`lib/features/auth/presentation/providers/auth_provider.dart`** (already modified in Phase 2)
- Ensure `canWrite` getter is already there: `bool get canWrite => _userProfile?.role != UserRole.viewer`
- Ensure `isViewer` getter: `bool get isViewer => _userProfile?.role == UserRole.viewer`

Post-Phase 8 deployment verification: run `SELECT policyname, tablename FROM pg_policies WHERE roles @> '{anon}'` and confirm it returns 0 rows. Also verify `SELECT policyname FROM pg_policies WHERE policyname ILIKE '%viewer%' OR cmd IN ('INSERT','UPDATE','DELETE')` shows `NOT is_viewer()` in all write policies.

### Phase 8 Acceptance Criteria
- [ ] `flutter analyze` — zero errors
- [ ] `flutter test` — all pass
- [ ] Viewer user: no FABs, no create/edit/delete buttons visible anywhere
- [ ] Viewer user: `ViewOnlyBanner` shown on entry list, entry editor, quantities, project list
- [ ] Viewer user: can read all projects, entries, photos, quantities
- [ ] Viewer user direct API write → Supabase RLS blocks → 403 error
- [ ] App handles RLS 403 gracefully (show friendly error, not crash)
- [ ] Admin/Engineer/Inspector: zero UI changes from their perspective
- [ ] Mock auth mode has a runtime assert preventing release builds
- [ ] All 6+ missing write providers (todos, forms, equipment, personnel_types, bid_items, daily_entries) have viewer guards

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| RLS misconfiguration allows cross-company data leak | Medium | High | Test Phase 1 with 2 Supabase accounts in different companies before Phase 2 |
| Roberto's `auth.users.id` not found for seed | Low | Medium | Check Supabase Auth dashboard before running Phase 1 migration |
| SQLite v24 migration breaks existing installs | Low | High | Test upgrade path with a v23 db file before Phase 1 merge |
| Router redirect loop (profile check causes infinite redirect) | Medium | High | Test all 5 redirect paths: no auth, no profile, pending, rejected, deactivated, approved |
| `pending_approval_screen` polling causes battery drain | Low | Medium | Use `Timer.periodic` at 10s intervals, cancel in `dispose()`, add Supabase Realtime as enhancement later |
| Firebase setup fails (missing config files) | Low | High | Phase 4 agent must document exact file placement before coding |
| Background sync on iOS is unreliable | High | Low | Documented in PRD as known limitation; Layer 3 (sync-on-open) is the safety net |
| PreferencesService migration runs twice | Low | Low | After migrating, clear the pref keys — check for null before migrating |
| `project_number` UNIQUE index breaks existing data | Medium | High | The uniqueness is within `(company_id, project_number)` — since there's only one company and all existing projects were Roberto's, this should be safe. Verify before applying. |
| Admin demotes self and locks out all admins | Low | High | Phase 6 last-admin guard: count admins before allowing demote/deactivate |
| Viewer RLS policy conflicts with existing company-scoped policies | Medium | Medium | Phase 8 adds additive policies; test: viewer insert attempt must return 403 |
| No rollback plan for Supabase migrations (LOW-4) | Medium | High | Write `rollback/` scripts for each migration phase (DROP new tables, DROP new columns, re-create old policies) before deploying |
| Cross-tenant sync leak via unfiltered `BaseRemoteDatasource.getAll()` | Medium | High | Add explicit `.eq('company_id', companyId)` on ALL pull queries as defense-in-depth (Phase 3 SEC-P3-C1 fix) |
| Photo storage publicly accessible via `getPublicUrl()` | Medium | High | Switch to signed URLs + company-scoped paths in Phase 1A (SEC-2 fix already addresses this; verify it's a Phase 1 blocker not a deferral) |
| 52+ `anon USING (true)` policies live until Phase 1 drops them | High | Critical | Deploy Phase 0 + Phase 1 atomically; verify with `SELECT FROM pg_policies WHERE roles @> '{anon}'` = 0 rows |
| `created_by_user_id` spoofable — no server enforcement | High | High | Add `BEFORE INSERT` trigger enforcing `created_by_user_id = auth.uid()` on all 17 data tables (SEC-P3-H3 fix) |
| Local SQLite retains leaked data permanently | Low | Medium | Clear local DB on sign-out and company change; no "recall" mechanism after cross-tenant leak |
| Partial migration rollback leaves mixed RLS state | Medium | High | Use atomic migration deployment; write rollback scripts for each phase before deploying |
| `BaseRemoteDatasource.deleteAll()` could wipe company data | Low | High | Restrict `deleteAll()` to debug builds; remove from production code paths entirely |
| Toolbox features (forms, todos, calculator) unguarded for viewers | High | Medium | Add viewer guards to all toolbox providers in Phase 8 (CONT-P3-H1 fix) |
| Mock auth has no concept of roles | Medium | Medium | `TestModeConfig.useMockAuth` must return a stub `UserProfile` with configurable role/status (HIGH-9 fix in Phase 2 acceptance criteria) |
| No rollback plan for provider constructor changes | Medium | Medium | Document rollback procedure: revert to previous constructor signatures if startup crash occurs after provider pattern changes |
| `UserAttributionText` FutureBuilder × 50 entries = 50 concurrent async calls | Low | Low | Use batch `getDisplayNames()` at list level (addressed in Phase 7 widget spec above) |
| JWT refresh token theft allows indefinite access after deactivation | Low | Medium | Reduce JWT expiry for sensitive deployments; document passive expiry model as accepted risk for standard use |

---

## Estimated File Count Per Phase

| Phase | New Files | Modified Files | Notes |
|-------|-----------|---------------|-------|
| 0 | 0 | 0 | Just deploy the SQL |
| 1 | 7 | 12 | Migration SQL + models + SQLite schema + datasources |
| 2 | 12 | 8 | 4 new screens + remote datasources + router + settings |
| 3 | 4 | 14 | Lifecycle manager + sync scoping across 8 remote datasources |
| 4 | 4 | 4 | Firebase setup + edge function + background handler |
| 5 | 2 | 5 | Project switcher widget + project-scoped queries |
| 6 | 4 | 3 | Admin screen + admin provider + admin repository |
| 7 | 2 | 8 | Attribution widget + entry/photo/pdf attribution display |
| 8 | 1 | 12 | View-only banner + viewer guards across 10 screens |
| **Total** | **36** | **66** | **102 files touched across 8 phases** |

---

## Agent Handoff Table

| Phase | Work Type | Agent(s) |
|-------|-----------|---------|
| 0 | Deploy Supabase migration | `backend-supabase-agent` |
| 1A | Supabase schema, RLS, seed, backfill | `backend-supabase-agent` |
| 1B | Dart models, datasources, repositories | `backend-data-layer-agent` |
| 1C | SQLite v24 migration + schema files | `backend-data-layer-agent` |
| 2A | AuthService + AuthProvider updates | `auth-agent` |
| 2B | Onboarding screens | `frontend-flutter-specialist-agent` |
| 2C | Settings + Edit Profile screen | `frontend-flutter-specialist-agent` |
| 2D | Router redirects | `auth-agent` |
| 2E | PreferencesService migration | `auth-agent` |
| 3A | Sync adapter company scoping | `backend-supabase-agent` |
| 3B-3C | Lifecycle manager, stale check | `backend-data-layer-agent` |
| 3D-3E | Remote datasource updates, profile sync | `backend-data-layer-agent` |
| 4 | Firebase + WorkManager + Edge Function | `backend-data-layer-agent` |
| 5 | Project switcher widget + scoped queries | `frontend-flutter-specialist-agent` |
| 6A | Admin data layer | `backend-data-layer-agent` |
| 6B | Admin dashboard screen | `frontend-flutter-specialist-agent` |
| 7A | User attribution repository + widget | `frontend-flutter-specialist-agent` |
| 7B | Attribution in entry/photo/project UI | `frontend-flutter-specialist-agent` |
| 7C | PDF attribution | `pdf-agent` |
| 8A | Viewer RLS migration | `backend-supabase-agent` |
| 8B | Viewer UI guards | `frontend-flutter-specialist-agent` |

---

## Verification Checklist (Per Phase)

Each phase must pass before the next begins:

```bash
# Static analysis
pwsh -Command "flutter analyze"    # Must be: No issues found

# Unit tests
pwsh -Command "flutter test"       # Must be: All tests pass

# Manual verification (per-phase acceptance criteria above)
```

PR checklist before merge:
- [ ] `flutter analyze` — no issues
- [ ] `flutter test` — all pass
- [ ] Phase acceptance criteria satisfied
- [ ] No hardcoded UUIDs left in Dart code (seed data only in SQL)
- [ ] Offline scenario tested (airplane mode): app still loads, shows stale banner if applicable
- [ ] No new anti-patterns (check `.claude/defects/` for relevant feature)


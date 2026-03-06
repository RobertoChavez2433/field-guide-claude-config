# Section B: Schema, Security & Settings -- Implementation Plan

## Pre-requisites

Before any of this section can be implemented:

1. **Branch**: Work on the existing `fix/sync-dns-resilience` branch or a dedicated `feature/section-b-schema-security` branch
2. **Current DB version**: SQLite is at v29 (`lib/core/database/database_service.dart:54`). This section bumps it to v30.
3. **Latest Supabase migration**: `20260304200000_drop_sync_status_from_supabase.sql`. New migration(s) must use a timestamp after `20260304200000`.
4. **No uncommitted schema changes**: Verify `git status` shows no pending changes to `database_service.dart` or `supabase/migrations/`.
5. **Section A (Sync Engine Core)** does NOT need to be complete first. Section B is independently deployable. However, the `sync_control`, `change_log`, `conflict_log`, `sync_lock`, and `synced_projects` tables in the v30 SQLite migration are shared with Section A. If Section A has already created them, skip those CREATE TABLE statements.

---

## Implementation Order Summary

The steps below are ordered by dependency:

1. **Step 1**: Supabase migration SQL file (all server-side schema + security changes in one atomic migration)
2. **Step 2**: `supabase/config.toml` -- secure_password_change
3. **Step 3**: UserProfile model expansion (add 4 new fields)
4. **Step 4**: SQLite v30 migration (schema tables + `database_service.dart`)
5. **Step 5**: PreferencesService dead code removal
6. **Step 6**: Consumer migration (PreferencesService -> AuthProvider.userProfile)
7. **Step 7**: PII cleanup from SharedPreferences
8. **Step 8**: Purge handler in SyncService
9. **Step 9**: Settings screen redesign
10. **Step 10**: Delete orphaned EditInspectorDialog widget
11. **Step 11**: Verification checklist

---

## Step 1: Supabase Migration -- Schema Alignment + Security Fixes

**File**: `supabase/migrations/20260305000000_schema_alignment_and_security.sql`
**Action**: Create
**Depends on**: Nothing (first step)

This is the complete, single-file Supabase migration. Every SQL statement below goes into this one file, in this exact order.

### 1.1 Migration ordering rationale

The SQL is ordered to satisfy dependencies:
- GAP-9 (inspector_forms soft-delete) MUST come before `get_table_integrity` RPC (which filters by `deleted_at IS NULL` on all 16 tables)
- `is_approved_admin()` function MUST come before admin RPC rewrites
- `user_certifications` table MUST exist before cert_number data migration
- Storage RLS fix is first because it is a BLOCKING security fix

### 1.2 Complete SQL file content

```sql
-- Migration: Schema alignment, security fixes, and profile expansion
-- Date: 2026-03-05
-- Covers: NEW-1 (Storage RLS), NEW-6 (lock_created_by), NEW-7 (Admin RPCs),
--         GAP-9 (inspector_forms soft-delete), GAP-10 (updated_at triggers),
--         GAP-19 (secure_password_change — config.toml, not SQL),
--         ADV-2 (enforce_insert_updated_at), ADV-9 (NOT NULL project_id),
--         ADV-15 (stamp_updated_by), ADV-22/23 (get_table_integrity),
--         ADV-25 (is_approved_admin), ADV-31 (calculation_history updated_at),
--         Decision 12 (profile expansion, user_certifications)

-- ============================================================================
-- PART 0: BLOCKING SECURITY FIX — Storage RLS (NEW-1)
-- ============================================================================
-- Current policies use (storage.foldername(name))[1] which matches 'entries'
-- (a constant string), not the companyId. Upload path is:
--   entries/{companyId}/{entryId}/{filename}
-- So [1]='entries', [2]=companyId, [3]=entryId.
-- Fix: change [1] to [2] in all three policies.

DROP POLICY IF EXISTS "company_photo_select" ON storage.objects;
CREATE POLICY "company_photo_select" ON storage.objects
  FOR SELECT TO authenticated
  USING (bucket_id = 'entry-photos'
    AND (storage.foldername(name))[2] = get_my_company_id()::text);

DROP POLICY IF EXISTS "company_photo_insert" ON storage.objects;
CREATE POLICY "company_photo_insert" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'entry-photos'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
    AND NOT is_viewer());

DROP POLICY IF EXISTS "company_photo_delete" ON storage.objects;
CREATE POLICY "company_photo_delete" ON storage.objects
  FOR DELETE TO authenticated
  USING (bucket_id = 'entry-photos'
    AND (storage.foldername(name))[2] = get_my_company_id()::text
    AND NOT is_viewer());

-- ============================================================================
-- PART 1: GAP-9 — Add soft-delete columns to inspector_forms on Supabase
-- ============================================================================
-- inspector_forms has deleted_at/deleted_by on SQLite (toolbox_tables.dart:24-25)
-- but is MISSING them on Supabase. Required before get_table_integrity RPC.

ALTER TABLE inspector_forms ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE inspector_forms ADD COLUMN IF NOT EXISTS deleted_by UUID REFERENCES auth.users(id);

CREATE INDEX IF NOT EXISTS idx_inspector_forms_deleted_at ON inspector_forms(deleted_at);

-- Update purge function to include inspector_forms
CREATE OR REPLACE FUNCTION purge_soft_deleted_records()
RETURNS void
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  -- Leaf junction tables (deepest children first)
  DELETE FROM entry_quantities WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM entry_equipment WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM entry_personnel WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM entry_personnel_counts WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM entry_contractors WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Photos (depend on entries and projects)
  DELETE FROM photos WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Toolbox tables (including inspector_forms)
  DELETE FROM form_responses WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM inspector_forms WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM todo_items WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';
  DELETE FROM calculation_history WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Personnel types
  DELETE FROM personnel_types WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Bid items
  DELETE FROM bid_items WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Equipment (depends on contractors)
  DELETE FROM equipment WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Daily entries (depend on projects)
  DELETE FROM daily_entries WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Contractors (depend on projects)
  DELETE FROM contractors WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Locations (depend on projects)
  DELETE FROM locations WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  -- Projects (top-level parent -- deleted last)
  DELETE FROM projects WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL '30 days';

  RAISE LOG 'purge_soft_deleted_records: completed at %', NOW();
END;
$$;

-- ============================================================================
-- PART 2: GAP-10 — updated_at triggers for entry_contractors & entry_personnel_counts
-- ============================================================================
-- [CORRECTION] The updated_at COLUMNS already exist on Supabase (added in
-- multi_tenant_foundation.sql:1048,1050). The ALTER TABLE ADD COLUMN is
-- idempotent (IF NOT EXISTS) so it's safe but redundant. The TRIGGERS however
-- do NOT exist yet — those are what's actually needed.

-- Idempotent column adds (no-op if already exist)
ALTER TABLE entry_contractors ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE entry_personnel_counts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Backfill any NULL updated_at values from created_at
UPDATE entry_contractors SET updated_at = created_at WHERE updated_at IS NULL;
UPDATE entry_personnel_counts SET updated_at = created_at WHERE updated_at IS NULL;

-- Create the missing triggers (these are the actual fix)
CREATE TRIGGER update_entry_contractors_updated_at
  BEFORE UPDATE ON entry_contractors
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_entry_personnel_counts_updated_at
  BEFORE UPDATE ON entry_personnel_counts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- PART 3: ADV-31 — calculation_history.updated_at NOT NULL + default
-- ============================================================================

UPDATE calculation_history SET updated_at = COALESCE(updated_at, created_at, NOW())
WHERE updated_at IS NULL;
ALTER TABLE calculation_history ALTER COLUMN updated_at SET NOT NULL;
ALTER TABLE calculation_history ALTER COLUMN updated_at SET DEFAULT NOW();

-- ============================================================================
-- PART 4: ADV-33 — form_responses.form_id FK alignment
-- ============================================================================
-- [CORRECTION] This was ALREADY fixed in catchup_v23.sql:247,253-266.
-- The DROP NOT NULL and DROP CONSTRAINT were already applied.
-- Including idempotent versions here for safety — these are no-ops.

ALTER TABLE form_responses ALTER COLUMN form_id DROP NOT NULL;
ALTER TABLE form_responses DROP CONSTRAINT IF EXISTS form_responses_form_id_fkey;

-- ============================================================================
-- PART 5: ADV-9 — NOT NULL constraint on project_id for toolbox tables
-- ============================================================================

-- Step 1: Backfill orphaned records
UPDATE inspector_forms
SET project_id = COALESCE(
  (SELECT de.project_id FROM daily_entries de WHERE de.id = inspector_forms.entry_id),
  (SELECT p.id FROM projects p WHERE p.company_id = (
    SELECT up.company_id FROM user_profiles up WHERE up.id = inspector_forms.created_by_user_id
  ) ORDER BY p.created_at LIMIT 1)
)
WHERE project_id IS NULL;

UPDATE todo_items
SET project_id = COALESCE(
  (SELECT de.project_id FROM daily_entries de WHERE de.id = todo_items.entry_id),
  (SELECT p.id FROM projects p WHERE p.company_id = (
    SELECT up.company_id FROM user_profiles up WHERE up.id = todo_items.created_by_user_id
  ) ORDER BY p.created_at LIMIT 1)
)
WHERE project_id IS NULL;

UPDATE calculation_history
SET project_id = COALESCE(
  (SELECT de.project_id FROM daily_entries de WHERE de.id = calculation_history.entry_id),
  (SELECT p.id FROM projects p WHERE p.company_id = (
    SELECT up.company_id FROM user_profiles up WHERE up.id = calculation_history.created_by_user_id
  ) ORDER BY p.created_at LIMIT 1)
)
WHERE project_id IS NULL;

-- Step 2: Hard-delete any remaining orphans that couldn't be backfilled
DELETE FROM inspector_forms WHERE project_id IS NULL;
DELETE FROM todo_items WHERE project_id IS NULL;
DELETE FROM calculation_history WHERE project_id IS NULL;

-- Step 3: Add NOT NULL constraints
ALTER TABLE inspector_forms ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE todo_items ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE calculation_history ALTER COLUMN project_id SET NOT NULL;

-- ============================================================================
-- PART 6: NEW-7 + ADV-25 — is_approved_admin() and Admin RPC rewrites
-- ============================================================================
-- All 6 admin RPCs currently check `role = 'admin'` but NOT `status = 'approved'`.
-- They also lack `SET search_path = public`.
-- Fix: create is_approved_admin() helper, rewrite all 6 RPCs.

CREATE OR REPLACE FUNCTION is_approved_admin()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM user_profiles
    WHERE id = auth.uid() AND role = 'admin' AND status = 'approved'
  )
$$ LANGUAGE sql SECURITY DEFINER STABLE SET search_path = public;

-- 6a: approve_join_request
CREATE OR REPLACE FUNCTION approve_join_request(
  request_id UUID,
  assigned_role TEXT DEFAULT 'inspector'
) RETURNS VOID AS $$
DECLARE
  v_company_id UUID;
  v_target_user_id UUID;
BEGIN
  -- is_approved_admin() MUST be first
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Not an approved admin';
  END IF;

  SELECT jr.company_id, jr.user_id INTO v_company_id, v_target_user_id
  FROM company_join_requests jr
  WHERE jr.id = request_id AND jr.status = 'pending';

  IF NOT FOUND THEN RAISE EXCEPTION 'Request not found or not pending'; END IF;
  IF v_company_id != get_my_company_id() THEN RAISE EXCEPTION 'Not your company'; END IF;
  IF assigned_role NOT IN ('inspector', 'engineer', 'viewer')
    THEN RAISE EXCEPTION 'Invalid role'; END IF;

  UPDATE company_join_requests
  SET status = 'approved', resolved_at = now(), resolved_by = auth.uid()
  WHERE id = request_id;

  UPDATE user_profiles
  SET company_id = v_company_id, role = assigned_role, status = 'approved', updated_at = now()
  WHERE id = v_target_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 6b: reject_join_request
CREATE OR REPLACE FUNCTION reject_join_request(request_id UUID)
RETURNS VOID AS $$
DECLARE
  v_company_id UUID;
BEGIN
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Not an approved admin';
  END IF;

  SELECT company_id INTO v_company_id
  FROM company_join_requests WHERE id = request_id AND status = 'pending';

  IF NOT FOUND THEN RAISE EXCEPTION 'Request not found or not pending'; END IF;
  IF v_company_id != get_my_company_id() THEN RAISE EXCEPTION 'Not your company'; END IF;

  UPDATE company_join_requests
  SET status = 'rejected', resolved_at = now(), resolved_by = auth.uid()
  WHERE id = request_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 6c: update_member_role
CREATE OR REPLACE FUNCTION update_member_role(target_user_id UUID, new_role TEXT)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_company_id UUID;
  v_target_company_id UUID;
  v_admin_count INTEGER;
BEGIN
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Not an approved admin';
  END IF;

  v_company_id := get_my_company_id();
  IF v_company_id IS NULL THEN RAISE EXCEPTION 'No company'; END IF;

  IF new_role NOT IN ('inspector', 'engineer', 'viewer')
    THEN RAISE EXCEPTION 'Invalid role'; END IF;

  SELECT company_id INTO v_target_company_id FROM user_profiles WHERE id = target_user_id;
  IF v_target_company_id != v_company_id THEN RAISE EXCEPTION 'User not in your company'; END IF;

  -- Last-admin guard: if demoting an admin, ensure at least one admin remains
  IF (SELECT role FROM user_profiles WHERE id = target_user_id) = 'admin' THEN
    SELECT count(*) INTO v_admin_count FROM user_profiles
      WHERE company_id = v_company_id AND role = 'admin' AND status = 'approved';
    IF v_admin_count <= 1 THEN RAISE EXCEPTION 'Cannot remove last admin'; END IF;
  END IF;

  UPDATE user_profiles
  SET role = new_role, updated_at = now()
  WHERE id = target_user_id;
END;
$$;

-- 6d: deactivate_member
CREATE OR REPLACE FUNCTION deactivate_member(target_user_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_company_id UUID;
  v_target_company_id UUID;
  v_admin_count INTEGER;
BEGIN
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Not an approved admin';
  END IF;

  v_company_id := get_my_company_id();
  IF v_company_id IS NULL THEN RAISE EXCEPTION 'No company'; END IF;

  SELECT company_id INTO v_target_company_id FROM user_profiles WHERE id = target_user_id;
  IF v_target_company_id != v_company_id THEN RAISE EXCEPTION 'User not in your company'; END IF;

  -- Last-admin guard
  IF (SELECT role FROM user_profiles WHERE id = target_user_id) = 'admin' THEN
    SELECT count(*) INTO v_admin_count FROM user_profiles
      WHERE company_id = v_company_id AND role = 'admin' AND status = 'approved';
    IF v_admin_count <= 1 THEN RAISE EXCEPTION 'Cannot deactivate last admin'; END IF;
  END IF;

  UPDATE user_profiles
  SET status = 'deactivated', updated_at = now()
  WHERE id = target_user_id;
END;
$$;

-- 6e: reactivate_member
CREATE OR REPLACE FUNCTION reactivate_member(target_user_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_company_id UUID;
  v_target_company_id UUID;
BEGIN
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Not an approved admin';
  END IF;

  v_company_id := get_my_company_id();
  IF v_company_id IS NULL THEN RAISE EXCEPTION 'No company'; END IF;

  SELECT company_id INTO v_target_company_id FROM user_profiles WHERE id = target_user_id;
  IF v_target_company_id != v_company_id THEN RAISE EXCEPTION 'User not in your company'; END IF;

  UPDATE user_profiles
  SET status = 'approved', updated_at = now()
  WHERE id = target_user_id;
END;
$$;

-- 6f: promote_to_admin
CREATE OR REPLACE FUNCTION promote_to_admin(target_user_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_company_id UUID;
  v_target_company_id UUID;
  v_target_status TEXT;
BEGIN
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Not an approved admin';
  END IF;

  v_company_id := get_my_company_id();
  IF v_company_id IS NULL THEN RAISE EXCEPTION 'No company'; END IF;

  SELECT company_id, status INTO v_target_company_id, v_target_status
    FROM user_profiles WHERE id = target_user_id;
  IF v_target_company_id != v_company_id THEN RAISE EXCEPTION 'User not in your company'; END IF;
  IF v_target_status != 'approved' THEN RAISE EXCEPTION 'User must be approved first'; END IF;

  UPDATE user_profiles
  SET role = 'admin', updated_at = now()
  WHERE id = target_user_id;
END;
$$;

-- ============================================================================
-- PART 7: NEW-6 + ADV-24 — lock_created_by() trigger on UPDATE
-- ============================================================================
-- This is a SEPARATE function from the existing enforce_created_by() (INSERT).
-- lock_created_by() fires BEFORE UPDATE to prevent created_by_user_id erasure.
-- COALESCE logic: preserves original; allows first-time stamping on legacy
-- records (NULL); prevents erasure to NULL.

CREATE OR REPLACE FUNCTION lock_created_by()
RETURNS TRIGGER AS $$
BEGIN
  NEW.created_by_user_id = COALESCE(OLD.created_by_user_id, NEW.created_by_user_id, auth.uid());
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Apply BEFORE UPDATE triggers on all 16 synced data tables
CREATE TRIGGER lock_created_by_projects
  BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_locations
  BEFORE UPDATE ON locations FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_contractors
  BEFORE UPDATE ON contractors FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_equipment
  BEFORE UPDATE ON equipment FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_bid_items
  BEFORE UPDATE ON bid_items FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_personnel_types
  BEFORE UPDATE ON personnel_types FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_daily_entries
  BEFORE UPDATE ON daily_entries FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_photos
  BEFORE UPDATE ON photos FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_entry_equipment
  BEFORE UPDATE ON entry_equipment FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_entry_quantities
  BEFORE UPDATE ON entry_quantities FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_entry_contractors
  BEFORE UPDATE ON entry_contractors FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_entry_personnel_counts
  BEFORE UPDATE ON entry_personnel_counts FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_inspector_forms
  BEFORE UPDATE ON inspector_forms FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_form_responses
  BEFORE UPDATE ON form_responses FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_todo_items
  BEFORE UPDATE ON todo_items FOR EACH ROW EXECUTE FUNCTION lock_created_by();
CREATE TRIGGER lock_created_by_calculation_history
  BEFORE UPDATE ON calculation_history FOR EACH ROW EXECUTE FUNCTION lock_created_by();

-- ============================================================================
-- PART 8: ADV-2 — enforce_insert_updated_at() anti-spoofing trigger
-- ============================================================================
-- Forces updated_at = NOW() on INSERT so clients cannot send stale timestamps.

CREATE OR REPLACE FUNCTION enforce_insert_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Apply BEFORE INSERT triggers on all 16 synced data tables
CREATE TRIGGER enforce_insert_updated_at_projects
  BEFORE INSERT ON projects FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_locations
  BEFORE INSERT ON locations FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_contractors
  BEFORE INSERT ON contractors FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_equipment
  BEFORE INSERT ON equipment FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_bid_items
  BEFORE INSERT ON bid_items FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_personnel_types
  BEFORE INSERT ON personnel_types FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_daily_entries
  BEFORE INSERT ON daily_entries FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_photos
  BEFORE INSERT ON photos FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_entry_equipment
  BEFORE INSERT ON entry_equipment FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_entry_quantities
  BEFORE INSERT ON entry_quantities FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_entry_contractors
  BEFORE INSERT ON entry_contractors FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_entry_personnel_counts
  BEFORE INSERT ON entry_personnel_counts FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_inspector_forms
  BEFORE INSERT ON inspector_forms FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_form_responses
  BEFORE INSERT ON form_responses FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_todo_items
  BEFORE INSERT ON todo_items FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();
CREATE TRIGGER enforce_insert_updated_at_calculation_history
  BEFORE INSERT ON calculation_history FOR EACH ROW EXECUTE FUNCTION enforce_insert_updated_at();

-- ============================================================================
-- PART 9: ADV-15 — Server-side stamp_updated_by trigger for daily_entries
-- ============================================================================

CREATE OR REPLACE FUNCTION stamp_updated_by()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_TABLE_NAME = 'daily_entries' THEN
    NEW.updated_by_user_id = auth.uid();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

DROP TRIGGER IF EXISTS stamp_updated_by_daily_entries ON daily_entries;
CREATE TRIGGER stamp_updated_by_daily_entries
  BEFORE UPDATE ON daily_entries FOR EACH ROW EXECUTE FUNCTION stamp_updated_by();

-- ============================================================================
-- PART 10: ADV-22 + ADV-23 — get_table_integrity RPC with id_checksum
-- ============================================================================
-- NOTE: This RPC uses `deleted_at IS NULL` on ALL tables. GAP-9 (PART 1 above)
-- must have already added deleted_at to inspector_forms before this works.

CREATE OR REPLACE FUNCTION get_table_integrity(p_table_name TEXT)
RETURNS TABLE (
  row_count BIGINT,
  max_updated_at TIMESTAMPTZ,
  id_checksum BIGINT
) AS $$
DECLARE
  v_company_id UUID;
  v_sql TEXT;
BEGIN
  v_company_id := get_my_company_id();
  IF v_company_id IS NULL THEN
    RAISE EXCEPTION 'No company context';
  END IF;

  -- Validate table name against allowlist to prevent SQL injection
  IF p_table_name NOT IN (
    'projects', 'locations', 'contractors', 'equipment', 'bid_items',
    'personnel_types', 'daily_entries', 'photos', 'entry_equipment',
    'entry_quantities', 'entry_contractors', 'entry_personnel_counts',
    'inspector_forms', 'form_responses', 'todo_items', 'calculation_history'
  ) THEN
    RAISE EXCEPTION 'Invalid table name: %', p_table_name;
  END IF;

  IF p_table_name = 'projects' THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE company_id = %L AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSIF p_table_name IN ('locations', 'contractors', 'bid_items', 'personnel_types', 'daily_entries',
                          'inspector_forms', 'todo_items', 'calculation_history') THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSIF p_table_name = 'equipment' THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE contractor_id IN (SELECT id FROM contractors WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L)) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSIF p_table_name = 'photos' THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE entry_id IN (SELECT id FROM daily_entries WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L)) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSIF p_table_name = 'form_responses' THEN
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  ELSE
    -- entry_equipment, entry_quantities, entry_contractors, entry_personnel_counts
    v_sql := format(
      'SELECT COUNT(*)::BIGINT, MAX(updated_at), SUM(hashtext(id::text))::BIGINT FROM %I WHERE entry_id IN (SELECT id FROM daily_entries WHERE project_id IN (SELECT id FROM projects WHERE company_id = %L)) AND deleted_at IS NULL',
      p_table_name, v_company_id
    );
  END IF;

  RETURN QUERY EXECUTE v_sql;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE SET search_path = public;

-- ============================================================================
-- PART 11: Decision 12 — Profile expansion: add columns to user_profiles
-- ============================================================================

ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS agency TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS initials TEXT;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS gauge_number TEXT;

-- ============================================================================
-- PART 12: Decision 12 — New user_certifications table
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_certifications (
  id TEXT PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
  cert_type TEXT NOT NULL,
  cert_number TEXT NOT NULL,
  expiry_date DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, cert_type)
);

CREATE TRIGGER update_user_certifications_updated_at
  BEFORE UPDATE ON user_certifications
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS policies for user_certifications
-- [CORRECTION] The original plan omitted RLS policies. Adding them here
-- following the same pattern as user_profiles.
ALTER TABLE user_certifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_certifications_select" ON user_certifications
  FOR SELECT TO authenticated
  USING (user_id IN (
    SELECT id FROM user_profiles WHERE company_id = get_my_company_id()
  ));

CREATE POLICY "user_certifications_insert" ON user_certifications
  FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid() AND NOT is_viewer());

CREATE POLICY "user_certifications_update" ON user_certifications
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid() AND NOT is_viewer())
  WITH CHECK (user_id = auth.uid() AND NOT is_viewer());

CREATE POLICY "user_certifications_delete" ON user_certifications
  FOR DELETE TO authenticated
  USING (user_id = auth.uid() AND NOT is_viewer());

-- ============================================================================
-- PART 13: Decision 12 — Migrate cert_number from user_profiles to user_certifications
-- ============================================================================

INSERT INTO user_certifications (id, user_id, cert_type, cert_number, created_at, updated_at)
SELECT gen_random_uuid()::text, id, 'primary', cert_number, created_at, updated_at
FROM user_profiles
WHERE cert_number IS NOT NULL
ON CONFLICT (user_id, cert_type) DO NOTHING;

-- NOTE: Do NOT drop cert_number column from user_profiles yet.
-- It remains as a read-only fallback until the app migration is verified.
-- A future migration will: ALTER TABLE user_profiles DROP COLUMN IF EXISTS cert_number;

-- ============================================================================
-- PART 14: Also fix enforce_created_by() to add SET search_path = public
-- ============================================================================
-- The existing enforce_created_by() (INSERT trigger) lacks SET search_path.
-- Recreate it with the security fix. All existing triggers referencing this
-- function continue to work because CREATE OR REPLACE preserves trigger bindings.

CREATE OR REPLACE FUNCTION enforce_created_by()
RETURNS TRIGGER AS $$
BEGIN
  NEW.created_by_user_id = auth.uid();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
```

---

## Step 2: Supabase Config -- secure_password_change

**File**: `supabase/config.toml`
**Action**: Modify
**Depends on**: Nothing

### 2.1 Change secure_password_change

At line 207, change:

**Before**:
```toml
secure_password_change = false
```

**After**:
```toml
secure_password_change = true
```

This is GAP-19. Users will need to reauthenticate (or have logged in recently) before changing their password.

---

## Step 3: UserProfile Model Expansion

**File**: `lib/features/auth/data/models/user_profile.dart`
**Action**: Modify
**Depends on**: Nothing (can be done in parallel with Steps 1-2)

### 3.1 Add 4 new fields to the class

Add after the existing `phone` field (line 12-13):

```dart
  final String? email;
  final String? agency;
  final String? initials;
  final String? gaugeNumber;
```

The full field list becomes:
```dart
  final String userId;
  final String? displayName;
  final String? certNumber;
  final String? phone;
  final String? email;       // NEW
  final String? agency;      // NEW
  final String? initials;    // NEW
  final String? gaugeNumber; // NEW
  final String? position;
  final String? companyId;
  final UserRole role;
  final MembershipStatus status;
  final DateTime? lastSyncedAt;
  final DateTime createdAt;
  final DateTime updatedAt;
```

### 3.2 Update the constructor

Add the 4 new optional parameters:

```dart
  UserProfile({
    String? userId,
    this.displayName,
    this.certNumber,
    this.phone,
    this.email,        // NEW
    this.agency,       // NEW
    this.initials,     // NEW
    this.gaugeNumber,  // NEW
    this.position,
    this.companyId,
    this.role = UserRole.inspector,
    this.status = MembershipStatus.pending,
    this.lastSyncedAt,
    DateTime? createdAt,
    DateTime? updatedAt,
  })  : userId = userId ?? const Uuid().v4(),
        createdAt = createdAt ?? DateTime.now(),
        updatedAt = updatedAt ?? DateTime.now();
```

### 3.3 Update copyWith()

Add the 4 new parameters:

```dart
  UserProfile copyWith({
    String? userId,
    String? displayName,
    String? certNumber,
    String? phone,
    String? email,        // NEW
    String? agency,       // NEW
    String? initials,     // NEW
    String? gaugeNumber,  // NEW
    String? position,
    String? companyId,
    UserRole? role,
    MembershipStatus? status,
    DateTime? lastSyncedAt,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return UserProfile(
      userId: userId ?? this.userId,
      displayName: displayName ?? this.displayName,
      certNumber: certNumber ?? this.certNumber,
      phone: phone ?? this.phone,
      email: email ?? this.email,            // NEW
      agency: agency ?? this.agency,          // NEW
      initials: initials ?? this.initials,    // NEW
      gaugeNumber: gaugeNumber ?? this.gaugeNumber, // NEW
      position: position ?? this.position,
      companyId: companyId ?? this.companyId,
      role: role ?? this.role,
      status: status ?? this.status,
      lastSyncedAt: lastSyncedAt ?? this.lastSyncedAt,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
```

### 3.4 Update toMap()

Add the 4 new fields to the map (after `phone`):

```dart
      if (email != null) 'email': email,
      if (agency != null) 'agency': agency,
      if (initials != null) 'initials': initials,
      if (gaugeNumber != null) 'gauge_number': gaugeNumber,
```

### 3.5 Update fromMap()

Add the 4 new fields to the factory:

```dart
      email: map['email'] as String?,
      agency: map['agency'] as String?,
      initials: map['initials'] as String?,
      gaugeNumber: map['gauge_number'] as String?,
```

### 3.6 Update fromJson()

Add the 4 new fields to the factory (same as fromMap):

```dart
      email: json['email'] as String?,
      agency: json['agency'] as String?,
      initials: json['initials'] as String?,
      gaugeNumber: json['gauge_number'] as String?,
```

### 3.7 Update toUpsertJson()

Add the new user-editable fields (email is read-only from auth, so omit it):

```dart
      if (agency != null) 'agency': agency,
      if (initials != null) 'initials': initials,
      if (gaugeNumber != null) 'gauge_number': gaugeNumber,
```

### 3.8 Update toJson()

Add the 4 new fields:

```dart
      if (email != null) 'email': email,
      if (agency != null) 'agency': agency,
      if (initials != null) 'initials': initials,
      if (gaugeNumber != null) 'gauge_number': gaugeNumber,
```

### 3.9 Add convenience getter for effective initials

Add after the `isViewer` getter:

```dart
  /// Get effective initials: use stored initials if set, otherwise derive from displayName.
  String get effectiveInitials {
    if (initials != null && initials!.isNotEmpty) {
      return initials!;
    }
    return _generateInitialsFromName(displayName ?? '');
  }

  static String _generateInitialsFromName(String name) {
    if (name.trim().isEmpty) return '';
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.length >= 2) {
      return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
    }
    return parts.first.substring(0, parts.first.length.clamp(0, 2)).toUpperCase();
  }
```

Note: The `generateInitialsFromName` function already exists in `lib/shared/utils/string_utils.dart`. You may import and use that instead of duplicating. Check the import:
```dart
import 'package:construction_inspector/shared/utils/string_utils.dart';
```
Then use `generateInitialsFromName(displayName ?? '')` directly.

---

## Step 4: SQLite v30 Migration

**File**: `lib/core/database/database_service.dart`
**Action**: Modify
**Depends on**: Step 3 (UserProfile model must have new fields for fresh-install schema)

Also modify:
- `lib/core/database/schema/core_tables.dart` (fresh-install schema)
- `lib/core/database/schema/sync_tables.dart` (new tables for fresh installs)

### 4.1 Bump database version

**File**: `lib/core/database/database_service.dart`

Change line 54 from:
```dart
      version: 29,
```
to:
```dart
      version: 30,
```

Also change line 90 (the in-memory database version):
```dart
      version: 30,
```

### 4.2 Update fresh-install schema: core_tables.dart

**File**: `lib/core/database/schema/core_tables.dart`

Update the `createUserProfilesTable` constant to include the 4 new columns. Change the table definition (lines 60-74) to:

```dart
  static const String createUserProfilesTable = '''
    CREATE TABLE IF NOT EXISTS user_profiles (
      id TEXT PRIMARY KEY,
      company_id TEXT,
      role TEXT NOT NULL DEFAULT 'inspector',
      status TEXT NOT NULL DEFAULT 'pending',
      display_name TEXT,
      cert_number TEXT,
      phone TEXT,
      email TEXT,
      agency TEXT,
      initials TEXT,
      gauge_number TEXT,
      position TEXT,
      last_synced_at TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
    )
  ''';
```

### 4.3 Update fresh-install schema: sync_tables.dart

**File**: `lib/core/database/schema/sync_tables.dart`

Add the new tables to SyncTables class. Add after the existing `createDeletionNotificationsTable`:

```dart
  /// Sync control table -- key-value store for sync state flags
  static const String createSyncControlTable = '''
    CREATE TABLE IF NOT EXISTS sync_control (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )
  ''';

  /// Change log table -- tracks local changes for push sync
  static const String createChangeLogTable = '''
    CREATE TABLE IF NOT EXISTS change_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      table_name TEXT NOT NULL,
      record_id TEXT NOT NULL,
      operation TEXT NOT NULL,
      changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      processed INTEGER NOT NULL DEFAULT 0,
      error_message TEXT,
      retry_count INTEGER NOT NULL DEFAULT 0,
      metadata TEXT
    )
  ''';

  /// Conflict log table -- records LWW conflict resolutions
  static const String createConflictLogTable = '''
    CREATE TABLE IF NOT EXISTS conflict_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      table_name TEXT NOT NULL,
      record_id TEXT NOT NULL,
      winner TEXT NOT NULL,
      lost_data TEXT NOT NULL,
      detected_at TEXT NOT NULL,
      dismissed_at TEXT,
      expires_at TEXT NOT NULL
    )
  ''';

  /// Sync lock table -- single-row mutex for sync operations
  static const String createSyncLockTable = '''
    CREATE TABLE IF NOT EXISTS sync_lock (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      locked_at TEXT NOT NULL,
      locked_by TEXT NOT NULL
    )
  ''';

  /// Synced projects table -- tracks which projects are synced to this device
  static const String createSyncedProjectsTable = '''
    CREATE TABLE IF NOT EXISTS synced_projects (
      project_id TEXT PRIMARY KEY,
      synced_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
    )
  ''';

  /// User certifications table -- mirrors Supabase user_certifications
  static const String createUserCertificationsTable = '''
    CREATE TABLE IF NOT EXISTS user_certifications (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      cert_type TEXT NOT NULL,
      cert_number TEXT NOT NULL,
      expiry_date TEXT,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
      UNIQUE(user_id, cert_type)
    )
  ''';
```

Also add the new indexes to the `indexes` list:

```dart
  static const List<String> indexes = [
    'CREATE INDEX idx_sync_queue_table ON sync_queue(table_name)',
    'CREATE INDEX idx_sync_queue_created ON sync_queue(created_at)',
    'CREATE INDEX idx_deletion_notifications_seen ON deletion_notifications(seen)',
    'CREATE INDEX idx_deletion_notifications_project ON deletion_notifications(project_id)',
    // New indexes for v30 tables
    'CREATE INDEX IF NOT EXISTS idx_change_log_unprocessed ON change_log(processed, table_name)',
    'CREATE INDEX IF NOT EXISTS idx_conflict_log_expires ON conflict_log(expires_at)',
  ];
```

### 4.4 Update _onCreate to create the new tables

**File**: `lib/core/database/database_service.dart`

Find the `_onCreate` method and add the new table creations after the existing sync tables. The exact location depends on where sync tables are created. Add:

```dart
    await db.execute(SyncTables.createSyncControlTable);
    await db.execute(SyncTables.createChangeLogTable);
    await db.execute(SyncTables.createConflictLogTable);
    await db.execute(SyncTables.createSyncLockTable);
    await db.execute(SyncTables.createSyncedProjectsTable);
    await db.execute(SyncTables.createUserCertificationsTable);
```

Also add the seed value for sync_control:
```dart
    await db.execute("INSERT OR IGNORE INTO sync_control (key, value) VALUES ('pulling', '0')");
```

### 4.5 Add v30 migration block

**File**: `lib/core/database/database_service.dart`

Add after the v29 migration block (after line 1153). Insert before the closing `}` of `_onUpgrade`:

```dart
    if (oldVersion < 30) {
      // Decision 1: sync_control table
      await db.execute('''
        CREATE TABLE IF NOT EXISTS sync_control (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        )
      ''');
      await db.execute("INSERT OR IGNORE INTO sync_control (key, value) VALUES ('pulling', '0')");

      // Change log table (with metadata column)
      await db.execute('''
        CREATE TABLE IF NOT EXISTS change_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          table_name TEXT NOT NULL,
          record_id TEXT NOT NULL,
          operation TEXT NOT NULL,
          changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
          processed INTEGER NOT NULL DEFAULT 0,
          error_message TEXT,
          retry_count INTEGER NOT NULL DEFAULT 0,
          metadata TEXT
        )
      ''');
      await db.execute(
        'CREATE INDEX IF NOT EXISTS idx_change_log_unprocessed ON change_log(processed, table_name)',
      );

      // Conflict log table (with expires_at column)
      await db.execute('''
        CREATE TABLE IF NOT EXISTS conflict_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          table_name TEXT NOT NULL,
          record_id TEXT NOT NULL,
          winner TEXT NOT NULL,
          lost_data TEXT NOT NULL,
          detected_at TEXT NOT NULL,
          dismissed_at TEXT,
          expires_at TEXT NOT NULL
        )
      ''');
      await db.execute(
        'CREATE INDEX IF NOT EXISTS idx_conflict_log_expires ON conflict_log(expires_at)',
      );

      // Decision 2: sync_lock table
      await db.execute('''
        CREATE TABLE IF NOT EXISTS sync_lock (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          locked_at TEXT NOT NULL,
          locked_by TEXT NOT NULL
        )
      ''');

      // Decision 4: synced_projects table
      await db.execute('''
        CREATE TABLE IF NOT EXISTS synced_projects (
          project_id TEXT PRIMARY KEY,
          synced_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now'))
        )
      ''');

      // Decision 12: user_certifications table
      await db.execute('''
        CREATE TABLE IF NOT EXISTS user_certifications (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          cert_type TEXT NOT NULL,
          cert_number TEXT NOT NULL,
          expiry_date TEXT,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now')),
          UNIQUE(user_id, cert_type)
        )
      ''');

      // Decision 12: Profile expansion columns on user_profiles
      // [CORRECTION] SQLite does NOT support ALTER TABLE ... ADD COLUMN IF NOT EXISTS.
      // Must use the _addColumnIfNotExists() helper (defined at line 225).
      await _addColumnIfNotExists(db, 'user_profiles', 'email', 'TEXT');
      await _addColumnIfNotExists(db, 'user_profiles', 'agency', 'TEXT');
      await _addColumnIfNotExists(db, 'user_profiles', 'initials', 'TEXT');
      await _addColumnIfNotExists(db, 'user_profiles', 'gauge_number', 'TEXT');

      // UNIQUE index on projects(company_id, project_number)
      await db.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_company_number ON projects(company_id, project_number)',
      );
    }
```

---

## Step 5: PreferencesService Dead Code Removal

**File**: `lib/shared/services/preferences_service.dart`
**Action**: Modify
**Depends on**: Step 6 must be done first (consumers must stop reading these before we remove them)

**IMPORTANT**: Steps 5 and 6 are interrelated. Do Step 6 (consumer migration) first to remove all callers, THEN do Step 5 (dead code removal). Otherwise the code won't compile.

### 5.1 Remove dead preference key constants

Remove these lines:
- Line 20: `static const String keyInspectorAgency = 'inspector_agency';`
- Line 25: `static const String keyShowOnlyManualFields = 'show_only_manual_fields';`
- Line 26: `static const String keyLastRoute = 'last_route_location';`
- Line 29: `static const String _prefillKeyPrefix = 'prefill_project_form';`
- Line 30: `static const String _prefillPromptedPrefix = 'prefill_prompted';`

### 5.2 Remove dead toggle key constants

Remove these lines:
- Line 21: `static const String keyAutoFetchWeather = 'auto_fetch_weather';`
- Line 22: `static const String keyAutoSyncWifi = 'auto_sync_wifi';`
- Line 23: `static const String keyUseLastValues = 'use_last_values';`
- Line 24: `static const String keyAutoFillEnabled = 'auto_fill_enabled';`

### 5.3 Remove dead methods

Remove the following method blocks entirely:

1. **inspectorAgency getter/setter** (lines 128-139):
   - `String? get inspectorAgency`
   - `Future<void> setInspectorAgency(String value)`

2. **autoFetchWeather getter/setter** (lines 146-156):
   - `bool get autoFetchWeather`
   - `Future<void> setAutoFetchWeather(bool value)`

3. **autoSyncWifi getter/setter** (lines 158-169):
   - `bool get autoSyncWifi`
   - `Future<void> setAutoSyncWifi(bool value)`

4. **useLastValues getter/setter** (lines 171-182):
   - `bool get useLastValues`
   - `Future<void> setUseLastValues(bool value)`

5. **autoFillEnabled getter/setter** (lines 184-195):
   - `bool get autoFillEnabled`
   - `Future<void> setAutoFillEnabled(bool value)`

6. **showOnlyManualFields getter/setter** (lines 197-208):
   - `bool? get showOnlyManualFields`
   - `Future<void> setShowOnlyManualFields(bool value)`

7. **lastRoute getter/setter/clear** (lines 210-225):
   - `String? get lastRoute`
   - `Future<void> setLastRoute(String location)`
   - `Future<void> clearLastRoute()`

8. **prefill helpers and methods** (lines 268-309):
   - `String _prefillKey(String projectId, String formId)`
   - `String _prefillPromptedKey(String projectId, String formId)`
   - `Map<String, dynamic>? getProjectFormPrefill(String projectId, String formId)`
   - `Future<void> setProjectFormPrefill(...)`
   - `bool getProjectFormPrefillPrompted(String projectId, String formId)`
   - `Future<void> setProjectFormPrefillPrompted(...)`

### 5.4 Update inspectorProfile getter

The current `inspectorProfile` getter (line 316-322) references `inspectorAgency` which was removed. Update it:

**Before** (line 316-322):
```dart
  Map<String, String?> get inspectorProfile => {
        'name': inspectorName,
        'initials': effectiveInitials,
        'phone': inspectorPhone,
        'cert_number': inspectorCertNumber,
        'agency': inspectorAgency,
      };
```

**After**:
```dart
  Map<String, String?> get inspectorProfile => {
        'name': inspectorName,
        'initials': effectiveInitials,
        'phone': inspectorPhone,
        'cert_number': inspectorCertNumber,
      };
```

### 5.5 Add the `remove` method if not present

The PII cleanup in Step 7 calls `prefs.remove(key)`. Verify that `PreferencesService` has a `remove` method. If not, add one:

```dart
  /// Remove a single preference key.
  Future<void> remove(String key) async {
    _ensureInitialized();
    await _prefs!.remove(key);
  }
```

---

## Step 6: Consumer Migration (PreferencesService -> AuthProvider.userProfile)

**Action**: Modify multiple files
**Depends on**: Step 3 (UserProfile model must have new fields)

### 6.1 mdot_hub_screen.dart

**File**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart`

At the `_hydrate` method (around line 150-165), change the auto-fill data source from PreferencesService to AuthProvider.

**Before** (lines 153-164):
```dart
      final prefs = context.read<PreferencesService>();
      final auto = _autoFillService.buildHeaderData(
        date: DateTime.now().toIso8601String().split('T').first,
        controlSectionId: project?.controlSectionId,
        jobNumber: project?.projectNumber,
        routeStreet: project?.routeStreet,
        gaugeNumber: prefs.gaugeNumber,
        inspector: prefs.inspectorName,
        certNumber: prefs.inspectorCertNumber,
        phone: prefs.inspectorPhone,
        constructionEng: project?.constructionEng,
      );
```

**After**:
```dart
      final userProfile = context.read<AuthProvider>().userProfile;
      final auto = _autoFillService.buildHeaderData(
        date: DateTime.now().toIso8601String().split('T').first,
        controlSectionId: project?.controlSectionId,
        jobNumber: project?.projectNumber,
        routeStreet: project?.routeStreet,
        gaugeNumber: userProfile?.gaugeNumber,
        inspector: userProfile?.displayName,
        certNumber: userProfile?.certNumber,
        phone: userProfile?.phone,
        constructionEng: project?.constructionEng,
      );
```

Also update the imports: ensure `AuthProvider` is imported. Remove the `PreferencesService` import if it is no longer used in this file.

### 6.2 form_viewer_screen.dart

**File**: `lib/features/forms/presentation/screens/form_viewer_screen.dart`

At the `_applyAutoFillIfNeeded` method (around line 75-91):

**Before** (lines 78-90):
```dart
    final prefs = context.read<PreferencesService>();
    _header = _autoFillService.buildHeaderData(
      projectNumber: project?.projectNumber,
      projectName: project?.name,
      date: DateTime.now().toIso8601String().split('T').first,
      inspector: prefs.inspectorName,
      controlSectionId: project?.controlSectionId,
      routeStreet: project?.routeStreet,
      constructionEng: project?.constructionEng,
      certNumber: prefs.inspectorCertNumber,
      phone: prefs.inspectorPhone,
      gaugeNumber: prefs.gaugeNumber,
    );
```

**After**:
```dart
    final userProfile = context.read<AuthProvider>().userProfile;
    _header = _autoFillService.buildHeaderData(
      projectNumber: project?.projectNumber,
      projectName: project?.name,
      date: DateTime.now().toIso8601String().split('T').first,
      inspector: userProfile?.displayName,
      controlSectionId: project?.controlSectionId,
      routeStreet: project?.routeStreet,
      constructionEng: project?.constructionEng,
      certNumber: userProfile?.certNumber,
      phone: userProfile?.phone,
      gaugeNumber: userProfile?.gaugeNumber,
    );
```

Update imports: add `AuthProvider`, remove `PreferencesService` if unused.

### 6.3 pdf_data_builder.dart

**File**: `lib/features/entries/presentation/controllers/pdf_data_builder.dart`

At lines 122-135, remove the SharedPreferences fallback and use AuthProvider instead.

**Before** (lines 122-135):
```dart
    // Get inspector name — prefer attribution repository when createdByUserId
    // is available; fall back to SharedPreferences for backward compat.
    String inspectorName;
    if (attributionRepository != null && entry.createdByUserId != null) {
      inspectorName = await attributionRepository.getDisplayName(entry.createdByUserId);
      // If attribution returned 'Unknown', fall back to SharedPreferences value.
      if (inspectorName == 'Unknown') {
        final prefs = await SharedPreferences.getInstance();
        inspectorName = prefs.getString('inspector_name') ?? 'Inspector';
      }
    } else {
      final prefs = await SharedPreferences.getInstance();
      inspectorName = prefs.getString('inspector_name') ?? 'Inspector';
    }
```

**After**:
```dart
    // Get inspector name — prefer attribution repository when createdByUserId
    // is available; fall back to AuthProvider.userProfile.displayName.
    String inspectorName;
    if (attributionRepository != null && entry.createdByUserId != null) {
      inspectorName = await attributionRepository.getDisplayName(entry.createdByUserId);
      if (inspectorName == 'Unknown') {
        inspectorName = userProfile?.displayName ?? 'Inspector';
      }
    } else {
      inspectorName = userProfile?.displayName ?? 'Inspector';
    }
```

This requires passing `userProfile` as a parameter to the build method. Check the method signature and add `UserProfile? userProfile` as a parameter. The caller must pass `context.read<AuthProvider>().userProfile`.

Remove the `import 'package:shared_preferences/shared_preferences.dart';` if it is no longer used.

### 6.4 entry_photos_section.dart

**File**: `lib/features/entries/presentation/widgets/entry_photos_section.dart`

At lines 87-88, replace SharedPreferences access with AuthProvider.

**Before** (lines 87-88):
```dart
    final prefs = await SharedPreferences.getInstance();
    final initials = prefs.getString('inspector_initials') ?? 'XX';
```

**After**:
```dart
    final authProvider = context.read<AuthProvider>();
    final initials = authProvider.userProfile?.effectiveInitials ?? 'XX';
```

This requires:
1. Adding `import 'package:provider/provider.dart';` if not present
2. Adding the AuthProvider import
3. Removing the `SharedPreferences` import if unused
4. The method using `context` -- if this is an async method without `BuildContext`, the `AuthProvider` must be captured before the `await`. Check the method to ensure `context` is accessible here. If the widget is a `StatefulWidget`, `context` is available via the state.

---

## Step 7: PII Cleanup from SharedPreferences

**File**: `lib/shared/services/preferences_service.dart` (add method)
**File**: `lib/main.dart` or app initialization code (call it once)
**Action**: Modify
**Depends on**: Step 6 (all consumers must be migrated before deleting PII)

### 7.1 Add cleanup method to PreferencesService

Add this method to the `PreferencesService` class:

```dart
  /// One-time cleanup of legacy PII keys from SharedPreferences.
  /// Called once after the Settings redesign migration.
  /// Uses a pref key gate to ensure it only runs once.
  Future<void> cleanupLegacyPii() async {
    _ensureInitialized();
    const gateKey = 'pii_cleanup_v1_done';
    if (_prefs!.getBool(gateKey) == true) return;

    for (final key in [
      'inspector_name',
      'cert_number',            // keyInspectorCertNumber value
      'inspector_cert_number',  // alternate key used by some flows
      'phone',
      'inspector_phone',
      'inspector_initials',
      'inspector_agency',
      'gauge_number',
    ]) {
      await _prefs!.remove(key);
    }

    await _prefs!.setBool(gateKey, true);
  }
```

### 7.2 Call cleanup on app startup

**File**: `lib/main.dart` (or wherever `PreferencesService.initialize()` is called)

After the preferences service is initialized and the user is authenticated, call:

```dart
await preferencesService.cleanupLegacyPii();
```

Place this after the `preferencesService.initialize()` call, ideally gated behind authentication being confirmed (so we know user_profiles data is available as the source of truth).

---

## Step 8: Purge Handler in SyncService

**File**: `lib/services/sync_service.dart`
**Action**: Modify
**Depends on**: Nothing

### 8.1 Add purge case to _processSyncQueueItem

At the `_processSyncQueueItem` method (line 691-718), add a `case 'purge':` block.

**Before** (lines 699-717):
```dart
    switch (operation) {
      case 'insert':
      case 'update':
        // Get current local data and upsert to remote
        final localData = await db.query(
          tableName,
          where: 'id = ?',
          whereArgs: [recordId],
        );
        if (localData.isNotEmpty) {
          await _supabase!
              .from(tableName)
              .upsert(_convertForRemote(tableName, localData.first));
        }
        break;
      case 'delete':
        await _supabase!.from(tableName).delete().eq('id', recordId);
        break;
    }
```

**After**:
```dart
    switch (operation) {
      case 'insert':
      case 'update':
        // Get current local data and upsert to remote
        final localData = await db.query(
          tableName,
          where: 'id = ?',
          whereArgs: [recordId],
        );
        if (localData.isNotEmpty) {
          await _supabase!
              .from(tableName)
              .upsert(_convertForRemote(tableName, localData.first));
        }
        break;
      case 'delete':
        await _supabase!.from(tableName).delete().eq('id', recordId);
        break;
      case 'purge':
        // GAP-3: Hard-delete expired soft-deleted records on the server.
        // Uses sync_control gate to bypass triggers during purge.
        await _supabase!.from(tableName).delete().eq('id', recordId);
        // Also remove the local record if it still exists
        await db.delete(tableName, where: 'id = ?', whereArgs: [recordId]);
        break;
    }
```

---

## Step 9: Settings Screen Redesign

**File**: `lib/features/settings/presentation/screens/settings_screen.dart`
**Action**: Modify (full rewrite of the build method body)
**Depends on**: Steps 3, 4, 5, 6 (model expansion + consumer migration + dead code removal)

### 9.1 Remove dead state variables and methods

Remove these state variables (lines 23-26):
```dart
  bool _autoFetchWeather = true;
  bool _autoSyncWifi = true;
  bool _autoFillEnabled = true;
  bool _useLastValues = true;
```

Remove the `_loadSettings` method (lines 41-49).

Remove the 4 toggle methods (lines 51-73):
- `_toggleAutoFetchWeather`
- `_toggleAutoSyncWifi`
- `_toggleAutoFillEnabled`
- `_toggleUseLastValues`

Remove the `_loadSettings()` call from `initState` (line 33). Keep `_loadTrashCount()`.

### 9.2 Rewrite the build method with new section ordering

The new section ordering is:

**1. ACCOUNT** (was split across Profile + Account)
```
Profile summary (name, role, company -- read-only)
Edit Profile -> /edit-profile
Admin Dashboard -> /admin-dashboard (admin only)
Sign Out
```

**2. SYNC & DATA** (was split across Cloud Sync + Data)
```
SyncSection widget (existing -- shows sync status, sync now button)
Trash -> /settings/trash (with badge count)
Clear Cached Exports
```

**3. FORM SETTINGS** (new section -- replaces Form Auto-Fill and pulls from PDF Export)
```
Gauge Number (editable text field -- reads/writes AuthProvider.userProfile.gaugeNumber)
Initials (editable text field -- reads/writes AuthProvider.userProfile.initials)
PDF Template (display: read-only info from AppTerminology)
```

**4. APPEARANCE** (same as before + Auto-Load from Project)
```
ThemeSection widget (existing)
Auto-Load toggle (from ProjectSettingsProvider)
```

**5. ABOUT** (same, minus Help & Support stub)
```
Version
Licenses
```

### 9.3 Exact widgets to REMOVE from the build method

| Widget/Tile | Current Location | Reason |
|-------------|-----------------|--------|
| `SectionHeader('Form Auto-Fill')` + both SwitchListTiles | lines 134-155 | Dead toggles |
| `SectionHeader('Project')` + Auto-Load toggle | lines 157-174 | Moved to APPEARANCE |
| `SectionHeader('Cloud Sync')` + Auto-Sync WiFi toggle | lines 213-227 | Dead toggle; SyncSection moves to SYNC & DATA |
| `SectionHeader('PDF Export')` + Company Template tile + Default Signature Name tile | lines 229-250 | Company Template -> Form Settings read-only; Signature Name is duplicate |
| `SectionHeader('Weather')` + Weather API tile + Auto-fetch Weather toggle | lines 253-273 | Dead toggle + unactionable display |
| Backup Data tile | lines 281-291 | Dead stub |
| Restore Data tile | lines 293-303 | Dead stub |
| Help & Support tile | lines 382-391 | Dead stub |

### 9.4 Exact widgets to ADD

1. **FORM SETTINGS section** with:
   - Gauge Number editable `ListTile` with trailing edit icon. On tap, show a dialog to edit `AuthProvider.userProfile.gaugeNumber`, then save via profile update.
   - Initials editable `ListTile`. Same pattern.
   - PDF Template read-only `ListTile` showing `AppTerminology.pdfTemplateDescription`.

2. **Auto-Load toggle** moved into the APPEARANCE section (after ThemeSection).

### 9.5 New section ordering skeleton

```dart
body: ListView(
  children: [
    // 1. ACCOUNT
    SectionHeader(title: 'Account'),
    // Profile summary: name, role, company (read-only) -- same Consumer<AuthProvider> as current Profile section
    // Edit Profile tile
    // Admin Dashboard tile (admin only)
    // Sign Out tile
    const Divider(),

    // 2. SYNC & DATA
    SectionHeader(title: 'Sync & Data'),
    const SyncSection(),
    // Trash tile (with badge count) -- moved from Data section
    // Clear Cached Exports tile -- moved from Data section
    const Divider(),

    // 3. FORM SETTINGS
    SectionHeader(title: 'Form Settings'),
    // Gauge Number tile (editable)
    // Initials tile (editable)
    // PDF Template tile (read-only)
    const Divider(),

    // 4. APPEARANCE
    SectionHeader(title: 'Appearance'),
    const ThemeSection(),
    // Auto-Load toggle (moved from Project section)
    const Divider(),

    // 5. ABOUT
    SectionHeader(title: 'About'),
    // Version tile
    // Licenses tile
    const SizedBox(height: 32),
  ],
),
```

### 9.6 Gauge Number and Initials editable tiles

For the Gauge Number and Initials tiles in FORM SETTINGS, use inline editing. Example pattern for Gauge Number:

```dart
Consumer<AuthProvider>(
  builder: (context, authProvider, _) {
    final profile = authProvider.userProfile;
    return ListTile(
      leading: const Icon(Icons.speed),
      title: const Text('Gauge Number'),
      subtitle: Text(profile?.gaugeNumber ?? 'Not set'),
      trailing: const Icon(Icons.edit, size: 18),
      onTap: () => _showEditDialog(
        context,
        title: 'Gauge Number',
        currentValue: profile?.gaugeNumber ?? '',
        onSave: (value) async {
          await authProvider.updateProfile(
            profile!.copyWith(gaugeNumber: value),
          );
        },
      ),
    );
  },
),
```

Implement a reusable `_showEditDialog` method:

```dart
Future<void> _showEditDialog(
  BuildContext context, {
  required String title,
  required String currentValue,
  required Future<void> Function(String) onSave,
}) async {
  final controller = TextEditingController(text: currentValue);
  final result = await showDialog<String>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text('Edit $title'),
      content: TextField(
        controller: controller,
        autofocus: true,
        decoration: InputDecoration(hintText: 'Enter $title'),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
        TextButton(
          onPressed: () => Navigator.pop(ctx, controller.text),
          child: const Text('Save'),
        ),
      ],
    ),
  );
  if (result != null && result != currentValue) {
    await onSave(result);
  }
}
```

Note: `authProvider.updateProfile()` must exist. If it does not, it needs to be added to `AuthProvider` to update the local user_profiles SQLite row and push to Supabase. Check the existing AuthProvider for an `updateProfile` method; if missing, add one that calls the user_profiles repository.

---

## Step 10: Delete Orphaned EditInspectorDialog Widget

**Depends on**: Step 9 (settings screen no longer references it)

### 10.1 Delete the widget file

**File to delete**: `lib/features/settings/presentation/widgets/edit_inspector_dialog.dart`

### 10.2 Remove the barrel export

**File**: `lib/features/settings/presentation/widgets/widgets.dart`

Remove line 4:
```dart
export 'edit_inspector_dialog.dart';
```

The file becomes:
```dart
export 'section_header.dart';
export 'theme_section.dart';
export 'sync_section.dart';
export 'sign_out_dialog.dart';
export 'clear_cache_dialog.dart';
export 'member_detail_sheet.dart';
```

### 10.3 Clean up testing keys

**File**: `lib/shared/testing_keys/testing_keys.dart` (or wherever settings testing keys are defined)

Search for and remove any testing keys related to `EditInspectorDialog`:
- `editInspectorNameDialog`
- `editInitialsDialog`
- Any other keys prefixed with `editInspector`

Also remove dead settings toggle testing keys:
- `settingsAutoFillToggle`
- `settingsUseLastValuesToggle`
- `settingsAutoSyncToggle`
- `settingsAutoWeatherToggle`
- `settingsAutoFillSection`

---

## Step 11: Verification Checklist

After all steps are complete, verify:

### 11.1 Compilation check

```
pwsh -Command "flutter analyze"
```

No errors should relate to removed preferences, missing fields, or import issues.

### 11.2 Supabase migration dry-run

Before applying the migration to production:
1. Apply to a staging/local Supabase instance first
2. Verify all 6 admin RPCs work with the `is_approved_admin()` check
3. Verify storage policies with a test upload: the path `entries/{companyId}/{entryId}/test.jpg` should only be accessible by users in that company
4. Verify `get_table_integrity('inspector_forms')` no longer fails (GAP-9 applied)
5. Verify `user_certifications` has proper RLS by testing SELECT/INSERT with different user contexts

### 11.3 SQLite migration test

1. Fresh install: all v30 tables are created correctly
2. Upgrade from v29: `_addColumnIfNotExists` runs for the 4 new user_profiles columns
3. Verify `user_profiles` table has `email`, `agency`, `initials`, `gauge_number` columns after migration

### 11.4 Consumer migration verification

Verify each consumer reads from `AuthProvider.userProfile` instead of `PreferencesService`:
- `mdot_hub_screen.dart` -- auto-fill uses `userProfile.gaugeNumber`, etc.
- `form_viewer_screen.dart` -- auto-fill uses `userProfile.displayName`, etc.
- `pdf_data_builder.dart` -- no more `SharedPreferences.getInstance()`
- `entry_photos_section.dart` -- uses `userProfile.effectiveInitials`

### 11.5 Settings screen visual check

Run the app and navigate to Settings. Verify:
- Sections appear in order: Account, Sync & Data, Form Settings, Appearance, About
- No dead toggles (Auto-Fill, Use Last Values, Auto-Sync WiFi, Auto-Fetch Weather)
- No dead stubs (Backup, Restore, Help & Support)
- No Weather API display, no Company Template in wrong section
- Gauge Number and Initials are editable
- PDF Template is read-only

### 11.6 PII cleanup verification

After first launch post-migration:
- Check SharedPreferences no longer contains: `inspector_name`, `cert_number`, `inspector_cert_number`, `phone`, `inspector_phone`, `inspector_initials`, `inspector_agency`, `gauge_number`
- Check `pii_cleanup_v1_done` is `true`

---

## Corrections Summary

| ID | Original Plan Claim | Correction |
|----|---------------------|------------|
| [CORRECTION-1] | ADV-33: `ALTER TABLE form_responses ALTER COLUMN form_id DROP NOT NULL` | Already applied in `20260222000000_catchup_v23.sql:247,253-266`. Included as idempotent no-op for safety. |
| [CORRECTION-2] | GAP-10: `ALTER TABLE entry_contractors ADD COLUMN updated_at` | Column already exists (added in `multi_tenant_foundation.sql:1048`). Only the UPDATE triggers are actually needed. ALTERs kept as idempotent no-ops. |
| [CORRECTION-3] | SQLite v30: `ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS email TEXT` | `IF NOT EXISTS` is invalid SQLite syntax. Must use `_addColumnIfNotExists()` helper at `database_service.dart:225`. |
| [CORRECTION-4] | user_certifications table: no RLS policies | Original plan omitted RLS. Added SELECT/INSERT/UPDATE/DELETE policies following same pattern as user_profiles. |
| [CORRECTION-5] | PII cleanup: "runs once on first launch" | No single-run mechanism was specified. Added `pii_cleanup_v1_done` pref key gate to ensure one-time execution. |
| [CORRECTION-6] | PreferencesService path | Actual path is `lib/shared/services/preferences_service.dart`, not in `lib/features/settings/`. |

---

## Files Modified/Created Summary

| Action | File Path |
|--------|-----------|
| CREATE | `supabase/migrations/20260305000000_schema_alignment_and_security.sql` |
| MODIFY | `supabase/config.toml` (line 207: secure_password_change = true) |
| MODIFY | `lib/features/auth/data/models/user_profile.dart` (4 new fields) |
| MODIFY | `lib/core/database/database_service.dart` (version bump + v30 migration) |
| MODIFY | `lib/core/database/schema/core_tables.dart` (user_profiles fresh schema) |
| MODIFY | `lib/core/database/schema/sync_tables.dart` (6 new table definitions) |
| MODIFY | `lib/shared/services/preferences_service.dart` (dead code removal + cleanup method) |
| MODIFY | `lib/features/forms/presentation/screens/mdot_hub_screen.dart` (consumer migration) |
| MODIFY | `lib/features/forms/presentation/screens/form_viewer_screen.dart` (consumer migration) |
| MODIFY | `lib/features/entries/presentation/controllers/pdf_data_builder.dart` (consumer migration) |
| MODIFY | `lib/features/entries/presentation/widgets/entry_photos_section.dart` (consumer migration) |
| MODIFY | `lib/services/sync_service.dart` (purge handler) |
| MODIFY | `lib/features/settings/presentation/screens/settings_screen.dart` (full redesign) |
| DELETE | `lib/features/settings/presentation/widgets/edit_inspector_dialog.dart` |
| MODIFY | `lib/features/settings/presentation/widgets/widgets.dart` (remove export) |
| MODIFY | Testing keys file (remove dead keys) |
| MODIFY | `lib/main.dart` (add PII cleanup call) |

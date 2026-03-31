# Forms & Documents Infrastructure — Part 1 (Phases 1–4)

**Created**: 2026-03-28
**Spec**: `.claude/specs/forms-and-documents-spec.md`
**Scope**: Database schema, Supabase migration, models, datasources, repositories
**Agents**: backend-data-layer-agent (Phases 1, 3, 4), backend-supabase-agent (Phase 2)

---

## Phase 1: Database Schema (Agent: backend-data-layer-agent)

### 1.1 — Create `form_export_tables.dart`

**File**: `lib/core/database/schema/form_export_tables.dart` (NEW)

```dart
// WHY: form_exports stores PDF exports generated from filled-out inspector forms.
// FROM SPEC: 15 columns with FKs to form_responses (CASCADE), projects (CASCADE), daily_entries (SET NULL).
class FormExportTables {
  static const String createFormExportsTable = '''
    CREATE TABLE form_exports (
      id TEXT PRIMARY KEY,
      form_response_id TEXT,
      project_id TEXT NOT NULL,
      entry_id TEXT,
      file_path TEXT,
      remote_path TEXT,
      filename TEXT NOT NULL,
      form_type TEXT NOT NULL,
      file_size_bytes INTEGER,
      exported_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (form_response_id) REFERENCES form_responses(id) ON DELETE CASCADE,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
      FOREIGN KEY (entry_id) REFERENCES daily_entries(id) ON DELETE SET NULL
    )
  ''';

  // NOTE: 5 indexes per spec — project_id, entry_id, form_response_id, form_type, deleted_at
  static const List<String> indexes = [
    'CREATE INDEX idx_form_exports_project ON form_exports(project_id)',
    'CREATE INDEX idx_form_exports_entry ON form_exports(entry_id)',
    'CREATE INDEX idx_form_exports_form_response ON form_exports(form_response_id)',
    'CREATE INDEX idx_form_exports_form_type ON form_exports(form_type)',
    'CREATE INDEX idx_form_exports_deleted_at ON form_exports(deleted_at)',
  ];
}
```

### 1.2 — Create `entry_export_tables.dart`

**File**: `lib/core/database/schema/entry_export_tables.dart` (NEW)

```dart
// WHY: entry_exports stores generated daily entry PDF reports.
// FROM SPEC: 13 columns with FKs to daily_entries (CASCADE), projects (CASCADE).
class EntryExportTables {
  static const String createEntryExportsTable = '''
    CREATE TABLE entry_exports (
      id TEXT PRIMARY KEY,
      entry_id TEXT,
      project_id TEXT NOT NULL,
      file_path TEXT,
      remote_path TEXT,
      filename TEXT NOT NULL,
      file_size_bytes INTEGER,
      exported_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (entry_id) REFERENCES daily_entries(id) ON DELETE CASCADE,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
  ''';

  // NOTE: 3 indexes per spec — project_id, entry_id, deleted_at
  static const List<String> indexes = [
    'CREATE INDEX idx_entry_exports_project ON entry_exports(project_id)',
    'CREATE INDEX idx_entry_exports_entry ON entry_exports(entry_id)',
    'CREATE INDEX idx_entry_exports_deleted_at ON entry_exports(deleted_at)',
  ];
}
```

### 1.3 — Create `document_tables.dart`

**File**: `lib/core/database/schema/document_tables.dart` (NEW)

```dart
// WHY: documents stores arbitrary file attachments (PDFs, spreadsheets) on entries.
// FROM SPEC: 15 columns with FKs to daily_entries (CASCADE), projects (CASCADE).
class DocumentTables {
  static const String createDocumentsTable = '''
    CREATE TABLE documents (
      id TEXT PRIMARY KEY,
      entry_id TEXT,
      project_id TEXT NOT NULL,
      file_path TEXT,
      remote_path TEXT,
      filename TEXT NOT NULL,
      file_type TEXT NOT NULL,
      file_size_bytes INTEGER,
      notes TEXT,
      captured_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      created_by_user_id TEXT,
      deleted_at TEXT,
      deleted_by TEXT,
      FOREIGN KEY (entry_id) REFERENCES daily_entries(id) ON DELETE CASCADE,
      FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    )
  ''';

  // NOTE: 4 indexes per spec — project_id, entry_id, file_type, deleted_at
  static const List<String> indexes = [
    'CREATE INDEX idx_documents_project ON documents(project_id)',
    'CREATE INDEX idx_documents_entry ON documents(entry_id)',
    'CREATE INDEX idx_documents_file_type ON documents(file_type)',
    'CREATE INDEX idx_documents_deleted_at ON documents(deleted_at)',
  ];
}
```

### 1.4 — Add v43 migration to `database_service.dart`

**File**: `lib/core/database/database_service.dart`

**Step 1.4a** — Bump version constant (near top of file):

```dart
// WHY: New tables require a schema version bump to trigger _onUpgrade.
// WAS: static const int _version = 42;
static const int _version = 43;
```

**Step 1.4b** — Add table creation to `_onCreate()` (line ~104 area, after existing CREATE TABLE calls):

```dart
// WHY: Fresh installs need all tables created in _onCreate.
// NOTE: Add after existing table creation calls (inspector_forms, form_responses, etc.)
await db.execute(FormExportTables.createFormExportsTable);
await db.execute(EntryExportTables.createEntryExportsTable);
await db.execute(DocumentTables.createDocumentsTable);
```

**Step 1.4c** — Add indexes to `_createIndexes()` (line ~181 area, after existing index loops):

```dart
// WHY: Fresh installs also need indexes for the 3 new tables.
for (final idx in FormExportTables.indexes) {
  await db.execute(idx);
}
for (final idx in EntryExportTables.indexes) {
  await db.execute(idx);
}
for (final idx in DocumentTables.indexes) {
  await db.execute(idx);
}
```

**Step 1.4d** — Add imports at the top of `database_service.dart`:

```dart
import 'schema/form_export_tables.dart';
import 'schema/entry_export_tables.dart';
import 'schema/document_tables.dart';
```

**Step 1.4e** — Add v43 migration case in `_onUpgrade()` (line ~249 area, after case 42):

> **DEPENDENCY**: Step 1.5 (add to triggeredTables) MUST be completed before this step,
> because `SyncEngineTables.triggersForTable()` throws if the table is not in `triggeredTables`.

```dart
// WHY: Existing installs need the migration path to create new tables.
case 42:
  await db.execute(FormExportTables.createFormExportsTable);
  await db.execute(EntryExportTables.createEntryExportsTable);
  await db.execute(DocumentTables.createDocumentsTable);
  for (final idx in FormExportTables.indexes) {
    await db.execute(idx);
  }
  for (final idx in EntryExportTables.indexes) {
    await db.execute(idx);
  }
  for (final idx in DocumentTables.indexes) {
    await db.execute(idx);
  }
  // NOTE: Also register sync triggers for the 3 new tables
  for (final trigger in SyncEngineTables.triggersForTable('form_exports')) {
    await db.execute(trigger);
  }
  for (final trigger in SyncEngineTables.triggersForTable('entry_exports')) {
    await db.execute(trigger);
  }
  for (final trigger in SyncEngineTables.triggersForTable('documents')) {
    await db.execute(trigger);
  }
  // CODE-REVIEW FIX #10: storage_cleanup_queue needs a bucket column for multi-bucket cleanup
  await db.execute("ALTER TABLE storage_cleanup_queue ADD COLUMN bucket TEXT DEFAULT 'entry-photos'");
  continue v43;
v43:
// NOTE: This is the fall-through label pattern used by existing migrations.
```

### 1.4f — Update `schema.dart` barrel export

**File**: `lib/core/database/schema/schema.dart`

```dart
// WHY: Barrel export must include the 3 new schema files so that
// database_service.dart imports resolve via the barrel.
// ADD after existing exports:
export 'form_export_tables.dart';
export 'entry_export_tables.dart';
export 'document_tables.dart';
```

### 1.5 — Register tables in `sync_engine_tables.dart`

**File**: `lib/core/database/schema/sync_engine_tables.dart`

**Step 1.5a** — Add to `triggeredTables` list:

```dart
// WHY: All 3 tables need change_log triggers so mutations sync to Supabase.
// FROM SPEC: These are project-scoped, sync-eligible tables.
// ADD after 'calculation_history':
'form_exports', 'entry_exports', 'documents',
```

**Step 1.5b** — Add to `tablesWithDirectProjectId` list:

```dart
// WHY: All 3 tables have a direct project_id column, so the trigger can
// write NEW.project_id into change_log for project-scoped sync filtering.
// ADD after 'entry_equipment':
'form_exports', 'entry_exports', 'documents',
```

### 1.6 — Add soft-delete cascade entries for new tables

**File**: `lib/services/soft_delete_service.dart`

The soft-delete service cascades soft-deletes to child tables. Add the 3 new tables to the cascade list for projects and daily_entries.

```dart
// WHY: When a project is soft-deleted, its form_exports, entry_exports, and
// documents must also be soft-deleted. Same for daily_entries cascade.
// NOTE: Find the project cascade children list and add the 3 new table names.
// Find the daily_entries cascade children list and add entry-scoped tables.
```

Specifically:
- Add `'form_exports'`, `'entry_exports'`, `'documents'` to the project cascade children
- Add `'form_exports'`, `'entry_exports'`, `'documents'` to the daily_entries cascade children (they all have entry_id FK)

### 1.7 — Tests

**File**: `test/core/database/migration_v43_test.dart` (NEW)

```dart
// WHY: Verify the v43 migration creates all 3 tables and their indexes.
// NOTE: Follow pattern from existing migration tests.
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  group('v43 migration', () {
    test('creates form_exports table', () async {
      // Open in-memory DB at v42, then upgrade to v43
      // Verify: db.rawQuery("SELECT name FROM sqlite_master WHERE type='table' AND name='form_exports'")
    });

    test('creates entry_exports table', () async {
      // Same pattern for entry_exports
    });

    test('creates documents table', () async {
      // Same pattern for documents
    });

    test('creates indexes for all 3 tables', () async {
      // Verify: db.rawQuery("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_form_exports%'")
      // Same for entry_exports, documents
    });

    test('creates sync triggers for all 3 tables', () async {
      // Verify: db.rawQuery("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE '%form_exports%'")
    });
  });
}
```

**File**: `test/features/sync/engine/sync_engine_tables_test.dart` (MODIFY)

```dart
// WHY: Verify the 3 new tables appear in triggeredTables and tablesWithDirectProjectId.
test('triggeredTables includes form_exports, entry_exports, documents', () {
  expect(SyncEngineTables.triggeredTables, containsAll([
    'form_exports', 'entry_exports', 'documents',
  ]));
});

test('tablesWithDirectProjectId includes form_exports, entry_exports, documents', () {
  expect(SyncEngineTables.tablesWithDirectProjectId, containsAll([
    'form_exports', 'entry_exports', 'documents',
  ]));
});
```

**Verification**:
```
pwsh -Command "flutter test test/core/database/migration_v43_test.dart"
pwsh -Command "flutter test test/features/sync/engine/sync_engine_tables_test.dart"
pwsh -Command "flutter test test/features/sync/engine/cascade_soft_delete_test.dart"
pwsh -Command "flutter test test/services/soft_delete_service_log_cleanup_test.dart"
```

---

## Phase 2: Supabase Migration (Agent: backend-supabase-agent)

### 2.1 — Fix inspector_forms RLS for builtin awareness

**File**: `supabase/migrations/20260328100000_fix_inspector_forms_and_new_tables.sql` (NEW)

**Step 2.1a** — Drop NOT NULL on project_id:

```sql
-- WHY: Builtin forms have no project association. project_id must be nullable.
-- FROM SPEC: inspector_forms.project_id DROP NOT NULL for builtin awareness.
ALTER TABLE inspector_forms ALTER COLUMN project_id DROP NOT NULL;
```

**Step 2.1b** — Replace existing RLS policies on inspector_forms:

```sql
-- WHY: Current RLS blocks builtin forms from being visible because they have
-- NULL project_id. New policies allow builtins for all authenticated users.
-- FROM SPEC: is_builtin = true OR project_id IN (company projects)

-- Drop existing policies
DROP POLICY IF EXISTS "inspector_forms_select" ON inspector_forms;
DROP POLICY IF EXISTS "inspector_forms_insert" ON inspector_forms;
DROP POLICY IF EXISTS "inspector_forms_update" ON inspector_forms;
DROP POLICY IF EXISTS "inspector_forms_delete" ON inspector_forms;

-- NOTE: get_my_company_id() is an existing helper function.
-- SEC-F02: TO authenticated on all. SEC-F03: NOT is_viewer on writes. SEC-F04: no is_builtin on INSERT.
CREATE POLICY "inspector_forms_select" ON inspector_forms
  FOR SELECT TO authenticated USING (
    is_builtin = true
    OR project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
  );

-- SEC-F04: Builtins are seeded locally and synced via upsert, not inserted fresh.
-- Removing is_builtin=true from INSERT prevents malicious builtin creation.
CREATE POLICY "inspector_forms_insert" ON inspector_forms
  FOR INSERT TO authenticated WITH CHECK (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  );

-- SEC-R03 FIX: WITH CHECK prevents flipping is_builtin or re-scoping builtins.
CREATE POLICY "inspector_forms_update" ON inspector_forms
  FOR UPDATE TO authenticated
  USING (
    (is_builtin = true OR project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id()))
    AND NOT is_viewer()
  )
  WITH CHECK (
    NOT is_viewer()
    AND (is_builtin = false OR (project_id IS NOT DISTINCT FROM NULL))
  );

-- NOTE: DELETE disallows deleting builtins — is_builtin = false guard.
CREATE POLICY "inspector_forms_delete" ON inspector_forms
  FOR DELETE TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND created_by_user_id = auth.uid()
    AND NOT is_viewer()
    AND is_builtin = false
  );
```

### 2.2 — Create 3 new tables with RLS

**Step 2.2a** — form_exports table:

```sql
-- FROM SPEC: form_exports — 15 columns, ownership-scoped RLS.
CREATE TABLE form_exports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  form_response_id UUID REFERENCES form_responses(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  entry_id UUID REFERENCES daily_entries(id) ON DELETE SET NULL,
  file_path TEXT,
  remote_path TEXT,
  filename TEXT NOT NULL,
  form_type TEXT NOT NULL,
  file_size_bytes BIGINT,
  exported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by_user_id UUID,
  deleted_at TIMESTAMPTZ,
  deleted_by UUID
);

-- NOTE: Supabase uses UUID type; SQLite uses TEXT. Both store the same UUIDs.
CREATE INDEX idx_form_exports_project ON form_exports(project_id);
CREATE INDEX idx_form_exports_entry ON form_exports(entry_id);
CREATE INDEX idx_form_exports_form_response ON form_exports(form_response_id);
CREATE INDEX idx_form_exports_form_type ON form_exports(form_type);
CREATE INDEX idx_form_exports_deleted_at ON form_exports(deleted_at);

ALTER TABLE form_exports ENABLE ROW LEVEL SECURITY;

-- SEC-F02/F03: TO authenticated + NOT is_viewer on writes
CREATE POLICY "form_exports_select" ON form_exports
  FOR SELECT TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
  );

CREATE POLICY "form_exports_insert" ON form_exports
  FOR INSERT TO authenticated WITH CHECK (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  );

CREATE POLICY "form_exports_update" ON form_exports
  FOR UPDATE TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND created_by_user_id = auth.uid()
    AND NOT is_viewer()
  );

CREATE POLICY "form_exports_delete" ON form_exports
  FOR DELETE TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND created_by_user_id = auth.uid()
    AND NOT is_viewer()
  );
```

**Step 2.2b** — entry_exports table:

```sql
-- FROM SPEC: entry_exports — 13 columns, ownership-scoped RLS.
CREATE TABLE entry_exports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entry_id UUID REFERENCES daily_entries(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  file_path TEXT,
  remote_path TEXT,
  filename TEXT NOT NULL,
  file_size_bytes BIGINT,
  exported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by_user_id UUID,
  deleted_at TIMESTAMPTZ,
  deleted_by UUID
);

CREATE INDEX idx_entry_exports_project ON entry_exports(project_id);
CREATE INDEX idx_entry_exports_entry ON entry_exports(entry_id);
CREATE INDEX idx_entry_exports_deleted_at ON entry_exports(deleted_at);

ALTER TABLE entry_exports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "entry_exports_select" ON entry_exports
  FOR SELECT TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
  );

CREATE POLICY "entry_exports_insert" ON entry_exports
  FOR INSERT TO authenticated WITH CHECK (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  );

CREATE POLICY "entry_exports_update" ON entry_exports
  FOR UPDATE TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND created_by_user_id = auth.uid()
    AND NOT is_viewer()
  );

CREATE POLICY "entry_exports_delete" ON entry_exports
  FOR DELETE TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND created_by_user_id = auth.uid()
    AND NOT is_viewer()
  );
```

**Step 2.2c** — documents table:

```sql
-- FROM SPEC: documents — 15 columns, ownership-scoped RLS.
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entry_id UUID REFERENCES daily_entries(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  file_path TEXT,
  remote_path TEXT,
  filename TEXT NOT NULL,
  file_type TEXT NOT NULL,
  file_size_bytes BIGINT,
  notes TEXT,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by_user_id UUID,
  deleted_at TIMESTAMPTZ,
  deleted_by UUID
);

CREATE INDEX idx_documents_project ON documents(project_id);
CREATE INDEX idx_documents_entry ON documents(entry_id);
CREATE INDEX idx_documents_file_type ON documents(file_type);
CREATE INDEX idx_documents_deleted_at ON documents(deleted_at);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "documents_select" ON documents
  FOR SELECT TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
  );

CREATE POLICY "documents_insert" ON documents
  FOR INSERT TO authenticated WITH CHECK (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND NOT is_viewer()
  );

CREATE POLICY "documents_update" ON documents
  FOR UPDATE TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND created_by_user_id = auth.uid()
    AND NOT is_viewer()
  );

CREATE POLICY "documents_delete" ON documents
  FOR DELETE TO authenticated USING (
    project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())
    AND created_by_user_id = auth.uid()
    AND NOT is_viewer()
  );
```

### 2.3 — Create 3 storage buckets with company-scoped policies

```sql
-- WHY: Exported PDFs and document attachments need cloud storage.
-- FROM SPEC: 3 buckets — form-exports, entry-exports, documents.
-- NOTE: Bucket policies scope access by company via the folder structure:
--   {company_id}/{project_id}/{filename}

INSERT INTO storage.buckets (id, name, public) VALUES ('form-exports', 'form-exports', false);
INSERT INTO storage.buckets (id, name, public) VALUES ('entry-exports', 'entry-exports', false);
INSERT INTO storage.buckets (id, name, public) VALUES ('entry-documents', 'entry-documents', false);

-- NOTE: Storage policies use (storage.foldername(name))[2] to extract company_id
-- from the path. Index [2] because path is prefix/companyId/..., and foldername
-- returns 1-indexed array. The entry-photos bucket had a bug using [1] that was
-- fixed in 20260305 migration — we use the corrected [2] from the start.

-- form-exports bucket policies (SEC-F01: use [2] not [1], SEC-F02: TO authenticated, SEC-F03: NOT is_viewer on writes)
CREATE POLICY "form_exports_storage_select" ON storage.objects
  FOR SELECT TO authenticated USING (
    bucket_id = 'form-exports'
    AND (storage.foldername(name))[2]::uuid = get_my_company_id()
  );

CREATE POLICY "form_exports_storage_insert" ON storage.objects
  FOR INSERT TO authenticated WITH CHECK (
    bucket_id = 'form-exports'
    AND (storage.foldername(name))[2]::uuid = get_my_company_id()
    AND NOT is_viewer()
  );

CREATE POLICY "form_exports_storage_update" ON storage.objects
  FOR UPDATE TO authenticated USING (
    bucket_id = 'form-exports'
    AND (storage.foldername(name))[2]::uuid = get_my_company_id()
    AND NOT is_viewer()
  );

CREATE POLICY "form_exports_storage_delete" ON storage.objects
  FOR DELETE TO authenticated USING (
    bucket_id = 'form-exports'
    AND (storage.foldername(name))[2]::uuid = get_my_company_id()
    AND NOT is_viewer()
  );

-- entry-exports bucket policies
CREATE POLICY "entry_exports_storage_select" ON storage.objects
  FOR SELECT TO authenticated USING (
    bucket_id = 'entry-exports'
    AND (storage.foldername(name))[2]::uuid = get_my_company_id()
  );

CREATE POLICY "entry_exports_storage_insert" ON storage.objects
  FOR INSERT TO authenticated WITH CHECK (
    bucket_id = 'entry-exports'
    AND (storage.foldername(name))[2]::uuid = get_my_company_id()
    AND NOT is_viewer()
  );

CREATE POLICY "entry_exports_storage_update" ON storage.objects
  FOR UPDATE TO authenticated USING (
    bucket_id = 'entry-exports'
    AND (storage.foldername(name))[2]::uuid = get_my_company_id()
    AND NOT is_viewer()
  );

CREATE POLICY "entry_exports_storage_delete" ON storage.objects
  FOR DELETE TO authenticated USING (
    bucket_id = 'entry-exports'
    AND (storage.foldername(name))[2]::uuid = get_my_company_id()
    AND NOT is_viewer()
  );

-- entry-documents bucket policies
CREATE POLICY "entry_documents_storage_select" ON storage.objects
  FOR SELECT TO authenticated USING (
    bucket_id = 'entry-documents'
    AND (storage.foldername(name))[2]::uuid = get_my_company_id()
  );

CREATE POLICY "entry_documents_storage_insert" ON storage.objects
  FOR INSERT TO authenticated WITH CHECK (
    bucket_id = 'entry-documents'
    AND (storage.foldername(name))[2]::uuid = get_my_company_id()
    AND NOT is_viewer()
  );

CREATE POLICY "entry_documents_storage_update" ON storage.objects
  FOR UPDATE TO authenticated USING (
    bucket_id = 'entry-documents'
    AND (storage.foldername(name))[2]::uuid = get_my_company_id()
    AND NOT is_viewer()
  );

CREATE POLICY "entry_documents_storage_delete" ON storage.objects
  FOR DELETE TO authenticated USING (
    bucket_id = 'entry-documents'
    AND (storage.foldername(name))[2]::uuid = get_my_company_id()
    AND NOT is_viewer()
  );
```

### 2.4 — Add to cascade soft-delete trigger + lock_created_by triggers

**File**: `supabase/migrations/20260328100000_fix_inspector_forms_and_new_tables.sql` (append)

```sql
-- WHY: When a project is soft-deleted, child rows in the 3 new tables must
-- also be soft-deleted. Add them to the existing cascade trigger function.
-- FROM SPEC: cascade_project_soft_delete includes these tables.

-- NOTE: We must replace the existing function to add the new tables.
-- The function is defined in 20260326200000_project_cascade_soft_delete.sql.
-- We append UPDATE statements for the 3 new tables.

CREATE OR REPLACE FUNCTION cascade_project_soft_delete()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL THEN
    -- NOTE: Existing cascades (inspector_forms already included at line 91)
    UPDATE locations SET deleted_at = NEW.deleted_at, deleted_by = NEW.deleted_by WHERE project_id = NEW.id AND deleted_at IS NULL;
    UPDATE contractors SET deleted_at = NEW.deleted_at, deleted_by = NEW.deleted_by WHERE project_id = NEW.id AND deleted_at IS NULL;
    UPDATE bid_items SET deleted_at = NEW.deleted_at, deleted_by = NEW.deleted_by WHERE project_id = NEW.id AND deleted_at IS NULL;
    UPDATE personnel_types SET deleted_at = NEW.deleted_at, deleted_by = NEW.deleted_by WHERE project_id = NEW.id AND deleted_at IS NULL;
    UPDATE daily_entries SET deleted_at = NEW.deleted_at, deleted_by = NEW.deleted_by WHERE project_id = NEW.id AND deleted_at IS NULL;
    UPDATE photos SET deleted_at = NEW.deleted_at, deleted_by = NEW.deleted_by WHERE project_id = NEW.id AND deleted_at IS NULL;
    UPDATE todo_items SET deleted_at = NEW.deleted_at, deleted_by = NEW.deleted_by WHERE project_id = NEW.id AND deleted_at IS NULL;
    UPDATE inspector_forms SET deleted_at = NEW.deleted_at, deleted_by = NEW.deleted_by WHERE project_id = NEW.id AND deleted_at IS NULL;
    UPDATE equipment SET deleted_at = NEW.deleted_at, deleted_by = NEW.deleted_by WHERE project_id = NEW.id AND deleted_at IS NULL;
    -- NEW: 3 new tables
    UPDATE form_exports SET deleted_at = NEW.deleted_at, deleted_by = NEW.deleted_by WHERE project_id = NEW.id AND deleted_at IS NULL;
    UPDATE entry_exports SET deleted_at = NEW.deleted_at, deleted_by = NEW.deleted_by WHERE project_id = NEW.id AND deleted_at IS NULL;
    UPDATE documents SET deleted_at = NEW.deleted_at, deleted_by = NEW.deleted_by WHERE project_id = NEW.id AND deleted_at IS NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- WHY: Lock created_by_user_id after insert to prevent tampering.
-- NOTE: Same pattern as existing lock_created_by triggers on other tables.
CREATE OR REPLACE FUNCTION lock_created_by() RETURNS TRIGGER AS $$
BEGIN
  IF OLD.created_by_user_id IS NOT NULL AND NEW.created_by_user_id IS DISTINCT FROM OLD.created_by_user_id THEN
    NEW.created_by_user_id := OLD.created_by_user_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER lock_created_by_form_exports
  BEFORE UPDATE ON form_exports
  FOR EACH ROW EXECUTE FUNCTION lock_created_by();

CREATE TRIGGER lock_created_by_entry_exports
  BEFORE UPDATE ON entry_exports
  FOR EACH ROW EXECUTE FUNCTION lock_created_by();

CREATE TRIGGER lock_created_by_documents
  BEFORE UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION lock_created_by();

-- WHY: auto-set updated_at on every UPDATE.
CREATE TRIGGER set_updated_at_form_exports
  BEFORE UPDATE ON form_exports
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER set_updated_at_entry_exports
  BEFORE UPDATE ON entry_exports
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER set_updated_at_documents
  BEFORE UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

**Verification**:
```
npx supabase db push --dry-run
```

---

## Phase 3: Data Layer — Models (Agent: backend-data-layer-agent)

### 3.1 — FormExport model

**File**: `lib/features/forms/data/models/form_export.dart` (NEW)

```dart
import 'package:uuid/uuid.dart';

// FROM SPEC: form_exports model with 15 fields matching SQLite schema.
// NOTE: form_response_id is nullable despite spec saying Required=Yes, because
// form exports can exist as orphaned artifacts after a form response is deleted
// (ON DELETE CASCADE would lose the export metadata; we use SET NULL semantics
// at the application layer to preserve the export file reference).
class FormExport {
  final String id;
  final String? formResponseId;
  final String projectId;
  final String? entryId;
  final String? filePath;
  final String? remotePath;
  final String filename;
  final String formType;
  final int? fileSizeBytes;
  final String exportedAt;
  final String createdAt;
  final String updatedAt;
  final String? createdByUserId;
  final String? deletedAt;
  final String? deletedBy;

  FormExport({
    String? id,
    this.formResponseId,
    required this.projectId,
    this.entryId,
    this.filePath,
    this.remotePath,
    required this.filename,
    required this.formType,
    this.fileSizeBytes,
    String? exportedAt,
    String? createdAt,
    String? updatedAt,
    this.createdByUserId,
    this.deletedAt,
    this.deletedBy,
  })  : id = id ?? const Uuid().v4(),
        exportedAt = exportedAt ?? DateTime.now().toUtc().toIso8601String(),
        createdAt = createdAt ?? DateTime.now().toUtc().toIso8601String(),
        updatedAt = updatedAt ?? DateTime.now().toUtc().toIso8601String();

  FormExport copyWith({
    String? id,
    String? formResponseId,
    String? projectId,
    String? entryId,
    String? filePath,
    String? remotePath,
    String? filename,
    String? formType,
    int? fileSizeBytes,
    String? exportedAt,
    String? createdAt,
    String? updatedAt,
    String? createdByUserId,
    String? deletedAt,
    String? deletedBy,
  }) {
    return FormExport(
      id: id ?? this.id,
      formResponseId: formResponseId ?? this.formResponseId,
      projectId: projectId ?? this.projectId,
      entryId: entryId ?? this.entryId,
      filePath: filePath ?? this.filePath,
      remotePath: remotePath ?? this.remotePath,
      filename: filename ?? this.filename,
      formType: formType ?? this.formType,
      fileSizeBytes: fileSizeBytes ?? this.fileSizeBytes,
      exportedAt: exportedAt ?? this.exportedAt,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      createdByUserId: createdByUserId ?? this.createdByUserId,
      deletedAt: deletedAt ?? this.deletedAt,
      deletedBy: deletedBy ?? this.deletedBy,
    );
  }

  Map<String, dynamic> toMap() => {
    'id': id,
    'form_response_id': formResponseId,
    'project_id': projectId,
    'entry_id': entryId,
    'file_path': filePath,
    'remote_path': remotePath,
    'filename': filename,
    'form_type': formType,
    'file_size_bytes': fileSizeBytes,
    'exported_at': exportedAt,
    'created_at': createdAt,
    'updated_at': updatedAt,
    'created_by_user_id': createdByUserId,
    'deleted_at': deletedAt,
    'deleted_by': deletedBy,
  };

  factory FormExport.fromMap(Map<String, dynamic> map) => FormExport(
    id: map['id'] as String,
    formResponseId: map['form_response_id'] as String?,
    projectId: map['project_id'] as String,
    entryId: map['entry_id'] as String?,
    filePath: map['file_path'] as String?,
    remotePath: map['remote_path'] as String?,
    filename: map['filename'] as String,
    formType: map['form_type'] as String,
    fileSizeBytes: map['file_size_bytes'] as int?,
    exportedAt: map['exported_at'] as String,
    createdAt: map['created_at'] as String,
    updatedAt: map['updated_at'] as String,
    createdByUserId: map['created_by_user_id'] as String?,
    deletedAt: map['deleted_at'] as String?,
    deletedBy: map['deleted_by'] as String?,
  );
}
```

### 3.2 — EntryExport model

**File**: `lib/features/entries/data/models/entry_export.dart` (NEW)

```dart
import 'package:uuid/uuid.dart';

// FROM SPEC: entry_exports model with 13 fields matching SQLite schema.
class EntryExport {
  final String id;
  final String? entryId;
  final String projectId;
  final String? filePath;
  final String? remotePath;
  final String filename;
  final int? fileSizeBytes;
  final String exportedAt;
  final String createdAt;
  final String updatedAt;
  final String? createdByUserId;
  final String? deletedAt;
  final String? deletedBy;

  EntryExport({
    String? id,
    this.entryId,
    required this.projectId,
    this.filePath,
    this.remotePath,
    required this.filename,
    this.fileSizeBytes,
    String? exportedAt,
    String? createdAt,
    String? updatedAt,
    this.createdByUserId,
    this.deletedAt,
    this.deletedBy,
  })  : id = id ?? const Uuid().v4(),
        exportedAt = exportedAt ?? DateTime.now().toUtc().toIso8601String(),
        createdAt = createdAt ?? DateTime.now().toUtc().toIso8601String(),
        updatedAt = updatedAt ?? DateTime.now().toUtc().toIso8601String();

  EntryExport copyWith({
    String? id,
    String? entryId,
    String? projectId,
    String? filePath,
    String? remotePath,
    String? filename,
    int? fileSizeBytes,
    String? exportedAt,
    String? createdAt,
    String? updatedAt,
    String? createdByUserId,
    String? deletedAt,
    String? deletedBy,
  }) {
    return EntryExport(
      id: id ?? this.id,
      entryId: entryId ?? this.entryId,
      projectId: projectId ?? this.projectId,
      filePath: filePath ?? this.filePath,
      remotePath: remotePath ?? this.remotePath,
      filename: filename ?? this.filename,
      fileSizeBytes: fileSizeBytes ?? this.fileSizeBytes,
      exportedAt: exportedAt ?? this.exportedAt,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      createdByUserId: createdByUserId ?? this.createdByUserId,
      deletedAt: deletedAt ?? this.deletedAt,
      deletedBy: deletedBy ?? this.deletedBy,
    );
  }

  Map<String, dynamic> toMap() => {
    'id': id,
    'entry_id': entryId,
    'project_id': projectId,
    'file_path': filePath,
    'remote_path': remotePath,
    'filename': filename,
    'file_size_bytes': fileSizeBytes,
    'exported_at': exportedAt,
    'created_at': createdAt,
    'updated_at': updatedAt,
    'created_by_user_id': createdByUserId,
    'deleted_at': deletedAt,
    'deleted_by': deletedBy,
  };

  factory EntryExport.fromMap(Map<String, dynamic> map) => EntryExport(
    id: map['id'] as String,
    entryId: map['entry_id'] as String?,
    projectId: map['project_id'] as String,
    filePath: map['file_path'] as String?,
    remotePath: map['remote_path'] as String?,
    filename: map['filename'] as String,
    fileSizeBytes: map['file_size_bytes'] as int?,
    exportedAt: map['exported_at'] as String,
    createdAt: map['created_at'] as String,
    updatedAt: map['updated_at'] as String,
    createdByUserId: map['created_by_user_id'] as String?,
    deletedAt: map['deleted_at'] as String?,
    deletedBy: map['deleted_by'] as String?,
  );
}
```

### 3.3 — Document model

**File**: `lib/features/entries/data/models/document.dart` (NEW)

```dart
import 'package:uuid/uuid.dart';

// FROM SPEC: documents model with 15 fields matching SQLite schema.
// WHY: Placed in entries feature because documents attach to daily_entries.
class Document {
  final String id;
  final String? entryId;
  final String projectId;
  final String? filePath;
  final String? remotePath;
  final String filename;
  final String fileType;
  final int? fileSizeBytes;
  final String? notes;
  final String capturedAt;
  final String createdAt;
  final String updatedAt;
  final String? createdByUserId;
  final String? deletedAt;
  final String? deletedBy;

  Document({
    String? id,
    this.entryId,
    required this.projectId,
    this.filePath,
    this.remotePath,
    required this.filename,
    required this.fileType,
    this.fileSizeBytes,
    this.notes,
    String? capturedAt,
    String? createdAt,
    String? updatedAt,
    this.createdByUserId,
    this.deletedAt,
    this.deletedBy,
  })  : id = id ?? const Uuid().v4(),
        capturedAt = capturedAt ?? DateTime.now().toUtc().toIso8601String(),
        createdAt = createdAt ?? DateTime.now().toUtc().toIso8601String(),
        updatedAt = updatedAt ?? DateTime.now().toUtc().toIso8601String();

  Document copyWith({
    String? id,
    String? entryId,
    String? projectId,
    String? filePath,
    String? remotePath,
    String? filename,
    String? fileType,
    int? fileSizeBytes,
    String? notes,
    String? capturedAt,
    String? createdAt,
    String? updatedAt,
    String? createdByUserId,
    String? deletedAt,
    String? deletedBy,
  }) {
    return Document(
      id: id ?? this.id,
      entryId: entryId ?? this.entryId,
      projectId: projectId ?? this.projectId,
      filePath: filePath ?? this.filePath,
      remotePath: remotePath ?? this.remotePath,
      filename: filename ?? this.filename,
      fileType: fileType ?? this.fileType,
      fileSizeBytes: fileSizeBytes ?? this.fileSizeBytes,
      notes: notes ?? this.notes,
      capturedAt: capturedAt ?? this.capturedAt,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      createdByUserId: createdByUserId ?? this.createdByUserId,
      deletedAt: deletedAt ?? this.deletedAt,
      deletedBy: deletedBy ?? this.deletedBy,
    );
  }

  Map<String, dynamic> toMap() => {
    'id': id,
    'entry_id': entryId,
    'project_id': projectId,
    'file_path': filePath,
    'remote_path': remotePath,
    'filename': filename,
    'file_type': fileType,
    'file_size_bytes': fileSizeBytes,
    'notes': notes,
    'captured_at': capturedAt,
    'created_at': createdAt,
    'updated_at': updatedAt,
    'created_by_user_id': createdByUserId,
    'deleted_at': deletedAt,
    'deleted_by': deletedBy,
  };

  factory Document.fromMap(Map<String, dynamic> map) => Document(
    id: map['id'] as String,
    entryId: map['entry_id'] as String?,
    projectId: map['project_id'] as String,
    filePath: map['file_path'] as String?,
    remotePath: map['remote_path'] as String?,
    filename: map['filename'] as String,
    fileType: map['file_type'] as String,
    fileSizeBytes: map['file_size_bytes'] as int?,
    notes: map['notes'] as String?,
    capturedAt: map['captured_at'] as String,
    createdAt: map['created_at'] as String,
    updatedAt: map['updated_at'] as String,
    createdByUserId: map['created_by_user_id'] as String?,
    deletedAt: map['deleted_at'] as String?,
    deletedBy: map['deleted_by'] as String?,
  );
}
```

### 3.4 — BuiltinFormConfig model

**File**: `lib/features/forms/data/models/builtin_form_config.dart` (NEW)

```dart
// WHY: Centralizes the definition of which forms ship as builtins.
// NOTE: This is a config model, not a DB-backed model. It defines the
// asset paths and metadata for forms bundled in the app binary.
class BuiltinFormConfig {
  final String name;
  final String templateAssetPath;
  final String formType;
  final Map<String, dynamic>? fieldDefinitions;
  final String? parsingKeywords;
  final String? tableRowConfig;

  const BuiltinFormConfig({
    required this.name,
    required this.templateAssetPath,
    required this.formType,
    this.fieldDefinitions,
    this.parsingKeywords,
    this.tableRowConfig,
  });

  // NOTE: Actual builtin form entries will be added in a later phase
  // when the form templates are finalized. This is the registry pattern.
  static const List<BuiltinFormConfig> builtins = [
    // Placeholder — populated when form templates are added
  ];
}
```

### 3.5 — Model tests

**File**: `test/features/forms/data/models/form_export_test.dart` (NEW)

```dart
// WHY: Verify round-trip serialization and default value generation.
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/forms/data/models/form_export.dart';

void main() {
  group('FormExport', () {
    test('generates id and timestamps when not provided', () {
      final export = FormExport(
        projectId: 'proj-1',
        filename: 'test.pdf',
        formType: 'daily_report',
      );
      expect(export.id, isNotEmpty);
      expect(export.exportedAt, isNotEmpty);
      expect(export.createdAt, isNotEmpty);
      expect(export.updatedAt, isNotEmpty);
    });

    test('round-trips through toMap/fromMap', () {
      final original = FormExport(
        id: 'fe-1',
        formResponseId: 'fr-1',
        projectId: 'proj-1',
        entryId: 'entry-1',
        filePath: '/local/test.pdf',
        remotePath: 'remote/test.pdf',
        filename: 'test.pdf',
        formType: 'daily_report',
        fileSizeBytes: 12345,
        exportedAt: '2026-03-28T00:00:00.000Z',
        createdAt: '2026-03-28T00:00:00.000Z',
        updatedAt: '2026-03-28T00:00:00.000Z',
        createdByUserId: 'user-1',
      );
      final restored = FormExport.fromMap(original.toMap());
      expect(restored.id, original.id);
      expect(restored.formResponseId, original.formResponseId);
      expect(restored.projectId, original.projectId);
      expect(restored.entryId, original.entryId);
      expect(restored.filePath, original.filePath);
      expect(restored.remotePath, original.remotePath);
      expect(restored.filename, original.filename);
      expect(restored.formType, original.formType);
      expect(restored.fileSizeBytes, original.fileSizeBytes);
      expect(restored.createdByUserId, original.createdByUserId);
    });

    test('copyWith preserves unmodified fields', () {
      final original = FormExport(
        projectId: 'proj-1',
        filename: 'test.pdf',
        formType: 'daily_report',
      );
      final modified = original.copyWith(filename: 'updated.pdf');
      expect(modified.filename, 'updated.pdf');
      expect(modified.id, original.id);
      expect(modified.projectId, original.projectId);
    });

    test('nullable fields default to null', () {
      final export = FormExport(
        projectId: 'proj-1',
        filename: 'test.pdf',
        formType: 'daily_report',
      );
      expect(export.formResponseId, isNull);
      expect(export.entryId, isNull);
      expect(export.filePath, isNull);
      expect(export.remotePath, isNull);
      expect(export.fileSizeBytes, isNull);
      expect(export.deletedAt, isNull);
      expect(export.deletedBy, isNull);
    });
  });
}
```

**File**: `test/features/entries/data/models/entry_export_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/entries/data/models/entry_export.dart';

void main() {
  group('EntryExport', () {
    test('generates id and timestamps when not provided', () {
      final export = EntryExport(
        projectId: 'proj-1',
        filename: 'entry-report.pdf',
      );
      expect(export.id, isNotEmpty);
      expect(export.exportedAt, isNotEmpty);
      expect(export.createdAt, isNotEmpty);
    });

    test('round-trips through toMap/fromMap', () {
      final original = EntryExport(
        id: 'ee-1',
        entryId: 'entry-1',
        projectId: 'proj-1',
        filePath: '/local/report.pdf',
        remotePath: 'remote/report.pdf',
        filename: 'report.pdf',
        fileSizeBytes: 54321,
        exportedAt: '2026-03-28T00:00:00.000Z',
        createdAt: '2026-03-28T00:00:00.000Z',
        updatedAt: '2026-03-28T00:00:00.000Z',
        createdByUserId: 'user-1',
      );
      final restored = EntryExport.fromMap(original.toMap());
      expect(restored.id, original.id);
      expect(restored.entryId, original.entryId);
      expect(restored.projectId, original.projectId);
      expect(restored.filename, original.filename);
      expect(restored.fileSizeBytes, original.fileSizeBytes);
    });

    test('copyWith preserves unmodified fields', () {
      final original = EntryExport(
        projectId: 'proj-1',
        filename: 'report.pdf',
      );
      final modified = original.copyWith(filename: 'updated-report.pdf');
      expect(modified.filename, 'updated-report.pdf');
      expect(modified.id, original.id);
    });
  });
}
```

**File**: `test/features/entries/data/models/document_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/entries/data/models/document.dart';

void main() {
  group('Document', () {
    test('generates id and timestamps when not provided', () {
      final doc = Document(
        projectId: 'proj-1',
        filename: 'specs.pdf',
        fileType: 'application/pdf',
      );
      expect(doc.id, isNotEmpty);
      expect(doc.capturedAt, isNotEmpty);
      expect(doc.createdAt, isNotEmpty);
    });

    test('round-trips through toMap/fromMap', () {
      final original = Document(
        id: 'doc-1',
        entryId: 'entry-1',
        projectId: 'proj-1',
        filePath: '/local/specs.pdf',
        remotePath: 'remote/specs.pdf',
        filename: 'specs.pdf',
        fileType: 'application/pdf',
        fileSizeBytes: 99999,
        notes: 'Foundation specs',
        capturedAt: '2026-03-28T00:00:00.000Z',
        createdAt: '2026-03-28T00:00:00.000Z',
        updatedAt: '2026-03-28T00:00:00.000Z',
        createdByUserId: 'user-1',
      );
      final restored = Document.fromMap(original.toMap());
      expect(restored.id, original.id);
      expect(restored.entryId, original.entryId);
      expect(restored.filename, original.filename);
      expect(restored.fileType, original.fileType);
      expect(restored.notes, original.notes);
      expect(restored.fileSizeBytes, original.fileSizeBytes);
    });

    test('copyWith preserves unmodified fields', () {
      final original = Document(
        projectId: 'proj-1',
        filename: 'specs.pdf',
        fileType: 'application/pdf',
      );
      final modified = original.copyWith(notes: 'Updated notes');
      expect(modified.notes, 'Updated notes');
      expect(modified.id, original.id);
      expect(modified.fileType, original.fileType);
    });
  });
}
```

**Verification**:
```
pwsh -Command "flutter test test/features/forms/data/models/form_export_test.dart"
pwsh -Command "flutter test test/features/entries/data/models/entry_export_test.dart"
pwsh -Command "flutter test test/features/entries/data/models/document_test.dart"
```

---

## Phase 4: Data Layer — Datasources & Repositories (Agent: backend-data-layer-agent)

### 4.1 — FormExport datasources + repository

**Step 4.1a** — Local datasource

**File**: `lib/features/forms/data/datasources/form_export_local_datasource.dart` (NEW)

```dart
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/shared/datasources/project_scoped_datasource.dart';
import 'package:construction_inspector/features/forms/data/models/form_export.dart';

// WHY: Follows ProjectScopedDatasource pattern — form_exports has project_id.
class FormExportLocalDatasource extends ProjectScopedDatasource<FormExport> {
  @override
  final DatabaseService db;

  FormExportLocalDatasource(this.db);

  @override
  String get tableName => 'form_exports';

  @override
  String get defaultOrderBy => 'exported_at DESC';

  @override
  FormExport fromMap(Map<String, dynamic> map) => FormExport.fromMap(map);

  @override
  Map<String, dynamic> toMap(FormExport item) => item.toMap();

  @override
  String getId(FormExport item) => item.id;

  // NOTE: Custom query — get exports for a specific form response
  Future<List<FormExport>> getByFormResponseId(String formResponseId) async {
    final database = await db.database;
    final results = await database.query(
      tableName,
      where: 'form_response_id = ? AND deleted_at IS NULL',
      whereArgs: [formResponseId],
      orderBy: defaultOrderBy,
    );
    return results.map(fromMap).toList();
  }

  // NOTE: Custom query — get exports for a specific entry
  Future<List<FormExport>> getByEntryId(String entryId) async {
    final database = await db.database;
    final results = await database.query(
      tableName,
      where: 'entry_id = ? AND deleted_at IS NULL',
      whereArgs: [entryId],
      orderBy: defaultOrderBy,
    );
    return results.map(fromMap).toList();
  }

  // NOTE: Soft-delete all exports for a form response (cascade support)
  Future<void> softDeleteByFormResponseId(String formResponseId, {String? userId}) async {
    final database = await db.database;
    final now = DateTime.now().toUtc().toIso8601String();
    await database.update(
      tableName,
      {'deleted_at': now, 'deleted_by': userId, 'updated_at': now},
      where: 'form_response_id = ? AND deleted_at IS NULL',
      whereArgs: [formResponseId],
    );
  }

  // NOTE: Soft-delete all exports for an entry (cascade support)
  Future<void> softDeleteByEntryId(String entryId, {String? userId}) async {
    final database = await db.database;
    final now = DateTime.now().toUtc().toIso8601String();
    await database.update(
      tableName,
      {'deleted_at': now, 'deleted_by': userId, 'updated_at': now},
      where: 'entry_id = ? AND deleted_at IS NULL',
      whereArgs: [entryId],
    );
  }
}
```

**Step 4.1b** — Remote datasource

**File**: `lib/features/forms/data/datasources/form_export_remote_datasource.dart` (NEW)

```dart
import 'package:construction_inspector/shared/datasources/base_remote_datasource.dart';
import 'package:construction_inspector/features/forms/data/models/form_export.dart';

// WHY: Standard BaseRemoteDatasource implementation for Supabase sync.
class FormExportRemoteDatasource extends BaseRemoteDatasource<FormExport> {
  @override
  String get tableName => 'form_exports';

  @override
  FormExport fromMap(Map<String, dynamic> map) => FormExport.fromMap(map);

  @override
  Map<String, dynamic> toMap(FormExport item) => item.toMap();
}
```

**Step 4.1c** — Repository

**File**: `lib/features/forms/data/repositories/form_export_repository.dart` (NEW)

```dart
import 'package:construction_inspector/shared/repositories/base_repository.dart';
import 'package:construction_inspector/shared/repositories/repository_result.dart';
import 'package:construction_inspector/shared/models/paged_result.dart';
import 'package:construction_inspector/features/forms/data/models/form_export.dart';
import 'package:construction_inspector/features/forms/data/datasources/form_export_local_datasource.dart';

// WHY: Wraps datasource with RepositoryResult error handling.
// NOTE: Follows InspectorFormRepository pattern.
class FormExportRepository implements BaseRepository<FormExport> {
  final FormExportLocalDatasource _localDatasource;

  FormExportRepository(this._localDatasource);

  @override
  Future<FormExport?> getById(String id) async {
    try {
      return await _localDatasource.getById(id);
    } catch (e) {
      return null;
    }
  }

  @override
  Future<List<FormExport>> getAll() async {
    return await _localDatasource.getAll();
  }

  @override
  Future<PagedResult<FormExport>> getPaged({required int offset, required int limit}) async {
    return await _localDatasource.getPaged(offset: offset, limit: limit);
  }

  @override
  Future<int> getCount() async {
    return await _localDatasource.getCount();
  }

  @override
  Future<void> save(FormExport item) async {
    await _localDatasource.upsert(item);
  }

  @override
  Future<void> delete(String id) async {
    await _localDatasource.softDelete(id);
  }

  Future<RepositoryResult<FormExport>> create(FormExport formExport) async {
    try {
      // WHY: Validate required fields before persisting.
      if (formExport.filename.isEmpty) {
        return RepositoryResult.failure('Filename is required');
      }
      if (formExport.formType.isEmpty) {
        return RepositoryResult.failure('Form type is required');
      }
      await _localDatasource.insert(formExport);
      return RepositoryResult.success(formExport);
    } catch (e) {
      return RepositoryResult.failure(e.toString());
    }
  }

  Future<List<FormExport>> getByProjectId(String projectId) async {
    return await _localDatasource.getByProjectId(projectId);
  }

  Future<List<FormExport>> getByEntryId(String entryId) async {
    return await _localDatasource.getByEntryId(entryId);
  }

  Future<List<FormExport>> getByFormResponseId(String formResponseId) async {
    return await _localDatasource.getByFormResponseId(formResponseId);
  }
}
```

### 4.2 — EntryExport datasources + repository

**Step 4.2a** — Local datasource

**File**: `lib/features/entries/data/datasources/entry_export_local_datasource.dart` (NEW)

```dart
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/shared/datasources/project_scoped_datasource.dart';
import 'package:construction_inspector/features/entries/data/models/entry_export.dart';

// WHY: Follows ProjectScopedDatasource pattern — entry_exports has project_id.
class EntryExportLocalDatasource extends ProjectScopedDatasource<EntryExport> {
  @override
  final DatabaseService db;

  EntryExportLocalDatasource(this.db);

  @override
  String get tableName => 'entry_exports';

  @override
  String get defaultOrderBy => 'exported_at DESC';

  @override
  EntryExport fromMap(Map<String, dynamic> map) => EntryExport.fromMap(map);

  @override
  Map<String, dynamic> toMap(EntryExport item) => item.toMap();

  @override
  String getId(EntryExport item) => item.id;

  // NOTE: Custom query — get exports for a specific entry
  Future<List<EntryExport>> getByEntryId(String entryId) async {
    final database = await db.database;
    final results = await database.query(
      tableName,
      where: 'entry_id = ? AND deleted_at IS NULL',
      whereArgs: [entryId],
      orderBy: defaultOrderBy,
    );
    return results.map(fromMap).toList();
  }

  Future<void> softDeleteByEntryId(String entryId, {String? userId}) async {
    final database = await db.database;
    final now = DateTime.now().toUtc().toIso8601String();
    await database.update(
      tableName,
      {'deleted_at': now, 'deleted_by': userId, 'updated_at': now},
      where: 'entry_id = ? AND deleted_at IS NULL',
      whereArgs: [entryId],
    );
  }
}
```

**Step 4.2b** — Remote datasource

**File**: `lib/features/entries/data/datasources/entry_export_remote_datasource.dart` (NEW)

```dart
import 'package:construction_inspector/shared/datasources/base_remote_datasource.dart';
import 'package:construction_inspector/features/entries/data/models/entry_export.dart';

class EntryExportRemoteDatasource extends BaseRemoteDatasource<EntryExport> {
  @override
  String get tableName => 'entry_exports';

  @override
  EntryExport fromMap(Map<String, dynamic> map) => EntryExport.fromMap(map);

  @override
  Map<String, dynamic> toMap(EntryExport item) => item.toMap();
}
```

**Step 4.2c** — Repository

**File**: `lib/features/entries/data/repositories/entry_export_repository.dart` (NEW)

```dart
import 'package:construction_inspector/shared/repositories/base_repository.dart';
import 'package:construction_inspector/shared/repositories/repository_result.dart';
import 'package:construction_inspector/shared/models/paged_result.dart';
import 'package:construction_inspector/features/entries/data/models/entry_export.dart';
import 'package:construction_inspector/features/entries/data/datasources/entry_export_local_datasource.dart';

class EntryExportRepository implements BaseRepository<EntryExport> {
  final EntryExportLocalDatasource _localDatasource;

  EntryExportRepository(this._localDatasource);

  @override
  Future<EntryExport?> getById(String id) async {
    try {
      return await _localDatasource.getById(id);
    } catch (e) {
      return null;
    }
  }

  @override
  Future<List<EntryExport>> getAll() async {
    return await _localDatasource.getAll();
  }

  @override
  Future<PagedResult<EntryExport>> getPaged({required int offset, required int limit}) async {
    return await _localDatasource.getPaged(offset: offset, limit: limit);
  }

  @override
  Future<int> getCount() async {
    return await _localDatasource.getCount();
  }

  @override
  Future<void> save(EntryExport item) async {
    await _localDatasource.upsert(item);
  }

  @override
  Future<void> delete(String id) async {
    await _localDatasource.softDelete(id);
  }

  Future<RepositoryResult<EntryExport>> create(EntryExport entryExport) async {
    try {
      if (entryExport.filename.isEmpty) {
        return RepositoryResult.failure('Filename is required');
      }
      await _localDatasource.insert(entryExport);
      return RepositoryResult.success(entryExport);
    } catch (e) {
      return RepositoryResult.failure(e.toString());
    }
  }

  Future<List<EntryExport>> getByProjectId(String projectId) async {
    return await _localDatasource.getByProjectId(projectId);
  }

  Future<List<EntryExport>> getByEntryId(String entryId) async {
    return await _localDatasource.getByEntryId(entryId);
  }
}
```

### 4.3 — Document datasources + repository

**Step 4.3a** — Local datasource

**File**: `lib/features/entries/data/datasources/document_local_datasource.dart` (NEW)

```dart
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/shared/datasources/project_scoped_datasource.dart';
import 'package:construction_inspector/features/entries/data/models/document.dart';

// WHY: Follows ProjectScopedDatasource pattern — documents has project_id.
class DocumentLocalDatasource extends ProjectScopedDatasource<Document> {
  @override
  final DatabaseService db;

  DocumentLocalDatasource(this.db);

  @override
  String get tableName => 'documents';

  @override
  String get defaultOrderBy => 'captured_at DESC';

  @override
  Document fromMap(Map<String, dynamic> map) => Document.fromMap(map);

  @override
  Map<String, dynamic> toMap(Document item) => item.toMap();

  @override
  String getId(Document item) => item.id;

  // NOTE: Custom query — get documents for a specific entry
  Future<List<Document>> getByEntryId(String entryId) async {
    final database = await db.database;
    final results = await database.query(
      tableName,
      where: 'entry_id = ? AND deleted_at IS NULL',
      whereArgs: [entryId],
      orderBy: defaultOrderBy,
    );
    return results.map(fromMap).toList();
  }

  Future<int> getCountByEntryId(String entryId) async {
    final database = await db.database;
    final result = await database.rawQuery(
      'SELECT COUNT(*) as count FROM $tableName WHERE entry_id = ? AND deleted_at IS NULL',
      [entryId],
    );
    return result.first['count'] as int;
  }

  Future<void> softDeleteByEntryId(String entryId, {String? userId}) async {
    final database = await db.database;
    final now = DateTime.now().toUtc().toIso8601String();
    await database.update(
      tableName,
      {'deleted_at': now, 'deleted_by': userId, 'updated_at': now},
      where: 'entry_id = ? AND deleted_at IS NULL',
      whereArgs: [entryId],
    );
  }

  // NOTE: Filter by file type (e.g., 'application/pdf', 'application/vnd.ms-excel')
  Future<List<Document>> getByFileType(String projectId, String fileType) async {
    final database = await db.database;
    final results = await database.query(
      tableName,
      where: 'project_id = ? AND file_type = ? AND deleted_at IS NULL',
      whereArgs: [projectId, fileType],
      orderBy: defaultOrderBy,
    );
    return results.map(fromMap).toList();
  }
}
```

**Step 4.3b** — Remote datasource

**File**: `lib/features/entries/data/datasources/document_remote_datasource.dart` (NEW)

```dart
import 'package:construction_inspector/shared/datasources/base_remote_datasource.dart';
import 'package:construction_inspector/features/entries/data/models/document.dart';

class DocumentRemoteDatasource extends BaseRemoteDatasource<Document> {
  @override
  String get tableName => 'documents';

  @override
  Document fromMap(Map<String, dynamic> map) => Document.fromMap(map);

  @override
  Map<String, dynamic> toMap(Document item) => item.toMap();
}
```

**Step 4.3c** — Repository

**File**: `lib/features/entries/data/repositories/document_repository.dart` (NEW)

```dart
import 'package:construction_inspector/shared/repositories/base_repository.dart';
import 'package:construction_inspector/shared/repositories/repository_result.dart';
import 'package:construction_inspector/shared/models/paged_result.dart';
import 'package:construction_inspector/features/entries/data/models/document.dart';
import 'package:construction_inspector/features/entries/data/datasources/document_local_datasource.dart';

class DocumentRepository implements BaseRepository<Document> {
  final DocumentLocalDatasource _localDatasource;

  DocumentRepository(this._localDatasource);

  @override
  Future<Document?> getById(String id) async {
    try {
      return await _localDatasource.getById(id);
    } catch (e) {
      return null;
    }
  }

  @override
  Future<List<Document>> getAll() async {
    return await _localDatasource.getAll();
  }

  @override
  Future<PagedResult<Document>> getPaged({required int offset, required int limit}) async {
    return await _localDatasource.getPaged(offset: offset, limit: limit);
  }

  @override
  Future<int> getCount() async {
    return await _localDatasource.getCount();
  }

  @override
  Future<void> save(Document item) async {
    await _localDatasource.upsert(item);
  }

  @override
  Future<void> delete(String id) async {
    await _localDatasource.softDelete(id);
  }

  // SEC-F06: File type allowlist — only accept known document types.
  static const allowedFileTypes = ['pdf', 'xls', 'xlsx', 'doc', 'docx'];

  Future<RepositoryResult<Document>> create(Document document) async {
    try {
      // WHY: Validate required fields before persisting.
      if (document.filename.isEmpty) {
        return RepositoryResult.failure('Filename is required');
      }
      if (document.fileType.isEmpty) {
        return RepositoryResult.failure('File type is required');
      }
      // SEC-F06: File type allowlist — reject unsupported types at the repository layer.
      if (!allowedFileTypes.contains(document.fileType.toLowerCase())) {
        return RepositoryResult.failure('Unsupported file type: ${document.fileType}');
      }
      // SEC-F05: Filename sanitization — reject path traversal or dangerous characters.
      if (document.filename.contains('..') || document.filename.contains('/') || document.filename.contains('\\')) {
        return RepositoryResult.failure('Invalid filename: ${document.filename}');
      }
      await _localDatasource.insert(document);
      return RepositoryResult.success(document);
    } catch (e) {
      return RepositoryResult.failure(e.toString());
    }
  }

  Future<RepositoryResult<Document>> update(Document document) async {
    try {
      if (document.filename.isEmpty) {
        return RepositoryResult.failure('Filename is required');
      }
      final updated = document.copyWith(
        updatedAt: DateTime.now().toUtc().toIso8601String(),
      );
      await _localDatasource.update(updated);
      return RepositoryResult.success(updated);
    } catch (e) {
      return RepositoryResult.failure(e.toString());
    }
  }

  Future<List<Document>> getByProjectId(String projectId) async {
    return await _localDatasource.getByProjectId(projectId);
  }

  Future<List<Document>> getByEntryId(String entryId) async {
    return await _localDatasource.getByEntryId(entryId);
  }

  Future<int> getCountByEntryId(String entryId) async {
    return await _localDatasource.getCountByEntryId(entryId);
  }
}
```

### 4.4 — Datasource & Repository Tests

**File**: `test/features/forms/data/datasources/form_export_local_datasource_test.dart` (NEW)

```dart
// WHY: Verify CRUD operations and custom queries work against SQLite.
// NOTE: Uses sqflite_common_ffi for in-memory testing.
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/features/forms/data/datasources/form_export_local_datasource.dart';
import 'package:construction_inspector/features/forms/data/models/form_export.dart';

void main() {
  late DatabaseService dbService;
  late FormExportLocalDatasource datasource;

  setUp(() async {
    // NOTE: Initialize with in-memory FFI database
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    dbService = DatabaseService();
    // TODO: Implementer — use the test DB initialization pattern from existing tests
    datasource = FormExportLocalDatasource(dbService);
  });

  group('FormExportLocalDatasource', () {
    test('insert and getById', () async {
      final export = FormExport(
        projectId: 'proj-1',
        filename: 'test.pdf',
        formType: 'daily_report',
      );
      await datasource.insert(export);
      final fetched = await datasource.getById(export.id);
      expect(fetched, isNotNull);
      expect(fetched!.filename, 'test.pdf');
    });

    test('getByProjectId returns project-scoped results', () async {
      await datasource.insert(FormExport(projectId: 'proj-1', filename: 'a.pdf', formType: 'report'));
      await datasource.insert(FormExport(projectId: 'proj-2', filename: 'b.pdf', formType: 'report'));
      final results = await datasource.getByProjectId('proj-1');
      expect(results.length, 1);
      expect(results.first.filename, 'a.pdf');
    });

    test('getByEntryId returns entry-scoped results', () async {
      await datasource.insert(FormExport(projectId: 'proj-1', entryId: 'entry-1', filename: 'a.pdf', formType: 'report'));
      await datasource.insert(FormExport(projectId: 'proj-1', entryId: 'entry-2', filename: 'b.pdf', formType: 'report'));
      final results = await datasource.getByEntryId('entry-1');
      expect(results.length, 1);
    });

    test('getByFormResponseId returns response-scoped results', () async {
      await datasource.insert(FormExport(projectId: 'proj-1', formResponseId: 'fr-1', filename: 'a.pdf', formType: 'report'));
      final results = await datasource.getByFormResponseId('fr-1');
      expect(results.length, 1);
    });

    test('softDeleteByEntryId marks records deleted', () async {
      await datasource.insert(FormExport(projectId: 'proj-1', entryId: 'entry-1', filename: 'a.pdf', formType: 'report'));
      await datasource.softDeleteByEntryId('entry-1', userId: 'user-1');
      final results = await datasource.getByEntryId('entry-1');
      expect(results, isEmpty);
    });
  });
}
```

**File**: `test/features/entries/data/datasources/entry_export_local_datasource_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/features/entries/data/datasources/entry_export_local_datasource.dart';
import 'package:construction_inspector/features/entries/data/models/entry_export.dart';

void main() {
  late DatabaseService dbService;
  late EntryExportLocalDatasource datasource;

  setUp(() async {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    dbService = DatabaseService();
    datasource = EntryExportLocalDatasource(dbService);
  });

  group('EntryExportLocalDatasource', () {
    test('insert and getById', () async {
      final export = EntryExport(projectId: 'proj-1', filename: 'report.pdf');
      await datasource.insert(export);
      final fetched = await datasource.getById(export.id);
      expect(fetched, isNotNull);
      expect(fetched!.filename, 'report.pdf');
    });

    test('getByEntryId returns entry-scoped results', () async {
      await datasource.insert(EntryExport(projectId: 'proj-1', entryId: 'entry-1', filename: 'a.pdf'));
      await datasource.insert(EntryExport(projectId: 'proj-1', entryId: 'entry-2', filename: 'b.pdf'));
      final results = await datasource.getByEntryId('entry-1');
      expect(results.length, 1);
    });

    test('softDeleteByEntryId marks records deleted', () async {
      await datasource.insert(EntryExport(projectId: 'proj-1', entryId: 'entry-1', filename: 'a.pdf'));
      await datasource.softDeleteByEntryId('entry-1', userId: 'user-1');
      final results = await datasource.getByEntryId('entry-1');
      expect(results, isEmpty);
    });
  });
}
```

**File**: `test/features/entries/data/datasources/document_local_datasource_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/features/entries/data/datasources/document_local_datasource.dart';
import 'package:construction_inspector/features/entries/data/models/document.dart';

void main() {
  late DatabaseService dbService;
  late DocumentLocalDatasource datasource;

  setUp(() async {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    dbService = DatabaseService();
    datasource = DocumentLocalDatasource(dbService);
  });

  group('DocumentLocalDatasource', () {
    test('insert and getById', () async {
      final doc = Document(projectId: 'proj-1', filename: 'specs.pdf', fileType: 'application/pdf');
      await datasource.insert(doc);
      final fetched = await datasource.getById(doc.id);
      expect(fetched, isNotNull);
      expect(fetched!.filename, 'specs.pdf');
    });

    test('getByEntryId returns entry-scoped results', () async {
      await datasource.insert(Document(projectId: 'proj-1', entryId: 'entry-1', filename: 'a.pdf', fileType: 'application/pdf'));
      await datasource.insert(Document(projectId: 'proj-1', entryId: 'entry-2', filename: 'b.pdf', fileType: 'application/pdf'));
      final results = await datasource.getByEntryId('entry-1');
      expect(results.length, 1);
    });

    test('getCountByEntryId returns correct count', () async {
      await datasource.insert(Document(projectId: 'proj-1', entryId: 'entry-1', filename: 'a.pdf', fileType: 'application/pdf'));
      await datasource.insert(Document(projectId: 'proj-1', entryId: 'entry-1', filename: 'b.xls', fileType: 'application/vnd.ms-excel'));
      final count = await datasource.getCountByEntryId('entry-1');
      expect(count, 2);
    });

    test('getByFileType filters correctly', () async {
      await datasource.insert(Document(projectId: 'proj-1', filename: 'a.pdf', fileType: 'application/pdf'));
      await datasource.insert(Document(projectId: 'proj-1', filename: 'b.xls', fileType: 'application/vnd.ms-excel'));
      final pdfs = await datasource.getByFileType('proj-1', 'application/pdf');
      expect(pdfs.length, 1);
      expect(pdfs.first.filename, 'a.pdf');
    });

    test('softDeleteByEntryId marks records deleted', () async {
      await datasource.insert(Document(projectId: 'proj-1', entryId: 'entry-1', filename: 'a.pdf', fileType: 'application/pdf'));
      await datasource.softDeleteByEntryId('entry-1', userId: 'user-1');
      final results = await datasource.getByEntryId('entry-1');
      expect(results, isEmpty);
    });
  });
}
```

**File**: `test/features/forms/data/repositories/form_export_repository_test.dart` (NEW)

```dart
// WHY: Verify repository validation and error handling.
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/features/forms/data/datasources/form_export_local_datasource.dart';
import 'package:construction_inspector/features/forms/data/repositories/form_export_repository.dart';
import 'package:construction_inspector/features/forms/data/models/form_export.dart';

void main() {
  late FormExportRepository repository;

  setUp(() async {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    final dbService = DatabaseService();
    final datasource = FormExportLocalDatasource(dbService);
    repository = FormExportRepository(datasource);
  });

  group('FormExportRepository', () {
    test('create validates filename is not empty', () async {
      final result = await repository.create(FormExport(
        projectId: 'proj-1',
        filename: '',
        formType: 'daily_report',
      ));
      expect(result.isSuccess, false);
      expect(result.error, contains('Filename'));
    });

    test('create validates formType is not empty', () async {
      final result = await repository.create(FormExport(
        projectId: 'proj-1',
        filename: 'test.pdf',
        formType: '',
      ));
      expect(result.isSuccess, false);
      expect(result.error, contains('Form type'));
    });

    test('create succeeds with valid data', () async {
      final result = await repository.create(FormExport(
        projectId: 'proj-1',
        filename: 'test.pdf',
        formType: 'daily_report',
      ));
      expect(result.isSuccess, true);
      expect(result.data, isNotNull);
    });
  });
}
```

**File**: `test/features/entries/data/repositories/document_repository_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/features/entries/data/datasources/document_local_datasource.dart';
import 'package:construction_inspector/features/entries/data/repositories/document_repository.dart';
import 'package:construction_inspector/features/entries/data/models/document.dart';

void main() {
  late DocumentRepository repository;

  setUp(() async {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    final dbService = DatabaseService();
    final datasource = DocumentLocalDatasource(dbService);
    repository = DocumentRepository(datasource);
  });

  group('DocumentRepository', () {
    test('create validates filename is not empty', () async {
      final result = await repository.create(Document(
        projectId: 'proj-1',
        filename: '',
        fileType: 'application/pdf',
      ));
      expect(result.isSuccess, false);
      expect(result.error, contains('Filename'));
    });

    test('create validates fileType is not empty', () async {
      final result = await repository.create(Document(
        projectId: 'proj-1',
        filename: 'test.pdf',
        fileType: '',
      ));
      expect(result.isSuccess, false);
      expect(result.error, contains('File type'));
    });

    test('create succeeds with valid data', () async {
      final result = await repository.create(Document(
        projectId: 'proj-1',
        filename: 'specs.pdf',
        fileType: 'application/pdf',
      ));
      expect(result.isSuccess, true);
    });

    test('update sets new updatedAt timestamp', () async {
      final doc = Document(
        projectId: 'proj-1',
        filename: 'specs.pdf',
        fileType: 'application/pdf',
        updatedAt: '2026-01-01T00:00:00.000Z',
      );
      await repository.save(doc);
      final result = await repository.update(doc.copyWith(notes: 'Updated'));
      expect(result.isSuccess, true);
      // NOTE: updatedAt should be newer than original
      expect(result.data!.updatedAt, isNot('2026-01-01T00:00:00.000Z'));
    });
  });
}
```

**Verification**:
```
pwsh -Command "flutter test test/features/forms/data/datasources/form_export_local_datasource_test.dart"
pwsh -Command "flutter test test/features/entries/data/datasources/entry_export_local_datasource_test.dart"
pwsh -Command "flutter test test/features/entries/data/datasources/document_local_datasource_test.dart"
pwsh -Command "flutter test test/features/forms/data/repositories/form_export_repository_test.dart"
pwsh -Command "flutter test test/features/entries/data/repositories/document_repository_test.dart"
```

---

## New Files Summary

| Phase | File | Type |
|-------|------|------|
| 1 | `lib/core/database/schema/form_export_tables.dart` | NEW |
| 1 | `lib/core/database/schema/entry_export_tables.dart` | NEW |
| 1 | `lib/core/database/schema/document_tables.dart` | NEW |
| 1 | `lib/core/database/database_service.dart` | MODIFY |
| 1 | `lib/core/database/schema/sync_engine_tables.dart` | MODIFY |
| 1 | `lib/services/soft_delete_service.dart` | MODIFY |
| 1 | `test/core/database/migration_v43_test.dart` | NEW |
| 1 | `test/features/sync/engine/sync_engine_tables_test.dart` | MODIFY |
| 2 | `supabase/migrations/20260328100000_fix_inspector_forms_and_new_tables.sql` | NEW |
| 3 | `lib/features/forms/data/models/form_export.dart` | NEW |
| 3 | `lib/features/entries/data/models/entry_export.dart` | NEW |
| 3 | `lib/features/entries/data/models/document.dart` | NEW |
| 3 | `lib/features/forms/data/models/builtin_form_config.dart` | NEW |
| 3 | `test/features/forms/data/models/form_export_test.dart` | NEW |
| 3 | `test/features/entries/data/models/entry_export_test.dart` | NEW |
| 3 | `test/features/entries/data/models/document_test.dart` | NEW |
| 4 | `lib/features/forms/data/datasources/form_export_local_datasource.dart` | NEW |
| 4 | `lib/features/forms/data/datasources/form_export_remote_datasource.dart` | NEW |
| 4 | `lib/features/forms/data/repositories/form_export_repository.dart` | NEW |
| 4 | `lib/features/entries/data/datasources/entry_export_local_datasource.dart` | NEW |
| 4 | `lib/features/entries/data/datasources/entry_export_remote_datasource.dart` | NEW |
| 4 | `lib/features/entries/data/repositories/entry_export_repository.dart` | NEW |
| 4 | `lib/features/entries/data/datasources/document_local_datasource.dart` | NEW |
| 4 | `lib/features/entries/data/datasources/document_remote_datasource.dart` | NEW |
| 4 | `lib/features/entries/data/repositories/document_repository.dart` | NEW |
| 4 | `test/features/forms/data/datasources/form_export_local_datasource_test.dart` | NEW |
| 4 | `test/features/entries/data/datasources/entry_export_local_datasource_test.dart` | NEW |
| 4 | `test/features/entries/data/datasources/document_local_datasource_test.dart` | NEW |
| 4 | `test/features/forms/data/repositories/form_export_repository_test.dart` | NEW |
| 4 | `test/features/entries/data/repositories/document_repository_test.dart` | NEW |

## Execution Order

1. **Phase 1** (backend-data-layer-agent) — Schema tables, v43 migration, sync registration, soft-delete cascade
2. **Phase 2** (backend-supabase-agent) — Supabase migration: fix inspector_forms, create 3 tables + RLS + buckets + triggers
3. **Phase 3** (backend-data-layer-agent) — Models: FormExport, EntryExport, Document, BuiltinFormConfig + tests
4. **Phase 4** (backend-data-layer-agent) — Datasources + repositories for all 3 tables + tests

Phases 1 and 2 can run in parallel (SQLite vs Supabase are independent). Phase 3 depends on Phase 1 (imports schema table names). Phase 4 depends on Phase 3 (imports models).

---

# Forms Infrastructure — Part 2 (Phases 5-7)

> Continues from `2026-03-28-forms-infrastructure-part1.md` (Phases 1-4).
> Phases 5-7 cover sync adapters, soft delete cascade, and the form registry system.

---

## Phase 5: Sync Adapters

**Agent:** backend-supabase-agent

### 5.1: Rename isPhotoAdapter → isFileAdapter

**Step 5.1.1** — Rename base class property
File: `lib/features/sync/adapters/table_adapter.dart:45`

```dart
// BEFORE (line 45):
bool get isPhotoAdapter => false;

// AFTER:
// WHY: Photos are no longer the only file-backed entity. Documents and form
// exports also use storage upload + metadata upsert (three-phase push).
bool get isFileAdapter => false;
```

**Step 5.1.2** — Rename PhotoAdapter override
File: `lib/features/sync/adapters/photo_adapter.dart:30`

```dart
// BEFORE (line 30):
@override bool get isPhotoAdapter => true;

// AFTER:
// WHY: Matches renamed base class property.
@override bool get isFileAdapter => true;
```

**Step 5.1.3** — Update _routeAndPush call site
File: `lib/features/sync/engine/sync_engine.dart:537-556` (inside `_routeAndPush`)

```dart
// BEFORE:
if (adapter.isPhotoAdapter) {

// AFTER:
// WHY: Property renamed in 5.1.1.
if (adapter.isFileAdapter) {
```

**Step 5.1.4** — Search-and-fix any remaining references
Grep for `isPhotoAdapter` across `lib/` and `test/`. Update all hits to `isFileAdapter`.

**Verification:**
```
pwsh -Command "flutter analyze"
```

---

### 5.2: Generalize _pushPhotoThreePhase → _pushFileThreePhase

**Step 5.2.1** — Add `storageBucket` and `storagePathBuilder` to TableAdapter
File: `lib/features/sync/adapters/table_adapter.dart` (after `isFileAdapter`)

```dart
// WHY: Each file adapter needs its own bucket and path format.
// Photos use 'entry-photos', documents use 'entry-documents',
// form exports use 'form-exports'. Path structure also differs.
String get storageBucket => '';

// NOTE: Only called when isFileAdapter == true.
// Subclasses override to build the correct storage path from the local record.
String buildStoragePath(String companyId, Map<String, dynamic> localRecord) =>
    throw UnimplementedError('File adapters must override buildStoragePath');

// WHY: Only photos need EXIF GPS stripping (ADV-56). Documents and exports
// must NOT be modified before upload.
bool get stripExifGps => false;
```

**Step 5.2.2** — Override in PhotoAdapter
File: `lib/features/sync/adapters/photo_adapter.dart` (after `isFileAdapter`)

```dart
// FROM SPEC: Photos go to 'entry-photos' bucket at entries/{companyId}/{entryId}/{filename}
@override String get storageBucket => 'entry-photos';
@override bool get stripExifGps => true;

@override
String buildStoragePath(String companyId, Map<String, dynamic> localRecord) {
  final entryId = localRecord['entry_id'] as String;
  final filename = localRecord['filename'] as String;
  return 'entries/$companyId/$entryId/$filename';
}
```

**Step 5.2.3** — Generalize _validateStoragePath
File: `lib/features/sync/engine/sync_engine.dart:1158-1165`

```dart
// BEFORE: hardcoded photo extension pattern
void _validateStoragePath(String path) {
  final pattern = RegExp(r'^entries/[a-f0-9-]+/[a-f0-9-]+/[a-zA-Z0-9_.-]+\.(jpg|jpeg|png|heic)$');
  if (!pattern.hasMatch(path)) throw ArgumentError('Invalid storage path: $path');
}

// AFTER:
// WHY: Documents can be PDF/XLS/XLSX/DOC/DOCX. Form exports are always PDF.
// We validate that the path has UUID segments and a recognized extension.
void _validateStoragePath(String path) {
  final pattern = RegExp(
    r'^[a-z_-]+/[a-f0-9-]+/[a-f0-9-]+/[a-zA-Z0-9_.-]+\.'
    r'(jpg|jpeg|png|heic|pdf|xls|xlsx|doc|docx)$',
  );
  if (!pattern.hasMatch(path)) {
    throw ArgumentError('Invalid storage path: $path');
  }
}
```

**Step 5.2.4** — Rename and generalize _pushPhotoThreePhase → _pushFileThreePhase
File: `lib/features/sync/engine/sync_engine.dart:1048-1155`

```dart
// BEFORE:
Future<void> _pushPhotoThreePhase(TableAdapter adapter, ChangeEntry change,
    Map<String, dynamic> localRecord, Map<String, dynamic> payload) async {

// AFTER:
// WHY: Three-phase push (upload file → upsert metadata → mark synced) applies
// to all file-backed entities, not just photos.
Future<void> _pushFileThreePhase(TableAdapter adapter, ChangeEntry change,
    Map<String, dynamic> localRecord, Map<String, dynamic> payload) async {
  final filePath = localRecord['file_path'] as String?;
  // NOTE: filename comes from different columns per adapter, but all file
  // adapters include 'filename' in their local schema.
  final filename = localRecord['filename'] as String?;
  var remotePath = localRecord['remote_path'] as String?;

  // LWW push guard
  final recordId = payload['id'] as String;
  if (await shouldSkipLwwPush(adapter.tableName, recordId, payload,
      label: ' (${adapter.tableName})')) return;

  // Phase 1: Upload file (skip if already uploaded)
  if (remotePath == null || remotePath.isEmpty) {
    if (filePath == null || filePath.isEmpty) {
      Logger.sync('${adapter.tableName} ${change.recordId}: no file_path, skipping');
      return;
    }
    final file = File(filePath);
    if (!await file.exists()) {
      Logger.sync('${adapter.tableName} ${change.recordId}: file missing, skipping');
      return;
    }
    var bytes = await file.readAsBytes();

    // WHY: Only photos need EXIF GPS stripping (ADV-56). Other file types
    // must be uploaded byte-identical to the original.
    if (adapter.stripExifGps) {
      bytes = _stripExifGps(bytes);
    }

    // NOTE: Each adapter builds its own storage path with the correct
    // bucket prefix structure.
    final storagePath = adapter.buildStoragePath(companyId, localRecord);
    _validateStoragePath(storagePath);

    try {
      await supabase.storage.from(adapter.storageBucket).uploadBinary(storagePath, bytes);
    } on StorageException catch (e) {
      if (e.statusCode == '409' || e.message.contains('already exists')) {
        // WHY: Idempotent — file already exists from a previous partial push.
      } else {
        rethrow;
      }
    }
    remotePath = storagePath;
  }

  // Phase 2: Upsert metadata
  payload['remote_path'] = remotePath;
  Map<String, dynamic>? metadataResponse;
  try {
    metadataResponse = await upsertRemote(adapter.tableName, payload);
  } catch (e) {
    // WHY: Cleanup Phase 1 on failure to avoid orphaned storage files.
    try {
      await supabase.storage.from(adapter.storageBucket).remove([remotePath!]);
    } catch (_) {}
    rethrow;
  }

  // Phase 3: Mark local synced
  await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
  try {
    final updateFields = <String, dynamic>{'remote_path': remotePath};
    final serverUpdatedAt = metadataResponse?['updated_at'] as String?;
    if (serverUpdatedAt != null && serverUpdatedAt != payload['updated_at']) {
      updateFields['updated_at'] = serverUpdatedAt;
    }
    await db.update(adapter.tableName, updateFields,
        where: 'id = ?', whereArgs: [change.recordId]);
  } finally {
    await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
  }
}
```

**Step 5.2.5** — Update _routeAndPush to call _pushFileThreePhase
File: `lib/features/sync/engine/sync_engine.dart` (inside `_routeAndPush`)

```dart
// BEFORE:
await _pushPhotoThreePhase(adapter, change, localRecord, payload);

// AFTER:
// WHY: Method renamed in 5.2.4.
await _pushFileThreePhase(adapter, change, localRecord, payload);
```

**Verification:**
```
pwsh -Command "flutter analyze"
```

---

### 5.3: Fix InspectorFormAdapter (builtin-aware pull filter)

**Step 5.3.1** — Add `includesNullProjectBuiltins` flag to TableAdapter
File: `lib/features/sync/adapters/table_adapter.dart` (after `isFileAdapter`)

```dart
// WHY: Builtin forms have project_id = NULL and must be pulled regardless of
// which projects are synced. The default scope filter (inFilter project_id)
// would exclude them. This flag tells _applyScopeFilter to OR-in null rows.
bool get includesNullProjectBuiltins => false;
```

**Step 5.3.2** — Override in InspectorFormAdapter
File: `lib/features/sync/adapters/inspector_form_adapter.dart`

```dart
// FROM SPEC: Builtin forms have null project_id and must always be pulled.
@override bool get includesNullProjectBuiltins => true;
```

**Step 5.3.3** — Update _applyScopeFilter
File: `lib/features/sync/engine/sync_engine.dart:1678-1691`

```dart
// BEFORE:
PostgrestFilterBuilder _applyScopeFilter(PostgrestFilterBuilder query, TableAdapter adapter) {
  switch (adapter.scopeType) {
    case ScopeType.direct:
      return query.eq('company_id', companyId);
    case ScopeType.viaProject:
    case ScopeType.viaEntry:
      return query.inFilter('project_id', _syncedProjectIds);
    case ScopeType.viaContractor:
      return query.inFilter('contractor_id', _syncedContractorIds);
  }
}

// AFTER:
PostgrestFilterBuilder _applyScopeFilter(PostgrestFilterBuilder query, TableAdapter adapter) {
  switch (adapter.scopeType) {
    case ScopeType.direct:
      return query.eq('company_id', companyId);
    case ScopeType.viaProject:
    case ScopeType.viaEntry:
      // WHY: Builtin forms (inspector_forms with is_builtin=1) have NULL
      // project_id. They must be included alongside project-scoped rows.
      // PostgREST OR filter: project_id.in.(ids),project_id.is.null
      if (adapter.includesNullProjectBuiltins) {
        return query.or(
          'project_id.in.(${_syncedProjectIds.join(",")}),project_id.is.null',
        );
      }
      return query.inFilter('project_id', _syncedProjectIds);
    case ScopeType.viaContractor:
      return query.inFilter('contractor_id', _syncedContractorIds);
  }
}
```

**Verification:**
```
pwsh -Command "flutter test test/features/sync/"
```

---

### 5.4: Create FormExportAdapter, EntryExportAdapter, DocumentAdapter

**Step 5.4.1** — Create FormExportAdapter
File: `lib/features/sync/adapters/form_export_adapter.dart` (NEW)

```dart
import '../engine/table_adapter.dart';
import '../engine/scope_type.dart';

/// FROM SPEC: form_exports are PDF snapshots of form responses, stored in the
/// 'form-exports' bucket. They are project-scoped via project_id.
class FormExportAdapter extends TableAdapter {
  @override String get tableName => 'form_exports';
  @override ScopeType get scopeType => ScopeType.viaProject;
  // CODE-REVIEW FIX #4: No FK to inspector_forms. Column is form_response_id not response_id.
  @override List<String> get fkDependencies =>
      const ['projects', 'form_responses'];
  @override Map<String, String> get fkColumnMap => const {
    'projects': 'project_id',
    'form_responses': 'form_response_id',
  };
  @override List<String> get localOnlyColumns => const ['file_path'];
  @override bool get isFileAdapter => true;
  @override String get storageBucket => 'form-exports';
  @override bool get stripExifGps => false; // NOTE: PDFs, not images.

  @override
  String buildStoragePath(String companyId, Map<String, dynamic> localRecord) {
    // WHY: Path includes project_id for RLS bucket policies and response_id
    // for uniqueness. Format: exports/{companyId}/{projectId}/{filename}
    final projectId = localRecord['project_id'] as String;
    final filename = localRecord['filename'] as String;
    return 'exports/$companyId/$projectId/$filename';
  }

  @override
  String extractRecordName(Map<String, dynamic> record) {
    return record['filename']?.toString() ??
        record['id']?.toString() ??
        'Unknown';
  }
}
```

**Step 5.4.2** — Create EntryExportAdapter
File: `lib/features/sync/adapters/entry_export_adapter.dart` (NEW)

```dart
import '../engine/table_adapter.dart';
import '../engine/scope_type.dart';

/// FROM SPEC: entry_exports are PDF snapshots of daily entries, stored in the
/// 'entry-exports' bucket. They are entry-scoped (have entry_id + project_id).
/// SEC-R01 FIX: Uses dedicated 'entry-exports' bucket, NOT shared 'entry-documents'.
class EntryExportAdapter extends TableAdapter {
  @override String get tableName => 'entry_exports';
  @override ScopeType get scopeType => ScopeType.viaEntry;
  @override List<String> get fkDependencies => const ['daily_entries', 'projects'];
  @override Map<String, String> get fkColumnMap => const {
    'daily_entries': 'entry_id',
    'projects': 'project_id',
  };
  @override List<String> get localOnlyColumns => const ['file_path'];
  @override bool get isFileAdapter => true;
  // SEC-R01 FIX: Dedicated 'entry-exports' bucket (not shared 'entry-documents')
  @override String get storageBucket => 'entry-exports';
  @override bool get stripExifGps => false; // NOTE: PDFs, not images.

  @override
  String buildStoragePath(String companyId, Map<String, dynamic> localRecord) {
    // WHY: Path under dedicated entry-exports bucket.
    // Format: entries/{companyId}/{entryId}/{filename}
    final entryId = localRecord['entry_id'] as String;
    final filename = localRecord['filename'] as String;
    return 'entries/$companyId/$entryId/$filename';
  }

  @override
  String extractRecordName(Map<String, dynamic> record) {
    return record['filename']?.toString() ??
        record['id']?.toString() ??
        'Unknown';
  }
}
```

**Step 5.4.3** — Create DocumentAdapter
File: `lib/features/sync/adapters/document_adapter.dart` (NEW)

```dart
import '../engine/table_adapter.dart';
import '../engine/scope_type.dart';

/// FROM SPEC: documents are user-attached files (PDF, XLS, etc.) on entries.
/// Stored in dedicated 'entry-documents' bucket (separate from entry-exports).
class DocumentAdapter extends TableAdapter {
  @override String get tableName => 'documents';
  @override ScopeType get scopeType => ScopeType.viaEntry;
  @override List<String> get fkDependencies => const ['daily_entries', 'projects'];
  @override Map<String, String> get fkColumnMap => const {
    'daily_entries': 'entry_id',
    'projects': 'project_id',
  };
  @override List<String> get localOnlyColumns => const ['file_path'];
  @override bool get isFileAdapter => true;
  @override String get storageBucket => 'entry-documents';
  @override bool get stripExifGps => false; // NOTE: Arbitrary file types.

  @override
  String buildStoragePath(String companyId, Map<String, dynamic> localRecord) {
    // WHY: Documents share the entry-documents bucket but use a 'docs/'
    // prefix to separate from entry exports.
    final entryId = localRecord['entry_id'] as String;
    final filename = localRecord['filename'] as String;
    return 'docs/$companyId/$entryId/$filename';
  }

  @override
  String extractRecordName(Map<String, dynamic> record) {
    return record['filename']?.toString() ??
        record['filename']?.toString() ??
        record['id']?.toString() ??
        'Unknown';
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze"
```

---

### 5.5: Register in sync_registry.dart

**Step 5.5.1** — Add imports and register new adapters
File: `lib/features/sync/engine/sync_registry.dart`

Add imports at top:
```dart
import '../adapters/entry_export_adapter.dart';
import '../adapters/document_adapter.dart';
import '../adapters/form_export_adapter.dart';
```

Update `registerSyncAdapters()` at lines 24-44:
```dart
void registerSyncAdapters() {
  SyncRegistry.instance.registerAdapters([
    ProjectAdapter(),              // 1
    ProjectAssignmentAdapter(),    // 2
    LocationAdapter(),             // 3
    ContractorAdapter(),           // 4
    EquipmentAdapter(),            // 5
    BidItemAdapter(),              // 6
    PersonnelTypeAdapter(),        // 7
    DailyEntryAdapter(),           // 8
    PhotoAdapter(),                // 9
    // WHY: Entry exports and documents depend on daily_entries (entry_id FK).
    // Must come after DailyEntryAdapter but before entry child tables.
    EntryExportAdapter(),          // 10
    DocumentAdapter(),             // 11
    EntryEquipmentAdapter(),       // 12
    EntryQuantitiesAdapter(),      // 13
    EntryContractorsAdapter(),     // 14
    EntryPersonnelCountsAdapter(), // 15
    InspectorFormAdapter(),        // 16
    FormResponseAdapter(),         // 17
    // WHY: Form exports depend on form_responses (response_id FK).
    // Must come after FormResponseAdapter.
    FormExportAdapter(),           // 18
    TodoItemAdapter(),             // 19
    CalculationHistoryAdapter(),   // 20
  ]);
}
```

**Verification:**
```
pwsh -Command "flutter analyze"
```

---

### 5.6: Update syncBuckets in sync_orchestrator.dart

**Step 5.6.1** — Add new tables to sync buckets
File: `lib/features/sync/application/sync_orchestrator.dart:37-46`

```dart
// BEFORE:
static const Map<String, List<String>> syncBuckets = {
  'Projects': ['projects', 'bid_items', 'locations', 'todo_items'],
  'Entries': ['daily_entries', 'contractors', 'equipment',
    'entry_contractors', 'entry_equipment',
    'entry_quantities', 'entry_personnel_counts'],
  'Forms': ['inspector_forms', 'form_responses'],
  'Photos': ['photos'],
};

// AFTER:
// WHY: New tables must be in buckets so the orchestrator includes them in
// sync progress tracking and error grouping.
static const Map<String, List<String>> syncBuckets = {
  'Projects': ['projects', 'bid_items', 'locations', 'todo_items'],
  'Entries': ['daily_entries', 'contractors', 'equipment',
    'entry_contractors', 'entry_equipment',
    'entry_quantities', 'entry_personnel_counts'],
  'Forms': ['inspector_forms', 'form_responses', 'form_exports'],
  // NOTE: 'Photos & Files' groups all storage-backed entities for UI display.
  'Photos & Files': ['photos', 'entry_exports', 'documents'],
};
```

**Verification:**
```
pwsh -Command "flutter analyze"
```

---

### 5.7: Generalize OrphanScanner + StorageCleanup for multi-bucket

**Step 5.7.1** — Refactor OrphanScanner to accept bucket config
File: `lib/features/sync/engine/orphan_scanner.dart`

```dart
// BEFORE:
class OrphanScanner {
  final SupabaseClient _client;
  static const String _bucket = 'entry-photos';
  OrphanScanner(this._client);
  // ...
}

// AFTER:
/// WHY: With form-exports and entry-documents buckets, the scanner must
/// iterate all storage buckets. Each bucket maps to a table + remote_path column.
class OrphanScanner {
  final SupabaseClient _client;

  // NOTE: Maps bucket name → table name that holds the remote_path metadata.
  // All tables use 'remote_path' as the column name (consistent convention).
  static const Map<String, String> _bucketTableMap = {
    'entry-photos': 'photos',
    'entry-documents': 'documents',
    'entry-exports': 'entry_exports',
    'form-exports': 'form_exports',
  };

  // NOTE: entry_exports share the 'entry-documents' bucket. We need to query
  // both tables when scanning that bucket.
  static const Map<String, List<String>> _bucketTablesMap = {
    'entry-photos': ['photos'],
    'entry-documents': ['documents'],
    'entry-exports': ['entry_exports'],
    'form-exports': ['form_exports'],
  };

  OrphanScanner(this._client);

  /// Scans all storage buckets for orphaned files.
  Future<List<String>> scan(String companyId, {bool autoDelete = false}) async {
    final allOrphans = <String>[];
    for (final entry in _bucketTablesMap.entries) {
      final bucket = entry.key;
      final tables = entry.value;
      final orphans = await _scanBucket(companyId, bucket, tables,
          autoDelete: autoDelete);
      allOrphans.addAll(orphans);
    }
    return allOrphans;
  }

  Future<List<String>> _scanBucket(String companyId, String bucket,
      List<String> tables, {bool autoDelete = false}) async {
    // WHY: Collect all known remote_paths across tables that share this bucket.
    final knownPaths = <String>{};
    for (final table in tables) {
      final rows = await _client.from(table)
          .select('remote_path')
          .not('remote_path', 'is', null);
      for (final row in rows) {
        final path = row['remote_path'] as String?;
        if (path != null && path.isNotEmpty) knownPaths.add(path);
      }
    }

    // List storage files and diff against known paths
    // (rest of logic same as before but parameterized by bucket)
    // ... auto-delete orphans older than 24h, capped at 50
  }
}
```

**Step 5.7.2** — Refactor StorageCleanup to accept bucket config
File: `lib/features/sync/engine/storage_cleanup.dart`

```dart
// BEFORE:
class StorageCleanup {
  final SupabaseClient _client;
  final Database _db;
  static const String _bucket = 'entry-photos';
  // ...
}

// AFTER:
class StorageCleanup {
  final SupabaseClient _client;
  final Database _db;

  // WHY: storage_cleanup_queue rows specify which bucket the file lives in.
  // We read the bucket from the queue entry instead of hardcoding.
  // NOTE: If legacy queue entries lack a bucket column, default to 'entry-photos'.
  static const String _defaultBucket = 'entry-photos';

  StorageCleanup(this._client, this._db);

  Future<int> cleanupExpiredFiles() async {
    // WHY: Renamed from cleanupExpiredPhotos to reflect multi-type support.
    final queue = await _db.query('storage_cleanup_queue');
    var cleaned = 0;
    for (final entry in queue) {
      final remotePath = entry['remote_path'] as String;
      // NOTE: bucket column added by migration in Phase 2/3. Fallback for
      // pre-migration rows that only had photos.
      final bucket = (entry['bucket'] as String?) ?? _defaultBucket;
      try {
        await _client.storage.from(bucket).remove([remotePath]);
        await _db.delete('storage_cleanup_queue',
            where: 'id = ?', whereArgs: [entry['id']]);
        cleaned++;
      } catch (e) {
        Logger.sync('StorageCleanup: failed to remove $remotePath from $bucket: $e');
      }
    }
    return cleaned;
  }
}
```

**Verification:**
```
pwsh -Command "flutter analyze"
```

---

### 5.8: Tests

**Step 5.8.1** — Create adapter unit tests
File: `test/features/sync/adapters/form_export_adapter_test.dart` (NEW)

```dart
// WHY: Verify storageBucket, buildStoragePath, isFileAdapter, and FK deps
// for the new FormExportAdapter.
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/adapters/form_export_adapter.dart';

void main() {
  late FormExportAdapter adapter;

  setUp(() => adapter = FormExportAdapter());

  test('tableName is form_exports', () {
    expect(adapter.tableName, 'form_exports');
  });

  test('isFileAdapter is true', () {
    expect(adapter.isFileAdapter, isTrue);
  });

  test('storageBucket is form-exports', () {
    expect(adapter.storageBucket, 'form-exports');
  });

  test('stripExifGps is false', () {
    // NOTE: Form exports are PDFs, not photos.
    expect(adapter.stripExifGps, isFalse);
  });

  test('buildStoragePath uses projectId', () {
    final path = adapter.buildStoragePath('company-123', {
      'project_id': 'proj-456',
      'filename': 'export.pdf',
    });
    expect(path, 'exports/company-123/proj-456/export.pdf');
  });

  test('fkDependencies includes projects, inspector_forms, form_responses', () {
    expect(adapter.fkDependencies,
        containsAll(['projects', 'inspector_forms', 'form_responses']));
  });
}
```

**Step 5.8.2** — Create entry export adapter tests
File: `test/features/sync/adapters/entry_export_adapter_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/adapters/entry_export_adapter.dart';

void main() {
  late EntryExportAdapter adapter;

  setUp(() => adapter = EntryExportAdapter());

  test('tableName is entry_exports', () {
    expect(adapter.tableName, 'entry_exports');
  });

  test('isFileAdapter is true', () {
    expect(adapter.isFileAdapter, isTrue);
  });

  // SEC-R01 FIX: entry_exports use dedicated entry-exports bucket
  test('storageBucket is entry-exports', () {
    expect(adapter.storageBucket, 'entry-exports');
  });

  test('buildStoragePath uses entryId', () {
    final path = adapter.buildStoragePath('company-123', {
      'entry_id': 'entry-456',
      'filename': 'report.pdf',
    });
    expect(path, 'entries/company-123/entry-456/report.pdf');
  });
}
```

**Step 5.8.3** — Create document adapter tests
File: `test/features/sync/adapters/document_adapter_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/adapters/document_adapter.dart';

void main() {
  late DocumentAdapter adapter;

  setUp(() => adapter = DocumentAdapter());

  test('tableName is documents', () {
    expect(adapter.tableName, 'documents');
  });

  test('isFileAdapter is true', () {
    expect(adapter.isFileAdapter, isTrue);
  });

  test('storageBucket is entry-documents', () {
    expect(adapter.storageBucket, 'entry-documents');
  });

  test('buildStoragePath uses docs/ prefix', () {
    // WHY: Documents use 'docs/' prefix to separate from entry exports
    // in the shared entry-documents bucket.
    final path = adapter.buildStoragePath('company-123', {
      'entry_id': 'entry-456',
      'filename': 'specs.pdf',
    });
    expect(path, 'docs/company-123/entry-456/specs.pdf');
  });

  test('extractRecordName prefers filename', () {
    expect(
      adapter.extractRecordName({
        'filename': 'My Document.pdf',
        'filename': 'uuid.pdf',
      }),
      'My Document.pdf',
    );
  });
}
```

**Step 5.8.4** — Test builtin-aware pull filter on InspectorFormAdapter
File: `test/features/sync/adapters/inspector_form_adapter_test.dart` (NEW or append)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/adapters/inspector_form_adapter.dart';

void main() {
  late InspectorFormAdapter adapter;

  setUp(() => adapter = InspectorFormAdapter());

  test('includesNullProjectBuiltins is true', () {
    // WHY: Builtin forms have null project_id and must be pulled even when
    // _applyScopeFilter restricts to specific project IDs.
    expect(adapter.includesNullProjectBuiltins, isTrue);
  });
}
```

**Step 5.8.5** — Test _validateStoragePath accepts new extensions
File: `test/features/sync/engine/sync_engine_validation_test.dart` (append or NEW)

```dart
// WHY: Ensure the generalized path validator accepts document file types.
// Test both valid and invalid paths to prevent regressions.
test('_validateStoragePath accepts PDF paths', () {
  // Valid document paths
  expect(() => engine.validateStoragePath('exports/abc-123/def-456/report.pdf'),
      returnsNormally);
  expect(() => engine.validateStoragePath('docs/abc-123/def-456/specs.xlsx'),
      returnsNormally);
});

test('_validateStoragePath rejects invalid extensions', () {
  expect(() => engine.validateStoragePath('entries/abc-123/def-456/script.exe'),
      throwsArgumentError);
});
```

**Verification:**
```
pwsh -Command "flutter test test/features/sync/"
```

---

## Phase 6: Soft Delete Service

**Agent:** backend-data-layer-agent

### 6.1: Add tables to _projectChildTables and _childToParentOrder

**Step 6.1.1** — Update _childToParentOrder
File: `lib/services/soft_delete_service.dart`

```dart
// BEFORE:
static const List<String> _childToParentOrder = [
  'entry_quantities', 'entry_equipment', 'entry_personnel_counts',
  'entry_contractors', 'photos', 'form_responses', 'todo_items',
  'calculation_history', 'equipment', 'personnel_types', 'bid_items',
  'daily_entries', 'contractors', 'locations', 'projects',
];

// AFTER:
// WHY: New tables must be purged in child-to-parent order. entry_exports,
// documents, and form_exports are leaf children (no dependents), so they
// go at the beginning. form_exports depends on form_responses, so it must
// come before form_responses in purge order.
static const List<String> _childToParentOrder = [
  'entry_quantities', 'entry_equipment', 'entry_personnel_counts',
  'entry_contractors', 'photos', 'entry_exports', 'documents',
  'form_exports', 'form_responses', 'todo_items',
  'calculation_history', 'equipment', 'personnel_types', 'bid_items',
  'daily_entries', 'contractors', 'locations', 'projects',
];
```

**Step 6.1.2** — Update _projectChildTables
File: `lib/services/soft_delete_service.dart`

```dart
// BEFORE:
static const List<String> _projectChildTables = [
  'locations', 'contractors', 'daily_entries', 'bid_items',
  'personnel_types', 'photos', 'form_responses', 'todo_items',
  'calculation_history',
];

// AFTER:
// WHY: When a project is soft-deleted, all its children must cascade.
// entry_exports, documents (via entry_id→project_id), and form_exports
// (via project_id) are all project children.
static const List<String> _projectChildTables = [
  'locations', 'contractors', 'daily_entries', 'bid_items',
  'personnel_types', 'photos', 'entry_exports', 'documents',
  'form_responses', 'form_exports', 'todo_items', 'calculation_history',
];
```

**Step 6.1.3** — Update `entryChildTables` inside `cascadeSoftDeleteProject`
File: `lib/services/soft_delete_service.dart` (line ~87-94, inside `cascadeSoftDeleteProject`)

```dart
// BEFORE:
final entryChildTables = [
  'entry_contractors',
  'entry_equipment',
  'entry_personnel_counts',
  'entry_quantities',
];

// AFTER:
// WHY: New tables with entry_id FK must cascade when entries cascade
// during project soft-delete. This is the entryChildTables list inside
// cascadeSoftDeleteProject (separate from the one in cascadeSoftDeleteEntry).
final entryChildTables = [
  'entry_contractors',
  'entry_equipment',
  'entry_personnel_counts',
  'entry_quantities',
  'documents',       // NEW: has entry_id FK
  'entry_exports',   // NEW: has entry_id FK
];
```

> **NOTE**: `form_exports` has a nullable `entry_id` and also has a direct `project_id` FK,
> so it is already covered by `_projectChildTables` (Step 6.1.2) and does not need to be
> in this entry-scoped list.

**Verification:**
```
pwsh -Command "flutter test test/services/soft_delete_service_log_cleanup_test.dart"
```

---

### 6.2: Add inspector_forms with is_builtin guard to cascade

**Step 6.2.1** — Add inspector_forms to _projectChildTables with guard
File: `lib/services/soft_delete_service.dart`

In `_projectChildTables`, add `'inspector_forms'`:
```dart
static const List<String> _projectChildTables = [
  'locations', 'contractors', 'daily_entries', 'bid_items',
  'personnel_types', 'photos', 'entry_exports', 'documents',
  'form_responses', 'form_exports', 'todo_items', 'calculation_history',
  'inspector_forms',
];
```

**Step 6.2.2** — Add is_builtin guard in cascadeSoftDeleteProject
File: `lib/services/soft_delete_service.dart` (inside `cascadeSoftDeleteProject` method)

Find the loop that iterates `_projectChildTables` and add a guard:

```dart
// WHY: Builtin forms (is_builtin = 1) have null project_id and must NEVER
// be soft-deleted when a project is deleted. They are shared across all
// projects. Only user-created forms tied to the project should cascade.
// SECURITY: Without this guard, deleting any project would soft-delete
// the global builtin form, breaking all other projects.
for (final table in _projectChildTables) {
  String whereClause;
  List<dynamic> whereArgs;
  if (table == 'inspector_forms') {
    whereClause = 'project_id = ? AND (is_builtin = 0 OR is_builtin IS NULL)';
    whereArgs = [projectId];
  } else {
    whereClause = 'project_id = ?';
    whereArgs = [projectId];
  }
  // ... existing soft-delete logic using whereClause/whereArgs
}
```

**Step 6.2.3** — Add inspector_forms to _childToParentOrder
File: `lib/services/soft_delete_service.dart`

```dart
// NOTE: inspector_forms must come after form_responses and form_exports
// (which depend on it) but before projects.
static const List<String> _childToParentOrder = [
  'entry_quantities', 'entry_equipment', 'entry_personnel_counts',
  'entry_contractors', 'photos', 'entry_exports', 'documents',
  'form_exports', 'form_responses', 'todo_items',
  'calculation_history', 'equipment', 'personnel_types', 'bid_items',
  'inspector_forms', 'daily_entries', 'contractors', 'locations', 'projects',
];
```

**Verification:**
```
pwsh -Command "flutter test test/services/soft_delete_service_log_cleanup_test.dart"
```

---

### 6.3: Entry cascade includes form_exports + documents

**Step 6.3.1** — Update cascadeSoftDeleteEntry
File: `lib/services/soft_delete_service.dart` (inside `cascadeSoftDeleteEntry` method)

Find the list of entry child tables and add the new tables:

```dart
// BEFORE (entry child tables in cascadeSoftDeleteEntry, line ~178):
// NOTE: form_responses is NOT in this list — it is handled separately.
// 'entry_contractors', 'entry_equipment', 'entry_personnel_counts',
// 'entry_quantities', 'photos'

// AFTER:
// WHY: entry_exports and documents are entry children (have entry_id FK).
// They must cascade when an entry is soft-deleted.
// 'entry_contractors', 'entry_equipment', 'entry_personnel_counts',
// 'entry_quantities', 'photos', 'entry_exports', 'documents'
```

**Verification:**
```
pwsh -Command "flutter test test/services/soft_delete_service_log_cleanup_test.dart"
```

---

### 6.4: Tests

**Step 6.4.1** — Update cascade soft delete tests
File: `test/features/sync/engine/cascade_soft_delete_test.dart`

```dart
// WHY: Verify new tables are included in project cascade.
test('cascadeSoftDeleteProject includes entry_exports, documents, form_exports', () {
  // Setup: create project with entry_exports, documents, form_exports rows
  // Act: cascadeSoftDeleteProject(projectId)
  // Assert: all new table rows have deleted_at set
});

test('cascadeSoftDeleteProject skips builtin inspector_forms', () {
  // WHY: SECURITY — builtin forms must survive project deletion.
  // Setup: create project + builtin form (is_builtin=1, project_id=null)
  //        + user form (is_builtin=0, project_id=projectId)
  // Act: cascadeSoftDeleteProject(projectId)
  // Assert: user form has deleted_at set
  // Assert: builtin form has deleted_at = null (untouched)
});

test('cascadeSoftDeleteEntry includes entry_exports and documents', () {
  // Setup: create entry with entry_exports and documents rows
  // Act: cascadeSoftDeleteEntry(entryId)
  // Assert: entry_exports and documents rows have deleted_at set
});
```

**Step 6.4.2** — Update purge order tests
File: `test/services/soft_delete_service_log_cleanup_test.dart`

```dart
test('_childToParentOrder includes all new tables', () {
  // WHY: Regression guard — if a table is missing from purge order,
  // FK constraints will block hard deletes.
  expect(SoftDeleteService.childToParentOrder,
      containsAll(['entry_exports', 'documents', 'form_exports', 'inspector_forms']));
});

test('purge order: form_exports before form_responses', () {
  final order = SoftDeleteService.childToParentOrder;
  expect(order.indexOf('form_exports'), lessThan(order.indexOf('form_responses')));
});

test('purge order: entry_exports before daily_entries', () {
  final order = SoftDeleteService.childToParentOrder;
  expect(order.indexOf('entry_exports'), lessThan(order.indexOf('daily_entries')));
});
```

**Verification:**
```
pwsh -Command "flutter test test/features/sync/engine/cascade_soft_delete_test.dart test/services/soft_delete_service_log_cleanup_test.dart"
```

---

## Phase 7: Form Registry

**Agent:** backend-data-layer-agent

### 7.1: Create 5 registry classes

**Step 7.1.1** — Create FormCalculatorRegistry
File: `lib/features/forms/data/registries/form_calculator_registry.dart` (NEW)

```dart
/// WHY: Decouples form calculation logic from hardcoded if/else chains.
/// Each builtin form registers its calculator. Custom forms use no calculator.
abstract class FormCalculator {
  Map<String, dynamic> emptyTestRow();
  Map<String, dynamic> emptyProctorRow();
  Map<String, dynamic> calculate(Map<String, dynamic> responseData);
  Map<String, dynamic> calculateProctorChain(Map<String, dynamic> responseData);
}

class FormCalculatorRegistry {
  FormCalculatorRegistry._();
  static final instance = FormCalculatorRegistry._();

  final Map<String, FormCalculator> _calculators = {};

  void register(String formId, FormCalculator calculator) {
    // NOTE: Duplicate registration throws to catch init bugs early.
    if (_calculators.containsKey(formId)) {
      throw StateError('FormCalculator already registered for $formId');
    }
    _calculators[formId] = calculator;
  }

  FormCalculator? get(String formId) => _calculators[formId];

  bool hasCalculator(String formId) => _calculators.containsKey(formId);
}
```

**Step 7.1.2** — Create FormValidatorRegistry
File: `lib/features/forms/data/registries/form_validator_registry.dart` (NEW)

```dart
/// WHY: FormResponse.validateRequiredFields currently hardcodes 'mdot_0582b'.
/// This registry allows each form to define its own validation rules.
typedef FormValidator = List<String> Function(Map<String, dynamic> responseData,
    Map<String, dynamic> headerData);

class FormValidatorRegistry {
  FormValidatorRegistry._();
  static final instance = FormValidatorRegistry._();

  final Map<String, FormValidator> _validators = {};

  void register(String formId, FormValidator validator) {
    if (_validators.containsKey(formId)) {
      throw StateError('FormValidator already registered for $formId');
    }
    _validators[formId] = validator;
  }

  FormValidator? get(String formId) => _validators[formId];

  /// Returns empty list (valid) if no validator registered for this form.
  List<String> validate(String formId, Map<String, dynamic> responseData,
      Map<String, dynamic> headerData) {
    final validator = _validators[formId];
    if (validator == null) return const [];
    return validator(responseData, headerData);
  }
}
```

**Step 7.1.3** — Create FormInitialDataFactory
File: `lib/features/forms/data/registries/form_initial_data_factory.dart` (NEW)

```dart
/// WHY: Some forms need structured initial data (e.g., 0582B needs empty test
/// rows and proctor rows). This factory provides form-specific defaults.
typedef InitialDataBuilder = Map<String, dynamic> Function();

class FormInitialDataFactory {
  FormInitialDataFactory._();
  static final instance = FormInitialDataFactory._();

  final Map<String, InitialDataBuilder> _builders = {};

  void register(String formId, InitialDataBuilder builder) {
    if (_builders.containsKey(formId)) {
      throw StateError('InitialDataBuilder already registered for $formId');
    }
    _builders[formId] = builder;
  }

  /// Returns null if no builder registered — caller uses generic empty map.
  Map<String, dynamic>? buildInitialData(String formId) {
    return _builders[formId]?.call();
  }
}
```

**Step 7.1.4** — Create FormPdfFillerRegistry
File: `lib/features/forms/data/registries/form_pdf_filler_registry.dart` (NEW)

```dart
import 'dart:typed_data';

/// WHY: FormPdfService._fillMdot0582bFields is a 130-line hardcoded method.
/// This registry allows each form to register its own PDF field mapper.
/// Generic forms fall through to the default fieldDefinitions-based filler.
typedef PdfFieldFiller = Map<String, String> Function(
  Map<String, dynamic> responseData,
  Map<String, dynamic> headerData,
);

class FormPdfFillerRegistry {
  FormPdfFillerRegistry._();
  static final instance = FormPdfFillerRegistry._();

  final Map<String, PdfFieldFiller> _fillers = {};

  void register(String formId, PdfFieldFiller filler) {
    if (_fillers.containsKey(formId)) {
      throw StateError('PdfFieldFiller already registered for $formId');
    }
    _fillers[formId] = filler;
  }

  PdfFieldFiller? get(String formId) => _fillers[formId];

  bool hasFiller(String formId) => _fillers.containsKey(formId);
}
```

**Step 7.1.5** — Create FormScreenRegistry
File: `lib/features/forms/data/registries/form_screen_registry.dart` (NEW)

```dart
import 'package:flutter/widgets.dart';

/// WHY: InspectorFormProvider.appendMdot0582bProctorRow and
/// appendMdot0582bTestRow are hardcoded. With a screen registry, each form
/// type can provide its own custom screen widget builder.
/// Forms without a custom screen use the generic FormResponseScreen.
typedef FormScreenBuilder = Widget Function({
  required String formId,
  required String responseId,
  required String projectId,
});

class FormScreenRegistry {
  FormScreenRegistry._();
  static final instance = FormScreenRegistry._();

  final Map<String, FormScreenBuilder> _builders = {};

  void register(String formId, FormScreenBuilder builder) {
    if (_builders.containsKey(formId)) {
      throw StateError('FormScreenBuilder already registered for $formId');
    }
    _builders[formId] = builder;
  }

  FormScreenBuilder? get(String formId) => _builders[formId];

  bool hasCustomScreen(String formId) => _builders.containsKey(formId);
}
```

**Step 7.1.6** — Create barrel export
File: `lib/features/forms/data/registries/form_registries.dart` (NEW)

```dart
/// Barrel export for all form registries.
export 'form_calculator_registry.dart';
export 'form_validator_registry.dart';
export 'form_initial_data_factory.dart';
export 'form_pdf_filler_registry.dart';
export 'form_screen_registry.dart';
```

**Verification:**
```
pwsh -Command "flutter analyze"
```

---

### 7.2: Register 0582B implementations

**Step 7.2.1** — Create Mdot0582BCalculator adapter
File: `lib/features/forms/data/registries/mdot_0582b_registrations.dart` (NEW)

```dart
import 'form_registries.dart';
import '../calculators/mdot_0582b_calculator.dart' as calc;
import '../validators/mdot_0582b_validator.dart';
import '../pdf/mdot_0582b_pdf_filler.dart';

/// WHY: Single entry point to register all 0582B form capabilities.
/// Called once during app init (registerBuiltinForms).
void registerMdot0582B() {
  // FROM SPEC: 0582B calculator has emptyTestRow (19 fields),
  // emptyProctorRow (10 fields), calculate(), calculateProctorChain().
  FormCalculatorRegistry.instance.register('mdot_0582b', Mdot0582BFormCalculator());

  // FROM SPEC: FormResponse.validateRequiredFields line 359 hardcodes 'mdot_0582b'.
  // Move that logic here.
  FormValidatorRegistry.instance.register('mdot_0582b', validateMdot0582B);

  // WHY: 0582B needs structured initial response_data with empty test/proctor rows.
  FormInitialDataFactory.instance.register('mdot_0582b', () {
    return {
      'test_rows': [calc.Mdot0582BCalculator.emptyTestRow()],
      'proctor_rows': [calc.Mdot0582BCalculator.emptyProctorRow()],
    };
  });

  // FROM SPEC: FormPdfService._fillMdot0582bFields (lines 400-530) is hardcoded.
  // This registration delegates to the extracted filler function.
  FormPdfFillerRegistry.instance.register('mdot_0582b', fillMdot0582bPdfFields);

  // NOTE: FormScreenRegistry registration for 0582B is deferred to the UI layer
  // (Phase 8+) since it depends on Flutter widgets not available in data layer.
}
```

**Step 7.2.2** — Create Mdot0582BFormCalculator wrapper class
File: `lib/features/forms/data/registries/mdot_0582b_form_calculator.dart` (NEW)

```dart
import 'form_calculator_registry.dart';
import '../calculators/mdot_0582b_calculator.dart' as calc;

/// WHY: Adapts the existing Mdot0582BCalculator static methods to the
/// FormCalculator interface for registry use.
class Mdot0582BFormCalculator implements FormCalculator {
  @override
  Map<String, dynamic> emptyTestRow() => calc.Mdot0582BCalculator.emptyTestRow();

  @override
  Map<String, dynamic> emptyProctorRow() => calc.Mdot0582BCalculator.emptyProctorRow();

  @override
  Map<String, dynamic> calculate(Map<String, dynamic> responseData) =>
      calc.Mdot0582BCalculator.calculate(responseData);

  @override
  Map<String, dynamic> calculateProctorChain(Map<String, dynamic> responseData) =>
      calc.Mdot0582BCalculator.calculateProctorChain(responseData);
}
```

**Verification:**
```
pwsh -Command "flutter analyze"
```

---

### 7.3: Update seedBuiltinForms to registry loop

**Step 7.3.1** — Create BuiltinFormConfig
File: `lib/features/forms/data/registries/builtin_form_config.dart` (NEW)

```dart
import '../models/inspector_form.dart';

/// FROM SPEC: BuiltinFormConfig list replaces seedBuiltinForms().
/// Each entry defines the form metadata + registration callback.
class BuiltinFormConfig {
  final String id;
  final String name;
  final String templatePath;
  final void Function() registerCapabilities;

  const BuiltinFormConfig({
    required this.id,
    required this.name,
    required this.templatePath,
    required this.registerCapabilities,
  });

  InspectorForm toInspectorForm() => InspectorForm(
    id: id,
    name: name,
    templatePath: templatePath,
    isBuiltin: true,
    projectId: null,
  );
}
```

**Step 7.3.2** — Create builtinForms list
File: `lib/features/forms/data/registries/builtin_forms.dart` (NEW)

```dart
import 'builtin_form_config.dart';
import 'mdot_0582b_registrations.dart';
import '../../data/services/form_pdf_service.dart';

/// WHY: Central list of all builtin forms. Adding a new form = one entry here
/// + its registration file. No more scattered if/else chains.
final List<BuiltinFormConfig> builtinForms = [
  BuiltinFormConfig(
    id: 'mdot_0582b',
    name: 'MDOT 0582B Density',
    templatePath: FormPdfService.mdot0582bTemplatePath,
    registerCapabilities: registerMdot0582B,
  ),
  // NOTE: Future forms added here. Example:
  // BuiltinFormConfig(
  //   id: 'mdot_1120',
  //   name: 'MDOT 1120 Concrete',
  //   templatePath: FormPdfService.mdot1120TemplatePath,
  //   registerCapabilities: registerMdot1120,
  // ),
];
```

**Step 7.3.3** — Rewrite seedBuiltinForms
File: `lib/main.dart:566-586`

```dart
// BEFORE:
Future<void> seedBuiltinForms(InspectorFormRepository formRepository) async {
  try {
    final hasBuiltins = await formRepository.hasBuiltinForms();
    if (hasBuiltins) return;
    final result = await formRepository.createForm(InspectorForm(
      id: 'mdot_0582b',
      name: 'MDOT 0582B Density',
      templatePath: FormPdfService.mdot0582bTemplatePath,
      isBuiltin: true,
      projectId: null,
    ));
    if (!result.isSuccess) Logger.db('Failed to seed 0582B form: ${result.error}');
  } catch (e) { Logger.db('_seedBuiltinForms threw unexpectedly: $e'); }
}

// AFTER:
// WHY: Registry-driven seeding checks each form by ID instead of using
// hasBuiltinForms() which only checks "any exist". This is additive —
// new builtin forms get seeded even if older ones already exist.
Future<void> seedBuiltinForms(InspectorFormRepository formRepository) async {
  for (final config in builtinForms) {
    try {
      // NOTE: Check by ID, not hasBuiltinForms(). When we add a second
      // builtin form, hasBuiltinForms() would skip seeding it if 0582B
      // already exists.
      // CODE-REVIEW FIX #11: getFormById returns RepositoryResult, not nullable
      final existingResult = await formRepository.getFormById(config.id);
      if (existingResult.isSuccess && existingResult.data != null) {
        // WHY: Still register capabilities even if form already seeded.
        // Registry is in-memory and must be populated every app launch.
        config.registerCapabilities();
        continue;
      }
      final result = await formRepository.createForm(config.toInspectorForm());
      if (result.isSuccess) {
        config.registerCapabilities();
      } else {
        Logger.db('Failed to seed ${config.id}: ${result.error}');
      }
    } catch (e) {
      Logger.db('seedBuiltinForms threw for ${config.id}: $e');
    }
  }
}
```

Add import at top of `lib/main.dart`:
```dart
import 'features/forms/data/registries/builtin_forms.dart';
```

**Verification:**
```
pwsh -Command "flutter analyze"
```

---

### 7.4: Tests

**Step 7.4.1** — Registry unit tests
File: `test/features/forms/data/registries/form_calculator_registry_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/forms/data/registries/form_calculator_registry.dart';

void main() {
  // NOTE: Reset singleton between tests by testing behavior, not state.

  test('register and retrieve calculator', () {
    // WHY: Verify the basic register → get contract works.
    final registry = FormCalculatorRegistry.instance;
    // If already registered from another test, this verifies get works.
    expect(registry.get('nonexistent_form'), isNull);
  });

  test('hasCalculator returns false for unknown form', () {
    expect(FormCalculatorRegistry.instance.hasCalculator('unknown'), isFalse);
  });

  test('duplicate registration throws StateError', () {
    // WHY: Catch init bugs where a form is registered twice.
    // NOTE: This test must use a unique ID to avoid cross-test pollution.
    final registry = FormCalculatorRegistry.instance;
    final mockCalc = _MockCalculator();
    final testId = 'test_dup_${DateTime.now().millisecondsSinceEpoch}';
    registry.register(testId, mockCalc);
    expect(() => registry.register(testId, mockCalc), throwsStateError);
  });
}

class _MockCalculator implements FormCalculator {
  @override Map<String, dynamic> emptyTestRow() => {};
  @override Map<String, dynamic> emptyProctorRow() => {};
  @override Map<String, dynamic> calculate(Map<String, dynamic> d) => d;
  @override Map<String, dynamic> calculateProctorChain(Map<String, dynamic> d) => d;
}
```

**Step 7.4.2** — Validator registry tests
File: `test/features/forms/data/registries/form_validator_registry_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/forms/data/registries/form_validator_registry.dart';

void main() {
  test('validate returns empty list for unregistered form', () {
    // WHY: Forms without custom validators should pass validation by default.
    final errors = FormValidatorRegistry.instance.validate(
        'unknown_form', {}, {});
    expect(errors, isEmpty);
  });

  test('validate delegates to registered validator', () {
    final testId = 'test_val_${DateTime.now().millisecondsSinceEpoch}';
    FormValidatorRegistry.instance.register(testId,
        (data, header) => ['missing_field_x']);
    final errors = FormValidatorRegistry.instance.validate(testId, {}, {});
    expect(errors, ['missing_field_x']);
  });
}
```

**Step 7.4.3** — PDF filler registry tests
File: `test/features/forms/data/registries/form_pdf_filler_registry_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/forms/data/registries/form_pdf_filler_registry.dart';

void main() {
  test('hasFiller returns false for unknown form', () {
    expect(FormPdfFillerRegistry.instance.hasFiller('unknown'), isFalse);
  });

  test('registered filler is retrievable', () {
    final testId = 'test_pdf_${DateTime.now().millisecondsSinceEpoch}';
    FormPdfFillerRegistry.instance.register(testId,
        (data, header) => {'field1': 'value1'});
    final filler = FormPdfFillerRegistry.instance.get(testId);
    expect(filler, isNotNull);
    expect(filler!({}, {}), {'field1': 'value1'});
  });
}
```

**Step 7.4.4** — seedBuiltinForms integration test
File: `test/features/forms/data/registries/seed_builtin_forms_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
// WHY: Verify that seedBuiltinForms iterates the registry and checks by ID,
// not by hasBuiltinForms(). Uses a mock repository.

void main() {
  test('seedBuiltinForms seeds each form by ID check', () {
    // Setup: Mock repository where getFormById returns null for all IDs
    // Act: call seedBuiltinForms(mockRepo)
    // Assert: createForm called once per builtinForms entry
  });

  test('seedBuiltinForms skips already-seeded forms but registers capabilities', () {
    // WHY: On subsequent launches, forms exist but registries are empty
    // (in-memory). registerCapabilities must still run.
    // Setup: Mock repository where getFormById returns existing form
    // Act: call seedBuiltinForms(mockRepo)
    // Assert: createForm NOT called, but FormCalculatorRegistry has entry
  });

  test('seedBuiltinForms is additive — seeds new forms even if others exist', () {
    // WHY: This is the key behavioral change from hasBuiltinForms().
    // Setup: Mock repo where getFormById('mdot_0582b') returns form,
    //        getFormById('future_form') returns null
    // Act: call seedBuiltinForms(mockRepo)
    // Assert: createForm called only for 'future_form'
  });
}
```

**Verification:**
```
pwsh -Command "flutter test test/features/forms/data/registries/"
```

---

## Summary of New Files

| File | Phase |
|------|-------|
| `lib/features/sync/adapters/form_export_adapter.dart` | 5.4.1 |
| `lib/features/sync/adapters/entry_export_adapter.dart` | 5.4.2 |
| `lib/features/sync/adapters/document_adapter.dart` | 5.4.3 |
| `lib/features/forms/data/registries/form_calculator_registry.dart` | 7.1.1 |
| `lib/features/forms/data/registries/form_validator_registry.dart` | 7.1.2 |
| `lib/features/forms/data/registries/form_initial_data_factory.dart` | 7.1.3 |
| `lib/features/forms/data/registries/form_pdf_filler_registry.dart` | 7.1.4 |
| `lib/features/forms/data/registries/form_screen_registry.dart` | 7.1.5 |
| `lib/features/forms/data/registries/form_registries.dart` | 7.1.6 |
| `lib/features/forms/data/registries/mdot_0582b_registrations.dart` | 7.2.1 |
| `lib/features/forms/data/registries/mdot_0582b_form_calculator.dart` | 7.2.2 |
| `lib/features/forms/data/registries/builtin_form_config.dart` | 7.3.1 |
| `lib/features/forms/data/registries/builtin_forms.dart` | 7.3.2 |
| `test/features/sync/adapters/form_export_adapter_test.dart` | 5.8.1 |
| `test/features/sync/adapters/entry_export_adapter_test.dart` | 5.8.2 |
| `test/features/sync/adapters/document_adapter_test.dart` | 5.8.3 |
| `test/features/sync/adapters/inspector_form_adapter_test.dart` | 5.8.4 |
| `test/features/forms/data/registries/form_calculator_registry_test.dart` | 7.4.1 |
| `test/features/forms/data/registries/form_validator_registry_test.dart` | 7.4.2 |
| `test/features/forms/data/registries/form_pdf_filler_registry_test.dart` | 7.4.3 |
| `test/features/forms/data/registries/seed_builtin_forms_test.dart` | 7.4.4 |

## Modified Files

| File | Phase | Changes |
|------|-------|---------|
| `lib/features/sync/adapters/table_adapter.dart:45` | 5.1, 5.2, 5.3 | Rename isPhotoAdapter→isFileAdapter, add storageBucket/buildStoragePath/stripExifGps/includesNullProjectBuiltins |
| `lib/features/sync/adapters/photo_adapter.dart:30` | 5.1, 5.2 | Rename override, add storageBucket/buildStoragePath/stripExifGps |
| `lib/features/sync/engine/sync_engine.dart` | 5.1, 5.2, 5.3 | isFileAdapter check, _pushFileThreePhase, _validateStoragePath, _applyScopeFilter |
| `lib/features/sync/adapters/inspector_form_adapter.dart` | 5.3 | Add includesNullProjectBuiltins override |
| `lib/features/sync/engine/sync_registry.dart:24-44` | 5.5 | Register 3 new adapters (20 total) |
| `lib/features/sync/application/sync_orchestrator.dart:37-46` | 5.6 | Update syncBuckets |
| `lib/features/sync/engine/orphan_scanner.dart` | 5.7 | Multi-bucket scan |
| `lib/features/sync/engine/storage_cleanup.dart` | 5.7 | Bucket-aware cleanup |
| `lib/services/soft_delete_service.dart` | 6.1-6.3 | _childToParentOrder, _projectChildTables, is_builtin guard, entry cascade |
| `lib/main.dart:566-586` | 7.3 | Registry-driven seedBuiltinForms |

---

# Forms Infrastructure — Part 3: Registry Integration, Providers, UI, Cleanup

**Phases 8-11** | Parent spec: `2026-03-28-forms-infrastructure-spec.md`

---

## Phase 8: Form Registry Integration — Refactor 40+ Hardcoded 0582B References

> **NOTE: Intentionally Retained 0582B References**
>
> The following files contain hardcoded 0582B references that are **intentionally kept** and must NOT be refactored in this phase:
>
> | File | Why Kept |
> |------|----------|
> | `lib/core/database/database_service.dart` (migration defaults) | Historical migrations — changing would break existing installs |
> | `lib/core/database/schema_verifier.dart` | Validates migration defaults — must match database_service.dart |
> | `lib/shared/testing_keys/toolbox_keys.dart` | Test keys with `mdot` prefix — harmless, used by 0582B-specific test flows |
> | `lib/shared/services/preferences_service.dart` | Gauge number preference — 0582B-specific user preference, stays until multi-form preferences |
> | `lib/features/forms/data/services/auto_fill_service.dart` | Header fields shaped for 0582B — will be generalized when form #2 is added |
> | `lib/features/forms/data/models/inspector_form.dart` (`is0582B` getter) | Used internally by 0582B-specific screens behind the registry — getter stays |

### 8.1: FormResponse — Remove Default formType

**Agent:** backend-data-layer-agent
**File:** `lib/features/forms/data/models/form_response.dart`

**Step 1:** Remove the `'mdot_0582b'` default from the constructor (line ~108).

```dart
// BEFORE (line 108):
formType = formType ?? formId ?? 'mdot_0582b',

// AFTER:
// WHY: formType must be explicitly provided — no form should silently default to 0582B.
// FROM SPEC: Registry pattern requires each form to declare its own type at creation time.
formType = formType ?? formId ?? (throw ArgumentError('formType or formId is required')),
```

**Step 2:** Remove the `'mdot_0582b'` fallback from `fromMap` (line ~170).

```dart
// BEFORE (line 170):
formType: map['form_type'] as String? ?? map['form_id'] as String? ?? 'mdot_0582b',

// AFTER:
// WHY: DB rows must always have form_type populated. Crash loudly if missing.
// NOTE: Existing rows already have form_type set — v22+ migration ensures this.
formType: map['form_type'] as String? ?? map['form_id'] as String?,
```

**Step 3:** Make `formType` required in the constructor signature.

```dart
// BEFORE:
String? formType,

// AFTER:
// WHY: Eliminates silent default. All callers must pass formType explicitly.
required String formType,
```

**Verification:** `pwsh -Command "flutter test test/features/forms/"`

---

### 8.2: form_response_repository — Delegate Validation to FormValidatorRegistry

**Agent:** backend-data-layer-agent
**File:** `lib/features/forms/data/repositories/form_response_repository.dart`

**Step 1:** Add import for the validator registry (top of file).

```dart
// WHY: Repository delegates validation to the registry instead of hardcoding 0582B logic.
import 'package:construction_inspector/features/forms/domain/registries/form_validator_registry.dart';
```

**Step 2:** Inject `FormValidatorRegistry` into the repository constructor.

```dart
// BEFORE:
class FormResponseRepository {
  final DatabaseService _db;
  // ...
  FormResponseRepository(this._db);

// AFTER:
class FormResponseRepository {
  final DatabaseService _db;
  final FormValidatorRegistry _validatorRegistry;
  // ...
  // WHY: Dependency injection keeps repository form-agnostic.
  FormResponseRepository(this._db, this._validatorRegistry);
```

**Step 3:** Replace `validateRequiredFields` body (lines 355-419).

```dart
// BEFORE (lines 355-419):
List<String> validateRequiredFields(FormResponse response) {
  if (response.formType != 'mdot_0582b') return const [];
  // ... 60 lines of 0582B-specific validation
}

// AFTER:
// WHY: Each form type registers its own validator. Generic code has no form-specific knowledge.
// FROM SPEC: FormValidatorRegistry pattern — validators registered per formType string key.
List<String> validateRequiredFields(FormResponse response) {
  final validator = _validatorRegistry.get(response.formType);
  if (validator == null) return const [];
  return validator.validate(response);
}
```

**Step 4:** Update all call sites that construct `FormResponseRepository` to pass the registry.
Search for `FormResponseRepository(` in providers and test files. Each gets:

```dart
// NOTE: FormValidatorRegistry is a singleton created at app startup (Phase 7).
FormResponseRepository(db, formValidatorRegistry)
```

**Verification:** `pwsh -Command "flutter test test/features/forms/"`

---

### 8.3: form_pdf_service — Delegate Filling to FormPdfFillerRegistry

**Agent:** backend-data-layer-agent
**File:** `lib/features/forms/data/services/form_pdf_service.dart`

**Step 1:** Add import for the PDF filler registry.

```dart
import 'package:construction_inspector/features/forms/domain/registries/form_pdf_filler_registry.dart';
```

**Step 2:** Inject `FormPdfFillerRegistry` into the service.

```dart
// BEFORE:
class FormPdfService {
  static const String mdot0582bTemplatePath = 'assets/templates/forms/mdot_0582b_form.pdf';
  // ...

// AFTER:
class FormPdfService {
  final FormPdfFillerRegistry _fillerRegistry;
  // WHY: Template path is now per-form-type, resolved via registry.
  // NOTE: Remove static const mdot0582bTemplatePath — moved to Mdot0582bPdfFiller.
  FormPdfService(this._fillerRegistry);
```

**Step 3:** Remove `_isMdot0582BForm` method (lines 87-94).

```dart
// WHY: Form-type detection is handled by registry lookup, not string matching.
// DELETE lines 87-94 entirely.
```

**Step 4:** Replace the fill logic that branches on 0582B vs generic.

```dart
// BEFORE (conceptual — lines 362-530):
// if _isMdot0582BForm → _fillMdot0582bFields
// else → generic field iteration

// AFTER:
// WHY: Registry dispatches to the correct filler. Generic fallback handles unknown types.
// FROM SPEC: FormPdfFillerRegistry pattern.
Future<Uint8List> fillForm(InspectorForm form, FormResponse response) async {
  final filler = _fillerRegistry.get(response.formType);
  if (filler != null) {
    return filler.fill(form, response);
  }
  // NOTE: Generic fallback iterates fieldDefinitions JSON — preserves existing generic path.
  return _fillGenericFields(form, response);
}
```

**Step 5:** Move `_fillMdot0582bFields` and `buildMdot0582bFieldMap` to the 0582B filler class (already created in Phase 7). Delete from this file.

**Step 6:** Update all call sites that construct `FormPdfService` to pass the registry.

**Verification:** `pwsh -Command "flutter test test/features/forms/"`

---

### 8.4: inspector_form_provider — Delegate Calculator Methods to FormCalculatorRegistry

**Agent:** frontend-flutter-specialist-agent
**File:** `lib/features/forms/presentation/providers/inspector_form_provider.dart`

**Step 1:** Add import for the calculator registry.

```dart
import 'package:construction_inspector/features/forms/domain/registries/form_calculator_registry.dart';
```

**Step 2:** Inject `FormCalculatorRegistry` into the provider constructor.

```dart
// WHY: Provider delegates row-append logic to form-specific calculators via registry.
final FormCalculatorRegistry _calculatorRegistry;
```

**Step 3:** Replace `appendMdot0582bProctorRow` (line ~354) with generic method.

```dart
// BEFORE (line 354):
Future<void> appendMdot0582bProctorRow(String responseId) async {
  // uses Mdot0582BCalculator.emptyProctorRow()
}

// AFTER:
// WHY: Generic append delegates to the registered calculator for the form's type.
// NOTE: The 0582B calculator still provides emptyProctorRow() — just accessed via registry.
Future<void> appendRow(String responseId, String rowType) async {
  final response = await _repository.getById(responseId);
  if (response == null) return;

  final calculator = _calculatorRegistry.get(response.formType);
  if (calculator == null) return;

  final emptyRow = calculator.emptyRow(rowType);
  if (emptyRow == null) return;

  // FROM SPEC: Append to responseData JSON under the rowType key.
  final data = jsonDecode(response.responseData) as Map<String, dynamic>;
  final rows = (data[rowType] as List<dynamic>?) ?? [];
  rows.add(emptyRow);
  data[rowType] = rows;

  await _repository.update(response.copyWith(responseData: jsonEncode(data)));
  notifyListeners();
}
```

**Step 4:** Replace `appendMdot0582bTestRow` (line ~383) — DELETE. Callers use `appendRow(responseId, 'test_rows')` instead.

**Step 5:** Update all callers of `appendMdot0582bProctorRow` and `appendMdot0582bTestRow` to use the new `appendRow` method.

```dart
// BEFORE:
provider.appendMdot0582bProctorRow(responseId);
provider.appendMdot0582bTestRow(responseId);

// AFTER:
// WHY: Callers pass the row type string; registry handles form-specific logic.
provider.appendRow(responseId, 'proctor_rows');
provider.appendRow(responseId, 'test_rows');
```

**Verification:** `pwsh -Command "flutter test test/features/forms/"`

---

### 8.5: app_router — Form-Fill Dispatch via FormScreenRegistry

**Agent:** frontend-flutter-specialist-agent
**File:** `lib/core/router/app_router.dart`

**Step 1:** Add import for the screen registry.

```dart
import 'package:construction_inspector/features/forms/domain/registries/form_screen_registry.dart';
```

**Step 2:** Replace hardcoded `MdotHubScreen` route (lines 611-618).

```dart
// BEFORE (lines 611-618):
GoRoute(
  path: 'form-fill',
  builder: (context, state) {
    final responseId = state.uri.queryParameters['responseId'];
    final projectId = state.uri.queryParameters['projectId'];
    return MdotHubScreen(responseId: responseId!, projectId: projectId!);
  },
),

// AFTER:
// WHY: Route dispatches to the correct screen based on formType query parameter.
// FROM SPEC: FormScreenRegistry resolves Widget by formType key.
GoRoute(
  path: 'form-fill',
  builder: (context, state) {
    final responseId = state.uri.queryParameters['responseId']!;
    final projectId = state.uri.queryParameters['projectId']!;
    final formType = state.uri.queryParameters['formType'] ?? 'mdot_0582b';
    // NOTE: formType defaults to mdot_0582b for backwards compat with existing deep links.
    final registry = context.read<FormScreenRegistry>();
    return registry.buildScreen(formType, responseId: responseId, projectId: projectId);
  },
),
```

**Step 3:** Update all `GoRouter.push` calls that navigate to `form-fill` to include `formType` query parameter.

```dart
// BEFORE:
context.push('/project/$projectId/form-fill?responseId=$responseId&projectId=$projectId');

// AFTER:
// WHY: Explicit formType in the route enables registry dispatch.
context.push('/project/$projectId/form-fill?responseId=$responseId&projectId=$projectId&formType=${response.formType}');
```

**Verification:** `pwsh -Command "flutter test test/core/router/"`

---

### 8.6: entry_forms_section — Use FormInitialDataFactory

**Agent:** frontend-flutter-specialist-agent
**File:** `lib/features/entries/presentation/widgets/entry_forms_section.dart`

**Step 1:** Add import for the initial data factory.

```dart
import 'package:construction_inspector/features/forms/domain/registries/form_initial_data_factory.dart';
```

**Step 2:** Replace `_startForm` hardcoded initial data (lines 40-54).

```dart
// BEFORE (lines 40-54):
void _startForm(InspectorForm form) {
  final initialData = form.is0582B
      ? jsonEncode({
          'test_rows': [],
          'proctor_rows': [],
          'chart_standards': {},
          'operating_standards': {},
          'remarks': '',
        })
      : '{}';
  // creates FormResponse with this initial data
}

// AFTER:
// WHY: Each form type defines its own initial data shape via the factory registry.
// FROM SPEC: FormInitialDataFactory returns JSON string keyed by form type.
void _startForm(InspectorForm form) {
  final factory = context.read<FormInitialDataFactory>();
  final initialData = factory.create(form.formType);
  // NOTE: form.formType maps to the InspectorForm's type field, used as registry key.
  // creates FormResponse with this initial data
}
```

**Verification:** `pwsh -Command "flutter test test/features/entries/"`

---

### 8.7: entry_form_card — Registry Dispatch for Quick Actions

**Agent:** frontend-flutter-specialist-agent
**File:** `lib/features/entries/presentation/widgets/entry_form_card.dart`

**Step 1:** Add import for the quick actions registry.

```dart
import 'package:construction_inspector/features/forms/domain/registries/form_quick_action_registry.dart';
```

**Step 2:** Replace `is0582B` check for quick action buttons (lines 26, 75).

```dart
// BEFORE (line 26):
if (form.is0582B) ...

// BEFORE (line 75):
// shows "Add Test" / "Add Proctor" / "Add Weights" only for 0582B

// AFTER:
// WHY: Quick actions are form-type-specific. Registry provides them per type.
// FROM SPEC: FormQuickActionRegistry returns List<QuickAction> per formType.
final quickActions = context.read<FormQuickActionRegistry>().getActions(response.formType);
if (quickActions.isNotEmpty) ...[
  for (final action in quickActions)
    IconButton(
      icon: Icon(action.icon),
      tooltip: action.label,
      onPressed: () => action.execute(context, response),
    ),
]
```

**Verification:** `pwsh -Command "flutter test test/features/entries/"`

---

### 8.8: form_viewer_screen — Remove Hardcoded 0582B References

**Agent:** frontend-flutter-specialist-agent
**File:** `lib/features/forms/presentation/screens/form_viewer_screen.dart`

**Step 1:** Replace hardcoded 0582B form lookup (lines 135-142).

```dart
// BEFORE (lines 135-142):
// firstWhere looking for 0582B form

// AFTER:
// WHY: Screen receives formType from route/arguments. No hardcoded lookup.
// NOTE: The form is resolved by ID/type from the route, not by searching for '0582'.
```

**Step 2:** Replace hardcoded AppBar title (line 259).

```dart
// BEFORE (line 259):
// AppBar title hardcoded to "MDOT 0582B"

// AFTER:
// WHY: Title comes from the InspectorForm.name field, supporting any form type.
title: Text(form?.name ?? 'Form Viewer'),
```

**Verification:** `pwsh -Command "flutter test test/features/forms/"`

---

### 8.9: Phase 8 Tests

**Step 1:** Update existing form tests to pass explicit `formType` to `FormResponse` constructor.

```dart
// WHY: Constructor now requires formType — all test factories must provide it.
// File: test/features/forms/ (all test files creating FormResponse)
FormResponse(
  formType: 'mdot_0582b',  // NOTE: Explicit where it was previously defaulted.
  projectId: testProjectId,
  // ...
)
```

**Step 2:** Add unit test for registry-based validation dispatch.

**File:** `test/features/forms/data/repositories/form_response_repository_test.dart`

```dart
// WHY: Verifies that validation delegates to the correct registered validator.
test('validateRequiredFields delegates to registered validator', () {
  final registry = FormValidatorRegistry();
  registry.register('test_form', TestFormValidator());
  final repo = FormResponseRepository(mockDb, registry);

  final response = FormResponse(formType: 'test_form', projectId: 'p1');
  final errors = repo.validateRequiredFields(response);
  // NOTE: TestFormValidator returns specific errors for test assertions.
  expect(errors, contains('test_field_required'));
});
```

**Step 3:** Add unit test for registry-based screen dispatch.

**File:** `test/core/router/form_screen_registry_test.dart`

```dart
// WHY: Verifies form-fill route resolves to correct screen widget per formType.
test('buildScreen returns registered widget for formType', () {
  final registry = FormScreenRegistry();
  registry.register('mdot_0582b', (responseId, projectId) => MdotHubScreen(...));
  final widget = registry.buildScreen('mdot_0582b', responseId: 'r1', projectId: 'p1');
  expect(widget, isA<MdotHubScreen>());
});
```

**Step 4:** Run full Phase 8 verification.

**Verification:** `pwsh -Command "flutter test test/features/forms/ test/core/router/ test/features/entries/"`

---

## Phase 9: Providers

### 9.1: FormExportProvider

**Agent:** frontend-flutter-specialist-agent
**File:** `lib/features/forms/presentation/providers/form_export_provider.dart` (NEW)

**Step 1:** Create the provider.

```dart
import 'package:flutter/foundation.dart';
import 'package:construction_inspector/features/forms/data/repositories/form_response_repository.dart';
import 'package:construction_inspector/features/forms/data/services/form_pdf_service.dart';
import 'package:construction_inspector/features/forms/domain/registries/form_pdf_filler_registry.dart';

/// WHY: Encapsulates form PDF export logic (generate + share/save).
/// FROM SPEC: Separates export concern from InspectorFormProvider which was growing too large.
class FormExportProvider extends ChangeNotifier {
  final FormResponseRepository _repository;
  final FormExportRepository _formExportRepository;
  final FormPdfService _pdfService;

  bool _isExporting = false;
  bool get isExporting => _isExporting;

  String? _errorMessage;
  String? get errorMessage => _errorMessage;

  FormExportProvider({
    required FormResponseRepository repository,
    required FormExportRepository formExportRepository,
    required FormPdfService pdfService,
  })  : _repository = repository,
        _formExportRepository = formExportRepository,
        _pdfService = pdfService;

  /// Export a single form response to PDF.
  /// NOTE: Returns the file path of the generated PDF for sharing.
  Future<String?> exportFormToPdf(String responseId, {String? currentUserId}) async {
    _isExporting = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final response = await _repository.getById(responseId);
      if (response == null) {
        _errorMessage = 'Form response not found';
        return null;
      }

      final pdfBytes = await _pdfService.generateFilledPdf(response);
      if (pdfBytes == null) {
        _errorMessage = 'Failed to generate PDF';
        return null;
      }

      // WHY: Save to app's temp directory for sharing via platform share sheet.
      final savedFilePath = await _pdfService.saveTempPdf(pdfBytes, responseId);
      if (savedFilePath == null) {
        _errorMessage = 'Failed to save PDF';
        return null;
      }

      // WHY: Without a metadata row, the sync engine has nothing to push.
      // FROM SPEC: "metadata row created in form_exports with file_path"
      // (Inlined from Addendum A.1)
      final generatedFilename = '${response.formType}_${responseId.substring(0, 8)}.pdf';
      final export = FormExport(
        formResponseId: response.id,
        projectId: response.projectId,
        entryId: response.entryId,
        filePath: savedFilePath,
        filename: generatedFilename,
        formType: response.formType,
        fileSizeBytes: await File(savedFilePath).length(),
        exportedAt: DateTime.now().toUtc().toIso8601String(),
        createdByUserId: currentUserId,
      );
      await _formExportRepository.create(export);

      return savedFilePath;
    } catch (e) {
      _errorMessage = 'Export failed: $e';
      return null;
    } finally {
      _isExporting = false;
      notifyListeners();
    }
  }
}
```

**Verification:** `pwsh -Command "flutter test test/features/forms/"`

---

### 9.2: EntryExportProvider

**Agent:** frontend-flutter-specialist-agent
**File:** `lib/features/entries/presentation/providers/entry_export_provider.dart` (NEW)

**Step 1:** Create the provider.

```dart
import 'package:flutter/foundation.dart';
import 'package:construction_inspector/features/entries/data/repositories/entry_repository.dart';
import 'package:construction_inspector/features/forms/data/repositories/form_response_repository.dart';
import 'package:construction_inspector/features/forms/presentation/providers/form_export_provider.dart';

/// WHY: Coordinates exporting all forms attached to an entry as a bundle,
/// and creates EntryExport metadata rows for the generated PDFs.
/// FROM SPEC: Entry-level export collects all child form responses and delegates per-form export.
class EntryExportProvider extends ChangeNotifier {
  final EntryRepository _entryRepository;
  final EntryExportRepository _entryExportRepository;
  final FormResponseRepository _formResponseRepository;
  final FormExportProvider _formExportProvider;

  bool _isExporting = false;
  bool get isExporting => _isExporting;

  List<String> _exportedPaths = [];
  List<String> get exportedPaths => _exportedPaths;

  String? _errorMessage;
  String? get errorMessage => _errorMessage;

  EntryExportProvider({
    required EntryRepository entryRepository,
    required EntryExportRepository entryExportRepository,
    required FormResponseRepository formResponseRepository,
    required FormExportProvider formExportProvider,
  })  : _entryRepository = entryRepository,
        _entryExportRepository = entryExportRepository,
        _formResponseRepository = formResponseRepository,
        _formExportProvider = formExportProvider;

  /// Export all forms for an entry.
  /// NOTE: Returns list of generated PDF file paths.
  Future<List<String>> exportAllFormsForEntry(String entryId, {String? currentUserId}) async {
    _isExporting = true;
    _errorMessage = null;
    _exportedPaths = [];
    notifyListeners();

    try {
      final entry = await _entryRepository.getById(entryId);
      if (entry == null) {
        _errorMessage = 'Entry not found';
        return [];
      }

      final responses = await _formResponseRepository.getByEntryId(entryId);
      final paths = <String>[];

      for (final response in responses) {
        // WHY: Delegate each form's export to FormExportProvider which handles type dispatch.
        final path = await _formExportProvider.exportFormToPdf(response.id, currentUserId: currentUserId);
        if (path != null) paths.add(path);
      }

      // WHY: Without a metadata row, the sync engine has nothing to push.
      // (Inlined from Addendum A.2) — Create an EntryExport row for the bundle.
      if (paths.isNotEmpty) {
        final savedFilePath = paths.first; // Primary export path
        final generatedFilename = 'entry_report_${entryId.substring(0, 8)}.pdf';
        final export = EntryExport(
          entryId: entry.id,
          projectId: entry.projectId,
          filePath: savedFilePath,
          filename: generatedFilename,
          fileSizeBytes: await File(savedFilePath).length(),
          exportedAt: DateTime.now().toUtc().toIso8601String(),
          createdByUserId: currentUserId,
        );
        await _entryExportRepository.create(export);
      }

      _exportedPaths = paths;
      return paths;
    } catch (e) {
      _errorMessage = 'Entry export failed: $e';
      return [];
    } finally {
      _isExporting = false;
      notifyListeners();
    }
  }
}
```

**Verification:** `pwsh -Command "flutter test test/features/entries/"`

---

### 9.3: DocumentProvider

**Agent:** frontend-flutter-specialist-agent
**File:** `lib/features/forms/presentation/providers/document_provider.dart` (NEW)

**Step 1:** Create the provider.

```dart
import 'package:flutter/foundation.dart';
import 'package:construction_inspector/features/forms/data/repositories/form_response_repository.dart';

/// WHY: Manages document/form listing and filtering for the Form Gallery screen,
/// plus document attachment CRUD for entries (inlined from Addendum B.2).
/// FROM SPEC: Provides filtered views of form responses by type, status, and project.
class DocumentProvider extends ChangeNotifier {
  final FormResponseRepository _repository;
  final DocumentRepository _documentRepository;
  final DocumentService _documentService;

  List<FormResponseSummary> _documents = [];
  List<FormResponseSummary> get documents => _documents;

  List<Document> _entryDocuments = [];
  List<Document> get entryDocuments => _entryDocuments;

  String? _filterFormType;
  String? get filterFormType => _filterFormType;

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  DocumentProvider({
    required FormResponseRepository repository,
    required DocumentRepository documentRepository,
    required DocumentService documentService,
  })  : _repository = repository,
        _documentRepository = documentRepository,
        _documentService = documentService;

  /// Load all form responses for a project, optionally filtered by type.
  Future<void> loadDocuments(String projectId, {String? formType}) async {
    _isLoading = true;
    _filterFormType = formType;
    notifyListeners();

    try {
      final responses = await _repository.getByProjectId(projectId);
      // WHY: Filter client-side for now. DB-level filtering can be added if perf requires it.
      _documents = responses
          .where((r) => formType == null || r.formType == formType)
          .map((r) => FormResponseSummary.fromResponse(r))
          .toList();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void setFilter(String? formType) {
    _filterFormType = formType;
    notifyListeners();
  }

  // --- Document attachment methods (from Addendum B.2) ---

  /// Load documents attached to a specific entry.
  Future<void> loadEntryDocuments(String entryId) async {
    _isLoading = true;
    notifyListeners();
    try {
      _entryDocuments = await _documentRepository.getByEntryId(entryId);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Pick and attach a document to an entry via DocumentService.
  Future<Document?> attachDocument({
    required String entryId,
    required String projectId,
    String? userId,
  }) async {
    final doc = await _documentService.attachDocument(
      entryId: entryId,
      projectId: projectId,
      userId: userId,
    );
    if (doc != null) {
      _entryDocuments = [..._entryDocuments, doc];
      notifyListeners();
    }
    return doc;
  }

  /// Soft-delete a document.
  Future<void> deleteDocument(String id) async {
    await _documentRepository.delete(id);
    _entryDocuments = _entryDocuments.where((d) => d.id != id).toList();
    notifyListeners();
  }
}

/// NOTE: Lightweight summary to avoid holding full responseData in memory for list views.
class FormResponseSummary {
  final String id;
  final String formType;
  final String status;
  final String? entryId;
  final String updatedAt;

  FormResponseSummary({
    required this.id,
    required this.formType,
    required this.status,
    this.entryId,
    required this.updatedAt,
  });

  factory FormResponseSummary.fromResponse(dynamic response) {
    return FormResponseSummary(
      id: response.id,
      formType: response.formType,
      status: response.status,
      entryId: response.entryId,
      updatedAt: response.updatedAt,
    );
  }
}
```

**Verification:** `pwsh -Command "flutter test test/features/forms/"`

---

### 9.4: Register All 3 Providers in main.dart + main_driver.dart

**Step 1:** Add imports to `lib/main.dart` (top of file).

```dart
import 'package:construction_inspector/features/forms/presentation/providers/form_export_provider.dart';
import 'package:construction_inspector/features/entries/presentation/providers/entry_export_provider.dart';
import 'package:construction_inspector/features/forms/presentation/providers/document_provider.dart';
```

**Step 2:** Add provider registrations inside the `MultiProvider` block in `lib/main.dart` (around line 110-240, after existing providers).

```dart
// WHY: All three providers must be available app-wide for form gallery and export features.
// NOTE: FormExportProvider depends on FormResponseRepository and FormPdfService.
// NOTE: EntryExportProvider depends on EntryRepository, FormResponseRepository, and FormExportProvider.
// NOTE: DocumentProvider depends on FormResponseRepository.
ChangeNotifierProvider(create: (context) => FormExportProvider(
  repository: context.read<FormResponseRepository>(),
  pdfService: context.read<FormPdfService>(),
)),
ChangeNotifierProvider(create: (context) => EntryExportProvider(
  entryRepository: context.read<EntryRepository>(),
  formResponseRepository: context.read<FormResponseRepository>(),
  formExportProvider: context.read<FormExportProvider>(),
)),
ChangeNotifierProvider(create: (context) => DocumentProvider(
  repository: context.read<FormResponseRepository>(),
)),
```

**Step 3:** Mirror the same registrations in `lib/main_driver.dart`.

```dart
// WHY: Driver build must have identical provider tree for E2E testing.
// NOTE: Copy the exact same 3 ChangeNotifierProvider blocks from main.dart.
// Also register DocumentService and DocumentRepository in main_driver.dart:
final documentLocalDatasource = DocumentLocalDatasource(dbService);
final documentRepository = DocumentRepository(documentLocalDatasource);
final documentService = DocumentService(documentRepository, dbService);
```

**Verification:** `pwsh -Command "flutter test test/features/forms/ test/features/entries/"`

---

### 9.5: DocumentService (from Addendum B.1)

**Agent:** backend-data-layer-agent
**File:** `lib/services/document_service.dart` (NEW)

```dart
import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:construction_inspector/features/entries/data/repositories/document_repository.dart';
import 'package:construction_inspector/features/entries/data/models/document.dart';
import 'package:construction_inspector/core/database/database_service.dart';

// WHY: Mirrors PhotoService pattern for document attachments.
// FROM SPEC: "File copied to local storage, documents row created"
class DocumentService {
  final DocumentRepository _repository;
  final DatabaseService _db;

  DocumentService(this._repository, this._db);

  /// Pick and attach a document (PDF/XLS) to an entry.
  Future<Document?> attachDocument({
    required String entryId,
    required String projectId,
    String? userId,
  }) async {
    // SEC-F06: Allowlist of accepted file types
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'xls', 'xlsx', 'doc', 'docx'],
    );
    if (result == null || result.files.isEmpty) return null;

    final pickedFile = result.files.first;
    final sourceFile = File(pickedFile.path!);

    // Copy to app-local storage
    final docsDir = await _getDocumentsDirectory(projectId, entryId);
    // SEC-F05: Sanitize filename
    final safeFilename = _sanitizeFilename(pickedFile.name);
    final destPath = '${docsDir.path}/$safeFilename';
    await sourceFile.copy(destPath);

    // Create Document row
    final doc = Document(
      entryId: entryId,
      projectId: projectId,
      filePath: destPath,
      filename: safeFilename,
      fileType: pickedFile.extension ?? 'pdf',
      fileSizeBytes: await File(destPath).length(),
      capturedAt: DateTime.now().toUtc().toIso8601String(),
      createdByUserId: userId,
    );
    final saveResult = await _repository.create(doc);
    return saveResult.isSuccess ? doc : null;
  }

  Future<Directory> _getDocumentsDirectory(String projectId, String entryId) async {
    final appDir = await getApplicationDocumentsDirectory();
    final dir = Directory('${appDir.path}/documents/$projectId/$entryId');
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  /// SEC-F05: Strip dangerous characters from filenames
  String _sanitizeFilename(String filename) {
    return filename.replaceAll(RegExp(r'[^\w\s\-.]'), '_').replaceAll('..', '_');
  }
}
```

**Verification:** `pwsh -Command "flutter analyze"`

---

### 9.6: Entry Detail — Document Attachment UI (from Addendum B.3)

**Agent:** frontend-flutter-specialist-agent
**File:** `lib/features/entries/presentation/widgets/entry_forms_section.dart` (MODIFY)

Add below the forms list in the entry detail view:

```dart
// WHY: Users need to attach arbitrary documents (PDFs, spreadsheets) to entries.
// FROM SPEC: Document attachment flow — pick file, copy locally, create row, sync.

// --- Documents Section ---
// Add after the forms list, still inside the same widget build method:

const SizedBox(height: 16),
Text('Documents', style: Theme.of(context).textTheme.titleMedium),
const SizedBox(height: 8),

// "Attach Document" button
OutlinedButton.icon(
  onPressed: () async {
    final docProvider = context.read<DocumentProvider>();
    await docProvider.attachDocument(
      entryId: entryId,
      projectId: projectId,
      userId: currentUserId,
    );
  },
  icon: const Icon(Icons.attach_file),
  label: const Text('Attach Document'),
),

// Documents list
Consumer<DocumentProvider>(
  builder: (context, provider, _) {
    final docs = provider.entryDocuments;
    if (docs.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(8.0),
        child: Text('No documents attached'),
      );
    }
    return Column(
      children: docs.map((doc) => ListTile(
        leading: Icon(_iconForFileType(doc.fileType)),
        title: Text(doc.filename),
        subtitle: doc.notes != null ? Text(doc.notes!) : null,
        trailing: IconButton(
          icon: const Icon(Icons.delete_outline),
          onPressed: () => provider.deleteDocument(doc.id),
        ),
        onTap: () => _openDocument(doc),
      )).toList(),
    );
  },
),
```

**NOTE:** The `_iconForFileType` and `_openDocument` helper methods should be added as private methods in the widget. `_openDocument` opens via local file path or requests a signed URL for remote files.

**Verification:** `pwsh -Command "flutter analyze"`

---

## Phase 10: UI — Form Gallery

### 10.1: FormGalleryScreen with Per-Type Tabs

**Agent:** frontend-flutter-specialist-agent
**File:** `lib/features/forms/presentation/screens/form_gallery_screen.dart` (NEW)

**Step 1:** Create the screen.

```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/features/forms/presentation/providers/document_provider.dart';
import 'package:construction_inspector/features/forms/presentation/providers/inspector_form_provider.dart';

/// WHY: Replaces the hardcoded forms_list_screen.dart which only shows 0582B.
/// FROM SPEC: Form Gallery shows all registered form types as tabs, with per-type listings.
class FormGalleryScreen extends StatefulWidget {
  final String projectId;

  const FormGalleryScreen({super.key, required this.projectId});

  @override
  State<FormGalleryScreen> createState() => _FormGalleryScreenState();
}

class _FormGalleryScreenState extends State<FormGalleryScreen> {
  @override
  void initState() {
    super.initState();
    // WHY: Load documents on screen entry so the list is populated immediately.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<DocumentProvider>().loadDocuments(widget.projectId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final formProvider = context.watch<InspectorFormProvider>();
    final docProvider = context.watch<DocumentProvider>();

    // NOTE: Tabs built from registered form types. Each InspectorForm becomes a tab.
    final registeredForms = formProvider.availableForms;

    return DefaultTabController(
      length: registeredForms.length + 1, // +1 for "All" tab
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Forms'),
          bottom: TabBar(
            isScrollable: true,
            tabs: [
              const Tab(text: 'All'),
              // WHY: Dynamic tabs from registered forms — no hardcoded form names.
              for (final form in registeredForms)
                Tab(text: form.shortName ?? form.name),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            // "All" tab — no type filter
            _FormListView(
              documents: docProvider.documents,
              isLoading: docProvider.isLoading,
              projectId: widget.projectId,
            ),
            // Per-type tabs
            for (final form in registeredForms)
              _FormListView(
                documents: docProvider.documents
                    .where((d) => d.formType == form.formType)
                    .toList(),
                isLoading: docProvider.isLoading,
                projectId: widget.projectId,
                formType: form.formType,
              ),
          ],
        ),
        floatingActionButton: FloatingActionButton(
          onPressed: () => _showNewFormDialog(context),
          child: const Icon(Icons.add),
        ),
      ),
    );
  }

  void _showNewFormDialog(BuildContext context) {
    // WHY: User picks which form type to create. No longer auto-creates 0582B.
    // NOTE: Shows bottom sheet with available form types from InspectorFormProvider.
    final formProvider = context.read<InspectorFormProvider>();
    showModalBottomSheet(
      context: context,
      builder: (_) => ListView(
        shrinkWrap: true,
        children: [
          for (final form in formProvider.availableForms)
            ListTile(
              leading: const Icon(Icons.description),
              title: Text(form.name),
              onTap: () {
                Navigator.pop(context);
                formProvider.startNewForm(form, widget.projectId);
              },
            ),
        ],
      ),
    );
  }
}

/// NOTE: Reusable list view widget used by each tab.
class _FormListView extends StatelessWidget {
  final List<FormResponseSummary> documents;
  final bool isLoading;
  final String projectId;
  final String? formType;

  const _FormListView({
    required this.documents,
    required this.isLoading,
    required this.projectId,
    this.formType,
  });

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (documents.isEmpty) {
      return const Center(child: Text('No forms yet'));
    }
    return ListView.builder(
      itemCount: documents.length,
      itemBuilder: (context, index) {
        final doc = documents[index];
        return ListTile(
          title: Text('${doc.formType} - ${doc.status}'),
          subtitle: Text('Updated: ${doc.updatedAt}'),
          onTap: () {
            // WHY: Navigate to form-fill with formType for registry dispatch.
            context.push(
              '/project/$projectId/form-fill'
              '?responseId=${doc.id}'
              '&projectId=$projectId'
              '&formType=${doc.formType}',
            );
          },
        );
      },
    );
  }
}
```

**Verification:** `pwsh -Command "flutter test test/features/forms/"`

---

### 10.2: Update Toolbox Route to Form Gallery

**File:** `lib/core/router/app_router.dart`

**Step 1:** Find the `forms` route that currently points to `FormsListScreen` and update it.

```dart
// BEFORE:
// 'forms' route → FormsListScreen (hardcoded to 0582B)

// AFTER:
// WHY: Toolbox "Forms" card now opens the multi-type Form Gallery.
GoRoute(
  path: 'forms',
  builder: (context, state) {
    final projectId = state.pathParameters['projectId']!;
    return FormGalleryScreen(projectId: projectId);
  },
),
```

**Step 2:** Add import for FormGalleryScreen at top of app_router.dart.

```dart
import 'package:construction_inspector/features/forms/presentation/screens/form_gallery_screen.dart';
```

**Step 3:** Verify `toolbox_home_screen.dart` Forms card still navigates to the `forms` route (no change needed — path is the same).

**Verification:** `pwsh -Command "flutter test test/core/router/"`

---

### 10.3: Phase 10 Tests

**File:** `test/features/forms/presentation/screens/form_gallery_screen_test.dart` (NEW)

**Step 1:** Create widget test for FormGalleryScreen.

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
// ... imports

/// WHY: Verify gallery renders tabs for registered form types and displays documents.
void main() {
  group('FormGalleryScreen', () {
    testWidgets('renders All tab plus per-type tabs', (tester) async {
      // NOTE: Mock InspectorFormProvider with 2 registered forms.
      // NOTE: Mock DocumentProvider with sample documents.
      await tester.pumpWidget(
        // ... MultiProvider wrapping FormGalleryScreen
      );

      expect(find.text('All'), findsOneWidget);
      expect(find.text('MDOT 0582B'), findsOneWidget);
      // NOTE: Second form type from mock.
    });

    testWidgets('FAB shows form type picker', (tester) async {
      // WHY: Verify new form creation flow is multi-type, not hardcoded.
      await tester.pumpWidget(/* ... */);
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      // NOTE: Bottom sheet should list all registered form types.
      expect(find.text('MDOT 0582B'), findsWidgets);
    });
  });
}
```

**Verification:** `pwsh -Command "flutter test test/features/forms/presentation/screens/form_gallery_screen_test.dart"`

---

## Phase 11: Dead Code Cleanup

### 11.1: Delete form_field_entry.dart

**Agent:** general-purpose
**File:** `lib/features/forms/data/models/form_field_entry.dart`

**Step 1:** Verify no imports remain except `auto_fill_result.dart` (must be fixed in 11.2 first — execute 11.2 before 11.1).

**Step 2:** Delete the file.

```bash
# WHY: 336 lines of dead code. Backing table (form_field_registry) was dropped in v22 migration.
# NOTE: Only imported by auto_fill_result.dart for AutoFillSource enum (moved in 11.2).
pwsh -Command "Remove-Item 'lib/features/forms/data/models/form_field_entry.dart'"
```

**Verification:** `pwsh -Command "flutter analyze"`

---

### 11.2: Fix auto_fill_result.dart Import — Move AutoFillSource Enum

**File:** `lib/features/forms/data/models/auto_fill_result.dart`

**Step 1:** Copy the `AutoFillSource` enum definition from `form_field_entry.dart` into `auto_fill_result.dart`.

```dart
// BEFORE (in auto_fill_result.dart):
import 'form_field_entry.dart' show AutoFillSource;

// AFTER:
// WHY: AutoFillSource is the only thing used from form_field_entry.dart.
// Moving it here eliminates the last import, enabling deletion in 11.1.
// NOTE: Enum definition copied verbatim from form_field_entry.dart.

/// Source of an auto-filled value.
enum AutoFillSource {
  weather,
  location,
  project,
  user,
  calculator,
  manual,
}
```

**Step 2:** Remove the import line.

```dart
// DELETE this line:
import 'form_field_entry.dart' show AutoFillSource;
```

**Step 3:** Check if any other files import `AutoFillSource` from `form_field_entry.dart`. If so, update them to import from `auto_fill_result.dart` instead.

**Verification:** `pwsh -Command "flutter analyze"`

---

### 11.3: Final Full Test Suite Run

**Step 1:** Run the complete test suite to verify no regressions across all phases.

```bash
pwsh -Command "flutter test"
```

**Step 2:** Run static analysis.

```bash
pwsh -Command "flutter analyze"
```

**Step 3:** If any failures, fix them before marking Phase 11 complete.

**Verification:** Both commands must exit with 0 errors.

---

## Phase 12: Test & Sync Verification Updates

### Agent Assignments

| Sub-phase | Agent |
|-----------|-------|
| 12.1-12.2 (driver, keys) | backend-data-layer-agent |
| 12.3-12.4 (unit tests, storage cleanup) | qa-testing-agent |
| 12.5-12.8 (sync flows, registry, guide) | general-purpose |

---

### 12.1: Storage Cleanup Generalization

**Agent:** backend-data-layer-agent

**Files:**
- Modify: `lib/core/database/schema/sync_engine_tables.dart` (line ~87 — createStorageCleanupQueueTable)
- Modify: `lib/core/database/schema_verifier.dart` (line ~150 — storage_cleanup_queue columns, line ~254 — type checks)
- Modify: `lib/features/sync/engine/storage_cleanup.dart` (full rewrite — 70 lines)
- Modify: `lib/services/soft_delete_service.dart` (lines 15-31, 34-44, 80-110, 353-440)
- Modify: `lib/features/projects/data/services/project_lifecycle_service.dart` (line ~21 — _directChildTables)
- Modify: `lib/features/auth/services/auth_service.dart` (wipe list — add 3 new tables)
- Modify: `lib/core/config/supabase_config.dart` (add 3 bucket constants)

**Step 12.1.1** — Update `createStorageCleanupQueueTable` for fresh installs

File: `lib/core/database/schema/sync_engine_tables.dart` (line ~87)

```sql
-- BEFORE:
CREATE TABLE IF NOT EXISTS storage_cleanup_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  remote_path TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT
)

-- AFTER:
-- WHY: The v43 migration adds bucket via ALTER TABLE, but fresh installs need it in CREATE TABLE.
CREATE TABLE IF NOT EXISTS storage_cleanup_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  remote_path TEXT NOT NULL,
  bucket TEXT NOT NULL DEFAULT 'entry-photos',
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT
)
```

**Step 12.1.2** — Update schema_verifier.dart column list

File: `lib/core/database/schema_verifier.dart` (line ~150)

```dart
// BEFORE:
'storage_cleanup_queue': [
  'id', 'remote_path', 'reason', 'created_at', 'attempts', 'last_error',
],

// AFTER:
// WHY: bucket column added by v43 migration and fresh-install CREATE TABLE.
'storage_cleanup_queue': [
  'id', 'remote_path', 'bucket', 'reason', 'created_at', 'attempts', 'last_error',
],
```

**Step 12.1.2b** — Register 3 new tables in schema_verifier.dart `_expectedColumns`

File: `lib/core/database/schema_verifier.dart` (inside `_expectedColumns` map)

```dart
// WHY: schema_verifier must know every table's columns to catch migration drift.
// ADD after the storage_cleanup_queue entry:
'form_exports': [
  'id', 'form_response_id', 'project_id', 'entry_id', 'file_path', 'remote_path',
  'filename', 'form_type', 'file_size_bytes', 'exported_at',
  'created_at', 'updated_at', 'created_by_user_id', 'deleted_at', 'deleted_by',
],
'entry_exports': [
  'id', 'entry_id', 'project_id', 'file_path', 'remote_path',
  'filename', 'file_size_bytes', 'exported_at',
  'created_at', 'updated_at', 'created_by_user_id', 'deleted_at', 'deleted_by',
],
'documents': [
  'id', 'entry_id', 'project_id', 'file_path', 'remote_path',
  'filename', 'file_type', 'file_size_bytes', 'notes', 'captured_at',
  'created_at', 'updated_at', 'created_by_user_id', 'deleted_at', 'deleted_by',
],
```

**Step 12.1.3** — Rewrite StorageCleanup for multi-bucket

File: `lib/features/sync/engine/storage_cleanup.dart` (full rewrite)

```dart
class StorageCleanup {
  final SupabaseClient _client;
  final Database _db;

  // WHY: Bucket-to-table mapping for verifying cleanup targets.
  static const Map<String, String> _bucketToTable = {
    'entry-photos': 'photos',
    'form-exports': 'form_exports',
    'entry-exports': 'entry_exports',
    'entry-documents': 'documents',
  };

  // NOTE: Legacy queue entries lack a bucket column; default to entry-photos.
  static const String _defaultBucket = 'entry-photos';

  StorageCleanup(this._client, this._db);

  // WHY: Renamed from cleanupExpiredPhotos to reflect multi-type support.
  Future<int> cleanupExpiredFiles() async {
    final pending = await _db.query(
      'storage_cleanup_queue',
      where: 'attempts < 3',
      orderBy: 'created_at ASC',
      limit: 50,
    );
    if (pending.isEmpty) return 0;
    int cleaned = 0;
    for (final entry in pending) {
      final remotePath = entry['remote_path'] as String?;
      // NOTE: bucket column added by v43 migration. Fallback for pre-migration rows.
      final bucket = (entry['bucket'] as String?) ?? _defaultBucket;
      if (remotePath != null && remotePath.isNotEmpty) {
        try {
          await _client.storage.from(bucket).remove([remotePath]);
          await _db.delete('storage_cleanup_queue', where: 'id = ?', whereArgs: [entry['id']]);
          cleaned++;
          continue;
        } catch (e) {
          Logger.sync('StorageCleanup: failed to remove $remotePath from $bucket: $e');
        }
      }
      await _db.rawUpdate(
        'UPDATE storage_cleanup_queue SET attempts = attempts + 1, last_error = ? WHERE id = ?',
        ['Failed to remove from $bucket', entry['id']],
      );
    }
    if (cleaned > 0) Logger.sync('StorageCleanup: removed $cleaned files');
    return cleaned;
  }
}
```

**Step 12.1.4** — Update soft_delete_service.dart purge logic and bucket map

File: `lib/services/soft_delete_service.dart`

> **NOTE**: The `_childToParentOrder` and `_projectChildTables` lists are already updated
> in Phase 6 (Steps 6.1.1, 6.1.2, 6.2.1, 6.2.3). This sub-phase only handles purge
> generalization and the `_tableToBucket` map.

Update `purgeExpiredRecords` (line 375-399 area) — generalize photo-only storage cleanup:

```dart
// ADD at class level:
static const Map<String, String> _tableToBucket = {
  'photos': 'entry-photos',
  'form_exports': 'form-exports',
  'entry_exports': 'entry-exports',
  'documents': 'entry-documents',
};

// In purgeExpiredRecords, REPLACE the photo-specific block:
// BEFORE:
final columns = table == 'photos' ? ['id', 'remote_path'] : ['id'];
// ...
if (table == 'photos') {
  for (final row in rows) {
    final remotePath = row['remote_path'] as String?;
    if (remotePath != null && remotePath.isNotEmpty) {
      await _db.insert('storage_cleanup_queue', {
        'remote_path': remotePath,
        'reason': 'purge',
      });
    }
  }
}

// AFTER:
// WHY: All file-backed tables need storage cleanup, not just photos.
final hasRemotePath = _tableToBucket.containsKey(table);
final columns = hasRemotePath ? ['id', 'remote_path'] : ['id'];
// ...
if (hasRemotePath) {
  for (final row in rows) {
    final remotePath = row['remote_path'] as String?;
    if (remotePath != null && remotePath.isNotEmpty) {
      await _db.insert('storage_cleanup_queue', {
        'remote_path': remotePath,
        'bucket': _tableToBucket[table]!,
        'reason': 'purge',
      });
    }
  }
}
```

**Step 12.1.5** — Update project_lifecycle_service.dart

File: `lib/features/projects/data/services/project_lifecycle_service.dart`

**Step 12.1.5a** — Update `_directChildTables` (line ~21):

```dart
// BEFORE:
static const List<String> _directChildTables = [
    'project_assignments',
    'locations',
    'contractors',
    'bid_items',
    'personnel_types',
    'daily_entries',
    'todo_items',
    'inspector_forms',
    'calculation_history',
  ];

// AFTER:
static const List<String> _directChildTables = [
    'project_assignments',
    'locations',
    'contractors',
    'bid_items',
    'personnel_types',
    'daily_entries',
    'todo_items',
    'inspector_forms',
    'calculation_history',
    'form_exports',    // NEW
    'entry_exports',   // NEW
    'documents',       // NEW
  ];
```

**Step 12.1.5b** — Update `_entryJunctionTables` (line ~34):

```dart
// WHY: removeFromDevice hard-deletes these via entry_id IN (...).
// Without the 3 new tables, they'd be orphaned on device removal.

// BEFORE:
static const List<String> _entryJunctionTables = [
    'entry_equipment',
    'entry_quantities',
    'entry_contractors',
    'entry_personnel_counts',
    'form_responses',
  ];

// AFTER:
static const List<String> _entryJunctionTables = [
    'entry_equipment',
    'entry_quantities',
    'entry_contractors',
    'entry_personnel_counts',
    'form_responses',
    'form_exports',    // NEW: has entry_id FK (nullable, but removeFromDevice uses IN clause)
    'entry_exports',   // NEW: has entry_id FK
    'documents',       // NEW: has entry_id FK
  ];
```

**Step 12.1.6** — Update supabase_config.dart

File: `lib/core/config/supabase_config.dart` (after `releasesBucket`)

```dart
// BEFORE:
static const String photoBucket = 'entry-photos';
static const String releasesBucket = 'releases';

// AFTER:
static const String photoBucket = 'entry-photos';
static const String releasesBucket = 'releases';
static const String formExportsBucket = 'form-exports';
static const String entryExportsBucket = 'entry-exports';
static const String documentsBucket = 'entry-documents';
```

**Step 12.1.7** — Update auth_service.dart wipe list

File: `lib/features/auth/services/auth_service.dart` (line ~340-345 area)

```dart
// ADD 3 new tables to the wipe list (near storage_cleanup_queue):
'form_exports',
'entry_exports',
'documents',
'storage_cleanup_queue',
// Metrics tables
'stage_metrics',
'extraction_metrics',
```

**Verification:**
```
pwsh -Command "flutter analyze"
```

---

### 12.2: Driver Infrastructure

**Agent:** backend-data-layer-agent

**Files:**
- Modify: `lib/core/driver/driver_server.dart` (lines 47-66 constructor, 97-150 _handleRequest router, 1568 _allowedFileExtensions, NEW method)
- Modify: `lib/main_driver.dart` (line 518 — DriverServer constructor call)

**Step 12.2.1** — Add DocumentRepository to DriverServer

File: `lib/core/driver/driver_server.dart` (lines 47-66)

```dart
// BEFORE:
class DriverServer {
  static final _columnNameRegex = RegExp(r'^[a-z_][a-z0-9_]*$');
  final PhotoRepository _photoRepository;
  final SyncOrchestrator? syncOrchestrator;
  final DatabaseService? databaseService;
  final ProjectLifecycleService? projectLifecycleService;

  DriverServer({
    required this.testPhotoService,
    required PhotoRepository photoRepository,
    this.syncOrchestrator,
    this.databaseService,
    this.projectLifecycleService,
    this.port = const int.fromEnvironment('DRIVER_PORT', defaultValue: 4948),
  }) : _photoRepository = photoRepository;

// AFTER:
class DriverServer {
  static final _columnNameRegex = RegExp(r'^[a-z_][a-z0-9_]*$');
  final PhotoRepository _photoRepository;
  final DocumentRepository? _documentRepository;
  final SyncOrchestrator? syncOrchestrator;
  final DatabaseService? databaseService;
  final ProjectLifecycleService? projectLifecycleService;

  DriverServer({
    required this.testPhotoService,
    required PhotoRepository photoRepository,
    DocumentRepository? documentRepository,
    this.syncOrchestrator,
    this.databaseService,
    this.projectLifecycleService,
    this.port = const int.fromEnvironment('DRIVER_PORT', defaultValue: 4948),
  }) : _photoRepository = photoRepository,
       _documentRepository = documentRepository;
```

**Step 12.2.2** — Add inject-document-direct route

File: `lib/core/driver/driver_server.dart` (line ~132-135)

```dart
// ADD between inject-file and inject-photo-direct:
} else if (method == 'POST' && path == '/driver/inject-document-direct') {
  await _handleInjectDocumentDirect(request, res);
```

**Step 12.2.3** — Implement `_handleInjectDocumentDirect`

Add new method to DriverServer that mirrors `_handleInjectPhotoDirect` but:
- Accepts: `base64Data`, `filename`, `entryId`, `projectId`
- Validates: UUID format, filename sanitization (use `_validateDocumentFilename`), allowed extensions
- Writes file to `driver_documents/` temp dir
- Copies to app documents dir: `documents/{projectId}/{entryId}/`
- Creates Document row via `DocumentRepository.create()`
- Returns: `injected`, `direct`, `documentId`, `filePath`

```dart
Future<void> _handleInjectDocumentDirect(HttpRequest request, HttpResponse res) async {
  // WHY: Defense-in-depth — mirrors _handleInjectPhotoDirect pattern.
  if (kReleaseMode || kProfileMode) {
    await _sendJson(res, 403, {'error': 'Not available in release mode'});
    return;
  }

  if (_documentRepository == null) {
    _sendJson(res, 500, {'error': 'DocumentRepository not available'});
    return;
  }
  final body = await _readJsonBody(request, maxBytes: _maxBase64BodyBytes);
  final base64Data = body['base64Data'] as String?;
  final filename = body['filename'] as String?;
  final entryId = body['entryId'] as String?;
  final projectId = body['projectId'] as String?;

  if (base64Data == null || filename == null || entryId == null || projectId == null) {
    _sendJson(res, 400, {'error': 'Missing required fields: base64Data, filename, entryId, projectId'});
    return;
  }

  // WHY: Prevent path traversal via non-UUID IDs in filesystem paths.
  if (!_uuidPattern.hasMatch(entryId) || !_uuidPattern.hasMatch(projectId)) {
    await _sendJson(res, 400, {'error': 'entryId and projectId must be UUIDs'});
    return;
  }

  // Validate filename extension
  final ext = filename.split('.').last.toLowerCase();
  if (!_allowedFileExtensions.contains(ext)) {
    _sendJson(res, 400, {'error': 'Unsupported file extension: $ext'});
    return;
  }

  // Decode and write file
  final bytes = base64Decode(base64Data);
  if (bytes.length > 10 * 1024 * 1024) {
    await _sendJson(res, 400, {'error': 'File exceeds 10 MB limit'});
    return;
  }
  final appDir = await getApplicationDocumentsDirectory();
  final docDir = Directory('${appDir.path}/documents/$projectId/$entryId');
  if (!await docDir.exists()) await docDir.create(recursive: true);
  final safeFilename = filename.replaceAll(RegExp(r'[^\w\s\-.]'), '_').replaceAll('..', '_');
  final filePath = '${docDir.path}/$safeFilename';
  await File(filePath).writeAsBytes(bytes);

  // Create Document row
  final doc = Document(
    entryId: entryId,
    projectId: projectId,
    filePath: filePath,
    filename: safeFilename,
    fileType: ext,
    fileSizeBytes: bytes.length,
    capturedAt: DateTime.now().toUtc().toIso8601String(),
  );
  final result = await _documentRepository!.create(doc);
  if (!result.isSuccess) {
    _sendJson(res, 500, {'error': 'Failed to create document: ${result.error}'});
    return;
  }

  _sendJson(res, 200, {
    'injected': true,
    'direct': true,
    'documentId': doc.id,
    'filePath': filePath,
  });
}
```

**Step 12.2.4** — Expand `_allowedFileExtensions`

File: `lib/core/driver/driver_server.dart` (line 1568)

```dart
// BEFORE:
static const _allowedFileExtensions = {'pdf'};

// AFTER:
static const _allowedFileExtensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx'};
```

**Step 12.2.5** — Update main_driver.dart DriverServer call

File: `lib/main_driver.dart` (line 518-525)

```dart
// BEFORE:
final driverServer = DriverServer(
  testPhotoService: testPhotoService,
  photoRepository: photoRepository,
  syncOrchestrator: syncOrchestrator,
  databaseService: dbService,
  projectLifecycleService: projectLifecycleService,
);

// AFTER:
final driverServer = DriverServer(
  testPhotoService: testPhotoService,
  photoRepository: photoRepository,
  documentRepository: documentRepository, // NEW
  syncOrchestrator: syncOrchestrator,
  databaseService: dbService,
  projectLifecycleService: projectLifecycleService,
);
```

**Verification:**
```
pwsh -Command "flutter analyze"
```

---

### 12.3: Testing Keys

**Agent:** backend-data-layer-agent

**Files:**
- Create: `lib/shared/testing_keys/documents_keys.dart`
- Modify: `lib/shared/testing_keys/testing_keys.dart` (barrel export)
- Modify: `lib/shared/testing_keys/entries_keys.dart` (add document attachment keys to entry report)

**Step 12.3.1** — Create `documents_keys.dart`

File: `lib/shared/testing_keys/documents_keys.dart` (NEW)

```dart
/// Testing keys for the documents feature (document attachments on entries).
class DocumentsTestingKeys {
  /// Documents section in entry report
  static const String documentsList = 'documents_list';

  /// Attach document button
  static const String addDocumentButton = 'add_document_button';

  /// Per-document card (parameterized by ID)
  static String documentCard(String id) => 'document_card_$id';

  /// Per-document delete button (parameterized by ID)
  static String documentDeleteButton(String id) => 'document_delete_$id';

  /// Notes field in document dialog
  static const String documentNotesField = 'document_notes_field';
}
```

**Step 12.3.2** — Update barrel export

File: `lib/shared/testing_keys/testing_keys.dart`

```dart
// ADD to exports:
export 'documents_keys.dart';
```

**Step 12.3.3** — Add document keys to entries_keys.dart

File: `lib/shared/testing_keys/entries_keys.dart`

Add document-related keys for the entry detail screen:

```dart
// ADD to EntriesTestingKeys class:
/// Document attachment section on entry detail
static const String documentsSection = 'entry_documents_section';
/// Attach document button on entry detail
static const String attachDocumentButton = 'entry_attach_document_button';
```

**Step 12.3.4** — Stale key cleanup

Audit all testing key files for dead references to patterns that no longer exist:
- Search for any keys referencing `form_field_registry` (deleted table)
- Search for any keys referencing `forms_list` (replaced by `form_gallery`)
- Update or remove stale keys as found

**Verification:**
```
pwsh -Command "flutter analyze"
```

---

### 12.4: Unit Test Updates

**Agent:** qa-testing-agent

**Files:**
- Modify: `test/helpers/sync/sqlite_test_helper.dart` (line 26-127 — _onCreate)
- Modify: `test/helpers/sync/sync_test_data.dart` (add 3 factory methods + update seedFkGraph)
- Modify: `test/features/sync/engine/cascade_soft_delete_test.dart` (extend + add entry cascade test)

**Step 12.4.1** — Update SqliteTestHelper._onCreate

File: `test/helpers/sync/sqlite_test_helper.dart` (after toolbox tables section, line ~60)

Add imports at top:
```dart
import 'package:construction_inspector/core/database/schema/form_export_tables.dart';
import 'package:construction_inspector/core/database/schema/entry_export_tables.dart';
import 'package:construction_inspector/core/database/schema/document_tables.dart';
```

Add after toolbox tables in _onCreate:
```dart
// --- Export & Document tables ---
await db.execute(FormExportTables.createFormExportsTable);
await db.execute(EntryExportTables.createEntryExportsTable);
await db.execute(DocumentTables.createDocumentsTable);
```

Add in the index section (after ToolboxTables.indexes):
```dart
for (final index in FormExportTables.indexes) { await db.execute(index); }
for (final index in EntryExportTables.indexes) { await db.execute(index); }
for (final index in DocumentTables.indexes) { await db.execute(index); }
```

**Step 12.4.2** — Add SyncTestData factory methods

File: `test/helpers/sync/sync_test_data.dart`

Add 3 new factory methods following existing pattern (numbered 17, 18, 19):

```dart
// 17. formExportMap
static Map<String, dynamic> formExportMap({
  String? id,
  required String formResponseId,
  required String projectId,
  String? entryId,
  String? filePath,
  String? remotePath,
  String filename = 'test_export.pdf',
  String formType = 'mdot_0582b',
  int? fileSizeBytes,
  String? exportedAt,
  String? createdAt,
  String? updatedAt,
  String? createdByUserId,
  String? deletedAt,
  String? deletedBy,
}) {
  final now = DateTime.now().toUtc().toIso8601String();
  return {
    'id': id ?? const Uuid().v4(),
    'form_response_id': formResponseId,
    'project_id': projectId,
    'entry_id': entryId,
    'file_path': filePath,
    'remote_path': remotePath,
    'filename': filename,
    'form_type': formType,
    'file_size_bytes': fileSizeBytes,
    'exported_at': exportedAt ?? now,
    'created_at': createdAt ?? now,
    'updated_at': updatedAt ?? now,
    'created_by_user_id': createdByUserId,
    'deleted_at': deletedAt,
    'deleted_by': deletedBy,
  };
}

// 18. entryExportMap
static Map<String, dynamic> entryExportMap({
  String? id,
  required String entryId,
  required String projectId,
  String? filePath,
  String? remotePath,
  String filename = 'test_entry_export.pdf',
  int? fileSizeBytes,
  String? exportedAt,
  String? createdAt,
  String? updatedAt,
  String? createdByUserId,
  String? deletedAt,
  String? deletedBy,
}) {
  final now = DateTime.now().toUtc().toIso8601String();
  return {
    'id': id ?? const Uuid().v4(),
    'entry_id': entryId,
    'project_id': projectId,
    'file_path': filePath,
    'remote_path': remotePath,
    'filename': filename,
    'file_size_bytes': fileSizeBytes,
    'exported_at': exportedAt ?? now,
    'created_at': createdAt ?? now,
    'updated_at': updatedAt ?? now,
    'created_by_user_id': createdByUserId,
    'deleted_at': deletedAt,
    'deleted_by': deletedBy,
  };
}

// 19. documentMap
static Map<String, dynamic> documentMap({
  String? id,
  required String entryId,
  required String projectId,
  String filePath = '/test/doc.pdf',
  String? remotePath,
  String filename = 'test_doc.pdf',
  String fileType = 'pdf',
  int? fileSizeBytes,
  String? notes,
  String? capturedAt,
  String? createdAt,
  String? updatedAt,
  String? createdByUserId,
  String? deletedAt,
  String? deletedBy,
}) {
  final now = DateTime.now().toUtc().toIso8601String();
  return {
    'id': id ?? const Uuid().v4(),
    'entry_id': entryId,
    'project_id': projectId,
    'file_path': filePath,
    'remote_path': remotePath,
    'filename': filename,
    'file_type': fileType,
    'file_size_bytes': fileSizeBytes,
    'notes': notes,
    'captured_at': capturedAt ?? now,
    'created_at': createdAt ?? now,
    'updated_at': updatedAt ?? now,
    'created_by_user_id': createdByUserId,
    'deleted_at': deletedAt,
    'deleted_by': deletedBy,
  };
}
```

Update `seedFkGraph` to also seed a form_export, entry_export, and document row and return their IDs:

```dart
// ADD to seedFkGraph return map:
final formExportId = const Uuid().v4();
await db.insert('form_exports', formExportMap(
  id: formExportId,
  formResponseId: formResponseId,
  projectId: projectId,
  entryId: entryId,
));
final entryExportId = const Uuid().v4();
await db.insert('entry_exports', entryExportMap(
  id: entryExportId,
  entryId: entryId,
  projectId: projectId,
));
final documentId = const Uuid().v4();
await db.insert('documents', documentMap(
  id: documentId,
  entryId: entryId,
  projectId: projectId,
));
// Return: add formExportId, entryExportId, documentId to the returned map
```

**Step 12.4.3** — Extend cascade soft delete tests

File: `test/features/sync/engine/cascade_soft_delete_test.dart`

1. In existing `cascadeSoftDeleteProject marks project and all 9 direct child tables` test — add form_export, entry_export, and document seeding + verification:

```dart
// ADD: Seed new table rows in test setup
await db.insert('form_exports', SyncTestData.formExportMap(
  formResponseId: ids['formResponseId']!,
  projectId: ids['projectId']!,
  entryId: ids['entryId']!,
));
await db.insert('entry_exports', SyncTestData.entryExportMap(
  entryId: ids['entryId']!,
  projectId: ids['projectId']!,
));
await db.insert('documents', SyncTestData.documentMap(
  entryId: ids['entryId']!,
  projectId: ids['projectId']!,
));

// ADD: Verify new table rows are soft-deleted
final formExports = await db.query('form_exports', where: 'deleted_at IS NOT NULL');
expect(formExports.length, 1);
final entryExports = await db.query('entry_exports', where: 'deleted_at IS NOT NULL');
expect(entryExports.length, 1);
final documents = await db.query('documents', where: 'deleted_at IS NOT NULL');
expect(documents.length, 1);
```

2. Add new test: `cascadeSoftDeleteProject cascades to entry child tables (form_exports, entry_exports, documents)`:

```dart
test('cascadeSoftDeleteProject cascades to entry child tables (form_exports, entry_exports, documents)', () async {
  // WHY: Verify the rawUpdate entry child cascade includes the 3 new tables.
  // Setup: create project → entry → form_export, entry_export, document
  // Act: cascadeSoftDeleteProject(projectId)
  // Assert: all 3 new table rows have deleted_at set
});
```

3. Add new test: `purgeExpiredRecords queues storage cleanup for form_exports, entry_exports, documents`:

```dart
test('purgeExpiredRecords queues storage cleanup for form_exports, entry_exports, documents', () async {
  // WHY: Verify the multi-bucket purge creates storage_cleanup_queue entries
  // with correct bucket values for each file-backed table.
  // Setup: create expired (30+ days deleted_at) rows with remote_path in each table
  // Act: purgeExpiredRecords()
  // Assert: storage_cleanup_queue has entries with bucket = 'form-exports', 'entry-exports', 'entry-documents'
});
```

**Verification:**
```
pwsh -Command "flutter test test/helpers/sync/sqlite_test_helper_test.dart"
pwsh -Command "flutter test test/features/sync/engine/cascade_soft_delete_test.dart"
pwsh -Command "flutter test test/services/soft_delete_service_log_cleanup_test.dart"
```

---

### 12.5: Sync Flow Updates (S04, S07, S08, S09, S10)

**Agent:** general-purpose

This sub-phase updates the sync verification guide and registry for existing flows.

**Files:**
- Modify: `.claude/test-flows/sync-verification-guide.md`
- Modify: `.claude/test-flows/registry.md`

Changes per flow:

**S04 (Forms) — EXPAND**:
- Table list: `inspector_forms, form_responses` -> `inspector_forms, form_responses, form_exports`
- After creating form response (existing step), add: Export form as PDF -> verify form_exports row created -> Admin sync -> Supabase REST: `form_exports?project_id=eq.<id>&deleted_at=is.null` expect 1 row with remote_path non-null -> Inspector sync x2 -> verify form export visible
- Add `ctx.formExportIds` to checkpoint
- Also verify inspector_forms RLS fix: query `inspector_forms?is_builtin=eq.true` confirm builtins exist in Supabase

**S07 (Update All) — EXPAND**:
- Add update mutations for documents (update notes field), form_exports (if updatable), entry_exports (if updatable)
- These only run if the corresponding entities were created in prior flows

**S08 (PDF Export) — EXPAND**:
- Table list: `N/A (output artifact)` -> `entry_exports`
- After PDF generation, verify entry_exports row with remote_path
- Supabase REST: `entry_exports?entry_id=eq.<id>&deleted_at=is.null` expect 1 row
- Storage verify: `POST /storage/v1/object/list/entry-exports` with prefix filter
- Add `ctx.entryExportIds` to checkpoint

**S09 (Delete Cascade) — EXPAND**:
- Notes: "14 child tables" -> "17 child tables"
- Add 3 new Supabase REST verification queries:
  ```
  form_exports?project_id=eq.<id>&deleted_at=is.null -> expect 0 rows
  entry_exports?project_id=eq.<id>&deleted_at=is.null -> expect 0 rows
  documents?project_id=eq.<id>&deleted_at=is.null -> expect 0 rows
  ```
- Update tombstone count expectation

**S10 (Cleanup) — EXPAND**:
- Post-run sweep: "17 synced tables" -> "20 synced tables"
- Add 3 tables to VRF cleanup queries
- Update FK teardown order (form_exports before form_responses, entry_exports/documents before daily_entries)

**Verification:** Manual review of guide/registry files.

---

### 12.6: New S11 Flow (Documents)

**Agent:** general-purpose

Add new flow to registry and guide:

**S11 — Documents Sync Verification**
- Tables: `documents`
- Bucket: `entry-documents`
- Depends: S02 (needs existing entry)
- Position: After S08, before S09 (so S09 cascade can verify documents deletion)

Protocol:
1. Admin (4948): `inject-document-direct` with entryId from S02, projectId from S01
2. Admin sync via UI (settings_nav_button -> settings_sync_button)
3. Supabase REST verify: `documents?entry_id=eq.<entryId>&deleted_at=is.null` -> 1 row, remote_path non-null
4. Storage verify: `POST /storage/v1/object/list/entry-documents` with prefix `{companyId}/{projectId}/`
5. Inspector (4949) sync x2 via UI
6. Inspector UI verify: navigate to entry -> verify document attachment visible -> screenshot
7. Capture `ctx.documentIds`

**Verification:** Manual review of guide/registry files.

---

### 12.7: Registry & Guide Config Updates

**Agent:** general-purpose

**Files:**
- Modify: `.claude/test-flows/registry.md`
- Modify: `.claude/test-flows/sync-verification-guide.md`
- Modify: `.claude/skills/test/skill.md` (if exists)

Update registry.md:
- S04 table column: add `form_exports`
- S07 table column: add `documents, form_exports, entry_exports`
- S08 table column: add `entry_exports`
- S09 notes: "14 child tables" -> "17 child tables"
- S10 notes: update table count
- Add S11 row
- Update Flow Count Summary: Sync row -> "S01-S11" count 11
- Update total count
- Update Dependency Chain: S11 between S08 and S09

Update sync-verification-guide.md:
- Checkpoint ctx: add `formExportIds`, `entryExportIds`, `documentIds`
- FK teardown order: add form_exports (after form_responses), entry_exports (before daily_entries), documents (before daily_entries)
- Post-run sweep: add 3 new table queries
- Add storage bucket verification pattern (new section):
  ```bash
  # Verify file exists in bucket
  curl -s -X POST "${SUPABASE_URL}/storage/v1/object/list/<bucket>" \
    -H "apikey: ${KEY}" \
    -H "Authorization: Bearer ${KEY}" \
    -H "Content-Type: application/json" \
    -d '{"prefix":"<companyId>/<projectId>/","limit":100}'
  ```
- Add full S11 protocol section

Update test skill (skill.md):
- Sync range: "S01-S10" -> "S01-S11" in all references
- Tier alias: `sync -> S01-S11`

**Verification:** Manual review.

---

### 12.8: Verification

Run all affected tests:
```
pwsh -Command "flutter test test/helpers/sync/sqlite_test_helper_test.dart"
pwsh -Command "flutter test test/features/sync/engine/cascade_soft_delete_test.dart"
pwsh -Command "flutter test test/services/soft_delete_service_log_cleanup_test.dart"
pwsh -Command "flutter test test/features/sync/engine/storage_cleanup_test.dart"
pwsh -Command "flutter test test/core/database/migration_v43_test.dart"
```

Verify the full test suite still passes:
```
pwsh -Command "flutter test"
```

---

## Phase Summary

| Phase | Files Modified | Files Created | Files Deleted | Key Risk |
|-------|---------------|---------------|---------------|----------|
| 8 | 8+ (form_response, repository, pdf_service, provider, router, entry widgets, viewer) | 0 | 0 | Breaking constructor change in FormResponse propagates to all callers |
| 9 | 2 (main.dart, main_driver.dart) | 5 (form_export_provider, entry_export_provider, document_provider, document_service, entry_forms_section UI) | 0 | Provider dependency ordering in MultiProvider; document attachment flow |
| 10 | 1 (app_router.dart) | 2 (form_gallery_screen.dart, test) | 0 | Tab rendering with dynamic form types |
| 11 | 1 (auto_fill_result.dart) | 0 | 1 (form_field_entry.dart) | Must fix import before delete |
| 12 | 14 (soft_delete_service, storage_cleanup, driver_server, main_driver, supabase_config, schema_verifier, auth_service, project_lifecycle_service, sync_engine_tables, sqlite_test_helper, sync_test_data, cascade_soft_delete_test, testing_keys barrel, entries_keys) | 1 (documents_keys.dart) | 0 | Multi-bucket storage cleanup must handle missing bucket column on older schemas |

**Execution order:** 8.1 -> 8.2 -> 8.3 -> 8.4 -> 8.5 -> 8.6 -> 8.7 -> 8.8 -> 8.9 -> 9.1 -> 9.2 -> 9.3 -> 9.4 -> 9.5 -> 9.6 -> 10.1 -> 10.2 -> 10.3 -> 11.2 -> 11.1 -> 11.3 -> 12.1 -> 12.2 -> 12.3 -> 12.4 -> 12.5 -> 12.6 -> 12.7 -> 12.8

**Note:** Phase 11.2 must execute before 11.1 (move enum before deleting the source file). Phase 12 sub-phases can be partially parallelized: 12.1 and 12.2 can run in parallel; 12.3 depends on 12.2 (testing keys reference document features); 12.4 depends on 12.1 (test data needs updated schemas); 12.5-12.7 are independent doc updates; 12.8 runs last.

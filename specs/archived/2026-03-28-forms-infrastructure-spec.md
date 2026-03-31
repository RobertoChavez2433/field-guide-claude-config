# Forms Infrastructure & Document Storage Spec

**Created**: 2026-03-28
**Status**: APPROVED
**Sizing**: L (multi-phase, security-sensitive)
**Related**: AASHTOWARE Plan Phase 9.2, Delete Flow Fix (S09)

---

## Overview

### Purpose
Build the infrastructure to scale from 1 form (MDOT 0582B) to 20+, with durable cloud storage for all exported artifacts (forms, entries/IDRs, document attachments), fix the RLS bug blocking form sync, and refactor hardcoded 0582B references into an extensible registry.

### Scope — IN
1. Fix inspector_forms RLS bug (NOT NULL constraint + policy + sync scope)
2. Extensible form registry (seed multiple builtins, form-type dispatch, per-type galleries)
3. `form_exports` storage system — local files + Supabase bucket for exported form PDFs
4. `entry_exports` storage system — same pattern for IDR/entry PDFs
5. `documents` table + storage — PDF/XLS attachments on entries
6. SQLite + Supabase schemas for all new tables
7. Form gallery in toolbox (per-type browsable views)
8. Soft delete cascade fix for inspector_forms
9. Refactor 40+ hardcoded 0582B references into registry pattern

### Scope — OUT
- AASHTOWARE/MDOT mode integration
- Custom form template uploads (admin-created forms)
- New form type implementations beyond 0582B
- MILogin OAuth2

### Success Criteria
- [ ] Builtin forms sync to Supabase without RLS denial
- [ ] All exported form PDFs stored locally AND synced to cloud
- [ ] All exported entry/IDR PDFs stored locally AND synced to cloud
- [ ] Document attachments (PDF/XLS) can be attached to entries and synced
- [ ] Form gallery shows responses grouped by form type
- [ ] Adding a new form type requires: config entry + template asset + calculator + screen (no hardcoded references elsewhere)
- [ ] Zero hardcoded `is0582B` or `'mdot_0582b'` checks outside of 0582B-specific implementation files
- [ ] All three new tables sync correctly via three-phase push
- [ ] RLS policies enforce ownership (create/edit/delete own only, view all on project)
- [ ] 3175+ existing tests still pass

---

## Approach Selected

**Storage Architecture: Three Separate Tables, Three Separate Buckets (Option B)**

Each file type gets its own Supabase storage bucket and its own metadata table. Full isolation — a bug in one doesn't affect others. Simpler per-bucket RLS.

**Rejected alternatives:**
- Option A (one shared bucket): One misconfigured policy affects all file types. Path-prefix RLS more complex.
- Option C (one unified table): Nullable FKs everywhere, queries need discriminator filters, violates codebase's clean domain separation.

---

## Data Model

### 1. Fix: `inspector_forms` (existing table)

**Supabase migration**:
- `ALTER TABLE inspector_forms ALTER COLUMN project_id DROP NOT NULL`
- Drop + recreate all 4 RLS policies to allow `is_builtin = true` access
- No re-seed needed — app seeds locally on startup, syncs up

**Sync engine**:
- `InspectorFormAdapter` pull filter: `.or('is_builtin.eq.true,project_id.in.(${syncedProjectIds})')`
- Push: builtins push with `project_id = null`, RLS allows via `is_builtin = true`
- Add `inspector_forms` to `tablesWithDirectProjectId` for project-scoped forms (builtins keep null in change_log)

**Soft delete**:
- Add to `SoftDeleteService._projectChildTables` with guard: only cascade where `is_builtin = 0`

### 2. New: `form_exports`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | TEXT PK | Yes | UUID |
| form_response_id | TEXT FK | Yes | -> form_responses.id |
| project_id | TEXT FK | Yes | -> projects.id (denormalized) |
| entry_id | TEXT FK | No | -> daily_entries.id (nullable, form may not be entry-linked) |
| file_path | TEXT | No | Local filesystem path |
| remote_path | TEXT | No | Supabase storage path |
| filename | TEXT | Yes | Human-readable name (naming convention) |
| form_type | TEXT | Yes | e.g. 'mdot_0582b' -- for gallery filtering |
| file_size_bytes | INTEGER | No | For storage management |
| exported_at | TEXT | Yes | When the export was generated |
| created_at | TEXT | Yes | Row creation |
| updated_at | TEXT | Yes | Row modification |
| created_by_user_id | TEXT | No | Audit trail |
| deleted_at | TEXT | No | Soft delete |
| deleted_by | TEXT | No | Soft delete |

**FKs**: `form_response_id -> form_responses(id) ON DELETE CASCADE`, `project_id -> projects(id) ON DELETE CASCADE`, `entry_id -> daily_entries(id) ON DELETE SET NULL`

**Supabase bucket**: `form-exports`
**Storage path**: `{companyId}/{projectId}/{formType}/{filename}`

**Indexes**: `project_id`, `entry_id`, `form_response_id`, `form_type`, `deleted_at`

### 3. New: `entry_exports`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | TEXT PK | Yes | UUID |
| entry_id | TEXT FK | Yes | -> daily_entries.id |
| project_id | TEXT FK | Yes | -> projects.id (denormalized) |
| file_path | TEXT | No | Local filesystem path |
| remote_path | TEXT | No | Supabase storage path |
| filename | TEXT | Yes | Human-readable name |
| file_size_bytes | INTEGER | No | For storage management |
| exported_at | TEXT | Yes | When the export was generated |
| created_at | TEXT | Yes | Row creation |
| updated_at | TEXT | Yes | Row modification |
| created_by_user_id | TEXT | No | Audit trail |
| deleted_at | TEXT | No | Soft delete |
| deleted_by | TEXT | No | Soft delete |

**FKs**: `entry_id -> daily_entries(id) ON DELETE CASCADE`, `project_id -> projects(id) ON DELETE CASCADE`

**Supabase bucket**: `entry-exports`
**Storage path**: `{companyId}/{projectId}/{entryId}/{filename}`

**Indexes**: `project_id`, `entry_id`, `deleted_at`

### 4. New: `documents`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | TEXT PK | Yes | UUID |
| entry_id | TEXT FK | Yes | -> daily_entries.id |
| project_id | TEXT FK | Yes | -> projects.id (denormalized) |
| file_path | TEXT | No | Local filesystem path |
| remote_path | TEXT | No | Supabase storage path |
| filename | TEXT | Yes | Original filename |
| file_type | TEXT | Yes | MIME type or extension (pdf, xlsx, etc.) |
| file_size_bytes | INTEGER | No | For storage management |
| notes | TEXT | No | User description/caption |
| captured_at | TEXT | Yes | When the file was picked/attached |
| created_at | TEXT | Yes | Row creation |
| updated_at | TEXT | Yes | Row modification |
| created_by_user_id | TEXT | No | Audit trail |
| deleted_at | TEXT | No | Soft delete |
| deleted_by | TEXT | No | Soft delete |

**FKs**: `entry_id -> daily_entries(id) ON DELETE CASCADE`, `project_id -> projects(id) ON DELETE CASCADE`

**Supabase bucket**: `entry-documents`
**Storage path**: `{companyId}/{projectId}/{entryId}/{filename}`

**Indexes**: `project_id`, `entry_id`, `file_type`, `deleted_at`

---

## Form Registry Architecture

### Seed Registry

Replace `seedBuiltinForms()` with a declarative list:

```dart
const builtinForms = [
  BuiltinFormConfig(
    id: 'mdot_0582b',
    name: 'MDOT 0582B Density',
    templateAsset: 'assets/templates/forms/mdot_0582b_form.pdf',
    fieldDefinitions: '...', // populated JSON
    tableRowConfig: '...',
    parsingKeywords: '...',
  ),
  // Form #2, #3... added here later
];
```

Seed function iterates the list, checks each by ID (not `hasBuiltinForms()` which only checks "any exist"), and creates/updates as needed.

### Form-Type Dispatch Interfaces

Five registries, each mapping `formType` string -> implementation:

| Registry | Purpose | 0582B Implementation |
|----------|---------|---------------------|
| `FormCalculatorRegistry` | Math/computation | `Mdot0582BCalculator` |
| `FormValidatorRegistry` | Required field validation | `Mdot0582BValidator` (extracted from `validateRequiredFields`) |
| `FormInitialDataFactory` | Empty response data shape | Returns `{test_rows: [], proctor_rows: [], ...}` |
| `FormPdfFillerRegistry` | PDF field mapping | `Mdot0582BPdfFiller` (extracted from `_fillMdot0582bFields`) |
| `FormScreenRegistry` | UI screen dispatch | `MdotHubScreen` (existing, unchanged) |

Each registry is a simple `Map<String, T>` populated at app init. The router, provider, PDF service, and repository all look up by `formType` instead of hardcoding `is0582B` checks.

### What Moves vs What Stays

**Moves behind interfaces** (40+ hardcoded references):
- Router `form-fill` -> dispatches via `FormScreenRegistry`
- `FormResponse` default `formType` -> no default, required parameter
- `validateRequiredFields()` -> delegates to `FormValidatorRegistry`
- `_fillMdot0582bFields()` -> delegates to `FormPdfFillerRegistry`
- `entry_forms_section._startForm()` initial data -> `FormInitialDataFactory`
- Provider `appendMdot0582bProctorRow/TestRow` -> calculator registry methods
- `forms_list_screen` -> dynamic `FormGalleryScreen` from registry
- `entry_form_card.dart` quick actions -> screen registry provides action config

**Stays as-is** (0582B-specific implementation files):
- `MdotHubScreen`, `hub_header_content`, `hub_proctor_content`, `hub_quick_test_content`
- `mdot_0582b_calculator.dart`, `one_point_calculator.dart`
- Template asset `mdot_0582b_form.pdf`

### `fieldDefinitions` JSON Population

Currently NULL for 0582B. Populate so the generic PDF fill path works as fallback, but the 0582B-specific `FormPdfFiller` takes priority when registered. Future simple forms can work with just `fieldDefinitions` JSON and no custom Dart code.

---

## Storage & Sync

### Three-Phase Push (mirrors photo pattern)

All three new tables use the same three-phase push as photos:

1. **Upload file** to Supabase Storage bucket -> get `remote_path`
2. **Upsert metadata row** to Supabase table with `remote_path`
3. **Mark local synced** -- update local SQLite with `remote_path` + server `updated_at`

If Phase 2 fails, Phase 1's uploaded file is cleaned up immediately. Each table gets its own sync adapter with `isFileAdapter => true` (renamed from `isPhotoAdapter` to be generic).

### Sync Adapters

| Adapter | Table | Bucket | Scope | FK Dependencies | Registry Position |
|---------|-------|--------|-------|-----------------|-------------------|
| `InspectorFormAdapter` (fix) | inspector_forms | -- | viaProjectOrBuiltin | projects | stays at 14 |
| `FormExportAdapter` (new) | form_exports | `form-exports` | viaProject | projects, form_responses | after form_responses (16) |
| `EntryExportAdapter` (new) | entry_exports | `entry-exports` | viaProject | projects, daily_entries | after daily_entries (~10) |
| `DocumentAdapter` (new) | documents | `entry-documents` | viaProject | projects, daily_entries | after daily_entries (~11) |

### Pull Behavior

Metadata rows pull normally. Files are NOT downloaded during pull. `file_path` stays null on pulled records, `remote_path` is populated. UI uses signed URLs for display/viewing. Optional download-on-demand when user taps to view.

`localOnlyColumns => ['file_path']` on all three file adapters.

### Orphan Scanner & Cleanup

Extend existing `OrphanScanner` and `StorageCleanup` to handle all four buckets (existing `entry-photos` + three new). Scanner already accepts a bucket parameter -- iterate the list.

### Inspector Forms Sync Fix

**Supabase**: Drop NOT NULL on `project_id`. Update RLS policies for builtin awareness.

**Sync engine**: `InspectorFormAdapter` pull filter uses `.or('is_builtin.eq.true,project_id.in.(ids)')`. Push allows null `project_id` for builtins.

**Change tracker**: Add `inspector_forms` to `tablesWithDirectProjectId` for project-scoped forms.

### Sync Orchestrator Buckets

```dart
'Forms': ['inspector_forms', 'form_responses', 'form_exports'],
'Entries': [...existing..., 'entry_exports'],
'Documents': ['documents'],
```

---

## User Flow & UI

### Form Gallery (Toolbox)

Existing "Forms" card in Toolbox opens a new `FormGalleryScreen`:

```
Toolbox Home
  -> Forms (existing card)
       -> Form Gallery Screen (new)
             [All Forms] tab -- all responses across types, sorted by date
             [MDOT 0582B] tab -- filtered to 0582b responses
             [Form Type #2] tab -- (future, auto-generated from registry)
```

Each tab shows response cards with status badges (draft/completed/exported). Tapping opens via `FormScreenRegistry`. FAB shows `FormSelectionDialog` listing all registered types. Exported forms show file icon indicating PDF artifact exists.

### Entry Detail -- Forms Section

- Form cards show type name from registry (not hardcoded "0582B")
- Quick actions dispatch through calculator registry
- New "Attach Document" button -> `FilePicker` for PDF/XLS
- Documents section below forms showing attached files

### Entry Detail -- Exports Section

- Entry export PDF (if exists) with timestamp, view/share actions
- Form export PDFs linked to entry's form responses
- "Export Entry" button generates + stores IDR PDF (creates `entry_exports` row + three-phase sync)

### Export Flow

1. PDF generated from data (existing logic)
2. File saved to local date-folder structure (existing behavior, unchanged)
3. **New**: metadata row created in `form_exports` or `entry_exports` with `file_path`
4. **New**: on next sync, three-phase push uploads file + syncs metadata
5. Status on `form_response` moves to `exported`

Local date-folder export remains the "hand to the office" deliverable. Cloud sync is durable backup + cross-device access.

### Document Attachment Flow

1. Tap "Attach Document" -> `FilePicker` (PDF/XLS filter)
2. File copied to local storage (`{appDocs}/documents/{projectId}/{entryId}/{filename}`)
3. `documents` row created with `file_path`, `file_type`, `filename`
4. On sync, three-phase push to `entry-documents` bucket
5. Viewable in entry detail

---

## Security & RLS

### Role Model

Three roles: **engineers**, **admins**, **inspectors**. All can view everything on the project. Create/edit/delete scoped to own records only.

### RLS Policies

**`inspector_forms` (fixed)**:
```sql
SELECT: is_builtin = true OR project_id IN (company projects)
INSERT: (is_builtin = true OR project_id IN (company projects))
UPDATE: (is_builtin = true OR project_id IN (company projects)) AND created_by_user_id = auth.uid()
DELETE: project_id IN (company projects) AND created_by_user_id = auth.uid() AND is_builtin = false
```

Builtins are read-only from Supabase's perspective. Nobody can delete builtins via RLS.

**`form_exports`, `entry_exports`, `documents`** (all three identical pattern):
```sql
SELECT: project_id IN (company projects)
INSERT: project_id IN (company projects)
UPDATE: project_id IN (company projects) AND created_by_user_id = auth.uid()
DELETE: project_id IN (company projects) AND created_by_user_id = auth.uid()
```

**Storage bucket policies** (all three buckets):
- SELECT: company_id from path `folder[1]` matches user's company
- INSERT/DELETE: same + ownership enforced via metadata table

### Security Considerations

| Concern | Mitigation |
|---------|------------|
| Builtin form tampering | RLS prevents DELETE of builtins. App-side repository guard blocks modify/delete. |
| File path traversal | Path validation regex on all three file adapters (like photos). |
| EXIF/metadata stripping | Form/entry exports are app-generated PDFs -- no EXIF. Documents stored as-is (business documents). |
| PII in exported PDFs | Company-scoped via RLS. No cross-company leakage. |
| Ownership enforcement | UPDATE/DELETE require `created_by_user_id = auth.uid()`. |
| Orphan files | Extended orphan scanner covers all four buckets. |
| Soft delete cascade | Project deletion soft-deletes all three new tables. Storage files cleaned via cleanup queue. |

---

## Migration & Cleanup

### SQLite Migration (v43)

- `CREATE TABLE form_exports` (15 columns, 3 FKs, 5 indexes)
- `CREATE TABLE entry_exports` (13 columns, 2 FKs, 3 indexes)
- `CREATE TABLE documents` (15 columns, 2 FKs, 4 indexes)
- Add all three tables to change_log triggers
- Add all three to `tablesWithDirectProjectId`

### Supabase Migration

- `ALTER TABLE inspector_forms ALTER COLUMN project_id DROP NOT NULL`
- Drop + recreate inspector_forms RLS policies (builtin-aware)
- `CREATE TABLE form_exports` with ownership-scoped RLS
- `CREATE TABLE entry_exports` with ownership-scoped RLS
- `CREATE TABLE documents` with ownership-scoped RLS
- Create storage buckets: `form-exports`, `entry-exports`, `entry-documents`
- Storage RLS policies for all three buckets
- Add all three tables to project cascade soft-delete trigger
- `lock_created_by` triggers on all three new tables

### Dead Code Removal

| File | What | Why |
|------|------|-----|
| `form_field_entry.dart` | Entire model class | Dead since v22 -- backing table dropped, never referenced |
| `auto_fill_result.dart` | `AutoFillSource` import from `form_field_entry.dart` | Move enum to own file or inline |

### 0582B Refactoring (40+ references)

| Current | Becomes |
|---------|---------|
| `seedBuiltinForms()` single hardcode | Loop over `builtinForms` config list |
| `FormResponse` default `formType: 'mdot_0582b'` | Required parameter, no default |
| `forms_list_screen.dart` hardcoded 0582B | Dynamic `FormGalleryScreen` from registry |
| `app_router.dart` form-fill -> `MdotHubScreen` | Dispatch via `FormScreenRegistry` |
| `entry_forms_section._startForm()` is0582B check | `FormInitialDataFactory` lookup |
| `form_response_repository.validateRequiredFields()` | `FormValidatorRegistry` dispatch |
| `form_pdf_service._fillMdot0582bFields()` | `FormPdfFillerRegistry` dispatch |
| `inspector_form_provider` appendMdot0582b methods | Calculator registry methods |
| `entry_form_card.dart` is0582B quick actions | Screen registry provides action config |
| `hasBuiltinForms()` check | Per-ID existence check in seed loop |

### Soft Delete Service Fix

- Add `inspector_forms` to `_projectChildTables` with `WHERE is_builtin = 0` guard
- Add `form_exports`, `entry_exports`, `documents` to `_projectChildTables`
- Add all three to `_childToParentOrder` in correct FK position

### Sync Registry Updates

Add to `registerSyncAdapters()` in FK dependency order:
- `EntryExportAdapter` after `DailyEntryAdapter` (~position 10)
- `DocumentAdapter` after `DailyEntryAdapter` (~position 11)
- `FormExportAdapter` after `FormResponseAdapter` (position 16)

Rename `isPhotoAdapter` to `isFileAdapter` on `TableAdapter` base class.

---

## Hardcoded 0582B Reference Inventory (from research)

### Production Code (`lib/`)

| File | Lines | Reference Type |
|------|-------|----------------|
| `lib/main.dart` | 562-586 | Seed: `id: 'mdot_0582b'`, name, template path |
| `lib/main_driver.dart` | 82, 229 | Imports + calls `seedBuiltinForms` |
| `lib/core/router/app_router.dart` | 614-617 | form-fill hardwired to `MdotHubScreen` |
| `lib/core/database/database_service.dart` | 737, 756, 768, 781, 790 | Migration defaults `'mdot_0582b'` |
| `lib/core/database/schema_verifier.dart` | 265 | Default value `'mdot_0582b'` |
| `lib/features/forms/data/models/inspector_form.dart` | 217-218 | `is0582B` getter |
| `lib/features/forms/data/models/form_response.dart` | 56, 108, 170, 207, 234, 302, 309 | Default formType |
| `lib/features/forms/data/services/form_pdf_service.dart` | 74-75, 87-94, 103-115, 400-530, 734, 904-1112 | Template path, detection, field mapping |
| `lib/features/forms/data/services/mdot_0582b_calculator.dart` | ENTIRE FILE | Calculator (stays, registered) |
| `lib/features/forms/data/services/one_point_calculator.dart` | ENTIRE FILE | Michigan Cone (stays, registered) |
| `lib/features/forms/presentation/screens/mdot_hub_screen.dart` | ENTIRE FILE | Hub screen (stays, registered) |
| `lib/features/forms/presentation/screens/forms_list_screen.dart` | 39, 60, 162, 181-214, 223, 249 | Hardcoded card/filter/labels |
| `lib/features/forms/presentation/screens/form_viewer_screen.dart` | 135-142, 259 | firstWhere for 0582B |
| `lib/features/forms/presentation/providers/inspector_form_provider.dart` | 354, 383 | appendMdot0582b methods |
| `lib/features/forms/presentation/widgets/hub_header_content.dart` | 19-30 | 0582B header fields |
| `lib/features/forms/presentation/widgets/hub_proctor_content.dart` | ENTIRE FILE | 0582B proctor UI (stays) |
| `lib/features/forms/presentation/widgets/hub_quick_test_content.dart` | ENTIRE FILE | 0582B test UI (stays) |
| `lib/features/forms/data/repositories/form_response_repository.dart` | 359 | validateRequiredFields only 0582B |
| `lib/features/entries/presentation/widgets/entry_form_card.dart` | 26, 75 | is0582B quick actions |
| `lib/features/entries/presentation/widgets/entry_forms_section.dart` | 40-54 | is0582B initial data |
| `lib/shared/testing_keys/toolbox_keys.dart` | 66-126 | Test keys with mdot prefix |
| `lib/shared/services/preferences_service.dart` | 40, 46 | Gauge number for 0582B header |
| `lib/features/forms/data/services/auto_fill_service.dart` | ENTIRE FILE | Header fields shaped for 0582B |

---

## Key File Paths (from research)

### Existing Files to Modify
- `lib/core/database/database_service.dart` -- v43 migration
- `lib/core/database/schema/sync_engine_tables.dart` -- triggers, tablesWithDirectProjectId
- `lib/core/router/app_router.dart` -- form-fill dispatch
- `lib/main.dart` -- seed registry
- `lib/main_driver.dart` -- seed registry
- `lib/features/sync/engine/sync_registry.dart` -- new adapters
- `lib/features/sync/engine/sync_engine.dart` -- isFileAdapter rename, three-phase push generalization
- `lib/features/sync/engine/orphan_scanner.dart` -- multi-bucket support
- `lib/features/sync/engine/storage_cleanup.dart` -- multi-bucket support
- `lib/features/sync/adapters/table_adapter.dart` -- isFileAdapter rename
- `lib/features/sync/adapters/photo_adapter.dart` -- isFileAdapter rename
- `lib/features/sync/adapters/inspector_form_adapter.dart` -- builtin-aware pull
- `lib/features/sync/application/sync_orchestrator.dart` -- bucket groupings
- `lib/features/forms/data/models/form_response.dart` -- remove default formType
- `lib/features/forms/data/repositories/form_response_repository.dart` -- validator registry
- `lib/features/forms/data/services/form_pdf_service.dart` -- filler registry
- `lib/features/forms/presentation/providers/inspector_form_provider.dart` -- calculator registry
- `lib/features/forms/presentation/screens/forms_list_screen.dart` -- replace with gallery
- `lib/features/entries/presentation/widgets/entry_forms_section.dart` -- initial data factory
- `lib/features/entries/presentation/widgets/entry_form_card.dart` -- registry dispatch
- `lib/services/soft_delete_service.dart` -- cascade additions

### New Files to Create
- `lib/features/forms/data/models/builtin_form_config.dart`
- `lib/features/forms/data/registry/form_calculator_registry.dart`
- `lib/features/forms/data/registry/form_validator_registry.dart`
- `lib/features/forms/data/registry/form_initial_data_factory.dart`
- `lib/features/forms/data/registry/form_pdf_filler_registry.dart`
- `lib/features/forms/data/registry/form_screen_registry.dart`
- `lib/features/forms/presentation/screens/form_gallery_screen.dart`
- `lib/features/form_exports/data/models/form_export.dart`
- `lib/features/form_exports/data/datasources/local/form_export_local_datasource.dart`
- `lib/features/form_exports/data/datasources/remote/form_export_remote_datasource.dart`
- `lib/features/form_exports/data/repositories/form_export_repository.dart`
- `lib/features/form_exports/presentation/providers/form_export_provider.dart`
- `lib/features/entry_exports/data/models/entry_export.dart`
- `lib/features/entry_exports/data/datasources/local/entry_export_local_datasource.dart`
- `lib/features/entry_exports/data/datasources/remote/entry_export_remote_datasource.dart`
- `lib/features/entry_exports/data/repositories/entry_export_repository.dart`
- `lib/features/entry_exports/presentation/providers/entry_export_provider.dart`
- `lib/features/documents/data/models/document.dart`
- `lib/features/documents/data/datasources/local/document_local_datasource.dart`
- `lib/features/documents/data/datasources/remote/document_remote_datasource.dart`
- `lib/features/documents/data/repositories/document_repository.dart`
- `lib/features/documents/presentation/providers/document_provider.dart`
- `lib/features/sync/adapters/form_export_adapter.dart`
- `lib/features/sync/adapters/entry_export_adapter.dart`
- `lib/features/sync/adapters/document_adapter.dart`
- `lib/core/database/schema/form_export_tables.dart`
- `lib/core/database/schema/entry_export_tables.dart`
- `lib/core/database/schema/document_tables.dart`
- `supabase/migrations/YYYYMMDD_forms_infrastructure.sql`

### Files to Delete
- `lib/features/forms/data/models/form_field_entry.dart` (dead code since v22)

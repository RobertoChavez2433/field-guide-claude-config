# Sync Verification Bug Report — 2026-03-27

Compiled from 3 test runs (mhaz3, mvs51, 2mthw) + S661 state + opus agent verification.

---

## OPEN — Priority Fixes

### BUG-SV-1: Assignment uncheck doesn't persist soft-delete
- **Severity**: HIGH
- **Source**: BUG-S01-2 (S661 confirmed)
- **Symptom**: Unchecking an inspector assignment in AssignmentsStep updates UI visually but doesn't write soft-delete to SQLite or create change_log entry. Supabase assignment row unchanged.
- **Root cause**: Creation path fixed (v40 triggers), but the unassignment/removal path in `ProjectAssignmentProvider.save()` doesn't persist the soft-delete correctly.
- **Key files**:
  - `lib/features/projects/presentation/widgets/assignments_step.dart`
  - `lib/features/projects/presentation/providers/project_assignment_provider.dart:118-154`
  - `lib/features/projects/presentation/screens/project_setup_screen.dart:1021-1053`

### BUG-SV-2: Contractor card doesn't collapse after "Done" + personnel/equipment don't sync
- **Severity**: HIGH
- **Symptom (UX)**: Tapping "Done" on the contractor editor card within a daily entry does NOT collapse the card back to its compact view. User is left wondering if their changes (personnel counts, equipment toggles) actually saved.
- **Symptom (data)**: Personnel counts and equipment selections save to local SQLite but never sync to Supabase. `entry_personnel_counts` and `entry_equipment` tables have 0 records in Supabase after sync.
- **Root cause (sync)**: `EntryPersonnelCountsLocalDatasource.saveCountsForEntryContractor()` (lines 50-101) wraps the entire transaction in `sync_control pulling='1'`, which suppresses all change_log INSERT triggers. The data lands in SQLite but no change_log entries are created, so the sync engine has nothing to push.
- **Root cause (equipment)**: `EntryEquipment.toMap()` (lines 35-43 of `entry_equipment.dart`) omits `project_id` and `created_by_user_id` columns that exist in the schema. Also uses hard-delete + re-insert pattern creating unnecessary delete churn.
- **Key files**:
  - `lib/features/entries/presentation/widgets/contractor_editor_widget.dart` — "Done" button (line 103)
  - `lib/features/entries/presentation/widgets/entry_contractors_section.dart:194, 234-236` — save chain
  - `lib/features/entries/presentation/controllers/contractor_editing_controller.dart:227-272` — save orchestration
  - `lib/features/contractors/data/datasources/local/entry_personnel_counts_local_datasource.dart:50-101` — sync_control suppression
  - `lib/features/contractors/data/datasources/local/entry_equipment_local_datasource.dart:100-116` — delete+insert pattern
  - `lib/features/contractors/data/models/entry_equipment.dart:35-43` — toMap() missing fields
  - `lib/core/database/schema/sync_engine_tables.dart:202-216` — trigger gate on sync_control

### BUG-SV-3: Entry wizard layout doesn't match edit entry screen
- **Severity**: MEDIUM
- **Symptom**: The entry creation wizard (multi-step flow) has a different layout/appearance than the edit entry screen. Users expect a consistent experience between creating and editing an entry.
- **Key files**:
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart` — edit mode (`_buildEditSections`)
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart` — create mode (`_buildCreateSections`)

### BUG-SV-4: Inspector sees unassigned projects in local cache
- **Severity**: MEDIUM (security — partially fixed)
- **Symptom**: Server-side RLS correctly blocks Supabase queries for unassigned inspectors. But `fetchRemoteProjects()` queries local SQLite with only `company_id` filter — no assignment gate for inspector role. Any project that landed in SQLite from a prior sync (before RLS was tightened) remains visible.
- **Root cause**: `project_provider.dart:649` — `db.query('projects', where: 'company_id = ? AND deleted_at IS NULL')` has no join to `project_assignments` for inspector role.
- **Key files**:
  - `lib/features/projects/presentation/providers/project_provider.dart:649-655` — fetchRemoteProjects SQLite query
  - `lib/features/projects/presentation/providers/project_provider.dart:144-154` — companyProjects getter

---

## OPEN — Low Priority

### BUG-SV-5: inject-photo-direct driver endpoint crashes
- **Severity**: LOW (driver/test infra only)
- **Symptom**: `inject-photo-direct` fails with "could not decode image for EXIF strip" when image format is unrecognized.
- **Root cause**: `test_photo_service.dart:81-83` — `img.decodeImage()` returns null with no fallback. Should skip EXIF strip and use original bytes.
- **Key files**:
  - `lib/core/driver/test_photo_service.dart:78-85`

<!-- RESOLVED 2026-03-30 BUG-SV-6: No form templates on fresh install — seedBuiltinForms is now called via AppInitializer.initialize() from both main.dart and main_driver.dart. Same fix as BUG-S04. -->

---

## COSMETIC / TECH DEBT

| Issue | Notes |
|-------|-------|
| RenderFlex overflows (4.9px, 128px, 19px, 27px) | Contractor cards, entry report, PDF generation screens |
| Orphan cleaner skips every admin sync cycle | "projects adapter has not completed yet" — admin role edge case |
| Contractor cards in project setup need redesign | User requested project setup cards match entry wizard cards |

---

## CONFIRMED FIXED (no action needed)

| ID | Bug | Fix |
|----|-----|-----|
| BUG-S01-1 | Unit dropdown TON->CY | setState removed, initialValue used (commit 38227eb) |
| BUG-1 | Contractor type Sub->Prime | Replaced with SegmentedButton (strongly-typed enum) |
| BUG-S01-2 (create) | Assignment creation not triggering change_log | v40 migration added triggers |
| BUG-S07-1 | Contractor names not editable | AddContractorDialog supports edit mode |
| BUG-S07-2 | Quantity inline edit missing | Fully implemented, was test data issue |
| BUG-5 | Personnel types not in project setup | Added at project_setup_screen.dart:772-785 |
| BUG-S09-1/2/3/4 | Delete flow (4 bugs) | Fixed S661 — RPC, RLS, cascade, orphan cleaner |
| SECURITY-S09-1 | daily_entries RLS missing ownership | Fixed S661 |
| BUG-4 (server) | Inspector pulls unassigned (Supabase) | RLS tightened in 20260326000000 + 20260326100000 |

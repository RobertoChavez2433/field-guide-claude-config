# Sync Verification Bugfixes Spec

**Date**: 2026-03-27
**Bugs**: BUG-SV-1, BUG-SV-2a/b/c, BUG-SV-4, BUG-SV-5
**Source**: `.claude/defects/_defects-sync-verification.md`
**Deferred**: BUG-SV-3 (entry wizard layout), BUG-SV-6 (form seeding) — context saved in `_deferred-sv3-sv6-context.md`

---

## Overview

### Purpose
Fix 6 bugs discovered during sync verification testing (S01-S10). These bugs prevent assignment uncheck from syncing, suppress personnel/equipment sync to Supabase, leave contractor cards stuck in edit mode, expose unassigned projects to inspectors locally, and crash the driver photo endpoint.

### Success Criteria
- [ ] Assignment uncheck persists as soft-delete, syncs to Supabase as tombstone
- [ ] Personnel counts appear in Supabase `entry_personnel_counts` after sync
- [ ] Equipment rows appear in Supabase `entry_equipment` after sync with stable IDs
- [ ] Contractor editor card collapses after tapping "Done"
- [ ] Inspector role sees only assigned projects in project list
- [ ] `inject-photo-direct` handles unknown image formats without crashing
- [ ] All existing unit tests still pass (3141/3141)
- [ ] S10 sync verification passes

---

## Data Model

No new tables or columns. All fixes use existing schema.

### Changes to Data Access Patterns

| Fix | Table | Current Pattern | New Pattern |
|-----|-------|----------------|-------------|
| SV-1 | `project_assignments` | Hard `DELETE` | `UPDATE SET deleted_at, deleted_by, updated_at` |
| SV-2b | `entry_personnel_counts` | All writes under `pulling='1'` suppression | No `sync_control` manipulation. Soft-delete + resurrect/insert. All operations generate change_log. |
| SV-2c | `entry_equipment` | Hard DELETE + INSERT with new UUIDs | Soft-delete old + upsert/resurrect with stable IDs |
| SV-2c | `entry_equipment` | `toMap()` omits `project_id`, `created_by_user_id` | Include all columns |

### Trigger Consequences
- SV-1: Will now fire `AFTER UPDATE` trigger (logs `operation='update'`) instead of `AFTER DELETE` (logged `operation='delete'`). Sync engine sees the row with `deleted_at` set and pushes soft-delete to Supabase.
- SV-2b: Removal of `sync_control` manipulation means all operations (soft-delete, insert, resurrect) fire their respective triggers normally. Every change generates a change_log entry for sync.
- SV-2c: Same pattern as SV-2b — soft-delete + resurrect with stable IDs, all triggers fire normally.

---

## State Management

### SV-2a: ContractorEditingController
- `saveIfEditingContractor()` at line ~270: add `_editingContractorId = null; _editingEquipmentIds = {};` before `notifyListeners()`
- Matches existing pattern in `cancelEditing()` at line 180

### SV-4: ProjectProvider
- Add `UserRole? _currentUserRole` field + setter (alongside existing `setCurrentUserId`)
- `companyProjects` getter: if `_currentUserRole == UserRole.inspector`, filter to `e.isAssigned == true`
- Caller in `main.dart` or wherever `setCurrentUserId` is called also sets role

### No changes to:
- `ProjectAssignmentProvider` — `save()` just calls the updated repository method, same signature but passes `deletedBy` parameter
- `EntryContractorsSection` — save chain unchanged, just the datasources beneath it

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| SV-1: User unchecks then re-checks same assignment before saving | `toggleAssignment()` adds back to in-memory set. `save()` computes diff — user won't appear in `removed` set. No delete fired. |
| SV-1: Uncheck fails mid-save (network down) | Soft-delete writes to local SQLite only. Sync pushes later when online. No data loss. |
| SV-2b: Personnel counts saved while sync is pulling | No `sync_control` manipulation in the datasource. Sync engine's own `pulling='1'` suppresses triggers during pull. User-initiated saves happen outside pull windows — triggers fire normally. No conflict. |
| SV-2c: Equipment save with zero items | Soft-delete all existing, insert nothing. Change_log gets the soft-delete updates. |
| SV-4: Engineer or admin role | Filter only applies to `UserRole.inspector`. Engineers and admins see all company projects unchanged. |
| SV-4: Role changes mid-session | Role field updated on next auth refresh. `companyProjects` getter uses current role value. |
| SV-5: HEIC/RAW image from device | `decodeImage()` returns null, fallback to original bytes with EXIF intact. Acceptable for test endpoint. |

---

## Security Implications

### SV-4: Inspector Project Visibility
- **Current risk**: Inspector can see names/numbers of all company projects in local SQLite cache, even if unassigned. Read-only information disclosure — can't download or interact, but can see metadata.
- **Fix**: Client-side filter in `companyProjects` getter. Defense-in-depth alongside existing server-side RLS.
- **Not a full RLS bypass**: Supabase RLS already blocks data access. This closes the local cache leak only.

### No RLS changes needed
All other fixes (SV-1, SV-2a/b/c, SV-5) operate within existing RLS policies. Soft-delete rows sync through the same `UPDATE` path — no new Supabase permissions required.

### Audit trail improvement
SV-1 now populates `deleted_by` on assignment soft-delete, creating an audit trail that the hard-delete path destroyed.

---

## Migration/Cleanup

### Dead Code Removal
| Method | File | Action |
|--------|------|--------|
| `deleteAllForProject()` | `project_assignment_repository.dart:118-125` | Remove (zero callers) |
| `replaceAllForProject()` | `project_assignment_repository.dart:79-102` | Remove (zero callers) |

### Stale Comment
`integrity_checker.dart:417` — comment references `project_assignments` as a table without soft-delete. Update to reflect current state (empty set).

### No Schema Migrations
All tables already have the required columns (`deleted_at`, `deleted_by`, `project_id`, `created_by_user_id`). No new migrations needed.

---

## Testing Strategy

### Unit Tests
| Component | Test Focus | Priority |
|-----------|-----------|----------|
| `ProjectAssignmentRepository` soft-delete | Verify UPDATE instead of DELETE, `deleted_at`/`deleted_by` populated | HIGH |
| `EntryPersonnelCountsLocalDatasource` | Verify change_log entries created for inserts, no `sync_control` manipulation | HIGH |
| `EntryEquipmentLocalDatasource` | Verify stable IDs on re-save, soft-delete + resurrect, `toMap()` includes all columns | HIGH |
| `ProjectProvider.companyProjects` | Verify inspector sees only assigned, engineer/admin sees all | HIGH |

### Verification
- Re-run S10 (assignment uncheck + sync) — should PASS
- Re-run S02 (entry contractors + personnel/equipment sync) — verify Supabase rows appear
- Manual: tap "Done" on contractor card, confirm collapse

### Existing Tests
- 3141/3141 must continue passing. No behavioral changes outside the bug paths.

---

## Fix Summary

| Bug | File(s) | Fix |
|-----|---------|-----|
| SV-1 | `project_assignment_repository.dart`, `project_assignment_provider.dart` | Convert `deleteByProjectAndUser()` to soft-delete (`UPDATE SET deleted_at, deleted_by, updated_at`). Pass `deletedBy` from provider. Remove 2 dead code methods. |
| SV-2a | `contractor_editing_controller.dart` | Add `_editingContractorId = null; _editingEquipmentIds = {};` before `notifyListeners()` in `saveIfEditingContractor()` |
| SV-2b | `entry_personnel_counts_local_datasource.dart` | Remove all `sync_control` manipulation. Restructure as soft-delete old rows + insert/resurrect new rows. All operations fire triggers normally. |
| SV-2c | `entry_equipment_local_datasource.dart`, `entry_equipment.dart` | Replace hard DELETE+INSERT with soft-delete + resurrect using stable IDs. Add `project_id`, `created_by_user_id` to `toMap()`. |
| SV-4 | `project_provider.dart`, `main.dart` | Add `UserRole? _currentUserRole` + setter. Filter `companyProjects` to `isAssigned == true` for inspectors. |
| SV-5 | `test_photo_service.dart` | Replace `throw StateError` with fallback to original bytes when `decodeImage()` returns null. |

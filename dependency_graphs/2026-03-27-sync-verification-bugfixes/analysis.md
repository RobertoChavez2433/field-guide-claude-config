# Sync Verification Bugfixes — Dependency Graph

## Direct Changes

### SV-1: Assignment soft-delete
| File | Symbol | Lines | Change |
|------|--------|-------|--------|
| `lib/features/projects/data/repositories/project_assignment_repository.dart` | `deleteByProjectAndUser()` | 107-114 | Convert hard DELETE to soft-delete UPDATE |
| `lib/features/projects/data/repositories/project_assignment_repository.dart` | `deleteAllForProject()` | 118-125 | REMOVE (dead code, zero callers) |
| `lib/features/projects/data/repositories/project_assignment_repository.dart` | `replaceAllForProject()` | 79-102 | REMOVE (dead code, zero callers) |
| `lib/features/projects/presentation/providers/project_assignment_provider.dart` | `save()` | 118-154 | Pass `deletedBy` to soft-delete method |

### SV-2a: Contractor card collapse
| File | Symbol | Lines | Change |
|------|--------|-------|--------|
| `lib/features/entries/presentation/controllers/contractor_editing_controller.dart` | `saveIfEditingContractor()` | 227-272 | Add `_editingContractorId = null; _editingEquipmentIds = {};` before `notifyListeners()` |

### SV-2b: Personnel counts sync
| File | Symbol | Lines | Change |
|------|--------|-------|--------|
| `lib/features/contractors/data/datasources/local/entry_personnel_counts_local_datasource.dart` | `saveCountsForEntryContractor()` | 42-105 | Remove ALL sync_control manipulation. Keep soft-delete + resurrect logic, let triggers fire normally. |

### SV-2c: Equipment save pattern
| File | Symbol | Lines | Change |
|------|--------|-------|--------|
| `lib/features/contractors/data/datasources/local/entry_equipment_local_datasource.dart` | `saveForEntry()` | 100-116 | Replace hard DELETE+INSERT with soft-delete + resurrect using stable IDs |
| `lib/features/contractors/data/models/entry_equipment.dart` | `EntryEquipment` class | 3-60 | Add `projectId`, `createdByUserId`, `deletedAt`, `deletedBy` fields |
| `lib/features/contractors/data/models/entry_equipment.dart` | `toMap()` | 35-44 | Include `project_id`, `created_by_user_id`, `deleted_at`, `deleted_by` |
| `lib/features/contractors/data/models/entry_equipment.dart` | `fromMap()` | 46-59 | Parse new fields |
| `lib/features/contractors/data/models/entry_equipment.dart` | `EntryEquipment()` constructor | 11-18 | Add new optional params |

### SV-4: Inspector project filter
| File | Symbol | Lines | Change |
|------|--------|-------|--------|
| `lib/features/projects/presentation/providers/project_provider.dart` | `companyProjects` getter | 144-154 | Add inspector role filter |
| `lib/features/projects/presentation/providers/project_provider.dart` | new `setCurrentUserRole()` | after 50 | New method + `_currentUserRole` field |
| `lib/features/projects/presentation/screens/project_list_screen.dart` | `_loadInitialData()` | ~48-52 | Wire role alongside `loadAssignments` call |

### SV-5: Driver photo fallback
| File | Symbol | Lines | Change |
|------|--------|-------|--------|
| `lib/core/driver/test_photo_service.dart` | `injectPhotoDirect()` | 66-112 | Replace `throw StateError` with fallback to original bytes |

### Cleanup
| File | Symbol | Lines | Change |
|------|--------|-------|--------|
| `lib/features/sync/engine/integrity_checker.dart` | comment | ~417 | Update stale comment about `_tablesWithoutSoftDelete` |

## Dependent Files (callers 2+ levels)

Blast radius is **zero** for all three datasource methods — they are only called from their immediate controller/provider. No transitive callers.

| Caller | Calls | Impact |
|--------|-------|--------|
| `project_assignment_provider.dart:save()` | `deleteByProjectAndUser()` | Signature change (add `deletedBy` param) |
| `contractor_editing_controller.dart:saveIfEditingContractor()` | `saveCountsForEntryContractor()`, `saveForEntry()` | No signature change |
| `project_list_screen.dart:_loadInitialData()` | `loadAssignments()` | Add `setCurrentUserRole()` call |

## Key Wiring Points

### Where `setCurrentUserId` is called
- **NEVER called** — the method exists but has zero callers. `_currentUserId` is only used in `_trackRecentProject` and as a dead reference in `deleteProject`.
- For SV-4, `setCurrentUserRole` should be wired at `project_list_screen.dart:48-52` alongside the `loadAssignments` call, which already has access to `authProvider`.

### How role is accessed
- `AuthProvider.isInspector` → `_userProfile?.role == UserRole.inspector` (line 191)
- `UserRole` enum at `lib/features/auth/data/models/user_role.dart:5` — values: `admin`, `engineer`, `inspector`
- `authProvider.userProfile?.role` gives the `UserRole` enum directly

### entry_equipment schema (from entry_tables.dart:58-71)
```sql
CREATE TABLE entry_equipment (
  id TEXT PRIMARY KEY,
  entry_id TEXT NOT NULL,
  equipment_id TEXT NOT NULL,
  was_used INTEGER NOT NULL DEFAULT 1,
  project_id TEXT,              -- NULLABLE, missing from toMap()
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  created_by_user_id TEXT,      -- NULLABLE, missing from toMap()
  deleted_at TEXT,              -- NULLABLE, missing from toMap()
  deleted_by TEXT,              -- NULLABLE, missing from toMap()
  FOREIGN KEY (entry_id) REFERENCES daily_entries(id) ON DELETE CASCADE,
  FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE
)
```

### Personnel counts ID pattern
Uses deterministic IDs: `'epc-$entryId-$contractorId-${entry.key}'` — already stable, good for resurrect pattern.

### Equipment ID pattern
Currently: `id = id ?? const Uuid().v4()` — generates NEW UUID every construction. For stable IDs, use deterministic pattern like `'ee-$entryId-$equipmentId'`.

### Existing EXIF fallback pattern (sync_engine.dart:1144-1170)
```dart
final image = img.decodeImage(bytes);
if (image == null) return bytes; // <-- graceful fallback
```

## Test Files
| Test | Coverage |
|------|----------|
| `test/features/projects/data/repositories/project_assignment_repository_test.dart` | If exists — add soft-delete test |
| `test/features/contractors/` | Personnel counts + equipment datasource tests |
| `test/features/projects/presentation/providers/project_provider_test.dart` | If exists — add inspector filter test |

## Data Flow

```
SV-1: AssignmentsStep checkbox → toggleAssignment() (in-memory)
      → save() → deleteByProjectAndUser() [CHANGE: soft-delete]
      → AFTER UPDATE trigger → change_log(operation='update')
      → sync engine pushes UPDATE with deleted_at to Supabase

SV-2a: Done button → _saveContractor() → saveIfEditingContractor()
       → saves data → [ADD: _editingContractorId = null]
       → notifyListeners() → card rebuilds in view mode

SV-2b: saveIfEditingContractor() → saveCountsForEntryContractor()
       → [REMOVE: sync_control manipulation]
       → soft-delete old → resurrect/insert new
       → triggers fire → change_log entries created → sync pushes

SV-2c: saveIfEditingContractor() → saveForEntry()
       → [CHANGE: soft-delete + resurrect with stable IDs]
       → triggers fire → change_log entries created → sync pushes

SV-4: project_list_screen → loadAssignments() + setCurrentUserRole()
      → companyProjects getter checks role
      → inspector sees only isAssigned==true

SV-5: inject-photo-direct → decodeImage() returns null
      → [CHANGE: use original bytes instead of throw]
```

## Blast Radius Summary
- **Direct**: 9 files modified
- **Dependent**: 1 file (project_list_screen wiring)
- **Tests**: 3-4 test files (new or modified)
- **Cleanup**: 2 dead methods + 1 stale comment

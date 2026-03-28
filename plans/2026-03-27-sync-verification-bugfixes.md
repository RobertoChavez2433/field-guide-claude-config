# Sync Verification Bugfixes Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Fix 6 bugs (SV-1, SV-2a/b/c, SV-4, SV-5) discovered during sync verification testing that prevent assignment uncheck sync, suppress personnel/equipment sync, leave contractor cards stuck, expose unassigned projects, and crash the driver photo endpoint.
**Spec:** `.claude/specs/2026-03-27-sync-verification-bugfixes-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-27-sync-verification-bugfixes/`

**Architecture:** All fixes are isolated to their respective feature boundaries. Data layer changes (model, datasource, repository) propagate upward to providers and UI. No new tables or migrations needed — only correcting how existing columns are populated and how delete operations work.
**Tech Stack:** Flutter/Dart, SQLite (sqflite), ChangeNotifier providers
**Blast Radius:** 10 direct files, 2 dependent (provider + screen wiring), 0 existing tests broken, 3 cleanup items

---

## Phase 1: Data Layer — Model & Datasource Fixes

### Sub-phase 1.1: EntryEquipment Model Extension (SV-2c)

**Files:**
- Modify: `lib/features/contractors/data/models/entry_equipment.dart:3-60`

**Agent**: `backend-data-layer-agent`

#### Step 1.1.1: Add missing fields to EntryEquipment class

Add `projectId`, `createdByUserId`, `deletedAt`, `deletedBy` fields to the model, update constructor, `toMap()`, `fromMap()`, and `copyWith()`.

```dart
// lib/features/contractors/data/models/entry_equipment.dart — FULL REPLACEMENT
class EntryEquipment {
  final String id;
  final String entryId;
  final String equipmentId;
  final bool wasUsed;
  final String? projectId;
  final String? createdByUserId;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? deletedAt;
  final String? deletedBy;

  EntryEquipment({
    String? id,
    required this.entryId,
    required this.equipmentId,
    this.wasUsed = true,
    this.projectId,
    this.createdByUserId,
    DateTime? createdAt,
    DateTime? updatedAt,
    this.deletedAt,
    this.deletedBy,
  }) : id = id ?? const Uuid().v4(),
       createdAt = createdAt ?? DateTime.now(),
       updatedAt = updatedAt ?? DateTime.now();

  EntryEquipment copyWith({
    bool? wasUsed,
    String? projectId,
    String? createdByUserId,
    DateTime? deletedAt,
    String? deletedBy,
  }) {
    return EntryEquipment(
      id: id,
      entryId: entryId,
      equipmentId: equipmentId,
      wasUsed: wasUsed ?? this.wasUsed,
      projectId: projectId ?? this.projectId,
      createdByUserId: createdByUserId ?? this.createdByUserId,
      createdAt: createdAt,
      updatedAt: DateTime.now(),
      deletedAt: deletedAt,  // NOTE: intentionally not ?? — allows clearing via explicit null
      deletedBy: deletedBy,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'entry_id': entryId,
      'equipment_id': equipmentId,
      'was_used': wasUsed ? 1 : 0,
      'project_id': projectId,              // FROM SPEC: missing from toMap(), required for sync
      'created_by_user_id': createdByUserId, // FROM SPEC: missing from toMap(), required for sync
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      'deleted_at': deletedAt?.toIso8601String(),
      'deleted_by': deletedBy,
    };
  }

  factory EntryEquipment.fromMap(Map<String, dynamic> map) {
    return EntryEquipment(
      id: map['id'] as String,
      entryId: map['entry_id'] as String,
      equipmentId: map['equipment_id'] as String,
      wasUsed: map['was_used'] == 1,
      projectId: map['project_id'] as String?,
      createdByUserId: map['created_by_user_id'] as String?,
      createdAt: map['created_at'] != null
          ? DateTime.parse(map['created_at'] as String)
          : DateTime.now(),
      updatedAt: map['updated_at'] != null
          ? DateTime.parse(map['updated_at'] as String)
          : DateTime.now(),
      deletedAt: map['deleted_at'] != null
          ? DateTime.parse(map['deleted_at'] as String)
          : null,
      deletedBy: map['deleted_by'] as String?,
    );
  }
}
```

NOTE: The `copyWith` for `deletedAt` intentionally does NOT use `?? this.deletedAt` so callers can pass explicit null to resurrect a row.

#### Step 1.1.2: Verify model compiles

Run: `pwsh -Command "flutter analyze lib/features/contractors/data/models/entry_equipment.dart"`
Expected: No errors (warnings acceptable)

---

### Sub-phase 1.2: Personnel Counts Datasource Fix (SV-2b)

**Files:**
- Modify: `lib/features/contractors/data/datasources/local/entry_personnel_counts_local_datasource.dart:42-105`

**Agent**: `backend-data-layer-agent`

#### Step 1.2.1: Remove sync_control manipulation from saveCountsForEntryContractor

The soft-delete + resurrect logic is already correct. The ONLY change is removing the `sync_control` wrapper that suppresses change_log triggers. Without this wrapper, all UPDATEs and INSERTs fire triggers normally, allowing sync to pick them up.

Replace lines 42-105 with:

```dart
Future<void> saveCountsForEntryContractor(
    String entryId,
    String contractorId,
    Map<String, int> counts,
  ) async {
    final database = await db.database;

    // WHY: No sync_control suppression — all operations must fire change_log
    // triggers so personnel counts sync to Supabase (BUG-SV-2b).
    try {
      await database.transaction((txn) async {
        final now = DateTime.now().toUtc().toIso8601String();

        // Soft-delete existing counts for this entry/contractor
        await txn.update(
          _countsTable,
          {'deleted_at': now},
          where: 'entry_id = ? AND contractor_id = ? AND deleted_at IS NULL',
          whereArgs: [entryId, contractorId],
        );

        // Insert new counts (only if > 0), resurrecting soft-deleted rows
        for (final entry in counts.entries) {
          if (entry.value > 0) {
            final id = 'epc-$entryId-$contractorId-${entry.key}';
            // Check for an existing (possibly soft-deleted) row with this ID
            final existing = await txn.query(
              _countsTable,
              where: 'id = ?',
              whereArgs: [id],
              limit: 1,
            );
            if (existing.isNotEmpty) {
              // Resurrect and update count
              await txn.update(
                _countsTable,
                {'deleted_at': null, 'count': entry.value},
                where: 'id = ?',
                whereArgs: [id],
              );
            } else {
              await txn.insert(_countsTable, {
                'id': id,
                'entry_id': entryId,
                'contractor_id': contractorId,
                'type_id': entry.key,
                'count': entry.value,
              });
            }
          }
        }
      });
    } catch (e) {
      throw Exception('Failed to save personnel counts: $e');
    }
  }
```

#### Step 1.2.2: Delete dead code method saveAllCountsForEntry

**REVIEW FIX (CRITICAL)**: `saveAllCountsForEntry` (lines ~113-178) has the identical `sync_control` suppression bug. It has **zero callers** — delete the entire method rather than fixing it. Verify zero callers first with a codebase search for `saveAllCountsForEntry`.

#### Step 1.2.3: Verify datasource compiles

Run: `pwsh -Command "flutter analyze lib/features/contractors/data/datasources/local/entry_personnel_counts_local_datasource.dart"`
Expected: No errors

---

### Sub-phase 1.3: Equipment Datasource — Soft-Delete + Resurrect (SV-2c)

**Files:**
- Modify: `lib/features/contractors/data/datasources/local/entry_equipment_local_datasource.dart:100-116`

**Agent**: `backend-data-layer-agent`

#### Step 1.3.1: Replace hard DELETE+INSERT with soft-delete + resurrect

Replace the `saveForEntry` method (lines 100-116) with:

```dart
Future<void> saveForEntry(String entryId, List<EntryEquipment> equipment) async {
    final database = await db.database;

    await database.transaction((txn) async {
      final now = DateTime.now().toUtc().toIso8601String();

      // WHY: Soft-delete instead of hard DELETE so sync engine can propagate
      // deletions as tombstones to Supabase (BUG-SV-2c).
      await txn.update(
        tableName,
        {'deleted_at': now, 'updated_at': now},
        where: 'entry_id = ? AND deleted_at IS NULL',
        whereArgs: [entryId],
      );

      // Resurrect or insert each equipment row with stable IDs
      for (final e in equipment) {
        final existing = await txn.query(
          tableName,
          where: 'id = ?',
          whereArgs: [e.id],
          limit: 1,
        );
        if (existing.isNotEmpty) {
          // Resurrect: clear deleted_at, update was_used and timestamp
          await txn.update(
            tableName,
            {
              'deleted_at': null,
              'deleted_by': null,
              'was_used': e.wasUsed ? 1 : 0,
              'updated_at': now,
              'project_id': e.projectId,
              'created_by_user_id': e.createdByUserId,
            },
            where: 'id = ?',
            whereArgs: [e.id],
          );
        } else {
          await txn.insert(tableName, e.toMap());
        }
      }
    });
  }
```

NOTE: Check whether the datasource has its own static `toMap(EntryEquipment e)` method. If so, either update it to include the new fields or switch to calling `e.toMap()` (the model's instance method). The insert call above uses `e.toMap()` — the model's method which now includes all columns.

#### Step 1.3.2: Add deleted_at filter to getUsedEquipmentIds

**REVIEW FIX (MEDIUM — Security)**: `getUsedEquipmentIds()` (lines ~36-45) queries with only `was_used = 1` filter, missing `deleted_at IS NULL`. After switching to soft-delete, this would return ghost equipment IDs from soft-deleted rows.

Add `AND deleted_at IS NULL` to the WHERE clause in `getUsedEquipmentIds`.

#### Step 1.3.3: Update datasource's static toMap if it exists

If `entry_equipment_local_datasource.dart` has a static `toMap(EntryEquipment e)` method, it must also be updated to include `project_id`, `created_by_user_id`, `deleted_at`, `deleted_by`. Alternatively, remove it and use the model's `toMap()` everywhere. The agent should check and reconcile.

#### Step 1.3.4: Verify datasource compiles

Run: `pwsh -Command "flutter analyze lib/features/contractors/data/datasources/local/entry_equipment_local_datasource.dart"`
Expected: No errors

---

## Phase 2: Repository & Controller Fixes

### Sub-phase 2.1: Assignment Soft-Delete (SV-1)

**Files:**
- Modify: `lib/features/projects/data/repositories/project_assignment_repository.dart:79-125`
- Modify: `lib/features/projects/presentation/providers/project_assignment_provider.dart:118-154`

**Agent**: `backend-data-layer-agent`

#### Step 2.1.1: Convert deleteByProjectAndUser to soft-delete

Replace lines 107-114 in `project_assignment_repository.dart`:

```dart
// FROM SPEC (BUG-SV-1): Soft-delete so sync engine propagates tombstone to Supabase.
  Future<void> deleteByProjectAndUser(String projectId, String userId, {required String deletedBy}) async {
    final db = await _db;
    final now = DateTime.now().toUtc().toIso8601String();
    await db.update(
      'project_assignments',
      {'deleted_at': now, 'deleted_by': deletedBy, 'updated_at': now},
      where: 'project_id = ? AND user_id = ? AND deleted_at IS NULL',
      whereArgs: [projectId, userId],
    );
  }
```

#### Step 2.1.2: Remove dead code methods

Delete `deleteAllForProject()` (lines ~118-125) and `replaceAllForProject()` (lines ~79-102). Both have zero callers.

NOTE: Verify zero callers before deleting. Search for `deleteAllForProject` and `replaceAllForProject` across the codebase.

#### Step 2.1.3: Pass deletedBy in ProjectAssignmentProvider.save()

In `project_assignment_provider.dart`, update the delete loop in `save()` (around line 131):

```dart
// Delete removed assignments
    for (final userId in removed) {
      // FROM SPEC (BUG-SV-1): Pass assignedBy as deletedBy for audit trail
      await _repository.deleteByProjectAndUser(projectId, userId, deletedBy: assignedBy);
    }
```

#### Step 2.1.4: Verify both files compile

Run: `pwsh -Command "flutter analyze lib/features/projects/data/repositories/project_assignment_repository.dart lib/features/projects/presentation/providers/project_assignment_provider.dart"`
Expected: No errors

---

### Sub-phase 2.2: Contractor Card Collapse Fix (SV-2a)

**Files:**
- Modify: `lib/features/entries/presentation/controllers/contractor_editing_controller.dart:227-272`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.2.1: Reset editing state before notifyListeners in saveIfEditingContractor

Add two lines before `notifyListeners()` at the end of `saveIfEditingContractor()`, matching the `cancelEditing()` pattern:

Find the block near the end of `saveIfEditingContractor()`:
```dart
    // Update local state
    _entryEquipment = updatedEquipment;

    notifyListeners();
```

Replace with:
```dart
    // Update local state
    _entryEquipment = updatedEquipment;

    // WHY: Reset editing state so the contractor card collapses after save,
    // matching cancelEditing() behavior (BUG-SV-2a).
    _editingContractorId = null;
    _editingEquipmentIds = {};

    notifyListeners();
```

#### Step 2.2.2: Verify controller compiles

Run: `pwsh -Command "flutter analyze lib/features/entries/presentation/controllers/contractor_editing_controller.dart"`
Expected: No errors

---

### Sub-phase 2.3: Stable Equipment IDs in Controller (SV-2c — wiring)

**Files:**
- Modify: `lib/features/entries/presentation/controllers/contractor_editing_controller.dart:245-260`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.3.1: Use deterministic IDs and pass projectId/createdByUserId

The controller constructs `EntryEquipment` objects at line ~252. Update to use stable deterministic IDs and pass the new required fields.

First, the controller needs access to `projectId` and `createdByUserId`. Check if these are already available on the controller class. If not, they must be passed into `saveIfEditingContractor()`.

Update the equipment construction loop:

```dart
    // Equipment belonging to the edited contractor
    for (final eq in _allProjectEquipment) {
      if (eq.contractorId == contractorId) {
        updatedEquipment.add(EntryEquipment(
          // WHY: Deterministic ID ensures soft-delete + resurrect finds the same row (BUG-SV-2c)
          id: 'ee-$entryId-${eq.id}',
          entryId: entryId,
          equipmentId: eq.id,
          wasUsed: _editingEquipmentIds.contains(eq.id),
          projectId: projectId,
          createdByUserId: createdByUserId,
        ));
      }
    }
```

**REVIEW FIX (MEDIUM)**: The "preserved equipment from other contractors" loop (lines ~258-263) copies existing `EntryEquipment` objects with their original random UUIDs. These must ALSO use deterministic IDs so soft-delete + resurrect works across saves. Update the preservation loop to reconstruct with deterministic IDs:

```dart
    // Preserve equipment from other contractors — use deterministic IDs
    for (final ee in _entryEquipment) {
      final equipment = _equipmentById[ee.equipmentId];
      if (equipment != null && equipment.contractorId != contractorId) {
        updatedEquipment.add(EntryEquipment(
          id: 'ee-$entryId-${ee.equipmentId}',
          entryId: entryId,
          equipmentId: ee.equipmentId,
          wasUsed: ee.wasUsed,
          projectId: projectId,
          createdByUserId: createdByUserId,
        ));
      }
    }
```

NOTE: The agent must determine how `projectId` and `createdByUserId` reach this method. Options:
1. They may already be fields on the controller (check the class).
2. Add them as parameters to `saveIfEditingContractor(String entryId, {required String projectId, required String createdByUserId})` and update all call sites.
3. If the controller already holds a reference to the entry or project, extract from there.

The agent should inspect the full controller class to decide the cleanest approach.

#### Step 2.3.2: Verify controller and call sites compile

Run: `pwsh -Command "flutter analyze lib/features/entries/"`
Expected: No errors

---

## Phase 3: Provider & UI Wiring

### Sub-phase 3.1: Inspector Project Filter (SV-4)

**Files:**
- Modify: `lib/features/projects/presentation/providers/project_provider.dart:48-50,144-154`
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart:48-52`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 3.1.1: Add UserRole field and setter to ProjectProvider

After the existing `_currentUserId` field (around line 23) and `setCurrentUserId` method (lines 48-50), add:

```dart
UserRole? _currentUserRole;

void setCurrentUserRole(UserRole? role) {
    _currentUserRole = role;
  }
```

Add the import at the top of the file:
```dart
import 'package:construction_inspector/features/auth/data/models/user_role.dart';
```

#### Step 3.1.2: Filter companyProjects for inspector role

Replace the `companyProjects` getter (lines 144-154):

```dart
List<MergedProjectEntry> get companyProjects {
    var active = _mergedProjects.where((e) => !e.isArchived).toList();

    // FROM SPEC (BUG-SV-4): Inspectors should only see projects they are assigned to.
    // Admins and engineers see all company projects.
    if (_currentUserRole == UserRole.inspector) {
      active = active.where((e) => e.isAssigned == true).toList();
    }

    switch (_companyFilter) {
      case CompanyFilter.all:
        return active;
      case CompanyFilter.onDevice:
        return active.where((e) => e.isLocal).toList();
      case CompanyFilter.notDownloaded:
        return active.where((e) => e.isRemoteOnly).toList();
    }
  }
```

NOTE: The agent must verify that `MergedProjectEntry` has an `isAssigned` field. If it doesn't, check how assignment status is tracked and use the correct field/method.

#### Step 3.1.3: Wire setCurrentUserRole in project_list_screen.dart

At `project_list_screen.dart` lines 48-52, add the role setter call:

```dart
final userId = authProvider.userId;
if (userId != null) {
  // FROM SPEC (BUG-SV-4): Set role so companyProjects filters for inspectors
  context.read<ProjectProvider>().setCurrentUserRole(authProvider.userProfile?.role);
  context.read<ProjectProvider>().loadAssignments(
    userId,
    context.read<DatabaseService>(),
  );
}
```

Add the import if not already present:
```dart
import 'package:construction_inspector/features/auth/data/models/user_role.dart';
```

NOTE: `authProvider.userProfile?.role` returns a `UserRole?` — verify this by checking the `UserProfile` model class. The `AuthProvider` already has an `isInspector` getter at line 191, confirming role is available on the profile.

#### Step 3.1.5: Fix companyProjectsCount badge leak

**REVIEW FIX (MEDIUM — Security)**: `companyProjectsCount` at line ~163 independently counts `_mergedProjects.where((e) => !e.isArchived).length` without the inspector filter. An inspector would see "Company (15)" in the tab badge but only 3 projects listed, leaking the total company project count.

Change:
```dart
int get companyProjectsCount =>
    _mergedProjects.where((e) => !e.isArchived).length;
```
To:
```dart
// REVIEW FIX: Use filtered getter so inspector badge matches visible projects
int get companyProjectsCount => companyProjects.length;
```

#### Step 3.1.4: Verify provider and screen compile

Run: `pwsh -Command "flutter analyze lib/features/projects/presentation/"`
Expected: No errors

---

### Sub-phase 3.2: Driver Photo Fallback (SV-5)

**Files:**
- Modify: `lib/core/driver/test_photo_service.dart:66-112`

**Agent**: `backend-data-layer-agent`

#### Step 3.2.1: Replace throw with fallback when decodeImage returns null

In `injectPhotoDirect()`, replace the decode + throw block (around lines 78-82):

Find:
```dart
    final image = img.decodeImage(bytes);
    if (image == null) {
      throw StateError('injectPhotoDirect: could not decode image for EXIF strip: ${file.path}');
    }
    final cleanBytes = img.encodeJpg(image, quality: 85);
```

Replace with:
```dart
    // WHY: Unknown formats (e.g., HEIC) shouldn't crash the endpoint.
    // Fallback to original bytes matches _stripExifGps pattern (BUG-SV-5).
    final image = img.decodeImage(bytes);
    final Uint8List cleanBytes;
    if (image == null) {
      Logger.photo('injectPhotoDirect: could not decode image for EXIF strip, using original bytes: ${file.path}');
      cleanBytes = bytes;
    } else {
      cleanBytes = Uint8List.fromList(img.encodeJpg(image, quality: 85));
    }
```

NOTE: Verify that `bytes` from `file.readAsBytes()` is already `Uint8List`. If the existing code uses `cleanBytes` as `List<int>`, adjust the type accordingly. Also ensure `Logger` and `Uint8List` imports are present.

#### Step 3.2.2: Verify driver compiles

Run: `pwsh -Command "flutter analyze lib/core/driver/test_photo_service.dart"`
Expected: No errors

---

## Phase 4: Cleanup & Verification

### Sub-phase 4.1: Stale Comment Update

**Files:**
- Modify: `lib/features/sync/engine/integrity_checker.dart` line ~417

**Agent**: `general-purpose`

#### Step 4.1.1: Update stale comment at integrity_checker.dart:417

**REVIEW FIX (CRITICAL)**: The comment at line 417 says `"Hard-delete for tables without deleted_at (e.g., project_assignments)"`. The `_tablesWithoutSoftDelete` set at line 63 is already empty `<String>{}` — no table uses this branch. Remove the `(e.g., project_assignments)` example from the comment since `project_assignments` has had soft-delete support since the v41 migration. The comment should just describe the empty-set branch generically.

Also remove the doc comment on `deleteAllForProject` (around line 117) that says `"Prefer [replaceAllForProject]"` — both methods are being deleted in Step 2.1.2.

#### Step 4.1.2: Run full test suite

Run: `pwsh -Command "flutter test"`
Expected: 3141/3141 PASS — no regressions

#### Step 4.1.3: Run static analysis

Run: `pwsh -Command "flutter analyze"`
Expected: No new errors introduced

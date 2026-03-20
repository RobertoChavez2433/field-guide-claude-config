# Dependency Graph: Baseline Bug Fix

## Direct Changes (13 bugs across 20+ files)

### Bug 1: Sync Pull Enrollment (CRITICAL)
| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/features/sync/engine/sync_engine.dart` | `SyncEngine._pull()` | 1107-1182 | MODIFY — add engine-internal enrollment after project_assignments adapter |
| `lib/features/sync/engine/sync_engine.dart` | `SyncEngine._loadSyncedProjectIds()` | 1386-1441 | MODIFY — remove `count > 0` guard on reload |
| `lib/main.dart` | `_runApp()` | 332-390 | KEEP — existing onPullComplete enrollment stays as fallback |

### Bug 2: Todo Priority (CRITICAL)
| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/features/todos/data/models/todo_item.dart` | `TodoItem.toMap()` | 93-107, line 102 | MODIFY — `priority.name` → `priority.index` |
| `lib/features/sync/adapters/type_converters.dart` | NEW `TodoPriorityConverter` | EOF | CREATE — safety net converter |
| `lib/features/sync/adapters/todo_item_adapter.dart` | `TodoItemAdapter.converters` | 17-19 | MODIFY — add `'priority': TodoPriorityConverter()` |
| `lib/core/database/database_service.dart` | `DatabaseService._onUpgrade()` | 1682 (after v38) | MODIFY — add v39 migration for error-state reset |

### Bug 3: LateInitializationError (HIGH)
| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/features/entries/presentation/screens/home_screen.dart` | `_HomeScreenState.initState()` | 73-121 | MODIFY — remove `addPostFrameCallback` block (lines 112-119) |
| `lib/features/entries/presentation/screens/home_screen.dart` | `_HomeScreenState.didChangeDependencies()` | 172-176 | MODIFY — add controller init with `_controllersInitialized` flag |

### Bug 4: Calendar RenderFlex Overflow (HIGH)
| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/features/entries/presentation/screens/home_screen.dart` | `_HomeScreenState.build()` | 349-407, line 389 | MODIFY — wrap `_buildCalendarSection` Consumer in `Flexible` |

### Bug 5: Photo Direct-Inject (HIGH)
| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/core/driver/driver_server.dart` | `DriverServer._handleRequest()` | 77-126 | MODIFY — add route for `/driver/inject-photo-direct` |
| `lib/core/driver/driver_server.dart` | NEW `_handleInjectPhotoDirect()` | after 537 | CREATE — new endpoint handler |
| `lib/core/driver/test_photo_service.dart` | NEW `injectPhotoDirect()` | after line 57 | CREATE — method wrapping PhotoRepository |
| `lib/main_driver.dart` | `_runApp()` | ~102 | MODIFY — pass PhotoRepository to TestPhotoService |

### Bug 6: Contractor Dropdown (HIGH)
| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/features/projects/presentation/widgets/add_contractor_dialog.dart` | `_AddContractorDialogState.build()` | 38-92, line 55 | MODIFY — `initialValue:` → `value:` |

### Bug 7: Display Name (MEDIUM)
| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `supabase/migrations/20260320000000_fix_handle_new_user.sql` | N/A | NEW | CREATE — trigger fix + backfill |
| `lib/features/auth/presentation/screens/register_screen.dart` | `_RegisterScreenState.build()` | 67+ (line ~82-91) | MODIFY — add name validator |
| `lib/features/auth/presentation/screens/profile_setup_screen.dart` | `_ProfileSetupScreenState._skip()` | 79-105 | MODIFY — remove skip option for name (require name) |
| `lib/core/router/app_router.dart` | `AppRouter._buildRouter()` | 125+ | MODIFY — add profile-completion redirect for NULL display_name |

### Bug 8: Ghost Project (MEDIUM)
| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/features/projects/presentation/screens/project_setup_screen.dart` | `_ProjectSetupScreenState._saveProject()` | 958-970 | MODIFY — add `_discardDraft()` before early return |

### Bug 9: Integrity Checker (MEDIUM)
| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/features/sync/engine/integrity_checker.dart` | `IntegrityChecker._checkTable()` | 151-236 | MODIFY — conditional `deleted_at` filter |
| `supabase/migrations/20260320000001_fix_integrity_rpc.sql` | N/A | NEW | CREATE — update `get_table_integrity` RPC |

### Bug 10: OrphanScanner (MEDIUM)
| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/features/sync/engine/orphan_scanner.dart` | `OrphanScanner.scan()` | 21-104, line 27 | MODIFY — remove `.eq('company_id', companyId)` + add path assertion |

### Bug 11: Duplicate Keys (LOW)
| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/shared/testing_keys/entries_keys.dart` | `EntriesTestingKeys.entryEditButton` | line 80 | MODIFY — convert to factory method with `EntrySection` enum |
| `lib/features/entries/presentation/screens/home_screen.dart` | `_HomeScreenState._buildEditablePreviewSection()` | line 1311 | MODIFY — pass section enum to key factory |

### Bug 15: Stale Config Banner (LOW)
| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/features/auth/presentation/providers/app_config_provider.dart` | `AppConfigProvider.isConfigStale` | 62-66 | MODIFY — return false when `_latestServerContact == null` |

### Bug 16: Sync Error Snackbar (LOW)
| File | Symbol | Lines | Change Type |
|------|--------|-------|-------------|
| `lib/features/sync/presentation/providers/sync_provider.dart` | `SyncProvider` class fields | ~30 | MODIFY — add `_syncErrorSnackbarVisible` flag |
| `lib/features/sync/presentation/providers/sync_provider.dart` | `SyncProvider._setupListeners()` | 83-147, line 122 | MODIFY — check dedup flag before calling toast |
| `lib/core/router/app_router.dart` | ScaffoldWithNavBar builder | 656-669 | MODIFY — set/clear flag in SnackBar lifecycle |

## Dependent Files (2+ levels)

| File | Reason |
|------|--------|
| `lib/features/sync/orchestrator/sync_orchestrator.dart` | Calls `SyncEngine.pushAndPull()` — indirectly affected by Bug 1 |
| `lib/features/todos/data/repositories/todo_repository.dart` | Uses `TodoItem.toMap()` — benefits from Bug 2 fix |
| `lib/features/todos/presentation/providers/todo_provider.dart` | Consumes TodoRepository — transitively benefits |
| `lib/features/sync/adapters/table_adapter.dart` | Base class with `supportsSoftDelete` — Bug 9 references it |
| `lib/features/sync/adapters/project_assignment_adapter.dart` | `supportsSoftDelete => false` — Bug 9 depends on this |
| `lib/features/photos/data/repositories/photo_repository.dart` | Bug 5 injects this into TestPhotoService |
| `lib/features/auth/presentation/providers/auth_provider.dart` | Bug 7 profile-completion gate reads user profile |

## Test Files

| Test File | Bugs Covered |
|-----------|-------------|
| `test/features/sync/engine/sync_engine_test.dart` | Bug 1 (enrollment), Bug 9 (supportsSoftDelete) |
| `test/features/todos/data/models/todo_item_test.dart` | Bug 2 (toMap priority) |
| `test/features/sync/adapters/type_converters_test.dart` | Bug 2 (TodoPriorityConverter) — NEW |
| `test/features/entries/presentation/screens/home_screen_test.dart` | Bug 3, Bug 4 |

## Supabase Migrations (DEPLOY FIRST)

1. `20260320000000_fix_handle_new_user.sql` — Bug 7: trigger + backfill
2. `20260320000001_fix_integrity_rpc.sql` — Bug 9: RPC conditional `deleted_at`

## Data Flow

```
Bug 1 (Sync Pull):
  SyncEngine._pull() → _pullTable(project_assignments) → [NEW] _enrollProjectsFromAssignments()
    → INSERT synced_projects → _loadSyncedProjectIds() → child adapters see project scope

Bug 2 (Todo Push):
  TodoItem.toMap() → {priority: index} → TodoItemAdapter.convertForRemote()
    → TodoPriorityConverter.toRemote() → Supabase INSERT (integer) → ✓

Bug 16 (Snackbar Dedup):
  SyncProvider._setupListeners().onSyncComplete → check _syncErrorSnackbarVisible
    → if false: call onSyncErrorToast → app_router shows SnackBar → set flag true
    → SnackBar auto-dismiss → set flag false
```

## Blast Radius Summary

| Category | Count |
|----------|-------|
| Direct modifications | 22 files |
| New files | 3 (2 SQL migrations, 1 test) |
| Dependent files | 7 |
| Test files | 4 |
| Supabase migrations | 2 (deploy first) |
| DB version bump | 38 → 39 |

# Dependency Graph: Baseline Bugfix v2

## Direct Changes

### BUG-17 (CRITICAL): Stop clearing local data on sign-out
| File | Lines | Change Type |
|------|-------|-------------|
| `lib/features/auth/presentation/providers/auth_provider.dart` | 323-358 (signOut), 365-379 (signOutLocally) | MODIFY: Remove `clearLocalCompanyData` calls |
| `lib/features/auth/services/auth_service.dart` | 312-358 (clearLocalCompanyData) | NO CHANGE: Keep method for account-delete/company-switch use |

**Callers of clearLocalCompanyData:**
- `auth_provider.dart:338` (signOut) - REMOVE
- `auth_provider.dart:369` (signOutLocally) - REMOVE
- `auth_provider.dart:778` (_mockSignOut) - REMOVE

**What signOut SHOULD still do:**
- Call `_authService.signOut()` (Supabase sign-out)
- Dispose BackgroundSyncHandler
- Clear in-memory state (_currentUser, _userProfile, _company, _isPasswordRecovery)
- Clear secure storage and recovery flags
- Do NOT clear SQLite data tables or sync metadata

### BUG-15 + BUG-7 (HIGH): Fix integrity RPC
| File | Lines | Change Type |
|------|-------|-------------|
| `supabase/migrations/20260320000003_fix_integrity_rpc_v2.sql` | NEW | CREATE: Revert to RETURNS TABLE, add entry_contractors to allowlist |
| `lib/features/sync/engine/integrity_checker.dart` | 189-203 (_checkTable) | NO CHANGE: Code already handles List<Map> from RETURNS TABLE |

**entry_contractors scoping path:** entry_id -> daily_entries.project_id -> projects.company_id (same ELSE branch as entry_equipment, entry_quantities, entry_personnel_counts)

### BUG-2 + BUG-8 (HIGH): Fix draft discard crash
| File | Lines | Change Type |
|------|-------|-------------|
| `lib/features/projects/presentation/screens/project_setup_screen.dart` | 359 (_discardDraft loop) | MODIFY: Remove 'equipment' from direct-delete list |

**Current:** `['equipment', 'bid_items', 'contractors', 'locations', 'personnel_types']`
**Fixed:** `['bid_items', 'contractors', 'locations', 'personnel_types']`
Equipment cascades via FK: `equipment.contractor_id REFERENCES contractors(id) ON DELETE CASCADE`

### BUG-1 (HIGH): Fix contractor type dropdown save
| File | Lines | Change Type |
|------|-------|-------------|
| `lib/features/projects/presentation/widgets/add_contractor_dialog.dart` | 98-120 (_handleAdd) | MODIFY: Await createContractor before Navigator.pop |

**Current flow:** Navigator.pop(context) -> await createContractor (fire and forget after pop)
**Fixed flow:** await createContractor -> if success Navigator.pop(context)

### BUG-4 (HIGH): Fix unarchive not reflecting in UI
| File | Lines | Change Type |
|------|-------|-------------|
| `lib/features/projects/presentation/providers/project_provider.dart` | 538-572 (toggleActive) | MODIFY: Call _buildMergedView() before notifyListeners() |

**_buildMergedView** (line 662-695) rebuilds `_mergedProjects` from `_projects` + `_remoteProjects`. Without it, `archivedProjects` getter (line 156) reads stale `_mergedProjects`.

### BUG-9 (MEDIUM): Fix TextEditingController lifecycle in photo dialog
| File | Lines | Change Type |
|------|-------|-------------|
| `lib/features/entries/presentation/widgets/photo_detail_dialog.dart` | 25-232 (showPhotoDetailDialog) | MODIFY: Convert to StatefulWidget or dispose controllers before pop |

**Controllers at risk:** filenameController (line 33), descriptionController (line 34)
**Pattern reference:** `lib/features/photos/presentation/widgets/photo_name_dialog.dart` (proper StatefulWidget with dispose)

### BUG-10 (MEDIUM): Fix duplicate GlobalKeys on project edit navigation
| File | Lines | Change Type |
|------|-------|-------------|
| `lib/features/projects/presentation/screens/project_setup_screen.dart` | 43 (_formKey) | MODIFY: Investigate DropdownButton overlay key collision during GoRouter transitions |

**Root cause:** DropdownButton creates internal overlay entries with GlobalKeys. During GoRouter animated transitions, two ProjectSetupScreen instances coexist momentarily. The _formKey itself is per-instance (correct), but overlay-internal keys collide.

### BUG-5 (MEDIUM): Add contractor edit UI
| File | Lines | Change Type |
|------|-------|-------------|
| `lib/features/projects/presentation/widgets/add_contractor_dialog.dart` | 8-120 | MODIFY: Add optional existingContractor param for edit mode |
| `lib/features/projects/presentation/screens/project_setup_screen.dart` | 558-678 (_buildContractorsTab) | MODIFY: Add edit IconButton to contractor card trailing |

**Backend ready:** `ContractorProvider.updateContractor()` exists at line 96, fully implemented.

### BUG-13 (MEDIUM): Add form response delete UI
| File | Lines | Change Type |
|------|-------|-------------|
| `lib/features/forms/presentation/screens/forms_list_screen.dart` | 171-186 (saved response ListTile) | MODIFY: Add delete IconButton next to "Open" button |

**Backend ready:** `InspectorFormProvider.deleteResponse()` exists at line 300, fully implemented.

### BUG-14 (MEDIUM): Fix inject-photo-direct for real sync lifecycle
| File | Lines | Change Type |
|------|-------|-------------|
| `lib/core/driver/test_photo_service.dart` | 64-108 (injectPhotoDirect) | MODIFY: Copy bundled test photos to real photo dir |
| `test_assets/test_photo_1.jpg` | NEW | CREATE: Bundled test photo 1 |
| `test_assets/test_photo_2.jpg` | NEW | CREATE: Bundled test photo 2 |

**Sync chain:** Phase 1 (upload file to storage) -> Phase 2 (upsert metadata) -> Phase 3 (mark synced)
**Current break:** PhotoAdapter.localOnlyColumns strips file_path; file not uploaded because path is temp.

### BUG-3/11/12 (LOW): Missing testing keys
| File | Lines | Change Type |
|------|-------|-------------|
| Multiple widget files | Various | MODIFY: Add Key parameters |
| `lib/shared/testing_keys/*.dart` | Various | MODIFY: Add new key constants |

**Files needing keys (BUG-3 pattern):**
- Bid item autocomplete suggestions (GlobalObjectKey -> keyed widget)
- Location dropdown items in entry wizard
- Weather edit dialog elements
- Submit confirmation dialog buttons (already have keys in entries_keys.dart: submitCancelButton, submitConfirmButton)
- Todo delete IconButton + PopupMenuItem
- Form response "Open" FilledButton
- Edit profile fields + save button
- Gauge/Initials dialog fields (hot-restart issue)
- Trash restore/delete-forever buttons (hot-restart issue)
- Member role dropdown (hot-restart issue)

**BUG-11:** Photo thumbnail delete GestureDetector needs key (`photo_thumbnail.dart:253`)
**BUG-12:** Equipment Chip deleteIcon not separately tappable. Replace Chip with custom widget exposing delete as keyed button.

## Blast Radius Summary

| Category | Count |
|----------|-------|
| Direct file changes | ~18 |
| Supabase migrations | 1 |
| Testing key files | ~6 |
| Test asset files | 2 |
| Total files affected | ~27 |

## Data Flow Diagram

```
Sign-Out Flow (BUG-17):
  AuthProvider.signOut()
    -> AuthService.signOut() (Supabase)
    -> [REMOVE] AuthService.clearLocalCompanyData(db)
    -> Clear in-memory state only
    -> notifyListeners()

Integrity Check Flow (BUG-7/15):
  SyncEngine.pushAndPull()
    -> IntegrityChecker.run()
      -> for each adapter: _checkTable(adapter)
        -> supabase.rpc('get_table_integrity', params)
          -> [FIX] RETURNS TABLE (not json)
          -> [FIX] entry_contractors in allowlist
        -> Compare local vs remote counts

Draft Discard Flow (BUG-2/8):
  _ProjectSetupScreenState._discardDraft()
    -> [FIX] Remove 'equipment' from delete list
    -> Delete: bid_items, contractors, locations, personnel_types
    -> Equipment cascades via FK on contractor delete

Contractor Add Flow (BUG-1):
  AddContractorDialog._handleAdd()
    -> [FIX] await contractorProvider.createContractor()
    -> THEN Navigator.pop()

Unarchive Flow (BUG-4):
  ProjectProvider.toggleActive()
    -> _repository.setActive()
    -> Update _projects[index]
    -> [FIX] _buildMergedView()
    -> notifyListeners()
```

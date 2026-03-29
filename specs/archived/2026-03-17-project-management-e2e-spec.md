# Project Management End-to-End Fix Spec

**Date**: 2026-03-17
**Session**: 585
**Status**: REVIEWED — adversarial findings applied

## 1. Overview

### Purpose
Fix the broken project management lifecycle end-to-end: import, creation, deletion, sync enrollment, and provider wiring. Currently, the Import button crashes (missing Provider), background sync auto-enrolls all projects (defeating selective download), photo files leak on removal, draft projects create orphans, and testing/logging coverage has critical gaps.

### Root Cause
The audit (S585) found 13 issues across 4 priority levels. The core tension: two conflicting sync models in the codebase (selective import vs auto-sync everything) with a missing Provider registration that crashes the entire project management UI.

### Scope

**In scope:**
- P0: Register SyncOrchestrator as a Provider (crash fix)
- Sync model: metadata auto-syncs via background pull, full data download only on explicit user confirmation
- Remove BLOCKER-38 auto-enrollment from `_pullTable()` — background sync must NOT auto-enroll
- Unified project cards with "My Projects" / "Available Projects" sections
- Role changes: Remove viewer role enum value, enforce Admin/Engineer/Inspector permissions
- Admin can delete remote-only projects directly (Supabase SECURITY DEFINER RPC)
- Immediate push on project creation when online; deferred push when offline
- Draft prompt on back navigation (save or discard)
- Full cleanup on soft-delete (remove from synced_projects, stop syncing)
- Photo file deletion on removeFromDevice
- ProjectSyncHealthProvider wiring
- Orphaned synced_projects cleanup
- All testing gaps from audit (sync engine error paths, project UI flows, provider methods)
- All logging gaps from audit (push/pull summaries, error categories, lifecycle events)
- Full mock-Supabase integration tests for `_push()`/`_pull()` end-to-end
- Photo three-phase push tests

**Out of scope:**
- Version-upgrade re-auth behavior (keep as-is per user decision)
- Notifications to team members on project creation

### Success Criteria
- [ ] Import button works — tapping shows confirmation, then downloads project data
- [ ] Fresh install shows all company projects as metadata with download option
- [ ] Background sync ONLY pushes/pulls for explicitly enrolled projects, never auto-enrolls
- [ ] Admin can delete any project (including remote-only) from any state
- [ ] Engineer can delete their own projects only
- [ ] Inspector cannot create or delete projects
- [ ] No orphaned photo files, draft rows, or synced_projects entries
- [ ] 0 crashes on project_list_screen (all Providers registered)
- [ ] Push/pull result summaries logged for every sync cycle
- [ ] All error categories individually logged in _handlePushError
- [ ] All HIGH testing gaps from audit have passing tests
- [ ] Failed imports show retry/cancel affordance (not broken card)
- [ ] Create-while-offline saves locally and defers push

---

## 2. Data Model

### Role Changes

Remove `UserRole.viewer` from the Dart enum. The enum becomes 3 roles:

| Role | Create Projects | Edit Projects | Delete Projects | Download Projects |
|------|----------------|---------------|-----------------|-------------------|
| Admin | Yes | All | All (including remote-only via Supabase RPC) | Yes |
| Engineer | Yes | Own + assigned | Own only | Yes |
| Inspector | No | Assigned only | No | Yes |

**IMPORTANT (MF-3)**: Keep `canWrite` property on `UserRole` and `AuthProvider`. It returns `true` for all 3 remaining roles (admin, engineer, inspector). This avoids touching 24 files and 10+ providers that depend on `canWrite` as a callback. Add NEW role-specific methods (`canCreateProject`, `canDeleteProject`, `canEditProject`) alongside `canWrite`, not as replacements.

### Supabase Migration

The migration must:
1. Convert any existing `role = 'viewer'` rows to `role = 'inspector'`:
   ```sql
   UPDATE user_profiles SET role = 'inspector' WHERE role = 'viewer';
   ```
2. Update CHECK constraint to remove 'viewer' (MF-6):
   ```sql
   ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS user_profiles_role_check;
   ALTER TABLE user_profiles ADD CONSTRAINT user_profiles_role_check CHECK (role IN ('admin','engineer','inspector'));
   ```
3. Update `approve_join_request` RPC to reject 'viewer' as valid role
4. Update `update_member_role` RPC to reject 'viewer' as valid role
5. Add inspector guard to projects UPDATE policy (MF-4):
   ```sql
   -- Prevent inspectors from soft-deleting projects via RLS
   -- WITH CHECK must include: NOT (role = 'inspector' AND deleted_at IS NOT NULL)
   ```

### synced_projects Table — No Schema Change

Behavioral change only:
- **INSERT**: Only via explicit user action (download confirmation, project creation, manual toggle)
- **DELETE**: On removeFromDevice, soft-delete cleanup, sign-out, and orphan cleanup
- **NEVER** auto-inserted during background sync pull

### Orphaned synced_projects Cleanup (SC-2)

If `synced_projects.project_id` has no matching row in `projects` table, delete the enrollment entry. Run this check:
- During `_loadSyncedProjectIds()` in sync engine
- On Projects screen open

### Sync Scope Changes

| Sync Action | Current Behavior | New Behavior |
|-------------|-----------------|-------------|
| Background pull (projects table) | Pulls ALL company projects, auto-enrolls each | Pulls ALL company projects (metadata), **NO auto-enroll** |
| Background pull (child tables) | Pulls for enrolled projects | No change |
| Available Projects data source | `fetchRemoteProjects()` direct Supabase query | **Local SQLite query** — `SELECT * FROM projects WHERE id NOT IN (SELECT project_id FROM synced_projects)`. Pull-to-refresh triggers sync for freshness. |
| Project creation | Draft inserted, push on next sync | Draft in SQLite, **immediate push on Save** (when online) or deferred push (when offline) |
| Soft-delete cleanup | Leaves synced_projects entry | **Removes synced_projects entry** + change_log entry to propagate via triggers |

### Auto-Enrollment Removal (Option A)

Keep `ScopeType.direct` on ProjectAdapter so background sync still pulls all company projects into local SQLite (for metadata in "Available Projects" section). **Remove** the auto-enroll insert into `synced_projects` from `_pullTable()`. Child data only syncs for explicitly enrolled projects.

---

## 3. User Flow

### Projects Screen — Two Sections

```
┌─────────────────────────────────┐
│  Projects                    🔍 │
├─────────────────────────────────┤
│  MY PROJECTS (2)                │
│  ┌───────────────────────────┐  │
│  │ ✅ Springfield  [Active]  │  │
│  │ # 7383i  │  ACME Corp    │  │
│  │ 📅 Today    ✏️  📦       │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ 🔄 Test         [Active]  │  │
│  │ # 28584  │  No client    │  │
│  │ 📅 3 days ago  ✏️  📦    │  │
│  └───────────────────────────┘  │
│                                 │
│  AVAILABLE PROJECTS (1)         │
│  ┌───────────────────────────┐  │
│  │ ☁️  hhhhj                 │  │
│  │ # u765                    │  │
│  │           ⬇️ Download     │  │
│  └───────────────────────────┘  │
│                                 │
│            [+ New Project]      │
└─────────────────────────────────┘
```

**Data source**: "My Projects" = projects in `synced_projects`. "Available Projects" = projects in local SQLite NOT in `synced_projects` (populated by background sync metadata pull). Pull-to-refresh triggers a sync to get the latest from Supabase.

### Interactions by Card Type

**My Projects (enrolled/local):**
- **Tap** → opens project dashboard
- **Long-press** → delete sheet (Remove from Device / Delete from Database)
- **Edit/Archive** icons visible per role permissions
- **Failed import state** → card shows "Download incomplete — tap to retry" with retry/cancel options (MF-2)

**Available Projects (remote-only metadata):**
- **Tap** → shows download confirmation dialog
- **Long-press** → Admin only: delete from database (Supabase RPC)
- **Download button** → same confirmation dialog as tap

### Download Confirmation Dialog

```
┌─────────────────────────────────┐
│  Download "Springfield"?        │
│                                 │
│  This will download all         │
│  project data including         │
│  entries, photos, and           │
│  locations to this device.      │
│                                 │
│  [Cancel]          [Download]   │
└─────────────────────────────────┘
```

### Project Creation Flow

1. Tap "+ New Project" → ProjectSetupScreen opens (Admin/Engineer only — FAB hidden for Inspector)
2. Draft row inserted in SQLite (trigger-suppressed, as today)
3. User fills in project details, locations, contractors, etc.
4. **Save**:
   - Enroll in `synced_projects`
   - If online → **immediate push** to Supabase (fire-and-forget with banner, not blocking — SC from review) → navigate to dashboard
   - If offline → save locally, defer push to next sync cycle. No error shown. (MF-1)
5. **Back without saving** → prompt dialog: "Save as draft?" / "Discard"
   - Save draft → row stays, shown in "My Projects" with `[Draft]` badge
   - Discard → delete draft row + all child records immediately

**Push ordering (MF-4 security)**: Immediate push must follow SyncRegistry adapter ordering (projects first, then children). Verified: `syncLocalAgencyProjects()` uses the registry ordering.

### Delete Flows

| Action | Who Can | What Happens |
|--------|---------|-------------|
| Remove from Device | Any role (own enrolled projects) | Hard-deletes local data + photos from disk + removes from synced_projects. Supabase untouched. Project moves to "Available". |
| Delete from Database (local) | Admin (any) or Engineer (own) | Soft-delete → triggers create change_log entry → immediate push → remove from synced_projects → clean up. |
| Delete from Database (remote-only) | Admin only | SECURITY DEFINER RPC `admin_soft_delete_project(project_id)`. No local data to clean. Disappears from "Available" on next sync/refresh. |

---

## 4. State Management

### Provider Fix (P0)

Add `Provider<SyncOrchestrator>.value(value: syncOrchestrator)` to the MultiProvider tree in `main.dart`. This unblocks all 3 call sites in `project_list_screen.dart`.

### Role Changes

- Delete `UserRole.viewer` from Dart enum
- **Keep `canWrite`** property — returns `true` for all 3 remaining roles (MF-3). No changes to the 24 files that use it.
- **Add** new role-specific methods on `AuthProvider`:
  - `bool get canCreateProject` → `role == admin || role == engineer`
  - `Future<bool> canDeleteProject(String projectId)` → `isAdmin || (isEngineer && createdByCurrentUser)`
  - `bool canEditProject(String projectId)` → `isAdmin || isEngineer || isAssignedInspector`
- `UserRole.fromString('viewer')` returns `UserRole.inspector` as fallback (already the default case behavior)

### ProjectProvider Changes

- Remove `fetchRemoteProjects()` Supabase call — no longer needed (SC-1)
- `myProjects` → query `projects` table joined with `synced_projects` (enrolled)
- `availableProjects` → query `projects` table WHERE `id NOT IN synced_projects` (metadata only)
- Reduce metadata columns for available projects to `id, name, project_number, company_id, is_active, updated_at` (SC-6 security)
- Pull-to-refresh triggers `syncOrchestrator.syncLocalAgencyProjects()` for freshness

### ProjectSyncHealthProvider — Wire It Up

Add call to `updateCounts()` after each sync cycle completes (in SyncProvider or SyncOrchestrator callback) so badges reflect actual sync status.

### Role Refresh on Screen Open (SC-5)

Call `authProvider.refreshUserProfile()` on Projects screen open alongside the data refresh. One additional Supabase query ensures role freshness — prevents stale-role authorization bypass.

---

## 5. Sync Engine Changes

### Remove Auto-Enrollment from `_pullTable()`

Remove the BLOCKER-38 auto-enrollment code from `sync_engine.dart`:
```dart
// REMOVE from _pullTable() (~lines 1082-1088):
if (adapter.tableName == 'projects') {
  await db.insert('synced_projects', {
    'project_id': recordId,
    'synced_at': DateTime.now().toUtc().toIso8601String(),
  }, conflictAlgorithm: ConflictAlgorithm.ignore);
  Logger.sync('Auto-enrolled pulled project: $recordId');
}
```

Also remove the `_loadSyncedProjectIds()` reload after projects adapter in `_pull()`:
```dart
// REMOVE from _pull() (~lines 977-981):
if (adapter.tableName == 'projects' && count > 0) {
  await _loadSyncedProjectIds();
  Logger.sync('Reloaded synced project IDs after pulling $count projects');
}
```

### Keep `ScopeType.direct` on ProjectAdapter

Projects adapter still pulls ALL company projects into local SQLite for metadata display. The difference: pulled projects are NOT enrolled, so child data is never downloaded unless the user explicitly confirms.

### Immediate Push on Project Creation

After `_saveProject()` in `ProjectSetupScreen`:
1. Enroll in `synced_projects`
2. If online → trigger `syncOrchestrator.syncLocalAgencyProjects()` as fire-and-forget with banner
3. If offline → no push, deferred to next sync cycle (MF-1)
4. Push follows SyncRegistry ordering: project first, then children (MF-4 security)

### Soft-Delete Cleanup

When `cascadeSoftDeleteProject()` runs:
1. Soft-delete the project and children (as today) — **triggers must be enabled** so change_log entries are created by SQLite triggers, not manually inserted (MF-6 from code review)
2. **NEW**: Remove from `synced_projects`
3. Change_log entries created by triggers in step 1 handle propagation
4. **NEW**: If online, trigger immediate push so the delete propagates
5. Clean up remaining change_log entries for that project (except the soft-delete entries)

### Remote-Only Delete (Admin) — SECURITY DEFINER RPC (MF-5)

New Supabase RPC function:
```sql
CREATE OR REPLACE FUNCTION admin_soft_delete_project(p_project_id TEXT)
RETURNS void AS $$
BEGIN
  -- Verify caller is admin
  IF NOT is_approved_admin() THEN
    RAISE EXCEPTION 'Only admins can delete projects remotely';
  END IF;

  -- Verify project belongs to caller's company
  IF NOT EXISTS (SELECT 1 FROM projects WHERE id = p_project_id AND company_id = get_my_company_id()) THEN
    RAISE EXCEPTION 'Project not found or not in your company';
  END IF;

  -- Soft-delete
  UPDATE projects SET deleted_at = NOW(), deleted_by = auth.uid(), updated_at = NOW()
  WHERE id = p_project_id;

  RAISE LOG 'admin_soft_delete_project: % by %', p_project_id, auth.uid();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

New method on `ProjectLifecycleService`:
```dart
Future<void> deleteFromSupabase(String projectId, {required bool isAdmin}) async {
  // Defense-in-depth: client-side admin check (SC-7)
  if (!isAdmin) {
    throw StateError('Only admins can delete remote-only projects');
  }
  await Supabase.instance.client.rpc('admin_soft_delete_project', params: {'p_project_id': projectId});
  // Remove from local SQLite metadata cache
  await _db.delete('projects', where: 'id = ?', whereArgs: [projectId]);
  Logger.sync('REMOTE_DELETE projectId=$projectId');
}
```

### SyncMutex Behavior During Import (SC-4)

If background sync holds the mutex when user taps "Download", the import's `syncLocalAgencyProjects()` call will wait for the mutex to release. The ImportRunner banner shows "Syncing..." state during this wait. No timeout — the user can navigate away and the import completes in the background.

---

## 6. Edge Cases & Error Handling

### Import Failures

| Scenario | Behavior |
|----------|----------|
| Network drops mid-download | SnackBar error. Enrollment persists — next background sync retries. Card shows "Download incomplete — tap to retry". |
| Supabase RLS denies access | SnackBar: "Permission denied. Contact your administrator." |
| Duplicate import tap | Double-tap guard (existing `runner.isImporting` check). |
| Import project deleted mid-download | Sync pulls soft-deleted project. Show as deleted, option to remove from device. |
| Failed import — incomplete data | Card in "My Projects" shows warning badge + "Tap to retry" or "Cancel download" option (MF-2). |
| Orphaned synced_projects entry (project deleted remotely) | Cleanup removes enrollment. Project disappears from "My Projects". |

### Create Edge Cases

| Scenario | Behavior |
|----------|----------|
| **Create while offline** (MF-1) | Draft saved locally, enrolled in synced_projects, push deferred to next sync cycle. No error shown. Banner: "Will sync when online." |
| Create while online | Immediate fire-and-forget push with banner. Navigate to dashboard immediately. |
| Push fails after creation | Change_log entry persists. Next sync retries. Project visible locally with "pending sync" badge. |

### Delete Edge Cases

| Scenario | Behavior |
|----------|----------|
| Delete while offline (local, unsynced changes) | Service guard throws StateError. UI: "Sync first" dialog. |
| Delete while offline (remote-only, admin) | SnackBar: "Cannot delete while offline." Block action. |
| Engineer deletes another engineer's project | `canDeleteProject()` returns false. Button not shown. Service + RLS enforce. |
| Inspector tries to delete own project | `canDeleteProject()` returns false. Button not shown. RLS also blocks (MF-4). |
| Two admins delete same project | Both soft-deletes propagate. Idempotent. |
| Remove from device, then re-download | Project moves to "Available", user downloads, full data re-syncs. Clean round-trip. |

### Draft Edge Cases

| Scenario | Behavior |
|----------|----------|
| Back button during creation | Prompt: "Save as draft?" / "Discard" |
| App killed during creation | Draft persists. Shown in "My Projects" with `[Draft]` badge. |
| Draft older than 30 days | StartupCleanupService runs as safety net. User manages explicitly. |
| Engineer creates draft, role changed to Inspector | Draft is theirs. Can finish saving but cannot create NEW projects. |

### Permission Edge Cases

| Scenario | Behavior |
|----------|----------|
| Inspector taps project card | Opens (if enrolled) or download confirmation (if available). No create/delete. |
| Admin deletes project Inspector is editing | Inspector's next save fails. SnackBar: "Project deleted." Navigate to list. |
| Role changes while app is open | AuthProvider notifies. Role refreshed on Projects screen open (SC-5). UI rebuilds. |
| Stale role cache | RLS is ultimate enforcement. Client-side checks are defense-in-depth only. |

---

## 7. Testing Strategy

### HIGH Priority — New Tests Required

| Area | Test | What to Verify |
|------|------|---------------|
| Import flow E2E | `test: enroll → sync → verify local data` | enrollProject + syncLocalAgencyProjects produces local data |
| Delete flow | `test: removeFromDevice success + failure` | Local data deleted, photos deleted from disk, synced_projects cleaned |
| Delete flow | `test: deleteFromDatabase success + permission denied` | Soft-delete propagates, unauthorized blocked, synced_projects cleaned |
| `_handlePushError()` | `test: 42501 RLS denial` | Increments `_rlsDenialCount`, marks failed, logged |
| `_handlePushError()` | `test: 23503 FK violation` | Marks failed with correct message, logged |
| `_handlePushError()` | `test: 429/503 rate limit` | Marks failed, retryable, logged |
| `_handlePushError()` | `test: SocketException/TimeoutException` | Marks failed, retryable, logged |
| Available Projects | `test: SQLite query for non-enrolled projects` | Correct projects in Available section |
| Download confirmation | `widget test: dialog show/cancel/confirm` | Dialog renders, cancel returns, confirm triggers import |
| Section rendering | `widget test: My Projects + Available` | Section headers render, correct projects in each |
| Role permissions | `widget test: Admin/Engineer/Inspector` | Correct actions visible per role |
| SyncProvider | `test: rlsDenials > 0 triggers toast` | Error callback invoked with message |
| Mock-Supabase | `test: _push() end-to-end` | Full push flow with mock Supabase client |
| Mock-Supabase | `test: _pull() end-to-end` | Full pull flow with mock Supabase client |
| Mock-Supabase | `test: _pullTable() conflict resolution` | Local-wins and remote-wins paths exercised |
| Photo push | `test: three-phase push` | Phase 1 upload, Phase 2 upsert, Phase 3 local mark, Phase 2 cleanup on failure |
| Failed import | `test: incomplete import shows retry/cancel` | Card shows warning state, retry triggers re-sync, cancel removes enrollment |
| Create offline | `test: save offline defers push` | Project saved, enrolled, no push error, syncs when online |
| Orphan cleanup | `test: orphaned synced_projects cleaned` | Enrollment deleted when project_id has no matching project row |

### MEDIUM Priority — New Tests Required

| Area | Test | What to Verify |
|------|------|---------------|
| Import error paths | `test: network failure → snackbar` | isSupabaseOnline=false triggers snackbar |
| Import double-tap | `test: isImporting guard` | Second tap returns early |
| SyncProvider | `test: circuit breaker state` | circuitBreakerTripped set correctly |
| ProjectProvider | `test: deleteProject, selectProject, toggleActive` | Provider methods work correctly |
| Draft handling | `test: back navigation prompt` | Dialog shown, save/discard work |
| Photo file cleanup | `test: removeFromDevice deletes files` | File.delete called for each path |
| Remote-only delete | `test: admin can delete via RPC, engineer cannot` | RPC call for admin, blocked for others |
| Remote-only delete | `test: inspector cannot soft-delete own project via RLS` | RLS blocks inspector soft-delete |
| Role refresh | `test: screen open refreshes profile` | refreshUserProfile called on init |

### LOW Priority

| Area | Test |
|------|------|
| Search | Filter by name, number, client |
| Loading state | CircularProgressIndicator shown |
| Error state | Error widget with retry |
| RefreshIndicator | Pull-to-refresh triggers sync |

---

## 8. Logging Strategy

### HIGH Priority — Add Immediately

| Location | Log Call | Purpose |
|----------|---------|---------|
| `_push()` completion | `Logger.sync('Push complete: $pushed pushed, $errors errors, $rlsDenials RLS denials')` | Sync cycle visibility |
| `_pull()` completion | `Logger.sync('Pull complete: $pulled pulled, $errors errors')` | Sync cycle visibility |
| `pushAndPull()` completion | `Logger.sync('Sync cycle: pushed=$X pulled=$Y errors=$Z duration=${ms}ms')` | Overall cycle summary |
| `_handlePushError()` 23505 | `Logger.sync('CONSTRAINT 23505: ${change.tableName}/${change.recordId}')` | Error categorization |
| `_handlePushError()` 23503 | `Logger.sync('FK VIOLATION 23503: ${change.tableName}/${change.recordId}')` | Error categorization |
| `_handlePushError()` 429/503 | `Logger.sync('RATE LIMITED: ${change.tableName}/${change.recordId}')` | Error categorization |
| `_handlePushError()` network | `Logger.sync('NETWORK ERROR: ${change.tableName}/${change.recordId}: $e')` | Error categorization |
| `_handleAuthError()` | `Logger.auth('Auth refresh attempted: success=$result')` | Auth debug |

### MEDIUM Priority

| Location | Log Call | Purpose |
|----------|---------|---------|
| `_handleRemoveFromDevice()` start | `Logger.sync('Remove from device: $projectId')` | Delete tracking |
| `_handleRemoveFromDevice()` success | `Logger.sync('Remove complete: $projectId')` | Delete tracking |
| `_handleDeleteFromDatabase()` start | `Logger.sync('Delete from database: $projectId')` | Delete tracking |
| `canDeleteFromDatabase()` result | `Logger.sync('Delete permission: $projectId allowed=$result')` | Permission audit |
| Import success | `Logger.sync('Import complete: $projectId')` | Import tracking |
| Network check failure | `Logger.sync('Network check failed — offline')` | Debug connectivity |
| `removeFromDevice()` steps | `Logger.sync('Remove step N: ...')` | Transaction debugging |
| `removeFromDevice()` force flag | `Logger.sync('Remove: force=$forceOfflineRemoval')` | Distinguish force |
| Remote delete (admin) | `Logger.sync('REMOTE_DELETE projectId=$projectId')` | Admin action audit |

### LOW Priority

| Location | Log Call | Purpose |
|----------|---------|---------|
| Role change detection | `Logger.auth('Role changed: $old → $new')` | Security audit |
| Sign-in/sign-out | `Logger.auth('Sign in/out: $userId')` | Session tracking |
| Profile load success | `Logger.auth('Profile loaded: role=$role')` | Debug auth |

---

## 9. Performance Considerations

### Metadata Source Change
Available Projects now comes from local SQLite instead of a Supabase query. This is faster (no network round-trip) and works offline. Fresh data arrives via background sync or pull-to-refresh.

### Download Confirmation
Large projects could take minutes. ImportRunner banner shows progress. Skip count pre-fetch for v1 — add counts later if requested.

### Section Rendering
Splitting projects into `myProjects` + `availableProjects` is a simple SQLite query with a NOT IN subquery. No performance concern.

### Immediate Push on Create
Fire-and-forget with banner (not blocking). User navigates to dashboard immediately. If push takes time on slow connection, the banner shows progress without blocking navigation.

---

## 10. Security Implications

### Remote-Only Delete — SECURITY DEFINER RPC (MF-5)
- `admin_soft_delete_project()` RPC validates admin role server-side
- Prevents column manipulation (raw UPDATE would allow arbitrary column changes)
- Client-side admin check as defense-in-depth (SC-7)
- Server-side audit logging via `RAISE LOG`

### Inspector Soft-Delete Blocked via RLS (MF-4)
- Current RLS allows any project owner to soft-delete, including inspectors
- New WITH CHECK clause: inspector role cannot set `deleted_at` on projects
- This closes the gap between spec (inspectors can't delete) and RLS (inspectors could delete own)

### Role Removal — Viewer (MF-6)
- Supabase migration converts `role = 'viewer'` → `role = 'inspector'`
- CHECK constraint updated to reject 'viewer'
- `approve_join_request` and `update_member_role` RPCs updated to reject 'viewer'
- `is_viewer()` function becomes dead code — clean up in future release (NH-1)
- `UserRole.fromString('viewer')` falls back to `inspector` during transition

### Metadata Column Reduction (SC-6)
- Available Projects query reduced to `id, name, project_number, company_id, is_active, updated_at`
- `description` and `created_by_user_id` not fetched for non-enrolled projects
- Reduces exposure if device is compromised

### Permission Enforcement Layers
1. **UI layer** — hides/disables buttons (defense-in-depth)
2. **Service layer** — throws on unauthorized action + client-side role check (enforcement)
3. **RLS layer** — Supabase rejects unauthorized writes (ultimate enforcement)

### Stale Role Cache Mitigation (SC-5)
- Role refreshed on Projects screen open via `authProvider.refreshUserProfile()`
- RLS is ultimate enforcement regardless of client cache state

---

## 11. Migration & Cleanup

### Code to Remove
- `UserRole.viewer` enum value (keep `canWrite`, it now always returns true)
- Auto-enrollment code in `sync_engine.dart:_pullTable()` (~lines 1082-1088)
- `_loadSyncedProjectIds()` reload in `_pull()` (~lines 977-981)
- `fetchRemoteProjects()` Supabase direct query in `ProjectProvider` (replaced by local SQLite query)

### Code to Add
- `Provider<SyncOrchestrator>.value()` in main.dart MultiProvider
- Role-specific permission methods: `canCreateProject`, `canDeleteProject(id)`, `canEditProject(id)` on AuthProvider
- Download confirmation dialog widget
- Draft save/discard prompt on back navigation in ProjectSetupScreen
- `admin_soft_delete_project()` Supabase RPC + `deleteFromSupabase()` on ProjectLifecycleService
- Photo file deletion in `_handleRemoveFromDevice()`
- `synced_projects` cleanup in `cascadeSoftDeleteProject()`
- Orphaned `synced_projects` cleanup (entries with no matching project row)
- Immediate push (fire-and-forget with banner) after project creation and database deletion
- Offline-aware creation: defer push when offline, no error
- Failed import card state with retry/cancel affordance
- `ProjectSyncHealthProvider.updateCounts()` call after sync cycles
- `availableProjects` local SQLite query (projects NOT IN synced_projects)
- Role refresh on Projects screen open
- All push/pull result logging (Section 8 HIGH)
- All error category logging in `_handlePushError()` (Section 8 HIGH)
- All lifecycle event logging (Section 8 MEDIUM)
- All tests from Section 7

### Supabase Migrations
1. Convert `role = 'viewer'` → `role = 'inspector'` + update CHECK constraint + update RPCs
2. Create `admin_soft_delete_project()` SECURITY DEFINER RPC
3. Add inspector guard to projects UPDATE WITH CHECK policy

---

## Decisions Log

| Decision | Rationale |
|----------|-----------|
| Auto-sync metadata only, explicit download for full data | New users don't need hundreds of projects auto-downloaded. Bandwidth/storage savings. |
| Option A: Keep ScopeType.direct, remove auto-enroll | Simplest change — remove 5 lines. Projects still sync for metadata. Child data gated by synced_projects. |
| Confirmation dialog before download | User must consent before large data transfers. |
| Unified cards with sections | Easy to find active work ("My Projects") and discover new projects ("Available"). Consistent card design. |
| Admin can delete remote-only directly via RPC | Admin shouldn't have to download a project just to delete it. RPC is safer than raw UPDATE. |
| Admin: all, Engineer: create+edit+delete own, Inspector: edit assigned | Matches construction industry hierarchy. |
| Remove viewer role | User confirmed it will never come up. 3 roles sufficient. |
| Keep `canWrite` (MF-3) | 102 occurrences across 24 files. Add new methods alongside, don't replace. |
| Immediate push on create (fire-and-forget) | Prevents orphaned children. Non-blocking with banner. |
| Defer push when offline (MF-1) | Save locally, no error. Push on next sync. Offline-first. |
| SECURITY DEFINER RPC for remote delete (MF-5) | Prevents column manipulation. Server-side admin validation. Audit logging. |
| Inspector can't soft-delete via RLS (MF-4) | Spec says Inspector: No delete. RLS must enforce this. |
| Update CHECK + RPCs to remove viewer (MF-6) | Prevents ghost viewer assignments after migration. |
| Available Projects from local SQLite + pull-to-refresh (SC-1) | Works offline, eliminates duplicate Supabase call, simpler code. |
| Reduce Available metadata columns (SC-6) | Minimizes data exposure on compromised devices. |
| Refresh role on screen open (SC-5) | Prevents stale-role authorization bypass. |
| Failed import shows retry/cancel (MF-2) | User must not be stuck with broken card in "My Projects". |
| Draft prompt on back (save/discard) | User controls whether abandoned work persists. |
| Full cleanup on soft-delete | No stale synced_projects entries. Clean state. |
| Photo files deleted on removeFromDevice | No orphaned files on disk. |
| Keep re-auth on every version bump | Security benefit outweighs convenience during beta. |
| All testing/logging gaps in scope | No orphan data, no silent failures, full observability. |

---

## Adversarial Review Summary

**Reviewed by**: code-review-agent (Opus), security-agent (Opus)
**Full review**: `.claude/adversarial_reviews/2026-03-17-project-management-e2e/review.md`

### Findings Applied
| # | Source | Finding | Resolution |
|---|--------|---------|------------|
| MF-1 | Code | Create-while-offline unspecified | Added: save locally, defer push, no error |
| MF-2 | Code | Failed import leaves broken card | Added: retry/cancel affordance on failed-import cards |
| MF-3 | Code | Removing canWrite touches 24 files | Changed: keep canWrite, add new methods alongside |
| MF-4 | Security | Inspector can soft-delete own projects via RLS | Added: inspector guard in projects UPDATE policy |
| MF-5 | Security | Raw UPDATE allows column manipulation | Changed: SECURITY DEFINER RPC for remote delete |
| MF-6 | Security | CHECK constraint + RPCs still accept viewer | Added: migration updates constraint + RPCs |
| SC-1 | Code | Use local SQLite for Available Projects | Accepted: eliminates Supabase query, works offline |
| SC-2 | Code | Orphaned synced_projects cleanup | Added: cleanup during _loadSyncedProjectIds |
| SC-4 | Code | SyncMutex during import undocumented | Added: documentation in Section 5 |
| SC-5 | Security | Stale role cache | Added: role refresh on screen open |
| SC-6 | Security | Metadata columns over-fetched | Added: reduced columns for Available |
| SC-7 | Security | No client-side admin guard on deleteFromSupabase | Added: isAdmin parameter with throw |

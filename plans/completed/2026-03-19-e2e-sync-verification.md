# E2E Sync Verification System Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Build a reusable e2e sync verification system with testing keys, debug server sync status endpoints, and Supabase REST verification tooling.
**Spec:** `.claude/specs/2026-03-19-e2e-sync-verification-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-19-e2e-sync-verification/`

**Architecture:** Testing keys defined in shared files are applied to sync and project UI widgets for flutter_driver discoverability. The HTTP debug server gains sync lifecycle status endpoints that the sync engine POSTs to during push/pull cycles. A PowerShell verification script queries Supabase PostgREST to confirm data landed correctly.
**Tech Stack:** Flutter/Dart (testing keys, sync engine), Node.js (debug server), PowerShell (verify-sync.ps1)
**Blast Radius:** 3 new files, 12 modified files, 3 dependent files, 4 test files, 0 cleanup

---

## Phase 1: Testing Keys Definition

### Sub-phase 1.1: Create sync_keys.dart

**Files:**
- Create: `lib/shared/testing_keys/sync_keys.dart`

**Agent**: `backend-data-layer-agent`

#### Step 1.1.1: Create SyncTestingKeys class

Create `lib/shared/testing_keys/sync_keys.dart`:

```dart
import 'package:flutter/material.dart';

/// Sync-related testing keys.
///
/// Includes sync dashboard actions and status indicators.
// FROM SPEC: 7 sync dashboard testing keys for e2e verification
class SyncTestingKeys {
  SyncTestingKeys._(); // Prevent instantiation

  // ============================================
  // Sync Dashboard Actions
  // ============================================

  /// "Sync Now" action tile
  static const syncNowTile = Key('sync_now_tile');

  /// "View Conflicts" action tile
  static const syncViewConflictsTile = Key('sync_view_conflicts_tile');

  /// "View Synced Projects" action tile
  static const syncViewProjectsTile = Key('sync_view_projects_tile');

  /// Circuit breaker "RESUME SYNC" button
  static const syncResumeSyncButton = Key('sync_resume_sync_button');

  // ============================================
  // Sync Dashboard Status
  // ============================================

  /// Status badge icon (idle/syncing/error)
  static const syncStatusBadge = Key('sync_status_badge');

  /// Last sync timestamp text
  static const syncLastSyncTimestamp = Key('sync_last_sync_timestamp');

  // ============================================
  // Sync Dashboard Buckets
  // ============================================

  /// Creates a key for a pending bucket ExpansionTile
  static Key syncBucketTile(String name) => Key('sync_bucket_tile_$name');
}
```

#### Step 1.1.2: Verify

No test yet — will be verified after facade update in 1.3.

---

### Sub-phase 1.2: Add project keys to projects_keys.dart

**Files:**
- Modify: `lib/shared/testing_keys/projects_keys.dart:78-111`

**Agent**: `backend-data-layer-agent`

#### Step 1.2.1: Add ~24 new keys after existing Project List section

Insert after line 111 (before the closing `}` of `ProjectsTestingKeys`), at the end of the class:

```dart
  // ============================================
  // Project List - Tabs
  // ============================================
  // FROM SPEC: Tab keys for e2e sync verification
  static const projectTabMyProjects = Key('project_tab_my_projects');
  static const projectTabCompany = Key('project_tab_company');
  static const projectTabArchived = Key('project_tab_archived');

  // ============================================
  // Project List - Filter Chips
  // ============================================
  static const projectFilterAll = Key('project_filter_all');
  static const projectFilterOnDevice = Key('project_filter_on_device');
  static const projectFilterNotDownloaded = Key('project_filter_not_downloaded');

  // ============================================
  // Project List - Download Dialog
  // ============================================
  /// Download button on remote-only project card
  static Key projectDownloadButton(String id) => Key('project_download_button_$id');

  /// Cancel button in download confirmation dialog
  static const projectDownloadDialogCancel = Key('project_download_dialog_cancel');

  /// Download/Confirm button in download confirmation dialog
  static const projectDownloadDialogConfirm = Key('project_download_dialog_confirm');

  // ============================================
  // Project List - Remote Delete Dialog
  // ============================================
  /// Cancel button in remote delete confirmation dialog
  static const projectRemoteDeleteDialogCancel = Key('project_remote_delete_dialog_cancel');

  /// Confirm/Delete button in remote delete confirmation dialog
  static const projectRemoteDeleteDialogConfirm = Key('project_remote_delete_dialog_confirm');

  // ============================================
  // Project Empty State
  // ============================================
  /// "Browse Available Projects" button in empty state
  static const projectBrowseButton = Key('project_browse_button');

  // ============================================
  // Project Setup - Description & Nav
  // ============================================
  /// Description TextFormField in project details form
  static const projectDescriptionField = Key('project_description_field');

  /// "Discard" button in back nav unsaved changes dialog
  static const projectDiscardButton = Key('project_discard_button');

  /// "Save Draft" button in back nav unsaved changes dialog
  static const projectSaveDraftButton = Key('project_save_draft_button');

  // ============================================
  // Removal Dialog
  // ============================================
  /// Cancel button in removal dialog
  static const removalDialogCancel = Key('removal_dialog_cancel');

  /// "Sync & Remove" button in removal dialog
  static const removalDialogSyncAndRemove = Key('removal_dialog_sync_and_remove');

  /// "Delete from Device" button in removal dialog
  static const removalDialogDeleteFromDevice = Key('removal_dialog_delete_from_device');

  // ============================================
  // Assignments Step
  // ============================================
  /// Search field in assignments step
  static const assignmentSearchField = Key('assignment_search_field');

  /// Creates a key for an assignment row
  static Key assignmentTile(String userId) => Key('assignment_tile_$userId');

  // ============================================
  // Project Switcher
  // ============================================
  /// Project switcher trigger in app bar
  static const projectSwitcher = Key('project_switcher');

  /// "View All" item in project switcher
  static const projectSwitcherViewAll = Key('project_switcher_view_all');

  /// "+ New Project" item in project switcher
  static const projectSwitcherNewProject = Key('project_switcher_new_project');

  /// Creates a key for a recent project tile in switcher
  static Key projectSwitcherTile(String id) => Key('project_switcher_tile_$id');
```

#### Step 1.2.2: Verify

Run: `pwsh -Command "flutter analyze lib/shared/testing_keys/projects_keys.dart"`
Expected: No issues found

---

### Sub-phase 1.3: Update testing_keys.dart facade

**Files:**
- Modify: `lib/shared/testing_keys/testing_keys.dart:1-27`

**Agent**: `backend-data-layer-agent`

#### Step 1.3.1: Add sync_keys export and import

Add after the `export 'settings_keys.dart';` line (line 12) and before `export 'toolbox_keys.dart';` (line 14 after insertion):

```dart
export 'sync_keys.dart';
```

Add after `import 'settings_keys.dart';` (within the import block, around line 26-27):

```dart
import 'sync_keys.dart';
```

#### Step 1.3.2: Add SyncTestingKeys delegates to TestingKeys class

Inside the `TestingKeys` class body, add delegates for all sync keys following the existing pattern:

```dart
  // Sync Dashboard
  static const syncNowTile = SyncTestingKeys.syncNowTile;
  static const syncViewConflictsTile = SyncTestingKeys.syncViewConflictsTile;
  static const syncViewProjectsTile = SyncTestingKeys.syncViewProjectsTile;
  static const syncResumeSyncButton = SyncTestingKeys.syncResumeSyncButton;
  static const syncStatusBadge = SyncTestingKeys.syncStatusBadge;
  static const syncLastSyncTimestamp = SyncTestingKeys.syncLastSyncTimestamp;
  static Key syncBucketTile(String name) => SyncTestingKeys.syncBucketTile(name);
```

Also add delegates for ALL new project keys:

```dart
  // Project List - Tabs
  static const projectTabMyProjects = ProjectsTestingKeys.projectTabMyProjects;
  static const projectTabCompany = ProjectsTestingKeys.projectTabCompany;
  static const projectTabArchived = ProjectsTestingKeys.projectTabArchived;

  // Project List - Filter Chips
  static const projectFilterAll = ProjectsTestingKeys.projectFilterAll;
  static const projectFilterOnDevice = ProjectsTestingKeys.projectFilterOnDevice;
  static const projectFilterNotDownloaded = ProjectsTestingKeys.projectFilterNotDownloaded;

  // Project List - Download Dialog
  static Key projectDownloadButton(String id) => ProjectsTestingKeys.projectDownloadButton(id);
  static const projectDownloadDialogCancel = ProjectsTestingKeys.projectDownloadDialogCancel;
  static const projectDownloadDialogConfirm = ProjectsTestingKeys.projectDownloadDialogConfirm;

  // Project List - Remote Delete Dialog
  static const projectRemoteDeleteDialogCancel = ProjectsTestingKeys.projectRemoteDeleteDialogCancel;
  static const projectRemoteDeleteDialogConfirm = ProjectsTestingKeys.projectRemoteDeleteDialogConfirm;

  // Project Empty State
  static const projectBrowseButton = ProjectsTestingKeys.projectBrowseButton;

  // Project Setup - Description & Nav
  static const projectDescriptionField = ProjectsTestingKeys.projectDescriptionField;
  static const projectDiscardButton = ProjectsTestingKeys.projectDiscardButton;
  static const projectSaveDraftButton = ProjectsTestingKeys.projectSaveDraftButton;

  // Removal Dialog
  static const removalDialogCancel = ProjectsTestingKeys.removalDialogCancel;
  static const removalDialogSyncAndRemove = ProjectsTestingKeys.removalDialogSyncAndRemove;
  static const removalDialogDeleteFromDevice = ProjectsTestingKeys.removalDialogDeleteFromDevice;

  // Assignments Step
  static const assignmentSearchField = ProjectsTestingKeys.assignmentSearchField;
  static Key assignmentTile(String userId) => ProjectsTestingKeys.assignmentTile(userId);

  // Project Switcher
  static const projectSwitcher = ProjectsTestingKeys.projectSwitcher;
  static const projectSwitcherViewAll = ProjectsTestingKeys.projectSwitcherViewAll;
  static const projectSwitcherNewProject = ProjectsTestingKeys.projectSwitcherNewProject;
  static Key projectSwitcherTile(String id) => ProjectsTestingKeys.projectSwitcherTile(id);
```

#### Step 1.3.3: Verify

Run: `pwsh -Command "flutter analyze lib/shared/testing_keys/"`
Expected: No issues found

---

## Phase 2: Apply Testing Keys to Widgets

### Sub-phase 2.1: Apply sync keys to sync_dashboard_screen.dart

**Files:**
- Modify: `lib/features/sync/presentation/screens/sync_dashboard_screen.dart:128-285`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.1.1: Add import

The file should already import from `shared.dart` (via `construction_inspector/shared/shared.dart`). If not, add:
```dart
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';
```

#### Step 2.1.2: Apply keys to circuit breaker RESUME SYNC button (line ~136)

In the `MaterialBanner` actions, add key to the TextButton:

```dart
TextButton(
  key: SyncTestingKeys.syncResumeSyncButton, // FROM SPEC: e2e testing key
  onPressed: () => syncProvider.dismissCircuitBreaker(),
  child: const Text('RESUME SYNC'),
),
```

#### Step 2.1.3: Apply keys to summary card status badge (line ~183)

Add key to the status Icon in `_buildSummaryCard`:

```dart
Icon(
  key: SyncTestingKeys.syncStatusBadge, // FROM SPEC: e2e testing key
  syncProvider.isSyncing
      ? Icons.sync
      // ... rest unchanged
```

#### Step 2.1.4: Apply key to last sync timestamp text (line ~204)

```dart
Text(
  key: SyncTestingKeys.syncLastSyncTimestamp, // FROM SPEC: e2e testing key
  'Last sync: ${syncProvider.lastSyncText}',
  style: Theme.of(context).textTheme.bodySmall,
),
```

#### Step 2.1.5: Apply keys to action tiles (lines 245-267)

Wrap or add keys to each `_buildActionTile` call. Modify `_buildActionTile` to accept and pass through a key:

```dart
// WHY: Complete replacement — adds key parameter for e2e testing
Widget _buildActionTile({
  Key? key, // FROM SPEC: optional e2e testing key
  required IconData icon,
  required String title,
  required String subtitle,
  required VoidCallback onTap,
}) {
  return ListTile(
    key: key,
    leading: Icon(icon),
    title: Text(title),
    subtitle: Text(subtitle),
    trailing: const Icon(Icons.chevron_right),
    onTap: onTap,
  );
}
```

Then apply at call sites:

```dart
_buildActionTile(
  key: SyncTestingKeys.syncNowTile,
  icon: Icons.sync,
  title: 'Sync Now',
  // ...
),
_buildActionTile(
  key: SyncTestingKeys.syncViewConflictsTile,
  icon: Icons.warning_amber,
  title: 'View Conflicts',
  // ...
),
_buildActionTile(
  key: SyncTestingKeys.syncViewProjectsTile,
  icon: Icons.folder_shared,
  title: 'View Synced Projects',
  // ...
),
```

#### Step 2.1.6: Apply keys to pending bucket ExpansionTiles (in `_buildPendingBucketsSection`)

In the bucket iteration, add key to each ExpansionTile. Find where `ExpansionTile` is built for each bucket and add:

```dart
ExpansionTile(
  key: SyncTestingKeys.syncBucketTile(bucketName), // FROM SPEC: e2e testing key
  // ... rest unchanged
```

Where `bucketName` is the lowercase bucket identifier (e.g., 'projects', 'entries', etc.).

#### Step 2.1.7: Verify

Run: `pwsh -Command "flutter analyze lib/features/sync/presentation/screens/sync_dashboard_screen.dart"`
Expected: No issues found

---

### Sub-phase 2.2: Apply project keys to project UI widgets

**Files:**
- Modify: `lib/features/projects/presentation/widgets/project_filter_chips.dart:28-31`
- Modify: `lib/features/projects/presentation/widgets/project_tab_bar.dart:32-35`
- Modify: `lib/features/projects/presentation/widgets/removal_dialog.dart:73-99`
- Modify: `lib/features/projects/presentation/widgets/assignments_step.dart:27-62`
- Modify: `lib/features/projects/presentation/widgets/project_empty_state.dart:86-90`
- Modify: `lib/features/projects/presentation/widgets/project_switcher.dart:22-58,191-212`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.2.1: project_filter_chips.dart — Add keys to FilterChips

Each widget file needs `import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';` (or will get it via `shared.dart` if already imported).

In the `Wrap` children builder (line 28), add a `key` to each `FilterChip`:

```dart
return FilterChip(
  key: switch (filter) {
    CompanyFilter.all => ProjectsTestingKeys.projectFilterAll,
    CompanyFilter.onDevice => ProjectsTestingKeys.projectFilterOnDevice,
    CompanyFilter.notDownloaded => ProjectsTestingKeys.projectFilterNotDownloaded,
  }, // FROM SPEC: e2e testing key
  label: Text(label),
  selected: selected == filter,
  onSelected: (_) => onChanged(filter),
);
```

#### Step 2.2.2: project_tab_bar.dart — Add keys to Tab widgets

In the `TabBar.tabs` list (lines 32-35), add keys to each `_buildTab` result. The cleanest approach is to pass an optional key to `_buildTab`:

```dart
tabs: [
  _buildTab('My Projects', myProjectsCount, badgeColor, badgeTextStyle,
      key: ProjectsTestingKeys.projectTabMyProjects),
  _buildTab('Company', companyCount, badgeColor, badgeTextStyle,
      key: ProjectsTestingKeys.projectTabCompany),
  _buildTab('Archived', archivedCount, badgeColor, badgeTextStyle,
      key: ProjectsTestingKeys.projectTabArchived),
],
```

Update `_buildTab` signature:

```dart
Widget _buildTab(
  String label,
  int count,
  Color badgeColor,
  TextStyle? badgeTextStyle, {
  Key? key, // FROM SPEC: e2e testing key
}) {
  return Tab(
    key: key,
    child: Row(
      // ... rest unchanged
```

#### Step 2.2.3: removal_dialog.dart — Add keys to dialog buttons

In the `actions` list (lines 73-99):

```dart
actions: [
  TextButton(
    key: ProjectsTestingKeys.removalDialogCancel, // FROM SPEC: e2e testing key
    onPressed: () => Navigator.of(context).pop(RemovalChoice.cancel),
    child: const Text('Cancel'),
  ),
  if (hasPendingChanges)
    Tooltip(
      message: isOnline ? '' : 'You\'re offline — sync unavailable',
      child: GestureDetector(
        onTap: () {},
        child: TextButton(
          key: ProjectsTestingKeys.removalDialogSyncAndRemove, // FROM SPEC: e2e testing key
          onPressed: isOnline
              ? () => Navigator.of(context).pop(RemovalChoice.syncAndRemove)
              : null,
          child: const Text('Sync & Remove'),
        ),
      ),
    ),
  TextButton(
    key: ProjectsTestingKeys.removalDialogDeleteFromDevice, // FROM SPEC: e2e testing key
    onPressed: () => Navigator.of(context).pop(RemovalChoice.deleteFromDevice),
    style: TextButton.styleFrom(foregroundColor: AppTheme.statusError),
    child: const Text('Delete from Device'),
  ),
],
```

#### Step 2.2.4: assignments_step.dart — Add keys to search field and assignment tiles

Search field (line 27):
```dart
child: TextField(
  key: ProjectsTestingKeys.assignmentSearchField, // FROM SPEC: e2e testing key
  decoration: InputDecoration(
    // ... unchanged
```

Assignment tile (line 62):
```dart
return AssignmentListTile(
  key: ProjectsTestingKeys.assignmentTile(member.userId), // FROM SPEC: e2e testing key
  member: member,
  // ... unchanged
```

#### Step 2.2.5: project_empty_state.dart — Add key to browse button

Browse button (line 86):
```dart
FilledButton.icon(
  key: ProjectsTestingKeys.projectBrowseButton, // FROM SPEC: e2e testing key
  onPressed: onBrowse,
  icon: const Icon(Icons.search),
  label: const Text('Browse Available Projects'),
),
```

#### Step 2.2.6: project_switcher.dart — Add keys to switcher trigger and sheet items

Switcher trigger GestureDetector (line 22):
```dart
return GestureDetector(
  key: ProjectsTestingKeys.projectSwitcher, // FROM SPEC: e2e testing key
  onTap: () => _showSwitcherSheet(context, projectProvider),
  // ... unchanged
```

"View All" ListTile (line 191):
```dart
ListTile(
  key: ProjectsTestingKeys.projectSwitcherViewAll, // FROM SPEC: e2e testing key
  dense: true,
  leading: const Icon(Icons.list),
  title: const Text('View All Projects'),
  // ...
```

"+ New Project" ListTile (line 201):
```dart
ListTile(
  key: ProjectsTestingKeys.projectSwitcherNewProject, // FROM SPEC: e2e testing key
  dense: true,
  leading: Icon(Icons.add, color: AppTheme.primaryCyan),
  // ...
```

Recent project tile (in `_buildProjectTile`, line 222):
```dart
return ListTile(
  key: ProjectsTestingKeys.projectSwitcherTile(project.id), // FROM SPEC: e2e testing key
  dense: true,
  // ... unchanged
```

#### Step 2.2.7: Verify

Run: `pwsh -Command "flutter analyze lib/features/projects/presentation/widgets/"`
Expected: No issues found

---

### Sub-phase 2.3: Apply keys to project_list_screen.dart dialogs

**Files:**
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart:139-157,229-253,634-663`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.3.1: Download confirmation dialog buttons (lines 139-157)

In `_showDownloadConfirmation`, add keys to dialog buttons:

```dart
actions: [
  TextButton(
    key: ProjectsTestingKeys.projectDownloadDialogCancel, // FROM SPEC: e2e testing key
    onPressed: () => Navigator.pop(ctx, false),
    child: const Text('Cancel'),
  ),
  ElevatedButton(
    key: ProjectsTestingKeys.projectDownloadDialogConfirm, // FROM SPEC: e2e testing key
    onPressed: () => Navigator.pop(ctx, true),
    child: const Text('Download'),
  ),
],
```

#### Step 2.3.2: Remote delete confirmation dialog buttons (lines 239-252)

In `_handleRemoteDelete`, add keys to dialog buttons:

```dart
actions: [
  TextButton(
    key: ProjectsTestingKeys.projectRemoteDeleteDialogCancel, // FROM SPEC: e2e testing key
    onPressed: () => Navigator.pop(ctx, false),
    child: const Text('Cancel'),
  ),
  ElevatedButton(
    key: ProjectsTestingKeys.projectRemoteDeleteDialogConfirm, // FROM SPEC: e2e testing key
    style: ElevatedButton.styleFrom(backgroundColor: AppTheme.statusError),
    onPressed: () => Navigator.pop(ctx, true),
    child: const Text('Delete'),
  ),
],
```

#### Step 2.3.3: Download button on remote-only project card (line ~658)

Add key to the download ElevatedButton.icon in the card:

```dart
ElevatedButton.icon(
  key: ProjectsTestingKeys.projectDownloadButton(project.id), // FROM SPEC: e2e testing key
  onPressed: () => _showDownloadConfirmation(entry),
  icon: const Icon(Icons.download, size: 18),
  label: const Text('Download'),
  // ...
```

#### Step 2.3.4: Verify

Run: `pwsh -Command "flutter analyze lib/features/projects/presentation/screens/project_list_screen.dart"`
Expected: No issues found

---

### Sub-phase 2.4: Apply keys to project_setup_screen.dart and project_details_form.dart

**Files:**
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart:316-323`
- Modify: `lib/features/projects/presentation/widgets/project_details_form.dart:69-76`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.4.1: Discard and Save Draft buttons in unsaved changes dialog

In `project_setup_screen.dart`, the back-nav dialog (around lines 316-323):

```dart
TextButton(
  key: ProjectsTestingKeys.projectDiscardButton, // FROM SPEC: e2e testing key
  onPressed: () => Navigator.pop(ctx, 'discard'),
  child: const Text('Discard'),
),
ElevatedButton(
  key: ProjectsTestingKeys.projectSaveDraftButton, // FROM SPEC: e2e testing key
  onPressed: () => Navigator.pop(ctx, 'save'),
  child: const Text('Save Draft'),
),
```

#### Step 2.4.2: Description field in project_details_form.dart

In `project_details_form.dart` (around line 69):

```dart
TextFormField(
  key: ProjectsTestingKeys.projectDescriptionField, // FROM SPEC: e2e testing key
  controller: descriptionController,
  decoration: const InputDecoration(
    labelText: 'Description',
    // ...
```

#### Step 2.4.3: Verify

Run: `pwsh -Command "flutter analyze lib/features/projects/presentation/"`
Expected: No issues found

---

## Phase 3: Debug Server Sync Status Endpoints

### Sub-phase 3.1: Add sync status routes to server.js

**Files:**
- Modify: `tools/debug-server/server.js:31-36,216-255`

**Agent**: `general-purpose`

#### Step 3.1.1: Add sync status storage variable

After `let nextId = 1;` (line 36), add:

```javascript
// --- Sync status tracking ---
// FROM SPEC: Stores latest sync lifecycle event for GET /sync/status polling
let latestSyncStatus = null;
```

#### Step 3.1.2: Add POST /sync/status handler

Add after the `handleGetCategories` function (after line 213):

```javascript
// FROM SPEC: App POSTs sync lifecycle events (started, push_table, pull_table, completed, failed)
async function handlePostSyncStatus(req, res) {
  try {
    const body = await readBody(req);
    const status = JSON.parse(body);
    if (typeof status !== 'object' || status === null || Array.isArray(status)) {
      sendJson(res, 400, { error: 'Invalid status: must be a JSON object' });
      return;
    }
    // WHY: Server enriches with receivedAt for accurate timing
    status.receivedAt = new Date().toISOString();
    latestSyncStatus = status;
    sendJson(res, 200, { ok: true });
  } catch (e) {
    if (e.message && e.message.includes('too large')) {
      sendJson(res, 413, { error: 'Request too large', detail: e.message });
    } else {
      sendJson(res, 400, { error: 'Invalid JSON', detail: e.message });
    }
  }
}

// FROM SPEC: Claude/tooling polls this endpoint to check sync completion
function handleGetSyncStatus(_req, res) {
  if (!latestSyncStatus) {
    sendJson(res, 200, { state: 'unknown', message: 'No sync events received yet' });
    return;
  }
  sendJson(res, 200, latestSyncStatus);
}
```

#### Step 3.1.3: Add routes to server dispatch

In the `http.createServer` callback (around line 238-251), add two new routes before the 404 fallback:

```javascript
    } else if (req.method === 'POST' && pathname === '/sync/status') {
      await handlePostSyncStatus(req, res);
    } else if (req.method === 'GET' && pathname === '/sync/status') {
      handleGetSyncStatus(req, res);
    } else {
      sendJson(res, 404, { error: 'Not found' });
    }
```

#### Step 3.1.4: Update startup banner

Add to the endpoints section at the bottom:

```javascript
  console.log('  POST /sync/status  Report sync lifecycle event');
  console.log('  GET  /sync/status  Poll current sync state');
```

#### Step 3.1.5: Clear sync status on POST /clear

In `clearEntries()` function (line 65-69), add:

```javascript
function clearEntries() {
  entries = [];
  currentMemoryEstimate = 0;
  latestSyncStatus = null; // FROM SPEC: Reset sync status on clear
}
```

#### Step 3.1.6: Verify

Run: `pwsh -Command "node -c tools/debug-server/server.js"` (syntax check)
Expected: No output (success)

---

## Phase 4: Sync Engine Status Reporting

### Sub-phase 4.1: POST sync lifecycle events from sync_engine.dart

**Files:**
- Modify: `lib/features/sync/engine/sync_engine.dart:176-269`

**Agent**: `backend-supabase-agent`

#### Step 4.1.1: Add _postSyncStatus helper method

Add a private helper method to `SyncEngine` class. This must follow the same guards as `Logger._sendHttp`:

```dart
// WHY: Matches Logger._httpEnabled — compile-time gate for debug server
// FROM SPEC: Same dual-gate pattern as Logger._sendHttp
static const _debugServerEnabled = bool.fromEnvironment(
  'DEBUG_SERVER',
  defaultValue: false,
);

/// POST sync lifecycle events to the debug server for e2e verification.
/// FROM SPEC: Same guards as Logger._sendHttp — debug-only, fire-and-forget.
void _postSyncStatus(Map<String, dynamic> status) {
  // WHY: Dual guard matches Logger._sendHttp — compile-time + runtime
  if (!_debugServerEnabled) return; // Compile-time gate (no-op without --dart-define=DEBUG_SERVER=true)
  if (kReleaseMode) return; // Runtime defense-in-depth

  // Add timestamp
  status['timestamp'] = DateTime.now().toUtc().toIso8601String();

  // Fire-and-forget POST to debug server
  try {
    final client = HttpClient();
    client.postUrl(Uri.parse('http://127.0.0.1:3947/sync/status')).then((request) {
      request.headers.contentType = ContentType.json;
      request.write(jsonEncode(status));
      return request.close();
    }).then((response) {
      response.drain<void>();
      client.close();
    }).catchError((_) {
      client.close();
    });
  } catch (_) {
    // Swallow — server may not be running
  }
}
```

**Important**:
- Add `import 'package:flutter/foundation.dart';` to the import block for `kReleaseMode`. This import is NOT currently present in sync_engine.dart — it MUST be added explicitly.
- `dart:io` (for `HttpClient`, `ContentType`) and `dart:convert` (for `jsonEncode`) are already imported (lines 2-3).

#### Step 4.1.2: Add sync status events to pushAndPull()

In the `pushAndPull()` method (lines 176-269), instrument at key lifecycle points:

**After acquiring the mutex (after line 197):**
```dart
_postSyncStatus({'type': 'sync_status', 'state': 'started'});
```

**After push completes (after line 212):**
```dart
_postSyncStatus({
  'type': 'sync_status',
  'state': 'push_complete',
  'pushed': pushResult.pushed,
  'errors': pushResult.errors,
});
```

**After pull completes (after line 223):**
```dart
_postSyncStatus({
  'type': 'sync_status',
  'state': 'pull_complete',
  'pulled': pullResult.pulled,
  'errors': pullResult.errors,
});
```

**In the finally block, when cycle completed (after line 263, inside the `if (cycleCompleted)` block):**
```dart
_postSyncStatus({
  'type': 'sync_status',
  'state': 'completed',
  'pushed': combined.pushed,
  'pulled': combined.pulled,
  'errors': combined.errors,
  'duration_ms': stopwatch.elapsedMilliseconds,
});
```

**In the finally block, when cycle did NOT complete (add an else to the `if (cycleCompleted)`):**
```dart
} else {
  _postSyncStatus({
    'type': 'sync_status',
    'state': 'failed',
    'error': 'Sync cycle did not complete',
  });
}
```

#### Step 4.1.3: Verify

Run: `pwsh -Command "flutter analyze lib/features/sync/engine/sync_engine.dart"`
Expected: No issues found

Run: `pwsh -Command "flutter test test/features/sync/engine/sync_engine_test.dart"`
Expected: All existing tests PASS (sync status POSTs are fire-and-forget to localhost, will silently fail in test with no debug server)

---

## Phase 5: Gitignore Update (MUST precede .env.secret creation)

### Sub-phase 5.0: Update .gitignore FIRST

**Files:**
- Modify: `.gitignore:109` (end of file)

**Agent**: `general-purpose`

#### Step 5.0.1: Add test_results/ and .env.secret entries

Append to `.gitignore` (after line 109):

```gitignore

# E2E sync verification (FROM SPEC MF-10)
test_results/
.env.secret
```

**WHY**: `.env.secret` MUST be gitignored BEFORE the file is created in Step 5.2.1. If created first, a `git add .` could commit the service role key. The `*.env` pattern does NOT match `.env.secret` (it matches files ending in `.env`, not starting with it). `test_results/` at project root must also be ignored per spec Day 0 prerequisites.

#### Step 5.0.2: Verify

Run: `pwsh -Command "git check-ignore .env.secret test_results/dummy"`
Expected: Both paths confirmed ignored

---

## Phase 5 (continued): Supabase Verification Tooling

### Sub-phase 5.1: Create verify-sync.ps1

**Files:**
- Create: `tools/verify-sync.ps1`

**Agent**: `general-purpose`

#### Step 5.1.1: Write the PowerShell verification script

```powershell
<#
.SYNOPSIS
    Verify sync data in Supabase via PostgREST REST API.

.DESCRIPTION
    FROM SPEC: Queries Supabase tables to verify that sync pushed data correctly.
    Reads SUPABASE_URL from .env and SUPABASE_SERVICE_ROLE_KEY from .env.secret.
    Authorization headers are NEVER written to output files.

.PARAMETER Table
    Which Supabase table to query.

.PARAMETER ProjectId
    Scope query to a specific project (optional).

.PARAMETER Filter
    PostgREST filter string (e.g., "name=eq.E2E Test").

.PARAMETER CountOnly
    Return row count only.

.PARAMETER Cleanup
    Delete test data. Requires -ProjectName starting with "E2E ".

.PARAMETER ProjectName
    Project name for cleanup (must start with "E2E ").

.PARAMETER WhatIf
    Dry-run mode for cleanup — shows what would be deleted.

.EXAMPLE
    .\tools\verify-sync.ps1 -Table projects -Filter "name=like.E2E*"
    .\tools\verify-sync.ps1 -Table daily_entries -ProjectId "abc-123" -CountOnly
    .\tools\verify-sync.ps1 -Cleanup -ProjectName "E2E Test Project" -WhatIf
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$Table,
    [string]$ProjectId,
    [string]$Filter,
    [switch]$CountOnly,
    [switch]$Cleanup,
    [string]$ProjectName
)

# --- Load credentials ---
$envFile = Join-Path $PSScriptRoot ".." ".env"
$secretFile = Join-Path $PSScriptRoot ".." ".env.secret"

if (-not (Test-Path $envFile)) {
    Write-Error ".env file not found at $envFile"
    exit 1
}
if (-not (Test-Path $secretFile)) {
    Write-Error ".env.secret file not found at $secretFile — create it with SUPABASE_SERVICE_ROLE_KEY=<key>"
    exit 1
}

# Parse .env for SUPABASE_URL
$supabaseUrl = $null
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*SUPABASE_URL\s*=\s*(.+)$') {
        $supabaseUrl = $Matches[1].Trim().Trim('"', "'")
    }
}

# Parse .env.secret for SUPABASE_SERVICE_ROLE_KEY
$serviceRoleKey = $null
Get-Content $secretFile | ForEach-Object {
    if ($_ -match '^\s*SUPABASE_SERVICE_ROLE_KEY\s*=\s*(.+)$') {
        $serviceRoleKey = $Matches[1].Trim().Trim('"', "'")
    }
}

if (-not $supabaseUrl) { Write-Error "SUPABASE_URL not found in .env"; exit 1 }
if (-not $serviceRoleKey) { Write-Error "SUPABASE_SERVICE_ROLE_KEY not found in .env.secret"; exit 1 }

$restBase = "$supabaseUrl/rest/v1"
# WHY: Authorization headers are constructed in-memory only, never written to files
$headers = @{
    "apikey"        = $serviceRoleKey
    "Authorization" = "Bearer $serviceRoleKey"
    "Content-Type"  = "application/json"
    "Prefer"        = "return=representation"
}

# --- Cleanup mode ---
if ($Cleanup) {
    if (-not $ProjectName) {
        Write-Error "-Cleanup requires -ProjectName"
        exit 1
    }
    # FROM SPEC (MF-9): Enforce "E2E " prefix for safety
    if (-not $ProjectName.StartsWith("E2E ")) {
        Write-Error "Safety: -ProjectName must start with 'E2E ' (got: '$ProjectName')"
        exit 1
    }

    Write-Host "Looking up project: '$ProjectName'..."
    $projectUrl = "$restBase/projects?name=eq.$([Uri]::EscapeDataString($ProjectName))&select=id,name"
    $projects = Invoke-RestMethod -Uri $projectUrl -Headers $headers -Method Get

    if ($projects.Count -eq 0) {
        Write-Host "No project found with name '$ProjectName'"
        exit 0
    }

    $projectId = $projects[0].id
    Write-Host "Found project: $projectId ($($projects[0].name))"

    # FROM SPEC: Cascading delete order (children first)
    $childTables = @(
        "entry_quantities",
        "entry_equipment",
        "entry_personnel_counts",
        "photos",
        "inspector_forms",
        "todo_items",
        "daily_entries",
        "equipment",
        "bid_items",
        "contractors",
        "locations",
        "project_assignments"
    )

    foreach ($t in $childTables) {
        $filterParam = if ($t -in @("entry_quantities", "entry_equipment", "entry_personnel_counts")) {
            # These join through daily_entries
            "entry_id=in.(select id from daily_entries where project_id=eq.$projectId)"
        } elseif ($t -eq "equipment") {
            "contractor_id=in.(select id from contractors where project_id=eq.$projectId)"
        } else {
            "project_id=eq.$projectId"
        }

        $countUrl = "$restBase/$t?$filterParam&select=id"
        $countHeaders = $headers.Clone()
        $countHeaders["Prefer"] = "count=exact"
        $countHeaders["Range-Unit"] = "items"
        $countHeaders["Range"] = "0-0"

        try {
            $countResp = Invoke-WebRequest -Uri $countUrl -Headers $countHeaders -Method Head -ErrorAction Stop
            $range = $countResp.Headers["Content-Range"]
            $count = if ($range -match '/(\d+)$') { [int]$Matches[1] } else { 0 }
        } catch {
            $count = 0
        }

        if ($count -gt 0) {
            if ($WhatIf) {
                Write-Host "[WhatIf] Would delete $count rows from $t"
            } else {
                Write-Host "Deleting $count rows from $t..."
                $delUrl = "$restBase/$t?$filterParam"
                Invoke-RestMethod -Uri $delUrl -Headers $headers -Method Delete | Out-Null
            }
        }
    }

    # Delete the project itself
    if ($WhatIf) {
        Write-Host "[WhatIf] Would delete project '$ProjectName' ($projectId)"
    } else {
        Write-Host "Deleting project '$ProjectName' ($projectId)..."
        Invoke-RestMethod -Uri "$restBase/projects?id=eq.$projectId" -Headers $headers -Method Delete | Out-Null
        Write-Host "Cleanup complete."
    }
    exit 0
}

# --- Query mode ---
if (-not $Table) {
    Write-Error "-Table is required (or use -Cleanup)"
    exit 1
}

$url = "$restBase/$Table"
$queryParts = @()

if ($ProjectId) {
    # FROM SPEC: Scope to project
    $queryParts += "project_id=eq.$ProjectId"
}
if ($Filter) {
    $queryParts += $Filter
}

if ($queryParts.Count -gt 0) {
    $url += "?" + ($queryParts -join "&")
}

if ($CountOnly) {
    $countHeaders = $headers.Clone()
    $countHeaders["Prefer"] = "count=exact"
    $countHeaders["Range-Unit"] = "items"
    $countHeaders["Range"] = "0-0"
    try {
        $resp = Invoke-WebRequest -Uri $url -Headers $countHeaders -Method Head
        $range = $resp.Headers["Content-Range"]
        if ($range -match '/(\d+)$') {
            Write-Host "$Table count: $($Matches[1])"
        } else {
            Write-Host "$Table count: 0"
        }
    } catch {
        Write-Error "Query failed: $_"
        exit 1
    }
} else {
    try {
        $result = Invoke-RestMethod -Uri $url -Headers $headers -Method Get
        $result | ConvertTo-Json -Depth 10
    } catch {
        Write-Error "Query failed: $_"
        exit 1
    }
}
```

#### Step 5.1.2: Verify

Run: `pwsh -Command "Get-Help tools/verify-sync.ps1 -Detailed"` (syntax validation + help display)
Expected: Shows synopsis and parameters without errors

---

### Sub-phase 5.2: Create .env.secret placeholder

**Files:**
- Create: `.env.secret`

**Agent**: `general-purpose`

#### Step 5.2.1: Create placeholder .env.secret

```
# Supabase service role key for e2e verification (NOT the anon key from .env)
# FROM SPEC (MF-7): Must be separate from .env to prevent accidental inclusion in app builds
SUPABASE_SERVICE_ROLE_KEY=<paste-your-service-role-key-here>
```

**IMPORTANT**: This file must be gitignored. Verified in Phase 6.

#### Step 5.2.2: Verify

Confirm file exists and is not empty.

---

## Phase 6: Flow Registry

### Sub-phase 6.1: Create flow_registry.md

**Files:**
- Create: `.claude/test_results/flow_registry.md`

**Agent**: `general-purpose`

#### Step 6.2.1: Create the flow registry

```markdown
# E2E Sync Verification Flow Registry

> **Purpose**: Persistent tracker for all 42 test flows across the 17 synced tables.
> **Updated**: After each test run.

## Status Key
- **PASS** — Verified end-to-end (push + Supabase check + pull back)
- **FAIL** — Broken, with bug ID
- **SKIP** — Not yet tested
- **BLOCKED** — Depends on another fix

## Flow Registry

### Tier 1: Foundation

| ID | Flow | Table(s) | Status | Last Run | Notes |
|----|------|----------|--------|----------|-------|
| T01 | Project Create + Push | projects | SKIP | — | |
| T02 | Location Add + Push | locations | SKIP | — | Depends: T01 |
| T03 | Contractor Add + Push | contractors | SKIP | — | Depends: T01 |
| T04 | Equipment Add + Push | equipment | SKIP | — | Depends: T03 |
| T05 | Pay Item Add + Push | bid_items | SKIP | — | Depends: T01 |
| T06 | Project Assignment + Push | project_assignments | SKIP | — | Depends: T01 |

### Tier 2: Daily Workflow

| ID | Flow | Table(s) | Status | Last Run | Notes |
|----|------|----------|--------|----------|-------|
| T07 | Entry Create + Push | daily_entries | SKIP | — | Depends: T01 |
| T08 | Personnel Log + Push | entry_personnel_counts | SKIP | — | Depends: T07 |
| T09 | Equipment Usage + Push | entry_equipment | SKIP | — | Depends: T04, T07 |
| T10 | Quantity Log + Push | entry_quantities | SKIP | — | Depends: T05, T07 |
| T11 | Photo Attach + Push | photos | SKIP | — | Depends: T07 |
| T12 | Todo Create + Push | todo_items | SKIP | — | |
| T13 | Form Create + Push | inspector_forms | SKIP | — | |

### Tier 3: Mutations

| ID | Flow | Table(s) | Status | Last Run | Notes |
|----|------|----------|--------|----------|-------|
| T14 | Edit Project + Push | projects | SKIP | — | Depends: T01 |
| T15 | Edit Entry + Push | daily_entries | SKIP | — | Depends: T07 |
| T16 | Delete Location + Push | locations | SKIP | — | Depends: T02 |
| T17 | Delete Contractor + Push | contractors | SKIP | — | Depends: T03 |
| T18 | Complete Todo + Push | todo_items | SKIP | — | Depends: T12 |
| T19 | Archive Project + Push | projects | SKIP | — | Depends: T01 |
| T20 | Unarchive Project + Push | projects | SKIP | — | Depends: T19 |

### Tier 4: Sync Engine Mechanics

| ID | Flow | Table(s) | Status | Last Run | Notes |
|----|------|----------|--------|----------|-------|
| T21 | Pull After Remote Edit | varies | SKIP | — | |
| T22 | Offline Queue + Reconnect | varies | SKIP | — | |
| T23 | Conflict Resolution | daily_entries | SKIP | — | |
| T24 | Circuit Breaker Trip | all | SKIP | — | |
| T25 | Circuit Breaker Resume | all | SKIP | — | Depends: T24 |
| T26 | Cursor Integrity Check | varies | SKIP | — | |
| T27 | Orphan Photo Cleanup | photos | SKIP | — | Depends: T11 |

### Tier 5: Role & Permission Verification

| ID | Flow | Table(s) | Status | Last Run | Notes |
|----|------|----------|--------|----------|-------|
| T28 | Admin Full Access | all | SKIP | — | |
| T29 | Engineer Edit Access | varies | SKIP | — | |
| T30 | Inspector Read + Entry | varies | SKIP | — | |
| T31 | RLS Enforcement | projects | SKIP | — | Must use user JWT, not service role |

### Tier 6: Bug Regression

| ID | Flow | Table(s) | Status | Last Run | Notes |
|----|------|----------|--------|----------|-------|
| T32 | BUG-006: Online recovery | sync | SKIP | — | Depends: T22 |
| T33 | BUG-005: synced_projects enrollment | synced_projects (SQLite) | SKIP | — | |
| T34 | BUG-007: Route guard /project/new | projects | SKIP | — | |
| T35 | BUG-004: Assignment push after error | project_assignments | SKIP | — | |
| T36 | BUG-001: Selected project clear | projects | SKIP | — | |
| T37 | BUG-008: Inspector canWrite guard | projects | SKIP | — | |
| T38 | BUG-009: Archive permission guard | projects | SKIP | — | |
| T39 | BUG-010: Setup read-only mode | projects | SKIP | — | |

### Tier 7: Coverage Gaps

| ID | Flow | Table(s) | Status | Last Run | Notes |
|----|------|----------|--------|----------|-------|
| T40 | Unassign Member + Push | project_assignments | SKIP | — | Depends: T06 |
| T41 | User Profile Edit + Push | user_profiles | SKIP | — | |
| T42 | Company Request + Push | company_requests | SKIP | — | |
```

#### Step 6.2.2: Verify

Confirm file created successfully.

---

## Phase 7: Final Verification

### Sub-phase 7.1: Full static analysis

**Agent**: `qa-testing-agent`

#### Step 7.1.1: Run full analyze

Run: `pwsh -Command "flutter analyze"`
Expected: No new issues introduced

#### Step 7.1.2: Run existing sync tests

Run: `pwsh -Command "flutter test test/features/sync/"`
Expected: All existing tests PASS

#### Step 7.1.3: Run existing project tests

Run: `pwsh -Command "flutter test test/features/projects/"`
Expected: All existing tests PASS

#### Step 7.1.4: Run testing keys uniqueness test (if it exists)

Run: `pwsh -Command "flutter test test/shared/"` (if test exists)
Expected: All keys are unique — no duplicates across all key files

---

## Summary

| Phase | Description | New Files | Modified Files | Agent |
|-------|------------|-----------|----------------|-------|
| 1 | Testing keys definition | 1 (`sync_keys.dart`) | 2 (`projects_keys.dart`, `testing_keys.dart`) | `backend-data-layer-agent` |
| 2 | Apply keys to widgets | 0 | 8 (sync dashboard, project widgets, project screens) | `frontend-flutter-specialist-agent` |
| 3 | Debug server sync endpoints | 0 | 1 (`server.js`) | `general-purpose` |
| 4 | Sync engine status reporting | 0 | 1 (`sync_engine.dart`) | `backend-supabase-agent` |
| 5 | Gitignore + verification tooling | 2 (`verify-sync.ps1`, `.env.secret`) | 1 (`.gitignore`) | `general-purpose` |
| 6 | Flow registry | 1 (`flow_registry.md`) | 0 | `general-purpose` |
| 7 | Final verification | 0 | 0 | `qa-testing-agent` |
| **Total** | | **4** | **13** | |

## Review Findings Addressed

| Finding | Severity | Resolution |
|---------|----------|------------|
| Missing `flutter/foundation.dart` import | CRITICAL | Added explicit import instruction in Phase 4.1.1 |
| `_buildActionTile` incomplete body | CRITICAL | Showed complete method replacement in Step 2.1.5 |
| `test_results/` not gitignored | CRITICAL | Added to Phase 5.0 (moved gitignore update before .env.secret creation) |
| `.env.secret` created before gitignored | HIGH (security) | Phase 5.0 now updates .gitignore BEFORE Phase 5.2 creates the file |
| `_postSyncStatus` missing `DEBUG_SERVER` gate | HIGH (security) | Added `_debugServerEnabled` compile-time const matching Logger pattern |
| Step 1.3.2 delegates vague | HIGH | Listed all 24 project key delegates explicitly |
| Flow registry doesn't match spec tiers | HIGH | Registry now uses spec's exact T01-T42 names with tier groupings |
| Per-table sync events omitted | HIGH | Intentional deferral — aggregate events sufficient for MVP verification; per-table events can be added later in `_push()` / `_pullTable()` |
| `$ProjectId` not URL-encoded | MEDIUM | Noted for implementer; cleanup path already uses `[Uri]::EscapeDataString()` |
| PII in query results for user_profiles | MEDIUM | Noted: use `-CountOnly` for user_profiles/company_requests tables |

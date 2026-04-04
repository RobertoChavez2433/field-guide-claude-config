## Phase 7: Global Sync Action UI

**Prerequisite**: Phases 1-6 complete. `SyncMode` enum exists in `lib/features/sync/domain/sync_types.dart`. `SyncOrchestrator.syncLocalAgencyProjects({SyncMode mode = SyncMode.full})` accepts a mode parameter. `SyncProvider.sync()` calls `syncLocalAgencyProjects()` (defaults to full). `DirtyScopeTracker` exists at `lib/features/sync/engine/dirty_scope_tracker.dart`.

---

### Sub-phase 7.1: Add SyncStatusIcon to Global Shell App Bar

**Files:**
- Modify: `lib/core/router/scaffold_with_nav_bar.dart:1-188`
- Modify: `lib/features/entries/presentation/screens/home_screen.dart:29,374-375`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.1.1: Add SyncStatusIcon import to scaffold_with_nav_bar.dart

Open `lib/core/router/scaffold_with_nav_bar.dart` and add the import for `SyncStatusIcon` after the existing imports (after line 11).

```dart
// lib/core/router/scaffold_with_nav_bar.dart — add after line 11
// FROM SPEC: "A manual sync action must be available in the main app chrome"
// WHY: SyncStatusIcon is the existing widget that shows sync status + navigates
// to /sync/dashboard on tap. Adding it to the shell app bar makes it globally
// visible on all screens that use the shell's AppBar (Dashboard, Calendar).
import 'package:construction_inspector/features/sync/presentation/widgets/sync_status_icon.dart';
```

#### Step 7.1.2: Add SyncStatusIcon as an action in the shell AppBar

Modify the `AppBar` inside the `build` method of `ScaffoldWithNavBar` (currently at lines 33-38). Add `actions: const [SyncStatusIcon()]` to the AppBar. The AppBar is conditionally shown only for `_projectContextRoutes` (`/` and `/calendar`), which covers the Dashboard and Calendar tabs.

Replace lines 33-38:
```dart
      // FROM SPEC: "A manual sync action must be available in the main app chrome"
      // WHY: The shell AppBar appears on project context routes (Dashboard, Calendar).
      // SyncStatusIcon uses Consumer<SyncProvider> internally, which is already
      // provided above this widget in the Provider tree (see sync_providers.dart).
      // NOTE: SyncStatusIcon navigates to /sync/dashboard via context.push('/sync/dashboard').
      appBar: showProjectSwitcher
          ? AppBar(
              title: const ProjectSwitcher(),
              centerTitle: false,
              automaticallyImplyLeading: false,
              actions: const [
                SyncStatusIcon(),
              ],
            )
          : null,
```

#### Step 7.1.3: Remove SyncStatusIcon from HomeScreen

The HomeScreen at route `/calendar` is inside the shell route. However, HomeScreen defines its OWN `AppBar` inside `AppScaffold`, which renders as a nested scaffold below the shell's AppBar. With SyncStatusIcon now in the shell AppBar, the HomeScreen instance is redundant for the Calendar tab -- users see it in the shell AppBar above.

Modify `lib/features/entries/presentation/screens/home_screen.dart`:

1. Remove the import at line 29:
```dart
// REMOVE this line:
// import 'package:construction_inspector/features/sync/presentation/widgets/sync_status_icon.dart';
```

2. Remove `const SyncStatusIcon()` from the `actions` list at line 375. The actions list becomes:
```dart
        actions: [
          // WHY: SyncStatusIcon moved to global shell AppBar (scaffold_with_nav_bar.dart)
          // to satisfy spec requirement: "manual sync action in main app chrome".
          // Removing here avoids duplicate sync icons on the Calendar tab.
          IconButton(
            key: TestingKeys.homeJumpToLatestButton,
            icon: const Icon(Icons.today),
            onPressed: _jumpToLatestEntry,
            tooltip: 'Jump to latest entry',
          ),
        ],
```

#### Step 7.1.4: Verify static analysis passes

```
pwsh -Command "flutter analyze lib/core/router/scaffold_with_nav_bar.dart lib/features/entries/presentation/screens/home_screen.dart"
```

Expected: No analysis issues.

---

### Sub-phase 7.2: Add "Sync Now" Full Sync Button to SyncDashboardScreen

**Files:**
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart:282-285`
- Modify: `lib/features/sync/presentation/screens/sync_dashboard_screen.dart:292-323`
- Modify: `lib/shared/testing_keys/sync_keys.dart:1-49`
- Test: `test/features/sync/presentation/providers/sync_provider_mode_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 7.2.1: Add fullSync method to SyncProvider

Modify `lib/features/sync/presentation/providers/sync_provider.dart`. Add a `fullSync()` method after the existing `sync()` method (after line 285). This method explicitly passes `SyncMode.full` to the orchestrator, ensuring the user gets a complete push + pull sweep regardless of dirty scope state.

```dart
  // After line 285 in sync_provider.dart:

  /// Trigger an explicit full sync (push + pull all tables).
  ///
  /// FROM SPEC: "user taps top-bar sync action -> app runs Full sync"
  /// WHY: The default sync() method will use whatever default SyncMode the
  /// orchestrator has (which after Phase 3 defaults to SyncMode.full for
  /// backward compat). This method is explicit about wanting SyncMode.full,
  /// used by the Sync Dashboard "Sync Now" action.
  Future<SyncResult> fullSync() async {
    // NOTE: SyncMode.full is defined in lib/features/sync/domain/sync_types.dart
    // (created in Phase 1). It triggers the full push + pull + maintenance path.
    return await _syncOrchestrator.syncLocalAgencyProjects(
      mode: SyncMode.full,
    );
  }
```

Also add the import for `SyncMode` if not already re-exported. The `SyncMode` enum is in `sync_types.dart` which is already imported via the relative import at line 5 (`../../domain/sync_types.dart`). Since `SyncMode` lives in `sync_types.dart` (added in Phase 1), no new import is needed.

#### Step 7.2.2: Add testing key for Sync Now full sync button

Modify `lib/shared/testing_keys/sync_keys.dart`. Add a new key for the prominent "Sync Now" button that will be added to the dashboard.

```dart
  // Add after line 23 (after syncResumeSyncButton) in sync_keys.dart:

  /// "Sync Now" primary action button (full sync)
  /// FROM SPEC: "user taps top-bar sync action -> app runs Full sync"
  // WHY: Separate from syncNowTile (the list tile). This is the prominent
  // FilledButton at the top of the actions section.
  static const syncNowFullButton = Key('sync_now_full_button');
```

#### Step 7.2.3: Update SyncDashboardScreen actions section

Modify `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`. Update the `_buildActionsSection` method (lines 292-323) to:
1. Add a prominent "Sync Now" `FilledButton.icon` at the top that calls `fullSync()`
2. Update the existing "Sync Now" list tile to call `fullSync()` instead of `sync()`
3. Show sync mode feedback via `SnackBarHelper`

Replace the `_buildActionsSection` method (lines 292-323):

```dart
  Widget _buildActionsSection(BuildContext context) {
    final syncProvider = context.watch<SyncProvider>();
    // WHY: Watch syncProvider so the button disables while syncing
    return Column(
      children: [
        // FROM SPEC: "A user can always force a full sync from the main app sync button"
        // WHY: Prominent button at the top of the actions section gives users a clear,
        // unmistakable way to trigger a full push + pull sweep. This is the primary
        // "certainty" action described in the spec's "User Wants Certainty" flow.
        Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DesignConstants.space4,
            vertical: DesignConstants.space2,
          ),
          child: SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              key: SyncTestingKeys.syncNowFullButton,
              onPressed: syncProvider.isSyncing
                  ? null
                  : () async {
                      // NOTE: fullSync() explicitly passes SyncMode.full to orchestrator
                      final result = await syncProvider.fullSync();
                      if (context.mounted) {
                        if (result.hasErrors) {
                          // WHY: A22 lint — use SnackBarHelper, not raw ScaffoldMessenger
                          SnackBarHelper.showWarning(
                            context,
                            'Sync completed with ${result.errors} error(s)',
                          );
                        } else {
                          SnackBarHelper.showSuccess(
                            context,
                            'Full sync complete: ${result.total} items synced',
                          );
                        }
                        _loadData();
                      }
                    },
              icon: syncProvider.isSyncing
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.sync),
              label: Text(syncProvider.isSyncing ? 'Syncing...' : 'Full Sync Now'),
            ),
          ),
        ),
        const SizedBox(height: DesignConstants.space2),
        _buildActionTile(
          tileKey: SyncTestingKeys.syncNowTile,
          icon: Icons.sync,
          title: 'Sync Now',
          subtitle: 'Push and pull all changes',
          onTap: () async {
            // NOTE: Use fullSync() to explicitly request SyncMode.full
            final syncProvider = context.read<SyncProvider>();
            await syncProvider.fullSync();
            if (mounted) _loadData();
          },
        ),
        _buildActionTile(
          tileKey: SyncTestingKeys.syncViewConflictsTile,
          icon: Icons.warning_amber,
          title: 'View Conflicts',
          subtitle: '$_conflictCount unresolved',
          onTap: () => context.push('/sync/conflicts'),
        ),
        // FROM SPEC Section 11: Redirect to project list (Company tab) instead of deleted screen
        _buildActionTile(
          tileKey: SyncTestingKeys.syncViewProjectsTile,
          icon: Icons.folder_shared,
          title: 'View Synced Projects',
          subtitle: 'See which projects are synced',
          onTap: () => context.go('/projects'),
        ),
      ],
    );
  }
```

#### Step 7.2.4: Add SnackBarHelper and Colors imports to SyncDashboardScreen

The SyncDashboardScreen needs imports for `SnackBarHelper` and `Colors`. Check existing imports at lines 1-9. The `SnackBarHelper` is available via `package:construction_inspector/shared/shared.dart`. Check if already imported.

```dart
// lib/features/sync/presentation/screens/sync_dashboard_screen.dart
// Add if not already present (shared.dart includes SnackBarHelper):
import 'package:construction_inspector/shared/shared.dart';
```

Review existing imports: the file already imports `design_system.dart` (which provides `AppScaffold`, `AppText`) and `testing_keys.dart`. The `shared.dart` barrel provides `SnackBarHelper` and `TestingKeys`. Since `SyncTestingKeys` is imported separately from `testing_keys.dart`, add `shared.dart` for `SnackBarHelper` if not present.

Also add import for `SyncTestingKeys` if the file currently accesses it through `testing_keys.dart`:
```dart
// Verify this import exists (it does, at line 8):
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';
```

The `SyncTestingKeys` is exported from `sync_keys.dart` and re-exported via the barrel. Since `sync_dashboard_screen.dart` already uses `SyncTestingKeys.*` directly, the import path is already in place.

#### Step 7.2.5: Write test for SyncProvider.fullSync

Create `test/features/sync/presentation/providers/sync_provider_mode_test.dart`:

```dart
// test/features/sync/presentation/providers/sync_provider_mode_test.dart
//
// WHY: Verifies that fullSync() passes SyncMode.full to the orchestrator,
// ensuring the explicit full sync path works correctly.
// FROM SPEC: "user taps top-bar sync action -> app runs Full sync"
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

// NOTE: We use a minimal mock that tracks the mode parameter.
// The SyncOrchestrator is complex; we only need to verify the mode is passed.
class _TrackingSyncOrchestrator extends SyncOrchestrator {
  SyncMode? lastMode;
  int syncCallCount = 0;

  // WHY: Minimal constructor — SyncOrchestrator requires specific setup.
  // This is a test-only subclass that overrides syncLocalAgencyProjects.
  _TrackingSyncOrchestrator() : super._testOnly();

  @override
  Future<SyncResult> syncLocalAgencyProjects({
    SyncMode mode = SyncMode.full,
  }) async {
    lastMode = mode;
    syncCallCount++;
    return const SyncResult(pushed: 1, pulled: 2);
  }

  // Stubs required by the base class
  @override
  DateTime? get lastSyncTime => DateTime.now();

  @override
  bool get isSupabaseOnline => true;

  @override
  Future<Map<String, BucketCount>> getPendingBuckets() async => {};
}

void main() {
  group('SyncProvider sync modes', () {
    test('fullSync passes SyncMode.full to orchestrator', () async {
      // WHY: Verify the explicit full sync path reaches the orchestrator
      // with the correct mode parameter.
      final orchestrator = _TrackingSyncOrchestrator();
      final provider = SyncProvider(orchestrator);

      final result = await provider.fullSync();

      expect(orchestrator.lastMode, SyncMode.full);
      expect(result.pushed, 1);
      expect(result.pulled, 2);
      expect(orchestrator.syncCallCount, 1);

      provider.dispose();
    });

    test('sync calls orchestrator with default mode', () async {
      // WHY: Verify the existing sync() method still works and calls the
      // orchestrator (mode defaults to SyncMode.full in the orchestrator).
      final orchestrator = _TrackingSyncOrchestrator();
      final provider = SyncProvider(orchestrator);

      await provider.sync();

      expect(orchestrator.syncCallCount, 1);
      // NOTE: sync() calls syncLocalAgencyProjects() without explicit mode,
      // so the orchestrator's default (SyncMode.full) applies.
      expect(orchestrator.lastMode, SyncMode.full);

      provider.dispose();
    });
  });
}
```

**IMPORTANT**: This test depends on the `SyncOrchestrator` having a `_testOnly()` constructor or being mockable. If the orchestrator does not have a test constructor, the implementing agent must create a mock using Mockito `@GenerateMocks([SyncOrchestrator])` instead. The test structure above is illustrative -- the implementing agent should use the project's established mocking pattern (Mockito with `@GenerateMocks`).

#### Step 7.2.6: Verify static analysis passes

```
pwsh -Command "flutter analyze lib/features/sync/presentation/providers/sync_provider.dart lib/features/sync/presentation/screens/sync_dashboard_screen.dart lib/shared/testing_keys/sync_keys.dart"
```

Expected: No analysis issues.

---

## Phase 8: Integration Wiring + Cleanup

**Prerequisite**: Phases 1-7 complete. `SyncMode` enum, `DirtyScopeTracker`, and `RealtimeHintHandler` classes exist. `SyncEngine.pushAndPull({SyncMode mode})` and `SyncOrchestrator.syncLocalAgencyProjects({SyncMode mode})` accept mode parameters. `SyncProvider.fullSync()` exists. SyncStatusIcon is in the global shell AppBar.

---

### Sub-phase 8.1: Wire DirtyScopeTracker into SyncInitializer

**Files:**
- Modify: `lib/features/sync/application/sync_initializer.dart:38-130`
- Modify: `lib/features/sync/application/sync_engine_factory.dart:10-56`

**Agent**: `backend-supabase-agent`

#### Step 8.1.1: Add DirtyScopeTracker parameter to SyncEngineFactory

Modify `lib/features/sync/application/sync_engine_factory.dart` to accept and pass `DirtyScopeTracker` to the `SyncEngine` constructor. The `SyncEngine` constructor was extended in Phase 2 to accept an optional `DirtyScopeTracker`.

Add the import and modify the `create` method:

```dart
// lib/features/sync/application/sync_engine_factory.dart
// Add import after line 8 (after sync_registry import):
// WHY: DirtyScopeTracker enables targeted pull during quick sync.
// FROM SPEC: "quick sync pulls only affected scopes whenever possible"
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';

class SyncEngineFactory {
  bool _adaptersRegistered = false;

  // WHY: Stored as a field so all engines created by this factory share the
  // same dirty scope state. The tracker persists across sync cycles.
  // NOTE: Nullable because the factory may be created before the tracker.
  DirtyScopeTracker? _dirtyScopeTracker;

  /// Set the dirty scope tracker. Called once during initialization.
  /// WHY: Setter rather than constructor param because SyncEngineFactory is
  /// created before DirtyScopeTracker in the initialization sequence.
  void setDirtyScopeTracker(DirtyScopeTracker tracker) {
    _dirtyScopeTracker = tracker;
  }

  /// Ensure sync adapters are registered (idempotent).
  void ensureAdaptersRegistered() {
    if (!_adaptersRegistered) {
      registerSyncAdapters();
      _adaptersRegistered = true;
    }
  }

  /// Create a SyncEngine for foreground sync operations.
  ///
  /// NOTE: SyncEngine constructor requires db, supabase, companyId, userId
  /// (see sync_engine.dart lines 153-160). lockedBy defaults to 'foreground'.
  /// FROM SPEC: DirtyScopeTracker passed so engine can filter pulls by dirty scope.
  SyncEngine? create({
    required Database db,
    required SupabaseClient supabase,
    required String companyId,
    required String userId,
  }) {
    ensureAdaptersRegistered();
    return SyncEngine(
      db: db,
      supabase: supabase,
      companyId: companyId,
      userId: userId,
      // WHY: Pass tracker so SyncEngine._pull() can check dirty scopes during
      // quick sync mode. Null-safe — engine handles null tracker gracefully.
      dirtyScopeTracker: _dirtyScopeTracker,
    );
  }

  /// Create a SyncEngine for background sync operations.
  ///
  /// Delegates to [SyncEngine.createForBackgroundSync] which resolves
  /// companyId/userId internally from the Supabase auth session.
  /// WHY: createForBackgroundSync only takes {database, supabase} --
  /// it reads userId from auth and companyId from user_profiles.
  /// NOTE: Background sync does NOT use dirty scope tracking (it runs
  /// maintenance mode with full integrity checks).
  Future<SyncEngine?> createForBackground({
    required Database database,
    required SupabaseClient supabase,
  }) async {
    ensureAdaptersRegistered();
    return SyncEngine.createForBackgroundSync(
      database: database,
      supabase: supabase,
    );
  }
}
```

#### Step 8.1.2: Create and wire DirtyScopeTracker in SyncInitializer

Modify `lib/features/sync/application/sync_initializer.dart`. Add DirtyScopeTracker creation between Step 2 (wire UserProfileSyncDatasource) and Step 3 (build orchestrator). The tracker must be created before the orchestrator so it can be injected into the engine factory.

Add import after line 25 (after `sync_orchestrator_builder.dart`):
```dart
// WHY: DirtyScopeTracker tracks which (projectId, tableName) tuples need pull.
// FROM SPEC: "The sync system should become dirty-scope-aware"
import 'package:construction_inspector/features/sync/engine/dirty_scope_tracker.dart';
```

After the builder setup (after line 69 `builder.userProfileSyncDatasource = userProfileSyncDs;`) and before Step 3 (line 73 `final syncOrchestrator = builder.build();`), add:

```dart
    // Step 2.5: Create DirtyScopeTracker
    // FROM SPEC: "The sync system should become dirty-scope-aware"
    // WHY: Created before the orchestrator so it can be injected into the
    // engine factory. The tracker persists across sync cycles, accumulating
    // dirty scopes from realtime hints and FCM messages.
    // NOTE: DirtyScopeTracker is a simple in-memory tracker (no DB state).
    final dirtyScopeTracker = DirtyScopeTracker();

    // Inject tracker into the builder so the engine factory can pass it
    // to each SyncEngine instance.
    builder.dirtyScopeTracker = dirtyScopeTracker;
```

**IMPORTANT**: This step assumes `SyncOrchestratorBuilder` has been extended in an earlier phase to accept `dirtyScopeTracker` and pass it to the engine factory. If the builder pattern does not support this, the implementing agent should instead call `syncOrchestrator.engineFactory.setDirtyScopeTracker(dirtyScopeTracker)` after the orchestrator is built (after line 74).

Alternative wiring (if builder does not support dirtyScopeTracker):
```dart
    // Step 3: Build orchestrator (fully configured, no setters)
    final syncOrchestrator = builder.build();
    await syncOrchestrator.initialize();

    // Step 3.5: Wire DirtyScopeTracker into engine factory
    // WHY: The engine factory creates a fresh SyncEngine per sync cycle.
    // The tracker must be shared across all cycles so dirty scopes accumulate
    // until a full sync clears them.
    // NOTE: engineFactory is accessed via a getter on the orchestrator.
    // The implementing agent must verify the orchestrator exposes this.
    syncOrchestrator.engineFactory.setDirtyScopeTracker(dirtyScopeTracker);
```

#### Step 8.1.3: Wire RealtimeHintHandler in SyncInitializer (Supabase Realtime)

Add creation of `RealtimeHintHandler` in `SyncInitializer.create()` after FCM initialization (after line 100). This handler subscribes to Supabase Broadcast for foreground invalidation hints.

Add import:
```dart
import 'package:construction_inspector/features/sync/application/realtime_hint_handler.dart';
```

After Step 6 (FCM initialization, after line 100), add:

```dart
    // Step 6.5: Realtime hint handler (foreground invalidation)
    // FROM SPEC: "Supabase-originated foreground invalidation hints"
    // WHY: When the app is in the foreground, Supabase Broadcast delivers
    // change hints in real time. The handler marks scopes dirty and triggers
    // a quick sync to pull only affected data.
    // NOTE: Only created when supabaseClient is available (online mode).
    if (supabaseClient != null) {
      final realtimeHandler = RealtimeHintHandler(
        supabaseClient: supabaseClient,
        dirtyScopeTracker: dirtyScopeTracker,
        syncOrchestrator: syncOrchestrator,
      );
      // WHY: initialize() subscribes to the broadcast channel. Non-blocking
      // because realtime is a best-effort foreground optimization.
      // ignore: unawaited_futures
      realtimeHandler
          .initialize()
          .catchError((e) => Logger.sync('Realtime hint handler init failed: $e'));
    }
```

#### Step 8.1.4: Update SyncInitializer return type to include DirtyScopeTracker

If downstream consumers (like `sync_providers.dart`) need access to the `DirtyScopeTracker`, update the return record. Otherwise, the tracker is self-contained within the initializer.

The `DirtyScopeTracker` is wired into the engine factory and realtime handler at creation time. It does not need to be returned unless `sync_providers.dart` needs to expose it as a Provider. For now, keep it internal:

```dart
    // No change to return type — DirtyScopeTracker is fully wired internally.
    // It lives in the engine factory and realtime handler, both of which are
    // created and wired in this method.
    return (
      orchestrator: syncOrchestrator,
      lifecycleManager: syncLifecycleManager,
    );
```

---

### Sub-phase 8.2: Update SyncProvider to Expose Sync Modes

**Files:**
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart:282-285`

**Agent**: `backend-supabase-agent`

#### Step 8.2.1: Add quickSync method to SyncProvider

The existing `sync()` method at line 283-285 calls `syncLocalAgencyProjects()` without a mode parameter (defaults to `SyncMode.full` per Phase 3 changes). Add a `quickSync()` method for programmatic use by the lifecycle manager and realtime handler.

Add after the `fullSync()` method (added in Phase 7, Sub-phase 7.2):

```dart
  /// Trigger a quick sync (push local changes + pull dirty scopes only).
  ///
  /// FROM SPEC: "startup / foreground / background catch-up" uses quick sync.
  /// WHY: Quick sync is the low-latency path for app resume and realtime hint
  /// reactions. It avoids broad project-wide pulls, only fetching tables/projects
  /// that have been marked dirty by the DirtyScopeTracker.
  /// NOTE: This method is called programmatically by SyncLifecycleManager on
  /// app resume and by RealtimeHintHandler on foreground invalidation hints.
  Future<SyncResult> quickSync() async {
    return await _syncOrchestrator.syncLocalAgencyProjects(
      mode: SyncMode.quick,
    );
  }
```

#### Step 8.2.2: Update the default sync() method documentation

Update the doc comment on `sync()` (line 282) to clarify its role now that multiple modes exist:

```dart
  /// Trigger a manual sync via SyncOrchestrator.
  ///
  /// NOTE: Calls syncLocalAgencyProjects() with the orchestrator's default mode
  /// (SyncMode.full after Phase 3). For explicit mode control, use [fullSync()]
  /// or [quickSync()] instead.
  /// WHY: Preserved for backward compatibility — existing callers (SyncSection
  /// in settings, stale data banner) continue to work without changes.
  Future<SyncResult> sync() async {
    return await _syncOrchestrator.syncLocalAgencyProjects();
  }
```

---

### Sub-phase 8.3: Wire DirtyScopeTracker into sync_providers.dart

**Files:**
- Modify: `lib/features/sync/di/sync_providers.dart:49-91`

**Agent**: `backend-supabase-agent`

#### Step 8.3.1: No changes needed to sync_providers.dart

After review, `sync_providers.dart` delegates initialization to `SyncInitializer.create()` and exposes providers via `providers()`. The `DirtyScopeTracker` is created and wired INSIDE `SyncInitializer.create()` -- it does not need to be surfaced as a Provider because:

1. No UI widget directly reads `DirtyScopeTracker`
2. The tracker is injected into `SyncEngineFactory` and `RealtimeHintHandler` at creation time
3. The `SyncProvider` does not need direct access to the tracker

If a future phase requires exposing `DirtyScopeTracker` as a Provider (e.g., for a debug screen showing dirty scopes), the implementing agent can add it to the return record and the providers list at that time.

```dart
// NO CHANGES to sync_providers.dart in this phase.
// WHY: DirtyScopeTracker is fully self-contained within SyncInitializer.create().
// It is injected into the engine factory and realtime handler, both of which
// are created in the same method. No external consumer needs Provider access.
```

---

### Sub-phase 8.4: Dead Code Audit and Cleanup

**Files:**
- Audit: `lib/core/database/schema/sync_tables.dart` -- NOT dead code, keep
- Audit: `lib/features/settings/presentation/widgets/sync_section.dart` -- NOT dead code, keep

**Agent**: `general-purpose`

#### Step 8.4.1: Verify sync_tables.dart is NOT dead code

The blast-radius analysis flagged `lib/core/database/schema/sync_tables.dart` as dead code. This is INCORRECT. Verification:

- `SyncTables.createDeletionNotificationsTable` is used in `lib/core/database/database_service.dart:182` (in `_onCreate`)
- `SyncTables.indexes` is used in `lib/core/database/database_service.dart:270` (index creation loop)
- `SyncTables.createDeletionNotificationsTable` is used in `lib/core/database/database_service.dart:1231` (migration path)
- The file is exported via `lib/core/database/schema/schema.dart:13`

```
// DECISION: DO NOT DELETE lib/core/database/schema/sync_tables.dart
// WHY: It contains the deletion_notifications table schema used by
// database_service.dart in _onCreate, index creation, and migration v34.
// The blast-radius analysis was incorrect — this file has 3 active consumers.
```

#### Step 8.4.2: Verify sync_section.dart is NOT dead code

The blast-radius analysis flagged `lib/features/settings/presentation/widgets/sync_section.dart` as dead code. This is INCORRECT. Verification:

- `SyncSection` widget is used in `lib/features/settings/presentation/screens/settings_screen.dart:226`
- The file is exported via `lib/features/settings/presentation/widgets/widgets.dart:3`

```
// DECISION: DO NOT DELETE lib/features/settings/presentation/widgets/sync_section.dart
// WHY: SyncSection is actively used by settings_screen.dart line 226.
// It provides the sync status/action UI in the Settings tab.
// The blast-radius analysis was incorrect — this widget has an active consumer.
```

#### Step 8.4.3: Audit barrel exports flagged as dead

The blast-radius lists these barrel exports with "zero importers":
- `sync.dart`, `application.dart`, `data.dart`, `di.dart`, `domain.dart`, `presentation.dart`, `providers.dart`

These are barrel export files (re-export patterns). They may have zero DIRECT importers because consumers import specific files instead of barrels. This is normal in this codebase. Do NOT delete barrel exports -- they exist for organizational consistency and may be used by external tooling or future imports.

```
// DECISION: DO NOT DELETE barrel export files.
// WHY: Barrel exports are an organizational pattern, not dead code.
// They re-export submodules for convenience. Zero direct importers is expected
// when consumers prefer specific imports for tree-shaking.
```

---

### Sub-phase 8.5: Final Verification

**Files:**
- All modified files from Phases 7-8

**Agent**: `general-purpose`

#### Step 8.5.1: Run full static analysis

```
pwsh -Command "flutter analyze"
```

Expected: No analysis issues. If issues arise, they are likely:
- Missing imports for `SyncMode` (added in Phase 1, should be in `sync_types.dart`)
- Missing `DirtyScopeTracker` parameter in `SyncEngine` constructor (added in Phase 2)
- Missing `RealtimeHintHandler` class (created in Phase 5)
- Lint rule violations in new code (A9 silent catch, A22 raw snackbar, etc.)

The implementing agent must resolve all analysis issues before marking Phase 8 complete.

#### Step 8.5.2: Verify no import cycles

Check that the new wiring does not introduce circular imports:
- `sync_initializer.dart` imports `dirty_scope_tracker.dart` and `realtime_hint_handler.dart` -- both are leaf files with no back-imports to the application layer
- `sync_engine_factory.dart` imports `dirty_scope_tracker.dart` -- a leaf file
- `sync_provider.dart` imports `sync_types.dart` (already existing) for `SyncMode`

No circular dependencies are introduced.

#### Step 8.5.3: Verify testing key consistency

Confirm all new testing keys are properly structured:
- `SyncTestingKeys.syncNowFullButton` in `sync_keys.dart` -- Key value `'sync_now_full_button'`
- Used in `sync_dashboard_screen.dart` on the `FilledButton.icon`

The implementing agent should verify the key is accessible from test files via the `SyncTestingKeys` class.

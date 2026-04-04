# Code Review — Cycle 1

**Verdict**: REJECT

6 Critical issues, 7 Significant issues, 5 Minor issues. The plan contains a pervasive phantom import (`sync_mode.dart`) that would break compilation in every file from Phase 4 onward, a silent data-loss regression in background sync, and extensive cross-phase contradictions where the same files are modified in incompatible ways across Phases 3, 4, and 8.

## Critical Issues

**C1: Phantom import `sync_mode.dart` — file does not exist (10 occurrences)**
- Plan lines 1636, 1675, 2062, 2118, 2239, 2290, 2352, 2443, 2575, 2642
- `SyncMode` is defined in `lib/features/sync/domain/sync_types.dart` (Phase 1, step 1.1.1). No `sync_mode.dart` exists anywhere in the codebase (verified via grep). Every file in Phases 4-6 importing from this phantom path will fail `flutter analyze`.
- Fix: Replace all 10 occurrences with `package:construction_inspector/features/sync/domain/sync_types.dart` or the appropriate relative path matching each file's existing import style.

**C2: Maintenance mode drops background push — silent data loss risk**
- Plan step 5.3.1 (lines 2302, 2311): Changes `BackgroundSyncHandler` from `engine.pushAndPull()` to `engine.pushAndPull(mode: SyncMode.maintenance)`.
- The maintenance case in pushAndPull (plan lines 978-1027) does NOT call `_push()` or `_pull()`. It only runs prune, integrity, and orphan scan.
- The plan's own comment at line 2300 claims "Push is still included" — this is factually wrong relative to the implementation 200 lines earlier.
- Result: Local changes made while the app is backgrounded will accumulate indefinitely until the user manually opens the app. This is a silent regression from current behavior where background sync pushes all pending changes every 4 hours.
- Fix: Either (a) add `_push()` to the maintenance mode path, (b) use `SyncMode.full` for background sync, or (c) create a `SyncMode.background` mode that does push + maintenance but skips full pull.

**C3: `catch (_)` silent catch in FCM background handler violates lint A9**
- Plan line 2539: `} catch (_) {` with empty body.
- Lint rule A9 enforces no silent catch blocks — every catch must include a `Logger.<category>()` call. The justification that Logger may fail in a background isolate is valid, but the solution must still include a best-effort log.
- Fix: `catch (e) { try { Logger.sync('FCM background error: $e'); } catch (_) { /* Logger unavailable in isolate */ } }`

**C4: `RealtimeHintHandler.initialize()` called but method does not exist**
- Phase 8.1.3 (line 3680): `realtimeHandler.initialize()`
- Phase 6.2 (lines 2624-2810) defines the class with `subscribe(String companyId)`, `_handleHint()`, `parseHintPayload()`, `dispose()`. No `initialize()` method.
- Phase 6.3 (line 2897) correctly uses `realtimeHintHandler.subscribe(companyId)`.
- Fix: Replace `realtimeHandler.initialize()` with `realtimeHandler.subscribe(companyId)`, obtaining `companyId` from `authProvider.userProfile?.companyId` with a null guard.

**C5: Test uses positional argument for named parameter — compile error**
- Plan lines 2617-2618: `tracker.isDirty('daily_entries', 'proj-456')` and `tracker.isDirty('photos', 'proj-456')`
- `isDirty` signature (plan line 416): `bool isDirty(String tableName, {String? projectId})`. `projectId` is named, not positional.
- Fix: Change to `tracker.isDirty('daily_entries', projectId: 'proj-456')` and `tracker.isDirty('photos', projectId: 'proj-456')`.

**C6: Test mock uses non-existent `super._testOnly()` constructor**
- Plan line 3443: `_TrackingSyncOrchestrator() : super._testOnly();`
- `SyncOrchestrator` has no `_testOnly()` constructor. The actual test constructor is `SyncOrchestrator.forTesting(DatabaseService dbService)` at `sync_orchestrator.dart:127`.
- Fix: `_TrackingSyncOrchestrator(DatabaseService dbService) : super.forTesting(dbService);` and update all call sites.

## Significant Issues

**S1: Phases 3, 4, and 8 apply duplicate, contradictory modifications to the same files**
- `SyncOrchestrator._dirtyScopeTracker`: Phase 3.3.1 (line 1224) adds as non-nullable `final DirtyScopeTracker`, Phase 4.2.2 (line 1928) adds as nullable `final DirtyScopeTracker?`.
- `SyncOrchestrator.fromBuilder`: Phase 3.3.2 (line 1246) uses `dirtyScopeTracker ?? DirtyScopeTracker()` default, Phase 4.2.2 (line 1956) allows null.
- `syncLocalAgencyProjects({SyncMode mode})`: Added in both Phase 3.3.4 (line 1303) and Phase 4.1.2 (line 1687).
- `_syncWithRetry({SyncMode mode})`: Added in both Phase 3.3.5 (line 1331) and Phase 4.1.3 (line 1707).
- `_doSync({SyncMode mode})`: Added in both Phase 3.3.6 (line 1377) and Phase 4.1.4 (line 1736).
- Fix: Consolidate into a single phase. Remove Phase 3.3 entirely (it duplicates Phase 4), or remove Phase 4 (it duplicates Phase 3.3). Pick nullable `DirtyScopeTracker?` consistently.

**S2: `SyncEngineFactory.create()` redesigned three incompatible ways**
- Phase 3.2 (line 1176): Adds `DirtyScopeTracker? dirtyScopeTracker` parameter.
- Phase 4.2.1 (line 1884): Repeats the same parameter addition.
- Phase 8.1.1 (line 3569): Removes the parameter, uses `_dirtyScopeTracker` field + `setDirtyScopeTracker()` setter.
- Fix: Use Phase 8.1.1's setter approach (correctly addresses initialization order where factory is created before tracker) and remove parameter-based designs from Phases 3.2 and 4.2.1.

**S3: Phase 6.3 changes `SyncInitializer.create` return type; Phase 8.1.4 reverts it**
- Phase 6.3.2 (line 2844): Adds `RealtimeHintHandler? realtimeHintHandler` to return record.
- Phase 6.5 (line 3118): Instructs updating ALL callers to destructure the new field.
- Phase 8.1.4 (line 3692): Says "No change to return type" and returns only `orchestrator` + `lifecycleManager`.
- Fix: Pick one approach. If handler needs external disposal on sign-out, keep Phase 6.3. If self-contained, remove Phase 6.3 and 6.5.

**S4: FCM hint test mock creates new `DirtyScopeTracker` on every property access**
- Plan line 2372: `DirtyScopeTracker? get dirtyScopeTracker => DirtyScopeTracker();`
- Each access gets a fresh instance — dirty marks are lost. The test at line 2377 cannot verify dirty-scope marking.
- Fix: Store a single instance: `final _tracker = DirtyScopeTracker(); @override DirtyScopeTracker? get dirtyScopeTracker => _tracker;`

**S5: `Colors.white` hardcoded in presentation file violates lint A13**
- Plan line 3360: `color: Colors.white` inside `sync_dashboard_screen.dart` (`lib/**/presentation/screens/`).
- Fix: `color: Theme.of(context).colorScheme.onPrimary`

**S6: Phase 8.1.3 passes `dirtyScopeTracker` to `RealtimeHintHandler` constructor, which doesn't accept it**
- Plan line 3673: `dirtyScopeTracker: dirtyScopeTracker,` in constructor call.
- Phase 6.2 constructor (line 2691) only accepts `supabaseClient` and `syncOrchestrator`.
- Fix: Remove `dirtyScopeTracker: dirtyScopeTracker,` from the constructor call.

**S7: `SyncOrchestrator.dirtyScopeTracker` getter nullability conflicts between phases**
- Phase 3.3.7 (line 1403): Returns non-nullable `DirtyScopeTracker`.
- Phase 4.2.4 (line 2025): Returns nullable `DirtyScopeTracker?`.
- Consumer code at lines 2480, 2767 uses `if (tracker != null)` null checks, expecting nullable.
- Fix: Use nullable `DirtyScopeTracker?` consistently.

## Minor Issues

**M1: Duplicate test coverage across Phase 1 and Phase 3 test files**
- `sync_types_test.dart` (Phase 1) and `sync_engine_mode_test.dart` (Phase 3) both test `SyncMode` enum values and `DirtyScopeTracker` marking/matching. Phase 3 tests should focus on engine integration.

**M2: Import path style inconsistency**
- Phase 3.3.1 (line 1211) uses absolute import for `dirty_scope_tracker.dart` in `sync_orchestrator.dart`. Phase 4.1.2 (line 1935) uses relative import. The file uses relative imports for existing dependencies. Use relative imports consistently.

**M3: Missing definitive import instruction for `shared.dart` in `sync_dashboard_screen.dart`**
- Step 7.2.4 says "Add if not already present." Verified: it is NOT present. State definitively: "Add this import."

**M4: `SyncStatusIcon` not truly global — only shows on Dashboard and Calendar tabs**
- Shell AppBar only renders for `_projectContextRoutes` (`/` and `/calendar`). Toolbox, Settings, and Projects screens get `appBar: null`. The spec says "available in the main app chrome."

**M5: Plan line numbers drift after Phase 3's pushAndPull rewrite**
- Phase 3 replaces ~150 lines of `pushAndPull()`. All subsequent line references to `sync_engine.dart` will be off. Implementing agents should search by method name, not line number.

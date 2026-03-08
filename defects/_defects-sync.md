# Defects: Sync

Active patterns for sync. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [FLUTTER] 2026-03-06: Mock SyncOrchestrator missing getPendingBuckets() causes test hang (Session 511)
**Pattern**: `MockSyncOrchestrator` in widget tests overrode `getPendingCount()` but not `getPendingBuckets()`. `SyncProvider._refreshPendingCount()` calls `getPendingBuckets()` → hits real DB init → hangs forever in test binding. Test runner shows infinite iterations.
**Prevention**: When mocking SyncOrchestrator, ALWAYS override both `getPendingCount()` AND `getPendingBuckets()`. Remove unnecessary `Future.delayed()` from mock methods — fake timers interact poorly with test bindings.
**Ref**: @test/features/sync/presentation/widgets/sync_status_icon_test.dart:170

### [ASYNC] 2026-03-06: _lastSyncTime persisted on failure creates 24h dead zone (Session 511)
**Pattern**: `_lastSyncTime = DateTime.now()` and its DB persist ran unconditionally after sync — even on failure. Lifecycle manager saw a recent timestamp and wouldn't force retry for 24 hours.
**Prevention**: Only update `_lastSyncTime` inside the `if (!result.hasErrors)` success block. Failed syncs should leave the old timestamp so staleness detection works.
**Ref**: @lib/features/sync/application/sync_orchestrator.dart:224-237

### [ASYNC] 2026-03-06: _isTransientError() defeats auth retry — 'auth' in nonTransientPatterns (Session 509) — FIXED
**Pattern**: FIX-A added a 5s retry loop in `_createEngine()`, but `_isTransientError()` has `'auth'` in `nonTransientPatterns`. The error "No auth context available for sync" matches, killing retries.
**Prevention**: Add early guard in `_isTransientError()` to treat "No auth context" as transient BEFORE the nonTransient pattern loop. **FIXED in Session 511**: Early-return guard added.
**Ref**: @lib/features/sync/application/sync_orchestrator.dart:367-374

### [CONFIG] 2026-03-06: Stale config banner checks only checkConfig() timestamp (Session 508)
**Pattern**: `AppConfigProvider.isConfigStale` only checks `_lastConfigCheckAt`. Successful sync also proves server reachability but doesn't reset the clock. Banner shows permanently if `checkConfig()` fails, even when sync works fine.
**Prevention**: Unify staleness to `max(lastConfigCheck, lastSyncSuccess) > 24h`. Call `recordSyncSuccess()` after successful push/pull.
**Ref**: @lib/features/auth/presentation/providers/app_config_provider.dart:57-61

### [DATA] 2026-03-06: SyncRegistry.registerAdapters() never called in production (Session 507)
**Pattern**: `SyncRegistry.instance.adapters` is empty in production — only called in test code. Push/pull loops iterate 0 adapters and silently succeed.
**Prevention**: Registration must happen in BOTH foreground (`SyncOrchestrator.initialize()`) AND background (`backgroundSyncCallback()`). Use a shared top-level function.
**Ref**: @lib/features/sync/engine/sync_registry.dart:26

<!-- Add defects above this line -->

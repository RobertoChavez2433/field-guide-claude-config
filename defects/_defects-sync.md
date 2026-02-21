# Defects: Sync

Active patterns for sync. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [TEST] 2026-02-21: SyncProvider Test Mock Construction Fails with Null DatabaseService
**Status**: RESOLVED in Session 426.
**Symptom**: `test/features/sync/presentation/providers/sync_provider_test.dart` fails before assertions with `type 'Null' is not a subtype of type 'DatabaseService'`, followed by `LateInitializationError` on `syncProvider`.
**Root Cause (observed)**: Test `MockSyncService` instantiation path is incompatible with current `SyncService` constructor expectations for `DatabaseService`.
**Impact**: Previously caused sync provider suite failures and contributed to non-green full-repo runs.
**Prevention/Fix Direction**: Keep test doubles aligned with non-null constructor contract and initialize test DB/FFI in setup.
**Ref**: @test/features/sync/presentation/providers/sync_provider_test.dart:7,99

<!-- Add defects above this line -->

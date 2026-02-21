# Defects: Sync

Active patterns for sync. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [TEST] 2026-02-21: SyncProvider Test Mock Construction Fails with Null DatabaseService
**Status**: OPEN (newly observed during full-suite loop in Session 422).
**Symptom**: `test/features/sync/presentation/providers/sync_provider_test.dart` fails before assertions with `type 'Null' is not a subtype of type 'DatabaseService'`, followed by `LateInitializationError` on `syncProvider`.
**Root Cause (observed)**: Test `MockSyncService` instantiation path is incompatible with current `SyncService` constructor expectations for `DatabaseService`.
**Impact**: Entire sync provider test suite fails, keeping full-repo test run non-green despite PDF scope passing.
**Prevention/Fix Direction**: Update sync test doubles to satisfy non-null constructor contract (or provide explicit fake `DatabaseService`), then rerun provider suite.
**Ref**: @test/features/sync/presentation/providers/sync_provider_test.dart:7,99

<!-- Add defects above this line -->

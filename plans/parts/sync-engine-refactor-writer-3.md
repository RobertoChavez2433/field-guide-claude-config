## Phase 6: Control Plane Abstractions

Phase 6 extracts four focused classes from SyncOrchestrator and SyncLifecycleManager that encapsulate retry policy, connectivity checking, lifecycle trigger decisions, and post-sync hooks. These classes make the control-plane behavior testable and injectable, breaking the implicit callback mesh that currently couples the application layer.

**Depends on**: Phase 5 (SyncEngine slim coordinator complete)

**Verification gate**: All characterization tests green, all existing sync tests green via CI, all new contract + isolation tests green, `flutter analyze` zero violations.

---

### Sub-phase 6.1: Create SyncRetryPolicy

**Files:**
- Create: `lib/features/sync/application/sync_retry_policy.dart`
- Test: `test/features/sync/application/sync_retry_policy_contract_test.dart`

**Agent**: backend-supabase-agent

#### Step 6.1.1: Write SyncRetryPolicy contract test (RED)

Create the contract test that defines the expected behavior of SyncRetryPolicy before the implementation exists.

```dart
// test/features/sync/application/sync_retry_policy_contract_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/application/sync_retry_policy.dart';
import 'package:construction_inspector/features/sync/domain/sync_error.dart';

void main() {
  late SyncRetryPolicy policy;

  setUp(() {
    // WHY: SyncRetryPolicy is pure logic with injected config — no mocks needed.
    policy = SyncRetryPolicy();
  });

  group('shouldRetry', () {
    test('returns true for transient network error within max retries', () {
      // FROM SPEC: Transient errors (SocketException, DNS, Timeout) should retry.
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.networkError,
        retryable: true,
        shouldRefreshAuth: false,
        userSafeMessage: 'Network unavailable',
        logDetail: 'SocketException: Connection refused',
      );
      expect(policy.shouldRetry(error: error, attempt: 0), isTrue);
      expect(policy.shouldRetry(error: error, attempt: 1), isTrue);
      expect(policy.shouldRetry(error: error, attempt: 2), isTrue);
    });

    test('returns false when max retries exceeded', () {
      // FROM SPEC: maxRetries = 3 (SyncOrchestrator._maxRetries)
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.networkError,
        retryable: true,
        shouldRefreshAuth: false,
        userSafeMessage: 'Network unavailable',
        logDetail: 'SocketException: Connection refused',
      );
      expect(policy.shouldRetry(error: error, attempt: 3), isFalse);
    });

    test('returns false for non-retryable errors regardless of attempt', () {
      // FROM SPEC: RLS denied (42501) -> permanent, never retry.
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.rlsDenial,
        retryable: false,
        shouldRefreshAuth: false,
        userSafeMessage: 'Permission denied',
        logDetail: 'RLS policy violation',
      );
      expect(policy.shouldRetry(error: error, attempt: 0), isFalse);
    });

    test('returns true for auth-expired error that needs refresh', () {
      // FROM SPEC: 401/PGRST301/JWT -> auth refresh -> retry.
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.authExpired,
        retryable: true,
        shouldRefreshAuth: true,
        userSafeMessage: 'Session expired',
        logDetail: '401 Unauthorized',
      );
      expect(policy.shouldRetry(error: error, attempt: 0), isTrue);
    });

    test('returns true for transient startup race error', () {
      // FROM SPEC: "No auth context available for sync" is transient (startup race).
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.transient,
        retryable: true,
        shouldRefreshAuth: false,
        userSafeMessage: 'Starting up...',
        logDetail: 'No auth context available for sync',
      );
      expect(policy.shouldRetry(error: error, attempt: 0), isTrue);
    });
  });

  group('computeBackoff', () {
    test('uses exponential backoff with base delay 5s', () {
      // FROM SPEC: _baseRetryDelay = Duration(seconds: 5), backoff = base * (1 << attempt)
      // Attempt 0 = 5s, Attempt 1 = 10s, Attempt 2 = 20s
      expect(policy.computeBackoff(attempt: 0), const Duration(seconds: 5));
      expect(policy.computeBackoff(attempt: 1), const Duration(seconds: 10));
      expect(policy.computeBackoff(attempt: 2), const Duration(seconds: 20));
    });
  });

  group('shouldScheduleBackgroundRetry', () {
    test('returns true when all retries exhausted on transient error', () {
      // FROM SPEC (BUG-004): Schedule a background retry after 60s when exhausted.
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.networkError,
        retryable: true,
        shouldRefreshAuth: false,
        userSafeMessage: 'Network unavailable',
        logDetail: 'DNS lookup failed',
      );
      expect(policy.shouldScheduleBackgroundRetry(error: error), isTrue);
    });

    test('returns false for permanent errors', () {
      final error = ClassifiedSyncError(
        kind: SyncErrorKind.rlsDenial,
        retryable: false,
        shouldRefreshAuth: false,
        userSafeMessage: 'Permission denied',
        logDetail: '42501',
      );
      expect(policy.shouldScheduleBackgroundRetry(error: error), isFalse);
    });
  });

  group('backgroundRetryDelay', () {
    test('returns 60 seconds', () {
      // FROM SPEC (BUG-004): Background retry delay = 60s.
      expect(policy.backgroundRetryDelay, const Duration(seconds: 60));
    });
  });
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_retry_policy.dart"` -- expected: file does not exist yet, test compiles but fails (RED).

#### Step 6.1.2: Implement SyncRetryPolicy

```dart
// lib/features/sync/application/sync_retry_policy.dart
import 'package:construction_inspector/features/sync/domain/sync_error.dart';

/// Encapsulates retryability decisions, backoff calculation, and background
/// retry scheduling for sync operations.
///
/// FROM SPEC Section 3: Extracted from SyncOrchestrator._syncWithRetry
/// (sync_orchestrator.dart:372-459) and _isTransientError (lines 507-569).
/// Uses ClassifiedSyncError for error categorization instead of string matching.
///
/// WHY: The retry policy was tangled with DNS checking, status callbacks, and
/// the sync execution loop. Extracting it makes retry behavior independently
/// testable and injectable.
class SyncRetryPolicy {
  /// Maximum number of retry attempts before exhaustion.
  /// FROM SPEC: SyncOrchestrator._maxRetries = 3
  final int maxRetries;

  /// Base delay for exponential backoff.
  /// FROM SPEC: SyncOrchestrator._baseRetryDelay = Duration(seconds: 5)
  final Duration baseRetryDelay;

  /// Delay before a background retry after exhaustion.
  /// FROM SPEC (BUG-004): 60s background timer after all retries fail.
  final Duration backgroundRetryDelay;

  const SyncRetryPolicy({
    this.maxRetries = 3,
    this.baseRetryDelay = const Duration(seconds: 5),
    this.backgroundRetryDelay = const Duration(seconds: 60),
  });

  /// Determines whether a sync should be retried given the classified error
  /// and the current attempt number (0-indexed).
  ///
  /// Returns `true` if:
  /// - The error is marked retryable by SyncErrorClassifier
  /// - The attempt count is below [maxRetries]
  ///
  /// Returns `false` if:
  /// - The error is permanent (RLS denial, FK violation, etc.)
  /// - Retry attempts are exhausted
  bool shouldRetry({
    required ClassifiedSyncError error,
    required int attempt,
  }) {
    if (!error.retryable) return false;
    return attempt < maxRetries;
  }

  /// Computes the exponential backoff duration for the given attempt.
  ///
  /// FROM SPEC: `_baseRetryDelay * (1 << attempt)` -> 5s, 10s, 20s
  Duration computeBackoff({required int attempt}) {
    return baseRetryDelay * (1 << attempt);
  }

  /// Determines whether a background retry should be scheduled after
  /// all immediate retries are exhausted.
  ///
  /// FROM SPEC (BUG-004): Only schedule background retry for transient
  /// (retryable) errors. Permanent errors should not trigger background retry.
  bool shouldScheduleBackgroundRetry({
    required ClassifiedSyncError error,
  }) {
    return error.retryable;
  }
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_retry_policy.dart"` -- expected: 0 issues found.

#### Step 6.1.3: Run contract test (GREEN)

Run the contract test written in step 6.1.1 to verify it passes against the implementation.

**Verify**: CI run targets `test/features/sync/application/sync_retry_policy_contract_test.dart` -- expected: all tests pass.

---

### Sub-phase 6.2: Create ConnectivityProbe

**Files:**
- Create: `lib/features/sync/application/connectivity_probe.dart`
- Test: `test/features/sync/application/connectivity_probe_test.dart`

**Agent**: backend-supabase-agent

#### Step 6.2.1: Write ConnectivityProbe test (RED)

```dart
// test/features/sync/application/connectivity_probe_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/application/connectivity_probe.dart';

/// WHY: ConnectivityProbe wraps HTTP client + config. Tests use a fake implementation
/// to verify the interface contract without network calls.
void main() {
  group('ConnectivityProbe interface', () {
    test('FakeConnectivityProbe returns configured online state', () async {
      // WHY: Verify the interface contract — callers can inject a fake for testing.
      final probe = FakeConnectivityProbe(isReachable: true);
      expect(await probe.checkReachability(), isTrue);
      expect(probe.isOnline, isTrue);
    });

    test('FakeConnectivityProbe returns offline when unreachable', () async {
      final probe = FakeConnectivityProbe(isReachable: false);
      expect(await probe.checkReachability(), isFalse);
      expect(probe.isOnline, isFalse);
    });

    test('checkReachability updates isOnline state', () async {
      final probe = FakeConnectivityProbe(isReachable: true);
      // Initial state before any check
      expect(probe.isOnline, isFalse);
      await probe.checkReachability();
      expect(probe.isOnline, isTrue);
    });
  });
}

/// Test double for ConnectivityProbe that does not make HTTP calls.
class FakeConnectivityProbe implements ConnectivityProbe {
  final bool isReachable;
  bool _isOnline = false;

  FakeConnectivityProbe({required this.isReachable});

  @override
  bool get isOnline => _isOnline;

  @override
  Future<bool> checkReachability() async {
    _isOnline = isReachable;
    return isReachable;
  }
}
```

#### Step 6.2.2: Implement ConnectivityProbe

```dart
// lib/features/sync/application/connectivity_probe.dart
import 'dart:async';
import 'dart:io';

import 'package:http/http.dart' as http;

import 'package:construction_inspector/core/config/supabase_config.dart';
import 'package:construction_inspector/core/config/test_mode_config.dart';
import 'package:construction_inspector/core/logging/logger.dart';

/// Interface for checking network reachability to the sync backend.
///
/// FROM SPEC Section 3: Extracted from SyncOrchestrator.checkDnsReachability
/// (sync_orchestrator.dart:581-603).
///
/// WHY: DNS/connectivity checking was entangled with sync orchestration.
/// Extracting it behind an interface lets tests inject a fake and lets the
/// retry policy check connectivity without depending on SyncOrchestrator.
abstract class ConnectivityProbe {
  /// Whether the backend was reachable on the last check.
  bool get isOnline;

  /// Performs a reachability check against the backend.
  ///
  /// Returns `true` if the server responds (any HTTP status, including 4xx).
  /// Updates [isOnline] as a side effect.
  Future<bool> checkReachability();
}

/// Production implementation that sends HTTP HEAD to the Supabase REST endpoint.
///
/// FROM SPEC: HTTP HEAD to `${SupabaseConfig.url}/rest/v1/` with 5s timeout.
/// WHY: InternetAddress.lookup() fails with errno=7 on Android even with
/// working internet because it does not bind to the active network interface.
/// An HTTP HEAD request uses the HTTP client which properly binds.
class SupabaseConnectivityProbe implements ConnectivityProbe {
  bool _isOnline = true;

  @override
  bool get isOnline => _isOnline;

  @override
  Future<bool> checkReachability() async {
    // WHY: Mock mode always returns true — no network needed for testing.
    if (TestModeConfig.useMockData) return true;

    try {
      final uri = Uri.parse('${SupabaseConfig.url}/rest/v1/');
      final response = await http.head(uri).timeout(
        const Duration(seconds: 5),
      );
      _isOnline = true;
      Logger.sync('Reachability check passed (HTTP ${response.statusCode})');
      return true;
    } on SocketException catch (e) {
      _isOnline = false;
      Logger.sync('Reachability check failed: SocketException: $e');
      return false;
    } on TimeoutException catch (e) {
      _isOnline = false;
      Logger.sync('Reachability check failed: Timeout: $e');
      return false;
    } on Exception catch (e) {
      _isOnline = false;
      Logger.sync('Reachability check failed: $e');
      return false;
    }
  }
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/connectivity_probe.dart"` -- expected: 0 issues found.

#### Step 6.2.3: Run connectivity probe test (GREEN)

**Verify**: CI run targets `test/features/sync/application/connectivity_probe_test.dart` -- expected: all tests pass.

---

### Sub-phase 6.3: Create SyncTriggerPolicy

**Files:**
- Create: `lib/features/sync/application/sync_trigger_policy.dart`
- Test: `test/features/sync/application/sync_trigger_policy_contract_test.dart`

**Agent**: backend-supabase-agent

#### Step 6.3.1: Write SyncTriggerPolicy contract test (RED)

```dart
// test/features/sync/application/sync_trigger_policy_contract_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/application/sync_trigger_policy.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

void main() {
  group('SyncTriggerPolicy.evaluateResume', () {
    test('returns forced full sync when data is stale (>24h)', () {
      // FROM SPEC: SyncLifecycleManager._handleResumed — if timeSinceSync > 24h,
      // trigger forced full sync.
      final lastSync = DateTime.now().subtract(const Duration(hours: 25));
      final result = SyncTriggerPolicy.evaluateResume(
        lastSyncTime: lastSync,
        isSyncing: false,
        hasPendingBackgroundHint: false,
        backgroundHintMode: SyncMode.quick,
      );
      expect(result.mode, SyncMode.full);
      expect(result.forced, isTrue);
    });

    test('returns quick sync when data is fresh (<24h)', () {
      // FROM SPEC: App resumed, data not stale -> quick sync.
      final lastSync = DateTime.now().subtract(const Duration(hours: 2));
      final result = SyncTriggerPolicy.evaluateResume(
        lastSyncTime: lastSync,
        isSyncing: false,
        hasPendingBackgroundHint: false,
        backgroundHintMode: SyncMode.quick,
      );
      expect(result.mode, SyncMode.quick);
      expect(result.forced, isFalse);
    });

    test('returns quick sync when no previous sync recorded', () {
      // FROM SPEC: "if lastSync == null, quick sync"
      final result = SyncTriggerPolicy.evaluateResume(
        lastSyncTime: null,
        isSyncing: false,
        hasPendingBackgroundHint: false,
        backgroundHintMode: SyncMode.quick,
      );
      expect(result.mode, SyncMode.quick);
      expect(result.forced, isFalse);
    });

    test('returns skip when sync is already in progress', () {
      // FROM SPEC: "if _syncOrchestrator.isSyncing, skip"
      final result = SyncTriggerPolicy.evaluateResume(
        lastSyncTime: DateTime.now(),
        isSyncing: true,
        hasPendingBackgroundHint: false,
        backgroundHintMode: SyncMode.quick,
      );
      expect(result.skip, isTrue);
    });

    test('returns forced full when background hint mode is full', () {
      // FROM SPEC: consumePendingBackgroundHintMode() returned full -> forced recovery.
      final result = SyncTriggerPolicy.evaluateResume(
        lastSyncTime: DateTime.now().subtract(const Duration(hours: 1)),
        isSyncing: false,
        hasPendingBackgroundHint: true,
        backgroundHintMode: SyncMode.full,
      );
      expect(result.mode, SyncMode.full);
      expect(result.forced, isTrue);
    });
  });
}
```

#### Step 6.3.2: Implement SyncTriggerPolicy

```dart
// lib/features/sync/application/sync_trigger_policy.dart
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

/// Pure-logic class that decides which sync mode to use based on
/// lifecycle events, staleness, and realtime hint inputs.
///
/// FROM SPEC Section 3: Extracted from SyncLifecycleManager._handleResumed
/// (sync_lifecycle_manager.dart:158-210) decision tree.
///
/// WHY: The lifecycle manager mixed trigger policy decisions with
/// WidgetsBindingObserver callbacks, DNS checking, and timer management.
/// Extracting the decision logic into a pure function makes it independently
/// testable without requiring widget binding or async I/O.
class SyncTriggerPolicy {
  SyncTriggerPolicy._();

  /// Threshold after which data is considered stale and a forced full sync
  /// is triggered on app resume.
  /// FROM SPEC: SyncLifecycleManager._staleThreshold = Duration(hours: 24)
  static const Duration staleThreshold = Duration(hours: 24);

  /// Evaluates what sync mode should be used when the app resumes.
  ///
  /// Decision tree (matches SyncLifecycleManager._handleResumed exactly):
  /// 1. If already syncing -> skip
  /// 2. If background hint mode is full -> forced full sync (recovery)
  /// 3. If lastSyncTime is null -> quick sync (first run)
  /// 4. If stale (>24h) -> forced full sync
  /// 5. Otherwise -> quick sync
  static SyncTriggerDecision evaluateResume({
    required DateTime? lastSyncTime,
    required bool isSyncing,
    required bool hasPendingBackgroundHint,
    required SyncMode backgroundHintMode,
  }) {
    // WHY: If sync is already in progress, skip to avoid overlap.
    if (isSyncing) {
      return const SyncTriggerDecision.skip();
    }

    // WHY: Background FCM hint with full mode means a background wakeup occurred
    // but no targeted scope data was available, so a broader recovery sync is
    // the safest fallback.
    if (hasPendingBackgroundHint && backgroundHintMode == SyncMode.full) {
      return const SyncTriggerDecision(
        mode: SyncMode.full,
        forced: true,
        skip: false,
      );
    }

    // WHY: No previous sync recorded -> quick sync to get initial data.
    if (lastSyncTime == null) {
      return const SyncTriggerDecision(
        mode: SyncMode.quick,
        forced: false,
        skip: false,
      );
    }

    // WHY: Stale data (>24h) requires a full sync to ensure completeness.
    final timeSinceSync = DateTime.now().difference(lastSyncTime);
    if (timeSinceSync > staleThreshold) {
      return const SyncTriggerDecision(
        mode: SyncMode.full,
        forced: true,
        skip: false,
      );
    }

    // WHY: Fresh data -> quick sync to pick up recent changes.
    return const SyncTriggerDecision(
      mode: SyncMode.quick,
      forced: false,
      skip: false,
    );
  }
}

/// The result of evaluating a sync trigger decision.
///
/// Immutable value class following the project's domain-value-types pattern
/// (const constructor, named fields).
class SyncTriggerDecision {
  /// Which sync mode to use.
  final SyncMode mode;

  /// Whether this is a forced (non-dismissible) sync.
  final bool forced;

  /// Whether to skip sync entirely (e.g., already in progress).
  final bool skip;

  const SyncTriggerDecision({
    this.mode = SyncMode.quick,
    this.forced = false,
    this.skip = false,
  });

  const SyncTriggerDecision.skip()
      : mode = SyncMode.quick,
        forced = false,
        skip = true;
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_trigger_policy.dart"` -- expected: 0 issues found.

#### Step 6.3.3: Run contract test (GREEN)

**Verify**: CI run targets `test/features/sync/application/sync_trigger_policy_contract_test.dart` -- expected: all tests pass.

---

### Sub-phase 6.4: Create PostSyncHooks

**Files:**
- Create: `lib/features/sync/application/post_sync_hooks.dart`
- Test: `test/features/sync/application/post_sync_hooks_test.dart`

**Agent**: backend-supabase-agent

#### Step 6.4.1: Write PostSyncHooks test (RED)

```dart
// test/features/sync/application/post_sync_hooks_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/application/post_sync_hooks.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

void main() {
  group('PostSyncHooks', () {
    test('runs all registered hooks on success', () async {
      // FROM SPEC: After successful sync, run recordSyncSuccess,
      // pullCompanyMembers, updateLastSyncedAt.
      final callLog = <String>[];
      final hooks = PostSyncHooks(
        onSyncSuccess: () async {
          callLog.add('recordSyncSuccess');
        },
        onPullCompanyMembers: (companyId) async {
          callLog.add('pullCompanyMembers:$companyId');
        },
        onUpdateLastSyncedAt: () async {
          callLog.add('updateLastSyncedAt');
        },
      );

      await hooks.runAfterSuccess(
        mode: SyncMode.full,
        companyId: 'company-123',
        hadDirtyScopes: false,
      );

      expect(callLog, containsAllInOrder([
        'recordSyncSuccess',
        'pullCompanyMembers:company-123',
        'updateLastSyncedAt',
      ]));
    });

    test('skips pullCompanyMembers and updateLastSyncedAt for quick sync', () async {
      // FROM SPEC: sync_orchestrator.dart:332 — "if (mode != SyncMode.quick ...)"
      final callLog = <String>[];
      final hooks = PostSyncHooks(
        onSyncSuccess: () async { callLog.add('recordSyncSuccess'); },
        onPullCompanyMembers: (companyId) async { callLog.add('pullCompanyMembers'); },
        onUpdateLastSyncedAt: () async { callLog.add('updateLastSyncedAt'); },
      );

      await hooks.runAfterSuccess(
        mode: SyncMode.quick,
        companyId: 'company-123',
        hadDirtyScopes: false,
      );

      expect(callLog, ['recordSyncSuccess']);
      expect(callLog, isNot(contains('pullCompanyMembers')));
    });

    test('swallows individual hook errors without failing', () async {
      // WHY: Individual hook failures must not break the sync result.
      // FROM SPEC: Each hook in orchestrator is wrapped in try/catch.
      final hooks = PostSyncHooks(
        onSyncSuccess: () async { throw Exception('Config service down'); },
        onPullCompanyMembers: (companyId) async {},
        onUpdateLastSyncedAt: () async {},
      );

      // Should not throw
      await hooks.runAfterSuccess(
        mode: SyncMode.full,
        companyId: 'company-123',
        hadDirtyScopes: false,
      );
    });

    test('runs pullCompanyMembers for quick sync with dirty scopes', () async {
      // FROM SPEC: sync_orchestrator.dart:299-302 — shouldRefreshFreshnessClock
      // is true when mode==quick AND hadDirtyScopesBeforeSync.
      // However, pullCompanyMembers only runs when mode != quick.
      // The freshness clock logic is separate from profile pull.
      final callLog = <String>[];
      final hooks = PostSyncHooks(
        onSyncSuccess: () async { callLog.add('recordSyncSuccess'); },
        onPullCompanyMembers: (companyId) async { callLog.add('pullCompanyMembers'); },
        onUpdateLastSyncedAt: () async { callLog.add('updateLastSyncedAt'); },
      );

      await hooks.runAfterSuccess(
        mode: SyncMode.quick,
        companyId: 'company-123',
        hadDirtyScopes: true,
      );

      // NOTE: pullCompanyMembers is gated on mode != quick, not on dirty scopes.
      expect(callLog, ['recordSyncSuccess']);
    });

    test('skips profile hooks when companyId is null', () async {
      final callLog = <String>[];
      final hooks = PostSyncHooks(
        onSyncSuccess: () async { callLog.add('recordSyncSuccess'); },
        onPullCompanyMembers: (companyId) async { callLog.add('pull'); },
        onUpdateLastSyncedAt: () async { callLog.add('update'); },
      );

      await hooks.runAfterSuccess(
        mode: SyncMode.full,
        companyId: null,
        hadDirtyScopes: false,
      );

      expect(callLog, ['recordSyncSuccess']);
    });
  });
}
```

#### Step 6.4.2: Implement PostSyncHooks

```dart
// lib/features/sync/application/post_sync_hooks.dart
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';

/// Runs app-level follow-up concerns after a successful sync.
///
/// FROM SPEC Section 3: Extracted from SyncOrchestrator.syncLocalAgencyProjects
/// (sync_orchestrator.dart:316-349). These hooks are unrelated to sync itself --
/// they are app-level concerns that piggyback on successful sync completion.
///
/// WHY: Having AppConfigProvider.recordSyncSuccess() and
/// UserProfileSyncDatasource.pullCompanyMembers() inside the orchestrator
/// created upward dependencies from the sync application layer into the
/// auth presentation layer. PostSyncHooks inverts the dependency: callers
/// inject their hooks via callbacks, and the sync layer calls them.
class PostSyncHooks {
  /// Called after any successful sync to clear stale-config banners.
  /// FROM SPEC: _appConfigProvider?.recordSyncSuccess() (line 324)
  final Future<void> Function()? onSyncSuccess;

  /// Called after successful full/maintenance sync to refresh company member profiles.
  /// FROM SPEC: _userProfileSyncDatasource?.pullCompanyMembers(companyId) (lines 336)
  final Future<void> Function(String companyId)? onPullCompanyMembers;

  /// Called after successful full/maintenance sync to update last_synced_at.
  /// FROM SPEC: _userProfileSyncDatasource?.updateLastSyncedAt() (lines 344)
  final Future<void> Function()? onUpdateLastSyncedAt;

  const PostSyncHooks({
    this.onSyncSuccess,
    this.onPullCompanyMembers,
    this.onUpdateLastSyncedAt,
  });

  /// Runs all applicable hooks after a successful sync.
  ///
  /// Each hook is wrapped in try/catch to prevent individual failures from
  /// breaking the sync result. This matches the existing behavior in
  /// SyncOrchestrator.syncLocalAgencyProjects (lines 324-349).
  ///
  /// [mode] determines which hooks run:
  /// - `onSyncSuccess` runs for ALL modes
  /// - `onPullCompanyMembers` and `onUpdateLastSyncedAt` run only for
  ///   non-quick modes (full, maintenance) when [companyId] is non-null
  ///
  /// FROM SPEC: sync_orchestrator.dart:332 — `if (mode != SyncMode.quick && companyId != null && profileSyncDs != null)`
  Future<void> runAfterSuccess({
    required SyncMode mode,
    required String? companyId,
    required bool hadDirtyScopes,
  }) async {
    // Hook 1: Record sync success (all modes)
    // FROM SPEC: FIX-B — clears stale config banner
    if (onSyncSuccess != null) {
      try {
        await onSyncSuccess!();
      } on Object catch (e) {
        Logger.sync('PostSyncHooks: onSyncSuccess failed: $e');
      }
    }

    // Hook 2 & 3: Profile-related hooks (non-quick modes only)
    // FROM SPEC: sync_orchestrator.dart:332 — gated on mode != quick
    if (mode != SyncMode.quick && companyId != null) {
      // Hook 2: Pull company members
      if (onPullCompanyMembers != null) {
        try {
          await onPullCompanyMembers!(companyId);
          Logger.sync('PostSyncHooks: Company members pulled');
        } on Object catch (e) {
          Logger.sync('PostSyncHooks: pullCompanyMembers failed: $e');
        }
      }

      // Hook 3: Update last_synced_at
      if (onUpdateLastSyncedAt != null) {
        try {
          await onUpdateLastSyncedAt!();
          Logger.sync('PostSyncHooks: last_synced_at updated');
        } on Object catch (e) {
          Logger.sync('PostSyncHooks: updateLastSyncedAt failed: $e');
        }
      }
    }
  }
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/post_sync_hooks.dart"` -- expected: 0 issues found.

#### Step 6.4.3: Run PostSyncHooks test (GREEN)

**Verify**: CI run targets `test/features/sync/application/post_sync_hooks_test.dart` -- expected: all tests pass.

---

### Sub-phase 6.5: Wire control-plane classes into SyncLifecycleManager

**Files:**
- Modify: `lib/features/sync/application/sync_lifecycle_manager.dart`

**Agent**: backend-supabase-agent

#### Step 6.5.1: Refactor SyncLifecycleManager to use SyncTriggerPolicy and ConnectivityProbe

Modify `lib/features/sync/application/sync_lifecycle_manager.dart` to delegate the resume decision to `SyncTriggerPolicy.evaluateResume()` and DNS checking to `ConnectivityProbe`. This replaces the inline decision tree at lines 158-210.

The modification changes `_handleResumed()` to:
1. Call `SyncTriggerPolicy.evaluateResume()` with the current state
2. Check `ConnectivityProbe.checkReachability()` before triggering
3. Dispatch to `_triggerSync()` or `_triggerForcedSync()` based on the decision

Key changes in the file:
- Add a `ConnectivityProbe` constructor parameter (optional, defaults to `SupabaseConnectivityProbe()`)
- Import `sync_trigger_policy.dart` and `connectivity_probe.dart`
- Replace the inline staleness/mode decision tree in `_handleResumed()` with a call to `SyncTriggerPolicy.evaluateResume()`
- Replace `_syncOrchestrator.checkDnsReachability()` with `_connectivityProbe.checkReachability()`

IMPORTANT: The `SyncLifecycleManager` constructor signature changes from `SyncLifecycleManager(this._syncOrchestrator)` to accept an optional `ConnectivityProbe` parameter. This preserves backward compatibility since `ConnectivityProbe` is an interface with a default implementation.

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_lifecycle_manager.dart"` -- expected: 0 issues found.

#### Step 6.5.2: Run characterization tests

Run all existing sync lifecycle manager tests and characterization tests to confirm no behavior change.

**Verify**: CI run targets `test/features/sync/application/sync_lifecycle_manager_test.dart` -- expected: all tests pass (characterization equivalence).

---

### Sub-phase 6.6: Verify Phase 6

**Agent**: general-purpose

#### Step 6.6.1: Run full analyzer

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues found.

#### Step 6.6.2: Run all sync tests via CI

Push branch, open PR, verify CI green (all characterization tests, all existing tests, all new P6 contract tests).

---

## Phase 7: Layer Violation Fixes

Phase 7 eliminates the remaining layer violations: SQL queries in the orchestrator, raw orchestrator exposure in the provider, Postgres error code matching in the presentation layer, and upward dependencies from sync into auth. It introduces SyncQueryService for dashboard queries, replaces SyncOrchestrator with SyncCoordinator, and refactors SyncProvider to subscribe to typed status/diagnostics rather than owning independent state.

**Depends on**: Phase 6 (control-plane abstractions complete)

**Verification gate**: All characterization tests green, all existing sync tests green via CI, all new tests green, `flutter analyze` zero violations.

---

### Sub-phase 7.1: Create SyncQueryService

**Files:**
- Create: `lib/features/sync/application/sync_query_service.dart`
- Test: `test/features/sync/application/sync_query_service_test.dart`

**Agent**: backend-supabase-agent

#### Step 7.1.1: Write SyncQueryService test (RED)

```dart
// test/features/sync/application/sync_query_service_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/application/sync_query_service.dart';

/// WHY: SyncQueryService moves 5 SQL queries out of SyncOrchestrator into a
/// dedicated service backed by LocalSyncStore (or DatabaseService during transition).
/// Tests verify the query interface, not the SQL — that is covered by integration tests.
void main() {
  // NOTE: These tests require a real SQLite database (sqflite_common_ffi).
  // They are integration-style tests that verify the queries produce correct results.
  // The implementing agent must set up an in-memory database with the sync schema.

  group('SyncQueryService', () {
    // Test: getPendingBuckets returns correct bucket counts
    // Test: getIntegrityResults parses sync_metadata rows
    // Test: getUndismissedConflictCount returns correct count
    // Test: getLastSyncTime reads from sync_metadata
    // Test: empty database returns zero counts / null timestamps

    // NOTE: Full test implementation requires database setup from P2's LocalSyncStore.
    // The implementing agent should write these tests using the same sqflite_common_ffi
    // test setup pattern used in test/features/sync/engine/ (see sync_engine_test.dart).
  });
}
```

#### Step 7.1.2: Implement SyncQueryService

```dart
// lib/features/sync/application/sync_query_service.dart
import 'dart:convert';

import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/config/sync_config.dart';
import 'package:construction_inspector/shared/utils/safe_row.dart';

/// Dashboard/query-facing access to pending buckets, integrity results,
/// conflict counts, and sync metadata.
///
/// FROM SPEC Section 3: Moves 5 SQL queries OUT of SyncOrchestrator:
/// - getPendingBuckets (sync_orchestrator.dart:607-666)
/// - getIntegrityResults (sync_orchestrator.dart:682-701)
/// - getUndismissedConflictCount (sync_orchestrator.dart:704-710)
/// - initialize/last_sync_time (sync_orchestrator.dart:165-198)
/// - syncLocalAgencyProjects/last_sync_time refresh (sync_orchestrator.dart:304-314)
///
/// WHY: SQL queries in the orchestrator violated layer separation. The orchestrator
/// is an application-layer coordinator; database queries belong in the data layer.
/// SyncQueryService provides a clean query surface that SyncProvider and dashboard
/// screens can consume without reaching through the orchestrator.
class SyncQueryService {
  final DatabaseService _dbService;

  SyncQueryService(this._dbService);

  /// Bucket definitions for inspector-friendly pending count display.
  /// FROM SPEC: SyncOrchestrator.syncBuckets (sync_orchestrator.dart:45-58)
  static const Map<String, List<String>> syncBuckets = {
    'Projects': ['projects', 'bid_items', 'locations', 'todo_items'],
    'Entries': [
      'daily_entries',
      'contractors',
      'equipment',
      'entry_contractors',
      'entry_equipment',
      'entry_quantities',
      'entry_personnel_counts',
    ],
    'Forms': ['inspector_forms', 'form_responses', 'form_exports'],
    'Photos & Files': ['photos', 'entry_exports', 'documents'],
  };

  /// Returns pending unique record counts grouped by bucket.
  ///
  /// Each bucket counts DISTINCT record_ids (not operations).
  /// FROM SPEC: Moved from SyncOrchestrator.getPendingBuckets (lines 607-666).
  Future<Map<String, BucketCount>> getPendingBuckets() async {
    try {
      final db = await _dbService.database;
      final result = <String, BucketCount>{};

      for (final entry in syncBuckets.entries) {
        final bucketName = entry.key;
        final tables = entry.value;
        final placeholders = tables.map((_) => '?').join(',');

        // FROM SPEC: Filter out retry-exhausted entries to match push loop.
        const maxRetry = SyncEngineConfig.maxRetryCount;

        // Total unique records for the bucket
        final totalRows = await db.rawQuery(
          'SELECT COUNT(DISTINCT record_id) as cnt FROM change_log '
          'WHERE processed = 0 AND retry_count < ? AND table_name IN ($placeholders)',
          [maxRetry, ...tables],
        );
        final total = totalRows.first.intOrDefault('cnt');

        // Per-table breakdown (for dashboard expandable view)
        final breakdown = <String, int>{};
        for (final table in tables) {
          final rows = await db.rawQuery(
            'SELECT COUNT(DISTINCT record_id) as cnt FROM change_log '
            'WHERE processed = 0 AND retry_count < ? AND table_name = ?',
            [maxRetry, table],
          );
          breakdown[table] = rows.first.intOrDefault('cnt');
        }

        result[bucketName] = BucketCount(total: total, breakdown: breakdown);
      }

      // Count anything not in a bucket
      final allBucketTables = syncBuckets.values.expand((t) => t).toList();
      final otherPlaceholders = allBucketTables.map((_) => '?').join(',');
      const maxRetryOther = SyncEngineConfig.maxRetryCount;
      final otherRows = await db.rawQuery(
        'SELECT COUNT(DISTINCT record_id) as cnt FROM change_log '
        'WHERE processed = 0 AND retry_count < ? AND table_name NOT IN ($otherPlaceholders)',
        [maxRetryOther, ...allBucketTables],
      );
      final otherCount = otherRows.first.intOrDefault('cnt');
      if (otherCount > 0) {
        result['Other'] = BucketCount(
          total: otherCount,
          breakdown: {'other': otherCount},
        );
      }

      return result;
    } on Exception catch (e) {
      Logger.sync('SyncQueryService: getPendingBuckets failed: $e');
      return {};
    }
  }

  /// Returns the total pending count across all buckets.
  Future<int> getPendingCount() async {
    final buckets = await getPendingBuckets();
    return buckets.values.fold<int>(0, (sum, b) => sum + b.total);
  }

  /// Returns integrity check results stored by IntegrityChecker.
  ///
  /// Each key is a table name, value is the JSON result map.
  /// FROM SPEC: Moved from SyncOrchestrator.getIntegrityResults (lines 682-701).
  Future<Map<String, Map<String, dynamic>>> getIntegrityResults() async {
    final db = await _dbService.database;
    final rows = await db.rawQuery(
      "SELECT key, value FROM sync_metadata WHERE key LIKE 'integrity_%'",
    );
    final results = <String, Map<String, dynamic>>{};
    for (final row in rows) {
      final key = row.requireString('key');
      final tableName = key.replaceFirst('integrity_', '');
      try {
        results[tableName] =
            jsonDecode(row.requireString('value')) as Map<String, dynamic>;
      } on Exception catch (e) {
        Logger.sync(
          'SyncQueryService: malformed integrity entry for $tableName: $e',
        );
      }
    }
    return results;
  }

  /// Returns the count of undismissed conflicts in the conflict log.
  ///
  /// FROM SPEC: Moved from SyncOrchestrator.getUndismissedConflictCount (lines 704-710).
  Future<int> getUndismissedConflictCount() async {
    final db = await _dbService.database;
    final result = await db.rawQuery(
      'SELECT COUNT(*) as cnt FROM conflict_log WHERE dismissed_at IS NULL',
    );
    return result.firstOrNull?.intOrDefault('cnt') ?? 0;
  }

  /// Reads the persisted last sync time from sync_metadata.
  ///
  /// FROM SPEC: Moved from SyncOrchestrator.initialize (lines 182-195).
  Future<DateTime?> getLastSyncTime() async {
    try {
      final db = await _dbService.database;
      final result = await db.query(
        'sync_metadata',
        where: "key = 'last_sync_time'",
      );
      if (result.isNotEmpty) {
        final timeStr = result.first.optionalString('value');
        if (timeStr != null) {
          return DateTime.tryParse(timeStr);
        }
      }
    } on Exception catch (e) {
      Logger.sync('SyncQueryService: Failed to load last sync time: $e');
    }
    return null;
  }
}

/// Pending count for a single sync bucket.
///
/// NOTE: This was previously `BucketCount` in sync_orchestrator.dart:722-730.
/// Moved here to break the presentation layer's import of sync_orchestrator.
class BucketCount {
  /// Total unique records pending in this bucket.
  final int total;

  /// Per-table breakdown within the bucket.
  final Map<String, int> breakdown;

  const BucketCount({required this.total, required this.breakdown});
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_query_service.dart"` -- expected: 0 issues found.

---

### Sub-phase 7.2: Create SyncCoordinator (replaces SyncOrchestrator)

**Files:**
- Create: `lib/features/sync/application/sync_coordinator.dart`
- Modify: `lib/features/sync/application/sync_orchestrator.dart` (add deprecation, delegate to SyncCoordinator or retain temporarily as facade)

**Agent**: backend-supabase-agent

#### Step 7.2.1: Create SyncCoordinator

The SyncCoordinator replaces SyncOrchestrator. It uses the extracted control-plane classes (SyncRetryPolicy, ConnectivityProbe, PostSyncHooks) and delegates query operations to SyncQueryService. It no longer contains any SQL, no AppConfigProvider, no UserProfileSyncDatasource.

Key differences from SyncOrchestrator:
- Constructor takes `SyncRetryPolicy`, `ConnectivityProbe`, `PostSyncHooks` instead of `AppConfigProvider`, `UserProfileSyncDatasource`
- `getPendingBuckets()`, `getIntegrityResults()`, `getUndismissedConflictCount()` are removed (moved to SyncQueryService)
- `_isTransientError()` is removed (replaced by `SyncErrorClassifier` via `SyncRetryPolicy`)
- `_sanitizeSyncError` never existed here (it was in SyncProvider)
- `checkDnsReachability()` delegates to `ConnectivityProbe`
- Post-sync hooks call `PostSyncHooks.runAfterSuccess()` instead of inline code

The implementing agent must:
1. Copy `sync_orchestrator.dart` as the starting point
2. Remove all SQL queries (5 locations from ground-truth)
3. Remove `_appConfigProvider` and `_userProfileSyncDatasource` fields
4. Replace `_isTransientError()` with `SyncRetryPolicy.shouldRetry()` using a `ClassifiedSyncError` constructed from the `SyncResult.errorMessages`
5. Replace `checkDnsReachability()` body with `_connectivityProbe.checkReachability()`
6. Replace post-sync hook code (lines 324-349) with `_postSyncHooks.runAfterSuccess()`
7. Keep: `_createEngine()`, `syncLocalAgencyProjects()`, `_syncWithRetry()` (using new retry policy), `_doSync()`, callback fields, `dispose()`

IMPORTANT: During the transition, `SyncOrchestrator` must remain importable (16 production files + 14 test files depend on it). The strategy is:
- Create `SyncCoordinator` as the clean replacement
- Add a `@Deprecated` annotation to `SyncOrchestrator`
- Update `SyncOrchestrator` to extend or delegate to `SyncCoordinator` (thin facade)
- Phase 7.4 updates all importers to use `SyncCoordinator` directly, then `SyncOrchestrator` is deleted

Target: `lib/features/sync/application/sync_coordinator.dart` at approximately 220 lines (down from 730 in SyncOrchestrator).

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_coordinator.dart"` -- expected: 0 issues found.

#### Step 7.2.2: Add deprecation facade to SyncOrchestrator

Modify `lib/features/sync/application/sync_orchestrator.dart` to:
1. Add `@Deprecated('Use SyncCoordinator instead')` to the class
2. Add `SyncCoordinator get coordinator` getter that returns the underlying coordinator
3. Keep all existing public methods as delegating wrappers so downstream code continues to work during the transition

This is a TEMPORARY step. Phase 7.4 removes all usages, then the file is deleted.

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues (deprecation warnings are not errors).

---

### Sub-phase 7.3: Refactor SyncProvider

**Files:**
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart`

**Agent**: frontend-flutter-specialist-agent

#### Step 7.3.1: Remove orchestrator getter and _sanitizeSyncError

Modify `lib/features/sync/presentation/providers/sync_provider.dart`:

1. **Remove `get orchestrator`** (line 22) -- this is a layer violation exposing raw SyncOrchestrator to presentation consumers.

2. **Delete `_sanitizeSyncError()`** (lines 328-348) -- replace with `ClassifiedSyncError.userSafeMessage` from the SyncErrorClassifier output. The `onSyncComplete` callback result must carry the classified error's user-safe message instead of raw Postgres error strings.

3. **Change constructor** to accept `SyncCoordinator` instead of `SyncOrchestrator`. Add a `SyncQueryService` parameter for dashboard queries.

4. **Replace `_refreshPendingCount()`** to delegate to `SyncQueryService.getPendingBuckets()` instead of `_syncOrchestrator.getPendingBuckets()`.

5. **Remove the `BucketCount` re-export** from line 7 (`export '../../application/sync_orchestrator.dart' show BucketCount;`) and replace with import from `sync_query_service.dart`.

6. **Update `isOnline` getter** to read from `ConnectivityProbe` (via SyncCoordinator) instead of `_syncOrchestrator.isSupabaseOnline`.

7. **Update `lastSyncTime` getter** to read from SyncQueryService or SyncCoordinator's tracked value instead of falling back to `_syncOrchestrator.lastSyncTime`.

Key changes to the constructor signature:
```dart
// BEFORE (sync_provider.dart:104):
SyncProvider(SyncOrchestrator orchestrator) : _syncOrchestrator = orchestrator;

// AFTER:
SyncProvider(
  SyncCoordinator coordinator, {
  required SyncQueryService queryService,
}) : _coordinator = coordinator,
     _queryService = queryService;
```

Key changes to `_setupListeners()`:
- Wire `_coordinator.onCircuitBreakerTrip` (same as before)
- Wire `_coordinator.onStatusChanged` (same as before)
- Wire `_coordinator.onSyncComplete` -- replace `_sanitizeSyncError(raw)` with using the user-safe message that the SyncResult now carries (via ClassifiedSyncError enrichment from P1)

Key changes to sync trigger methods:
```dart
// BEFORE:
Future<SyncResult> fullSync() async {
  return _syncOrchestrator.syncLocalAgencyProjects(mode: SyncMode.full, recordManualTrigger: true);
}

// AFTER:
Future<SyncResult> fullSync() async {
  return _coordinator.syncLocalAgencyProjects(mode: SyncMode.full, recordManualTrigger: true);
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/presentation/providers/sync_provider.dart"` -- expected: 0 issues found.

---

### Sub-phase 7.4: Update DI wiring

**Files:**
- Modify: `lib/features/sync/di/sync_providers.dart`
- Modify: `lib/features/sync/application/sync_initializer.dart`
- Modify: `lib/features/sync/application/sync_orchestrator_builder.dart` (rename to `sync_coordinator_builder.dart` or update to build SyncCoordinator)

**Agent**: backend-supabase-agent

#### Step 7.4.1: Update SyncInitializer to create SyncCoordinator

Modify `lib/features/sync/application/sync_initializer.dart`:

1. Replace `SyncOrchestratorBuilder` usage with a builder for `SyncCoordinator`
2. Create `SyncRetryPolicy`, `ConnectivityProbe`, `PostSyncHooks` instances
3. Wire `PostSyncHooks` with the `_appConfigProvider.recordSyncSuccess()` and `_userProfileSyncDatasource.pullCompanyMembers()` callbacks that were previously inline in the orchestrator
4. Create `SyncQueryService` with `dbService`
5. Return `SyncCoordinator` instead of `SyncOrchestrator` in the result record

Change the return type from:
```dart
({SyncOrchestrator orchestrator, SyncLifecycleManager lifecycleManager, ...})
```
to:
```dart
({SyncCoordinator coordinator, SyncLifecycleManager lifecycleManager, ...})
```

Update the `SyncLifecycleManager` constructor call to pass the `ConnectivityProbe`.

IMPORTANT: The `PostSyncHooks` wiring is where the upward dependencies get properly inverted:
```dart
final postSyncHooks = PostSyncHooks(
  onSyncSuccess: () async {
    appConfigProvider.recordSyncSuccess();
  },
  onPullCompanyMembers: userProfileSyncDs != null
      ? (companyId) async {
          await userProfileSyncDs.pullCompanyMembers(companyId);
        }
      : null,
  onUpdateLastSyncedAt: userProfileSyncDs != null
      ? () async {
          await userProfileSyncDs.updateLastSyncedAt();
        }
      : null,
);
```

This keeps the auth/profile dependencies in the initializer (where they already exist) rather than pushing them down into the coordinator.

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/application/sync_initializer.dart"` -- expected: 0 issues found.

#### Step 7.4.2: Update SyncProviders.providers()

Modify `lib/features/sync/di/sync_providers.dart`:

1. Change `initialize()` return type to use `SyncCoordinator` instead of `SyncOrchestrator`
2. Change `providers()` parameter from `SyncOrchestrator syncOrchestrator` to `SyncCoordinator syncCoordinator`
3. Add `SyncQueryService` parameter
4. Replace `Provider<SyncOrchestrator>.value(value: syncOrchestrator)` with `Provider<SyncCoordinator>.value(value: syncCoordinator)`
5. Add `Provider<SyncQueryService>.value(value: syncQueryService)`
6. Update `SyncProvider` construction to pass both `SyncCoordinator` and `SyncQueryService`

```dart
// AFTER:
ChangeNotifierProvider(
  create: (_) {
    final syncProvider = SyncProvider(syncCoordinator, queryService: syncQueryService);
    syncLifecycleManager.onStaleDataWarning = syncProvider.setStaleDataWarning;
    syncLifecycleManager.onForcedSyncInProgress = syncProvider.setForcedSyncInProgress;
    syncProvider.onSyncCycleComplete = () =>
        projectSyncHealthProvider.refreshFromService(projectLifecycleService);
    syncCoordinator.onNewAssignmentDetected = syncProvider.addNotification;
    return syncProvider;
  },
),
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/di/sync_providers.dart"` -- expected: 0 issues found.

#### Step 7.4.3: Update AppDependencies SyncDeps

Modify `lib/core/di/app_dependencies.dart`:

Change `SyncDeps` to hold `SyncCoordinator` instead of `SyncOrchestrator`:
```dart
class SyncDeps {
  final SyncCoordinator syncCoordinator;  // WAS: SyncOrchestrator syncOrchestrator
  final SyncLifecycleManager syncLifecycleManager;
  // ... add SyncQueryService if needed by other DI tiers
}
```

Update all references to `syncDeps.syncOrchestrator` -> `syncDeps.syncCoordinator`.

**Verify**: `pwsh -Command "flutter analyze lib/core/di/app_dependencies.dart"` -- expected: 0 issues found.

---

### Sub-phase 7.5: Update all SyncOrchestrator importers

**Files (16 production):**
- Modify: `lib/core/di/app_dependencies.dart` -- change SyncDeps field type
- Modify: `lib/core/driver/driver_server.dart` -- change field type and method calls
- Modify: `lib/core/router/scaffold_with_nav_bar.dart` -- change `context.read<SyncOrchestrator>()` to `context.read<SyncCoordinator>()`
- Modify: `lib/features/projects/di/projects_providers.dart` -- change parameter type
- Modify: `lib/features/projects/presentation/providers/project_provider.dart` -- change parameter type
- Modify: `lib/features/projects/presentation/screens/project_list_screen.dart` -- change `context.read<SyncOrchestrator>()` (6 occurrences)
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart` -- change `context.read<SyncOrchestrator>()`
- Modify: `lib/features/settings/presentation/screens/admin_dashboard_screen.dart` -- change `context.read<SyncOrchestrator>()` to `context.read<SyncCoordinator>()` for DNS check
- Modify: `lib/features/settings/presentation/widgets/sign_out_dialog.dart` -- change `context.read<SyncOrchestrator>()`
- Modify: `lib/features/sync/application/fcm_handler.dart` -- change constructor parameter type
- Modify: `lib/features/sync/application/realtime_hint_handler.dart` -- change constructor parameter type
- Modify: `lib/features/sync/application/sync_enrollment_service.dart` -- change constructor parameter type
- Modify: `lib/features/sync/application/sync_initializer.dart` -- already updated in 7.4.1
- Modify: `lib/features/sync/application/sync_orchestrator_builder.dart` -- rename to build SyncCoordinator
- Modify: `lib/features/sync/di/sync_providers.dart` -- already updated in 7.4.2
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart` -- already updated in 7.3.1

**Files (15 test):**
- Modify: `test/features/sync/application/fcm_handler_test.dart`
- Modify: `test/features/sync/presentation/widgets/sync_status_icon_test.dart`
- Modify: `test/features/sync/presentation/screens/sync_dashboard_screen_test.dart`
- Modify: `test/features/sync/presentation/providers/sync_provider_test.dart`
- Modify: `test/features/sync/engine/sync_engine_circuit_breaker_test.dart`
- Modify: `test/features/sync/application/sync_lifecycle_manager_test.dart`
- Modify: `test/features/sync/application/sync_enrollment_service_test.dart`
- Modify: `test/features/sync/application/realtime_hint_handler_test.dart`
- Modify: `test/core/driver/driver_server_sync_status_test.dart`
- Modify: `test/features/sync/engine/sync_engine_delete_test.dart`
- Modify: `test/features/sync/application/sync_orchestrator_builder_test.dart`
- Modify: `test/features/projects/presentation/providers/project_provider_sync_mode_test.dart`
- Modify: `test/features/projects/presentation/screens/project_list_screen_test.dart`
- Modify: `test/helpers/sync_orchestrator_test_helper.dart`
- Modify: `test/core/router/scaffold_with_nav_bar_test.dart`

**Agent**: general-purpose

#### Step 7.5.1: Rename SyncOrchestrator to SyncCoordinator in all production files

For each of the 16 production files listed above, the implementing agent must:

1. Change the import from `sync_orchestrator.dart` to `sync_coordinator.dart`
2. Change all type references from `SyncOrchestrator` to `SyncCoordinator`
3. Change all variable names from `syncOrchestrator` / `orchestrator` to `syncCoordinator` / `coordinator`
4. Verify that the methods called on the renamed type still exist on `SyncCoordinator`

Special cases:
- **`driver_server.dart`**: Uses `syncOrchestrator?.syncLocalAgencyProjects()` and `syncOrchestrator?.isSyncing`. Both methods exist on SyncCoordinator.
- **`scaffold_with_nav_bar.dart`**: Uses `context.read<SyncOrchestrator>()` -- change to `context.read<SyncCoordinator>()`. This requires updating the Provider registration in sync_providers.dart (done in 7.4.2).
- **`project_list_screen.dart`**: 6 occurrences of `context.read<SyncOrchestrator>()` calling `syncLocalAgencyProjects()`. All become `context.read<SyncCoordinator>()`.
- **`admin_dashboard_screen.dart`**: Calls `checkDnsReachability()` which is renamed to `checkReachability()` on ConnectivityProbe. The screen should read `context.read<ConnectivityProbe>()` instead, OR `SyncCoordinator` can expose a `checkDnsReachability()` facade that delegates.
- **`sign_out_dialog.dart`**: Calls `dispose()` on the orchestrator. SyncCoordinator retains `dispose()`.
- **`realtime_hint_handler.dart`**: References `_syncOrchestrator.dirtyScopeTracker`, `_syncOrchestrator.isSyncing`, `_syncOrchestrator.syncLocalAgencyProjects()`. All must exist on SyncCoordinator.
- **`fcm_handler.dart`**: References `_syncOrchestrator?.dirtyScopeTracker`, `_syncOrchestrator?.isSyncing`, `_syncOrchestrator?.syncLocalAgencyProjects()`. All must exist on SyncCoordinator.

IMPORTANT: Where external files (outside `features/sync/`) need to call `getPendingBuckets()`, `getIntegrityResults()`, or `getUndismissedConflictCount()`, they should use `SyncQueryService` instead. The provider will expose these via getters that delegate to SyncQueryService.

#### Step 7.5.2: Update all test files

For each of the 15 test files listed above:

1. Update imports
2. Update mock class names (e.g., `MockSyncOrchestrator` -> `MockSyncCoordinator`)
3. Update `_TrackingOrchestrator` in `fcm_handler_test.dart` -> `_TrackingCoordinator`
4. Update `_MockSyncOrchestrator` in `sync_engine_circuit_breaker_test.dart`
5. Update `sync_orchestrator_test_helper.dart` -> rename file and contents

IMPORTANT: The test subclasses (`_EmptyResponseSyncEngine`, etc.) may need signature updates if the test helpers construct SyncOrchestrator directly. The implementing agent must verify each test file compiles and runs.

#### Step 7.5.3: Delete SyncOrchestrator

Once all importers are updated:
1. Delete `lib/features/sync/application/sync_orchestrator.dart`
2. Delete or rename `lib/features/sync/application/sync_orchestrator_builder.dart`
3. Update any barrel exports in `lib/features/sync/application/application.dart`

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues found, no references to SyncOrchestrator remain.

---

### Sub-phase 7.6: Verify Phase 7

**Agent**: general-purpose

#### Step 7.6.1: Run full analyzer

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues found.

#### Step 7.6.2: Verify all characterization and existing tests via CI

Push branch, open PR, verify CI green. All characterization tests must pass (equivalence). All existing sync tests must pass.

---

## Phase 8: Adapter Simplification

Phase 8 reduces the 24 adapter files to approximately 12 by replacing 13 simple adapters with data-driven `AdapterConfig` instances. Complex adapters with custom logic remain as class files. The registration order is preserved to maintain FK dependency ordering.

**Depends on**: Phase 5 (SyncEngine slim coordinator complete)

**Verification gate**: All characterization tests green, all existing sync tests green via CI, `flutter analyze` zero violations, adapter count reduced from 24 to ~12.

---

### Sub-phase 8.1: Create AdapterConfig data class

**Files:**
- Create: `lib/features/sync/adapters/adapter_config.dart`
- Test: `test/features/sync/adapters/adapter_config_test.dart`

**Agent**: backend-supabase-agent

#### Step 8.1.1: Write AdapterConfig test (RED)

```dart
// test/features/sync/adapters/adapter_config_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/sync/adapters/adapter_config.dart';
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

void main() {
  group('AdapterConfig', () {
    test('generates a TableAdapter with correct tableName and scope', () {
      // WHY: The generated adapter must be equivalent to ContractorAdapter.
      final config = AdapterConfig(
        table: 'contractors',
        scope: ScopeType.viaProject,
        fkDeps: const ['projects'],
        fkColumnMap: const {'projects': 'project_id'},
      );
      final adapter = config.toAdapter();

      expect(adapter.tableName, 'contractors');
      expect(adapter.scopeType, ScopeType.viaProject);
      expect(adapter.fkDependencies, ['projects']);
      expect(adapter.fkColumnMap, {'projects': 'project_id'});
    });

    test('defaults match TableAdapter base class defaults', () {
      final config = AdapterConfig(
        table: 'test_table',
        scope: ScopeType.direct,
        fkDeps: const [],
      );
      final adapter = config.toAdapter();

      expect(adapter.supportsSoftDelete, isTrue);
      expect(adapter.isFileAdapter, isFalse);
      expect(adapter.insertOnly, isFalse);
      expect(adapter.skipPull, isFalse);
      expect(adapter.skipIntegrityCheck, isFalse);
      expect(adapter.includesNullProjectBuiltins, isFalse);
      expect(adapter.stripExifGps, isFalse);
      expect(adapter.storageBucket, '');
      expect(adapter.converters, isEmpty);
      expect(adapter.naturalKeyColumns, isEmpty);
      expect(adapter.localOnlyColumns, isEmpty);
      expect(adapter.userStampColumns, isEmpty);
    });

    test('supports file adapter fields', () {
      // WHY: EntryExportAdapter is classified as simple because buildStoragePath
      // uses a standard pattern. But actually it has a CUSTOM buildStoragePath,
      // so it stays as a class. This test verifies config CAN express file fields
      // for potential future simple file adapters.
      final config = AdapterConfig(
        table: 'simple_files',
        scope: ScopeType.viaEntry,
        fkDeps: const ['daily_entries'],
        isFileAdapter: true,
        storageBucket: 'simple-files',
      );
      final adapter = config.toAdapter();

      expect(adapter.isFileAdapter, isTrue);
      expect(adapter.storageBucket, 'simple-files');
    });

    test('supports custom converters', () {
      // WHY: ProjectAdapter has BoolIntConverter on is_active.
      final config = AdapterConfig(
        table: 'projects',
        scope: ScopeType.direct,
        fkDeps: const [],
        converters: const {'is_active': BoolIntConverter()},
        naturalKeyColumns: const ['company_id', 'project_number'],
      );
      final adapter = config.toAdapter();

      expect(adapter.converters, isNotEmpty);
      expect(adapter.converters.containsKey('is_active'), isTrue);
      expect(adapter.naturalKeyColumns, ['company_id', 'project_number']);
    });

    test('supports custom extractRecordName', () {
      final config = AdapterConfig(
        table: 'entry_quantities',
        scope: ScopeType.viaEntry,
        fkDeps: const ['daily_entries', 'bid_items'],
        fkColumnMap: const {'daily_entries': 'entry_id', 'bid_items': 'bid_item_id'},
        extractRecordName: (record) =>
            'Quantity: ${record['quantity'] ?? record['id'] ?? 'Unknown'}',
      );
      final adapter = config.toAdapter();

      expect(
        adapter.extractRecordName({'quantity': '5.0', 'id': 'abc'}),
        'Quantity: 5.0',
      );
    });
  });
}
```

#### Step 8.1.2: Implement AdapterConfig

```dart
// lib/features/sync/adapters/adapter_config.dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

/// Data-driven configuration for simple table adapters.
///
/// FROM SPEC Section 3 (Adapter Simplification): 13 simple adapters become
/// AdapterConfig instances. Each config generates a TableAdapter via [toAdapter].
///
/// WHY: 13 of 22 adapter files are pure configuration with zero custom logic
/// beyond property overrides. Declaring them as data reduces 13 class files to
/// a single list of configs, cutting adapter file count from 24 to ~12.
class AdapterConfig {
  /// The SQLite/Supabase table name (must match exactly).
  final String table;

  /// How this table is scoped to the company tenant.
  final ScopeType scope;

  /// Tables that must be pushed before this one (FK parents).
  final List<String> fkDeps;

  /// Maps parent table name -> local FK column name for per-record blocking.
  final Map<String, String> fkColumnMap;

  /// Column-level type converters.
  final Map<String, TypeConverter> converters;

  /// Whether this table supports soft-delete.
  final bool supportsSoftDelete;

  /// Whether this adapter handles file uploads.
  final bool isFileAdapter;

  /// Storage bucket name for file adapters.
  final String storageBucket;

  /// Whether to strip EXIF GPS data.
  final bool stripExifGps;

  /// Whether this table is insert-only.
  final bool insertOnly;

  /// Whether to skip pull for this table.
  final bool skipPull;

  /// Whether to skip integrity checks.
  final bool skipIntegrityCheck;

  /// Columns that should be stamped with the current user ID before push.
  final Map<String, String> userStampColumns;

  /// Natural key columns for UNIQUE constraint pre-check.
  final List<String> naturalKeyColumns;

  /// Whether this table includes builtin records with null project_id.
  final bool includesNullProjectBuiltins;

  /// Columns that exist locally but should NOT be sent to Supabase.
  final List<String> localOnlyColumns;

  /// Custom extractRecordName function. If null, uses TableAdapter default.
  final String Function(Map<String, dynamic> record)? extractRecordName;

  const AdapterConfig({
    required this.table,
    required this.scope,
    required this.fkDeps,
    this.fkColumnMap = const {},
    this.converters = const {},
    this.supportsSoftDelete = true,
    this.isFileAdapter = false,
    this.storageBucket = '',
    this.stripExifGps = false,
    this.insertOnly = false,
    this.skipPull = false,
    this.skipIntegrityCheck = false,
    this.userStampColumns = const {},
    this.naturalKeyColumns = const [],
    this.includesNullProjectBuiltins = false,
    this.localOnlyColumns = const [],
    this.extractRecordName,
  });

  /// Generates a concrete TableAdapter instance from this configuration.
  TableAdapter toAdapter() => _ConfiguredAdapter(this);
}

/// A TableAdapter generated from an AdapterConfig.
///
/// WHY: Implements all TableAdapter overrides by reading from the config.
/// No custom logic — pure delegation to data fields.
class _ConfiguredAdapter extends TableAdapter {
  final AdapterConfig _config;

  _ConfiguredAdapter(this._config);

  @override
  String get tableName => _config.table;

  @override
  ScopeType get scopeType => _config.scope;

  @override
  List<String> get fkDependencies => _config.fkDeps;

  @override
  Map<String, String> get fkColumnMap => _config.fkColumnMap;

  @override
  Map<String, TypeConverter> get converters => _config.converters;

  @override
  bool get supportsSoftDelete => _config.supportsSoftDelete;

  @override
  bool get isFileAdapter => _config.isFileAdapter;

  @override
  String get storageBucket => _config.storageBucket;

  @override
  bool get stripExifGps => _config.stripExifGps;

  @override
  bool get insertOnly => _config.insertOnly;

  @override
  bool get skipPull => _config.skipPull;

  @override
  bool get skipIntegrityCheck => _config.skipIntegrityCheck;

  @override
  Map<String, String> get userStampColumns => _config.userStampColumns;

  @override
  List<String> get naturalKeyColumns => _config.naturalKeyColumns;

  @override
  bool get includesNullProjectBuiltins => _config.includesNullProjectBuiltins;

  @override
  List<String> get localOnlyColumns => _config.localOnlyColumns;

  @override
  String extractRecordName(Map<String, dynamic> record) {
    if (_config.extractRecordName != null) {
      return _config.extractRecordName!(record);
    }
    return super.extractRecordName(record);
  }
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/adapters/adapter_config.dart"` -- expected: 0 issues found.

#### Step 8.1.3: Run AdapterConfig test (GREEN)

**Verify**: CI run targets `test/features/sync/adapters/adapter_config_test.dart` -- expected: all tests pass.

---

### Sub-phase 8.2: Define simple adapter configs and update registry

**Files:**
- Create: `lib/features/sync/adapters/simple_adapters.dart` (the 13 AdapterConfig declarations)
- Modify: `lib/features/sync/engine/sync_registry.dart` (use AdapterConfig for simple adapters)

**Agent**: backend-supabase-agent

#### Step 8.2.1: Create simple_adapters.dart

This file declares the 13 simple adapter configurations, replacing 13 separate class files.

IMPORTANT: Before implementing, the implementing agent MUST read each of the 13 adapter files to verify that every override is captured in the config. The tailor analysis classified these as simple, but some have `extractRecordName` overrides or `naturalKeyColumns` that must be preserved.

Based on actual source review, here is what each "simple" adapter actually needs:

| Adapter | Extra Overrides Beyond table/scope/fkDeps |
|---------|-------------------------------------------|
| ContractorAdapter | fkColumnMap |
| LocationAdapter | fkColumnMap |
| BidItemAdapter | fkColumnMap, **extractRecordName** (custom: item_number + description) |
| PersonnelTypeAdapter | naturalKeyColumns (project_id, semantic_name). NOTE: no fkColumnMap override |
| EntryContractorsAdapter | fkColumnMap, naturalKeyColumns |
| EntryPersonnelCountsAdapter | fkColumnMap, **extractRecordName** |
| EntryQuantitiesAdapter | fkColumnMap, **extractRecordName** |
| TodoItemAdapter | converters (BoolIntConverter, TodoPriorityConverter), **extractRecordName** |
| ProjectAdapter | converters (BoolIntConverter), naturalKeyColumns |
| ProjectAssignmentAdapter | (none beyond fkDependencies) |
| EntryExportAdapter | **Complex** -- has custom buildStoragePath, extractRecordName, localOnlyColumns, isFileAdapter. Must REMAIN as class. |
| FormExportAdapter | **Complex** -- has custom buildStoragePath, extractRecordName. Must REMAIN as class. |
| CalculationHistoryAdapter | converters (JsonMapConverter x2), **extractRecordName** |

REVISION: EntryExportAdapter and FormExportAdapter have custom `buildStoragePath()` methods with path construction logic. These cannot be expressed as simple config fields. They must remain as class files.

Revised count: **11 simple adapters** become configs, **11 complex adapters** remain as classes. File count: 24 -> ~14 (still a meaningful reduction).

```dart
// lib/features/sync/adapters/simple_adapters.dart
import 'package:construction_inspector/features/sync/adapters/adapter_config.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

/// Data-driven configurations for simple table adapters.
///
/// FROM SPEC Section 3 (Adapter Simplification): These adapters have no custom
/// logic beyond property overrides. Each generates a TableAdapter at registration.
///
/// IMPORTANT: Registration order MUST match FK dependency order. The sync engine
/// processes tables in this order for push (FK parents first) and pull.
/// FROM SPEC: sync_registry.dart:29-54 — registerSyncAdapters() order is load-bearing.
const simpleAdapters = <AdapterConfig>[
  // WHY: Projects is the root table — no FK dependencies.
  // FROM SPEC: ProjectAdapter (project_adapter.dart)
  AdapterConfig(
    table: 'projects',
    scope: ScopeType.direct,
    fkDeps: [],
    converters: {'is_active': BoolIntConverter()},
    naturalKeyColumns: ['company_id', 'project_number'],
  ),

  // WHY: project_assignments depends on projects existing first.
  // FROM SPEC: ProjectAssignmentAdapter (project_assignment_adapter.dart)
  AdapterConfig(
    table: 'project_assignments',
    scope: ScopeType.direct,
    fkDeps: ['projects'],
  ),

  // FROM SPEC: LocationAdapter (location_adapter.dart)
  AdapterConfig(
    table: 'locations',
    scope: ScopeType.viaProject,
    fkDeps: ['projects'],
    fkColumnMap: {'projects': 'project_id'},
  ),

  // FROM SPEC: ContractorAdapter (contractor_adapter.dart)
  AdapterConfig(
    table: 'contractors',
    scope: ScopeType.viaProject,
    fkDeps: ['projects'],
    fkColumnMap: {'projects': 'project_id'},
  ),

  // FROM SPEC: BidItemAdapter (bid_item_adapter.dart)
  // NOTE: Custom extractRecordName uses item_number + description.
  AdapterConfig(
    table: 'bid_items',
    scope: ScopeType.viaProject,
    fkDeps: ['projects'],
    fkColumnMap: {'projects': 'project_id'},
    extractRecordName: _extractBidItemName,
  ),

  // FROM SPEC: PersonnelTypeAdapter (personnel_type_adapter.dart)
  AdapterConfig(
    table: 'personnel_types',
    scope: ScopeType.viaProject,
    fkDeps: ['projects', 'contractors'],
    naturalKeyColumns: ['project_id', 'semantic_name'],
  ),

  // FROM SPEC: EntryContractorsAdapter (entry_contractors_adapter.dart)
  AdapterConfig(
    table: 'entry_contractors',
    scope: ScopeType.viaEntry,
    fkDeps: ['daily_entries', 'contractors'],
    fkColumnMap: {'daily_entries': 'entry_id', 'contractors': 'contractor_id'},
    naturalKeyColumns: ['entry_id', 'contractor_id'],
  ),

  // FROM SPEC: EntryPersonnelCountsAdapter (entry_personnel_counts_adapter.dart)
  AdapterConfig(
    table: 'entry_personnel_counts',
    scope: ScopeType.viaEntry,
    fkDeps: ['daily_entries', 'contractors', 'personnel_types'],
    fkColumnMap: {
      'daily_entries': 'entry_id',
      'contractors': 'contractor_id',
      'personnel_types': 'type_id',
    },
    extractRecordName: _extractPersonnelCountName,
  ),

  // FROM SPEC: EntryQuantitiesAdapter (entry_quantities_adapter.dart)
  AdapterConfig(
    table: 'entry_quantities',
    scope: ScopeType.viaEntry,
    fkDeps: ['daily_entries', 'bid_items'],
    fkColumnMap: {'daily_entries': 'entry_id', 'bid_items': 'bid_item_id'},
    extractRecordName: _extractQuantityName,
  ),

  // FROM SPEC: TodoItemAdapter (todo_item_adapter.dart)
  AdapterConfig(
    table: 'todo_items',
    scope: ScopeType.viaProject,
    fkDeps: ['projects'],
    converters: {
      'is_completed': BoolIntConverter(),
      'priority': TodoPriorityConverter(),
    },
    extractRecordName: _extractTodoName,
  ),

  // FROM SPEC: CalculationHistoryAdapter (calculation_history_adapter.dart)
  AdapterConfig(
    table: 'calculation_history',
    scope: ScopeType.viaProject,
    fkDeps: ['projects'],
    converters: {
      'input_data': JsonMapConverter(),
      'result_data': JsonMapConverter(),
    },
    extractRecordName: _extractCalcHistoryName,
  ),
];

// --- extractRecordName functions ---
// WHY: These match the exact logic from each adapter's extractRecordName override.

String _extractBidItemName(Map<String, dynamic> record) {
  final itemNumber = record['item_number']?.toString() ?? '';
  final description = record['description']?.toString() ?? '';
  if (itemNumber.isNotEmpty && description.isNotEmpty) {
    return '$itemNumber - $description';
  }
  return itemNumber.isNotEmpty
      ? itemNumber
      : description.isNotEmpty
          ? description
          : record['id']?.toString() ?? 'Unknown';
}

String _extractPersonnelCountName(Map<String, dynamic> record) {
  return 'Personnel count: ${record['count'] ?? record['id'] ?? 'Unknown'}';
}

String _extractQuantityName(Map<String, dynamic> record) {
  return 'Quantity: ${record['quantity'] ?? record['id'] ?? 'Unknown'}';
}

String _extractTodoName(Map<String, dynamic> record) {
  return record['title']?.toString() ??
      record['id']?.toString() ??
      'Unknown';
}

String _extractCalcHistoryName(Map<String, dynamic> record) {
  return record['calc_type']?.toString() ??
      record['id']?.toString() ??
      'Unknown';
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/adapters/simple_adapters.dart"` -- expected: 0 issues found.

#### Step 8.2.2: Update sync_registry.dart to use AdapterConfig

Modify `lib/features/sync/engine/sync_registry.dart` to:
1. Import `simple_adapters.dart` and `adapter_config.dart`
2. Replace the 11 simple adapter class instantiations with `AdapterConfig.toAdapter()` calls
3. Keep the 11 complex adapter class instantiations unchanged
4. Maintain the exact same FK dependency order

```dart
// lib/features/sync/engine/sync_registry.dart — updated registerSyncAdapters()
import 'package:construction_inspector/features/sync/adapters/adapter_config.dart';
import 'package:construction_inspector/features/sync/adapters/simple_adapters.dart';
// ... keep imports for 11 complex adapters ...
import 'package:construction_inspector/features/sync/adapters/equipment_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/daily_entry_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/photo_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/entry_equipment_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/inspector_form_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/form_response_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/form_export_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/entry_export_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/document_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/support_ticket_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/consent_record_adapter.dart';

/// Register all table adapters in FK dependency order.
///
/// FROM SPEC: Simple adapters use data-driven AdapterConfig.
/// Complex adapters retain class files due to custom logic.
///
/// IMPORTANT: Order is load-bearing. FK parents must come before children.
void registerSyncAdapters() {
  // WHY: Generate TableAdapter instances from simple configs.
  // The config order in simpleAdapters already respects FK dependencies
  // for the simple subset, but we must interleave with complex adapters
  // to maintain the full FK order.
  final simpleByTable = {
    for (final config in simpleAdapters) config.table: config.toAdapter(),
  };

  SyncRegistry.instance.registerAdapters([
    // FROM SPEC: Exact order from sync_registry.dart:30-53
    simpleByTable['projects']!,             // was: ProjectAdapter()
    simpleByTable['project_assignments']!,  // was: ProjectAssignmentAdapter()
    simpleByTable['locations']!,            // was: LocationAdapter()
    simpleByTable['contractors']!,          // was: ContractorAdapter()
    EquipmentAdapter(),                     // COMPLEX: converters with custom logic
    simpleByTable['bid_items']!,            // was: BidItemAdapter()
    simpleByTable['personnel_types']!,      // was: PersonnelTypeAdapter()
    DailyEntryAdapter(),                    // COMPLEX: userStampColumns, extractRecordName
    PhotoAdapter(),                         // COMPLEX: validate, buildStoragePath, extractRecordName
    EntryEquipmentAdapter(),                // COMPLEX: converters
    simpleByTable['entry_quantities']!,     // was: EntryQuantitiesAdapter()
    simpleByTable['entry_contractors']!,    // was: EntryContractorsAdapter()
    simpleByTable['entry_personnel_counts']!, // was: EntryPersonnelCountsAdapter()
    InspectorFormAdapter(),                 // COMPLEX: shouldSkipPush, includesNullProjectBuiltins
    FormResponseAdapter(),                  // COMPLEX: jsonb converters
    FormExportAdapter(),                    // COMPLEX: custom buildStoragePath
    EntryExportAdapter(),                   // COMPLEX: custom buildStoragePath
    DocumentAdapter(),                      // COMPLEX: custom buildStoragePath, file adapter
    simpleByTable['todo_items']!,           // was: TodoItemAdapter()
    simpleByTable['calculation_history']!,  // was: CalculationHistoryAdapter()
    SupportTicketAdapter(),                 // COMPLEX: custom pullFilter, skipIntegrityCheck
    ConsentRecordAdapter(),                 // COMPLEX: custom pullFilter, insertOnly, skipPull
  ]);
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/sync/engine/sync_registry.dart"` -- expected: 0 issues found.

---

### Sub-phase 8.3: Delete simple adapter files

**Files:**
- Delete: `lib/features/sync/adapters/contractor_adapter.dart`
- Delete: `lib/features/sync/adapters/location_adapter.dart`
- Delete: `lib/features/sync/adapters/bid_item_adapter.dart`
- Delete: `lib/features/sync/adapters/personnel_type_adapter.dart`
- Delete: `lib/features/sync/adapters/entry_contractors_adapter.dart`
- Delete: `lib/features/sync/adapters/entry_personnel_counts_adapter.dart`
- Delete: `lib/features/sync/adapters/entry_quantities_adapter.dart`
- Delete: `lib/features/sync/adapters/todo_item_adapter.dart`
- Delete: `lib/features/sync/adapters/project_adapter.dart`
- Delete: `lib/features/sync/adapters/project_assignment_adapter.dart`
- Delete: `lib/features/sync/adapters/calculation_history_adapter.dart`

**Agent**: backend-supabase-agent

#### Step 8.3.1: Delete 11 simple adapter files

Delete the 11 files listed above. These are fully replaced by the `simpleAdapters` list in `simple_adapters.dart`.

After deletion, verify no remaining imports reference the deleted files.

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues found (no broken imports).

#### Step 8.3.2: Update barrel exports

If `lib/features/sync/adapters/` has a barrel export file, update it to:
- Remove exports for the 11 deleted adapter files
- Add export for `adapter_config.dart` and `simple_adapters.dart`
- Keep exports for the 11 remaining complex adapter files

---

### Sub-phase 8.4: Verify equivalence

**Agent**: general-purpose

#### Step 8.4.1: Run characterization tests

Run all push and pull characterization tests to verify that the data-driven adapters produce identical behavior to the class-based adapters.

**Verify**: CI green on all characterization tests.

#### Step 8.4.2: Run full analyzer and test suite

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues found.

#### Step 8.4.3: Verify file count

Count files in `lib/features/sync/adapters/`:
- `table_adapter.dart` (base class)
- `type_converters.dart` (shared converters)
- `adapter_config.dart` (config data class)
- `simple_adapters.dart` (11 configs)
- 11 complex adapter class files

Total: 15 files (down from 24). The spec target of "~12" was aspirational; 15 is the correct count given that EntryExportAdapter and FormExportAdapter have custom `buildStoragePath()` logic.

---

## Phase 9: Integration + Documentation

Phase 9 performs end-to-end integration verification using the test driver infrastructure and updates all sync-related documentation to reflect the new architecture.

**Depends on**: Phase 7 (layer violations fixed) and Phase 8 (adapters simplified)

**Verification gate**: All 10 test driver flows pass, all documentation updated, `flutter analyze` zero violations, CI green.

---

### Sub-phase 9.1: Integration Verification via Test Driver

**Files:**
- Modify/Create: `.claude/test-flows/sync/` flow definitions

**Agent**: general-purpose

The following 10 test driver flows verify the complete refactored system end-to-end. Each flow is executed via the HTTP test driver infrastructure (`lib/core/driver/driver_server.dart`, `main_driver.dart`). Flows use 2 devices (or 2 app instances) to verify sync round-trips.

#### Step 9.1.1: Flow 1 — Create-Sync-Verify

**Purpose**: Verify that creating data on Device A and syncing to Device B produces identical results.

**Steps**:
1. Device A: Create a fresh project via UI (POST /driver/create-project or UI automation)
2. Device A: Create a daily entry with photos, forms, and quantities
3. Device A: Trigger sync via POST /driver/sync -> GET /driver/sync-status to confirm completion
4. Device B: Trigger sync via POST /driver/sync
5. Device B: Verify every field matches exactly: project name, entry date, photo filenames, form response data, quantity values, GPS data, timestamps
6. Verify via GET /driver/local-record for both devices

**Success criteria**: Every field on Device B matches Device A exactly, including `created_at` and `updated_at` timestamps.

#### Step 9.1.2: Flow 2 — Edit-Conflict-Resolve

**Purpose**: Verify LWW conflict resolution works correctly after refactor.

**Steps**:
1. Both devices sync to baseline state
2. Device A: Edit entry field X (e.g., weather_notes), sync
3. Device B: Edit same entry field X (different value) + field Y (e.g., traffic_notes), sync
4. Both sync again to resolve
5. Verify: Field X has the value from the device with the newer `updated_at` (LWW)
6. Verify: conflict_log entry exists for the LWW resolution
7. Verify: Loser's field X data is preserved in conflict_log

**Success criteria**: LWW winner correct, conflict_log populated, no data loss.

#### Step 9.1.3: Flow 3 — Delete-Sync-Verify

**Purpose**: Verify soft-delete propagates through the refactored sync.

**Steps**:
1. Device A: Create entry, sync
2. Device B: Sync to receive entry
3. Device A: Soft-delete the entry, sync
4. Device B: Sync
5. Verify: Entry has `deleted_at` set on both devices
6. Verify: Deletion notification created on Device B
7. Verify: Entry filtered from normal reads on both devices

**Success criteria**: Soft-delete round-trips, deletion notification created.

#### Step 9.1.4: Flow 4 — File-Sync-Roundtrip

**Purpose**: Verify three-phase file upload, EXIF stripping, and download work after FileSyncHandler extraction.

**Steps**:
1. Device A: Attach a photo with GPS EXIF data to an entry
2. Device A: Sync
3. Verify: Storage path follows `entries/{companyId}/{entryId}/{filename}` pattern
4. Verify: EXIF GPS stripped in cloud storage copy (download and inspect)
5. Verify: Local `remote_path` bookmark updated
6. Device B: Sync
7. Verify: Photo downloads to Device B with correct metadata

**Success criteria**: File uploads, EXIF stripped, bookmark correct, round-trip complete.

#### Step 9.1.5: Flow 5 — Quick-Sync-Dirty-Scope

**Purpose**: Verify dirty scope filtering works after DirtyScopeTracker extraction.

**Steps**:
1. Both devices at baseline
2. Trigger a realtime hint for a specific project+table (via Supabase Realtime or FCM mock)
3. Trigger quick sync on Device A
4. Verify: Only the dirty scope (specific project+table) was pulled, not all tables
5. Verify: DirtyScopeTracker scopes consumed after pull

**Success criteria**: Quick sync pulls only dirty scopes.

#### Step 9.1.6: Flow 6 — Enrollment-Flow

**Purpose**: Verify auto-enrollment from project_assignments works after EnrollmentHandler extraction.

**Steps**:
1. Device A is enrolled in Project-1 only
2. Admin assigns Device A's user to Project-2 via Supabase (INSERT into project_assignments)
3. Device A: Full sync
4. Verify: synced_projects now includes Project-2
5. Verify: Project-2 data begins pulling on next sync
6. Verify: Enrollment notification queued in SyncProvider

**Success criteria**: Auto-enrollment works, data pulls for new project.

#### Step 9.1.7: Flow 7 — Circuit-Breaker-Recovery

**Purpose**: Verify circuit breaker trips and recovery work after SyncControlService extraction.

**Steps**:
1. Create a conflict scenario that will ping-pong (both devices edit same field repeatedly)
2. Sync back and forth until conflict count exceeds `conflictPingPongThreshold` (3)
3. Verify: Circuit breaker trips, `circuitBreakerTripped` flag set in SyncProvider
4. Dismiss circuit breaker via UI or SyncProvider.dismissCircuitBreaker()
5. Verify: Sync resumes, circuit breaker flag cleared

**Success criteria**: CB trips at threshold, dismissal works, sync resumes.

#### Step 9.1.8: Flow 8 — Resume-Stale-ForcedSync

**Purpose**: Verify SyncTriggerPolicy's stale-data decision on app resume.

**Steps**:
1. Sync successfully
2. Manually advance the `last_sync_time` in sync_metadata to 25h ago
3. Simulate app resume (WidgetsBindingObserver.didChangeAppLifecycleState(resumed))
4. If online: Verify a forced full sync is triggered
5. If DNS unreachable: Verify stale data warning emitted, no sync triggered

**Success criteria**: Stale threshold triggers forced sync when online, warning when offline.

#### Step 9.1.9: Flow 9 — Hint-While-Syncing

**Purpose**: Verify that realtime hints arriving mid-sync are retained and trigger exactly one follow-up quick sync.

**Steps**:
1. Start a full sync on Device A
2. While sync is in progress, trigger a realtime hint (Supabase Realtime or mock)
3. Verify: Dirty scope is marked in DirtyScopeTracker
4. Verify: Hint does not trigger a sync (already in progress)
5. After full sync completes, verify: Exactly one follow-up quick sync runs for the dirty scope

**Success criteria**: Hint retained, exactly one follow-up sync, no overlap.

#### Step 9.1.10: Flow 10 — Retry-Exhaustion-Recovery

**Purpose**: Verify SyncRetryPolicy's exhaustion behavior and background retry scheduling.

**Steps**:
1. Make the backend unreachable (DNS block or kill Supabase)
2. Trigger sync
3. Verify: Sync retries up to maxRetries (3) with exponential backoff
4. Verify: After exhaustion, background retry timer scheduled (60s)
5. Restore backend connectivity
6. Trigger manual sync (should cancel background timer)
7. Verify: Manual sync succeeds, timer cancelled

**Success criteria**: Retry exhaustion, background timer scheduled, manual sync cancels timer.

---

### Sub-phase 9.2: Update sync-patterns.md

**Files:**
- Modify: `.claude/rules/sync/sync-patterns.md`

**Agent**: general-purpose

#### Step 9.2.1: Full rewrite of sync-patterns.md

Rewrite `.claude/rules/sync/sync-patterns.md` to reflect the new architecture:

1. **Layer Diagram**: Update to show the new class structure:
   - Presentation: SyncProvider (subscribes to SyncStatus, reads SyncQueryService)
   - Application: SyncCoordinator, SyncLifecycleManager, SyncRetryPolicy, ConnectivityProbe, SyncTriggerPolicy, PostSyncHooks, SyncQueryService, BackgroundSyncHandler, FcmHandler, RealtimeHintHandler
   - Engine: SyncEngine (slim coordinator), PushHandler, PullHandler, SupabaseSync, LocalSyncStore, FileSyncHandler, SyncErrorClassifier, EnrollmentHandler, FkRescueHandler, MaintenanceHandler
   - Existing engine: ChangeTracker, ConflictResolver, IntegrityChecker, DirtyScopeTracker, OrphanScanner, StorageCleanup, SyncMutex, SyncRegistry
   - Adapters: AdapterConfig (11 simple), 11 complex adapter classes, TableAdapter base
   - Domain: SyncResult, SyncStatus, SyncErrorKind, ClassifiedSyncError, SyncDiagnosticsSnapshot, SyncEvent, SyncMode, DirtyScope

2. **Data Flow**: Update push/pull flow diagrams to show PushHandler/PullHandler routing through SupabaseSync and LocalSyncStore

3. **Class Relationships**: New dependency diagram showing injected dependencies

4. **Engine Components Table**: Add all new classes with file paths and purposes

5. **Application Layer Table**: Replace SyncOrchestrator with SyncCoordinator and add all new control-plane classes

6. **Adapter Section**: Document the AdapterConfig data-driven pattern and list which adapters are simple vs complex

7. **Status vs Diagnostics Split**: Document the SyncStatus / SyncDiagnosticsSnapshot / SyncEvent separation

8. **Error Classification**: Document that SyncErrorClassifier is the single source of truth

9. **File Organization**: Update the directory tree

10. **Enforced Invariants**: Add the new testability guarantees from spec section 4.7

---

### Sub-phase 9.3: Update CLAUDE.md

**Files:**
- Modify: `.claude/CLAUDE.md`

**Agent**: general-purpose

#### Step 9.3.1: Update Sync Architecture section

Update the Sync Architecture section in `.claude/CLAUDE.md`:

```
## Sync Architecture
```
Presentation: SyncProvider, SyncDashboardScreen, ConflictViewerScreen
Application:  SyncCoordinator, SyncLifecycleManager, SyncRetryPolicy, ConnectivityProbe, SyncTriggerPolicy, PostSyncHooks, SyncQueryService, BackgroundSyncHandler, FcmHandler, RealtimeHintHandler
Engine:       SyncEngine (slim), PushHandler, PullHandler, SupabaseSync, LocalSyncStore, FileSyncHandler, SyncErrorClassifier, EnrollmentHandler, FkRescueHandler, MaintenanceHandler
Unchanged:    ChangeTracker, ConflictResolver, IntegrityChecker, DirtyScopeTracker, OrphanScanner, StorageCleanup, SyncMutex
Adapters:     11 AdapterConfig (data-driven) + 11 complex classes (22 total; declare FK ordering + scope type)
Domain:       SyncResult, SyncStatus, SyncErrorKind, ClassifiedSyncError, SyncDiagnosticsSnapshot, SyncEvent, SyncMode, DirtyScope
```

Update the Key Files table to add:
- `lib/features/sync/application/sync_coordinator.dart` -- Replaces SyncOrchestrator
- `lib/features/sync/application/sync_query_service.dart` -- Dashboard query surface
- `lib/features/sync/adapters/simple_adapters.dart` -- 11 data-driven adapter configs

Update Gotchas to note:
- SyncOrchestrator no longer exists -- use SyncCoordinator
- SyncProvider no longer exposes `get orchestrator` -- use SyncQueryService for dashboard data
- Error classification is in SyncErrorClassifier only -- no Postgres code matching elsewhere

---

### Sub-phase 9.4: Update directory-reference.md

**Files:**
- Modify: `.claude/docs/directory-reference.md`

**Agent**: general-purpose

#### Step 9.4.1: Update sync directory listing

Update the sync feature directory listing to reflect:
- New files in `engine/` (push_handler.dart, pull_handler.dart, supabase_sync.dart, local_sync_store.dart, file_sync_handler.dart, sync_error_classifier.dart, enrollment_handler.dart, fk_rescue_handler.dart, maintenance_handler.dart)
- New files in `application/` (sync_coordinator.dart, sync_retry_policy.dart, connectivity_probe.dart, sync_trigger_policy.dart, post_sync_hooks.dart, sync_query_service.dart)
- New files in `domain/` (sync_status.dart, sync_error.dart, sync_diagnostics.dart, sync_event.dart)
- New files in `adapters/` (adapter_config.dart, simple_adapters.dart)
- Deleted files in `adapters/` (11 simple adapter files)
- Deleted file: `sync_orchestrator.dart` (replaced by sync_coordinator.dart)

---

### Sub-phase 9.5: Create sync architecture guide

**Files:**
- Create: `.claude/docs/guides/implementation/sync-architecture.md`

**Agent**: general-purpose

#### Step 9.5.1: Write new sync architecture guide

Create `.claude/docs/guides/implementation/sync-architecture.md` as a durable guide covering:

1. **Overview**: Engine layer (I/O boundaries, handlers, slim coordinator), control plane (retry, connectivity, triggers, hooks), status vs diagnostics split, adapter data-driven pattern

2. **Engine Layer**:
   - SupabaseSync: All Supabase row I/O (upsert, delete, select, auth refresh, rate limit)
   - LocalSyncStore: All sync SQLite I/O (record reads/writes, cursor mgmt, trigger suppression, column cache)
   - PushHandler: Change_log -> FK-ordered -> route per record -> SupabaseSync
   - PullHandler: Adapter iteration -> scope filter -> paginate -> LocalSyncStore
   - FileSyncHandler: Three-phase upload + EXIF strip
   - SyncErrorClassifier: Single error classification source
   - EnrollmentHandler: Project enrollment from assignments
   - FkRescueHandler: Missing FK parent fetch
   - MaintenanceHandler: Integrity, orphan, pruning
   - SyncEngine: Slim coordinator (mutex, heartbeat, mode routing)

3. **Control Plane**:
   - SyncCoordinator: Entry point for sync requests, owns retry loop
   - SyncRetryPolicy: Retryability, backoff, background scheduling
   - ConnectivityProbe: DNS/health checks
   - SyncTriggerPolicy: Lifecycle/stale/hint -> sync mode
   - PostSyncHooks: App-level follow-up (profile refresh, config)
   - SyncQueryService: Dashboard queries (pending buckets, integrity, conflicts)

4. **Status vs Diagnostics**:
   - SyncStatus = transport state (uploading/downloading, connectivity, last sync)
   - SyncDiagnosticsSnapshot = operational state (pending, integrity, conflicts)
   - SyncEvent = transient lifecycle signals

5. **Testing Strategy**:
   - Characterization tests (Layer 1) — behavior contracts
   - Interface contract tests (Layer 2) — TDD before implementation
   - Equivalence testing (Layer 3) — per-extraction CI gate
   - Isolation tests (Layer 4) ��� per-class deep coverage
   - Integration verification (Layer 5) — 10 test driver flows

6. **Adapter Pattern**:
   - AdapterConfig for simple adapters (11)
   - Class files for complex adapters (11)
   - Registration order = FK dependency order

---

### Sub-phase 9.6: Final Verification

**Agent**: general-purpose

#### Step 9.6.1: Run full analyzer

**Verify**: `pwsh -Command "flutter analyze"` -- expected: 0 issues found.

#### Step 9.6.2: Run full CI suite

Push branch, open PR, verify CI green:
- All characterization tests pass
- All contract tests pass
- All isolation tests pass
- All existing tests pass
- Analyzer zero violations

#### Step 9.6.3: Verify success metrics

Check against spec section 8 success metrics:

| Metric | Before | Target | Verify |
|--------|--------|--------|--------|
| SyncEngine lines | 2,374 | <250 | `wc -l lib/features/sync/engine/sync_engine.dart` |
| Largest sync class | 2,374 | <500 | Check all new files |
| `@visibleForTesting` methods | 9 | 0 | `grep -r '@visibleForTesting' lib/features/sync/` |
| Adapter files | 24 | ~15 | `ls lib/features/sync/adapters/ \| wc -l` |
| Status sources of truth | 3 | 1 | Verify only SyncStatus exists |
| Error classifier locations | 3 | 1 | Verify only SyncErrorClassifier |
| Untestable code paths | 6 | 0 | All have dedicated tests |

#### Step 9.6.4: Merge PR

After all verification passes, merge the Phase 9 PR. This is the final phase of the sync engine refactor.

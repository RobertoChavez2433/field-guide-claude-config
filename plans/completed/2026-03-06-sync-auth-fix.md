# Sync "No Auth Context" Fix — Implementation Plan

**Date**: 2026-03-06
**Branch**: `feat/sync-engine-rewrite`
**Files affected**: 2 (sync_orchestrator.dart, sync_provider.dart)
**Risk**: Low — targeted surgical changes with no schema or API surface changes

---

## Executive Summary

The error "No auth context available for sync" persists through app restarts because of two cooperating bugs:

1. `_isTransientError()` contains `'auth'` and `'Auth'` in `nonTransientPatterns`. Because the error message "No auth context available for sync" contains 'auth', `_syncWithRetry()` classifies the failure as permanent and exits immediately — the FIX-A polling loop inside `_createEngine()` never gets a second chance on the next retry cycle.

2. The polling window in `_createEngine()` is 5 seconds (`maxWait`). `loadUserProfile()` in `AuthProvider` makes up to 3 sequential Supabase calls (profile fetch → optional migration upsert → company fetch). On a cold start with moderate network latency (>1.5s/call), 5 seconds is routinely exhausted before `setAdapterCompanyContext()` is called.

3. `SyncProvider.sync()` has no auth guard — a manual sync tap before the profile resolves runs through the full error path and latches the failure state into `_consecutiveFailures`.

The three fixes are independent and can be applied atomically in one commit.

---

## Call Chain (Annotated)

```
AppLifecycleState.resumed
  └─ SyncLifecycleManager._handleResumed()                     [sync_lifecycle_manager.dart:74]
       └─ _triggerDnsAwareSync(forced: true)                   [sync_lifecycle_manager.dart:119]
            └─ _triggerForcedSync()                            [sync_lifecycle_manager.dart:144]
                 └─ syncOrchestrator.syncLocalAgencyProjects() [sync_orchestrator.dart:203]
                      └─ _syncWithRetry()                      [sync_orchestrator.dart:268]
                           └─ _doSync()                        [sync_orchestrator.dart:324]
                                └─ _createEngine()             [sync_orchestrator.dart:163]
                                     └─ polls 5s, still null
                                     └─ returns null
                                └─ returns SyncResult(error: 'No auth context available for sync')
                           └─ _isTransientError(result)        [sync_orchestrator.dart:353]
                                └─ msg.contains('auth') → returns false  ← BUG (line 366)
                           └─ returns immediately (no retry)
```

---

## Phase 1 — Fix `_isTransientError()` misclassification

**File**: `lib/features/sync/application/sync_orchestrator.dart`
**Location**: `_isTransientError()` method, starting at line 353

### Problem

The `nonTransientPatterns` list at line 365–376 contains `'auth'` and `'Auth'`. The error message `'No auth context available for sync'` (emitted at line 335 in `_doSync()`) matches `'auth'`, causing the entire retry mechanism to short-circuit.

The original intent of the `'auth'` pattern was to catch genuine Supabase auth failures (expired token, 401, RLS violation). A missing-context error is structurally different: auth IS valid, but the context object hasn't been populated yet by the async `loadUserProfile()` call. It is inherently transient.

### Change

Add an early-return guard at the top of `_isTransientError()`, before the pattern loop, that explicitly marks the no-context error as transient.

**Current code** (`sync_orchestrator.dart:353–392`):
```dart
bool _isTransientError(SyncResult result) {
  final transientPatterns = [
    'DNS',
    'dns',
    'SocketException',
    'host lookup',
    'TimeoutException',
    'Connection refused',
    'Connection reset',
    'Network is unreachable',
    'offline',
  ];
  final nonTransientPatterns = [
    'auth',
    'Auth',
    'RLS',
    ...
  ];

  for (final msg in result.errorMessages) {
    // If any non-transient pattern matches, don't retry
    for (final pattern in nonTransientPatterns) {
      if (msg.contains(pattern)) return false;
    }
    ...
  }
  return true;
}
```

**Replacement**:
```dart
bool _isTransientError(SyncResult result) {
  // FIX: "No auth context" is a transient startup race — auth IS valid but
  // the companyId/userId hasn't been populated by loadUserProfile() yet.
  // Guard this BEFORE the nonTransientPatterns loop, which contains 'auth'.
  const noContextMsg = 'No auth context available for sync';
  if (result.errorMessages.any((m) => m.contains(noContextMsg))) {
    DebugLogger.sync('_isTransientError: no-context error treated as transient');
    return true;
  }

  final transientPatterns = [
    'DNS',
    'dns',
    'SocketException',
    'host lookup',
    'TimeoutException',
    'Connection refused',
    'Connection reset',
    'Network is unreachable',
    'offline',
  ];
  final nonTransientPatterns = [
    'auth',
    'Auth',
    'RLS',
    'permission',
    'Permission',
    'not configured',
    'already in progress',
    'has no column',
    'DatabaseException',
    'no such column',
    'table has no column',
  ];

  for (final msg in result.errorMessages) {
    for (final pattern in nonTransientPatterns) {
      if (msg.contains(pattern)) return false;
    }
    for (final pattern in transientPatterns) {
      if (msg.contains(pattern)) return true;
    }
  }

  return true;
}
```

**Exact insertion point**: After the method signature `bool _isTransientError(SyncResult result) {` at line 353, before line 354 (`final transientPatterns = [`).

---

## Phase 2 — Increase `_createEngine()` polling window

**File**: `lib/features/sync/application/sync_orchestrator.dart`
**Location**: `_createEngine()` method, line 169

### Problem

`loadUserProfile()` in `AuthProvider` (auth_provider.dart:453) makes up to 3 sequential network calls:
1. `_authService.loadUserProfile(uid)` — fetches the user_profiles row
2. (conditional) `_authService.updateUserProfile(migrated)` — migration upsert if legacy prefs exist
3. `_authService.getCompanyById(companyId)` — fetches the company row if not cached locally

Each call has no explicit timeout in AuthService. On a cold start where the device is resuming from a sleep state with a slow radio (common on Android), each call can take 2–4 seconds. Three calls at 3s each = 9 seconds — well beyond the current 5-second cap.

The fix increases `maxWait` to 15 seconds, which covers the worst-case 3-call chain with margin. This is safe because `_createEngine()` is only invoked inside `_doSync()`, which is already called from a background-aware context (SyncLifecycleManager or BackgroundSyncHandler).

### Change

**Current code** (`sync_orchestrator.dart:169`):
```dart
const maxWait = Duration(seconds: 5);
```

**Replacement**:
```dart
// FIX: loadUserProfile() makes up to 3 sequential Supabase calls
// (profile + optional migration upsert + company fetch). On cold start
// with slow radio, this can exceed 5s. Use 15s to cover worst-case.
const maxWait = Duration(seconds: 15);
```

Also update the adjacent log message at line 173:
```dart
// Current:
DebugLogger.sync('SyncOrchestrator: Auth context missing, waiting up to 5s...');

// Replacement:
DebugLogger.sync('SyncOrchestrator: Auth context missing, waiting up to 15s...');
```

---

## Phase 3 — Gate `SyncProvider.sync()` behind auth readiness

**File**: `lib/features/sync/presentation/providers/sync_provider.dart`
**Location**: `sync()` method, line 160

### Problem

`SyncProvider.sync()` (line 160–162) calls straight through to `syncLocalAgencyProjects()` with no check on whether auth context is ready. If a user taps the manual sync button during the brief window when `loadUserProfile()` is still in flight, the call returns `'No auth context available for sync'`, increments `_consecutiveFailures`, and — after two such taps — shows the persistent error toast.

After Phase 1 and 2 land, the retry logic will handle this automatically from lifecycle-triggered syncs. However, the manual sync path bypasses `_syncWithRetry()` indirectly (it calls `syncLocalAgencyProjects()` which calls `_syncWithRetry()` internally — so it IS retried). The real problem is UX: the user receives no feedback that the system is still warming up.

### Change

Add an `authContextReady` callback to `SyncProvider` that `main.dart` wires to `AuthProvider`. If the context is not ready, return a silent no-op result and optionally surface a user-friendly message via the existing `onSyncErrorToast` callback.

**SyncProvider additions**:
```dart
/// Returns true if the auth context (companyId + userId) is ready for sync.
/// Wired in main.dart via [setAuthReadinessCheck].
bool Function()? _authReadinessCheck;

/// Wire in the auth readiness check from main.dart.
void setAuthReadinessCheck(bool Function() check) {
  _authReadinessCheck = check;
}

/// Trigger a manual sync via SyncOrchestrator.
/// Returns a silent no-op if auth context is not yet ready (startup race guard).
Future<SyncResult> sync() async {
  final isReady = _authReadinessCheck?.call() ?? true;
  if (!isReady) {
    DebugLogger.sync('SyncProvider.sync(): auth not ready, deferring manual sync');
    // Optional: surface a brief status message to the user
    onSyncErrorToast?.call('Sign-in completing — please try again in a moment');
    return const SyncResult();  // silent no-op, no error counted
  }
  return await _syncOrchestrator.syncLocalAgencyProjects();
}
```

**main.dart wiring** (after line 309 where `authProvider.addListener(updateSyncContext)` is called):
```dart
// Wire auth readiness check to SyncProvider so manual sync taps during
// loadUserProfile() do not increment consecutiveFailures.
// Access SyncProvider lazily to avoid creation-order issues.
// The readiness check mirrors syncLifecycleManager.isReadyForSync.
// Note: SyncProvider is created inside MultiProvider; wire after runApp via
// a post-frame callback registered on the navigator observer, OR inject the
// check directly into SyncOrchestrator as an alternative.
```

Note: Because `SyncProvider` is created inside `MultiProvider` in `ConstructionInspectorApp.build()` (main.dart:700–711), and `authProvider` exists before `runApp()`, the cleanest wiring approach is to add the `authReadinessCheck` to `SyncOrchestrator` instead (which is accessible before `runApp()`), and have `SyncOrchestrator.syncLocalAgencyProjects()` check it before calling `_syncWithRetry()`.

**Revised approach — add guard to `SyncOrchestrator` instead**:

In `sync_orchestrator.dart`, add to `syncLocalAgencyProjects()` at line 203:
```dart
Future<SyncResult> syncLocalAgencyProjects() async {
  // FIX: If the auth context provider says context is not ready (companyId still
  // loading), return a silent no-op instead of entering the retry loop and
  // accumulating failure counts.
  final ctx = _syncContextProvider?.call();
  final hasContext = ctx?.companyId != null && ctx?.userId != null;
  if (!hasContext && _companyId == null) {
    DebugLogger.sync('SyncOrchestrator: auth context not ready, skipping sync cycle');
    return const SyncResult(); // silent no-op, does NOT set error status
  }

  _updateStatus(SyncAdapterStatus.syncing);
  // ... rest of existing method
```

This approach requires no changes to `SyncProvider` or `main.dart` wiring and achieves the same outcome: manual sync taps during the startup window return a clean empty result, not an error.

---

## Files to Modify

| File | Lines changed | Purpose |
|------|--------------|---------|
| `lib/features/sync/application/sync_orchestrator.dart` | ~15 lines | Fix 1 (transient guard), Fix 2 (maxWait), Fix 3 (context guard) |
| `lib/features/sync/presentation/providers/sync_provider.dart` | 0 lines | No change required if Fix 3 is applied in orchestrator |

---

## Implementation Order

Apply in this order to minimize risk of merge conflicts:

1. **Fix 2 first** (change `maxWait` from 5 to 15 seconds) — one-line change, trivially reversible
2. **Fix 1 second** (add no-context early-return guard in `_isTransientError`) — 8 lines, isolated method
3. **Fix 3 last** (add context guard at top of `syncLocalAgencyProjects`) — 6 lines, depends on understanding Fix 1 behavior first

All three changes are in `sync_orchestrator.dart` and can be applied in a single edit session.

---

## Exact Code Changes (Copy-Ready)

### Change A — `_createEngine()` maxWait (line 169)

```
OLD:  const maxWait = Duration(seconds: 5);
NEW:  const maxWait = Duration(seconds: 15);
```

### Change B — `_createEngine()` log message (line 173)

```
OLD:  DebugLogger.sync('SyncOrchestrator: Auth context missing, waiting up to 5s...');
NEW:  DebugLogger.sync('SyncOrchestrator: Auth context missing, waiting up to 15s...');
```

### Change C — `_isTransientError()` early guard (insert after line 353)

Insert immediately after `bool _isTransientError(SyncResult result) {`:

```dart
    // FIX-1: "No auth context available for sync" is a transient startup race —
    // auth is valid but companyId/userId hasn't been populated by
    // loadUserProfile() yet. Evaluate BEFORE the nonTransientPatterns loop
    // which contains 'auth', or this error will be misclassified as permanent.
    const noContextMsg = 'No auth context available for sync';
    if (result.errorMessages.any((m) => m.contains(noContextMsg))) {
      DebugLogger.sync('_isTransientError: no-context error → transient (startup race)');
      return true;
    }
```

### Change D — `syncLocalAgencyProjects()` context guard (insert after line 204)

Insert immediately after `_updateStatus(SyncAdapterStatus.syncing);`:

```dart
    // FIX-3: If both the inline context fields AND the context provider
    // report no companyId, auth is still loading. Return a silent no-op
    // to avoid accumulating failure counts on manual sync taps during startup.
    if (_companyId == null) {
      final ctx = _syncContextProvider?.call();
      if (ctx?.companyId == null) {
        _updateStatus(SyncAdapterStatus.idle);
        DebugLogger.sync('SyncOrchestrator: auth context not yet ready, skipping cycle');
        return const SyncResult();
      }
    }
```

---

## Verification Checklist

### Unit Tests (existing, must still pass)
- [ ] `flutter test` — all tests green (no regressions)

### Manual Scenarios to Test

**Scenario 1: Cold start on slow network**
1. Kill app
2. Disable WiFi (force slow cellular or throttle in dev options)
3. Launch app
4. Observe: app opens, auth loads within 15s, sync completes silently
5. Observe: logs show "Auth context resolved after wait" (not "No auth context available")

**Scenario 2: Resume after background**
1. Send app to background for 25+ hours (or force lastSyncTime to be stale)
2. Resume
3. Observe: forced sync triggers, completes without "No auth context" error

**Scenario 3: Manual sync tap during startup**
1. Launch app on slow network
2. Immediately navigate to the sync screen and tap manual sync
3. Observe: no error toast, no error count increment
4. Observe: second tap after profile loads succeeds

**Scenario 4: Genuine auth failure still blocked**
1. Invalidate the Supabase session (delete row in auth.users from dashboard)
2. Resume app
3. Observe: sync fails, `_isTransientError()` still returns `false` for real auth errors (e.g., "JWT expired")
4. Observe: no retry loops on permanent auth failure

**Log Markers to Watch**
```
[SYNC] SyncOrchestrator: Auth context missing, waiting up to 15s...
[SYNC] SyncOrchestrator: Auth context resolved after wait
[SYNC] _isTransientError: no-context error → transient (startup race)
[SYNC] SyncOrchestrator: auth context not yet ready, skipping cycle
```

---

## Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| 15s polling delay blocks foreground sync visibly | Low | Medium | Polling is async with 500ms intervals; UI is not blocked. Lifecycle sync happens in background. |
| No-context early-return masks a real auth outage | Low | High | The guard uses the exact string 'No auth context available for sync', which is only emitted from `_doSync()` line 335 when `_createEngine()` returns null — not from Supabase auth errors. Real auth errors have different messages ('JWT expired', '401', etc). |
| Fix 3 context guard swallows errors permanently | Low | Medium | The guard only fires when `_companyId == null` AND `_syncContextProvider` also reports null. Once `setAdapterCompanyContext()` is called by the `authProvider.addListener` hook in main.dart, `_companyId` is non-null and the guard is never entered again. |
| maxWait increase delays failure detection | Very Low | Low | The 15s wait only applies when companyId IS null. If Supabase itself is down, DNS check fails before `_createEngine()` is reached. |
| Regression in retry behavior | Low | Medium | All three changes are additive guards, not restructuring. `_syncWithRetry()` loop logic is unchanged. |

---

## Rollback Plan

All changes are in a single file (`sync_orchestrator.dart`). To rollback:
- Revert `maxWait` from `Duration(seconds: 15)` to `Duration(seconds: 5)`
- Remove the `noContextMsg` early-return block from `_isTransientError()`
- Remove the context guard from `syncLocalAgencyProjects()`

No database migrations, no schema changes, no provider interface changes required.

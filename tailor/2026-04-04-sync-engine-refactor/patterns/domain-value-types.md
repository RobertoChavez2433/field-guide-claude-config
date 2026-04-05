# Pattern: Domain Value Types

## How We Do It

The sync domain layer uses immutable value classes with `const` constructors, `copyWith()` methods using sentinel patterns, and operator overloading (`+`) for combining results. All types are in `lib/features/sync/domain/sync_types.dart`. The refactor adds 4 new domain types in separate files.

## Exemplar: SyncResult

```dart
// lib/features/sync/domain/sync_types.dart:4-66
class SyncResult {
  final int pushed;
  final int pulled;
  final int errors;
  final List<String> errorMessages;
  final int rlsDenials;
  final int skippedPush;

  const SyncResult({
    this.pushed = 0,
    this.pulled = 0,
    this.errors = 0,
    this.errorMessages = const [],
    this.rlsDenials = 0,
    this.skippedPush = 0,
  });

  bool get hasErrors => errors > 0;
  int get total => pushed + pulled;
  bool get isSuccess => !hasErrors;

  static const _sentinel = Object();

  SyncResult copyWith({
    Object? pushed = _sentinel,
    Object? pulled = _sentinel,
    Object? errors = _sentinel,
    Object? errorMessages = _sentinel,
    Object? rlsDenials = _sentinel,
    Object? skippedPush = _sentinel,
  }) {
    return SyncResult(
      pushed: identical(pushed, _sentinel) ? this.pushed : pushed! as int,
      // ... etc
    );
  }

  SyncResult operator +(SyncResult other) {
    return SyncResult(
      pushed: pushed + other.pushed,
      pulled: pulled + other.pulled,
      errors: errors + other.errors,
      errorMessages: [...errorMessages, ...other.errorMessages],
      rlsDenials: rlsDenials + other.rlsDenials,
      skippedPush: skippedPush + other.skippedPush,
    );
  }
}
```

## Exemplar: DirtyScope

```dart
// lib/features/sync/domain/sync_types.dart:83-109
@immutable
class DirtyScope {
  final String? projectId;
  final String? tableName;
  final DateTime markedAt;

  const DirtyScope({this.projectId, this.tableName, required this.markedAt});

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is DirtyScope &&
          runtimeType == other.runtimeType &&
          projectId == other.projectId &&
          tableName == other.tableName;

  @override
  int get hashCode => Object.hash(projectId, tableName);

  bool get isCompanyWide => projectId == null;
  bool get isAllTables => tableName == null;
}
```

## Exemplar: SyncEngineResult (Engine-Internal)

```dart
// lib/features/sync/engine/sync_engine.dart:35-73
class SyncEngineResult {
  final int pushed;
  final int pulled;
  final int errors;
  final List<String> errorMessages;
  final bool lockFailed;
  final int rlsDenials;
  final int conflicts;
  final int skippedFk;
  final int skippedPush;

  const SyncEngineResult({ /* all defaulted */ });

  bool get hasErrors => errors > 0;
  bool get isSuccess => !hasErrors && !lockFailed && conflicts == 0;

  SyncEngineResult operator +(SyncEngineResult other) { /* combines all fields */ }
}
```

**Note**: SyncEngineResult is a superset of SyncResult. SyncOrchestrator converts SyncEngineResult → SyncResult. The refactor replaces both with the unified SyncStatus stream.

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| SyncResult.copyWith | sync_types.dart:27 | `SyncResult copyWith({...})` | Immutable updates |
| SyncResult.+ | sync_types.dart:52 | `SyncResult operator +(SyncResult other)` | Combining push + pull results |
| SyncEngineResult.+ | sync_engine.dart:61 | `SyncEngineResult operator +(SyncEngineResult other)` | Combining results within engine |

## New Domain Types (from spec)

| Type | File | Purpose |
|------|------|---------|
| `SyncStatus` | `domain/sync_status.dart` | Immutable transport state, replaces triple tracking |
| `SyncErrorKind` | `domain/sync_error.dart` | Error category enum |
| `ClassifiedSyncError` | `domain/sync_error.dart` | Rich error with retry/auth/UI metadata |
| `SyncDiagnosticsSnapshot` | `domain/sync_diagnostics.dart` | Dashboard/query operational state |
| `SyncEvent` | `domain/sync_event.dart` | Typed lifecycle signals |

All new types should follow the existing pattern: `const` constructor, `@immutable`, `==`/`hashCode` where equality matters, `copyWith` where mutation is needed.

## Imports

```dart
import 'package:flutter/foundation.dart';
import 'package:construction_inspector/features/sync/domain/sync_types.dart';
```

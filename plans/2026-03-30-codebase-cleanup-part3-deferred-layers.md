# Codebase Cleanup Part 3: Deferred Implementations + Layer Violation Fixes

**Date:** 2026-03-30
**Size:** L (5 phases, ~25 files touched)
**Branch:** `cleanup/deferred-layer-fixes`

---

## Phase 11: Layer Violation Fixes

### Sub-phase 11.1: DeletionNotificationBanner — Extract Raw SQL to Datasource + Repository

**Files:**
- Create: `lib/features/sync/data/datasources/local/deletion_notification_local_datasource.dart`
- Create: `lib/features/sync/data/repositories/deletion_notification_repository.dart`
- Modify: `lib/features/sync/presentation/widgets/deletion_notification_banner.dart`
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart` (wire injection)
- Test: `test/features/sync/data/datasources/deletion_notification_local_datasource_test.dart`
- Test: `test/features/sync/presentation/widgets/deletion_notification_banner_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 11.1.1: Create DeletionNotificationLocalDatasource

Create `lib/features/sync/data/datasources/local/deletion_notification_local_datasource.dart`:

```dart
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';

/// Datasource for deletion_notifications table.
///
/// WHY: Extracted from DeletionNotificationBanner to eliminate raw SQL in presentation layer.
/// Does NOT extend GenericLocalDatasource — non-standard API (no CRUD, no soft-delete).
class DeletionNotificationLocalDatasource {
  final DatabaseService _dbService;

  DeletionNotificationLocalDatasource(this._dbService);

  /// Get unseen deletion notifications (up to [limit]), newest first.
  ///
  /// Returns empty list if table doesn't exist (first-run startup race).
  Future<List<Map<String, dynamic>>> getUnseenNotifications({int limit = 10}) async {
    try {
      final db = await _dbService.database;
      return await db.query(
        'deletion_notifications',
        where: 'seen = 0',
        orderBy: 'deleted_at DESC',
        limit: limit,
      );
    } catch (e) {
      // WHY: Table may not exist yet during first run — known startup race
      if (e.toString().contains('no such table')) {
        Logger.db('deletion_notifications table not ready: $e');
        return [];
      }
      Logger.db('DeletionNotificationLocalDatasource.getUnseenNotifications: $e');
      return [];
    }
  }

  /// Mark all unseen notifications as seen.
  Future<void> markAllAsSeen() async {
    try {
      final db = await _dbService.database;
      await db.update(
        'deletion_notifications',
        {'seen': 1},
        where: 'seen = 0',
      );
    } catch (e) {
      Logger.db('DeletionNotificationLocalDatasource.markAllAsSeen: $e');
    }
  }
}
```

#### Step 11.1.2: Create DeletionNotificationRepository

Create `lib/features/sync/data/repositories/deletion_notification_repository.dart`:

```dart
import '../datasources/local/deletion_notification_local_datasource.dart';

/// Repository for deletion notifications shown after sync.
///
/// WHY: Thin wrapper to complete the data layer hierarchy.
/// Does NOT implement BaseRepository — non-standard API (no save/getAll/delete).
class DeletionNotificationRepository {
  final DeletionNotificationLocalDatasource _datasource;

  DeletionNotificationRepository(this._datasource);

  /// Get unseen notifications (up to [limit]).
  Future<List<Map<String, dynamic>>> getUnseenNotifications({int limit = 10}) {
    return _datasource.getUnseenNotifications(limit: limit);
  }

  /// Mark all notifications as seen (dismiss action).
  Future<void> markAllAsSeen() {
    return _datasource.markAllAsSeen();
  }
}
```

#### Step 11.1.3: Wire repository and refactor DeletionNotificationBanner

Modify `lib/features/sync/presentation/widgets/deletion_notification_banner.dart`:

1. Remove `import 'package:construction_inspector/core/database/database_service.dart';`
2. Add `import 'package:construction_inspector/features/sync/data/repositories/deletion_notification_repository.dart';`
3. Replace `_loadNotifications()` body (lines 37-56):
```dart
Future<void> _loadNotifications() async {
  // WHY: Delegates to repository instead of raw SQL in presentation layer
  final repo = context.read<DeletionNotificationRepository>();
  final results = await repo.getUnseenNotifications();
  if (mounted) {
    setState(() => _unseenNotifications = results);
  }
}
```
4. Replace `_dismiss()` body (lines 59-73):
```dart
Future<void> _dismiss() async {
  // WHY: Delegates to repository instead of raw SQL in presentation layer
  final repo = context.read<DeletionNotificationRepository>();
  await repo.markAllAsSeen();
  if (mounted) {
    setState(() => _dismissed = true);
  }
}
```
5. Remove the two `// TODO: Extract to repository` comments (lines 38, 61).

Wire the repository into the Provider tree — add to the sync providers or `app_initializer.dart` where `DatabaseService` is available. The `DeletionNotificationRepository` needs to be registered as a `Provider<DeletionNotificationRepository>` above where `DeletionNotificationBanner` is used.

#### Step 11.1.4: Test

Create unit test for datasource:
```dart
// test/features/sync/data/datasources/deletion_notification_local_datasource_test.dart
// Test getUnseenNotifications returns empty list when table missing
// Test getUnseenNotifications returns results ordered by deleted_at DESC
// Test markAllAsSeen sets seen=1 on all unseen rows
```

Run: `pwsh -Command "flutter test test/features/sync/data/datasources/deletion_notification_local_datasource_test.dart"`

---

### Sub-phase 11.2: ConflictViewerScreen — Extract Raw SQL to Datasource

**Files:**
- Create: `lib/features/sync/data/datasources/local/conflict_local_datasource.dart`
- Create: `lib/features/sync/data/repositories/conflict_repository.dart`
- Modify: `lib/features/sync/presentation/screens/conflict_viewer_screen.dart`
- Test: `test/features/sync/data/datasources/conflict_local_datasource_test.dart`
- Test: `test/features/sync/presentation/screens/conflict_viewer_screen_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 11.2.1: Create ConflictLocalDatasource

Create `lib/features/sync/data/datasources/local/conflict_local_datasource.dart`:

```dart
import 'dart:convert';
import 'package:sqflite/sqflite.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/sync/engine/sync_registry.dart';

/// Datasource for the conflict_log table.
///
/// WHY: Extracted from ConflictViewerScreen to eliminate 6 raw SQL calls in presentation layer.
/// SECURITY: restoreConflict validates tableName against SyncRegistry.knownTableNames
/// to prevent arbitrary table writes from tampered conflict_log data.
class ConflictLocalDatasource {
  final DatabaseService _dbService;
  final SyncRegistry _syncRegistry;

  ConflictLocalDatasource(this._dbService, this._syncRegistry);

  /// Allowed table names for restore operations.
  /// WHY: SECURITY — prevents arbitrary table writes from tampered conflict_log data.
  Set<String> get _knownTableNames =>
      _syncRegistry.adapters.map((a) => a.tableName).toSet();

  /// Get all unresolved conflicts, newest first.
  Future<List<Map<String, dynamic>>> getUnresolvedConflicts() async {
    final db = await _dbService.database;
    return db.query(
      'conflict_log',
      where: 'dismissed_at IS NULL',
      orderBy: 'detected_at DESC',
    );
  }

  /// Dismiss a conflict by setting dismissed_at.
  Future<void> dismissConflict(int conflictId) async {
    final db = await _dbService.database;
    await db.update(
      'conflict_log',
      {'dismissed_at': DateTime.now().toUtc().toIso8601String()},
      where: 'id = ?',
      whereArgs: [conflictId],
    );
  }

  /// Restore lost data from a conflict record into the target table.
  ///
  /// SECURITY: Validates [tableName] against SyncRegistry's known tables.
  /// Strips protected columns (company_id, role, status, created_by_user_id,
  /// id, deleted_at, deleted_by, updated_at, updated_by_user_id) to prevent
  /// privilege escalation or ownership tampering.
  ///
  /// Throws [ArgumentError] if tableName is not in SyncRegistry.
  /// Throws [StateError] if the target record has been permanently deleted.
  /// Throws [FormatException] if lostDataJson is null/empty or malformed.
  Future<void> restoreConflict({
    required int conflictId,
    required String tableName,
    required String recordId,
    required String? lostDataJson,
  }) async {
    // WHY: SECURITY — validate tableName against known sync tables
    if (!_knownTableNames.contains(tableName)) {
      throw ArgumentError(
        'ConflictLocalDatasource: tableName "$tableName" not in SyncRegistry. '
        'Refusing to write to unknown table.',
      );
    }

    if (lostDataJson == null || lostDataJson.isEmpty) {
      throw const FormatException('No lost data available to restore.');
    }

    final lostData = jsonDecode(lostDataJson) as Map<String, dynamic>;
    final db = await _dbService.database;

    // Read current record
    final records = await db.query(
      tableName,
      where: 'id = ?',
      whereArgs: [recordId],
    );

    if (records.isEmpty) {
      throw StateError(
        'This record has been permanently deleted and cannot be restored.',
      );
    }

    final currentRecord = Map<String, dynamic>.from(records.first);

    // WHY: Strip protected columns from lostData before merge to prevent
    // privilege escalation or ownership tampering (Phase 6 HIGH finding).
    final strippedLostData = Map<String, dynamic>.from(lostData)
      ..remove('company_id')
      ..remove('role')
      ..remove('status')
      ..remove('created_by_user_id')
      ..remove('id')
      ..remove('deleted_at')
      ..remove('deleted_by')
      ..remove('updated_at')
      ..remove('updated_by_user_id');

    // Merge stripped lost_data into current record
    final merged = {...currentRecord, ...strippedLostData};

    // Validate via adapter (validate throws on invalid data)
    final adapter = _syncRegistry.adapterFor(tableName);
    await adapter.validate(merged);

    // Apply merged data
    await db.update(
      tableName,
      merged,
      where: 'id = ?',
      whereArgs: [recordId],
    );

    // Mark conflict as dismissed
    await dismissConflict(conflictId);

    Logger.sync('[ConflictLocalDatasource] restored conflict $conflictId '
        'table=$tableName record=$recordId');
  }
}
```

#### Step 11.2.2: Create ConflictRepository

Create `lib/features/sync/data/repositories/conflict_repository.dart`:

```dart
import '../datasources/local/conflict_local_datasource.dart';

/// Repository for sync conflict resolution.
///
/// WHY: Thin wrapper around ConflictLocalDatasource.
/// Does NOT implement BaseRepository — non-standard API.
class ConflictRepository {
  final ConflictLocalDatasource _datasource;

  ConflictRepository(this._datasource);

  Future<List<Map<String, dynamic>>> getUnresolvedConflicts() {
    return _datasource.getUnresolvedConflicts();
  }

  Future<void> dismissConflict(int conflictId) {
    return _datasource.dismissConflict(conflictId);
  }

  /// Restore lost data. Throws on validation failure, missing record, or unknown table.
  Future<void> restoreConflict({
    required int conflictId,
    required String tableName,
    required String recordId,
    required String? lostDataJson,
  }) {
    return _datasource.restoreConflict(
      conflictId: conflictId,
      tableName: tableName,
      recordId: recordId,
      lostDataJson: lostDataJson,
    );
  }
}
```

#### Step 11.2.3: Refactor ConflictViewerScreen

Modify `lib/features/sync/presentation/screens/conflict_viewer_screen.dart`:

1. Remove imports: `import 'package:sqflite/sqflite.dart';`, `import '../../engine/sync_registry.dart';`
2. Remove: `import 'package:construction_inspector/core/database/database_service.dart';`
3. Add: `import 'package:construction_inspector/features/sync/data/repositories/conflict_repository.dart';`
4. Remove `_getDatabase()` method (line 32-34) and `_syncRegistry` getter (line 37)
5. Replace `_loadConflicts()` (lines 45-64):
```dart
Future<void> _loadConflicts() async {
  try {
    // WHY: Delegates to repository instead of raw SQL in presentation layer
    final repo = context.read<ConflictRepository>();
    final results = await repo.getUnresolvedConflicts();
    if (mounted) {
      setState(() {
        _conflicts = results;
        _isLoading = false;
      });
    }
  } catch (e) {
    Logger.sync('[ConflictViewer] loadConflicts error: $e');
    if (mounted) {
      setState(() => _isLoading = false);
    }
  }
}
```
6. Replace `_dismissConflict()` (lines 67-82):
```dart
Future<void> _dismissConflict(Map<String, dynamic> conflict) async {
  try {
    final repo = context.read<ConflictRepository>();
    await repo.dismissConflict(conflict['id'] as int);
    await _loadConflicts();
  } catch (e) {
    if (mounted) {
      SnackBarHelper.showError(context, 'Failed to dismiss: $e');
    }
  }
}
```
7. Replace `_restoreConflict()` (lines 84-163):
```dart
Future<void> _restoreConflict(Map<String, dynamic> conflict) async {
  try {
    final repo = context.read<ConflictRepository>();
    await repo.restoreConflict(
      conflictId: conflict['id'] as int,
      tableName: conflict['table_name'] as String,
      recordId: conflict['record_id'] as String,
      lostDataJson: conflict['lost_data'] as String?,
    );
    await _loadConflicts();
    if (mounted) {
      SnackBarHelper.showSuccess(context, 'Conflict resolved — data restored.');
    }
  } on ArgumentError catch (e) {
    _showError('Security error: ${e.message}');
  } on StateError catch (e) {
    _showError(e.message);
  } on FormatException catch (e) {
    _showError(e.message);
  } catch (e) {
    _showError('Restore failed: $e');
  }
}
```

Wire `ConflictRepository` into the Provider tree alongside `DeletionNotificationRepository`.

#### Step 11.2.4: Test

Create unit test for ConflictLocalDatasource:
```dart
// test/features/sync/data/datasources/conflict_local_datasource_test.dart
// Test getUnresolvedConflicts returns only non-dismissed conflicts
// Test dismissConflict sets dismissed_at
// Test restoreConflict rejects unknown tableName (ArgumentError)
// Test restoreConflict strips protected columns before merge
// Test restoreConflict throws StateError when record permanently deleted
// Test restoreConflict throws FormatException when lostDataJson is empty
```

Run: `pwsh -Command "flutter test test/features/sync/data/datasources/conflict_local_datasource_test.dart"`

---

### Sub-phase 11.3: FormQuickActionRegistry — Remove BuildContext from Data Layer

**Files:**
- Modify: `lib/features/forms/data/registries/form_quick_action_registry.dart`
- Modify: Any callers of `FormQuickAction.execute` (search for `.execute(`)
- Test: `test/features/forms/data/registries/form_quick_action_registry_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 11.3.1: Replace BuildContext with Action Descriptor

Modify `lib/features/forms/data/registries/form_quick_action_registry.dart`:

1. Remove `import 'package:flutter/material.dart';` — replace with `import 'package:flutter/widgets.dart';` (still need `IconData`)
2. Replace `FormQuickAction` class:
```dart
/// Descriptor for a quick action that the presentation layer interprets.
///
/// WHY: Data layer must not take BuildContext. The execute callback returns
/// a FormQuickActionResult that the presentation layer interprets (navigate,
/// show dialog, etc.).
class FormQuickAction {
  final IconData icon;
  final String label;

  /// Returns a route path or action descriptor. The presentation layer
  /// is responsible for navigation/dialog display.
  final FormQuickActionResult Function(FormResponse response) execute;

  const FormQuickAction({
    required this.icon,
    required this.label,
    required this.execute,
  });
}

/// Result from executing a quick action.
/// WHY: Decouples data layer from Flutter navigation. Presentation layer
/// interprets the result type and performs the appropriate action.
class FormQuickActionResult {
  final FormQuickActionType type;
  final String? routePath;
  final Map<String, String>? queryParameters;

  const FormQuickActionResult({
    required this.type,
    this.routePath,
    this.queryParameters,
  });

  const FormQuickActionResult.navigate({
    required String route,
    Map<String, String>? params,
  })  : type = FormQuickActionType.navigate,
        routePath = route,
        queryParameters = params;

  const FormQuickActionResult.noOp()
      : type = FormQuickActionType.noOp,
        routePath = null,
        queryParameters = null;
}

enum FormQuickActionType { navigate, noOp }
```

#### Step 11.3.2: Update All Callers

Search for all callers of `FormQuickAction.execute` and update them to:
1. Call `action.execute(response)` (no BuildContext)
2. Interpret the `FormQuickActionResult` — if `type == navigate`, call `context.push(result.routePath!, queryParameters: result.queryParameters)`

Also update any `FormQuickAction` registrations that currently capture `BuildContext` in their `execute` callback — change them to return `FormQuickActionResult.navigate(...)` instead.

#### Step 11.3.3: Test

Run: `pwsh -Command "flutter test test/features/forms/"`

---

### Sub-phase 11.4: Auth Layer — Wrap Supabase Exceptions + Constructor Injection Fixes

**Files:**
- Modify: `lib/features/auth/presentation/providers/auth_provider.dart` (line 431 — wrap AuthException)
- Modify: `lib/features/auth/presentation/screens/update_password_screen.dart` (catch domain exception)
- Modify: `lib/features/auth/data/repositories/user_attribution_repository.dart` (line 77 — inject SupabaseClient)
- Modify: `lib/features/projects/data/services/project_lifecycle_service.dart` (line 362 — use injected client)
- Test: `test/features/auth/presentation/providers/auth_provider_test.dart`

**Agent**: `auth-agent`

#### Step 11.4.1: Wrap AuthException in AuthProvider.resetPassword

In `lib/features/auth/presentation/providers/auth_provider.dart`, the `resetPassword` method (line 431) catches `AuthException` directly. This is acceptable for now since `AuthProvider` already imports `supabase_flutter` for `AuthState` and `User` types.

**Note as tech debt:** Full domain auth type abstraction (M14/M15) would require:
- Creating `lib/features/auth/domain/models/auth_state.dart` wrapping Supabase `AuthState`
- Creating `lib/features/auth/domain/exceptions/auth_exception.dart`
- Mapping in `AuthService`

This is out of scope for this cleanup. The current import is a known deviation documented in the codebase.

For `update_password_screen.dart` (line 4 imports `supabase_flutter` for `AuthException`):

Modify `lib/features/auth/presentation/providers/auth_provider.dart` — wrap the `updatePassword` method so it catches `AuthException` and rethrows as a domain-level exception:

```dart
/// Update the current user's password during a recovery flow.
///
/// WHY: Wraps AuthService.updatePassword to catch Supabase-specific exceptions
/// and rethrow as domain exceptions so screens don't import supabase_flutter.
Future<void> updatePassword(String newPassword) async {
  try {
    await _authService.updatePassword(newPassword);
  } on AuthException catch (e) {
    // WHY: Map Supabase exceptions to user-friendly messages
    if (e.message.contains('expired') || e.message.contains('session')) {
      throw PasswordUpdateException(
        'Your recovery session has expired. Please request a new reset link.',
        isExpired: true,
      );
    }
    throw PasswordUpdateException(AuthErrorParser.parse(e.message));
  }
}
```

Create a simple domain exception class in `lib/features/auth/domain/exceptions/password_update_exception.dart`:

```dart
/// Domain exception for password update failures.
/// WHY: Screens catch this instead of importing supabase_flutter for AuthException.
class PasswordUpdateException implements Exception {
  final String message;
  final bool isExpired;

  const PasswordUpdateException(this.message, {this.isExpired = false});

  @override
  String toString() => message;
}
```

Then modify `update_password_screen.dart` to:
1. Remove `import 'package:supabase_flutter/supabase_flutter.dart';`
2. Add `import 'package:construction_inspector/features/auth/domain/exceptions/password_update_exception.dart';`
3. Replace `on AuthException catch (e)` with `on PasswordUpdateException catch (e)` — use `e.isExpired` for the expired-link detection logic.

#### Step 11.4.2: UserAttributionRepository — Inject SupabaseClient

Modify `lib/features/auth/data/repositories/user_attribution_repository.dart`:

Replace line 77 (`final client = Supabase.instance.client;`) with constructor injection:

```dart
class UserAttributionRepository {
  final SupabaseClient? _client;

  // WHY: Constructor injection replaces Supabase.instance.client inline usage.
  // Nullable because client may not be configured in offline/mock mode.
  UserAttributionRepository({SupabaseClient? client}) : _client = client;

  // ... existing _cache field ...

  Future<String> _fetchFromRemote(String userId) async {
    if (_client == null) return 'Unknown';
    try {
      final row = await _client
          .from('user_profiles')
          .select('display_name')
          .eq('id', userId)
          .maybeSingle();
      final name = row?['display_name'] as String?;
      if (name != null && name.isNotEmpty) return name;
    } catch (e) {
      Logger.auth('[UserAttributionRepository] Remote fetch failed for $userId: $e');
    }
    return 'Unknown';
  }
```

Update the `attributionRepository` field in `AuthProvider` (line 56-57) to use the injected client. Since `AuthProvider` receives `AuthService` which wraps the Supabase client, the cleanest approach is to pass `SupabaseClient?` as an optional param to `AuthProvider` and forward it:

In `AuthProvider` constructor, add `SupabaseClient? supabaseClient` param:
```dart
final UserAttributionRepository attributionRepository;

AuthProvider(
  this._authService, {
  // ... existing params ...
  SupabaseClient? supabaseClient,
}) : // ... existing initializers ...
     attributionRepository = UserAttributionRepository(client: supabaseClient) {
```

Update all call sites that construct `AuthProvider` to pass the client.

#### Step 11.4.3: ProjectLifecycleService — Use Injected Client

Modify `lib/features/projects/data/services/project_lifecycle_service.dart`:

The constructor already accepts `Database _db`. For the Supabase RPC call on line 362, the service needs a `SupabaseClient`. Check if there's already one — the class only has `final Database _db;`.

Add a `SupabaseClient?` field:

```dart
class ProjectLifecycleService {
  final Database _db;
  final SupabaseClient? _supabaseClient;

  ProjectLifecycleService(this._db, {SupabaseClient? supabaseClient})
      : _supabaseClient = supabaseClient;
```

Replace line 362 (`await Supabase.instance.client.rpc(`) with:
```dart
    // WHY: Use injected client instead of Supabase.instance.client singleton
    final client = _supabaseClient;
    if (client == null) {
      throw StateError('deleteFromSupabase requires a SupabaseClient');
    }
    await client.rpc(
      'admin_soft_delete_project',
      params: {'p_project_id': projectId},
    );
```

Update the call site that constructs `ProjectLifecycleService` to pass the Supabase client.

#### Step 11.4.4: Test

Run: `pwsh -Command "flutter test test/features/auth/"`
Run: `pwsh -Command "flutter test test/features/projects/"`

---

### Sub-phase 11.5: FormQuickActionRegistry BuildContext Caller Update

This is covered in Sub-phase 11.3 Step 11.3.2. Listing separately to ensure the presentation-layer callers are found and updated.

**Agent**: `frontend-flutter-specialist-agent`

#### Step 11.5.1: Find All Callers

Search for:
- `FormQuickAction(` — registration sites that pass `(BuildContext context, FormResponse response)` lambdas
- `.execute(context,` — invocation sites

Update registrations to return `FormQuickActionResult` instead of taking `BuildContext`.
Update invocations to handle the result in the presentation layer.

#### Step 11.5.2: Test

Run: `pwsh -Command "flutter test test/features/forms/"`

---

## Phase 12: Implement Document Opening

### Sub-phase 12.1: Replace _openDocument Placeholder with Real Implementation

**Files:**
- Modify: `lib/features/entries/presentation/widgets/entry_forms_section.dart` (lines 304-312)
- Test: `test/features/entries/presentation/widgets/entry_forms_section_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 12.1.1: Implement _openDocument with url_launcher

`url_launcher` is already in `pubspec.yaml` (v6.3.1). No new dependency needed.

Replace `_openDocument` method (lines 304-312) in `lib/features/entries/presentation/widgets/entry_forms_section.dart`:

```dart
Future<void> _openDocument(BuildContext context, Document doc) async {
  // WHY: Replaces placeholder snackbar with actual document opening.
  // Uses url_launcher (already in pubspec) for file:// URIs.
  if (doc.filePath == null || doc.filePath!.isEmpty) {
    SnackBarHelper.showError(context, 'Document file not available locally.');
    return;
  }

  final file = File(doc.filePath!);
  if (!await file.exists()) {
    // TODO: Remote signed URL support can be added when DocumentService supports it.
    SnackBarHelper.showError(
      context,
      'File not found on device. Re-sync to download.',
    );
    return;
  }

  final uri = Uri.file(doc.filePath!);
  try {
    final launched = await launchUrl(
      uri,
      // WHY: externalApplication ensures the OS opens the file with its
      // native viewer (PDF reader, image viewer, etc.) rather than in-app.
      mode: LaunchMode.externalApplication,
    );
    if (!launched && context.mounted) {
      SnackBarHelper.showError(
        context,
        'No app available to open ${doc.filename}.',
      );
    }
  } catch (e) {
    Logger.ui('_openDocument error: $e');
    if (context.mounted) {
      SnackBarHelper.showError(context, 'Failed to open document.');
    }
  }
}
```

Add imports at the top of the file:
```dart
import 'dart:io';
import 'package:url_launcher/url_launcher.dart';
```

Remove the `// TODO: Integrate open_file...` comment.

#### Step 12.1.2: Test

Verify that the method compiles and no regressions in the entry forms section:

Run: `pwsh -Command "flutter test test/features/entries/"`

---

## Phase 13: Implement Support/Consent Sync

### Sub-phase 13.1: SupportTicketAdapter — Push-Only Sync

**Files:**
- Create: `lib/features/sync/adapters/support_ticket_adapter.dart`
- Modify: `lib/features/sync/engine/sync_registry.dart` (register adapter)
- Modify: `lib/features/settings/data/repositories/support_repository.dart` (remove TODO comment)
- Test: `test/features/sync/adapters/support_ticket_adapter_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 13.1.1: Create SupportTicketAdapter

Create `lib/features/sync/adapters/support_ticket_adapter.dart`:

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

/// Adapter for support_tickets table.
///
/// WHY: Enables sync for support tickets (previously local-only).
/// Push-only initially — client creates tickets, server updates status.
/// Pull brings status updates from admin dashboard back to client.
///
/// The Supabase support_tickets table was created in pre-release hardening migrations.
class SupportTicketAdapter extends TableAdapter {
  @override
  String get tableName => 'support_tickets';

  /// WHY: Scoped via user_id (user-scoped, not project-scoped).
  @override
  ScopeType get scopeType => ScopeType.viaUser;

  /// No FK dependencies — support tickets are standalone.
  @override
  List<String> get fkDependencies => const [];

  /// WHY: support_tickets does not use soft-delete. Tickets are append-only
  /// from the client. The server may update status but never soft-deletes.
  @override
  bool get supportsSoftDelete => false;

  @override
  String extractRecordName(Map<String, dynamic> record) {
    return record['subject']?.toString() ??
        record['id']?.toString() ??
        'Unknown';
  }
}
```

**IMPORTANT:** Verify `ScopeType.viaUser` exists in `lib/features/sync/engine/scope_type.dart`. If not, the adapter should use the scope type that filters by `user_id`. Check the actual enum values and select the correct one. If only `viaProject` and `viaCompany` exist, the support ticket pull filter will need to be added as a custom scope or the adapter will need to override the pull filter method.

#### Step 13.1.2: Register in SyncRegistry

Modify `lib/features/sync/engine/sync_registry.dart`:

1. Add import: `import 'package:construction_inspector/features/sync/adapters/support_ticket_adapter.dart';`
2. Add `SupportTicketAdapter()` to the `registerSyncAdapters()` list, after `CalculationHistoryAdapter()` (no FK deps, so order doesn't matter — append at end):

```dart
    CalculationHistoryAdapter(),
    SupportTicketAdapter(),  // WHY: Push-only, no FK deps, appended at end
  ]);
```

#### Step 13.1.3: Remove TODO from SupportRepository

Modify `lib/features/settings/data/repositories/support_repository.dart`:

Remove the TODO comment block (lines 8-12). Replace with:

```dart
  // WHY: Sync handled by SupportTicketAdapter in SyncRegistry.
  // Client pushes new tickets; pulls bring status updates from admin dashboard.
```

#### Step 13.1.4: Column Mapping Verification

Verify that the local `support_tickets` SQLite columns match the Supabase table columns. Check `lib/core/database/database_service.dart` (or schema files) for the CREATE TABLE statement and compare against the Supabase migration. If column names differ, add entries to the `converters` map in the adapter.

#### Step 13.1.5: Test

Run: `pwsh -Command "flutter test test/features/sync/"`

---

### Sub-phase 13.2: ConsentRecordAdapter — Push-Only Sync

**Files:**
- Create: `lib/features/sync/adapters/consent_record_adapter.dart`
- Modify: `lib/features/sync/engine/sync_registry.dart` (register adapter)
- Modify: `lib/features/settings/data/repositories/consent_repository.dart` (remove TODO comment)
- Test: `test/features/sync/adapters/consent_record_adapter_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 13.2.1: Create ConsentRecordAdapter

Create `lib/features/sync/adapters/consent_record_adapter.dart`:

```dart
import 'package:construction_inspector/features/sync/adapters/table_adapter.dart';
import 'package:construction_inspector/features/sync/adapters/type_converters.dart';
import 'package:construction_inspector/features/sync/engine/scope_type.dart';

/// Adapter for user_consent_records table.
///
/// WHY: Enables sync for consent records (previously local-only).
/// Push-only, no pull/conflict resolution needed — append-only table with
/// server-side triggers that enforce immutability.
///
/// FROM SPEC: ConsentRecord model uses accepted_at (not created_at) as timestamp.
class ConsentRecordAdapter extends TableAdapter {
  @override
  String get tableName => 'user_consent_records';

  /// WHY: Scoped via user_id (user-scoped, not project-scoped).
  @override
  ScopeType get scopeType => ScopeType.viaUser;

  /// No FK dependencies — consent records are standalone.
  @override
  List<String> get fkDependencies => const [];

  /// WHY: Consent records are append-only. Never soft-deleted.
  @override
  bool get supportsSoftDelete => false;

  @override
  String extractRecordName(Map<String, dynamic> record) {
    final type = record['policy_type']?.toString() ?? 'unknown';
    final version = record['policy_version']?.toString() ?? '?';
    return '$type v$version';
  }
}
```

**Same note as 13.1.1:** Verify `ScopeType.viaUser` exists. Adapt accordingly.

#### Step 13.2.2: Register in SyncRegistry

Modify `lib/features/sync/engine/sync_registry.dart`:

1. Add import: `import 'package:construction_inspector/features/sync/adapters/consent_record_adapter.dart';`
2. Add `ConsentRecordAdapter()` to the list:

```dart
    SupportTicketAdapter(),
    ConsentRecordAdapter(),  // WHY: Push-only, append-only, no FK deps
  ]);
```

#### Step 13.2.3: Remove TODO from ConsentRepository

Modify `lib/features/settings/data/repositories/consent_repository.dart`:

Remove the TODO comment block (lines 9-12). Replace with:

```dart
  // WHY: Sync handled by ConsentRecordAdapter in SyncRegistry.
  // Push-only — no pull or conflict resolution (append-only with server triggers).
```

#### Step 13.2.4: Test

Run: `pwsh -Command "flutter test test/features/sync/"`

---

## Phase 14: Hardcoded Value Fixes

### Sub-phase 14.1: Remove Hardcoded formType Default in Router

**Files:**
- Modify: `lib/core/router/app_router.dart` (lines 694-695)
- Test: Manual verification (router test if exists)

**Agent**: `general-purpose`

#### Step 14.1.1: Look Up formType from FormResponseRepository

Modify `lib/core/router/app_router.dart` at the `/form/:responseId` route (line 694-695):

The route builder has access to `context`, and `FormResponseRepository` should be available via Provider. Replace the hardcoded default:

```dart
builder: (context, state) {
  final responseId = state.pathParameters['responseId']!;
  final projectId = state.uri.queryParameters['projectId'] ?? '';

  // WHY: Look up formType from repository when not in query params.
  // Removes hardcoded 'mdot_0582b' default that broke non-0582B form navigation.
  String? formType = state.uri.queryParameters['formType'];
  if (formType == null || formType.isEmpty) {
    // WHY: Synchronous fallback not possible — repository is async.
    // Use FutureBuilder or redirect to an intermediate loading screen.
    // For now, return a FutureBuilder that resolves the form type.
    return FutureBuilder<String?>(
      future: context.read<FormResponseRepository>().getFormTypeForResponse(responseId),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        final resolvedType = snapshot.data ?? 'mdot_0582b';
        final registry = FormScreenRegistry.instance;
        final builder = registry.get(resolvedType);
        if (builder != null) {
          return builder(
            formId: resolvedType,
            responseId: responseId,
            projectId: projectId,
          );
        }
        return Scaffold(
          body: Center(child: Text('Unknown form type: $resolvedType')),
        );
      },
    );
  }

  final registry = FormScreenRegistry.instance;
  final builder = registry.get(formType);
  // ... rest of existing builder code ...
```

**PREREQUISITE:** Verify `FormResponseRepository` has a method like `getFormTypeForResponse(String responseId)`. If not, add one:

In `lib/features/forms/domain/repositories/form_response_repository.dart`:
```dart
/// Look up the form_type for a response by ID.
/// WHY: Router needs to resolve formType when not provided in query params.
Future<String?> getFormTypeForResponse(String responseId);
```

And implement in the concrete repository class — a simple `SELECT form_type FROM form_responses WHERE id = ?` query.

Remove the `// TODO: Remove hardcoded default` comment.

#### Step 14.1.2: Test

Run: `pwsh -Command "flutter test test/core/router/"`

---

### Sub-phase 14.2: Enable Sentry Performance Tracing

**Files:**
- Modify: `lib/main.dart` (lines 75-79)
- Test: Manual verification (Sentry doesn't need unit tests)

**Agent**: `general-purpose`

#### Step 14.2.1: Set tracesSampleRate and Add Consent Check

Modify `lib/main.dart` lines 75-79:

Replace:
```dart
      // NOTE: tracesSampleRate intentionally kept at 0.0. Performance tracing requires
      // a beforeSendTransaction consent check. Deferred to a future hardening phase
      // (consent UI wiring complete as of Phase 7, but transaction tracing not prioritized
      // for initial release).
      options.tracesSampleRate = 0.0;
```

With:
```dart
      // WHY: 10% sampling rate for performance tracing. Consent is checked
      // in beforeSendTransaction — transactions are dropped when user has
      // not granted analytics consent.
      options.tracesSampleRate = 0.1;
      options.beforeSendTransaction = _beforeSendTransaction;
```

Add the callback function near `_beforeSendSentry`:

```dart
/// Drop performance transactions when the user has not consented to analytics.
/// WHY: GDPR compliance — no telemetry without explicit consent.
SentryTransaction? _beforeSendTransaction(SentryTransaction transaction, Hint hint) {
  if (!sentryConsentGranted) return null;
  return transaction;
}
```

Add import if not already present:
```dart
import 'package:construction_inspector/core/config/sentry_consent.dart';
```

#### Step 14.2.2: Test

Run: `pwsh -Command "flutter analyze"`

---

### Sub-phase 14.3: Fetch Consent Policy Version from app_config

**Files:**
- Modify: `lib/features/settings/presentation/providers/consent_provider.dart` (lines 26-28)
- Modify: `lib/features/auth/presentation/providers/app_config_provider.dart` (expose policy version)
- Test: `test/features/settings/presentation/providers/consent_provider_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 14.3.1: Add Policy Version to AppConfigProvider

Modify `lib/features/auth/presentation/providers/app_config_provider.dart`:

Add a new cached field:
```dart
String? _currentPolicyVersion;
```

Add a getter:
```dart
/// Current consent policy version from remote config.
/// Falls back to '1.0.0' when not configured remotely.
String get currentPolicyVersion => _currentPolicyVersion ?? '1.0.0';
```

In the method that parses the fetched config map (wherever `configMap` is processed), add:
```dart
_currentPolicyVersion = configMap['current_policy_version'];
```

**PREREQUISITE:** Add a `current_policy_version` key-value pair to the Supabase `app_config` table. This is a data migration, not a code change:

```sql
INSERT INTO app_config (key, value) VALUES ('current_policy_version', '1.0.0')
ON CONFLICT (key) DO NOTHING;
```

#### Step 14.3.2: Update ConsentProvider to Use AppConfigProvider

Modify `lib/features/settings/presentation/providers/consent_provider.dart`:

1. Add `AppConfigProvider` as a dependency:
```dart
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
```

2. Add field and constructor param:
```dart
final AppConfigProvider? _appConfigProvider;

ConsentProvider({
  required PreferencesService preferencesService,
  required ConsentRepository consentRepository,
  required AuthProvider authProvider,
  AppConfigProvider? appConfigProvider,
})  : _prefs = preferencesService,
      _consentRepository = consentRepository,
      _authProvider = authProvider,
      _appConfigProvider = appConfigProvider;
```

3. Replace the static constant (line 28):
```dart
/// Current policy version. Fetched from app_config table via AppConfigProvider.
/// Falls back to '1.0.0' when remote config is unavailable.
/// WHY: Remote versioning allows forcing re-consent on policy updates
/// without an app update.
String get currentPolicyVersion =>
    _appConfigProvider?.currentPolicyVersion ?? _fallbackPolicyVersion;

static const String _fallbackPolicyVersion = '1.0.0';
```

4. Update all internal references from `currentPolicyVersion` (static) to the new getter. Since it was `static const`, callers may reference it as `ConsentProvider.currentPolicyVersion` — search and update those to use the instance getter instead.

#### Step 14.3.3: Test

Run: `pwsh -Command "flutter test test/features/settings/"`

---

## Phase 15: Deprecated Code Migration

### Sub-phase 15.1: Remove NormalizeProctorRowUseCase — Migrate to Calculator

**Files:**
- Modify: `lib/features/forms/data/registries/form_calculator_registry.dart` (add normalization logic)
- Modify: `lib/features/forms/presentation/providers/inspector_form_provider.dart` (remove deprecated field, lines 8,19-20,29-30,38,389-414)
- Modify: `lib/features/forms/di/forms_providers.dart` (remove use case, lines 14,45-46,67)
- Modify: `lib/test_harness/harness_providers.dart` (lines 181,301-302)
- Modify: `lib/features/forms/presentation/screens/mdot_hub_screen.dart` (2 call sites)
- Delete: `lib/features/forms/domain/usecases/normalize_proctor_row_use_case.dart`
- Test: `test/features/forms/presentation/providers/inspector_form_provider_test.dart`

**Agent**: `general-purpose`

#### Step 15.1.1: Move Normalization Logic into Mdot0582bCalculator

Locate the Mdot0582bCalculator in `lib/features/forms/data/registries/form_calculator_registry.dart` or a sub-file. Add a method that handles the 0582B-specific weight normalization (the logic currently in `normalize_proctor_row_use_case.dart` lines 27-38):

```dart
/// Normalize 0582B proctor row data before appending.
/// WHY: Migrated from deprecated NormalizeProctorRowUseCase.
/// Strips chart_type, normalizes weights_20_10 list, sets wet_soil_mold_g.
Map<String, dynamic> normalizeProctorRow(Map<String, dynamic> row) {
  final normalized = Map<String, dynamic>.from(row);
  normalized.remove('chart_type');
  final weights =
      (normalized['weights_20_10'] as List?)
          ?.map((value) => '$value'.trim())
          .where((value) => value.isNotEmpty)
          .toList() ??
      <String>[];
  normalized['weights_20_10'] = weights;
  if (weights.isNotEmpty) {
    normalized['wet_soil_mold_g'] = weights.last;
  }
  return normalized;
}
```

#### Step 15.1.2: Update appendMdot0582bProctorRow Callers

In `lib/features/forms/presentation/screens/mdot_hub_screen.dart`, the two call sites (lines 512 and 564) call `provider.appendMdot0582bProctorRow(responseId: ..., row: ...)`.

These need to be migrated to use the calculator normalization + `appendRow()`. However, `appendRow` uses `CalculateFormFieldUseCase` which calls the calculator registry. The normalization needs to happen before the row is appended.

**Option A (simpler):** Keep `appendMdot0582bProctorRow` in InspectorFormProvider but inline the normalization (remove the deprecated use case dependency):

```dart
Future<FormResponse?> appendMdot0582bProctorRow({
  required String responseId,
  required Map<String, dynamic> row,
}) async {
  // WHY: Normalization moved from NormalizeProctorRowUseCase into calculator
  final calculator = FormCalculatorRegistry.instance.get('mdot_0582b');
  final normalizedRow = calculator?.normalizeProctorRow(row) ?? row;

  // Append via the save use case directly
  final result = await _saveFormResponseUseCase.appendProctorRow(
    responseId: responseId,
    row: normalizedRow,
  );
  // ... update _responses list ...
}
```

Remove the `@Deprecated` annotation since this is now the canonical path.

#### Step 15.1.3: Remove NormalizeProctorRowUseCase from DI

In `lib/features/forms/di/forms_providers.dart`:
1. Remove import (line 14)
2. Remove `final normalizeProctorRowUseCase = ...` (line 46)
3. Remove `normalizeProctorRowUseCase: normalizeProctorRowUseCase,` from InspectorFormProvider construction (line 67)

In `lib/test_harness/harness_providers.dart`:
1. Remove `final normalizeProctorRowUseCase = ...` (line 181)
2. Remove `normalizeProctorRowUseCase: normalizeProctorRowUseCase,` (line 302)

In `lib/features/forms/presentation/providers/inspector_form_provider.dart`:
1. Remove import of `normalize_proctor_row_use_case.dart` (line 8)
2. Remove `final NormalizeProctorRowUseCase _normalizeProctorRowUseCase;` field (line 20)
3. Remove constructor param and initializer (lines 29-30, 38)

#### Step 15.1.4: Delete Deprecated Use Case

Delete `lib/features/forms/domain/usecases/normalize_proctor_row_use_case.dart`.

#### Step 15.1.5: Test

Run: `pwsh -Command "flutter test test/features/forms/"`

---

### Sub-phase 15.2: Remove Deprecated deleteByEntryId Methods

**Files:**
- Modify: `lib/features/photos/data/datasources/local/photo_local_datasource.dart` (line 62-67)
- Modify: `lib/features/contractors/data/datasources/local/entry_equipment_local_datasource.dart` (line 89-94)
- Modify: `lib/features/quantities/data/datasources/local/entry_quantity_local_datasource.dart` (line 125-130)
- Modify: `lib/features/forms/data/datasources/local/form_response_local_datasource.dart` (line 104-110)
- Test: Verify no callers remain first

**Agent**: `backend-data-layer-agent`

#### Step 15.2.1: Verify No Active Callers

Search for all invocations of each deprecated `deleteByEntryId` on the 4 local datasource classes. The grep output shows:
- `photo_local_datasource.dart:63` — deprecated method. Callers: `photo_repository_test.dart` (test mock uses it)
- `entry_equipment_local_datasource.dart:90` — deprecated method. No production callers found.
- `entry_quantity_local_datasource.dart:126` — deprecated method. Test callers in `entry_quantity_repository_test.dart` (mock datasource)
- `form_response_local_datasource.dart:105` — deprecated method. No production callers found.

**WARNING:** Test mocks reference `deleteByEntryId`. Before removing, verify test mocks call `softDeleteByEntryId` instead. If test mocks still reference the deprecated method, update them first.

#### Step 15.2.2: Update Test Mocks

In `test/helpers/mocks/mock_repositories.dart` (line 636), `test/data/repositories/photo_repository_test.dart` (line 46), and `test/data/repositories/entry_quantity_repository_test.dart` (line 58):

Rename `deleteByEntryId` to `softDeleteByEntryId` if the mock is implementing the datasource interface. If it's implementing the repository interface (which uses `softDeleteByEntryId`), no change needed — just verify.

#### Step 15.2.3: Remove Deprecated Methods

From each of the 4 files, remove the `@Deprecated` method and its doc comment:

1. `photo_local_datasource.dart` — remove lines 61-67 (`deleteByEntryId`)
2. `entry_equipment_local_datasource.dart` — remove lines 88-94 (`deleteByEntryId`)
3. `entry_quantity_local_datasource.dart` — remove lines 124-130 (`deleteByEntryId`)
4. `form_response_local_datasource.dart` — remove lines 103-110 (`deleteByEntryId`)

#### Step 15.2.4: Test

Run: `pwsh -Command "flutter test test/features/photos/ test/features/contractors/ test/features/quantities/ test/features/forms/ test/data/repositories/"`

---

### Sub-phase 15.3: Extract SyncControlService

**Files:**
- Create: `lib/features/sync/engine/sync_control_service.dart`
- Modify: `lib/features/projects/data/repositories/project_repository.dart` (lines 68-77)
- Modify: `lib/features/projects/data/services/project_lifecycle_service.dart` (sync_control usage)
- Test: `test/features/sync/engine/sync_control_service_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 15.3.1: Create SyncControlService

Create `lib/features/sync/engine/sync_control_service.dart`:

```dart
import 'package:sqflite/sqflite.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';

/// Service that suppresses change_log triggers during operations that
/// should not generate sync events (draft saves, device removal, etc.).
///
/// WHY: Extracted from project_repository.saveDraftSuppressed() and
/// project_lifecycle_service.removeFromDevice() to eliminate duplicate
/// sync_control SQL across the codebase.
///
/// Uses the sync_control table's 'pulling' key — when set to '1',
/// SQLite triggers skip change_log inserts.
class SyncControlService {
  final DatabaseService _dbService;

  SyncControlService(this._dbService);

  /// Run [operation] with sync triggers suppressed.
  ///
  /// Sets sync_control.pulling = '1' before the operation and '0' after,
  /// guaranteeing cleanup via try/finally even on exception.
  Future<T> runSuppressed<T>(Future<T> Function() operation) async {
    final db = await _dbService.database;
    await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
    try {
      return await operation();
    } finally {
      await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
    }
  }

  /// Run [operation] with sync triggers suppressed, using an existing [Database].
  ///
  /// WHY: Some callers (e.g. ProjectLifecycleService) already hold a Database
  /// reference and should not re-acquire it.
  Future<T> runSuppressedWithDb<T>(Database db, Future<T> Function() operation) async {
    await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
    try {
      return await operation();
    } finally {
      await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
    }
  }
}
```

#### Step 15.3.2: Refactor ProjectRepository

Modify `lib/features/projects/data/repositories/project_repository.dart`:

Add `SyncControlService` as a constructor dependency. Replace `saveDraftSuppressed` (lines 70-78):

```dart
final SyncControlService _syncControlService;

// In constructor:
// ProjectRepository(this._localDatasource, this._databaseService, this._syncControlService);

/// Saves a project draft while suppressing change_log triggers.
/// WHY: Draft saves should not trigger sync — the project isn't finalized yet.
Future<void> saveDraftSuppressed(Project project) async {
  await _syncControlService.runSuppressed(() => save(project));
}
```

Similarly refactor `discardDraft` (lines 83-97) to use `_syncControlService.runSuppressed(...)`.

Remove the `// TODO: Extract sync_control suppression` comment (line 68).

#### Step 15.3.3: Refactor ProjectLifecycleService

Modify `lib/features/projects/data/services/project_lifecycle_service.dart`:

Replace inline sync_control SQL (lines 108, 273) with `SyncControlService.runSuppressedWithDb(db, ...)`. Add `SyncControlService` as a constructor param, or pass the `DatabaseService` and use `runSuppressed`.

**NOTE:** `ProjectLifecycleService` constructor takes `Database _db` directly (not `DatabaseService`). Use `runSuppressedWithDb(db, ...)` variant.

#### Step 15.3.4: Test

Create unit test:
```dart
// test/features/sync/engine/sync_control_service_test.dart
// Test runSuppressed sets pulling=1 before and pulling=0 after
// Test runSuppressed resets pulling=0 even on exception
// Test runSuppressedWithDb works with an existing Database instance
```

Run: `pwsh -Command "flutter test test/features/sync/engine/sync_control_service_test.dart"`
Run: `pwsh -Command "flutter test test/features/projects/"`

---

### Sub-phase 15.4: Clean Up app_theme.dart Self-Deprecated References

**Files:**
- Modify: `lib/core/theme/app_theme.dart`
- Test: `pwsh -Command "flutter analyze"`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 15.4.1: Audit Internal References

The file has ~16 `@Deprecated` annotations. The deprecated constants in `AppTheme` forward to `AppColors.*` values. Internal references within `app_theme.dart` that use deprecated constants (e.g., `primaryCyan`, `statusSuccess`, `surfaceElevated`) should be replaced with their `AppColors.*` sources directly.

Example replacements within `app_theme.dart`:
- `primaryCyan` → `AppColors.primaryCyan`  (already what it forwards to, but remove the self-reference if the deprecated constant is used internally)
- `statusSuccess` → `AppColors.statusSuccess`
- `surfaceElevated` → `AppColors.surfaceElevated`

**IMPORTANT:** Do NOT remove the deprecated constants themselves — they exist for external backward compat. Only replace *internal* usage of the deprecated names with the non-deprecated `AppColors.*` sources.

Search within `app_theme.dart` for uses of each deprecated constant name in theme definitions (colorScheme, etc.) and replace with the `AppColors.*` direct reference.

#### Step 15.4.2: Test

Run: `pwsh -Command "flutter analyze"`

The analyze output should show no new warnings. Existing deprecation warnings from external callers are expected and will be addressed separately.

---

## Execution Order & Dependencies

```
Phase 11 (Layer Violations)
├── 11.1 DeletionNotificationBanner ──┐
├── 11.2 ConflictViewerScreen ────────┤ (independent, can parallel)
├── 11.3+11.5 FormQuickActionRegistry ┤
└── 11.4 Auth + Injection ────────────┘

Phase 12 (Document Opening) ← independent

Phase 13 (Sync Adapters)
├── 13.1 SupportTicketAdapter ──┐ (independent, can parallel)
└── 13.2 ConsentRecordAdapter ──┘

Phase 14 (Hardcoded Values)
├── 14.1 Router formType ← needs FormResponseRepository method
├── 14.2 Sentry tracing  ← independent
└── 14.3 Policy version  ← needs app_config migration

Phase 15 (Deprecated Code)
├── 15.1 NormalizeProctorRowUseCase ← independent
├── 15.2 deleteByEntryId methods ← independent
├── 15.3 SyncControlService ← independent
└── 15.4 app_theme cleanup ← independent
```

**Parallelism:** Sub-phases within each phase are independent unless noted. Phases 11-15 can be executed in order, but sub-phases within each can be dispatched to parallel agents.

## Verification

After all phases, run full test suite and static analysis:

```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
```

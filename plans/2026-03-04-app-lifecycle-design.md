# App Lifecycle & Startup Safety Design

**Date**: 2026-03-04
**Status**: DESIGN COMPLETE — Ready for implementation
**Triggered by**: DB migration gap + missing dart-defines caused 25min stuck loop

## Problem Statement

No defined behavior for app state transitions. Today's bugs:
1. DB migration v28 missed 2 tables → can't re-run → crash on delete
2. APK built without `--dart-define-from-file` → "Supabase not configured" crash in release
3. Stale route restored from previous version → "Page Not Found"
4. No distinction between background-resume vs cold-start vs upgrade

## Decisions (from brainstorm)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Error recovery | Auto-repair silently | User shouldn't see migration plumbing |
| Background → foreground | Resume same page | Standard mobile behavior |
| Kill app → reopen | Dashboard, stay logged in | Fresh navigation, preserve session |
| New APK installed | Force re-auth (login screen) | Schema/config may have changed |
| Version detection | App version + DB version | Catches all upgrade scenarios |
| Migration safety | Column-level verification on startup | Self-healing, no version bumps for hotfixes |
| Build safety | Build script is only path | No code changes needed, current crash is fine |

## App State Transitions

### State 1: Background → Foreground (App Resumed)
**Trigger**: User switches back to app from recent apps
**Behavior**:
- Resume exactly where they were (same screen, same scroll position)
- Run inactivity timeout check (existing behavior)
- Refresh remote config if due (existing behavior)
- **No route reset, no re-auth, no migration**

### State 2: Kill App → Reopen (Cold Start, Same Version)
**Trigger**: User swipes away from recent apps, then taps icon
**Detection**: `storedAppVersion == currentAppVersion`
**Behavior**:
1. Run startup sequence (DB init, Supabase init, etc.)
2. Run schema verifier (column-level check, ~50ms)
3. Check auth state — if still logged in, go to **Dashboard** (`/`)
4. **Do NOT restore last route** — always start at Dashboard
5. If not logged in, go to login screen

### State 3: Install New APK → Open (Upgrade)
**Trigger**: User installs a new APK version over the old one
**Detection**: `storedAppVersion != currentAppVersion`
**Behavior**:
1. Run startup sequence (DB init with migrations, Supabase init)
2. Run schema verifier (catches anything migrations missed)
3. **Force re-auth** — clear auth session, go to login screen
4. Update stored app version to current
5. Clear stored last route

### State 4: Fresh Install → First Open
**Trigger**: App installed for first time (no existing DB)
**Detection**: No stored app version
**Behavior**:
1. Create DB from scratch (onCreate path)
2. Run schema verifier (validates fresh schema too)
3. Go to login/registration screen
4. Store app version

## Implementation

### Phase 0: Schema Verifier (~50ms startup cost)

New file: `lib/core/database/schema_verifier.dart`

```dart
class SchemaVerifier {
  /// Canonical schema definition: every table and its required columns.
  /// Single source of truth — when adding a column, add it HERE.
  static const Map<String, List<String>> expectedSchema = {
    'projects': ['id', 'name', 'project_number', ..., 'deleted_at', 'deleted_by'],
    'daily_entries': [..., 'deleted_at', 'deleted_by'],
    'entry_contractors': [..., 'deleted_at', 'deleted_by'],
    'entry_personnel_counts': [..., 'deleted_at', 'deleted_by'],
    // ... all 16+ tables
  };

  /// Verify all expected columns exist, add any missing ones.
  static Future<void> verify(Database db) async {
    for (final entry in expectedSchema.entries) {
      final table = entry.key;
      final expectedColumns = entry.value;
      final actualColumns = await db.rawQuery('PRAGMA table_info($table)');
      final actualNames = actualColumns.map((c) => c['name'] as String).toSet();

      for (final col in expectedColumns) {
        if (!actualNames.contains(col)) {
          await db.execute('ALTER TABLE $table ADD COLUMN $col TEXT');
          // Log the repair for debugging
        }
      }
    }
  }
}
```

Called from `DatabaseService` after `openDatabase()` returns, before any other code touches the DB.

### Phase 1: App Version Tracking

In `main.dart` `_runApp()`, after DB init:

```dart
// Detect app state transition
final currentVersion = packageInfo.version; // from package_info_plus
final storedVersion = preferencesService.getString('app_version');
final isUpgrade = storedVersion != null && storedVersion != currentVersion;
final isFreshInstall = storedVersion == null;

if (isUpgrade) {
  // Force re-auth: clear session
  await preferencesService.clearAuthSession();
  // Clear stale route
  await preferencesService.setLastRoute(null);
}

// Always store current version
await preferencesService.setString('app_version', currentVersion);
```

### Phase 2: Route Restore Logic Change

Current (`main.dart:349-355`):
```dart
if (!isDriverMode && projectSettingsProvider.lastProjectId != null && lastRoute != null) {
  appRouter.setInitialLocation(lastRoute);
}
```

New:
```dart
// Only restore route on background-resume (handled by OS, not this code).
// Cold starts always go to dashboard.
// This code path is cold-start only — don't restore routes.
// (Background resume is handled by the OS keeping the activity alive)
```

Effectively: **remove route restore entirely**. The OS handles background-resume. Cold starts always go to `/`.

### Phase 3: Auth Session Handling on Upgrade

In `AuthProvider` or `_runApp()`:
```dart
if (isUpgrade) {
  // Sign out locally (don't hit Supabase — might have new URL)
  await authProvider.signOutLocally();
}
```

## Files to Change

| File | Change |
|------|--------|
| `lib/core/database/schema_verifier.dart` | **NEW** — Column-level verification |
| `lib/core/database/database_service.dart` | Call SchemaVerifier after openDatabase |
| `lib/main.dart` | Add version detection, remove route restore, add upgrade re-auth |
| `pubspec.yaml` | Add `package_info_plus` dependency |
| `lib/shared/services/preferences_service.dart` | Add `app_version` getter/setter if needed |

## Quality Gates

1. Fresh install → login screen, DB has all columns
2. Same version cold start → dashboard, still logged in
3. Upgrade (version change) → login screen, DB repaired
4. Background resume → same screen, no flicker
5. Schema verifier catches missing column → adds it silently

## Agent Assignments

| Phase | Agent | Description |
|-------|-------|-------------|
| 0 | backend-data-layer-agent | SchemaVerifier + DB integration |
| 1-3 | frontend-flutter-specialist-agent | main.dart lifecycle + route + auth |
| Review | code-review-agent | Verify all transitions correct |

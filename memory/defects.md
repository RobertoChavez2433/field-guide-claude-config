# Defects Log

Active patterns to avoid. Max 15 defects - oldest auto-archives.
Archive: @.claude/memory/defects-archive.md

## Categories
- **[ASYNC]** - Context safety, dispose issues
- **[E2E]** - Patrol testing patterns
- **[FLUTTER]** - Widget, Provider patterns
- **[DATA]** - Repository, collection access
- **[CONFIG]** - Supabase, credentials, environment

---

## Active Patterns

### [ASYNC] 2026-01-21: Async Context Safety
**Pattern**: Using context after await without mounted check
**Prevention**: Always `if (!mounted) return;` before setState/context after await
**Ref**: @lib/features/entries/presentation/screens/entry_wizard_screen.dart

### [ASYNC] 2026-01-20: Async in dispose()
**Pattern**: Calling async methods in dispose() - context already deactivated
**Prevention**: Use `WidgetsBindingObserver.didChangeAppLifecycleState` for lifecycle saves

### [ASYNC] 2026-01-19: Provider Returned Before Async Init
**Pattern**: Returning Provider from `create:` before async init completes
**Prevention**: Add `isInitializing` flag, show loading state until false
**Ref**: @lib/main.dart:365-378

### [E2E] 2026-01-25: Silent Skip with if(widget.exists)
**Pattern**: Using `if (widget.exists) { ... }` silently skips when widget not visible
**Prevention**: Use `waitForVisible()` instead - let it fail explicitly if widget should exist

### [E2E] 2026-01-24: Test Helper Missing scrollTo()
**Pattern**: Calling `$(finder).tap()` on widgets below the fold
**Prevention**: Always `$(finder).scrollTo()` before `$(finder).tap()` for form fields

### [E2E] 2026-01-23: TestingKeys Defined But Not Wired
**Pattern**: Adding key to TestingKeys class but not assigning to widget
**Prevention**: After adding TestingKey, immediately wire: `key: TestingKeys.myKey`

### [E2E] 2026-01-22: Patrol CLI Version Mismatch
**Pattern**: Upgrading patrol package without upgrading patrol_cli
**Prevention**: patrol v4.x requires patrol_cli v4.x - run `dart pub global activate patrol_cli`

### [E2E] 2026-01-18: dismissKeyboard() Closes Dialogs
**Pattern**: Using `h.dismissKeyboard()` (pressBack) inside dialogs
**Prevention**: Use `scrollTo()` to make buttons visible instead of pressBack

### [E2E] 2026-01-17: Git Bash Silent Output
**Pattern**: Running Flutter/Patrol commands through Git Bash loses stdout/stderr
**Prevention**: Always use PowerShell: `pwsh -File run_patrol_batched.ps1`

### [DATA] 2026-01-20: Unsafe Collection Access
**Pattern**: `.first` on empty list, `firstWhere` without `orElse`
**Prevention**: Use `.where((e) => e.id == id).firstOrNull` pattern

### [DATA] 2026-01-16: Seed Version Not Incremented
**Pattern**: Updating form JSON definitions without incrementing seed version
**Prevention**: Always increment `seedVersion` in seed data when modifying form JSON

### [DATA] 2026-01-15: Missing Auto-Fill Source Config
**Pattern**: Form field JSON missing `autoFillSource` property
**Prevention**: Include `autoFillSource` for fields that should auto-fill; increment seed version

### [CONFIG] 2026-01-19: Supabase Instance Access
**Pattern**: Accessing Supabase.instance without checking configuration
**Prevention**: Always check `SupabaseConfig.isConfigured` before accessing Supabase.instance

### [CONFIG] 2026-01-14: flutter_secure_storage v10 Changes
**Pattern**: Using deprecated `encryptedSharedPreferences` option
**Prevention**: Remove option - v10 uses custom ciphers by default, auto-migrates data

### [FLUTTER] 2026-01-18: Deprecated Flutter APIs
**Pattern**: Using deprecated APIs (WillPopScope, withOpacity)
**Prevention**: `WillPopScope` -> `PopScope`; `withOpacity(0.5)` -> `withValues(alpha: 0.5)`

---

<!-- Add new defects above this line -->

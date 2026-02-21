# Defects: Toolbox

Active patterns for toolbox. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [FLUTTER] 2026-02-22: Stale route restoration traps user on dead-end screen
**Pattern**: Saving ALL route changes to SharedPreferences (including dynamic-ID routes like `/form/:responseId`) causes app to restore to a screen whose entity no longer exists, with no back button or error recovery.
**Prevention**: Use an allowlist of static routes for persistence. Always add error recovery UI (icon + message + "Go Back" button via `safeGoBack`) to screens that load entities by ID.
**Ref**: @lib/main.dart:253 (`_isRestorableRoute`), @lib/features/toolbox/presentation/screens/form_fill_screen.dart:449

### [FLUTTER] 2026-02-20: Flutter Driver can't interact with dialog overlays
**Pattern**: `showDialog`/`AlertDialog` widgets are invisible to Flutter Driver finders (`ByText`, `ByType`, `ByValueKey`) on Windows. Tap/waitFor commands timeout silently.
**Prevention**: Guard all dialogs with `if (const bool.fromEnvironment('FLUTTER_DRIVER')) return;` before `showDialog`. Add `ValueKey` to dialog buttons anyway for future testability.
**Ref**: @lib/features/toolbox/presentation/screens/form_fill_screen.dart:673

<!-- Add defects above this line -->

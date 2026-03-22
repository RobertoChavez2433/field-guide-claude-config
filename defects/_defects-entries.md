# Defects: Entries

Active patterns for entries. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [E2E] 2026-03-22: Tap-to-edit sections require explicit section tap before field interaction
**Pattern**: Activities, safety, and temperature sections in the entry editor use tap-to-edit mode (`alwaysEditing: false`). TextFields only render after tapping the section card (setting `_isEditing=true`). Test flows that skip this tap step get 404 (widget not found) because the TextField doesn't exist in the tree yet.
**Prevention**: E2E flows must tap the section card key (e.g., `report_activities_section`) and wait for the field key (e.g., `report_activities_field`) before attempting text input. The `isViewer` guard also blocks editing for non-creators on safety/temperature sections.
**Ref**: `lib/features/entries/presentation/widgets/entry_activities_section.dart:67,96`, `lib/features/entries/presentation/screens/entry_editor_screen.dart:896,1313`
**Ref**: `lib/features/entries/presentation/screens/entry_editor_screen.dart` (T62/T63)

### [DATA] 2026-03-21: createdByUserId never set on entry creation
**Pattern**: `DailyEntry` constructor in entry wizard omitted `createdByUserId`, so all entries had null attribution. Delete buttons and attribution text never appeared.
**Prevention**: When adding attribution/ownership fields to models, grep all creation sites to ensure the field is populated. Add to provider or screen-level creation.
**Ref**: `lib/features/entries/presentation/screens/entry_editor_screen.dart:364`

### [FLUTTER] 2026-03-03: firstWhere crash on sync-deleted location
**Pattern**: `locations.firstWhere((l) => l.id == value)` throws `StateError` if a location was sync-deleted but its ID remains in a dropdown. This is a recurring anti-pattern across 5+ reviews.
**Prevention**: Always use `.where(...).firstOrNull` with null guard. Never use `.firstWhere` without `orElse`.
**Ref**: @lib/features/entries/presentation/screens/report_widgets/report_location_edit_dialog.dart:36

### [DATA] 2026-03-03: Dead code from unused provider methods
**Pattern**: `undoSubmission()` was implemented in repository + provider but UI called `updateEntry(entry.copyWith(...))` instead. The dedicated method had validation (status guard, syncStatus=pending) that the raw path bypassed.
**Prevention**: When adding a dedicated method with validation, wire it into the UI immediately and grep for alternative paths that bypass it.
**Ref**: @lib/features/entries/presentation/screens/entry_editor_screen.dart:313-315

### [DATA] 2026-03-03: Timestamp drift between repository and provider
**Pattern**: Repository creates `batchTimestamp = DateTime.now().toUtc()` for SQLite writes. Provider creates a second `DateTime.now().toUtc()` for in-memory state. Timestamps differ.
**Prevention**: Return the timestamp from the repository method and use it in the provider for in-memory updates.
**Ref**: @lib/features/entries/data/repositories/daily_entry_repository.dart:224


<!-- RESOLVED 2026-03-21 S619: [SECURITY] Inspectors can edit other users' entries — Fixed: canEditEntry() now denies ALL non-creators. Null createdByUserId = read-only. Ref: auth_provider.dart:192-196 -->

<!-- Add defects above this line -->

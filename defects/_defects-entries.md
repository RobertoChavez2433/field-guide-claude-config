# Defects: Entries

Active patterns for entries. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [CONFIG] 2026-03-03: Flutter Keys invisible to UIAutomator
**Pattern**: `Key('login_email_field')` does not produce `resource-id` in Android UIAutomator XML dump. Zero resource-ids found on any widget.
**Prevention**: Investigate whether `ValueKey` + explicit `Semantics` widget is needed, or if Flutter's native view embedder doesn't propagate Keys to Android accessibility IDs. May need a custom SemanticsKey approach.
**Ref**: `lib/shared/testing_keys/testing_keys.dart`, UIAutomator dump from Session 487

## Active Patterns

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

### [TEST] 2026-03-03: submit-entry flow fails — required fields missing
**Status**: OPEN
**Source**: Automated test run 2026-03-03-1834
**Symptom**: "Mark Ready & Review" button is disabled (enabled=false) because create-entry flow only fills activities field. Location and SESC measures are required by the review flow but were left empty.
**Fix**: Update create-entry test flow to fill location (select first available) and SESC measures. Or update submit-entry flow to use "Skip" to bypass review validation.
**Screenshot**: `.claude/test-results/2026-03-03-1834-run/screenshots/wave3_submit_step6_review_screen.png`
**Ref**: `entry_review_screen.dart:241` (`_canMarkReady` checks `getMissingFields()`)

<!-- Add defects above this line -->

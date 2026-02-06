# Defects Log

Active patterns to avoid. Max 7 defects - oldest auto-archives.
Archive: @.claude/logs/defects-archive.md

## Categories
- **[ASYNC]** - Context safety, dispose issues
- **[E2E]** - Patrol testing patterns
- **[FLUTTER]** - Widget, Provider patterns
- **[DATA]** - Repository, collection access
- **[CONFIG]** - Supabase, credentials, environment

---

## Active Patterns

### [DATA] 2026-02-04: Substring Keyword Matching Causes False Positives
**Pattern**: Using `String.contains()` for keyword matching allows substring false positives ("BIDDER" matches "BID", "PRICES" matches "PRICE")
**Prevention**: Use word-boundary matching (RegExp `\bKEYWORD\b`) for single-word patterns; multi-word patterns can use contains safely
**Ref**: @lib/features/pdf/services/table_extraction/table_locator.dart:299

### [DATA] 2026-02-04: else-if Chain Blocks Multi-Category Keyword Matching
**Pattern**: Using `else if` chain in keyword matching prevents independent elements from matching different categories
**Prevention**: Use independent `if` + `continue` pattern; each element checks all categories before moving to next
**Ref**: @lib/features/pdf/services/table_extraction/header_column_detector.dart:228

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

---

<!-- Add new defects above this line -->

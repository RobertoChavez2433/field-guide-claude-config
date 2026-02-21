# Defects: Quantities

Active patterns for quantities. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [DATA] 2026-02-20: Item Number sort uses string comparison instead of numeric
**Pattern**: Quantities list "Sort by Item Number" produces lexicographic order (#1, #10, #100, #2) instead of numeric (#1, #2, #3..., #10..., #100). Item numbers stored/compared as strings.
**Prevention**: Use `int.tryParse()` or numeric comparator when sorting by item number. Never sort numeric IDs as raw strings.
**Ref**: Quantities screen sort logic (likely in bid_item_provider or quantities_screen)

### [DATA] 2026-02-20: Quantities search field does not filter results
**Pattern**: Search TextField accepts input but onChanged/onSubmitted not wired to filter logic — list remains at full 131 items regardless of query text.
**Prevention**: Verify search field's onChanged triggers provider filter. Add integration test for search filtering.
**Ref**: Quantities screen search field (`quantities_search_field`)

### [RESOLVED] 2026-02-20: DuplicateStrategy switch fallthrough in importBatch
**Status**: FIXED (Session 399).
**Pattern**: `importBatch` duplicate handling switch lacked explicit `break`s, causing fallthrough and incorrect duplicate behavior paths.
**Prevention**: Require explicit `break` in duplicate strategy switch and include strategy-path tests for skip/replace/error.
**Ref**: @lib/features/quantities/presentation/providers/bid_item_provider.dart:187

### [RESOLVED] 2026-02-20: M&P enrichment no-op when provider project context is unset
**Status**: FIXED (Session 399).
**Pattern**: `enrichWithMeasurementPayment` returned early when `currentProjectId` was null, causing silent no-op in valid M&P apply flows.
**Prevention**: Resolve matched bid items by id via repository fallback, track touched project ids, and reload/notify safely even without preset provider context.
**Ref**: @lib/features/quantities/presentation/providers/bid_item_provider.dart:293

<!-- Add defects above this line -->

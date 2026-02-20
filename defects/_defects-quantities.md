# Defects: Quantities

Active patterns for quantities. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

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

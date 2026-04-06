# Code Review — Pay Application Implementation Plan

**Date**: 2026-04-06
**Plan**: `.claude/plans/2026-04-05-pay-application.md`
**Verdict**: **REJECT** — 7 Critical, 7 High, 6 Medium, 5 Low findings

## Critical Issues

1. **AppScaffold API mismatch** — `title:` and `actions:` params don't exist. Use `appBar: AppBar(...)` pattern.
2. **Provider-Repository method name mismatches** — `findByExactRange` vs `findByDateRange`, `getNextNumber` vs `getNextApplicationNumber`, `numberExists` vs `isNumberUsed`.
3. **Provider-Repository type mismatches** — Provider passes DateTime, repository expects String.
4. **Provider `findOverlapping` return type** — Treats List as nullable. Should check `isNotEmpty`.
5. **Duplicate route/TestingKeys across Phases 7 and 10** — Consolidate into Phase 10 only.
6. **Test code uses non-existent APIs** — `generate()` params, `computeSummary()`, `ContractorImportParser`.
7. **Widget tests use non-existent widget/provider APIs** — Dialog as widget vs static show(), wrong param names.

## High Issues

8. **Raw `ScaffoldMessenger` bypasses `SnackBarHelper`** — Use `SnackBarHelper.show*()`.
9. **`ProjectAnalyticsProvider` uses `dynamic` casts** — Type the `Future.wait` results properly.
10. **`_bidItemLabel()` ignores AppTerminology** — Use `AppTerminology.bidItemPlural.toLowerCase()`.
11. **Overlap date comparison string format inconsistency** — Ensure consistent ISO format.
12. **Delete flow incomplete** — Soft-delete cascade doesn't propagate between tables.
13. **Test calls `findOverlapping` with non-existent `excludeExactMatch` param**.
14. **`ExportPayAppUseCase` exists but is never used** — Dead code, provider reimplements inline.

## Medium Issues

15. Discrepancy computation compares bid quantities instead of actual tracked quantities.
16. Unused `DailyEntryRepository` dependency in provider.
17. `sourceRecordId` never set — breaks history list navigation.
18. Pre-existing `entry_personnel_counts` in `tablesWithDirectProjectId` issue (not plan's fault).
19. `REAL` type for monetary columns — consistent with existing but Postgres could use NUMERIC.
20. Test expects ASC order but datasource defaults to DESC.

## Low Issues

- Duplicated `scheduledValue` computation — extract to BidItem getter.
- `excel` package version not verified against SDK.
- `file_picker` not added to pubspec.yaml.
- Contractor parsers have TODO stubs.
- `ContractorLineItem.copyWith` can't clear `matchedBidItemId` to null.

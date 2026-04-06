# Completeness Review — Pay Application Implementation Plan

**Date**: 2026-04-06
**Verdict**: **REJECT** — 5 Critical, 6 High, 5 Medium, 2 Low

## Critical Findings

1. **Provider-Repository method name mismatches** — `findByExactRange` vs `findByDateRange`, `getNextNumber` vs `getNextApplicationNumber`, `numberExists` vs `isNumberUsed`. Compile failures.
2. **PayAppExcelExporter never called from provider** — Provider reimplements export inline without actual file generation. G703 xlsx file never created.
3. **exportDiscrepancyPdf creates no actual PDF** — No PDF builder service exists. Only creates metadata record.
4. **ProjectAnalyticsProvider never registered** — Defined but not in provider tree. Runtime crash.
5. **Zero integration tests** — Spec requires 12 integration test scenarios. Plan has none.

## High Findings

6. **ExportPayAppUseCase is dead code** — Properly implemented but never wired into DI or called by provider.
7. **XlsxContractorParser is a stub** — Returns empty list. Primary import format non-functional.
8. **_bidItemLabel() hardcoded** — Ignores AppTerminology, always returns 'pay items'.
9. **Delete cascade incomplete** — Doesn't delete PayApplication row or local/remote files.
10. **Missing barrel files** — screens.dart, repositories.dart, providers.dart barrels referenced but never created.
11. **Test import path wrong** — Tests import from domain/services/ but exporter is at data/services/.
12. **Missing test flow doc updates** — 6 doc files required by spec Section 9 not updated.

## Medium Findings

13. Zero-quantity warning missing for empty date ranges.
14. Daily discrepancy section unimplemented (hasDailyDetail always false).
15. Re-compare prompt missing when importing again in same session.
16. Export convergence not addressed (spec Section 12).
17. No isolate for Excel generation performance.
18. ManualMatchEditor edit button is a placeholder.

## Low Findings

19. getLastPayApp reads stale cache instead of querying repository.
20. sourceRecordId never set on ExportArtifact — breaks history list navigation.

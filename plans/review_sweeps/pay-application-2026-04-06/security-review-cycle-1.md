# Security Review — Pay Application Implementation Plan

**Date**: 2026-04-06
**Plan**: `.claude/plans/2026-04-05-pay-application.md`
**Verdict**: **REJECT** — 3 HIGH, 5 MEDIUM findings

## Finding S1 [HIGH] — Missing `WITH CHECK` on UPDATE RLS policies
**Phase**: 5.4
Fix: Add `WITH CHECK` to both UPDATE policies matching the `USING` clause pattern.

## Finding S2 [HIGH] — Missing `canWrite` guard on `ExportArtifactProvider.deleteArtifact`
**Phase**: 6.4
Fix: Inject `_canWrite` into `ExportArtifactProvider` and guard `deleteArtifact`.

## Finding S3 [HIGH] — Missing `canWrite` guard on `ContractorComparisonProvider.exportDiscrepancyPdf`
**Phase**: 8.3
Fix: Add `canWrite` parameter and guard both `importContractorArtifact` and `exportDiscrepancyPdf`.

## Finding S4 [MEDIUM] — `PayAppExcelExporter.saveToFile` lacks directory validation
**Phase**: 4.3
Fix: Add directory/filename traversal validation.

## Finding S5 [MEDIUM] — Imported contractor file path not validated for traversal
**Phase**: 8.2
Fix: Validate path against app sandbox before reading.

## Finding S6 [MEDIUM] — Imported contractor file not deleted after parsing
**Phase**: 8.3
Fix: Add explicit file deletion after parsing completes.

## Finding S7 [MEDIUM] — `save()` bypasses `create()` SEC-F05 validation
**Phase**: 6.5
Fix: Wire provider through use case, or consolidate validation into `save()`.

## Finding S8 [MEDIUM] — Duplicate export flow creates maintenance risk
**Phase**: 4.4 / 6.5
Fix: Wire `PayApplicationProvider.exportPayApp()` to delegate to `ExportPayAppUseCase`.

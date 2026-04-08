# Pay Application Audit Plan

Date: 2026-04-06
Spec: `.claude/specs/2026-04-05-pay-application-spec.md`
Scope baseline: commits `f4496b9a`, `1fa98f38`, `2632a627`, `d2e800b2`, `cffe835c`

## End Goals

1. The branch analyzes cleanly and the pay-app wiring compiles end to end.
2. Pay-app export, replace, exported-history, comparison, analytics, and delete flows are fully wired from DI to routes to persistence.
3. The local/remote schema and sync registration for `export_artifacts` and `pay_applications` are aligned.
4. Critical behavior matches the spec:
   - exact-range replace preserves identity/number
   - overlapping ranges are blocked
   - exported history shows pay apps separately from editable saved responses
   - contractor comparison remains ephemeral except exported discrepancy PDFs
   - analytics uses pay-app-aware totals
5. The fixed gaps are covered by focused tests so the branch does not regress immediately.

## Audit Findings To Resolve

1. Fix compile-time breakages in pay-app DI, comparison export, and quantities wiring.
2. Fix incorrect contractor-comparison daily discrepancy math so owner-side daily values are comparable to contractor amounts.
3. Restore missing remote schema coverage for `export_artifacts` and `pay_applications`, including storage bucket/RLS/integrity-sync plumbing required by the branch's sync registration.
4. Close obvious spec-alignment gaps in comparison/export UX and pay-app verification coverage.
5. Add or extend focused tests for the fixed paths, then rerun analysis and targeted test suites.

## Out Of Scope

1. Unrelated sync-engine refactor cleanup outside the pay-app/export/analytics blast radius.
2. Broad UI redesign not required to satisfy the approved pay-app spec.
3. Historical `.claude` archaeology unless needed to unblock a concrete pay-app issue.

## Verification Gate

1. `flutter analyze`
2. Focused `flutter test` suites for DI/bootstrap, database/export dual-write, and new pay-app regressions
3. Review of touched files against the spec success criteria and test-flow docs

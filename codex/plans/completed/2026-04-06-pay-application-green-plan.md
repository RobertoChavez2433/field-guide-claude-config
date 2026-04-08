# Pay Application Green Plan

Date: 2026-04-06
Spec: `.claude/specs/2026-04-05-pay-application-spec.md`
Flow reference: `.claude/test-flows/tiers/pay-app-and-exports.md`

## Goal

Drive the pay-application/export branch to a defensible green state by closing
the last unproven product paths rather than continuing broad review.

## Current Status

Already proven in this iteration:

1. `flutter analyze` is green.
2. Pay-app export/use-case/provider regressions are green.
3. Export-artifact file sync regressions are green.
4. Windows driver on port `4949` responds through `/driver/ready` and basic
   route/key probes.

Still not fully proven:

1. Real export flow coverage from `QuantitiesScreen` through save/share and
   detail navigation.
2. Contractor parser coverage for `.xlsx` and best-effort `.pdf`.
3. PDF content fidelity beyond `bytes.isNotEmpty`.
4. Sync edge cases around missing `export_artifact_id` parent rescue and
   local-only `local_path` cache writes.
5. P01-P06 acceptance coverage remains only partially automated.

## Execution Queue

1. Export fidelity
   - Strengthen `contractor_comparison_pdf_exporter_test.dart` to assert text
     content and daily-section behavior.
   - Add `.xlsx` parser coverage and a historical no-year daily-header case for
     `pay_app_import_parser.dart`.
   - Add a chaining-oriented pay-app export test if previous-snapshot behavior
     still looks ambiguous after parser/export coverage.

2. Sync correctness
   - Add coverage for artifact-scoped storage paths so same filename does not
     alias blobs.
   - Verify or fix `pay_applications` pull rescue when `export_artifact_id`
     parent is missing.
   - Verify or fix recovered `local_path` cache writes so they stay local-only
     and do not enqueue sync work.

3. UI/flow verification
   - Add higher-signal widget coverage around `QuantitiesScreen` export gating
     and post-export actions where feasible.
   - Use the Windows driver on `4949` for targeted route/key validation and, if
     stable enough, start covering P01-P03 or the strongest reachable subset.

4. Final gate
   - Re-run `flutter analyze`.
   - Re-run the pay-app/export/sync targeted suite.
   - Re-run driver readiness and the concrete runtime checks exercised in this
     iteration.

## Stop Condition

Stop only when the remaining pay-app/export slice is green, or when the only
open items are clearly external/unverifiable in this session and documented as
residual risk with exact scope.

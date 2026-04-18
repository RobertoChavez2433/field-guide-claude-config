# 2026-04-12 Prerelease Final Canonical Tracker

Purpose: concise replacement working tracker for the last prerelease pass. The
large 2026-04-11 tracker remains the evidence archive; this file is the active
status surface so we do not lose our place.

## Current Verdict

- [ ] Prerelease is not fully closed yet.
- [x] Major product lanes are functionally closed by prior evidence: pay app
  exports, all-form PDF proof, Office Technician, review comments, auth/sync
  hardening, schema drift guards, logging security, quantity ordering, photo
  rename, personnel picker, calculators, and S21 sync/background recovery.
- [ ] Final release honesty is still open until this concise tracker is
  reconciled, the remaining high-risk code hygiene items are either fixed or
  explicitly accepted, and a final completeness pass is recorded.
- [ ] Current working tree is dirty with env/tooling/CI changes unrelated to
  this tracker pass; review or commit them before final release tagging.

## Active Priority Order

1. [x] Reconcile stale prerelease tracker state into this canonical tracker.
2. [x] Set Supabase `GOOGLE_CLOUD_VISION_API_KEY` for the
   `google-cloud-vision-ocr` Edge Function before Google Cloud Vision live
   import proof.
   - 2026-04-12: Hardened function deployed. Readiness with debug-function
     allowance now passes after setting the Supabase
     `GOOGLE_CLOUD_VISION_API_KEY` secret.
   - 2026-04-12 live smoke: remote `company_app_config` table and
     `admin_set_company_app_config` RPC were applied. Google billing/API key
     restrictions were corrected. Direct Google Vision smoke and deployed
     Supabase Edge Function smoke both returned `PAY ITEM 204` through a real
     authenticated session with company OCR mode set to `auto`.
   - 2026-04-12 prerelease cleanup: remote `codex-admin-sql` Edge Function was
     deleted. Full Google Cloud OCR readiness now passes without debug-function
     allowance.
3. [ ] Refactor and test `lib/features/pdf/services/idr_pdf_template_writer.dart`.
4. [ ] Strengthen PDF extraction/post-processing with new pay-item and M&P
   fixture/golden tests, then refactor
   `lib/features/pdf/services/extraction/shared/post_process_utils.dart`.
   - Standard harness/pointer: `integration_test/pre_release_pdf_corpus_test.dart`
     and `test/features/pdf/extraction/PDF_HARDENING.md`.
   - Manifest contract: `test/features/pdf/extraction/integration/pre_release_pdf_corpus_manifest_test.dart`.
   - S21 corpus result on 2026-04-12: Berrien pay items/M&P passes; Huron
     Valley and Grand Blanc pay-item PDFs extract zero items, and their paired
     M&P PDFs parse zero entries. Treat as general OCR/table extraction
     hardening, not filename-specific patching.
5. [ ] Review `lib/core/logging/logger.dart` for a small seam split around the
   high-complexity `_log` path, without weakening sanitizer/Sentry/support-log
   contracts.
6. [ ] Review large 1126/1174R UI files; split only if the change is low-risk
   and backed by focused widget tests.
7. [ ] Define a phased `shared.dart` barrel import migration or document an
   explicit prerelease deferral.
8. [ ] Run and record final completeness review after the above decisions.

## Reconciled Large-Tracker Items

- [x] SESC review-screen S21 proof is closed. The old OPEN block in the large
  tracker is superseded by later `PASS / REVIEW SESC ACTION` evidence: the S21
  tapped `review_field_action_sesc_measures` and verified `report_sesc_field`
  opened visible/enabled in Safety & Site Conditions. Local route tests also
  cover missing review extras.
- [x] `LocalSyncStore` oversized-file item is closed. It is now a thin facade
  around record, metadata, diagnostic, and scope store seams.
- [x] The old Logical Commit Plan checklist is stale, not an implementation
  backlog. Later commits/addenda supersede it.
- [ ] Final completeness review remains open until this tracker has no stale
  open entries and final evidence is recorded.
- [ ] Broad `shared.dart` barrel audit remains open. Current count is 190
  imports across `lib` and `test`, with 178 in `lib`.

## High-Risk Code Items

- [ ] `idr_pdf_template_writer.dart`
  - Current concern: large file, IDR release-critical export path.
  - Known high-complexity methods: `fillDocument` and `_fillContractorSection`.
  - Direction: extract writer helpers by responsibility while preserving fixed
    template IDR release baseline and all field-name/field-count behavior.

- [ ] `post_process_utils.dart`
  - Current concern: 691-line static PDF extraction utility bucket.
  - Main entry `cleanDescriptionArtifacts` is low complexity, so avoid
    behavior churn. Split by general OCR/post-processing responsibility only
    after new PDF fixtures prove the current gaps.

- [ ] `logger.dart`
  - Current concern: logging is security-critical and `Logger._log` is high
    complexity.
  - Existing protections: logging sanitizer and Sentry/support-log contracts are
    lint-locked. Any split must keep those tests green.

## Lower-Risk Hygiene Items

- [ ] `mdot_1126_form_screen.dart`
  - Large but mostly low-complexity UI composition.
- [ ] `mdot_1174r_form_screen.dart`
  - Large but mostly low-complexity UI composition.
- [ ] `mdot_1174r_sections.dart`
  - Large section-widget file. Split by section only if test coverage is clear.
- [ ] `shared.dart` barrel imports
  - Too broad for a risky one-shot prerelease migration. Prefer an allowlist or
    feature-by-feature migration after release unless current work touches a
    call site.

## New PDF Fixture Set

Add the following as repeatable extraction fixtures/goldens. Treat failures as
general algorithmic extraction issues, not one-off PDF-specific patches.

- [ ] `127449 Berrien County US-12 Shoulder Widening Intersection Reconstruction CTC [14-22] Pay Items.pdf`
- [ ] `127449 Berrien County US-12 Shoulder Widening Intersection Reconstruction CTC [248-268) M&P.pdf`
- [ ] `917245 Huron Valley DWSRF Water System Improvements CTC [22-30] Pay Items.pdf`
- [ ] `917245 Huron Valley DWSRF Water System Improvements CTC [412-427) M&P.pdf`
- [ ] `938710 Grand Blanc Sewer Infrastructure Rehabilitation CTC [18-26] Pay Items.pdf`
- [ ] `938710 Grand Blanc Sewer Infrastructure Rehabilitation CTC [285-301) M&P.pdf`

Fixture goals:

- [ ] Import each PDF through the same production extraction/parsing pipeline
  used for Springfield pay items.
- [ ] Create stable expected outputs for pay items and M&P items.
- [ ] Assert item count, item numbers, descriptions, units, quantities, and
  section classification where applicable.
- [ ] When a new parsing issue appears, fix through a general extraction rule
  and add regression coverage naming the algorithmic failure mode.

## Final Completeness Gate

- [ ] `flutter analyze lib test`
- [ ] `dart run custom_lint`
- [ ] Relevant focused PDF extraction tests, including the six new fixtures.
- [ ] Relevant IDR export/template writer tests.
- [ ] Focused logger tests if `logger.dart` is touched.
- [ ] Full `flutter test --reporter expanded`, unless a tiny intentional
  exception set is explicitly documented with owner and follow-up.
- [ ] S21 proof only for behavior that changes mobile runtime behavior.
- [ ] Final tracker self-review: no stale OPEN blocks, no stale checklist, and
  all deferred hygiene clearly labeled as accepted post-prerelease work.

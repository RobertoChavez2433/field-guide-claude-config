# 2026-04-24 Focused Forms, Pay App, PDF Import, And Responsiveness Remaining Verification Spec

## Summary

This replaces the prior focused forms/pay-app verification checklist with a
current-state to-do list based on the latest retained evidence.

Grounded state at handoff:

- `Phase 1` canonical contracts are complete.
- `flutter analyze` was brought back to zero and must stay there.
- Tablet Pay Items/Quantities split-pane reselection was already fixed and
  remains regression-only coverage.
- Strong UI fill evidence already exists for `IDR`, `MDOT 1126`, and
  `MDOT 0582B`.
- `MDOT 1174R` has real S21 edit/preview/export path evidence, but its explicit
  full-capacity machine-checkable closure still needs to be locked.
- The last completed two-device forms run failed on the tablet cleanup/sync
  tail because of stale undismissed conflict residue, not a fresh form
  runtime/layout defect. That residue repair is now baseline and must be
  re-proven on fresh evidence.
- New required scope: verify the PDF import flow, including the post-import
  pay-items confirmation UI that currently renders cut off on tablet.

This lane stays narrowly scoped to forms, pay-app, PDF import, saved exports,
sync responsiveness, and the architecture guardrails that keep those flows
reliable.

## Remaining Verification Checklist

### 0. Baseline And Lane Control

- [ ] Save this replacement plan under `.codex/plans/` and point active work at it.
- [ ] Create the working branch as `pre-release-hardening`.
- [ ] Preserve retained evidence from
  `tools/testing/test-results/2026-04-24/phase2u-forms-supported-phone-tablet-20260424-0720/`.
- [ ] Record the grounded interpretation of that run:
  - S21 advanced through real form lifecycles without runtime/layout failures.
  - Tablet failure was an unclassified stop rooted in stale cleanup conflict residue.
  - That old residue is not accepted as a current blocker after the repair; it must be rechecked on fresh evidence.
- [ ] Keep the lane on real auth only, real backend only, explicit Springfield project binding only.

### 1. Phase 0 Move-On Gate

- [ ] Keep `flutter analyze` at zero before every device rerun.
- [ ] Keep focused lint/static rules only where they lock verified architecture boundaries or expose real binding gaps.
- [ ] Re-run targeted responsiveness capture for:
  - tab switching
  - Springfield Daily Entries long-scroll
  - form entry/edit/save/preview/export/reopen
  - pay-app detail/export/saved-export reopen
  - full UI-triggered sync with a real non-zero payload
  - PDF import preview and post-import pay-items confirmation
- [ ] Publish one scorecard per run in JSON, Markdown, and CSV with:
  - p50/p95/p99/max frame cost
  - build vs raster attribution
  - 60 FPS compatibility
  - 120 FPS readiness visibility
- [ ] Treat 60 FPS compatibility as the move-on floor.
- [ ] Preserve 120 FPS misses for follow-up optimization, but do not block Phase 1+ work on 120 FPS readiness alone once 60 FPS compatibility is green.
- [ ] Keep a standardized responsiveness surface catalog so any trace-proven infra issue is checked across other affected screens.

### 2. Forms Full-Capacity Closure

- [ ] Re-prove `IDR` full-capacity UI fillability on the current build and lock saved-state, preview, export, and reopen evidence.
- [ ] Re-prove `MDOT 1126` full-capacity UI fillability on the current build and lock saved-state, preview, export, and reopen evidence.
- [ ] Re-prove `MDOT 0582B` full-capacity UI fillability on the current build and lock saved-state, preview, export, and reopen evidence.
- [ ] Finish `MDOT 1174R` full-capacity machine-checkable closure so it has the same acceptance shape as the other forms.
- [ ] For every form, acceptance requires:
  - full UI entry, not DB-only field seeding
  - no phantom/duplicate/row-zero behavior
  - saved local state matches contract
  - remote synced state matches contract where sync is in scope
  - preview reflects latest saved state
  - export matches contract field/cell inventory
  - exported artifact reopens correctly
- [ ] Preserve artifact-backed proof for every form in canonical result locations.

### 3. PDF Import Verification And UI Repair

- [ ] Add PDF import to the targeted verification set.
- [ ] Verify import preview discovers the expected pay items and exposes the correct item count.
- [ ] Verify the post-import pay-items confirmation surface works on phone and tablet.
- [ ] Fix the tablet post-import confirmation UI so it is not cut off, clipped, or visually malformed when showing actions like `Import <N> Items`.
- [ ] Verify the confirmation surface remains usable with large import counts and split/compact layouts.
- [ ] Verify import completion, pay-item creation/update results, and reopen behavior against the real project data.
- [ ] Add responsiveness capture around:
  - import preview open
  - selection changes
  - import confirmation render
  - import execution completion
- [ ] Add this flow to regression evidence so it is no longer outside the release-facing forms/pay-items lane.

### 4. Pay App End-To-End Closure

- [ ] Re-prove the positive-earned pay-app scenario with non-zero period and earned-to-date totals.
- [ ] Re-prove stale/missing local artifact recovery.
- [ ] Re-prove rebuild/replacement updates the existing pay app instead of creating the wrong duplicate path.
- [ ] Re-prove export produces a fresh workbook with correct path, hash, timestamp, and contents.
- [ ] Re-prove saved export open/copy/share actions use the rebuilt current artifact.
- [ ] Re-prove Settings saved-export reopen if it remains part of the shipped flow.
- [ ] Keep contractor comparison either:
  - explicitly in scope with parity verification, or
  - explicitly excluded in this replacement spec before execution begins.
- [ ] Keep the already-fixed tablet split-pane pay-item selection issue on regression coverage only.

### 5. Fresh Device Acceptance Passes

- [ ] Pass 1: targeted current-build rerun on phone and tablet with fresh artifacts.
- [ ] Review all evidence after Pass 1:
  - frame timing
  - screenshots
  - sync status
  - saved/exported artifacts
  - DB/remote proof
  - PDF import confirmation UI
- [ ] Fix only trace-backed or artifact-backed failures.
- [ ] Pass 2: rerun the same targeted flows to prove the result is not residue-dependent.
- [ ] Do not claim completion until both passes are green for the in-scope current-build flows.

## Targeted Flow Set

- `forms-supported-forms-proof-ui-flow`
- `idr-full-capacity-ui-flow`
- `forms-save-reload-ui-flow`
- `forms-pdf-preview-ui-flow`
- `forms-export-proof-ui-flow`
- `forms-gallery-ui-flow`
- `forms-gallery-backward-traversal-ui-flow`
- `pay-app-forward-happy-ui-flow`
- `pay-app-export-proof-ui-flow`
- `pay-app-backward-traversal-ui-flow`
- `settings-saved-exports-ui-flow`
- `sync-full-responsiveness-ui-flow`
- `daily-entries-list-scroll-responsiveness-ui-flow`
- new targeted PDF import verification flow covering preview, confirmation UI,
  import execution, and reopen proof

## Test And Evidence Plan

- Keep machine-checkable contracts as the acceptance source of truth.
- Keep every new current-build run under
  `tools/testing/test-results/<date>/<run-id>/`.
- For each accepted form/pay-app/PDF-import flow, retain:
  - `summary.json`
  - `report.md`
  - screenshots for critical states
  - saved/exported artifacts
  - parsed preview/export inspections
  - sync/runtime diagnostics
  - responsiveness scorecards
- Treat old evidence as baseline context only; acceptance must come from fresh
  current-build artifacts.

## Assumptions And Defaults

- This is a replacement checklist, not an append-only addendum.
- The old tablet unclassified failure is treated as historical residue caused by
  stale conflict cleanup until a fresh current-build rerun proves otherwise.
- `1174R` stays open until it has the same explicit machine-checkable
  full-capacity closure as `IDR`, `1126`, and `0582B`.
- The PDF import confirmation UI issue is release-relevant and now part of this
  lane.
- 60 FPS compatibility is the move-on gate; 120 FPS readiness remains visible
  follow-up work, not the blocker once 60 FPS acceptance is green.

## 2026-04-24 Session Append

### Completed This Session

- [x] Keep the active lane on branch `pre-release-hardening` with this spec as
  the live checklist.
- [x] Preserve the April 24 baseline interpretation:
  - S21 previously advanced through real form lifecycles without fresh
    runtime/layout failures.
  - The old tablet stop remains treated as stale cleanup/conflict residue until
    fresh reruns prove otherwise.
- [x] Add the PDF import lane to targeted verification and regression coverage.
- [x] Add PDF import lifecycle proof and responsiveness capture plumbing for:
  - preview open
  - selection changes
  - import execution
  - reopen proof
- [x] Fix the tablet PDF import confirmation bar clipping/cutoff issue by
  moving the confirmation actions onto the shared bottom-bar surface with
  narrow-width fallback layout behavior.
- [x] Add a durable guardrail against the recurring Android dual-build mistake:
  - `.codex/AGENTS.md` now says to reuse remote driver port `4948` across
    Android devices and vary only host-forwarded ports.
  - `tools/start-driver.ps1` now defaults Android remote driver port to
    `4948` instead of mirroring the host port.
  - `tools/testing/tests/DriverLabStartup.Tests.ps1` now locks that contract.
- [x] Re-establish a live S21 `flutter run` driver lane under active
  monitoring:
  - host driver `4948`
  - control port `4950`
  - remote driver `4948`
  - confirmed `/diagnostics/device_state` sign-in-ready at `/login`
  - confirmed foreground package `com.fieldguideapp.inspector`
- [x] Re-establish a live tablet `flutter run` driver lane far enough to reach
  app driver state on:
  - host driver `4952`
  - control port `4953`
  - remote driver `4948`
  - confirmed `/diagnostics/device_state` responding with `/login`

### Important Execution Notes For Next Session

- [x] Prefer `flutter run` driver lanes over rebuilding APK variants unless a
  trace-backed reason requires a rebuild.
- [x] Do not launch parallel Android driver APK builds that vary the device-side
  driver port.
- [x] Actively monitor startup instead of waiting blind:
  - watch the flutter-run control endpoint
  - tail the stdout log
  - check foreground window/focus
  - probe `/diagnostics/device_state`
- [x] The earlier S21 startup failure was not an app hang; it was a wrong-port
  wait caused by the app binding a fallback port in one run. The launcher now
  detects the actual bound port from stdout and rewires adb forwarding.
- [ ] Re-run the harness/static verification after the latest
  `tools/start-driver-flutter-run.ps1` edits. Last confirmed harness green was
  before the final flutter-run monitoring changes.

### Open Before Device Acceptance Work Resumes

- [ ] Re-run `flutter analyze` after the latest launcher/monitoring edits.
- [ ] Confirm the tablet is fully foreground/interaction-ready after the
  notification permission overlay dismissal:
  - last confirmed tablet state before interruption had live driver/device
    state at `/login`
  - last UI dump showed the app login screen
  - explicit final foreground confirmation after overlay clearance still needs
    to be rechecked at session start
- [ ] Normalize the live actor mapping to continue device work with:
  - S21 driver `4948`, control `4950`
  - Tablet driver `4952`, control `4953`

### Remaining Release-Facing Checklist

- [ ] Keep `flutter analyze` at zero before each fresh rerun.
- [ ] Defer any additional responsiveness-only work unless a fresh device run
  exposes a real usability failure.
- [ ] Re-prove `IDR` full-capacity fill/save/preview/export/reopen evidence on
  the current build.
- [ ] Re-prove `MDOT 1126` full-capacity fill/save/preview/export/reopen
  evidence on the current build.
- [ ] Re-prove `MDOT 0582B` full-capacity fill/save/preview/export/reopen
  evidence on the current build.
- [ ] Finish `MDOT 1174R` full-capacity machine-checkable closure.
- [ ] Re-prove PDF import preview, confirmation, import completion, reopen
  behavior, and real project-data outcomes on both phone and tablet with fresh
  artifacts.
- [ ] Re-prove the positive-earned pay-app scenario with export/rebuild/reopen
  artifact proof.
- [ ] Re-prove stale or missing pay-app local artifact recovery.
- [ ] Re-prove saved export open/copy/share behavior, including Settings reopen
  if it remains shipped.
- [ ] Execute fresh phone/tablet Pass 1 on the current build with artifact
  review.
- [ ] Fix only artifact-backed or trace-backed failures from Pass 1.
- [ ] Execute fresh phone/tablet Pass 2 and do not claim completion until both
  passes are green.

## 2026-04-24 PDF Import / Form Editability Append

### Completed

- [x] Replaced the rejected full-route/summary PDF import handoff with a
  bounded `PdfImportReviewDialog` opened from the current project screen.
- [x] Restored the real import review behavior inside that dialog:
  - all parsed pay items are available in the scrollable list
  - each row shows item number, description, quantity/unit, confidence percent,
    select checkbox, edit, and remove controls
  - the import action imports the currently selected rows through
    `BidItemProvider.importBatch`
- [x] Added focused widget proof that the workflow dialog shows confidence,
  scrolls beyond the first five items, and imports all selected rows.
- [x] Verified live S21 behavior with the Springfield 131-item PDF:
  - route stayed `/project/harness-project-001/edit?tab=3`
  - dialog showed `Import Preview`, `Found 131 pay items`, OCR confidence,
    per-item confidence, edit/remove controls, and `Import 131 Items`
  - screenshot saved at
    `tools/testing/runtime/flutter-run/s21-pdf-import-review-dialog.png`
- [x] Verified live tablet behavior with the same PDF:
  - route stayed `/project/harness-project-001/edit?tab=3`
  - dialog showed the same review/confidence/edit/import surface
  - screenshot saved at
    `tools/testing/runtime/flutter-run/tablet-pdf-import-review-dialog.png`
- [x] Debugged the MDOT 0582B “sent result cannot be changed” issue:
  - last-sent test `Edit` previously only expanded the section
  - it now removes the last sent test row from the response and restores that
    row into the editable input fields so the corrected send replaces it
  - last-sent proctor `Edit` now reopens the proctor when no sent tests depend
    on it, and blocks with a clear error when dependent tests must be edited
    first
- [x] Added controller tests for reopening the last sent test and proctor.

### Verification

- [x] `flutter analyze`
- [x] `flutter test test/features/pdf/presentation/screens/pdf_import_preview_screen_test.dart test/features/forms/presentation/controllers/mdot_hub_controller_test.dart`
- [x] `flutter test test/features/forms/widgets/hub_proctor_content_test.dart test/features/forms/presentation/controllers/mdot_hub_controller_test.dart test/features/pdf/presentation/screens/pdf_import_preview_screen_test.dart`
- [x] `tools/testing/Test-TestingHarness.ps1`

### Still Required In Fresh Form Verification Flows

- [x] Add an explicit MDOT 0582B form verification step that sends a test,
  taps Edit on the last-sent test, changes a value, re-sends it, previews PDF,
  and verifies only the corrected row is present.
- [x] Add an explicit proctor reopen step proving the app blocks proctor edits
  while dependent tests exist. The in-app controller/widget tests cover the
  permitted reopen path when no dependent tests exist; a full device flow that
  removes every dependent test before reopening the proctor remains a later
  expansion if we need live proof beyond the controller contract.
- [x] Audit `submitted` form-response locking separately from exported PDF
  artifacts. Exported responses remain editable by model policy, but submitted
  responses still intentionally lock until a dedicated reopen/undo-submit
  product decision is implemented.

### 2026-04-24 Continuation

- [x] Added contracted driver keys for the last-sent MDOT 0582B edit buttons:
  - `hub_test_edit_last_sent_button`
  - `hub_proctor_edit_last_sent_button`
- [x] Extended `mdot0582b-only` verification with
  `Invoke-SoakMdot0582BLastSentEditProof`:
  - proves proctor edit is blocked while dependent sent tests exist
  - taps last-sent test Edit
  - changes the wet density result
  - resends the test
  - verifies the test-row count stayed unchanged and the last row contains the
    corrected value
  - opens the 0582B PDF preview afterward
- [x] Added harness wiring coverage so this edit/resend/preview proof cannot
  disappear from the MDOT 0582B flow silently.
- [x] Fixed the PDF import review dialog analyzer issues:
  - controller lifecycle now handles widget updates
  - provider construction was removed from the dialog build tree
- [x] Tightened submitted/exported form-response audit coverage:
  - exported responses remain editable and re-exportable
  - submitted responses remain locked with an accurate error message until a
    dedicated reopen/undo-submit policy is implemented

### Continuation Verification

- [x] `flutter analyze`
- [x] `flutter test test/features/pdf/presentation/screens/pdf_import_preview_screen_test.dart test/features/forms/data/repositories/form_response_repository_test.dart test/features/forms/widgets/hub_proctor_content_test.dart test/features/forms/presentation/widgets/hub_quick_test_content_test.dart test/features/forms/presentation/controllers/mdot_hub_controller_test.dart`
- [x] `pwsh -NoProfile -File tools/testing/Test-TestingHarness.ps1`
- [x] `pwsh -NoProfile -Command '$ErrorActionPreference="Stop"; . .\tools\testing\flows\sync\Flow.Mdot0582B.ps1; "loaded"'`

### Tablet Device Proof

- [x] Ran the MDOT 0582B edit/resend/preview proof on tablet device
  `R52X90378YB` against the actually synced Springfield project
  `75ae3283-d4b2-4035-ba2f-7b4adb018199`.
- [x] Passing run:
  `tools/testing/test-results/2026-04-24/20260424-tablet-mdot0582b-edit-resend-proof-r9-springfield/summary.json`
  - `passed: true`
  - `failedActionCount: 0`
  - `queueDrainResult: drained`
  - `unprocessedRowCount: 0`
  - `blockedRowCount: 0`
  - `runtimeErrors: 0`
  - `loggingGaps: 0`
  - `syncEngineExercised: true`
- [x] The tablet proof covered:
  - reopen last-sent test
  - correct wet density to `149.9`
  - resend without increasing the test row count (`12`)
  - verify corrected local data
  - preview the PDF afterward
  - sync to remote and clean up with final queues drained
- [x] Patched the artifact publisher to preserve redirected
  `background.stdout.log` and `background.stderr.log` files instead of trying
  to compact/delete handles owned by the parent PowerShell process.

### Remaining Device Gap

- [ ] S21 phone MDOT 0582B edit/resend device proof is still blocked by the
  earlier driver connectivity issue on port `4948`; do not count the phone as
  verified for this specific flow until that driver lane is restored.

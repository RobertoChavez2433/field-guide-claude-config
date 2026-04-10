# 2026-04-09 Export Artifact Contract Plan

## Goal

Unify export behavior across:

- forms
- daily entries
- pay applications

without pretending they have identical attachment/bundling semantics.

The contract should standardize preview/export/save/share capability ownership,
while leaving artifact-specific rules explicit:

- forms can attach to entries and bundle with entry export
- daily entries are the bundle root
- pay apps are standalone project-scoped exports and do not attach to entries

## Product Intent Captured

- preview/export is a shared platform contract, not a per-form invention
- attached forms must export with the daily entry bundle
- forms must still export standalone
- pay apps are exportable artifacts but remain independent of entry attachment
- new forms should inherit these rules by default instead of re-implementing
  bespoke screen logic

## Audit Summary

Current ownership is split across multiple local seams:

- forms
  - preview/export/share was recently unified under
    `FormPdfActionOwner`
- entries
  - preview/save/share still live in `EntryPdfPreviewScreen`
  - older dialog flow still exists in `report_pdf_actions_dialog.dart`
  - bundle export lives separately in `ExportEntryUseCase`
- pay apps
  - export creation flow lives in `QuantitiesPayAppExporter`
  - exported-file save/share lives in `PayAppDetailFileOps`
  - post-export follow-up uses `ExportSaveShareDialog`

This means the export system currently has:

- one shared form contract
- one entry contract
- one pay-app contract
- no shared capability registry declaring what each exportable artifact is
  supposed to support

## Target Architecture

### A. Shared Export Capability Registry

Add a shared registry describing each exportable artifact type:

- `form`
- `entry`
- `pay_app`

Each capability record should define:

- `id`
- `displayName`
- `canPreview`
- `canExportStandalone`
- `canAttachToEntry`
- `canBundleWithEntry`
- `isBundleRoot`
- `supportsSaveCopy`
- `supportsShare`
- `previewOwner`
- `exportOwner`
- `followUpOwner`

### B. Shared Follow-Up / File-Action Owner

Extract save-copy/share handling for already-exported files into a reusable
owner so pay apps, settings export history, and future export surfaces stop
duplicating `ExportArtifactFileService` orchestration and snackbar copy.

### C. Entry Export Contract Alignment

Bring the daily-entry preview/export surface under the same capability model:

- preview
- save/export
- share
- bundle root semantics

### D. Form Attachment Contract

Formalize attach-to-entry as a shared capability seam instead of leaving it as
1126-only behavior.

This will likely need:

- generic attachment policy model
- generic attach owner
- artifact-level “attachable to entry” capability gate

### E. Enforcement

Add lint only where the signal is statically honest.

Good lint candidates:

- keep exportable artifact IDs registered in the shared capability registry
- restrict direct exported-file save/share orchestration to approved owners
- restrict top-level exportable screens from directly invoking low-level
  preview/share APIs outside approved owners

Not honestly lintable by itself:

- correct Android chooser/task-stack behavior
- whether a particular artifact should attach to a particular entry at runtime

## Execution Order

### Phase 1: Registry Baseline

- [x] Add shared export capability model + registry
- [x] Register baseline artifact types: `form`, `entry`, `pay_app`
- [x] Add tests locking the baseline capability contract
- [x] Add an enforcement lint if the registry contract can be checked honestly

### Phase 2: Adopt In Live Owners

- [x] Make `FormPdfActionOwner` declare/use the `form` capability
- [x] Make entry preview/export flow declare/use the `entry` capability
- [x] Make pay-app export and pay-app detail file ops declare/use the
      `pay_app` capability
- [x] Replace hardcoded follow-up labels/messages where the capability record
      should own them

### Phase 3: Shared Exported-File Action Owner

- [x] Extract reusable owner for `save copy` / `share file` from exported local
      artifacts
- [x] Migrate `PayAppDetailFileOps`
- [x] Migrate settings saved-export actions
- [x] Reuse in pay-app post-export follow-up where honest

### Phase 4: Entry + Bundle Alignment

- [x] Audit and collapse duplicate entry export UI between preview screen and
      older report dialog surfaces
- [x] Align entry export follow-up actions with the shared contract
- [x] Verify bundle-root semantics remain explicit and tested

### Phase 5: Form Attachment Standardization

- [x] Design generic attach-to-entry capability seam for forms
- [x] Determine whether all attachable forms should share one attach owner
- [x] Keep pay-app explicitly outside that attach contract
- [x] Verify attached forms still export inside entry bundle
- [x] Add a shared attached-form presentation contract for entry-editor cards
      so attached forms stop rendering form-internal quick actions

### Phase 6: Device Validation

- [x] S21 proof: form preview/export still healthy
- [x] S21 proof: entry preview/save/share still healthy after migration
- [x] S21 proof: pay-app export/save/share still healthy after migration
- [x] S21 proof: entry bundle still includes attached forms correctly
- [x] S21 proof: attached entry-form cards show export-style editable names,
      tap into the wizard, and keep preview separate

## First Slice To Implement Now

1. Add shared export capability registry.
2. Use it in the live form/entry/pay-app export owners.
3. Add the first enforcement rule if the static signal is honest.

## Current Honest Next Slice

1. Keep pay-app explicitly outside the attach contract and lock that in the
   capability docs/tests.
2. Verify attached forms still export inside entry bundle.
3. Decide which follow-up labels/messages should come directly from the shared
   capability contract instead of hardcoded UI copy.
4. Reinstall and validate the migrated entry export path plus the generic
   attach flow on the S21.

## 2026-04-09 Progress Update

Entry export no longer carries two product-facing UI owners.

What landed:
- added `EntryPdfActionOwner` to own entry save/share/export-record side
  effects after preview is open
- rewired `EntryPdfPreviewScreen` to use the shared owner instead of owning
  `saveEntryExport + recordExport + sharePdf` inline
- deleted the dead `report_pdf_actions_dialog.dart` and
  `report_debug_pdf_actions_dialog.dart` surfaces and removed their barrel
  exports
- updated the export capability registry so `entry.exportOwner` and
  `entry.followUpOwner` now point to `EntryPdfActionOwner`
- added lint `no_direct_entry_pdf_actions_outside_owner`

Verification:
- `flutter test test/core/exports/export_artifact_capability_registry_test.dart test/features/entries/presentation/support/entry_pdf_action_owner_test.dart`
- `dart test test/architecture/no_direct_entry_pdf_actions_outside_owner_test.dart`
- targeted `flutter analyze`
- root `dart run custom_lint`

Honest remaining gap from this slice:
- source/test/lint are clean, but the migrated entry export path still needs a
  fresh S21 validation pass before it can be called device-closed

## 2026-04-09 Progress Update 2

Generic form-entry attachment no longer depends on 1126-specific use-case names
or inline entry-link mutation in presentation code.

What landed:
- added `ResolveFormAttachmentEntryUseCase`
- added `CreateFormAttachmentEntryUseCase`
- deleted the now-obsolete 1126-specific attachment use-case files
- added `FormEntryAttachmentOwner` to own picker/attach/create-and-attach flow
- rewired `AttachStep` to use the generic use cases and shared owner
- rewired `FormsListScreen` to use the shared entry-picker owner
- added lint
  `no_form_response_entry_attachment_mutation_outside_owner`

Verification:
- `flutter test test/features/forms/domain/usecases/resolve_form_attachment_entry_use_case_test.dart test/features/forms/domain/usecases/create_form_attachment_entry_use_case_test.dart test/features/forms/presentation/support/form_entry_attachment_owner_test.dart test/features/forms/presentation/screens/forms_list_screen_test.dart test/features/forms/presentation/screens/mdot_1126_form_screen_test.dart`
- `dart test test/architecture/no_form_response_entry_attachment_mutation_outside_owner_test.dart`
- targeted `flutter analyze`
- root `dart run custom_lint`

Important architecture note:
- `InspectorFormProvider` still exposes response mutation through extension
  methods, which is why the shared owner currently uses the repository for the
  actual attach mutation instead of a mockable provider-owned method. That is
  now an explicit cleanup follow-up, not hidden drift.

## 2026-04-09 Progress Update 4

Attached forms inside the entry editor now have a shared presentation contract
instead of leaking form-internal 0582B quick actions into the daily-entry UI.

What landed:
- added `FormAttachmentDisplayNamePolicy`
- rewired `FormExportFilenamePolicy` to honor the same custom attachment name
  used by the entry-editor card
- entry attachment cards now:
  - show the export-style filename
  - open the form wizard on card tap
  - keep `View Form` as a separate preview action
  - offer rename through a shared filename dialog
- `FormAttachmentManager` now supports in-place replacement after attachment
  rename

Verification:
- `flutter test test/features/entries/presentation/widgets/entry_form_card_test.dart test/features/forms/data/services/form_attachment_display_name_policy_test.dart test/features/forms/data/services/form_export_filename_policy_test.dart test/features/entries/presentation/widgets/entry_forms_section_test.dart`
- targeted `flutter analyze`
- root `dart run custom_lint`

## 2026-04-09 Device Closure: Attached Entry-Form Card Contract

- [x] S21 proof on the real attached 0582B row
  - the entry editor now shows the attached form with an export-style filename
    instead of internal 0582B quick-action chips
  - the visible attachment name is editable:
    - live device proof shows the persisted renamed filename
      `CompanyPrefix_0582B_Apr08.pdf`
  - tapping the attached form card opens the real 0582B wizard/editor
  - tapping `View Form` opens the real PDF preview shell for quick
    verification before bundle export
  - `AppTextField` now forwards its key to the underlying `TextFormField`,
    which made the rename dialog honestly driver-typable instead of only
    wrapper-detectable
- proof artifacts:
  - `.codex/tmp/live_debug/entry-editor-after-scroll-forms.png`
  - `.codex/tmp/live_debug/entry-form-card-open-result.png`
  - `.codex/tmp/live_debug/entry-form-card-preview-result.png`
  - `.codex/tmp/live_debug/entry-attachment-renamed-final.png`

Status change:
- remove `attached entry-form cards need S21 proof` from the export-contract
  backlog
- keep only the narrower export backlog:
  - capability-driven follow-up labels/messages
  - standalone-form dated-folder product decision

## 2026-04-09 Progress Update 5

Attached-form presentation is now device-proven on the S21, not just
source/test-clean.

What was validated live:
- entry-editor attachment cards now show the export-style filename instead of
  0582B quick-action chips
- the live device screenshot confirms the attachment card renders the renamed
  filename (`CompanyPrefix_0582B_Apr08.pdf`) in the Forms section
- tapping the attached 0582B card opens the real 0582B wizard/editor
- tapping `View Form` opens the real PDF preview shell for quick verification
- the bundle/export path remains intact for attached forms

Artifacts:
- `.codex/tmp/live_debug/post-scroll-entry.png`
- `.codex/tmp/live_debug/entry-form-open-after-tap.png`
- `.codex/tmp/live_debug/entry-attached-form-preview-open.png`

Open export-contract backlog after this closure:
- dated-folder behavior for standalone form exports is still a product-policy
  decision rather than an unresolved plumbing bug

## 2026-04-09 Progress Update 6

The shared export capability contract now owns the remaining follow-up dialog
copy that was still hardcoded in live form and pay-app owners.

What landed:
- `ExportArtifactCapability` now declares:
  - `exportedDialogTitle`
  - `exportedDialogBodyText`
  - `saveCopyActionLabel`
  - `shareActionLabel`
  - `saveCopyDialogTitle`
- `FormPdfActionOwner` now reads its exported/saved-copy dialog copy from the
  shared capability record
- `QuantitiesPayAppExporter` now does the same for pay-app export follow-up
  copy

Verification:
- `flutter test test/core/exports/export_artifact_capability_registry_test.dart test/features/forms/presentation/support/form_pdf_action_owner_test.dart`
- targeted `flutter analyze`
- root `dart run custom_lint`

Honest remaining gap from this slice:
- the new card contract still needs S21 proof on the real attached 0582B row

## 2026-04-09 Progress Update 3

Pay-app data is now split the way the product actually needs it:
- canonical syncable pay-app data stays in `pay_applications`
- local workbook/export history stays in `export_artifacts`

What landed:
- retired sync for local-only export history tables:
  - `entry_exports`
  - `form_exports`
  - `export_artifacts`
- added runtime repair:
  - `RepairSyncStateV20260409LocalOnlyExportQueue`
- added upgrade migration:
  - `v57` removes legacy export-history triggers and purges queued residue
- rebuilt `pay_applications` as canonical data:
  - `export_artifact_id` is now optional
  - local DB migration `v58` rebuilds the table and removes the old
    artifact-uniqueness assumption
  - Supabase migration
    `20260409130500_make_pay_apps_canonical_and_artifact_optional.sql`
    makes the remote column nullable as well
- pay-app sync adapter now treats `export_artifact_id` as local-only/local-read:
  - stripped on push
  - ignored on pull
- detail/workbook/delete flows now treat artifacts as local history:
  - detail loading falls back by `source_record_id`
  - workbook building falls back by `source_record_id`
  - deleting an export artifact clears the local pointer instead of deleting
    canonical pay-app data
  - deleting a pay app is now its own use case

Verification:
- targeted sync schema/registry/repair/migration tests are green
- targeted pay-app use-case/detail-screen tests are green
- targeted `flutter analyze` is green
- root `dart run custom_lint` is green

Live device proof:
- S21 upgraded to the new local schema:
  - `PRAGMA table_info('pay_applications')` shows
    `export_artifact_id` with `notnull = 0`
- live trigger state after install:
  - no triggers on `entry_exports`, `form_exports`, or `export_artifacts`
  - `pay_applications` still has insert/update/delete sync triggers
- live sync state after upgrade was clean:
  - `pendingCount = 0`
  - `blockedCount = 0`

Honest remaining gap from this slice:
- I have device proof for the schema/trigger split and clean queue state
- I have not yet re-run a full pay-app creation + sync cycle on-device after
  the canonical/local split

## 2026-04-09 Progress Update 4

The full on-device pay-app cycle is now characterized honestly:

- real S21 flow completed:
  - navigated to `Pay Items & Quantities`
  - exported a new pay app through the live dialogs
  - confirmed the exported detail screen opened for `Pay App #4`
- queue ownership before sync was correct:
  - `pendingCount = 1`
  - the only queued row was `pay_applications/<new-id>`
  - `export_artifacts`, `form_exports`, and `entry_exports` stayed out of
    `change_log`
  - the local pay-app row still held a local `export_artifact_id`, and the
    local export artifact row existed with a real on-device file path
- the remote schema exposed the true remaining blocker:
  - sync failed with Postgres `23502`
  - remote `pay_applications.export_artifact_id` is still `NOT NULL`
  - this proves the client split is correct but the linked backend migration
    is not applied yet
- landed follow-up protection in source:
  - `ChangeTracker.markBlocked(...)`
  - `SyncErrorClassifier.isRemoteSchemaCompatibilityError(...)`
  - `PushErrorHandler` now immediately blocks this pay-app schema mismatch
    instead of burning retries
  - new startup repair:
    - `RepairSyncStateV20260409PayAppSchemaMismatch`
  - `SyncStateRepairRunner` catalog bumped to `2026-04-09.2`
- verified locally:
  - targeted sync tests green
  - targeted `flutter analyze` green
  - root `dart run custom_lint` green
- verified on the S21 after reinstall:
  - the already-poisoned pay-app row was converted from `pending` to
    `blocked` on startup
  - `driver/sync-status` showed:
    - `pendingCount = 0`
    - `blockedCount = 1`
  - running sync again no longer retried the blocked pay-app row:
    - sync returned success with `pushed = 0`, `pulled = 0`
    - the row stayed blocked with the explicit remote-schema-mismatch message

Honest remaining blocker:
- the linked Supabase project still needs
  `20260409130500_make_pay_apps_canonical_and_artifact_optional.sql`
  applied remotely
- I could not apply it from this environment because:
  - linked migration history is already drifted (`db push` blocked)
  - direct `supabase db query --linked` needs `SUPABASE_DB_PASSWORD`, which is
    not available in this workspace

## 2026-04-09 Progress Update 5

The backend blocker is now closed end to end:

- remote schema is fixed on the linked Supabase project:
  - `public.pay_applications.export_artifact_id` is now nullable
  - `pay_applications_export_artifact_id_fkey` exists with `ON DELETE SET NULL`
- landed the missing operator recovery seam in source:
  - `LocalSyncStore.resetBlockedPayAppSchemaMismatchChanges()`
  - `SyncRecoveryService.rerunKnownRepairs()` now requeues blocked pay-app
    schema-mismatch rows before rerunning the conservative repair catalog
- verified locally:
  - new database-backed recovery test is green
  - targeted `flutter analyze` is green
  - root `dart run custom_lint` is green
- verified on the S21 after reinstall:
  - initial state showed the old blocked pay-app row:
    - `pendingCount = 0`
    - `blockedCount = 1`
  - `POST /driver/run-sync-repairs` requeued it cleanly:
    - `pendingCount = 1`
    - `blockedCount = 0`
  - `POST /driver/sync` then drained it fully:
    - `pendingCount = 0`
    - `blockedCount = 0`
    - `unprocessedCount = 0`
  - local `pay_applications/<id>` still exists on-device with its local
    `export_artifact_id`
  - remote `public.pay_applications/<id>` now exists with:
    - `application_number = 4`
    - `export_artifact_id = null`

This closes the pay-app export-history split with honest end-to-end proof:

- canonical pay-app data syncs and is backed up
- workbook/export history stays local-only
- stale blocked rows can now be explicitly repaired after backend deployment

## 2026-04-09 Progress Update 6

Entry export is now testable enough for live bundle verification:

- added stable preview-shell keys in source:
  - `report_pdf_preview_dialog`
  - `report_pdf_save_as_button`
  - `report_pdf_share_button`
- locked with source verification:
  - new `entry_pdf_preview_screen_test.dart`
  - existing `entry_pdf_action_owner_test.dart`
  - targeted `flutter analyze`
  - root `dart run custom_lint`
- verified on the S21 against the real Apr 9 draft entry:
  - the attached `mdot_1126` response still points at
    `daily_entries/fb3ddde9-9429-48d5-bf4e-de2fabdfebe1`
  - opening the draft entry and exporting from the live preview now exposes the
    keyed preview shell
  - tapping `Save` opens `Export Folder Name` with suggested folder `04-09`
    instead of the single-PDF save path
  - screenshot proof:
    - `.codex/tmp/entry-export-folder-dialog.png`

Conclusion:

- attached forms are still influencing the entry export contract correctly
- daily-entry export remains the bundle root when forms are attached
- the remaining open part is the separate 1126 attach-step/create-entry UI flow,
  not the bundle/export side

## 2026-04-09 Progress Update 7

Shared form export is now closed across the shipped form surfaces.

- Closed the remaining drift between dedicated form shells and the fallback
  viewer:
  - the fallback viewer no longer requires preview before export
  - the fallback viewer no longer submits or marks the response exported
  - forms now use a shared `Form Exported` follow-up dialog with:
    - `Not Now`
    - `Save Copy`
    - `Share File`
- Source changes:
  - added `lib/core/exports/export_save_share_dialog.dart`
  - upgraded `ExportArtifactCapabilityRegistry` so `form` supports save-copy
  - widened `ExportFormUseCase` to return `FormExportArtifactResult`
  - updated `FormPdfService.saveTempPdf(...)` to accept stable generated
    filenames
  - rewired `FormExportProvider`, `FormPdfActionOwner`,
    `FormViewerController`, and `FormViewerScreen` onto the shared contract
- Verified locally:
  - targeted form/export tests green
  - targeted `flutter analyze` green
  - root `dart run custom_lint` green
- Verified on the S21:
  - generic fallback viewer route `/form/fa74c344-0977-4b3a-9263-727796b6af41`
    opens the shared `Form Exported` dialog
  - dedicated 0582B shell route
    `/form/fa74c344-0977-4b3a-9263-727796b6af41?formType=mdot_0582b`
    opens the same dialog
  - dedicated 1126 shell route
    `/form/c1b792f9-1248-420f-a218-a029fce446de?formType=mdot_1126`
    opens the same dialog
  - after export, both sampled device DB rows still report `status = open`
- Proof artifacts:
  - `.codex/tmp/generic-form-viewer-export-dialog.png`
  - `.codex/tmp/mdot-0582b-live-export-dialog.png`
  - `.codex/tmp/mdot-1126-live-export-dialog.png`

## 2026-04-09 Progress Update 8

Shared form export is now verified through the actual save-copy handoff too.

- S21 proof:
  - from the generic 0582B fallback viewer, choosing `Save Copy` from
    `Form Exported` hands off to Android's picker
  - artifact:
    - `.codex/tmp/0582b-save-copy-picker-verified.png`
- This means the current shared form export contract is now honestly closed for:
  - preview
  - standalone export
  - shared follow-up dialog
  - share handoff
  - save-copy handoff
- What remains open in the export plan is product-policy work, not plumbing:
- whether standalone forms should prefer dated-folder defaults
- whether attach-vs-export should be surfaced as one decision point for
  attachable forms
- whether any additional form shells still deserve a dedicated affordance

## 2026-04-09 16:55 ET Additional Export-Contract Progress

What closed in this pass:
- shared standalone form export now has one date-aware filename policy instead
  of per-screen literals
- Forms screen now presents form-export context more honestly:
  - linked vs standalone response state
  - form-only export history

What landed:
- `FormExportFilenamePolicy`
- `ExportFormUseCase` now defaults to that policy
- `MdotHubScreen` no longer hardcodes a separate 0582B export filename
- `FormGalleryResponseTile` now surfaces attachment context
- `FormGalleryScreen` export history is restricted to `form_pdf`

Honest remaining export-policy gap:
- attach-vs-export decision for attachable standalone forms
- dated-folder save path for standalone forms

## 2026-04-09 16:58 ET Attach/Export Contract Closure

- Closed:
  - attachable standalone forms now surface one shared
    `Attach Before Export?` decision
  - 0582B draft-heavy export no longer drifts because the hub saves before
    export
  - shared signed-form export validation now aligns standalone and bundled
    export behavior
- Device proof:
  - `.codex/tmp/0582b-attach-export-decision-3.png`
  - `.codex/tmp/0582b-after-attach-export.png`
  - `.codex/tmp/forms-gallery-0582b-linked-after-attach.png`
  - `.codex/tmp/1126-export-blocked-after-edit.png`

Remaining export-plan gap:
- standalone-form dated-folder behavior if product wants more than the current
  date-aware filename + Android picker flow

## 2026-04-09 18:22 ET Rename-Flow Verification Crash

While finishing the last live proof for attached-form renaming on the S21, the
app hit Flutter's red error surface during driver-driven modal text entry.

What is already device-proven:
- attached-form cards show export-style filenames
- tapping the card opens the form wizard/editor
- `View Form` opens the PDF preview shell
- the rename affordance is visible and opens `Rename Attached Form`

Crash artifacts:
- `.codex/tmp/live_debug/device-crash-yellow-border-driver.png`
- `.codex/tmp/live_debug/debug-server-logs-latest.ndjson`

Captured runtime errors:
- `FlutterError: A TextEditingController was used after being disposed`
- framework assertion: `_dependents.isEmpty`
- duplicate overlay `GlobalKey` errors

Current assessment:
- the attached-form card product contract is live and largely closed
- the remaining gap is the rename-save automation path, which currently
  destabilizes the modal teardown under driver text injection and needs a
  dedicated follow-up

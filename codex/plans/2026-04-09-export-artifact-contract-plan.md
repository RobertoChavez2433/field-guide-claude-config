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
- [ ] Replace hardcoded follow-up labels/messages where the capability record
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
- [ ] Keep pay-app explicitly outside that attach contract
- [ ] Verify attached forms still export inside entry bundle

### Phase 6: Device Validation

- [ ] S21 proof: form preview/export still healthy
- [ ] S21 proof: entry preview/save/share still healthy after migration
- [ ] S21 proof: pay-app export/save/share still healthy after migration
- [ ] S21 proof: entry bundle still includes attached forms correctly

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

# Entry Wizard + Report Screen Bugfix Plan (Contractor-Scoped Roles, UX, Export)

## Objectives
- Make personnel types truly contractor-scoped (schema + data + UI + sync).
- Fix entry wizard keyboard/focus behavior (no forced return to Activities, back closes keyboard first).
- Fix report screen contractor add flow and ordering (prime first).
- Enable inline edits for location and weather on report header.
- Export remains: report PDF + photos.pdf in folder when photos exist.
- Keep tests green by updating keys, helpers, and REQUIRED_UI_KEYS in the same PR.

## Constraints
- Preserve existing data and migrate safely.
- No test break between phases; update tests alongside UI changes.
- Avoid duplicate keys in widget tree; add contractor-scoped keys where needed.
- Avoid pumpAndSettle in tests; use condition-based waits.

---

## Phase 0 - Discovery + Testing Impact (no functional changes)
### Subphase 0.1 - Inventory keys + tests
1. List current keys used by entry wizard and report screens.
2. Identify patrol tests that tap or wait for those keys.
3. Note any duplicate key usage (e.g., add personnel button per contractor).
4. For any key planned for removal, run `rg` to confirm zero references before deletion.

### Subphase 0.2 - Baseline verification
1. Run `flutter analyze`.
2. Run E2E: `entry_lifecycle_test.dart`, `entry_management_test.dart`, `photo_flow_test.dart`.
3. Capture current failure points and logs for comparison.

Deliverable: Baseline notes + key/test map.

---

## Phase 1 - Contractor-Scoped Personnel Types (Schema + Migration + UI)
### Subphase 1.1 - Schema updates (local + remote)
1. Add `contractor_id` column to `personnel_types` table (nullable initially).
2. Add index on (`project_id`, `contractor_id`).
3. Add Supabase migration for `contractor_id` on `personnel_types`.

### Subphase 1.2 - Data migration (preserve existing data)
1. For each project:
   - Load all project-level personnel types (`contractor_id` null).
   - Load all contractors in project.
2. For each contractor + each existing type:
   - Create new PersonnelType row with new id, `contractor_id` set, copy name/short_code/sort_order.
3. Update `entry_personnel_counts` rows:
   - Remap `type_id` using (old_type_id, contractor_id) mapping.
4. Keep legacy project-level rows until migration validation is complete; then remove or hide them.

### Subphase 1.3 - Model + datasource changes
1. Update `PersonnelType` model to include `contractorId` (nullable for legacy rows).
2. Update local datasource queries to filter by contractorId.
3. Update repository methods:
   - `getByContractor(projectId, contractorId)`
   - `createType` requires contractorId
4. Update remote datasource mapping to include contractorId.

### Subphase 1.4 - Provider + Entry Wizard UI
1. Update provider to cache types by contractorId.
2. Entry wizard: use contractor-specific types for counters.
3. Add personnel type dialog must pass contractorId and only update that contractor's counts.
4. Deleting a personnel type only removes it for the owning contractor.

### Subphase 1.5 - Testing keys + implications
1. Add contractor-scoped add button key to avoid duplicates:
   - `TestingKeys.entryWizardAddPersonnelButton(contractorId)`
2. Use this key in UI and update tests to use it.
3. Update `integration_test/patrol/REQUIRED_UI_KEYS.md` to include the new key.
4. Remove any old keys only after `rg` confirms no remaining references.

Deliverable: Contractor-scoped types end-to-end with migration and test-safe keys.

---

## Phase 2 - Entry Wizard UX Fixes (Keyboard + Focus + Navigation)
### Subphase 2.1 - Focus handling around photos
1. Before opening photo source dialog, call `FocusScope.of(context).unfocus()`.
2. After photo name dialog returns (save/cancel), keep focus cleared.
3. Ensure scroll position stays where the user was (do not auto-jump to Activities).

### Subphase 2.2 - Back button behavior
1. Add `PopScope` (or `WillPopScope`) to intercept back:
   - If focus is active, unfocus and block pop.
   - Only show exit dialog if no active focus.
2. Ensure AppBar close button still shows exit dialog.

### Subphase 2.3 - Test implications
1. Update photo flow tests to assert wizard remains in place after adding photo.
2. Add a small helper to dismiss keyboard when needed (condition-based).

Deliverable: Keyboard no longer sticks open; back button closes keyboard first.

---

## Phase 3 - Report Screen Fixes (Contractors + Header Editing)
### Subphase 3.1 - Contractor add flow
1. When selecting a contractor in add dialog, insert placeholder counts in `_personnelCounts`.
2. Ensure contractor row renders even with zero counts.
3. Save flow must persist contractor entry even if counts are zero.

### Subphase 3.2 - Contractor ordering (prime first)
1. Sort contractors before rendering:
   - Prime first, then subs.
   - Secondary sort by contractor name.

### Subphase 3.3 - Inline header edits (location + weather)
1. Make location tappable to open dropdown and persist selection.
2. Make weather tappable to open a selector and persist selection.
3. Update local header state after save.

### Subphase 3.4 - Testing keys + implications
1. Apply existing keys to UI where missing:
   - `TestingKeys.reportContractorCard(contractorId)` on contractor rows.
   - `TestingKeys.reportAddContractorButton` on add CTA.
2. Add new keys for header edits:
   - `TestingKeys.reportHeaderLocationButton`
   - `TestingKeys.reportHeaderLocationDropdown`
   - `TestingKeys.reportHeaderWeatherButton`
   - `TestingKeys.reportHeaderWeatherDropdown`
3. Add a key for add-contractor list item:
   - `TestingKeys.reportAddContractorItem(contractorId)`
4. Update REQUIRED_UI_KEYS and patrol tests to use these keys.

Deliverable: Contractors add correctly, prime-first order, header is editable with testable keys.

---

## Phase 4 - Export Fix (Folder Output + Error Handling)
### Subphase 4.1 - Export content validation
1. Keep current behavior: folder contains report PDF + `photos.pdf` when photos exist.
2. Verify folder export runs only when photos exist and write succeeds.

### Subphase 4.2 - Robust error handling
1. Wrap `saveEntryExport` call in report screen with try/catch.
2. On failure, show snackbar with error and log details.
3. If folder created but write failed, notify user explicitly.

### Subphase 4.3 - Test implications
1. Add an export unit test for `PdfService._writeExportFiles` using a temp directory.
2. For E2E, add manual verification checklist (device file system).

Deliverable: Export is stable and failures are visible; output stays report PDF + photos.pdf.

---

## Phase 5 - Tests + Verification
### Subphase 5.1 - Update existing tests
1. Update helpers to create contractor-specific personnel types:
   - Use `entryWizardAddPersonnelButton(contractorId)` key.
2. Update report screen tests to add contractor and verify row appears.
3. Update tests to verify prime-first ordering.

### Subphase 5.2 - Add targeted tests
1. Entry wizard: add personnel type for Contractor A does not show for Contractor B.
2. Report header: location and weather edits persist after navigation.
3. Export: verify report PDF + `photos.pdf` exist in export folder (unit test or manual step).

### Subphase 5.3 - Manual validation
1. Create entry with multiple contractors and unique personnel types.
2. Generate report, add contractor, ensure prime shown first.
3. Edit header location/weather and confirm persistence.
4. Export with photos and confirm report PDF + photos.pdf in folder.

Deliverable: Test coverage for new behavior; manual QA checklist executed.

---

## Files Likely Touched
- `lib/features/entries/presentation/screens/entry_wizard_screen.dart`
- `lib/features/entries/presentation/screens/report_screen.dart`
- `lib/features/contractors/data/models/personnel_type.dart`
- `lib/features/contractors/data/datasources/local/personnel_type_local_datasource.dart`
- `lib/features/contractors/data/datasources/remote/personnel_type_remote_datasource.dart`
- `lib/features/contractors/data/repositories/personnel_type_repository.dart`
- `lib/features/contractors/presentation/providers/personnel_type_provider.dart`
- `lib/core/database/database_service.dart` (migration)
- `lib/features/pdf/services/pdf_service.dart`
- `lib/shared/testing_keys.dart`
- `integration_test/patrol/REQUIRED_UI_KEYS.md`
- `integration_test/patrol/helpers/patrol_test_helpers.dart`
- `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`
- `integration_test/patrol/e2e_tests/entry_management_test.dart`
- `integration_test/patrol/e2e_tests/photo_flow_test.dart`

---

## Acceptance Criteria
- Personnel types are contractor-scoped and migration preserves existing counts.
- Adding personnel type only affects the selected contractor.
- Entry wizard photo flow does not keep keyboard open or force Activities focus.
- Report screen can add contractors and shows prime first.
- Location and weather can be edited inline on report header.
- Export folder contains report PDF + photos.pdf (when photos exist).
- All updated E2E tests pass and REQUIRED_UI_KEYS.md is current.

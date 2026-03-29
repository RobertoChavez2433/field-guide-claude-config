# UI Refactor Plan — Addendum (2026-03-21)

> **Parent plan**: `2026-03-06-ui-refactor-comprehensive.md`
> **Type**: Addendum — surgical additions and one deletion to existing phases
> **Date**: 2026-03-21
> **Reason**: Audit discovered 9 widgets with design-system violations that were missing from the original plan, 1 deleted screen that must be removed, and 4 widgets with zero testing-key coverage.

---

## Scope Update

| Metric | Original | Updated | Delta |
|--------|----------|---------|-------|
| Widgets in scope | 80+ | 89+ | +9 new widgets |
| Phases affected | 12 | 12 (no new phases) | 0 |
| Steps added | — | 10 new steps | +10 |
| Steps removed | — | 1 (Phase 6.E) | -1 |
| Testing key files added | 0 | 1 (`pdf_keys.dart`) | +1 |
| Testing keys added | 0 | 8 new keys | +8 |
| Widgets with zero key coverage | 0 | 4 identified, all resolved | +4 resolved |

---

## Phase 5.A Additions — ProjectListScreen Sub-Widgets

These widgets are consumed by `project_list_screen.dart` and must be refactored alongside it in Phase 5.A.

### Step 5.A.2 — ProjectTabBar

- **File**: `lib/features/projects/presentation/widgets/project_tab_bar.dart`
- **Agent**: `frontend-flutter-specialist-agent`
- **Classes**: `ProjectTabBar`
- **Violations → Replacements**:
  | Violation | Replacement |
  |-----------|-------------|
  | `BorderRadius.circular(10)` (badge) | `AppTheme.radiusCompact` |
  | Raw spacing values | `AppTheme.space*` tokens |
- **Testing Keys**: Already covered (3 tab keys). No action needed.

### Step 5.A.3 — ProjectFilterChips

- **File**: `lib/features/projects/presentation/widgets/project_filter_chips.dart`
- **Agent**: `frontend-flutter-specialist-agent`
- **Classes**: `ProjectFilterChips`
- **Violations → Replacements**:
  | Violation | Replacement |
  |-----------|-------------|
  | `EdgeInsets.symmetric(horizontal: 16, vertical: 8)` | `EdgeInsets.symmetric(horizontal: AppTheme.space4, vertical: AppTheme.space2)` |
  | `Wrap(spacing: 8)` | `Wrap(spacing: AppTheme.space2)` |
- **Testing Keys**: Already covered (3 filter chip keys). No action needed.

### Step 5.A.4 — ProjectEmptyState

- **File**: `lib/features/projects/presentation/widgets/project_empty_state.dart`
- **Agent**: `frontend-flutter-specialist-agent`
- **Classes**: `ProjectEmptyState`, `EmptyStateVariant`
- **Violations → Replacements**:
  | Violation | Replacement |
  |-----------|-------------|
  | `SizedBox(height: 16)` | `SizedBox(height: AppTheme.space4)` |
  | `SizedBox(height: 8)` | `SizedBox(height: AppTheme.space2)` |
  | `SizedBox(height: 24)` | `SizedBox(height: AppTheme.space6)` |
  | `Icon(size: 64)` | Keep as-is — intentionally large hero icon, no token for 64px (same rationale as Phase 9.C.1 `Icon size: 80`) |
  | `EdgeInsets.all(32)` | `EdgeInsets.all(AppTheme.space8)` |
- **Testing Keys**: Already covered (`projectBrowseButton`). No action needed.

### Step 5.A.5 — ProjectImportBanner

- **File**: `lib/features/projects/presentation/widgets/project_import_banner.dart`
- **Agent**: `frontend-flutter-specialist-agent`
- **Classes**: `ProjectImportBanner`
- **Violations → Replacements**:
  | Violation | Replacement |
  |-----------|-------------|
  | `Colors.blue.shade50` (enrolling bg) | `cs.primaryContainer` or `fg.statusInfo` with 10% opacity |
  | `Colors.green.shade50` (complete bg) | `fg.statusSuccess` with 10% opacity |
  | `Colors.green.shade700` (complete icon) | `fg.statusSuccess` |
  | `Colors.red.shade50` (failed bg) | `cs.errorContainer` |
  | `Colors.red.shade700` (failed icon) | `cs.error` |
  | `Icon(Icons.close, size: 20)` | Use design-system icon sizing |
  | `EdgeInsets.symmetric(horizontal: 16, vertical: 12)` | `EdgeInsets.symmetric(horizontal: AppTheme.space4, vertical: AppTheme.space3)` |
  | `SizedBox(width: 12)` | `SizedBox(width: AppTheme.space3)` |
  | `SizedBox(width: 20, height: 20)` | Keep (progress indicator sizing) |
- **Testing Keys**: **ZERO coverage — must add**. See Testing Keys Phase below.

---

## Phase 6.E Deletion — ProjectSelectionScreen (REMOVED)

**Action**: Delete Phase 6.E entirely from the plan.

**Reason**: `lib/features/sync/presentation/screens/project_selection_screen.dart` was deleted in commit `f1efd01` (2026-03-19). The functionality was consolidated into `project_list_screen.dart`, which is already covered by Phase 5.A.

**Original violations** (`Colors.red:146`, `Colors.grey:213`) are now irrelevant — the file no longer exists.

**Impact**: Phases 6.F through 6.I retain their original numbering (no renumber).

---

## Phase 7.B Additions — AssignmentsStep in ProjectSetupScreen

### Step 7.B.3 — AssignmentsStep

> **Note**: Numbered 7.B.3 because the original plan already defines Step 7.B.2 ("Restyle project widgets").

- **File**: `lib/features/projects/presentation/widgets/assignments_step.dart`
- **Agent**: `frontend-flutter-specialist-agent`
- **Classes**: `AssignmentsStep`, `AssignmentListTile`, `_RoleBadge`
- **Key Decision**: Replace `_RoleBadge` entirely with `AppChip` from the design system (Phase 1.B.3). This eliminates the private widget and reuses the standard component.
- **Violations → Replacements**:
  | Violation | Replacement |
  |-----------|-------------|
  | `_RoleBadge` with `Colors.purple` (admin) | `AppChip.purple()` — reuses `AppTheme.sectionPhotos` purple accent. Semantic mismatch (photos vs role) is accepted; the color value (#BA68C8) reads correctly as "admin purple" to the user. No new token needed. |
  | `_RoleBadge` with `Colors.blue` (engineer) | `AppChip.cyan()` — maps to `cs.primary`. Blue→cyan shift is acceptable; both read as "technical/engineer". |
  | `_RoleBadge` with `Colors.green` (inspector) | `AppChip.green()` — maps to `fg.statusSuccess` |
  | `_RoleBadge` with `Colors.grey` (unknown) | `AppChip.neutral()` — maps to `cs.onSurfaceVariant` |
  | `fontSize: 11` (role badge text) | `AppText.labelSmall` (handled by `AppChip` internals) |
  | `BorderRadius.circular(12)` (role badge) | `AppTheme.radiusMedium` (handled by `AppChip` internals) |
  | `BorderRadius.circular(8)` (search field) | `AppTheme.radiusSmall` |
  | `EdgeInsets.all(16)` | `EdgeInsets.all(AppTheme.space4)` |
  | `EdgeInsets.symmetric(horizontal: 16)` | `EdgeInsets.symmetric(horizontal: AppTheme.space4)` |
  | `EdgeInsets.symmetric(horizontal: 8, vertical: 4)` | Handled by `AppChip` padding |
- **Testing Keys**: Already covered (`assignmentSearchField`, `assignmentTile(userId)`). No action needed.

---

## Phase 8.B Additions — ExtractionBanner and ExtractionDetailSheet

### Step 8.B.2 — ExtractionBanner

- **File**: `lib/features/pdf/presentation/widgets/extraction_banner.dart`
- **Agent**: `frontend-flutter-specialist-agent`
- **Classes**: `ExtractionBanner`, `_ExtractionBannerState`
- **Note**: This widget is mounted in `app_router.dart:763` (nav shell) and is visible on ALL routes with a nav bar. Changes affect global UI.
- **Violations → Replacements**:
  | Violation | Replacement |
  |-----------|-------------|
  | `Colors.white` (icon, text, progress bar) | `fg.textInverse` |
  | `Colors.white70` (elapsed time) | `fg.textInverse.withOpacity(0.7)` |
  | `Colors.white24` (progress bar bg) | `fg.textInverse.withOpacity(0.24)` |
  | `fontSize: 13` (main text) | `AppText.bodySmall` |
  | `fontSize: 12` (elapsed time) | `AppText.bodySmall` |
  | `Icon(size: 20)` | Use design-system icon sizing |
  | `EdgeInsets.symmetric(horizontal: 16)` | `EdgeInsets.symmetric(horizontal: AppTheme.space4)` |
  | `SizedBox(width: 12)` | `SizedBox(width: AppTheme.space3)` |
- **Design Note**: The container backgrounds already use `AppTheme.statusSuccess`, `AppTheme.statusError`, `AppTheme.primaryCyan` — these are correct and should NOT be changed. Only the foreground `Colors.white*` values need replacement with `fg.textInverse` variants.
- **Testing Keys**: **ZERO coverage — must add**. See Testing Keys Phase below.

### Step 8.B.3 — ExtractionDetailSheet

- **File**: `lib/features/pdf/presentation/widgets/extraction_detail_sheet.dart`
- **Agent**: `frontend-flutter-specialist-agent`
- **Classes**: `ExtractionDetailSheet`
- **Consumer**: Opened from `extraction_banner.dart:172` on banner tap.
- **Violations → Replacements**:
  | Violation | Replacement |
  |-----------|-------------|
  | `fontSize: 18` (title) | `AppText.titleLarge` |
  | `fontSize: 14` (stage text) | `AppText.bodyMedium` |
  | `fontSize: 13` (elapsed) | `AppText.bodySmall` |
  | `FontWeight.bold` (title) | Handled by `AppText.titleLarge` |
  | `FontWeight.w600` (current stage) | Use `AppText.bodyMedium` with explicit `fontWeight: FontWeight.w600` or a design-system text style |
  | `EdgeInsets.all(24)` | `EdgeInsets.all(AppTheme.space6)` |
  | `EdgeInsets.symmetric(vertical: 2)` | Keep as-is — below token floor (2px is sub-grid intentional spacing) |
- **Testing Keys**: **ZERO coverage — must add**. See Testing Keys Phase below.
- **Also listed in Phase 10.A** (bottom sheet aspect).

---

## Phase 10.A Additions — Bottom Sheets

### Step 10.A.2 — ProjectDeleteSheet

- **File**: `lib/features/projects/presentation/widgets/project_delete_sheet.dart`
- **Agent**: `frontend-flutter-specialist-agent`
- **Classes**: `ProjectDeleteSheet`, `_ProjectDeleteSheetState`
- **Severity**: SEVERE — extensive raw Material color usage.
- **Sheet Structure**: This sheet is shown via raw `showModalBottomSheet`. Wrap call site with `AppBottomSheet.show()` for consistent drag handle, SafeArea, and glass styling.
- **Violations → Replacements**:
  | Violation | Replacement |
  |-----------|-------------|
  | `Colors.orange.shade50` (warning bg) | `fg.statusWarning` with 10% opacity |
  | `Colors.orange.shade200` (warning border) | `fg.statusWarning` with 40% opacity |
  | `Colors.orange.shade700` (warning icon) | `fg.statusWarning` |
  | `Colors.orange.shade900` (warning text) | `fg.statusWarning` — must remain visually urgent as a data-loss warning; do NOT use `cs.onSurface` (too neutral) |
  | `Colors.red` (destructive button bg) | `cs.error` |
  | `Colors.white` (destructive button text) | `cs.onError` |
  | `BorderRadius.circular(8)` (warning container) | `AppTheme.radiusSmall` |
  | `EdgeInsets.all(16)` | `EdgeInsets.all(AppTheme.space4)` |
  | `EdgeInsets.all(12)` | `EdgeInsets.all(AppTheme.space3)` |
  | `SizedBox(height: 8)` | `SizedBox(height: AppTheme.space2)` |
  | `SizedBox(height: 12)` | `SizedBox(height: AppTheme.space3)` |
  | `SizedBox(height: 16)` | `SizedBox(height: AppTheme.space4)` |
  | `SizedBox(width: 8)` | `SizedBox(width: AppTheme.space2)` |
- **Testing Keys**: **ZERO coverage — must add**. See Testing Keys Phase below.

### Step 10.A.3 — ExtractionDetailSheet (bottom sheet aspect)

- **Note**: The file-level refactor is handled in Step 8.B.3. This step only covers ensuring the sheet structure follows the design system's bottom sheet pattern.
- **Acceptance Condition**: Confirm `AppBottomSheet.show()` is used at the call site in `extraction_banner.dart:172` (currently uses raw `showModalBottomSheet`). Verify drag handle, SafeArea, and glass surface are applied.

---

## Phase 10.B Additions — Dialogs

### Step 10.B.2 — RemovalDialog

- **File**: `lib/features/projects/presentation/widgets/removal_dialog.dart`
- **Agent**: `frontend-flutter-specialist-agent`
- **Classes**: `RemovalDialog`, `RemovalChoice`
- **Violations → Replacements**:
  | Violation | Replacement |
  |-----------|-------------|
  | `fontSize: 13` (warning text) | `AppText.bodySmall` |
  | `BorderRadius.circular(8)` (warning container) | `AppTheme.radiusSmall` |
  | `EdgeInsets.all(12)` | `EdgeInsets.all(AppTheme.space3)` |
  | `SizedBox(height: 12)` | `SizedBox(height: AppTheme.space3)` |
  | `SizedBox(width: 8)` | `SizedBox(width: AppTheme.space2)` |
  | `Icon(..., size: 20)` | Use design-system icon sizing |
- **Note**: `AppTheme.statusWarning` is already used for color — only spacing and typography need replacement.
- **Testing Keys**: Already covered (3 button keys). No action needed.

---

## Testing Keys Phase — Zero-Coverage Widget Keys

**Priority**: Must be completed BEFORE or concurrent with the corresponding refactor steps. Keys should exist before UI refactor touches the widgets.

### Step TK.1 — Add ProjectDeleteSheet Keys to `projects_keys.dart`

- **File**: `lib/shared/testing_keys/projects_keys.dart`
- **Agent**: `qa-testing-agent`
- **Keys to add**:
  ```dart
  static const projectDeleteSheetRemoveCheckbox = Key('projectDeleteSheetRemoveCheckbox');
  static const projectDeleteSheetDatabaseCheckbox = Key('projectDeleteSheetDatabaseCheckbox');
  static const projectDeleteSheetConfirmButton = Key('projectDeleteSheetConfirmButton');
  ```

### Step TK.2 — Add ProjectImportBanner Keys to `projects_keys.dart`

- **File**: `lib/shared/testing_keys/projects_keys.dart`
- **Agent**: `qa-testing-agent`
- **Keys to add**:
  ```dart
  static const projectImportBannerDismiss = Key('projectImportBannerDismiss');
  ```

### Step TK.3 — Create `pdf_keys.dart` with Extraction Keys

- **File**: `lib/shared/testing_keys/pdf_keys.dart` (NEW FILE)
- **Agent**: `qa-testing-agent`
- **Keys to add**:
  ```dart
  import 'package:flutter/foundation.dart';

  /// PDF-related testing keys.
  ///
  /// Includes extraction banner, extraction detail sheet, and PDF import widgets.
  class PdfTestingKeys {
    PdfTestingKeys._();
    static const extractionBannerTap = Key('extractionBannerTap');
    static const extractionDetailCancelButton = Key('extractionDetailCancelButton');
    static const extractionDetailDismissButton = Key('extractionDetailDismissButton');
    static const extractionDetailCloseButton = Key('extractionDetailCloseButton');
  }
  ```

### Step TK.4 — Update Facade `testing_keys.dart`

- **File**: `lib/shared/testing_keys/testing_keys.dart`
- **Agent**: `qa-testing-agent`
- **Action**: Add re-export for `pdf_keys.dart`:
  ```dart
  export 'pdf_keys.dart';
  ```

### Step TK.5 — Wire Keys into Widgets

- **Agent**: `qa-testing-agent`
- **Actions**:
  | Widget File | Key Assignment |
  |-------------|----------------|
  | `project_delete_sheet.dart` | Add `key: ProjectsKeys.projectDeleteSheetRemoveCheckbox` to Remove checkbox |
  | `project_delete_sheet.dart` | Add `key: ProjectsKeys.projectDeleteSheetDatabaseCheckbox` to Database checkbox |
  | `project_delete_sheet.dart` | Add `key: ProjectsKeys.projectDeleteSheetConfirmButton` to Confirm button |
  | `project_import_banner.dart` | Add `key: ProjectsKeys.projectImportBannerDismiss` to dismiss IconButton |
  | `extraction_banner.dart` | Add `key: PdfTestingKeys.extractionBannerTap` to GestureDetector |
  | `extraction_detail_sheet.dart` | Add `key: PdfTestingKeys.extractionDetailCancelButton` to Cancel OutlinedButton |
  | `extraction_detail_sheet.dart` | Add `key: PdfTestingKeys.extractionDetailDismissButton` to Dismiss ElevatedButton |
  | `extraction_detail_sheet.dart` | Add `key: PdfTestingKeys.extractionDetailCloseButton` to Close ElevatedButton |

---

## Phase 12 Update — Cleanup Sweep Additions

Add these 9 files to the Phase 12 final sweep checklist for verification that no raw values remain:

1. `lib/features/projects/presentation/widgets/assignments_step.dart`
2. `lib/features/projects/presentation/widgets/project_empty_state.dart`
3. `lib/features/projects/presentation/widgets/project_filter_chips.dart`
4. `lib/features/projects/presentation/widgets/project_tab_bar.dart`
5. `lib/features/projects/presentation/widgets/removal_dialog.dart`
6. `lib/features/projects/presentation/widgets/project_delete_sheet.dart`
7. `lib/features/projects/presentation/widgets/project_import_banner.dart`
8. `lib/features/pdf/presentation/widgets/extraction_banner.dart`
9. `lib/features/pdf/presentation/widgets/extraction_detail_sheet.dart`

---

## Verification Commands

After each phase step, run:

```bash
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
```

---

## Dependency Order

```
TK.1-TK.5 (testing keys)  ─── can run in parallel with or before any refactor step
Phase 5.A.2-5.A.5         ─── after Phase 5.A.1 (original plan)
Phase 6.E                 ─── DELETE (no work needed)
Phase 7.B.3               ─── after Phase 7.B.2 (original plan), after Phase 1.B.3 (AppChip)
Phase 8.B.2-8.B.3         ─── after Phase 8.B.1 (original plan)
Phase 10.A.2-10.A.3       ─── after Phase 10.A.1 (original plan)
Phase 10.B.2              ─── after Phase 10.B.1 (original plan)
Phase 12                  ─── last (unchanged)
```

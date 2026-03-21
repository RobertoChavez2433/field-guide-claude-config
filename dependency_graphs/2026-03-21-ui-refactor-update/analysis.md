# UI Refactor Plan Update — Dependency Analysis

**Date**: 2026-03-21
**Purpose**: Surgical update to `.claude/plans/2026-03-06-ui-refactor-comprehensive.md`

---

## 1. New Widgets Added Post-March 6 (9 files)

### Project Feature (7 widgets)

| # | File | Classes | Consumer | Violations | Testing Keys |
|---|------|---------|----------|------------|--------------|
| 1 | `lib/features/projects/presentation/widgets/assignments_step.dart` | `AssignmentsStep`, `AssignmentListTile`, `_RoleBadge` | `project_setup_screen.dart:282` | `Colors.*` (x4: purple/blue/green/grey in _RoleBadge), `fontSize:11`, `BR.circular(8,12)`, raw spacing | Covered: `assignmentSearchField`, `assignmentTile(userId)` |
| 2 | `lib/features/projects/presentation/widgets/project_empty_state.dart` | `ProjectEmptyState`, `EmptyStateVariant` | `project_list_screen.dart:405,456,506` | Minor: raw spacing, `Icon(size:64)` | Covered: `projectBrowseButton` |
| 3 | `lib/features/projects/presentation/widgets/project_filter_chips.dart` | `ProjectFilterChips` | `project_list_screen.dart:448` | Minor: raw spacing only | Covered: 3 filter chips |
| 4 | `lib/features/projects/presentation/widgets/project_tab_bar.dart` | `ProjectTabBar` | `project_list_screen.dart:330` | `BR.circular(10)`, raw spacing | Covered: 3 tab keys |
| 5 | `lib/features/projects/presentation/widgets/removal_dialog.dart` | `RemovalDialog`, `RemovalChoice` | `project_list_screen.dart:542` | `fontSize:13`, `BR.circular(8)`, raw spacing | Covered: 3 buttons |
| 6 | `lib/features/projects/presentation/widgets/project_delete_sheet.dart` | `ProjectDeleteSheet`, `_ProjectDeleteSheetState` | `project_list_screen_test.dart` (tests only — used in admin flows) | **SEVERE**: `Colors.orange.shade*` (x4), `Colors.red`, `Colors.white`, `BR.circular(8)`, raw padding | **ZERO keys** |
| 7 | `lib/features/projects/presentation/widgets/project_import_banner.dart` | `ProjectImportBanner` | `project_list_screen.dart:342` | `Colors.blue/green/red.shade*` (x5+), raw icon size, raw spacing | **ZERO keys** |

### PDF Feature (2 widgets)

| # | File | Classes | Consumer | Violations | Testing Keys |
|---|------|---------|----------|------------|--------------|
| 8 | `lib/features/pdf/presentation/widgets/extraction_banner.dart` | `ExtractionBanner`, `_ExtractionBannerState` | `app_router.dart:763` (nav shell) | `Colors.white*` (x4+), `fontSize` (x2: 12,13), raw icon size, raw spacing | **ZERO keys** |
| 9 | `lib/features/pdf/presentation/widgets/extraction_detail_sheet.dart` | `ExtractionDetailSheet` | `extraction_banner.dart:172` (opened from banner) | `fontSize` (x3: 13,14,18), raw spacing | **ZERO keys** |

---

## 2. Deleted Screen

- `lib/features/sync/presentation/screens/project_selection_screen.dart` — **DELETED** in commit `f1efd01`
- Plan Phase 6.E references this file — must be removed
- Functionality consolidated into `project_list_screen.dart`

---

## 3. Blast Radius Summary

### Direct Changes (9 new widget files)
All 9 widgets are leaf widgets — no downstream consumers depend on them except their direct parents.

### Consumers (parent screens that embed the new widgets)
- `project_list_screen.dart` — consumes 5 of 7 project widgets (tabs, filters, empty state, import banner, removal dialog)
- `project_setup_screen.dart` — consumes AssignmentsStep
- `app_router.dart` — embeds ExtractionBanner in nav shell
- `extraction_banner.dart` — opens ExtractionDetailSheet

### Test Files
- `test/features/projects/presentation/screens/project_list_screen_test.dart` — references ProjectDeleteSheet
- `test/features/projects/presentation/widgets/project_delete_sheet_test.dart` — dedicated test file

### Testing Keys Files
- `lib/shared/testing_keys/projects_keys.dart` — already has keys for tabs, filters, empty state, assignments, removal dialog. **Missing**: project_delete_sheet, project_import_banner
- `lib/shared/testing_keys/photos_keys.dart` — **Missing**: extraction_banner, extraction_detail_sheet (or a new `pdf_keys.dart`)
- `lib/shared/testing_keys/testing_keys.dart` — facade file, needs re-export of any new key files

---

## 4. Phase Mapping (where new items slot into existing plan)

| New Widget | Target Phase | Rationale |
|------------|-------------|-----------|
| `project_tab_bar.dart` | Phase 5.A (ProjectListScreen) | Part of project list UI |
| `project_filter_chips.dart` | Phase 5.A (ProjectListScreen) | Part of project list UI |
| `project_empty_state.dart` | Phase 5.A (ProjectListScreen) | Part of project list UI |
| `project_import_banner.dart` | Phase 5.A (ProjectListScreen) | Part of project list UI |
| `assignments_step.dart` | Phase 7.B (ProjectSetupScreen) | Part of project setup wizard |
| `project_delete_sheet.dart` | Phase 10.A (Bottom Sheets) | Modal surface |
| `removal_dialog.dart` | Phase 10.B (Dialogs) | Modal surface |
| `extraction_banner.dart` | Phase 8.B (PDF Import Screens) | PDF feature widget |
| `extraction_detail_sheet.dart` | Phase 8.B (PDF Import Screens) + Phase 10.A (Bottom Sheets) | PDF feature + modal surface |
| Phase 6.E (ProjectSelectionScreen) | **DELETE** | File no longer exists |

---

## 5. Source Code Excerpts

### _RoleBadge (assignments_step.dart:125-156) — worst violation in project widgets
```dart
class _RoleBadge extends StatelessWidget {
  final String role;
  const _RoleBadge({required this.role});
  @override
  Widget build(BuildContext context) {
    final (color, label) = switch (role) {
      'admin' => (Colors.purple, 'Admin'),      // RAW
      'engineer' => (Colors.blue, 'Engineer'),   // RAW
      'inspector' => (Colors.green, 'Inspector'),// RAW
      _ => (Colors.grey, role),                  // RAW
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4), // RAW
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12), // RAW
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(label, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: color)), // RAW fontSize
    );
  }
}
```

### ProjectDeleteSheet (_ProjectDeleteSheetState build, lines 31-153) — most severe violations
- `Colors.orange.shade50/200/700/900` for warning container
- `Colors.red` / `Colors.white` for destructive button
- `BR.circular(8)`, raw padding
- Zero testing keys on any interactive element

### ProjectImportBanner (lines 7-84) — status color violations
- `Colors.blue.shade50` (enrolling/syncing)
- `Colors.green.shade50/700` (complete)
- `Colors.red.shade50/700` (failed)
- `Icon(size: 20)` raw
- Zero testing keys

### ExtractionBanner (_ExtractionBannerState build, lines 24-202) — Colors.white violations
- `Colors.white` (x3), `Colors.white70`, `Colors.white24`
- `fontSize: 13`, `fontSize: 12`
- `Icon(size: 20)` raw
- Zero testing keys

### ExtractionDetailSheet (lines 10-168) — fontSize violations
- `fontSize: 18` (title), `fontSize: 14` (stage text), `fontSize: 13` (elapsed)
- `EdgeInsets.all(24)` raw
- Zero testing keys on Cancel/Dismiss/Close buttons

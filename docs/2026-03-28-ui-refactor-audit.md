# UI Refactor Codebase Audit — 2026-03-28

## Executive Summary

Full codebase audit for refreshing the 2026-03-06 UI refactor plan. The design system has NOT been implemented. The codebase has grown since the original plan (new screens, features, widgets). T Vivid design language remains the target.

---

## 1. Screen Inventory (40 total: 33 routed + 7 nested)

### Auth Feature (10 screens)
| Screen | File | Route | Status |
|--------|------|-------|--------|
| LoginScreen | `lib/features/auth/presentation/screens/login_screen.dart` | `/login` | Uses AppTheme tokens, Theme.of(context).textTheme. Clean. |
| RegisterScreen | `lib/features/auth/presentation/screens/register_screen.dart` | `/register` | Clean token usage. |
| ForgotPasswordScreen | `lib/features/auth/presentation/screens/forgot_password_screen.dart` | `/forgot-password` | Clean. |
| OtpVerificationScreen | `lib/features/auth/presentation/screens/otp_verification_screen.dart` | `/verify-otp` | Clean. |
| UpdatePasswordScreen | `lib/features/auth/presentation/screens/update_password_screen.dart` | `/update-password` | Clean. |
| UpdateRequiredScreen | `lib/features/auth/presentation/screens/update_required_screen.dart` | `/update-required` | **VIOLATIONS**: Hardcoded padding (32, 24, 16), hardcoded fontSize (13, 14). |
| ProfileSetupScreen | `lib/features/auth/presentation/screens/profile_setup_screen.dart` | `/profile-setup` | Clean. |
| CompanySetupScreen | `lib/features/auth/presentation/screens/company_setup_screen.dart` | `/company-setup` | Clean. |
| PendingApprovalScreen | `lib/features/auth/presentation/screens/pending_approval_screen.dart` | `/pending-approval` | Clean. |
| AccountStatusScreen | `lib/features/auth/presentation/screens/account_status_screen.dart` | `/account-status` | **NEW since March 6**. Clean. |

### Entries Feature (6 screens + 1 nested)
| Screen | File | Route | Status |
|--------|------|-------|--------|
| HomeScreen (Calendar) | `lib/features/entries/presentation/screens/home_screen.dart` | `/calendar` (shell tab 2) | ~1800 lines. **TOP VIOLATOR**: 38 inline TextStyle, 31 literal EdgeInsets, 9 literal BorderRadius. |
| EntryEditorScreen | `lib/features/entries/presentation/screens/entry_editor_screen.dart` | `/entry/:projectId/:date`, `/report/:entryId` | ~1500 lines. **UNIFIED** (replaced old wizard + report). 10 TextStyle, 11 EdgeInsets, 4 BorderRadius violations. |
| EntriesListScreen | `lib/features/entries/presentation/screens/entries_list_screen.dart` | `/entries` | 16 inline TextStyle, 10 literal EdgeInsets. |
| DraftsListScreen | `lib/features/entries/presentation/screens/drafts_list_screen.dart` | `/drafts/:projectId` | Hardcoded padding, Colors.black.withValues. |
| EntryReviewScreen | `lib/features/entries/presentation/screens/entry_review_screen.dart` | `/review` | Hardcoded TextStyle + EdgeInsets. |
| ReviewSummaryScreen | `lib/features/entries/presentation/screens/review_summary_screen.dart` | `/review-summary` | **NEW since March 6**. Colors.red hardcoded. |
| _PhotoViewerScreen (nested) | Inside gallery_screen.dart | No route (Navigator.push) | All hardcoded dark colors. |

### Dashboard Feature (1 screen)
| Screen | File | Route | Status |
|--------|------|-------|--------|
| ProjectDashboardScreen | `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` | `/` (shell tab 1) | 13 TextStyle, 18 EdgeInsets, 13 BorderRadius. Colors.amber/orange hardcoded. |

### Projects Feature (2 screens)
| Screen | File | Route | Status |
|--------|------|-------|--------|
| ProjectListScreen | `lib/features/projects/presentation/screens/project_list_screen.dart` | `/projects` (shell tab 3) | 6 Colors.* violations, some literal EdgeInsets. |
| ProjectSetupScreen | `lib/features/projects/presentation/screens/project_setup_screen.dart` | `/project/new`, `/project/:projectId/edit` | 9 EdgeInsets violations. |

### Settings Feature (5 screens)
| Screen | File | Route | Status |
|--------|------|-------|--------|
| SettingsScreen | `lib/features/settings/presentation/screens/settings_screen.dart` | `/settings` (shell tab 4) | Mostly clean. |
| EditProfileScreen | `lib/features/settings/presentation/screens/edit_profile_screen.dart` | `/edit-profile` | **NEW since March 6**. Clean. |
| AdminDashboardScreen | `lib/features/settings/presentation/screens/admin_dashboard_screen.dart` | `/admin-dashboard` | 6 Colors.grey hardcoded. |
| TrashScreen | `lib/features/settings/presentation/screens/trash_screen.dart` | `/settings/trash` | **NEW since March 6**. Hardcoded fontSize (12, 13, 14, 18). |
| PersonnelTypesScreen | `lib/features/settings/presentation/screens/personnel_types_screen.dart` | `/personnel-types/:projectId` | Mostly AppTheme tokens. |

### Quantities Feature (2 screens)
| Screen | File | Route | Status |
|--------|------|-------|--------|
| QuantitiesScreen | `lib/features/quantities/presentation/screens/quantities_screen.dart` | `/quantities` | Colors.orange/amber hardcoded for warning. |
| QuantityCalculatorScreen | `lib/features/quantities/presentation/screens/quantity_calculator_screen.dart` | `/quantity-calculator/:entryId` | AppTheme tokens. Clean. |

### Toolbox Feature (1 screen)
| Screen | File | Route | Status |
|--------|------|-------|--------|
| ToolboxHomeScreen | `lib/features/toolbox/presentation/screens/toolbox_home_screen.dart` | `/toolbox` | **NEW since March 6**. Clean token usage. |

### Calculator Feature (1 screen)
| Screen | File | Route | Status |
|--------|------|-------|--------|
| CalculatorScreen | `lib/features/calculator/presentation/screens/calculator_screen.dart` | `/calculator` | AppTheme tokens. Clean. |

### Gallery Feature (1 screen + 1 nested)
| Screen | File | Route | Status |
|--------|------|-------|--------|
| GalleryScreen | `lib/features/gallery/presentation/screens/gallery_screen.dart` | `/gallery` | 10 Colors.* violations. Nested _PhotoViewerScreen all hardcoded. |

### Todos Feature (1 screen)
| Screen | File | Route | Status |
|--------|------|-------|--------|
| TodosScreen | `lib/features/todos/presentation/screens/todos_screen.dart` | `/todos` | Uses AppTheme tokens. Some literal BorderRadius. |

### Forms Feature (3 screens + 5 nested stubs)
| Screen | File | Route | Status |
|--------|------|-------|--------|
| FormsListScreen | `lib/features/forms/presentation/screens/forms_list_screen.dart` | `/forms` | AppTheme tokens. |
| FormViewerScreen | `lib/features/forms/presentation/screens/form_viewer_screen.dart` | Not directly routed | AppTheme tokens. Nested _PdfPreviewScreen. |
| MdotHubScreen | `lib/features/forms/presentation/screens/mdot_hub_screen.dart` | `/form/:responseId` | **NEW since March 6**. 4 nested stub screens. |

### Sync Feature (2 screens)
| Screen | File | Route | Status |
|--------|------|-------|--------|
| SyncDashboardScreen | `lib/features/sync/presentation/screens/sync_dashboard_screen.dart` | `/sync/dashboard` | **WORST OFFENDER**: Heavy Colors.green/red/amber/grey/orange/white. |
| ConflictViewerScreen | `lib/features/sync/presentation/screens/conflict_viewer_screen.dart` | `/sync/conflicts` | **WORST OFFENDER**: Almost no AppTheme usage, all Colors.*. |

### PDF Feature (2 screens)
| Screen | File | Route | Status |
|--------|------|-------|--------|
| PdfImportPreviewScreen | `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart` | `/import/preview/:projectId` | Some violations. |
| MpImportPreviewScreen | `lib/features/pdf/presentation/screens/mp_import_preview_screen.dart` | `/mp-import/preview/:projectId` | **NEW since March 6**. Some violations. |

### Shell Wrapper
| Component | File | Status |
|-----------|------|--------|
| ScaffoldWithNavBar | `lib/core/router/app_router.dart:648` | Colors.red.shade700, Colors.orange, Colors.white directly. |

---

## 2. Violation Summary

| Violation Type | Count | Files Affected |
|----------------|-------|----------------|
| Inline `TextStyle(` constructors | 447 | 81 |
| Literal `EdgeInsets` values | 377 | 96 |
| Literal `BorderRadius.circular()` | 188 | 50 |
| Raw `Colors.*` usage | 88 | 25 |
| Ad-hoc `withValues(alpha:)` | 183 | 56 |
| Static `AppTheme.*` (not theme-aware) | 1,462 | 102+ |
| Dynamic `Theme.of(context)` usage | 106 | 32 |

### Top 10 Most-Violating Files
| File | TextStyle | EdgeInsets | BorderRadius | Colors.* | Total |
|------|-----------|------------|--------------|----------|-------|
| home_screen.dart | 38 | 31 | 9 | 1 | 79 |
| contractor_editor_widget.dart | 22 | 22 | 6 | 0 | 50 |
| project_dashboard_screen.dart | 13 | 18 | 13 | 4 | 48 |
| gallery_screen.dart | 10 | 9 | 0 | 10 | 29 |
| entries_list_screen.dart | 16 | 10 | 3 | 1 | 30 |
| bid_item_detail_sheet.dart | 14 | 6 | 7 | 0 | 27 |
| hub_proctor_content.dart | 14 | 7 | 6 | 0 | 27 |
| pdf_import_preview_screen.dart | 15 | 5 | 6 | 0 | 26 |
| entry_editor_screen.dart | 10 | 11 | 4 | 0 | 25 |
| calculator_screen.dart | 5 | 6 | 0 | 0 | 11+ |

---

## 3. Theme System State

### What Exists
- `lib/core/theme/colors.dart` — AppColors with 57 named color constants
- `lib/core/theme/design_constants.dart` — DesignConstants with spacing/radius/elevation/animation tokens
- `lib/core/theme/app_theme.dart` — AppTheme facade (1540 lines), 3 ThemeData builders (dark/light/HC)
- `lib/core/theme/theme.dart` — Barrel export

### What Does NOT Exist
- **No `FieldGuideColors` ThemeExtension** — custom colors are NOT theme-reactive
- **No `lib/core/design_system/` directory** — no component library
- **Light/HC themes incomplete** — missing filledButtonTheme, iconButtonTheme, bottomSheetTheme, chipTheme, sliderTheme
- **19 unnamed Color literals** in app_theme.dart ColorScheme constructors

---

## 4. Widget Inventory

### Shared Widgets (9)
- `showConfirmationDialog()`, `showDeleteConfirmationDialog()`, `showUnsavedChangesDialog()` (confirmation_dialog.dart)
- `EmptyStateWidget`, `SearchBarField`, `ContextualFeedbackOverlay`
- `StaleConfigWarning`, `VersionBanner`
- `showStoragePermissionDialog()`

### Feature Widgets (80+)
- **Entries**: 22 widgets + 9 report widgets
- **Photos**: 3 widgets (PhotoNameDialog, PhotoSourceDialog, PhotoThumbnail)
- **Quantities**: 3 widgets (QuantitySummaryHeader, BidItemCard, BidItemDetailSheet)
- **Dashboard**: 4 widgets (DashboardStatCard, BudgetOverviewCard, TrackedItemRow, AlertItemRow)
- **Settings**: 6 widgets (SectionHeader, SignOutDialog, ThemeSection, ClearCacheDialog, SyncSection, MemberDetailSheet)
- **Forms**: 7 widgets (FormAccordion, StatusPillBar, SummaryTiles, HubHeaderContent, HubQuickTestContent, HubProctorContent, FormThumbnail)
- **Projects**: 15 widgets (ProjectImportBanner, ProjectFilterChips, ProjectTabBar, ProjectEmptyState, ProjectSwitcher, RemovalDialog, ProjectDeleteSheet, PayItemSourceDialog, AddLocationDialog, AddEquipmentDialog, BidItemDialog, AddContractorDialog, EquipmentChip, ProjectDetailsForm, AssignmentsStep + AssignmentListTile)
- **PDF**: 2 widgets (ExtractionBanner, ExtractionDetailSheet)
- **Sync**: 2 widgets (SyncStatusIcon, DeletionNotificationBanner)
- **Auth**: 1 widget (UserAttributionText)

### Bottom Sheets (8)
1. BidItemPickerSheet (entries)
2. PhotoSourceDialog (photos)
3. BidItemDetailSheet (quantities)
4. ExtractionDetailSheet (pdf)
5. _ProjectSwitcherSheet (projects)
6. ProjectDeleteSheet (projects)
7. MemberDetailSheet (settings)
8. showReportAddContractorSheet (entries/report)

### Dialogs (30+)
See full list in widgets audit. Includes 3 shared confirmation dialogs, 6 project CRUD dialogs, 9 report dialogs, and various feature-specific dialogs.

---

## 5. Candidates for New Design System Components

Beyond the original 20 components in the plan:

1. **SectionCard** — Colored header strip + icon + title + child. Used 5+ times in entry editor sections.
2. **StatusChip/LabelBadge** — `color.withValues(alpha: 0.1)` bg + colored text. Used 6+ times.
3. **MiniSpinner** — `SizedBox(16-24) + CircularProgressIndicator(strokeWidth: 2)`. Used 19 times.
4. **InfoBanner/WarningBox** — Icon + colored container + message. Used 5+ times.
5. **DragHandle** — Bottom sheet drag handle. Used 3+ times.
6. **CrudFormDialog<T>** — Base pattern for Add/Edit dialogs. Used 4+ times.
7. **AppTheme.accentTint** — `primaryCyan.withValues(alpha: 0.1)`. Used 12+ times.
8. **SnackBarHelper migration** — 102 direct ScaffoldMessenger calls vs 26 SnackBarHelper calls.

---

## 6. Data Layer Summary

### Providers: 22 total
- Auth/Config: AuthProvider, AppConfigProvider, AdminProvider
- Projects: ProjectProvider, ProjectSettingsProvider, ProjectSyncHealthProvider, ProjectImportRunner, ProjectAssignmentProvider
- Entries: DailyEntryProvider, CalendarFormatProvider
- Contractors: ContractorProvider, EquipmentProvider, PersonnelTypeProvider
- Quantities: BidItemProvider, EntryQuantityProvider, LocationProvider
- Toolbox: PhotoProvider, GalleryProvider, InspectorFormProvider, TodoProvider, CalculatorProvider
- Sync/UI: SyncProvider, ThemeProvider

### Repositories: 16 total
### Models: 20 UI-visible models
### Database: v42, 28+ tables

### Key Data-Layer Patterns
- `BaseListProvider<T>` pattern used by 5 providers — refactor must preserve
- `canWrite` guards on all write-capable providers — must not bypass
- Pagination via `PagedResult<T>` in 3 providers
- Role-based filtering at provider level (not just UI)

### Missing Feature: Safety Repeat-Last Toggles
NOT implemented. Needs data layer + UI work.

---

## 7. New Additions Since March 6, 2026

### New Screens (6)
1. AccountStatusScreen (auth)
2. EditProfileScreen (settings)
3. ReviewSummaryScreen (entries)
4. ToolboxHomeScreen (toolbox)
5. MdotHubScreen (forms) + 4 nested stubs
6. MpImportPreviewScreen (pdf)
7. TrashScreen (settings)

### Major Feature Changes
1. Unified Entry Editor (replaced wizard + report)
2. Cascade Soft-Delete system
3. Project Assignments system
4. Deletion Notification Banner
5. LWW Push Guard (sync)
6. MDOT Hub (forms/0582B calculator)
7. Sync Engine Rewrite (test infrastructure)

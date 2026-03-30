# Screens And Navigation Audit

Date: 2026-03-30
Layer: screens, navigation flows, presentation-level behavior, UX-facing hygiene

## Findings

### 1. High | Confirmed
The old forms screen is still alive in non-production navigation surfaces even after `FormGalleryScreen` replaced it in the router.

Evidence:

- Production router uses `FormGalleryScreen`:
  - `lib/core/router/app_router.dart:684`
- Deprecated screen still exists and is exported:
  - `lib/features/forms/presentation/screens/screens.dart:3`
  - `lib/features/forms/presentation/screens/forms_list_screen.dart`
- Test-harness flows still expose it:
  - `lib/test_harness/screen_registry.dart:84`
  - `lib/test_harness/flow_registry.dart:33,48,210,225`

Why this matters:

- The navigation surface is no longer singular.
- Old screen logic keeps receiving maintenance and test attention even though it is no longer the production path.

### 2. High | Confirmed
`EntryEditorScreen` still carries dead state and analyzer-visible async-context issues in active production code.

Evidence:

- Dead members:
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart:99` `_isFetchingWeather`
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart:480` `_autoFetchWeather`
- Async `BuildContext` warnings from current analyzer output:
  - `entry_editor_screen.dart:899`
  - `entry_editor_screen.dart:900`
  - `entry_editor_screen.dart:903`
  - `entry_editor_screen.dart:930`

Why this matters:

- This is not just stylistic debt; it is active screen-layer hygiene debt in one of the app’s largest and most critical screens.

### 3. Medium | Confirmed
Several high-traffic screens remain extremely large, which raises change risk and makes audit/fix work slower.

Evidence:

- `lib/features/entries/presentation/screens/home_screen.dart` `1904` lines
- `lib/features/entries/presentation/screens/entry_editor_screen.dart` `1694` lines
- `lib/features/projects/presentation/screens/project_list_screen.dart` `1065` lines
- `lib/features/projects/presentation/screens/project_setup_screen.dart` `1065` lines
- `lib/features/forms/presentation/screens/mdot_hub_screen.dart` `1084` lines

Why this matters:

- These are no longer isolated exceptions; they form a pattern in the presentation layer.
- UI correctness and cleanup work remain expensive because multiple concerns live together in the same files.

### 4. Medium | Confirmed
`FormGalleryScreen` still depends on external side effects for correctness instead of owning its full data-loading contract.

Evidence:

- `lib/features/forms/presentation/screens/form_gallery_screen.dart:56-65` builds tabs from `InspectorFormProvider.forms`.
- `lib/features/forms/presentation/screens/form_gallery_screen.dart:48-50` only loads documents in `didChangeDependencies`.
- The screen itself never guarantees builtin form loading before rendering the tab set.

Why this matters:

- The screen’s correctness depends on startup seeding/loading having already happened elsewhere.
- That is workable today, but fragile for deep links, test harnesses, and future feature expansion.

### 5. Medium | Confirmed
Document viewing UX is still incomplete for remote-only attachments.

Evidence:

- `lib/features/entries/presentation/widgets/entry_forms_section.dart:326-330`
- Missing local files fall through to an error and a TODO about future signed-URL support.

Why this matters:

- The documents feature is present, but the user-facing recovery path is incomplete on devices that did not create the file locally.

### 6. Medium | Confirmed
`FormViewerScreen` presents itself as a generic form viewer, but only renders the full body for 0582B.

Evidence:

- `lib/features/forms/presentation/screens/form_viewer_screen.dart:266-267` titles the page from the current `formType`.
- `lib/features/forms/presentation/screens/form_viewer_screen.dart:297-306` gates tests, proctors, and standards behind `response.formType == 'mdot_0582b'`.

Why this matters:

- The navigation and UX layer suggests broader form support than the screen actually provides.
- Other forms currently route into a viewer that degrades to a partial experience instead of a true generic renderer.

### 7. High | Confirmed
`FormGalleryScreen` can keep showing the last project's form list after project context disappears because it never clears stale `DocumentProvider.documents`.

Evidence:

- `lib/features/forms/presentation/screens/form_gallery_screen.dart:31-51` only reloads when `_resolvedProjectId` is non-null, non-empty, and changed.
- `lib/features/forms/presentation/screens/form_gallery_screen.dart:56-65` always renders from `docProvider.documents`, even when `hasProject` is false.
- `lib/features/forms/presentation/screens/form_gallery_screen.dart:106-110` disables creation when no project is resolved, but the list body still uses the existing document cache.
- `lib/features/forms/presentation/providers/document_provider.dart:12-13,40-54` stores documents in provider state and has no clear/reset path when project context becomes null.

Why this matters:

- Losing project selection can leave the gallery showing stale forms from a previously selected project.
- The screen looks disabled for creation, but the content can still imply an active project context that no longer exists.
- This is screen-layer state drift, not just provider design debt, because the UI never reconciles the null-project case.

### 8. Medium | Confirmed
`ProjectSetupScreen` still exposes the Assignments tab in the new-project flow even though the screen contract and inline comments describe that tab as edit-only.

Evidence:

- `lib/features/projects/presentation/screens/project_setup_screen.dart:72` defines edit mode as `widget.projectId != null`.
- `lib/features/projects/presentation/screens/project_setup_screen.dart:77-80` creates a `TabController(length: 5)` unconditionally.
- `lib/features/projects/presentation/screens/project_setup_screen.dart:253-258` always builds the five-tab `TabBar`, including `Assignments`.
- `lib/features/projects/presentation/screens/project_setup_screen.dart:287-289` comments that the assignment tab is "Only shown when editing", but the code still always inserts `const AssignmentsStep()`.
- `lib/features/projects/presentation/widgets/assignments_step.dart:15-76` renders the assignment search/list UI directly from `ProjectAssignmentProvider`; it is not a placeholder hidden behind an edit-only guard.

Why this matters:

- The user can reach an assignments surface before project creation is finalized, which does not match the stated flow contract.
- This increases presentation-layer ambiguity around whether assignments are part of draft creation or post-save project administration.
- The mismatch looks like unfinished recent UI work rather than intentional behavior.

### 9. Medium | Confirmed
The harness navigation flows still bypass the production shell route, so screen-level verification outside the live router misses bottom-nav, project-switcher, and banner behavior.

Evidence:

- Production routing wraps dashboard, calendar, projects, and settings in `ShellRoute` with `ScaffoldWithNavBar`:
  - `lib/core/router/app_router.dart:425-456`
  - `lib/core/router/app_router.dart:750-930`
- The harness `dashboard-nav` flow defines those screens as standalone `GoRoute`s with no shell wrapper:
  - `lib/test_harness/flow_registry.dart:88-123`
- The harness screen registry exposes the screens directly rather than through the shell container:
  - `lib/test_harness/screen_registry.dart:32-35`

Why this matters:

- Harness navigation does not exercise the real app chrome that owns the bottom navigation bar, project switcher, extraction banner, offline banner, and sync error toast action.
- A screen can look correct in harness isolation while still regressing once mounted under the production shell.
- This is stale navigation-surface drift introduced by keeping older test/harness paths alive after router evolution.

### 10. Medium | Confirmed
The presentation layer still keeps `FormFillScreen` alive as a second legacy screen identity even though production routing no longer uses it.

Evidence:

- Production router only exposes the forms gallery plus `/form/:responseId` dispatch/fallback:
  - `lib/core/router/app_router.dart:684-715`
- `FormFillScreen` still exists as a public screen alias:
  - `lib/features/forms/presentation/screens/mdot_hub_screen.dart:1112-1120`
- The harness still routes directly to it:
  - `lib/test_harness/screen_registry.dart:93-95`
  - `lib/test_harness/harness_seed_data.dart:190`
- The dedicated screen test still spends coverage on this alias rather than the production router path:
  - `test/features/forms/presentation/screens/form_sub_screens_test.dart:8-17`

Why this matters:

- The app now has two names for the same full-form screen experience: the production router path and the legacy `FormFillScreen` alias.
- Non-production navigation and tests continue to preserve that older identity, which makes screen ownership and routing semantics less clear.
- This is stale presentation compatibility surface, not an active production route.

### 11. Medium | Confirmed
Active screen flows still depend on deprecated Flutter form-field API usage.

Evidence:

- The targeted analyzer run reports `deprecated_member_use` for:
  - `lib/features/projects/presentation/widgets/project_details_form.dart:64`
  - `lib/features/settings/presentation/screens/help_support_screen.dart:95`
- `ProjectSetupScreen` mounts `ProjectDetailsForm` directly in its details tab:
  - `lib/features/projects/presentation/screens/project_setup_screen.dart:412`
- The deprecated call sites are live UI controls:
  - `lib/features/projects/presentation/widgets/project_details_form.dart:63-70`
  - `lib/features/settings/presentation/screens/help_support_screen.dart:89-101`

Why this matters:

- These are not dormant widgets; they are part of the project setup flow and the help/support submission flow.
- Leaving deprecated Flutter API usage in current screens makes future framework upgrades riskier and obscures whether a regression is business logic or framework churn.
- Classification: active screen-layer hygiene debt.

### 12. Low | Confirmed
Screen-layer import cleanup remains incomplete after the `shared.dart` barrel migration.

Evidence:

- The targeted analyzer run reports redundant imports in active presentation screens:
  - `lib/features/auth/presentation/screens/company_setup_screen.dart:10-11`
  - `lib/features/auth/presentation/screens/profile_setup_screen.dart:7-9`
  - `lib/features/auth/presentation/screens/register_screen.dart:6-10`
  - `lib/features/forms/presentation/screens/form_viewer_screen.dart:8-15`
  - `lib/features/forms/presentation/screens/mdot_hub_screen.dart:10-20`
- The files themselves still import both `package:construction_inspector/shared/shared.dart` and narrower testing-key/formatter modules that the analyzer now marks unnecessary.

Why this matters:

- The screen layer still carries post-refactor import residue, which makes dependencies less clear and keeps analyzer noise elevated in presentation files.
- This is low-severity hygiene debt, but it directly affects the readability and integrity of the current screen surfaces.

## Coverage Gaps

- There are tests for `entry_editor_screen`, `settings_screen`, `form_gallery_screen`, and `forms_list_screen`, but no single navigation-level test asserts that the production router and the test harness expose the same form screen flow.
- The stale `FormsListScreen` still has its own dedicated test file, while no router-level test proves that production navigation has fully moved to `FormGalleryScreen`.
- `test/features/projects/presentation/screens/project_save_navigation_test.dart:1-35` is an explicit placeholder with `expect(true, isTrue)`, so the create-project save path still has no real navigation verification.
- `test/features/projects/presentation/screens/project_setup_screen_test.dart:1-217` and `test/features/projects/presentation/screens/project_setup_screen_ui_state_test.dart:1-158` mostly assert mirrored boolean logic and comments rather than pumping `ProjectSetupScreen`; there is no widget-level coverage for the new-project assignments-tab surface, back-navigation prompt flow, or post-save destination behavior.
- `test/features/settings/presentation/screens/settings_screen_test.dart:1-160` is largely static documentation tests under `MaterialApp(home: SettingsScreen())`; it does not verify navigation to `/edit-profile`, `/admin-dashboard`, `/sync/dashboard`, or `/settings/trash`.
- `test/features/projects/presentation/screens/project_list_screen_test.dart:59-87` mounts `ProjectListScreen` under plain `MaterialApp`, so project-card selection, edit, and FAB routes are not exercised through `GoRouter` or the production shell container.
- `test/features/forms/presentation/screens/form_gallery_screen_test.dart:59-75,85-169` verifies tab rendering and a direct-project-ID creation path, but there is no regression test covering project deselection/null-project state to ensure stale form rows are not left visible.
- `test/features/forms/presentation/screens/form_sub_screens_test.dart:8-46` only verifies that legacy alias screens delegate to `MdotHubScreen`; it does not verify the actual production router contract that replaced those direct screen identities.
- No direct widget or integration test was found covering the deprecated dropdown-backed controls in `ProjectDetailsForm` or `HelpSupportScreen`, so framework-facing API drift in those screen flows is currently caught only by analyzer output.

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

## Coverage Gaps

- There are tests for `entry_editor_screen`, `settings_screen`, `form_gallery_screen`, and `forms_list_screen`, but no single navigation-level test asserts that the production router and the test harness expose the same form screen flow.
- The stale `FormsListScreen` still has its own dedicated test file, while no router-level test proves that production navigation has fully moved to `FormGalleryScreen`.

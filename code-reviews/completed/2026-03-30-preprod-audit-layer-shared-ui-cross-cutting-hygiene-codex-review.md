# Shared UI And Cross-Cutting Hygiene Audit

Date: 2026-03-30
Layer: shared theme/UI utilities, common hygiene debt, dead/stale surface area

## Findings

### 1. Medium | Confirmed
The design-token migration is incomplete and still depends on a large deprecated compatibility layer.

Evidence:

- `lib/core/theme/app_theme.dart` is `1670` lines and still exports many deprecated aliases.
- Deprecated aliases are actively marked in source:
  - `lib/core/theme/app_theme.dart:15-18`
  - `lib/core/theme/app_theme.dart:28-35`
  - `lib/core/theme/app_theme.dart:40-56`
  - `lib/core/theme/app_theme.dart:114-118`
- Current analyzer output contains `135` `deprecated_member_use_from_same_package` findings, heavily concentrated in golden tests.

Why this matters:

- The migration path is still wide enough that stale token usage keeps accumulating.
- The shared theme surface is larger and noisier than it needs to be for a pre-production stabilization phase.

### 2. Medium | Confirmed
The codebase still carries meaningful analyzer-visible hygiene debt in handwritten code, not just in generated or archive files.

Evidence:

- Current analyzer output shows `39` issues in the `unused/unnecessary import/unused field/unused element` bucket.
- Representative active-source examples:
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart:99` unused field
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart:480` unused element
  - `lib/features/forms/di/forms_providers.dart` multiple unnecessary imports
  - `lib/features/auth/presentation/screens/company_setup_screen.dart:11` unnecessary import

Why this matters:

- This is precisely the kind of “general hygiene rot” that slows future fix passes.
- The debt is current and handwritten, not just legacy or generated output.

### 3. Medium | Confirmed
Silent exception swallowing remains a broad cross-cutting pattern.

Evidence:

- There are `32` silent `catch (_) / catch(_)` blocks in `lib/`.
- The pattern appears in logging, sync UI, PDF/OCR utilities, and other cross-cutting files.

Why this matters:

- Silent fallback patterns are hard to distinguish from intentional resilience.
- This reduces debuggability in precisely the areas that already have large surface area.

### 4. Low | Confirmed
Large shared utility files remain maintenance hotspots.

Evidence:

- `lib/shared/testing_keys/testing_keys.dart` is `1069` lines.
- `lib/core/logging/logger.dart` is `990` lines.
- `lib/core/theme/app_theme.dart` is `1670` lines.

Why this matters:

- These files accumulate unrelated concerns and make targeted cleanup slower.
- They are not immediate blockers, but they are part of the broader hygiene burden.

### 5. Medium | Confirmed
Dead-or-stale form screen surface still leaks through shared exports and harness infrastructure.

Evidence:

- `lib/features/forms/presentation/screens/screens.dart:3` still exports `forms_list_screen.dart`.
- Test harness files still treat `FormsListScreen` as a supported screen.

Why this matters:

- Shared exports and harness registries are preserving stale surface area instead of helping the old path die off.

### 6. Medium | Confirmed
The shared testing-key surface still preserves obsolete form-list assumptions as if they were current product contracts.

Evidence:

- `lib/shared/testing_keys/toolbox_keys.dart:19-49` defines a dedicated `forms_list_screen` key family and related saved-response keys for the old list screen.
- Those keys still line up with the stale screen and harness references rather than the current production router flow.

Why this matters:

- Shared testing utilities are part of the maintained API of the codebase.
- Keeping stale screen contracts alive in shared helpers makes drift harder to remove and easier to accidentally preserve in new tests.

### 7. Medium | Confirmed
The shared umbrella barrel has become a catch-all compatibility import that blurs layer boundaries instead of enforcing them.

Evidence:

- `lib/shared/shared.dart:1-10` exports datasources, domain models, providers, repositories, preferences, testing keys, time provider, utils, validation, and widgets from one surface.
- The barrel is imported broadly across runtime code, including:
  - `lib/core/router/app_router.dart:14`
  - `lib/features/pdf/services/pdf_service.dart:21`
  - `lib/features/projects/presentation/screens/project_setup_screen.dart:9`
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart:11`
- Repo-wide search during this pass found `84` production imports of `package:construction_inspector/shared/shared.dart`.
- Even shared widgets use the broad barrel where they only need testing keys:
  - `lib/shared/widgets/confirmation_dialog.dart:2`
  - `lib/shared/widgets/permission_dialog.dart:4`

Why this matters:

- A single import now exposes UI helpers, testing contracts, and data-layer primitives together.
- This makes dependency review harder and lets cross-layer coupling spread silently.
- It also makes later cleanup riskier because removing any shared export can have unexpectedly wide impact.

### 8. Medium | Confirmed
The testing-key compatibility surface now preserves multiple overlapping names for the same widget contracts, which reduces test specificity and keeps stale vocabulary alive.

Evidence:

- `lib/shared/testing_keys/navigation_keys.dart:15` aliases `bottomNavCalendar` directly to `calendarNavButton` for test compatibility.
- `lib/shared/testing_keys/navigation_keys.dart:23-25` intentionally gives `addProjectFab` the same key string as `ProjectsTestingKeys.projectCreateButton`.
- `lib/shared/testing_keys/projects_keys.dart:100-104` defines `projectCreateButton = Key('project_create_button')`.
- The real runtime widget in `lib/features/projects/presentation/screens/project_list_screen.dart:356-362` is keyed as `TestingKeys.addProjectFab`.
- `test/features/projects/presentation/screens/project_list_screen_test.dart:280`, `:329`, `:604`, `:619`, and `:634` assert both `TestingKeys.addProjectFab` and `TestingKeys.projectCreateButton` against the same creation surface.
- `lib/shared/testing_keys/toolbox_keys.dart:246-259` still carries legacy generic calculator keys explicitly marked as legacy, and repo-wide search during this pass found no active runtime or test references to those key constants outside the testing-key facade itself.

Why this matters:

- Old and new test names can both pass while referring to one widget, so tests are less precise than they appear.
- The shared testing API is preserving compatibility vocabulary instead of forcing tests onto the current product contract.
- Unused legacy key families are dead shared API surface that still has to be maintained and understood.

### 9. Medium | Confirmed
`SearchBarField` does not handle controller replacement, so the shared widget can leave a listener on an old controller and stop reacting correctly when a parent swaps controllers.

Evidence:

- `lib/shared/widgets/search_bar_field.dart:35-43` adds the listener in `initState()` and removes it in `dispose()`.
- `lib/shared/widgets/search_bar_field.dart:46-47` depends on that listener to call `setState()` and keep the clear-button state in sync.
- The widget does not implement `didUpdateWidget`, so there is no handoff path when `widget.controller` changes.
- It is used as a reusable shared component in:
  - `lib/features/projects/presentation/screens/project_list_screen.dart:1004-1008`
  - `lib/features/quantities/presentation/screens/quantities_screen.dart:181-186`

Why this matters:

- The shared widget contract is only safe when parents never replace controllers.
- If a controller is swapped during rebuilds, the old controller keeps the listener and the new controller will not drive the suffix-icon state.
- This is a reusable-component hygiene bug, not just a local screen quirk.

### 10. Medium | Confirmed
`ContextualFeedbackOverlay` can strand a global overlay on screen when the calling widget unmounts before the auto-dismiss timer fires.

Evidence:

- `lib/shared/widgets/contextual_feedback_overlay.dart:24` stores overlay state in a global static `_currentOverlay`.
- `lib/shared/widgets/contextual_feedback_overlay.dart:113-118` removes the overlay only when `_currentOverlay != null && mounted()`.
- If the caller-provided `mounted()` callback returns `false`, the code does not remove the overlay and does not clear `_currentOverlay`.
- The shared overlay is used from live screen flows such as:
  - `lib/features/entries/presentation/screens/entries_list_screen.dart:83-90`
  - `lib/features/entries/presentation/screens/home_screen.dart:241`

Why this matters:

- A transient feedback overlay can outlive the screen that created it and remain visible after navigation/disposal.
- Because the state is static, this leak is app-global rather than local to one widget instance.
- This is exactly the kind of subtle shared-utility failure that is easy to miss in manual verification and hard to diagnose later.

## Additional Coverage Gaps

- Shared theme behavior is well represented by golden tests, but the analyzer results show the golden suite itself still depends on deprecated theme tokens.
- There is no single hygiene gate today that prevents deprecated theme aliases from continuing to spread.
- `test/golden/widgets/confirmation_dialog_test.dart` is the only direct shared-widget coverage found in this pass; there are no direct widget tests for `SearchBarField`, `VersionBanner`, `StaleConfigWarning`, `showStoragePermissionDialog()`, or `ContextualFeedbackOverlay`.
- There is no test asserting that testing-key aliases are intentional and still mapped to the right live widgets, or that unused legacy testing keys are being retired instead of preserved indefinitely.

### 11. Medium | Confirmed
`shared/domain/domain.dart` is now an empty compatibility barrel that is still exported as part of the primary shared contract.

Evidence:

- `lib/shared/shared.dart:2` still exports `domain/domain.dart`.
- `lib/shared/domain/domain.dart:1-8` contains only barrel comments describing a shared-domain import surface.
- `lib/shared/domain/domain.dart:8` explicitly says the prior `UseCase` base class was removed because no use case extends it.
- Repo-wide search during this pass found no imports of `package:construction_inspector/shared/domain/domain.dart` outside the file’s own self-documenting comment.
- Targeted analyzer output for the shared layer reports `dangling_library_doc_comments` on `lib/shared/domain/domain.dart:1-8`, which matches the file being only comments and no live declarations.
- Git history shows this file comes from older shared-layer infrastructure work rather than an active in-progress change:
  - `99b6558 refactor(domain): add shared domain layer infrastructure`

Why this matters:

- The main shared import surface is still exporting a contract that no longer exists.
- This is stale compatibility scaffolding, not an unfinished current implementation.
- Keeping empty barrels in the canonical shared surface makes dependency review noisier and cleanup planning harder.

### 12. Medium | Confirmed
The testing-key layer is not actually governed by one canonical shared contract; live code still bypasses `TestingKeys` and reaches feature-specific key classes directly.

Evidence:

- `lib/shared/testing_keys/testing_keys.dart:36-38` describes itself as the centralized testing-key surface and “the single source of truth for all widget keys used in tests.”
- Repo-wide search during this pass found `57` direct non-facade references to feature-specific `*TestingKeys` classes in `lib/` and `test/`, excluding the key-definition files and `TestingKeys` facade itself.
- Representative runtime bypasses include:
  - `lib/features/settings/presentation/screens/consent_screen.dart:117,151,258` using `ConsentTestingKeys.*`
  - `lib/features/auth/presentation/screens/register_screen.dart:213` using `ConsentTestingKeys.registerTosCheckbox`
  - `lib/features/projects/presentation/widgets/project_switcher.dart:24,189,200,222` using `ProjectsTestingKeys.*`
  - `lib/features/projects/presentation/screens/project_list_screen.dart:160,165,257,262,844` using `ProjectsTestingKeys.*`
- `lib/shared/testing_keys/consent_keys.dart:16-19` defines active consent keys, but `lib/shared/testing_keys/testing_keys.dart` does not expose `consentScreen`, `consentAcceptButton`, or `registerTosCheckbox` through the `TestingKeys` facade.

Why this matters:

- The documented “single source of truth” is already split across two active public contracts: the large `TestingKeys` facade and direct feature-specific key classes.
- That split makes key ownership less predictable and weakens the integrity of the shared testing API.
- It also makes later cleanup riskier because removing or renaming keys in one surface does not necessarily update the other.

### 13. Medium | Confirmed
The shared widget layer still contains hidden service-composition and broad shared-barrel coupling, so it is not consistently acting as a pure presentation boundary.

Evidence:

- `lib/shared/widgets/permission_dialog.dart:13` constructs `PermissionService()` directly inside `showStoragePermissionDialog(...)`.
- `lib/shared/widgets/permission_dialog.dart:46-84` couples that shared widget flow to lifecycle-observer permission orchestration rather than a passed-in dependency or callback contract.
- Repo-wide search during this pass found only two shared widgets importing the broad umbrella barrel:
  - `lib/shared/widgets/confirmation_dialog.dart:2`
  - `lib/shared/widgets/permission_dialog.dart:4`
- In both files, the broad barrel is only needed for testing-key access rather than for a legitimately mixed shared dependency surface.

Why this matters:

- Shared UI code is still directly instantiating service-layer behavior instead of receiving it through a cleaner contract.
- That blurs the line between shared presentation utilities and integration logic.
- It also means the shared widget layer is preserving exactly the kind of broad-coupling pattern this audit is trying to isolate before production.

### 14. Medium | Confirmed
The shared layer still exports dormant pagination and time abstractions that currently have no consumers in production or test code.

Evidence:

- `lib/shared/providers/providers.dart:1-2` exports both `base_list_provider.dart` and `paged_list_provider.dart`.
- `lib/shared/providers/paged_list_provider.dart:14-165` defines a full generic pagination provider, but repo-wide search during this pass found no subclasses, instantiations, or imports beyond the file itself.
- `lib/shared/shared.dart:7` exports `time_provider.dart`.
- `lib/shared/time_provider.dart:25-121` defines `TimeProvider`, `RealTimeProvider`, `FixedTimeProvider`, and `AppTime`, but repo-wide search during this pass found no uses of `AppTime`, `TimeProvider`, `RealTimeProvider`, or `FixedTimeProvider` outside that file.
- Git history indicates both are older shared abstractions rather than fresh unfinished work:
  - `3a86b18 feat(pagination): Phase 13 Complete - Pagination UI + Sync Chunking`
  - `a5de5fe feat(e2e): Add state reset and time provider for deterministic tests (PR-4A/4B)`
  - `8e03ab4 feat(e2e): Add mock Supabase auth for network-free testing (PR-5A)`

Why this matters:

- The primary shared export surface is still carrying abstractions that look supported but are not actually part of the live architecture.
- Dormant generic infrastructure increases the apparent supported API without providing current value.
- This is stale shared compatibility/dead surface, not a recently started implementation that simply needs finishing.

## Coverage Gaps

- There is still no direct test or lint gate that fails when an empty shared barrel like `shared/domain/domain.dart` remains exported but unused.
- There is no verification guarding the claimed canonical ownership of `TestingKeys` against direct `*TestingKeys` bypasses in runtime code.
- There is no direct widget test around `showStoragePermissionDialog()` even though it owns lifecycle-observer behavior and direct service construction inside the shared widget layer.
- There is no test or static guard asserting that dormant shared exports like `PagedListProvider` and `AppTime` are either intentionally retained or actually consumed.

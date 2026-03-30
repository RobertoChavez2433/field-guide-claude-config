# Providers And State Audit

Date: 2026-03-30
Layer: Provider wiring, ChangeNotifier scope, state ownership, state-layer hygiene

## Findings

### 1. High | Confirmed
The provider refactor introduced more structure, but several providers still behave like large god objects.

Evidence:

- `lib/features/entries/presentation/providers/daily_entry_provider.dart` is `625` lines and still owns CRUD, pagination, date indexing, filtering state, selection state, submit flows, and compatibility APIs.
- `lib/features/projects/presentation/providers/project_provider.dart` is `715` lines and still owns auth-aware initialization, selected-project restoration, screen cache management, and sync-triggering auth reactions.

Why this matters:

- Feature state is still concentrated in a few large mutable objects.
- The new use-case layer did not materially shrink the provider responsibility surface.

### 2. Medium | Confirmed
Provider ordering remains manual and comment-driven, which keeps runtime coupling high.

Evidence:

- `lib/core/di/app_providers.dart:55-137` relies on spread ordering for cross-provider reads.
- `lib/core/di/app_providers.dart:94-95` explicitly documents that forms must appear before entries because entries read forms through `context.read`.

Why this matters:

- The widget tree order is still a hidden dependency graph.
- A future provider reorder can break runtime behavior without a compile-time signal.

### 3. Medium | Confirmed
Multiple provider `dispose()` overrides are now pure no-ops and have become hygiene noise.

Evidence:

- Analyzer flags unnecessary overrides in active provider files, including:
  - `lib/features/auth/presentation/providers/app_config_provider.dart:276`
  - `lib/features/calculator/presentation/providers/calculator_provider.dart:192`
  - `lib/features/contractors/presentation/providers/contractor_provider.dart:123`
  - `lib/features/contractors/presentation/providers/equipment_provider.dart:279`
  - `lib/features/contractors/presentation/providers/personnel_type_provider.dart:232`
  - `lib/features/entries/presentation/providers/daily_entry_provider.dart:625`
  - `lib/features/entries/presentation/providers/entry_export_provider.dart:92`

Why this matters:

- These overrides signal expected lifecycle work where none exists.
- They add noise to already large provider files and make real disposal obligations harder to spot.

### 4. Medium | Confirmed
Presentation code still instantiates datasource objects directly instead of consuming provider-managed state dependencies.

Evidence:

- `lib/features/settings/presentation/screens/settings_screen.dart:36-38` creates `UserCertificationLocalDatasource` directly from `DatabaseService`.

Why this matters:

- The presentation layer is still reaching below repository/provider boundaries for read models.
- This undermines the consistency of the recent DI cleanup.

### 5. Medium | Confirmed
The new `FilterEntriesUseCase` is a thin pass-through, but `DailyEntryProvider` still owns most filtering complexity itself.

Evidence:

- `lib/features/entries/domain/usecases/filter_entries_use_case.dart:4-34` is effectively a repository wrapper.
- `lib/features/entries/presentation/providers/daily_entry_provider.dart:66-75` and surrounding methods still own filter state, filtered collections, and UI-oriented filter orchestration.

Why this matters:

- The domain layer exists structurally, but state complexity remains presentation-heavy.
- This is not wrong by itself, but it means the refactor has not yet delivered a meaningful simplification of provider behavior.

### 6. Medium | Confirmed
The provider registration file still encodes runtime coupling through comments that overstate the level of safety.

Evidence:

- `lib/core/di/app_providers.dart:94-95` says forms must come before entries and that the ordering is "compile-time enforced."
- The actual mechanism here is `MultiProvider` list order, which is a runtime widget-tree contract, not a compile-time dependency guarantee.

Why this matters:

- This makes a fragile runtime dependency sound safer than it is.
- The refactor still relies on developers preserving provider order manually.
- Misleading wiring comments are a real maintenance hazard in a codebase already carrying recent large-scale movement.

### 7. High | Confirmed
Write-permission enforcement is inconsistent across the provider layer. Some providers default to full write access until DI patches them, while others expose mutation paths with no provider-level write guard at all.

Evidence:

- `lib/shared/providers/base_list_provider.dart:196-213` defines `canWrite` with a default of `() => true`.
- Several feature DI modules patch the permission callback only after provider construction:
  - `lib/features/locations/di/locations_providers.dart:13-18`
  - `lib/features/calculator/di/calculator_providers.dart:13-18`
  - `lib/features/contractors/di/contractors_providers.dart:19-38`
  - `lib/features/entries/di/entries_providers.dart:46-60`
  - `lib/features/quantities/di/quantities_providers.dart:16-21`
  - `lib/features/todos/di/todos_providers.dart:13-18`
- Standalone providers also carry permissive defaults:
  - `lib/features/calculator/presentation/providers/calculator_provider.dart:24-26`
  - `lib/features/contractors/presentation/providers/equipment_provider.dart:145-146`
  - `lib/features/todos/presentation/providers/todo_provider.dart:49-51`
- `EntryQuantityProvider` exposes mutating methods without any `canWrite` guard:
  - `lib/features/quantities/presentation/providers/entry_quantity_provider.dart:98-130`
  - `lib/features/quantities/presentation/providers/entry_quantity_provider.dart:135-172`
  - `lib/features/quantities/presentation/providers/entry_quantity_provider.dart:235-278`
  - `lib/features/quantities/presentation/providers/entry_quantity_provider.dart:303-335`
- `PhotoProvider` guards add/delete flows, but `updatePhoto()` does not check `canWrite`:
  - guarded: `lib/features/photos/presentation/providers/photo_provider.dart:80-97,117-130,165-179`
  - unguarded: `lib/features/photos/presentation/providers/photo_provider.dart:99-114`
- `DocumentProvider` exposes attachment/deletion mutations with no auth-backed write callback, and `formProviders` does not inject one:
  - `lib/features/forms/presentation/providers/document_provider.dart:92-130`
  - `lib/features/forms/di/forms_providers.dart:73-75`

Why this matters:

- The provider layer is not a consistent defense-in-depth boundary for viewer vs editor behavior.
- Alternate entrypoints, harnesses, and direct widget/provider tests can instantiate writable providers by default.
- The permission model has become convention-based rather than constructor-enforced.

### 8. Medium | Confirmed
Sync-related provider/state wiring owns long-lived listeners and lifecycle observers without a matching teardown path in the provider layer.

Evidence:

- `lib/features/sync/di/sync_providers.dart:71-80` registers `authProvider.addListener(updateSyncContext)`.
- `lib/features/sync/di/sync_providers.dart:225-226` registers `WidgetsBinding.instance.addObserver(syncLifecycleManager)`.
- No matching `authProvider.removeListener(updateSyncContext)`, `WidgetsBinding.instance.removeObserver(syncLifecycleManager)`, or `syncLifecycleManager.dispose()` call exists in `lib/` or `test/`.
- `lib/features/sync/presentation/providers/sync_provider.dart:107-184` assigns `_syncOrchestrator.onCircuitBreakerTrip`, `onStatusChanged`, and `onSyncComplete`.
- `lib/features/sync/presentation/providers/sync_provider.dart:335-340` does not clear those orchestrator callback fields on dispose.

Why this matters:

- Ownership is implicitly tied to one-time app-lifetime construction instead of explicit notifier lifecycle management.
- Re-init, alternate bootstrap paths, or future provider-graph changes can retain stale callbacks into old state objects.
- This kind of leak is easy to miss because the current production app tends to create these objects once, but the provider layer itself does not enforce that assumption.

Classification: state ownership debt, not dead code.

## Coverage Gaps

- Providers have broad test coverage in aggregate, but composition-order assumptions in `app_providers.dart` are not directly tested.
- No direct tests verify that provider registration order changes would fail fast rather than silently altering runtime behavior.
- No direct test files exist for `InspectorFormProvider` or `app_providers.dart`, even though both are key hubs in the new forms/provider composition model.
- Key provider tests still bypass the production setup paths they rely on at runtime:
  - `test/features/projects/presentation/providers/project_provider_test.dart:11-17` constructs `ProjectProvider(repo)` directly and does not exercise `initWithAuth(...)`
  - `test/features/projects/presentation/providers/project_provider_tabs_test.dart:14-20` does the same
  - `test/features/sync/presentation/providers/sync_provider_test.dart:12-16` uses `SyncOrchestrator.forTesting(...)`
  - no tests reference `buildAppProviders(...)`, `projectProviders(...)`, `entryProviders(...)`, `formProviders(...)`, or `SyncProviders.providers(...)`
- The harness graph diverges from the production provider graph in ways that can mask provider-layer issues:
  - `lib/test_harness/harness_providers.dart:241-252` builds `ProjectProvider` without `initWithAuth(...)`
  - `lib/test_harness/harness_providers.dart:289` creates `SyncProvider(syncOrchestrator)` without the `SyncProviders.providers(...)` callback/lifecycle wiring
  - `lib/test_harness/harness_providers.dart:293-300` creates `InspectorFormProvider` with `canWrite: () => true`
- There are no direct provider tests proving restricted-role behavior for:
  - `EntryQuantityProvider` mutation methods
  - `PhotoProvider.updatePhoto()`
  - `DocumentProvider.attachDocument()` / `deleteDocument()`

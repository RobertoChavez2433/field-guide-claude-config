# 2026-04-08 Lint-First Enforcement Plan

## Objective

Turn the beta audit into enforceable guardrails before more UI/sync iteration
lands, so stale-state bugs, route drift, and bottom-sheet jank surface at
lint/test time instead of during device testing.

## Completion Standard

For any sync-risk or user-facing workflow fix, the change is incomplete until
it includes:

- source fix
- local-state repair path when old builds can poison device state
- regression coverage for dirty-upgrade behavior when applicable

## Phase 1: Enforce The Current Drift

### 1. Route-Intent Ownership

Goal:
- one entry-flow navigation layer instead of scattered direct route calls

Implement:
- create a shared entry-flow route intent helper in entries presentation
- move `entry`, `report`, `review`, and `review-summary` navigation through it
- add a lint that forbids direct calls to those route names outside the helper

Touch first:
- `lib/features/dashboard/presentation/widgets/dashboard_todays_entry.dart`
- `lib/features/dashboard/presentation/widgets/dashboard_sliver_app_bar.dart`
- `lib/features/entries/presentation/screens/home_screen_actions.dart`
- `lib/features/entries/presentation/screens/entries_list_screen.dart`
- `lib/features/entries/presentation/screens/drafts_list_screen.dart`
- `lib/features/entries/presentation/screens/entry_review_screen.dart`
- `lib/features/entries/presentation/screens/review_summary_screen.dart`
- `lib/features/entries/presentation/screens/entry_editor_state_mixin.dart`
- `lib/features/entries/presentation/widgets/entries_list_states.dart`

Verification:
- custom lint catches direct route drift
- targeted widget/unit tests still pass for entry/dashboard flows

### 2. User-Facing Sync Integrity Removal

Goal:
- integrity diagnostics stop leaking into dashboard-facing models/controllers/UI

Implement:
- remove `integrityResults` from the user-facing sync diagnostics snapshot
- remove integrity loading from `SyncQueryService.assembleDiagnostics()`
- remove integrity state from `SyncDashboardController`
- delete the user-facing integrity widget surface from sync dashboard widgets
- add a lint that blocks integrity diagnostics from re-entering user-facing sync
  presentation/query models

Touch first:
- `lib/features/sync/domain/sync_diagnostics.dart`
- `lib/features/sync/application/sync_query_service.dart`
- `lib/features/sync/presentation/controllers/sync_dashboard_controller.dart`
- `lib/features/sync/presentation/widgets/sync_dashboard_diagnostics_widgets.dart`
- affected sync tests

Verification:
- sync dashboard tests assert pending/conflict/transparency only
- custom lint catches reintroduction of integrity UI surface

### 3. Responsive Bottom-Sheet Contract

Goal:
- no more ambiguous scrollable sheets with hidden overflow behavior

Implement:
- harden `AppBottomSheet` with explicit max-height constraints instead of
  arbitrary `Flexible`
- add a dedicated scrollable sheet path for content that is expected to scroll
- migrate the forms new-form picker to the constrained scrollable path
- add a lint that flags direct scrollable widgets passed to `AppBottomSheet.show`

Touch first:
- `lib/core/design_system/surfaces/app_bottom_sheet.dart`
- `lib/features/forms/presentation/screens/form_gallery_screen.dart`
- any additional `AppBottomSheet.show` call sites surfaced by the new lint

Verification:
- custom lint catches raw scrollable builder bodies
- targeted widget tests cover the forms picker and dashboard screens affected by
  the design-system change

## Phase 2: Add Sync Recovery Architecture

### 4. Versioned Repair Runner

Goal:
- fixed builds repair poisoned local sync state on startup instead of inheriting
  it forever

Implement:
- add `SyncStateRepairRunner`
- persist applied repair jobs through sync metadata
- register runner from `sync_initializer.dart`
- ship first repair job for known exhausted equipment tombstone failures

Touch first:
- `lib/features/sync/application/sync_initializer.dart`
- new repair runner/job files under `lib/features/sync/application/`
- `lib/features/sync/engine/sync_metadata_store.dart`
- `lib/features/sync/engine/local_sync_store.dart`

Verification:
- clean-state startup test
- dirty-upgrade repair test

### 5. Queue Healing And Beta Repair Tooling

Goal:
- blocked queue rows become repairable state, not invisible rot

Implement:
- classify exhausted permanent failures as blocked/quarantined
- expose blocked-count/build/schema/repair fingerprints in debug/beta UI
- add beta repair actions:
  - rebuild diagnostics
  - reset blocked queue entries
  - evict and rehydrate one project
  - full local sync reset without auth loss

## Phase 3: Expand Enforcement Beyond The First Slice

### 6. Mutation/State Contracts

Goal:
- create/update/delete always reconcile visible UI immediately

Implement:
- shared mutation completion helpers where provider-owned state must refresh
- contract tests for stale-after-delete/stale-after-save regressions
- lint exploration only where the static signal is honest

### 7. Preload Contracts

Goal:
- screens and sheets are not interactive until required builtin/project data is
  ready

Implement:
- explicit preload state for forms/toolbox/sheets
- contract tests for empty-enabled sheet regressions

### 8. Responsive Content Contracts

Goal:
- dialog/sheet/list layouts adapt without overflow or hidden affordances

Implement:
- keep replacing ad hoc `Flexible`/unbounded scroll patterns with explicit
  constrained layout owners
- add more lints when repeated anti-patterns are concrete enough to detect

## New Lint Candidates To Watch For During Implementation

- no direct entry-flow route calls outside shared intent helpers
- no user-facing sync integrity diagnostics
- no raw scrollable body passed to `AppBottomSheet.show`
- no sync repair job writes outside approved repair owners
- require repair registration for versioned sync repair jobs
- no provider mutation method that returns success without touching canonical
  state or triggering a reload helper
- no interactive form/toolbox action enabled before required preload resolves

The last three are not ready to enforce blindly yet. Treat them as active
design targets while the first enforcement slice lands.

## 2026-04-08 20:05 ET Tooling Closure

- Root enforcement is operational again.
- The `dart run custom_lint` blocker was caused by upstream `custom_lint`
  workspace discovery following generated Windows plugin symlinks before
  analyzer excludes were applied.
- The repo now carries a narrow CLI patch in `third_party/custom_lint_patched`
  and overrides `custom_lint` to that path from `pubspec.yaml`.
- This restores the lint-first workflow requirement:
  - add/adjust rules
  - run root `dart run custom_lint`
  - fix surfaced findings immediately
- Immediate follow-up findings exposed and fixed in the same pass:
  - raw divider usage in equipment manager dialog
  - repair test DB creation aligned with shared `TestDbFactory`
  - lint allowlists updated for the new repair-runner/local-store ownership model

## 2026-04-08 20:33 ET Recovery Enforcement Extension

- Completed the next implementation slice after the initial lint-first pass:
  - blocked queue diagnostics are now first-class
  - operator repair actions now have an explicit service owner
  - build/schema/repair fingerprinting is exposed through the sync dashboard
- New enforcement added:
  - `no_sync_state_repair_runner_instantiation_outside_approved_owners`
    - approved owners:
      - `lib/features/sync/application/sync_initializer.dart`
      - `lib/features/sync/application/sync_recovery_service.dart`
- New runtime contracts now in code:
  - blocked queue rows are surfaced separately from pending uploads
  - repair execution is routed through `SyncRecoveryService`
  - derived diagnostics can be cleared without DB surgery through the new recovery service
- Verification after this slice:
  - targeted `flutter analyze`: green
  - targeted sync widget/unit tests: green
  - root `dart run custom_lint`: green
  - new lint test: green
- Next enforcement candidates now that this slice exists:
  - require new `SyncStateRepairJob` implementations to live under the approved repairs directory
  - require recovery actions in UI to route through `SyncRecoveryService` instead of ad hoc store access
  - once a real blocked-row classification model exists, add lint/test coverage that prevents dashboards from collapsing blocked rows back into generic pending state

## 2026-04-08 20:49 ET Verification Harness Alignment

- On-device verification exposed a new class of architecture drift:
  - the sync dashboard had the correct blocked-vs-pending semantics
  - the driver harness endpoint did not
- This is exactly the kind of invisible verification jank that keeps poisoning
  iteration, so it is now tracked as part of the lint-first implementation plan.

### Fix Landed

- `lib/core/driver/driver_data_sync_handler.dart`
  now classifies queue state into:
  - `pendingCount`
  - `blockedCount`
  - `unprocessedCount`
- Added `test/core/driver/driver_data_sync_handler_test.dart` so the harness
  contract is no longer implicit.

### Enforcement Implication

- We need to keep treating debug/driver surfaces as architecture-owned
  interfaces, not disposable tooling.
- When product semantics split a state dimension, the harness must split it too.

### New Lint / Enforcement Candidate

- candidate:
  - no stale verification surface semantics
- practical meaning:
  - when a user-facing diagnostics model adds a first-class state dimension
    such as `blocked`, any approved driver/debug status endpoint exposing the
    same concept must expose that dimension explicitly rather than collapsing it
    back into a legacy aggregate
- honest status:
  - not ready for static lint yet
  - worth tracking as a contract-test requirement for debug/driver endpoints

## 2026-04-08 21:11 ET Repair Catalog Enforcement Extension

- Landed another honest lint-first enforcement step for sync recovery:
  - `no_sync_state_repair_job_outside_repairs_directory`
- What it enforces:
  - any `SyncStateRepairJob` implementation must live under
    `lib/features/sync/application/repairs/`
- Why this matters:
  - versioned local-state repairs are now a first-class architecture surface
  - letting repair jobs appear ad hoc across unrelated files would recreate the
    same invisible drift we are trying to remove from sync itself

### Runtime Contract Expanded

- `SyncStateRepairRunner` now ships with a three-job default catalog:
  - equipment tombstone retry reset
  - project assignment residue purge
  - builtin form queue residue purge

### Still Not Claimed

- We do not yet have a static lint that proves every repair job file is
  registered in the runner.
- That cross-file completeness check is still better handled by targeted tests
  or a purpose-built repo-wide contract check rather than a dishonest heuristic.

## 2026-04-08 21:43 ET Repair Harness Enforcement Follow-Through

- Live proof work immediately found the next architecture trap:
  - adding deliberate stale-state injection tempts the driver layer to mutate
    `change_log` directly
- The lints did their job and blocked that drift.

### What Changed Instead Of Weakening Lints

- Added `SyncPoisonStateService` as an explicit sync-application owner for
  sanctioned poison-state verification.
- Kept actual SQLite ownership in `LocalSyncStore`.
- Had `SyncInitializer` construct the service so
  `no_sync_handler_construction_outside_factory` stays true.
- Updated the existing ownership allowlists only where the architecture now
  honestly permits it:
  - `SyncPoisonStateService` is an approved `change_log` mutation owner
  - test-only `require_soft_delete_filter` allowlist now includes
    `test/core/driver/driver_data_sync_handler_test.dart`

### New Architectural Standard Clarified

- Debug/driver verification tooling is allowed to create synthetic poisoned
  sync state only when all of the following are true:
  - scenario set is explicit and closed
  - mutation flows through an approved sync owner
  - low-level SQLite access stays inside approved store owners
  - the harness itself is test/debug-only

### Candidate Future Enforcement

- candidate:
  - `no_open_ended_sync_poison_scenarios`
- practical meaning:
  - debug stale-state injection APIs must only accept scenario enums/const
    allowlists, never arbitrary table/column/SQL payloads
- honest status:
  - not implemented yet
  - worth adding if we continue investing in recovery verification tooling

## 2026-04-08 22:44 ET Testing-Notes Enforcement Extension

- The latest beta testing notes were converted into
  `.codex/plans/2026-04-08-beta-testing-notes-spec.md`.
- New enforcement candidates from that spec:
  - `no_dashboard_duplicate_side_panel_before_desktop_redesign`
  - `no_form_creation_action_before_builtin_forms_ready`
  - `no_raw_0582b_item_of_work_options`
- Honest enforcement status:
  - the first and third are realistic once the ownership abstractions land
  - the preload rule should wait until builtin-form readiness has a shared
    explicit owner instead of screen-local heuristics
- Immediate implementation follow-through chosen from the spec:
  - fix activities state-ownership rendering
  - collapse the temporary duplicate dashboard side panel
  - add contract tests before moving on to the deeper forms/0582B wave

## 2026-04-08 23:08 ET Enforcement Follow-Through

- Completed the first chosen follow-through slice:
  - activities state-ownership rendering fixed
  - duplicate dashboard side panel removed
  - regression test added for the activities contract
- Also moved the forms preload contract forward immediately:
  - `FormGalleryScreen` now disables create until builtin forms are ready
  - loading/empty-preload states are explicit
  - tests now lock that behavior
- No new lint was added in this pass because the current forms preload logic is
  still screen-local. The honest next step is to extract a shared readiness
  owner first, then lint against bypassing it.

## 2026-04-08 23:18 ET Export Contract Follow-Through

- Closed one product-contract mismatch directly in code instead of trying to
  lint around it:
  - `ExportFormUseCase` no longer blocks the 0582B hub export flow on missing
    required fields
- No new lint is warranted for this slice yet because the current issue was not
  architectural drift; it was the wrong domain policy encoded in the use case.

## 2026-04-08 23:59 ET 0582B Catalog Enforcement Extension

- Added the next honest form-domain lint:
  - `no_raw_0582b_item_of_work_options`
- What it enforces:
  - fake inline `Mainline / Shoulder / Other` item-of-work literals may not
    re-enter the forms feature once the shipped PDF-backed catalog exists
- Why the first implementation had to be tightened:
  - a repo-wide string-literal rule falsely flagged unrelated `"Other"`
    buckets in sync diagnostics and support categories
  - the correct static scope is the forms feature only
- Runtime/product contracts expanded in the same slice:
  - 0582B now has a single shipped catalog owner for item-of-work codes and
    density-requirement metadata
  - exported forms remain editable, so the generic export path no longer
    conflicts with the product rule that PDFs are artifacts rather than a lock
- New enforcement opportunity surfaced by this slice:
  - once 0582B numbering logic is moved behind a dedicated owner, add a lint
    that prevents ad hoc test-number sequencing outside that owner

## 2026-04-09 06:04 ET Header Ownership Enforcement Extension

- Added `no_nested_form_header_access_outside_header_owners`
- What it enforces:
  - builtin-form code may not reach back into `responseData['header']` outside
    the narrow approved migration/export fallback owners
- Why it was worth adding now:
  - the 1126 header bug was a direct state-ownership split between canonical
    `headerData` and an unsanctioned nested payload fallback
  - this is exactly the kind of invisible jank we want the lint layer to catch
    before device testing
- Honest next enforcement opportunity:
  - if builtin-form header migration expands, consider a follow-up lint that
    prevents ad hoc normalization logic outside the shared
    `FormHeaderOwnershipService`

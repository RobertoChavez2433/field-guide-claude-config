Date: 2026-04-08
Branch: `sync-engine-refactor`
Repo: `local/Field_Guide_App-37debbe5`

# Beta Research Inventory

This artifact is the durable reference for the current beta audit.

It consolidates:
- the live Notion export snapshot
- current CodeMunch repo/index facts
- repo-backed centrality and hotspot signals
- current god-sized file inventory
- routing audit conclusions
- the current lint cleanup state

The current working reference that should be used alongside this inventory is:

- [2026-04-08-codemunch-beta-audit-reference.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-08-codemunch-beta-audit-reference.md)

## Inputs

Primary audit source:
- `C:\Users\rseba\AppData\Local\Temp\notion_beta_export_632c1bec\inner\Field_Guide_App_Notion_Import_2026-04-07 33cc3411c1b58029a802cc3289f9cbab.md`

CodeMunch index source:
- resolved repo: `local/Field_Guide_App-37debbe5`
- indexed at: `2026-04-08T08:37:15.166724`
- note: CodeMunch reported the index as stale versus current HEAD after local edits, so treat the structural rankings below as a stable snapshot, not a final post-edit truth

## Notion Reconciliation

### Previously Open From The Notion Export, Now Closed In Code

- i18n scaffolding is now wired through Flutter localization plumbing and generated `AppLocalizations`.
- responsive-layout adoption is now in place on the remaining obvious shell/export screens.
- user-facing export UX for forms/pay apps now includes a dedicated Settings-based `Saved Exports` surface backed by the unified artifact store.
- contractor bulk import is now wired through the live project-contractors surface with preview/apply flow and repository-backed batch validation.
- app lock is now wired through settings plus a runtime app gate, with PIN/biometric storage and lifecycle auto-lock.
- weather now has durable cached reads with persisted fallback behavior for offline periods.
- `daily-sync-push` now has client/server hardening rather than remaining a deferred note.
- rollback CI enforcement is now live in the quality gate instead of being a scope decision.

### Closed Since The Notion Snapshot

- shipped forms export fidelity is now proven in code for IDR, MDOT 0582B, and MDOT 1126
- pay-app export regression slices were rerun after shared export changes
- production route caller standardization on named routes is in place
- driver shell/forms routing parity with production has been repaired
- auth redirect routing proof is green through the new seam
- sync-hint RPC ownership now lives in the approved owner components and the sync-hint lint rules are green
- the custom lint backlog is currently clean
- `driver_server.dart`, `database_service.dart`, `logger.dart`, `form_pdf_service.dart`, `extraction_pipeline.dart`, `pdf_service.dart`, `project_lifecycle_service.dart`, `realtime_hint_handler.dart`, and `soft_delete_service.dart` have all been reduced below the active beta blocker threshold
- repo follow-through for `codex-admin-sql`, `debug_emit_sync_hint_self`, and sync-hint migration squash is complete
- `daily-sync-push` rate-limiting hardening, rollback CI enforcement, biometric/PIN lock, contractor bulk import, and weather offline cache are now implemented in repo state

## CodeMunch Repo Facts

- 2,000 indexed files
- 13,936 indexed symbols
- 1,913 Dart files
- largest directory clusters:
  - `lib/features/`: 1118 files
  - `test/features/`: 293 files
  - `fg_lint_packages/field_guide_lints/`: 178 files
  - `lib/core/`: 152 files

## Most Imported Files

- `lib/core/design_system/design_system.dart` — imported by 296 files
- `lib/core/logging/logger.dart` — imported by 279 files
- `lib/shared/shared.dart` — imported by 176 files
- `lib/features/pdf/services/extraction/models/models.dart` — imported by 122 files
- `lib/core/database/database_service.dart` — imported by 105 files
- `lib/features/auth/presentation/providers/auth_provider.dart` — imported by 81 files

## Most Central Symbols

- `Logger`
- `disableSentryReporting`
- `PagedResult`
- `BaseRepository`
- `DesignConstants`
- `DatabaseService`
- `SafeRow`
- `DailyEntry`
- `AuthProvider`
- `SyncResult`

Why this matters:
- the original beta god-object queue is now largely burned down
- the remaining larger files are mostly specialized helpers, support utilities, or lower-priority product surfaces rather than the former central blocker facades

## God-Sized File Inventory

Current top Dart files by LOC snapshot:
- `1173 lib/shared/testing_keys/testing_keys.dart`
- `835 lib/features/pdf/services/extraction/shared/post_process_utils.dart`
- `706 lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart`
- `629 lib/core/database/database_upgrade_foundation.dart`
- `580 lib/features/sync/engine/integrity_checker.dart`
- `570 lib/core/database/schema_verifier.dart`
- `551 lib/core/driver/driver_interaction_handler.dart`
- `544 lib/features/pdf/services/extraction/stages/grid_line_removal_support.dart`
- `538 lib/features/pdf/services/extraction/stages/column_detector_v2.dart`
- `538 lib/features/pdf/services/extraction/stages/ocr_grid_page_recognition_stage.dart`
- `528 lib/features/pdf/services/extraction/stages/post_processing_stage_support.dart`
- `524 lib/core/driver/driver_data_sync_handler.dart`
- `516 lib/features/pdf/services/extraction/stages/grid_line_column_detector.dart`
- `514 lib/features/pdf/services/extraction/pipeline/synthetic_region_builder.dart`
- `500 lib/core/database/database_upgrade_sync_engine.dart`

Large provider/controller/service/helper/screen surfaces at or above ~250 LOC:
- `lib/core/database/database_upgrade_foundation.dart` — 629
- `lib/features/sync/engine/integrity_checker.dart` — 580
- `lib/core/database/schema_verifier.dart` — 570
- `lib/core/driver/driver_interaction_handler.dart` — 551
- `lib/core/driver/driver_data_sync_handler.dart` — 524
- `lib/services/photo_service.dart` — 367
- `lib/features/calculator/data/services/calculator_service.dart` — 324
- `lib/features/forms/presentation/screens/mdot_hub_screen.dart` — 299
- `lib/features/todos/presentation/screens/todos_screen.dart` — 279
- `lib/features/pdf/services/mp/mp_extraction_service.dart` — 278
- `lib/features/settings/presentation/screens/consent_screen.dart` — 277
- `lib/features/auth/presentation/screens/register_screen.dart` — 275
- `lib/features/auth/presentation/providers/app_config_provider.dart` — 266
- `lib/features/auth/services/auth_service.dart` — 264
- `lib/features/pay_applications/presentation/screens/contractor_comparison_screen.dart` — 260
- `lib/features/pdf/presentation/helpers/pdf_import_helper.dart` — 259
- `lib/features/projects/presentation/controllers/project_setup_controller.dart` — 257
- `lib/features/settings/presentation/screens/admin_dashboard_screen.dart` — 256
- `lib/features/entries/presentation/controllers/entry_editing_controller.dart` — 254
- `lib/features/forms/presentation/screens/form_viewer_screen.dart` — 254
- `lib/features/forms/presentation/controllers/form_viewer_controller.dart` — 251

## Search-Discovered Hotspots

Compact CodeMunch search for `Provider Service Controller Helper` surfaced these notable candidates:
- `pay_application_detail_screen.dart::_buildBody`
- `sync_providers.dart::SyncProviders.providers`
- `consent_support_factory.dart::createConsentAndSupportProviders`
- `project_setup_controller.dart::ProjectSetupController`
- `project_setup_save_service.dart::ProjectSetupSaveService`
- `entry_editor_helpers.dart::EntryEditorHelpers.isEmptyDraft`

These should stay visible during decomposition because they are likely to regrow complexity even when their parent files shrink.

## Routing Audit Snapshot

Production routing:
- no glaring missing production named routes found during the audit
- no remaining production raw `context.go('/...')` / `push('/...')` callers were left in scope after the named-route standardization wave

What was actually wrong:
- driver/harness navigation still modeled stale shell/forms routes

What was fixed:
- driver navigation now models the production shell contract
- driver forms flow now uses `FormGalleryScreen`
- driver forms flow now dispatches via the live `/form/:responseId` contract
- a dedicated route-contract lint and test were added so that drift is surfaced immediately

## Current Lint Snapshot

At the start of this artifact pass, `dart run custom_lint` reported 5 issues:
- 1 error:
  - `no_sync_hint_rpc_outside_approved_owners` in `sync_hint_channel_rpc_service.dart`
- 4 warnings:
  - `no_state_reload_after_rpc` in `driver_diagnostics_handler.dart`
  - `max_import_count` in `export_entry_use_case_test.dart`
  - `max_import_count` in `quantities_screen_export_flow_test.dart`
  - `max_import_count` in `quantities_screen_pay_app_export_flow_test.dart`

The active cleanup wave is targeting those exact files without changing rule breadth.

## Recommended Execution Order

1. Keep the inventory current so any new god-object regression is visible immediately.
2. Treat the remaining oversized-file list as maintenance-only unless a new surface regrows past the threshold.
3. Re-open decomposition only if the inventory shows a real regression.

## 2026-04-08 19:34 ET Sync, State, And UI Contract Audit

### Audit Scope

- CodeMunch repo index used: `local/Field_Guide_App-37debbe5`
- Targeted audit areas:
  - sync recovery and metadata ownership
  - custom lint plugin architecture and existing sync-integrity rules
  - provider mutation/state reconciliation surfaces
  - entry/dashboard route navigation ownership
  - bottom-sheet/dialog responsive constraints
  - user-facing sync diagnostics exposure

### Current Architecture Anchors

- Custom lint plugin entrypoint: `fg_lint_packages/field_guide_lints/lib/field_guide_lints.dart`
- Active rule families already in place:
  - `architecture/`
  - `data_safety/`
  - `sync_integrity/`
  - `test_quality/`
- Sync durable metadata owner: `lib/features/sync/engine/sync_metadata_store.dart`
- Sync app startup seam: `lib/features/sync/application/sync_initializer.dart`
- Sync query/diagnostics seam: `lib/features/sync/application/sync_query_service.dart`
- User-facing sync dashboard state seam: `lib/features/sync/presentation/controllers/sync_dashboard_controller.dart`
- Shared bottom-sheet owner: `lib/core/design_system/surfaces/app_bottom_sheet.dart`

### Principal Finding

The repo has strong ownership lints for sync boundaries, but it does not yet
have a first-class repair architecture for poisoned local state. That is the
missing layer behind the repeated “fixed code + stale local DB + misleading UI”
cycle.

### Enforceability Matrix

Can be enforced now with code + lint:
- versioned sync-repair runner registration and approved repair ownership
- entry-flow route-intent ownership instead of scattered named-route calls
- no user-facing integrity diagnostics in production sync presentation
- no raw/unconstrained scrollable bottom-sheet bodies

Needs runtime abstraction + contract tests, not lint-only:
- one state-ownership rule per screen
- one mutation contract per provider/screen
- preload-before-interaction guarantees
- responsive affordance correctness for complex dialogs/sheets
- dirty-upgrade sync repair behavior

Lint can support these areas, but should not pretend to fully prove them.

### Concrete Hotspots Found

Sync recovery:
- `lib/features/sync/application/sync_initializer.dart`
  - best place to run a new `SyncStateRepairRunner`
- `lib/features/sync/engine/sync_metadata_store.dart`
  - current durable key-value seam for repair job bookkeeping
- `lib/features/sync/engine/change_tracker.dart`
  - retry exhaustion currently creates queue rot with no healing/requeue path

User-facing sync diagnostics drift:
- `lib/features/sync/application/sync_query_service.dart`
  - still loads integrity metadata into diagnostics
- `lib/features/sync/presentation/controllers/sync_dashboard_controller.dart`
  - still stores `integrityResults`
- `lib/features/sync/presentation/widgets/sync_dashboard_diagnostics_widgets.dart`
  - `SyncIntegritySection` still exists as a user-facing widget surface

Route-intent drift:
- `lib/features/dashboard/presentation/widgets/dashboard_todays_entry.dart`
- `lib/features/entries/presentation/screens/home_screen_actions.dart`
- `lib/features/entries/presentation/screens/entries_list_screen.dart`
- `lib/features/entries/presentation/screens/drafts_list_screen.dart`
- `lib/features/entries/presentation/screens/entry_review_screen.dart`
- `lib/features/entries/presentation/screens/review_summary_screen.dart`
- `lib/features/entries/presentation/screens/entry_editor_state_mixin.dart`

Bottom-sheet/UI jank risk:
- `lib/core/design_system/surfaces/app_bottom_sheet.dart`
  - currently uses `Flexible` around arbitrary child content
  - this does not guarantee visible constraints, scroll affordance, or stable height behavior
- `lib/features/forms/presentation/screens/form_gallery_screen.dart`
  - `_showNewFormDialog()` returns a raw `ListView` inside `AppBottomSheet.show`
  - likely explains the user-reported stuck/empty bottom sheet in Forms

### Standardization Direction Captured From User Guidance

- one explicit local state repair layer
- versioned repair jobs
- derived sync diagnostics treated as rebuildable history, not truth
- queue healing, not just queue retry
- fresh-state tooling for dev and beta
- build/database/repair fingerprints
- clean-state and dirty-upgrade tests for sync fixes
- one state-ownership rule per screen
- one mutation contract
- one route-intent layer
- one preload contract
- one responsive content contract for dialogs/sheets
- contract tests for the behaviors that static analysis cannot prove

### Recommended Next Implementation Order

1. Add `SyncStateRepairRunner` + first versioned repair job for the known exhausted equipment tombstones.
2. Introduce an entry-flow route intent helper and add a lint that forbids direct route strings for that flow outside the helper.
3. Remove integrity diagnostics from the user-facing sync query/controller path instead of only hiding the widget.
4. Replace the fragile bottom-sheet content pattern with explicit constraints and visible affordances, then lint against raw scrollable bottom-sheet bodies.
5. Add dirty-upgrade tests and beta repair tooling after the repair runner lands.

## 2026-04-08 20:13 ET First Enforcement Slice Implemented

### What Landed

- `EntryFlowRouteIntents` now owns the entry-flow route calls that were spread across dashboard and entries presentation.
- New architecture lint: `no_entry_flow_route_calls_outside_intents`
- New sync-integrity lint: `no_user_facing_sync_integrity_surface`
- New architecture lint: `no_scrollable_app_bottom_sheet_body`
- `AppBottomSheet` now enforces an explicit max-height contract and has a scrollable variant with a visible affordance.
- Forms new-form picker now uses the new scrollable bottom-sheet path.
- User-facing sync diagnostics no longer carry integrity data through:
  - `SyncDiagnosticsSnapshot`
  - `SyncQueryService`
  - `SyncDashboardController`
  - sync dashboard widgets

### Verification Snapshot

- Targeted app `flutter analyze`: green
- Targeted sync/forms widget/unit tests: green
- New lint package tests: green
- Lint package `dart analyze`: only pre-existing unrelated infos

### Remaining Tooling Blocker

- Root `dart run custom_lint` still crashes during workspace discovery on a generated Windows plugin path under `windows/flutter/ephemeral/.plugin_symlinks/flusseract/...`
- That blocker should be fixed before claiming full-root lint enforcement is fully operational again

## 2026-04-08 20:17 ET Startup Repair Slice Implemented

## 2026-04-09 13:25 ET Entry Export Contract Audit Closure

### Audit Outcome

The remaining entry export drift was not in bundle generation itself. The real
problem was duplicated presentation ownership:

- `EntryPdfPreviewScreen` owned save/share/export-record side effects inline
- dead `report_pdf_actions_dialog.dart` and
  `report_debug_pdf_actions_dialog.dart` still duplicated old preview/share
  flows even though no callers remained

That combination left the entry export contract structurally weaker than the
new form/pay-app export seams.

### What Landed

- new owner: `lib/features/entries/presentation/support/entry_pdf_action_owner.dart`
- `EntryPdfPreviewScreen` now delegates save/share/export-record work to that
  owner
- dead report PDF action dialogs removed from
  `lib/features/entries/presentation/screens/report_widgets/`
- capability registry updated so entry export/follow-up ownership is explicit
- new lint:
  `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_direct_entry_pdf_actions_outside_owner.dart`

### Verification Snapshot

- targeted app tests: green
- targeted lint test: green
- targeted `flutter analyze`: green
- root `dart run custom_lint`: green

### Honest Remaining Gap

This closes the source architecture seam, but not yet the device proof. The
fresh S21 validation of entry preview/save/share after the owner migration is
still open.

## 2026-04-09 12:08 ET Generic Form Attachment Audit Closure

### Audit Outcome

Form attachment had a naming/ownership drift problem:

- the only create-for-attach and resolve-candidates use cases were 1126-named
- `AttachStep` mutated `response.entryId` inline
- `FormsListScreen` used a separate picker path with no shared attachment owner

That would have made every new attachable form either copy the 1126 stack or
invent another entry-link flow.

### What Landed

- generic use cases:
  - `resolve_form_attachment_entry_use_case.dart`
  - `create_form_attachment_entry_use_case.dart`
- shared owner:
  - `form_entry_attachment_owner.dart`
- rewired consumers:
  - `attach_step.dart`
  - `forms_list_screen.dart`
- new lint:
  - `no_form_response_entry_attachment_mutation_outside_owner`

### Verification Snapshot

- forms-domain/usecase tests: green
- forms-support/widget tests: green
- touched-screen tests: green
- targeted `flutter analyze`: green
- root `dart run custom_lint`: green

### Honest Remaining Gaps

- the generic attach flow still needs S21 proof
- attached-form inclusion in the daily-entry export bundle still needs an
  explicit end-to-end close after this refactor
- `InspectorFormProvider` mutation still leans on extension methods, which is a
  mockability/ownership smell to clean up later

### What Landed

- `lib/features/sync/application/sync_state_repair_runner.dart`
- `lib/features/sync/application/sync_state_repair_job.dart`
- first versioned job:
  - `lib/features/sync/application/repairs/repair_sync_state_v2026_04_08_equipment_tombstones.dart`
- startup registration from:
  - `lib/features/sync/application/sync_initializer.dart`
- supporting queue repair primitive:
  - `lib/features/sync/engine/local_sync_store.dart::resetRetryExhaustedChanges(...)`

### Why This Is The Right First Repair

- The stale blocked-sync condition currently on-device was known exhausted
  `equipment` delete rows carrying the old `contractor:` UUID error.
- The push/router code already has the source fix for contractor-derived
  fallback project IDs.
- That means the missing piece was not another routing change; it was a way to
  reset the poisoned retries on upgraded devices so the fixed code can run.

### Coverage

- `test/features/sync/application/sync_state_repair_runner_test.dart`
  verifies:
  - matching exhausted rows are reset
  - repair metadata is recorded
  - the versioned job only runs once per local DB

## 2026-04-08 20:05 ET Root `custom_lint` Blocker Closed

### Root Cause

- The failure was not in any app lint rule. It was in `custom_lint` workspace
  discovery itself.
- `custom_lint 0.8.1` scans the working directory with a recursive
  `Directory.listSync(recursive: true)` before it evaluates analyzer excludes.
- On this repo, that walk followed
  `windows/flutter/ephemeral/.plugin_symlinks/flusseract` into generated Android
  `.cxx` output and hit a broken generated path, throwing
  `PathNotFoundException` before rule execution.

### Durable Fix

- Vendored the CLI package into:
  - `third_party/custom_lint_patched`
- Patched `lib/src/workspace.dart` in the vendored package so root discovery:
  - walks directories safely
  - skips broken/generated paths instead of crashing
  - does not follow symlinked trees during root discovery
- Wired the app to the patched package through:
  - `pubspec.yaml` `dependency_overrides.custom_lint`

### Why This Approach Was Chosen

- `analysis_options.yaml` excludes could not solve the issue because the crash
  happened before analyzer filtering.
- Shell cleanup of `windows/flutter/ephemeral` would be fragile and would
  regress every time generated plugin artifacts reappeared.
- A repo-owned patch keeps `dart run custom_lint` stable in local dev and CI
  without relying on manual cleanup discipline.

### Verification

- `flutter pub get`: picked up `custom_lint 0.8.1` from path
  `third_party/custom_lint_patched`
- root `dart run custom_lint`: green
- targeted `flutter test test/features/sync/application/sync_state_repair_runner_test.dart`: green

## 2026-04-08 20:33 ET Blocked Queue Visibility + Repair Ownership

### Core Finding

- The dashboard previously reported only pushable pending rows plus grouped
  conflicts.
- Retry-exhausted `change_log` rows were effectively invisible even though they
  are the local poison that keeps invalidating verification sessions.

### Direction Landed

- Blocked queue state is now a first-class diagnostics surface, not an implicit
  absence from pending counts.
- Build/database/repair identity is now part of the sync diagnostics snapshot.

### Ownership Map

- blocked queue SQL ownership:
  - `lib/features/sync/engine/local_sync_store.dart`
- dashboard diagnostics assembly:
  - `lib/features/sync/application/sync_query_service.dart`
- operator-facing repair actions:
  - `lib/features/sync/application/sync_recovery_service.dart`
- startup one-time repair execution:
  - `lib/features/sync/application/sync_state_repair_runner.dart`

### Resulting UX Surface

- The sync dashboard now distinguishes:
  - pending uploads
  - blocked queue rows
  - grouped record conflicts
- The dashboard now exposes:
  - app/build version
  - SQLite schema version
  - repair catalog version
  - applied repair count
  - latest applied repair job metadata

### Enforcement Added

- Added `no_sync_state_repair_runner_instantiation_outside_approved_owners`.
- Repair-runner execution is now constrained to the startup owner and the
  explicit recovery-service owner.

### Remaining Gap

- `Repair Blocked Queue` currently reruns only known versioned repair jobs.
- This is intentionally safer than blindly resetting every blocked `change_log`
  row.
- Broader blocked-row healing still needs more versioned jobs and dirty-upgrade
  coverage.

## 2026-04-08 20:49 ET On-Device Dirty-State Verification

### What Was Proven On The S21

- A deliberately poisoned queue row can now be surfaced, repaired, and cleared
  on the real device without DB surgery after the repair action.
- The exact verified sequence was:
  - blocked synthetic row injected into `change_log`
  - dashboard surfaced `Blocked = 1`
  - repair action converted it to `Pending = 1`
  - sync cleared the row to a clean queue

### Verification Artifacts

- `.codex/tmp/device_sync_verify/sync-dashboard-blocked-before.png`
- `.codex/tmp/device_sync_verify/sync-dashboard-after-repair.png`
- `.codex/tmp/device_sync_verify/sync-dashboard-clean.png`

### Important Finding

- The user-facing dashboard semantics were correct.
- The driver-only verification endpoint was not:
  - `/driver/sync-status` still counted all `processed = 0` rows as pending
  - this meant blocked rows were surfaced honestly in the UI but lied about by
    the harness

### Follow-On Fix

- Updated `lib/core/driver/driver_data_sync_handler.dart` so the driver endpoint
  now exposes:
  - `pendingCount`
  - `blockedCount`
  - `unprocessedCount`
- Added `test/core/driver/driver_data_sync_handler_test.dart` to lock that
  queue classification contract.

### Why This Matters

- The sync system can only be credibly verified if the verification harness uses
  the same queue semantics as the app.
- This closes one of the invisible-headache failure modes:
  - correct product behavior
  - misleading debug endpoint
  - wasted time chasing a non-product bug

## 2026-04-08 21:11 ET Additional Runtime Repair Classes

### Promoted From Legacy/Upgrade Knowledge Into Runtime Repair

- `project_assignments` `change_log` residue:
  - previously only represented in upgrade repair logic and root-cause analysis
  - now promoted into the live versioned runtime repair catalog
- builtin `inspector_forms` `change_log` residue:
  - previously handled only in old migration cleanup after trigger fixes
  - now promoted into the runtime repair catalog for dirty upgraded devices

### Why These Two Matter

- Both are impossible steady-state push rows.
- Both create the exact stale-poison pattern that keeps verification sessions
  from starting from a true current-state baseline.
- Both are safer to purge than to retry because the correct steady state is
  “these rows should not exist in `change_log` at all.”

### New Runtime Ownership Shape

- repair-safe queue purge primitives now live in:
  - `lib/features/sync/engine/local_sync_store.dart`
- versioned repair jobs now live in:
  - `lib/features/sync/application/repairs/`
- catalog assembly remains owned by:
  - `lib/features/sync/application/sync_state_repair_runner.dart`

### Enforcement Added

- Added lint:
  - `no_sync_state_repair_job_outside_repairs_directory`
- This is an honest static rule because path ownership is locally knowable.
- Registration completeness is still better handled as test/process discipline
  until we have a reliable cross-file rule.

## 2026-04-08 21:43 ET Live Device Repair Proof

### What Was Actually Proved

- The new `project_assignments` and builtin-form stale-state repairs are not
  just unit-tested; they executed successfully on the S21 against deliberate
  synthetic poison rows.
- The proof path was:
  - inject one approved poison scenario
  - verify `blocked = 1` through the live driver/dashboard state
  - run the sanctioned repair service
  - verify queue returned to `pending = 0`, `blocked = 0`,
    `unprocessed = 0`

### Why The Harness Needed Refactoring

- The first attempt put synthetic `change_log` writes directly in
  `DriverDataSyncHandler`.
- Existing lints correctly rejected that as architecture drift:
  - `no_change_log_mutation_outside_sync_owners`
  - `no_raw_sync_sql_outside_store_owners`
  - `no_sync_handler_construction_outside_factory`
- Correct fix:
  - `SyncInitializer` now constructs `SyncPoisonStateService`
  - `SyncPoisonStateService` is the explicit sync-application poison owner
  - `LocalSyncStore` owns the actual row injection and query selection
  - driver layer only triggers the sanctioned service

### Product-Surface Insight

- `rerunKnownRepairs()` is broader than “reset blocked queue.”
- Some repair jobs reset retries.
- Some repair jobs purge impossible stale rows.
- Therefore user/dev copy must stay generic:
  - `Repair Sync State`
  - not `Reset blocked rows`

### Fresh-State Tooling Progress

- We now have three layers of stale-state recovery:
  - startup versioned repair runner
  - operator-triggered repair service
  - driver-only deliberate poison injection for proof
- Debug settings now expose:
  - `Repair Sync State`
  - `Rebuild Sync Diagnostics`

### Still Missing

- Cold-start upgrade proof for these two repair classes on the already-upgraded
  S21 is still not explicitly replayed.
- We would need either:
  - repair-metadata reset tooling
  - or a clean upgraded fixture device state
  - to prove the exact first-launch metadata gate, not just the shared repair
    job execution path

## 2026-04-08 22:15 ET One-Screen Sync Status Audit

### Corrected Direction

- Do not split sync into a production `Sync Status` screen plus a separate
  dashboard.
- Keep the existing sync dashboard route and collapse it into one surface with:
  - user-safe status always visible
  - raw diagnostics/debug tools only in debug mode

### Key Findings

- `ConflictResolver` is present and functional, but it only does:
  - LWW winner selection
  - grouped conflict history logging via `conflict_log`
- `ConflictViewerScreen` remains a debug inspection/replay tool.
- The actual missing product seam was the absence of provider-owned sync
  attention projection.

### Code Seams Confirmed

- engine resolution owner:
  - `lib/features/sync/engine/conflict_resolver.dart`
- grouped conflict restore/dismiss owner:
  - `lib/features/sync/data/datasources/local/conflict_local_datasource.dart`
- raw conflict UI:
  - `lib/features/sync/presentation/screens/conflict_viewer_screen.dart`
- single user-facing sync route/screen:
  - `lib/core/router/routes/sync_routes.dart`
  - `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`
- status propagation seams:
  - `lib/features/sync/presentation/providers/sync_provider.dart`
  - `lib/features/sync/presentation/widgets/sync_status_icon.dart`
  - `lib/core/router/shell_banners.dart`

### Architecture Changes Landed

- `SyncProvider` now owns:
  - pending upload projection
  - blocked queue projection
  - grouped conflict attention projection
  - deduped user-safe sync notices
- The user-facing screen now reads `Sync Status`.
- Debug-only sections remain on the same route rather than moving to a second
  production screen.
- The raw conflict route is now debug-only.
- The sync status actions reuse the existing help/support flow for
  `Report Sync Issue`.

### New Enforcement

- Added lint:
  - `no_sync_conflict_navigation_outside_debug_owners`

### Next Lint Opportunities

- `no_conflict_repository_usage_outside_debug_owners`
- `no_sync_debug_surface_outside_debug_gates`
- `no_sync_dashboard_debug_copy_in_user_surface`

### Remaining Product Gap

- This is still automatic resolution plus notices, not a full merge editor.
- The next honest product improvement is a support taxonomy so sync reports are
  classified well enough to be actionable without handing users raw
  conflict-log tooling.

## 2026-04-08 22:44 ET Beta Testing Notes Spec Audit

### New Working Spec

- Added `.codex/plans/2026-04-08-beta-testing-notes-spec.md` as the current
  working implementation spec for the latest beta device-testing notes.

### High-Signal Findings

- The latest notes are not one class of bug. They cluster into six architecture
  buckets:
  - stale state ownership after mutation
  - route-intent honesty
  - preload contract gaps
  - responsive dialog/sheet/layout issues
  - 0582B domain/export correctness
  - cross-account/resume restoration safety
- Several user-reported items are already partially addressed in source and
  should be treated as verification work, not blindly reimplemented:
  - continue-today title honesty
  - submitted-entry prompt
  - some equipment dialog scroll affordance work
- The highest-confidence still-open code defects are:
  - activities section reading from a stale widget entry snapshot after save
  - wide dashboard duplicating content through the temporary side panel
  - forms gallery/create flow lacking a real builtin-form preload contract
  - 0582B export validation remaining stricter than the intended product flow
  - trash visibility rules likely being too weak for cross-account isolation

### Enforcement Follow-Up

- New lint candidates promoted into the live backlog:
  - no dashboard duplicate side panel before desktop redesign
  - no form creation action before builtin forms are ready
  - no raw 0582B item-of-work options outside a dedicated registry/owner
- Runtime/test-first items still not honest enough for static lint:
  - state ownership per screen
  - mutation completeness
  - trash scope correctness
  - foreground resume safety

## 2026-04-08 23:08 ET First Testing-Notes Implementation Wave

### Landed

- `EntryActivitiesSection` no longer depends solely on the widget-entry snapshot
  for read-only rendering after save.
- The dashboard no longer duplicates quick stats/budget content on wide layouts.
- `FormGalleryScreen` now has an explicit builtin-form preload contract:
  - loading state while builtin forms are loading
  - retryable empty state when builtin forms are unavailable
  - disabled create action until builtin forms are ready
  - corrected bottom-sheet close context for the add-form flow

### Verification

- `test/features/entries/presentation/widgets/entry_activities_section_test.dart`
- `test/features/forms/presentation/screens/form_gallery_screen_test.dart`
- targeted `flutter analyze`
- root `dart run custom_lint`

### What This Closed

- one real stale-after-save state-ownership defect
- one real desktop duplicate-content regression
- one real preload-contract gap in the forms gallery
- one concrete bottom-sheet interaction bug that matched the user-reported
  stuck add-form sheet behavior

## 2026-04-08 23:18 ET 0582B Export Policy Slice

### Landed

- `ExportFormUseCase` no longer validates required export fields before PDF
  generation.

### Why This Was Safe

- The user-reported blocker was on the 0582B hub export path, which uses
  `FormExportProvider -> ExportFormUseCase`.
- That path does not depend on the later generic `markAsExported()` repository
  transition to generate the PDF artifact.

### What This Closed

- the concrete blocker where incomplete 0582B forms failed before export even
  though the intended product flow is “export now, edit later”

## 2026-04-08 23:59 ET 0582B Catalog + Editable Export Follow-Through

### Concrete Findings Closed

- The 0582B quick-test UI was still using fake item-of-work placeholders
  (`Mainline / Shoulder / Other`) even though the shipped PDF carries a real
  page-2 density-requirements table with export codes, spec sections, and
  minimum compaction thresholds.
- The Forms Gallery stale-response problem was not in the save path itself; it
  was a missing reload contract:
  - `DocumentProvider.loadDocuments()` only ran on project changes
  - returning from `/form/:responseId` did not refresh the gallery list
- The generic form-viewer export path still encoded the wrong product contract:
  - exported responses became uneditable
  - re-export from an already exported response was blocked by local status
    semantics, even though exported PDFs are meant to be artifacts, not locks

### What Landed

- New 0582B catalog:
  - `lib/features/forms/data/registries/mdot_0582b_item_of_work_catalog.dart`
- New shared formatting helpers:
  - `lib/features/forms/data/services/mdot_0582b_display_formatter.dart`
- 0582B UI/export surfaces updated:
  - `hub_quick_test_content.dart`
  - `form_viewer_sections.dart`
  - `entry_form_card.dart`
  - `mdot_0582b_pdf_filler.dart`
- Forms Gallery return-path reloads:
  - `form_gallery_response_tile.dart`
  - `form_gallery_screen.dart`
- Editable-export contract update:
  - `form_response.dart`
  - `form_response_repository.dart`
  - `form_viewer_controller_test.dart`

### Enforcement Added

- `no_raw_0582b_item_of_work_options`
  - purpose: keep fake inline 0582B options from reappearing once the shipped
    catalog exists
  - tuned after first run so it only targets the forms feature and does not
    flag unrelated `"Other"` diagnostics buckets elsewhere in the app

## 2026-04-09 00:34 ET 1126 Header + Pay-App Workbook Audit

### MDOT 1126 Header Findings

- The current 1126 implementation is internally inconsistent about header
  ownership:
  - creation path seeds known header values into `FormResponse.headerData`
  - UI render path (`header_step.dart`) reads only `responseData['header']`
  - edit path (`mdot_1126_form_screen.dart::_patchHeader`) persists edits back
    into `responseData['header']`
- This is the direct root cause for the user report that the SESC header does
  not auto-load like 0582B.
- It also means the 1126 wizard is violating the intended standard:
  - canonical persisted model source should be `headerData`
  - legacy nested header payload should be treated as compatibility input, not
    the active source of truth

### Standardization Direction

- Reuse `AutoFillService`, but extend it with builtin-form-specific header
  helpers instead of ad hoc screen-local header maps.
- Normalize 1126 on load:
  - merge `headerData`
  - then any legacy `responseData['header']` values as fallback only
  - then known project/profile autofill for any still-missing values
  - persist the canonical result back into `headerData`
  - strip legacy nested header payload from `responseData`

### Pay-App Workbook Findings

- Current pay-app export is artifact-correct but product-incomplete:
  - each pay app persists as its own `.xlsx`
  - there is no project workbook accumulation/export flow
  - the dialog copy and action model still imply “single file” rather than
    “project workbook”
- Best-fit implementation without breaking the current export-artifact/sync
  model:
  - keep the internal saved pay-app artifact as a per-pay-app workbook
  - add a separate project-workbook export path that builds a user-facing
    workbook from the saved pay-app artifacts for that project
  - this preserves snapshot fidelity while adding the inspector-facing export
    model the user expects

## 2026-04-09 06:04 ET 1126 Header Ownership + Project Workbook Closure

### What Landed

- Added `FormHeaderOwnershipService` as the sanctioned owner for migrating
  legacy builtin-form nested headers into canonical `FormResponse.headerData`.
- Rewired `Mdot1126FormScreen` to use that service during load, merging:
  - canonical header data
  - legacy nested header fallback
  - known project/profile autofill for still-missing values
- Simplified `Mdot1126HeaderStep` so it now renders directly from
  `parsedHeaderData` instead of trying to merge a second screen-local header
  source.
- Added `ProjectPayAppWorkbookFileService` and
  `RebuildProjectPayAppWorkbookUseCase`.
- Reworked pay-app post-export behavior so the canonical per-project workbook
  is rebuilt and written to a stable app-documents path on every successful
  pay-app export.

### Enforcement Added

- `no_nested_form_header_access_outside_header_owners`
  - purpose: prevent new builtin-form code from drifting back to
    `responseData['header']` as a second source of truth
  - approved owners limited to migration/export compatibility files only

### Research Outcome

- The right standard is now clearer:
  - `headerData` is the canonical persisted header owner for builtin forms
  - nested header payloads are compatibility input only
  - project workbook export should be a maintained local aggregate artifact,
    not rebuilt only at the last save prompt

## 2026-04-09 06:28 ET S21 Device Validation Inventory

### Confirmed On-Device Passes

- Dashboard hydration:
  - Springfield still loads with `131` pay items on the live device
  - the earlier stale `0 pay items` regression remains closed in the current
    build
- Activities state-ownership repair:
  - editing `Activities`, saving, and returning to read-only now shows the
    exact new text immediately
  - this validates the controller/live-state rendering fix, not just the
    widget test
- Continue-today route intent:
  - dashboard shows `Continue Today's Entry`
  - tapping it reopens the same draft
  - entry title remains the honest date label instead of `New Entry`
- Calendar functional backdating:
  - selecting a prior date still surfaces that day's entries
  - tapped prior-day entry reopened correctly
- Pay-app export path:
  - date-range dialog -> zero-entry warning -> number confirmation ->
    exported dialog is working end to end on-device
  - exported dialog now correctly offers:
    - `Save Project Workbook`
    - `Share File`
  - `Save Project Workbook` launches Android DocumentsUI, proving the save-copy
    handoff exists now

### Confirmed On-Device Failures / Partial Closures

- Calendar layout:
  - still visibly overflowed on-device
  - screenshot captured the live Flutter warning stripe:
    `BOTTOM OVERFLOWED BY 154 PIXELS`
- MDOT 1126 header autofill:
  - improvement is partial, not complete
  - populated:
    - project name
    - contractor name
    - inspector name
  - still blank on-device:
    - permit number
    - location
- Forms gallery create flow:
  - add sheet is much better visually:
    - real form options render
    - `Scroll for more` affordance is visible
  - but create-path closure is still not proven:
    - selecting `MDOT 1126 Weekly SESC` from the sheet dismissed it and left
      the app on `/forms`
    - this may be a real create-flow bug or a remaining targeting ambiguity,
      but it is not honest to mark the `+` path complete yet
- Conflict viewer clarity:
  - grouped conflicts load
  - card labels remain too generic to distinguish logical records on-device

### New Restoration / Export Finding

- The highest-severity new device issue is the Android picker return path:
  - after entering the pay-app `Save Project Workbook` flow and relaunching the
    app, the visible UI resumed into an orphaned `Pay Items` screen with
    `0 items`
  - route state and visible UI drifted apart
  - Android back returned to the system picker instead of a valid app root
- Important scoping note:
  - force-stop + relaunch returns correctly to `Projects`
  - this isolates the bug to resume/restoration around the picker/export flow,
    not generic cold-start auth routing

### Useful Artifact Index

- Forms:
  - `.codex/tmp/s21-forms-add-sheet.png`
  - `.codex/tmp/s21-1126-saved-response-open.png`
  - `.codex/tmp/s21-0582b-saved-response-open.png`
- Pay app:
  - `.codex/tmp/s21-pay-app-export-open.png`
  - `.codex/tmp/s21-pay-app-export-step2.png`
  - `.codex/tmp/s21-pay-app-export-step3.png`
  - `.codex/tmp/s21-pay-app-export-finished.png`
  - `.codex/tmp/s21-pay-app-save-workbook-system-picker.png`
- Entry/calendar:
  - `.codex/tmp/s21-entry-after-start-today.png`
  - `.codex/tmp/s21-activities-after-save.png`
  - `.codex/tmp/s21-dashboard-after-entry-created.png`
  - `.codex/tmp/s21-continue-today-reopen.png`
  - `.codex/tmp/s21-calendar-screen.png`
  - `.codex/tmp/s21-calendar-backdate-selected.png`
  - `.codex/tmp/s21-calendar-entry-open.png`

### Research Direction Locked By This Pass

- Resume/restoration needs a specific export/picker hardening slice:
  - route/UI state must stay aligned after leaving the app for DocumentsUI
  - returning from external picker workflows cannot strand the user in an
    orphaned project-scoped screen with lost project context
- 1126 header closure now needs data-source completion, not ownership theory:
  - ownership is better
  - remaining blank fields mean the preload inputs themselves are still
    incomplete or inconsistently mapped

## 2026-04-09 07:12 ET Follow-Up Audit Note: Resume And Forms Recovery Slice

Additional repo-backed findings after the latest implementation wave:

- `lib/core/router/app_router.dart`
  - restoration policy is now materially narrower: only root shell routes are
    restorable, while project-scoped editor/export/settings/sync utility flows
    are explicitly non-restorable
  - this is the correct seam for preventing external-picker resume from
    restoring back into transient nested routes
- `lib/features/quantities/presentation/screens/quantities_screen.dart`
  - the screen now reacts to late project restoration instead of assuming the
    selected project existed at first build
  - this closes the exact stale-state class that produced an orphaned
    `Pay Items / 0 items` screen after external picker resume
- `lib/features/forms/presentation/screens/form_gallery_screen.dart`
  - the add-form sheet now round-trips a selected `InspectorForm` explicitly
    and routes `MDOT 1126` through the shared creation dispatcher
  - the preload contract is now stronger both in product code and in the
    refreshed widget coverage
- `lib/features/forms/presentation/screens/mdot_1126_form_screen.dart`
  - header autofill coverage has been extended to include permit/location
    fallback resolution instead of only the already-known project/contractor/
    inspector fields
- `lib/features/entries/presentation/widgets/home_screen_body.dart`
  - compact calendar/day layout is now scroll-based, which is the right shared
    responsive direction rather than adding one-off pixel constraints around the
    previous overflow path

This slice is source-verified but not yet device-verified. The remaining truth
source for closure is live S21 validation of:
- picker resume correctness
- calendar overflow removal
- forms `+` creation routing
- 1126 permit/location header population

## 2026-04-09 07:20 ET Device Truth Update

What the S21 pass proved:

- the compact calendar layout change was the right fix; the prior overflow no
  longer reproduced and no overflow logs were emitted during the validation
- the forms add-sheet bug was split into two layers:
  - structural sheet bug: fixed
  - duplicate visible text targets in the gallery plus sheet: still a driver
    targeting nuance, not a product regression once the actual sheet row is
    tapped
- 1126 header autofill is now live with permit/location populated on device

What remains architecturally important:

- the external-picker resume problem is no longer a pure missing-project-state
  issue
- it is now a route/back-stack truth problem:
  - visible UI, internal route state, and Android task stack can still diverge
    after launcher relaunch from `DocumentsUI`
- `Mdot1126FormScreen` is now the outlier form surface for app-bar affordances:
  - it lacks the preview/export parity already present on `FormViewerScreen`
    and `MdotHubScreen`

## 2026-04-09 08:05 ET Follow-Up Audit Note: What The New Pass Proved

- `Mdot1126FormScreen` is no longer an affordance outlier
  - preview/export parity is now implemented and live on-device
- the launcher-resume fix was best solved at the Android activity/task layer,
  not with more Flutter-side restoration heuristics
  - `singleTask` removed the user-facing back-stack resurrection of
    `DocumentsUI`
- the remaining inconsistency after picker relaunch is currently in diagnostics
  - visible UI and user-facing back behavior are correct
  - `DriverWidgetInspector.currentRouteName()` still reported `/quantities`
    while pay-app detail was visible
  - this points to driver route inspection being too shallow for that relaunch
    case, and it should be tracked separately from product routing truth

## 2026-04-09 09:15 ET Audit Follow-Up: Remaining Closure Inventory

### Remaining Product Gaps After Full Reconciliation

- Cross-account trash isolation remains unclosed.
  - No later artifact proves that same-device account switching clears or
    re-scopes trash results correctly.
- Entry date editing remains a real feature gap.
  - Calendar backdating is proven, but there is still no direct in-flow
    report-date editing contract.
- 0582B original/recheck numbering remains open.
- 0582B export UX remains open around:
  - dated-folder support
  - attach-vs-export decision
  - multi-surface export-flow cleanup
- 1126 / SESC remains broader than header ownership.
  - header autofill and preview/export parity are closed
  - broader wizard/carry-forward friction still needs an explicit pass
- grouped conflict viewer usefulness remains weak even after conflict grouping
  and sync-surface simplification
- sync report taxonomy remains the next honest product improvement for the
  simplified production sync surface

### Source-Landed But Still Unverified Enough To Keep Open

- project delete immediate UI refresh and valid fallback selection
- Windows dashboard duplicate-pane removal on Windows
- generic form-viewer parity for incomplete 0582B export if the same rule must
  hold outside the hub flow
- repeated pay-app workbook accumulation across multiple exports
- broader app-wide foreground resume slowness outside the now-fixed
  picker-resume/back-stack path

### Lint Exploration From This Reconciliation

- Honest candidate lint areas:
  - owner restriction for restoration-sensitive external-intent/picker launch
    flows
  - owner restriction for stale screen-local read-only rendering when a live
    provider/controller source is available
  - owner restriction for destructive mutations so refresh/reload ownership
    cannot drift
  - expanded shared route-intent enforcement for continue/edit/open-submitted
    entry paths
  - preload gating enforcement at action-trigger sites
- Not honest enough for static lint alone:
  - Android task-stack correctness
  - route/back behavior after background/foreground
  - trash scope correctness
  - accumulation correctness in exported workbooks
- Conclusion:
  - the navigation/state bugs from this wave are partly lint-preventable, but
    the lockout/resume class must still be handled as a lint + contract-test +

### 2026-04-09 Project Removal Semantics Finding

- The latest project-delete verification found a distinct stale-state bug that
  was not just provider refresh drift.
- Local device removal intentionally preserves the `projects` metadata row so a
  project can remain known/available after eviction.
- The merged projects loader was still defining local/on-device membership from
  `projects` table presence alone, so removed projects stayed visible as local.
- Correct semantic definition:
  - known/available project = metadata row in `projects`
  - on-device/enrolled project = `projects INNER JOIN synced_projects`
- Fix landed in the repository/use-case layer by adding
  `getEnrolledByCompanyId()` and switching `FetchRemoteProjectsUseCase` to use
  the enrolled join.
- Risk class:
  - any UI that treats metadata presence as local enrollment can recreate this
    stale state bug
  - this is a strong candidate for future lint/contract-test coverage around
    source-of-truth ownership for merged list state
- Additional device finding from the same verification:
  - the original `ProjectDeleteSheet` was also violating the responsive
    bottom-sheet contract
  - a persistent sync error banner could push the confirm action below the fold
    while the sheet body remained non-scrollable
  - fix landed by moving the path to `AppBottomSheet.showScrollable()` and
    making the sheet body itself a `SingleChildScrollView`
- Final closure detail from the cold-start persistence pass:
  - there were two separate assignment-enrollment owners, and both had to be
    brought under the same manual-removal contract
  - application path:
    - `SyncEnrollmentService.handleAssignmentPull()`
  - engine path:
    - `EnrollmentHandler.reconcile()`
    - `EnrollmentHandler.enrollFromAssignments()`
  - a user-intent marker in `sync_metadata` now gates all auto-enrollment until
    the user explicitly downloads the project again
  - lesson:
    - when we standardize ownership rules, we need to audit every duplicate
      owner path, not just the first one that matches the bug
  - end-to-end device proof now covers the full intent cycle:
    - manual local removal
    - cold relaunch with project still suppressed
    - explicit user redownload restoring the project
    device-proof problem, not a lint-only problem

## 2026-04-09 09:45 ET Follow-Up: What Was Honest Enough To Enforce

- `form-new` route ownership was honest enough for static lint.
  - landed:
    - `no_form_new_route_calls_outside_approved_owners`
  - why it qualifies:
    - the stuck/empty form-create bug depended on route ownership drifting past
      the approved preload-aware creation surfaces
    - this is a concrete named-route ownership signal, not a vague UX smell
- project-delete refresh was not honest enough for lint.
  - what was done instead:
    - fixed provider-side fallback selection directly
    - added provider contract tests
  - why no lint:
    - the stale-delete bug was behavioral state repair, not a clean static AST
      smell
- submitted-entry continue behavior was also better handled as a contract test
  than lint.
  - landed:
    - widget tests for prompt visibility, revert-to-draft, and open-submitted
  - why no lint:
    - the bug is about runtime branching and navigation side effects, not a
      single forbidden API usage

## 2026-04-09 09:52 ET Equipment Manager Follow-Up

- The equipment-manager report is now closed for the actual contractor edit
  flow in the entry editor.
- The narrow fix was better than a broad dialog-host mutation:
  - first attempted approach:
    - make all `AppDialog.show()` dialogs `scrollable: true`
  - outcome:
    - not trusted as a repo-wide change; the equipment add path became unstable
      enough during device probing that it was not honest to keep the global
      behavior change
  - final approach:
    - localize the responsive fix to `EquipmentManagerDialog`
    - remove auto-focus when equipment already exists
    - add explicit helper copy for multi-item lists
    - constrain and scroll the dialog body under keyboard insets
- Device proof on the S21:
  - open state shows existing equipment immediately
  - helper copy makes discoverability explicit
  - focusing the text field no longer reproduces the overflow stripe
- Architectural lesson:
  - this bug class did not expose a clean static-lint signal
  - the honest protection here is:
    - localized responsive component ownership
    - widget tests around autofocus/scroll behavior
    - device proof for keyboard/IME layout states

## 2026-04-09 10:05 ET Trash Scope Follow-Up

- The cross-account trash report had a second state-ownership seam beyond the
  SQL filter itself.
- `TrashScreen` originally:
  - loaded deleted items once in `didChangeDependencies()`
  - used `context.read<AuthProvider>()`, which does not subscribe to auth
    scope changes
  - kept the old grouped trash state alive if the mounted screen survived an
    account switch
- Landed fix:
  - treat `userId + isAdmin` as the trash-scope identity
  - reset the controller and reload trash when that scope changes
  - subscribe to auth-scope changes by reading the provider with dependency
    tracking in `didChangeDependencies()`
- Coverage:
  - new widget test simulates a mounted-screen user switch and proves
    `User One Entry` is replaced by `User Two Entry`
- Honest conclusion:
  - this is another state-ownership/runtime bug class, not a good lint target
  - a lint cannot honestly prove account-scope reload correctness here
  - the right protection is:
    - explicit reload ownership
    - contract tests for account-switch behavior
    - real multi-account device proof before final closure

## 2026-04-09 09:26 ET Device Proof: Submitted Entry Prompt Path

- The submitted-entry flow no longer belongs in the unverified bucket.
- S21 proof sequence on the current driver build:
  - selected Springfield
  - opened the Apr 9 draft from `1 Draft — Tap to Review`
  - submitted the draft from review
  - dashboard switched to `Today's Entry Submitted`
  - tapping the card opened `Today's Entry Already Exists`
- Both decision branches were validated on-device:
  - `Open Submitted` opened the existing submitted report
  - `Revert to Draft` reopened the same entry in editable form state and showed
    `Entry reverted to draft`
  - after backing to dashboard, the state was honest again:
    - `1 Draft — Tap to Review`
    - `Continue Today's Entry`
- Conclusion:
  - the original bug class is closed:
    - dashboard no longer silently creates a new entry when today's entry is
      already submitted
  - this remains a contract-test/device-proof class, not a realistic lint-only
    candidate
## 2026-04-09 11:05 ET Forms/Export Validation Notes

- 0582B numbering root cause was still real:
  - hub/controller logic treated every sent test row as a new chronological
    test by incrementing blindly
  - the product note required original numbering to stay chronological while
    rechecks remain attached to the failed original until a passing result
- Resolution:
  - extracted `Mdot0582bTestNumberingService`
  - moved next-test resolution out of ad hoc controller math
  - kept the recheck chain open only when failure can be evaluated honestly
    from:
    - `percent_compaction`
    - selected item-of-work density requirement
  - unknown/incomplete rows do not hold the workflow hostage in recheck mode
- S21 proof captured:
  - failing original stayed on `Test #2`
  - the next draft became `Test #2 · Recheck #1`
  - a passing recheck reset to `Test #3`
- Forms/export revalidation truth:
  - 1126 saved response header/autofill is healthy on-device
  - 1126 preview/export are healthy on-device
  - 0582B export is healthy on-device even when the current draft is incomplete
- Pay-app workbook accumulation proof:
  - canonical workbook path exists in-app under:
    - `app_flutter/exports/pay-applications/project-workbooks/...`
  - direct workbook inspection showed three worksheets:
    - `Pay App #1`
    - `Pay App #2`
    - `Pay App #3`
  - this is now backed by a regression test at:
    - `test/features/pay_applications/domain/usecases/build_project_pay_app_workbook_use_case_test.dart`
- Remaining forms/export gaps after this research pass:
  - 0582B export UX still needs a real product pass:
    - dated-folder support
    - attach-vs-export decision
    - flow cleanup
  - 1126 / SESC still needs broader e2e proof beyond header + preview/export:
    - carry-forward
    - attach-step/create-entry
    - reminders
  - generic form-viewer export parity still needs an explicit close/decision

## 2026-04-09 11:30 ET Shared Form PDF Contract Notes

- Structural drift confirmed:
  - before this slice, three different form shells each owned their own
    preview/export/share flow:
    - `mdot_hub_screen.dart`
    - `mdot_1126_form_screen.dart`
    - `form_viewer_screen.dart`
  - the duplicated logic was not just cosmetic:
    - preview route ownership differed
    - snackbar/share sequencing differed
    - builtin-form lookup lived ad hoc in the 0582B hub
- Standardization landed:
  - `FormPdfActionOwner` now owns:
    - open preview shell from bytes
    - preview a filled response
    - preview form data
    - preview debug form
    - export/share generated file path
    - builtin-form lookup for preview use cases
- Enforcement landed:
  - `no_direct_form_pdf_actions_outside_owner`
  - narrowed intentionally to top-level form `*_screen.dart` files so it does
    not falsely fire on legitimate non-export internal PDF generation like the
    1126 pre-sign hash path in `mdot_1126_steps.dart`
- S21 proof after refactor:
  - 1126 preview/export remained healthy
  - 0582B preview/export remained healthy
  - Android chooser handoff confirms the shared export owner still reaches the
    real device boundary rather than only succeeding in local tests
- Remaining architectural form gap:
  - preview/export is now standardized, but attach-to-entry is still not a
    unified reusable contract for future forms
  - that is the next shared-form seam to formalize once the product policy is
    settled

## 2026-04-09 11:45 ET Export Artifact Audit Notes

- Export ownership is currently split into three major artifact families:
  - forms:
    - `FormPdfActionOwner`
  - entries:
    - `EntryPdfPreviewScreen`
    - `report_pdf_actions_dialog.dart`
    - `ExportEntryUseCase`
  - pay apps:
    - `QuantitiesPayAppExporter`
    - `PayAppDetailFileOps`
    - `ExportSaveShareDialog`
- Conclusion from audit:
  - forms already have a shared preview/export owner
  - entries and pay apps still behave as isolated export systems
  - the next honest standardization seam is not “one owner for everything”
    but:
    - one shared export capability registry
    - then specialized owners per artifact family that must declare their
      capability
- durable implementation plan captured in:
  - `.codex/plans/2026-04-09-export-artifact-contract-plan.md`

## 2026-04-09 12:00 ET Export Capability Registry Notes

- The first shared cross-artifact export seam now exists:
  - `ExportArtifactCapabilityRegistry`
- Registry currently declares the baseline contract for:
  - `form`
  - `entry`
  - `pay_app`
- Adoption is intentionally partial but meaningful:
  - forms:
    - `FormPdfActionOwner` asserts/declares against `form`
  - entries:
    - preview/report export surfaces now declare against `entry`
  - pay apps:
    - export/detail file owners now declare against `pay_app`
- This is enough to make the architecture explicit before deeper refactors:
  - exported-file follow-up ownership is still duplicated
  - attachment semantics are still not unified
  - but future work now has a single contract vocabulary instead of three
    unrelated export implementations

## 2026-04-09 12:15 ET Exported-File Action Owner Notes

- Shared follow-up owner now exists for already-exported local artifacts:
  - `ExportArtifactFileActionOwner`
- Direct file-action duplication removed from:
  - `PayAppDetailFileOps`
  - `SettingsSavedExportActions`
  - `QuantitiesPayAppExporter`
- This made the next honest lint possible:
  - `no_direct_export_artifact_file_service_usage_outside_owner`
- Remaining export-system duplication after this slice:
  - entry export still has two UI-level owners:
    - `EntryPdfPreviewScreen`
    - `report_pdf_actions_dialog.dart`
  - that is the next best cleanup seam if the goal is one export contract
    across entries/forms/pay apps

## 2026-04-09 13:10 ET Pay-App Sync/Export Research Notes

- Root product distinction now explicit:
  - canonical business records sync
  - export history stays local
- Applied to pay apps:
  - `pay_applications` remains canonical sync data
  - workbook/export history remains local through `export_artifacts`
- Sync-engine classification now reflects that split:
  - local-only export-history tables:
    - `entry_exports`
    - `form_exports`
    - `export_artifacts`
  - canonical sync table:
    - `pay_applications`
- Adapter behavior for pay apps:
  - `export_artifact_id` is local-only linkage metadata
  - remote null cannot wipe local linkage
  - local linkage does not push back to Supabase
- Migration/repair strategy:
  - `v57` retires legacy export-history sync residue
  - `v58` rebuilds `pay_applications` with nullable `export_artifact_id`
  - runtime repair purges queued residue for local-only export-history tables
- Device proof already captured:
  - no local-only export-history triggers remain on the S21
  - `pay_applications` still participates in the sync engine
  - upgraded queue starts clean
- Remaining research/validation gap:
  - must prove with a live create/export/sync cycle that canonical pay-app
    records still sync while local workbook/export history never enters the
    queue

## 2026-04-09 13:35 ET Pay-App E2E Research Closure

- Live S21 proof now exists for the client-side split:
  - exported a real new pay app through the UI
  - observed exactly one queued `change_log` row:
    - `pay_applications/<new-id>`
  - observed zero queued rows for:
    - `export_artifacts`
    - `form_exports`
    - `entry_exports`
  - confirmed local artifact metadata still exists and points at a real local
    workbook file
- The true remaining failure is backend deployment drift:
  - linked remote schema still has `pay_applications.export_artifact_id`
    `NOT NULL`
  - therefore canonical pay-app sync currently fails with `23502`
- New protection added because this class of failure is a deployment mismatch,
  not a user-data error:
  - pay-app schema mismatch is now detected explicitly
  - row is blocked immediately instead of consuming repeated retries
  - startup repair quarantines existing matching rows into blocked state
- Practical outcome:
  - pay-app exports no longer silently poison normal sync runs on-device
  - they remain safely local and clearly blocked until the backend migration is
    deployed

## 2026-04-09 14:05 ET Pay-App Research Closure

- Backend deployment drift is no longer hypothetical:
  - the linked Supabase project was updated
  - `public.pay_applications.export_artifact_id` is nullable
  - export-artifact FK now deletes with `SET NULL`
- Recovery architecture is now complete enough for this stale-state class:
  - startup repair still quarantines raw schema-mismatch failures
  - explicit operator repair now requeues already-blocked pay-app rows after
    backend deployment
- Live proof:
  - S21 blocked row moved from `blocked` to `pending` through the repair path
  - follow-up sync drained cleanly
  - remote `pay_applications/<id>` exists with `export_artifact_id = null`
- Research conclusion:
  - canonical syncable pay-app data + local-only workbook/export history is the
    correct split
  - this class of stale state now has:
    - quarantine on mismatch
    - explicit requeue after backend fix
    - verified drain path

## 2026-04-09 14:25 ET Entry Export Research Closure

- The generic attachment refactor now has live bundle-side proof:
  - the saved `mdot_1126` response remains linked to the Apr 9 draft entry
  - the entry export preview now exposes stable save/share keys
  - the save flow chooses folder export (`Export Folder Name`, `04-09`) on the
    S21 for that attached draft
- Practical interpretation:
  - the entry export system still sees attached forms after the shared
    `FormEntryAttachmentOwner` refactor
  - bundle-root behavior on daily entries remains intact
- Remaining research gap is narrower now:
  - direct live proof for the wizard-side attach-step/create-entry flow itself
## 2026-04-09 15:35 ET 1126 Attach/Reminder Research Notes

- The attach-step false positive from earlier testing was methodological, not architectural:
  - raw adb coordinate taps can hit the wrong layer during rapid step transitions
  - the driver’s widget-text tap endpoint gives reliable proof for button-owned flows
- The real 1126 attach/product state after fixes is:
  - same-date match:
    - explicit recommended row
    - explicit `Choose a different existing entry` override
  - no same-date match:
    - explicit create-entry CTA
    - explicit override CTA
    - no ambiguous inline entry list at the default decision point
- Reminder drift root cause was confirmed in source:
  - `weekly_sesc_toolbox_todo.dart`
  - `entry_editor_body.dart`
  - dashboard reminder slot in `project_dashboard_screen.dart`
  - all routed to `form-new` without an inspection date
  - `form_new_dispatcher_screen.dart` only had `projectId`, so it defaulted new 1126 drafts to `DateTime.now()`
- Reminder fix shape now in source:
  - `inspectionDate` is a query parameter on `form-new`
  - dispatcher forwards it into `InspectorFormProvider.createMdot1126Response`
  - this keeps weekly reminder cadence honest without adding a second creation route

## 2026-04-09 15:58 ET Shared Form Export Contract Notes

- The last export mismatch was between:
  - dedicated form shells (`MdotHubScreen`, `Mdot1126FormScreen`)
  - the generic fallback viewer (`FormViewerScreen`)
- Before this slice:
  - fallback viewer required preview before export
  - fallback viewer implicitly submitted open forms
  - fallback viewer marked forms exported after the PDF write
  - `FormPdfActionOwner` only shared a temp file and could not offer
    `Save Copy`
- The honest contract is now:
  - forms remain editable after export
  - export records local artifact/history rows
  - post-export actions are shared and explicit
  - shipped form surfaces behave the same whether they use a dedicated shell or
    the fallback viewer
- Device proof completed:
  - generic viewer export dialog opened for saved 0582B response
    `fa74c344-0977-4b3a-9263-727796b6af41`
  - live 0582B shell export dialog opened for the same response when routed
    through `formType=mdot_0582b`
  - live 1126 shell export dialog opened for
    `c1b792f9-1248-420f-a218-a029fce446de`
  - post-export DB inspection confirmed both rows remained `status = open`

## 2026-04-09 16:03 ET Signature Identity And Save-Copy Notes

- 1126 signature identity drift root cause is now narrowed and fixed:
  - editable header text is no longer the primary signer identity source
  - carried-forward inspector names no longer silently override the next
    inspector's signer identity
  - accepted typed signer text is now stored in response data
- Practical effect:
  - UI validation, saved response payload, and audit row now share a more
    coherent signer story
  - the remaining gap is broader multi-inspector device validation, not a known
    single-user source seam
- Additional device proof:
  - `Save Copy` from the shared `Form Exported` dialog now reaches Android's
    picker on the S21
  - artifact:
    - `.codex/tmp/0582b-save-copy-picker-verified.png`

## 2026-04-09 16:40 ET Entry Route-Identity Findings

- The remaining entry-date-edit gap was not missing feature code.
- Source already had:
  - date edit button
  - date picker dialog
  - collision dialog
  - route-intent navigation to the target entry/date
- The real bug was route/state drift:
  - `EntryEditorScreen` did not reload when `projectId`, `entryId`, or `date`
    changed on the same mounted widget state
  - that let the route point at one entry while the visible header still
    rendered another
- Resolution:
  - explicit route-identity helper
  - `didUpdateWidget(...)` reload ownership
  - new pending-id regeneration for create-mode route hops
- This is another example of the same broader state-ownership rule:
  - route changes are mutations of screen identity and must rebind canonical
    state, not just navigation location

## 2026-04-09 16:55 ET 1126 Dedupe + Forms Context Notes

- Weekly 1126 duplicate-draft drift was still real in source:
  - creation flow had carry-forward logic but no same-date open-draft reuse
  - repeated same-date creation could therefore keep creating parallel drafts
- The smallest honest fix was not a UI patch:
  - add a same-date open-draft resolver use case
  - call it before carry-forward/create
- Reminder logic also needed to acknowledge work-in-progress:
  - current-cycle open drafts should expose resume context instead of behaving
    like no weekly work exists yet
- Export-context drift findings closed in the same pass:
  - date-aware filenames belong in one shared policy, not screen literals
  - Forms screen should not mix pay apps/photos/entry exports into form export
    history
  - saved response rows need linked-vs-standalone context because attachment
    state is part of the product meaning, not just metadata

## 2026-04-09 16:58 ET Additional Forms/Export Inventory Closure

- Attach-vs-export is no longer just a planned policy item.
  - it is now source/test/device-proven for the live 0582B shell
- The 0582B hub export drift was real and is now closed.
  - prior state:
    - preview could reflect unsaved draft state
    - export used only the persisted response row
  - landed fix:
    - `MdotHubScreen` now saves the current draft before export
  - live proof:
    - device DB now stores edited `counts_mc = 777` after export without a
      manual save tap
- 1126 attach proof is now complete.
  - create-entry branch verified on-device
  - existing-entry branch verified on-device
- standalone signed-form validation is now aligned.
  - a signed 1126 edited via the keyed date picker now blocks export on-device
  - current block copy is functionally correct but still somewhat raw:
    - `measures, signature`

What remains honestly open in research after this closure:
- standalone-form dated-folder product behavior
- reminder-surface `resume draft` screenshot proof
- conflict viewer usefulness

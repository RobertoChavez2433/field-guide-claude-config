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

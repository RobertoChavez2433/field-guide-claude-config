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

### Still Open From The Notion Export

- `driver_server.dart` remains a large pre-merge blocker.
- `database_service.dart` remains oversized and still belongs on the beta queue.
- `form_pdf_service.dart` and `extraction_pipeline.dart` remain oversized.
- `codex-admin-sql` edge function still needs explicit audit/documentation.
- `debug_emit_sync_hint_self` still needs to be gated or removed before production.
- migration rollback coverage remains incomplete.
- sync-hint migration squash remains open.
- i18n and responsive-layout adoption are still real gaps.

### Closed Since The Notion Snapshot

- shipped forms export fidelity is now proven in code for IDR, MDOT 0582B, and MDOT 1126
- pay-app export regression slices were rerun after shared export changes
- production route caller standardization on named routes is in place
- driver shell/forms routing parity with production has been repaired
- auth redirect routing proof is green through the new seam
- sync-hint RPC ownership now lives in the approved owner components and the sync-hint lint rules are green
- the custom lint backlog is currently clean; remaining work is architectural decomposition and dead-code burn-down

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
- the current backlog should prioritize decomposition around `DatabaseService`, `AuthProvider`, and the heavyweight driver/forms/pdf surfaces because they remain both large and structurally central

## God-Sized File Inventory

Current top Dart files by LOC snapshot:
- `2606 lib/core/database/database_service.dart`
- `1895 lib/core/driver/driver_server.dart`
- `1445 lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`
- `1258 lib/features/forms/data/services/form_pdf_service.dart`
- `1173 lib/shared/testing_keys/testing_keys.dart`
- `994 lib/core/logging/logger.dart`
- `835 lib/features/pdf/services/extraction/shared/post_process_utils.dart`
- `823 lib/services/soft_delete_service.dart`
- `726 lib/features/pdf/services/pdf_service.dart`

Large provider/controller/service/helper/screen surfaces at or above ~250 LOC:
- `lib/core/database/database_service.dart` — 2606
- `lib/features/forms/data/services/form_pdf_service.dart` — 1258
- `lib/services/soft_delete_service.dart` — 823
- `lib/features/pdf/services/pdf_service.dart` — 726
- `lib/features/projects/data/services/project_lifecycle_service.dart` — 441
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

1. Finish the 5 remaining lint issues so the architecture baseline is fully green again.
2. Audit and resolve `debug_emit_sync_hint_self` and `codex-admin-sql`.
3. Decide the migration-squash and rollback backfill strategy and move it into execution, not just tracking.
4. Start decomposing the highest-risk oversized files in this order:
   - `driver_server.dart`
   - `database_service.dart`
   - `form_pdf_service.dart`
   - `extraction_pipeline.dart`
5. Keep platform/product gaps visible, but do not let them obscure the current release-critical hard blockers.

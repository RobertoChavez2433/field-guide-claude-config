Date: 2026-04-08
Branch: `sync-engine-refactor`
Status key: `[ ]` pending, `[-]` in progress, `[x]` done, `[!]` blocked, `[>]` reference

# Beta Central Tracker

This is the canonical append-only beta tracker.

Use this file as the single running source of truth for:
- phases
- sub-phases
- sprint slices
- concrete steps
- blocker status
- verification status
- references to supporting artifacts

Older beta docs remain as supporting artifacts only:
- [2026-04-07-beta-release-unified-todo.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/completed/2026-04-07-beta-release-unified-todo.md)
- [2026-04-08-beta-release-session-handoff.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/completed/2026-04-08-beta-release-session-handoff.md)
- [2026-04-08-beta-research-inventory.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-08-beta-research-inventory.md)
- [2026-04-08-codemunch-beta-audit-reference.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-08-codemunch-beta-audit-reference.md)

Primary external audit source for this tracker:
- Notion export snapshot: `C:\Users\rseba\AppData\Local\Temp\notion_beta_export_632c1bec\inner\Field_Guide_App_Notion_Import_2026-04-07 33cc3411c1b58029a802cc3289f9cbab.md`

## Finish Criteria

Beta is not done until all of these are true:
- `flutter analyze` is clean.
- `dart run custom_lint` is clean.
- local Supabase bootstrap/reset is reproducible from repo state, or it is explicitly moved out of beta with a documented reason.
- shipped forms export is proven correct against live template mappings.
- pay-app export flow is proven from UI trigger through artifact persistence and detail flows.
- routing is standardized and production route contracts are covered.
- provider/controller architecture drift is burned down behind explicit endpoints.
- the current pre-merge security and migration blockers from the Notion audit are either closed or formally descoped.
- remaining oversized core files are either decomposed or explicitly moved out of beta scope.

## Current Source Of Truth

[>] Notion blocker snapshot
- `driver_server.dart` remained a pre-production god-object blocker in the audit snapshot; the live branch has now reduced it to a thin lifecycle/dispatch shell and closed the blocker.
- `codex-admin-sql` edge function remains an undocumented security review blocker.
- `debug_emit_sync_hint_self` remains a pre-prod gate/remove item.
- sync-hint migration squash, rollback coverage, and sync-push fan-out hardening were open in the audit snapshot but are now closed in repo state.
- i18n/responsive/a11y remain real gaps, but they are below the current export/routing/security hard blockers.

[>] Code-backed status snapshot
- forms export proof is closed for shipped beta forms: IDR, MDOT 0582B, MDOT 1126.
- routing audit found no missing production named routes.
- driver/harness shell/forms routing drift has been fixed.
- auth/gallery/photos/projects provider drift wave is largely integrated and targeted tests are green.
- sync-hint RPC ownership and post-RPC refresh lint issues are closed.
- repo no longer carries the `debug_emit_sync_hint_self` app/edge-function probes.
- repo no longer carries the undocumented `codex-admin-sql` arbitrary-SQL edge function source.
- sync-hint migration churn is now collapsed into `20260408160000_sync_hint_final_state.sql` with a paired rollback file.
- `driver_server.dart` decomposition has started with widget-tree inspection extracted into `driver_widget_inspector.dart`.
- `driver_server.dart` decomposition now also routes sync/data endpoints through `driver_data_sync_handler.dart` and file/document/photo injection through `driver_file_injection_handler.dart`.
- `driver_server.dart` interaction/navigation handlers now live in `lib/core/driver/driver_interaction_handler.dart`, leaving `DriverServer` focused on HTTP dispatch plus the remaining ready/find/tree/screenshot/admin seams.
- `driver_server.dart` now also delegates ready/find/tree/screenshot/hot-restart endpoints to `lib/core/driver/driver_shell_handler.dart`, leaving the server focused on lifecycle and dispatch.
- logging standardization has started: payload redaction/JSON-safety now lives in `lib/core/logging/log_payload_sanitizer.dart` while `Logger` keeps the same public API.
- logger transport/lifecycle extraction is now in place: file-sink lifecycle lives in `lib/core/logging/logger_file_transport.dart` and HTTP delivery lives in `lib/core/logging/logger_http_transport.dart` while `Logger` stays the public facade.
- `Logger.error()` no longer owns the Sentry/error-reporting pipeline inline; that now lives in `lib/core/logging/logger_error_reporter.dart`.
- `database_service.dart` no longer owns fresh-install bootstrap inline; canonical schema creation, index creation, schema verification, and entry-scoped `project_id` repair now live in `lib/core/database/database_bootstrap.dart`.
- `database_service.dart` no longer owns the low-version upgrade chain inline; migrations `v2-v24` now live in `lib/core/database/database_upgrade_foundation.dart`.
- `database_service.dart` no longer owns the review-submit / daily-entry workflow migration block inline; migrations `v25-v27` now live in `lib/core/database/database_upgrade_entry_workflows.dart`.
- `database_service.dart` no longer owns the sync-engine rebuild / contract expansion migration block inline; migrations `v28-v37` now live in `lib/core/database/database_upgrade_sync_engine.dart`.
- `form_pdf_service.dart` no longer owns field-name variation matching, row-to-PDF field mapping, checkbox parsing, or summary fallback formatting inline; those now live in `lib/features/forms/data/services/form_pdf_field_writer.dart`.
- `form_pdf_service.dart` now also delegates preview-cache ownership to `lib/features/forms/data/services/form_pdf_preview_cache.dart` and template-byte loading/caching to `lib/features/forms/data/services/form_pdf_template_loader.dart`.
- direct PDF preview/share/temp-save ownership now lives in `lib/features/pdf/services/pdf_output_service.dart`, with both `form_pdf_service.dart` and `pdf_service.dart` delegating to the shared owner.
- direct `Printing.layoutPdf` / `Printing.sharePdf` drift is now blocked by `no_direct_printing_output_usage`, which closes the exact architectural seam surfaced during the output extraction.
- `pdf_service.dart` no longer owns multi-file export bundle writing inline; entry export payload models now live in `lib/features/pdf/services/pdf_export_models.dart` and file generation/writes now live in `lib/features/pdf/services/pdf_export_bundle_writer.dart`.
- `pdf_service.dart` no longer owns the shipped IDR template asset/rendering block inline; template loading, field maps, contractor/equipment section filling, formatting, and debug-template generation now live in `lib/features/pdf/services/idr_pdf_template_writer.dart`.
- direct `rootBundle.load('assets/templates/idr_template.pdf')` drift is now blocked by `no_direct_idr_template_usage`, which locks IDR template ownership to the extracted writer.
- existing custom lints continue paying for themselves during refactor work: `sync_table_contract_must_come_from_registry` immediately caught a hardcoded table-contract list during the bootstrap extraction and forced the code back onto `SyncEngineTables`.
- `database_service.dart` no longer owns the cleanup/stabilization migration block inline; migrations `v38-v42` now live in `lib/core/database/database_upgrade_stabilization.dart`.
- `database_service.dart` no longer owns the late upgrade tail inline; migrations `v43-v56` now live in `lib/core/database/database_upgrade_repairs.dart`.
- the post-extraction audit closed one real migration hazard: `v42` change-log cleanup now scopes itself to version-correct registry tables and has dedicated regression coverage in `test/core/database/migration_v42_test.dart`.
- `extraction_pipeline.dart` no longer owns the tabular extraction tail inline; row classification through parsed-item conversion now live in `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_tabular_runner.dart`.
- `extraction_pipeline.dart` no longer owns structure-detection staging inline; provisional classification, region detection, and column detection now live in `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_structure_runner.dart`.
- `extraction_pipeline.dart` no longer owns stage-trace/run-state/attempt scaffolding inline; that runtime support now lives in `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_stage_runtime.dart`.
- `extraction_pipeline.dart` no longer owns the retry loop and per-attempt execution shell inline; that orchestration now lives in `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_attempt_runner.dart`.
- `extraction_pipeline.dart` no longer owns post-processing/quality-validation attempt lifecycle inline; that logic now lives in `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_attempt_lifecycle.dart`.
- `soft_delete_service.dart` no longer owns storage cleanup queue bookkeeping, restore cascade flow, or purge/hard-delete sync propagation inline; those now live in `lib/services/soft_delete_storage_support.dart`, `lib/services/soft_delete_restore_support.dart`, and `lib/services/soft_delete_purge_support.dart`.
- `realtime_hint_handler.dart` no longer owns realtime transport lifecycle inline; registration/deactivation RPCs, channel subscription/refresh, fallback polling, and transport-health publication now live in `lib/features/sync/application/realtime_hint_transport_controller.dart`.
- sync-hint transport ownership is now explicitly lint-locked to the approved realtime owners (`RealtimeHintHandler` plus `RealtimeHintTransportController`) instead of the older single-file assumption.
- `project_lifecycle_service.dart` no longer owns destructive local project eviction inline; that transaction now lives in `lib/features/sync/engine/project_local_eviction_executor.dart`.
- the project-lifecycle extraction also tightened lint ownership: `change_log` mutation no longer whitelists `project_lifecycle_service.dart`, and the new executor is now the approved owner for the local hard-delete path alongside the existing sync/data-safety allowlists.
- this form-PDF slice did not justify a new custom lint yet; the concrete issue uncovered was stale mirrored test logic, so the tests now target the extracted production helper directly instead of a second implementation.
- the database migration-tail slice likewise did not justify a brand-new lint rule, but it did force the late-upgrade trigger loops back onto `SyncEngineTables` registry constants instead of hardcoded synced-table lists.
- Docker Desktop runtime is now confirmed healthy through `docker version`, `docker info`, and `docker run --rm hello-world`.
- local Supabase startup/reset is now working from repo state after restoring the missing bootstrap path and fixing several migration ordering assumptions.
- `supabase start`, `supabase status`, `supabase migration list --local`, and `supabase db reset` now succeed in the current shell.
- current repo now carries an explicit early bootstrap migration plus follow-up ordering guards where older migrations assumed preexisting auth users, tables, or sync-hint functions.
- contractor bulk import is now live end-to-end with parser, preview/apply service, repository batch validation, provider support, import preview dialog, and project-contractors UI wiring.
- app lock is now live through settings with persisted PIN/biometric config, runtime lock gating in `AppWidget`, lifecycle auto-locking, and sync-startup suppression while the runtime lock is active.
- weather now has a durable offline cache path backed by `PreferencesService`, including fresh-cache hits, stale-cache fallback on network failure, and persisted refresh behavior.
- `daily_sync` hardening now exists on both sides of the push path: the client persists a cooldown and coalesces queued background broadcasts, and the Supabase edge function now claims a server-side dispatch slot before fan-out.
- rollback enforcement is now active in CI through both changed-migration companion checks and forward-enforced rollback coverage validation for the new migration era.
- `dart analyze` is clean.
- `flutter analyze` is clean again on the latest pipeline and soft-delete passes alongside clean `dart analyze`, clean `dart run custom_lint`, and the focused extraction suites.
- `dart run custom_lint` is clean.
- current repo-backed size and importance inventory is captured in the research artifact.

## Active Triage: Sync UX, Conflict Inflation, And Resume Stability

## 2026-04-09 13:25 ET Export-Artifact Contract Hardening

[-] Continue standardizing export flows across forms, entries, and pay apps

What closed in this slice:
- entry export no longer has duplicate product-facing preview/action surfaces
- `EntryPdfActionOwner` now owns generated entry save/share/export-record
  behavior
- `EntryPdfPreviewScreen` now delegates save/share to the shared owner
- dead `report_pdf_actions_dialog.dart` and
  `report_debug_pdf_actions_dialog.dart` were removed from the repo
- export capability registry now points entry export/follow-up ownership to
  `EntryPdfActionOwner`
- new architecture lint: `no_direct_entry_pdf_actions_outside_owner`

Verification:
- [x] targeted `flutter test` for export capability registry and entry owner
- [x] targeted lint-package `dart test`
- [x] targeted `flutter analyze`
- [x] root `dart run custom_lint`
- [ ] fresh S21 validation of the migrated entry export path

Current next export backlog after this slice:
- [ ] generic attach-to-entry contract for non-pay-app forms
- [ ] move remaining user-facing export copy/messages onto the shared
      capability contract where it reduces drift
- [ ] S21 validation for entry preview/save/share after the owner migration

## 2026-04-09 12:08 ET Generic Form Attachment Contract

[x] Standardize attach-to-entry for non-pay-app forms

What closed in this slice:
- generic form attachment use cases replaced the 1126-specific naming drift
- `FormEntryAttachmentOwner` now owns shared entry-link selection and attach
  mutation
- `AttachStep` and `FormsListScreen` both route through the shared owner
- new architecture lint:
  `no_form_response_entry_attachment_mutation_outside_owner`

Verification:
- [x] forms-domain + forms-support + touched-screen test batch green
- [x] lint-package test green
- [x] targeted `flutter analyze` green
- [x] root `dart run custom_lint` green

Honest follow-up:
- [ ] prove attached forms still export correctly inside the daily-entry bundle
- [ ] S21 validate the generic form attach flow
- [ ] later provider cleanup: move form-response mutation off extension methods
      and onto explicit mockable provider members

### 2026-04-08 18:05 ET

[-] Stabilize the user-facing sync experience before further beta rollout
User notes captured from live S21 testing:
- project delete does not auto-refresh the project list; audit the rest of the app for the same stale-refresh pattern
- sync reported completion while the dashboard still showed pending work and conflict counts
- the sync dashboard does not make conflicts or pending work transparent enough for an end user
- there is no intuitive way to clear or resolve visible conflict rows from the current dashboard flow
- the integrity-check section is misleading and should not be exposed in the user-facing sync dashboard
- repeated manual syncs increased visible conflicts from `12 -> 15 -> 20 -> 24`
- resuming the app from background can leave the UI briefly frozen before it comes back to life

Verified findings from logs plus live device database inspection:
- the dashboard/conflict viewer is counting raw `conflict_log` rows instead of distinct active logical conflicts; the inspected device database showed `24` unresolved rows but only `4` distinct `(table_name, record_id)` pairs
- builtin `inspector_forms/mdot_1126` is stuck in a phantom conflict loop because builtin forms are seeded locally with a fresh `updated_at`, but builtin rows are also skipped on push; repeated pulls can therefore log the same local-wins conflict indefinitely
- project deletion is locally soft-deleting pull-only `project_assignments` mirror rows, which can create unsyncable local-wins conflicts that are re-logged on every pull
- the project delete UI is stale because `ProjectProvider.deleteProject()` mutates `_projects` without rebuilding the merged view or refetching synced state
- the sync dashboard is stale by design because it only reloads on init/manual refresh and does not react to sync completion, follow-up syncs, or background-triggered sync activity
- the earlier `2 pending` state was not a persistent backlog at inspection time; the live device database showed `0` unprocessed `change_log` rows, which points to stale dashboard state rather than a still-blocked queue
- overlapping quick/full sync attempts and mutex skips add noise, but they were not the primary source of the phantom conflict growth

Implementation slices for the next pass:
- [ ] rebuild/refetch project and sync-dashboard state after destructive mutations and sync completion
- [ ] remove the integrity-check section from the user-facing sync dashboard
- [ ] make pending changes and conflicts transparent enough for end users to understand what is actually blocked
- [ ] count and display distinct active conflicts instead of raw history rows
- [ ] stop creating phantom conflicts for builtin forms and pull-only `project_assignments`
- [ ] investigate and fix the resume-from-background freeze/recovery behavior

### 2026-04-08 18:30 ET

[-] Latest live UX findings from on-device testing
New user-reported findings to verify and fix:
- when editing entry activities, tapping done does not show the text that was typed
- the create-equipment popup technically scrolls, but only one equipment row is visible at a time and there is no clear affordance that the list is scrollable
- when opening an existing entry from dashboard "Continue Today's Entry", the screen still says "New Entry"
- if today's entry was already submitted, dashboard "Continue Today's Entry" starts a brand-new entry instead of explaining that a submitted entry already exists and offering an unsubmit path
- users need an intuitive way to create/edit a report for a different date; likely by allowing the entry date to be edited inside the new-entry flow
- backdating from the calendar screen already works and should be preserved
- the calendar screen is throwing an overflow error, which indicates a responsive/scaffold tokenization gap
- the toolbox Forms screen shows no forms, and tapping the add button opens a bottom sheet/scroll box that becomes stuck and unusable

Expected verification work before/while fixing:
- [ ] verify the activities edit/display bug and trace whether it is a controller save issue, section-state refresh issue, or read-only display binding issue
- [ ] verify the equipment popup layout/constraints and make scrolling/discovery obvious instead of hidden
- [ ] verify all entry-title / continue-entry routing paths so edit vs new wording is honest across dashboard and entry editor
- [ ] verify the submitted-entry continue flow and add an explicit unsubmit-or-open-existing decision instead of silently creating a duplicate/new entry
- [ ] verify where entry date can be safely edited without breaking the existing calendar backdate flow
- [ ] verify the calendar overflow source and fix it through the shared responsive scaffolding rather than a one-off pixel tweak
- [ ] verify why toolbox forms are missing and why the add-form sheet becomes non-interactive

### 2026-04-08 18:50 ET

[-] Current-build verification after reinstalling the fresh driver build
Important context:
- earlier beta feedback was partially gathered against a stale APK on the S21; this verification block only includes issues reproduced against the fresh current-source build launched with `lib/main_driver.dart` plus `.env`
- inspector-role constraint confirmed during repro: this account cannot create projects, so project-creation flows are not part of the current verification surface

Verified on-device against the fresh build:
- `Continue Today's Entry` still routes into the entry editor with the header `New Entry`
- editing Activities, entering text, and tapping `Done` persists to SQLite but the card immediately falls back to `Tap to add activities`
- the Forms gallery opens from Toolbox, but shows no available form tabs beyond `All`
- tapping the Forms `+` button opens a nearly empty bottom sheet stub with no visible choices
- current sync errors are not only stale UI anymore: fresh logs show pending equipment delete pushes failing with `22P02 invalid input syntax for type uuid` for contractor-scoped IDs like `contractor:<uuid>`

Verified root causes:
- `DashboardTodaysEntry` always navigates to the create-by-date route instead of resolving and opening today's existing entry; it only changes the card label/icon based on `hasTodaysEntry`
  - file: [dashboard_todays_entry.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/dashboard/presentation/widgets/dashboard_todays_entry.dart)
- `ProjectDashboardScreen` only loads project-scoped dashboard providers once in `initState`; if the selected project is restored after the first frame or switched later, the header can update to the new project while entries/pay-items/totals still reflect empty or stale provider state
  - file: [project_dashboard_screen.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/dashboard/presentation/screens/project_dashboard_screen.dart)
- the entry-editor app bar title uses `isDraftEntry` as a proxy for "new", so any draft edit session is mislabeled as `New Entry`
  - file: [entry_editor_app_bar.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/entries/presentation/widgets/entry_editor_app_bar.dart)
- the Activities section saves through `DailyEntryProvider.updateEntry`, but `_saveAndStopEditing()` never updates the screen-local `entry` object afterward; view mode renders `DailyEntry.activitiesDisplayText(entry?.activities)` from stale state
  - files: [entry_activities_section.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/entries/presentation/widgets/entry_activities_section.dart), [entry_editor_state_mixin.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/entries/presentation/screens/entry_editor_state_mixin.dart)
- create-mode entry loading only reuses an existing draft for the same day; if today's entry is already submitted, the create route allocates a brand-new draft instead of surfacing the submitted entry and offering an unsubmit/open decision
  - file: [entry_editor_load_helpers.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/entries/presentation/screens/entry_editor_load_helpers.dart)
- the Forms gallery and add-form sheet both depend on `InspectorFormProvider.forms`, but `FormGalleryScreen` never loads builtin forms before rendering; when that list is empty, tabs are empty and the add-form sheet renders an empty `ListView`
  - files: [form_gallery_screen.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/forms/presentation/screens/form_gallery_screen.dart), [inspector_form_provider.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/forms/presentation/providers/inspector_form_provider.dart)
- the equipment manager dialog is a real layout/constraints problem: the list area lives in `Flexible + SingleChildScrollView` inside a `Column(mainAxisSize: min)` hosted by `AlertDialog`, which allows the equipment list viewport to collapse so far that only about one row is visible with no strong affordance that more content exists
  - files: [equipment_manager_dialog.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/entries/presentation/widgets/equipment_manager_dialog.dart), [app_dialog.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/core/design_system/surfaces/app_dialog.dart)
- the calendar-format toggle is a likely responsive overflow source on smaller widths because it hardcodes a centered `Row` of three padded buttons instead of adapting/wrapping; this has not yet been re-triggered live in the fresh session, but the structure matches the reported overflow failure mode
  - file: [home_calendar_section.dart](/C:/Users/rseba/Projects/Field_Guide_App/lib/features/entries/presentation/widgets/home_calendar_section.dart)
- current delete/refresh drift is broader than just projects: several destructive/update flows still mutate provider collections, but downstream screens often keep rendering screen-local model snapshots instead of refreshed provider-backed state; the Activities bug is a verified concrete instance of this underlying pattern

Implementation slices added from the fresh-build verification:
- [ ] replace stale screen-local entry rendering after saves with refreshed/live model state
- [ ] make dashboard "Continue Today's Entry" resolve today's actual entry and differentiate draft vs submitted behavior honestly
- [ ] add an explicit submitted-entry decision flow instead of silently creating a new draft for the same day
- [ ] load builtin forms before rendering the form gallery and prevent empty add-form sheets
- [ ] redesign the equipment manager dialog list area so multiple rows are visible and scrolling is obvious
- [ ] convert the calendar format toggle to a responsive layout that cannot overflow on narrow screens
- [ ] trace and fix the failing equipment tombstone push payloads causing the fresh `2 pending` sync state

### 2026-04-08 19:02 ET

[-] Standardize UI wiring contracts so these regressions stop recurring
User direction to carry forward into implementation and linting:
- one state-ownership rule per screen: detail screens must render the live provider/model source after mutation, not stale screen-local copies
- one mutation contract: every create/update/delete must either update canonical provider state or immediately trigger a required reload path
- one route-intent layer: actions like continue today, new entry, view submitted, and edit draft must go through shared intent helpers instead of ad hoc per-screen navigation
- one preload contract for screens and sheets: interactive affordances must stay disabled or loading until required data such as builtin forms or contractor data has been loaded
- one responsive content contract for dialogs and sheets: scrolling regions need explicit size constraints and visible affordances instead of unconstrained `Flexible` layouts inside transient surfaces
- contract tests should assert behavior, not just render snapshots: save updates visible state, delete removes items without manual refresh, continue today reopens the real entry, and enabled sheets never open empty
- investigate whether these contracts can be enforced codebase-wide with additional custom lints rather than only one-off tests

Follow-up slices:
- [ ] turn the above rules into explicit architecture guidance tied to the affected screens and providers
- [ ] audit which rules are test-only versus realistically enforceable with `custom_lint`
- [ ] add the missing contract tests for state ownership, mutation refresh, route intent, preload gating, and responsive transient surfaces

## Phase 1: Release-Critical Proof And Routing

### 1.1 Forms Export Fidelity

[x] Prove shipped forms export against live template fields
- IDR
- MDOT 0582B
- MDOT 1126

[x] Re-verify pay-app regression slices after shared export changes

### 1.2 Routing Standardization

[x] Standardize production `go_router` callers on named routes
[x] Add lint coverage for raw path navigation drift
[x] Repair auth redirect proof with a testable force-reauth seam
[x] Align driver/harness shell routing with production `ShellRoute`
[x] Align driver/harness forms routing with `FormGalleryScreen` and `/form/:responseId`
[x] Add real driver route contract coverage

### 1.3 Routing Gaps Audit

[x] Audit production route definitions for missing named routes
Outcome:
- no glaring missing production routes were found in the live router
- the main gap was driver/harness drift, not production route absence

## Phase 2: Architecture Standardization

### 2.1 Provider/Controller Endpoint Drift

[x] Close earlier drift in calculator / todos / support / consent / admin / contractors / locations / quantities / entries / pay-app
[x] Continue auth / gallery / photos / projects drift cleanup
Current status:
- integrated enough to keep targeted auth/photos/projects tests green
- final custom-lint cleanup is back to zero in the current session

### 2.2 Routing And Endpoint Standardization Rules

[x] Keep `prefer_named_go_router_navigation`
[x] Add `driver_route_contract_sync`
[x] Keep sync table contract ownership enforced by `sync_table_contract_must_come_from_registry`
[x] Lock direct `Printing.sharePdf` / `Printing.layoutPdf` ownership to `PdfOutputService`
[x] Lock direct shipped IDR template loading to `IdrPdfTemplateWriter`
[x] Lock direct `sentry_flutter` ownership to the approved entry/config/logging owners
[x] Freeze follow-up custom-lint work unless new drift appears after the current cleanup
Outcome:
- keep the existing architecture rules active
- only add new lints if a real regression-prone seam reappears

### 2.3 Oversized Surface Audit

[x] Keep one current inventory of god-sized files and central symbols as maintenance-only
Reference:
- [2026-04-08-beta-research-inventory.md](/C:/Users/rseba/Projects/Field_Guide_App/.codex/plans/2026-04-08-beta-research-inventory.md)

## Phase 3: Pre-Merge Security And Migration Blockers

### 3.1 Security Surfaces From Notion Audit

[x] Audit `supabase/functions/codex-admin-sql`
Outcome:
- function source was an undocumented arbitrary-SQL executor over `SUPABASE_DB_URL`
- repo source has been removed from the beta branch; remote undeploy still needs environment-side follow-through if this function was already deployed
[x] Gate or delete `debug_emit_sync_hint_self`
Outcome:
- driver diagnostics no longer exposes the debug broadcast route
- `supabase/functions/sync-hint-debug` has been removed from the repo
- consolidated migration `20260408160000_sync_hint_final_state.sql` no longer defines the debug RPC and explicitly drops any stale copy
[x] Land `daily-sync-push` rate-limiting hardening
Outcome:
- added persisted client-side coalescing in `daily_sync_push_rate_limiter.dart` so duplicate broad `daily_sync` pushes do not retrigger the same quick sync across handler restarts or background queueing
- wired the limiter through `fcm_handler.dart` and `fcm_background_callback.dart`, with targeted regression coverage in `test/features/sync/application/fcm_handler_test.dart`
- added server-side dispatch claiming via `supabase/migrations/20260408173000_sync_push_rate_limit.sql` and the `claim_sync_push_rate_limit` RPC so the edge function can suppress duplicate fan-out for the same scope within the guard window
- updated `supabase/functions/daily-sync-push/index.ts` to rate-limit before FCM lookup/realtime broadcast fan-out and return a non-error `202` response when the dispatch slot is still cooling down

### 3.2 Migration Safety

[x] Restore a reproducible local Supabase bootstrap/reset path before merge
Outcome needed:
- added `20260101000000_bootstrap_base_schema.sql` to restore the missing base schema bootstrap
- guarded later migrations that assumed a seeded auth user, a pre-created `project_assignments` table, or an already-defined `broadcast_sync_hint_project()` function
- verified `supabase start`, `supabase status`, `supabase migration list --local`, and `supabase db reset` successfully in the current shell
[x] Squash the sync-hint migration churn into a clean final-state migration set before merge
Outcome:
- deleted the incremental April sync-hint churn migrations in favor of one final-state file: `20260408160000_sync_hint_final_state.sql`
[x] Backfill rollback SQL for the recent uncovered migration wave
Outcome:
- added `supabase/rollbacks/20260408160000_rollback.sql` for the consolidated sync-hint stack
[x] Enforce paired rollback SQL for new Supabase migrations in CI
Outcome:
- added `scripts/check_changed_migration_rollbacks.py` so CI fails when a changed migration is missing its companion `supabase/rollbacks/<timestamp>_rollback.sql`
- added `scripts/validate_migration_rollbacks.py` so the repo also enforces forward rollback coverage for the new migration era starting at `20260408160000`
- wired `.github/workflows/quality-gate.yml` to run both rollback guards inside `architecture-validation`
- kept historical pre-convention migrations out of scope so the guard is forward-enforcing instead of retroactively blocking the branch

## Phase 4: Oversized Core Surface Reduction

### 4.1 Highest Priority Files

[x] `lib/core/driver/driver_server.dart`
Current status:
- down to 209 LOC in the working tree after the widget-inspector, data/sync, file-injection, interaction/navigation, and shell endpoint extractions
- extracted widget-tree inspection helpers into `lib/core/driver/driver_widget_inspector.dart`
- extracted sync/data request handling into `lib/core/driver/driver_data_sync_handler.dart`
- extracted file/document/photo injection routes into `lib/core/driver/driver_file_injection_handler.dart`
- extracted tap/text/scroll/back/navigate/wait/overlay/route handlers into `lib/core/driver/driver_interaction_handler.dart` (551 LOC helper)
- extracted ready/find/tree/screenshot/hot-restart endpoints into `lib/core/driver/driver_shell_handler.dart` (241 LOC helper)
- `DriverServer` is now a thin lifecycle and dispatch shell rather than a beta blocker
[x] `lib/core/logging/logger.dart`
Current status:
- facade is now down to 346 LOC and imported by 279 files; transport, runtime-hook, and Sentry concerns have been moved out of the main file
- extracted payload redaction and JSON-safety into `lib/core/logging/log_payload_sanitizer.dart`
- `Logger` now delegates scrubbing/JSON-safe coercion to the helper instead of owning those concerns inline
- extracted file transport and sink lifecycle into `lib/core/logging/logger_file_transport.dart` (348 LOC)
- extracted HTTP transport into `lib/core/logging/logger_http_transport.dart` (98 LOC)
- extracted Sentry/error-reporting flow into `lib/core/logging/logger_error_reporter.dart` (101 LOC)
- extracted runtime hooks and lifecycle observer wiring into `lib/core/logging/logger_runtime_hooks.dart` (72 LOC)
- extracted direct Sentry capture ownership into `lib/core/logging/logger_sentry_transport.dart` (44 LOC)
- `lib/features/settings/presentation/screens/help_support_screen.dart` now routes bug-report UI through `lib/core/config/sentry_feedback_launcher.dart` instead of importing the Sentry SDK directly
- `no_direct_sentry_usage_outside_approved_owners` now lint-locks direct `sentry_flutter` imports to `lib/main.dart`, `sentry_pii_filter.dart`, `sentry_feedback_launcher.dart`, and `logger_sentry_transport.dart`
- logger/Sentry refactor is now effectively closed for beta; follow-up work is additive coverage or future facade cleanup, not unresolved ownership drift
[x] `lib/core/database/database_service.dart`
Current status:
- down to 185 LOC and imported by 105 files
- extracted fresh-install bootstrap, index creation, schema verification, and entry-scoped `project_id` repair into `lib/core/database/database_bootstrap.dart` (190 LOC)
- extracted lower-version upgrade migrations `v2-v24` into `lib/core/database/database_upgrade_foundation.dart` (674 LOC)
- extracted daily-entry / review-submit workflow migrations `v25-v27` into `lib/core/database/database_upgrade_entry_workflows.dart` (290 LOC)
- extracted sync-engine foundation / rebuild migrations `v28-v37` into `lib/core/database/database_upgrade_sync_engine.dart` (550 LOC)
- extracted cleanup/stabilization migrations `v38-v42` into `lib/core/database/database_upgrade_stabilization.dart` (205 LOC)
- extracted late upgrade migrations `v43-v56` into `lib/core/database/database_upgrade_repairs.dart` (532 LOC)
- `DatabaseService` is now a thin lifecycle/open/close facade with migration dispatch only
- added `test/core/database/migration_v42_test.dart` to lock the pre-`v43` upgrade path against future registry drift
[x] `lib/features/forms/data/services/form_pdf_service.dart`
Current status:
- down to 195 LOC after extracting field matching, row mapping, checkbox parsing, summary fallback formatting, preview-cache ownership, template-byte loading/caching, signature stamping, shared PDF output/save/share ownership, and the remaining rendering orchestration
- extracted `lib/features/forms/data/services/form_pdf_field_writer.dart` (524 LOC)
- extracted `lib/features/forms/data/services/form_pdf_preview_cache.dart` (63 LOC)
- extracted `lib/features/forms/data/services/form_pdf_signature_stamper.dart` (139 LOC)
- extracted `lib/features/forms/data/services/form_pdf_template_loader.dart` (100 LOC)
- extracted `lib/features/forms/data/services/form_pdf_rendering_service.dart` (258 LOC)
- extracted shared preview/share/save/temp persistence ownership into `lib/features/pdf/services/pdf_output_service.dart` (238 LOC)
- pure-logic form-PDF tests now execute the production helper instead of a mirrored in-test copy, which removes a second drifting contract surface
- screens now route export sharing back through `FormPdfService` instead of calling `Printing.sharePdf` directly
- `FormPdfService` is now a thin facade over preview/output/signature/rendering seams rather than a beta blocker
[x] `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`
Current status:
- down to 276 LOC after extracting the tabular tail into `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_tabular_runner.dart` (183 LOC), structure detection into `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_structure_runner.dart` (177 LOC), runtime/attempt scaffolding into `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_stage_runtime.dart` (145 LOC), retry-loop/per-attempt orchestration into `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_attempt_runner.dart` (165 LOC), attempt lifecycle into `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_attempt_lifecycle.dart` (261 LOC), and top-level orchestration/stage dispatch into `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_facade.dart` (219 LOC)
- OCR orchestration already lives in `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_ocr_runner.dart` (236 LOC)
- recent passes moved row classification, final header consolidation, row merging, cell extraction, numeric interpretation, row parsing, field-confidence scoring, structure detection, runtime support, retry orchestration, and attempt lifecycle out of the main file
- stage-trace and registry contract tests stayed green, which keeps the emitted stage-id contract intact for downstream diagnostics consumers
- `ExtractionPipeline` is now a thin orchestrator plus injected runners rather than a beta blocker

### 4.2 Next Queue

[x] `lib/services/soft_delete_service.dart`
Current status:
- down to 237 LOC after extracting purge/delete-push support into `lib/services/soft_delete_purge_support.dart` (307 LOC), restore orchestration into `lib/services/soft_delete_restore_support.dart` (253 LOC), and storage-cleanup queue ownership into `lib/services/soft_delete_storage_support.dart` (85 LOC)
- `SoftDeleteService` is now primarily the project/entry cascade facade plus count delegation, not a central beta blocker
- targeted soft-delete verification stayed green across cascade, restore, purge, hard-delete, and change-log cleanup behavior
- no new lint rule landed here; this seam was internal decomposition rather than a repeatable repo-wide architecture boundary
[x] `lib/features/pdf/services/pdf_service.dart`
- down to 91 LOC after extracting shared output/save/share/preview ownership, the multi-file export bundle writer, and the shipped IDR template owner
- extracted `lib/features/pdf/services/pdf_output_service.dart` (238 LOC)
- extracted `lib/features/pdf/services/pdf_export_models.dart` (44 LOC)
- extracted `lib/features/pdf/services/pdf_export_bundle_writer.dart` (118 LOC)
- extracted `lib/features/pdf/services/idr_pdf_template_writer.dart` (285 LOC)
- `PdfService` is now a thin export/output/template facade rather than a beta blocker
- `no_direct_idr_template_usage` now lint-enforces that the shipped IDR template asset only loads in the approved writer
[x] `lib/features/projects/data/services/project_lifecycle_service.dart`
- down to 215 LOC after extracting the local device-eviction transaction into `lib/features/sync/engine/project_local_eviction_executor.dart` (272 LOC)
- `ProjectLifecycleService` now keeps argument validation, unsynced-change policy, enrollment, local delete authorization, and remote Supabase delete/restore instead of owning delete-graph traversal, sync suppression, mutex lifecycle, conflict cleanup, or fresh-pull cursor reset inline
- existing sync/data-safety lints now approve the new executor as the hard-delete owner, and `no_change_log_mutation_outside_sync_owners` no longer needs to whitelist `project_lifecycle_service.dart`
- re-ran `flutter analyze`, `dart run custom_lint`, `flutter test --concurrency 1 test/features/projects/data/services/project_lifecycle_service_test.dart test/features/projects/integration/project_lifecycle_integration_test.dart test/features/sync/engine/scope_revocation_cleaner_test.dart`, and the targeted lint-package tests green after the extraction
[x] `lib/features/sync/application/realtime_hint_handler.dart`
- down to 245 LOC after extracting registration/deactivation RPCs, channel subscribe/refresh lifecycle, fallback polling, and transport-health publication into `lib/features/sync/application/realtime_hint_transport_controller.dart` (369 LOC)
- `RealtimeHintHandler` now keeps payload parsing, dirty-scope marking, quick-sync throttling, and the public facade instead of transport ownership
- updated the existing sync-hint ownership lints so the new helper is an approved transport owner rather than weakening the boundary
- re-ran `flutter analyze`, `dart run custom_lint`, `flutter test --concurrency 1 test/features/sync/application/realtime_hint_handler_test.dart test/features/sync/characterization/characterization_realtime_hint_test.dart test/features/auth/domain/use_cases/sign_out_use_case_test.dart`, and the targeted lint-package sync-integrity tests green after the extraction

## Phase 5: Platform And Product Gaps

These were the remaining product/platform scope items after the refactor queue closed. They are now fully accounted for in repo state.

Explicitly moved out of pre-beta scope:
- accessibility audit on high-traffic screens
- GDPR/account deletion
- full multi-language localization rollout beyond English scaffolding

Closed beta gates in this phase:
- i18n scaffolding is now wired through Flutter localization plumbing (`flutter_localizations`, `l10n.yaml`, generated `AppLocalizations`, and localized shell-tab labels)
- responsive shell/layout adoption is now in place for the remaining obvious shell and export surfaces (`SettingsScreen`, `FormGalleryScreen`, `FormViewerScreen`, and `PayApplicationDetailScreen`)
- settings data export UI now has a project-scoped `Saved Exports` route under Settings with reusable save-copy/share actions on the unified export-artifact store
- contractor bulk import now supports file parsing, preview, batch validation, and import apply from the project contractors surface
- biometric/PIN lock now ships as a settings-managed app lock with runtime gate and lifecycle auto-lock
- weather offline cache now persists weather snapshots for cached/fallback reads across offline periods
- `daily-sync-push` rate-limiting hardening is now live on both the client and edge-function paths
- rollback CI enforcement is now live in the quality gate

[x] i18n scaffolding implementation
[x] responsive shell/layout adoption
[x] settings data export UI for forms/pay apps/export artifacts
[x] contractor bulk import
[x] biometric/PIN lock
[x] weather offline cache
[x] `daily-sync-push` rate-limiting hardening
[x] rollback CI enforcement

## Active Sprint Slice: Responsive Rollout Completion

Context:
- responsive primitives already exist (`AppBreakpoint`, `AppResponsiveBuilder`, `AppResponsivePadding`, `AppAdaptiveLayout`)
- current rollout is partial: several top-level screens still render plain mobile-first layouts with no breakpoint-aware structure
- user confirmed responsive adoption is an absolute beta requirement across phones, tablets, and desktop/laptop usage
- user also confirmed that i18n should stop at English-only scaffolding; do not expand localization scope beyond the existing plumbing

Audit snapshot on 2026-04-08:
- already responsive:
  - `project_list_screen.dart`
  - `project_setup_screen.dart`
  - `project_dashboard_screen.dart`
  - `entries_list_screen.dart`
  - `form_gallery_screen.dart`
  - `form_viewer_screen.dart`
  - `pay_application_detail_screen.dart`
  - `quantities_screen.dart`
  - `quantity_calculator_screen.dart`
  - `settings_screen.dart`
  - `settings_saved_exports_screen.dart`
  - `todos_screen.dart`
- still lacking explicit responsive structure among top-level screens:
  - auth flow: `login_screen.dart`, `register_screen.dart`, `company_setup_screen.dart`, `profile_setup_screen.dart`, `forgot_password_screen.dart`, `otp_verification_screen.dart`, `update_password_screen.dart`
  - core field workflow/support screens: `mdot_hub_screen.dart`, `contractor_comparison_screen.dart`, `gallery_screen.dart`, `contractor_selection_screen.dart`
  - entries/review flow: `drafts_list_screen.dart`, `entry_review_screen.dart`, `review_summary_screen.dart`, `entry_editor_screen.dart`, `entry_pdf_preview_screen.dart`
  - settings/support/admin flow: `admin_dashboard_screen.dart`, `consent_screen.dart`, `edit_profile_screen.dart`, `help_support_screen.dart`, `trash_screen.dart`, `personnel_types_screen.dart`, `app_lock_settings_screen.dart`, `app_lock_unlock_screen.dart`
  - sync/analytics/tooling screens: `sync_dashboard_screen.dart`, `conflict_viewer_screen.dart`, `project_analytics_screen.dart`, `calculator_screen.dart`, `pdf_import_preview_screen.dart`, `mp_import_preview_screen.dart`, `toolbox_home_screen.dart`

Implementation policy:
- treat top-level screens as complete only when they have intentional compact vs medium/expanded structure, not just wider padding
- prefer shared responsive primitives over ad hoc `MediaQuery` branching
- focus first on high-traffic field/user flows before low-frequency admin/support surfaces
- keep this as screen-layout work, not a new design-system or localization expansion

[x] Wave 1: highest-impact responsive gaps
- auth screens
- MDOT/forms hub surface
- contractor comparison
- gallery
- entry review/drafts screens

[x] Wave 2: secondary operational surfaces
- sync dashboard and conflict viewer
- admin dashboard
- consent/help/trash/personnel types/edit profile
- import preview and toolbox surfaces

Responsive rollout progress since the 2026-04-08 audit:
- [x] auth/onboarding flow now has a shared responsive shell across the full sign-in and recovery path:
  - `login_screen.dart`
  - `register_screen.dart`
  - `company_setup_screen.dart`
  - `profile_setup_screen.dart`
  - `forgot_password_screen.dart`
  - `otp_verification_screen.dart`
  - `update_password_screen.dart`
- [>] `mdot_hub_screen.dart` already delegated breakpoint-aware layout through `MdotHubBodyContent`, so this slice kept the existing responsive body contract rather than layering on another shell
- [x] field workflow surfaces now reflow intentionally at wider breakpoints:
  - `contractor_comparison_screen.dart`
  - `gallery_screen.dart`
  - `contractor_selection_screen.dart`
- [x] entries/review flow now has breakpoint-aware scaffolding on the remaining user-facing surfaces:
  - `drafts_list_screen.dart`
  - `entry_review_screen.dart`
  - `review_summary_screen.dart`
  - `entry_pdf_preview_screen.dart`
- [>] `entry_editor_screen.dart` already had responsive body orchestration through `EntryEditorBody`, so no additional screen-level shell was required in this slice
- [x] support/admin/tools responsive rollout now covers the requested surfaces:
  - `help_support_screen.dart`
  - `edit_profile_screen.dart`
  - `trash_screen.dart`
  - `consent_screen.dart`
  - `personnel_types_screen.dart`
  - `app_lock_settings_screen.dart`
  - `app_lock_unlock_screen.dart`
  - `admin_dashboard_screen.dart`
  - `sync_dashboard_screen.dart`
  - `conflict_viewer_screen.dart`
  - `toolbox_home_screen.dart`
- [x] analytics/import preview surfaces now finish the remaining top-level rollout:
  - `project_analytics_screen.dart`
  - `pdf_import_preview_screen.dart`
  - `mp_import_preview_screen.dart`
- [x] calculator top-level shell required no additional work because the actual tab bodies were already breakpoint-aware through `HmaCalculatorTab` and `ConcreteCalculatorTab`
- [x] responsive rollout is now closed for the audited top-level screens; future work is maintenance-only when new surfaces or regressions appear

## Active Sprint Slice: 2026-04-08 Routing + Tracker Consolidation

### Slice A: Centralize the beta planning surface

[x] create one canonical beta tracker
[x] create one durable CodeMunch + Notion research artifact
[x] wire both artifacts into the existing beta docs

### Slice B: Finish current lint drift

[x] eliminate remaining `custom_lint` warnings without weakening rules
Open at slice start:
- sync-hint RPC owner warning
- driver diagnostics post-RPC refresh warning
- max-import-count warnings in 3 tests

### Slice C: Cross-reference Notion blockers with current repo reality

[x] forms-export blocker is now closed in code, even though Notion snapshot still listed forms test gaps
[x] routing production gap concern was checked; the real issue was driver parity, now closed
[x] security blockers now have concrete repo follow-through for `debug_emit_sync_hint_self` and `codex-admin-sql`
[x] active oversized beta refactor queue is closed; remaining large files are lower-priority or outside the current beta decomposition list

## Verification Ledger

Most recently confirmed green before this tracker was created:
- `flutter analyze`
- routing suite around `app_router`, `app_redirect`, `scaffold_with_nav_bar`, driver route contract, and form dispatcher
- forms export mapping matrix and shipped PDF filler tests
- targeted auth/photos/projects/provider tests

Current session re-verified:
- `flutter analyze`
- `dart run custom_lint`
- `flutter test --concurrency 1 test/features/forms/services/form_pdf_service_test.dart test/features/forms/services/form_pdf_service_debug_test.dart test/features/forms/services/form_pdf_service_cache_test.dart test/features/forms/services/form_export_mapping_matrix_test.dart test/features/forms/domain/usecases/export_form_use_case_test.dart test/services/pdf_service_test.dart test/services/pdf_service_debug_test.dart`
- `flutter test test/features/auth/domain/use_cases/sign_out_use_case_test.dart`
- `flutter test test/features/entries/domain/usecases/export_entry_use_case_test.dart test/features/quantities/presentation/screens/quantities_screen_export_flow_test.dart test/features/quantities/presentation/screens/quantities_screen_pay_app_export_flow_test.dart`
- `flutter test test/features/sync/application/server_hint_plumbing_test.dart`
- `flutter test test/core/logging/log_payload_sanitizer_test.dart test/core/logging/logger_scrubbing_test.dart test/core/logging/logger_test.dart test/core/logging/logger_rotation_test.dart test/core/di/sentry_integration_test.dart`
- `flutter test --concurrency 1 test/core/logging/logger_test.dart test/core/database/database_service_test.dart test/core/database/database_service_project_id_repair_test.dart test/core/database/schema_verifier_report_test.dart test/core/driver/driver_route_contract_test.dart test/core/driver/driver_server_sync_status_test.dart`
- `flutter test --concurrency 1 test/core/driver/driver_server_sync_status_test.dart test/features/sync/application/server_hint_plumbing_test.dart`
- `flutter test --concurrency 1 test/core/database/database_service_test.dart test/core/database/database_service_project_id_repair_test.dart test/core/database/schema_verifier_report_test.dart`
- `flutter test --concurrency 1 test/core/driver/driver_route_contract_test.dart test/core/driver/driver_server_sync_status_test.dart test/core/driver/driver_file_injection_test.dart`
- `flutter test --concurrency 1 test/features/forms/services/form_pdf_service_test.dart test/features/forms/services/form_pdf_service_debug_test.dart test/features/forms/services/form_pdf_service_cache_test.dart test/features/forms/services/form_export_mapping_matrix_test.dart`
- `flutter test --concurrency 1 test/core/database/database_service_test.dart test/core/database/database_service_project_id_repair_test.dart test/core/database/schema_verifier_report_test.dart test/core/database/migration_v43_test.dart test/core/database/migration_v47_test.dart test/core/database/extraction_schema_migration_test.dart test/core/database/project_assignment_changelog_repair_test.dart`
- `flutter test --concurrency 1 test/features/forms/services/form_pdf_service_test.dart test/features/forms/services/form_pdf_service_debug_test.dart test/features/forms/services/form_pdf_service_cache_test.dart test/features/forms/services/form_export_mapping_matrix_test.dart test/core/database/database_service_test.dart test/core/database/database_service_project_id_repair_test.dart test/core/database/schema_verifier_report_test.dart test/features/pdf/extraction/pipeline/extraction_pipeline_test.dart`
- `flutter analyze`
- `dart run custom_lint`
- `flutter test --concurrency 1 test/features/contractors/data/services/contractor_import_service_test.dart test/features/contractors/presentation/providers/contractor_provider_test.dart test/features/settings/data/services/app_lock_storage_test.dart test/features/settings/presentation/providers/app_lock_provider_test.dart test/features/settings/presentation/screens/app_lock_settings_screen_test.dart test/features/settings/presentation/screens/settings_screen_test.dart test/services/weather_service_test.dart`
- `flutter test --concurrency 1 test/features/sync/application/fcm_handler_test.dart test/features/sync/application/server_hint_plumbing_test.dart`
- `python scripts/check_changed_migration_rollbacks.py supabase/migrations/20260408173000_sync_push_rate_limit.sql`
- `python scripts/validate_migration_rollbacks.py`
- `supabase migration list --local`
- `supabase db reset --local`
- `flutter analyze`
- `dart run custom_lint`
- `flutter test --concurrency 1 test/core/database/database_service_test.dart test/core/database/database_service_project_id_repair_test.dart test/core/database/schema_verifier_report_test.dart test/core/database/migration_v43_test.dart test/core/database/migration_v47_test.dart test/core/database/extraction_schema_migration_test.dart test/core/database/project_assignment_changelog_repair_test.dart test/features/sync/schema/support_ticket_schema_test.dart`
- `flutter analyze`
- `dart run custom_lint`
- `flutter test --concurrency 1 test/core/database/migration_v42_test.dart test/core/database/database_service_test.dart test/core/database/database_service_project_id_repair_test.dart test/core/database/schema_verifier_report_test.dart test/core/database/migration_v43_test.dart test/core/database/migration_v47_test.dart test/core/database/extraction_schema_migration_test.dart test/core/database/project_assignment_changelog_repair_test.dart test/features/sync/schema/support_ticket_schema_test.dart`
- `flutter analyze`
- `dart run custom_lint`
- `flutter test --concurrency 1 test/features/pdf/extraction/pipeline/extraction_pipeline_test.dart test/features/pdf/extraction/pipeline/re_extraction_loop_test.dart test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart test/features/pdf/extraction/pipeline/stage_registry_contract_test.dart`
- `flutter analyze`
- `dart run custom_lint`
- `flutter test --concurrency 1 test/core/driver/driver_route_contract_test.dart test/core/driver/driver_server_sync_status_test.dart test/core/driver/driver_file_injection_test.dart`
- `flutter analyze`
- `dart run custom_lint`
- `flutter test --concurrency 1 test/core/logging/log_payload_sanitizer_test.dart test/core/logging/logger_scrubbing_test.dart test/core/logging/logger_test.dart test/core/logging/logger_rotation_test.dart test/core/di/sentry_integration_test.dart`
- `flutter analyze`
- `dart run custom_lint`
- `flutter test --concurrency 1 test/features/forms/services/form_pdf_service_test.dart test/features/forms/services/form_pdf_service_debug_test.dart test/features/forms/services/form_pdf_service_cache_test.dart test/features/forms/services/form_export_mapping_matrix_test.dart test/features/forms/domain/usecases/export_form_use_case_test.dart`
- `flutter test --concurrency 1 test/features/forms/presentation/screens/form_sub_screens_test.dart test/features/forms/presentation/controllers/form_viewer_controller_test.dart test/features/forms/presentation/providers/form_export_provider_test.dart`
- `dart test test/architecture/no_direct_printing_output_usage_test.dart` (run from `fg_lint_packages/field_guide_lints`)
- `flutter test --concurrency 1 test/features/forms/services/form_pdf_signature_stamper_test.dart test/features/forms/services/form_pdf_service_test.dart test/features/forms/services/form_pdf_service_debug_test.dart test/features/forms/services/form_pdf_service_cache_test.dart test/features/forms/services/form_export_mapping_matrix_test.dart test/features/forms/domain/usecases/sign_form_response_use_case_test.dart`
- `flutter analyze`
- `dart run custom_lint`

Current session environment check:
- `supabase --version` -> `2.84.2`
- `supabase projects list` confirmed remote access to linked project `vsqvkxvvmnnhdajtgblj` (`Construction Inspector App`)
- `docker version` succeeded with client `29.3.1` and server `Docker Desktop 4.68.0`
- `docker info` succeeded against context `desktop-linux`
- `docker run --rm hello-world` completed successfully
- `supabase start` succeeds and brings up the local stack
- `supabase status` succeeds against the running local stack
- `supabase migration list --local` succeeds and shows the local migration chain including `20260408173000`
- `supabase db reset --local` succeeds end-to-end, including the new `20260408173000_sync_push_rate_limit.sql` migration
- non-blocking warnings remain:
  - local service versions differ slightly from the linked remote project (`gotrue`, `storage-api`)
  - analytics on Windows warns about Docker daemon TCP exposure, but the local stack still starts successfully

## Restart Handoff

Resume from this exact state after restart:
- Supabase CLI is fixed in-shell and verified at `2.84.2`.
- Remote Supabase access is already available through the linked hosted project.
- Docker Desktop and local Supabase validation are now working from repo state.
- the local migration/bootstrap blocker is closed in the current branch.
- contractor bulk import, app lock, and weather offline cache are now implemented rather than deferred.
- sync-push hardening is now active on both client and edge-function paths.
- rollback coverage is now enforced in CI through changed-migration and forward-era guards.
- `driver_server.dart` extraction is effectively closed; the server is now a thin lifecycle/dispatch shell with its endpoint logic delegated into dedicated handlers.
- `logger.dart` extraction is effectively closed; transport, runtime hooks, and Sentry ownership now live in dedicated helpers with direct SDK imports lint-locked to approved owners.
- `database_service.dart` extraction is effectively closed; bootstrap and all upgrade waves now live in dedicated helpers, with `migration_v42_test.dart` guarding the pre-`v43` path.
- `form_pdf_service.dart` extraction is effectively closed; the service is now a thin facade over rendering, preview-cache, signature, and shared PDF output helpers.
- `pdf_service.dart` no longer owns preview/share/save or bundle-file generation inline; it is now a thin export/output/template facade rather than an active beta blocker.
- `extraction_pipeline.dart` extraction is effectively closed; the main file is now a thin orchestrator and the top-level facade/stage dispatch live in `extraction_pipeline_facade.dart`.
- `soft_delete_service.dart` is also below the beta blocker threshold now; its remaining surface is a stable cascade/count facade rather than an oversized decomposition target.
- follow-up custom-lint work should continue targeting regression-prone seams after concrete extractions rather than broad speculative rule churn; the new `Printing` ownership rule is the current example of that approach paying off.

Immediate post-restart verification:
- `docker version`
- `docker info`
- `supabase status`
- `supabase start`
- if local stack comes up: `supabase db reset` and `supabase migration list --local`

Immediate code follow-up once environment is confirmed:
- re-run `flutter analyze`
- re-run `dart run custom_lint`
- continue the next `form_pdf_service.dart` extraction around final orchestration, or switch to `extraction_pipeline.dart` if the form seam stops being the cleanest cut
- keep `extraction_pipeline.dart` visible as the largest remaining central beta surface after the database-service extraction closes

## Append Log

### 2026-04-08 09:xx ET

- Collapsed the beta planning sprawl into this central tracker.
- Bound the tracker to the live Notion export snapshot instead of only the prior local mirror.
- Added a dedicated research inventory artifact for CodeMunch-backed size/ownership findings.
- Added a standing CodeMunch beta audit reference alongside the tracker and research inventory.
- Archived the older Codex plan files under `.codex/plans/completed/` so the active folder stays focused on the live tracker plus reference artifacts.
- Cleaned the remaining `custom_lint` backlog to zero.
- Re-ran `flutter analyze` clean.
- Moved the real Codex tree under `.claude/codex` and replaced the root `.codex` path with a junction so the app repo keeps ignoring `.codex` while the nested `.claude` repo can track the actual Codex files.

### 2026-04-08 09:13 ET

- Re-validated the lint-cleanup slice with clean `flutter analyze`, clean `dart run custom_lint`, and green targeted export/pay-app tests.
- Removed the driver-exposed debug sync-hint probe path and the repo-local `sync-hint-debug` edge function source.
- Removed the undocumented `supabase/functions/codex-admin-sql` source after confirming it was an unrestricted arbitrary-SQL executor.

### 2026-04-08 09:26 ET

- Collapsed the April sync-hint migration churn into `supabase/migrations/20260408160000_sync_hint_final_state.sql`.
- Added `supabase/rollbacks/20260408160000_rollback.sql` so the consolidated sync-hint lane now has explicit rollback coverage.
- Deleted the superseded incremental sync-hint migrations that had repeatedly redefined the same functions over a few hours.
- Re-ran `dart run custom_lint` and `flutter test test/features/sync/application/server_hint_plumbing_test.dart` green after the squash.

### 2026-04-08 09:31 ET

- Extracted widget-tree inspection logic out of `lib/core/driver/driver_server.dart` into `lib/core/driver/driver_widget_inspector.dart` to start burning down the top god-object on the beta queue.
- Re-ran `flutter analyze`, `dart run custom_lint`, and `flutter test test/core/driver/driver_server_sync_status_test.dart test/features/sync/application/server_hint_plumbing_test.dart` green after the extraction.

### 2026-04-08 09:40 ET

- Extracted the sync/data mutation and status endpoints out of `lib/core/driver/driver_server.dart` into `lib/core/driver/driver_data_sync_handler.dart`.
- Extracted file/document/photo injection endpoints out of `lib/core/driver/driver_server.dart` into `lib/core/driver/driver_file_injection_handler.dart`.
- Kept the driver-only lint allowlists tight by approving the new handler owners instead of weakening the rules.
- Re-ran `flutter analyze`, `dart run custom_lint`, and `flutter test test/core/driver/driver_server_sync_status_test.dart test/features/sync/application/server_hint_plumbing_test.dart` green after the extractions.

### 2026-04-08 09:58 ET

### 2026-04-08 10:xx ET

- Confirmed the first logger decomposition slice is in place: `Logger` now delegates payload redaction / JSON-safety to `lib/core/logging/log_payload_sanitizer.dart` while keeping the public API stable.
- Verified targeted logging suites green, with `--concurrency 1` noted as necessary for the global logger/path-provider shared-state tests.
- Fixed Supabase CLI availability in this shell and verified `supabase --version` -> `2.84.2`.
- Confirmed remote Supabase access is already available via the linked project `vsqvkxvvmnnhdajtgblj` (`Construction Inspector App`).
- Confirmed the remaining local Supabase blocker is Docker runtime availability, not Supabase auth or CLI resolution.
- Started Docker Desktop installation via `winget`; admin-side feature enablement, reboot, and first-run startup remain the next environment steps before local-stack validation.
- Continued the logging refactor by centralizing redaction and JSON-safe payload shaping in `lib/core/logging/log_payload_sanitizer.dart`.
- Kept the `Logger` public API stable while moving scrubbing and JSON-safe coercion behind helper delegates.
- Extended the sanitizer/report path so opaque values inside nested list payloads now fall back to JSON-safe strings instead of failing mid-encode.
- Re-ran `flutter analyze`, `dart run custom_lint`, and `flutter test test/core/logging/logger_scrubbing_test.dart test/core/logging/logger_test.dart test/core/logging/logger_rotation_test.dart test/core/di/sentry_integration_test.dart` green after the extraction.
- Confirmed the current shell now resolves Supabase CLI as `supabase 2.84.2`, so the earlier PATH caveat is no longer accurate.
- Updated pure scrubbing callers in `lib/core/config/sentry_pii_filter.dart` and `lib/features/settings/domain/usecases/submit_support_ticket_use_case.dart` to use the sanitizer helper directly instead of depending on `Logger`.
- Added `test/core/logging/log_payload_sanitizer_test.dart` so the logging rules now have direct unit coverage outside `Logger`'s lifecycle/file-I/O state.
- Re-ran `flutter analyze`, `dart run custom_lint`, and the logging verification suite with `--concurrency 1` because the logger tests share global `Logger` and `path_provider` state across files.

### 2026-04-08 10:00 ET

- Re-ran the logging verification slice including `test/core/logging/log_payload_sanitizer_test.dart`, `logger_scrubbing_test.dart`, `logger_test.dart`, `logger_rotation_test.dart`, and `test/core/di/sentry_integration_test.dart` together in the current shell.
- Verified the extracted sanitizer still preserves `Logger` behavior while directly covering opaque-object JSON fallback and nested payload coercion.

### 2026-04-08 10:27 ET

- Confirmed Docker/Desktop is healthy in this environment with successful `docker version`, `docker info`, and `docker run --rm hello-world`.
- Confirmed local Supabase startup is runtime-unblocked and identified the missing local bootstrap path as the next concrete repo blocker.
- Re-audited the remaining god-object queue against the live tree: `driver_server.dart` is down to 922 LOC, `logger.dart` remains 942 LOC, and `database_service.dart` remains the largest central open surface at 2606 LOC.
- Promoted the missing reproducible local Supabase bootstrap/reset path to an explicit beta merge blocker ahead of lower-priority platform gap work.

### 2026-04-08 10:37 ET

- Added `supabase/migrations/20260101000000_bootstrap_base_schema.sql` to restore the missing base Supabase bootstrap that earlier migrations still assumed.
- Patched `20260222100000_multi_tenant_foundation.sql` so empty local resets no longer require a hardcoded auth user seed to exist.
- Patched `20260318180831_fix_project_assignments_review.sql` to skip its review-only policy fix until `project_assignments` actually exists.
- Patched `20260406095500_add_pay_app_export_artifacts.sql` so sync-hint triggers wait for `broadcast_sync_hint_project()` from the later consolidated sync-hint migration.
- Verified the full local validation loop in the current shell: `supabase start`, `supabase status`, `supabase migration list --local`, and `supabase db reset` all succeed.

### 2026-04-08 11:18 ET

- Extracted the form-PDF field writer out of `lib/features/forms/data/services/form_pdf_service.dart` into `lib/features/forms/data/services/form_pdf_field_writer.dart`.
- Moved field-name variation matching, row-to-PDF mapping, checkbox parsing, and summary fallback formatting behind the dedicated helper while keeping `FormPdfService` focused on template/load/orchestration flow.
- Repointed the pure-logic form-PDF tests to the production helper instead of the stale mirrored in-test implementation, then aligned expectations to the real alias contract.
- Re-ran `flutter test --concurrency 1 test/features/forms/services/form_pdf_service_test.dart test/features/forms/services/form_pdf_service_debug_test.dart test/features/forms/services/form_pdf_service_cache_test.dart test/features/forms/services/form_export_mapping_matrix_test.dart`, `flutter analyze`, and `dart run custom_lint` green after the extraction.

### 2026-04-08 11:31 ET

- Extracted preview-cache ownership out of `lib/features/forms/data/services/form_pdf_service.dart` into `lib/features/forms/data/services/form_pdf_preview_cache.dart`.
- Extracted template-byte loading and asset/file cache ownership into `lib/features/forms/data/services/form_pdf_template_loader.dart`, while re-exporting `TemplateLoadException` through `form_pdf_service.dart` to keep the public surface stable.
- Cleaned the late database-upgrade helper so `sync_table_contract_must_come_from_registry` is satisfied there too; the lint caught another hardcoded synced-table list during the cleanup pass.
- Re-ran `flutter analyze`, `dart run custom_lint`, and `flutter test --concurrency 1 test/features/forms/services/form_pdf_service_test.dart test/features/forms/services/form_pdf_service_debug_test.dart test/features/forms/services/form_pdf_service_cache_test.dart test/features/forms/services/form_export_mapping_matrix_test.dart test/core/database/database_service_test.dart test/core/database/database_service_project_id_repair_test.dart test/core/database/schema_verifier_report_test.dart test/features/pdf/extraction/pipeline/extraction_pipeline_test.dart` green after the extractions and lint fixes.

### 2026-04-08 12:08 ET

- Finished the `database_service.dart` migration extraction: `v28-v37` now live in `lib/core/database/database_upgrade_sync_engine.dart` and `v38-v42` now live in `lib/core/database/database_upgrade_stabilization.dart`.
- Reduced `lib/core/database/database_service.dart` to a 185 LOC lifecycle/open/close facade that only dispatches to the extracted migration helpers.
- Reused canonical `PhotoTables` schema definitions inside the `v42` helper instead of hardcoding a second `photos` table shape.
- Added `SyncEngineTables.changeLogRepairTablesV42` so the `v42` cleanup loop only targets tables that actually exist on a real pre-`v43` upgrade path.
- Added `test/core/database/migration_v42_test.dart` to verify a `v41 -> current` style upgrade succeeds without requiring future sync tables and still backfills the entry-scoped `project_id` fields.
- Re-ran `flutter test --concurrency 1 test/core/database/migration_v42_test.dart test/core/database/database_service_test.dart test/core/database/database_service_project_id_repair_test.dart test/core/database/schema_verifier_report_test.dart test/core/database/migration_v43_test.dart test/core/database/migration_v47_test.dart test/core/database/extraction_schema_migration_test.dart test/core/database/project_assignment_changelog_repair_test.dart test/features/sync/schema/support_ticket_schema_test.dart`, `flutter analyze`, and `dart run custom_lint` green after the final hardening pass.

### 2026-04-08 12:17 ET

- Extracted the tabular tail out of `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` into `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_tabular_runner.dart`.
- Reduced `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` to 1215 LOC while preserving the existing stage-emission contract.
- Kept the shared `ExtractionPipelineStageSink` contract instead of creating another duplicated callback surface.
- Re-ran `flutter test --concurrency 1 test/features/pdf/extraction/pipeline/extraction_pipeline_test.dart test/features/pdf/extraction/pipeline/re_extraction_loop_test.dart test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart test/features/pdf/extraction/pipeline/stage_registry_contract_test.dart`, `flutter analyze`, and `dart run custom_lint` green after the extraction.

### 2026-04-08 12:37 ET

- Marked accessibility audit and GDPR/account deletion as explicitly post-beta rather than pre-beta gate items.
- Extracted ready/find/tree/screenshot/hot-restart endpoints out of `lib/core/driver/driver_server.dart` into `lib/core/driver/driver_shell_handler.dart`.
- Reduced `lib/core/driver/driver_server.dart` to 209 LOC and closed it out as a thin lifecycle/dispatch shell rather than an active god-object blocker.
- Extracted the error-reporting pipeline out of `lib/core/logging/logger.dart` into `lib/core/logging/logger_error_reporter.dart`.
- Reduced `lib/core/logging/logger.dart` to 420 LOC while adding direct log-file coverage that `Logger.error()` writes scrubbed error output to `errors.log`.
- Re-ran `flutter test --concurrency 1 test/core/driver/driver_route_contract_test.dart test/core/driver/driver_server_sync_status_test.dart test/core/driver/driver_file_injection_test.dart`, `flutter test --concurrency 1 test/core/logging/log_payload_sanitizer_test.dart test/core/logging/logger_scrubbing_test.dart test/core/logging/logger_test.dart test/core/logging/logger_rotation_test.dart test/core/di/sentry_integration_test.dart`, `flutter analyze`, and `dart run custom_lint` green after the extractions.

### 2026-04-08 12:56 ET

- Extracted shared PDF preview/share/save/temp persistence into `lib/features/pdf/services/pdf_output_service.dart`.
- Reduced `lib/features/forms/data/services/form_pdf_service.dart` to 598 LOC by moving output ownership behind the shared helper while keeping its public facade stable.
- Reduced `lib/features/pdf/services/pdf_service.dart` to 672 LOC by delegating single-PDF save/share/preview behavior into the shared output owner instead of duplicating file-picker and `Printing` flows.
- Removed direct `Printing.sharePdf` calls from `lib/features/forms/presentation/screens/form_viewer_screen.dart` and `lib/features/forms/presentation/screens/mdot_hub_screen.dart`; both screens now route sharing back through `FormPdfService`.
- Wired the existing `no_direct_printing_output_usage` rule into the active architecture rule set so future `Printing.layoutPdf` / `Printing.sharePdf` drift cannot re-enter screens or feature services.
- Re-ran `flutter analyze`, `dart run custom_lint`, `flutter test --concurrency 1 test/features/forms/services/form_pdf_service_test.dart test/features/forms/services/form_pdf_service_debug_test.dart test/features/forms/services/form_pdf_service_cache_test.dart test/features/forms/services/form_export_mapping_matrix_test.dart test/features/forms/domain/usecases/export_form_use_case_test.dart`, `flutter test --concurrency 1 test/features/forms/presentation/screens/form_sub_screens_test.dart test/features/forms/presentation/controllers/form_viewer_controller_test.dart test/features/forms/presentation/providers/form_export_provider_test.dart`, and `dart test test/architecture/no_direct_printing_output_usage_test.dart` from `fg_lint_packages/field_guide_lints` green after the extraction and lint enforcement pass.

### 2026-04-08 13:02 ET

- Extracted the signature-field lookup and fallback stamping path out of `lib/features/forms/data/services/form_pdf_service.dart` into `lib/features/forms/data/services/form_pdf_signature_stamper.dart`.
- Reduced `lib/features/forms/data/services/form_pdf_service.dart` further to 458 LOC, leaving the remaining surface concentrated in the top-level orchestration flow instead of signature internals.
- Added `test/features/forms/services/form_pdf_signature_stamper_test.dart` to lock empty-input passthrough, unknown-form passthrough, and configured fallback stamping behavior.
- Re-ran `flutter test --concurrency 1 test/features/forms/services/form_pdf_signature_stamper_test.dart test/features/forms/services/form_pdf_service_test.dart test/features/forms/services/form_pdf_service_debug_test.dart test/features/forms/services/form_pdf_service_cache_test.dart test/features/forms/services/form_export_mapping_matrix_test.dart test/features/forms/domain/usecases/sign_form_response_use_case_test.dart`, `flutter analyze`, and `dart run custom_lint` green after the extraction.

### 2026-04-08 13:08 ET

- Moved entry export payload models out of `lib/features/pdf/services/pdf_service.dart` into `lib/features/pdf/services/pdf_export_models.dart`.
- Extracted multi-file entry export generation and file writes into `lib/features/pdf/services/pdf_export_bundle_writer.dart`.
- Reduced `lib/features/pdf/services/pdf_service.dart` to 568 LOC and `lib/features/forms/data/services/form_pdf_service.dart` to 457 LOC; both remaining surfaces are now orchestration-heavy rather than platform-output or attachment-file-generation heavy.
- Re-ran `flutter analyze`, `dart run custom_lint`, `flutter test --concurrency 1 test/features/forms/services/form_pdf_service_test.dart test/features/forms/services/form_pdf_service_debug_test.dart test/features/forms/services/form_pdf_service_cache_test.dart test/features/forms/services/form_export_mapping_matrix_test.dart test/features/forms/domain/usecases/export_form_use_case_test.dart test/services/pdf_service_test.dart test/services/pdf_service_debug_test.dart`, and `dart test test/architecture/no_direct_printing_output_usage_test.dart` from `fg_lint_packages/field_guide_lints` green after the bundle-writer extraction.

### 2026-04-08 13:18 ET

- Extracted structure-detection staging out of `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` into `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_structure_runner.dart`.
- Extracted stage-trace/run-state/attempt scaffolding out of `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` into `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_stage_runtime.dart`.
- Reduced `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` to 920 LOC, leaving the remaining surface centered on top-level attempt orchestration and post-processing/quality flow.
- Re-ran `dart run custom_lint` and `flutter test --concurrency 1 test/features/pdf/extraction/pipeline/extraction_pipeline_test.dart test/features/pdf/extraction/pipeline/re_extraction_loop_test.dart test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart test/features/pdf/extraction/pipeline/stage_registry_contract_test.dart` green after the extractions.
- `flutter analyze` crashed in the Flutter toolchain on this pass with `Bad state: Too many elements`, so the branch verification note is being carried by clean `dart analyze` plus the focused extraction test slice for now.

### 2026-04-08 13:22 ET

- Extracted post-processing/quality-validation attempt lifecycle out of `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` into `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_attempt_lifecycle.dart`.
- Reduced `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` further to 632 LOC, leaving the main file focused on top-level orchestration plus extraction-stage dispatch.
- Re-ran `dart analyze`, `dart run custom_lint`, and `flutter test --concurrency 1 test/features/pdf/extraction/pipeline/extraction_pipeline_test.dart test/features/pdf/extraction/pipeline/re_extraction_loop_test.dart test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart test/features/pdf/extraction/pipeline/stage_registry_contract_test.dart` green after the lifecycle extraction.

### 2026-04-08 13:25 ET

- Extracted the retry loop and per-attempt execution shell out of `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` into `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_attempt_runner.dart`.
- Reduced `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` to 526 LOC, leaving the main file primarily as document-lifetime orchestration plus extraction-stage dispatch.
- Re-ran `flutter analyze`, `dart run custom_lint`, and `flutter test --concurrency 1 test/features/pdf/extraction/pipeline/extraction_pipeline_test.dart test/features/pdf/extraction/pipeline/re_extraction_loop_test.dart test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart test/features/pdf/extraction/pipeline/stage_registry_contract_test.dart` green after the attempt-runner extraction.

### 2026-04-08 13:44 ET

- Reduced `lib/services/soft_delete_service.dart` to 260 LOC by extracting purge/delete-push support into `lib/services/soft_delete_purge_support.dart`, restore orchestration into `lib/services/soft_delete_restore_support.dart`, and storage-cleanup queue ownership into `lib/services/soft_delete_storage_support.dart`.
- Kept the public service API stable while moving purge, restore, hard-delete, and storage-queue mechanics behind dedicated helpers.
- Re-ran `flutter analyze`, `dart run custom_lint`, and `flutter test --concurrency 1 test/features/sync/engine/cascade_soft_delete_test.dart test/features/sync/engine/delete_propagation_verifier_test.dart test/services/soft_delete_service_log_cleanup_test.dart` green after the extraction.

### 2026-04-08 13:57 ET

- Extracted realtime transport lifecycle out of `lib/features/sync/application/realtime_hint_handler.dart` into `lib/features/sync/application/realtime_hint_transport_controller.dart`.
- Reduced `lib/features/sync/application/realtime_hint_handler.dart` to 245 LOC, leaving it focused on payload parsing, dirty-scope marking, quick-sync throttling, and public facade methods rather than channel/RPC lifecycle.
- Updated the sync-hint ownership lints so registration/deactivation RPCs and `sync_hint` channel subscriptions are explicitly allowed in the new transport owner instead of silently drifting past the rule boundary.
- Cleaned dead imports left behind in `lib/features/pdf/services/pdf_service.dart` during the verification pass.
- Re-ran `flutter analyze`, `dart run custom_lint`, `flutter test --concurrency 1 test/features/sync/application/realtime_hint_handler_test.dart test/features/sync/characterization/characterization_realtime_hint_test.dart test/features/auth/domain/use_cases/sign_out_use_case_test.dart`, and `dart test test/sync_integrity/no_sync_hint_rpc_outside_approved_owners_test.dart test/sync_integrity/no_sync_hint_broadcast_subscription_outside_realtime_handler_test.dart` from `fg_lint_packages/field_guide_lints` green after the extraction.

### 2026-04-08 14:05 ET

- Extracted the local device-eviction transaction out of `lib/features/projects/data/services/project_lifecycle_service.dart` into `lib/features/sync/engine/project_local_eviction_executor.dart`.
- Reduced `lib/features/projects/data/services/project_lifecycle_service.dart` to 215 LOC, leaving it focused on enrollment, unsynced-change guardrails, local authorization checks, and remote delete/restore RPCs rather than delete-graph traversal, sync suppression, conflict cleanup, or fresh-pull cursor reset.
- Tightened the ownership lints around that seam: `no_change_log_mutation_outside_sync_owners` now points at the new executor instead of the service, and the existing raw-sync/raw-delete owner rules now explicitly approve the executor as the local hard-delete boundary.
- Updated the project-lifecycle integration and scope-revocation fixtures to include the live sync/delete-graph support tables (`sync_lock`, `sync_metadata`, `export_artifacts`, `pay_applications`) that the extracted executor now exercises directly.
- Re-ran `flutter analyze`, `dart run custom_lint`, `flutter test --concurrency 1 test/features/projects/data/services/project_lifecycle_service_test.dart test/features/projects/integration/project_lifecycle_integration_test.dart test/features/sync/engine/scope_revocation_cleaner_test.dart`, and `dart test test/sync_integrity/no_change_log_mutation_outside_sync_owners_test.dart test/sync_integrity/no_synced_projects_mutation_outside_scope_owners_test.dart test/sync_integrity/no_raw_sync_sql_outside_store_owners_test.dart test/data_safety/avoid_raw_database_delete_test.dart` from `fg_lint_packages/field_guide_lints` green after the extraction.

### 2026-04-08 14:14 ET

- Extracted the shipped IDR template owner out of `lib/features/pdf/services/pdf_service.dart` into `lib/features/pdf/services/idr_pdf_template_writer.dart`.
- Reduced `lib/features/pdf/services/pdf_service.dart` to 91 LOC, leaving it focused on export/output orchestration and thin delegation rather than template asset loading, field maps, contractor section filling, formatting, or debug-template generation.
- Added `no_direct_idr_template_usage` so direct `rootBundle.load('assets/templates/idr_template.pdf')` calls in `lib/` must stay inside `IdrPdfTemplateWriter`.
- Re-ran `flutter analyze`, `dart run custom_lint`, `flutter test --concurrency 1 test/services/pdf_service_test.dart test/services/pdf_service_debug_test.dart test/services/pdf_field_mapping_test.dart test/features/forms/services/form_export_mapping_matrix_test.dart`, and `dart test test/architecture/no_direct_idr_template_usage_test.dart` from `fg_lint_packages/field_guide_lints` green after the extraction and lint pass.

### 2026-04-08 14:34 ET

- Finished the remaining logger runtime-hook extraction by moving error-handler installation, zone print capture, lifecycle observer wiring, and `AppLifecycleLogger` out of `lib/core/logging/logger.dart` into `lib/core/logging/logger_runtime_hooks.dart`.
- Reduced `lib/core/logging/logger.dart` further to 346 LOC while keeping the public `Logger` API stable for app startup and existing callers.
- Centralized direct Sentry ownership into `lib/main.dart`, `lib/core/config/sentry_pii_filter.dart`, `lib/core/config/sentry_feedback_launcher.dart`, and `lib/core/logging/logger_sentry_transport.dart`; `help_support_screen.dart` now goes through the launcher instead of importing `sentry_flutter` directly.
- Added `no_direct_sentry_usage_outside_approved_owners` so direct `sentry_flutter` imports cannot drift back into screens or feature services.
- Added `test/core/config/sentry_pii_filter_test.dart` to lock event scrubbing, consent gating, and user/request stripping on the actual Sentry before-send seam.
- Re-ran `flutter analyze`, `dart run custom_lint`, `flutter test --concurrency 1 test/core/logging/logger_test.dart test/core/logging/logger_scrubbing_test.dart test/core/logging/log_payload_sanitizer_test.dart test/core/di/app_bootstrap_test.dart test/core/di/sentry_integration_test.dart test/core/config/sentry_pii_filter_test.dart test/features/settings/presentation/screens/help_support_screen_test.dart`, and `dart test test/architecture/no_direct_sentry_usage_outside_approved_owners_test.dart` from `fg_lint_packages/field_guide_lints` green after the refactor.

### 2026-04-08 14:48 ET

- Finished the remaining `form_pdf_service.dart` seam by moving the rendering-heavy template/open/fill/debug/remarks flow into `lib/features/forms/data/services/form_pdf_rendering_service.dart`.
- Reduced `lib/features/forms/data/services/form_pdf_service.dart` to 195 LOC so it now acts as a thin preview/output/signature/rendering facade.
- Finished the remaining `extraction_pipeline.dart` seam by moving top-level extraction orchestration and stage-dispatch helpers into `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_facade.dart`.
- Reduced `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart` to 276 LOC so it now stays focused on injected stage ownership instead of orchestration internals.
- Re-verified `lib/services/soft_delete_service.dart` at 237 LOC as a stable facade rather than an active beta blocker.
- Re-ran `flutter analyze`, `dart run custom_lint`, and `flutter test --concurrency 1 test/features/forms/services/form_pdf_service_test.dart test/features/forms/services/form_pdf_service_debug_test.dart test/features/forms/services/form_export_mapping_matrix_test.dart test/features/forms/domain/usecases/export_form_use_case_test.dart test/features/pdf/extraction/pipeline/extraction_pipeline_test.dart test/features/pdf/extraction/pipeline/re_extraction_loop_test.dart test/features/pdf/extraction/pipeline/stage_trace_contract_test.dart test/features/pdf/extraction/pipeline/stage_registry_contract_test.dart test/features/sync/engine/cascade_soft_delete_test.dart test/features/sync/engine/delete_propagation_verifier_test.dart test/services/soft_delete_service_log_cleanup_test.dart` green after the final extraction pass.

### 2026-04-08 15:20 ET

- Closed the last three active beta gates that were left after the refactor queue:
  - wired app-level i18n scaffolding with `flutter_localizations`, `l10n.yaml`, generated `AppLocalizations`, and localized shell navigation labels
  - implemented responsive reflow on the remaining obvious shell/export holdouts: `SettingsScreen`, `FormGalleryScreen`, `FormViewerScreen`, and `PayApplicationDetailScreen`
  - added `/settings/saved-exports` with reusable save-copy/share actions on top of the unified export artifact store
- Fixed the audit-discovered export-history type drift by treating photo artifacts consistently (`photo` plus legacy `photo_export` labeling) in the shared history widget.
- Re-ran `flutter analyze`, `dart run custom_lint`, and the targeted shell/settings/forms/pay-app verification slice:
  - `test/core/router/scaffold_with_nav_bar_test.dart`
  - `test/features/settings/presentation/screens/settings_screen_test.dart`
  - `test/features/settings/presentation/screens/settings_saved_exports_screen_test.dart`
  - `test/features/forms/presentation/screens/form_gallery_screen_test.dart`
  - `test/features/pay_applications/presentation/screens/pay_application_detail_screen_test.dart`
  - all green after fixing the test-harness/provider issues surfaced by the audit pass

### 2026-04-08 19:34 ET

- Saved the current sync/state/UI architecture audit after the stale-state and phantom-conflict debugging wave so this context is not lost before the enforcement work lands.
- Core systemic finding: the app is still missing an explicit poisoned-local-state recovery layer. We fix source bugs, but the fixed build inherits stale `change_log`, `conflict_log`, and `sync_metadata` state from the broken build, which is why the same class of issues keeps resurfacing after each patch.
- The practical completion rule for sync bugs is now explicit:
  - code fix
  - repair for already-bad local state
  - dirty-upgrade regression test
- Current best insertion point for that recovery layer is `lib/features/sync/application/sync_initializer.dart`, immediately after opening the database and before normal sync startup. Current durable metadata owner is `lib/features/sync/engine/sync_metadata_store.dart`, surfaced through `lib/features/sync/engine/local_sync_store.dart`.
- First recovery framework slice to build next:
  - `SyncStateRepairRunner`
  - versioned repair jobs recorded in `sync_metadata`
  - first concrete repair job for the known exhausted equipment delete rows created by the old `contractor:` fallback bug
  - developer/beta repair actions after the runner exists
- Audit result: some of the requested contracts are statically enforceable now, but some are not honest lint-only problems and need contract tests plus shared abstractions.
- High-signal rules that are enforceable right now:
  - route-intent ownership for entry flow navigation instead of ad hoc `context.pushNamed('report'/'review'/'entry')`
  - no user-facing integrity diagnostics in sync presentation
  - no raw/unconstrained scrollable bottom-sheet bodies
  - repair/state-healing writes only through approved sync owners and versioned repair jobs
- Contracts that need shared runtime patterns plus tests, not just lint heuristics:
  - one state-ownership rule per screen
  - one mutation contract per provider/screen
  - preload-before-interaction guarantees for form/toolbox screens and sheets
  - responsive dialog/sheet affordance correctness
- Concrete code hotspots found during the audit:
  - `lib/core/design_system/surfaces/app_bottom_sheet.dart` still wraps sheet content in `Flexible`; this is exactly the fragile pattern you called out and explains why some sheets feel broken or visually ambiguous when content height/scroll behavior changes.
  - `lib/features/forms/presentation/screens/form_gallery_screen.dart` opens the new-form picker with `AppBottomSheet.show(... ListView ...)`; this is a likely root cause for the “empty/stuck scroll box at the bottom” behavior in Forms.
  - entry-flow navigation is still scattered across UI files instead of going through a single intent layer:
    - `lib/features/dashboard/presentation/widgets/dashboard_todays_entry.dart`
    - `lib/features/entries/presentation/screens/home_screen_actions.dart`
    - `lib/features/entries/presentation/screens/entries_list_screen.dart`
    - `lib/features/entries/presentation/screens/drafts_list_screen.dart`
    - `lib/features/entries/presentation/screens/entry_review_screen.dart`
    - `lib/features/entries/presentation/screens/review_summary_screen.dart`
    - `lib/features/entries/presentation/screens/entry_editor_state_mixin.dart`
  - sync diagnostics still carry integrity metadata through the user-facing query/controller path even after the section was hidden:
    - `lib/features/sync/application/sync_query_service.dart`
    - `lib/features/sync/presentation/controllers/sync_dashboard_controller.dart`
    - `lib/features/sync/presentation/widgets/sync_dashboard_diagnostics_widgets.dart`
- Standardization direction saved from the user:
  - one explicit local state repair layer
  - versioned repair jobs
  - derived diagnostics treated as rebuildable history, not truth
  - queue healing instead of queue rot after retry exhaustion
  - fresh-state beta/dev tooling
  - build/database/repair fingerprints
  - clean-state and dirty-upgrade coverage for every sync-risk fix
  - one state-ownership rule per screen
  - one mutation contract
  - one route-intent layer
  - one preload contract
  - one responsive content contract for dialogs/sheets
  - contract tests for all of the above
- Next implementation slice should land in this order:
  1. save the route-intent helper and lint boundary for entry flow
  2. add the sync repair runner plus the first versioned repair job
  3. remove integrity diagnostics from the user-facing sync path instead of only hiding the section
  4. harden `AppBottomSheet` with explicit constraints/affordance and lint against raw scrollable builder bodies
  5. add dirty-upgrade tests and beta repair tooling

### 2026-04-08 20:01 ET

- Added a dedicated lint-first implementation plan at `.codex/plans/2026-04-08-lint-first-enforcement-plan.md` so the next hardening wave is anchored to enforceable guardrails instead of ad hoc fixes.
- Locked the first implementation slice to three guardrails before broader sync/UI iteration:
  - entry-flow route-intent ownership
  - removal of user-facing sync integrity diagnostics
  - explicit bottom-sheet scroll/height constraints with lint coverage
- Expanded the route-intent hotspot list after a code pass found additional direct entry-flow calls outside the original audit list:
  - `lib/features/dashboard/presentation/widgets/dashboard_sliver_app_bar.dart`
  - `lib/features/entries/presentation/widgets/entries_list_states.dart`
- Confirmed the sync dashboard still carries integrity data through current live production surfaces:
  - `lib/features/sync/domain/sync_diagnostics.dart`
  - `lib/features/sync/application/sync_query_service.dart`
  - `lib/features/sync/presentation/controllers/sync_dashboard_controller.dart`
  - `lib/features/sync/presentation/widgets/sync_dashboard_diagnostics_widgets.dart`
- Confirmed the current bottom-sheet owner still uses the fragile pattern the user called out:
  - `lib/core/design_system/surfaces/app_bottom_sheet.dart` still wraps arbitrary content in `Flexible`
  - `lib/features/forms/presentation/screens/form_gallery_screen.dart` still passes a raw `ListView` into `AppBottomSheet.show`
- Active rule/watch list for this iteration:
  - no direct entry-flow route calls outside a shared helper
  - no user-facing sync integrity diagnostics
  - no raw scrollable body passed to `AppBottomSheet.show`
  - keep watching for honest opportunities to add lint around mutation completion, preload gating, and sync-repair ownership without pretending static analysis can prove more than it can

### 2026-04-08 20:13 ET

- Landed the first lint-first enforcement slice.
- Entry-flow route ownership:
  - added `lib/features/entries/presentation/navigation/entry_flow_route_intents.dart`
  - rewired dashboard/entries route calls for `entry`, `report`, `review`, and `review-summary` through the helper
  - added custom lint `no_entry_flow_route_calls_outside_intents`
- User-facing sync integrity removal:
  - removed `integrityResults` from `SyncDiagnosticsSnapshot`
  - removed integrity loading from `SyncQueryService`
  - removed integrity state from `SyncDashboardController`
  - deleted the lingering `SyncIntegritySection` user-facing widget surface
  - added custom lint `no_user_facing_sync_integrity_surface`
- Bottom-sheet responsive contract:
  - replaced the old unconstrained `Flexible(child: builder(...))` pattern in `AppBottomSheet` with explicit max-height constrained sheet content
  - added `AppBottomSheet.showScrollable(...)` with a visible scroll affordance
  - migrated the Forms new-form picker to the scrollable sheet path
  - added custom lint `no_scrollable_app_bottom_sheet_body`
- Verification for this slice:
  - targeted root `flutter analyze` on edited app/test files: green
  - targeted `flutter test`:
    - `test/features/sync/application/sync_query_service_test.dart`
    - `test/features/sync/presentation/controllers/sync_dashboard_controller_test.dart`
    - `test/features/sync/presentation/providers/sync_provider_test.dart`
    - `test/features/sync/presentation/screens/sync_dashboard_screen_test.dart`
    - `test/features/forms/presentation/screens/form_gallery_screen_test.dart`
    - all green
  - lint package verification:
    - `dart test` for the 3 new lint rule tests: green
    - `dart analyze lib test` inside `fg_lint_packages/field_guide_lints`: only 3 pre-existing infos in unrelated rule files, no new rule errors
- Verification blocker still present:
  - root `dart run custom_lint` crashes before rule evaluation because workspace scanning trips over a generated Windows plugin path under `windows/flutter/ephemeral/.plugin_symlinks/flusseract/...`
  - this is a tooling/environment blocker, not a lint failure in the new rules, but it still needs a repo-safe workaround so full-root linting is reliable again
- New candidate rules/watch items surfaced during implementation:
  - versioned sync repair registration/ownership lint once `SyncStateRepairRunner` exists
  - preload contract lint only after there is a real shared preload owner abstraction
  - mutation-completion lint only after provider mutation helpers are standardized enough to avoid dishonest heuristics

### 2026-04-08 20:17 ET

- Landed the first sync recovery framework slice:
  - added `SyncStateRepairRunner`
  - added `SyncStateRepairJob` contract
  - registered startup repair execution from `SyncInitializer`
  - added first versioned repair job:
    - `repair_sync_state_v2026_04_08_equipment_tombstones`
- The first repair job is intentionally narrow and only resets exhausted `equipment` `delete` rows whose error text matches the old `contractor:` UUID fallback bug. This is deliberate: the fixed push router already normalizes contractor-derived fallback project IDs correctly, so the correct repair is to un-poison those rows and let the fixed code retry them.
- Added the supporting local-store primitive `resetRetryExhaustedChanges(...)` so future versioned jobs can repair other poisoned queue rows without bypassing the sync I/O owner.
- Verification for the repair slice:
  - targeted `flutter analyze` on the new repair files and touched sync seams: green
  - targeted `flutter test` including `test/features/sync/application/sync_state_repair_runner_test.dart`: green
- Important current limit:
  - this is a one-time versioned startup repair, not a full operator-facing repair console yet
  - if a fresh build poisons a new class of rows tomorrow, we still need:
    - a new versioned repair job
    - eventually a debug/beta repair UI for manual recovery without DB surgery

### 2026-04-08 20:05 ET

- Fixed the repo-root `dart run custom_lint` crash on Windows.
- Root cause:
  - `custom_lint 0.8.1` recursively walked the entire repo from the working directory using `Directory.listSync(recursive: true)`.
  - That traversal followed `windows/flutter/ephemeral/.plugin_symlinks/flusseract` into generated Android `.cxx` content and died on a stale/missing generated path before any lint rules ran.
  - `analysis_options.yaml` excludes could not help because the crash happened during `custom_lint` workspace discovery, before analyzer filtering.
- Repo-safe fix landed:
  - vendored `custom_lint` into `third_party/custom_lint_patched`
  - patched workspace discovery in `third_party/custom_lint_patched/lib/src/workspace.dart` to walk directories safely, skip broken paths, and avoid following symlinked trees
  - pinned the app to the patched CLI with a `dependency_overrides.custom_lint` path override in `pubspec.yaml`
- Follow-on cleanup after root lint started working again:
  - replaced a raw `Divider` in `equipment_manager_dialog.dart`
  - allowed `LocalSyncStore` as a valid `change_log` mutation owner for the new repair primitive
  - aligned `sync_state_repair_runner_test.dart` with `TestDbFactory`
  - added the repair-runner test to the soft-delete-filter allowlist because it intentionally inspects `change_log`
- Verification:
  - root `dart run custom_lint`: green
  - `flutter test test/features/sync/application/sync_state_repair_runner_test.dart`: green

### 2026-04-08 20:33 ET

- Landed the next sync-recovery verification slice so blocked queue state is now visible instead of being silently excluded from the dashboard.
- `SyncDiagnosticsSnapshot` now carries:
  - `totalBlockedCount`
  - `blockedBuckets`
  - `SyncStateFingerprint` with app version, schema version, repair catalog version, applied repair count, and latest applied repair metadata
- `SyncQueryService` now assembles blocked queue diagnostics from `change_log` rows where `processed = 0` and `retry_count >= maxRetryCount`, separate from ordinary pending uploads.
- `LocalSyncStore` now owns the new query primitives for:
  - blocked distinct counts per table / bucket / non-bucket tables
  - schema version reads via `PRAGMA user_version`
  - metadata prefix loads / clears for repair and derived-diagnostics state
- Added `SyncRecoveryService` as the explicit operator-facing repair owner:
  - rerun all known versioned repair jobs on demand
  - rebuild derived diagnostics by clearing `integrity_*` metadata
- Wired the recovery service through startup/DI:
  - `SyncInitializer` now creates it alongside `SyncQueryService`
  - `SyncDeps` now carries it
  - widget-tree providers now expose it for sync dashboard use
- Sync dashboard now surfaces the new state:
  - summary card shows `Pending`, `Blocked`, and `Conflicts`
  - transparency copy explains blocked rows are excluded from pending uploads until repaired
  - new `Device Sync State` card shows build/schema/repair fingerprint data
  - blocked queue has its own bucket section
  - dashboard action tiles now include:
    - `Repair Blocked Queue` when blocked rows exist
    - debug-only `Rebuild Diagnostics`
- Added the next recovery ownership lint:
  - `no_sync_state_repair_runner_instantiation_outside_approved_owners`
  - approved owners are currently `sync_initializer.dart` and `sync_recovery_service.dart`
- Root lint also caught one honest architecture hole during this slice:
  - `sync_metadata_store.dart` needed explicit approval for metadata-table deletes in the `avoid_raw_database_delete` allowlist
  - repair metadata parsing in `SyncQueryService` now logs malformed metadata instead of silently swallowing it
- Verification for this slice:
  - targeted `flutter analyze`: green
  - `flutter test`
    - `test/features/sync/application/sync_query_service_test.dart`
    - `test/features/sync/presentation/controllers/sync_dashboard_controller_test.dart`
    - `test/features/sync/presentation/screens/sync_dashboard_screen_test.dart`
    - `test/features/sync/application/sync_state_repair_runner_test.dart`
    - all green
  - `dart test test/sync_integrity/no_sync_state_repair_runner_instantiation_outside_approved_owners_test.dart` in `fg_lint_packages/field_guide_lints`: green
  - root `dart run custom_lint`: green
- Immediate next sync-hardening TODO from here:
  - do not stop at visibility; add true queue-healing classification and operator repair coverage for more stale-state classes than the current equipment tombstone bug
  - add device/on-S21 validation of the new blocked-state dashboard and repair action against a deliberately poisoned queue

### 2026-04-08 20:49 ET

- Completed on-device dirty-state verification on the S21 for the new blocked queue surface and repair path.
- Verification procedure:
  - rebuilt and reinstalled the current `main_driver.dart` Android debug build on `RFCNC0Y975L`
  - injected a synthetic stale row into the live device DB matching the real repair signature:
    - `change_log.table_name = equipment`
    - `operation = delete`
    - `retry_count = 5`
    - `error_message` containing the old `22P02` / `contractor:` UUID bug text
  - opened `/sync/dashboard` through the live driver build and captured the device UI at each step
- Observed device behavior before repair:
  - dashboard showed `0 Pending`, `1 Blocked`, `0 Conflicts`
  - transparency copy correctly explained that blocked rows are excluded from pending until repaired
  - `Repair Blocked Queue` action was visible and enabled
  - integrity diagnostics remained absent from the user-facing dashboard
- Observed device behavior after tapping `Repair Blocked Queue`:
  - the stale row changed from blocked to ordinary pending in place
  - dashboard refreshed without manual navigation
  - dashboard showed `1 Pending`, `0 Blocked`, `0 Conflicts`
- Observed device behavior after running sync:
  - the repaired row cleared fully
  - dashboard returned to `0 Pending`, `0 Blocked`, `0 Conflicts`
  - no new conflicts were generated by this verification path
- Evidence captured:
  - `.codex/tmp/device_sync_verify/sync-dashboard-blocked-before.png`
  - `.codex/tmp/device_sync_verify/sync-dashboard-after-repair.png`
  - `.codex/tmp/device_sync_verify/sync-dashboard-clean.png`
- Honest tooling gap discovered during verification:
  - the driver-only endpoint `/driver/sync-status` still counted all `processed = 0` rows as pending, so it misreported blocked rows even though the dashboard surface was correct
- Tooling fix landed immediately:
  - `lib/core/driver/driver_data_sync_handler.dart` now reports:
    - `pendingCount`
    - `blockedCount`
    - `unprocessedCount`
  - added `test/core/driver/driver_data_sync_handler_test.dart` to lock the classification contract
- Verification for the tooling fix:
  - `flutter test test/core/driver/driver_data_sync_handler_test.dart`: green
  - targeted `flutter analyze` on the touched driver files: green
  - root `dart run custom_lint`: green
- Current status after reinstall:
  - the S21 is on the latest driver build again
  - `/driver/sync-status` now matches the dashboard semantics
  - device queue is clean (`pending=0`, `blocked=0`, `unprocessed=0`)

### 2026-04-08 21:11 ET

- Expanded the runtime sync repair catalog beyond the first equipment tombstone job.
- New versioned startup repairs now run through `SyncStateRepairRunner`:
  - `repair_sync_state_v2026_04_08_project_assignment_residue`
    - purges impossible pending `project_assignments` queue rows
    - WHY: `project_assignments` is pull-only, so any local `change_log` row for it is poison from the old local-mutation breach
  - `repair_sync_state_v2026_04_08_builtin_form_change_log`
    - purges impossible pending `change_log` rows for `inspector_forms` where `is_builtin = 1`
    - WHY: builtin forms are server-seeded reference data and must never be queued for push
- `LocalSyncStore` now owns the repair-safe queue purge primitives needed by those jobs:
  - `purgePendingChangesForTable(...)`
  - `purgePendingBuiltinInspectorFormChanges()`
- `SyncStateRepairRunner.repairCatalogVersion` advanced to `2026-04-08.2`
- Added the next lint boundary:
  - `no_sync_state_repair_job_outside_repairs_directory`
  - purpose: keep all runtime sync repair jobs in `lib/features/sync/application/repairs/`
- Honest enforcement note:
  - this does not yet prove that every repair job file is registered in `SyncStateRepairRunner`
  - static lint is not honest enough for that cross-file guarantee yet
  - for now, we enforce repair ownership by directory and runner ownership separately
- Verification:
  - `flutter test`
    - `test/features/sync/application/sync_state_repair_runner_test.dart`
    - `test/features/sync/application/sync_query_service_test.dart`
    - `test/features/sync/presentation/screens/sync_dashboard_screen_test.dart`
  - `dart test`
    - `fg_lint_packages/field_guide_lints/test/sync_integrity/no_sync_state_repair_job_outside_repairs_directory_test.dart`
  - targeted `flutter analyze`: green
  - root `dart run custom_lint`: green
- Device state:
  - reinstalled the latest driver build on the S21 after this slice
  - current device run is on the new repair catalog build

### 2026-04-08 21:43 ET

- Live S21 proof completed for the two new stale-state repair classes using the
  fresh driver build and a sanctioned poison-state harness.
- Added explicit driver-only repair verification surfaces:
  - `/driver/inject-sync-poison`
    - allowed scenarios:
      - `project_assignment_residue`
      - `builtin_form_change_log`
  - `/driver/run-sync-repairs`
    - force-runs the approved `SyncRecoveryService` repair path
- Important architecture tightening during that work:
  - direct synthetic `change_log` mutation was NOT left in the driver handler
  - instead:
    - `SyncPoisonStateService` became the explicit sync-application owner
    - `SyncInitializer` now constructs and injects it
    - `LocalSyncStore` owns the actual poison-row I/O
  - this kept the new harness inside the existing sync ownership/lint model
    instead of weakening it
- Live proof results on S21:
  - baseline before each scenario:
    - `pending = 0`
    - `blocked = 0`
    - `unprocessed = 0`
  - `project_assignment_residue`
    - injected one blocked `change_log` row for real local assignment
      `ea526f59-e982-4b3c-902c-ccb48c923f0a`
    - dashboard/driver status surfaced `blocked = 1`
    - repair run removed it cleanly back to `0 / 0 / 0`
  - `builtin_form_change_log`
    - injected one blocked builtin-form `change_log` row for builtin form
      `mdot_0582b`
    - dashboard/driver status surfaced `blocked = 1`
    - repair run removed it cleanly back to `0 / 0 / 0`
- Saved proof artifacts:
  - `.codex/tmp/device_sync_verify_repairs/repair-proof-summary.json`
  - `.codex/tmp/device_sync_verify_repairs/sync-dashboard-clean-before.png`
  - `.codex/tmp/device_sync_verify_repairs/project-assignment-blocked.png`
  - `.codex/tmp/device_sync_verify_repairs/project-assignment-clean.png`
  - `.codex/tmp/device_sync_verify_repairs/builtin-form-blocked.png`
  - `.codex/tmp/device_sync_verify_repairs/builtin-form-clean.png`
- Product-surface follow-up from the proof:
  - the old dashboard copy was lying by implying the action only “reset blocked
    rows for retry”
  - repairs can also purge impossible residue, so the dashboard action was
    renamed conceptually to `Repair Sync State` with generic success messaging
- Added the requested debug/settings recovery surface:
  - `Repair Sync State`
  - `Rebuild Sync Diagnostics`
  - both now live in `Settings > Sync & Data` for debug builds
- Verification after this slice:
  - `flutter analyze` on touched sync/settings/driver files: green
  - `flutter test`
    - `test/core/driver/driver_data_sync_handler_test.dart`
    - `test/features/sync/application/sync_state_repair_runner_test.dart`
    - `test/features/sync/presentation/controllers/sync_dashboard_controller_test.dart`
    - `test/features/sync/presentation/screens/sync_dashboard_screen_test.dart`
    - `test/features/settings/presentation/screens/settings_screen_test.dart`
  - root `dart run custom_lint`: green
- Honest remaining note:
  - this proves the repair job code and repair-service path live on-device for
    these two poison classes
  - we still have not yet re-proved the exact cold-start “first launch after
    upgrade” metadata-gated path on S21 for these two jobs

### 2026-04-08 22:15 ET

- Corrected the sync-surface direction after an accidental drift toward a
  separate production `Sync Status` screen.
- Product direction is now explicit:
  - keep the existing `/sync/dashboard` route
  - treat it as the single user-facing `Sync Status` screen
  - gate raw diagnostics and conflict-log tooling for debug/internal use
  - do not proliferate more sync screens
- Fresh audit of the current merge/conflict path confirmed:
  - `ConflictResolver` exists and is working as designed
  - it is engine-only LWW plus `conflict_log` audit history
  - `ConflictViewerScreen` is still a debug/audit tool, not a real
    production merge workflow
- The real architecture gap was provider-owned sync attention state:
  - `SyncProvider` knew pending counts and generic notifications
  - it did not project grouped conflict attention or blocked queue attention
    into the shell/app-bar/user-facing sync surface
- Landed the first one-screen sync-status slice:
  - `SyncProvider` now loads and exposes:
    - `blockedCount`
    - `activeConflictCount`
    - `hasBlockedAttention`
    - `hasConflictAttention`
    - deduped sync notices
  - provider refresh now reloads blocked/conflict attention alongside pending
    state during startup and after sync completion
  - provider now emits user-safe notices when:
    - grouped conflict attention increases
    - blocked queue attention increases
  - the existing dashboard app bar/title now reads `Sync Status`
  - the same screen now keeps only the user-safe layer always visible:
    - summary
    - transparency copy
    - notices
    - actions
    - report issue entrypoint
  - debug-only on that same screen:
    - `View Conflict Log`
    - device fingerprint card
    - pending bucket diagnostics
    - blocked bucket diagnostics
    - rebuild diagnostics
    - stuck-records card
  - settings now labels the entrypoint `Sync Status`
  - sync actions now expose `Report Sync Issue`, which routes into the
    existing help/support flow
  - shell banners now surface blocked/conflict attention in user-safe copy
  - app-bar sync icon now reflects blocked/conflict attention instead of only
    pending transport state
  - `/sync/conflicts` route is now debug-only
- Added lint:
  - `no_sync_conflict_navigation_outside_debug_owners`
  - intent: keep raw conflict-log navigation from drifting back into
    arbitrary product screens
- Verification:
  - targeted `flutter analyze`: green
  - `flutter test`
    - `test/features/sync/presentation/providers/sync_provider_test.dart`
    - `test/features/sync/presentation/screens/sync_dashboard_screen_test.dart`
    - `test/features/settings/presentation/screens/settings_screen_test.dart`
    - `test/features/sync/presentation/controllers/sync_dashboard_controller_test.dart`
  - `dart test`
    - `fg_lint_packages/field_guide_lints/test/sync_integrity/no_sync_conflict_navigation_outside_debug_owners_test.dart`
  - root `dart run custom_lint`: green
- Honest remaining gap from this slice:
  - this improves honesty and containment of merge outcomes
  - it does not create a full field-level merge editor
  - next product-facing work should classify sync report categories so those
    help/support submissions are actually actionable

### 2026-04-08 22:44 ET

- Saved the latest device-testing notes into a dedicated implementation spec:
  - `.codex/plans/2026-04-08-beta-testing-notes-spec.md`
- That spec is now the source of truth for the next non-sync beta wave:
  - state ownership after mutation
  - entry-flow honesty and date handling
  - responsive/dialog contract cleanup
  - forms preload and gallery truthfulness
  - 0582B domain/export correctness
  - trash/account scoping
  - resume/restoration stability
- Important classification from the audit:
  - some user notes are already partially fixed in source and now need device
    verification rather than another code rewrite
  - the remaining highest-leverage open issues are:
    - activities save not rendering immediately
    - wide dashboard duplicate side panel
    - forms preload honesty
    - 0582B export/domain correctness
    - trash cross-account leakage
    - resume/back-stack edge cases
- Immediate next implementation slice from the spec:
  - fix activities state-ownership rendering
  - remove duplicate wide dashboard content
  - add targeted tests for both before moving deeper into forms/0582B

### 2026-04-08 23:08 ET

- Completed the first implementation wave from
  `.codex/plans/2026-04-08-beta-testing-notes-spec.md`.
- Landed:
  - `lib/features/entries/presentation/widgets/entry_activities_section.dart`
    now renders saved activities from the live controller snapshot first, so
    the section no longer falls back to stale `DailyEntry` widget data
    immediately after tapping `Done`
  - `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`
    no longer renders the temporary duplicate large-screen side panel
  - new regression test:
    - `test/features/entries/presentation/widgets/entry_activities_section_test.dart`
- Continued directly into the forms preload wave:
  - `lib/features/forms/presentation/screens/form_gallery_screen.dart` now:
    - blocks the create action until builtin forms are ready
    - shows a real loading state while builtin forms are loading
    - shows an honest retryable empty-preload state when forms are not ready
    - closes the add-form sheet via the sheet context instead of the parent
      screen context
  - updated tests:
    - `test/features/forms/presentation/screens/form_gallery_screen_test.dart`
- Verification for this wave:
  - `flutter test`
    - `test/features/entries/presentation/widgets/entry_activities_section_test.dart`
    - `test/features/forms/presentation/screens/form_gallery_screen_test.dart`
  - targeted `flutter analyze` on touched files: green
  - root `dart run custom_lint`: green
- Honest remaining gaps after this wave:
  - project delete still needs explicit fresh-build/device verification against
    the latest source
  - the 0582B correctness/export cluster is still open and is likely the next
    highest-value product wave
  - trash/account scoping and resume/back-stack recovery are still open

### 2026-04-08 23:18 ET

- Moved one more item from the 0582B/export cluster:
  - `lib/features/forms/domain/usecases/export_form_use_case.dart`
    no longer blocks export on `validateForExport()`
- Product effect:
  - incomplete 0582B forms can now still generate/export a PDF from the hub
    flow instead of failing before PDF generation
  - this aligns the code with the stated product contract that exports remain
    editable artifacts and should not be blocked by missing required fields
- Verification:
  - updated `test/features/forms/domain/usecases/export_form_use_case_test.dart`
  - reran:
    - `flutter test`
      - `test/features/forms/domain/usecases/export_form_use_case_test.dart`
      - `test/features/forms/presentation/screens/form_gallery_screen_test.dart`
      - `test/features/entries/presentation/widgets/entry_activities_section_test.dart`
    - targeted `flutter analyze`
    - root `dart run custom_lint`
- Honest remaining nuance:
  - the generic `markAsExported()` repository path still validates export
    completeness
  - that is separate from the 0582B hub export blocker that the user reported
    and should only be changed if we intentionally want the same policy in the
    generic form-viewer flow

### 2026-04-08 23:59 ET

- Completed the next 0582B/forms-gallery wave from
  `.codex/plans/2026-04-08-beta-testing-notes-spec.md`.
- Landed a real 0582B item-of-work catalog based on page 2 of the shipped PDF:
  - `lib/features/forms/data/registries/mdot_0582b_item_of_work_catalog.dart`
- Added shared 0582B formatting helpers and applied them across the hub,
  viewer, entry-card, and PDF export paths:
  - one-decimal display
  - `xx+xx` station formatting
  - station input formatter
- Fixed the quick-test domain drift:
  - removed fake `Mainline / Shoulder / Other` options
  - dropdown now uses the shipped catalog
  - requirement copy now shows the actual item description, minimum compaction,
    export code, and spec section
- Fixed stale saved responses in Forms Gallery after returning from a form:
  - both opening an existing saved response and creating a new response now
    reload the gallery document list for the active project
- Added new architecture lint:
  - `no_raw_0582b_item_of_work_options`
  - scope intentionally narrowed to the forms feature so generic `"Other"`
    buckets elsewhere are not falsely flagged
- Also closed the generic exported-form lock mismatch:
  - exported forms now remain editable
  - already-exported responses can be exported again
  - `markAsExported()` no longer acts like an export-field validation gate
    after PDF generation succeeds
- Verification:
  - targeted `flutter analyze`: green
  - targeted `flutter test`: green
  - new lint test: green
  - root `dart run custom_lint`: green
- Honest remaining 0582B/forms gaps after this slice:
  - original/recheck numbering logic still needs a dedicated pass
  - export destination UX still needs:
    - dated-folder support
    - attach-vs-export decision
    - multiple-bottom-sheet cleanup

### 2026-04-09 00:34 ET

- New concrete form-entry standardization finding from the 1126 audit:
  - the MDOT 1126 wizard has a split header source-of-truth
  - new/carry-forward 1126 drafts seed header values into `FormResponse.headerData`
  - but `Mdot1126HeaderStep` renders from `responseData['header']`
  - and `_patchHeader()` in `mdot_1126_form_screen.dart` writes edits back into
    `responseData['header']`
- Product effect:
  - first-open 1126 headers can look blank even when the draft already has
    known header values
  - the wizard is violating the same state-ownership rule we are trying to
    enforce elsewhere: one canonical provider/model source per screen
  - header autofill for builtin forms is still inconsistent instead of routing
    through one standardized known-data preload contract
- New concrete pay-app export finding from the workbook audit:
  - current pay-app export still behaves like a single saved `.xlsx` artifact
    per pay app
  - the post-export dialog only offers one-off file actions (`Save Copy`,
    `Share File`)
  - there is no project-workbook flow that accumulates the project's pay apps
    into one inspector-facing workbook export
- Direction locked for the next implementation slice:
  - make `FormResponse.headerData` the canonical 1126 header store and migrate
    any legacy nested `responseData['header']` data forward on load/edit
  - add shared builtin-form header autofill helpers so 1126 stops falling back
    to manual inspector re-entry for already-known project/profile data
  - add a project-workbook export path for pay apps instead of only exporting
    a one-off workbook artifact

### 2026-04-09 06:04 ET

- Completed the next forms/pay-app standardization slice.
- MDOT 1126 / SESC header ownership is now formalized:
  - added `FormHeaderOwnershipService`
  - `Mdot1126FormScreen` now normalizes legacy nested header payloads into
    canonical `FormResponse.headerData` on load
  - `Mdot1126HeaderStep` now renders only from `parsedHeaderData`
- Added enforcement so the old nested-header pattern does not creep back in:
  - new architecture lint:
    `no_nested_form_header_access_outside_header_owners`
  - approved fallback owners are intentionally narrow:
    - `form_header_ownership_service.dart`
    - `mdot_1126_pdf_filler.dart`
- Pay-app export now maintains a real per-project workbook in app storage:
  - added `ProjectPayAppWorkbookFileService`
  - added `RebuildProjectPayAppWorkbookUseCase`
  - every successful pay-app export now refreshes the canonical project workbook
    under a stable local path before the post-export dialog is shown
  - `Save Project Workbook` now writes a copy of that maintained project
    workbook instead of rebuilding an ad hoc one-off byte stream only at the
    last button tap
- Why this matters:
  - SESC header preload now follows the same canonical ownership contract we
    want across builtin forms
  - pay-app export is closer to the intended “single workbook per project that
    keeps accumulating pay apps” workflow instead of only a set of isolated
    snapshot files
- Verification:
  - `flutter analyze` on touched forms/pay-app/test files: green
  - `flutter test`
    - `test/features/forms/services/auto_fill_service_test.dart`
    - `test/features/forms/services/form_header_ownership_service_test.dart`
    - `test/features/forms/presentation/widgets/header_step_test.dart`
    - `test/features/pay_applications/data/services/pay_app_project_workbook_builder_test.dart`
    - `test/features/pay_applications/domain/usecases/rebuild_project_pay_app_workbook_use_case_test.dart`
    - `test/features/quantities/presentation/screens/quantities_screen_export_flow_test.dart`
    - `test/features/quantities/presentation/screens/quantities_screen_pay_app_export_flow_test.dart`
    - `test/features/quantities/presentation/screens/quantities_screen_test.dart`
  - `dart test`
    - `fg_lint_packages/field_guide_lints/test/architecture/no_nested_form_header_access_outside_header_owners_test.dart`
  - root `dart run custom_lint`: green
- Honest remaining gaps after this slice:
  - MDOT 1126 still needs broader end-to-end hardening beyond header preload:
    carry-forward UX, attachment/export/device validation, and any remaining
    wizard friction
  - the project workbook is now maintained locally, but on-device/manual
    validation of the updated pay-app export workflow is still pending
  - the broader beta spec backlog remains open beyond this focused slice

### 2026-04-09 06:28 ET On-Device Validation Pass

- Continued live validation on the S21 (`RFCNC0Y975L`) against the current
  driver build using the saved beta spec as the checklist.
- Saved device artifacts:
  - `.codex/tmp/s21-1126-saved-response-open.png`
  - `.codex/tmp/s21-0582b-saved-response-open.png`
  - `.codex/tmp/s21-pay-app-export-finished.png`
  - `.codex/tmp/s21-pay-app-save-workbook-system-picker.png`
  - `.codex/tmp/s21-calendar-screen.png`
  - `.codex/tmp/s21-calendar-entry-open.png`
  - `.codex/tmp/s21-activities-after-save.png`
  - `.codex/tmp/s21-continue-today-reopen.png`

- Confirmed fixed on-device:
  - dashboard hydration is still good:
    - Springfield loads with `131` pay items instead of the old stale `0`
      state
  - activities state ownership is fixed:
    - after entering `Placed erosion controls and verified traffic setup.`
      the read-only `Activities` section immediately rendered the saved text
      with no manual refresh
  - continue-today honesty is fixed:
    - dashboard shows `Continue Today's Entry`
    - reopening it returns to the existing draft
    - the editor title remains the real date (`Apr 9, 2026`), not `New Entry`
  - calendar backdate behavior still works functionally:
    - selecting `2026-04-08` surfaces prior entry cards
    - tapping a prior-day entry reopens that entry successfully
  - pay-app export flow is materially improved on-device:
    - `Pay Application Range` dialog opens
    - `No Tracked Entries` warning opens
    - `Pay Application Number` confirmation opens
    - export completes and shows the new dialog with:
      - `Save Project Workbook`
      - `Share File`
    - `Save Project Workbook` hands off into Android DocumentsUI instead of
      failing silently

- Confirmed still failing on-device:
  - calendar overflow is still real:
    - live screen shows `BOTTOM OVERFLOWED BY 154 PIXELS`
  - MDOT 1126 / SESC header preload is only partially fixed:
    - saved-response open now shows:
      - project name populated
      - contractor name populated
      - inspector name populated
    - but `Permit number` and `Location` were still blank on-device
  - forms gallery create flow is not honestly closed:
    - saved responses are present
    - add-form sheet now renders real options plus visible `Scroll for more`
      affordance
    - but selecting `MDOT 1126 Weekly SESC` from that sheet dismissed the
      sheet and left the app on `/forms` instead of clearly opening a create
      flow
    - this needs follow-up before claiming the forms `+` path is fixed
  - conflict viewer UX remains too weak for grouped conflicts:
    - grouped rows load
    - but cards still look too generic on-device (`form responses`) to be
      useful for support/debugging

- New high-priority on-device restoration finding:
  - after using the pay-app `Save Project Workbook` path and relaunching from
    the Android picker, the app resumed into an orphaned `Pay Items` screen
    with `0 items`
  - in that bad state:
    - visible UI stayed on `Pay Items`
    - driver route state drifted (`/quantities` and later `/projects`)
      without matching the visible screen
    - Android back surfaced the underlying DocumentsUI picker again instead of
      returning to a valid app root
  - a full force-stop + relaunch recovered correctly to `Projects`, so cold
    start is fine; the broken behavior is specifically the picker/resume
    restoration path

- User-facing sync/status note from device:
  - after clean relaunch the project list showed the simple sync notice banner:
    `2 changes were kept automatically during sync. Review sync status if
    something looks wrong.`
  - this matches the intended simpler production-facing sync surface better
    than the older raw diagnostics view

- Honest next work after this device pass:
  - fix the Android picker/export resume restoration path and route/UI drift
  - fix calendar responsive overflow
  - finish the 1126 header preload closure (`Permit number`, `Location`)
  - re-verify the forms gallery `+` create path with a deterministic keyed
    target or fix the create action if it is truly dismissing without
    navigation

### 2026-04-09 07:12 ET Pre-Device Source Closure For Resume, Calendar, And Forms

[-] Close the last known source-side blockers before the next S21 pass
Implemented in source:
- restoration is now intentionally limited to root shell routes in
  `lib/core/router/app_router.dart`
- `QuantitiesScreen` now reloads project-scoped state when project selection is
  restored after the first frame, which closes the previously observed
  `Pay Items / 0 items` orphan path in source
- compact calendar/day layout no longer relies on the old
  `Column + Expanded` composition that was producing the on-device overflow
- `FormGalleryScreen` now returns the selected form from the bottom sheet and
  routes `MDOT 1126` creation through the shared `form-new` path
- `MDOT 1126` header autofill now includes permit/location fallback chains

Verification completed before device reinstall:
- `flutter analyze` on the affected router/forms/quantities/calendar slice: green
- `flutter test`
  - `test/features/quantities/presentation/screens/quantities_screen_test.dart`
  - `test/features/forms/presentation/screens/form_gallery_screen_test.dart`
  - `test/core/router/app_router_test.dart`
- root `dart run custom_lint`: green

Still not honestly closed until the next S21 pass proves:
- Android picker resume returns to a valid app state
- calendar no longer overflows on-device
- Forms `+` -> `MDOT 1126` opens a real create flow on-device
- `MDOT 1126` permit/location header fields are populated on-device

### 2026-04-09 07:20 ET S21 Revalidation Results

[x] Revalidated successfully on device:
- calendar overflow no longer reproduces on the S21
- Forms `+` now opens a usable picker and `MDOT 1126 Weekly SESC` opens the
  create flow when the actual sheet item is tapped
- `MDOT 1126` header autofill now shows permit and location on the S21

[!] Picker/export resume remains partially broken:
- the worst old `Pay Items / 0 items` orphan state did not come back
- but launcher resume still left route/UI truth out of sync:
  - visible UI came back to dashboard
  - driver still reported `/quantities`
  - Android back resurfaced `DocumentsUI`

[-] Newly added product requirement from live validation:
- `MDOT 1126` needs preview/export parity with the other form surfaces
- source audit confirms `Mdot1126FormScreen` currently lacks the standard
  preview/export app-bar actions

### 2026-04-09 08:05 ET Follow-Up Device Closure: 1126 Parity And Picker Resume

[x] Closed in this pass:
- `MDOT 1126` now has preview/export parity with the other form surfaces
  - source:
    - `lib/features/forms/presentation/screens/mdot_1126_form_screen.dart`
  - regression coverage:
    - `test/features/forms/presentation/screens/mdot_1126_form_screen_test.dart`
  - device proof:
    - app bar now shows preview/export on the S21
    - preview opens the live 1126 PDF preview screen
- external-picker user-facing lockout path is closed with the
  `singleTask` activity-mode change
  - launcher relaunch no longer leaves `DocumentsUI` behind the app on back
  - back now returns from pay-app detail to `Pay Items`, not to the picker

[-] Residual follow-up, no longer a product blocker:
- driver route-reporting truth after launcher relaunch is still shallow
  - visible UI showed pay-app detail
  - `/driver/ready` still reported `/quantities`
  - this now looks like a driver diagnostics issue, not a production
    navigation/back-stack issue

### 2026-04-09 09:15 ET Audit Reconciliation: Remaining Unverified / Unclosed Work

- Added a dedicated post-audit closure backlog so the next iterations are driven
  by true remaining work, not by mixed fixed/open history scattered through the
  tracker.
- Remaining product work still open after reconciling the full testing-notes
  spec, tracker, and research inventory:
  - cross-account trash contamination and account-switch isolation
  - in-flow entry date editing / different-date report creation
  - 0582B original/recheck numbering logic
  - 0582B export UX:
    - dated-folder support
    - attach-vs-export decision
    - cleanup of the confusing multi-surface export path
  - broader 1126 / SESC wizard hardening beyond header preload and preview
  - grouped conflict viewer usefulness
  - support-facing sync issue taxonomy so user reports are actionable
- Source-landed items still needing honest closure proof:
  - project delete immediate refresh and selected-project fallback
  - Windows dashboard duplicate-panel removal on an actual Windows pass
  - generic form-viewer parity for incomplete 0582B export behavior if required
  - pay-app workbook accumulation over repeated exports
  - broader app-wide foreground resume slowness outside the fixed picker path
- Contract-test / verification backlog added from this reconciliation:
  - project delete without manual refresh
  - account-switch trash isolation
  - resume/back root-stack safety
  - driver route-reporting truth after launcher relaunch

### 2026-04-09 09:15 ET Lint Watchlist Added From The Audit

- Added explicit lint exploration items so we keep using architecture rules to
  prevent classes of bugs instead of only fixing instances.
- Candidate lint/restriction areas to evaluate next:
  - restrict ownership of restoration-sensitive external intent / picker launch
    flows
  - restrict stale screen-local read-only rendering when a live
    provider/controller source already exists
  - require destructive mutations to route through approved provider/reload
    owners
  - expand shared route-intent enforcement for continue/edit/open-submitted
    entry flows
  - enforce preload gating at the action-trigger layer so enabled actions do
    not open empty forms/sheets
- Explicit caution carried forward:
  - home/back lockout and resume correctness are not fully statically
    knowable problems
- any lint here must be paired with contract tests and device/runtime proof,
    not treated as sufficient on its own

### 2026-04-09 09:45 ET Next Enforcement + Closure Slice

- Added architecture lint:
  - `no_form_new_route_calls_outside_approved_owners`
  - rationale:
    - the Forms `+` / preload bug class had an honest static ownership signal
    - direct `form-new` route calls are now constrained to the approved creation
      owners instead of drifting into arbitrary screens
- Fixed a real remaining source gap in project deletion:
  - if the deleted project was selected, `ProjectProvider.deleteProject()` now
    repairs selection immediately to the next valid remaining project when
    possible
  - this closes part of the original stale-delete contract that had only been
    partially addressed before
- Added the missing submitted-entry contract test coverage:
  - `DashboardTodaysEntry` now has widget tests for:
    - prompt visibility
    - revert-to-draft path
    - open-submitted path
- Verification in this slice:
  - targeted `flutter test`: green
  - targeted `flutter analyze`: green
  - root `dart run custom_lint`: green
- Honest remaining status after this pass:
  - project delete still needs real on-device proof against the original manual
    refresh complaint
  - submitted-entry continue flow was source/test-closed at this point, but it
    was still awaiting explicit S21 proof before retirement from the live
    verification backlog

## 2026-04-09 09:26 ET S21 Validation: Submitted Entry Continue Flow Closed

- Revalidated the original dashboard complaint on-device instead of relying on
  source/tests alone.
- Live sequence:
  - selected Springfield from `Projects`
  - opened the existing Apr 9 draft from `1 Draft — Tap to Review`
  - marked it ready, submitted it, and returned to dashboard
  - confirmed dashboard state changed to `Today's Entry Submitted`
  - tapped the submitted card and exercised both decision branches
- Results:
  - `Open Submitted` opened the existing submitted report
  - `Revert to Draft` reopened the same entry in editable state and surfaced
    `Entry reverted to draft`
  - backing to dashboard restored the honest draft state:
    `1 Draft — Tap to Review` and `Continue Today's Entry`
- Proof artifacts:
  - `.codex/tmp/s21-after-submit-confirm.png`
  - `.codex/tmp/s21-submitted-entry-prompt.png`
  - `.codex/tmp/s21-open-submitted-branch.png`
  - `.codex/tmp/s21-revert-to-draft-branch.png`
  - `.codex/tmp/s21-dashboard-after-revert-back.png`
- Closure:
  - retire the submitted-entry prompt flow from the unverified backlog
  - the original behavior of silently starting a new entry for a submitted day
    is no longer reproducing on the S21

## 2026-04-09 09:52 ET S21 Validation: Equipment Manager Closed

- Closed the contractor equipment-manager path from the original user note.
- Source changes:
  - `EquipmentManagerDialog` no longer auto-focuses the name field when
    equipment already exists
  - helper copy now appears whenever more than one equipment item is present
  - the dialog body now constrains itself and scrolls under keyboard insets
    instead of overflowing
- Device proof on Springfield / Hoffman Brothers:
  - dialog opens with the keyboard closed so existing equipment is visible
    immediately
  - the scroll/discovery helper text is visible in the open state
  - tapping into `Equipment Name` no longer reproduces the yellow/black
    overflow stripe that previously appeared on the S21
- Proof artifacts:
  - `.codex/tmp/s21-equip-final-open.png`
  - `.codex/tmp/s21-equip-final-keyboard.png`
- Verification:
  - `flutter test test/features/entries/presentation/widgets/equipment_manager_dialog_test.dart`
  - `flutter analyze lib/features/entries/presentation/widgets/equipment_manager_dialog.dart test/features/entries/presentation/widgets/equipment_manager_dialog_test.dart`
  - root `dart run custom_lint`
- Honest note:
  - this closes the contractor equipment-manager flow that matched the user
    report
  - the separate standalone add/edit equipment dialogs remain a follow-up audit
    item if they need the exact same responsive contract

## 2026-04-09 10:05 ET Trash Scope Hardening

- Root-cause audit:
  - the repo-side `deleted_by = userId` filter is not the only problem
  - `TrashScreen` was loading once per mount and never reacting if the auth
    scope changed underneath the existing mounted screen
  - result:
    - prior-user grouped trash state could survive an account switch even if
      the repository query itself was scoped correctly
- Source fix landed:
  - `TrashScreen` now treats `userId + isAdmin` as a reload boundary
  - `TrashScreenController` gained `resetForScopeChange()`
  - on auth-scope change:
    - grouped items clear
    - loading state resets
    - filter/selection state clears
    - a new trash query runs for the new scope
  - `didChangeDependencies()` now actually subscribes to auth-scope changes
    instead of using `read()` only
- Contract coverage:
  - added widget test proving that switching from `user-test-1` to
    `user-test-2` on the same mounted `TrashScreen` replaces the visible trash
    rows instead of leaving the first user's items on screen
- Verification:
  - `flutter test test/features/settings/presentation/screens/trash_screen_test.dart`
  - `flutter analyze lib/features/settings/presentation/screens/trash_screen.dart lib/features/settings/presentation/controllers/trash_screen_controller.dart test/features/settings/presentation/screens/trash_screen_test.dart`
  - root `dart run custom_lint`
- Honest status:
  - source/test-closed for mounted-screen account switching
  - still needs real two-account device proof before A3 can be retired from
    the live product backlog

## 2026-04-09 Project Removal Semantics Audit

- Verified a second root cause in the project delete/remove-from-device stale
  state path:
  - the device-removal flow intentionally preserves the `projects` metadata row
    so the project can remain available for re-download
  - `FetchRemoteProjectsUseCase` was still loading `localProjects` from
    `ProjectRepository.getByCompanyId()`, which reads the metadata table only
  - result: a removed project still rendered as local/on-device even though its
    `synced_projects` enrollment row had been removed
- Fix landed:
  - added `getEnrolledByCompanyId()` to the project repository stack
  - implemented the local query as `projects INNER JOIN synced_projects`
  - switched `FetchRemoteProjectsUseCase` to define on-device/enrolled projects
    through that join instead of all metadata rows
- Verification after the source fix:
  - `flutter test test/features/projects/domain/use_cases/fetch_remote_projects_use_case_test.dart`
  - `flutter test test/features/projects/data/services/project_lifecycle_service_test.dart`
  - targeted `flutter analyze`
  - all green
- Honest status:
  - source semantics are now correct
  - 2026-04-09 S21 validation now closes the live flow:
    - delete sheet opens with scroll hint and a reachable confirm button
    - `Remove from device` runs on-device
    - `My Projects` updates immediately to the empty state without manual
      refresh
    - the app shows `Project removed from device`
  - 2026-04-09 follow-up validation also closes the cold-start persistence bug:
    - local removal was being undone on relaunch because assigned projects were
      being auto-enrolled again during startup sync
    - there were two distinct enrollment owners:
      - application `SyncEnrollmentService`
      - engine `EnrollmentHandler`
    - explicit local removal now persists a manual-removal marker in
      `sync_metadata`
    - explicit user download clears that marker
    - both enrollment owners now skip marked projects
    - fresh S21 relaunch proof:
      - `FetchRemoteProjectsUseCase: enrolled projects=0`
      - `available (unenrolled)=1`
      - UI stays on `No projects on your device`
    - explicit redownload is also validated:
      - `Company` tab shows Springfield as `Remote`
      - download confirmation opens
      - import runs and completes
      - project returns as `On Device`
### 2026-04-09 11:05 ET Forms/Export Closure Wave

- Closed the real remaining 0582B domain gap:
  - original/recheck numbering is now owned by
    `lib/features/forms/data/services/mdot_0582b_test_numbering_service.dart`
  - explicit failures keep the user on the same base test number as a recheck
  - passing rechecks reset the workflow back to the next chronological original
  - the hub now renders honest labels such as `Test #2 · Recheck #1`
- Verified the numbering fix on the S21:
  - failing original sent as `Test #2`
  - next screen state became `Test #2 · Recheck #1`
  - passing recheck reset to `Test #3`
- Revalidated forms/export paths on-device:
  - 1126 saved response opens with autofilled header values
  - 1126 preview renders the real PDF
  - 1126 export succeeds with `PDF exported`
  - 0582B export succeeds on-device even with an incomplete current draft
- Closed the pay-app workbook accumulation proof gap:
  - pulled the canonical workbook out of the app sandbox on the S21
  - confirmed sheet names:
    - `Pay App #1`
    - `Pay App #2`
    - `Pay App #3`
  - added source regression coverage in
    `test/features/pay_applications/domain/usecases/build_project_pay_app_workbook_use_case_test.dart`
- Honest forms/export backlog after this wave:
  - 0582B export destination UX still needs:
    - dated-folder support
    - attach-vs-export decision
    - export-flow cleanup
  - broader 1126 / SESC hardening is still open around:
    - carry-forward/week-over-week workflow
    - attach-step/create-entry behavior
    - reminder cadence/end-to-end proof
  - generic form-viewer export parity still needs an explicit product decision
    if “incomplete export allowed” must hold outside the hub/specialized shells

## 2026-04-09 11:30 ET Shared Form PDF Ownership + Device Revalidation

- Landed a reusable form PDF action owner at:
  - `lib/features/forms/presentation/support/form_pdf_action_owner.dart`
- Moved the current top-level form shells onto that shared owner:
  - `Mdot1126FormScreen`
  - `MdotHubScreen`
  - `FormViewerScreen`
- Added architecture lint:
  - `no_direct_form_pdf_actions_outside_owner`
  - intent:
    - new form screens must not hand-roll preview/export/share plumbing again
    - top-level form screens now have one approved PDF action seam
- Test/analysis verification is green:
  - shared-owner widget tests
  - 1126 screen tests
  - form-viewer controller tests
  - new lint test
  - targeted `flutter analyze`
  - root `dart run custom_lint`
- S21 proof on the fresh driver build:
  - 1126 still opens with preview/export actions visible
  - 1126 preview opens the real PDF preview shell
  - 1126 export reaches Android’s chooser with the generated PDF
  - 0582B preview opens the real PDF preview shell
  - 0582B export reaches Android’s chooser with the generated PDF
- Honest conclusion:
  - the shared form preview/export contract is now closed for the current forms
  - remaining forms work is no longer “make preview/export consistent”; it is
    now the next real product gaps:
    - generic attach-to-entry path for non-pay-app forms
    - generic form-viewer export policy
    - broader 1126 / SESC weekly workflow hardening

## 2026-04-09 11:45 ET Export Artifact Contract Direction

- Intent expanded:
  - export standardization is no longer forms-only
  - `entry` and `pay_app` are now explicitly part of the same export
    architecture
- durable plan created:
  - `.codex/plans/2026-04-09-export-artifact-contract-plan.md`
- first implementation slice queued:
  - add shared export capability registry for:
    - `form`
    - `entry`
    - `pay_app`
  - begin adopting that registry in the existing live export owners
- key product distinction preserved:
  - share preview/export plumbing where possible
  - keep attachment and bundle semantics capability-driven instead of forcing
    pay apps or entries into form-style attachment rules

## 2026-04-09 12:00 ET Export Capability Registry Landed

- Added shared export capability contract file:
  - `lib/core/exports/export_artifact_capability_registry.dart`
- Baseline artifact families are now explicit in source:
  - `form`
  - `entry`
  - `pay_app`
- Initial adoption landed in the current live owners:
  - `FormPdfActionOwner`
  - `EntryPdfPreviewScreen`
  - `showReportPdfActionsDialog`
  - `PayAppDetailFileOps`
  - `QuantitiesPayAppExporter`
- Added architecture lint:
  - `export_artifact_capability_registry_contract_sync`
- Verification is green:
  - registry unit test
  - shared form export owner test
  - new lint test
  - targeted `flutter analyze`
  - root `dart run custom_lint`
- Next export-contract slice:
  - extract the shared exported-file follow-up owner so pay apps and saved
    export history stop duplicating save/share file orchestration

## 2026-04-09 12:15 ET Exported-File Follow-Up Owner Landed

- Added shared owner:
  - `ExportArtifactFileActionOwner`
- Migrated onto the owner:
  - `PayAppDetailFileOps`
  - `SettingsSavedExportActions`
  - pay-app post-export follow-up in `QuantitiesPayAppExporter`
- Added lint:
  - `no_direct_export_artifact_file_service_usage_outside_owner`
- Verification is green:
  - new exported-file owner widget test
  - saved exports screen test still green
  - registry test still green
  - new lint test
  - targeted `flutter analyze`
  - root `dart run custom_lint`
- Honest next export gap:
  - entry export still has duplicate UI ownership between preview screen and
    older report dialog surfaces

## 2026-04-09 13:10 ET Canonical Pay-App Data + Local-Only Export History

- Product direction locked:
  - canonical pay-app business data must remain syncable/backed up
  - workbook/export history must remain local-only
  - export history should never poison the sync queue again
- Landed sync-surface split:
  - local-only export history tables now retire sync triggers and queue writes:
    - `entry_exports`
    - `form_exports`
    - `export_artifacts`
  - canonical `pay_applications` remains sync-backed
- Landed recovery/migration support:
  - runtime repair:
    - `RepairSyncStateV20260409LocalOnlyExportQueue`
  - DB upgrade:
    - `v57` removes legacy export-history triggers and purges queued residue
  - DB upgrade:
    - `v58` rebuilds `pay_applications` so `export_artifact_id` is optional
- Landed pay-app architecture split:
  - `pay_applications` is now canonical syncable data
  - `export_artifact_id` is optional local linkage metadata
  - adapter treats `export_artifact_id` as local-only:
    - stripped on push
    - ignored on pull
  - detail/workbook lookup now falls back by `source_record_id`
  - deleting an export artifact no longer deletes canonical pay-app data
  - deleting a pay app is now its own explicit use case
- Verification already green in source:
  - targeted migration tests
  - targeted sync schema/adapter/repair tests
  - targeted pay-app use-case/detail-screen tests
  - targeted `flutter analyze`
  - root `dart run custom_lint`
- Live S21 upgrade proof already captured:
  - `pay_applications.export_artifact_id` is nullable on-device
  - no triggers remain on `entry_exports`, `form_exports`, or
    `export_artifacts`
  - `pay_applications` still has sync triggers
  - queue was clean after upgrade
- Honest remaining gap:
  - still need a fresh on-device pay-app creation/export/sync cycle proving:
    - newly created pay apps enqueue only canonical `pay_applications`
    - workbook/export history stays out of `change_log`
    - sync drains the canonical pay-app row cleanly with no blocked residue

## 2026-04-09 13:35 ET Pay-App E2E Validation + Quarantine Follow-Up

- On-device export validation is now closed for queue ownership:
  - created a real `Pay App #4` on the S21 through the live export dialogs
  - confirmed only `pay_applications/<id>` entered `change_log`
  - confirmed `export_artifacts`, `form_exports`, and `entry_exports` stayed
    out of the queue
  - confirmed the local artifact row still existed with a real local file path
- Real backend blocker discovered during sync:
  - remote sync failed with:
    - `23502 null value in column "export_artifact_id" of relation "pay_applications" violates not-null constraint`
  - direct remote schema probe confirmed:
    - `public.pay_applications.export_artifact_id` is still `NOT NULL`
- Landed containment so the device does not keep poisoning sync:
  - pay-app remote-schema mismatch is now detected explicitly in
    `PushErrorHandler`
  - the row is immediately moved to blocked queue state instead of burning
    retries
  - startup repair now quarantines already-poisoned pay-app rows into blocked
    state
- Reinstalled and validated on the S21:
  - previous poisoned pay-app row now shows:
    - `pendingCount = 0`
    - `blockedCount = 1`
  - running sync again does not retry it
  - blocked row remains with explicit remediation text
- Current honest status:
  - local architecture is correct
  - local queue protection is correct
  - remote migration is still missing
- External blocker:
  - could not apply the linked remote migration from this environment because
    `supabase db push` is blocked by history drift and `supabase db query --linked`
    requires `SUPABASE_DB_PASSWORD`, which is not present in the workspace

## 2026-04-09 14:05 ET Pay-App Sync Closure

- Remote migration is now applied on the linked Supabase project:
  - `public.pay_applications.export_artifact_id` is nullable
  - the export-artifact FK is restored with `ON DELETE SET NULL`
- Recovery path is now complete in source:
  - `Repair Sync State` requeues blocked pay-app schema-mismatch rows before
    rerunning the repair catalog
- Verified locally:
  - targeted sync recovery test green
  - targeted `flutter analyze` green
  - root `dart run custom_lint` green
- Verified on the S21:
  - pre-repair state: `0 pending / 1 blocked`
  - after `run-sync-repairs`: `1 pending / 0 blocked`
  - after sync: `0 pending / 0 blocked / 0 unprocessed`
  - remote `pay_applications/91571c6c-8f54-456e-89fd-9b0957480333` now exists
    with `application_number = 4` and `export_artifact_id = null`

Status change:
- pay-app export no longer poisons sync
- canonical pay-app sync plus local-only workbook/export history is now closed
  with live backend + S21 proof

## 2026-04-09 14:25 ET Entry Bundle Proof

- Added stable testing keys to the entry preview shell:
  - `report_pdf_preview_dialog`
  - `report_pdf_save_as_button`
  - `report_pdf_share_button`
- Added source coverage:
  - `test/features/entries/presentation/screens/entry_pdf_preview_screen_test.dart`
- Re-verified:
  - targeted entry preview/owner tests green
  - targeted `flutter analyze` green
  - root `dart run custom_lint` green
- Live S21 proof for the bundle side of generic form attachment:
  - the existing `mdot_1126` response is still attached to the Apr 9 draft
  - exporting that draft entry opens the keyed `Daily Entry Preview`
  - tapping save opens the folder-export dialog (`Export Folder Name`, `04-09`)
    instead of the standalone PDF save flow
  - screenshot saved at `.codex/tmp/entry-export-folder-dialog.png`

Status change:
- attached-form bundle export is now closed on-device
- the remaining attachment-related gap is the wizard-side
  attach-step/create-entry UI proof
## 2026-04-09 15:35 ET MDOT 1126 Attach And Reminder Workflow Closure

- MDOT 1126 now uses typed validated signature input instead of the drawn signature path
  - the original renderer crash was closed by replacing the fragile UI-image generation path with CPU-side PNG generation
  - the S21 sign flow is stable again
- the 1126 attach step is now honestly device-proven in both branches:
  - same-date branch:
    - on-device, a signed `2026-04-09` 1126 returns to the Apr 9 entry surface
  - no-match branch:
    - on-device, a signed `2026-04-11` 1126 shows explicit create-vs-override actions
    - creating the entry produces a new `daily_entries` row and navigates to `/entry/.../2026-04-11`
- the attach UI is safer now:
  - it no longer presents a live inline list of every existing entry by default
  - override selection goes through an explicit existing-entry picker
- weekly SESC reminder routing was dropping the due date on the floor
  - root cause:
    - `WeeklySescReminderBanner`, `WeeklySescToolboxTodo`, and the dashboard reminder slot all opened `form-new` without any due-date payload
    - `FormNewDispatcherScreen` therefore fell back to `DateTime.now()`
  - fixed:
    - reminder open actions now pass `inspectionDate=YYYY-MM-DD`
    - `FormNewDispatcherScreen` accepts and forwards that date into `createMdot1126Response`
  - S21 proof:
    - `/form/new/mdot_1126?inspectionDate=2026-04-15` opens the rainfall step seeded to `Apr 15, 2026`

Still open after this closure:
- broader 0582B export UX cleanup
- entry date editing in-flow
- cross-account trash device proof
- conflict viewer usefulness
- sync issue taxonomy / reporting

## 2026-04-09 15:58 ET Shared Form Export Contract Closure

- Closed the remaining form-export contract drift.
- Root cause:
  - `FormViewerController` still enforced the obsolete
    `preview -> submit -> mark exported` policy
  - `FormPdfActionOwner` only shared temp files, so forms did not inherit the
    save/share follow-up contract that entries and pay apps already used
- Fixed in source:
  - `lib/core/exports/export_save_share_dialog.dart`
  - `lib/core/exports/export_artifact_capability_registry.dart`
  - `lib/features/forms/domain/usecases/export_form_use_case.dart`
  - `lib/features/forms/data/services/form_pdf_service.dart`
  - `lib/features/forms/presentation/providers/form_export_provider.dart`
  - `lib/features/forms/presentation/support/form_pdf_action_owner.dart`
  - `lib/features/forms/presentation/controllers/form_viewer_controller.dart`
  - `lib/features/forms/presentation/screens/form_viewer_screen.dart`
- Resulting behavior:
  - form export no longer requires preview first
  - form export no longer submits the response
  - form export no longer marks the response exported
  - exported forms now open a shared `Form Exported` dialog with:
    - `Not Now`
    - `Save Copy`
    - `Share File`
- Verified on the S21:
  - generic fallback viewer export:
    `/form/fa74c344-0977-4b3a-9263-727796b6af41`
  - dedicated 0582B shell export:
    `/form/fa74c344-0977-4b3a-9263-727796b6af41?formType=mdot_0582b`
  - dedicated 1126 shell export:
    `/form/c1b792f9-1248-420f-a218-a029fce446de?formType=mdot_1126`
  - after export, both sampled rows still reported `status = open` in the
    device DB
- Proof artifacts:
  - `.codex/tmp/generic-form-viewer-export-dialog.png`
  - `.codex/tmp/mdot-0582b-live-export-dialog.png`
  - `.codex/tmp/mdot-1126-live-export-dialog.png`

## 2026-04-09 16:03 ET Save-Copy And 1126 Signature Identity Follow-Up

- Shared standalone form export is now proven past the dialog layer.
  - S21 proof:
    - from the generic 0582B viewer, `Save Copy` hands off to Android's system
      picker
    - proof artifact:
      `.codex/tmp/0582b-save-copy-picker-verified.png`
- Closed the 1126 signature-identity source gap.
  - root cause:
    - typed-signature validation was reading editable
      `headerData['inspector_name']`
    - carry-forward reused the prior inspector name, so a different inspector
      could inherit stale signer identity
    - when expected signer text was blank, any non-empty typed name passed
  - fixed in source:
    - `typed_signature_field.dart`
    - `sign_form_response_use_case.dart`
    - `build_carry_forward_1126_use_case.dart`
    - `mdot_1126_steps.dart`
  - resulting contract:
    - typed-signature validation now refuses to sign when no expected signer
      name exists
    - 1126 carry-forward no longer treats the prior inspector name as canonical
      for the next draft
    - accepted typed signer text is persisted with the form response alongside
      `signature_audit_id`
    - the 1126 signature step prefers the authenticated profile display name
      over editable header text
- S21 proof on fresh rebuild:
  - a new 1126 draft reaches signature with prompt text:
    `Type "E2E Test Admin" to sign this form.`
  - tapping `Sign` still advances to the attach step without crash/regression
  - proof artifacts:
    - `.codex/tmp/1126-signature-step-fresh-build.png`
    - `.codex/tmp/1126-post-sign-attach-fresh-build.png`

Still honestly open after this pass:
- 0582B export UX still lacks the dated-folder / attach-vs-export product
  decision closure
- cross-account trash device proof
- conflict viewer usefulness
- sync issue taxonomy / reporting

## 2026-04-09 16:40 ET Entry Date Editing Closure

- Root cause closed:
  - `EntryEditorScreen` reused stale mounted state across route-parameter
    changes because it only loaded entry data on first mount
- Landed:
  - `entry_editor_route_binding.dart`
  - `EntryEditorScreen.didUpdateWidget(...)` reload path
  - pending create-id regeneration for create-mode route hops
- Verified locally:
  - `flutter test test/features/entries/presentation/screens/entry_editor_route_binding_test.dart`
  - targeted `flutter analyze`
  - root `dart run custom_lint`
- Verified on the S21:
  - clean date-change branch now updates both route and visible header
  - collision -> `Open Existing Draft` now updates both route and visible
    header instead of leaving the stale previous entry rendered
- Proof artifacts:
  - `.codex/tmp/entry-date-edit-after-fix-clean-25.png`
  - `.codex/tmp/entry-date-edit-after-fix-open-existing.png`

Status change:
- remove entry date editing from the active open backlog

## 2026-04-09 16:55 ET 1126 Draft Dedupe + Forms Context Slice

- Closed:
  - same-date MDOT 1126 creation no longer mints duplicate drafts
  - shared form export filenames are now date-aware
  - Forms gallery now shows linked-vs-standalone context
  - Forms export history is now scoped to form PDFs only
- Landed:
  - `load_open_1126_draft_for_date_use_case.dart`
  - `form_export_filename_policy.dart`
  - reminder model/support updated to carry `resumeResponseId`
- Verified on the S21:
  - `/form/new/mdot_1126?inspectionDate=2026-04-15` reopened the same response
    id on the second invocation:
    - `ee145e67-a904-4a0d-ba23-068a6525d3bd`
  - 0582B export dialog now shows a date-aware filename:
    - `MDOT_0582B_2026-04-08_fa74c344.pdf`
  - Forms screen shows:
    - `Standalone`
    - `Linked to daily entry`
  - Forms export history visible rows are now only `Form PDFs`
- Proof artifacts:
  - `.codex/tmp/0582b-export-dialog-dated-filename.png`
  - `.codex/tmp/forms-gallery-linked-history-cleanup.png`
  - `.codex/tmp/forms-gallery-export-history-form-only-2.png`

Honest remaining gap from this slice:
- the reminder UI `resume draft` copy is source-landed, but I have not yet
  captured a live reminder-surface screenshot in the resume state

## 2026-04-09 16:58 ET Form Export And 1126 Attach Device Closure

- Closed on the S21:
  - 0582B attach-vs-export decision
  - 0582B save-before-export persistence
  - 1126 attach-step create-entry branch
  - 1126 attach-step existing-entry branch
  - standalone 1126 export blocking after a signed edit
- Landed:
  - `form_export_decision_dialog.dart`
  - `form_export_validation_policy.dart`
  - shared-owner updates in:
    - `FormPdfActionOwner`
    - `FormEntryAttachmentOwner`
    - `FormViewerScreen`
    - `MdotHubScreen`
  - prevention lint:
    - `no_signature_pad_field_usage`
- Verified locally:
  - targeted `flutter test`
  - targeted `flutter analyze`
  - root `dart run custom_lint`
- Verified on the S21:
  - 0582B now shows `Attach Before Export?` with:
    - `Export As Is`
    - `Attach and Export`
  - exporting as-is after editing `counts_mc` to `777` persisted that draft
    value into the live device DB without a manual save
  - choosing `Attach and Export`:
    - showed `Attached to the 2026-04-08 daily entry before export.`
    - updated the response row to a non-null `entry_id`
    - changed the Forms gallery subtitle to `Linked to daily entry`
  - `/form/new/mdot_1126?inspectionDate=2026-04-28`:
    - showed the typed signer prompt
    - reached attach with `Create new entry for 2026-04-28`
    - navigated into `/entry/.../2026-04-28`
  - `/form/new/mdot_1126?inspectionDate=2026-04-25`:
    - showed `2026-04-25 (matches inspection date)`
    - navigated into `/entry/.../2026-04-25`
  - editing signed 1126 `0c84aa6b-a660-4a73-902a-8b4779f79d5d` via the keyed
    date picker now blocks export with:
    - `Export blocked: measures, signature`
- Proof artifacts:
  - `.codex/tmp/0582b-attach-export-decision-3.png`
  - `.codex/tmp/0582b-after-attach-export.png`
  - `.codex/tmp/forms-gallery-0582b-linked-after-attach.png`
  - `.codex/tmp/1126-signature-step-typed.png`
  - `.codex/tmp/1126-attach-step-create-entry.png`
  - `.codex/tmp/1126-after-create-entry-attach.png`
  - `.codex/tmp/1126-existing-entry-attach-step.png`
  - `.codex/tmp/1126-existing-entry-after-attach.png`
  - `.codex/tmp/1126-export-blocked-after-edit.png`

Status change:
- remove `0582B attach-vs-export` from the open backlog
- remove `1126 attach-step/create-entry` from the open backlog

Still honestly open after this closure:
- standalone-form dated-folder behavior remains a product-policy question
- reminder-surface `resume draft` copy still needs direct device proof
- cross-account trash device proof
- conflict viewer usefulness
- sync issue taxonomy / reporting

## 2026-04-09 17:20 ET Sync Status False-Active Conflict Count

- New live S21 screenshot shows:
  - `34 changes need review`
  - `0 Pending`
  - `0 Blocked`
  - `34 Conflicts`
- This is **not** a fresh sync-engine conflict storm.
  - driver sync status at the same time:
    - `pendingCount=0`
    - `blockedCount=0`
    - `unprocessedCount=0`
  - latest on-device full sync log:
    - `conflicts=0`
- Read-only device DB proof:
  - `84` raw undismissed `conflict_log` rows
  - `34` grouped logical records
  - most are `winner = remote` historical rows for:
    - `form_responses`
    - `personnel_types`
- Root cause:
  - user-facing Sync Status is still surfacing grouped historical remote-win
    conflict history as active review work
  - sync hardening stopped queue poisoning, but did not yet contain historical
    conflict residue in the product surface
- Follow-up now added to active work:
  - only count actionable conflicts in user-facing status
  - auto-dismiss or downgrade stale remote-win history
  - preserve raw history for debug/support only
- Parallel investigation opened:
  - intermittent yellow full-screen border may be sizing or overlay related
  - fresh driver screenshot did not capture it, so that remains open

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

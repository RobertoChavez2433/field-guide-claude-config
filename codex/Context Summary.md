# Context Summary

## Project Snapshot

- App: Field Guide (`construction_inspector`) for construction inspectors
- Stack: Flutter, Provider, SQLite-first local storage, optional Supabase sync,
  Firebase on mobile
- Shape: `lib/core`, `lib/features`, `lib/services`, `lib/shared`,
  `lib/test_harness`

## Core Entry Points

- `lib/main.dart` wires startup, providers, database, auth, sync, and services.
- `lib/core/router/app_router.dart` owns route guards, onboarding redirects,
  password recovery trapping, and shell navigation.
- `lib/core/database/database_service.dart` owns SQLite connection lifecycle and
  delegates schema bootstrap and migrations to dedicated helpers.

## Current Active Context

- Latest session handoff source: `.claude/autoload/_state.md`
- Durable project patterns: `.claude/memory/MEMORY.md`
- Highest-priority active Codex tracker: `.codex/plans/2026-04-08-beta-central-tracker.md`
- Environment handoff state: Supabase CLI, remote project access, Docker/Desktop, and local Supabase stack validation are working; `supabase start`, `supabase status`, `supabase migration list --local`, and `supabase db reset` now succeed from repo state
- Current verified refactor state:
  - `driver_server.dart` is reduced to dispatch plus remaining diagnostics/admin seams; interaction/navigation now lives in `lib/core/driver/driver_interaction_handler.dart`
  - `driver_server.dart` now also delegates ready/find/tree/screenshot/hot-restart endpoints to `lib/core/driver/driver_shell_handler.dart`, leaving the server as a thin lifecycle/dispatch shell
  - `Logger` now keeps the public facade while file transport and HTTP transport live in `lib/core/logging/logger_file_transport.dart` and `lib/core/logging/logger_http_transport.dart`
  - `Logger.error()` now delegates the error-reporting/Sentry path into `lib/core/logging/logger_error_reporter.dart`
  - `Logger` now also delegates runtime hook wiring into `lib/core/logging/logger_runtime_hooks.dart`, leaving `logger.dart` as a 346 LOC facade instead of a runtime/transport/Sentry grab bag
  - direct Sentry capture ownership now lives in `lib/core/logging/logger_sentry_transport.dart`, while bug-report UI now routes through `lib/core/config/sentry_feedback_launcher.dart`
  - `no_direct_sentry_usage_outside_approved_owners` now lint-enforces that direct `sentry_flutter` imports stay inside `lib/main.dart`, `sentry_pii_filter.dart`, `sentry_feedback_launcher.dart`, and `logger_sentry_transport.dart`
  - `test/core/config/sentry_pii_filter_test.dart` now locks the live before-send privacy contract: consent gating, message/breadcrumb/exception scrubbing, and user/request stripping
  - `database_service.dart` no longer owns fresh-install bootstrap inline; that logic now lives in `lib/core/database/database_bootstrap.dart`
  - `database_service.dart` no longer owns the low-version upgrade chain inline; migrations `v2-v24` now live in `lib/core/database/database_upgrade_foundation.dart`
  - `database_service.dart` no longer owns the daily-entry workflow migration block inline; migrations `v25-v27` now live in `lib/core/database/database_upgrade_entry_workflows.dart`
  - `database_service.dart` no longer owns the sync-engine rebuild block inline; migrations `v28-v37` now live in `lib/core/database/database_upgrade_sync_engine.dart`
  - `database_service.dart` no longer owns the cleanup/stabilization migration block inline; migrations `v38-v42` now live in `lib/core/database/database_upgrade_stabilization.dart`
  - `database_service.dart` also no longer owns the late upgrade tail inline; migrations `v43-v56` now live in `lib/core/database/database_upgrade_repairs.dart`
  - `database_service.dart` is now a thin 185 LOC lifecycle/open/close facade with migration dispatch only
  - `test/core/database/migration_v42_test.dart` now guards the real pre-`v43` upgrade path against sync-table registry drift
  - `extraction_pipeline.dart` no longer owns the tabular extraction tail inline; that flow now lives in `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_tabular_runner.dart`
  - `extraction_pipeline.dart` no longer owns structure-detection staging inline; that flow now lives in `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_structure_runner.dart`
  - `extraction_pipeline.dart` no longer owns stage-trace/run-state/attempt scaffolding inline; that support now lives in `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_stage_runtime.dart`
  - `extraction_pipeline.dart` no longer owns the retry loop and per-attempt execution shell inline; that orchestration now lives in `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_attempt_runner.dart`
  - `extraction_pipeline.dart` no longer owns post-processing/quality-validation attempt lifecycle inline; that support now lives in `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_attempt_lifecycle.dart`
  - `extraction_pipeline.dart` no longer owns top-level extraction orchestration and stage-dispatch helpers inline; that seam now lives in `lib/features/pdf/services/extraction/pipeline/extraction_pipeline_facade.dart`
  - `extraction_pipeline.dart` is down to 276 LOC, with OCR, tabular, structure, runtime, attempt-runner, attempt-lifecycle, and facade seams extracted behind dedicated helpers
  - `soft_delete_service.dart` is down to 237 LOC; purge/delete-push support now lives in `lib/services/soft_delete_purge_support.dart`, restore orchestration now lives in `lib/services/soft_delete_restore_support.dart`, and storage-cleanup queue ownership now lives in `lib/services/soft_delete_storage_support.dart`
  - `realtime_hint_handler.dart` is down to 245 LOC; registration/deactivation RPCs, channel subscribe/refresh lifecycle, fallback polling, and transport-health publication now live in `lib/features/sync/application/realtime_hint_transport_controller.dart` (369 LOC)
  - sync-hint transport ownership is still lint-locked after that split: the approved owners are now `RealtimeHintHandler` plus `RealtimeHintTransportController`, not arbitrary callers
  - `project_lifecycle_service.dart` is down to 215 LOC; the destructive local device-eviction transaction now lives in `lib/features/sync/engine/project_local_eviction_executor.dart` (272 LOC)
  - the project-lifecycle split also tightened lint ownership: `change_log` mutation no longer needs to whitelist `ProjectLifecycleService`, and the new executor is now the approved hard-delete owner in the existing sync/data-safety rules
  - `form_pdf_service.dart` is down to 195 LOC; field matching, row mapping, checkbox parsing, summary fallback formatting, preview-cache ownership, template loading/caching, signature stamping, shared PDF output ownership, and rendering orchestration now live in dedicated helpers
  - `lib/features/forms/data/services/form_pdf_rendering_service.dart` now owns template loading, document opening/filling, registry filler application, debug rendering, and older-proctor remarks assembly
  - `lib/features/forms/data/services/form_pdf_signature_stamper.dart` now owns signature-field lookup and fallback stamping for signed 1126 exports
  - direct preview/share/temp-save ownership now lives in `lib/features/pdf/services/pdf_output_service.dart` (238 LOC), which is reused by both `form_pdf_service.dart` and `pdf_service.dart`
  - `form_viewer_screen.dart` and `mdot_hub_screen.dart` now route export sharing back through `FormPdfService` instead of calling `Printing.sharePdf` directly
  - `no_direct_printing_output_usage` now lint-enforces that `Printing.layoutPdf` / `Printing.sharePdf` stay in the approved output owner
  - `pdf_service.dart` is down to 91 LOC; entry export payload models now live in `lib/features/pdf/services/pdf_export_models.dart`, bundle file generation now lives in `lib/features/pdf/services/pdf_export_bundle_writer.dart`, and the shipped IDR template owner now lives in `lib/features/pdf/services/idr_pdf_template_writer.dart` (285 LOC)
  - `no_direct_idr_template_usage` now lint-enforces that direct `rootBundle.load('assets/templates/idr_template.pdf')` calls stay in `IdrPdfTemplateWriter`
  - form-PDF pure-logic tests now target the extracted production helper instead of a mirrored test-only copy
  - app-level i18n scaffolding is now live: `flutter_localizations`, `l10n.yaml`, `lib/l10n/app_en.arb`, generated `AppLocalizations`, and localized shell navigation labels are wired through `lib/core/app_widget.dart` and `lib/core/router/scaffold_with_nav_bar.dart`
  - Settings now has a project-scoped `Saved Exports` route (`/settings/saved-exports`) with reusable save-copy/share actions over the unified export artifact store; `SettingsSyncDataSection` exposes the new entry point
  - the last obviously mobile-first beta screens now reflow at wider breakpoints: `lib/features/settings/presentation/screens/settings_screen.dart`, `lib/features/forms/presentation/screens/form_gallery_screen.dart`, `lib/features/forms/presentation/screens/form_viewer_screen.dart`, and `lib/features/pay_applications/presentation/screens/pay_application_detail_screen.dart`
  - auth/onboarding now uses a shared responsive shell across `login_screen.dart`, `register_screen.dart`, `company_setup_screen.dart`, `profile_setup_screen.dart`, `forgot_password_screen.dart`, `otp_verification_screen.dart`, and `update_password_screen.dart`
  - field workflow responsive rollout is now in place for `lib/features/pay_applications/presentation/screens/contractor_comparison_screen.dart`, `lib/features/gallery/presentation/screens/gallery_screen.dart`, and `lib/features/contractors/presentation/screens/contractor_selection_screen.dart`; `MdotHubBodyContent` already provided the responsive body orchestration for `mdot_hub_screen.dart`
  - entries/review responsive rollout is now in place for `lib/features/entries/presentation/screens/drafts_list_screen.dart`, `lib/features/entries/presentation/screens/entry_review_screen.dart`, `lib/features/entries/presentation/screens/review_summary_screen.dart`, and `lib/features/entries/presentation/screens/entry_pdf_preview_screen.dart`; `EntryEditorBody` already provided the responsive body orchestration for `entry_editor_screen.dart`
  - support/admin/tools responsive rollout now covers `help_support_screen.dart`, `edit_profile_screen.dart`, `trash_screen.dart`, `consent_screen.dart`, `personnel_types_screen.dart`, `app_lock_settings_screen.dart`, `app_lock_unlock_screen.dart`, `admin_dashboard_screen.dart`, `sync_dashboard_screen.dart`, `conflict_viewer_screen.dart`, and `toolbox_home_screen.dart`
  - analytics and import-preview responsive rollout is now in place for `project_analytics_screen.dart`, `pdf_import_preview_screen.dart`, and `mp_import_preview_screen.dart`; calculator tabs were already responsive through `HmaCalculatorTab` and `ConcreteCalculatorTab`
  - export artifact history now treats `photo` and `photo_export` consistently in the shared history widget, closing the audit-discovered type drift on photo exports
  - responsive rollout for the audited top-level screens is now closed; future responsive work is maintenance-only as new screens are added or existing screens regress
  - contractor bulk import is now live through parser/service/provider/repository wiring plus project-contractors preview/apply UI
  - app lock is now live through settings with persisted PIN/biometric config, runtime gate enforcement in `AppWidget`, lifecycle auto-lock, and sync-startup suppression while locked
  - weather now has a durable offline cache path backed by `PreferencesService`, including fresh-cache hits, stale-cache fallback, and persisted refresh behavior
  - `daily_sync` hardening now exists on both client and server paths: the app coalesces broad pushes behind a persisted cooldown, and the edge function claims a server-side dispatch slot before FCM/realtime fan-out
  - rollback coverage is now enforced in CI through `scripts/check_changed_migration_rollbacks.py` plus `scripts/validate_migration_rollbacks.py`, both wired into `.github/workflows/quality-gate.yml`
  - local Supabase verification now includes `supabase db reset --local` applying `20260408173000_sync_push_rate_limit.sql` successfully
  - `flutter analyze`, `dart run custom_lint`, and the targeted contractor/app-lock/weather/sync-hardening plus earlier form-PDF/database/pipeline/PDF-output/soft-delete/realtime-hint/project-lifecycle/logging-Sentry/settings-export/responsive slices are clean after these changes
- Highest-priority upstream plan: `.claude/plans/2026-02-28-password-reset-token-hash-fix.md`
- Major open secondary plan: `.claude/plans/2026-02-22-testing-strategy-overhaul.md`

## Use This Directory To Stay Lean

- `.codex/PLAN.md` indexes active planning without loading all historical plans.
- `.codex/CLAUDE_CONTEXT_BRIDGE.md` maps the exact `.claude/` files to open for
  session handoff, feature context, agents, skills, and rules.

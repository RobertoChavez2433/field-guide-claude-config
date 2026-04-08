# Session State

**Last Updated**: 2026-04-07
**Branch**: `sync-engine-refactor`
**Status**: `sync-engine-refactor` has completed the sync release-proof sweep. The broad sync lints are active, the sync-hint ownership lints are active, and the remaining work is closeout or optional non-blocking harness cleanup rather than a pending live proof lane.

## Current State

- PR `#249` merged the UI design-system refactor, including the 300-line presentation ceiling enforced by `scripts/audit_ui_file_sizes.ps1`.
- Sync-driving UI now has explicit contracts through:
  - `lib/core/driver/screen_registry.dart`
  - `lib/core/driver/screen_contract_registry.dart`
  - `lib/core/driver/flow_registry.dart`
  - `lib/core/driver/driver_diagnostics_handler.dart`
- `/diagnostics/screen_contract` is the unified sync-facing UI inspection endpoint.
- Screen-local controller composition now lives in `di/*screen_providers.dart` files across auth, entries, forms, projects, quantities, settings, dashboard, pay applications, and similar refactored features.
- CI now enforces sync adapter drift with `scripts/validate_sync_adapter_registry.py` against `sync_engine_tables.dart`, `simple_adapters.dart`, and `sync_registry.dart`.
- The legacy `BaseRemoteDatasource` sync bypass has been removed; the remaining sync work is proof breadth, not major leftover executor cleanup.
- Foreground private-channel hints are now live-proven through the owned split:
  - `RealtimeHintHandler` owns subscribe / refresh / consume
  - `SyncHintRemoteEmitter` owns push-side `emit_sync_hint(...)`
  - `sync_hint_subscriptions` is the active-channel source of truth
- New custom lint now explicitly guards:
  - `push_handler_requires_sync_hint_emitter`
  - `no_sync_hint_rpc_outside_approved_owners`
  - `no_sync_hint_broadcast_subscription_outside_realtime_handler`
  - `no_client_sync_hint_broadcast_http`
- Current live proof checkpoint is `complete` after closing:
  - delete / restore / hard-delete / revocation
  - remove-from-device / fresh-pull parity
  - file-backed create/delete/cleanup
  - integrity / maintenance
  - support-ticket and consent live flows
  - retry/restart chaos matrix
  - quick-resume and realtime-hint mode proof
  - global full sync
  - dirty-scope isolation
  - private channel register/teardown
  - final mixed-flow soak

## Quality Gates

- `flutter analyze` must stay clean.
- `dart run custom_lint` must stay clean.
- `scripts/audit_ui_file_sizes.ps1` must stay green.
- `python scripts/validate_sync_adapter_registry.py` must stay green.
- No ignore comments, analyzer excludes, or severity downgrades are permitted to bypass the lint gates.

## New Architecture Enforcement

Custom lint now explicitly enforces:
- `max_ui_callable_length`
- `max_ui_file_length`
- `screen_registry_contract_sync`

Existing rules still enforce:
- single composition roots
- no business logic in DI
- no datasource imports in presentation
- design-system widget/token usage

Cross-file sync drift is now guarded in CI by:
- `scripts/validate_sync_adapter_registry.py`

## Resume Priorities

1. Burn down the broad sync-architecture lint backlog without narrowing the rules, starting with raw Supabase sync-table I/O still living in legacy remote datasources.
2. Keep driver registries, testing keys, screen contracts, and sync adapter validation aligned in the same change when UI/sync seams move.
3. Address only non-blocking harness follow-up if needed, such as the tiny-PNG `/driver/inject-photo-direct` 500, without weakening the sync architecture rules.

### Session 747 (2026-04-07, Codex)
**Work**: Merged the UI design-system refactor, closed the last UI issues, added structural sync adapter drift validation, and switched the workspace back to `sync-engine-refactor`.
**Decisions**: Treat GitHub issues as the defect system of record; do not use `.claude/defects`. Enforce sync adapter drift with a structural validator instead of count-based CI checks.
**Next**: Catch `sync-engine-refactor` up to the merged UI baseline, then continue the sync delete-orchestration split against the new UI orchestrator/provider/controller endpoints.

### Session 748 (2026-04-07, Codex)
**Work**: Locked in the broad sync ownership lints, added a pull-only local-write guard, repaired upgraded-install sync drift, and ran `custom_lint` to expose the remaining legacy Supabase sync access layer instead of hiding it.
**Decisions**: Keep `no_raw_supabase_sync_table_io_outside_supabase_sync` broad even if it surfaces many violations; treat the exposed remote datasource and shared datasource usage as real Phase 0 architecture debt before final release proof.
**Next**: Burn down the broad lint backlog starting with legacy remote datasources and `BaseRemoteDatasource`, then resume live proof at remove-from-device/fresh-pull parity using the phased plan.

### Session 749 (2026-04-07, Claude Opus 4.6)
**Work**: Implemented the full MDOT 1126 Weekly SESC Report plan via the implement skill (10 phases) using Agent-tool dispatch (no headless), with code-review + completeness reviewers only (no security per user request). Added signature_files / signature_audit_log SQLite v54 + Postgres migration, signatures feature module, sync adapters, 7 forms domain use cases, MDOT 1126 validator + PDF filler + registrations, full wizard presentation layer (controller, header step, rainfall, tri-state measures, drawn signature pad, attach), export-bundling block-on-unsigned, weekly reminder UI bindings, and Phase 10 sync registry + lint allowlist integration. Caught and fixed: HIGH SECURITY DEFINER search_path injection in Postgres trigger functions; CRITICAL WizardActivityTracker DI lookup that would have crashed every wizard launch; HIGH infinite refresh loop in SescReminderProvider (resolved/pending sets); two plan gaps (missing header step, missing GPS capture per SEC-1126-08) per user option C. Working tree on `sync-engine-refactor` was broken into 13 logical commits by layer (sync refactor / sync lint rules / project assignments / 10 MDOT 1126 phase commits) and pushed.
**Decisions**: Headless mode is too slow/lossy — use Agent tool for all dispatches per global feedback. Run review/fix sweeps from main conversation, not inside the orchestrator. Always verify agent "done" claims with direct grep before accepting. Mixed-DI files (app_dependencies.dart, app_providers.dart, sync_registry.dart, sync_engine_tables.dart, simple_adapters.dart, project_lifecycle_integration_test.dart) are committed in their MDOT 1126 phase commit with the message acknowledging they bundle concurrent-session refactor work — splitting hunks across commits would have required interactive `git add -p`. Header lives only in `FormResponse.headerData` (canonical 0582B pattern); date helpers consolidated in `lib/shared/utils/date_format.dart`. AppVersion sourced from `AppConfigProvider` with a drift test instead of hardcoding pubspec strings.
**Next**: Manual driver verification of the 1126 wizard end-to-end (first-week + carry-forward), weekly reminder visibility on dashboard/entry/toolbox, edit-after-sign export blocking, and daily export bundle (IDR + 1126 PDF + photos in one folder). Run `npx supabase db push` to land `20260408000000_signature_tables.sql` before any device test. Follow-ups documented in checkpoint: back-fill spec §2 audit table to mention `signature_png_sha256`, abstract `dart:io` out of `sign_form_response_use_case.dart` via a `SignatureFileStore` port, address pre-existing `lib/features/entries/data/datasources/remote/remote_datasources.dart` dangling export error, clean stale flusseract Windows ephemeral build cache so `dart run custom_lint` can run locally again. Phase 10 sync_registry/sync_engine_tables changes should also be smoke-tested for the auto-trigger generation path the implementer noted as a future hardening target.

### Session 750 (2026-04-07, Codex)
**Work**: Closed the foreground private-channel hint lane live, then locked the contract into docs and lint rules. Added `SyncHintRemoteEmitter` as the explicit push-side owner of `emit_sync_hint(...)`, simplified active-channel lookup to `sync_hint_subscriptions`, updated the `.claude` sync docs/state to match the shipped architecture, and added four sync-hint lint rules to stop future ownership drift.
**Decisions**: Foreground invalidation is now an owned contract, not a trigger side effect. `RealtimeHintHandler` is the only normal client subscriber, `SyncHintRemoteEmitter` is the only normal client emitter, and raw client `/realtime/v1/api/broadcast` use is forbidden.
**Next**: Resume live proof at `global-full-sync-proof`, followed by dirty-scope isolation, private channel register/teardown, and the final mixed-flow soak.

### Session 751 (2026-04-07, Codex)
**Work**: Completed the remaining live validation lanes on Windows + S21, including global full sync, dirty-scope isolation, private channel teardown/rebind, and the final mixed-flow soak. Fixed the last scoped-hint parsing gap by normalizing nested private-broadcast envelopes in `RealtimeHintHandler`, then proved the final release matrix end to end.
**Decisions**: The release-proof sweep is complete. Full sync remains the no-hint catch-up path, quick sync now respects strict dirty scopes from private broadcasts, `sync_hint_subscriptions` is confirmed as the private-channel lifecycle source of truth, and the broad sync lints stay in place with no narrowing.
**Next**: Close out artifacts, review any optional non-blocking harness cleanup, and keep future sync changes behind the existing ownership and hint-contract lint gates.

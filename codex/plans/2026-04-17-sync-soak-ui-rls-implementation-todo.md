# Sync Soak + UI/RLS Implementation TODO

Date: 2026-04-17
Branch: `gocr-integration`

Controlling specs:

- `.codex/plans/2026-04-17-enterprise-sync-soak-hardening-spec.md`
- `.codex/plans/2026-04-17-sync-hardening-ui-rls-closeout-todo-spec.md`

Companion implementation checkpoint log:

- `.codex/checkpoints/2026-04-17-sync-soak-implementation-checkpoints.md`

## Current Verdict

- [x] The clean `12k` local Docker run is now treated as backend/RLS evidence
  only, not device-sync proof.
- [x] Backend/RLS soak summaries now expose `soakLayer=backend_rls`.
- [x] Backend/RLS soak summaries now expose `syncEngineExercised=false`.
- [x] Device driver soak summaries now expose `soakLayer=device_sync`.
- [x] Device driver soak summaries now expose `syncEngineExercised=true`.
- [x] CI job and artifact labels now say backend/RLS soak instead of generic
  soak where GitHub is not running phones.
- [x] Driver `/driver/change-log` diagnostics now include grouped table,
  operation, retry, project id, error message, blocked, unprocessed, and
  max-retry counts.
- [x] A local device-lab runner now exists for S21/S10-style multi-driver UI
  sync evidence: `tools/enterprise-sync-soak-lab.ps1`.
- [x] One-user S21 sync drains to zero pending/blocked rows on the current
  build.
- [x] One-user S10 sync drains to zero pending/blocked rows on the current
  build.
- [x] Multi-device S21+S10 sync soak wrapper has real execution evidence.
- [x] The first blocked-row root causes are fixed: debug harness seed residue,
  fresh-backlog circuit-breaker deadlock, and previous-user consent RLS residue.

## Still Open

- [ ] true UI-driven mutations across daily entries, quantities, photos/files, forms, signatures;
- [ ] real role churn and same-device account switching sweeps;
- [ ] backend actors running concurrently with device actors;
- [ ] 10-20 users across 15 projects with weighted action mix and jitter;
- [ ] file/storage object proof;
- [ ] failure injection;
- [ ] staging/GitHub proof and repeated green soak history.

## Enterprise Sync Soak Hardening

### Phase 0 - Rename And Deconfuse Existing Soak

- [x] Add backend summary field `soakLayer=backend_rls`.
- [x] Add backend summary field `syncEngineExercised=false`.
- [x] Add device summary field `soakLayer=device_sync`.
- [x] Add device summary field `syncEngineExercised=true`.
- [x] Rename local backend/RLS summary files to
  `backend-rls-soak-*.json`.
- [x] Rename GitHub backend/RLS job labels and artifact names.
- [x] Keep backend/RLS soak in CI.
- [x] Update every docs reference that still says generic soak where it means
  backend/RLS soak.
- [x] Add a small workflow/doc note that GitHub backend/RLS soaks do not run
  S21/S10 device actors.

### Phase 1 - Device Actor Harness Foundation

- [x] Add a multi-driver lab runner accepting actor specs like
  `S21:4948:inspector:1` and `S10:4949:inspector:2`.
- [x] Capture per-device initial `/driver/change-log`.
- [x] Capture per-device initial `/diagnostics/sync_runtime`.
- [x] Capture per-device initial `/diagnostics/screen_contract`.
- [x] Capture per-device screenshots.
- [x] Capture per-round sync status before UI sync.
- [x] Capture per-round change-log before and after UI sync.
- [x] Capture per-round runtime diagnostics after UI sync.
- [x] Write a top-level `summary.json`.
- [x] Write per-device `timeline.json`.
- [x] Support ramp-up between device actors.
- [x] Preserve artifacts when an actor fails.
- [x] Add debug-log capture per actor.
- [x] Add current user id and current project id to the actor timeline once
  existing diagnostics expose them.
- [x] Run the lab runner against real S21 and S10 driver apps.
- [x] Store successful and failed sample artifacts under
  `.claude/test-results/<date>/enterprise-sync-soak/<run-id>/`.

### Phase 2 - Local App Change Generation

- [x] Preserve lower-level driver local mutation as
  `driver_local_mutation`, not full UI proof.
- [x] Add optional device-lab local mutation mode that asserts a local
  `change_log` row appears before UI sync.
- [x] Build true UI-driven daily-entry activity mutation.
- [x] Build true UI-driven quantity mutation.
- [ ] Build true UI-driven personnel/equipment/contractor mutation.
- [x] Build true UI-driven photo capture/import mutation with bytes.
- [ ] Build true UI-driven form/signature mutation.
- [ ] Assert every UI-driven mutation has the expected local record before
  sync.
- [x] Fail device soak if the matching local `change_log` row remains
  unprocessed after a successful sync.

### Phase 3 - Realistic Multi-Actor Workload

- [ ] Model named actors: admin, engineer, office technician, inspector A,
  inspector B, inspector C.
- [x] Support 2-4 device app actors plus 8-16 backend actors in one run.
- [x] Add a parent host-side concurrent wrapper that keeps backend/RLS and
  device-sync child summaries separate.
- [ ] Use the full 15-project fixture, not just projects 1-3.
- [ ] Expand the harness to 10-20 distinct active user accounts if the fixture
  still only has 12 real personas.
- [ ] Add weighted actions for quantities/pay items.
- [ ] Add weighted actions for forms/signatures.
- [ ] Add weighted actions for auth/session switching.
- [ ] Add field-like think time and jitter in both backend and device lanes.
- [ ] Add burst windows where actors edit the same project concurrently.
- [ ] Require convergence with no local queue residue.

### Phase 4 - Role And Scope Hardening

- [ ] Verify every role's visible project set before, during, and after sync.
- [ ] Add assignment revocation while a device is viewing the project list.
- [ ] Add assignment grant while another device is already open.
- [ ] Fail on unauthorized project flashes in project list.
- [ ] Fail on unauthorized project flashes in project selector.
- [ ] Fail on unauthorized project flashes in recent activity.
- [ ] Fail on unauthorized project flashes in sync dashboard.
- [ ] Fail on unauthorized project flashes in forms/photos/documents.
- [ ] Add same-device account switching: inspector -> admin.
- [ ] Add same-device account switching: admin -> inspector.
- [ ] Add same-device account switching: inspector A -> inspector B.
- [ ] Add logout/login after blocked queue state exists.
- [ ] Assert providers, selected project, caches, and synced scopes rebuild
  after user switch.

### Phase 5 - File And Storage Soak

- [ ] Add small, normal, large, and GPS-EXIF image fixtures.
- [ ] Create photo rows with real local `file_path`.
- [ ] Assert Supabase Storage upload occurs.
- [ ] Assert local `remote_path` is bookmarked.
- [ ] Assert another device downloads/previews the object.
- [ ] Assert Storage RLS blocks unauthorized role/project access.
- [ ] Assert EXIF GPS stripping where configured.
- [ ] Assert stale remote path replacement and cleanup.
- [ ] Assert `storage_cleanup_queue` for delete/restore/purge.
- [ ] Extend object proof to form exports, entry documents, entry exports,
  pay-app exports, and signatures.

### Phase 6 - Failure Injection

- [ ] Offline/online transition during queued local writes.
- [ ] Network drop during push.
- [ ] Network drop during pull.
- [ ] Timeout/socket failure during file upload.
- [ ] Auth expiration/refresh during sync.
- [ ] Supabase transient/rate-limit failure.
- [ ] App background/foreground during sync.
- [ ] App process restart mid-sync.
- [ ] Stale `sync_lock` setup and recovery assertion.
- [ ] SQLite busy/lock contention probe.
- [ ] Realtime hint burst while sync is already active.
- [ ] Dirty-scope overflow/degrade path.

### Phase 7 - Realtime And Dirty Scope Proof

- [ ] Bind realtime hints for each active company/device actor.
- [ ] Mutate project-scoped tables through backend actors while devices idle.
- [ ] Assert dirty scopes are marked on the correct devices.
- [ ] Assert quick sync runs or queues a follow-up while already syncing.
- [ ] Assert dirty scopes clear only after successful pull.
- [ ] Assert company mismatch hints are ignored.
- [ ] Assert assignment hints update the visible project set.
- [ ] Capture realtime client errors and backend logs.

### Phase 8 - Fixture Scale-Up

- [x] Existing closeout work expanded local fixture shape for p001-p003.
- [ ] Expand deterministic fixture to 15 projects with realistic records per
  project.
- [ ] Include old/new/deleted/restored/assigned/unassigned/reassigned projects.
- [ ] Include long notes and many rows per entry.
- [ ] Include binary files and export artifacts.
- [ ] Add fixture version/hash to every backend/RLS and device-sync artifact.

### Phase 9 - Observability And Failure Triage

- [x] Backend summaries include attempted, successful, failed, latency, worker,
  user, and action counts.
- [x] Device lab runner captures before/after queue state and screenshots.
- [x] `/driver/change-log` now returns grouped blocked/unprocessed counts by
  table, operation, retry count, project id, and error message for triage.
- [x] Add per-table sync health breakdown to soak summaries.
- [ ] Add backend log drain checks for postgres, auth, storage, realtime, and
  edge logs.
- [ ] Add Sentry event drain checks.
- [ ] Add storage object status into failure bundles.
- [ ] Add debug-log snippets into failure bundles.
- [ ] Add fail-fast for catastrophic failures while preserving final evidence.

### Phase 10 - CI And Local Lab Strategy

- [x] Backend/RLS soak remains in GitHub CI.
- [x] Staging backend/RLS soak remains in GitHub/manual workflows.
- [x] Device-sync lab runner is local-device only and does not pretend GitHub
  ran phones.
- [ ] Add a manual/nightly workflow placeholder that requires uploading or
  linking external S21/S10 lab artifacts.
- [ ] Require three consecutive backend/RLS staging soaks.
- [ ] Require three consecutive S21/S10 device-sync lab soaks.
- [ ] Require focused rerun for every sync bug fix.

### Phase 11 - Immediate Bug-Finding Queue

- [x] Add a runner capable of capturing S21/S10 current change-log and runtime
  state before UI sync.
- [x] Run current S21 blocked queue capture with the new grouped diagnostics.
- [x] Classify blocked rows by table, retry count, operation, project id, and
  error message.
- [x] Capture sync dashboard screenshot and repair state from S21.
- [x] Determine whether blocked rows are stale residue, schema/payload
  mismatch, RLS denial, storage path/object issue, local trigger/project-id
  bug, auth/session mismatch, or sync lock/gate issue.
- [x] Fix the one-user S21 failure.
- [x] Rerun S21 until pending, blocked, and unprocessed are zero.
- [x] Repeat on S10.
- [x] Run first S21+S10 device-lab wrapper after one-device green proof.

## Sync Hardening UI/RLS Closeout

### Staging + Fixture Proof

- [ ] Full staging fixture provisioning path with staging-only harness password.
- [ ] Staging admin sign-in proof.
- [ ] Staging inspector sign-in proof.
- [ ] Local reset proof after expanded fixture.
- [ ] Local sync matrix proof after expanded fixture.
- [ ] Local backend/RLS soak proof after expanded fixture.
- [ ] Local performance proof after expanded fixture.
- [ ] Update `scripts/perf_baseline.json` only after expanded fixture
  acceptance.
- [ ] Staging schema hash parity proof.
- [ ] Three green 10-minute staging backend/RLS soaks.
- [ ] Three green 15-minute staging nightly backend/RLS soaks.

### Role And Permission Boundary Repairs

- [ ] Real S21/S10 admin session rerun.
- [ ] Real S21/S10 inspector session rerun.
- [ ] Real S21/S10 engineer session rerun.
- [ ] Real S21/S10 office technician session rerun.
- [ ] Trash cross-role record isolation proof with real sessions.
- [ ] Engineer and office technician real credentials or staging harness
  personas without `MOCK_AUTH`.
- [ ] Denied route proof for project create/remove/archive/delete.
- [x] Route guards for PDF import preview and MP import preview use
  `canManageProjects`, matching the Quantities UI entrypoint.
- [x] Route guards for pay-app detail/compare use `canManageProjects`,
  matching the Quantities UI entrypoint.
- [ ] Real-device denied route proof for PDF import controls.
- [ ] Real-device denied route proof for pay-app management/detail/delete/compare.
- [x] Code-side Quantities screen gating for inspector PDF import/pay-app
  export entry points.
- [ ] Denied route proof for trash and admin routes.

### Sync State And Runtime Defect Repairs

- [x] Investigate S10 `pending/unprocessed ~1680`.
- [x] Investigate S21 pending/unprocessed counts with blocked rows.
- [x] Fix `change_log exceeds 1000` circuit-breaker state.
- [x] Fix harness/company mismatch for `harness-company-001`.
- [ ] Verify realtime subscription leak fix on devices.
- [ ] Reconcile Sync Dashboard UI with `/sync/status`.
- [ ] Investigate widget-tree locked runtime sync noise.
- [ ] Investigate signature integrity-drift counts.
- [ ] Investigate BaseListProvider daily-entry update failures.

### Navigation And UI Bug Closeout

- [ ] Broader stranded-route/back-shell sweep beyond review/draft routes.
- [ ] Projects -> Dashboard bottom-nav switch from `/projects`.
- [ ] Dashboard seeded-project state.
- [ ] Full project download/import graph assertion after sync.
- [ ] Entry PDF export failure.
- [ ] Pay App comparison XLSX path.
- [ ] Form viewer compact labels.
- [ ] Any still-reproing S21 overflow.
- [ ] Saved Exports tile/deep link proof.
- [ ] Admin Settings Trash tile proof.
- [ ] PDF import preview sentinel/import proof.

### External Phase 7 Release Gates

- [ ] Supabase Log Drains to Sentry proof.
- [ ] Sentry repository dispatch proof.
- [ ] Staging performance proof.
- [ ] Full test PR gate.
- [ ] Five ship-bar confirmations at one commit.
- [ ] Pre-alpha tag only after all layer-specific evidence is green.

## Review Gate

- [x] Run unit/widget/script tests touched by the enterprise soak changes.
- [x] Run a spec review against the enterprise sync soak hardening spec.
- [x] Run a spec review against the UI/RLS closeout spec.
- [x] Update this checklist with every result and artifact path.

Latest local verification:

- `dart analyze lib/core/driver/driver_diagnostics_handler.dart lib/core/driver/driver_server.dart test/core/driver/driver_diagnostics_routes_test.dart`
- `flutter test test/core/driver/driver_diagnostics_routes_test.dart`
- PowerShell parser check for `tools\enterprise-sync-soak-lab.ps1`
- PowerShell parser check for `tools\enterprise-sync-soak-lab.ps1` after
  adding `-UiMutationModes quantity`
- PowerShell parser check for `tools\enterprise-sync-concurrent-soak.ps1`
- `git diff --check` for the actor-context/device-lab/docs/checkpoint files
- `flutter test test/harness/soak_driver_test.dart test/harness/soak_driver_app_test.dart test/core/driver/driver_data_sync_handler_test.dart`
- `flutter test test/features/quantities/presentation/screens/quantities_screen_test.dart`
- `flutter test test/features/quantities/presentation/screens/quantities_screen_export_flow_test.dart test/features/quantities/presentation/screens/quantities_screen_pay_app_export_flow_test.dart`
- `dart analyze integration_test/sync/soak/soak_driver.dart integration_test/sync/soak/soak_metrics_collector.dart integration_test/sync/soak/soak_ci_10min_test.dart integration_test/sync/soak/soak_nightly_15min_test.dart integration_test/sync/harness/harness_driver_client.dart lib/core/driver/driver_data_sync_handler.dart lib/core/driver/driver_data_sync_handler_query_routes.dart lib/features/quantities/presentation/screens/quantities_screen.dart`
- `dart analyze ... lib/core/router/routes/pay_app_routes.dart lib/core/router/routes/form_routes.dart test/helpers/quantities_screen_export_flow_harness.dart`
- PowerShell parser checks for `tools/enterprise-sync-soak-lab.ps1` and
  `tools/measure-device-sync.ps1`
- GitHub workflow YAML parse for all `.github/workflows/*.yml`

Latest 2026-04-17 device evidence:

- S21 repaired stale harness residue via `/driver/run-sync-repairs`:
  `rowsAffected=20`, `pendingCount=0`, `blockedCount=0`.
- S10 repaired stale harness residue via `/driver/run-sync-repairs`:
  `rowsAffected=21`; remaining `1596` fresh pending rows exposed the old
  circuit-breaker design bug.
- S21 UI-triggered device sync passed:
  `.claude/test-results/2026-04-17/device-sync-measurements/S21-sync-20260417-150655.json`.
- S10 UI-triggered device sync passed:
  `.claude/test-results/2026-04-17/device-sync-measurements/S10-sync-20260417-150600.json`.
- S21+S10 device-lab wrapper passed:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-150725/summary.json`.
- The S10 failure immediately before the fix is preserved at
  `.claude/test-results/2026-04-17/device-sync-measurements/S10-sync-20260417-150308.json`;
  it narrowed the residue to two previous-user `user_consent_records`.

Latest 2026-04-17 code verification additions:

- `flutter test test/features/sync/application/sync_state_repair_runner_test.dart`
- `flutter test test/features/sync/engine/change_tracker_circuit_breaker_test.dart test/features/sync/engine/change_tracker_test.dart test/features/sync/engine/push_handler_test.dart test/features/sync/engine/sync_engine_status_test.dart test/core/driver/driver_data_sync_handler_test.dart`
- `flutter test test/features/sync/engine/push_handler_user_scoped_payload_test.dart`
- Targeted `dart analyze` for the touched sync engine, driver, repair, and
  test files.

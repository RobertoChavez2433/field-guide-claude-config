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
- [x] The S21 red-screen class exposed by the all-modes run has been isolated
  through focused state-machine flows. S21 `sync-only`, `daily-entry-only`,
  `quantity-only`, and `photo-only` are green in the refactored harness with
  strict log gates.
- [x] S10 stayed parked until the refactored S21 `combined` gate was
  implemented and green. The next device-sync gate is reintroducing S10 as a
  regression actor, not returning to legacy all-modes acceptance.
- [x] The refactored `combined` S21 flow is implemented and has accepted S21
  evidence. Do not use the legacy all-modes path as a substitute for future
  combined or regression proof.
- [x] S10 refactored regression is green for daily-entry, quantity, photo,
  contractor/personnel/equipment, and combined flows. Accepted combined
  artifact:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-combined-initial/summary.json`.
- [x] S21 `cleanup-only` live replay is green against accepted S21 combined and
  contractor ledgers:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-cleanup-only-replay-accepted-ledgers-idempotent/summary.json`.

## Still Open

- [ ] true UI-driven mutations across daily entries, quantities, photos/files,
  forms, and signatures;
  daily-entry, quantity, and photo paths are implemented and proven on S21 as
  isolated refactored state-machine gates and as the refactored S21
  `combined` gate. The contractor/personnel/equipment graph is also proven on
  S21 through `-Flow contractors-only`, S10 regression is green for the
  implemented flows, and the first form/signature/file-backed lane is proven
  through MDOT 1126 typed signature on S21, S21 cleanup-only replay, and S10.
  MDOT 1126 expanded fields/rows are also accepted on S21. The MDOT 0582B
  form-response mutation lane is accepted on S21; its export/storage proof
  remains open. MDOT 1174R is implemented/wired but not accepted; latest S21
  diagnostics are blocked on compact section/body proof while opening
  Quantities after QA edits.
  The remaining near-term form work is accepting MDOT 1174R, builtin form
  exports, saved-form/gallery lifecycle sweeps, and S10 regression for the
  newly accepted form lanes;
- [ ] real role churn and same-device account switching sweeps;
- [ ] backend/RLS virtual actors running concurrently with the limited
  real-device lane;
- [ ] 10-20 user workload across 15 projects with weighted action mix and
  jitter; this does not require 10-20 physical devices. Final app-user scale
  needs a headless app-sync actor lane with real sessions and isolated local
  stores before this can be called 10-20 app users. Backend actors remain
  RLS/remote-pressure evidence, not local app sync evidence;
- [x] S21 photo storage object proof for the implemented photo lane:
  three S21 `photo-only` runs proved storage download, ledger-owned row
  cleanup, storage delete, and storage absence.
- [x] Extend file/storage object proof to MDOT 1126 typed signatures:
  accepted S21/S10 MDOT runs prove signature storage download, ledger-owned
  cleanup, storage delete, and storage absence.
- [ ] Extend file/storage object proof to form exports, entry documents, entry
  exports, pay-app exports, cross-device download/preview, and additional
  signature/export paths;
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

- [x] Run the immediate hardening loop S21-only, one focused refactored flow at
  a time:
  - `-Flow sync-only`
  - `-Flow daily-entry-only`
  - `-Flow quantity-only`
  - `-Flow photo-only`
- [x] Implement and run the refactored S21 `combined` flow after the isolated
  gates, rather than falling back to legacy `-UiMutationModes`.
- [x] Preserve lower-level driver local mutation as
  `driver_local_mutation`, not full UI proof.
- [x] Add optional device-lab local mutation mode that asserts a local
  `change_log` row appears before UI sync.
- [x] Build true UI-driven daily-entry activity mutation.
- [x] Build true UI-driven quantity mutation.
- [x] Build true UI-driven personnel/equipment/contractor mutation.
  Accepted S21 artifact:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-contractors-fourth/summary.json`.
- [x] Build true UI-driven photo capture/import mutation with bytes.
- [x] Fix the report/photo runtime red screen exposed by the all-modes S21/S10
  soak for the focused S21 photo path. Root cause was the photo name dialog
  opening with autofocus immediately after the source/picker route transition.
- [x] Build true UI-driven MDOT 1126 typed-signature mutation with storage
  proof. Accepted S21 artifact:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-accepted-with-cleanup-sync-retry/summary.json`.
- [x] Build true UI-driven MDOT 1126 expanded field/row mutation proof.
  Accepted S21 artifact:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-signature-ready-or-nav/summary.json`.
- [x] Build true UI-driven MDOT 0582B form-response mutation proof.
  Accepted S21 artifact:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-accepted-initial/summary.json`.
- [ ] Build remaining true UI-driven form/signature mutations:
  MDOT 1174R is implemented/wired but not S21-accepted yet; latest diagnostics
  are blocked on compact section/body proof while opening Quantities after QA
  edits. Cleanup and final queue drain passed after the latest diagnostics.
  Current hardening moves the expanded-section sentinel onto the mounted body
  and makes driver text entry fail loudly on non-editable targets. Builtin
  form exports and saved-form/gallery lifecycle sweeps remain unimplemented.
- [ ] Assert every UI-driven mutation has the expected local record before
  sync. Implemented daily-entry, quantity, photo, contractor graph,
  MDOT 1126 typed-signature/expanded, and MDOT 0582B mutation flows already do
  this; keep this open for the remaining MDOT 1174R/export/gallery families.
- [x] Fail device soak if the matching local `change_log` row remains
  unprocessed after a successful sync.

### Phase 3 - Realistic Multi-Actor Workload

- [x] Keep Phase 3 blocked until S10 regression is green through the
  refactored path, with no Flutter red screens and no local queue residue.
  The refactored S21 `combined` prerequisite and S10 implemented-flow
  regression are now green.
- [ ] Model named actors: admin, engineer, office technician, inspector A,
  inspector B, inspector C.
- [x] Support 2-4 device app actors plus 8-16 backend actors in one run.
- [x] Add a parent host-side concurrent wrapper that keeps backend/RLS and
  device-sync child summaries separate. The wrapper now forwards `-Flow` to
  the device runner so future backend/device overlap can use the refactored
  `combined` path instead of legacy `-UiMutationModes`; real execution proof
  is still open.
- [ ] Use the full 15-project fixture, not just projects 1-3.
- [ ] Expand the harness to 10-20 distinct active user accounts if the fixture
  still only has 12 real personas.
- [ ] Add headless app-sync actors with isolated SQLite stores and real
  Supabase sessions before claiming 10-20 app users; the current backend actor
  lane remains RLS/remote-pressure evidence, not local app sync evidence.
- [ ] Keep physical device expectations to the actual lab: S21 primary, S10
  regression after S21 is clean, and at most an optional emulator if it is
  stable enough to add signal.
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
- [x] Create S21 photo rows with real local `file_path` in the implemented
  photo lane.
- [x] Assert Supabase Storage upload occurs for the implemented S21 photo lane.
- [x] Assert local `remote_path` is bookmarked for the implemented S21 photo
  lane.
- [ ] Assert another device downloads/previews the object.
- [ ] Assert Storage RLS blocks unauthorized role/project access.
- [ ] Assert EXIF GPS stripping where configured.
- [ ] Assert stale remote path replacement and cleanup.
- [ ] Assert `storage_cleanup_queue` for delete/restore/purge.
- [x] Extend object proof to MDOT 1126 typed-signature signatures.
- [ ] Extend object proof to form exports, entry documents, entry exports,
  pay-app exports, and additional signature/export paths.

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
- [x] Add strict device-log runtime scanning for Flutter/runtime failure
  signatures and fail the round when they appear.
- [x] Treat missing log capture as a `loggingGaps` pass/fail blocker for strict
  device-lab acceptance runs.
- [ ] Scan failure-capture logs in catch blocks with the same runtime scanner
  used for normal round logs.
- [ ] Deduplicate repeated Flutter runtime log signatures into a compact
  failure fingerprint.
- [ ] Add screenshot/widget-tree red-screen classification so visible red
  screens fail even when logcat misses the corresponding Flutter signature.
- [ ] Replace broad `driver_or_sync_error` classification with specific
  categories: `driver_preflight_failed`, `widget_wait_timeout`,
  `widget_tap_not_found`, `route_mismatch`, `picker_not_completed`,
  `runtime_log_error`, `logging_gap`, `cleanup_failed`, and
  `queue_residue_detected`.
- [ ] Add backend log drain checks for postgres, auth, storage, realtime, and
  edge logs.
- [ ] Add Sentry event drain checks.
- [ ] Add storage object status into failure bundles.
- [ ] Add debug-log snippets into failure bundles.
- [ ] Add fail-fast for catastrophic failures while preserving final evidence.
- [ ] A user-observed red screen can be tied to either a log signature,
  screenshot/widget-tree classification, or an explicit logging gap.
- [x] Implemented failed mutation runs record generated row IDs or original
  values, cleanup obligations, cleanup attempts, and cleanup outcome.
- [x] Extend mutation-ledger guarantees to `combined` by composing the
  ledger-owned daily-entry, quantity, and photo child phases.
- [x] Extend mutation-ledger guarantees to `cleanup-only` for the implemented
  daily-entry, quantity, and photo ledger families. It requires explicit
  ledger paths, copies source ledgers into the new artifact tree, and reuses
  ledger-owned cleanup helpers with UI-triggered sync.
- [x] Extend the same mutation-ledger guarantees to S10 regression for the
  implemented mutation flows.
- [x] Extend the same mutation-ledger guarantees to MDOT 1126 typed-signature
  form/signature flow, including `form_responses`, `signature_files`,
  `signature_audit_log`, signature storage download, cleanup sync, storage
  delete, and storage absence.
- [ ] Extend the same mutation-ledger guarantees to remaining mutation-family
  flows.

### Phase 9A - Device-Lab Harness Refactor

- [ ] Keep `tools/enterprise-sync-soak-lab.ps1` as a thin CLI wrapper.
  Refactored `-Flow sync-only`, `daily-entry-only`, `quantity-only`, and
  `photo-only` are wired through `tools/sync-soak/`; legacy mutation modes
  remain in the monolith and must not be used as the acceptance path.
- [x] Do not create a third HTTP server. Reuse the existing app-side
  `DriverServer` for UI/device control and the host-side `tools/debug-server`
  for structured logs, sync status, artifacts, and service-role verification
  utilities.
- [ ] Reuse `tools/start-driver.ps1` and `tools/wait-for-driver.ps1` for
  debug-server/app-driver startup and readiness checks instead of duplicating
  ADB port wiring in the soak wrapper.
- [x] Move actor parsing and summary models to a dedicated soak model module.
  First slice: `tools/sync-soak/SoakModels.ps1`.
- [x] Move driver HTTP calls to a dedicated driver client module.
  First slice: `tools/sync-soak/DriverClient.ps1`.
- [x] Move screenshot/logcat/JSON artifact handling to an artifact writer
  module.
- [x] Add a shared step runner used by every UI flow.
  First slice: `tools/sync-soak/StepRunner.ps1`; remaining legacy mutation
  flows still need to be migrated onto it.
- [x] Step runner must query both debug-server `/logs/errors` or
  `/logs/summary` and bounded ADB logcat for the operation window; missing
  either evidence channel is a visible logging gap.
- [x] Split implemented S21 UI flows into focused modules:
  - daily-entry activity,
  - quantity,
  - photo,
  - Sync Dashboard sync.
- [x] Add a dedicated `cleanup-only` module.
- [x] Add a dedicated `combined` module.
- [x] Add a mutation ledger for original values, generated IDs, remote paths,
  and cleanup status in the implemented daily-entry, quantity, and photo flows.
- [x] Reuse `tools/measure-device-sync.ps1` behavior for the Sync Dashboard
  flow: UI-trigger only, status polling, screenshots, no `POST /driver/sync`.
- [ ] Reuse `integration_test/sync/harness/harness_driver_client.dart`,
  `integration_test/sync/soak/soak_driver.dart`, and
  `integration_test/sync/soak/soak_metrics_collector.dart` semantics for typed
  driver calls, 15-project fixture metadata, action taxonomy, actor reports,
  and backend/device layer summaries.
- [ ] Treat direct driver mutation/file-injection endpoints as setup or
  recovery seams unless the flow first enters the real UI path; do not count
  direct endpoint mutations as UI mutation proof.
- [x] Add `sync-only`, `daily-entry-only`, `quantity-only`, `photo-only`, and
  `combined` modes so S21 can be hardened one flow at a time or as the
  accepted combined parent. These modes are implemented and proven on S21
  through the refactored path.
- [x] Add `cleanup-only`; it requires explicit `-CleanupLedgerPaths`, supports
  semicolon-delimited path lists for `pwsh -File`, replays only ledger-owned
  daily-entry/quantity/photo/contractor cleanup obligations, treats
  already-clean accepted ledgers as idempotent proof, and still fails closed
  instead of falling through to legacy all-modes behavior.
- [ ] Add harness self-tests for sample `FlutterError` log input, missing
  logcat capture, widget wait timeout bundles, cleanup failure, and direct
  `/driver/sync` recovery being labeled non-acceptance.
  First slice exists at `tools/test-sync-soak-harness.ps1` for runtime
  signatures, widget wait timeout classification, logging-gap classification,
  visible `ErrorWidget` classification, direct-sync non-acceptance labels,
  ordered mutation-ledger access, state sentinels, combined aggregation,
  cleanup-only ledger assignment/replay filtering, S10 gate catalog/run-guide,
  and specific cleanup-ledger/storage/change-log/unsupported-flow
  classifications.

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
- [x] Pause full all-modes device soaks until the S21-focused harness refactor
  and single-flow gates are complete.
- [x] Keep S10 parked until S21 sync-only, daily-entry-only, quantity-only, and
  photo-only flows are each green with cleanup proof.
- [x] Keep S10 parked until the refactored S21 `combined` flow is implemented
  and green.
- [x] Keep 15-20 user simulation parked until S21 combined
  daily-entry/quantity/photo is green under strict logs; when resumed, use
  headless app-sync actors plus backend/RLS virtual actors rather than assuming
  additional physical devices.
- [x] One real S21 can complete each implemented write flow independently with
  zero runtime log errors, zero logging gaps, zero queue residue, storage proof
  where applicable, and cleanup proof.
  Current progress: the non-mutating S21 `sync-only` gate passed three serial
  times through the refactored harness with zero runtime errors, zero logging
  gaps, and zero queue residue. S21 `daily-entry-only` passed three serial
  write-flow runs after the cleanup fix:
  `20260417-s21-refactor-daily-entry-only-serial-2b`,
  `20260417-s21-refactor-daily-entry-only-serial-3`, and
  `20260417-s21-refactor-daily-entry-only-serial-4`. The daily-entry cleanup
  proof now includes exact local and remote ledger-value sentinels. S21
  `quantity-only` and `photo-only` each have three accepted passes; all six
  quantity/photo summaries report `passed=true`, `runtimeErrors=0`,
  `loggingGaps=0`, `queueDrainResult=drained`, and no direct `/driver/sync`.
  Photo runs additionally prove storage download, storage delete, and storage
  absence. This closes the implemented S21 daily-entry, quantity, and photo
  write-flow gate. S21 `contractors-only` also passed at
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-contractors-fourth/summary.json`,
  including contractor, entry-contractor, default/custom personnel types,
  equipment, entry personnel count, entry equipment, cleanup sync, remote
  soft-delete proof, and final live S21 `/driver/change-log` empty. This does
  did not close the still-missing form/signature/file-backed families at that
  point. The refactored S21 `combined` gate also
  passed at
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-final/summary.json`
  with daily-entry, quantity, and photo child phases all green under strict
  logs and final live S21 `/driver/change-log` empty.
- S21 MDOT 1126 typed-signature now closes the first form/signature/file-backed
  write lane:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-accepted-with-cleanup-sync-retry/summary.json`.
  S21 cleanup-only replay of that accepted MDOT ledger and S10 MDOT regression
  are also green:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-cleanup-only-replay-accepted-ledger/summary.json`
  and
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot1126-signature-regression-with-cleanup-sync-retry/summary.json`.
  This did not close MDOT 1126 expanded fields/rows at that point; the expanded
  lane later passed on S21. MDOT 0582B form-response mutation later passed on
  S21. MDOT 1174R is now implemented/wired but not accepted; latest S21
  diagnostics are blocked on compact section/body proof while opening
  Quantities after QA edits, with cleanup and final queue drain proven.
  Builtin form exports,
  saved-form/gallery lifecycle sweeps, MDOT 0582B export/storage proof, and
  cross-device file-backed proof remain open.
- S10 refactored regression passed:
  - `20260418-s10-state-machine-daily-entry-only-initial`
  - `20260418-s10-state-machine-quantity-only-initial`
  - `20260418-s10-state-machine-photo-only-initial`
  - `20260418-s10-state-machine-contractors-only-initial`
  - `20260418-s10-state-machine-combined-initial`
  All report `passed=true`, zero runtime errors, zero logging gaps, drained
  queue, and `directDriverSyncEndpointUsed=false`.
- S21 cleanup-only replay passed at
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-cleanup-only-replay-accepted-ledgers-idempotent/summary.json`.
  It replays accepted S21 combined and contractor ledgers and ends with S21 and
  S10 live `/driver/change-log` empty.

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
- [x] Investigate signature integrity-drift counts. Latest MDOT runs accepted
  because per-ledger rows and storage objects proved correctly, but logs still
  showed broader `signature_files` / `signature_audit_log` count drift
  (`local=1`, `remote=25`). Root cause was a local/remote schema mismatch:
  local SQLite required `signature_files.local_path NOT NULL`, while Supabase
  allows null local paths for rows created on other devices. Local schema v61
  rebuilds `signature_files` with nullable `local_path`.
- [ ] Prove the signature integrity drift is gone on live S21/S10 after both
  devices upgrade to v61 and pull signature rows created by the other device.
  S21 post-v61 backlog drain is now artifact-backed at
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-post-v61-signature-backlog-sync-only/summary.json`;
  keep this open for S10 post-v61 cross-device proof.
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

- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`
- `flutter test test/features/sync/engine/supabase_sync_contract_test.dart test/features/sync/adapters/adapter_config_test.dart`
- `flutter test test/core/driver/driver_data_sync_policy_test.dart`
- `flutter test test/features/sync/engine/push_handler_test.dart test/features/sync/engine/sync_engine_delete_test.dart`
- S21 MDOT 1126 typed-signature:
  - `20260418-s21-mdot1126-signature-accepted-with-cleanup-sync-retry`
- S21 MDOT 1126 cleanup-only replay:
  - `20260418-s21-mdot1126-signature-cleanup-only-replay-accepted-ledger`
- S10 MDOT 1126 typed-signature regression:
  - `20260418-s10-mdot1126-signature-regression-with-cleanup-sync-retry`
- S21 post-v61 signature backlog sync-only:
  - `20260418-s21-post-v61-signature-backlog-sync-only`
- S21 MDOT 1126 expanded fields/rows:
  - `20260418-s21-mdot1126-expanded-after-signature-ready-or-nav`
    (`passed=true`, `failedActorRounds=0`, `runtimeErrors=0`,
    `loggingGaps=0`, `queueDrainResult=drained`, `blockedRowCount=0`,
    `unprocessedRowCount=0`, `maxRetryCount=0`,
    `directDriverSyncEndpointUsed=false`, final S21 queue empty).
  - Mutation sync was triggered through the Sync Dashboard UI and proved
    pre-sync `change_log` rows for `form_responses`, `signature_files`, and
    `signature_audit_log`.
  - The accepted ledger proves signature storage download, ledger-owned
    cleanup, storage delete, and storage absence.
  - Non-acceptance diagnostics are preserved in
    `20260418-s21-mdot1126-expanded-initial` and
    `20260418-s21-mdot1126-expanded-after-rainfall-ui`; both cleaned up through
    UI sync and ended with an empty S21 queue.
- S21 MDOT 0582B form-response mutation:
  - `20260418-s21-mdot0582b-accepted-initial`
    (`passed=true`, `failedActorRounds=0`, `runtimeErrors=0`,
    `loggingGaps=0`, `queueDrainResult=drained`, `blockedRowCount=0`,
    `unprocessedRowCount=0`, `maxRetryCount=0`,
    `directDriverSyncEndpointUsed=false`, final S21 queue empty).
  - Mutation sync was triggered through the Sync Dashboard UI and proved
    pre-sync `change_log` rows for `form_responses`.
  - The accepted ledger proves report-attached creation, header markers,
    chart/operating standards, HMA proctor row, quick-test row, post-sync
    remote `form_responses`, ledger-owned cleanup, UI-triggered cleanup sync,
    and remote soft-delete.
  - Non-acceptance diagnostics are preserved in
    `20260418-s21-mdot0582b-initial`,
    `20260418-s21-mdot0582b-after-test-section-fix`, and
    `20260418-s21-mdot0582b-after-remote-json-proof`; each cleaned up through
    UI sync and ended with an empty S21 queue.
- S21 MDOT 1174R implementation diagnostics:
  - `20260418-s21-mdot1174r-after-bidirectional-scroll` is non-acceptance
    evidence. It failed switching from Air/Slump to QA because
    `mdot1174_workflow_nav_qa` was not mounted while
    `mdot1174_section_header_qa` was present; cleanup passed and the final S21
    queue drained.
  - `20260418-s21-mdot1174r-after-expanded-sentinel` is still
    non-acceptance evidence. It progressed to QA/comments, then failed opening
    Quantities; cleanup passed, no runtime/logging gaps were captured, no
    direct `/driver/sync` was used, and the final S21 queue drained.
  - The current patch moves `mdot1174_section_expanded_*` proof from the
    chevron icon onto the mounted section body and makes `/driver/text` fail
    loudly when the key has no editable descendant. Live S21 acceptance
    remains open until a rerun proves local `change_log`, remote
    `form_responses`, ledger cleanup, zero runtime/logging gaps, and final
    empty queue.
  - `20260418-s21-mdot1174r-visible-text-only` is clean non-acceptance
    evidence: runtime/logging/queue/cleanup/direct-sync gates were clean, but
    `/driver/scroll-to-key` could not make the mounted Air/Slump composer field
    visible.
  - `20260418-s21-mdot1174r-after-ensure-visible-scroll` is the latest
    red-screen stop. It failed loudly with `runtime_log_error`,
    `runtimeErrors=27`, duplicate GlobalKey/detached render-object assertions,
    `queueDrainResult=residue_detected`, and local `form_responses` queue
    residue. `20260418-s21-mdot1174r-redscreen-residue-recovery-sync-only`
    recovered through UI-triggered `sync-only`, passed with zero runtime/logging
    gaps, drained the queue, and a live `/driver/change-log` check was empty.
    Do not retry 1174R until MDOT 1174R row-section key/state ownership is
    reviewed.
  - Artifact hygiene: `.claude/test-results/2026-04-18/enterprise-sync-soak`
    had 54 run folders, 3,676 files, and about 523 MB of generated evidence at
    this handoff. Keep raw artifacts only for accepted runs, the latest blocker,
    and one representative run per distinct failure class after summaries are
    recorded here.
- `dart analyze lib/features/photos/presentation/widgets/photo_name_dialog.dart lib/features/entries/presentation/widgets/entry_photos_section_actions.dart`
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`
- S21 refactored combined gate:
  - `20260418-s21-state-machine-combined-final`
- S21 refactored single-flow gates:
  - `20260418-s21-state-machine-sync-only-final-single-gate`
  - `20260418-s21-state-machine-daily-entry-final-single-gate`
  - `20260418-s21-state-machine-quantity-confidence-3`
  - `20260418-s21-state-machine-photo-confidence-3`
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

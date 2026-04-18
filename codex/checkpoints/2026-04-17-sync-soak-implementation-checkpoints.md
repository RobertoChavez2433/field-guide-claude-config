# Sync Soak Implementation Checkpoints

Date started: 2026-04-17
Branch: `gocr-integration`

Controlling verification gates:

- `.codex/plans/2026-04-17-enterprise-sync-soak-hardening-spec.md`
- `.codex/plans/2026-04-17-sync-hardening-ui-rls-closeout-todo-spec.md`
- `.codex/plans/2026-04-17-sync-soak-ui-rls-implementation-todo.md`

Purpose: keep append-only implementation notes separate from the to-do lists so
we can see what each slice found, what changed, what was verified, and what
must stay open until real S21/S10/staging/GitHub evidence exists.

## Standing Rules

- Do not mark any of the seven enterprise gates complete without real evidence.
- Backend/RLS soak is useful but still does not prove device sync.
- Device evidence must use real sessions, the app UI, local SQLite
  `change_log`, and Sync Dashboard-triggered sync. Do not use `MOCK_AUTH`.
- A green code path is not enough for ship-bar closure. The final gate is
  repeated device/staging/GitHub artifacts with screenshots, logs, queue state,
  storage proof, and role-boundary checks.

## 2026-04-17 - Baseline Before This Checkpoint Log

### What We Found

- The original high-action-count local soak was a backend/RLS stress test, not
  a device-sync test. It bypassed local SQLite, `SyncEngine`, storage bytes,
  app auth switching, and multi-device convergence.
- Real device failures existed even while backend/RLS soak was green:
  stale harness seed residue, fresh-backlog circuit breaker behavior, bounded
  full-sync push draining, and previous-user consent residue.
- The enterprise sync soak spec is still not complete.

### What We Did

- Split soak evidence into backend/RLS and device-sync layers.
- Added device-lab wrapper evidence for S21/S10 UI-triggered sync.
- Fixed the first one-user S21/S10 queue-drain failures.
- Added grouped change-log diagnostics, backend/RLS action taxonomy, fixture
  version/hash, actor reports, and burst-window fields.

### Evidence So Far

- S21 UI-triggered sync:
  `.claude/test-results/2026-04-17/device-sync-measurements/S21-sync-20260417-150655.json`
- S10 UI-triggered sync:
  `.claude/test-results/2026-04-17/device-sync-measurements/S10-sync-20260417-150600.json`
- S21+S10 device-lab wrapper:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-150725/summary.json`

### Keep Doing

- Expand from one-user sync proof to real UI-driven mutations, role churn,
  storage bytes, failure injection, backend/device concurrency, and repeated
  staging/GitHub evidence.

## 2026-04-17 - Actor Context, Storage/Fault Hooks, First UI Mutation

### What We Found

- Device-lab timelines needed to prove which authenticated user and selected
  project were active for each actor. Without that, S21/S10 artifacts could
  show queue state but not enough session context.
- File/storage and failure-injection proof needed host-side wiring before the
  S21/S10 lab can collect realistic evidence.
- The first low-risk true UI mutation seam is daily-entry activities because it
  uses existing report routes, existing `TestingKeys`, real text entry, and the
  production save path.

### What We Did

- Added read-only `/diagnostics/actor_context` to expose:
  current route, `canPop`, bottom-nav presence, authenticated user id,
  selected project id/name, project counts, and assignment-loaded state.
- Wired `tools/enterprise-sync-soak-lab.ps1` to capture actor context before,
  during, and after actor runs.
- Added per-table final queue health into the device-lab summary.
- Added optional `-StorageProofManifest` support for real Supabase Storage
  object download/hash/min-byte proof.
- Added optional host-side Android failure injection modes:
  `network-offline-online-before-sync` and
  `app-background-foreground-before-sync`.
- Added optional `-UiMutationModes daily-entry-activity`, which navigates to a
  seeded report, edits the real location-scoped activities text field, taps
  `Save Entry`, verifies the local `daily_entries` row, and verifies a matching
  pre-sync `change_log` row.
- Updated central docs so the new lab options are discoverable.

### Verification

- `dart analyze lib/core/driver/driver_diagnostics_handler.dart lib/core/driver/driver_server.dart test/core/driver/driver_diagnostics_routes_test.dart`
- `flutter test test/core/driver/driver_diagnostics_routes_test.dart`
- PowerShell parser check for `tools\enterprise-sync-soak-lab.ps1`
- `git diff --check` for the touched files

### What Is Still Not Proven

- The new UI mutation helper has not yet been run on S21/S10.
- The storage proof hook exists, but no real storage manifest has been produced
  from a device-uploaded file yet.
- The failure-injection hooks exist, but no S21/S10 failure-injection run has
  passed yet.
- The seven enterprise gates remain open.

### Next Implementation Slice

- Build UI-driven quantity mutation and prove it creates a local
  `entry_quantities` row plus a matching `change_log` row.
- Build UI-driven photo/file mutation with bytes, then generate the storage
  proof manifest from the resulting `remote_path`.
- Run S21/S10 with `-UiMutationModes daily-entry-activity` before checking any
  broader UI-driven mutation item.
- Keep role churn and same-device account switching separate from mutation
  proof so failures are easier to triage.

## 2026-04-17 - Quantity UI Mutation And Parallel Seam Review

### What We Found

- The report editor already exposes a production UI path for quantities:
  `/report/<entryId>` -> `report_add_quantity_button` ->
  `bid_item_picker_<bidItemId>` -> `quantity_amount_field` /
  `quantity_notes_field` -> `quantity_dialog_save`.
- The quantity id is generated by app code, so the device lab must discover it
  from the new `entry_quantities` `change_log` row instead of assuming a fixed
  seeded id.
- Backend actors should stay as separate `backend_rls` evidence. The cleanest
  concurrency seam is a host-side parent wrapper that runs the backend/RLS soak
  and the device lab at the same time, then writes a manifest pointing at both
  summaries.
- Photo/file proof can use the live UI plus `/driver/inject-photo` or
  `/driver/inject-file` to supply picker bytes without directly creating the
  row. Direct inject routes remain fallback-only because they bypass the UI.
- Same-device account switching can be driven through real settings sign-out
  and login UI keys, with `/diagnostics/actor_context` and sync status as the
  post-switch proof seams.

### What We Did

- Added optional `-UiMutationModes quantity` to
  `tools/enterprise-sync-soak-lab.ps1`.
- The quantity mode navigates to a seeded report, opens the real pay-item
  picker, selects a seeded bid item, fills the real add-quantity dialog, and
  saves through the app provider path.
- The lab now discovers the app-generated `entry_quantities` id from the new
  unprocessed `change_log` row, verifies the local row's `entry_id`,
  `bid_item_id`, `quantity`, and `notes`, and records the proof in
  `round-<n>-ui-mutations.json`.
- Added a generic post-sync assertion that fails a run if any recorded UI
  mutation still has an unprocessed matching `change_log` row after a
  successful UI-triggered sync.
- Updated developer docs and the live implementation TODO for the new quantity
  mode.

### Verification

- PowerShell parser check for `tools\enterprise-sync-soak-lab.ps1`.

### What Is Still Not Proven

- The new quantity mutation mode has not yet been run on S21/S10.
- Daily-entry activity and quantity are only two of the required UI mutation
  families; photos/files, forms/signatures, and personnel/equipment/contractor
  rows remain open.
- Backend/device concurrency is not implemented yet; it is now mapped to a
  parent wrapper.
- The seven enterprise gates remain open.

### Next Implementation Slice

- Add a parent host-side enterprise wrapper that starts backend/RLS soak with
  10-20 virtual users while `tools/enterprise-sync-soak-lab.ps1` drives device
  actors, then writes a parent manifest preserving both evidence layers.
- Build UI-driven photo/file mutation with real picker-injected bytes and
  generate a storage proof manifest from the synced `remote_path`.
- Run S21/S10 with `-UiMutationModes daily-entry-activity,quantity` before
  checking any broader UI-driven mutation item.

## 2026-04-17 - Backend/Device Concurrent Parent Wrapper

### What We Found

- The backend/RLS soak already supports 20 virtual users and 8 concurrent
  workers through `SOAK_USER_COUNT` and `SOAK_CONCURRENCY`.
- The missing implementation piece was orchestration with the device lab, not
  another backend action loop.
- The device lab should not absorb backend actors internally because that would
  blur the `backend_rls` and `device_sync` evidence layers.

### What We Did

- Added `tools/enterprise-sync-concurrent-soak.ps1` as a parent orchestrator.
- The wrapper starts the backend/RLS soak in a background job, runs
  `tools/enterprise-sync-soak-lab.ps1` in the foreground, waits for both, and
  writes a parent `manifest.json`.
- The parent manifest links the copied backend/RLS summary and the device-sync
  summary, records the backend virtual-user/concurrency settings, and only
  passes if both child summaries pass while preserving their layer labels.
- Updated docs and the implementation TODO so the new concurrent lab command is
  discoverable.

### Verification

- PowerShell parser check for `tools\enterprise-sync-concurrent-soak.ps1`.

### What Is Still Not Proven

- The concurrent wrapper has not yet been run with real S21/S10 devices and a
  real backend/RLS soak.
- A parent manifest proves overlap only after execution; no enterprise gate is
  complete from static script validation.
- The backend soak still mutates only the backend/RLS layer. Device-sync proof
  still depends on the phone/tablet child artifacts.

### Next Implementation Slice

- Build UI-driven photo/file mutation with real picker-injected bytes and
  generate a storage proof manifest from the synced `remote_path`.
- Add a short dry-command validation path for the wrapper if we need CI-side
  syntax proof without launching devices.
- Run S21/S10 with
  `tools\enterprise-sync-concurrent-soak.ps1 -UiMutationModes daily-entry-activity,quantity`
  once the devices are ready.

## 2026-04-17 - Photo UI Mutation And Generated Storage Proof

### What We Found

- The active daily-entry photo path is the report attachments section:
  `report_add_photo_button` -> `photo_source_dialog` ->
  `photo_capture_gallery` or `photo_capture_camera` ->
  `photo_name_dialog`.
- `/driver/inject-photo` supplies bytes to `TestPhotoService` without creating
  a row directly. The app still consumes the injected file through the real
  picker path, naming dialog, `PhotoService.savePhoto`, local repository, and
  sync trigger.
- `photos.remote_path` is not available before sync. A real object proof has to
  happen after UI-triggered sync, by rereading the local row and then checking
  the `entry-photos` bucket.

### What We Did

- Added optional `-UiMutationModes photo` to
  `tools/enterprise-sync-soak-lab.ps1` and the concurrent parent wrapper.
- The photo mode injects a small real image payload, drives the live Add Photo
  flow, fills filename and description, verifies the local `photos` row, and
  verifies a matching pre-sync `change_log` row.
- After successful UI-triggered sync, recorded photo mutations must have a
  non-empty `remote_path`.
- The lab now generates a per-photo storage manifest and runs the existing
  Supabase Storage object proof against the `entry-photos` bucket. The run
  fails if the object proof fails.
- Updated docs and the implementation TODO for the photo mode.

### Verification

- PowerShell parser check for `tools\enterprise-sync-soak-lab.ps1`.
- PowerShell parser check for `tools\enterprise-sync-concurrent-soak.ps1`.

### What Is Still Not Proven

- The new photo mode has not yet been run on S21/S10.
- Host storage proof requires `SUPABASE_URL` and `SUPABASE_ANON_KEY` available
  to the lab process, plus an access token if anon access cannot read the
  object under storage RLS.
- This closes only the photo row/object path. Other file-backed rows,
  signatures, form exports, entry documents, entry exports, and pay-app exports
  remain open.

### Next Implementation Slice

- Superseded by the later S21-first state-machine lane below. Do not run the
  old S21/S10 concurrent `-UiMutationModes daily-entry-activity,quantity,photo`
  path as acceptance evidence.
- Continue with the refactored S21 `combined` flow after the isolated gates.
- Build UI-driven form/signature mutation proof next, or add role-switch
  UI automation if the immediate priority shifts back to role churn.

## 2026-04-17 - Device Photo Soak Blocked By Runtime Red Screens

### What We Found

- The current two-device method is viable, but the app is not currently stable
  enough to accept it as green. Continuing to rerun the soak produces more
  red-screen evidence, not closure.
- S10 produced a full all-modes pass for the current UI mutation slice in
  `20260417-1919-device-all-modes-smoke`:
  daily-entry activity, quantity, photo, UI-triggered sync, zero queue residue,
  and generated Supabase Storage proof all passed.
- S21 previously produced the same local mutation/sync shape, and generated
  object proof now works with service-role storage verification, but repeated
  runs exposed a Flutter runtime failure before the run can be accepted.
- The recurring runtime failure is not a queue/RLS/storage failure. The device
  widget tree collapses to `ErrorWidget` with Flutter errors including:
  `Tried to build dirty widget in the wrong build scope`,
  `_elements.contains(element)` assertion failures, and duplicate
  `GlobalKey`/`InheritedGoRouter` messages.
- The red-screen artifacts are preserved under:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/s21-logcat-after-1922.txt`
  and
  `.claude/test-results/2026-04-17/enterprise-sync-soak/s10-logcat-after-1922.txt`.

### What We Did

- Tightened the device lab to:
  - use service-role storage proof from `.env.secret` when no explicit
    `SUPABASE_STORAGE_ACCESS_TOKEN` is supplied;
  - record storage proof auth mode and response details;
  - add driver wait timeout headroom so client HTTP timeouts do not cancel
    long `/driver/wait` calls early;
  - avoid retrying the photo source tap after the source sheet has already
    been selected.
- Verified parser health for `tools\enterprise-sync-soak-lab.ps1`.
- Confirmed storage proof can download the generated object from Supabase
  Storage. The previous anon proof returned `Object not found`; service-role
  proof downloaded the object and hashed it.

### Evidence Captured

- Drain after process restart passed, both devices zero queue residue:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-1918-drain-after-process-restart/summary.json`.
- S10 current all-modes pass inside a mixed run:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-1919-device-all-modes-smoke/S10/timeline.json`.
- S10 generated storage proof passed:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-1919-device-all-modes-smoke/S10/round-1-storage-proof-a5213455-00da-4302-b012-9172ef27fe5b.json`.
- S21/S10 red-screen failure run:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-1922-device-all-modes-smoke/summary.json`.

### Current Blocker

- Do not proceed to the concurrent parent wrapper or the 15-20 user workload
  until the Flutter red-screen/runtime navigation defect is fixed and a focused
  S21/S10 rerun passes without `ErrorWidget`, duplicate `GlobalKey`, dirty
  build-scope, or `_elements.contains(element)` failures.
- The next implementation slice is a runtime defect fix, not more soak
  expansion. Start from the photo naming dialog / report route transition path
  and the `InheritedGoRouter` duplicate GlobalKey logs captured above.
- S10 is parked for now. Use S21-only hardening runs until the report/photo
  flow is stable on the primary device. S10 should come back as a regression
  device after S21 is clean, not as a second noisy actor during root-cause work.
  Parking command used on 2026-04-17:
  `adb -s R52X90378YB shell am force-stop com.fieldguideapp.inspector` and
  `adb -s R52X90378YB forward --remove tcp:4949`.
- Historical S21-only hardening command shape was the legacy
  `-UiMutationModes daily-entry-activity,quantity,photo` path. It is now
  superseded by refactored `-Flow sync-only`, `-Flow daily-entry-only`,
  `-Flow quantity-only`, `-Flow photo-only`, and next `combined`.

## 2026-04-17 - S21 Strict-Log Audit And Harness Refactor Pause

### What We Found

- Full all-modes S21 reruns must pause. The latest failures are not one defect;
  they mix app runtime failures, photo picker stalls, cleanup residue, driver
  readiness gaps, and harness classification gaps.
- `tools/enterprise-sync-soak-lab.ps1` has grown to 1,864 lines with 36
  top-level functions. It currently mixes driver HTTP, ADB/logcat, artifact
  writing, UI flow steps, sync measurement, storage proof, cleanup/recovery
  behavior, and pass/fail aggregation in one script. That shape is now slowing
  root-cause work.
- S10 remains parked. The next valid path is S21-only single-flow hardening,
  not S10/S21 concurrent soak and not 15-20 user simulation.

### Strict-Log Improvements Made

- Added runtime log scanning to the lab runner.
- Runtime signatures now fail the round even if queue drain and storage proof
  pass.
- Missing log capture now increments `loggingGaps` and prevents the summary
  from passing.
- Runtime failure signatures currently include:
  `FlutterError`, `ErrorWidget`, `Multiple widgets used the same GlobalKey`,
  `Duplicate GlobalKey`, `Tried to build dirty`,
  `Another exception was thrown`, `Dart Unhandled Exception`,
  `FATAL EXCEPTION`, and `AndroidRuntime`.
- Failure artifacts now include a failure screenshot and expanded logcat bundle
  when catch-block failures or runtime-log failures occur.

### Evidence From Latest S21 Runs

- Strict log gate caught the red-screen runtime failure:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-strictlog-stablekey-all-modes/summary.json`.
  Summary: `passed=false`, `failedActorRounds=1`, `runtimeErrors=1`,
  `loggingGaps=0`, `queueDrainResult=drained`.
- The captured runtime signature was:
  `FlutterError: Multiple widgets used the same GlobalKey` with
  `InheritedGoRouter(goRouter: Instance of 'GoRouter')`.
- Cleanup sync then failed because the cleanup payload used
  `deleted_by = enterprise-soak-cleanup`, which is not a UUID:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-strictlog-cleanup-sync/summary.json`.
- Cleanup rerun still failed because local cleanup updates conflicted with
  already-synced newer remote versions:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-strictlog-cleanup-sync-rerun/summary.json`.
- A direct `/driver/sync` recovery cleared the cleanup queue. This is recorded
  as recovery only, not acceptance evidence.
- Post-cleanup strict no-mutation drain passed:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-post-cleanup-strict-drain/summary.json`.
  Summary: `passed=true`, `queueDrainResult=drained`, `runtimeErrors=0`,
  `loggingGaps=0`.
- After route-transition patches, latest all-modes S21 still failed:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-fullscreen-notransition-strict-all-modes/summary.json`.
  The failure was a `photo_name_dialog` timeout, not a captured Flutter runtime
  log error. Screenshot showed the photo source sheet still open on
  "Choose from Gallery":
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-fullscreen-notransition-strict-all-modes/S21/round-1-failure-screenshot.png`.

### Failure Pattern Audit

Artifact aggregation across 2026-04-17 soak summaries shows these repeated
failure groups:

- Driver readiness / endpoint gaps: port refused, `404`, `503 no live context`,
  or stale route state before mutation.
- Daily-entry update not observed: the field was edited but local verification
  did not see the expected row state in time.
- Sync dashboard/button missing: `/sync/dashboard` was not actually ready, or
  `sync_now_full_button` was not tappable when the harness expected it.
- Quantity flow widget missing: bid-item sheet, quantity save, or notes field
  assumptions did not match the live UI.
- Photo flow timeout: source sheet remained visible and `photo_name_dialog`
  never appeared.
- Storage proof/environment failures: object proof failed until service-role
  style storage proof was used.
- Runtime red screens: duplicate `GlobalKey` / `InheritedGoRouter`, plus
  earlier dirty build-scope and `_elements.contains(element)` failures.
- Cleanup/queue residue: generated rows and activity updates persisted after
  failed exploratory runs, and cleanup itself can conflict if not designed as
  a first-class phase.

### Current Status

- S21 local queue was recovered to zero unprocessed/blocked rows after the
  latest failed all-modes run by restoring the daily-entry activity field,
  soft-deleting the generated quantity, and using direct `/driver/sync` as a
  recovery-only action.
- Because direct `/driver/sync` bypasses the Sync Dashboard, that recovery does
  not count as UI proof.
- The current app/harness state is not ready for another full all-modes soak.

### New Action Plan

- Added focused plan:
  `.codex/plans/2026-04-17-s21-soak-harness-audit-and-recovery-plan.md`.
- The plan requires:
  - keeping S10 parked;
  - keeping 15-20 user simulation parked;
  - refactoring the soak harness around driver client, step runner, artifact
    writer, flow modules, cleanup ledger, and summary aggregation;
  - adding fail-loud gates for runtime logs, missing logs, screenshots/widget
    tree red-screen evidence, queue residue, and cleanup residue;
  - proving S21 one flow at a time before any combined run.

### Next Implementation Slice

1. Add or refactor a `StepRunner` so every UI step captures route, screenshot,
   log status, and queue context on failure.
2. Split the current monolithic lab script into focused modules or at minimum
   flow-specific files under `tools/sync-soak/`.
3. Add a mutation ledger and cleanup phase before running more write flows.
4. Run S21 in this order only:
   sync-only drain, daily-entry-only, quantity-only, photo-only, then combined.
5. Do not bring S10, concurrent backend actors, role churn, or 15-20 user load
   back until those S21 single-flow gates are clean.

## 2026-04-17 - Driver/Debug Reuse Audit

### Question

Before building `tools/sync-soak/` modules, audit whether the existing driver
and debug infrastructure already provides the server/control-plane pieces.

### Findings

- The two existing HTTP servers are complementary, not duplicate
  implementations:
  - `lib/core/driver/driver_server.dart` runs inside the debug app and should
    remain the app/device control plane for S21/S10 UI actions, screenshots,
    widget trees, local records, change logs, actor context, and sync runtime.
  - `tools/debug-server/server.js` runs on the workstation and should remain
    the structured log, artifact, sync-status, and trusted host-verification
    support server.
- `tools/start-driver.ps1` already starts the debug log server, builds/installs
  the driver app, sets `DEBUG_SERVER=true`, sets `DRIVER_PORT`, and wires ADB
  `reverse`/`forward` for Android.
- `tools/wait-for-driver.ps1` already checks both `/driver/ready` and
  debug-server `/health`.
- `tools/measure-device-sync.ps1` already contains the right UI-triggered Sync
  Dashboard pattern and should be extracted or wrapped instead of rewritten.
- `integration_test/sync/harness/harness_driver_client.dart` already provides
  a typed driver client. If the flow runner moves to Dart later, it should use
  this client instead of reimplementing endpoint semantics.
- `integration_test/sync/soak/soak_driver.dart` and
  `integration_test/sync/soak/soak_metrics_collector.dart` already model the
  15-project fixture, weighted action taxonomy, virtual users, concurrency,
  burst windows, actor reports, and backend/device layer summary fields.
- `lib/core/driver/screen_contract_registry.dart` already exposes screen/root
  key/action/state metadata through `/diagnostics/screen_contract`; StepRunner
  should use that to validate route/screen state.
- The local systematic-debugging docs are process guidance, not runtime code.
  The useful rule here is to stop after repeated hypotheses/fix failures,
  capture evidence, classify the root cause, and avoid continuing through later
  flows.

### Decision

- Do not create a third HTTP server.
- Continue with the thin CLI plus modules refactor, but make the modules
  clients/orchestrators around the existing app-side `DriverServer` and
  host-side `debug-server`.
- Add new driver or debug-server endpoints only after proving the evidence gap
  cannot be closed by existing `/driver/tree`, `/driver/screenshot`,
  `/diagnostics/*`, `/driver/change-log`, `/driver/local-record`,
  debug-server `/logs/*`, or `supabase-verifier.js`.

### Reuse Map

- `DriverClient.ps1`: wraps existing app-side driver endpoints.
- `ArtifactWriter.ps1`: captures screenshots via `/driver/screenshot`, widget
  trees via `/driver/tree`, screen contracts via `/diagnostics/screen_contract`,
  debug-server logs via `/logs/errors` and `/logs/summary`, plus bounded ADB
  logcat.
- `StepRunner.ps1`: no raw flow calls to `Invoke-DriverJson`; every step goes
  through one wrapper that captures pre/post route, screen contract, logs, and
  failure bundle.
- `Flow.SyncDashboard.ps1`: extract/wrap `tools/measure-device-sync.ps1`
  behavior; no direct `/driver/sync` in acceptance flows.
- `Cleanup.ps1`: use mutation ledger plus trusted host cleanup/verification via
  `supabase-verifier.js` or narrowly scoped debug-server additions if needed.
- `Summary.ps1`: keep summary fields aligned with `SoakSummary` so parent
  manifests can compare `backend_rls` and `device_sync` without translation.

### 15-20 User Clarification

- The lab does not require 15-20 physical phones. Current physical device
  capacity is S21 + S10, with an optional emulator only if it proves stable.
- One S21 cannot simulate 15-20 concurrent visible UI users.
- The valid scale model remains:
  - S21 primary real-device UI/device-sync acceptance actor;
  - S10 regression real-device actor after S21 is clean;
  - optional emulator as a third UI/device actor if it adds signal;
  - headless app-sync actors for the 10-20 app-user lane, each with real
    Supabase auth and isolated local state;
  - backend/RLS virtual users for remote pressure and policy assertions.
- A single S21 may cycle accounts sequentially for role churn and cache-reset
  proof, but that is account-switching proof, not concurrent 20-device proof.
- Parent manifests should distinguish `device_ui`, `headless_app_sync`, and
  `backend_rls` evidence instead of flattening all actors into one bucket.

## 2026-04-17 - First Harness Module Split

### What We Found

- The existing lab script could keep the legacy all-modes path intact while a
  stricter S21-first path is introduced behind a new `-Flow` switch.
- The first valuable acceptance slice is `sync-only` because it proves driver
  readiness, Sync Dashboard navigation, UI-triggered sync, log capture, widget
  tree inspection, and queue residue checks before any new mutation residue is
  created.

### What We Did

- Added `tools/sync-soak/SoakModels.ps1` for actor parsing, summary shape,
  queue-count helpers, acceptance labels, and failure classification.
- Added `tools/sync-soak/DriverClient.ps1` as a thin client around the
  existing app-side driver server. No new HTTP server was added.
- Added `tools/sync-soak/ArtifactWriter.ps1` for JSON artifacts, screenshots,
  ADB logcat capture, debug-server `/logs/errors` and `/logs/summary`
  capture, runtime signature fingerprints, and widget-tree red-screen
  classification.
- Added `tools/sync-soak/StepRunner.ps1` so refactored UI steps capture
  pre/post route and screen-contract state, named step artifacts, debug-server
  evidence, bounded ADB logcat, widget-tree state, runtime errors, and logging
  gaps.
- Added `tools/sync-soak/Flow.SyncDashboard.ps1`, reusing the
  `tools/measure-device-sync.ps1` pattern: navigate to `/sync/dashboard`, wait
  for real keys, tap `sync_now_full_button`, poll `/driver/sync-status`, and
  never call direct `/driver/sync` for acceptance.
- Wired `tools/enterprise-sync-soak-lab.ps1 -Flow sync-only` through the new
  modules. Other refactored flows intentionally fail closed until their modules
  are added.
- Added `tools/test-sync-soak-harness.ps1` for fast classifier checks:
  `FlutterError`, widget wait timeout, logging gap classification,
  `ErrorWidget` widget-tree classification, and direct-sync non-acceptance.

### Verification

- PowerShell parser check passed for:
  - `tools/enterprise-sync-soak-lab.ps1`
  - `tools/test-sync-soak-harness.ps1`
  - every `tools/sync-soak/*.ps1` module
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` passed.

### What Is Still Not Proven

- Daily-entry-only, quantity-only, photo-only, cleanup-only, and mutation
  ledger modules are still open.
- The legacy all-modes mutation path still exists and should not be used for
  acceptance until those flows are migrated onto `StepRunner`.

### Next Implementation Slice

- Migrate daily-entry-only onto `StepRunner`, including mutation ledger
  capture and cleanup proof.

## 2026-04-17 - S21 Refactored Sync-Only Proof

### What We Found

- The first refactored S21 `sync-only` run failed in preflight before any
  mutation. This was a useful fail-loud result, not a sync failure:
  `/driver/ready`, `/driver/current-route`, and `/diagnostics/screen_contract`
  responded, but `/driver/screenshot` and `/driver/tree` hung until host HTTP
  timeout.
- Root cause: app-side driver evidence endpoints could wait indefinitely for a
  Flutter frame or screenshot encoding. That created exactly the observability
  gap the refactor was meant to eliminate.
- The harness also initially mislabeled the generic preflight HTTP timeout as
  `widget_wait_timeout`; that classification should be reserved for
  `/driver/wait` key timeouts.

### What We Did

- Updated `lib/core/driver/driver_shell_handler.dart` so driver evidence
  endpoints fail loudly instead of hanging:
  - `_waitForFrame()` now has a 3-second timeout and logs a driver-category
    error.
  - screenshot `toImage()` and PNG encoding each have a 5-second timeout.
- Added `test/core/driver/driver_shell_handler_timeout_contract_test.dart` to
  lock the bounded-timeout evidence contract.
- Tightened the PowerShell failure classifier so generic preflight HTTP
  timeout stays a preflight/evidence failure instead of becoming
  `widget_wait_timeout`.
- Reinstalled the S21 driver build with:
  `pwsh -NoProfile -File tools/start-driver.ps1 -Platform android -DeviceId RFCNC0Y975L -DriverPort 4948 -Timeout 180 -ForceRebuild`.
- Verified `/driver/screenshot` and `/driver/tree` on S21 both returned in
  roughly `0.14s` after reinstall.
- Ran three serial S21 `sync-only` passes through the refactored module path.

### Evidence

- Initial fail-loud preflight failure:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-sync-only/summary.json`
- Green S21 serial sync-only runs:
  - `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-sync-only-rerun/summary.json`
  - `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-sync-only-serial-2/summary.json`
  - `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-sync-only-serial-3/summary.json`
- Each accepted run reports:
  - `passed=true`
  - `queueDrainResult=drained`
  - `blockedRowCount=0`
  - `unprocessedRowCount=0`
  - `runtimeErrors=0`
  - `loggingGaps=0`
  - `directDriverSyncEndpointUsed=false`
  - `acceptanceLabel=ui_acceptance`
  - debug-server evidence captured for 4 operation windows
  - ADB logcat evidence captured for 4 operation windows

### Verification

- `dart analyze lib/core/driver/driver_shell_handler.dart test/core/driver/driver_shell_handler_timeout_contract_test.dart`
- `flutter test test/core/driver/driver_shell_handler_timeout_contract_test.dart test/core/driver/main_driver_screenshot_boundary_contract_test.dart`
- PowerShell parser check for:
  - `tools/enterprise-sync-soak-lab.ps1`
  - `tools/test-sync-soak-harness.ps1`
  - every `tools/sync-soak/*.ps1` module
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`

### What Is Still Not Proven

- Daily-entry-only, quantity-only, photo-only, cleanup-only, and combined
  all-modes are still not accepted through the refactored path.
- Two accidental parallel sync-only runs were green but are explicitly not
  counted toward the three-consecutive gate because they targeted the same S21
  at the same time.
- S10 remains parked.

### Next Implementation Slice

- Move daily-entry-only onto the refactored modules:
  StepRunner-driven UI steps, mutation ledger original-value capture, UI sync,
  cleanup restore, second UI sync, and local/remote restored proof.

## 2026-04-17 - S21 Daily-Entry-Only Cleanup Proof

### What We Found

- The first S21 `daily-entry-only` refactored run mutated and synced a real
  `daily_entries` row, then failed during host-side Supabase REST proof with
  `401 Unauthorized`.
- That failure exposed a cleanup-ordering risk: a post-mutation proof failure
  could stop the round before ledger cleanup ran.
- The Supabase env currently provides `sb_secret_` / `sb_publishable` keys,
  not a PostgREST service-role JWT. Host REST proof is therefore not the right
  acceptance seam for current-user RLS proof.
- The selected row already contained older generated soak text from previous
  work. The recovery in this slice restored only the exact pre-run value
  captured in this run's ledger; it did not delete or rewrite historical data.

### What We Did

- Recovered the failed run using the mutation ledger:
  - restored only `daily_entries/f14d87c1-d870-444e-ba2b-bca5762aa485`,
  - restored only the captured daily-entry activity value,
  - did not delete any live rows,
  - synced cleanup through the UI sync dashboard.
- Added app-side `/driver/remote-record` as a read-only proof endpoint using
  the app's current real Supabase session, table allowlisting, and column-name
  validation.
- Reran S21 `daily-entry-only`; it passed with mutation proof, UI sync,
  cleanup restore, cleanup sync, final local proof, and final remote proof.
- Hardened the PowerShell daily-entry flow so cleanup is not just a happy-path
  block:
  - mutation-sync and cleanup-sync artifacts now get distinct names,
  - remote mutation proof errors are recorded without skipping cleanup,
  - failure after a local mutation attempts ledger-owned cleanup before the
    round is recorded failed,
  - recovery-only direct local restore is marked as recovery evidence and only
    targets the ledger-owned row/field.

### Evidence

- Initial failed daily-entry run:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only/summary.json`
- Ledger used for recovery:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only/S21/round-1-mutation-ledger.json`
- Recovery cleanup sync:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-daily-entry-ledger-cleanup-sync/summary.json`
- Accepted S21 daily-entry run:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only-rerun/summary.json`
- Accepted run reports:
  - `passed=true`
  - `queueDrainResult=drained`
  - `blockedRowCount=0`
  - `unprocessedRowCount=0`
  - `runtimeErrors=0`
  - `loggingGaps=0`
  - `directDriverSyncEndpointUsed=false`
  - `cleanupPassed=true`
  - final local and remote daily-entry activity no longer contain this run's
    generated marker.

### Cleanup Safety Rule

- The S21 harness may only clean up rows and storage objects recorded in its
  mutation ledger.
- For existing rows, cleanup must restore captured pre-run values rather than
  deleting records.
- For newly-created rows or storage objects in future quantity/photo/file
  flows, cleanup must prove ownership with the ledger ID plus generated marker
  before soft-deleting a row or removing a storage object.

### What Is Still Not Proven

- Daily-entry-only has one accepted green pass. The three-consecutive pass
  gate still needs two more serial S21 runs.
- Quantity-only, photo-only, cleanup-only, and combined all-modes remain
  unaccepted in the refactored path.
- S10 and 15-20 user scale-up remain parked.

### Next Implementation Slice

- Run two more serial S21 `daily-entry-only` passes under the hardened cleanup
  path.
- If both pass, implement `quantity-only` with a ledger-owned generated row and
  cleanup that soft-deletes only that generated row.

## 2026-04-17 - S21 Daily-Entry Sentinels And Three-Pass Gate

### What We Found

- `20260417-s21-refactor-daily-entry-only-serial-2` failed exactly where the
  harness needed to get smarter:
  - the mutation and mutation sync succeeded,
  - cleanup attempted to use the ledger,
  - the helper read an ordered PowerShell ledger entry as object properties,
    which made `previousActivities` / `previousLocationText` resolve as empty,
  - the recovery-only local restore set `activities` to null locally,
  - the cleanup sync drained the queue, but remote proof still showed the
    generated marker.
- That means queue-zero alone is not a sufficient cleanup proof. Cleanup must
  prove exact local and remote field state, not just drain change-log rows.

### What We Did

- Stopped the pass sequence after the failure and recovered only the ledger
  row:
  - restored through a real UI edit cycle,
  - synced through the Sync Dashboard,
  - verified remote no longer contained the generated marker or temporary
    recovery marker.
- Fixed the ledger reader with `Get-SoakLedgerValue` so ordered dictionaries
  and PSCustomObjects are handled the same way.
- Added `[AllowEmptyString()]` to the daily-entry activity edit text parameter
  so a legitimate empty pre-run field can be restored through the UI.
- Added `tools/sync-soak/StateSentinels.ps1` with reusable state sentinels:
  exact text, marker absent, queue drained, route, and actor session.
- Wired state sentinels into the refactored runner and daily-entry cleanup.
  Cleanup now records:
  - local generated marker absent,
  - local exact ledger value,
  - remote generated marker absent,
  - remote exact ledger value.
- Added fast self-test coverage for ordered ledger lookup and sentinel helpers.

### Evidence

- Failed pass that exposed the cleanup bug:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only-serial-2/summary.json`
- UI ledger recovery:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-daily-entry-serial-2-ui-ledger-recovery/ledger-recovery-result.json`
- Accepted daily-entry serial replacement:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only-serial-2b/summary.json`
- Accepted sentinel-backed serial runs:
  - `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only-serial-3/summary.json`
  - `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only-serial-4/summary.json`
- `serial-3` and `serial-4` cleanup ledgers both report:
  - `cleanupPassed=true`
  - `uiRestorePassed=true`
  - `recoveryOnlyLocalRestoreUsed=false`
  - local marker absent sentinel `passed=true`
  - local exact ledger sentinel `passed=true`
  - remote marker absent sentinel `passed=true`
  - remote exact ledger sentinel `passed=true`
  - final S21 change log has zero blocked and zero unprocessed rows.

### Decision

- Sentinel keys/checks are the right hardening direction, as long as they are
  real app UI keys, diagnostics, local database reads, remote current-session
  reads, and queue/runtime evidence. They are guardrails and recovery
  checkpoints; they do not replace real UI mutation/sync proof.
- Do not scale to S10, emulator, or 15-20 users until each single-flow S21
  module has these same sentinels and cleanup ownership checks.

### Current Gate Status

- S21 `sync-only`: three accepted serial passes.
- S21 `daily-entry-only`: three accepted serial passes after the cleanup fix:
  `serial-2b`, `serial-3`, and `serial-4`.
- S21 `quantity-only`: next implementation gate.
- S21 `photo-only`, combined S21, S10 regression, emulator, and 15-20 user
  scale-up remain parked.

## 2026-04-18 - Sentinel State Machine And S21 Quantity Gate

### What We Found

- The first state-machine daily-entry reruns exposed a brittle sentinel: after
  typing activity text, the field key may disappear during keyboard dismissal,
  even though the local record mutation succeeded. That postcondition now
  checks the stable entry editor route/root and lets the local-record sentinel
  prove the data mutation.
- The initial quantity-only implementation failed loudly before data mutation:
  - first on `InheritedElement.notifyClients` / `RenderEditable attached`
    assertions during pay-item picker search;
  - then on duplicate GoRouter `GlobalKey` after the failed modal state;
  - then on the same text-field assertions when the quantity dialog opened
    immediately after the pay-item bottom sheet with autofocus enabled.
- All failed quantity attempts left no generated row and no change-log residue.

### What We Did

- Added `tools/sync-soak/StateMachine.ps1` and wired it into the refactored CLI
  and self-test. Transitions now write `state-machine/transition-*.json` and
  preserve failed sentinel payloads.
- Tightened `StepRunner` so a driver 500 plus captured Flutter runtime evidence
  is classified as `runtime_log_error`, not a generic driver error.
- Added the refactored `quantity-only` module with:
  - UI creation through the report quantity flow,
  - a unique notes marker for cleanup ownership,
  - change-log-derived generated row id,
  - UI-triggered mutation sync,
  - ledger-owned cleanup that soft-deletes only the generated row,
  - `deleted_by` set to the current authenticated user id,
  - UI-triggered cleanup sync,
  - local and remote soft-delete sentinels.
- Hardened the S21 app/driver modal path:
  - `/driver/back` now waits through modal pop teardown before returning;
  - the quantity picker waits between bottom-sheet close and dialog open;
  - the quantity amount field no longer autofocuses on dialog open.

### Evidence

- State-machine sync-only proof after sentinel fix:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-sync-only-after-sentinel-fix/summary.json`
- State-machine daily-entry proof after sentinel fix:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-daily-entry-only-after-sentinel-fix/summary.json`
- Post-rebuild sync-only smoke:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-sync-only-after-driver-rebuild/summary.json`
- Accepted quantity-only proof:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-quantity-only-after-autofocus-fix/summary.json`
- Daily-entry regression after quantity fixes:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-daily-entry-after-quantity-fixes/summary.json`

### Current Gate Status

- S21 `sync-only`: green after state-machine changes and after driver rebuild.
- S21 `daily-entry-only`: green after state-machine changes and after quantity
  modal fixes.
- S21 `quantity-only`: first accepted green pass with cleanup proof at this
  checkpoint. The follow-up checkpoint below records the later quantity/photo
  confidence passes.
- S21 `photo-only`, combined S21, S10 regression, emulator, and 15-20 user
  scale-up remained parked at this checkpoint.

## 2026-04-18 - S21 Photo Gate And Single-Flow Sweep

### What We Found

- The photo-only red screen was the same modal/text-field class as quantity:
  `InheritedElement.notifyClients` and `RenderEditable attached` assertions
  after the gallery source path opened the photo name dialog.
- After the UI red screen was fixed, the photo flow created and synced the row,
  but cleanup initially failed because the storage absence proof treated only
  HTTP 404 as absence. Supabase Storage returned HTTP 400 with an embedded
  `statusCode:"404"` and `Object not found` body after delete.
- One later failed run was a StrictMode harness bug: `Invoke-WebRequest
  -OutFile` did not expose `StatusCode`, and the catch block assumed every
  exception had a `Response` property. Cleanup still passed in that run.

### What We Did

- Hardened the app photo path:
  - the camera/gallery path waits through `kThemeAnimationDuration` before
    opening `PhotoNameDialog`;
  - `PhotoNameDialog` no longer autofocuses the filename field on open.
- Added the refactored `photo-only` module with:
  - `/driver/inject-photo` only as picker input, not as row creation;
  - live UI Add Photo flow through source sheet, name dialog, and Save Photo;
  - local `photos` row discovery via `change_log`;
  - UI-triggered mutation sync;
  - remote row proof;
  - Supabase Storage object download proof;
  - ledger-owned local soft delete with current user UUID;
  - UI-triggered cleanup sync;
  - remote soft-delete proof;
  - storage object delete and absence proof.
- Hardened the storage helpers under StrictMode:
  - response status handling tolerates missing `StatusCode` on successful
    `-OutFile` downloads;
  - exception status handling checks for `Response` before reading it;
  - absence proof records response content and accepts Supabase Storage's
    `400` plus embedded object-not-found response as a valid absence signal.

### Evidence

- Accepted S21 photo-only proof:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-photo-only-storage-status-fix/summary.json`
- Photo proof details from that run:
  - `passed=true`
  - `failedActorRounds=0`
  - `runtimeErrors=0`
  - `loggingGaps=0`
  - `queueDrainResult=drained`
  - `directDriverSyncEndpointUsed=false`
  - storage download proof `passed=true`, `bytes=68`
  - cleanup `passed=true`
  - storage delete `passed=true`
  - storage absence `passed=true`
- Final rebuilt-app S21 single-flow sweep:
  - sync-only:
    `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-sync-only-final-single-gate/summary.json`
  - daily-entry-only:
    `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-daily-entry-final-single-gate/summary.json`
  - quantity-only:
    `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-quantity-final-single-gate/summary.json`
  - photo-only:
    `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-photo-only-storage-status-fix/summary.json`
- All four final single-flow summaries report:
  - `passed=true`
  - `failedActorRounds=0`
  - `runtimeErrors=0`
  - `loggingGaps=0`
  - `queueDrainResult=drained`
  - `blockedRowCount=0`
  - `unprocessedRowCount=0`
  - `maxRetryCount=0`
  - `directDriverSyncEndpointUsed=false`
- Live S21 queue after the sweep:
  `/driver/change-log` returned `count=0`, `unprocessedCount=0`,
  `blockedCount=0`, and `maxRetryCount=0`.

### Current Gate Status

- S21 `sync-only`: green.
- S21 `daily-entry-only`: green.
- S21 `quantity-only`: three accepted passes with cleanup:
  - `20260418-s21-state-machine-quantity-only-after-autofocus-fix`
  - `20260418-s21-state-machine-quantity-final-single-gate`
  - `20260418-s21-state-machine-quantity-confidence-3`
- S21 `photo-only`: three accepted passes with storage proof and cleanup:
  - `20260418-s21-state-machine-photo-only-storage-status-fix`
  - `20260418-s21-state-machine-photo-confidence-2`
  - `20260418-s21-state-machine-photo-confidence-3`
- All six quantity/photo confidence summaries report `passed=true`,
  `failedActorRounds=0`, `runtimeErrors=0`, `loggingGaps=0`,
  `queueDrainResult=drained`, `blockedRowCount=0`, `unprocessedRowCount=0`,
  `maxRetryCount=0`, and `directDriverSyncEndpointUsed=false`.
- Refactored `combined` is still not implemented. The CLI declares the value
  but fails closed, and the legacy all-modes runner should not be used as a
  substitute for this gate.
- S10, emulator, headless app-sync actors, backend/device overlap, and 15-20
  user scale-up remain parked until the combined S21 gate is implemented and
  green.

## 2026-04-18 - Refactored S21 Combined Gate

### What We Found

- The safest first combined implementation is sequential composition of the
  proven refactored phases: daily-entry mutate/sync/cleanup, then quantity
  mutate/sync/cleanup, then photo mutate/sync/cleanup. This avoids mixing three
  local mutation families behind one shared sync before the harness has S10
  regression evidence.
- The first live combined attempt exposed a parent-summary finalizer bug, not
  an app/runtime/sync defect. The child daily-entry, quantity, and photo phases
  all completed and cleaned up, and the live S21 queue was empty, but the
  parent summary failed on PowerShell list coercion before it could finalize
  `queueDrainResult` and `passed`.

### What We Did

- Added `tools/sync-soak/Flow.Combined.ps1`.
- Wired `-Flow combined` in `tools/enterprise-sync-soak-lab.ps1`.
- The combined module now:
  - writes a parent `combined` summary with phase order and child summary
    paths;
  - runs daily-entry, quantity, and photo through the existing refactored
    state-machine flow modules;
  - stops before later phases if a child phase fails;
  - aggregates strict runtime/logging/direct-sync counters;
  - captures final parent actor context, sync runtime, and `/driver/change-log`
    after all phases;
  - passes only when every child phase passes, final queue is drained, there
    are no runtime errors or logging gaps, and no direct `/driver/sync` was
    used.
- Added a fast combined summary aggregation self-test to
  `tools/test-sync-soak-harness.ps1`.
- Fixed the parent finalizer list-counting bug exposed by the first live run.

### Evidence

- Non-acceptance harness-finalizer failure:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-initial/summary.json`
  - child daily-entry, quantity, and photo phases passed;
  - live `/driver/change-log` after the failure was empty;
  - parent summary was not accepted because `Complete-SoakCombinedSummary`
    threw before setting final pass fields.
- Accepted S21 combined proof:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-final/summary.json`
  - parent: `passed=true`, `failedActorRounds=0`, `runtimeErrors=0`,
    `loggingGaps=0`, `queueDrainResult=drained`, `blockedRowCount=0`,
    `unprocessedRowCount=0`, `maxRetryCount=0`,
    `directDriverSyncEndpointUsed=false`, `acceptanceLabel=ui_acceptance`;
  - phase summaries: daily-entry-only, quantity-only, and photo-only each
    passed with zero runtime errors, zero logging gaps, drained queue, and no
    direct driver sync;
  - photo storage proof downloaded `68` bytes from `entry-photos`, deleted the
    generated object, and proved object absence through Supabase's
    object-not-found response;
  - final live S21 `/driver/change-log` returned `count=0`,
    `unprocessedCount=0`, `blockedCount=0`, and `maxRetryCount=0`.

### Verification

- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`
- Cleared debug logs with `POST http://127.0.0.1:3947/clear` before the live
  accepted run.
- Confirmed S21 queue empty before and after the accepted run with
  `GET http://127.0.0.1:4948/driver/change-log`.

### Current Gate Status

- S21 `sync-only`: green.
- S21 `daily-entry-only`: green.
- S21 `quantity-only`: three accepted passes with cleanup.
- S21 `photo-only`: three accepted passes with storage proof and cleanup.
- S21 `combined`: green through the refactored state-machine module.
- S10 is now the next real-device regression gate. Emulator, headless
  app-sync actors, backend/device overlap, and 15-20 user scale-up remain
  parked until S10 regression is green.

## 2026-04-18 - Spec Audit And Agent Task List

### What We Found

- The active specs now agree on the main truth: S21 refactored
  `sync-only`, `daily-entry-only`, `quantity-only`, `photo-only`, and
  `combined` are green, and S10 regression is the next device-sync gate.
- The enterprise spec is still intentionally open. S21 combined does not prove
  S10 mutation regression, role churn, backend/device overlap, headless
  app-sync scale, 15-project fixtures, failure injection, realtime dirty
  scopes, staging soaks, or external release gates.
- The concurrent parent wrapper existed, but it only forwarded legacy
  `-UiMutationModes`; that would have forced future backend/device overlap
  away from the accepted refactored `-Flow combined` path.

### What We Did

- Added `.codex/plans/2026-04-18-sync-soak-spec-audit-agent-task-list.md` as a
  Codex addendum that maps remaining spec work into implementation-agent lanes:
  S10/cleanup-only, remaining mutation families, role/account switching,
  storage expansion, failure injection/observability, and fixture/staging/scale.
- Updated current context and plan docs so they no longer describe S21
  `combined` as future work.
- Split stale combined checklist items so `combined` is closed and
  `cleanup-only` remains open.
- Scoped S21 photo and S21 write-flow checklist items to the implemented lanes
  only, leaving personnel/equipment/contractor/form/signature/file-backed
  families open.
- Added `-Flow` support to `tools/enterprise-sync-concurrent-soak.ps1` and
  reject mixed refactored/legacy switches, matching the device runner's
  fail-closed contract.

### Verification

- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`
- PowerShell parser check for `tools/enterprise-sync-concurrent-soak.ps1`
- PowerShell parser check for `tools/enterprise-sync-soak-lab.ps1`
- `git diff --check`

### Current Gate Status

- S21 combined remains accepted at
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-final/summary.json`.
- S10 refactored combined regression is still unproven and is the next live
  device gate.
- Backend/device overlap can now target refactored `-Flow` gates from the
  parent wrapper, but no overlap run has been accepted yet.

## 2026-04-18 - Begin Audit Task List Implementation

### What We Changed

- Added `tools/sync-soak/Flow.CleanupOnly.ps1`.
  - `cleanup-only` now requires explicit `-CleanupLedgerPaths`.
  - It assigns ledgers to actors by actor-id path segment, or to the only
    actor in a one-actor run.
  - It copies source ledgers into the new artifact tree before replaying
    cleanup, so old accepted evidence is not mutated.
  - It reuses the existing daily-entry, quantity, and photo ledger cleanup
    helpers and keeps UI-triggered Sync Dashboard sync as the cleanup
    acceptance path.
- Wired `-Flow cleanup-only` through `tools/enterprise-sync-soak-lab.ps1` and
  `tools/enterprise-sync-concurrent-soak.ps1`.
- Added `tools/sync-soak/S10Regression.ps1` and a
  `-PrintS10RegressionRunGuide` path on the device runner. The guide prints
  the ordered S10 refactored gate commands and rejects legacy all-modes and
  direct `/driver/sync` acceptance.
- Tightened harness failure classification for cleanup-ledger, storage
  proof/cleanup, change-log proof, and unsupported-flow failures.

### Verification

- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`
- PowerShell parser checks:
  - `tools/sync-soak/Flow.CleanupOnly.ps1`
  - `tools/sync-soak/S10Regression.ps1`
  - `tools/enterprise-sync-soak-lab.ps1`
  - `tools/enterprise-sync-concurrent-soak.ps1`
- Smoke-printed S10 run guide with:
  `pwsh -NoProfile -File tools/enterprise-sync-soak-lab.ps1 -Actors "S10:4949:inspector:1" -PrintS10RegressionRunGuide -Rounds 1 -RampUpSeconds 0`

### Still Open

- No new S10 live device gate was run in this slice.
- `cleanup-only` is parser/self-test proven but not yet live-device accepted.
- Contractor/personnel/equipment is the next smallest true-UI mutation family
  to implement; forms/signatures remain larger and file-backed.
- Legacy catch paths still need deeper evidence-bundle reuse before the broad
  fallback can be eliminated everywhere.

## 2026-04-18 - S21 Contractor/Personnel/Equipment Gate

### What Changed

- Added `tools/sync-soak/Flow.Contractors.ps1` and wired
  `-Flow contractors-only` through the device runner and concurrent wrapper.
- The flow drives the real report contractor UI:
  - create project contractor from the report contractors section;
  - prove the local contractor and entry-contractor rows;
  - add a custom personnel type and equipment item through the contractor
    editor dialogs;
  - save one crew count and one equipment-use chip;
  - prove local `change_log` rows before sync;
  - sync through the Sync Dashboard;
  - prove remote rows;
  - cleanup ledger-owned rows and sync cleanup through the Sync Dashboard.
- Hardened the ledger so it owns every generated row, including the default
  personnel types created with a new contractor, not just the custom type used
  for the crew count.
- Added partial-failure cleanup discovery for contractor/personnel/equipment
  rows so a failed run can soft-delete generated rows before recording the
  failure.
- Fixed compact S21 runtime failures by removing immediate dialog autofocus
  from the report contractor create dialog and the personnel/equipment manager
  dialogs. The live failures were duplicate `GlobalKey`/detached render errors
  caused by keyboard focus during dialog transitions.

### Accepted Evidence

- Accepted S21 contractor/personnel/equipment proof:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-contractors-fourth/summary.json`
- Acceptance facts:
  - `passed=true`
  - `failedActorRounds=0`
  - `runtimeErrors=0`
  - `loggingGaps=0`
  - `queueDrainResult=drained`
  - `blockedRowCount=0`
  - `unprocessedRowCount=0`
  - `maxRetryCount=0`
  - `directDriverSyncEndpointUsed=false`
  - final live S21 `/driver/change-log` returned `count=0`,
    `unprocessedCount=0`, `blockedCount=0`, and `maxRetryCount=0`
- Ledger proof:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-contractors-fourth/S21/round-1-mutation-ledger.json`
  has `cleanupPassed=true` and includes contractor, entry-contractor,
  four personnel types, equipment, entry personnel count, and entry equipment
  cleanup with remote soft-delete sentinels.

### Recovery Evidence

- Earlier contractor attempts intentionally remain failed artifacts:
  `20260418-s21-state-machine-contractors-initial`,
  `20260418-s21-state-machine-contractors-second`, and
  `20260418-s21-state-machine-contractors-third`.
- Partial generated rows from failed attempts were recovered through
  UI-triggered Sync Dashboard sync, and the accepted run started and ended with
  an empty S21 queue.

### Verification

- `dart format` on changed Dart dialog/key files.
- `flutter analyze` on changed dialog/key files.
- `flutter test test/features/contractors/data/datasources/local/entry_contractors_local_datasource_test.dart`
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`
- PowerShell parser check for `tools/sync-soak/Flow.Contractors.ps1`
- `git diff --check`

### Current Gate Status

- S21 `contractors-only`: green through the refactored state-machine module.
- S21 `sync-only`, `daily-entry-only`, `quantity-only`, `photo-only`, and
  `combined`: still green from prior accepted artifacts.
- Still open by spec intent: S10 refactored regression, cleanup-only live
  replay, forms/signatures/file-backed mutation families, role/account sweeps,
  broader storage/RLS checks, failure injection, backend/device overlap,
  staging, and scale/headless actors.

## 2026-04-18 - S10 Regression And Cleanup-Only Replay

### What Changed

- Reintroduced S10 through the refactored state-machine path after S21
  `combined` and S21 `contractors-only` were green.
- Rebuilt and launched the S10 driver on port `4949`.
- Drained inherited old S10 queue rows with a UI-triggered `sync-only`
  preflight before starting mutation regression.
- Hardened `cleanup-only` replay:
  - fixed the contractor replay branch to use the `cleanup_only` reason;
  - added semicolon-delimited `-CleanupLedgerPaths` normalization so
    `pwsh -File` can pass multiple ledgers reliably;
  - fixed replay-ledger mutation enumeration over generic `List[object]`;
  - made quantity, photo, and contractor cleanup helpers idempotent when a
    previously accepted ledger is already locally and remotely clean.

### Accepted Evidence

- S10 sync-only preflight/drain:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-sync-only-preexisting-drain/summary.json`
- S10 daily-entry-only:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-daily-entry-only-initial/summary.json`
- S10 quantity-only:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-quantity-only-initial/summary.json`
- S10 photo-only:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-photo-only-initial/summary.json`
- S10 contractors-only:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-contractors-only-initial/summary.json`
- S10 combined:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-combined-initial/summary.json`
- S21 cleanup-only replay:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-cleanup-only-replay-accepted-ledgers-idempotent/summary.json`

All accepted summaries report `passed=true`, `failedActorRounds=0`,
`runtimeErrors=0`, `loggingGaps=0`, `queueDrainResult=drained`,
`blockedRowCount=0`, `unprocessedRowCount=0`, `maxRetryCount=0`, and
`directDriverSyncEndpointUsed=false`.

### Non-Acceptance Artifacts Preserved

- First cleanup replay launch failed before execution because `pwsh -File`
  flattened multiple cleanup ledger paths into positional arguments:
  `20260418-s21-cleanup-only-replay-accepted-ledgers`.
- Second cleanup replay exposed already-clean ledger idempotency gaps:
  `20260418-s21-cleanup-only-replay-accepted-ledgers-after-enumeration-fix`.

### Verification

- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`
- PowerShell parser checks for:
  - `tools/sync-soak/Flow.CleanupOnly.ps1`
  - `tools/sync-soak/Flow.Quantity.ps1`
  - `tools/sync-soak/Flow.Photo.ps1`
  - `tools/sync-soak/Flow.Contractors.ps1`
  - `tools/enterprise-sync-soak-lab.ps1`
  - `tools/enterprise-sync-concurrent-soak.ps1`
- Final live S21 and S10 `/driver/change-log` checks returned `count=0`,
  `unprocessedCount=0`, `blockedCount=0`, and `maxRetryCount=0`.

### Current Gate Status

- S21 `sync-only`, `daily-entry-only`, `quantity-only`, `photo-only`,
  `contractors-only`, `combined`, and `cleanup-only` replay are green through
  refactored state-machine modules or replay.
- S10 regression is green for the implemented refactored flows:
  daily-entry, quantity, photo, contractors, and combined.
- Still open by spec intent: MDOT 1126 typed-signature/form-backed mutation
  flow, broader file-backed exports/documents, role/account sweeps,
  storage/RLS denial expansion, failure injection, backend/device overlap,
  staging, and scale/headless actors.

### Next Implementation Slice

- Implement the MDOT 1126 typed-signature flow from `/report/:entryId` as the
  smallest file-backed form/signature lane.
- Expected proof tables: `form_responses`, `signature_files`, and
  `signature_audit_log`.
- Expected storage path: `signatures/{companyId}/{projectId}/{id}.png`.
- Keep export/document/pay-app file-backed flows behind the signature proof.

## 2026-04-18 - MDOT 1126 Typed-Signature Flow

### What Changed

- Added the refactored `mdot1126-signature-only` flow under
  `tools/sync-soak/`.
- Wired the flow through `tools/enterprise-sync-soak-lab.ps1`,
  `tools/enterprise-sync-concurrent-soak.ps1`, cleanup-only replay, and the
  S10 regression catalog.
- Extended driver data-sync policy so the harness can query and
  ledger-clean `signature_files` and `signature_audit_log` through existing
  production driver seams.
- Fixed soft-delete push for signature tables: they support `deleted_at` but
  intentionally do not have `deleted_by`, so their adapters now omit
  `deleted_by` from remote tombstone payloads.
- Hardened cleanup replay for already-soft-deleted ledger rows with pending
  `change_log` residue and made signature storage cleanup prove/delete/absence
  even during idempotent replay.
- Hardened Sync Dashboard measurement to retry the UI sync button when pending
  rows remain and no new sync has started after the first tap.

### Recovery Evidence

- Failed signed run `20260418-s21-mdot1126-signature-nav-select-submit`
  exposed the signature-table `deleted_by` remote schema mismatch during
  cleanup.
- Rebuilt S21 on port `4948` after the fix and replayed the failed signed
  ledger cleanly:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signed-ledger-cleanup-replay-after-deletedby-fix/summary.json`.
- A later failed fresh run,
  `20260418-s21-mdot1126-signature-accepted-after-deletedby-fix`, exposed the
  immediate second-sync timing gap; its ledger was recovered by cleanup-only:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-fresh-failed-ledger-cleanup-replay-with-sync-retry/summary.json`.

### Accepted Evidence

- S21 MDOT 1126 typed-signature:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-accepted-with-cleanup-sync-retry/summary.json`
- S21 cleanup-only replay of accepted MDOT ledger:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-cleanup-only-replay-accepted-ledger/summary.json`
- S10 MDOT 1126 typed-signature regression:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot1126-signature-regression-with-cleanup-sync-retry/summary.json`
- S10 pre-MDOT residue drain:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-pre-mdot-residue-sync-only/summary.json`
- S21 post-S10 MDOT residue drain:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-post-s10-mdot-residue-sync-only/summary.json`

All accepted summaries report `passed=true`, `failedActorRounds=0`,
`runtimeErrors=0`, `loggingGaps=0`, `queueDrainResult=drained`,
`blockedRowCount=0`, `unprocessedRowCount=0`, `maxRetryCount=0`, and
`directDriverSyncEndpointUsed=false`. Accepted MDOT ledgers prove
`form_responses`, `signature_files`, `signature_audit_log`, storage download,
ledger-owned cleanup, storage delete, and storage absence.

### Verification

- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`
- `flutter test test/features/sync/engine/supabase_sync_contract_test.dart test/features/sync/adapters/adapter_config_test.dart`
- `flutter test test/core/driver/driver_data_sync_policy_test.dart`
- `flutter test test/features/sync/engine/push_handler_test.dart test/features/sync/engine/sync_engine_delete_test.dart`
- Rebuilt S21 driver on `RFCNC0Y975L` port `4948`.
- Rebuilt S10 driver on `R52X90378YB` port `4949`.

### Current Gate Status

- S21 MDOT 1126 typed-signature: green.
- S21 cleanup-only replay for accepted MDOT ledger: green.
- S10 MDOT 1126 typed-signature regression: green.
- Still open by spec intent at this checkpoint: MDOT 1126 expanded field/row
  coverage, MDOT 0582B, MDOT 1174R, generic builtin form exports,
  saved-form/gallery lifecycle sweeps, role/account sweeps, broader
  storage/RLS denial, failure injection, backend/device overlap, staging, and
  scale/headless actors. A later checkpoint below accepts MDOT 1126 expanded
  fields/rows on S21.

## 2026-04-18 - Spec Refresh And Next Implementation Queue

### What Changed

- Updated the active Codex plan index, S21 harness recovery plan, MDOT 1126
  typed-signature plan, UI/RLS implementation TODO, and sync-soak audit task
  list so they reflect the accepted MDOT 1126 typed-signature S21/S10 evidence
  instead of treating all form/signature work as open.
- Split the remaining form/signature work into ordered lanes:
  MDOT 1126 expanded fields/rows, MDOT 0582B, MDOT 1174R, builtin form
  exports, and saved-form/gallery lifecycle sweeps.
- Promoted four spec-review hardening items ahead of new form work:
  fail-fast mutation preflight on non-empty queue, no inferred signature
  storage path proof, fail-closed cleanup when a required signature
  `remotePath` is missing, and focused harness self-tests for those contracts.
- Kept signature integrity count drift open as a root-cause item before broad
  form/signature scale-up.

### Current Next Slice

- Implement the MDOT typed-signature harness-contract hardening first, then
  re-run parser/self-tests.
- After that, investigate signature integrity drift and proceed to MDOT 1126
  expanded field/row flow.

### Harness Contract Hardening Result

- `Wait-SoakMdot1126SignatureRemotePath` now fails closed when
  `signature_files.remote_path` never appears instead of returning the row for
  later inference.
- `Invoke-SoakMdot1126SignatureLedgerCleanup` now supports
  `-RequireStorageRemotePath`; normal accepted cleanup and cleanup-only replay
  use it so a malformed signature ledger cannot skip storage delete/absence
  proof.
- Failure-recovery cleanup still omits `-RequireStorageRemotePath`, allowing
  row cleanup after pre-upload failures where no storage object should exist.
- Harness self-tests now cover `mdot1126-signature-only` flow wiring,
  dirty-preflight detection, signatures bucket absence proof, no inferred
  remote path, missing required `remotePath` rejection, and mismatched ledger
  `remotePath` rejection.

Verification:

- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`

### Signature Integrity Drift Root Cause

- The broader `signature_files` / `signature_audit_log` integrity drift seen
  in MDOT live logs was traced to a local/remote schema mismatch, not to the
  accepted per-ledger signature mutation itself.
- Supabase allows `signature_files.local_path` to be null because a signature
  row created on one device has no local filesystem path on another device
  until that object is downloaded or cached.
- The local SQLite schema required `signature_files.local_path TEXT NOT NULL`,
  so pulling remote signature metadata from other devices could fail before
  the local signature/audit row counts converged.
- Local schema v61 now rebuilds `signature_files` with nullable `local_path`,
  preserves existing `signature_files` and `signature_audit_log` rows, and
  reinstalls signature indexes, change-log triggers, and immutability triggers.

Verification:

- `flutter test test/core/database/migration_v61_test.dart`
- `flutter test test/features/sync/engine/integrity_checker_test.dart test/features/sync/adapters/adapter_config_test.dart`
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`

Still open at this checkpoint:

- Rebuild/upgrade live S21 and S10, run a post-v61 signature pull/sync pass,
  and confirm the broader signature integrity drift no longer appears in the
  device logs.
- Continue implementation with MDOT 1126 expanded fields/rows, then MDOT 0582B,
  MDOT 1174R, form exports, and saved-form/gallery lifecycle sweeps. A later
  checkpoint below accepts MDOT 1126 expanded fields/rows on S21.

## 2026-04-18 - Post-v61 S21 Proof And MDOT 1126 Expanded Start

### What Changed

- Rebuilt the S21 driver after the local schema v61 signature migration.
- Confirmed `/diagnostics/sync_runtime` reported schemaVersion 61.
- The rebuild exposed a local backlog of remote signature metadata rows:
  `signature_files` and `signature_audit_log` inserts that previously could
  not converge under the old non-null `signature_files.local_path` schema.
- Ran a refactored S21 `sync-only` pass through the Sync Dashboard UI to drain
  that backlog.
- Implemented the `mdot1126-expanded-only` refactored flow under
  `tools/sync-soak/`, reusing the accepted MDOT signature creation, signing,
  storage proof, and ledger cleanup path while adding header, rainfall, SESC
  measure, and remarks marker proof.
- Mounted the rainfall-events editor in the report-attached MDOT 1126
  inspection section so the current workflow shell has a real UI surface for
  rainfall row proof.

### Accepted Evidence

- S21 post-v61 signature backlog sync-only:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-post-v61-signature-backlog-sync-only/summary.json`
- Acceptance facts:
  `passed=true`, `failedActorRounds=0`, `runtimeErrors=0`, `loggingGaps=0`,
  `queueDrainResult=drained`, final queue empty, and
  `directDriverSyncEndpointUsed=false`.

### Non-Acceptance Evidence Preserved

- `20260418-s21-mdot1126-expanded-initial` failed because the harness still
  expected old step next-buttons that are not mounted in the report-attached
  workflow shell.
- `20260418-s21-mdot1126-expanded-after-rainfall-ui` failed waiting for
  `mdot1126_rainfall_0_inches` after tapping `mdot1126_rainfall_add`.
  Cleanup soft-deleted the draft form response, synced cleanup through the
  Sync Dashboard UI, and ended with an empty S21 queue.
- The current root cause is harness visibility, not a storage or sync failure:
  the add button existed in the widget tree while the screen was still
  positioned around the header section, and the driver tap endpoint does not
  prove the keyed widget is visible before dispatching a tap.

### Verification

- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`
- `dart analyze lib/features/forms/presentation/screens/mdot_1126_steps.dart`
- S21 driver rebuild with:
  `pwsh -NoProfile -File tools/start-driver.ps1 -Platform android -DeviceId RFCNC0Y975L -DriverPort 4948 -Timeout 180 -ForceRebuild`

### Current Gate Status

- S21 post-v61 signature backlog drain: green.
- S10 post-v61 cross-device signature proof: open.
- MDOT 1126 expanded flow: accepted on S21 in the next checkpoint below.
- Next slice: S10 post-v61 cross-device signature proof, then MDOT 0582B,
  MDOT 1174R, form exports, and saved-form/gallery lifecycle sweeps.

## 2026-04-18 - S21 MDOT 1126 Expanded Accepted

### What Changed

- Hardened `tools/sync-soak/Flow.Mdot1126Expanded.ps1` so the expanded lane
  opens the newly-created form directly, navigates by section title/key instead
  of old next-buttons, proves rainfall and SESC measure rows, and orders SESC
  measure edits before the workflow auto-advances away from the section.
- Hardened the MDOT signature helper so the expanded lane can submit from a
  signature-ready screen even when the workflow nav header is offscreen.
- Added an initial rainfall row to the MDOT 1126 schema so the report-attached
  form has a stable keyed row for the first rainfall proof.
- Tightened driver tap/tap-text routes to target visible, preferred tappable
  controls instead of accepting broad offscreen widget-tree matches.

### Accepted Evidence

- S21 MDOT 1126 expanded fields/rows:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-signature-ready-or-nav/summary.json`.
- Acceptance facts:
  `passed=true`, `failedActorRounds=0`, `runtimeErrors=0`, `loggingGaps=0`,
  `queueDrainResult=drained`, `blockedRowCount=0`, `unprocessedRowCount=0`,
  `maxRetryCount=0`, `directDriverSyncEndpointUsed=false`, and final S21
  `/driver/change-log` empty.
- Mutation UI sync artifact:
  `round-1-mdot1126-expanded-mutation-ui-sync.json` reported
  `triggeredThroughUi=true`, `directDriverSyncEndpointUsed=false`,
  `observedSyncing=true`, `startChangeLog.count=13`, and
  `finalChangeLog.count=0`.
- The pre-sync local queue included `form_responses:insert`,
  `form_responses:update`, `signature_files:insert`, and
  `signature_audit_log:insert`.
- The ledger proved post-sync remote rows, typed-signature storage download
  from the `signatures` bucket, ledger-owned cleanup for `form_responses`,
  `signature_files`, and `signature_audit_log`, storage delete, storage
  absence, and UI-triggered cleanup sync.

### Verification

- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`
- `dart analyze lib/features/forms/data/services/mdot_1126_schema.dart test/features/forms/data/services/mdot_1126_schema_test.dart test/features/forms/presentation/screens/mdot_1126_steps_test.dart lib/core/driver/driver_widget_inspector.dart lib/core/driver/driver_interaction_handler_gesture_routes.dart`
- `flutter test test/features/forms/data/services/mdot_1126_schema_test.dart test/features/forms/presentation/screens/mdot_1126_steps_test.dart`

### Current Gate Status

- S21 MDOT 1126 expanded fields/rows: green.
- S21 post-v61 signature backlog drain: green.
- S10 post-v61 cross-device signature proof: open.
- Remaining spec lanes at this checkpoint: MDOT 0582B, MDOT 1174R, generic
  builtin form exports, saved-form/gallery lifecycle sweeps, role/account
  sweeps, broader storage/RLS denial, failure injection, backend/device
  overlap, staging, and scale/headless actors. A later checkpoint below accepts
  the MDOT 0582B mutation lane on S21; MDOT 0582B export/storage proof remains
  open.

## 2026-04-18 - S21 MDOT 0582B Accepted

### What Changed

- Added `tools/sync-soak/Flow.Mdot0582B.ps1` as the refactored
  `mdot0582b-only` flow.
- Wired `-Flow mdot0582b-only` through `tools/enterprise-sync-soak-lab.ps1`.
- Added generic `form_responses` ledger cleanup support for cleanup-only replay
  readiness.
- Added harness self-test coverage for the new flow wiring, report-attached
  form creation keys, standards/proctor/test marker proof, and
  `form_responses` cleanup-only dispatch.

### Accepted Evidence

- S21 MDOT 0582B form-response mutation:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-accepted-initial/summary.json`.
- Acceptance facts:
  `passed=true`, `failedActorRounds=0`, `runtimeErrors=0`, `loggingGaps=0`,
  `queueDrainResult=drained`, `blockedRowCount=0`, `unprocessedRowCount=0`,
  `maxRetryCount=0`, `directDriverSyncEndpointUsed=false`, and final S21
  `/driver/change-log` empty.
- Mutation sync used the Sync Dashboard UI and proved pre-sync local
  `change_log` rows for `form_responses`.
- Local and remote proofs covered report-attached creation, header job/route/
  remarks/signature markers, chart standards, operating standards, HMA proctor
  row, quick-test row, and `deleted_at = null` before cleanup.
- Cleanup was ledger-owned, synced through the Sync Dashboard UI, and proved
  remote `form_responses` soft-delete.

### Non-Acceptance Evidence Preserved

- `20260418-s21-mdot0582b-initial` proved header/proctor progress but failed
  because the harness collapsed the quick-test section after proctor auto-opened
  it.
- `20260418-s21-mdot0582b-after-test-section-fix` proved full local mutation
  but failed remote JSON parsing.
- `20260418-s21-mdot0582b-after-remote-json-proof` proved local and remote
  marker values but failed on PowerShell PSCustomObject property-count handling.
- Each failed diagnostic run cleaned up through UI sync and ended with an empty
  S21 queue.

### Verification

- PowerShell parser checks for:
  - `tools/sync-soak/Flow.Mdot0582B.ps1`
  - `tools/sync-soak/Flow.CleanupOnly.ps1`
  - `tools/test-sync-soak-harness.ps1`
  - `tools/enterprise-sync-soak-lab.ps1`
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`
- Read-only S21 queue check after the accepted run returned `count=0`,
  `unprocessedCount=0`, `blockedCount=0`, and `maxRetryCount=0`.

### Current Gate Status

- S21 MDOT 0582B form-response mutation: green.
- MDOT 0582B PDF/export and storage-byte proof: open in the generic form
  export lane.
- S10 regression for MDOT 1126 expanded and MDOT 0582B: open.
- Next implementation lanes: S10 post-v61 cross-device signature proof,
  MDOT 1174R, builtin form exports, saved-form/gallery lifecycle sweeps,
  role/account sweeps, broader storage/RLS denial, failure injection,
  backend/device overlap, staging, and scale/headless actors.

## 2026-04-18 - MDOT 1174R Implementation Started, Not Accepted

### What Changed

- Added `tools/sync-soak/Flow.Mdot1174R.ps1` as the initial refactored
  `mdot1174r-only` lane.
- Wired `-Flow mdot1174r-only` through `tools/enterprise-sync-soak-lab.ps1`
  and `tools/enterprise-sync-concurrent-soak.ps1`.
- Added static harness checks for 1174R report-attached creation, marker proof
  coverage, and flow wiring.
- Added `form_workflow_scroll_view` and 1174R section-header keys so the driver
  can target the real workflow shell on compact S21 layouts.
- Hardened `/driver/scroll-to-key` to search from the top after a downward pass
  misses a target above the current scroll offset.
- Updated 1174R section selection to prefer the stable section-header key and
  fall back to the compact nav pill. This targets the latest S21 failure where
  `mdot1174_section_header_qa` was mounted but `mdot1174_workflow_nav_qa` was
  not.

### Non-Acceptance Evidence Preserved

- `20260418-s21-mdot1174r-initial` created a draft and proved failure cleanup,
  but did not open the created form before editing.
- `20260418-s21-mdot1174r-after-open-created-form` opened the form but still
  failed on one-way scroll visibility for header fields.
- `20260418-s21-mdot1174r-after-header-nav-skip` reached later section
  navigation but failed on one-way scroll to the placement nav.
- `20260418-s21-mdot1174r-after-auto-advance` failed on placement field
  visibility after mounted direct text changes.
- `20260418-s21-mdot1174r-after-mounted-text` exposed a runtime-log failure
  while waiting for QA after partial Air/Slump entry:
  Flutter `Duplicate GlobalKey` plus detached `RenderEditable` assertions.
  Restart recovery later proved the generated row was locally and remotely
  soft-deleted and the S21 queue returned empty.
- `20260418-s21-mdot1174r-after-section-headers` failed switching to Placement
  via section-header key; cleanup passed and final queue drained.
- `20260418-s21-mdot1174r-after-bidirectional-scroll` failed switching from
  Air/Slump to QA because the compact workflow nav was unmounted at the current
  scroll position; cleanup passed and final queue drained.

### Verification

- PowerShell parser checks for:
  - `tools/sync-soak/Flow.Mdot1174R.ps1`
  - `tools/test-sync-soak-harness.ps1`
  - `tools/enterprise-sync-soak-lab.ps1`
  - `tools/enterprise-sync-concurrent-soak.ps1`
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`
- `dart analyze lib/core/driver/driver_interaction_handler_gesture_routes.dart lib/shared/testing_keys/toolbox_keys.dart lib/shared/testing_keys/testing_keys.dart lib/features/forms/presentation/screens/mdot_1174r_form_screen.dart lib/features/forms/presentation/screens/mdot_1174r_body.dart`
- S21 final `/driver/change-log` after the latest diagnostic run:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`.

### Current Gate Status

- MDOT 1174R code/harness lane: implemented enough for live diagnostics.
- S21 MDOT 1174R acceptance: open.
- Current blocker: compact workflow section switching for 1174R row sections.
  A first harness patch now prefers section headers over unmounted nav pills;
  the next slice is a live S21 rerun to prove whether that closes Air/Slump ->
  QA without reintroducing GlobalKey/RenderEditable runtime errors.

## 2026-04-18 - MDOT 1174R Expanded-Body Sentinel Hardening

### Latest Non-Acceptance Evidence

- `20260418-s21-mdot1174r-after-header-first-selection` remained
  non-acceptance evidence; cleanup passed and final queue drained.
- `20260418-s21-mdot1174r-after-first-field-scroll-selection` progressed
  farther but failed opening Quantities; cleanup passed and final queue
  drained.
- `20260418-s21-mdot1174r-after-title-fallback-selection` progressed to
  Remarks but remained non-acceptance evidence; cleanup passed and final queue
  drained.
- `20260418-s21-mdot1174r-after-expanded-sentinel` progressed through
  QA/comments, then failed opening Quantities after QA edits. Metrics remained
  fail-loud and clean after recovery: `runtimeErrors=0`, `loggingGaps=0`,
  `queueDrainResult=drained`, `blockedRowCount=0`, `unprocessedRowCount=0`,
  `maxRetryCount=0`, and `directDriverSyncEndpointUsed=false`.

### Current Patch

- Moved `AppFormSection.expandedKey` from the chevron icon onto the expanded
  body wrapper so `mdot1174_section_expanded_*` proves mounted section content,
  not only an icon repaint.
- Hardened `/driver/text` so a key with no mounted `EditableText` descendant
  returns a 409 instead of silently succeeding without changing data.

### Actionable Checklist

- [x] Keep MDOT 1174R in the refactored `mdot1174r-only` lane only; do not use
  legacy all-modes proof.
- [x] Preserve ledger-owned cleanup and UI-triggered cleanup sync on every
  failed diagnostic run.
- [x] Update the spec-facing docs with MDOT 1174R status and the current
  Quantities/body-proof blocker.
- [ ] Run formatter, harness parser tests, and Dart analyzer for the patched
  driver/form files.
- [ ] Rebuild the S21 driver so the expanded-body sentinel and text-route
  hardening are live on-device.
- [ ] Clear logs and confirm S21 `/driver/change-log` is empty.
- [ ] Rerun S21 `mdot1174r-only`.
- [ ] Accept only when the artifact proves local markers, local pre-sync
  `change_log`, remote `form_responses`, ledger cleanup, UI-triggered cleanup
  sync, final empty queue, zero runtime/log gaps, and no direct `/driver/sync`.

## 2026-04-18 - MDOT 1174R Red-Screen Stop And Artifact Hygiene Handoff

### Additional Non-Acceptance Evidence

- `20260418-s21-mdot1174r-after-expanded-body-sentinel` remained
  non-acceptance evidence. It kept runtime/logging clean and drained cleanup,
  but section selection could still collapse or miss the mounted QA body.
- `20260418-s21-mdot1174r-after-section-open-only` re-exposed the
  row-section runtime failure: duplicate GlobalKey plus detached render-object
  assertions, queue residue, and failed cleanup navigation. The later
  `20260418-s21-mdot1174r-residue-recovery-sync-only` run recovered through the
  refactored UI-triggered `sync-only` lane.
- `20260418-s21-mdot1174r-after-no-animated-size-keepalive` still failed with
  duplicate GlobalKey/detached render-object runtime errors and queue residue
  after removing section-body animation and keeping repeated-row composer state
  alive.
- `20260418-s21-mdot1174r-visible-text-only` is the latest clean
  non-acceptance diagnostic. It had `runtimeErrors=0`, `loggingGaps=0`,
  `queueDrainResult=drained`, `blockedRowCount=0`, `unprocessedRowCount=0`,
  `maxRetryCount=0`, and `directDriverSyncEndpointUsed=false`; cleanup passed
  and the final live queue drained. It failed because `/driver/scroll-to-key`
  could not bring `mdot1174_air_slump_pairs_composer_left_time` into visible
  range even though the Air section body and target key were mounted in the
  widget tree.
- `20260418-s21-mdot1174r-after-ensure-visible-scroll` is the latest
  red-screen stop and must not be treated as acceptance. It failed loudly during
  `mdot1174r-fields-and-rows` with `failureClassification=runtime_log_error`,
  `runtimeErrors=27`, duplicate GlobalKey fingerprints, detached render-object
  assertions, `queueDrainResult=residue_detected`, and local `form_responses`
  queue residue. The harness correctly stopped on runtime evidence.
- `20260418-s21-mdot1174r-redscreen-residue-recovery-sync-only` recovered that
  residue through the refactored Sync Dashboard UI path. It passed with
  `failedActorRounds=0`, `runtimeErrors=0`, `loggingGaps=0`,
  `queueDrainResult=drained`, `blockedRowCount=0`, `unprocessedRowCount=0`,
  `maxRetryCount=0`, and `directDriverSyncEndpointUsed=false`; the live S21
  `/driver/change-log` was empty afterward.

### Current Code State

- `AppFormSection.expandedKey` now sits on the mounted expanded body wrapper.
- `/driver/text` now requires a visible mounted `EditableText`; hidden or
  non-editable targets return 409.
- Section-body `AnimatedSize` has been removed to reduce rebuild/reparent
  churn around form rows.
- `FormRepeatedRowComposer` keeps state alive while mounted so draft row
  controllers survive intra-section scrolling.
- `/driver/scroll-to-key` now tries `Scrollable.ensureVisible` before manual
  scanning. This helped target mounted fields directly, but the latest live run
  shows the deeper row-section GlobalKey/state ownership issue is still active.

### Lint Guardrails Added

- Added `form_workflow_sentinel_contract_sync` to keep
  `AppFormSection.expandedKey` on mounted expanded body content and prevent a
  regression back to header/icon-only proof.
- Added `no_animated_size_in_form_workflows` to ban `AnimatedSize`,
  `AnimatedSwitcher`, and `AnimatedCrossFade` around form workflow body
  surfaces with keyed editable content.
- Removed the remaining `AnimatedSize` body wrapper from `FormAccordion` after
  the new rule caught it.
- Extended sync lint allowlists for approved debug/repair owners and tightened
  the v61 migration test queries with explicit `deleted_at IS NULL` filters so
  these changes do not leave ERROR-level custom-lint drift.
- Verification:
  - `dart analyze` on the new lint rules, sync lint allowlist edits, and v61
    migration test.
  - `dart test` for the new lint rule tests.
  - `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`.
  - `flutter test test/core/database/migration_v61_test.dart`.
  - Full `dart run custom_lint` now has no ERROR-level findings from this lane;
    six WARNING-level findings remain open in existing files.

### Artifact Cleanup Policy

- Added `tools/sync-soak/Export-SoakResultIndex.ps1` to condense raw run
  folders into a human-readable Markdown report and machine-readable JSON
  report before cleanup. Current generated reports:
  - `.codex/reports/2026-04-18-enterprise-sync-soak-result-index.md`
  - `.codex/reports/2026-04-18-enterprise-sync-soak-result-index.json`
  - `.codex/reports/2026-04-18-all-test-results-result-index.md`
  - `.codex/reports/2026-04-18-all-test-results-result-index.json`
  These cover 55 runs, 15 passes, 40 failures, and failure groups for
  `change_log_proof_failed`, `driver_or_sync_error`, `runtime_log_error`,
  `unprocessed_change_log_rows`, `widget_tap_not_found`, and
  `widget_wait_timeout`.
- The full raw-tree index covers 165 runs, 76 passes, and 89 failures before
  cleanup. It also preserves older `cleanup_failed`,
  `queue_not_drained_or_sync_not_observed`, and `unknown_failure` classes.
- `tools/enterprise-sync-soak-lab.ps1` now writes a compact result index into
  each future run folder automatically after `summary.json` is finalized.
- Preserve in docs/checkpoints, not by keeping every raw folder: artifact id,
  pass/fail, failure class, runtime fingerprints, queue/cleanup outcome, and
  direct-sync status.
- Keep raw artifacts for the latest accepted run, the latest blocker run, and
  one representative run per distinct failure class.
- Keep `summary.json`, failure screenshots, failure debug summaries/errors,
  `timeline.json`, mutation ledgers, and cleanup proof when they are the only
  evidence for a distinct behavior.
- Delete duplicate screenshot/logcat/widget-tree bulk after the facts are
  recorded.
- Do not delete the first artifact for a new runtime signature until the
  signature is captured here and a later run proves the fix.
- Local cleanup scope at handoff:
  - `build/` was generated and about 13 GB.
  - `releases/android/debug/` held three debug APK copies of roughly 315 MB
    each plus tiny manifests/device-state files.
  - `.dart_tool/` was generated cache and about 5 GB; delete only when a full
    `flutter pub get`/rebuild is acceptable.
  - `.claude/test-results/` was about 1.2 GB overall; the 2026-04-18
    `enterprise-sync-soak` subset was 54 run folders, 3,676 files, and about
    523 MB.
  - S21/S10 Downloads include personal/non-harness files. Only remove clearly
    generated Field Guide debug/export/conflict artifacts by exact path; do not
    bulk-clear Downloads and do not clear app data unless intentionally
    resetting device sync state.
- Post-audit cleanup completed on 2026-04-18:
  - compact reports were preserved under `.codex/reports/` before deleting raw
    duplicate evidence;
  - ignored raw `.claude/test-results/2026-04-18` residue was removed after the
    all-results index captured the failure classes;
  - generated local artifacts were removed: `build/`, `.dart_tool/`,
    `android/.gradle`, root Flutter/debug logs, debug APKs, build manifest, and
    generated device-state files;
  - post-cleanup local verification showed `.dart_tool`, `build`, and
    `android/.gradle` absent, `releases/android/debug` reduced to `.gitkeep`,
    and tracked historical `.claude/test-results` evidence retained at
    497 files / 11.26 MB;
  - S21 `/sdcard/Download` cleanup removed only exact generated files:
    `device-ci.db` plus `conflict_*` DB/shm/wal files;
  - S10 cleanup found no exact Field Guide generated debug artifact candidate,
    so S10 Downloads and app data were left intact.

### Next Session Checklist

- [x] Recover the S21 queue through the refactored `sync-only` flow and Sync
  Dashboard UI only; do not call `/driver/sync`.
- [x] Confirm `/driver/change-log` returns `count=0`, `unprocessedCount=0`,
  `blockedCount=0`, and `maxRetryCount=0` before any new mutation run.
- [ ] Audit MDOT 1174R repeated-row/section key ownership before retrying.
  The active blocker is duplicate GlobalKey/detached render-object state during
  row-section entry, not Supabase sync.
- [ ] Add artifact-retention controls before another long soak loop so duplicate
  failures keep compact summaries instead of full screenshots/logcat/widget
  tree bundles.
- [ ] Rerun S21 `mdot1174r-only` only after the state/key fix and clean
  preflight. Acceptance still requires local markers, pre-sync local
  `change_log`, post-sync remote `form_responses`, ledger-owned cleanup,
  UI-triggered cleanup sync, final empty queue, zero runtime/log gaps, and no
  direct `/driver/sync`.

# 2026-04-17 S21 Soak Harness Audit And Recovery Plan

## Current Decision

Pause full S21 all-modes soak reruns.

The current device soak harness is useful for finding bugs, but it is not yet
structured enough to be a reliable acceptance gate. Repeated all-modes reruns
have mixed app defects, driver-flow fragility, cleanup residue, and harness
observability gaps into the same failure stream. The refactored S21 gates,
S10 implemented-flow regression, S21 cleanup-only replay, and MDOT 1126
typed-signature form/signature lane are now green. Keep the legacy all-modes
runner out of acceptance evidence; the remaining work should continue through
focused refactored flows before optional emulator actors, headless app-sync
actors, backend overlap, role churn, or 15-20 user workload simulation are
claimed. Latest hardening: MDOT signature cleanup now fails closed on missing
or mismatched storage `remotePath`, and local database v61 makes
`signature_files.local_path` nullable to match Supabase so cross-device
signature rows can pull. S21 post-v61 signature backlog drain is now green;
S10 post-v61 cross-device integrity proof remains open. MDOT 1126 expanded
fields/rows are now accepted on S21 through the refactored
`mdot1126-expanded-only` flow, and MDOT 0582B form-response mutation is
accepted on S21 through `mdot0582b-only`. MDOT 0582B export/storage proof
remains open. MDOT 1174R is implemented/wired as `mdot1174r-only` but not
accepted. The clean `visible-text-only` diagnostic proved the remaining scroll
visibility failure without runtime/logging/queue residue; the follow-up
`after-ensure-visible-scroll` run failed loudly on a red screen with duplicate
GlobalKey/detached render-object runtime errors and local `form_responses`
queue residue. The next work is S21 recovery through UI-triggered `sync-only`,
artifact pruning after docs preserve the failure facts, and MDOT 1174R
row-section key/state ownership review before another acceptance attempt.
After MDOT 1174R acceptance, continue with builtin form exports and
saved-form/gallery lifecycle sweeps.

## Evidence Baseline

Artifact root:

`.claude/test-results/2026-04-17/enterprise-sync-soak/`

Most relevant latest runs:

- `20260417-s21-strictlog-stablekey-all-modes`
  - Failed loudly after strict log gating.
  - `summary.json`: `passed=false`, `failedActorRounds=1`,
    `runtimeErrors=1`, `loggingGaps=0`, `queueDrainResult=drained`.
  - Failure class: `runtime_log_error`.
  - Runtime signature: `FlutterError: Multiple widgets used the same GlobalKey`
    with `InheritedGoRouter(goRouter: Instance of 'GoRouter')`.
- `20260417-s21-strictlog-cleanup-sync`
  - Failed cleanup sync with queue residue after invalid cleanup payload.
  - Root cause: cleanup wrote `deleted_by = enterprise-soak-cleanup`, but
    remote schema expects UUID.
- `20260417-s21-strictlog-cleanup-sync-rerun`
  - Failed cleanup sync with conflict/newer-version state.
  - Dashboard showed "newer changes were kept automatically."
  - Recovery used direct `/driver/sync`; this is not acceptance evidence.
- `20260417-s21-post-cleanup-strict-drain`
  - Passed after recovery.
  - `passed=true`, `queueDrainResult=drained`, `runtimeErrors=0`,
    `loggingGaps=0`.
- `20260417-s21-fullscreen-notransition-strict-all-modes`
  - Failed loudly.
  - `summary.json`: `passed=false`, `failedActorRounds=1`,
    `queueDrainResult=residue_detected`, `unprocessedRowCount=2`,
    `runtimeErrors=1`, `loggingGaps=0`.
  - Failure was not a captured Flutter runtime log error. The script timed out
    waiting for `photo_name_dialog`.
  - Screenshot showed the photo source bottom sheet still open on
    "Choose from Gallery."

## Failure Audit

The failures are not one defect. They break down into these groups.

### 1. Harness/Driver Readiness And Endpoint Gaps

Observed examples:

- Driver port unavailable: `127.0.0.1:4948` refused.
- Driver endpoint missing or app not ready: `404 Not Found`, `503 no live context`.
- Required widgets not found because the app was still transitioning or on a
  stale route.

Why this matters:

- These are setup/driver health failures, not sync acceptance failures.
- The harness currently records them as generic `driver_or_sync_error`.
- They should fail loudly with a dedicated `driver_readiness_failure` class and
  should not mutate data.

Required fixes:

- Add a preflight phase that validates each actor before any mutation:
  `/driver/ready`, `/driver/current-route`, `/diagnostics/screen_contract`,
  `/driver/change-log`, screenshot, logcat capture, auth context, project
  context.
- If preflight fails, stop before creating rows.
- Record a first-class `driverPreflight` artifact per actor.

### 2. UI Flow Step Fragility

Observed examples:

- `entry_editor_screen` timeout.
- `entry_editor_scroll` not found.
- `sync_dashboard_screen` or `sync_now_full_button` not found.
- `bid_item_picker_sheet` timeout.
- `quantity_dialog_save` not found.
- `quantity_notes_field` not found.
- `photo_name_dialog` timeout while the source sheet remained open.

Why this matters:

- The harness has monolithic flow functions. When a step fails, artifacts do not
  consistently show which UI state was visible immediately before and after the
  action.
- Current wait/tap/text calls do not consistently capture per-step screenshots,
  route, widget tree, visible text, and log deltas.

Required fixes:

- Replace raw `Invoke-DriverJson` calls inside flows with a `StepRunner`.
- Every step records:
  - step name,
  - action type,
  - target key/text/path,
  - current route before and after,
  - screenshot before and after for high-risk steps,
  - screen contract or widget tree on failure,
  - logcat delta or bounded log snapshot,
  - local queue count on failure.
- Failure classes should distinguish:
  - `widget_wait_timeout`,
  - `widget_tap_not_found`,
  - `route_mismatch`,
  - `picker_not_completed`,
  - `sync_not_started`,
  - `sync_queue_residue`.

### 3. Runtime Red Screens

Observed examples:

- `FlutterError: Multiple widgets used the same GlobalKey.`
- Parents described as `InheritedGoRouter(goRouter: Instance of 'GoRouter')`.
- Earlier red-screen notes also included dirty build-scope and
  `_elements.contains(element)` failures.

What improved:

- Strict log gating now correctly fails the run when the captured log contains
  runtime failure signatures.
- Missing log capture is now a failure via `loggingGaps`.

Still missing:

- The failure log scan currently happens after round log capture. It should also
  run against failure logs inside catch blocks.
- Runtime log errors should be deduplicated and summarized so the same
  FlutterError repeated 40 times does not bury the root signature.
- Red-screen detection should not rely only on logcat. The harness should also
  inspect screenshot state and widget tree for `ErrorWidget`.

Required fixes:

- Add `Assert-NoRuntimeErrors` after every high-risk navigation and after every
  failure artifact capture.
- Add screenshot/widget-tree red-screen classifier:
  - `flutter_error_widget_visible`,
  - `blank_or_black_screen`,
  - `route_unknown`,
  - `driver_screen_unknown`.
- Persist runtime signature fingerprint:
  `category + first FlutterError line + first framework stack frame`.

### 4. Queue Residue And Cleanup Failures

Observed examples:

- Generated `entry_quantities` and `photos` rows remained after failed runs.
- `daily_entries.activities` was overwritten repeatedly by soak text.
- Cleanup initially used an invalid non-UUID `deleted_by`.
- Later cleanup updates conflicted with already-synced newer remote versions.
- Direct `/driver/sync` cleared cleanup residue, but it is not valid acceptance
  evidence because the spec requires UI-triggered sync.

Why this matters:

- Queue drain proves local sync queue health. It does not prove the database was
  returned to its original fixture state.
- The soak has been polluting fixture data with generated quantities, photos,
  and daily-entry activity text.

Required fixes:

- Add a `MutationLedger` before any flow writes:
  - record original values for updates,
  - record generated row IDs,
  - record remote paths,
  - record cleanup actions required,
  - record cleanup status.
- Add a cleanup phase that can run independently:
  - restore original fields,
  - soft-delete generated rows using the authenticated user UUID,
  - delete generated storage objects,
  - sync cleanup through the UI when possible,
  - verify remote rows are restored/deleted,
  - verify storage object absence.
- If cleanup cannot complete, mark the run `cleanup_failed` even if the flow
  itself passed.
- Add a dedicated recovery-only command path that is clearly labeled
  non-acceptance, such as `-RecoveryOnly`.

### 5. Storage Proof And Secret Handling

Observed examples:

- Early storage proof failed with object not found under anon-style proof.
- Service-role storage proof later proved generated photo object downloads.
- Host REST cleanup using the key in `.env.secret` hit Supabase's
  "Forbidden use of secret API key in browser" guard.

Required fixes:

- Split storage proof from backend cleanup.
- Use the app/auth path for normal acceptance proof.
- For cleanup, prefer a local trusted server/script path that uses the correct
  protected environment credentials, not a browser-restricted key path.
- Store cleanup proof as separate artifacts:
  - `storage-object-before.json`,
  - `storage-object-proof.json`,
  - `storage-object-delete.json`,
  - `storage-object-after.json`.

### 6. Script Structure Problem

Current shape:

- `tools/enterprise-sync-soak-lab.ps1` is 1,864 lines.
- It has 36 top-level functions.
- It mixes:
  - actor parsing,
  - driver HTTP client,
  - ADB/logcat,
  - artifact IO,
  - UI flow actions,
  - storage proof,
  - sync measurement,
  - cleanup-like recovery,
  - summary pass/fail logic,
  - parent orchestration.

Why this matters:

- Adding new flows now increases risk because each flow duplicates navigation,
  waiting, screenshots, log capture, queue assertions, and cleanup logic.
- Failures are too often classified as generic `driver_or_sync_error`.
- The script can continue after serious app/runtime failures unless every new
  path remembers to call the same assertions.

## Existing Driver/Debug Reuse Audit

Decision: do not build a third HTTP server for the soak refactor.

The repo already has two intentionally separate HTTP surfaces:

- App-side driver server:
  `lib/core/driver/driver_server.dart`
  - Runs inside the debug driver app through `lib/main_driver.dart`.
  - Binds to the device/app loopback driver port.
  - Owns UI automation, widget inspection, screenshots, local SQLite/change-log
    diagnostics, file/photo injection, actor context, sync runtime, and
    driver-only maintenance endpoints.
  - This is the correct control plane for S21/S10 UI and local-device proof.
- Host-side debug log server:
  `tools/debug-server/server.js`
  - Runs on the workstation at port 3947.
  - Receives structured app logs through `Logger` when `DEBUG_SERVER=true`.
  - Stores log/session artifacts, exposes `/logs`, `/logs/errors`,
    `/logs/summary`, `/sync/status`, and artifact upload/download endpoints.
  - It is also colocated with service-role verification utilities such as
    `tools/debug-server/supabase-verifier.js` and cleanup entrypoint
    `tools/debug-server/run-tests.js`.
  - This is the correct host proof/log/cleanup support surface. It should not
    become the UI driver.

Existing startup scripts already know how to wire both surfaces:

- `tools/start-driver.ps1`
  - Starts the debug log server if needed.
  - Builds/installs the driver app for Android when needed.
  - Adds `DEBUG_SERVER=true` and `DRIVER_PORT`.
  - Sets `adb reverse tcp:3947 tcp:3947` so the device can post logs.
  - Sets `adb forward tcp:<driverPort> tcp:<driverPort>` so the host can call
    the app-side driver.
- `tools/wait-for-driver.ps1`
  - Polls both `/driver/ready` and debug-server `/health`.
- `tools/stop-driver.ps1`
  - Stops app/debug-server processes; Android force-stop still needs to remain
    in the actor preflight/cleanup path because the script's Windows process
    cleanup is not enough for a parked device.

Reusable code and patterns:

- `integration_test/sync/harness/harness_driver_client.dart`
  - Already provides a typed Dart client for `/diagnostics/*`, `/driver/*`,
    UI-triggered Sync Dashboard sync, local record reads, change-log reads,
    remote assignment maintenance, and update/create record helpers.
  - Good candidate for future Dart-based flow runners or a compiled harness
    CLI. Do not duplicate its semantics if a PowerShell module keeps using the
    same HTTP endpoints.
- `integration_test/sync/soak/soak_driver.dart`
  - Already models backend/RLS virtual users, weighted action mix, 15-project
    fixture IDs, burst windows, per-actor reports, failure buckets, and the
    distinction between `backend_rls` and `device_sync`.
  - Reuse this taxonomy and summary schema for the parent/concurrent harness.
    The device UI runner should not pretend a single phone is 20 concurrent
    UI users.
- `integration_test/sync/soak/soak_metrics_collector.dart`
  - Already samples sync transport/runtime and summarizes user count,
    concurrency, action delay, burst windows, fixture version/hash, and
    `syncEngineExercised`.
  - Reuse summary field names so backend and device manifests remain
    comparable.
- `lib/core/driver/screen_contract_registry.dart`
  - Already maps active screens to route, root key, action keys, and state
    keys through `/diagnostics/screen_contract`.
  - StepRunner should use this for route/screen assertions instead of encoding
    all screen expectations only in PowerShell.
- `lib/core/driver/flow_registry.dart` and `lib/core/driver/flows/*`
  - Existing flow definitions are useful as screen/route metadata and for
    future Dart runner work.
  - They are not currently enough to execute the S21 mutation flows by
    themselves, so the immediate S21 runner still needs focused flow modules.
- `tools/measure-device-sync.ps1`
  - Already performs UI-triggered Sync Dashboard proof without
    `POST /driver/sync`, samples `/driver/sync-status`, captures screenshots,
    and writes a JSON artifact.
  - The refactored Sync Dashboard flow should reuse this behavior or extract it
    into the shared `Flow.SyncDashboard` module.
- `.codex/skills/systematic-debugging.md` and
  `.claude/skills/systematic-debugging/SKILL.md`
  - These are process guidance, not runtime infrastructure.
  - The relevant rule for this harness is: no fixes before root cause. After
    three repeated red-screen/fix failures, the harness should stop, classify,
    capture evidence, and require an explicit root-cause slice instead of
    continuing through later flows.

Confirmed gaps:

- The app-side driver can dump widget trees, screen contracts, screenshots,
  actor context, sync runtime, sync status, local rows, and change logs, but the
  current PowerShell flow does not collect them consistently before and after
  each high-risk step.
- The debug log server has strong `/logs/errors` and `/logs/summary`
  endpoints, but the current soak script still relies heavily on ADB logcat.
  StepRunner should query both debug-server logs and bounded logcat, and treat
  either missing channel as a logged gap.
- The debug log server uses a hostname-derived `deviceId`; two Android devices
  may not be human-readable as S21/S10 in `/logs` without external mapping.
  Actor artifacts should record the device label, driver port, ADB serial, and
  debug-server device id observed in logs.
- `supabase-verifier.js` verifies records, storage objects, cascade deletion,
  and prefix cleanup, but it is a Node module/CLI, not a running HTTP
  verification service. The soak refactor can call it as a trusted local
  process, or add narrowly scoped debug-server verification endpoints later if
  that is cleaner.
- Existing direct driver mutation endpoints (`/driver/update-record`,
  `/driver/create-record`, `/driver/inject-photo-direct`,
  `/driver/inject-document-direct`) are useful for controlled setup/recovery,
  but they must stay labeled as non-UI mutation proof unless the flow enters
  the real UI path first.

Architecture decision:

- Keep the thin CLI plus modules plan.
- The modules are clients/orchestrators around the existing servers, not new
  servers.
- Add new driver endpoints only when an evidence gap cannot be closed by the
  existing `/driver/tree`, `/driver/screenshot`, `/diagnostics/*`,
  `/driver/change-log`, `/driver/local-record`, debug-server `/logs/*`, or
  Supabase verifier utilities.

## Harness Refactor Plan

Use PowerShell modules/classes or dot-sourced scripts under `tools/sync-soak/`.
Keep `tools/enterprise-sync-soak-lab.ps1` as a thin CLI wrapper.

### Proposed Files

- `tools/sync-soak/SoakModels.ps1`
  - Actor spec model.
  - Round/event model.
  - Failure classification constants.
  - Mutation ledger model.
- `tools/sync-soak/DriverClient.ps1`
  - Wrap the existing app-side driver server; do not create a new server.
  - `Invoke-DriverJson`
  - route reads,
  - widget waits,
  - tap/text/scroll helpers,
  - driver readiness preflight.
- `tools/sync-soak/ArtifactWriter.ps1`
  - JSON writing,
  - screenshot capture,
  - logcat capture,
  - failure bundle creation,
  - runtime log scanner,
  - screenshot/widget-tree classifiers.
- `tools/sync-soak/StepRunner.ps1`
  - one wrapper for all UI actions.
  - mandatory step telemetry.
  - fail-fast on runtime signatures and missing logs.
  - query debug-server `/logs/errors` and `/logs/summary` for each operation
    window, with ADB logcat as a second channel.
- `tools/sync-soak/Flow.DailyEntryActivity.ps1`
  - one focused daily-entry activity flow.
- `tools/sync-soak/Flow.Quantity.ps1`
  - one focused quantity flow.
- `tools/sync-soak/Flow.Photo.ps1`
  - one focused photo flow with screenshot after each picker step.
- `tools/sync-soak/Flow.SyncDashboard.ps1`
  - UI-triggered sync only.
  - no mutation responsibility.
  - extract or reuse the behavior already proven in
    `tools/measure-device-sync.ps1`.
- `tools/sync-soak/Cleanup.ps1`
  - mutation ledger cleanup.
  - remote/storage cleanup proof.
  - recovery-only direct sync path clearly marked non-acceptance.
- `tools/sync-soak/Summary.ps1`
  - pass/fail aggregation.
  - no generic pass if runtime/log/cleanup gates fail.

### Acceptance Gates For The Harness Itself

- [ ] A simulated widget-missing failure exits non-zero and writes failure
  bundle.
- [ ] A sample log containing `FlutterError` exits non-zero and reports
  `runtime_log_error`.
- [ ] Missing logcat capture exits non-zero as `logging_gap`.
- [ ] A failed flow does not run later flows in the same round unless explicitly
  configured for exploratory mode.
- [ ] A failed flow still writes summary, timeline, failure screenshot, log,
  route, queue counts, and mutation ledger.
- [ ] Cleanup failure is visible as `cleanup_failed`, not hidden by queue drain.
- [ ] Direct `/driver/sync` recovery is never counted as UI acceptance proof.

## S21 Recovery To-Do

### Phase A - Freeze And Baseline

- [x] Keep S10 parked until the refactored S21 combined gate is green.
- [x] Reintroduce S10 as the next regression actor through the refactored path.
  S10 is green for daily-entry, quantity, photo, contractors, combined, and
  MDOT 1126 typed-signature flows.
- [ ] Keep backend 15-20 actor load parked.
- [ ] Preserve current failed artifacts; do not overwrite them.
- [x] Record current S21 queue state before next work:
  `/driver/change-log`, `/driver/sync-status`, `/diagnostics/sync_runtime`,
  `/driver/current-route`, screenshot, logcat.
- [x] Confirm S21 starts from zero pending/blocked/unprocessed rows.
- [ ] Confirm no live red screen before running any mutation.

### Phase B - Harness Fail-Loud Work

- [ ] Reuse `tools/start-driver.ps1` and `tools/wait-for-driver.ps1` for
  device/debug-server setup instead of duplicating startup logic in the soak
  CLI.
- [x] Keep using the existing app-side `DriverServer` and host-side
  `debug-server`; do not add another HTTP server.
- [x] Refactor or introduce `StepRunner` before adding more flows.
  First slice: `tools/sync-soak/StepRunner.ps1`.
- [x] Make every flow step write named step artifacts.
  First slice applies to the refactored `sync-only` flow.
- [x] Scan success logs and failure logs for runtime signatures.
  First slice scans debug-server errors and ADB logcat after every
  refactored step and on failure evidence bundles.
- [x] Add screenshot/widget-tree red-screen classifier.
  First slice classifies `ErrorWidget` / `FlutterError` widget-tree evidence
  as runtime failure.
- [ ] Add failure classification taxonomy and remove broad default
  `driver_or_sync_error` where more specific evidence exists.
  First slice adds the taxonomy for the refactored path; legacy mutation
  flows still need migration.
- [x] Add mutation ledger and cleanup lifecycle.
  First daily-entry slice now restores only the ledger-owned
  `daily_entries` row/location that it mutated. If a failure happens after the
  local mutation is applied, the flow attempts ledger cleanup before recording
  the failed round.
- [x] Add reusable state sentinels for exact-value and queue assertions.
  `tools/sync-soak/StateSentinels.ps1` now provides exact text, marker-absent,
  route, actor-session, and queue-drained sentinels. Daily-entry cleanup uses
  exact local and remote ledger-value sentinels.
- [x] Add `-Flow daily-entry-activity|quantity|photo|sync-only|cleanup-only`
  or equivalent targeted mode so single-flow S21 proofs are not forced through
  all modes.
  `-Flow sync-only`, `-Flow daily-entry-only`, `-Flow quantity-only`, and
  `-Flow photo-only` are implemented and have accepted S21 evidence.
  `-Flow combined` is also implemented and accepted. `cleanup-only` is
  implemented and accepted against combined, contractor, and MDOT signature
  ledgers.
- [ ] Decide after the first PowerShell module split whether flow execution
  should remain PowerShell or move to a small Dart CLI that reuses
  `HarnessDriverClient`, `SoakDriver`, and `SoakMetricsCollector`.

### Phase C - Isolated S21 Flow Proof

- [x] Run S21 sync-only drain:
  - no mutation,
  - UI-triggered sync,
  - zero residue,
  - zero runtime logs,
  - zero logging gaps.
  Evidence:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-sync-only-rerun/summary.json`
  plus the two serial follow-ups listed in Phase E.
- [x] Run S21 daily-entry-activity only:
  - capture previous activities,
  - mutate one location,
  - sync through UI,
  - restore previous activities,
  - sync cleanup,
  - prove final local and remote value restored.
  Evidence:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only-rerun/summary.json`.
  This is one accepted daily-entry-only pass, not the three-pass confidence
  gate.
- [x] Run S21 quantity only:
  - create one generated quantity,
  - sync through UI,
  - soft-delete with real user UUID,
  - sync cleanup,
  - prove final local/remote deleted state.
  Evidence:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-quantity-only-after-autofocus-fix/summary.json`.
  The accepted run created one ledger-marked `entry_quantities` row, synced it,
  soft-deleted only that ledger-owned row with the current user id in
  `deleted_by`, synced cleanup through the Sync Dashboard, and proved local and
  remote soft-delete sentinels with final queue zero.
- [x] Run S21 photo only:
  - capture screenshot before Add Photo,
  - capture screenshot at source sheet,
  - capture screenshot after choosing gallery,
  - require `photo_name_dialog`,
  - sync through UI,
  - prove storage object exists,
  - cleanup photo row and storage object,
  - prove storage object absent.
  Evidence:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-photo-only-storage-status-fix/summary.json`.
  The accepted run created one ledger-marked `photos` row through the real Add
  Photo UI, synced through the Sync Dashboard, downloaded the generated storage
  object from `entry-photos`, soft-deleted only the ledger-owned row, synced
  cleanup through the Sync Dashboard, deleted the generated storage object, and
  proved storage absence using Supabase's object-not-found response.

### Phase D - App Defect Isolation

- [ ] If GoRouter duplicate `GlobalKey` returns, stop and build a minimal
  navigation repro:
  `/projects` -> `/report/<entryId>` -> `/sync/dashboard` -> `/report/<entryId>`.
- [ ] Add widget/integration coverage for that repro before another soak run.
- [x] If photo source sheet stalls, inspect the picker abstraction and
  `TestPhotoService` handoff:
  - prove injected file is available before tapping gallery,
  - prove tap target chosen exactly once,
  - prove permission/picker result completes,
  - add driver artifact for picker result state.
  Latest photo isolation found two issues before the accepted run:
  - the photo naming dialog autofocused immediately after the photo source
    bottom sheet and picker result path, causing the same S21 text-field
    framework assertions seen in the quantity flow;
  - the first storage absence helper only accepted HTTP 404, but Supabase
    Storage returned HTTP 400 with an embedded `statusCode:"404"` and
    `Object not found` body after delete.
  The flow now waits through the route animation before opening the photo name
  dialog, the filename field no longer autofocuses, and storage proof helpers
  record/interpret Supabase Storage status details under StrictMode.
- [ ] If quantity widgets are missing, isolate quantity flow layout and picker
  state with screenshots and widget-tree dumps.
  Latest quantity isolation found two app/harness defects before the accepted
  run:
  - the driver returned from `/driver/back` before modal pop teardown had
    settled, allowing the next command to inspect overlapping GoRouter
    subtrees;
  - the quantity flow opened an autofocus dialog immediately after the pay-item
    picker bottom sheet closed, causing `InheritedElement.notifyClients` and
    `RenderEditable attached` assertions on S21. The flow now taps visible
    pay-item keys before using search, `/driver/back` waits through the pop
    transition, and the quantity dialog no longer autofocuses the amount field.

### Phase E - Rebuild Confidence

- [x] Require three consecutive green S21 sync-only runs.
  Accepted serial runs:
  - `20260417-s21-refactor-sync-only-rerun`
  - `20260417-s21-refactor-sync-only-serial-2`
  - `20260417-s21-refactor-sync-only-serial-3`
  Each has `passed=true`, `queueDrainResult=drained`,
  `runtimeErrors=0`, `loggingGaps=0`, and
  `directDriverSyncEndpointUsed=false`.
- [x] Require three consecutive green S21 daily-entry-only runs with cleanup.
  Current accepted serial runs:
  - `20260417-s21-refactor-daily-entry-only-serial-2b`
  - `20260417-s21-refactor-daily-entry-only-serial-3`
  - `20260417-s21-refactor-daily-entry-only-serial-4`
  The failed `20260417-s21-refactor-daily-entry-only-serial-2` is excluded
  from the streak; it exposed a ledger ordered-dictionary read bug and was
  recovered via UI ledger restore.
- [x] Require three consecutive green S21 quantity-only runs with cleanup.
  Accepted runs:
  - `20260418-s21-state-machine-quantity-only-after-autofocus-fix`
  - `20260418-s21-state-machine-quantity-final-single-gate`
  - `20260418-s21-state-machine-quantity-confidence-3`
  Each has `passed=true`, `runtimeErrors=0`, `loggingGaps=0`,
  `queueDrainResult=drained`, and `directDriverSyncEndpointUsed=false`.
- [x] Require three consecutive green S21 photo-only runs with cleanup and
  storage object proof.
  Accepted runs:
  - `20260418-s21-state-machine-photo-only-storage-status-fix`
  - `20260418-s21-state-machine-photo-confidence-2`
  - `20260418-s21-state-machine-photo-confidence-3`
  Each has `passed=true`, `runtimeErrors=0`, `loggingGaps=0`,
  `queueDrainResult=drained`, `directDriverSyncEndpointUsed=false`, storage
  download proof, ledger-owned row cleanup, storage delete proof, and storage
  absence proof.
- [x] Only then run combined S21
  `daily-entry-activity,quantity,photo`.
  Accepted run:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-final/summary.json`.
  The flow uses the refactored `combined` module, not legacy all-modes. It
  runs daily-entry, quantity, and photo as sequential
  mutate/sync/cleanup phases under state-machine transitions. Each phase
  passed with `failedActorRounds=0`, `runtimeErrors=0`, `loggingGaps=0`,
  `queueDrainResult=drained`, `blockedRowCount=0`,
  `unprocessedRowCount=0`, `maxRetryCount=0`, and
  `directDriverSyncEndpointUsed=false`. The parent summary also reports
  `passed=true`, `actionCount=3`, final queue drained, and no direct
  `/driver/sync`. Photo storage proof downloaded `68` bytes, deleted the
  storage object, and proved Supabase Storage absence via object-not-found.
  The earlier
  `20260418-s21-state-machine-combined-initial` artifact is non-acceptance
  evidence: all child phases passed and the live queue was empty, but the
  parent summary finalizer failed on a PowerShell list-coercion bug before the
  summary could be accepted.
- [x] Only after combined S21 is green, bring S10 back as a regression actor.
  S10 regression is green through implemented refactored flows, including
  MDOT 1126 typed signature.
- [ ] Only after S21+S10 are green, optionally add one emulator actor if it is
  stable enough to provide useful extra device-lab signal.
- [ ] Only after the real-device lane is stable, resume the 15-20 user and
  15-project workload plan through headless app-sync actors plus backend/RLS
  virtual actors.

## Scale Model Clarification

The 15-20 user target does not require 15-20 physical phones.

The intended lab model is:

- S21 as the primary real-device UI/device-sync acceptance actor.
- S10 as a regression real-device actor after S21 is clean.
- Optional Android emulator as a third UI/device actor only if it is stable and
  not adding noise.
- Headless app-sync actors for the app-sync scale lane. These must use real
  Supabase sessions and isolated local stores so they exercise app sync state
  without needing a visible phone UI.
- Backend/RLS virtual actors for remote pressure, role/RLS assertions, weighted
  action mix, jitter, and burst windows.

The acceptance language should distinguish these layers:

- `device_ui`: real devices/emulator exercising the visible app and driver
  control plane.
- `headless_app_sync`: app-sync runtime actors without a visible UI, each with
  isolated local state and real auth.
- `backend_rls`: Supabase client actors proving backend policy and remote
  contention, not local SQLite/device sync.

A single S21 may cycle accounts sequentially for role churn and cache-reset
proof. That is valid role-switch proof, but it is not the 15-20 concurrent user
lane.

## Non-Negotiables Going Forward

- No all-modes rerun is accepted if the user sees a red screen, even if logs do
  not capture a Flutter signature.
- No run is accepted without log capture.
- No run is accepted with queue residue.
- No run is accepted with cleanup residue from generated data.
- No direct `/driver/sync` run counts as UI sync proof.
- No S10, emulator, headless app-sync, or backend actor scale-up until S21
  single-flow proof is stable.

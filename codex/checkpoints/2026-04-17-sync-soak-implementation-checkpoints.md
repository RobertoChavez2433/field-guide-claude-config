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

- Run S21/S10 with
  `tools\enterprise-sync-concurrent-soak.ps1 -UiMutationModes daily-entry-activity,quantity,photo`
  and capture the first parent manifest.
- Build UI-driven form/signature mutation proof next, or add role-switch
  UI automation if the immediate priority shifts back to role churn.

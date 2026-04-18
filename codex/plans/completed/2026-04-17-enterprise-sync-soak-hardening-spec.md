# Enterprise Sync Soak Hardening Spec

Date: 2026-04-17
Branch: `gocr-integration`
Research memo: `.codex/research/2026-04-17-sync-soak-gap-research.md`

## Intent

Build a realistic, bug-finding sync test system that simulates 10-20 live users
across 15 projects with phone/tablet app actors, backend remote actors, role
changes, file bytes, offline/online transitions, and concurrent sync triggers.

The goal is not to make the existing action count larger. The goal is to
exercise the same surfaces that fail on devices:

- local SQLite `change_log`,
- `sync_lock`,
- `SyncEngine.pushAndPull`,
- retry/block/repair paths,
- storage byte upload/download,
- auth/session rebinding,
- realtime dirty scopes,
- UI-triggered sync,
- multi-device convergence.

## Current Verdict

- [x] Backend/RLS soak exists and has passed a 10-minute local Docker run.
- [x] Backend/RLS soak now records attempted, failed, successful, worker, user,
  and latency counts.
- [x] Backend/RLS soak is useful for RLS and direct remote CRUD pressure.
- [x] Backend/RLS soak is not device-sync evidence.
- [ ] Device-sync soak is not enterprise-grade yet. Current status: S21
  refactored gates are green for `sync-only`, `daily-entry-only`,
  `quantity-only`, `photo-only`, and `combined`; the next device-sync gate is
  S10 regression through the refactored path.
- [x] S21 blocked/unprocessed local rows were reproduced, classified as
  obsolete debug-driver harness seed residue, repaired, and rerun to green.
- [x] S10 `~1.6k` pending local rows were reproduced, classified as a fresh
  backlog plus stale previous-user consent rows, repaired in sync-engine code,
  and rerun to green.

## Non-Negotiables

- [x] Do not call the current `12k` backend result device-sync proof.
- [x] Do not accept `POST /driver/sync` as device signoff evidence.
- [x] Do not use `MOCK_AUTH`.
- [ ] Do not pass a device cell if screenshots, debug logs, sync state, or
  visible UI show defects.
- [ ] Do not mark a soak successful if any actor ends with blocked rows,
  unprocessed rows, retry-count growth, stale locks, unauthorized project
  visibility, missing storage objects, or unchanged `lastSyncTime`.
- [x] Keep backend/RLS and device-sync metrics separate in artifacts.

## Phase 0 - Rename And Deconfuse The Existing Soak

- [x] Rename artifacts or labels from generic `soak` to `backend_rls_soak`
  where they refer to direct Supabase client runs.
- [x] Update CI job names and artifact filenames to make the layer obvious.
- [x] Update docs so the current backend soak explicitly says it bypasses local
  SQLite, `SyncEngine`, and file bytes.
- [x] Add summary output field `soakLayer=backend_rls` to backend summaries.
- [x] Add summary output field `syncEngineExercised=false` to backend
  summaries.
- [x] Keep backend/RLS soak in CI because it still catches policy regressions.

Acceptance:

- [x] A reviewer cannot mistake backend/RLS soak for device sync proof.

## Phase 1 - Device Actor Harness Foundation

- [x] Add a multi-driver runner that accepts multiple device actors:
  - `S21:4948`
  - `S10:4949`
  - future Windows actor.
- [x] Start each actor with a real debug driver app and real Supabase session.
- [x] Poll each actor independently through:
  - `/driver/sync-status`
  - `/driver/change-log`
  - `/diagnostics/sync_runtime`
  - `/diagnostics/screen_contract`
- [x] Add an artifact directory layout:
  - `.claude/test-results/<date>/enterprise-sync-soak/<run-id>/summary.json`
  - per-device `timeline.json`
  - per-device `change-log-before.json`
  - per-device `change-log-after.json`
  - per-device `sync-runtime.json`
  - per-device screenshots/log snippets.
- [x] Add a device actor timeline schema:
  - actor id,
  - device label,
  - driver port,
  - role,
  - current user id,
  - current project id,
  - operation,
  - started/completed timestamps,
  - pre/post sync status,
  - pre/post change-log counts,
  - failure classification.
- [x] Add a controller that supports ramp-up instead of starting every actor at
  once.
- [x] Add hard stop and cleanup so a failed actor still writes final evidence.

Partial implementation note: `tools/enterprise-sync-soak-lab.ps1` now writes
the run directory, per-device timelines, status/change-log/runtime artifacts,
and screenshots. Debug-log snippets plus live current user/project ids remain
open because existing diagnostics do not expose those fields yet.

Device proof note: `20260417-150725` ran S21 (`4948`) and S10 (`4949`) through
the local device lab on real debug apps/sessions and passed with
`failedActorRounds=0`.

Acceptance:

- [x] One command can coordinate S21 and S10 in the same run.
- [x] Artifacts prove every actor's local sync status before and after each
  sync cycle.

## Phase 2 - Local App Change Generation

- [x] Replace raw remote-only mutations in the implemented S21 daily-entry,
  quantity, and photo device paths with app-side local changes.
- [ ] Continue replacing raw remote-only mutations for personnel, equipment,
  contractor, forms, signatures, and other file-backed rows.
- [x] For implemented daily-entry, quantity, and photo app-side mutations,
  assert that a local `change_log` row appears before sync.
- [ ] For remaining app-side mutation families, assert that a local
  `change_log` row appears before sync.
- [ ] Add per-table change-log assertions:
  - table name,
  - record id,
  - operation,
  - project id,
  - retry count,
  - processed flag,
  - error message.
- [x] Add local record assertions before and after sync for implemented
  daily-entry, quantity, and photo flows.
- [ ] Add local record assertions before and after sync for remaining mutation
  families.
- [x] Keep raw driver SQLite mutation only as a lower-level fallback, and label
  it `driver_local_mutation`, not full UI proof.
- [ ] Add UI-driven mutations for the highest-risk flows first:
  - daily entry activities, (implemented/proven on S21 isolated gate)
  - quantities, (implemented/proven on S21 isolated gate)
  - personnel/equipment/contractor rows,
  - photo capture/import, (implemented/proven on S21 isolated gate with
    storage proof and cleanup)
  - forms,
  - project assignment visibility.

Acceptance:

- [ ] Device soak fails if a local app action does not create the expected
  `change_log` row.
- [ ] Device soak fails if the row remains unprocessed after a successful sync.

## Phase 3 - Realistic Multi-Actor Workload

- [ ] Model actors as humans, not loop counters:
  - admin,
  - engineer,
  - office technician,
  - inspector A,
  - inspector B,
  - inspector C.
- [ ] Support 10-20 workload actors with layer-specific evidence:
  - 2-4 real UI device app actors,
  - 8-16 backend remote actors for RLS/remote pressure,
  - a future headless app-sync actor lane before claiming 10-20 app users are
    proven through local SQLite/change-log/SyncEngine behavior.
- [ ] Seed or generate 15 projects.
- [ ] Assign inspectors to overlapping but not identical project sets.
- [ ] Use ramp-up:
  - first admin,
  - then inspectors,
  - then remote office/engineer actors,
  - then assignment churn.
- [ ] Use weighted action mix:
  - 20% reads/navigation/scope verification,
  - 20% daily entry edits,
  - 15% quantities/pay items,
  - 15% photos/files,
  - 10% forms/signatures,
  - 10% delete/restore/removal,
  - 5% project assignment churn,
  - 5% auth/session switching.
- [ ] Add think time and jitter so actor timing is field-like.
- [ ] Add burst windows where multiple actors edit the same project.

Acceptance:

- [ ] The run produces simultaneous backend and device activity.
- [ ] Two actors can mutate the same project and converge without local queue
  residue.

## Phase 4 - Role And Scope Hardening

- [ ] Verify every role's visible project set before, during, and after sync.
- [ ] Add assignment revocation while an inspector is viewing the project list.
- [ ] Add assignment grant while another device is already open.
- [ ] Assert no unauthorized project flashes in:
  - project list,
  - project selector,
  - recent activity,
  - sync dashboard,
  - form/project pickers,
  - photo/document lists.
- [ ] Add same-device account switching:
  - inspector -> admin,
  - admin -> inspector,
  - inspector A -> inspector B,
  - logout -> login after blocked queue state exists.
- [ ] Assert local caches, selected project, project provider state, and synced
  scopes are rebuilt after user switch.
- [ ] Add failure if previous user's project metadata appears after login.

Acceptance:

- [ ] No role can see unauthorized projects, even transiently.
- [ ] Same-device account switching leaves no stale project state.

## Phase 5 - File And Storage Soak

- [ ] Add real image fixtures in multiple sizes:
  - small thumbnail-like image,
  - normal field photo,
  - large photo,
  - image with GPS EXIF metadata.
- [x] Create photo rows from the app/device with real local `file_path` in the
  S21 `photo-only` gate.
- [x] Assert storage upload occurs in the S21 `photo-only` gate by downloading
  the generated object from Supabase Storage after UI-triggered sync.
- [x] Assert `remote_path` is bookmarked locally in the S21 `photo-only` gate.
- [ ] Assert another device can download/preview the uploaded object.
- [ ] Assert storage RLS blocks unauthorized role/project access.
- [ ] Assert EXIF GPS stripping where configured.
- [ ] Add stale remote path replacement and cleanup.
- [ ] Add `storage_cleanup_queue` assertions for delete/restore/purge paths.
- [ ] Extend to other file-backed rows:
  - form exports,
  - entry documents,
  - entry exports,
  - pay-app export artifacts,
  - signatures.

Acceptance:

- [x] Implemented photo rows require row proof and object proof.
- [ ] Remaining file-backed rows require row proof and object proof.
- [x] Implemented photo device soak fails on missing object, bad storage
  access, failed download, or failed storage cleanup proof.
- [ ] Extend missing-object/bad-access/failed-download/orphaned-cleanup failure
  gates to remaining file-backed rows.

## Phase 6 - Failure Injection

- [ ] Add network offline/online transition during queued local writes.
- [ ] Add network drop during push.
- [ ] Add network drop during pull.
- [ ] Add timeout/socket failure during file upload.
- [ ] Add auth expiration/refresh during sync.
- [ ] Add Supabase transient/rate-limit style failure.
- [ ] Add app background/foreground during sync.
- [ ] Add app process restart mid-sync.
- [ ] Add stale `sync_lock` setup and recovery assertion.
- [ ] Add SQLite busy/lock contention probe if feasible on device.
- [ ] Add realtime hint burst while sync is already active.
- [ ] Add dirty-scope overflow/degrade path.

Acceptance:

- [ ] Retryable failures retry or recover.
- [ ] Non-retryable failures are classified and visible.
- [ ] Repair-required state is visible when appropriate.
- [ ] The final state after recovery has no unexpected blocked/unprocessed rows.

## Phase 7 - Realtime And Dirty Scope Proof

- [ ] Bind realtime hints for the active company on each device actor.
- [ ] Have backend actors mutate project-scoped tables while devices are idle.
- [ ] Assert dirty scopes are marked on devices.
- [ ] Assert quick sync runs or queues follow-up sync when already syncing.
- [ ] Assert dirty scopes clear only after successful pull.
- [ ] Assert company mismatch hints are ignored.
- [ ] Assert assignment hints update visible project set.
- [ ] Capture realtime client errors and backend logs when limits or reconnects
  occur.

Acceptance:

- [ ] Remote changes appear on the correct devices without manual full sync.
- [ ] Unauthorized devices do not see unauthorized project data.

## Phase 8 - Fixture Scale-Up

- [ ] Expand deterministic fixture to 15 projects.
- [ ] Add 10-20 active users.
- [ ] Add realistic records per project:
  - daily entries,
  - quantities,
  - personnel,
  - contractors,
  - equipment,
  - photos,
  - forms,
  - signatures,
  - documents,
  - exports,
  - support/consent records.
- [ ] Include old projects, newly created projects, deleted projects, restored
  projects, assigned projects, unassigned projects, and reassigned projects.
- [ ] Include realistic field payload size:
  - long notes,
  - many rows per entry,
  - binary files,
  - export artifacts.
- [ ] Add fixture version/hash to every soak artifact.

Acceptance:

- [ ] First-sync and steady-state sync are both measured against field-like data.

## Phase 9 - Observability And Failure Triage

- [x] Add per-run summary:
  - actor count,
  - action count,
  - failed action count,
  - queue-drain result,
  - blocked row count,
  - unprocessed row count,
  - max retry count,
  - storage object failures,
  - unauthorized visibility failures,
  - runtime errors,
  - screenshots captured,
  - logs captured.
- [x] Add per-table sync health breakdown.
- [ ] Add backend log drain checks for postgres, auth, storage, realtime, and
  edge logs where available.
- [ ] Add Sentry event drain checks.
- [ ] Add automatic failure bundle:
  - actor timeline,
  - screenshots,
  - runtime diagnostics,
  - local change-log entries,
  - backend rows,
  - storage object status,
  - relevant logs.
- [ ] Add fail-fast for catastrophic failures, but preserve final artifact
  collection.

Acceptance:

- [x] Refactored S21 single-flow failures can be triaged from artifacts without
  rerunning immediately.
- [ ] Extend the same artifact completeness to S10 regression,
  headless app-sync, and backend/device overlap runs. `combined` now has
  accepted parent/child summary, queue, runtime/log, and photo storage proof.

## Phase 10 - CI And Local Lab Strategy

- [x] Keep backend/RLS soak in GitHub CI because it can run without devices.
- [x] Run staging backend/RLS soak from GitHub on every release candidate.
- [x] Run device-sync soak locally in the device lab until cloud device coverage
  is available.
- [ ] Add a nightly/manual workflow that records expected external device-lab
  artifacts without pretending GitHub ran phones.
- [ ] Add a future cloud-device lane when the app is stable enough.
- [ ] Require three consecutive backend/RLS staging soaks.
- [ ] Require three consecutive device-sync lab soaks on S21/S10.
- [ ] Require a focused rerun for every sync bug fix.

Acceptance:

- [ ] Release signoff states which layer passed: backend/RLS, staging backend,
  device-sync lab, UI role sweep, or all of them.

## Phase 11 - Immediate Bug-Finding Queue

- [x] Start with the current S21 blocked queue.
- [x] Capture current `/driver/change-log` rows, grouped by table, retry count,
  operation, and error message.
- [x] Capture current `/diagnostics/sync_runtime`.
- [x] Capture sync dashboard screenshot and repair state.
- [x] Determine whether blocked rows are:
  - invalid old local residue,
  - schema/payload mismatch,
  - RLS denial,
  - storage path/object problem,
  - local trigger/project-id bug,
  - auth/session mismatch,
  - sync lock/gate issue.
- [x] Fix the one-user S21 failure before treating multi-user soak results as
  meaningful.
- [x] Re-run one-device app sync until pending and blocked are both zero.
- [x] Run first S21+S10 device-lab soak after one-device sync was green.

Acceptance:

- [x] One real device can complete UI-triggered full sync with zero local queue
  residue before multi-device stress is considered valid.

## Ship Bar For Sync Soak Hardening

- [ ] Backend/RLS soak passes locally and on staging.
- [x] S21 one-user device sync passes with zero pending/blocked rows.
- [x] S10 one-user device sync passes with zero pending/blocked rows.
- [x] S21+S10 device-lab sync wrapper passes.
- [ ] Multi-role device/backend actor soak passes.
- [x] S21 implemented photo file/storage object proof passes as an isolated
  gate.
- [ ] Full file/storage object proof across remaining file-backed rows and
  cross-device access passes.
- [ ] Same-device auth switching passes.
- [ ] Failure injection passes or creates correct repair-required evidence.
- [ ] No unauthorized project metadata flashes in UI.
- [ ] Artifacts are complete enough for post-run triage.

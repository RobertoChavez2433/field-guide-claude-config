# Sync Soak Unified Hardening Todo

Date: 2026-04-18
Status: active controlling todo/spec
Branch audited: `gocr-integration` at `022a673a`

## Purpose

This is the single forward working list for sync-soak hardening, device
evidence, scale testing, and sync-engine reliability work. It consolidates:

- `.claude/codex/plans/2026-04-18-mdot-1126-typed-signature-sync-soak-plan.md`
- `.claude/codex/plans/2026-04-18-sync-engine-external-hardening-todo.md`
- `.claude/codex/plans/2026-04-18-sync-soak-spec-audit-agent-task-list.md`
- `.claude/codex/reports/2026-04-18-all-test-results-result-index.json`
- `.claude/codex/reports/2026-04-18-enterprise-sync-soak-result-index.json`

Use this file as the checklist that gets checked off as implementation and
artifact-backed verification land. Use
`.codex/checkpoints/2026-04-18-sync-soak-unified-implementation-log.md` as the
append-only narrative of what changed, what evidence was collected, and what
remains open.

## Current Direction

The branch direction is consistent: harden the current custom sync engine and
device-soak harness, not replace the engine before release.

Recent branch work shows a clear movement toward:

- modular refactored soak flows under `tools/sync-soak/`;
- strict UI-driver failure behavior instead of silent or broad passes;
- direct `/driver/sync` rejection as acceptance evidence;
- ledger-owned cleanup and replayable mutation ledgers;
- signature file contract repair, including `remote_path` proof and schema v61
  nullable `signature_files.local_path`;
- S21-first live acceptance, S10 regression, and later scale-up;
- custom lint guardrails for sync, form workflow sentinels, and keyed editable
  form bodies.

## External Pattern Policy

PowerSync is a reference corpus, not a migration target for this release.
The useful work is to learn from PowerSync, Jepsen, Elle, WatermelonDB, RxDB,
FoundationDB/TigerBeetle-style simulation, and related local-first systems, and
then either reuse compatible pieces or port the patterns into Field Guide.

This is a pragmatic reuse lane, not a research sink. If a tool/package does
not fit Field Guide's licensing, Flutter/Dart/PowerShell harness shape, real
session requirements, Supabase/RLS semantics, or device-soak evidence model,
close the candidate as "not worth pursuing" and keep the local implementation.

- [ ] Prefer direct reuse of compatible open-source packages or tooling where
  the license and architecture fit.
- [ ] Treat PowerSync client SDK/helper packages as possible reference or reuse
  candidates where they are Apache 2.0 or MIT.
- [ ] Treat PowerSync Service and CLI internals as source-available reference
  material unless legal/product review explicitly clears reuse.
- [ ] Prefer reusing Jepsen/Elle checker concepts or tooling for history
  analysis where practical instead of building every checker from scratch.
- [ ] Do not introduce a second production sync truth.
- [ ] Do not make a PowerSync migration a release gate.

Reuse triage rules:

- [ ] Time-box initial reuse discovery to one focused pass before building new
  checker/attachment/diagnostic primitives.
- [ ] For each candidate, record license, runtime, integration cost, expected
  code deleted or avoided, and exact Field Guide failure mode it helps.
- [ ] Adopt only when the candidate removes real implementation risk faster
  than local code.
- [ ] Reject quickly when it requires a second sync truth, weakens real-device
  evidence, hides Supabase/RLS behavior, or adds more adaptation code than it
  saves.

Pattern adoption targets:

- checkpoints and write checkpoints;
- scoped/bucket-style reconciliation hashes;
- diagnostics surfaces and artifact fields;
- attachment queue state machines;
- deterministic operation histories;
- nemesis/fault schedules;
- final quiescence gates;
- checker-based safety and liveness assertions;
- operation history retention/compaction policies.

## Evidence Baseline

Accepted device evidence:

- [x] S21 `sync-only`, `daily-entry-only`, `quantity-only`, `photo-only`, and
  `combined` refactored state-machine gates.
- [x] S21 `contractors-only` contractor/personnel/equipment graph.
- [x] S10 refactored regression for daily-entry, quantity, photo, contractor,
  and combined.
- [x] S21 cleanup-only replay for accepted combined, contractor, and MDOT 1126
  signature ledgers.
- [x] MDOT 1126 typed-signature lane accepted on S21, S10, and S21
  cleanup-only replay.
- [x] MDOT 1126 expanded fields/rows accepted on S21.
- [x] MDOT 0582B form-response mutation accepted on S21.
- [x] S21 post-v61 signature backlog drain accepted.
- [x] S21 recovery after MDOT 1174R red-screen residue accepted through
  refactored `sync-only`.

Known open evidence:

- [ ] MDOT 1174R is implemented/wired but not accepted.
- [ ] S10 post-v61 cross-device signature metadata pull is not proven.
- [ ] S10 regressions for MDOT 1126 expanded and MDOT 0582B are not proven.
- [ ] S10 regression for MDOT 1174R is blocked until S21 acceptance.
- [ ] MDOT 0582B export/storage proof is not proven.
- [ ] Generic builtin form export proof is not proven.
- [ ] Saved-form/gallery lifecycle sweeps are not proven.
- [ ] Role/account, RLS denial, failure injection, staging, and scale gates are
  absent from the indexed results.

Current result-index facts:

- Full index: 165 runs, 76 pass, 89 fail.
- Enterprise sync-soak index: 55 runs, 15 pass, 40 fail.
- Current P0 failure: `20260418-s21-mdot1174r-after-ensure-visible-scroll`.
- Latest P0 failure class: `runtime_log_error`.
- Latest P0 runtime evidence: `runtimeErrors=27`,
  `queueDrainResult=residue_detected`, `unprocessedRowCount=33`.
- Failure fingerprints include duplicate `GlobalKey`, multiple widgets using
  the same `GlobalKey`, and detached render-object assertions.
- Clean non-acceptance diagnostic:
  `20260418-s21-mdot1174r-visible-text-only` failed because
  `/driver/scroll-to-key` could not find
  `mdot1174_air_slump_pairs_composer_left_time` after 40 scrolls.
- Recovery proof exists, but recovery is not mutation acceptance:
  `20260418-s21-mdot1174r-redscreen-residue-recovery-sync-only`.

## Acceptance Rules

No lane is complete until the artifact proves all applicable items:

- [ ] Real session, no `MOCK_AUTH`.
- [ ] Refactored flow path, not legacy all-modes.
- [ ] UI-triggered Sync Dashboard sync only.
- [ ] `directDriverSyncEndpointUsed=false`.
- [ ] Preflight queue is empty for mutation acceptance runs.
- [ ] Local mutation markers are present.
- [ ] Local pre-sync `change_log` rows are present for touched tables.
- [ ] Post-sync remote row/object proof is present.
- [ ] Pull/local proof is present when the lane claims cross-device or
  post-write freshness.
- [ ] Mutation ledger captures every cleanup obligation.
- [ ] Cleanup is ledger-owned, not broad project/form-type deletion.
- [ ] Cleanup sync is UI-triggered.
- [ ] Final `/driver/change-log` is empty.
- [ ] `runtimeErrors=0`.
- [ ] `loggingGaps=0`.
- [ ] `blockedRowCount=0`.
- [ ] `unprocessedRowCount=0`.
- [ ] `maxRetryCount=0`.
- [ ] Screenshots, sync state, and debug logs show no UI/layout/runtime/sync
  defect.
- [ ] Docs/checkpoints are updated only after the artifact exists.

## Completion Model And Ending Parameters

The ending parameters are not active until the P0, P1, and proposed P2 work in
this spec is implemented and artifact-backed. P2 is part of the planned
hardening scope, not optional stretch work for this wave.

Do not start a final "are we done?" assessment while any proposed P2 section
below remains open:

- Device-Soak Jepsen-Style Workload Layer;
- Failure Injection And Liveness;
- Backend/Device Overlap;
- Staging And Release Gates;
- 15-20 Actor Scale Model;
- Operational Diagnostics And Alerts;
- Consistency Contract Docs.

Once every P0, P1, and proposed P2 item is closed with evidence, this
hardening wave can be considered complete only after Field Guide records three
consecutive green full-system sync-soak runs on staging or staging-equivalent
backend state.

Each full-system run must include:

- S21 as the primary real-device actor;
- S10 as the regression real-device actor;
- 10-20 total real-session actors through real devices, headless app-sync
  actors, and/or backend pressure actors;
- at least 15 seeded projects;
- daily entries, quantities, photos, signatures, form responses, form exports,
  saved-form/gallery lifecycle, and at least one storage-backed export family;
- role/account switching or revocation;
- at least one fault window followed by explicit quiescence.

Each accepted final run must prove:

- `directDriverSyncEndpointUsed=false`;
- `runtimeErrors=0`;
- `loggingGaps=0`;
- `blockedRowCount=0`;
- `unprocessedRowCount=0`;
- `maxRetryCount=0`;
- final `/driver/change-log` empty on participating devices;
- local/remote reconciliation hashes match for required tables;
- storage row/object consistency passes;
- no unauthorized reads or stale role/project scope;
- no lost acknowledged writes.

Liveness thresholds:

- after faults stop, all actors reach quiescence within 10 minutes;
- p95 sync-to-visible-local convergence is <= 2 minutes for row data;
- p95 file-backed object availability is <= 5 minutes.

Artifact requirements:

- summary JSON;
- operation history;
- actor list;
- fixture hash;
- app build and schema version;
- screenshots;
- debug-log extracts;
- reconciliation output;
- retained first-failure artifacts for any failed attempt in the streak window.

Track progress toward completion with:

- `Sync Soak Exit Score = accepted required gates / required gates`;
- target exit score: `100%`, plus three consecutive green full-system runs;
- `Safety Violations = lost acknowledged writes + unauthorized reads +
  unreconciled local/remote mismatches + storage row/object mismatches`;
- target safety violations: `0`.

## Ordered Todo

### P0 - Stabilize Current Device State And Harness Hygiene

- [ ] Confirm S21 live `/driver/change-log` is empty before any new mutation
  attempt.
- [ ] Confirm S10 live `/driver/change-log` is empty before any new S10 proof.
- [ ] Preserve the MDOT 1174R blocker facts in checkpoints before pruning any
  remaining raw artifacts.
- [ ] Add or wire an artifact-retention knob before more soak loops:
  - keep all accepted evidence;
  - keep the first instance of each new failure class;
  - for duplicate failures, keep summary/debug extracts and prune bulk
    screenshots/logcat/widget trees unless requested.
- [ ] Keep broad `driver_or_sync_error`, `unknown_failure`, and
  `queue_not_drained_or_sync_not_observed` as non-acceptance classes.
- [ ] Continue replacing broad failure classes with specific classifications:
  widget targeting, state sentinel, storage proof, cleanup ledger,
  change-log proof, runtime log, auth/RLS denial, queue liveness, and
  reconciliation mismatch.

### P0 - Close Post-v61 Signature Drift Proof

- [ ] Run S10 post-v61 cross-device signature proof after S10 pulls
  S21-created schemaVersion 61 signature rows.
- [ ] Prove S10 local `signature_files` and `signature_audit_log` metadata can
  exist without a device-local file path.
- [ ] Prove S10 final queue drain and no integrity drift.
- [ ] Record the accepted artifact in this file and the implementation log.

### P0 - Fix And Accept MDOT 1174R On S21

- [ ] Review MDOT 1174R row-section key/state ownership before retrying.
- [ ] Fix duplicate `GlobalKey` ownership in repeated row composers and
  compact workflow sections.
- [ ] Fix detached render-object assertions exposed by
  `/driver/scroll-to-key` plus `Scrollable.ensureVisible`.
- [ ] Verify section/body sentinels for placement, quantities, QA,
  air/slump, remarks, and signature stay mounted only where the keyed editable
  descendants are actually visible/editable.
- [ ] Rebuild/restart the S21 driver after the fix.
- [ ] Rerun S21 `mdot1174r-only`.
- [ ] Accept only if the artifact proves:
  - local form markers;
  - local pre-sync `change_log`;
  - post-sync remote `form_responses`;
  - ledger-owned cleanup;
  - UI-triggered cleanup sync;
  - final empty queue;
  - zero runtime/logging gaps;
  - no direct `/driver/sync`.
- [ ] If it fails, stop after one run, recover through UI `sync-only`, and
  update the implementation log with the next exact blocker.

### P1 - Run S10 Form Regressions

- [ ] Run S10 `mdot1126-expanded-only` regression.
- [ ] Run S10 `mdot0582b-only` regression.
- [ ] Run S10 `mdot1174r-only` regression after S21 acceptance.
- [ ] For each S10 run, require the same local marker, pre-sync
  `change_log`, remote row, cleanup, queue, runtime, logging, and direct-sync
  gates as S21.

### P1 - Builtin Form Export Proof

- [ ] Implement/refactor a generic export proof flow for `mdot_1126`.
- [ ] Implement/refactor a generic export proof flow for `mdot_0582b`.
- [ ] Implement/refactor a generic export proof flow for `mdot_1174r`.
- [ ] For each form export, prove:
  - report-attached saved form source;
  - export row or export artifact row;
  - local pre-sync `change_log` where applicable;
  - storage bytes where bytes are created;
  - authorized download;
  - cleanup delete;
  - storage absence;
  - final queue drain.
- [ ] Keep MDOT 0582B mutation acceptance separate from MDOT 0582B
  export/storage acceptance.

### P1 - Saved-Form And Gallery Lifecycle

- [ ] Create saved form from `/report/:entryId`.
- [ ] Reopen from form gallery.
- [ ] Edit/save a previously created form.
- [ ] Exercise export decision path.
- [ ] Delete/cleanup through production UI/service seams.
- [ ] Prove local and remote absence after cleanup.
- [ ] Run the lifecycle sweep for:
  - `mdot_1126`;
  - `mdot_0582b`;
  - `mdot_1174r`.

### P1 - File, Storage, And Attachment Hardening

- [ ] Extend storage object proof beyond photos and signatures to:
  - form exports;
  - entry documents;
  - entry exports;
  - pay-app exports;
  - other file-backed table families.
- [ ] Add unauthorized storage access denial proof for each bucket/path family.
- [ ] Add small, normal, large, and GPS-EXIF image fixtures.
- [ ] Prove cross-device download/preview of uploaded objects.
- [ ] Add `storage_cleanup_queue` assertions for delete/restore/purge paths.
- [ ] Add durable attachment/file states:
  - upload started;
  - upload succeeded;
  - row upsert succeeded;
  - local bookmark succeeded;
  - stale object cleanup queued;
  - cleanup retry failed/succeeded.
- [ ] Test crash/retry cases:
  - after upload before row upsert;
  - after row upsert before bookmark;
  - after bookmark before `change_log` processed;
  - after storage delete failure before cleanup retry.
- [ ] Investigate PowerSync attachment helper package ideas before building
  new attachment queue primitives from scratch.

### P1 - Role, Scope, Account, And RLS Sweeps

- [ ] Inventory real account fixtures and UI keys for admin, inspector,
  engineer, and office technician.
- [ ] Run role sweeps with real sessions and no `MOCK_AUTH`.
- [ ] Prove denied routes and hidden controls for:
  - project management;
  - PDF import;
  - pay-app management;
  - trash;
  - admin surfaces;
  - export/download actions;
  - storage-backed previews.
- [ ] Add same-device account switching:
  - admin to inspector;
  - inspector to office technician;
  - active user to revoked user;
  - revoked user back to allowed user.
- [ ] Prove selected project, providers, realtime channels, local scope cache,
  Sync Dashboard state, screenshots, and debug logs do not leak stale account
  data.
- [ ] Treat permission grants and revocations as sync changes, not absence
  inference.

### P1 - Sync Engine Correctness Hardening

- [ ] Replace offset/range pull pagination with stable keyset/checkpoint
  pagination.
- [ ] Test equal `updated_at` rows across page boundaries.
- [ ] Test concurrent remote insert during pull.
- [ ] Test long-offline pull.
- [ ] Test restart after partial page.
- [ ] Add per-scope reconciliation probes after sync:
  - project/table row counts;
  - stable hashes for high-value tables;
  - local samples;
  - remote samples;
  - mismatch classification.
- [ ] Include at minimum:
  - `projects`;
  - `project_assignments`;
  - `daily_entries`;
  - `entry_quantities`;
  - `photos`;
  - `form_responses`;
  - `signature_files`;
  - `signature_audit_log`;
  - `documents`;
  - `pay_applications`;
  - export artifact tables.
- [ ] Add write-checkpoint semantics:
  - queue drain proof;
  - remote write proof;
  - next-pull proof;
  - final local proof.
- [ ] Do not mark sync fresh until the local write is visible through the
  server/pull path.
- [ ] Prove realtime hints are only hints:
  - missed hints;
  - delayed hints;
  - duplicate hints;
  - out-of-order hints;
  - fallback polling convergence;
  - no unauthorized project data flash during role revocation.
- [ ] Add idempotent replay tests for:
  - duplicate local push after remote upsert succeeds;
  - duplicate pull page replay;
  - duplicate row apply;
  - duplicate soft-delete push;
  - already-absent remote row;
  - duplicate upload;
  - storage 409;
  - row upsert replay;
  - bookmark replay.
- [ ] Add crash/restart tests around:
  - `sync_control.pulling = '1'`;
  - held `sync_lock`;
  - cursor update;
  - manual conflict re-push insertion;
  - auth refresh;
  - background retry scheduling.
- [ ] Split conflict strategy by domain:
  - LWW where product-approved;
  - stronger behavior or documented preservation for signatures, signed form
    responses, audit rows, quantities, and narrative fields.
- [ ] Fix misleading file-sync phase logging where phase 2 row-upsert failure
  is reported as phase 3 bookmark failure.

### P2 - Device-Soak Jepsen-Style Workload Layer

- [ ] Run the reuse triage before implementing custom checkers:
  - Jepsen direct use;
  - Elle direct history checker use;
  - lightweight local checker modeled after Jepsen/Elle if direct use is too
    heavy.
- [ ] Add a seedable operation scheduler.
- [ ] Record every operation in a history log:
  - actor;
  - device/session;
  - user;
  - project;
  - table/object family;
  - record id;
  - start/end time;
  - result;
  - expected invariant impact.
- [ ] Add checker actors that read local and remote state without mutating.
- [ ] Add invariant checkers:
  - no lost acknowledged writes;
  - local/remote convergence after quiescence;
  - no unauthorized role visibility;
  - no blocked/unprocessed rows;
  - conflict-log expectations;
  - row/object consistency for file-backed records;
  - no stale account/project scope after switching.
- [ ] Evaluate whether Jepsen or Elle can consume our operation history
  directly before writing custom checkers.
- [ ] If using Jepsen/Elle directly is too heavy, keep the same model:
  history, generators, nemesis/fault schedule, and checkers.

### P2 - Failure Injection And Liveness

- [ ] Add offline burst replay.
- [ ] Add long-offline replay.
- [ ] Add network partitions:
  - full disconnect;
  - outbound-only where possible;
  - inbound-only where possible.
- [ ] Add auth failure cases:
  - 401/auth refresh;
  - 403/RLS denial;
  - revoked assignment during offline window.
- [ ] Add storage failure cases:
  - 409 conflict;
  - timeout;
  - rate-limit style transient failure;
  - cleanup delete failure.
- [ ] Add app lifecycle faults:
  - pause/resume;
  - background/foreground;
  - process kill/restart while preserving SQLite files.
- [ ] Add realtime/fallback faults:
  - missed hint;
  - duplicate hint;
  - out-of-order hint;
  - dirty-scope overflow.
- [ ] Add explicit quiescence phase:
  - stop new writes;
  - heal faults;
  - wait for queue count zero;
  - wait for blocked count zero;
  - wait for sync/download state idle;
  - wait for realtime/fallback settled;
  - wait for reconciliation hashes matched.
- [ ] Add separate liveness acceptance thresholds: recovery must happen within
  a defined timeout after faults stop.

### P2 - Backend/Device Overlap

- [ ] Keep backend/RLS soak and device-sync soak summaries explicitly separate.
- [ ] Run backend/RLS pressure concurrently with a refactored device `-Flow`
  gate.
- [ ] Preserve child summaries by evidence layer:
  - backend/RLS direct Supabase pressure;
  - real-device local SQLite/change-log sync;
  - headless app-sync actors;
  - final checker/reconciliation output.
- [ ] Do not let backend/RLS success satisfy device-sync acceptance.
- [ ] Stamp fixture version/hash into every artifact.

### P2 - Staging And Release Gates

- [ ] Provision staging-only harness credentials.
- [ ] Prove staging schema hash parity.
- [ ] Prove staging RLS/storage policy parity.
- [ ] Run local reset, sync matrix, backend/RLS soak, and performance proof
  after fixture expansion.
- [ ] Collect three green staging backend/RLS soaks.
- [ ] Collect three green staging/nightly device-sync or app-sync soaks.
- [ ] Add GitHub/CI run proof after push.
- [ ] Preserve repeated green history before release tagging.

### P2 - 15-20 Actor Scale Model

Target shape:

- two live devices: S21 primary and S10 regression;
- one emulator if stable enough to add signal;
- headless app-sync actors with isolated local stores and real sessions;
- backend/RLS virtual actors for remote pressure only.

Scale todo:

- [ ] Expand deterministic fixture to 15 projects.
- [ ] Provision 10-20 active users with realistic role/project assignments.
- [ ] Include realistic records and binary/export artifacts.
- [ ] Add headless app-sync actors using the actual sync engine, local store,
  auth/session binding, and storage paths.
- [ ] Ensure each headless actor has an isolated local database/store.
- [ ] Run S21 and S10 concurrently with headless app-sync actors.
- [ ] Add emulator only after it is stable and artifact-producing.
- [ ] Add backend/RLS actors concurrently as pressure, not as device-sync proof.
- [ ] Require final checker output for all 15-20 users:
  - no lost acknowledged writes;
  - no unauthorized reads;
  - local/remote convergence;
  - storage row/object consistency;
  - empty queues;
  - no stale auth/project scope.

### P2 - Operational Diagnostics And Alerts

- [ ] Define a Field Guide sync diagnostics contract inspired by PowerSync:
  - connected/connecting;
  - uploading;
  - downloading;
  - first-sync complete;
  - last sync timestamp;
  - queue count;
  - blocked count;
  - retry count;
  - active user/company/project;
  - app version;
  - schema version;
  - sync run id.
- [ ] Persist the same fields into device-soak artifacts.
- [ ] Emit the same fields into debug logs and Sentry/log events where safe.
- [ ] Add staging/backend alerts for:
  - blocked queue rows;
  - rising retry counts;
  - stale sync locks;
  - stale `pulling=1`;
  - stale last sync;
  - repeated reconciliation mismatch;
  - storage cleanup backlog;
  - per-device sync timeout;
  - Supabase/Postgres replication or storage errors;
  - RLS denials;
  - backend log-drain failures.
- [ ] Define retention/compaction policy for:
  - `change_log`;
  - `conflict_log`;
  - debug logs;
  - repair audit rows;
  - storage cleanup queue;
  - soak operation histories.

### P2 - Consistency Contract Docs

- [ ] Write `docs/sync-consistency-contract.md`.
- [ ] Document what the engine guarantees and what it does not.
- [ ] Cover:
  - local acknowledged writes;
  - remote acknowledged writes;
  - eventual convergence;
  - conflict policy;
  - immutable/audit tables;
  - file object semantics;
  - storage cleanup;
  - role revocation;
  - realtime hints;
  - recovery responsibilities.
- [ ] Document per-table sync/conflict semantics:
  - scope type;
  - insert/update/delete behavior;
  - soft-delete support;
  - file behavior;
  - conflict strategy;
  - whether LWW is allowed;
  - natural-key remap behavior;
  - required soak coverage.
- [ ] Add a new synced table checklist:
  - adapter metadata;
  - SQLite trigger coverage;
  - Supabase table/RLS/storage policies;
  - migration and rollback;
  - fixture data;
  - characterization tests;
  - device-soak mutation or explicit exemption;
  - reconciliation probe membership.
- [ ] Write `docs/sync-scale-hardening-playbook.md`:
  - actor model;
  - seedable workloads;
  - fault families;
  - quiescence gates;
  - convergence checkers;
  - diagnostics;
  - release thresholds;
  - mapping from PowerSync/Jepsen/WatermelonDB/RxDB patterns to Field Guide.

### P3 - Optional PowerSync Evaluation After Release Gates

This is not a migration gate. It is optional and only worth doing if the
earlier reuse triage finds a concrete reason to go deeper after current
S21/S10/staging gates are green.

- [ ] Review PowerSync Apache/MIT client/helper packages for reusable
  attachment, SQLite, diagnostics, and app-sync testing components.
- [ ] Review PowerSync Service/source-available internals for design patterns,
  not copy/paste reuse unless licensing is cleared.
- [ ] If useful, run a one-week throwaway branch proof over one project with:
  - assignments;
  - contractors;
  - daily entries;
  - quantities;
  - one photo;
  - one form response;
  - one signature file;
  - role revocation;
  - file object proof.
- [ ] Record whether pattern adoption remains enough.
- [ ] Stop the spike if it adds a second sync truth, delays release gates, or
  requires substantial custom code for the same Field Guide semantics.

## Source References For External Pattern Review

- PowerSync open-source/source-availability overview:
  `https://www.powersync.com/open-source`
- PowerSync Dart/Flutter repository:
  `https://github.com/powersync-ja/powersync.dart`
- PowerSync Service repository:
  `https://github.com/powersync-ja/powersync-service`
- PowerSync diagnostics docs:
  `https://docs.powersync.com/maintenance-ops/self-hosting/diagnostics`
- PowerSync write checkpoint docs:
  `https://docs.powersync.com/handling-writes/custom-write-checkpoints`
- PowerSync protocol/checksum docs:
  `https://docs.powersync.com/architecture/powersync-protocol`
- Jepsen:
  `https://github.com/jepsen-io/jepsen`
- Elle:
  `https://github.com/jepsen-io/elle`

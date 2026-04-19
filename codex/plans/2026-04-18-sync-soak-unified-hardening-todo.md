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
- [x] S21 MDOT 1174R mutation acceptance after repeated-row key/focus
  hardening:
  `20260418-s21-mdot1174r-after-repeated-row-focus-hardening`.
- [x] S21 MDOT 1174R post-responsive-theme stability rerun:
  `20260418-s21-mdot1174r-post-responsive-theme-stability-fix-rerun`.
- [x] S10 post-v61 signature cross-device pull/drain proof:
  `20260418-s10-post-v61-signature-cross-device-sync-only`.
- [x] S10 MDOT 1126 expanded regression:
  `20260418-s10-mdot1126-expanded-after-verified-remarks-open`.
- [x] S10 MDOT 0582B regression:
  `20260418-s10-mdot0582b-after-medium-layout-key-fix`.
- [x] S10 MDOT 1174R regression after responsive-theme stability fix:
  `20260418-s10-mdot1174r-after-responsive-theme-stability-fix`.
- [x] MDOT 1126 builtin form export proof accepted on S21 and S10:
  `20260418-s21-mdot1126-export-after-attached-branch-fix` and
  `20260418-s10-mdot1126-export-after-attached-branch-fix`.
  - S21: `form_exports/1db318cb-07ee-41c2-935f-f5a4f4ee2831`,
    `export_artifacts/0f446168-6e24-4370-b1ba-6533f1c0b736`,
    SHA-256
    `5b3e002eabcdbd9eba2798375e4cb7bdae287fdd627163e9518509b5e003d142`.
  - S10: `form_exports/42b68f47-fa72-414d-9e46-724e6d883db9`,
    `export_artifacts/eb087db2-ef94-4d36-9fc0-b6738bbac5a9`,
    SHA-256
    `72b002f452d7ba354a0ed91ff2e7851f0966cfc5b236949abab55cd1392d8a0d`.
- [x] MDOT 0582B builtin form export proof accepted on S21 and S10:
  `20260418-s21-mdot0582b-export-initial` and
  `20260418-s10-mdot0582b-export-initial`.
  - S21: `form_exports/ad06b8f0-570e-4ca6-85bc-04439a7b56ed`,
    `export_artifacts/64dad3e0-c590-4ac6-bd0f-a608a9dce4bb`,
    SHA-256
    `9ce8fd72ae05a844a2dbd665e2fb1db46d99a76807f462ff46735bea0d9d2495`.
  - S10: `form_exports/b9e3cf93-757e-492c-beb8-7e04acc0d845`,
    `export_artifacts/b09df381-9f0e-43a9-8c4c-15d6e36f0c82`,
    SHA-256
    `6b52096ec3cee301e5c6c5e8718479134047e45839663741e2de0ab0d2cf0534`.
- [x] MDOT 1174R builtin form export proof accepted on S21 and S10:
  `20260418-s21-mdot1174r-export-initial` and
  `20260418-s10-mdot1174r-export-initial`.
  - S21: `form_exports/bb038620-8bda-4f12-8ff3-12f766d1cd10`,
    `export_artifacts/e6aa8fa6-5285-458f-af1d-1258b65e12bf`,
    SHA-256
    `cea5eb3ef9cad81bb6c14d784b6f184d40a681e3bdfe439ca15e382eef521c46`.
  - S10: `form_exports/e40ff8ed-7ae3-45a1-a719-4115e777c190`,
    `export_artifacts/a5b86437-0437-47fb-94a0-9b06da0c9232`,
    SHA-256
    `abad92554598729f225309d4601e005cd6b31106376808bd9509339b0c06b2ce`.
- [x] Saved-form/gallery lifecycle sweep accepted for MDOT 1126, MDOT 0582B,
  and MDOT 1174R on S21 and S10:
  `20260418-s21-form-gallery-lifecycle-final-build` and
  `20260418-s10-form-gallery-lifecycle-after-expanded-hub-key`.
  - S21 gates: `queueDrainResult=drained`, `failedActorRounds=0`,
    `runtimeErrors=0`, `loggingGaps=0`, `blockedRowCount=0`,
    `unprocessedRowCount=0`, `maxRetryCount=0`,
    `directDriverSyncEndpointUsed=false`.
  - S10 gates: `queueDrainResult=drained`, `failedActorRounds=0`,
    `runtimeErrors=0`, `loggingGaps=0`, `blockedRowCount=0`,
    `unprocessedRowCount=0`, `maxRetryCount=0`,
    `directDriverSyncEndpointUsed=false`.
  - S21 ledger IDs:
    `mdot_1126` `form_responses/0daa8349-cc23-4eaa-895e-bbcef8b7e2e7`,
    `form_exports/8486fcf4-1fa9-427e-9e53-70e105a94cab`,
    `export_artifacts/614d8cc7-0da6-4406-aaa4-dedbc1149a12`;
    `mdot_0582b`
    `form_responses/9685c4a9-ba17-4701-bf25-bc4147870571`,
    `form_exports/11553762-bf4b-4ac1-871e-0f2967f0bdcd`,
    `export_artifacts/47b03535-8b71-4b09-b4e2-a7eeac35dd9a`;
    `mdot_1174r`
    `form_responses/7a8f2c49-0c4f-4b7d-9ba3-4afb81f2da66`,
    `form_exports/a40effdf-ad6c-4a5a-b2cd-e114aec0c9a7`,
    `export_artifacts/167600f5-8e97-4ca1-88cc-cd617284a922`.
  - S10 ledger IDs:
    `mdot_1126` `form_responses/99a2fb1c-38fe-4817-b01d-694d522ade7b`,
    `form_exports/fcd57aed-6cd7-4a63-acf8-bf3ccbd2abab`,
    `export_artifacts/c71c18f2-0b3c-4f59-a642-81935dd80e38`;
    `mdot_0582b`
    `form_responses/5aed14a2-273d-4e7f-b512-c109b9a8d74f`,
    `form_exports/fa373a7a-c2de-4f6c-9b87-37bf50f03ecd`,
    `export_artifacts/4692fc6f-c7f8-4007-877b-9ada6b9ea317`;
    `mdot_1174r`
    `form_responses/aac12ea1-6cee-476a-becc-717b99d92d9b`,
    `form_exports/7ba1c210-2289-43fd-8741-50bab02cc13e`,
    `export_artifacts/1a1b8d52-e2c8-4322-ab5f-728d9ba43d8a`.

Known open evidence:

- [x] MDOT 1174R is implemented/wired and accepted on S21.
- [x] S10 post-v61 cross-device signature metadata pull is proven.
- [x] S10 regressions for MDOT 1126 expanded and MDOT 0582B are proven.
- [x] S10 regression for MDOT 1174R is proven after S21 acceptance and the
  responsive-theme red-screen fix.
- [x] MDOT 0582B export proof is proven for the current local-only
  `form_exports` / `export_artifacts` contract.
- [x] MDOT 1174R export proof is proven for the current local-only
  `form_exports` / `export_artifacts` contract.
- [x] Generic builtin form export proof is proven for the current local-only
  `form_exports` / `export_artifacts` contract: MDOT 1126, MDOT 0582B, and
  MDOT 1174R are accepted on S21/S10.
- [x] Saved-form/gallery lifecycle sweeps are proven for MDOT 1126,
  MDOT 0582B, and MDOT 1174R on S21/S10.
- [x] Entry-document storage object proof is proven on S21 through the
  refactored `documents-only` flow:
  `20260418-s21-documents-entry-object-proof-after-denial-classifier`.
  The artifact proves UI-created `documents/b4efc514-b14f-41e4-a257-b5ef0989ed5a`,
  remote row path, authorized `entry-documents` storage bytes/hash,
  unauthorized denial for the same bucket/path, cleanup storage
  delete/absence, empty final queue, zero runtime/logging gaps, and
  `directDriverSyncEndpointUsed=false`.
- [x] Remote object unauthorized-denial proof is proven for all currently
  applicable remote storage families: `entry-photos` through
  `20260418-s21-photo-storage-denial-proof`, `signatures` through
  `20260418-s21-mdot1126-signature-storage-denial-proof`, and
  `entry-documents` through the document proof artifacts.
- [x] Cross-device document download/preview is proven S21 to S10 through
  `20260418-s21-s10-documents-cross-device-download-proof`: S10 pulled the
  S21-created `documents` row via UI sync, tapped the document tile, cached a
  local file, and `/driver/local-file-head` proved the receiver bytes/hash
  matched the storage proof before ledger cleanup.
- [ ] Role/account, RLS denial, failure injection, staging, and scale gates are
  absent from the indexed results.
- [x] File/storage/attachment hardening is the active next P1 lane after
  saved-form/gallery lifecycle acceptance. The current implementation pass
  starts with an inventory of production file-backed families, storage buckets,
  cleanup queues, and existing proof helpers before adding new primitives.

Current result-index facts:

- Full index: 165 runs, 76 pass, 89 fail.
- Enterprise sync-soak index: 55 runs, 15 pass, 40 fail.
- Historical P0 failure preserved:
  `20260418-s21-mdot1174r-after-ensure-visible-scroll`.
- Historical P0 failure class: `runtime_log_error`.
- Historical P0 runtime evidence: `runtimeErrors=27`,
  `queueDrainResult=residue_detected`, `unprocessedRowCount=33`.
- Historical failure fingerprints include duplicate `GlobalKey`, multiple
  widgets using the same `GlobalKey`, and detached render-object assertions.
- Clean non-acceptance diagnostic:
  `20260418-s21-mdot1174r-visible-text-only` failed because
  `/driver/scroll-to-key` could not find
  `mdot1174_air_slump_pairs_composer_left_time` after 40 scrolls.
- Recovery proof exists, but recovery is not mutation acceptance:
  `20260418-s21-mdot1174r-redscreen-residue-recovery-sync-only`.
- Latest P0 MDOT 1174R acceptance evidence:
  `20260418-s21-mdot1174r-post-responsive-theme-stability-fix-rerun`
  passed with `queueDrainResult=drained`, `runtimeErrors=0`,
  `loggingGaps=0`, `blockedRowCount=0`, `unprocessedRowCount=0`,
  `maxRetryCount=0`, and `directDriverSyncEndpointUsed=false`.

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

- [x] Confirm S21 live `/driver/change-log` is empty before any new mutation
  attempt.
- [x] Confirm S10 live `/driver/change-log` is empty before any new S10 proof.
- [x] Preserve the MDOT 1174R blocker facts in checkpoints before pruning any
  remaining raw artifacts.
- [x] Add or wire an artifact-retention knob before more soak loops:
  - keep all accepted evidence;
  - keep the first instance of each new failure class;
  - for duplicate failures, keep summary/debug extracts and prune bulk
    screenshots/logcat/widget trees unless requested.
- [x] Keep broad `driver_or_sync_error`, `unknown_failure`, and
  `queue_not_drained_or_sync_not_observed` as non-acceptance classes.
- [x] Continue replacing broad failure classes with specific classifications:
  widget targeting, state sentinel, storage proof, cleanup ledger,
  change-log proof, runtime log, auth/RLS denial, queue liveness, and
  reconciliation mismatch.

### P0 - Close Post-v61 Signature Drift Proof

- [x] Run S10 post-v61 cross-device signature proof after S10 pulls
  S21-created schemaVersion 61 signature rows.
- [x] Prove S10 local `signature_files` and `signature_audit_log` metadata can
  exist without a device-local file path.
- [x] Prove S10 final queue drain and no integrity drift.
- [x] Record the accepted artifact in this file and the implementation log.

### P0 - Fix And Accept MDOT 1174R On S21

- [x] Review MDOT 1174R row-section key/state ownership before retrying.
- [x] Fix duplicate `GlobalKey` ownership in repeated row composers and
  compact workflow sections.
- [x] Fix detached render-object assertions exposed by
  `/driver/scroll-to-key` plus `Scrollable.ensureVisible`.
- [x] Verify section/body sentinels for placement, quantities, QA,
  air/slump, remarks, and signature stay mounted only where the keyed editable
  descendants are actually visible/editable.
- [x] Rebuild/restart the S21 driver after the fix.
- [x] Rerun S21 `mdot1174r-only`.
- [x] Accept only if the artifact proves:
  - local form markers;
  - local pre-sync `change_log`;
  - post-sync remote `form_responses`;
  - ledger-owned cleanup;
  - UI-triggered cleanup sync;
  - final empty queue;
  - zero runtime/logging gaps;
  - no direct `/driver/sync`.
- [x] If it fails, stop after one run, recover through UI `sync-only`, and
  update the implementation log with the next exact blocker.

### P1 - Run S10 Form Regressions

- [x] Run S10 `mdot1126-expanded-only` regression.
- [x] Run S10 `mdot0582b-only` regression.
- [x] Run S10 `mdot1174r-only` regression after S21 acceptance.
- [x] For each S10 run, require the same local marker, pre-sync
  `change_log`, remote row, cleanup, queue, runtime, logging, and direct-sync
  gates as S21.

### P1 - Responsive Root Shell Architecture Guardrail

- [x] Add the S10 responsive-theme red-screen failure to this controlling
  checklist as a structural architecture rule item.
- [x] Keep root app shell wrappers stable across breakpoint/density changes;
  vary wrapper configuration instead of sometimes returning the router child
  directly.
- [x] Add custom lint coverage:
  `no_conditional_root_shell_child_wrapper`.
- [x] Wire the lint into `architectureRules`.
- [x] Add focused lint-package tests proving rule code, severity, and
  correction guidance.
- [x] Verify the rule with focused architecture lint tests and `dart analyze`.

### P1 - Builtin Form Export Proof

- [x] Implement/refactor a generic export proof flow for `mdot_1126`.
- [x] Implement/refactor a generic export proof flow for `mdot_0582b`.
- [x] Implement/refactor a generic export proof flow for `mdot_1174r`.
- [x] For each form export, prove:
  - report-attached saved form source;
  - export row or export artifact row;
  - local pre-sync `change_log` where applicable;
  - storage bytes where bytes are created;
  - authorized download;
  - cleanup delete;
  - storage absence;
  - final queue drain.
- [x] Keep MDOT 0582B mutation acceptance separate from MDOT 0582B
  export/storage acceptance.

### P1 - Saved-Form And Gallery Lifecycle

- [x] Create saved form from `/report/:entryId`.
- [x] Reopen from form gallery.
- [x] Edit/save a previously created form.
- [x] Exercise export decision path.
- [x] Delete/cleanup through production UI/service seams.
- [x] Prove local and remote absence after cleanup.
- [x] Run the lifecycle sweep for:
  - [x] `mdot_1126` on S21/S10;
  - [x] `mdot_0582b` on S21/S10;
  - [x] `mdot_1174r` on S21/S10.

### P1 - File, Storage, And Attachment Hardening

- [x] Extend storage object proof beyond photos and signatures to:
  - form exports;
  - entry documents;
  - entry exports;
  - pay-app exports;
  - other file-backed table families.
  - [x] Added local adapter contract coverage for every file-backed family:
    bucket mapping, local file path column, local-only history flags, storage
    cleanup registry mapping, and storage path validation.
  - [x] Fixed generalized storage path validation so nested
    `export_artifacts` paths such as
    `artifacts/<company>/<project>/<artifact>/<filename>` are accepted.
  - [x] Added generalized replay coverage across file-backed families:
    photos cover upload replay, storage 409, missing local file with existing
    `remote_path`, and row-upsert replay; documents cover upload/upsert/bookmark
    through the real adapter; `signature_files` cover existing-remote metadata
    replay with absent local file; `export_artifacts` cover `local_path`,
    storage path changes, and stale cleanup retry queueing.
  - [x] Added storage-family diagnostics to post-sync reconciliation artifacts
    so local-only export families are explicit in soak summaries instead of
    implicit skip behavior.
  - [x] Classified `entry_exports`, `form_exports`, `export_artifacts`, and
    pay-application exports as local-only byte/history families for the current
    adapter contract; photos, signatures, and entry documents remain
    remote-object proof families.
  - [x] Entry documents are now live-proven on S21:
    `20260418-s21-documents-entry-object-proof-after-denial-classifier`
    created a document through `/report/:entryId`, synced through the UI,
    proved the remote row and `entry-documents` object bytes/hash, then
    performed ledger-owned cleanup with storage delete/absence proof.
  - [x] Local-only export families are closed by explicit contract evidence,
    not remote object inference: `entry_exports`, `form_exports`,
    `export_artifacts`, and pay-application export artifacts remain local
    byte/history families under the current `skipPush`/`skipPull` adapter
    contract, with accepted local row/file/hash proof and diagnostics.
- [x] Add unauthorized storage access denial proof for each bucket/path family.
  - [x] Added `Assert-SoakStorageUnauthorizedDenied` and harness tests for
    denial response classification.
  - [x] Ran the denial helper for the live entry-document object path in
    `20260418-s21-documents-entry-object-proof-after-denial-classifier`; the
    accepted denial shape was HTTP 400 with `Bucket not found` from the private
    `entry-documents` bucket.
  - [x] Ran the denial helper against proven-present `entry-photos` objects:
    `20260418-s21-photo-storage-denial-proof` passed with unauthorized HTTP
    400 `Bucket not found` for the same path as the authorized storage proof.
  - [x] Ran the denial helper against proven-present `signatures` objects:
    `20260418-s21-mdot1126-signature-storage-denial-proof` passed with
    unauthorized HTTP 400 `Bucket not found` for the same path as the
    authorized storage proof.
  - [x] Local-only export/history families have no remote bucket/path object
    to deny under the current adapter contract; denial proof applies to the
    three remote-object families above.
- [x] Add small, normal, large, and GPS-EXIF image fixtures.
- [x] Prove cross-device download/preview of uploaded objects.
  - [x] Added and accepted `documents-cross-device-only`:
    `20260418-s21-s10-documents-cross-device-download-proof` created a
    document on S21, synced it through the UI, pulled it on S10 through the UI,
    tapped the pulled document tile on S10, and proved the S10 cached file
    bytes/hash matched the source storage proof before source cleanup and
    receiver cleanup pull.
- [x] Add `storage_cleanup_queue` assertions for delete/restore/purge paths.
- [x] Add durable attachment/file states:
  - [x] upload started;
  - [x] upload succeeded;
  - [x] row upsert succeeded;
  - [x] row upsert failed;
  - [x] local bookmark succeeded;
  - [x] local bookmark failed;
  - [x] stale object cleanup queued;
  - [x] cleanup retry failed/succeeded.
  - [x] Added `file_sync_state_log` plus v62 migration/fresh-schema wiring as
    diagnostic evidence, not a second production sync queue.
  - [x] Added signatures bucket coverage to cleanup/orphan registries.
- [x] Test crash/retry cases:
  - [x] after upload before row upsert;
  - [x] after row upsert before bookmark;
  - [x] after bookmark before `change_log` processed;
  - [x] after storage delete failure before cleanup retry.
  - [x] `bookmarkRemotePath` now fails if phase 3 updates zero local rows,
    preventing a missing local bookmark target from being treated as a
    successful file push.
  - [x] Focused file-sync evidence covers phase-2 cleanup, phase-3 bookmark
    failure state logging, duplicate upload/upsert replay, and deferred stale
    storage cleanup retry queueing.
  - [x] Bookmark-completed replay with a still-unprocessed `change_log` row now
    proves no duplicate upload, no extra `change_log` row from the replayed
    bookmark, and successful queue drain after `markProcessed`.
- [x] Added stale local file cache invalidation coverage for remote path
  replacement, remote delete, and unchanged remote path.
- [x] Investigate PowerSync attachment helper package ideas before building
  new attachment queue primitives from scratch.
  - [x] Current PowerSync docs mark legacy Dart
    `powersync_attachments_helper` deprecated and recommend built-in SDK
    attachment helpers.
  - [x] Reused the pattern, not the package: local-only attachment state,
    explicit phase transitions, retry/cleanup evidence, and verification hooks
    inside the existing Field Guide sync engine.
  - [x] Rejected direct adoption for this release because it depends on the
    PowerSync database/queue substrate and would introduce a second sync truth.

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

- [x] Replace offset/range pull pagination with stable keyset/checkpoint
  pagination.
- [x] Test equal `updated_at` rows across page boundaries.
- [x] Test concurrent remote insert during pull.
- [x] Test long-offline pull.
- [x] Test restart after partial page.
- [x] Add per-scope reconciliation probes after sync:
  - project/table row counts;
  - stable hashes for high-value tables;
  - local samples;
  - remote samples;
  - mismatch classification.
  - [x] Add a debug-driver local reconciliation snapshot endpoint with
    bounded row counts, stable selected-column hashes, sample ids, sample
    rows, and truncation classification.
  - [x] Add a matching debug-driver remote reconciliation snapshot endpoint
    that uses the app's real Supabase device session, not host service-role
    credentials.
  - [x] Add a sync-soak reconciliation harness module that can compare local
    driver snapshots with device-session remote snapshots and classify
    unavailable remote snapshots, truncation, count mismatches, and hash
    mismatches.
  - [x] Rebuild/restart S21 and S10 driver apps and prove the local snapshot
    endpoint on device with empty queues.
  - [x] Wire the reconciliation probe into post-sync flow artifacts and require
    a passing local/remote comparison before accepting covered flow lanes.
  - [x] Prove the post-sync gate with S21
    `20260418-s21-sync-only-active-reconciliation-gate-rerun`: 13 table
    specs, `reconciliationFailedCount=0`, `queueDrainResult=drained`,
    `runtimeErrors=0`, `loggingGaps=0`, `blockedRowCount=0`,
    `unprocessedRowCount=0`, `maxRetryCount=0`, and
    `directDriverSyncEndpointUsed=false`.
  - [x] Record local-only export history handling explicitly: `form_exports`,
    `export_artifacts`, and `entry_exports` are included in the artifact as
    local-only active-row snapshots, while remote comparison is skipped because
    the current adapters are `skipPull`/`skipPush` local history tables.
  - [x] Keep remote soft-deleted tombstones out of the normal convergence hash;
    active-row reconciliation is the post-sync gate, while tombstone retention
    and cleanup remain covered by delete/cleanup-specific gates.
- [x] Include at minimum:
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
- [x] Add write-checkpoint semantics:
  - [x] queue drain proof before advancing `last_sync_time`;
  - [x] remote write proof;
  - [x] follow-up pull path proof for cycles that pushed local writes;
  - [x] final local proof that the acknowledged write is visible after the
    server/pull path.
- [x] Do not mark sync fresh until the local write is visible through the
  server/pull path.
  - [x] Block fresh sync metadata when the final local queue is not drained.
  - [x] Block fresh sync metadata when a cycle pushed local writes but skipped
    the follow-up pull path.
  - [x] Add per-record proof that pushed writes are visible through the
    server/pull path before treating the write scope as fresh.
- [x] Prove realtime hints are only hints:
  - [x] missed hints;
  - [x] delayed hints;
  - [x] duplicate hints;
  - [x] out-of-order hints;
  - [x] fallback polling convergence;
  - [x] no unauthorized project data flash during role revocation.
- [x] Add idempotent replay tests for:
  - [x] duplicate local push after remote upsert succeeds;
  - [x] duplicate pull page replay;
  - [x] duplicate row apply;
  - [x] duplicate soft-delete push;
  - [x] already-absent remote row;
  - [x] duplicate upload;
  - [x] storage 409;
  - [x] row upsert replay;
  - [x] bookmark replay.
  - [x] Add focused PullHandler coverage proving a duplicate pull page replay
    does not duplicate rows and rows with matching `updated_at` are treated as
    already applied.
  - [x] Verify existing idempotent remote absence coverage:
    `sync_engine_delete_test.dart` covers empty-response soft-delete replay and
    `supabase_sync_contract_test.dart` covers hard-delete 404/not-found as
    idempotent success.
  - [x] Verify existing storage duplicate coverage:
    `file_sync_handler_test.dart` covers storage 409/already-exists continuing
    to metadata upsert.
  - [x] Complete and index the remaining replay matrix with one artifact-backed
    test per replay class.
- [x] Add crash/restart tests around:
  - [x] `sync_control.pulling = '1'`;
  - [x] held `sync_lock`;
  - [x] cursor update;
  - [x] manual conflict re-push insertion;
  - [x] auth refresh;
  - [x] background retry scheduling.
- [x] Split conflict strategy by domain:
  - [x] LWW remains the default for product-approved business records.
  - [x] Sparse push-skip audit rows still use LWW so server-timestamp-only
    checks do not claim a local preservation win.
  - [x] Signed local `form_responses` are preserved over newer unsigned pulled
    rows.
  - [x] `signature_files` preserve local immutable fingerprint metadata when a
    full pulled row disagrees, while still accepting newer `remote_path`
    updates when the immutable fingerprint matches.
  - [x] `signature_audit_log` preserves the local immutable audit chain when a
    full pulled row disagrees.
  - [x] `entry_quantities` and narrative fields keep LWW while preserving the
    discarded quantity, notes, and narrative text in changed-column
    `conflict_log` diffs.
  - [x] Focused evidence:
    `conflict_resolver_domain_policy_test.dart`,
    `conflict_clock_skew_test.dart`, `sync_invariants_property_test.dart`, and
    `sync_engine_lww_test.dart` passed under analyzer and Flutter test.
- [x] Fix misleading file-sync phase logging where phase 2 row-upsert failure
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

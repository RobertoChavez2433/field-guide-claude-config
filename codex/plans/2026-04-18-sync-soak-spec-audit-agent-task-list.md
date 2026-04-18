# Sync Soak Spec Audit And Agent Task List

Date: 2026-04-18

## Purpose

Convert the remaining sync-soak and UI/RLS specs into an execution queue after
the refactored S21 `combined` gate passed. This addendum does not replace the
controlling specs:

- `.codex/plans/2026-04-17-enterprise-sync-soak-hardening-spec.md`
- `.codex/plans/2026-04-17-sync-soak-ui-rls-implementation-todo.md`
- `.codex/plans/2026-04-17-sync-hardening-ui-rls-closeout-todo-spec.md`
- `.codex/plans/2026-04-17-s21-soak-harness-audit-and-recovery-plan.md`

## Current Accepted Device Evidence

- S21 `sync-only`, `daily-entry-only`, `quantity-only`, `photo-only`, and
  `combined` refactored state-machine gates are green.
- Accepted combined artifact:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-final/summary.json`.
- S21 `contractors-only` is green for the contractor/personnel/equipment
  graph:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-contractors-fourth/summary.json`.
- S10 refactored regression is green for `daily-entry-only`,
  `quantity-only`, `photo-only`, `contractors-only`, and `combined` after a
  sync-only preflight drained inherited old queue rows:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-combined-initial/summary.json`.
- S21 `cleanup-only` live replay is green against the accepted S21 combined
  and contractor ledgers:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-cleanup-only-replay-accepted-ledgers-idempotent/summary.json`.
- S21 MDOT 1126 typed-signature flow is green through the refactored
  `mdot1126-signature-only` module:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-accepted-with-cleanup-sync-retry/summary.json`.
- S21 cleanup-only replay of the accepted MDOT 1126 signature ledger is green:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-cleanup-only-replay-accepted-ledger/summary.json`.
- S10 MDOT 1126 typed-signature regression is green:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot1126-signature-regression-with-cleanup-sync-retry/summary.json`.
- S21 post-v61 signature backlog drain is green after upgrading the driver app
  to schemaVersion 61:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-post-v61-signature-backlog-sync-only/summary.json`.
  This proves the local nullable `signature_files.local_path` migration can
  pull the previously blocked remote signature metadata on S21 and drain the
  exposed `signature_files` / `signature_audit_log` queue through Sync
  Dashboard UI sync.
- S21 MDOT 1126 expanded fields/rows are green through the refactored
  `mdot1126-expanded-only` module:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-signature-ready-or-nav/summary.json`.
  The accepted run proves header markers, rainfall row, SESC measure
  type/location/status/corrective action, remarks, typed signature,
  pre-sync local `change_log` rows, post-sync remote `form_responses`,
  `signature_files`, and `signature_audit_log`, signature storage download,
  ledger-owned cleanup, storage delete/absence, UI-triggered cleanup sync, and
  final empty queue. Earlier failed artifacts are preserved as non-acceptance
  diagnostics only.
- S21 MDOT 0582B form-response mutation is green through the refactored
  `mdot0582b-only` module:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-accepted-initial/summary.json`.
  The accepted run proves report-attached creation, local marker proof for
  header data, chart standards, operating standards, HMA proctor row, quick
  test row, pre-sync local `change_log`, post-sync remote `form_responses`,
  ledger-owned cleanup, UI-triggered cleanup sync, remote soft-delete, and
  final empty queue. PDF/export and storage-byte proof for MDOT 0582B remains
  a separate open export lane.
- Combined acceptance facts: `passed=true`, `failedActorRounds=0`,
  `runtimeErrors=0`, `loggingGaps=0`, `queueDrainResult=drained`,
  `blockedRowCount=0`, `unprocessedRowCount=0`, `maxRetryCount=0`, and
  `directDriverSyncEndpointUsed=false`.
- Photo and MDOT 1126 signature flows prove storage download,
  ledger-owned row cleanup, storage delete, and storage absence.
- Final live S21 and S10 `/driver/change-log` checks after this continuation
  returned `count=0`, `unprocessedCount=0`, `blockedCount=0`, and
  `maxRetryCount=0`.
- Legacy all-modes and direct `/driver/sync` remain non-acceptance paths.
- `tools/enterprise-sync-concurrent-soak.ps1` can now forward `-Flow` to the
  device runner, so future backend/device overlap can target the refactored
  combined path. That is harness readiness only; it is not execution proof.

## 2026-04-18 Continuation Checklist

This is the active on-screen queue for the next implementation passes. Items
stay open until backed by artifacts, not just code changes.

### Immediate Ordered Queue

- [x] Close MDOT typed-signature harness-contract hardening before adding more
  form flows:
  - [x] mutation-run preflight must fail fast on non-empty `/driver/change-log`;
  - [x] signature storage proof must require `signature_files.remote_path`
    from the synced row, with no inferred acceptance path;
  - [x] signature cleanup must fail when a ledger that requires storage cleanup
    is missing `remotePath`;
  - [x] harness self-tests must cover `mdot1126-signature-only` flow
    validation and `signatures` bucket/path cleanup contracts, including
    mismatched ledger `remotePath`.
- [x] Decide and document the root cause for signature integrity count drift
  (`signature_files` / `signature_audit_log` local `1` vs remote `25`) before
  broad form/signature scale-up. Root cause: the local SQLite schema required
  `signature_files.local_path NOT NULL`, while Supabase allows null local paths
  for rows created on other devices. v61 rebuilds `signature_files` with
  nullable `local_path`; live S21/S10 post-upgrade integrity proof remains a
  separate verification item.
- [x] Prove S21 post-v61 signature backlog drain after pulling remote
  signature rows created before the nullable `local_path` migration.
- [ ] Prove post-v61 S10 signature integrity drift is gone after it pulls
  signature rows created by S21 on schemaVersion 61.
- [x] Accept MDOT 1126 expanded field/row flow live on S21.
- [x] Implement MDOT 0582B form-response mutation flow.
- [ ] Accept MDOT 1174R flow on S21. The refactored `mdot1174r-only` module is
  implemented and wired, but the latest live diagnostic is non-acceptance
  evidence blocked on compact section/body proof while opening Quantities
  after QA edits. Cleanup passed and the final S21 queue drained.
- [ ] Implement builtin form export proof for `mdot_0582b`, `mdot_1126`, and
  `mdot_1174r`.
- [ ] Implement saved-form/gallery lifecycle sweeps for all builtin forms.
- [ ] Then resume role/account sweeps, storage/RLS denial expansion, failure
  injection, backend/device overlap, staging, and scale/headless actors.

### Current Remaining Implementation Queue After MDOT 0582B

This is the actionable queue to dispatch across implementation agents. A lane
is not complete until its artifact shows UI-triggered sync, no direct
`/driver/sync`, final empty queue, no runtime/logging gaps, and docs updated.

- [ ] Agent A - S10 and cross-device form regression:
  run S10 post-v61 cross-device signature proof, then S10 regression for
  `mdot1126-expanded-only` and `mdot0582b-only`.
- [ ] Agent B - MDOT 1174R mutation:
  finish S21 acceptance for the implemented/wired `mdot1174r-only` flow. It
  already creates from `/report/:entryId` and targets concrete header and row
  markers with `mdot1174_*` keys; the current blocker is compact workflow
  section/body proof around Quantities after QA edits. Acceptance still
  requires local `change_log`, remote `form_responses`, ledger-owned cleanup,
  UI-triggered cleanup sync, final empty queue, zero runtime/log gaps, and no
  direct `/driver/sync`.

#### Agent B Current Checklist

- [x] Wire `mdot1174r-only` into the refactored harness.
- [x] Create MDOT 1174R from `/report/:entryId` with a ledger-owned
  `form_responses` row.
- [x] Add stable section header and expanded-section keys for the workflow.
- [x] Prove diagnostic cleanup leaves S21 `/driver/change-log` empty after
  failed 1174R attempts.
- [x] Move expanded-section proof onto the mounted body instead of the chevron
  icon.
- [x] Make `/driver/text` fail loudly when the target key has no editable
  descendant.
- [ ] Rebuild S21 driver after the sentinel/text-route hardening patch.
- [ ] Rerun `mdot1174r-only` on S21 and accept only if markers reach local
  `form_responses`, local pre-sync `change_log`, remote `form_responses`,
  ledger cleanup, UI-triggered cleanup sync, and final empty queue.
- [ ] Update checkpoints with the accepted artifact or the next blocking
  artifact before moving to export/gallery lanes.
- [ ] Agent C - builtin form exports and saved-form/gallery lifecycle:
  add export/artifact proof for `mdot_1126`, `mdot_0582b`, and `mdot_1174r`;
  prove created rows/bytes, authorized download, cleanup delete, storage
  absence, and saved-gallery reopen/edit/delete behavior.
- [ ] Agent D - role, RLS, and failure expansion:
  add real-account role sweeps, storage/RLS denial checks, offline/network/auth
  failure injection, backend/device overlap, staging credentials/schema proof,
  and headless app-sync actors for the later 15-20 user scale gate.

### Agent 1 - S10 Regression And Cleanup Replay

- [x] Confirm S10 is physically attached through ADB.
- [x] Start or rebuild the S10 driver on port `4949`.
- [x] Prove the S10 queue is empty before mutation regression.
- [x] Run S10 `sync-only`, then isolated daily-entry, quantity, photo,
  contractor, and combined refactored flows.
- [x] Live-replay cleanup-only ledgers from accepted S21 combined and
  contractor runs.
- [x] Gate: final `/driver/change-log` empty, no runtime errors, no logging
  gaps, no blocked/unprocessed rows, and no direct `/driver/sync`.

### Agent 2 - File-Backed Forms And Signatures

- [x] Audit existing form/signature/file-backed UI keys, production save paths,
  local tables, change-log coverage, and cleanup seams.
- [x] Implement MDOT 1126 typed-signature creation from `/report/:entryId` as
  the first file-backed form/signature flow. Prove `form_responses`,
  `signature_files`, `signature_audit_log`, and signature object absence after
  ledger-owned cleanup.
- [x] Implement the first smallest real UI mutation flow from that audit.
- [x] Accept MDOT 1126 expanded data-entry flow beyond signature-only:
  rainfall rows, SESC measure rows/statuses, remarks, typed signature,
  `form_responses`, `signature_files`, `signature_audit_log`, storage object,
  export/cleanup proof as applicable.
- [x] Implement MDOT 0582B (`mdot_0582b`) report-attached mutation flow:
  create response, enter header/standards/proctor/test markers, prove local
  `form_responses` JSON, local pre-sync `change_log`, post-sync remote
  `form_responses`, ledger-owned cleanup, UI-triggered cleanup sync, remote
  soft-delete, and final queue drain. PDF export/storage proof remains open in
  the generic export lane.
- [ ] Accept MDOT 1174R (`mdot_1174r`) flow on S21: the code path now creates
  a response and attempts concrete section fields/list rows using
  `mdot1174_*` UI keys, but live acceptance remains open until section
  body proof and row entry are stable and the artifact proves
  `form_responses`, ledger-owned cleanup, and final queue drain. Export object
  proof stays in the generic export lane unless invoked explicitly.
- [ ] Implement generic form export flow for every builtin form:
  `mdot_0582b`, `mdot_1126`, and `mdot_1174r`. Prove `form_exports` or
  `export_artifacts` rows, storage/download where bytes are created,
  cleanup, and storage absence.
- [ ] Implement saved-form/gallery lifecycle sweeps for every builtin form:
  create, reopen, save/edit, export decision dialog, delete/cleanup, and final
  local/remote absence.
- [ ] Add byte/object proof for every mutation that creates storage content.
- [ ] Gate: local row, local pre-sync `change_log`, remote row/object,
  UI-triggered cleanup sync, remote cleanup, and storage absence proof.

### Agent 3 - Role And Account Sweeps

- [ ] Inventory real login/account switching UI keys and role fixtures.
- [ ] Build same-device account switching sweep using real sessions.
- [ ] Prove denied controls/routes stay hidden for restricted roles.
- [ ] Gate: screenshots, actor context, selected project, providers, and sync
  dashboard state show no stale-account leakage.

### Agent 4 - Storage/RLS And Failure Injection

- [ ] Extend storage proof from photo objects to unauthorized access denial and
  additional file-backed buckets.
- [ ] Add queued-write offline/online and network-drop push/pull runs for the
  refactored flows.
- [ ] Add auth-refresh, background/foreground, restart, stale-lock, realtime
  burst, and dirty-scope overflow cases.
- [ ] Gate: specific failure classifications, evidence bundles, queue cleanup,
  and no silent pass on missing logs.

### Agent 5 - Backend/Device, Staging, And Scale

- [ ] Run backend/RLS pressure concurrently with refactored device `-Flow`
  gates and preserve layer-separated summaries.
- [ ] Expand deterministic fixture and stamp fixture version/hash into every
  artifact.
- [ ] Provision staging-only credentials and prove schema parity.
- [ ] Add headless app-sync actors with real sessions and isolated stores.
- [ ] Gate: repeated green staging/nightly/device artifacts before any
  15-20-account acceptance claim.

## Parallel Implementation Agent Lanes

### Agent 1 - S10 Regression And Cleanup-Only

- [x] Preflight S10 driver/debug-server readiness and queue state.
- [x] Add S10 refactored gate catalog/run-guide helper that rejects legacy
  all-modes and direct `/driver/sync` acceptance.
- [x] Run S10 `sync-only` through the refactored path.
- [x] Run S10 daily-entry, quantity, and photo isolated gates.
- [x] Run S10 contractor/personnel/equipment isolated gate.
- [x] Run S10 `combined` after isolated gates pass.
- [x] Add `cleanup-only` ledger replay mode for daily-entry, quantity, and
  photo ledgers. It requires explicit ledger paths, copies ledgers into the
  new run artifact, and reuses the existing ledger-owned cleanup helpers with
  UI-triggered sync.
- [x] Gate: no runtime errors, logging gaps, queue residue, cleanup residue, or
  direct `/driver/sync`.

### Agent 2 - Remaining UI Mutation Families

- [x] Build true UI-driven personnel/equipment/contractor mutation proof.
  Accepted S21 artifact:
  `.claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-contractors-fourth/summary.json`.
  This covers contractor, entry-contractor, default/custom personnel types,
  equipment, entry personnel count, and entry equipment rows with
  ledger-owned cleanup and UI-triggered cleanup sync.
- [x] Build true UI-driven MDOT 1126 typed-signature mutation proof.
- [x] Build true UI-driven MDOT 1126 expanded field/row mutation proof.
- [x] Build true UI-driven MDOT 0582B mutation proof. Accepted S21 artifact:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-accepted-initial/summary.json`.
- [ ] Build true UI-driven MDOT 1174R mutation proof. Implementation is wired;
  S21 acceptance is still open after non-acceptance diagnostics. Latest
  blocker: `20260418-s21-mdot1174r-after-expanded-sentinel` failed while
  opening Quantities after QA edits; cleanup and final queue drain passed.
- [ ] Build true UI-driven form export proof for each builtin form.
- [ ] Extend local record, local `change_log`, post-sync remote row, cleanup,
  and ledger-owned proof to each family.
- [ ] Add file/object proof where the mutation creates or changes bytes.
- [ ] Gate: every new family fails loudly on missing pre-sync `change_log`,
  post-sync unprocessed rows, runtime/log defects, or cleanup failure.

### Agent 3 - Role, Scope, And Account Switching

- [ ] Rerun real S21/S10 sessions for admin, inspector, engineer, and office
  technician without `MOCK_AUTH`.
- [ ] Prove denied routes and hidden controls for project management, PDF
  import, pay-app management, trash, and admin surfaces.
- [ ] Add same-device account switching sweeps and assert caches, selected
  project, providers, and synced scopes rebuild.
- [ ] Gate: no unauthorized project metadata or route/control flashes in UI,
  screenshots, debug logs, or sync dashboard state.

### Agent 4 - File/Storage Expansion

- [ ] Add small, normal, large, and GPS-EXIF image fixtures.
- [ ] Prove cross-device download/preview of uploaded photo objects.
- [ ] Prove Storage RLS denial for unauthorized role/project access.
- [ ] Extend object proof to form exports, entry documents, entry exports,
  pay-app exports, and signatures.
- [ ] Add `storage_cleanup_queue` assertions for delete/restore/purge paths.

### Agent 5 - Failure Injection And Observability

- [ ] Run queued-write offline/online, network-drop push/pull, upload timeout,
  auth refresh, background/foreground, process restart, stale `sync_lock`,
  realtime burst, and dirty-scope overflow cases.
- [ ] Replace remaining broad `driver_or_sync_error` classifications with
  specific categories where evidence allows.
  - 2026-04-18 partial: added specific harness classifications for cleanup
    ledger, storage proof/cleanup, change-log proof, and unsupported-flow
    failures. Legacy catch-path evidence-bundle reuse remains open.
- [ ] Deduplicate runtime error fingerprints and ensure catch-block logs use
  the same runtime scanner as normal step logs.
- [ ] Add backend log drain and Sentry drain checks where credentials and
  environment support them.

### Agent 6 - Fixture, Staging, And Scale

- [ ] Run backend/RLS pressure concurrently with a refactored device `-Flow`
  gate and keep child summaries layer-separated.
- [ ] Expand deterministic fixture to 15 projects and 10-20 active users with
  realistic records and binary/export artifacts.
- [ ] Add fixture version/hash to every backend/RLS and device-sync artifact.
- [ ] Run local reset, sync matrix, backend/RLS soak, and performance proof
  after fixture expansion.
- [ ] Provision staging with staging-only harness credentials, prove schema hash
  parity, and collect three green staging backend/RLS soaks plus three green
  nightly soaks.
- [ ] Add headless app-sync actors with isolated local stores and real sessions
  before claiming 10-20 app-user sync coverage.

## Review Loop

## 2026-04-18 Handoff: MDOT 1174R Stop, Artifact Audit, And Cleanup Policy

### Current State

- MDOT 1174R remains implemented/wired but not accepted.
- Latest clean non-acceptance:
  `20260418-s21-mdot1174r-visible-text-only`.
  It had `runtimeErrors=0`, `loggingGaps=0`, `queueDrainResult=drained`,
  no direct `/driver/sync`, cleanup passed, and final queue drained, but it
  failed scrolling the mounted Air/Slump composer field into visible range.
- Latest red-screen stop:
  `20260418-s21-mdot1174r-after-ensure-visible-scroll`.
  It correctly failed loudly during `mdot1174r-fields-and-rows` with
  `failureClassification=runtime_log_error`, `runtimeErrors=27`, duplicate
  GlobalKey fingerprints, detached render-object assertions, and local
  `form_responses` queue residue. It is not acceptance evidence.
- Current app/harness patch state:
  - `AppFormSection.expandedKey` now proves mounted expanded body content.
  - `/driver/text` now requires a visible mounted `EditableText`.
  - `AnimatedSize` was removed from the section body.
  - repeated-row composer state is kept alive while mounted.
  - `/driver/scroll-to-key` now tries `Scrollable.ensureVisible` before manual
    scanning, but this latest patch re-exposed the row-section GlobalKey
    failure and needs review before another acceptance attempt.
- Current live data state after the interrupted red-screen run showed local
  `form_responses` queue residue. Recovery used the Sync Dashboard UI through
  the refactored `sync-only` flow only:
  `20260418-s21-mdot1174r-redscreen-residue-recovery-sync-only` passed with
  zero runtime/logging gaps, drained queue, no blocked/unprocessed rows, and no
  direct `/driver/sync`; a live `/driver/change-log` check was empty afterward.

### Next Session Checklist

- [x] Recover S21 from the red-screen run:
  restart/reopen the driver if needed, clear debug logs, run refactored
  `sync-only` through the Sync Dashboard UI, and confirm `/driver/change-log`
  is empty.
- [x] Preserve the durable failure facts in docs/checkpoints before deleting
  raw artifacts: run id, pass/fail, failure class, runtime fingerprints,
  cleanup/queue outcome, and direct-sync status.
- [x] Audit and prune generated artifacts. Keep the latest accepted artifact,
  the latest blocker artifact, and one representative artifact per distinct
  failure class. Delete duplicate raw reruns after their facts are recorded.
- [x] Add a compact review index before deleting evidence:
  - Human report:
    `.codex/reports/2026-04-18-enterprise-sync-soak-result-index.md`
  - Machine report:
    `.codex/reports/2026-04-18-enterprise-sync-soak-result-index.json`
  - Exporter:
    `tools/sync-soak/Export-SoakResultIndex.ps1`
  - Current index covers 55 2026-04-18 enterprise-sync-soak runs, 15 passes,
    40 failures, and groups failures by `change_log_proof_failed`,
    `driver_or_sync_error`, `runtime_log_error`,
    `unprocessed_change_log_rows`, `widget_tap_not_found`, and
    `widget_wait_timeout`.
  - Full raw tree audit:
    `.codex/reports/2026-04-18-all-test-results-result-index.md` and
    `.codex/reports/2026-04-18-all-test-results-result-index.json`.
  - Full raw tree index covers 165 runs, 76 passes, 89 failures, and also
    captures older `cleanup_failed`, `queue_not_drained_or_sync_not_observed`,
    and `unknown_failure` classes before raw artifact cleanup.

### Failure Classes Captured Before Raw Artifact Cleanup

- [ ] `runtime_log_error`: still active for MDOT 1174R duplicate
  GlobalKey/detached render-object failures.
- [ ] `driver_or_sync_error`: broad legacy/harness catch-all remains too
  coarse; future work should keep replacing it with specific categories.
- [ ] `widget_wait_timeout` and `widget_tap_not_found`: historical driver/UI
  locator failures remain useful as evidence for key/sentinel hardening.
- [ ] `change_log_proof_failed`, `cleanup_failed`, and
  `unprocessed_change_log_rows`: historical cleanup/proof residues are indexed;
  current S21 live queue was recovered, but these stay as regression classes.
- [ ] `unknown_failure`: older runs lacked enough classification detail; keep
  the compact index entry and avoid accepting any run with this class.
- [ ] `queue_not_drained_or_sync_not_observed`: older device-sync measurement
  failure class; keep as a release-gate blocker if it recurs.
- [x] Clean local build/debug output before continuing:
  - Preserved `.codex/reports/*result-index.md/json` before deletion.
  - Removed ignored raw `.claude/test-results/2026-04-18` residue after the
    compact indexes captured all 2026-04-18 enterprise-sync-soak failures.
  - Removed generated `build/`, `.dart_tool/`, `android/.gradle`, root Flutter
    debug logs, debug APKs, build manifest, and generated device-state files.
  - Post-cleanup verification: `.dart_tool`, `build`, and `android/.gradle`
    are absent; `releases/android/debug` contains only `.gitkeep`; tracked
    historical `.claude/test-results` evidence remains at 497 files / 11.26 MB.
- [x] Clean device-side generated clutter conservatively. S21/S10 Downloads
  contain personal/non-harness files; only exact generated files were removed.
  Removed S21 `device-ci.db` and `conflict_*` DB/shm/wal files from
  `/sdcard/Download`; verification found no remaining S21/S10
  `device-ci`, `conflict_*.db`, FieldGuide, field-guide, soak, or debug
  matches in `/sdcard/Download`. Did not clear app data and did not bulk-delete
  S10 files.
- [ ] Add or wire an artifact-retention knob before more soak loops. Target
  behavior: retain all evidence for accepted runs and the first instance of a
  new failure class; for duplicate failures keep summaries/debug extracts and
  remove screenshots/logcat/widget-tree bulk unless explicitly requested.
- [x] Lock current form workflow/sentinel lessons into custom lint:
  - Added `form_workflow_sentinel_contract_sync` so
    `AppFormSection.expandedKey` remains on mounted expanded body content and
    cannot drift back to a header/icon sentinel.
  - Added `no_animated_size_in_form_workflows` so form workflow body surfaces
    cannot wrap keyed editable content in `AnimatedSize`, `AnimatedSwitcher`,
    or `AnimatedCrossFade`.
  - Removed the remaining `AnimatedSize` body wrapper from `FormAccordion`.
  - Extended existing sync lint allowlists for approved debug/repair owners and
    fixed the v61 migration test soft-delete filters so the ERROR-level custom
    lint gate is clean for these changes.
  - Verification: targeted `dart analyze`, lint-package tests for the new
    rules, `tools/test-sync-soak-harness.ps1`, `flutter test
    test/core/database/migration_v61_test.dart`, and full `dart run
    custom_lint` with only pre-existing WARNING-level findings remaining.
- [ ] Review MDOT 1174R row-section key/state ownership before retrying:
  duplicate GlobalKey and detached render-object errors are now the active
  blocker, not backend sync.
- [ ] Rerun S21 `mdot1174r-only` only after the above review. Accept only when
  the artifact proves local markers, local pre-sync `change_log`, post-sync
  remote `form_responses`, ledger-owned cleanup, UI-triggered cleanup sync,
  final empty queue, zero runtime/logging gaps, and no direct `/driver/sync`.
- [ ] After MDOT 1174R acceptance, move to builtin form exports and
  saved-form/gallery lifecycle sweeps.

After each lane lands:

1. Run the lane's script/unit/widget tests.
2. Run `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` if the soak
   harness changed.
3. Run the relevant S21/S10 live gate when the lane touches device behavior.
4. Review the controlling specs and this task list for drift.
5. Patch docs/checkpoints only after artifact-backed evidence exists.

Spec intent is not fully captured until the ship bar in the enterprise sync
soak hardening spec and the external Phase 7 release gates are all green at the
same commit.

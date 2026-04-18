# MDOT 1126 Typed-Signature Sync Soak Plan

## Purpose

Implement the next refactored device-sync soak lane for the MDOT 1126
typed-signature path. This lane must prove a real UI-created form response,
typed signature, signature audit row, signature file row, Supabase Storage
object, ledger-owned cleanup, UI-triggered cleanup sync, and final local/remote
absence. It is the first form/signature/file-backed mutation gate after the
daily-entry, quantity, photo, contractor graph, S10 regression, and cleanup-only
replay lanes.

The active implementation target is an isolated refactored flow:

```powershell
pwsh -NoProfile -File tools/enterprise-sync-soak-lab.ps1 `
  -Actors "S21:4948:inspector:1" `
  -Rounds 1 `
  -RampUpSeconds 0 `
  -Flow mdot1126-signature-only `
  -RunId 20260418-s21-mdot1126-signature-initial
```

Do not use the legacy all-modes runner or `-UiMutationModes` as acceptance
evidence.

## Status - 2026-04-18

The isolated MDOT 1126 typed-signature lane is implemented and accepted on
S21, S21 cleanup-only replay, and S10 regression. MDOT 1126 expanded
fields/rows are accepted on S21, and the MDOT 0582B form-response mutation lane
is accepted on S21 as the next form-response baseline. The accepted MDOT 1126
artifacts prove the intended row family (`form_responses`, `signature_files`,
`signature_audit_log`), signature storage download, ledger-owned cleanup,
storage delete, storage absence, final queue drain, zero runtime errors, zero
logging gaps, and no direct `/driver/sync`.

Spec review after the accepted runs found four harness-contract hardening
items that must be closed before broader form/signature scale-up:

- [x] Fail fast when the preflight `/driver/change-log` is not empty for
  mutation acceptance runs, instead of only snapshotting it.
- [x] Require `signature_files.remote_path` to be present in the synced row;
  do not infer `signatures/{companyId}/{projectId}/{id}.png` as acceptance
  proof.
- [x] Treat a missing cleanup ledger `remotePath` as a storage-proof failure,
  not as permission to skip delete/absence proof.
- [x] Add focused harness self-tests for `mdot1126-signature-only` flow
  validation, `signatures` bucket/path proof, and missing-ID/missing-or-wrong
  `remotePath` cleanup rejection.
- [x] Fix the local schema root cause behind broader signature integrity drift:
  `signature_files.local_path` is now nullable locally, matching Supabase, and
  v61 rebuilds existing local databases so cross-device signature metadata can
  pull even when the remote row has no device-local file path.

## Acceptance Gate

- [x] Flow is implemented under `tools/sync-soak/` as a refactored
  state-machine module.
- [x] `tools/enterprise-sync-soak-lab.ps1` exposes `-Flow
  mdot1126-signature-only`.
- [x] `tools/enterprise-sync-concurrent-soak.ps1` accepts the same flow for
  later device-lab orchestration.
- [x] Harness self-tests pass:
  `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1`.
- [x] The S21 preflight queue is empty before the run.
- [x] The S21 run uses only Sync Dashboard UI sync; `directDriverSyncEndpointUsed`
  remains `false`.
- [x] The form is created from `/report/:entryId`, not from a detached
  form-gallery path.
- [x] Local `change_log` rows are proven before sync for all created/changed
  tables:
  - [x] `form_responses`
  - [x] `signature_files`
  - [x] `signature_audit_log`
- [x] Post-sign local proof validates:
  - [x] `form_responses.form_type == mdot_1126`
  - [x] `form_responses.entry_id == target.entryId`
  - [x] `form_responses.project_id == target.projectId`
  - [x] `form_responses.response_data.signature_audit_id == signatureAuditId`
  - [x] `form_responses.response_data.typed_signer_name == typedSignerName`
  - [x] `signature_audit_log.signed_record_type == form_response`
  - [x] `signature_audit_log.signed_record_id == formResponseId`
  - [x] `signature_audit_log.signature_file_id == signatureFileId`
  - [x] `signature_files.project_id == target.projectId`
  - [x] `signature_files.mime_type == image/png`
  - [x] `signature_files.file_size_bytes > 0`
  - [x] `signature_files.sha256` is non-empty
- [x] Post-mutation UI sync proves remote rows for all three tables.
- [x] Post-sync signature storage object is downloaded from Supabase Storage:
  - [x] bucket `signatures`
  - [x] path `signature_files.remote_path`
  - [x] byte count greater than zero
  - [x] SHA-256 captured in artifact
- [x] Mutation ledger records every cleanup obligation:
  - [x] `table = form_signature`
  - [x] `entryId`
  - [x] `projectId`
  - [x] `formResponseId`
  - [x] `signatureFileId`
  - [x] `signatureAuditId`
  - [x] `typedSignerName`
  - [x] `remotePath`
  - [x] `signatureSha256`
  - [x] `cleanupRequired = true`
- [x] Cleanup is ledger-owned only; no broad delete by project, form type, or
  marker.
- [x] Cleanup soft-deletes `signature_audit_log`, `signature_files`, and
  `form_responses` through existing driver update seams, then uses Sync
  Dashboard UI sync.
- [x] Post-cleanup proof validates local and remote soft-delete state for all
  three rows.
- [x] Post-cleanup storage proof deletes the signature object and then proves
  object absence.
- [x] Final S21 `/driver/change-log` is empty:
  - [x] `queueDrainResult = drained`
  - [x] `blockedRowCount = 0`
  - [x] `unprocessedRowCount = 0`
  - [x] `maxRetryCount = 0`
- [x] The run fails loudly on runtime errors, red screens, logging gaps, queue
  residue, storage proof failure, cleanup failure, or direct driver sync usage.
- [x] Plan/checkpoint docs are updated with artifact paths and remaining work.

## UI Path

The initial implementation should use the report-attached form path because the
spec requires creation from `/report/:entryId`.

- [ ] Resolve a seeded target with the same project/date/entry helper used by
  the daily-entry, quantity, photo, and contractor flows.
- [ ] Navigate to `/report/{entryId}`.
- [ ] Wait for `entry_editor_screen` and `entry_editor_scroll`.
- [ ] Scroll to `report_add_form_button`.
- [ ] Tap `report_add_form_button`.
- [ ] Wait for `form_selection_dialog`.
- [ ] Tap `form_selection_item_mdot_1126`.
- [ ] Wait for `/form/{responseId}` and `mdot1126_form_screen`.
- [ ] Identify the generated `form_responses` row from local data and
  `change_log`, scoped by `entry_id`, `project_id`, and `form_type`.
- [ ] Select the signature workflow section with
  `mdot1126_workflow_nav_signature`.
- [ ] Type the current real profile display name into
  `mdot1126_typed_signature_field`.
- [ ] Tap `mdot1126_typed_signature_sign_button`.
- [ ] Wait until local `form_responses.response_data.signature_audit_id`,
  `signature_audit_log`, and `signature_files` exist.

The expected signer name is resolved by the app from
`AuthProvider.userProfile.displayName`, falling back to the form's inspector
name. The harness should derive the typed name from live actor context or local
`user_profiles`, not from a test-only hook.

## App-Side Enablers

- [x] Extend `DriverDataSyncPolicy.queryableDataTables` with:
  - [x] `signature_files`
  - [x] `signature_audit_log`
- [x] Extend `DriverDataSyncPolicy.genericUpdateRecordTables` with the same
  tables so ledger-owned soft-delete cleanup can reuse `/driver/update-record`.
- [x] Keep this scoped to already-synced production tables. Do not add
  mutation-only test hooks or bypass signature production services.
- [x] Add/update tests for the policy if a driver-policy test already exists.

## Harness Implementation

- [x] Add `tools/sync-soak/Flow.Mdot1126Signature.ps1`.
- [x] Reuse existing helpers instead of duplicating orchestration:
  - [x] state transitions from `StateMachine.ps1`
  - [x] target resolution from existing UI mutation flows
  - [x] Sync Dashboard flow from `Flow.SyncDashboard.ps1`
  - [x] row query/proof helpers from `Flow.Contractors.ps1`
  - [x] storage proof/delete/absence helpers from `Flow.Photo.ps1`
  - [x] ledger helpers from `SoakModels.ps1`
- [x] Implement `Invoke-SoakMdot1126SignatureCreate`.
- [x] Implement `Get-SoakCurrentProfileDisplayName`.
- [x] Implement `Wait-SoakMdot1126SignatureRows`.
- [x] Implement `Invoke-SoakMdot1126SignatureLedgerCleanup`.
- [x] Implement `Invoke-SoakMdot1126SignatureOnlyRun`.
- [x] Wire the module in `tools/enterprise-sync-soak-lab.ps1`.
- [x] Wire the flow into `tools/enterprise-sync-concurrent-soak.ps1`.
- [x] Add `form_signature` support to `tools/sync-soak/Flow.CleanupOnly.ps1`
  after the isolated lane can produce a valid ledger.
- [x] Add focused parser/self-tests for:
  - [x] flow validation accepts `mdot1126-signature-only`
  - [x] cleanup-only dispatch accepts `form_signature`
  - [x] signature storage path proof uses bucket `signatures`
  - [x] ledger-owned cleanup rejects missing IDs and missing or mismatched
    `remotePath`

## Live Verification Sequence

Run these only after parser/self-tests pass.

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:3947/clear -TimeoutSec 5
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:4948/driver/change-log -TimeoutSec 10
```

If the S21 queue is empty, run:

```powershell
pwsh -NoProfile -File tools/enterprise-sync-soak-lab.ps1 `
  -Actors "S21:4948:inspector:1" `
  -Rounds 1 `
  -RampUpSeconds 0 `
  -Flow mdot1126-signature-only `
  -RunId 20260418-s21-mdot1126-signature-initial
```

On any failure, stop and inspect artifacts immediately. Do not click through red
screens or continue to other lanes.

After a green S21 pass:

- [x] Run S10 refactored regression for `mdot1126-signature-only`.
- [x] Run S21 cleanup-only replay against the accepted signature ledger.
- [x] Add the MDOT 1126 lane to the broader S21/S10 combined-regression plan
  only after isolated S21, isolated S10, and cleanup replay are green.

## Still Open After This Lane

- [x] MDOT 1126 expanded field/row flow beyond signature-only: rainfall rows,
  SESC measures, remarks, save/reopen, signature proof, and cleanup proof are
  accepted on S21 through `mdot1126-expanded-only`:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-signature-ready-or-nav/summary.json`.
  Builtin export proof remains tracked in the generic export lane below.
- [x] MDOT 0582B form-response mutation flow: standards, proctor rows, test
  rows, remarks, sync proof, and cleanup are accepted on S21 through
  `mdot0582b-only`:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-accepted-initial/summary.json`.
  MDOT 0582B export artifact/storage proof remains tracked in the generic
  export lane below.
- [ ] MDOT 1174R full form flow: concrete fields/list rows, sync proof,
  cleanup, and export artifact proof.
- [ ] Generic builtin form export coverage for `mdot_0582b`, `mdot_1126`, and
  `mdot_1174r`, including storage download/delete/absence where bytes are
  created.
- [ ] Saved-form/gallery lifecycle sweeps for all builtin forms.
- [ ] Role/account sweeps.
- [ ] Broader storage/RLS denial checks.
- [ ] Failure injection.
- [ ] Backend/device overlap.
- [ ] Staging.
- [ ] Scale/headless 15-20 actors.
- [ ] Other file-backed families: form exports, entry exports, documents, pay
  application exports.
- [ ] Live post-v61 proof that the old signature integrity drift no longer
  appears after S21/S10 pull remote signature rows created by the other device.
  S21 post-v61 backlog drain is accepted; S10 post-v61 cross-device proof
  remains open.

## 2026-04-18 Evidence Update

- S21 accepted isolated MDOT 1126 typed-signature run:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-accepted-with-cleanup-sync-retry/summary.json`.
- S21 cleanup-only replay of the accepted signature ledger:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-cleanup-only-replay-accepted-ledger/summary.json`.
- S10 accepted isolated MDOT 1126 typed-signature regression:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot1126-signature-regression-with-cleanup-sync-retry/summary.json`.
- All accepted summaries reported `passed=true`, `failedActorRounds=0`,
  `runtimeErrors=0`, `loggingGaps=0`, `queueDrainResult=drained`,
  `blockedRowCount=0`, `unprocessedRowCount=0`, `maxRetryCount=0`, and
  `directDriverSyncEndpointUsed=false`.
- Accepted ledgers prove `form_responses`, `signature_files`,
  `signature_audit_log`, signature storage download, ledger-owned cleanup,
  storage delete, and storage absence.
- Harness-contract hardening after acceptance:
  - missing `signature_files.remote_path` now fails closed;
  - cleanup-only requires ledger `remotePath`;
  - cleanup-only rejects ledger `remotePath` that does not match the local
    `signature_files.remote_path`;
  - local schema v61 makes `signature_files.local_path` nullable to match
    Supabase and support cross-device signature metadata pulls.
- S21 post-v61 signature backlog drain:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-post-v61-signature-backlog-sync-only/summary.json`.
  It ran after the S21 driver rebuild to schemaVersion 61, surfaced remote
  signature metadata backlog locally, drained through Sync Dashboard UI sync,
  and ended with an empty queue and no direct driver sync.
- S21 accepted MDOT 1126 expanded fields/rows:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-signature-ready-or-nav/summary.json`.
  The run reported `passed=true`, `failedActorRounds=0`, `runtimeErrors=0`,
  `loggingGaps=0`, `queueDrainResult=drained`, `blockedRowCount=0`,
  `unprocessedRowCount=0`, `maxRetryCount=0`, and
  `directDriverSyncEndpointUsed=false`.
- The accepted expanded run proved local pre-sync `change_log` rows, post-sync
  remote `form_responses`, `signature_files`, and `signature_audit_log`, typed
  signature storage download, ledger-owned cleanup, storage delete/absence,
  and final empty S21 queue.
- Non-acceptance diagnostics are preserved in
  `20260418-s21-mdot1126-expanded-initial` and
  `20260418-s21-mdot1126-expanded-after-rainfall-ui`; those failures drove the
  section-navigation, rainfall-row visibility, and signature-ready hardening
  and cleaned up through UI sync.

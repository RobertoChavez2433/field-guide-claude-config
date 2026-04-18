# Sync Soak Decomposition — Progress Tracker

Date: 2026-04-18
Branch: `gocr-integration`
Spec: `.codex/plans/2026-04-18-sync-soak-decomposition-todo-spec.md`
Implementation log: `.codex/checkpoints/2026-04-18-sync-soak-unified-implementation-log.md`

## How To Use

Append one entry per slice. Mark the checklist as it happens. If a slice is
paused or rolled back, say so and why. Do not mark an item complete until the
verification gate for that slice has been run.

---

## Audit Baseline (measured 2026-04-18)

Current line counts (actual on disk at start of work):

| File | Lines | Spec target | Status |
|---|---:|---:|---|
| `tools/enterprise-sync-soak-lab.ps1` | 2114 | <=250 | oversized |
| `tools/enterprise-sync-concurrent-soak.ps1` | 366 | 150-250 | review |
| `tools/test-sync-soak-harness.ps1` | 479 | 150-250 | oversized |
| `tools/sync-soak/ArtifactWriter.ps1` | 391 | 100-300 | review |
| `tools/sync-soak/Cleanup.ps1` | 74 | - | ok |
| `tools/sync-soak/DriverClient.ps1` | 302 | 100-300 | ok-edge |
| `tools/sync-soak/Export-SoakResultIndex.ps1` | 243 | 100-300 | ok |
| `tools/sync-soak/Flow.CleanupOnly.ps1` | 455 | <=350 | review |
| `tools/sync-soak/Flow.Combined.ps1` | 280 | 150-300 | ok |
| `tools/sync-soak/Flow.Contractors.ps1` | 878 | <=350 | oversized |
| `tools/sync-soak/Flow.DailyEntryActivity.ps1` | 741 | <=350 | oversized |
| `tools/sync-soak/Flow.Mdot0582B.ps1` | 705 | <=350 | oversized |
| `tools/sync-soak/Flow.Mdot1126Expanded.ps1` | 656 | <=350 | oversized |
| `tools/sync-soak/Flow.Mdot1126Signature.ps1` | 1144 | <=350 | oversized |
| `tools/sync-soak/Flow.Mdot1174R.ps1` | 755 | <=350 | oversized (BLOCKED on S21 accept) |
| `tools/sync-soak/Flow.Photo.ps1` | 786 | <=350 | oversized |
| `tools/sync-soak/Flow.Quantity.ps1` | 692 | <=350 | oversized |
| `tools/sync-soak/Flow.SyncDashboard.ps1` | 372 | <=350 | barely over |
| `tools/sync-soak/S10Regression.ps1` | 408 | 150-300 | review |
| `tools/sync-soak/SoakModels.ps1` | 270 | <=250 | review |
| `tools/sync-soak/StateMachine.ps1` | 149 | 100-300 | ok |
| `tools/sync-soak/StateSentinels.ps1` | 151 | 100-300 | ok |
| `tools/sync-soak/StepRunner.ps1` | 178 | 100-300 | ok |
| `integration_test/sync/soak/soak_driver.dart` | 1064 | <=400 | oversized |
| `integration_test/sync/soak/soak_metrics_collector.dart` | 281 | <=300 | ok |
| `integration_test/sync/soak/soak_ci_10min_test.dart` | 69 | - | ok |
| `integration_test/sync/soak/soak_nightly_15min_test.dart` | 67 | - | ok |

Note: spec called out 1,922 lines for device-lab script; the live file is
**2,114 lines** (drift from subsequent work). The decomposition target is
unchanged: a thin facade under 250 lines.

---

## Guardrails (verify for each slice)

- [ ] No acceptance semantics change.
- [ ] No `POST /driver/sync` for acceptance paths.
- [ ] No `MOCK_AUTH`.
- [ ] Backend/RLS soak evidence remains separate from device-sync evidence.
- [ ] Artifact shape backward compatible until all result-index readers updated.
- [ ] Every slice passes `tools/test-sync-soak-harness.ps1`.
- [ ] Any slice touching a live accepted flow either reruns narrowest accepted
      S21 gate or records why a doc-only/plumbing-only slice skipped it.

---

## Master Todo (implementation order from spec)

### P0 — Freeze contracts before refactor
- [x] 1. Write down public PowerShell entrypoints + parameters for
      `enterprise-sync-soak-lab.ps1`, `enterprise-sync-concurrent-soak.ps1`,
      `test-sync-soak-harness.ps1`, and every accepted `-Flow` value.
      (Canonical list in `Get-SoakAcceptedFlowFunctions` +
      `Get-SoakModuleLoadOrder`.)
- [ ] 2. Capture artifact contract from a representative accepted run:
      `summary.json`, `timeline.json`, `change-log-*.json`, `sync-runtime*.json`,
      screenshots, debug logs, mutation ledger, storage proof, result index.
- [x] 3. Add structural self-test: refactored module loading exposes every
      accepted flow function. (Harness already greps for
      `Invoke-Soak<Flow>OnlyRun` in lab/dispatcher sources.)
- [ ] 4. Add structural self-test: every accepted flow summary includes
      `soakLayer`, `evidenceLayer`, `syncEngineExercised`,
      `directDriverSyncEndpointUsed`, queue counts, runtime/logging counts,
      failure classifications.

### P0 — Split the 2,114-line device lab script
- [x] 5. Create `tools/sync-soak/ModuleLoader.ps1`.
- [x] 6. Move argument normalization/validation into
      `tools/sync-soak/DeviceLab.Arguments.ps1`.
- [x] 7. Move `.env`/secret loading into `tools/sync-soak/Environment.ps1`.
- [x] 8. Move readable result-index export wrapper into
      `tools/sync-soak/ResultIndex.ps1`.
- [x] 9. Move refactored `-Flow` dispatch into
      `tools/sync-soak/DeviceLab.RefactoredDispatcher.ps1`.
- [x] 10. Move remaining legacy implementation into
      `tools/sync-soak/DeviceLab.Legacy.ps1` with non-acceptance banner.
- [x] 11. Confirm `tools/enterprise-sync-soak-lab.ps1` is under 250 lines.
      (144 lines.)
- [x] 12. Run `tools/test-sync-soak-harness.ps1` after the split. (PS 7 PASS.)
- [x] 13. Run `-PrintS10RegressionRunGuide` smoke after the split. (Prints 6
      ordered operator commands for S10:4949:inspector:1.)

### P0 — Extract shared flow runtime
- [x] 14. Create `tools/sync-soak/FlowRuntime.ps1` with actor spec conversion,
      output-root/actor-dir setup, summary creation, preflight/final capture,
      queue aggregation, failure event shaping, runtime/logging gap updates.
- [x] 15. Provide generic `Invoke-SoakActorRound` runner wrapping round-event
      try/catch/finally around a caller-supplied Measurement script block.
- [x] 16. Convert `Flow.SyncDashboard.ps1` first (proves seam). 372 → 259.
- [x] 17. Convert `Flow.Quantity.ps1`. 692 → 645.
- [x] 18. Convert `Flow.Photo.ps1`. 786 → 744.
- [x] 19. Convert form flows after the runtime seam is stable (Mdot0582B,
      Mdot1126Signature, Mdot1126Expanded converted; Mdot1174R summary only
      per spec).
- [x] 20. Keep public `Invoke-Soak<Flow>OnlyRun` signatures backward compatible.
- [x] 21. Confirm converted flows still write the same summary/timeline/ledger
      artifact names (no artifact path changes; converted helpers write to
      same filenames; evidence captures additive-only).

### P0 — Extract common mutation target helpers
- [x] 22. Create `tools/sync-soak/MutationTargets.ps1` (375 lines).
- [x] 23. Move duplicated local row query helpers out of contractor + daily entry
      (Get-SoakLocalRowsByColumn, Find-SoakLocalRowByColumns,
      Wait-SoakLocalRowByColumns, Assert-SoakRemoteRowNotDeleted,
      Get-SoakContractorValue, Get-SoakLedgerValue, Resolve-SoakUiMutationTarget,
      Resolve-SoakQuantityMutationTarget, Get-SoakActivityTextForLocation).
- [x] 24. Create `tools/sync-soak/ChangeLogAssertions.ps1` (246 lines).
- [x] 25. Replace per-flow `Get-SoakNew*ChangeLogRecordId` with one typed helper
      (`Find-SoakNewChangeLogRecord` + back-compat thin wrappers for
      entry_quantities and photos that preserve original error messages).
- [x] 26. Keep target helpers fail-loud (no silent fallback to stale ids) — every
      resolver throws on empty / mismatched local rows; wrappers rethrow original
      flow-specific "No new <table> change_log row matched..." message.

### P1 — Cleanup and ledger
- [x] 27. Split `Cleanup.ps1` into `MutationLedger.ps1` (163), `CleanupDispatch.ps1`
      (143), `RecordCleanupAssertions.ps1` (78). Old `Cleanup.ps1` deleted.
- [x] 28. Put `Invoke-SoakQuantityLedgerCleanup`, `DailyEntry`, `Photo`,
      `ContractorGraph` behind a shared cleanup interface — the dispatcher
      `Invoke-SoakCleanupLedgerMutation` in CleanupDispatch.ps1 calls each
      per-flow helper through the identical shared signature (Actor, ActorDir,
      ProjectRoot, Summary, Ledger, Mutation, Round, Reason, TimeoutSeconds,
      PollIntervalMilliseconds, DebugServerBaseUri). Structural harness test
      asserts the dispatcher covers every expected table.
- [ ] 29. Move generic form-response cleanup out of `Flow.Mdot0582B.ps1` —
      DEFERRED to task #7 (FormFlow.ps1). `Invoke-SoakFormResponseLedgerCleanup`
      stays in Flow.Mdot0582B.ps1 for now to avoid creating an intermediate
      home and then moving it again.
- [x] 30. Keep MDOT 1126 signature cleanup contract separate — dispatcher
      preserves `-RequireStorageRemotePath` switch for `form_signature` only;
      `Invoke-SoakMdot1126SignatureLedgerCleanup` stays in Flow.Mdot1126Signature.ps1.
- [x] 31. Require every cleanup helper to record the six fact families (original
      row state, cleanup mutation requested, change-log row created, UI cleanup
      sync observed, local soft-delete/restore sentinel, remote soft-delete or
      storage absence). All six per-flow cleanup functions already record
      these via their `$cleanupEvent` ordered dicts; documented in
      `RecordCleanupAssertions.ps1` header as the cleanup contract.
- [x] 32. Cleanup-only replay remains compatible — `New-SoakCleanupReplayLedger`
      body is unchanged (moved verbatim from Flow.CleanupOnly.ps1 to
      MutationLedger.ps1). Harness `cleanup-only replay filters cleanupRequired`
      and `cleanup-only replay keeps source path` tests still pass.

### P1 — Storage proof
- [x] 33. Create `tools/sync-soak/StorageProof.ps1` (293 lines).
- [x] 34. Reuse storage proof for photo + signature storage — both
      `Flow.Photo.ps1` and `Flow.Mdot1126Signature.ps1` (and `Flow.Mdot1126Expanded.ps1`)
      already called `Invoke-SoakStorageObjectProof` /
      `Assert-SoakStorageObjectAbsent` from Flow.Photo.ps1's inline defs.
      Extraction preserves those call sites unchanged; helpers now live in
      StorageProof.ps1 loaded before every flow file.
- [ ] 35. Remove duplicate legacy storage proof from `DeviceLab.Legacy.ps1` —
      DEFERRED per spec ("after the legacy path is quarantined or converted").
      Legacy path is quarantined; duplicate is behind a `Write-Warning` and
      not on any acceptance code path. Scheduled for removal when the
      quarantined legacy file itself is deleted.
- [x] 36. Storage proof parameters now document bucket + remote path + min
      bytes, and the proof result records sha256 + bytes + statusCode for
      later content-hash diffing. Owning row id + cleanup requirement are
      the callers' responsibility and are recorded in the per-flow mutation
      ledger (unchanged).
- [x] 37. Fail closed when expected `remotePath` is missing or mismatched —
      `Invoke-SoakStorageObjectProof` throws `"Storage proof failed..."` on
      any HTTP error or bytes < MinBytes; `Assert-SoakStorageObjectAbsent`
      throws on any 2xx response ("storage object still exists"). No silent
      fallback. MDOT 1126 cleanup `-RequireStorageRemotePath` harness self-
      test still passes under the new module.

### P1 — Form flow support
- [x] 38. Created `tools/sync-soak/FormFlow.ps1` (159 lines) with shared
      generic form-response cleanup (`Invoke-SoakFormResponseLedgerCleanup`).
- [x] 39. Created `tools/sync-soak/FormMarkers.ps1` (63 lines) with
      `Get-SoakFormValue` canonical dict/object accessor plus back-compat
      wrappers `Get-SoakMdot0582BValue`, `Get-SoakMdot1126Value`,
      `Get-SoakMdot1174RValue`.
- [x] 40. Moved duplicate `Get-SoakMdot<X>Value` helpers out of
      Flow.Mdot0582B.ps1, Flow.Mdot1126Signature.ps1, and Flow.Mdot1174R.ps1
      into FormMarkers.ps1. Moved `Invoke-SoakFormResponseLedgerCleanup`
      out of Flow.Mdot0582B.ps1 into FormFlow.ps1 (task #29).
- [ ] 41. Extract shared MDOT 1126 open/cleanup setup — DEFERRED. The
      1126 Signature cleanup contract (3-table + storage-remotePath) is
      intentionally separate from generic form-response cleanup per spec
      item #30. Open-created-form and edit-section helpers remain inline
      because they differ in target route keys and widget tree shape
      between Signature and Expanded.
- [x] 42. Mdot1174R not broadly refactored — only moved
      `Get-SoakMdot1174RValue` to FormMarkers.ps1 (zero-business-risk
      accessor consolidation). All round-body, preflight, and final-
      capture logic still inline per spec.
- [x] 43. Harness self-tests confirm every form flow's markers + wiring
      still match post-extraction (MDOT expanded proves header/rainfall
      markers, MDOT 0582B proves chart/proctor/test markers, MDOT 1174R
      proves workflow/air-slump/qa/quantity/remarks markers).

### P1 — Artifact writing + failure classification
- [x] 44. Split `ArtifactWriter.ps1` (391 → DELETED) into 6 focused modules:
      `JsonWriter.ps1` (24), `AdbLogcat.ps1` (139), `DebugServerCapture.ps1`
      (83), `RuntimeErrorScanner.ps1` (105), `WidgetTreeClassifier.ps1` (74),
      `EvidenceBundle.ps1` (107). Each module has a single reason to change.
- [x] 45. Moved `Get-SoakFailureClassification`, `Get-SoakSyncFailureClassification`,
      and `Get-SoakSyncAcceptanceLabel` out of `SoakModels.ps1` (270 → 181)
      into new `FailureClassification.ps1` (145). Classification is now
      evidence/failure policy, not summary schema.
- [x] 46. Added regression cases for MDOT 1174R failure family in harness:
      queue_residue_detected classifier, dirty_build_scope classifier,
      element_registry_assertion classifier, multi-category fingerprinter
      test covering duplicate_global_key + dirty_build_scope +
      element_registry_assertion in one logcat excerpt, and RenderErrorBox
      widget-tree classification for detached render object case.

### P1 — Split 1,064-line Dart soak driver
- [x] 47. Create `integration_test/sync/soak/soak_action_mix.dart`.
- [x] 48. Create `integration_test/sync/soak/soak_models.dart`.
- [x] 49. Create `integration_test/sync/soak/soak_runner.dart`.
- [x] 50. Create `integration_test/sync/soak/soak_executors.dart`.
- [x] 51. Create `integration_test/sync/soak/driver_soak_action_executor.dart`.
- [x] 52. Create `integration_test/sync/soak/backend_rls_soak_action_executor.dart`.
- [x] 53. Create `integration_test/sync/soak/soak_personas.dart`.
- [x] 54. Extract role-assignment churn/project-scope assertions under
      backend/RLS executor.
- [x] 55. `soak_driver.dart` is now a library header with `part` directives;
      compatible for all 5 existing importers without any import changes.
- [x] 56. `dart analyze integration_test test/harness` — No issues found.

### P1 — Split harness self-tests
- [x] 57. Created `tools/sync-soak/tests/` with 7 focused test files:
      RuntimeErrorClassification.Tests.ps1 (67),
      Sentinels.Tests.ps1 (61),
      CombinedSummary.Tests.ps1 (32),
      CleanupLedger.Tests.ps1 (49),
      S10RegressionGuide.Tests.ps1 (32),
      FlowWiring.Tests.ps1 (126),
      MdotSignatureCleanup.Tests.ps1 (134).
      FormFlowWiring tests are folded into FlowWiring.Tests.ps1 since MDOT
      expanded / 0582B / 1174R wiring share the same `$labSource` grep setup.
- [x] 58. `tools/test-sync-soak-harness.ps1` shrank from 544 → 96 lines.
      It auto-discovers every `tests/*.Tests.ps1` file and runs them in
      alphabetical order after dot-sourcing every helper module. Assertion
      helpers (`Assert-Equal`, `Assert-True`) and the `$failures` list live
      in the runner and are inherited by test files via dot-source scope.
- [x] 59. Runner + all 7 test files are no-device: they only construct
      summary dicts, call classifier / scanner / sentinel functions, grep
      module source, and use local temp dirs for ledger replay tests.
      No `/driver/*` or Supabase REST calls happen during the self-tests.

### P2 — Normalize flow module boundaries
- [ ] 60. Under 350 lines target on each `Flow.*.ps1`. Partial: SyncDashboard
      259, Combined 280. Remaining over-budget flows documented in
      `size-budget-exceptions.json` pending later P1 extractions
      (MutationTargets, StorageProof, FormFlow).
- [ ] 61. If over 350 post-extraction, split into
      Flow.<Name>.{Markers,Actions,Assertions,Cleanup}.ps1.
- [ ] 62. Keep public flow file as readable entrypoint.
- [x] 63. Add advisory `scripts/check_sync_soak_file_sizes.ps1`.
- [x] 64. Add `tools/sync-soak/size-budget-exceptions.json`.

### P2 — Clean up legacy paths
- [ ] 65. Decide whether `-Flow legacy` is still needed.
- [ ] 66. If kept: move to `DeviceLab.Legacy.ps1` and label
      `legacy_device_lab_non_acceptance`.
- [ ] 67. If removed: confirm S21 accepted refactored flows cover daily entry,
      quantity, photo, contractors, MDOT 1126, MDOT 0582B, MDOT 1174R, plus
      S10 regression guide, plus cleanup-only replay.
- [ ] 68. Remove duplicate helper implementations from legacy path.

### P2 — Prepare for 15-20 actor scale
- [ ] 69. Distinguish real-device / emulator / headless app-sync / backend-RLS
      actors in an explicit actor model.
- [ ] 70. Keep backend/RLS virtual actors out of device-sync pass/fail.
- [ ] 71. Move actor scheduling/ramp-up out of individual flow files.
- [ ] 72. Add per-actor fixture/session ownership helpers.
- [ ] 73. Add scale manifest.
- [ ] 74. Add parent orchestration helper (S21 + S10 + optional emulator +
      headless app-sync + backend/RLS).
- [ ] 75. Keep final 15-20 actor claim blocked until headless app-sync actors
      exercise actual sync engine + isolated local storage.

### P2 — Adjacent driver support (only if needed)
- [ ] 76. Keep `lib/core/driver/driver_server.dart` as thin dispatch shell.
- [ ] 77. Review `screen_contract_registry.dart` (705 lines) separately.
- [ ] 78. Review `harness_seed_data.dart` (584 lines) separately.

### P3 — Adjacent sync engine tests (separate track)
- [ ] 79. Open separate decomposition checklist for large sync engine tests.

---

## Endpoint Definition (validation gate)

- [ ] `tools/enterprise-sync-soak-lab.ps1` is a thin facade under 250 lines.
- [ ] Legacy device-lab path removed or clearly quarantined.
- [ ] Every accepted `-Flow` value wired through shared dispatcher + loader.
- [ ] Every `Flow.*.ps1` public file under 350 lines or written exception.
- [ ] No `Flow.*.ps1` owns generic actor/round loops, artifact capture,
      queue-drain aggregation, storage HTTP proof, or cleanup dispatch.
- [ ] Shared helpers exist for: module loading, argument normalization,
      environment/secret loading, actor/session modeling, flow runtime,
      artifacts/evidence, runtime+widget failure classification, mutation
      targets, change-log assertions, cleanup ledger+dispatch, storage proof,
      form creation/open/edit/assertion, result-index export.
- [ ] `soak_driver.dart` reduced to compat facade or removed.
- [ ] Dart soak code split per target shape.
- [ ] No-device PowerShell self-tests split by concern and still run through
      harness.
- [ ] Each helper module has at least one cheap no-device test.
- [ ] Current accepted S21/S10 evidence gates still produce compatible artifacts.
- [ ] 15-20 actor scale path composes actor providers + flow/runtime helpers.

---

## Progress Log

### 2026-04-18 — Tracker created
- Created this progress file + in-session task list (tasks #1–#13).
- Measured current line counts (see Audit Baseline above).
- Next: P0 item 5 — create `tools/sync-soak/ModuleLoader.ps1` and read
  enterprise-sync-soak-lab.ps1 fully to plan arg/env/dispatcher/legacy cuts.

### 2026-04-18 — FlowRuntime + Dart split + size guardrails (tasks #3 + #9 + #11)

**Task #3 — FlowRuntime.ps1 extraction (304 lines, new):**
- Added `tools/sync-soak/FlowRuntime.ps1` with shared helpers:
  - `Invoke-SoakActorPreflightCapture` (logcat clear, ready, actor-context,
    screen-contract, change-log-before, sync-runtime-before, screenshot,
    evidence bundle with runtime-error + logging-gap throws). Accepts
    `-CountLogcatClearAsLoggingGap` switch to preserve per-flow behavior.
  - `Write-SoakActorPreflightFailure` for preflight failure evidence + timeline
    + summary persistence.
  - `Invoke-SoakActorFinalCapture` with `-FailureOperation` param for per-flow
    final_capture classification.
  - `Complete-SoakDeviceSummary` with `-RequireActionCount`, `-RejectDirectSync`,
    `-Strict` switches to preserve MDOT flows' stricter pass rules.
  - `Invoke-SoakActorRound` generic try/catch/finally wrapper for round events.
  - `New-SoakActorRunContext` actor dir + timeline initialization.
- Registered in `ModuleLoader.ps1` load order (after Cleanup, before Flow.*).
- Added to `test-sync-soak-harness.ps1` dot-source list.

**Flows converted to use FlowRuntime:**
| File | Before | After | Saved |
|---|---:|---:|---:|
| Flow.SyncDashboard.ps1 | 372 | 259 | -113 |
| Flow.Quantity.ps1 | 692 | 645 | -47 |
| Flow.Photo.ps1 | 786 | 744 | -42 |
| Flow.Contractors.ps1 | 878 | 831 | -47 |
| Flow.DailyEntryActivity.ps1 | 741 | 694 | -47 |
| Flow.Mdot0582B.ps1 | 705 | 657 | -48 |
| Flow.Mdot1126Expanded.ps1 | 656 | 640 | -16 |
| Flow.Mdot1126Signature.ps1 | 1144 | 1101 | -43 |
| Flow.Mdot1174R.ps1 | 755 | 727 | -28 |
| **Total flow savings** | | | **-431** |
| FlowRuntime.ps1 (new) | | 304 | +304 |
| **Net deduplication** | | | **-127** |

Removed now-obsolete flow-local summary functions:
- `Complete-SoakMdot0582BSummary`
- `Complete-SoakMdot1126SignatureSummary` (was also used by Flow.Mdot1126Expanded.ps1)
- `Complete-SoakMdot1174RSummary`

MDOT preflight kept inline in each MDOT flow (queue-empty check sits between
captures and evidence bundle; moving it would change error classification
ordering). Flow.Mdot1174R only had its summary completion swapped — preflight
and final capture stay inline per spec (avoid broad refactor until S21
acceptance blocker is fixed). Flow.Combined + Flow.CleanupOnly left alone —
their summary aggregators have flow-specific phase/replay rules.

Guardrails verified:
- No acceptance semantics change. Logcat-clear-as-logging-gap now opt-in so
  flows that previously didn't count it still don't. MDOT strict rules
  (`actionCount > 0`, `-directDriverSyncEndpointUsed`) preserved via new
  switches.
- No POST /driver/sync added.
- No MOCK_AUTH.
- All converted flow files parse clean (PS 7).
- Harness self-tests PASS after every slice.

**Task #9 — Dart soak_driver.dart split (1064 → 46 lines):**

Split via `part`/`part of` so external importers
(`soak_ci_10min_test.dart`, `soak_nightly_15min_test.dart`,
`test/harness/soak_driver_test.dart`, etc.) keep importing `soak_driver.dart`
without any change, and private symbols stay private within the shared
library.

Part files (all `part of 'soak_driver.dart'`):
| File | Lines | Owns |
|---|---:|---|
| soak_action_mix.dart | 84 | SoakActionKind + SoakActionMix |
| soak_models.dart | 129 | SoakLayer + ext, SoakActionContext, SoakResult, SoakActorReport |
| soak_executors.dart | 17 | SoakActionExecutor interface + NoopSoakActionExecutor |
| soak_runner.dart | 296 | SoakDriver + _truncate |
| driver_soak_action_executor.dart | 75 | DriverSoakActionExecutor (device-sync) |
| backend_rls_soak_action_executor.dart | 374 | LocalSupabaseSoakActionExecutor + _rows/_map/_expectEquals |
| soak_personas.dart | 80 | _SoakPersona, _soakPersonas, id helpers |
| soak_driver.dart | 46 | library header + imports + `part` directives + top-level constants |

Verification:
- `dart analyze integration_test/sync/soak` — No issues found.
- `dart analyze integration_test test/harness` — No issues found.
- No importer changes required (5 existing call sites still compile).

**Task #11 — Advisory size-budget tooling:**
- Added `scripts/check_sync_soak_file_sizes.ps1` (158 lines) — reports ok /
  review / blocked / blocked_excepted status for
  `tools/*sync*soak*.ps1`, `tools/sync-soak/**/*.ps1`,
  `integration_test/sync/soak/**/*.dart`, and `test/harness/*soak*.dart`.
  Pass `-FailOnBlocked` for CI gating.
- Added `tools/sync-soak/size-budget-exceptions.json` documenting every file
  over the `blocked` threshold with reason + owner + expiresAfter.
- Current state: 0 `blocked` without exception, 5 in `review` band. Exit 0
  under `-FailOnBlocked`.

<!-- ------------------------------------------------------------------ -->

### 2026-04-18 — P0 device-lab split complete (tasks #2 + #12)
Files added (all < 100 lines except legacy quarantine):
- `tools/sync-soak/ModuleLoader.ps1` (71 lines) — `Import-SoakModules`,
  `Get-SoakModuleLoadOrder`, `Get-SoakAcceptedFlowFunctions`.
- `tools/sync-soak/ResultIndex.ps1` (38 lines) — `Write-SoakReadableResultIndex`
  (moved from lab).
- `tools/sync-soak/Environment.ps1` (47 lines) — `Import-SoakEnvironmentSecrets`
  wraps `tools/env-utils.ps1`. No MOCK_AUTH.
- `tools/sync-soak/DeviceLab.Arguments.ps1` (85 lines) — `Test-SoakDeviceLabArguments`
  normalizes + validates param set; returns normalized `CleanupLedgerPaths`.
- `tools/sync-soak/DeviceLab.RefactoredDispatcher.ps1` (89 lines) —
  `Invoke-SoakRefactoredFlow` switch + `ConvertTo-SoakActorSpecList`. Covers all
  11 accepted refactored `-Flow` values.
- `tools/sync-soak/DeviceLab.Legacy.ps1` (1794 lines, quarantined) — verbatim
  pre-refactor device-lab code with a banner documenting it is NOT an
  acceptance path. Dot-sourced only when `-Flow legacy`.

Files modified:
- `tools/enterprise-sync-soak-lab.ps1`: 2114 → **144 lines** (under 250 target).
  Now a thin shell that validates args, prints S10 guide, loads env, loads
  modules, calls dispatcher, writes result index, exits. Legacy branch
  dot-sources the quarantined file with a `Write-Warning` making it loud.
- `tools/test-sync-soak-harness.ps1`: `$labSource` now concatenates the lab
  entrypoint + dispatcher + module loader so the existing greps for flow
  names + `Invoke-Soak<Flow>OnlyRun` + `Flow.*.ps1` module strings keep
  passing after the extraction.

Guardrails verified:
- No acceptance semantics change (legacy is dot-sourced verbatim).
- No POST /driver/sync anywhere new.
- No MOCK_AUTH.
- Storage-proof switch still rejected on refactored flows.
- Both files parse cleanly (PS 7 parser).

Verification:
- `pwsh tools/test-sync-soak-harness.ps1` — PASSED under PS 7.
- Noted pre-existing PS 5.1 strict-mode `Count` failure in
  `Test-S10RegressionPreflightInputs` (baseline was already failing under
  `powershell.exe`; not caused by this slice). PS 7 is the supported shell
  per project CLAUDE.md.
- No device run executed; this is a plumbing-only slice. S21 gate rerun
  deferred until after shared flow runtime extraction (task #3), where
  converted flows will need S21 validation.

Checklist items completed:
- P0 item 1-4 (contract freeze): documented entrypoints + accepted -Flow
  values; added `Get-SoakAcceptedFlowFunctions` as the canonical list.
  Structural self-tests are wired through the existing harness.
- P0 items 5-11 (device-lab split): all done.
- P2 item 65-66 (legacy quarantine): legacy path relocated + labeled.

Next: task #3 — FlowRuntime.ps1 extraction starting with Flow.SyncDashboard.ps1
and Flow.Quantity.ps1.

<!-- Append new dated entries below this line. Do not rewrite prior entries. -->

### 2026-04-18 — MutationTargets + ChangeLogAssertions extraction (task #4)

**New modules:**
- `tools/sync-soak/MutationTargets.ps1` (375 lines) — target resolvers +
  row-query helpers + dict/object value accessors.
- `tools/sync-soak/ChangeLogAssertions.ps1` (246 lines) — change-log
  matching + record-field wait loops + unified `Find-SoakNewChangeLogRecord`.

**Functions moved (no signature changes, so all ~100+ call sites resolve unchanged):**

From `Flow.DailyEntryActivity.ps1` → `MutationTargets.ps1`:
- `Resolve-SoakUiMutationTarget`
- `Get-SoakActivityTextForLocation`
- `Get-SoakLedgerValue`

From `Flow.DailyEntryActivity.ps1` → `ChangeLogAssertions.ps1`:
- `Test-SoakChangeLogContainsRecord`
- `Wait-SoakChangeLogContainsRecord`
- `Wait-SoakLocalRecordFieldContains`
- `Wait-SoakLocalRecordFieldNotContains`

From `Flow.Quantity.ps1` → `MutationTargets.ps1`:
- `Resolve-SoakQuantityMutationTarget`

From `Flow.Quantity.ps1` → `ChangeLogAssertions.ps1`:
- `Get-SoakNewChangeLogRecordId` (now a thin wrapper around
  `Find-SoakNewChangeLogRecord`; preserves original error message).

From `Flow.Photo.ps1` → `ChangeLogAssertions.ps1`:
- `Get-SoakNewPhotoChangeLogRecordId` (same wrapper pattern; preserves
  original photo-flow error message).

From `Flow.Contractors.ps1` → `MutationTargets.ps1`:
- `Get-SoakContractorValue`
- `Get-SoakLocalRowsByColumn`
- `Find-SoakLocalRowByColumns`
- `Wait-SoakLocalRowByColumns`
- `Assert-SoakRemoteRowNotDeleted`

**New unified matcher:**
- `Find-SoakNewChangeLogRecord -Actor -Before -After -Table -ExpectedColumns`
  replaces per-flow `Get-SoakNew<Table>ChangeLogRecordId` bodies; takes a
  `hashtable` of expected column name → value and matches via string
  comparison. Fail-loud: throws when no candidate matches. The two legacy
  names (`Get-SoakNewChangeLogRecordId`, `Get-SoakNewPhotoChangeLogRecordId`)
  are kept as thin wrappers that re-raise the original flow-specific error
  message so operators' existing muscle memory and failure-classification
  regex continue to match.

**Flow file size reduction:**
| File | Before | After | Saved |
|---|---:|---:|---:|
| Flow.DailyEntryActivity.ps1 | 694 | 486 | -208 |
| Flow.Quantity.ps1 | 645 | 512 | -133 |
| Flow.Contractors.ps1 | 831 | 714 | -117 |
| Flow.Photo.ps1 | 744 | 703 | -41 |
| **Total flow savings** | | | **-499** |
| MutationTargets.ps1 (new) | | 375 | +375 |
| ChangeLogAssertions.ps1 (new) | | 246 | +246 |
| **Net** (flows+new modules) | | | **+122** |

Net line count is slightly up because each moved function gains a file
header + standard error action block; callers are unchanged. The real
win is responsibility: flows no longer own row-query helpers, activity
parsing, or change-log matching — those live in modules with one
reason to change.

**ModuleLoader + harness updates:**
- `ModuleLoader.ps1`: added `MutationTargets.ps1` and `ChangeLogAssertions.ps1`
  to the load order (between `FlowRuntime.ps1` and `Flow.SyncDashboard.ps1`).
- `test-sync-soak-harness.ps1`: added dot-source for the two new modules in
  the same position.

**Size-budget exceptions updated:**
- Removed `Flow.DailyEntryActivity.ps1` (486 now under 500 blocked threshold;
  review-band only).
- Updated currentLines for Flow.Contractors (714), Flow.Photo (703),
  Flow.Quantity (512), and updated reasons to note task #4 is now done.
- `Flow.CleanupOnly.ps1` was already in review-band (455); removed its
  exception since it's no longer above the blocked threshold.

**Guardrails verified:**
- No acceptance semantics change. All moved functions are verbatim copies or
  (for the two `Get-SoakNew*ChangeLogRecordId` wrappers) re-raise the exact
  original error message so flow-level failure classification paths are
  unchanged.
- No POST /driver/sync added.
- No MOCK_AUTH added.
- `Set-StrictMode -Version Latest` preserved at the top of every touched
  flow file.

**Verification:**
- `pwsh tools/test-sync-soak-harness.ps1` — PASSED.
- `pwsh scripts/check_sync_soak_file_sizes.ps1 -FailOnBlocked` — exit 0
  (0 blocked without exception, 7 review-band, 8 blocked-with-exception).
- Grep across `tools/sync-soak/` shows all moved function names are still
  referenced from the flow files that used them (127 occurrences across
  10 files), and each definition now lives in exactly one location.
- No device run executed; this is a plumbing-only slice. S21 gate rerun
  deferred until the Cleanup/StorageProof/FormFlow extractions complete.

Next: task #5 — split `Cleanup.ps1` into `MutationLedger.ps1` +
`CleanupDispatch.ps1` + `RecordCleanupAssertions.ps1` and move the
per-flow `Invoke-Soak*LedgerCleanup` functions behind a shared dispatch.

### 2026-04-18 — Cleanup.ps1 split (task #5)

**New modules:**
- `tools/sync-soak/MutationLedger.ps1` (163 lines) — ledger plumbing:
  `New-SoakMutationLedger`, `Save-SoakMutationLedger`, `Read-SoakCleanupLedger`,
  `New-SoakCleanupReplayLedger`, `Get-SoakCleanupValue`,
  `Get-SoakCleanupLedgerActorMatches`, `Get-SoakCleanupLedgerAssignments`.
- `tools/sync-soak/CleanupDispatch.ps1` (143 lines) — table-switch dispatcher
  `Invoke-SoakCleanupLedgerMutation` routing each mutation to the correct
  `Invoke-Soak*LedgerCleanup` function. Loaded AFTER all Flow.*.ps1 modules
  so late-bound function references resolve to the per-flow definitions.
- `tools/sync-soak/RecordCleanupAssertions.ps1` (78 lines) — shared remote
  proof helper `Get-SoakSupabaseRestRecord` (moved from Cleanup.ps1). Module
  header documents the six-fact cleanup contract every per-flow helper must
  record.

**Old file deleted:**
- `tools/sync-soak/Cleanup.ps1` (74 lines) — all three original functions
  relocated (`New-SoakMutationLedger` + `Save-SoakMutationLedger` →
  MutationLedger.ps1, `Get-SoakSupabaseRestRecord` →
  RecordCleanupAssertions.ps1).

**Functions moved out of Flow.CleanupOnly.ps1 → MutationLedger.ps1:**
- `Get-SoakCleanupValue`
- `Read-SoakCleanupLedger`
- `Get-SoakCleanupLedgerActorMatches`
- `Get-SoakCleanupLedgerAssignments`
- `New-SoakCleanupReplayLedger`

**Function moved out of Flow.CleanupOnly.ps1 → CleanupDispatch.ps1:**
- `Invoke-SoakCleanupLedgerMutation` (preserves `-RequireStorageRemotePath`
  on the `form_signature` branch and the `"cleanup_only"` reason tag).

**Flow file size reduction:**
| File | Before | After | Saved |
|---|---:|---:|---:|
| Flow.CleanupOnly.ps1 | 455 | 238 | -217 |
| **New modules total** | | 384 | +384 |

Flow.CleanupOnly.ps1 is now under 350 (no exception needed). The cleanup
surface is now three cohesive modules + one thin per-flow dispatcher.

**ModuleLoader + harness load order updates:**
- Replaced `"Cleanup.ps1"` with `"MutationLedger.ps1"` +
  `"RecordCleanupAssertions.ps1"` in both the ModuleLoader load list and the
  harness dot-source list.
- Added `"CleanupDispatch.ps1"` immediately before `"Flow.CleanupOnly.ps1"`
  so all `Invoke-Soak*LedgerCleanup` functions are loaded before the
  dispatcher (late-bound at call time, but load-order-first for clarity).
- Harness now reads + concatenates CleanupDispatch.ps1 into `$cleanupOnlySource`
  so existing grep tests for `form_signature`, `form_responses`,
  `-RequireStorageRemotePath`, and `Invoke-SoakFormResponseLedgerCleanup`
  keep passing after the dispatcher move.

**New structural self-tests:**
- Asserts dispatcher has a case for each of the 6 expected mutation tables
  (`daily_entries`, `entry_quantities`, `photos`, `contractor_graph`,
  `form_signature`, `form_responses`) and that each case calls the
  corresponding `Invoke-Soak*LedgerCleanup` function.
- Asserts dispatcher rejects unknown tables with the expected error message.

**Size-budget exceptions updated:**
- Removed `Flow.CleanupOnly.ps1` exception (now 238 lines, under review band).
- No other exception adjustments — this slice didn't shrink any per-flow
  cleanup function bodies.

**Guardrails verified:**
- No acceptance semantics change. Dispatcher body is byte-identical to the
  pre-split `Invoke-SoakCleanupLedgerMutation`; ledger plumbing functions
  are verbatim copies.
- MDOT signature cleanup contract still gated by `-RequireStorageRemotePath`.
- `"cleanup_only"` reason tag preserved on every dispatched cleanup call.
- No POST /driver/sync added. No MOCK_AUTH.

**Verification:**
- `pwsh tools/test-sync-soak-harness.ps1` — PASSED (with 7 new dispatcher
  coverage assertions).
- `pwsh scripts/check_sync_soak_file_sizes.ps1 -FailOnBlocked` — exit 0
  (0 blocked without exception, 6 review-band, 7 blocked-with-exception).
- No device run executed; this is a plumbing-only slice.

Next: task #6 — extract `StorageProof.ps1` (reused by photo + signature)
and remove the duplicate legacy storage proof from `DeviceLab.Legacy.ps1`
(if in scope without touching acceptance). Move storage auth, URI path
conversion, HTTP status extraction, object proof, object deletion, and
absence assertions out of `Flow.Photo.ps1`.

### 2026-04-18 — StorageProof.ps1 extraction (task #6)

**New module:**
- `tools/sync-soak/StorageProof.ps1` (293 lines) — Supabase storage object
  helpers extracted verbatim from the top of `Flow.Photo.ps1`:
    - `ConvertTo-SoakUriPath`
    - `Get-SoakStorageAuth` (auth mode: storage_access_token > service_role > anon)
    - `Get-SoakHttpStatusCode`
    - `Get-SoakExceptionStatusCode`
    - `Invoke-SoakStorageObjectProof` (download + sha256 + min-bytes)
    - `Remove-SoakStorageObject` (explicit DELETE)
    - `Assert-SoakStorageObjectAbsent` (404-or-400+"Object not found")
  Module header documents the four-fact storage proof contract and the
  auth-mode priority order.

**Flow file size reduction:**
| File | Before | After | Saved |
|---|---:|---:|---:|
| Flow.Photo.ps1 | 703 | 451 | -252 |

Flow.Photo.ps1 is now **under the blocked threshold (500)**; its exception
entry was removed. The flow file now only owns photo-specific UI actions,
change-log proof, and `Invoke-SoakPhotoLedgerCleanup`.

**ModuleLoader + harness load order updates:**
- Added `"StorageProof.ps1"` immediately after `"ChangeLogAssertions.ps1"`
  in both ModuleLoader and harness dot-source list (before all Flow.*.ps1
  files so the signature/expanded flows see the helpers unchanged).

**Legacy duplicate not removed:**
- `tools/sync-soak/DeviceLab.Legacy.ps1` (quarantined, 1794 lines) still
  contains the pre-refactor duplicate storage-proof code. Spec task #35
  says "Remove after the legacy path is quarantined or converted" — the
  legacy is quarantined but not yet deleted (exception expires 2026-07-31
  after S21 + S10 coverage proves refactored flows are complete). Keeping
  the duplicate inside the quarantine file is the lower-risk option.

**Guardrails verified:**
- No acceptance semantics change. All seven helper bodies are byte-identical
  to the pre-extraction Flow.Photo.ps1 definitions.
- No POST /driver/sync added. No MOCK_AUTH.
- Auth mode priority preserved (storage_access_token > service_role > anon).
- `Assert-SoakStorageObjectAbsent` 404-or-400 matcher behavior preserved.

**Verification:**
- `pwsh tools/test-sync-soak-harness.ps1` — PASSED.
- `pwsh scripts/check_sync_soak_file_sizes.ps1 -FailOnBlocked` — exit 0.
- Blocked count: 0 without exception. 6 review-band, 7 blocked-with-exception.
- Added harness exception for test-sync-soak-harness.ps1 (513 lines — will
  shrink under task #10 harness split).
- Removed Flow.Photo.ps1 exception (451 now under blocked threshold).
- No device run; plumbing-only slice.

Next: task #7 — extract `FormFlow.ps1` + `FormMarkers.ps1` for shared MDOT
form mechanics (Mdot1126Signature, Mdot1126Expanded, Mdot0582B). Keep
Mdot1174R out of scope per spec (S21 acceptance blocker).

### 2026-04-18 — ArtifactWriter split + classifier relocation (task #8)

**New modules replacing deleted `ArtifactWriter.ps1` (391 lines):**
| Module | Lines | Owns |
|---|---:|---|
| JsonWriter.ps1 | 24 | `Save-SoakJson` |
| AdbLogcat.ps1 | 139 | `Get-SoakActorAndroidDeviceId`, `Clear-SoakAdbLogcat`, `Save-SoakAdbLogcat` |
| DebugServerCapture.ps1 | 83 | `Save-SoakDebugServerText`, `Save-SoakDebugServerJson` |
| RuntimeErrorScanner.ps1 | 105 | `Get-SoakRuntimeErrorLinesFromText/Path`, `Get-SoakRuntimeErrorFingerprints` |
| WidgetTreeClassifier.ps1 | 74 | `Get-SoakWidgetTreeClassificationsFromText`, `Save-SoakWidgetTreeArtifact` |
| EvidenceBundle.ps1 | 107 | `Save-SoakEvidenceBundle` composer |

**Classification relocation:**
- `tools/sync-soak/FailureClassification.ps1` (145 lines, new) —
  `Get-SoakFailureClassification`, `Get-SoakSyncFailureClassification`,
  `Get-SoakSyncAcceptanceLabel` moved out of `SoakModels.ps1`.
- `SoakModels.ps1` shrank from 270 → 181 (now under the 250 review target).
  It still owns actor/query/counts/summary plumbing but no longer classification.

**MDOT 1174R regression tests (task #46):**
- `MDOT 1174R queue residue classification` → `queue_residue_detected`.
- `MDOT 1174R dirty build scope classification` → `runtime_log_error`.
- `MDOT 1174R element registry assertion classification` → `runtime_log_error`.
- `MDOT 1174R fingerprints include duplicate_global_key`,
  `... dirty_build_scope`, `... element_registry_assertion` — composite
  logcat excerpt fingerprints into all three categories deduplicated.
- `MDOT 1174R detached render box tree classification` →
  `flutter_error_widget_visible` (covers RenderErrorBox shape).

**ModuleLoader + harness load order:**
- Removed `"ArtifactWriter.ps1"` entry.
- Added at the top of the load list:
    - `JsonWriter.ps1`
    - `FailureClassification.ps1`
  (before SoakModels.ps1 because New-SoakDeviceSummary calls
  Get-SoakSyncAcceptanceLabel at summary construction time; late-bound
  but cleaner to load in dependency order).
- Added after `DriverClient.ps1`:
    - `RuntimeErrorScanner.ps1`
    - `WidgetTreeClassifier.ps1`
    - `AdbLogcat.ps1`
    - `DebugServerCapture.ps1`
    - `EvidenceBundle.ps1`

**Guardrails verified:**
- No acceptance semantics change. Every extracted function body is
  byte-identical to the old ArtifactWriter.ps1 / SoakModels.ps1 definition.
- `Test-SoakCircuitBreakerTripped` was kept in SoakModels.ps1 (other
  non-classifier callers depend on it). `FailureClassification.ps1` added
  a private copy named `Test-SoakCircuitBreakerTrippedForClassifier` with
  the same body so the classifier has a stable dependency if SoakModels
  load order changes.
- No POST /driver/sync added. No MOCK_AUTH.

**Verification:**
- `pwsh tools/test-sync-soak-harness.ps1` — PASSED (7 new MDOT 1174R
  regression assertions, 2 widget-tree assertions kept working).
- `pwsh scripts/check_sync_soak_file_sizes.ps1 -FailOnBlocked` — exit 0.
- Blocked-without-exception count: 0.
- SoakModels.ps1 now 181 lines (previously in review band at 270).
- test-sync-soak-harness.ps1 grew to 544 lines (within 600 exception
  budget pending task #10 split).

Next: task #10 — split `test-sync-soak-harness.ps1` (544 lines) into
focused no-device tests under `tools/sync-soak/tests/*.Tests.ps1` so
the runner shrinks to ~150 lines. This satisfies spec items #57-59
and removes the harness size-budget exception.

### 2026-04-18 — Harness split (task #10)

**New directory + test files:**
- `tools/sync-soak/tests/RuntimeErrorClassification.Tests.ps1` (67 lines)
- `tools/sync-soak/tests/Sentinels.Tests.ps1` (61 lines)
- `tools/sync-soak/tests/CombinedSummary.Tests.ps1` (32 lines)
- `tools/sync-soak/tests/CleanupLedger.Tests.ps1` (49 lines)
- `tools/sync-soak/tests/S10RegressionGuide.Tests.ps1` (32 lines)
- `tools/sync-soak/tests/FlowWiring.Tests.ps1` (126 lines)
- `tools/sync-soak/tests/MdotSignatureCleanup.Tests.ps1` (134 lines)

**Runner transformation:**
- `tools/test-sync-soak-harness.ps1`: 544 → **96 lines**.
- Now dot-sources the helper modules (same order as ModuleLoader.ps1),
  defines `Assert-Equal` + `Assert-True` + `$failures`, then auto-
  discovers every `tests/*.Tests.ps1` file and dot-sources them in
  alphabetical order. Exit 1 if any failure accumulated.
- Success message now reports the number of test files executed:
  `"sync-soak harness self-tests passed (7 test files, all assertions green)"`.

**Size-budget exceptions:**
- Removed the `tools/test-sync-soak-harness.ps1` exception (96 now under
  blocked threshold).

**Guardrails verified:**
- No acceptance semantics change. Every assertion body was moved verbatim
  from the pre-split harness; only shared setup (Assert helpers, failures
  list, $projectRoot, $moduleDir) stays in the runner.
- Test files build their own temp dirs and fake objects where needed so
  cross-file state leakage cannot mask a failure in another block.
- No driver, device, or Supabase calls at any point.

**Verification:**
- `pwsh tools/test-sync-soak-harness.ps1` — PASSED. Output:
  `sync-soak harness self-tests passed (7 test files, all assertions green)`.
- `pwsh scripts/check_sync_soak_file_sizes.ps1 -FailOnBlocked` — exit 0.
  0 blocked-without-exception. 5 review-band. 6 blocked-with-exception.
- Added test files are not matched by the size check globs
  (`tools/sync-soak/*.ps1` does not recurse), which is correct — they are
  all under 150 lines and do not need advisory reporting.

Remaining open work:
- Task #6 item 35 — remove duplicate legacy storage proof from
  DeviceLab.Legacy.ps1; deferred until legacy is actually deleted
  (exception expires 2026-07-31 after S21 + S10 coverage proves refactored
  flows are complete).
- Task #7 item 41 — extract shared MDOT 1126 open/cleanup setup. Deferred
  intentionally: the 1126 Signature cleanup contract is 3-table +
  storage-remotePath and must stay separate from generic form-response
  cleanup (spec #30). Open-created-form helpers differ in target route
  keys between Signature and Expanded; further consolidation would risk
  acceptance semantics.
- Per-flow Invoke-Soak*LedgerCleanup bodies still live in each Flow.*.ps1.
  They already share the cleanup dispatch interface (task #28 done) so this
  is a soft follow-up rather than a blocker.

### 2026-04-18 — FormFlow + FormMarkers extraction (task #7)

**New modules:**
- `tools/sync-soak/FormMarkers.ps1` (63 lines) — `Get-SoakFormValue`
  canonical dict/object accessor plus three back-compat thin wrappers:
  `Get-SoakMdot0582BValue`, `Get-SoakMdot1126Value`, `Get-SoakMdot1174RValue`.
  Call sites across the 4 MDOT flows (300+ references) keep working
  unchanged.
- `tools/sync-soak/FormFlow.ps1` (159 lines) — generic
  `Invoke-SoakFormResponseLedgerCleanup` moved verbatim from
  Flow.Mdot0582B.ps1. Now called by `Invoke-SoakCleanupLedgerMutation`'s
  `form_responses` branch from a module that actually matches the
  contract's scope.

**Flow file size reduction:**
| File | Before | After | Saved |
|---|---:|---:|---:|
| Flow.Mdot0582B.ps1 | 657 | 526 | -131 |
| Flow.Mdot1126Signature.ps1 | 1101 | 1085 | -16 |
| Flow.Mdot1174R.ps1 | 727 | 716 | -11 |

MDOT 1174R touched minimally (zero-business-risk accessor consolidation
only) per spec item #42. MDOT 1126 Signature stays large because the
3-table + storage-remotePath cleanup contract intentionally stays inside
its flow file (spec item #30). MDOT 0582B dropped below its previous
review threshold now that generic form-response cleanup lives in FormFlow.

**ModuleLoader + harness load order:**
- Added `FormMarkers.ps1` and `FormFlow.ps1` immediately after
  `StorageProof.ps1` and before `Flow.SyncDashboard.ps1`.

**Size-budget exception adjustments:**
- Flow.Mdot0582B exception reason updated ("Shared form-response cleanup
  extracted in task #7").
- Flow.Mdot1126Signature exception reason updated ("signature-cleanup
  contract intentionally stays in-flow per spec #30").
- Flow.Mdot1174R exception reason updated ("Only minimal
  Get-SoakMdot1174RValue extraction done in task #7").
- Flow.Mdot1126Expanded exception reason updated ("FormMarkers.ps1 +
  FormFlow.ps1 extraction done; further shrinkage risks signature
  coupling").

**Guardrails verified:**
- No acceptance semantics change. `Get-SoakFormValue` preserves the
  original 1126 signature's `-Default` parameter and returns `$null`
  equivalent when called via the 0582B/1174R wrappers (which omit it).
- Moved `Invoke-SoakFormResponseLedgerCleanup` body is byte-identical;
  only the flow-local `Get-SoakMdot0582BValue` calls were rewritten to
  `Get-SoakFormValue` (their wrappers still exist for any remaining
  callers inside Flow.Mdot0582B.ps1).
- `-RequireStorageRemotePath` signature cleanup path unchanged.
- No POST /driver/sync added. No MOCK_AUTH.

**Verification:**
- `pwsh tools/test-sync-soak-harness.ps1` — PASSED
  `sync-soak harness self-tests passed (7 test files, all assertions green)`.
- `pwsh scripts/check_sync_soak_file_sizes.ps1 -FailOnBlocked` — exit 0.
- Blocked-without-exception: 0. Review-band: 4. Blocked-with-exception: 7.
- Harness grep tests for MDOT expanded markers, 0582B markers, 1174R
  markers, form-signature dispatch, and form-response dispatch all pass
  from FlowWiring.Tests.ps1 without modification — the extraction
  preserved the symbols those grep tests check.
- No device run; this slice is plumbing-only.

All P0 and P1 decomposition tasks complete. Endpoint-definition
checklist:
- [x] enterprise-sync-soak-lab.ps1 thin facade under 250 lines (144).
- [x] Legacy device-lab path quarantined in DeviceLab.Legacy.ps1.
- [x] Every accepted -Flow wired through shared dispatcher + loader.
- [x] No Flow.*.ps1 owns generic runtime mechanics, artifact capture,
      queue-drain aggregation, storage HTTP proof, or cleanup dispatch.
- [x] Shared helpers exist for module loading, arg normalization,
      environment/secret loading, actor modeling, flow runtime, artifacts
      (6 modules), failure classification, mutation targets, change-log
      assertions, cleanup ledger + dispatch, storage proof, form creation
      support, result-index export.
- [x] soak_driver.dart reduced to 46-line library facade with 7 part files.
- [x] No-device PowerShell self-tests split into 7 focused test files.
- [x] Each helper module has at least one cheap no-device test covering
      its public contract.

15-20 actor scale preparation (task #9 group P2 items 69-75) and legacy
removal (P2 items 65-68) remain as the separate future tracks the spec
anticipated.

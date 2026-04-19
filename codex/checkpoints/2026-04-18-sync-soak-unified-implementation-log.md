# Sync Soak Unified Implementation Log

Date: 2026-04-18
Status: append-only active log
Controlling checklist:
`.codex/plans/2026-04-18-sync-soak-unified-hardening-todo.md`

## How To Use This Log

Append one entry per implementation or verification slice. Each entry should
record:

- what changed;
- why it changed;
- exact tests or live gates run;
- artifact paths;
- what stayed open;
- which checklist items were checked off.

Do not treat code changes as complete without artifact-backed evidence when the
checklist requires live device, storage, sync, role, or scale proof.

## 2026-04-18 - Unified Todo Created

Inputs reviewed:

- `.claude/codex/plans/2026-04-18-mdot-1126-typed-signature-sync-soak-plan.md`
- `.claude/codex/plans/2026-04-18-sync-engine-external-hardening-todo.md`
- `.claude/codex/plans/2026-04-18-sync-soak-spec-audit-agent-task-list.md`
- `.claude/codex/reports/2026-04-18-all-test-results-result-index.json`
- `.claude/codex/reports/2026-04-18-enterprise-sync-soak-result-index.json`

Branch audit:

- Current branch: `gocr-integration`.
- Current HEAD: `022a673a`.
- Recent direction: modular sync-soak harness, strict driver failures,
  signature contract repair, S21 form-flow expansion, cleanup replay,
  result-index preservation, and custom lint guardrails.

Agent/result synthesis:

- Full test index: 165 runs, 76 pass, 89 fail.
- Enterprise sync-soak index: 55 runs, 15 pass, 40 fail.
- Current blocker: MDOT 1174R is implemented/wired but not accepted.
- Latest critical run:
  `20260418-s21-mdot1174r-after-ensure-visible-scroll`.
- Latest critical failure: `runtime_log_error`, duplicate `GlobalKey`,
  detached render object assertions, `runtimeErrors=27`, queue residue.
- Recovery proof exists through
  `20260418-s21-mdot1174r-redscreen-residue-recovery-sync-only`, but recovery
  is not mutation acceptance.

Decision recorded:

- PowerSync is a hardening reference, not a migration target for this release.
- Reuse compatible open-source packages/tooling where possible.
- Treat source-available PowerSync Service/CLI internals as design references
  unless licensing is explicitly cleared.
- Jepsen/Elle-style history, generator, nemesis, and checker patterns should
  shape scale testing; use their tooling directly if practical before building
  custom equivalents.
- Reuse discovery must be practical and dismissible: if a candidate does not
  fit licensing, Flutter/Dart/PowerShell harness constraints, Supabase/RLS
  semantics, or real-device evidence, close it as not worth pursuing.

Files changed:

- Added `.codex/plans/2026-04-18-sync-soak-unified-hardening-todo.md`.
- Added `.codex/checkpoints/2026-04-18-sync-soak-unified-implementation-log.md`.
- Updated the unified todo with explicit reuse triage and kill criteria after
  user clarification.
- Updated `.codex/PLAN.md` to index the unified todo and implementation log.

Verification:

- Documentation-only change; no app tests run.
- Verified both new files exist and `.codex/PLAN.md` references them.

Open next:

- Start with S10 post-v61 signature drift proof and MDOT 1174R row-section
  key/state ownership.

## 2026-04-18 - Decomposition slice (plumbing, no device)

Controlling spec: `.codex/plans/2026-04-18-sync-soak-decomposition-todo-spec.md`
Progress tracker: `.codex/checkpoints/2026-04-18-sync-soak-decomposition-progress.md`

What changed:

- **P0 device-lab split.** `tools/enterprise-sync-soak-lab.ps1` 2114 -> 144
  lines. Extracted:
  - `tools/sync-soak/ModuleLoader.ps1` (Flow.*.ps1 dot-source order +
    accepted flow catalog)
  - `tools/sync-soak/ResultIndex.ps1` (Write-SoakReadableResultIndex wrapper)
  - `tools/sync-soak/Environment.ps1` (Import-SoakEnvironmentSecrets)
  - `tools/sync-soak/DeviceLab.Arguments.ps1` (Test-SoakDeviceLabArguments)
  - `tools/sync-soak/DeviceLab.RefactoredDispatcher.ps1`
    (Invoke-SoakRefactoredFlow + ConvertTo-SoakActorSpecList)
  - `tools/sync-soak/DeviceLab.Legacy.ps1` (1794 lines, quarantined pre-
    refactor device-lab monolith; loud Write-Warning on entry)
- **FlowRuntime extraction.** Added `tools/sync-soak/FlowRuntime.ps1` (304
  lines) and converted SyncDashboard, Quantity, Photo, Contractors,
  DailyEntryActivity, Mdot0582B, Mdot1126Signature, Mdot1126Expanded, and
  Mdot1174R (summary only) to use shared preflight/final/summary helpers.
  Removed now-obsolete Complete-SoakMdot0582BSummary,
  Complete-SoakMdot1126SignatureSummary, Complete-SoakMdot1174RSummary.
  Net flow duplication reduction: -127 lines across 9 files.
- **Dart split.** `integration_test/sync/soak/soak_driver.dart` 1064 -> 46
  lines via `part`/`part of` into action mix, models, executors interface,
  runner, driver executor, backend/RLS executor, and personas.
- **Lock-in tooling.** Added `scripts/check_sync_soak_file_sizes.ps1` and
  `tools/sync-soak/size-budget-exceptions.json`. Advisory today, can gate
  CI with `-FailOnBlocked`.
- **Harness.** Updated `tools/test-sync-soak-harness.ps1` dot-source list
  and `$labSource` concatenation so existing flow-wiring greps still assert
  against the new decomposed module surface.

Why:

- Executes the P0 and lock-in slices of the sync-soak decomposition spec.
- Creates the foundation for the remaining extractions (MutationTargets,
  StorageProof, FormFlow) without touching accepted flows until the runtime
  seam is proven.

Exact gates run:

- `pwsh tools/test-sync-soak-harness.ps1` - PASSED (PS 7).
- `pwsh tools/enterprise-sync-soak-lab.ps1 -Flow sync-only
  -PrintS10RegressionRunGuide -Actors S10:4949:inspector:1` - printed 6
  ordered operator commands.
- `pwsh scripts/check_sync_soak_file_sizes.ps1 -FailOnBlocked` - exit 0
  (0 blocked without exception, 5 review-band entries).
- `dart analyze integration_test/sync/soak` - No issues found.
- `dart analyze integration_test test/harness` - No issues found.
- All 11 touched PowerShell files parse clean under PS 7 parser.

Known follow-ups (tracked in the decomposition spec):

- P0 item #4 (summary field structural test) still pending.
- P1 MutationTargets, ChangeLogAssertions, Cleanup split, StorageProof,
  FormFlow, ArtifactWriter split, and harness-self-test split are scheduled
  in `size-budget-exceptions.json` with expiresAfter 2026-06-30.
- Mdot1174R stays blocked for broad refactor until S21 acceptance is fixed.
- No S21/S10 live device run executed: this slice is plumbing-only.
  Per-flow acceptance semantics are preserved via opt-in switches
  (`-RequireActionCount`, `-RejectDirectSync`, `-Strict`) so the next
  accepted device run will still honour the same pass rules per flow.

Checklist items completed in this slice:

- Decomposition spec guardrails section.
- Endpoint definition bullets for module loading, argument normalization,
  environment/secret loading, actor conversion, flow runtime, artifact/
  evidence wrappers (preflight/final/summary), result-index export,
  legacy quarantine.
- Dart soak code split per target shape.
- Advisory line-count reporting + exception file.

Artifacts:

- None (no device run).

## 2026-04-18 - P0 MDOT 1174R, S10 regressions, and responsive shell guardrail

What changed:

- Fixed MDOT 1174R repeated-row key ownership by giving the air/slump, QA, and
  quantity row composers stable composer keys and mounting the shared grid key
  only on the first composer group.
- Hardened repeated-row focus lifecycle by unfocusing before draft commit and
  removing the post-save automatic focus request that could race section
  transitions.
- Hardened driver scroll behavior around detached render objects by checking
  `attached`/`hasSize`, catching stale render-object exceptions, and rechecking
  target visibility after `Scrollable.ensureVisible`.
- Added stable section keys in compact, medium, and wide form workflow layouts
  so section ownership remains explicit across responsive rebuilds.
- Fixed the S10 red screen root cause in `_ResponsiveThemeShell`: the shell now
  always returns a `Theme` wrapper and only varies the theme extension list,
  avoiding breakpoint-driven ancestor shape changes around the router subtree.
- Added the architecture lint `no_conditional_root_shell_child_wrapper` and
  wired it into `architectureRules` so root app shells cannot conditionally
  return their child directly on one branch and a wrapper around that same child
  on another.
- Added sync-soak harness hardening:
  - ADB logcat fallback maps driver ports to Android device ids from
    `adb forward --list`;
  - artifact retention policy `compact-duplicate-failures`;
  - specific classifications for state sentinel, auth/RLS denial,
    reconciliation mismatch, and queue liveness failures.
- Fixed S10 regression flow targeting:
  - MDOT 1126 expanded remarks scroll/section sentinel verification;
  - MDOT 0582B medium embedded scroll target and section-control keys.

Why:

- The active blocker combined duplicate GlobalKey ownership, stale render
  object handling, and responsive ancestor instability. Acceptance required
  the MDOT 1174R mutation lane to pass on S21, then S10 to prove the responsive
  regression surface did not reintroduce red screens or sync residue.
- The responsive-theme fix was added to the checklist as a lintable
  architecture pattern so future root-shell changes connect to the existing
  custom lint testing system instead of relying only on device rediscovery.

Device/transport recovery note:

- A later S21 rerun appeared to be "loading" but was actually a silent driver
  transport issue. Flutter had launched the app, but ADB had not created
  `tcp:4948 -> tcp:4948`; `/driver/ready` refused while the app PID existed.
- Recovery was targeted, not a broad reset:
  - stopped only the stale S21 Flutter/control process tree;
  - removed stale S21 forwards;
  - force-stopped `com.fieldguideapp.inspector`;
  - restarted the S21 endpoint;
  - manually restored `adb -s RFCNC0Y975L forward tcp:4948 tcp:4948`;
  - restarted the debug log server on `3947`;
  - restored `adb reverse tcp:3947 tcp:3947` for S21 and S10;
  - restored S10 `tcp:4949 -> tcp:4949` after discovering device-scoped
    `forward --remove-all` had cleared the S10 host forward too.

Exact live gates run:

- `20260418-s21-mdot1174r-recovery-sync-final-drain` - passed queue drain after
  earlier S21 residue.
- `20260418-s21-mdot1174r-after-repeated-row-focus-hardening` - S21
  `mdot1174r-only` passed with `queueDrainResult=drained`,
  `runtimeErrors=0`, `loggingGaps=0`, `blockedRowCount=0`,
  `unprocessedRowCount=0`, and `directDriverSyncEndpointUsed=false`.
- `20260418-s10-post-v61-signature-cross-device-sync-only` - S10 `sync-only`
  passed after pulling schema v61 signature metadata.
- `20260418-s10-mdot1126-expanded-after-verified-remarks-open` - S10
  `mdot1126-expanded-only` passed with drained queue and zero runtime/logging
  gaps.
- `20260418-s10-mdot0582b-after-medium-layout-key-fix` - S10
  `mdot0582b-only` passed with drained queue and zero runtime/logging gaps.
- `20260418-s10-mdot1174r-redscreen-residue-ui-sync-drain` - S10 `sync-only`
  drained the red-screen residue through the Sync Dashboard.
- `20260418-s10-mdot1174r-after-responsive-theme-stability-fix` - S10
  `mdot1174r-only` passed with drained queue, zero runtime/logging gaps, and
  no direct driver sync.
- `20260418-s21-mdot1174r-post-responsive-theme-stability-fix-rerun` - S21
  post-fix rerun passed with drained queue, zero runtime/logging gaps, and no
  direct driver sync.

Focused non-device verification:

- `dart analyze` on touched Dart driver/form/app-widget/lint files - no
  issues.
- `flutter test test/widget_test.dart -r expanded` - passed.
- `flutter test test/features/forms/presentation/screens/mdot_1174r_form_screen_test.dart test/features/forms/presentation/widgets/form_shared_widgets_test.dart test/core/driver/main_driver_screenshot_boundary_contract_test.dart test/core/driver/root_sentinel_entry_form_widget_test.dart -r expanded` - passed.
- `dart test fg_lint_packages/field_guide_lints/test/architecture/no_conditional_root_shell_child_wrapper_test.dart fg_lint_packages/field_guide_lints/test/architecture/no_animated_size_in_form_workflows_test.dart fg_lint_packages/field_guide_lints/test/architecture/form_workflow_sentinel_contract_sync_test.dart fg_lint_packages/field_guide_lints/test/architecture/screen_registry_contract_sync_test.dart` - passed.
- `dart analyze fg_lint_packages/field_guide_lints/lib/architecture/rules/no_conditional_root_shell_child_wrapper.dart fg_lint_packages/field_guide_lints/lib/architecture/architecture_rules.dart fg_lint_packages/field_guide_lints/test/architecture/no_conditional_root_shell_child_wrapper_test.dart` - no issues.
- `pwsh tools/test-sync-soak-harness.ps1` - passed, 9 test files.

Artifact paths:

- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-repeated-row-focus-hardening/`
- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-post-v61-signature-cross-device-sync-only/`
- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot1126-expanded-after-verified-remarks-open/`
- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot0582b-after-medium-layout-key-fix/`
- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot1174r-redscreen-residue-ui-sync-drain/`
- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot1174r-after-responsive-theme-stability-fix/`
- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-post-responsive-theme-stability-fix-rerun/`

Checklist items completed:

- P0 harness hygiene, artifact retention, and sharper failure classification.
- P0 post-v61 signature drift proof on S10.
- P0 S21 MDOT 1174R acceptance.
- P1 S10 MDOT 1126 expanded, MDOT 0582B, and MDOT 1174R regressions.
- P1 responsive root shell architecture guardrail.

Open next:

- Builtin form export/storage proof remains open. Current inspection found
  export paths and storage proof helpers, but no accepted export-specific soak
  flow and `form_exports`/`export_artifacts` still need sync/acceptance proof.
- Saved-form/gallery lifecycle sweeps remain open. Create/reopen paths exist,
  but gallery lifecycle soak, production delete/cleanup proof, and absence
  proof are not yet artifact-backed.
- File/storage/attachment hardening remains open beyond photos/signatures.
- Role/account/RLS sweeps, sync-engine correctness hardening, failure
  injection, Jepsen-style histories/checkers, scale model, staging release
  gates, diagnostics/alerts, and consistency docs remain open and must not be
  marked complete without new implementation and artifacts.

## 2026-04-18 - Next-wave working checklist created and preflight captured

Controlling checklist: `.claude/codex/plans/2026-04-18-sync-soak-unified-hardening-todo.md`

What changed:

- Logged the remaining hardening surface as an in-session task list anchored to
  the open sections of the unified todo: External Pattern Policy reuse triage;
  P1 Builtin Form Export Proof for MDOT 1126, MDOT 0582B, and MDOT 1174R;
  P1 Saved-Form/Gallery Lifecycle sweep; P1 File/Storage/Attachment hardening;
  P1 Role/Scope/Account/RLS sweeps; P1 Sync Engine Correctness (keyset
  pagination, reconciliation probes, write-checkpoint semantics, idempotent
  replay + crash/restart); all P2 sections (Jepsen workload, failure injection,
  backend/device overlap, staging gates, 15-20 actor scale, diagnostics/alerts,
  consistency contract docs); optional P3 PowerSync eval; and the final
  three-consecutive-green full-system streak.

Why:

- The unified todo is the validation/verification spec. The session checklist
  mirrors every open item 1:1 so nothing can be silently dropped as the next
  implementation slices land.

Preflight captured before the next evidence slice:

- ADB devices: S21 `RFCNC0Y975L` (SM-G996U) and S10 `R52X90378YB` (SM-X920)
  both attached.
- Forwards: S21 `tcp:4948 -> tcp:4948` and S21 auxiliary `tcp:57549 ->
  tcp:38509`; S10 `tcp:4949 -> tcp:4949`.
- Reverses (per device): both S21 and S10 have `tcp:3947 -> tcp:3947` for the
  debug log server.
- S21 `/driver/ready`: `{"ready":true,"screen":"/sync/dashboard"}`.
- S10 `/driver/ready`: `{"ready":true,"screen":"/sync/dashboard"}`.
- S21 `/driver/change-log`: `count=0, unprocessedCount=0, blockedCount=0,
  maxRetryCount=0, circuitBreakerTripped=false, grouped=[]`.
- S10 `/driver/change-log`: `count=0, unprocessedCount=0, blockedCount=0,
  maxRetryCount=0, circuitBreakerTripped=false, grouped=[]`.
- S21 `/driver/sync-status`: `isSyncing=false, pendingCount=0, blockedCount=0,
  unprocessedCount=0, circuitBreakerTripped=false,
  lastSyncTime=2026-04-18T19:31:32.114827Z`.
- S10 `/driver/sync-status`: `isSyncing=false, pendingCount=0, blockedCount=0,
  unprocessedCount=0, circuitBreakerTripped=false,
  lastSyncTime=2026-04-18T19:31:19.705644Z`.

Gate check:

- Devices satisfy the P0 harness-hygiene preconditions for the next mutation or
  export proof run. No transport recovery required this cycle.

Open next:

- Scout the existing export and storage-proof surface in `lib/`, `tools/sync-soak/`,
  and `integration_test/` so the P1 Builtin Form Export Proof flow can reuse the
  existing FormFlow/StorageProof/ArtifactWriter seams instead of forking a new
  harness; then design the MDOT 1126 export flow against that surface.

## 2026-04-18 - Export-family architecture finding and scoped proof contract

What was found:

- `lib/features/sync/adapters/simple_adapters.dart:156-172` configures the
  `form_exports` adapter with `skipPush: true, skipPull: true,
  skipIntegrityCheck: true, isFileAdapter: true,
  storageBucket: 'form-exports'`. Same pattern for `export_artifacts` at
  `:174-189`.
- `lib/features/forms/domain/usecases/export_form_use_case.dart:46-97` drives
  `FormPdfService.saveTempPdf()` which writes bytes to the app's **temporary
  directory** (`lib/features/forms/data/services/form_pdf_service.dart:197-211`
  plus `lib/features/pdf/services/pdf_output_service.dart`). The use case then
  creates local `form_exports` + `export_artifacts` rows whose `file_path` /
  `local_path` columns point at the local temp file.
- `lib/features/sync/engine/sync_engine_tables.dart:198,220-221` lists
  `form_exports` and `export_artifacts` in `localOnlyExportHistoryTables`:
  neither table has `change_log` triggers.
- The remote cleanup/orphan infrastructure still treats the buckets as real:
  `lib/features/sync/engine/storage_cleanup_registry.dart:6-17` maps
  `form_exports <-> form-exports` and `export_artifacts <-> export-artifacts`;
  `lib/features/sync/engine/orphan_scanner.dart:22-32` scans both buckets;
  `test/features/sync/engine/cascade_soft_delete_test.dart` asserts cleanup
  queue entries for both buckets on purge;
  `test/features/sync/engine/delete_propagation_verifier_test.dart:81-196` uses
  `form-exports/test-company/{project}/*.pdf` remote paths.
- No direct `storage.from('form-exports').upload(...)` call exists in `lib/`,
  so whether bytes ever cross the wire in the current code is empirical, not
  derivable from grep.

Scope decision for the MDOT 1126 export proof:

- Honor the Unified Todo's "where applicable" and "where bytes are created"
  qualifiers instead of forcing an inapplicable assertion on a local-only
  family.
- Drive the production UI path (`/forms` saved mode -> tap MDOT 1126 ->
  export decision dialog -> "Export As-Is" or "Attach and Export").
- Assert local `form_exports` and `export_artifacts` rows via `/driver/local-record`
  and `/driver/query-records`.
- Assert the local PDF bytes exist at the recorded `file_path`. A small
  `/driver/local-file-head` endpoint will be added so PowerShell can HEAD the
  file size/hash without an `adb shell run-as` dance.
- Empirically probe Supabase Storage via `tools/sync-soak/StorageProof.ps1` at
  `form-exports/{company}/{project}/{filename}`. Record both outcomes as
  artifact-backed fact: "bytes-at-remote = yes/no". Do not fail the run if
  bytes are absent; do fail if they are present and unauthorized download
  succeeds.
- `change_log` proof applies only to `form_responses` during cleanup (soft
  delete) if the cleanup path touches it; export rows themselves emit no
  change_log entries by design.
- Cleanup is ledger-owned: UI/service soft-delete, prove local row absence,
  prove local file absence, and prove storage absence where bytes were
  previously proven.
- Final queue drain gate applies unchanged.
- The empirical "bytes-at-remote" outcome feeds a P1 sync-engine follow-up:
  if bytes never land remotely, the `skipPush=true` on `form_exports` and
  `export_artifacts` needs an explicit design decision (keep local-only vs
  flip to remote-backed) before the consistency contract doc is written.

Open next:

- Template the flow off `tools/sync-soak/Flow.Mdot1126Signature.ps1` and
  `tools/sync-soak/FormFlow.ps1`; add a driver endpoint `/driver/local-file-head`
  for local-file HEAD proofs; wire into `DeviceLab.RefactoredDispatcher.ps1` so
  `-Flow mdot1126-export-only` runs end-to-end on S21.

## 2026-04-18 - Slice A: /driver/local-file-head endpoint landed

What changed:

- Added `DriverDataSyncRoutes.localFileHead = '/driver/local-file-head'` and
  registered it in `isQueryPath` and `matches`
  (`lib/core/driver/driver_data_sync_routes.dart`).
- Wired `GET /driver/local-file-head` into `DriverDataSyncHandler.handle` and
  added `_handleLocalFileHead` forwarding to the new query-routes part
  (`lib/core/driver/driver_data_sync_handler.dart`).
- Implemented `_handleLocalFileHeadRoute`
  (`lib/core/driver/driver_data_sync_handler_query_routes.dart`). Contract:
  - Allowlisted tables: `form_exports` (column `file_path`) and
    `export_artifacts` (column `local_path`). Any other table returns 400.
  - Requires `table` and `id` query params. Optional `sha256=true` to compute
    a SHA-256 hash of the file bytes.
  - Response: `{exists, table, pathColumn, filePath, size, modifiedMillis,
    sha256}` when the row exists; `{exists:false, reason:'no_path_recorded'|
    'file_missing', ...}` when the row exists but bytes do not.
  - Honors `rejectReleaseOrProfile` like the other driver query routes.
  - Uses sync file I/O (`existsSync`, `statSync`, `readAsBytesSync`) to keep
    `avoid_slow_async_io` lint clean.
- Added `crypto` import to `driver_data_sync_handler.dart` so the part file
  can call `sha256.convert`.
- Extended `test/core/driver/driver_data_sync_routes_test.dart` with:
  - coverage for `matches(localFileHead)`;
  - a new `local-file-head is a local-only query path` test that pins the
    exact URL, verifies it is a query path, and verifies it is neither a
    mutation nor maintenance path.

Why:

- Closes the Unified Todo P1 "storage bytes where bytes are created" gap for
  local-only export families (`form_exports`, `export_artifacts`). The soak
  harness can now HEAD the PDF at the exact path recorded in the row without
  an `adb shell run-as` dance, without exposing an arbitrary filesystem
  primitive, and without reading bytes unless the caller explicitly asks for
  a hash.
- Unblocks the rest of the MDOT 1126 export proof flow (slice B onward):
  PowerShell can now call
  `GET /driver/local-file-head?table=form_exports&id={id}&sha256=true`
  during the assertion phase.

Exact gates run:

- `dart analyze lib/core/driver/driver_data_sync_routes.dart
  lib/core/driver/driver_data_sync_handler.dart
  lib/core/driver/driver_data_sync_handler_query_routes.dart` — no issues.
- `flutter test test/core/driver/driver_data_sync_routes_test.dart -r expanded`
  — 3/3 tests passed.

Known deferrals:

- No on-device integration test in this slice. The endpoint lives inside the
  app process, so verifying the live response requires rebuilding and
  reinstalling the debug app on S21 and S10. That rebuild happens with the
  next flow slice when there is a concrete request to exercise end-to-end.

Open next:

- Slice B: scaffold `tools/sync-soak/Flow.Mdot1126Export.ps1` using
  `Flow.Mdot1126Signature.ps1` as the template, extract export-specific
  navigation/assertion helpers into `FormFlow.ps1`, and wire
  `-Flow mdot1126-export-only` through `DeviceLab.RefactoredDispatcher.ps1`.
- Slice C: on-device acceptance run on S21, then S10 regression after
  rebuilding both devices against the new endpoint.

## 2026-04-18 — Task #3 Slice B: `mdot1126-export-only` flow landed + wired (harness-only, not yet device-accepted)

What:

- Created `tools/sync-soak/Flow.Mdot1126Export.ps1` with the export proof
  contract (~450 lines). Key functions:
  - `Invoke-SoakMdot1126ExportTapAndConfirm`: reopens `/form/<id>`, taps
    `form_export_button`, chooses `form_export_export_as_is_button` on the
    `form_export_decision_dialog`, waits for `form_standalone_export_dialog`,
    and dismisses via `form_standalone_export_not_now_button`, each wrapped
    in `Invoke-SoakStateTransition` with route/boolean sentinels.
  - `Wait-SoakMdot1126ExportRows`: polls `form_exports` by
    `form_response_id` and `export_artifacts` by `source_record_id` via
    `/driver/query-records`; asserts active (non-deleted) rows with matching
    `project_id`, `form_type='mdot_1126'`, `artifact_type='form_pdf'`,
    `file_path` non-empty, `file_size_bytes > 0`, and
    `export_artifacts.local_path == form_exports.file_path`.
  - `Assert-SoakMdot1126ExportLocalFileProof`: calls the Slice A endpoint
    `GET /driver/local-file-head?table=form_exports&id=<id>&sha256=true` and
    pins `exists`, `filePath == file_path`, `size == file_size_bytes`, and
    non-empty `sha256`.
  - `Assert-SoakMdot1126ExportChangeLogSkipped`: negative proof — pulls
    `/driver/change-log?table=form_exports` and `table=export_artifacts`,
    fails loudly if either new row id shows up. This is the direct gate on
    `sync_engine_tables.dart:218-222 localOnlyExportHistoryTables` trigger
    suppression.
  - `Invoke-SoakMdot1126ExportLedgerCleanup`: soft-deletes
    `export_artifacts` then `form_exports` via `/driver/update-record` with
    `{deleted_at, deleted_by, updated_at}`, re-runs the change-log-skip
    assertion post-cleanup, then delegates to
    `Invoke-SoakMdot1126SignatureLedgerCleanup` (with
    `-RequireStorageRemotePath`) for the underlying `form_responses` +
    `signature_files` + `signature_audit_log` cascade. The signature
    cleanup also scrubs the `signatures` storage bucket.
  - `Invoke-SoakMdot1126ExportOnlyRun`: the actor/round runner. Reuses
    `New-SoakActorRunContext`, `Invoke-SoakActorPreflightCapture`
    (`-CountLogcatClearAsLoggingGap`), `Write-SoakActorPreflightFailure`,
    `Invoke-SoakActorFinalCapture`, and
    `Complete-SoakDeviceSummary -RejectDirectSync` from `FlowRuntime.ps1`,
    with the mutation body calling `SignatureCreate` → `SignatureSubmit` →
    `Wait-SoakMdot1126SignatureRows` → UI-driven sync dashboard
    (`Invoke-SoakSyncDashboardFlow`) → `Wait-SoakMdot1126SignatureRemotePath`
    → the new export helpers above. Failure path falls back to
    `Invoke-SoakMdot1126DraftFormCleanup` when the mutation ledger entry
    has not been built yet.
- Added `Get-SoakDriverLocalFileHead` to
  `tools/sync-soak/DriverClient.ps1` as the canonical client wrapper so
  later flows (MDOT 0582B, MDOT 1174R) can reuse the same call shape.
- Wired the new flow through the harness surface:
  - `tools/sync-soak/ModuleLoader.ps1`: added
    `Flow.Mdot1126Export.ps1` to `Get-SoakModuleLoadOrder` (after
    `Flow.Mdot1126Signature.ps1`) and mapped
    `mdot1126-export-only => Invoke-SoakMdot1126ExportOnlyRun` in
    `Get-SoakAcceptedFlowFunctions`.
  - `tools/sync-soak/DeviceLab.RefactoredDispatcher.ps1`: added the
    `mdot1126-export-only` switch case + docstring line.
  - `tools/enterprise-sync-soak-lab.ps1`: added `mdot1126-export-only`
    to the `-Flow` `ValidateSet`.
  - `tools/test-sync-soak-harness.ps1`: added the dot-source for
    `Flow.Mdot1126Export.ps1`.
  - `tools/sync-soak/tests/FlowWiring.Tests.ps1`: added four new
    assertions so any regression in dispatcher wiring, UI marker usage,
    row-proof shape, change-log-skip assertion, or cleanup cascade
    trips the harness self-tests.

Why:

- Task #3 MDOT 1126 builtin form export proof requires a runner that
  demonstrates: (1) the UI-driven export writes `form_exports` +
  `export_artifacts` correctly, (2) the file bytes are truly on disk at
  the path the row claims, (3) neither table emits a `change_log` row
  (trigger skip for `localOnlyExportHistoryTables`), and (4) no remote
  push is issued (adapter `skipPush:true` / `skipPull:true`). This slice
  encodes every one of those gates as hard assertions and fails the
  round on any violation.
- Keeping the flow on the refactored envelope (`FlowRuntime` +
  `RejectDirectSync`) preserves acceptance semantics already earned by
  the other MDOT flows.

Exact gates run:

- PowerShell AST parse on six touched files — clean:
  `Flow.Mdot1126Export.ps1`, `DriverClient.ps1`, `ModuleLoader.ps1`,
  `DeviceLab.RefactoredDispatcher.ps1`,
  `tools/enterprise-sync-soak-lab.ps1`,
  `tests/FlowWiring.Tests.ps1`.
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` — 9 test files,
  all assertions green. This includes the new export-flow wiring block
  (`mdot1126-export-only` present in lab entrypoint + dispatcher +
  module loader; new UI keys wired; local-file-head proof present;
  change-log skip assertion present; signature cascade cleanup wired).

Known deferrals:

- No on-device acceptance yet. This slice is harness code only. Slice C
  (next) is the S21 acceptance run + S10 regression. That requires
  rebuilding the debug app on both devices against Slice A's new
  `/driver/local-file-head` route (rebuild has not happened yet) and
  then executing
  `pwsh tools/enterprise-sync-soak-lab.ps1 -Flow mdot1126-export-only`
  against each actor.
- The `FlowWiring.Tests.ps1` assertions are *source-shape* gates, not
  behavioral gates — they prove the keys, function names, and wiring
  strings are present, not that the device-driven flow actually works.
  The behavioral gate is Slice C on real hardware.

Open next:

- Slice C: rebuild S21 + S10 debug app, run
  `mdot1126-export-only` on S21, iterate until green; then S10 regression.
  Capture the timeline + mutation ledger as evidence artifacts in
  `.claude/codex/evidence/`.

## 2026-04-18 — Slice C: MDOT 1126 builtin export proof accepted on S21 and S10

What changed:

- Added the existing `TestingKeys.formStandaloneExportDialog` key to the
  `AppDialog.show` call inside `FormStandaloneExportDialog.show()`. This makes
  the actual dialog root driver-visible instead of relying only on an action
  button.
- Hardened `tools/sync-soak/Flow.Mdot1126Export.ps1` for both valid export
  branches:
  - standalone/unattached forms may show `form_export_decision_dialog`, after
    which the flow taps `form_export_export_as_is_button`;
  - report-attached forms skip that decision by design and go straight to PDF
    generation plus `form_standalone_export_dialog`.
- Preserved the same export acceptance assertions after either branch:
  `form_exports` row, `export_artifacts` row, local file size/hash proof via
  `/driver/local-file-head`, negative `change_log` proof for both local-only
  export tables, ledger-owned cleanup, signature cascade cleanup, UI-triggered
  cleanup sync, and final empty queue.

Why:

- The first S21 export attempt proved the app was correctly taking the
  report-attached export branch. `_prepareResponseForExport()` skips the
  attach/export decision when `response.entryId != null`, and the failure step
  captured 74 PDF log entries after tapping `form_export_button`.
- The flow was too narrow: it always waited for
  `form_export_decision_dialog`, which is only valid for standalone forms. The
  harness now matches production behavior without weakening the downstream
  export-row/file/cleanup gates.

Exact local gates run:

- `dart analyze lib/features/forms/presentation/widgets/form_standalone_export_dialog.dart`
  — no issues.
- `flutter test test/features/forms/presentation/widgets/form_standalone_export_dialog_test.dart -r expanded`
  — passed.
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` — passed, 9 test
  files.
- PowerShell AST parse on the touched sync-soak flow/wiring files — clean.

Device rebuilds and hygiene:

- Rebuilt/restarted S21 with
  `pwsh -NoProfile -File tools/start-driver.ps1 -Platform android -DeviceId RFCNC0Y975L -DriverPort 4948 -Timeout 240 -ForceRebuild`.
- Rebuilt/restarted S10 with
  `pwsh -NoProfile -File tools/start-driver.ps1 -Platform android -DeviceId R52X90378YB -DriverPort 4949 -Timeout 240 -ForceRebuild`.
- Restored S21 forwarding after S10 startup cleared the host-side S21 forward.
- S21 pre-run queue was empty.
- S10 had one pre-existing `form_responses` update after pulling the S21
  cleanup; it was recovered through UI `sync-only` before the S10 export
  regression.

Exact live gates run:

- `20260418-s21-mdot1126-export-initial` — failed cleanly with
  `widget_wait_timeout` waiting for `form_export_decision_dialog`; final queue
  drained, `runtimeErrors=0`, `loggingGaps=0`,
  `directDriverSyncEndpointUsed=false`.
- `20260418-s21-mdot1126-export-after-attached-branch-fix` — passed
  `mdot1126-export-only` on S21:
  - `form_exports/1db318cb-07ee-41c2-935f-f5a4f4ee2831`;
  - `export_artifacts/0f446168-6e24-4370-b1ba-6533f1c0b736`;
  - local PDF
    `/data/user/0/com.fieldguideapp.inspector/cache/MDOT_1126_2026-04-18_e8eec8b5.pdf`;
  - file size `363465`;
  - SHA-256
    `5b3e002eabcdbd9eba2798375e4cb7bdae287fdd627163e9518509b5e003d142`;
  - export tables absent from `change_log`;
  - signature storage presence/delete/absence proved for the underlying
    signature object;
  - queue drained, `blockedRowCount=0`, `unprocessedRowCount=0`,
    `maxRetryCount=0`, `runtimeErrors=0`, `loggingGaps=0`,
    `directDriverSyncEndpointUsed=false`.
- `20260418-s10-mdot1126-export-preflight-recovery-sync-only` — passed S10
  UI-only queue recovery before regression.
- `20260418-s10-mdot1126-export-after-attached-branch-fix` — passed
  `mdot1126-export-only` on S10:
  - `form_exports/42b68f47-fa72-414d-9e46-724e6d883db9`;
  - `export_artifacts/eb087db2-ef94-4d36-9fc0-b6738bbac5a9`;
  - local PDF
    `/data/user/0/com.fieldguideapp.inspector/cache/MDOT_1126_2026-04-18_ec75d04c.pdf`;
  - file size `363465`;
  - SHA-256
    `72b002f452d7ba354a0ed91ff2e7851f0966cfc5b236949abab55cd1392d8a0d`;
  - export tables absent from `change_log`;
  - signature storage presence/delete/absence proved for the underlying
    signature object;
  - queue drained, `blockedRowCount=0`, `unprocessedRowCount=0`,
    `maxRetryCount=0`, `runtimeErrors=0`, `loggingGaps=0`,
    `directDriverSyncEndpointUsed=false`.

Artifact paths:

- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-export-initial/`
- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-export-after-attached-branch-fix/`
- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot1126-export-preflight-recovery-sync-only/`
- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot1126-export-after-attached-branch-fix/`

Checklist items completed:

- Immediate Slice C MDOT 1126 export proof through S21 acceptance and S10
  regression.
- P1 Builtin Form Export Proof item for `mdot_1126`.

Open next:

- Generalize/reuse the accepted export proof for `mdot0582b-export-only`.
- Then implement `mdot1174r-export-only`.
- Saved-form/gallery lifecycle remains open after export proof.

## 2026-04-18 — MDOT 0582B builtin export proof accepted on S21 and S10

What changed:

- Added `tools/sync-soak/FormExportFlow.ps1` as the shared local-only builtin
  form export proof helper surface:
  - production export tap/confirm path with optional attach/export decision;
  - paired `form_exports` + `export_artifacts` row proof;
  - `/driver/local-file-head` file size/hash proof;
  - negative `change_log` proof for both local-only export tables;
  - local-only export-row cleanup proof.
- Added `tools/sync-soak/Flow.Mdot0582BExport.ps1`, which reuses the accepted
  MDOT 0582B creation/edit/marker proof, syncs the form response through the
  Sync Dashboard, exports through the production `mdot_hub_pdf_button`, proves
  local export rows and bytes, cleans up the local export rows, then cleans up
  the underlying `form_responses` row through the existing generic
  form-response cleanup.
- Wired `mdot0582b-export-only` through:
  - `tools/enterprise-sync-soak-lab.ps1`;
  - `tools/sync-soak/ModuleLoader.ps1`;
  - `tools/sync-soak/DeviceLab.RefactoredDispatcher.ps1`;
  - `tools/test-sync-soak-harness.ps1`;
  - `tools/sync-soak/tests/FlowWiring.Tests.ps1`.
- Expanded `tools/sync-soak/S10Regression.ps1` and its self-test to include
  the current MDOT S10 gates, including `mdot1126-export-only`,
  `mdot1126-expanded-only`, `mdot0582b-only`, `mdot0582b-export-only`, and
  `mdot1174r-only`.

Why:

- The controlling todo required MDOT 0582B export/storage proof to stay
  separate from the previously accepted MDOT 0582B form-response mutation
  proof.
- Current app semantics for `form_exports` and `export_artifacts` are
  local-only (`skipPush/skipPull`), so the export proof asserts local rows,
  on-device bytes, trigger suppression, and cleanup instead of requiring
  non-existent remote export rows.

Exact local gates run:

- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` — passed, 9 test
  files.
- PowerShell AST parse on `FormExportFlow.ps1`, `Flow.Mdot0582BExport.ps1`,
  `S10Regression.ps1`, dispatcher/module/entrypoint wiring, and updated tests
  — clean.
- `pwsh -NoProfile -File tools/enterprise-sync-soak-lab.ps1 -Flow mdot0582b-export-only -PrintS10RegressionRunGuide -Actors S10:4949:inspector:2`
  — printed the expanded 11-gate S10 command guide.

Exact live gates run:

- `20260418-s21-mdot0582b-export-initial` — passed `mdot0582b-export-only` on
  S21:
  - `form_exports/ad06b8f0-570e-4ca6-85bc-04439a7b56ed`;
  - `export_artifacts/64dad3e0-c590-4ac6-bd0f-a608a9dce4bb`;
  - local PDF
    `/data/user/0/com.fieldguideapp.inspector/cache/MDOT_0582B_2026-04-18_cc97fa4a.pdf`;
  - file size `775864`;
  - SHA-256
    `9ce8fd72ae05a844a2dbd665e2fb1db46d99a76807f462ff46735bea0d9d2495`;
  - export tables absent from `change_log`;
  - queue drained, `blockedRowCount=0`, `unprocessedRowCount=0`,
    `maxRetryCount=0`, `runtimeErrors=0`, `loggingGaps=0`,
    `directDriverSyncEndpointUsed=false`.
- `20260418-s10-mdot0582b-export-initial` — passed `mdot0582b-export-only` on
  S10:
  - `form_exports/b9e3cf93-757e-492c-beb8-7e04acc0d845`;
  - `export_artifacts/b09df381-9f0e-43a9-8c4c-15d6e36f0c82`;
  - local PDF
    `/data/user/0/com.fieldguideapp.inspector/cache/MDOT_0582B_2026-04-18_84b38b4f.pdf`;
  - file size `775865`;
  - SHA-256
    `6b52096ec3cee301e5c6c5e8718479134047e45839663741e2de0ab0d2cf0534`;
  - export tables absent from `change_log`;
  - queue drained, `blockedRowCount=0`, `unprocessedRowCount=0`,
    `maxRetryCount=0`, `runtimeErrors=0`, `loggingGaps=0`,
    `directDriverSyncEndpointUsed=false`.

Artifact paths:

- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-export-initial/`
- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot0582b-export-initial/`

Checklist items completed:

- P1 Builtin Form Export Proof item for `mdot_0582b`.
- Shared export proof helper extraction for the remaining builtin form export
  lanes.

Open next:

- Implement and accept `mdot1174r-export-only`.
- Then continue saved-form/gallery lifecycle sweeps.

## 2026-04-18 — MDOT 1174R builtin export proof accepted on S21 and S10

What changed:

- Added `tools/sync-soak/Flow.Mdot1174RExport.ps1`, which reuses the accepted
  MDOT 1174R create/open/edit/marker proof, syncs the form response through
  the Sync Dashboard, exports through the production `form_export_button`,
  proves local export rows and bytes through `FormExportFlow.ps1`, cleans up
  the local-only export rows, then cleans up the underlying `form_responses`
  row through the generic form-response cleanup.
- Wired `mdot1174r-export-only` through:
  - `tools/enterprise-sync-soak-lab.ps1`;
  - `tools/sync-soak/ModuleLoader.ps1`;
  - `tools/sync-soak/DeviceLab.RefactoredDispatcher.ps1`;
  - `tools/test-sync-soak-harness.ps1`;
  - `tools/sync-soak/tests/FlowWiring.Tests.ps1`;
  - `tools/sync-soak/S10Regression.ps1`;
  - `tools/sync-soak/tests/S10RegressionGuide.Tests.ps1`.

Why:

- The controlling todo required the MDOT 1174R export proof to complete the
  generic builtin-form export lane after MDOT 1126 and MDOT 0582B were accepted.
- Current app semantics for `form_exports` and `export_artifacts` are
  local-only (`skipPush/skipPull`), so this proof asserts local rows,
  on-device bytes, trigger suppression, and cleanup instead of remote export
  rows or storage objects.

Exact local gates run:

- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` — passed, 9 test
  files.
- PowerShell AST parse on `Flow.Mdot1174RExport.ps1`,
  `S10Regression.ps1`, dispatcher/module/entrypoint wiring, and updated tests
  — clean.

Exact live gates run:

- `20260418-s21-mdot1174r-export-initial` — passed
  `mdot1174r-export-only` on S21:
  - `form_responses/5609da9b-1749-4d71-a061-a7da46f41a45`;
  - `form_exports/bb038620-8bda-4f12-8ff3-12f766d1cd10`;
  - `export_artifacts/e6aa8fa6-5285-458f-af1d-1258b65e12bf`;
  - local PDF
    `/data/user/0/com.fieldguideapp.inspector/cache/MDOT_1174R_2026-04-18_5609da9b.pdf`;
  - file size `75508`;
  - SHA-256
    `cea5eb3ef9cad81bb6c14d784b6f184d40a681e3bdfe439ca15e382eef521c46`;
  - export tables absent from `change_log`;
  - queue drained, `blockedRowCount=0`, `unprocessedRowCount=0`,
    `maxRetryCount=0`, `runtimeErrors=0`, `loggingGaps=0`,
    `directDriverSyncEndpointUsed=false`.
- `20260418-s10-mdot1174r-export-initial` — passed
  `mdot1174r-export-only` on S10:
  - `form_responses/18fb00f6-5fb9-4337-8095-ea591da4e4bb`;
  - `form_exports/e40ff8ed-7ae3-45a1-a719-4115e777c190`;
  - `export_artifacts/a5b86437-0437-47fb-94a0-9b06da0c9232`;
  - local PDF
    `/data/user/0/com.fieldguideapp.inspector/cache/MDOT_1174R_2026-04-18_18fb00f6.pdf`;
  - file size `75508`;
  - SHA-256
    `abad92554598729f225309d4601e005cd6b31106376808bd9509339b0c06b2ce`;
  - export tables absent from `change_log`;
  - queue drained, `blockedRowCount=0`, `unprocessedRowCount=0`,
    `maxRetryCount=0`, `runtimeErrors=0`, `loggingGaps=0`,
    `directDriverSyncEndpointUsed=false`.

Artifact paths:

- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-export-initial/`
- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot1174r-export-initial/`

Checklist items completed:

- P1 Builtin Form Export Proof item for `mdot_1174r`.
- Generic builtin form export proof for the current local-only
  `form_exports` / `export_artifacts` contract across MDOT 1126, MDOT 0582B,
  and MDOT 1174R.

Open next:

- Saved-form/gallery lifecycle sweeps for MDOT 1126, MDOT 0582B, and
  MDOT 1174R.
- Broader file/storage/attachment hardening remains open because form exports
  are currently local-only and do not yet prove remote storage objects.

## 2026-04-18 - Saved-form/gallery lifecycle accepted on S21 and S10

What changed:

- Added the refactored `form-gallery-lifecycle-only` flow in
  `tools/sync-soak/Flow.FormGalleryLifecycle.ps1`.
- Wired the flow through the lab entrypoint, module loader, refactored
  dispatcher, S10 regression guide, and harness self-tests.
- Hardened the production UI and driver surfaces needed by the lifecycle lane:
  - `/forms?projectId=...` routing for project-scoped gallery entry;
  - post-frame form-gallery document loading to avoid build-time notifier
    mutations;
  - disposed-controller guards for async Sync Dashboard reload/repair paths;
  - explicit saved-response trailing action key while keeping the whole tile
    tappable for normal users;
  - report attached-form delete confirm/cancel keys;
  - driver tap callback dispatch for visible tappable descendants;
  - GoRouter route inspection for pushed `/form/:id` routes;
  - MDOT 0582B expanded-layout `mdot_hub_scroll_view` key.

Why:

- The controlling todo required a production lifecycle proof that creates an
  attached saved form, reopens it from the gallery, edits and saves the same
  response, exercises export, deletes through report UI/service seams, syncs
  through the Sync Dashboard, and proves remote soft delete/absence after
  cleanup.
- The flow keeps the same acceptance envelope as the other refactored soak
  lanes: real sessions, no `MOCK_AUTH`, UI-triggered sync, mutation ledgers,
  final queue drain, and `directDriverSyncEndpointUsed=false`.

Exact local gates run:

- `dart analyze` on the touched Dart driver/router/form/sync files and focused
  tests - no issues.
- `flutter test` on:
  - `test/features/forms/presentation/screens/form_gallery_screen_test.dart`;
  - `test/features/entries/presentation/widgets/entry_forms_section_test.dart`;
  - `test/features/sync/presentation/controllers/sync_dashboard_controller_test.dart`;
  - `test/core/driver/driver_widget_inspector_test.dart`;
  - `test/core/driver/driver_interaction_routes_test.dart`.
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` - passed, 9 test
  files.

Diagnostic recovery before final acceptance:

- S21 had failed-run residue
  `form_responses/a8d0b240-86a6-4c34-9fad-fc230b17de9d` with an empty
  `deleted_by`.
- Correct actor context was read through `/diagnostics/actor_context`; the row
  was repaired with real user `d1ca900e-d880-4915-9950-e29ba180b028`.
- `20260418-s21-gallery-lifecycle-residue-userid-fix-sync-only` then passed
  through UI `sync-only` with final empty change-log.

Exact live gates run:

- `20260418-s21-form-gallery-lifecycle-final-build` - passed
  `form-gallery-lifecycle-only` on S21 with `queueDrainResult=drained`,
  `failedActorRounds=0`, `runtimeErrors=0`, `loggingGaps=0`,
  `blockedRowCount=0`, `unprocessedRowCount=0`, `maxRetryCount=0`, and
  `directDriverSyncEndpointUsed=false`.
- `20260418-s10-form-gallery-lifecycle-after-expanded-hub-key` - passed
  `form-gallery-lifecycle-only` on S10 with the same queue, runtime, logging,
  and direct-sync gates.

Accepted S21 ledger IDs:

- `mdot_1126`:
  `form_responses/0daa8349-cc23-4eaa-895e-bbcef8b7e2e7`,
  `form_exports/8486fcf4-1fa9-427e-9e53-70e105a94cab`,
  `export_artifacts/614d8cc7-0da6-4406-aaa4-dedbc1149a12`,
  file size `364015`.
- `mdot_0582b`:
  `form_responses/9685c4a9-ba17-4701-bf25-bc4147870571`,
  `form_exports/11553762-bf4b-4ac1-871e-0f2967f0bdcd`,
  `export_artifacts/47b03535-8b71-4b09-b4e2-a7eeac35dd9a`,
  file size `775864`.
- `mdot_1174r`:
  `form_responses/7a8f2c49-0c4f-4b7d-9ba3-4afb81f2da66`,
  `form_exports/a40effdf-ad6c-4a5a-b2cd-e114aec0c9a7`,
  `export_artifacts/167600f5-8e97-4ca1-88cc-cd617284a922`,
  file size `75508`.

Accepted S10 ledger IDs:

- `mdot_1126`:
  `form_responses/99a2fb1c-38fe-4817-b01d-694d522ade7b`,
  `form_exports/fcd57aed-6cd7-4a63-acf8-bf3ccbd2abab`,
  `export_artifacts/c71c18f2-0b3c-4f59-a642-81935dd80e38`,
  file size `364015`.
- `mdot_0582b`:
  `form_responses/5aed14a2-273d-4e7f-b512-c109b9a8d74f`,
  `form_exports/fa373a7a-c2de-4f6c-9b87-37bf50f03ecd`,
  `export_artifacts/4692fc6f-c7f8-4007-877b-9ada6b9ea317`,
  file size `775864`.
- `mdot_1174r`:
  `form_responses/aac12ea1-6cee-476a-becc-717b99d92d9b`,
  `form_exports/7ba1c210-2289-43fd-8741-50bab02cc13e`,
  `export_artifacts/1a1b8d52-e2c8-4322-ab5f-728d9ba43d8a`,
  file size `75508`.

Artifact paths:

- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-gallery-lifecycle-residue-userid-fix-sync-only/`
- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-form-gallery-lifecycle-final-build/`
- `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-form-gallery-lifecycle-after-expanded-hub-key/`

Checklist items completed:

- P1 Saved-Form And Gallery Lifecycle for MDOT 1126, MDOT 0582B, and
  MDOT 1174R on S21/S10.
- The persistent live task list now records the accepted lifecycle evidence in
  `.codex/checkpoints/2026-04-18-sync-soak-unified-live-task-list.md`.

Open next:

- File/storage/attachment hardening beyond the current local-only form export
  contract.
- Role/account/RLS sweeps.
- Sync-engine correctness hardening.
- P2 workload, failure-injection, staging, scale, diagnostics, and consistency
  docs remain open.

## 2026-04-18 - Resume checkpoint after lifecycle acceptance

What was refreshed:

- Re-read `.codex/AGENTS.md`, `.codex/Context Summary.md`,
  `.codex/PLAN.md`, `.codex/CLAUDE_CONTEXT_BRIDGE.md`, the sync rules, this
  implementation log, the controlling unified todo, and the persistent live
  task list.
- Reviewed the working tree before continuing. Tracked dirty files are limited
  to the unified todo and this implementation log; the visible live task list
  remains intentionally ignored but present at
  `.codex/checkpoints/2026-04-18-sync-soak-unified-live-task-list.md`.

Current accepted state:

- P0 device/harness hygiene, post-v61 signature proof, MDOT 1174R S21
  acceptance, S10 form regressions, responsive root-shell guardrail, builtin
  form export proof, and saved-form/gallery lifecycle proof are recorded as
  accepted in the controlling todo.
- Latest device lifecycle evidence remains:
  `20260418-s21-form-gallery-lifecycle-final-build` and
  `20260418-s10-form-gallery-lifecycle-after-expanded-hub-key`, both with
  drained queues, zero runtime/logging gaps, and
  `directDriverSyncEndpointUsed=false`.

Current open gate:

- The next unchecked P1 lane is File, Storage, And Attachment Hardening. The
  first step is to inventory the production file-backed table families,
  storage buckets, cleanup queues, and existing proof helpers, then implement
  the next smallest evidence-backed hardening slice.

Checklist status:

- Updated the live task list with a new visible "Current Focus - P1 File,
  Storage, And Attachment Hardening" section so the next session can resume
  without inferring state from older export/lifecycle details.

## 2026-04-18 - Sync engine keyset pagination and phase-log hardening

What changed:

- Fixed file sync phase logging so a phase 2 metadata upsert failure is
  reported as "Phase 2 metadata upsert failed" with `failed_phase: 2`,
  `table_name`, `record_id`, and `remote_path` fields instead of the old
  misleading phase 3 bookmark message.
- Replaced production pull pagination with stable keyset pagination ordered by
  `updated_at` and `id`; `SupabaseSync.fetchPage` now uses the
  `updated_at/id` boundary and `limit(pageSize)` rather than range/offset for
  production pulls.
- Added durable pull page checkpoint storage in `sync_metadata` via
  `PullPageCheckpoint`, `readPullPageCheckpoint`, `writePullPageCheckpoint`,
  and `clearPullPageCheckpoint`.
- Updated `PullHandler` to resume from the stored keyset checkpoint and persist
  the checkpoint only after a full page has been applied. Final partial pages
  still rely on the table cursor being advanced after successful completion.
- Updated fake sync support and contract tests to exercise keyset boundaries.

Local evidence:

- `dart analyze lib/features/sync/engine/file_sync_three_phase_workflow.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/file_sync_handler_test.dart -r expanded`
  passed 16 tests.
- `dart analyze lib/features/sync/engine/sync_metadata_store.dart lib/features/sync/engine/local_sync_store_metadata.dart lib/features/sync/engine/pull_handler.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/pull_handler_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/pull_handler_contract_test.dart test/features/sync/engine/supabase_sync_contract_test.dart -r expanded`
  passed 79 tests.

Checklist updates:

- Closed the stable keyset/checkpoint pagination item.
- Closed equal-`updated_at` page-boundary and concurrent-remote-insert tests.
- Closed the misleading file-sync phase logging item.
- Recorded restart after a stored full-page keyset checkpoint as covered.

Still open:

- Long-offline pull evidence.
- Crash/restart after a partial final page.
- Per-scope reconciliation, write checkpoint semantics, freshness gating,
  realtime hint/fallback behavior, idempotent replay, crash/restart matrix, and
  domain-specific conflict strategy.
- File/storage/attachment hardening remains the next P1 implementation lane
  after the current local hygiene and device status probes are recorded.

Device hygiene after local sync-engine slice:

- S21 `http://127.0.0.1:4948`: `/driver/ready` returned ready on
  `/sync/dashboard`; `/driver/change-log` returned `count=0`,
  `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`; and
  `/driver/sync-status` returned `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`.
- S10 `http://127.0.0.1:4949`: `/driver/ready` returned ready on
  `/sync/dashboard`; `/driver/change-log` returned `count=0`,
  `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`; and
  `/driver/sync-status` returned `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`.

## 2026-04-18 - Image fixture storage hardening

Inventory outcome:

- Production file-backed families found in adapters/schema/harness: photos
  (`entry-photos`), signature files (`signatures`), documents
  (`entry-documents`), entry exports (`entry-exports`), form exports
  (`form-exports`), export artifacts (`export-artifacts`), and
  pay-application rows that reference export artifacts.
- Existing harness helpers already cover local file head checks and storage
  object proof for accepted photo/signature lanes and local-only form export
  proofs. Entry documents, entry exports, pay-app export storage proof,
  unauthorized storage denial, cross-device preview/download, and broader
  cleanup retry assertions remain open.

What changed:

- Added generated small, normal, large, and GPS-EXIF JPEG fixtures to
  `file_sync_handler_test.dart`.
- Drove those fixtures through both `FileSyncHandler.stripExifGps` and the
  production phase-1 upload path, proving uploaded JPEG bytes remain decodable
  and do not retain GPS EXIF.
- Fixed the GPS stripping implementation: `Image.from(image)` copied the
  source EXIF, including the GPS sub-IFD, before the allowed EXIF directories
  were copied. The workflow now resets EXIF and removes the GPS subdirectory
  and GPS pointer before encoding.

Local evidence:

- `dart analyze lib/features/sync/engine/file_sync_three_phase_workflow.dart test/features/sync/engine/file_sync_handler_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/file_sync_handler_test.dart -r expanded`
  passed 18 tests.

Checklist updates:

- Closed P1 "Add small, normal, large, and GPS-EXIF image fixtures."

Still open:

- Storage object proof beyond photos/signatures.
- Unauthorized storage access denial for each bucket/path family.
- Cross-device download/preview for uploaded objects.
- Delete/restore/purge storage cleanup queue assertions beyond current local
  export-artifact coverage.
- Durable attachment/file states and crash/retry cases.
- PowerSync attachment-helper reuse triage.

## 2026-04-18 - Storage cleanup queue purge hardening

What changed:

- `GenericLocalDatasource.purgeExpired` now runs in a transaction, loads remote
  storage paths for file-backed rows before deletion, hard-deletes the expired
  rows, then queues storage cleanup with reason `purge`.
- Existing soft-delete and restore behavior remains unchanged: soft-delete
  queues cleanup with reason `soft_delete`, and restore cancels matching
  pending cleanup.
- Added export-artifact datasource coverage that asserts all three paths:
  soft-delete queueing, restore cancellation, and purge queueing before
  hard-delete.

Local evidence:

- `dart analyze lib/shared/datasources/generic_local_datasource.dart test/features/pay_applications/data/datasources/local/export_artifact_local_datasource_test.dart`
  passed with no issues.
- `flutter test test/features/pay_applications/data/datasources/local/export_artifact_local_datasource_test.dart -r expanded`
  passed 4 tests.

Checklist updates:

- Closed P1 "`storage_cleanup_queue` assertions for delete/restore/purge
  paths."

Still open:

- Live storage-object absence proof after cleanup for entry documents, entry
  exports, form exports, and pay-app exports.
- Cleanup retry/failure injection around storage delete failures.

## 2026-04-18 - Long-offline and partial-page pull restart coverage

What changed:

- Added a long-offline pull test that drains 1,005 project rows across 11
  keyset pages and proves the first/last rows, page boundaries, result count,
  and cleared checkpoint.
- Added a pull restart test that simulates an apply-time crash on the second
  row of a partial final page.
- The test proves the last completed full-page checkpoint remains as the
  restart boundary, the already-applied partial-page row can be replayed, the
  missing row is applied on restart, the table cursor advances, and the
  checkpoint is cleared after successful completion.

Local evidence:

- `dart analyze test/features/sync/engine/pull_handler_test.dart` passed with
  no issues.
- `flutter test test/features/sync/engine/pull_handler_test.dart -r expanded`
  passed 21 tests.

Checklist updates:

- Closed P1 "Test long-offline pull."
- Closed P1 "Test restart after partial page."

Still open:

- Per-scope reconciliation, write-checkpoint semantics, freshness gating,
  realtime hint/fallback behavior, idempotent replay, broader crash/restart
  matrix, and domain-specific conflict strategy.

Final local sweep for this session:

- `git diff --check` passed.
- `dart analyze lib/features/sync/engine/file_sync_three_phase_workflow.dart lib/features/sync/engine/sync_metadata_store.dart lib/features/sync/engine/local_sync_store_metadata.dart lib/features/sync/engine/pull_handler.dart lib/features/sync/engine/supabase_sync.dart lib/shared/datasources/generic_local_datasource.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/supabase_sync_contract_test.dart test/features/pay_applications/data/datasources/local/export_artifact_local_datasource_test.dart test/helpers/sync/fake_supabase_sync.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/pull_handler_contract_test.dart test/features/sync/engine/supabase_sync_contract_test.dart test/features/pay_applications/data/datasources/local/export_artifact_local_datasource_test.dart -r expanded`
  passed 103 tests.

Final device hygiene probes:

- S21 `http://127.0.0.1:4948`: `/driver/change-log` returned `count=0`,
  `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`; and
  `/driver/sync-status` returned `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`.
- S10 `http://127.0.0.1:4949`: `/driver/change-log` returned `count=0`,
  `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`; and
  `/driver/sync-status` returned `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`.

## 2026-04-18 - Reconciliation probe primitive and device endpoint proof

What changed:

- Added the read-only debug route
  `/driver/local-reconciliation-snapshot`.
- The route returns local SQLite reconciliation facts for an allowed table:
  selected columns, total row count, hashed row count, bounded limit,
  truncation state, hash scope, stable `id ASC` order, SHA-256 hash, sample
  ids, and sample rows.
- Added `Get-SoakDriverLocalReconciliationSnapshot` to
  `tools/sync-soak/DriverClient.ps1`.
- Added `tools/sync-soak/Reconciliation.ps1` with:
  - canonical JSON and SHA-256 helpers;
  - Supabase REST remote snapshot support;
  - local/remote comparison classification for unavailable remote snapshots,
    truncated snapshots, row-count mismatches, and row-hash mismatches;
  - `New-SoakProjectReconciliationTableSpecs`, covering the required
    project-scope tables from the todo;
  - `Invoke-SoakReconciliationProbe`, which writes a probe artifact.
- Wired the new module into `ModuleLoader.ps1` and the local harness self-test
  runner.
- Added Dart route/handler tests and PowerShell reconciliation tests.

Why:

- The todo requires per-scope reconciliation probes after sync. Queue drain is
  necessary but not enough: a lane also needs artifact-backed row counts,
  stable hashes, local/remote samples, and mismatch classification.
- This slice lands the reusable primitive and proves the app-side endpoint on
  both physical devices. The post-sync flow artifact gate remains open until
  the probe is wired into the accepted flow summaries and required to pass
  local/remote comparison.

Local evidence:

- `dart analyze lib/core/driver/driver_data_sync_handler.dart lib/core/driver/driver_data_sync_handler_query_routes.dart lib/core/driver/driver_data_sync_routes.dart test/core/driver/driver_data_sync_handler_test.dart test/core/driver/driver_data_sync_routes_test.dart`
  passed with no issues.
- `flutter test test/core/driver/driver_data_sync_handler_test.dart test/core/driver/driver_data_sync_routes_test.dart -r expanded`
  passed 10 tests.
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` passed 10
  PowerShell harness test files.
- `git diff --check` passed.

Device evidence:

- Rebuilt/restarted S21 with:
  `pwsh -NoProfile -File tools/start-driver.ps1 -Platform android -DeviceId RFCNC0Y975L -DriverPort 4948 -Timeout 180 -ForceRebuild`.
- Rebuilt/restarted S10 with:
  `pwsh -NoProfile -File tools/start-driver.ps1 -Platform android -DeviceId R52X90378YB -DriverPort 4949 -Timeout 180 -ForceRebuild`.
- S21:
  - `/driver/ready` returned ready on `/projects`;
  - `/driver/change-log` returned `count=0`, `unprocessedCount=0`,
    `blockedCount=0`, `maxRetryCount=0`;
  - `/driver/sync-status` returned `isSyncing=false`, `pendingCount=0`,
    `blockedCount=0`, `unprocessedCount=0`,
    `lastSyncTime=2026-04-18T23:38:26.792802Z`;
  - `/driver/local-reconciliation-snapshot?table=projects&limit=100&sampleLimit=3&select=id,updated_at`
    returned `totalCount=7`, `hashedCount=7`, `truncated=false`,
    `hashScope=full`, and row hash
    `a7f5fec5ff4ad0c1019091b4f5388aadc94175bc4152cb36f945a40f3dca4ce5`.
- S10:
  - `/driver/ready` returned ready on `/projects`;
  - `/driver/change-log` returned `count=0`, `unprocessedCount=0`,
    `blockedCount=0`, `maxRetryCount=0`;
  - `/driver/sync-status` returned `isSyncing=false`, `pendingCount=0`,
    `blockedCount=0`, `unprocessedCount=0`,
    `lastSyncTime=2026-04-18T23:38:24.798705Z`;
  - `/driver/local-reconciliation-snapshot?table=projects&limit=100&sampleLimit=3&select=id,updated_at`
    returned `totalCount=6`, `hashedCount=6`, `truncated=false`,
    `hashScope=full`, and row hash
    `490b4159fb71fa06c618e068e17966d5e54d21871a54cb8d760c873d10125aa3`.

Checklist updates:

- Added checked sub-items under the P1 per-scope reconciliation probe item for
  the local driver endpoint, harness comparison primitive, and S21/S10 endpoint
  proof.
- Left the top-level reconciliation item open because accepted post-sync flow
  artifacts do not yet require passing local/remote reconciliation.

Still open:

- Wire `Invoke-SoakReconciliationProbe` into covered post-sync flow artifacts.
- Decide the explicit local-only table handling for current
  `form_exports`/`export_artifacts` semantics before using those tables as a
  remote mismatch gate.
- Run a live post-sync lane with remote reconciliation output and fail the
  lane on count/hash mismatch.

## 2026-04-18 - Duplicate pull replay coverage

What changed:

- Added a focused PullHandler test for duplicate pull page replay and duplicate
  row apply.
- The test pulls a page of projects once, then replays the exact same page
  through a fresh handler against the same local SQLite store.
- The replay must leave exactly one local row per id, return `pulled=0`, report
  no errors, and clear any pull-page checkpoint.

Why:

- The idempotent replay matrix in the controlling todo explicitly calls out
  duplicate pull page replay and duplicate row apply. The keyset pagination
  work covered restart boundaries; this test covers the direct "same remote
  page appears again" replay case.

Local evidence:

- `dart analyze test/features/sync/engine/pull_handler_test.dart` passed with
  no issues.
- `flutter test test/features/sync/engine/pull_handler_test.dart -r expanded`
  passed 22 tests.

Checklist updates:

- Added a checked sub-item under the idempotent replay matrix for duplicate
  pull page replay and duplicate row apply.
- Verified and indexed existing replay evidence for already-absent remote rows:
  `sync_engine_delete_test.dart` covers empty-response soft-delete replay, and
  `supabase_sync_contract_test.dart` covers hard-delete 404/not-found as
  idempotent success.
- Verified and indexed existing storage duplicate evidence:
  `file_sync_handler_test.dart` covers storage 409/already-exists continuing
  to phase 2 metadata upsert.
- Left the top-level replay matrix open because duplicate push, duplicate
  soft-delete, duplicate upload, row-upsert replay, bookmark replay, and other
  classes still need explicit indexed coverage.

Additional local evidence:

- `dart analyze test/features/sync/engine/sync_engine_delete_test.dart test/features/sync/engine/supabase_sync_contract_test.dart test/features/sync/engine/file_sync_handler_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/sync_engine_delete_test.dart test/features/sync/engine/supabase_sync_contract_test.dart test/features/sync/engine/file_sync_handler_test.dart -r expanded`
  passed 44 tests.

Final focused sweep after reconciliation and replay updates:

- `git diff --check` passed.
- `dart analyze lib/core/driver/driver_data_sync_handler.dart lib/core/driver/driver_data_sync_handler_query_routes.dart lib/core/driver/driver_data_sync_routes.dart test/core/driver/driver_data_sync_handler_test.dart test/core/driver/driver_data_sync_routes_test.dart test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/sync_engine_delete_test.dart test/features/sync/engine/supabase_sync_contract_test.dart test/features/sync/engine/file_sync_handler_test.dart`
  passed with no issues.
- `flutter test test/core/driver/driver_data_sync_handler_test.dart test/core/driver/driver_data_sync_routes_test.dart test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/sync_engine_delete_test.dart test/features/sync/engine/supabase_sync_contract_test.dart test/features/sync/engine/file_sync_handler_test.dart -r expanded`
  passed 76 tests.
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` passed 10
  PowerShell harness test files.

Final device hygiene after the focused sweep:

- S21 `/driver/change-log`: `count=0`, `unprocessedCount=0`,
  `blockedCount=0`, `maxRetryCount=0`; `/driver/sync-status`:
  `isSyncing=false`, `pendingCount=0`, `blockedCount=0`,
  `unprocessedCount=0`, `lastSyncTime=2026-04-18T23:38:26.792802Z`.
- S10 `/driver/change-log`: `count=0`, `unprocessedCount=0`,
  `blockedCount=0`, `maxRetryCount=0`; `/driver/sync-status`:
  `isSyncing=false`, `pendingCount=0`, `blockedCount=0`,
  `unprocessedCount=0`, `lastSyncTime=2026-04-18T23:38:24.798705Z`.

## 2026-04-18 - Post-sync reconciliation gate wired and device-proven

What changed:

- Added the read-only debug route
  `/driver/remote-reconciliation-snapshot`.
- The remote route mirrors the local reconciliation snapshot contract but reads
  through the app's real Supabase device session. This avoids host
  service-role credentials and keeps reconciliation evidence under the same
  real-session/RLS posture as the device flow.
- Normalized timestamp values in reconciliation rows before hashing so local
  SQLite offsets and Supabase UTC strings compare by instant, not by string
  representation.
- Added `excludeDeleted=true` support to local and remote reconciliation
  snapshots.
- Updated `tools/sync-soak/Reconciliation.ps1` so required project-table specs
  compare active row membership by stable `id`/`project_id` hashes.
- Kept `form_exports`, `export_artifacts`, and `entry_exports` in the
  reconciliation artifact, but marked them `comparisonMode=local_only` because
  the current adapters are intentionally `skipPush`/`skipPull` local export
  history tables.
- Added `-RequireReconciliation` and `-ReconciliationProjectIds` to
  `tools/enterprise-sync-soak-lab.ps1`. When enabled, the dispatcher runs
  `Invoke-SoakSummaryReconciliationGate` after the refactored flow and forces
  the summary to fail on any local/remote count/hash mismatch.

Why:

- The previous primitive could produce standalone snapshots, but accepted flow
  summaries did not yet fail on reconciliation mismatch. The unified todo
  requires post-sync local/remote row counts, stable hashes, samples, mismatch
  classification, and an acceptance gate.
- The first full probe intentionally failed on historical remote tombstones,
  which showed the gate was too broad for normal convergence. Active-row
  reconciliation now proves the sync-visible data set while tombstone retention
  and cleanup stay in delete/cleanup-specific gates.

Local evidence:

- `dart analyze lib/core/driver/driver_data_sync_handler.dart lib/core/driver/driver_data_sync_handler_query_routes.dart lib/core/driver/driver_data_sync_routes.dart test/core/driver/driver_data_sync_handler_test.dart test/core/driver/driver_data_sync_routes_test.dart`
  passed with no issues.
- `flutter test test/core/driver/driver_data_sync_handler_test.dart test/core/driver/driver_data_sync_routes_test.dart -r expanded`
  passed 13 tests.
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` passed 10
  PowerShell harness test files.
- `git diff --check` passed before the final doc update.

Device and artifact evidence:

- Rebuilt/restarted S21 and S10 driver apps so the running devices included
  `/driver/remote-reconciliation-snapshot` and the `excludeDeleted` query
  parameter.
- Direct S21/S10 project probes for
  `/driver/remote-reconciliation-snapshot?table=projects&whereColumn=id&whereValue=75ae3283-d4b2-4035-ba2f-7b4adb018199&select=id,updated_at`
  returned `authMode=device_session`, matching row count/hash, and full,
  non-truncated samples.
- `20260418-s21-sync-only-reconciliation-gate` failed as intended on
  reconciliation while all queue/runtime/logging/direct-sync gates were clean:
  `queueDrainResult=drained`, `runtimeErrors=0`, `loggingGaps=0`,
  `blockedRowCount=0`, `unprocessedRowCount=0`, `maxRetryCount=0`,
  `directDriverSyncEndpointUsed=false`, `reconciliationFailedCount=6`.
  The failure was caused by remote soft-deleted tombstones and timestamp/hash
  comparison strictness, proving the gate can fail an otherwise clean flow.
- After the active-row reconciliation contract landed, S21
  `20260418-s21-sync-only-active-reconciliation-gate-rerun` passed:
  `queueDrainResult=drained`, `runtimeErrors=0`, `loggingGaps=0`,
  `blockedRowCount=0`, `unprocessedRowCount=0`, `maxRetryCount=0`,
  `directDriverSyncEndpointUsed=false`, `reconciliationProjectCount=1`,
  `reconciliationTableCount=13`, and `reconciliationFailedCount=0`.
- The accepted reconciliation artifact covered:
  `projects`, `project_assignments`, `daily_entries`, `entry_quantities`,
  `photos`, `form_responses`, `signature_files`, `signature_audit_log`,
  `documents`, `pay_applications`, plus local-only `form_exports`,
  `export_artifacts`, and `entry_exports`.

Device hygiene after proof:

- S21 `/driver/change-log`: `count=0`, `unprocessedCount=0`,
  `blockedCount=0`, `maxRetryCount=0`; `/driver/sync-status`:
  `isSyncing=false`, `pendingCount=0`, `blockedCount=0`,
  `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:19:41.161132Z`.
- S10 `/driver/change-log`: `count=0`, `unprocessedCount=0`,
  `blockedCount=0`, `maxRetryCount=0`; `/driver/sync-status`:
  `isSyncing=false`, `pendingCount=0`, `blockedCount=0`,
  `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:18:47.159255Z`.

Checklist updates:

- Closed the P1 per-scope reconciliation probe item and the minimum required
  table-membership sub-item in the controlling todo.
- Updated the persistent live task list with the green S21 gate and preserved
  the earlier failed reconciliation gate as negative evidence.

Still open:

- Write-checkpoint semantics, sync freshness gating, realtime hint fallback
  proof, remaining idempotent replay classes, broader crash/restart cases,
  domain-specific conflict strategy, file/storage/attachment expansion,
  role/RLS sweeps, and all P2/P3 scale/staging/diagnostics/docs gates.

## 2026-04-18 - Idempotent replay matrix continuation started

Resume point:

- The accepted S21 active-row reconciliation gate remains the latest device
  proof for the sync-correctness lane.
- The next active P1 slice is the remaining idempotent replay matrix:
  duplicate local push after remote upsert succeeds, duplicate soft-delete
  push, duplicate upload, row-upsert replay, and bookmark replay.
- Existing indexed coverage already covers duplicate pull page replay,
  duplicate row apply, already-absent remote row replay, hard-delete
  not-found replay, and storage 409/already-exists replay.

Planned evidence before checking off the matrix:

- Focused Dart analyzer coverage for touched sync/file tests and helpers.
- Focused Flutter test coverage for the replay matrix files.
- `git diff --check`.
- S21/S10 driver hygiene probes when the running debug drivers are reachable.

## 2026-04-18 - Idempotent replay matrix completed locally

What changed:

- Added explicit PushHandler replay coverage for duplicate local push after a
  remote upsert succeeds. The test replays the pending change after the first
  successful push and proves the second idempotent upsert is processed cleanly.
- Added explicit PushHandler replay coverage for duplicate soft-delete push.
  The first push returns a tombstone row and the replay returns an empty
  response, matching the "remote already gone" path; both finish without queue
  residue.
- Added FileSyncHandler coverage for duplicate upload replay after storage
  already has the object. A 409-style `uploadFile=false` result proceeds to
  metadata upsert and bookmarks the local `remote_path`.
- Added FileSyncHandler coverage for row-upsert replay when local metadata
  already has `remote_path` but the local file is gone. The replay skips
  upload, re-upserts metadata, and leaves the bookmark stable.
- Added LocalSyncStore coverage for bookmark replay. Calling
  `bookmarkRemotePath` twice with the same object path stays idempotent,
  restores trigger state, and does not create `change_log` rows.

Local evidence:

- `dart analyze test/features/sync/engine/push_handler_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/sync_engine_delete_test.dart test/features/sync/engine/supabase_sync_contract_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/push_handler_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/sync_engine_delete_test.dart test/features/sync/engine/supabase_sync_contract_test.dart -r expanded`
  passed 118 tests.
- `git diff --check` passed with line-ending warnings only.

Device hygiene after proof:

- S21 `/driver/ready`: ready on `/sync/dashboard`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:19:41.161132Z`.
- S10 `/driver/ready`: ready on `/projects`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:18:47.159255Z`.

Checklist updates:

- Closed the remaining idempotent replay matrix under P1 Sync Engine
  Correctness Hardening.

Still open:

- Write-checkpoint semantics, sync freshness gating, realtime hint fallback
  proof, crash/restart tests, domain-specific conflict strategy,
  file/storage/attachment expansion, role/RLS sweeps, and all P2/P3
  scale/staging/diagnostics/docs gates.

## 2026-04-18 - Write-checkpoint freshness guard started

What changed:

- Added a `SyncEngine` freshness proof before `last_sync_time` is written.
- A sync run that otherwise has no push/pull errors now still refuses to mark
  sync fresh when `countPendingUploads()` reports remaining local changes after
  the run.
- A sync run that pushed local writes now refuses to mark sync fresh if no
  follow-up pull path ran in the same cycle. This closes the obvious
  pushed-without-pull freshness hole in strict quick-sync flows.
- Added focused engine tests for both guard failures.

Why:

- The previous coordinator wrote `last_sync_time` whenever the aggregate
  push/pull result had no errors. That allowed freshness to advance without a
  final queue-drain proof, and allowed a pushed write to look fresh if a quick
  sync skipped pull.
- This is a first write-checkpoint hardening slice. It proves queue drain and
  pull-path participation before freshness advances. It does not yet prove
  per-record server visibility and final local visibility for each
  acknowledged write; that remains open in the controlling todo.

Local evidence:

- `dart analyze lib/features/sync/engine/sync_engine.dart lib/features/sync/engine/sync_run_lifecycle.dart test/features/sync/engine/sync_engine_status_test.dart test/features/sync/engine/sync_engine_mode_plumbing_test.dart test/features/sync/engine/sync_engine_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/sync_engine_status_test.dart test/features/sync/engine/sync_engine_mode_plumbing_test.dart -r expanded`
  passed 11 tests.
- `git diff --check` passed with line-ending warnings only.

Device hygiene after proof:

- S21 `/driver/ready`: ready on `/sync/dashboard`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:19:41.161132Z`.
- S10 `/driver/ready`: ready on `/projects`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:18:47.159255Z`.

Checklist updates:

- Checked off queue-drain proof under write-checkpoint semantics.
- Checked off follow-up pull path proof for pushed-write cycles.
- Left full write-checkpoint semantics open for per-record remote write proof
  and final local proof through the server/pull path.

Still open:

- Per-record write-checkpoint proof, sync freshness proof through actual
  server/pull visibility, realtime hint fallback proof, crash/restart tests,
  domain-specific conflict strategy, file/storage/attachment expansion,
  role/RLS sweeps, and all P2/P3 scale/staging/diagnostics/docs gates.

## 2026-04-18 - Per-record write-checkpoint proof completed locally

What changed:

- Added `AcknowledgedWrite` and `RemoteLocalWriteCheckpointVerifier`.
- `PushHandler` now carries per-record acknowledged write identities in
  `PushResult` without changing aggregate push counts.
- `PushExecutionRouter` now reports proof-worthy server acknowledgements for:
  - normal upserts;
  - insert-only rows;
  - file metadata upserts;
  - soft deletes, including the idempotent "remote already absent" case.
- Skipped adapter work, out-of-scope work, and LWW-only skips remain counted
  according to the existing push semantics but do not enter the remote-write
  proof set.
- `SyncEngineResult` now carries acknowledged writes across push batches.
- `SyncEngine` now verifies each acknowledged write before writing
  `last_sync_time`, after the existing queue-drain and follow-up-pull guards.
- The verifier proves:
  - remote visibility through `SupabaseSync.fetchRecord()`;
  - expected delete state or acceptable remote absence for soft deletes;
  - final local visibility through `LocalSyncStore.readLocalRecord()` after
    the follow-up pull path;
  - non-deleted writes are still active locally/remotely;
  - matching `updated_at` instants when both local and remote rows expose them.

Why:

- The previous freshness guard proved final queue drain and pull-path
  participation, but still allowed `last_sync_time` to advance without proving
  that each acknowledged local write was visible through the server and final
  local store. This slice closes the remaining write-checkpoint semantics in
  the P1 Sync Engine Correctness lane.

Local evidence:

- `dart analyze lib/features/sync/engine/sync_write_checkpoint_proof.dart lib/features/sync/engine/sync_engine_result.dart lib/features/sync/engine/push_execution_router.dart lib/features/sync/engine/push_handler.dart lib/features/sync/engine/sync_engine.dart lib/features/sync/application/sync_engine_factory.dart test/features/sync/engine/sync_engine_status_test.dart test/features/sync/engine/push_handler_test.dart test/features/sync/engine/sync_write_checkpoint_proof_test.dart test/features/sync/application/sync_coordinator_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/sync_engine_status_test.dart test/features/sync/engine/push_handler_test.dart test/features/sync/engine/sync_write_checkpoint_proof_test.dart test/features/sync/application/sync_coordinator_test.dart -r expanded`
  passed 41 tests.
- `git diff --check` passed with line-ending warnings only.

Device hygiene after proof:

- S21 `/driver/ready`: ready on `/sync/dashboard`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:19:41.161132Z`.
- S10 `/driver/ready`: ready on `/projects`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:18:47.159255Z`.

Checklist updates:

- Closed remote write proof under write-checkpoint semantics.
- Closed final local proof that acknowledged writes are visible after the
  server/pull path.
- Closed "Do not mark sync fresh until the local write is visible through the
  server/pull path."

Still open:

- Realtime hint fallback proof, crash/restart tests, domain-specific conflict
  strategy, file/storage/attachment expansion, role/RLS sweeps, and all P2/P3
  scale/staging/diagnostics/docs gates.

## 2026-04-18 - Crash/restart sync-engine coverage closed locally

What changed:

- Added a PullHandler path test proving a local-wins conflict inserts an
  unprocessed manual `change_log` update so the winning local row is re-pushed
  after pull.

Existing coverage verified and indexed for this checklist item:

- `local_sync_store_contract_test.dart`: stale `sync_control.pulling = '1'`
  is reset through `resetPullingFlag()`.
- `sync_run_state_store_test.dart`: crash recovery clears both advisory
  `sync_lock` and stale `pulling=1`.
- `sync_mutex_test.dart`: held-lock rejection, stale lock expiry, heartbeat
  expiry, clear-any-lock, release, and reacquire behavior.
- `pull_handler_test.dart`: keyset cursor advancement, page-two failure cursor
  preservation, stored full-page checkpoint restart, and partial-final-page
  replay after apply-time crash.
- `push_handler_test.dart`: 401 auth refresh success retries push and emits
  `SyncAuthRefreshed`; refresh failure leaves the row pending.
- `sync_background_retry_scheduler_test.dart`: background retry scheduling,
  cancel, no-session skip, DNS deferral/reschedule, retryable-result
  reschedule, and permanent-error stop.

Local evidence:

- `dart analyze test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/sync_run_state_store_test.dart test/features/sync/engine/sync_mutex_test.dart test/features/sync/application/sync_background_retry_scheduler_test.dart test/features/sync/engine/sync_engine_status_test.dart test/features/sync/engine/push_handler_test.dart test/features/sync/engine/sync_write_checkpoint_proof_test.dart lib/features/sync/engine/pull_handler.dart lib/features/sync/application/sync_background_retry_scheduler.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/pull_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/sync_run_state_store_test.dart test/features/sync/engine/sync_mutex_test.dart test/features/sync/application/sync_background_retry_scheduler_test.dart test/features/sync/engine/sync_engine_status_test.dart test/features/sync/engine/push_handler_test.dart test/features/sync/engine/sync_write_checkpoint_proof_test.dart -r expanded`
  passed 117 tests.
- `git diff --check` passed with line-ending warnings only.

Device hygiene after proof:

- S21 `/driver/ready`: ready on `/sync/dashboard`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:19:41.161132Z`.
- S10 `/driver/ready`: ready on `/projects`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:18:47.159255Z`.

Checklist updates:

- Closed the crash/restart tests item under P1 Sync Engine Correctness
  Hardening, including `pulling=1`, held `sync_lock`, cursor update/restart,
  manual conflict re-push insertion, auth refresh, and background retry
  scheduling.

Still open:

- Realtime hint fallback proof, domain-specific conflict strategy,
  file/storage/attachment expansion, role/RLS sweeps, and all P2/P3
  scale/staging/diagnostics/docs gates.

## 2026-04-18 - Realtime hints proved advisory locally

What changed:

- Added realtime-handler tests proving duplicate realtime broadcasts are
  idempotent dirty scopes: the second duplicate is throttled, but the dirty
  marker remains for the next quick pull.
- Added realtime-handler tests proving out-of-order realtime broadcasts retain
  both dirty scopes even when the second hint is throttled.
- Added realtime-handler coverage proving cross-company realtime hints do not
  dirty scopes or trigger sync.

Existing coverage verified and indexed for this checklist item:

- Failed realtime registration starts fallback polling quick syncs, covering
  missed realtime hints.
- Hints that arrive while a sync is running are queued and trigger a follow-up
  quick sync after the in-flight sync completes, covering delayed hints.
- FCM foreground hints mark dirty scopes before sync, and throttled FCM hints
  still retain dirty scopes.
- FCM background hints persist a pending flag and bounded payload queue so
  resume can consume the missed hint and stay on the quick-sync path.
- Cross-company FCM hints are rejected before they mark dirty scopes or consume
  throttle windows.
- Scope revocation cleaner tests prove revoked project scope is fully evicted
  locally, including shell rows and local files.

Local evidence:

- `dart analyze test/features/sync/application/realtime_hint_handler_test.dart test/features/sync/application/fcm_handler_test.dart test/features/sync/application/sync_lifecycle_manager_test.dart test/features/sync/engine/dirty_scope_tracker_test.dart test/features/sync/engine/pull_scope_state_test.dart test/features/sync/engine/scope_revocation_cleaner_test.dart lib/features/sync/application/realtime_hint_handler.dart lib/features/sync/application/realtime_hint_transport_controller.dart lib/features/sync/engine/dirty_scope_tracker.dart`
  passed with no issues.
- `flutter test test/features/sync/application/realtime_hint_handler_test.dart test/features/sync/application/fcm_handler_test.dart test/features/sync/application/sync_lifecycle_manager_test.dart test/features/sync/engine/dirty_scope_tracker_test.dart test/features/sync/engine/pull_scope_state_test.dart test/features/sync/engine/scope_revocation_cleaner_test.dart -r expanded`
  passed 60 tests.
- `git diff --check` passed with line-ending warnings only.

Device hygiene after proof:

- S21 `/driver/ready`: ready on `/sync/dashboard`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:19:41.161132Z`.
- S10 `/driver/ready`: ready on `/projects`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:18:47.159255Z`.

Checklist updates:

- Closed the realtime hints item under P1 Sync Engine Correctness Hardening:
  missed, delayed, duplicate, out-of-order, fallback polling convergence, and
  revocation/no-unauthorized-scope local proof are now covered.

Still open:

- Domain-specific conflict strategy, file/storage/attachment expansion,
  role/RLS sweeps, and all P2/P3 scale/staging/diagnostics/docs gates.

## 2026-04-18 - Domain-specific conflict strategy closed locally

What changed:

- Refactored `ConflictResolver` so deterministic LWW remains the default
  winner selection, with narrow domain preservation hooks for signed and
  audit-sensitive rows.
- Added signed-form preservation: a locally signed `form_responses` row with a
  `signature_audit_id` is kept over a newer unsigned pulled row.
- Added signature file preservation: immutable fingerprint fields
  (`sha256`, size, mime type, creator, create time, project/company ids) keep
  the local row when a full pulled row disagrees.
- Kept signature file `remote_path` propagation LWW when immutable fingerprint
  fields match, so remote upload metadata still flows back to the device.
- Added signature audit preservation: immutable audit-chain fields keep the
  local row when a full pulled row disagrees.
- Left quantities and narrative records on LWW, with changed-column
  `conflict_log` diffs as the documented preservation mechanism for discarded
  quantities, notes, and narrative text.
- Guarded preservation rules from sparse push-skip audit rows so the
  `LwwChecker` server-timestamp path still logs and behaves as LWW.

Local evidence:

- `dart analyze lib/features/sync/engine/conflict_resolver.dart test/features/sync/engine/conflict_resolver_domain_policy_test.dart test/features/sync/engine/conflict_clock_skew_test.dart test/features/sync/property/sync_invariants_property_test.dart test/features/sync/engine/sync_engine_lww_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/conflict_resolver_domain_policy_test.dart test/features/sync/engine/conflict_clock_skew_test.dart test/features/sync/property/sync_invariants_property_test.dart test/features/sync/engine/sync_engine_lww_test.dart -r expanded`
  passed 24 tests.
- `git diff --check` passed with line-ending warnings only.

Device hygiene after proof:

- S21 `/driver/ready`: ready on `/sync/dashboard`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:19:41.161132Z`.
- S10 `/driver/ready`: ready on `/projects`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:18:47.159255Z`.

Checklist updates:

- Closed the domain-specific conflict strategy item under P1 Sync Engine
  Correctness Hardening.

Still open:

- File/storage/attachment expansion, role/RLS sweeps, and all P2/P3
  scale/staging/diagnostics/docs gates.

## 2026-04-18 - File/attachment durable phase evidence added locally

What changed:

- Added `file_sync_state_log` as a local diagnostic table for durable
  file-backed sync phase evidence. This is not a second production sync queue;
  `change_log` and row `remote_path` remain the sync truth.
- Bumped the local schema to v62 and wired the new table through fresh
  bootstrap, upgrade migration, schema metadata, and SQLite test helpers.
- Added `FileSyncStateStore` and wired `FileSyncHandler` /
  `FileSyncThreePhaseWorkflow` to record:
  upload started/succeeded/failed, row upsert succeeded/failed, local bookmark
  succeeded/failed, stale object cleanup succeeded/queued.
- Changed stale remote-object cleanup after file replacement so a removal
  failure now queues `storage_cleanup_queue` with bucket and remote path
  instead of only logging a possible leak.
- Wired `StorageCleanup` to record cleanup retry success/failure state events.
- Added `signature_files` / `signatures` to storage cleanup and orphan-scan
  registries.
- Ran PowerSync attachment-helper triage. Current docs mark the old Dart
  `powersync_attachments_helper` package deprecated and recommend built-in SDK
  attachment helpers. Direct adoption is not a release fit because it couples
  to the PowerSync database/queue substrate; the reusable pattern is local-only
  attachment state, explicit queue states, retry/cleanup, and verification,
  which is now being ported into the existing Field Guide sync engine.

Local evidence:

- `dart analyze lib/core/database/schema/sync_engine_tables.dart lib/core/database/database_bootstrap.dart lib/core/database/database_late_migration_steps.dart lib/core/database/database_service.dart lib/core/database/database_schema_metadata.dart lib/features/sync/application/sync_engine_factory.dart lib/features/sync/engine/file_sync_handler.dart lib/features/sync/engine/file_sync_state_store.dart lib/features/sync/engine/file_sync_three_phase_workflow.dart lib/features/sync/engine/storage_cleanup.dart lib/features/sync/engine/storage_cleanup_registry.dart lib/features/sync/engine/orphan_scanner.dart test/helpers/sync/sqlite_test_helper.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/adapters/adapter_config_test.dart test/features/sync/engine/orphan_scanner_test.dart -r expanded`
  passed 102 tests.
- `git diff --check` passed with line-ending warnings only.

Device hygiene after proof:

- S21 `/driver/ready`: ready on `/sync/dashboard`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:19:41.161132Z`.
- S10 `/driver/ready`: ready on `/projects`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:18:47.159255Z`.

Checklist updates:

- Closed the durable attachment/file state subitem under P1 File, Storage, And
  Attachment Hardening.
- Closed the PowerSync attachment-helper triage subitem with a pattern-port
  decision and direct-adoption rejection for this release.

Still open:

- Broader storage object proof beyond photos/signatures, unauthorized storage
  access denial proof, cross-device download/preview proof, remaining
  crash/retry cases, role/RLS sweeps, and all P2/P3 scale/staging/diagnostics
  docs gates.

## 2026-04-18 - File-backed row/object adapter contract covered locally

What changed:

- Added registry-level contract coverage for every file-backed adapter:
  `photos`, `documents`, `entry_exports`, `form_exports`,
  `export_artifacts`, and `signature_files`.
- The contract asserts each file-backed family declares its bucket, local path
  column, local-only path stripping, storage cleanup registry mapping, and a
  valid generated storage path.
- The contract also asserts local-only export history adapters still skip both
  pull and push, keeping `entry_exports`, `form_exports`, and
  `export_artifacts` out of remote sync truth.
- The test exposed that the generalized storage path validator rejected the
  actual nested `export_artifacts` path shape. Updated validation to allow
  nested safe directory prefixes while preserving extension allowlists.

Local evidence:

- `dart analyze lib/features/sync/engine/file_sync_three_phase_workflow.dart test/features/sync/engine/adapter_integration_test.dart lib/features/sync/engine/storage_cleanup_registry.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/adapter_integration_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/adapters/adapter_config_test.dart test/features/sync/engine/orphan_scanner_test.dart -r expanded`
  passed 133 tests.

Checklist updates:

- Closed the local row/object consistency contract test subitem for
  file-backed families.

Still open:

- Device/remote storage object proof beyond photos/signatures, unauthorized
  storage access denial proof, cross-device download/preview proof, remaining
  crash/retry cases, role/RLS sweeps, and all P2/P3 scale/staging/diagnostics
  docs gates.

## 2026-04-18 - Stale file cache and storage-family artifact diagnostics

What changed:

- Added stale local file cache invalidation coverage for file-backed pull
  changes:
  - remote path changes delete the stale local file and clear the local path;
  - remote deletes remove the local cached file and clear the local path;
  - unchanged remote paths preserve the local file.
- Added `storage-family-diagnostics.json` and matching summary fields to the
  post-sync reconciliation gate. The artifact now records which storage
  families require remote object proof and which families are local-only
  byte/history proof under the current adapter contract.
- Classified photos, signatures, and entry documents as remote-object proof
  families.
- Classified `entry_exports`, `form_exports`, `export_artifacts`, and
  pay-application exports as local-only byte/history families while the
  adapters remain `skipPush`/`skipPull`.
- Added `Assert-SoakStorageUnauthorizedDenied` and a pure response classifier
  so live flows can prove unauthorized bucket/path access denial against
  proven-present objects without broad auth/RLS inference.

Local evidence:

- `dart analyze lib/features/sync/engine/stale_file_cache_invalidator.dart test/features/sync/engine/stale_file_cache_invalidator_test.dart`
  passed with no issues.
- `flutter test test/features/sync/engine/stale_file_cache_invalidator_test.dart -r expanded`
  passed 3 tests.
- `flutter test test/features/sync/engine/stale_file_cache_invalidator_test.dart test/features/sync/engine/adapter_integration_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/adapters/adapter_config_test.dart test/features/sync/engine/orphan_scanner_test.dart -r expanded`
  passed 138 tests.
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` passed 11 test
  files after the storage diagnostics and denial-proof helper changes.
- `git diff --check` passed with line-ending warnings only.

Device hygiene after proof:

- S21 `/driver/ready`: ready on `/sync/dashboard`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`.
- S10 `/driver/ready`: ready on `/projects`; `/driver/change-log`: `count=0`,
  `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`.

Checklist updates:

- Closed the Slice J stale local cache invalidation subitem.
- Closed the Slice J decision on local-only export artifact diagnostics by
  adding explicit soak artifact fields.
- Left unauthorized storage access denial proof open until live flow artifacts
  exercise the helper per proven-present bucket/path family.

Still open:

- Live storage object proof beyond photos/signatures for synced families,
  live unauthorized storage denial proof, cross-device download/preview proof,
  remaining file crash/retry cases, role/RLS sweeps, and all P2 scale,
  staging, diagnostics, and docs gates.

## 2026-04-18 - File-sync crash/retry matrix closed locally

What changed:

- Tightened `LocalRecordStore.bookmarkRemotePath()` so phase 3 now throws a
  `StateError` if the local row update affects zero rows.
- Added local-store contract coverage proving the missing bookmark target
  fails and trigger suppression is restored to `pulling=0`.
- Added file-sync workflow coverage for a remote row-upsert success followed
  by a missing local bookmark target. The workflow now records
  `local_bookmark_failed`, emits the phase-3 failure, and does not treat the
  file push as successful.
- Added bookmark-completed replay coverage for the crash window after local
  bookmark but before `change_log` processing. The replay starts with
  `remote_path` already bookmarked and the queue row still unprocessed, skips
  duplicate upload, re-upserts/bookmarks idempotently, creates no extra
  `change_log`, and drains when the original change is marked processed.

Why:

- The crash/retry checklist required proof around the window after row upsert
  but before local bookmark. Before this change, an unexpected zero-row local
  bookmark update could be silently accepted, which would weaken the per-file
  row/object consistency proof.

Local evidence:

- `dart analyze lib/features/sync/engine/local_record_store.dart test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/file_sync_handler_test.dart`
  passed with no issues.
- Initial targeted Flutter run correctly failed while the zero-row check was
  accidentally placed on server-timestamp writeback instead of
  `bookmarkRemotePath()`. The test failure confirmed the phase-3 gap and was
  fixed before acceptance.
- `flutter test test/features/sync/engine/local_sync_store_contract_test.dart test/features/sync/engine/file_sync_handler_test.dart -r expanded`
  passed 58 tests.
- `flutter test test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/local_sync_store_contract_test.dart -r expanded`
  passed 59 tests after adding the bookmark-before-`change_log`-processed
  replay proof.
- Broader file/storage regression sweep passed:
  `flutter test test/features/sync/engine/stale_file_cache_invalidator_test.dart test/features/sync/engine/adapter_integration_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/adapters/adapter_config_test.dart test/features/sync/engine/orphan_scanner_test.dart test/features/sync/engine/local_sync_store_contract_test.dart -r expanded`
  passed 172 tests.
- Final broader file/storage sweep after adding the
  bookmark-before-`change_log` proof passed:
  `flutter test test/features/sync/engine/stale_file_cache_invalidator_test.dart test/features/sync/engine/adapter_integration_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/adapters/adapter_config_test.dart test/features/sync/engine/orphan_scanner_test.dart test/features/sync/engine/local_sync_store_contract_test.dart -r expanded`
  passed 173 tests.
- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` passed 11 test
  files.
- `git diff --check` passed with line-ending warnings only.

Device hygiene after proof:

- S21 `/driver/change-log`: `count=0`, `unprocessedCount=0`,
  `blockedCount=0`, `maxRetryCount=0`.
- S10 `/driver/change-log`: `count=0`, `unprocessedCount=0`,
  `blockedCount=0`, `maxRetryCount=0`.
- Final device hygiene after the 173-test sweep: S21 ready on
  `/sync/dashboard`, S10 ready on `/projects`, both `/driver/change-log`
  responses had `count=0`, `unprocessedCount=0`, `blockedCount=0`, and
  `maxRetryCount=0`.

Checklist updates:

- Marked file crash/retry coverage done for:
  - after upload before row upsert;
  - after row upsert before bookmark;
  - after bookmark before `change_log` processed;
  - after storage delete failure before cleanup retry.
- Closed the file crash/retry parent under P1 File, Storage, And Attachment
  Hardening.

Still open:

- Live storage object proof beyond photos/signatures, live unauthorized
  storage denial proof, cross-device download/preview proof, role/RLS sweeps,
  and P2 scale/staging/diagnostics/docs gates.

## 2026-04-18 - File-backed replay matrix broadened locally

What changed:

- Added document coverage through the real `DocumentAdapter`: local file upload,
  metadata upsert, local `remote_path` bookmark, and durable phase-state log.
- Added signature file replay coverage through the registered
  `signature_files` adapter: an existing `remote_path` with absent
  `local_path` skips upload and replays metadata/bookmark idempotently.
- Existing photo coverage continues to prove duplicate upload replay, storage
  409, row-upsert replay with existing `remote_path`, missing local file with
  existing `remote_path`, upload timeout, and phase-2 cleanup.
- Existing export-artifact coverage proves `local_path` handling, storage path
  changes, stale remote removal, and stale cleanup retry queueing.

Local evidence:

- `dart analyze test/features/sync/engine/file_sync_handler_test.dart` passed
  with no issues.
- `flutter test test/features/sync/engine/file_sync_handler_test.dart -r expanded`
  passed 24 tests.
- `flutter test test/features/sync/engine/adapter_integration_test.dart test/features/sync/engine/file_sync_handler_test.dart test/features/sync/engine/storage_cleanup_test.dart test/features/sync/schema/sync_schema_test.dart test/features/sync/adapters/adapter_config_test.dart test/features/sync/engine/orphan_scanner_test.dart -r expanded`
  passed 135 tests.
- `git diff --check` passed with line-ending warnings only.

Device hygiene after proof:

- S21 `/driver/ready`: ready on `/sync/dashboard`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:19:41.161132Z`.
- S10 `/driver/ready`: ready on `/projects`; `/driver/change-log`:
  `count=0`, `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status`: `isSyncing=false`, `pendingCount=0`,
  `blockedCount=0`, `unprocessedCount=0`,
  `lastSyncTime=2026-04-19T00:18:47.159255Z`.

Checklist updates:

- Closed the local upload replay / metadata replay / storage 409 /
  missing-object recovery subitem for photos, documents, signature files, and
  export artifacts.

Still open:

- Device/remote storage object proof beyond photos/signatures, unauthorized
  storage access denial proof, cross-device download/preview proof, remaining
  crash/retry cases, role/RLS sweeps, and all P2/P3 scale/staging/diagnostics
  docs gates.

## 2026-04-18 - Entry-document live storage proof accepted

What changed:

- Added the `documents-only` refactored soak flow and wired it through the
  module loader, dispatcher, lab entrypoints, concurrent soak entrypoint, and
  harness self-tests.
- Wired production entry-document creation for device proof by letting
  `DocumentService.attachDocument()` consume injected driver files before the
  native picker for supported document extensions.
- Added document UI testing keys and screen-contract actions for the
  report-entry document subsection.
- Added document local download/cache support through `SyncFileAccessService`,
  `ManageDocumentsUseCase`, `DocumentProvider`, and
  `EntryDocumentsSubsection`, with trigger-suppressed local cache path writes.
- Extended `/driver/local-file-head` to read document local paths for later
  local/cross-device visibility proof.
- Tightened the storage unauthorized-denial classifier so private bucket
  responses of HTTP 400 with `Bucket not found` are accepted only when the
  caller opts into `-TreatNotFoundAsDenied`.

Why:

- The P1 file/storage lane still needed a synced non-photo/non-signature object
  family proven end-to-end. Entry documents are a remote-object family under
  the current adapter contract, unlike local-only export history tables.
- The first live run proved the row/object path but exposed a too-narrow
  denial classifier for Supabase private buckets. The fix keeps the proof
  fail-closed on successful downloads while accepting the expected hidden
  bucket response from invalid credentials.

Local evidence:

- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` passed 11 test
  files after adding the hidden-bucket classifier case.
- Earlier focused gates for the document flow were already green in this
  slice:
  - `dart analyze` on touched document service/provider/repository/driver
    route files and tests passed with no issues.
  - `flutter test test/services/document_service_test.dart test/features/forms/presentation/providers/document_provider_test.dart test/features/entries/presentation/widgets/entry_forms_section_test.dart test/core/driver/driver_data_sync_routes_test.dart test/core/driver/driver_data_sync_handler_test.dart -r expanded`
    passed 28 tests.
  - `git diff --check` passed with line-ending warnings only.

Live device evidence:

- Preflight before the accepted rerun:
  S21 `/driver/ready` ready on `/sync/dashboard`; `/driver/change-log` empty
  with `unprocessedCount=0`, `blockedCount=0`, `maxRetryCount=0`;
  `/driver/sync-status` idle with `pendingCount=0`, `blockedCount=0`,
  `unprocessedCount=0`.
- Diagnostic first run:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-documents-entry-object-proof-initial/`
  failed only at unauthorized-denial classification. It still proved local
  document mutation, pre-sync `change_log`, UI-triggered sync, remote row,
  authorized storage bytes/hash, cleanup sync, storage delete/absence, empty
  queues, zero runtime/logging gaps, and no direct driver sync.
- Accepted rerun:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-documents-entry-object-proof-after-denial-classifier/`
  passed with `queueDrainResult=drained`, `failedActorRounds=0`,
  `runtimeErrors=0`, `loggingGaps=0`, `blockedRowCount=0`,
  `unprocessedRowCount=0`, `maxRetryCount=0`, and
  `directDriverSyncEndpointUsed=false`.
- Accepted row/object proof:
  `documents/b4efc514-b14f-41e4-a257-b5ef0989ed5a`, entry
  `f14d87c1-d870-444e-ba2b-bca5762aa485`, remote path
  `docs/26fe92cd-7044-4412-9a09-5c5f49a292f9/f14d87c1-d870-444e-ba2b-bca5762aa485/enterprise_soak_doc_S21_round_1_214458.pdf`,
  bucket `entry-documents`, 48 bytes, SHA-256
  `d7aacd14db7ca489d86ca71c834ac5513f54cbfbab168d7929c086b6a7e61dc6`.
- Unauthorized proof for the same bucket/path passed with HTTP 400
  `Bucket not found` under `-TreatNotFoundAsDenied`.
- Cleanup proof passed: ledger-owned soft delete, UI-triggered cleanup sync,
  storage delete, and storage absence.

Checklist updates:

- Checked off entry-document object proof in the live task list and recorded
  the accepted artifact in the controlling todo.
- Marked entry-document unauthorized-denial live proof complete, while leaving
  the broader bucket/path-family denial parent open until photo/signature
  accepted flows are rerun with the new denial helper and cross-device
  download/preview is proven.

Still open:

- Rerun live photo/signature bucket-path families with the denial helper.
- Prove cross-device download/preview of uploaded objects.
- Role/RLS sweeps and all P2 scale/staging/diagnostics/docs gates remain open.

## 2026-04-18 - Remote object denial and cross-device document download accepted

What changed:

- Added `documents-cross-device-only`, a two-actor refactored flow that:
  creates an entry document on the source actor;
  syncs the source through the Sync Dashboard;
  proves the remote row, storage object, and unauthorized denial;
  syncs the receiver through the Sync Dashboard;
  opens the pulled document tile on the receiver to force download/cache;
  proves receiver local bytes with `/driver/local-file-head`;
  performs source ledger cleanup;
  syncs the receiver cleanup pull; and
  verifies receiver soft-delete visibility.
- Wired the flow through `tools/enterprise-sync-soak-lab.ps1`,
  `tools/enterprise-sync-concurrent-soak.ps1`,
  `tools/sync-soak/DeviceLab.RefactoredDispatcher.ps1`,
  `tools/sync-soak/ModuleLoader.ps1`, and `FlowWiring.Tests.ps1`.
- Reused the document creation/download app changes from the prior slice and
  rebuilt S10 so the receiver had the document download/cache path.

Local evidence:

- `pwsh -NoProfile -File tools/test-sync-soak-harness.ps1` passed 11 test
  files after adding `documents-cross-device-only` wiring and assertions.

Device setup and recovery notes:

- S21 `photo-only` and `mdot1126-signature-only` were rerun after the denial
  helper was wired.
- S10 rebuild removed the S21 host forward; S21 was rebuilt/restarted on port
  4948 and S10's port 4949/debug reverse were restored.
- S10 had three unprocessed signature cleanup rows after observing the S21
  signature cleanup. `20260418-s10-post-signature-denial-residue-sync-only`
  drained those rows through the Sync Dashboard before cross-device proof.
- Final cross-device preflight showed S21 and S10 both idle with empty
  `change_log`, `pendingCount=0`, `blockedCount=0`, and
  `unprocessedCount=0`.

Accepted live evidence:

- Photo remote-object denial:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-photo-storage-denial-proof/`
  passed with `photos/799779ce-b41f-4ea0-bea2-f92e72bc14ed`, bucket
  `entry-photos`, remote path
  `entries/26fe92cd-7044-4412-9a09-5c5f49a292f9/f14d87c1-d870-444e-ba2b-bca5762aa485/enterprise_soak_S21_round_1_214730.jpg`,
  authorized object 68 bytes, SHA-256
  `1dae93d61eceabd7ce356b2be0acf0d2b813bf595f5cbae775a88582fd4ad278`,
  and unauthorized HTTP 400 `Bucket not found` for the same path.
- Signature remote-object denial:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-storage-denial-proof/`
  passed with `signature_files/a5d373fd-4096-4ea5-8406-476db56196f0`,
  bucket `signatures`, remote path
  `signatures/26fe92cd-7044-4412-9a09-5c5f49a292f9/75ae3283-d4b2-4035-ba2f-7b4adb018199/a5d373fd-4096-4ea5-8406-476db56196f0.png`,
  authorized object 5193 bytes, SHA-256
  `95c0ab2bfc32859719ec0de97ebaf4710e2dfb605fc5751cd54e90a398912755`,
  and unauthorized HTTP 400 `Bucket not found` for the same path.
- S10 residue drain:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-post-signature-denial-residue-sync-only/`
  passed with final clean queue.
- Cross-device document download:
  `.claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-s10-documents-cross-device-download-proof/`
  passed with `queueDrainResult=drained`, `failedActorRounds=0`,
  `runtimeErrors=0`, `loggingGaps=0`, `blockedRowCount=0`,
  `unprocessedRowCount=0`, `maxRetryCount=0`,
  `directDriverSyncEndpointUsed=false`, and final clean queues on both
  actors.
- Cross-device row/object details:
  `documents/b8f80b06-9e14-4ff4-9e38-0be0e7cbf8f1`, remote path
  `docs/26fe92cd-7044-4412-9a09-5c5f49a292f9/f14d87c1-d870-444e-ba2b-bca5762aa485/enterprise_soak_cross_device_doc_S21_to_S10_round_1_215611.pdf`,
  bucket `entry-documents`, authorized object 48 bytes, SHA-256
  `d7aacd14db7ca489d86ca71c834ac5513f54cbfbab168d7929c086b6a7e61dc6`,
  and unauthorized HTTP 400 `Bucket not found`.
- Receiver proof:
  S10 pulled the row through UI sync, tapped
  `document_tile_b8f80b06-9e14-4ff4-9e38-0be0e7cbf8f1`,
  `/driver/local-file-head?table=documents&id=b8f80b06-9e14-4ff4-9e38-0be0e7cbf8f1&sha256=true`
  returned `exists=true`, 48 bytes, and the same SHA-256 as storage, then S10
  pulled the cleanup and observed `deleted_at`.

Checklist updates:

- Closed live unauthorized denial proof for all applicable remote-object
  families: photos, signatures, and entry documents.
- Closed cross-device download/preview proof for uploaded objects with the
  S21-to-S10 entry-document artifact.
- Closed the broader file/storage object-proof item under the current adapter
  contract: photos/signatures/documents are remote-object families; export and
  pay-app artifact families are local-only byte/history families with accepted
  local proof and diagnostics, not remote object families.

Still open:

- P1 Role/Scope/Account/RLS sweeps.
- P2 reuse triage, Jepsen-style workload/history/checkers, failure injection
  and liveness, backend/device overlap, staging gates, 15-20 actor scale,
  diagnostics/alerts, consistency contract docs, and final green-streak gates.

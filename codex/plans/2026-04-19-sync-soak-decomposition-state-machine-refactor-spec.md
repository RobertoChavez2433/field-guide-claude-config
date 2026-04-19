# Sync Soak Decomposition + State Machine Refactor Todo Spec (Comprehensive)

Date: 2026-04-19
Branch: `gocr-integration`
Supersedes as working copy: `.codex/plans/2026-04-19-sync-soak-driver-decomposition-todo-spec.md`
Append implementation notes to:
`.codex/checkpoints/2026-04-19-sync-soak-decomposition-state-machine-progress.md`
(new — create on first slice).

## Purpose

This spec is the singular comprehensive to-do list for two interlocked
hardening tracks on the sync-soak + device-runner systems:

1. **Structural decomposition track** — inherited verbatim (with sequencing
   adjustments) from the 2026-04-19 driver-decomposition spec. Breaks up
   `SoakDriver.run`, relocates `harness_seed_data.dart`, extracts
   auth/project diagnostics builders, strategy-maps action dispatchers,
   route-tables the driver-data-sync handler, and lands a shared
   `SoakActorProvisioner`. Structural debt only; no new acceptance
   semantics.
2. **State machine refactor track** (NEW) — standardizes the key taxonomy
   so sentinels are the primary state contract, adds a canonical
   `DeviceStateSnapshot` aggregating UI / app / data / sync state per
   device, makes sentinels pervasive with deadline-budget assertions,
   lands an orchestrator state machine for cross-device invariants,
   closes the `SyncStatus.undismissedConflictCount` gap that makes the
   existing `Assert-SoakNoUndismissedConflictsSentinel` dead code, and
   produces one unified cross-device timeline as evidence.

The two tracks are blended here because the state machine work cannot
land cleanly on top of the current god-shaped driver surface
(`driver_diagnostics_handler._handleActorContext` at cyclomatic 42 is
exactly the place a new aggregated snapshot endpoint needs to live), and
the decomposition lanes benefit from the state-machine track's
measurable acceptance criteria (schema contracts, fail-loud rules) as
their regression fence.

The predecessor 2026-04-18 decomposition closed P0/P1 (`.claude/codex/plans/2026-04-18-sync-soak-decomposition-todo-spec.md`),
splitting `tools/enterprise-sync-soak-lab.ps1` into a 144-line facade,
pulling out FlowRuntime / MutationTargets / ChangeLogAssertions /
MutationLedger / CleanupDispatch / StorageProof / FormFlow / FormMarkers /
JsonWriter / FailureClassification / ArtifactWriter, and reducing
`integration_test/sync/soak/soak_driver.dart` from 998 lines to a 56-line
library facade with 7 part files. P2 and P3 lanes from that spec were
deferred; this spec picks them up alongside the new state-machine work.

Primary hardening tracker remains:
`.codex/plans/2026-04-18-sync-soak-unified-hardening-todo.md`

Related codebase hygiene tracker (do not overlap):
`.codex/plans/2026-04-19-codebase-hygiene-refactor-todo-spec.md`

## Guardrails

Inherit everything in `.claude/codex/plans/2026-04-18-sync-soak-decomposition-todo-spec.md`,
plus the follow-on guardrails below. State-machine additions are marked
`(STATE MACHINE)`.

- [ ] Do not change acceptance semantics while decomposing.
- [ ] Do not call `POST /driver/sync` for acceptance paths; UI-triggered sync
  remains the accepted device-sync path.
- [ ] Do not use `MOCK_AUTH`; every auth/sync proof stays on real sessions and
  real backend state.
- [ ] Keep backend/RLS soak evidence separate from device-sync evidence, and
  keep headless-app-sync evidence separate from both.
- [ ] Every slice must pass `tools/test-sync-soak-harness.ps1` and
  `dart analyze integration_test test/harness`.
- [ ] Every slice that touches a live accepted flow must rerun the narrowest
  accepted S21 gate or record why a doc-only/plumbing-only slice did not
  require a device run.
- [ ] Do not add test-only methods or lifecycle hooks to production classes.
  Driver-server endpoints stay production-like; soak-only state lives in
  integration_test/ or in driver modules that are only dot-sourced by the
  driver.
- [ ] Do not bypass the `SyncCoordinator`-as-sync-entrypoint rule in any
  production path. The headless-app-sync executor's direct
  `SyncEngineFactory().create()` is an intentional test seam for
  engine-in-isolation testing and stays scoped to `integration_test/`.
- [ ] Do not reintroduce `sync_status` columns or indexes.
- [ ] `change_log` remains trigger-owned; no manual inserts from soak code.
- [ ] Do not weaken existing custom lint rules, widen allowlists, or add
  `// ignore:` comments to make a decomposition slice pass.
- [ ] Do not let this spec delete the `.codex/plans/2026-04-18-*` spec's
  exception file; extend the exception file with any new budgets needed.
- [ ] **(STATE MACHINE)** `SyncStatus` remains the single source of truth
  for transport state. New fields are additive; existing consumers stay
  green without signature changes.
- [ ] **(STATE MACHINE)** No test-only hooks grow on production classes.
  New observability is exposed only through driver HTTP seams and
  structured logs.
- [ ] **(STATE MACHINE)** The canonical `DeviceStateSnapshot` is a
  read-only aggregation; it does not introduce new state, new mutable
  fields, or new cross-module dependencies.
- [ ] **(STATE MACHINE)** No Riverpod, no second state-management system,
  no runtime statechart library. Orthogonal regions are expressed in the
  snapshot shape, not in a runtime machine.
- [ ] **(STATE MACHINE)** No network protocol change. All coordination
  remains over the existing driver HTTP endpoints + PowerShell harness.
- [ ] **(STATE MACHINE)** Typed-key catalog migration is feature-by-
  feature; each cut-over PR preserves existing `TestingKeys.*` call
  sites via generated re-exports until the feature module is fully
  migrated.

## Audit Baseline

Measured on branch `gocr-integration`, 2026-04-19 after re-index.

### App-side driver layer (`lib/core/driver/`)

| File | Lines | Symbol shape | Status |
|---|---:|---|---|
| `screen_contract_registry.dart` | 719 | 1 class, registry-shaped | oversized |
| `harness_seed_data.dart` | 615 | 1 class, 9 feature-datasource imports, 10 feature-model imports | oversized + layering breach |
| `driver_diagnostics_handler.dart` | 611 | `_handleActorContext` c42 / 97 LOC — #20 hotspot repo-wide | oversized + hotspot |
| `driver_data_sync_handler_query_routes.dart` | 516 | part-style route file | oversized |
| `driver_interaction_handler_gesture_routes.dart` | 499 | part-style route file | oversized |
| `driver_data_sync_handler.dart` | 492 | dispatcher c20, 20+ private `_handle*` stubs | review |
| `driver_file_injection_handler.dart` | 451 | photo+doc+direct injection in one class | review |
| `screen_registry.dart` | 354 | cross-feature registry | review |
| `driver_widget_inspector.dart` | 329 | widget-tree scraping surface | review |
| `driver_server.dart` | 203 | 12+ nullable deps "for backward compat" | review |

### Dart soak layer (`integration_test/sync/soak/`)

| File | Lines | Symbol shape | Status |
|---|---:|---|---|
| `headless_app_sync_action_executor.dart` | 592 | 1 executor (~550) + `_HeadlessAppSyncActor` inner class | oversized |
| `backend_rls_soak_action_executor.dart` | 374 | `execute` dispatcher c24 / 147 LOC | review |
| `soak_runner.dart` | 325 | `SoakDriver.run` c30 / nesting 8 / 204 LOC | oversized + hotspot |
| `soak_metrics_collector.dart` | 281 | review |
| `soak_models.dart` | 129 | ok |
| `soak_action_mix.dart` | 84 | ok |
| `soak_personas.dart` | 80 | ok |
| `driver_soak_action_executor.dart` | 75 | ok |
| `soak_driver.dart` | 56 | library facade | ok |
| `soak_executors.dart` | 17 | ok |

### Hotspot cross-check (re-index 2026-04-19, 60-day churn window)

- `_handleActorContext` at `lib/core/driver/driver_diagnostics_handler.dart:326`
  — cyclomatic 42, nesting 4, param_count 1, churn 8, hotspot score 92.28,
  **#20 on the repo-wide hotspot list**. Only driver/soak-surface method
  in the top 25.
- `SoakDriver.run` at `integration_test/sync/soak/soak_runner.dart:116` —
  cyclomatic 30, nesting 8, body 204 lines. Not in top 25 because the file
  is new and has low churn yet; structural shape is still above the Dart
  budget.
- `LocalSupabaseSoakActionExecutor.execute` at
  `integration_test/sync/soak/backend_rls_soak_action_executor.dart:35` —
  cyclomatic 24, nesting 4, body 147 lines. Long-switch smell on
  `SoakActionKind`.
- `DriverDataSyncHandler.handle` at
  `lib/core/driver/driver_data_sync_handler.dart:48` — cyclomatic 20,
  nesting 2, 47-line dispatcher body; 20 `_handle*` stubs delegated. The
  2026-04-18 spec already extracted `*_query_routes`, `*_mutation_routes`,
  `*_maintenance_routes` part files; the dispatcher itself has not been
  migrated to a route table.

### Verified layering breach

`lib/core/driver/harness_seed_data.dart` reaches directly into:

- `lib/features/auth/data/datasources/local/user_profile_local_datasource.dart`
- `lib/features/contractors/data/datasources/local/contractor_local_datasource.dart`
- `lib/features/contractors/data/datasources/local/personnel_type_local_datasource.dart`
- `lib/features/entries/data/datasources/local/daily_entry_local_datasource.dart`
- `lib/features/forms/data/datasources/local/form_response_local_datasource.dart`
- `lib/features/forms/data/datasources/local/inspector_form_local_datasource.dart`
- `lib/features/locations/data/datasources/local/location_local_datasource.dart`
- `lib/features/projects/data/datasources/local/project_local_datasource.dart`
- `lib/features/quantities/data/datasources/local/bid_item_local_datasource.dart`

Plus ~10 feature model imports. Callers, verified:

- `lib/core/driver/driver_seed_handler.dart` (`/driver/seed` HTTP endpoint).
- `lib/core/driver/screen_registry.dart` (driver-rendered screens).
- `lib/core/driver/flows/verification_flow_definitions.dart`.
- `test/core/driver/driver_seed_handler_test.dart`.
- `test/features/sync/application/sync_state_repair_runner_test.dart`.

Zero production callers. `lib/main.dart`, `lib/core/di/`, and `lib/core/router/`
do not depend on `HarnessSeedData`. Relocating under `integration_test/` is a
location-convention fix, not a functional change.

### State-machine baseline (NEW)

#### Existing assets — extend, do not replace

| Subsystem | File(s) | LOC | Why kept |
|---|---|---:|---|
| Event-sourced state transitions | `tools/sync-soak/StateMachine.ps1` | 149 | Per-actor counters, JSON persistence, pre/post sentinel hooks, recovery blocks — all correct |
| Sentinel assertion library | `tools/sync-soak/StateSentinels.ps1` | 286 | 8 typed assertion shapes; consistent `New-SoakSentinelResult` envelope; structured error JSON |
| Failure classification | `tools/sync-soak/FailureClassification.ps1` | 150 | 20+ categories; structured; drives `throw "[$classification] …"` contract |
| Evidence bundle | `tools/sync-soak/EvidenceBundle.ps1` | 122 | Logs + surface + widget tree + runtime-error fingerprints per prefix |
| Screen contract registry | `lib/core/driver/screen_contract_registry.dart` | 719 | Already couples each screen to its sentinel key + expected action/state keys |
| TestingKeys facade | `lib/shared/testing_keys/*.dart` | 17 files, ~2,500 | Feature-scoped, deterministic, parameterized where needed |
| SyncStatus single truth | `lib/features/sync/domain/sync_status.dart` | 214 | Immutable, `copyWith`, already the contract per `rules/sync/sync-patterns.md` |

#### Verified gaps

- **`Assert-SoakNoUndismissedConflictsSentinel` is dead code.** The
  sentinel at `tools/sync-soak/StateSentinels.ps1:95-121` checks for
  `SyncStatus.undismissedConflictCount`. Field is **absent** from
  `lib/features/sync/domain/sync_status.dart:32-73`. Today the assertion
  always fails on the `hasConflictField` check with error "Sync status
  does not expose undismissedConflictCount." If invoked on a live
  `SyncStatus` JSON, it fails; if invoked on an ad-hoc object that
  happens to expose the field (none today), it would pass trivially.
- **Key taxonomy is hand-maintained across 17 files.** ~2,500 LOC of
  constants in `lib/shared/testing_keys/*.dart`. PowerShell call sites
  reference matching string literals (`'sync_dashboard_screen'`,
  `'conflict_viewer_screen'`, …) with no compile-time link. A rename
  breaks the harness silently at runtime.
- **Sentinel coverage is partial.** Root-screen sentinels exist
  (`projectSetupScreen`, `syncDashboardScreen`, `loginScreen`, …) and
  three have unit-test coverage (`root_sentinel_project_widget_test.dart`,
  `root_sentinel_auth_widget_test.dart`, `root_sentinel_sync_widget_test.dart`).
  Remaining screens — most of `entries`, `forms`, `documents`, `pay_app`,
  `toolbox`, `support`, `settings` — have no sentinel test coverage.
- **GlobalKey usage spans 38 files.** Forms (`mdot_1126_form_screen.dart`,
  `mdot_hub_screen_widgets.dart`), entry editor
  (`entry_editor_body.dart`, `entry_editor_dialogs.dart`), project setup,
  calculator tabs, auth screens. A comment in
  `lib/core/driver/driver_keys.dart:6-7` documents a prior
  "duplicate-key assertions during route transitions on the live Android
  driver build" incident that forced a `ValueKey<String>` replacement at
  the app root. The pattern is not uniformly enforced.
- **No unified device-state snapshot endpoint.** Seven fine-grained
  `/diagnostics/*` endpoints (`/diagnostics/actor_context`,
  `/diagnostics/sync_transport`, `/diagnostics/sync_runtime`,
  `/diagnostics/screen_contract`, `/diagnostics/wizards`,
  `/diagnostics/observable_controllers`, `/diagnostics/theme`). The
  harness hits multiple endpoints to assemble a "where is this device"
  picture; there is no single atomic read.
- **No cross-device timeline.** Per-actor JSON artifacts are timestamped
  but never merged. Operators hand-correlate across 4 actor directories.
  `tools/sync-soak/Export-SoakResultIndex.ps1` aggregates summary
  statistics, not timelines.
- **Data state reporting is minimal.** Change-log blocked/unprocessed
  counts are exposed via `/driver/change-log`; there is no per-table row
  count, no DB-open/seeded flag, no last-local-write timestamp exposed
  from the device.
- **`loggingGaps` enforcement is inconsistent.** `FlowRuntime.ps1`
  throws on preflight logging gaps, but secondary gaps inside recovery
  blocks can mask the original failure; downstream flows can proceed.
- **Runtime errors are detected but not asserted.** `RuntimeErrorScanner`
  produces a fingerprint list per evidence bundle. No declarative rule
  engine says "any `GlobalKey duplicate` fingerprint is fatal"; it
  relies on flow-specific post-sentinels to notice.

## Target Shape

### At-scale test picture (inherited)

The at-scale sync tests run across three evidence layers. This spec's
decomposition protects the three-layer shape:

1. **Backend/RLS virtual actors** — drive Supabase directly via service-role
   and anon keys, prove RLS and project scope. Owner:
   `backend_rls_soak_action_executor.dart`.
2. **Device-sync actors** — real or emulator devices speaking HTTP to the
   driver-server; UI-triggered sync is the acceptance seam. Owner:
   `driver_soak_action_executor.dart` + `lib/core/driver/*`.
3. **Headless app-sync actors** — isolated SQLite + real `SyncEngine`,
   no device, no UI; prove engine-in-isolation correctness at scale.
   Owner: `headless_app_sync_action_executor.dart`.

A `SoakDriver` on top runs N actors concurrently with burst pacing and
periodic sampling. Each evidence layer preserves its own failure
classification, artifact shape, and pass/fail policy.

### Target component shape (decomposition)

- `SoakDriver` becomes a thin coordinator: resolve executor → build run
  state → delegate loop/pool/sampling → finalize `SoakResult`.
- `SoakWorkerPool` owns worker spin-up, burst-cycle pacing, and
  `await Future.wait(...)`.
- `SoakSampler` owns periodic metric capture (every N seconds).
- `SoakRunState` owns mutable counters, action maps, failures list,
  actor reports. No closure-captured mutation.
- `SoakFixtureRepair` owns the mutable-seed-row reset routine currently
  hiding inside `HeadlessAppSyncActionExecutor._repairMutableHarnessSeedState`.
- `_HeadlessAppSyncActor` becomes its own part file with documented scope.
- `HarnessSeedData`, `HarnessSeedDefaults`, `HarnessSeedPayAppData` move to
  `integration_test/sync/harness/seed/` alongside `harness_environment.dart`,
  `harness_fixture_cursor.dart`, `harness_auth.dart`, `harness_assertions.dart`,
  `harness_driver_client.dart`.
- `DriverDiagnosticsHandler._handleActorContext` splits into
  `_buildAuthDiagnostics` and `_buildProjectDiagnostics` sub-builders.
- `DriverDataSyncHandler.handle` becomes a route-table dispatcher instead
  of a 20-branch `if/else` chain.

### Target component shape (state machine — NEW)

- A canonical `lib/core/driver/device_state_snapshot.dart` value class
  aggregating four orthogonal regions (Harel statechart style —
  regions evolve independently, snapshot is a single atomic read):

  ```
  DeviceStateSnapshot {
    runId, actorId, capturedAtUtc, schemaVersion
    ui:   { currentRoute, sentinelKey, visibleModals[], loadingOverlays[], focusedField? }
    app:  { lifecycle, auth{userId,role,companyId,sessionValid}, activeWizards[], network{reachable,metered} }
    data: { dbOpen, schemaVersion, seededAt?, lastLocalWriteAt?, rowCountsByTable{}, pendingMigrations[] }
    sync: { status (SyncStatus), phase, lastPushAt?, lastPullAt?,
            pendingChangeLog{blocked,unprocessed},
            undismissedConflictCount,
            perTable{table -> {lastSyncAt, inFlight, lastError}} }
  }
  ```

- Four region builders under `lib/core/driver/state/` — each pulls from
  its existing owner. No new state is introduced; snapshot is a
  read-only aggregation:
  - `ui_region_builder.dart` ← `GoRouter`, `ScreenContractRegistry`,
    `WizardActivityTracker`.
  - `app_region_builder.dart` ← `AuthProvider`, connectivity service,
    lifecycle enum.
  - `data_region_builder.dart` ← `DatabaseService`, bounded row-count
    allowlist, `sync_metadata`.
  - `sync_region_builder.dart` ← `SyncCoordinator`, `SyncStatusStore`,
    `SyncRegistry`.

- One new `GET /diagnostics/device_state` endpoint on
  `DriverDiagnosticsHandler` returning the snapshot. Seven existing
  `/diagnostics/*` endpoints remain as fine-grained probes.

- `DevicePosture` — a pure-function projector
  (`lib/core/driver/device_state_machine.dart`) deriving one of a small
  enum from a snapshot:
  `{ booting, awaitingSignIn, awaitingConsent, idleOnDashboard,
  wizardActive, syncing, tripped, errored }`.
  Derived, never stored.

- Typed key catalog generated once from
  `tools/gen-keys/keys.yaml`:
  - Dart → `lib/shared/testing_keys/generated/keys.g.dart`.
  - PowerShell → `tools/sync-soak/generated/Keys.ps1`.
  - JSON index → `tools/sync-soak/generated/keys.json`.
  Generator is a Dart script under `tools/gen-keys/` using
  `build_runner` conventions already present in the repo.

- Harness-side additions:
  - `tools/sync-soak/DevicePosture.ps1` — `Get-`, `Assert-`, and
    `Assert-Eventually-` variants. The `Assert-Eventually-` primitive
    is Awaitility-style: `-AtMostMs`, `-PollIntervalMs`, `-DuringMs`
    for stability windows.
  - `tools/sync-soak/OrchestratorStateMachine.ps1` — cross-device
    state machine validating multi-actor invariants (e.g., all 4
    actors observe the same row count for `projects` after the
    convergence window).
  - `tools/sync-soak/LogAssertions.ps1` — declarative rule engine
    over `RuntimeErrorScanner` output; `severity: fatal` rules fail
    the run regardless of sentinel pass/fail.
  - `tools/sync-soak/Timeline.ps1` — merges every per-actor
    transition JSON + orchestrator transitions + evidence into one
    `timeline.json` + static `timeline.html` swimlane per run.

### Out of shape (explicit non-goals)

- Do not split `HeadlessAppSyncActionExecutor` into
  provisioner/dispatcher/asserter; the six responsibility groups are
  cohesive and per-action dispatch needs to call all three concerns in
  order. Only the inner `_HeadlessAppSyncActor` moves out.
- Do not route the headless executor through `SyncCoordinator`. Direct
  `SyncEngineFactory().create(...)` is the correct seam for engine-in-
  isolation tests.
- Do not broadly refactor `Flow.Mdot1174R.ps1` (still blocked on S21
  acceptance per 2026-04-18 spec item #42); only touch PowerShell if a
  Dart slice needs a new `/diagnostics/*` shape.
- Do not touch `lib/features/sync/application/sync_coordinator.dart`'s
  entrypoint contract. Observer-extraction from its 5 public callback
  hooks is a candidate but is explicitly deferred to a separate spec.
- **(STATE MACHINE)** Do not introduce a runtime statechart library
  (XState, fsm2). `DevicePosture` is a pure enum derivation.
  Orthogonality lives in the snapshot shape.
- **(STATE MACHINE)** Do not adopt OpenTelemetry / W3C traceparent
  propagation. A simple `runId / actorId / transitionIndex` triple is
  sufficient at this scale; OTel is the escape hatch if evidence ever
  outgrows filesystem artifacts.
- **(STATE MACHINE)** Do not migrate to Appium / Maestro / Patrol /
  Detox-style harnesses. Current PowerShell harness stays; this spec
  makes it smarter, not different.
- **(STATE MACHINE)** Do not adopt TLA+ or formal model checking.
  Future spec if sync-protocol confidence ever requires it.
- **(STATE MACHINE)** Do not reintroduce `sync_status` columns or
  indexes. `undismissedConflictCount` lives on the in-memory
  `SyncStatus` immutable, not in persisted DB rows.

## Size Goals

Inherit 2026-04-18 size goals (`scripts/check_sync_soak_file_sizes.ps1` +
`tools/sync-soak/size-budget-exceptions.json`). Follow-on additions:

- [ ] Dart files in `integration_test/sync/soak/` stay under 400 lines
  unless listed in the size-budget exception file.
- [ ] Dart files in `lib/core/driver/` stay under 500 lines unless
  listed in a driver-specific exception file (create
  `lib/core/driver/size-budget-exceptions.json` if needed — do not mix
  with the soak exception file).
- [ ] Any `_handle*` method in `lib/core/driver/` with cyclomatic > 15
  requires an extraction task or a written exception.
- [ ] Any SoakActionExecutor `execute` with cyclomatic > 12 requires a
  strategy-map or extraction task.
- [ ] Any `SoakDriver`-shaped coordinator method with nesting > 4 requires
  an extraction task.
- [ ] **(STATE MACHINE)** Each new region-builder file under
  `lib/core/driver/state/` stays under 150 lines. Any single region's
  `build(...)` stays under cyclomatic 10.
- [ ] **(STATE MACHINE)** `DeviceStateSnapshot` + nested region classes
  stay under 300 lines total.
- [ ] **(STATE MACHINE)** `lib/shared/testing_keys/generated/keys.g.dart`
  is exempt from size budgets (generated code) but the generator input
  `tools/gen-keys/keys.yaml` stays under 800 lines; split by feature if
  it grows past that.

## Measurable End Goals

This section is the spec's acceptance contract. Every item is externally
verifiable — a command, a file diff, or a produced artifact.

### Structural decomposition goals

- [ ] **ED-1** `lib/core/driver/harness_seed_data.dart` no longer exists
  under `lib/core/`; it lives under `integration_test/sync/harness/seed/`.
  Verification: `Test-Path lib/core/driver/harness_seed_data.dart` → false;
  `Test-Path integration_test/sync/harness/seed/harness_seed_data.dart` → true;
  `mcp__jcodemunch__get_coupling_metrics` reports Ce=0 from
  `lib/core/driver/` into feature data layers.
- [ ] **ED-2** `DriverDiagnosticsHandler._handleActorContext` cyclomatic ≤ 10,
  body ≤ 30 LOC. Verification: `mcp__jcodemunch__get_symbol_complexity`
  reports CC ≤ 10 for the symbol; file ≤ 500 lines.
- [ ] **ED-3** `SoakDriver.run` cyclomatic ≤ 8, nesting ≤ 4, body ≤ 40 LOC.
  Verification: `mcp__jcodemunch__get_symbol_complexity` reports the
  numbers; `integration_test/sync/soak/soak_runner.dart` ≤ 200 lines.
- [ ] **ED-4** `LocalSupabaseSoakActionExecutor.execute` cyclomatic ≤ 12;
  each per-action method cyclomatic ≤ 10. Verification: codemunch
  complexity report.
- [ ] **ED-5** `DriverDataSyncHandler.handle` cyclomatic ≤ 6; dispatches
  exclusively via a route table. Verification: code review +
  `test/core/driver/driver_data_sync_handler_route_table_test.dart`
  asserts every accepted route string is in the registered table.
- [ ] **ED-6** `_handleActorContext` no longer appears in
  `mcp__jcodemunch__get_hotspots` top 25 for the repo.
- [ ] **ED-7** `DriverServer` constructor has zero nullable parameters
  marked "backward compat". Verification: `grep` in
  `lib/core/driver/driver_server.dart` finds zero `// NEW — nullable`
  comments; every parameter is non-nullable in the signature.
- [ ] **ED-8** All three evidence layers (backend/RLS, device-sync,
  headless-app-sync) share a `SoakActorProvisioner` interface.
  Verification: `grep` for `implements SoakActorProvisioner` finds three
  classes — one per layer.

### State-machine goals

- [ ] **ES-1** `SyncStatus.undismissedConflictCount` field exists with
  default 0 and is populated from the existing conflict-log query.
  Verification: `grep` in `lib/features/sync/domain/sync_status.dart`
  finds the field in the constructor, `copyWith`, `==`, `hashCode`;
  unit test `test/features/sync/domain/sync_status_test.dart` covers
  default, set, clear.
- [ ] **ES-2** `Assert-SoakNoUndismissedConflictsSentinel` passes in a
  real soak run on `gocr-integration` **without** the `hasConflictField`
  error. Verification: a soak run with pre-seeded conflict_log rows that
  are then dismissed produces a passing sentinel JSON in
  `{actor}/state-machine/transition-*.json`.
- [ ] **ES-3** `GET /diagnostics/device_state` returns a valid
  `DeviceStateSnapshot` v1 with all four regions populated on any built
  driver binary. Verification: integration test
  `test/core/driver/device_state_endpoint_test.dart` asserts schema;
  schema fixture stored at
  `test/core/driver/fixtures/device_state_snapshot_v1.json`.
- [ ] **ES-4** `DeviceStateSnapshot.schemaVersion` mismatch between
  driver binary and harness is detected and fails within **5 seconds
  per actor** with classification `schema_mismatch`. Verification:
  Pester test in `tools/sync-soak/tests/DevicePosture.Tests.ps1`
  injects a fake v99 snapshot and asserts the abort path.
- [ ] **ES-5** `DevicePosture` derivation covers at least 8 enum values
  with table-driven unit tests. Verification:
  `test/core/driver/device_state_machine_test.dart` asserts every enum
  value is reachable from at least one realistic snapshot input.
- [ ] **ES-6** Typed key catalog generator produces byte-identical Dart
  and PowerShell output across three consecutive runs. Verification:
  CI step `pwsh tools/gen-keys/verify-idempotent.ps1` runs
  generator thrice and diffs outputs; exits 0.
- [ ] **ES-7** All 16 feature testing-keys modules are replaced with
  re-exports of the generated catalog at final cut-over.
  Verification: `grep -L 'generated/keys.g.dart'
  lib/shared/testing_keys/*.dart` returns only `testing_keys.dart`
  (the facade); all others import the generated file.
- [ ] **ES-8** A custom_lint rule blocks raw `Key('...')` in `lib/`
  outside the generated file and the documented GlobalKey allowlist.
  Verification: negative fixture in
  `fg_lint_packages/field_guide_lints/test/architecture/no_raw_key_outside_generated_test.dart`
  triggers the rule; positive fixture (import from generated) does not.
- [ ] **ES-9** `Assert-EventuallyDevicePosture` detects a deliberately
  broken state within `AtMostMs` and fails with a single classified
  failure (not a cascade). Verification: Pester test seeds a bad
  posture and asserts one `state_sentinel_failed` in the result, zero
  extra failures.
- [ ] **ES-10** Log assertion rules fire on: `GlobalKey duplicate`,
  `FlutterError`, any unhandled `Exception` stack trace, any `42501`
  RLS denial, any `sync_control.pulling` stuck-on log line.
  Verification: Pester test feeds each fingerprint to `LogAssertions`
  and asserts fatal classification.
- [ ] **ES-11** Any flow that completes with a non-empty
  `loggingGaps` array fails the run unless the flow opts in to
  tolerate a specific gap by name with written justification.
  Verification: Pester test injects a gap and asserts `FlowRuntime`
  promotes it to fatal; opt-in test demonstrates allow-listed flow
  passes.
- [ ] **ES-12** `timeline.html` is generated on every run and shows
  one swimlane per actor, each row an event with classification,
  linked to its evidence bundle. Verification: visual inspection of a
  real soak run's artifact; file exists at
  `{runDir}/timeline.html` and parses as valid HTML; `timeline.json`
  is sorted chronologically.
- [ ] **ES-13** Every state-machine transition JSON, orchestrator
  transition JSON, and evidence bundle carries a `runId`, `actorId`,
  and `transitionIndex` triple. Verification: Pester assertion over a
  completed run's artifacts.
- [ ] **ES-14** End-to-end failure injection drill passes: 3 seeded
  failure modes (undismissed conflict, stuck-on `sync_control.pulling`,
  role check broken) each produce **one** root classified failure and
  an actor-divergence point visible in `timeline.html`. Verification:
  dedicated drill script under
  `tools/sync-soak/drills/` with documented expected output.

## Endpoint Definition

The work is complete when every item below is checked.

### Decomposition endpoint items

- [ ] `lib/core/driver/harness_seed_data.dart`, `harness_seed_defaults.dart`,
  and `harness_seed_pay_app_data.dart` live under
  `integration_test/sync/harness/seed/`, and no file under
  `lib/core/driver/` imports them.
- [ ] `lib/core/driver/driver_diagnostics_handler.dart` is under 500 lines,
  and `_handleActorContext` has cyclomatic ≤ 10 and ≤ 30 LOC.
- [ ] `lib/core/driver/driver_data_sync_handler.dart`'s `handle` dispatcher
  is under cyclomatic 8 and dispatches via a route table registered by
  `*_query_routes.dart`, `*_mutation_routes.dart`, `*_maintenance_routes.dart`.
- [ ] `lib/core/driver/screen_contract_registry.dart` has either been split
  by contract cluster or has a written size-budget exception that names the
  cluster it is intentionally registry-shaped around.
- [ ] `lib/core/driver/driver_server.dart` constructor takes no nullable
  "backward compat" dependencies; every required seam is explicitly wired
  by `driver_setup.dart`.
- [ ] `integration_test/sync/soak/soak_runner.dart` is under 200 lines.
  `SoakDriver.run` has cyclomatic ≤ 8 and nesting ≤ 4.
- [ ] `integration_test/sync/soak/soak_worker_pool.dart` (new) owns the
  worker spin-up loop and burst-cycle pacing.
- [ ] `integration_test/sync/soak/soak_sampler.dart` (new) owns periodic
  metric capture.
- [ ] `integration_test/sync/soak/soak_run_state.dart` (new) owns counters,
  action maps, failures, actor reports, with named mutation methods.
- [ ] `integration_test/sync/soak/soak_fixture_repair.dart` (new) owns
  mutable-seed-row reset.
- [ ] `integration_test/sync/soak/headless_app_sync_actor.dart` (new) owns
  `_HeadlessAppSyncActor` and exposes it privately back to the executor.
- [ ] `integration_test/sync/soak/backend_rls_soak_action_executor.dart`'s
  `execute` uses a `Map<SoakActionKind, Future<void> Function(...)>`
  strategy table instead of a switch ladder, and is under cyclomatic 12.
- [ ] All 3 evidence layers (backend/RLS, device-sync, headless-app-sync)
  share a common `SoakActorProvisioner` interface for 15-20 actor scale
  ramp-up.

### State-machine endpoint items

- [ ] `lib/features/sync/domain/sync_status.dart` exposes
  `undismissedConflictCount: int` with default 0, plumbed through
  `copyWith`, `==`, `hashCode`, `toString`.
- [ ] `Assert-SoakNoUndismissedConflictsSentinel` passes in a real soak
  run without the `hasConflictField` error path.
- [ ] `lib/core/driver/device_state_snapshot.dart` defines
  `DeviceStateSnapshot`, `UiRegion`, `AppRegion`, `DataRegion`,
  `SyncRegion` value classes with `toJson` and `schemaVersion = 1`.
- [ ] `lib/core/driver/state/{ui,app,data,sync}_region_builder.dart`
  each expose one `build(...)` function with CC ≤ 10 and file ≤ 150
  LOC.
- [ ] `lib/core/driver/device_state_machine.dart` exposes
  `DevicePosture derive(DeviceStateSnapshot s)` — pure function, no
  state, unit-tested.
- [ ] `DriverDiagnosticsHandler` exposes
  `GET /diagnostics/device_state` returning the snapshot; existing
  seven `/diagnostics/*` endpoints remain unchanged.
- [ ] `tools/gen-keys/` generator produces
  `lib/shared/testing_keys/generated/keys.g.dart`,
  `tools/sync-soak/generated/Keys.ps1`, and
  `tools/sync-soak/generated/keys.json` from
  `tools/gen-keys/keys.yaml`.
- [ ] Every feature testing-keys module
  (`auth_keys.dart`, `common_keys.dart`, …) is a re-export of generated
  constants; no hand-written `Key('...')` constants remain in catalogued
  areas.
- [ ] `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_key_outside_generated.dart`
  is registered in `architecture_rules.dart`, has positive + negative
  test fixtures, and reports zero false positives on `lib/`.
- [ ] `tools/sync-soak/DevicePosture.ps1` exposes
  `Get-SoakDevicePosture`, `Assert-SoakDevicePosture`,
  `Assert-EventuallyDevicePosture`, with the Awaitility parameter set
  `-AtMostMs`, `-PollIntervalMs`, `-DuringMs`.
- [ ] At least one flow (recommended: `Flow.SyncDashboard.ps1`) is
  fully ported from route+key scatter to `Assert-EventuallyDevicePosture`,
  demonstrating time-to-detect for a deliberately broken state is less
  than `-AtMostMs`.
- [ ] `tools/sync-soak/OrchestratorStateMachine.ps1` implements the
  cross-device invariant primitive; at least one cross-device invariant
  ("after Actor A creates `project_X`, Actors B/C/D observe `project_X`
  in the local DB within the convergence window") is end-to-end
  verified.
- [ ] `tools/sync-soak/LogAssertions.ps1` implements the rule engine
  with at least 5 seeded fatal rules
  (`no_global_key_duplicate`, `no_flutter_error_widget`,
  `no_unhandled_exception`, `no_rls_denial_42501`,
  `no_sync_control_stuck_pulling`).
- [ ] `FlowRuntime.ps1` invokes `LogAssertions` between action and
  post-sentinels; a `fatal` rule fires classifies appropriately and
  aborts the flow.
- [ ] `tools/sync-soak/Timeline.ps1` merges per-actor + orchestrator
  transitions into `timeline.json` + static `timeline.html` on every
  run, included in evidence bundle.
- [ ] `.claude/docs/state-harness.md` documents the snapshot schema,
  sentinel contract, and log-assertion rule format.
- [ ] `.claude/rules/sync/sync-patterns.md` references the
  `DeviceStateSnapshot` + sentinel contract as part of the sync
  inspection surface.

### Shared endpoint items

- [ ] `dart analyze integration_test test/harness test/core/driver`
  reports no issues.
- [ ] `tools/test-sync-soak-harness.ps1` passes.
- [ ] `pwsh scripts/check_sync_soak_file_sizes.ps1 -FailOnBlocked`
  exits 0.
- [ ] S21 smoke rerun on the converted soak path passes, or a written
  plumbing-only note exists per guardrail.

## Lock-In Plan

Extend the 2026-04-18 size-budget tooling rather than replacing it.

- [ ] Add `lib/core/driver/**/*.dart` to the file-size report scope in
  `scripts/check_sync_soak_file_sizes.ps1` (or create a sibling
  `scripts/check_driver_file_sizes.ps1` if the scope feels foreign to
  the soak script).
- [ ] Create `lib/core/driver/size-budget-exceptions.json` only when a
  driver file needs an intentional exception (do not pre-seed).
- [ ] Add a CodeMunch-backed periodic audit command:
  - [ ] `get_hotspots` with `min_complexity=10` filtered to
    `lib/core/driver/**` and `integration_test/sync/soak/**` to catch
    new god methods before they land.
  - [ ] `get_coupling_metrics` on `harness_seed_data.dart` after the
    relocation to prove Ce drops from ~23 to 0 in `lib/core/driver/`.
- [ ] Add a PR checklist item: any new `lib/core/driver/_handle*` method
  over cyclomatic 10 must explain why it is not extracted.
- [ ] Treat a new 500+ line file in `lib/core/driver/` as a failed
  architecture review even if tests pass.
- [ ] Keep exception files per-concern (soak vs driver); do not merge.
- [ ] **(STATE MACHINE)** Add a CI gate:
  `pwsh tools/gen-keys/verify-idempotent.ps1` fails if generator output
  differs across runs or from the committed file.
- [ ] **(STATE MACHINE)** Add a CI gate: `dart run custom_lint` must
  report zero `no_raw_key_outside_generated` violations in `lib/`.
- [ ] **(STATE MACHINE)** Add a PR checklist item: any new
  `/diagnostics/*` endpoint must include a fixture at
  `test/core/driver/fixtures/` and a schema-shape assertion.

## Decomposition Philosophy

Inherit 2026-04-18 philosophy. Follow-on additions:

- [ ] Decompose by responsibility, not by arbitrary line chunks.
- [ ] Prefer named helpers around concepts we already test or discuss:
  actor, worker pool, sampler, run state, fixture repair, diagnostics
  builder, route table, seed fixture, region builder, sentinel,
  posture, log rule.
- [ ] Extract pure functions first (`SoakRunState`, diagnostics builders,
  region builders, `DevicePosture.derive`); extract side-effect helpers
  second behind narrow contracts (`SoakWorkerPool`, `SoakFixtureRepair`,
  `LogAssertions`, `Timeline`).
- [ ] Leave executor- and handler-specific business intent inside the
  executor/handler file so reviewers can still read what the test or the
  HTTP contract proves.
- [ ] Hoist inner private classes out of their host file when the host
  crosses its size budget AND the inner class is a stable data bag with
  at least two dependent methods.
- [ ] Do not split a cohesive 500-line class into micro-files. Only split
  when responsibilities are separable and there is a test or a caller
  that already treats them separately.
- [ ] When moving a file across the `lib/` → `integration_test/` boundary,
  land the move and every importer update in one commit.
- [ ] **(STATE MACHINE)** Prefer compile-time contracts to runtime
  checks where possible. Typed key catalog over string registry;
  snapshot schema version over ad-hoc field probing.
- [ ] **(STATE MACHINE)** Extend existing subsystems; do not rebuild.
  `StateMachine.ps1`, `StateSentinels.ps1`, `FailureClassification.ps1`,
  `EvidenceBundle.ps1` are all kept.
- [ ] **(STATE MACHINE)** New observability rides the existing driver
  HTTP seam. No new transport. No new state mutable from production.

## P0: Relocate harness_seed_data out of lib/core/driver/

Highest architectural-ROI slice. Fixes the single biggest layering breach
in the driver surface (Ce=23 reaching into 8 feature packages' data layers
from `lib/core/`).

- [ ] Create `integration_test/sync/harness/seed/` and move the three
  files verbatim:
  - `lib/core/driver/harness_seed_data.dart`
  - `lib/core/driver/harness_seed_defaults.dart`
  - `lib/core/driver/harness_seed_pay_app_data.dart`
- [ ] Update the three verified callers in the same commit:
  - `lib/core/driver/driver_seed_handler.dart` (the only driver-server
    caller — review whether the seed handler itself should also move to
    `integration_test/` or whether it is the driver's HTTP seam).
  - `lib/core/driver/screen_registry.dart`.
  - `lib/core/driver/flows/verification_flow_definitions.dart`.
- [ ] Update the two test callers in the same commit:
  - `test/core/driver/driver_seed_handler_test.dart`.
  - `test/features/sync/application/sync_state_repair_runner_test.dart`.
- [ ] Verify no `lib/**` file outside of `lib/core/driver/driver_seed_handler.dart`
  imports the seed files before or after the move.
- [ ] Decide whether `driver_seed_handler.dart` stays in `lib/core/driver/`
  (HTTP endpoint that happens to need the fixture) or moves alongside the
  fixture. Default: stays in `lib/core/driver/`, imports from
  `integration_test/` — accept that `lib/` is importing from
  `integration_test/` here because the handler is the driver-server's
  seam, and the driver-server itself already lives in `lib/core/`.
  Re-evaluate if this creates a `pubspec.yaml` dev-dependency issue.
- [ ] Run `dart analyze lib integration_test test` after the move.
- [ ] Run `tools/test-sync-soak-harness.ps1`.
- [ ] Confirm `mcp__jcodemunch__get_coupling_metrics` on the relocated
  file shows Ca from `lib/**` only includes `driver_seed_handler.dart`
  (or zero, if that also moved).
- [ ] Do not change any seed data values in this slice. Pure relocation.

## P0: Close the undismissedConflictCount gap (STATE MACHINE)

Smallest state-machine slice, unblocks existing dead-code sentinel.
Sequence early so downstream work can assume the field exists.

- [ ] Add `undismissedConflictCount: int` to `SyncStatus` with default 0
  in `lib/features/sync/domain/sync_status.dart`. Update `copyWith`,
  `==`, `hashCode`, `toString`.
- [ ] Wire the count in whichever class currently populates
  `SyncStatus` (verify: `SyncStatusStore` is the expected owner).
  Use the existing conflict-log query path used by
  `Assert-SoakNoUndismissedConflictsSentinel`; do not add a new query.
- [ ] Expose the field on `/diagnostics/sync_transport` so the existing
  sentinel passes without PowerShell-side code change.
- [ ] Add unit tests to `test/features/sync/domain/sync_status_test.dart`
  covering default, set, clear via `copyWith`.
- [ ] Add a driver handler test to
  `test/core/driver/driver_diagnostics_routes_test.dart` asserting the
  field is serialized on `/diagnostics/sync_transport`.
- [ ] Exit criterion (**ES-1** + **ES-2**):
  `Assert-SoakNoUndismissedConflictsSentinel` passes in a real soak run
  on `gocr-integration` with zero conflicts; regression run with seeded
  conflicts fails with the correct classification.
- [ ] Do not add new transport state or a second source of truth;
  `SyncStatus` remains the single truth.

## P0: Extract SoakRunState + SoakWorkerPool + SoakSampler

Highest soak-side ROI. Breaks up the 204-line `SoakDriver.run` and
unblocks 15-20 actor ramp-up (2026-04-18 spec P2 item #69-75).

- [ ] Create `integration_test/sync/soak/soak_run_state.dart` as a new
  `part of 'soak_driver.dart'` file owning:
  - `attemptedActions`, `successfulActions`, `failedActions`, `errors`,
    `rlsDenials`, `totalActionLatencyMs`, `maxActionLatencyMs` counters.
  - `actionCounts`, `successfulActionCounts`, `failedActionCounts` maps.
  - `samples`, `failures`, `actorReports` collections.
  - Named mutation methods: `recordAction(kind, succeeded, latencyMs)`,
    `recordFailure(kind, classification, actor)`, `recordSample(sample)`,
    `recordRlsDenial()`, `recordActor(report)`.
  - No closure-captured mutation surfaces leak outside.
- [ ] Create `integration_test/sync/soak/soak_sampler.dart` owning the
  periodic sampling loop and the `nextSampleAt` bookkeeping.
  - Public API: `Future<void> maybeSample(SoakRunState state, DateTime now)`
    and `DateTime? get nextSampleAt`.
- [ ] Create `integration_test/sync/soak/soak_worker_pool.dart` owning:
  - `Future<void> run({required SoakRunState state, required SoakSampler sampler, required Duration deadline})`.
  - The existing burst-cycle logic (`_burstCycleActions`, `_burstWindowActions`).
  - The existing per-worker `do {...} while(deadline)` loop.
  - The existing per-action try/catch/finally with error classification.
- [ ] Reduce `SoakDriver.run` to the coordinator shape:
  - Validate inputs.
  - Initialize executor.
  - Build `SoakRunState`, `SoakSampler`, `SoakWorkerPool`.
  - `await pool.run(state: state, sampler: sampler, deadline: deadline)`.
  - Finalize `SoakSummary` and return `SoakResult`.
- [ ] Target: `SoakDriver.run` cyclomatic ≤ 8, nesting ≤ 4, body ≤ 40 LOC.
- [ ] Preserve the three factory constructors:
  `SoakDriver.forLocalSupabase`, `SoakDriver.forDriver`,
  `SoakDriver.forHeadlessAppSync`.
- [ ] Preserve burst-cycle semantics exactly. Action-pacing rule change is
  out of scope for this slice.
- [ ] Preserve the failure-list cap at 50 (`failures.length < 50`).
- [ ] Preserve `SoakActionContext.burstWindowActive` signal to executors.
- [ ] Keep every existing test in `test/harness/soak_driver_test.dart`,
  `test/harness/soak_ci_10min_test.dart`,
  `test/harness/soak_nightly_15min_test.dart` green without signature
  changes.
- [ ] Run `dart analyze integration_test test/harness`.
- [ ] Run `tools/test-sync-soak-harness.ps1`.

## P0: Split _handleActorContext into auth + project builders

Directly addresses the #20 repo-wide hotspot in the driver layer
(cyclomatic 42 → expected ~3 + 2 + 3 after extraction). This slice also
prepares the handler for the `/diagnostics/device_state` endpoint in P1.

- [ ] In `lib/core/driver/driver_diagnostics_handler.dart`, extract:
  - `Map<String, dynamic> _buildAuthDiagnostics(AuthProvider? auth, User? currentUser)`
    owning lines 385-407 of the current method.
  - `Map<String, dynamic> _buildProjectDiagnostics(ProjectProvider? project)`
    owning lines 333-375 (the three `.map().take(25)` chains) plus lines
    408-420 (dict assembly).
- [ ] Reduce `_handleActorContext` to: find providers → build route →
  build auth block → build project block → assemble payload → `_sendJson`.
- [ ] Target: `_handleActorContext` cyclomatic ≤ 5, body ≤ 25 LOC. Each
  new builder ≤ 30 LOC.
- [ ] Do not touch `_handleSyncTransport` or `_handleSyncRuntime` in this
  slice — agent verification confirmed zero overlap.
- [ ] Preserve the `available` field's meaning (present when either auth
  or project provider resolved).
- [ ] Keep `_findAuthProvider()` / `_findProjectProvider()` helpers where
  they are.
- [ ] Add a structural self-test in `tools/sync-soak/tests/` or a unit
  test under `test/core/driver/driver_diagnostics_routes_test.dart` that
  asserts the shape of `auth` and `project` sub-objects separately.
- [ ] Run `dart analyze lib test/core/driver`.
- [ ] Confirm CodeMunch complexity on `_handleActorContext` drops below
  10 after the slice.

## P1: Extract SoakFixtureRepair out of the headless executor

Addresses the mutable-fixture-state smell surfaced by
`HeadlessAppSyncActionExecutor._repairMutableHarnessSeedState` (56 LOC).
This pattern will only get worse with 15-20 actors.

- [ ] Create `integration_test/sync/soak/soak_fixture_repair.dart` as a
  new `part of 'soak_driver.dart'` file owning:
  - `Future<Map<String, Object?>> repairMutableSeedState(SupabaseClient adminClient)`.
  - Any related helpers currently private to the headless executor.
- [ ] Move `_repairMutableHarnessSeedState` from
  `headless_app_sync_action_executor.dart` into the new helper.
- [ ] Make the contract explicit: it restores soft-deleted seeded photos
  for projects 1-3 (the mutation-target projects) and returns a repair
  summary.
- [ ] Ensure the repair is callable from both the headless executor and
  the backend/RLS executor if the latter ever mutates seed rows (today
  it does not).
- [ ] Ensure the repair writes its summary to the same artifact path as
  today (`_fixtureRepairSummary`).
- [ ] Preserve the admin-actor-signed-in precondition (do not change
  which persona runs the repair).
- [ ] Update the headless executor to call the extracted helper instead
  of owning the body itself.
- [ ] Run `dart analyze integration_test test/harness`.
- [ ] Run `tools/test-sync-soak-harness.ps1`.

## P1: Hoist _HeadlessAppSyncActor to its own part file

- [ ] Create `integration_test/sync/soak/headless_app_sync_actor.dart` as
  a `part of 'soak_driver.dart'` file.
- [ ] Move `_HeadlessAppSyncActor` (lines 552-573 of
  `headless_app_sync_action_executor.dart`) into it verbatim. Keep the
  class name `_HeadlessAppSyncActor` (underscore-prefixed) — Dart `part`
  files share the library's privacy, so the symbol remains private to
  the soak library.
- [ ] Add a file-level dartdoc on the new file explaining the actor is a
  data bag with one mutable flag (`initialPullComplete`) and all behavior
  belongs to the executor.
- [ ] Do not add any new methods to the actor in this slice.
- [ ] Confirm `headless_app_sync_action_executor.dart` drops below 550
  lines after the hoist.

## P1: Land DeviceStateSnapshot + region builders (STATE MACHINE)

Depends on: P0 `_handleActorContext` split landed. The new endpoint
reuses the now-clean auth + project builders and composes them with the
three new region builders.

- [ ] Create `lib/core/driver/device_state_snapshot.dart` with immutable
  value classes: `DeviceStateSnapshot`, `UiRegion`, `AppRegion`,
  `DataRegion`, `SyncRegion`. All have `toJson()`. Schema is locked to
  `schemaVersion = 1`.
- [ ] Create `lib/core/driver/state/ui_region_builder.dart` pulling from
  `GoRouter`, `ScreenContractRegistry`, `WizardActivityTracker`.
  Function shape: `UiRegion buildUiRegion(BuildContext context)`.
- [ ] Create `lib/core/driver/state/app_region_builder.dart` pulling from
  `AuthProvider`, existing connectivity service, lifecycle enum derived
  from app-bootstrap flags.
- [ ] Create `lib/core/driver/state/data_region_builder.dart` pulling
  from `DatabaseService` (open/schema), `sync_metadata`, and a bounded
  row-count allowlist (`projects`, `entries`, `change_log`,
  `conflict_log`, `photos`, `todo_items`).
- [ ] Create `lib/core/driver/state/sync_region_builder.dart` pulling
  from `SyncCoordinator`, `SyncStatusStore`, `SyncRegistry` for
  per-table detail.
- [ ] Add `GET /diagnostics/device_state` to
  `lib/core/driver/driver_diagnostics_handler.dart`, composing the four
  region builders + the P0-extracted auth/project builders into one
  `DeviceStateSnapshot` JSON.
- [ ] Do not remove or alter any of the existing seven
  `/diagnostics/*` endpoints. The snapshot is additive.
- [ ] Add unit tests for each region builder under
  `test/core/driver/state/`.
- [ ] Add integration test
  `test/core/driver/device_state_endpoint_test.dart` asserting the full
  shape against a fixture at
  `test/core/driver/fixtures/device_state_snapshot_v1.json`.
- [ ] Add PowerShell-side `Get-SoakDeviceStateSnapshot` in a new file
  `tools/sync-soak/DeviceStateSnapshot.ps1` + unit coverage in
  `tools/sync-soak/tests/DeviceStateSnapshot.Tests.ps1`.
- [ ] Exit criterion: **ES-3** + **ES-4** (schema-mismatch Pester test).

## P1: Land DevicePosture + Assert-EventuallyDevicePosture (STATE MACHINE)

Depends on: P1 DeviceStateSnapshot endpoint live.

- [ ] Create `lib/core/driver/device_state_machine.dart` with enum
  `DevicePosture { booting, awaitingSignIn, awaitingConsent,
  idleOnDashboard, wizardActive, syncing, tripped, errored }` and
  `DevicePosture derive(DeviceStateSnapshot)` pure function.
- [ ] Add table-driven unit tests to
  `test/core/driver/device_state_machine_test.dart` covering at least
  one realistic snapshot → posture mapping per enum value
  (**ES-5**).
- [ ] Create `tools/sync-soak/DevicePosture.ps1` exposing:
  - `Get-SoakDevicePosture -Actor $Actor`.
  - `Assert-SoakDevicePosture -Actor -Expected`.
  - `Assert-EventuallyDevicePosture -Actor -Expected -AtMostMs -PollIntervalMs -DuringMs`.
- [ ] The Eventually primitive MUST support `-DuringMs` stability
  windows (state must hold across the window before passing) to match
  Awaitility's `during(...)` semantics.
- [ ] Port one flow to the new primitive.
  Recommendation: `tools/sync-soak/Flow.SyncDashboard.ps1`. Replace the
  current `Assert-SoakRouteSentinel` + `Wait-SoakDriverKey` scatter
  with `Assert-EventuallyDevicePosture` where applicable.
- [ ] Exit criterion: **ES-9** — a deliberately broken state fails
  within `-AtMostMs` with a single classified failure, not a cascade.
- [ ] Preserve existing per-actor transition JSON shape; the Posture
  assertion emits a sentinel result consistent with
  `New-SoakSentinelResult`.

## P1: Strategy-map the SoakActionExecutor dispatchers

Both `LocalSupabaseSoakActionExecutor.execute` and
`HeadlessAppSyncActionExecutor.execute` currently switch on
`SoakActionKind`. The backend/RLS executor's switch is c24 / 147 LOC; the
headless executor's is c9 / 36 LOC.

- [ ] In `backend_rls_soak_action_executor.dart`, convert `execute` to a
  `Map<SoakActionKind, Future<void> Function(SoakActionContext)>` field
  populated in the constructor. Each case body becomes a private method.
  Target: `execute` cyclomatic ≤ 4, each case method cyclomatic ≤ 10.
- [ ] In `headless_app_sync_action_executor.dart`, apply the same
  refactor even though its switch is already under cyclomatic 12 — the
  symmetry pays off when a fourth action kind is added.
- [ ] Preserve fail-loud behavior on unknown actions (throw
  `StateError` with the action kind).
- [ ] Preserve the per-action error classification and retry shape.
- [ ] Preserve `SoakActionContext.burstWindowActive` semantics in every
  case branch.
- [ ] Keep every `SoakActionKind` value observable in the existing action
  counts and failure maps.

## P1: Route-table the driver_data_sync_handler dispatcher

- [ ] In `lib/core/driver/driver_data_sync_handler.dart`, replace the 20-
  branch `handle` dispatcher with a route-table built at construction
  time. Each `*_query_routes.dart`, `*_mutation_routes.dart`, and
  `*_maintenance_routes.dart` file registers its routes into the table
  instead of the dispatcher hard-coding each path.
- [ ] Target: `handle` cyclomatic ≤ 6, body ≤ 25 LOC.
- [ ] Preserve `DriverHttpGuards`-style request validation order: method
  check → path match → body parse → handler call.
- [ ] Preserve every route contract currently used by the harness driver
  client in `integration_test/sync/harness/harness_driver_client.dart`.
- [ ] Add a structural self-test under `test/core/driver/` that asserts
  every accepted route string is present in the registered table.
- [ ] Do not invent new routes in this slice.

## P1: Prepare SoakActorProvisioner interface for 15-20 actor scale

This is the bridge from the three disparate executor initialize shapes to
a shared ramp-up / provisioner contract. Fulfills 2026-04-18 spec P2
items #69-75.

- [ ] Define a `SoakActorProvisioner` abstract interface in
  `integration_test/sync/soak/soak_actor_provisioner.dart`
  (part file) with:
  - `String get actorKind` — one of `backend_rls_virtual`,
    `device_sync`, `headless_app_sync`, `emulator`.
  - `Future<int> provision(int count, SoakRunState state)` — returns
    the actual count provisioned.
  - `Future<void> teardown()`.
- [ ] Refit each executor's existing `initialize(int userCount)` as an
  adapter over the provisioner contract without changing what each
  executor does internally.
- [ ] Add a scale-manifest artifact written once per run: actor kind,
  auth user, project scope, local store path, driver port (device-sync
  only), evidence layer.
- [ ] Keep backend/RLS virtual actors out of device-sync pass/fail
  accounting (inherit 2026-04-18 guardrail #70).
- [ ] Do not ship a parent orchestration helper in this slice; the
  provisioner interface is the bridge, the orchestrator is a follow-on.
- [ ] Do not unlock the "15-20 actor claim" in external docs until the
  headless-app-sync executor has a green nightly against real Supabase
  with isolated local storage (inherit 2026-04-18 guardrail #75).

## P2: Typed key catalog (STATE MACHINE)

Depends on: P2 `screen_contract_registry` reviewed (so contract keys are
stable), and P1 `/diagnostics/device_state` in use (so a rename breaks
the snapshot's `ui.sentinelKey` field on a visible surface).

- [ ] Create `tools/gen-keys/` with a Dart CLI generator using the
  project's existing Dart tooling. Accept input at
  `tools/gen-keys/keys.yaml`.
- [ ] Write the YAML schema reference inline at the top of the
  generator source; each entry shape:
  ```yaml
  - id: sync_dashboard_screen
    kind: sentinel              # sentinel | action | state | list_item
    feature: sync
    route: /sync
    required_state_keys: [sync_pending_count, sync_phase]
    dynamic: false
  ```
- [ ] Generate Dart output at
  `lib/shared/testing_keys/generated/keys.g.dart`. Expose constants with
  the SAME NAMES as the current hand-written ones so the migration is
  a re-export swap.
- [ ] Generate PowerShell output at
  `tools/sync-soak/generated/Keys.ps1`.
- [ ] Generate JSON index at `tools/sync-soak/generated/keys.json`
  consumed by the harness at startup to refuse unknown keys early.
- [ ] Seed `tools/gen-keys/keys.yaml` from the existing
  `lib/shared/testing_keys/*.dart` content via a one-time scrape
  script. Do not hand-transcribe.
- [ ] Add a custom_lint rule
  `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_key_outside_generated.dart`
  forbidding `Key('...')` in `lib/` outside the generated file. Allow
  `ValueKey<T>(...)` and the documented GlobalKey allowlist.
- [ ] Register the lint rule in
  `fg_lint_packages/field_guide_lints/lib/architecture/architecture_rules.dart`.
- [ ] Add positive + negative fixtures under
  `fg_lint_packages/field_guide_lints/test/architecture/no_raw_key_outside_generated_test.dart`.
- [ ] Cut-over feature-by-feature. Each cut-over is one PR:
  - Move YAML entries in for that feature.
  - Replace the hand-written constants in that feature's key module
    with re-exports from `generated/keys.g.dart`.
  - Run `flutter analyze` + `dart run custom_lint` + a soak smoke.
  - Suggested order: `common`, `navigation`, `auth`, `sync`, `consent`,
    `projects`, `settings`, `documents`, `photos`, `contractors`,
    `locations`, `entries`, `quantities`, `pay_app`, `support`,
    `toolbox`. Rationale: small + stable feature modules first.
- [ ] Add the idempotency verification step
  `tools/gen-keys/verify-idempotent.ps1`.
- [ ] Exit criterion: **ES-6** + **ES-7** + **ES-8**.

## P2: driver_server DI tidy-up

- [ ] In `lib/core/driver/driver_server.dart`, remove the `//   NEW —
  nullable for backward compat` constructor branches. Make every
  previously-nullable sync/database/project-lifecycle dependency
  required in the constructor.
- [ ] Update `lib/core/driver/driver_setup.dart` to wire every
  dependency explicitly. No ad-hoc wiring.
- [ ] Remove any runtime `if (x == null)` guards that only existed to
  support the nullable constructor shape.
- [ ] Run every driver-server test and every soak smoke that hits
  `/driver/ready`.
- [ ] Inherit 2026-04-18 spec item #76: `driver_server.dart` remains a
  thin dispatch shell. Verify it is still under 220 lines after this
  slice.

## P2: driver_file_injection_handler split

- [ ] In `lib/core/driver/driver_file_injection_handler.dart` (451 lines),
  separate the four `_handleInject*` methods into two handler files
  aligned with their acceptance contracts:
  - `driver_photo_injection_handler.dart` owns `_handleInjectPhoto` and
    `_handleInjectPhotoDirect`.
  - `driver_document_injection_handler.dart` owns `_handleInjectFile`
    and `_handleInjectDocumentDirect`.
- [ ] Keep the shared helpers (`_validatePhotoFilename`,
  `_validateFilename`, `_readJsonBody`, `_sendJson`, size constants,
  UUID pattern) in a `driver_injection_shared.dart` file.
- [ ] Preserve the 32 MiB / 45 MiB size limits exactly.
- [ ] Preserve the UUID pattern exactly.
- [ ] Preserve the allowed-extension sets exactly.
- [ ] Update `driver_server.dart` to register both handlers.

## P2: screen_contract_registry review

The 2026-04-18 spec (item #77) deferred this as "registry-shaped, not a
soak runner". 719 lines is now past the 500 threshold. Do not split
reflexively; first decide whether the registry is one cohesive table or
several clusters.

- [ ] Read the full registry and list every registered screen contract
  with its source feature.
- [ ] If all contracts are shape-isomorphic (same fields, same
  diagnostics output), keep as-is and add a size-budget exception noting
  "intentionally registry-shaped" with expiry 2026-09-30.
- [ ] If contracts cluster by feature (auth, projects, forms, sync), split
  the registry into per-cluster files that each expose a registration
  function called by `lib/core/driver/screen_registry.dart`.
- [ ] Do not invent a new contract format.
- [ ] Do not move contracts closer to the feature they describe; the
  2026-04-18 guardrail ("screens stay inspectable through existing driver
  contracts") implies the registry is the integration point.

## P2: Clean up soak_driver.dart inheritance

- [ ] Confirm `integration_test/sync/soak/soak_driver.dart` still matches
  the `part` layout after the P0/P1 slices land:
  - `soak_action_mix.dart`
  - `soak_models.dart`
  - `soak_executors.dart`
  - `soak_runner.dart`
  - `soak_run_state.dart` (new)
  - `soak_sampler.dart` (new)
  - `soak_worker_pool.dart` (new)
  - `soak_fixture_repair.dart` (new)
  - `soak_actor_provisioner.dart` (new)
  - `driver_soak_action_executor.dart`
  - `backend_rls_soak_action_executor.dart`
  - `headless_app_sync_action_executor.dart`
  - `headless_app_sync_actor.dart` (new)
  - `soak_personas.dart`
- [ ] Confirm the facade itself remains under 80 lines.
- [ ] Confirm every importer still imports `soak_driver.dart` only.

## P3: Orchestrator state machine (STATE MACHINE)

Depends on: P1 DevicePosture primitive in use on at least one flow,
P2 typed key catalog cut-over complete (so cross-device invariants can
reference stable keys).

- [ ] Create `tools/sync-soak/OrchestratorStateMachine.ps1` with:
  - `Invoke-SoakOrchestratorTransition` — cross-device analog of
    `Invoke-SoakStateTransition`, taking an array of actors and a
    scenario definition.
  - `Assert-SoakOrchestratorInvariant` — declarative invariant runner
    (e.g., "`rowCountsByTable.projects` is identical across all
    actors within the convergence window").
- [ ] Implement and verify end-to-end the first cross-device invariant:
  "after Actor A creates `project_X`, Actors B/C/D observe
  `project_X` in the local DB within a convergence window of 30s."
- [ ] Emit `orchestrator-transition-*.json` in the run directory,
  timestamped, referencing per-actor transitions for cross-link.
- [ ] Add Pester coverage for the primitive in
  `tools/sync-soak/tests/OrchestratorStateMachine.Tests.ps1`.
- [ ] Do not port every existing flow to the orchestrator in this
  slice. One reference flow is the acceptance criterion.

## P3: Fail-loud log engine (STATE MACHINE)

Can land in parallel with P3 orchestrator (no dependency between them).

- [ ] Create `tools/sync-soak/LogAssertions.ps1` as a declarative rule
  engine over the output of `RuntimeErrorScanner` and adb-logcat.
  Rule shape:
  ```
  {
    id: 'no_global_key_duplicate',
    match: regex-or-category,
    severity: 'fatal' | 'warning',
    classification: 'runtime_log_error'
  }
  ```
- [ ] Seed five fatal rules (**ES-10**):
  - `no_global_key_duplicate` — Flutter's duplicate GlobalKey assertion.
  - `no_flutter_error_widget` — ErrorWidget visibility in widget tree.
  - `no_unhandled_exception` — any unhandled `Exception` stack trace
    in adb-logcat.
  - `no_rls_denial_42501` — any `42501` Postgres RLS denial.
  - `no_sync_control_stuck_pulling` — `sync_control.pulling=true` log
    lines that persist past a threshold.
- [ ] Wire `LogAssertions` into `FlowRuntime.ps1` between action and
  post-sentinels; a matching fatal rule aborts the flow via
  `throw "[$classification] ..."`.
- [ ] Enforce the `loggingGaps` rule (**ES-11**): any flow completing
  with a non-empty `loggingGaps` array fails, unless the flow opts in
  to tolerate a specific gap name with a documented reason field.
- [ ] Add Pester coverage in
  `tools/sync-soak/tests/LogAssertions.Tests.ps1` per rule.

## P3: Unified cross-device timeline (STATE MACHINE)

Depends on: P3 orchestrator (to have orchestrator transition JSON to
merge) and P3 log engine (to have fatal rule hits to flag).

- [ ] Create `tools/sync-soak/Timeline.ps1`:
  - `Get-SoakTimeline -RunDir` — reads every
    `{actor}/state-machine/*.json`, `orchestrator-transition-*.json`,
    and evidence-bundle summaries in `RunDir`; emits `timeline.json`
    sorted by `capturedAtUtc`, keyed by `runId/actorId/transitionIndex`.
  - `Render-SoakTimelineHtml -TimelineJson -Out` — static HTML swimlane
    per actor with inline CSS/SVG (no JS framework, no server).
- [ ] Include in the default evidence bundle on every run.
- [ ] Exit criterion: **ES-12**.

## P3: Defer until MDOT 1174R unblocked (inherited)

Inherit 2026-04-18 spec item #42: do not broadly refactor
`Flow.Mdot1174R.ps1` until the row-section key/state failure is fixed or
the refactor is directly targeted at reducing that failure. Follow-on
deferrals:

- [ ] Do not restructure `driver_interaction_handler_gesture_routes.dart`
  (499 lines) until after P0/P1 land.
- [ ] Do not restructure `driver_data_sync_handler_query_routes.dart`
  (516 lines) until after P1 route-table lands, since the table shape may
  naturally shrink this file.
- [ ] Do not touch `driver_widget_inspector.dart` (329 lines); the
  testing rule ("keep sync-visible UI inspectable through existing
  driver contracts") prefers stable inspector behavior over splitting.
- [ ] Do not open the `lib/features/sync/application/sync_coordinator.dart`
  observer-extraction lane here; that deserves its own spec because
  `SyncCoordinator` has Ca=44 and is the sync entrypoint for real users.

## P3: Adjacent sync engine tests (separate track)

Inherit 2026-04-18 spec P3 item #79 verbatim. Still separate.

- [ ] Open a separate decomposition checklist for large sync engine tests:
  - `test/features/sync/engine/sync_engine_test.dart` (1,433 lines,
    `main` cyclomatic 96, #3 hotspot).
  - `test/features/sync/engine/file_sync_handler_test.dart` (`main`
    cyclomatic 118, #2 hotspot).
  - `test/features/projects/presentation/screens/project_list_screen_test.dart`
    (`main` cyclomatic 216, #1 hotspot).
- [ ] Prefer fixture builders and scenario helpers over huge inline test
  setup.
- [ ] Do not mix this into the soak+driver decomposition.

## P3: Hardening & docs (STATE MACHINE)

- [ ] Update `.claude/rules/sync/sync-patterns.md` with the
  `DeviceStateSnapshot` + sentinel contract as part of the sync
  inspection surface.
- [ ] Write one-page `.claude/docs/state-harness.md` covering:
  - Snapshot schema (v1).
  - Sentinel contract and Eventually semantics.
  - Log-assertion rule format.
  - Orchestrator invariant format.
  - How to add a new `DevicePosture` enum value.
- [ ] Audit remaining `GlobalKey` sites that were allowlisted during
  P2 cut-over: migrate what can go to `ValueKey` from the generated
  catalog; document why each remaining site stays.
- [ ] Run the three acceptance drills as part of the spec's close-out:
  - **Failure injection drill** (**ES-14**).
  - **Key rename drill** (**ES-6** + **ES-8**).
  - **Observability drill** (**ES-12**).

## Suggested Implementation Order

Order minimizes acceptance risk: smallest layering fix first, then
state-machine unblock, then soak structural work (protected by
`test-sync-soak-harness.ps1`), then driver layer (protected by driver
tests + S21 reruns), then state-machine build-out on the now-clean
foundation, then deferred lanes.

1. [ ] **P0** Relocate `harness_seed_data.dart` + siblings to
   `integration_test/sync/harness/seed/`. Single commit, six caller
   updates, pure move.
2. [ ] **P0** Close the `undismissedConflictCount` gap on `SyncStatus`
   and unblock `Assert-SoakNoUndismissedConflictsSentinel`.
3. [ ] **P0** Extract `SoakRunState`, `SoakWorkerPool`, `SoakSampler` and
   reduce `SoakDriver.run` to coordinator shape. One PR, three new part
   files.
4. [ ] **P0** Split `_handleActorContext` into auth + project builders.
   Small PR, verifiable by CodeMunch complexity check.
5. [ ] **P1** Land `DeviceStateSnapshot` value class + four region
   builders + `GET /diagnostics/device_state`. Integration test + PS
   wrapper.
6. [ ] **P1** Extract `SoakFixtureRepair` from the headless executor.
7. [ ] **P1** Hoist `_HeadlessAppSyncActor` to its own part file.
8. [ ] **P1** Strategy-map the two `SoakActionExecutor.execute`
   dispatchers (backend/RLS first, then headless).
9. [ ] **P1** Route-table the `DriverDataSyncHandler.handle` dispatcher.
10. [ ] **P1** Land the `SoakActorProvisioner` interface + scale
    manifest; keep the "15-20 actor claim" gated behind a green nightly.
11. [ ] **P1** Land `DevicePosture` derivation + PS
    `Assert-EventuallyDevicePosture`; port `Flow.SyncDashboard.ps1` as
    the reference consumer.
12. [ ] **P2** `DriverServer` DI tidy-up (remove nullable back-compat).
13. [ ] **P2** Split `driver_file_injection_handler.dart` by photo vs
    document surface.
14. [ ] **P2** Review `screen_contract_registry.dart`; split or document
    the exception.
15. [ ] **P2** Typed key catalog generator + cut-over feature-by-feature
    (16 PRs, sequenced by the documented feature order).
16. [ ] **P2** Confirm `soak_driver.dart` facade shape after all P0/P1
    slices.
17. [ ] **P3** Orchestrator state machine + first cross-device
    invariant.
18. [ ] **P3** Fail-loud log engine + five seeded fatal rules +
    `loggingGaps` enforcement.
19. [ ] **P3** Unified cross-device timeline (`timeline.json` +
    `timeline.html`).
20. [ ] **P3** Run the three acceptance drills and close out.
21. [ ] **P3** Open the separate sync-engine test decomposition
    checklist.

## Acceptance Gates

- [ ] `dart analyze lib integration_test test/harness test/core/driver`
  reports no issues after every slice.
- [ ] `dart run custom_lint` reports no new warnings after every slice.
- [ ] `tools/test-sync-soak-harness.ps1` passes after every slice.
- [ ] `pwsh scripts/check_sync_soak_file_sizes.ps1 -FailOnBlocked` exits 0
  after every slice, with any new exceptions documented in the exception
  file and motivated in the slice's progress-log entry.
- [ ] S21 smoke passes on the next device-sync slice that touches the
  accepted path, or a written plumbing-only note exists per guardrail.
- [ ] `mcp__jcodemunch__get_hotspots` top 25 after the decomposition no
  longer lists `_handleActorContext` or any other
  `lib/core/driver/**` method.
- [ ] `mcp__jcodemunch__get_coupling_metrics` on
  `lib/core/driver/harness_seed_data.dart` is "file not found" (file
  relocated) or Ce=0 in the `lib/core/driver/` scope.
- [ ] `mcp__jcodemunch__get_coupling_metrics` on
  `lib/core/driver/driver_server.dart` shows no nullable-compat
  dependencies (constructor reads as required).
- [ ] `integration_test/sync/soak/soak_runner.dart` under 200 lines;
  `SoakDriver.run` cyclomatic ≤ 8, nesting ≤ 4.
- [ ] `integration_test/sync/soak/headless_app_sync_action_executor.dart`
  under 550 lines.
- [ ] `integration_test/sync/soak/backend_rls_soak_action_executor.dart`
  `execute` cyclomatic ≤ 12.
- [ ] `lib/core/driver/driver_data_sync_handler.dart` `handle`
  cyclomatic ≤ 6.
- [ ] `lib/core/driver/driver_diagnostics_handler.dart` under 500 lines
  and `_handleActorContext` cyclomatic ≤ 10.
- [ ] No file in `lib/core/driver/` imports from
  `lib/features/*/data/datasources/local/*.dart` except the original
  cross-feature exception that already existed before this spec (none
  known — the spec expects a clean slate).
- [ ] Every converted soak flow writes the same summary/timeline/ledger
  artifact names as before the slice (inherit 2026-04-18 acceptance
  gate).
- [ ] Backend/RLS and device-sync summaries remain separately labeled;
  headless-app-sync summaries land in a third label
  (`soakLayer: headless_app_sync`) distinct from both.
- [ ] The next S21 accepted flow attempted after each behavioral
  extraction has `runtimeErrors=0`, `loggingGaps=0`, final queue
  drained, and no direct driver sync acceptance.
- [ ] **(STATE MACHINE)** Every measurable end goal **ES-1** through
  **ES-14** is individually checked and referenced in the progress
  checkpoint with the verification command and its expected output.
- [ ] The progress checkpoint
  (`.codex/checkpoints/2026-04-19-sync-soak-decomposition-state-machine-progress.md`)
  records every file moved, every public function preserved, every
  generated artifact, and every verification command/artifact.

## Risk Register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Relocating `harness_seed_data` breaks a caller not in the verified list | Low | Single-commit move + full `dart analyze lib integration_test test` before merge |
| `SoakDriver.run` extraction regresses burst-cycle or sample pacing | Medium | Preserve exact counters and semantics; reuse existing `soak_driver_test.dart` without signature changes |
| `DeviceStateSnapshot` region builders become a perf hog on low-end emulators | Medium | Bounded row-count allowlist; opt-in expensive fields; measure in P1 integration test |
| Typed key catalog generator + PS consumer drift | Medium | One YAML source; JSON index consumed by both Dart and PS; idempotency gate in CI |
| Cut-over PRs break live soak runs | High if rushed | Feature-by-feature in P2; each PR smoke-tested; soak gate before merge |
| `undismissedConflictCount` query is expensive once populated | Low | Reuse the existing conflict-log query path; no new joins |
| PS-side `OrchestratorStateMachine` becomes a god-module | Medium | Coordinator only: no per-flow knowledge; per-flow expected matrices injected |
| Log-assertion fatal rules produce false positives on existing runs | Medium | Pester coverage per rule; gate behind a flag for the first two soak nightlies, then enforce |
| Schema-version bump pain when regenerating keys | Medium | Generator verifies byte-identical output; schema version bump is a deliberate PR, never accidental |
| We ship this and runtime impact isn't verified on a real device | HIGH | Per CLAUDE.md: every P-lane exit requires real 2-device smoke, not just unit tests |

## Open Questions (resolve before the relevant lane starts)

1. **Where does `DevicePosture` live for test consumption?**
   Recommendation: stay in `lib/core/driver/` (test-facing diagnostics
   already live there). Re-evaluate at P3 if production code ever
   needs the enum.
2. **YAML catalog vs Dart-first catalog?**
   Recommendation: YAML. Language-neutral; Dart and PS both consume a
   generated artifact; one-way codegen avoids coupling PS to the
   Dart build pipeline.
3. **Row-count allowlist scope for `DataRegion.rowCountsByTable`.**
   Recommendation: `projects`, `entries`, `change_log`,
   `conflict_log`, `photos`, `todo_items`. Others hidden behind a
   debug flag. Re-evaluate if a new convergence assertion needs a
   new table.
4. **Cut-over risk for the typed key catalog — full vs partial.**
   Recommendation: full cut-over before P3 orchestrator lands,
   because cross-device invariants depend on key stability. Feature-
   by-feature cut-over is the delivery strategy, not the exit state.
5. **Keep `driver_seed_handler.dart` in `lib/core/driver/` or relocate?**
   Recommendation: stays in `lib/core/driver/`, imports from
   `integration_test/`. Re-evaluate if `pubspec.yaml` dev-dependency
   constraints are violated.
6. **How strict is the `loggingGaps` fatality rule at first landing?**
   Recommendation: warning-only for the first two soak nightlies, then
   flip to fatal. Prevents a hard cutover on an unknown-frequency
   event.


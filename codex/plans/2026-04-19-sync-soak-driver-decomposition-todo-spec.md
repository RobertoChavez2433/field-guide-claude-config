# Sync Soak + Driver Decomposition Todo Spec (Follow-On)

Date: 2026-04-19
Branch: `gocr-integration`

## Purpose

Follow-on decomposition backlog for the sync-soak + device-runner systems after
the 2026-04-18 decomposition closed P0/P1 (`.claude/codex/plans/2026-04-18-sync-soak-decomposition-todo-spec.md`).
That predecessor split `tools/enterprise-sync-soak-lab.ps1` into a 144-line
facade, pulled out FlowRuntime / MutationTargets / ChangeLogAssertions /
MutationLedger / CleanupDispatch / StorageProof / FormFlow / FormMarkers /
JsonWriter / FailureClassification / ArtifactWriter split, and reduced
`integration_test/sync/soak/soak_driver.dart` from 998 lines to a 56-line
library facade with 7 part files. P2 and P3 lanes were deliberately deferred:
the app-side driver layer was left alone ("only if needed"), the 15-20 actor
scale orchestration was parked behind "headless app-sync actors exercise
actual sync engine and isolated local storage", and adjacent sync-engine test
cleanup was split off as a separate track.

Since 2026-04-18, a third soak evidence layer has landed: isolated-SQLite
headless app-sync actors. This expanded the runtime surface — `soak_runner.dart`
grew to 325 lines with a 204-line `run()` method (cyclomatic 30, nesting 8),
`backend_rls_soak_action_executor.dart` grew to 374 lines with a 147-line
dispatcher (cyclomatic 24), and the new `headless_app_sync_action_executor.dart`
landed at 592 lines. The app-side driver layer that was parked as "adjacent
driver support only if needed" now needs the decomposition it was promised:
`harness_seed_data.dart` has ballooned to 615 lines and pulls from 9
feature datasources and 10 feature models, `driver_diagnostics_handler.dart`
is 611 lines and its `_handleActorContext` is currently the #20 hotspot
repo-wide (cyclomatic 42, 97-line body), and `screen_contract_registry.dart`
is now 719 lines.

This spec is the structural-debt companion that picks up those deferred
lanes and the new debt that accumulated while building the third evidence
layer. It is not a replacement for the unified hardening checklist and must
preserve every acceptance contract the predecessor locked in.

Primary hardening tracker:
`.codex/plans/2026-04-18-sync-soak-unified-hardening-todo.md`

Append implementation notes to:
`.codex/checkpoints/2026-04-19-sync-soak-driver-decomposition-progress.md`
(new — create on first slice).

## Guardrails

Inherit everything in `.claude/codex/plans/2026-04-18-sync-soak-decomposition-todo-spec.md`,
plus the following follow-on guardrails.

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

## Target Shape

### At-scale test picture

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

### Target component shape

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

### Out of shape (explicit non-goals for this spec)

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

## Endpoint Definition

The decomposition lane is complete when every item below is checked:

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
- [ ] `dart analyze integration_test test/harness` reports no issues.
- [ ] `tools/test-sync-soak-harness.ps1` passes.
- [ ] `pwsh scripts/check_sync_soak_file_sizes.ps1 -FailOnBlocked` exits 0.
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

## Decomposition Philosophy

Inherit 2026-04-18 philosophy. Follow-on additions:

- [ ] Decompose by responsibility, not by arbitrary line chunks.
- [ ] Prefer named helpers around concepts we already test or discuss:
  actor, worker pool, sampler, run state, fixture repair, diagnostics
  builder, route table, seed fixture.
- [ ] Extract pure functions first (`SoakRunState`, diagnostics builders);
  extract side-effect helpers second behind narrow contracts
  (`SoakWorkerPool`, `SoakFixtureRepair`).
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
(cyclomatic 42 → expected ~3 + 2 + 3 after extraction).

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

## P3: Defer until MDOT 1174R unblocked

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

## Suggested Implementation Order

Order minimizes acceptance risk: smallest layering fix first, then soak
structural work (protected by `test-sync-soak-harness.ps1`), then driver
layer (protected by driver tests + S21 reruns), then deferred lanes.

1. [ ] **P0** Relocate `harness_seed_data.dart` + siblings to
   `integration_test/sync/harness/seed/`. Single commit, six caller
   updates, pure move.
2. [ ] **P0** Extract `SoakRunState`, `SoakWorkerPool`, `SoakSampler` and
   reduce `SoakDriver.run` to coordinator shape. One PR, three new part
   files.
3. [ ] **P0** Split `_handleActorContext` into auth + project builders.
   Small PR, verifiable by CodeMunch complexity check.
4. [ ] **P1** Extract `SoakFixtureRepair` from the headless executor.
5. [ ] **P1** Hoist `_HeadlessAppSyncActor` to its own part file.
6. [ ] **P1** Strategy-map the two `SoakActionExecutor.execute`
   dispatchers (backend/RLS first, then headless).
7. [ ] **P1** Route-table the `DriverDataSyncHandler.handle` dispatcher.
8. [ ] **P1** Land the `SoakActorProvisioner` interface + scale manifest;
   keep the "15-20 actor claim" gated behind a green nightly.
9. [ ] **P2** `DriverServer` DI tidy-up (remove nullable back-compat).
10. [ ] **P2** Split `driver_file_injection_handler.dart` by photo vs
   document surface.
11. [ ] **P2** Review `screen_contract_registry.dart`; split or document
   the exception.
12. [ ] **P2** Confirm `soak_driver.dart` facade shape after all P0/P1
   slices.
13. [ ] **P3** Open the separate sync-engine test decomposition checklist.

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
- [ ] The progress checkpoint
  (`.codex/checkpoints/2026-04-19-sync-soak-driver-decomposition-progress.md`)
  records every file moved, every public function preserved, and every
  verification command/artifact.

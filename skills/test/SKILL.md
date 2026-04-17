---
name: test
description: "Manually drive UI E2E flows through the HTTP driver, collect logs/screenshots/sync evidence, and report failures without turning the skill into an auto-fix workflow."
user-invocable: true
disable-model-invocation: true
---

# Test

Manually drive end-to-end flows through the HTTP driver/debug server. This
skill captures evidence, writes organized artifacts, and reports failures. It
does not treat route-only runner output as a pass and does not turn failures
into an automatic repair pipeline.

## Artifact Root

Write live test artifacts to one folder:

- `.claude/test-results/YYYY-MM-DD_HHmm-manual-ui-rls-sweep/`

Use only this root for new runs.

Required files: `README.md`, `coverage.md`, `findings.md`,
`findings.jsonl`, and `run-manifest.json`.

Required evidence folders: `devices/s21/{logs,screenshots,sync}/`,
`devices/s10/{logs,screenshots,sync}/`, `features/`, `rls/by-role/`, and
`rls/service-role-checks/`.

## Hard Rules

1. Claude is the user. Manually drive the app; helpers may collect evidence
   but must not decide pass/fail for a broad flow.
2. Use `/driver/wait` or `/driver/find` to prove state changes. Do not rely on
   blind sleeps.
3. Read the relevant `testing_keys/*.dart` file before guessing keys.
4. Capture screenshots at checkpoints, but review only failed/warning cells,
   visually ambiguous screens, suspected layout defects, and representative
   proof images.
5. Do not auto-fix failures or dispatch fixer agents from this skill.
6. Bugs live in the run folder first: `findings.md` plus `findings.jsonl`.
7. Keep flows feature-scoped. Do not thread setup or auth through downstream
   features; use `/driver/seed` preconditions unless the selected feature is
   `auth`.
8. UI E2E cells fail on visible UI defects, sync defects, permission defects,
   bad back/forward flow, nested-screen confusion, or new debug-log errors;
   route/key assertions alone are not enough.

## Concise Flow Shape

Anthropic's prompting guidance favors short, structured subtasks with clear
fixed context and variable inputs. Apply the same shape to E2E flows:

- one feature file owns one user surface
- one sub-flow verifies one navigation or behavior edge
- `requires` declares state setup; steps do not replay setup UI
- split a sub-flow when it needs more than one route transition, one mutation,
  and one assertion checkpoint
- keep assertions concrete: sentinel key, current route, exported file, or PDF
  field state
- auth is tested in `auth.md`; other features start from seeded, role-specific
  app state

## Sync Hard Rules

For `S01-S21`, these are mandatory:

1. Never use `POST /driver/sync`. Sync through the UI only.
2. Prove each sync mutation across the applicable chain:
   - sender UI
   - sender SQLite
   - sender `change_log`
   - Supabase row or storage object
   - receiver SQLite
   - receiver UI
3. After text entry on Android, dismiss the keyboard before tapping buttons.
4. After navigation taps, verify arrival with a known sentinel key.
5. Check debug-server errors and sync logs after every sync-relevant step.

## Required References

Always load these first:

- `references/driver-and-navigation.md`
- `references/debug-server-and-logs.md`

Then load only the feature or sync docs the requested scope needs:

- `test-flows/features/auth.md`
- `test-flows/features/dashboard.md`
- `test-flows/features/projects.md`
- `test-flows/features/entries.md`
- `test-flows/features/forms.md`
- `test-flows/features/pay_applications.md`
- `test-flows/features/quantities.md`
- `test-flows/features/analytics.md`
- `test-flows/features/pdf.md`
- `test-flows/features/gallery.md`
- `test-flows/features/toolbox.md`
- `test-flows/features/calculator.md`
- `test-flows/features/todos.md`
- `test-flows/features/settings.md`
- `test-flows/features/sync_ui.md`
- `test-flows/features/contractors.md`
- `test-flows/flow-dependencies.md`
- `test-flows/sync/framework.md`
- `test-flows/sync/flows-S01-S03.md`
- `test-flows/sync/flows-S04-S06.md`
- `test-flows/sync/flows-S07-S10.md`
- `test-flows/sync/flows-S11-S19.md`
- `test-flows/manual/manual-ui-sweep.md`
- `test-flows/manual/role-boundaries.md`

## Inputs

Supported command shapes:

- `/test auth`
- `/test entries`
- `/test entries deep_link_entry --device s21`
- `/test forms --device s10`
- `/test sync`
- `/test S01`
- `/test T15-T23`
- `/test manual-ui-sweep`
- `/test role-boundaries`
- `/test --resume`

## Workflow

### 1. Preflight

- parse the requested scope
- verify driver readiness
- start or reuse the driver with `tools/start-driver.ps1`
- read `.claude/test-credentials.secret`
- create the run directory and required subfolders

Prefer `tools/start-driver.ps1` over manual launch commands.

### 2. Execute Flows

For each feature sub-flow or manual checklist cell:

1. call `POST /driver/seed` with each YAML `requires` precondition
2. manually perform the steps from the feature, sync, or manual overlay doc
3. verify the expected state with `/driver/find` and `/driver/current-route`
4. scan debug-server errors for the cell window
5. capture a screenshot when useful; review it when the cell fails, warns, is
   visually ambiguous, or needs representative proof
6. inspect sync state on both devices for sync-relevant cells
7. record PASS or FAIL in `coverage.md`
8. record every defect in `findings.md` and `findings.jsonl`

### 3. Per-Feature Wrap-Up

After each feature:

- scan debug-server errors since feature start
- capture a log summary if needed for the report
- update `coverage.md`
- update `findings.md`
- update `findings.jsonl`

### 4. Compaction / Resume

After every 4 features, or at the sync compaction boundaries, stop with:

```text
Checkpoint written. Say 'continue' to proceed.
```

On resume:

1. find the latest run under `.claude/test-results/`
2. read `checkpoint.json`
3. restore the required driver and app state
4. continue from `next_flow`

## Checkpoint File

Write after every flow:

- `.claude/test-results/<run>/checkpoint.json`

Track:

- run id
- platform
- current role
- completed flows
- next flow
- findings
- observations
- any persisted IDs needed for resume

## Findings Files

Write after every feature:

- `.claude/test-results/<run>/findings.md`
- `.claude/test-results/<run>/findings.jsonl`

Each finding must include:

- id
- severity: blocker, high, medium, low
- category
- feature
- device
- role
- route and screen
- steps, expected result, actual result
- log evidence path
- screenshot evidence path when useful
- sync evidence path when relevant
- status: open, fixed, retest-needed, spec-gap, or blocked

## Failure Signals

Treat these as authoritative failures:

- driver returns `404`
- driver returns `408`
- `/driver/find` proves the target never appeared
- debug server reports new errors for the operation window
- sync does not settle when the flow expects it to
- visible UI defects, sync defects, or debug-log runtime errors appear
- permission or RLS behavior disagrees with the role contract
- back/forward flow creates nested, stranded, or confusing screens

## Missing-Key Protocol

If a flow fails because a key is missing:

1. record the missing key
2. finish the rest of the tier if possible
3. report the missing key as a concrete failure

Do not dispatch a fixer agent from this skill.

## Role Handling

Always be explicit about the account in use.

- default role: `admin`
- inspector flows use the inspector account from credentials
- role-boundary runs cover `admin`, `engineer`, `officeTechnician`, and
  `inspector`

After login or role switch:

1. normalize to a known screen
2. verify the expected project context
3. dismiss overlays before continuing

For denied paths, record both UI behavior and backend/log behavior when
possible. Service-role checks are verification-only and never the app actor.

## Driver And Platform Notes

- use `tools/start-driver.ps1` and `tools/stop-driver.ps1`
- use `POST /driver/hot-restart` only when a hot restart is actually safe
- use `python` or `py -3` instead of assuming `python3` on Windows
- use `pwsh -Command` for PowerShell invocations

## Test Data Safety

- use timestamped names for E2E-created records
- prefer reusable E2E data when the existing state is still valid
- never print secrets from `.claude/test-credentials.secret`
- keep service-role exposure limited to the existing verification tooling

## Teardown

When the run is complete:

```text
pwsh -File tools/stop-driver.ps1
```

Leave the debug server running only if the user wants to inspect logs.

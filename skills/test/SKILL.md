---
name: test
description: "Run HTTP-driver E2E flows, write shared test artifacts, and report failures without turning the skill into an auto-fix workflow."
user-invocable: true
disable-model-invocation: true
---

# Test

Run end-to-end flows through the HTTP driver. This skill executes flows,
captures evidence, writes artifacts, and reports failures. It does not turn
failed tests into an automatic repair pipeline.

## Artifact Root

Write live test artifacts to:

- `.claude/test-results/YYYY-MM-DD_HHmm_<descriptor>/`

Use only this root for new runs.

## Hard Rules

1. Use `/driver/wait` or `/driver/find` to prove state changes. Do not rely on
   blind sleeps.
2. Read the relevant `testing_keys/*.dart` file before guessing keys.
3. Save screenshots for every flow, but only inspect them inline when a failure
   signal appears.
4. Do not auto-fix failures or dispatch fixer agents from this skill.
5. Bugs live in GitHub Issues, not local defect files.

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

Then load only the tier or sync docs the requested scope needs:

- `test-flows/tiers/setup-and-auth.md`
- `test-flows/tiers/entry-crud.md`
- `test-flows/tiers/toolbox-and-pdf.md`
- `test-flows/tiers/pay-app-and-exports.md`
- `test-flows/tiers/settings-and-admin.md`
- `test-flows/tiers/mutations.md`
- `test-flows/tiers/verification.md`
- `test-flows/tiers/manual-flows.md`
- `test-flows/flow-dependencies.md`
- `test-flows/sync/framework.md`
- `test-flows/sync/flows-S01-S03.md`
- `test-flows/sync/flows-S04-S06.md`
- `test-flows/sync/flows-S07-S10.md`
- `test-flows/sync/flows-S11-S19.md`

## Inputs

Supported command shapes:

- `/test auth`
- `/test entries`
- `/test sync`
- `/test S01`
- `/test T15-T23`
- `/test full`
- `/test --resume`

## Workflow

### 1. Preflight

- parse the requested scope
- verify driver readiness
- start or reuse the driver with `tools/start-driver.ps1`
- read `.claude/test-credentials.secret`
- create the run directory

Prefer `tools/start-driver.ps1` over manual launch commands.

### 2. Execute Flows

For each flow:

1. perform the steps from the tier or sync doc
2. verify the expected state
3. scan for new errors
4. save a screenshot
5. record PASS or FAIL in the checkpoint

### 3. Per-Tier Wrap-Up

After each tier:

- scan debug-server errors since tier start
- capture a log summary if needed for the report
- update `checkpoint.json`
- update `report.md`

### 4. Compaction / Resume

After every 2 tiers, or at the sync compaction boundaries, stop with:

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
- bugs
- observations
- any persisted IDs needed for resume

## Report File

Write after every tier:

- `.claude/test-results/<run>/report.md`

Keep it short:

- tier results table
- bugs found
- notable observations

## Failure Signals

Treat these as authoritative failures:

- driver returns `404`
- driver returns `408`
- `/driver/find` proves the target never appeared
- debug server reports new errors for the operation window
- sync does not settle when the flow expects it to

Use screenshots only to clarify a real failure, not to guess current state.

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

After login or role switch:

1. normalize to a known screen
2. verify the expected project context
3. dismiss overlays before continuing

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

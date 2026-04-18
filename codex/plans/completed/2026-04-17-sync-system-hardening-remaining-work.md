# Sync System Hardening Remaining Work

Source plan: `.claude/plans/2026-04-16-sync-system-hardening-and-harness.md`
Controlling spec: `.claude/specs/2026-04-16-sync-system-hardening-and-harness-spec.md`
Implementation checklist: `.codex/plans/2026-04-17-sync-system-hardening-implementation-checklist.md`

## Current State

Phases 1 through 6 are implemented and locally verified. The branch contains the
local Supabase fixture, harness driver, correctness matrix, logging/Sentry event
pipeline, property-based concurrency suite, soak driver, targeted sync hardening,
local performance proof, staging CI wiring, schema hash script, performance
regression script, and shared GitHub auto-issue policy.

The remaining work is Phase 7 completion plus a corrected product-intent pass
that was missed when the fixture checklist was interpreted as generic FK breadth.
Most Phase 7 work is external staging and operations work, but the final sweep
found repo-side gaps that should be closed before declaring the spec fully
implemented.

## Ship Blockers

### 1. Correct the daily-entry location/activity model

Status: open product-intent gap.

The earlier fixture checklist said "at least 2 locations per project" and treated
locations mostly as FK coverage. That missed the actual intent. Locations are
not just project metadata; they are the way the daily entry's Activities tab is
organized.

Required behavior:

- Remove the entry-level location system from the Header tab/card. Header should
  not be the main place users manage locations.
- In the entry wizard Activities tab, let users record separate activity text
  under each location, for example:

```text
- Location 1

  This is the activities section for location 1.

- Location 2

  This is the activities section for location 2.
```

- On tablet, the Activities tab should take more of the left-side screen area so
  the UI uses currently empty horizontal space.
- Entry preview, review, list cards, and PDFs should render activities grouped
  by location, not as a flat `"Location - text"` line per item.
- Export output should preserve the location header followed by that location's
  activities.
- Legacy plain-text `daily_entries.activities` should still render safely.

Relevant current code:

- `lib/features/entries/data/models/daily_entry.dart` already supports
  JSON-encoded activity items with `locationName`, but display currently
  flattens them as `Location - text`.
- `lib/features/entries/presentation/controllers/pdf_data_builder_helpers.dart`
  already detects JSON activities, but must be verified against the exact
  location-heading export shape.
- `lib/features/entries/presentation/widgets/entry_header_card.dart` and
  `entry_header_location_weather_row.dart` still make location a header concern.
- `lib/features/entries/presentation/widgets/entry_editor_body.dart` and
  `entry_activities_section.dart` are the likely UI ownership points.

Tests to add/update:

- Activity serialization unit test for multiple locations with grouped output.
- Widget test proving the Activities section shows per-location editors.
- Tablet-width widget/golden-style test proving the Activities pane uses the
  available left-side space.
- PDF data builder test proving grouped location headers and activities export
  in the intended order.
- Regression test proving the header no longer owns entry location selection.

### 2. Stop weather from re-appending/re-fetching on every entry load

Status: open product bug.

Current behavior described by the user: every time the entry wizard loads,
whether creating a new entry, editing an entry, or viewing an old entry, weather
reloads and appends. The desired behavior is: fetch weather one time when
creating an entry, then preserve it unless the user manually edits it.

Relevant current code:

- `lib/features/entries/presentation/screens/entry_editor_state_mixin.dart`
  calls `autoFetchWeather()` after `loadEntryData()` whenever
  `result.entry.weather == null`.
- `autoFetchWeather()` guards only on `current.weather != null`; it does not
  distinguish new-entry creation from editing/viewing an existing entry.

Required behavior:

- Auto-fetch weather only for a newly created entry.
- Do not auto-fetch when opening an existing entry, editing an old entry, or
  viewing an entry with missing weather.
- Do not append duplicate weather text or duplicate weather-derived data.
- Manual weather edit remains available.

Tests to add/update:

- New-entry load calls auto weather exactly once.
- Existing entry load with `weather == null` does not auto-fetch.
- Reopening an entry after weather was set does not append or modify weather.
- Editing/viewer mode does not auto-fetch.

### 3. Fix project import confidence-screen Import button

Status: open product bug.

Current reported behavior: after project import says it succeeded and the user
is on the confidence screen, clicking `Import` does nothing.

Required behavior:

- The confidence screen `Import` button must call the real import/apply path.
- The button must show actionable disabled/loading/error states instead of
  appearing clickable with no result.
- Successful import must create the project graph and navigate/confirm in a way
  the user can observe.
- Failure must surface an error and leave enough state for retry.

Likely code areas:

- `lib/features/pdf/presentation/controllers/pdf_import_controller.dart`
- `lib/features/pdf/presentation/controllers/mp_import_controller.dart`
- import preview/confidence widgets under `lib/features/pdf/presentation/`
- project creation/import service/provider code under `lib/features/projects/`

Tests to add/update:

- Controller test proving the confidence-screen import action invokes apply.
- Widget test proving tapping `Import` changes state and reports success/failure.
- Integration/harness test proving imported project data appears after import
  and sync.

### 4. Scale the Docker/staging fixture to realistic project data

Status: open fixture/spec correction.

The earlier fixture minimums were too small and did not match the intended
project-creation/import load. Correct the fixture targets for local Docker and
staging.

Per project target:

- Contractors: 4 per project.
- Equipment: 5 rows per contractor, therefore 20 equipment rows per project.
- Bid items: 50 per project. The user meant "bid items", not "bit items".
- Personnel types: at least 4-5 per project. Two is wrong because contractor
  creation already gives three default personnel types.
- Daily entries: at least 20 per project.
- Photos: at least 1 photo per daily entry.
- Locations: create enough meaningful locations to exercise location-grouped
  activities, but do not treat "different locations per project" as the core
  requirement. The core requirement is activities grouped under locations.

Fixture intent:

- The seed should stress realistic project graph size, import scale, sync
  payload size, and UI/export behavior.
- Daily entries should contain activities grouped by location, not a single flat
  activity string.
- Photos should reference daily entries and, where supported, locations.
- Keep deterministic IDs and deterministic storage paths.
- Keep the fixture usable in local Docker and staging.

Tests/validators to add/update:

- Update `scripts/validate_harness_fixture_parity.py` so it verifies the larger
  fixture counts.
- Add fixture SQL probes for contractor/equipment/bid item/personnel/daily
  entry/photo counts.
- Re-run local reset and performance proof after scaling; the 2-second ceiling
  must be measured against this larger intended fixture, not the smaller FK
  smoke fixture.
- Update the staging performance baseline only after the larger fixture is
  accepted.

### 5. Add form coverage to the fixture and daily-entry harness

Status: open fixture/spec correction.

Forms are doable through Docker. The schema supports this through
`form_responses.entry_id`, which can reference `daily_entries.id`, plus
`form_responses.project_id` for project-scoped sync/RLS. The earlier fixture
did not seed entry-linked form responses, so the daily-entry graph did not
exercise forms.

Required fixture behavior:

- Seed or reuse the relevant `inspector_forms` definitions for the supported
  form types.
- Seed `form_responses` attached to daily entries through `entry_id`.
- Cover the current form set called out by the sync spec: 0582B, 1174R, 1126,
  and IDR.
- Ensure form responses sync with the project and entry graph.
- Ensure form exports, if seeded or generated by tests, remain linked to project
  and entry where applicable.

Tests/validators to add/update:

- Matrix/harness test proving entry-linked `form_responses` are visible to
  authorized roles and hidden from unauthorized roles.
- Export test proving forms attached to entries are preserved through daily-entry
  export flows where the product expects that.
- Fixture parity validator checks at least one entry-linked response per form
  type.

### 6. Retarget the nightly 15-minute soak to staging

Status: open repo-side gap.

The spec requires both the 10-minute CI soak and the 15-minute nightly soak to
run green against a dedicated staging Supabase project before the ship bar can
close. The quality gate 10-minute soak is already staged, but
`.github/workflows/nightly-soak.yml` still runs:

- job name `local-soak`
- `tools/supabase_local_reset.ps1`
- step name `Run 15-minute local soak`
- no `STAGING_SUPABASE_URL` / `STAGING_SUPABASE_ANON_KEY` dart defines

Next implementation steps:

- Rename the workflow job/steps so they describe staging, not local Docker.
- Remove the local Supabase reset from the nightly path.
- Point `test/harness/soak_nightly_15min_test.dart` at
  `STAGING_SUPABASE_URL` and `STAGING_SUPABASE_ANON_KEY`, matching the quality
  gate pattern.
- Keep service-role secrets out of every Flutter-invoking nightly step.
- Only increment `AUTO_ISSUE_SOAK_GREEN_STREAK` after the staging nightly soak
  passes.
- Update the implementation checklist after this is fixed.

Acceptance gate:

```powershell
python -m unittest discover -s test\scripts -p "*_test.py"
```

Then run the nightly workflow manually with staging secrets and confirm the soak
metrics artifact is produced from staging.

### 7. Resolve the staging harness fixture credential strategy

Status: open design/implementation gap.

The local seed is intentionally marked `LOCAL DOCKER ONLY`, and its known
password `HarnessPass!1` is explicitly documented as never reaching staging or
prod. The staging CI harness currently uses the same hard-coded password through
`HarnessAuthConfig.password`, so staging cannot honestly run unless one of these
is true:

- staging is provisioned with the same local-only password, violating the seed
  warning, or
- the harness is updated to accept a staging-only password secret.

Next implementation steps:

- Add a `HARNESS_SUPABASE_PASSWORD` dart define to `HarnessAuthConfig`, defaulting
  to `HarnessPass!1` only for local Docker.
- Pass `HARNESS_SUPABASE_PASSWORD` from a GitHub secret to staging soak and
  staging performance steps.
- Create a staging fixture provisioning path that applies the same deterministic
  company/user/project/assignment IDs but uses the staging-only password. This
  should be a guarded staging operation, not `tools/supabase_local_reset.ps1`.
- Document the staging fixture reset/seed command in
  `docs/sync-phase7-staging-ops.md`.
- Add/update tests so the local default still works and staging can override the
  password without exposing service-role credentials to Flutter.

Acceptance gates:

```powershell
flutter test test\harness\harness_auth_helpers_test.dart
python scripts\validate_harness_fixture_parity.py
```

Then prove a staging sign-in for `admin@harness.test` and
`inspector1@harness.test` using the staging-only password.

### 8. Enforce the auto-issue 24-hour rate limit across closed issues

Status: open repo-side gap.

`scripts/github_auto_issue_policy.py` groups and updates open issues by
fingerprint, and it refuses raw `userIds`, but it does not yet enforce the full
spec rule of "1 issue per fingerprint per 24 hours" after an issue was closed.
If no open issue exists, the current `--apply` path can create a new issue for a
recently closed fingerprint.

Next implementation steps:

- Extend `apply_decisions()` to search recent closed issues for the same
  `auto-fingerprint` marker before creating a new one.
- If a same-fingerprint issue was closed less than 24 hours ago, emit/update a
  `noop` decision or comment without creating a new issue.
- Add unit coverage for:
  - recently closed issue suppresses create
  - closed issue older than 24 hours allows create
  - existing open issue still updates
- Keep the script stdlib-only apart from shelling out to `gh`.

Acceptance gate:

```powershell
python -m unittest test\scripts\github_auto_issue_policy_test.py
```

Then run one synthetic `--apply` pass in a test repo or dry repository context
before enabling it as a live auto-filer.

### 9. Provision and seed staging safely

Status: external ops blocker, with repo docs to update after the credential
strategy is resolved.

Required external work:

- Provision a dedicated staging Supabase project on the Pro plan.
- Record owner, region, and cost attribution in the ship-bar PR.
- Populate GitHub Actions secrets:
  - `STAGING_SUPABASE_DATABASE_URL`
  - `STAGING_SUPABASE_URL`
  - `STAGING_SUPABASE_ANON_KEY`
  - `STAGING_SUPABASE_SERVICE_ROLE_KEY`
  - proposed: `HARNESS_SUPABASE_PASSWORD`
- Populate matching Codemagic environment variables if Codemagic will run any
  staging-adjacent validation.
- Apply migrations to staging.
- Seed deterministic harness fixture data with staging-only credentials and the
  corrected realistic project graph described above.
- Verify staging sign-in for admin and inspector personas.
- Verify `scripts/hash_schema.py` reports matching local/staging schema hashes.

Acceptance gates:

```powershell
python scripts\hash_schema.py --db-url "local=postgresql://postgres:postgres@127.0.0.1:54322/postgres" --db-url "staging=$env:STAGING_SUPABASE_DATABASE_URL"
```

Plus staging sign-in smoke for `admin@harness.test` and
`inspector1@harness.test`.

### 10. Verify Supabase Log Drains into Sentry

Status: external ops blocker.

Phase 4 added the custom Log Drain sink and local filter tests, but the spec is
not fully closed until staging forwards `postgres_logs`, `auth_logs`, and
`edge_logs` into Sentry and the operator can see them there.

Next steps:

- Configure the staging Supabase Log Drain endpoint selected in Phase 4.
- Confirm Sentry receives at least one event from each source:
  `postgres_logs`, `auth_logs`, and `edge_logs`.
- Run or CI-execute the Deno test for
  `supabase/functions/_shared/log_drain_sink.test.ts`; it was not run locally
  because Deno was not installed in the workspace.
- Record Sentry project/event links or screenshots in the ship-bar PR.

Acceptance gate:

```powershell
deno test supabase/functions/_shared/log_drain_sink.test.ts
```

### 11. Configure Sentry to GitHub repository dispatch

Status: external ops blocker.

The receiving workflow exists at `.github/workflows/sentry-auto-issue.yml`, but
the Sentry-side webhook/GitHub App configuration still has to be proven live.

Next steps:

- Configure Sentry to dispatch `repository_dispatch` events of type
  `sentry-event`.
- Confirm payload normalization hashes raw Sentry user IDs before invoking
  `scripts/github_auto_issue_policy.py`.
- Send one synthetic fatal event and verify it creates or updates a GitHub issue
  with only hashed user identifiers.
- Send one warning event and verify it stays digest-only.

Acceptance gate:

Run `.github/workflows/sentry-auto-issue.yml` through `workflow_dispatch`, then
through real `repository_dispatch`, and verify the issue behavior.

### 12. Run staging performance proof

Status: external staging gate.

Local Docker proof is recorded in `docs/sync-phase6-profiling.md` and
`scripts/perf_baseline.json`:

- cold full sync median: 471 ms
- warm quick sync median: 138 ms
- ceiling: 2000 ms

The spec requires the ship-bar performance proof against staging, not just local
Docker.

Next steps:

- Run `test/harness/sync_performance_local_test.dart` against staging with the
  staging URL, anon key, and staging harness password.
- Record median of at least three cold full-sync runs.
- Confirm cold full sync is `<= 2000 ms`.
- Confirm warm foreground unblock is `<= 500 ms`.
- Confirm the performance regression script passes against
  `scripts/perf_baseline.json`.
- Record the numbers in the ship-bar PR and update
  `docs/sync-phase7-staging-ops.md` if needed.

Acceptance gate:

```powershell
pwsh -File tools\run_tests_capture.ps1 test\harness\sync_performance_local_test.dart --dart-define=RUN_LOCAL_HARNESS=true --dart-define=STAGING_SUPABASE_URL=$env:STAGING_SUPABASE_URL --dart-define=HARNESS_SUPABASE_URL=$env:STAGING_SUPABASE_URL --dart-define=HARNESS_SUPABASE_ANON_KEY=$env:STAGING_SUPABASE_ANON_KEY --dart-define=HARNESS_SUPABASE_PASSWORD=$env:HARNESS_SUPABASE_PASSWORD
python scripts\check_perf_regression.py --baseline scripts\perf_baseline.json --actual build\perf\sync-performance.json
```

### 13. Prove three consecutive green staging soaks

Status: external CI history gate.

The spec requires:

- 10-minute CI soak green against staging for three consecutive sync-touching PR
  runs.
- 15-minute nightly soak green against staging for three consecutive nights.
- Nightly auto-issue policy only armed after that three-green-night stability
  period.

Next steps:

- After the nightly staging retarget is fixed, manually run the nightly workflow
  once to validate secrets and artifact output.
- Let three scheduled nightly runs pass.
- Confirm `AUTO_ISSUE_SOAK_GREEN_STREAK >= 3`.
- Confirm `AUTO_ISSUE_SOAK_STABILITY_FLAG=armed`.
- Confirm failed nightly events after arming route through the shared
  auto-issue policy.

Acceptance evidence:

- Links to three green quality-gate runs.
- Links to three green nightly runs.
- Repository variable values after the third nightly pass.

### 14. Run a full test PR through the persistent gates

Status: external CI verification blocker.

Before the plan is fully closed, run the new workflows end-to-end in a test PR.

Required checks:

- Staging schema hash gate passes on normal state.
- Staging schema hash gate fails on synthetic local/staging drift.
- 10-minute staging soak passes and uploads `build/soak`.
- Staging sync performance measurement passes and uploads `build/perf`.
- `scripts/check_perf_regression.py` fails on a seeded +15% regression and
  passes on a seeded +5% delta.
- Shared auto-issue policy handles synthetic lint, Sentry, and nightly-soak
  events with the expected create/update/digest/close behavior.
- Service-role preflight proves no service-role secret is available to Flutter
  steps.

Acceptance evidence:

- Test PR link.
- Failed synthetic-drift run link.
- Successful final rerun link.
- Artifacts for soak and performance metrics.

### 15. Confirm all five ship-bar conditions simultaneously

Status: external release gate.

Do not tag until all five are true at the same commit:

- Correctness matrix green.
- All five Phase 6 defects fixed.
- 10-minute staging CI soak and 15-minute staging nightly soak stable.
- Staging cold full sync `<= 2000 ms`.
- Logging/Sentry/GitHub auto-issue pipeline live, with performance gate wired.

Acceptance evidence:

- Ship-bar PR checklist with links to the exact runs/events.
- Staging performance numbers.
- Sentry Log Drain proof.
- Sentry-to-GitHub issue proof.
- Green-streak variable proof.

### 16. Cut the pre-alpha-eligible tag

Status: final external release marker.

After the ship bar is true, tag the exact commit as pre-alpha eligible. The
delivery mechanism is outside this spec, but the tag is the durable marker that
this sync hardening plan has completed.

## Non-Blocking Cleanup

- Remove the unreachable legacy inline lint issue-management shell block that
  remains after `exit 0` in `.github/workflows/quality-gate.yml`. Behavior is
  already delegated to `scripts/github_auto_issue_policy.py`, but removing the
  dead block will make the workflow easier to audit.
- Consider renaming `RUN_LOCAL_HARNESS` to a neutral `RUN_SYNC_HARNESS` in a
  later cleanup. It currently controls both local and staging harness execution,
  which is confusing but not itself a behavior failure.
- Update `.codex/plans/2026-04-17-sync-system-hardening-implementation-checklist.md`
  once the nightly staging gap, credential strategy, and rate-limit fix are
  complete.

## Suggested Next Session Order

1. Fix the product-intent gaps: location-grouped Activities tab/export, weather
   fetch-on-create-only, and project import confidence-screen Import action.
2. Scale the local Docker fixture to the corrected realistic graph and add
   entry-linked form responses.
3. Re-run local reset, fixture validators, matrix, soak, and performance proof
   against the larger fixture.
4. Implement the staging harness password override.
5. Implement a safe staging fixture provisioning path and document it.
6. Retarget `.github/workflows/nightly-soak.yml` to staging.
7. Add the 24-hour closed-issue rate-limit behavior and tests to
   `scripts/github_auto_issue_policy.py`.
8. Run local script/unit gates.
9. Provision staging secrets/resources.
10. Run staging sign-in smoke, schema hash, 10-minute soak, nightly soak, and
   staging performance proof.
11. Configure and prove Log Drains plus Sentry repository dispatch.
12. Run the test PR gates and collect evidence.
13. Confirm the five ship-bar conditions and cut the tag.

## Last Known Local Evidence

These gates passed before this remaining-work sweep:

- `pwsh -File tools\supabase_local_reset.ps1`
- `flutter test test\harness\harness_sync_matrix_local_test.dart --dart-define=RUN_LOCAL_HARNESS=true`
- `flutter test test\features\sync\property\sync_invariants_property_test.dart test\harness\glados_invariants_test.dart`
- `flutter test test\features\sync\characterization`
- `flutter test test\harness\sync_performance_local_test.dart --dart-define=RUN_LOCAL_HARNESS=true`
- `pwsh -File scripts\soak_local.ps1 -DurationMinutes 10 -UserCount 20`
- `python -m unittest discover -s test\scripts -p "*_test.py"`
- `python scripts\hash_schema.py --db-url local=postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- `python scripts\validate_sync_adapter_registry.py`
- `python scripts\verify_database_schema_platform_parity.py`
- `python scripts\validate_harness_fixture_parity.py`
- `pwsh -File scripts\audit_logging_coverage.ps1`
- `pwsh -File .claude\hooks\checks\run-analyze.ps1`
- `pwsh -File .claude\hooks\checks\run-custom-lint.ps1`

The remaining items above are not local proof gaps for Phases 1 through 6. They
are the final Phase 7 staging, observability, CI-history, and release gates.

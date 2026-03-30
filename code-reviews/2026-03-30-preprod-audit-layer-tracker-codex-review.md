# Per-Layer Audit Tracker

Date: 2026-03-30
Mode: read-only reporting only
Goal: run additional fresh-eyes sweeps one layer at a time and append only verified findings to the existing layer reports

## Fresh-Pass Protocol

For each layer pass:

1. Reload only this tracker, the audit index, and the target layer report.
2. Re-read only the code, tests, git history, and analyzer signals relevant to that layer.
3. Verify:
   - core behavior and wiring for that layer
   - dead code or stale references
   - unfinished recent work that should not be misclassified as dead
   - unused imports, unused members, and hygiene debt
   - duplicated logic or duplicated entry points
   - test coverage and tooling gaps relevant to that layer
4. Append findings to the existing layer report.
5. Do not clean up code in this phase.

Note: I cannot force platform compaction on demand, but I can emulate the intended "fresh set of eyes" by isolating each pass to one layer and reloading only the relevant local context before reviewing it.

## Layer TODO

- [x] Wiring / Startup / Routing
  Report: `2026-03-30-preprod-audit-wiring-routing-codex-review.md`
  Scope: composition root, app startup, router contract, route guards, app-wide bootstrap duplication

- [x] Data / Database / Sync
  Report: `2026-03-30-preprod-audit-data-sync-codex-review.md`
  Scope: schema, migrations, datasources, repositories, sync engine/bootstrap, local/remote boundary integrity

- [x] Providers / State
  Report: `2026-03-30-preprod-audit-providers-state-codex-review.md`
  Scope: provider ordering, notifier ownership, cross-provider coupling, state-layer dead code and hygiene

- [ ] Services / Integrations
  Report: `2026-03-30-preprod-audit-services-integrations-codex-review.md`
  Scope: logging, telemetry, background services, PDF/image integrations, support/help integrations

- [ ] Features / Business Logic
  Report: `2026-03-30-preprod-audit-features-business-logic-codex-review.md`
  Scope: form infrastructure, feature completeness, domain-model drift, hidden special cases

- [ ] Screens / Navigation UX
  Report: `2026-03-30-preprod-audit-screens-navigation-codex-review.md`
  Scope: screen behavior, user flows, stale UI surfaces, presentation dead code, navigation consistency

- [ ] Shared UI / Cross-Cutting Hygiene
  Report: `2026-03-30-preprod-audit-shared-ui-hygiene-codex-review.md`
  Scope: theme tokens, shared utilities, testing keys, deprecated compatibility layers, cross-cutting hygiene

- [ ] Tests / Tooling / Quality Gates
  Report: `2026-03-30-preprod-audit-tests-tooling-codex-review.md`
  Scope: coverage gaps, stale fixtures, CI gates, skips/suppressions, misleading test surfaces

## Current Pass

- Completed: Wiring / Startup / Routing
- Completed: Data / Database / Sync
- Completed: Providers / State
- Next recommended pass: Services / Integrations

## Pass Log

- Wiring / Startup / Routing
  Result: completed additional fresh scoped sweep
  New additions: split composition root, duplicated consent/auth entrypoint bootstrap, missing parity tests between `main.dart` and `main_driver.dart`

- Data / Database / Sync
  Result: completed additional fresh scoped sweep
  New additions: schema verifier only repairs missing columns, `SyncOrchestrator` still depends on post-construction setter wiring, `updateLastSyncedAt()` ignores its `userId` parameter, schema repair ownership is split across migrations and post-open verification, and the report now documents that existing sync tests mostly bypass the real production bootstrap path

- Providers / State
  Result: completed additional fresh scoped sweep
  New additions: provider-layer write guards are inconsistent and often patched after construction, sync/auth listener ownership lacks symmetric teardown in the provider layer, and the report now documents that provider tests and the test harness bypass meaningful parts of the real production provider graph

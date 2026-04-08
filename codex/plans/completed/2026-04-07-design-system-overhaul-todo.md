# UI Design System Branch Audit TODO

**Date:** 2026-04-07
**Branch intent:** `ui-design-system-refactor`
**Audit source:** working branch + structural audit + sync-surface verification + `flutter analyze` + `dart run custom_lint`
**Status:** Launch-candidate

## Current Audit Snapshot

- [x] `flutter analyze` is clean.
- [x] `dart run custom_lint` is clean.
- [x] No UI/design-system/presentation artifacts over 300 lines remain in audited scope.
- [x] Repeatable line-count audit added at `scripts/audit_ui_file_sizes.ps1`.
- [x] Sync-relevant screen contracts, flow definitions, and diagnostics payloads are present and wired.
- [x] Sync-critical UI tests pass for dashboard and conflict viewer surfaces.
- [x] No ignore-based suppression tricks were added in this refactor path.

## Completed Structural Refactors

- [x] Break up the former god providers/controllers into focused modules.
  - [x] `AuthProvider`
  - [x] `ProjectProvider`
  - [x] `ContractorComparisonProvider`
  - [x] `AppConfigProvider`
  - [x] `SyncProvider`
  - [x] `EntryQuantityProvider`
  - [x] `ContractorEditingController`
  - [x] `TodoProvider`
  - [x] `HomeScreen`

- [x] Re-audit extracted helpers so the 300-line rule was not bypassed sideways.
- [x] Preserve subclassable/provider entrypoints needed by tests and sync-facing callers.

## Sync / Driver Exposure Verification

- [x] `screen_registry.dart` includes sync/settings/quantities-relevant screens needed for harness bootstrapping.
- [x] `screen_contract_registry.dart` exposes stable screen/root/action/state contracts for sync-relevant UI.
- [x] `driver_diagnostics_handler.dart` exposes `/diagnostics/screen_contract` with route + contract metadata in one payload.
- [x] `flow_registry.dart` retains declarative sync/settings/quantities verification flows.
- [x] Sync-critical UI tests pass:
  - [x] `test/features/sync/presentation/screens/sync_dashboard_screen_test.dart`
  - [x] `test/features/sync/presentation/screens/conflict_viewer_screen_test.dart`

## Remaining Merge Checklist

- [ ] Final manual product decision: call the branch “live” and merge.
- [ ] Optional: run broader integration/driver coverage beyond the targeted sync screen tests if you want extra confidence before merge.

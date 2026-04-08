# Sync Orchestrator Refactor TODO

Date: 2026-04-06
Status key: `[ ]` pending, `[-]` in progress, `[x]` done

## Active Queue

[x] Finalize extraction seams and test plan for `pull_handler`, `push_handler`,
    and `integrity_checker`
[x] Add the refactor plan to `.codex/PLAN.md`
[x] Wait for parallel review notes from the pull/push explorers and fold in any
    missing risks

## Pull Refactor

[x] Add or tighten characterization tests for pull cursor writes
[x] Add a negative rescue-path test so failed pay-app dependency rescue cannot
    look like success
[x] Extract `PullDependencyRescuer`
[x] Extract `PullFileCacheReconciler`
[x] Extract `PullRecordApplier`
[x] Reduce `PullHandler` to page iteration, callbacks, and cursor management
[x] Rerun `pull_handler_contract_test.dart`

## Push Refactor

[x] Add characterization coverage for out-of-scope skip behavior
[x] Add characterization coverage for LWW skip accounting if still weak
[x] Extract `PushChangePlanner`
[x] Extract `PushRecordExecutor`
[x] Reduce `PushHandler` to orchestration, retry handling, and progress updates
[x] Rerun `push_handler_contract_test.dart`

## Integrity / Maintenance

[x] Decide whether `purgeOrphans` moves into an `OrphanPurger` now or stays put
    under the April 4 refactor constraints
[x] If extracted, add direct tests for pulling-flag restoration and scoped
    orphan purge behavior
[x] Re-run integrity and maintenance tests

## Verification

[x] Run `flutter analyze`
[x] Run focused sync suite:
    `pull_handler_contract_test.dart`
    `push_handler_contract_test.dart`
    `file_sync_handler_test.dart`
    `file_sync_handler_contract_test.dart`
    `enrollment_handler_test.dart`
    `integrity_checker_test.dart`
    `integrity_integration_test.dart`
    `maintenance_handler_test.dart`
    `orphan_scanner_test.dart`
    `cascade_soft_delete_test.dart`
    `sync_schema_test.dart`
[x] Run focused pay-app/export slice if sync changes touch pay-app behavior
[ ] Run Windows runtime smoke on isolated driver/debug ports
    Blocked by external `sentry-native` fetch failure (`chromium.googlesource.com` 429)
[x] Run S21 runtime smoke on isolated driver/debug ports
[x] Record any remaining unproven sync/pay-app acceptance gaps after runtime checks
[ ] Restore incidental generated Windows files before final handoff

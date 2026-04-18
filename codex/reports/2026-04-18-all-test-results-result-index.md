# Sync Soak Result Index

- Generated UTC: 2026-04-18T15:39:19.8685287Z
- Input root: .claude\test-results
- Runs: 165
- Passed: 76
- Failed: 89

## Failure Groups

| Classification | Count | Latest Run | Queue | Runtime Errors |
| --- | ---: | --- | --- | ---: |
| change_log_proof_failed | 3 | 20260418-s21-cleanup-only-replay-accepted-ledgers-after-enumeration-fix | drained | 0 |
| cleanup_failed | 5 | 20260417-s21-refactor-daily-entry-only-serial-2 | drained | 0 |
| driver_or_sync_error | 44 | 20260417-144148 |  | 0 |
| queue_not_drained_or_sync_not_observed | 1 | 20260417-144220 |  | 0 |
| runtime_log_error | 12 | 20260417-s21-strictlog-stablekey-all-modes | drained | 1 |
| unknown_failure | 3 | 20260417-1916-storage-proof-rerun | drained | 1 |
| unprocessed_change_log_rows | 3 | 20260417-s21-strictlog-cleanup-sync-rerun | residue_detected | 0 |
| widget_tap_not_found | 3 | 20260418-s21-mdot1126-expanded-after-direct-field-entry | drained | 0 |
| widget_wait_timeout | 18 | 20260417-s21-refactor-sync-only | not_collected | 0 |

## Runs

| Result | Flow | Run | Queue | Runtime | Logs | Direct Sync | Summary |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| FAIL |  | 20260417-144148 |  | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-144148/summary.json |
| PASS |  | 20260417-150725 |  | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-150725/summary.json |
| FAIL |  | 20260417-181106-device | drained | 2 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-181106-concurrent/device-sync/summary.json |
| FAIL |  | 20260417-182214-device | drained | 2 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-182214-concurrent/device-sync/summary.json |
| FAIL |  | 20260417-182214-s21-daily-smoke | drained | 1 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-182214-s21-daily-smoke/summary.json |
| PASS |  | 20260417-182642-s21-daily-smoke | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-182642-s21-daily-smoke/summary.json |
| FAIL |  | 20260417-182745-device-all-modes-smoke | residue_detected | 2 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-182745-device-all-modes-smoke/summary.json |
| PASS |  | 20260417-182745-drain-after-sync-button-race | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-182745-drain-after-sync-button-race/summary.json |
| FAIL |  | 20260417-144220 |  | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-144220/summary.json |
| FAIL |  | 20260417-183010-device-all-modes-smoke | drained | 2 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-183010-device-all-modes-smoke/summary.json |
| PASS |  | 20260417-184056-drain-after-aborted-mutation | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-184056-drain-after-aborted-mutation/summary.json |
| FAIL |  | 20260417-184152-device-all-modes-smoke | drained | 2 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-184152-device-all-modes-smoke/summary.json |
| PASS |  | 20260417-184459-drain-after-manual-activity-proof | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-184459-drain-after-manual-activity-proof/summary.json |
| FAIL |  | 20260417-184549-device-all-modes-smoke | residue_detected | 2 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-184549-device-all-modes-smoke/summary.json |
| PASS |  | 20260417-185007-drain-before-scroll-target-rerun | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-185007-drain-before-scroll-target-rerun/summary.json |
| FAIL |  | 20260417-185054-device-all-modes-smoke | residue_detected | 2 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-185054-device-all-modes-smoke/summary.json |
| FAIL |  | 20260417-185322-drain-before-quantity-rerun | residue_detected | 1 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-185322-drain-before-quantity-rerun/summary.json |
| FAIL |  | 20260417-183758-device-all-modes-smoke | residue_detected | 2 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-183758-device-all-modes-smoke/summary.json |
| FAIL |  | 20260417-185531-device-all-modes-smoke | residue_detected | 2 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-185531-device-all-modes-smoke/summary.json |
| PASS |  | 20260417-185828-drain-after-guarded-nav-patch | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-185828-drain-after-guarded-nav-patch/summary.json |
| FAIL |  | 20260417-190010-device-all-modes-smoke | residue_detected | 2 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-190010-device-all-modes-smoke/summary.json |
| FAIL |  | 20260417-190258-device-all-modes-smoke | residue_detected | 2 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-190258-device-all-modes-smoke/summary.json |
| FAIL |  | 20260417-1916-storage-proof-rerun | drained | 1 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-1916-storage-proof-rerun/summary.json |
| PASS |  | 20260417-1918-drain-after-process-restart | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-1918-drain-after-process-restart/summary.json |
| FAIL |  | 20260417-1919-device-all-modes-smoke | residue_detected | 1 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-1919-device-all-modes-smoke/summary.json |
| FAIL |  | 20260417-1922-device-all-modes-smoke | residue_detected | 2 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-1922-device-all-modes-smoke/summary.json |
| PASS | sync-only | 20260417-s21-daily-entry-ledger-cleanup-sync | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-daily-entry-ledger-cleanup-sync/summary.json |
| PASS | sync-only | 20260417-s21-daily-entry-serial-2-ledger-recovery-sync | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-daily-entry-serial-2-ledger-recovery-sync/summary.json |
| PASS |  | 20260417-190205-drain-before-photo-fallback-rerun | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-190205-drain-before-photo-fallback-rerun/summary.json |
| PASS | daily-entry-ledger-recovery | 20260417-s21-daily-entry-serial-2-ui-ledger-recovery | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-daily-entry-serial-2-ui-ledger-recovery/summary.json |
| PASS |  | 20260417-s21-post-cleanup-strict-drain | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-post-cleanup-strict-drain/summary.json |
| FAIL |  | 20260417-s21-postpatch-all-modes-rerun | residue_detected | 1 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-postpatch-all-modes-rerun/summary.json |
| FAIL |  | 20260417-s21-postpatch-all-modes | residue_detected | 1 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-postpatch-all-modes/summary.json |
| PASS |  | 20260417-s21-postpatch-drain | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-postpatch-drain/summary.json |
| PASS |  | 20260417-s21-postpatch-photo-save-drain | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-postpatch-photo-save-drain/summary.json |
| PASS | daily-entry-only | 20260417-s21-refactor-daily-entry-only-rerun | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only-rerun/summary.json |
| FAIL | daily-entry-only | 20260417-s21-refactor-daily-entry-only-serial-2 | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only-serial-2/summary.json |
| FAIL |  | 20260417-s21-fullscreen-notransition-strict-all-modes | residue_detected | 1 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-fullscreen-notransition-strict-all-modes/summary.json |
| PASS | daily-entry-only | 20260417-s21-refactor-daily-entry-only-serial-2b | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only-serial-2b/summary.json |
| PASS | daily-entry-only | 20260417-s21-refactor-daily-entry-only-serial-3 | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only-serial-3/summary.json |
| PASS | daily-entry-only | 20260417-s21-refactor-daily-entry-only-serial-4 | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only-serial-4/summary.json |
| FAIL | daily-entry-only | 20260417-s21-refactor-daily-entry-only | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-daily-entry-only/summary.json |
| PASS | sync-only | 20260417-s21-refactor-sync-only-rerun-2 | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-sync-only-rerun-2/summary.json |
| PASS | sync-only | 20260417-s21-refactor-sync-only-rerun-3 | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-sync-only-rerun-3/summary.json |
| PASS | sync-only | 20260417-s21-refactor-sync-only-rerun | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-sync-only-rerun/summary.json |
| PASS | sync-only | 20260417-s21-refactor-sync-only-serial-2 | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-sync-only-serial-2/summary.json |
| PASS | sync-only | 20260417-s21-refactor-sync-only-serial-3 | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-sync-only-serial-3/summary.json |
| FAIL | sync-only | 20260417-s21-refactor-sync-only | not_collected | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-refactor-sync-only/summary.json |
| PASS |  | 20260417-s21-shell-notransition-all-modes | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-shell-notransition-all-modes/summary.json |
| PASS |  | 20260417-s21-shell-notransition-drain | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-shell-notransition-drain/summary.json |
| PASS |  | 20260417-s21-shell-stablekey-drain | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-shell-stablekey-drain/summary.json |
| FAIL |  | 20260417-s21-strictlog-cleanup-sync-rerun | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-strictlog-cleanup-sync-rerun/summary.json |
| FAIL |  | 20260417-s21-strictlog-cleanup-sync | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-strictlog-cleanup-sync/summary.json |
| FAIL |  | 20260417-s21-strictlog-stablekey-all-modes | drained | 1 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260417-s21-strictlog-stablekey-all-modes/summary.json |
| PASS | daily-entry-only | 20260418-s10-state-machine-combined-initial-daily-entry-only | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-combined-initial/phases/daily-entry-only/summary.json |
| PASS | photo-only | 20260418-s10-state-machine-combined-initial-photo-only | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-combined-initial/phases/photo-only/summary.json |
| PASS | quantity-only | 20260418-s10-state-machine-combined-initial-quantity-only | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-combined-initial/phases/quantity-only/summary.json |
| PASS | combined | 20260418-s10-state-machine-combined-initial | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-combined-initial/summary.json |
| PASS | contractors-only | 20260418-s10-state-machine-contractors-only-initial | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-contractors-only-initial/summary.json |
| PASS | daily-entry-only | 20260418-s10-state-machine-daily-entry-only-initial | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-daily-entry-only-initial/summary.json |
| FAIL | combined | 20260418-s21-state-machine-combined-initial |  | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-initial/summary.json |
| PASS | quantity-only | 20260418-s10-state-machine-quantity-only-initial | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-quantity-only-initial/summary.json |
| PASS | sync-only | 20260418-s10-state-machine-sync-only-preexisting-drain | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-sync-only-preexisting-drain/summary.json |
| FAIL | cleanup-only | 20260418-s21-cleanup-only-replay-accepted-ledgers-after-enumeration-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-cleanup-only-replay-accepted-ledgers-after-enumeration-fix/summary.json |
| PASS | cleanup-only | 20260418-s21-cleanup-only-replay-accepted-ledgers-idempotent | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-cleanup-only-replay-accepted-ledgers-idempotent/summary.json |
| FAIL | cleanup-only | 20260418-s21-cleanup-only-replay-accepted-ledgers | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-cleanup-only-replay-accepted-ledgers/summary.json |
| FAIL | sync-only | 20260418-s21-contractors-partial-cleanup-sync-2 | not_collected | 8 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-contractors-partial-cleanup-sync-2/summary.json |
| PASS | sync-only | 20260418-s21-contractors-partial-cleanup-sync | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-contractors-partial-cleanup-sync/summary.json |
| PASS | sync-only | 20260418-s21-mdot1126-failed-draft-cleanup-sync | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-mdot1126-failed-draft-cleanup-sync/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-initial | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-mdot1126-signature-initial/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-nav-fix | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-mdot1126-signature-nav-fix/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-resolver-fix | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-mdot1126-signature-resolver-fix/summary.json |
| PASS | sync-only | 20260418-s21-pre-mdot1126-queue-drain | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-pre-mdot1126-queue-drain/summary.json |
| PASS | daily-entry-only | 20260418-s21-state-machine-combined-final-daily-entry-only | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-final/phases/daily-entry-only/summary.json |
| PASS | photo-only | 20260418-s21-state-machine-combined-final-photo-only | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-final/phases/photo-only/summary.json |
| PASS | quantity-only | 20260418-s21-state-machine-combined-final-quantity-only | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-final/phases/quantity-only/summary.json |
| PASS | combined | 20260418-s21-state-machine-combined-final | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-final/summary.json |
| PASS | daily-entry-only | 20260418-s21-state-machine-combined-initial-daily-entry-only | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-initial/phases/daily-entry-only/summary.json |
| PASS | photo-only | 20260418-s21-state-machine-combined-initial-photo-only | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-initial/phases/photo-only/summary.json |
| PASS | quantity-only | 20260418-s21-state-machine-combined-initial-quantity-only | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-combined-initial/phases/quantity-only/summary.json |
| PASS | contractors-only | 20260418-s21-state-machine-contractors-fourth | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-contractors-fourth/summary.json |
| PASS | photo-only | 20260418-s10-state-machine-photo-only-initial | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s10-state-machine-photo-only-initial/summary.json |
| FAIL | contractors-only | 20260418-s21-state-machine-contractors-initial | drained | 1 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-contractors-initial/summary.json |
| PASS | cleanup-only | 20260418-s21-mdot1126-signed-ledger-cleanup-replay-after-deletedby-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signed-ledger-cleanup-replay-after-deletedby-fix/summary.json |
| PASS | daily-entry-only | 20260418-s21-state-machine-daily-entry-after-quantity-fixes | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-daily-entry-after-quantity-fixes/summary.json |
| PASS | daily-entry-only | 20260418-s21-state-machine-daily-entry-final-single-gate | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-daily-entry-final-single-gate/summary.json |
| FAIL | daily-entry-ledger-recovery | 20260418-s21-state-machine-daily-entry-ledger-recovery | residue_detected | 12 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-daily-entry-ledger-recovery/summary.json |
| PASS | daily-entry-only | 20260418-s21-state-machine-daily-entry-only-after-sentinel-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-daily-entry-only-after-sentinel-fix/summary.json |
| FAIL | daily-entry-only | 20260418-s21-state-machine-daily-entry-only-rerun | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-daily-entry-only-rerun/summary.json |
| FAIL | daily-entry-only | 20260418-s21-state-machine-daily-entry-only | not_collected | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-daily-entry-only/summary.json |
| FAIL | sync-only | 20260418-s21-state-machine-ledger-recovery-sync | not_collected | 11 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-ledger-recovery-sync/summary.json |
| FAIL | contractors-only | 20260418-s21-state-machine-contractors-third | residue_detected | 20 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-contractors-third/summary.json |
| PASS | photo-only | 20260418-s21-state-machine-photo-confidence-2 | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-photo-confidence-2/summary.json |
| FAIL | photo-only | 20260418-s21-state-machine-photo-only-after-dialog-settle-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-photo-only-after-dialog-settle-fix/summary.json |
| FAIL | photo-only | 20260418-s21-state-machine-photo-only-file-stem-fix | drained | 5 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-photo-only-file-stem-fix/summary.json |
| FAIL | photo-only | 20260418-s21-state-machine-photo-only-initial | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-photo-only-initial/summary.json |
| FAIL | photo-only | 20260418-s21-state-machine-photo-only-storage-absence-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-photo-only-storage-absence-fix/summary.json |
| PASS | photo-only | 20260418-s21-state-machine-photo-only-storage-status-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-photo-only-storage-status-fix/summary.json |
| PASS | quantity-only | 20260418-s21-state-machine-quantity-confidence-3 | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-quantity-confidence-3/summary.json |
| PASS | quantity-only | 20260418-s21-state-machine-quantity-final-single-gate | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-quantity-final-single-gate/summary.json |
| PASS | photo-only | 20260418-s21-state-machine-photo-confidence-3 | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-photo-confidence-3/summary.json |
| PASS | quantity-only | 20260418-s21-state-machine-quantity-only-after-autofocus-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-quantity-only-after-autofocus-fix/summary.json |
| FAIL | quantity-only | 20260418-s21-state-machine-quantity-only-after-driver-fix | drained | 8 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-quantity-only-after-driver-fix/summary.json |
| FAIL | quantity-only | 20260418-s21-state-machine-quantity-only-after-modal-fix | drained | 5 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-quantity-only-after-modal-fix/summary.json |
| FAIL | quantity-only | 20260418-s21-state-machine-quantity-only-visible-item | not_collected | 3 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-quantity-only-visible-item/summary.json |
| PASS | sync-only | 20260418-s21-state-machine-sync-only-after-driver-rebuild | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-sync-only-after-driver-rebuild/summary.json |
| PASS | sync-only | 20260418-s21-state-machine-sync-only-after-sentinel-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-sync-only-after-sentinel-fix/summary.json |
| PASS | sync-only | 20260418-s21-state-machine-sync-only-final-single-gate | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-sync-only-final-single-gate/summary.json |
| PASS | sync-only | 20260418-s21-state-machine-sync-only | drained | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-sync-only/summary.json |
| PASS | mdot1126-signature-only | 20260418-s10-mdot1126-signature-regression-with-cleanup-sync-retry | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot1126-signature-regression-with-cleanup-sync-retry/summary.json |
| PASS | sync-only | 20260418-s10-pre-mdot-residue-sync-only | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-pre-mdot-residue-sync-only/summary.json |
| FAIL | quantity-only | 20260418-s21-state-machine-quantity-only-initial | drained | 5 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-quantity-only-initial/summary.json |
| PASS | mdot0582b-only | 20260418-s21-mdot0582b-accepted-initial | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-accepted-initial/summary.json |
| FAIL | mdot0582b-only | 20260418-s21-mdot0582b-after-test-section-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-after-test-section-fix/summary.json |
| FAIL | mdot0582b-only | 20260418-s21-mdot0582b-initial | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-initial/summary.json |
| FAIL | sync-only | 20260418-s21-mdot1126-cleanup-residue-retry-sync | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-cleanup-residue-retry-sync/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-center-visible-tap | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-center-visible-tap/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-direct-field-entry | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-direct-field-entry/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-direct-form-route | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-direct-form-route/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-material-button-target | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-material-button-target/summary.json |
| FAIL | mdot0582b-only | 20260418-s21-mdot0582b-after-remote-json-proof | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-after-remote-json-proof/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-preferred-text-target | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-preferred-text-target/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-rainfall-ui | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-rainfall-ui/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-scroll-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-scroll-fix/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-section-scroll-fallback | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-section-scroll-fallback/summary.json |
| PASS | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-signature-ready-or-nav | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-signature-ready-or-nav/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-starter-rainfall-row | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-starter-rainfall-row/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-status-before-location | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-status-before-location/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-status-key-tap | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-status-key-tap/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-tap-target-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-tap-target-fix/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-text-tap | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-text-tap/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-initial | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-initial/summary.json |
| PASS | cleanup-only | 20260418-s21-mdot1126-fresh-failed-ledger-cleanup-replay-with-sync-retry | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-fresh-failed-ledger-cleanup-replay-with-sync-retry/summary.json |
| PASS | sync-only | 20260418-s21-mdot1126-nav-fix-draft-cleanup-sync | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-nav-fix-draft-cleanup-sync/summary.json |
| PASS | sync-only | 20260418-s21-mdot1126-section-fallback-draft-cleanup-sync | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-section-fallback-draft-cleanup-sync/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-accepted-after-deletedby-fix | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-accepted-after-deletedby-fix/summary.json |
| PASS | mdot1126-signature-only | 20260418-s21-mdot1126-signature-accepted-with-cleanup-sync-retry | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-accepted-with-cleanup-sync-retry/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-body-ready-submit | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-body-ready-submit/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-canonical-form-route | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-canonical-form-route/summary.json |
| PASS | cleanup-only | 20260418-s21-mdot1126-signature-cleanup-only-replay-accepted-ledger | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-cleanup-only-replay-accepted-ledger/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-nav-select-submit | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-nav-select-submit/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-section-fallback | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-section-fallback/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-visible-submit | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-visible-submit/summary.json |
| PASS | sync-only | 20260418-s21-post-s10-mdot-residue-sync-only | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-post-s10-mdot-residue-sync-only/summary.json |
| PASS | sync-only | 20260418-s21-mdot1126-visible-submit-draft-cleanup-sync | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-visible-submit-draft-cleanup-sync/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-auto-advance | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-auto-advance/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-bidirectional-scroll | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-bidirectional-scroll/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-ensure-visible-scroll | residue_detected | 27 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-ensure-visible-scroll/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-expanded-body-sentinel | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-expanded-body-sentinel/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-expanded-sentinel | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-expanded-sentinel/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-first-field-scroll-selection | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-first-field-scroll-selection/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-header-first-selection | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-header-first-selection/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-header-nav-skip | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-header-nav-skip/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-mounted-text | residue_detected | 35 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-mounted-text/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-no-animated-size-keepalive | residue_detected | 27 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-no-animated-size-keepalive/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-open-created-form | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-open-created-form/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-section-headers | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-section-headers/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-section-open-only | residue_detected | 27 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-section-open-only/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-title-fallback-selection | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-title-fallback-selection/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-initial | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-initial/summary.json |
| PASS | sync-only | 20260418-s21-mdot1174r-redscreen-residue-recovery-sync-only | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-redscreen-residue-recovery-sync-only/summary.json |
| PASS | sync-only | 20260418-s21-mdot1174r-residue-recovery-sync-only | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-residue-recovery-sync-only/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-visible-text-only | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-visible-text-only/summary.json |
| FAIL | contractors-only | 20260418-s21-state-machine-contractors-second | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-17/enterprise-sync-soak/20260418-s21-state-machine-contractors-second/summary.json |
| PASS | sync-only | 20260418-s21-post-v61-signature-backlog-sync-only | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-post-v61-signature-backlog-sync-only/summary.json |

## Failure Details

### 20260417-144148

- Flow: 
- Failure class: driver_or_sync_error
- Queue: , blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: No connection could be made because the target machine actively refused it. (127.0.0.1:4948)
- Error: Response status code does not indicate success: 404 (Not Found).
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-s21-refactor-daily-entry-only-serial-2

- Flow: daily-entry-only
- Failure class: cleanup_failed
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: Daily-entry cleanup failed: Remote daily_entries/f14d87c1-d870-444e-ba2b-bca5762aa485 cleanup proof failed after ledger restore.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260417-s21-postpatch-all-modes

- Flow: 
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=2, maxRetry=0
- Runtime/logging: runtimeErrors=1, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: No new photos change_log row matched entry_id=f14d87c1-d870-444e-ba2b-bca5762aa485 filename=enterprise_soak_S21_round_193812.jpg.
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-s21-postpatch-all-modes-rerun

- Flow: 
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=2, maxRetry=0
- Runtime/logging: runtimeErrors=1, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: POST /driver/wait failed for S21 body={"key":"entry_editor_screen","timeoutMs":15000}: Response status code does not indicate success: 408 (Request Time-out).  {   "found": false,   "key": "entry_editor_screen",   "error": "Widget not found...
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-1922-device-all-modes-smoke

- Flow: 
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=4, maxRetry=0
- Runtime/logging: runtimeErrors=2, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: POST /driver/wait failed for S21 body={"timeoutMs":15000,"key":"entry_editor_screen"}: Response status code does not indicate success: 408 (Request Time-out).  {   "found": false,   "key": "entry_editor_screen",   "error": "Widget not found...
- Error: POST /driver/text failed for S10 body={"text":"enterprise UI photo S10 round 1","key":"photo_name_description_field"}: Response status code does not indicate success: 404 (Not Found).  {   "error": "Widget not found",   "key": "photo_name_d...
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-1919-device-all-modes-smoke

- Flow: 
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=2, maxRetry=0
- Runtime/logging: runtimeErrors=1, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: POST /driver/wait failed for S21 body={"key":"photo_name_dialog","timeoutMs":30000}: The request was canceled due to the configured HttpClient.Timeout of 30 seconds elapsing.
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-1916-storage-proof-rerun

- Flow: 
- Failure class: unknown_failure
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=1, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: GET /diagnostics/screen_contract failed for S10: Response status code does not indicate success: 503 (Service Unavailable).  {   "error": "no live context" }
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-190258-device-all-modes-smoke

- Flow: 
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=2, maxRetry=0
- Runtime/logging: runtimeErrors=2, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: UI photo mutation storage proof failed for photos/0b9229a1-bf47-47b3-8388-6d234e125493.
- Error: POST /driver/text failed for S10 body={"key":"photo_name_filename_field","text":"enterprise_soak_S10_round_190344"}: Response status code does not indicate success: 404 (Not Found).  {   "error": "Widget not found",   "key": "photo_name_fil...
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260418-s21-state-machine-combined-initial

- Flow: combined
- Failure class: unknown_failure
- Queue: , blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Compact evidence files to keep: summary.json

### 20260417-s21-fullscreen-notransition-strict-all-modes

- Flow: 
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=2, maxRetry=0
- Runtime/logging: runtimeErrors=1, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: POST /driver/wait failed for S21 body={"timeoutMs":30000,"key":"photo_name_dialog"}: Response status code does not indicate success: 408 (Request Time-out).  {   "found": false,   "key": "photo_name_dialog",   "error": "Widget not found wit...
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260418-s21-state-machine-contractors-initial

- Flow: contractors-only
- Failure class: runtime_log_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=1, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [runtime_log_error] state transition 'contractor-graph-mutate-open-create-contractor' failed for S21: [runtime_log_error] step 'contractor-graph-mutate-open-create-contractor' failed for S21: Runtime failure evidence captured during step 'c...
- Runtime fingerprint: flutter_error_widget - ErrorWidget visible in widget tree
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260418-s21-mdot1126-signature-nav-select-submit

- Flow: mdot1126-signature-only
- Failure class: change_log_proof_failed
- Queue: residue_detected, blocked=0, unprocessed=3, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: MDOT 1126 signature cleanup failed: MDOT 1126 cleanup sync failed: unprocessed_change_log_rows
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-signature-canonical-form-route

- Flow: mdot1126-signature-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1126-signature-submit-type-signature' failed for S21: [driver_or_sync_error] step 'mdot1126-signature-submit-type-signature' failed for S21: POST /driver/scroll-to-key failed for S21 body={"maxS...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-signature-body-ready-submit

- Flow: mdot1126-signature-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1126-signature-mutate-type-signature' failed for S21: [driver_or_sync_error] step 'mdot1126-signature-mutate-type-signature' failed for S21: POST /driver/scroll-to-key failed for S21 body={"targ...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-signature-accepted-after-deletedby-fix

- Flow: mdot1126-signature-only
- Failure class: change_log_proof_failed
- Queue: residue_detected, blocked=0, unprocessed=3, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: MDOT 1126 signature cleanup failed: MDOT 1126 cleanup sync failed: unprocessed_change_log_rows
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-initial

- Flow: mdot1126-expanded-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [driver_or_sync_error] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/scroll-to-...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-text-tap

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/wait failed f...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-tap-target-fix

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/wait failed f...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-status-key-tap

- Flow: mdot1126-expanded-only
- Failure class: widget_tap_not_found
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_tap_not_found] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_tap_not_found] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/tap failed ...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-signature-section-fallback

- Flow: mdot1126-signature-only
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=2, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: Timed out waiting for MDOT 1126 signature rows for form_responses/8a2fb439-6564-4361-a3fb-32b6917708be: form_responses/8a2fb439-6564-4361-a3fb-32b6917708be has no response_data.signature_audit_id yet.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260417-190010-device-all-modes-smoke

- Flow: 
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=3, maxRetry=0
- Runtime/logging: runtimeErrors=2, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: POST /driver/tap failed for S21 body={"key":"quantity_dialog_save"}: Response status code does not indicate success: 404 (Not Found).  {   "error": "Widget not found",   "key": "quantity_dialog_save" }
- Error: POST /driver/wait failed for S10 body={"key":"photo_name_dialog","timeoutMs":15000}: Response status code does not indicate success: 408 (Request Time-out).  {   "found": false,   "key": "photo_name_dialog",   "error": "Widget not found wit...
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-185531-device-all-modes-smoke

- Flow: 
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=3, maxRetry=0
- Runtime/logging: runtimeErrors=2, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: POST /driver/tap failed for S21 body={"key":"quantity_dialog_save"}: Response status code does not indicate success: 404 (Not Found).  {   "error": "Widget not found",   "key": "quantity_dialog_save" }
- Error: POST /driver/wait failed for S10 body={"timeoutMs":15000,"key":"photo_name_dialog"}: Response status code does not indicate success: 408 (Request Time-out).  {   "found": false,   "key": "photo_name_dialog",   "error": "Widget not found wit...
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-144220

- Flow: 
- Failure class: driver_or_sync_error, queue_not_drained_or_sync_not_observed
- Queue: , blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: Response status code does not indicate success: 404 (Not Found).
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-s21-strictlog-cleanup-sync-rerun

- Flow: 
- Failure class: unprocessed_change_log_rows
- Queue: residue_detected, blocked=0, unprocessed=6, maxRetry=1
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-s21-refactor-sync-only

- Flow: sync-only
- Failure class: widget_wait_timeout
- Queue: not_collected, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: The request was canceled due to the configured HttpClient.Timeout of 15 seconds elapsing.
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260418-s21-mdot1126-signature-resolver-fix

- Flow: mdot1126-signature-only
- Failure class: widget_wait_timeout
- Queue: residue_detected, blocked=0, unprocessed=2, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-signature-mutate-type-signature' failed for S21: [widget_wait_timeout] step 'mdot1126-signature-mutate-type-signature' failed for S21: POST /driver/wait failed for S21 body={"key":"mdot1126_t...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-signature-nav-fix

- Flow: mdot1126-signature-only
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=2, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: Timed out waiting for MDOT 1126 signature rows for form_responses/0bfa141f-2b49-4ef1-a962-ea1aa140b962: form_responses/0bfa141f-2b49-4ef1-a962-ea1aa140b962 has no response_data.signature_audit_id yet.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-signature-initial

- Flow: mdot1126-signature-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: GET /driver/query-records?table=user_profiles&limit=5&whereValue=d1ca900e-d880-4915-9950-e29ba180b028&whereColumn=user_id failed for S21: Response status code does not indicate success: 500 (Internal Server Error).  {   "error": "Query fail...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-contractors-partial-cleanup-sync-2

- Flow: sync-only
- Failure class: runtime_log_error
- Queue: not_collected, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=8, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [runtime_log_error] preflight captured runtime failure evidence.
- Runtime fingerprint: duplicate_global_key - 03:10:32 [app ] FlutterError: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-17 23:10:31.172 13477 13477 I flutter : [23:10:31.147] [ERROR] FlutterError: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-17 23:10:31.172 13477 13477 I flutter : Error: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 03:10:32 [app ] FlutterError: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-17 23:10:31.172 13477 13477 I flutter : [23:10:31.147] [ERROR] FlutterError: Multiple widgets used the same GlobalKey.
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260418-s21-cleanup-only-replay-accepted-ledgers

- Flow: cleanup-only
- Failure class: cleanup_failed
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: Argument types do not match
- Error: Argument types do not match
- Error: Argument types do not match
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260418-s21-cleanup-only-replay-accepted-ledgers-after-enumeration-fix

- Flow: cleanup-only
- Failure class: change_log_proof_failed, cleanup_failed
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: cleanup-only failed for entry_quantities/d733492e-c0bf-4a73-8d4f-644207fbd66c: Quantity cleanup did not create a change_log row for entry_quantities/d733492e-c0bf-4a73-8d4f-644207fbd66c.
- Error: cleanup-only failed for photos/db4eb554-0ce0-4507-b0b8-1f64cc5943db: Photo cleanup sync failed: sync_not_observed_or_last_sync_unchanged
- Error: cleanup-only failed for contractor_graph/: Contractor graph cleanup did not create a change_log row for entry_personnel_counts/epc-f14d87c1-d870-444e-ba2b-bca5762aa485-f48249bb-ba74-437c-9c01-c57eb467475b-4ac938ee-7411-4172-8274-d0de16c82f4...
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-s21-refactor-daily-entry-only

- Flow: daily-entry-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: Remote daily_entries/f14d87c1-d870-444e-ba2b-bca5762aa485 did not contain the mutated activity text after sync.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260417-185322-drain-before-quantity-rerun

- Flow: 
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=1, maxRetry=0
- Runtime/logging: runtimeErrors=1, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: POST /driver/wait failed for S21 body={"timeoutMs":15000,"key":"sync_dashboard_screen"}: Response status code does not indicate success: 408 (Request Time-out).  {   "found": false,   "key": "sync_dashboard_screen",   "error": "Widget not f...
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-185054-device-all-modes-smoke

- Flow: 
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=2, maxRetry=0
- Runtime/logging: runtimeErrors=2, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: POST /driver/text failed for S21 body={"text":"enterprise UI quantity S21 round 1 185103","key":"quantity_notes_field"}: Response status code does not indicate success: 404 (Not Found).  {   "error": "Widget not found",   "key": "quantity_n...
- Error: POST /driver/wait failed for S10 body={"key":"quantity_amount_field","timeoutMs":15000}: Response status code does not indicate success: 408 (Request Time-out).  {   "found": false,   "key": "quantity_amount_field",   "error": "Widget not f...
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-184549-device-all-modes-smoke

- Flow: 
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=1, maxRetry=0
- Runtime/logging: runtimeErrors=2, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: POST /driver/wait failed for S21 body={"timeoutMs":15000,"key":"bid_item_picker_sheet"}: Response status code does not indicate success: 408 (Request Time-out).  {   "found": false,   "key": "bid_item_picker_sheet",   "error": "Widget not f...
- Error: UI daily-entry activity mutation did not update local daily_entries/c945ebcc-c7e5-4ea8-a1d7-e7a0e7642217 on S10.
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-184152-device-all-modes-smoke

- Flow: 
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=2, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: UI daily-entry activity mutation did not update local daily_entries/f14d87c1-d870-444e-ba2b-bca5762aa485 on S21.
- Error: UI daily-entry activity mutation did not update local daily_entries/c945ebcc-c7e5-4ea8-a1d7-e7a0e7642217 on S10.
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-183758-device-all-modes-smoke

- Flow: 
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=1, maxRetry=0
- Runtime/logging: runtimeErrors=2, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: UI daily-entry activity mutation did not update local daily_entries/51008a84-c025-4ed4-8d3e-1d9f1d3846b2 on S21.
- Error: POST /driver/wait failed for S10: The request was canceled due to the configured HttpClient.Timeout of 15 seconds elapsing.
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-183010-device-all-modes-smoke

- Flow: 
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=2, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: UI photo mutation storage proof failed for photos/75272da0-367b-4be4-838a-7b5102f9f366.
- Error: UI daily-entry activity mutation did not update local daily_entries/51008a84-c025-4ed4-8d3e-1d9f1d3846b2 on S10.
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-182745-device-all-modes-smoke

- Flow: 
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=6, maxRetry=0
- Runtime/logging: runtimeErrors=2, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: POST /driver/tap failed for S21: Response status code does not indicate success: 404 (Not Found).  {   "error": "Widget not found",   "key": "sync_now_full_button" }
- Error: POST /driver/tap failed for S10: Response status code does not indicate success: 404 (Not Found).  {   "error": "Widget not found",   "key": "sync_now_full_button" }
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-182214-s21-daily-smoke

- Flow: 
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=1, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: POST /driver/scroll failed for S21: Response status code does not indicate success: 404 (Not Found).  {   "error": "Scrollable not found",   "key": "entry_editor_scroll" }
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-182214-device

- Flow: 
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=2, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: UI daily-entry activity mutation did not update local daily_entries/c945ebcc-c7e5-4ea8-a1d7-e7a0e7642217 on S21.
- Error: UI daily-entry activity mutation did not update local daily_entries/c945ebcc-c7e5-4ea8-a1d7-e7a0e7642217 on S10.
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260417-181106-device

- Flow: 
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=2, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: Response status code does not indicate success: 404 (Not Found).
- Error: Response status code does not indicate success: 404 (Not Found).
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260418-s21-mdot1126-expanded-after-status-before-location

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-signature-submit-open-created-form' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-signature-submit-open-created-form' failed for S21: POST /driver/wait failed for S21...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260417-s21-strictlog-cleanup-sync

- Flow: 
- Failure class: unprocessed_change_log_rows
- Queue: residue_detected, blocked=0, unprocessed=4, maxRetry=1
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260418-s21-mdot1126-expanded-after-starter-rainfall-row

- Flow: mdot1126-expanded-only
- Failure class: widget_tap_not_found
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_tap_not_found] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_tap_not_found] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/tap-text fa...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-state-machine-contractors-second

- Flow: contractors-only
- Failure class: widget_wait_timeout
- Queue: residue_detected, blocked=0, unprocessed=6, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'contractor-graph-mutate-add-equipment' failed for S21: [widget_wait_timeout] step 'contractor-graph-mutate-add-equipment' failed for S21: POST /driver/wait failed for S21 body={"timeoutMs":15000,"key"...
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260418-s21-state-machine-photo-only-after-dialog-settle-fix

- Flow: photo-only
- Failure class: cleanup_failed
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: The property 'Response' cannot be found on this object. Verify that the property exists.; ledger cleanup failed: Storage absence proof failed for entry-photos/entries/26fe92cd-7044-4412-9a09-5c5f49a292f9/f14d87c1-d870-444e-ba2b-bca5762aa485...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-state-machine-ledger-recovery-sync

- Flow: sync-only
- Failure class: runtime_log_error
- Queue: not_collected, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=11, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [runtime_log_error] preflight captured runtime failure evidence.
- Runtime fingerprint: duplicate_global_key - 01:20:53 [app ] FlutterError: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-17 21:20:52.428 30081 30081 I flutter : [21:20:52.392] [ERROR] FlutterError: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-17 21:20:52.428 30081 30081 I flutter : Error: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: flutter_runtime - 01:19:05 [app ] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 01:19:05 [app ] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260418-s21-state-machine-daily-entry-only

- Flow: daily-entry-only
- Failure class: driver_or_sync_error, widget_wait_timeout
- Queue: not_collected, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'daily-entry-mutate-enter-activity-text' failed for S21: POST /driver/wait failed for S21 body={"key":"activity_location_field_21dc1de1-4e31-4fa2-84d1-7c462a538da6","timeoutMs":5000}: Response status c...
- Error: The property 'blocked' cannot be found on this object. Verify that the property exists.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-state-machine-daily-entry-only-rerun

- Flow: daily-entry-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'daily-entry-mutate-enter-activity-text' failed for S21: POST /driver/wait failed for S21 body={"timeoutMs":5000,"key":"activity_location_field_21dc1de1-4e31-4fa2-84d1-7c462a538da6"}: Response status c...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-state-machine-daily-entry-ledger-recovery

- Flow: daily-entry-ledger-recovery
- Failure class: unknown_failure
- Queue: residue_detected, blocked=0, unprocessed=5, maxRetry=0
- Runtime/logging: runtimeErrors=12, loggingGaps=0
- Direct driver sync endpoint used: False
- Runtime fingerprint: duplicate_global_key - 01:20:00 [app ] FlutterError: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-17 21:19:59.456 30081 30081 I flutter : [21:19:59.450] [ERROR] FlutterError: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-17 21:19:59.456 30081 30081 I flutter : Error: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-17 21:19:59.491 30081 30081 I flutter : [21:19:59.488] [ERROR] FlutterError: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-17 21:19:59.491 30081 30081 I flutter : Error: Multiple widgets used the same GlobalKey.
- Compact evidence files to keep: summary.json, S21/round-1-mutation-ledger.json

### 20260418-s21-state-machine-contractors-third

- Flow: contractors-only
- Failure class: cleanup_failed
- Queue: residue_detected, blocked=0, unprocessed=13, maxRetry=0
- Runtime/logging: runtimeErrors=20, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [runtime_log_error] state transition 'contractor-graph-mutate-add-equipment' failed for S21: [runtime_log_error] step 'contractor-graph-mutate-add-equipment' failed for S21: Runtime failure evidence captured during step 'contractor-graph-mu...
- Runtime fingerprint: flutter_runtime - 03:09:17 [app ] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: duplicate_global_key - 03:09:17 [app ] FlutterError: Duplicate GlobalKey detected in widget tree.
- Runtime fingerprint: flutter_runtime - 04-17 23:09:16.138 13477 13477 I flutter : [23:09:16.076] [ERROR] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 04-17 23:09:16.534 13477 13477 I flutter : [23:09:16.532] [ERROR] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: duplicate_global_key - 04-17 23:09:16.781 13477 13477 I flutter : [23:09:16.780] [ERROR] FlutterError: Duplicate GlobalKey detected in widget tree.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-state-machine-quantity-only-after-driver-fix

- Flow: quantity-only
- Failure class: runtime_log_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=8, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [runtime_log_error] state transition 'quantity-mutate-select-bid-item' failed for S21: [runtime_log_error] step 'quantity-mutate-select-bid-item' failed for S21: Runtime failure evidence captured during step 'quantity-mutate-select-bid-item...
- Runtime fingerprint: flutter_runtime - 01:36:46 [app ] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 01:36:46 [app ] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Runtime fingerprint: duplicate_global_key - 01:36:46 [app ] FlutterError: Duplicate GlobalKey detected in widget tree.
- Runtime fingerprint: flutter_runtime - 04-17 21:36:45.081 3986 3986 I flutter : [21:36:45.073] [ERROR] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 04-17 21:36:45.143 3986 3986 I flutter : [21:36:45.140] [ERROR] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-state-machine-quantity-only-after-modal-fix

- Flow: quantity-only
- Failure class: runtime_log_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=5, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [runtime_log_error] state transition 'quantity-mutate-select-bid-item' failed for S21: [runtime_log_error] step 'quantity-mutate-select-bid-item' failed for S21: Runtime failure evidence captured during step 'quantity-mutate-select-bid-item...
- Runtime fingerprint: flutter_runtime - 01:38:33 [app ] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 01:38:33 [app ] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Runtime fingerprint: flutter_runtime - 04-17 21:38:32.360 4871 4871 I flutter : [21:38:32.352] [ERROR] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 04-17 21:38:32.503 4871 4871 I flutter : [21:38:32.501] [ERROR] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Runtime fingerprint: flutter_runtime - 04-17 21:38:32.518 4871 4871 I flutter : [21:38:32.516] [ERROR] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-state-machine-photo-only-file-stem-fix

- Flow: photo-only
- Failure class: runtime_log_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=5, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [runtime_log_error] state transition 'photo-mutate-select-gallery' failed for S21: [runtime_log_error] step 'photo-mutate-select-gallery' failed for S21: Runtime failure evidence captured during step 'photo-mutate-select-gallery'.
- Runtime fingerprint: flutter_runtime - 01:48:54 [app ] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 01:48:54 [app ] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Runtime fingerprint: flutter_runtime - 04-17 21:48:53.450 7069 7069 I flutter : [21:48:53.442] [ERROR] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 04-17 21:48:53.561 7069 7069 I flutter : [21:48:53.558] [ERROR] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Runtime fingerprint: flutter_runtime - 04-17 21:48:53.577 7069 7069 I flutter : [21:48:53.575] [ERROR] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot0582b-after-remote-json-proof

- Flow: mdot0582b-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: The property 'Count' cannot be found on this object. Verify that the property exists.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-direct-form-route

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/wait failed f...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-direct-field-entry

- Flow: mdot1126-expanded-only
- Failure class: widget_tap_not_found
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_tap_not_found] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_tap_not_found] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/tap-text fa...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-center-visible-tap

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/wait failed f...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-cleanup-residue-retry-sync

- Flow: sync-only
- Failure class: unprocessed_change_log_rows
- Queue: residue_detected, blocked=0, unprocessed=4, maxRetry=1
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: Sync-only measurement failed: unprocessed_change_log_rows
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260418-s21-mdot0582b-initial

- Flow: mdot0582b-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot0582b-header-proctor-test' failed for S21: [driver_or_sync_error] step 'mdot0582b-header-proctor-test' failed for S21: POST /driver/scroll-to-key failed for S21 body={"target":"hub_test_field_we...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot0582b-after-test-section-fix

- Flow: mdot0582b-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: Failed to parse MDOT 0582B JSON payload: Conversion from JSON failed with error: Unexpected character encountered while parsing value: @. Path '', line 0, position 0.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-state-machine-quantity-only-initial

- Flow: quantity-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=5, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'quantity-mutate-select-bid-item' failed for S21: [driver_or_sync_error] step 'quantity-mutate-select-bid-item' failed for S21: Response status code does not indicate success: 500 (Internal Server Er...
- Runtime fingerprint: flutter_runtime - 01:32:39 [app ] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 01:32:39 [app ] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Runtime fingerprint: flutter_runtime - 04-17 21:32:38.296 592 592 I flutter : [21:32:38.289] [ERROR] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 04-17 21:32:38.390 592 592 I flutter : [21:32:38.387] [ERROR] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Runtime fingerprint: flutter_runtime - 04-17 21:32:38.400 592 592 I flutter : [21:32:38.397] [ERROR] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-state-machine-quantity-only-visible-item

- Flow: quantity-only
- Failure class: runtime_log_error
- Queue: not_collected, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=3, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [runtime_log_error] preflight captured runtime failure evidence.
- Runtime fingerprint: duplicate_global_key - 01:34:30 [app ] FlutterError: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-17 21:34:29.916 592 592 I flutter : [21:34:29.881] [ERROR] FlutterError: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-17 21:34:29.917 592 592 I flutter : Error: Multiple widgets used the same GlobalKey.
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260418-s21-mdot1126-expanded-after-material-button-target

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/wait failed f...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-state-machine-photo-only-initial

- Flow: photo-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: The variable '$round_' cannot be retrieved because it has not been set.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-state-machine-photo-only-storage-absence-fix

- Flow: photo-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: The property 'Response' cannot be found on this object. Verify that the property exists.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-preferred-text-target

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/wait failed f...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-auto-advance

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/scroll-to-key failed for S21 body={"maxScrolls":40,"scrollable":"form_...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-visible-text-only

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/scroll-to-key failed for S21 body={"scrollable":"form_workflow_scroll_...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-initial

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/scroll-to-key failed for S21 body={"maxScrolls":40,"scrollable":"form_...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-title-fallback-selection

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: MDOT 1174R section 'remarks' could not be opened. header key mdot1174_section_heade...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-section-open-only

- Flow: mdot1174r-only
- Failure class: runtime_log_error
- Queue: residue_detected, blocked=0, unprocessed=31, maxRetry=0
- Runtime/logging: runtimeErrors=27, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [runtime_log_error] state transition 'mdot1174r-fields-and-rows' failed for S21: [runtime_log_error] step 'mdot1174r-fields-and-rows' failed for S21: Runtime failure evidence captured during step 'mdot1174r-fields-and-rows'.
- Runtime fingerprint: flutter_runtime - 14:50:11 [app ] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 14:50:11 [app ] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Runtime fingerprint: duplicate_global_key - 14:50:11 [app ] FlutterError: Duplicate GlobalKey detected in widget tree.
- Runtime fingerprint: duplicate_global_key - 14:50:52 [app ] FlutterError: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-18 10:50:51.489 30244 30244 I flutter : [10:50:51.484] [ERROR] FlutterError: Multiple widgets used the same GlobalKey.
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-section-headers

- Flow: mdot1174r-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1174r-fields-and-rows' failed for S21: [widget_wait_timeout] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/wait failed for S21 body={"key":"mdot1174_field_maximum_time","timeoutMs"...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-open-created-form

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/scroll-to-key failed for S21 body={"target":"mdot1174_field_contractor...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-no-animated-size-keepalive

- Flow: mdot1174r-only
- Failure class: runtime_log_error
- Queue: residue_detected, blocked=0, unprocessed=32, maxRetry=0
- Runtime/logging: runtimeErrors=27, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [runtime_log_error] state transition 'mdot1174r-fields-and-rows' failed for S21: [runtime_log_error] step 'mdot1174r-fields-and-rows' failed for S21: Runtime failure evidence captured during step 'mdot1174r-fields-and-rows'.
- Runtime fingerprint: flutter_runtime - 14:56:49 [app ] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 14:56:49 [app ] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Runtime fingerprint: duplicate_global_key - 14:56:49 [app ] FlutterError: Duplicate GlobalKey detected in widget tree.
- Runtime fingerprint: duplicate_global_key - 14:57:21 [app ] FlutterError: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-18 10:57:21.366 31944 31944 I flutter : [10:57:21.359] [ERROR] FlutterError: Multiple widgets used the same GlobalKey.
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-mounted-text

- Flow: mdot1174r-only
- Failure class: runtime_log_error
- Queue: residue_detected, blocked=0, unprocessed=25, maxRetry=0
- Runtime/logging: runtimeErrors=35, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [runtime_log_error] state transition 'mdot1174r-fields-and-rows' failed for S21: [runtime_log_error] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/wait failed for S21 body={"key":"mdot1174_qa_rows_composer_lot_number","timeo...
- Runtime fingerprint: flutter_runtime - 14:05:45 [app ] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 14:05:45 [app ] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Runtime fingerprint: duplicate_global_key - 14:05:45 [app ] FlutterError: Duplicate GlobalKey detected in widget tree.
- Runtime fingerprint: flutter_runtime - 04-18 10:05:44.992 24534 24534 I flutter : [10:05:44.982] [ERROR] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 04-18 10:05:45.053 24534 24534 I flutter : [10:05:45.050] [ERROR] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-header-nav-skip

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/scroll-to-key failed for S21 body={"scrollable":"form_workflow_scroll_...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-header-first-selection

- Flow: mdot1174r-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1174r-fields-and-rows' failed for S21: [widget_wait_timeout] step 'mdot1174r-fields-and-rows' failed for S21: MDOT 1174R section 'placement' could not be opened. header key mdot1174_section_header...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-first-field-scroll-selection

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: MDOT 1174R section 'quantities' could not be opened. header key mdot1174_section_he...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-expanded-sentinel

- Flow: mdot1174r-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1174r-fields-and-rows' failed for S21: [widget_wait_timeout] step 'mdot1174r-fields-and-rows' failed for S21: MDOT 1174R section 'quantities' could not be opened. header key mdot1174_section_heade...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-expanded-body-sentinel

- Flow: mdot1174r-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1174r-fields-and-rows' failed for S21: [widget_wait_timeout] step 'mdot1174r-fields-and-rows' failed for S21: MDOT 1174R section 'qa' could not be opened. header key mdot1174_section_header_qa fai...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-ensure-visible-scroll

- Flow: mdot1174r-only
- Failure class: runtime_log_error
- Queue: residue_detected, blocked=0, unprocessed=33, maxRetry=0
- Runtime/logging: runtimeErrors=27, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [runtime_log_error] state transition 'mdot1174r-fields-and-rows' failed for S21: [runtime_log_error] step 'mdot1174r-fields-and-rows' failed for S21: Runtime failure evidence captured during step 'mdot1174r-fields-and-rows'.
- Runtime fingerprint: flutter_runtime - 15:05:53 [app ] FlutterError: 'package:flutter/src/widgets/framework.dart': Failed assertion: line 6417 pos 14: '() {
- Runtime fingerprint: flutter_runtime - 15:05:53 [app ] FlutterError: 'package:flutter/src/rendering/object.dart': Failed assertion: line 3536 pos 12: 'attached': is not true.
- Runtime fingerprint: duplicate_global_key - 15:05:53 [app ] FlutterError: Duplicate GlobalKey detected in widget tree.
- Runtime fingerprint: duplicate_global_key - 15:06:33 [app ] FlutterError: Multiple widgets used the same GlobalKey.
- Runtime fingerprint: duplicate_global_key - 04-18 11:06:33.335 1941 1941 I flutter : [11:06:33.331] [ERROR] FlutterError: Multiple widgets used the same GlobalKey.
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-bidirectional-scroll

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/scroll-to-key failed for S21 body={"maxScrolls":50,"target":"mdot1174_...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-section-scroll-fallback

- Flow: mdot1126-expanded-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [driver_or_sync_error] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/scroll-to-...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-scroll-fix

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/wait failed f...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-rainfall-ui

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/wait failed f...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-signature-visible-submit

- Flow: mdot1126-signature-only
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=2, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1126-signature-mutate-type-signature' failed for S21: [driver_or_sync_error] step 'mdot1126-signature-mutate-type-signature' failed for S21: POST /driver/scroll-to-key failed for S21 body={"scro...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260417-s21-strictlog-stablekey-all-modes

- Flow: 
- Failure class: runtime_log_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=1, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: Captured device log contained app runtime errors.
- Compact evidence files to keep: summary.json, S21/timeline.json


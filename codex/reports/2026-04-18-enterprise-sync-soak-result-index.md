# Sync Soak Result Index

- Generated UTC: 2026-04-18T15:21:06.0084751Z
- Input root: .claude\test-results\2026-04-18\enterprise-sync-soak
- Runs: 55
- Passed: 15
- Failed: 40

## Failure Groups

| Classification | Count | Latest Run | Queue | Runtime Errors |
| --- | ---: | --- | --- | ---: |
| change_log_proof_failed | 2 | 20260418-s21-mdot1126-signature-accepted-after-deletedby-fix | residue_detected | 0 |
| driver_or_sync_error | 17 | 20260418-s21-mdot0582b-after-remote-json-proof | drained | 0 |
| runtime_log_error | 4 | 20260418-s21-mdot1174r-after-ensure-visible-scroll | residue_detected | 27 |
| unprocessed_change_log_rows | 1 | 20260418-s21-mdot1126-cleanup-residue-retry-sync | residue_detected | 0 |
| widget_tap_not_found | 3 | 20260418-s21-mdot1126-expanded-after-direct-field-entry | drained | 0 |
| widget_wait_timeout | 13 | 20260418-s21-mdot1126-expanded-after-center-visible-tap | drained | 0 |

## Runs

| Result | Flow | Run | Queue | Runtime | Logs | Direct Sync | Summary |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| PASS | mdot1126-signature-only | 20260418-s10-mdot1126-signature-regression-with-cleanup-sync-retry | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-mdot1126-signature-regression-with-cleanup-sync-retry/summary.json |
| PASS | sync-only | 20260418-s10-pre-mdot-residue-sync-only | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s10-pre-mdot-residue-sync-only/summary.json |
| PASS | mdot0582b-only | 20260418-s21-mdot0582b-accepted-initial | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-accepted-initial/summary.json |
| FAIL | mdot0582b-only | 20260418-s21-mdot0582b-after-remote-json-proof | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-after-remote-json-proof/summary.json |
| FAIL | mdot0582b-only | 20260418-s21-mdot0582b-after-test-section-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-after-test-section-fix/summary.json |
| FAIL | mdot0582b-only | 20260418-s21-mdot0582b-initial | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot0582b-initial/summary.json |
| FAIL | sync-only | 20260418-s21-mdot1126-cleanup-residue-retry-sync | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-cleanup-residue-retry-sync/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-center-visible-tap | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-center-visible-tap/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-direct-field-entry | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-direct-field-entry/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-direct-form-route | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-direct-form-route/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-material-button-target | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-material-button-target/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-preferred-text-target | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-preferred-text-target/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-accepted-after-deletedby-fix | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-accepted-after-deletedby-fix/summary.json |
| PASS | mdot1126-signature-only | 20260418-s21-mdot1126-signature-accepted-with-cleanup-sync-retry | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-accepted-with-cleanup-sync-retry/summary.json |
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
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-rainfall-ui | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-rainfall-ui/summary.json |
| FAIL | mdot1126-expanded-only | 20260418-s21-mdot1126-expanded-after-scroll-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-expanded-after-scroll-fix/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-body-ready-submit | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-body-ready-submit/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-header-first-selection | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-header-first-selection/summary.json |
| PASS | cleanup-only | 20260418-s21-mdot1126-signature-cleanup-only-replay-accepted-ledger | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-cleanup-only-replay-accepted-ledger/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-nav-select-submit | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-nav-select-submit/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-section-fallback | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-section-fallback/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-visible-submit | residue_detected | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-visible-submit/summary.json |
| PASS | cleanup-only | 20260418-s21-mdot1126-signed-ledger-cleanup-replay-after-deletedby-fix | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signed-ledger-cleanup-replay-after-deletedby-fix/summary.json |
| PASS | sync-only | 20260418-s21-mdot1126-visible-submit-draft-cleanup-sync | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-visible-submit-draft-cleanup-sync/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-auto-advance | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-auto-advance/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-bidirectional-scroll | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-bidirectional-scroll/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-ensure-visible-scroll | residue_detected | 27 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-ensure-visible-scroll/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-expanded-body-sentinel | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-expanded-body-sentinel/summary.json |
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-expanded-sentinel | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-expanded-sentinel/summary.json |
| PASS | sync-only | 20260418-s21-post-s10-mdot-residue-sync-only | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-post-s10-mdot-residue-sync-only/summary.json |
| FAIL | mdot1126-signature-only | 20260418-s21-mdot1126-signature-canonical-form-route | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1126-signature-canonical-form-route/summary.json |
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
| FAIL | mdot1174r-only | 20260418-s21-mdot1174r-after-first-field-scroll-selection | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-mdot1174r-after-first-field-scroll-selection/summary.json |
| PASS | sync-only | 20260418-s21-post-v61-signature-backlog-sync-only | drained | 0 | 0 | no | .claude/test-results/2026-04-18/enterprise-sync-soak/20260418-s21-post-v61-signature-backlog-sync-only/summary.json |

## Failure Details

### 20260418-s21-mdot1126-signature-nav-select-submit

- Flow: mdot1126-signature-only
- Failure class: change_log_proof_failed
- Queue: residue_detected, blocked=0, unprocessed=3, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: MDOT 1126 signature cleanup failed: MDOT 1126 cleanup sync failed: unprocessed_change_log_rows
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot0582b-after-remote-json-proof

- Flow: mdot0582b-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: The property 'Count' cannot be found on this object. Verify that the property exists.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot0582b-after-test-section-fix

- Flow: mdot0582b-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: Failed to parse MDOT 0582B JSON payload: Conversion from JSON failed with error: Unexpected character encountered while parsing value: @. Path '', line 0, position 0.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot0582b-initial

- Flow: mdot0582b-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot0582b-header-proctor-test' failed for S21: [driver_or_sync_error] step 'mdot0582b-header-proctor-test' failed for S21: POST /driver/scroll-to-key failed for S21 body={"target":"hub_test_field_we...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-cleanup-residue-retry-sync

- Flow: sync-only
- Failure class: unprocessed_change_log_rows
- Queue: residue_detected, blocked=0, unprocessed=4, maxRetry=1
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: Sync-only measurement failed: unprocessed_change_log_rows
- Compact evidence files to keep: summary.json, S21/timeline.json

### 20260418-s21-mdot1126-expanded-after-center-visible-tap

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

### 20260418-s21-mdot1126-expanded-after-direct-form-route

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/wait failed f...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-signature-accepted-after-deletedby-fix

- Flow: mdot1126-signature-only
- Failure class: change_log_proof_failed
- Queue: residue_detected, blocked=0, unprocessed=3, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: MDOT 1126 signature cleanup failed: MDOT 1126 cleanup sync failed: unprocessed_change_log_rows
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-material-button-target

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

### 20260418-s21-mdot1126-expanded-after-section-scroll-fallback

- Flow: mdot1126-expanded-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [driver_or_sync_error] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/scroll-to-...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-starter-rainfall-row

- Flow: mdot1126-expanded-only
- Failure class: widget_tap_not_found
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_tap_not_found] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_tap_not_found] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/tap-text fa...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-status-before-location

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-signature-submit-open-created-form' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-signature-submit-open-created-form' failed for S21: POST /driver/wait failed for S21...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-status-key-tap

- Flow: mdot1126-expanded-only
- Failure class: widget_tap_not_found
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_tap_not_found] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_tap_not_found] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/tap failed ...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-tap-target-fix

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/wait failed f...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-text-tap

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/wait failed f...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-after-preferred-text-target

- Flow: mdot1126-expanded-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: [widget_wait_timeout] step 'mdot1126-expanded-edit-header-rainfall-measures-remarks' failed for S21: POST /driver/wait failed f...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-signature-body-ready-submit

- Flow: mdot1126-signature-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1126-signature-mutate-type-signature' failed for S21: [driver_or_sync_error] step 'mdot1126-signature-mutate-type-signature' failed for S21: POST /driver/scroll-to-key failed for S21 body={"targ...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-header-first-selection

- Flow: mdot1174r-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1174r-fields-and-rows' failed for S21: [widget_wait_timeout] step 'mdot1174r-fields-and-rows' failed for S21: MDOT 1174R section 'placement' could not be opened. header key mdot1174_section_header...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-visible-text-only

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/scroll-to-key failed for S21 body={"scrollable":"form_workflow_scroll_...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-signature-section-fallback

- Flow: mdot1126-signature-only
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=2, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: Timed out waiting for MDOT 1126 signature rows for form_responses/8a2fb439-6564-4361-a3fb-32b6917708be: form_responses/8a2fb439-6564-4361-a3fb-32b6917708be has no response_data.signature_audit_id yet.
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-signature-visible-submit

- Flow: mdot1126-signature-only
- Failure class: driver_or_sync_error
- Queue: residue_detected, blocked=0, unprocessed=2, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1126-signature-mutate-type-signature' failed for S21: [driver_or_sync_error] step 'mdot1126-signature-mutate-type-signature' failed for S21: POST /driver/scroll-to-key failed for S21 body={"scro...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-auto-advance

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/scroll-to-key failed for S21 body={"maxScrolls":40,"scrollable":"form_...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-bidirectional-scroll

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/scroll-to-key failed for S21 body={"maxScrolls":50,"target":"mdot1174_...
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

### 20260418-s21-mdot1174r-after-expanded-body-sentinel

- Flow: mdot1174r-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1174r-fields-and-rows' failed for S21: [widget_wait_timeout] step 'mdot1174r-fields-and-rows' failed for S21: MDOT 1174R section 'qa' could not be opened. header key mdot1174_section_header_qa fai...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-expanded-sentinel

- Flow: mdot1174r-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1174r-fields-and-rows' failed for S21: [widget_wait_timeout] step 'mdot1174r-fields-and-rows' failed for S21: MDOT 1174R section 'quantities' could not be opened. header key mdot1174_section_heade...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-signature-canonical-form-route

- Flow: mdot1126-signature-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1126-signature-submit-type-signature' failed for S21: [driver_or_sync_error] step 'mdot1126-signature-submit-type-signature' failed for S21: POST /driver/scroll-to-key failed for S21 body={"maxS...
- Compact evidence files to keep: summary.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-first-field-scroll-selection

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: MDOT 1174R section 'quantities' could not be opened. header key mdot1174_section_he...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-header-nav-skip

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/scroll-to-key failed for S21 body={"scrollable":"form_workflow_scroll_...
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

### 20260418-s21-mdot1174r-after-open-created-form

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/scroll-to-key failed for S21 body={"target":"mdot1174_field_contractor...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-after-section-headers

- Flow: mdot1174r-only
- Failure class: widget_wait_timeout
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [widget_wait_timeout] state transition 'mdot1174r-fields-and-rows' failed for S21: [widget_wait_timeout] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/wait failed for S21 body={"key":"mdot1174_field_maximum_time","timeoutMs"...
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

### 20260418-s21-mdot1174r-after-title-fallback-selection

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: MDOT 1174R section 'remarks' could not be opened. header key mdot1174_section_heade...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1174r-initial

- Flow: mdot1174r-only
- Failure class: driver_or_sync_error
- Queue: drained, blocked=0, unprocessed=0, maxRetry=0
- Runtime/logging: runtimeErrors=0, loggingGaps=0
- Direct driver sync endpoint used: False
- Error: [state_sentinel_failed] state transition 'mdot1174r-fields-and-rows' failed for S21: [driver_or_sync_error] step 'mdot1174r-fields-and-rows' failed for S21: POST /driver/scroll-to-key failed for S21 body={"maxScrolls":40,"scrollable":"form_...
- Compact evidence files to keep: summary.json, S21/final-debug-summary.json, S21/final-debug-errors.txt, S21/change-log-final.json, S21/timeline.json, S21/round-1-mutation-ledger.json

### 20260418-s21-mdot1126-expanded-initial

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


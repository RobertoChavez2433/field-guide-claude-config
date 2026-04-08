Date: 2026-04-07
Branch: `sync-engine-refactor`
Status key: `[ ]` pending, `[-]` in progress, `[x]` done

# Sync UI Endpoint Refactor TODO

## Immediate Refactor Slice

[x] Align sync dashboard with the post-merge UI endpoint pattern
[x] Add `sync_screen_providers.dart` for screen-local sync controller scopes
[x] Move sync dashboard async diagnostics/loading state out of the screen widget
[x] Keep every touched sync UI component at or below the 350-line ceiling

[x] Decompose live delete verification endpoints before the next device wave
[x] Extract `/driver/delete-propagation` into its own handler instead of extending `DriverServer`
[x] Deduplicate project snapshot table output from `DeletePropagationVerifier`
[x] Preserve the existing HTTP contract used by the live run artifacts

## Validation

[x] Add targeted tests for sync dashboard controller loading/error behavior
[x] Add regression coverage for deduplicated project delete-propagation snapshots
[x] Run focused sync presentation + delete verification tests
[x] Run `flutter analyze`

## After Refactor

[x] Update live checklist/report/checkpoint with the refactor checkpoint
[ ] Resume `project-delete-storage-and-ui-verification`
[ ] Continue file-backed delete lanes and restore/revocation lanes

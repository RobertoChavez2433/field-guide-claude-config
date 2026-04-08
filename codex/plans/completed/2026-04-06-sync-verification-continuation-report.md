# Sync Verification Continuation Report

Date: 2026-04-06
Branch: `sync-engine-refactor`
Head: `ed6027e4` (`wip: snapshot payapp sync verification`)

## Intent

Resume with sync verification as the top priority and hold a hard release bar:
no known data-loss path across SQLite, `change_log`, Supabase rows, or storage
objects for the newly wired pay-app/export sync surfaces.

The next session should stay narrowly focused on proving the sync system, not on
general product polish. Pay-app export format and UI details are secondary until
the sync round-trips and destructive paths are bulletproof.

## What Was Completed

### 1. Sync-engine risk reduction

- Thinned sync orchestration by extracting record-level helpers out of the
  oversized handlers:
  - `pull_fk_violation_resolver.dart`
  - `pull_record_applicator.dart`
  - `push_execution_router.dart`
  - `push_table_planner.dart`
  - `stale_file_cache_invalidator.dart`
  - `orphan_purger.dart`
- Kept `pull_handler.dart` and `push_handler.dart` closer to orchestration while
  preserving the pay-app/export-artifact rescue and file-cache behavior.

### 2. Pay-app/export data-loss fixes

- Fixed file-backed sync to respect `local_path`/`remote_path` correctly for
  `export_artifacts`.
- Fixed artifact-scoped storage path generation so same-filename exports do not
  alias the same remote blob.
- Tightened pay-app export cleanup so failed metadata persistence removes the
  new file and replacement does not delete the old file before the new metadata
  is durable.
- Added soft-delete/purge coverage for `export_artifacts` and `pay_applications`.
- Fixed chronology and duplicate-number guards to live in provider logic instead
  of only UI.
- Fixed analytics chronology to compare actual chronology rather than relying on
  user-overridden numbering.

### 3. Comparison/export fidelity work

- Added quantity-aware comparison/discrepancy support end to end:
  - exported workbook carries quantity columns
  - parser handles quantity-aware CSV/XLSX plus best-effort fallback for
    amount-only contractor files
  - discrepancy summary/table/PDF now show quantity variances as well as dollar
    variances
- Added a permanent reusable contractor fixture:
  - `test/fixtures/pay_applications/contractor_pay_app_5_items.csv`
- Cleaned up user-facing pay-app/comparison dialog copy to be less speculative
  and more operator-facing.

### 4. Local verification already green

Focused pay-app tests passed:
- `pay_app_import_parser_test.dart`
- `pay_app_excel_exporter_test.dart`
- `contractor_comparison_pdf_exporter_test.dart`
- `contractor_comparison_provider_test.dart`
- `manual_match_editor_test.dart`
- `pay_app_date_range_dialog_test.dart`

Focused sync tests passed:
- `sync_error_classifier_contract_test.dart`
- `integrity_checker_test.dart`
- `orphan_scanner_test.dart`
- `pull_handler_test.dart`
- `pull_handler_contract_test.dart`
- `push_handler_test.dart`
- `push_handler_contract_test.dart`
- `sync_schema_test.dart`

Targeted `flutter analyze` on the changed pay-app/sync surfaces passed.

## What Was Found

### Fixed defects

1. File-backed `export_artifacts` could sync metadata without a valid upload
   path.
2. Phase-2 sync failure could delete an already-good remote artifact even when
   no new upload occurred.
3. Pay-app export replacement could delete the old local file before the new
   metadata persistence succeeded.
4. Local purge/soft-delete coverage skipped pay-app/export tables.
5. Pull-side pay-app dependency rescue and file-cache invalidation were too
   buried in `PullHandler`.
6. Push eligibility/blocking/order planning were too buried in `PushHandler`.
7. Comparison/discrepancy outputs did not show quantity variances.
8. Dialog copy was too developer-oriented and ambiguous.

### Still-open or still-unproven items

1. Full S21 sync-verification flow is not yet complete.
2. Windows runtime verification is still blocked by external desktop runtime
   friction and was deprioritized in favor of Android proof.
3. The live backend schema for `pay_applications` / `export_artifacts` still
   needs explicit runtime verification after migration deployment.
4. The comparison/export device flow hit a live overflow/freeze on S21 after
   CSV import; local widget coverage was strengthened, but device proof is not
   yet re-run after the last cleanup.
5. The new file-backed/user-scoped adapters still need first-class sync flows:
   `export_artifacts`, `pay_applications`, `form_exports`, `entry_exports`,
   `support_tickets`, `user_consent_records`.

## Quality Gates For The Next Session

Do not call sync verification complete until all of the following are true:

### Gate 1: Local proof

- Focused sync and pay-app tests stay green after every fix.
- Targeted `flutter analyze` stays green on touched files.
- No new swallowed exceptions or catch-and-log-only paths are added.

### Gate 2: Runtime proof on S21

- Use an isolated driver port with no overlap against the other active device
  sessions.
- After each sync action, verify:
  - UI result
  - SQLite row via driver/local-record
  - `change_log` state via driver/change-log
  - debug-server sync logs
  - Supabase row via `tools/verify-sync.ps1`
  - storage object existence for file-backed tables

### Gate 3: File-backed round-trip proof

First-class flows must exist and be exercised for:
- `export_artifacts`
- `pay_applications`
- `form_exports`
- `entry_exports`
- `photos`
- `documents`

Each flow must prove create, sync, receive, and destructive cleanup behavior.

### Gate 4: Insert-only/user-scoped proof

First-class flows must exist and be exercised for:
- `support_tickets`
- `user_consent_records`

These must prove:
- no hidden `updated_at` / soft-delete assumptions
- no invalid pull/integrity probing
- queue drains correctly
- remote-side semantics remain insert-only where intended

### Gate 5: Destructive and recovery proof

Must explicitly prove:
- pay-app replace does not lose the previous artifact before the new metadata is
  durable
- delete propagation cleans SQLite, `change_log`, Supabase, and storage without
  orphaning
- fresh pull after `remove-from-device` rehydrates file-backed and non-file
  state correctly
- restart/retry flows do not leave duplicate linkage or stranded `change_log`
  entries

## Immediate Next Execution Order

1. Re-establish S21 runtime on an isolated port from the main
   `sync-engine-refactor` worktree.
2. Log in as admin and use a fresh admin-owned test project.
3. Run the pay-app/export artifact sync proof first:
   - create/export
   - sync
   - inspect SQLite / `change_log` / Supabase / storage
4. Run replace, delete, retry/restart, and fresh-pull proof for the same
   tables.
5. Extend the same style of proof to `form_exports`, `entry_exports`,
   `support_tickets`, and `user_consent_records`.
6. Only after sync proof is strong enough, return to the remaining export-format
   and device-level comparison polish.

## Runtime / Environment Notes

- All worktree content was migrated back onto `sync-engine-refactor` as commit
  `ed6027e4`.
- The stale verification worktrees were removed after the handoff content and
  runtime screenshots were copied back into the main repo.
- Backup recovery still exists in:
  - branch `codex/payapp-sync-short`
  - `C:\temp\payapp_sync_worktree.patch`
- Android native builds from deep Windows worktree paths are unreliable because
  `flusseract`/CMake resolves the real path; use the main repo path or another
  short real checkout path if a fresh short-path runtime becomes necessary.

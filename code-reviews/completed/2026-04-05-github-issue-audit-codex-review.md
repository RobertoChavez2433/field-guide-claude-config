# GitHub Issue Audit

Date: 2026-04-05
Repo: `Field-Guide/construction-inspector-tracking-app`
Branch audited: `sync-engine-refactor`

## Scope

Excluded per request:
- `#127` Bundle merging for multi-form export
- `#128` File list dialog for multi-file sharing UX
- `#129` Remote signed URL fallback for synced documents

Not treated as errors:
- `#133` reminder only
- `#178` enhancement / future lint-rule work

## Confirmed Current TODO

- [ ] `#198` ToS consent is requested again after signing back in
  Verified in code. Sign-out clears `consent_accepted` and in-memory consent state in `ConsentProvider.clearOnSignOut()`, and `AppBootstrap` calls that on every auth transition from signed-in to signed-out. This matches the reported behavior, so the issue is current.

- [ ] `#167` `verify-sync.ps1` loads the wrong credential source
  Verified in code. `tools/verify-sync.ps1` still reads root `.env` plus `.env.secret`, while the current sync test tooling reads `tools/debug-server/.env.test`. The mismatch explains the invalid-key failures and is still present.

- [ ] `#166` Entry PDF export omits attached photos after direct photo injection
  Verified in code. PDF export uses `_photoManager.photos`, and `PhotoAttachmentManager` only snapshots provider state when `loadPhotos()` runs. The driver endpoint `/driver/inject-photo-direct` writes directly through the repository and does not refresh the manager/provider state afterwards, so export can still see `0` photos.

- [ ] `#89` SQLite encryption (`sqlcipher`)
  Verified unresolved. The app still uses plain `sqflite` / `sqflite_common_ffi` and plain `openDatabase()`; there is no `sqlcipher` dependency or encrypted-open path in the current branch.

- [ ] `#42` pdfrx rendering fails silently in background isolates
  Verified as an active limitation. `PdfImportHelper` still documents that the background-isolate path silently fails and explicitly routes import work onto the main thread as a workaround.

- [ ] `#91` PDF OCR blocker: Item 38 superscript `th` becomes `"`
  Still marked open in shared project state on 2026-04-05. I did not re-run the OCR flow locally, but there is no evidence in the current branch that this parked blocker was fixed.

- [ ] `#92` PDF OCR blocker: Item 130 whitewash destroys `y` descender
  Still marked open in shared project state on 2026-04-05. I did not re-run the OCR flow locally, but there is no evidence in the current branch that this parked blocker was fixed.

- [ ] `#186` Lint: `require_soft_delete_filter` — 43 violations
  Verified by current GitHub quality-gate issue update on 2026-04-05. Mostly test-code debt, but still current.

- [ ] `#187` Lint: `no_direct_database_construction` — 4 violations
  Verified by current GitHub quality-gate issue update on 2026-04-05.

- [ ] `#188` Lint: `no_silent_catch` — 4 violations
  Verified by current GitHub quality-gate issue update on 2026-04-05.

- [ ] `#189` Lint: `avoid_raw_database_delete` — 3 violations
  Verified by current GitHub quality-gate issue update on 2026-04-05.

- [ ] `#190` Lint: `path_traversal_guard` — 4 violations
  Verified by current GitHub quality-gate issue update on 2026-04-05.

- [ ] `#191` Lint: `no_skip_without_issue_ref` — 2 violations
  Verified by current GitHub quality-gate issue update on 2026-04-05.

- [ ] `#194` Lint: `max_import_count` — 1 violation
  Verified by current GitHub quality-gate issue update on 2026-04-05.

- [ ] `#195` Lint: `cached_connectivity_recheck` — 2 violations
  Verified by current GitHub quality-gate issue update on 2026-04-05.

- [ ] `#196` Lint: `sync_time_on_success_only` — 1 violation
  Verified by current GitHub quality-gate issue update on 2026-04-05.

- [ ] `#197` Lint: `no_late_sync_dependencies` — 2 violations
  Verified by current GitHub quality-gate issue update on 2026-04-05.

## Needs Runtime Repro

- [ ] `#164` Startup sync pushes daily entry into Supabase RLS denial
  The issue reference is stale because `sync_orchestrator.dart` no longer exists on this branch, but I also did not find a clear static proof that the underlying push-eligibility bug is fixed. This needs a live sync repro against Supabase on the refactored engine.

- [ ] `#165` Basic navigation still throws RenderFlex overflow errors
  The issue is based on Android runtime logs. I did not run the Android app in this audit, so this remains unverified but still plausible.

- [ ] `#152` `RangeError (index): Invalid value: Valid value range is empty: 0`
  The GitHub issue is only a Sentry shell with no usable stack or repro in the repo. This needs Sentry details or a fresh local reproduction before it can become actionable.

## Likely Stale / Resolved

- [x] `#163` Project setup inline contractor creation lost HTTP-driver keys
  Resolved in current source. `_InlineContractorCreationCard` now includes `contractor_name_field` and `contractor_save_button`.

- [x] `#169` Project setup contractor type selector is not driver-addressable
  Resolved in current source. The edit UI exposes `contractor_editor_done_button`, `contractor_type_prime`, and `contractor_type_sub`.

- [x] `#170` Manual pay item dialog saves default `FT` after `TON` is selected
  Resolved in current source. The dialog updates `_selectedUnit` in `onChanged` and persists `unit: _selectedUnit` on save.

- [x] `#168` Closing entry PDF preview triggers deactivated-widget ancestor lookup
  Likely resolved by refactor. The current preview flow pushes a dedicated `EntryPdfPreviewScreen` and no longer uses the old dialog callback pattern described in the issue.

## Redundant / Non-Actionable

- [x] `#151` Sentry RenderFlex overflow issue
  Redundant with `#165`. Keep the human-written defect, close the generic Sentry duplicate.

- [x] `#153` User feedback: "Buggy application"
  Non-actionable. No stack, no repro, no scoped symptom.

## Notes

- I ran targeted Flutter tests for consent/bootstrap behavior:
  - `test/core/di/app_bootstrap_test.dart`
  - `test/features/settings/presentation/providers/consent_provider_test.dart`
  Result: pass.

- I could not complete a local `dart run custom_lint` verification because the tool crashes on this Windows workspace while walking a stale `windows/flutter/ephemeral/.plugin_symlinks/...` path. For lint issues, I relied on the GitHub quality-gate issues, which were all updated on 2026-04-05 and therefore are current.

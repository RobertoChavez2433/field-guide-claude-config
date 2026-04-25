# Master Audit Tracker — Pre-Beta Blocker + Issue Punch List

**Generated:** 2026-04-25
**Sources:**
- `code-reviews/2026-04-24-preprod-audit-notion-final.md` — 7 blockers + 19 secondary findings (audit against HEAD `50d2c470`)
- 40 open GitHub issues (`gh issue list --state open`, snapshot in `_audit_research/gh_issues.json`)

**Verification method:** parallel debug-research agents (8 lanes) cross-checked each finding against the live working tree on `main` (post-`50d2c470`). Each entry is annotated with current STATUS based on what the agents could read in the tree right now.

**Status legend:**
- `[ ]` open / still-valid in code
- `[~]` partially fixed (mitigation present, gap remains)
- `[x]` fully fixed in code (recommend close on GH issue / strike from audit)
- `[?]` cannot verify from code alone (needs runtime / device repro)

**Goal:** clear all 5–7 audit blockers + every still-valid GitHub issue. Items confirmed fully-fixed should be closed without further work.

---

## End-Goal Acceptance Criteria

The internal-POC `CONDITIONAL GO` flips to `GO` when **all** of the following are true:

1. All four Sprint-1 audit blockers (B1, B2, B3, B4) are `[x]` with merged behavior tests.
2. All Sprint-2 architecture blockers (B5, B6, B7) are at least `[~]` with a documented landing plan.
3. Every GitHub issue currently labeled `bug` / `defect` / `blocker` is either `[x]` or has an explicit decision recorded (parked, cannot-repro, won't-fix).
4. One full pass of `flutter analyze`, `dart run custom_lint`, and `flutter test` runs green from a clean candidate commit (Sprint-6 exit criterion still unmet from prior audit).
5. One nightly sync-soak harness pass green on the same candidate commit.

---

## Section 1 — Sprint 1 Blockers (Internal POC Gating)

These four blockers are what the audit names as the difference between `CONDITIONAL GO` and `GO` for the 4–5-person internal POC.

### `[ ]` B1 — `PersistPayAppExportUseCase.execute` double-delete + leaked-artifact paths · CRITICAL

**Status:** `still-valid` (line numbers match audit exactly; behavior unchanged since `50d2c470`)

**File:** `lib/features/pay_applications/domain/usecases/persist_pay_app_export_use_case.dart`

**Three confirmed defects:**

1. **Double-delete on rollback (`:120-129`)** — catch block runs a guarded `_deleteLocalFile(localPath)` at `:125` and an unconditional `_deleteLocalFile(localPath)` at `:127`. Both delete the same just-written file. The guarded branch is also semantically wrong (it should be deleting `existingArtifact.localPath`, not `localPath`).

```dart
} on Object catch (error) {
  Logger.db('[PersistPayAppExportUseCase] persistence failed: $error');
  if (replaceTarget &&
      existingArtifact?.localPath != null &&
      existingArtifact!.localPath != localPath) {
    await _deleteLocalFile(localPath);     // :125 — wrong target
  }
  await _deleteLocalFile(localPath);       // :127 — duplicate of guarded path
  rethrow;
}
```

2. **Duplicated post-success delete + contradictory log (`:131-169`)**:
   - `:131-138` and `:156-162` are byte-identical predicates and bodies.
   - `:149-154` fires `'Copy persistence retained source artifact ... it was not replaced.'` whenever `replaceTarget` is true — i.e., it logs the inverse of what just happened.
   - The `else if` at `:163-168` re-runs the same delete when the first `if` falls through, with overlapping conditions.

3. **Replace-branch missing rollback (`:81-102`)** — when `existingArtifact == null && replaceTarget == true`, the code creates an artifact row at `:84-92` and updates the pay-application at `:95-102`. If the update throws, the new artifact row stays; the catch block then deletes the local file out from under it. The non-replace branch at `:110-118` already does this rollback correctly — mirror it.

**Direct production impact:** GitHub issue **#288** (`DatabaseException FOREIGN KEY constraint failed` on `UPDATE pay_applications`) and **#289** (`Bad state: Failed to update pay application.`) are both Sentry-captured productions of this exact code path. Closing B1 closes #288 and #289.

**Required fix:**
- [ ] Collapse `:131-169` to a single post-success cleanup block: delete prior file iff `existingArtifact != null && existingArtifact.localPath != localPath`.
- [ ] Drop the `_deleteLocalFile(localPath)` call at `:125`. Keep only `:127`.
- [ ] In the replace branch at `:81-102`, on `existingArtifact == null && replaceTarget == true`, on pay-app `update` failure, delete the artifact row created at `:85-92` before rethrowing — mirror the non-replace branch's `:114` rollback.
- [ ] Remove or invert the misleading `Copy persistence retained source artifact` log at `:149-154`.
- [ ] Add a behavior test that drives `persistSuccessful == false` on the replace path and asserts no orphan artifact row or file remains.

**Cross-issue dependency:** B5 (`path_provider` in `domain/`) lives in the same file. Fix together.

---

### `[~]` B2 — Sync-repair failure signal durably written but no consumer · HIGH

**Status:** `partially-fixed` — UI consumer chain landed AFTER the audit was written. The audit's premise ("no consumer") is no longer accurate. Remaining gap: dashboard-actions tile gating.

**Write path (unchanged from audit):**
- `lib/features/sync/application/sync_state_repair_runner.dart:96-107` — writes `sync_repair_failure::<jobId>` metadata with `{repair_required: true, failed_at, error}` on repair exception.
- `lib/features/sync/application/sync_recovery_service.dart:37-58` — re-runs pending repairs before sync resumes.

**Read path (NEW, post-audit):**
- `lib/features/sync/application/sync_query_service.dart:226-300` — `getStateFingerprint()` now loads `failureMetadataPrefix`, parses each entry, exposes `failedRepairCount`, `latestFailedRepairJobId`, `latestRepairFailureAt`.
- `lib/features/sync/presentation/providers/sync_provider_listeners.dart:137,154-157,204-215` — listener reads `fingerprint.failedRepairCount`, calls `_publishRepairRequiredNotice` which adds an in-app banner: `"$currentCount sync repair $jobLabel failed on this device. Open Sync Status and rerun repair before trusting sync is clean."`
- `lib/features/sync/presentation/providers/sync_provider.dart:123-129,136` — `hasRepairRequiredAttention` feeds `hasSyncAttention`.
- `lib/features/sync/presentation/widgets/sync_status_icon.dart:74,85,96` — app-bar icon turns `cs.error` red, switches to `Icons.sync_problem`, tooltip becomes `'Sync repair required'`.
- `lib/features/sync/presentation/providers/sync_provider_status_text.dart:11-15` — status text renders `'Repair required'` / `'$n repairs required'`.

**Remaining gap:** `lib/features/sync/presentation/widgets/sync_dashboard_actions_section.dart:110` gates its "Fix Sync Issues" tile on `controller.blockedCount > 0`, not `failedRepairCount > 0`. If only repair failures exist (no blocked changes), the dashboard tile does not light up, and the operator must spot the app-bar icon or in-app notification banner. Functional path to `rerunKnownRepairs()` is intact via the existing repair tile, but the dedicated "Fix Sync Issues" tile is gated on the wrong field.

**Required fix:**
- [ ] Either widen the dashboard-actions tile gate at `sync_dashboard_actions_section.dart:110` to `controller.blockedCount > 0 || controller.failedRepairCount > 0`, OR add a dedicated "Repairs failed" tile.
- [ ] Document the retry-budget policy in code or `.claude/rules/sync/sync-patterns.md` (after N failed retries, quarantine the affected scope and stop retrying until operator action).
- [ ] Add a behavior test that seeds a failing repair marker, launches the recovery service, and asserts the banner + status icon + dashboard tile are surfaced.

---

### `[ ]` B3 — `ValueNormalizer.normalize` PDF heuristic-gate violation · HIGH

**Status:** `still-valid`. Audit cited `:497-528`; current location is `lib/features/pdf/services/extraction/stages/value_normalizer.dart:275-321` — the file was reorganized post-audit but the heuristic block is unchanged. Behavior identical.

**File:** `lib/features/pdf/services/extraction/stages/value_normalizer.dart`
**Function:** `_repairQuantityFromDescriptionContext` at `:275-321`

```dart
if (normalizedUnit == 'FT' &&
    RegExp(r'^Pavt Mrkg,\s*Sprayable Thermopl,\s*6 inch,\s*Yellow$',
        caseSensitive: false).hasMatch(text) &&
    RegExp(r'^50[.,]\s*0\s*0$', caseSensitive: false).hasMatch(raw)) {
  return 60.0;
}

if ((normalizedUnit == 'SFT') &&
    RegExp(r'^Sign,\s*Type B,\s*Temp,\s*Prismatic,\s*(?:Furn|Oper)$',
        caseSensitive: false).hasMatch(text)) {
  if (RegExp(r'^15[CO0]\s*88$', caseSensitive: false).hasMatch(raw)) return 450.0;
  if (raw == '150' && quantity == 150.0) return 450.0;
}

if ((normalizedUnit == 'SYD' || normalizedUnit == 'SY') &&
    RegExp(r'^_?\s*Cold Weather Protection,\s*Conc Pavt$',
        caseSensitive: false).hasMatch(text) &&
    raw == '110.000' && quantity == 110.0) {
  return 116.0;
}
```

**Rule violated:** `.claude/rules/pdf/pdf-extraction-testing.md` — "Never branch on document key, PDF name, fixture path, agency, contractor, county, expected text, or one item number."

**Risk:** any future PDF whose pay-item description matches one of the three regexes with a legitimately-different quantity will be silently overwritten to the hardcoded value (60.0 / 450.0 / 116.0).

**Required fix:**
- [ ] Delete the three branches at `value_normalizer.dart:275-321`.
- [ ] If the underlying OCR misreads (`15C 88 → 450`, `50.00 → 60.0`, `110.000 → 116.0`) are real recurring digit-confusion patterns, lift them into the OCR repair catalog (digit-confusion side) or express as a broad arithmetic consistency rule (`bid_amount / unit_price == quantity`).
- [ ] Verify the companion part file `lib/features/pdf/services/extraction/stages/value_normalizer_steps.dart` does not contain a second copy of these heuristics.
- [ ] Rerun the full-corpus PDF replay; record which fixtures regress and whether each regression is a real OCR error or a stale fixture.

---

### `[ ]` B4 — Migration test coverage trails runtime by 15 versions · HIGH

**Status:** `still-valid`. No new migration tests have been added since the audit.

**Runtime:** `lib/core/database/database_service.dart:71` and `:112` — `version: 63`.
**Schema assertion:** `test/core/database/database_service_test.dart:228` — `expect(version, equals(63));` (audit cited line 488; file was reorganized but assertion still pins v63).

**Existing dedicated migration tests:** v42, v43, v47, v57, v58, v61 (6 files). Plus `project_assignment_changelog_repair_test.dart` partially covers v56.

**Missing dedicated upgrade-from-N tests:** v44, v45, v46, v48, v49, v50, v51, v52, v53, v54, v55, v59, v60, v62, v63 (15 versions).

**Highest-risk uncovered transitions (per audit):**
- v48 — inspector_forms trigger rebuild
- v50 — soft-delete column additions
- v52 — export_artifacts + pay_applications new tables with backfill
- v54 — signature_files + signature_audit_log
- v55 — support_tickets canonical rebuild
- v59 — support_tickets.issue_code (audit specifically called this out)
- v60 — todo_items review-comment columns
- v62 — file_sync_state_log
- v63 — current runtime version, no test at all

**Required fix:**
- [ ] Add migration tests for `v48`, `v50`, `v52`, `v54`, `v55`, `v59`, `v60`, `v62`, `v63` following the `v58` / `v61` pattern: open DB at version `N-1` with realistic partial schema, run `DatabaseUpgradeRepairs.applyLateMigrations` or specific step, assert end-state schema / column / trigger / index presence.
- [ ] Introduce `test/_helpers/migration_fixture.dart` that produces a DB at any target version, so each new migration test becomes a two-line fixture call.
- [ ] Optionally re-execute `v43`, `v57`, `v58` tests live against the current tree to confirm they still pass.

---

## Section 2 — Sprint 2 Blockers (Architecture)

### `[ ]` B5 — `path_provider` imported inside `domain/usecases/` · HIGH

**Status:** `still-valid`. Both audited imports persist verbatim.

**Files:**
- `lib/features/pay_applications/domain/usecases/persist_pay_app_export_use_case.dart:4` — `import 'package:path_provider/path_provider.dart';`
- `lib/features/entries/domain/usecases/export_entry_use_case.dart:5` — same import.

**Rule violated:** `.claude/rules/architecture.md` — "Keep domain code pure Dart. No Flutter imports in `domain/`."

**Companion finding (not in audit):** Grep across `lib/features/**/domain/**` shows seven domain files importing `dart:io`. `dart:io` is core Dart (not strictly Flutter) but couples domain to filesystem/HttpClient/Process and prevents web targets. Files:
- `lib/features/entries/domain/usecases/export_entry_use_case.dart:2`
- `lib/features/entries/domain/usecases/entry_pdf_export_use_case.dart:1`
- `lib/features/settings/domain/usecases/submit_support_ticket_use_case.dart:1`
- `lib/features/pay_applications/domain/usecases/delete_export_artifact_use_case.dart:1`
- `lib/features/forms/domain/usecases/export_form_use_case.dart:1`
- `lib/features/forms/domain/usecases/sign_form_response_use_case.dart:1`
- `lib/features/pay_applications/domain/usecases/persist_pay_app_export_use_case.dart:1`

No other Flutter-plugin imports leak into domain (verified: no `package:flutter/`, `flutter_secure_storage`, `shared_preferences`, `package_info_plus`, `device_info_plus`).

**Required fix:**
- [ ] Move filesystem concerns into a data-side owner. `lib/features/pay_applications/data/services/export_artifact_file_service.dart` already exists and uses `File`; extend it (or add a sibling) to resolve and expose directories.
- [ ] Inject the resolved directory or an artifact-file service through the repository seam — use case receives a path/stream/service, not the plugin.
- [ ] Remove `path_provider` and `dart:io` imports from both flagged use cases.
- [ ] Decide policy on the other 5 `dart:io`-importing domain use cases — likely needs a sibling fix pass.

---

### `[~]` B6 — Driver gesture handler oversize + duplicated widget tables · HIGH

**Status:** `partially-fixed`. Recent commit `777aa391 refactor(core): split driver route hotspots` extracted parts of the file. Gesture-routes file shrank from 842 → 316 lines. Duplicated widget tables reduced from 3 sites to 2. `_handleScrollToKeyRoute` and the `as dynamic` type-safety hole are unchanged — only relocated.

**Current line counts:**
- `lib/core/driver/driver_interaction_handler_gesture_routes.dart` — **316** (was 842) ✓
- `lib/core/driver/driver_interaction_handler_navigation_routes.dart` — 474
- `lib/core/driver/driver_shell_handler.dart` — 280
- `lib/core/driver/driver_widget_inspector.dart` — 521
- `lib/core/driver/driver_interaction_handler_scroll_to_key_route.dart` — NEW; `_handleScrollToKeyRoute` at `:3-283` (~280 lines, function size unchanged).
- `lib/core/driver/driver_interaction_handler_tap_callbacks.dart` — NEW; holds `_canInvokeDriverTapCallback` (`:3-18`) and `_invokeDriverTapCallback` (`:20-74`) extracted from gesture_routes.

**Remaining defects:**
1. **`_handleScrollToKeyRoute` is still 280 lines, single function** — only relocated, not decomposed.
2. **Widget-type table still duplicated in two places** — `driver_interaction_handler_tap_callbacks.dart:3-74` and `driver_shell_handler.dart:118-147` independently re-list `ElevatedButton, TextButton, OutlinedButton, FilledButton, IconButton, InkWell, GestureDetector, AppGlassCard, AppListTile, AppChip, AppInfoBanner, AppErrorState, ListTile`.
3. **`as dynamic` type-safety hole unchanged** at `driver_shell_handler.dart:120-124`:
   ```dart
   if (widget is ElevatedButton || widget is TextButton ||
       widget is OutlinedButton || widget is FilledButton) {
     enabled = (widget as dynamic).onPressed != null;
   ```

**Required fix:**
- [ ] Hoist `_canInvokeDriverTapCallback` / `_invokeDriverTapCallback` / the widget-type table into `DriverWidgetInspector` as a single `tapCallbackFor(Widget)` / `widgetEnabledState(Widget)` surface. All call sites consume the same policy.
- [ ] Replace the `as dynamic` cast with an explicit per-type switch or sealed helper.
- [ ] Decompose `_handleScrollToKeyRoute` — extract local async closures into named private helpers; split the `maxScrolls * 2` body so the loop reads top-to-bottom.

---

### `[ ]` B7 — Third-party `*_patched/` trees missing patch manifests · HIGH

**Status:** `still-valid`.

**Vendored trees with no manifest:**
- `third_party/custom_lint_patched/` — verbatim upstream README, no PATCHES.md, no .patch files.
- `third_party/dartcv4_patched/` — same.
- `third_party/printing_patched/` — same.

**`pubspec.yaml` overrides (lines 207-227, audit said 208-222 — minor drift):**
- `custom_lint` override has WHY comment (Windows symlink crash).
- `dartcv4` override has WHY comment (Windows MSVC / vc17 runtime shim).
- **`printing` override at `pubspec.yaml:220-221` has NO WHY comment** — the next WHY comment (lines 222-225) belongs to `package_info_plus` / `device_info_plus`.

**Required fix:**
- [ ] Add a `PATCHES.md` to each vendored tree enumerating exact files changed vs upstream version, the upstream version tag, and the rationale.
- [ ] Add a WHY comment block at `pubspec.yaml:220-221` for the `printing` override.
- [ ] (Optional) Replace vendoring with pinned forks on GitHub whose branch name encodes the patch summary (`v5.12.0-windows-symlink-fix`), so `pub get` can pin to a diff-visible commit.

---

## Section 3 — Secondary Hygiene Findings (Medium / Low)

### Medium

#### `[ ]` H1 — Stale `go_router` recommendation in project + rule docs

`.claude/CLAUDE.md:45` and `.claude/rules/frontend/flutter-ui.md:15` still recommend `go_router`. Zero `go_router` imports remain in `lib/`. AutoRoute migration is complete.

**Fix:** swap each recommendation line to: "Prefer `AppNavigator` / `context.appGo` / `context.appPush` over raw `Navigator`. Route definitions live in `lib/core/router/autoroute/` and `lib/core/navigation/`."

#### `[~]` H2 — Stale `sync_orchestrator.dart:NNN` line refs

Audit said 25+ across 13 files. Current count is **17 across 7 files**: `sync_diagnostics.dart` (2), `sync_error.dart` (1), `connectivity_probe.dart` (1), `post_sync_hooks.dart` (3), `sync_query_service.dart` (5), `sync_retry_policy.dart` (1), `sync_error_classifier.dart` (4). Six of the audit-listed files were already cleaned.

**Fix:** strip remaining `FROM SPEC: sync_orchestrator.dart:NNN` and `WHY: ... SyncOrchestrator...` tags in those 7 files.

#### `[ ]` H3 — `SyncRunMetrics` missing from sync domain barrel

`lib/features/sync/domain/domain.dart:5-9` exports five files; does NOT export `sync_run_metrics.dart`. `SyncResult`, `SyncDiagnostics`, `SyncEngineEvent` all expose `SyncRunMetrics`.

**Fix:** add `export 'sync_run_metrics.dart';` to `domain.dart`.

#### `[x]` H4 — `SyncEngine.pushAndPull` overshoots 250-line budget — **CLOSED**

Audit said file was 437 lines, method 181 lines. Current `lib/features/sync/engine/sync_engine.dart` is **315 lines**; `pushAndPull` runs `:99-156` (**58 lines**), delegates to `_executeSyncEngineModeCycle` and `_finishFreshSyncCycle` in `sync_engine_run_phases.dart`. The audited overshoot is gone.

**Action:** strike from audit. No work required.

#### `[ ]` H5 — `temp_restore_test_project` migration debris

`supabase/migrations/20260327200002_temp_restore_test_project.sql` exists. Disables triggers on 17 tables and nulls `deleted_at` for project UUID `2e568469-4376-42e2-b24f-b4b445e6f3e9`.

**Fix:** can't delete an already-applied migration. Add a clear header comment marking it historical-only-must-never-be-edited-as-template. Move future ad-hoc data rescues to `supabase/adhoc/`.

#### `[ ]` H6 — Repair-job catalog has 17 entries with no eviction policy

`lib/features/sync/application/sync_state_repair_runner.dart:39-57` registers exactly 17 jobs spanning 2026-04-08 through 2026-04-24. `repairCatalogVersion = '2026-04-24.1'` at line 28. No eviction logic.

**Fix:** document a retention policy: once a repair ID is satisfied by a later schema migration, tombstone and remove from `defaultJobs`.

#### `[ ]` H7 — Legacy `lib/core/theme/*` re-export shims

- `theme.dart` — 0 consumers in `lib/`
- `field_guide_colors.dart` — 0 consumers in `lib/`. Header self-says: "All 4 re-export shims ... will be cleaned up in Phase 6."
- `design_constants.dart` — 0 consumers
- `colors.dart` — 1 consumer: `lib/features/entries/presentation/utils/weather_helpers.dart:2`

**Fix:** update `weather_helpers.dart` to import from the new design-system entry, then delete all four shim files.

#### `[~]` H8 — `shared.dart` barrel has dormant export lines

Audit framing was wrong about the barrel itself ("dormant"). The barrel has **171 importers** in `lib/`. Per-line dormancy claim cannot be verified without symbol-resolution; `preferences_service.dart` has 19 direct importers (audit said 22) but none through the barrel.

**Fix:** either (a) drop the dormant lines after running a symbol-level audit through CodeMunch, or (b) leave as-is — barrel is heavily used, the cost of cleanup is low priority.

#### `[ ]` H9 — `PermissionDialog.showStoragePermissionDialog` zero call sites

`lib/shared/widgets/permission_dialog.dart` is the only Dart hit for `showStoragePermissionDialog` and `PermissionDialog`.

**Fix:** delete `permission_dialog.dart`, `lib/shared/widgets/widgets.dart`, and the export line from `shared.dart`. Drops the entire `lib/shared/widgets/` directory.

#### `[~]` H10 — `pay_app_import_parser.dart` regex typo + size

Audit said file was 475 lines (over 300-line cap). Current path is `lib/features/pay_applications/data/services/pay_app_import_parser.dart`, **195 lines** — under cap.

**Remaining defect:** regex typo at `:185` survived: `RegExp(r'[^0-9.\\-]')` should be `RegExp(r'[^0-9.\-]')`. The literal backslash-character is matching cell content with backslashes, which is wrong.

**Fix:** fix regex typo. The size finding can be marked `[x]`.

#### `[~]` H11 — Orphan scripts/tools (16 files audit, 12 truly orphan in tree)

Of the 16 audit-listed files, only 4 have any inbound reference:
- `scripts/cleanup_google_ocr_research.ps1` — referenced by `test/features/pdf/extraction/PDF_HARDENING.md:198-199`.
- `scripts/run_patrol.ps1` / `scripts/run_patrol_debug.ps1` — README + self-doc only.
- `scripts/flutter_run_endpoint.ps1` — invoked by `tools/start-driver-flutter-run.ps1:341, 395`. **In use.**
- `tools/build_golden_from_run.dart` — self-reference only.
- `tools/create-defect-issue.ps1` — self-reference only; **also violates `.claude/CLAUDE.md` rule "Do not create `.claude/defects/*`".**

The other 11 (`bring_window`, `fix_taskbar`, `list_windows`, `check_virtual_desktop`, `view_pdf_logs`, `validate_feature_spec`, `validate_ui_structure`, `validate_retired_flow_ids`, `dump_inspect`, `gocr_trace_viewer`, plus `cleanup_google_ocr_research`) are orphans.

**Fix:** delete the 11 orphans + `create-defect-issue.ps1`. Refresh `README.md:74`. Keep `flutter_run_endpoint.ps1`.

#### `[ ]` H12 — Integration-test giant `main()` bodies (grew since audit)

| File | Audit lines | Current lines | testWidgets count |
|---|---|---|---|
| `integration_test/cell_crop_diagnostic_test.dart` | 172 | **209** | 1 |
| `integration_test/grid_removal_diagnostic_test.dart` | 383 | **497** | 1 |
| `integration_test/springfield_report_test.dart` | 469 | **604** | 1 |
| `integration_test/pre_release_pdf_corpus_test.dart` | 245 | **347** | 1 |

**Fix:** split each `main()` body into `group(...) { test(...); test(...); }` blocks keyed on stage (cell crop, grid removal, comparison, regression). Single-`testWidgets` wrapping defeats per-stage failure localization.

#### `[ ]` H13 — Hand-written `OcrCropPageResult` (de)serializer

`lib/features/pdf/services/extraction/stages/ocr_page_recognition_worker_payload.dart:304-473` (audit said `:304-472`, off by one). Cyc complexity 62 per CodeMunch.

**Fix:** convert to `freezed`-generated `toJson`/`fromJson`, OR add a round-trip property test asserting every record field appears in both maps, eliminating silent-data-loss risk on the isolate boundary.

#### `[ ]` H14 — Raw `FilledButton` in `inline_contractor_chooser.dart:94`

Confirmed. `Cancel` uses `AppButton.text`, but `Done` uses raw `FilledButton(onPressed: onDone, child: const Text('Done'))`.

**Fix:** replace with `AppButton.primary(label: 'Done', onPressed: onDone)`.

#### `[ ]` H15 — `AuthProvider` constructs `FlutterSecureStorage` directly

`lib/features/auth/presentation/providers/auth_provider.dart:24` imports it, `:48` holds it, `:83-92` accepts an optional override and falls back to `const FlutterSecureStorage()`. `SecureStorageGateway` already abstracts this for `CheckInactivityUseCase` and `SignOutUseCase`.

**Fix:** route AuthProvider through `SecureStorageGateway`; remove direct `FlutterSecureStorage` import + constructor fallback.

#### `[ ]` H16 — Duplicate `last_active_at` cleanup

`lib/features/auth/presentation/providers/auth_provider_security_actions.dart:43-49` and `lib/features/auth/domain/usecases/sign_out_use_case.dart:60-67` both delete the secure-storage key `'last_active_at'`. `check_inactivity_use_case.dart:18` also reads it.

**Fix:** centralize cleanup in `SignOutUseCase` (or new `SecurityStorageCleanup`). Route `forceReauthOnly()` / `signOutLocally()` through it.

### Low

#### `[ ]` H17 — Dormant DS components

- `lib/core/design_system/atoms/app_avatar.dart` — `AppAvatar` has 0 consumers.
- `lib/core/design_system/animation/app_container_transform.dart` — `AppContainerTransform` has 0 consumers.
- `lib/core/design_system/surfaces/app_sticky_header.dart` — `AppStickyHeader` has 0 consumers.

**Fix:** confirm with design owner and delete, or leave a `// WHY: reserved for <feature>` note.

#### `[~]` H18 — Per-feature testing-keys shim files

Audit said 16 shim files. Actual count is 16 three-line shims + `forms_keys.dart` (215 lines, no longer a shim) + `testing_keys.dart` barrel (24 lines) + `screen_sentinel_catalog.dart` (80 lines).

**Fix:** collapse the 16 three-line shims into `testing_keys.dart` `show`-clauses; update `screen_sentinel_catalog.dart` import; leave `forms_keys.dart` alone.

#### `[ ]` H19 — Unused `StackTrace` parameters in `auth_sync_listener_bootstrap`

`lib/core/bootstrap/auth_sync_listener_bootstrap.dart:161-167` and `:307-317` declare `StackTrace stackTrace` in `catchError` signatures but never pass it to `Logger.error(..., stack: stackTrace)`.

**Fix:** swap `Logger.sync(...)` to `Logger.error(..., error: error, stack: stackTrace, category: 'sync')` in both callbacks.

---

## Section 4 — GitHub Issues: Recent Sentry / Config (305-311)

### `[x]` #311 — `PostgrestException: column user_consent_records.updated_at does not exist` (42703) — **CLOSED**

**File:** `lib/features/sync/adapters/consent_record_adapter.dart`
- `:42` — `bool get insertOnly => true;`
- `:49` — `bool get skipPull => true;` with comment naming the 42703 prevention.
- `:54` — `bool get skipIntegrityCheck => true;`
- `lib/features/sync/engine/integrity_checker.dart:163-165` honors the skip.

Server schema confirmed: `supabase/migrations/20260329000001_consent_and_support_tables.sql:8-15` defines `user_consent_records` without `updated_at`. The adapter now never queries it.

**Action:** close GH issue #311 — code path is sealed.

---

### `[x]` #308 — Log Drain server-side scrubbing — **CLOSED**

**File:** `supabase/functions/_shared/log_drain_sink.ts`
- `:7` — email regex.
- `:10-11` — UUID-in-WHERE regex covering `id|user_id|project_id|company_id|record_id`.
- `:12, 27-28` — `raw_user_meta_data` redaction (string + key + JSON shape).
- `:39-41` — consent gate: drops payload when `consent !== true`.
- Test coverage: `supabase/functions/_shared/log_drain_sink.test.ts:6-36` asserts each scrub plus consent gate.

**Action:** close GH issue #308 — sink wraps every forwarded log; tests cover all three categories.

---

### `[~]` #307 — Service-role key exclusion preflight — **PARTIALLY**

**Workflow guard:** `.github/workflows/quality-gate.yml:593-601` — preflight throws if `STAGING_SUPABASE_SERVICE_ROLE_KEY` is set, but only when `steps.sync_changes.outputs.sync == 'true'`.

**Harness guard:** `integration_test/sync/harness/harness_auth.dart:79-87` — runtime check throws `StateError` if any env key contains `SERVICE_ROLE`. Correct and broad.

**Gaps:**
1. Workflow preflight only fires on sync-path PRs.
2. Bare `SUPABASE_SERVICE_ROLE_KEY` (no `STAGING_` prefix) is not scanned anywhere in `.github/workflows`.
3. Preflight reads `env.STAGING_SUPABASE_SERVICE_ROLE_KEY` from a workflow-level env that is never declared — sees empty string in normal CI even if the key were misconfigured at job/step level.

**Required fix:**
- [ ] Run preflight unconditionally (drop the `sync == 'true'` gate).
- [ ] Match both `STAGING_SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_SERVICE_ROLE_KEY`.
- [ ] Read from `${{ secrets.* }}` and from job-level `env:` not workflow-level.

---

### `[ ]` #306 — Raw `recordId` in RLS (42501) denials reaches Sentry

**Leak point:** `lib/features/sync/engine/push_error_handler.dart:144-145`:
```dart
if (classified.kind == SyncErrorKind.rlsDenial) {
  Logger.error('RLS DENIED (42501): ${change.tableName}/${change.recordId}');
```

**Pipe:** `Logger.error` → `LoggerErrorReporter.report` (`lib/core/logging/logger_error_reporter.dart:99-109`) → `LoggerSentryTransport.report` (`lib/core/logging/logger_sentry_transport.dart:81-93`) → `Sentry.captureMessage(message, ...)` with no UUID redaction.

**Why `beforeSendSentry` doesn't catch it:**
- `lib/core/config/sentry_pii_filter.dart:63-67` drops events only when `extra['eventClass'] == LogEventClasses.rlsDenial && extra.containsKey('recordId')`. The push-error-handler call puts the UUID **in the message string**, not in `extra`.
- `LogPayloadSanitizer.scrubString` (`lib/core/logging/log_payload_sanitizer.dart:75-111`) only redacts emails, JWTs, and key/value pairs — has no UUID regex.

**Note:** `lib/features/sync/engine/sync_error_classifier.dart:248-257` does NOT include `recordId` in its `Logger.sync(rlsDenial, data: {...})` payload. Classifier path is clean. Only the leak is in `push_error_handler.dart:145`.

**Required fix:**
- [ ] Hash (first 8 hex of SHA-256) or omit `recordId` in `push_error_handler.dart:145` log message.
- [ ] Add a UUID-redaction regex to `LogPayloadSanitizer.scrubString` as defense-in-depth.
- [ ] Assert in `beforeSendSentry` that any `rlsDenial`-classified message string contains no UUID-shaped substring.

---

### `[~]` #305 — Supabase seed must pair `auth.users` with `auth.identities` — **PARTIALLY**

**Pairing:** `supabase/seed.sql:151-207` inserts `auth.users` with `provider='email'`. `:231-254` inserts `auth.identities` with `identity_data = jsonb_build_object('sub', user_id::text, 'email', email, 'email_verified', true)`. Both inside `BEGIN; ... COMMIT;` (lines 12, 846) → atomic. ✓

**Gap:** no curl-based sign-in smoke test gating downstream tiers. Grep across `scripts/`, `.github/`, `supabase/`, `tools/` for `signInWithPassword`, `grant_type=password`, `/auth/v1/token` returned only `tools/testing/driver/RoleAccounts.ps1:182` — a developer helper, not a CI smoke gate.

**Required fix:**
- [ ] Add a curl-based sign-in step early in `quality-gate.yml` (and/or `staging-schema-gate.yml`) that fails the build before downstream tiers run if seeded credentials cannot exchange for a token.

---

## Section 5 — GitHub Issues: UI / Sync Errors (287-304)

### `[~]` #304 — Duplicate GlobalKey on S21 admin analytics nav switch

**Source:** `BUG-1f671deb5e` from `2026-04-16_2007_codex_ui_matrix_s21_admin` test run. Cell `s21__admin__analytics__nav_bar_switch_mid_flow`. **Route at failure was `/settings`, NOT analytics** — the duplicate key fires from a screen reachable via the bottom-nav switch from analytics.

**Existing scoped-key fixes (related):**
- `lib/core/driver/driver_keys.dart:6-11` — replaced an app-root `GlobalKey` with `ValueKey` after duplicate-key assertions during route transitions on the live Android driver build.
- `lib/features/projects/presentation/screens/project_setup_screen.dart:41-46` — `BUG-10` comment notes the same general failure mode; fixed by scoping to `projectId`.

**Audit of remaining bare `GlobalKey()` reachable from primary shell:**
- `lib/features/forms/presentation/screens/mdot_hub_screen_widgets.dart:13` — `final _sectionKeys = List.generate(3, (_) => GlobalKey())`. Scoped to `State`, likely safe.
- `lib/features/forms/presentation/screens/mdot_1126_form_screen.dart:58-60` — `Map<String, GlobalKey>` in `late final` initializer. Scoped to `State`, likely safe.
- `lib/features/analytics/presentation/screens/*` — declares no `GlobalKey` directly.

**Likely root cause:** at least one bare `GlobalKey()` somewhere on the `/settings` route is being reused across two route instances for one frame during the nav transition.

**Required fix:**
- [ ] Reproduce the matrix cell on S21 to capture a full stack with widget origin (the truncated Sentry-Logs payload doesn't reach an app frame).
- [ ] Audit `lib/features/settings/presentation/**` for any `GlobalKey()` reachable on `/settings`; scope to a stable per-route id, or downgrade to `ValueKey`/`UniqueKey` where identity isn't required.

---

### `[ ]` #303 — S21 UI E2E preflight starts with dirty sync queue

**Evidence:** preflight fingerprint `{blockedCount: 0, isSyncing: true, lastSyncTime: null, pendingCount: 10, unprocessedCount: 10}`. Test was at `/projects` route.

**Diagnosis:** **harness orchestration gap, not an app bug.**
- App: `lib/core/driver/driver_interaction_handler_preflight.dart:10-54` — `_assertInteractionReady` correctly observes `interactionReady`; with blockers it returns 409 with `state_sentinel_failed`.
- Driver maintenance routes (`lib/core/driver/driver_data_sync_handler_maintenance_routes.dart:1-60`) expose `sync`, `resetIntegrityCheck`, `injectSyncPoison`, `runSyncRepairs`, `removeFromDevice`, `restoreProjectRemote` — but **no "reset/truncate change_log" route**.
- The harness in `tools/testing/...` does not appear to call `runSyncRepairs` + drain before the matrix.

**Required fix:**
- [ ] Add a harness preflight step that polls `device_state` until `pendingCount == 0 && unprocessedCount == 0 && isSyncing == false`, OR fails the matrix run with a clear error.
- [ ] OR add an explicit driver "drain" route to `driver_data_sync_handler_maintenance_routes.dart`.
- [ ] File path: `integration_test/ui_matrix/` and `test/harness/ui_e2e_preflight.dart` (or wherever `preflight__s21__admin` originates).

---

### `[~]` #302 — Contractor name conflict raised as Sentry error

**Stack:** `base_list_provider.dart:77 createItem` ← `safe_action_mixin.dart:51 runSafeAction` ← `entry_contractors_section_actions.dart:212 createAndAddProjectContractor`.

**Confirmed chain:**
- `lib/features/contractors/data/repositories/contractor_repository_impl.dart:55-74` — `create` correctly returns `RepositoryResult.failure(...)` on duplicate name.
- `lib/shared/providers/base_list_provider.dart:71-86` — `createItem` wraps the failure in `RepositoryActionError` and rethrows inside `runSafeAction`.
- `lib/shared/providers/safe_action_mixin.dart:50-62` — `runSafeAction` catches `Exception` and calls `Logger.error('[$tag] $label failed', error: e, stack: stack)`.
- `lib/core/logging/logger_sentry_transport.dart:67` — `Logger.error` forwards to Sentry.

**Issue:** validation works, but `BaseListProvider.createItem` reports every duplicate-name validation failure to Sentry as an `error`. This is user input, not a defect. Same pattern affects locations and bid-item duplicate validation.

**Required fix:**
- [ ] In `safe_action_mixin.dart:50-62`, special-case `RepositoryActionError` — log at `Logger.ui` / `warn` level, do NOT escalate to Sentry.
- [ ] OR centralize: have `runSafeAction` accept a `domainErrors:` set; `Logger.error` only fires for errors NOT in that set.

---

### `[ ]` #301 — `TimeoutException after 0:00:05.000000: Future not completed`

**Source confirmed:**
- `lib/features/auth/data/repositories/app_config_repository.dart:26-46` — `fetchConfig` uses `.timeout(timeout)`; default 5s.
- `lib/features/auth/presentation/providers/app_config_provider.dart:42` — timeout `DesignConstants.fetchTimeout = Duration(seconds: 5)` (defined at `lib/core/design_system/tokens/design_constants.dart:44`).
- `app_config_provider.dart:162-228` — `checkConfig` runs through `runSafeAction`; `TimeoutException` extends `Exception`, gets logged via `Logger.error` → Sentry.

**Issue:** a 5s remote-config fetch timeout on flaky cellular is normal. App already has a fail-open fallback at `app_config_provider.dart:208-228`. But the timeout escalates to Sentry as an error.

**Required fix:**
- [ ] Catch `TimeoutException` explicitly in `app_config_provider.dart` (before `runSafeAction` wraps it) — route to `Logger.lifecycle` warn-level. Keep the existing fail-open fallback intact.
- [ ] Optionally widen the timeout to 10s for first-run/cold-start scenarios.

---

### `[?]` #300 — `AuthRetryableFetchException: Bad file descriptor` on token refresh

**Stack:** GoTrue retry path entirely inside `package:gotrue` (`fetch.dart:190`, `gotrue_client.dart:1114`). URL: `vsqvkxvvmnnhdajtgblj.supabase.co/auth/v1/token?grant_type=refresh_token`. Status: null. `Bad file descriptor` is a `dart:io` OS error from a closed/recycled socket.

**App-side handling already correct:**
- `lib/features/auth/services/auth_service.dart:163-168` — refreshSession callsite wraps with try/catch.
- `lib/features/sync/engine/supabase_sync.dart:415-426` — same.
- `gotrue_client` retries internally; `AuthRetryableFetchException` is thrown after retry budget is spent. Callers swallow it.

**Issue:** transient OS-level error not caused by app code. Sentry auto-issues each event, but production users see no functional impact.

**Required fix:**
- [ ] Filter `AuthRetryableFetchException` from `LoggerSentryTransport` (or `beforeSendSentry`) when `statusCode == null` and message contains `"Bad file descriptor"` / `"ClientException"`.

---

### `[x]` #295 — `Null check operator used on a null value` from `form_routes.dart:37` — **CLOSED (obsolete)**

Stack: `form_routes.dart:37 formRoutes.<fn>` ← `_CustomNavigatorState._buildPageForGoRoute.<fn>`. Reference is to a **go_router** path. Verified: `form_routes.dart` does NOT exist anywhere in `lib/`. AutoRoute migration is complete (`go_router` is fully gone — see audit Blocker 1 closure).

**Action:** close GH issue #295 — Sentry stack is from a pre-migration build that no longer ships.

---

### `[ ]` #294 — `NETWORKERROR: bid_items/14bf8045-d1d0-494f-8e74-551dd11b4339`

**Confirmed chain:**
- `lib/features/sync/engine/push_error_handler.dart:88-93` — when `classified.kind` is `networkError` or `rateLimited`, code calls `Logger.error('${classified.kind.name.toUpperCase()}: ${change.tableName}/${change.recordId}')`. That is the literal Sentry title we see.
- `lib/features/sync/engine/sync_error_classifier.dart:142-164` — `SocketException` and `TimeoutException` correctly classified as `networkError` with `retryable: true`.
- `lib/core/logging/logger_sentry_transport.dart:67` — `Logger.error` captures to Sentry on every retry attempt.

**Issue:** transient retryable network errors are intentionally retried, but the line-91 `Logger.error` reports each attempt as a Sentry error event. Net result: noisy alerts on conditions the sync engine already recovers from.

**Required fix:**
- [ ] Change the `networkError` / `rateLimited` branch in `push_error_handler.dart:90-93` to `Logger.sync` (or `Logger.warn`). Reserve `Logger.error` for the non-retryable branch at the bottom of the same handler.

Note: this is the exact same `recordId` field whose UUID-leak version is tracked under GH **#306** above. Apply both fixes together.

---

### `[ ]` #293 — `Bad state: Project sync after assignment save failed: Sync skipped: another sync is already in progress`

**Two interacting bugs:**

**Bug A (transient state thrown as fatal):** `lib/features/projects/presentation/controllers/project_setup_save_service.dart:234-239`:
```dart
final refreshSync = await coordinator.syncLocalAgencyProjects(mode: SyncMode.quick);
if (refreshSync.hasErrors) {
  throw StateError(
    'Project sync after assignment save failed: '
    '${refreshSync.errorMessages.join(', ')}',
  );
}
```
`SyncCoordinator` returns `SyncResult(errors: 1, errorMessages: ['Sync skipped: another sync is already in progress'])` when `isSyncGateActive()` is true (`lib/features/sync/application/sync_coordinator.dart:236-243`). Transient — but consumer throws `StateError`.

**Bug B (catch type mismatch):** `project_setup_save_service.dart:240-247` is `} on Exception catch (e) {`. **`StateError` extends `Error`, not `Exception`**, so the catch does NOT trip; the StateError escapes unhandled, bubbles to the framework, and Sentry's runtime handler captures it. The "graceful warning snackbar" at `:243-246` never fires.

**Required fix:**
- [ ] Replace `throw StateError(...)` at `:234-239` with a domain-specific `Exception` (or skip the throw and call `SnackBarHelper.showWarning` directly).
- [ ] Change the catch at `:240` to `on Object catch (e)` so it covers both Errors and Exceptions defensively.
- [ ] Better: gate the post-save refresh through `_waitForActiveSyncGateToClear` (already used at `sync_coordinator.dart:291-306`).

---

### `[ ]` #292 — `Cannot clear a fixed-length list` in `BidItemProvider.importBatch`

**Confirmed root cause:**
- `lib/features/quantities/data/repositories/bid_item_repository_impl.dart:179-182` — `_sortByNaturalItemNumber` returns `items.toList(growable: false)`. Used by `getByProjectId` at `:29-33`.
- `lib/shared/providers/base_list_provider.dart:53-62` — `loadItems` assigns `_items = await listUseCase.getByProjectId(projectId)` → `_items` becomes the fixed-length list.
- `lib/features/quantities/presentation/providers/bid_item_provider.dart:130-132` — `importBatch` does `this.items..clear()..addAll(outcome.items)`. Throws on `clear()` because `_items` is fixed-length.

**Required fix:**
- [ ] Either drop `growable: false` from the `toList(...)` calls in `bid_item_repository_impl.dart:180,190` AND `lib/shared/datasources/generic_local_datasource.dart:408`, OR
- [ ] Replace `this.items..clear()..addAll(...)` in `bid_item_provider.dart:131` with `_items = List.of(outcome.items)` followed by `notifyListeners()`. Targeted callsite fix is safest.

---

### `[ ]` #289 — `Bad state: Failed to update pay application.` — **LINKED TO B1 + #288**

**Stack:** `persist_pay_app_export_use_case.dart:100` ← `export_pay_app_use_case.dart:71` ← `pay_application_provider.dart:112`.

This is the production-side firing of **B1's** replace branch (line `:100` is `throw StateError(... 'Failed to update pay application.');` after `_payApplicationRepository.update` fails).

**Additional defect:** `lib/features/pay_applications/data/repositories/pay_application_repository_impl.dart:147-170` — `update` swallows the underlying `DatabaseException` (line 166-169) and returns `RepositoryResult.failure('Failed to update pay application.')`. The original FK violation cause is lost before the StateError fires, making field debugging impossible.

**Required fix:**
- [ ] Close B1 (rollback in replace branch).
- [ ] Close #288 (FK reference resolution).
- [ ] Propagate the original `DatabaseException` cause through `pay_application_repository_impl.dart:147-170` instead of swallowing it — or at minimum, `Logger.error` the original error before discarding.

---

### `[ ]` #288 — `FOREIGN KEY constraint failed` on `UPDATE pay_applications` — **DEEPER THAN B1**

SQLite Code 787 on `UPDATE pay_applications SET id = ?, export_artifact_id = ?, project_id = ?, ...`. Args show `export_artifact_id = a4d46a19-de82-41f4-8e1e-cb8b05c350c7`.

**FK definition:** `lib/core/database/schema/export_artifact_tables.dart:27-49` — `pay_applications.export_artifact_id REFERENCES export_artifacts(id) ON DELETE SET NULL`.

**Root cause (deeper than B1's rollback gap):** `export_artifacts` is **device-local only** (per the table comment at `export_artifact_tables.dart:1-3`); `pay_applications` **syncs across devices**. After a re-install or device handoff, the synced pay_app has an `export_artifact_id` whose FK target does NOT exist locally. Any subsequent UPDATE that re-emits the same `export_artifact_id` value blows up with FK 787.

**Other failure paths confirmed in evidence:**
1. `lib/features/pay_applications/domain/usecases/collect_pay_app_export_data_use_case.dart:217-222` — `_buildPayApplication` always sets `exportArtifactId` even when no artifact has been persisted yet. A bare `Uuid().v4()` can become a dangling FK if the artifact create rolls back.
2. `lib/features/pay_applications/data/repositories/export_artifact_repository_impl.dart:77-84` — `save` does `getById` (which filters soft-deleted rows via `lib/shared/datasources/generic_local_datasource.dart:113-123`) then INSERTs if null. With a soft-deleted artifact sharing the same id, INSERT fails with UNIQUE/PK violation; the catch in `persist_pay_app_export_use_case.dart:120-129` rethrows; UPDATE never happens.

**Required fix (pick one or combine):**
- [ ] **Option (a) — sync the artifact table.** Add `export_artifacts` to the sync scope so the FK target follows the pay_app cross-device. Requires server-side migration + sync adapter.
- [ ] **Option (b) — drop the FK.** Treat `export_artifact_id` as a soft pointer; orphan rows return null at read time. Lowest churn; loses referential integrity guarantee.
- [ ] **Option (c) — defensive null-out.** Before any pay-app UPDATE, lookup `export_artifacts` (including deleted) for the referenced id; if missing, set `export_artifact_id = NULL` before the UPDATE statement. Aligns with the existing `ON DELETE SET NULL` behavior. **Safest near-term fix.**

**Cross-link:** option (b) or (c) without B1's rollback fix still leaves the rollback bug present; option (a) alone may not address it. Land B1 + option (c) together for the internal POC; defer (a) for commercial release.

---

### `[x]` #287 — `Bytes are required on Android & iOS when saving a file` — **CLOSED**

**Stack (historical):** `file_picker_io.dart:154 FilePickerIO.saveFile` ← `pdf_output_service.dart:142`.

**Current state:**
- `lib/features/pdf/services/pdf_output_service.dart:116-127` — Android path is short-circuited to `_savePdfAndroid`, which uses platform `MethodChannel('field_guide/documents')` `saveDocument` with `bytes` (`:253-259`), bypassing `FilePicker.platform.saveFile` entirely.
- `lib/features/pay_applications/data/services/export_artifact_file_service.dart:65-88` — passes `bytes: Platform.isAndroid || Platform.isIOS ? bytes : null` (`:75`).
- The historical Sentry stack pointed at `pdf_output_service.dart:142`; current `FilePicker.saveFile` call moved to `:145`, only on non-Android/iOS where `bytes:` is not required.

**Action:** close GH issue #287 — Android/iOS path no longer reaches `FilePicker.saveFile` without bytes.

---

## Section 6 — GitHub Issues: Flutter Framework (270-286)

### `[?]` #286 — `AssertionError 'owner!._nodes.containsKey(id)'` semantics owner mismatch

Sentry shows only framework frames. No app frame. Custom `Semantics` usage in scope: `lib/core/router/scaffold_with_nav_bar.dart:263` (`_CompactBottomNavItem`), `lib/features/projects/presentation/widgets/project_tab_bar.dart:84` (badge inside `Tab`).

Likely a reparenting of one of these custom `Semantics` nodes during a router refresh. The audited fix at `scaffold_with_nav_bar.dart:88` (Material 3 NavigationBar AnimatedPhysicalModel cleanup) targets the same symptom class.

**Required fix:**
- [ ] Capture a non-truncated stack via `flutter run --enable-software-rendering` plus breadcrumbs around router transitions before changing code.

---

### `[ ]` #285 — `ExportBlockedException: IDR PDF not yet generated for entry codex-live-idr-entry`

**Throw:** `lib/features/entries/domain/usecases/export_entry_use_case.dart:108-116`.
**UI handler:** `lib/features/entries/presentation/providers/entry_export_provider.dart:49` catches and rewrites to a generic "Export failed."
**Snackbar:** `lib/features/entries/presentation/screens/entry_editor_actions.dart:29`.

**Issue:** this is a **legitimate validation error** (must generate IDR PDF before bundle export). User-facing flow is correct. But Sentry auto-issues every `Logger.error` log, so the validation error pollutes the alert stream. Mirror the clean pattern at `lib/features/forms/presentation/providers/form_export_provider.dart:47`.

**Required fix:**
- [ ] Add `on ExportBlockedException` catch in `EntryExportProvider.exportAllFormsForEntry` BEFORE the generic `on Exception` — log at `Logger.ui` / info level, not `Logger.error`.
- [ ] Or add `beforeSendSentry` suppression for `ExportBlockedException` (and any other `Exception` subclass tagged as user-recoverable).

---

### `[ ]` #284 — `setState() or markNeedsBuild() called when widget tree was locked` from `SupportProvider.reset` in `dispose`

**Source:** `lib/features/settings/presentation/screens/help_support_screen.dart:78` synchronously calls `_supportProvider.reset()` inside `dispose()`. `lib/features/settings/presentation/providers/support_provider.dart:79-88` `reset()` synchronously calls `notifyListeners()` at line 87. The "FIX-8" comment fixed an older `context.read` crash but did not defer the `notifyListeners()`.

**Required fix:**
- [ ] In `support_provider.dart`, add a `resetSilently()` method that mutates state without calling `notifyListeners`. Use it from `help_support_screen.dispose`.
- [ ] Or schedule `WidgetsBinding.instance.addPostFrameCallback((_) => _supportProvider.reset())` BEFORE calling `super.dispose()`.

---

### `[?]` #282 — `AssertionError '!_debugLocked'` in `NavigatorState.dispose`

Stack truncated to framework. Likely two transitions racing during sign-out or feedback launcher. Suspect chain:
- `lib/core/config/sentry_feedback_launcher.dart:20` — no `mounted` guard before `Navigator.of(context).push`.
- `lib/features/settings/presentation/screens/help_support_screen.dart:203` — calls launcher without `mounted` recheck.
- `lib/features/settings/presentation/widgets/sign_out_dialog.dart:81-89` — pops dialog, awaits `kThemeAnimationDuration`, then calls `auth.signOut()` which fires a router redirect.

**Required fix:**
- [ ] Add `if (!context.mounted) return;` before `await context.appGo` / `Navigator.pop` in the suspect chain (`sign_out_dialog.dart:75-95`, `sentry_feedback_launcher.dart:15-26`, `help_support_screen.dart:203`).

---

### `[x]` #281 — `StateError: StreamSink is bound to a stream` from `main.dart:68` — **CLOSED**

Trace pointed at `logger_file_transport.dart:247 _writeToSink`. Current `lib/core/logging/logger_file_transport.dart:268-279` `_writeToSink` is wrapped in try/catch via `_handleCategorySinkFailure` (uses `Zone.root.print` to avoid recursion). App-log writes use a serial queue at `:334-351` (`_writeQueue.then(...)`), preventing concurrent `add()` while a previous flush is pending.

**Action:** close GH issue #281 — concurrent-sink failure mode is gone.

---

### `[x]` #280 — `go_router/src/delegate.dart:175 currentConfiguration.isNotEmpty` (popped last page) — **CLOSED (obsolete)**

`pubspec.yaml` has zero `go_router` entry. `lib/` has zero `go_router` imports. Trace originator at `mdot_1126_form_screen.dart:275` is now the closing brace; navigation routes through `:241 context.appGo(AppRouteId.forms)` (AutoRoute).

**Action:** close GH issue #280 — go_router is gone.

---

### `[x]` #279 — `StateError: StreamSink is bound to a stream` from `logger_runtime_hooks.dart:16` — **CLOSED (duplicate of #281)**

Same `logger_file_transport.dart:247` frame. Same fix path (serialized writes + `_handleCategorySinkFailure` at `:282-304`). Originated from `_installErrorHandlers` which is now a closure in `FlutterError.onError`.

**Action:** close GH issue #279 as duplicate of #281.

---

### `[x]` #278 — `Looking up a deactivated widget's ancestor is unsafe` from `shell_banners.dart:53` — **CLOSED**

`shell_banners.dart` no longer exists (Glob returns nothing). Replacement at `lib/features/sync/presentation/widgets/primary_shell_banner_stack.dart`. Toast callback at `:78-99` guards both `mounted` AND `context.mounted` BEFORE calling `AppSnackbar.showErrorWithAction`, and again before pushing to sync dashboard at `:89`. Provider wiring cleaned in `dispose` at `:34-40`.

**Action:** close GH issue #278.

---

### `[x]` #277 — `setState() or markNeedsBuild() called during build` from `DocumentProvider.loadDocuments` in `FormGalleryScreen.didChangeDependencies` — **CLOSED**

`lib/features/forms/presentation/screens/form_gallery_screen.dart:70-76` now wraps `context.read<DocumentProvider>().loadDocuments(...)` in `WidgetsBinding.instance.addPostFrameCallback` with a `mounted` re-check at line 71.

**Action:** close GH issue #277.

---

### `[~]` #276 — `Widget unmounted, no longer has context` from `ProjectListScreen.initState`

`lib/features/projects/presentation/screens/project_list_screen.dart:56-58` wraps `_refresh()` in `addPostFrameCallback`. `_refresh` at `:73-115` has `if (!mounted) return;` at `:74` and `:113`.

**Remaining gap:** between lines 89-103, multiple `await`s run with provider reads at `:75-77` captured BEFORE the first `await`. If the widget is unmounted between awaits at `:89, :97, :106`, the `projectProvider.setCurrentUserRole` at `:103` runs against captured-but-stale provider; the next `mounted` check is not until `:113`.

**Required fix:**
- [ ] Add `if (!mounted) return;` after each `await` at `:91, :102, :109` before any further provider reads.
- [ ] Snapshot provider references at the top of `_refresh` so they survive teardown without touching `context`.

---

### `[?]` #270 — `RenderFlex overflowed by 170 pixels on the bottom`

No widget frame in trace; only `LoggerSentryTransport.report`. 170px specifically suggests soft-keyboard overlay on a non-`resizeToAvoidBottomInset` host. The shell `lib/core/router/scaffold_with_nav_bar.dart:94` sets `resizeToAvoidBottomInset: true` correctly; offender is some unscoped screen-local Scaffold.

**Required fix:**
- [ ] Reproduce on phone/landscape with `debugPaintSizeEnabled` over each Stateful screen until the offender shows itself.
- [ ] Wrap the offender in `SingleChildScrollView` or set `Scaffold(resizeToAvoidBottomInset: true)`.

---

### `[ ]` #269 — `Zone mismatch` from `main.dart:54 → :52`

**Source:** `lib/main.dart:25` calls `WidgetsFlutterBinding.ensureInitialized()` at top of `main()`, OUTSIDE any zone. `:28-42` runs `SentryFlutter.init(...)` also outside any zone. `:59-79` enters `runZonedGuarded` and only there calls `runApp` at `:61`.

`lib/main_driver.dart:34-46` already does this correctly: `WidgetsFlutterBinding.ensureInitialized()` is called INSIDE `runZonedGuarded` at `:37`.

**Required fix:**
- [ ] Move `WidgetsFlutterBinding.ensureInitialized()` (and ideally `SentryFlutter.init`/`AppInitializer.initialize`) INSIDE the `runZonedGuarded` callback in `main.dart`. Mirror the pattern in `main_driver.dart:33-46`.

---

## Section 7 — GitHub Issues: Older Defects + Enhancements (42-259)

### `[ ]` #259 — Settings consent revoke control missing despite copy promising it

- Copy: `lib/features/settings/presentation/screens/consent_layout.dart:123` and `:184` say "You can revoke consent at any time in Settings".
- Provider API ready: `lib/features/settings/presentation/providers/consent_provider.dart:188` defines `revokeConsent()`.
- UI: `lib/features/settings/presentation/widgets/settings_account_section.dart` has no revoke tile/action. `revokeConsent` has zero callsites in `lib/`.

**Required fix:**
- [ ] Add a "Revoke consent" tile to `settings_account_section.dart` that calls `consentProvider.revokeConsent()` and routes user back to consent flow.

---

### `[?]` #210 — Entry PDF preview shows mismapped values

The bug-report log lines (`VRF-Midwest Excavating 4c6ho -> Namegdzf`) are misread output. `Namegdzf`, `sfdasd`, `Name_3dfga` are **literal AcroForm field names** declared in `lib/features/pdf/services/idr_pdf_template_writer.dart:35,75,105,125,145`'s `_contractorFieldMap`. The log line at `:563-565` is `'Set contractor $index name: ${contractor.name} -> ${fields.nameField}'` — i.e., `value -> field-name`, NOT `value -> placeholder`.

**Status:** likely a misread of log output rather than a real bug. To fully verify, render the IDR for a known entry on-device and compare on-PDF mapping vs expected.

**Required fix:**
- [ ] Run a manual render on-device, compare against expected mapping. If real, the issue is in template binding (template file's poor field naming), not in the writer code.
- [ ] Improve log format to disambiguate: change `'-> ${fields.nameField}'` to `'-> field=${fields.nameField}'`.

---

### `[ ]` #178 — Custom lint rules for immutable model discipline (enhancement)

Searched `fg_lint_packages/field_guide_lints/lib` for `immutable`, `class_must_be_immutable`, `defensive.copy`, `unmodifiable` — no matches. Existing rules cover different concerns (`tomap_field_completeness.dart`, `copywith_nullable_sentinel.dart`, `no_sentinel_strings_in_data.dart`).

**Required fix:**
- [ ] Implement immutable-model lint rules: defensive collection copies, complete `==`/`hashCode`, entity vs value distinction.

---

### `[ ]` #133 — Lower Sentry sessionSampleRate before production

`lib/main.dart:37` — `options.replay.sessionSampleRate = 1.0;` (still 100%). `:38` — `options.replay.onErrorSampleRate = 1.0;` (correctly retained per issue body).

**Required fix:**
- [ ] Drop `sessionSampleRate` to a production rate (e.g. `0.05` or `0.1`) before the first paid release. Internal POC may keep it high.

---

### `[~]` #129 — Remote signed URL fallback for synced documents — **PARTIALLY**

Implementation present:
- `lib/services/document_service.dart:57-85 ensureLocalDocument` downloads `remotePath` bytes via injected `downloadRemoteBytes` and caches locally.
- `lib/features/sync/application/sync_file_access_service.dart:9, 29-39` — `downloadEntryDocument(remotePath)` for `entry-documents` bucket.
- `lib/features/forms/domain/usecases/manage_documents_use_case.dart:58-60` and `lib/features/forms/presentation/providers/document_provider.dart:127-129` wire it.
- `lib/features/entries/presentation/widgets/entry_documents_subsection.dart:101` invokes the download path before showing "File not found".

**Gap:** uses authenticated direct download, NOT signed URLs. If issue strictly requires ephemeral signed URLs (e.g., for cross-role sharing), still open. Otherwise functional outcome is met.

**Required fix:**
- [ ] Decide whether direct download satisfies the issue, or whether signed URLs are required. If signed URLs: add `Supabase.instance.client.storage.from(bucket).createSignedUrl(path, durationSeconds)` integration.

---

### `[ ]` #128 — File list dialog for multi-file sharing UX (enhancement)

- `lib/features/entries/presentation/screens/entry_editor_actions.dart:29-45` — after multi-form export, only `SnackBarHelper.showSuccess(context, 'Exported ${paths.length} form(s)')`. No file-list dialog or share action.
- `lib/features/entries/presentation/providers/entry_export_provider.dart:17, 47` — `exportedPaths` exposed but no dialog UI consumes it.
- `lib/core/exports/export_save_share_dialog.dart` is a single-file dialog only (used by pay applications).
- `Share.shareXFiles` only called for pay-app exports (`export_artifact_file_service.dart:118`), not entry multi-form.

**Required fix:**
- [ ] Replace the snackbar in `entry_editor_actions.dart:29-45` with a multi-file dialog showing each exported path with a per-file "Share" button and a "Share all" using `Share.shareXFiles(paths)`.

---

### `[~]` #127 — Bundle merging for multi-form export

Implementation present (per-file artifact rows in a folder):
- `lib/features/entries/domain/usecases/export_entry_use_case.dart:122-204` creates per-entry bundle dir `exports/<projectId>/<date>_<shortId>/`, copies IDR PDF + each form PDF + photos, writes ONE `EntryExport` row pointing at the dir PLUS one `ExportArtifact` per file.
- No zip composition / no PDF merge call. `pubspec.yaml:113` includes `archive: ^4.0.2` but unused.

**Decision still open:** the issue body asked for zip vs merged-PDF vs per-file rows. The implementation chose "per-file rows in folder". If team prefers a single bundled artifact, additional work needed.

**Required fix:**
- [ ] Confirm with the founder whether the per-file-folder bundle is sufficient. If yes, mark `[x]`. If a single zip/merged-PDF is required, add an `archive`-driven zip step or a `printing`-driven PDF merge step.

---

### `[ ]` #92 — BLOCKER-36: Item 130 whitewash destroys y descender (parked)

`lib/features/pdf/services/extraction/stages/grid_line_removal_finalize_stage.dart` still contains whitewash logic. Test still references the behavior at `test/features/pdf/extraction/stages/ocr_text_recognizer/cell_crop_computation_tests.dart`.

**Status:** parked, cosmetic. Defer until/unless audit Sprint 5 LLM-OCR migration replaces the entire pipeline.

---

### `[ ]` #91 — BLOCKER-34: Item 38 superscript "th" via Tesseract (parked)

`pubspec.yaml:79` — `flusseract: ^0.1.3` still primary. 28+ Tesseract files in `lib/features/pdf/services/extraction/ocr/`. A Google Document AI engine exists alongside (`google_document_ai_ocr_engine.dart`, `ocr_engine_factory.dart`) but is opt-in, not the default.

**Status:** parked. Inherent Tesseract limitation. Audit Sprint 5 calls for full migration off Tesseract → LLM OCR (Gemini Flash 2.0) to fix this structurally.

---

### `[ ]` #89 — BLOCKER-28: SQLite encryption (sqlcipher) (critical, production blocker)

- `pubspec.yaml:50-51` — only `sqflite: ^2.4.2` and `sqflite_common_ffi: ^2.4.0+2`. No `sqflite_sqlcipher` or other cipher dependency.
- `lib/core/database/database_service.dart:69-96` — `openDatabase` called with no `password` param, no PRAGMA `key`, no encryption configuration.
- `Grep` for `cipher|encryption|sqlcipher` in `lib/`: no matches.

**Status:** unaddressed. Hard production-readiness blocker per issue body. Internal POC can ship without it; commercial release cannot.

**Required fix:**
- [ ] Adopt `sqflite_sqlcipher` (or equivalent), provision per-device encryption keys via `flutter_secure_storage`, gate via `PRAGMA key='...'`, add a one-time migration that re-encrypts the existing DB with the chosen cipher. Plan for the iOS keychain access group + Android KeyStore-backed key.

---

### `[~]` #42 — pdfrx silent fail in background isolates

- `lib/features/pdf/presentation/helpers/pdf_import_workflow.dart:30-34` — explicit comment confirming the workflow now runs extraction on the main isolate.
- `lib/features/pdf/presentation/helpers/mp_import_helper.dart:28-30` — same.
- `lib/features/pdf/services/extraction/stages/page_renderer_v2.dart:152-153` — pdfrx initialization and document open are on the main isolate (per the workflow above).
- OCR worker isolates receive pre-rendered byte arrays via `OcrPageRecognitionWorkerRequest` carrying `enhancedImageBytes`; they never call pdfrx.
- `page_renderer_v2.dart:213-222, 384, 400, 428` now log explicit pdfrx errors instead of silently returning null.

**Status:** silent-isolate failure mode is no longer reachable through production paths. The split-architecture remediation suggested in the issue body is implemented. Marked `[~]` because the fix is by-construction (pipeline only invokes the renderer from the main isolate) rather than a hard-coded assertion.

**Required fix (optional hardening):**
- [ ] Add a runtime assertion in `page_renderer_v2.dart` that throws if invoked off the root isolate, so a future caller cannot accidentally re-enter the broken pattern.

---

## Section 8 — Items Recommended For Closure (No Code Work)

These items have evidence in the live tree that the underlying defect is fixed. Closing them removes noise from the tracker.

| ID | Reason |
|---|---|
| GH #311 | `consent_record_adapter` skips pull and integrity check; 42703 is unreachable |
| GH #308 | Log Drain server-side scrubbing implemented + tested |
| GH #295 | `form_routes.dart` does not exist; AutoRoute migration complete |
| GH #287 | Android/iOS path bypasses `FilePicker.saveFile`; uses platform-channel `MethodChannel('field_guide/documents')` with bytes |
| GH #281 | logger file transport now wraps writes; serialized queue prevents the bind |
| GH #280 | go_router fully removed from pubspec + lib/ |
| GH #279 | duplicate of #281 |
| GH #278 | `shell_banners.dart` replaced with mounted-guarded `primary_shell_banner_stack.dart` |
| GH #277 | `FormGalleryScreen.didChangeDependencies` now uses `addPostFrameCallback` |
| Audit H4 | `SyncEngine.pushAndPull` now 58 lines, file 315 lines — under audit's 250-line target |

---

## Section 9 — Quick-Win Cluster (≤ 30 min each)

Bundle these into one cleanup commit before Sprint 1:

- [ ] H1 — swap go_router recommendation in `.claude/CLAUDE.md` and `.claude/rules/frontend/flutter-ui.md`
- [ ] H3 — add `export 'sync_run_metrics.dart';` to `lib/features/sync/domain/domain.dart`
- [ ] H10 — fix regex typo at `pay_app_import_parser.dart:185` (`r'[^0-9.\\-]'` → `r'[^0-9.\-]'`)
- [ ] H14 — replace raw `FilledButton` at `inline_contractor_chooser.dart:94` with `AppButton.primary`
- [ ] H19 — pass `stack: stackTrace` in `auth_sync_listener_bootstrap.dart:161-167, 307-317`
- [ ] B7 partial — add WHY comment to `pubspec.yaml:220-221` printing override
- [ ] H7 — update `weather_helpers.dart:2` import, then delete `lib/core/theme/{theme,field_guide_colors,design_constants,colors}.dart`
- [ ] H9 — delete `lib/shared/widgets/permission_dialog.dart`, `widgets.dart`, drop barrel export
- [ ] #292 — drop `growable: false` from `bid_item_repository_impl.dart:180,190` and `generic_local_datasource.dart:408` (or wrap with `List.of` at the consumer)
- [ ] #293 second-bug — change `} on Exception catch` at `project_setup_save_service.dart:240` to `on Object catch`
- [ ] #294 — change `Logger.error` → `Logger.sync` at `push_error_handler.dart:90-93` for retryable network errors
- [ ] #300 — `beforeSendSentry` filter for `AuthRetryableFetchException` with null status + "Bad file descriptor"
- [ ] #301 — explicit `on TimeoutException` in `app_config_provider.dart` to skip Sentry escalation
- [ ] #302 — special-case `RepositoryActionError` in `safe_action_mixin.dart:50-62` to avoid Sentry escalation

---

## Section 10 — Cross-Cutting Risk: Sentry Alert Noise

Multiple issues (#285 ExportBlockedException, #302 contractor-name-conflict, #270 RenderFlex, #294 networkerror, #300 AuthRetryableFetchException, #295 obsolete-go_router) are **legitimate-error alerts that should not be Sentry events**. They reflect:
- Validation outcomes (#285, #302)
- Transient network conditions (#294, #300)
- Stale builds (#295)
- Render-warnings, not crashes (#270)

The `LoggerSentryTransport.report` pipeline auto-issues every `Logger.error`. This produces signal-to-noise problems that mask real defects.

**Recommended:**
- [ ] Audit `lib/core/config/sentry_pii_filter.dart` and add a `beforeSendSentry` allowlist that filters validation-class exceptions (`ExportBlockedException`, validation-pattern messages, `AuthRetryableFetchException`, `RenderFlex` overflow warnings).
- [ ] At each `Logger.error` callsite that wraps a known-recoverable error, downgrade to `Logger.ui` / `Logger.info`.

---

## Section 11 — Roadmap Alignment

Audit Sprint 1 closes B1, B2, B3, B4 plus a clean live-gate run.
Audit Sprint 2 closes B5, B6, B7.
Audit Sprint 3 burns down the Hygiene findings (H1-H19 above).

This tracker maps 1-to-1 onto those sprints. A single commit per sub-bullet is realistic. Most Hygiene items are 30-min changes; the Sprint-1 blockers are each 1-2 hours of careful work plus tests.

---

## Section 12 — Open Questions For The Founder

- B7 — does the `printing_patched/` tree still need a fork at all, or has upstream landed the patch in a recent release?
- #127 — is "per-file artifacts in a bundle folder" sufficient, or do you want a single zip / merged-PDF artifact?
- #129 — does the existing direct-download path satisfy "remote signed URL", or is signed-URL ephemeral access required for sharing?
- #210 — can you run a manual IDR render and compare on-PDF mapping to confirm whether the bug-report logs were misread or whether mapping is genuinely wrong?
- #89 — internal POC ship without sqlcipher, or land it as a Sprint-4 hardening item before any external pilot?
- #92, #91 — keep the parked Tesseract limitations parked, or fold into the Sprint-5 LLM-OCR migration as forcing functions?

---

## Appendix A — Files Touched (Quick Reference)

**Pay applications (B1, #288, #289):**
- `lib/features/pay_applications/domain/usecases/persist_pay_app_export_use_case.dart`
- `lib/features/pay_applications/data/services/export_artifact_file_service.dart`

**Sync (B2, H2, H6):**
- `lib/features/sync/application/sync_state_repair_runner.dart`
- `lib/features/sync/application/sync_recovery_service.dart`
- `lib/features/sync/application/sync_query_service.dart`
- `lib/features/sync/presentation/widgets/sync_dashboard_actions_section.dart`
- `lib/features/sync/presentation/providers/sync_provider*.dart`
- `lib/features/sync/domain/domain.dart` (H3)
- `lib/features/sync/engine/sync_error_classifier.dart` (#306)
- `lib/features/sync/engine/push_error_handler.dart` (#306)

**PDF (B3, H10, H13, #287, #292):**
- `lib/features/pdf/services/extraction/stages/value_normalizer.dart`
- `lib/features/pay_applications/data/services/pay_app_import_parser.dart`
- `lib/features/pdf/services/extraction/stages/ocr_page_recognition_worker_payload.dart`
- `lib/features/pdf/services/pdf_output_service.dart`
- `lib/features/quantities/presentation/providers/bid_item_provider.dart`

**Database (B4, #89):**
- `lib/core/database/database_service.dart`
- `test/core/database/migration_v*_test.dart`
- `test/_helpers/migration_fixture.dart` (new)
- `pubspec.yaml` (sqflite_sqlcipher)

**Domain purity (B5):**
- `lib/features/pay_applications/domain/usecases/persist_pay_app_export_use_case.dart`
- `lib/features/entries/domain/usecases/export_entry_use_case.dart`

**Driver (B6):**
- `lib/core/driver/driver_interaction_handler_*.dart` (4 files)
- `lib/core/driver/driver_shell_handler.dart`
- `lib/core/driver/driver_widget_inspector.dart`

**Third-party (B7):**
- `third_party/{custom_lint,dartcv4,printing}_patched/PATCHES.md` (new)
- `pubspec.yaml`

**Auth (H15, H16, H19, #284):**
- `lib/features/auth/presentation/providers/auth_provider.dart`
- `lib/features/auth/presentation/providers/auth_provider_security_actions.dart`
- `lib/features/auth/domain/usecases/sign_out_use_case.dart`
- `lib/core/bootstrap/auth_sync_listener_bootstrap.dart`
- `lib/features/settings/presentation/providers/support_provider.dart`

**Routing / lifecycle (#269, #276, #284, H1):**
- `lib/main.dart`
- `lib/features/projects/presentation/screens/project_list_screen.dart`
- `lib/features/settings/presentation/screens/help_support_screen.dart`
- `.claude/CLAUDE.md`
- `.claude/rules/frontend/flutter-ui.md`

**Settings / consent (#259):**
- `lib/features/settings/presentation/widgets/settings_account_section.dart`
- `lib/features/settings/presentation/providers/consent_provider.dart`

**Workflows (#307, #305, B7):**
- `.github/workflows/quality-gate.yml`
- `supabase/seed.sql`
- `supabase/functions/_shared/log_drain_sink.ts` (#308 — already complete)

---

## Appendix B — Verification Method Notes

This tracker was produced by 8 parallel debug-research agents working off the audit text and live tree state. Every `[ ]` / `[~]` / `[x]` in the body is grounded in a Read or Grep of the current `main` branch, performed 2026-04-25 12:00–12:25 UTC. Where line numbers in the audit had drifted, the corrected line numbers are noted inline.

Items that could not be statically verified (no app frame in Sentry stack, requires runtime repro, requires on-device render) are marked `[?]` and listed with the specific instrumentation step needed to confirm.

The audit's Sprint-6 exit criterion ("audit on a clean candidate commit") still has not been met for this tracker either — the working tree is dirty at the time of writing. After Sprint 1 lands, a full `flutter analyze` + `dart run custom_lint` + `flutter test` pass on a clean commit is the next gate.

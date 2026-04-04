# Async Lint Audit — Fix Plan

**Created**: 2026-04-04 (Session 730)
**Branch**: Create new branch `fix/async-lint-cleanup` from `main`
**Scope**: 288 analyzer violations across 4 async-related lint rules
**Worktree**: This work runs in a parallel worktree, independent of `codex/reimplement-entry-ui-continuity`

---

## Rules in Scope

| Rule | Count | Risk |
|------|-------|------|
| `discarded_futures` | 150 | Silent failures — errors swallowed in non-async contexts |
| `unnecessary_await_in_return` | 64 | Unnecessary microtask tick, but 29 MUST keep await |
| `avoid_slow_async_io` | 48 | Async IO where sync alternatives exist |
| `unawaited_futures` | 26 | Futures not awaited in async contexts |

---

## Phase 1: SILENT_FAILURE_BUG (11 violations) — HIGHEST PRIORITY

These are real bugs where failed futures are silently lost. **The sync_lifecycle_manager alone has 7 violations — likely the root cause of sync debugging hell.**

### 1A. `lib/features/sync/application/sync_lifecycle_manager.dart` (7 bugs)

| Line | Code | Problem | Fix |
|------|------|---------|-----|
| 131 | `_handleResumed()` in `didChangeAppLifecycleState` | Framework `void` override discards async future. Entry point for ALL lifecycle sync. | Wrap: `unawaited(_handleResumed())` + verify top-level try/catch inside `_handleResumed()` |
| 145 | `_triggerSync()` inside `Timer` callback | Timer discards future. App-paused sync — most important path for data safety. | `Timer(_debounceDelay, () { unawaited(_triggerSync()); })` + verify internal error handling |
| 157 | `_triggerSync()` in `_handleDetached` | App about to die. Silent sync failure = data loss. | `unawaited(_triggerSync())` — cannot await in this context |
| 184 | `_triggerDnsAwareSync(forced: true)` in `_handleResumed` | Not awaited. Forced recovery sync errors dropped. `onForcedSyncInProgress` may not reset → stuck UI. | `await _triggerDnsAwareSync(forced: true)` |
| 194 | `_triggerDnsAwareSync(forced: false)` in `_handleResumed` | Quick sync on resume not awaited. Stale-data warning never cleared. | `await _triggerDnsAwareSync(forced: false)` |
| 203 | `_triggerDnsAwareSync(forced: true)` in `_handleResumed` | Stale-data forced sync path. `onStaleDataWarning` never cleared if fails. | `await _triggerDnsAwareSync(forced: true)` |
| 207 | `_triggerDnsAwareSync(forced: false)` in `_handleResumed` | Normal resume quick-sync. Errors silently dropped. | `await _triggerDnsAwareSync(forced: false)` |

**Strategy**: Lines 184/194/203/207 are inside `_handleResumed()` which is already `async` — just add `await`. Lines 131/145/157 are in non-async framework callbacks — use `unawaited()` wrapper and ensure the called methods have robust internal try/catch.

### 1B. `lib/features/sync/presentation/providers/sync_provider.dart` (2 bugs)

| Line | Code | Problem | Fix |
|------|------|---------|-----|
| 106 | `_refreshPendingCount()` in constructor | DB query future discarded. Pending count stuck at 0 → user thinks synced. | `unawaited(_refreshPendingCount())` + add try/catch inside method |
| 170 | `_refreshPendingCount()` in `onSyncComplete` | Post-sync refresh discarded. Stale pending counts + false "synced" signal. | `unawaited(_refreshPendingCount())` + add try/catch inside method |

### 1C. `lib/features/auth/presentation/providers/auth_provider.dart` (2 bugs)

| Line | Code | Problem | Fix |
|------|------|---------|-----|
| 105 | `loadUserProfile()` in constructor | Profile load fails → `_isLoadingProfile` stays true forever → infinite loading screen. | `unawaited(loadUserProfile())` + verify finally block always sets `_isLoadingProfile = false` |
| 140 | `loadUserProfile()` in auth state listener | Profile load fails → `_userProfile` stays null → router redirects to /profile-setup wrongly. | `unawaited(loadUserProfile())` + verify internal error handling |

---

## Phase 2: NEEDS_AWAIT (18 violations) — MEDIUM PRIORITY

Fragile code that works by accident. Each needs judgment on whether to `await` or `unawaited()`.

| # | File:Line | Code | Fix |
|---|-----------|------|-----|
| 1 | `project_provider.dart:594` | `_settingsProvider?.clearIfMatches(id)` — deleted project ID persists | `await` if async, else `unawaited()` |
| 2 | `project_provider.dart:788` | `loadAndRestore(initialCompanyId)` — first project load fire-and-forget | `unawaited()` |
| 3 | `project_provider.dart:802` | `loadAndRestore(newCompanyId)` — company-change reload discarded | `unawaited()` |
| 4 | `app_initializer.dart:193` | `appConfigProvider.clearOnSignOut()` — stale config persists | `unawaited()` |
| 5 | `app_bootstrap.dart:98` | `consentProvider.clearOnSignOut()` — **privacy/GDPR issue** | Make listener async + await |
| 6 | `app_bootstrap.dart:103` | `consentProvider.writeDeferredAuditRecordsIfNeeded()` — audit trail gaps | `unawaited()` with error handling |
| 7 | `auth_provider.dart:115` | `_preferencesService?.setPasswordRecoveryActive()` — recovery flag not persisted | `unawaited()` |
| 8 | `auth_provider.dart:130` | `_preferencesService?.clearPasswordRecoveryActive()` — stuck on /update-password | `unawaited()` |
| 9 | `auth_provider.dart:852` | `_authSubscription?.cancel()` — listener fires on disposed provider | `unawaited()` |
| 10 | `sync_engine.dart:433-435` | Debug HTTP POST — has `.catchError()`, just needs wrapper | `unawaited()` |
| 11 | `fcm_handler.dart:138` | `_saveFcmToken(...)` — push notifications break silently | `unawaited(...catchError(...))` |
| 12 | `app_redirect.dart:124` | `_authProvider.handleForceReauth(...)` — signOut failure leaves stale creds | `unawaited()` |
| 13 | `scaffold_with_nav_bar.dart:53` | `.closed.then(...)` — snackbar flag never cleared | `unawaited()` |
| 14 | `app_config_provider.dart:147` | `_secureStorage.write(...)` — stale sync timestamp | `unawaited()` |
| 15-17 | `trash_screen.dart:279,324,377` | `_loadDeletedItems()` after operations — stale UI | `await _loadDeletedItems()` |
| 18 | `project_provider.dart:775` | Already has `unawaited()` but missing `.catchError()` | Add `.catchError(...)` |

---

## Phase 3: MECHANICAL FIXES — LOW RISK, HIGH VOLUME

### 3A. `unnecessary_await_in_return` — Remove `await` (40 fixes)

**Simple**: Remove `await` keyword from `return await ...` statements. No behavioral change.

Files (count per file):
- `form_export_repository.dart` (6)
- `document_repository.dart` (6)
- `entry_export_repository.dart` (5)
- `extraction_metrics_local_datasource.dart` (4)
- `pdf_service.dart` (6)
- `sync_provider.dart` (3)
- `auth_service.dart` (3)
- `permission_service.dart` (1)
- `image_service.dart` (3)
- `photo_service.dart` (2)
- `form_pdf_service.dart` (1)
- `sync_orchestrator.dart` (1)
- `mock_database.dart` (1) [test]
- `sync_schema_test.dart` (2) [test]
- `tesseract_initializer.dart` (1)

### 3B. `unnecessary_await_in_return` — DO NOT TOUCH (29 cases)

**These are inside try/catch or try/finally blocks. Removing `await` would break error handling.**

Critical sync integrity cases:
- `sync_control_service.dart:28,43` — try/finally resets `pulling` flag
- `sync_engine.dart:450,462` — try/finally releases SyncMutex

Other try/catch cases (keep await for fallback values):
- `form_export_repository.dart:18`
- `document_repository.dart:19`
- `entry_export_repository.dart:16`
- `deletion_notification_local_datasource.dart:19`
- `entry_quantity_provider.dart:296,342`
- `todo_provider.dart:218,280`
- `photo_repository_impl.dart:191`
- `daily_entry_provider.dart:452,466`
- `form_pdf_service.dart:1158`
- `photo_remote_datasource.dart:140`
- `inspector_form_repository.dart:173,193,223,237`
- `form_response_repository.dart:323,353,367`
- `sync_engine.dart:789` (actually mechanical — verify before fixing)

### 3C. `avoid_slow_async_io` — Switch to sync (30 fixes)

Switch `file.exists()` → `file.existsSync()`, `file.stat()` → `file.statSync()`, etc.

**Safe to switch** (background/init/isolate context):
- `logger.dart:316,357,408,417,441,474,481,1046` (8 — all startup/init)
- `image_service.dart:33,103,142,184,200` (5 — init, cache clear, isolates)
- `tesseract_initializer.dart:55,68,70,96,104,118` (6 — all init)
- `sync_engine.dart:1256` (1 — background sync push)
- `document_service.dart:56` (1 — file just written)
- `export_entry_use_case.dart:60` (1 — file just written)
- `export_form_use_case.dart:48` (1 — file just written)
- `driver_server.dart:869,964` (2 — test/debug only)
- `clear_cache_dialog.dart:51,64` (2 — user-triggered cleanup)
- `support_provider.dart:163,179` (2 — log upload)
- `photo_remote_datasource.dart:137` (1 — isolate)
- Test files: `logger_rotation_test.dart:56,57,71,72`, `image_service_test.dart:18,32`, `export_form_use_case_test.dart:138` (7)

**Note**: When switching, if the enclosing method was only `async` for these IO calls, it may become eligible to drop `async` entirely. Check return types.

### 3D. `avoid_slow_async_io` — KEEP ASYNC (18 cases)

These run on the UI thread. Switching to sync would cause jank.

- `photo_service.dart:54,93,153,326,337,368,374,375` (8 — camera/gallery flows)
- `image_service.dart:56` (1 — gallery scroll hot path)
- `document_service.dart:67` (1 — file picker flow)
- `entry_forms_section.dart:325` (1 — tap handler)
- `project_list_screen.dart:221` (1 — project delete)
- `form_pdf_service.dart:275` (1 — PDF template loading)
- `photo_repository_impl.dart:103,128` (2 — photo delete)
- `pdf_import_service.dart:263` (1 — PDF import)
- `pdf_service.dart:534` (1 — folder export)
- `photo_pdf_service.dart:51` (1 — photo PDF generation)

### 3E. UI_CALLBACK — Wrap with `unawaited()` (76 fixes)

All in button handlers, `onTap`, `initState`, `addPostFrameCallback` where the framework signature is `void`. Mechanical: wrap the future-returning call with `unawaited()`.

**Import needed**: Add `import 'dart:async';` to each file (for `unawaited`).

Top files by count:
- `todos_screen.dart` (12)
- `home_screen.dart` (10)
- `settings_screen.dart` (5)
- `auth_provider.dart` (5 — some overlap with Phase 1/2)
- `project_list_screen.dart` (4)
- `project_setup_screen.dart` (4)
- `project_dashboard_screen.dart` (4)
- `entries_list_screen.dart` (4)
- `calculator_screen.dart` (4)
- `form_gallery_screen.dart` (4)
- `toolbox_home_screen.dart` (4)
- `entry_editor_screen.dart` (3)
- `gallery_screen.dart` (3)
- `extraction_banner.dart` (3)
- `deletion_notification_banner.dart` (3)
- Remaining widgets (2-1 each): `app_section_card`, `contractor_editor_widget`, `entry_activities_section`, `entry_form_card`, `entry_forms_section`, `entry_quantities_section`, `photo_name_dialog`, `permission_dialog`, `project_switcher`, `sign_out_dialog`

### 3F. FIRE_AND_FORGET_OK — Wrap with `unawaited()` (21 fixes)

Intentionally fire-and-forget. Just needs explicit `unawaited()` wrapper for lint compliance.

- `analytics.dart:37` — has `.catchError()`
- `logger.dart:213,237,241,243,248,724` (6)
- `project_provider.dart:465,474` (2)
- `sync_provider.dart:184` — has `.catchError()`
- `sync_engine.dart:433,435` — debug HTTP, has `.catchError()`
- Various screens: `forms_list_screen`, `form_viewer_screen`, `quantities_screen`, `quantity_calculator_screen`, `help_support_screen`, `admin_dashboard_screen`, `personnel_types_screen`, `legal_document_screen`, `theme_section`, `extraction_job_runner`, `drafts_list_screen`, `pdf_import_helper`, `mp_import_helper`
- Test files: `auth_provider_test`, `extraction_job_runner_test`, `pay_item_source_dialog_test`, `project_delete_sheet_test`, `sync_engine_circuit_breaker_test`

---

## Execution Order

| Phase | Description | Violations | Risk | Approach |
|-------|-------------|------------|------|----------|
| 1 | SILENT_FAILURE_BUG | 11 | HIGH | Manual, careful. Read each file, understand error propagation. |
| 2 | NEEDS_AWAIT | 18 | MEDIUM | Manual judgment per case. |
| 3A | Remove `return await` | 40 | LOW | Mechanical. Skip the 29 KEEP_AWAIT cases. |
| 3B | Verify DO NOT TOUCH list | 29 | NONE | No changes — just validate they're in try/catch. |
| 3C | Switch to sync IO | 30 | LOW | Mechanical. Check return type changes needed. |
| 3E | `unawaited()` wrappers (UI) | 76 | LOW | Mechanical. Add `import 'dart:async'` + wrap calls. |
| 3F | `unawaited()` wrappers (fire-and-forget) | 21 | LOW | Mechanical. Same pattern as 3E. |

**Total**: ~196 fixes (92 skipped: 29 KEEP_AWAIT + 18 KEEP_ASYNC + ~45 overlap/test)

---

## Validation

After all fixes:
1. `pwsh -Command "flutter analyze"` — target 0 for these 4 rules
2. CI run — no test regressions
3. Manual sync test — verify lifecycle manager error propagation works (app pause/resume/detach cycle)

---

## Context for Next Session

- The audit was done in Session 730 (2026-04-04) using two parallel Explore agents
- Full audit reports are in conversation context only (not persisted as files)
- This plan captures ALL findings from both agents
- The `codex/reimplement-entry-ui-continuity` branch has the smarter sync strategy code — this async fix work should branch from `main` to avoid conflicts
- **Key insight**: sync_lifecycle_manager.dart has 7 silent failure bugs that likely explain why the sync system has been impossible to debug — every sync trigger path silently swallows errors

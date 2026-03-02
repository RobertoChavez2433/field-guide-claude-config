# Testing Strategy Overhaul — BLOCKER-11

**Date**: 2026-02-22 | **Sessions**: 454-457
**Status**: OPEN — Blocks efficient completion of remaining 29/38 E2E tests

## Problem Statement

After 5+ sessions and ~6 hours, only 9/38 tests are complete. The dart-mcp + flutter_driver approach is fundamentally mismatched to the task. ~90% of time is spent on build failures, process management, and Supabase credential workarounds — not actually verifying app behavior.

## Root Cause: Wrong Testing Tier

| Time Sink | Est. Time | Root Cause |
|-----------|-----------|------------|
| CMake 4.x build failures | 45 min | Firebase SDK incompatibility |
| Wrong Supabase anon key | 30 min | --dart-define impossible via dart-mcp |
| Missing INSERT RLS policy | 45 min | Real bug, but found via slow path |
| Backfill migration | 30 min | Real bug, correct to find via E2E |
| native_assets dir failures | 20 min | Recurring cmake issue after stop |
| Process stop/restart cycles | 60 min | ~12 cycles at 5 min each |
| Routing bugs (3) | 45 min | GoRouter logic testable in widget tests |
| Session compaction/rebuilds | 30 min | 5 sessions = 5 context rebuilds |
| Missing ValueKey additions | 20 min | flutter_driver needs keys, widget tests use finders |
| **Total overhead** | **~5.5 hours** | |
| **Actual test execution** | **~30 min** | 9 tests done |

## 10 Specific Issues Identified

### CRITICAL
1. **`launch_app` doesn't support `--dart-define`** — All `TestModeConfig` flags (`MOCK_AUTH`, `MOCK_DATA`, `PATROL_TEST`) are permanently false via dart-mcp. Credentials had to be hardcoded.
2. **`SyncOrchestrator` → `Supabase.instance` crash** — `driver_main.dart` uses production constructor. Fixed for harness (`forTesting()`), but full-app path still crashes without `--dart-define=MOCK_DATA=true`.
3. **Stop/rebuild/relaunch cycle is 30-60s** — native_assets/windows dir disappears after stop, cmake install fails. Each flow switch requires full rebuild.

### HIGH
4. **Flutter Driver can't interact with dialogs** — AlertDialog, BottomSheet, showDialog all hang. Requires `FLUTTER_DRIVER` compile-time guard on every dialog.
5. **Hot restart underutilized** — Could avoid full rebuild for Dart-only changes but was never used in sessions 454-456.

### MEDIUM
6. **`harness_config.json` uses relative path** — Silent fallback to wrong screen if working dir is different.
7. **`seedScreenData` missing for new multi-tenant screens** — dashboard-nav, project-management, entry-flow all have `seedScreens: []`.
8. **AuthProvider in harness always returns null profile** — Can't test admin-gated or role-based UI.

### LOW
9. **`FormsListScreen` in seedScreens but no seed case** — Works by accident due to ordering, fragile.
10. **`get_widget_tree` 250K+ char overflow** — Known limitation, screenshot workaround documented.

## Recommended Strategy: Widget Tests

**Key insight**: ~33 of 38 tests are UI navigation, form validation, role-based routing, and CRUD display verification — all testable with `flutter test` at 1-3 seconds each, zero build cycle.

### Test Tier Reclassification

| Tier | Tool | Speed | Tests |
|------|------|-------|-------|
| **Widget tests** | `flutter test` | 1-3s each | 33 tests (auth routing, projects, admin, settings, nav guards, entries, toolbox) |
| **Provider unit tests** | `flutter test` | <1s each | Validation logic, user attribution |
| **Integration tests** | dart-mcp or manual | 2-5min each | T-AUTH-05 (Supabase RLS), T-SYNC-01-06 (real sync) |

### Implementation Plan

#### Phase 1: Create widget test infrastructure (1-2 hours)

1. **`test/helpers/widget_test_harness.dart`** — Reuse `buildHarnessProviders` from `lib/test_harness/harness_providers.dart` but add:
   - `StubAuthProvider` with configurable `isAuthenticated`, `userProfile`, `canWrite`
   - `buildTestApp(Widget child, {UserProfile? profile, bool isAdmin?})` wrapper
   - `seedBaseData(dbService)` reuse

2. **`test/helpers/stub_auth_provider.dart`** — Pre-configured profiles:
   - `unauthenticated` (no user)
   - `pendingApproval` (status=pending)
   - `approvedAdmin` (status=approved, role=admin)
   - `approvedViewer` (status=approved, role=viewer)
   - `rejected` / `deactivated`

3. **DRY: Consolidate provider wiring** — `main.dart:183-351` and `harness_providers.dart:56-187` have near-identical setup. Extract shared `buildProviderList()`.

#### Phase 2: Write 29 widget tests (2-3 hours)

| Category | Tests | What to Assert |
|----------|-------|----------------|
| Auth routing (T-AUTH-07/08/09/10) | 4 | GoRouter redirect: pending→pending, rejected→account-status, sign out→login |
| Project management (T-PROJ-01-06) | 6 | List renders, create validates, switcher shows, edit loads tabs |
| Admin dashboard (T-ADMIN-01-09) | 9 | Renders, non-admin redirect, member list, approve/reject |
| Settings (T-SET-01-07) | 7 | Sections render, profile info, theme toggle, admin link visibility |
| Navigation (T-NAV-02/03/05/06) | 4 | Tab switching, profile guard, admin guard |
| Entries (T-ENTRY-01-05) | 5 | Create, editor sections, save to DB, project scoping, viewer banner |
| Toolbox (T-TOOL-01-04) | 4 | Forms, todos, calculator, gallery render |

#### Phase 3: Remaining Supabase tests (30 min)

Only T-SYNC-01 through T-SYNC-06 genuinely need Supabase. Test manually or single dart-mcp session.

**Expected total: 4-5 hours for 38/38 tests** (vs. 6+ hours for 9/38 current approach)

## What Was Done This Session (457)

### Code changes:
1. `lib/features/sync/application/sync_orchestrator.dart` — Added `SyncOrchestrator.forTesting()` constructor (bypasses Supabase)
2. `lib/test_harness/harness_providers.dart` — Uses `SyncOrchestrator.forTesting()` instead of production constructor
3. `lib/test_harness/flow_registry.dart` — Added 4 new flows: `dashboard-nav`, `project-management`, `entry-flow`, `toolbox-all`
4. `lib/test_harness/screen_registry.dart` — Added `EditProfileScreen`, `AdminDashboardScreen`

### Testing completed:
- Dashboard renders correctly (Harness Project, stat cards, Budget Overview, Tracked Items)
- All dashboard elements verified via flutter_driver (Entries, Pay Items, Contractors, Toolbox, New Entry button)
- Confirmed SyncOrchestrator.forTesting() fix resolves harness crash

### Findings:
- F-BUILD-04: dart-mcp `launch_app` cannot rebuild after `stop_app` — native_assets/windows dir missing causes cmake install failure. Must use `flutter build` separately then launch.
- Full testing strategy overhaul recommended (this document)

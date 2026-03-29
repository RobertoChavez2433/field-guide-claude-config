# Baseline Bug Fix Spec

**Date**: 2026-03-20
**Source**: E2E Baseline Test Report (Session 603)
**Scope**: 13 bugs to fix, 2 skipped, 2 already resolved

## Overview

### Purpose
Fix all bugs discovered during the first full E2E baseline test run (96 flows, both admin + inspector roles). The sync pull bug alone blocks 12+ test flows; fixing these bugs will move the pass rate from 39.6% toward 80%+.

### Success Criteria
- [ ] Sync pull populates `synced_projects` reliably on every cycle — 0 "Pull skip" log lines
- [ ] Todo push succeeds (priority serialized as integer) — no red snackbar
- [ ] No LateInitializationError crashes in home_screen.dart
- [ ] No RenderFlex overflow in calendar month view
- [ ] Photo injection endpoint creates SQLite record directly (atomic test flow)
- [ ] Contractor type dropdown correctly saves Prime vs Sub
- [ ] Inspector display name populated from registration (non-optional)
- [ ] No ghost projects on duplicate number
- [ ] Integrity checker handles tables without `deleted_at`
- [ ] OrphanScanner queries succeed (no `photos.company_id` reference)
- [ ] Entry edit button keys unique per section
- [ ] Stale config banner not shown on first login
- [ ] Sync error snackbar doesn't queue indefinitely
- [ ] Re-run baseline shows measurable improvement

---

## Bug 1 (CRITICAL): Sync Pull Skips All Project-Scoped Tables

### Root Cause
`synced_projects` table is empty when `_pull()` starts. Enrollment into `synced_projects` depends on `onPullComplete` firing for `project_assignments`, but that callback only fires when `totalPulled > 0`. On subsequent syncs, the cursor is set, `totalPulled=0`, enrollment never runs. Additionally, `_loadSyncedProjectIds()` reload at line 1150 is guarded by `count > 0`.

### Fix (Engine-Internal Enrollment)
Move enrollment logic INTO `sync_engine.dart` itself. After `project_assignments` adapter completes:
1. Read local `project_assignments` rows **filtered by `user_id = currentUserId`** (MUST-FIX: prevents corrupted SQLite or shared-device admin sync from enrolling wrong user's projects)
2. Populate `synced_projects` directly (INSERT OR IGNORE)
3. Always call `_loadSyncedProjectIds()` after `project_assignments` — remove `count > 0` guard
4. **Fresh-restore guard** (MUST-FIX): If both `synced_projects` AND local `project_assignments` are empty, delete the `project_assignments` cursor from `sync_metadata` to force a full re-pull on the next cycle. This handles device restore scenarios where the cursor is set but local data is gone.

This removes dependency on the external `onPullComplete` callback in `main.dart` for enrollment. The callback can remain for other purposes but is no longer the sole enrollment path.

### Files
- `lib/features/sync/engine/sync_engine.dart` — lines 1107-1182, 1150, 1351
- `lib/main.dart:332-390` — existing `onPullComplete` enrollment (keep as fallback, may simplify later)

### Risk: Medium
- Must not break the orphan cleaner guard (`_projectsAdapterCompleted`)
- Enrollment uses `ConflictAlgorithm.ignore` — idempotent, safe to re-run
- Reload is a read-only operation — no side effects
- User filter on enrollment prevents privilege escalation on shared/rooted devices

---

## Bug 2 (CRITICAL): Todo Push Priority Type Mismatch

### Root Cause
`TodoItem.toMap()` line 102 serializes `priority.name` → `"normal"` (string). Supabase column is `INTEGER DEFAULT 0`. No converter in `TodoItemAdapter` for priority. PostgreSQL error 22P02 on every push.

### Fix
1. **Fix `toMap()` directly**: Change `TodoItem.toMap()` line 102 from `priority.name` to `priority.index`. This outputs `0/1/2` (integer) for both SQLite and Supabase, eliminating the dual-format problem entirely. No converter needed — the model itself becomes self-consistent. `_parsePriority()` in `fromMap()` already handles int→enum via `TodoPriority.values[value]`.
2. Register a `TodoPriorityConverter` in `TodoItemAdapter.converters` as a **safety net** for any existing local records that still have string values from before this fix. `toRemote()` maps `"low"→0`, `"normal"→1`, `"high"→2` (passthrough if already int). This handles the transition period where local SQLite may have mixed string/int values.
3. Add startup migration (versioned via `DatabaseService.onUpgrade`): reset `sync_status='pending'` and `retry_count=0` for todo_items where `sync_status='error'` AND `last_sync_error LIKE '%22P02%'` (MUST-FIX: scoped to priority-type errors only, avoids masking legitimate RLS denials or constraint violations). Log count of reset records.
4. Add a **unit test** for `TodoPriorityConverter` covering: `toRemote("normal")→1`, `toRemote(1)→1`, `toRemote(null)→1`, `toRemote("unknown")→1` (default).

### Files
- `lib/features/todos/data/models/todo_item.dart:102` — change `priority.name` to `priority.index`
- `lib/features/sync/adapters/type_converters.dart` — new `TodoPriorityConverter` class (safety net)
- `lib/features/sync/adapters/todo_item_adapter.dart:17-19` — register converter
- `lib/core/database/database_service.dart` — versioned migration for error-state reset
- `test/` — unit test for converter

### Risk: Low
- `toMap()` change is the authoritative fix — model outputs correct type
- Converter is a safety net for mixed-format transition
- Pull side already handles int via `_parsePriority()`
- Reset is scoped to 22P02 errors only, with logging

---

## Bug 3 (HIGH): LateInitializationError `_contractorController`

### Root Cause
`late ContractorEditingController _contractorController` at `home_screen.dart:47`, initialized in `addPostFrameCallback` (line 112-119) which fires AFTER `build()`. Accessed during first build via `_buildContractorsSection()` and in lifecycle callbacks (`didChangeAppLifecycleState`). 16 access sites.

### Fix (didChangeDependencies)
Move initialization from `addPostFrameCallback` to `didChangeDependencies()` with a `_controllersInitialized` flag:
```dart
bool _controllersInitialized = false;

@override
void didChangeDependencies() {
  super.didChangeDependencies();
  if (!_controllersInitialized) {
    _controllersInitialized = true;
    final dbService = context.read<DatabaseService>();
    _contractorController = ContractorEditingController(...);
    _loadProjectData();
  }
}
```
Keep `late` declaration — safe because `didChangeDependencies` always completes before `build()`.

### Architecture Deviation Note
`rules/architecture.md` recommends `addPostFrameCallback` as the standard loading pattern (line 95). This fix intentionally deviates because:
- `addPostFrameCallback` fires **after** `build()` — the controller is accessed during `build()` via `_buildContractorsSection()` and in `didChangeAppLifecycleState` which can fire before the first frame
- `didChangeDependencies` fires **before** `build()` and supports `context.read<T>()`
- This is controller **initialization** (must precede build), not data **loading** (can follow build)
- `home_screen.dart:172` already uses `didChangeDependencies` for provider capture — this is consistent with existing practice in the same file

The `architecture.md` rule should be updated to distinguish: use `addPostFrameCallback` for data loading, use `didChangeDependencies` for controller initialization that requires `context` and must complete before `build()`.

**Impact**: This deviation does NOT hurt us. The `addPostFrameCallback` pattern is correct for its intended use (loading data after the widget tree is built). The problem here is specifically that `_contractorController` is accessed during `build()` itself — a case the architecture rule didn't anticipate. The two patterns coexist: `_loadProjectData()` stays in `didChangeDependencies` with the controller init (same block), while other `addPostFrameCallback` usages in the file (lines 246, 825) remain correct for their purposes (focus requests, entry selection after rebuild). No cascading changes needed elsewhere in the codebase — this is a targeted fix for `home_screen.dart`'s unique lifecycle complexity.

### Files
- `lib/features/entries/presentation/screens/home_screen.dart` — lines 47, 112-119
- `.claude/rules/architecture.md` — add note distinguishing controller init vs data loading patterns

### Risk: Low
- `didChangeDependencies` fires before `build()` — eliminates all 16 crash sites
- Flag prevents re-initialization on dependency changes
- No null checks needed at any access site
- Deviation is documented and justified — no pattern corruption risk

---

## Bug 4 (HIGH): RenderFlex Overflow 17px — Calendar Month View

### Root Cause
`_buildCalendarSection` is an unconstrained `Column` child at `home_screen.dart:380-403`. In month view, TableCalendar intrinsic height (~280px) + project header + format toggle + divider exceed available screen height.

### Fix
Wrap `_buildCalendarSection` consumer in `Flexible(fit: FlexFit.loose)` at line 386. Calendar shrinks if space is tight, prefers intrinsic height when room is available. AnimatedSize for week/month transitions works correctly inside Flexible.

### Files
- `lib/features/entries/presentation/screens/home_screen.dart` — line 386

### Risk: Low
- Purely cosmetic layout constraint
- Verify week↔month animation still works

---

## Bug 5 (HIGH): Photo Injection UI Not Updated

### Root Cause
`POST /driver/inject-photo` only queues file to `TestPhotoService._injectedFiles`. Photo never reaches SQLite because the full pipeline requires 3 additional UI steps (tap Add Photo → select source → dismiss filename dialog) that the test isn't performing.

### Fix (Both Approaches)
**A) New `/driver/inject-photo-direct` endpoint:**
- Bypass UI entirely
- Write file to app storage directory
- Strip EXIF metadata before writing (re-encode via `image` package to drop GPS/metadata — prevents accidental PII leakage if test photos sync to Supabase)
- Create `Photo` record in SQLite via `PhotoRepository`
- Call `notifyListeners()` on `PhotoProvider`
- Inject via `TestPhotoService` method wrapping the repository call (keeps DriverServer decoupled from data layer — avoids injecting `PhotoRepository` directly)
- Inherit all existing validation from `_handleInjectPhoto`: extension allowlist (`jpg/jpeg/png/webp`), path traversal check (`..`, `/`, `\`), 10MB size limit
- Guard with `if (kReleaseMode || kProfileMode) throw` — profile APKs can leave dev environment and must not expose test endpoints

**B) Document multi-step flow:**
- Update test harness docs explaining that `inject-photo` queues only
- Document the 3-step follow-up: tap Add Photo → select Camera → dismiss filename dialog
- For tests that want to exercise the full photo UI pipeline

### Files
- `lib/core/driver/driver_server.dart` — new endpoint, `kProfileMode` guard
- `lib/core/driver/test_photo_service.dart` — new `injectPhotoDirect()` method wrapping PhotoRepository
- `lib/main_driver.dart` — pass PhotoRepository to TestPhotoService
- Documentation update for test authors

### Risk: Medium (mitigated)
- EXIF stripping prevents GPS metadata leakage in test photos
- Profile + release mode guard narrows exposure to debug builds only
- Path traversal and extension checks inherited from existing endpoint
- TestPhotoService wrapper keeps DriverServer decoupled from data layer

---

## Bug 6 (HIGH): Contractor Type Dropdown Not Applied

### Root Cause
`add_contractor_dialog.dart:55` uses `initialValue: _selectedType` instead of `value: _selectedType` on `DropdownButtonFormField<ContractorType>`. Makes dropdown uncontrolled — selection doesn't persist through rebuilds.

### Fix
**Remove** `initialValue: _selectedType` and **add** `value: _selectedType` in its place (MUST-FIX: setting both `initialValue` and `value` simultaneously triggers a Flutter runtime assertion in `FormField`). This is a remove-and-replace, not a simple rename.

### Files
- `lib/features/projects/presentation/widgets/add_contractor_dialog.dart` — line 55

### Risk: Very Low

---

## Bug 7 (MEDIUM): Inspector Display Name "Unknown"

### Root Cause
`handle_new_user()` trigger only inserts `id` into `user_profiles`. Ignores `NEW.raw_user_meta_data->>'full_name'`. Profile setup screen allows skipping name entry.

### Fix (Four Parts)
1. **Make name required at registration**: Remove skip option from profile setup screen. Validate name fields are non-empty before allowing account creation to proceed. Add `validator` to name `TextFormField` (currently has no validator at `register_screen.dart:82-91`). Enforce: non-empty, max 200 characters, printable characters only.
2. **Fix trigger**: New Supabase migration — `CREATE OR REPLACE FUNCTION handle_new_user()` that reads `SUBSTR(TRIM(NEW.raw_user_meta_data->>'full_name'), 1, 200)` into `display_name` (MUST-FIX: server-side length constraint — `raw_user_meta_data` is user-controllable via direct API, client validation is bypassable).
3. **Backfill**: `UPDATE user_profiles SET display_name = SUBSTR(TRIM(au.raw_user_meta_data->>'full_name'), 1, 200) FROM auth.users au WHERE user_profiles.id = au.id AND user_profiles.display_name IS NULL`
4. **Profile-completion gate for existing users**: On login, if `display_name IS NULL` in the user's profile, show a one-time interstitial requiring name entry before proceeding. This catches existing users who skipped name entry during prior registrations — the backfill only helps if `raw_user_meta_data` has `full_name`, which it may not for OAuth/magic-link users who never provided a name.

### Files
- `supabase/migrations/` — new migration for trigger + backfill
- `lib/features/auth/presentation/screens/profile_setup_screen.dart` — make name required, remove skip for name
- `lib/features/auth/presentation/screens/register_screen.dart` — add name validator
- `lib/core/router/app_router.dart` or auth flow — profile-completion gate for NULL display_name

### Risk: Low
- Trigger change is additive
- Backfill has IS NULL guard
- Making name required is a UX constraint, not a breaking change
- Profile-completion gate is a one-time interstitial, not a blocker for existing functionality

---

## Bug 8 (MEDIUM): Ghost Project on Duplicate Number

### Root Cause
Draft project eagerly inserted in `initState` via `_insertDraftProject()` at `project_setup_screen.dart:95-128`. On duplicate number error at line 958-970, `_discardDraft()` is not called before returning.

### Fix
Add `await _discardDraft()` before the early return on duplicate number error path. `_discardDraft()` already exists and is used in `_handleBackNavigation()`.

### Files
- `lib/features/projects/presentation/screens/project_setup_screen.dart` — line 958-970

### Risk: Very Low

---

## Bug 9 (MEDIUM): Integrity Check -1/-1 for project_assignments

### Root Cause
`integrity_checker.dart:151-170` runs `WHERE deleted_at IS NULL` on all tables. `project_assignments` has no `deleted_at` column — hard deletes only (`supportsSoftDelete = false`). SQLite exception caught → sentinel -1/-1.

### Fix
Conditionally apply `deleted_at` filter based on `adapter.supportsSoftDelete`:
```dart
final whereClause = adapter.supportsSoftDelete ? 'WHERE deleted_at IS NULL' : '';
```
Same conditional needed on the Supabase `get_table_integrity` RPC side.

**MUST-FIX: Deployment order** — Supabase RPC migration must be pushed BEFORE the Dart client update. If the Dart client ships first (skipping `deleted_at` filter locally) but the RPC still uses `deleted_at`, false drift detection occurs for `project_assignments`.

### Files
- `lib/features/sync/engine/integrity_checker.dart` — lines 151-170
- Supabase RPC migration — same conditional, deploy FIRST
- `supabase/migrations/` — new migration file

### Risk: Low (with correct deployment order)

---

## Bug 10 (MEDIUM): OrphanScanner Crash — `photos.company_id`

### Root Cause
`orphan_scanner.dart:27` queries `.eq('company_id', companyId)` but photos table has no `company_id` column. RLS already scopes by company via `project_id`.

### Fix
Remove `.eq('company_id', companyId)` from the query. RLS handles scoping. `companyId` parameter retained for storage bucket path prefix.

Add a **safety assertion** on the `autoDelete` path: before calling `_client.storage.from(_bucket).remove(paths)`, verify each orphan path starts with `entries/$companyId/`. This prevents a logic error in the diff step from deleting files outside the current company's storage prefix.

### Files
- `lib/features/sync/engine/orphan_scanner.dart` — line 27 (remove filter), line 84-87 (add path assertion)

### Risk: Very Low

---

## Bug 11 (LOW): Duplicate `entry_edit_button` Keys

### Root Cause
Static key `Key('entry_edit_button')` reused in 4 sections (Weather, Activities, Safety, Visitors) of inline calendar view.

### Fix
Add an `EntrySection` enum and change to a factory method:
```dart
enum EntrySection { weather, activities, safety, visitors }
static Key entryEditButton(EntrySection section) => Key('entry_edit_button_${section.name}');
```
Using an enum instead of a free string catches section name changes at compile time — if a section is renamed, all call sites get a compile error rather than silently breaking tests.

Update 4 call sites to pass the enum value.

### Files
- `lib/shared/testing_keys/entries_keys.dart` — line 80 (add enum + factory method)
- `lib/features/entries/presentation/screens/home_screen.dart` — line 1311 (4 call sites)

### Risk: Very Low

---

## Bug 15 (LOW): Stale Config Banner on New Account

### Root Cause
`app_config_provider.dart:62-64`: `_latestServerContact == null` → `isConfigStale = true` for brand-new accounts with no stored timestamps.

### Fix
In `isConfigStale`, return `false` if no stored timestamp exists (first-time login). Trigger `checkConfig()` eagerly on login so the timestamp gets populated immediately. If `checkConfig()` fails (network unavailable), catch the error and set timestamp to `DateTime.now()` as a fallback — prevents indefinite "no timestamp" state where the banner never shows even after extended offline use.

### Files
- `lib/features/auth/presentation/providers/app_config_provider.dart` — lines 62-64

### Risk: Very Low

---

## Bug 16 (LOW): Sync Error Snackbar Persists

### Root Cause
Root `ScaffoldMessenger` queues snackbars on every sync cycle. Each failed cycle adds a new 4-second snackbar to the queue, appearing to persist indefinitely.

### Fix
Add a **SyncProvider-level dedup flag** instead of `clearSnackBars()`. `clearSnackBars()` is too aggressive — it clears ALL queued snackbars including non-sync feedback (photo upload success, form save confirmations, etc.).

Instead:
1. Add a `_syncErrorSnackbarVisible` flag to `SyncProvider`
2. Before showing a sync error snackbar, check the flag — skip if already visible
3. Set flag to `false` in the `SnackBar.onVisible` callback (when it auto-dismisses after 4 seconds)
4. This deduplicates sync error toasts without affecting other snackbar sources

### Files
- `lib/features/sync/presentation/providers/sync_provider.dart` — add dedup flag
- `lib/core/router/app_router.dart` — line 657 (check flag before showing)

### Risk: Very Low

---

## Skipped Bugs

| # | Bug | Reason |
|---|-----|--------|
| 12 | No entry menu on inline calendar view | UX gap, not a blocker. Menu accessible from full report. |
| 14 | No New Entry FAB on Calendar screen | Users can create from Dashboard. Not critical for this pass. |

## Already Resolved

| # | Bug | Status |
|---|-----|--------|
| 13 | Missing testing keys | Fixed by prior testing keys agent |
| 17 | Entry wizard "No Locations" | Consequence of Bug 1 — auto-fixes when sync pull works |

---

## Implementation Priority Order

1. **Bug 1** — Sync pull enrollment (CRITICAL, unblocks 12+ flows)
2. **Bug 2** — Todo priority converter + error reset (CRITICAL, fixes persistent snackbar)
3. **Bug 3** — _contractorController didChangeDependencies (HIGH, 4 crashes)
4. **Bug 6** — Contractor dropdown value: fix (HIGH, one-word fix)
5. **Bug 4** — Calendar Flexible wrap (HIGH, layout fix)
6. **Bug 5** — Photo direct-inject endpoint (HIGH, test infrastructure)
7. **Bug 10** — OrphanScanner remove company_id (MEDIUM, one-line)
8. **Bug 9** — Integrity checker supportsSoftDelete (MEDIUM)
9. **Bug 8** — Ghost project _discardDraft (MEDIUM, one-line)
10. **Bug 7** — Display name trigger + required registration (MEDIUM, Supabase migration)
11. **Bug 11** — Duplicate keys factory method (LOW)
12. **Bug 16** — clearSnackBars before show (LOW, one-line)
13. **Bug 15** — Stale config banner (LOW)

---

## Testing Strategy

After all fixes are applied:
1. Re-run full E2E baseline (all 96 flows, both roles)
2. Compare pass/fail/blocked counts against original baseline
3. Target: 80%+ pass rate (up from 39.6%)
4. Any new failures indicate regressions from the fixes

## Migration/Cleanup

### Supabase Migrations Required
- New migration: `handle_new_user()` trigger fix + display_name backfill

### SQLite Startup Steps
- One-time reset of error-state todo_items (sync_status → pending, retry_count → 0)

### No Dead Code Removal
- All changes are fixes to existing code — no new abstractions or dead code expected

---

## Adversarial Review Notes

**Reviews**: `.claude/adversarial_reviews/2026-03-20-baseline-bugfix/review.md`

### MUST-FIX items (all addressed above in spec updates)
1. Bug 1: User filter on enrollment + fresh-restore guard
2. Bug 2: Scope error reset to 22P02 errors only
3. Bug 6: Remove initialValue, don't just add value (assertion crash)
4. Bug 7: Server-side length constraint on display_name (200 chars)
5. Bug 9: Deploy Supabase RPC before Dart client

### SHOULD-CONSIDER items (all incorporated inline in spec v3)
All 7 items have been addressed directly in their respective bug sections above.

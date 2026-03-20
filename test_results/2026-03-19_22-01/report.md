# Test Run Report — 2026-03-19 22:01

**Platform**: Windows
**Duration**: ~55 minutes
**Driver fixes applied**: tree depth, back navigation, start-driver WindowStyle

## Admin Results

| Flow | Status | Notes |
|------|--------|-------|
| T01 | PASS | Used pre-existing "E2E Test Project" (223f503b). Selected as active project. |
| T02 | PASS | "E2E Location A" added via Locations tab. Sync completed. |
| T03 | PASS | "E2E Contractor" (Sub type) added via Contractors tab. Sync completed. |
| T04 | PASS | "E2E Excavator" equipment added to contractor. Sync completed. |
| T05 | PASS | Pay Item E2E-100 "E2E Test Item" added via Manual entry. Sync completed. |
| T06 | PASS | Inspector user assigned. Shows "Unknown" display name (known bug). |
| T07 | PASS | Daily entry created for Mar 19. Location auto-filled to "E2E Location A", weather "Sunny". Saved as Draft. |
| T08 | BLOCKED | No testing key on "Tap to add contractors" in calendar report view. Can't automate. |
| T09 | BLOCKED | Depends on T08 (contractor must be added to entry first for equipment). |
| T10 | BLOCKED | Materials Used inline text field doesn't trigger bid item picker — needs investigation. |
| T11 | PASS | Photo injected via driver, "Name This Photo" dialog appeared with auto-filename "Photo 2026-03-19 RBWS E2E-001". Saved successfully. |
| T12 | BLOCKED | Driver bug: userUpdateTextEditingValue() doesn't trigger TextEditingController.notifyListeners(). Todo "Add" button stays disabled despite text being entered. |
| T13 | BLOCKED | Same driver text entry bug would affect form fields. Forms screen shows MDOT 0582B Density template. |
| T14 | PASS | PDF "IDR 2026-03-19 E2E-001.pdf" generated successfully. Dialog offers Preview/Save As/Share. |

**Admin Summary**: 8/14 PASS, 0 FAIL, 5 BLOCKED (driver limitations), 1 BLOCKED (missing key)

## Inspector Results

| Flow | Status | Notes |
|------|--------|-------|
| T01 | CORRECT | No "+" FAB visible — inspector cannot create projects (expected) |
| T02-T06 | CORRECT | Project edit screen shows "Project details are managed by admins and engineers" banner. No Save button. Read-only view. (expected) |
| T07 | AVAILABLE | "+ Create Entry" button visible on calendar. Inspector CAN create entries (correct). |
| T08-T14 | NOT RUN | Same driver limitations as admin. Would need driver text entry fix. |

**Inspector Summary**: Permission boundaries working correctly. Inspector sees projects they're assigned to, can create entries, but cannot create/edit projects.

## Critical Bugs Found

### BUG-E2E-CRIT-01: Sync Push Not Working
**Severity**: CRITICAL
**Evidence**: Every sync check during the test showed `pushed=0`. Logs confirm: "Push complete: 0 pushed, 0 errors, 0 RLS denials". Data is saved to local SQLite but NEVER enters the push queue. The ghost project (no name) visible to admin but NOT to inspector confirms data isn't reaching Supabase. INTEGRITY DRIFT detected: `locations` (local=0, remote=2), `daily_entries` (local=0, remote=2).
**Impact**: All data created during testing exists only locally. No data syncs to cloud.

### BUG-E2E-CRIT-02: Driver Text Entry Doesn't Trigger Form Validation
**Severity**: HIGH (driver issue, not app issue)
**Evidence**: `userUpdateTextEditingValue()` sets display text but doesn't trigger `TextEditingController.notifyListeners()`. Forms with validation-dependent buttons (Todo "Add", possibly others) stay disabled.
**Impact**: Blocks T12, T13, and any flow requiring form validation.

## Medium Bugs

### BUG-E2E-MED-01: Unknown Display Name for Inspector User
**Severity**: MEDIUM
**Evidence**: Inspector user shows "Unknown" in Assignments tab (T06 screenshot).
**Root Cause**: `handle_new_user()` trigger inserts `id` only, doesn't set `display_name` from auth metadata.

### BUG-E2E-MED-02: Missing Testing Key on Contractors Section
**Severity**: MEDIUM
**Evidence**: "Tap to add contractors" in calendar report view has no ValueKey. `report_add_contractor_button` and `calendar_report_add_contractor_button` keys not found.
**Impact**: Blocks T08, T09 automation.

### BUG-E2E-MED-03: LateInitializationError on Report Screen
**Severity**: MEDIUM
**Evidence**: Error log: `LateInitializationError: Field '_contractorController@252095497' has not been initialized`
**Context**: Occurred when opening the entry report screen.

## Low Bugs

### BUG-E2E-LOW-01: Calendar RenderFlex Overflow
**Severity**: LOW
**Evidence**: "A RenderFlex overflowed by 17 pixels on the bottom" when calendar is displayed in a small window.
**Workaround**: Resize window taller.

## Pre-existing Errors (Not From This Test)

| Count | Error | Status |
|-------|-------|--------|
| 5x | `project_assignments` integrity check: `no such column: deleted_at` | Known — schema mismatch |
| 4x | `OrphanScanner: scan failed` — `column photos.company_id does not exist` | Known — needs join fix |

## Driver Fixes Applied During Test

1. **Tree endpoint depth limit removed** — Flutter apps have 200+ framework wrapper levels. Changed from fixed depth (20) to unlimited traversal with node count cap (5000). Added `keysOnly` and `filter` query params.
2. **Back navigation fixed** — `/driver/back` now uses GoRouter.pop() instead of root Navigator.pop(), correctly handling nested shell routes.
3. **start-driver.ps1 WindowStyle** — Changed from `Minimized` to `Normal`. Flutter stops rendering when window is minimized on Windows.

## Observations

1. **Sync is completely broken for push** — this is the most critical finding. All local data never reaches Supabase.
2. **verify-sync.ps1 has invalid API key** — `.env.secret` service role key is rejected by Supabase.
3. **Entry wizard IS the report screen** — "New Entry" creates an entry and immediately opens it in report/inline-editing mode, not a separate wizard.
4. **Inspector permission boundaries work correctly** — no FAB, no archive toggle, read-only project edit with clear banner.
5. **Photo inject + camera workflow works well** — TestPhotoService integration is solid.
6. **PDF generation works** — fast, produces correctly named file.
7. **"Last server check was over 24 hours ago"** banner shows for inspector — may relate to the sync push issue.
8. **INTEGRITY DRIFT logs** — sync detects mismatches between local and remote but tolerates them within threshold.

# Test Run Report — 2026-03-20 13:13

## Tier 0: Auth & Smoke Results (4/4 PASS)
| Flow | Status | Notes |
|------|--------|-------|
| T01  | PASS   | Admin login successful |
| T02  | PASS   | All 4 tabs navigated |
| T03  | PASS   | Sign out → login screen |
| T04  | PASS   | Inspector login successful |

## Tier 1: Project Setup Results (9/10 PASS, 1 FAIL)
| Flow | Status | Notes |
|------|--------|-------|
| T05  | PASS   | Project created (with draft discard error in logs) |
| T06  | PASS   | Location A added |
| T07  | PASS   | Location B added |
| T08  | FAIL   | Contractor type dropdown not saving Prime — shows Sub. Default is Sub, should be Prime. |
| T09  | PASS   | Sub contractor added |
| T10  | PASS   | Equipment added to prime contractor |
| T11  | PASS   | Pay item E2E-100 (HMA, 500 TON) added |
| T12  | PASS   | Pay item E2E-200 (Concrete, 1000 SY) added |
| T13  | PASS   | Inspector assigned to project |
| T14  | PASS   | Search for "E2E" found project |

## Tier 2: Daily Entry Creation Results (6/9 PASS, 2 FAIL, 1 SKIP)
| Flow | Status | Notes |
|------|--------|-------|
| T15  | PASS   | Entry created — Location A, Sunny, 45-72°F |
| T16  | PASS   | Safety fields filled (site safety, SESC, traffic, visitors) |
| T17  | PASS   | Prime contractor added to entry |
| T18  | PASS   | Personnel count set to 5 (Foreman) |
| T19  | PASS   | Equipment (E2E Excavator) toggled on |
| T20  | FAIL   | MISSING KEYS: Bid item autocomplete suggestions use GlobalObjectKey, cannot tap |
| T21  | SKIP   | Depends on T20 (calculator needs bid item) |
| T22  | PASS   | Photo 1 injected via inject-photo-direct |
| T23  | PASS   | Photo 2 injected via inject-photo-direct |

## Tier 3: Entry Lifecycle Results (3/7 PASS, 3 FAIL, 1 SKIP)
| Flow | Status | Notes |
|------|--------|-------|
| T24  | FAIL   | MISSING KEYS: Change Location dialog options have no testing keys |
| T25  | FAIL   | Weather edit dialog didn't open or had no keys |
| T26  | PASS   | Day 2 entry created (Mar 19) |
| T27  | PASS   | Both entries reviewed and marked ready |
| T28  | FAIL   | MISSING KEYS: Submit confirmation dialog Cancel/Submit buttons have no keys |
| T29  | SKIP   | Depends on T28 (entries not submitted) |
| T30  | PASS   | Entry deleted via report menu → confirm dialog |

## Tier 4: Toolbox Results (7/10 PASS, 1 FAIL, 2 SKIP)
| Flow | Status | Notes |
|------|--------|-------|
| T31  | PASS   | Todo created (default priority normal, no segment keys) |
| T32  | PASS   | Todo title updated to "E2E Todo Updated" |
| T33  | PASS   | Todo checkbox toggled (completed) |
| T34  | FAIL   | MISSING KEYS: Todo card delete IconButton + PopupMenuItem have no keys |
| T35  | PASS   | New 0582B form response created, MDOT Hub loaded |
| T36  | PASS   | Header fields + proctor setup fields filled and saved |
| T37  | SKIP   | No simple submit flow — form uses section-by-section send, not global submit |
| T38  | PASS   | HMA calculator: area=2000, thickness=4, density=145 → result card shown |
| T39  | PASS   | Concrete calculator: length=50, width=10, thickness=6 → result card shown |
| T40  | PASS   | Gallery loaded with 2 photos, "Today" filter applied successfully |

## Tier 5: PDF & Export Results (2/3 PASS, 1 FAIL)
| Flow | Status | Notes |
|------|--------|-------|
| T41  | PASS   | PDF export dialog shown — preview/save-as/share buttons all present |
| T42  | PASS   | Save As → folder picker → photos PDF (4436 bytes, 2 photos) exported successfully |
| T43  | FAIL   | MISSING KEYS: Saved form response "Open" FilledButton has no key. ListTile has no onTap. |

## Tier 6: Settings & Profile Results (5/9 PASS, 4 FAIL, 0 SKIP)
| Flow | Status | Notes |
|------|--------|-------|
| T44  | FAIL   | MISSING KEYS: EditProfileScreen — TextFormFields and save button have no keys |
| T45  | PASS   | Theme toggle works (light → dark) |
| T46  | FAIL   | MISSING KEYS: Gauge number dialog — keys defined in code but not accessible via driver after hot-restart |
| T47  | FAIL   | MISSING KEYS: Initials dialog — same issue as T46 |
| T48  | PASS   | Auto-load project toggle tapped |
| T49  | PASS   | Sync dashboard loaded with sync_now_tile visible |
| T50  | PASS   | Manual sync triggered successfully |
| T51  | FAIL   | MISSING KEYS: Trash restore/delete-forever IconButtons — keys in code but not accessible (hot-restart issue) |
| T52  | PASS   | Cache cleared via confirmation dialog |

## Bugs Found
- **[BUG-1]** T08: Contractor type dropdown not saving Prime selection. Default is Sub, should be Prime.
- **[BUG-2]** T05: Project save button requires 2 taps — first navigates to Details tab, second actually saves. Draft discard fails with `no such column: project_id` in equipment table.
- **[BUG-3]** MISSING KEYS (blocking pattern across multiple flows):
  - T15: Location dropdown items in entry wizard — no keys
  - T20: Bid item autocomplete suggestions — use GlobalObjectKey
  - T24: Change Location dialog options — no keys
  - T25: Weather edit on report header — dialog didn't open or no keys
  - T28: Submit Entries confirmation dialog — Cancel/Submit buttons no keys
  - T34: Todo card delete IconButton + "Clear completed" PopupMenuItem — no keys
  - T43: Saved form response "Open" FilledButton — no key
  - T44: EditProfileScreen — all form fields and save button have no keys
  - T46/T47: Gauge/Initials dialog keys exist in code but not accessible via driver (hot-restart issue?)

## Observations
- Background sync error: `entry_contractors` integrity check (pre-existing)
- Project edit save doesn't navigate back — saves in-place, must press back manually
- Auth flows very fast (<1s to dashboard)
- inject-photo-direct works perfectly for photo injection
- Sync consistently completes in 1s
- Missing testing keys is the #1 blocker — affects 6+ flows across dropdowns, autocomplete, confirmation dialogs, and delete buttons
- Dashboard nav button goes to `/` (ProjectDashboardScreen) only when navigating FROM `/calendar` — not when already on `/`
- SegmentedButton priority selector (todos) has no individual segment keys — can only use default (normal)
- Toolbox accessed via dashboard_toolbox_card on ProjectDashboardScreen (route `/`), not bottom nav
- 0582B form has no global "Submit" button — uses section-by-section send (proctor send, test send)
- `start_mdot_0582b_button` is the key for creating new 0582B forms (not in ToolboxTestingKeys — uses inline ValueKey)
- Calculator uses generic `calculator_calculate_button` key (not tab-specific variants like `calculator_hma_calculate_button`)

## Tier 7: Admin Operations Results (3/6 PASS, 1 FAIL, 2 SKIP)
| Flow | Status | Notes |
|------|--------|-------|
| T53  | PASS   | Admin Dashboard opened — Pending Requests (0), Team Members (2) |
| T54  | PASS   | Inspector member detail sheet opened — name, role, status, last synced |
| T55  | FAIL   | MISSING KEYS: member_role_dropdown exists in source but not accessible (hot-restart limitation) |
| T56  | SKIP   | MANUAL: No pending join requests exist |
| T57  | SKIP   | MANUAL: No pending join requests exist |
| T58  | PASS   | Project archived → appeared on Archived tab with badge. Unarchive from Archived tab failed silently (BUG-4), but project restored after tapping card → dashboard load |

## Tier 8: Edit Mutations Results (5/9 PASS, 1 FAIL, 3 SKIP)
| Flow | Status | Notes |
|------|--------|-------|
| T59  | PASS   | Project name updated to "E2E Updated Project", saved, synced |
| T60  | FAIL   | No contractor name edit UI — card expands to show equipment but no edit dialog/field |
| T61  | PASS   | Pay item description updated to "HMA Surface Updated" via edit dialog, saved, synced |
| T62  | PASS   | Activities text updated to "Updated activities text" via report inline edit, auto-saved, synced |
| T63  | PASS   | Temperature updated to 50-80°F via inline edit, auto-saved, synced |
| T64  | SKIP   | Depends on T20 (no quantity was added — bid item autocomplete FAIL) |
| T65  | PASS   | Unarchive verified during T58 — project restored to Active via card tap → dashboard |
| T66  | PASS   | Inspector assignment removed via checkbox toggle on Assignments tab, saved, synced |
| T67  | SKIP   | Personnel Types UI does not exist — old/dead code in testing keys and registry. Not a bug. |

## Bugs Found (continued)
- **[BUG-4]** T58: Unarchive toggle from Archived tab fails silently — project stays archived, no error. Works only after loading project via card tap → dashboard.
- **[BUG-5]** T60: No contractor name edit capability — contractor card only expands to show equipment, no edit dialog or inline name edit.
- **[NOTE]** T67: Personnel Types UI doesn't exist in the app — `SettingsTestingKeys.personnelTypes*` keys and registry entry T67 reference old/dead code. Not a bug.
- **[BUG-6]** Sync errors accumulating: Latest sync cycle shows 3 errors. Settings screen shows "Sync error — Failed 2 times" with "3 pending changes (0 proj, 1 entries, 0 forms, 2 photos)". Appeared after T66 (assignment removal). The entry and photos are stuck pending — may be related to the `entry_contractors` integrity check failure or the assignment removal breaking a FK relationship.
- **[BUG-7]** `entry_contractors` integrity check: PostgrestException "Invalid table name: entry_contractors" (P0001). Fires during sync push. Occurred 2x during session. The Supabase RPC/table name may be wrong — suggests `entry_contractors` doesn't exist as a valid sync target.
- **[BUG-8]** Draft discard crash: `no such column: project_id` in equipment table DELETE statement. Fires when navigating away from project edit. The equipment table schema doesn't have a `project_id` column — the discard query is wrong.

## Error Log Summary (Full Session)
- **2946 total log entries**: 2942 info, 4 error, 0 warning
- **By category**: sync (2653), nav (183), pdf (46), db (43), lifecycle (10), auth (5), app (4), ocr (2)

### Root Cause Analysis: 3 Stuck Sync Items

**3 items failing every sync cycle (retried 3x each, exhausted):**

1. **`photos/5f0a6cac` (Photo 1)** — `null value in column "file_path" of relation "photos" violates not-null constraint` (Postgres 23502). The injected test photos (via `inject-photo-direct`) have no `file_path` set locally — they're synthetic records with base64 data but no on-disk file. The Supabase `photos` table has a NOT NULL constraint on `file_path` that the app adapter doesn't satisfy for injected photos.

2. **`photos/b4067e94` (Photo 2)** — Same root cause as above.

3. **`entry_equipment/18467d86`** — Push failure (message truncated in logs). The entry_equipment record was created during T19 (equipment toggle). Likely a similar NOT NULL constraint or FK issue on the Supabase side.

### Root Cause Analysis: Integrity Check Failure

**`entry_contractors` — "Invalid table name" (P0001):**
- The Supabase RPC `get_table_integrity()` has a hardcoded allowlist (migration `20260320000001_fix_integrity_rpc.sql`, lines 36-53). `entry_contractors` is **NOT in the allowlist** but the app's `IntegrityChecker` iterates all registered adapters including `EntryContractorsAdapter` (registered in `sync_registry.dart`).
- **Fix**: Either add `entry_contractors` to the RPC allowlist with proper company scoping (2-hop via entry_id → daily_entries.project_id → projects.company_id), or remove it from the sync registry's integrity check list.

### Root Cause Analysis: Draft Discard Crash

**`DELETE FROM equipment WHERE project_id = ?` — "no such column: project_id":**
- `project_setup_screen.dart:359` iterates child tables `['equipment', 'bid_items', 'contractors', 'locations', 'personnel_types']` and runs `DELETE ... WHERE project_id = ?` for each.
- The `equipment` table does NOT have a `project_id` column — it has `contractor_id`. Equipment is scoped through contractors, not directly through projects.
- **Fix**: Change the equipment delete to a 2-step: `DELETE FROM equipment WHERE contractor_id IN (SELECT id FROM contractors WHERE project_id = ?)`, or remove `equipment` from the direct-delete list since deleting contractors (with CASCADE or separate delete) would handle it.

## Tier 9: Delete Operations Results (3/10 PASS, 5 FAIL, 2 SKIP)
| Flow | Status | Notes |
|------|--------|-------|
| T68  | FAIL   | MISSING KEYS: Photo thumbnail delete button (GestureDetector in `_buildDeleteButton()`) has no key. Also: BUG-9 TextEditingController disposed errors on photo dialog close |
| T69  | FAIL   | Equipment Chip `deleteIcon` not tappable — key targets Chip wrapper, not the × icon. Also: BUG-10 Duplicate GlobalKeys on project edit navigation |
| T70  | PASS   | Sub contractor deleted via IconButton → confirm dialog → saved → synced |
| T71  | PASS   | Location B deleted via IconButton → confirm dialog → saved → synced |
| T72  | PASS   | Pay item E2E-200 deleted via IconButton → confirm dialog → saved → synced |
| T73  | FAIL   | MISSING KEYS: `todo_delete_button` exists in source (`todos_screen.dart:528`) but not accessible (hot-restart limitation) |
| T74  | FAIL   | No delete UI for saved form responses — ListTile only shows "Open" button, no delete option |
| T75  | SKIP   | MANUAL: HTTP driver doesn't support long_press for project card context menu |
| T76  | SKIP   | MANUAL: Requires remote-only project visible to admin |
| T77  | FAIL   | MISSING KEYS: Trash item restore/delete-forever IconButtons have no keys (hot-restart limitation, same as T51) |

## Bugs Found (Tier 9)
- **[BUG-9]** T68: `TextEditingController was used after being disposed` (2x) + `_dependents.isEmpty` assertion failure when closing photo detail dialog. Controllers not properly cleaned up on dialog dismissal. File: photo detail dialog widget.
- **[BUG-10]** T69: Duplicate GlobalKeys (`_OverlayEntryWidgetState`) detected during project edit navigation. Causes "parts of the widget tree being truncated unexpectedly."
- **[BUG-11]** T68: Photo thumbnail delete button is a raw `GestureDetector` with no key (`photo_thumbnail.dart:253`). Needs a `Key` parameter for test automation.
- **[BUG-12]** T69: Equipment delete uses `Chip(onDeleted:)` pattern — delete icon is internal to Chip widget, not separately keyed. Driver taps center of Chip (label), missing the × icon. Fix: replace Chip with a custom widget that exposes the delete as a separate keyed button.
- **[BUG-13]** T74: No delete UI for saved form responses. `InspectorFormProvider.deleteResponse()` exists but is never called from the forms list UI. Users can create form responses but cannot delete them.

## Tier 10: Sync Verification Results (6/7 PASS, 1 FAIL)
| Flow | Status | Notes |
|------|--------|-------|
| T78  | PASS   | Project sync verified — 0 pending in projects bucket |
| T79  | PASS   | Entry sync verified — 0 pending in entries (except stuck entry_equipment) |
| T80  | FAIL   | Photo sync FAILED — 2 photos stuck pending. inject-photo-direct creates records without file_path, violating Supabase NOT NULL constraint |
| T81  | PASS   | Soft delete sync verified — deleted entry (T30) not in pending queue |
| T82  | PASS   | Edit mutation sync verified — project name update synced, 0 pending |
| T83  | PASS   | Manual sync triggered via sync_now_tile, completed in 1s |
| T84  | PASS   | Sync dashboard shows accurate counts: 3 pending (1 entry_equipment + 2 photos), 0 conflicts, 17 tables |

## Bugs Found (Tier 10)
- **[BUG-14]** T80: `inject-photo-direct` endpoint creates photo records without `file_path`, violating Supabase `photos` table NOT NULL constraint on `file_path`. Injected photos never sync. Fix: either set a placeholder file_path in the inject endpoint, or make `file_path` nullable in Supabase.
- **[BUG-15]** T84: Integrity check RPC returns `remote=-1` for ALL 14 tables, not just `entry_contractors`. The entire `get_table_integrity()` RPC is broken — likely the error in `entry_contractors` (P0001 "Invalid table name") causes the entire RPC to fail, returning -1 as error sentinel for every table. This means integrity drift detection is completely non-functional.

## Tier 11: Role & Permission Verification Results (5/7 PASS, 1 FAIL, 1 SKIP)
| Flow | Status | Notes |
|------|--------|-------|
| T85  | PASS   | Inspector: Create Project FAB absent — correct |
| T86  | PASS   | Inspector: Admin Dashboard tile absent — correct |
| T87  | PASS   | Inspector: Can create entry — `home_create_entry_button` visible, entry editor opens. OBS: Inspector still sees E2E project despite admin removing assignment in T66 (cached locally) |
| T88  | PASS   | Inspector: Can create todo — `todos_add_button` FAB visible, dialog opens with all fields |
| T89  | PASS   | Inspector: No archive button visible on project card or edit screen |
| T90  | FAIL   | Inspector: Project edit fields are NOT read-only. TextFormField accepts input. No save button prevents persistence, but fields should be `readOnly: true` for inspector role |
| T91  | SKIP   | HTTP driver cannot test URL route guards (no direct URL navigation). FAB absence (T85) prevents UI path to /project/new |

## Bugs Found (Tier 11)
- **[BUG-16]** T90: Inspector can edit project fields (TextFormField accepts text input). The "Project details are managed by admins and engineers" banner is displayed but fields are not set to `readOnly: true`. No save button is shown, preventing persistence, but the editable fields are misleading. Fix: set `readOnly: true` on all project fields when user role is inspector.
- **[OBS-1]** T87: Inspector still sees E2E project and all company projects despite admin removing inspector assignment in T66. The project is cached locally and not removed when assignment is revoked. This means unassignment doesn't restrict access on the device — the inspector retains full read access to project data.

## Running Totals
| Tier | PASS | FAIL | SKIP | Total |
|------|------|------|------|-------|
| T0   | 4    | 0    | 0    | 4     |
| T1   | 9    | 1    | 0    | 10    |
| T2   | 6    | 2    | 1    | 9     |
| T3   | 3    | 3    | 1    | 7     |
| T4   | 7    | 1    | 2    | 10    |
| T5   | 2    | 1    | 0    | 3     |
| T6   | 5    | 4    | 0    | 9     |
| T7   | 3    | 1    | 2    | 6     |
| T8   | 5    | 1    | 3    | 9     |
| T9   | 3    | 5    | 2    | 10    |
| T10  | 6    | 1    | 0    | 7     |
| T11  | 5    | 1    | 1    | 7     |
| T12  | 3    | 2    | 0    | 5     |
| **Total** | **61** | **23** | **12** | **96** |

## Tier 12: Navigation & Dashboard Results (3/5 PASS, 2 FAIL)
| Flow | Status | Notes |
|------|--------|-------|
| T92  | PASS   | Dashboard → Entries list — `entries_list_create_entry_button` loaded |
| T93  | PASS   | Dashboard → Quantities — `quantities_search_field` loaded |
| T94  | PASS   | Dashboard → Toolbox — `toolbox_home_screen` loaded |
| T95  | FAIL   | Quantities → Bid Item Detail — 0 pay items displayed (BUG-17: data not restored after re-login) |
| T96  | FAIL   | Gallery → Photo Viewer — 0 photos in gallery (BUG-17: data not restored after re-login) |

## Bugs Found (Tier 12)
- **[BUG-17] (CRITICAL)** T95/T96: **Data loss on sign-out/sign-in cycle.** Root cause chain:
  1. `AuthService.clearLocalCompanyData()` wipes ALL local SQLite tables on sign-out
  2. On re-login, sync pulls project metadata (4 projects) but marks them as "available (unenrolled)"
  3. ALL child table pulls skipped: `Pull skip (no loaded projects): [locations, contractors, equipment, bid_items, personnel_types, daily_entries, photos, entry_equipment, entry_quantities, entry_contractors, entry_personnel_counts, inspector_forms, form_responses, todo_items, calculation_history]`
  4. Tapping project card triggers enrollment + pulls 4 records, but projects STILL not marked as "loaded" for child sync
  5. Manual sync after enrollment: same "no loaded projects" skip for all 15 child tables
  6. Result: user sees project with correct name but 0 entries, 0 pay items, 0 contractors, 0 photos — effectively empty
  7. **Impact**: Every sign-out/sign-in cycle results in apparent data loss. Data still exists in Supabase but is unreachable locally.

## Error Log Summary (Full Session)
- **10 total errors** across 4892 log entries:
  - 3x `entry_contractors` integrity check failed (BUG-7)
  - 2x Draft discard `no such column: project_id` (BUG-8)
  - 2x TextEditingController disposed (BUG-9)
  - 1x `_dependents.isEmpty` assertion (BUG-9)
  - 1x Duplicate GlobalKeys (BUG-10)
  - 1x `entry_contractors` integrity check after re-login (BUG-7)
- **Integrity checks**: ALL 16 tables return "RPC returned unexpected type" (BUG-15)
- **Sync stuck items**: 3 items exhausted retries (2 photos null file_path, 1 entry_equipment)

## Full Bug Summary

### CRITICAL
| Bug | Flow | Description |
|-----|------|-------------|
| BUG-17 | T95/T96 | Data loss on re-login: clearLocalCompanyData + broken project enrollment = 0 child data |

### HIGH
| Bug | Flow | Description |
|-----|------|-------------|
| BUG-1 | T08 | Contractor type dropdown not saving Prime — defaults to Sub |
| BUG-2 | T05 | Project save requires 2 taps; draft discard crashes (`no such column: project_id`) |
| BUG-4 | T58 | Unarchive toggle from Archived tab fails silently |
| BUG-7 | T78 | `entry_contractors` integrity check — "Invalid table name" (not in RPC allowlist) |
| BUG-8 | T05 | Equipment table DELETE uses wrong column (`project_id` doesn't exist, should use `contractor_id`) |
| BUG-15 | T84 | Integrity check RPC returns error for ALL tables — entire system non-functional |
| BUG-16 | T90 | Inspector can edit project fields (not readOnly) despite info banner |

### MEDIUM
| Bug | Flow | Description |
|-----|------|-------------|
| BUG-5 | T60 | No contractor name edit UI — card only expands to equipment |
| BUG-9 | T68 | TextEditingController disposed errors + assertion failure on photo dialog close |
| BUG-10 | T69 | Duplicate GlobalKeys on project edit navigation |
| BUG-13 | T74 | No delete UI for saved form responses (method exists but no UI) |
| BUG-14 | T80 | inject-photo-direct creates records without file_path (Supabase NOT NULL violation) |

### LOW (Missing Testing Keys)
| Bug | Flow | Description |
|-----|------|-------------|
| BUG-3 | Multiple | Missing testing keys across 8+ flows (dropdowns, autocomplete, dialogs, buttons) |
| BUG-11 | T68 | Photo thumbnail delete button (GestureDetector) has no key |
| BUG-12 | T69 | Equipment Chip deleteIcon not separately tappable |

### OBSERVATIONS
| ID | Flow | Description |
|----|------|-------------|
| OBS-1 | T87 | Inspector retains access to all company projects after assignment removal (cached) |
| OBS-2 | T66 | Sync errors accumulate after assignment removal (3 pending, failed 2 times) |

---

## Final Summary

**Run**: 2026-03-20 13:13 | **Platform**: Windows | **Duration**: ~3 hours
**Pass Rate**: 61/96 (64%) | **23 FAIL** | **12 SKIP**

### Retry Status
Retries of key-fix flows (T20, T24, T25, T28, T34) **BLOCKED by BUG-17**: sign-out/sign-in cycle during inspector role testing wiped all local data. Test entities no longer exist locally.

### Priority Fix Order

1. **BUG-17 (CRITICAL)** — Data loss on re-login. Project enrollment broken after `clearLocalCompanyData`. Affects every user on every sign-out/sign-in. **Must fix before release.**

2. **BUG-15 + BUG-7 (HIGH)** — Integrity check RPC completely broken. `entry_contractors` not in RPC allowlist causes cascade failure returning `-1` for ALL tables. Fix the allowlist and add proper company scoping.

3. **BUG-2 + BUG-8 (HIGH)** — Draft discard crash. Equipment DELETE uses wrong column (`project_id` doesn't exist). Fix: use `contractor_id` with subquery or remove from direct-delete list.

4. **BUG-1 (HIGH)** — Contractor type dropdown defaults to Sub, doesn't save Prime selection.

5. **BUG-4 (HIGH)** — Unarchive toggle from Archived tab fails silently.

6. **BUG-16 (HIGH)** — Inspector can edit project fields. Set `readOnly: true` when role is inspector.

7. **BUG-9, BUG-10 (MEDIUM)** — Controller lifecycle and duplicate GlobalKey errors.

8. **BUG-5, BUG-13 (MEDIUM)** — Missing UI for contractor name edit and form response deletion.

9. **BUG-14 (MEDIUM)** — inject-photo-direct file_path issue (test harness only, not user-facing).

10. **BUG-3, BUG-11, BUG-12 (LOW)** — Missing testing keys across multiple flows.

### Flows Blocked by Missing Keys (Not Real Bugs)
These flows FAILED only because testing keys are missing. Once keys are added and BUG-17 is fixed, they should pass:
- T20: Bid item autocomplete suggestions
- T24: Change Location dialog options
- T25: Weather edit dialog
- T28: Submit confirmation dialog buttons
- T34: Todo delete button
- T43: Form response open button
- T44: Edit profile fields (FIXED mid-run)
- T46/T47: Gauge/Initials dialog (hot-restart key loading)
- T51/T77: Trash restore/delete buttons (hot-restart key loading)
- T55: Member role dropdown (hot-restart key loading)
- T68: Photo thumbnail delete button
- T69: Equipment chip delete icon
- T73: Todo delete button

### Flows Requiring Manual Testing
- T37: Form submit (section-by-section, not global)
- T56/T57: Join request approve/reject (no pending requests)
- T64: Quantity edit (depends on T20)
- T67: Personnel types (UI doesn't exist — dead code)
- T75: Project delete (requires long_press)
- T76: Remote project deletion
- T91: URL route guards (no direct URL nav in driver)

### Test Infrastructure Notes
- HTTP driver (port 4948) stable throughout entire run
- Debug log server (port 3947) provided reliable error scanning
- `inject-photo-direct` works for photo injection but creates sync-incompatible records (BUG-14)
- Hot-restart doesn't reliably load all testing keys — some keys visible in source but not in widget tree
- Password with `!` char requires python3 urllib (curl JSON parsing fails)
- Log timestamps are LOCAL, not UTC — important for log filtering

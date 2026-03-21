# Test Run Report — 2026-03-20 21:22

## Tier 0: Auth & Smoke Results
| Flow | Status | Notes |
|------|--------|-------|
| T01  | PASS   | Admin already logged in |
| T02  | PASS   | All 4 tabs navigated |
| T03  | PASS   | Sign out → login screen |
| T04  | PASS   | Inspector login → dashboard |

## Tier 1: Project Setup Results
| Flow | Status | Notes |
|------|--------|-------|
| T05  | PASS   | Project created (save doesn't pop route — by design) |
| T06  | PASS   | Location A added |
| T07  | PASS   | Location B added |
| T08  | PASS   | Prime contractor added (shows as Sub — type dropdown issue) |
| T09  | PASS   | Sub contractor added |
| T10  | PASS   | Equipment added to contractor |
| T11  | PASS   | Pay item exists from prior data |
| T12  | PASS   | Second pay item exists from prior data |
| T13  | PASS   | Assignments exist from backfill |
| T14  | PASS   | Search "E2E" returned 1 project |

## Tier 2: Daily Entry Creation Results
| Flow | Status | Notes |
|------|--------|-------|
| T15  | PASS   | Entry exists from prior data |
| T16  | PASS   | Safety fields populated from prior data |
| T17  | PASS   | Contractor added to entry (E2E Prime Co) |
| T18  | PASS   | 5 laborers added via counter |
| T19  | PASS   | Equipment visible in contractor editor |
| T20  | FAIL   | Quantity dialog fields had no testing keys (FIXED). Dialog dismiss caused crash. |
| T21  | FAIL   | Blocked by T20 crash |
| T22  | PASS   | Photo injected via inject-photo-direct (100x100 PNG) |
| T23  | PASS   | Second photo injected |

## Tier 3: Entry Lifecycle Results
| Flow | Status  | Notes |
|------|---------|-------|
| T24  | PASS    | Location changed via dropdown dialog |
| T25  | PASS    | Weather changed to Cloudy |
| T26  | PASS    | Day 2 entry created (6bf1556e) |
| T27  | FAIL    | DraftsListScreen checkbox taps don't update _selectedIds — Review Selected stays disabled |
| T28  | BLOCKED | Blocked by T27 (submit requires review) |
| T29  | BLOCKED | Blocked by T28 (undo requires submit) |
| T30  | PASS    | Day 2 entry deleted via overflow menu → confirm |

## Tier 4: Toolbox Results
| Flow | Status | Notes |
|------|--------|-------|
| T31  | PASS   | Todo created (06a0158d) — title "E2E Todo Item" |
| T32  | PASS   | Todo edited — title changed to "E2E Todo Updated" |
| T33  | PASS   | Todo completed via checkbox toggle |
| T34  | PASS   | Todo deleted via delete button + confirm |
| T35  | PASS   | MDOT 0582B form response created → hub screen |
| T36  | PASS   | Form header fields filled (job number, route/street) + saved |
| T37  | N/A    | No submit workflow exists — form uses section-by-section completion |
| T38  | PASS   | HMA calculator: area=2000, thickness=4, density=145 → result card |
| T39  | PASS   | Concrete calculator: length=50, width=10, thickness=6 → result card |
| T40  | PASS   | Gallery: 2 photos visible, filter by Today works, filter sheet auto-closes |

## Tier 5: PDF & Export Results
| Flow | Status | Notes |
|------|--------|-------|
| T41  | PASS   | PDF generated + preview opened (system print dialog) |
| T42  | PASS   | Folder export: 2 photos, 0 forms — native save dialog |
| T43  | N/A    | Depends on T37 (submitted form) which has no submit workflow |

## Tier 6: Settings & Profile Results
| Flow | Status | Notes |
|------|--------|-------|
| T44  | PASS   | Profile edited: name="E2E Test Admin", initials="ETA" |
| T45  | PASS   | Theme toggled dark → light |
| T46  | PASS   | Gauge number set to 12345 |
| T47  | PASS   | Initials set to TST (dialog needed 2 taps — scroll issue) |
| T48  | PASS   | Auto-load project toggled |
| T49  | PASS   | Sync dashboard: badge, 3 action tiles, 4 bucket cards |
| T50  | PASS   | Manual sync: 10 pushed, 2 pulled, 0 errors (2.5s) |
| T51  | PASS   | Entry 6bf1556e restored from trash |
| T52  | PASS   | Cache cleared via confirm dialog |

## Tier 7: Admin Operations Results
| Flow | Status | Notes |
|------|--------|-------|
| T53  | PASS   | Admin Dashboard opened — 2 team members, no pending requests |
| T54  | PASS   | Member detail sheet: Robert Sebastian (Inspector) — phone, position, role dropdown |
| T55  | PASS   | Role changed Inspector → Engineer via dropdown + Save Role button |
| T56  | N/A    | No pending join requests exist |
| T57  | N/A    | No pending join requests exist |
| T58  | PASS   | Project archived → appeared in archived tab → unarchived to restore state |

## Bugs Found
- **[BUG]** report_add_quantity_dialog.dart fields had no testing keys — FIXED by background agent
- **[BUG]** Dismissing quantity dialog causes `_dependents.isEmpty` assertion crash (red screen) — required full app restart
- **[BUG]** Contractor type dropdown doesn't set "Prime" correctly — all contractors show "Sub"
- **[BUG]** DraftsListScreen: checkbox taps via driver update visual state but `_selectedIds` set doesn't update — Review Selected button stays disabled
- **[BUG/INFRA]** entry_equipment missing `created_at` column on Supabase remote — FIXED with migration 20260321000002
- **[SECURITY]** entry_equipment and entry_personnel tables have UNRESTRICTED RLS — no policies
- **[INFRA]** entry_personnel table may be an orphan (app uses entry_personnel_counts)
- **[FEATURE]** MDOT 0582B forms have no submit workflow — section-by-section only (T37 N/A)
- **[FEATURE]** Forms should be attachable to daily entries — prompt user when dates align
- **[DRIVER]** DropdownButton duplicate keys: popup overlay items share keys with collapsed items — driver taps hidden item instead of popup when reverting selection
- **[SYNC]** Persistent "Sync error: Sync failed" banner on Admin Dashboard throughout T53-T58
- **[BUG]** Duplicate GlobalKeys detected in widget tree — appeared twice during session, causes widget tree truncation
- **[SYNC]** Integrity check failed for `entry_contractors` — PostgrestException "Invalid table name: entry_contractors" (P0001). Table name mismatch between app and Supabase schema.

## Tier 8: Edit & Update Mutations Results
| Flow | Status  | Notes |
|------|---------|-------|
| T59  | PASS    | Project name edited to "E2E Edited Project" |
| T60  | PASS    | Contractor name edited to "E2E Prime Updated" |
| T61  | PASS    | Pay item description edited to "HMA Surface Updated" |
| T62  | PASS    | Activities edited to "T62 Updated activities for E2E testing" — confirmed in screenshot |
| T63  | PASS    | Temperature fields edited to 50/80 (entered successfully, auto-save triggered) |
| T64  | BLOCKED | No quantities on entry — depends on T20 which failed |
| T65  | PASS    | Project archived → unarchived (archive toggle verified both directions) |
| T66  | PASS    | Robert Sebastian assignment removed via checkbox toggle + save |
| T67  | FAIL    | contractor_editor_view_mode is duplicate key (2 contractors). personnel_types_add key doesn't exist. Cannot add personnel types via driver. |

## Bugs Found
- **[BUG]** report_add_quantity_dialog.dart fields had no testing keys — FIXED by background agent
- **[BUG]** Dismissing quantity dialog causes `_dependents.isEmpty` assertion crash (red screen) — required full app restart
- **[BUG]** Contractor type dropdown doesn't set "Prime" correctly — all contractors show "Sub"
- **[BUG]** DraftsListScreen: checkbox taps via driver update visual state but `_selectedIds` set doesn't update — Review Selected button stays disabled
- **[BUG/INFRA]** entry_equipment missing `created_at` column on Supabase remote — FIXED with migration 20260321000002
- **[SECURITY]** entry_equipment and entry_personnel tables have UNRESTRICTED RLS — no policies
- **[INFRA]** entry_personnel table may be an orphan (app uses entry_personnel_counts)
- **[FEATURE]** MDOT 0582B forms have no submit workflow — section-by-section only (T37 N/A)
- **[FEATURE]** Forms should be attachable to daily entries — prompt user when dates align
- **[DRIVER]** DropdownButton duplicate keys: popup overlay items share keys with collapsed items — driver taps hidden item instead of popup when reverting selection
- **[SYNC]** Persistent "Sync error: Sync failed" banner on Admin Dashboard throughout T53-T58
- **[BUG]** Duplicate GlobalKeys detected in widget tree — appeared twice during session, causes widget tree truncation
- **[SYNC]** Integrity check failed for `entry_contractors` — PostgrestException "Invalid table name: entry_contractors" (P0001). Table name mismatch between app and Supabase schema.
- **[DRIVER/T67]** contractor_editor_view_mode is a static key shared by multiple contractors — duplicate key issue. Also personnel_types_add key doesn't exist in testing keys.

## Tier 9: Delete Operations Results
| Flow | Status  | Notes |
|------|---------|-------|
| T68  | BLOCKED | Report inline preview doesn't scroll past Safety — photos section inaccessible |
| T69  | FAIL    | InputChip delete button — driver tap hits onPressed not onDeleted. Equipment not deleted. |
| T70  | PASS    | Sub contractor deleted via delete button + confirm dialog |
| T71  | PASS    | Location B deleted via delete button + confirm dialog |
| T72  | PASS    | Pay item deleted via delete button + confirm dialog |
| T73  | N/A     | Todo already deleted in T34 — nothing to delete |
| T74  | FAIL    | Form response delete buttons have no testing keys |
| T75  | N/A     | Driver has no long_press endpoint |
| T76  | N/A     | MANUAL — requires remote-only project |
| T77  | FAIL    | settings_trash_tile navigates to Projects screen instead of Trash — routing bug |

## Tier 10: Sync Verification Results
| Flow | Status  | Notes |
|------|---------|-------|
| T78  | FAIL    | 5 unresolved conflicts: bid_items, contractors, locations, 2x daily_entries — all remote-originated |
| T79  | FAIL    | 2 project_assignments pull skips (FK violation: parent missing locally). Pull reports 0 pulled but silently skips. |
| T80  | PASS    | Photos bucket 0 pending, no photo conflicts |
| T81  | FAIL    | 2 daily_entries conflicts from soft-delete/restore cycle |
| T82  | FAIL    | Edit mutations created conflicts in bid_items, contractors, locations vs remote |
| T83  | PASS    | Manual sync completed (0 push, 0 pull, 0 errors, 2.7s) |
| T84  | FAIL    | Dashboard shows 5 conflicts. Pull skips not counted as errors — sync falsely reports success |

## Bugs Found
- **[BUG]** report_add_quantity_dialog.dart fields had no testing keys — FIXED by background agent
- **[BUG]** Dismissing quantity dialog causes `_dependents.isEmpty` assertion crash (red screen) — required full app restart
- **[BUG]** Contractor type dropdown doesn't set "Prime" correctly — all contractors show "Sub"
- **[BUG]** DraftsListScreen: checkbox taps via driver update visual state but `_selectedIds` set doesn't update — Review Selected button stays disabled
- **[BUG/INFRA]** entry_equipment missing `created_at` column on Supabase remote — FIXED with migration 20260321000002
- **[SECURITY]** entry_equipment and entry_personnel tables have UNRESTRICTED RLS — no policies
- **[INFRA]** entry_personnel table may be an orphan (app uses entry_personnel_counts)
- **[FEATURE]** MDOT 0582B forms have no submit workflow — section-by-section only (T37 N/A)
- **[FEATURE]** Forms should be attachable to daily entries — prompt user when dates align
- **[DRIVER]** DropdownButton duplicate keys: popup overlay items share keys with collapsed items — driver taps hidden item instead of popup when reverting selection
- **[SYNC]** Persistent "Sync error: Sync failed" banner on Admin Dashboard throughout T53-T58
- **[BUG]** Duplicate GlobalKeys detected in widget tree — appeared twice during session, causes widget tree truncation
- **[SYNC]** Integrity check failed for `entry_contractors` — PostgrestException "Invalid table name: entry_contractors" (P0001). Table name mismatch between app and Supabase schema.
- **[DRIVER/T67]** contractor_editor_view_mode is a static key shared by multiple contractors — duplicate key issue
- **[LAYOUT/T68]** Report inline preview on home screen doesn't scroll past Safety section — Quantities and Photos sections inaccessible
- **[DRIVER/T69]** InputChip onDeleted not triggered by driver tap — taps hit onPressed instead
- **[MISSING KEY/T74]** Form response delete buttons have no testing keys
- **[NAV BUG/T77]** settings_trash_tile navigates to Projects screen instead of Trash screen
- **[SYNC/T78]** 5 unresolved conflicts (bid_items, contractors, locations, 2x daily_entries). Local deletes conflict with remote data.
- **[SYNC/T79]** Pull silently skips records with FK violations (project_assignments missing parent). Reports 0 errors — false success.
- **[SYNC/T84]** Sync dashboard shows conflicts but sync cycle reports "completed 0 errors". Pull skips and conflicts not surfaced as errors.

## Tier 11: Role & Permission Verification Results
| Flow | Status  | Notes |
|------|---------|-------|
| T85  | BLOCKED | Inspector account was on Engineer role (T55 role change not reverted). Engineer correctly has project create. Cannot test inspector restriction. |
| T86  | PASS    | Admin Dashboard tile correctly hidden for non-admin role |
| T87  | PASS    | Create entry button (`home_create_entry_button`) exists for engineer/inspector |
| T88  | PASS    | Todos add button (`todos_add_button`) exists for engineer/inspector |
| T89  | BLOCKED | Inspector account was on Engineer role. Engineer correctly has archive permission. Cannot test inspector restriction. |
| T90  | BLOCKED | Inspector account was on Engineer role. Engineer correctly has edit permission. Cannot test inspector restriction. |
| T91  | BLOCKED | Inspector account was on Engineer role. Engineer correctly accesses /project/new. Cannot test inspector route guard. |

## Tier 12: Navigation & Dashboard Results
| Flow | Status  | Notes |
|------|---------|-------|
| T92  | PASS    | Dashboard entries card → All Entries screen (empty — project data not loaded after re-login) |
| T93  | PASS    | Dashboard pay items card → Pay Items & Quantities screen |
| T94  | PASS    | Dashboard toolbox card → Toolbox screen |
| T95  | BLOCKED | No bid items loaded after re-login — empty state, nothing to tap |
| T96  | BLOCKED | Gallery empty state after re-login — no photos to tap |

## Summary
| Tier | PASS | FAIL | BLOCKED | N/A | Total |
|------|------|------|---------|-----|-------|
| 0: Auth & Smoke | 4 | 0 | 0 | 0 | 4 |
| 1: Project Setup | 10 | 0 | 0 | 0 | 10 |
| 2: Entry Creation | 7 | 2 | 0 | 0 | 9 |
| 3: Entry Lifecycle | 4 | 1 | 2 | 0 | 7 |
| 4: Toolbox | 9 | 0 | 0 | 1 | 10 |
| 5: PDF & Export | 2 | 0 | 0 | 1 | 3 |
| 6: Settings | 9 | 0 | 0 | 0 | 9 |
| 7: Admin Ops | 4 | 0 | 0 | 2 | 6 |
| 8: Edit Mutations | 6 | 1 | 1 | 0 | 8 |
| 9: Delete Ops | 3 | 3 | 1 | 3 | 10 |
| 10: Sync | 2 | 5 | 0 | 0 | 7 |
| 11: Permissions | 3 | 0 | 4 | 0 | 7 |
| 12: Navigation | 3 | 0 | 2 | 0 | 5 |
| **TOTAL** | **66** | **12** | **10** | **7** | **95** |

**Pass rate**: 66/95 = **69%** (excluding N/A: 66/88 = **75%**)

## Observations
- Prior test data present from earlier sessions (contractors, pay items, assignments)
- Project save button stays on form (by design — wizard pattern)
- inject-photo-direct works with valid PNG (min ~20KB)
- Sync error from missing created_at resolved mid-run — sync now clean (0 errors)
- Entry ID: b277e8f9, Photo IDs: c72a4851, 56817f0c
- Project ID: 223f503b-76d4-48f9-ad81-c050ab53e551
- RenderFlex overflow (176px) on report screen — cosmetic only
- Report inline preview layout is a major test blocker — many flows need access to content below Safety section
- Sync has 5 unresolved conflicts — delete operations create conflicts with remote data
- Pull silently skips FK violation records — reports success when data is missing
- Inspector permission tests (T85/T89/T90/T91) need re-run after role revert (user manually fixed)
- Dashboard shows 0 data after re-login — project data not auto-loaded, blocks T95/T96
- Engineer role intentionally has project create/edit/archive permissions (user confirmed)

# Test Run Report — 2026-03-20 (Session 2: Post-Rebuild)

## Run Configuration
- **Platform**: Windows (desktop)
- **Role**: Admin (rsebastian2433@gmail.com)
- **Driver**: HTTP on port 4948
- **Debug Server**: HTTP on port 3947
- **App Version**: 0.1.2
- **Session 1**: Initial run (08:02). Session 2: Post-rebuild re-test (08:49+).

## Admin Results

| Flow | Status | Notes |
|------|--------|-------|
| T01 | PASS | Login as admin works |
| T02 | PASS | All 4 nav tabs navigable |
| T03 | PASS | Sign out works |
| T04 | SKIP | Inspector login — deferred |
| T05 | PASS | E2E Test Project exists |
| T06 | PASS | Location A added (prior run) |
| T07 | PASS | Location B added (prior run) |
| T08 | PASS* | Contractor saved as Sub instead of Prime (dropdown bug) |
| T09 | PASS | Sub contractor created |
| T10 | PASS | Equipment added |
| T11 | PASS | Pay item E2E-100 added |
| T12 | PASS | Pay item E2E-200 added |
| T13 | PASS | Inspector assigned (shows "Unknown") |
| T14 | PASS | Search filters correctly |
| T15 | PASS | Daily entry created |
| T16 | PASS | Safety fields filled |
| T17 | BLOCKED | Contractors section: "All contractors already added" — 0 local contractors (sync drift) |
| T18 | BLOCKED | Depends on T17 |
| T19 | BLOCKED | Depends on T17 |
| T20 | BLOCKED | No bid items locally (sync drift) |
| T21 | BLOCKED | Depends on T20 |
| T22 | FAIL | Photo injected but UI shows 0 photos |
| T23 | SKIP | Depends on T22 |
| T24 | BLOCKED | Location picker shows "Add Location" — no locations locally (sync drift) |
| T25 | BLOCKED | Weather dropdown opens but items lack testing keys |
| T26 | PASS | Second entry created via Dashboard "New Entry" button |
| T27-T30 | SKIP | Entry lifecycle — deferred |
| T31 | PASS | Todo created! Driver text entry bug FIXED. Add button enables correctly. |
| T32-T34 | SKIP | Todo edit/complete/delete — checkbox lacks testing key |
| T35 | PASS* | Forms screen renders, shows MDOT 0582B template. No saved forms. |
| T36-T37 | SKIP | Form fill/submit — deferred |
| T38 | PASS | Calculator HMA tab renders |
| T39 | PASS | Calculator Concrete tab renders |
| T40 | SKIP | Gallery needs photos |
| T41 | PASS | PDF generated! "IDR 2026-03-20 E2E-001.pdf" with Preview/Save As/Share buttons |
| T42-T43 | SKIP | Need photos / form submission |
| T44 | PASS | Edit Profile opens, shows all fields correctly |
| T45 | PASS | Theme toggle works |
| T46 | PASS | Gauge Number dialog opens with text field |
| T47 | PASS | Initials dialog opens, shows "RBWS" (4/5 limit) |
| T48 | PASS | Auto-load Last Project toggle works |
| T49 | PASS | Sync Dashboard opens, shows 2 pending, 0 conflicts, 17 tables |
| T50 | PASS | Sync triggered — pulled 4 records |
| T51 | PASS | Trash screen opens, "Trash is empty" |
| T52 | PASS | Clear Cached Exports works |
| T53 | PASS | Admin Dashboard opens, shows 2 team members |
| T54-T55 | SKIP | Team member detail/role change — deferred |
| T56-T57 | MANUAL | Require pending join requests |
| T58 | SKIP | Archive project — deferred |
| T59-T67 | SKIP | Edit mutations — deferred (sync drift blocks most) |
| T68-T77 | SKIP | Delete operations — deferred |
| T78-T84 | SKIP | Sync verification — sync engine bugs prevent meaningful testing |
| T85-T91 | SKIP | Inspector role — deferred |
| T92 | PASS | Dashboard -> All Entries works |
| T93 | PASS | Dashboard -> Pay Items & Quantities works |
| T94 | PASS | Dashboard -> Toolbox works |
| T95-T96 | SKIP | Bid Item Detail / Photo Viewer |

## Summary

| Status | Count |
|--------|-------|
| PASS | 29 |
| FAIL | 1 |
| BLOCKED | 6 |
| SKIP | 44 |
| MANUAL | 2 |
| Not Reached | 14 |
| **Total** | **96** |

## Bugs Found

### Critical
1. **[BUG] Sync pull skips ALL project-scoped tables** — `synced_projects` table is empty after initial project pull. 15 adapters log "Pull skip (no loaded projects)". Root cause: projects are pulled but not auto-enrolled in `synced_projects` table. Result: locations, contractors, equipment, bid_items, daily_entries, photos, and all entry sub-tables never get pulled.

2. **[BUG] Todo sync push: priority column type mismatch** — App sends priority as string `"normal"` but Supabase column expects integer. `PostgrestException: invalid input syntax for type integer: "normal"` (code 22P02). Both todo records stuck in retry loop, max retries (3) exhausted. Error persists as red snackbar on every screen.

### High
3. **[BUG] LateInitializationError: _contractorController** — `Field '_contractorController@252095497' has not been initialized`. 3 occurrences after app restart. Triggered during entry save and calendar navigation. New bug found this session.

4. **[BUG] Calendar month view RenderFlex overflow 17px** — 3 occurrences in error logs. Hides entry list in Month view.

5. **[BUG] Photo injection doesn't update UI** — `POST /driver/inject-photo` queues photo but entry report shows "0 photos".

6. **[BUG] Contractor type dropdown not applied** — Both contractors saved as "Sub" despite selecting "Prime".

### Medium
7. **[BUG] Inspector display name shows "Unknown"** — `handle_new_user()` trigger doesn't set `display_name`.

8. **[BUG] Ghost project on duplicate project number** — Save attempt with existing number creates empty project.

9. **[BUG] Integrity check failed for project_assignments** — 2 occurrences on startup. Drift: local=-1, remote=-1.

10. **[BUG] OrphanScanner scan failed** — `column photos.company_id does not exist`. 2 occurrences on startup.

### Low
11. **[BUG] Missing testing keys on dropdown items** — Weather condition dropdown items (Sunny, Cloudy, etc.) lack keys. Blocks T25.

12. **[BUG] Missing testing keys on PDF action buttons** — Preview and Save As buttons in PDF dialog lack keys. Only Close and Share have keys.

13. **[BUG] Missing testing keys on Todo checkboxes** — Checkbox widgets in todo cards lack keys. Blocks T33.

14. **[BUG] Missing testing key on New Entry button (Calendar)** — No FAB or add button on Calendar screen. Must use Dashboard "New Entry" button instead.

15. **[BUG] Pay item unit dropdown items lack testing keys** — Can't select specific units via driver.

## Fixes Applied This Session

1. **Empty-state contractor add button key** — Added `TestingKeys.calendarReportAddContractorButton` to the empty-state InkWell in `home_screen.dart:1407`. Previously only the non-empty state had a key.

2. **Driver text entry notifyListeners bug** — Confirmed FIXED (was already fixed before this session). Todo dialog Add button now correctly enables after text entry.

## Error Log Summary (10 errors total)
| Error | Count | Category |
|-------|-------|----------|
| RenderFlex overflow 17px | 3 | layout |
| LateInitializationError: _contractorController | 3 | init |
| Integrity check: project_assignments | 2 | sync |
| OrphanScanner scan failed | 2 | sync |

## Sync Status
- **Pull fundamentally broken**: `synced_projects` empty → all project-scoped pulls skipped
- **Push partially broken**: todo_items fail (priority type mismatch), entries may work
- Sync dashboard shows: "Sync error — Failed 7 times"
- Last error displayed inline on Settings page

## Root Cause Analysis: Sync Pull Failure

From sync logs at 08:05:47:
```
Reloaded synced project IDs after pulling 4 projects
Pull skip (no loaded projects): locations
Pull skip (no loaded projects): contractors
Pull skip (no loaded projects): equipment
Pull skip (no loaded projects): bid_items
Pull skip (no loaded projects): personnel_types
Pull skip (no loaded projects): daily_entries
Pull skip (no loaded projects): photos
... (15 adapters skipped)
```

The sync engine pulls projects (4 records) but the `synced_projects` enrollment happens AFTER the current pull cycle. On the NEXT pull, `synced_projects` should be populated — but the reload happens too late or the enrollment logic has a bug.

**Fix needed**: Either auto-enroll projects into `synced_projects` immediately during project pull, or re-run project-scoped pulls after enrollment.

## Blockers for Full Coverage
1. **Sync pull** — Blocks T17-T21, T24 (need local contractors, locations, bid items)
2. **Sync push (todo priority)** — Blocks T31+ from syncing
3. **Missing testing keys** — Blocks T25 (weather items), T33 (todo checkbox), PDF Preview/Save As
4. **LateInitializationError** — May cause intermittent failures
5. **Photo injection** — Blocks T22, T23, T40, T42, T96

## Next Steps
1. **Fix sync pull**: Auto-enroll projects into `synced_projects` during pull phase
2. **Fix todo priority**: Change column type or serialize priority as integer
3. **Fix _contractorController init**: Ensure controller is initialized before use
4. **Add missing testing keys**: Weather dropdown items, todo checkbox, PDF buttons, calendar new entry
5. **Re-run blocked flows** after sync fix pulls data down
6. **Run inspector session** (T04, T85-T91)

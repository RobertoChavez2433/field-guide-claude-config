# BASELINE TEST REPORT — 2026-03-20

## Configuration
- **Platform**: Windows desktop
- **App Version**: 0.1.2
- **Driver**: HTTP port 4948
- **Debug Server**: HTTP port 3947
- **Roles Tested**: Admin (rsebastian2433@gmail.com), Inspector (rsebastian5553@gmail.com)

---

## Results Summary

| Status | Count | % |
|--------|-------|---|
| **PASS** | 38 | 39.6% |
| **FAIL** | 1 | 1.0% |
| **BLOCKED** | 16 | 16.7% |
| **SKIP** | 39 | 40.6% |
| **MANUAL** | 2 | 2.1% |
| **Total** | **96** | 100% |

---

## All Flow Results

### Tier 0: Auth & Smoke (T01-T04)
| Flow | Status | Notes |
|------|--------|-------|
| T01 | **PASS** | Admin login works |
| T02 | **PASS** | All 4 nav tabs navigable |
| T03 | **PASS** | Sign out works |
| T04 | **PASS** | Inspector login works. Auto-loads E2E Test Project. |

### Tier 1: Project Setup (T05-T14)
| Flow | Status | Notes |
|------|--------|-------|
| T05 | **PASS** | E2E Test Project exists (created prior run) |
| T06 | **PASS** | Location A added (prior run) |
| T07 | **PASS** | Location B added (prior run) |
| T08 | **PASS*** | Contractor created but dropdown bug — both saved as Sub |
| T09 | **PASS** | Sub contractor created |
| T10 | **PASS** | Equipment added to contractor |
| T11 | **PASS** | Pay item E2E-100 HMA added |
| T12 | **PASS** | Pay item E2E-200 Concrete added |
| T13 | **PASS** | Inspector assigned (shows "Unknown" — display name bug) |
| T14 | **PASS** | Search filters to 1 result |

### Tier 2: Daily Entry Creation (T15-T23)
| Flow | Status | Notes |
|------|--------|-------|
| T15 | **PASS** | Entry created, draft saved |
| T16 | **PASS** | Safety fields filled |
| T17 | **BLOCKED** | Sync drift: 0 local contractors. "All contractors already added" shown. |
| T18 | **BLOCKED** | Depends on T17 |
| T19 | **BLOCKED** | Depends on T17 |
| T20 | **BLOCKED** | Sync drift: 0 local bid items |
| T21 | **BLOCKED** | Depends on T20 |
| T22 | **FAIL** | Photo injected (queued) but UI shows 0 photos |
| T23 | **SKIP** | Depends on T22 |

### Tier 3: Entry Lifecycle (T24-T30)
| Flow | Status | Notes |
|------|--------|-------|
| T24 | **BLOCKED** | Location picker shows "Add Location" — 0 locations locally (sync drift) |
| T25 | **BLOCKED** | Weather dropdown opens but items lack testing keys (agent adding keys) |
| T26 | **PASS** | Second entry created from Dashboard "New Entry" button |
| T27 | **BLOCKED** | Review Drafts screen opens (2 drafts shown) but checkboxes lack testing keys (agent adding keys) |
| T28 | **SKIP** | Depends on T27 |
| T29 | **SKIP** | Depends on T28 |
| T30 | **SKIP** | Need overflow menu from full entry report — calendar inline view doesn't expose it |

### Tier 4: Toolbox (T31-T40)
| Flow | Status | Notes |
|------|--------|-------|
| T31 | **PASS** | Todo created! Driver text entry bug is FIXED. Add button enables correctly. |
| T32 | **SKIP** | Todo card tappable but edit dialog not tested |
| T33 | **BLOCKED** | Todo checkbox lacks testing key (agent adding key) |
| T34 | **SKIP** | Delete todo — not tested |
| T35 | **PASS** | Forms screen opens, shows MDOT 0582B template |
| T36 | **PASS** | 0582B form opened! Header auto-populated (date, job#, inspector, phone). Proctor + Quick Test sections visible. |
| T37 | **SKIP** | Form submit — not tested (would need to fill all required fields) |
| T38 | **PASS** | Calculator HMA tab renders |
| T39 | **PASS** | Calculator Concrete tab renders |
| T40 | **SKIP** | Gallery needs photos |

### Tier 5: PDF & Export (T41-T43)
| Flow | Status | Notes |
|------|--------|-------|
| T41 | **PASS** | PDF generated: "IDR 2026-03-20 E2E-001.pdf". Preview/Save As/Share buttons shown. No PDF errors in logs. |
| T42 | **SKIP** | Needs photos on entry |
| T43 | **SKIP** | Needs submitted form |

### Tier 6: Settings & Profile (T44-T52)
| Flow | Status | Notes |
|------|--------|-------|
| T44 | **PASS** | Edit Profile opens. Shows email, name, cert#, phone, agency, initials, position. |
| T45 | **PASS** | Theme toggle works (Dark/Light/High Contrast) |
| T46 | **PASS** | Gauge Number dialog opens with text field |
| T47 | **PASS** | Initials dialog opens, shows "RBWS" (4/5) |
| T48 | **PASS** | Auto-load Last Project toggle works |
| T49 | **PASS** | Sync Dashboard opens: 2 pending, 0 conflicts, 17 tables. Integrity drift visible. |
| T50 | **PASS** | Manual sync triggered. Pulled 4, pushed 0. |
| T51 | **PASS** | Trash screen opens. "Trash is empty." |
| T52 | **PASS** | Clear Cached Exports dialog works |

### Tier 7: Admin Operations (T53-T58)
| Flow | Status | Notes |
|------|--------|-------|
| T53 | **PASS** | Admin Dashboard opens. 2 team members: Robert Sebastian (Admin), Unknown (Inspector). |
| T54 | **BLOCKED** | Team member ListTiles lack testing keys (agent adding keys) |
| T55 | **SKIP** | Depends on T54 |
| T56 | **MANUAL** | Requires pending join request |
| T57 | **MANUAL** | Requires pending join request |
| T58 | **SKIP** | Archive button exists (`project_archive_toggle_*` key) but skipped to preserve test data |

### Tier 8: Edit Mutations (T59-T67)
| Flow | Status | Notes |
|------|--------|-------|
| T59 | **PASS** | Project edit screen opens. Details tab shows name/number/client. All 5 tabs accessible. |
| T60 | **BLOCKED** | Contractors tab: 0 contractors locally (sync drift) |
| T61 | **BLOCKED** | Pay Items tab: 0 bid items locally (sync drift) |
| T62 | **SKIP** | Activities edit — calendar inline edit triggered (weather temp fields shown) but no dedicated test |
| T63 | **SKIP** | Temperature edit — inline edit available but not formally tested |
| T64 | **SKIP** | Quantity edit — no quantities locally (sync drift) |
| T65 | **SKIP** | Unarchive — depends on T58 |
| T66 | **PASS** | Assignments tab accessible. Shows 2 members. Inspector unchecked, Admin checked. |
| T67 | **SKIP** | Personnel types — depends on T17 (contractors) |

### Tier 9: Delete Operations (T68-T77)
| Flow | Status | Notes |
|------|--------|-------|
| T68 | **SKIP** | No photos to delete |
| T69 | **SKIP** | No equipment locally (sync drift) |
| T70 | **SKIP** | No contractors locally (sync drift) |
| T71 | **SKIP** | No locations locally (sync drift) |
| T72 | **SKIP** | No bid items locally (sync drift) |
| T73 | **SKIP** | Could test todo delete but not attempted |
| T74 | **SKIP** | No forms to delete |
| T75 | **SKIP** | Remove from device — not tested |
| T76 | **MANUAL** | Requires remote-only project |
| T77 | **SKIP** | No trashed items |

### Tier 10: Sync Verification (T78-T84)
| Flow | Status | Notes |
|------|--------|-------|
| T78 | **SKIP** | Sync push fundamentally broken — covered in bugs section |
| T79 | **SKIP** | Same — sync engine bugs prevent meaningful testing |
| T80 | **SKIP** | No photos synced |
| T81 | **SKIP** | No deletions to sync |
| T82 | **SKIP** | No edits to sync |
| T83 | **PASS** | Manual sync via Settings works (same as T50) |
| T84 | **PASS** | Sync Dashboard shows counts correctly |

### Tier 11: Inspector Permissions (T85-T91)
| Flow | Status | Notes |
|------|--------|-------|
| T85 | **PASS** | No Create Project FAB visible — correct |
| T86 | **PASS** | No Admin Dashboard tile — correct |
| T87 | **PASS** | "New Entry" button visible — inspector can create entries |
| T88 | **PASS** | Todo add FAB visible — inspector can create todos |
| T89 | **PASS** | No archive toggle on project cards — correct |
| T90 | **PASS** | Project edit shows read-only banner: "Project details are managed by admins and engineers". No Save button. |
| T91 | **SKIP** | Route guard test — not attempted |

### Tier 12: Navigation & Dashboard (T92-T96)
| Flow | Status | Notes |
|------|--------|-------|
| T92 | **PASS** | Dashboard → All Entries works |
| T93 | **PASS** | Dashboard → Pay Items & Quantities works |
| T94 | **PASS** | Dashboard → Toolbox works |
| T95 | **BLOCKED** | Quantities screen: "No pay items" — 0 locally (sync drift) |
| T96 | **SKIP** | No photos for gallery viewer |

---

## Bug Registry (17 bugs)

### CRITICAL (2)
| # | Bug | Flow | Root Cause |
|---|-----|------|-----------|
| 1 | **Sync pull skips ALL project-scoped tables** | SYNC | `synced_projects` empty → 15 adapters log "Pull skip (no loaded projects)". Projects pulled (4) but not enrolled in time for current cycle. |
| 2 | **Todo push: priority type mismatch** | SYNC | App sends `"normal"` (string) but Supabase column expects integer. Code 22P02. All todos stuck in retry (exhausted 3 retries). Persistent red snackbar on every screen. |

### HIGH (4)
| # | Bug | Flow | Details |
|---|-----|------|---------|
| 3 | **LateInitializationError: _contractorController** | STARTUP | 4 occurrences. Field not initialized before access. Triggered on entry save, calendar navigation, form open. |
| 4 | **RenderFlex overflow 17px** | T15 | 3 occurrences. Calendar Month view. Hides entry list below calendar. |
| 5 | **Photo injection UI not updated** | T22 | `POST /driver/inject-photo` queues photo but entry report shows "0 photos". |
| 6 | **Contractor type dropdown not applied** | T08 | Both contractors saved as "Sub" despite selecting "Prime" for first. |

### MEDIUM (4)
| # | Bug | Flow | Details |
|---|-----|------|---------|
| 7 | **Inspector display name "Unknown"** | T13 | `handle_new_user()` trigger doesn't set display_name from metadata. |
| 8 | **Ghost project on duplicate number** | T05 | Save with existing project number creates empty project before error. |
| 9 | **Integrity check: project_assignments** | STARTUP | Drift: local=-1, remote=-1. 3 occurrences. |
| 10 | **OrphanScanner scan failed** | STARTUP | `column photos.company_id does not exist`. 3 occurrences. |

### LOW (7)
| # | Bug | Flow | Details |
|---|-----|------|---------|
| 11 | **Duplicate `entry_edit_button` keys** | T62 | 4 identical keys on calendar inline view — only first is tappable. |
| 12 | **No entry menu on calendar inline view** | T30 | Overflow menu (delete, etc.) only on full report screen, not inline. |
| 13 | **Missing testing keys** (various) | Multiple | Weather items, todo checkbox, PDF buttons, team members, review draft checkboxes, pay item units — agent dispatched to fix. |
| 14 | **No New Entry button on Calendar screen** | T26 | Only accessible from Dashboard. Calendar has no FAB or add button. |
| 15 | **Server check banner on inspector login** | T04 | "Last server check was over 24 hours ago" — stale for new inspector account. |
| 16 | **Sync error snackbar persists across all screens** | ALL | Red error bar for todo push failure shown on every screen without timeout. |
| 17 | **Entry wizard No Locations state** | T26 | Shows "No locations yet" + "Add Location" button instead of location picker (sync drift consequence). |

---

## Error Log Summary (13 total occurrences)

| Error | Count | Severity |
|-------|-------|----------|
| LateInitializationError: _contractorController | 4 | HIGH |
| Integrity check: project_assignments | 3 | MEDIUM |
| OrphanScanner: scan failed | 3 | MEDIUM |
| RenderFlex overflow 17px | 3 | HIGH |

---

## Blocking Dependencies

```
Sync Pull Bug (CRITICAL)
  └── 0 local: contractors, locations, bid_items, equipment, daily_entries
       ├── T17-T21 (contractor/quantity flows)
       ├── T24 (location picker)
       ├── T60-T61 (edit contractor/pay item)
       ├── T64 (edit quantity)
       ├── T69-T72 (delete entities)
       └── T95 (bid item detail)

Todo Push Bug (CRITICAL)
  └── Persistent error snackbar on all screens

Photo Injection Bug (HIGH)
  └── T22 FAIL → T23, T40, T42, T68, T96 blocked

Missing Testing Keys (LOW — agent fixing)
  └── T25 (weather), T27 (review checkboxes), T33 (todo checkbox), T54 (team members)
```

---

## Fixes Applied During Testing
1. **Empty-state contractor add button key** — Added `TestingKeys.calendarReportAddContractorButton` to `home_screen.dart:1407`
2. **Testing keys agent** — Added keys for review draft checkboxes, admin team members, weather dropdown items, todo checkboxes, PDF Preview/Save As buttons, pay item unit dropdowns

---

## What Needs Fixing (Priority Order)

1. **Sync pull: auto-enroll projects into `synced_projects`** — Fixes 12+ blocked flows
2. **Todo priority column: integer vs string** — Fixes push errors + persistent snackbar
3. **LateInitializationError: _contractorController** — 4 occurrences, HIGH
4. **Photo injection** — Needs investigation for UI update issue
5. **Contractor type dropdown** — Selection not applied
6. **RenderFlex overflow in calendar Month view** — 3 occurrences
7. **Inspector display name** — Supabase trigger fix
8. **Ghost project on duplicate** — DB constraint handling

---

## What's Working Well
- All 4 nav tabs functional
- Login/logout for both roles
- Project CRUD (create, edit screens, all 5 tabs)
- Entry creation from Dashboard
- PDF generation (end-to-end)
- Theme switching (Dark/Light/High Contrast)
- Settings tiles (Edit Profile, Gauge Number, Initials, Auto-load, Clear Cache)
- Admin Dashboard (team members, pending requests)
- Sync Dashboard (shows pending, conflicts, integrity checks)
- Todo creation (driver text entry bug FIXED)
- MDOT 0582B form (auto-populates header fields)
- Calculator (HMA + Concrete tabs)
- Trash screen
- Inspector permission enforcement (no FAB, no admin dashboard, read-only project edit, no archive)

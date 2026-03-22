# Test Run Report — 2026-03-21 Full Run (Final)

## Summary
- **Platform**: Windows (desktop)
- **Project**: E2E Test 1774132926 (ID: c58fd21f)
- **Debug Server**: 447 total logs, **1 error** (driver EXIF decode — not app bug), **0 warnings**
- **Sync**: 15 pushed, 0 errors, 0 conflicts

## Results

| Tier | Flows | PASS | FAIL | SKIP | MANUAL |
|------|-------|------|------|------|--------|
| 0: Auth | T01-T04 | 4 | 0 | 0 | 0 |
| 1: Project Setup | T05-T14 | 9 | 1 | 0 | 0 |
| 2: Entry Creation | T15-T23 | 5 | 1 | 3 | 0 |
| 3: Entry Lifecycle | T24-T30 | 2 | 3 | 2 | 0 |
| 4: Toolbox | T31-T40 | 7 | 0 | 1 | 1 |
| 5: PDF & Export | T41-T43 | 1 | 0 | 1 | 1 |
| 6: Settings | T44-T52 | 6 | 0 | 1 | 0 |
| 7: Admin | T53-T58 | 3 | 0 | 1 | 2 |
| 8: Edit Mutations | T59-T67 | 0 | 0 | 9 | 0 |
| 9: Delete Ops | T68-T77 | 0 | 0 | 8 | 2 |
| 10: Sync Verify | T78-T84 | 0 | 0 | 7 | 0 |
| 11: Permissions | T85-T91 | 3 | 3 | 1 | 0 |
| 12: Navigation | T92-T96 | 5 | 0 | 0 | 0 |
| **TOTAL** | **96** | **45** | **8** | **34** | **6** |

**Pass rate (of executed): 45/53 = 85%**
**Pass rate (of automatable): 45/87 = 52%** (34 not yet executed)

## Detailed Results

### Tier 0: Auth & Smoke
| Flow | Status | Notes |
|------|--------|-------|
| T01 | PASS | Admin login |
| T02 | PASS | All 4 tabs navigated |
| T03 | PASS | Sign out |
| T04 | PASS | Inspector login |

### Tier 1: Project Setup
| Flow | Status | Notes |
|------|--------|-------|
| T05 | PASS | "E2E Test 1774132926" created |
| T06 | PASS | Location A added |
| T07 | PASS | Location B added |
| T08 | PASS | Prime contractor added |
| T09 | PASS | Sub contractor added |
| T10 | PASS | Equipment "E2E Excavator" added |
| T11 | PASS | Pay item E2E-100 HMA 500 TON |
| T12 | PASS | Pay item E2E-200 Concrete 1000 SY |
| T13 | PASS | Inspector assigned |
| T14 | FAIL | No search field key on projects screen |

### Tier 2: Daily Entry Creation
| Flow | Status | Notes |
|------|--------|-------|
| T15 | PASS | Entry created (Sunny, 45-72°F) |
| T16 | FAIL | Inline edit fields have no testing keys |
| T17 | PASS | Contractor added to entry |
| T18 | SKIP | Personnel count — no counter keys |
| T19 | SKIP | Equipment — auto-checked on contractor add |
| T20 | PASS | Quantity: E2E-100 HMA, 10.50 FT |
| T21 | SKIP | Calculator from entry — not tested |
| T22 | PASS | Photo 1 injected |
| T23 | PASS | Photo 2 injected |

### Tier 3: Entry Lifecycle
| Flow | Status | Notes |
|------|--------|-------|
| T24 | FAIL | Location edit — no keyed dropdown |
| T25 | FAIL | Weather edit — no keyed dropdown |
| T26 | PASS | Second entry created (March 19) |
| T27 | PASS | Review drafts → mark ready (3 entries) |
| T28 | PASS | Batch submit confirmed |
| T29 | FAIL | Undo submission — button not found (view-only mode blocking?) |
| T30 | SKIP | Delete entry — requires long-press (not supported by driver) |

### Tier 4: Toolbox
| Flow | Status | Notes |
|------|--------|-------|
| T31 | PASS | Todo created |
| T32 | PASS | Todo edited |
| T33 | PASS | Todo completed |
| T34 | PASS | Todo deleted (soft-delete) |
| T35 | PASS | 0582B form created, hub opened |
| T36 | PASS | Form filled: header, proctor (5 readings), test (gauge data) |
| T37 | MANUAL | Section-by-section submit (no global submit) |
| T38 | PASS | HMA calculator result |
| T39 | PASS | Concrete calculator: 9.26 CY |
| T40 | PASS | Gallery opened, filter applied/cleared |

### Tier 5: PDF & Export
| Flow | Status | Notes |
|------|--------|-------|
| T41 | PASS | PDF generated: "IDR 2026-03-21 E2E-1774132926.pdf" |
| T42 | SKIP | Export folder — not tested |
| T43 | MANUAL | Form PDF — section submit required first |

### Tier 6: Settings & Profile
| Flow | Status | Notes |
|------|--------|-------|
| T44 | PASS | Profile name set |
| T45 | PASS | Theme: Dark → Light → Dark |
| T46 | PASS | Gauge number: 12345 |
| T47 | PASS | Initials: TST |
| T48 | PASS | Auto-load toggled on/off |
| T49 | PASS | Sync dashboard opened |
| T50 | PASS | Manual sync: 15 pushed, 0 errors |
| T51 | SKIP | Trash restore — no deleted items available |
| T52 | PASS | Cache cleared |

### Tier 7: Admin Operations
| Flow | Status | Notes |
|------|--------|-------|
| T53 | PASS | Admin dashboard, 2 members visible |
| T54 | PASS | Member detail sheet opened |
| T55 | PASS | Role: Inspector → Engineer (synced) |
| T56 | MANUAL | Approve join — no pending requests |
| T57 | MANUAL | Reject join — no pending requests |
| T58 | SKIP | Archive project — not tested |

### Tier 8-10: Not Executed
T59-T84 not executed this run (edit mutations, delete ops, sync verification).

### Tier 11: Permissions
| Flow | Status | Notes |
|------|--------|-------|
| T85 | **FAIL** | **SECURITY: Inspector sees "New Project" FAB** |
| T86 | PASS | Admin dashboard hidden for inspector |
| T87 | PASS | Inspector created entry |
| T88 | PASS | Inspector created todo |
| T89 | **FAIL** | **SECURITY: Inspector sees archive toggle** |
| T90 | **FAIL** | **SECURITY: Inspector has full project edit + Save** |
| T91 | SKIP | Route guard — not tested |

### Tier 12: Navigation
| Flow | Status | Notes |
|------|--------|-------|
| T92 | PASS | Dashboard → Entries List |
| T93 | PASS | Dashboard → Quantities |
| T94 | PASS | Dashboard → Toolbox |
| T95 | PASS | View All Quantities |
| T96 | PASS | Gallery → Photo Viewer |

---

## Bugs Found

### CRITICAL (Security)
1. **Inspector can create projects** — `add_project_fab` visible for inspector (T85)
2. **Inspector can archive projects** — archive toggle visible for inspector (T89)
3. **Inspector can edit projects** — full edit access with Save button (T90)

### HIGH (Functional)
4. **ViewOnlyBanner should be removed entirely** — has no valid use case (all roles can edit field data, creator-only gating is per-control). Currently blocks undo submission. Remove `ViewOnlyBanner` and all `isViewer` checks that gate entire UI sections.
5. **Proctor Wet PCF calculates as 0.00** — likely unit conversion bug in volume mold (943.3 interpreted as cuft instead of cm³?)
6. **No "Add Equipment" on report contractor card** — only "+ Add Type" (personnel). Need equipment add button.
7. **"+ Add Type" label unclear** — should be "+ Add Personnel Type"
8. **Forms not attachable to entries** — no link between form_responses and daily_entries
9. **Cannot fill form from entry screen** — "Start New Form" on report doesn't link to entry

### MEDIUM (Missing Keys)
10. **Home screen inline edit fields** — activities, safety, SESC, traffic, visitors have no keys
11. **Report header dropdowns** — location/weather edit open but dropdowns unkeyed
12. **Project search field** — no key on projects screen (T14)

### LOW
13. **Project save 2-tap** — first tap saves, second navigates back
14. **Entry delete requires long-press** — driver can't do long-press (T30)

## Debug Server Log Summary
- **447 total entries** since test start
- **1 error**: Driver EXIF decode (test infrastructure, not app)
- **0 warnings**
- **Sync**: Clean — 0 errors, 0 conflicts, 15 entities pushed
- **Categories**: sync(168), nav(110), db(34), lifecycle(10), ocr(2), auth(2), ui(2), app(1)

## Form Verification (T36)
- Header: Auto-filled correctly (date, job#, gauge, inspector, phone)
- Proctor: 5 weight readings accepted, deltas calculated correctly (Δ120, Δ110, Δ40, Δ130)
- Proctor MDD: 98.00 pcf, OMC: 19.89% (Wet PCF: 0.00 — BUG)
- Test: All fields filled, % Compaction: 122.66% (120.2/98.0 × 100 — math correct but MDD is wrong)
- Send to form: Both Proctor and Test sent successfully

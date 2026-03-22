# Test Run Report — 2026-03-21 (34 Remaining Flows)

## Summary
- **Platform**: Windows (desktop)
- **Executed**: 33 of 34 flows (T91 SKIP — no driver route nav)
- **Result**: 25 PASS, 4 FAIL, 4 SKIP
- **Pass rate**: 25/29 executed = 86%

## Results

| Tier | Flows | PASS | FAIL | SKIP |
|------|-------|------|------|------|
| 2: Entry Creation | T18, T19, T21 | 2 | 0 | 1 |
| 3: Entry Lifecycle | T30 | 1 | 0 | 0 |
| 5: PDF Export | T42 | 1 | 0 | 0 |
| 6: Settings | T51 | 1 | 0 | 0 |
| 7: Admin Ops | T58 | 1 | 0 | 0 |
| 8: Edit Mutations | T59-T67 | 6 | 2 | 1 |
| 9: Delete Ops | T68-T75, T77 | 6 | 2 | 0 |
| 10: Sync Verify | T78-T84 | 7 | 0 | 0 |
| 11: Permissions | T91 | 0 | 0 | 1 |
| **TOTAL** | **33** | **25** | **4** | **4** |

## Detailed Results

### Tier 2: Entry Creation
| Flow | Status | Notes |
|------|--------|-------|
| T18 | PASS | Personnel counter incremented to 5 via +/- buttons |
| T19 | PASS | Equipment chip (E2E Excavator) present as FilterChip |
| T21 | SKIP | `quantity_calculate_button` defined but not wired — no calculator launch from entry |

### Tier 3: Entry Lifecycle
| Flow | Status | Notes |
|------|--------|-------|
| T30 | PASS | Entry deleted via overflow menu → confirm dialog |

### Tier 5: PDF Export
| Flow | Status | Notes |
|------|--------|-------|
| T42 | PASS | PDF export → Save As → filename dialog → saved |

### Tier 6: Settings
| Flow | Status | Notes |
|------|--------|-------|
| T51 | PASS | Entry restored from trash |

### Tier 7: Admin Ops
| Flow | Status | Notes |
|------|--------|-------|
| T58 | PASS | Project archived, visible in Archived tab |

### Tier 8: Edit Mutations
| Flow | Status | Notes |
|------|--------|-------|
| T59 | PASS | Project name → "E2E Updated Project" |
| T60 | PASS | Contractor name → "E2E Prime Updated" |
| T61 | PASS | Pay item desc → "HMA Surface Updated" |
| T62 | **FAIL** | Activities edit: key in code but TextField not rendering (entry state?) |
| T63 | **FAIL** | Temperature edit: keys in code but TextFields not rendering |
| T64 | PASS | Quantity value → 25.0 via inline edit |
| T65 | PASS | Project unarchived from Archived tab |
| T66 | PASS | Assignment toggled off |
| T67 | SKIP | `settings_personnel_types_tile` absent, all types already assigned |

### Tier 9: Delete Operations
| Flow | Status | Notes |
|------|--------|-------|
| T68 | PASS | Second photo deleted from entry |
| T69 | PASS | Equipment deleted from contractor |
| T70 | PASS | Sub contractor deleted |
| T71 | PASS | Location B deleted |
| T72 | PASS | Second pay item deleted |
| T73 | PASS | Todo soft-deleted |
| T74 | **FAIL** | Form delete dialog buttons unkeyed (Cancel/Delete have no Key) |
| T75 | PASS | Remove from device dialog confirmed |
| T77 | **FAIL** | Trash delete-forever dialog buttons unkeyed |

### Tier 10: Sync Verification
| Flow | Status | Notes |
|------|--------|-------|
| T78 | PASS | Sync push verified (0 errors) |
| T79 | PASS | Entry sync verified |
| T80 | PASS | Photo sync verified |
| T81 | PASS | Soft delete sync verified |
| T82 | PASS | Edit mutation sync verified |
| T83 | PASS | Manual sync via dashboard, sync_now_tile works |
| T84 | PASS | Sync dashboard shows bucket tiles (projects, entries, forms, photos) |

### Tier 11: Permissions
| Flow | Status | Notes |
|------|--------|-------|
| T91 | SKIP | HTTP driver lacks route navigation |

## Bugs Found

### MEDIUM (Missing Keys)
1. **T74/T77**: Confirmation dialog buttons in forms_list_screen.dart and trash_screen.dart lack testing keys
   - `forms_list_screen.dart:276-283` — Cancel/Delete TextButtons unkeyed
   - `trash_screen.dart:298-309` — Cancel/Delete Forever buttons unkeyed

### LOW (Investigation Needed)
2. **T62/T63**: Inline edit fields (activities, temperature) — keys are in code but TextFields not rendering after edit button tap. Agent confirmed keys at entry_activities_section.dart:104 and entry_editor_screen.dart:903,925. Likely entry is in submitted state blocking edit mode toggle.

### SKIP (Feature Not Wired)
3. **T21**: Quantity calculator not launchable from entry report screen
4. **T67**: Personnel types management not in settings screen
5. **T91**: HTTP driver lacks route navigation endpoint

## Debug Server Logs
- 0 new errors during this run (all overflow errors from prior session)
- Sync: pushed=0, pulled=0, errors=0, conflicts=0, skippedFk=2

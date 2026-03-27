# 0582B Naming/HMA Mode Fixes + IDR Template Replacement

**Date:** 2026-03-26
**Status:** Approved
**Size:** M (multiple files, UI + calculator + PDF changes)

---

## Overview

### Purpose
Fix the MDOT 0582B density form to match the real paper form's naming conventions, add an HMA/Soil mode toggle, fix unit issues, and replace the IDR template with the original untouched copy.

### Scope
**Included:**
- Rename all 0582B field labels to match the actual form (column letters + full names)
- Add HMA/Soil mode toggle to the proctor section
- Fix Volume Mold units from cm³ to cu. ft.
- Replace IDR PDF template with original source-of-truth copy
- Wire up IDR debug PDF generation for field mapping verification

**Excluded:**
- IDR field mapping corrections (follow-up after debug PDF review)
- Any changes to the 0582B PDF template itself
- Page 2 density requirements table (future feature)

### Success Criteria
- [ ] Every field label in the proctor section includes its 0582B column letter (A–J) and full name
- [ ] Every field label in the quick test section includes its 0582B column number (1–16) and full name
- [ ] HMA mode toggle lets inspector enter Gmm OR Max Density PCF directly, hiding all soil-specific fields
- [ ] Soil mode works identically to current flow (20/10 weights → one-point calc)
- [ ] Volume Mold accepts cu. ft. input directly with no auto-conversion
- [ ] IDR exports use the original `IDR 2019-XX-XX Initials.pdf` template unchanged
- [ ] Debug PDF can be generated from the new IDR template for field mapping review

---

## Task 1: 0582B Field Label Renaming

### Proctor Section Labels (hub_proctor_content.dart)

| Current Label | New Label | 0582B Column |
|---|---|---|
| `Moisture %` | `(B) Moisture %` | B |
| `Vol Mold (cm³)` | `(C) Volume Mold Cu. Ft.` | C |
| `Mold (g)` | `(E) Mold (g)` | E |
| `MDD` (live card) | `(I) Max Density PCF` | I |
| `OMC` (live card) | `(J) Optimum Moisture %` | J |
| `Wet Soil` (calc) | `(F) Wet Soil (g)` | F |
| `Wet Soil (lbs)` (calc) | `(G) Wet Soil (lbs)` | G |
| `Wet PCF` (calc) | `(H) Compacted Soil Wet PCF` | H |

Also update:
- `lastSentProctor` banner: `MDD` → `(I) Max Density`, `OMC` → `(J) Opt. Moisture`
- Collapsed summary tiles: `MDD` → `Max Density`, `OMC` → `Opt. Moisture`
- Live card text: `LIVE   MDD $maxDensity  OMC $optimum%` → `LIVE  (I) $maxDensity PCF  (J) $optimum%`

### Quick Test Section Labels (hub_quick_test_content.dart)

| Current Label | New Label | 0582B Column |
|---|---|---|
| `Orig/Recheck` | `(1) Original / (2) Recheck` | 1, 2 |
| `Depth (in)` | `(3) Test Depth (in)` | 3 |
| `Counts MC` | `(4) Counts MC` | 4 |
| `Counts DC` | `(5) Counts DC` | 5 |
| `Dry Density` | `(6) Dry Density PCF` | 6 |
| `Wet Density` | `(7) Wet Density PCF` | 7 |
| `Moisture PCF` | `(8) Moisture PCF` | 8 |
| `Moisture %` | `(9) Moisture %` | 9 |
| `Max Density (P#1)` | `(10) Max Density PCF` | 10 |
| `% Compaction` | `(11) % Compaction` | 11 |
| `Station` | `(12) Station` | 12 |
| `Left (ft)` | `(13) Left (ft)` | 13 |
| `Right (ft)` | `(14) Right (ft)` | 14 |
| `Below Grade (ft)` | `(15) Depth Below Grade (ft)` | 15 |
| `Item of Work` dropdown | `(16) Item of Work` | 16 |

Also update:
- `Using Proctor #N · MDD $maxDensity` → `Using Proctor #N · (I) Max Density $maxDensity PCF`
- Summary tiles: `Dry` → `(6) Dry`, `Wet` → `(7) Wet`, `Comp%` → `(11) Comp%`

### Files Changed
- `lib/features/forms/presentation/widgets/hub_proctor_content.dart` — all proctor labels
- `lib/features/forms/presentation/widgets/hub_quick_test_content.dart` — all test labels
- `lib/features/forms/presentation/screens/mdot_hub_screen.dart` — summary tiles, banner text

---

## Task 2: HMA/Soil Mode Toggle

### UI Design

A `SegmentedButton` or `ToggleButtons` at the top of the proctor section, above the SETUP row:

```
[ SOIL ] [ HMA ]
```

Default: **Soil** (matches current behavior).

### Soil Mode (current flow, unchanged)
Shows all existing fields:
- (B) Moisture %, (C) Volume Mold Cu. Ft., (E) Mold (g)
- 20/10 WEIGHTS section
- CALCULATED section (F, G, H, I, J)
- SEND button

### HMA Mode
Shows only:
- **Gmm input field** — labeled `Gmm (from JMF)`, optional
- **Max Density PCF input field** — labeled `(I) Max Density PCF`, optional
- When Gmm is entered: auto-calculates Max Density = `Gmm × 62.4` and fills the Max Density field
- When Max Density is entered directly: uses that value as-is
- Only one needs to be filled — Gmm takes precedence if both present
- Helper text below Gmm field: `TMD = Gmm × 62.4 (see JMF form 1911)`
- No Optimum Moisture % for HMA
- SEND button (enabled when Max Density has a value)

### Hidden in HMA Mode
- (B) Moisture % field
- (C) Volume Mold field
- (E) Mold (g) field
- 20/10 WEIGHTS section (all weight readings)
- Confirm/Edit Weights buttons
- CALCULATED section (F, G, H columns)
- LIVE card shows only `(I) Max Density PCF` (no (J) Optimum Moisture)

### Data Flow — HMA Mode Send
When sending a proctor row in HMA mode:
```dart
{
  'test_number': _proctorNo,
  'proctor_number': _proctorNo,
  'mode': 'hma',
  'gmm': gmmValue,  // if entered
  'max_density_pcf': maxDensityPcf,  // Gmm × 62.4 or direct entry
  // All other proctor fields omitted or empty
}
```

### State Management
- New state field in `_MdotHubScreenState`: `String _proctorMode = 'soil';` (values: `'soil'`, `'hma'`)
- New controllers: `_hmaGmm = TextEditingController()`, `_hmaMaxDensity = TextEditingController()`
- `_canSendProctor` logic branches on mode:
  - Soil: current logic (weights confirmed, all 3 setup fields, valid one-point calc)
  - HMA: `_hmaMaxDensity.text.trim().isNotEmpty`
- Draft save/restore includes `proctor_mode` and HMA field values
- HMA Gmm `onChanged` auto-calculates: `double gmm = parse(text); _hmaMaxDensity.text = (gmm * 62.4).toStringAsFixed(2);`

### Widget Changes
- `HubProctorContent` gets new parameters: `proctorMode`, `onModeChanged`, `gmmController`, `hmaMaxDensityController`, `onGmmChanged`
- Mode toggle rendered at top of widget, before SETUP section
- Conditional rendering based on mode

### Files Changed
- `lib/features/forms/presentation/widgets/hub_proctor_content.dart` — mode toggle + conditional rendering
- `lib/features/forms/presentation/screens/mdot_hub_screen.dart` — new state, controllers, mode-aware send logic, draft persistence
- `lib/features/forms/presentation/providers/inspector_form_provider.dart` — accept mode field in proctor row

---

## Task 3: Volume Mold Units Fix

### Current Behavior
- UI label: `Vol Mold (cm³)`
- Input: cm³ (e.g., `943.3`)
- Calculator auto-converts: if value > 1.0, divides by 28,316.846
- Stored as: `volume_mold_cuft`

### New Behavior
- UI label: `(C) Volume Mold Cu. Ft.`
- Input: cu. ft. directly (e.g., `0.0333`)
- **Remove auto-conversion** in `mdot_0582b_calculator.dart:80-84`
- Pass value straight through to calculation
- Stored as: `volume_mold_cuft` (no key change needed)

### Files Changed
- `lib/features/forms/data/services/mdot_0582b_calculator.dart:80-84` — remove cm³→ft³ auto-conversion
- `lib/features/forms/presentation/widgets/hub_proctor_content.dart:156` — label change (covered in Task 1)

---

## Task 4: IDR Template Replacement

### Steps
1. Copy `C:\Users\rseba\Downloads\IDR 2019-XX-XX Initials.pdf` to `assets/templates/idr_template.pdf` (overwrite)
2. The file is the **source of truth** — never modify it
3. Verify `pubspec.yaml` still references `assets/templates/idr_template.pdf`

### Debug PDF Generation
Wire up the existing `PdfService.generateDebugPdf()` method to be accessible from the UI:
- The method already exists at `lib/features/pdf/services/pdf_service.dart:640`
- The dialog already exists at `lib/features/entries/presentation/screens/report_widgets/report_debug_pdf_actions_dialog.dart`
- The testing key `reportDebugPdfMenuItem` already exists
- **Missing piece**: Add a `PopupMenuItem` in the entry editor overflow menu (`entry_editor_screen.dart`) that calls `generateDebugPdf()` and shows the dialog

### Files Changed
- `assets/templates/idr_template.pdf` — replaced with original
- `lib/features/entries/presentation/screens/entry_editor_screen.dart` — add debug PDF menu item

---

## Edge Cases

| Scenario | Handling |
|---|---|
| Switch from HMA→Soil mid-entry | Clear HMA fields, show soil fields, recalc from scratch |
| Switch from Soil→HMA mid-entry | Clear soil fields, show HMA fields, weight readings preserved in state but hidden |
| Gmm entered then cleared | Max Density field cleared too (if it was auto-calculated) |
| Both Gmm and direct Max Density entered | Gmm takes precedence, recalculates Max Density |
| Existing saved drafts | No migration needed — app never used cm³ values. Volume was always stored as cu. ft. |
| IDR template has different field names than expected | Debug PDF will reveal this — mapping fixes are a separate follow-up task |

---

## Testing Strategy

### Unit Tests
| Component | Test Focus | Priority |
|---|---|---|
| `Mdot0582BCalculator.calculateProctorChain()` | Verify no auto-conversion when value < 1.0 | HIGH |
| HMA max density calc | `Gmm × 62.4` produces correct TMD | HIGH |

### Widget Tests
| Widget | Test Focus | Priority |
|---|---|---|
| `HubProctorContent` | Mode toggle shows/hides correct fields | HIGH |
| `HubProctorContent` | HMA mode Gmm auto-calc populates Max Density | HIGH |
| `HubQuickTestContent` | Column number labels render correctly | MED |

### Manual Verification
- [ ] All field labels match the debug PDF column letters
- [ ] HMA mode hides soil fields, shows Gmm + Max Density
- [ ] Soil mode unchanged from current behavior
- [ ] Vol Mold accepts cu. ft. (e.g., 0.0333), no auto-conversion
- [ ] IDR debug PDF generates with field names visible
- [ ] IDR exports use the new template with correct formatting

---

## Migration/Cleanup

### Dead Code
- Remove `_cubicCmPerCubicFt` constant from calculator (no longer needed after removing auto-conversion)
- Remove the cm³→ft³ conversion block (lines 80-84 of calculator)

### No Schema Changes
- All data keys remain the same (`volume_mold_cuft`, `max_density_pcf`, `optimum_moisture_pct`)
- New keys added to proctor row: `mode` (string), `gmm` (string, optional)
- No database migration needed — these are JSON fields within `response_data`

# Dependency Graph: 0582B Fixes + IDR Template Replacement

## Direct Changes

### 1. hub_proctor_content.dart (PRESENTATION)
- **File:** `lib/features/forms/presentation/widgets/hub_proctor_content.dart`
- **Change type:** MODIFY — rename labels, add HMA/Soil mode toggle, conditional rendering
- **Key symbols:**
  - `HubProctorContent` class (line 5) — add new params: `proctorMode`, `onModeChanged`, `gmmController`, `hmaMaxDensityController`, `onGmmChanged`
  - `build()` (line 44) — add SegmentedButton, conditional soil/hma rendering
  - `_setupField()` (line 311) — label changes only
  - `_calcPair()` (line 411) — label changes
  - `_formatted()` (line 454) — no change
- **Current constructor params (line 5-41):** proctorNumber, moistureController, volumeController, moldController, weightReadings, calcResult, finalReadingNumber, finalWeightText, lastSentProctor, weightsConfirmed, canSend, onAddReading, onConfirmWeights, onEditWeights, onSend, onChanged

### 2. hub_quick_test_content.dart (PRESENTATION)
- **File:** `lib/features/forms/presentation/widgets/hub_quick_test_content.dart`
- **Change type:** MODIFY — rename labels only
- **Key symbols:**
  - `HubQuickTestContent` class (line 6) — no param changes
  - `build()` (line 43) — update label strings
  - `_row()` (line 190) — no change
  - `_field()` (line 200) — label param changes at call sites
  - `_calcField()` (line 213) — label param changes at call sites

### 3. mdot_hub_screen.dart (PRESENTATION)
- **File:** `lib/features/forms/presentation/screens/mdot_hub_screen.dart`
- **Change type:** MODIFY — new state fields, controllers, mode-aware logic, label changes
- **Key symbols:**
  - `_MdotHubScreenState` (line 27) — add `_proctorMode`, `_hmaGmm`, `_hmaMaxDensity` controllers
  - `_canSendProctor` (line 285-293) — branch on mode
  - `_sendProctor()` (line 407-467) — branch on mode for row data
  - `_draft()` (line 355-369) — include proctor_mode + HMA fields
  - `_hydrate()` (line 150-233) — restore proctor_mode + HMA fields
  - `_recalcProctor()` (line 309-318) — skip for HMA mode
  - Summary tiles (lines 766-784) — rename MDD/OMC labels
  - HubProctorContent instantiation (lines 785-805) — pass new params

### 4. mdot_0582b_calculator.dart (DATA/SERVICE)
- **File:** `lib/features/forms/data/services/mdot_0582b_calculator.dart`
- **Change type:** MODIFY — remove cm³→ft³ auto-conversion, remove `_cubicCmPerCubicFt` constant
- **Key symbols:**
  - `_cubicCmPerCubicFt` constant (line 11) — DELETE
  - `calculateProctorChain()` (lines 74-112) — remove lines 80-84 (auto-conversion block)
  - Pass `volumeMoldCuft` directly to `_calculateCompactedWetPcf()`

### 5. inspector_form_provider.dart (PRESENTATION/PROVIDER)
- **File:** `lib/features/forms/presentation/providers/inspector_form_provider.dart`
- **Change type:** MODIFY — accept `mode` and `gmm` fields in proctor row (minor)
- **Key symbol:**
  - `appendMdot0582bProctorRow()` (line 354-381) — for HMA mode, skip weight normalization when `row['mode'] == 'hma'`

### 6. idr_template.pdf (ASSET)
- **File:** `assets/templates/idr_template.pdf`
- **Change type:** REPLACE — overwrite with original source-of-truth PDF
- **Source:** `C:\Users\rseba\Downloads\IDR 2019-XX-XX Initials.pdf`

### 7. entry_editor_screen.dart (PRESENTATION)
- **File:** `lib/features/entries/presentation/screens/entry_editor_screen.dart`
- **Change type:** MODIFY — add debug PDF PopupMenuItem to overflow menu
- **Key area:** Lines 755-776 (PopupMenuButton itemBuilder)
- **Imports needed:** `report_debug_pdf_actions_dialog.dart` — ALREADY exported via `report_widgets.dart` barrel (line 30)
- **PdfService already available:** imported via `services.dart` barrel (line 26)

## Dependent Files (consumers — 2 levels)

| File | Relationship | Impact |
|------|-------------|--------|
| `lib/features/forms/presentation/widgets/widgets.dart` | Barrel for widgets | Re-exports HubProctorContent, HubQuickTestContent — no change needed |
| `lib/features/forms/presentation/screens/mdot_hub_screen.dart` | Direct consumer of both widgets + calculator | DIRECT CHANGE (listed above) |
| `lib/test_harness/stub_services.dart` | Stubs for PdfService/FormPdfService | No change needed — stubs return empty bytes |

## Test Files

| Test File | Exercises | Status |
|-----------|-----------|--------|
| `test/features/forms/services/mdot_0582b_calculator_test.dart` | `Mdot0582BCalculator` | EXISTS — needs update for removed auto-conversion + new HMA calc test |
| `test/services/pdf_service_test.dart` | `PdfService` (IDR) | EXISTS — no changes needed (tests stub) |
| `test/features/forms/services/form_pdf_service_test.dart` | `FormPdfService` (0582B) | EXISTS — no changes needed |

## Dead Code to Remove

| Symbol | File | Line | Reason |
|--------|------|------|--------|
| `_cubicCmPerCubicFt` | `mdot_0582b_calculator.dart` | 11 | No longer needed after removing auto-conversion |
| cm³→ft³ conversion block | `mdot_0582b_calculator.dart` | 80-84 | Replaced by direct cu. ft. input |

## Data Flow Diagram

```
SOIL MODE (existing):
  Setup Fields (B,C,E) → 20/10 Weights → Calculator.calculateProctorChain()
    → wet_soil_g(F), wet_soil_lbs(G), compacted_wet_pcf(H)
    → OnePointCalculator → max_density_pcf(I), optimum_moisture_pct(J)
    → Provider.appendMdot0582bProctorRow() → FormResponse JSON

HMA MODE (new):
  Gmm field → Gmm × 62.4 → max_density_pcf(I)
  OR: Direct Max Density PCF field → max_density_pcf(I)
    → Provider.appendMdot0582bProctorRow() → FormResponse JSON
    (no B,C,E,F,G,H,J fields)

IDR TEMPLATE:
  Original PDF → assets/templates/idr_template.pdf
    → PdfService.generateIdrPdf() → filled PDF
    → PdfService.generateDebugPdf() → field-mapped PDF
      → showReportDebugPdfActionsDialog() → Preview/Save/Share
```

## Blast Radius Summary

- **Direct changes:** 7 files (5 Dart, 1 asset, 1 test)
- **Dependent files:** 2 (barrel + stubs, no changes needed)
- **Test files to update:** 1 (`mdot_0582b_calculator_test.dart`)
- **Dead code removal:** 2 items (constant + conversion block)

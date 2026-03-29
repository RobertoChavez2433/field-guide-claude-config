# 0582B Naming/HMA Mode Fixes + IDR Template Replacement — Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Fix 0582B density form labels to match the real paper form, add HMA/Soil mode toggle, fix volume mold units, and replace IDR template with original copy.
**Spec:** `.claude/specs/2026-03-26-0582b-fixes-and-idr-template-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-26-0582b-fixes-and-idr-template/`

**Architecture:** Label renaming is a straight find-replace across two widget files and one screen file. The HMA/Soil toggle adds a segmented button to the proctor section that conditionally hides soil-specific fields, requiring new state in `mdot_hub_screen.dart` and new parameters on `HubProctorContent`. The calculator change removes a unit auto-conversion that is no longer needed since users now enter cu. ft. directly.
**Tech Stack:** Flutter/Dart, PDF assets
**Blast Radius:** 7 direct files, 0 dependent (label-only changes), 1 test file, 0 cleanup

---

## Phase 1: Data Layer — Calculator Fix

### Sub-phase 1.1: Remove Volume Mold Auto-Conversion

**Files:**
- Modify: `lib/features/forms/data/services/mdot_0582b_calculator.dart:11,80-84`

**Agent**: `backend-data-layer-agent`

#### Step 1.1.1: Delete the `_cubicCmPerCubicFt` constant

```
old_string: static const double _cubicCmPerCubicFt = 28316.846;
new_string: [DELETE LINE]
```

// WHY: Users now enter volume in cu. ft. directly; the auto-conversion from cm³ is no longer needed.

#### Step 1.1.2: Replace the auto-conversion block with direct assignment

```
old_string:
    // Auto-convert cm³ to ft³ if value > 1.0 (no standard mold exceeds 1 ft³;
    // the common ASTM mold is 943.3 cm³ = 0.0333 ft³).
    final volumeCuft = (volumeMoldCuft != null && volumeMoldCuft > 1.0)
        ? volumeMoldCuft / _cubicCmPerCubicFt
        : volumeMoldCuft;

new_string:
    // FROM SPEC: Users enter volume directly in cu. ft. — no conversion needed.
    final volumeCuft = volumeMoldCuft;
```

---

## Phase 2: Testing Keys

### Sub-phase 2.1: Add New HMA Mode Testing Keys

**Files:**
- Modify: `lib/shared/testing_keys/toolbox_keys.dart`
- Modify: `lib/shared/testing_keys/testing_keys.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 2.1.1: Add three new keys to `toolbox_keys.dart`

Insert after the `hubProctorSendButton` key definition:

```dart
  // FROM SPEC: New keys for HMA/Soil mode toggle
  static const hubProctorModeToggle = Key('hub_proctor_mode_toggle');
  static const hubProctorGmmField = Key('hub_proctor_gmm_field');
  static const hubProctorHmaMaxDensity = Key('hub_proctor_hma_max_density');
```

#### Step 2.1.2: Delegate new keys in `testing_keys.dart`

Add the three new delegations alongside the existing `hubProctor*` delegations in the `TestingKeys` class:

```dart
  static const hubProctorModeToggle = ToolboxTestingKeys.hubProctorModeToggle;
  static const hubProctorGmmField = ToolboxTestingKeys.hubProctorGmmField;
  static const hubProctorHmaMaxDensity = ToolboxTestingKeys.hubProctorHmaMaxDensity;
```

---

## Phase 3: Presentation — Label Renaming

### Sub-phase 3.1: Proctor Content Label Renaming

**Files:**
- Modify: `lib/features/forms/presentation/widgets/hub_proctor_content.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 3.1.1: Rename `lastSentProctor` banner labels

```
old_string:
              '· MDD ${lastSentProctor!['max_density_pcf'] ?? '--'} '
              '· OMC ${lastSentProctor!['optimum_moisture_pct'] ?? '--'}% '
              '· ${((lastSentProctor!['weights_20_10'] as List?)?.length ?? 0)} readings',

new_string:
              '· (I) Max Density ${lastSentProctor!['max_density_pcf'] ?? '--'} '
              '· (J) Opt. Moisture ${lastSentProctor!['optimum_moisture_pct'] ?? '--'}% '
              '· ${((lastSentProctor!['weights_20_10'] as List?)?.length ?? 0)} readings',
```

#### Step 3.1.2: Rename LIVE card text

```
old_string: 'LIVE   MDD $maxDensity  OMC $optimum%'
new_string: 'LIVE  (I) $maxDensity PCF  (J) $optimum%'
```

#### Step 3.1.3: Rename setup field labels

Apply these label replacements in the `_setupField` calls:

| old_string | new_string |
|---|---|
| `label: 'Moisture %'` | `label: '(B) Moisture %'` |
| `label: 'Vol Mold (cm³)'` | `label: '(C) Volume Mold Cu. Ft.'` |
| `label: 'Mold (g)'` | `label: '(E) Mold (g)'` |

**CAUTION**: The `_setupField` method uses `label:` as the named parameter (lines 148, 156, 164). Inside `_setupField`, `label` is passed to `InputDecoration(labelText: label)`. The find-replace targets the call site (`label:`), NOT the `InputDecoration` (`labelText:`).

#### Step 3.1.4: Rename CALCULATED section labels AND fix duplicate units

The `_calcPair` calls have units in BOTH the label and value strings. After renaming labels to include units, remove the duplicate unit from the value argument to avoid display like "(F) Wet Soil (g) — 1234.56 g".

Replace the full `_calcPair(...)` calls (lines 244-277 of `hub_proctor_content.dart`):

```
old_string:
                    child: _calcPair(
                      'Wet Soil',
                      '${_formatted('wet_soil_g')} g',
                    ),

new_string:
                    child: _calcPair(
                      '(F) Wet Soil (g)',
                      _formatted('wet_soil_g'),
                    ),
```

```
old_string:
                    child: _calcPair(
                      'Wet Soil (lbs)',
                      _formatted('wet_soil_lbs'),
                    ),

new_string:
                    child: _calcPair(
                      '(G) Wet Soil (lbs)',
                      _formatted('wet_soil_lbs'),
                    ),
```

```
old_string:
                    child: _calcPair(
                      'Wet PCF',
                      _formatted('compacted_wet_pcf'),
                    ),

new_string:
                    child: _calcPair(
                      '(H) Compacted Soil Wet PCF',
                      _formatted('compacted_wet_pcf'),
                    ),
```

```
old_string:
                    child: _calcPair(
                      'MDD',
                      '${_formatted('max_density_pcf')} pcf',
                    ),

new_string:
                    child: _calcPair(
                      '(I) Max Density PCF',
                      _formatted('max_density_pcf'),
                    ),
```

```
old_string:
                    child: _calcPair(
                      'OMC',
                      '${_formatted('optimum_moisture_pct')}%',
                    ),

new_string:
                    child: _calcPair(
                      '(J) Optimum Moisture %',
                      _formatted('optimum_moisture_pct'),
                    ),
```

**NOTE**: `(G) Wet Soil (lbs)` value `_formatted('wet_soil_lbs')` was already plain (no unit suffix). `(H) Compacted Soil Wet PCF` value was also plain. Only (F), (I), and (J) had duplicate units that needed stripping from the value.

### Sub-phase 3.2: Quick Test Content Label Renaming

**Files:**
- Modify: `lib/features/forms/presentation/widgets/hub_quick_test_content.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 3.2.1: Rename the proctor reference banner

```
old_string: 'Using Proctor #$proctorNumber · MDD $maxDensity'
new_string: 'Using Proctor #$proctorNumber · (I) Max Density $maxDensity PCF'
```

#### Step 3.2.2: Rename summary tile labels in lastSentTest banner

Use the full `label:` prefix to avoid matching `'Dry'` inside `'Dry Density'` at line 132 or `'Wet'` inside `'Wet Density'` at line 134:

| old_string | new_string |
|---|---|
| `label: 'Dry',` (line 78) | `label: '(6) Dry',` |
| `label: 'Wet',` (line 82) | `label: '(7) Wet',` |
| `label: 'Comp%',` (line 86) | `label: '(11) Comp%',` |

#### Step 3.2.3: Rename input field labels

Apply these replacements in the field/row calls:

| old_string | new_string |
|---|---|
| `'Orig/Recheck'` | `'(1) Original / (2) Recheck'` |
| `'Depth (in)'` | `'(3) Test Depth (in)'` |
| `'Counts MC'` | `'(4) Counts MC'` |
| `'Counts DC'` | `'(5) Counts DC'` |
| `'Dry Density'` | `'(6) Dry Density PCF'` |
| `'Wet Density'` | `'(7) Wet Density PCF'` |
| `'Moisture %'` (in _row call, ~line 134) | `'(9) Moisture %'` |
| `'Max Density (P#1)'` | `'(10) Max Density PCF'` |
| `'% Compaction'` | `'(11) % Compaction'` |
| `'Moisture PCF'` | `'(8) Moisture PCF'` |
| `'Station'` | `'(12) Station'` |
| `'Left (ft)'` | `'(13) Left (ft)'` |
| `'Right (ft)'` | `'(14) Right (ft)'` |
| `'Below Grade (ft)'` | `'(15) Depth Below Grade (ft)'` |
| `'Item of Work'` (dropdown label) | `'(16) Item of Work'` |

**CAUTION**: The `'Moisture %'` label appears in both proctor (Step 3.1.3) and quick test (this step). In hub_proctor_content.dart it becomes `'(B) Moisture %'`. In hub_quick_test_content.dart it becomes `'(9) Moisture %'`. These are different files so no collision, but verify the correct replacement is applied to each file.

### Sub-phase 3.3: Hub Screen Summary Tile Label Renaming

**Files:**
- Modify: `lib/features/forms/presentation/screens/mdot_hub_screen.dart:766-784`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 3.3.1: Rename proctor summary tile labels

In the proctor summary tiles section (~lines 766-784):

| old_string | new_string |
|---|---|
| `label: 'MDD',` (~line 768) | `label: 'Max Density',` |
| `label: 'OMC',` (~line 773) | `label: 'Opt. Moisture',` |

// FROM SPEC: Collapsed summary tiles use short names without column letters.

#### Step 3.3.2: Rename quick test summary tile labels

In the quick test collapsed summary tiles (~lines 831-841 of `mdot_hub_screen.dart`):

| old_string | new_string |
|---|---|
| `label: 'Dry'` (test summary tile, ~line 831) | `label: '(6) Dry'` |
| `label: 'Wet'` (test summary tile, ~line 836) | `label: '(7) Wet'` |
| `label: 'Comp%'` (test summary tile, ~line 841) | `label: '(11) Comp%'` |

**CAUTION**: The proctor section also has summary tiles with `'MDD'`/`'OMC'`/`'Wet PCF'` at ~lines 768-780. Ensure the find-replace targets the correct section. The test summary tiles are ~50 lines below the proctor ones.

---

## Phase 4: Presentation — HMA/Soil Mode Toggle

### Sub-phase 4.1: Add HMA State to Hub Screen

**Files:**
- Modify: `lib/features/forms/presentation/screens/mdot_hub_screen.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 4.1.1: Add new state variables

Add after the existing proctor state declarations (~line 44-51):

```dart
  // FROM SPEC: HMA/Soil mode toggle for proctor section
  String _proctorMode = 'soil';
  late final TextEditingController _hmaGmmController;
  late final TextEditingController _hmaMaxDensityController;
```

#### Step 4.1.2: Initialize and dispose new controllers

In `initState`, add alongside existing controller initialization:

```dart
    _hmaGmmController = TextEditingController();
    _hmaMaxDensityController = TextEditingController();
```

In `dispose`, add:

```dart
    _hmaGmmController.dispose();
    _hmaMaxDensityController.dispose();
```

#### Step 4.1.3: Add `_onProctorModeChanged` method

```dart
  // FROM SPEC: Switching modes clears the other mode's fields.
  // IMPORTANT: Weight readings are preserved in state but hidden (spec edge case).
  // Do NOT remove or dispose weight controllers on mode switch.
  void _onProctorModeChanged(String mode) {
    setState(() {
      _proctorMode = mode;
      if (mode == 'hma') {
        // Clear soil setup fields only — weight readings preserved but hidden
        _proctor['moisture']!.clear();
        _proctor['volume']!.clear();
        _proctor['mold']!.clear();
        _weightsConfirmed = false;
        _proctorCalc = null;
      } else {
        // Clear HMA fields
        _hmaGmmController.clear();
        _hmaMaxDensityController.clear();
      }
    });
    // Recalc so LIVE card reflects current mode's values immediately
    _recalcProctor();
    _touch();
  }
```

#### Step 4.1.4: Make `_recalcProctor()` mode-aware

The existing `_recalcProctor()` (lines 309-318) runs the soil calculator unconditionally. In HMA mode, soil fields are empty so `_proctorCalc` becomes all nulls — the LIVE card reads from `calcResult` and would show `--` for everything.

Update `_recalcProctor()` to branch on mode:

```
old_string:
  void _recalcProctor() {
    setState(() {
      _proctorCalc = _calculator.calculateProctorChain(
        moisturePercent: _asProctorDouble('moisture'),
        volumeMoldCuft: _asProctorDouble('volume'),
        wetSoilMoldG: _weightsConfirmed ? _finalWeightAsDouble : null,
        moldG: _asProctorDouble('mold'),
      );
    });
  }

new_string:
  void _recalcProctor() {
    setState(() {
      if (_proctorMode == 'hma') {
        // HMA mode: populate calcResult with the HMA Max Density value
        // so the LIVE card can display it via _formatted('max_density_pcf')
        final maxDensity = double.tryParse(_hmaMaxDensityController.text.trim());
        _proctorCalc = {
          'max_density_pcf': maxDensity,
          'optimum_moisture_pct': null,
          'compacted_wet_pcf': null,
          'wet_soil_g': null,
          'wet_soil_lbs': null,
          'one_point_error': null,
        };
      } else {
        _proctorCalc = _calculator.calculateProctorChain(
          moisturePercent: _asProctorDouble('moisture'),
          volumeMoldCuft: _asProctorDouble('volume'),
          wetSoilMoldG: _weightsConfirmed ? _finalWeightAsDouble : null,
          moldG: _asProctorDouble('mold'),
        );
      }
    });
  }
```

#### Step 4.1.5: Add `_onGmmChanged` method

```dart
  // FROM SPEC: Gmm auto-calculates Max Density = Gmm × 62.4
  // SECURITY: Gmm must be in [2.0, 2.8] range (specific gravity of aggregate mixes).
  // Values outside this range are physically impossible and would produce nonsensical densities.
  void _onGmmChanged(String value) {
    final gmm = double.tryParse(value);
    if (gmm != null && gmm >= 2.0 && gmm <= 2.8) {
      _hmaMaxDensityController.text = (gmm * 62.4).toStringAsFixed(2);
    } else {
      _hmaMaxDensityController.clear();
    }
    // IMPORTANT: Call _recalcProctor so the LIVE card updates with the new HMA Max Density
    _recalcProctor();
    _touch();
  }
```

#### Step 4.1.6: Update `_canSendProctor` to branch on mode

Wrap the existing `_canSendProctor` logic (~lines 285-293) with a mode check:

```dart
  bool get _canSendProctor {
    if (_proctorMode == 'hma') {
      // FROM SPEC: HMA mode only needs Max Density to have a value
      // SECURITY: Max Density must be in [100, 175] range (physically possible PCF values)
      final maxDensity = double.tryParse(_hmaMaxDensityController.text.trim());
      return maxDensity != null && maxDensity >= 100 && maxDensity <= 175;
    }
    // existing soil mode logic unchanged
    ...
  }
```

#### Step 4.1.7: Update `_sendProctor` to branch on mode

In `_sendProctor()` (~lines 407-467), add the HMA branch **BEFORE the `final weights = _enteredWeights; if (weights.isEmpty) return;` guard at lines 409-410**. This is critical — HMA mode has no weight readings, so the weights guard would silently block HMA sends if the branch comes after it.

The insertion point is immediately after `if (_response == null || _saving || !_canSendProctor) return;` (line 408) and before `final weights = _enteredWeights;` (line 409):

```dart
  if (_proctorMode == 'hma') {
    setState(() => _saving = true);
    final gmmValue = double.tryParse(_hmaGmmController.text);
    final maxDensityPcf = double.tryParse(_hmaMaxDensityController.text);

    final row = <String, dynamic>{
      'test_number': _proctorNo,
      'proctor_number': _proctorNo,
      'mode': 'hma',
      'gmm': gmmValue,
      'max_density_pcf': maxDensityPcf,
    };

    // NOTE: Uses Provider pattern (context.read), NOT Riverpod (ref.read).
    // SECURITY: Wrapped in try/finally to guarantee _saving is reset on exception.
    // Without this, an unhandled throw would leave _saving=true permanently,
    // locking the user out of all send/save operations.
    final provider = context.read<InspectorFormProvider>();
    try {
      final saved = await provider.appendMdot0582bProctorRow(
        responseId: _response!.id,
        row: row,
      );
      if (!mounted) return;
      setState(() {
        _saving = false;
        if (saved != null) {
          _response = saved;
          _lastSentProctor = saved.parsedProctorRows.lastOrNull;
          _proctorNo += 1;
          _dirty = false;
          _hmaGmmController.clear();
          _hmaMaxDensityController.clear();
        }
      });
      if (saved == null) {
        _snack(provider.error ?? 'Failed to send proctor', color: AppTheme.statusError);
        return;
      }
      _snack('Proctor #${_proctorNo - 1} sent to 0582B', color: AppTheme.accentAmber);
      _recalcTest();
      await _expand(2);
    } catch (e) {
      if (mounted) {
        setState(() => _saving = false);
        _snack('Failed to send proctor: $e', color: AppTheme.statusError);
      }
    }
    return;
  }
  // ... existing soil send logic
```

#### Step 4.1.8: Update `_draft()` to save/restore HMA state

In `_draft()` (~line 355-369), add HMA fields **inside the `'proctor'` submap** (not at the top level):

```dart
  Map<String, dynamic> _draft() => {
    'proctor': {
      // ... existing proctor fields ...
      'moisture_percent': _proctor['moisture']!.text.trim(),
      'volume_mold_cuft': _proctor['volume']!.text.trim(),
      'mold_g': _proctor['mold']!.text.trim(),
      'weights_20_10': _enteredWeights,
      'wet_soil_mold_g': _finalWeightText ?? '',
      'weights_confirmed': _weightsConfirmed,
      // NEW: HMA mode fields nested inside proctor submap
      'proctor_mode': _proctorMode,
      'hma_gmm': _hmaGmmController.text.trim(),
      'hma_max_density': _hmaMaxDensityController.text.trim(),
    },
    'test': { ... },
  };
```

In `_hydrate()` (~line 190-203, inside the `if (proctorDraft != null)` block), restore HMA state from the **nested** `proctorDraft`:

```dart
    if (proctorDraft != null) {
      // ... existing field restoration ...
      // NEW: Restore HMA mode state
      // SECURITY: Constrain to known values only
      _proctorMode = (proctorDraft['proctor_mode'] == 'hma') ? 'hma' : 'soil';
      _hmaGmmController.text = (proctorDraft['hma_gmm'] ?? '').toString();
      _hmaMaxDensityController.text = (proctorDraft['hma_max_density'] ?? '').toString();
    }
```

**NOTE**: No changes needed to `inspector_form_provider.dart`. The `appendMdot0582bProctorRow` method accepts `Map<String, dynamic>` and passes arbitrary keys through. The new `mode` and `gmm` keys will persist without modification.

### Sub-phase 4.2: Add HMA Mode UI to Proctor Content Widget

**Files:**
- Modify: `lib/features/forms/presentation/widgets/hub_proctor_content.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 4.2.1: Add new constructor parameters

Add to the `HubProctorContent` constructor:

```dart
  final String proctorMode;
  final ValueChanged<String> onModeChanged;
  final TextEditingController gmmController;
  final TextEditingController hmaMaxDensityController;
  final ValueChanged<String> onGmmChanged;
```

#### Step 4.2.2: Add SegmentedButton at top of build method

Insert as the first child in the Column, before the `lastSentProctor` banner:

```dart
  // FROM SPEC: HMA/Soil mode toggle at top of proctor section
  SegmentedButton<String>(
    key: TestingKeys.hubProctorModeToggle,
    segments: const [
      ButtonSegment(value: 'soil', label: Text('SOIL')),
      ButtonSegment(value: 'hma', label: Text('HMA')),
    ],
    selected: {proctorMode},
    onSelectionChanged: (set) => onModeChanged(set.first),
  ),
  const SizedBox(height: 12),
```

#### Step 4.2.3: Wrap soil-only sections in mode conditional

Wrap the following sections with `if (proctorMode == 'soil') ...[]`:
- SETUP row (Moisture %, Volume Mold, Mold fields)
- 20/10 WEIGHTS section (header, weight cards, confirm/edit buttons)
- CALCULATED section (header and calc card)

#### Step 4.2.4: Add HMA-specific fields

Add after the mode toggle, inside `if (proctorMode == 'hma') ...[]`:

```dart
  // FROM SPEC: HMA mode shows only Gmm and Max Density fields
  Padding(
    padding: const EdgeInsets.symmetric(horizontal: 8),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextFormField(
          key: TestingKeys.hubProctorGmmField,
          controller: gmmController,
          onChanged: onGmmChanged,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(
            labelText: 'Gmm (from JMF)',
            helperText: 'TMD = Gmm × 62.4 (see JMF form 1911)',
          ),
        ),
        const SizedBox(height: 12),
        TextFormField(
          key: TestingKeys.hubProctorHmaMaxDensity,
          controller: hmaMaxDensityController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(
            labelText: '(I) Max Density PCF',
          ),
        ),
      ],
    ),
  ),
```

#### Step 4.2.5: Update LIVE card for HMA mode

In the LIVE card section, conditionally hide (J) optimum moisture when in HMA mode:

```dart
  // FROM SPEC: HMA mode LIVE card shows only (I) Max Density PCF (no J)
  if (proctorMode == 'hma')
    Text('LIVE  (I) $maxDensity PCF', ...)
  else
    Text('LIVE  (I) $maxDensity PCF  (J) $optimum%', ...),
```

### Sub-phase 4.3: Wire HMA Parameters in Hub Screen

**Files:**
- Modify: `lib/features/forms/presentation/screens/mdot_hub_screen.dart:785-805`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 4.3.1: Pass new parameters to HubProctorContent

Add to the `HubProctorContent(...)` instantiation:

```dart
  proctorMode: _proctorMode,
  onModeChanged: _onProctorModeChanged,
  gmmController: _hmaGmmController,
  hmaMaxDensityController: _hmaMaxDensityController,
  onGmmChanged: _onGmmChanged,
```

---

## Phase 5: IDR Template Replacement + Debug PDF Wiring

### Sub-phase 5.1: Replace IDR Template

**Files:**
- Replace: `assets/templates/idr_template.pdf`

**Agent**: `general-purpose`

#### Step 5.1.1: Copy original IDR PDF

The user will provide the source path to the original IDR PDF. Copy it to `assets/templates/idr_template.pdf`, overwriting the existing file.

**NOTE**: The user must supply the source PDF path at execution time. Prompt if not available.

### Sub-phase 5.2: Add Debug PDF Menu Item to Entry Editor

**Files:**
- Modify: `lib/features/entries/presentation/screens/entry_editor_screen.dart:755-776`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 5.2.1: Add debug PDF PopupMenuItem to overflow menu (debug builds only)

In the `itemBuilder` of the `PopupMenuButton`, add a new item before the delete item. **Gate behind `kDebugMode`** so it never ships to production:

```dart
  // SECURITY: Debug-only — exposes internal PDF field schema
  if (kDebugMode)
    PopupMenuItem(
      key: TestingKeys.reportDebugPdfMenuItem,
      value: 'debug_pdf',
      child: const ListTile(
        leading: Icon(Icons.bug_report),
        title: Text('Debug IDR PDF'),
        contentPadding: EdgeInsets.zero,
      ),
    ),
```

**NOTE**: `kDebugMode` is defined in `package:flutter/foundation.dart` which is re-exported by `package:flutter/material.dart`. Since `entry_editor_screen.dart` already imports `material.dart` (line 3), `kDebugMode` is available without adding a new import. No import change needed.

#### Step 5.2.2: Handle debug_pdf selection in onSelected

Update the `onSelected` callback to handle the new value:

```
old_string:
            onSelected: (value) {
              if (value == 'delete') _confirmDelete();
            },

new_string:
            onSelected: (value) async {
              if (value == 'delete') _confirmDelete();
              if (value == 'debug_pdf') {
                // FROM SPEC: Wire up IDR debug PDF generation for field mapping verification
                // NOTE: Uses Provider pattern (context.read), NOT Riverpod.
                final pdfService = context.read<PdfService>();
                final pdfBytes = await pdfService.generateDebugPdf();
                if (!mounted) return;
                showReportDebugPdfActionsDialog(
                  context: context,
                  pdfBytes: pdfBytes,
                  pdfService: pdfService,
                );
              }
            },
```

**NOTE**: `PdfService` is available via `services.dart` barrel (line 26, imports `package:construction_inspector/features/pdf/services/services.dart`). The `showReportDebugPdfActionsDialog` is available via `report_widgets.dart` barrel (line 30). `Uint8List` is imported at line 2 (`dart:typed_data`).

---

## Phase 6: Tests

### Sub-phase 6.1: Update Calculator Tests

**Files:**
- Modify: `test/features/forms/services/mdot_0582b_calculator_test.dart`

**Agent**: `qa-testing-agent`

#### Step 6.1.1: Add test verifying no auto-conversion

Add a new test case:

```dart
    test('uses volume mold value directly without conversion', () {
      // FROM SPEC: Volume is now entered in cu. ft. — no cm³ auto-conversion
      // Previously, values > 1.0 were auto-converted from cm³ to ft³.
      // Now 0.0333 should pass through unchanged.
      final result = calculator.calculateProctorChain(
        moisturePercent: 7.3, volumeMoldCuft: 0.0333,
        wetSoilMoldG: 3810, moldG: 1640,
      );
      expect(result['compacted_wet_pcf'], 143.54);
    });

    test('large volume mold value is NOT auto-converted from cm³', () {
      // FROM SPEC: Removed auto-conversion. A value of 943.3 should be used as-is
      // (this would produce nonsensical results, but the conversion is removed).
      final result = calculator.calculateProctorChain(
        moisturePercent: 7.3, volumeMoldCuft: 943.3,
        wetSoilMoldG: 3810, moldG: 1640,
      );
      // With 943.3 as direct cu. ft., wet_pcf = wet_soil_lbs / 943.3
      // This verifies the old conversion path is gone
      expect(result['compacted_wet_pcf'], isNotNull);
      expect(result['compacted_wet_pcf'], isNot(143.54));
    });
```

#### Step 6.1.2: Verify existing tests still pass

Existing proctor chain test uses `volumeMoldCuft: 0.0333` which is < 1.0 — it was never auto-converted, so results should remain identical. No changes needed to existing tests.

### Sub-phase 6.2: Widget Tests for HMA Mode

**Files:**
- Create: `test/features/forms/widgets/hub_proctor_content_test.dart`

**Agent**: `qa-testing-agent`

#### Step 6.2.1: Write widget test for HMA/Soil mode toggle visibility

```dart
// FROM SPEC: HMA mode hides soil fields, shows Gmm + Max Density
// Test that toggling mode shows/hides the correct fields
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/forms/presentation/widgets/hub_proctor_content.dart';
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';

void main() {
  group('HubProctorContent HMA mode', () {
    // Helper to build widget with given mode
    Widget buildWidget({required String mode}) {
      return MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: HubProctorContent(
              proctorNumber: 1,
              moistureController: TextEditingController(),
              volumeController: TextEditingController(),
              moldController: TextEditingController(),
              weightReadings: [TextEditingController(), TextEditingController()],
              calcResult: null,
              finalReadingNumber: null,
              finalWeightText: null,
              lastSentProctor: null,
              weightsConfirmed: false,
              canSend: false,
              onAddReading: () {},
              onConfirmWeights: () {},
              onEditWeights: () {},
              onSend: () {},
              onChanged: () {},
              proctorMode: mode,
              onModeChanged: (_) {},
              gmmController: TextEditingController(),
              hmaMaxDensityController: TextEditingController(),
              onGmmChanged: (_) {},
            ),
          ),
        ),
      );
    }

    testWidgets('soil mode shows setup fields and hides HMA fields', (tester) async {
      await tester.pumpWidget(buildWidget(mode: 'soil'));
      // Soil setup fields visible
      expect(find.byKey(TestingKeys.hubProctorSetupField('moisture_pct')), findsOneWidget);
      expect(find.byKey(TestingKeys.hubProctorSetupField('volume_mold')), findsOneWidget);
      expect(find.byKey(TestingKeys.hubProctorSetupField('mold_g')), findsOneWidget);
      // HMA fields not visible
      expect(find.byKey(TestingKeys.hubProctorGmmField), findsNothing);
      expect(find.byKey(TestingKeys.hubProctorHmaMaxDensity), findsNothing);
    });

    testWidgets('hma mode shows Gmm/MaxDensity and hides soil fields', (tester) async {
      await tester.pumpWidget(buildWidget(mode: 'hma'));
      // HMA fields visible
      expect(find.byKey(TestingKeys.hubProctorGmmField), findsOneWidget);
      expect(find.byKey(TestingKeys.hubProctorHmaMaxDensity), findsOneWidget);
      // Soil setup fields not visible
      expect(find.byKey(TestingKeys.hubProctorSetupField('moisture_pct')), findsNothing);
      expect(find.byKey(TestingKeys.hubProctorSetupField('volume_mold')), findsNothing);
    });
  });
}
```

#### Step 6.2.2: Write widget test for Gmm auto-calc

```dart
    testWidgets('Gmm input triggers onGmmChanged callback', (tester) async {
      String? lastGmmValue;
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: HubProctorContent(
              proctorNumber: 1,
              moistureController: TextEditingController(),
              volumeController: TextEditingController(),
              moldController: TextEditingController(),
              weightReadings: [TextEditingController(), TextEditingController()],
              calcResult: null,
              finalReadingNumber: null,
              finalWeightText: null,
              lastSentProctor: null,
              weightsConfirmed: false,
              canSend: false,
              onAddReading: () {},
              onConfirmWeights: () {},
              onEditWeights: () {},
              onSend: () {},
              onChanged: () {},
              proctorMode: 'hma',
              onModeChanged: (_) {},
              gmmController: TextEditingController(),
              hmaMaxDensityController: TextEditingController(),
              onGmmChanged: (v) => lastGmmValue = v,
            ),
          ),
        ),
      ));
      await tester.enterText(find.byKey(TestingKeys.hubProctorGmmField), '2.450');
      expect(lastGmmValue, '2.450');
    });
```

#### Step 6.2.3: Run widget tests

```
pwsh -Command "flutter test test/features/forms/widgets/hub_proctor_content_test.dart"
```

---

## Phase 7: Verification

### Sub-phase 7.1: Run Tests and Analysis

**Agent**: `general-purpose`

#### Step 7.1.1: Run calculator tests

```
pwsh -Command "flutter test test/features/forms/services/mdot_0582b_calculator_test.dart"
```

#### Step 7.1.2: Run static analysis

```
pwsh -Command "flutter analyze"
```

#### Step 7.1.3: Run full test suite

```
pwsh -Command "flutter test"
```

Fix any failures before marking complete.

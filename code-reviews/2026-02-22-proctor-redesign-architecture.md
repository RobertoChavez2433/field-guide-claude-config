# Code Review: 0582B Proctor + 20/10 Redesign — Architecture & State Management

**Date**: 2026-02-22
**Reviewer**: code-review-agent
**Scope**: Hub screen state management, section control, controller lifecycle

---

## Critical Issues (Must Fix)

### 1. `DropdownButtonFormField` uses non-existent `initialValue` parameter
**File**: `lib/features/forms/presentation/widgets/hub_quick_test_content.dart:105,117`

`DropdownButtonFormField` has a `value` parameter, not `initialValue`. Both the Orig/Recheck and Item of Work dropdowns are affected.

**Fix**: Change `initialValue: origRecheck` to `value: origRecheck` (line 105) and `initialValue: itemOfWork` to `value: itemOfWork` (line 117).

### 2. `_hydrate` silently drops 'Other' for `item_of_work` — data loss on draft restore
**File**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart:218`

The hydration guard only accepts `'Mainline'` or `'Shoulder'`, but the dropdown offers `'Other'` as a third option. Selecting 'Other', saving draft, and re-opening silently reverts to `'Mainline'`.

**Fix**: Add `|| itemOfWork == 'Other'` to the guard.

---

## Suggestions (Should Consider)

### 1. Dead redirect wrapper classes (4 classes, 35 lines)
**File**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart:886-920`

`FormFillScreen`, `QuickTestEntryScreen`, `ProctorEntryScreen`, `WeightsEntryScreen` are StatelessWidget shims that wrap `MdotHubScreen`. Router already uses `MdotHubScreen` directly.

**Fix**: Remove wrappers, update test harness registries to use `MdotHubScreen` directly.

### 2. ~20 dead testing keys from old 4-section design
**File**: `lib/shared/testing_keys/testing_keys.dart:221-275,280-282`

Keys like `mdot0582bProctorMoistureField`, `mdot0582bWeightsProctorChip`, `inputBarValueField` etc. are defined but unused.

**Fix**: Delete the `mdot0582b*` keys (lines 221-275) and `inputBar*` keys (lines 280-282).

### 3. `AnimatedCrossFade` always builds both children
**File**: `lib/features/forms/presentation/widgets/form_accordion.dart:102`

All 3 sections' expanded content (with TextFormFields) is always in the widget tree even when collapsed.

**Fix**: Use conditional rendering with `AnimatedSize`/`AnimatedSwitcher`.

### 4. `_previewPdf` lacks error handling
**File**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart:530`

`generatePreviewPdf` can throw; no try/catch wraps the call.

**Fix**: Wrap in try/catch, show snackbar on failure.

### 5. `_recalcTest` calls `setState(() {})` with empty body
**File**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart:315`

**Fix**: Move text assignment into `setState` callback for clarity.

### 6. Defensive `chart_type` removal still in provider
**File**: `lib/features/forms/presentation/providers/inspector_form_provider.dart:355`

Hub no longer sends `chart_type`. The `normalizedRow.remove('chart_type')` is dead defensive code.

### 7. Test field clearing outside `setState`
**File**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart:503-506`

After test send, field clearing occurs after `setState`. Proctor clearing (lines 408-414) is inside `setState`. Inconsistent.

### 8. `_confirmHeader` mutates `_headerConfirmed` outside `setState`
**File**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart:365`

**Fix**: Set inside `setState` for framework correctness.

---

## Minor

- `_sectionKeys` (line 29): Named keys would be more readable than indexed list.
- `HubHeaderContent._buildField` line 73-74: Redundant ternary `isAuto ? BorderStyle.solid : BorderStyle.solid`.
- `StatusPillBar` line 33-34: Trailing `SizedBox(width: 8)` after last pill.
- `form_viewer_screen.dart:328-333`: Still shows separate "Weights" button routing to same hub.

---

## Positive Observations

- Controller lifecycle is thorough — `dispose()` properly cleans up all four controller groups. `_restoreWeightReadings` correctly disposes old controllers before replacing.
- `mounted` checks after every async operation. Consistent and correct.
- Widget decomposition is excellent — hub screen owns all state; all three content widgets are pure StatelessWidgets.
- Provider usage follows project patterns: `context.read<>()` for one-shot operations.
- Draft round-trip is symmetric: `_draft()` and `_hydrate()` produce and consume the same JSON shape.
- `PopScope` with save/discard dialog correctly prevents accidental data loss.

---

## KISS/DRY Opportunities

- **Duplicate `percent_compaction` calculation**: `_calculator.calculate(...)` appears in both `build()` (lines 829-839) and `_sendTest()` (lines 463-473). Extract to a getter.
- **Duplicate number formatting**: `_fmt` (line 318) and `HubProctorContent._formatted` (line 379) do the same thing.
- **Large inline row maps**: `_sendProctor` (11 entries) and `_sendTest` (20+ entries). Extract to named builder methods.

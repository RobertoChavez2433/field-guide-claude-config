# Code Review: 0582B Proctor Widget & Calculation Logic

**Date**: 2026-02-22
**Reviewer**: code-review-agent
**Scope**: HubProctorContent widget, calculator chain, delta chips, LIVE card

---

## Critical Issues (Must Fix)

### 1. `_sendProctor` saves `weights.last` but calculation uses `_finalWeightAsDouble` — dual-derivation risk
**File**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart:388`

`_enteredWeights` (line 239) strips empty entries and compacts the list; `_finalWeightText` (line 244) scans backward through the original controller list. Both currently produce the same value but walk different data paths. If filtering logic changes, the persisted `wet_soil_mold_g` will silently diverge from the calculated MDD/OMC.

**Fix**: Replace `weights.last` at line 388 with `_finalWeightText ?? ''`, or compute the final weight once and reference it in both places.

### 2. Delta chip misleads when user leaves a gap between readings
**File**: `lib/features/forms/presentation/widgets/hub_proctor_content.dart:371-377`

`_deltaFor(index)` compares `weightReadings[index]` with `weightReadings[index - 1]`. If user fills readings 1 and 3 but leaves 2 empty, delta returns null. The chip shows amber "Δ --" and `isConverged` evaluates to `false`, so the green convergence border never appears even if the filled readings converge.

**Fix**: Either compute delta against the nearest previous *filled* reading, or show a distinct "fill previous reading" warning.

---

## Suggestions (Should Consider)

### 1. LIVE card appears green even when all values are `--`
**File**: `lib/features/forms/presentation/widgets/hub_proctor_content.dart:68-123`

Green border and "LIVE" pill render unconditionally. After a send (when `_proctorCalc` is null), card shows "LIVE MDD -- OMC --%" with full green treatment.

**Fix**: Use green only when `calcResult` contains a valid `max_density_pcf`. Use neutral style when values are `--`.

### 2. No maximum limit on weight readings
**File**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart:435-439`

`_addWeightReading()` unconditionally adds a controller. No upper bound.

**Fix**: Cap at 10-15 and disable the "Add Reading" button at the limit.

### 3. Widget test coverage for `HubProctorContent` is missing
**File**: `test/features/forms/presentation/widgets/form_shared_widgets_test.dart`

Tests exist for `FormAccordion`, `StatusPillBar`, `SummaryTiles`, `HubHeaderContent` — but not `HubProctorContent`, the most complex widget in the hub.

**Fix**: Add tests for delta chip colors, LIVE card updates, SEND button disable state, previously-sent summary rendering.

### 4. `_calcPair` label font size (11sp) may be too small for field use
**File**: `lib/features/forms/presentation/widgets/hub_proctor_content.dart:361`

Inspectors use this outdoors in bright sunlight, often with gloves. 11sp is below Material Design's recommended minimum.

**Fix**: Use `fontSize: 12` minimum.

### 5. `_formatted()` duplicated across widget and screen
**Files**: `hub_proctor_content.dart:379` and `mdot_hub_screen.dart:318`

Both do the same thing (format num to 2 decimal places with `--` fallback) but have different signatures.

**Fix**: Extract a shared `formatNumOrDash(dynamic value)` utility.

---

## Minor

- Line 86: `'LIVE   MDD $maxDensity  OMC $optimum%'` uses multiple spaces for alignment — fragile. Use `Row` with `SizedBox`.
- Line 171: `'+ Add Reading'` alongside `Icons.add` is redundant. Just "Add Reading".
- Line 100: `BorderRadius.circular(999)` for pill shape — `StadiumBorder` communicates intent better.
- Lines 886-921: Four wrapper classes should have doc comments explaining why they exist.
- `hub_proctor_content.dart:49-66`: Previously-sent summary card lacks `Semantics` for screen reader accessibility.

---

## Positive Observations

- Clean architecture separation: `HubProctorContent` is pure stateless, all business logic in `MdotHubScreen`.
- Robust null propagation in calculator: `calculateProctorChain` handles null at every step.
- Thorough testing key coverage on every interactive element.
- Delta calculation correctness: `|current - previous|` with `.abs()`, 10g threshold is domain-correct.
- OnePointCalculator ground-truth validation: 14-point test suite validates against known Michigan Cone values.
- Proper `mounted` checks after every async.
- Calculation chain verified correct: `finalWeight → wetSoilG → wetSoilLbs → compactedWetPcf → OnePoint → MDD, OMC`.
- SEND validation properly conservative: requires all 3 setup fields + reading + valid MDD + no error.

---

## KISS/DRY Opportunities

- Validation logic (`_canSendProctor`) belongs closer to the domain — `calculateProctorChain` could return a typed result class with `bool get isComplete`.
- `_formatted` / `_fmt` duplication (covered in Suggestions #5).

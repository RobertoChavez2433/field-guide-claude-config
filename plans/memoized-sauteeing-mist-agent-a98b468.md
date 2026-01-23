# Inspector Toolbox Feature - Implementation Plan

**Last Updated**: 2026-01-22
**Status**: READY FOR IMPLEMENTATION
**Source**: User request for construction calculation and conversion tools for field inspectors

---

## Overview

The Inspector Toolbox is a comprehensive set of calculation and conversion tools specifically designed for construction inspectors to perform common field calculations quickly and accurately. This feature will integrate with existing material quantities and provide offline-first functionality with optional calculation history tracking.

---

## Research Summary

### Industry Standard Tools Needed

Based on construction inspection industry standards and common field requirements, inspectors need:

1. **Material Volume/Area Calculations**: Convert between units (SF, SY, CF, CY)
2. **HMA (Hot Mix Asphalt) Calculations**: Tonnage based on area, thickness, and density
3. **Concrete Volume Calculations**: Slab, wall, column, and footing volumes
4. **Aggregate/Base Material Calculations**: Tonnage and volume conversions
5. **Compaction Calculations**: Lift thickness, density, and compaction factors
6. **Earthwork Calculations**: Cut/fill volumes and grade calculations
7. **Reinforcement Calculations**: Rebar spacing, quantity, and weight
8. **Paint/Coating Coverage**: Area coverage per gallon
9. **Unit Conversions**: Quick reference for common construction units

### Key Formulas and Constants

#### HMA (Hot Mix Asphalt)
- **Tonnage Formula**: `Tons = (Area_SF × Thickness_inches × Density_PCF) / (12 × 2000)`
- **Coverage Formula**: `SYD = (Tons × 2000 × 12) / (Thickness_inches × Density_PCF × 9)`
- **Standard Density**: 145-150 PCF (pounds per cubic foot) for compacted HMA
- **Conversion**: 1 SYD = 9 SF, 1 CY = 27 CF

#### Concrete
- **Slab Volume**: `CY = (Length_ft × Width_ft × Thickness_inches) / (12 × 27)`
- **Wall Volume**: `CY = (Length_ft × Height_ft × Thickness_inches) / (12 × 27)`
- **Cylinder Volume**: `CY = (π × (Diameter_ft/2)² × Height_ft) / 27`
- **Standard Density**: 150 PCF for concrete
- **Waste Factor**: Typically 5-10% added to calculated volume

#### Aggregate/Base Material
- **Tonnage to CY**: `CY = Tons / Density_factor`
- **Density Factors** (tons/CY):
  - Gravel/Stone (1/4"-2"): 1.4
  - Sand: 1.35
  - Base aggregate: 1.35-1.4
  - Crushed stone: 1.4-1.5

#### Compaction
- **Compaction Percentage**: `% = (Field_Density / Max_Density) × 100`
- **Lift Thickness**: Uncompacted to compacted conversion
- **Typical Compaction Ratios**:
  - Soil: 0.8-0.9 (80-90%)
  - Aggregate: 0.9-0.95 (90-95%)
  - HMA: 0.92-0.96 (92-96%)

#### Grade/Slope
- **Slope Percentage**: `% = (Rise_ft / Run_ft) × 100`
- **Slope Ratio**: `Ratio = Run_ft / Rise_ft` (e.g., 4:1)
- **Degrees to Percentage**: `% = tan(degrees) × 100`

#### Rebar
- **Weight per Linear Foot** (lbs/ft):
  - #3: 0.376, #4: 0.668, #5: 1.043, #6: 1.502
  - #7: 2.044, #8: 2.670, #9: 3.400, #10: 4.303
- **Spacing Calculation**: `Quantity = (Length_ft × Width_ft) / Spacing_on_center`
- **Lap Length**: Typically 40-60 bar diameters

#### Paint/Coating Coverage
- **Coverage Rate**: Typically 200-400 SF/gallon depending on surface
- **Formula**: `Gallons = (Area_SF / Coverage_rate) × Coats`

---

## Task 1: Create Toolbox Feature Structure (CRITICAL)

### Summary
Set up the feature-first folder structure for the new toolbox feature with data models, repositories, providers, and screens following established app architecture.

### Implementation Steps

1. Create feature folder structure (file: `lib/features/toolbox/`)
   ```
   lib/features/toolbox/
   ├── data/
   │   ├── models/
   │   │   ├── calculation_result.dart
   │   │   ├── calculation_history.dart
   │   │   └── models.dart (barrel)
   │   ├── datasources/
   │   │   ├── local/
   │   │   │   └── calculation_history_local_datasource.dart
   │   │   └── datasources.dart (barrel)
   │   ├── repositories/
   │   │   ├── calculation_history_repository.dart
   │   │   └── repositories.dart (barrel)
   │   └── data.dart (barrel)
   ├── domain/
   │   ├── calculators/
   │   │   ├── hma_calculator.dart
   │   │   ├── concrete_calculator.dart
   │   │   ├── aggregate_calculator.dart
   │   │   ├── compaction_calculator.dart
   │   │   ├── grade_calculator.dart
   │   │   ├── rebar_calculator.dart
   │   │   ├── paint_calculator.dart
   │   │   ├── unit_converter.dart
   │   │   └── calculators.dart (barrel)
   │   └── domain.dart (barrel)
   ├── presentation/
   │   ├── providers/
   │   │   ├── toolbox_provider.dart
   │   │   ├── calculation_history_provider.dart
   │   │   └── providers.dart (barrel)
   │   ├── screens/
   │   │   ├── toolbox_home_screen.dart
   │   │   ├── hma_calculator_screen.dart
   │   │   ├── concrete_calculator_screen.dart
   │   │   ├── aggregate_calculator_screen.dart
   │   │   ├── compaction_calculator_screen.dart
   │   │   ├── grade_calculator_screen.dart
   │   │   ├── rebar_calculator_screen.dart
   │   │   ├── paint_calculator_screen.dart
   │   │   ├── unit_converter_screen.dart
   │   │   ├── calculation_history_screen.dart
   │   │   └── screens.dart (barrel)
   │   ├── widgets/
   │   │   ├── calculator_card.dart
   │   │   ├── calculation_result_card.dart
   │   │   ├── input_field.dart
   │   │   ├── unit_dropdown.dart
   │   │   └── widgets.dart (barrel)
   │   └── presentation.dart (barrel)
   └── toolbox.dart (barrel)
   ```

2. Add database schema for calculation history (file: `lib/core/database/database_service.dart`)
   ```sql
   CREATE TABLE calculation_history (
     id TEXT PRIMARY KEY,
     calculator_type TEXT NOT NULL,
     input_values TEXT NOT NULL,
     result_values TEXT NOT NULL,
     notes TEXT,
     project_id TEXT,
     entry_id TEXT,
     created_at TEXT NOT NULL,
     FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
     FOREIGN KEY (entry_id) REFERENCES daily_entries(id) ON DELETE CASCADE
   )
   ```

3. Add Supabase schema migration (file: `supabase/migrations/toolbox_schema.sql`)
   - Same table structure as SQLite
   - Add RLS policies for user-owned calculations
   - Add indexes for project_id, entry_id, calculator_type, created_at

### Files to Create/Modify

| File | Changes |
|------|---------|
| `lib/features/toolbox/` | Create entire feature structure |
| `lib/core/database/database_service.dart` | Add calculation_history table in _onCreate |
| `lib/core/router/app_router.dart` | Add routes for toolbox screens |
| `lib/main.dart` | Add ToolboxProvider to provider list |
| `supabase/migrations/toolbox_schema.sql` | Create Supabase schema |

### Agent Assignment
**Agent**: `data-layer-agent`

---

## Task 2: Implement Calculator Domain Logic (CRITICAL)

### Summary
Create all calculator classes with pure business logic for construction calculations. These are stateless calculator classes that implement formulas and return CalculationResult objects.

### Implementation Steps

1. Create base CalculationResult model (file: `lib/features/toolbox/data/models/calculation_result.dart`)
   ```dart
   class CalculationResult {
     final String calculatorType;
     final Map<String, dynamic> inputs;
     final Map<String, dynamic> outputs;
     final List<String> formulas; // Show user what formula was used
     final DateTime calculatedAt;
   }
   ```

2. Implement HMA Calculator (file: `lib/features/toolbox/domain/calculators/hma_calculator.dart`)
   - `calculateTonnage(area, thickness, density)`
   - `calculateCoverage(tons, thickness, density)`
   - `calculateAreaFromTonnage(tons, thickness, density)`
   - `calculateThicknessFromTonnage(tons, area, density)`
   - Default density: 145 PCF (user configurable)

3. Implement Concrete Calculator (file: `lib/features/toolbox/domain/calculators/concrete_calculator.dart`)
   - `calculateSlabVolume(length, width, thickness, wastePercent)`
   - `calculateWallVolume(length, height, thickness, wastePercent)`
   - `calculateColumnVolume(diameter, height, wastePercent)`
   - `calculateFootingVolume(length, width, depth, wastePercent)`
   - `calculateBags(cubicYards, bagsPerCubicYard)`

4. Implement Aggregate Calculator (file: `lib/features/toolbox/domain/calculators/aggregate_calculator.dart`)
   - `calculateTonnage(cubicYards, densityFactor)`
   - `calculateVolume(tons, densityFactor)`
   - Preset density factors for common materials
   - Custom density factor input

5. Implement Compaction Calculator (file: `lib/features/toolbox/domain/calculators/compaction_calculator.dart`)
   - `calculateCompactionPercent(fieldDensity, maxDensity)`
   - `calculateRequiredDensity(maxDensity, requiredPercent)`
   - `calculateLiftThickness(uncompactedThickness, compactionRatio)`

6. Implement Grade Calculator (file: `lib/features/toolbox/domain/calculators/grade_calculator.dart`)
   - `calculateSlopePercent(rise, run)`
   - `calculateSlopeRatio(rise, run)`
   - `degreesToPercent(degrees)`
   - `percentToDegrees(percent)`

7. Implement Rebar Calculator (file: `lib/features/toolbox/domain/calculators/rebar_calculator.dart`)
   - `calculateWeight(barSize, lengthFeet)`
   - `calculateQuantity(length, width, spacing)`
   - `calculateLapLength(barSize, barDiameters)`
   - Preset bar weights (#3 through #10)

8. Implement Paint Calculator (file: `lib/features/toolbox/domain/calculators/paint_calculator.dart`)
   - `calculateGallons(area, coverageRate, coats)`
   - `calculateCoverage(area, gallons, coats)`
   - Preset coverage rates for surfaces

9. Implement Unit Converter (file: `lib/features/toolbox/domain/calculators/unit_converter.dart`)
   - Length: ft, in, m, cm, mm
   - Area: SF, SY, SQ, acres, hectares
   - Volume: CF, CY, gallons, liters
   - Weight: lbs, tons, kg, metric tons
   - Temperature: F, C

### Files to Create

| File | Changes |
|------|---------|
| `lib/features/toolbox/data/models/calculation_result.dart` | Create model with serialization |
| `lib/features/toolbox/domain/calculators/hma_calculator.dart` | Implement all HMA formulas |
| `lib/features/toolbox/domain/calculators/concrete_calculator.dart` | Implement all concrete formulas |
| `lib/features/toolbox/domain/calculators/aggregate_calculator.dart` | Implement aggregate formulas |
| `lib/features/toolbox/domain/calculators/compaction_calculator.dart` | Implement compaction formulas |
| `lib/features/toolbox/domain/calculators/grade_calculator.dart` | Implement grade/slope formulas |
| `lib/features/toolbox/domain/calculators/rebar_calculator.dart` | Implement rebar formulas |
| `lib/features/toolbox/domain/calculators/paint_calculator.dart` | Implement paint coverage formulas |
| `lib/features/toolbox/domain/calculators/unit_converter.dart` | Implement unit conversions |

### Agent Assignment
**Agent**: `data-layer-agent`

---

## Task 3: Create Calculation History Data Layer (HIGH)

### Summary
Implement data persistence for calculation history with local SQLite storage and optional cloud sync.

### Implementation Steps

1. Create CalculationHistory model (file: `lib/features/toolbox/data/models/calculation_history.dart`)
   ```dart
   class CalculationHistory {
     final String id;
     final String calculatorType;
     final Map<String, dynamic> inputValues;
     final Map<String, dynamic> resultValues;
     final String? notes;
     final String? projectId;
     final String? entryId;
     final DateTime createdAt;
   }
   ```

2. Create local datasource (file: `lib/features/toolbox/data/datasources/local/calculation_history_local_datasource.dart`)
   - CRUD operations for calculation_history table
   - Query by project, entry, calculator type
   - Date range filtering

3. Create repository (file: `lib/features/toolbox/data/repositories/calculation_history_repository.dart`)
   - saveCalculation()
   - deleteCalculation()
   - getCalculationsByProject()
   - getCalculationsByEntry()
   - getRecentCalculations(limit)
   - getCalculationsByType(calculatorType)

4. Create provider (file: `lib/features/toolbox/presentation/providers/calculation_history_provider.dart`)
   - ChangeNotifier for history list
   - Load/save/delete operations
   - Filter by project/entry/type

### Files to Create

| File | Changes |
|------|---------|
| `lib/features/toolbox/data/models/calculation_history.dart` | Create model with JSON serialization |
| `lib/features/toolbox/data/datasources/local/calculation_history_local_datasource.dart` | Implement SQLite operations |
| `lib/features/toolbox/data/repositories/calculation_history_repository.dart` | Implement repository pattern |
| `lib/features/toolbox/presentation/providers/calculation_history_provider.dart` | Create ChangeNotifier provider |

### Agent Assignment
**Agent**: `data-layer-agent`

---

## Task 4: Build Toolbox Home Screen UI (HIGH)

### Summary
Create the main toolbox landing screen with calculator cards and quick access to recent calculations.

### Implementation Steps

1. Create ToolboxHomeScreen (file: `lib/features/toolbox/presentation/screens/toolbox_home_screen.dart`)
   - Grid of calculator cards
   - Quick access to recent calculations
   - Search/filter calculators
   - Link to full calculation history

2. Create CalculatorCard widget (file: `lib/features/toolbox/presentation/widgets/calculator_card.dart`)
   - Icon, title, description
   - Tap to navigate to calculator screen
   - Material 3 design with elevation

3. Add navigation route (file: `lib/core/router/app_router.dart`)
   ```dart
   GoRoute(
     path: '/toolbox',
     name: 'toolbox',
     builder: (context, state) => const ToolboxHomeScreen(),
   )
   ```

4. Add toolbox access from Dashboard (file: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`)
   - Add "Inspector Toolbox" card/button to dashboard
   - Show count of recent calculations

### UI Design Specifications

- **Layout**: 2-column grid on mobile, 3-4 columns on tablet/desktop
- **Card Design**:
  - Material 3 elevated card
  - Large icon at top (construction-related icons)
  - Calculator name
  - Brief description (1 line)
  - Tap animation
- **Colors**: Use AppTheme constants
- **Recent Calculations**: Scrollable horizontal list below grid

### Files to Create/Modify

| File | Changes |
|------|---------|
| `lib/features/toolbox/presentation/screens/toolbox_home_screen.dart` | Create home screen |
| `lib/features/toolbox/presentation/widgets/calculator_card.dart` | Create reusable card widget |
| `lib/core/router/app_router.dart` | Add /toolbox route |
| `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` | Add toolbox access button |

### Agent Assignment
**Agent**: `flutter-specialist-agent`

---

## Task 5: Build Individual Calculator Screens (HIGH)

### Summary
Create dedicated screens for each calculator with input forms, real-time calculations, and result display.

### Implementation Steps

1. Create HMA Calculator Screen (file: `lib/features/toolbox/presentation/screens/hma_calculator_screen.dart`)
   - Mode selector: Tonnage / Coverage / Area / Thickness
   - Input fields based on mode
   - Real-time calculation display
   - Save to history button
   - Export/share result

2. Create Concrete Calculator Screen (file: `lib/features/toolbox/presentation/screens/concrete_calculator_screen.dart`)
   - Shape selector: Slab / Wall / Column / Footing
   - Dimension inputs based on shape
   - Waste percentage slider
   - Unit selector (CY/CF)
   - Visual diagram showing dimensions

3. Create Aggregate Calculator Screen (file: `lib/features/toolbox/presentation/screens/aggregate_calculator_screen.dart`)
   - Mode: Tonnage or Volume
   - Material type dropdown (preset density factors)
   - Custom density input option
   - Conversion table display

4. Create Compaction Calculator Screen (file: `lib/features/toolbox/presentation/screens/compaction_calculator_screen.dart`)
   - Mode selector: Percent / Density / Lift Thickness
   - Input fields with validation
   - Pass/fail indicator for compaction percent
   - Specification presets (95%, 98%, etc.)

5. Create Grade Calculator Screen (file: `lib/features/toolbox/presentation/screens/grade_calculator_screen.dart`)
   - Mode selector: Percent / Ratio / Degrees
   - Rise and run inputs
   - Multi-format result display
   - Visual slope diagram

6. Create Rebar Calculator Screen (file: `lib/features/toolbox/presentation/screens/rebar_calculator_screen.dart`)
   - Mode selector: Weight / Quantity / Lap Length
   - Bar size dropdown (#3-#10)
   - Dimension inputs
   - Weight table reference

7. Create Paint Calculator Screen (file: `lib/features/toolbox/presentation/screens/paint_calculator_screen.dart`)
   - Mode: Gallons needed / Coverage area
   - Surface type dropdown
   - Custom coverage rate input
   - Number of coats selector

8. Create Unit Converter Screen (file: `lib/features/toolbox/presentation/screens/unit_converter_screen.dart`)
   - Category tabs: Length / Area / Volume / Weight / Temp
   - From/To unit dropdowns
   - Input field with real-time conversion
   - Conversion table for common values

### Shared Widget Components

Create reusable widgets (file: `lib/features/toolbox/presentation/widgets/`)
- `input_field.dart`: Numeric input with unit label
- `unit_dropdown.dart`: Unit selector dropdown
- `calculation_result_card.dart`: Display calculation results
- `formula_display.dart`: Show formula used
- `save_calculation_button.dart`: Save to history with optional notes

### UI/UX Patterns

- **Real-time Calculation**: Update results as user types (debounced)
- **Input Validation**: Show errors for invalid inputs
- **Result Emphasis**: Large, bold result with unit
- **Formula Transparency**: Show formula used
- **Quick Actions**: Save, Share, Clear buttons
- **Field Access Optimization**:
  - Remember last used values
  - Quick number pad for numeric inputs
  - Large tap targets for field use
  - Landscape support for tablets

### Files to Create

| File | Changes |
|------|---------|
| `lib/features/toolbox/presentation/screens/hma_calculator_screen.dart` | Full HMA calculator UI |
| `lib/features/toolbox/presentation/screens/concrete_calculator_screen.dart` | Full concrete calculator UI |
| `lib/features/toolbox/presentation/screens/aggregate_calculator_screen.dart` | Full aggregate calculator UI |
| `lib/features/toolbox/presentation/screens/compaction_calculator_screen.dart` | Full compaction calculator UI |
| `lib/features/toolbox/presentation/screens/grade_calculator_screen.dart` | Full grade calculator UI |
| `lib/features/toolbox/presentation/screens/rebar_calculator_screen.dart` | Full rebar calculator UI |
| `lib/features/toolbox/presentation/screens/paint_calculator_screen.dart` | Full paint calculator UI |
| `lib/features/toolbox/presentation/screens/unit_converter_screen.dart` | Full unit converter UI |
| `lib/features/toolbox/presentation/widgets/*.dart` | Shared calculator widgets |

### Agent Assignment
**Agent**: `flutter-specialist-agent`

---

## Task 6: Implement Calculation History Screen (MEDIUM)

### Summary
Create a screen to view, search, and manage calculation history with filtering and export capabilities.

### Implementation Steps

1. Create CalculationHistoryScreen (file: `lib/features/toolbox/presentation/screens/calculation_history_screen.dart`)
   - List of past calculations with date/time
   - Filter by calculator type
   - Filter by project/entry
   - Search by notes
   - Tap to view full calculation details
   - Swipe to delete
   - Bulk delete option

2. Create calculation detail bottom sheet
   - Full input/output display
   - Notes (editable)
   - Formula used
   - Associated project/entry (if any)
   - Actions: Re-run with same inputs, Share, Delete

3. Add route (file: `lib/core/router/app_router.dart`)
   ```dart
   GoRoute(
     path: '/toolbox/history',
     name: 'toolbox-history',
     builder: (context, state) => const CalculationHistoryScreen(),
   )
   ```

### Files to Create/Modify

| File | Changes |
|------|---------|
| `lib/features/toolbox/presentation/screens/calculation_history_screen.dart` | Create history screen |
| `lib/core/router/app_router.dart` | Add history route |

### Agent Assignment
**Agent**: `flutter-specialist-agent`

---

## Task 7: Integration with Existing Features (MEDIUM)

### Summary
Connect toolbox with existing material quantities, daily entries, and dashboard for seamless workflow.

### Implementation Steps

1. Add "Calculate" button to quantity entry
   - From bid item quantity screen, tap "Calculate"
   - Pre-populate calculator with bid item unit
   - Suggest appropriate calculator based on unit (CY -> concrete, SY -> HMA)
   - Option to save result back to quantity

2. Link calculations to daily entries
   - When on entry wizard, calculations can be tagged to that entry
   - View entry-specific calculations from report screen
   - Include calculation summary in PDF export

3. Dashboard integration
   - Show recent calculations on dashboard
   - Quick access to most-used calculators
   - Calculation statistics (count by type)

4. Material auto-population
   - When creating calculation from material quantity:
     - Auto-fill area/volume from bid item
     - Use standard densities if available
     - Link calculation to project

### Files to Modify

| File | Changes |
|------|---------|
| `lib/features/quantities/presentation/screens/quantities_screen.dart` | Add "Calculate" button |
| `lib/features/entries/presentation/screens/entry_wizard_screen.dart` | Enable calculation tagging |
| `lib/features/entries/presentation/screens/report_screen.dart` | Show linked calculations |
| `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` | Add toolbox statistics |

### Agent Assignment
**Agent**: `flutter-specialist-agent`

---

## Task 8: Offline Support and Data Sync (MEDIUM)

### Summary
Ensure all calculator functions work offline and implement cloud sync for calculation history.

### Implementation Steps

1. Verify offline calculator logic
   - All calculators are pure functions (no network calls)
   - Results calculated locally
   - History stored in SQLite first

2. Implement sync for calculation history
   - Create remote datasource (file: `lib/features/toolbox/data/datasources/remote/calculation_history_remote_datasource.dart`)
   - Add sync logic to repository
   - Register with sync orchestrator

3. Handle sync conflicts
   - Calculation history is append-only (no conflicts)
   - Use created_at for ordering
   - No update/delete sync needed initially

4. Add sync status indicators
   - Show sync status in history screen
   - Retry failed syncs

### Files to Create/Modify

| File | Changes |
|------|---------|
| `lib/features/toolbox/data/datasources/remote/calculation_history_remote_datasource.dart` | Create remote datasource |
| `lib/features/toolbox/data/repositories/calculation_history_repository.dart` | Add sync methods |
| `lib/features/sync/data/repositories/sync_orchestrator.dart` | Register toolbox sync |

### Agent Assignment
**Agent**: `supabase-agent`

---

## Task 9: Settings and User Preferences (LOW)

### Summary
Add user preferences for default units, density values, and calculator presets.

### Implementation Steps

1. Create toolbox settings model (file: `lib/features/toolbox/data/models/toolbox_settings.dart`)
   ```dart
   class ToolboxSettings {
     final String defaultLengthUnit; // ft, m
     final String defaultAreaUnit; // SF, SY, SQ
     final String defaultVolumeUnit; // CY, CF
     final double defaultHmaDensity; // 145 PCF
     final double defaultConcreteWaste; // 10%
     final Map<String, double> customDensityFactors;
   }
   ```

2. Add settings storage in shared preferences
   - Save/load toolbox settings
   - Merge with app settings or separate

3. Create toolbox settings screen (file: `lib/features/toolbox/presentation/screens/toolbox_settings_screen.dart`)
   - Default units
   - Default density values
   - Custom material presets
   - Access from toolbox home (gear icon)

4. Apply settings in calculators
   - Load default values from settings
   - Show user's preferred units first
   - Save custom density factors

### Files to Create/Modify

| File | Changes |
|------|---------|
| `lib/features/toolbox/data/models/toolbox_settings.dart` | Create settings model |
| `lib/features/toolbox/presentation/screens/toolbox_settings_screen.dart` | Create settings UI |
| `lib/features/toolbox/presentation/providers/toolbox_settings_provider.dart` | Settings state management |
| All calculator screens | Apply user defaults |

### Agent Assignment
**Agent**: `flutter-specialist-agent`

---

## Task 10: Testing and Documentation (LOW)

### Summary
Comprehensive testing of calculation accuracy and widget functionality, plus user documentation.

### Implementation Steps

1. Unit tests for calculators
   - Test all formulas with known values
   - Edge cases (zero, negative, very large numbers)
   - Precision testing (decimal places)
   - File: `test/features/toolbox/domain/calculators/*_test.dart`

2. Widget tests for screens
   - Input validation
   - Real-time calculation updates
   - Save functionality
   - File: `test/features/toolbox/presentation/screens/*_test.dart`

3. Integration tests
   - Full calculation workflow
   - History persistence
   - Integration with quantities
   - File: `integration_test/toolbox_test.dart`

4. Create user documentation
   - Calculator reference guide (formulas, when to use)
   - Video demos of each calculator
   - Common calculation scenarios
   - File: `docs/USER_GUIDE_TOOLBOX.md`

### Files to Create

| File | Changes |
|------|---------|
| `test/features/toolbox/domain/calculators/*_test.dart` | Unit tests for all calculators |
| `test/features/toolbox/presentation/screens/*_test.dart` | Widget tests |
| `integration_test/toolbox_test.dart` | E2E test |
| `docs/USER_GUIDE_TOOLBOX.md` | User documentation |

### Agent Assignment
**Agent**: `qa-testing-agent`

---

## Execution Order

### Phase 1: Foundation (Critical - Week 1)
1. **Task 1**: Create Toolbox Feature Structure - `data-layer-agent`
2. **Task 2**: Implement Calculator Domain Logic - `data-layer-agent`

### Phase 2: Data Persistence (High - Week 1-2)
3. **Task 3**: Create Calculation History Data Layer - `data-layer-agent`
4. **Task 8**: Offline Support and Data Sync - `supabase-agent`

### Phase 3: User Interface (High - Week 2-3)
5. **Task 4**: Build Toolbox Home Screen UI - `flutter-specialist-agent`
6. **Task 5**: Build Individual Calculator Screens - `flutter-specialist-agent`
7. **Task 6**: Implement Calculation History Screen - `flutter-specialist-agent`

### Phase 4: Integration (Medium - Week 3-4)
8. **Task 7**: Integration with Existing Features - `flutter-specialist-agent`
9. **Task 9**: Settings and User Preferences - `flutter-specialist-agent`

### Phase 5: Quality Assurance (Low - Week 4)
10. **Task 10**: Testing and Documentation - `qa-testing-agent`

---

## Technical Considerations

### Offline-First Requirements
- All calculations performed locally (no API calls)
- Calculator logic is pure functions
- History stored in SQLite immediately
- Sync happens in background
- No degradation when offline

### Performance Optimization
- Debounce real-time calculations (300ms)
- Lazy load calculation history
- Cache last used calculator settings
- Minimize widget rebuilds with const constructors
- Use ListView.builder for history lists

### Accessibility
- Large tap targets (minimum 48x48)
- Screen reader support
- High contrast mode support (already in app)
- Keyboard navigation for desktop
- Clear input validation messages

### Security
- No sensitive data in calculations
- History is user-scoped (RLS policies)
- Input sanitization for notes
- No code injection via formula display

### Cross-Platform Considerations
- Responsive layouts (mobile/tablet/desktop)
- Landscape mode optimization for tablets
- Keyboard shortcuts for desktop
- Native number keyboards on mobile
- Platform-specific haptic feedback

---

## UI/UX Design Guidelines

### Calculator Screen Layout Pattern
```
┌─────────────────────────────────┐
│  [← Back]  Calculator Name  [⚙] │ <- AppBar with settings
├─────────────────────────────────┤
│                                 │
│  [Mode Selector Chips]          │ <- If calculator has multiple modes
│                                 │
│  Input Section:                 │
│  ┌─────────────────────────┐   │
│  │ Label        [unit ▼]   │   │ <- Input with unit selector
│  │ [       value      ]     │   │
│  └─────────────────────────┘   │
│                                 │
│  [Calculate Button]             │ <- Optional if real-time
│                                 │
│  Result Section:                │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━┓   │
│  ┃  Result: 123.45 CY      ┃   │ <- Elevated card
│  ┃  Formula: (L×W×T)/(12×27)  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━┛   │
│                                 │
│  [Save] [Share] [Clear]         │ <- Action buttons
│                                 │
└─────────────────────────────────┘
```

### Color Scheme
- Input fields: Material 3 default
- Result cards: Elevated with primary color accent
- Success indicators: `AppTheme.success`
- Warning indicators: `AppTheme.warning`
- Error states: `AppTheme.error`

### Icons for Calculators
- HMA: `Icons.layers`
- Concrete: `Icons.architecture`
- Aggregate: `Icons.grain`
- Compaction: `Icons.compress`
- Grade: `Icons.terrain`
- Rebar: `Icons.grid_on`
- Paint: `Icons.format_paint`
- Units: `Icons.compare_arrows`
- History: `Icons.history`

---

## Verification Checklist

After implementation:

### Functional Requirements
- [ ] All 8 calculators produce accurate results
- [ ] Results match industry-standard calculations
- [ ] Real-time calculation updates work smoothly
- [ ] Calculation history saves and loads correctly
- [ ] History filters and search work as expected
- [ ] Integration with quantities functions properly
- [ ] Integration with daily entries functions properly
- [ ] Offline mode works for all features
- [ ] Sync to Supabase works without errors

### Code Quality
- [ ] Run `flutter analyze` - no errors
- [ ] Run `flutter test` - all tests pass
- [ ] All calculators have unit tests
- [ ] All screens have widget tests
- [ ] E2E test covers main workflows
- [ ] Code follows project coding standards
- [ ] No hardcoded values (use constants)
- [ ] Proper error handling throughout

### UI/UX Requirements
- [ ] Calculator screens are responsive (mobile/tablet/desktop)
- [ ] Input validation provides clear feedback
- [ ] Large tap targets for field use
- [ ] Landscape mode works on tablets
- [ ] Theme consistency (Light/Dark/High Contrast)
- [ ] Loading states show appropriate indicators
- [ ] Empty states have helpful messages
- [ ] Accessibility features work (screen readers)

### Performance
- [ ] Real-time calculations don't lag
- [ ] History list scrolls smoothly with 100+ items
- [ ] No memory leaks in calculator screens
- [ ] App size increase is reasonable (<2MB)
- [ ] Cold start time not significantly impacted

### Documentation
- [ ] User guide created
- [ ] Calculator formulas documented
- [ ] Code comments for complex calculations
- [ ] README updated with toolbox feature
- [ ] API documentation for calculators

---

## Future Enhancements (Post-MVP)

### Advanced Features
1. **Calculation Templates**: Save frequently used input sets
2. **Batch Calculations**: Calculate multiple scenarios at once
3. **Cost Estimation**: Integrate unit prices from bid items
4. **Photo Attachment**: Attach site photos to calculations
5. **Voice Input**: Dictate measurements in the field
6. **GPS Tagging**: Auto-tag calculations with location
7. **Weather Integration**: Show weather conditions with calculations
8. **PDF Export**: Export calculation summary to PDF
9. **Team Sharing**: Share calculations with team members
10. **Custom Calculators**: User-defined formulas

### Additional Calculators
- Pipe volume calculator
- Area/perimeter for complex shapes
- Truck load calculator
- Time/duration calculator
- Material waste calculator
- Excavation volume calculator
- Paving strip width calculator
- Signage area calculator

### Integration Enhancements
- Auto-populate from material deliveries
- Link to test results
- Calculation alerts based on thresholds
- Weekly calculation summary reports

---

## Risk Assessment

### High Risk
- **Calculation Accuracy**: Critical that formulas are correct
  - *Mitigation*: Extensive unit testing, manual verification, industry standard references

- **Unit Conversion Errors**: Wrong conversions could cause major issues
  - *Mitigation*: Unit test all conversions, clear unit labels, confirmation dialogs

### Medium Risk
- **User Confusion**: Too many options/modes could confuse users
  - *Mitigation*: Clear UI, contextual help, progressive disclosure

- **Performance**: Real-time calculations could lag on older devices
  - *Mitigation*: Debouncing, optimization, performance testing

### Low Risk
- **Sync Conflicts**: Calculation history conflicts are unlikely
  - *Mitigation*: Append-only design, proper sync error handling

---

## Success Metrics

### Usage Metrics
- Number of calculations performed per user per week
- Most-used calculator types
- Calculation history retention rate
- Integration usage (calculations from quantities)

### Quality Metrics
- Calculation accuracy (verified against known values)
- Bug reports related to calculators
- User feedback on ease of use
- Time saved vs manual calculations

### Performance Metrics
- Average calculation time (<100ms)
- Screen load time (<500ms)
- Sync success rate (>95%)
- App stability (no crashes)

---

## Dependencies

### New Packages Required
None - all calculations use built-in Dart math library

### Existing Packages Used
- `provider`: State management
- `go_router`: Navigation
- `sqflite`: Local storage
- `supabase_flutter`: Cloud sync
- `intl`: Number formatting
- `uuid`: ID generation

---

## Questions for User

Before implementation begins, please confirm:

1. **Priority**: Which calculators are most critical for your workflow? (This will determine implementation order)

2. **Density Values**: Do you have specific density values you use for HMA, concrete, or aggregates that differ from the standards listed?

3. **Units**: Do you primarily work in imperial (ft, yards, tons) or metric (m, cubic meters, kg)?

4. **Integration**: Is auto-populating calculators from material quantities a high priority, or can that be Phase 2?

5. **History**: Should calculation history sync to cloud or stay local-only initially?

6. **PDF**: Do you want calculation summaries included in daily entry PDF exports?

7. **Custom Calculators**: Do you have any project-specific calculation needs not covered by the standard set?

8. **User Roles**: Should certain calculators be restricted based on user roles, or available to all?

---

## Notes

- This is a comprehensive plan covering all aspects of the Inspector Toolbox feature
- Estimated timeline: 4 weeks with proper agent delegation
- Can be implemented in phases if needed (Core calculators first, then history/integration)
- All calculations follow industry-standard formulas and practices
- Offline-first design ensures field usability without internet
- Designed to integrate seamlessly with existing app architecture

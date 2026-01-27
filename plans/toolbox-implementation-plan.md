# Multi-Feature Implementation Plan

## Overview

Four features to implement:
1. **Auto-load last selected project** - Remember and load last project on app launch
2. **Pay items numeric sorting** - Fix "1, 10, 2" to be "1, 2, 10"
3. **Contractor dialog dropdown fix** - Fix Type dropdown clipping
4. **Toolbox** - Replace Locations card (RIGHT side) with Toolbox containing Forms, Calculator, Gallery, To-Do's

---

## Feature 1: Auto-Load Last Selected Project

### Problem
Dashboard shows no project when re-entering app. User wants last project auto-loaded.

### Solution
Create `ProjectSettingsProvider` following `ThemeProvider` pattern.

### Files

| File | Changes |
|------|---------|
| `lib/features/projects/presentation/providers/project_settings_provider.dart` | **CREATE** |
| `lib/features/projects/presentation/providers/project_provider.dart` | Save selected project ID |
| `lib/main.dart` | Register provider |
| `lib/features/dashboard/presentation/screens/dashboard_screen.dart` | Auto-load on init |
| `lib/features/settings/presentation/screens/settings_screen.dart` | Add toggle |

### Implementation

```dart
// project_settings_provider.dart
class ProjectSettingsProvider extends ChangeNotifier {
  static const String _lastProjectKey = 'last_selected_project_id';
  static const String _autoLoadKey = 'auto_load_last_project';

  String? _lastProjectId;
  bool _autoLoadEnabled = true;

  Future<void> setLastProject(String? projectId) async {
    _lastProjectId = projectId;
    final prefs = await SharedPreferences.getInstance();
    if (projectId != null) {
      await prefs.setString(_lastProjectKey, projectId);
    } else {
      await prefs.remove(_lastProjectKey);
    }
  }
}
```

---

## Feature 2: Pay Items Numeric Sorting

### Problem
`lib/features/quantities/presentation/providers/bid_item_provider.dart:29-31`:
```dart
items.sort((a, b) => a.itemNumber.compareTo(b.itemNumber)); // String comparison
```
Results in: "1, 10, 2, 20" instead of "1, 2, 10, 20"

### Solution
Natural sort comparison.

### Files

| File | Changes |
|------|---------|
| `lib/shared/utils/natural_sort.dart` | **CREATE** |
| `lib/features/quantities/presentation/providers/bid_item_provider.dart` | Use natural sort |

### Implementation

```dart
// natural_sort.dart
int naturalCompare(String a, String b) {
  final regExp = RegExp(r'(\d+)|(\D+)');
  final partsA = regExp.allMatches(a).map((m) => m.group(0)!).toList();
  final partsB = regExp.allMatches(b).map((m) => m.group(0)!).toList();

  for (int i = 0; i < partsA.length && i < partsB.length; i++) {
    final numA = int.tryParse(partsA[i]);
    final numB = int.tryParse(partsB[i]);
    int result;
    if (numA != null && numB != null) {
      result = numA.compareTo(numB);
    } else {
      result = partsA[i].compareTo(partsB[i]);
    }
    if (result != 0) return result;
  }
  return partsA.length.compareTo(partsB.length);
}
```

---

## Feature 3: Contractor Dialog Dropdown Fix

### Problem
Type dropdown clips in Add Contractor dialog (screenshot provided).

### Root Cause
`lib/features/projects/presentation/screens/project_setup_screen.dart:604-676`:
- `AlertDialog` with `Column(mainAxisSize: MainAxisSize.min)` clips dropdown overlay

### Solution
Wrap in `SingleChildScrollView`.

### Files

| File | Changes |
|------|---------|
| `lib/features/projects/presentation/screens/project_setup_screen.dart` | Fix `_showAddContractorDialog()` |

### Implementation

```dart
AlertDialog(
  content: SingleChildScrollView(  // ADD THIS
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        TextField(...),
        DropdownButtonFormField<ContractorType>(
          isExpanded: true,
          menuMaxHeight: 300,  // ADD THIS
          ...
        ),
      ],
    ),
  ),
)
```

---

## Feature 4: Toolbox

### Overview
Replace Locations card on dashboard (RIGHT side) with Toolbox card leading to:
- **Forms** - Inspector forms linked to Test Results, exportable with IDR
- **Calculator** - HMA yield, Concrete calcs, measurement calculator
- **Gallery** - All project photos
- **To-Do's** - Inspector notes/tasks

### User Priority
> "Start with 1 or 2 forms and get the data pathing right first"

---

### Phase 1: Foundation

#### Database Schema
**File**: `lib/core/database/database_service.dart`

```sql
-- Inspector Forms
CREATE TABLE inspector_forms (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  form_fields TEXT NOT NULL,  -- JSON
  is_active INTEGER DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Form Responses (links to daily_entries for Test Results)
CREATE TABLE form_responses (
  id TEXT PRIMARY KEY,
  form_id TEXT NOT NULL,
  entry_id TEXT,  -- Links to daily_entries.id
  project_id TEXT NOT NULL,
  response_data TEXT NOT NULL,  -- JSON
  submitted_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (form_id) REFERENCES inspector_forms(id) ON DELETE CASCADE,
  FOREIGN KEY (entry_id) REFERENCES daily_entries(id) ON DELETE SET NULL
);

-- Todo Items
CREATE TABLE todo_items (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  entry_id TEXT,
  title TEXT NOT NULL,
  description TEXT,
  is_completed INTEGER DEFAULT 0,
  due_date TEXT,
  priority INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Calculation History
CREATE TABLE calculation_history (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  entry_id TEXT,
  calculator_type TEXT NOT NULL,
  input_values TEXT NOT NULL,
  result_values TEXT NOT NULL,
  notes TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
```

#### Feature Structure
```
lib/features/toolbox/
├── data/
│   ├── models/
│   │   ├── inspector_form.dart
│   │   ├── form_response.dart
│   │   ├── todo_item.dart
│   │   └── calculation_history.dart
│   ├── datasources/local/
│   │   ├── form_local_datasource.dart
│   │   ├── todo_local_datasource.dart
│   │   └── calculation_history_local_datasource.dart
│   └── repositories/
│       ├── form_repository.dart
│       ├── todo_repository.dart
│       └── calculation_history_repository.dart
├── domain/calculators/
│   ├── hma_calculator.dart
│   └── concrete_calculator.dart
├── presentation/
│   ├── providers/
│   │   ├── form_provider.dart
│   │   ├── todo_provider.dart
│   │   └── calculator_provider.dart
│   ├── screens/
│   │   ├── toolbox_home_screen.dart
│   │   ├── forms_screen.dart
│   │   ├── form_detail_screen.dart
│   │   ├── calculator_screen.dart
│   │   ├── gallery_screen.dart
│   │   └── todos_screen.dart
│   └── widgets/
└── toolbox.dart (barrel)
```

#### Routing
**File**: `lib/core/router/app_router.dart`

```dart
GoRoute(
  path: '/toolbox',
  name: 'toolbox',
  builder: (context, state) => const ToolboxHomeScreen(),
  routes: [
    GoRoute(path: 'forms', name: 'toolbox-forms', ...),
    GoRoute(path: 'forms/:formId', name: 'toolbox-form-detail', ...),
    GoRoute(path: 'calculator', name: 'toolbox-calculator', ...),
    GoRoute(path: 'gallery', name: 'toolbox-gallery', ...),
    GoRoute(path: 'todos', name: 'toolbox-todos', ...),
  ],
),
```

#### Dashboard Modification
**File**: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`

Replace Locations card (RIGHT side, index 1 in grid) with Toolbox:
```dart
_buildStatCard(
  key: TestingKeys.dashboardToolboxCard,
  icon: Icons.build_circle_outlined,
  label: 'Toolbox',
  value: '',
  onTap: () => context.pushNamed('toolbox'),
),
```

**Note**: Locations feature remains accessible in Project Edit screen (contractor editing). Only the dashboard card is removed.

#### Supabase Schema (Full Sync)
**File**: `supabase/migrations/toolbox_schema.sql`

```sql
-- Inspector Forms
CREATE TABLE inspector_forms (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  template_path TEXT,
  form_fields JSONB NOT NULL,
  parsing_keywords JSONB,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

-- Form Responses
CREATE TABLE form_responses (
  id TEXT PRIMARY KEY,
  form_id TEXT NOT NULL REFERENCES inspector_forms(id) ON DELETE CASCADE,
  entry_id TEXT REFERENCES daily_entries(id) ON DELETE SET NULL,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  response_data JSONB NOT NULL,
  table_rows JSONB,
  is_open BOOLEAN DEFAULT true,
  submitted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

-- Todo Items
CREATE TABLE todo_items (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  entry_id TEXT REFERENCES daily_entries(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  description TEXT,
  is_completed BOOLEAN DEFAULT false,
  due_date TIMESTAMPTZ,
  priority INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

-- Calculation History
CREATE TABLE calculation_history (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  entry_id TEXT REFERENCES daily_entries(id) ON DELETE SET NULL,
  calculator_type TEXT NOT NULL,
  input_values JSONB NOT NULL,
  result_values JSONB NOT NULL,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL
);

-- Indexes
CREATE INDEX idx_form_responses_project ON form_responses(project_id);
CREATE INDEX idx_form_responses_entry ON form_responses(entry_id);
CREATE INDEX idx_todo_items_project ON todo_items(project_id);
CREATE INDEX idx_calc_history_project ON calculation_history(project_id);

-- RLS Policies (user-scoped via project ownership)
ALTER TABLE inspector_forms ENABLE ROW LEVEL SECURITY;
ALTER TABLE form_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE todo_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE calculation_history ENABLE ROW LEVEL SECURITY;
```

Register tables in sync orchestrator: `lib/features/sync/application/sync_orchestrator.dart`

---

### Phase 2: Forms (MDOT 1174R & 0582B)

#### PDF Templates
- **1174R** - Inspector's Report of Concrete Placed (Roadway)
- **0582B** - Moisture and Density Determination (Nuclear Method)

Templates at: `Pre-devolopment and brainstorming/Form Templates for export/`

#### Data Models
```dart
// inspector_form.dart
class InspectorForm {
  final String id;
  final String projectId;
  final String name;
  final String templatePath;  // PDF template file path
  final List<FormFieldDefinition> fields;
  final List<String> parsingKeywords;  // Keywords for smart parsing
  final bool isActive;
  final DateTime createdAt;
  final DateTime updatedAt;
}

class FormFieldDefinition {
  final String id;
  final String label;
  final String pdfFieldName;  // Maps to PDF form field
  final FormFieldType type;
  final bool required;
  final bool autoFill;  // True for project/entry data
  final String? autoFillSource;  // e.g., "project.controlSectionId"
  final List<String> keywords;  // For smart parsing
  final int sortOrder;
  final bool isTableRow;  // True for multi-row fields (tests)
}

// form_response.dart
class FormResponse {
  final String id;
  final String formId;
  final String? entryId;  // Links to DailyEntry
  final String projectId;
  final Map<String, dynamic> responseData;
  final List<Map<String, dynamic>> tableRows;  // Multi-row data (tests)
  final bool isOpen;  // True = actively being filled
  final DateTime? submittedAt;
  final DateTime createdAt;
  final DateTime updatedAt;
}
```

#### Hybrid Input UI (Test Results Section)

**Workflow:**
1. User opens Test Results section for an entry
2. User selects forms for the day (1174R and/or 0582B)
3. System creates "open" FormResponse instances linked to entry
4. **Hybrid Input**: Quick-entry text box + structured fields below
5. User types: `10:30 slump 4 air 5.5 temp 68/72 2cyl`
6. Parser extracts → shows in structured fields for confirmation
7. "Add Test" button saves row, clears for next test
8. On export: Fill PDF templates, save to export folder

#### Auto-Fill Fields (from project/entry data)
| PDF Field | Source |
|-----------|--------|
| Date | Entry date |
| Control Section ID | Project.controlSectionId |
| Job Number | Project.jobNumber |
| Route | Project.route |
| Contractor | Entry contractor |
| Weather | Entry weather data |
| Inspector | Settings.inspectorName |

#### Smart Parsing Keywords

**1174R Concrete:**
| Field | Keywords |
|-------|----------|
| Time | time, @, am, pm |
| Slump | slump, s: |
| Air Content | air, ac, % |
| Concrete Temp | concrete, conc, ct |
| Atmosphere Temp | atmosphere, atm, at |
| Cylinders | cyl, cylinder, beam |

**0582B Density:**
| Field | Keywords |
|-------|----------|
| Station | sta, station, + |
| Offset | offset, left, right, lt, rt, ft |
| Dry Density | dry, dd |
| Wet Density | wet, wd |
| Moisture | moisture, moist, m% |
| Max Density | max, md |

**Common fields fill BOTH forms:**
- Location, Date, Station → auto-fill on all open forms

#### Multi-Row Test Data (Add Test button)
- Each "Add Test" creates a new row in `tableRows`
- 1174R: Temperatures/Air/Slump table (multiple trucks)
- 0582B: In-place density table (multiple test locations)
- Auto-calculate: Percent Compaction = (Dry / Max) × 100

#### Calculator Integration (Item Measurements)
For 1174R Item table (Length × Width × Depth):
- Calculator auto-calculates Measured Sq/Cu Yards
- Shows Over/Under % based on Plan yards

#### PDF Export
- Use pdf-agent pattern to fill actual MDOT PDF templates
- Each form exports as separate PDF file
- Filenames saved to IDR attachments (like photos)

---

### Phase 3: Calculator

#### Domain Logic
```dart
// hma_calculator.dart
class HmaCalculator {
  /// Tonnage = (Area_SF x Thickness_in x Density_PCF) / (12 x 2000)
  static double calculateTonnage({
    required double areaSf,
    required double thicknessInches,
    double densityPcf = 145.0,
  }) => (areaSf * thicknessInches * densityPcf) / 24000;
}

// concrete_calculator.dart
class ConcreteCalculator {
  /// CY = (L x W x Thickness_in) / (12 x 27)
  static double calculateSlabVolume({
    required double lengthFt,
    required double widthFt,
    required double thicknessIn,
    double wasteFactor = 1.05,
  }) => (lengthFt * widthFt * thicknessIn) / 324 * wasteFactor;
}
```

#### Quantities Integration
Add "Calculate" button in quantities screen that opens calculator and returns result.

---

### Phase 4: Gallery

Reuse existing `PhotoProvider` from `lib/features/photos/`. Gallery screen shows grid of all project photos with filtering.

---

### Phase 5: To-Do's

Simple todo list with add/edit/delete, completion checkboxes, optional entry linking.

---

## Files Summary

### New Files
| File | Purpose |
|------|---------|
| `lib/features/projects/presentation/providers/project_settings_provider.dart` | Last project persistence |
| `lib/shared/utils/natural_sort.dart` | Numeric string sorting |
| `lib/features/toolbox/` (feature) | Toolbox feature |

### Modified Files
| File | Changes |
|------|---------|
| `lib/main.dart` | Register new providers |
| `lib/core/router/app_router.dart` | Add toolbox routes |
| `lib/core/database/database_service.dart` | Add tables, bump version |
| `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart` | Replace Locations with Toolbox (RIGHT) |
| `lib/features/projects/presentation/providers/project_provider.dart` | Persist selection |
| `lib/features/projects/presentation/screens/project_setup_screen.dart` | Fix dropdown |
| `lib/features/quantities/presentation/providers/bid_item_provider.dart` | Numeric sort |
| `lib/features/settings/presentation/screens/settings_screen.dart` | Auto-load toggle |
| `lib/shared/testing_keys.dart` | Toolbox keys |

---

## Implementation Order

### PR 1: Quick Fixes
- Pay items numeric sorting
- Contractor dialog dropdown fix

### PR 2: Auto-Load Project Setting
- ProjectSettingsProvider
- Dashboard auto-load
- Settings toggle

### PR 3: Toolbox Foundation
- SQLite schema (4 tables) + Supabase migration
- Feature folder structure
- Routing
- Dashboard card (RIGHT side, replaces Locations)
- ToolboxHomeScreen with 4 cards
- Sync orchestrator registration

### PR 4: Forms Data Layer
- InspectorForm, FormResponse models
- Datasources, repositories, providers
- MDOT form templates (1174R, 0582B) as built-in data

### PR 5: Forms UI + Smart Parsing
- FormsScreen (select forms for day)
- Hybrid input UI (text box + structured fields)
- Smart parsing engine with keywords
- Add Test button for multi-row data
- Auto-fill from project/entry data

### PR 6: Forms PDF Export
- PDF template filling (pdf-agent pattern)
- Export to folder as separate PDF files
- Add filenames to IDR attachments section

### PR 7: Calculator
- HMA, Concrete calculators
- CalculatorScreen
- Item measurements integration (auto-calc cubic yards)
- Quantities screen integration

### PR 8: Gallery & To-Do's
- GalleryScreen (reuse PhotoProvider)
- TodoItem model, provider
- TodosScreen

---

## Verification

### Feature 1: Auto-Load Project
1. Select project, close app
2. Reopen → last project auto-loaded
3. Settings → disable toggle → reopen → no project selected

### Feature 2: Pay Items Sorting
1. Create items: "1", "2", "10", "20"
2. List shows: 1, 2, 10, 20 (not 1, 10, 2, 20)

### Feature 3: Contractor Dialog
1. Add Contractor → dropdown expands properly, no clipping

### Feature 4: Toolbox
1. Dashboard → Toolbox card on RIGHT side (Locations card gone)
2. Tap → 4 cards (Forms, Calculator, Gallery, To-Do's)

### Feature 4a: Forms
1. Open entry → Test Results → Select "1174R Concrete"
2. Auto-fill shows: Date, Control Section, Route, Contractor, Weather
3. Type: `10:30 slump 4 air 5.5 temp 68/72 2cyl`
4. Parser shows structured fields: Time=10:30, Slump=4", Air=5.5%, etc.
5. Click "Add Test" → row added, input clears
6. Repeat for more truck arrivals
7. Export → PDF filled with data, saved to export folder
8. IDR attachments section shows form filename

### Feature 4b: Calculator
1. Open Calculator → HMA/Concrete options
2. Enter dimensions → auto-calculate cubic yards
3. From Item measurements → Calculator → result returns to form

### Feature 4c: Gallery
1. Open Gallery → shows all project photos in grid
2. Filter by date/entry works

### Feature 4d: To-Do's
1. Add todo → appears in list
2. Mark complete → moves to completed section
3. Link to entry (optional) works

---

## Testing Impact

### Existing Tests Affected
| Test Area | Impact |
|-----------|--------|
| Dashboard tests | Update for Toolbox card (was Locations) |
| Pay items tests | Verify no tests assume lexicographic order |
| Contractor dialog | Should pass; add assertion for dropdown |

### New Tests Needed
| Area | Type | Coverage |
|------|------|----------|
| `natural_sort.dart` | Unit | Edge cases: "1a", "a1", "10.5" |
| `HmaCalculator` | Unit | Known-value formula verification |
| `ConcreteCalculator` | Unit | Known-value formula verification |
| Smart parsing | Unit | Each keyword pattern, edge cases |
| Form data layer | Unit | CRUD, JSON serialization |
| ToolboxHomeScreen | Widget | Card navigation, project scoping |
| Hybrid input UI | Widget | Text parsing → structured fields |
| PDF export | Integration | Fill template, verify fields |

### Run Commands
```bash
# All tests
flutter test

# Specific feature
flutter test test/features/toolbox/

# Check analyzer
flutter analyze
```

# Form Filling Streamline Plan

**Created**: 2026-01-28 | **Status**: Draft
**Goal**: Eliminate repeated data entry, enable live PDF preview, add density calculations, and make adding new forms near-zero effort.

---

## PDF Library: Syncfusion (FREE)

**Status**: Keep using Syncfusion - you qualify for the **Community License** (free).

Syncfusion Community License requirements:
- Individual developers or companies with < $1M annual revenue
- ≤ 5 developers using Syncfusion products
- ≤ 10 total employees

**Since you're developing this personally** (not as work product for your employer), **you qualify as an individual developer**. No changes needed to the current PDF approach.

---

## Problem Summary

| Pain Point | Impact |
|-----------|--------|
| Plain TextFormFields in a scrollable list | Can't see what the actual PDF looks like while filling |
| Only 5 fields auto-filled via hardcoded switch | Repeated manual entry of project/inspector/date/contractor on every form |
| No centralized field registry | Adding a new form means manually mapping every PDF field name |
| Field definitions are hardcoded JSON in seed service | No way to query "which fields can be auto-filled across all forms" |
| No PDF preview during editing | "Guesswork" -- fill, export, check, go back, fix |
| **0582B density calculations manual** | Inspector must manually calculate dry density, moisture %, compaction % |

---

## Phase 1: Form Field Registry (PR 10)

**Goal**: Single source of truth for every PDF field across all templates.

### New SQLite Table: `form_field_registry` (DB version 14)

```sql
CREATE TABLE form_field_registry (
  id TEXT PRIMARY KEY,
  form_id TEXT NOT NULL,
  pdf_field_name TEXT NOT NULL,        -- Actual AcroForm name: "JOB NUMBER", "Text1.0.0"
  semantic_name TEXT NOT NULL,          -- Canonical name: "project_number"
  category TEXT NOT NULL,               -- FieldCategory enum value
  field_type TEXT NOT NULL DEFAULT 'text',
  label TEXT,
  is_required INTEGER NOT NULL DEFAULT 0,
  is_auto_fillable INTEGER NOT NULL DEFAULT 0,
  auto_fill_source TEXT,                -- e.g., "project.projectNumber"
  sort_order INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (form_id) REFERENCES inspector_forms(id) ON DELETE CASCADE,
  UNIQUE(form_id, pdf_field_name)
);
```

### New Table: `field_semantic_aliases`

Maps aliases so "project_number", "job_number", and "control_section_id" all resolve to the same auto-fill source.

```sql
CREATE TABLE field_semantic_aliases (
  id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  alias_name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(alias_name)
);
```

### New Model: `FormFieldEntry`

```dart
enum FieldCategory {
  projectInfo,    // project_number, project_name, control_section
  inspectorInfo,  // inspector, certification_number, inspector_phone
  dateTime,       // date, inspector_date
  location,       // location, route, structure_number
  contractor,     // contractor, subcontractor, concrete_supplier
  weather,        // weather_am, weather_pm
  testData,       // slump, air_content, temperature, wet_density
  equipment,      // gauge_number
  notes,          // comments, notes, remarks
  calculated,     // percent_compaction (derived)
  other,
}
```

### New Files
| File | Purpose |
|------|---------|
| `lib/features/toolbox/data/models/form_field_entry.dart` | Model + FieldCategory enum |
| `lib/features/toolbox/data/models/field_semantic_alias.dart` | Alias model |
| `lib/features/toolbox/data/datasources/local/form_field_registry_datasource.dart` | SQLite datasource |
| `lib/features/toolbox/data/repositories/form_field_registry_repository.dart` | Repository |
| `lib/features/toolbox/data/services/field_registry_service.dart` | Populate from JSON, query by form/category |

### Modified Files
| File | Change |
|------|--------|
| `lib/core/database/database_service.dart` | Version 14 migration |
| `lib/features/toolbox/data/models/models.dart` | Barrel exports |

### Migration Strategy
- Additive only (new tables, no existing data changed)
- On migration, populate registry from existing `fieldDefinitions` JSON
- Seed alias table with known aliases

---

## Phase 2: Smart Auto-Fill Engine (PR 11)

**Goal**: Replace 5-field switch statement with data-driven engine. Auto-fill 20-25 fields.

### New Service: `AutoFillEngine`

```dart
class AutoFillContext {
  final Project? project;
  final DailyEntry? entry;
  final Contractor? primeContractor;
  final List<Contractor> subcontractors;
  final Location? location;
  final String? inspectorName;
  final String? inspectorPhone;
  final String? certificationNumber;
  final String? weatherAm;
  final String? weatherPm;
}

class AutoFillResult {
  final Map<String, String> filledValues;    // fieldName -> value
  final Map<String, String> fillSources;     // fieldName -> "From project"
  final List<String> unfillableFields;        // need manual entry
}

class AutoFillEngine {
  Future<AutoFillResult> autoFill(String formId, AutoFillContext context);
}
```

### Auto-Fill Source Mapping

| Category | # Fields | Data Source |
|----------|----------|------------|
| Project | 6+ | `Project` model (projectNumber, name, clientName, mdotContractId, mdotProjectCode, mdotCounty, mdotDistrict) |
| Inspector | 4 | SharedPreferences (name, phone, certNumber, agency) |
| Date | 2 | `DateTime.now()` or entry date |
| Location | 2 | `Location` model (name, description) |
| Contractor | 3 | `Contractor` model (prime name, sub name, supplier) |
| Weather | 2 | Entry weather or weather API |
| **Total** | **~20** | **vs. current 5** |

### Visual Indicator
Auto-filled fields get a small "auto-filled" chip next to the label showing the source (e.g., "From project"). Users see instantly what was filled and where it came from.

### New Files
| File | Purpose |
|------|---------|
| `lib/features/toolbox/data/services/auto_fill_engine.dart` | Engine + context + result |

### Modified Files
| File | Change |
|------|--------|
| `form_fill_screen.dart` | Replace `_autoFillFromContext` switch with engine call |
| `form_seed_service.dart` | Set `auto_fill_source` for all builtin fields |

---

## Phase 2B: Density Calculator Service (PR 11.5)

**Goal**: Auto-calculate derived fields on MDOT 0582B Density form (and future forms with formulas).

### Nuclear Density Gauge Formulas (AASHTO T310 / MDOT)

The 0582B form has built-in formulas. Instead of manually charting values, the app will calculate them.

**Input Fields** (from nuclear gauge or Proctor test):
| Field | Source | Unit |
|-------|--------|------|
| Wet Density | Nuclear gauge readout | PCF (lb/ft³) |
| Moisture | Nuclear gauge readout | PCF |
| Max Density | Proctor test (AASHTO T99/T180) or JMF | PCF |

**Calculated Fields** (auto-computed):
| Field | Formula | Unit |
|-------|---------|------|
| **Dry Density** | `Wet Density - Moisture (PCF)` | PCF |
| **Dry Density (alt)** | `Wet Density / (1 + Moisture%/100)` | PCF |
| **Moisture %** | `(Moisture PCF / Dry Density) × 100` | % |
| **% Compaction** | `(Dry Density / Max Density) × 100` | % |

### Calculation Example

```
Given:
  Wet Density = 135.0 PCF (from gauge)
  Moisture    = 15.0 PCF  (from gauge)
  Max Density = 125.0 PCF (from Proctor)

Calculate:
  Dry Density    = 135.0 - 15.0 = 120.0 PCF
  Moisture %     = (15.0 / 120.0) × 100 = 12.5%
  % Compaction   = (120.0 / 125.0) × 100 = 96.0%
```

### New Service: `DensityCalculatorService`

```dart
class DensityCalculatorService {
  /// Calculate dry density from wet density and moisture.
  double calculateDryDensity({
    required double wetDensity,
    required double moisturePcf,
  }) => wetDensity - moisturePcf;

  /// Calculate dry density using moisture percentage.
  double calculateDryDensityFromPercent({
    required double wetDensity,
    required double moisturePercent,
  }) => wetDensity / (1 + moisturePercent / 100);

  /// Calculate moisture percentage.
  double calculateMoisturePercent({
    required double moisturePcf,
    required double dryDensity,
  }) => (moisturePcf / dryDensity) * 100;

  /// Calculate percent compaction.
  double calculateCompaction({
    required double dryDensity,
    required double maxDensity,
  }) => (dryDensity / maxDensity) * 100;

  /// Calculate all derived values for a density test.
  DensityTestResult calculateAll({
    required double wetDensity,
    required double moisturePcf,
    required double maxDensity,
  });
}

class DensityTestResult {
  final double wetDensity;
  final double moisturePcf;
  final double dryDensity;
  final double moisturePercent;
  final double maxDensity;
  final double percentCompaction;
  final bool passesSpec; // true if compaction >= 95% (configurable)
}
```

### Form Field Calculation Integration

Add to `FormFieldEntry` model:
```dart
class FormFieldEntry {
  // ... existing fields ...

  /// Formula to calculate this field from other fields.
  /// Format: "calculated:formula_name" or "calculated:field1 + field2"
  final String? calculationFormula;

  /// Fields this calculation depends on (for triggering recalc).
  final List<String>? dependsOn;
}
```

### 0582B Form Field Definitions (Updated)

```dart
// Add calculated fields to MDOT 0582B Density form
{
  'name': 'dry_density',
  'type': 'number',
  'pdfField': 'DRY DENSITY',
  'label': 'Dry Density (PCF)',
  'calculationFormula': 'wet_density - moisture_pcf',
  'dependsOn': ['wet_density', 'moisture_pcf'],
},
{
  'name': 'moisture_percent',
  'type': 'number',
  'pdfField': 'MOISTURE %',
  'label': 'Moisture %',
  'calculationFormula': '(moisture_pcf / dry_density) * 100',
  'dependsOn': ['moisture_pcf', 'dry_density'],
},
{
  'name': 'percent_compaction',
  'type': 'number',
  'pdfField': 'COMPACTION %',
  'label': '% Compaction',
  'calculationFormula': '(dry_density / max_density) * 100',
  'dependsOn': ['dry_density', 'max_density'],
},
```

### UI Integration

When a field with dependencies changes:
1. Identify all fields that depend on it
2. Recalculate those fields using `DensityCalculatorService`
3. Update the field values and trigger UI refresh
4. Show calculated fields with a "calculator" icon to indicate auto-computed

### New Files
| File | Purpose |
|------|---------|
| `lib/features/toolbox/data/services/density_calculator_service.dart` | Nuclear gauge formulas |
| `lib/features/toolbox/data/services/form_calculation_service.dart` | Generic calculated field engine |

### Modified Files
| File | Change |
|------|--------|
| `form_fill_screen.dart` | Add real-time calculation on field change |
| `form_seed_service.dart` | Add calculated field definitions to 0582B |
| `form_field_entry.dart` | Add `calculationFormula` and `dependsOn` fields |

### Sources
- [MDOT 0582B Form](https://mdotjboss.state.mi.us/webforms/GetDocument.htm?fileName=0582B.pdf)
- [AASHTO T310 Standard](https://wsdot.wa.gov/publications/manuals/fulltext/m46-01/t310.pdf)
- [APNGA Gauge Basics](https://www.apnga.com/gauge-basics/)
- [NY DOT GTM-10b](https://www.dot.ny.gov/divisions/engineering/technical-services/technical-services-repository/GTM-10b.pdf)

---

## Phase 3: PDF Preview UI (PR 12)

**Goal**: See the actual filled PDF while editing -- no more guesswork.

### Approach: Tabbed View

Mobile screen is too small for side-by-side. Use tabs:

- **Tab 1: "Fields"** -- form fields, quick entry, table rows (existing UI, cleaned up)
- **Tab 2: "Preview"** -- live PDF rendered from current field values

### Preview Implementation

Uses existing `FormPdfService.generateFormPdf()` + `printing` package's `PdfPreview` widget (already in pubspec). Zero new dependencies.

### Refresh Strategy
1. **Manual refresh button** in preview tab app bar (primary)
2. **Auto-refresh on tab switch** if unsaved changes exist
3. Future: debounced auto-refresh (500ms after last keystroke)

### Screen Refactor

Split the 1180-line `form_fill_screen.dart` into:

| Widget | Purpose | Est. Lines |
|--------|---------|-----------|
| `form_fill_screen.dart` | Shell: TabBarView, state | ~300 |
| `form_fields_tab.dart` | Fields, quick entry, rows | ~500 |
| `form_preview_tab.dart` | PDF preview + refresh | ~150 |
| `form_fill_widgets.dart` | Shared: status card, chips | ~200 |

### New Files
| File | Purpose |
|------|---------|
| `lib/features/toolbox/presentation/widgets/form_fields_tab.dart` | Extracted fields tab |
| `lib/features/toolbox/presentation/widgets/form_preview_tab.dart` | PDF preview tab |
| `lib/features/toolbox/presentation/widgets/form_fill_widgets.dart` | Shared widgets |

### Modified Files
| File | Change |
|------|--------|
| `form_fill_screen.dart` | Refactor to tabbed layout |

---

## Phase 4: Scalable Form Import (PR 13)

**Goal**: Adding a new MDOT form = drop in a PDF + confirm field mappings.

### Field Discovery Service

Scans a PDF template and auto-suggests semantic mappings:

```dart
class FieldDiscoveryService {
  Future<List<DiscoveredField>> discoverFields(Uint8List pdfBytes);
  List<FormFieldEntry> matchToSemantics(String formId, List<DiscoveredField> discovered);
}
```

### Heuristic Matching (layered confidence)

| Strategy | Confidence | Example |
|----------|-----------|---------|
| Exact alias match | 1.0 | "JOB NUMBER" in alias table |
| Normalized match | 0.9 | "job_number" == "JOBNUMBER" |
| Keyword containment | 0.7 | Field contains "date" |
| MDOT pattern match | 0.5 | "TextN.N.N" positional guess |
| Unmatched | 0.0 | Falls to `FieldCategory.other` |

### Form Import Workflow
1. User taps "Import Form" on forms list
2. Picks a PDF from device storage
3. System scans all AcroForm fields
4. "Field Mapping Screen" shows each field with:
   - PDF field name (read-only)
   - Suggested semantic name (editable dropdown)
   - Category (editable)
   - Auto-fill toggle + source dropdown
5. User confirms -- system creates `InspectorForm` + registry entries

### New Files
| File | Purpose |
|------|---------|
| `lib/features/toolbox/data/services/field_discovery_service.dart` | PDF scanner + heuristic matcher |
| `lib/features/toolbox/presentation/screens/form_import_screen.dart` | Import flow |
| `lib/features/toolbox/presentation/screens/field_mapping_screen.dart` | Field-by-field mapping UI |

### Modified Files
| File | Change |
|------|--------|
| `forms_list_screen.dart` | Add "Import Form" button |
| `app_router.dart` | New routes for import/mapping screens |

---

## Phase 5: Integration & Polish (PR 14)

**Goal**: Wire everything together, expand user profile, ensure backward compat.

### Inspector Profile Expansion

Add to Settings screen (stored in SharedPreferences):
- `inspector_name` (existing)
- `inspector_phone` (new)
- `inspector_certification_number` (new)
- `inspector_agency` (new)

Enter once, auto-fill everywhere.

### Backward Compatibility
- `InspectorForm.fieldDefinitions` JSON kept and still populated
- `FormPdfService` reads from registry with fallback to JSON
- Existing `FormResponse.responseData` format unchanged
- Old forms created before registry still work

### New Files
| File | Purpose |
|------|---------|
| `lib/features/toolbox/presentation/providers/form_fill_provider.dart` | Extracted state management |

### Modified Files
| File | Change |
|------|--------|
| `settings_screen.dart` | Add inspector profile fields |
| `form_seed_service.dart` | v3: populate registry + aliases |
| `form_pdf_service.dart` | Use registry as primary field source |
| `main.dart` | Wire new providers and services |

---

## PR Dependency Chain

```
PR 10 (Registry) ─── foundation for everything
  │
  ├──> PR 11 (Auto-Fill Engine) ─── uses registry queries
  │       │
  │       ├──> PR 11.5 (Density Calculator) ─── extends calculated fields
  │       │
  │       └──> PR 12 (Preview UI) ─── shows auto-filled + calculated fields
  │               │
  └──────────────>├──> PR 13 (Form Import) ─── uses registry + discovery
                  │
                  └──> PR 14 (Integration) ─── wires everything together
```

---

## Testing Strategy

| PR | Test Focus | Est. Tests |
|----|-----------|-----------|
| 10 | FormFieldEntry model serialization, FieldCategory enum, registry CRUD, alias resolution | 15-20 |
| 11 | All 20+ resolver mappings, partial context handling, no-overwrite rule | 10-15 |
| 11.5 | Density formulas: dry density, moisture %, compaction %, edge cases (division by zero) | 10-15 |
| 12 | Tab rendering, preview generation, tab-switch refresh | 5-10 |
| 13 | Field discovery accuracy, heuristic confidence, import flow | 10-15 |
| 14 | End-to-end: create form -> auto-fill -> preview -> export | 5-10 |

### Key Test Scenarios
1. Given full context, all auto-fillable fields are populated
2. Given partial context (no contractor), only non-contractor fields filled
3. Fields with existing values are never overwritten by auto-fill
4. Forms created before registry still work (backward compat)
5. Preview bytes generated successfully from current field values
6. Known MDOT PDFs produce correct discovered field counts
7. **Density calculations**: Given wet=135, moisture=15, max=125 → dry=120, moisture%=12.5, compaction=96.0
8. **Calculation chain**: Changing wet_density triggers recalculation of dry_density, moisture%, compaction%

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| PDF generation slow on mobile for preview | Manual refresh only, cache bytes, dispose documents immediately |
| 100+ fields in complex forms | Group by category in mapping screen, show summary counts |
| Heuristic false positives | Always require user confirmation, show confidence scores |
| Migration complexity | Additive-only (new tables), no existing data modified |

---

## Complete File Inventory

### New Files (15)
```
lib/features/toolbox/data/models/form_field_entry.dart          (PR 10)
lib/features/toolbox/data/models/field_semantic_alias.dart       (PR 10)
lib/features/toolbox/data/datasources/local/form_field_registry_datasource.dart  (PR 10)
lib/features/toolbox/data/repositories/form_field_registry_repository.dart       (PR 10)
lib/features/toolbox/data/services/field_registry_service.dart   (PR 10)
lib/features/toolbox/data/services/auto_fill_engine.dart         (PR 11)
lib/features/toolbox/data/services/density_calculator_service.dart   (PR 11.5)
lib/features/toolbox/data/services/form_calculation_service.dart     (PR 11.5)
lib/features/toolbox/presentation/widgets/form_fields_tab.dart   (PR 12)
lib/features/toolbox/presentation/widgets/form_preview_tab.dart  (PR 12)
lib/features/toolbox/presentation/widgets/form_fill_widgets.dart (PR 12)
lib/features/toolbox/data/services/field_discovery_service.dart  (PR 13)
lib/features/toolbox/presentation/screens/form_import_screen.dart    (PR 13)
lib/features/toolbox/presentation/screens/field_mapping_screen.dart  (PR 13)
lib/features/toolbox/presentation/providers/form_fill_provider.dart  (PR 14)
```

### Modified Files (11)
```
lib/core/database/database_service.dart              (PR 10)
lib/features/toolbox/data/models/models.dart          (PR 10)
lib/features/toolbox/data/models/form_field_entry.dart            (PR 11.5 - add calculationFormula, dependsOn)
lib/features/toolbox/data/datasources/local/local_datasources.dart (PR 10)
lib/features/toolbox/presentation/screens/form_fill_screen.dart     (PR 11, 11.5, 12)
lib/features/toolbox/data/services/form_seed_service.dart           (PR 11, 11.5, 14)
lib/features/toolbox/data/services/form_pdf_service.dart            (PR 14)
lib/features/toolbox/presentation/screens/forms_list_screen.dart    (PR 13)
lib/features/settings/presentation/screens/settings_screen.dart     (PR 14)
lib/main.dart                                                        (PR 14)
lib/core/router/app_router.dart                                      (PR 13)
```

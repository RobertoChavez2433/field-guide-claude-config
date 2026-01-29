# Form Completion Debug - Implementation Plan

**Created**: 2026-01-29
**Status**: READY
**Session**: 198

## Overview

Fix three issues discovered during Windows desktop testing:
1. Blank screen when app reloads into last saved project
2. FormFillScreen UI too cluttered - hard to identify fields needing input
3. Auto-fill not working - fields remain empty

---

## Issue 1: Blank Screen on Project Restore

### Root Cause

Race condition in `lib/main.dart:365-378`:
- `loadProjects().then()` executes asynchronously
- Provider returns immediately BEFORE `selectedProject` is set
- Screens render with `selectedProject == null` showing blank state
- ~200ms later, project loads and screen updates (visible flicker)

### Solution

Add `isRestoringProject` flag to `ProjectProvider` to show loading state instead of blank state during project restoration.

### Files to Modify

| File | Change |
|------|--------|
| `lib/features/projects/presentation/providers/project_provider.dart` | Add `isRestoringProject` flag |
| `lib/main.dart:365-378` | Set flag before/after restoration |
| `lib/features/entries/presentation/screens/home_screen.dart:648-654` | Check flag, show loading |
| `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:54-56` | Check flag, show loading |

### Implementation Steps

1. **Add flag to ProjectProvider**:
```dart
bool _isRestoringProject = false;
bool get isRestoringProject => _isRestoringProject;

void setRestoringProject(bool value) {
  _isRestoringProject = value;
  notifyListeners();
}
```

2. **Update main.dart** (lines 365-378):
```dart
provider.loadProjects().then((_) {
  if (projectSettingsProvider.autoLoadEnabled &&
      projectSettingsProvider.lastProjectId != null) {
    provider.setRestoringProject(true);  // ADD
    final project = provider.getProjectById(
      projectSettingsProvider.lastProjectId!,
    );
    if (project != null) {
      provider.setSelectedProject(project);
    } else {
      projectSettingsProvider.setLastProjectId(null);
    }
    provider.setRestoringProject(false);  // ADD
  }
});
```

3. **Update home_screen.dart** (line 648):
```dart
if (projectProvider.isRestoringProject) {
  return const Center(child: CircularProgressIndicator());
}
if (projectProvider.projects.isEmpty) {
  return _buildNoProjectsState();
}
```

4. **Update project_dashboard_screen.dart** (line 54):
```dart
if (projectProvider.isRestoringProject) {
  return const Center(child: CircularProgressIndicator());
}
if (project == null) {
  return _buildNoProjectSelected();
}
```

### Risk: Low
- Simple flag addition with no side effects
- Only affects startup sequence

---

## Issue 2: FormFillScreen UI Clutter

### Root Cause

All 25 fields displayed linearly without categorization. The data model already has:
- `isAutoFillable: bool` - Whether field can be auto-filled
- `autoFillSource: AutoFillSource?` - Data source (8 enum values)
- `category: String?` - Semantic grouping
- `isRequired: bool` - Required fields

But the UI doesn't use this metadata for filtering or grouping.

### Solution

Add a "Show Only Manual Fields" toggle that filters out auto-filled fields, showing only fields that need user input.

### Files to Modify

| File | Change |
|------|--------|
| `lib/features/toolbox/presentation/screens/form_fill_screen.dart` | Add filter toggle state |
| `lib/features/toolbox/presentation/widgets/form_fields_tab.dart` | Filter field list |
| `lib/features/toolbox/presentation/widgets/form_fields_config.dart` | Pass filter flag |

### Implementation Steps

1. **Add state in form_fill_screen.dart**:
```dart
bool _showOnlyManualFields = true;  // Default to simplified view
```

2. **Add toggle in app bar or field list header**:
```dart
SwitchListTile(
  title: const Text('Show only fields needing input'),
  value: _showOnlyManualFields,
  onChanged: (value) => setState(() => _showOnlyManualFields = value),
)
```

3. **Pass to FormFieldsConfig**:
```dart
FormFieldsConfig(
  // ... existing params
  showOnlyManualFields: _showOnlyManualFields,
)
```

4. **Filter in form_fields_tab.dart** (lines 59-97):
```dart
final displayFields = fieldsConfig.showOnlyManualFields
    ? fieldsConfig.fields.where((field) {
        final fieldName = field['name'] as String;
        final entry = fieldsConfig.fieldEntries
            .where((e) => e.fieldName == fieldName)
            .firstOrNull;
        // Show if: not auto-fillable, OR auto-fillable but empty
        if (entry == null || !entry.isAutoFillable) return true;
        final controller = fieldsConfig.fieldControllers[fieldName];
        return controller?.text.isEmpty ?? true;
      }).toList()
    : fieldsConfig.fields;

// Use displayFields instead of fieldsConfig.fields in map()
```

### Risk: Low
- UI-only change with existing data
- Easily reversible with toggle

---

## Issue 3: Auto-Fill Not Working

### Root Cause

Fields loaded from registry have `isAutoFillable = false` and `autoFillSource = null`.

**Evidence from logs**:
- `[FormFill] Loaded 25 fields from registry` - Fields ARE loaded
- But ALL fields skip at line 106 in `auto_fill_engine.dart`:
  `if (!field.isAutoFillable || field.autoFillSource == null) continue;`

**The JSON seed files are missing auto-fill configuration.**

### Solution

1. Update form JSON seed files with auto-fill configuration
2. Add debug logging to auto_fill_engine.dart for visibility

### Files to Modify

| File | Change |
|------|--------|
| `assets/forms/mdot_0582b_density.json` | Add auto-fill config to fields |
| `assets/forms/mdot_1174r_concrete.json` | Add auto-fill config to fields |
| `lib/features/toolbox/services/field_registry_service.dart` | Parse auto-fill config |
| `lib/features/toolbox/data/services/auto_fill_engine.dart` | Add debug logging |

### Implementation Steps

#### Step 1: Update JSON Field Definitions

Current format (missing auto-fill):
```json
{
  "fieldName": "project_number",
  "label": "Project Number",
  "isRequired": true
}
```

Updated format:
```json
{
  "fieldName": "project_number",
  "label": "Project Number",
  "isRequired": true,
  "isAutoFillable": true,
  "autoFillSource": "project"
}
```

#### Step 2: Map auto-fill sources

| Field | Source |
|-------|--------|
| project_number, control_section_id, job_number, route_number | `project` |
| density_inspector, certification_number, inspector_phone | `inspectorProfile` |
| date | `entry` |
| agency_company | `contractor` |
| station, offset, elevation | `location` |
| material_type | `carryForward` |

#### Step 3: Update field_registry_service.dart

Ensure JSON parsing includes auto-fill fields:
```dart
FormFieldEntry(
  // ... existing
  isAutoFillable: json['isAutoFillable'] as bool? ?? false,
  autoFillSource: json['autoFillSource'] != null
      ? AutoFillSource.values.byName(json['autoFillSource'] as String)
      : null,
)
```

#### Step 4: Add debug logging to auto_fill_engine.dart

At start of `autoFill()`:
```dart
debugPrint('[AutoFill] Processing ${fields.length} fields');
```

At line 106-108:
```dart
if (!field.isAutoFillable || field.autoFillSource == null) {
  debugPrint('[AutoFill] Skipping ${field.fieldName}: isAutoFillable=${field.isAutoFillable}, source=${field.autoFillSource}');
  continue;
}
```

At line 135-136:
```dart
if (result != null) {
  debugPrint('[AutoFill] Filled ${field.fieldName} from ${field.autoFillSource}: ${result.value}');
  results[field.fieldName] = result;
}
```

At end:
```dart
debugPrint('[AutoFill] Results: ${results.length} filled, ${unfilled.length} unfilled');
```

### Risk: Medium
- Requires database migration if fields already seeded
- May need to clear app data or re-seed forms

---

## Execution Order

1. **Issue 1**: Blank Screen Fix (easiest, no data changes)
2. **Issue 2**: UI Filter Toggle (UI-only, easily testable)
3. **Issue 3**: Auto-Fill Configuration (requires data updates)

---

## Testing Verification

### Issue 1: Blank Screen
- [ ] Cold start app with auto-load enabled
- [ ] Verify loading indicator shows briefly
- [ ] Verify no blank "Select Project" state flashes
- [ ] Verify project content appears correctly

### Issue 2: UI Filter
- [ ] Open form fill screen
- [ ] Toggle "Show only manual fields"
- [ ] Verify auto-filled fields hide when toggle ON
- [ ] Verify all fields show when toggle OFF
- [ ] Verify toggle state persists during session

### Issue 3: Auto-Fill
- [ ] Clear app data: `adb shell pm clear com.fvconstruction.construction_inspector`
- [ ] Launch app, select project
- [ ] Open MDOT 0582B Density form
- [ ] Verify Project Number auto-fills
- [ ] Verify Date auto-fills
- [ ] Verify Inspector fields auto-fill
- [ ] Check debug logs show auto-fill activity

---

## Agent Assignment

| Issue | Agent |
|-------|-------|
| Issue 1 | `flutter-specialist-agent` |
| Issue 2 | `flutter-specialist-agent` |
| Issue 3 | `data-layer-agent` (JSON/seeding) + `flutter-specialist-agent` (logging) |

---

## Success Criteria

1. No blank screen flicker on app startup with saved project
2. FormFillScreen shows toggle to simplify field view
3. Auto-fill populates project/inspector/date fields correctly
4. Debug logs show auto-fill activity for troubleshooting
5. Zero new analyzer errors
6. No regressions in existing functionality

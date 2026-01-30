# Implementation Plan: Composite Field Type for "Dist from C/L"

**Last Updated**: 2026-01-29
**Status**: READY
**Issue**: Issue 3 Option A - Composite Field Type

## Overview

Create a reusable composite field type that displays a single label with multiple stacked inputs underneath. First use case: "Dist from C/L" with Left/Right inputs to replace separate `dist_left` and `dist_right` fields.

## Current State Analysis

### Existing Architecture
1. **Field Definition** (`lib/features/toolbox/data/models/form_field_entry.dart`)
   - Current field types: text, textarea, checkbox, radio, dropdown, date, signature
   - Each field maps to a single PDF field via `pdfFieldName`
   - Fields are defined in JSON with type, label, pdfField properties

2. **Field Rendering** (`lib/features/toolbox/presentation/widgets/dynamic_form_field.dart`)
   - `DynamicFormField` widget renders based on field type
   - Switch statement handles different field types
   - Each field has one controller, one label, one PDF mapping

3. **Table Row System** (Already handles multiple inputs!)
   - `TableColumnConfig` in `density_grouped_entry_section.dart` defines columns with `pdfPrefix`
   - Each column renders as separate TextField with its own controller
   - Columns are arranged in left/right layout via `entryLayout`
   - PDF mapping: `{pdfPrefix}{rowNum}` (e.g., "12Row1", "13Row1")

4. **Current "Dist from C/L" Implementation**
   - Two separate fields in JSON (lines 169-170):
     - `dist_left`: label "Dist from C/L (L)", maps to "12Row"
     - `dist_right`: label "Dist from C/L (R)", maps to "13Row"
   - Both listed separately in `entryLayout.rightColumn`

### Key Insight
The table row system ALREADY implements the core composite field concept:
- Single group label → Multiple fields underneath
- Multiple controllers → Multiple PDF mappings
- Layout control → Stacked arrangement

We can adapt this pattern for **top-level form fields** (not just table rows).

## Design Decision

### Option A: New Field Type "composite" (RECOMMENDED)
Add a new field type that allows nested sub-fields.

**Pros**:
- Clean JSON schema
- Reusable pattern
- Self-documenting

**Cons**:
- More code changes
- New enum value

### Option B: Field Metadata Flag
Add `compositeFields: []` array to existing field definitions.

**Pros**:
- Minimal changes

**Cons**:
- Less intuitive
- Harder to validate

**DECISION**: Use Option A (new field type) for clarity and reusability.

## Detailed Design

### 1. JSON Schema (Form Definition)

**Before** (`mdot_0582b_density.json:169-170`):
```json
{
  "name": "dist_left",
  "semantic_name": "dist_left",
  "type": "text",
  "pdfField": "12Row",
  "label": "Dist from C/L (L)",
  "required": false
},
{
  "name": "dist_right",
  "semantic_name": "dist_right",
  "type": "text",
  "pdfField": "13Row",
  "label": "Dist from C/L (R)",
  "required": false
}
```

**After** (Composite Field):
```json
{
  "name": "dist_from_cl",
  "semantic_name": "dist_from_cl",
  "type": "composite",
  "label": "Dist from C/L",
  "required": false,
  "subFields": [
    {
      "name": "left",
      "label": "Left",
      "type": "text",
      "pdfField": "12Row"
    },
    {
      "name": "right",
      "label": "Right",
      "type": "text",
      "pdfField": "13Row"
    }
  ]
}
```

### 2. Data Storage (Response Data)

**Storage Format**: Flat structure with dot notation
```json
{
  "dist_from_cl.left": "25.5",
  "dist_from_cl.right": "30.2"
}
```

**Rationale**:
- Preserves existing storage schema
- No database migrations needed
- PDF mapping straightforward

### 3. PDF Mapping

Each subfield maps to its own PDF field independently:
- `dist_from_cl.left` → "12Row" (from subFields[0].pdfField)
- `dist_from_cl.right` → "13Row" (from subFields[1].pdfField)

**Implementation in `FormPdfService._fillTableRowFields`**:
- When mapping table rows, check for composite field pattern
- For field name like "dist_from_cl.left", split on "." and map using parent field's subFields config

### 4. Field Registry

**Option**: Store composite fields as individual entries with parent reference:
```dart
FormFieldEntry(
  fieldName: "dist_from_cl.left",
  label: "Dist from C/L - Left",
  pdfFieldName: "12Row",
  compositeParent: "dist_from_cl",  // New property
  ...
)
```

## Implementation Tasks

### Task 1: Update Field Type Enum (CRITICAL)

**Priority**: CRITICAL
**Estimated Time**: 15 minutes

#### Summary
Add `composite` to `PdfFieldType` enum.

#### Files to Modify
| File | Changes |
|------|---------|
| `lib/features/toolbox/data/models/form_field_entry.dart` | Add `PdfFieldType.composite` (line ~7-27) |

#### Specific Changes
```dart
enum PdfFieldType {
  text,
  textarea,
  checkbox,
  radio,
  dropdown,
  date,
  signature,
  composite,  // NEW: Composite field with multiple sub-fields
}
```

#### Agent
**Agent**: `data-layer-agent`

---

### Task 2: Update FormFieldEntry Model (HIGH)

**Priority**: HIGH
**Estimated Time**: 30 minutes

#### Summary
Add support for composite field metadata (sub-fields, parent reference).

#### Files to Modify
| File | Changes |
|------|---------|
| `lib/features/toolbox/data/models/form_field_entry.dart` | Add `subFields`, `compositeParent` properties |

#### Specific Changes
1. Add properties:
   ```dart
   /// For composite fields: sub-field definitions
   /// Structure: List<{name, label, type, pdfField}>
   final String? subFieldsJson;

   /// For sub-fields: reference to parent composite field name
   final String? compositeParent;
   ```

2. Update constructor, `copyWith`, `toMap`, `fromMap`

3. Add helper getters:
   ```dart
   /// Parse sub-fields from JSON
   List<Map<String, dynamic>> get parsedSubFields {
     if (subFieldsJson == null || subFieldsJson!.isEmpty) return [];
     try {
       final decoded = jsonDecode(subFieldsJson!) as List;
       return decoded.cast<Map<String, dynamic>>();
     } catch (e) {
       return [];
     }
   }

   /// Whether this is a composite field
   bool get isComposite => pdfFieldType == PdfFieldType.composite;
   ```

#### Agent
**Agent**: `data-layer-agent`

---

### Task 3: Update Database Schema (HIGH)

**Priority**: HIGH
**Estimated Time**: 20 minutes

#### Summary
Add columns for composite field support.

#### Files to Modify
| File | Changes |
|------|---------|
| `lib/core/database/database_service.dart` | Add migration for `sub_fields_json`, `composite_parent` columns |

#### Specific Changes
1. Add migration v21 (current version is v20):
   ```sql
   ALTER TABLE form_field_registry
   ADD COLUMN sub_fields_json TEXT;

   ALTER TABLE form_field_registry
   ADD COLUMN composite_parent TEXT;
   ```

2. Update `CREATE TABLE` statement in `_createTables` (line ~50-215)

#### Verification
- Run `flutter analyze` - no errors
- Launch app - database migrates successfully
- Check logs for "Database upgraded to version 21"

#### Agent
**Agent**: `data-layer-agent`

---

### Task 4: Update Field Discovery Service (HIGH)

**Priority**: HIGH
**Estimated Time**: 45 minutes

#### Summary
Expand composite fields into individual sub-field entries during form seeding.

#### Files to Modify
| File | Changes |
|------|---------|
| `lib/features/toolbox/data/services/field_discovery_service.dart` | Handle composite fields in `_createFieldEntries` |

#### Specific Changes
1. When processing field definitions:
   ```dart
   // Detect composite field
   if (fieldType == 'composite') {
     final subFields = fieldDef['subFields'] as List<dynamic>?;
     if (subFields == null || subFields.isEmpty) {
       debugPrint('[FieldDiscovery] Composite field missing subFields: $fieldName');
       continue;
     }

     // Create parent entry
     entries.add(FormFieldEntry(
       formId: formId,
       fieldName: fieldName,
       pdfFieldType: PdfFieldType.composite,
       label: label,
       subFieldsJson: jsonEncode(subFields),
       sortOrder: sortOrder,
       ...
     ));

     // Create sub-field entries
     for (final subFieldMap in subFields) {
       final subField = subFieldMap as Map<String, dynamic>;
       final subName = subField['name'] as String;
       final subLabel = subField['label'] as String? ?? subName;
       final subType = subField['type'] as String? ?? 'text';
       final subPdfField = subField['pdfField'] as String?;

       entries.add(FormFieldEntry(
         formId: formId,
         fieldName: '$fieldName.$subName',  // Dot notation
         pdfFieldName: subPdfField,
         pdfFieldType: _parseFieldType(subType),
         label: '$label - $subLabel',  // "Dist from C/L - Left"
         compositeParent: fieldName,
         sortOrder: sortOrder,
         ...
       ));
     }
     continue;  // Skip normal field creation
   }
   ```

#### Verification
- Seed form with composite field
- Check `form_field_registry` table for parent + sub-field entries
- Verify `fieldName` uses dot notation (e.g., "dist_from_cl.left")

#### Agent
**Agent**: `data-layer-agent`

---

### Task 5: Create CompositeFormField Widget (CRITICAL)

**Priority**: CRITICAL
**Estimated Time**: 60 minutes

#### Summary
New widget to render composite fields with stacked inputs.

#### Files to Create
| File | Purpose |
|------|---------|
| `lib/features/toolbox/presentation/widgets/composite_form_field.dart` | Composite field widget |

#### Widget Design
```dart
/// Renders a composite field with multiple stacked sub-fields.
///
/// Displays a single label at the top, followed by TextField widgets
/// for each sub-field arranged vertically.
class CompositeFormField extends StatelessWidget {
  final Map<String, dynamic> field;
  final Map<String, TextEditingController> controllers;
  final bool isEditable;
  final VoidCallback onChanged;

  const CompositeFormField({
    super.key,
    required this.field,
    required this.controllers,
    required this.isEditable,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final label = field['label'] as String;
    final subFields = field['subFields'] as List<dynamic>? ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Main label
        Padding(
          padding: const EdgeInsets.only(bottom: AppTheme.space2),
          child: Text(
            label,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
        ),

        // Sub-fields stacked vertically
        ...subFields.map((subFieldMap) {
          final subField = subFieldMap as Map<String, dynamic>;
          final subName = subField['name'] as String;
          final subLabel = subField['label'] as String? ?? subName;
          final fieldName = field['name'] as String;
          final fullFieldName = '$fieldName.$subName';
          final controller = controllers[fullFieldName];

          if (controller == null) return const SizedBox.shrink();

          return Padding(
            padding: const EdgeInsets.only(bottom: AppTheme.space2),
            child: TextFormField(
              key: TestingKeys.formField(fullFieldName),
              controller: controller,
              enabled: isEditable,
              decoration: InputDecoration(
                labelText: subLabel,
                isDense: true,
              ),
              onChanged: (_) => onChanged(),
            ),
          );
        }).toList(),
      ],
    );
  }
}
```

#### Agent
**Agent**: `flutter-specialist-agent`

---

### Task 6: Integrate CompositeFormField into DynamicFormField (CRITICAL)

**Priority**: CRITICAL
**Estimated Time**: 30 minutes

#### Summary
Add composite field rendering to the field type switch.

#### Files to Modify
| File | Changes |
|------|---------|
| `lib/features/toolbox/presentation/widgets/dynamic_form_field.dart` | Add case for composite type |
| `lib/features/toolbox/presentation/widgets/widgets.dart` | Export CompositeFormField |

#### Specific Changes (dynamic_form_field.dart)
```dart
// Line ~69, add before 'case checkbox:'
case 'composite':
  // For composite fields, we need access to multiple controllers
  // Pass the field definition and let CompositeFormField handle it
  input = CompositeFormField(
    field: widget.field,
    controllers: widget.compositeControllers ?? {},  // NEW PROPERTY
    isEditable: widget.isEditable,
    onChanged: widget.onChanged,
  );
  break;
```

**Note**: DynamicFormField needs new property `Map<String, TextEditingController>? compositeControllers`

#### Agent
**Agent**: `flutter-specialist-agent`

---

### Task 7: Update FormFillScreen Controller Management (HIGH)

**Priority**: HIGH
**Estimated Time**: 45 minutes

#### Summary
Initialize controllers for composite sub-fields.

#### Files to Modify
| File | Changes |
|------|---------|
| `lib/features/toolbox/presentation/screens/form_fill_screen.dart` | Update `_loadData` to create sub-field controllers |

#### Specific Changes
1. In `_loadData` (line ~88), after loading field definitions:
   ```dart
   // Initialize controllers for composite sub-fields
   for (final field in fields) {
     final fieldType = field['type'] as String?;
     final fieldName = field['name'] as String;

     if (fieldType == 'composite') {
       // Create controller for parent (not used, but keeps structure consistent)
       _fieldControllers[fieldName] = TextEditingController();

       // Create controllers for sub-fields
       final subFields = field['subFields'] as List<dynamic>? ?? [];
       for (final subFieldMap in subFields) {
         final subField = subFieldMap as Map<String, dynamic>;
         final subName = subField['name'] as String;
         final fullFieldName = '$fieldName.$subName';

         final value = responseData[fullFieldName] as String? ?? '';
         _fieldControllers[fullFieldName] = TextEditingController(text: value);
       }
     } else {
       // Normal field
       final value = responseData[fieldName] as String? ?? '';
       _fieldControllers[fieldName] = TextEditingController(text: value);
     }
   }
   ```

2. Update `_saveForm` to handle composite fields:
   ```dart
   for (final entry in _fieldControllers.entries) {
     // Store all controllers (including sub-fields with dot notation)
     responseData[entry.key] = entry.value.text;
   }
   ```

#### Agent
**Agent**: `flutter-specialist-agent`

---

### Task 8: Update PDF Mapping Service (HIGH)

**Priority**: HIGH
**Estimated Time**: 30 minutes

#### Summary
Map composite sub-fields to PDF fields using dot notation.

#### Files to Modify
| File | Changes |
|------|---------|
| `lib/features/toolbox/data/services/form_pdf_service.dart` | Handle dot notation in field names |

#### Specific Changes
In `generateFormPdf` (line ~309-318):
```dart
// Fill form fields from response data
for (final fieldDef in fieldDefinitions) {
  final fieldName = fieldDef['name'] as String;
  final fieldType = fieldDef['type'] as String?;

  // Handle composite fields
  if (fieldType == 'composite') {
    final subFields = fieldDef['subFields'] as List<dynamic>? ?? [];
    for (final subFieldMap in subFields) {
      final subField = subFieldMap as Map<String, dynamic>;
      final subName = subField['name'] as String;
      final fullFieldName = '$fieldName.$subName';
      final pdfField = subField['pdfField'] as String?;
      final value = responseData[fullFieldName];

      if (value != null && pdfField != null) {
        _setField(form, pdfField, value.toString());
      }
    }
    continue;  // Skip normal field processing
  }

  // Normal field processing...
  final pdfField = fieldDef['pdfField'] as String? ?? fieldName;
  final value = responseData[fieldName];
  if (value != null) {
    _setField(form, pdfField, value.toString());
  }
}
```

#### Agent
**Agent**: `pdf-agent`

---

### Task 9: Update 0582B Form JSON (CRITICAL)

**Priority**: CRITICAL
**Estimated Time**: 15 minutes

#### Summary
Replace separate dist_left/dist_right with composite field.

#### Files to Modify
| File | Changes |
|------|---------|
| `assets/data/forms/mdot_0582b_density.json` | Replace lines 169-170, update entryLayout |

#### Specific Changes
1. **Remove** lines 169-170 (dist_left, dist_right)

2. **Add** composite field (insert at line 169):
   ```json
   {
     "name": "dist_from_cl",
     "semantic_name": "dist_from_cl",
     "type": "composite",
     "label": "Dist from C/L",
     "required": false,
     "subFields": [
       {
         "name": "left",
         "label": "Left",
         "type": "text",
         "pdfField": "12Row"
       },
       {
         "name": "right",
         "label": "Right",
         "type": "text",
         "pdfField": "13Row"
       }
     ]
   }
   ```

3. **Update** `tableRowConfig.groups[0].entryLayout.rightColumn` (line ~176):
   ```json
   "rightColumn": [
     "test_depth",
     "counts_dc",
     "wet_density",
     "moisture_percent",
     "percent_compaction",
     "station",
     "dist_from_cl",
     "item_of_work"
   ]
   ```

4. **Remove** `dist_left` and `dist_right` from `parsingKeywords.fieldMappings` and `synonyms` (lines 223-224, 241-242)

5. **Increment seed version** in form seeding service to trigger re-population

#### Agent
**Agent**: `data-layer-agent`

---

### Task 10: Update Parsing Keywords (MEDIUM)

**Priority**: MEDIUM
**Estimated Time**: 20 minutes

#### Summary
Update smart text parsing to recognize composite field names.

#### Files to Modify
| File | Changes |
|------|---------|
| `lib/features/toolbox/data/services/form_parsing_service.dart` | Handle composite field mapping |

#### Specific Changes
When mapping parsed keywords to field names:
```dart
// Check for composite field sub-field pattern
if (normalizedFieldName.contains('.')) {
  // It's a sub-field like "dist_from_cl.left"
  // Map synonym to full field name
  fieldMappings[synonym] = normalizedFieldName;
} else {
  // Normal field...
}
```

Update JSON parsing keywords (optional, can use full names):
```json
"fieldMappings": {
  "dist left": "dist_from_cl.left",
  "dist right": "dist_from_cl.right"
}
```

#### Agent
**Agent**: `data-layer-agent`

---

## Execution Order

### Phase 1: Data Layer (Critical Path)
**Estimated Time**: 2.5 hours

1. Task 1: Update Field Type Enum - `data-layer-agent`
2. Task 2: Update FormFieldEntry Model - `data-layer-agent`
3. Task 3: Update Database Schema - `data-layer-agent`
4. Task 4: Update Field Discovery Service - `data-layer-agent`

**Deliverables**: Composite fields can be seeded into database

---

### Phase 2: UI Layer (Critical Path)
**Estimated Time**: 2.5 hours

5. Task 5: Create CompositeFormField Widget - `flutter-specialist-agent`
6. Task 6: Integrate into DynamicFormField - `flutter-specialist-agent`
7. Task 7: Update FormFillScreen - `flutter-specialist-agent`

**Deliverables**: Composite fields can be rendered and edited

---

### Phase 3: Integration (Critical Path)
**Estimated Time**: 1.5 hours

8. Task 8: Update PDF Mapping Service - `pdf-agent`
9. Task 9: Update 0582B Form JSON - `data-layer-agent`

**Deliverables**: 0582B form uses composite field, exports to PDF correctly

---

### Phase 4: Enhancement (Optional)
**Estimated Time**: 20 minutes

10. Task 10: Update Parsing Keywords - `data-layer-agent`

**Deliverables**: Smart text parsing works with composite fields

---

## Verification Checklist

### Unit Tests
- [ ] `PdfFieldType.composite` enum value accessible
- [ ] `FormFieldEntry.parsedSubFields` returns correct structure
- [ ] Database migration v21 applies successfully

### Integration Tests
- [ ] Form with composite field seeds correctly
- [ ] Sub-field controllers initialize with data
- [ ] Sub-field values save to `responseData` with dot notation
- [ ] PDF export maps sub-fields to correct PDF fields

### Manual Testing
1. **Form Loading**
   - [ ] Open existing 0582B form response
   - [ ] Composite field renders with "Dist from C/L" label
   - [ ] Two text fields ("Left", "Right") appear stacked underneath
   - [ ] Existing `dist_left`/`dist_right` data migrates (or form shows empty)

2. **Data Entry**
   - [ ] Enter value in Left field - marks form as dirty
   - [ ] Enter value in Right field - marks form as dirty
   - [ ] Save form - values persist

3. **PDF Export**
   - [ ] Export to PDF
   - [ ] Open PDF template
   - [ ] Verify "12Row" field contains Left value
   - [ ] Verify "13Row" field contains Right value

4. **Auto-fill** (if applicable)
   - [ ] Auto-fill indicators appear on sub-fields if source configured
   - [ ] Clear auto-fill works on sub-fields

5. **Carry-forward** (if applicable)
   - [ ] Previous form's dist_from_cl values carry forward to new form

### Regression Testing
- [ ] `flutter analyze` - no new errors
- [ ] `flutter test` - all existing tests pass
- [ ] Other forms without composite fields still work
- [ ] Table rows section still functions correctly

---

## Edge Cases & Considerations

### 1. Backward Compatibility
**Issue**: Existing responses have `dist_left` and `dist_right` as separate fields.

**Solution**:
- Add data migration in `FormResponseRepository`:
  ```dart
  // Migrate old dist_left/dist_right to composite format
  if (responseData.containsKey('dist_left') || responseData.containsKey('dist_right')) {
    responseData['dist_from_cl.left'] = responseData['dist_left'] ?? '';
    responseData['dist_from_cl.right'] = responseData['dist_right'] ?? '';
    responseData.remove('dist_left');
    responseData.remove('dist_right');
  }
  ```

### 2. Auto-fill Support
**Question**: Can composite sub-fields be auto-filled?

**Answer**: Yes, treat each sub-field as independent for auto-fill:
- `dist_from_cl.left` can have `autoFillSource: "location"`
- `dist_from_cl.right` can have `autoFillSource: "location"`

### 3. Validation
**Question**: Can composite fields be marked as required?

**Answer**:
- Parent field `required: true` - all sub-fields required
- Sub-field `required: true` - specific sub-field required
- Implement validation in `CompositeFormField` widget

### 4. Testing Keys
**Pattern**: Use dot notation for sub-field keys
```dart
TestingKeys.formField('dist_from_cl.left')
TestingKeys.formField('dist_from_cl.right')
```

### 5. Layout Flexibility
**Current Design**: Stacked vertically (simplest)

**Future Enhancement**: Support horizontal layout via config:
```json
{
  "type": "composite",
  "layout": "horizontal",
  "subFields": [...]
}
```

---

## Future Enhancements

### Enhancement 1: Composite Fields in Table Rows
**Use Case**: Grouped test entry could use composite fields for station/offset pairs

**Design**:
- Add `type: "composite"` support to `TableColumnConfig`
- Render composite columns as multiple inputs side-by-side

### Enhancement 2: Nested Composites
**Use Case**: Address field (Street/City/State/Zip)

**Design**: Allow `subFields` to contain `type: "composite"`

### Enhancement 3: Visual Grouping Styles
**Options**:
- Card border around sub-fields
- Colored left border
- Indentation

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking existing forms | HIGH | Thorough testing, backward compatibility migration |
| PDF mapping errors | MEDIUM | Extensive PDF export verification |
| Auto-fill conflicts | LOW | Sub-fields are independent, existing auto-fill logic applies |
| Performance impact | LOW | Minimal (one parent field to N sub-fields in memory) |

---

## Success Criteria

1. **Functional**: 0582B form displays "Dist from C/L" with Left/Right inputs
2. **Data Integrity**: Sub-field values save/load correctly with dot notation
3. **PDF Export**: Left/Right values map to 12Row/13Row in PDF
4. **Reusability**: Another form can add composite field by updating JSON
5. **No Regressions**: Existing forms and tests continue to work

---

## Notes

- **Design Philosophy**: Extend existing patterns rather than reinvent
- **Table Row Inspiration**: The grouped entry system already solved this problem for repeating rows
- **Flat Storage**: Dot notation keeps database schema simple
- **Agent Delegation**: Clear boundaries between data, UI, and PDF concerns

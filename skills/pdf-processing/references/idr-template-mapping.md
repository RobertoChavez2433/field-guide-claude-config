# IDR Template Field Mapping

Complete field mapping for `assets/templates/idr_template.pdf`.

## Template Overview

- **File**: `assets/templates/idr_template.pdf`
- **Total Fields**: 179
- **Pages**: Multiple
- **Field Naming**: Legacy garbage names (e.g., `ggggsssssssssss`)

---

## Contractor Fields

### Dart Mapping Location
`lib/features/pdf/services/pdf_service.dart` - `_contractorFieldMap`

### Field Mappings

| Logical Name | PDF Field Name | Page | Status |
|--------------|----------------|------|--------|
| contractor_name | TBD | 1 | Unverified |
| contractor_address | TBD | 1 | Unverified |
| contractor_city | TBD | 1 | Unverified |
| contractor_state | TBD | 1 | Unverified |
| contractor_zip | TBD | 1 | Unverified |
| contractor_phone | TBD | 1 | Unverified |

> **Note**: Run `extract_form_field_info.py` to populate actual field names.

---

## Equipment Fields

### Dart Mapping Location
`lib/features/pdf/services/pdf_service.dart` - `_equipmentFieldMap`

### Field Mappings

| Logical Name | PDF Field Name | Page | Status |
|--------------|----------------|------|--------|
| equipment_description | TBD | 2 | Unverified |
| equipment_quantity | TBD | 2 | Unverified |
| equipment_hours | TBD | 2 | Unverified |

---

## Project Information Fields

| Logical Name | PDF Field Name | Page | Status |
|--------------|----------------|------|--------|
| project_name | TBD | 1 | Unverified |
| project_number | TBD | 1 | Unverified |
| project_location | TBD | 1 | Unverified |
| report_date | TBD | 1 | Unverified |
| report_number | TBD | 1 | Unverified |

---

## Weather Fields

| Logical Name | PDF Field Name | Page | Status |
|--------------|----------------|------|--------|
| weather_am | TBD | 1 | Unverified |
| weather_pm | TBD | 1 | Unverified |
| temperature_high | TBD | 1 | Unverified |
| temperature_low | TBD | 1 | Unverified |

---

## Verification Process

### Step 1: Extract All Fields
```bash
python .claude/skills/pdf-processing/scripts/extract_form_field_info.py \
  assets/templates/idr_template.pdf \
  idr_fields.json
```

### Step 2: Create Visual Debug
```bash
python .claude/skills/pdf-processing/scripts/convert_pdf_to_images.py \
  assets/templates/idr_template.pdf \
  idr_images/
```

### Step 3: Test Fill Individual Fields
```bash
# Create test data JSON
echo '{"ggggsssssssssss": "TEST VALUE"}' > test_data.json

# Fill and verify
python .claude/skills/pdf-processing/scripts/fill_fillable_fields.py \
  assets/templates/idr_template.pdf \
  test_output.pdf \
  test_data.json
```

### Step 4: Update This Document
Mark field as "Verified" once visual confirmation is complete.

---

## Cross-Reference with Dart

### Sync Dart Mappings
When updating this document, also update:
- `lib/features/pdf/services/pdf_service.dart` - `_contractorFieldMap`
- `lib/features/pdf/services/pdf_service.dart` - `_equipmentFieldMap`

### Debug PDF Generation
The app's `generateDebugPdf()` method creates a debug PDF showing field positions.
Compare Python extraction results with Dart debug output.

---

## Known Issues

### Garbage Field Names
The IDR template uses meaningless field names like:
- `ggggsssssssssss`
- `sfdasd`
- `asdfsdf`

**Cause**: Legacy PDF creation tool or poor naming convention.
**Mitigation**: This mapping document serves as the canonical reference.

### Field Position Drift
Some fields may have incorrect bounding boxes in the PDF metadata.
**Mitigation**: Always verify visually before using in production.

---

## Updating This Document

When verifying a new field:

1. Run the visual verification scripts
2. Confirm the field name maps to the expected visual position
3. Update the table above with:
   - Correct PDF field name
   - Page number
   - Change status to "Verified"
4. Update corresponding Dart mapping
5. Run app's debug PDF to cross-verify

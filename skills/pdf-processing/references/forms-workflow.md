# PDF Forms Workflow

Two approaches for working with PDF forms, depending on whether the PDF has fillable fields or requires annotation-based filling.

## Decision Tree

```
PDF Input
    |
    v
+-- Is fillable? --+
|                  |
v                  v
YES               NO
|                  |
v                  v
Path A:           Path B:
Form Fields       Annotations
```

## Path A: Fillable PDF Forms

Use when `check_fillable_fields.py` reports fillable fields.

### Step 1: Extract Field Information
```bash
python .claude/skills/pdf-processing/scripts/extract_form_field_info.py input.pdf fields.json
```

Output JSON structure:
```json
{
  "field_name": {
    "type": "text|checkbox|radio|dropdown",
    "page": 1,
    "rect": [x1, y1, x2, y2],
    "value": "current_value"
  }
}
```

### Step 2: Create Mapping
Map logical field names to PDF field names:
```python
field_mapping = {
    "contractor_name": "ggggsssssssssss",  # Garbage name in PDF
    "contractor_address": "sfdasd",
    # ...
}
```

### Step 3: Fill Fields
```bash
python .claude/skills/pdf-processing/scripts/fill_fillable_fields.py input.pdf output.pdf data.json
```

### Step 4: Verify
```bash
python .claude/skills/pdf-processing/scripts/create_validation_image.py output.pdf validation/
```

---

## Path B: Annotation-Based Filling

Use when PDF has no fillable fields (scanned forms, images, etc.).

### Step 1: Convert to Images
```bash
python .claude/skills/pdf-processing/scripts/convert_pdf_to_images.py input.pdf images/
```

### Step 2: Determine Coordinates
Open images and identify pixel coordinates for each field.

### Step 3: Create Position Map
```python
positions = {
    "contractor_name": {"page": 1, "x": 150, "y": 200, "width": 300, "height": 20},
    # ...
}
```

### Step 4: Fill with Annotations
```bash
python .claude/skills/pdf-processing/scripts/fill_pdf_form_with_annotations.py input.pdf output.pdf positions.json data.json
```

---

## Project-Specific Paths

### IDR Template (Path A - Fillable)
- **Template**: `assets/templates/idr_template.pdf`
- **Field Count**: 179 fields
- **Dart Mappings**: `lib/features/pdf/services/pdf_service.dart`

### Test Outputs
- **Debug PDFs**: `Troubleshooting/IDR Test Exports/`
- **Reference Forms**: `Pre-development and brainstorming/Form Templates for export/`

---

## Common Issues

### Issue: Field Names Don't Match Visual Position
**Cause**: Legacy PDF with meaningless field names
**Solution**: Always use visual verification before mapping

### Issue: Checkbox Not Toggling
**Cause**: PDF uses non-standard checkbox values
**Solution**: Check extracted field info for valid values (often "Yes"/"Off" or "1"/"0")

### Issue: Text Truncated
**Cause**: Font size too large for field bounds
**Solution**: Check field rect dimensions, adjust font size accordingly

### Issue: Coordinates Don't Match
**Cause**: PDF coordinate system (origin at bottom-left)
**Solution**: Use `check_bounding_boxes.py` to visualize actual positions

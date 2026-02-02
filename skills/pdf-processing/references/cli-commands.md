# PDF Processing CLI Commands

Quick reference for all Python CLI tools.

## Prerequisites

### Python Dependencies
```bash
pip install -r .claude/skills/pdf-processing/scripts/requirements.txt
```

Or install individually:
```bash
pip install pypdf pdfplumber pdf2image Pillow
```

### Windows: Poppler Installation (Required for pdf2image)
1. Download: https://github.com/oschwartz10612/poppler-windows/releases
2. Extract to `C:\Program Files\poppler\`
3. Add `C:\Program Files\poppler\bin` to PATH

### Verify Installation
```bash
python -c "import pypdf; import pdfplumber; print('Core packages OK')"
python -c "from pdf2image import convert_from_path; print('pdf2image OK')"
```

---

## Analysis Commands

### Check If PDF Has Fillable Fields
```bash
python .claude/skills/pdf-processing/scripts/check_fillable_fields.py <pdf_path>
```
**Output**: "This PDF has fillable form fields" or "This PDF does NOT have fillable form fields"

### Extract Form Field Information
```bash
python .claude/skills/pdf-processing/scripts/extract_form_field_info.py <pdf_path> <output.json>
```
**Output**: JSON file with field names, types, positions, and current values

### Convert PDF to Images
```bash
python .claude/skills/pdf-processing/scripts/convert_pdf_to_images.py <pdf_path> <output_dir>
```
**Output**: PNG images for each page (page_1.png, page_2.png, etc.)

### Check Bounding Boxes
```bash
python .claude/skills/pdf-processing/scripts/check_bounding_boxes.py <pdf_path> <output_dir>
```
**Output**: Images with field bounding boxes drawn

---

## Filling Commands

### Fill Fillable Fields (Path A)
```bash
python .claude/skills/pdf-processing/scripts/fill_fillable_fields.py <input.pdf> <output.pdf> <data.json>
```
**Input JSON format**:
```json
{
  "field_name_1": "value1",
  "field_name_2": "value2"
}
```

### Fill with Annotations (Path B)
```bash
python .claude/skills/pdf-processing/scripts/fill_pdf_form_with_annotations.py <input.pdf> <output.pdf> <positions.json> <data.json>
```
**Positions JSON format**:
```json
{
  "field_name": {
    "page": 1,
    "x": 150,
    "y": 200,
    "width": 300,
    "height": 20
  }
}
```

---

## Validation Commands

### Create Validation Images
```bash
python .claude/skills/pdf-processing/scripts/create_validation_image.py <pdf_path> <output_dir>
```
**Output**: Annotated images showing filled field values

---

## Project-Specific Examples

### IDR Template Analysis
```bash
# Check fillability
python .claude/skills/pdf-processing/scripts/check_fillable_fields.py assets/templates/idr_template.pdf

# Extract all 179 fields
python .claude/skills/pdf-processing/scripts/extract_form_field_info.py \
  assets/templates/idr_template.pdf \
  Troubleshooting/idr_fields.json

# Visual analysis
python .claude/skills/pdf-processing/scripts/convert_pdf_to_images.py \
  assets/templates/idr_template.pdf \
  Troubleshooting/idr_images/
```

### Debug Field Position
```bash
# Fill single field to verify position
echo '{"ggggsssssssssss": "TEST VALUE"}' > test_data.json

python .claude/skills/pdf-processing/scripts/fill_fillable_fields.py \
  assets/templates/idr_template.pdf \
  Troubleshooting/test_output.pdf \
  test_data.json

# Visualize result
python .claude/skills/pdf-processing/scripts/create_validation_image.py \
  Troubleshooting/test_output.pdf \
  Troubleshooting/validation/
```

### Bid Schedule Analysis
```bash
# For PDFs that fail Dart parsers
python .claude/skills/pdf-processing/scripts/convert_pdf_to_images.py \
  problematic_schedule.pdf \
  analysis/

# Check structure
python .claude/skills/pdf-processing/scripts/check_fillable_fields.py problematic_schedule.pdf
```

---

## Common Workflows

### Workflow 1: New Field Mapping
```bash
# 1. Extract all fields
python .claude/skills/pdf-processing/scripts/extract_form_field_info.py template.pdf fields.json

# 2. Review JSON, identify candidate field names

# 3. Test fill one field at a time
echo '{"candidate_field": "TEST"}' > test.json
python .claude/skills/pdf-processing/scripts/fill_fillable_fields.py template.pdf test.pdf test.json

# 4. Visual verification
python .claude/skills/pdf-processing/scripts/create_validation_image.py test.pdf verify/

# 5. Update idr-template-mapping.md with verified mapping
```

### Workflow 2: Debug Parser Failure
```bash
# 1. Convert to images for visual inspection
python .claude/skills/pdf-processing/scripts/convert_pdf_to_images.py problem.pdf images/

# 2. Check structure
python .claude/skills/pdf-processing/scripts/check_fillable_fields.py problem.pdf

# 3. If fillable, extract field info
python .claude/skills/pdf-processing/scripts/extract_form_field_info.py problem.pdf info.json

# 4. Compare extracted text with expected data
# 5. Identify why Dart parser failed
```

---

## Troubleshooting

### "poppler not found" Error
Ensure Poppler is installed and in PATH:
```bash
where pdftoppm  # Windows
which pdftoppm  # Unix
```

### "No module named 'pypdf'" Error
Install dependencies:
```bash
pip install -r .claude/skills/pdf-processing/scripts/requirements.txt
```

### Output Images Are Empty
Check PDF isn't password protected or corrupted:
```bash
python -c "import pypdf; print(pypdf.PdfReader('file.pdf').pages)"
```

# PDF Processing Skill

**Purpose**: Python CLI tools for PDF template debugging, extraction analysis, and import troubleshooting.

## Iron Law

> **VERIFY FIELD POSITIONS VISUALLY BEFORE FILLING PROGRAMMATICALLY**

The IDR template has 179 form fields with non-intuitive names (e.g., `ggggsssssssssss`, `sfdasd`). Never assume a field name maps to a visual position without debug verification.

## When to Use

- Debugging IDR template field positions
- Analyzing PDFs that fail the Dart parser cascade
- Pre-analyzing bid schedules before import
- Troubleshooting low-confidence extraction results
- Creating field mapping documentation

## When NOT to Use

- Runtime PDF generation (use Syncfusion Flutter PDF)
- In-app OCR (future: Google ML Kit)
- PDF preview/sharing (use printing package)

## Three-Phase Workflow

### Phase 1: PDF Analysis
```bash
# Check if fillable
python .claude/skills/pdf-processing/scripts/check_fillable_fields.py <pdf>

# Extract field metadata (for fillable PDFs)
python .claude/skills/pdf-processing/scripts/extract_form_field_info.py <pdf> <output.json>

# Convert to images for visual analysis
python .claude/skills/pdf-processing/scripts/convert_pdf_to_images.py <pdf> <output_dir>
```

### Phase 2: Verification
- Compare extracted fields to expected mappings
- Use validation images to check bounding boxes
- Cross-reference with Dart `_contractorFieldMap` in pdf_service.dart

### Phase 3: Integration
- Update `lib/features/pdf/services/pdf_service.dart` field mappings
- Run app's `generateDebugPdf()` to cross-verify
- Test with real data

## Reference Documents

@.claude/skills/pdf-processing/references/forms-workflow.md
@.claude/skills/pdf-processing/references/extraction-enhancement.md
@.claude/skills/pdf-processing/references/idr-template-mapping.md
@.claude/skills/pdf-processing/references/cli-commands.md

## Rationalization Prevention

| If You Think... | Stop And... |
|-----------------|-------------|
| "This field name looks right" | Run visual verification first |
| "I'll map all fields at once" | Map and verify one section at a time |
| "The Dart debug PDF is enough" | Python scripts reveal more detail |
| "pdfplumber can replace Syncfusion" | No - scripts for dev, Syncfusion for runtime |

## Project-Specific Context

### IDR Template Location
- Template: `assets/templates/idr_template.pdf`
- Test exports: `Troubleshooting/IDR Test Exports/`
- Reference forms: `Pre-development and brainstorming/Form Templates for export/`

### Existing Dart Field Mappings
- `lib/features/pdf/services/pdf_service.dart:150-171` - `_contractorFieldMap`
- `lib/features/pdf/services/pdf_service.dart:160-171` - `_equipmentFieldMap`

### Parser Files (for comparison)
- `lib/features/pdf/services/pdf_import_service.dart` - Main import service
- `lib/features/pdf/services/parsers/column_layout_parser.dart` - Primary parser
- `lib/features/pdf/services/parsers/clumped_text_parser.dart` - Fallback parser

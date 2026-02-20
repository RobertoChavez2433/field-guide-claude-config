---
paths:
  - "lib/features/pdf/**/*.dart"
  - "assets/templates/**/*.pdf"
---

# PDF Generation Expert

## Quick Reference

### Key Files
```
lib/features/pdf/
├── data/
│   ├── models/          # PDF-related models
│   ├── services/        # PDF generation services
│   └── parsers/         # Bid item PDF parsers
└── presentation/
    ├── screens/         # Preview screens
    └── widgets/         # PDF-related widgets
```

### Template Location
- Templates: `assets/templates/*.pdf`
- Form field mappings are defined inline in `lib/features/pdf/services/pdf_service.dart`

## PDF Template Field Mapping

### Field Naming Conventions
**DO:** `project_name`, `contractor_1_name`, `foreman_count_1`
**DON'T:** `Text10`, `ggggsssssssssss`, `Name_3234234`

### Syncfusion PDF Pattern
```dart
// Load template
final bytes = await rootBundle.load('assets/templates/form.pdf');
final document = PdfDocument(inputBytes: bytes.buffer.asUint8List());

// Get form
final form = document.form;

// Fill field by name
final field = form.fields[fieldName] as PdfTextBoxField;
field.text = value;

// Save
final outputBytes = await document.save();
document.dispose();
```

### Field Mapping Best Practices
```dart
class FormFieldMappings {
  static const Map<String, String> dailyReport = {
    'project_name': 'projectName',
    'date': 'date',
    'weather': 'weatherConditions',
    'contractor_1_name': 'primeContractor',
  };
}
```

## PDF Parsing (Bid Items)

### ParsedBidItem Model
```dart
class ParsedBidItem {
  final String itemNumber;
  final String description;
  final String unit;
  final double quantity;
  final double unitPrice;
  final double confidence;  // 0.0 - 1.0
  final List<String> warnings;
}
```

### Confidence Handling
```dart
if (confidence < 0.6) return UserValidationRequired(value, confidence);
else if (confidence < 0.8) return ExtractedWithWarning(value, confidence);
else return ExtractedValue(value);
```

## PDF Extraction Pipeline (V2 — Current)

### Stage Overview

| Stage | Class | Purpose |
|-------|-------|---------|
| 0 | `DocumentQualityProfiler` | Detect scan vs native PDF, char count |
| 2B-i | `PageRendererV2` | Rasterize pages to PNG (adaptive DPI: ≤10 pages→300, 11-25→250, >25→200) |
| 2B-ii | `ImagePreprocessorV2` | Grayscale + adaptive contrast (no binarization) |
| 2B-ii.5 | `GridLineDetector` | Detect table grid lines (normalized positions) |
| 2B-ii.6 | `GridLineRemover` | Remove grid lines via OpenCV inpainting (grid pages only) |
| 2B-iii | `TextRecognizerV2` | Cell-level OCR (grid pages) or full-page PSM 4 (non-grid) |
| 3 | `ElementValidator` | Coordinate normalization + element filtering |
| 4A | `RowClassifierV3` | Row classification (provisional then final) |
| 4B | `RegionDetectorV2` | Table region detection (two-pass) |
| 4C | `ColumnDetectorV2` | Column boundary detection |
| 4D | `CellExtractorV2` | Extract text per grid cell |
| 4D.5 | `NumericInterpreter` | Parse numeric/currency values |
| 4E | `RowParserV3` | Map cells to ParsedBidItem fields |
| 4E.5 | `FieldConfidenceScorer` | Per-field confidence (weighted geometric mean) |
| 5 | `PostProcessorV2` | Normalization, deduplication, math backsolve |
| 6 | `QualityValidator` | Overall quality check; triggers re-extraction if below threshold |

Re-extraction loop: up to 2 retries at 400 DPI (PSM 3 then PSM 6). Best result by `overallScore` kept.

### Image Preprocessing (Stage 2B-ii)
File: `lib/features/pdf/services/extraction/stages/image_preprocessor_v2.dart`

Steps (in order):
1. Decode PNG (`img.decodeImage(params.imageBytes)`)
2. Measure contrast (luminance std dev, sampled 1-in-10 pixels)
3. Grayscale conversion (`img.grayscale`)
4. Adaptive contrast enhancement (`img.adjustColor`, factor chosen by pre-contrast: <0.3→1.8, <0.5→1.5, <0.7→1.2, ≥0.7→no-op)
5. Convert to 1-channel (`processed.convert(numChannels: 1)`) for Tesseract compatibility
6. Encode to PNG

**REMOVED**: Binarization — deliberately removed (destroyed 92% of image data on clean PDFs).
**NOT IMPLEMENTED**: Deskewing (`skewAngle` hardcoded to 0.0).

### Grid Line Removal (Stage 2B-ii.6)
File: `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
Package: `opencv_dart` v2.2.1+3

Only runs on pages where `GridLineDetector` flagged a grid. Steps:
1. Decode directly to grayscale Mat (`cv.imdecode(inputBytes, cv.IMREAD_GRAYSCALE)`)
2. Adaptive threshold (ADAPTIVE_THRESH_MEAN_C, THRESH_BINARY_INV, blockSize=15, C=-2.0)
3. Morphological open for horizontal lines (kernel: width/30 × 1)
4. Morphological open for vertical lines (kernel: 1 × height/30)
5. Combine masks + dilate 1 iteration with 3×3 kernel
6. Inpaint (`cv.INPAINT_TELEA`, radius=2.0)

### OCR Engine + Cell PSM Selection (Stages 2B-iii)
Files:
- `lib/features/pdf/services/extraction/ocr/tesseract_engine_v2.dart` — executes OCR with a given `OcrConfigV2` (PSM is caller-provided, not decided here)
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart` — decides PSM per cell via `_determineRowPsm`

Package: `flusseract` (Tesseract 5)

**Grid pages** — cell-level cropping:
- PSM per cell: row 0 (header) → PSM 6, tall rows (>1.8× median height) → PSM 6, data rows → PSM 7
- CropUpscaler: targets 600 DPI, cubic interpolation, 10px padding, max 2000px output
- Re-OCR fallback triggered when: numeric column (`{3, 4, 5}`), row > 0, all elements have confidence < 0.50, AND no digit characters in existing results. Re-runs with PSM 8 + numeric whitelist.

**Non-grid pages** — full page with PSM 4 (single column of text)

### Confidence Scoring (Stage 4E.5)
File: `lib/features/pdf/services/extraction/stages/field_confidence_scorer.dart`

Weighted geometric mean across 3 factors:
| Factor | Weight | Source |
|--------|--------|--------|
| OCR confidence | 50% | Tesseract `x_wconf` / 100 |
| Format validation | 30% | `FieldFormatValidator` per field type |
| Interpretation confidence | 20% | Pattern match name |

Zero-conf sentinel: if `x_wconf == 0.0` but text is non-empty → uses 0.50 neutral prior.

Low-confidence threshold: **0.80**. Items below this counted in `items_below_0_80`.

### Math Backsolve (Stage 5)
When `qty × unitPrice ≠ bidAmount`: derives `unitPrice = bidAmount / qty` (if round-trips within $0.02).
Applies -0.03 confidence penalty.

## Common Issues

### Field Not Found
```dart
// BAD - crashes if field doesn't exist
final field = form.fields['wrong_name'] as PdfTextBoxField;

// GOOD - handle missing fields gracefully
final fieldIndex = form.fields.indexOf(form.fields
    .cast<PdfField?>()
    .firstWhere((f) => f?.name == fieldName, orElse: () => null));
if (fieldIndex == -1) {
  debugPrint('[PDF] Field not found: $fieldName');
  return;
}
```

### Page Breaks
- Don't split related content across pages
- Use conditional page breaks before large sections
- Test with maximum data to verify layout

### Empty Sections
- Show placeholder text: "No data available"
- Use consistent styling for empty states
- Don't leave blank spaces without indication

## Debugging

```dart
// List all form fields
for (var i = 0; i < form.fields.count; i++) {
  final field = form.fields[i];
  debugPrint('Field $i: ${field.name} (${field.runtimeType})');
}

// Print field mapping issues
if (unmappedFields.isNotEmpty) {
  debugPrint('[PDF] Unmapped fields: $unmappedFields');
}
```

## Testing

### Unit Test Pattern
```dart
test('fills project name field', () async {
  final bytes = await File('test/fixtures/template.pdf').readAsBytes();
  final result = await pdfService.fillTemplate(bytes, {'project_name': 'Test'});

  final doc = PdfDocument(inputBytes: result);
  final field = doc.form.fields['project_name'] as PdfTextBoxField;
  expect(field.text, 'Test');
  doc.dispose();
});
```

## Quality Checklist

- [ ] All fields map to correct visual positions
- [ ] No `[PDF] Field not found` errors in console
- [ ] Data appears in expected format
- [ ] Page breaks don't split content awkwardly
- [ ] Empty sections show appropriate placeholder
- [ ] Maximum content tested (no overflow)

## Pull Request Template
```markdown
## PDF Changes
- [ ] Template affected: [template name]
- [ ] Fields modified: [list]
- [ ] Pipeline stage(s) modified: [e.g., Stage 4E RowParserV3, Stage 5 PostProcessorV2]

## Testing
- [ ] Preview verified with sample data
- [ ] Maximum content tested (no overflow)
- [ ] Empty state tested
- [ ] Field mapping validated
- [ ] Scorecard regenerated (if extraction pipeline changed)
```

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
- Form definitions: `lib/features/pdf/data/services/form_field_mappings.dart`

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

### Parser Chain
1. `ColumnLayoutParser` - Multi-column PDFs with clear structure
2. `ClumpedTextParser` - Densely formatted PDFs without clear columns
3. Fallback to raw text extraction

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

## OCR Integration

### Page Segmentation Modes (PSM)
| Mode | Use Case |
|------|----------|
| 6 | Single uniform block (forms, receipts) |
| 7 | Single text line (field values) |
| 11 | Sparse text (scattered labels) |
| 13 | Raw line (single line, no processing) |

### Preprocessing Pipeline
1. Convert to grayscale
2. Resize if too small (upscale to 1500px width)
3. Denoise (median filter)
4. Increase contrast (2x enhancement)
5. Sharpen (2x enhancement)
6. Adaptive binarization (local threshold)
7. Deskew if rotated

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

## Pull Request Template
```markdown
## PDF Changes
- [ ] Template affected: [template name]
- [ ] Fields modified: [list]
- [ ] Parser changes: [ColumnLayout/Clumped/None]

## Testing
- [ ] Preview verified with sample data
- [ ] Maximum content tested (no overflow)
- [ ] Empty state tested
- [ ] Field mapping validated
```

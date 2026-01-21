# PDF Workflows

## OCR Data Extraction

### When to Use OCR
- **Density test forms** - Extract moisture/density readings from photos
- **Field measurement sheets** - Capture handwritten or printed values
- **Existing inspection reports** - Import data from scanned documents

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

### Flutter OCR Packages
| Package | Best For | Offline |
|---------|----------|---------|
| `google_ml_kit` | General text recognition | Yes |
| `firebase_ml_vision` | Cloud-enhanced accuracy | No |
| `tesseract_ocr` | Custom configuration | Yes |

### Confidence Handling
```dart
if (confidence < 60) return UserValidationRequired(value, confidence);
else if (confidence < 80) return ExtractedWithWarning(value, confidence);
else return ExtractedValue(value);
```

## PDF Template Creation

### Field Naming Conventions
**DO:** `project_name`, `contractor_1_name`, `foreman_count_1`
**DON'T:** `Text10`, `ggggsssssssssss`, `Name_3234234`

### Template Creation Workflow
1. **Design Layout** - Sketch form, identify fields, plan positions
2. **Create in Adobe Acrobat Pro** - File → Create → Blank Page, Tools → Prepare Form
3. **Set Field Properties** - Multiline for descriptions, proper alignment, tab order
4. **Test with Sample Data** - Fill manually, check overflow, verify accessibility
5. **Integrate into App** - Add to `assets/templates/`, update `pubspec.yaml`, create field mapping

### Template Structure Best Practices
- Page 1: Header + Primary Data (project info, main contractor)
- Page 2: Secondary Data (additional contractors, activities)
- Page 3: Summary + Signatures (safety, materials, signature fields)

## Template Modification

### When to Modify vs Create New
**Modify:** Fixing typos, adjusting sizes, adding 1-2 fields
**Create New:** Significant layout changes, different structure, many new fields

### Renaming Fields in Adobe Acrobat
1. Tools → Prepare Form
2. Right-click field → Properties
3. Change Name in General tab
4. Update corresponding code mapping

### Preserving Mappings
1. Document current field names before changes
2. Make changes incrementally
3. Test after each modification
4. Update `pdf_service.dart` mappings immediately

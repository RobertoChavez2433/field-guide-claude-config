# Tech Stack

## Core
| Component | Version |
|-----------|---------|
| Flutter | 3.38+ |
| Dart | 3.10+ |
| Android SDK | 36 (min 24) |
| iOS | 15.0+ |

## Key Packages
| Package | Purpose |
|---------|---------|
| provider | State management |
| go_router | Navigation |
| supabase_flutter | Backend/Auth |
| sqflite | Local storage |
| syncfusion_flutter_pdf | PDF generation |
| pdfx | PDF rendering to images |
| printing | PDF preview/rasterization |
| flusseract | Tesseract OCR (replaces flutter_tesseract_ocr, Session 280) |
| syncfusion_flutter_pdfviewer | PDF viewing/rendering |
| image | Image preprocessing |
| xml | HOCR parsing |

## Custom Packages
| Package | Location | Purpose |
|---------|----------|---------|
| flusseract | `packages/flusseract/` | Tesseract OCR plugin (all platforms) |

## Build Commands
```bash
flutter pub get          # Dependencies
flutter analyze          # Lint
flutter test             # Unit tests
flutter run              # Debug
flutter build apk        # Android release
```

## Debug Commands
```bash
# PDF Parser Diagnostics - verbose logging for PDF pipeline
flutter run --dart-define=PDF_PARSER_DIAGNOSTICS=true
flutter test test/features/pdf/ --dart-define=PDF_PARSER_DIAGNOSTICS=true
```

## Development Tools
| Tool | Location | Purpose |
|------|----------|---------|
| run_and_tail_logs.ps1 | `tools/` | Run app with live log tailing |
| dump_inspect.py | `tools/` | Crash dump analysis |

## Detailed References
- Platform versions: `.claude/rules/platform-standards.md`
- Architecture: `.claude/rules/architecture.md`
- Database schema: `lib/core/database/database_service.dart:50-215`
- OCR architecture: `lib/features/pdf/services/ocr/`

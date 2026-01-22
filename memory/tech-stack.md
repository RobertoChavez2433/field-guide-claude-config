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

## Build Commands
```bash
flutter pub get          # Dependencies
flutter analyze          # Lint
flutter test             # Unit tests
flutter run              # Debug
flutter build apk        # Android release
```

## Detailed References
- Platform versions: `.claude/docs/2026-platform-standards-update.md`
- Architecture: `.claude/docs/architectural_patterns.md`
- Database schema: `lib/core/database/database_service.dart:50-215`

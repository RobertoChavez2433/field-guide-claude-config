# Tech Stack & Environment

## Framework & Dependencies

| Layer | Technology | Version |
|-------|------------|---------|
| Framework | Flutter | 3.38+ |
| Language | Dart | 3.10+ |
| Platforms | Android, iOS, Windows | - |
| Local DB | SQLite | via sqflite |
| Cloud Backend | Supabase | PostgreSQL + Storage |
| State | Provider | ChangeNotifier pattern |
| Navigation | go_router | Shell routes for tabs |
| PDF | syncfusion_flutter_pdf | + printing package |
| Images | image_picker, geolocator | Camera + GPS |
| Weather | Open-Meteo API | Free, no key |

## Build Commands

```bash
# Dependencies
flutter pub get

# Analyze (run before commits)
flutter analyze

# Run on Windows
flutter run -d windows

# Run on connected device
flutter run

# Build release APK
flutter build apk --release

# Build Windows release
flutter build windows --release
```

## Test Commands

```bash
# Run all tests
flutter test

# Run with coverage
flutter test --coverage

# Run specific test file
flutter test test/path/to/test.dart
```

## Environment Setup

1. **Flutter SDK**: `C:\Flutter\flutter\bin\`
2. **Windows**: Developer Mode enabled
3. **Android**: Android Studio + SDK installed
4. **iOS**: macOS + Xcode (not available on this machine)

## Reference Documents

| Document | Location |
|----------|----------|
| Target PDF Template | `Pre-devolopment and brainstorming/Screenshot examples/IDR 2025-05-12 RBWS 864130.pdf` |
| Notion Workflow | `Pre-devolopment and brainstorming/Screenshot examples/Latest Notion Page*.png` |
| Requirements | `Pre-devolopment and brainstorming/PROJECT_SUMMARY.md` |
| Architecture | `.claude/docs/architectural_patterns.md` |
| Database Schema | `lib/core/database/database_service.dart` |
| Route Definitions | `lib/core/router/app_router.dart:15-100` |

## Supabase

- **CLI**: `npx supabase` (installed locally via npm)
- **Schema**: `supabase_schema_v3.sql` (latest)
- **Storage**: `photos` bucket for images

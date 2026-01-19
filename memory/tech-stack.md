# Tech Stack

## Core Framework
| Component | Version | Documentation |
|-----------|---------|---------------|
| Flutter | 3.38+ | https://docs.flutter.dev |
| Dart | 3.10+ | https://dart.dev/guides |
| SDK | ^3.10.7 | pubspec.yaml |

## State Management
| Package | Version | Docs |
|---------|---------|------|
| provider | ^6.1.2 | https://pub.dev/packages/provider |

## Navigation
| Package | Version | Docs |
|---------|---------|------|
| go_router | ^14.6.2 | https://pub.dev/packages/go_router |

## Backend & Auth
| Service | Version | Docs |
|---------|---------|------|
| Supabase Flutter | ^2.8.3 | https://supabase.com/docs/reference/dart |
| Supabase CLI | npx | https://supabase.com/docs/reference/cli |

## Local Storage
| Package | Version | Docs |
|---------|---------|------|
| sqflite | ^2.4.1 | https://pub.dev/packages/sqflite |
| sqflite_common_ffi | ^2.3.4 | Desktop support |

## PDF Generation
| Package | Version | Docs |
|---------|---------|------|
| pdf | ^3.11.1 | https://pub.dev/packages/pdf |
| printing | ^5.13.4 | https://pub.dev/packages/printing |
| syncfusion_flutter_pdf | ^27.1.48 | https://help.syncfusion.com/flutter/pdf |

## Media & Location
| Package | Version | Purpose |
|---------|---------|---------|
| image_picker | ^1.1.2 | Camera/gallery |
| geolocator | ^13.0.2 | GPS coordinates |
| geocoding | ^3.0.0 | Address lookup |

## External APIs
| Service | Auth | Docs |
|---------|------|------|
| Open-Meteo | None (free) | https://open-meteo.com/en/docs |

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

## Reference Documents

| Document | Location |
|----------|----------|
| Target PDF Template | `Pre-devolopment and brainstorming/Screenshot examples/IDR 2025-05-12 RBWS 864130.pdf` |
| Requirements | `Pre-devolopment and brainstorming/PROJECT_SUMMARY.md` |
| Architecture | `.claude/docs/architectural_patterns.md` |
| Database Schema | `lib/services/database_service.dart:50-215` |
| Route Definitions | `lib/core/router/app_router.dart:15-100` |

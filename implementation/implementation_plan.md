# Field Guide App - Implementation Plan
## Updated: 2026-01-20

---

## Executive Summary

**App Name**: Field Guide (Construction Inspector App)
**Current State**: Feature-First Reorganization COMPLETE, Testing Infrastructure COMPLETE
**Tests**: 392 passing (363 unit + 29 golden)
**Analyzer**: 0 errors, ~21 info warnings (expected deprecations)

---

## Session 12 Completed Work

### Data Layer Fixes (3 agents)

| Task | Status | Details |
|------|--------|---------|
| Add `updatedAt` to 9 models | Complete | DB version 9, backward compatible |
| PhotoRepository RepositoryResult | Complete | Consistent error handling pattern |
| Migration error handling | Complete | `_addColumnIfNotExists` helper |

### Testing Infrastructure (2 agents)

| Task | Status | Details |
|------|--------|---------|
| Golden Tests | Complete | 29 tests, 7 files, 28 baseline images |
| Patrol Tests | Complete | 15 tests, 4 files, native automation |

### Code Reviews (3 agents)

| Review | Score | Status |
|--------|-------|--------|
| Data Layer | 8.5/10 | No critical issues |
| Golden Tests | 8.5/10 | No critical issues |
| Patrol Tests | 8.5/10 | No critical issues |

---

## Test Coverage

### Current Test Suite (392 total)

| Category | Count | Location |
|----------|-------|----------|
| Unit Tests | 363 | `test/` |
| Golden Tests | 29 | `test/golden/` |
| Patrol Tests | 15 | `integration_test/patrol/` (ready to run) |

### Golden Test Coverage

**Themes (12 tests)**:
- Dark theme (5 tests)
- Light theme (4 tests)
- High contrast theme (3 tests)

**Widgets (17 tests)**:
- Confirmation dialogs (6 tests)
- Entry cards (4 tests)
- Project cards (6 tests)
- Weather widgets (4 tests)

### Patrol Test Coverage

**Native Interactions (15 tests)**:
- App smoke test (3 tests)
- Camera permissions (3 tests)
- Location permissions (4 tests)
- Photo capture (5 tests)

---

## Commands Reference

### Run Tests
```bash
# All unit tests
flutter test

# Golden tests
flutter test test/golden/

# Update golden images
flutter test --update-goldens test/golden/

# Patrol tests (requires device)
patrol test
```

### Analysis
```bash
flutter analyze
```

---

## Priority Action Items

### CRITICAL (Before Production)

1. [x] Fix inconsistent `updatedAt` tracking - DONE
2. [x] Fix PhotoRepository error handling - DONE
3. [x] Fix migration error handling - DONE
4. [ ] Fix Supabase credentials (use environment variables)
5. [ ] Fix ProjectProvider unsafe firstWhere calls
6. [ ] Add mounted checks to auto-save async operations
7. [ ] Handle entry creation failure (show error to user)

### HIGH (Next Sprint)

8. [ ] Migrate deprecated barrel imports to feature-specific
9. [ ] Add Key widgets to UI for Patrol tests
10. [ ] Implement auth flow for Patrol tests
11. [ ] Decompose mega-screens (home_screen, entry_wizard_screen)
12. [ ] Implement dead letter queue for failed syncs

### MEDIUM (Technical Debt)

13. [ ] Activate TolerantGoldenFileComparator
14. [ ] Add golden tests for error/loading/empty states
15. [ ] Add screen-level golden tests
16. [ ] Extract DRY patterns in Patrol tests
17. [ ] Split theme file into separate files

---

## Code Review Findings Summary

### Data Layer (8.5/10)
- **Positive**: Excellent defensive migration, consistent model patterns
- **Suggestion**: Extract timestamp parsing utility (DRY)
- **Minor**: EntryPersonnel/EntryEquipment null handling inconsistent

### Golden Tests (8.5/10)
- **Positive**: Excellent helpers, comprehensive theme coverage
- **Suggestion**: Activate TolerantGoldenFileComparator
- **Suggestion**: Add test lifecycle hooks (setUpAll)
- **Gap**: Missing error/loading/empty state tests

### Patrol Tests (8.5/10)
- **Positive**: Excellent documentation, graceful degradation
- **Suggestion**: Add Key widgets to critical UI elements
- **Suggestion**: Implement authentication helper
- **Fix Needed**: Remove deprecated `.or()` from README

---

## File Locations

### New Test Infrastructure

```
test/golden/
├── goldens/              # 28 baseline images
├── themes/               # 3 theme test files
├── widgets/              # 4 widget test files
├── test_helpers.dart     # Golden test utilities
└── README.md             # Documentation

integration_test/patrol/
├── app_smoke_test.dart
├── camera_permission_test.dart
├── location_permission_test.dart
├── photo_capture_test.dart
├── test_bundle.dart
├── README.md
├── QUICK_START.md
└── setup_patrol.md
```

### Modified Data Layer Files

```
lib/features/*/data/models/   # 9 models with updatedAt
lib/features/photos/data/repositories/photo_repository.dart
lib/core/database/database_service.dart  # Version 9
```

---

## Deprecated Imports Migration

The following imports need to be migrated (21 files):

**Lib files**:
- `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`
- `lib/features/entries/presentation/screens/entry_wizard_screen.dart`
- `lib/features/entries/presentation/screens/home_screen.dart`
- `lib/features/entries/presentation/screens/report_screen.dart`
- `lib/features/pdf/services/photo_pdf_service.dart`
- `lib/features/settings/presentation/screens/personnel_types_screen.dart`
- `lib/main.dart`
- `lib/services/sync_service.dart`

**Test files**:
- `test/data/models/bid_item_test.dart`
- `test/data/models/daily_entry_test.dart`
- `test/data/models/photo_test.dart`
- `test/data/repositories/bid_item_repository_test.dart`
- `test/data/repositories/daily_entry_repository_test.dart`
- `test/data/repositories/entry_quantity_repository_test.dart`
- `test/data/repositories/photo_repository_test.dart`
- `test/helpers/test_helpers.dart`
- `test/presentation/providers/daily_entry_provider_test.dart`
- `test/services/photo_service_test.dart`

**Migration Pattern**:
```dart
// OLD (deprecated)
import 'package:construction_inspector/data/models/models.dart';

// NEW (feature-specific)
import 'package:construction_inspector/features/projects/data/models/project.dart';
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';
```

---

## Next Session Priorities

1. Fix remaining CRITICAL issues (Supabase credentials, ProjectProvider)
2. Migrate deprecated imports (21 files)
3. Add Key widgets for Patrol test reliability
4. Run Patrol tests on device to verify

---

## Historical Notes

- Session 12: Testing infrastructure complete (golden + patrol)
- Session 11: Rules files optimization
- Session 10: Claude config efficiency refactoring
- Sessions 1-9: Feature-first reorganization (15 phases)

See `.claude/logs/session-log.md` for full history.

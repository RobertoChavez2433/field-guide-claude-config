# E2E Test Key Coverage Remediation Plan

**Goal**: Stabilize Patrol E2E tests by eliminating brittle text/icon selectors, ensuring every testable UI element has a TestingKeys entry, and consolidating legacy tests.

**Target**: 95% test pass rate after each PR

---

## Current State

| Metric | Count |
|--------|-------|
| Total test cases | 68 |
| Test files | 26 |
| Text selectors (`$('...')`) | 170+ |
| Hardcoded keys (`Key('...')`) | 2 |
| Legacy tests to consolidate | 11 files |

---

## Phase 0: Seed Data Fixture (BLOCKER)

**Scope**: Create deterministic test data with known IDs for dynamic key testing.

### Files to Create/Modify
- `integration_test/patrol/fixtures/test_seed_data.dart` (new)
- `integration_test/patrol/helpers/test_database_helper.dart` (new)

### Seed Data Required
```dart
// Known IDs for dynamic key testing
const seedProjectId = 'test-project-001';
const seedLocationId = 'test-location-001';
const seedEntryId = 'test-entry-001';
const seedContractorId = 'test-contractor-001';
const seedBidItemId = 'test-biditem-001';
const seedPhotoId = 'test-photo-001';
```

### Verification
```bash
# Run smoke test with seed data
patrol test integration_test/patrol/app_smoke_test.dart
```

---

## Phase 1: Fix Entry Wizard Test Logic (CRITICAL)

**Scope**: Fix fundamental mismatch - tests assume tabs but entry wizard uses scrollable sections.

### Problem
Tests tap `$('Quantities')`, `$('Activities')`, `$('Weather')` as tabs, but entry wizard is a `SingleChildScrollView` with Card sections.

### Files to Modify

| File | Changes |
|------|---------|
| `lib/shared/testing_keys.dart` | Add 5 section keys |
| `lib/features/entries/presentation/screens/entry_wizard_screen.dart` | Assign section keys to Cards |
| `lib/features/entries/presentation/widgets/entry_basics_section.dart` | Add wrapper key |
| `lib/features/entries/presentation/widgets/entry_safety_section.dart` | Add wrapper key + 5 field keys |
| `integration_test/patrol/helpers/patrol_test_helpers.dart` | Add `scrollToSection()` helper |

### New Keys
```dart
// Section headers for scroll targeting
static const entryBasicsSection = Key('entry_basics_section');
static const entryPersonnelSection = Key('entry_personnel_section');
static const entryActivitiesSection = Key('entry_activities_section');
static const entryQuantitiesSection = Key('entry_quantities_section');
static const entrySafetySection = Key('entry_safety_section');

// Safety section fields (missing)
static const entryWizardSiteSafety = Key('entry_wizard_site_safety');
static const entryWizardSescMeasures = Key('entry_wizard_sesc_measures');
static const entryWizardTrafficControl = Key('entry_wizard_traffic_control');
static const entryWizardVisitors = Key('entry_wizard_visitors');
static const entryWizardExtras = Key('entry_wizard_extras');
```

### Test Logic Fix
```dart
// BEFORE (fails - no tabs exist)
await $('Quantities').tap();

// AFTER (works - scroll to section)
await h.scrollToSection(TestingKeys.entryQuantitiesSection);
```

### Tests to Update
- `quantities_flow_test.dart` - Replace all tab taps with scroll
- `entry_management_test.dart` - Replace tab navigation
- `e2e_tests/entry_lifecycle_test.dart` - Verify scroll works

### Verification
```bash
patrol test integration_test/patrol/quantities_flow_test.dart
patrol test integration_test/patrol/entry_management_test.dart
# Target: 95% pass (5/5 quantities tests, 1/1 entry test)
```

---

## Phase 2: Settings Theme + Help/Version Keys

**Scope**: Add keys to all settings interactive elements including theme options, help, and version tiles.

### Files to Modify

| File | Changes |
|------|---------|
| `lib/shared/testing_keys.dart` | Add 10+ settings keys |
| `lib/features/settings/presentation/screens/settings_screen.dart` | Assign keys to RadioListTiles, tiles |

### New Keys
```dart
// Theme options (individual RadioListTile keys)
static const settingsThemeDark = Key('settings_theme_dark');
static const settingsThemeLight = Key('settings_theme_light');
static const settingsThemeHighContrast = Key('settings_theme_high_contrast');

// Help & Version
static const settingsHelpSupportTile = Key('settings_help_support_tile');
static const settingsVersionTile = Key('settings_version_tile');
static const settingsLicensesTile = Key('settings_licenses_tile');

// Data management
static const settingsBackupTile = Key('settings_backup_tile');
static const settingsRestoreTile = Key('settings_restore_tile');
static const settingsClearCacheTile = Key('settings_clear_cache_tile');

// Section headers
static const settingsAppearanceSection = Key('settings_appearance_section');
static const settingsUserSection = Key('settings_user_section');
static const settingsAccountSection = Key('settings_account_section');
static const settingsDataSection = Key('settings_data_section');
```

### Tests to Update
- `settings_flow_test.dart` - Replace `$('Dark')`, `$('Light')`, `$('About')` with keys
- `e2e_tests/settings_theme_test.dart` - Use new theme keys

### Verification
```bash
patrol test integration_test/patrol/settings_flow_test.dart
patrol test integration_test/patrol/e2e_tests/settings_theme_test.dart
# Target: 95% pass (5/5 settings tests, 4/4 theme tests)
```

---

## Phase 3: Centralize Dynamic Keys

**Scope**: Move all inline dynamic key patterns to TestingKeys helpers.

### Files to Modify

| File | Changes |
|------|---------|
| `lib/shared/testing_keys.dart` | Add 6 dynamic key helpers |
| `lib/features/entries/presentation/screens/entry_wizard_screen.dart` | Use centralized helpers |

### New Dynamic Key Helpers
```dart
// Contractor/Equipment (currently inline)
static Key contractorCheckbox(String id) => Key('contractor_checkbox_$id');
static Key equipmentChip(String id) => Key('equipment_chip_$id');

// Quantity actions
static Key quantityEditButton(String bidItemId) => Key('quantity_edit_$bidItemId');
static Key quantityDeleteButton(String bidItemId) => Key('quantity_delete_$bidItemId');

// Bid item picker
static Key bidItemPickerItem(String bidItemId) => Key('bid_item_picker_$bidItemId');

// Location
static Key locationCard(String locationId) => Key('location_card_$locationId');
```

### Verification
```bash
patrol test integration_test/patrol/e2e_tests/entry_lifecycle_test.dart
# Target: 95% pass
```

---

## Phase 4: Quantity Flow Keys + Test Migration

**Scope**: Add all quantity-related keys and migrate quantities_flow_test.dart (~35 selectors).

### Files to Modify

| File | Changes |
|------|---------|
| `lib/shared/testing_keys.dart` | Add 8 quantity keys |
| `lib/features/entries/presentation/screens/entry_wizard_screen.dart` | Assign keys to quantity widgets |

### New Keys
```dart
// Quantity section controls
static const quantityAddButton = Key('quantity_add_button');
static const quantityDialog = Key('quantity_dialog');
static const quantityBidItemDropdown = Key('quantity_bid_item_dropdown');
static const quantityAmountField = Key('quantity_amount_field');
static const quantityNotesField = Key('quantity_notes_field');
static const quantityDialogSave = Key('quantity_dialog_save');
static const quantityDialogCancel = Key('quantity_dialog_cancel');

// Bid item picker
static const bidItemPickerDialog = Key('bid_item_picker_dialog');
static const bidItemPickerSearch = Key('bid_item_picker_search');
static const bidItemPickerClose = Key('bid_item_picker_close');
```

### Test Consolidation
- Move `integration_test/patrol/quantities_flow_test.dart` -> `integration_test/patrol/e2e_tests/quantities_flow_test.dart`
- Update `test_bundle.dart` imports

### Verification
```bash
patrol test integration_test/patrol/e2e_tests/quantities_flow_test.dart
# Target: 95% pass (5/5 tests)
```

---

## Phase 5: Contractor Flow Keys + Test Migration

**Scope**: Add contractor-related keys and migrate contractors_flow_test.dart (~25 selectors).

### Files to Modify

| File | Changes |
|------|---------|
| `lib/shared/testing_keys.dart` | Add 6 contractor keys |
| `lib/features/projects/presentation/screens/project_setup_screen.dart` | Assign keys |

### New Keys
```dart
// Contractor list
static const contractorAddButton = Key('contractor_add_button');
static Key contractorCard(String id) => Key('contractor_card_$id');
static Key contractorEditButton(String id) => Key('contractor_edit_$id');
static Key contractorDeleteButton(String id) => Key('contractor_delete_$id');

// Contractor type options
static const contractorTypePrime = Key('contractor_type_prime');
static const contractorTypeSub = Key('contractor_type_sub');
static const contractorTypeSupplier = Key('contractor_type_supplier');
```

### Test Consolidation
- Move `integration_test/patrol/contractors_flow_test.dart` -> `integration_test/patrol/e2e_tests/contractors_flow_test.dart`

### Verification
```bash
patrol test integration_test/patrol/e2e_tests/contractors_flow_test.dart
# Target: 95% pass (4/4 tests)
```

---

## Phase 6: Navigation + Helper Normalization

**Scope**: Fix navigation helpers and remaining nav-related text selectors.

### Files to Modify

| File | Changes |
|------|---------|
| `integration_test/patrol/helpers/patrol_test_helpers.dart` | Refactor `navigateToTab()` to use Keys |

### Helper Changes
```dart
// BEFORE
Future<void> navigateToTab(String tabKey, String tabName) async {
  await $(Key(tabKey)).tap();  // Constructs key from string
}

// AFTER
Future<void> navigateToTab(Key tabKey) async {
  await $(tabKey).tap();  // Uses TestingKeys directly
}

// Convenience wrappers
Future<void> navigateToDashboard() => navigateToTab(TestingKeys.dashboardNavButton);
Future<void> navigateToCalendar() => navigateToTab(TestingKeys.calendarNavButton);
Future<void> navigateToProjects() => navigateToTab(TestingKeys.projectsNavButton);
Future<void> navigateToSettings() => navigateToTab(TestingKeys.settingsNavButton);
```

### Tests to Update
- `navigation_flow_test.dart` - Replace `$('Home')`, `$('Projects')`, `$('Settings')`

### Verification
```bash
patrol test integration_test/patrol/navigation_flow_test.dart
# Target: 95% pass (3/3 tests)
```

---

## Phase 7: Offline/Sync Keys + Test Migration

**Scope**: Add sync status keys and migrate offline_mode_test.dart (~20 selectors).

### Files to Modify

| File | Changes |
|------|---------|
| `lib/shared/testing_keys.dart` | Add 5 sync keys |
| `lib/features/sync/presentation/widgets/sync_status_indicator.dart` | Assign keys |

### New Keys
```dart
static const offlineIndicator = Key('offline_indicator');
static const pendingChangesCount = Key('pending_changes_count');
static const lastSyncTimestamp = Key('last_sync_timestamp');
static const syncProgressIndicator = Key('sync_progress_indicator');
static const syncErrorMessage = Key('sync_error_message');
```

### Test Consolidation
- Merge `integration_test/patrol/offline_mode_test.dart` into `integration_test/patrol/e2e_tests/offline_sync_test.dart`

### Verification
```bash
patrol test integration_test/patrol/e2e_tests/offline_sync_test.dart
# Target: 95% pass
```

---

## Phase 8: Auth + Remaining Legacy Test Migration

**Scope**: Migrate remaining legacy tests and add any missing auth keys.

### Files to Consolidate

| From | To | Action |
|------|-----|--------|
| `patrol/app_smoke_test.dart` | `e2e_tests/app_smoke_test.dart` | Move + update keys |
| `patrol/auth_flow_test.dart` | `e2e_tests/auth_flow_test.dart` | Move + fix hardcoded key |
| `patrol/photo_capture_test.dart` | Merge into `e2e_tests/photo_flow_test.dart` | Consolidate |
| `patrol/entry_management_test.dart` | `e2e_tests/entry_management_test.dart` | Move |
| `patrol/project_management_test.dart` | Already in e2e_tests | Delete legacy |
| `patrol/location_permission_test.dart` | `isolated/location_permission_test.dart` | Keep isolated |
| `patrol/camera_permission_test.dart` | `isolated/camera_permission_test.dart` | Keep isolated |

### Fix Hardcoded Key
```dart
// auth_flow_test.dart:334 - BEFORE
final submitButton = $(Key('reset_password_submit_button'));

// AFTER
final submitButton = $(TestingKeys.resetPasswordSendButton);
```

### Update test_bundle.dart
- Remove old imports
- Add new e2e_tests imports
- Update group names

### Verification
```bash
patrol test integration_test/test_bundle.dart
# Target: 95% pass (65/68 tests)
```

---

## Phase 9: Final Cleanup + Documentation

**Scope**: Remove empty legacy files, update documentation, add CI validation.

### Files to Delete
- `integration_test/patrol/quantities_flow_test.dart` (moved)
- `integration_test/patrol/contractors_flow_test.dart` (moved)
- `integration_test/patrol/settings_flow_test.dart` (moved)
- `integration_test/patrol/offline_mode_test.dart` (merged)
- `integration_test/patrol/auth_flow_test.dart` (moved)
- `integration_test/patrol/app_smoke_test.dart` (moved)
- `integration_test/patrol/navigation_flow_test.dart` (moved)
- `integration_test/patrol/photo_capture_test.dart` (merged)
- `integration_test/patrol/entry_management_test.dart` (moved)
- `integration_test/patrol/project_management_test.dart` (duplicate)

### Documentation Updates
- `integration_test/patrol/README.md` - Updated structure
- `integration_test/patrol/REQUIRED_UI_KEYS.md` - Key inventory
- `.claude/docs/testing-guide.md` - E2E testing best practices

### CI Validation Script
```bash
# Add to CI - fails if any text selectors found
rg "\\\$\\('" integration_test/patrol/e2e_tests --type dart | grep -v "// content-verification" && exit 1 || exit 0
```

### Final Verification
```bash
# Full test suite
patrol test integration_test/test_bundle.dart

# Verify no text selectors (except content verification)
rg "\$\('" integration_test/patrol/e2e_tests --type dart
```

---

## Summary

| Phase | Scope | Keys Added | Selectors Removed | Tests Fixed |
|-------|-------|------------|-------------------|-------------|
| 0 | Seed Data | 0 | 0 | Enables dynamic keys |
| 1 | Entry Wizard Logic | 10 | ~15 | 6 |
| 2 | Settings Theme/Help | 13 | ~10 | 9 |
| 3 | Dynamic Keys | 6 | ~8 | - |
| 4 | Quantities | 10 | ~35 | 5 |
| 5 | Contractors | 7 | ~25 | 4 |
| 6 | Navigation | 0 | ~10 | 3 |
| 7 | Offline/Sync | 5 | ~20 | 7 |
| 8 | Auth + Legacy | 1 | ~40 | 15 |
| 9 | Cleanup | 0 | ~7 | - |
| **Total** | | **52** | **170+** | **49** |

---

## Final Structure

```
integration_test/
├── patrol/
│   ├── e2e_tests/           # All consolidated E2E tests
│   │   ├── app_smoke_test.dart
│   │   ├── auth_flow_test.dart
│   │   ├── contractors_flow_test.dart
│   │   ├── entry_lifecycle_test.dart
│   │   ├── entry_management_test.dart
│   │   ├── navigation_flow_test.dart
│   │   ├── offline_sync_test.dart
│   │   ├── photo_flow_test.dart
│   │   ├── project_management_test.dart
│   │   ├── quantities_flow_test.dart
│   │   └── settings_theme_test.dart
│   ├── isolated/           # Permission & edge case tests
│   │   ├── app_lifecycle_test.dart
│   │   ├── auth_validation_test.dart
│   │   ├── camera_permission_test.dart
│   │   ├── entry_validation_test.dart
│   │   ├── location_permission_test.dart
│   │   └── navigation_edge_test.dart
│   ├── fixtures/           # Test data
│   │   └── test_seed_data.dart
│   ├── helpers/            # Test utilities
│   │   ├── patrol_test_helpers.dart
│   │   ├── test_database_helper.dart
│   │   └── README.md
│   ├── README.md
│   └── REQUIRED_UI_KEYS.md
└── test_bundle.dart
```

---

## Completion Criteria

1. `rg "\$\('" integration_test/patrol/e2e_tests` returns only explicit content assertions
2. `rg "Key\('" integration_test/patrol` returns 0 hardcoded keys
3. All flows pass 3x in a row on real device
4. 95%+ test pass rate on full bundle
5. All legacy tests consolidated into `e2e_tests/` or `isolated/`

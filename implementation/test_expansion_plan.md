# Patrol Test Expansion Plan

**Last Updated**: 2026-01-21
**Status**: READY FOR IMPLEMENTATION
**Source**: User request for comprehensive Patrol integration test coverage expansion

---

## Executive Summary

**Current State**: 85 tests across 13 files - primarily UI navigation and happy-path flows
**Gap Analysis**: Missing form validation, CRUD completeness, photo workflows, end-to-end scenarios
**Proposal**: Add 120+ targeted tests across 4 phases to achieve comprehensive feature coverage

### Coverage Gaps Identified

| Category | Current | Target | Gap |
|----------|---------|--------|-----|
| Form Validation | 3 tests (auth only) | 35 tests | +32 tests |
| CRUD Operations | 15 tests (incomplete) | 45 tests | +30 tests |
| Photo Workflows | 0 actual tests | 15 tests | +15 tests |
| End-to-End Flows | 5 tests | 25 tests | +20 tests |
| Data Integrity | 0 tests | 15 tests | +15 tests |
| Edge Cases | 2 tests | 10 tests | +8 tests |

**Total New Tests**: ~120 tests (bringing total to ~205 tests)

### Batch Allocation Strategy

Current batch configuration supports ~20 tests per batch with 12G heap. Proposed distribution:

| Test File | Current | New | Total | Batch Assignment |
|-----------|---------|-----|-------|------------------|
| auth_flow_test.dart | 10 | 5 | 15 | Batch 1 |
| project_management_test.dart | 9 | 18 | 27 | Batches 2-3 |
| entry_management_test.dart | 11 | 25 | 36 | Batches 4-6 |
| contractors_flow_test.dart | 4 | 20 | 24 | Batches 7-8 |
| quantities_flow_test.dart | 5 | 22 | 27 | Batches 9-10 |
| photo_capture_test.dart | 5 | 15 | 20 | Batch 11 |
| settings_flow_test.dart | 6 | 10 | 16 | Batch 12 |
| offline_mode_test.dart | 10 | 5 | 15 | Batch 13 |
| **NEW: locations_flow_test.dart** | 0 | 15 | 15 | Batch 14 |
| **NEW: pdf_export_test.dart** | 0 | 12 | 12 | Batch 15 |
| **NEW: data_integrity_test.dart** | 0 | 8 | 8 | Batch 16 |

---

## Phase 1: Form Validation & Input Testing (Priority: CRITICAL)

**Rationale**: Validation tests prevent user errors and ensure data quality. Currently ZERO validation tests except basic auth.

**Duration Estimate**: 2-3 days
**Agent**: qa-testing-agent

### Task 1.1: Project Form Validation

**File**: `integration_test/patrol/project_management_test.dart`

**New Tests to Add** (8 tests):

1. **validates empty project name shows error**
   - Open create dialog
   - Leave name field empty
   - Tap create button
   - Verify error message "Project name is required"

2. **validates project name minimum length**
   - Enter name with 1 character
   - Verify error "Name must be at least 3 characters"

3. **validates project name maximum length**
   - Enter 101 characters
   - Verify error or truncation to 100 chars

4. **validates MDOT number format when MDOT enabled**
   - Enable MDOT toggle
   - Enter invalid format "ABC123"
   - Verify error "MDOT number must be 6 digits"

5. **validates start date is before end date**
   - Set end date before start date
   - Verify error "End date must be after start date"

6. **validates required location when creating project**
   - Leave location field empty
   - Verify cannot save without location

7. **validates duplicate project names**
   - Create project "Test Project"
   - Try creating another with same name
   - Verify warning or automatic disambiguation

8. **validates archive confirmation before archiving**
   - Swipe to archive
   - Verify confirmation dialog appears
   - Cancel and verify project still active

### Task 1.2: Daily Entry Form Validation

**File**: `integration_test/patrol/entry_management_test.dart`

**New Tests to Add** (12 tests):

1. **validates required location selection**
   - Open entry wizard
   - Leave location unselected
   - Attempt to save
   - Verify error "Location is required"

2. **validates temperature low is less than high**
   - Enter temp low: 75, temp high: 65
   - Verify error "Low temp cannot exceed high temp"

3. **validates temperature range limits**
   - Enter temp: -150 (below valid range)
   - Verify error or clamping to valid range

4. **validates activities field not empty for submitted entries**
   - Leave activities blank
   - Try to submit (not save as draft)
   - Verify error "Activities required for submitted entries"

5. **validates personnel count is numeric**
   - Enter "abc" in personnel count field
   - Verify input rejected or error shown

6. **validates equipment hours are non-negative**
   - Enter -5 hours for equipment
   - Verify error "Hours must be positive"

7. **validates date cannot be in future**
   - Select date tomorrow
   - Verify error "Cannot create entries for future dates"

8. **validates cannot submit entry without weather data**
   - Leave weather section blank
   - Attempt submit
   - Verify error "Weather data required"

9. **validates photo caption length limit**
   - Capture photo
   - Enter 500+ character caption
   - Verify truncation or error

10. **validates contractor selection before adding equipment**
    - Try adding equipment without contractor selected
    - Verify error "Select contractor first"

11. **validates quantity cannot exceed bid item total**
    - Add quantity 1000 for bid item with total 500
    - Verify warning "Exceeds bid item total"

12. **validates unique entry per location per date**
    - Create entry for Location A on Jan 15
    - Try creating another for Location A on Jan 15
    - Verify error or warning

### Task 1.3: Contractor Form Validation

**File**: `integration_test/patrol/contractors_flow_test.dart`

**New Tests to Add** (6 tests):

1. **validates empty contractor name shows error**
   - Open add contractor dialog
   - Leave name empty
   - Tap save
   - Verify error "Contractor name required"

2. **validates contractor type must be selected**
   - Enter name but leave type dropdown unselected
   - Verify cannot save without type

3. **validates equipment name required**
   - Add equipment with empty name
   - Verify error "Equipment name required"

4. **validates equipment type must be selected**
   - Add equipment without type
   - Verify error shown

5. **validates duplicate equipment names within contractor**
   - Add equipment "Excavator #1"
   - Try adding another "Excavator #1" to same contractor
   - Verify error or disambiguation

6. **validates prime contractor uniqueness**
   - Set contractor A as prime
   - Try setting contractor B as prime
   - Verify warning "Only one prime contractor allowed" and auto-toggle

### Task 1.4: Quantities/Bid Items Form Validation

**File**: `integration_test/patrol/quantities_flow_test.dart`

**New Tests to Add** (6 tests):

1. **validates bid item number is unique**
   - Add bid item #100
   - Try adding another #100
   - Verify error "Bid item number already exists"

2. **validates bid item description required**
   - Enter number but leave description empty
   - Verify error "Description required"

3. **validates bid item quantity is positive**
   - Enter quantity: -10
   - Verify error "Quantity must be positive"

4. **validates bid item unit is selected**
   - Leave unit dropdown empty
   - Verify error "Unit is required"

5. **validates PDF import parsable format**
   - Import malformed PDF
   - Verify graceful error "Could not parse PDF items"

6. **validates manual entry fields all required**
   - Leave one field empty when adding manual bid item
   - Verify cannot save incomplete item

---

## Phase 2: CRUD Operation Completeness (Priority: HIGH)

**Rationale**: Current tests open dialogs but don't verify data modifications persist. Need full Create-Read-Update-Delete cycles.

**Duration Estimate**: 3-4 days
**Agent**: qa-testing-agent

### Task 2.1: Complete Project CRUD

**File**: `integration_test/patrol/project_management_test.dart`

**New Tests to Add** (10 tests):

1. **creates project and verifies it appears in list**
   - Create project "Alpha Project"
   - Close dialog
   - Verify project card with name "Alpha Project" exists
   - Tap card to verify details screen shows correct data

2. **edits project name and verifies change persists**
   - Open existing project
   - Tap edit icon
   - Change name from "Old Name" to "New Name"
   - Save
   - Navigate back and verify card shows "New Name"

3. **edits project location and verifies update**
   - Open project
   - Edit location field
   - Save
   - Reopen project and verify location changed

4. **toggles MDOT mode and verifies field visibility**
   - Create/edit project
   - Disable MDOT toggle
   - Verify MDOT number field hidden
   - Enable toggle
   - Verify field appears and accepts input

5. **changes project dates and verifies calendar update**
   - Edit project start/end dates
   - Save
   - Navigate to dashboard/calendar
   - Verify project timeline reflects new dates

6. **archives project and verifies removal from active list**
   - Swipe to archive
   - Confirm
   - Verify project no longer in main list
   - Verify archive count incremented

7. **unarchives project and verifies return to active list**
   - Navigate to archived projects
   - Tap unarchive
   - Return to main list
   - Verify project reappears

8. **deletes project with confirmation**
   - Long-press project or access delete option
   - Confirm deletion
   - Verify project completely removed
   - Verify associated data (entries/locations) handling

9. **searches projects by name**
   - Create multiple projects
   - Enter search term
   - Verify filtered list shows only matching projects

10. **filters projects by status (active/archived)**
    - Create mix of active and archived projects
    - Apply filter
    - Verify list updates correctly

### Task 2.2: Complete Entry CRUD

**File**: `integration_test/patrol/entry_management_test.dart`

**New Tests to Add** (8 tests):

1. **creates entry and verifies calendar shows it**
   - Create entry with wizard
   - Save as draft
   - Return to home screen
   - Verify entry card appears on selected date

2. **edits entry weather and verifies update**
   - Open existing entry
   - Change weather from sunny to rainy
   - Change temp values
   - Save
   - Reopen and verify weather data persisted

3. **edits entry activities and verifies text update**
   - Open entry
   - Modify activities text
   - Save
   - Verify inline view shows updated text

4. **adds contractor to entry and verifies association**
   - Open entry
   - Add contractor from list
   - Add personnel count
   - Save
   - Reopen and verify contractor appears

5. **removes contractor from entry**
   - Open entry with contractor
   - Tap remove/delete contractor
   - Save
   - Verify contractor no longer associated

6. **changes entry status draft to submitted**
   - Open draft entry
   - Fill required fields
   - Tap submit button
   - Verify status changes to "Submitted"
   - Verify cannot edit submitted entry (or requires unlock)

7. **deletes entry and verifies removal from calendar**
   - Open entry
   - Tap delete button
   - Confirm deletion
   - Return to calendar
   - Verify entry no longer visible

8. **filters calendar by location**
   - Create entries for different locations
   - Apply location filter
   - Verify calendar shows only matching entries

### Task 2.3: Complete Contractor CRUD

**File**: `integration_test/patrol/contractors_flow_test.dart`

**New Tests to Add** (8 tests):

1. **creates contractor and verifies in list**
   - Navigate to project contractors
   - Add contractor "Smith Construction"
   - Select type "Sub"
   - Save
   - Verify contractor appears in list with correct type badge

2. **edits contractor name and type**
   - Tap contractor
   - Edit name to "Smith Bros Construction"
   - Change type to "Prime"
   - Save
   - Verify updates persist

3. **deletes contractor and verifies removal**
   - Long-press or tap delete on contractor
   - Confirm deletion
   - Verify contractor removed from list

4. **adds equipment to contractor**
   - Open contractor details
   - Tap add equipment
   - Enter "Excavator CAT 320"
   - Select equipment type
   - Save
   - Verify equipment appears under contractor

5. **edits equipment details**
   - Open contractor
   - Tap equipment item
   - Change name and type
   - Save
   - Verify changes persist

6. **deletes equipment from contractor**
   - Open contractor with equipment
   - Delete equipment
   - Confirm
   - Verify equipment removed but contractor remains

7. **toggles contractor between prime and sub**
   - Set contractor as Prime
   - Verify badge/indicator changes
   - Toggle to Sub
   - Verify badge updates

8. **verifies equipment appears in entry wizard**
   - Create contractor with equipment
   - Open entry wizard
   - Navigate to equipment section
   - Verify equipment from contractor is selectable

### Task 2.4: Complete Quantities CRUD

**File**: `integration_test/patrol/quantities_flow_test.dart`

**New Tests to Add** (6 tests):

1. **creates manual bid item and verifies in list**
   - Navigate to quantities screen
   - Tap add manual
   - Enter item #100, description, quantity, unit
   - Save
   - Verify appears in sorted list

2. **edits bid item quantity and description**
   - Tap bid item
   - Modify quantity and description
   - Save
   - Verify changes persist and list updates

3. **deletes bid item and verifies removal**
   - Long-press or delete bid item
   - Confirm
   - Verify removed from list
   - Verify associated entry quantities handled

4. **imports bid items from PDF and verifies parsing**
   - Tap import PDF
   - Select valid PDF with items
   - Verify preview shows parsed items
   - Confirm import
   - Verify items appear in list

5. **adds quantity to bid item from entry**
   - Open daily entry
   - Navigate to quantities section
   - Select bid item and enter quantity
   - Save entry
   - Navigate to quantities screen
   - Verify bid item shows updated "used" quantity

6. **sorts bid items by number, description, and usage**
   - Create multiple bid items
   - Tap sort by number - verify ascending order
   - Tap sort by description - verify alphabetical
   - Tap sort by usage - verify high-to-low

---

## Phase 3: Photo Workflows & Integration (Priority: HIGH)

**Rationale**: Current photo tests press back to cancel - NO actual photo testing. Photos are critical for field app.

**Duration Estimate**: 2-3 days
**Agent**: qa-testing-agent

### Task 3.1: Photo Capture & Management

**File**: `integration_test/patrol/photo_capture_test.dart`

**New Tests to Add** (10 tests):

1. **captures photo and verifies thumbnail appears**
   - Open photo source dialog
   - Tap camera
   - Grant camera permission if needed
   - Use $.native.takePhoto()
   - Verify photo thumbnail appears in UI
   - Verify photo saved to local database

2. **selects photo from gallery and displays**
   - Open photo source dialog
   - Tap gallery
   - Use $.native.selectPhoto()
   - Verify photo appears
   - Verify imported to app storage

3. **renames photo and verifies caption update**
   - Capture photo
   - Tap photo thumbnail
   - Enter caption "Foundation pour - North side"
   - Save
   - Verify caption displays on thumbnail

4. **deletes photo and verifies removal**
   - Capture photo
   - Tap delete icon
   - Confirm deletion
   - Verify thumbnail removed
   - Verify file deleted from storage

5. **attaches multiple photos to entry**
   - Open entry wizard
   - Capture 3 photos in sequence
   - Save entry
   - Verify all 3 photos associated with entry
   - Verify count badge shows "3"

6. **views full-size photo from thumbnail**
   - Tap photo thumbnail
   - Verify full-size dialog/screen opens
   - Verify can swipe to next photo

7. **captures photo in offline mode**
   - Enable airplane mode (manual test note)
   - Capture photo
   - Verify photo saves locally
   - Verify sync status marked as pending

8. **verifies photo EXIF data captured**
   - Capture photo with GPS enabled
   - Open photo details
   - Verify timestamp captured
   - Verify GPS coordinates captured (if permission granted)

9. **handles camera permission denial gracefully**
   - Open camera
   - Use $.native.denyPermission()
   - Verify error message shown
   - Verify returns to previous screen without crash

10. **handles multiple photos in sequence without memory issues**
    - Capture 10 photos rapidly
    - Verify all 10 saved
    - Verify no memory errors
    - Verify thumbnails all render

### Task 3.2: Photo-Entry Integration

**File**: `integration_test/patrol/entry_management_test.dart`

**New Tests to Add** (5 tests):

1. **attaches photo to entry and verifies in report**
   - Create entry
   - Capture photo
   - Save entry
   - Navigate to report screen
   - Verify photo appears in report

2. **filters entries by "has photos"**
   - Create entries with and without photos
   - Apply filter "With Photos"
   - Verify only photo entries shown

3. **deletes entry with photos and verifies photo cleanup**
   - Create entry with 3 photos
   - Delete entry
   - Confirm deletion
   - Verify photos also deleted or orphaned appropriately

4. **edits entry photo caption after entry submitted**
   - Submit entry with photo
   - Reopen entry
   - Edit photo caption
   - Verify change allowed and persists

5. **exports entry as PDF and verifies photos included**
   - Create entry with photos
   - Export to PDF
   - Verify photos embedded in PDF

---

## Phase 4: End-to-End Workflows & Data Integrity (Priority: MEDIUM)

**Rationale**: Test realistic user journeys and cross-feature data consistency.

**Duration Estimate**: 3-4 days
**Agent**: qa-testing-agent

### Task 4.1: End-to-End User Journeys

**File**: `integration_test/patrol/e2e_workflows_test.dart` (NEW FILE)

**New Tests to Add** (15 tests):

1. **complete project setup to first entry workflow**
   - Create new project
   - Add location to project
   - Add contractor to project
   - Import bid items from PDF
   - Create first daily entry
   - Add weather, activities, contractor, quantities
   - Capture photo
   - Submit entry
   - Verify all data accessible from project dashboard

2. **multi-location project daily routine**
   - Create project with 3 locations
   - Create entry for Location A
   - Navigate back to calendar
   - Create entry for Location B same date
   - Verify both entries distinct
   - Filter calendar by location

3. **contractor equipment usage tracking**
   - Create contractor with 2 equipment items
   - Create entry and add equipment hours
   - Create second entry with different hours
   - Navigate to contractor details
   - Verify total hours accumulated

4. **bid item quantity tracking across entries**
   - Create bid item #200 with total 1000 CY
   - Entry 1: Add 100 CY
   - Entry 2: Add 150 CY
   - Navigate to quantities screen
   - Verify bid item shows 250 CY used, 750 remaining

5. **offline entry creation and sync workflow**
   - Enable offline mode (manual)
   - Create project
   - Create entry with photo
   - Verify sync status "Pending"
   - Re-enable network
   - Trigger manual sync
   - Verify sync status changes to "Synced"

6. **weekly report generation workflow**
   - Create 5 entries across week
   - Navigate to reports
   - Select date range
   - Generate report
   - Verify all entries included

7. **personnel type customization workflow**
   - Navigate to settings
   - Open personnel types
   - Add custom type "Safety Inspector"
   - Reorder types via drag-drop
   - Navigate to entry wizard
   - Verify custom type appears in dropdown

8. **theme change persistence workflow**
   - Navigate to settings
   - Change theme to Dark Mode
   - Close app ($.native.pressHome)
   - Reopen app ($.native.openApp)
   - Verify dark theme persists

9. **inspector profile setup workflow**
   - Navigate to settings
   - Enter inspector name "John Doe"
   - Enter initials "JD"
   - Save
   - Create new entry
   - Verify inspector name pre-populated

10. **auto-fetch weather workflow**
    - Enable auto-fetch weather in settings
    - Grant location permission
    - Create new entry
    - Wait for weather API call
    - Verify weather fields auto-populated

11. **photo attachment bulk workflow**
    - Create entry
    - Capture 5 photos in sequence
    - Add captions to each
    - Save entry
    - Navigate to report
    - Verify all 5 photos in order

12. **project archive and unarchive workflow**
    - Create project with entries
    - Archive project
    - Verify entries no longer in calendar
    - Unarchive project
    - Verify entries reappear

13. **contractor deletion with dependencies workflow**
    - Create contractor
    - Add contractor to 3 entries
    - Attempt to delete contractor
    - Verify warning "Contractor used in X entries"
    - Confirm deletion
    - Verify entries updated (contractor removed or marked deleted)

14. **bid item deletion with quantities workflow**
    - Create bid item
    - Add quantities in 2 entries
    - Attempt to delete bid item
    - Verify warning about existing quantities
    - Confirm deletion
    - Verify quantities handled (removed or orphaned)

15. **search and filter combined workflow**
    - Create 10 projects with varied names/dates
    - Apply search filter "Bridge"
    - Apply date range filter
    - Apply status filter "Active"
    - Verify combined filters work correctly

### Task 4.2: Data Integrity Tests

**File**: `integration_test/patrol/data_integrity_test.dart` (NEW FILE)

**New Tests to Add** (8 tests):

1. **verifies entry timestamps update on edit**
   - Create entry with initial timestamp
   - Wait 5 seconds
   - Edit entry
   - Save
   - Verify updated_at > created_at

2. **verifies project-location relationship integrity**
   - Create project
   - Add 2 locations
   - Delete project
   - Verify locations also deleted (cascade)

3. **verifies entry-photo relationship integrity**
   - Create entry with photo
   - Delete entry
   - Verify photo deleted
   - Verify file system cleaned up

4. **verifies contractor-equipment relationship integrity**
   - Create contractor with equipment
   - Delete contractor
   - Verify equipment also deleted

5. **verifies bid item-quantity relationship integrity**
   - Create bid item
   - Add quantity in entry
   - Delete bid item
   - Verify quantity handled appropriately

6. **verifies unique constraint enforcement**
   - Create project with MDOT number "123456"
   - Try creating another with same number
   - Verify constraint prevents duplicate

7. **verifies sync status consistency**
   - Create entry offline
   - Verify sync_status = 'pending'
   - Modify entry
   - Verify sync_status remains 'pending'

8. **verifies date consistency across related entities**
   - Create entry on Jan 15
   - Add quantities to entry
   - Verify quantities inherit entry date

### Task 4.3: Settings & Persistence Tests

**File**: `integration_test/patrol/settings_flow_test.dart`

**New Tests to Add** (10 tests):

1. **changes theme and verifies visual update**
   - Open settings
   - Tap Dark Mode
   - Verify background color changes
   - Navigate to projects
   - Verify theme persists across navigation

2. **toggles high contrast mode and verifies UI changes**
   - Open settings
   - Enable High Contrast
   - Verify text contrast increased
   - Verify button borders more visible

3. **saves inspector name and verifies in entry**
   - Set inspector name "Jane Smith"
   - Create entry
   - Verify inspector field shows "Jane Smith"

4. **saves inspector initials and verifies in report**
   - Set initials "JS"
   - Create entry and generate report
   - Verify initials appear in report header

5. **toggles auto-fetch weather and verifies behavior**
   - Disable auto-fetch
   - Create entry
   - Verify weather fields empty
   - Enable auto-fetch
   - Create entry
   - Verify weather fetched automatically

6. **toggles auto-sync WiFi only and verifies sync behavior**
   - Enable WiFi-only sync
   - Trigger sync on cellular (manual note)
   - Verify sync skipped with warning

7. **clears all data and verifies reset**
   - Create test data
   - Navigate to settings
   - Tap "Clear All Data"
   - Confirm
   - Verify all projects/entries deleted
   - Verify database tables empty

8. **exports data and verifies file created**
   - Create test data
   - Tap "Export Data"
   - Verify file picker opens
   - Select location
   - Verify .json or .zip file created

9. **imports data and verifies restoration**
   - Export data
   - Clear all data
   - Import exported file
   - Verify all projects/entries restored

10. **verifies settings persist after app restart**
    - Change multiple settings
    - Close app ($.native.pressHome)
    - Reopen app ($.native.openApp)
    - Navigate to settings
    - Verify all changes persisted

### Task 4.4: New Feature Test Files

**File**: `integration_test/patrol/locations_flow_test.dart` (NEW FILE)

**New Tests to Add** (15 tests):

1. **creates location for project**
2. **edits location name and address**
3. **deletes location and verifies cascade to entries**
4. **assigns location to entry**
5. **filters entries by location**
6. **verifies location required before entry creation**
7. **validates location name not empty**
8. **validates unique location names per project**
9. **searches locations by name**
10. **sorts locations alphabetically**
11. **verifies location appears in dropdown selectors**
12. **creates multiple locations for project**
13. **archives location and verifies unavailable for new entries**
14. **exports locations list**
15. **imports locations from file**

**File**: `integration_test/patrol/pdf_export_test.dart` (NEW FILE)

**New Tests to Add** (12 tests):

1. **exports single entry as PDF**
2. **exports date range as PDF**
3. **exports project summary as PDF**
4. **verifies PDF includes photos**
5. **verifies PDF includes weather data**
6. **verifies PDF includes contractor data**
7. **verifies PDF includes quantities**
8. **previews PDF before export**
9. **shares PDF via share dialog**
10. **saves PDF to device storage**
11. **verifies PDF template field mapping correct**
12. **handles PDF export errors gracefully**

---

## Execution Order

### Sprint 1: Critical Validation (Week 1)
1. Phase 1, Task 1.1: Project validation tests - `qa-testing-agent`
2. Phase 1, Task 1.2: Entry validation tests - `qa-testing-agent`
3. Phase 1, Task 1.3: Contractor validation tests - `qa-testing-agent`

### Sprint 2: CRUD Completeness (Week 2)
4. Phase 2, Task 2.1: Complete Project CRUD - `qa-testing-agent`
5. Phase 2, Task 2.2: Complete Entry CRUD - `qa-testing-agent`
6. Phase 2, Task 2.3: Complete Contractor CRUD - `qa-testing-agent`

### Sprint 3: Photos & Quantities (Week 3)
7. Phase 3, Task 3.1: Photo workflows - `qa-testing-agent`
8. Phase 3, Task 3.2: Photo-entry integration - `qa-testing-agent`
9. Phase 2, Task 2.4: Complete Quantities CRUD - `qa-testing-agent`
10. Phase 1, Task 1.4: Quantities validation - `qa-testing-agent`

### Sprint 4: E2E & Integrity (Week 4)
11. Phase 4, Task 4.1: End-to-end workflows - `qa-testing-agent`
12. Phase 4, Task 4.2: Data integrity tests - `qa-testing-agent`
13. Phase 4, Task 4.3: Settings persistence tests - `qa-testing-agent`
14. Phase 4, Task 4.4: New feature test files - `qa-testing-agent`

---

## Implementation Guidelines

### Test Quality Standards

1. **Independence**: Each test must be fully independent
   - Reset app state between tests if needed
   - Don't rely on data created in previous tests
   - Use unique identifiers (timestamps, UUIDs)

2. **Explicitness**: Tests should verify actual behavior, not just navigation
   - BAD: "opens dialog and presses back"
   - GOOD: "creates project, verifies in list, edits name, verifies update persists"

3. **Resilience**: Use condition-based waits, not hardcoded delays
   - Replace `Future.delayed(Duration(seconds: 3))` with `$.waitUntilVisible()`
   - Extract common wait patterns to test_config.dart helpers

4. **Coverage**: Each test should verify multiple assertions
   - Don't just test "dialog opens"
   - Test "dialog opens, fields validate, data saves, appears in list, edit works, delete works"

### Batch Management

**Current Constraint**: Max 5 tests per device run due to memory exhaustion

**Batch Strategy**:
- Group tests by feature to maintain logical organization
- Balance batch sizes (aim for 15-20 tests per file)
- Monitor test execution time (keep batches under 10 minutes)
- Use batched runner script: `run_patrol_batched.ps1`

### Widget Key Requirements

**Add Keys to UI Elements**:

Current keys identified in codebase (15 files use Key()). Need to add:

| Screen | Keys Needed |
|--------|-------------|
| Entry Wizard | `entry_location_field`, `entry_weather_dropdown`, `entry_temp_low`, `entry_temp_high`, `entry_activities_field`, `entry_save_draft_button`, `entry_submit_button` |
| Project List | `project_search_field`, `project_filter_button`, `project_archive_toggle` |
| Contractors | `contractor_name_field`, `contractor_type_dropdown`, `equipment_name_field`, `equipment_type_dropdown` |
| Quantities | `bid_item_number_field`, `bid_item_description_field`, `bid_item_quantity_field`, `bid_item_unit_dropdown` |
| Settings | `settings_inspector_name`, `settings_inspector_initials`, `settings_theme_dropdown`, `settings_auto_weather_toggle` |

### Error Handling Patterns

```dart
// Pattern 1: Permission handling
try {
  await $.native.grantPermissionWhenInUse();
} catch (e) {
  // Permission already granted or not needed
}

// Pattern 2: Native element interaction
try {
  await $.native.takePhoto();
} catch (e) {
  // Camera may not be available in emulator
  // Skip test with meaningful message
  markTestSkipped('Camera not available');
}

// Pattern 3: Wait with timeout
await $.waitUntilVisible(
  $(Key('expected_widget')),
  timeout: Duration(seconds: 10),
);
```

---

## Success Metrics

### Quantitative Targets

| Metric | Current | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Target |
|--------|---------|---------|---------|---------|---------|--------|
| Total Tests | 85 | 117 | 147 | 172 | 205 | 205 |
| Validation Coverage | 3% | 40% | 40% | 40% | 40% | 40% |
| CRUD Coverage | 18% | 18% | 80% | 80% | 80% | 80% |
| Photo Coverage | 0% | 0% | 0% | 75% | 75% | 75% |
| E2E Coverage | 6% | 6% | 6% | 6% | 50% | 50% |
| Pass Rate | 65% | 75% | 80% | 85% | 90% | 90%+ |

### Qualitative Goals

1. **Defect Prevention**: Tests catch validation errors before user sees them
2. **Regression Safety**: CRUD operations fully verified to prevent data loss
3. **User Confidence**: Photo workflows validated to ensure field usability
4. **Integration Assurance**: E2E tests verify features work together correctly

---

## Risk Mitigation

### Known Constraints

1. **Memory Limitations**: Tests must run in small batches (5 per device run)
   - Mitigation: Batched runner script handles automatic batching
   - Monitor: Watch for OOM crashes, reduce batch size if needed

2. **Test Orchestrator Exit Code Issue**: Returns 1 even when tests pass
   - Mitigation: Parse test summary output for actual pass/fail status
   - Defect logged: @.claude/memory/defects.md:336-343

3. **Airplane Mode Limitation**: Patrol cannot programmatically control network
   - Mitigation: Offline tests require manual network disable step
   - Alternative: Mock network responses at service layer

4. **Platform Differences**: Android vs iOS native interactions differ
   - Mitigation: Use platform-specific conditionals where needed
   - Test on both platforms before considering complete

### Rollback Plan

If test expansion causes instability:

1. **Immediate**: Disable new test batches via patrol.yaml exclusions
2. **Short-term**: Reduce batch sizes to isolate problematic tests
3. **Long-term**: Refactor tests to reduce memory usage (fewer widgets, more focused)

---

## Verification Checklist

After implementation, verify:

- [ ] All tests pass on Android emulator
- [ ] All tests pass on iOS simulator
- [ ] All tests pass on real devices (Android + iOS)
- [ ] Batch runner script completes without manual intervention
- [ ] Test execution time per batch < 10 minutes
- [ ] No memory exhaustion crashes during batched runs
- [ ] Widget keys added to all referenced UI elements
- [ ] Test documentation updated in README.md
- [ ] Defect log updated with any issues discovered
- [ ] Coverage report shows 40%+ validation, 80%+ CRUD, 75%+ photo

---

## Agent Assignment

**Primary Agent**: `qa-testing-agent`
**Supporting Agents**:
- `flutter-specialist-agent` - Add widget keys to UI screens
- `code-review-agent` - Review test quality and coverage
- `planning-agent` - Adjust plan based on findings

---

## References

- Current Test Suite: `integration_test/patrol/`
- Test Documentation: `integration_test/patrol/README.md`
- Batch Runner: `run_patrol_batched.ps1`
- Defect Log: `.claude/memory/defects.md`
- Platform Standards: `.claude/docs/2026-platform-standards-update.md`
- Coding Standards: `.claude/rules/coding-standards.md`

---

## Notes

1. **Incremental Approach**: Implement phase-by-phase to validate batch stability
2. **Test Quality Over Quantity**: 100 high-quality tests > 200 flaky tests
3. **Real-World Scenarios**: Focus on tests that mirror actual field inspector workflows
4. **Performance Monitoring**: Track test execution time and memory usage per batch
5. **Documentation**: Update README.md after each phase with new test descriptions

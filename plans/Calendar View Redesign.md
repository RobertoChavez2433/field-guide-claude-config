# Calendar Screen Layout Restructure Plan

## Overview
Transform the calendar screen from a horizontal split layout (200px entry sidebar + report preview) to a vertical stacked layout (calendar top, entry list middle, scrollable report bottom).

## Current State
**File:** `lib/features/entries/presentation/screens/home_screen.dart` (~1,900 lines)

```
Current Layout:
Column
├── Project Header
├── Calendar Section (TableCalendar)
├── Divider
└── Expanded
    └── Row (HORIZONTAL SPLIT - this is the "jumbled" part)
        ├── Left: Entry List (200px fixed, vertical scroll)
        └── Right: Report Preview (flexible width)
```

## Target State
```
New Layout:
Column
├── Project Header (unchanged)
├── Calendar Section (compact - week view default)
├── Divider
├── Date Header + Entry Count
├── Entry List (FULL WIDTH, horizontal scroll / grid)
├── Divider
└── Expanded Report Section (FULL WIDTH, scrollable)
    ├── All editable sections (weather, activities, safety, crew)
    └── "View Full Report" / "Edit Report" navigation button
```

---

## Phased Implementation

### PR 1: Widget Extraction (Foundation)
**Scope:** Extract embedded private widgets to separate files for reuse and reduced home_screen.dart complexity.

**Files to Create:**
- `lib/features/entries/presentation/widgets/modern_entry_card.dart`
- `lib/features/entries/presentation/widgets/animated_day_cell.dart`

**Files to Modify:**
- `lib/features/entries/presentation/widgets/widgets.dart` (add exports)
- `lib/features/entries/presentation/screens/home_screen.dart` (import extracted)

**Changes:**
1. Extract `_ModernEntryCard` (lines ~1782-1897) to public `ModernEntryCard`
   - Add `isCompact` parameter for horizontal list mode
   - Preserve `TestingKeys.entryCard(entryId)`
2. Extract `_AnimatedDayCell` (lines ~1676-1778) to public `AnimatedDayCell`
   - Preserve `TestingKeys.calendarDay(dateKey)`
3. Update barrel exports

**Testing:** `flutter analyze`, existing E2E tests pass

---

### PR 2: Entry List Full-Width Horizontal Layout
**Scope:** Transform entry list from vertical 200px sidebar to full-width horizontal section.

**File to Modify:**
- `lib/features/entries/presentation/screens/home_screen.dart`

**Changes:**
1. Modify `_buildSelectedDayContent` (line ~875):
   - Remove `Row` wrapper that creates horizontal split
   - Replace with `Column` containing entry section + report section

2. Create `_buildEntryListHorizontal`:
   ```dart
   SizedBox(
     height: 110, // Compact card height
     child: ListView.builder(
       scrollDirection: Axis.horizontal,
       itemCount: entries.length,
       itemBuilder: (context, index) => ModernEntryCard(isCompact: true, ...),
     ),
   )
   ```

3. Add responsive breakpoint:
   - Mobile (<600px): Horizontal scroll list
   - Tablet (>=600px): Grid layout (2-3 columns)

**Testing:** E2E tests, verify entry selection updates preview

---

### PR 3: Compact Calendar with Week Default
**Scope:** Default calendar to week view, preserve toggle capability.

**Files to Modify:**
- `lib/features/entries/presentation/providers/calendar_format_provider.dart`
- `lib/features/entries/presentation/screens/home_screen.dart`

**Changes:**
1. Change default format from `CalendarFormat.month` to `CalendarFormat.week`
2. Add height animation for smooth format transitions:
   ```dart
   AnimatedContainer(
     duration: Duration(milliseconds: 250),
     height: format == CalendarFormat.week ? 100 :
             format == CalendarFormat.twoWeeks ? 180 : 300,
     child: _buildCalendar(...),
   )
   ```
3. Preserve format toggle buttons (Month/2Weeks/Week)

**Testing:** Format persistence, date selection, navigation

---

### PR 4: Full-Width Scrollable Report Section
**Scope:** Transform report preview to full-width bottom section with complete scrollable content.

**File to Modify:**
- `lib/features/entries/presentation/screens/home_screen.dart`

**Changes:**
1. Modify `_buildReportPreview` for full-width layout:
   - Remove LayoutBuilder constraint check
   - Add section headers for visual organization
   - Ensure all sections are visible and scrollable

2. Structure:
   ```dart
   Expanded(
     child: Card(
       child: Column(
         children: [
           // Header with location + "Edit Report" button
           Row(
             children: [
               Expanded(child: Text(location.name)),
               ElevatedButton("Edit Report" → navigates to ReportScreen),
             ],
           ),
           Divider(),
           // Scrollable content
           Expanded(
             child: SingleChildScrollView(
               child: Column(
                 children: [
                   _buildWeatherSection(entry),      // Editable
                   _buildActivitiesSection(entry),   // Editable
                   _buildSafetySection(entry),       // Editable
                   _buildCrewSection(entry),         // Read-only summary
                 ],
               ),
             ),
           ),
         ],
       ),
     ),
   )
   ```

3. Preserve all inline editing:
   - Auto-save on focus loss
   - Text controllers and focus nodes
   - Section highlight on edit

**Testing:** Full E2E pass, inline editing, scroll with keyboard, auto-save

---

## Files Summary

| File | Change |
|------|--------|
| `widgets/modern_entry_card.dart` | CREATE - Extract from home_screen |
| `widgets/animated_day_cell.dart` | CREATE - Extract from home_screen |
| `widgets/widgets.dart` | MODIFY - Add exports |
| `screens/home_screen.dart` | MODIFY - Major restructure |
| `providers/calendar_format_provider.dart` | MODIFY - Default to week |

## TestingKeys to Preserve
- `TestingKeys.homeViewFullReportButton`
- `TestingKeys.homeCreateEntryButton`
- `TestingKeys.entryCard(entryId)`
- `TestingKeys.homeCalendarFormatMonth/TwoWeeks/Week`
- `TestingKeys.calendarDay(dateKey)`
- `TestingKeys.addEntryFab`
- All entry edit section keys

## Verification
1. Run `flutter analyze` after each PR
2. Run E2E test suite: `pwsh -File run_patrol_debug.ps1`
3. Manual test on phone and tablet sizes
4. Verify auto-save behavior preserved

---

## Confirmed Decisions
1. **Entry list (middle):** Horizontal scroll - cards side-by-side, swipe to see more
2. **Report section (bottom):** Full report preview with ALL sections visible, scrollable, AND editable inline (tap to edit like other screens)

---

## Detailed PR Breakdown

### PR 1: Widget Extraction (Foundation)

#### Phase 1.1: Extract ModernEntryCard
- Extract `_ModernEntryCard` class (~115 lines) to new file
- Make public, add `isCompact` parameter
- Update home_screen.dart imports

#### Phase 1.2: Extract AnimatedDayCell
- Extract `_AnimatedDayCell` class (~102 lines) to new file
- Make public, preserve animation logic
- Update home_screen.dart imports

#### Phase 1.3: Barrel Exports
- Add both widgets to `widgets.dart` barrel file
- Verify `flutter analyze` passes

**Deliverables:** 2 new widget files, reduced home_screen.dart by ~220 lines

---

### PR 2: Entry List Horizontal Layout

#### Phase 2.1: Create Horizontal Entry List Method
- New `_buildEntryListHorizontal()` method
- `SizedBox(height: 110)` with horizontal `ListView.builder`
- Use `ModernEntryCard(isCompact: true)`

#### Phase 2.2: Modify Selected Day Content Structure
- Change `_buildSelectedDayContent` from Row to Column layout
- Entry list section (fixed height) above report section (expanded)

#### Phase 2.3: Update ModernEntryCard for Compact Mode
- Add `isCompact` layout variant
- Horizontal card layout: icon + location + status badge
- Reduced height and padding

**Deliverables:** Entry list renders horizontally, selection still works

---

### PR 3: Compact Calendar

#### Phase 3.1: Change Default Format
- Update `CalendarFormatProvider` default to `CalendarFormat.week`
- Verify persistence still works for user overrides

#### Phase 3.2: Add Height Animation
- Wrap calendar in `AnimatedContainer`
- Smooth transitions between week/2weeks/month views

**Deliverables:** Calendar defaults compact, can still expand

---

### PR 4: Full-Width Editable Report Section

#### Phase 4.1: Restructure Report Preview Layout
- Remove LayoutBuilder constraint checks
- Full-width card with scrollable content
- Section headers for visual organization

#### Phase 4.2: Preserve Inline Editing (CRITICAL)
- Keep all text controllers and focus nodes:
  - `_tempLowController`, `_tempHighController`
  - `_activitiesController`
  - `_siteSafetyController`, `_sescController`, `_trafficController`, `_visitorsController`
- Keep focus listeners for auto-save on blur
- Keep `_editingSection` state for highlighting active field
- Keep `_startEditing()` and `_saveIfEditing()` methods

#### Phase 4.3: Editable Sections
Ensure tap-to-edit behavior for all sections:
- **Weather:** Temperature fields editable on tap
- **Activities:** Multi-line text field, editable on tap
- **Safety:** Site safety, SESC, traffic control, visitors - all editable on tap
- **Crew:** Read-only summary (editing happens in EntryWizard)

#### Phase 4.4: Navigation Button
- Prominent "Edit Report" button at bottom
- Navigates to full `ReportScreen` for complete editing experience
- Preserve `TestingKeys.homeViewFullReportButton`

**Deliverables:** Full report visible, all fields editable inline, scrollable

---

## E2E Testing Strategy

### New TestingKeys Required

Add these to `lib/shared/testing_keys.dart`:

```dart
// ============================================
// Calendar Screen - New Layout Keys
// ============================================

/// Horizontal entry list container (for scroll testing)
static const homeEntryListHorizontal = Key('home_entry_list_horizontal');

/// Report preview container (for visibility/scroll testing)
static const homeReportPreviewSection = Key('home_report_preview_section');

/// Report preview scroll view (for scroll testing)
static const homeReportPreviewScrollView = Key('home_report_preview_scroll_view');

/// Edit Report button in preview (navigates to ReportScreen)
static const homeEditReportButton = Key('home_edit_report_button');

// Home Screen - Inline Edit Section Keys
/// Weather section in home screen preview (tap to edit)
static const homeWeatherSection = Key('home_weather_section');

/// Activities section in home screen preview (tap to edit)
static const homeActivitiesSection = Key('home_activities_section');

/// Safety section in home screen preview (tap to edit)
static const homeSafetySection = Key('home_safety_section');

/// Crew section in home screen preview (read-only)
static const homeCrewSection = Key('home_crew_section');

// Home Screen - Inline Edit Fields
static const homeTempLowField = Key('home_temp_low_field');
static const homeTempHighField = Key('home_temp_high_field');
static const homeActivitiesField = Key('home_activities_field');
static const homeSiteSafetyField = Key('home_site_safety_field');
static const homeSescField = Key('home_sesc_field');
static const homeTrafficField = Key('home_traffic_field');
static const homeVisitorsField = Key('home_visitors_field');
```

### Existing Keys to Preserve (Verified)
- `TestingKeys.addEntryFab` - FAB for new entry
- `TestingKeys.homeViewFullReportButton` → rename to `homeEditReportButton`
- `TestingKeys.homeCreateEntryButton` - Empty state button
- `TestingKeys.homeCalendarFormatMonth/TwoWeeks/Week` - Format toggles
- `TestingKeys.calendarDay(dateKey)` - Dynamic calendar day keys
- `TestingKeys.entryCard(entryId)` - Dynamic entry card keys
- `TestingKeys.homeJumpToLatestButton` - Jump to latest

### E2E Test Scenarios

#### PR 1 Tests (Widget Extraction)
- **Existing tests should pass unchanged** - No behavioral changes
- Verify `entryCard(entryId)` keys still work after extraction

#### PR 2 Tests (Horizontal Entry List)
```dart
// Test: Entry list horizontal scroll
patrolTest('can scroll through entry list horizontally', ($) async {
  await h.launchAppAndWait();
  await h.signInIfNeeded();
  await h.selectProject('Test Project');
  await h.navigateToCalendar();

  // Select a day with multiple entries
  await $(TestingKeys.calendarDay('2026-01-25')).tap();

  // Verify horizontal list exists
  await h.waitForVisible(TestingKeys.homeEntryListHorizontal);

  // Scroll to see more entries
  await $(TestingKeys.homeEntryListHorizontal).scrollTo(
    $(TestingKeys.entryCard('entry_id_3')),
    scrollDirection: AxisDirection.right,
  );

  // Tap an entry
  await $(TestingKeys.entryCard('entry_id_3')).tap();

  // Verify report preview updates
  await h.waitForVisible(TestingKeys.homeReportPreviewSection);
});
```

#### PR 3 Tests (Compact Calendar)
```dart
// Test: Calendar defaults to week view
patrolTest('calendar defaults to week view', ($) async {
  await h.launchAppAndWait();
  await h.signInIfNeeded();
  await h.selectProject('Test Project');
  await h.navigateToCalendar();

  // Week toggle should be active by default
  // (verify by checking calendar height or active button state)
  await h.waitForVisible(TestingKeys.homeCalendarFormatWeek);

  // Can expand to month
  await $(TestingKeys.homeCalendarFormatMonth).tap();
  await h.pumpAndWait(milliseconds: 300); // Animation

  // Can collapse back to week
  await $(TestingKeys.homeCalendarFormatWeek).tap();
});
```

#### PR 4 Tests (Inline Editing)
```dart
// Test: Can edit activities inline in home screen
patrolTest('can edit activities inline', ($) async {
  await h.launchAppAndWait();
  await h.signInIfNeeded();
  await h.selectProject('Test Project');
  await h.navigateToCalendar();
  await h.selectEntryOnCalendar('2026-01-25', 0);

  // Scroll to activities section if needed
  await $(TestingKeys.homeActivitiesSection).scrollTo();

  // Tap to edit
  await $(TestingKeys.homeActivitiesSection).tap();

  // Enter text
  await $(TestingKeys.homeActivitiesField).enterText('Updated activities');

  // Tap elsewhere to trigger auto-save
  await $(TestingKeys.homeWeatherSection).tap();

  // Verify change persisted (navigate away and back)
  await h.navigateToDashboard();
  await h.navigateToCalendar();
  await h.selectEntryOnCalendar('2026-01-25', 0);

  // Should see updated text
  await h.waitForText('Updated activities');
});

// Test: Can scroll to see full report
patrolTest('can scroll to see full report', ($) async {
  await h.launchAppAndWait();
  await h.signInIfNeeded();
  await h.selectProject('Test Project');
  await h.navigateToCalendar();
  await h.selectEntryOnCalendar('2026-01-25', 0);

  // Scroll down in report preview
  await $(TestingKeys.homeReportPreviewScrollView).scrollTo(
    $(TestingKeys.homeCrewSection),
    scrollDirection: AxisDirection.down,
  );

  // Crew section should be visible
  await h.assertVisible(TestingKeys.homeCrewSection, 'Crew section');

  // Edit Report button should be visible
  await h.waitForVisible(TestingKeys.homeEditReportButton);
});

// Test: Edit Report button navigates to ReportScreen
patrolTest('edit report button navigates to report screen', ($) async {
  await h.launchAppAndWait();
  await h.signInIfNeeded();
  await h.selectProject('Test Project');
  await h.navigateToCalendar();
  await h.selectEntryOnCalendar('2026-01-25', 0);

  await $(TestingKeys.homeEditReportButton).scrollTo();
  await $(TestingKeys.homeEditReportButton).tap();

  // Should be on ReportScreen
  await h.waitForVisible(TestingKeys.reportScreenTitle);
});
```

### Test Helper Updates

Add to `PatrolTestHelpers`:

```dart
/// Select an entry on the calendar by date and index
Future<void> selectEntryOnCalendar(String dateKey, int entryIndex) async {
  await $(TestingKeys.calendarDay(dateKey)).tap();
  await pumpAndWait(milliseconds: 300);

  // If multiple entries, scroll to and tap the specific one
  // (implementation depends on entry ID format)
}

/// Scroll within the report preview section
Future<void> scrollReportPreviewTo(Key targetKey) async {
  await $(TestingKeys.homeReportPreviewScrollView).scrollTo(
    $(targetKey),
    scrollDirection: AxisDirection.down,
  );
}
```

### Regression Test Checklist

Each PR must pass:
1. `auth_flow_test.dart` - Auth still works
2. `app_smoke_test.dart` - App loads, navigation works
3. `entry_lifecycle_test.dart` - Entry CRUD operations
4. `entry_management_test.dart` - Entry list operations
5. `project_setup_flow_test.dart` - Project context

Run with: `pwsh -File run_patrol_debug.ps1`

### Test Files to Update

| File | Changes Needed |
|------|----------------|
| `integration_test/patrol/helpers/patrol_test_helpers.dart` | Add `selectEntryOnCalendar()`, `scrollReportPreviewTo()` |
| `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart` | Update entry selection flow for horizontal list |
| `integration_test/patrol/e2e_tests/entry_management_test.dart` | Update entry list interactions |

### Known Test Risks

1. **Horizontal scroll detection**: Patrol's `scrollTo()` may need `scrollDirection: AxisDirection.right` for horizontal lists
2. **Entry selection timing**: May need additional `pumpAndWait()` after entry tap for preview to load
3. **Keyboard interactions**: Inline editing may require `dismissKeyboard()` after text entry - use `scrollTo()` instead to avoid closing dialogs
4. **Report preview height**: Ensure report section has enough height for scroll testing on smaller screens

### Defects to Avoid (from defects.md)

- **Never use `pumpAndSettle()` or `pump(Duration)`** - use condition-based waits
- **Always `scrollTo()` before `tap()`** for below-fold elements
- **Check `.exists` doesn't mean hit-testable** - use `safeTap(..., scroll: true)`
- **Keyboard covers text field after tap** - call `scrollTo()` again before `enterText()`

# Manual Testing Checklist
## Construction Inspector App

**Version**: 1.0
**Last Updated**: 2026-01-20
**Estimated Time**: 45-60 minutes (full suite)

---

## Quick Reference

| Suite | Priority | Time | Sections |
|-------|----------|------|----------|
| 1. App Launch | Critical | 2 min | Startup, crash-free |
| 2. Authentication | Critical | 5 min | Login, register, logout |
| 3. Projects | High | 5 min | CRUD operations |
| 4. Entries | High | 10 min | Create, edit, auto-save |
| 5. Contractors | Medium | 5 min | Personnel, equipment |
| 6. Quantities | Medium | 5 min | Bid items, entry quantities |
| 7. Photos | High | 5 min | Capture, gallery, captions |
| 8. PDF | High | 5 min | Generate, export |
| 9. Sync | Critical | 5 min | Offline/online |
| 10. Settings | Medium | 3 min | Themes, preferences |
| 11. Navigation | Medium | 3 min | All routes work |
| 12. Edge Cases | Low | 5 min | Error handling |

---

## Pre-Test Setup

### Environment Check
- [ ] Device/emulator is running
- [ ] App is freshly installed OR database cleared
- [ ] Network connectivity available (for sync tests)
- [ ] Camera available (for photo tests)

### Test Account
- **Email**: test@example.com (or your test account)
- **Password**: (your test password)

---

## Suite 1: App Launch & Startup (Critical)

### 1.1 Cold Start
- [ ] App launches without crash
- [ ] Splash screen appears (if implemented)
- [ ] Login screen displays correctly
- [ ] No console errors on startup

### 1.2 Warm Start
- [ ] Background app and return - state preserved
- [ ] Rotate device (if mobile) - no crash
- [ ] Memory pressure recovery (optional)

### 1.3 First-Time User
- [ ] Fresh install shows login/register options
- [ ] No lingering data from previous installs

**Pass Criteria**: App starts cleanly, no crashes, login screen visible

---

## Suite 2: Authentication (Critical)

### 2.1 Login Flow
- [ ] Enter valid email/password
- [ ] Tap "Login" button
- [ ] Loading indicator appears
- [ ] Successful login redirects to Dashboard/Projects
- [ ] User session persists after app restart

### 2.2 Login Error Handling
- [ ] Invalid email format shows error
- [ ] Wrong password shows "Invalid credentials" message
- [ ] Empty fields show validation errors
- [ ] Network error shows appropriate message

### 2.3 Registration Flow
- [ ] Tap "Create Account" / "Register"
- [ ] Fill in email, password, confirm password
- [ ] Password mismatch shows error
- [ ] Successful registration creates account
- [ ] Email verification prompt (if enabled)

### 2.4 Forgot Password
- [ ] Tap "Forgot Password" link
- [ ] Enter email address
- [ ] Submit shows success message
- [ ] Check email for reset link (if testing full flow)

### 2.5 Logout
- [ ] Navigate to Settings
- [ ] Tap "Logout" button
- [ ] Confirmation dialog appears (if implemented)
- [ ] Returns to login screen
- [ ] Session is cleared (restart app to verify)

**Pass Criteria**: All auth flows work, errors handled gracefully

---

## Suite 3: Project Management (High)

### 3.1 Project List
- [ ] Project list screen loads
- [ ] Existing projects display correctly
- [ ] Project cards show: name, number, status
- [ ] Empty state shows if no projects

### 3.2 Create Project
- [ ] Tap "+" or "New Project" button
- [ ] Project form appears
- [ ] Fill required fields:
  - [ ] Project Name
  - [ ] Project Number
  - [ ] Start Date
  - [ ] (Optional fields as needed)
- [ ] Save button creates project
- [ ] New project appears in list
- [ ] Toast/snackbar confirms creation

### 3.3 Edit Project
- [ ] Tap existing project to open
- [ ] Tap edit button/icon
- [ ] Modify project details
- [ ] Save changes
- [ ] Changes persist after navigating away

### 3.4 Delete Project
- [ ] Open project edit/detail screen
- [ ] Tap delete button
- [ ] Confirmation dialog appears
- [ ] Confirm deletion
- [ ] Project removed from list
- [ ] Associated entries/data handled appropriately

### 3.5 Project Selection
- [ ] Tap project to select as active
- [ ] Dashboard shows selected project data
- [ ] Project context persists across screens

**Pass Criteria**: Full CRUD operations work, data persists

---

## Suite 4: Daily Entries (High)

### 4.1 Entry List View
- [ ] Navigate to Calendar/Home screen
- [ ] Calendar displays current month
- [ ] Entries show on correct dates
- [ ] Tap date to see entry preview

### 4.2 Create New Entry
- [ ] Tap "+" or select date without entry
- [ ] Entry wizard/form opens
- [ ] Date is pre-filled correctly
- [ ] Weather section available

### 4.3 Entry Wizard Sections
Test each section of the entry wizard:

#### Weather Section
- [ ] Auto-fetch weather button works
- [ ] Manual weather entry possible
- [ ] Temperature, conditions, wind display
- [ ] Weather data saves correctly

#### Work Description
- [ ] Text field accepts input
- [ ] Text persists when navigating sections
- [ ] Long text handled properly

#### Contractors Section
- [ ] Add contractor button works
- [ ] Select from existing contractors
- [ ] Add personnel count
- [ ] Add equipment
- [ ] Multiple contractors can be added
- [ ] Remove contractor works

#### Quantities Section
- [ ] Add quantity button works
- [ ] Select bid item from list
- [ ] Enter quantity value
- [ ] Location selection works
- [ ] Multiple quantities can be added

#### Photos Section
- [ ] Photo section accessible
- [ ] (Detailed in Suite 7)

### 4.4 Auto-Save
- [ ] Make changes to entry
- [ ] Navigate away without explicit save
- [ ] Return to entry - changes preserved
- [ ] No data loss on unexpected exit

### 4.5 Edit Existing Entry
- [ ] Open entry from calendar
- [ ] Report screen shows entry details
- [ ] Inline editing works (tap to edit)
- [ ] Changes save correctly

### 4.6 Entry Validation
- [ ] Required fields enforced
- [ ] Invalid data shows errors
- [ ] Cannot save incomplete required data

**Pass Criteria**: Entries create, edit, auto-save, all sections work

---

## Suite 5: Contractors & Personnel (Medium)

### 5.1 Contractor List
- [ ] View all contractors
- [ ] Search/filter works (if implemented)
- [ ] Contractor details visible

### 5.2 Add Contractor
- [ ] Create new contractor
- [ ] Fill name, type, contact info
- [ ] Save contractor
- [ ] Appears in contractor list

### 5.3 Equipment Management
- [ ] View equipment for contractor
- [ ] Add new equipment
- [ ] Equipment type selection
- [ ] Equipment appears in entry wizard

### 5.4 Personnel Types
- [ ] Navigate to Settings > Personnel Types
- [ ] View existing types (Foreman, Laborer, etc.)
- [ ] Add custom personnel type
- [ ] Custom type available in entry wizard

### 5.5 Entry Personnel
- [ ] Add personnel to entry
- [ ] Select personnel type
- [ ] Enter count/hours
- [ ] Personnel data saves with entry

**Pass Criteria**: Contractors, equipment, personnel CRUD works

---

## Suite 6: Quantities & Bid Items (Medium)

### 6.1 Bid Items List
- [ ] Navigate to Quantities screen
- [ ] All bid items display
- [ ] Item number, description, unit visible
- [ ] Total quantities shown

### 6.2 Add Bid Item
- [ ] Create new bid item (if allowed)
- [ ] Enter item number, description, unit, unit price
- [ ] Save bid item
- [ ] Item appears in list

### 6.3 Entry Quantities
- [ ] In entry wizard, add quantity
- [ ] Select bid item from picker
- [ ] Enter quantity value
- [ ] Select location (if required)
- [ ] Quantity saves with entry

### 6.4 Quantity Calculations
- [ ] Total installed quantities calculate correctly
- [ ] Budget impact displays (if implemented)
- [ ] Running totals accurate

### 6.5 Quantity Editing
- [ ] Edit existing quantity on entry
- [ ] Change value, location
- [ ] Delete quantity from entry
- [ ] Changes persist

**Pass Criteria**: Bid items display, quantities add/edit/delete

---

## Suite 7: Photos (High)

### 7.1 Photo Capture
- [ ] Open entry, go to Photos section
- [ ] Tap camera button
- [ ] Camera opens (grant permission if needed)
- [ ] Take photo
- [ ] Photo appears in entry

### 7.2 Gallery Selection
- [ ] Tap gallery button
- [ ] Photo picker opens
- [ ] Select photo(s)
- [ ] Selected photos appear in entry

### 7.3 Photo Details
- [ ] Tap photo to view full size
- [ ] Pinch to zoom works
- [ ] Photo metadata visible (date, GPS if captured)

### 7.4 Photo Captions
- [ ] Add caption to photo
- [ ] Caption saves correctly
- [ ] Caption displays in photo list
- [ ] Edit caption works

### 7.5 Photo Deletion
- [ ] Delete photo from entry
- [ ] Confirmation dialog appears
- [ ] Photo removed from entry
- [ ] Storage cleaned up

### 7.6 Photo Performance
- [ ] Adding 5+ photos doesn't lag
- [ ] Thumbnails load quickly
- [ ] Full-size images load on demand

**Pass Criteria**: Capture, select, caption, delete all work

---

## Suite 8: PDF Generation (High)

### 8.1 Generate PDF
- [ ] Open entry report screen
- [ ] Tap "Export PDF" or similar
- [ ] Loading indicator appears
- [ ] PDF generates without error

### 8.2 PDF Preview
- [ ] PDF preview displays (if implemented)
- [ ] All sections render correctly:
  - [ ] Header with project info
  - [ ] Date and weather
  - [ ] Work description
  - [ ] Contractors/personnel table
  - [ ] Quantities table
  - [ ] Photos (if included)

### 8.3 PDF Export
- [ ] Share/save PDF option works
- [ ] PDF saves to device/folder
- [ ] File opens in PDF viewer
- [ ] PDF is readable and formatted

### 8.4 PDF with Photos
- [ ] Generate PDF with embedded photos
- [ ] Photos appear in correct section
- [ ] Captions display with photos
- [ ] PDF file size reasonable

### 8.5 Batch PDF Export (if implemented)
- [ ] Select multiple entries
- [ ] Export to folder
- [ ] All PDFs generate correctly
- [ ] Files named appropriately

**Pass Criteria**: PDF generates, contains correct data, exports successfully

---

## Suite 9: Sync & Offline (Critical)

### 9.1 Online Sync
- [ ] Ensure network connected
- [ ] Navigate to Settings or sync indicator
- [ ] Trigger manual sync
- [ ] Sync completes successfully
- [ ] Last sync time updates

### 9.2 Sync Status Indicators
- [ ] Unsynced items show indicator (dot, icon)
- [ ] After sync, indicators clear
- [ ] Sync progress visible during sync

### 9.3 Offline Mode
- [ ] Disable network (airplane mode)
- [ ] Create new entry
- [ ] Entry saves locally
- [ ] Entry marked as "pending sync"

### 9.4 Offline to Online Transition
- [ ] Re-enable network
- [ ] Trigger sync (auto or manual)
- [ ] Offline entries upload
- [ ] Sync status updates to "synced"

### 9.5 Conflict Handling
- [ ] (If testable) Create conflict scenario
- [ ] Last-write-wins applied correctly
- [ ] No data corruption

### 9.6 Sync Error Recovery
- [ ] Simulate sync failure (if possible)
- [ ] Error message displayed
- [ ] Retry mechanism works
- [ ] No data loss on failure

**Pass Criteria**: Online sync works, offline entries queue and sync

---

## Suite 10: Settings & Themes (Medium)

### 10.1 Settings Screen
- [ ] Navigate to Settings tab
- [ ] All settings options visible
- [ ] Settings values reflect current state

### 10.2 Theme Switching
- [ ] Change to **Dark Mode**
  - [ ] UI updates immediately
  - [ ] All screens use dark colors
  - [ ] Text is readable
  - [ ] No white flash on navigation
- [ ] Change to **Light Mode**
  - [ ] UI updates immediately
  - [ ] All screens use light colors
- [ ] Change to **High Contrast** (if available)
  - [ ] Increased contrast visible
  - [ ] Accessibility improved

### 10.3 Theme Persistence
- [ ] Set theme preference
- [ ] Close and restart app
- [ ] Theme preference preserved

### 10.4 Other Settings
- [ ] Test any other configurable settings
- [ ] Settings save correctly
- [ ] Settings apply as expected

### 10.5 About/Version Info
- [ ] App version displays correctly
- [ ] Build number visible (if shown)

**Pass Criteria**: Theme switching works and persists, settings save

---

## Suite 11: Navigation (Medium)

### 11.1 Bottom Navigation
- [ ] Dashboard tab loads Dashboard
- [ ] Calendar tab loads Home/Calendar
- [ ] Projects tab loads Project List
- [ ] Settings tab loads Settings

### 11.2 Deep Navigation
- [ ] Navigate: Projects > Project > Entry > Report
- [ ] Back button returns correctly at each level
- [ ] No navigation stack issues

### 11.3 Route Parameters
- [ ] Entry routes include correct projectId, date
- [ ] Report routes include correct entryId
- [ ] Invalid routes show error or redirect

### 11.4 App Bar Actions
- [ ] Back buttons work correctly
- [ ] Action buttons (edit, delete, etc.) work
- [ ] Menu items accessible

### 11.5 Keyboard Navigation (Desktop)
- [ ] Tab through form fields
- [ ] Enter submits forms
- [ ] Escape closes dialogs

**Pass Criteria**: All navigation paths work, no dead ends

---

## Suite 12: Edge Cases & Error Handling (Low)

### 12.1 Empty States
- [ ] No projects: Empty state message
- [ ] No entries: Calendar shows no entries
- [ ] No photos: Photo section empty state
- [ ] No contractors: Add contractor prompt

### 12.2 Long Content
- [ ] Very long project name displays (truncate/wrap)
- [ ] Very long work description handles properly
- [ ] Long contractor names don't break UI

### 12.3 Special Characters
- [ ] Project name with special chars: `Test & "Project" <1>`
- [ ] Work description with emojis (if supported)
- [ ] SQL injection attempt: `'; DROP TABLE--`

### 12.4 Boundary Values
- [ ] Zero quantities accepted (if valid)
- [ ] Negative values rejected (if invalid)
- [ ] Very large numbers handled

### 12.5 Network Errors
- [ ] Slow network shows loading
- [ ] Timeout shows retry option
- [ ] No network shows offline mode

### 12.6 Permission Denied
- [ ] Camera permission denied - graceful fallback
- [ ] Location permission denied - works without GPS
- [ ] Storage permission denied - error message

**Pass Criteria**: App handles edge cases without crashing

---

## Test Results Template

### Test Run Summary
| Date | Tester | Device | OS Version | App Version |
|------|--------|--------|------------|-------------|
| YYYY-MM-DD | Name | Device | Version | v1.0.0 |

### Suite Results
| Suite | Pass | Fail | Skip | Notes |
|-------|------|------|------|-------|
| 1. App Launch | /4 | | | |
| 2. Authentication | /16 | | | |
| 3. Projects | /17 | | | |
| 4. Entries | /21 | | | |
| 5. Contractors | /14 | | | |
| 6. Quantities | /14 | | | |
| 7. Photos | /15 | | | |
| 8. PDF | /13 | | | |
| 9. Sync | /15 | | | |
| 10. Settings | /11 | | | |
| 11. Navigation | /12 | | | |
| 12. Edge Cases | /16 | | | |
| **TOTAL** | /168 | | | |

### Bugs Found
| ID | Suite | Severity | Description | Steps to Reproduce |
|----|-------|----------|-------------|-------------------|
| 1 | | | | |
| 2 | | | | |

### Notes
-
-

---

## Quick Smoke Test (5 minutes)

For rapid verification after changes:

1. [ ] App launches
2. [ ] Login works
3. [ ] Create entry (any data)
4. [ ] Add photo
5. [ ] Generate PDF
6. [ ] Sync completes
7. [ ] Switch theme
8. [ ] Logout

**If all pass**: Basic functionality intact

---

## Regression Test Triggers

Run **full suite** after:
- Major feature additions
- Database schema changes
- Provider/state management changes
- Navigation/routing changes
- Sync service modifications

Run **smoke test** after:
- UI tweaks
- Bug fixes
- Documentation changes
- Minor refactoring

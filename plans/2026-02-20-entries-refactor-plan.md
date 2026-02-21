# Entries Feature Refactor Plan

**Date**: 2026-02-20
**Catalog Source**: `.claude/code-reviews/2026-02-20-master-refactor-catalog.md`
**Scope**: Entries feature (8,466 lines across 4 screens) + testability for dart-mcp automation

---

## Context

The entries feature is where inspectors spend the bulk of their time. It has 4 god-class screens (ReportScreen 2,761 lines, EntryWizard 2,610 lines, HomeScreen 2,382 lines, EntriesListScreen 713 lines) with massive duplication: 3 screens maintain identical TextEditingControllers, contractor state, and save logic. This makes bugs easy to introduce (fix one screen, forget the other two) and new features require touching 3 files.

**Key decisions (from brainstorming):**
- **Goal**: Comprehensive (dedup + extensibility + reliability + testability)
- **Screen consolidation**: Merge EntryWizard + ReportScreen into a single `EntryEditorScreen`
- **Create UX**: Soft progressive (all sections visible, auto-scroll to next empty section)
- **Controller pattern**: ChangeNotifier (consistent with existing Provider architecture)
- **Testing**: Full-app dart-mcp testing + widget test harnesses on demand per component
- **Sequencing**: Bottom-up (foundations first). App breakage acceptable during refactor.

**Target outcome**: 4 screens (8,466 lines) become 3 screens (~4,800 lines) with shared controllers and independently testable components.

---

## Phase 0: DI Fixes (Trivial, ~30 min)

Fix direct service instantiation before extracting controllers, so controllers receive dependencies cleanly.

| Catalog ID | What | File | Change |
|------------|------|------|--------|
| E-08 | Fix `DatabaseService()` in 3 screens | report_screen:113, home_screen:104, wizard:123 | Inject via Provider from `main.dart` |
| E-16 | Fix `PdfService()` | report_screen:54 | Register in MultiProvider, inject via `context.read` |
| E-18 | Fix `WeatherService()` + `ImageService()` | wizard:104-105 | Register in MultiProvider, inject via `context.read` |

**Files to modify**: `lib/main.dart` (add Provider registrations), 3 screen files (replace `Service()` with `context.read<Service>()`)

---

## Phase 1: Core Controller Extractions (E-01, E-02, E-03, E-04)

Extract the 4 shared controllers that eliminate duplication across screens. Each becomes a ChangeNotifier that screens consume via Provider.

### 1A: EntryEditingController (E-01)

**New file**: `lib/features/entries/presentation/controllers/entry_editing_controller.dart`

**Owns**:
- 7 TextEditingControllers: tempLow, tempHigh, activities, siteSafety, sesc, traffic, visitors
- 7 FocusNodes (matching)
- `editingSection` state (String?) for inline edit mode
- `isDirty` tracking for unsaved changes
- `populateFrom(DailyEntry)` — fills all controllers from entry
- `buildEntry(DailyEntry base)` — returns updated DailyEntry from controller values
- `save(DailyEntryRepository repo, DailyEntry base)` — builds + saves + resets dirty flag
- `dispose()` — disposes all controllers + focus nodes

**Constructor**: `EntryEditingController()` — no dependencies needed (stateless form manager)

**Consumers**: HomeScreen, EntryEditorScreen (new)

**Lines saved**: ~250 (7 controllers + 7 focus nodes + populate + save + dispose duplicated 3x)

### 1B: ContractorEditingController (E-02)

**New file**: `lib/features/entries/presentation/controllers/contractor_editing_controller.dart`

**Owns**:
- `personnel` (List<EntryPersonnel>)
- `entryEquipment` (List<EntryEquipment>)
- `contractorsById` (Map<String, Contractor>)
- `equipmentById` (Map<String, Equipment>)
- `personnelTypes` (List<PersonnelType>)
- `personnelCounts` / `editingPersonnelCounts` (Map<String, Map<String, int>>)
- `allProjectEquipment` (List<Equipment>)
- `editingContractorId` (String?)
- `editingEquipmentIds` (Set<String>)
- `saveIfEditingContractor()` — the 90-line save method currently duplicated 3x
- `startEditingContractor(String contractorId)` / `cancelEditing()`
- `loadForEntry(String entryId, String projectId, datasources)` — loads all contractor/personnel/equipment data
- `dispose()`

**Dependencies (injected via constructor)**:
- `EntryPersonnelLocalDatasource`
- `EntryEquipmentLocalDatasource`
- `EntryContractorsLocalDatasource`
- `PersonnelTypeRepository`
- `EquipmentRepository`

**Consumers**: HomeScreen, EntryEditorScreen

**Lines saved**: ~500 (12 state fields + 90-line save + load/init duplicated 3x)

### 1C: PhotoAttachmentManager (E-03)

**New file**: `lib/features/entries/presentation/controllers/photo_attachment_manager.dart`

**Owns**:
- `photos` (List<Photo>)
- `capturePhoto(PhotoService, String entryId)` — camera capture + save
- `pickFromGallery(PhotoService, String entryId)` — gallery picker + save
- `renamePhoto(String photoId, String newName)` — rename with dialog
- `deletePhoto(String photoId)` — delete with confirmation
- `loadPhotos(String entryId)` — load photos for entry

**Dependencies**: `PhotoService` (passed to methods, not constructor — keeps it lightweight)

**Consumers**: EntryEditorScreen only (HomeScreen doesn't handle photos)

**Lines saved**: ~200

### 1D: FormAttachmentManager (E-04)

**New file**: `lib/features/entries/presentation/controllers/form_attachment_manager.dart`

**Owns**:
- `forms` (List<FormResponse>)
- `selectForm()` — show form selection dialog
- `startForm(String formTemplateId, String entryId)` — create new form response
- `openForm(String formResponseId)` — navigate to form fill
- `deleteForm(String formResponseId)` — delete form response
- `loadForms(String entryId)` — load form responses for entry

**Consumers**: EntryEditorScreen only

**Lines saved**: ~100

### Phase 1 Verification
- Each controller gets a widget test harness: `test_harnesses/entry_editing_harness.dart`, `test_harnesses/contractor_editing_harness.dart`
- Drive via dart-mcp: populate fields, edit, save, verify state
- Run `flutter analyze` after each extraction

---

## Phase 2: Small Widget Extractions (E-10, E-11, E-12, E-13)

Extract 4 small shared widgets. These are quick wins that simplify the later screen merge.

| ID | Widget | New File | Lines Saved |
|----|--------|----------|-------------|
| E-12 | `StatusBadge` — status color/text/icon (duplicated 4x) | `lib/features/entries/presentation/widgets/status_badge.dart` | ~80 |
| E-10 | `ContextualFeedbackOverlay` — animated overlay (duplicated 2x) | `lib/shared/widgets/contextual_feedback_overlay.dart` | ~75 |
| E-13 | `SimpleInfoRow` — label+value row (duplicated 2x) | `lib/features/entries/presentation/widgets/simple_info_row.dart` | ~22 |
| E-11 | `DeleteEntryDialog` — **already extracted** (97 lines in widgets/) | N/A | Already done |

**Note**: E-11 already exists at `lib/features/entries/presentation/widgets/delete_entry_dialog.dart`. Verify home_screen and entries_list_screen are both using it. If not, wire them up.

---

## Phase 3: EntryEditorScreen — The Big Merge (E-05, E-06, E-14, E-17)

Replace both `entry_wizard_screen.dart` (2,610 lines) and `report_screen.dart` (2,761 lines) with a single `EntryEditorScreen`.

### 3A: Create EntryEditorScreen

**New file**: `lib/features/entries/presentation/screens/entry_editor_screen.dart`

**Constructor params**:
```
EntryEditorScreen({
  required String projectId,
  String? entryId,        // null = create mode, non-null = edit mode
  String? locationId,     // pre-selected location for create mode
  DateTime? date,         // pre-selected date for create mode
})
```

**State it owns** (minimal — most state is in controllers):
- `_isCreateMode` (derived from entryId == null)
- `_isLoading` / `_entry` (loaded DailyEntry)
- `_scrollController` (for soft-progressive auto-scroll)
- `_sectionKeys` (GlobalKey per section for scroll targeting)

**Provided via ChangeNotifierProvider (screen-scoped)**:
- `EntryEditingController`
- `ContractorEditingController`
- `PhotoAttachmentManager`
- `FormAttachmentManager`

**Layout** (single scrollable column, both modes):
```
AppBar (title: "New Entry" or "Entry {date}" | actions: PDF export, menu)
├── EntryBasicsSection (existing widget, location + weather + temp)
├── EntryContractorsSection (wraps ContractorEditorWidget with controller)
├── EntryActivitiesSection (activities textarea)
├── EntryQuantitiesSection (bid items + quantities)
├── EntrySafetySection (existing widget, safety fields)
├── EntryPhotosSection (photos grid + capture/pick)
├── EntryFormsSection (form attachments list)
└── ActionBar (Save Draft | Submit — or just auto-save indicator in edit mode)
```

**Soft progressive behavior** (create mode only):
- All sections visible from the start
- After saving basics section, auto-scroll to contractors
- After adding contractors, auto-scroll to activities
- Uses `Scrollable.ensureVisible(sectionKey.currentContext)` with animation
- No locking, no step gating — just smart scroll guidance

### 3B: Section Widget Extractions

New section widgets that don't exist yet (existing ones like EntryBasicsSection and EntrySafetySection are reused):

| Widget | Purpose | Key interaction |
|--------|---------|----------------|
| `EntryContractorsSection` | Wraps ContractorEditorWidget, connects to ContractorEditingController | Add/edit/remove contractors |
| `EntryActivitiesSection` | Activities textarea with auto-save | Text input → controller |
| `EntryQuantitiesSection` | Bid item picker + quantity list | Add/edit/remove quantities |
| `EntryPhotosSection` | Photo grid + capture/pick buttons | Delegates to PhotoAttachmentManager |
| `EntryFormsSection` | Form responses list + add button | Delegates to FormAttachmentManager |
| `EntryActionBar` | Save Draft / Submit / auto-save indicator | Calls controller.save() |

Each section widget:
- Accepts its controller via constructor (no Provider.of lookup)
- Has `ValueKey` for dart-mcp testability
- Is independently renderable in a harness

### 3C: PDF Export Integration (E-17)

**New file**: `lib/features/entries/presentation/controllers/pdf_data_builder.dart`

Extracts the 142-line `_exportPdf()` god method into a builder:
- `PdfDataBuilder.fromEntry(DailyEntry, contractors, photos, quantities)` — builds PDF data map
- `PdfDataBuilder.generate(PdfService)` — generates PDF and returns file path
- EntryEditorScreen calls `PdfDataBuilder` instead of inline PDF logic

### 3D: Type-Safe Contractor Data (E-14)

Replace `Map<String, dynamic>` with typed model in entry_wizard flow:
- Create `ContractorEditState` class with typed fields
- ContractorEditingController uses this instead of raw maps
- Eliminates 40+ stringly-typed accesses

### 3E: Data Loading Orchestration (E-15)

**New method on EntryEditorScreen**: `_loadEntryData()` — single method that:
1. Loads DailyEntry from repo
2. Calls `entryEditingController.populateFrom(entry)`
3. Calls `contractorController.loadForEntry(entryId, projectId)`
4. Calls `photoManager.loadPhotos(entryId)`
5. Calls `formManager.loadForms(entryId)`

Replaces the ~100-line load methods currently duplicated 3x.

### 3F: Route Updates

Update `lib/core/router/app_router.dart`:
- Replace wizard route → `EntryEditorScreen(entryId: null, ...)`
- Replace report route → `EntryEditorScreen(entryId: id, ...)`
- HomeScreen "new entry" FAB → navigates to `EntryEditorScreen(entryId: null)`
- EntriesListScreen tap → navigates to `EntryEditorScreen(entryId: entry.id)`

### 3G: Delete Old Files

After EntryEditorScreen is working:
- Delete `entry_wizard_screen.dart` (2,610 lines)
- Delete `report_screen.dart` (2,761 lines)
- Update barrel exports

---

## Phase 4: HomeScreen Cleanup (E-07)

HomeScreen keeps its calendar + inline editing, but now uses shared controllers.

**Changes**:
- Remove all TextEditingControllers (use EntryEditingController)
- Remove all contractor state (use ContractorEditingController)
- Remove `_saveIfEditingContractor()` (use controller method)
- Remove `_saveIfEditing()` entry save (use controller method)
- Keep: calendar, animation, split-view preview, focus listeners
- Adopt: StatusBadge, ContextualFeedbackOverlay, SimpleInfoRow shared widgets

**Estimated reduction**: 2,382 → ~1,200 lines

---

## Phase 5: EntriesListScreen Polish

Minor cleanup (713 lines, smallest screen):
- Adopt shared StatusBadge widget
- Adopt shared ContextualFeedbackOverlay widget
- Verify using shared DeleteEntryDialog widget
- No controller changes needed (read-only screen)

**Estimated reduction**: 713 → ~550 lines

---

## Phase 6: Legacy Cleanup (E-09)

**After** all screens use ContractorEditingController:
- Remove legacy personnel fallback code (dual-track counting with hardcoded foreman/operator/laborer)
- Remove string matching for personnel type names
- ~350 lines of legacy compat code across all screens
- **Requires**: Verify DB migration path for old data

---

## File Inventory

### New files (9)

| File | Type | Lines (est) |
|------|------|-------------|
| `lib/features/entries/presentation/controllers/entry_editing_controller.dart` | ChangeNotifier | ~120 |
| `lib/features/entries/presentation/controllers/contractor_editing_controller.dart` | ChangeNotifier | ~200 |
| `lib/features/entries/presentation/controllers/photo_attachment_manager.dart` | ChangeNotifier | ~100 |
| `lib/features/entries/presentation/controllers/form_attachment_manager.dart` | ChangeNotifier | ~80 |
| `lib/features/entries/presentation/controllers/pdf_data_builder.dart` | Utility | ~60 |
| `lib/features/entries/presentation/screens/entry_editor_screen.dart` | Screen | ~600 |
| `lib/features/entries/presentation/widgets/status_badge.dart` | Widget | ~50 |
| `lib/features/entries/presentation/widgets/simple_info_row.dart` | Widget | ~25 |
| `lib/shared/widgets/contextual_feedback_overlay.dart` | Widget | ~80 |

### New section widgets (6) — extracted from EntryEditorScreen during Phase 3

| File | Lines (est) |
|------|-------------|
| `lib/features/entries/presentation/widgets/entry_contractors_section.dart` | ~60 |
| `lib/features/entries/presentation/widgets/entry_activities_section.dart` | ~50 |
| `lib/features/entries/presentation/widgets/entry_quantities_section.dart` | ~80 |
| `lib/features/entries/presentation/widgets/entry_photos_section.dart` | ~80 |
| `lib/features/entries/presentation/widgets/entry_forms_section.dart` | ~60 |
| `lib/features/entries/presentation/widgets/entry_action_bar.dart` | ~50 |

### Deleted files (2)
- `lib/features/entries/presentation/screens/entry_wizard_screen.dart` (2,610 lines)
- `lib/features/entries/presentation/screens/report_screen.dart` (2,761 lines)

### Modified files (key ones)
- `lib/main.dart` — add Provider registrations for services + controllers
- `lib/core/router/app_router.dart` — update routes
- `lib/features/entries/presentation/screens/home_screen.dart` — adopt controllers
- `lib/features/entries/presentation/screens/entries_list_screen.dart` — adopt shared widgets
- `lib/features/entries/presentation/widgets/widgets.dart` — update barrel export

---

## Estimated Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total entries lines | 8,466 | ~4,800 | -43% |
| Screens with editing | 3 | 2 | -33% |
| TextEditingController copies | 21 (7x3) | 7 (1 controller) | -67% |
| Contractor save method copies | 3 | 1 | -67% |
| Independently testable components | 0 | 6+ controllers/widgets | +6 |
| Files | 4 screens + 10 widgets | 3 screens + 19 widgets + 5 controllers | More modular |

---

## Verification Plan

After each phase:
1. `pwsh -Command "flutter analyze"` — zero new warnings
2. `pwsh -Command "flutter test"` — all existing tests pass
3. Launch app via dart-mcp, navigate to entries feature, verify:
   - Create new entry (soft progressive scroll)
   - Edit existing entry (all sections visible)
   - Add/edit contractors
   - Capture/attach photo
   - PDF export
   - HomeScreen inline editing still works
   - EntriesListScreen filtering and navigation work

After Phase 3 (big merge):
- Create widget test harnesses for EntryEditingController and ContractorEditingController
- Drive harnesses via dart-mcp to verify controller behavior in isolation

---

## Agent Assignments

| Phase | Primary Agent | Support |
|-------|--------------|---------|
| Phase 0 (DI fixes) | backend-data-layer-agent | — |
| Phase 1 (controllers) | backend-data-layer-agent | code-review-agent (validate abstractions) |
| Phase 2 (widgets) | frontend-flutter-specialist-agent | — |
| Phase 3 (EntryEditorScreen) | frontend-flutter-specialist-agent | backend-data-layer-agent (data loading) |
| Phase 4 (HomeScreen) | frontend-flutter-specialist-agent | — |
| Phase 5 (EntriesListScreen) | frontend-flutter-specialist-agent | — |
| Phase 6 (legacy cleanup) | backend-data-layer-agent | qa-testing-agent (verify no regressions) |
| All phases | qa-testing-agent | dart-mcp verification after each phase |

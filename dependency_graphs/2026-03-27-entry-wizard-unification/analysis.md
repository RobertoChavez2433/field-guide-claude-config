# Entry Wizard Unification — Dependency Graph

**Generated**: 2026-03-27
**Spec**: `.claude/specs/2026-03-27-entry-wizard-unification-spec.md`

---

## Direct Changes

| File | Symbol(s) | Lines | Change Type |
|------|-----------|-------|-------------|
| `lib/features/entries/presentation/screens/entry_editor_screen.dart` | `_EntryEditorScreenState._isCreateMode` | 83 | DELETE |
| | `_EntryEditorScreenState._buildCreateSections` | 1080-1139 | DELETE |
| | `_EntryEditorScreenState._buildEditSections` | 1145-1265 | DELETE → merge into `_buildSections()` |
| | `_EntryEditorScreenState._persistCreateEntry` | 343-388 | DELETE |
| | `_EntryEditorScreenState._saveDraft` | 339-341 | DELETE |
| | `_EntryEditorScreenState.build` | 1020-1074 | MODIFY — remove `_isCreateMode` branch |
| | `_EntryEditorScreenState.initState` | 139-148 | MODIFY — add draft creation |
| | `_EntryEditorScreenState._initAndLoad` | 150-163 | MODIFY — merge create/edit load paths |
| | `_EntryEditorScreenState._loadEntryData` | 205-289 | MODIFY — merge create/edit load paths |
| | `_EditableSafetyCardState.build` | 1343-1480 | MODIFY — add extrasOverruns TextField + copy button |
| | `_EntryEditorScreenState._buildSafetySection` | 1274-1292 | MODIFY — pass projectId for copy feature |
| | `_EntryEditorScreenState._buildEntryHeader` | 818-1013 | MODIFY — make adaptive (expand/collapse) |
| | `_extrasController` | 115 | DELETE — replace with controller on EntryEditingController |
| `lib/features/entries/presentation/widgets/entry_safety_section.dart` | `EntrySafetySection` | 9-102 | DELETE FILE |
| `lib/features/entries/presentation/controllers/entry_editing_controller.dart` | `EntryEditingController.buildEntry` | 106-126 | MODIFY — add extrasOverruns |
| | `EntryEditingController.populateFrom` | 90-100 | MODIFY — add extrasOverruns |
| | New: `extrasOverrunsController` | — | ADD field + getter |
| | New: `extrasOverrunsFocus` | — | ADD field + getter |
| `lib/features/entries/presentation/widgets/entry_action_bar.dart` | `EntryActionBar` | 11-151 | MODIFY — remove isCreateMode, onSaveDraft, _buildCreateActions |
| `lib/features/entries/presentation/widgets/entry_basics_section.dart` | `EntryBasicsSection` | 10 | MINOR — used as expandable header component |
| `lib/features/entries/presentation/widgets/entry_contractors_section.dart` | `EntryContractorsSection` | 21 | MODERATE — token migration |
| `lib/features/entries/presentation/widgets/contractor_editor_widget.dart` | `ContractorEditorWidget` | 8 | MODERATE — token migration |
| | `ContractorSummaryWidget` | 529 | MODERATE — token migration |
| `lib/features/entries/presentation/widgets/entry_quantities_section.dart` | `_EntryQuantitiesSectionState.build` | 158 | TRIVIAL — rename header text |
| `lib/core/router/app_router.dart` | entry route | 429-443 | MODIFY — add draft lookup/creation |
| `lib/features/entries/data/repositories/daily_entry_repository.dart` | `DailyEntryRepository` | 10-251 | ADD — `getLastEntrySafetyFields()` |
| `lib/features/entries/data/datasources/local/daily_entry_local_datasource.dart` | `DailyEntryLocalDatasource` | 6-105 | ADD — `getLastEntrySafetyFields()` raw query |
| `lib/main.dart` | startup | 302-304 | ADD — `_seedBuiltinForms()` call |
| `lib/features/forms/presentation/screens/mdot_hub_screen.dart` | `_previewPdf` | 680-688 | MODIFY — remove transient fallback |

## Blast Radius

- **EntryEditorScreen**: 0 external importers (only referenced from router)
- **EntrySafetySection**: 0 external importers (only used in entry_editor_screen.dart)
- **EntryActionBar**: 0 external importers (only used in entry_editor_screen.dart)
- **ContractorEditorWidget**: 0 external importers (only used in entry_contractors_section.dart)

**Blast radius is fully contained within the entry feature + router + main.dart.**

## Test Files

| Test File | Exercises |
|-----------|-----------|
| `test/features/entries/presentation/screens/entry_editor_screen_test.dart` | Entry editor create/edit flows |
| `test/features/entries/presentation/screens/entry_editor_report_test.dart` | Report/edit mode |

## Dead Code After Changes

| Code | File | Reason |
|------|------|--------|
| `_isCreateMode` getter | entry_editor_screen.dart:83 | No mode branching |
| `_buildCreateSections()` | entry_editor_screen.dart:1080-1139 | Replaced by unified method |
| `_buildEditSections()` | entry_editor_screen.dart:1145-1265 | Merged into unified method |
| `_persistCreateEntry()` | entry_editor_screen.dart:343-388 | Draft created at init |
| `_saveDraft()` | entry_editor_screen.dart:339-341 | No explicit save button |
| `_extrasController` standalone | entry_editor_screen.dart:115 | Moved to EntryEditingController |
| `EntrySafetySection` class | entry_safety_section.dart (entire file) | Replaced by unified safety card |
| `EntryActionBar.isCreateMode` | entry_action_bar.dart:14 | Always auto-save mode |
| `EntryActionBar._buildCreateActions` | entry_action_bar.dart:41-85 | No create actions |
| `EntryActionBar.onSaveDraft` | entry_action_bar.dart:22 | No save draft callback |
| `EntryActionBar.onSubmit` | entry_action_bar.dart:23 | No submit callback |
| Transient InspectorForm fallback | mdot_hub_screen.dart:682-687 | Seeded row exists in DB |

## Data Flow Diagram

```
User taps "+" on entries list
    │
    ▼
Router: /entry/:projectId/:date
    │
    ▼
EntryEditorScreen.initState()
    │
    ├── Query: existing draft for project+date?
    │   ├── YES → load existing entry
    │   └── NO  → create minimal draft (projectId, date, status:draft)
    │
    ▼
_loadEntryData() — unified path
    │
    ├── Load locations, contractors, equipment, personnel types, bid items
    ├── Load contractor controller data
    ├── Load photos + forms (if entry exists)
    └── populateFrom(entry) — fills all text controllers
    │
    ▼
_buildSections() — unified, all 9 sections
    │
    ├── Header (adaptive: expanded if empty, collapsed if set)
    ├── Activities (tap-to-edit)
    ├── Contractors (full editor)
    ├── Safety (tap-to-edit + "Copy from last entry" button)
    ├── Pay Items Used (renamed)
    ├── Photos
    ├── Forms
    ├── Status
    └── Auto-save indicator
    │
    ▼
Back button
    │
    ├── _isEmptyDraft()? → Prompt: Keep/Discard
    └── Has data? → Auto-save + pop
```

## Summary Counts

- **Direct**: 13 files
- **Dependent**: 0 (fully contained)
- **Tests**: 2 existing test files
- **Cleanup**: 11 dead code items + 1 file deletion

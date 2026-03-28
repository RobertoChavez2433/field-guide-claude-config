# Deferred Bugs — Context Report for Next Session

Saved 2026-03-27. Full root cause analysis from 4 opus exploration agents.

---

## BUG-SV-3: Entry Wizard Layout Doesn't Match Edit Entry Screen (MEDIUM)

### Summary
The entry creation wizard (multi-step) has a fundamentally different layout than the edit entry screen. This is an **architectural difference**, not a cosmetic bug.

### Key File
`lib/features/entries/presentation/screens/entry_editor_screen.dart`
- Branch at **line 1064**: `_isCreateMode ? _buildCreateSections() : _buildEditSections()`

### CREATE mode (`_buildCreateSections`, lines 1080-1138) — 3 sections + action bar:
| Order | Section | Widget |
|-------|---------|--------|
| 1 | Basics (location, weather, temp) | `EntryBasicsSection` |
| 2 | Activities | `EntryActivitiesSection(alwaysEditing: true)` |
| 3 | Safety | `EntrySafetySection` (direct form fields) |
| 4 | Action bar (save draft) | `EntryActionBar(isCreateMode: true)` |

### EDIT mode (`_buildEditSections`, lines 1145-1264) — 9 sections + action bar:
| Order | Section | Widget |
|-------|---------|--------|
| 1 | Submitted banner (conditional) | `SubmittedBanner` |
| 2 | Header (project, location, weather, date, temp) | `_buildEntryHeader()` (line 818) |
| 3 | Activities | `EntryActivitiesSection(alwaysEditing: false)` |
| 4 | Contractors | `EntryContractorsSection` |
| 5 | Safety | `_EditableSafetyCard` (tap-to-edit wrapper) |
| 6 | Quantities / materials | `EntryQuantitiesSection` |
| 7 | Photos | `EntryPhotosSection` |
| 8 | Forms | `EntryFormsSection` |
| 9 | Status | `EntryStatusSection` |
| 10 | Action bar (auto-save) | `EntryActionBar(isCreateMode: false)` |

### Key Differences
- **Basics vs Header**: Create uses interactive `EntryBasicsSection`, edit uses read-only `_buildEntryHeader()`
- **Activities**: Create passes `alwaysEditing: true`, edit passes `alwaysEditing: false` (tap-to-edit)
- **Safety**: Create uses `EntrySafetySection` directly, edit wraps in `_EditableSafetyCard` (line 1303)
- **5 missing sections in create**: Contractors, Quantities, Photos, Forms, Status
- **Interaction model**: Create = always-editable, Edit = tap-to-edit

### Design Decision Needed
Is this by-design (create = quick draft, edit = full entry)? Or should create become a full wizard? Options:
- A) Accept asymmetry as intentional
- B) Add optional "advanced" sections to create behind expand/collapse
- C) Full unification — same sections in both modes

---

## BUG-SV-6: No Form Templates on Fresh Install (LOW)

### Summary
`inspector_forms` table is empty on fresh install. No startup seeding logic exists. The `hasBuiltinForms()` method exists as an idempotency guard but nothing calls it.

### Current State
- **`hasBuiltinForms()`**: `inspector_form_local_datasource.dart:79-84` — counts rows where `is_builtin = 1`
- **No `seedBuiltinForms()`** exists anywhere in production code
- **Test harness only**: `lib/test_harness/harness_seed_data.dart:258-266` inserts an `InspectorForm` with `isBuiltin: true`

### Asset Files
- `assets/templates/forms/mdot_0582b_form.pdf` — only template PDF on disk
- `assets/data/forms/*.json` — planned directory, never created
- Docs reference `mdot_1174r_concrete.pdf` but file doesn't exist

### How Forms Work Without Seeding (workaround)
- `FormsListScreen._start0582B()` creates a `FormResponse` directly (not an `InspectorForm`)
- `mdot_hub_screen.dart:678-688` creates transient in-memory `InspectorForm` via `orElse:` fallback — never persisted to SQLite

### Table Schema (`toolbox_tables.dart:6-28`)
Key columns: `id`, `project_id` (nullable for builtins), `name`, `template_path`, `field_definitions`, `is_builtin` (DEFAULT 0), `template_source` (DEFAULT 'asset'), `template_hash`, `template_version`, `template_bytes BLOB`, standard audit columns

### Startup Insertion Point
`lib/main.dart:283-307` — detects fresh install via `isFreshInstall` flag. Natural insertion point after repo creation (~line 236), gated behind `hasBuiltinForms()`.

### Fix Shape
1. Create `_seedBuiltinForms()` function
2. Check `hasBuiltinForms()`, if false insert MDOT 0582B record
3. Call from `main.dart` after `InspectorFormRepository` is created
4. Optionally create `assets/data/forms/mdot_0582b.json` for field definitions

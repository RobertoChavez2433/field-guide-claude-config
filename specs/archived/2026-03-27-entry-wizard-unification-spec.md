# Entry Wizard Unification Spec

**Date**: 2026-03-27
**Status**: Approved
**Scope**: Entry screen unification, contractor card cleanup, safety copy, extrasOverruns fix, form seeding, rename

---

## Overview

### Purpose
Eliminate the create/edit entry screen bifurcation that forces inspectors through a fragmented workflow. Unify into a single screen that immediately creates a draft and presents the full editor. Simultaneously fix the contractor card's visual inconsistencies, a silent data-loss bug on the `extrasOverruns` field, and seed the 0582B form template on fresh install.

### Scope
| In | Out |
|----|-----|
| Unified entry screen (no `_isCreateMode`) | SV-1/2/4/5 fixes (separate plan) |
| Immediate draft persistence on create | New form templates beyond 0582B |
| Adaptive header (expanded → tap-to-edit) | Step-by-step wizard progress bar |
| Safety card "Copy from last entry" | Theme token system redesign |
| Fix `extrasOverruns` save + edit | |
| Contractor card token migration + spacing | |
| Rename "Materials Used" → "Pay Items Used" | |
| Seed 0582B on fresh install | |

### Success Criteria
- [ ] No `_isCreateMode` branching in `entry_editor_screen.dart`
- [ ] Create entry navigates to unified screen with all 9 sections visible
- [ ] Header auto-expands when location/weather empty, collapses when set
- [ ] "Copy from last entry" fills empty safety fields from most recent same-project entry
- [ ] `extrasOverruns` persists on save and is editable in the safety card
- [ ] Contractor card uses zero hardcoded font sizes — all `textTheme` references
- [ ] UI reads "Pay Items Used" not "Materials Used"
- [ ] Fresh install has 0582B in `inspector_forms` table

---

## Data Model

### No New Entities

No new tables or models. All changes operate on existing structures.

### Modified Behavior: Entry Creation

Currently `_persistCreateEntry()` builds a full `DailyEntry` with location/weather/text fields before inserting. The new flow inserts a minimal draft immediately on navigation:

| Field | Value |
|-------|-------|
| `id` | Pre-generated UUID (existing `_pendingEntryId` pattern) |
| `projectId` | From route parameter |
| `date` | From route parameter |
| `status` | `EntryStatus.draft` |
| `createdByUserId` | Current auth user |
| `createdAt` / `updatedAt` | `DateTime.now()` |

All other fields (`locationId`, `weather`, `tempLow`, `tempHigh`, activities, safety fields) start null/empty and get populated via auto-save as the user fills them in.

### New Query: Last Entry Safety Fields

Repository method to fetch the most recent entry's safety fields for the "Copy from last entry" feature:

```sql
SELECT site_safety, sesc_measures, traffic_control, visitors, extras_overruns
FROM daily_entries
WHERE project_id = ? AND deleted_at IS NULL
ORDER BY date DESC, created_at DESC
LIMIT 1
```

Returns a map of field values. No new model needed — just a raw query returning the 5 string fields.

### Form Seeding Record

One `InspectorForm` row inserted on fresh install:

| Field | Value |
|-------|-------|
| `id` | `'mdot_0582b'` (matches existing hardcoded references) |
| `projectId` | `null` (built-in, not project-specific) |
| `name` | `'MDOT 0582B Density'` |
| `templatePath` | `FormPdfService.mdot0582bTemplatePath` |
| `isBuiltin` | `true` |
| `templateSource` | `TemplateSource.asset` |
| `templateVersion` | `1` |

### Sync Considerations

- Minimal draft creation uses the same `createEntry()` path — change_log picks it up automatically
- The safety field copy is a local read followed by normal field edits — no sync implications
- The seeded `InspectorForm` is local-only (built-in forms don't sync to Supabase)

---

## User Flow

### Entry Points (unchanged)

1. **Entries list screen** → "+" FAB → picks date → navigates to `/entry/:projectId/:date`
2. **Entries list screen** → taps existing entry → navigates to `/report/:entryId`

### New Unified Flow

Both routes resolve to the same unified screen. The only difference is whether an `entryId` exists yet.

```
Route: /entry/:projectId/:date (no entryId)
  → Screen opens
  → Checks for existing draft on same project+date
  → If found: loads existing draft
  → If not: persists minimal draft (projectId + date + draft status)
  → Now has an entryId
  → Renders full editor (all 9 sections)
  → Header basics expanded (location/weather empty)

Route: /report/:entryId
  → Screen opens
  → Loads existing entry by ID
  → Renders full editor (all 9 sections)
  → Header collapsed (values already set) or expanded (if still empty)
```

### Screen Layout (unified, top to bottom)

| # | Section | Behavior |
|---|---------|----------|
| 1 | Submitted banner | Conditional — only when `status == submitted` |
| 2 | Header / Basics | **Expanded** if location or weather empty. **Collapsed** (tap-to-edit) once both set. |
| 3 | Activities | Tap-to-edit text field |
| 4 | Contractors | Full contractor card list with personnel + equipment |
| 5 | Safety & Site Conditions | Tap-to-edit card with "Copy from last entry" button. 5 fields: site safety, SESC, traffic control, visitors, extras & overruns |
| 6 | Pay Items Used | _(renamed from "Materials Used")_ Bid item quantities |
| 7 | Photos | Photo grid with capture/gallery |
| 8 | Forms | Attached form responses + "Start New Form" |
| 9 | Status | Draft/Submitted badge + signature |
| 10 | Action bar | Auto-save indicator |

### "Copy from Last Entry" Interaction

1. User taps "Copy from last entry" button on safety card
2. System queries most recent entry on same project
3. Only fills fields that are currently empty
4. If no previous entry exists, button is disabled or hidden
5. Toast: "Copied from [date] entry" (so user knows what they got)

### Back Button Behavior

- If entry has any meaningful data (location set, any text field filled, any contractors/photos/quantities/forms added): auto-save and pop. No prompt.
- If entry is still a bare skeleton (only `projectId + date + status: draft`): show dialog — "Discard empty draft?" with "Discard" (delete + pop) and "Keep Draft" (pop).

---

## UI Components

### Modified Widgets

| Widget | File | Change |
|--------|------|--------|
| `EntryEditorScreen` | `entry_editor_screen.dart` | Remove `_isCreateMode` branch. Single `_buildSections()` method. Immediate draft creation in `initState`. Back prompt for empty drafts. |
| `EntryBasicsSection` | `entry_basics_section.dart` | Becomes the "expanded header" — shown when location or weather is empty. Hidden when both set (replaced by tap-to-edit header). |
| `_buildEntryHeader` | `entry_editor_screen.dart` | Becomes the "collapsed header" — shown when location and weather are populated. Tap to re-expand basics. |
| `_EditableSafetyCard` | `entry_editor_screen.dart` | Add `extrasOverruns` TextField in edit mode. Add "Copy from last entry" button. |
| `EntrySafetySection` | `entry_safety_section.dart` | Delete — create-only widget replaced by unified `_EditableSafetyCard` |
| `EntryActionBar` | `entry_action_bar.dart` | Remove `isCreateMode` parameter and "Save Draft" button. Always show auto-save indicator. |
| `EntryQuantitiesSection` | `entry_quantities_section.dart` | Rename header text "Materials Used" → "Pay Items Used" |
| `ContractorEditorWidget` | `contractor_editor_widget.dart` | Migrate all hardcoded font sizes to `textTheme`. Normalize spacing tokens. |
| `EntryContractorsSection` | `entry_contractors_section.dart` | Migrate hardcoded styles to `textTheme`. Normalize padding/spacing. |

### Contractor Card Token Migration

**Typography** — map to `textTheme`:

| Current (hardcoded) | Proposed (theme token) |
|----------------------|------------------------|
| Section header 16px bold | `titleMedium` |
| Contractor name 14-15px w600 (inconsistent) | `titleSmall` (consistent across view/edit) |
| Body text 12px (counts, descriptions) | `bodySmall` |
| Chip labels 11-12px (inconsistent) | `labelSmall` (consistent across view/edit) |
| Button text 11-13px | `labelMedium` |
| Badge text 10px | `labelSmall` |
| Counter value 14px bold | `titleSmall` |

**Spacing** — replace hardcoded values with `AppTheme.space*` tokens:

| Current (hardcoded) | Proposed (token) |
|---------------------|------------------|
| Header padding `EdgeInsets.all(16)` | `AppTheme.space4` (16) |
| Footer padding `EdgeInsets.all(12)` | `AppTheme.space4` (match header) |
| Icon-to-text gap 4-8px inconsistent | `AppTheme.space2` (8) everywhere |
| Equipment wrap spacing 6/4 vs 6/6 | `AppTheme.space2` (8) / `AppTheme.space1` (4) consistent |
| Personnel wrap spacing 16/8 | `AppTheme.space4` (16) / `AppTheme.space2` (8) |
| Section gaps (SizedBox 4-12px) | `AppTheme.space2` (8) standard, `AppTheme.space3` (12) between major sections |

**Border radius** — replace hardcoded `Radius.circular(12)` and `4` with `AppTheme.radiusMedium` and `AppTheme.radiusSmall`.

### Empty Draft Detection

Helper method `_isEmptyDraft(DailyEntry entry)` checks: no locationId, no weather, no temperature, no activities, no safety fields, no contractors, no photos, no quantities, no forms. Used to trigger the keep/discard prompt on back.

### Back Prompt Dialog

Simple `AlertDialog`:
- Title: "Discard empty draft?"
- Content: "This entry has no data yet."
- Actions: "Discard" (delete + pop) / "Keep Draft" (pop)

---

## State Management

### Entry Creation Flow Change

Currently `DailyEntryProvider.createEntry()` is called from `_persistCreateEntry()` on explicit "Save Draft" tap. New flow:

1. Screen `initState` (or `didChangeDependencies`) — if no `entryId` in route params:
   - Check for existing draft: `WHERE project_id = ? AND date = ? AND deleted_at IS NULL`
   - If found: load it as `_currentEntry`
   - If not: build minimal `DailyEntry(id: uuid, projectId, date, status: draft)`, call `entryProvider.createEntry(minimalEntry)`, store as `_currentEntry`
   - Screen now behaves identically to edit mode

2. All subsequent edits go through the existing auto-save path (`entryProvider.updateEntry()`)

### Auto-Save for All Fields

With unification, auto-save works from the start:
- **Activities**: saves on focus loss (existing behavior)
- **Safety fields**: saves on "Done" button (existing behavior) — now includes `extrasOverruns`
- **Temperature**: saves on "Done" button (existing behavior)
- **Location/Weather**: saves on selection (header dropdowns)
- **Contractors/Photos/Quantities/Forms**: already auto-persist through their own providers

No new providers or repositories needed. The `EntryEditingController` gains one field: wire `extrasOverruns` into `buildEntry()`.

### "Copy from Last Entry" State Flow

1. Button tap → call new `DailyEntryRepository.getLastEntrySafetyFields(projectId)`
2. Returns `Map<String, String?>` with the 5 field values
3. For each field: if the current controller text is empty, set it from the map
4. Mark the editing controller as dirty → triggers auto-save on next blur/Done

No caching needed — it's a one-time query per tap.

### Empty Draft Detection

`_isEmptyDraft()` checks the in-memory `_currentEntry` plus controllers:
- All text controllers empty (activities, safety fields, temperature)
- No locationId set
- No weather set
- Contractor count == 0
- Photo count == 0
- Quantity count == 0
- Form count == 0

Local check — no DB query needed.

---

## Edge Cases

### Error States

| Scenario | Handling | UI Feedback |
|----------|----------|-------------|
| Draft creation fails (DB error on open) | Catch, show error, pop back | Snackbar: "Failed to create entry" |
| No previous entry for safety copy | Button disabled or hidden | No button shown if no prior entries exist |
| User creates entry for date that already has a draft | Detect existing draft, open it instead of creating duplicate | Navigate to existing entry — no duplicate rows |
| Back button during active edit (field has focus) | Save current field first, then run empty draft check | Seamless — auto-save fires before prompt |
| App killed mid-creation | Minimal draft already persisted | User finds draft in entries list on next launch |

### Duplicate Date Guard

If the user taps "+" and picks a date that already has a draft entry for that project, open the existing draft rather than creating a second one. Query at screen open: `WHERE project_id = ? AND date = ? AND deleted_at IS NULL`. If found, load it. If not, create the minimal draft.

### Boundaries

- **Empty draft cleanup**: Only the keep/discard prompt on back. No background job or timer deleting old empty drafts.
- **Safety copy with all fields populated**: Button still visible but tap is a no-op (all fields already have content). Toast: "All fields already have data"
- **Safety copy when previous entry has null fields**: Only copies non-null values into empty fields. Null source fields are skipped.

### Permission Edge Cases

- `canEditFieldData` auth check still gates all editing (existing behavior, unchanged)
- Submitted entries: submitted banner shows, fields become read-only (existing behavior, unchanged)
- No new permission concerns — same data, same operations, just unified screen

---

## Migration/Cleanup

### Dead Code Removal

| Code | File | Reason |
|------|------|--------|
| `_isCreateMode` field | `entry_editor_screen.dart:83` | No longer needed — always full editor |
| `_buildCreateSections()` | `entry_editor_screen.dart:1080-1139` | Replaced by unified `_buildSections()` |
| `_buildEditSections()` | `entry_editor_screen.dart:1145-1265` | Merged into unified `_buildSections()` |
| `_persistCreateEntry()` | `entry_editor_screen.dart:339-388` | Draft created in initState instead |
| `_saveDraft()` | `entry_editor_screen.dart` | No explicit save button — auto-save only |
| `EntrySafetySection` widget | `entry_safety_section.dart` | Replaced by unified `_EditableSafetyCard` |
| `EntryActionBar.isCreateMode` param | `entry_action_bar.dart` | Always auto-save indicator |
| `safeGoBack` call after save | `entry_editor_screen.dart:383` | No post-save navigation — user is already on the screen |
| Transient `InspectorForm` fallback in `MdotHubScreen` | `mdot_hub_screen.dart:682-687` | Seeded row exists in DB now |

### Route Changes

Currently two separate routes:
- `/entry/:projectId/:date` (create) → `app_router.dart:430-443`
- `/report/:entryId` (edit) → `app_router.dart:446-454`

New behavior:
- `/entry/:projectId/:date` — checks for existing draft, creates if needed, opens unified screen with entryId
- `/report/:entryId` — opens unified screen with entryId
- Both routes resolve to the same screen. The create route does the draft lookup/creation first.

### Schema Changes

None. No new tables, no new columns, no migrations. All changes are app-layer only.

### `EntryEditingController` Change

Add `extrasOverruns` to `buildEntry()` method (line 106-126). One field addition — not a structural change.

### Files Touched Summary

| File | Change Type |
|------|-------------|
| `entry_editor_screen.dart` | Major refactor — remove branching, add draft creation, back prompt, adaptive header |
| `entry_safety_section.dart` | Delete (replaced by unified safety card) |
| `entry_editing_controller.dart` | Minor — add `extrasOverruns` to `buildEntry()` |
| `entry_action_bar.dart` | Minor — remove `isCreateMode` param |
| `entry_basics_section.dart` | Minor — used as expandable header component |
| `entry_contractors_section.dart` | Moderate — token migration |
| `contractor_editor_widget.dart` | Moderate — token migration |
| `entry_quantities_section.dart` | Trivial — rename header text |
| `app_router.dart` | Minor — create route does draft lookup/creation |
| `daily_entry_repository.dart` | Minor — add `getLastEntrySafetyFields()` |
| `daily_entry_local_datasource.dart` | Minor — add safety fields query |
| `main.dart` | Minor — add `_seedBuiltinForms()` at startup |
| `mdot_hub_screen.dart` | Minor — remove transient fallback |

---

## Decisions Log

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| Unified screen, no mode branching | Continuity — same screen for create and edit | Keep lite create mode (fragmented UX) |
| Immediate draft persistence on open | Enables auto-save from first interaction, photos can reference entry ID | Persist on explicit save (current behavior — forces manual re-find) |
| Adaptive header (expanded → collapsed) | Best of both worlds — guided on first fill, compact after | Always expanded (wastes space), always collapsed (not discoverable) |
| "Copy from last entry" fills empty only | Respects user edits, prevents accidental overwrites | Overwrite all (destructive), per-field copy icons (too granular) |
| Keep/discard prompt on empty back | User choice, no silent data loss or orphan clutter | Auto-delete (surprising), keep all (orphan drafts) |
| Contractor card uses existing tokens | Consistency with design system, no new abstractions | Keep hardcoded values (inconsistent), redesign token system (out of scope) |
| Seed 0582B only | Only template that exists on disk | Build seeding framework for future forms (YAGNI) |

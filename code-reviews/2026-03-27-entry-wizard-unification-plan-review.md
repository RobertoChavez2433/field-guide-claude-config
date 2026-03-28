# Entry Wizard Unification — Plan Review

**Date**: 2026-03-27
**Plan**: `.claude/plans/2026-03-27-entry-wizard-unification.md`
**Spec**: `.claude/specs/2026-03-27-entry-wizard-unification-spec.md`

---

## Code Review: REJECT → fix and resubmit

### CRITICAL (4)

1. **`RepositoryResult` has no `.when()` method** — Steps 2.1.2, 3.1.3
   - `RepositoryResult` has `.data`, `.error`, `.isSuccess` only
   - Fix: `if (result.isSuccess) { entry = result.data; } else { /* error */ }`

2. **`context.read<DailyEntryRepository>()` not registered as Provider** — Steps 2.1.2, 2.1.6, 3.1.3
   - Repository is constructed in main.dart but never registered standalone
   - Fix: Access via provider's repository getter or use datasource directly

3. **`DailyEntryProvider` has no `getByDate()` method** — Step 2.1.2
   - Fix: Use repository directly via the provider's public getter

4. **Wrong DB access pattern in datasource query** — Step 1.2.1
   - `db` is `DatabaseService`, not `Database`. Need `final database = await db.database;` first

### HIGH (4)

5. **Draft creation pre-fills fields spec says should be null** — Step 2.1.2
   - Plan sets `locationId: widget.locationId` and `weather: WeatherCondition.sunny`
   - Spec requires all null/empty. Breaks adaptive header logic.

6. **Empty draft detection logic wrong** — Step 2.1.6
   - Uses `_isDraftEntry && !_editingController.isDirty` but `isDirty` only tracks text changes
   - Need `_isEmptyDraft()` helper checking all providers (photos, contractors, quantities, forms)

7. **`createdByUserId` missing from draft** — Step 2.1.2
   - Spec requires it. Without it, `canEditEntry()` treats null-owner as legacy = any user can edit.
   - Fix: Add `createdByUserId: context.read<AuthProvider>().userId`

8. **Form seed name mismatch** — Step 1.3.1
   - Plan: `'MDOT 0582B'`. Spec: `'MDOT 0582B Density'`

### MEDIUM (5)

9. Safety query missing `created_at DESC` tiebreaker
10. Not all `_isCreateMode` references enumerated (8 total)
11. `_startEditing()` won't populate new extrasOverrunsController
12. Copy button wiring unclear — needs `onCopyFromLast` callback param on `_EditableSafetyCard`
13. `_buildSafetySection` wrapper method not addressed in plan

### MINOR
- `_markDirty` listener pattern wrong — controller uses `markDirty()` via UI `onChanged`
- Template defaults omitted (harmless — constructor defaults handle it)
- Duplicate draft check returns all entries including submitted — filter to draft only

---

## Security Review: APPROVE with conditions

### HIGH (2, overlapping with code review)
1. `createdByUserId` missing from draft (= HIGH #7 above)
2. Duplicate draft check returns submitted entries too — filter to `status == draft`

### PASSED
- Auth/permission gates preserved (all 5 checks survive)
- "Copy from last entry" correctly project-scoped
- Safety query respects `deleted_at IS NULL`
- Form seeding safe (deterministic, idempotent)
- Draft DoS mitigated by one-per-project-per-date guard
- No new untrusted input boundaries

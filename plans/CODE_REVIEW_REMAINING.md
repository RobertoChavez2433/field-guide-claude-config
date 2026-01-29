# Code Review Remaining Items

**Created**: 2026-01-29 (Session 185)
**Updated**: 2026-01-29 (Session 186) - All items complete
**Source**: Verification of CODE_REVIEW_BACKLOG.md items

Items verified against current codebase. Original 32 items reviewed.

---

## Summary

| Status | Count | Description |
|--------|-------|-------------|
| ✅ Fixed | 32 | All items implemented or resolved |
| ⏳ Remaining | 0 | None |

---

## ✅ Fixed Items (32)

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Enum deserialization without fallback | Uses `byNameOr()` with fallback |
| 2 | Index-based enum serialization | Uses `priority.name` + `_parsePriority()` with legacy support |
| 3 | Missing `updatedAt` in immutable models | Documented as intentional design (append-only) |
| 4 | Shared enum parsing utility | `lib/shared/utils/enum_utils.dart` created |
| 5 | Missing `toString()` methods | Both `CalculationHistory` and `TodoItem` have `toString()` |
| 6 | FormSeedService optional parameter | Uses named parameter pattern |
| 7 | Document case normalization | `FieldSemanticAlias` has doc comment explaining normalization |
| 8-10 | Carry-forward cache issues | Fixed in Session 160 |
| 11 | Tests don't test actual AutoFillEngine | Tests now use real `AutoFillEngine`, `AutoFillContext`, `AutoFillResult` |
| 12 | FormFillScreen local state | Removed unused FormFillProvider (Session 186) |
| 13 | Async context safety in AutoFillContextBuilder | Constructor DI refactor (Session 186) |
| 14 | Duplicate `_generateInitialsFromName` | Method removed, uses `prefsService.effectiveInitials` |
| 15 | Hardcoded auto-fill field list | `_isFieldAutoFillable()` and `_getAutoFillSource()` removed |
| 16 | Magic strings in auto-fill matching | Documented as intentional for performance |
| 17 | Confidence visual differentiation | Added to AutoFillIndicator (Session 185) |
| 18 | Duplicate CalculationResult classes | Renamed to FormCalculationResult (Session 185) |
| 19 | Auto-fill context building duplication | Uses shared `_performAutoFill()` method |
| 20 | Magic numbers for compaction spec | Uses `DensityCompactionSpecs` constants |
| 21 | FormFieldsTab 28+ parameters | Grouped into 6 config objects (Session 186) |
| 22 | Debug print without kDebugMode | Added guard in FormStateHasher (Session 185) |
| 23 | Status helpers could be shared | Created FormResponseStatusHelper (Session 185) |
| 24 | Missing mounted check in FieldMappingScreen | Fixed in Session 165 |
| 25 | updateMapping uses filtered index | Added `updateMappingByObject()`, old method deprecated |
| 26 | Providers not registered in main.dart | Fixed in Session 165 |
| 27 | saveForm has TODO - not integrated | Fixed in Session 165 |
| 28 | Duplicate `_getFieldIcon` functions | No longer found in codebase |
| 29 | Stub classes use fragile pattern | No longer found in codebase |
| 30 | Dead applyCategory code | Removed from FieldMappingProvider (Session 185) |
| 31 | Async context reads in context builder | Constructor DI refactor (Session 186) |
| 32 | Temp auto-fill helpers | `_isFieldAutoFillable()` and `_getAutoFillSource()` removed |

---

## Session 186 Fixes

### #12. FormFillScreen Uses Local State Instead of Provider
**Resolution**: Removed unused `FormFillProvider` - it was dead code never integrated.
- Deleted `lib/features/toolbox/presentation/providers/form_fill_provider.dart`
- Updated barrel export

### #13. Async Context Safety in AutoFillContextBuilder
**Resolution**: Refactored to use constructor dependency injection.
- All repositories passed via constructor
- No more `context.read<T>()` inside async methods
- Eliminates `use_build_context_synchronously` warnings

### #21. FormFieldsTab Has Many Parameters (28+)
**Resolution**: Created 6 config classes to group related parameters:
- `FormFieldsConfig` - fields, controllers, editability
- `AutoFillConfig` - auto-fill results and callbacks
- `QuickEntryConfig` - quick entry controller and callbacks
- `ParsingConfig` - parsing preview state
- `TableConfig` - table row data
- `TestHistoryConfig` - test history display

---

## Reference

- Original backlog: `.claude/plans/CODE_REVIEW_BACKLOG.md`
- Session 185: Fixed items 17, 18, 22, 23, 30
- Session 186: Fixed items 12, 13, 21

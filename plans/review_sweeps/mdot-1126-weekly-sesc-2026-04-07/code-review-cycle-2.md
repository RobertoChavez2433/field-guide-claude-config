# Code Review — Cycle 2

**Plan**: `.claude/plans/2026-04-06-mdot-1126-weekly-sesc.md`
**Reviewer**: code-review-agent (opus)
**Date**: 2026-04-07

## VERDICT: REJECT

Cycle-1 fixes landed nearly all required corrections. All of the original bad symbols are gone from active code blocks, registries/API signatures match verified codebase shapes, and new phases (6.4 carry-forward, 8.0 ExportBlockedException, 9.0 SescReminderProvider, 7.7 repo-layer invalidation, 5.3.1.a SignatureContextProvider) are coherent.

**However, one new compile-breaking defect was introduced** during the AppSegmented → AppChip swap.

## NEW CRITICAL DEFECT — AppChip props (Phase 7.3.2 SescMeasuresChecklist)

Plan code uses:
```dart
AppChip(
  label: label,
  selected: (measures[i]['status']?.toString() ?? 'in_place') == value,
  onSelected: (_) => onChange(i, {...}),
)
```

Actual `AppChip` (`lib/core/design_system/atoms/app_chip.dart:16-32`):
```dart
const AppChip({
  required String label,
  required Color backgroundColor,
  required Color foregroundColor,
  IconData? icon,
  VoidCallback? onTap,
  VoidCallback? onDeleted,
});
```

No `selected:`, no `onSelected:`. Named factories (`AppChip.cyan/amber/error/...`) wrap colors only.

**Fix options:**
1. Use `AppChip.cyan/amber/...` factories with `onTap:` — select color based on `status == value` in parent.
2. Use Material `ChoiceChip` directly if `no_raw_chip` lint doesn't exist.
3. Add a new `AppChoiceChip` / `AppToggleChip` to design system (out of scope).

Option (1) is the minimal, correct fix. The NOTE in the plan telling implementers to "verify" prop names is not sufficient — these props do not exist on any AppChip overload.

## Cycle-1 Findings Status

All 21 cycle-1 findings verified RESOLVED. Spot checks:
- `AppCard`, `AppButton.tertiary`, `AppBanner(title:`, `is_user_in_company`, `company_users`, `markDirty` → all gone from code blocks
- `WizardActivityTracker` API matches verified `register(key/label/hasUnsavedChanges)` + `markChanged(key)`
- `FormQuickAction.execute(response)` signature correct
- `SchemaVerifier` uses `Map<String, List<String>>` + `_columnTypes` partition correctly
- `builtinForms` edited in place, not redeclared
- `FieldGuideSpacing.of(context)` verified as real static accessor at `field_guide_spacing.dart:85`
- Phase 7.7 universal invalidation correctly moved to `FormResponseRepositoryImpl.update`
- Phase 6.4 carry-forward orchestration wires LoadPrior + BuildCarryForward
- Phase 5.3.1 signature embedding + weekly anchor persistence correct

## Medium (non-blocking)

- **Missing `Uuid` import** in Phase 7.5 add-measures step — mention as NOTE
- **Provider registration reminder** — SignatureContextProvider, FormPdfService, SignFormResponseUseCase, Resolve1126AttachmentEntryUseCase, CreateInspectionDateEntryUseCase must be exposed in widget-tree tier 5 so `context.read<...>()` calls in widget code resolve (Phase 10.1.1 lists but should be explicit)
- **Phase 7.7 `getById` return type** assumed `FormResponse?` — verify if actual is `Future<RepositoryResult<FormResponse>>` and unwrap `.data`

## Low

- DRY: `FormDateUtils.toIsoDate(DateTime)` could dedupe ISO formatting across multiple use cases
- Raw `EdgeInsets.only/all` at multiple call sites using token values — verify `no_hardcoded_spacing` lint allows token-derived values

## Action Required

Fix the AppChip API mismatch in Phase 7.3.2 to use the verified factory pattern. All other findings are non-blocking. Re-review after fix.

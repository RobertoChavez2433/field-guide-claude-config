# Code Review — Cycle 1

> **STATUS:** Addressed in fixer cycle 1. See `fixer-cycle-1-summary.md`.



**Plan**: `.claude/plans/2026-04-06-mdot-1126-weekly-sesc.md`
**Reviewer**: code-review-agent (opus)
**Date**: 2026-04-07

## VERDICT: REJECT

## Critical (compile-breaking)

### Design System (Phase 7)
- **`AppCard` does not exist.** Use `AppSectionCard` (organisms/app_section_card.dart) which requires `icon`, `title`, `child`, or `AppGlassCard`. Used in: RainfallEventsEditor, SescMeasuresChecklist, SignaturePadField, WeeklySescReminderCard, toolbox TODO (9.3.1).
- **`AppCard(onTap: ...)` is invalid** — `AppSectionCard` has no `onTap` param. Wrap in `InkWell` or use `ListTile`.
- **`AppButton.tertiary` does not exist** — only `primary/secondary/ghost/danger/icon`. Use `AppButton.ghost` in SignaturePadField Clear button (7.3.4).
- **`AppSegmented` / `AppSegmentedOption` do not exist.** SescMeasuresChecklist (7.3.2) needs replacement — use `AppChip` row with selection state, or add new DS component first.
- **`AppBanner(title:, subtitle:, onTap:)` is wrong.** Actual API: `AppBanner({required IconData icon, required String message, AppBannerSeverity? severity, List<Widget> actions, bool dismissible, VoidCallback? onDismiss})`. Rewrite 7.4.1 to use `icon`, `message`, `severity: AppBannerSeverity.warning`, and `actions: [AppButton.ghost(label: 'Open', onPressed: onTap)]`.
- **`FieldGuideSpacing.of(context)` does not exist** as static. It's a `ThemeExtension`. Use `Theme.of(context).extension<FieldGuideSpacing>()!` (or the canonical context extension if present — grep `lib/core/design_system/tokens/field_guide_spacing.dart` first).
- **Import paths wrong:** `core/design_system/layout/spacing.dart` and `core/design_system/molecules/app_card.dart` do not exist. Use `package:construction_inspector/core/design_system/design_system.dart` barrel.
- **`AppIcons.rain`** does not exist; use `Icons.water_drop` directly — `FormQuickAction.icon` is typed `IconData`.

### Registries
- **`FormQuickAction.execute` signature wrong** — it's `FormQuickActionResult Function(FormResponse response)`, not `() => ...`. Phase 6.3.1 must be `execute: (response) => const FormQuickActionResult.navigate(...)`.
- **`builtinForms` is `final`, not `const`** — Phase 6.3.2 must edit the existing list literal in place, not redeclare.

### Schema Verifier
- **`expectedSchema` shape is wrong.** Actual type is `Map<String, List<String>>` (column name lists), not `Map<String, Map<String, String>>`. Column types live in a separate `_columnTypes` map only for non-TEXT columns. Fix Phase 2.3.1 to add both tables' column lists and add only `file_size_bytes` (INTEGER), `gps_lat` (REAL), `gps_lng` (REAL) to `_columnTypes`.

### WizardActivityTracker (Phase 7.2.1)
- **API mismatch.** Actual `register({required String key, required String label, required bool Function() hasUnsavedChanges})`. Actual method is `markChanged(String key)`, not `markDirty`. Plan's calls will not compile.

## High
- **`ExportBlockedException` undefined** — referenced in Phase 8.1.3 but never created. Add a file `lib/features/entries/domain/errors/export_blocked_exception.dart`.
- **Phase 7.5 `_build<Step>` bodies stubbed with `...`** — must commit to actual bindings, not `formProvider.saveFormResponse(...)` (unverified).
- **Phase 7.7 hook location unverified** — `inspector_form_provider_response_actions.dart` not verified. Add a grep step.
- **CLAUDE.md "5 files" rule** — plan touches 4 (database_service, schema/new, schema_verifier, 2 test helpers). Locate and add the fifth touch.

## Medium
- **Phase 2.4 line number citations** (`:587`, `:152`) are brittle — reference by helper name only.
- **Phase 5.2.1 `LoadPrior1126UseCase` docstring** says "most-recent signed" but returns latest of any status. Either filter or fix docstring.
- **Phase 4.1.1 misleading comment** on `stripExifGps: false` — it gates FileSyncHandler behavior generically, not PNG-specific.
- **Phase 5.4.1 `matches.first`** → use `matches.firstOrNull` per agent-memory rule.

## Low
- DRY: extract `FormDateUtils` for repeated ISO parse/format logic.

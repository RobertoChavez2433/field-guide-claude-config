# Reviewer Rules

Static context for all 3 reviewer types. Appended via `--append-system-prompt-file`.

## Reviewer Baseline Rules
- You are READ-ONLY. NEVER modify source code.
- Scope: review ONLY files from the current phase, not the entire codebase.
- Always read the spec first — it is the source of truth for intent.
- Always read the plan — it defines what should have been implemented.

## Severity Calibration

| Level | Definition | Blocks approval? |
|-------|-----------|-----------------|
| CRITICAL | Breaks functionality, security vuln, spec requirement completely missing | YES |
| HIGH | Wrong behavior, missing error handling, key requirement partially missing | YES |
| MEDIUM | Suboptimal pattern, missing edge case, doesn't fully match spec intent | YES |
| LOW | Style, naming, minor improvement, nitpick | NO (logged only) |

## Verdict Rules
- **"approve"** — Zero findings at CRITICAL, HIGH, or MEDIUM severity
- **"reject"** — One or more findings at CRITICAL, HIGH, or MEDIUM severity
- LOW findings do not affect verdict but MUST still be reported

## Implementation Shortcuts (CRITICAL severity — always flag)

AI implementers commonly use these shortcuts to appear done while skipping real work.
Grep for ALL of these patterns across every file in the phase. Any match is CRITICAL.

- `// ignore:` or `// ignore_for_file:` — lint suppression instead of fixing root cause
- `// TODO`, `// FIXME`, `// HACK`, `// PLACEHOLDER` — deferred work disguised as completion
- `// removed`, `// deleted`, `// no longer needed` — fake cleanup commentary
- `throw UnimplementedError()` or `throw UnsupportedError()` — stub implementations
- Empty method bodies or methods that only return `null`/`[]`/`{}`/`0`/`false` when real logic is required
- `pass`-equivalent patterns: catch blocks that silently swallow errors with no logging
- Test methods with no assertions (`expect`, `verify`, `check`) — skeleton tests that always pass
- `skip:` parameter on tests — skipped tests count as missing
- Hardcoded return values that bypass actual logic (e.g., `return true;` instead of real validation)
- `print()` instead of proper `Logger` calls — debug leftovers
- Commented-out code blocks — dead code left behind instead of implementing or removing
- `as dynamic` or `as Object` casts to bypass type safety
- Dummy/placeholder class names (`MyWidget`, `TempProvider`, `TestClass` in non-test code)

## Anti-Patterns to Flag
- God Class (>500 lines, too many responsibilities)
- Copy-Paste (duplicate logic across files)
- Magic Values (hardcoded numbers/strings without constants)
- Over-Engineering (abstractions for single use cases)
- Missing Null Safety (force unwraps, missing null checks)
- Async Anti-patterns (missing await, fire-and-forget, no mounted check)

## Design System Red Flags (HIGH severity — always flag)

In any file under `lib/**/presentation/**` or `lib/shared/widgets/**`:

- **Raw Material widgets** instead of design system equivalents:
  - `ElevatedButton`/`TextButton`/`OutlinedButton`/`FilledButton`/`IconButton` (use `AppButton.*`)
  - `Divider`/`VerticalDivider` (use `AppDivider`)
  - `Tooltip` (use `AppTooltip`)
  - `DropdownButton`/`DropdownButtonFormField` (use `AppDropdown`)
  - `SnackBar(` constructor (use `SnackBarHelper.show*()` / `AppSnackbar`)
  - `Scaffold(` in screen files (use `AppScaffold`)
  - `AlertDialog`/`showDialog`/`showModalBottomSheet` (use `AppDialog.show()`/`AppBottomSheet.show()`)
  - Inline `TextStyle(...)` (use `AppText.*` or textTheme)
  - Inline `Container`/`MaterialBanner` for notifications (use `AppBanner`)
- **Hardcoded design tokens**:
  - Numeric `EdgeInsets`/`SizedBox` literals (must use `FieldGuideSpacing.of(context).*`)
  - `BorderRadius.circular(N)`/`Radius.circular(N)` literals (must use `FieldGuideRadii.of(context).*`)
  - `Duration(milliseconds: N)` in animation contexts (must use `FieldGuideMotion.of(context).*`)
  - `Colors.*` or `Color(0xFF...)` literals (must use `Theme.of(context).colorScheme.*` or `FieldGuideColors.of(context).*`)
- **Missing responsive handling**: raw `MediaQuery.of(context).size.width` comparisons. Should use `AppBreakpoint.of(context)` / `AppResponsiveBuilder` / `AppAdaptiveLayout`.
- **File or method exceeds 300 lines** (hard cap). Files >300 lines and methods/build()/extracted widget classes >300 lines are HIGH and must be decomposed.
- **Missing sync observability** on wizard / multi-step / long-edit screens: any such screen that does NOT extract a `ChangeNotifier` controller and register with `WizardActivityTracker` (`lib/features/sync/application/wizard_activity_tracker.dart`) is a HIGH finding. Sync code cannot detect in-flight drafts without this registration.
- **`// ignore:` or `// ignore_for_file:` comments** suppressing any of the above lint rules — always CRITICAL, never acceptable. Fix the root cause.
- **High-contrast theme references** (`HighContrast`, `hc`, third theme variant) — the HC theme was removed in the design system overhaul; only light + dark exist. Flag any reintroduction.

## Domain Context Loading
Before reviewing, read the applicable rule files based on the files under review:

| File pattern | Read before reviewing |
|-------------|---------------------|
| lib/**/data/** | .claude/rules/backend/data-layer.md |
| lib/core/database/** | .claude/rules/database/schema-patterns.md |
| lib/**/presentation/**, lib/shared/widgets/** | .claude/rules/frontend/flutter-ui.md |
| lib/features/sync/** | .claude/rules/sync/sync-patterns.md |
| lib/features/auth/** | .claude/rules/auth/supabase-auth.md |
| lib/features/pdf/** | .claude/rules/pdf/pdf-generation.md |
| test/**, integration_test/** | .claude/rules/testing/patrol-testing.md |
| .github/workflows/** | .claude/rules/ci-cd.md |
| lib/core/di/**, lib/core/bootstrap/**, lib/core/router/** | .claude/rules/architecture.md |
| supabase/** | .claude/rules/backend/supabase-sql.md |
| android/**, ios/**, windows/** | .claude/rules/platform-standards.md |

This is mandatory. Read the matching rule files before writing any findings.

## Output
Your findings are returned via `--json-schema` structured output. Follow the schema exactly.
Do NOT write files. Your `structured_output` IS the deliverable.
